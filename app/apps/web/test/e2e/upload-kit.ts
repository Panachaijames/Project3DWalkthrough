// Helpers of tests/e2e/upload.spec.ts (ACCEPTANCE A-7; WORK_BREAKDOWN U6). The same spec runs against the mock API
// (WT_SERVE=web: apps/web/test/mock-api, started by web-kit's useApi) and, at integration, against the real API and worker:
// every request goes through the web origin's /api proxy, and the API's own answers (getBuild, the plan) choose what to
// click, so the spec never depends on the mock's data.
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { expect, type APIRequestContext, type Page } from '@playwright/test';
import type { BuildDetail, BuildSettings, PlanGeometry } from '../../src/upload/contracts';
import { APP_DIR, PROTOTYPES_DIR } from '../mock-api/fixtures';

export const BANK_DWGS = [
  path.join(PROTOTYPES_DIR, 'I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg'),
  path.join(PROTOTYPES_DIR, 'I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg'),
];

/** The build id of the Build page on screen. */
export async function buildIdOf(page: Page): Promise<string> {
  const id = await page.getByTestId('build-page').getAttribute('data-build-id');
  if (!id) throw new Error('no build page');
  return id;
}

export async function getBuild(request: APIRequestContext, projectId: string, buildId: string): Promise<BuildDetail> {
  const r = await request.get(`/api/projects/${projectId}/builds/${buildId}`);
  expect(r.status()).toBe(200);
  return (await r.json()) as BuildDetail;
}

/** PUT the settings with If-Match on the build's revision (U-13.1). */
export async function putBuildSettings(request: APIRequestContext, projectId: string, buildId: string, settings: BuildSettings,
  layersReviewed = true): Promise<BuildDetail> {
  const d = await getBuild(request, projectId, buildId);
  const r = await request.put(`/api/projects/${projectId}/builds/${buildId}/settings`, {
    data: { settings, layersReviewed },
    headers: { 'if-match': `"${d.settingsRevision}"` },
  });
  expect(r.status(), await r.text()).toBe(200);
  return (await r.json()) as BuildDetail;
}

/** A source's plan geometry, as the canvas gets it. */
export async function planOf(request: APIRequestContext, url: string): Promise<PlanGeometry> {
  const r = await request.get(url);
  expect(r.status()).toBe(200);
  return (await r.json()) as PlanGeometry;
}

/** An item to set aside: a drawn entry (not a text or block anchor) on the given layer. */
export function itemOn(plan: PlanGeometry, layer: string): string {
  const li = plan.layers.indexOf(layer);
  const i = plan.items.key.findIndex((_, n) => plan.items.layer[n] === li && plan.items.type[n]! <= 2);
  if (i < 0) throw new Error(`no item on ${layer}`);
  return plan.items.key[i]!;
}

/** An item drawn inside a nested block (key a/b/c, its parent a/b an INSERT anchor): the block pick mode climbs to a/b. */
export function itemInBlock(plan: PlanGeometry): { key: string; anchor: string } {
  const type = new Map(plan.items.key.map((k, n) => [k, plan.items.type[n]!]));
  for (let n = 0; n < plan.items.key.length; n++) {
    const key = plan.items.key[n]!;
    const parts = key.split('/');
    if (parts.length !== 3 || plan.items.type[n] === 5) continue;
    const anchor = parts.slice(0, 2).join('/');
    if (type.get(anchor) === 5) return { key, anchor };
  }
  throw new Error('no item inside a nested block');
}

/** Waits until the settings saver says Saved (nothing waiting, nothing in flight). */
export async function settingsSaved(page: Page): Promise<void> {
  await expect(page.getByTestId('settings-status')).toHaveAttribute('data-status', 'saved', { timeout: 30_000 });
}

/** Waits for a build run newer than `afterRun` (null: any) to end done, and returns the build (its error if not). */
export async function waitForResult(page: Page, request: APIRequestContext, projectId: string, buildId: string, afterRun: string | null): Promise<BuildDetail> {
  let d: BuildDetail | null = null;
  await expect.poll(async () => {
    d = await getBuild(request, projectId, buildId);
    const run = d.run;
    if (!run || run.kind !== 'build' || run.status === 'queued' || run.status === 'running') return 'waiting';
    if (run.status !== 'done') return `${run.status}: ${run.error?.code ?? ''} ${run.error?.message ?? ''}`;
    return d.result && d.result.runId !== afterRun ? 'done' : 'waiting';
  }, { timeout: 8 * 60_000, intervals: [1_000] }).toBe('done');
  await expect(page.getByTestId('build-page')).toBeVisible();
  return d!;
}

/** The synthetic hostile DXF (tools/upload/make-test-dxf.py hostile, the builder Python): ACCEPTANCE A-7's second test. */
export function makeHostileDxf(out: string): string {
  try {
    execFileSync(process.execPath, ['tools/run-builder-py.mjs', 'tools/upload/make-test-dxf.py', 'hostile', out], {
      cwd: APP_DIR, stdio: 'pipe', env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    });
  } catch (err) {
    // no builder Python here (a mock-API run elsewhere): a minimal DXF with the same names is enough for the mock
    const names = ["A-WALL<img src=x onerror=alert(1)>", "A-DOOR</script><script>alert(2)</script>", "I-FURN $' $& &amp"];
    const lines = ['0', 'SECTION', '2', 'HEADER', '9', '$ACADVER', '1', 'AC1032', '0', 'ENDSEC', '0', 'SECTION', '2', 'TABLES', '0', 'TABLE', '2', 'LAYER',
      ...names.flatMap(n => ['0', 'LAYER', '2', n, '70', '0', '62', '7', '6', 'Continuous']), '0', 'ENDTAB', '0', 'ENDSEC', '0', 'EOF'];
    writeFileSync(out, `${lines.join('\r\n')}\r\n`, 'latin1');
    void err;
  }
  return out;
}

/** The version's own .ms with the `upload` profile, generated at test time with the build's date (U-11.5; real API only). */
export function uploadProfileScript(modelFile: string, files: string[], date: string, outDir: string): Buffer {
  const script = path.join(outDir, 'gen_upload_ms.py');
  writeFileSync(script, [
    'import json, sys',
    'from pathlib import Path',
    'from walkthrough_builder.out.maxscript import maxscript',
    'model = Path(sys.argv[1]).read_bytes()',
    "profile = json.loads(Path('fixtures/upload/max-texts/upload.json').read_text(encoding='utf-8'))",
    "out = maxscript(model, profile, files=json.loads(sys.argv[2]), units='mm', date=sys.argv[3])",
    'Path(sys.argv[4]).write_bytes(out)',
  ].join('\n'), 'utf8');
  const out = path.join(outDir, 'expected-upload.ms');
  execFileSync(process.execPath, ['tools/run-builder-py.mjs', script, modelFile, JSON.stringify(files), date, out], { cwd: APP_DIR, stdio: 'pipe' });
  return readFileSync(out);
}
