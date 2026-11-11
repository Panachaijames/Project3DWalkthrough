#!/bin/bash
# Final check (UF): every e2e spec (npm run test:e2e: a freshly seeded e2e store, the real API and worker), with the walk
# checks of A-6 on the offline files of the versions the acceptance run saved (made with make-offline.mjs).
cd "/c/Users/DWP2/Desktop/Project walkthrough/app" || exit 9
W="$TEMP/wt-uf"
export WT_TMP="$W/e2e" WT_WEB_PORT=5740 WT_API_PORT=8740 PYTHONIOENCODING=utf-8
export WT_UPLOAD_OFFLINE_DIR="$W/offline" WT_UPLOAD_DATA_DIR="$W/acc/data"
export WT_UPLOAD_WALK_SHOULD="house-upload,suite-upload,suite-outlines,tower-upload,suite-revit,presidential-suite"
rm -rf "$W/e2e"; mkdir -p "$W/e2e"
t0=$(date +%s)
npm run test:e2e > "$W/logs/e2e.txt" 2>&1
rc=$?
echo "e2e exit $rc ($(( $(date +%s) - t0 )) s): $(grep -E '^\s+[0-9]+ (passed|failed|flaky|skipped|did not run)' "$W/logs/e2e.txt" | tr '\n' ' ')" | tee "$W/logs/e2e-summary.txt"
