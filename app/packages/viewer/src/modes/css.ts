// The modes CSS chunk (DESIGN.md 11.6), added once per viewer through ctx.ui.addStyle. Port of viewer_modes.js's <style>,
// rule for rule: ids become [data-wt=...] (the selector map), body classes root flags (.wtv[data-fp] ...), every overlay
// `position: absolute` inside the root instead of `fixed`, every vw / vh a % of the root (the overlays are the root's
// children), and the width / height media queries `@container wtv` queries with the same numbers. The photo frame's
// `100vmax` shade stays (the root clips it). The classes vm-label / vm-row are also used by the replay's markup (as
// build_replay.js used the modes' ones). Owner: builder B.
export const MODES_CSS = `
.wtv [data-wt=panel], .wtv [data-wt=hint] { z-index: 6 }
.wtv .vm-label { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); margin: 10px 0 4px }
.wtv .vm-row { display: flex; gap: 6px; flex-wrap: wrap; align-items: center }
.wtv [data-wt=hud] { position: absolute; top: 12px; left: 50%; transform: translateX(-50%); max-width: calc(100% - 24px); box-sizing: border-box; background: #1d2329eb; color: #fff; border-radius: 999px; padding: 6px 8px 6px 14px; font-size: 12.5px; display: none; align-items: center; gap: 8px; z-index: 7 }
.wtv [data-wt=hud] span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.wtv [data-wt=hud] button { padding: 3px 10px; font-size: 12px; flex: none }
.wtv [data-wt=hud] .vm-narrow { display: none }
.wtv [data-wt=cross] { position: absolute; left: 50%; top: 50%; width: 14px; height: 14px; margin: -7px 0 0 -7px; pointer-events: none; display: none; z-index: 4 }
.wtv [data-wt=cross]::before, .wtv [data-wt=cross]::after { content: ''; position: absolute; background: #fff; box-shadow: 0 0 2px #000a }
.wtv [data-wt=cross]::before { left: 6px; top: 0; width: 2px; height: 14px }
.wtv [data-wt=cross]::after { top: 6px; left: 0; height: 2px; width: 14px }
.wtv [data-wt=camera-panel] { position: absolute; top: 12px; right: 12px; width: min(270px, calc(100% - 48px)); max-height: calc(100% - 60px); overflow: auto; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; box-shadow: 0 2px 10px #0001; display: none; z-index: 8; font-size: 13px }
.wtv [data-wt=camera-panel] h2 { font-size: 14px; margin: 0 0 4px; display: flex; justify-content: space-between; align-items: center }
.wtv [data-wt=camera-panel] h2 button { padding: 0 8px }
.wtv [data-wt=camera-panel] .vm-f { margin: 9px 0 }
.wtv [data-wt=camera-panel] .vm-f > div:first-child { display: flex; justify-content: space-between; color: var(--muted); font-size: 12px; margin-bottom: 2px }
.wtv [data-wt=camera-panel] input[type=range] { width: 100%; margin: 0 }
.wtv [data-wt=camera-panel] select { font: inherit; font-size: 13px; padding: 3px 6px; border: 1px solid var(--line); border-radius: 6px; background: #fff; color: var(--ink) }
.wtv [data-wt=camera-panel] .vm-note { color: var(--muted); font-size: 11.5px; margin: 2px 0 6px }
.wtv [data-wt=shot] { width: 100%; margin-top: 10px; padding: 8px; font-weight: 600 }
.wtv [data-wt=photos] { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px }
.wtv [data-wt=photos] img { width: 72px; height: 48px; object-fit: cover; border-radius: 4px; border: 1px solid var(--line); cursor: pointer }
.wtv [data-wt=frame] { position: absolute; pointer-events: none; display: none; z-index: 3 }
.wtv [data-wt=frame].vm-crop { border: 1px solid #fffd; box-shadow: 0 0 0 100vmax #0e121666 }
.wtv [data-wt=frame] i { position: absolute; background: #ffffffa0 }
.wtv [data-wt=flash] { position: absolute; inset: 0; background: #fff; opacity: 0; pointer-events: none; z-index: 9 }
.wtv [data-wt=stick] { position: absolute; left: 22px; bottom: 26px; width: 116px; height: 116px; border-radius: 50%; background: #1d232940; border: 2px solid #ffffffb0; display: none; z-index: 7; touch-action: none; user-select: none; -webkit-user-select: none }
.wtv [data-wt=stick] b { position: absolute; left: 50%; top: 50%; width: 50px; height: 50px; margin: -25px 0 0 -25px; border-radius: 50%; background: #fffffff0; box-shadow: 0 1px 5px #0006; pointer-events: none }
.wtv [data-wt=updown] { position: absolute; right: 22px; bottom: 26px; display: none; flex-direction: column; gap: 10px; z-index: 7 }
.wtv [data-wt=updown] button { min-width: 104px; padding: 12px 10px; border-radius: 12px; background: #1d2329c0; border: 2px solid #ffffffb0; color: #fff; font-weight: 600; touch-action: none; user-select: none; -webkit-user-select: none }
.wtv .vm-off { opacity: .45; pointer-events: none }
.wtv[data-crowded] [data-wt=panel] { display: none }
@container wtv (max-width: 700px) or (max-height: 500px) {
.wtv[data-fp] [data-wt=panel], .wtv[data-fp] [data-wt=hint], .wtv[data-camopen] [data-wt=panel] { display: none }
.wtv [data-wt=hud] .vm-narrow { display: inline-block }
.wtv [data-wt=hud] .vm-more { display: none }
.wtv [data-wt=camera-panel] .vm-f { margin: 5px 0 }
.wtv [data-wt=shot] { margin-top: 6px; padding: 7px }
.wtv [data-wt=photos] img { width: 54px; height: 36px }
.wtv [data-wt=photos] img:nth-child(n+5) { display: none }
}
@container wtv (max-width: 700px) {
.wtv [data-wt=camera-panel] { top: 58px; left: 12px; right: 12px; width: auto; max-height: 42%; padding: 8px 12px }
}
@container wtv (min-width: 701px) {
.wtv[data-fp] [data-wt=camera-panel] { top: 58px; max-height: calc(100% - 70px) }
.wtv[data-touchui] [data-wt=camera-panel] { max-height: calc(100% - 270px); min-height: 110px }
}
.wtv [data-wt=snap] { background: var(--accent) !important; border-color: #fff !important }
`;
