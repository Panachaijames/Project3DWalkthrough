// Playwright globalTeardown: cancels every open run of the API the config started (docs/upload/DESIGN.md U-3.4: a worker
// never outlives its e2e run), then releases the machine-wide Edge lock taken by global-setup.ts (same process).
// The API's address comes from playwright.config.ts (WT_E2E_API, set only when it starts the API). Every failure here is
// reported and swallowed: the lock is always released.
import { release } from '../../tools/edge-lock.mjs';

type Json = Record<string, unknown>;

async function getJson(url: string): Promise<Json | null> {
  const r = await fetch(url, { signal: AbortSignal.timeout(10_000) });
  return r.ok ? ((await r.json()) as Json) : null;
}

/** POSTs `{}` to the cancel URL of every build whose run is queued or running; returns how many it asked. */
export async function cancelOpenRuns(api: string): Promise<number> {
  const list = await getJson(`${api}/api/projects`);
  let asked = 0;
  for (const p of (list?.projects as { id: string }[] | undefined) ?? []) {
    const builds = await getJson(`${api}/api/projects/${encodeURIComponent(p.id)}/builds`).catch(() => null);
    for (const b of (builds?.builds as { runStatus: string | null; url: string }[] | undefined) ?? []) {
      if (b.runStatus !== 'queued' && b.runStatus !== 'running') continue;
      const detail = await getJson(`${api}${b.url}?withSettings=false`).catch(() => null);
      const cancel = (detail?.urls as { cancel?: string } | undefined)?.cancel;
      if (!cancel) continue;
      await fetch(`${api}${cancel}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{}',
                                       signal: AbortSignal.timeout(10_000) }).catch(() => undefined);
      asked++;
    }
  }
  return asked;
}

export default async function globalTeardown(): Promise<void> {
  try {
    const api = process.env.WT_E2E_API;
    if (api) {
      const n = await cancelOpenRuns(api);
      if (n) console.log(`global-teardown: asked ${n} open run(s) to stop`);
    }
  } catch (err) {
    console.warn(`global-teardown: could not cancel open runs: ${err instanceof Error ? err.message : String(err)}`);
  } finally {
    release();
  }
}
