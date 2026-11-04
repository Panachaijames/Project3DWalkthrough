// Builds the two pages of the chair test (run from this folder, after slim_chair.mjs):
//   node make_chair_test.mjs
//   chair_test.html     a copy of ../bank_test/bank_3d_preview.html (read only, unchanged) with one module script added before
//                       </body> (chair_test_module.js with chair_load.js, Chair.glb as base64 and chair_slim.json) and its
//                       title changed; three still comes from the CDN through the page's own import map
//   chair_compare.html  the full and the slimmed chair side by side (chair_compare_module.js), the same data
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PROJECT = path.resolve(HERE, '..');
const BANK = path.join(PROJECT, 'bank_test', 'bank_3d_preview.html');
const read = p => readFileSync(p, 'utf8');
const bank = read(BANK);
const glb = readFileSync(path.join(PROJECT, 'Chair.glb'));
const slim = read(path.join(HERE, 'chair_slim.json'));
const load = read(path.join(HERE, 'chair_load.js'));
const fill = src => src.replace('__CHAIR_LOAD__', () => load).replace("'__GLB_B64__'", () => `'${glb.toString('base64')}'`).replace('__SLIM_JSON__', () => slim);
const eol = bank.includes('\r\n') ? '\r\n' : '\n';                          // the bank page has CRLF line ends: so does what is added
const lines = s => s.replace(/\r?\n/g, eol);

// ---------------------------------------------------------------- chair_test.html
const TITLE = '<title>Bank branch test</title>';
if (!bank.includes(TITLE) || bank.lastIndexOf('</body>') < 0) throw new Error('the bank page is not the one this was written for (title or </body> not found)');
const module = fill(read(path.join(HERE, 'chair_test_module.js')));
const added = lines(`<!-- ===== Chair test (added by furniture_test/make_chair_test.mjs; everything above is the bank page as it is) ===== -->\n<script type="module">\n${module}</script>\n`);
const at = bank.lastIndexOf('</body>');
const page = bank.slice(0, at).replace(TITLE, '<title>Chair test (bank)</title>') + added + bank.slice(at);
writeFileSync(path.join(HERE, 'chair_test.html'), page);

// ---------------------------------------------------------------- chair_compare.html
const compare = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chair: full and slimmed</title>
<style>
  :root { --bg:#eef0f2; --ink:#1d2329; --muted:#5b6670; }
  html, body { margin:0; height:100%; overflow:hidden; background:var(--bg); color:var(--ink); font:14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; }
  canvas { display:block; }
  .lab { position:fixed; top:14px; width:50%; text-align:center; font-size:15px; pointer-events:none; }
  .lab b { font-size:17px; }
  #l-full { left:0; } #l-slim { left:50%; }
  #split { position:fixed; top:0; bottom:0; left:50%; width:1px; background:#c9cfd4; }
  #note { position:fixed; left:16px; right:16px; bottom:10px; text-align:center; color:var(--muted); font-size:12.5px; pointer-events:none; }
</style>
</head>
<body>
<div class="lab" id="l-full"></div><div class="lab" id="l-slim"></div><div id="split"></div><div id="note"></div>
<script type="importmap">
{ "imports": { "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
               "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/" } }
</script>
<script type="module">
${fill(read(path.join(HERE, 'chair_compare_module.js')))}</script>
</body>
</html>
`;
writeFileSync(path.join(HERE, 'chair_compare.html'), compare);
const kb = s => Math.round(Buffer.byteLength(s) / 1024);
console.log(`chair_test.html ${kb(page)} KB (bank page ${kb(bank)} KB, sha1 ${createHash('sha1').update(bank).digest('hex').slice(0, 12)}) | chair_compare.html ${kb(compare)} KB`);
