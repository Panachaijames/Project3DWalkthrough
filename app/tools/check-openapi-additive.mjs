#!/usr/bin/env node
// Proves the upload milestone's API change is ADDITIVE (docs/upload/DESIGN.md U-15.2; scaffold U0):
//  1. apps/web/openapi.json against the committed one (`git show HEAD:...`, read-only): every old path, every old method
//     with its whole operation (parameters, body, responses, texts) and every old component schema is deep-equal in
//     the new document;
//  2. apps/web/src/api/generated/** compared BY EXPORTED SYMBOL: each committed file and its new version are parsed with
//     the TypeScript compiler API, import declarations are ignored (Hey API writes each import list on one long line,
//     which any new operation rewrites), and every previously exported function, const, type, interface and re-exported
//     name must still be there with identical text;
//  3. the two copies of each contract file are identical: docs/contracts.ts = packages/viewer/src/contracts.ts and
//     docs/upload/upload-contracts.ts = apps/web/src/upload/contracts.ts.
// Exits 1 listing what moved. `--base <rev>` compares with another commit. The default is 66b4c06, the API before the
// rooms milestone (docs/rooms/DESIGN.md R-12.5; before that milestone the default was the foundation's baseline commit
// 9eb2d58, which still passes: `--base 9eb2d58`. UR, V3-10: the default was once HEAD, which held the milestone itself,
// so the check compared the API with itself and could not fail).
//
// The rooms milestone's one more additive case (R-12.5; tools/openapi-additive-rules.mjs, tested on hand-made pairs in
// packages/viewer/test/unit/scaffold/openapi-additive.test.ts): an existing component schema may gain a property that
// is NOT required (every old property, its `required` list and every other key deep-equal), and an interface or object
// type of the generated client may gain OPTIONAL members (every other member's text identical).
//
// `--openapi <file>` checks that document instead of apps/web/openapi.json, and then only part 1 runs (for tests of the
// rule itself: a required property added, or a property's type changed, must fail).
//   node tools/check-openapi-additive.mjs
//   node tools/check-openapi-additive.mjs --base 9eb2d58
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { isDeepStrictEqual } from 'node:util';
import ts from 'typescript';
import { APP, parseArgs } from './lib.mjs';
import { schemaChange, symbolChange } from './openapi-additive-rules.mjs';

const args = parseArgs(process.argv.slice(2), { flags: ['base', 'openapi'] });
/** "Baseline: prototypes, plan and the application foundation (4 Nov 2026)": the API the upload milestone only added to. */
export const FOUNDATION = '9eb2d5819784472821ad6a8b0c11eba642a27d0b';
/** The API before the rooms milestone (main, 10 Nov 2026): what this milestone must only add to. */
export const BEFORE_ROOMS = '66b4c063edaf2fa77d81b93c47ec93e4467ba9cd';
const BASE = args.base ?? BEFORE_ROOMS;
const problems = [];
const notes = [];

const git = (...a) => execFileSync('git', a, { cwd: APP, encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 });
const atBase = rel => git('show', `${BASE}:./${rel}`);
// ls-tree run in app/ prints paths relative to app/ (without --full-name)
const filesAtBase = dir => git('ls-tree', '-r', '--name-only', BASE, '--', dir).split('\n').filter(Boolean);

// ---------------------------------------------------------------------------------------------------- 1. openapi.json
const OPENAPI = 'apps/web/openapi.json';
const oldDoc = JSON.parse(atBase(OPENAPI));
const newDoc = JSON.parse(readFileSync(args.openapi ? path.resolve(args.openapi) : path.join(APP, OPENAPI), 'utf8'));
let oldOps = 0;
for (const [p, item] of Object.entries(oldDoc.paths ?? {})) {
  const now = newDoc.paths?.[p];
  if (!now) { problems.push(`openapi: path ${p} is gone`); continue; }
  for (const [method, op] of Object.entries(item)) {
    oldOps++;
    if (!(method in now)) problems.push(`openapi: ${method.toUpperCase()} ${p} is gone`);
    else if (!isDeepStrictEqual(op, now[method])) problems.push(`openapi: ${method.toUpperCase()} ${p} (${op.operationId}) changed`);
  }
}
const oldSchemas = oldDoc.components?.schemas ?? {};
const grown = [];
for (const [name, schema] of Object.entries(oldSchemas)) {
  const now = newDoc.components?.schemas?.[name];
  if (!now) { problems.push(`openapi: component schema ${name} is gone`); continue; }
  const why = schemaChange(schema, now);
  if (why) problems.push(`openapi: component schema ${name}: ${why}`);
  else if (!isDeepStrictEqual(schema, now)) grown.push(name);
}
const newOps = Object.values(newDoc.paths ?? {}).reduce((n, item) => n + Object.keys(item).length, 0);
notes.push(`openapi: ${oldOps} old operations and ${Object.keys(oldSchemas).length} old schemas unchanged`
  + (grown.length ? ` (${grown.length} of them gained optional properties: ${grown.join(', ')})` : '')
  + `; ${newOps} operations, ${Object.keys(newDoc.components?.schemas ?? {}).length} schemas now`);

// ---------------------------------------------------------------------------------------- 2. generated client by symbol
function exportsOf(fileName, text) {
  const sf = ts.createSourceFile(fileName, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const out = new Map();                       // symbol key -> text
  const isExported = node => ts.getCombinedModifierFlags(node) & ts.ModifierFlags.Export;
  for (const st of sf.statements) {
    if (ts.isImportDeclaration(st) || ts.isImportEqualsDeclaration(st)) continue;
    if (ts.isExportDeclaration(st)) {
      const from = st.moduleSpecifier ? st.moduleSpecifier.text : '';
      if (!st.exportClause) { out.set(`* from ${from}`, st.getText(sf)); continue; }
      if (ts.isNamespaceExport(st.exportClause)) { out.set(`* as ${st.exportClause.name.text} from ${from}`, st.getText(sf)); continue; }
      for (const el of st.exportClause.elements) {
        const typeOnly = st.isTypeOnly || el.isTypeOnly;
        out.set(`re-export ${el.name.text} from ${from}`, `${typeOnly ? 'type ' : ''}${el.propertyName ? el.propertyName.text + ' as ' : ''}${el.name.text}`);
      }
      continue;
    }
    if (ts.isExportAssignment(st)) { out.set('export default', st.getText(sf)); continue; }
    if (!isExported(st)) continue;
    if (ts.isVariableStatement(st)) {
      for (const d of st.declarationList.declarations) out.set(`const ${d.name.getText(sf)}`, st.getText(sf));
    } else if (ts.isFunctionDeclaration(st) || ts.isTypeAliasDeclaration(st) || ts.isInterfaceDeclaration(st)
      || ts.isClassDeclaration(st) || ts.isEnumDeclaration(st) || ts.isModuleDeclaration(st)) {
      const kind = ts.SyntaxKind[st.kind];
      out.set(`${kind} ${st.name ? st.name.getText(sf) : '(default)'}`, st.getText(sf));
    } else {
      out.set(`statement ${st.pos}`, st.getText(sf));
    }
  }
  return out;
}

const GEN = 'apps/web/src/api/generated';
let symbols = 0;
const widened = [];
for (const rel of args.openapi ? [] : filesAtBase(GEN)) {
  const abs = path.join(APP, rel);
  if (!existsSync(abs)) { problems.push(`generated: ${rel} is gone`); continue; }
  const before = exportsOf(rel, atBase(rel));
  const after = exportsOf(rel, readFileSync(abs, 'utf8'));
  for (const [key, text] of before) {
    symbols++;
    if (!after.has(key)) { problems.push(`generated: ${rel}: ${key} is gone`); continue; }
    const why = symbolChange(text, after.get(key));
    if (why) problems.push(`generated: ${rel}: ${key}: ${why}`);
    else if (after.get(key) !== text) widened.push(key.replace(/^\w+ /, ''));
  }
}
if (!args.openapi) {
  notes.push(`generated: ${symbols} previously exported symbols compared in ${filesAtBase(GEN).length} files`
    + (widened.length ? ` (${widened.length} gained optional members: ${widened.join(', ')})` : ''));
}

// ------------------------------------------------------------------------------------------------ 3. the contract copies
for (const [a, b] of args.openapi ? [] : [['docs/contracts.ts', 'packages/viewer/src/contracts.ts'],
                                         ['docs/upload/upload-contracts.ts', 'apps/web/src/upload/contracts.ts']]) {
  const pa = path.join(APP, a), pb = path.join(APP, b);
  if (!existsSync(pa) || !existsSync(pb)) { problems.push(`copies: ${existsSync(pa) ? b : a} is missing`); continue; }
  if (!readFileSync(pa).equals(readFileSync(pb))) problems.push(`copies: ${a} and ${b} differ`);
  else notes.push(`copies: ${a} = ${b}`);
}

for (const n of notes) console.log(`check-openapi-additive: ${n}`);
if (problems.length) {
  for (const p of problems) console.error(`check-openapi-additive: ${p}`);
  process.exit(1);
}
console.log(`check-openapi-additive: ok (additive against ${BASE})`);
