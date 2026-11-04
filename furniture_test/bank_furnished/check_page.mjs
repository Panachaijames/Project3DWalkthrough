// A quick look at bank_furnished.html in headless Edge (the real graphics chip; never a visible window): it opens, every way of
// drawing switches, the counts add up, no page errors; screenshots of Orbit and of the Walk views to OUT for a look by eye.
//   node check_page.mjs            Env: PORT (9770 - 9789, default 9784), BF_TMP (temp folder for the Edge profile, default
//                                  %TEMP%\bank-furnished), OUT (screenshots, default BF_TMP\check). Holds the one-Edge-at-a-time lock.
import { mkdirSync, readFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { launch, sleep } from './browser.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TMP = process.env.BF_TMP || path.join(os.tmpdir(), 'bank-furnished');
const OUT = process.env.OUT || path.join(TMP, 'check');
mkdirSync(OUT, { recursive: true });
const page = pathToFileURL(path.join(HERE, 'bank_furnished.html')).href;
const spots = JSON.parse(readFileSync(path.join(HERE, 'walk_spots.json'), 'utf8')).levels;
const ready = '!!(window.__bankFurnished && window.__bankFurnished.ready)';
const b = await launch({ port: Number(process.env.PORT || 9784), profile: path.join(TMP, 'profile-check'), step: 'furniture_test bank_furnished check' });
const problems = [];
const collect = tag => problems.push(...b.logs.filter(l => /exception|error|warn/i.test(l)).map(l => `${tag}: ${l}`));
try {
  await b.goto(page + '?build=0', ready, 180000);
  await sleep(1500);
  const info = await b.evaluate(`(() => { const F = __bankFurnished; return { gpu: F.gpu, counts: F.counts, boxesDrawn: F.boxesDrawn(), startup: F.startup, downloads: F.downloads.map(d => d.label + ' ' + (d.bytes / 1048576).toFixed(2) + ' MB') }; })()`);
  console.log(JSON.stringify(info, null, 1));
  if (info.boxesDrawn !== info.counts.boxes) problems.push(`A: ${info.boxesDrawn} boxes drawn of ${info.counts.boxes}`);
  await b.shot(path.join(OUT, 'orbit_A.png'));
  for (const [m, bud] of [['B'], ['C', 20000], ['C', 5000], ['C', 2500], ['D'], ['E'], ['P', 'full'], ['P', 5000], ['A']]) {
    const sw = await b.evaluate(`__bankFurnished.setMode('${m}'${bud ? `, ${JSON.stringify(bud)}` : ''})`);
    await sleep(1200);
    const r = await b.evaluate(`(() => { const F = __bankFurnished; return { live: F.live(), boxesDrawn: F.boxesDrawn(), memory: F.memory(), copies: F.copies().length }; })()`);
    console.log(m, bud || '', JSON.stringify({ switch: sw, ...r }));
    await b.shot(path.join(OUT, `orbit_${m}${bud || ''}.png`));
  }
  collect('orbit');
  for (const [lv, s] of Object.entries(spots)) for (const which of ['busiest', 'widest']) {
    const v = s[which];
    await b.goto(page + `?build=0&${v.url}&furniture=B`, ready, 180000);
    await sleep(1500);
    const at = await b.evaluate(`(() => { const s = __viewer.state; return { mode: s.mode, floor: s.floor.key, x: +s.pos.x.toFixed(2), planY: +(-s.pos.z).toFixed(2), yaw: +(s.yaw * 180 / Math.PI).toFixed(1) }; })()`);
    console.log(lv, which, 'asked', v.x, v.y, v.yawDeg, 'got', JSON.stringify(at), JSON.stringify(await b.evaluate('__bankFurnished.live()')));
    await b.shot(path.join(OUT, `walk_${lv}_${which}_B.png`));
    for (const [m, bud] of [['C', 2500], ['D']]) {
      await b.evaluate(`__bankFurnished.setMode('${m}'${bud ? `, ${bud}` : ''})`);
      await sleep(1000);
      console.log('   ', m, bud || '', JSON.stringify(await b.evaluate('__bankFurnished.live()')));
      await b.shot(path.join(OUT, `walk_${lv}_${which}_${m}${bud || ''}.png`));
    }
    collect(`${lv} ${which}`);
  }
} finally {
  await b.close();
}
console.log(problems.length ? 'PROBLEMS:\n' + problems.join('\n') : 'no problems');
