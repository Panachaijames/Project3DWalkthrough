// Step "Check" (docs/upload/DESIGN.md U-2 5e, U-12): per floor the plan with the built walls, glass, openings, furniture
// boxes and flags over it; the flag list; the diff against the previous build and the latest version. Tools: select items
// (click, shift-click, box; pick modes item / whole block / layer in a box, or by key and layer with Find) -> Set aside
// / Restore (an ItemRef with every field from the plan entry; an INSERT anchor's ref covers its subtree); an opening ->
// kind, head, sill; an outline suggestion -> wall / glass / refuse; grey furniture families -> a kind; floor heights and
// the project's heights; Rebuild (the screen keeps the last result while it runs). Keyboard: Esc clears the selection,
// Delete sets it aside. Locked while a source is read again. Keys, layers and flag texts are drawing text: text only.
import { useQuery } from '@tanstack/react-query';
import { EyeOff, Hammer, RotateCcw, Search, X } from 'lucide-react';
import { useMemo, useState, type KeyboardEvent } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { runBuild } from '@/api/generated/sdk.gen';
import { PlanCanvas, type DecodedPlan, type PickMode } from '@/plan';
import type { Bbox, BuildDetail, BuildDiff, BuildOverlay, Flag, ItemRef, OpeningFix } from '@/upload/contracts';
import { rawQueryOptions } from '@/upload/raw';
import { errorReason, formatNumber } from '@/lib/format';
import { cn } from '@/lib/utils';
import { useBuildContext, useLockText, usePlan } from './context';
import { DiffPanel } from './DiffPanel';
import { NativeSelect, NumberField } from './fields';
import { FlagList } from './FlagList';
import { FurnitureWords } from './FurnitureWords';
import { OpeningEditor } from './OpeningEditor';
import { RunPanel } from './RunPanel';
import {
  addSetAside, itemRef, restoreSetAside, roleOf, setDefaults, setFurnitureWord, setOpeningFix, setOutlineEdge, updateFloor,
} from './settingsEdit';

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

export function CheckStep() {
  const { detail, settings, change, editable: canEdit, setDetail, projectId, buildId, saverState } = useBuildContext();
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

  const [tool, setTool] = useState<'pan' | 'select'>('select');
  const [pick, setPick] = useState<PickMode>('item');
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [focus, setFocus] = useState<Bbox | null>(null);
  const [activeFlag, setActiveFlag] = useState<string | null>(null);
  const [opening, setOpening] = useState<string | null>(null);
  const [family, setFamily] = useState<string | null>(null);
  const [find, setFind] = useState('');
  const [against, setAgainst] = useState(0);
  const [drawDiff, setDrawDiff] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const flags = useMemo(() => (overlay?.flags ?? []).filter(f => f.floor === key || f.floor === null), [overlay, key]);
  const setAsideRefs = (settings?.fixes.setAside ?? []).filter(r => r.floor === key);
  const setAsideKeys = useMemo(() => new Set(setAsideRefs.map(r => r.key)), [setAsideRefs.map(r => r.key).join('\n')]);   // eslint-disable-line react-hooks/exhaustive-deps
  const greyFamilies = flags.filter(f => f.kind === 'grey-furniture' && f.ref.family).map(f => {
    const m = /(\d+)/.exec(f.detail);
    return { family: f.ref.family!, count: m ? Number(m[1]) : null };
  });
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
  const selectedAside = [...selected].filter(k => setAsideKeys.has(k) || [...setAsideKeys].some(a => k.startsWith(`${a}/`)));
  const selectedFree = [...selected].filter(k => !selectedAside.includes(k));
  const setAside = () => {
    const refs = refsOf(selectedFree);
    if (refs.length) change(addSetAside(refs));
    setSelected(new Set());
  };
  const restore = (keys: string[]) => {
    if (key && keys.length) change(restoreSetAside(key, keys));
    setSelected(new Set());
  };
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest('input, select, textarea')) return;
    if (e.key === 'Escape') { setSelected(new Set()); setOpening(null); }
    else if ((e.key === 'Delete' || e.key === 'Backspace') && editable && selectedFree.length) { e.preventDefault(); setAside(); }
  };
  const rebuild = async () => {
    setStarting(true);
    setRunError(null);
    try {
      const { data } = await runBuild({ path: { projectId, buildId }, body: {}, throwOnError: true });
      setDetail(data as BuildDetail);
    } catch (err) {
      setRunError(errorReason(err));
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
      <section className="grid min-w-0 content-start gap-2">
        {lock && <Alert data-testid="check-locked"><AlertDescription>{lock}</AlertDescription></Alert>}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap gap-1" role="tablist" aria-label="Floor">
            {floorKeys.map(k => {
              const f = result.floors.find(x => x.key === k);
              return (
                <Button key={k} size="sm" role="tab" aria-selected={k === key} variant={k === key ? 'default' : 'outline'} data-testid="check-floor" data-key={k}
                  onClick={() => { setFloorKey(k); setSelected(new Set()); setOpening(null); setFocus(null); }}>
                  {f?.name ?? k}
                </Button>
              );
            })}
          </div>
          <NativeSelect aria-label="Tool" value={tool} onChange={e => setTool(e.target.value === 'pan' ? 'pan' : 'select')} data-testid="check-tool">
            <option value="select">Select</option>
            <option value="pan">Pan</option>
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
        <div className="h-[560px] overflow-hidden rounded-lg border bg-white" data-testid="check-canvas" tabIndex={-1}>
          {plan && settings ? (
            <PlanCanvas
              plan={plan}
              roleOf={i => roleOf(settings, plan.layers[i] ?? '')}
              area={ofloor?.area ?? setting?.area ?? null}
              overlay={ofloor}
              flags={flags.filter(f => f.floor === key)}
              selected={selected}
              setAside={setAsideKeys}
              diff={drawDiff ? diffBody : null}
              tool={tool}
              pick={pick}
              focus={focus}
              onSelect={select}
              onOpening={id => setOpening(id)}
              onFlag={id => { setActiveFlag(id); const f = flags.find(x => x.id === id); if (f?.ref.keys) select(f.ref.keys, 'replace'); }}
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
        <section className="grid gap-2" data-testid="set-aside-list">
          <h4 className="text-sm font-semibold">{`Set aside on this floor (${setAsideRefs.length})`}</h4>
          {setAsideRefs.length > 0 && (
            <ul className="grid max-h-40 gap-0.5 overflow-auto text-xs">
              {setAsideRefs.map(r => (
                <li key={r.key} className="flex items-center gap-2" data-testid="set-aside-row" data-key={r.key}>
                  <span className="font-mono">{r.key}</span>
                  <span className="min-w-0 flex-1 truncate text-muted-foreground">{r.layer}</span>
                  <Button size="sm" variant="ghost" className="h-6" disabled={!editable} onClick={() => restore([r.key])} data-testid="restore-one">Restore</Button>
                </li>
              ))}
            </ul>
          )}
        </section>
        <FlagList
          flags={flags}
          activeId={activeFlag}
          disabled={!editable}
          outlineOf={outlineOf}
          onShow={f => { setActiveFlag(f.id); setFocus(bboxAround(f)); }}
          onSelectKeys={keys => select(keys, 'replace')}
          onOpening={id => setOpening(id)}
          onOutline={(f, as) => { if (key && f.ref.edge) change(setOutlineEdge({ floor: key, a: f.ref.edge[0], b: f.ref.edge[1], as })); }}
          onFamily={setFamily}
        />
        {settings && (
          <FurnitureWords families={greyFamilies} settings={settings} disabled={!editable} focus={family}
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
            </div>
          </section>
        )}
      </section>
    </div>
  );
}
