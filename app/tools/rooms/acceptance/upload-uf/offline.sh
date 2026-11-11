#!/bin/bash
# Final check (UF): the offline file of every version the acceptance run saved (A-6 walks them from disk).
cd "/c/Users/DWP2/Desktop/Project walkthrough/app" || exit 9
W="$TEMP/wt-uf"
rm -rf "$W/offline"; mkdir -p "$W/offline"
for pv in bank-reupload:1 bank-sampeng:3 house-upload:1 suite-upload:1 suite-outlines:1 tower-upload:1 suite-revit:1 presidential-suite:2; do
  p=${pv%%:*}; v=${pv##*:}
  node packages/viewer/scripts/make-offline.mjs --data "$W/acc/data" --template dist/offline-template/viewer-template.html \
    --out "$W/offline" --project "$p" --version "$v" 2>&1 | tail -1
done
ls -la "$W/offline"
