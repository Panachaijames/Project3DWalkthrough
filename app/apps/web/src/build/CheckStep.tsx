// Step "Check" (docs/upload/DESIGN.md U-2 5e, U-12): per floor the plan with the built walls, glass, openings, furniture
// boxes and flags over it; the flag list; the diff against the previous build and the latest version. Tools: select items
// (click, shift-click, box; pick modes item / whole block / layer in a box, or by key and layer with Find) -> Set aside
// / Restore (an ItemRef with every field from the plan entry; an INSERT anchor's ref covers its subtree); an opening ->
// kind, head, sill; an outline suggestion -> wall / glass / refuse; grey furniture families -> a kind; floor heights and
// the project's heights; Rebuild (the screen keeps the last result while it runs). Keyboard: Esc clears the selection,
// Delete sets it aside. Locked while a source is read again. Keys, layers and flag texts are drawing text: text only.
// The rooms milestone (docs/rooms/DESIGN.md R-6.2, R-6.4, R-12.6; R6): the line that says which way the draft is built;
// the ticks Rooms, Floor plate, Furniture; the counts in the page; the tools Draw a line and Rooms and stairs with the
// room and stair panels; the flag cards' buttons; "Fixes on this floor" with Remove; the fixes waiting for a Rebuild
// drawn on the plan (plan/marks.ts) and marked; the set-aside tick "The floor runs past it"; the ceiling height.
import { useQuery } from '@tanstack/react-query';
import type { Vec2 } from '@walkthrough/viewer';
import { EyeOff, Hammer, Maximize2, RotateCcw, Search, X, ZoomIn, ZoomOut } from 'lucide-react';
import { useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { runBuild } from '@/api/generated/sdk.gen';
import { PlanCanvas, type DecodedPlan, type PickMode, type PlanShow } from '@/plan';
import { hasMarks, NO_MARKS, withMarks } from '@/plan/marks';
import type { Bbox, BuildDetail, BuildDiff, BuildOverlay, Flag, FlagKind, ItemRef, OpeningFix, SetAside } from '@/upload/contracts';
import { rawQueryOptions } from '@/upload/raw';
import { errorReason, formatNumber } from '@/lib/format';
import { cn } from '@/lib/utils';
import { isRunInProgress, STARTED_ELSEWHERE } from './BuildStep';
import { useBuildContext, useLockText, usePlan } from './context';
import { DiffPanel } from './DiffPanel';
import { NativeSelect, NumberField } from './fields';
import { FLAG_KIND_TEXT, FlagList, type FlagRoomsActions } from './FlagList';
import { FurnitureWords } from './FurnitureWords';
import { OpeningEditor } from './OpeningEditor';
import { CheckCounts, FixesList, RoomPanel, ShowTicks, StairPanel, type RoomTarget } from './RoomsPanels';
import { closeHereFix, fixMarks, flagFix, notDoorwayFix, outdoorsFix, pointIn, sameEnds, stairFixFor, xHoleFloorFix } from './roomsFixes';
import { RulesLine } from './RulesLine';
import { RunPanel } from './RunPanel';
import {
  addClosing, addSetAside, asideOf, closingsOf, defaultCeilingHeight, itemRef, removeClosing, restoreSetAside, roleOf, rulesOf,
  setDefaults, setFloorPast, setFurnitureWord, setOpeningFix, setOutlineEdge, setRoomFix, setRules, setStairFix, updateFloor,
} from './settingsEdit';
import { CHECK_TOOLS, TID, type CheckTool } from './testids';

/** The tool select's words (CHECK_TOOLS' order). */
export const CHECK_TOOL_TEXT: Record<CheckTool, string> = { pan: 'Pan', select: 'Select', 'draw-line': 'Draw a line', rooms: 'Rooms and stairs' };
export const DRAW_LINE_HINT = 'Draw a line: click its two ends (each snaps to a drawn corner within 6 px); Esc drops the first end.';
export const ROOMS_TOOL_HINT = 'Rooms and stairs: click a stair, one of the app\'s dashed closings, or a room; or a place with no room.';

export const TYPE_NAMES = ['line', 'closed line', 'solid fill', 'pattern fill', 'text', 'block'];
const FIND_LIMIT = 50;
export const PICK_MODES: { mode: PickMode; text: string }[] = [
  { mode: 'item', text: 'One item' },
  { mode: 'block', text: 'The whole block' },
  { mode: 'layer-in-box', text: 'A layer in a box' },
];

/** key -> entry index (the first entry of a key: a hatch's loops share it). */
export function keyIndex(plan: DecodedPlan): Map<string, number> {
  const m = new Map<string, number>();
  for (let i = 0; i < plan.count; i++) { const k = plan.keyAt(i); if (!m.has(k)) m.set(k, i); }
  return m;
}

/** The innermost INSERT anchor (type 5) whose subtree holds this key (by key prefix, U-12.1), or the key itself. */
export function blockOf(key: string, index: Map<string, number>, plan: DecodedPlan): string {
  const i = index.get(key);
  if (i !== undefined && plan.typeAt(i) === 5) return key;
  const parts = key.split('/');
  for (let n = parts.length - 1; n >= 1; n--) {
    const k = parts.slice(0, n).join('/');
    const j = index.get(k);
    if (j !== undefined && plan.typeAt(j) === 5) return k;
  }
  return key;
}

/** The entry of exactly this key first (if any), then entries whose key starts with the query or whose layer contains it
 *  (case-insensitive), in drawing order, at most `limit`. */
export function findItems(plan: DecodedPlan, query: string, limit = FIND_LIMIT, index?: Map<string, number>): { key: string; layer: string; type: number }[] {
  const q = query.trim();
  if (!q) return [];
  const lq = q.toLowerCase();
  const out: { key: string; layer: string; type: number }[] = [];
  const seen = new Set<string>();
  const exact = index?.get(q);
  if (exact !== undefined) {
    out.push({ key: q, layer: plan.layers[plan.layerAt(exact)] ?? '', type: plan.typeAt(exact) });
    seen.add(q);
  }
  for (let i = 0; i < plan.count && out.length < limit; i++) {
    const key = plan.keyAt(i);
    if (seen.has(key)) continue;
    const layer = plan.layers[plan.layerAt(i)] ?? '';
    if (key.startsWith(q) || layer.toLowerCase().includes(lq)) {
      seen.add(key);
      out.push({ key, layer, type: plan.typeAt(i) });
    }
  }
  return out;
}

const bboxAround = (f: Flag): Bbox | null => f.bbox ?? (f.at ? [f.at[0] - 3, f.at[1] - 3, f.at[0] + 3, f.at[1] + 3] : null);

/** A grey-furniture flag's piece count: the title's own ending ('<family>: 3 grey boxes') or the detail's 'so its 3
 *  pieces are grey'; never the first number of a sentence that starts with the family name (UR, V2-7: TF2092P showed
 *  '2092 pieces'). null when neither says it. */
export function greyCount(f: Pick<Flag, 'title' | 'detail'>): number | null {
  const t = /: (\d+) grey box(?:es)?$/.exec(f.title);
  if (t) return Number(t[1]);
  const d = /so its (\d+) pieces? (?:are|is) grey/.exec(f.detail);
  return d ? Number(d[1]) : null;
}

/** The canvas's controls, said once above it (UR, V2-13: nothing on the screen said how the canvas works). */
export const CANVAS_HINT = 'Wheel: zoom · drag: select a box (Shift adds, Alt takes what it touches) · middle button or the Pan tool: move · F: fit';

/** RR (S1): the plan column: sticky under the app bar (h-12) on a wide screen, scrolling by itself when taller than
 *  the window. */
export const PLAN_COLUMN = 'grid min-w-0 content-start gap-2 xl:sticky xl:top-14 xl:z-10 xl:max-h-[calc(100svh-4.5rem)] xl:self-start xl:overflow-y-auto';

/** The set-aside list: rows of this height, this many pixels shown, windowed beyond WINDOW_ASIDE rows (UR, V3-5). */
export const ASIDE_ROW = 26;
export const ASIDE_VIEW = 160;
export const WINDOW_ASIDE = 100;

function SetAsideList({ refs, editable, onRestore, onFloorPast }: {
  refs: SetAside[]; editable: boolean; onRestore: (key: string) => void; onFloorPast?: (key: string, on: boolean) => void;
}) {
  const [top, setTop] = useState(0);
  const windowed = refs.length > WINDOW_ASIDE;
  const first = windowed ? Math.max(0, Math.floor(top / ASIDE_ROW) - 5) : 0;
  const last = windowed ? Math.min(refs.length, Math.ceil((top + ASIDE_VIEW) / ASIDE_ROW) + 5) : refs.length;
  return (
    <div className="overflow-auto text-xs" style={{ maxHeight: ASIDE_VIEW }} onScroll={e => setTop((e.target as HTMLDivElement).scrollTop)}
      data-testid="set-aside-scroll" data-windowed={windowed ? '' : undefined}>
      <ul className="grid gap-0">
        {first > 0 && <li style={{ height: first * ASIDE_ROW }} aria-hidden="true" />}
        {refs.slice(first, last).map(r => (
          <li key={r.key} className="flex items-center gap-2" style={{ height: ASIDE_ROW }} data-testid="set-aside-row" data-key={r.key}>
            <span className="font-mono">{r.key}</span>
            <span className="min-w-0 flex-1 truncate text-muted-foreground">{r.layer}</span>
            {onFloorPast && (
              <label className="flex shrink-0 items-center gap-1" title="The floor runs past this line: it no longer bounds a room">
                <Checkbox checked={!!r.floorPast} disabled={!editable} onCheckedChange={v => onFloorPast(r.key, v === true)} data-testid={TID.setAsideFloorPast} />
                The floor runs past it
              </label>
            )}
            <Button size="sm" variant="ghost" className="h-6" disabled={!editable} onClick={() => onRestore(r.key)} data-testid="restore-one">Restore</Button>
          </li>
        ))}
        {last < refs.length && <li style={{ height: (refs.length - last) * ASIDE_ROW }} aria-hidden="true" />}
      </ul>
    </div>
  );
}

export function CheckStep() {
  const { detail, settings, change, editable: canEdit, setDetail, refresh, projectId, buildId, saverState } = useBuildContext();
  const lock = useLockText();
  const editable = canEdit && !lock;
  const result = detail.result;
  const overlayQ = useQuery(rawQueryOptions<BuildOverlay>(result?.urls.overlay, result?.runId ?? ''));
  const diffQ = useQuery(rawQueryOptions<BuildDiff>(result?.urls.diff, result?.runId ?? ''));
  const overlay = overlayQ.data;
  const floorKeys = overlay?.floors.map(f => f.key) ?? result?.floors.map(f => f.key) ?? [];
  const [floorKey, setFloorKey] = useState<string | null>(null);
  const key = floorKey && floorKeys.includes(floorKey) ? floorKey : floorKeys[0] ?? null;
  const ofloor = overlay?.floors.find(f => f.key === key) ?? null;
  const setting = settings?.floors.find(f => f.key === key) ?? null;
  const sourceSha1 = ofloor?.source ?? setting?.source;
  const src = detail.sources.find(s => s.sha1 === sourceSha1);
  const { plan, loading } = usePlan(src);
  const index = useMemo(() => (plan ? keyIndex(plan) : new Map<string, number>()), [plan]);

  const [tool, setTool] = useState<CheckTool>('select');
  const [show, setShow] = useState<PlanShow>({ rooms: true, plate: true, furniture: true });
  const [roomTarget, setRoomTarget] = useState<RoomTarget | null>(null);
  const [stairId, setStairId] = useState<string | null>(null);
  /** The stair whose bottom tread is being picked ("This is the bottom", then one pick). */
  const [stairPick, setStairPick] = useState<string | null>(null);
  const [pick, setPick] = useState<PickMode>('item');
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [focus, setFocus] = useState<Bbox | null>(null);
  const [activeFlag, setActiveFlag] = useState<string | null>(null);
  const [opening, setOpening] = useState<string | null>(null);
  /** The grey family a flag's "Give it a kind" named, and how many clicks so far (each brings its select into view). */
  const [family, setFamily] = useState<{ name: string; seq: number } | null>(null);
  const [find, setFind] = useState('');
  const [against, setAgainst] = useState(0);
  const [drawDiff, setDrawDiff] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [flagKind, setFlagKind] = useState<'' | FlagKind>('');
  const [checkOnly, setCheckOnly] = useState(false);
  const canvasBox = useRef<HTMLDivElement>(null);

  const flags = useMemo(() => (overlay?.flags ?? []).filter(f => f.floor === key || f.floor === null), [overlay, key]);
  const canvasFlags = useMemo(() => flags.filter(f => f.floor === key), [flags, key]);
  const allAside = settings?.fixes.setAside;
  const setAsideRefs = useMemo(() => (allAside ?? []).filter(r => r.floor === key), [allAside, key]);
  const setAsideKeys = useMemo(() => new Set(setAsideRefs.map(r => r.key)), [setAsideRefs]);
  const greyFamilies = flags.filter(f => f.kind === 'grey-furniture' && f.ref.family).map(f => ({ family: f.ref.family!, count: greyCount(f) }));
  // the flag list by kind and severity (UR, V2-13: the house's ground floor alone had 47 cards)
  const kindsHere = useMemo(() => {
    const m = new Map<FlagKind, number>();
    for (const f of flags) m.set(f.kind, (m.get(f.kind) ?? 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [flags]);
  const listed = useMemo(() => flags.filter(f => (!flagKind || f.kind === flagKind) && (!checkOnly || f.severity === 'check')),
    [flags, flagKind, checkOnly]);
  const canvasKey = (k: string) => {
    // the canvas's own keys (+, -, F): it listens on its <canvas> (plan/controller.ts)
    canvasBox.current?.querySelector('canvas')?.dispatchEvent(new KeyboardEvent('keydown', { key: k, cancelable: true }));
  };
  const diffBody = diffQ.data?.against[Math.min(against, Math.max(0, (diffQ.data?.against.length ?? 1) - 1))]?.diff ?? null;
  const run = detail.run;
  const active = run && (run.status === 'queued' || run.status === 'running');

  const select = (keys: string[], mode: 'replace' | 'add' | 'toggle') => {
    setSelected(prev => {
      if (mode === 'replace') return new Set(keys);
      const next = new Set(prev);
      for (const k of keys) {
        if (mode === 'add') next.add(k);
        else if (next.has(k)) next.delete(k); else next.add(k);
      }
      return next;
    });
  };
  const refsOf = (keys: Iterable<string>): ItemRef[] => {
    if (!plan || !key) return [];
    const out: ItemRef[] = [];
    for (const k of keys) { const r = itemRef(plan, key, k); if (r) out.push(r); }
    return out;
  };
  const selectedAside = useMemo(() => asideOf(selected, setAsideKeys), [selected, setAsideKeys]);
  const selectedFree = useMemo(() => {
    const aside = new Set(selectedAside);
    return [...selected].filter(k => !aside.has(k));
  }, [selected, selectedAside]);
  const setAside = () => {
    const refs = refsOf(selectedFree);
    if (refs.length) change(addSetAside(refs));
    setSelected(new Set());
  };
  const restore = (keys: string[]) => {
    if (key && keys.length) change(restoreSetAside(key, keys));
    setSelected(new Set());
  };
  // ---- the rooms milestone: the fixes of R-6.2 written from the tools, the panels and the flag cards
  const stale = !!result?.stale;
  const fixes = useMemo(() => (settings && key && ofloor ? fixMarks(settings, key, ofloor, stale) : null), [settings, key, ofloor, stale]);
  // RR (S13): the room or stair open in a panel is outlined on the plan (a small room picked there can be found again)
  const pickedRoom = roomTarget?.id || null;
  const marks = useMemo(() => (ofloor && (pickedRoom || stairId) ? { ...(fixes ?? NO_MARKS), pickedRoom, pickedStair: stairId } : fixes),
    [fixes, ofloor, pickedRoom, stairId]);
  const canvasOverlay = useMemo(() => (ofloor && marks && hasMarks(marks) ? withMarks(ofloor, marks) : ofloor), [ofloor, marks]);
  const closePanels = () => { setRoomTarget(null); setStairId(null); setStairPick(null); };
  const onLine = (a: Vec2, b: Vec2) => { if (key) change(addClosing({ floor: key, a, b, use: 'line' })); };
  /** A click on one of the app's closings: it is taken out (one room), or put back when it was. */
  const onClosing = (index: number) => {
    const c = ofloor?.closings?.[index];
    if (!c || !key || !settings || c.kind === 'staff') return;
    const was = closingsOf(settings).find(f => f.floor === key && f.use === 'none' && sameEnds(f.a, f.b, c.a, c.b, 0.3));
    change(was ? removeClosing(was) : addClosing({ floor: key, a: c.a, b: c.b, use: 'none' }));
  };
  const onSpace = (id: string) => {
    const sp = ofloor?.spaces?.find(s => s.id === id);
    if (!sp) return;
    setStairId(null); setStairPick(null);
    setRoomTarget({ id, at: pointIn(sp.o, sp.h) });
  };
  const onPoint = (pt: Vec2) => { setStairId(null); setStairPick(null); setRoomTarget({ id: '', at: [Math.round(pt[0] * 1000) / 1000, Math.round(pt[1] * 1000) / 1000] }); };
  const onStair = (id: string) => { setRoomTarget(null); setStairPick(null); setStairId(id); };
  const onBottom = (p: Vec2) => {
    const st = ofloor?.stairs?.find(s => s.id === stairPick);
    setStairPick(null);
    if (!st || !key || !settings) return;
    const fix = stairFixFor(settings, key, ofloor, st.id);
    change(setStairFix({ floor: key, at: fix?.at ?? pointIn(st.outline), bottom: p, use: fix?.use ?? 'auto' }, fix?.at ?? null));
  };
  const flagActions: FlagRoomsActions = {
    fixOf: f => flagFix(f, settings, ofloor, stale),
    onCloseHere: f => { const fx = closeHereFix(f); if (fx) change(addClosing(fx)); },
    onOutdoors: f => { const fx = outdoorsFix(f, ofloor); if (fx) change(setRoomFix(fx)); },
    onNotDoorway: f => { const fx = notDoorwayFix(f); if (fx) change(addClosing(fx)); },
    onItIsFloor: f => { const fx = xHoleFloorFix(f); if (fx) change(setRoomFix(fx)); },
    earlier: !!settings && rulesOf(settings) === 'earlier',
    onUseNew: () => change(setRules('new')),
  };
  const canvasTool = stairPick ? 'pick-point' as const : tool;
  /** RR (S1): on a screen too narrow for the sticky plan column, Show brings the plan into view (nothing moves when it
   *  is in view already). After the render it causes: a tool's hint line above the plan moves it. */
  const [showTick, setShowTick] = useState(0);
  useLayoutEffect(() => { if (showTick) canvasBox.current?.scrollIntoView?.({ block: 'nearest' }); }, [showTick]);
  const showPlan = () => setShowTick(t => t + 1);
  const showAt = (box: Bbox | null) => { if (box) setFocus(box); showPlan(); };
  /** RR (S2): a stair card's "Open this stair": the tool Rooms and stairs with that stair's panel open. */
  const openStair = (f: Flag) => {
    const id = f.ref.stair;
    if (!id || !(ofloor?.stairs ?? []).some(s => s.id === id)) return;
    setTool('rooms'); setRoomTarget(null); setStairPick(null); setStairId(id);
    setActiveFlag(f.id); showAt(bboxAround(f));
  };

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest('input, select, textarea')) return;
    if (e.key === 'Escape') { setSelected(new Set()); setOpening(null); closePanels(); }
    else if ((e.key === 'Delete' || e.key === 'Backspace') && editable && selectedFree.length) { e.preventDefault(); setAside(); }
  };
  const rebuild = async () => {
    setStarting(true);
    setRunError(null);
    try {
      const { data } = await runBuild({ path: { projectId, buildId }, body: {}, throwOnError: true });
      setDetail(data as BuildDetail);
    } catch (err) {
      if (isRunInProgress(err)) {
        refresh();                                          // a run started elsewhere: show and poll it (UR, V2-14)
        setRunError(STARTED_ELSEWHERE);
      } else {
        setRunError(errorReason(err));
      }
    } finally {
      setStarting(false);
    }
  };
  const editing = opening && ofloor ? ofloor.openings.find(o => o.id === opening) ?? null : null;
  const fixOf = (o: { a: [number, number]; b: [number, number] }): OpeningFix | null => (settings?.fixes.openings ?? []).find(f => f.floor === key
    && ((Math.abs(f.a[0] - o.a[0]) < 0.005 && Math.abs(f.a[1] - o.a[1]) < 0.005 && Math.abs(f.b[0] - o.b[0]) < 0.005 && Math.abs(f.b[1] - o.b[1]) < 0.005)
      || (Math.abs(f.a[0] - o.b[0]) < 0.005 && Math.abs(f.a[1] - o.b[1]) < 0.005 && Math.abs(f.b[0] - o.a[0]) < 0.005 && Math.abs(f.b[1] - o.a[1]) < 0.005))) ?? null;
  const outlineOf = (f: Flag) => {
    const e = f.ref.edge;
    if (!e) return null;
    const fix = (settings?.fixes.outlineEdges ?? []).find(x => x.floor === key && Math.abs(x.a[0] - e[0][0]) < 0.005 && Math.abs(x.a[1] - e[0][1]) < 0.005 && Math.abs(x.b[0] - e[1][0]) < 0.005 && Math.abs(x.b[1] - e[1][1]) < 0.005);
    return fix?.as ?? null;
  };
  const found = plan ? findItems(plan, find, FIND_LIMIT, index) : [];
  const floorIndex = settings?.floors.findIndex(f => f.key === key) ?? -1;

  if (!result) return <p className="text-sm text-muted-foreground" data-testid="check-step">Build the draft first.</p>;

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]" data-testid="check-step" onKeyDown={onKeyDown}>
      {/* RR (S1): on a wide screen the plan column stays on screen under the app bar while the flag list scrolls; when it
          is taller than the window it scrolls by itself */}
      <section className={PLAN_COLUMN} data-testid="check-plan-column">
        {lock && <Alert data-testid="check-locked"><AlertDescription>{lock}</AlertDescription></Alert>}
        <RulesLine settings={settings} editable={editable} />
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap gap-1" role="tablist" aria-label="Floor">
            {floorKeys.map(k => {
              const f = result.floors.find(x => x.key === k);
              return (
                <Button key={k} size="sm" role="tab" aria-selected={k === key} variant={k === key ? 'default' : 'outline'} data-testid="check-floor" data-key={k}
                  onClick={() => { setFloorKey(k); setSelected(new Set()); setOpening(null); setFocus(null); closePanels(); }}>
                  {f?.name ?? k}
                </Button>
              );
            })}
          </div>
          <NativeSelect aria-label="Tool" value={tool} data-testid={TID.checkTool}
            onChange={e => { const v = e.target.value as CheckTool; setTool(CHECK_TOOLS.includes(v) ? v : 'select'); setStairPick(null); }}>
            {(['select', 'pan', 'draw-line', 'rooms'] as const).map(t => <option key={t} value={t}>{CHECK_TOOL_TEXT[t]}</option>)}
          </NativeSelect>
          <NativeSelect aria-label="Pick" value={pick} onChange={e => setPick(e.target.value as PickMode)} data-testid="pick-mode">
            {PICK_MODES.map(m => <option key={m.mode} value={m.mode}>{m.text}</option>)}
          </NativeSelect>
          <span className="text-sm text-muted-foreground" data-testid="selection-count">{`${formatNumber(selected.size)} selected`}</span>
          <Button size="sm" disabled={!editable || !selectedFree.length} onClick={setAside} data-testid="set-aside">
            <EyeOff aria-hidden="true" />
            Set aside
          </Button>
          <Button size="sm" variant="outline" disabled={!editable || !selectedAside.length} onClick={() => restore(selectedAside)} data-testid="restore">
            <RotateCcw aria-hidden="true" />
            Restore
          </Button>
          {selected.size > 0 && (
            <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())} data-testid="clear-selection"><X aria-hidden="true" />Clear</Button>
          )}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <ShowTicks show={show} onShow={setShow} />
          <CheckCounts of={ofloor} />
        </div>
        {(tool === 'draw-line' || tool === 'rooms' || stairPick) && (
          <p className="text-xs font-medium text-amber-800" data-testid={tool === 'draw-line' && !stairPick ? TID.drawLineHint : 'rooms-tool-hint'}>
            {stairPick ? 'Click the stair\'s bottom tread on the plan.' : tool === 'draw-line' ? DRAW_LINE_HINT : ROOMS_TOOL_HINT}
          </p>
        )}
        <div className="flex flex-wrap items-center justify-between gap-2" data-testid="canvas-help">
          <p className="text-xs text-muted-foreground">{CANVAS_HINT}</p>
          <div className="flex items-center gap-1">
            <Button size="sm" variant="outline" className="h-7" disabled={!plan} onClick={() => canvasKey('f')} data-testid="canvas-fit" title="Fit the plan (F)">
              <Maximize2 aria-hidden="true" />
              Fit
            </Button>
            <Button size="icon" variant="outline" className="size-7" disabled={!plan} onClick={() => canvasKey('+')} data-testid="canvas-zoom-in" aria-label="Zoom in" title="Zoom in (+)">
              <ZoomIn aria-hidden="true" />
            </Button>
            <Button size="icon" variant="outline" className="size-7" disabled={!plan} onClick={() => canvasKey('-')} data-testid="canvas-zoom-out" aria-label="Zoom out" title="Zoom out (-)">
              <ZoomOut aria-hidden="true" />
            </Button>
          </div>
        </div>
        <div ref={canvasBox} className="h-[560px] overflow-hidden rounded-lg border bg-white" data-testid="check-canvas" tabIndex={-1}>
          {plan && settings ? (
            <PlanCanvas
              plan={plan}
              roleOf={i => roleOf(settings, plan.layers[i] ?? '')}
              area={ofloor?.area ?? setting?.area ?? null}
              overlay={canvasOverlay}
              flags={canvasFlags}
              selected={selected}
              setAside={setAsideKeys}
              diff={drawDiff ? diffBody : null}
              tool={canvasTool}
              pick={pick}
              focus={focus}
              show={show}
              onSelect={select}
              onOpening={id => setOpening(id)}
              onFlag={id => { setActiveFlag(id); const f = flags.find(x => x.id === id); if (f?.ref.keys) select(f.ref.keys, 'replace'); }}
              onPick={onBottom}
              onLine={onLine}
              onSpace={onSpace}
              onStair={onStair}
              onClosing={onClosing}
              onPoint={onPoint}
            />
          ) : (
            <p className="p-4 text-sm text-muted-foreground">{loading ? 'Loading the plan...' : 'No plan to show.'}</p>
          )}
        </div>
        <div className="grid gap-1" data-testid="find">
          <div className="flex items-center gap-2">
            <Search aria-hidden="true" className="size-4 text-muted-foreground" />
            <Input className="h-8" placeholder="Find items by key (e.g. BA/2C4) or layer" value={find} onChange={e => setFind(e.target.value)} data-testid="find-items" aria-label="Find items" />
          </div>
          {found.length > 0 && plan && (
            <ul className="grid max-h-48 gap-0.5 overflow-auto rounded-md border bg-background p-1 text-xs" data-testid="find-results">
              {found.map(f => (
                <li key={f.key}>
                  <button
                    type="button"
                    className={cn('flex w-full items-center gap-2 rounded px-2 py-0.5 text-left hover:bg-accent', selected.has(f.key) && 'bg-accent')}
                    data-testid="find-result"
                    data-key={f.key}
                    data-type={f.type}
                    onClick={e => {
                      const k = pick === 'block' ? blockOf(f.key, index, plan) : f.key;
                      select([k], e.shiftKey ? 'toggle' : 'replace');
                    }}
                  >
                    <span className="font-mono">{f.key}</span>
                    <span className="truncate text-muted-foreground">{`${f.layer} · ${TYPE_NAMES[f.type] ?? f.type}${setAsideKeys.has(f.key) ? ' · set aside' : ''}`}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <DiffPanel diff={diffQ.data} against={against} onAgainst={setAgainst} draw={drawDiff} onDraw={setDrawDiff} floor={key ?? undefined} />
      </section>

      <section className="grid min-w-0 content-start gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Button disabled={!editable || !!active || starting || saverState?.status === 'saving' || saverState?.status === 'pending'} onClick={() => void rebuild()} data-testid="rebuild">
            <Hammer aria-hidden="true" />
            Rebuild
          </Button>
          {result.stale && <span className="text-xs text-amber-700" data-testid="check-stale">Changes wait for the next build.</span>}
        </div>
        {runError && <Alert variant="destructive" data-testid="rebuild-error"><AlertDescription>{runError}</AlertDescription></Alert>}
        {run && run.kind === 'build' && (active || run.status === 'failed' || run.status === 'cancelled') && <RunPanel run={run} />}
        {editing && key && (
          <OpeningEditor floor={key} opening={editing} fix={fixOf(editing)} disabled={!editable}
            onApply={fix => { change(setOpeningFix(fix)); setOpening(null); }} onClose={() => setOpening(null)} />
        )}
        {roomTarget && key && settings && (
          <RoomPanel key={`${roomTarget.id}:${roomTarget.at.join(',')}`} floor={key} target={roomTarget} settings={settings} of={ofloor} stale={stale}
            editable={editable} onClose={() => setRoomTarget(null)} />
        )}
        {stairId && key && settings && (
          <StairPanel floor={key} stairId={stairId} settings={settings} of={ofloor} stale={stale} editable={editable} picking={stairPick === stairId}
            onPickBottom={() => setStairPick(stairPick === stairId ? null : stairId)} onClose={() => { setStairId(null); setStairPick(null); }} />
        )}
        <section className="grid gap-2" data-testid="set-aside-list">
          <h4 className="text-sm font-semibold">{`Set aside on this floor (${formatNumber(setAsideRefs.length)})`}</h4>
          {setAsideRefs.length > 0 && (
            <SetAsideList refs={setAsideRefs} editable={editable} onRestore={k => restore([k])}
              onFloorPast={settings && rulesOf(settings) === 'new' && key ? (k, on) => change(setFloorPast(key, k, on)) : undefined} />
          )}
        </section>
        {settings && key && (
          <FixesList settings={settings} floor={key} of={ofloor} stale={stale} editable={editable}
            onShow={at => showAt([at[0] - 3, at[1] - 3, at[0] + 3, at[1] + 3])} />
        )}
        {flags.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 text-sm" data-testid="flag-filter">
            <span className="font-semibold">{`Flags (${formatNumber(listed.length)} of ${formatNumber(flags.length)})`}</span>
            <NativeSelect aria-label="Flags of one kind" value={flagKind} onChange={e => setFlagKind(e.target.value as '' | FlagKind)} data-testid="flag-kind-filter">
              <option value="">Every kind</option>
              {kindsHere.map(([k, n]) => <option key={k} value={k}>{`${FLAG_KIND_TEXT[k] ?? k} (${n})`}</option>)}
            </NativeSelect>
            <label className="flex items-center gap-1.5">
              <Checkbox checked={checkOnly} onCheckedChange={v => setCheckOnly(v === true)} data-testid="flag-check-only" />
              To check only
            </label>
          </div>
        )}
        <FlagList
          flags={listed}
          activeId={activeFlag}
          disabled={!editable}
          outlineOf={outlineOf}
          onShow={f => { setActiveFlag(f.id); showAt(bboxAround(f)); }}
          onOpenStair={openStair}
          onSelectKeys={keys => select(keys, 'replace')}
          onOpening={id => setOpening(id)}
          onOutline={(f, as) => { if (key && f.ref.edge) change(setOutlineEdge({ floor: key, a: f.ref.edge[0], b: f.ref.edge[1], as })); }}
          onFamily={name => setFamily(f => ({ name, seq: (f?.seq ?? 0) + 1 }))}
          rooms={flagActions}
        />
        {settings && (
          <FurnitureWords families={greyFamilies} settings={settings} disabled={!editable} focus={family?.name ?? null} focusSeq={family?.seq}
            onKind={(fam, kind) => change(setFurnitureWord(fam, kind))} />
        )}
        {settings && setting && floorIndex >= 0 && (
          <section className="grid gap-2 rounded-lg border bg-background p-3" data-testid="heights-panel">
            <h4 className="text-sm font-semibold">Heights</h4>
            <div className="grid grid-cols-2 gap-3">
              <NumberField label={`${setting.name}: level`} value={setting.level} disabled={!editable} testId="check-level" onCommit={v => change(updateFloor(floorIndex, { level: v ?? 0 }))} />
              <NumberField label={`${setting.name}: wall height`} value={setting.wallHeight} disabled={!editable} testId="check-wall-height" onCommit={v => change(updateFloor(floorIndex, { wallHeight: v ?? setting.wallHeight }))} />
              <NumberField label="Door head (project)" value={settings.defaults.doorHead} disabled={!editable} testId="check-door-head" onCommit={v => change(setDefaults({ doorHead: v ?? settings.defaults.doorHead }))} />
              <NumberField label="Railing height" value={settings.defaults.railingHeight} disabled={!editable} testId="check-railing" onCommit={v => change(setDefaults({ railingHeight: v ?? settings.defaults.railingHeight }))} />
              <NumberField label="Single-line height" value={settings.defaults.singleLineHeight} disabled={!editable} testId="check-single-line" onCommit={v => change(setDefaults({ singleLineHeight: v ?? settings.defaults.singleLineHeight }))} />
              <NumberField label={`${setting.name}: ceiling height`} value={setting.ceilingHeight ?? null} allowEmpty disabled={!editable}
                placeholder={String(defaultCeilingHeight(settings, floorIndex) ?? 'none')} testId={TID.heightsCeiling} dataKey={setting.key}
                onCommit={v => change(updateFloor(floorIndex, { ceilingHeight: v }))} />
            </div>
          </section>
        )}
      </section>
    </div>
  );
}
