# Fix round after the tower test (28 Oct 2026)

The held-out test on L29 / L30 (27 Oct) scored 39 of 54 (72 %), below the 80 % gate (`../blind_run_L29_L30/README.md`). This
folder holds the record of what was changed in the detector because of it and how the change was checked. The figures that came out
(older four drawings 139 of 143, tower floors 54 of 54) are **development-set figures**: the tower floors were used to design the
fixes. A fifth drawing from another office is still needed.

| | |
|---|---|
| `merged_openings.diff`, `merged_geomkit.diff` | The whole change to `../openings.py` and `../geomkit.py` against the frozen code of 27 Oct (`../blind_run_L29_L30/frozen_code/`, sha1 of `openings.py` starts `730a29203309`) |
| `patches/cluster_*.diff` | The six fixes as first made, each in a private copy of the 27 Oct detector and against that code: `passages` (stub-to-stub gaps, stair halls, frames), `sliders` (leaves drawn as line pairs, pocket sliders), `screens` (1-2 cm glass screens), `facade` (curtain-wall fins and bays), `mouths` (a wall end facing the side of another wall is no passage), `glassdoors` (fixed glass beside a door) |
| `reviews/round2_*` | Round 2: two blind auditors judged 22 passages the mouth rule removes and 14 it keeps (anonymous, mixed; `removed_passages_secret_which_was_removed_or_kept.json` is the key to the candidates); two adversarial reviewers (the mouth rule, the sidelight rule) with their findings |
| `reviews/round3_*` | Round 3: three general reviewers of the merged detector: counterexamples (`round3_counterexamples.json`), code and performance (`round3_code_and_performance.json`), fuzzing (`round3_fuzzing.json`) |
| `reviews/round4_*` | Round 4: two fresh reviewers of everything changed after round 3 (the delta): a line-by-line code review (`round4_final_delta_code.json`: 8 findings, 2 of them regressions) and adversarial tests of the changed functions (`round4_final_delta_tests.json`: 7 findings, one of them a regression on a real door); all addressed |
| `reviews/audit_verdicts_on_the_extras.json` | The blind audit of the 49 tower extras (27 Oct) that told which detections were false |
| `tools/` | The regression harness (`run7_regression_harness.py`: runs the six drawings of a detector copy, scores them, compares with a baseline; `sweep_const.py` sweeps one constant; `cmp_ops.py` lists what differs between two outputs). They carry the paths of the scratch folders they were written in; `../run_all.py` is the version for this folder |

## What each reviewer finding led to

Accepted (all checked on the six drawings: older 139 of 143, tower 54 of 54, no door or window of the four older drawings changed in kind or by more than 1 mm):

- A doorway between two collinear wall ends of **different thickness**, centred on one axis, was dropped as a "mouth": judged on the
  axis now (`CENTRED_OUT`), but only for a gap that starts at a free wall end (round 4: the one real-data case, a stair wall's corner
  facing a column box, was a false passage).
- Limits that sat on common drawn sizes (a 0.20 m cross wall, a 0.45 m run, 1.40 m, 0.10 m overlaps, 0.25 m jamb returns, 0.6 / 1.6 m gaps)
  decided by floating-point noise; they were moved to the middle of their measured range (`CROSS_PIECE` 0.225, `WALL_RUN` 0.6,
  `DOORWAY` 1.45, `FACE_TOL` 0.035, `RUNS_ON` 0.7, `JAMB_RETURN` 0.275, `SIDELIGHT_MIN` 0.17) and every comparison carries 0.5 mm (`EPS`).
  The ranges quoted in the comments were re-measured with the shipped code in round 4 (for example `CROSS_PIECE` 0.11-0.24, `WALL_RUN`
  0.26-0.90, `RUNS_ON` 0.2-1.1, `FACE_TOL` 0.03-0.045, `JAMB_RETURN` 0.21-0.33, `DOORWAY` 1.31-1.55).
- A wall band behind a door symbol is a wall up to 0.6 m (inclusive, like its four twins) **and only if nothing of the wall goes on beyond
  the 0.6 m section window**: a thicker wall or a core block is cut short by the window, and its "band" is the window. The tower's two
  shaft doors stand on the face of such a block (the mass behind them is 1 m or more): they were read on their chord on one floor and 0.3 m
  behind it, with a 0.6 m "wall", on the other, by a tenth of a millimetre of rounding. Both are read on their chord now, where the key has
  them. Round 4 caught two earlier attempts: a strict "under 0.6 m" lost the wall of every door symbol on a wall of exactly 0.6 m, and an
  inclusive limit with 0.5 mm of tolerance moved the L29 shaft door 0.30 m off the chord (the clipped window passed as a band). The
  search ray for wall material along a chord that is on a wall face now runs 1 mm into the wall side, so that the face is not grazed
  (one Sukhumvit door end moved by 1 mm; the shaft door no longer flips under nanometre noise).
- Curtain-wall test: glass of a glass-role layer that ran 0.2 m past a wall end dropped a real window; the limit is 0.7 m (the gaps the
  test removes on the six floors have glass running on by 0.98 m or more, and no window gap on them has glass running on by more than
  0.2 m). The test that glass beside an uncut wall is no bay applies to glass-only bands.
- **Free-standing thin piers** read as a row of passages: both stubs must belong to a wall of 0.8 m or more (measured on its minimum rotated
  rectangle, with 0.5 mm of tolerance, so that it does not depend on how the drawing is turned); a free post is judged on its minimum
  rotated rectangle too, with the tolerance on its 0.9 m and 1:2 limits (round 4: a 0.2 x 0.4 m or 0.3 x 0.6 m pier was a post or not
  depending on where the sheet sat and made false passages in rows of piers), and a piece wider than its diagonal limit is skipped
  before the rectangle is computed.
- **Double doors** fell apart into two single doors when their arcs came in the other order in the file (score depended on item order): both
  orders are tried.
- **Unit scale** was applied after the de-duplication (which rounds to 1 mm only in mm): a drawing in metres lost its walls. Scaling
  now comes first.
- **Crashes**: a small self-crossing outline (a MultiPolygon without `.exterior` in `jamb_at`: `small_shapes` now splits it; a first
  version kept only the largest piece in `geomkit.Prim`, which lost a wall piece of a self-touching outline, round 4 reverted it) and a failed
  union of near-degenerate wall pieces.
- Sidelights: the dropped glass is recorded (`sidelights`, and in the evidence, with the layers whose lines cover part of it); a door
  trimmed to under 0.5 m, or with its leaf outside its gap, is not trimmed; the limit is off the drawn size 0.15 m; the 0.5 m guard, the
  half-covered share and the layer list carry the tolerance, and so do the 0.45 / 1.6 m (single) and 0.3 / 1.3 m (double) leaf radius limits
  of door symbols (a leaf of exactly 0.45 m was found in 26 of 40 sheet positions).
- Speed: strip search with a numpy pre-filter (4 times faster on 800 thin screens; same gaps).
- **Rounding ties found by the fuzzing reviewer** (limits that equal a drawn size decided results by the last bit of a float, so that the
  same drawing gave other results when moved, rotated or touched by a nanometre): wall strips must be thinner than 0.55 m (a 0.55 m
  pier beside the bank's double door read it as 2.42 m instead of 1.60 m in some orientations; thin screens are strips under 3 cm
  + 0.5 mm, walls start there, so no thickness falls between the two); an arc's open tip within 0.05 m of a wall counts as on it
  (+0.5 mm; a Sukhumvit door was lost to a window); the 0.1 m overlap of leaf lines with a gap (+0.5 mm; L30's cavity slider was a
  passage on one sheet position and a door on another); leaf lines are level within 1 cm instead of 5 mm (the 4.8 m slider was lost
  in 4 of 4 runs with 3 mm of noise on the vertices, and is found in all eight with 1 cm); the 0.6 / 1.6 / 2.75 / 3.6 m gap limits of
  `passage_ok`; the arc centre is worked out relative to its first point. Effect on the six drawings: the L30 shaft door is read on its chord as
  the L29 one (0.05 m instead of 0.25 m from the key) and one Sukhumvit door end moves by 1 mm; on noise: 1 nm to 1 micrometre of jitter on every vertex changed 32-41 openings in ten runs before and 8 after.
- A failed union of wall pieces falls back to a grid-snapped union: the same openings to within 5 mm, but ids can be numbered in another
  order (round 4 measured it; the first wording said "the same result").
- Documentation: the docstring says what the code does where it differed (the flush-corner clause looks at the far end only; a thin
  screen is a closed outline or hatch, not two separate lines; the output record's `sidelights`; glass-only for the uncut-wall test).

Found by the fuzzing reviewer and left as they are (each is listed in `../README.md`, "Limits worth knowing"): the gap direction
is taken from one short wall-end face (noise is amplified 7-25 times), the 3 cm strip floor sits 5 mm under two reveals, leaves and glass
are read from single line segments (a line cut in two is not read), the facade-glass test needs one long band, `far_face` looks along one
ray, and constants that rest on one or two drawings (`DOORWAY`, `JAMB_RETURN`, `SIDELIGHT_MIN`).

Kept as they are, written down in `../README.md` ("Limits worth knowing"): the cliff in the passage rule at a cross wall thicker than 0.225 m; walls
more than 2 degrees off the line; flush-cornered gaps wider than 1.45 m; ribbon windows drawn as one glass line through piers (read as
a curtain wall); glass-role windows (map window layers as `window`); sidelights only on window and glass layers; the 2 m limit on a
leaf beside a thin screen; the answer-key convention for doors with fixed glass (leaf, not wall end to wall end).

## How to run the check

From `..`: `OPENINGS_DATA=<folder with a prims.pkl per drawing> python -B run_all.py last_run --png`, which prints the scores of the four
older drawings (key `keys/final/all.json`) and the tower floors (key `keys/tower/tower_audited.json`) and the detections no key lists.
Expected on 28 Oct 2026: older 139 of 143 (8 not in the key), tower 54 of 54 (6 not in the key).
