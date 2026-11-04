// The environment variables the web app reads (Vite exposes only VITE_* names to the page).
interface ImportMetaEnv {
  /** Base URL of the API; default '' (the same origin, through the /api proxy). */
  readonly VITE_API_BASE?: string;
  /** '1': the viewer exposes its test hook (Playwright's web server sets it; DESIGN.md 11.7). */
  readonly VITE_WTV_TEST_HOOK?: string;
  /** '1': @walkthrough/viewer is aliased to test/fake-viewer.ts (set in the environment of vite / vitest). */
  readonly VITE_FAKE_VIEWER?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
