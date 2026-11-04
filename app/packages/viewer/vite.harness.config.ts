// The browser harness (DESIGN.md 2, 17.4): serves packages/viewer/test/harness/** on 127.0.0.1. Each builder passes its
// own port: `npm run harness -- --port 5721`. Pages may import anything under app/ (fixtures, src). Frozen after the scaffold.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

const slash = (p: string) => p.replaceAll('\\', '/');
const here = slash(path.dirname(fileURLToPath(import.meta.url)));
const appRoot = slash(path.resolve(here, '../..'));

export default defineConfig({
  root: `${here}/test/harness`,
  cacheDir: process.env.WT_TMP ? slash(path.join(process.env.WT_TMP, 'vite-harness')) : undefined,
  server: { host: '127.0.0.1', strictPort: true, fs: { allow: [appRoot] } },
  preview: { host: '127.0.0.1', strictPort: true },
});
