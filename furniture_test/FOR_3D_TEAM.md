# Furniture models for the walkthrough test

We want to put your real furniture into the bank branch walkthrough and measure how much detail a browser can carry. So
far one chair has been tested (`Chair.glb`): at full detail it is 41,921 triangles, and a slimmed copy at 12 % looks the
same at walking distance. Now we need a full set.

**Which pieces.** `bank_families_for_3d_team.csv` (opens in Excel) lists the bank's 54 furniture families with their kind,
how many pieces the bank has and the size of each piece in the drawing. All of them is best. If that is too many, the
first 20 rows cover about 150 of the 185 pieces.

**How to export each piece** (3ds Max 2023 or newer: File > Export > glTF, as .glb):
1. **One piece per file, at the origin** (0, 0, 0), not where it stands in your scene.
2. **Front facing Max's -Y** (towards you in the Front view), the way the CAD blocks are drawn.
3. **Base on the ground** (z = 0), real size, no scale left on the object (Reset XForm on a copy).
4. **Materials converted to Physical Material** (or the glTF Material) first. V-Ray and Corona materials come out black.
5. **Keep the UVW mapping**, and let the textures be packed into the .glb.
6. **Name the file after its family**, the first column of the list. If a name is awkward, any name will do, as long as
   you say which family it is.

Send them at full detail; do not slim anything (the test does that). If converting the materials takes too long, send
the models anyway with their texture files: the speed test still works without materials, only the look test does not.
FBX is fine only if .glb is not possible.
