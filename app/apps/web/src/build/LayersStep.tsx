// Step "Layers" (docs/upload/DESIGN.md U-2 5b, U-8.1, U-8.3, U-14.3): one row per layer name across the sources (100 - 400
// rows): name, on/off/frozen, items by type, fills, door arcs, texts, inserts, top block families, the suggested role with
// where it came from (its evidence under the sheet when the row is picked), and a native <select> showing the 17 role
// labels with one line of help (and a legend of every role). A suggestion whose name and contents disagree, or that only
// the contents made for a role that builds parts, carries a "check" mark (UR, V2-6). Filters (not mapped yet,
// suggestions to check, by role, search) and "apply to all rows shown". Rows are windowed
// above 200 (a fixed row height and a slice; no library). The sheet on the canvas with the hovered or picked layer lit
// and every layer coloured by its role. A warning chip on an `ignore` row whose items lie within 1 m of wall-role lines
// (nearLayers). Changes save as settings (800 ms debounce, If-Match); every save from this step carries
// layersReviewed: true, and seeing the step once sends it with no change too (U-8.3). Layer names are text only.
import { useQueries } from '@tanstack/react-query';
import { TriangleAlert } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { decodePlan, nearLayers, PlanCanvas, type DecodedPlan } from '@/plan';
import type { DrawingRead, LayerRead, LayerRole, LayerSuggestion, PlanGeometry } from '@/upload/contracts';
import { rawQueryOptions } from '@/upload/raw';
import { cn } from '@/lib/utils';
import { formatNumber } from '@/lib/format';
import { sourceToken, useBuildContext } from './context';
import { NativeSelect } from './fields';
import {
  CLOSE_TO_WALLS, CLOSE_TO_WALLS_M, isRole, roleHelp, roleLabel, ROLES, SUGGESTION_FROM, SUGGESTION_FROM_SHORT, suggestionToCheck,
  WALL_ROLES,
} from './roles';
import { roleOf, setRoles } from './settingsEdit';

/** The Doors column (UR, V2-12: '0/8' had no legend). */
export const DOORS_HELP = 'door swings with a leaf, of the door-sized arcs on the layer';

/** Rows above this many are windowed (U-14.3). */
export const WINDOW_ABOVE = 200;
export const ROW_HEIGHT = 36;
/** The table's scrolling height (px) and the rows drawn beyond it on each side. */
export const VIEW_HEIGHT = 560;
const OVERSCAN = 8;

export interface LayerRow {
  name: string;
  /** null: no drawing read lists it (a name from the settings or the suggestions only). */
  read: {
    on: boolean; frozen: boolean; items: number; byType: Record<string, number>; solidHatches: number; doorArcs: number;
    doorArcsWithLeaf: number; texts: number; inserts: number; topBlocks: { family: string; count: number }[];
  } | null;
  /** Indexes of the sources whose drawing has the layer. */
  sources: number[];
}

/** One row per layer name across the drawings (counts summed, top blocks merged), then the names only the settings or the
 *  suggestions know; sorted by name. */
export function layerRows(drawings: (DrawingRead | undefined)[], extraNames: Iterable<string>): LayerRow[] {
  const rows = new Map<string, LayerRow>();
  drawings.forEach((d, si) => {
    for (const l of d?.layers ?? []) {
      const row = rows.get(l.name) ?? { name: l.name, read: null, sources: [] };
      row.sources.push(si);
      row.read = mergeRead(row.read, l);
      rows.set(l.name, row);
    }
  });
  for (const n of extraNames) if (!rows.has(n)) rows.set(n, { name: n, read: null, sources: [] });
  return [...rows.values()].sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
}

function mergeRead(r: LayerRow['read'], l: LayerRead): NonNullable<LayerRow['read']> {
  const byType = { ...(r?.byType ?? {}) };
  for (const [k, v] of Object.entries(l.byType)) byType[k] = (byType[k] ?? 0) + v;
  const blocks = new Map((r?.topBlocks ?? []).map(b => [b.family, b.count]));
  for (const b of l.topBlocks) blocks.set(b.family, (blocks.get(b.family) ?? 0) + b.count);
  return {
    on: (r?.on ?? false) || l.state.on,
    frozen: (r?.frozen ?? false) || l.state.frozen,
    items: (r?.items ?? 0) + l.items,
    byType,
    solidHatches: (r?.solidHatches ?? 0) + l.solidHatches,
    doorArcs: (r?.doorArcs ?? 0) + l.doorArcs,
    doorArcsWithLeaf: (r?.doorArcsWithLeaf ?? 0) + l.doorArcsWithLeaf,
    texts: (r?.texts ?? 0) + l.texts,
    inserts: (r?.inserts ?? 0) + l.inserts,
    topBlocks: [...blocks.entries()].map(([family, count]) => ({ family, count })).sort((a, b) => b.count - a.count).slice(0, 10),
  };
}

/** The layers set to `ignore` that have items close to wall-role lines in any source (U-8.1). */
export function closeToWalls(plans: (DecodedPlan | null)[], role: (layer: string) => LayerRole,
  near: typeof nearLayers = nearLayers): Set<string> {
  const out = new Set<string>();
  for (const plan of plans) {
    if (!plan) continue;
    const walls = new Set<number>();
    plan.layers.forEach((n, i) => { if (WALL_ROLES.has(role(n))) walls.add(i); });
    if (!walls.size) continue;
    for (const [i, count] of near(plan, walls, CLOSE_TO_WALLS_M)) {
      const n = plan.layers[i];
      if (n !== undefined && count > 0 && role(n) === 'ignore') out.add(n);
    }
  }
  return out;
}

const STATE_TEXT = (r: LayerRow['read']) => (!r ? '' : r.frozen ? 'frozen' : r.on ? 'on' : 'off');
const typesText = (byType: Record<string, number>) =>
  Object.entries(byType).sort((a, b) => b[1] - a[1]).map(([t, n]) => `${t} ${formatNumber(n)}`).join(', ');

function RoleSelect({ value, onChange, disabled, name }: { value: LayerRole; onChange: (r: LayerRole) => void; disabled: boolean; name: string }) {
  return (
    <NativeSelect
      aria-label={`Role of ${name}`}
      data-testid="role-select"
      // the cell's width, never wider (UR, V2-12: a 192 px select overflowed its column and the table scrolled sideways)
      className="h-7 w-full min-w-0"
      value={value}
      disabled={disabled}
      title={roleHelp(value)}
      onChange={e => { if (isRole(e.target.value)) onChange(e.target.value); }}
    >
      {ROLES.map(r => <option key={r.role} value={r.role} title={r.help}>{r.label}</option>)}
    </NativeSelect>
  );
}

function SuggestionCell({ s }: { s: LayerSuggestion | undefined }) {
  if (!s) return <span className="text-xs text-muted-foreground">-</span>;
  const check = suggestionToCheck(s);
  return (
    <span className="flex min-w-0 items-center gap-1 text-xs" data-testid="layer-suggestion" data-role={s.role} data-from={s.from} data-check={check ? '' : undefined}
      title={[`${roleLabel(s.role)}: ${SUGGESTION_FROM[s.from]}`, ...s.evidence].join('\n')}>
      <span className="truncate">
        {roleLabel(s.role)}
        <span className="text-muted-foreground">{` · ${SUGGESTION_FROM_SHORT[s.from]}`}</span>
      </span>
      {check && (
        <Badge variant="outline" className="shrink-0 border-amber-500 px-1 text-amber-700" title={check} data-testid="suggestion-check">check</Badge>
      )}
    </span>
  );
}

/** A layer no rule mapped yet (UR, V2-12: "Unmapped only" counted the layers missing from the settings, and after the
 *  proposal every layer is in them): not in the settings, or still `other` as the suggester's default (nothing known). */
export function notMappedYet(name: string, settings: { layers: Record<string, LayerRole> } | null, s: LayerSuggestion | undefined): boolean {
  if (!settings || !(name in settings.layers)) return true;
  return settings.layers[name] === 'other' && (!s || s.from === 'default');
}

export function LayersStep() {
  const { detail, settings, change, editable, saver } = useBuildContext();
  const sources = detail.sources;
  const drawingQs = useQueries({ queries: sources.map(s => rawQueryOptions<DrawingRead>(s.urls?.drawing, sourceToken(s))) });
  const planQs = useQueries({ queries: sources.map(s => rawQueryOptions<PlanGeometry>(s.urls?.plan, sourceToken(s))) });
  const drawings = drawingQs.map(q => q.data);
  const planData = planQs.map(q => q.data);
  const plans = useMemo(() => planData.map(p => { try { return p ? decodePlan(p) : null; } catch { return null; } }),
    // eslint-style: decoded once per answer
    planData);   // eslint-disable-line react-hooks/exhaustive-deps

  const [search, setSearch] = useState('');
  const [unmapped, setUnmapped] = useState(false);
  const [toCheck, setToCheck] = useState(false);
  const [roleFilter, setRoleFilter] = useState<'' | LayerRole>('');
  const [applyRole, setApplyRole] = useState<LayerRole>('ignore');
  const [picked, setPicked] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [sheet, setSheet] = useState(0);
  const [scrollTop, setScrollTop] = useState(0);

  // seen once: the review goes with the next save, or alone (U-8.3)
  useEffect(() => {
    if (saver && editable && !detail.layersReviewedAt) saver.markReviewed();
  }, [saver, editable, detail.layersReviewedAt]);

  const suggestions = detail.suggestions;
  const rows = useMemo(
    () => layerRows(drawings, [...Object.keys(settings?.layers ?? {}), ...Object.keys(suggestions)]),
    [drawings.map(d => d ? d.source.sha1 + d.layers.length : '').join(','), settings?.layers, suggestions],   // eslint-disable-line react-hooks/exhaustive-deps
  );
  const role = (n: string): LayerRole => (settings ? roleOf(settings, n) : suggestions[n]?.role ?? 'other');
  const near = useMemo(() => (settings ? closeToWalls(plans, n => roleOf(settings, n)) : new Set<string>()), [plans, settings]);

  const q = search.trim().toLowerCase();
  const checks = useMemo(() => new Set(Object.entries(suggestions).filter(([, s]) => suggestionToCheck(s)).map(([n]) => n)), [suggestions]);
  const shown = rows.filter(r =>
    (!q || r.name.toLowerCase().includes(q))
    && (!unmapped || notMappedYet(r.name, settings, suggestions[r.name]))
    && (!toCheck || checks.has(r.name))
    && (!roleFilter || role(r.name) === roleFilter));

  const windowed = shown.length > WINDOW_ABOVE;
  const first = windowed ? Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN) : 0;
  const last = windowed ? Math.min(shown.length, Math.ceil((scrollTop + VIEW_HEIGHT) / ROW_HEIGHT) + OVERSCAN) : shown.length;
  const slice = shown.slice(first, last);

  const plan = plans[sheet] ?? null;
  const lit = hovered ?? picked;
  const highlight = plan && lit !== null ? plan.layers.indexOf(lit) : -1;
  const pickedRow = picked !== null ? rows.find(r => r.name === picked) ?? null : null;
  const pickedSuggestion = picked !== null ? suggestions[picked] : undefined;
  const setRole = (names: string[], r: LayerRole) => change(setRoles(names, r), { layersReviewed: true });

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]" data-testid="layers-step">
      <section className="grid min-w-0 content-start gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Input className="h-8 w-56" placeholder="Search layers" value={search} onChange={e => { setSearch(e.target.value); setScrollTop(0); }} data-testid="layers-search" aria-label="Search layers" />
          <label className="flex items-center gap-1.5 text-sm" title="Layers no rule mapped: not built, kept as context by default">
            <Checkbox checked={unmapped} onCheckedChange={v => { setUnmapped(v === true); setScrollTop(0); }} data-testid="layers-unmapped" />
            Not mapped yet
          </label>
          <label className="flex items-center gap-1.5 text-sm" title="Suggestions whose name and contents disagree, or made from the contents alone">
            <Checkbox checked={toCheck} onCheckedChange={v => { setToCheck(v === true); setScrollTop(0); }} data-testid="layers-to-check" />
            {`Suggestions to check (${formatNumber(checks.size)})`}
          </label>
          <NativeSelect aria-label="Show the layers of one role" value={roleFilter} onChange={e => { setRoleFilter(e.target.value as '' | LayerRole); setScrollTop(0); }} data-testid="layers-role-filter">
            <option value="">Every role</option>
            {ROLES.map(r => <option key={r.role} value={r.role}>{r.label}</option>)}
          </NativeSelect>
          <span className="text-sm text-muted-foreground" data-testid="layers-count">{`${formatNumber(shown.length)} of ${formatNumber(rows.length)} layers`}</span>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted-foreground">Apply to all rows shown:</span>
          <NativeSelect aria-label="Role for every row shown" value={applyRole} onChange={e => { if (isRole(e.target.value)) setApplyRole(e.target.value); }} data-testid="apply-role" disabled={!editable}>
            {ROLES.map(r => <option key={r.role} value={r.role}>{r.label}</option>)}
          </NativeSelect>
          <Button size="sm" variant="outline" disabled={!editable || !shown.length} onClick={() => setRole(shown.map(r => r.name), applyRole)} data-testid="apply-role-button">
            {`Apply to ${formatNumber(shown.length)}`}
          </Button>
          <span className="text-xs text-muted-foreground">{roleHelp(applyRole)}</span>
        </div>
        <details className="text-sm" data-testid="roles-legend">
          <summary className="cursor-pointer text-xs text-muted-foreground">What each role does</summary>
          <dl className="mt-1 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-0.5 text-xs">
            {ROLES.map(r => (
              <div key={r.role} className="contents"><dt className="font-medium">{r.label}</dt><dd className="text-muted-foreground">{r.help}</dd></div>
            ))}
          </dl>
        </details>

        <div
          className="overflow-auto rounded-lg border bg-background"
          style={{ maxHeight: VIEW_HEIGHT }}
          onScroll={e => setScrollTop((e.target as HTMLDivElement).scrollTop)}
          data-testid="layers-scroll"
        >
          <table className="w-full table-fixed text-sm" data-testid="layers-table" data-windowed={windowed ? '' : undefined}>
            <colgroup>
              <col className="w-[24%]" /><col className="w-[5%]" /><col className="w-[6%]" /><col className="w-[5%]" /><col className="w-[7%]" />
              <col className="w-[5%]" /><col className="w-[6%]" /><col className="w-[10%]" /><col className="w-[14%]" /><col className="w-[18%]" />
            </colgroup>
            <thead className="sticky top-0 z-10 bg-muted text-left text-xs text-muted-foreground">
              <tr style={{ height: ROW_HEIGHT }}>
                <th className="px-2 font-medium">Layer</th><th className="font-medium">State</th><th className="font-medium">Items</th>
                <th className="font-medium" title="Solid fills">Fills</th>
                <th className="font-medium" title={DOORS_HELP}>Doors</th>
                <th className="font-medium">Texts</th><th className="font-medium">Inserts</th><th className="font-medium">Blocks</th>
                <th className="font-medium" title="The role suggested, and where it came from">Suggested</th><th className="pr-2 font-medium">Role</th>
              </tr>
            </thead>
            <tbody>
              {first > 0 && <tr style={{ height: first * ROW_HEIGHT }} aria-hidden="true" />}
              {slice.map(r => {
                const rd = r.read;
                const value = role(r.name);
                const chip = value === 'ignore' && near.has(r.name);
                return (
                  <tr
                    key={r.name}
                    style={{ height: ROW_HEIGHT }}
                    className={cn('border-t', picked === r.name && 'bg-accent', hovered === r.name && 'bg-accent/60')}
                    data-testid="layer-row"
                    data-layer={r.name}
                    data-role={value}
                    onMouseEnter={() => setHovered(r.name)}
                    onMouseLeave={() => setHovered(h => (h === r.name ? null : h))}
                    onClick={() => setPicked(p => (p === r.name ? null : r.name))}
                  >
                    <td className="px-2" title={r.name} data-testid="layer-name">
                      {/* the name gives way, never the chip (UR, V2-5: the ellipsis hid it on the bank's G-ANNO-TEXT) */}
                      <div className="flex min-w-0 items-center gap-1.5">
                        <span className="min-w-0 truncate font-mono text-xs">{r.name}</span>
                        {chip && (
                          <Badge variant="outline" className="shrink-0 border-amber-500 text-amber-700" title={CLOSE_TO_WALLS} data-testid="close-to-walls">
                            <TriangleAlert aria-hidden="true" />
                            close to walls
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="text-xs">{STATE_TEXT(rd)}</td>
                    <td className="truncate text-xs tabular-nums" title={rd ? typesText(rd.byType) : ''}>{rd ? formatNumber(rd.items) : ''}</td>
                    <td className="text-xs tabular-nums">{rd?.solidHatches || ''}</td>
                    <td className="text-xs tabular-nums" title={DOORS_HELP}>{rd && rd.doorArcs ? `${rd.doorArcsWithLeaf} of ${rd.doorArcs}` : ''}</td>
                    <td className="text-xs tabular-nums">{rd?.texts || ''}</td>
                    <td className="text-xs tabular-nums">{rd?.inserts || ''}</td>
                    <td className="truncate text-xs" title={rd ? rd.topBlocks.map(b => `${b.family} (${b.count})`).join('\n') : ''}>
                      {rd ? rd.topBlocks.slice(0, 2).map(b => b.family).join(', ') : ''}
                    </td>
                    <td className="min-w-0 pr-1"><SuggestionCell s={suggestions[r.name]} /></td>
                    <td className="pr-2" onClick={e => e.stopPropagation()}>
                      <RoleSelect value={value} name={r.name} disabled={!editable} onChange={x => setRole([r.name], x)} />
                    </td>
                  </tr>
                );
              })}
              {last < shown.length && <tr style={{ height: (shown.length - last) * ROW_HEIGHT }} aria-hidden="true" />}
            </tbody>
          </table>
          {!shown.length && <p className="p-4 text-sm text-muted-foreground" data-testid="layers-none">No layer matches.</p>}
        </div>
      </section>

      <section className="grid min-w-0 content-start gap-3">
        {sources.length > 1 && (
          <div className="flex flex-wrap gap-1" role="tablist" aria-label="Sheet">
            {sources.map((s, i) => (
              <Button key={s.sha1} size="sm" variant={i === sheet ? 'default' : 'outline'} role="tab" aria-selected={i === sheet} onClick={() => setSheet(i)} data-testid="layers-sheet">
                <span className="max-w-48 truncate">{s.name}</span>
              </Button>
            ))}
          </div>
        )}
        <div className="h-[420px] overflow-hidden rounded-lg border bg-white" data-testid="layers-canvas">
          {plan ? (
            <PlanCanvas
              plan={plan}
              roleOf={i => role(plan.layers[i] ?? '')}
              highlightLayer={highlight >= 0 ? highlight : null}
              selected={new Set()}
              setAside={new Set()}
              tool="pan"
              onHover={info => setHovered(info ? info.layer : null)}
            />
          ) : (
            <p className="p-4 text-sm text-muted-foreground">{planQs[sheet]?.isError ? 'The sheet could not be loaded.' : 'Loading the sheet...'}</p>
          )}
        </div>
        {pickedRow && (
          <div className="grid gap-1 rounded-lg border bg-background p-3 text-sm" data-testid="layer-detail">
            <p className="font-mono text-xs font-semibold">{pickedRow.name}</p>
            <p>{`${roleLabel(role(pickedRow.name))}: ${roleHelp(role(pickedRow.name))}`}</p>
            {pickedRow.read && <p className="text-xs text-muted-foreground">{typesText(pickedRow.read.byType) || 'no items'}</p>}
            {pickedSuggestion && (
              <div className="text-xs">
                <p className="font-medium">{`Suggested: ${roleLabel(pickedSuggestion.role)} (${SUGGESTION_FROM[pickedSuggestion.from]})`}</p>
                <ul className="list-disc pl-4" data-testid="layer-evidence">
                  {pickedSuggestion.evidence.map((e, i) => <li key={i}>{e}</li>)}
                </ul>
                {suggestionToCheck(pickedSuggestion) && (
                  <p className="mt-1 font-medium text-amber-700" data-testid="layer-check-reason">{`Check this one: ${suggestionToCheck(pickedSuggestion)}`}</p>
                )}
              </div>
            )}
            {role(pickedRow.name) === 'ignore' && near.has(pickedRow.name) && <p className="text-xs text-amber-700">{CLOSE_TO_WALLS}</p>}
          </div>
        )}
      </section>
    </div>
  );
}
