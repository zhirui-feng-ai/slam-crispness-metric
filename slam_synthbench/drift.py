"""
drift.py — physically-grounded drift injection, organized by the research's
three error tiers (research-failure-modes §"Noise/Bias/Failure Taxonomy",
research-error-accumulation §1, research-imu-grades §1-2).

    Tier            Modes                          Crispness should…
    ────────────    ───────────────────────────    ──────────────────────────
    NOISE           sensor_noise                   …NOT fire (zero-mean, benign)
    BIAS            accel_bias (O(t²)),            …fire — this is the target
                    gyro_bias  (O(t³))               (monotonic surface smear)
    CATASTROPHIC    dynamic_objects, degeneracy,   …crater hard
                    weather_dropout, imu_saturation
    PHENOMENOLOGICAL  the original 7 patterns,     …(legacy baseline, recalibrated
                      ported to 3D / physical units    to meters & 6-DoF)

Every mode is a function  f(traj, scene, level, rng) -> (pose_errors (N,6),
SensorEffects).  `level` ∈ [0,1] is a dimensionless severity knob; each mode
maps it to physical magnitude internally and the realized RMS position error
(meters) is reported as `drift_intensity` — the true sweep x-axis. Modes that
corrupt the cloud without moving the ego pose (noise, weather, dynamic objects)
report drift_intensity≈0 and expose their realized physical parameter instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import numpy as np

from .geometry import Quad, box_quads
from .trajectory import Trajectory
from .scenes import Scene

G = 9.81  # m/s²


class Tier(str, Enum):
    NOISE = "noise"
    BIAS = "bias"
    CATASTROPHIC = "catastrophic"
    PHENOMENOLOGICAL = "phenomenological"


@dataclass
class SensorEffects:
    """Sensor-level corruption a drift mode may request (None = use cfg default)."""
    range_noise_sigma: float | None = None
    dropout_prob: float | None = None
    max_range: float | None = None
    scale_factor: float = 1.0          # RANGE_SCALE: multiply local distances
    dynamic_quads = None               # callable(i, n) -> list[Quad] | None


@dataclass
class DriftResult:
    perturbed_poses: np.ndarray   # (N,6) drifted (SLAM-estimated) poses
    pose_errors: np.ndarray       # (N,6) per-pose error
    drift_intensity: float        # RMS position error (meters)
    effects: SensorEffects
    mode: str
    tier: str
    level: float
    realized: dict                # mode-specific physical params (for labeling x-axis)


# ── IMU grade table (research-imu-grades §1-2) ───────────────────────────────

@dataclass(frozen=True)
class IMUGrade:
    name: str
    gyro_bias_dph: float    # gyro bias instability, °/h
    accel_bias_mg: float    # accel bias instability, mg
    pos_err_60s: float      # unaided dead-reckon position error at 60 s, meters

IMU_GRADES = {
    "consumer":   IMUGrade("consumer",   100.0, 3.0,   400.0),
    "industrial": IMUGrade("industrial",   8.0, 0.5,    40.0),
    "tactical":   IMUGrade("tactical",     0.5, 0.05,    5.0),
    "navigation": IMUGrade("navigation",   0.02, 0.005,  0.5),
}
IMU_GRADE_ORDER = ["consumer", "industrial", "tactical", "navigation"]


# ── helpers ──────────────────────────────────────────────────────────────────

def _zero_errors(n: int) -> np.ndarray:
    return np.zeros((n, 6))


def _tau(traj: Trajectory) -> np.ndarray:
    return traj.t - traj.t[0]


def _heading_dirs(traj: Trajectory) -> tuple[np.ndarray, np.ndarray]:
    """Unit forward (heading) and left (lateral) world directions at pose 0."""
    yaw0 = traj.poses[0, 5]
    fwd = np.array([np.cos(yaw0), np.sin(yaw0), 0.0])
    left = np.array([-np.sin(yaw0), np.cos(yaw0), 0.0])
    return fwd, left


def _rms_pos(errors: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.sum(errors[:, :3] ** 2, axis=1))))


# ── NOISE tier ─────────────────────────────────────────────────────────────

def sensor_noise(traj, scene, level, rng):
    """Zero-mean per-point range jitter. 0 → 0.15 m. No pose error (benign)."""
    sigma = 0.02 + level * 0.13
    eff = SensorEffects(range_noise_sigma=sigma)
    return _zero_errors(traj.n), eff, {"range_noise_sigma": sigma}


# ── BIAS tier (calibrated O(t²)/O(t³)) ───────────────────────────────────────

def accel_bias_field(traj, b_a, direction):
    """Position error ½·b_a·t² along `direction`. b_a in m/s²."""
    tau = _tau(traj)
    mag = 0.5 * b_a * tau ** 2
    err = _zero_errors(traj.n)
    err[:, :3] = mag[:, None] * direction[None, :]
    return err


def gyro_bias_field(traj, b_g, direction):
    """Gravity-coupled cubic position error (1/6)·g·b_g·t³ + linear tilt b_g·t.
    b_g in rad/s. (research-error-accumulation §1.)"""
    tau = _tau(traj)
    mag = (1.0 / 6.0) * G * b_g * tau ** 3
    err = _zero_errors(traj.n)
    err[:, :3] = mag[:, None] * direction[None, :]
    err[:, 5] = b_g * tau            # heading error grows linearly
    err[:, 4] = 0.5 * b_g * tau      # mild pitch tilt
    return err


def accel_bias(traj, scene, level, rng):
    """level → b_a ∈ [0, 1e-2] m/s²  (~0 → 4.5 m at 30 s)."""
    b_a = level * 1.0e-2
    fwd, left = _heading_dirs(traj)
    direction = (fwd + 0.6 * left)
    direction /= np.linalg.norm(direction)
    err = accel_bias_field(traj, b_a, direction)
    return err, SensorEffects(), {"b_a_mps2": b_a, "b_a_mg": b_a / (G * 1e-3)}


def gyro_bias(traj, scene, level, rng):
    """level → b_g ∈ [0, 1e-4] rad/s  (~0 → 4.4 m at 30 s, the O(t³) target)."""
    b_g = level * 1.0e-4
    fwd, left = _heading_dirs(traj)
    err = gyro_bias_field(traj, b_g, left)
    return err, SensorEffects(), {"b_g_rad_s": b_g, "b_g_dph": np.rad2deg(b_g) * 3600}


def imu_grade_bias(grade_name):
    """Factory: a BIAS mode reproducing a specific IMU grade's unaided drift.
    level scales the grade's nominal 30 s error (gyro-bias-dominated t³ shape)."""
    grade = IMU_GRADES[grade_name]

    def mode(traj, scene, level, rng):
        tau = _tau(traj)
        T = max(tau[-1], 1e-6)
        # t³ growth normalized so the curve reaches the grade's 30 s magnitude.
        target_30s = grade.pos_err_60s * (30.0 / 60.0) ** 3   # t³ scaling from 60 s table
        mag = level * target_30s * (tau / T) ** 3
        fwd, left = _heading_dirs(traj)
        err = _zero_errors(traj.n)
        err[:, :3] = mag[:, None] * left[None, :]
        err[:, 5] = np.deg2rad(grade.gyro_bias_dph) / 3600.0 * tau
        return err, SensorEffects(), {"grade": grade_name, "pos_err_30s": float(mag[-1])}

    return mode


# ── CATASTROPHIC tier ────────────────────────────────────────────────────────

def dynamic_objects(traj, scene, level, rng):
    """Moving vehicles leave ghost trails (research-failure-modes §2). Ego pose
    unaffected; the map is corrupted by transient surfaces swept across time."""
    n_obj = int(round(1 + level * 5))           # 1 → 6 moving cars
    b = scene.bounds
    starts, vels, sizes = [], [], []
    for _ in range(n_obj):
        sx = rng.uniform(b[0, 0] + 5, b[0, 1] - 5)
        sy = rng.uniform(b[1, 0] + 2, b[1, 1] - 2)
        starts.append([sx, sy, 0.8])
        speed = rng.uniform(3.0, 12.0) * rng.choice([-1, 1])
        vels.append([speed, rng.uniform(-1, 1), 0.0])
        sizes.append([4.5, 1.9, 1.5])
    starts = np.array(starts); vels = np.array(vels); sizes = np.array(sizes)
    span = traj.duration

    def dyn(i, n):
        frac = i / max(n - 1, 1)
        quads = []
        for s0, v, sz in zip(starts, vels, sizes):
            c = s0 + v * (frac * span)
            quads += box_quads([c[0], c[1], sz[2] / 2], sz)
        return quads

    eff = SensorEffects()
    eff.dynamic_quads = dyn
    return _zero_errors(traj.n), eff, {"n_objects": n_obj}


def geometric_degeneracy(traj, scene, level, rng):
    """ICP 'slide' along the scene's unconstrained axis (research-failure-modes
    §1). Random-walk + slow bias along degenerate_axis; tiny elsewhere."""
    axis = scene.degenerate_axis
    if axis is None:
        fwd, _ = _heading_dirs(traj); axis = fwd
    axis = np.asarray(axis, float); axis = axis / np.linalg.norm(axis)
    n = traj.n
    step = level * 0.25                       # per-step slide std (meters)
    walk = np.cumsum(rng.normal(0, step, n))
    bias = level * 4.0 * (_tau(traj) / max(_tau(traj)[-1], 1e-6))  # up to 4 m creep
    mag = walk + bias
    err = _zero_errors(n)
    err[:, :3] = mag[:, None] * axis[None, :]
    # small incidental cross-axis jitter
    err[:, :3] += rng.normal(0, step * 0.1, (n, 3))
    return err, SensorEffects(), {"degenerate_axis": axis.tolist()}


def weather_dropout(traj, scene, level, rng):
    """Rain/fog: point dropout + range collapse (research-failure-modes §5).
    No pose smear — tests metric behavior under sparsity, not drift."""
    dp = level * 0.6                           # up to 60% point loss (≈ heavy rain)
    max_range = 80.0 - level * 55.0            # 80 m → 25 m (fog collapse)
    eff = SensorEffects(dropout_prob=dp, max_range=max_range)
    return _zero_errors(traj.n), eff, {"dropout_prob": dp, "max_range": max_range}


def imu_saturation(traj, scene, level, rng):
    """Gyro clips during an aggressive maneuver window → garbage heading →
    localized rotational smear, partial recovery (research-failure-modes §3)."""
    n = traj.n
    err = _zero_errors(n)
    w0, w1 = int(0.45 * n), int(0.58 * n)
    peak = level * 0.6                         # up to ~34° heading error at peak
    yaw_err = np.zeros(n)
    yaw_err[w0:w1] = np.linspace(0, peak, w1 - w0)
    yaw_err[w1:] = peak * 0.5                  # partial recovery (residual bias)
    err[:, 5] = yaw_err
    # heading error couples into position via lever arm from sensor offset
    fwd, left = _heading_dirs(traj)
    err[:, :3] = (yaw_err[:, None] * 1.5) * left[None, :]
    return err, SensorEffects(), {"peak_yaw_rad": peak}


# ── PHENOMENOLOGICAL tier (original 7, ported to 3D + physical units) ────────

def _phen_random_walk(traj, scene, level, rng):
    n = traj.n
    s = level * 0.12
    err = _zero_errors(n)
    err[:, 0] = np.cumsum(rng.normal(0, s, n))
    err[:, 1] = np.cumsum(rng.normal(0, s, n))
    err[:, 5] = np.cumsum(rng.normal(0, s * 0.01, n))
    return err, SensorEffects(), {"step_sigma": s}


def _phen_yaw_bias(traj, scene, level, rng):
    n = traj.n
    rate = level * 0.004
    cdt = np.cumsum(rng.normal(1.0, 0.1, n) * rate)
    err = _zero_errors(n)
    err[:, 5] = cdt
    err[:, 0] = np.sin(cdt) * level * 3.0
    err[:, 1] = -np.cos(cdt) * level * 3.0 + level * 3.0
    return err, SensorEffects(), {"yaw_rate": rate}


def _phen_range_scale(traj, scene, level, rng):
    sf = 1.0 + level * 0.04
    return _zero_errors(traj.n), SensorEffects(scale_factor=sf), {"scale_factor": sf}


def _phen_loop_seam(traj, scene, level, rng):
    n = traj.n
    s = level * 0.12
    loop_at = int(n * 0.65)
    err = _zero_errors(n)
    cx = np.cumsum(rng.normal(0, s, n)); cy = np.cumsum(rng.normal(0, s, n))
    err[:loop_at, 0] = cx[:loop_at]; err[:loop_at, 1] = cy[:loop_at]
    # snap to 0 after closure → ghost seam between the two halves
    return err, SensorEffects(), {"loop_at": loop_at}


def _phen_sinusoidal(traj, scene, level, rng):
    n = traj.n
    t = np.linspace(0, 2 * np.pi, n)
    freq = 5.0
    err = _zero_errors(n)
    err[:, 0] = level * 2.0 * np.sin(t * freq)
    err[:, 1] = level * 2.0 * np.cos(t * freq)
    return err, SensorEffects(), {"freq": freq}


def _phen_step_jump(traj, scene, level, rng):
    n = traj.n
    step_at = int(n * 0.5)
    err = _zero_errors(n)
    err[step_at:, 0] = level * 2.5
    err[step_at:, 1] = level * 1.4
    err[step_at:, 5] = level * 0.04
    return err, SensorEffects(), {"step_at": step_at}


def _phen_gyro_saturation(traj, scene, level, rng):
    n = traj.n
    rate = level * 0.006
    err = _zero_errors(n)
    err[:, 5] = np.cumsum(rng.normal(1.0, 0.1, n) * rate)  # pure heading drift
    return err, SensorEffects(), {"gyro_rate": rate}


# ── Registry ──────────────────────────────────────────────────────────────

DRIFT_MODES = {
    # tier, fn
    "sensor_noise":        (Tier.NOISE, sensor_noise),
    "accel_bias":          (Tier.BIAS, accel_bias),
    "gyro_bias":           (Tier.BIAS, gyro_bias),
    "dynamic_objects":     (Tier.CATASTROPHIC, dynamic_objects),
    "geometric_degeneracy":(Tier.CATASTROPHIC, geometric_degeneracy),
    "weather_dropout":     (Tier.CATASTROPHIC, weather_dropout),
    "imu_saturation":      (Tier.CATASTROPHIC, imu_saturation),
    "random_walk":         (Tier.PHENOMENOLOGICAL, _phen_random_walk),
    "yaw_bias":            (Tier.PHENOMENOLOGICAL, _phen_yaw_bias),
    "range_scale":         (Tier.PHENOMENOLOGICAL, _phen_range_scale),
    "loop_closure_seam":   (Tier.PHENOMENOLOGICAL, _phen_loop_seam),
    "sinusoidal":          (Tier.PHENOMENOLOGICAL, _phen_sinusoidal),
    "step_jump":           (Tier.PHENOMENOLOGICAL, _phen_step_jump),
    "gyro_saturation":     (Tier.PHENOMENOLOGICAL, _phen_gyro_saturation),
}


# Register one BIAS mode per IMU grade (used by the IMU-grade experiment).
for _g in IMU_GRADE_ORDER:
    DRIFT_MODES[f"imu_{_g}"] = (Tier.BIAS, imu_grade_bias(_g))


def list_modes(tier: Tier | None = None) -> list[str]:
    if tier is None:
        return list(DRIFT_MODES)
    return [k for k, (t, _) in DRIFT_MODES.items() if t == tier]


def inject(traj: Trajectory, scene: Scene, mode: str, level: float,
           seed: int = 0) -> DriftResult:
    """Apply drift `mode` at severity `level` to a clean trajectory."""
    if mode not in DRIFT_MODES:
        raise KeyError(f"unknown drift mode {mode!r}; have {list(DRIFT_MODES)}")
    tier, fn = DRIFT_MODES[mode]
    rng = np.random.default_rng(seed)
    pose_errors, effects, realized = fn(traj, scene, level, rng)
    perturbed = traj.poses + pose_errors
    return DriftResult(
        perturbed_poses=perturbed,
        pose_errors=pose_errors,
        drift_intensity=_rms_pos(pose_errors),
        effects=effects,
        mode=mode,
        tier=tier.value,
        level=level,
        realized=realized,
    )
