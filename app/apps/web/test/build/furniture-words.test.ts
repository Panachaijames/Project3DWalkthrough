// After the final check of 9 Nov 2026 (docs/upload/contract-issues/UR.md, "After the final check (9 Nov)"): the pure rules.
//   * A grey family given a kind on the Check step: the word saved is the family exactly as its flag shows it, for the
//     final check's names (the house's five, SmartTable, a HermanMiller_ family), and the select reads the kind back;
//     one family, one kind (a word of the same family saved before in another way, 'TF2092 P', is replaced, not kept
//     beside it); the kind the select shows is the one the builder gives (the same form, the same order of kinds), also
//     for settings saved before the fix and for the acceptance settings' own words.
//   * familyForm on the builder's table (services/builder/tests/test_furniture_words.py FORMS and CODES: the same rows).
//   * The furniture size limits: setFurnitureLimits (the same values are no change), furnitureIssues (the API's bounds
//     and words) and the pre-build checklist.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { FURNITURE_KINDS as KINDS_OF_COMPONENT, kindOfFamily as kindOfComponent } from '@/build/FurnitureWords';
import {
  familyForm, furnitureIssues, FURNITURE_KINDS, kindOfFamily, setFurnitureLimits, setFurnitureWord,
} from '@/build/settingsEdit';
import { checklist } from '@/build/steps';
import type { BuildDetail, BuildSettings } from '@/upload/contracts';
import { FIXTURES_DIR } from '../mock-api/fixtures';

const U = (...p: string[]) => path.join(FIXTURES_DIR, 'upload', ...p);
const BANK = JSON.parse(readFileSync(U('settings', 'bank.json'), 'utf8')) as BuildSettings;
const HOUSE = JSON.parse(readFileSync(U('settings', 'house.json'), 'utf8')) as BuildSettings;
const withWords = (words: Record<string, string[]>): BuildSettings => ({ ...HOUSE, furniture: { ...HOUSE.furniture, words } });

const HERMAN = 'HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range';
/** The final check's names, each with a kind the furniture kit's vocabulary does not give it (as the builder test). */
const SEVEN: [string, string][] = [
  ['TF2092P', 'sanitary'], ['TF0560P', 'sanitary'], ['A$C2619574F', 'sanitary'], ['A$C238E5230', 'bed'],
  ['A$C5BF14633', 'coffee-table'], ['SmartTable', 'bar-table'], [HERMAN, 'sofa'],
];

describe('a grey family given a kind on the Check step (U-12.3)', () => {
  it('saves each of the final check\'s names exactly as its flag shows it, and the select reads the kind back', () => {
    let s = withWords({});
    for (const [family, kind] of SEVEN) {
      s = setFurnitureWord(family, kind)(s);
      expect(kindOfFamily(s, family)).toBe(kind);
    }
    expect(s.furniture.words).toEqual({
      sanitary: ['TF2092P', 'TF0560P', 'A$C2619574F'], bed: ['A$C238E5230'], 'coffee-table': ['A$C5BF14633'],
      'bar-table': ['SmartTable'], sofa: [HERMAN],
    });
    // what the saver sends: the names unchanged (no camel-case split, no trimming, no case change)
    expect((JSON.parse(JSON.stringify(s)) as BuildSettings).furniture.words).toEqual(s.furniture.words);
    // another kind moves the family; "No kind (grey)" takes it out
    const moved = setFurnitureWord('A$C238E5230', 'sofa')(s);
    expect(moved.furniture.words.bed).toBeUndefined();
    expect(moved.furniture.words.sofa).toEqual([HERMAN, 'A$C238E5230']);
    expect(kindOfFamily(moved, 'A$C238E5230')).toBe('sofa');
    expect(kindOfFamily(setFurnitureWord('TF2092P', '')(s), 'TF2092P')).toBe('');
    expect(kindOfFamily(s, 'TF2092PX')).toBe('');                                       // another family
  });

  it('settings saved before the fix and the acceptance settings\' words show the kind the build gives', () => {
    // saved by the screen before the fix (the final check's house): the family as shown
    const before = withWords({ sanitary: ['TF2092P', 'TF0560P', 'A$C2619574F', 'klkjlll'], bed: ['A$C238E5230'] });
    expect(kindOfFamily(before, 'TF2092P')).toBe('sanitary');
    expect(kindOfFamily(before, 'A$C238E5230')).toBe('bed');
    // the acceptance settings write the kit's split form ('TF2092 P'): one family with 'TF2092P'
    expect(kindOfFamily(HOUSE, 'TF2092P')).toBe('sanitary');
    expect(kindOfFamily(HOUSE, 'A$C5BF14633')).toBe('coffee-table');
    expect(kindOfFamily(HOUSE, 'BASE')).toBe('cabinet');
    // a new kind replaces the older form instead of keeping both
    const t = setFurnitureWord('TF2092P', 'bed')(HOUSE);
    expect(t.furniture.words.sanitary).toEqual(['TF0560 P', 'klkjlll', 'A$C2619574 F']);
    expect(t.furniture.words.bed).toEqual(['A$C238 E5230', 'TF2092P']);
    expect(kindOfFamily(t, 'TF2092P')).toBe('bed');
  });

  it('the builder\'s order when hand-made settings give one family two kinds; unknown kinds and blank names give none', () => {
    expect(kindOfFamily(withWords({ sofa: ['TF2092P'], bed: ['TF2092 P'] }), 'TF2092P')).toBe('bed');   // sorted: bed first
    expect(kindOfFamily(withWords({ nonsense: ['TF2092P'] }), 'TF2092P')).toBe('');
    expect(kindOfFamily(withWords({ sofa: ['   '] }), ' ')).toBe('');
    expect(kindOfComponent).toBe(kindOfFamily);
    expect(KINDS_OF_COMPONENT).toBe(FURNITURE_KINDS);
    expect(FURNITURE_KINDS.map(k => k.kind)).toHaveLength(22);
  });
});

describe('familyForm: the builder\'s family_form', () => {
  // the rows of services/builder/tests/test_furniture_words.py FORMS
  const FORMS: [string, string][] = [
    ['TF2092P', 'tf2092p'], ['TF2092 P', 'tf2092p'], ['A$C238 E5230', 'a$c238e5230'], ['A$C5BF14633', 'a$c5bf14633'],
    ['SmartTable', 'smarttable'], [HERMAN, 'hermanmiller_seating_aer1a_newaeron_workchair_asize-se101_sizelow-hgtrange'],
    ['Fritz-Hansen_SH200 - Default', 'fritz-hansen_sh200-default'], ['loose shapes on XR_L44$0$I-FURN', 'looseshapesonxr_l44$0$i-furn'],
    [' tab\there\nand\rthere ', 'tabhereandthere'], ['', ''],
  ];
  // ... and its CODES (code points as numbers on both sides)
  const CODES: [number[], string | number[]][] = [
    [[0x58, 0x0b, 0x59, 0x0c, 0x5a, 0x1c, 0x61, 0x1f, 0x62, 0x85, 0x63, 0xa0, 0x64, 0x1680, 0x65, 0x2000, 0x66, 0x200a, 0x67,
      0x2028, 0x68, 0x2029, 0x69, 0x202f, 0x6a, 0x205f, 0x6b, 0x3000, 0x6c], 'xyzabcdefghijkl'],
    [[0xfeff, 0x42, 0x200b, 0x43], [0xfeff, 0x62, 0x200b, 0x63]],
    [[0x130], [0x69, 0x307]],
    [[0xe1a, 0xe49, 0xe32, 0xe19, 0x20, 0x33, 0x31], [0xe1a, 0xe49, 0xe32, 0xe19, 0x33, 0x31]],
  ];
  it('the same rows give the same forms', () => {
    for (const [name, form] of FORMS) expect(familyForm(name), name).toBe(form);
    for (const [codes, want] of CODES) {
      expect(familyForm(String.fromCodePoint(...codes))).toBe(typeof want === 'string' ? want : String.fromCodePoint(...want));
    }
  });
});

const detail = (s: BuildSettings): BuildDetail => ({
  id: '20261109T101500-0a1b2c', projectId: 'p', createdAt: '', updatedAt: '', status: 'open', savedVersion: null, sourceNames: [],
  runStatus: 'done', url: '', sources: [], settings: s, settingsRevision: 2, layersReviewedAt: '2026-11-09T00:00:00Z',
  suggestions: {}, run: null, result: null, urls: { settings: '', run: '', cancel: '', save: '' },
});

describe('the furniture size limits (U-10.4 minSize, minDepth)', () => {
  it('setFurnitureLimits changes only what differs; the same values are no change', () => {
    expect(BANK.furniture.minSize).toBe(0.08);
    expect(BANK.furniture.minDepth).toBeNull();
    expect(setFurnitureLimits({ minSize: 0.08 })(BANK)).toBe(BANK);
    expect(setFurnitureLimits({ minDepth: null })(BANK)).toBe(BANK);
    const s = setFurnitureLimits({ minSize: 0.25, minDepth: 0.25 })(BANK);
    expect([s.furniture.minSize, s.furniture.minDepth]).toEqual([0.25, 0.25]);
    expect(s.furniture.words).toBe(BANK.furniture.words);                              // the rest untouched
    expect(setFurnitureLimits({ minDepth: null })(s).furniture).toEqual({ ...s.furniture, minDepth: null });
    expect(setFurnitureLimits({ minSize: 0.25 })(s)).toBe(s);
  });

  it('furnitureIssues: 0 - 10 m each (no depth limit is fine), in the API\'s words; the checklist blocks on them', () => {
    expect(furnitureIssues(BANK)).toEqual([]);
    expect(furnitureIssues(HOUSE)).toEqual([]);
    expect(furnitureIssues(setFurnitureLimits({ minSize: 0, minDepth: 10 })(BANK))).toEqual([]);
    const bad = setFurnitureLimits({ minSize: 12, minDepth: -0.1 })(BANK);
    expect(furnitureIssues(bad)).toEqual([
      { path: 'furniture/minSize', message: 'the smallest piece is 0 - 10 m' },
      { path: 'furniture/minDepth', message: 'the smallest depth is 0 - 10 m' },
    ]);
    expect(checklist(detail(BANK), BANK)).toEqual([]);
    expect(checklist(detail(bad), bad).map(i => [i.step, i.level, i.text])).toEqual([
      ['floors', 'block', 'the smallest piece is 0 - 10 m'],
      ['floors', 'block', 'the smallest depth is 0 - 10 m'],
    ]);
  });
});
