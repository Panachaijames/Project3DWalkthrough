#!/bin/bash
# RI (rooms milestone), the acceptance runner's step `rooms-builds` (ACCEPTANCE RA-3 - RA-9, RA-13, RA-14): a served API
# over the acceptance store (<WT_TMP>/data, started as a copy of R0's copy of the upload milestone's store, so one store
# holds the eight old versions and the new ones), the real worker, then:
#   * the five drawings with the new rule (fixtures/upload/settings/<name>-rooms.json), each a new project saved as v1;
#   * the tower and the new suite again with every item of their single-line flags set aside (build1, then build2 with
#     the set-asides; build2 saved);
#   * RA-13 (ra13.py): the new fixes through a rebuild and a re-upload, on the house.
# Records in <WT_TMP>/out/<case>/ (acc.py). Run from app/ by run.mjs (WT_TMP set); ports WT_API_PORT (default 8748).
set -u
APP="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$APP" || exit 9
HERE="$APP/tools/rooms/acceptance"
: "${WT_TMP:?WT_TMP must be set (run.mjs sets it)}"
PORT="${WT_API_PORT:-8748}"
case "$PORT" in 8710|5710) echo "never the owner's ports"; exit 2;; esac
W="$WT_TMP"
SRC="${WT_ACC_STORE_FROM:-$TEMP/wt-r0/acc-9nov}"
if [ ! -d "$W/data/projects" ]; then
  echo "copying the acceptance store $SRC -> $W/data (and its cache)"
  mkdir -p "$W/data" && cp -r "$SRC/." "$W/data/" || exit 3
  [ -d "${SRC}-cache" ] && mkdir -p "$W/cache" && cp -r "${SRC}-cache/." "$W/cache/"
fi
export WALKTHROUGH_DATA_DIR="$W/data" WALKTHROUGH_CACHE_DIR="$W/cache" PYTHONIOENCODING=utf-8
mkdir -p "$W/out" "$W/logs"
node tools/run-api.mjs --port "$PORT" --data "$W/data" > "$W/logs/rooms-api.txt" 2>&1 &
API=$!
for i in $(seq 1 120); do curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/api/projects" 2>/dev/null | grep -q 200 && break; sleep 1; done
echo "api up after $i s"
C="$HERE/rooms/cases"
CASES="${WT_ROOMS_CASES:-bank-rooms house-rooms suite-rooms tower-rooms suite-revit-rooms tower-aside suite-revit-aside}"
ARGS=()
for c in $CASES; do ARGS+=("$C/$c.json"); done
node tools/run-py.mjs "$HERE/upload-ur/acc.py" --base "http://127.0.0.1:$PORT" --store "$W/data" --out "$W/out" "${ARGS[@]}"
echo "cases exit $?"
if [ -z "${WT_ROOMS_NO_RA13:-}" ]; then
  node tools/run-py.mjs "$HERE/rooms/ra13.py" --base "http://127.0.0.1:$PORT" --store "$W/data" --out "$W/out"
  echo "ra13 exit $?"
fi
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force }"
sleep 2; kill $API 2>/dev/null
echo ROOMS-BUILDS-DONE
