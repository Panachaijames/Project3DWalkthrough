# Furniture proxy boxes (shared by the bank, the house and the presidential suite)

Started 28 Oct 2026 after the 3D team ran the bank-branch 3ds Max script (structure good, furniture left).
Owner's decisions (28 Oct): **one coloured box per furniture piece, colour = kind; boxes block you in Walk mode and not in Ghost mode;
every colour (kind) has a text box for its height in mm** (examples given: coffee table 450, kitchen table 750, counter top 850,
bar table 1000).  This file is the contract the builders, the viewer module and the 3ds Max module are all written to.

## What a proxy is

One oriented rectangle per piece (the minimum rotated rectangle of the piece's drawn geometry), stood up to the kind's height.
It is a placeholder: the 3D team replaces it with their own model by family name (the family list says which).  Round or L-shaped
pieces get the rectangle around them, and a block that draws a door-swing arc gets a box that includes the swing: boxes are what is
drawn, not the nominal size.  Nothing in the code names a drawing, a handle, a coordinate or a product: only fixed vocabularies of
words and physical sizes in metres.  A piece's kind is decided in this order:

1. a name on the skip list (built-in skip words such as outlet, cover, mullion, and the project file's `furniture.skip`): not furniture;
2. the office's own words, the project file's `furniture.words` (`{kind: [words]}`, plain text matched as whole words, any case):
   they win over the vocabulary (this is where a staff member says that 'Fritz-Hansen' means seat, or that the cryptic block
   'jdlkasdjkla' of the presidential suite is a tree).  The kit matches them against the name as it reads it, with CamelCase split
   ('TF2092P' reads 'TF2092 P'), so a word must be written that way (open item: also try the name as written);
3. the built-in vocabulary of `furniture_kit.py`, applied to the block's family name (ordered rules, first match wins);
4. the layer name's words (sanitary, plant, casework), only when the name says nothing;
5. otherwise `other`.

**Reading the drawing** is each builder's job; the kit only takes points and names.  A piece is a block insert on a furniture
layer, at any depth (a linked model can hold real fittings): the bank gives layers the `furniture` role in `bank_project.json`;
the presidential suite and the house list them in their own `src/furniture.json` (`layers`, `looseLayers`, `heights`, `bases`,
`words`, `skip`, `minSize`, the house also `minDepth`; keys that start with `_` are notes).  A reader that does not keep an
insert's own layer (the suite's `read_dxf.py`) puts a block on the layer most of its drawing is on.  For a block bound from an
xref (`Xr_SDC_DD_ID-PRS-Fur$0$dining chair RS01`, `XR_L44$0$FRIDGE-600`) the family is the text after the last `$0$`, the layer
stays as it is, and a piece nested in another block notes `inside block <outermost block>`.  Loose shapes (not in a block) on a
furniture layer that touch within 1 cm form a cluster, a box when its hull fills 70 % of its rectangle; its family reads
`loose shapes on <layer>` and its kind comes from the layer words or `other`.  Rules the house builder adds for its drawing (not
the contract): a block whose name says nothing that holds two or more known floor-standing blocks is a room's worth (the kitchen):
its parts are the pieces and its own loose lines are dropped; dashed loose shapes are hidden lines, not pieces; a cluster made only of
closed outlines must fill 70 % by the outlines' area as well (a U of three wardrobes passes the hull test at 99 % and fills 36 %);
and `minDepth` drops pieces thinner than a piece of furniture can be.

## Kinds table (order = legend order; heights in mm are office defaults, editable per kind)

| key | label | colour | height | base | onTop | support | blocks |
|---|---|---|---|---|---|---|---|
| atm | ATM / kiosk | #c0392b | 1500 | 0 | no | no | yes |
| computer | Computer / monitor | #7b3fb5 | 450 | 0 | yes | no | yes |
| printer | Printer / copier | #8e8e8e | 300 | 0 | yes | no | yes |
| phone | Telephone | #d1306a | 150 | 0 | yes | no | yes |
| tv | TV / wall screen | #34408f | 600 | 900 | no | no | yes |
| partition | Privacy screen / panel | #4fb99f | 1200 | 0 | no | no | yes |
| curtain | Curtain | #c9a0dc | 2400 | 0 | no | no | **no** |
| lamp | Lamp | #ffd23f | 500 | 0 | yes | no | yes |
| plant | Plant | #2e9e4f | 600 | 0 | yes | no | yes |
| sanitary | Sanitary fitting | #17a2a2 | 850 | 0 | no | no | yes |
| appliance | Appliance | #b8860b | 900 | 0 | no | no | yes |
| bed | Bed | #e377c2 | 500 | 0 | no | no | yes |
| seat | Chair / stool | #e07b00 | 450 | 0 | no | no | yes |
| sofa | Sofa / armchair | #ffb347 | 800 | 0 | no | no | yes |
| seat-back | Seat back | #fa8072 | 800 | 0 | no | no | yes |
| table | Table / desk | #8a5a2b | 750 | 0 | no | **yes** | yes |
| coffee-table | Coffee / side table | #c9a37a | 450 | 0 | no | **yes** | yes |
| bar-table | Bar table | #5a3a1a | 1000 | 0 | no | **yes** | yes |
| counter | Counter top | #a0522d | 850 | 0 | no | **yes** | yes |
| cabinet | Cabinet / casework | #2f7fc1 | 900 | 0 | no | **yes** | yes |
| tall-cabinet | Tall cabinet / wardrobe | #1b4f8a | 2100 | 0 | no | no | yes |
| other | Other furniture | #6b6b6b | 750 | 0 | no | no | yes |

* **height**: what the text box starts with (mm; the viewer's text box takes 10 - 5000, and so does the Max spinner).  Whole mm, a half
  rounds up everywhere (the kit, the viewer, the CSV and the Max spinner: 460.5 -> 461).  **base**: height of the underside above the
  floor (mm; the wall TV hangs at 900).  A model lists only the kinds that occur: 'other' is absent when nothing falls into it.
* **onTop** kinds sit on a support (a `support` kind: tables, counters and cabinets).  A piece's support is the NEAREST support box
  that holds its centre or lies within 0.10 m of it (a printer on a counter's overhang): nearest = the smallest distance from the
  piece's centre to the support's rectangle (0 when the centre is inside it); a tie goes to the support with the smaller area, then to
  the lower id.  A tall cabinet is not a support.  A piece with `on` set stands at its support's top (`z0 = support's base + support's
  current height`), otherwise at its kind's base, so when the table height is edited the computer on it moves with it, and it may stand
  up to 0.10 m outside its support's drawn box.  Supports never sit on anything (no chains).
* **seat-back**: a seat's back drawn as a piece of its own (a round sofa's back cushions, drawn as bars along its rim) stands on the
  floor at the seat's rim, 800 mm high, and the seat under it is a `seat` (450), because a kind's height is shared: an 800 mm `sofa`
  box would hide its own backs.
* **blocks**: whether Walk stops you at it (the viewer shows it as a tick box next to the height; curtains default to not blocking).
  Ghost never blocks, for any kind (Ghost ignores every collider, walls included).  A box lower than Walk's knee ray (0.35 m)
  does not stop you (you can step over it).  A box is single-sided for Walk: a player whose knee or chest ray starts inside a box (entered
  Walk by double-clicking on it, a start spot that falls in one, or a tick switched on under them) meets none of its faces and walks out
  of it, except in a pocket of overlapping boxes where only other boxes hold them (5 of the bank's 172 blocking boxes; Exit, 1 and 3 leave
  Walk).  The shared `viewer_modes.js` is not changed for this.
* **doorways stay clear**: a box with a non-empty `approach` (below) does not stop Walk while the viewer's tick 'Keep doorways clear'
  is on (the default); it stays drawn, and its hover label says 'does not stop you: in the approach of <ids>'.  With the tick off, every
  box that blocks stops you.  The tick is shown only when at least one piece has an approach; it is remembered next to the typed heights
  (same storage key, only when off, as `"keepDoorways": false`); 'Reset heights' leaves it as it is.

## Model JSON (written by each builder, read by the viewer and the 3ds Max script)

Same frame as `parts`: metres, drawing coordinates minus `offset`; plan (x, y) -> three.js (x, z = -y); heights above the level of `floor`.

```json
"furnitureKinds": [ { "key": "seat", "label": "Chair / stool", "colour": "#e07b00", "height": 450, "base": 0,
                      "onTop": false, "support": false, "blocks": true, "count": 85 } ],
"furniture": [ { "id": "L1-seat-001", "floor": "L1", "kind": "seat",
                 "family": "mollie_chair_a685_revit - A685 2", "block": "<raw block name>", "layer": "I-FURN", "handle": "2A4F",
                 "x": 12.346, "y": -3.21, "w": 0.6, "d": 0.57, "rot": 37.5, "on": null, "approach": [], "n": 1, "note": "" } ]
```

* `furnitureKinds`: only kinds that occur, in the table's order; `height` / `base` in mm after the office's overrides from the
  project file's `furniture` section (`heights`, `bases`; also `words`, `skip` and `minSize` as described above); `count` over all levels.
* `x, y`: the centre of the box; `w >= d` are the sizes along its own long and short axis (metres, mm precision);
  `rot`: degrees counter-clockwise (plan, y up) from +x to the long axis, in [0, 180), rounded to 0.01 degree.  A square or round box
  (`w - d < 0.001`, decided before rounding) has no meaningful long axis and is stored with rot in [0, 90); a rounding that reaches the end
  of the range wraps to 0.0 (square 89.996 -> 0.0, otherwise 179.996 -> 0.0).  three.js:
  `mesh.rotation.y = rot` (radians) at (x, z0, -y).  3ds Max: `matrix3 [cos,sin,0] [-sin,cos,0] [0,0,1] [x+offset.x, y+offset.y, level+z0]`.
* `on`: id of the supporting piece or `null`.  `n`: how many drawn pieces went into this box (cabinet fronts merged into a run, or the
  number of loose shapes in a cluster).  `handle`: the DXF handle of the block ("" for a cluster of loose shapes and for a piece nested
  inside another block, whose top-level handle would name the whole linked model; a cabinet that absorbed fronts keeps its own block's
  handle).  `block` is "" for a loose cluster, and `family` then reads `loose shapes on <layer>`.  `note` says what is not obvious:
  `inside block <name>`, `fronts merged: 12 x <family>`, `run of N fronts: ...`, `drawn loose, not as a block`, `in the approach of
  L2-002`.  `id`: `<floor>-<kind>-<nnn>`, numbered per floor and kind in a fixed order (by x then y), so the same drawing always
  gives the same ids.
* `approach`: ids (as in the model's `openings`; the presidential suite has no `openings` but its own `doors` list, whose codes are
  the ids: D-codes doors, O-codes open passages) of the doors and passages of the same floor whose approach the box stands in, `[]`
  when none; sorted.  Kinds that never block (curtains) are marked all the same.  The builder works it out from the model's openings (windows do not count) and, when the list is not empty, adds
  `in the approach of <ids joined by ", ">` to `note` (separated from other notes by "; "), so the 3D team can see which pieces to move.
  The approach of an opening is what a person of radius 0.30 m needs to walk straight through it: the zone Z = a rectangle centred on
  the opening, along the wall (opening width + 2 x 0.30 m) by across it 1.80 m (0.90 m each side).  A piece is in the approach when
  its centre lies in Z, or when its rectangle overlaps the clear corridor (the opening's own width by 1.80 m) by at least 0.0025 m2.
  A long box that only touches the margin of Z with its end is not in the approach.  Edges count as in: a centre exactly on Z's boundary,
  an overlap of exactly 0.0025 m2 (the kit takes distances to the micrometre and areas to the mm2 so float noise never decides an edge).
  On the bank this marks 13 of the 185 boxes, in the approach of 12 of the 42 doors and passages.  A builder passes the model's openings
  (same frame as its pieces) as the last argument of `furniture_kit.finish(pieces, floors, heights, bases, openings)`; `mark_approaches`
  is the same step on its own, and without openings every piece gets `approach: []`.
* Resolved at run time: `z0 = on ? base(support) + height(support) : kind.base`, `z1 = z0 + kind.height` (kinds in mm, boxes in m).
* A model whose own data has no `offset` or `floors` (the house: `house3d_merged.json` has `centre`, and its upper plan is shifted
  -74.021 m onto the ground plan's grid) gets them in the furniture JSON (`furniture_house.json`: `offset`, `floors` [{key, name,
  level}], `frame` {centre, shift}), and the page passes them to the viewer module.  Its upper-floor rows then give x_m, y_m on the
  shared grid: add 74.021 m to x for the place on the DWG sheet.  The presidential suite's model has an `offset` but no `floors`
  (one level): its page hands the module that level itself.
* **Where it is used (2 Nov):** the bank branch (185 boxes, 14 kinds), the presidential suite (120 boxes, 13 kinds; 41 grey: the
  drawing names neither 11 blocks nor 30 groups of loose lines), the Sukhumvit house (76 boxes, 9 kinds; 48 grey) and the hotel read
  from two plan pictures (`hotel_test/`, 2 Nov: 159 boxes, 8 kinds, every kind read by eye from the drawing; the check-in's round sofa
  and sofa have their backs as `seat-back` boxes, at the owner's word).  Pages and Max scripts: the bank, the suite and the hotel (page +
  script); the house (page only, it has no Max script).  The kit has 22 kinds since 2 Nov (`seat-back` added).

## The family list (CSV, for the 3D team)

`<project>_furniture_list.csv`, UTF-8 with BOM, comma separated, CRLF line ends, written by the builder with the office-default heights;
the viewer's "Save list (CSV)" button writes the same columns with the heights currently typed in.  Columns, in this order:
`id, level, kind, kind_label, family, block, layer, dxf_handle, x_m, y_m, width_mm, depth_mm, height_mm, base_mm, rotation_deg,
on_top_of, merged, note` - `x_m, y_m` are DRAWING coordinates (model + offset) with 3 decimals, sizes and heights are whole mm,
`base_mm` is the resolved underside (a computer on a 750 table says 750), `rotation_deg` 1 decimal, `level` is the floor key (L1).
Whole-mm values round half up (JavaScript `Math.round`: 62.5 -> 63).  Every row, the last included, ends with CRLF.  Sorted by level
(the model's floor order), kind (the kinds table's order), id.  Text rules, so that Python and JavaScript write the same bytes: RFC 4180
quoting (a field with a comma, a double quote, CR or LF is wrapped in double quotes, inner quotes doubled); `merged` is `n`;
`on_top_of` and `note` are empty strings when unset; decimals via fixed notation (Python `f'{v:.3f}'`, JavaScript `v.toFixed(3)`) and
never `-0.000` (write `0.000`); the text a function returns has NO byte-order mark - the file writer / the download adds `EF BB BF`
in front.

## 3ds Max

Boxes are live Box primitives (never Editable Poly), placed with an explicit `matrix3`, on layers `<PX>_<floor>_Furn_<Kind>`.  Each box is
checked as it is built: base z, top z and the four corners carried through its transform (reasons `base z`, `top z`, `corner 1`-`corner 4`),
and the world bounding box (node min / max, reason `bounding box`) only for an unrotated box, because Autodesk does not document what
min / max return for a turned node; a box that fails goes on `<PX>_Check_Failed` and is listed.  In the window the height spinners stand
two to a row, captioned with the kind's label when it has at most 16 characters (else its key in words), range 10 - 5000 whole mm,
half up (a model default outside the range widens the spinner just enough to hold it; a kind height under 0.5 mm is refused);
'Furniture boxes only' reports in a message of its own ('Added N furniture boxes ...').  Text in
the Max script is plain ASCII: Thai and other non-Latin letters are dropped from family, block, layer and the object name (2 of the
bank's 185 pieces), and 113 family names are cut at 40 characters in the object name.  The user property `<PX>_furnId` is the key that
ties a box to its row in the family list, which keeps the full UTF-8 names; `<PX>_family` holds the whole ASCII text.  User properties
come back from `getUserProp` as numbers or booleans when the text looks like one (a DXF handle that is all digits, `true`), so match
families by `<PX>_family` text or by the CSV, and an absent value (no support, no block, no handle, an all-Thai family) is written as the word `none` (read back alike as none, undefined,
a missing property or empty text; a kind may not be called `none`).
No Max machine was available when this was written: the furniture code has been checked as text only (lint, a mock interpreter and
the geometry re-computed independently), never run in 3ds Max.

## Files

* `furniture_kit.py` - kinds table, classification vocabulary, footprints, cabinet-front merging, supports, door approaches, CSV
  (builders import it); `test_furniture_kit.py` its tests.
* `furniture_boxes.js` - the viewer module (pasted into each viewer page the way `viewer_modes.js` is; a page may give it a detached
  slot div as `panel` and append that after `installBuildReplay`, and `window.__host.furniture` carries its API for tests: `pieces()` with
  `approach` and `blocking` (true while the box is in its level's colliders), `kinds()`, `setHeight`, `setVisible`, `setBlocks`,
  `setKeepDoorways` / `keepDoorways`, `reset`, `csv`, `meshOf`);
  `test_boxes.mjs` + `fixtures/harness.html` its tests in headless Edge (also run on the real bank model).
  A page whose level records are not the bank's `FL` gives the module an adapter `FL = {<key>: {key, name, level, group, colliders,
  walkables, late}}` built from its own arrays (the colliders and late lists must be the very arrays Walk and the replay use), with
  the model's own level, not Walk's floor objects: the house's Build settings move the floor groups, so a level taken from Walk would
  lift a box twice.  The suite's page passes `model: {...D, floors: [FL.suite]}` because its model has no floors.  Pages: bank
  (`bank_test/test_bank.mjs`, 49 checks), suite (`presidential_test/test_presidential.mjs`, 37, port PRES_PORT), house
  (`cad_test/test_house_furniture.mjs`, 29).  The 'Keep doorways clear' tooltip counts every box in an approach, curtains included.
* `furniture_max.py` - the 3ds Max script fragments (boxes, layers, height spinners) the generators splice in; `test_furniture_max.py`
  tests them against the generators (it runs both real generators, the bank's and the suite's; the suite's fixture is the mini model's
  level L1 under the key 'suite'), and `bank_test/test_bank_maxscript.py` (137) and `presidential_test/test_presidential_maxscript.py`
  (151) check the real generated scripts against their models and against the scripts that were run in Max (kept in each project's
  `previous_before_furniture_*` folder).  A one-level script (the suite: layers `PS_suite_Furn_<Kind>`) has no per-part floor index,
  so its 'Furniture boxes only' takes the level from the window's 'Floor level' spinner and says so.
* `fixtures/mini_model.json` - a small hand-made model in the contract above (for tests of the viewer and Max modules);
  `fixtures/expected_csv.py` an independent writer of the CSV; `fixtures/maxscript_lite.py`, `fixtures/maxscript_mock.py` a lint and a
  mock interpreter for the Max text; `fixtures/mini_furniture*.ms` generated test scripts (the Max test rewrites them).
