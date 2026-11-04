// Builder A: a store written by hand from the fixtures, in the layout of DESIGN.md 9.1 (meta.json, versions/<n>/...), for
// make-offline.mjs (the unit test) and the browser checks of the offline files it makes (test/harness/core). Three
// projects: the bank v2 (stages, saved heights), the hotel (two plan pictures, no stages) and a model whose drawing text is
// hostile: names with </script>, <!--, $' $& $` $$, the two template markers and an <img onerror>.
import { createHash } from 'node:crypto';
import { copyFileSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
export const TMP = process.env.WT_TMP ?? path.join(os.tmpdir(), 'wt-a');
export const HOSTILE = ['</script><script>window.__pwned = 1</script>', "$'", '$&', '$`', '$$', '__WTV_DATA__', '__WTV_STAMP__', '<!--',
  '<img src=x onerror="window.__pwned = 1">'];
const STAMP_ASIDE = '__WTV_' + 'STAMP__';
const read = (rel: string) => readFileSync(path.join(APP, rel));
const json = (rel: string): any => JSON.parse(read(rel).toString('utf8'));
const sha1 = (b: Buffer | string) => createHash('sha1').update(b).digest('hex');

export interface StoreVersion { projectId: string; version: number; stamp: string; dir: string }

function writeJson(file: string, value: unknown, indent?: number) {
  mkdirSync(path.dirname(file), { recursive: true });
  writeFileSync(file, `${JSON.stringify(value, null, indent)}\n`, 'utf8');
}

function counts(m: any) {
  return { floors: m.floors.length, parts: m.parts.length, openings: m.openings.length, furniture: (m.furniture ?? []).length,
    furnitureKinds: (m.furnitureKinds ?? []).length, rooms: m.rooms.length };
}

function version(projectId: string, n: number, opts: { model: any; modelText: string; presentation: any; stages: string | null;
  assets?: { name: string; role: string; floor?: string; file: string; mediaType: string; modelRef?: string }[]; overrides?: Record<string, number> | null;
  label: string; root: string;
  /** The 3ds Max script, copied (read-only) from the project folder (a path relative to it) into downloads/. */
  maxScript?: string;
  /** A converted model's stamp is its source's (DESIGN.md 6.3): the stamp and the file it comes from. */
  stamp?: { stamp: string; source: string } }): StoreVersion {
  const dir = path.join(opts.root, 'projects', projectId, 'versions', String(n));
  mkdirSync(path.join(dir, 'assets'), { recursive: true });
  writeFileSync(path.join(dir, 'model.json'), opts.modelText, 'utf8');
  if (opts.stages) writeFileSync(path.join(dir, 'stages.json'), opts.stages, 'utf8');
  const assets = (opts.assets ?? []).map(a => {
    copyFileSync(path.join(APP, a.file), path.join(dir, 'assets', a.name));
    const bytes = read(a.file);
    return { name: a.name, role: a.role, ...(a.floor ? { floor: a.floor } : {}), mediaType: a.mediaType, bytes: statSync(path.join(APP, a.file)).size,
      sha1: sha1(bytes), ...(a.modelRef ? { modelRef: a.modelRef } : {}) };
  });
  const modelSha1 = sha1(opts.modelText);
  const stamp = opts.stamp?.stamp ?? modelSha1.slice(0, 12);
  let maxScript: string | null = null;
  if (opts.maxScript) {
    maxScript = path.basename(opts.maxScript);
    mkdirSync(path.join(dir, 'downloads'), { recursive: true });
    copyFileSync(path.join(APP, '..', opts.maxScript), path.join(dir, 'downloads', maxScript));
  }
  writeJson(path.join(dir, 'version.json'), {
    format: 'walkthrough-version/1', projectId, version: n, label: opts.label, createdAt: '2026-11-03T05:00:00Z',
    sourceKind: 'cad', sourceFiles: opts.model.source, modelFormat: 'built-model/1', modelSha1, stamp, stampSource: opts.stamp?.source ?? 'model.json',
    counts: counts(opts.model), floors: opts.model.floors.map((f: any) => ({ key: f.key, name: f.name, level: f.level })),
    hasStages: !!opts.stages, assets, downloads: { maxScript, furnitureCsv: !!opts.model.furniture?.length },
    presentation: opts.presentation,
  }, 2);
  if (opts.overrides) writeJson(path.join(dir, 'overrides.json'), { format: 'walkthrough-overrides/1', heights: opts.overrides, revision: 3, updatedAt: '2026-11-03T06:00:00Z' }, 2);
  return { projectId, version: n, stamp, dir };
}

function meta(root: string, id: string, model: any, versions: number[]) {
  writeJson(path.join(root, 'projects', id, 'meta.json'), {
    format: 'walkthrough-project/1', id, name: model.project, shortName: model.shortName, projectNo: model.projectNo ?? null,
    sourceKind: 'cad', createdAt: '2026-11-03T05:00:00Z', updatedAt: '2026-11-03T06:00:00Z', latestVersion: Math.max(...versions), versions,
  }, 2);
}

/** Writes the store at <root> (default <WT_TMP>/data), replacing what was there. */
export function writeStore(root = path.join(TMP, 'data')): { root: string; versions: StoreVersion[] } {
  rmSync(root, { recursive: true, force: true });
  const out: StoreVersion[] = [];

  // the bank v2: model and stages byte for byte, a saved height
  const bankText = read('fixtures/models/bank-v2.model.json').toString('utf8');
  const bank = JSON.parse(bankText);
  meta(root, 'bank-sampeng', bank, [2]);
  out.push(version('bank-sampeng', 2, { root, model: bank, modelText: bankText, presentation: json('fixtures/presentation/bank-sampeng-v2.json'),
    stages: read('fixtures/stages/bank-v2.stages.json').toString('utf8'), overrides: { table: 600 }, label: '29 Oct 2026: furniture boxes' }));

  // the hotel: its two plan pictures, no stages
  const hotelText = read('fixtures/models/hotel.model.json').toString('utf8');
  const hotel = JSON.parse(hotelText);
  meta(root, 'hotel-lobby', hotel, [1]);
  out.push(version('hotel-lobby', 1, { root, model: hotel, modelText: hotelText, presentation: json('fixtures/presentation/hotel-lobby.json'), stages: null,
    label: '2 Nov 2026: read from two plan pictures', assets: [
      { name: 'floor1_plan.png', role: 'plan-picture', floor: 'F1', file: 'fixtures/pictures/floor1_plan.png', mediaType: 'image/png', modelRef: '../source/floor1_plan.png' },
      { name: 'floor2_plan.png', role: 'plan-picture', floor: 'F2', file: 'fixtures/pictures/floor2_plan.png', mediaType: 'image/png', modelRef: '../source/floor2_plan.png' },
    ] }));

  // hostile drawing text: the mini model with every name of the corpus in it
  const mini = json('fixtures/models/mini.model.json');
  const evil = HOSTILE.join(' ');
  mini.project = `Hostile ${evil}`;
  mini.shortName = `Hostile ${HOSTILE[0]}`;
  mini.source = [...HOSTILE];
  mini.rooms = HOSTILE.map((h, i) => ({ floor: mini.floors[i % mini.floors.length].key, name: h, label: h, area: 10 + i, x: 1 + i * 0.5, y: 1 + i * 0.3 }));
  mini.furniture.forEach((p: any, i: number) => { p.family = HOSTILE[i % HOSTILE.length]; p.layer = HOSTILE[(i + 1) % HOSTILE.length]; p.block = HOSTILE[(i + 2) % HOSTILE.length]; p.note = evil; });
  mini.furnitureKinds.forEach((k: any, i: number) => { k.label = `${k.label} ${HOSTILE[i % HOSTILE.length]}`; });
  const miniText = `${JSON.stringify(mini)}\n`;
  const pres = {
    documentTitle: `Hostile ${STAMP_ASIDE} ${HOSTILE[1]}`, heading: `Hostile ${HOSTILE[0]}`,
    intro: HOSTILE.map((h, i) => ({ text: `${h} `, bold: i % 2 === 0 })), accent: '#2f6f8f',
    legend: { layout: 'lines', items: HOSTILE.map(h => ({ colour: '#e3ddd3', text: h })) },
    camera: { kind: 'fitSlabs', away: [21.6, 22.05, 26.1], targetY: 1.2, panForPanel: true },
  };
  meta(root, 'hostile-names', mini, [1]);
  out.push(version('hostile-names', 1, { root, model: mini, modelText: miniText, presentation: pres, stages: null, label: `hostile ${evil}` }));
  return { root, versions: out };
}

/**
 * The store of the e2e checks on the app target before the seed exists (builder A's own run of tests/e2e/structure.spec.ts
 * and offline.spec.ts with WT_OFFLINE_DIR / WT_DATA_DIR): the five versions of lib/target.ts from the fixtures (the bank's
 * and the hotel's models and the bank's stages byte for byte, the provisional suite and house, the provisional
 * presentations, the 3ds Max scripts copied from the prototype folders, the suite stamped with its source's sha1 as the seed
 * will), the suite and the house without replay data (there are no provisional stages, DESIGN.md 17.1), and the hostile one.
 */
export function writeE2eStore(root = path.join(TMP, 'e2e-data')): { root: string; versions: StoreVersion[] } {
  rmSync(root, { recursive: true, force: true });
  const out: StoreVersion[] = [];
  const text = (rel: string) => read(rel).toString('utf8');
  const bank1 = text('fixtures/models/bank-v1.model.json'), bank2 = text('fixtures/models/bank-v2.model.json');
  meta(root, 'bank-sampeng', JSON.parse(bank2), [1, 2]);
  out.push(version('bank-sampeng', 1, { root, model: JSON.parse(bank1), modelText: bank1, presentation: json('fixtures/presentation/bank-sampeng-v1.json'),
    stages: text('fixtures/stages/bank-v1.stages.json'), label: '27 Oct 2026: two levels, openings from the detector (before the fix round)',
    maxScript: 'bank_test/previous_before_fix_round_2026-10-27/Bangkok_Bank_Sampeng.ms' }));
  out.push(version('bank-sampeng', 2, { root, model: JSON.parse(bank2), modelText: bank2, presentation: json('fixtures/presentation/bank-sampeng-v2.json'),
    stages: text('fixtures/stages/bank-v2.stages.json'), label: '29 Oct 2026: furniture boxes', maxScript: 'bank_test/Bangkok_Bank_Sampeng.ms' }));
  const suite = text('fixtures/models/suite.model.json');
  meta(root, 'presidential-suite', JSON.parse(suite), [1]);
  out.push(version('presidential-suite', 1, { root, model: JSON.parse(suite), modelText: suite, presentation: json('fixtures/presentation/presidential-suite.json'),
    stages: null, label: '29 Oct 2026: furniture boxes', maxScript: 'presidential_test/Presidential_Suite.ms',
    stamp: { stamp: sha1(readFileSync(path.join(APP, '..', 'presidential_test/src/pres2_model.json'))).slice(0, 12), source: 'source/pres2_model.json' } }));
  const house = text('fixtures/models/house.model.json');
  meta(root, 'sukhumvit-house', JSON.parse(house), [1]);
  out.push(version('sukhumvit-house', 1, { root, model: JSON.parse(house), modelText: house, presentation: json('fixtures/presentation/sukhumvit-house.json'),
    stages: null, label: '29 Oct 2026: openings and furniture boxes' }));
  const hotel = text('fixtures/models/hotel.model.json');
  meta(root, 'hotel-lobby', JSON.parse(hotel), [1]);
  out.push(version('hotel-lobby', 1, { root, model: JSON.parse(hotel), modelText: hotel, presentation: json('fixtures/presentation/hotel-lobby.json'), stages: null,
    label: '2 Nov 2026: read from two plan pictures', maxScript: 'hotel_test/Hotel_Lobby.ms', assets: [
      { name: 'floor1_plan.png', role: 'plan-picture', floor: 'F1', file: 'fixtures/pictures/floor1_plan.png', mediaType: 'image/png', modelRef: '../source/floor1_plan.png' },
      { name: 'floor2_plan.png', role: 'plan-picture', floor: 'F2', file: 'fixtures/pictures/floor2_plan.png', mediaType: 'image/png', modelRef: '../source/floor2_plan.png' },
    ] }));
  const hostile = writeStore(path.join(root, '.hostile')).versions.find(v => v.projectId === 'hostile-names')!;
  mkdirSync(path.join(root, 'projects', 'hostile-names'), { recursive: true });
  for (const f of ['meta.json']) copyFileSync(path.join(root, '.hostile', 'projects', 'hostile-names', f), path.join(root, 'projects', 'hostile-names', f));
  mkdirSync(path.join(root, 'projects', 'hostile-names', 'versions', '1', 'assets'), { recursive: true });
  for (const f of ['model.json', 'version.json']) copyFileSync(path.join(hostile.dir, f), path.join(root, 'projects', 'hostile-names', 'versions', '1', f));
  rmSync(path.join(root, '.hostile'), { recursive: true, force: true });
  out.push({ ...hostile, dir: path.join(root, 'projects', 'hostile-names', 'versions', '1') });
  return { root, versions: out };
}

/** A template like the built one: the two markers once each, around a data element, with a tail after it. */
export const HAND_TEMPLATE = '<!doctype html><html><head><meta charset="utf-8"><meta name="model-data" content="__WTV_STAMP__"><title>Walkthrough</title>'
  + '<script type="module">/* the viewer */</script></head><body><div id="wtv-app"></div><script type="application/json" id="wtv-data">__WTV_DATA__</script>'
  + '<p>the tail</p></body></html>\n';
