// The replay's CSS chunk (port of build_replay.js's <style>; DESIGN.md 11.6). Owner: builder D.
// Every selector starts with .wtv; the card and the caption are absolute overlays inside the viewer root (never fixed);
// the prototype's vw / vh became % of the root, its (max-width: 700px) media query a container query on the root
// (`container: wtv / size`). `#br-...` ids became the data-wt names of the selector map, `.on` became aria-pressed and the
// body class br-on the root flag data-replay. The page-wide rules the card's buttons, labels and rows relied on (the
// pages' `button`, `button.on`, `label`, and viewer_modes.js's `.vm-label` / `.vm-row`) are repeated here for the card and
// the Build row only, with the same values, so the replay looks as it did whatever the rest of the CSS does; the
// card's own rules are more specific than these, as the prototype's ids were.
export const REPLAY_CSS = `
.wtv [data-wt=replay-card]{position:absolute;top:12px;left:12px;width:min(330px,calc(100% - 48px));max-height:calc(100% - 110px);overflow:auto;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;box-shadow:0 2px 10px #0001;z-index:8;display:none}
.wtv [data-wt=replay-card] button,.wtv [data-wt=replay-row] button{border:1px solid var(--line);background:#fff;border-radius:7px;padding:5px 10px;cursor:pointer;font:inherit;font-size:13px;color:var(--ink)}
.wtv [data-wt=replay-card] button[aria-pressed=true],.wtv [data-wt=replay-row] button[aria-pressed=true]{background:var(--accent);border-color:var(--accent);color:#fff}
.wtv [data-wt=replay-card] label{font-size:13px;display:flex;align-items:center;gap:6px}
.wtv [data-wt=replay-card] .vm-label,.wtv [data-wt=replay-row] .vm-label{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:10px 0 4px}
.wtv [data-wt=replay-card] .vm-row,.wtv [data-wt=replay-row] .vm-row{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.wtv [data-wt=replay-card] h1{font-size:15px;margin:0 0 4px}
.wtv [data-wt=replay-card] .br-file{font-weight:600;margin:0 0 2px;color:var(--ink);font-size:13px}
.wtv [data-wt=replay-card] ul{margin:0 0 8px;padding-left:18px;color:var(--muted);font-size:12.5px}
.wtv [data-wt=replay-card] table{border-collapse:collapse;width:100%;font-size:12.5px}
.wtv [data-wt=replay-card] td,.wtv [data-wt=replay-card] th{padding:3px 4px;text-align:left;vertical-align:middle}
.wtv [data-wt=replay-card] th{color:var(--muted);font-weight:500;font-size:11.5px}
.wtv [data-wt=replay-card] input[type=number]{width:62px;font:inherit;font-size:12.5px;padding:2px 4px;border:1px solid var(--line);border-radius:5px;background:#fff;color:var(--ink);color-scheme:light}
.wtv [data-wt=replay-card] details{margin:8px 0;font-size:12.5px}
.wtv [data-wt=replay-card] summary{cursor:pointer;color:var(--ink)}
.wtv [data-wt=replay-card] details td:first-child{white-space:nowrap;padding-right:8px}
.wtv [data-wt=replay-card] details td{color:var(--muted)}
.wtv [data-wt=replay-card] .br-note{color:var(--muted);font-size:11.5px;margin:4px 0 0}
.wtv [data-wt=replay-card] button[data-wt=replay-go]{width:100%;margin-top:10px;padding:9px;font-weight:600;background:var(--accent);border-color:var(--accent);color:#fff;position:sticky;bottom:0;box-shadow:0 -6px 8px var(--panel)}
.wtv [data-wt=replay-card] button[data-wt=replay-skip-settings]{width:100%;margin-top:6px;border:none;background:none;color:var(--muted);text-decoration:underline;font-size:12.5px}
.wtv [data-wt=replay-steps]{list-style:none;margin:6px 0 8px;padding:0;font-size:13px}
.wtv [data-wt=replay-steps] li{display:flex;align-items:center;gap:8px;padding:3px 0;color:var(--muted)}
.wtv [data-wt=replay-steps] li i{flex:none;width:16px;height:16px;border-radius:50%;border:1.5px solid var(--line);display:inline-flex;align-items:center;justify-content:center;font-style:normal;font-size:10px;box-sizing:border-box}
.wtv [data-wt=replay-steps] li[data-state=now]{color:var(--ink);font-weight:600}
.wtv [data-wt=replay-steps] li[data-state=now] i{border-color:var(--accent);background:var(--accent)}
.wtv [data-wt=replay-steps] li[data-state=done]{color:var(--ink)}
.wtv [data-wt=replay-steps] li[data-state=done] i{border-color:var(--accent);color:var(--accent)}
.wtv [data-wt=replay-bar]{height:4px;background:var(--line);border-radius:2px;overflow:hidden;margin:4px 0 10px}
.wtv [data-wt=replay-bar] i{display:block;height:100%;width:0;background:var(--accent)}
.wtv [data-wt=replay-caption]{position:absolute;left:50%;bottom:22px;transform:translateX(-50%);width:min(680px,calc(100% - 24px));box-sizing:border-box;background:#1d2329e6;color:#fff;border-radius:10px;padding:10px 14px;font-size:13.5px;line-height:1.45;z-index:8;display:none;transition:opacity .25s}
.wtv [data-wt=replay-caption] b{color:#fff}
.wtv[data-replay] [data-wt=hint],.wtv[data-replay] [data-wt=panel]{display:none}
@container wtv (max-width: 700px){
.wtv [data-wt=replay-card]{width:auto;right:12px;max-height:46%}
.wtv [data-wt=replay-steps]{display:grid;grid-template-columns:1fr 1fr;column-gap:8px}
.wtv [data-wt=replay-steps] li{font-size:12px}
.wtv [data-wt=replay-caption]{bottom:12px;font-size:12.5px}
}
`;
