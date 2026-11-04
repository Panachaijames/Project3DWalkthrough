// The offline template build (DESIGN.md 16): packages/viewer/offline/viewer-template.html -> exactly
// app/dist/offline-template/viewer-template.html, one file (vite-plugin-singlefile): three, three-mesh-bvh, the viewer and
// its CSS inlined, nothing fetched. `root` and `outDir` are absolute: with the root left at app/, Vite would keep the
// input's folders under outDir. Run from app/: `npm run build:offline:template`. Frozen after the scaffold.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';

const slash = (p: string) => p.replaceAll('\\', '/');
const here = slash(path.dirname(fileURLToPath(import.meta.url)));
const appRoot = slash(path.resolve(here, '../..'));

export default defineConfig({
  root: `${here}/offline`,
  base: './',
  plugins: [viteSingleFile()],
  cacheDir: process.env.WT_TMP ? slash(path.join(process.env.WT_TMP, 'vite-offline')) : undefined,
  server: { host: '127.0.0.1' },
  preview: { host: '127.0.0.1' },
  build: {
    outDir: `${appRoot}/dist/offline-template`,
    emptyOutDir: true,
    rolldownOptions: { input: `${here}/offline/viewer-template.html` },
  },
});
