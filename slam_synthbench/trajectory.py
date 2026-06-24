"""
trajectory.py — ground-truth 3D pose sequences with physical time stamps.

A Trajectory carries the (N,6) clean poses AND the per-pose timestamp `t`
(seconds). Timestamps are load-bearing: the calibrated-bias drift tier integrates
IMU error over *time* (O(t²) accel-bias, O(t³) gyro-bias), so a 30 s segment at
60 km/h must actually span 30 s of `t` for the error budget to be physical
(research-error-accumulation §1).

Default operating point: 60 km/h ≈ 16.7 m/s, 10 Hz pose rate. A 30 s segment is
then ~500 m and 300 poses — the crispness operating window.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .scenes import Scene


@dataclass
class Trajectory:
    poses: np.ndarray   # (N,6) x,y,z,roll,pitch,yaw  (ground truth)
    t: np.ndarray       # (N,) timestamps (seconds)
    speed: float        # m/s (nominal)

    @property
    def n(self) -> int:
        return len(self.poses)

    @property
    def duration(self) -> float:
        return float(self.t[-1] - self.t[0]) if len(self.t) else 0.0


def make_trajectory(scene: Scene, speed: float = 16.7, rate_hz: float = 10.0,
                    duration: float = 30.0, kind: str | None = None) -> Trajectory:
    """
    Build a clean trajectory for `scene`. `kind` overrides scene.path_kind.

    speed     : m/s (default 16.7 ≈ 60 km/h)
    rate_hz   : pose sample rate
    duration  : seconds (default 30 s — the crispness operating window)
    """
    kind = kind or scene.path_kind
    n = max(int(round(duration * rate_hz)), 8)
    t = np.arange(n) / rate_hz
    b = scene.bounds
    poses = np.zeros((n, 6))

    if kind == "loop":
        cx, cy = (b[0].mean(), b[1].mean())
        rx = (b[0, 1] - b[0, 0]) / 2 - 3.0
        ry = (b[1, 1] - b[1, 0]) / 2 - 3.0
        z = (b[2, 1] - b[2, 0]) * 0.5
        # Walk a full loop; speed sets how far around in `duration`.
        circ = 2 * np.pi * np.hypot(rx, ry) / np.sqrt(2)
        laps = max(1, speed * duration / max(circ, 1e-6))
        ang = np.linspace(0, 2 * np.pi * laps, n, endpoint=False)
        poses[:, 0] = cx + rx * np.cos(ang)
        poses[:, 1] = cy + ry * np.sin(ang)
        poses[:, 2] = z
        poses[:, 5] = ang + np.pi / 2  # yaw tangent to the loop

    elif kind == "serpentine":
        x0, x1 = b[0, 0] + 4, b[0, 1] - 4
        y0, y1 = b[1, 0] + 4, b[1, 1] - 4
        z = (b[2, 1] - b[2, 0]) * 0.4
        s = np.linspace(0, 1, n)
        poses[:, 0] = x0 + (x1 - x0) * s
        poses[:, 1] = (y0 + y1) / 2 + (y1 - y0) / 2 * np.sin(s * np.pi * 3)
        poses[:, 2] = z
        dx = np.gradient(poses[:, 0]); dy = np.gradient(poses[:, 1])
        poses[:, 5] = np.arctan2(dy, dx)

    else:  # "straight" — corridor / tunnel / highway
        x0 = b[0, 0] + 2.0
        travel = min(speed * duration, (b[0, 1] - b[0, 0]) - 4.0)
        z = (b[2, 1] - b[2, 0]) * 0.4
        poses[:, 0] = np.linspace(x0, x0 + travel, n)
        poses[:, 1] = b[1].mean()
        poses[:, 2] = z
        poses[:, 5] = 0.0  # heading +x

    return Trajectory(poses=poses, t=t, speed=speed)
