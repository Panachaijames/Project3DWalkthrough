// Builder B: the modes CSS chunk follows D-11.6 (as C tests its chunks): every selector under .wtv, no vh / vw (the
// photo frame's 100vmax shade is the one exception), no width / height media query (container queries on `wtv` with the
// prototype's numbers instead), no position: fixed, and every rule of viewer_modes.js's <style> is there.
import { describe, expect, it } from 'vitest';
import { MODES_CSS } from '../../../src/modes/css';

const css = MODES_CSS.replace(/\/\*[\s\S]*?\*\//g, '');
/** Every selector list of a rule (outside the at-rule headers). */
function selectors(text: string): string[] {
  const out: string[] = [];
  for (const m of text.matchAll(/([^{}@]+)\{[^{}]*\}/g)) for (const sel of m[1]!.split(',')) out.push(sel.trim());
  return out.filter(Boolean);
}

describe('MODES_CSS', () => {
  it('scopes every selector under .wtv', () => {
    const sels = selectors(css);
    expect(sels.length).toBeGreaterThan(40);
    for (const sel of sels) expect(sel, sel).toMatch(/^\.wtv(\[|\s|$)/);
  });

  it('has no vh / vw units and only the frame shade in vmax', () => {
    expect(css).not.toMatch(/\d(vh|vw|vmin|dvh|svh|lvh|dvw|svw|lvw)\b/);
    expect(css.match(/vmax/g)).toEqual(['vmax']);
    expect(css).toContain('box-shadow: 0 0 0 100vmax #0e121666');
  });

  it('has no size media queries: the same numbers as container queries on the root (container wtv)', () => {
    expect(css).not.toMatch(/@media/);
    const queries = [...css.matchAll(/@container\s+([^{]+)\{/g)].map(m => m[1]!.trim());
    expect(queries).toEqual(['wtv (max-width: 700px) or (max-height: 500px)', 'wtv (max-width: 700px)', 'wtv (min-width: 701px)']);
  });

  it('puts every overlay absolute in the root, never fixed', () => {
    expect(css).not.toMatch(/position:\s*fixed/);
    for (const wt of ['hud', 'cross', 'camera-panel', 'frame', 'flash', 'stick', 'updown']) {
      expect(css, wt).toMatch(new RegExp(`\\.wtv \\[data-wt=${wt}\\] \\{ position: absolute;`));
    }
  });

  it('keeps the prototype sizes, made root-relative', () => {
    expect(css).toContain('max-width: calc(100% - 24px)');                               // HUD
    expect(css).toContain('width: min(270px, calc(100% - 48px)); max-height: calc(100% - 60px)');   // Camera panel
    expect(css).toContain('.wtv[data-fp] [data-wt=camera-panel] { top: 58px; max-height: calc(100% - 70px) }');
    expect(css).toContain('.wtv[data-touchui] [data-wt=camera-panel] { max-height: calc(100% - 270px); min-height: 110px }');
    expect(css).toContain('width: auto; max-height: 42%; padding: 8px 12px');           // narrow: 42vh -> 42 %
    expect(css).toContain('width: 116px; height: 116px');                               // the stick
    expect(css).toContain('.wtv[data-crowded] [data-wt=panel] { display: none }');
    expect(css).toContain('.wtv [data-wt=snap] { background: var(--accent) !important; border-color: #fff !important }');
    expect(css).toContain('.wtv [data-wt=panel], .wtv [data-wt=hint] { z-index: 6 }');
  });

  it('every prototype id has its data-wt selector', () => {
    for (const wt of ['hud', 'cross', 'camera-panel', 'shot', 'photos', 'frame', 'flash', 'stick', 'updown', 'snap']) expect(css).toContain(`[data-wt=${wt}]`);
    for (const flag of ['fp', 'camopen', 'crowded', 'touchui']) expect(css).toContain(`.wtv[data-${flag}]`);
    for (const cls of ['vm-label', 'vm-row', 'vm-narrow', 'vm-more', 'vm-f', 'vm-note', 'vm-crop', 'vm-off']) expect(css).toContain(`.${cls}`);
  });
});
