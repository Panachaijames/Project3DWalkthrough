# Answer key of `presidential suite_layout.dwg` (cache `suite_revit`): held-out test, step 4 of 7

`suite_revit.json` is the answer key of the fifth drawing of the openings detector's held-out test: a Revit export of a
hotel presidential suite made by the company's 3D team on 9 Nov 2026, one plan per file. It was made from the drawing and
three independent lists only, without any detector output, in the format of `../tower/tower.json`, for
`../../tools/score.py`. Every entry carries the floor tag **`suite_revit`** (see "Floor tag" below). Coordinates are
drawing metres (DXF millimetres / 1000).

## Counts

| | door | passage | window | total |
|---|---|---|---|---|
| **Scored** | **15** | **1** | 0 | **16** |
| Optional (not counted either way) | 6 | 2 | 18 | 26 |
| All entries | 21 | 3 | 18 | 42 |

- **Scored doors (15):** 11 of the suite (4 pocket sliders of 1.10 m, 1 bi-fold of 2.225 m, 5 hinged singles of
  0.75-1.00 m, the 1.80 m double entrance door) and 4 corridor doors outside the suite (riser doors D22 and D06, two unit
  doors D01 of the neighbouring units).
- **Scored passage (1):** SR-08, the 1.975 m doorless opening with a dashed head between the foyer and the living and
  dining area.
- **Optional (26):** the two riser double doors cut by the view crop (SR-17, SR-18), the four glass doors of the bathroom
  glass screens (SR-19 WC compartment, SR-20 / SR-21 master shower, SR-22 room east of the BOH), two open sides of rooms
  (SR-23 dressing area, SR-24 lobby of bedroom 2) and the 18 fixed curtain-wall facets of the six bays (SR-25 to SR-42).
- **No scored window**: the drawing has no window family and no window layer; all its facade glazing is fixed curtain
  wall, as on the tower floors.

The scored openings (widths wall end to wall end, frames inside the opening included):

| Id | Kind | Width | Where | What |
|---|---|---|---|---|
| SR-01 | door | 1.10 | x 7.454, y 2.234-3.334 | pocket slider, master bedroom / dressing area |
| SR-02 | door | 1.10 | x 7.454, y 10.284-11.384 | pocket slider, master bedroom / master bathroom |
| SR-03 | door | 2.225 | x 9.462, y 0.959-3.184 | bi-fold, dressing area / walk-in wardrobe |
| SR-04 | door | 1.10 | y 5.156, x 8.129-9.229 | pocket slider, bedroom foyer / master bathroom |
| SR-05 | door | 1.00 | x 11.562, y 3.697-4.698 | hinged, foyer / bedroom foyer |
| SR-06 | door | 0.75 | y 3.259, x 11.712-12.462 | hinged, foyer / small room south of it |
| SR-07 | door | 1.80 | y 3.259, x 13.287-15.087 | double, corridor / foyer (suite entrance) |
| SR-08 | passage | 1.975 | y 5.136, x 13.137-15.112 | doorless with a dashed head, foyer / living and dining |
| SR-09 | door | 0.80 | y 3.359, x 20.712-21.512 | hinged, corridor / BOH |
| SR-10 | door | 0.80 | x 20.512, y 4.409-5.209 | hinged, bar / BOH |
| SR-11 | door | 1.10 | x 20.512, y 6.084-7.184 | pocket slider, dining / lobby of bedroom 2 |
| SR-12 | door | 0.80 | x 22.812, y 6.034-6.834 | hinged, lobby of bedroom 2 / room east of the BOH |
| SR-13 | door | 1.80 | y 3.259, x 15.237-17.037 | double service door D22, corridor / riser |
| SR-14 | door | 0.85 | y 1.159, x 16.187-17.037 | single service door D06, corridor / riser |
| SR-15 | door | 1.00 | y 0.859, x 19.177-20.177 | unit door D01, corridor alcove / neighbouring unit |
| SR-16 | door | 1.00 | y 0.859, x 20.847-21.847 | unit door D01, corridor alcove / neighbouring unit |

`disputes/work/key_marked.png` shows every entry of the key on the plan (scored solid, optional dashed, rejected places
as crosses).

## How the key was made

1. **Inputs** (made in steps 2 and 3, read here and not changed): `description.md`, `drawing.json`, `pictures/`, and three
   lists in `labels/`, each made without the others and without any detector output:
   - **A**, geometry first (wall gaps from the fills, then what fills them): 42 entries;
   - **B**, pictures first, then measured from the geometry: 42 entries;
   - **C**, a geometry-only inventory made without opening any picture: 44 entries, a list in the format of
     `../tower/labels/inventory-l29.json` (its first element is a header).
2. **Comparison with the scorer's matching**, the tower key's tool run as it is (from `detector/`):

       python -B tools/three_way.py suite_revit keys/suite_revit/disputes/suite_revit.json keys/suite_revit/labels/A.json keys/suite_revit/labels/B.json --inv keys/suite_revit/labels/C.json --floor suite_revit --box 1.569,0.008,25.079,13.084

   with A and B as the two labellers and C as the inventory (the box is the plan's extent from `drawing.json`):
   **41 accepted, 3 disputes** (`disputes/suite_revit.json`, named after the part as in `../tower/disputes/`).
   `three_way.py` compares kinds and A's ends with B's only. This step also counts as a dispute a different optional
   flag, subtype or width beyond tolerance between any two lists, so `disputes/compare_full.py` clusters the same way
   (`score.py`'s `match`, pairwise, joined transitively) and checks every place across all three lists:
   **44 places, 40 agreed, 4 disputes** (`disputes/comparison_full.json`). The fourth dispute is an optional flag, which
   `three_way.py` does not compare. No subtype differs: the lists name the same door types in other words (the one
   detail that differs, SR-06's leaf 0.665 m in B and 0.70 m in A and C, changes neither the type nor the ends).
3. **Disputes decided from the drawing, not by majority** (next section): queries of the drawing cache
   (`disputes/work/q.py`), new close-ups (`disputes/work/d*.png`, `ends_*.png`, drawn with `scripts/zoom.py`), the
   description and pictures, and the conventions of the earlier keys.
4. **The key.** `disputes/build_key.py` writes `parts/suite_revit.json` (the adjudicated part: openings, glass walls,
   uncertain points, rejected places, method, as `../tower/parts/*.json`) and `spec.json` (one part covering the whole
   plan, box = the extent in `drawing.json`, floor `suite_revit`), then runs `tools/combine_keys.py spec.json
   suite_revit.json` as it is. Agreed openings stand as agreed: each keeps labeller A's record, as `three_way.py` takes it,
   with the key id **SR-nn = A-nn** and the three lists' ids in `lists`; `agreement` is `all three` or `decided`, and
   `decision` says what was settled and why. Nothing was added that no list has, and no agreed opening was judged again.
5. **Self-check** with `tools/score.py`: the key read as a detection file scores 16 of 16 with 26 of 26 optional found;
   lists A and B read the same way score 16 of 16 with no extra; list C 16 of 16 with 2 extras (the two rejected alcove
   mouths).

## The four disputes and how they were decided

**1. SR-19, the glass door of the WC compartment in the master bathroom (A-19 / SRB-05 / C-24): optional or scored.**
A and B listed it optional, C scored it; all three have the same kind and ends ((9.5166, 5.3507)-(9.5166, 6.0507),
0.70 m). **Decided optional.** The door stands in the bathroom's glass screen, not in a wall: 10 mm glass on layer 0
(lines x 9.5116 / 9.5216) between two 0.10 m layer-0 kerb lines (x 9.4666 / 9.5666) that run on unbroken past it; the
glass stops at y 5.3507 and restarts at y 6.0507. It is drawn exactly like the two shower doors further along the same
screen (SR-20, SR-21): a 10 mm glass leaf open 30 degrees, a dashed 30-degree swing on `A-DOOR-HDLN`, a handle outline on
`A-GENM-HDLN`, no door frame (every hinged and pocket door in a wall has 4 to 18 `A-DOOR-FRAM` lines; only the bi-fold
and the four glass-screen doors have none); and it is one of the four exploded copies of the same unused shower-door family
`IN_SHOWER DOOR1 - Shower door_700X2160MM`. The compartment behind it (x 9.57-11.49, y 5.25-6.94) holds only the WC: an
enclosure inside the master bathroom. The earlier keys treat a shower screen as a glass wall whose door belongs to the
enclosure (Sukhumvit, shared definition of 26 Oct) and toilet cubicle doors as optional (tower), and the three lists agree
that the screens' other three doors are optional, so this one is optional too. Close-ups:
`disputes/work/d1_wc_glass_door.png`, `d1_master_bath.png`.

**2 and 3. C-40 and C-43, the two mouths of the corridor alcove (listed by C only, as optional passages; A and B rejected
them).** **Decided: not openings** (in the key's `rejected`). The corridor's south wall (`A-WALL`, y 1.109-1.209) turns
south at x 18.987 and resumes only at the column x 20.262-20.762 (its north face flush with the wall), and again from the
column to x 21.937: two recesses of 1.175 m by 0.30 m, each with a unit door at its back (SR-15, SR-16, both scored).
Nothing is drawn across either mouth on any layer (a query of every cache item in x 19.10-20.25 and x 20.77-21.93,
y 0.95-1.22 finds none: no head, threshold, frame or leaf). A recess is the corridor's space in front of its door and the
opening is the door at its back, the call the older keys made for the same case (presidential R5: the mouth of the alcove
in front of D4, "D4 at the back of the alcove is the opening"; Sukhumvit g-west R-02). C's own note calls each "the mouth
of a recess in front of a door, not an opening of its own". Close-up: `disputes/work/d23_corridor_alcove.png`.

**4. SR-24, the open side of the lobby of bedroom 2 (A-24 / SRB-24 / C-20): ends 0.070 m apart.** Same kind, same x ends,
optional in all three; A put it on y 6.9941, B and C on y 6.9241. **Decided y 6.9241.** The wall whose end bounds the
mouth is the layer-0 fill 51FC, x 22.7366-24.7866, y 6.8541-6.9941 (0.14 m with its linings): its centre line is y 6.9241,
and A's line is its north face. The convention, A's own included, puts a/b on the wall centre line. Ends x 20.6116 (the
face of the partition that holds the pocket door SR-11 at this height) and x 22.7366, 2.125 m. Close-up:
`disputes/work/d4_lobby_open_side.png`.

## Agreed openings: ends where the lists differ within tolerance

32 of the 40 agreed openings have the same ends in all three lists. For the other 8 the key takes the ends that two lists
share and the drawing supports:

- **The six middle facets of the bays** (SR-26, SR-29, SR-32, SR-35, SR-38, SR-41; 0.05 m, the 5 cm limit of agreement):
  B and C (identical) end the facet where its pane and mullion lines end, at the faces of the corner wedges (`A-WALL`,
  block `Walls 13`); A ran 0.05 m past each end into the wedges (3.617 / 1.517 m instead of 3.517 / 1.417 m). The key
  takes B and C: the faces of the bounding wall material, as all three lists have for the first and third facet of every
  bay (`disputes/work/ends_*.png`).
- **SR-05** (0.6 mm): A and C, the fill 51B3 that starts at y 4.6980; B took the drawn end line at y 4.6974.
- **SR-20** (0.1 mm): B and C, the glass end line at y 7.8655; A took y 7.8654.

## Conventions (those of the earlier keys, which all three lists also state)

- a and b on the wall centre line at the faces of the wall ends that bound the opening, the 50 mm door frames inside the
  opening included (wall end to wall end); a door at a corner ends at the face of the cross wall.
- A door in a glass screen is measured by its leaf (the gap in the glass); the fixed glass beside it is a glass wall.
- Optional: passage mouths into open space (a wall end facing a cross wall), doors cut by the view crop (their second jamb
  is not in the drawing), doors of shower and WC glass screens, fixed curtain-wall facets.
- Doors outside the suite that stand in walls of the drawing (corridor risers, the neighbouring units) are scored, like
  the tower key's shaft doors.
- Not openings: recesses in front of a door, niches, cabinet recesses, casework and wardrobe fronts, open plan, the
  corridor's own jogs, walls cut by the crop.

## Uncertain points (also in the key's `uncertain`)

- **SR-19** is optional by the decision above. If the 3D team wants doors in glass screens scored whatever the room, set
  `optional` to false on SR-19 to SR-22 (their ends need no change): 20 scored openings.
- **Doors outside the suite** (SR-13 to SR-16) are scored. If the key is meant to cover the suite only, they become
  optional: 12 scored openings.
- **SR-17 / SR-18** keep the nominal 1.80 m of their type and hinges; only 1.092 m of each is drawn before the crop.
- **SR-03**, the bi-fold of the walk-in wardrobe, is scored as a room door; if walk-in wardrobes count as casework it
  would be optional.
- **Curtain-wall bays** are listed per straight facet as optional windows. Other readings: one window per bay, or glass
  wall only (the tower key). None is scored either way.
- **Width at the scorer's limit.** The doors are measured wall end to wall end with the 50 mm frames inside the opening;
  the clear width between the frames is 0.10 m less (0.05 m for SR-06). For the 0.80 m and 1.00 m doors (SR-05, SR-09,
  SR-10, SR-12, SR-15, SR-16) that difference is exactly the scorer's width tolerance (max(0.10 m, 10 %)), so a detection
  measured between the frames passes or fails there on rounding.
- **The rejected alcove mouths.** A passage detected at a mouth counts as an extra. If the unit door behind it is not
  detected, the scorer pairs the door with that passage (centres exactly 0.30 m apart, its centre limit) and fails it on
  width (1.175 against 1.00).
- **SR-23 / SR-24**, the open sides, could also be read as no opening at all; they are optional.
- **SR-06** is 0.75 m between the wall fills, but its east frame stands 0.05 m inside the wall stub (leaf 0.70).

## Floor tag

`tools/prims.py` tags every item of a drawing it has no special case for with the cache name, so all 29,886 items of
this cache carry the area `suite_revit` (`drawing.json`). `openings.py` (`run()`) reads the items of each area named in
the mapping's `"floors"` and writes each opening's `floor` as the name the mapping gives that area (`{area: floor name}`;
ids `<last part of that name>-nnn`). The key carries `suite_revit`, the floor tag of `drawing.json`, so `score.py`
(which pairs per floor string) matches an output made with `"floors": {"suite_revit": "suite_revit"}`. This step did not
read the held-out run's mapping (it lies in `../../blind_run_suite_revit/`): if that mapping names the floor otherwise
(for example `suite_revit:suite`), rename the floor in the key, or in the output, before scoring, or every key opening
counts as missed.

## Independence

No detector output of this drawing, no mapping of it and nothing in `../../blind_run_suite_revit/` was opened. Once, a
content search for the word "shower" over `detector/` (looking for how the earlier keys treated shower doors) also listed
two file names inside that folder among its 51 matches; their contents were not shown or read.

## Files

| | |
|---|---|
| `suite_revit.json` | **The answer key**: 42 openings (16 scored, 26 optional), glass walls, uncertain points, rejected places; made by `tools/combine_keys.py` from `spec.json` |
| `spec.json` | One part covering the whole plan (box = the extent in `drawing.json`), floor `suite_revit` |
| `parts/suite_revit.json` | The adjudicated part with the method note (input of `combine_keys.py`) |
| `disputes/suite_revit.json` | What `tools/three_way.py` found: 41 accepted openings (A's records) and 3 disputes with every list's version |
| `disputes/comparison_full.json`, `compare_full.py` | Every place across the three lists with its checks (presence, kind, optional flag, ends, width): 40 agreed, 4 disputes |
| `disputes/build_key.py` | Builds `parts/suite_revit.json`, `spec.json` and the key from the lists and the decisions, and runs the self-check |
| `disputes/work/q.py` | Lists every cache item in a box (used for the measurements above); needs `OPENINGS_DATA` = the WORK folder of `drawing.json` |
| `disputes/work/d1_*.png`, `d23_*.png`, `d4_*.png`, `ends_*.png` | Close-ups of the disputes and of the bay facet ends (`scripts/zoom.py`) |
| `disputes/work/key_marked.png`, `mark_key.py` | The key drawn on the plan |
| `labels/` | The three lists (A, B, C) and their labellers' scripts and pictures, as made in step 3 |
| `description.md`, `drawing.json`, `pictures/`, `scripts/` | The drawing's description, facts, pictures and scripts from step 2 |

To rebuild (Git Bash, from `detector/`, `WORK` as in `drawing.json`): run the `three_way.py` command above, then
`python -B keys/suite_revit/disputes/compare_full.py`, then `python -B keys/suite_revit/disputes/build_key.py`
(`OPENINGS_DATA=$WORK` is needed only for `q.py` and `mark_key.py`).
