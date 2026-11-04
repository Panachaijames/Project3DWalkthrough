// apps/web Vite config (DESIGN.md 2, 3, 15; WORK_BREAKDOWN S.6). Frozen after the scaffold.
// * Binds 127.0.0.1 only: on this machine Vite's default `localhost` listens on [::1] only (DESIGN.md 3).
// * /api is proxied to the API on 127.0.0.1:$WT_API_PORT (default 8710), for `vite` and `vite preview` alike.
// * VITE_FAKE_VIEWER=1 aliases @walkthrough/viewer to test/fake-viewer.ts (builder F's page-flow tests).
// * WT_TMP set: the dependency cache goes under it, so parallel runs never share one.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, type Alias } from 'vite';

const slash = (p: string) => p.replaceAll('\\', '/');
const here = slash(path.dirname(fileURLToPath(import.meta.url)));
const appRoot = slash(path.resolve(here, '../..'));
const apiTarget = `http://127.0.0.1:${process.env.WT_API_PORT ?? '8710'}`;
const proxy = { '/api': { target: apiTarget, changeOrigin: false } };

const alias: Alias[] = [{ find: /^@\//, replacement: `${here}/src/` }];
if (process.env.VITE_FAKE_VIEWER === '1') {
  alias.unshift({ find: /^@walkthrough\/viewer$/, replacement: `${here}/test/fake-viewer.ts` });
}

export default defineConfig({
  root: here,
  plugins: [react(), tailwindcss()],
  resolve: { alias },
  server: { host: '127.0.0.1', port: 5710, strictPort: true, proxy, fs: { allow: [appRoot] } },
  preview: { host: '127.0.0.1', port: 4710, strictPort: true, proxy },
  cacheDir: process.env.WT_TMP ? slash(path.join(process.env.WT_TMP, 'vite-web')) : undefined,
  build: { outDir: `${appRoot}/dist/web`, emptyOutDir: true },
});
