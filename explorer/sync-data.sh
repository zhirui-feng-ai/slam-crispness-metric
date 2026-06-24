#!/usr/bin/env bash
# Copy the latest generated experiment outputs into the explorer's public/ dir.
# Run automatically by `npm run dev` / `npm run build`, or manually: `npm run sync`.
set -e
cd "$(dirname "$0")"
mkdir -p public/data public/figures public/reports
cp ../experiments/results/*.json ../experiments/results/*.csv public/data/ 2>/dev/null || true
cp ../figures/*.png public/figures/ 2>/dev/null || true
cp ../reports/*.md public/reports/ 2>/dev/null || true
echo "synced: $(ls public/data | wc -l | tr -d ' ') data files, $(ls public/figures | wc -l | tr -d ' ') figures, $(ls public/reports | wc -l | tr -d ' ') reports"
