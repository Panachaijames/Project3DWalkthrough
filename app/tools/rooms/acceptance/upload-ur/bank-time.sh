#!/bin/bash
cd "/c/Users/DWP2/Desktop/Project walkthrough/app"
W="$TEMP/wt-ur"
export WT_TMP="$W/acc-time" WALKTHROUGH_DATA_DIR="$W/acc-time/data" WALKTHROUGH_CACHE_DIR="$W/acc-time/cache" PYTHONIOENCODING=utf-8
rm -rf "$W/acc-time"; mkdir -p "$W/acc-time/out"
node tools/run-api.mjs --port 8739 --data "$W/acc-time/data" --seed-fresh > "$W/logs/acc-time-api.txt" 2>&1 &
API=$!
for i in $(seq 1 120); do curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8739/api/projects 2>/dev/null | grep -q 200 && break; sleep 1; done
node tools/run-py.mjs "$W/scripts/acc.py" --base http://127.0.0.1:8739 --store "$W/acc-time/data" --out "$W/acc-time/out" "$W/acc/cases/bank-time.json"
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8739 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force }"
sleep 2; kill $API 2>/dev/null
python -c "
import json,os
r=json.load(open(os.path.join(os.environ['TEMP'],'wt-ur','acc-time','out','bank-time','record.json'),encoding='utf-8'))
p=r['prepare']; print('wall', p['wall'], {s['name']: s['seconds'] for s in p['run']['steps']})
"
