#!/bin/bash
# Final check (UF): the checks on the recorded acceptance cases (A-1, A-3 / A-4, A-8, A-9, A-10, the head-table numbers).
cd "/c/Users/DWP2/Desktop/Project walkthrough/app" || exit 9
W="$TEMP/wt-uf"
export PYTHONIOENCODING=utf-8
PY=/c/Python314/python.exe
L="$W/logs"
echo "== A-1"; $PY -B "$W/scripts/check_a1.py" "$W/acc/out" "$W/acc/data" "$W/acc/cache" > "$L/check-a1.txt" 2>&1; echo "exit $?"; cut -c1-2500 "$L/check-a1.txt"
echo "== A-3 / A-4"; $PY -B "$W/scripts/check_a3_a4.py" "$W/acc/out" "$W/acc/data" > "$L/check-a3a4.txt" 2>&1; echo "exit $?"; cut -c1-1500 "$L/check-a3a4.txt"
echo "== A-8"; $PY -B "$W/scripts/check_a8.py" "$W/acc/out" "$W/acc/data" > "$L/check-a8.txt" 2>&1; echo "exit $?"; cat "$L/check-a8.txt"
echo "== A-9"; $PY -B -c "
import json,os
r=json.load(open(os.path.join(r'$W','acc','out','a9','record.json'),encoding='utf-8'))
print('ok', r.get('ok'), r.get('error'))
for k in ('report2fixes','report3fixes'):
    print(k, json.dumps(r.get(k), ensure_ascii=False)[:1500])
print('reuploadFixesEqual', r.get('reuploadFixesEqual'), 'model3EqualsModel2', r.get('model3EqualsModel2'))
print('furniture', r.get('furniture'), 'parts', r.get('parts'), 'openingKinds', r.get('openingKinds'))
print('diff2', json.dumps(r.get('diff2'), ensure_ascii=False)[:800])
"
echo "== A-10"; $PY -B "$W/scripts/times.py" "$W/acc/out" > "$L/times.txt" 2>&1; cat "$L/times.txt"
echo "== versions"; $PY -B "$W/scripts/version_rows.py" "$W/acc/data" > "$L/version-rows.txt" 2>&1; cat "$L/version-rows.txt"
