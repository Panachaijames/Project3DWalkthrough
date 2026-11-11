// The rules of tools/check-openapi-additive.mjs as pure functions, so they can be tested on hand-made pairs
// (docs/rooms/DESIGN.md R-12.5; rooms scaffold R0). No I/O here.
//
//   schemaChange(old, now)      why a component schema's change is NOT additive, or null. Additive = deep-equal, or: an
//                               object schema gained properties that are not required, with every old property, the
//                               `required` list and every other key of the schema deep-equal.
//   symbolChange(old, now)      the same for one exported symbol of the generated client (its source text): identical,
//                               or an interface / object type alias that gained OPTIONAL members while every old
//                               member's text stayed identical.
import { isDeepStrictEqual } from 'node:util';
import ts from 'typescript';

/** @returns {string | null} */
export function schemaChange(old, now) {
  if (isDeepStrictEqual(old, now)) return null;
  const isObj = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  if (!isObj(old) || !isObj(now) || !isObj(old.properties) || !isObj(now.properties)) return 'changed';
  for (const key of new Set([...Object.keys(old), ...Object.keys(now)])) {
    if (key === 'properties') continue;
    if (!isDeepStrictEqual(old[key], now[key])) return key === 'required' ? 'its required list changed' : `its ${key} changed`;
  }
  for (const [name, prop] of Object.entries(old.properties)) {
    if (!(name in now.properties)) return `property ${name} is gone`;
    if (!isDeepStrictEqual(prop, now.properties[name])) return `property ${name} changed`;
  }
  const required = new Set(Array.isArray(now.required) ? now.required : []);
  for (const name of Object.keys(now.properties)) {
    if (!(name in old.properties) && required.has(name)) return `new property ${name} is required`;   // unreachable while `required` is compared; kept as the rule's own words
  }
  return null;
}

/** The members of `export interface X { ... }` or `export type X = { ... }` by name -> { text, optional }, else null. */
function membersOf(text) {
  const sf = ts.createSourceFile('symbol.ts', text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  if (sf.statements.length !== 1) return null;
  const st = sf.statements[0];
  let list = null, head = '';
  if (ts.isInterfaceDeclaration(st)) {
    list = st.members;
    head = text.slice(0, st.members.pos);
  } else if (ts.isTypeAliasDeclaration(st) && ts.isTypeLiteralNode(st.type)) {
    list = st.type.members;
    head = text.slice(0, st.type.members.pos);
  }
  if (!list) return null;
  const members = new Map();
  for (const m of list) {
    const name = m.name ? m.name.getText(sf) : `(${ts.SyntaxKind[m.kind]} ${m.pos})`;
    if (members.has(name)) return null;
    members.set(name, { text: m.getText(sf).replace(/[;,]\s*$/, ''), optional: !!m.questionToken });   // the last member may end without ';'
  }
  return { head: head.replace(/\s+/g, ' ').trim(), members };
}

/** @returns {string | null} */
export function symbolChange(old, now) {
  if (old === now) return null;
  const a = membersOf(old), b = membersOf(now);
  if (!a || !b || a.head !== b.head) return 'changed';
  for (const [name, m] of a.members) {
    const n = b.members.get(name);
    if (!n) return `member ${name} is gone`;
    if (n.text !== m.text) return `member ${name} changed`;
  }
  for (const [name, n] of b.members) {
    if (!a.members.has(name) && !n.optional) return `new member ${name} is not optional`;
  }
  return null;
}
