#!/usr/bin/env node
// Template + store -> <out>/<projectId>-v<n>.html for every version of the store (DESIGN.md 16). Owner: builder A.
//   node packages/viewer/scripts/make-offline.mjs --data data --template dist/offline-template/viewer-template.html --out dist/offline
//        [--project <projectId>] [--version <n>]
// Paths are relative to the working folder (npm runs it from app/). Exit code 1 on any problem, with a message.
//
// The payload is plain concatenation of the store's files as they are (UTF-8 text, trailing newline included), so that
// this script and the API's walkthrough_api/offline.py give the same bytes:
//   {"format":"walkthrough-offline/1","project":<meta.json>,"version":<version.json>,"model":<model.json>,
//    "stages":<stages.json or null>,"pictures":{"<floor>":"data:<mediaType>;base64,<base64>",...},"overrides":<overrides.json or null>}
// (no line breaks between the parts; the plan pictures in model floor order), then every "<" in it replaced by the six
// characters < (still valid JSON: "<" occurs only inside strings; no "</script" and no "<!--" can remain).
// Assembly substitutes in the TEMPLATE only, never searches or rewrites the payload: each marker must occur exactly once
// in the template, the stamp goes in first, then the template is split on the data marker into exactly two pieces and
// piece0 + payload + piece1 is written. Never String.prototype.replace with the payload: a replacement string expands
// $' $& $` $$, and $' would insert the template's own tail (with its </script>) inside the data.
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readdirSync, readFileSync, renameSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const STAMP_MARKER = '__WTV_STAMP__';
export const DATA_MARKER = '__WTV_DATA__';
const FLOOR_KEY = /^[A-Za-z0-9_]{1,32}$/;
const MEDIA_TYPE = /^[A-Za-z0-9.+-]+\/[A-Za-z0-9.+-]+$/;
const ASSET_NAME = /^[A-Za-z0-9._-]+$/;
const PROJECT_ID = /^[a-z0-9][a-z0-9-]{1,62}$/;

export class OfflineError extends Error {
  constructor(message) { super(message); this.name = 'OfflineError'; }
}

/** How often `marker` occurs in `text` (non-overlapping). */
export function occurrences(text, marker) {
  return text.split(marker).length - 1;
}

/** The template with the stamp and the payload in it (DESIGN.md 16 "Assembly"). */
export function assemble(template, stamp, payload) {
  for (const marker of [STAMP_MARKER, DATA_MARKER]) {
    const n = occurrences(template, marker);
    if (n !== 1) throw new OfflineError(`the template must contain ${marker} exactly once (found ${n})`);
  }
  if (!/^[0-9a-f]{12}$/.test(stamp)) throw new OfflineError(`the stamp must be 12 hex characters (got ${JSON.stringify(stamp)})`);
  const stamped = template.split(STAMP_MARKER).join(stamp);
  const pieces = stamped.split(DATA_MARKER);
  if (pieces.length !== 2) throw new OfflineError(`the stamped template must split into two pieces on ${DATA_MARKER} (got ${pieces.length})`);
  return pieces[0] + payload + pieces[1];
}

/** The payload text from the files' texts (strings as stored) and the pictures ([floor, mediaType, base64] in floor order). */
export function payloadText({ meta, version, model, stages = null, pictures = [], overrides = null }) {
  const pics = pictures.map(([floor, mediaType, base64]) => {
    if (!FLOOR_KEY.test(floor)) throw new OfflineError(`plan picture floor key ${JSON.stringify(floor)} is not a floor key`);
    if (!MEDIA_TYPE.test(mediaType)) throw new OfflineError(`plan picture media type ${JSON.stringify(mediaType)} is not a media type`);
    return `"${floor}":"data:${mediaType};base64,${base64}"`;
  }).join(',');
  const text = `{"format":"walkthrough-offline/1","project":${meta},"version":${version},"model":${model},`
    + `"stages":${stages ?? 'null'},"pictures":{${pics}},"overrides":${overrides ?? 'null'}}`;
  return text.split('<').join('\\u003c');
}

/**
 * The first key an object of `text` (valid JSON) repeats, decoded, or null. JSON.parse keeps the last of a repeated key;
 * the API's strict reader (walkthrough_api/jsonio.loads_strict) refuses the file, and so does this script.
 */
export function repeatedKey(text) {
  const stack = [];                 // per open container: a Set of its keys (object) or null (array)
  let expectKey = false;
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i);
    if (c === 34) {                 // a string: find its end, skipping escapes
      let j = i + 1;
      while (j < text.length && text.charCodeAt(j) !== 34) j += text.charCodeAt(j) === 92 ? 2 : 1;
      const keys = stack[stack.length - 1];
      if (keys && expectKey) {
        const key = JSON.parse(text.slice(i, j + 1));
        if (keys.has(key)) return key;
        keys.add(key);
        expectKey = false;
      }
      i = j;
    } else if (c === 123) { stack.push(new Set()); expectKey = true; }       // {
    else if (c === 91) stack.push(null);                                      // [
    else if (c === 125 || c === 93) stack.pop();                              // } ]
    else if (c === 44) expectKey = stack[stack.length - 1] instanceof Set;    // ,
  }
  return null;
}

const UTF8 = new TextDecoder('utf-8', { fatal: true });

/**
 * A store JSON file: its text as stored and the parsed value. Strict as the API's reader (DESIGN.md 9.1): UTF-8 without a
 * byte-order mark, valid UTF-8, JSON (no NaN / Infinity), no repeated key; so Node and Python refuse the same files
 * (fix step, first code review finding 16). `bytes` for checks over the stored bytes (the model's sha1).
 */
function readText(file, what) {
  if (!existsSync(file)) throw new OfflineError(`${what}: ${file} is missing`);
  const bytes = readFileSync(file);
  if (bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) {
    throw new OfflineError(`${what}: ${file} starts with a byte-order mark (the store's JSON is UTF-8 without one, DESIGN.md 9.1)`);
  }
  let text;
  try { text = UTF8.decode(bytes); } catch { throw new OfflineError(`${what}: ${file} is not UTF-8`); }
  let parsed;
  try { parsed = JSON.parse(text); } catch (err) { throw new OfflineError(`${what}: ${file} is not JSON (${err.message})`); }
  const repeated = repeatedKey(text);
  if (repeated !== null) throw new OfflineError(`${what}: ${file} repeats the key ${JSON.stringify(repeated)} (not strict JSON, DESIGN.md 9.1)`);
  return { text, parsed, bytes };
}

/** One version's offline HTML: { fileName, html, stamp }. */
export function buildVersion({ data, projectId, version, template }) {
  const projectDir = path.join(data, 'projects', projectId);
  const dir = path.join(projectDir, 'versions', String(version));
  const what = `${projectId} v${version}`;
  const meta = readText(path.join(projectDir, 'meta.json'), `${projectId} meta`);
  const ver = readText(path.join(dir, 'version.json'), `${what} version`);
  const model = readText(path.join(dir, 'model.json'), `${what} model`);
  const stagesFile = path.join(dir, 'stages.json');
  const stages = existsSync(stagesFile) ? readText(stagesFile, `${what} stages`).text : null;
  const overridesFile = path.join(dir, 'overrides.json');
  const overrides = existsSync(overridesFile) ? readText(overridesFile, `${what} overrides`).text : null;
  const stamp = ver.parsed.stamp;
  if (typeof stamp !== 'string') throw new OfflineError(`${what}: version.json has no stamp`);
  // the version's model, as the API checks it (views.model_bytes, offline.py): never a model.json changed on disk
  if (createHash('sha1').update(model.bytes).digest('hex') !== ver.parsed.modelSha1) {
    throw new OfflineError(`${what}: model.json does not match the modelSha1 of its version.json (changed on disk?)`);
  }
  const assets = Array.isArray(ver.parsed.assets) ? ver.parsed.assets : [];
  const floors = Array.isArray(model.parsed.floors) ? model.parsed.floors.map(f => f.key) : [];
  const pictures = [];
  for (const key of floors) {
    const asset = assets.find(a => a && a.role === 'plan-picture' && a.floor === key);
    if (!asset) continue;
    if (typeof asset.name !== 'string' || !ASSET_NAME.test(asset.name)) throw new OfflineError(`${what}: plan picture name ${JSON.stringify(asset.name)} is not a file name`);
    const file = path.join(dir, 'assets', asset.name);
    if (!existsSync(file)) throw new OfflineError(`${what}: plan picture ${file} is missing`);
    pictures.push([key, String(asset.mediaType), readFileSync(file).toString('base64')]);
  }
  const payload = payloadText({ meta: meta.text, version: ver.text, model: model.text, stages, pictures, overrides });
  return { fileName: `${projectId}-v${version}.html`, html: assemble(template, stamp, payload), stamp };
}

/** The versions of the store: [{ projectId, version }] in project and version order. */
export function storeVersions(data) {
  const projects = path.join(data, 'projects');
  if (!existsSync(projects)) throw new OfflineError(`no store at ${projects} (run \`npm run seed\` first)`);
  const out = [];
  for (const projectId of readdirSync(projects).sort()) {
    if (!PROJECT_ID.test(projectId) || !statSync(path.join(projects, projectId)).isDirectory()) continue;
    const metaFile = path.join(projects, projectId, 'meta.json');
    if (!existsSync(metaFile)) continue;
    const meta = readText(metaFile, `${projectId} meta`).parsed;
    let versions = Array.isArray(meta.versions) ? meta.versions.filter(n => Number.isInteger(n) && n >= 1) : null;
    if (!versions) {
      const vdir = path.join(projects, projectId, 'versions');
      versions = existsSync(vdir) ? readdirSync(vdir).filter(n => /^[1-9][0-9]*$/.test(n)).map(Number) : [];
    }
    for (const version of [...versions].sort((a, b) => a - b)) out.push({ projectId, version });
  }
  return out;
}

/** Every (or the chosen) version into `out`; returns [{ file, bytes, stamp }]. */
export function makeOffline({ data, template: templateFile, out, project = null, version = null }) {
  if (!existsSync(templateFile)) throw new OfflineError(`no offline template at ${templateFile} (run \`npm run build:offline:template\` first)`);
  const template = readFileSync(templateFile, 'utf8');
  for (const marker of [STAMP_MARKER, DATA_MARKER]) {
    const n = occurrences(template, marker);
    if (n !== 1) throw new OfflineError(`the template ${templateFile} must contain ${marker} exactly once (found ${n})`);
  }
  const todo = storeVersions(data).filter(v => (project === null || v.projectId === project) && (version === null || v.version === version));
  mkdirSync(out, { recursive: true });
  const written = [];
  for (const v of todo) {
    const { fileName, html, stamp } = buildVersion({ data, projectId: v.projectId, version: v.version, template });
    const file = path.join(out, fileName), tmp = `${file}.${process.pid}.tmp`;
    writeFileSync(tmp, html, 'utf8');
    renameSync(tmp, file);
    written.push({ file, bytes: Buffer.byteLength(html, 'utf8'), stamp });
  }
  return written;
}

function parseCli(argv) {
  const opts = { data: 'data', template: 'dist/offline-template/viewer-template.html', out: 'dist/offline', project: null, version: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i], eq = a.indexOf('=');
    const name = a.startsWith('--') ? (eq > 0 ? a.slice(2, eq) : a.slice(2)) : null;
    const value = () => (eq > 0 ? a.slice(eq + 1) : argv[++i]);
    if (name === 'data' || name === 'template' || name === 'out' || name === 'project') opts[name] = value();
    else if (name === 'version') opts.version = Number(value());
    else throw new OfflineError(`unknown argument ${a} (--data, --template, --out, --project, --version)`);
  }
  if (opts.version !== null && !(Number.isInteger(opts.version) && opts.version >= 1)) throw new OfflineError('--version takes a whole number from 1');
  return opts;
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
if (isMain) {
  try {
    const opts = parseCli(process.argv.slice(2));
    const written = makeOffline(opts);
    for (const w of written) console.log(`make-offline: ${path.relative(process.cwd(), w.file)}  ${Math.round(w.bytes / 1024)} KB  (model data ${w.stamp})`);
    if (!written.length) console.log(`make-offline: the store at ${opts.data} has no versions${opts.project ? ` of ${opts.project}` : ''}: no offline files written`);
  } catch (err) {
    console.error(`make-offline: ${err instanceof OfflineError ? err.message : err && err.stack || err}`);
    process.exit(1);
  }
}
