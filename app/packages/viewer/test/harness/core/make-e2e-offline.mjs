#!/usr/bin/env node
// Builder A: offline files for the app-target e2e checks before the seed exists (tests/e2e/structure.spec.ts,
// offline.spec.ts, leak.spec.ts with WT_OFFLINE_DIR / WT_DATA_DIR). Writes the hand-made store of
// test/unit/core/store.ts writeE2eStore into <WT_TMP>/e2e-data (the five versions of tests/e2e/lib/target.ts and the
// hostile one) and runs scripts/make-offline.mjs on it with a template built into <WT_TMP>/offline-template:
//   npx vite build -c packages/viewer/vite.offline.config.ts --outDir "$TEMP/wt-a/offline-template"
//   WT_TMP="$TEMP/wt-a" node packages/viewer/test/harness/core/make-e2e-offline.mjs
// Then, e.g.: E2E_TARGET=app WT_SERVE= WT_SKIP_STORE_CHECK=1 WT_OFFLINE_DIR="$TEMP/wt-a/offline" WT_DATA_DIR="$TEMP/wt-a/e2e-data"
//   WT_WEB_PORT=5721 WT_TMP="$TEMP/wt-a" npx playwright test -c tests/e2e/playwright.config.ts --project=e2e tests/e2e/structure.spec.ts
// Node 24 strips the types of store.ts itself (no build step). Nothing is written outside WT_TMP.
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TMP = process.env.WT_TMP ?? path.join(os.tmpdir(), 'wt-a');
const { writeE2eStore } = await import(pathToFileURL(path.join(HERE, '../../unit/core/store.ts')).href);
const { makeOffline } = await import(pathToFileURL(path.join(HERE, '../../../scripts/make-offline.mjs')).href);

const store = writeE2eStore(path.join(TMP, 'e2e-data'));
const written = makeOffline({ data: store.root, template: path.join(TMP, 'offline-template', 'viewer-template.html'), out: path.join(TMP, 'offline') });
for (const w of written) console.log(`${path.basename(w.file)}  ${Math.round(w.bytes / 1024)} KB  (model data ${w.stamp})`);
console.log(`store: ${store.root}`);
