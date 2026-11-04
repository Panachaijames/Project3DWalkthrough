// Builder C: the stored furniture state (DESIGN.md 11.2, 18.31, 17.2): junk ignored, only `false` keeps the doorways tick off,
// nothing stored when nothing differs from the starting heights, a Reset over saved heights is stored, host mode stores no
// heights, the prototypes' JSON shape and key order.
import { describe, expect, it } from 'vitest';
import type { FurnitureKind } from '../../../src/contracts';
import { loadStored, readStoredState, saveStored, writeStoredState } from '../../../src/furniture/storage';
import { loadModel } from './util';

const kinds = loadModel('mini').furnitureKinds as FurnitureKind[];
const byKey = (key: string) => kinds.filter(k => k.key === key);

describe('readStoredState', () => {
  it('reads whole mm 10 - 5000 for known kinds and the doorways tick', () => {
    expect(readStoredState('{"table":600,"coffee-table":420}', kinds)).toEqual({ heights: { table: 600, 'coffee-table': 420 }, keepDoorways: true });
    expect(readStoredState('{"table":600,"keepDoorways":false}', kinds)).toEqual({ heights: { table: 600 }, keepDoorways: false });
    expect(readStoredState('{"table":"640","seat":460.5}', kinds)).toEqual({ heights: { table: 640, seat: 461 }, keepDoorways: true });
  });
  it('ignores values that are not numbers in range and kinds this model does not have (test_boxes.mjs garbage), keeps the rest', () => {
    const s = readStoredState(JSON.stringify({ table: 'tall', seat: 12, plant: 99999, sofa: 800, 'tall-cabinet': 1900 }), kinds);
    expect(s.heights).toEqual({ seat: 12, 'tall-cabinet': 1900 });
  });
  it('ignores text that is not JSON, null, nothing, and JSON that is not an object', () => {
    for (const raw of [null, '', 'not json {', 'null', '5', '"x"', '[]', 'true']) {
      expect(readStoredState(raw, kinds), String(raw)).toEqual({ heights: {}, keepDoorways: true });
    }
  });
  it('only a stored false turns the doorways tick off ("no", 0, null, true leave it on); the heights next to it are still read', () => {
    for (const raw of ['{"keepDoorways":"no","table":800}', '{"keepDoorways":0}', '{"keepDoorways":null}', '{"keepDoorways":true}']) {
      const s = readStoredState(raw, kinds);
      expect(s.keepDoorways, raw).toBe(true);
      expect(s.heights, raw).toEqual(raw.includes('"table"') ? { table: 800 } : {});
    }
  });
  it('reads only the kinds it is given (a kind without pieces has no row: not read)', () => {
    expect(readStoredState('{"table":600,"seat":480}', byKey('seat'))).toEqual({ heights: { seat: 480 }, keepDoorways: true });
  });
});

describe('writeStoredState', () => {
  const model = { table: 750, seat: 450, 'coffee-table': 450 };
  it('local: the kinds that differ from the starting heights, in the given order, then keepDoorways: false', () => {
    expect(writeStoredState({ heights: { ...model, table: 600 }, keepDoorways: true }, 'local', model)).toBe('{"table":600}');
    expect(writeStoredState({ heights: { ...model, table: 600 }, keepDoorways: false }, 'local', model)).toBe('{"table":600,"keepDoorways":false}');
    expect(writeStoredState({ heights: { ...model, seat: 480, table: 600 }, keepDoorways: true }, 'local', model)).toBe('{"table":600,"seat":480}');
  });
  it('nothing to keep: null (the key is removed)', () => {
    expect(writeStoredState({ heights: { ...model }, keepDoorways: true }, 'local', model)).toBeNull();
    expect(writeStoredState({ heights: { ...model, table: 600 }, keepDoorways: true }, 'host', model)).toBeNull();
  });
  it('the doorways tick alone, in both modes', () => {
    expect(writeStoredState({ heights: { ...model }, keepDoorways: false }, 'local', model)).toBe('{"keepDoorways":false}');
    expect(writeStoredState({ heights: { ...model, table: 600 }, keepDoorways: false }, 'host', model)).toBe('{"keepDoorways":false}');
  });
  it('the baseline is the starting heights: with table 600 saved, the model height typed back (or a Reset) is stored, 600 is not', () => {
    const start = { ...model, table: 600 };                     // the model's heights with the saved ones over them
    expect(writeStoredState({ heights: { ...model }, keepDoorways: true }, 'local', start)).toBe('{"table":750}');
    expect(writeStoredState({ heights: { ...start }, keepDoorways: true }, 'local', start)).toBeNull();
  });
  it('round trip: what is written reads back', () => {
    const text = writeStoredState({ heights: { ...model, table: 600, seat: 480 }, keepDoorways: false }, 'local', model)!;
    expect(readStoredState(text, kinds)).toEqual({ heights: { table: 600, seat: 480 }, keepDoorways: false });
  });
});

describe('loadStored / saveStored without a storage', () => {
  it('Node has no localStorage: nothing is read, nothing throws', () => {
    expect(loadStored('walkthrough-furniture-heights:Fixture:abc')).toBeNull();
    expect(() => saveStored('walkthrough-furniture-heights:Fixture:abc', '{"table":600}')).not.toThrow();
    expect(() => saveStored('walkthrough-furniture-heights:Fixture:abc', null)).not.toThrow();
  });
});
