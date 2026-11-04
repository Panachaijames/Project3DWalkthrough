// vitest for both workspaces (DESIGN.md 2, 17.2; WORK_BREAKDOWN S.1). Frozen after the scaffold.
// * viewer: Node by default; a DOM test starts with the docblock `// @vitest-environment happy-dom`.
// * web: happy-dom, the React plugin, the `@` alias, and (VITE_FAKE_VIEWER=1) the same fake-viewer alias as the web
//   app's vite.config.ts.
// `npm run test:unit` runs both; `npx vitest run --project viewer` (or web) runs one.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import type { Alias } from 'vite';
import { defineConfig } from 'vitest/config';

const slash = (p: string) => p.replaceAll('\\', '/');
const here = slash(path.dirname(fileURLToPath(import.meta.url)));
const web = `${here}/apps/web`;

const webAlias: Alias[] = [{ find: /^@\//, replacement: `${web}/src/` }];
if (process.env.VITE_FAKE_VIEWER === '1') {
  webAlias.unshift({ find: /^@walkthrough\/viewer$/, replacement: `${web}/test/fake-viewer.ts` });
}

export default defineConfig({
  cacheDir: process.env.WT_TMP ? slash(path.join(process.env.WT_TMP, 'vite-vitest')) : undefined,
  test: {
    projects: [
      {
        extends: false,
        root: `${here}/packages/viewer`,
        test: {
          name: 'viewer',
          environment: 'node',
          include: ['test/**/*.test.ts'],
        },
      },
      {
        extends: false,
        root: web,
        plugins: [react()],
        resolve: { alias: webAlias },
        test: {
          name: 'web',
          environment: 'happy-dom',
          include: ['test/**/*.test.{ts,tsx}', 'src/**/*.test.{ts,tsx}'],
        },
      },
    ],
  },
});
