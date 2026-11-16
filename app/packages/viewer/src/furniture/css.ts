// The furniture CSS chunk (DESIGN.md 11.6; furniture_boxes.js's <style>), added once through ctx.ui.addStyle when the model
// has furniture. Owner: builder C. Every selector under `.wtv`, the prototype's `.fb-*` classes as the data-wt names of the
// selector map; sizes root-relative (the label's max-width is % of the root, which is its containing block); no vh / vw and no
// size media query. `.fb-sw` and `.fb-h` were border-box on the pages and stay so (more specific than `.wtv *`'s revert).
export const FURNITURE_CSS = `
.wtv [data-wt=furniture] { margin-top: 10px; border-top: 1px solid var(--line, #d5dade); padding-top: 8px; font-size: 12.5px; }
.wtv [data-wt=furniture-titlebar] { display: flex; justify-content: space-between; align-items: center; font-size: 11px;
  letter-spacing: .06em; text-transform: uppercase; color: var(--muted, #5b6670); }
.wtv [data-wt=furniture-titlebar] label { font-size: 12px; letter-spacing: 0; text-transform: none; color: var(--ink, #1d2329); }
.wtv [data-wt=furniture-note] { color: var(--muted, #5b6670); font-size: 11.5px; margin: 4px 0 6px; }
.wtv [data-wt=furniture-door] { display: flex; align-items: center; gap: 6px; margin: 0 0 6px; font-size: 12px; color: var(--ink, #1d2329); }
.wtv [data-wt=furniture-door] input { margin: 0; }
.wtv [data-wt=furniture-row], .wtv [data-wt=furniture-head] { display: grid; grid-template-columns: 16px 12px minmax(0, 1fr) 52px 38px;
  gap: 6px; align-items: center; padding: 1px 0; }
.wtv [data-wt=furniture-row] input[type=checkbox] { margin: 0; justify-self: center; }
.wtv [data-wt=furniture-head] { font-size: 10px; color: var(--muted, #5b6670); text-align: center; }
.wtv [data-wt=furniture-head] span:nth-child(3) { text-align: left; }
.wtv [data-wt=kind-swatch] { width: 12px; height: 12px; border-radius: 3px; border: 1px solid #0003; box-sizing: border-box; }
.wtv [data-wt=kind-label] { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wtv [data-wt=kind-height] { width: 100%; box-sizing: border-box; font: inherit; font-size: 12.5px; text-align: right; padding: 2px 5px;
  border: 1px solid var(--line, #d5dade); border-radius: 5px; background: #fff; color: var(--ink, #1d2329); color-scheme: light; }
.wtv [data-wt=kind-height][data-edited] { border-color: var(--accent, #2f6f8f); }
.wtv [data-wt=kind-height][data-bad] { border-color: #b42318; background: #fdecea; }
.wtv [data-wt=furniture-buttons] { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.wtv [data-wt=furniture-tip] { position: absolute; display: none; pointer-events: none; z-index: 5; max-width: min(340px, calc(100% - 24px));
  overflow-wrap: anywhere; background: #1d2329eb; color: #fff; border-radius: 8px; padding: 6px 10px; font-size: 12px; line-height: 1.4; }
.wtv [data-wt=furniture-tip] span { color: #c9d1d8; }
.wtv [data-wt=furniture-row][data-empty] [data-wt=kind-label], .wtv [data-wt=furniture-row][data-empty] [data-wt=kind-swatch] { opacity: .45; }
.wtv [data-wt=furniture-edit-hint] { color: var(--muted, #5b6670); font-size: 11.5px; margin: -2px 0 6px; }
.wtv [data-wt=furniture-removed] { margin-top: 6px; font-size: 12px; color: var(--ink, #1d2329); }
.wtv [data-wt=furniture-removed] button, .wtv [data-wt=box-card] [data-wt=box-undo] { border: 0; background: none; padding: 0;
  border-radius: 0; font-size: 12px; color: var(--accent, #2f6f8f); text-decoration: underline; cursor: pointer; }
.wtv [data-wt=box-card] { position: absolute; top: 12px; right: 12px; width: min(280px, calc(100% - 48px)); box-sizing: border-box;
  z-index: 7; pointer-events: auto; display: none; background: var(--panel, #ffffffee); border: 1px solid var(--line, #d5dade);
  border-left: 4px solid #ff2bd6; border-radius: 10px; padding: 10px 12px; box-shadow: 0 2px 10px #0001; font-size: 12.5px;
  line-height: 1.45; overflow-wrap: anywhere; color: var(--ink, #1d2329); }
.wtv [data-wt=box-card] [data-wt=box-kind] { font-weight: 600; font-size: 13.5px; padding-right: 22px; }
.wtv [data-wt=box-card] [data-wt=box-note], .wtv [data-wt=box-card] [data-wt=box-id] { color: var(--muted, #5b6670); }
.wtv [data-wt=box-card] [data-wt=box-id] { font-size: 11px; }
.wtv [data-wt=box-card] [data-wt=box-cascade] { margin-top: 4px; color: #8a4b00; }
.wtv [data-wt=box-card] [data-wt=box-buttons] { display: flex; gap: 8px; align-items: center; margin-top: 8px; }
.wtv [data-wt=box-card] [data-wt=box-delete] { background: #b42318; border-color: #b42318; color: #fff; }
.wtv [data-wt=box-card] [data-wt=box-close] { position: absolute; top: 6px; right: 8px; border: 0; background: none; padding: 0 4px;
  font-size: 16px; line-height: 1.2; color: var(--muted, #5b6670); }
.wtv [data-wt=box-toast] { position: absolute; left: 50%; bottom: 34px; transform: translateX(-50%); max-width: calc(100% - 24px);
  box-sizing: border-box; z-index: 7; pointer-events: none; display: none; background: #1d2329eb; color: #fff; border-radius: 8px;
  padding: 6px 12px; font-size: 12.5px; overflow-wrap: anywhere; text-align: center; }
.wtv [data-wt=boxes-restore] { position: absolute; display: none; flex-direction: column; box-sizing: border-box; z-index: 7;
  width: min(380px, calc(100% - 24px)); max-height: 50%; background: var(--panel, #ffffffee); border: 1px solid var(--line, #d5dade);
  border-radius: 10px; box-shadow: 0 2px 10px #0002; font-size: 12.5px; color: var(--ink, #1d2329); }
.wtv [data-wt=boxes-restore-head] { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px 6px 12px; }
.wtv [data-wt=boxes-restore-close] { border: 0; background: none; padding: 0 4px; font-size: 16px; line-height: 1.2; color: var(--muted, #5b6670); }
.wtv [data-wt=boxes-restore-list] { overflow: auto; flex: 1 1 auto; min-height: 0; padding: 0 12px; }
.wtv [data-wt=boxes-restore-row] { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 4px 0;
  border-top: 1px solid var(--line, #d5dade); overflow-wrap: anywhere; }
.wtv [data-wt=boxes-restore-row] small { color: var(--muted, #5b6670); font-size: 11px; }
.wtv [data-wt=boxes-restore-row] button { flex: none; font-size: 12px; padding: 3px 8px; }
.wtv [data-wt=boxes-restore-foot] { display: flex; justify-content: flex-start; padding: 8px 12px; border-top: 1px solid var(--line, #d5dade); }
.wtv[data-replay] [data-wt=box-card], .wtv[data-replay] [data-wt=box-toast] { visibility: hidden; }
`;
