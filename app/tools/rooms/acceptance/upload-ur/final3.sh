#!/bin/bash
cd "/c/Users/DWP2/Desktop/Project walkthrough/app"
export WT_TMP="$TEMP/wt-ur/final3" WALKTHROUGH_DATA_DIR="$TEMP/wt-ur/final3/data" WALKTHROUGH_CACHE_DIR="$TEMP/wt-ur/final3/cache"
export WT_WEB_PORT=5739 WT_API_PORT=8739 PYTHONIOENCODING=utf-8 WT_REF="$TEMP/wt-u0/ref"
rm -rf "$WT_TMP"; mkdir -p "$WT_TMP/api-tests"
L="$TEMP/wt-ur/logs"
run() { local name=$1; shift; local t0=$(date +%s); "$@" > "$L/final3-$name.txt" 2>&1; local rc=$?; echo "$name exit $rc ($(( $(date +%s) - t0 )) s): $(grep -E 'passed|failed|ok \(|error' "$L/final3-$name.txt" | tail -2 | tr '\n' ' ' | cut -c1-220)"; }
run check-pins npm run check:pins
run typecheck npm run typecheck
run unit npm run test:unit
run builder npm run test:builder
echo FINAL3-DONE
