#!/bin/bash
# The two A-12 new-project cases again, on the same acceptance store, with the office fixture the integration's store had.
APP="/c/Users/DWP2/Desktop/Project walkthrough/app"
cd "$APP"
W="$TEMP/wt-ur"
export WT_TMP="$W/acc" WALKTHROUGH_DATA_DIR="$W/acc/data" WALKTHROUGH_CACHE_DIR="$W/acc/cache" PYTHONIOENCODING=utf-8
mkdir -p "$W/acc/data/mappings"
cp fixtures/upload/mappings/dwp-revit.json "$W/acc/data/mappings/dwp-revit.json"
node tools/run-api.mjs --port 8739 --data "$W/acc/data" > "$W/logs/acc-api2.txt" 2>&1 &
API=$!
for i in $(seq 1 120); do curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8739/api/projects 2>/dev/null | grep -q 200 && break; sleep 1; done
echo "api up after $i s"
C="$W/acc/cases"
node tools/run-py.mjs "$W/scripts/acc.py" --base http://127.0.0.1:8739 --store "$W/acc/data" --out "$W/acc/out" \
  "$C/suite-revit-prep.json" "$C/suite-revit.json"
echo "cases exit $?"
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8739 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force }"
sleep 2; kill $API 2>/dev/null
echo ACC12-DONE
