#!/usr/bin/env node
// Checks the generated API client (DESIGN.md 2, 10.5): apps/web/src/api/generated/sdk.gen.ts exists and exports a function
// for every operationId of apps/web/openapi.json, and the TanStack Query file has the options / mutation helpers.
// openapi-ts exits 0 even when it generated nothing, so `npm run gen:api` ends with this check. Exits 1 on any miss.
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { APP } from './lib.mjs';

const web = path.join(APP, 'apps', 'web');
const specPath = path.join(web, 'openapi.json');
const sdkPath = path.join(web, 'src', 'api', 'generated', 'sdk.gen.ts');
const rqPath = path.join(web, 'src', 'api', 'generated', '@tanstack', 'react-query.gen.ts');
const problems = [];

if (!existsSync(specPath)) problems.push(`missing ${specPath} (run npm run gen:api)`);
if (!existsSync(sdkPath)) problems.push(`missing ${sdkPath} (openapi-ts generated nothing?)`);
if (!problems.length) {
  const spec = JSON.parse(readFileSync(specPath, 'utf8'));
  const ops = [];
  for (const item of Object.values(spec.paths ?? {})) {
    for (const [method, op] of Object.entries(item)) if (op && op.operationId) ops.push({ id: op.operationId, method });
  }
  if (!ops.length) problems.push('openapi.json has no operations');
  const exported = name => new RegExp(`export\\s+(?:const|function|async\\s+function)\\s+${name}\\b`);
  const sdk = readFileSync(sdkPath, 'utf8');
  for (const { id } of ops) if (!exported(id).test(sdk)) problems.push(`sdk.gen.ts exports no function ${id}`);
  if (!existsSync(rqPath)) problems.push(`missing ${rqPath}`);
  else {
    const rq = readFileSync(rqPath, 'utf8');
    for (const { id, method } of ops) {
      const helper = method === 'get' ? `${id}Options` : `${id}Mutation`;
      if (!exported(helper).test(rq)) problems.push(`react-query.gen.ts exports no ${helper}`);
    }
  }
  if (!problems.length) console.log(`check-generated: ok (${ops.length} operations; sdk functions and query helpers present)`);
}
if (problems.length) {
  for (const p of problems) console.error(`check-generated: ${p}`);
  process.exit(1);
}
