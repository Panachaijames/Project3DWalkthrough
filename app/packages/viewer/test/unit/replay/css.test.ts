// Builder D: the replay's CSS chunk keeps the rules of DESIGN.md 11.6 (as C's and B's chunks do): every selector starts
// with .wtv, no vh / vw (sizes are % of the root), no size media query (a container query on the root instead), no
// position: fixed, no ids; and it still says what the prototype's said.
import { describe, expect, it } from 'vitest';
import { REPLAY_CSS } from '../../../src/replay/css';

/** Selector lists of every rule, with the @container blocks opened up. */
function rules(css: string): { selectors: string[]; body: string; at: string | null }[] {
  const out: { selectors: string[]; body: string; at: string | null }[] = [];
  let rest = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const atRe = /@([a-z-]+)[^{]*\{((?:[^{}]*\{[^{}]*\})*)\s*\}/g;
  for (const m of rest.matchAll(atRe)) {
    for (const r of m[2]!.matchAll(/([^{}]+)\{([^{}]*)\}/g)) out.push({ selectors: r[1]!.split(',').map(s => s.trim()), body: r[2]!, at: m[0].slice(0, m[0].indexOf('{')).trim() });
  }
  rest = rest.replace(atRe, '');
  for (const r of rest.matchAll(/([^{}]+)\{([^{}]*)\}/g)) out.push({ selectors: r[1]!.split(',').map(s => s.trim()), body: r[2]!, at: null });
  return out;
}

describe('REPLAY_CSS (DESIGN.md 11.6)', () => {
  const all = rules(REPLAY_CSS);

  it('scopes every selector under .wtv', () => {
    expect(all.length).toBeGreaterThan(30);
    for (const r of all) for (const s of r.selectors) expect(s).toMatch(/^\.wtv[\s[]/);
  });

  it('has no vh / vw, no media query, no fixed positions and no ids; the narrow layout is a container query on the root', () => {
    expect(REPLAY_CSS).not.toMatch(/\d(vh|vw|vmin|dvh|svh|lvh)\b/);
    expect(REPLAY_CSS).not.toMatch(/@media/);
    expect(REPLAY_CSS).not.toMatch(/position:\s*fixed/);
    for (const r of all) for (const s of r.selectors) expect(s).not.toMatch(/#/);
    const at = [...new Set(all.map(r => r.at).filter(Boolean))];
    expect(at).toEqual(['@container wtv (max-width: 700px)']);
    expect(all.filter(r => r.at).flatMap(r => r.selectors)).toEqual([
      '.wtv [data-wt=replay-card]', '.wtv [data-wt=replay-steps]', '.wtv [data-wt=replay-steps] li', '.wtv [data-wt=replay-caption]',
    ]);
  });

  it('keeps the prototype values, root-relative', () => {
    const body = (sel: string, at: string | null = null) => all.find(r => r.at === at && r.selectors.includes(sel))?.body ?? '';
    expect(body('.wtv [data-wt=replay-card]')).toContain('position:absolute;top:12px;left:12px;width:min(330px,calc(100% - 48px));max-height:calc(100% - 110px)');
    expect(body('.wtv [data-wt=replay-card]')).toContain('z-index:8;display:none');
    expect(body('.wtv [data-wt=replay-caption]')).toContain('width:min(680px,calc(100% - 24px));box-sizing:border-box');
    expect(body('.wtv [data-wt=replay-card]', '@container wtv (max-width: 700px)')).toBe('width:auto;right:12px;max-height:46%');
    expect(body('.wtv[data-replay] [data-wt=hint]')).toBe('display:none');
    expect(body('.wtv[data-replay] [data-wt=panel]')).toBe('display:none');
    expect(body('.wtv [data-wt=replay-steps] li[data-state=now] i')).toBe('border-color:var(--accent);background:var(--accent)');
    expect(body('.wtv [data-wt=replay-card] button[data-wt=replay-go]')).toContain('position:sticky;bottom:0');
  });
});
