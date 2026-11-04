// Builder A: parsePresentation / resolvePresentation (DESIGN.md 8) and DEFAULT_REPLAY_TEXTS (7.2). The defaults; each
// fixture presentation resolved against its model and compared with what the prototype page showed (title, heading, intro
// text, accent, legend, floor buttons, tick labels, camera); idempotence; type faults refused.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import type { BuiltModel, Presentation } from '../../../src/contracts';
import { ModelError } from '../../../src/model/parse';
import { DEFAULT_REPLAY_TEXTS, parsePresentation, resolvePresentation } from '../../../src/model/presentation';
import { DEFAULT_PART_STYLES } from '../../../src/model/styles';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const json = (rel: string): any => JSON.parse(readFileSync(path.join(APP, rel), 'utf8'));
const VERSIONS = [
  { facts: 'bank-sampeng-v1', model: 'bank-v1' }, { facts: 'bank-sampeng-v2', model: 'bank-v2' },
  { facts: 'presidential-suite', model: 'suite' }, { facts: 'sukhumvit-house', model: 'house' }, { facts: 'hotel-lobby', model: 'hotel' },
];

describe('parsePresentation', () => {
  const minimal: Presentation = {
    documentTitle: 'T', heading: 'H', intro: [], accent: '#123456', legend: { layout: 'inline', items: [] },
    camera: { kind: 'fixed', position: [1, 2, 3], target: [0, 0, 0] },
  };
  it('fills the defaults that need no model: accent, creaseAngle 25, groundPlane null', () => {
    const { accent: _, ...noAccent } = minimal;
    const p = parsePresentation(noAccent);
    expect(p.accent).toBe('#2f6f8f');
    expect(p.creaseAngle).toBe(25);
    expect(p.groundPlane).toBeNull();
  });
  it('refuses missing or mistyped fields with a ModelError at JSON Pointer paths', () => {
    const bad = (p: unknown) => { try { parsePresentation(p); return []; } catch (e) { expect(e).toBeInstanceOf(ModelError); return (e as ModelError).issues.map(i => i.path); } };
    expect(bad({ ...minimal, heading: 3 })).toEqual(['/heading']);
    expect(bad({ ...minimal, camera: { kind: 'orbit' } })).toEqual(['/camera/kind']);
    expect(bad({ ...minimal, legend: { layout: 'grid', items: [] } })).toEqual(['/legend/layout']);
    expect(bad({ ...minimal, partStyles: { roof: {} } })).toEqual(['/partStyles/roof']);
    expect(bad({ ...minimal, toggles: { picture: 'yes' } })).toEqual(['/toggles/picture']);
    expect(bad({ ...minimal, intro: [{ text: 'a', bold: 'yes' }] })).toEqual(['/intro/0/bold']);
    const { documentTitle: _d, ...noTitle } = minimal;
    expect(bad(noTitle)).toEqual(['']);
    expect(bad('a string')).toEqual(['']);
  });
  it('refuses a legend colour that is not #rrggbb: the swatch is a style.background, never url(...) (fix step)', () => {
    const bad = (colour: string) => { try { parsePresentation({ ...minimal, legend: { layout: 'inline', items: [{ colour, text: 'x' }] } }); return []; } catch (e) { return (e as ModelError).issues.map(i => i.path); } };
    expect(bad('url(https://example.com/x.png)')).toEqual(['/legend/items/0/colour']);
    expect(bad('red')).toEqual(['/legend/items/0/colour']);
    expect(bad('#c0392b\n')).toEqual(['/legend/items/0/colour']);
    expect(bad('#C0392b')).toEqual([]);
  });
  it('ignores fields it does not know (a newer writer)', () => {
    expect(() => parsePresentation({ ...minimal, somethingNew: { a: 1 } })).not.toThrow();
  });
});

describe('resolvePresentation', () => {
  it.each(VERSIONS)('$facts: the fixture resolves to what the prototype page showed', ({ facts: f, model: m }) => {
    const facts = json(`fixtures/prototype/${f}.json`);
    const model = json(`fixtures/models/${m}.model.json`) as BuiltModel;
    const r = resolvePresentation(parsePresentation(json(`fixtures/presentation/${f}.json`)), model);
    expect(r.documentTitle).toBe(facts.title);
    expect(r.heading).toBe(facts.heading);
    expect(r.intro.map(x => x.text).join('')).toBe(facts.intro.text);
    expect(r.accent).toBe(facts.accent);
    expect(r.legend).toEqual(facts.legend);
    // floor buttons: 'both' -> floorButtons.all, the rest the floors' labels (one floor: no row)
    if (model.floors.length > 1) {
      const texts = facts.floorButtons.map((b: { key: string; text: string }) => b.key === 'both' ? r.floorButtons.all : r.floorButtons.labels[b.key]);
      expect(texts).toEqual(facts.floorButtons.map((b: { text: string }) => b.text));
    }
    for (const t of facts.ticks as { id: 'plates' | 'glass' | 'rooms' | 'single' | 'picture'; label: string; checked: boolean; title: string | null }[]) {
      expect(r.labels[t.id]).toBe(t.label);
      expect(r.toggles[t.id]).toBe(t.checked);
      if (t.title) expect(r.labels.pictureTitle).toBe(t.title);
    }
    expect(r.camera.far).toBe(facts.scene.camera.far);
    if (r.camera.kind === 'fixed') {
      expect(r.camera.position).toEqual(facts.scene.camera.position.map((v: number) => Math.round(v * 1e6) / 1e6));
      expect(r.camera.target).toEqual(facts.scene.camera.target);
    }
  });

  it('merges the house partStyles over the defaults and keeps everything else of the style', () => {
    const r = resolvePresentation(parsePresentation(json('fixtures/presentation/sukhumvit-house.json')), json('fixtures/models/house.model.json'));
    expect(r.partStyles.glass).toEqual({ ...DEFAULT_PART_STYLES.glass, color: '#8fd0e0', edge: '#4f9fb3', opacity: 0.35, roughness: 0.85, edgeOpacity: 0.6, renderOrder: 0 });
    expect(r.partStyles.pane.renderOrder).toBe(0);
    expect(r.partStyles.single).toEqual({ ...DEFAULT_PART_STYLES.single, opacity: 0.9 });
    expect(r.partStyles.wall).toEqual(DEFAULT_PART_STYLES.wall);
    expect(r.creaseAngle).toBe(40);
    expect(r.groundPlane).toEqual({ size: [80, 50], colour: '#dfe3e0' });
    expect(r.floorButtons).toEqual({ all: 'Both floors', labels: { ground: 'Ground', upper: 'Upper' } });
  });

  it('defaults: Both floors, floor names, the tick labels, far 600, every kind styled, all ticks on but the picture', () => {
    const model = json('fixtures/models/mini.model.json') as BuiltModel;
    const r = resolvePresentation(parsePresentation({ documentTitle: 'T', heading: 'H', intro: [], legend: { layout: 'lines', items: [] },
      camera: { kind: 'fitSlabs', away: [1, 2, 3], targetY: 2.5, panForPanel: true } }), model);
    expect(r.floorButtons).toEqual({ all: 'Both floors', labels: Object.fromEntries(model.floors.map(f => [f.key, f.name])) });
    expect(r.labels).toEqual({ plates: 'Floor plates', glass: 'Glass', rooms: 'Room names', single: 'Single-line items', picture: 'Plan picture',
      pictureTitle: "Each floor's source picture, laid on its floor plate at the model's scale and position" });
    expect(r.camera).toEqual({ kind: 'fitSlabs', away: [1, 2, 3], targetY: 2.5, panForPanel: true, far: 600 });
    expect(Object.keys(r.partStyles).sort()).toEqual(Object.keys(DEFAULT_PART_STYLES).sort());
    expect(r.toggles).toEqual({ plates: true, glass: true, rooms: true, single: true, picture: false });
  });

  it('is idempotent: a resolved presentation resolves to itself', () => {
    for (const { facts: f, model: m } of VERSIONS) {
      const model = json(`fixtures/models/${m}.model.json`);
      const once = resolvePresentation(parsePresentation(json(`fixtures/presentation/${f}.json`)), model);
      const twice = resolvePresentation(parsePresentation(once), model);
      expect(twice).toEqual(once);
    }
  });
});

describe('DEFAULT_REPLAY_TEXTS (7.2: the bank page values)', () => {
  it('are the bank page values', () => {
    expect(DEFAULT_REPLAY_TEXTS.layersTitle).toBe('How the drawing was read');
    expect(Object.values(DEFAULT_REPLAY_TEXTS.stepTitles)).toEqual(['Read the drawing', 'Sort the layers', 'Line up the levels',
      'Find the wall faces', 'Merge, cut the openings', 'Raise the walls', 'Floors, stairs, room names']);
    expect(DEFAULT_REPLAY_TEXTS.colors).toEqual({ wall: '#7a6650', glass: '#2f86a8', door: '#c0702a', stair: '#2e8b47', railing: '#9b3fa0',
      ink: '#3b4148', faint: '#a4acb4', piece: '#cfc2b0', pieceEdge: '#8a7a66', run: '#e3ddd3', runEdge: '#6f675d' });
  });
  it('match the bank stages captured from the page (step titles)', () => {
    const facts = json('fixtures/prototype/bank-sampeng-v2.json');
    expect(facts.card.steps.map((s: { title: string }) => s.title)).toEqual(Object.values(DEFAULT_REPLAY_TEXTS.stepTitles));
    expect(facts.card.layersTitle).toBe(DEFAULT_REPLAY_TEXTS.layersTitle);
  });
});
