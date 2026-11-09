// UR, V1-4 (docs/upload/contract-issues/UR.md): the unit tests' hand-made store lives in <WT_TMP>/unit-store, never in
// <WT_TMP>/data, the folder the upload milestone gives to the API (WALKTHROUGH_DATA_DIR=<WT_TMP>\data): a `test:unit` run
// replaced a served acceptance store there. No unit test source may name <WT_TMP>/data again.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { expect, it } from 'vitest';
import { APP, TMP, UNIT_STORE } from './store';

function sources(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = path.join(dir, name);
    if (statSync(p).isDirectory()) out.push(...sources(p));
    else if (/\.(ts|tsx|mts|mjs)$/.test(name)) out.push(p);
  }
  return out;
}

it('the unit store is <WT_TMP>/unit-store, not the API\'s <WT_TMP>/data', () => {
  expect(path.resolve(UNIT_STORE)).toBe(path.resolve(TMP, 'unit-store'));
  expect(path.resolve(UNIT_STORE)).not.toBe(path.resolve(TMP, 'data'));
});

it('no unit test writes into <WT_TMP>/data', () => {
  const roots = [path.join(APP, 'packages', 'viewer', 'test', 'unit'), path.join(APP, 'apps', 'web', 'test')];
  const offenders = roots.flatMap(sources).filter(f => /join\(\s*(TMP|process\.env\.WT_TMP[^,]*)\s*,\s*'data'\s*\)/.test(readFileSync(f, 'utf8')));
  expect(offenders).toEqual([]);
});
