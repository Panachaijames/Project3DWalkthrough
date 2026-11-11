#!/bin/bash
cd "/c/Users/DWP2/Desktop/Project walkthrough/app"
export WT_TMP="$TEMP/wt-ur/final2" WALKTHROUGH_DATA_DIR="$TEMP/wt-ur/final2/data" WALKTHROUGH_CACHE_DIR="$TEMP/wt-ur/final2/cache"
export WT_WEB_PORT=5739 WT_API_PORT=8739 PYTHONIOENCODING=utf-8 WT_REF="$TEMP/wt-u0/ref"
rm -rf "$WT_TMP"; mkdir -p "$WT_TMP/api-tests"
L="$TEMP/wt-ur/logs"
run() { local name=$1; shift; local t0=$(date +%s); "$@" > "$L/final2-$name.txt" 2>&1; local rc=$?; echo "$name exit $rc ($(( $(date +%s) - t0 )) s): $(tail -1 "$L/final2-$name.txt" | cut -c1-200)"; }
run api npm run test:api
WT_INTEGRATION=1 run api-integration npm run test:api
echo API-DONE
