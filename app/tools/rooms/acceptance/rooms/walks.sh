#!/bin/bash
# RI (rooms milestone), step `rooms-walks`, in Edge (one at a time through the Edge lock; nothing served):
#   * upload-walk.spec.ts on the new-rule offline files with WT_ROOMS_PROBES=1: RA-6's probes found again by floor and
#     sheet point (floor 0.4 - 0.9 m in front; the walk from there), the walls, doors and glass checks (RA-6's bank row);
#     reports in <WT_TMP>/e2e-rooms/upload-walk/;
#   * stairs.spec.ts on the same files (RA-8's ceilings, RA-10's climbs) with WT_FPS_GPU=1 (RA-14: the frame rate with the
#     laptop's GPU, `fpsGpu` in <WT_TMP>/e2e-rooms/stairs/<file>.json); the suites have no stair to climb.
set -u
APP="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$APP" || exit 9
: "${WT_TMP:?WT_TMP must be set (run.mjs sets it)}"
W="$WT_TMP"
E="$W/e2e-rooms"
rm -rf "$E"; mkdir -p "$E"
export WT_WEB_PORT="${WT_WEB_PORT:-5748}" WT_API_PORT="${WT_API_PORT:-8748}" WT_SERVE=none WT_SKIP_STORE_CHECK=1 PYTHONIOENCODING=utf-8
SHOULD="house-rooms,suite-rooms,tower-rooms,suite-revit-rooms,tower-aside,suite-revit-aside"
t0=$(date +%s)
WT_TMP="$E" WT_ROOMS_PROBES=1 WT_UPLOAD_OFFLINE_DIR="$W/offline-rooms" WT_UPLOAD_DATA_DIR="$W/data" \
  WT_UPLOAD_WALK_SHOULD="$SHOULD" \
  npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/upload-walk.spec.ts > "$W/logs/rooms-upload-walk.txt" 2>&1
rc1=$?
echo "upload-walk exit $rc1 ($(( $(date +%s) - t0 )) s): $(grep -E '[0-9]+ (passed|failed|flaky|skipped)' "$W/logs/rooms-upload-walk.txt" | tail -4 | tr '\n' ' ')"
t0=$(date +%s)
WT_TMP="$E" WT_ROOMS_OFFLINE_DIR="$W/offline-rooms" WT_FPS_GPU=1 \
  WT_ROOMS_NO_STAIRS="suite-rooms-v1,suite-revit-rooms-v1,suite-revit-aside-v1" \
  npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/stairs.spec.ts > "$W/logs/rooms-stairs.txt" 2>&1
rc2=$?
echo "stairs exit $rc2 ($(( $(date +%s) - t0 )) s): $(grep -E '[0-9]+ (passed|failed|flaky|skipped)' "$W/logs/rooms-stairs.txt" | tail -4 | tr '\n' ' ')"
[ $rc1 -eq 0 ] && [ $rc2 -eq 0 ]
