// Close-ups of the slimmed models next to the full ones, for a look by eye (headless Edge, the real graphics chip; never a
// visible window): the same Ghost view, about 1 m and 3 m from a mollie chair (visitor chair01, 241,326 triangles) at level 1's
// desks, and about 1 m from a monitor, in B (full) and C at 20,000 / 10,000 / 5,000 / 2,500 a piece. Then
//   python -B compose_closeup.py <shots folder>      puts them side by side into slimmed_closeup.png here.
//   node shots_closeup.mjs          Env: PORT (9770 - 9789, default 9785), BF_TMP (temp folder, default %TEMP%\bank-furnished), OUT
import { mkdirSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { launch, sleep } from './browser.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TMP = process.env.BF_TMP || path.join(os.tmpdir(), 'bank-furnished');
const OUT = process.env.OUT || path.join(TMP, 'closeup');
mkdirSync(OUT, { recursive: true });
const page = pathToFileURL(path.join(HERE, 'bank_furnished.html')).href;
// Ghost views (three.js x, y, z = plan x, height, -plan y), looking at the piece: L1-seat-012's chair stands at plan (-1.79, -2.43)
const look = (name, at, from, h, lens) => {
  const dx = at[0] - from[0], dy = at[1] - from[1], d = Math.hypot(dx, dy);
  const yaw = Math.atan2(-dx, dy) * 180 / Math.PI, pitch = -Math.atan2(h - at[2], d) * 180 / Math.PI;
  return { name, url: `?build=0&mode=ghost&x=${from[0]}&y=${h}&z=${-from[1]}&yaw=${yaw.toFixed(1)}&pitch=${pitch.toFixed(1)}&lens=${lens}` };
};
const VIEWS = [
  look('chair_1m', [-1.79, -2.43, 0.45], [-0.95, -1.85], 1.35, 35),
  look('chair_3m', [-1.79, -2.43, 0.45], [0.55, -0.45], 1.6, 35),
  look('monitor_1m', [-2.75, -2.5, 0.9], [-3.45, -3.05], 1.25, 35),          // from the user's side: screen, keyboard (11,440 triangles of keys) and mouse
];
const WAYS = [['B'], ['C', 20000], ['C', 10000], ['C', 5000], ['C', 2500]];
const ready = '!!(window.__bankFurnished && window.__bankFurnished.ready)';
const b = await launch({ port: Number(process.env.PORT || 9785), profile: path.join(TMP, 'profile-closeup'), step: 'furniture_test bank_furnished close-ups' });
try {
  for (const v of VIEWS) {
    await b.goto(page + v.url, ready, 180000);
    await b.evaluate(`(() => { const s = document.createElement('style'); s.textContent = '#bf-panel, #panel, #vm-hud, #vm-cross, #hint { display: none !important; }'; document.head.appendChild(s); })()`);
    for (const [m, bud] of WAYS) {
      await b.evaluate(`__bankFurnished.setMode('${m}'${bud ? `, ${bud}` : ''})`);
      await sleep(1200);
      await b.shot(path.join(OUT, `${v.name}_${m}${bud || ''}.png`));
    }
    console.log(v.name, v.url, JSON.stringify(await b.evaluate('__bankFurnished.live()')));
  }
  const errs = b.logs.filter(l => /exception|error/i.test(l));
  if (errs.length) console.log('page errors:\n' + errs.join('\n'));
} finally {
  await b.close();
}
console.log('shots in ' + OUT);
