#!/bin/bash
# UR's e2e re-run (WORK_BREAKDOWN UI step 5 again): every spec, the walk checks on the acceptance store's offline files.
cd "/c/Users/DWP2/Desktop/Project walkthrough/app"
W="$TEMP/wt-ur"
export WT_TMP="$W/e2e" WT_WEB_PORT=5739 WT_API_PORT=8739 PYTHONIOENCODING=utf-8
export WT_UPLOAD_OFFLINE_DIR="$W/offline" WT_UPLOAD_DATA_DIR="$W/acc/data"
export WT_UPLOAD_WALK_SHOULD="house-upload,suite-upload,suite-outlines,tower-upload,suite-revit,presidential-suite"
rm -rf "$W/e2e"; mkdir -p "$W/e2e"
t0=$(date +%s)
npm run test:e2e > "$W/logs/e2e.txt" 2>&1
echo "e2e exit $? ($(( $(date +%s) - t0 )) s): $(grep -E 'passed|failed|flaky|skipped' "$W/logs/e2e.txt" | tail -4 | tr '\n' ' ')"
