// Builder C: the pure furniture helpers (DESIGN.md 13 "Furniture", 17.2): whole mm, typed heights, Python's digits, RFC 4180,
// the underside, the Walk rule and the family list byte for byte against the prototypes' files and the Python goldens.
import { describe, expect, it } from 'vitest';
import type { BuiltModel, FurniturePiece } from '../../../src/contracts';
import {
  CSV_COLUMNS, closeRemoved, csvField, csvFileName, fixedDecimals, furnitureCsv, furnitureData, groupsOf, heightFromData,
  parseTypedHeight, removedIdsOf, stopsWalk, undersideMm, wholeMm,
} from '../../../src/furniture/logic';
import { BOM, FURNISHED, csvFile, golden, loadModel, loadVariant, readText, typedHeights, FURN } from './util';
import path from 'node:path';

describe('wholeMm', () => {
  it('rounds half up, as furniture_kit.csv_text and Math.round', () => {
    expect(wholeMm(62.5)).toBe(63);
    expect(wholeMm(460.5)).toBe(461);
    expect(wholeMm(10.5)).toBe(11);
    expect(wholeMm(10.49)).toBe(10);
    expect(wholeMm(750)).toBe(750);
    expect(wholeMm(-0.5)).toBe(0);
  });
});

describe('parseTypedHeight', () => {
  it("refuses '', '4,5', '-3', 'abc', 6 and 9999 and takes 10 and 5000", () => {
    for (const s of ['', '4,5', '-3', 'abc', '6', '9999', ' ', '1e3', '0x20', '600mm', '.5']) expect(parseTypedHeight(s)).toBeNull();
    expect(parseTypedHeight('10')).toBe(10);
    expect(parseTypedHeight('5000')).toBe(5000);
  });
  it('takes whole mm of a decimal number with spaces around it, half up, inside the range', () => {
    expect(parseTypedHeight(' 600 ')).toBe(600);
    expect(parseTypedHeight('9.5')).toBe(10);
    expect(parseTypedHeight('600.')).toBe(600);
    expect(parseTypedHeight('5000.4')).toBe(5000);
    expect(parseTypedHeight('5000.5')).toBeNull();
    expect(parseTypedHeight('9.4')).toBeNull();
  });
  it('heightFromData (stored, saved, API values) reads Number(v) the same way', () => {
    expect(heightFromData(600)).toBe(600);
    expect(heightFromData('600')).toBe(600);
    expect(heightFromData(460.5)).toBe(461);
    for (const v of [9, 5001, 'tall', null, undefined, true, {}, NaN, 99999]) expect(heightFromData(v)).toBeNull();
  });
});

describe('fixedDecimals', () => {
  it("gives Python's f'{v:.nf}' digits (an exact tie goes to the even digit) and never -0.000", () => {
    // [value, places, Python's text] (computed with Python 3.14.3 and furniture_kit._fixed's rule)
    const cases: [number, number, string][] = [
      [12.25, 1, '12.2'], [12.35, 1, '12.3'], [0.0625, 3, '0.062'], [-0.0004, 3, '0.000'], [-12.25, 1, '-12.2'], [0.125, 2, '0.12'],
      [0.375, 2, '0.38'], [1.005, 2, '1.00'], [2.675, 2, '2.67'], [179.95, 1, '179.9'], [0.0005, 3, '0.001'], [-0.0005, 3, '-0.001'],
      [-0.0015, 3, '-0.002'], [1234.5675, 3, '1234.568'], [2.4995 + 1, 3, '3.499'], [-1.0004 + 1, 3, '0.000'], [0.75, 1, '0.8'],
      [89.996, 2, '90.00'], [-2.5e-7, 3, '0.000'], [0.05, 1, '0.1'], [0.15, 1, '0.1'], [0.25, 1, '0.2'], [0.35, 1, '0.3'], [0.45, 1, '0.5'],
    ];
    for (const [v, n, want] of cases) expect(fixedDecimals(v, n), `${v} to ${n}`).toBe(want);
  });
});

describe('csvField', () => {
  it('quotes a field with a comma, a double quote, CR or LF (inner quotes doubled), and writes null / undefined as empty', () => {
    expect(csvField('plain')).toBe('plain');
    expect(csvField('Chair, "Lux" model')).toBe('"Chair, ""Lux"" model"');
    expect(csvField('Block A\nsecond line')).toBe('"Block A\nsecond line"');
    expect(csvField('I-FURN\rCR')).toBe('"I-FURN\rCR"');
    expect(csvField('say "hi"')).toBe('"say ""hi"""');
    expect(csvField(null)).toBe('');
    expect(csvField(undefined)).toBe('');
    expect(csvField(600)).toBe('600');
    expect(csvField('')).toBe('');
  });
});

describe('stopsWalk', () => {
  it('a box stops Walk while its kind is shown and stops you, unless the doorways are kept clear and it is in an approach', () => {
    const on = { visible: true, blocks: true };
    expect(stopsWalk(on, [], true)).toBe(true);
    expect(stopsWalk({ visible: false, blocks: true }, [], true)).toBe(false);          // hidden
    expect(stopsWalk({ visible: true, blocks: false }, [], false)).toBe(false);         // stops off (a curtain's default)
    expect(stopsWalk(on, ['L1-001'], true)).toBe(false);                                 // in an approach, the tick on
    expect(stopsWalk(on, ['L1-001'], false)).toBe(true);                                 // ... the tick off
    expect(stopsWalk({ visible: true, blocks: false }, ['L1-001'], false)).toBe(false);
  });
});

describe('undersideMm', () => {
  const mini = loadModel('mini');
  const piece = (id: string) => mini.furniture!.find(p => p.id === id)!;
  it('a computer and a printer on a 750 mm table stand at 750, the wall TV hangs at 900, a chair stands on the floor', () => {
    expect(undersideMm(piece('L1-computer-001'), mini, {})).toBe(750);
    expect(undersideMm(piece('L1-printer-001'), mini, {})).toBe(750);
    expect(undersideMm(piece('L1-tv-001'), mini, {})).toBe(900);
    expect(undersideMm(piece('L1-seat-001'), mini, {})).toBe(0);
    expect(undersideMm(piece('L2-computer-001'), mini, {})).toBe(750);
  });
  it('follows a typed table height (600: the computer at 600), and the table itself stays on the floor', () => {
    expect(undersideMm(piece('L1-computer-001'), mini, { table: 600 })).toBe(600);
    expect(undersideMm(piece('L1-table-001'), mini, { table: 600 })).toBe(0);
  });
  it('a support that is not there: the piece stands on its kind base; bases are whole mm', () => {
    const broken = loadVariant('broken.json');
    expect(undersideMm(broken.furniture!.find(p => p.id === 'L1-computer-001')!, broken, {})).toBe(0);
    const awkward = loadVariant('awkward.json');
    expect(undersideMm(awkward.furniture!.find(p => p.id === 'Z1-plant-001')!, awkward, {})).toBe(11);     // a base of 10.5 mm
  });
  it('stops after three steps (no chains in real data; a piece standing on itself does not loop)', () => {
    const m = structuredClone(mini);
    const self = m.furniture!.find(p => p.id === 'L1-table-001')! as FurniturePiece;
    self.on = 'L1-table-001';
    expect(undersideMm(self, m, {})).toBe(3 * 750);
  });
});

describe('furnitureCsv', () => {
  it('has the README columns, CRLF after every row, no byte-order mark', () => {
    const text = furnitureCsv(loadModel('mini'), {});
    expect(text.split('\r\n')[0]).toBe(CSV_COLUMNS.join(','));
    expect(text.endsWith('\r\n')).toBe(true);
    expect(text.charCodeAt(0)).not.toBe(0xfeff);
    expect(/(^|[^\r])\n/.test(text)).toBe(false);
  });

  for (const f of FURNISHED) {
    it(`${f.model}: equals the prototype's ${f.csv}.csv without its BOM, byte for byte (model heights)`, () => {
      const file = csvFile(`${f.csv}.csv`);
      expect(file.subarray(0, 3).equals(BOM)).toBe(true);
      expect(Buffer.from(furnitureCsv(loadModel(f.model), {}), 'utf8').equals(file.subarray(3))).toBe(true);
    });
    it(`${f.model}: equals ${f.csv}-typed.csv (furniture_kit.csv_text with table 600, seat 300, cabinet 1000, other 2100)`, () => {
      const model = loadModel(f.model), file = csvFile(`${f.csv}-typed.csv`);
      const typed = typedHeights(model);
      expect(Object.keys(typed).length).toBeGreaterThan(0);
      expect(Buffer.from(furnitureCsv(model, typed), 'utf8').equals(file.subarray(3))).toBe(true);
    });
  }

  it('the prototype mini model equals expected_csv.py and furniture_kit.csv_text, with the model heights and with typed ones', () => {
    const mini = loadVariant('mini-original.json');
    expect(furnitureCsv(mini, {})).toBe(golden('mini.csv'));
    expect(furnitureCsv(mini, {})).toBe(golden('mini.kit.csv'));
    const typed = JSON.parse(readText(path.join(FURN, 'mini-typed-heights.json'))) as Record<string, number>;
    expect(furnitureCsv(mini, typed)).toBe(golden('mini-typed.csv'));
    expect(furnitureCsv(mini, typed)).toBe(golden('mini-typed.kit.csv'));
    const rows = Object.fromEntries(furnitureCsv(mini, typed).split('\r\n').slice(1, -1).map(l => [l.split(',')[0], l.split(',')]));
    expect(rows['L1-table-001']![12]).toBe('600');
    expect(rows['L1-computer-001']![13]).toBe('600');
    expect(rows['L2-computer-001']![13]).toBe('600');
  });

  it('the v1 mini fixture gives the same rows as the prototype mini model (its parts and doorway records change nothing)', () => {
    expect(furnitureCsv(loadModel('mini'), {})).toBe(golden('mini.csv'));
  });

  it('the awkward model of test_boxes.mjs equals Python byte for byte: commas, quotes, CR / LF, -0.0004, ties, 460.5 mm, floors not alphabetical', () => {
    const aw = loadVariant('awkward.json');
    const text = furnitureCsv(aw, {});
    expect(text).toBe(golden('awkward.csv'));
    expect(text).toBe(golden('awkward.kit.csv'));
    expect(text).toContain('"Chair, ""Lux"" model"');
    expect(text).toContain('"Block A\nsecond line"');
    expect(text).toContain('"run of 4, ""fronts"""');
    expect(text).toContain('"I-FURN\rCR"');
    expect(text).not.toContain('-0.000');
    expect(text).toContain(',0.000,0.062,63,570,461,0,12.2,');
    expect(text).toContain(',7.000,2.000,500,500,600,11,179.9,,7,');
    expect(text.indexOf('\r\nZ1-')).toBeLessThan(text.indexOf('\r\nA2-'));
  });

  it('leaves out pieces of an unknown kind or floor, puts a piece with a missing support on its kind base, keeps its on_top_of', () => {
    const broken = loadVariant('broken.json');
    const text = furnitureCsv(broken, {});
    expect(text).not.toContain('L9-seat-001');
    expect(text).not.toContain('L1-sofa-001');
    const row = text.split('\r\n').find(l => l.startsWith('L1-computer-001,'))!.split(',');
    expect(row[13]).toBe('0');
    expect(row[15]).toBe('L1-no-such-table');
    expect(text.split('\r\n').length).toBe(loadVariant('mini-original.json').furniture!.length + 2);
  });

  it('takes the floor order of the model and the kind order of furnitureKinds, then the id, whatever the order in the file', () => {
    const m = loadModel('bank-v2');
    const shuffled: BuiltModel = { ...m, furniture: [...m.furniture!].reverse() };
    expect(furnitureCsv(shuffled, {})).toBe(furnitureCsv(m, {}));
  });

  it('a model without furniture gives the header only', () => {
    expect(furnitureCsv(loadModel('bank-v1'), {})).toBe(CSV_COLUMNS.join(',') + '\r\n');
  });
});

describe('furnitureData and the file name', () => {
  it('keeps the pieces of known kinds and floors, in model order, and lists the others', () => {
    const d = furnitureData(loadVariant('broken.json'));
    expect(d.leftOut.map(p => p.id).sort()).toEqual(['L1-sofa-001', 'L9-seat-001']);
    expect(d.pieces.length).toBe(17);
  });
  it('names the CSV <photoName>_furniture_list.csv', () => {
    expect(csvFileName('BangkokBank-Sampeng')).toBe('BangkokBank-Sampeng_furniture_list.csv');
    expect(csvFileName('Fixture')).toBe('Fixture_furniture_list.csv');
    expect(csvFileName('a b/c')).toBe('a-b-c_furniture_list.csv');
  });
});

// ---------------------------------------------------------------------------------------------------------------------
// Deleted boxes (docs/boxes/DESIGN.md 2.5, 2.6, 4; step BX)
// ---------------------------------------------------------------------------------------------------------------------

describe('furnitureCsv with deleted boxes', () => {
  /** The golden without the rows of the given ids (the id is the first column; no id of the fixtures needs quoting). */
  const without = (text: string, ids: readonly string[]) => text.split('\r\n').filter(l => !ids.some(id => l.startsWith(id + ','))).join('\r\n');

  it('no third argument, undefined and an empty set give the text of before, byte for byte (the four projects and the Python goldens)', () => {
    for (const f of FURNISHED) {
      const m = loadModel(f.model), file = csvFile(`${f.csv}.csv`).subarray(BOM.length).toString('utf8');
      expect(furnitureCsv(m, {}), f.model).toBe(file);
      expect(furnitureCsv(m, {}, undefined), f.model).toBe(file);
      expect(furnitureCsv(m, {}, new Set()), f.model).toBe(file);
      const typed = csvFile(`${f.csv}-typed.csv`).subarray(BOM.length).toString('utf8');
      expect(furnitureCsv(m, typedHeights(m), new Set()), f.model).toBe(typed);
    }
    expect(furnitureCsv(loadVariant('mini-original.json'), {}, new Set())).toBe(golden('mini.csv'));
  });

  it('with deleted ids: the golden minus those rows, every other row unchanged (the closure keeps base_mm and on_top_of right)', () => {
    const mini = loadVariant('mini-original.json');
    const gone = [...closeRemoved(['L1-table-001', 'L2-seat-001'], mini.furniture!)];
    expect(gone.sort()).toEqual(['L1-computer-001', 'L1-printer-001', 'L1-table-001', 'L2-seat-001']);
    expect(furnitureCsv(mini, {}, new Set(gone))).toBe(without(golden('mini.csv'), gone));
    const typed = JSON.parse(readText(path.join(FURN, 'mini-typed-heights.json'))) as Record<string, number>;
    expect(furnitureCsv(mini, typed, new Set(gone))).toBe(without(golden('mini-typed.csv'), gone));
    // the bank: a table with what stands on it, and a chair
    const bank = loadModel('bank-v2'), file = csvFile('bank-v2.csv').subarray(BOM.length).toString('utf8');
    const support = bank.furniture!.find(p => bank.furniture!.some(q => q.on === p.id))!;
    const ids = [...closeRemoved([support.id, bank.furniture!.find(p => p.kind === 'seat')!.id], bank.furniture!)];
    expect(ids.length).toBeGreaterThan(2);
    const text = furnitureCsv(bank, {}, new Set(ids));
    expect(text).toBe(without(file, ids));
    expect(text.split('\r\n').length).toBe(file.split('\r\n').length - ids.length);
    // a deleted piece that only stood on a table: the table's row and every other row stay as they were
    const computer = bank.furniture!.find(p => p.on)!;
    expect(furnitureCsv(bank, {}, new Set([computer.id]))).toBe(without(file, [computer.id]));
  });

  it('every box deleted: the header only; an id the model lacks changes nothing', () => {
    const mini = loadVariant('mini-original.json');
    expect(furnitureCsv(mini, {}, new Set(mini.furniture!.map(p => p.id)))).toBe(CSV_COLUMNS.join(',') + '\r\n');
    expect(furnitureCsv(mini, {}, new Set(['L9-nothing-001']))).toBe(golden('mini.csv'));
  });
});

describe('closeRemoved (the closure rule, shared with the API)', () => {
  interface Case { name: string; pieces: { id: string; on?: string | null }[]; ids: string[]; closed: string[] }
  const cases = (JSON.parse(readText(path.join(FURN, 'close-removed.cases.json'))) as { cases: Case[] }).cases;

  it('every case of close-removed.cases.json (the file the API\'s Python test reads too)', () => {
    expect(cases.length).toBeGreaterThanOrEqual(12);
    for (const c of cases) {
      const got = closeRemoved(c.ids, c.pieces);
      expect([...got].sort(), c.name).toEqual([...new Set(c.closed)].sort());
      expect([...closeRemoved(got, c.pieces)].sort(), `${c.name}: closing twice changes nothing`).toEqual([...got].sort());
    }
  });
  it('takes any iterable and never changes what it was given', () => {
    const pieces = [{ id: 'c', on: 't' }, { id: 't', on: null }];
    const ids = new Set(['t']);
    expect([...closeRemoved(ids, pieces)].sort()).toEqual(['c', 't']);
    expect([...ids]).toEqual(['t']);
    expect([...closeRemoved((function* () { yield 't'; })(), pieces)].sort()).toEqual(['c', 't']);
  });
});

describe('groupsOf and removedIdsOf', () => {
  const pieces = [
    { id: 'L1-computer-001', on: 'L1-table-001' }, { id: 'L1-printer-001', on: 'L1-table-001' }, { id: 'L1-seat-001', on: null },
    { id: 'L1-table-001', on: null }, { id: 'L2-computer-001', on: 'L2-table-001' }, { id: 'L2-table-001', on: null },
  ];
  it('one group per deleted piece whose support is not deleted, the deleted pieces on it folded in, in the order given', () => {
    expect(groupsOf(new Set(), pieces)).toEqual([]);
    expect(groupsOf(new Set(['L1-table-001', 'L1-computer-001', 'L1-printer-001', 'L1-seat-001']), pieces)).toEqual([
      { top: 'L1-seat-001', on: [] }, { top: 'L1-table-001', on: ['L1-computer-001', 'L1-printer-001'] },
    ]);
    // a computer deleted on its own (its table stays) is its own group
    expect(groupsOf(new Set(['L2-computer-001', 'L1-printer-001']), pieces)).toEqual([{ top: 'L1-printer-001', on: [] }, { top: 'L2-computer-001', on: [] }]);
    // an id that names no piece is in no group
    expect(groupsOf(new Set(['nothing']), pieces)).toEqual([]);
    // a chain: all under the lowest deleted support
    const chain = [{ id: 'vase', on: 'tray' }, { id: 'tray', on: 'table' }, { id: 'table', on: null }];
    expect(groupsOf(new Set(['vase', 'tray', 'table']), chain)).toEqual([{ top: 'table', on: ['vase', 'tray'] }]);
    expect(groupsOf(new Set(['vase', 'tray']), chain)).toEqual([{ top: 'tray', on: ['vase'] }]);
  });
  it('removedIdsOf reads a map leniently: only an object with removed exactly true counts', () => {
    expect(removedIdsOf({ a: { removed: true }, b: { removed: false }, c: {}, d: 'yes', e: null, f: 7, g: [true], h: { removed: 1 }, i: { removed: true, kind: 'x' } }))
      .toEqual(['a', 'i']);
    for (const odd of [null, undefined, 'x', 7, [], [{ removed: true }], true]) expect(removedIdsOf(odd)).toEqual([]);
  });
});
