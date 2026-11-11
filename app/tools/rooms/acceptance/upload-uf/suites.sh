#!/bin/bash
# Final check (UF): every suite from a clean start, one after the other, in a fresh WT_TMP (ports 5740 / 8740).
APP="/c/Users/DWP2/Desktop/Project walkthrough/app"
cd "$APP" || exit 9
W="$TEMP/wt-uf"
export WT_TMP="$W/suites" WALKTHROUGH_DATA_DIR="$W/suites/data" WALKTHROUGH_CACHE_DIR="$W/suites/cache"
export WT_WEB_PORT=5740 WT_API_PORT=8740 PYTHONIOENCODING=utf-8 WT_REF="$TEMP/wt-u0/ref"
rm -rf "$WT_TMP"; mkdir -p "$WT_TMP/api-tests"
L="$W/logs"
SUM="$L/suites-summary.txt"
: > "$SUM"
run() {
  local name=$1; shift
  local t0=$(date +%s)
  "$@" > "$L/suite-$name.txt" 2>&1
  local rc=$?
  local line="$name exit $rc ($(( $(date +%s) - t0 )) s): $(grep -E 'passed|failed|error|ok \(|Tests |Test Files' "$L/suite-$name.txt" | tail -3 | tr '\n' ' ' | cut -c1-400)"
  echo "$line" | tee -a "$SUM"
}
run check-pins npm run check:pins
run typecheck npm run typecheck
run unit npm run test:unit
run builder npm run test:builder
run api npm run test:api
WT_INTEGRATION=1 run api-integration npm run test:api
run gen-api npm run gen:api
echo "gen:api git status (empty = no change): [$(cd .. && git status --porcelain -- app/apps/web/openapi.json app/apps/web/src/api/generated | tr '\n' ' ')]" | tee -a "$SUM"
run additive node tools/check-openapi-additive.mjs
run build npm run build
echo "after build, git status of app/ (empty = nothing tracked changed): [$(cd .. && git status --porcelain -- app | tr '\n' ' ')]" | tee -a "$SUM"
echo SUITES-DONE | tee -a "$SUM"
