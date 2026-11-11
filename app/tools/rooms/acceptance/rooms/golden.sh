#!/bin/bash
# RI (rooms milestone), step `rooms-golden`: WT_ACCEPTANCE=1 runs the builder tests marked `acceptance`: RA-15 (each
# new-rule build in two child processes, the pinned references: test_r_rooms_golden.py) and RA-18 (every door of the bank
# and the house undone in turn: test_r1_drawings.py), with the rest of test_r_rooms_golden.py.
set -u
APP="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$APP" || exit 9
: "${WT_TMP:?WT_TMP must be set (run.mjs sets it)}"
G="$WT_TMP/golden"
mkdir -p "$G"
export WT_TMP="$G" WALKTHROUGH_DATA_DIR="$G/data" WALKTHROUGH_CACHE_DIR="$G/cache" PYTHONIOENCODING=utf-8 WT_ACCEPTANCE=1
export WT_REF="${WT_REF:-$TEMP/wt-u0/ref}"
node tools/run-builder-py.mjs -m pytest services/builder/tests/test_r_rooms_golden.py \
  "services/builder/tests/test_r1_drawings.py::test_ra18_each_door_undone_in_turn" -q -rA --durations=12
