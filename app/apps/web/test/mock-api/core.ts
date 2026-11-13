// A mock of the API (DESIGN.md 10.2) over the typed fixtures, for the web app's tests: the same routes, JSON shapes
// (the generated types), error bodies and download headers as the real API, with the saved heights kept in memory
// (PUT semantics of 10.2: kinds of the model only, whole mm 10 - 5000, values equal to the model's dropped, revision + 1).
// The furniture CSV is a fixture: the prototype's CSV with no saved heights, the typed golden when the saved heights are
// exactly the golden's (fixtures/csv), else a 500 (`mock_no_golden`, so a test never reads a made-up CSV). The offline
// HTML is a stand-in page that carries the offline payload (DESIGN.md 16: format, project, version, model, stages,
// pictures, overrides; `<` escaped) but no viewer.
// Adapters: server.ts (HTTP, behind the Vite proxy: the Playwright specs) and fetch.ts (vitest's fetch).
// The upload milestone (docs/upload/DESIGN.md U-13.1, WORK_BREAKDOWN U6) adds createProject, listOffices, the uploads and
// the builds (builds.ts): projects made in memory (no version until a build is saved) and versions saved from builds.
// The deletes of 12 Nov 2026 (docs/contract-issues/DEL.md): deleteProject and deleteVersion as the API answers them (204;
// 404; 409 only_version; 409 busy while a draft of the project has a run queued or running); a deleted version's number
// is never given again.
import type {
  AssetInfo,
  HeightOverrides,
  ProjectDetail,
  ProjectList,
  ProjectSummary,
  VersionCounts,
  VersionDetail,
  VersionSummary,
} from '../../src/api/generated/types.gen';
import type { BuiltModel, HeightMap } from '../../../../packages/viewer/src/contracts';
import { createUploadMock, type UploadMock } from './builds';
import { MOCK_VERSIONS, readBytes, readJson, sha1, type MockVersionSource } from './fixtures';
import { error, file, json, JSON_TYPE, noContent, type MockRequest, type MockResponse } from './http';

export type { MockRequest, MockResponse } from './http';

interface SavedHeights { heights: HeightMap; revision: number; updatedAt: string | null }

export interface MockApi {
  handle(req: MockRequest): MockResponse;
  /** Every request handled, in order. */
  readonly requests: MockRequest[];
  /** The saved heights of a version (a copy). */
  saved(projectId: string, version: number): HeightOverrides;
  /** Sets the saved heights directly (as if saved earlier). */
  setSaved(projectId: string, version: number, heights: HeightMap): void;
  /** Projects as the list returns them (newest first). */
  list(): ProjectSummary[];
  project(projectId: string): ProjectDetail | null;
  version(projectId: string, version: number): VersionDetail | null;
  /** The source of a version (its fixture files). */
  source(projectId: string, version: number): MockVersionSource | null;
  /** The upload milestone's routes and their state (uploads, sources, builds, offices). */
  readonly uploads: UploadMock;
}

interface CreatedProject { id: string; name: string; shortName: string; projectNo: string | null; createdAt: string }

/** The Max script's attachment name, as the API gives it: the stored name with the version (Bangkok_Bank_Sampeng_v2.ms). */
const maxScriptName = (stored: string, version: number) => {
  const dot = stored.lastIndexOf('.');                    // Python's Path stem + suffix (views.max_script_file_name)
  return dot > 0 ? `${stored.slice(0, dot)}_v${version}${stored.slice(dot)}` : `${stored}_v${version}`;
};
const enc = (s: string) => Buffer.from(s, 'utf8');

const countsOf = (m: BuiltModel): VersionCounts => ({
  floors: m.floors.length,
  parts: m.parts.length,
  openings: m.openings.length,
  furniture: (m.furniture ?? []).length,
  furnitureKinds: (m.furnitureKinds ?? []).length,
  rooms: m.rooms.length,
});

export function createMockApi(): MockApi {
  const requests: MockRequest[] = [];
  const saved = new Map<string, SavedHeights>();
  const updated = new Map<string, string>();   // projectId -> a later save's time
  const keyOf = (id: string, n: number) => `${id}/${n}`;
  const modelOf = (s: MockVersionSource) => readJson(s.model) as BuiltModel;
  const stampOf = (s: MockVersionSource) => s.stamp ?? sha1(readBytes(s.model)).slice(0, 12);
  const added: MockVersionSource[] = [];
  const created = new Map<string, CreatedProject>();
  const deletedProjects = new Set<string>();                     // seeded (fixture) projects deleted
  const deletedVersions = new Set<string>();                     // `${projectId}/${n}`
  const everyVersion = () => [...MOCK_VERSIONS.filter(v => !deletedProjects.has(v.projectId)), ...added];
  const allVersions = () => everyVersion().filter(v => !deletedVersions.has(keyOf(v.projectId, v.version)));
  const source = (id: string, n: number) => allVersions().find(v => v.projectId === id && v.version === n) ?? null;
  const versionsOf = (id: string) => allVersions().filter(v => v.projectId === id).sort((a, b) => a.version - b.version);
  const savedOf = (id: string, n: number): SavedHeights => saved.get(keyOf(id, n)) ?? { heights: {}, revision: 0, updatedAt: null };
  const overridesOf = (id: string, n: number): HeightOverrides => {
    const s = savedOf(id, n);
    return { heights: { ...s.heights }, revision: s.revision, updatedAt: s.updatedAt };
  };

  function versionSummary(s: MockVersionSource): VersionSummary {
    const m = modelOf(s);
    return {
      version: s.version,
      label: s.label,
      createdAt: s.createdAt,
      stamp: stampOf(s),
      sourceKind: s.sourceKind,
      counts: countsOf(m),
      hasStages: s.stages !== null,
      hasMaxScript: s.maxScript !== null,
      hasFurniture: (m.furniture ?? []).length > 0,
      url: `/api/projects/${s.projectId}/versions/${s.version}`,
    };
  }

  function versionDetail(s: MockVersionSource): VersionDetail {
    const m = modelOf(s);
    const sum = versionSummary(s);
    const base = sum.url;
    const assets: AssetInfo[] = s.pictures.map(p => {
      const b = readBytes(p.file);
      return { name: p.name, role: 'plan-picture', floor: p.floor, mediaType: 'image/png', bytes: b.length, sha1: sha1(b), url: `${base}/assets/${p.name}` };
    });
    if (s.thumbnail) {
      const b = readBytes(s.thumbnail);
      assets.push({ name: 'topview.png', role: 'thumbnail', floor: null, mediaType: 'image/png', bytes: b.length, sha1: sha1(b), url: `${base}/assets/topview.png` });
    }
    return {
      ...sum,
      projectId: s.projectId,
      modelSha1: sha1(readBytes(s.model)),
      stampSource: s.stampSource,
      floors: m.floors.map(f => ({ key: f.key, name: f.name, level: f.level })),
      urls: { model: `${base}/model`, stages: s.stages ? `${base}/stages` : null },
      assets,
      downloads: {
        maxScript: s.maxScript ? { url: `${base}/downloads/max-script`, fileName: maxScriptName(s.maxScript.name, s.version), mediaType: 'text/plain; charset=utf-8' } : null,
        furnitureCsv: sum.hasFurniture
          ? { url: `${base}/downloads/furniture-csv`, fileName: `${m.photoName}_furniture_list.csv`, mediaType: 'text/csv; charset=utf-8' }
          : null,
        offlineHtml: { url: `${base}/downloads/offline-html`, fileName: `${s.projectId}-v${s.version}.html`, mediaType: 'text/html; charset=utf-8' },
      },
      presentation: readJson(s.presentation) as Record<string, unknown>,
      overrides: overridesOf(s.projectId, s.version),
    };
  }

  function projectSummary(id: string): ProjectSummary | null {
    const vs = versionsOf(id);
    const first = vs[0];
    const latest = vs[vs.length - 1];
    const made = created.get(id);
    if (!first || !latest) {
      if (!made) return null;
      // a project made by createProject, before its first version (U-14.1)
      return {
        id, name: made.name, shortName: made.shortName, projectNo: made.projectNo, sourceKind: 'cad', floors: [],
        furnitureCount: 0, openingsCount: 0, stamp: '', latestVersion: 0, versionCount: 0,
        createdAt: made.createdAt, updatedAt: updated.get(id) ?? made.createdAt, thumbnailUrl: null, url: `/api/projects/${id}`,
      };
    }
    const m = modelOf(latest);
    const later = updated.get(id);
    return {
      id,
      name: made?.name ?? latest.projectName ?? m.project,
      shortName: made?.shortName ?? latest.shortName ?? m.shortName,
      projectNo: made ? made.projectNo : latest.projectNo !== undefined ? latest.projectNo : m.projectNo ?? null,
      sourceKind: latest.sourceKind,
      floors: m.floors.map(f => ({ key: f.key, name: f.name, level: f.level })),
      furnitureCount: (m.furniture ?? []).length,
      openingsCount: m.openings.length,
      stamp: stampOf(latest),
      latestVersion: latest.version,
      versionCount: vs.length,
      createdAt: made?.createdAt ?? first.createdAt,
      updatedAt: later && later > latest.createdAt ? later : latest.createdAt,
      thumbnailUrl: latest.thumbnail ? `/api/projects/${id}/thumbnail` : null,
      url: `/api/projects/${id}`,
    };
  }

  const projectIds = () => [...new Set([...allVersions().map(v => v.projectId), ...created.keys()])];
  const list = () => projectIds().map(projectSummary).filter((p): p is ProjectSummary => !!p)
    .sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : a.updatedAt > b.updatedAt ? -1 : 0));
  const project = (id: string): ProjectDetail | null => {
    const p = projectSummary(id);
    return p ? { ...p, versions: versionsOf(id).map(versionSummary) } : null;
  };

  function putHeights(s: MockVersionSource, body: string | null | undefined): MockResponse {
    const m = modelOf(s);
    if (!(m.furniture ?? []).length) return error(404, 'no_furniture', 'This version has no furniture.');
    let parsed: unknown;
    try { parsed = JSON.parse(body ?? ''); } catch { return json(422, { detail: [{ loc: ['body'], msg: 'JSON decode error', type: 'json_invalid' }] }); }
    const heights = (parsed as { heights?: unknown } | null)?.heights;
    if (!heights || typeof heights !== 'object' || Array.isArray(heights)) {
      return json(422, { detail: [{ loc: ['body', 'heights'], msg: 'Field required', type: 'missing' }] });
    }
    const kinds = new Map((m.furnitureKinds ?? []).map(k => [k.key, Math.floor(k.height + 0.5)]));
    const unknownKinds: string[] = [];
    const outOfRange: string[] = [];
    const out: HeightMap = {};
    for (const [k, v] of Object.entries(heights as Record<string, unknown>)) {
      if (!kinds.has(k)) { unknownKinds.push(k); continue; }
      if (typeof v !== 'number' || !Number.isInteger(v) || v < 10 || v > 5000) { outOfRange.push(k); continue; }
      if (v !== kinds.get(k)) out[k] = v;
    }
    if (unknownKinds.length || outOfRange.length) {
      return error(422, 'invalid_heights', 'Every key must be a furniture kind of the model and every value a whole number of mm, 10 - 5000.',
        { unknownKinds, outOfRange });
    }
    const prev = savedOf(s.projectId, s.version);
    const now = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
    saved.set(keyOf(s.projectId, s.version), { heights: out, revision: prev.revision + 1, updatedAt: now });
    updated.set(s.projectId, now);
    return json(200, overridesOf(s.projectId, s.version));
  }

  function csv(s: MockVersionSource): MockResponse {
    const m = modelOf(s);
    if (!s.csv || !(m.furniture ?? []).length) return error(404, 'no_furniture', 'This version has no furniture.');
    const h = savedOf(s.projectId, s.version).heights;
    const name = `${m.photoName}_furniture_list.csv`;
    const same = (a: HeightMap, b: HeightMap) => Object.keys(a).length === Object.keys(b).length && Object.entries(a).every(([k, v]) => b[k] === v);
    if (!Object.keys(h).length) return file(readBytes(s.csv.plain), 'text/csv; charset=utf-8', name);
    if (same(h, s.csv.typedHeights)) return file(readBytes(s.csv.typed), 'text/csv; charset=utf-8', name);
    return error(500, 'mock_no_golden', `The mock API has no CSV golden for the heights ${JSON.stringify(h)}.`);
  }

  function offlineHtml(s: MockVersionSource): MockResponse {
    const m = modelOf(s);
    const detail = versionDetail(s);
    const p = projectSummary(s.projectId)!;
    const meta = {
      format: 'walkthrough-project/1', id: p.id, name: p.name, shortName: p.shortName, projectNo: p.projectNo, sourceKind: p.sourceKind,
      createdAt: p.createdAt, updatedAt: p.updatedAt, latestVersion: p.latestVersion, versions: versionsOf(s.projectId).map(v => v.version),
    };
    const version = {
      format: 'walkthrough-version/1', projectId: s.projectId, version: s.version, label: s.label, createdAt: s.createdAt,
      sourceKind: s.sourceKind, sourceFiles: m.source, modelFormat: 'built-model/1', modelSha1: detail.modelSha1, stamp: detail.stamp,
      stampSource: s.stampSource, counts: detail.counts, floors: detail.floors, hasStages: detail.hasStages, assets: [],
      downloads: { maxScript: s.maxScript?.name ?? null, furnitureCsv: detail.hasFurniture }, presentation: detail.presentation,
    };
    const sv = savedOf(s.projectId, s.version);
    const overrides = sv.revision ? { format: 'walkthrough-overrides/1', heights: sv.heights, revision: sv.revision, updatedAt: sv.updatedAt } : null;
    const pictures = Object.fromEntries(s.pictures.map(pic => [pic.floor, `data:image/png;base64,${readBytes(pic.file).toString('base64')}`]));
    const payload = `{"format":"walkthrough-offline/1","project":${JSON.stringify(meta)},"version":${JSON.stringify(version)},"model":${readBytes(s.model).toString('utf8')},`
      + `"stages":${s.stages ? readBytes(s.stages).toString('utf8') : 'null'},"pictures":${JSON.stringify(pictures)},"overrides":${JSON.stringify(overrides)}}`;
    const title = String((detail.presentation as { documentTitle?: unknown }).documentTitle ?? 'Walkthrough')
      .replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!));
    const html = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
      + `<meta name="model-data" content="${detail.stamp}"><title>${title}</title></head>`
      + '<body><p>Stand-in offline file from the web tests\' mock API (no viewer in it).</p>'
      + `<script type="application/json" id="wtv-data">${payload.replaceAll('<', '\\u003c')}</script></body></html>`;
    return file(enc(html), 'text/html; charset=utf-8', `${s.projectId}-v${s.version}.html`);
  }

  const uploads: UploadMock = createUploadMock({
    hasProject: id => !!project(id),
    createProject: p => {
      const t = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
      created.set(p.id, { id: p.id, name: p.name, shortName: p.shortName, projectNo: p.projectNo, createdAt: t });
    },
    latestVersion: id => versionsOf(id).at(-1)?.version ?? 0,
    nextVersion: id => Math.max(0, ...everyVersion().filter(v => v.projectId === id).map(v => v.version)) + 1,
    addVersion: v => {
      added.push(v);
      updated.set(v.projectId, v.createdAt);
    },
    versionDetail: (id, n) => { const s = source(id, n); return s ? versionDetail(s) : null; },
    projectDetail: id => project(id),
    projectName: id => {
      const p = projectSummary(id);
      return p ? { name: p.name, shortName: p.shortName, projectNo: p.projectNo } : null;
    },
  });

  const BUSY = (what: string) => `Wait for the build to finish (or cancel it), then delete the ${what}.`;

  function deleteProject(id: string): MockResponse {
    const busy = uploads.busy(id);
    if (busy.length) return error(409, 'busy', BUSY('project'), { builds: busy });
    if (MOCK_VERSIONS.some(v => v.projectId === id)) deletedProjects.add(id);
    for (let i = added.length - 1; i >= 0; i--) if (added[i]!.projectId === id) added.splice(i, 1);
    for (const k of [...deletedVersions, ...saved.keys()]) if (k.startsWith(`${id}/`)) { deletedVersions.delete(k); saved.delete(k); }
    created.delete(id);
    updated.delete(id);
    uploads.dropProject(id);
    return noContent();
  }

  function deleteVersion(id: string, n: number): MockResponse {
    if (versionsOf(id).length <= 1) return error(409, 'only_version', "This is the project's only version: delete the project instead.");
    const busy = uploads.busy(id);
    if (busy.length) return error(409, 'busy', BUSY('version'), { builds: busy });
    deletedVersions.add(keyOf(id, n));
    saved.delete(keyOf(id, n));
    updated.set(id, new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'));
    uploads.dropSavedDraft(id, n);
    return noContent();
  }

  function handle(req: MockRequest): MockResponse {
    requests.push(req);
    const method = req.method.toUpperCase();
    const parts = req.path.replace(/\/+$/, '').split('/').slice(1).map(decodeURIComponent);   // ['api', ...]
    if (parts[0] !== 'api') return error(404, 'not_found', `No route ${req.path}.`);
    const upload = uploads.handle(req, method, parts);
    if (upload) return upload;
    const [, a, id, b, n, c, d] = parts;
    const heightsRoute = parts.length === 6 && b === 'versions' && c === 'furniture-heights';
    const deleteRoute = a === 'projects' && (parts.length === 3 || (parts.length === 5 && b === 'versions'));
    if (method !== 'GET' && !(method === 'PUT' && heightsRoute) && !(method === 'DELETE' && deleteRoute)) {
      return error(405, 'method_not_allowed', `${method} is not allowed here.`);
    }
    if (a === 'health' && parts.length === 2) return json(200, { status: 'ok', apiVersion: 'mock', projects: projectIds().length });
    if (a !== 'projects') return error(404, 'not_found', `No route ${req.path}.`);
    if (parts.length === 2) { const body: ProjectList = { projects: list() }; return json(200, body); }
    if (!id || !/^[a-z0-9][a-z0-9-]{1,62}$/.test(id)) {
      return json(422, { detail: [{ loc: ['path', 'projectId'], msg: "String should match pattern '^[a-z0-9][a-z0-9-]{1,62}$'", type: 'string_pattern_mismatch' }] });
    }
    const proj = project(id);
    if (!proj) return error(404, 'project_not_found', `There is no project ${id}.`);
    if (parts.length === 3 && method === 'DELETE') return deleteProject(id);
    if (parts.length === 3) return json(200, proj);
    if (b === 'thumbnail' && parts.length === 4) {
      const latest = source(id, proj.latestVersion);
      return latest?.thumbnail ? file(readBytes(latest.thumbnail), 'image/png') : error(404, 'no_thumbnail', `Project ${id} has no thumbnail.`);
    }
    if (b !== 'versions' || !n) return error(404, 'not_found', `No route ${req.path}.`);
    const ver = Number(n);
    if (!/^\d+$/.test(n) || ver < 1) return json(422, { detail: [{ loc: ['path', 'version'], msg: 'Input should be greater than or equal to 1', type: 'greater_than_equal' }] });
    const s = source(id, ver);
    if (!s) {
      return error(404, 'version_not_found', deletedVersions.has(keyOf(id, ver)) ? `version ${ver} of '${id}' was deleted` : `Project ${id} has no version ${ver}.`);
    }
    if (parts.length === 5 && method === 'DELETE') return deleteVersion(id, ver);
    if (parts.length === 5) return json(200, versionDetail(s));
    if (c === 'model' && parts.length === 6) {
      const res = file(readBytes(s.model), JSON_TYPE);
      res.headers['x-model-stamp'] = stampOf(s);
      return res;
    }
    if (c === 'stages' && parts.length === 6) return s.stages ? file(readBytes(s.stages), JSON_TYPE) : error(404, 'no_stages', `Version ${ver} has no build replay.`);
    if (c === 'assets' && d && parts.length === 7) {
      const pic = s.pictures.find(p => p.name === d);
      if (pic) return file(readBytes(pic.file), 'image/png');
      if (d === 'topview.png' && s.thumbnail) return file(readBytes(s.thumbnail), 'image/png');
      return error(404, 'asset_not_found', `Version ${ver} has no asset ${d}.`);
    }
    if (c === 'downloads' && parts.length === 7) {
      if (d === 'max-script') return s.maxScript ? file(readBytes(s.maxScript.file), 'text/plain; charset=utf-8', maxScriptName(s.maxScript.name, s.version)) : error(404, 'no_max_script', `Version ${ver} has no 3ds Max script.`);
      if (d === 'furniture-csv') return csv(s);
      if (d === 'offline-html') return offlineHtml(s);
    }
    if (c === 'furniture-heights' && parts.length === 6) {
      if (!(modelOf(s).furniture ?? []).length) return error(404, 'no_furniture', 'This version has no furniture.');
      return method === 'PUT' ? putHeights(s, req.body) : json(200, overridesOf(id, ver));
    }
    return error(404, 'not_found', `No route ${req.path}.`);
  }

  return {
    handle,
    requests,
    saved: (id, n) => overridesOf(id, n),
    setSaved: (id, n, heights) => {
      const prev = savedOf(id, n);
      saved.set(keyOf(id, n), { heights: { ...heights }, revision: prev.revision + 1, updatedAt: new Date().toISOString() });
    },
    list,
    project,
    version: (id, n) => { const s = source(id, n); return s ? versionDetail(s) : null; },
    source,
    uploads,
  };
}
