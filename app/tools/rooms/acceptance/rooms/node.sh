#!/bin/bash
# RI (rooms milestone), step `rooms-node`: RA-10's Node part on the real new-rule models (R4's climb.test.ts, defined only
# with WT_ROOMS_MODELS) and RA-14's Node times (WT_R4_TIMING=1: the first view, a move on the stair), from the models
# `rooms-builds` saved. Results: <WT_TMP>/node-rooms/real-climb-<name>.json, real-timing-<name>.json.
set -u
APP="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$APP" || exit 9
: "${WT_TMP:?WT_TMP must be set (run.mjs sets it)}"
W="$WT_TMP"
N="$W/node-rooms"
rm -rf "$N"; mkdir -p "$N/models"
for x in bank:bank-rooms house:house-rooms tower:tower-rooms; do
  cp "$W/data/projects/${x#*:}/versions/1/model.json" "$N/models/${x%%:*}.model.json" || exit 3
done
WT_TMP="$N" WT_ROOMS_MODELS="$N/models" WT_ROOMS_NAMES=house,bank,tower WT_R4_TIMING=1 \
  npx vitest run --project viewer packages/viewer/test/unit/modes/climb.test.ts -t "real new-rule"
