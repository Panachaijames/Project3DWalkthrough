#!/bin/bash
cd "/c/Users/DWP2/Desktop/Project walkthrough/app"
export WT_TMP="$TEMP/wt-ur/final" WALKTHROUGH_DATA_DIR="$TEMP/wt-ur/final/data" WALKTHROUGH_CACHE_DIR="$TEMP/wt-ur/final/cache"
export WT_WEB_PORT=5739 WT_API_PORT=8739 PYTHONIOENCODING=utf-8 WT_REF="$TEMP/wt-u0/ref"
mkdir -p "$WT_TMP/api-tests"
L="$TEMP/wt-ur/logs"
run() { local name=$1; shift; local t0=$(date +%s); "$@" > "$L/final-$name.txt" 2>&1; local rc=$?; echo "$name exit $rc ($(( $(date +%s) - t0 )) s): $(tail -3 "$L/final-$name.txt" | tr '\n' ' ' | cut -c1-300)"; }
run check-pins npm run check:pins
run typecheck npm run typecheck
run unit npm run test:unit
run builder npm run test:builder
run api npm run test:api
WT_INTEGRATION=1 run api-integration npm run test:api
echo ALL-DONE
