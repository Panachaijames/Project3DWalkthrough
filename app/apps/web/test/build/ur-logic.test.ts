// UR (the review-and-fix step of the upload milestone, docs/upload/contract-issues/UR.md): the pure rules behind the web
// app's fixes, each with the case a verifier found.
//   V3-5  set-asides: linear edits (20,000 refs; 10,000 onto 10,000), the selection check, the saver applying each change
//         once and sending nothing for a change that changes nothing (V3-1);
//   V2-7  a grey family's count from the flag's own wording, never the first number of a name like TF2092P;
//   V2-2  the loss alert's first sentence counts placements, not items;
//   V2-6  suggestions to check (the name and contents disagree, or contents alone made a building role);
//   V2-11 the units chosen against the door votes;
//   V2-15 project ids: no id of digits alone, no dangling or double hyphen;
//   V3-8  the files of a version are offered again only when a saved draft made it.
import { describe, expect, it } from 'vitest';
import { lossText } from '@/build/FilesStep';
import { greyCount } from '@/build/CheckStep';
import { suggestionToCheck } from '@/build/roles';
import { addSetAside, asideOf, keyAndHolders, restoreSetAside, setOffice, setPieceLayer } from '@/build/settingsEdit';
import { checklist, errorAdvice, firstReadingEnded, unitsAgainstVotes } from '@/build/steps';
import { latestFromUpload } from '@/pages/UploadPage';
import { projectIdOf, projectIdProblem } from '@/lib/slug';
import type { BuildDetail, BuildSettings, ItemRef } from '@/upload/contracts';
import { createSettingsSaver } from '@/upload/settingsSaver';

const SETTINGS = {
  format: 'build-settings/1', office: null,
  project: { name: 'P', shortName: 'P', projectNo: null, exportedFrom: null, photoName: 'P', maxPrefix: 'PP', maxFileName: 'P.ms' },
  sources: [{ sha1: 'a'.repeat(40), name: 'L1.dwg', kind: 'dwg', units: 'm', unitsConfirmed: true }],
  layers: {}, floors: [],
  defaults: { doorHead: 2.1, windowSill: 0.9, windowHead: 2.1, railingHeight: 1.1, slabThickness: 0.25, singleLineHeight: 1 },
  furniture: { heights: {}, bases: {}, words: {}, skip: [], minSize: 0.08, minDepth: null, looseLayers: [], pieceLayer: 'insert' },
  vocabulary: {},
  options: { revitWallTypes: 'auto', parapets: 'auto', objectClosures: true, liftShafts: true, plinth: 'auto', outlineWalls: 'off', offset: 'auto' },
  fixes: { setAside: [], openings: [], outlineEdges: [] },
} as unknown as BuildSettings;

const ref = (i: number, floor = 'L1'): ItemRef => ({ floor, source: 'a'.repeat(40), key: `B${i}/${i}`, sig: '0'.repeat(12), rsig: '', elementId: null, layer: 'A-WALL' });
const refs = (from: number, n: number) => Array.from({ length: n }, (_, i) => ref(from + i));
const ms = (f: () => void) => { const t0 = performance.now(); f(); return performance.now() - t0; };

describe('V3-5 set-asides at the 20,000 cap', () => {
  it('addSetAside is linear: 20,000 refs, and 10,000 onto 10,000, each well under the old 2.8 s and 3.3 s', () => {
    let s = SETTINGS;
    expect(ms(() => { s = addSetAside(refs(0, 20_000))(SETTINGS); })).toBeLessThan(400);
    expect(s.fixes.setAside.length).toBe(20_000);
    let t = addSetAside(refs(0, 10_000))(SETTINGS);
    expect(ms(() => { t = addSetAside(refs(5_000, 10_000))(t); })).toBeLessThan(400);
    expect(t.fixes.setAside.length).toBe(15_000);                       // the 5,000 already there are kept once
    expect(addSetAside(refs(0, 10))(t)).toBe(t);                          // nothing new: the same settings
  });

  it('restoreSetAside drops a key and the blocks holding it, linear in the set-asides', () => {
    const s = addSetAside([...refs(0, 20_000), { ...ref(0), key: 'BLOCK' }])(SETTINGS);
    let t = s;
    expect(ms(() => { t = restoreSetAside('L1', refs(0, 5_000).map(r => r.key))(s); })).toBeLessThan(300);
    expect(t.fixes.setAside.length).toBe(15_001);
    const inside = restoreSetAside('L1', ['BLOCK/7/9'])(t);               // an item inside the set-aside block
    expect(inside.fixes.setAside.some(r => r.key === 'BLOCK')).toBe(false);
    expect(restoreSetAside('L2', ['B7/7'])(s)).toBe(s);                    // another floor: untouched
    expect(keyAndHolders('a/b/c')).toEqual(['a/b/c', 'a/b', 'a']);
  });

  it('the selection check is linear: 10,000 selected against 10,000 set aside', () => {
    const aside = new Set(refs(0, 10_000).map(r => r.key));
    const selected = [...refs(5_000, 10_000).map(r => r.key), 'B3/3/inner'];
    let got: string[] = [];
    expect(ms(() => { got = asideOf(selected, aside); })).toBeLessThan(200);
    expect(got.length).toBe(5_001);
    expect(got).toContain('B3/3/inner');
  });

  it('the saver applies each change once (it was applied three times per change)', () => {
    let calls = 0;
    const saver = createSettingsSaver({ base: { settings: SETTINGS, revision: 1 }, debounceMs: 10_000, put: () => new Promise(() => undefined) });
    const counted = (s: BuildSettings) => { calls++; return addSetAside([ref(1)])(s); };
    saver.change(counted);
    expect(calls).toBe(1);
    expect(saver.state.settings.fixes.setAside.length).toBe(1);
    saver.flush();                                                       // sending: no further application
    expect(calls).toBe(1);
    expect(saver.state.status).toBe('saving');
    saver.close();
  });
});

describe('V3-1 a change that changes nothing is not saved', () => {
  it('setOffice of the same office returns the same settings, and the saver sends no PUT for it', async () => {
    expect(setOffice(null)(SETTINGS)).toBe(SETTINGS);
    expect(setOffice('dwp')(SETTINGS).office).toBe('dwp');
    expect(setPieceLayer('insert')(SETTINGS)).toBe(SETTINGS);
    const puts: unknown[] = [];
    const saver = createSettingsSaver({ base: { settings: SETTINGS, revision: 4 }, debounceMs: 0, put: s => { puts.push(s); return new Promise(() => undefined); } });
    saver.change(setOffice(null));
    saver.flush();
    expect(puts.length).toBe(0);
    expect(saver.state.status).toBe('saved');
    expect(saver.state.revision).toBe(4);
    saver.change(setOffice('dwp'));
    saver.flush();
    expect(puts.length).toBe(1);
    saver.close();
  });
});

describe('V2-7 grey families', () => {
  it('the count is the flag\'s own, not a number in the family name', () => {
    const flag = (family: string, n: number) => ({
      title: `${family}: ${n} grey box${n === 1 ? '' : 'es'}`,
      detail: `The furniture kit does not know what ${family} is, so its ${n} piece${n === 1 ? ' is' : 's are'} grey. Pick a kind for the family.`,
    });
    expect(greyCount(flag('TF2092P', 3))).toBe(3);
    expect(greyCount(flag('A$C2619574F', 1))).toBe(1);
    expect(greyCount(flag('loose shapes on XR_L44$0$I-FURN', 21))).toBe(21);
    expect(greyCount(flag('Fritz-Hansen_SH200 - Default', 8))).toBe(8);
    expect(greyCount({ title: 'TF0560P', detail: 'so its 4 pieces are grey' })).toBe(4);
    expect(greyCount({ title: 'TF0560P', detail: 'no count here' })).toBeNull();
  });
});

describe('V2-2 the loss alert', () => {
  it('counts placements of lost blocks, never as items', () => {
    expect(lossText(4)).toBe('4 placements of lost blocks are in the plan, and the notes above say how many items did not come through.');
    expect(lossText(1)).toContain('1 placement of lost blocks is in the plan');
    expect(lossText(0)).toContain('Parts of the plan did not come through');
    expect(lossText(4)).not.toMatch(/4 items/);
  });
});

describe('V2-6 suggestions to check', () => {
  it('a name the contents contradict, or a building role from the contents alone', () => {
    expect(suggestionToCheck({ role: 'ignore', from: 'name', evidence: ['named like an ignore layer (*ANNO*)', 'named like an ignore layer, but only texts (12), such as BA, BE, UP ...'] }))
      .toBe('the name and the contents disagree: named like an ignore layer, but only texts (12), such as BA, BE, UP ...');
    expect(suggestionToCheck({ role: 'glass', from: 'contents', evidence: ['12 glass-like line pairs (0.5 - 7 cm apart) among its 24 lines, and no fills'] }))
      .toContain('suggested by what is drawn on it only');
    expect(suggestionToCheck({ role: 'door', from: 'contents', evidence: ['7 door swings with their leaves'] })).not.toBeNull();
    expect(suggestionToCheck({ role: 'wall', from: 'name', evidence: ['named like a wall layer (A-WALL*)', 'its contents agree: 3 solid fills ...'] })).toBeNull();
    expect(suggestionToCheck({ role: 'room-name', from: 'contents', evidence: ['only texts (3), such as LOBBY'] })).toBeNull();
    expect(suggestionToCheck({ role: 'other', from: 'default', evidence: ['no rule matched'] })).toBeNull();
    expect(suggestionToCheck(undefined)).toBeNull();
  });
});

describe('V2-11 units against the door votes', () => {
  const votes = { mm: 28, cm: 0, m: 0, in: 0, ft: 0 };
  it('metres on a millimetre drawing is said, on the Files step and as a checklist warning', () => {
    expect(unitsAgainstVotes('m', votes)).toBe('its door symbols measure right in millimetres (28 doors), none in metres: check the units');
    expect(unitsAgainstVotes('mm', votes)).toBeNull();
    expect(unitsAgainstVotes('m', { mm: 2, cm: 0, m: 0, in: 0, ft: 0 })).toBeNull();     // too few doors to say
    expect(unitsAgainstVotes('m', { mm: 28, cm: 0, m: 4, in: 0, ft: 0 })).toBeNull();    // some doors agree
    const d = { settingsRevision: 2, sources: [], run: null, layersReviewedAt: '2026-11-09T00:00:00Z', status: 'open' } as unknown as BuildDetail;
    const items = checklist(d, SETTINGS, { votes: { ['a'.repeat(40)]: votes } });
    const warn = items.find(i => i.id === `units-votes:${'a'.repeat(40)}`);
    expect(warn?.level).toBe('warn');
    expect(warn?.text).toBe('L1.dwg: its door symbols measure right in millimetres (28 doors), none in metres: check the units');
  });
});

describe('V3-4 a first reading that ended', () => {
  it('is read again from the Files step, with advice that says so', () => {
    const run = (status: string, only: string[] | null = null) => ({ kind: 'prepare', status, only });
    const d = (r: unknown, revision = 0) => ({ run: r, settingsRevision: revision, status: 'open' }) as unknown as BuildDetail;
    expect(firstReadingEnded(d(run('interrupted')))).toBe(true);
    expect(firstReadingEnded(d(run('cancelled')))).toBe(true);
    expect(firstReadingEnded(d(run('failed')))).toBe(true);
    expect(firstReadingEnded(d(run('running')))).toBe(false);
    expect(firstReadingEnded(d(run('failed'), 1))).toBe(false);
    expect(firstReadingEnded(d(run('failed', ['x'])))).toBe(false);
    expect(errorAdvice('interrupted', 'prepare')).toBe('The reading stopped (the API or the computer restarted): read the drawings again.');
    expect(errorAdvice('cancelled', 'prepare')).toContain('read the drawings again');
    expect(errorAdvice('interrupted', 'build')).toBe('The run stopped (the API or the computer restarted): build again.');
  });
});

describe('V2-15 project ids', () => {
  it('a name of digits makes no id; an id with a dangling or double hyphen is refused', () => {
    expect(projectIdOf('บ้านสุขุมวิท ซอย 31')).toBe('');
    expect(projectIdOf('Sukhumvit 31')).toBe('sukhumvit-31');
    expect(projectIdOf('2026')).toBe('');
    expect(projectIdProblem('ab-')).toBe('ending in a letter or digit, with no two hyphens in a row');
    expect(projectIdProblem('a--b')).not.toBeNull();
    expect(projectIdProblem('a-b')).toBeNull();
  });
});

describe('V3-8 the files of a version again', () => {
  it('only when a saved draft made the latest version', () => {
    expect(latestFromUpload(2, [])).toBe(false);
    expect(latestFromUpload(2, [{ status: 'saved', savedVersion: 1 }, { status: 'open', savedVersion: null }])).toBe(false);
    expect(latestFromUpload(2, [{ status: 'saved', savedVersion: 2 }])).toBe(true);
    expect(latestFromUpload(0, [{ status: 'saved', savedVersion: 0 }])).toBe(false);
  });
});
