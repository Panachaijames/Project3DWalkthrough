#!/bin/bash
# Final check (UF): `npm run dev` as the owner starts it (API 8710 with --reload, web 5710), on a fresh copy of app/data
# (the owner's store, never touched) and a cache under %TEMP%\wt-uf\dev (never the default cache). Runs until stopped.
cd "/c/Users/DWP2/Desktop/Project walkthrough/app" || exit 9
W="$TEMP/wt-uf"
rm -rf "$W/dev/data" "$W/dev/cache"; mkdir -p "$W/dev"
cp -a data "$W/dev/data"
export WALKTHROUGH_DATA_DIR="$W/dev/data" WALKTHROUGH_CACHE_DIR="$W/dev/cache" WT_TMP="$W/dev" PYTHONIOENCODING=utf-8
exec npm run dev
