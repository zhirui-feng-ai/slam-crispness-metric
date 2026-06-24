"""
export_clouds.py — pre-generate 3D point clouds of the on-road `street` scene
for the explorer's 3D viewer (the static app can't run the Python sim live).

Writes Float32 .bin clouds + a manifest.json into explorer/public/clouds/:
  · reference.bin              the ideal (clean) map
  · <mode>_l<level>.bin        observed map under that drift mode + severity

Each .bin is a flat little-endian float32 array [x0,y0,z0, x1,y1,z1, …].
Clouds are random-downsampled (preserves drift smear) to keep the web payload small.
"""

from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from slam_synthbench import (build_scene, make_trajectory, reference_cloud,
                             observed_cloud, inject, LidarConfig)
from slam_synthbench.metrics import voxel_pca_crispness, chamfer_oracle, knn_entropy_mme
from slam_synthbench.sampling import random_downsample

OUT = ROOT / "explorer" / "public" / "clouds"
OUT.mkdir(parents=True, exist_ok=True)

CFG = LidarConfig(n_beams=40, azimuth_step_deg=1.5, max_range=80.0, range_noise_sigma=0.02)
DURATION, SPEED = 14.0, 16.7
NPOINTS = 45_000            # web payload per cloud (~540 KB)
MODES = ["gyro_bias", "random_walk"]
LEVELS = [0.33, 0.66, 1.0]
SEED = 0


def write_bin(cloud, name):
    arr = np.ascontiguousarray(cloud, dtype=np.float32)
    arr.tofile(OUT / name)
    return name, len(cloud)


def metrics_of(cloud, ref):
    return {
        "crispness": round(float(voxel_pca_crispness(cloud, voxel=0.5)), 4),
        "knn_mme": round(float(knn_entropy_mme(cloud)), 3),
        "chamfer": round(float(chamfer_oracle(cloud, ref)), 4),
    }


def run():
    print("[export] building street scene + reference cloud…")
    scene = build_scene("street")
    traj = make_trajectory(scene, speed=SPEED, duration=DURATION)
    ref_full = reference_cloud(scene, traj, CFG)
    ref = random_downsample(ref_full, NPOINTS, seed=SEED)
    b = scene.bounds

    manifest = {
        "scene": "street",
        "bounds": {"x": b[0].tolist(), "y": b[1].tolist(), "z": b[2].tolist()},
        "n_poses": traj.n, "duration": traj.duration,
        "levels": [0.0] + LEVELS,
        "modes": MODES,
        "reference": {"file": "reference.bin", **{"n_points": len(ref)}, **metrics_of(ref, ref)},
        "clouds": {},   # mode -> list of {level, file, n_points, drift_intensity, metrics…}
    }
    write_bin(ref, "reference.bin")

    for mode in MODES:
        rows = [{"level": 0.0, "file": "reference.bin", "n_points": len(ref),
                 "drift_intensity": 0.0, **metrics_of(ref, ref)}]
        for lvl in LEVELS:
            dr = inject(traj, scene, mode, lvl, seed=SEED)
            obs = random_downsample(observed_cloud(scene, traj, dr, CFG, seed=SEED), NPOINTS, seed=SEED)
            fname = f"{mode}_l{int(lvl*100):03d}.bin"
            write_bin(obs, fname)
            rows.append({"level": lvl, "file": fname, "n_points": len(obs),
                         "drift_intensity": round(float(dr.drift_intensity), 3),
                         **metrics_of(obs, ref)})
            print(f"  {mode:12s} level {lvl:.2f}  drift={dr.drift_intensity:5.2f} m  "
                  f"N={len(obs)}  crisp={rows[-1]['crispness']:.3f}")
        manifest["clouds"][mode] = rows

    with open(OUT / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    total_mb = sum(p.stat().st_size for p in OUT.glob("*.bin")) / 1e6
    print(f"[export] wrote {len(list(OUT.glob('*.bin')))} clouds ({total_mb:.1f} MB) + manifest → {OUT}")


if __name__ == "__main__":
    run()
