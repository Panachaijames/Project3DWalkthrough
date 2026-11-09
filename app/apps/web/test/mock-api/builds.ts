// The mock API's upload-milestone routes (docs/upload/DESIGN.md U-13.1; WORK_BREAKDOWN U6 "the mock API's new routes"):
// createProject and listOffices, in-memory uploads (raw parts, completion with the magic-byte check, dedupe by sha1) and
// builds whose runs complete from the fixtures (fixtures/upload: the bank's prepare and build), step by step: every
// getBuild moves the run on by `config.stepsPerRequest` steps (`config.hold` keeps it still), so the screens see
// queued -> running -> done with their progress. A prepare adopts the proposal as revision 1 when it ends (U-3.3); a
// units change in a settings PUT rescales that source's boxes and starts a one-source prepare (U-7.4); runBuild's 409s
// (run_in_progress, not_prepared, build_saved, units_unconfirmed, layers_not_reviewed); Cancel sets cancelRequested and
// ends the run `config.cancelAfter` requests later; saveBuild makes a version in memory (the bank's v2 files) once.
// Sources: the bank's two DWGs read as the fixtures of I1201 / I1202 (by sha1, else by position); a DXF reads as the
// synthetic hostile drawing (synthetic.ts). Raw files are served as stored, with the source's own sha1 and name.
import { randomBytes } from 'node:crypto';
import path from 'node:path';
import { gunzipSync, gzipSync } from 'node:zlib';
import type * as C from '../../src/upload/contracts';
import type { VersionDetail } from '../../src/api/generated/types.gen';
import { FIXTURES_DIR, PROTOTYPES_DIR, readBytes, readJson, type MockVersionSource } from './fixtures';
import { error, file, json, JSON_TYPE, noContent, sha1Hex, validation, type MockRequest, type MockResponse } from './http';
import { syntheticConversion, syntheticDrawing, syntheticPlan, syntheticSuggestions } from './synthetic';

const F = (...p: string[]) => path.join(FIXTURES_DIR, ...p);
const P = (...p: string[]) => path.join(PROTOTYPES_DIR, ...p);
const U = (...p: string[]) => F('upload', ...p);

export const BANK1_SHA1 = '459d40fc230607ffe35e2ee9d443cd2b0105dc36';
export const BANK2_SHA1 = '6551bdc6f0cff4e31e83b68a55d22cf42703029a';
const BANK_FIXTURES = [
  {
    sha1: BANK1_SHA1,
    conversion: U('conversion', 'bank1.conversion.json'),
    drawing: U('drawing', 'bank1.drawing.json'),
    plan: U('plan', 'bank1.plan.json.gz'),
  },
  {
    sha1: BANK2_SHA1,
    conversion: U('runs', 'bank-prepare', 'out', 'sources', BANK2_SHA1, 'conversion.json'),
    drawing: U('runs', 'bank-prepare', 'out', 'sources', BANK2_SHA1, 'drawing.json'),
    plan: U('runs', 'bank-prepare', 'out', 'sources', BANK2_SHA1, 'plan.json.gz'),
  },
];
export const BUILD_FILES = {
  model: F('models', 'bank-v2.model.json'),
  stages: F('stages', 'bank-v2.stages.json'),
  presentation: U('runs', 'bank-build', 'out', 'presentation.json'),
  overlay: U('overlay', 'bank.overlay.json'),
  proposal: U('runs', 'bank-prepare', 'out', 'proposed-settings.json'),
  suggestions: U('runs', 'bank-prepare', 'out', 'suggestions.json'),
  buildJob: U('runs', 'bank-build', 'job.json'),
  topview: P('bank_test', 'src', 'bank_topview.png'),
  maxScript: P('bank_test', 'Bangkok_Bank_Sampeng.ms'),
  csv: F('csv', 'bank-v2.csv'),
  csvTyped: F('csv', 'bank-v2-typed.csv'),
  office: U('mappings', 'dwp-revit.json'),
};

export const PART_BYTES = 8_388_608;
export const MAX_UPLOAD_BYTES = 300 * 1024 * 1024;
export const SETTINGS_MAX_BYTES = 8 * 1024 * 1024;
/** Reserved project ids (U-13.3). */
export const RESERVED_IDS = ['new', 'bank-sampeng', 'presidential-suite', 'sukhumvit-house', 'hotel-lobby'];

export interface MockBuildConfig {
  partBytes: number;
  maxUploadBytes: number;
  /** Run steps each getBuild moves a running run on (Infinity: the run ends at the next getBuild). */
  stepsPerRequest: number;
  /** Runs stay where they are. */
  hold: boolean;
  /** The next build run fails at its 'detect' step with this error. */
  failBuild: { code: C.RunErrorCode; message: string } | null;
  /** getBuild requests between Cancel and the run's 'cancelled' (Stopping... meanwhile). */
  cancelAfter: number;
  settingsMaxBytes: number;
  /** false: a finished prepare is not adopted yet (the units select stays disabled, U-3.3) until it is set true again. */
  adopt: boolean;
  /** Per source sha1: another conversion report / drawing read fixture file (absolute path), e.g. the suite's loss. */
  conversionFixture: Record<string, string>;
  drawingFixture: Record<string, string>;
  /** Flags added to every overlay (their floor as given). */
  extraFlags: C.Flag[];
  /** The next prepare run fails at its first step with this error, publishing a 'failed' conversion report for every
   *  DWG it reads (as the worker does, so the Files step can say why: UR, V3-9). */
  failPrepare: { code: C.RunErrorCode; message: string } | null;
}

export interface UploadHost {
  hasProject(id: string): boolean;
  createProject(p: { id: string; name: string; shortName: string; projectNo: string | null; office: string | null }): void;
  latestVersion(id: string): number;
  addVersion(v: MockVersionSource): void;
  versionDetail(id: string, n: number): VersionDetail | null;
  projectDetail(id: string): unknown;
  projectName(id: string): { name: string; shortName: string; projectNo: string | null } | null;
}

interface SourceRec { sha1: string; name: string; bytes: number; kind: 'dwg' | 'dxf'; formatVersion: string | null; uploadedAt: string; data: Buffer }
interface SessionRec { s: C.UploadSession; parts: Map<number, Buffer>; createdAt: string }
interface ReadRec { units: C.Units; index: number }
interface RunRec {
  info: C.RunInfo;
  cursor: number;
  cancelAt: number | null;
  settings: C.BuildSettings;
  revision: number;
  fail: { code: C.RunErrorCode; message: string } | null;
}
interface ResultRec {
  runId: string;
  finishedAt: string;
  settingsRevision: number;
  settings: C.BuildSettings;
}
export interface BuildRec {
  id: string;
  projectId: string;
  createdAt: string;
  updatedAt: string;
  status: 'open' | 'saved';
  sources: string[];
  from: C.BuildRecord['from'];
  savedVersion: number | null;
  layersReviewedAt: string | null;
  revision: number;
  settings: C.BuildSettings;
  /** The settings to adopt when the first prepare ends (a `from` build or version), else null: the proposal. */
  startFrom: { settings: C.BuildSettings; reviewed: boolean } | null;
  runs: RunRec[];
  read: Map<string, ReadRec>;
  suggestions: Record<string, C.LayerSuggestion>;
  results: ResultRec[];
}

export interface UploadMock {
  config: MockBuildConfig;
  handle(req: MockRequest, method: string, parts: string[]): MockResponse | null;
  builds(projectId: string): BuildRec[];
  build(projectId: string, buildId: string): BuildRec | null;
  /** Ends every run (of one build, or all) as done. */
  finishRuns(projectId?: string, buildId?: string): void;
  offices(): C.OfficeInfo[];
  office(id: string): C.OfficeMapping | null;
  sources(projectId: string): C.SourceFile[];
  sessions(): C.UploadSession[];
  /** The settings saved with a version made by saveBuild. */
  versionSettings(projectId: string, version: number): C.BuildSettings | null;
  /** Adds a build directly (tests): its sources must have been added with addSource. */
  addSource(projectId: string, src: { name: string; bytes: Buffer; kind?: 'dwg' | 'dxf' }): C.SourceFile;
  createBuildNow(projectId: string, sources: string[], opts?: { finish?: boolean; reviewed?: boolean; built?: boolean }): BuildRec;
}

const now = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
const hex = (n: number) => randomBytes(Math.ceil(n / 2)).toString('hex').slice(0, n);
const UNIT_M: Record<C.Units, number> = { mm: 0.001, cm: 0.01, m: 1, in: 0.0254, ft: 0.3048 };

function buildId(): string {
  const d = new Date();
  const p = (n: number, w = 2) => String(n).padStart(w, '0');
  return `${d.getUTCFullYear()}${p(d.getUTCMonth() + 1)}${p(d.getUTCDate())}T${p(d.getUTCHours())}${p(d.getUTCMinutes())}${p(d.getUTCSeconds())}-${hex(6)}`;
}

/** U-13.3's slug: NFKD, ASCII letters and digits, the rest to '-', 2 - 40 characters cut at a '-'; '' when nothing is left. */
export function slugOf(name: string, max = 40): string {
  let s = name.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  if (s.length > max) {
    const cut = s.slice(0, max);
    const at = cut.lastIndexOf('-');
    s = (at >= 2 ? cut.slice(0, at) : cut).replace(/-+$/g, '');
  }
  return s.length >= 2 ? s : '';
}

function namingOf(name: string, shortName: string): C.ProjectNaming {
  const words = name.normalize('NFKD').replace(/[^\x20-\x7e]/g, ' ').split(/[^A-Za-z0-9]+/).filter(Boolean);
  const photo = shortName.normalize('NFKD').replace(/[^A-Za-z0-9_.-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 64) || 'Project';
  const initials = words.slice(0, 4).map(w => w[0]!.toUpperCase()).join('').replace(/[^A-Z]/g, '');
  const prefix = (initials.slice(0, 4) || 'XX').padEnd(2, 'X');
  const fileStem = (words.join('_').slice(0, 57) || 'Project');
  return { photoName: photo, maxPrefix: prefix, maxFileName: `${fileStem}.ms` };
}

const PREPARE_LABEL = (verb: string, name: string) => `${verb} ${name}`;

function prepareSteps(sources: SourceRec[], only: string[] | null): { name: string; label: string }[] {
  const out: { name: string; label: string }[] = [];
  sources.forEach((s, i) => {
    if (only && !only.includes(s.sha1)) return;
    if (s.kind === 'dwg' && !only) {
      out.push({ name: `convert:${i}`, label: PREPARE_LABEL('Converting', s.name) });
      out.push({ name: `check:${i}`, label: PREPARE_LABEL('Checking', s.name) });
    }
    out.push({ name: `read:${i}`, label: PREPARE_LABEL('Reading', s.name) });
  });
  if (!only) out.push({ name: 'suggest', label: 'Suggesting layer roles' });
  return out;
}

function buildSteps(settings: C.BuildSettings): { name: string; label: string }[] {
  const job = readJson(BUILD_FILES.buildJob) as C.JobRecord;
  const fixed = job.steps.filter(s => !s.name.startsWith('detect:'));
  const out: { name: string; label: string }[] = [];
  for (const s of fixed) {
    if (s.name === 'walls') {
      for (const f of settings.floors) out.push({ name: `detect:${f.key}`, label: `Finding doors and windows on ${f.name}` });
    }
    out.push({ name: s.name, label: s.label });
  }
  return out;
}

const magic = (b: Buffer) => b.subarray(0, 32).toString('latin1');

/** U-5.1's first-bytes check: the kind, or an error code. */
export function checkMagic(kind: 'dwg' | 'dxf', data: Buffer): { ok: true; formatVersion: string | null } | { ok: false; code: string; message: string } {
  const head = magic(data);
  if (kind === 'dwg') {
    const m = /^AC(\d{4})/.exec(head);
    if (m) {
      const n = Number(m[1]);
      if (n >= 1012) return { ok: true, formatVersion: head.slice(0, 6) };
      return { ok: false, code: 'unsupported_version', message: 'This DWG is older than R13: save it as a newer DWG, or export a DXF.' };
    }
    if (/^AC[12]\./.test(head)) return { ok: false, code: 'unsupported_version', message: 'This DWG is older than R13: save it as a newer DWG, or export a DXF.' };
    return { ok: false, code: 'bad_kind', message: 'This file is not a DWG drawing.' };
  }
  if (head.startsWith('AutoCAD Binary DXF\r\n\x1a\x00')) return { ok: true, formatVersion: null };
  const text = data.subarray(0, 4096).toString('latin1');
  const lines = text.split(/\r?\n/).map(l => l.trim());
  let i = 0;
  while (i < lines.length && lines[i] === '') i++;
  while (lines[i] === '999') i += 2;
  if (lines[i] === '0' && lines[i + 1] === 'SECTION') {
    const v = /\$ACADVER\s*\r?\n\s*1\s*\r?\n\s*(AC\d{4})/.exec(data.toString('latin1'));
    return { ok: true, formatVersion: v ? v[1]! : null };
  }
  return { ok: false, code: 'bad_kind', message: 'This file is not a DXF drawing.' };
}

export function createUploadMock(host: UploadHost): UploadMock {
  const config: MockBuildConfig = {
    partBytes: PART_BYTES,
    maxUploadBytes: MAX_UPLOAD_BYTES,
    stepsPerRequest: 1,
    hold: false,
    failBuild: null,
    cancelAfter: 1,
    settingsMaxBytes: SETTINGS_MAX_BYTES,
    adopt: true,
    conversionFixture: {},
    drawingFixture: {},
    extraFlags: [],
    failPrepare: null,
  };
  /** Per build id and source sha1: the notes of a conversion that failed in the build's newest prepare. */
  const failedConversions = new Map<string, Map<string, string[]>>();
  const sessions = new Map<string, SessionRec>();
  const sources = new Map<string, Map<string, SourceRec>>();          // projectId -> sha1 -> source
  const builds = new Map<string, Map<string, BuildRec>>();            // projectId -> buildId -> build
  const versionSettings = new Map<string, C.BuildSettings>();         // `${projectId}/${n}`
  const offices = new Map<string, C.OfficeMapping>();
  /** The office a project was made with (createProject), for its proposals. */
  const projectOffices = new Map<string, string | null>();
  const officeFixture = readJson(BUILD_FILES.office) as C.OfficeMapping;
  offices.set(officeFixture.id, clone(officeFixture));

  const sourcesOf = (pid: string) => { let m = sources.get(pid); if (!m) { m = new Map(); sources.set(pid, m); } return m; };
  const buildsOf = (pid: string) => { let m = builds.get(pid); if (!m) { m = new Map(); builds.set(pid, m); } return m; };
  const buildUrl = (b: BuildRec) => `/api/projects/${b.projectId}/builds/${b.id}`;
  const srcRec = (b: BuildRec, sha1: string) => sourcesOf(b.projectId).get(sha1)!;
  const sourceFile = (s: SourceRec): C.SourceFile => ({ sha1: s.sha1, name: s.name, bytes: s.bytes, kind: s.kind, formatVersion: s.formatVersion, uploadedAt: s.uploadedAt });

  // ------------------------------------------------------------------------------------------- raw files per source
  const fixtureOf = (b: BuildRec, sha1: string) => {
    const s = srcRec(b, sha1);
    if (s.kind === 'dxf') return null;
    const byHash = BANK_FIXTURES.find(f => f.sha1 === sha1);
    if (byHash) return byHash;
    const i = b.sources.indexOf(sha1);
    return BANK_FIXTURES[(i < 0 ? 0 : i) % BANK_FIXTURES.length]!;
  };
  const rawCache = new Map<string, unknown>();
  function cached<T>(key: string, make: () => T): T {
    if (!rawCache.has(key)) rawCache.set(key, make());
    return rawCache.get(key) as T;
  }
  function conversionOf(b: BuildRec, sha1: string): C.ConversionReport {
    const s = srcRec(b, sha1);
    const fx = fixtureOf(b, sha1);
    const over = config.conversionFixture[sha1];
    if (!fx && !over) return syntheticConversion(s);
    const r = clone(readJson(over ?? fx!.conversion) as C.ConversionReport);
    r.source = { ...r.source, sha1, name: s.name, bytes: s.bytes };
    return r;
  }
  function drawingOf(b: BuildRec, sha1: string): C.DrawingRead {
    const s = srcRec(b, sha1);
    const fx = fixtureOf(b, sha1);
    const units = b.read.get(sha1)?.units ?? 'mm';
    const over = config.drawingFixture[sha1];
    return cached(`drawing:${sha1}:${s.name}:${units}:${over ?? fx?.drawing ?? 'synthetic'}`, () => {
      const d = over || fx ? clone(readJson(over ?? fx!.drawing) as C.DrawingRead) : syntheticDrawing(s);
      d.source = { sha1, name: s.name };
      if (units !== d.units.used) d.units = { ...d.units, used: units, verdict: d.units.declared === units ? 'agree' : 'votes-win' };
      return d;
    });
  }
  function planOf(b: BuildRec, sha1: string): Buffer {
    const fx = fixtureOf(b, sha1);
    const units = b.read.get(sha1)?.units ?? 'mm';
    return cached(`plan:${sha1}:${units}:${fx?.plan ?? 'synthetic'}`, () => {
      const p = fx ? JSON.parse(gunzipSync(readBytes(fx.plan)).toString('utf8')) as C.PlanGeometry : syntheticPlan(sha1);
      p.source = sha1;
      p.units = units;
      return gzipSync(Buffer.from(JSON.stringify(p), 'utf8'), { level: 6 });
    });
  }

  // ------------------------------------------------------------------------------------------------ the proposal
  function proposal(b: BuildRec): C.BuildSettings {
    const base = readJson(BUILD_FILES.proposal) as C.BuildSettings;
    const srcs = b.sources.map(sha => srcRec(b, sha));
    const allDxf = srcs.every(s => s.kind === 'dxf');
    const names = host.projectName(b.projectId);
    const naming = names && !RESERVED_IDS.includes(b.projectId) ? namingOf(names.name, names.shortName) : base.project;
    const layers: Record<string, C.LayerRole> = {};
    const sugg = suggestionsOf(b);
    for (const [k, v] of Object.entries(sugg)) layers[k] = v.role;
    return {
      ...clone(base),
      office: projectOffices.get(b.projectId) ?? null,
      project: {
        ...clone(base.project),
        ...(names && !RESERVED_IDS.includes(b.projectId) ? { name: names.name, shortName: names.shortName, projectNo: names.projectNo } : {}),
        ...naming,
        exportedFrom: allDxf ? null : base.project.exportedFrom,
      },
      sources: srcs.map(s => ({ sha1: s.sha1, name: s.name, kind: s.kind, units: b.read.get(s.sha1)?.units ?? 'mm', unitsConfirmed: true })),
      layers,
      floors: srcs.map((s, i) => {
        const f = base.floors[i];
        return {
          key: f?.key ?? `L${i + 1}`,
          name: f?.name ?? `Level ${i + 1}`,
          source: s.sha1,
          area: { kind: 'wholeFile' as const },
          level: f?.level ?? Math.round(i * 3.7 * 1000) / 1000,
          wallHeight: f?.wallHeight ?? 3.7,
          slabThickness: null, doorHead: null, windowSill: null, windowHead: null,
          align: { method: 'auto' as const },
        };
      }),
    };
  }
  function suggestionsOf(b: BuildRec): Record<string, C.LayerSuggestion> {
    const out: Record<string, C.LayerSuggestion> = {};
    for (const sha of b.sources) {
      const s = srcRec(b, sha);
      const fromFile = s.kind === 'dxf' ? syntheticSuggestions() : (readJson(BUILD_FILES.suggestions) as C.LayerSuggestions).layers;
      for (const [k, v] of Object.entries(fromFile)) if (!(k in out)) out[k] = clone(v);
    }
    return out;
  }

  // --------------------------------------------------------------------------------------------------- the runs
  function startRun(b: BuildRec, kind: C.RunKind, only: string[] | null): RunRec {
    const n = b.runs.length + 1;
    const runId = `${String(n).padStart(4, '0')}-${kind}`;
    const srcs = b.sources.map(sha => srcRec(b, sha));
    const steps = kind === 'prepare' ? prepareSteps(srcs, only) : buildSteps(b.settings);
    const run: RunRec = {
      info: {
        id: runId, kind, status: 'queued', step: null, progress: 0,
        steps: steps.map(s => ({ ...s, status: 'waiting', seconds: null, note: '' })),
        messages: [{ at: now(), level: 'info', text: kind === 'prepare' ? 'Waiting to read the drawings' : 'Waiting to build' }],
        error: null, queuedAt: now(), startedAt: null, finishedAt: null, cancelRequested: false, only,
      },
      cursor: -1,
      cancelAt: null,
      settings: clone(b.settings),
      revision: b.revision,
      fail: kind === 'build' ? config.failBuild : config.failPrepare,
    };
    if (kind === 'prepare') { config.failPrepare = null; failedConversions.delete(b.id); }
    b.runs.push(run);
    b.updatedAt = now();
    return run;
  }
  const activeRun = (b: BuildRec) => b.runs.find(r => r.info.status === 'queued' || r.info.status === 'running') ?? null;
  const lastRun = (b: BuildRec) => b.runs[b.runs.length - 1] ?? null;

  function finish(b: BuildRec, run: RunRec, status: C.RunStatus, err: { code: string; message: string; step: string | null } | null) {
    run.info.status = status;
    run.info.finishedAt = now();
    run.info.error = err;
    run.info.cancelRequested = false;
    run.info.progress = status === 'done' ? 1 : run.info.progress;
    run.info.messages.push({ at: now(), level: status === 'done' ? 'info' : 'error', text: status === 'done' ? 'Done' : err?.message ?? status });
    if (status !== 'done') return;
    if (run.info.kind === 'prepare') {
      for (const sha of run.info.only ?? b.sources) {
        const d = run.settings.sources.find(s => s.sha1 === sha);
        b.read.set(sha, { units: d?.units ?? b.read.get(sha)?.units ?? 'mm', index: b.sources.indexOf(sha) });
      }
      adoptIfReady(b);
    } else {
      b.results.push({ runId: run.info.id, finishedAt: run.info.finishedAt!, settingsRevision: run.revision, settings: run.settings });
    }
    b.updatedAt = now();
  }

  /** The first prepare's proposal (or the `from` settings) becomes revision 1 (U-3.3), once, when config.adopt. */
  function adoptIfReady(b: BuildRec) {
    if (b.revision !== 0 || !config.adopt) return;
    if (!b.runs.some(r => r.info.kind === 'prepare' && r.info.status === 'done')) return;
    b.suggestions = suggestionsOf(b);
    if (b.startFrom) {
      const s = clone(b.startFrom.settings);
      s.sources = b.sources.map(sha => {
        const prev = s.sources.find(x => x.sha1 === sha);
        const r = srcRec(b, sha);
        return prev ?? { sha1: sha, name: r.name, kind: r.kind, units: b.read.get(sha)?.units ?? 'mm', unitsConfirmed: true };
      });
      // floors re-pointed at sources by file name (U-3.3)
      s.floors = s.floors.map(f => {
        const was = b.startFrom!.settings.sources.find(x => x.sha1 === f.source);
        const same = was ? s.sources.find(x => x.name === was.name) : null;
        return same ? { ...f, source: same.sha1 } : f;
      });
      b.settings = s;
      if (b.startFrom.reviewed) b.layersReviewedAt = now();
    } else {
      b.settings = proposal(b);
    }
    b.revision = 1;
    b.updatedAt = now();
  }

  function advance(b: BuildRec) {
    const run = activeRun(b);
    if (!run) return;
    if (run.info.cancelRequested && run.cancelAt !== null) {
      if (run.cancelAt <= 0) {
        const at = run.info.step;
        for (const s of run.info.steps) if (s.status === 'running') s.status = 'failed';
        finish(b, run, 'cancelled', { code: 'cancelled', message: 'The run was cancelled.', step: at });
        return;
      }
      run.cancelAt--;
      return;
    }
    if (config.hold) return;
    let moves = config.stepsPerRequest;
    while (moves-- > 0 && (run.info.status === 'queued' || run.info.status === 'running')) {
      if (run.info.status === 'queued') {
        run.info.status = 'running';
        run.info.startedAt = now();
        run.cursor = 0;
        const first = run.info.steps[0];
        if (first) { first.status = 'running'; run.info.step = first.name; }
        run.info.messages.push({ at: now(), level: 'info', text: first ? `${first.label}...` : 'Started' });
        continue;
      }
      const cur = run.info.steps[run.cursor];
      if (cur && run.fail && cur.name.startsWith('detect:')) {
        cur.status = 'failed';
        finish(b, run, 'failed', { code: run.fail.code, message: run.fail.message, step: cur.name });
        return;
      }
      if (cur && run.fail && run.info.kind === 'prepare') {
        cur.status = 'failed';
        const notes = new Map<string, string>();
        for (const sha of b.sources) if (srcRec(b, sha).kind === 'dwg') notes.set(sha, `${srcRec(b, sha).name}: ${run.fail.message}`);
        failedConversions.set(b.id, new Map([...notes].map(([k, v]) => [k, [v]])));
        finish(b, run, 'failed', { code: run.fail.code, message: run.fail.message, step: cur.name });
        return;
      }
      if (cur) { cur.status = 'done'; cur.seconds = 0.5; }
      run.cursor++;
      run.info.progress = run.info.steps.length ? Math.min(1, run.cursor / run.info.steps.length) : 1;
      const next = run.info.steps[run.cursor];
      if (next) {
        next.status = 'running';
        run.info.step = next.name;
        run.info.messages.push({ at: now(), level: 'info', text: `${next.label}...` });
      } else {
        finish(b, run, 'done', null);
      }
    }
  }

  // --------------------------------------------------------------------------------------------------- the detail
  function sourceInfo(b: BuildRec, sha1: string): C.BuildSourceInfo {
    const s = srcRec(b, sha1);
    const read = b.read.get(sha1);
    const base = `${buildUrl(b)}/sources/${sha1}`;
    if (!read) {
      // a failed conversion of the newest prepare reaches the Files step (the API's failed_conversion: UR, V3-9)
      const failed = failedConversions.get(b.id)?.get(sha1);
      const conversion = failed ? { verdict: 'failed' as const, notes: failed, lostInModelSpace: 0 } : null;
      return { sha1, name: s.name, bytes: s.bytes, kind: s.kind, conversion, units: null, urls: null };
    }
    const conv = conversionOf(b, sha1);
    const d = drawingOf(b, sha1);
    return {
      sha1, name: s.name, bytes: s.bytes, kind: s.kind,
      // the placements of lost blocks in the plan, as the API counts them (U5.md; UR, V2-2: the mock sent the missing
      // item count, so the Files step's "4 items" read right against the mock only)
      conversion: { verdict: conv.verdict, notes: conv.notes, lostInModelSpace: conv.lostBlocks.reduce((a, lb) => a + lb.inserts.length, 0) },
      units: { declared: d.units.declared, used: d.units.used, verdict: d.units.verdict, note: d.units.note },
      urls: { conversion: `${base}/conversion`, drawing: `${base}/drawing`, plan: `${base}/plan` },
    };
  }

  const setAsideOn = (s: C.BuildSettings, floor: string) => s.fixes.setAside.filter(r => r.floor === floor).length;
  /** The API's is_stale: the settings changed since the run in more than the office (UR, V3-1). */
  const recipe = (s: C.BuildSettings) => JSON.stringify({ ...s, office: null });
  const isStale = (b: BuildRec, r: ResultRec) => r.settingsRevision !== b.revision && recipe(r.settings) !== recipe(b.settings);
  function resultFloors(r: ResultRec): C.BuildResultInfo['floors'] {
    const m = readJson(BUILD_FILES.model) as { parts: { floor: string }[]; openings: { floor: string; kind: string }[]; furniture?: { floor: string }[]; rooms: { floor: string }[]; floors: { key: string }[] };
    return r.settings.floors.map((f, i) => {
      const mk = m.floors[i % m.floors.length]!.key;
      const ops = m.openings.filter(o => o.floor === mk);
      const count = (k: string) => ops.filter(o => o.kind === k).length;
      return {
        key: f.key, name: f.name, level: f.level,
        parts: Math.max(0, m.parts.filter(p => p.floor === mk).length - setAsideOn(r.settings, f.key)),
        openings: { door: count('door'), window: count('window'), passage: count('passage') },
        furniture: (m.furniture ?? []).filter(x => x.floor === mk).length,
        rooms: m.rooms.filter(x => x.floor === mk).length,
      };
    });
  }
  function resultInfo(b: BuildRec, r: ResultRec): C.BuildResultInfo {
    const floors = resultFloors(r);
    const overlay = overlayOf(b, r);
    const byKind: Record<string, number> = {};
    for (const f of overlay.flags) byKind[f.kind] = (byKind[f.kind] ?? 0) + 1;
    const url = buildUrl(b);
    return {
      runId: r.runId,
      finishedAt: r.finishedAt,
      stale: isStale(b, r),
      settingsRevision: r.settingsRevision,
      counts: {
        floors: floors.length,
        parts: floors.reduce((a, f) => a + f.parts, 0),
        openings: floors.reduce((a, f) => a + f.openings.door + f.openings.window + f.openings.passage, 0),
        furniture: floors.reduce((a, f) => a + f.furniture, 0),
        furnitureKinds: 14,
        rooms: floors.reduce((a, f) => a + f.rooms, 0),
      },
      floors,
      flags: { total: overlay.flags.length, check: overlay.flags.filter(f => f.severity === 'check').length, byKind },
      stamp: sha1Hex(readBytes(BUILD_FILES.model)).slice(0, 12),
      presentation: readJson(BUILD_FILES.presentation) as Record<string, unknown>,
      urls: { model: `${url}/model`, stages: `${url}/stages`, overlay: `${url}/overlay`, diff: `${url}/diff`, topview: `${url}/topview`, maxScript: `${url}/max-script` },
      seconds: { total: 4.5 },
    };
  }

  function detail(b: BuildRec, withSettings: boolean): C.BuildDetail {
    const run = activeRun(b) ?? lastRun(b);
    const last = b.results[b.results.length - 1];
    const url = buildUrl(b);
    return {
      id: b.id, projectId: b.projectId, createdAt: b.createdAt, updatedAt: b.updatedAt, status: b.status,
      savedVersion: b.savedVersion,
      sourceNames: b.sources.map(sha => srcRec(b, sha).name),
      runStatus: lastRun(b)?.info.status ?? null,
      url,
      sources: b.sources.map(sha => sourceInfo(b, sha)),
      settings: withSettings ? clone(b.settings) : null,
      settingsRevision: b.revision,
      layersReviewedAt: b.layersReviewedAt,
      suggestions: b.revision >= 1 ? clone(b.suggestions) : {},
      run: run ? clone(run.info) : null,
      result: last ? resultInfo(b, last) : null,
      urls: { settings: `${url}/settings`, run: `${url}/run`, cancel: `${url}/cancel`, save: `${url}/save` },
    };
  }
  const summary = (b: BuildRec): C.BuildSummary => {
    const d = detail(b, false);
    return { id: d.id, projectId: d.projectId, createdAt: d.createdAt, updatedAt: d.updatedAt, status: d.status, savedVersion: d.savedVersion, sourceNames: d.sourceNames, runStatus: d.runStatus, url: d.url };
  };

  // ------------------------------------------------------------------------------------------- overlay and diff
  function overlayOf(b: BuildRec, r: ResultRec): C.BuildOverlay {
    const bank = readJson(BUILD_FILES.overlay) as C.BuildOverlay;
    const floors = r.settings.floors.map((f, i) => {
      const of = clone(bank.floors[i % bank.floors.length]!);
      return { ...of, key: f.key, source: f.source, area: f.area, setAside: r.settings.fixes.setAside.filter(s => s.floor === f.key).map(s => s.key) };
    });
    const keyMap = new Map(bank.floors.map((f, i) => [f.key, r.settings.floors[i]?.key ?? null]));
    const flags = bank.flags
      .map(f => ({ ...clone(f), floor: f.floor === null ? null : keyMap.get(f.floor) ?? null }))
      .filter(f => f.floor !== null || f.kind === 'units');
    return { format: 'build-overlay/1', floors, flags: [...flags, ...clone(config.extraFlags)] };
  }
  function diffOf(b: BuildRec, r: ResultRec): C.BuildDiff {
    const idx = b.results.indexOf(r);
    const against: C.BuildDiff['against'] = [];
    const now = resultFloors(r);
    const prev = idx > 0 ? b.results[idx - 1]! : null;
    const body = (before: C.BuildResultInfo['floors'] | null): C.DiffBody => {
      const counts: C.DiffBody['counts'] = {};
      for (const f of now) {
        counts[f.key] = {};
        const was = before?.find(x => x.key === f.key);
        if (was && was.parts !== f.parts) counts[f.key]!.parts = [was.parts, f.parts];
      }
      return { counts, partsAdded: [], partsRemoved: [], openingsAdded: [], openingsRemoved: [], openingsChanged: [], furnitureByKind: {}, roomsAdded: [], roomsRemoved: [] };
    };
    if (prev) against.push({ kind: 'previous-run', ref: prev.runId, diff: body(resultFloors(prev)) });
    const latest = host.latestVersion(b.projectId);
    if (latest >= 1) against.push({ kind: 'version', ref: `v${latest}`, diff: body(resultFloors({ ...r, settings: { ...r.settings, fixes: { ...r.settings.fixes, setAside: [] } } })) });
    return { format: 'build-diff/1', against };
  }

  // ------------------------------------------------------------------------------------------- settings checks
  function settingsIssues(s: C.BuildSettings, b: BuildRec): { path: string; message: string }[] {
    const out: { path: string; message: string }[] = [];
    if (s.format !== 'build-settings/1') out.push({ path: 'format', message: 'must be build-settings/1' });
    const keys = new Set<string>();
    s.floors.forEach((f, i) => {
      if (!/^[A-Za-z0-9_]{1,32}$/.test(f.key)) out.push({ path: `floors/${i}/key`, message: 'a floor key is letters, digits and _ (at most 32)' });
      if (keys.has(f.key)) out.push({ path: `floors/${i}/key`, message: 'floor keys must be unique' });
      keys.add(f.key);
      if (i > 0 && !(f.level > s.floors[i - 1]!.level)) out.push({ path: `floors/${i}/level`, message: 'levels must increase' });
      if (!(f.wallHeight >= 0.05 && f.wallHeight <= 50)) out.push({ path: `floors/${i}/wallHeight`, message: 'wall height 0.05 - 50 m' });
      if (!b.sources.includes(f.source)) out.push({ path: `floors/${i}/source`, message: 'not a source of the build' });
      if (f.area.kind === 'box' && !(f.area.bbox[0] < f.area.bbox[2] && f.area.bbox[1] < f.area.bbox[3])) out.push({ path: `floors/${i}/area`, message: 'an empty box' });
    });
    // the furniture size limits, as the API's settings_issues (U-13.2: 0 - 10 m; no depth limit is null)
    if (!(s.furniture.minSize >= 0 && s.furniture.minSize <= 10)) out.push({ path: 'furniture/minSize', message: 'the smallest piece is 0 - 10 m' });
    if (s.furniture.minDepth !== null && !(s.furniture.minDepth >= 0 && s.furniture.minDepth <= 10)) out.push({ path: 'furniture/minDepth', message: 'the smallest depth is 0 - 10 m' });
    if (s.fixes.setAside.length > 20_000) out.push({ path: 'fixes/setAside', message: 'at most 20,000 set-asides' });
    if (s.sources.some(x => x.units === null)) out.push({ path: 'sources', message: 'every source needs its units' });
    if (s.office !== null && !/^[a-z0-9][a-z0-9-]{1,62}$/.test(s.office)) out.push({ path: 'office', message: 'not an office id' });
    return out;
  }

  function rescale(s: C.BuildSettings, sha1: string, k: number): C.BuildSettings {
    const r = (v: number) => Math.round(v * k * 1e6) / 1e6;
    const floorsOf = new Set(s.floors.filter(f => f.source === sha1).map(f => f.key));
    return {
      ...s,
      floors: s.floors.map(f => f.source !== sha1 || f.area.kind !== 'box' ? f
        : { ...f, area: { ...f.area, bbox: f.area.bbox.map(r) as C.Bbox, pad: r(f.area.pad) } }),
      fixes: {
        ...s.fixes,
        openings: s.fixes.openings.map(o => floorsOf.has(o.floor) ? { ...o, a: [r(o.a[0]), r(o.a[1])], b: [r(o.b[0]), r(o.b[1])] } : o),
        outlineEdges: s.fixes.outlineEdges.map(o => floorsOf.has(o.floor) ? { ...o, a: [r(o.a[0]), r(o.a[1])], b: [r(o.b[0]), r(o.b[1])] } : o),
      },
    };
  }

  // ---------------------------------------------------------------------------------------------------- routes
  function createProject(body: string | null | undefined): MockResponse {
    let req: C.NewProjectRequest;
    try { req = JSON.parse(body ?? '') as C.NewProjectRequest; } catch { return validation(['body'], 'JSON decode error', 'json_invalid'); }
    const name = (req.name ?? '').trim();
    if (!name || name.length > 200) return error(422, 'bad_project', 'A project needs a name (at most 200 characters).');
    const shortName = (req.shortName ?? '').trim() || name;
    let id = req.id ?? null;
    if (id !== null && id !== '') {
      if (!/^[a-z0-9][a-z0-9-]{1,39}$/.test(id)) return error(422, 'bad_project', 'A new project id is 2 - 40 lower-case letters, digits and -, starting with a letter or digit.');
      if (id.endsWith('-') || id.includes('--')) return error(422, 'bad_project', 'a project id ends with a letter or digit and has no two hyphens in a row');
      if (RESERVED_IDS.includes(id)) return error(422, 'bad_project', `The id ${id} is reserved.`);
    } else {
      // as the API's derived_project_id: a slug with no letter ('31' of a Thai name) is no id (UR, V2-15)
      const s = slugOf(name);
      id = /[a-z]/.test(s) ? s : `project-${hex(6)}`;
    }
    if (host.hasProject(id) || (RESERVED_IDS.includes(id) && req.id == null)) {
      let n = 2;
      while (host.hasProject(`${id}-${n}`) || RESERVED_IDS.includes(`${id}-${n}`)) n++;
      return error(409, 'project_exists', `There is already a project ${id}.`, { suggested: `${id}-${n}` });
    }
    let office: string | null = null;
    if (req.office) {
      if (!offices.has(req.office)) return error(422, 'bad_project', `There is no office ${req.office}.`);
      office = req.office;
    } else if (req.newOfficeName && req.newOfficeName.trim()) {
      const oid = slugOf(req.newOfficeName, 63) || `office-${hex(6)}`;
      if (!offices.has(oid)) {
        offices.set(oid, { format: 'office-mapping/1', id: oid, name: req.newOfficeName.trim(), createdAt: now(), updatedAt: now(), layers: {}, furnitureWords: {} });
      }
      office = oid;
    }
    host.createProject({ id, name, shortName, projectNo: req.projectNo ?? null, office });
    projectOffices.set(id, office);
    return json(201, host.projectDetail(id));
  }

  function createUpload(body: string | null | undefined): MockResponse {
    let req: C.UploadRequest;
    try { req = JSON.parse(body ?? '') as C.UploadRequest; } catch { return validation(['body'], 'JSON decode error', 'json_invalid'); }
    if (!host.hasProject(req.projectId)) return error(404, 'project_not_found', `There is no project ${req.projectId}.`);
    if (req.bytes > config.maxUploadBytes) {
      const mb = (n: number) => `${(n / 1_000_000).toFixed(1)} MB`;
      return error(413, 'too_large', `${req.fileName} is ${mb(req.bytes)}; at most ${mb(config.maxUploadBytes)} can be uploaded`);
    }
    // eslint-disable-next-line no-control-regex
    if (!/\.(dwg|dxf)$/i.test(req.fileName) || req.fileName.length > 255 || /[\x00-\x1f\x7f]/.test(req.fileName)) {
      return error(422, 'bad_kind', 'Only DWG and DXF drawings can be uploaded (a name ending in .dwg or .dxf).');
    }
    const id = `u${hex(24)}`;
    const parts = Math.max(1, Math.ceil(req.bytes / config.partBytes));
    const s: C.UploadSession = {
      id, projectId: req.projectId, fileName: req.fileName, bytes: req.bytes, partBytes: config.partBytes, parts, received: [],
      expiresAt: new Date(Date.now() + 24 * 3600_000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
      partUrls: Array.from({ length: parts }, (_, i) => `/api/uploads/${id}/parts/${i + 1}`),
      completeUrl: `/api/uploads/${id}/complete`,
      url: `/api/uploads/${id}`,
    };
    sessions.set(id, { s, parts: new Map(), createdAt: now() });
    return json(201, s);
  }

  function putPart(rec: SessionRec, n: number, bytes: Buffer): MockResponse {
    const s = rec.s;
    if (!Number.isInteger(n) || n < 1 || n > s.parts) return error(422, 'bad_part', `There is no part ${n} (1 - ${s.parts}).`);
    const want = n < s.parts ? s.partBytes : s.bytes - (s.parts - 1) * s.partBytes;
    if (bytes.length !== want) return error(422, 'bad_part', `Part ${n} must be ${want} bytes, not ${bytes.length}.`);
    rec.parts.set(n, bytes);
    s.received = [...rec.parts.keys()].sort((a, b) => a - b);
    return json(200, { part: n, bytes: bytes.length } satisfies C.UploadPartResult);
  }

  function complete(rec: SessionRec): MockResponse {
    const s = rec.s;
    const missing: number[] = [];
    for (let i = 1; i <= s.parts; i++) if (!rec.parts.has(i)) missing.push(i);
    if (missing.length) return error(409, 'incomplete', `${missing.length} part(s) are missing.`, { missing });
    const data = Buffer.concat([...Array(s.parts)].map((_, i) => rec.parts.get(i + 1)!));
    const kind: 'dwg' | 'dxf' = /\.dxf$/i.test(s.fileName) ? 'dxf' : 'dwg';
    const m = checkMagic(kind, data);
    if (!m.ok) { sessions.delete(s.id); return error(422, m.code, m.message); }
    const sha1 = sha1Hex(data);
    const store = sourcesOf(s.projectId);
    let src = store.get(sha1);
    if (!src) {
      src = { sha1, name: s.fileName, bytes: data.length, kind, formatVersion: m.formatVersion, uploadedAt: now(), data };
      store.set(sha1, src);
    }
    sessions.delete(s.id);
    return json(201, sourceFile(src));
  }

  function createBuild(pid: string, body: string | null | undefined): MockResponse {
    let req: C.NewBuildRequest;
    try { req = JSON.parse(body ?? '') as C.NewBuildRequest; } catch { return validation(['body'], 'JSON decode error', 'json_invalid'); }
    let startFrom: BuildRec['startFrom'] = null;
    let from: C.BuildRecord['from'] = { kind: 'none' };
    let fromSources: string[] | null = null;
    const f = req.from ?? null;
    const latest = host.latestVersion(pid);
    if (f?.kind === 'build') {
      const other = buildsOf(pid).get(f.build);
      if (!other) return error(404, 'build_not_found', `Project ${pid} has no build ${f.build}.`);
      startFrom = { settings: clone(other.settings), reviewed: !!other.layersReviewedAt };
      from = { kind: 'build', build: f.build };
      fromSources = other.sources;
    } else if (f?.kind === 'version' || f?.kind === 'latest' || (f === null && latest >= 1)) {
      const n = f?.kind === 'version' ? f.version : latest;
      if (f?.kind === 'version' && !host.versionDetail(pid, n)) return error(404, 'version_not_found', `Project ${pid} has no version ${n}.`);
      const vs = versionSettings.get(`${pid}/${n}`);
      // as the API: a version that was not built from uploads (a seeded one) has no settings to take (UR, V3-8: the
      // mock answered 422 bad_sources where the API answers 404 version_not_found)
      if (!vs && f?.kind === 'version') {
        return error(404, 'version_not_found', `v${n} of ${pid} has no build settings: it was not built from uploaded drawings`);
      }
      if (vs) {
        startFrom = { settings: clone(vs), reviewed: true };
        from = { kind: 'version', version: n };
        fromSources = vs.sources.map(x => x.sha1);
      }
    }
    const list = req.sources ?? fromSources;
    if (!list || !list.length) return error(422, 'bad_sources', 'A build needs at least one source file.');
    if (new Set(list).size !== list.length) return error(422, 'bad_sources', 'A source is named twice.');
    for (const sha of list) if (!sourcesOf(pid).has(sha)) return error(404, 'source_not_found', `Project ${pid} has no source ${sha}.`);
    const b = newBuild(pid, list, from, startFrom);
    return json(201, detail(b, true));
  }

  function newBuild(pid: string, list: string[], from: C.BuildRecord['from'], startFrom: BuildRec['startFrom']): BuildRec {
    const t = now();
    const base = readJson(BUILD_FILES.proposal) as C.BuildSettings;
    const b: BuildRec = {
      id: buildId(), projectId: pid, createdAt: t, updatedAt: t, status: 'open', sources: list.slice(), from, savedVersion: null,
      layersReviewedAt: null, revision: 0,
      settings: { ...clone(base), sources: list.map(sha => { const s = sourcesOf(pid).get(sha)!; return { sha1: sha, name: s.name, kind: s.kind, units: null, unitsConfirmed: false }; }), floors: [], layers: {} },
      startFrom, runs: [], read: new Map(), suggestions: {}, results: [],
    };
    buildsOf(pid).set(b.id, b);
    startRun(b, 'prepare', null);
    return b;
  }

  function putSettings(b: BuildRec, req: MockRequest): MockResponse {
    if (b.status === 'saved') return error(409, 'build_saved', `This build was saved as v${b.savedVersion}.`, { version: b.savedVersion });
    if ((req.body ?? '').length > config.settingsMaxBytes) return error(413, 'body_too_large', 'The settings are larger than 8 MiB.');
    if (b.revision === 0) return error(409, 'not_prepared', 'The drawings are still being read: the settings can be saved once the proposal is in.');
    const active = activeRun(b);
    if (active && active.info.kind === 'prepare') return error(409, 'run_in_progress', 'A drawing is being read again: wait for it.');
    const ifMatch = req.headers?.['if-match'] ?? null;
    if (ifMatch !== `"${b.revision}"`) {
      return error(412, 'revision_conflict', 'The settings were changed elsewhere since.', { revision: b.revision, settings: clone(b.settings) });
    }
    let upd: C.BuildSettingsUpdate;
    try { upd = JSON.parse(req.body ?? '') as C.BuildSettingsUpdate; } catch { return validation(['body'], 'JSON decode error', 'json_invalid'); }
    if (!upd || typeof upd !== 'object' || !upd.settings) return validation(['body', 'settings'], 'Field required', 'missing');
    const issues = settingsIssues(upd.settings, b);
    if (issues.length) return error(422, 'invalid_settings', 'The settings cannot be used as they are.', { issues });
    let next = upd.settings;
    const changed: string[] = [];
    for (const src of next.sources) {
      const old = b.settings.sources.find(x => x.sha1 === src.sha1);
      if (old && old.units && src.units && old.units !== src.units) {
        next = rescale(next, src.sha1, UNIT_M[src.units] / UNIT_M[old.units]);
        changed.push(src.sha1);
      }
    }
    b.settings = clone(next);
    b.revision++;
    if (upd.layersReviewed && !b.layersReviewedAt) b.layersReviewedAt = now();
    b.updatedAt = now();
    if (changed.length) startRun(b, 'prepare', changed);
    return json(200, detail(b, true));
  }

  function runBuild(b: BuildRec): MockResponse {
    if (b.status === 'saved') return error(409, 'build_saved', `This build was saved as v${b.savedVersion}.`, { version: b.savedVersion });
    if (activeRun(b)) return error(409, 'run_in_progress', 'A run of this build is going.');
    if (b.revision === 0) {
      // the first reading ended without a proposal: read the files again (the API's first_reading_ended: UR, V3-4)
      const first = b.runs.filter(r => r.info.kind === 'prepare' && !r.info.only).at(-1);
      if (first && ['failed', 'cancelled', 'interrupted'].includes(first.info.status)) {
        startRun(b, 'prepare', null);
        return json(202, detail(b, true));
      }
      return error(409, 'not_prepared', 'The drawings are still being read.');
    }
    if (b.settings.sources.some(s => !s.unitsConfirmed)) return error(409, 'units_unconfirmed', 'Confirm the units of every drawing first (Files step).');
    if (!b.layersReviewedAt) return error(409, 'layers_not_reviewed', 'Look through the Layers step once before building.');
    startRun(b, 'build', null);
    return json(202, detail(b, true));
  }

  function cancelRun(b: BuildRec): MockResponse {
    const run = activeRun(b);
    if (!run) return error(409, 'no_run', 'No run of this build is going.');
    run.info.cancelRequested = true;
    run.cancelAt = config.cancelAfter;
    run.info.messages.push({ at: now(), level: 'warn', text: 'Stopping...' });
    return json(200, detail(b, true));
  }

  function save(b: BuildRec, body: string | null | undefined): MockResponse {
    if (b.status === 'saved') return error(409, 'build_saved', `This build was saved as v${b.savedVersion}.`, { version: b.savedVersion });
    if (activeRun(b)) return error(409, 'run_in_progress', 'A run of this build is going.');
    const r = b.results[b.results.length - 1];
    if (!r) return error(409, 'not_built', 'This draft has not been built yet.');
    if (isStale(b, r)) return error(409, 'stale', 'The settings changed since the last build: build again first.');
    let req: C.SaveBuildRequest;
    try { req = JSON.parse(body ?? '') as C.SaveBuildRequest; } catch { return validation(['body'], 'JSON decode error', 'json_invalid'); }
    if (typeof req.label !== 'string' || !req.label.trim() || req.label.length > 200) return validation(['body', 'label'], 'String should have 1 - 200 characters', 'string_too_short');
    const n = host.latestVersion(b.projectId) + 1;
    const names = host.projectName(b.projectId);
    host.addVersion({
      projectId: b.projectId, version: n, label: req.label, createdAt: now(), sourceKind: 'cad',
      model: BUILD_FILES.model, stages: BUILD_FILES.stages, presentation: BUILD_FILES.presentation, stampSource: 'model.json',
      maxScript: { file: BUILD_FILES.maxScript, name: b.settings.project.maxFileName },
      thumbnail: BUILD_FILES.topview, pictures: [],
      csv: { plain: BUILD_FILES.csv, typed: BUILD_FILES.csvTyped, typedHeights: { table: 600, seat: 300, cabinet: 1000 } },
      ...(names ? { projectName: names.name, shortName: names.shortName, projectNo: names.projectNo } : {}),
    });
    versionSettings.set(`${b.projectId}/${n}`, clone(b.settings));
    if (req.rememberMapping && b.settings.office) {
      const o = offices.get(b.settings.office) ?? { format: 'office-mapping/1' as const, id: b.settings.office, name: b.settings.office, createdAt: now(), updatedAt: now(), layers: {}, furnitureWords: {} };
      for (const [layer, role] of Object.entries(b.settings.layers)) {
        if (role === 'other' && b.suggestions[layer]?.role !== 'other' && b.suggestions[layer] !== undefined) continue;
        const key = layer.toUpperCase().replace(/^.*\$0\$/, '').replace(/\s+/g, ' ').trim();
        const was = o.layers[key];
        o.layers[key] = { role, names: [...new Set([...(was?.names ?? []), layer])].slice(0, 10), uses: (was?.uses ?? 0) + 1, lastProject: b.projectId, lastUsedAt: now(), was: was && was.role !== role ? was.role : was?.was ?? null };
      }
      o.updatedAt = now();
      offices.set(o.id, o);
    }
    b.status = 'saved';
    b.savedVersion = n;
    b.updatedAt = now();
    return json(201, host.versionDetail(b.projectId, n));
  }

  function rawRoute(b: BuildRec, req: MockRequest, what: string): MockResponse {
    const r = b.results[b.results.length - 1];
    if (!r) return error(404, 'not_built', 'This draft has not been built yet.');
    switch (what) {
      case 'overlay': return file(Buffer.from(JSON.stringify(overlayOf(b, r))), JSON_TYPE);
      case 'diff': return file(Buffer.from(JSON.stringify(diffOf(b, r))), JSON_TYPE);
      case 'model': { const res = file(readBytes(BUILD_FILES.model), JSON_TYPE); res.headers['x-model-stamp'] = sha1Hex(readBytes(BUILD_FILES.model)).slice(0, 12); return res; }
      case 'stages': return file(readBytes(BUILD_FILES.stages), JSON_TYPE);
      case 'topview': return file(readBytes(BUILD_FILES.topview), 'image/png');
      case 'max-script': {
        const name = b.settings.project.maxFileName;
        const dot = name.lastIndexOf('.');
        return file(readBytes(BUILD_FILES.maxScript), 'text/plain; charset=utf-8', `${dot > 0 ? name.slice(0, dot) : name}_draft.ms`);
      }
    }
    void req;
    return error(404, 'not_found', 'No such file.');
  }

  function sourceRaw(b: BuildRec, sha1: string, what: string, req: MockRequest): MockResponse {
    if (!b.sources.includes(sha1)) return error(404, 'not_ready', 'There is no such source in this build.');
    if (!b.read.has(sha1)) return error(404, 'not_ready', 'This drawing has not been read yet.');
    if (what === 'conversion') return file(Buffer.from(JSON.stringify(conversionOf(b, sha1))), JSON_TYPE);
    if (what === 'drawing') return file(Buffer.from(JSON.stringify(drawingOf(b, sha1))), JSON_TYPE);
    if (what === 'plan') {
      const gz = planOf(b, sha1);
      if ((req.headers?.['accept-encoding'] ?? '').includes('gzip')) {
        const res = file(gz, JSON_TYPE);
        res.headers['content-encoding'] = 'gzip';
        res.headers.etag = `"${sha1Hex(gz)}"`;
        return res;
      }
      return file(gunzipSync(gz), JSON_TYPE);
    }
    return error(404, 'not_found', 'No such file.');
  }

  function handle(req: MockRequest, method: string, parts: string[]): MockResponse | null {
    const [, a, id, b, bid, c, sha, d] = parts;     // ['api', a, id, b, bid, c, sha, d]
    if (a === 'offices' && parts.length === 2 && method === 'GET') {
      return json(200, { offices: [...offices.values()].map(o => ({ id: o.id, name: o.name, layers: Object.keys(o.layers).length, updatedAt: o.updatedAt })) });
    }
    if (a === 'projects' && parts.length === 2 && method === 'POST') return createProject(req.body);
    if (a === 'uploads') {
      if (parts.length === 2 && method === 'POST') return createUpload(req.body);
      if (!id || !/^u[0-9a-f]{24}$/.test(id)) return validation(['path', 'uploadId'], "String should match pattern '^u[0-9a-f]{24}$'", 'string_pattern_mismatch');
      const rec = sessions.get(id);
      if (!rec) return error(404, 'upload_not_found', 'There is no such upload (it was finished, cancelled or has expired).');
      if (parts.length === 3 && method === 'GET') return json(200, rec.s);
      if (parts.length === 3 && method === 'DELETE') { sessions.delete(id); return noContent(); }
      if (parts.length === 5 && b === 'parts' && method === 'PUT') return putPart(rec, Number(bid), req.bytes ?? Buffer.from(req.body ?? '', 'utf8'));
      if (parts.length === 4 && b === 'complete' && method === 'POST') return complete(rec);
      return error(405, 'method_not_allowed', `${method} is not allowed here.`);
    }
    if (a !== 'projects' || b !== 'builds' || !id) return null;
    if (!host.hasProject(id)) return error(404, 'project_not_found', `There is no project ${id}.`);
    if (parts.length === 4) {
      if (method === 'GET') {
        const list = [...buildsOf(id).values()].sort((x, y) => (x.createdAt < y.createdAt ? 1 : x.createdAt > y.createdAt ? -1 : x.id < y.id ? 1 : -1));
        return json(200, { builds: list.map(summary) });
      }
      if (method === 'POST') return createBuild(id, req.body);
      return error(405, 'method_not_allowed', `${method} is not allowed here.`);
    }
    if (!bid || !/^[0-9]{8}T[0-9]{6}-[0-9a-f]{6}$/.test(bid)) return validation(['path', 'buildId'], "String should match pattern '^[0-9]{8}T[0-9]{6}-[0-9a-f]{6}$'", 'string_pattern_mismatch');
    const build = buildsOf(id).get(bid);
    if (!build) return error(404, 'build_not_found', `Project ${id} has no build ${bid}.`);
    if (parts.length === 5) {
      if (method === 'GET') {
        advance(build);
        adoptIfReady(build);
        const withSettings = new URLSearchParams(req.query ?? '').get('withSettings') !== 'false';
        return json(200, detail(build, withSettings));
      }
      if (method === 'DELETE') {
        if (build.status === 'saved') return error(409, 'build_saved', `This build was saved as v${build.savedVersion}.`, { version: build.savedVersion });
        if (activeRun(build)) return error(409, 'run_in_progress', 'A run of this build is going.');
        buildsOf(id).delete(bid);
        return noContent();
      }
      return error(405, 'method_not_allowed', `${method} is not allowed here.`);
    }
    if (parts.length === 6) {
      if (c === 'settings' && method === 'PUT') return putSettings(build, req);
      if (c === 'run' && method === 'POST') return runBuild(build);
      if (c === 'cancel' && method === 'POST') return cancelRun(build);
      if (c === 'save' && method === 'POST') return save(build, req.body);
      if (method === 'GET' && c && ['overlay', 'diff', 'model', 'stages', 'topview', 'max-script'].includes(c)) return rawRoute(build, req, c);
    }
    if (parts.length === 8 && c === 'sources' && sha && d && method === 'GET') return sourceRaw(build, sha, d, req);
    return error(404, 'not_found', `No route ${req.path}.`);
  }

  function finishRuns(pid?: string, bid?: string) {
    for (const [p, m] of builds) {
      if (pid && p !== pid) continue;
      for (const b of m.values()) {
        if (bid && b.id !== bid) continue;
        for (let guard = 0; guard < 1000 && activeRun(b); guard++) {
          const run = activeRun(b)!;
          if (run.info.status === 'queued') { run.info.status = 'running'; run.cursor = 0; run.info.startedAt = now(); }
          for (const s of run.info.steps) { s.status = 'done'; s.seconds = 0.5; }
          run.cursor = run.info.steps.length;
          finish(b, run, 'done', null);
        }
      }
    }
  }

  return {
    config,
    handle,
    builds: pid => [...buildsOf(pid).values()],
    build: (pid, bid) => buildsOf(pid).get(bid) ?? null,
    finishRuns,
    offices: () => [...offices.values()].map(o => ({ id: o.id, name: o.name, layers: Object.keys(o.layers).length, updatedAt: o.updatedAt })),
    office: id => (offices.has(id) ? clone(offices.get(id)!) : null),
    sources: pid => [...sourcesOf(pid).values()].map(sourceFile),
    sessions: () => [...sessions.values()].map(r => clone(r.s)),
    versionSettings: (pid, n) => (versionSettings.has(`${pid}/${n}`) ? clone(versionSettings.get(`${pid}/${n}`)!) : null),
    addSource(pid, src) {
      const kind = src.kind ?? (/\.dxf$/i.test(src.name) ? 'dxf' : 'dwg');
      const sha1 = sha1Hex(src.bytes);
      const rec: SourceRec = { sha1, name: src.name, bytes: src.bytes.length, kind, formatVersion: kind === 'dwg' ? 'AC1032' : null, uploadedAt: now(), data: src.bytes };
      if (!sourcesOf(pid).has(sha1)) sourcesOf(pid).set(sha1, rec);
      return sourceFile(sourcesOf(pid).get(sha1)!);
    },
    createBuildNow(pid, list, opts = {}) {
      const b = newBuild(pid, list, { kind: 'none' }, null);
      if (opts.finish || opts.reviewed || opts.built) finishRuns(pid, b.id);
      if (opts.reviewed || opts.built) b.layersReviewedAt = now();
      if (opts.built) { startRun(b, 'build', null); finishRuns(pid, b.id); }
      return b;
    },
  };
}
