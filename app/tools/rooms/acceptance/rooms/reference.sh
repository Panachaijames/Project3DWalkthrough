#!/bin/bash
# RI (rooms milestone), step `reference-checks` (RA-2, RA-16): every saved version of app/data as at the milestone's
# start (docs/rooms/reference/versions.sha1), every file outside app/ as listed (outside.txt), no new __pycache__; and
# the upload acceptance store's copy (R0's, read only) against acc-9nov.versions.sha1.
set -u
APP="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$APP" || exit 9
rc=0
node tools/rooms/reference.mjs versions --check || rc=1
node tools/rooms/reference.mjs outside --check || rc=1
node tools/rooms/reference.mjs store "$TEMP/wt-r0/acc-9nov" --check docs/rooms/reference/acc-9nov.versions.sha1 || rc=1
# the acceptance store the new steps built into (a copy of it): the eight old versions are still as on 9 Nov
[ -n "${WT_TMP:-}" ] && [ -d "$WT_TMP/data/projects" ] && { node tools/rooms/reference.mjs store "$WT_TMP/data" --check docs/rooms/reference/acc-9nov.versions.sha1 || rc=1; }
exit $rc
