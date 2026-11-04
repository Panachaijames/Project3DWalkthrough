# Hotel test (2 Nov 2026)

A hotel's floor 1 (the lobby) and floor 2 run through the CAD-to-3D pipeline from **two presentation pictures, with no CAD
at all**: `source/floor1_plan.png` (1498 x 945 px) and `source/floor2_plan.png` (882 x 945 px). Floor to floor is
**2.90 m** (the owner's). It is the first model read from pictures: there are no layers, blocks or text to read, so a
person reads what cannot be measured (room names, what each piece of furniture is, which gap is a door) into
`src/picture_readings.json`, and `src/read_pictures.py` measures everything else on the pixels.

**Status (2 Nov 2026, late evening).** The model was rebuilt after the owner's answers of the afternoon (the scale is now
the stair, 2.50 m), the owner's correction of the first page (the purple "Computer / monitor" boxes at the check-in are seat
backs) and the second review's small faults (see "Fixed in the last round"). Model-data stamp **`6ab030750886`**, the
same on the page and the Max script.
- The page's 56 browser checks: **all 56 pass**, on two runs in a row. The two that failed on the last model (a slit
  beside the lintel at six doors, Walk's skins narrowing three of them) pass unchanged; the one check edited is the
  check-in's, for the sofa's new family name.
- The Max script's 196 text checks pass. **It has not been run in 3ds Max yet.**

| File | What it is |
|---|---|
| `hotel_3d_preview.html` | The 3D viewer: Orbit / Walk / Ghost, Camera, Floor 1 / Floor 2 / Both floors, glass, floor plates, room names, the **Plan picture** tick, the furniture boxes with a height box per kind |
| `Hotel_Lobby.ms` | The 3ds Max script: the same model as live, editable objects; the furniture as Box primitives on a layer per floor and kind; the hidden datum gives each picture's size and place |
| `hotel_topview.png` | Top view of both floors as built, furniture in its kind colours |
| `hotel_furniture_list.csv` | The family list for the 3D team: one row per furniture box (159 rows, UTF-8 with BOM) |
| `test_hotel.mjs` | Browser checks (56): `node hotel_test/test_hotel.mjs` from the project folder |
| `test_hotel_maxscript.py` | Text checks of the Max script against the model (196): `python -B hotel_test/test_hotel_maxscript.py` |
| `source/` | The two pictures, as received |
| `src/` | The scripts and the data they made: `picture_readings.json` (read by eye), `read_pictures.py` and `picture_kit.py` (pixels to `takeoff.json`), `hotel_project.json` (the owner's facts, decisions and assumptions), `build_model.py` (to `hotel_model.json`, `hotel_summary.json`, the CSV and the top view), `overlay.py` (the model drawn back on the pictures), `make_html.py` (the page), `generate_maxscript.py` (the Max script) |

## The owner's facts and answers

2–3 Nov 2026.
- **With the pictures:** the first picture is floor 1, the second is floor 2. The lift entrance is 1 m (rough). FL to FL
  is 2900 mm.
- **After the first build** (the answers to its questions):
  1. "One real dimension: stair width 2500 mm." This is floor 1's main flight, between its two brown side walls, which
     arrives at floor 2's middle "iconic staircase". It is now the scale's main reference.
  2. "Floor 2, west side: solid wall." As built.
  3. "The middle stair is going down to floor 1, the upper one is going up to floor 3." The iconic staircase is the
     floor 1 to floor 2 stair. The stair beside the toilets rises from floor 2 to a floor 3 that is not drawn.
  4. "The large white faceted shape in the middle of floor 2 is a seating." It is built as sculptural seating, kind
     seat, 450 mm.
- **After the first page:** the purple boxes the page called "Computer / monitor" at floor 1's check-in are **seat
  backs**, not screens: a monitor on the sofa makes no sense. The round shape and the rectangle are seating. See
  "Furniture boxes".
- **3 Nov:** floor 2's furniture, small at the stair's scale, stays as drawn: "keep it strictly as the drawing said".
  No size on floor 2 is changed, and the lift doors stay at the owner's 1 m.

## How the pictures were read

- **Scale from the stair.** Floor 1's flight is 2.50 m wide, taken as its **clear** width between the inner faces of its
  side walls. That is 148.19 px, measured on 22 rows clear of the red "Luggage storage" box, which is drawn on those
  faces. So floor 1 has 59.28 px per metre across.
  - Clear width is the only reading that gives sensible furniture: floor 1's armchairs come out 0.69–0.78 m and its sofa
    1.84 m. Measured over the side walls they would be 0.6 m and 1.5 m.
- **Cores matched, a scale per axis.** Both pictures draw the same lift core. Its faces give the ratio between the two
  pictures' scales: x 1.4095, y 1.3539. Floor 1 is drawn about 4 % wider than tall against floor 2.
  - Floor 2 is taken as drawn square (its round tables are round). So floor 1 is **59.28 x 56.94 px/m**
    (across x down) and floor 2 **42.06 px/m**.
  - The cores then stack within 0.034 m. With one ratio for both axes they were up to 4.5 px apart.
- **The lift doors** are built **1.00 m** wide (the owner's), each on its drawn centre. At the stair's scale they are
  drawn 1.12 / 1.12 m on floor 1 and 1.25 / 1.28 m on floor 2.
- **Walls** are traced on the centres of their outline strokes, so a wall is as thick as its strokes are apart. Straight
  faces are fitted to the straight runs. The red annotation strokes are painted over first, so the stair walls and the
  north wall come out straight and closed. At four places measured by hand the walls match face-to-face within 0.8 cm.
  - Walls drawn as light lines (the pantry's on its dark fill, the toilets' on teal) are given by hand as bands. So is
    the wall between the FEMALE toilet and the upper stair: a light band on the teal with a dark stroke on the stair
    side, whose centre is its face (0.18 m). Traced, only the stroke was dark enough, and face fitting had built the wall
    east of the stroke, on the stair's side.
  - The upper stair's two side walls' inner faces are measured like floor 1's flight: 2.75 m clear, as drawn.
  - The outside stair's spine is drawn faintly, like the tread lines that run on under it: it is read as a low wall.
- **How sure.** Everything hangs on the one stair width.
  - The owner's 1 m lift door is rough. If the scale came from the four lift doors instead, the model would be 0.84 x
    this size. From floor 1's two doors alone it would be 0.90 x.
  - Floor 2 draws the stair 2.93 m wide over its stringers. That matches floor 1's flight measured over its side walls
    (2.934 m), so the two drawings agree with each other.
  - Floor 2's furniture comes out small at this scale (dining chairs 0.40 x 0.36 m, bar stools 0.36–0.38 m). Floor 1's
    looks right. Kept as drawn (the owner, 3 Nov).
- **Size.** Floor 1's main walls measure 18.51 m x 8.26 m over their outer faces, or 18.51 m x 11.18 m with the stair
  bay and the RED BOX. Laid at the model's scale, the pictures cover 25.27 m x 16.60 m (floor 1) and 20.97 m x 22.47 m
  (floor 2).

The page checks the reading against the pictures. Along every face of the model's walls (a spot every 5 cm), the picture
is darker 4 cm inside the wall than 12 cm outside it:
- by 104 grey levels on floor 1 and 73 on floor 2;
- read 0.1 m off in any direction, at most 51; read 0.3 m off, at most 41.

A copy of the page with the pictures moved 5 cm, 10 cm or 20 cm fails that check.

## What was built

| Part | Floor 1 | Floor 2 | Height | From |
|---|---|---|---|---|
| Wall parts | 8 | 8 | 2.90 m (to the next floor) | The grey wall fill and its outline strokes; floor 1's two brown stair walls; the RED BOX's black walls (about 6 cm). On floor 2, one of the 8 is the wall that closes the picture's cut edge (assumed) |
| Low walls | – | 1 | 1.10 m | The outside stair's spine (0.48 m) |
| Glass | 8 panes and 8 mullions | 2 panes and the transom over ENTRY | full height, 5 cm thick | Floor 1's south facade and the core's two south windows; floor 2's bar side to the terrace |
| Lintels | 5 | 13 | from the head (2.10 m) to 2.90 m | One over each door (ENTRY has a glass transom instead) and each hatch |
| Hatch sills | – | 2 | 0.85 m and 0.90 m | The serving hatch to the canteen counter (its sill at the pantry counter's top) and the food lift's hatch |
| Railings | – | 7 | 1.10 m | 3 round the open stair (west, east, south); 4 on the terrace's open edges |
| Steps | 16 (the flight up to floor 2) | 7 (the stair up toward floor 3) | risers of 0.171 m | Stairs, below |
| Flat tread lines | – | 14 | on the floor | The outside stair |
| Floor plates | 158.4 m² inside, plus a 25.3 m² forecourt | 408.9 m², terrace included, with 5 openings | 0.20 m slab | Floors, below |
| Room names | 10 | 14 | | The hand lettering and red callouts |

- **Openings, 20 in all.** Floor 1 has 5 doors:
  - the 2 lift doors;
  - the car-park door;
  - the RED BOX's inner and outer doors (the ENTRANCE).

  Floor 2 has 12 doors, 1 passage (the toilet lobby) and 2 hatches. Every door and passage can be walked through its
  middle both ways. Five lead out of the drawn floor and are checked from inside only: F1-003 car park, F2-001 and
  F2-002 lifts, F2-007 key access, and F2-010 the pantry's double door to the food lift.
- **Each door is taken from its jambs as built.** Its width is the gap between the walls (or panes) on either side, and
  its lintel fills that gap, flush with both jambs. The lift doors are exactly 1.00 m (the owner's). So no slit runs up
  beside a lintel, none stands proud of a wall, and Walk gets each door's full width.
- **Stairs.**
  - The iconic staircase (F1-S1) has 16 solid steps from floor 1 that land on floor 2: 17 risers of 0.171 m, goings of
    0.27 m, 2.50 m wide. Floor 2 is open over the flight and only there (2.50 m x 4.33 m). No step runs under the slab,
    there is no slot beside the flight, and no tread line floats over the opening.
    - The picture's break line cuts both side walls. The east one is drawn on past the flight's top end. The west one is
      carried on 0.68 m to the flight's top end, at its own 0.22 m section. Along the whole run the widest gap between a
      step and a side wall is now 0.001 m. Before, nothing stood west of steps 14 and 15, and a slot up to 0.31 m high
      opened between them and floor 2's slab edge.
  - The upper stair (F2-S1) has 7 solid steps rising north from floor 2 toward floor 3, between its side walls (2.76 m).
    They end in the air at +1.19 m, because floor 3 is not drawn.
  - The outside stair is drawn flat, with a 1.10 m low wall (its spine, 0.48 m) between its flights.
- **Floors.**
  - Floor 1's forecourt is outdoor paving at 0.00 in front of the facade, so Walk can step out of the entrance. It is
    only about 0.56 m deep in front of the RED BOX, as drawn: the road beyond is not floor.
  - Floor 2's terrace runs to the outline floor 1 dashes for the floor above. That is 0.42 m south and 0.54 m east past
    floor 2's picture. Its railing runs to the facades at both ends.
  - Floor 2's back of house goes on past the picture's top edge. Where its floor would end in the air there (8.47 m, from
    the pantry's west wall to the east facade), a full-height wall 0.15 m thick closes it, just beyond the edge. It is
    labelled "picture edge (the drawing stops here; assumed closed)".
  - Floor 2 has openings over the stair (10.82 m²), lift 1 (4.94 m²), lift 2 (5.00 m²), a small shaft (2.16 m²) and a
    duct (0.23 m²). The food lift is a closed dumbwaiter with a hatch.

## Furniture boxes

Every piece drawn is **one coloured box, colour = kind**, with a **height in mm per kind**. The height can be typed in the
viewer and in the Max script's window. Boxes stop you in Walk and not in Ghost. This is the shared furniture code in
`../furniture/` (the owner's decisions of 28 Oct). **159 boxes in 8 kinds**: 23 on floor 1 and 136 on floor 2.

| Kind | Floor 1 | Floor 2 | Height (mm) | What |
|---|---|---|---|---|
| Plant | – | 3 | 600 | a plant and two shrubs |
| Chair / stool (seat) | 5 | 45 | 450 | Floor 1: the L-shaped built-in bench (2 boxes), the check-in's round sofa and check-in sofa, a round stool. Floor 2: dining chairs, chairs, bar stools, round stools, a bench, and the **sculptural seating** (3 boxes following the faceted form) |
| Sofa / armchair | 5 | 32 | 800 | armchairs, sofas, outdoor sofas and armchairs |
| **Seat back** | 5 | – | 800 | the check-in's seat backs (the owner, 2 Nov) |
| Table / desk | 1 | 3 | 750 | a desk; the dining table, two small round tables |
| Coffee / side table | 6 | 18 | 450 | coffee and round side tables, outdoor side tables |
| Counter top | 1 | 10 | 850 | the coffee counter; the bar and back bar, the canteen counters, the pantry counter at the serving hatch and a worktop in the back room |
| Cabinet / casework | – | 25 | 900 | the signature display cabinets, display cabinets, a console |

- **No grey boxes.** Every piece got a kind, so there is no "Other" kind, and no lamps.
  - The circles with a cross (2 on floor 1, 3 on floor 2) are read as ceiling or pendant lights.
  - The faint square with a cross in floor 2's lift lobby is a glyph of the printed background drawing.
  - The art work on floor 1 is a panel on the wall.
- **The check-in (the owner, 2 Nov).** The page first showed purple "Computer / monitor" boxes there: a monitor on the
  rectangle (then read as a check-in desk) and four self check-in screens on the round shape (then read as a round
  table). They are now:
  - the **round sofa** (F1-seat-004, 2.49 x 2.40 m) and the **check-in sofa** (F1-seat-003, 1.42 x 1.04 m), both kind
    Chair / stool, 450 mm;
  - their **five seat backs** (F1-seat-back-001 to 005, salmon, 800 mm), standing on the floor where they are drawn: one
    at the check-in sofa's north rim, four round the round sofa's rim. Each back's outer face is 0.08–0.19 m inside the
    seat's edge, so 350 mm of back shows above the seat.

  The two seats are kind seat, not sofa, because every box of one kind gets the same height: an 800 mm sofa box would hide
  its own 800 mm backs. The round sofa is a square box round the drawn circle, so its corners stand up to about 0.5 m
  beyond it. Nothing in the hotel stands on another box now.
- **The serving hatch.** The pantry counter (F2-counter-006, 850 mm) stands in the serving hatch F2-014, so the hatch's
  sill is at the counter's top, 0.85 m: the counter reads flush through the hatch. The white strip east of the food lift
  is a worktop (F2-counter-009) in the back room, in front of a wall the picture draws solid.
- **Doorways.** One box (F2-coffee-table-001) stands in the approach of the toilet lobby's passage. With *Keep doorways
  clear* ticked (the default) every door and passage can be walked through.
- **For the 3D team.** `hotel_furniture_list.csv` has one row per box: kind, family, place, size and height.
  - Families are short names ("round sofa", "seat back", "bar stool") and the remarks are in the note.
  - The check-in's rectangle is family **"check-in sofa"** (renamed 2 Nov, evening), so "sofa" now only means floor 2's
    three sofas: kind Sofa, 800 mm, their backs in the box. The check-in sofa is kind Chair / stool with a separate
    back box.
  - In the legend and the hover label the check-in seats show as "Chair / stool", with "round sofa" or "check-in sofa"
    under it.

## Try the page

Open `hotel_3d_preview.html` (a double-click is enough: the two pictures are inside the page). The panel on the left has:
- **Both floors / Floor 1 / Floor 2.**
- **Orbit / Walk / Ghost / Camera** (keys 1, 2, 3; P takes a photo, named `Hotel-pictures_...`).
- The ticks **Floor plates, Glass, Room names** and **Plan picture**.
- The legend, and the furniture boxes with a height box per kind.

The **Plan picture** tick lays each floor's picture flat on its floor plate, 5 mm above it, at the model's scale and
place, so you can see the model on the drawing it was read from.
- It is **off when the page opens**. Tick it, or open the page with `?picture=1` at the end of its address.
- It shows with its floor (both floors in Walk).
- It is not a floor or a wall: Walk, the furniture and the double-click do not see it.

Things worth a look:
- Walk in from the forecourt through both RED BOX doors.
- Walk up to the open stair on floor 2 (PgUp): its railings, Floor 1's flight below, the stair to floor 3 beyond.
- The check-in's seats with their backs.
- The sculptural seating.
- Floor 2's terrace with its railing, and the outside stair's low spine.

## Try the 3ds Max script

1. Open 3ds Max with a **new, empty scene**. The script will not touch a scene that has objects in it.
2. *Scripting → Run Script…* and pick `Hotel_Lobby.ms` (or drag it onto a viewport).
3. A small window opens, with each floor's level and wall height (0.00 / 2.90 m and 2.90 / 2.90 m) and, under *Furniture
   boxes*, one height in mm per kind. Leave them and press **BUILD THE MODEL**. Build sets System Units to metres.
4. The MAXScript Listener (F11) should say **"HL BUILD COMPLETE: 273 objects ... 0 failed checks"**: 89 parts, 1 stair
   shape, 24 room names and 159 furniture boxes, plus one hidden datum. The message box says the same. If no window
   opens at all, the Listener shows a syntax error and its line: tell us the line.
5. *Save As* to keep it.

The script works like the bank's: every line of its code is the bank's script, which the 3D team ran on 28 Oct, plus the
furniture code of 29 Oct.
- Every part is a **live object, never an Editable Poly**: an editable spline with an **Extrude** modifier (output: mesh)
  and a Smooth modifier.
- **Update levels and heights** moves every part to its level. It sets walls, glass, mullions and lintels to the new wall
  height; steps, slabs, low walls, sills and railings keep their heights.
- **Collapse to Editable Mesh** works before Build or afterwards.
- **Apply furniture heights** and **Furniture boxes only** work as on the bank.
- **Position.** It is placed at the pictures' own frame in metres: 0,0 is the lift core's north-west corner on both
  floors. Untick *At the drawing's own coordinates* to centre it on the origin.
- **The pictures.** To lay a picture under its floor, read the hidden point **`HL_ORIGIN_DWG`** (layer `HL_Datums`),
  under *Object Properties > User Defined*.
  - `Picture_F1`: `source/floor1_plan.png`, a plane **25.2716 x 16.5971 m**, centre **[-5.3129, -3.7404] m** from the point.
  - `Picture_F2`: `source/floor2_plan.png`, a plane **20.9722 x 22.4702 m**, centre **[-6.3953, 0.1636] m**.
  - Floor 1's plane is not square in pixels per metre (59.28 across, 56.94 down), so scale the picture to those metres
    exactly.

| Layer (per floor: `F1`, `F2`) | Objects |
|---|---|
| `HL_F1_Walls`, `HL_F2_Walls` | 8 + 8 wall parts (floor 2's include `HL_F2_Wall_..._picture edge (the drawing stops here; assumed closed)`) |
| `HL_F2_Parapets` | 1 low wall: the outside stair's spine, 1.10 m |
| `HL_F1_Glass`, `HL_F1_GlassFrames`, `HL_F2_Glass` | 8 panes and 8 mullions; 2 panes and the ENTRY transom |
| `HL_F1_Lintels`, `HL_F2_Lintels`, `HL_F2_Sills` | 5 + 13 lintels, 2 hatch sills |
| `HL_F2_Railings` | 7 railings |
| `HL_F1_Steps`, `HL_F2_Steps` | 16 + 7 steps |
| `HL_F1_Slab`, `HL_F2_Slab` | 2 slabs on floor 1 (inside, forecourt) and 1 on floor 2 (5 holes) |
| `HL_F2_Stairs` | The outside stair's 14 tread lines, as a plain spline shape |
| `HL_F1_RoomNames`, `HL_F2_RoomNames` | 10 + 14 text shapes |
| `HL_F1_Furn_Seat`, `HL_F1_Furn_SeatBack`, `HL_F2_Furn_Cabinet`, ... | The 159 furniture boxes, one layer per floor and kind (13), named `HL_F1_Furn_seat-back_001_seat back` ... with the family as a user property |
| `HL_Datums` | The hidden point with the source, the levels and the two pictures' placement |
| `HL_Check_Failed` | Should not appear: anything here failed the closed-solid, height or position check |

That is 31 layers. **Not yet run in 3ds Max.** It is checked as text instead: a token lint, a mock interpreter that runs
Build, Apply, Update levels and Furniture boxes only, and every outline and box corner worked out again from the model.

## Assumptions

Each one is in `src/hotel_project.json`. The owner can change any of them.
- **The scale:**
  - The 2.50 m stair is the flight's clear width between its side walls.
  - Each picture has its own scale per axis from the shared lift core, and floor 2 is drawn square (see "How the pictures
    were read").
  - The lift doors are built exactly 1.00 m on their drawn centres, with wall back at both ends.
- **Heights:**
  - Levels are 0.00 and +2.90 m, and walls are 2.90 m high on both floors, up to the next floor.
  - The slab is 0.20 m under each floor.
  - Door heads are 2.10 m everywhere, the lift doors included, with a lintel above each door to the top of the wall.
  - Railings and low walls are 1.10 m. No section or elevation was given.
- **Walls:**
  - A wall is as thick as its outline strokes are apart.
  - The RED BOX's walls (two dark strokes, about 6 cm) and the stair's two brown side walls on floor 1 are full-height
    walls. The picture's break line cuts the flight's side walls, not the walls themselves: they run on to the flight's
    top end.
  - Walls drawn as light lines (the pantry's on its dark fill, the toilets' on teal) are read by eye as bands 0.12–0.24 m
    thick.
- **Glass** is 5 cm thick and full height:
  - floor 1's south facade, whose mullions are the dark ticks drawn on it, 0.22–0.27 m wide;
  - the core's two south windows;
  - floor 2's bar side to the terrace, with a glass transom over the ENTRY door, which stands between glass.

  Floor 2's west facade is wall (the owner).
- **The iconic stair:**
  - It is built as 17 risers of 0.171 m between its side walls. The bottom riser is on floor 2's drawn void edge, where
    floor 2's bench stands; that is 0.24 m north of floor 1's lowest drawn tread line, so that no step runs under
    floor 2's slab.
  - Floor 2's opening is fitted to the flight, with 1.10 m railings on the slab at its west, east and south edges. The
    south railing is not drawn (the bench stands there), but the drop is 2.90 m.
- **The upper stair:**
  - Its 8 drawn riser lines become 7 solid steps rising north (goings 0.32 m), between its side walls, ending in the air
    at +1.19 m.
  - The grey landing north of them is left at floor 2's level, where the FEMALE door F2-006 opens.
- **The outside stair:**
  - Its tread lines lie flat: it is not known whether it goes up or down to the street.
  - The spine between its flights (0.48 m) is a 1.10 m low wall: it is drawn faintly, like the tread lines.
  - Its outer west line is its one west wall; the inner double line is read as a kerb or rail line.
- **Floor 2's openings:** it is open over both lift shafts, the small shaft and a duct. The food lift is a closed
  dumbwaiter with a hatch on its north side, facing the food lift lobby. The white strip in the pantry's south wall,
  facing the canteen counter, is a serving hatch, open from the pantry counter's top (0.85 m) to 2.10 m. The white
  strip east of the food lift stands in front of a wall the picture draws solid: a worktop, not a second hatch.
- **Floors:**
  - Floor 1 is the inside of its walls and glazing, with the RED BOX.
  - The forecourt paving is outdoor floor at 0.00, from the facade to the road (the thin rounded line in the paving is not
    its edge).
  - Floor 2 includes the pantry, the outside stair's enclosure and the terrace, which runs past the picture's edges to the
    outline floor 1 dashes for the floor above, with a 1.10 m railing on its open edges, run to the facades.
  - The floor beyond floor 2's top edge (the back of house, the toilets) is not modelled. Where the drawing stops with the
    floor open (8.47 m, from the pantry's west wall to the east facade), it is **assumed closed**: a full-height wall,
    0.15 m, stands just beyond the edge, labelled "picture edge (the drawing stops here; assumed closed)", so nobody
    walks off it. The toilets are closed by their drawn north wall.
- **Room names** stand where their lettering or red callout is. Car park and Entrance lie outside floor 1's plate, as
  their labels do. "Luggage storage" (the red box drawn over the lower half of the flight) is put at the flight's north
  end, where the high steps leave headroom underneath.
- **Furniture:**
  - The kind of each piece is judged by what it looks like.
  - The sculptural seating is 3 boxes, kind seat.
  - The check-in's seats and seat backs are as above.
  - The circles with a cross are lights, not boxes.
  - Every kind keeps the furniture kit's office height.
- **Left out as annotation:** the red callout lines and dots (their words kept as room names), the black traffic arrows,
  the dashed site lines (floor 1's dashed outline of the floor above is used for the terrace's edge), the bar zone's
  dashed outline, and the faint printed text of the underlying drawings.

## Questions still open for the owner

- **The stair to floor 3** stops at +1.19 m after 7 steps. The picture draws a grey landing at its top, where the FEMALE
  toilet's second door (F2-006) opens. Is that a half-landing (about +1.37 m, 8 risers) where the flight turns back up
  to floor 3? If so, the FEMALE door cannot open onto it: is it really there? Until then the steps end in the air, with
  a 1.19 m drop to the landing behind the top step.
- **"Iconic staircase":** the picture writes it by the upper stair (beside the toilets), and the room name stands there.
  Your "iconic staircase" is the middle one (the stair from floor 1). Should the name move onto the middle opening?
- **The drop-off road** in front of the RED BOX: only about 0.5 m of paving is drawn before it (built 0.56 m, as
  drawn). Should the road be floor too?
- **The round sofa** is one square box (2.49 x 2.40 m) round the drawn circle, as the furniture kit makes every piece a
  box, so its corners stand up to 0.5 m beyond the circle. Keep it, or two crossed boxes (about 2.43 x 1.71 m each),
  which halve the overhang?
- **Lift doors:** at the stair's scale the drawn lift openings are 1.12 m (floor 1) and 1.25–1.28 m (floor 2). Is the
  1 m lift entrance the door's clear width inside a wider opening? Each is built 1.00 m either way.
- **The circles with a cross:** ceiling or pendant lights, as built (no boxes)?
- **The outside stair:** does it go up to floor 3 or down to the street? Is the inner double line on its west side a
  wall?
- **"Luggage storage":** the space under the stair's high end, as placed, or a change to the stair?
- **The middle stair's opening** is built 2.50 m between floor 1's side walls, so floor 2's floor covers the walls' tops.
  Should it be over the walls instead (2.93 m, railings on the walls' tops), as floor 2 draws it?
- **Floor 2's top edge:** what lies beyond it? The back of house is closed there by an assumed wall.
- **The plan picture:** should it be on when the page opens? It is off now, so the page opens on the clean model.
- **3ds Max:** should the script lay the two pictures under their floors as textured planes? Now it only gives their
  size and place on the datum, which is new Max code that has never been run.

## Fixed in the last round (the second review, 2 Nov, late evening)

Each general fix is a rule in `src/build_model.py` (its rules docstring says it); the readings' fixes are in
`src/picture_readings.json`.

| # | Fault | Now |
|---|---|---|
| 1 | At six doors the gap between the refitted walls was wider than the recorded door: a slit beside the lintel from 2.10 m up to the floor above, Walk's skins narrowing three doors, and lintels standing up to 6.5 cm proud of the walls | Every door and passage is taken from its built jambs (rule 5). F1-003 2.058 → 2.083 m, F1-004 1.805 → 1.829, F1-005 1.738 → 1.756, F2-006 0.713 → 0.725, F2-007 1.926 → 2.009 (its 8.5 cm slit), F2-013 1.308 → 1.322, the passage F2-003 0.999 → 1.013. Measured on the outlines: no slit wider than the builder's 1 mm clearance at any of the 17 doors, and no lintel proud of a wall by more than 1 mm; Walk gets every door's full width (the page's check, 17 of 17). The same rule made the ENTRY transom 5 cm deep and flush with the panes on either side; it was 0.19 m and stood up to 10.4 cm proud of them |
| 2 | Serving hatch F2-015 cut through a wall the picture draws solid | Gone, the wall solid again. The white strip is a worktop in the back room. F2-014 kept |
| 3 | F2-014's counter (850 mm) sat inside the hatch's 900 mm sill | A hatch with a counter in it has its sill at the counter's top (rule 5): 0.85 m. The food lift's hatch keeps 0.90 m |
| 4 | The terrace railing stopped 0.15 m short of the walls at both ends | Each railing runs on to the wall face its end lies near (rule 8): 0.000 m at both ends |
| 5 | The outside stair's spine was a full-height wall | A 1.10 m low wall (rule 3; read as a low wall) |
| 6 | Floor 1's west stair wall stopped 0.68 m short of the flight's top end: beside steps 14–15 a slot up to 0.31 m high under floor 2's slab edge | A side wall the break line cuts is carried on to the top riser (rule 6). Widest slot along the whole run 0.001 m (43 places, 0.1 m apart) |
| 7 | The wall between the FEMALE toilet and the upper stair stood on the stair's side of its stroke (0.09 m thick); the stair was 2.62 m wide where 2.75 m is drawn | Re-read as drawn (0.18 m, px 267.5–275). The stair's side walls are measured (2.75 m clear) and its steps run from wall face to wall face (rule 6): 2.76 m |
| 8 | Floor 2's back of house ran off the picture's top edge with an open slab edge | Closed by a full-height wall just beyond the edge (rule 8), labelled "picture edge (the drawing stops here; assumed closed)" |
| 9 | "sofa" meant two things | Floor 1's check-in sofa is family "check-in sofa" |

Found and fixed on the way:
- **A wall across the upper stair's top step.** The stair's top riser line, with the arrow's head on it and the step's
  shadow under it, is 5 px of wall grey: it had been traced as a 2.90 m wall, 7.6 cm thick, standing on the top step.
  It is erased as a tread line.
- **F2-013's west jamb.** The wall stub there was half a hand-drawn band (3 px north of the drawing) and half a notched
  trace. It is one band now, as drawn (px 733.5–743.5, to the door at px 580).
- The FEMALE toilet's south wall now ends on the re-read wall's face, not 5 cm into the stair.

## Known defects and notes

- **F1-004** (the RED BOX's inner doors): face fitting built the wall west of it 0.13 m thick, against the RED BOX's 6 cm
  walls and the 6 cm wall east of it. The lintel keeps the door's own band there, so above the door's west end the
  wall's south face stands 2.8 cm out from the lintel: a step, not a slit.
- The upper stair's top steps stand over a hollow and end in the air (the owner's question above).
- The Max script has not been run in 3ds Max; its furniture code has never run in Max either.

## Rebuild and test

From the project folder. It needs Python 3 with Pillow, numpy, shapely and matplotlib, and Node 22 with Edge for the
browser checks. The builder uses `../furniture/furniture_kit.py` and `../presidential_test/src/geom.py`; the page embeds
`../viewer-modes/viewer_modes.js` and `../furniture/furniture_boxes.js` unchanged.

    # 1. The pictures -> src/takeoff.json (it will not overwrite a take-off edited by hand: --force to do so)
    python -B hotel_test/src/read_pictures.py
    # 2. The model -> src/hotel_model.json, src/hotel_summary.json, hotel_furniture_list.csv, hotel_topview.png
    python -B hotel_test/src/build_model.py
    #    (to check it by eye: the model drawn on both pictures, at 1x and 2x, a margin view of floor 2 for what stands
    #     beyond its picture's edges, and floor 2 over floor 1)
    python -B hotel_test/src/overlay.py <a folder outside the project>
    # 3. The viewer and the Max script (both stamped with the same model data)
    python -B hotel_test/src/make_html.py hotel_test/hotel_3d_preview.html
    python -B hotel_test/src/generate_maxscript.py hotel_test/Hotel_Lobby.ms
    # 4. Checks (headless Edge on port 9421; HOTEL_PORT, HOTEL_PROFILE, HOTEL_OUT to change the port, profile and screenshot folder)
    node hotel_test/test_hotel.mjs
    python -B hotel_test/test_hotel_maxscript.py
    python -B furniture/test_furniture_kit.py

The reader, the builder, the page and the Max script each give the same bytes when run twice. The browser checks (56,
about 60 s) cover:
- **The page:** it opens without errors, with both pictures; room names show and none sits on another; the floor
  buttons, Walk on both floors, PgUp and PgDn.
- **Walls and doors:**
  - walls stop you at 40 random spots per floor;
  - every door and passage can be walked through both ways;
  - door heads are 2.10 m and each lintel reaches both jambs;
  - the passage is left open;
  - the lift doors are 1.00 m with walled shafts, and the walk skins reach into no door;
  - the glazing stops you.
- **Floor 2:** floor where its plate is, open over the stair and the shafts.
- **Stairs:** the steps sit one riser apart; the iconic stair lands on floor 2 with no step under the slab and no tread
  line over the opening; the upper stair rises toward floor 3.
- **What the owner's answers changed:**
  - the 2 hatches are open from sill to head;
  - the forecourt is floor, and the entrance can be walked out and in;
  - the railings on the terrace and round the open stair stop you;
  - no lamp boxes stand on the light symbols;
  - the sculptural seating is kind seat;
  - the check-in has no computer box left, and its five seat backs stand at the rims of the round sofa and the
    check-in sofa.
- **Ghost** goes through a wall.
- **The Plan picture tick:** off at first, `?picture=1`, the source files byte for byte, the sheets' corners, and the
  walls lining up with the picture.
- **The furniture:** the legend, 159 boxes on their floors, typed heights, Walk stopped short of 154 real boxes, a hidden
  kind, a seat typed 300 mm stepped over, Ghost through a table and a counter, all doors with the boxes on, *Keep doorways
  clear*, nobody held inside a box, the page's CSV equal to `hotel_furniture_list.csv`, the hover label, and the side
  panel at 1366 x 768 and 1920 x 1080.
- **The rest:** the Camera's photo name, the model-data stamp shared with the Max script, and no page errors.

The Max checks (196) cover the file, every part's outline, the room names and stair lines, every box's corners, the
code's rules, a comparison with the bank's scripts line by line, the generator, the lint, a mock run of every button,
and the datum's picture placement.
