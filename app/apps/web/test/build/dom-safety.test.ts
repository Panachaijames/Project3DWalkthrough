// Drawing text in React text nodes only (docs/upload/DESIGN.md U-14.3; ACCEPTANCE 2.3 U6): `dangerouslySetInnerHTML` and
// `innerHTML` appear nowhere in apps/web/src (U7's plan module included: it is part of the web app).
import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const SRC = path.resolve(__dirname, '../../src');

function files(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = path.join(dir, name);
    if (statSync(p).isDirectory()) out.push(...files(p));
    else if (/\.(ts|tsx)$/.test(name)) out.push(p);
  }
  return out;
}

describe('no HTML from strings in apps/web/src', () => {
  it('dangerouslySetInnerHTML, innerHTML, outerHTML and insertAdjacentHTML are not used', () => {
    const all = files(SRC);
    expect(all.length).toBeGreaterThan(40);
    const hits = all.flatMap(f => readFileSync(f, 'utf8').split('\n')
      .map((line, i) => ({ f: path.relative(SRC, f), i: i + 1, line }))
      .filter(x => /dangerouslySetInnerHTML|\binnerHTML\b|\bouterHTML\b|insertAdjacentHTML/.test(x.line)));
    expect(hits).toEqual([]);
  });
});
