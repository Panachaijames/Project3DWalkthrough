// Builder C: the CSS rules of DESIGN.md 11.6 / 17.2 ui for C's chunks (BASE_CSS, the furniture chunk): the host's reset undone
// first, every selector under .wtv, no vh / vw and no size media query, the panel, legend and furniture rules ported.
import { describe, expect, it } from 'vitest';
import { FURNITURE_CSS } from '../../../src/furniture/css';
import { BASE_CSS } from '../../../src/ui/css';

/** Top-level selector lists of a chunk (inside @container blocks too), with comments taken out. */
function selectors(css: string): string[] {
  const out: string[] = [];
  const text = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const re = /([^{}]+)\{/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    const s = m[1]!.trim();
    if (s.startsWith('@')) continue;
    out.push(...s.split(',').map(x => x.trim()));
  }
  return out;
}

describe('BASE_CSS and the furniture chunk', () => {
  it("BASE_CSS starts with D-11.6's all: revert rule, then the root rule", () => {
    expect(BASE_CSS.startsWith('.wtv, .wtv *, .wtv *::before, .wtv *::after { all: revert; }')).toBe(true);
    const rest = BASE_CSS.slice(BASE_CSS.indexOf('}') + 1).trimStart();
    expect(rest.startsWith('.wtv {')).toBe(true);
    for (const v of ['--bg: #eef0f2', '--panel: #ffffffee', '--ink: #1d2329', '--muted: #5b6670', '--line: #d5dade', 'container: wtv / size',
      'position: relative', 'overflow: hidden', 'font: 14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif']) expect(rest.split('}')[0]).toContain(v);
  });

  for (const [name, css] of [['BASE_CSS', BASE_CSS], ['FURNITURE_CSS', FURNITURE_CSS]] as const) {
    it(`${name}: every selector starts with .wtv`, () => {
      const sel = selectors(css);
      expect(sel.length).toBeGreaterThan(5);
      for (const s of sel) expect(s, s).toMatch(/^\.wtv[\s.[:,>]|^\.wtv$/);
    });
    it(`${name}: no vh / vw, no size media query, no position: fixed`, () => {
      expect(css).not.toMatch(/\d(vh|vw|vmin|dvh|svh|lvh)\b/);
      expect(css).not.toMatch(/\b100vmax\b/);
      expect(css).not.toMatch(/@media/);
      expect(css).not.toMatch(/position:\s*fixed/);
    });
  }

  it("the side panel: absolute, 12 / 12, min(330px, calc(100% - 48px)), content-box (revert), max-height 100% - 60px or - 90px with furniture", () => {
    expect(BASE_CSS).toMatch(/\.wtv \.wtv-panel \{ position: absolute; top: 12px; left: 12px; width: min\(330px, calc\(100% - 48px\)\); max-height: calc\(100% - 60px\);/);
    expect(BASE_CSS).toContain('.wtv .wtv-panel[data-furniture] { max-height: calc(100% - 90px); }');
    expect(BASE_CSS).toMatch(/padding: 12px 14px;/);
    expect(BASE_CSS).not.toMatch(/\.wtv-panel[^}]*box-sizing/);
  });

  it('the legend: inline (line-height 1.9, swatch margin 0 4px 0 8px, the first 0) and lines (1.45, a 16 px hanging indent)', () => {
    expect(BASE_CSS).toContain('.wtv [data-wt=legend] { font-size: 12.5px; line-height: 1.9; margin-top: 8px; }');
    expect(BASE_CSS).toContain('margin: 0 4px 0 8px');
    expect(BASE_CSS).toContain('.wtv [data-wt=legend] > span:first-child { margin-left: 0; }');
    expect(BASE_CSS).toContain('.wtv [data-wt=legend][data-layout=lines] { line-height: 1.45; }');
    expect(BASE_CSS).toContain('padding-left: 16px; text-indent: -16px;');
  });

  it('active buttons by aria-pressed, the hint and the error box absolute in the root, the panel hidden by the root flags', () => {
    expect(BASE_CSS).toContain('.wtv button[aria-pressed=true] { background: var(--accent); border-color: var(--accent); color: #fff; }');
    expect(BASE_CSS).toMatch(/\.wtv \[data-wt=hint\] \{ position: absolute; bottom: 10px; left: 12px; right: 12px;/);
    expect(BASE_CSS).toContain('.wtv [data-wt=error][hidden] { display: none; }');
    expect(BASE_CSS).toContain('.wtv[data-crowded] .wtv-panel { display: none; }');
    expect(BASE_CSS).toContain('.wtv[data-replay] .wtv-panel, .wtv[data-replay] [data-wt=hint] { display: none; }');
    expect(BASE_CSS).toMatch(/@container wtv \(max-width: 700px\) or \(max-height: 500px\)/);
  });

  it('the furniture chunk keeps the pages\' border-box rules (.fb-sw, .fb-h) and puts the label absolute in the root', () => {
    expect(FURNITURE_CSS).toMatch(/\[data-wt=kind-swatch\] \{[^}]*box-sizing: border-box/);
    expect(FURNITURE_CSS).toMatch(/\[data-wt=kind-height\] \{[^}]*box-sizing: border-box/);
    expect(FURNITURE_CSS).toMatch(/\[data-wt=furniture-tip\] \{ position: absolute;[^}]*max-width: min\(340px, calc\(100% - 24px\)\)/);
    expect(FURNITURE_CSS).toContain('grid-template-columns: 16px 12px minmax(0, 1fr) 52px 38px');
  });
});
