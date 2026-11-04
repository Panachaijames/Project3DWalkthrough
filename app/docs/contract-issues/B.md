# Contract issues: builder B (viewer modes), 3 Nov 2026

Written only by builder B. The integration step settles each with the architect (DESIGN.md 18.0). None of them blocked B:
each is handled inside B's own files, as said. B-1 to B-3 are about the ported browser checks (test plan), B-4 to B-8
about the port itself (information: where the port is not literally the prototype, and why), B-9 about a scaffold doc.

## B-1. D-17.4's "40 random slides (>= 90 %)" does not hold for the hotel and the suite with the prototype's own walking

test_viewers.mjs asked it of the house only (36 of 40 at least). D-17.4 extends it to the bank, the suite and the hotel.
Measured on 3 Nov with the same spot rule (40 spots near a wall on the first floor, walk at the nearest wall, then try
+-40 degrees for 1 m; a slide counts above 0.3 m) and the same spots: on the prototype pages (`E2E_TARGET=prototype`, the
`slides` annotation of the report) the house 37 of 40, the bank 36, the suite **35**, the hotel's floor 1 **30**; in Node
with the port on the fixture models (makeTestContext) exactly the same numbers (and the hotel's floor 2: 38). The failures
are inside corners of small rooms: the nearest wall seen at chest height lies diagonally into a corner, so after walking
into it both slide directions run into the other wall at once (in the diagnostics the blocking wall's normal is at right
angles to the one walked into, the slide after it 0 - 1 cm). That is the prototype's walking, not a port defect (the port
is behaviour for behaviour; the unit tests pin the rays, the slide and the floor-edge rule).
**Handled in `tests/e2e/modes.spec.ts`:** the house keeps its own test's box (-22 .. 22 x -14 .. 14 m) and 90 %; the others
draw their spots over the floor plates (`walkables`, the same spots on every target: the group's box also held the
hidden furniture boxes, which differ between the pages and the app) and ask the share the prototype reaches: bank 90 %,
suite 85 %, hotel 70 %. **Suggestion:** D-17.4 reads "40 random slides (>= 90 % on the house and the bank; the suite and the
hotel at least the prototype's 35 and 30 of 40)", or the check leaves out spots that end in an inside corner.

## B-2. "Walk stops at a wall and does not pass through": the prototype judged the straight line from the start to the end

test_viewers.mjs checks `!probe.crosses(start, end)` after holding W at the nearest wall. When that wall ends close by
(a wall end, a column), you slide along it, walk round its end and stop at another wall; the straight line from the start
to the end then cuts the first wall's corner although you never went through it (seen on the bank, 3 Nov, at 7.5 fps:
slid 0.6 m along a wall, then 4.5 m on to the next one). **Handled** in `modes.spec.ts` and the harness spec: the position
is sampled every 200 - 250 ms while the key is held and every leg of that path is checked with `probe.crosses` (a tunnel
through a wall still shows in the leg where it happens). The same for the 40-degree slide.

## B-3. Fixed-time key holds measure the frame rate, not the viewer

The modes cap a frame's time step at 0.05 s (D-13), so below 20 fps a held key moves you less per second: at 5 - 8 fps
(seen on 3 Nov with six builders on the laptop) Ghost flew 3.6 m in 1.5 s at the suite's wall 4.04 m away, a 700 ms
Space hold rose 0 m once (a frame longer than the hold: key down and up both landed before the next frame), and a 1.2 s
slide at 40 degrees along a bank wall went 0.20 m where the probe slides 0.43 m. **Handled:** the checks of what a key
does (W walks, the slide, Ghost flies through the wall, Space rises, C sinks, the stick and Up move you) hold the key until
it has done it, at most a few seconds; the speeds themselves (1.5 / 3.4 m/s, 6 m/s x 3, the dt cap) are checked exactly
in the unit tests (`test/unit/modes/modes-dom.test.ts`, tick). The checks stay inside `timedDescribe`.

## B-4. Leaving Orbit while the modes are locked (information)

viewer_modes.js's setMode did not look at the lock: nothing could call it during the replay (the panel with the mode
buttons is hidden, the keys, the wheel and the double-click check the lock, and any `mode` key in the address makes the
replay skip its settings screen, so applyUrl never ran locked). The app has new callers: the public `Viewer.setMode`, and
a host passing `options.build: 'settings' | 'play'` together with an address `mode`. Entering Walk or Ghost under the
Build settings card would leave them running beneath the replay. So, matching the contract's "lock: ... Orbit only":
`setMode` refuses Walk and Ghost while locked (Orbit is always allowed), and `applyAddress` leaves the mode, floor, point
and direction alone while locked; everything else of the address is applied as applyUrl does (`cam=1` sets `camWanted`).
No prototype flow changes.

## B-5. setMode blurs only the viewer's own focused control (information)

viewer_modes.js blurred `document.activeElement`, whatever it was, when Walk or Ghost started. The port blurs it only when
it is inside the viewer's root, so the host's focused control keeps its focus (and, by D-11.5 / 18.15, its keys). Clicking
the canvas still hands the keys back to the viewer (the browser moves focus to the body).

## B-6. `ctx.size()` never returns 0 in A's context (information)

takePhoto returns null when the root has no size, as the prototype did with `canvas.clientWidth` 0. A's `size()` returns
the last non-zero size when the root is hidden, so on a hidden viewer a photo is drawn at that size instead of null.
Harmless; noted because the contract says only "Root size in CSS px".

## B-7. Two "no download" flags (information)

`ResolvedOptions.noDownload` (A, from the address) and `ModesState.noDownload` (set by `applyAddress`, as the prototype's
`s.noDownload`) are both honoured: a photo is downloaded only when neither is set. A thumbnail's "click to save again"
downloads in any case, as on the prototype pages. Every photo emits the public `photo` event after its thumbnail.

## B-8. Client rectangles where events carry client coordinates (information)

D-11.5 makes screen maths root-relative (`ctx.size()`, `ctx.rectOf()`): the frame rectangle, the Camera and side panels,
the crowded rule and `narrow()` use them. The double-click (event -> normalised device coordinates over the canvas) and the
touch stick (event -> knob offset) keep `getBoundingClientRect()`, because the event's `clientX / clientY` are client
coordinates too; mixing the two frames would be wrong below the staff app's bar.

## B-9. app/CLAUDE.md's Playwright command with a spec path fails as written (scaffold's doc)

`npx playwright test -c tests/e2e/playwright.config.ts --project e2e tests/e2e/modes.spec.ts` stops at once with
`Project(s) "tests/e2e/modes.spec.ts" not found`: in Playwright 1.64.1 `--project` takes several values, so the path is
read as a second project name. `--project=e2e tests/e2e/modes.spec.ts` (and `--project=harness
packages/viewer/test/harness/modes`) work, and the config's own `projectArgs()` reads that form too. Suggestion: the
`=` form in CLAUDE.md, WORK_BREAKDOWN and the spec headers (B's headers use it).
