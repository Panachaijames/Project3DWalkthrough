// Test helpers of the replay (builder D): the shared fixtures read through node:fs, and a small replay data file made
// from a model's own parts for the projects that have no stages fixture yet (the suite's and the house's are converted
// by builder E's seed; DESIGN.md 17.1 has none provisional).
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { BuiltModel, Presentation, ReplayData, StepKey } from '../../../src/contracts';

export const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const json = <T>(rel: string): T => JSON.parse(readFileSync(path.join(APP, rel), 'utf8')) as T;

export const model = (name: string): BuiltModel => json<BuiltModel>(`fixtures/models/${name}.model.json`);
export const stages = (name: string): ReplayData => json<ReplayData>(`fixtures/stages/${name}.stages.json`);
export const presentation = (name: string): Presentation => json<Presentation>(`fixtures/presentation/${name}.json`);

export interface CardFacts {
  inputs: { floor: string; prop: 'level' | 'height'; value: string }[];
  introTitle: string; facts: string[]; layersTitle: string; layers: [string, string][];
  settings: Record<string, { level: number; height: number }>;
  steps: { key: StepKey; title: string; caption: string; t0: number; t1: number }[];
  stepList: string[];
}
/** The Build settings card as the prototype page showed it (fixtures/prototype, captured by the scaffold). */
export const card = (name: string): CardFacts => json<{ card: CardFacts }>(`fixtures/prototype/${name}.json`).card;

/** Replay data for any model (tests only): test/harness/replay/synthetic.ts stagesFor, one implementation for both. */
export { stagesFor as synthStages } from '../../harness/replay/synthetic';
