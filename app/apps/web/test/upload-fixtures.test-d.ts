// Scaffold U0 (docs/upload/WORK_BREAKDOWN.md U0 step 6; ACCEPTANCE 2.5): the upload fixtures satisfy the contract types.
// Type-level only (`npm run typecheck` compiles it with tsconfig.test.json); nothing here runs.
//
// A JSON import widens literals and tuples ("drawing-read/1" is `string`, [x, y] is `number[]`), so each fixture is
// checked against Widen<T> of its type: the same keys, nesting, optionality, nullability and value kinds, with string
// literal unions read as string and tuples as arrays. The literal values themselves are checked by the API's pydantic
// records (`node tools/run-py.mjs -m walkthrough_api.check_file <kind> <file>`). plan/*.plan.json.gz is gzip: check_file
// checks it. build-result / replay-input are the builder's internal types (contracts.py; services/builder/tests).
import type * as C from '@/upload/contracts';
import bankSettings from '../../../fixtures/upload/settings/bank.json';
import houseSettings from '../../../fixtures/upload/settings/house.json';
import suiteSettings from '../../../fixtures/upload/settings/suite.json';
import towerSettings from '../../../fixtures/upload/settings/tower.json';
import smallSettings from '../../../fixtures/upload/settings/small.json';
import office from '../../../fixtures/upload/mappings/dwp-revit.json';
import bank1Drawing from '../../../fixtures/upload/drawing/bank1.drawing.json';
import houseDrawing from '../../../fixtures/upload/drawing/sukhumvit.drawing.json';
import bank1Conversion from '../../../fixtures/upload/conversion/bank1.conversion.json';
import suiteConversion from '../../../fixtures/upload/conversion/presidential.conversion.json';
import overlay from '../../../fixtures/upload/overlay/bank.overlay.json';
import prepareJob from '../../../fixtures/upload/runs/bank-prepare/job.json';
import buildJob from '../../../fixtures/upload/runs/bank-build/job.json';
import suggestions from '../../../fixtures/upload/runs/bank-prepare/out/suggestions.json';
import proposed from '../../../fixtures/upload/runs/bank-prepare/out/proposed-settings.json';
import diff from '../../../fixtures/upload/runs/bank-build/out/diff.json';
import openings from '../../../fixtures/upload/runs/bank-build/out/openings.json';
import pieces from '../../../fixtures/upload/runs/bank-build/out/pieces.json';
import inputs from '../../../fixtures/upload/runs/bank-build/out/inputs.json';

/** T with string literals as string, number / boolean literals widened, tuples and arrays as arrays (what a JSON
 *  import's inferred type can be checked against). A Record<string, V> also takes `undefined` values: an array of JSON
 *  objects is inferred with `key?: undefined` for every key some other element has. */
export type Widen<T> =
  T extends string ? string
  : T extends number ? number
  : T extends boolean ? boolean
  : T extends null | undefined ? T
  : T extends readonly (infer E)[] ? Widen<E>[]
  : T extends object ? (string extends keyof T ? { [k: string]: Widen<T[keyof T]> | undefined }
                                               : { [K in keyof T]: Widen<T[K]> })
  : T;

export const fixtures = [
  bankSettings satisfies Widen<C.BuildSettings>,
  houseSettings satisfies Widen<C.BuildSettings>,
  suiteSettings satisfies Widen<C.BuildSettings>,
  towerSettings satisfies Widen<C.BuildSettings>,
  smallSettings satisfies Widen<C.BuildSettings>,
  proposed satisfies Widen<C.BuildSettings>,
  office satisfies Widen<C.OfficeMapping>,
  bank1Drawing satisfies Widen<C.DrawingRead>,
  houseDrawing satisfies Widen<C.DrawingRead>,
  bank1Conversion satisfies Widen<C.ConversionReport>,
  suiteConversion satisfies Widen<C.ConversionReport>,
  overlay satisfies Widen<C.BuildOverlay>,
  prepareJob satisfies Widen<C.JobRecord>,
  buildJob satisfies Widen<C.JobRecord>,
  suggestions satisfies Widen<C.LayerSuggestions>,
  diff satisfies Widen<C.BuildDiff>,
  openings satisfies Widen<C.OpeningsFile>,
  pieces satisfies Widen<C.FurniturePlacements>,
  inputs satisfies Widen<C.VersionInputs>,
];

// Widen keeps the structure: a fixture missing a required key, or with a key the type does not have, fails.
// @ts-expect-error a BuildSettings without `fixes`
export const missingKey = { ...bankSettings, fixes: undefined } satisfies Widen<C.BuildSettings>;
// @ts-expect-error an unknown key
export const extraKey = { ...bankSettings, colour: 'red' } satisfies Widen<C.BuildSettings>;
