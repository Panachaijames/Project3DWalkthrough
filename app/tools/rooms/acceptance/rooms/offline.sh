#!/bin/bash
# RI (rooms milestone), step `rooms-offline`: the offline file of every new-rule version that `rooms-builds` saved
# (<WT_TMP>/data, version 1 of each project), made with the build's viewer template (dist/offline-template, written by
# `npm run build`; WT_OFFLINE_TEMPLATE to use another) into <WT_TMP>/offline-rooms.
set -u
APP="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$APP" || exit 9
: "${WT_TMP:?WT_TMP must be set (run.mjs sets it)}"
W="$WT_TMP"
T="${WT_OFFLINE_TEMPLATE:-dist/offline-template/viewer-template.html}"
[ -f "$T" ] || { echo "no viewer template at $T: run npm run build (or set WT_OFFLINE_TEMPLATE)"; exit 3; }
rm -rf "$W/offline-rooms"; mkdir -p "$W/offline-rooms"
rc=0
for p in ${WT_ROOMS_PROJECTS:-bank-rooms house-rooms suite-rooms tower-rooms suite-revit-rooms tower-aside suite-revit-aside}; do
  node packages/viewer/scripts/make-offline.mjs --data "$W/data" --template "$T" --out "$W/offline-rooms" \
    --project "$p" --version 1 2>&1 | tail -1 || rc=1
done
ls -la "$W/offline-rooms"
exit $rc
