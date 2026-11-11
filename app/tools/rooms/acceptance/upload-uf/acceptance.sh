#!/bin/bash
# Final check (UF): the acceptance cases of ACCEPTANCE.md through a SERVED API (node tools/run-api.mjs --seed-fresh, a
# freshly seeded store in %TEMP%\wt-uf\acc\data, a fresh cache) and the real worker, in the integration step's order;
# then A-9 on the same store. The office fixture dwp-revit goes into the store before the A-12 cases (A-12: "with the
# office mapping"; a fresh seed has no office).
APP="/c/Users/DWP2/Desktop/Project walkthrough/app"
cd "$APP" || exit 9
W="$TEMP/wt-uf"
export WT_TMP="$W/acc" WALKTHROUGH_DATA_DIR="$W/acc/data" WALKTHROUGH_CACHE_DIR="$W/acc/cache" PYTHONIOENCODING=utf-8
PORT=8740
rm -rf "$W/acc/data" "$W/acc/cache" "$W/acc/out"; mkdir -p "$W/acc/out"
node tools/run-api.mjs --port $PORT --data "$W/acc/data" --seed-fresh > "$W/logs/acc-api.txt" 2>&1 &
API=$!
for i in $(seq 1 180); do curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:$PORT/api/health 2>/dev/null | grep -q 200 && break; sleep 1; done
echo "api up after $i s"
C="$W/acc/cases"
node tools/run-py.mjs "$W/scripts/acc.py" --base http://127.0.0.1:$PORT --store "$W/acc/data" --out "$W/acc/out" \
  "$C/bank-reupload.json" "$C/bank-v3.json" "$C/house.json" "$C/suite.json" "$C/suite-outlines.json" "$C/tower.json" \
  "$C/xx-probe.json"
echo "cases (first batch) exit $?"
mkdir -p "$W/acc/data/mappings"
cp fixtures/upload/mappings/dwp-revit.json "$W/acc/data/mappings/dwp-revit.json"
node tools/run-py.mjs "$W/scripts/acc.py" --base http://127.0.0.1:$PORT --store "$W/acc/data" --out "$W/acc/out" \
  "$C/suite-revit-prep.json" "$C/suite-v2-prep.json" "$C/suite-revit.json" "$C/suite-v2.json"
echo "cases (A-12) exit $?"
node tools/run-py.mjs "$W/scripts/a9.py" --base http://127.0.0.1:$PORT --store "$W/acc/data" --out "$W/acc/out"
echo "a9 exit $?"
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force }"
sleep 2; kill $API 2>/dev/null
echo ACC-DONE
