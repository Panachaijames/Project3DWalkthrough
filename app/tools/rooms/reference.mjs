// The "nothing else moved" references of the rooms milestone (DESIGN R-13, ACCEPTANCE RA-2 and RA-16). Scaffold R0.
//
//   node tools/rooms/reference.mjs versions --write | --check [--data <dir>]
//       docs/rooms/reference/versions.sha1: the sha1 of every file under <data>/projects/*/versions/ (default app/data).
//       --check: every listed file still has its sha1 (new files are allowed: the owner uses the app).
//   node tools/rooms/reference.mjs outside --write | --check
//       docs/rooms/reference/outside.txt: every file of the project folder outside app/ (sha1, bytes, path), without
//       .git/, .claude/, detector/blind_run_suite_revit/, detector/keys/suite_revit/ and the documents the main
//       session edits (walkthrough_app_plan.md and every README.md); and the __pycache__ folders that were there.
//       --check: no listed file changed or went away, and there is no new __pycache__ folder. New files are reported
//       (exit 1 too: nothing may be added to the prototype folders).
//   node tools/rooms/reference.mjs store <dir> --write <out.sha1> | --check <ref.sha1>
//       the same listing as "versions" for any store (the upload acceptance store's copy).
//
// Read-only outside app/docs/rooms/reference (and the <out> of "store"). Exit 0 = as recorded, 1 = something moved.
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const APP = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const ROOT = resolve(APP, '..');
const REF = join(APP, 'docs', 'rooms', 'reference');

const sha1 = (file) => createHash('sha1').update(readFileSync(file)).digest('hex');
const slash = (p) => p.split(sep).join('/');

function walk(dir, skip, out = [], caches = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true }).sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0))) {
    const full = join(dir, entry.name);
    const rel = slash(relative(ROOT, full));
    if (entry.isDirectory()) {
      if (entry.name === '__pycache__') { caches.push(rel); continue; }
      if (skip(rel, true)) continue;
      walk(full, skip, out, caches);
    } else if (entry.isFile()) {
      if (skip(rel, false)) continue;
      out.push(full);
    }
  }
  return { files: out, caches };
}

// ---- versions -------------------------------------------------------------------------------------------------------
function versionFiles(data) {
  const projects = join(data, 'projects');
  const out = [];
  if (!existsSync(projects)) return out;
  for (const project of readdirSync(projects).sort()) {
    const versions = join(projects, project, 'versions');
    if (!existsSync(versions) || !statSync(versions).isDirectory()) continue;
    const stack = [versions];
    while (stack.length) {
      const dir = stack.pop();
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const full = join(dir, entry.name);
        if (entry.isDirectory()) stack.push(full);
        else if (entry.isFile()) out.push(full);
      }
    }
  }
  return out.map((file) => [slash(relative(data, file)), file]).sort((a, b) => (a[0] < b[0] ? -1 : 1));
}

function writeVersions(data, outFile, title) {
  const rows = versionFiles(data);
  const lines = [
    `# ${title}`,
    `# ${rows.length} files; "<sha1>  <path under the store>"; written by tools/rooms/reference.mjs, never by hand.`,
    ...rows.map(([rel, file]) => `${sha1(file)}  ${rel}`),
  ];
  mkdirSync(dirname(outFile), { recursive: true });
  writeFileSync(outFile, lines.join('\n') + '\n');
  console.log(`${rows.length} files -> ${outFile}`);
  return 0;
}

function checkVersions(data, refFile) {
  const want = readFileSync(refFile, 'utf8').split('\n').filter((l) => l && !l.startsWith('#')).map((l) => [l.slice(0, 40), l.slice(42)]);
  const moved = [];
  for (const [hash, rel] of want) {
    const file = join(data, ...rel.split('/'));
    if (!existsSync(file)) moved.push(`  gone     ${rel}`);
    else if (sha1(file) !== hash) moved.push(`  changed  ${rel}`);
  }
  const listed = new Set(want.map(([, rel]) => rel));
  const added = versionFiles(data).filter(([rel]) => !listed.has(rel)).length;
  console.log(`${want.length} listed files: ${want.length - moved.length} unchanged, ${moved.length} moved; ${added} new files (allowed)`);
  for (const line of moved) console.log(line);
  return moved.length ? 1 : 0;
}

// ---- outside --------------------------------------------------------------------------------------------------------
const SKIP_DIRS = ['app', '.git', '.claude', 'detector/blind_run_suite_revit', 'detector/keys/suite_revit'];
const skipOutside = (rel, isDir) => {
  if (isDir) return SKIP_DIRS.includes(rel);
  const name = rel.split('/').pop();
  return rel === 'walkthrough_app_plan.md' || name === 'README.md';
};

function outsideRows() {
  const { files, caches } = walk(ROOT, skipOutside);
  const rows = files.map((file) => [slash(relative(ROOT, file)), statSync(file).size, sha1(file)]);
  rows.sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  return { rows, caches: caches.filter((c) => !SKIP_DIRS.some((d) => c === d || c.startsWith(d + '/'))).sort() };
}

function writeOutside(outFile) {
  const { rows, caches } = outsideRows();
  const lines = [
    '# Every file of the project folder outside app/, as it was when the rooms scaffold (R0) started, 11 Nov 2026.',
    '# Not listed: .git/, .claude/, detector/blind_run_suite_revit/, detector/keys/suite_revit/, and the documents the',
    '# main session edits (walkthrough_app_plan.md and every README.md). "<sha1>  <bytes>  <path>".',
    '# Written by tools/rooms/reference.mjs outside --write; checked with --check (DESIGN R-13, ACCEPTANCE RA-16).',
    `# ${rows.length} files, ${rows.reduce((n, r) => n + r[1], 0)} bytes.`,
    ...caches.map((c) => `# pycache ${c}`),
    ...rows.map(([rel, size, hash]) => `${hash}  ${size}  ${rel}`),
  ];
  mkdirSync(dirname(outFile), { recursive: true });
  writeFileSync(outFile, lines.join('\n') + '\n');
  console.log(`${rows.length} files, ${caches.length} __pycache__ folders -> ${outFile}`);
  return 0;
}

function checkOutside(refFile) {
  const text = readFileSync(refFile, 'utf8').split('\n').filter(Boolean);
  const cachesBefore = text.filter((l) => l.startsWith('# pycache ')).map((l) => l.slice(10));
  const want = new Map(text.filter((l) => !l.startsWith('#')).map((l) => {
    const [hash, size, ...rest] = l.split('  ');
    return [rest.join('  '), [Number(size), hash]];
  }));
  const { rows, caches } = outsideRows();
  const have = new Map(rows.map(([rel, size, hash]) => [rel, [size, hash]]));
  const out = [];
  for (const [rel, [size, hash]] of want) {
    const now = have.get(rel);
    if (!now) out.push(`  gone     ${rel}`);
    else if (now[0] !== size || now[1] !== hash) out.push(`  changed  ${rel}`);
  }
  for (const rel of have.keys()) if (!want.has(rel)) out.push(`  new      ${rel}`);
  for (const c of caches) if (!cachesBefore.includes(c)) out.push(`  new __pycache__  ${c}`);
  console.log(`${want.size} listed files; ${out.length} differences; __pycache__ folders ${caches.length} (${cachesBefore.length} at the start)`);
  for (const line of out) console.log(line);
  return out.length ? 1 : 0;
}

// ---- main -----------------------------------------------------------------------------------------------------------
const [what, ...rest] = process.argv.slice(2);
const flag = (name) => { const i = rest.indexOf(name); return i >= 0 ? rest[i + 1] : undefined; };
let code = 2;
if (what === 'versions') {
  const data = resolve(flag('--data') ?? join(APP, 'data'));
  const file = join(REF, 'versions.sha1');
  if (rest.includes('--write')) code = writeVersions(data, file, 'The saved versions of app/data when the rooms scaffold (R0) started, 11 Nov 2026 (DESIGN R-13, RA-2).');
  else if (rest.includes('--check')) code = checkVersions(data, file);
} else if (what === 'outside') {
  const file = join(REF, 'outside.txt');
  if (rest.includes('--write')) code = writeOutside(file);
  else if (rest.includes('--check')) code = checkOutside(file);
} else if (what === 'store') {
  const data = resolve(rest[0] ?? '');
  if (flag('--write')) code = writeVersions(data, resolve(flag('--write')), `The saved versions of a store (${slash(data)}).`);
  else if (flag('--check')) code = checkVersions(data, resolve(flag('--check')));
}
if (code === 2) console.error('usage: node tools/rooms/reference.mjs versions|outside --write|--check, or store <dir> --write <out>|--check <ref>');
process.exit(code);
