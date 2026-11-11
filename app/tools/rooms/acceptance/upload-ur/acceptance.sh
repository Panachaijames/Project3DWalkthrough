#!/bin/bash
# UR's acceptance re-run (WORK_BREAKDOWN UI step 4 again): a served API on 8739 over a freshly seeded store, the real
# worker, the cases of the integration step in order, then the A-1, A-8, A-9 and A-10 checks.
APP="/c/Users/DWP2/Desktop/Project walkthrough/app"
cd "$APP"
W="$TEMP/wt-ur"
export WT_TMP="$W/acc" WALKTHROUGH_DATA_DIR="$W/acc/data" WALKTHROUGH_CACHE_DIR="$W/acc/cache" PYTHONIOENCODING=utf-8
rm -rf "$W/acc/data" "$W/acc/cache" "$W/acc/out"; mkdir -p "$W/acc/out"
node tools/run-api.mjs --port 8739 --data "$W/acc/data" --seed-fresh > "$W/logs/acc-api.txt" 2>&1 &
API=$!
for i in $(seq 1 120); do curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8739/api/projects 2>/dev/null | grep -q 200 && break; sleep 1; done
echo "api up after $i s"
C="$W/acc/cases"
node tools/run-py.mjs "$W/scripts/acc.py" --base http://127.0.0.1:8739 --store "$W/acc/data" --out "$W/acc/out" \
  "$C/bank-reupload.json" "$C/bank-v3.json" "$C/house.json" "$C/suite.json" "$C/suite-outlines.json" "$C/tower.json" \
  "$C/xx-probe.json" "$C/suite-revit-prep.json" "$C/suite-v2-prep.json" "$C/suite-revit.json" "$C/suite-v2.json"
echo "cases exit $?"
node tools/run-py.mjs "$W/scripts/a9.py" --base http://127.0.0.1:8739 --store "$W/acc/data" --out "$W/acc/out"
echo "a9 exit $?"
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8739 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force }"
sleep 2; kill $API 2>/dev/null
echo ACC-DONE
