// U7 (docs/upload/DESIGN.md U-11.6, ACCEPTANCE 2.3 U7): the family list's formula guard. In the text columns (id, level,
// kind, kind_label, family, block, layer, dxf_handle, on_top_of, note) a value starting with =, +, -, @, TAB or CR gets a
// leading ' before the RFC 4180 quoting; the number columns never change; the four seeded CSVs (the goldens) do not
// change. The same rule as the API's furniture_csv.py (U5).
import { describe, expect, it } from 'vitest';
import type { BuiltModel, FurnitureKind, FurniturePiece } from '../../../src/contracts';
import { CSV_COLUMNS, furnitureCsv } from '../../../src/furniture/logic';
import { BOM, FURNISHED, csvFile, loadModel, loadVariant, typedHeights } from './util';

/** A minimal RFC 4180 reader (quoted fields with doubled quotes, CR / LF inside quotes), to read the rows back. */
function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [], field = '', i = 0, quoted = false;
  while (i < text.length) {
    const c = text[i]!;
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i += 2; continue; }
      if (c === '"') { quoted = false; i++; continue; }
      field += c; i++; continue;
    }
    if (c === '"' && field === '') { quoted = true; i++; continue; }
    if (c === ',') { row.push(field); field = ''; i++; continue; }
    if (c === '\r' && text[i + 1] === '\n') { row.push(field); rows.push(row); row = []; field = ''; i += 2; continue; }
    field += c; i++;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return rows;
}

type Column = (typeof CSV_COLUMNS)[number];
const TEXT_COLUMNS: Column[] = ['id', 'level', 'kind', 'kind_label', 'family', 'block', 'layer', 'dxf_handle', 'on_top_of', 'note'];
const NUMBER_COLUMNS: Column[] = ['x_m', 'y_m', 'width_mm', 'depth_mm', 'height_mm', 'base_mm', 'rotation_deg', 'merged'];
const col = (name: Column) => CSV_COLUMNS.indexOf(name);

/** The hostile corpus: [value, what the CSV holds]. Each of the six first characters is guarded; the rest are controls. */
const HOSTILE: [string, string][] = [
  ['=1+2', "'=1+2"],
  ['+SUM(A1:A9)', "'+SUM(A1:A9)"],
  ['-2+3', "'-2+3"],
  ['@cmd', "'@cmd"],
  ['\tTAB first', "'\tTAB first"],
  ['\rCR first', "'\rCR first"],
  ['=HYPERLINK("http://example.invalid","click")', `'=HYPERLINK("http://example.invalid","click")`],
  ["=cmd|' /C calc'!A0", "'=cmd|' /C calc'!A0"],
  ["'already quoted", "'already quoted"],
  [' =space first', ' =space first'],
  ['a=b', 'a=b'],
  ['\nLF first', '\nLF first'],
  ['เก้าอี้ -1', 'เก้าอี้ -1'],
  ['<img src=x onerror=alert(1)>', '<img src=x onerror=alert(1)>'],
];

/** One floor, one kind, two pieces (the second on the first), every text field = `value` (+ a suffix for the ids); the
 *  numbers negative (they never get a quote). */
function hostileModel(value: string): BuiltModel {
  const base = loadVariant('mini-original.json');
  const kinds: FurnitureKind[] = [
    { key: value, label: value, colour: '#888888', height: 750, base: 0, onTop: false, support: true, blocks: true, count: 2 },
  ];
  const support: FurniturePiece = {
    id: `${value}#1`, floor: value, kind: value, family: value, block: value, layer: value, handle: value, x: -1.25, y: -2.5,
    w: 0.6, d: 0.6, rot: -12.25, on: null, approach: [], n: 1, note: value,
  };
  const top: FurniturePiece = { ...support, id: `${value}#2`, on: support.id, x: -0.0004, y: -3, rot: 0 };
  return { ...base, offset: [-10, -20], floors: [{ ...base.floors[0]!, key: value }], furnitureKinds: kinds, furniture: [support, top] };
}

describe('the CSV formula guard (U-11.6)', () => {
  for (const [value, want] of HOSTILE) {
    it(`a text field ${JSON.stringify(value)} is written ${JSON.stringify(want)} in every text column; numbers unchanged`, () => {
      const rows = parseCsv(furnitureCsv(hostileModel(value), {}));
      expect(rows[0]).toEqual([...CSV_COLUMNS]);
      expect(rows.length).toBe(3);
      const [support, top] = [rows[1]!, rows[2]!];
      for (const c of ['level', 'kind', 'kind_label', 'family', 'block', 'layer', 'dxf_handle', 'note'] as Column[]) {
        expect(support[col(c)], c).toBe(want);
        expect(top[col(c)], c).toBe(want);
      }
      // the ids carry a suffix: the guard looks at the first character only
      expect(support[col('id')]).toBe(`${want}#1`);
      expect(top[col('id')]).toBe(`${want}#2`);
      expect(top[col('on_top_of')]).toBe(`${want}#1`);
      expect(support[col('on_top_of')]).toBe('');
      // number columns: never a quote, negatives as they are
      expect(NUMBER_COLUMNS.map(c => support[col(c)])).toEqual(['-11.250', '-22.500', '600', '600', '750', '0', '-12.2', '1']);
      expect(NUMBER_COLUMNS.map(c => top[col(c)])).toEqual(['-10.000', '-23.000', '600', '600', '750', '750', '0.0', '1']);
    });
  }

  it('guards before quoting: a guarded value with a comma, a double quote or a line break is still one RFC 4180 field', () => {
    const text = furnitureCsv(hostileModel('=A1,"B"\nC'), {});
    expect(text).toContain(`,"'=A1,""B""\nC",`);
    expect(parseCsv(text)[1]![col('family')]).toBe(`'=A1,"B"\nC`);
  });

  it('the guarded columns are exactly the text columns: all ten guarded, the eight number columns never', () => {
    expect([...TEXT_COLUMNS, ...NUMBER_COLUMNS].sort()).toEqual([...CSV_COLUMNS].sort());
    const top = parseCsv(furnitureCsv(hostileModel('-x'), {}))[2]!;
    for (const c of TEXT_COLUMNS) expect(top[col(c)]!.startsWith("'-x"), c).toBe(true);
    for (const c of NUMBER_COLUMNS) expect(top[col(c)]!.startsWith("'"), c).toBe(false);
  });

  it('a non-string value in a text column (an older hand-made file) is guarded on its text; null stays empty', () => {
    const m = hostileModel('ok');
    (m.furniture![0] as unknown as Record<string, unknown>).handle = -5;
    (m.furniture![0] as unknown as Record<string, unknown>).note = null;
    const row = parseCsv(furnitureCsv(m, {}))[1]!;
    expect(row[col('dxf_handle')]).toBe("'-5");
    expect(row[col('note')]).toBe('');
  });
});

describe('the four seeded CSVs do not change (the goldens)', () => {
  for (const f of FURNISHED) {
    it(`${f.model}: no text field starts with = + - @ TAB CR; the list equals ${f.csv}.csv and ${f.csv}-typed.csv byte for byte`, () => {
      const model = loadModel(f.model);
      const kinds = new Map((model.furnitureKinds ?? []).map(k => [k.key, k]));
      const starts = (model.furniture ?? []).flatMap(p => [p.id, p.floor, p.kind, kinds.get(p.kind)?.label, p.family, p.block,
        p.layer, p.handle, p.on, p.note]).filter(v => v !== null && v !== undefined && /^[=+\-@\t\r]/.test(String(v)));
      expect(starts).toEqual([]);
      expect(Buffer.from(furnitureCsv(model, {}), 'utf8').equals(csvFile(`${f.csv}.csv`).subarray(BOM.length))).toBe(true);
      expect(Buffer.from(furnitureCsv(model, typedHeights(model)), 'utf8')
        .equals(csvFile(`${f.csv}-typed.csv`).subarray(BOM.length))).toBe(true);
    });
  }
});
