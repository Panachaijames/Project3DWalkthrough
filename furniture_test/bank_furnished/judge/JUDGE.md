# Slimming judge: how far the bank's own furniture can be slimmed

3 Nov 2026. The 3D team's eight models for the bank branch (`banquet/`) and the chair test's `Chair.glb` were each slimmed
once with three.js 0.186.1's SimplifyModifier (meshoptimizer inside; read from `app/node_modules`, nothing installed) to 50,
25, 12 and 6 % of their triangles, and to 20,000 / 10,000 / 5,000 / 2,500 where those are below their count. Every level was
measured against the full model, drawn beside it under the same light and neutral material at walking distance and close up,
at the size it has on a 1920 × 1080 screen, and judged by eye. Nothing was timed. The pictures were drawn by Edge on the
Intel chip in 10 s; the CPU was 40 % busy before and 43 % on average (60 % at most) during that run, other agents' work
included (`render_run.json`).

**In short:** every chair looked the same at walking distance at about 5,000 triangles and was fine close up at about 10,000,
however heavy it came (the mollie chair: 241,326). The light models (104 - 6,084 triangles) mostly showed it from about
half (the pouf held to a quarter at 3 m), and the 104-triangle desk could lose nothing. So the spec below slims only what is above its kind's number,
and the bank's furniture comes to about 0.6 - 0.7 million triangles, a third of the laptop budget.

## Verdicts

*The same at 3 m*: the lowest level I could not tell from the full model at walking distance. *Acceptable close up*: the
lowest level with nothing a client would notice standing at it (differences that show only side by side are allowed).
*Same close up*: the lowest level I could not tell apart standing at it. The slimmed levels have their normals worked out
again as in the chair test.

| Model (pieces in the bank) | Full | The same at 3 m | Acceptable close up | Same close up | What goes first | Sheet |
|---|---:|---|---|---|---|---|
| visitor chair01, mollie chair (19) | 241,326 | **5,000 budget: 4,940** (2.0 %) | **10,000 budget: 9,712** (4.0 %) | 20,000 budget: 19,744 (8.2 %) | lumps along the backrest's top edge and where the seat meets the back: close up from 5,000, at 3 m from 2,500 | `visitor_chair01.png` |
| visitor chair02, round VISIONA stool (4) | 6,084 | **50 %: 3,042** | **50 %: 3,042** | 50 %: 3,042 | a streak down the cone-shaped base from 2,500 (41 %), which is the shading, not the shape; then the cushion's rim turns polygonal (12 %) | `visitor_chair02.png` |
| stool, VISIONA pouf (5) | 2,680 | **25 %: 670** | **25 %: 670** | 50 %: 1,330 | its rounded edges turn into flat facets (12 %, 320) | `stool.png` |
| sofa, SE107 bench (3) | 2,223 | **50 %: 1,108** | **50 %: 1,108** (a corner a touch flatter) | full | the rounded corners turn into facets (25 %, 554), then the back pad goes square (12 %) | `sofa.png` |
| banquet, DIOR bench: one copy for the run of 4 modules | 4,720 | **50 %: 2,360** | **25 %: 1,180** | 50 %: 2,360 | the cushions' piping line and the soft curve of their fronts (25 %), then the cushion ends (12 %) | `banquet.png` |
| working table (5) | 104 | **do not slim** | full | full | 50 % (52): the modesty panel's recess goes; 25 %: shading bands; 12 %: a leg becomes a spike | `working_table.png` |
| side table (9) | 1,564 | **50 %: 782** | **50 %: 782** | 50 %: 782 | the curve where the upright meets the base flattens (25 %), then the rounded corners of the top and the base (12 %) | `side_table.png` |
| monitor: screen, keyboard and mouse (16) | 15,290 | **2,500 budget: 2,496** (16 %) | **5,000 budget: 4,999** (33 %) | 10,000 budget (65 %) | faint banding on the flat screen (the shading) from 50 %, the keyboard's indicator dots and the stand's ring at 5,000 - 2,500, some keys merge at 12 %, a jumble at 6 % | `monitor.png` |
| Chair.glb, the chair test's chair (75 seats in that test) | 41,921 | **5,000 budget: 4,999** (12 %) | **10,000 budget: 9,997** (24 %) | 20,000 budget: 19,997 (48 %) | the seam lines (mostly gone at 10,000), flat facets on the back and the seat edge (5,000), a dent in the back (2,500) | `chair_test.png` |

The chair test's own verdict on `Chair.glb` (12 %, 5,030 triangles: the same at walking distance, a few flat facets and no
seam lines close up) is what these pictures show too; this run's 12 % came out at 5,027 triangles.

## The spec proposed for the application

Two copies of each model in the browser, both made once on import. The original stays in the library for Max; the browser
never needs it (the mollie chair at 19,744 triangles cannot be told from its 241,326 even standing at it).

| Kind | Every piece | Close-up copy (pieces within 2 m) | From |
|---|---:|---:|---|
| **Chair** (task, visitor, dining, small armchair) | **5,000** | 10,000 | the mollie chair at 4,940 and the chair test's chair at 4,999 look the same at 3 m; both need about 10,000 close up |
| **Stool, pouf** | **3,000** | 6,000 | the round stool looks the same at 3,042 both ways (at 2,500 a faint streak shows); the pouf at 670 / 1,330 |
| **Sofa, bench** | **5,000** | 10,000 | both bank models are under it (2,223 and 4,720) and lose shape below about half; nothing heavier came, so a big upholstered sofa may need the rule's step up |
| **Table, desk, side table** | **2,000** | 4,000 | the desk (104) and the side table (1,564) are under it; slimming them showed at once |
| **Monitor and small electronics** | **2,500** | 5,000 | the monitor set looks the same at 3 m at 2,496 and is fine close up at 4,999 |
| Not measured, by likeness | cabinet 2,000; plant 5,000; sanitary fitting 2,500; ATM 5,000; TV, privacy screen 500 | twice that | |

**The rule for any model:**
1. **At or below its kind's number: keep it as it is.** Do not slim it: the light models here lost their shape fast (the
   desk at 50 %, the side table's curves at 25 %, the sofa's corners at 25 %).
2. **Above it: slim once to the number** (weld by position at 0.1 mm, drop the normals, SimplifyModifier, work the normals
   out again) **and check it against the original**: the largest gap that can be seen at most 3 mm (one pixel at 3 m on a
   1920 × 1080 screen through the Walk lens); outline overlap at least 0.98 from the front, the side and the top (2 mm grid:
   nothing missing); at least 98 % of the surface area kept. If a check fails, try 1.5, 2 and 3 times the number and keep the
   first that passes; if none does, keep 3 times and flag the model in the library for the 3D team.
3. **The close-up copy**: the same, starting at twice the number, with the largest gap at most 1.5 mm (one pixel close up),
   used for the pieces within 2 m of the viewer. An Ultra setting would show this copy everywhere, not the original.
4. **Someone looks at it once** on the library page before it is used: the checks do not see shading faults (the streaks on
   the round stool at 2,500 and on the monitor's screen pass every check).

Run on these nine models, the rule gives: the mollie chair 4,940 and a close-up copy of 9,712 (both pass at the first try);
the chair test's chair 4,999 and a close-up copy of 19,997 (9,997 leaves a 1.7 mm gap, so it steps up; 15,000 was not made); the round stool
about 3,000 (its 3,042 level passes) with itself as the close-up copy; the monitor 2,496 and 4,999; the pouf, the sofa, the
banquet, the desk and the side table stay as they are. Each of these is a level I judged the same at 3 m (and acceptable
close up for the copies). The checks are on the safe side: they would also turn down the sofa at 50 % (a 6 mm gap at its
plinth, on the floor) and the side table at 50 % (its thin front outline), which looked the same.

**visitor chair01 (241,326 triangles).** A high-detail mesh (4 parts, each with a 6.4 scale left on it: an imported asset),
5.8 times `Chair.glb` and 8.1 MB. Slimmed to 4,940 triangles (2 %) it looks the same at walking distance, at 9,712 (4 %) it
is fine close up, and at 19,744 (8 %) it cannot be told apart even standing at it. So: import it like any other chair, 5,000
for every piece and 10,000 for the close-up copy; its 19 pieces go from 4.59 million triangles to 93,860. Slimming it takes
about 0.1 s. Ask the 3D team for a browser export of about 20,000 triangles with the scale reset, so that the library file is
about 0.2 MB instead of 8.1 MB, and keep the original for Max.

**Textures, for later (not measured: the exports carry none yet).** Within the plan's 2k limit:
- 1k (1024 × 1024) per map for a chair, stool, table or monitor; 2k only for the base colour of a big piece with its own print
  (a sofa, a long bench, a large desk or cabinet); 512 for small things (a phone, a mouse, a vase). Fabrics, woods and stones
  as repeating (tiled) textures rather than one big picture per piece.
- Three maps per material (base colour, normal, roughness / metal / occlusion), KTX2 compressed (Basis: ETC1S for colour and
  the third map, UASTC for normal maps), with mipmaps.
- Rough memory (worked out, not measured): with mipmaps a 1k map takes about 1.3 MB of graphics memory compressed (BC7; half
  that as BC1) and 5.3 MB uncompressed, a 2k map four times as much; a material's three 1k maps about 3.3 MB compressed. The
  bank's 54 families at about 2 materials each would need about 360 MB at 1k compressed, 1.4 GB at 2k compressed and 1.7 GB
  at 1k uncompressed. The laptop's Intel chip shares its 16 GB and the MX570 has 2 GB: so always compressed, 1k as the rule,
  materials shared between families, and a texture line next to the triangles in the budget meter (about 400 MB for the
  furniture). To be tested when the team's materials come across.

**The bank at this spec** (`spec_totals.json`): the 8 families' 65 pieces go from 4,893,555 triangles at full detail to
185,349. All 185 pieces at their kind's number would be at most 631,000, and the close-up copies at the busiest place (17
pieces within 2 m, at the level 1 desks) add 56,000: about 0.69 million in the worst case, a third of the 2-million budget.

## How it was done

- **The models.** Each GLB read with three.js's GLTFLoader and put in its own frame: turned back by its real turn in the
  team's scene (`../analysis.json`), front towards the camera, footprint centred, base on the floor, all parts merged into one
  mesh. The monitor stands on a plain desk top at 0.75 m in the pictures.
- **Slimming** (`slim_levels.mjs`), as the chair test's `slim_chair.mjs`: the merged mesh welded by position at 0.1 mm with
  its normals dropped, then SimplifyModifier (meshoptimizer's simplify, no error limit) down to the level's share of the
  triangles, each level from the full model. It is quick: at most 0.13 s a level on this laptop, 0.08 - 0.12 s for the
  241,326-triangle chair.
- **Shape against the full model.** *Outline overlap*: the filled silhouettes seen from the front, the side and the top on a
  2 mm grid, cells in both / cells in either (1 = the same; a thin outline, like the side table's from the front, makes it
  strict). *Area kept*: slimmed surface area / full. *Largest gap*: how far any point of one surface is from the other, both
  ways (every vertex, up to 100,000, and 100,000 points spread by area, to the nearest point of the other surface,
  three-mesh-bvh 0.9.16), over the points that can be seen from outside (a ray in one of 26 directions gets away) and over all
  points. For scale: one pixel of a 1920 × 1080 screen through the Walk lens is 3.0 mm at walking distance and about 1.4 mm
  close up.
- **Pictures** (`judge_page.html` and `judge_page.js`, run by `render_cells.mjs` in headless Edge on the Intel chip, inside
  the machine's one-Edge-at-a-time lock, ports 9770 - 9771): three.js 0.186.1, the bank page's light (sky light and one sun),
  the chair test's neutral material, a plain floor. The Walk camera: eye 1.6 m, 24 mm lens (53° tall), 30° to the right of the
  front, looking at the middle of the piece; *walking distance* = 3 m from its centre, *close up* = 0.6 m from its edge (Walk
  itself stops 0.3 m from a box). Each picture is a crop of the 1920 × 1080 frame, so at 100 % the model is as many pixels as
  on a client's screen. The full model keeps its exported normals; the slimmed ones have theirs worked out again (smooth
  across edges under 40°). `compose_sheets.py` lays out the sheets; big pieces are shown reduced there (noted on each row),
  and I judged them from the pictures at 100 %.
- **Picture differences** (`picture_diffs.json`): each level's picture against the full model's, pixel for pixel: the share
  of the model's pixels whose brightness changed by more than 10 of 255, and the structural similarity (SSIM). The levels I
  could not tell apart at 3 m changed 0.4 - 1.8 % of the pixels, those where something went mostly 3 - 10 % (the side table's
  flattened curve at 25 %: 1.7 %). Two exceptions, so read
  them as a guide only: the chair test's chair (its seam lines: 3.3 % already at 20,000) and the monitor (a slight change of
  tone on its flat screen: 2.9 % at 2,500).

### Normals: two findings for the import step

1. **Do not carry the exported normals through the slimmer.** Welded by position and normal (SimplifyModifier then weighs the
   normals and keeps hard edges as seams; `KEEP_NORMALS=1`), 6 of the 9 models could not get near their targets: the mollie
   chair stopped at about 26,100 triangles whatever was asked, the monitor at 5,900, the chair test's chair at 7,540, the side
   table at 748, the stool at 348, and the desk was not slimmed at all. Pushed further, it dropped whole parts (outline
   overlap 0.61 - 0.86, gaps of 4 - 40 cm; `levels_keepnormals.json`). Weld by position and drop the normals, as the chair
   test did.
2. **Working the normals out again is what shows first on smooth round pieces,** before the shape does: the streak down the
   round stool's base at 2,500 and the faint bands on the monitor's flat screen. Weighting each face by its corner angle did
   not help (`normals_compare.png`); the round stool's own normals, carried through, had no streak, but that way fails on most
   models (above). Worth trying in the app, not tested here: slim by position as now, then give each new vertex the normal of
   the nearest point of the original surface, except across sharp edges. Until then the stool number is 3,000 rather than
   2,500, and step 4 of the rule (someone looks once) stays.

## All levels and their measures

From `levels.json`. Outline overlap: 1 = the same silhouette; area kept: of the full model's surface; gaps over the points that
can be seen from outside (the 99th percentile in brackets) and over all points; KB: positions (32-bit) and indices,
uncompressed. The levels are in the order they were made (by size).

| Model | Level | Triangles | Share | Outline overlap, front / side / top | Area kept | Largest gap seen (99th percentile) | Largest anywhere | KB |
|---|---|---:|---:|---|---:|---|---:|---:|
| **visitor chair01** | full | 241,326 | 100 % | | | | | |
| | 50 % | 119,658 | 49.6 % | 0.9996 / 0.9997 / 0.9999 | 100.0 % | 0.4 mm (0.1) | 0.4 mm | 1350 |
| | 25 % | 59,888 | 24.8 % | 0.9994 / 0.9995 / 0.9998 | 100.0 % | 0.5 mm (0.2) | 0.5 mm | 674 |
| | 12 % | 28,450 | 11.8 % | 0.9987 / 0.9990 / 0.9997 | 100.0 % | 0.7 mm (0.3) | 0.7 mm | 317 |
| | 20,000 budget | 19,744 | 8.2 % | 0.9986 / 0.9985 / 0.9995 | 99.9 % | 0.8 mm (0.4) | 0.9 mm | 219 |
| | 6 % | 14,338 | 5.9 % | 0.9982 / 0.9981 / 0.9991 | 99.9 % | 0.9 mm (0.5) | 1.1 mm | 157 |
| | 10,000 budget | 9,712 | 4.0 % | 0.9970 / 0.9973 / 0.9986 | 99.9 % | 1.5 mm (0.7) | 1.5 mm | 106 |
| | 5,000 budget | 4,940 | 2.1 % | 0.9938 / 0.9948 / 0.9967 | 99.8 % | 2.5 mm (1.2) | 2.6 mm | 53 |
| | 2,500 budget | 2,346 | 1.0 % | 0.9878 / 0.9893 / 0.9943 | 99.7 % | 3.5 mm (2.4) | 5.3 mm | 25 |
| **visitor chair02** | full | 6,084 | 100 % | | | | | |
| | 5,000 budget | 5,000 | 82.2 % | 1.0000 / 1.0000 / 1.0000 | 100.0 % | 1.3 mm (0.1) | 1.3 mm | 59 |
| | 50 % | 3,042 | 50.0 % | 0.9999 / 1.0000 / 1.0000 | 100.0 % | 1.5 mm (0.3) | 1.5 mm | 36 |
| | 2,500 budget | 2,500 | 41.1 % | 0.9989 / 0.9989 / 1.0000 | 99.9 % | 1.5 mm (0.5) | 1.5 mm | 29 |
| | 25 % | 1,520 | 25.0 % | 0.9977 / 0.9978 / 1.0000 | 99.8 % | 2.6 mm (1.5) | 2.6 mm | 18 |
| | 12 % | 728 | 12.0 % | 0.9934 / 0.9946 / 0.9952 | 99.2 % | 5.9 mm (2.1) | 5.9 mm | 9 |
| | 6 % | 364 | 6.0 % | 0.9890 / 0.9871 / 0.9893 | 98.3 % | 7.4 mm (4.8) | 7.4 mm | 4 |
| **stool** | full | 2,680 | 100 % | | | | | |
| | 2,500 budget | 2,500 | 93.3 % | 1.0000 / 1.0000 / 1.0000 | 100.0 % | 0.2 mm (0.1) | 0.2 mm | 28 |
| | 50 % | 1,330 | 49.6 % | 1.0000 / 1.0000 / 0.9996 | 99.9 % | 0.9 mm (0.2) | 0.9 mm | 15 |
| | 25 % | 670 | 25.0 % | 0.9965 / 1.0000 / 0.9965 | 99.8 % | 1.8 mm (0.8) | 1.8 mm | 8 |
| | 12 % | 320 | 11.9 % | 0.9956 / 0.9995 / 0.9912 | 99.4 % | 3.6 mm (1.5) | 3.6 mm | 4 |
| | 6 % | 158 | 5.9 % | 0.9949 / 0.9934 / 0.9869 | 98.5 % | 6.9 mm (3.8) | 6.9 mm | 2 |
| **sofa** | full | 2,223 | 100 % | | | | | |
| | 50 % | 1,108 | 49.8 % | 0.9989 / 0.9992 / 0.9999 | 99.8 % | 6.0 mm (2.7) | 6.0 mm | 13 |
| | 25 % | 554 | 24.9 % | 0.9974 / 0.9969 / 0.9991 | 99.4 % | 7.7 mm (5.4) | 7.7 mm | 6 |
| | 12 % | 256 | 11.5 % | 0.9961 / 0.9908 / 0.9958 | 98.5 % | 22.2 mm (14.3) | 22.2 mm | 3 |
| | 6 % | 132 | 5.9 % | 0.9892 / 0.9879 / 0.9922 | 96.9 % | 47.4 mm (30.4) | 47.4 mm | 2 |
| **banquet** | full | 4,720 | 100 % | | | | | |
| | 2,500 budget | 2,498 | 52.9 % | 1.0000 / 1.0000 / 1.0000 | 100.0 % | 1.3 mm (0.1) | 1.3 mm | 29 |
| | 50 % | 2,360 | 50.0 % | 1.0000 / 1.0000 / 1.0000 | 100.0 % | 1.3 mm (0.2) | 1.3 mm | 28 |
| | 25 % | 1,180 | 25.0 % | 0.9994 / 0.9992 / 1.0000 | 99.9 % | 2.1 mm (1.1) | 2.1 mm | 14 |
| | 12 % | 564 | 11.9 % | 0.9938 / 0.9968 / 1.0000 | 99.7 % | 5.6 mm (2.8) | 5.6 mm | 7 |
| | 6 % | 282 | 6.0 % | 0.9904 / 0.9953 / 1.0000 | 99.3 % | 6.4 mm (4.9) | 6.6 mm | 3 |
| **working table** | full | 104 | 100 % | | | | | |
| | 50 % | 52 | 50.0 % | 0.9999 / 0.9961 / 0.9960 | 99.8 % | 2.5 mm (2.5) | 2.5 mm | 1 |
| | 25 % | 26 | 25.0 % | 0.9982 / 0.9961 / 0.9960 | 96.7 % | 49.4 mm (31.1) | 49.4 mm | 1 |
| | 12 % | 12 | 11.5 % | 0.9656 / 0.7326 / 0.9770 | 78.9 % | 587.8 mm (409.9) | 587.8 mm | 1 |
| | 6 % | 6 | 5.8 % | 0.0453 / 0.4948 / 0.9770 | 46.4 % | 749.4 mm (703.1) | 749.4 mm | 1 |
| **side table** | full | 1,564 | 100 % | | | | | |
| | 50 % | 782 | 50.0 % | 0.9886 / 0.9999 / 1.0000 | 99.7 % | 1.0 mm (0.2) | 1.0 mm | 9 |
| | 25 % | 390 | 24.9 % | 0.9576 / 0.9997 / 0.9999 | 99.2 % | 3.8 mm (1.2) | 3.8 mm | 5 |
| | 12 % | 186 | 11.9 % | 0.9131 / 0.9993 / 0.9979 | 98.6 % | 9.9 mm (5.0) | 9.9 mm | 2 |
| | 6 % | 92 | 5.9 % | 0.8508 / 0.9892 / 0.9836 | 94.1 % | 19.1 mm (11.1) | 19.1 mm | 1 |
| **monitor** | full | 15,290 | 100 % | | | | | |
| | 10,000 budget | 10,000 | 65.4 % | 1.0000 / 0.9999 / 1.0000 | 100.0 % | 0.5 mm (0.1) | 0.5 mm | 121 |
| | 50 % | 7,644 | 50.0 % | 1.0000 / 0.9997 / 0.9998 | 99.8 % | 0.5 mm (0.3) | 0.5 mm | 93 |
| | 5,000 budget | 4,999 | 32.7 % | 1.0000 / 0.9984 / 0.9964 | 99.5 % | 0.7 mm (0.4) | 0.7 mm | 62 |
| | 25 % | 3,814 | 24.9 % | 0.9999 / 0.9980 / 0.9962 | 99.3 % | 0.9 mm (0.5) | 0.9 mm | 48 |
| | 2,500 budget | 2,496 | 16.3 % | 0.9998 / 0.9965 / 0.9957 | 99.0 % | 1.0 mm (0.6) | 1.0 mm | 33 |
| | 12 % | 1,834 | 12.0 % | 0.9964 / 0.9877 / 0.9885 | 98.6 % | 1.6 mm (1.0) | 1.6 mm | 25 |
| | 6 % | 914 | 6.0 % | 0.9864 / 0.9255 / 0.9737 | 94.2 % | 11.3 mm (6.7) | 11.3 mm | 13 |
| **Chair.glb (the chair test)** | full | 41,921 | 100 % | | | | | |
| | 50 % | 20,956 | 50.0 % | 0.9994 / 0.9992 / 0.9999 | 99.9 % | 1.1 mm (0.2) | 1.8 mm | 247 |
| | 20,000 budget | 19,997 | 47.7 % | 0.9995 / 0.9992 / 0.9999 | 99.9 % | 1.1 mm (0.3) | 2.1 mm | 236 |
| | 25 % | 10,473 | 25.0 % | 0.9974 / 0.9967 / 0.9996 | 99.6 % | 1.6 mm (0.7) | 2.2 mm | 124 |
| | 10,000 budget | 9,997 | 23.8 % | 0.9972 / 0.9967 / 0.9996 | 99.6 % | 1.7 mm (0.7) | 2.4 mm | 118 |
| | 12 % | 5,027 | 12.0 % | 0.9952 / 0.9941 / 0.9987 | 98.9 % | 2.3 mm (1.4) | 2.4 mm | 60 |
| | 5,000 budget | 4,999 | 11.9 % | 0.9952 / 0.9941 / 0.9986 | 98.9 % | 2.0 mm (1.4) | 2.4 mm | 59 |
| | 6 % | 2,513 | 6.0 % | 0.9899 / 0.9870 / 0.9972 | 98.5 % | 4.8 mm (2.4) | 4.8 mm | 30 |
| | 2,500 budget | 2,498 | 6.0 % | 0.9910 / 0.9875 / 0.9973 | 98.5 % | 4.8 mm (2.4) | 4.8 mm | 30 |

## Files (all in `furniture_test/bank_furnished/judge/`)

- **Sheets** (PNG): `visitor_chair01.png`, `visitor_chair02.png`, `stool.png`, `sofa.png`, `banquet.png`,
  `working_table.png`, `side_table.png`, `monitor.png`, `chair_test.png`: the full model and four levels side by side,
  walking distance above, close up below, the triangle count under each. `normals_compare.png`: the three ways of getting
  the normals after slimming, at 100 %.
- **Numbers**: `levels.json` (every level's measures), `picture_diffs.json` (the picture differences, both normal methods),
  `levels_keepnormals.json` (the variant with the exported normals carried through), `spec_totals.json` (the bank at the
  spec), `render_run.json` (the picture run: chip, CPU load).
- **The slimmed levels** for the furnished bank page or the app: `levels/<model>.json` (the level list and the matrix from the
  GLB scene to the model's frame) with `levels/<model>.bin` (positions, then 32-bit indices, per level, in the model's frame:
  front towards +z, footprint centred, base at 0). `levels/visitor_chair02_n.*` is the round stool with its normals carried
  through (used in `normals_compare.png`).
- **Scripts** (each takes its folders as arguments and writes only there; nothing installed, three.js and three-mesh-bvh read
  from `app/node_modules`):
  `node slim_levels.mjs "<project>" "<project>/furniture_test/bank_furnished/judge"` (about 25 min, nearly all of it the gap
  measures), then `node render_cells.mjs "<project>" "<a temp folder>/cells"` (10 s once it has the Edge lock; on 3 Nov it
  waited well over an hour in all for other agents' runs), then `python compose_sheets.py "<temp>/cells" "<judge>" "<judge>"` and
  `python spec_totals.py "<project>" "<judge>"`. The picture cells themselves are kept out of the project.
