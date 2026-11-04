// Shared bits of C's unit tests: fixture paths and loaders. Owner: builder C.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { BuiltModel, Presentation } from '../../../src/contracts';

export const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
export const FURN = path.join(APP, 'packages/viewer/test/fixtures/furniture');

export const readText = (p: string) => readFileSync(p, 'utf8');
export const loadModel = (name: string) => JSON.parse(readText(path.join(APP, 'fixtures/models', `${name}.model.json`))) as BuiltModel;
export const loadPresentation = (name: string) => JSON.parse(readText(path.join(APP, 'fixtures/presentation', `${name}.json`))) as Presentation;
/** A furniture/test_boxes.mjs variant of this folder (not v1: straight into the helpers). */
export const loadVariant = (name: string) => JSON.parse(readText(path.join(FURN, name))) as BuiltModel;
export const golden = (name: string) => readText(path.join(FURN, name));
/** A prototype CSV of fixtures/csv (with the byte-order mark, as downloaded). */
export const csvFile = (name: string) => readFileSync(path.join(APP, 'fixtures/csv', name));
export const BOM = Buffer.from([0xef, 0xbb, 0xbf]);

/** The four furnished fixture models with their CSV names and presentations. */
export const FURNISHED = [
  { model: 'bank-v2', csv: 'bank-v2', presentation: 'bank-sampeng-v2' },
  { model: 'suite', csv: 'suite', presentation: 'presidential-suite' },
  { model: 'house', csv: 'house', presentation: 'sukhumvit-house' },
  { model: 'hotel', csv: 'hotel', presentation: 'hotel-lobby' },
] as const;

/** The typed heights of fixtures/csv/<project>-typed.csv (tools/make-csv-goldens.py), where the model has the kind. */
export function typedHeights(model: BuiltModel): Record<string, number> {
  const typed: Record<string, number> = { table: 600, seat: 300, cabinet: 1000, other: 2100 };
  const kinds = new Set((model.furnitureKinds ?? []).map(k => k.key));
  return Object.fromEntries(Object.entries(typed).filter(([k]) => kinds.has(k)));
}
