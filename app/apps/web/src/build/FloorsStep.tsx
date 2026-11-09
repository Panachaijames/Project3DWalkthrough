// Step "Floors" (docs/upload/DESIGN.md U-2 5c, U-9, U-14.3): each source's sheet with the area proposals and the level
// tags marked; the floor list (add, remove, reorder); per floor: key, name, source, area (whole file, or a box: a
// proposal clicked or a box drawn on the sheet; pad and match under "Advanced", with one line of help each), level (typed,
// or picked from the list of ALL the source's level tags with their labels, each marked on the sheet when hovered),
// wall height (default: next level - this level; the top floor typed), slab thickness, door head / window sill / head,
// alignment (auto, grid, origin, two points picked on both sheets); "propose areas again on the wall layers" (in the
// browser, on the decoded plan); the project details (office, names, photo name, Max prefix and file name, exported
// from) and the project defaults. Locked while a source is read again (U-7.4). Names from the drawing are text.
import { ArrowDown, ArrowUp, Crosshair, Plus, SquareDashed, Trash2 } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { proposeAreas, PlanCanvas } from '@/plan';
import type { Vec2 } from '@walkthrough/viewer';
import type { AreaProposal, Bbox, BuildSettings, Flag, FloorAlign, FloorArea, FloorSetup, LevelTag } from '@/upload/contracts';
import { cn } from '@/lib/utils';
import { useBuildContext, useDrawing, useLockText, usePlan } from './context';
import { FieldRow, NativeSelect, NumberField, TextField } from './fields';
import { OfficeSelect } from './OfficeSelect';
import { WALL_ROLES } from './roles';
import {
  addFloor, boxArea, defaultWallHeight, floorIssues, moveFloor, namingIssues, removeFloor, roleOf, round3, setDefaults,
  setOffice, setProject, updateFloor, DEFAULT_MATCH, DEFAULT_PAD,
} from './settingsEdit';

export const PAD_HELP = 'how far outside the box a line may reach';
export const MATCH_HELP = 'all: a line must lie wholly inside; any: one point inside is enough, for a plan that touches its neighbours';

type PickTarget = { floor: number; pair: 0 | 1; side: 0 | 1 };
type Tool = { kind: 'pan' } | { kind: 'box'; floor: number } | { kind: 'point'; target: PickTarget };

const fmtLevel = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}`;
const size = (b: Bbox) => `${round3(b[2] - b[0])} x ${round3(b[3] - b[1])} m`;

function sortedTags(tags: readonly LevelTag[]): LevelTag[] {
  return [...tags].sort((a, b) => a.value - b.value || a.y - b.y || a.x - b.x);
}

/** A proposal of the reader or of "propose again" as the list shows it. */
interface Proposal { id: string; bbox: Bbox; looks: AreaProposal['looks'] | 'walls'; items: number | null }

function FloorCard({ index, floor, settings, editable, selected, onSelect, tool, setTool, onPreview, onMark, proposals }: {
  index: number; floor: FloorSetup; settings: BuildSettings; editable: boolean; selected: boolean; onSelect: () => void;
  tool: Tool; setTool: (t: Tool) => void; onPreview: (a: FloorArea | null) => void; onMark: (t: LevelTag | null) => void;
  proposals: Proposal[];
}) {
  const { change, detail } = useBuildContext();
  const src = detail.sources.find(s => s.sha1 === floor.source);
  const drawing = useDrawing(src);
  const tags = useMemo(() => sortedTags(drawing.data?.levelTags ?? []), [drawing.data]);
  const set = (patch: Partial<FloorSetup>) => change(updateFloor(index, patch));
  const def = defaultWallHeight(settings.floors, index);
  const isTop = index === settings.floors.length - 1;
  const area = floor.area;
  const align = floor.align;
  const pickPoint = (pair: 0 | 1, side: 0 | 1) => setTool({ kind: 'point', target: { floor: index, pair, side } });
  const picking = (pair: 0 | 1, side: 0 | 1) => tool.kind === 'point' && tool.target.floor === index && tool.target.pair === pair && tool.target.side === side;
  const pairs = align.method === 'points' ? align.pairs : null;
  const showPoint = (p: Vec2 | undefined) => (p ? `${round3(p[0])}, ${round3(p[1])}` : 'not picked');

  return (
    <article
      className={cn('grid gap-3 rounded-lg border bg-background p-4', selected && 'ring-2 ring-primary/40')}
      data-testid="floor-card"
      data-index={index}
      data-key={floor.key}
      onFocusCapture={onSelect}
      onClick={onSelect}
    >
      <header className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">{`Floor ${index + 1}`}</h3>
        <div className="flex items-center gap-1">
          <Button size="icon" variant="ghost" className="size-7" disabled={!editable || index === 0} onClick={() => change(moveFloor(index, -1))} aria-label="Move up" data-testid="floor-up"><ArrowUp /></Button>
          <Button size="icon" variant="ghost" className="size-7" disabled={!editable || isTop} onClick={() => change(moveFloor(index, 1))} aria-label="Move down" data-testid="floor-down"><ArrowDown /></Button>
          <Button size="icon" variant="ghost" className="size-7" disabled={!editable || settings.floors.length <= 1} onClick={() => change(removeFloor(index))} aria-label="Remove the floor" data-testid="remove-floor"><Trash2 /></Button>
        </div>
      </header>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <TextField label="Key" value={floor.key} disabled={!editable} onCommit={v => set({ key: v.trim() })} testId="floor-key" />
        <TextField label="Name" value={floor.name} disabled={!editable} onCommit={v => set({ name: v })} testId="floor-name" className="col-span-1 md:col-span-2" />
        <FieldRow label="Source">
          <NativeSelect value={floor.source} disabled={!editable} onChange={e => set({ source: e.target.value })} data-testid="floor-source">
            {settings.sources.map(s => <option key={s.sha1} value={s.sha1}>{s.name}</option>)}
            {!settings.sources.some(s => s.sha1 === floor.source) && <option value={floor.source}>(no source)</option>}
          </NativeSelect>
        </FieldRow>
      </div>

      <fieldset className="grid gap-2" data-testid="floor-area" data-kind={area.kind}>
        <legend className="text-xs font-medium text-muted-foreground">Area</legend>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <label className="flex items-center gap-1.5">
            <input type="radio" name={`area-${index}`} checked={area.kind === 'wholeFile'} disabled={!editable} onChange={() => set({ area: { kind: 'wholeFile' } })} data-testid="area-whole" />
            The whole file
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="radio" name={`area-${index}`} checked={area.kind === 'box'} disabled={!editable} data-testid="area-box"
              onChange={() => set({ area: boxArea(proposals[0]?.bbox ?? [0, 0, 0, 0]) })}
            />
            A box on the sheet
          </label>
          {area.kind === 'box' && (
            <Button size="sm" variant={tool.kind === 'box' && tool.floor === index ? 'default' : 'outline'} disabled={!editable} onClick={() => setTool(tool.kind === 'box' && tool.floor === index ? { kind: 'pan' } : { kind: 'box', floor: index })} data-testid="area-draw">
              <SquareDashed aria-hidden="true" />
              {tool.kind === 'box' && tool.floor === index ? 'Drag a box on the sheet...' : 'Draw a box'}
            </Button>
          )}
        </div>
        {area.kind === 'box' && (
          <>
            <div className="flex flex-wrap items-end gap-2">
              {(['x0', 'y0', 'x1', 'y1'] as const).map((k, i) => (
                <NumberField key={k} label={k} value={area.bbox[i]!} disabled={!editable} testId={`box-${k}`}
                  onCommit={v => { const b = [...area.bbox] as Bbox; b[i] = v ?? 0; set({ area: { ...area, bbox: b } }); }} />
              ))}
            </div>
            {proposals.length > 0 && (
              <div className="flex flex-wrap gap-1" data-testid="area-proposals">
                {proposals.map(p => (
                  <Button key={p.id} size="sm" variant="outline" disabled={!editable} data-testid="area-proposal" data-id={p.id}
                    onMouseEnter={() => onPreview(boxArea(p.bbox, area.pad, area.match))} onMouseLeave={() => onPreview(null)}
                    onClick={() => set({ area: boxArea(p.bbox, area.pad, area.match) })}>
                    {`${p.id} (${p.looks}, ${size(p.bbox)})`}
                  </Button>
                ))}
              </div>
            )}
            <details className="text-sm" data-testid="area-advanced">
              <summary className="cursor-pointer text-xs text-muted-foreground">Advanced</summary>
              <div className="mt-2 grid gap-3 md:grid-cols-2">
                <NumberField label="Pad" help={PAD_HELP} value={area.pad} disabled={!editable} testId="area-pad" onCommit={v => set({ area: { ...area, pad: v ?? DEFAULT_PAD } })} />
                <FieldRow label="Match" help={MATCH_HELP}>
                  <NativeSelect value={area.match} disabled={!editable} data-testid="area-match" onChange={e => set({ area: { ...area, match: e.target.value === 'any' ? 'any' : 'all' } })}>
                    <option value="all">all</option>
                    <option value="any">any</option>
                  </NativeSelect>
                </FieldRow>
              </div>
            </details>
          </>
        )}
      </fieldset>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <NumberField label="Level" value={floor.level} disabled={!editable} testId="floor-level" onCommit={v => set({ level: v ?? 0 })} />
        <div className="grid gap-1">
          <NumberField
            label="Wall height"
            value={floor.wallHeight > 0 ? floor.wallHeight : null}
            allowEmpty
            disabled={!editable}
            testId="floor-wall-height"
            placeholder={def !== null ? String(def) : 'type it'}
            onCommit={v => set({ wallHeight: v ?? 0 })}
          />
          {def !== null && floor.wallHeight !== def && (
            <Button size="sm" variant="link" className="h-auto justify-start p-0 text-xs" disabled={!editable} onClick={() => set({ wallHeight: def })} data-testid="use-default-height">
              {`Use ${def} m (to the next level)`}
            </Button>
          )}
          {isTop && <p className="text-xs text-muted-foreground">The top floor's wall height is typed.</p>}
        </div>
        <NumberField label="Slab thickness" value={floor.slabThickness} allowEmpty placeholder={String(settings.defaults.slabThickness)} disabled={!editable} testId="floor-slab" onCommit={v => set({ slabThickness: v })} />
        <NumberField label="Door head" value={floor.doorHead} allowEmpty placeholder={String(settings.defaults.doorHead)} disabled={!editable} testId="floor-door-head" onCommit={v => set({ doorHead: v })} />
        <NumberField label="Window sill" value={floor.windowSill} allowEmpty placeholder={String(settings.defaults.windowSill)} disabled={!editable} testId="floor-window-sill" onCommit={v => set({ windowSill: v })} />
        <NumberField label="Window head" value={floor.windowHead} allowEmpty placeholder={String(settings.defaults.windowHead)} disabled={!editable} testId="floor-window-head" onCommit={v => set({ windowHead: v })} />
      </div>

      <details className="text-sm" data-testid="level-tags">
        <summary className="cursor-pointer text-xs text-muted-foreground">
          {tags.length ? `Pick the level from the drawing's level tags (${tags.length})` : 'This drawing has no level tags: type the level'}
        </summary>
        {tags.length > 0 && (
          <ul className="mt-2 grid max-h-48 gap-0.5 overflow-auto">
            {tags.map((t, i) => (
              <li key={i}>
                <button
                  type="button"
                  className="w-full truncate rounded px-2 py-0.5 text-left text-xs hover:bg-accent disabled:opacity-50"
                  disabled={!editable}
                  data-testid="level-tag"
                  data-value={t.value}
                  onMouseEnter={() => onMark(t)}
                  onMouseLeave={() => onMark(null)}
                  onFocus={() => onMark(t)}
                  onBlur={() => onMark(null)}
                  onClick={() => set({ level: round3(t.value) })}
                >
                  <span className="font-mono">{fmtLevel(t.value)}</span>
                  {t.label && <span>{` · ${t.label}`}</span>}
                  <span className="text-muted-foreground">{` · ${t.text} on ${t.layer}`}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </details>

      {index > 0 && (
        <div className="grid gap-2" data-testid="floor-align">
          <FieldRow label="Line up with the first floor" help={align.method === 'auto' ? 'grid when two grid lines are shared, else origin' : undefined}>
            <NativeSelect
              value={align.method}
              disabled={!editable}
              data-testid="align-method"
              onChange={e => {
                const m = e.target.value as FloorAlign['method'];
                set({ align: m === 'points' ? { method: 'points', pairs: [[[0, 0], [0, 0]], [[0, 0], [0, 0]]] } : { method: m } });
              }}
            >
              <option value="auto">auto</option>
              <option value="grid">grid lines</option>
              <option value="origin">the drawing origin</option>
              <option value="points">two points</option>
            </NativeSelect>
          </FieldRow>
          {pairs && (
            <div className="grid gap-1 text-xs">
              {([0, 1] as const).map(pair => (
                <div key={pair} className="flex flex-wrap items-center gap-2">
                  <span className="w-14 font-medium">{`Point ${pair + 1}`}</span>
                  {([0, 1] as const).map(side => (
                    <Button key={side} size="sm" variant={picking(pair, side) ? 'default' : 'outline'} disabled={!editable} data-testid={`align-pick-${pair}-${side}`}
                      onClick={() => (picking(pair, side) ? setTool({ kind: 'pan' }) : pickPoint(pair, side))}>
                      <Crosshair aria-hidden="true" />
                      {`${side === 0 ? 'on the first floor' : 'on this floor'}: ${showPoint(pairs[pair][side])}`}
                    </Button>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </article>
  );
}

function ProjectDetails({ settings, editable }: { settings: BuildSettings; editable: boolean }) {
  const { change } = useBuildContext();
  const p = settings.project;
  const d = settings.defaults;
  const issues = namingIssues(settings);
  const bad = (path: string) => issues.some(i => i.path === path);
  return (
    <section className="grid gap-3 rounded-lg border bg-background p-4" data-testid="project-details">
      <h3 className="text-sm font-semibold">Project details</h3>
      <OfficeSelect mode="settings" disabled={!editable} value={{ office: settings.office, newOfficeName: null }} onChange={v => change(setOffice(v.office))} />
      <div className="grid gap-3 md:grid-cols-2">
        <TextField label="Name" value={p.name} disabled={!editable} onCommit={v => change(setProject({ name: v }))} testId="project-name" />
        <TextField label="Short name" value={p.shortName} disabled={!editable} onCommit={v => change(setProject({ shortName: v }))} testId="project-short-name" />
        <TextField label="Project no" value={p.projectNo ?? ''} disabled={!editable} onCommit={v => change(setProject({ projectNo: v.trim() || null }))} testId="project-no" />
        <TextField label="Exported from" help="e.g. Revit; only quoted in texts" value={p.exportedFrom ?? ''} disabled={!editable} onCommit={v => change(setProject({ exportedFrom: v.trim() || null }))} testId="exported-from" />
        <TextField label="Photo name" value={p.photoName} invalid={bad('project/photoName')} disabled={!editable} onCommit={v => change(setProject({ photoName: v.trim() }))} testId="photo-name" />
        <TextField label="Max prefix" value={p.maxPrefix} invalid={bad('project/maxPrefix')} disabled={!editable} onCommit={v => change(setProject({ maxPrefix: v.trim().toUpperCase() }))} testId="max-prefix" />
        <TextField label="Max file name" value={p.maxFileName} invalid={bad('project/maxFileName')} disabled={!editable} onCommit={v => change(setProject({ maxFileName: v.trim() }))} testId="max-file-name" />
      </div>
      <h4 className="text-xs font-semibold text-muted-foreground">Project defaults</h4>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3" data-testid="project-defaults">
        <NumberField label="Door head" value={d.doorHead} disabled={!editable} testId="default-door-head" onCommit={v => change(setDefaults({ doorHead: v ?? d.doorHead }))} />
        <NumberField label="Window sill" value={d.windowSill} disabled={!editable} testId="default-window-sill" onCommit={v => change(setDefaults({ windowSill: v ?? d.windowSill }))} />
        <NumberField label="Window head" value={d.windowHead} disabled={!editable} testId="default-window-head" onCommit={v => change(setDefaults({ windowHead: v ?? d.windowHead }))} />
        <NumberField label="Railing height" value={d.railingHeight} disabled={!editable} testId="default-railing" onCommit={v => change(setDefaults({ railingHeight: v ?? d.railingHeight }))} />
        <NumberField label="Slab thickness" value={d.slabThickness} disabled={!editable} testId="default-slab" onCommit={v => change(setDefaults({ slabThickness: v ?? d.slabThickness }))} />
        <NumberField label="Single-line height" value={d.singleLineHeight} disabled={!editable} testId="default-single-line" onCommit={v => change(setDefaults({ singleLineHeight: v ?? d.singleLineHeight }))} />
      </div>
      {issues.length > 0 && <ul className="text-xs text-destructive">{issues.map(i => <li key={i.path}>{i.message}</li>)}</ul>}
    </section>
  );
}

export function FloorsStep() {
  const { settings, editable: canEdit, detail, change } = useBuildContext();
  const lock = useLockText();
  const editable = canEdit && !lock;
  const [current, setCurrent] = useState(0);
  const [tool, setTool] = useState<Tool>({ kind: 'pan' });
  const [preview, setPreview] = useState<FloorArea | null>(null);
  const [mark, setMark] = useState<LevelTag | null>(null);
  const [again, setAgain] = useState<Record<string, Bbox[]>>({});
  const floors = settings?.floors ?? [];
  const floor = floors[Math.min(current, Math.max(0, floors.length - 1))];
  // the sheet shows the floor being worked on, or the first floor's when a point is picked on it
  const sheetSha1 = tool.kind === 'point' && tool.target.side === 0 ? floors[0]?.source : floor?.source;
  const sheetSrc = detail.sources.find(s => s.sha1 === sheetSha1);
  const { plan, loading } = usePlan(sheetSrc);
  const drawing = useDrawing(sheetSrc);

  if (!settings) return <p className="text-sm text-muted-foreground" data-testid="floors-step">Reading the drawings...</p>;
  const issues = floorIssues(settings);

  const proposalsFor = (sha1: string | undefined): Proposal[] => {
    if (!sha1) return [];
    const fromReader = sha1 === sheetSha1 ? (drawing.data?.areas ?? []).map(a => ({ id: a.id, bbox: a.bbox, looks: a.looks, items: a.items })) : [];
    const fromWalls = (again[sha1] ?? []).map((b, i) => ({ id: `w${i + 1}`, bbox: b, looks: 'walls' as const, items: null }));
    return [...fromReader, ...fromWalls];
  };

  const markFlags: Flag[] = mark ? [{
    id: 'mark:level', kind: 'alignment', floor: null, severity: 'info', title: mark.label ?? mark.text, detail: mark.text,
    at: [mark.x, mark.y], bbox: null, ref: {},
  }] : [];
  const pickedFlags: Flag[] = [];
  floors.forEach((f, i) => {
    if (f.align.method !== 'points') return;
    f.align.pairs.forEach((pair, pi) => pair.forEach((p, side) => {
      const onSheet = side === 0 ? floors[0]?.source : f.source;
      if (onSheet === sheetSha1 && (p[0] !== 0 || p[1] !== 0)) {
        pickedFlags.push({ id: `mark:point:${i}:${pi}:${side}`, kind: 'alignment', floor: null, severity: 'info', title: `Point ${pi + 1}`, detail: '', at: p, bbox: null, ref: {} });
      }
    }));
  });
  const focus: Bbox | null = mark ? [mark.x - 4, mark.y - 4, mark.x + 4, mark.y + 4] : null;

  const onBox = (b: Bbox) => {
    if (tool.kind !== 'box') return;
    const f = floors[tool.floor];
    if (!f) return;
    const pad = f.area.kind === 'box' ? f.area.pad : DEFAULT_PAD;
    const match = f.area.kind === 'box' ? f.area.match : DEFAULT_MATCH;
    change(updateFloor(tool.floor, { area: boxArea(b, pad, match) }));
    setTool({ kind: 'pan' });
  };
  const onPick = (p: Vec2) => {
    if (tool.kind !== 'point') return;
    const { floor: fi, pair, side } = tool.target;
    const f = floors[fi];
    if (!f || f.align.method !== 'points') return;
    const pairs = f.align.pairs.map(x => [x[0], x[1]]) as [[Vec2, Vec2], [Vec2, Vec2]];
    pairs[pair][side] = [round3(p[0]), round3(p[1])];
    change(updateFloor(fi, { align: { method: 'points', pairs } }));
    setTool({ kind: 'pan' });
  };
  const proposeAgain = () => {
    if (!plan || !sheetSha1) return;
    const walls = new Set<number>();
    plan.layers.forEach((n, i) => { if (WALL_ROLES.has(roleOf(settings, n))) walls.add(i); });
    setAgain(a => ({ ...a, [sheetSha1]: proposeAreas(plan, walls) }));
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]" data-testid="floors-step">
      <section className="grid content-start gap-3">
        {lock && (
          <Alert data-testid="floors-locked"><AlertDescription>{lock}</AlertDescription></Alert>
        )}
        {floors.map((f, i) => (
          <FloorCard
            key={i}
            index={i}
            floor={f}
            settings={settings}
            editable={editable}
            selected={i === current}
            onSelect={() => setCurrent(i)}
            tool={tool}
            setTool={t => { setTool(t); if (t.kind === 'box') setCurrent(t.floor); if (t.kind === 'point') setCurrent(t.target.floor); }}
            onPreview={setPreview}
            onMark={setMark}
            proposals={proposalsFor(f.source)}
          />
        ))}
        <div>
          <Button variant="outline" disabled={!editable} onClick={() => { change(addFloor()); setCurrent(floors.length); }} data-testid="add-floor">
            <Plus aria-hidden="true" />
            Add a floor
          </Button>
        </div>
        {issues.length > 0 && (
          <ul className="grid gap-0.5 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive" data-testid="floor-issues">
            {issues.map(i => <li key={i.path + i.message}>{i.message}</li>)}
          </ul>
        )}
        <ProjectDetails settings={settings} editable={editable} />
      </section>

      <section className="grid content-start gap-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="truncate text-sm font-medium" data-testid="floors-sheet-name">{sheetSrc?.name ?? ''}</p>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" disabled={!plan} onClick={proposeAgain} data-testid="propose-again">Propose areas again on the wall layers</Button>
          </div>
        </div>
        {tool.kind !== 'pan' && (
          <p className="text-xs font-medium" data-testid="floors-tool">
            {tool.kind === 'box' ? 'Drag a box round the floor\'s plan.' : `Click the point ${tool.target.side === 0 ? 'on the first floor\'s sheet' : 'on this floor\'s sheet'}.`}
            <Button size="sm" variant="link" className="h-auto p-0 pl-2 text-xs" onClick={() => setTool({ kind: 'pan' })}>Stop</Button>
          </p>
        )}
        <div className="h-[520px] overflow-hidden rounded-lg border bg-white" data-testid="floors-canvas">
          {plan ? (
            <PlanCanvas
              plan={plan}
              roleOf={i => roleOf(settings, plan.layers[i] ?? '')}
              area={preview ?? (floor && floor.source === sheetSha1 ? floor.area : null)}
              flags={[...markFlags, ...pickedFlags]}
              focus={focus}
              selected={new Set()}
              setAside={new Set()}
              tool={tool.kind === 'box' ? 'draw-box' : tool.kind === 'point' ? 'pick-point' : 'pan'}
              onBox={onBox}
              onPick={onPick}
            />
          ) : (
            <p className="p-4 text-sm text-muted-foreground">{loading ? 'Loading the sheet...' : 'No sheet to show.'}</p>
          )}
        </div>
      </section>
    </div>
  );
}
