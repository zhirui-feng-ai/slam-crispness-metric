# SynthBench Explorer

Static React + Vite front-end for browsing the synthetic-experiment outputs.
Reads the generated `results/`, `figures/`, and `reports/` — no backend.

## Run

```bash
cd synthetic-experiment/explorer
npm install          # first time (approve esbuild scripts if prompted)
npm run dev          # → http://localhost:5173  (auto-syncs data first)
# or a production build:
npm run build && npm run preview
```

`npm run dev`/`build` run [`sync-data.sh`](sync-data.sh) first, which copies the
latest experiment outputs into `public/`. After re-running
`python experiments/run_all.py`, just `npm run sync` (or restart dev) to refresh.

**3D Road Scene clouds** are generated separately (they're large binaries written
straight into `public/clouds/`):

```bash
./.venv/bin/python experiments/export_clouds.py   # regenerate street clouds
```
Edit `MODES` / `LEVELS` / `NPOINTS` in that script to change what the viewer offers.

## Views

| Tab | What |
|---|---|
| **Overview** | pipeline, headline stats, key findings |
| **How It Works** | from-scratch math tutorial + interactive eigenvalue demo |
| **3D Road Scene** | Three.js point-cloud viewer of an urban street; slider morphs clean → drifted |
| **Scorecard** | sortable metric × dimension table (heat-colored) + recommendations + F0 |
| **Dataset Explorer** | live replot from `core_dataset.csv` — pick scene/mode/metrics, overlay the oracle |
| **Catalogs** | the 5 scenes, 18 drift modes (by tier, with physical models), 6 metrics |
| **Figures** | all 9 generated figures with captions |
| **Reports** | `results.md` / `methods.md` rendered with figures inline |

## Notes

- Static only: the Dataset Explorer replots the **already-computed** 432-sample
  sweep. To evaluate parameter combinations outside that sweep, extend the sweep
  in `experiments/` and re-sync (a live Python backend could be added as a future
  "live" tab).
- `public/data`, `public/figures`, `public/reports` are git-ignored generated
  copies — `npm run sync` recreates them.
