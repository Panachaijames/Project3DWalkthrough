// BASE_CSS: the root's CSS, the first chunk of the viewer's one stylesheet (DESIGN.md 11.6, 18.17). Owner: builder C.
// The pages' <style> (bank, hotel, suite and house generators; the same rules on all four) moved under `.wtv`:
//   * it starts by undoing the host's reset: every element inside the root starts from the browser's own defaults, exactly
//     as on the prototype pages, whatever the host page resets (Tailwind's preflight is in @layer base: these unlayered rules
//     beat it); then the root rule (the pages' body: font, colour, background, the custom properties);
//   * `position: fixed` became `absolute` in the root, `vw` / `vh` became `%` of the root (every overlay is an absolute child
//     of the root, so `%` resolves against it), the pages' width / height media queries `@container wtv` queries;
//   * `.on` became `aria-pressed="true"`, ids and classes the data-wt names of the selector map;
//   * the side panel's z-index 6 and its hiding rules (viewer_modes.js `.vm-panel`, `.vm-crowded`, `.vm-fp`, `.vm-camopen`;
//     build_replay.js `.br-on`) keyed on the root flags that modes and the replay set (data-crowded, data-fp, data-camopen,
//     data-replay): the panel and the hint are this module's, so their rules are here too.
// No vh / vw and no size media query (D-17.2 ui).
export const BASE_CSS = `.wtv, .wtv *, .wtv *::before, .wtv *::after { all: revert; }
.wtv { --bg: #eef0f2; --panel: #ffffffee; --ink: #1d2329; --muted: #5b6670; --line: #d5dade;
  position: relative; width: 100%; height: 100%; overflow: hidden; container: wtv / size;
  background: var(--bg); color: var(--ink); font: 14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; }
.wtv canvas { display: block; width: 100%; height: 100%; }
.wtv h1 { font-size: 15px; margin: 0 0 4px; }
.wtv p { margin: 0 0 10px; color: var(--muted); font-size: 12.5px; }
.wtv .wtv-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.wtv button { border: 1px solid var(--line); background: #fff; border-radius: 7px; padding: 5px 10px; cursor: pointer; font: inherit;
  font-size: 13px; color: var(--ink); }
.wtv button[aria-pressed=true] { background: var(--accent); border-color: var(--accent); color: #fff; }
.wtv label { font-size: 13px; display: flex; align-items: center; gap: 6px; }
.wtv .wtv-panel { position: absolute; top: 12px; left: 12px; width: min(330px, calc(100% - 48px)); max-height: calc(100% - 60px);
  overflow: auto; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px;
  box-shadow: 0 2px 10px #0001; z-index: 6; }
.wtv .wtv-panel[data-furniture] { max-height: calc(100% - 90px); }
.wtv [data-wt=legend] { font-size: 12.5px; line-height: 1.9; margin-top: 8px; }
.wtv [data-wt=legend] > span { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin: 0 4px 0 8px; vertical-align: -1px; }
.wtv [data-wt=legend] > span:first-child { margin-left: 0; }
.wtv [data-wt=legend][data-layout=lines] { line-height: 1.45; }
.wtv [data-wt=legend][data-layout=lines] > div { margin: 3px 0; padding-left: 16px; text-indent: -16px; }
.wtv [data-wt=legend][data-layout=lines] > div > span { display: inline-block; width: 10px; height: 10px; border-radius: 2px;
  margin: 0 6px 0 0; vertical-align: -1px; text-indent: 0; }
.wtv [data-wt=hint] { position: absolute; bottom: 10px; left: 12px; right: 12px; color: var(--muted); font-size: 12px; z-index: 6; }
.wtv [data-wt=error] { display: block; position: absolute; right: 12px; bottom: 12px; max-width: 420px; background: #b42318; color: #fff;
  font-size: 12px; padding: 8px 10px; border-radius: 8px; z-index: 10; white-space: pre-wrap; }
.wtv [data-wt=error][hidden] { display: none; }
.wtv [data-wt=room] { position: absolute; transform: translate(-50%, -50%); font-size: 11.5px; background: #ffffffd9; color: #1d2329;
  padding: 1px 6px; border-radius: 5px; border: 1px solid #d5dade; pointer-events: none; white-space: nowrap; z-index: 2; display: none; }
.wtv[data-crowded] .wtv-panel { display: none; }
.wtv[data-replay] .wtv-panel, .wtv[data-replay] [data-wt=hint] { display: none; }
@container wtv (max-width: 700px) or (max-height: 500px) {
  .wtv[data-fp] .wtv-panel, .wtv[data-fp] [data-wt=hint], .wtv[data-camopen] .wtv-panel { display: none; }
}
`;
