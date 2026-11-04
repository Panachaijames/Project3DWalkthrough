# Feedback on the bank furniture exports

3 Nov 2026, for the 3D team. This is about the eight files for the bank branch (Bangkok Bank Sampeng) in `banquet/` (banquet, monitor, side table, sofa, stool, visitor chair01, visitor chair02, working table) and their export logs. Thank you: they let us try the project's own furniture in the walkthrough for the first time.

## What came through well

- **Real size.** Every model matches its CAD block to within a few millimetres. For example, the working table is 1,801 × 1,000 × 750 mm on a 1,787 × 1,000 mm block.
- **Placed in our bank scene, in the drawing's own coordinates.** This let us tell automatically which piece each file came from: the working table stood 2 mm from its piece, visitor chair01 19 mm from its piece and visitor chair02 36 mm from its piece. From that we could put each model at every piece of its family: 65 pieces from 8 files.
- **Clean meshes and clean exports.** There are no broken triangles, and every export finished with no errors.
- **Mostly light.** Six of the eight are light enough to use as they are (104 to 6,084 triangles).

## What did not

- **Materials:** all 23 materials came out as a black `fallback Material`. The logs don't mention it; their only message is "got document version: 1.38, upgrading to 1.38...", once per material.
- **Textures:** the files have no texture coordinates (UVs) and no textures.
- **visitor chair01 (the mollie chair) is 241,326 triangles and 8.1 MB.** That is 94 % of the triangles in all eight files. At its 19 pieces it comes to 4.6 million, more than twice what a laptop can show for a whole project. We slim it ourselves on import, and at 20,000 it looks the same even close up, so there is no need to make a light version.
- **Scale left on the objects:**
  - 6.406 on visitor chair01;
  - 2.258 on the keyboard;
  - 304.8 on the sofa (a Revit family in feet);
  - 0.95 - 0.98 across and 1.004 up on visitor chair02;
  - one side-table leg mirrored (scale -1).
- **A pivot far from its object:** the working table's pivot is 1.8 m from the table, on the next desk.
- **Three files not on their piece:**
  - the sofa stood 0.47 m from its piece and a quarter turn round;
  - the stool stood where the drawing has a mollie chair;
  - the side table stood on no piece at all.
  So we could not tell from the scene where these three belong.
- **Not the CAD piece:**
  - The banquet is one 3 m bench where the drawing has four 1 m `SOFA_BENCH_DIOR - TYPE 2` modules in a 4 m run.
  - The monitor file holds a screen, a keyboard and a mouse together, and its keyboard sits 0.5 m from where the CAD block draws one. At three counters on level 2 it hangs off the 0.6 m cabinet.
- **Names:** the files are called `sofa`, `stool`, `side table` and so on, and only the sofa's mesh carries its family's name. Which families are the **side table** (its 0.45 × 0.30 m top matches no family in the bank) and the **stool**?

## Please change before the next batch

1. **Materials:** before exporting, convert V-Ray / Corona materials to **Physical Material** (Rendering > Scene Converter), or use the **glTF Material**. If a model comes out black after export, the conversion was missed.
2. **Textures:** keep a **UVW map** on every object and use bitmaps in the material; the GLB packs them into the file. 1024 px maps are enough; use 2048 only for a big piece with its own print.
3. **One CAD family per file, named exactly after the family**, for example `mollie_chair_a685_revit - A685 2.glb`. The names are in `bank_families_for_3d_team.csv`. If a family is drawn as a set (the computer is a screen, a keyboard and a mouse), keep the parts where the CAD block draws them.
4. **At the origin, the way the CAD block is drawn.** We now place every copy by its CAD block (its insertion point, its turn and Revit's flip), so each model should match its block sitting at 0,0,0 and not turned:
   - the block's insertion point (the Revit family's origin) at 0,0,0, with the pivot there too;
   - the front towards -Y (the Front view);
   - the base on the floor (z = 0);
   - no turn.
   Exporting in place worked for this test, but only for the five models that stood exactly on their own piece, and the next project will have a different scene. If exporting in place is much easier for you, it can still work, but only if the model stands exactly on its own CAD block and the file name says which piece it is, for example `... A685 2 @ L1-seat-012.glb`.
5. **No scale and no mirror on the object:** apply Reset XForm on a copy and collapse it before exporting, at real size as now.
6. **Send one file first.** We will check its size, place, materials and textures and reply before you do the rest.

Your originals stay as they are for Max. We keep them in the library and make the light browser copies ourselves.
