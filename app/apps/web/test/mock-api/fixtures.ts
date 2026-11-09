// Typed fixtures of the four projects (five versions) for the web app's tests (WORK_BREAKDOWN F): the version and project
// JSON is written by hand to the generated client's types (src/api/generated/types.gen.ts), from the seed table of
// DESIGN.md 9.2; the files it serves are the shared fixtures (app/fixtures: the bank and hotel models are the real v1
// files, the suite and house the provisional ones; the presentations; the bank stages; the hotel pictures; the CSVs and
// their typed goldens) and, read-only, the prototypes' own Max scripts and top views. Node only (node:fs): vitest and the
// Playwright specs import it, the app never does.
// Mock limits: the suite and the house have no stages here (there are no provisional stages fixtures, DESIGN.md 17.1),
// so their mock versions say hasStages false; the seeded store has their converted replays.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { HeightMap } from '../../../../packages/viewer/src/contracts';
import type { SourceKind } from '../../../../packages/viewer/src/contracts';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const APP_DIR = path.resolve(HERE, '../../../..');
export const PROTOTYPES_DIR = path.resolve(APP_DIR, '..');
export const FIXTURES_DIR = path.join(APP_DIR, 'fixtures');

export interface MockFile {
  /** Absolute path of the bytes served. */
  file: string;
  /** The name the API gives it. */
  name: string;
}

export interface MockVersionSource {
  projectId: string;
  version: number;
  label: string;
  /** The model source file's mtime (UTC), as the seed writes it (DESIGN.md 9.2). */
  createdAt: string;
  sourceKind: SourceKind;
  model: string;
  stages: string | null;
  presentation: string;
  /** Overrides the stamp (the suite's is its source model's); default sha1(model)[:12]. */
  stamp?: string;
  stampSource: string;
  maxScript: MockFile | null;
  thumbnail: string | null;
  pictures: (MockFile & { floor: string })[];
  /** The furniture CSV with no saved heights and the typed golden with its heights (fixtures/csv). */
  csv: { plain: string; typed: string; typedHeights: HeightMap } | null;
  /** A version saved from a build of a project made by createProject (builds.ts): the project's own names. */
  projectName?: string;
  shortName?: string;
  projectNo?: string | null;
}

const F = (...p: string[]) => path.join(FIXTURES_DIR, ...p);
const P = (...p: string[]) => path.join(PROTOTYPES_DIR, ...p);

export const MOCK_VERSIONS: MockVersionSource[] = [
  {
    projectId: 'bank-sampeng', version: 1,
    label: '27 Oct 2026: two levels, openings from the detector (before the fix round)',
    createdAt: '2026-10-27T04:31:57Z', sourceKind: 'cad',
    model: F('models', 'bank-v1.model.json'), stages: F('stages', 'bank-v1.stages.json'),
    presentation: F('presentation', 'bank-sampeng-v1.json'), stampSource: 'model.json',
    maxScript: { file: P('bank_test', 'previous_before_fix_round_2026-10-27', 'Bangkok_Bank_Sampeng.ms'), name: 'Bangkok_Bank_Sampeng.ms' },
    thumbnail: P('bank_test', 'previous_before_fix_round_2026-10-27', 'bank_topview.png'),
    pictures: [], csv: null,
  },
  {
    projectId: 'bank-sampeng', version: 2,
    label: '29 Oct 2026: furniture boxes',
    createdAt: '2026-10-29T03:24:53Z', sourceKind: 'cad',
    model: F('models', 'bank-v2.model.json'), stages: F('stages', 'bank-v2.stages.json'),
    presentation: F('presentation', 'bank-sampeng-v2.json'), stampSource: 'model.json',
    maxScript: { file: P('bank_test', 'Bangkok_Bank_Sampeng.ms'), name: 'Bangkok_Bank_Sampeng.ms' },
    thumbnail: P('bank_test', 'bank_topview.png'),
    pictures: [],
    csv: { plain: F('csv', 'bank-v2.csv'), typed: F('csv', 'bank-v2-typed.csv'), typedHeights: { table: 600, seat: 300, cabinet: 1000 } },
  },
  {
    projectId: 'presidential-suite', version: 1,
    label: '29 Oct 2026: furniture boxes',
    createdAt: '2026-10-29T05:24:22Z', sourceKind: 'cad',
    model: F('models', 'suite.model.json'), stages: null,
    presentation: F('presentation', 'presidential-suite.json'),
    stamp: 'f1b95c53eb3d', stampSource: 'source/pres2_model.json',
    maxScript: { file: P('presidential_test', 'Presidential_Suite.ms'), name: 'Presidential_Suite.ms' },
    thumbnail: P('presidential_test', 'presidential_topview.png'),
    pictures: [],
    csv: { plain: F('csv', 'suite.csv'), typed: F('csv', 'suite-typed.csv'), typedHeights: { table: 600, seat: 300, other: 2100 } },
  },
  {
    projectId: 'sukhumvit-house', version: 1,
    label: '29 Oct 2026: openings and furniture boxes',
    createdAt: '2026-10-29T05:34:39Z', sourceKind: 'cad',
    model: F('models', 'house.model.json'), stages: null,
    presentation: F('presentation', 'sukhumvit-house.json'), stampSource: 'model.json',
    maxScript: null, thumbnail: null, pictures: [],
    csv: { plain: F('csv', 'house.csv'), typed: F('csv', 'house-typed.csv'), typedHeights: { seat: 300, cabinet: 1000, other: 2100 } },
  },
  {
    projectId: 'hotel-lobby', version: 1,
    label: '2 Nov 2026: read from two plan pictures',
    createdAt: '2026-11-02T11:56:02Z', sourceKind: 'pictures',
    model: F('models', 'hotel.model.json'), stages: null,
    presentation: F('presentation', 'hotel-lobby.json'), stampSource: 'model.json',
    maxScript: { file: P('hotel_test', 'Hotel_Lobby.ms'), name: 'Hotel_Lobby.ms' },
    thumbnail: P('hotel_test', 'hotel_topview.png'),
    pictures: [
      { floor: 'F1', name: 'floor1_plan.png', file: F('pictures', 'floor1_plan.png') },
      { floor: 'F2', name: 'floor2_plan.png', file: F('pictures', 'floor2_plan.png') },
    ],
    csv: { plain: F('csv', 'hotel.csv'), typed: F('csv', 'hotel-typed.csv'), typedHeights: { table: 600, seat: 300, cabinet: 1000 } },
  },
];

const bytesCache = new Map<string, Buffer>();
/** A fixture file's bytes (cached; read-only). */
export function readBytes(file: string): Buffer {
  let b = bytesCache.get(file);
  if (!b) { b = readFileSync(file); bytesCache.set(file, b); }
  return b;
}
export const sha1 = (b: Buffer | string) => createHash('sha1').update(b).digest('hex');
export const readJson = (file: string): unknown => JSON.parse(readBytes(file).toString('utf8'));
