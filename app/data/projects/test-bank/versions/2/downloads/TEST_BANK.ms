-- TEST_BANK / built by the walkthrough app from "I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg + I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg", 17 Nov 2026
-- Same model as the version in the walkthrough app (model data 0b36911854fa). Floor levels +0.00 / +3.00 m, wall heights 3.00 / 3.00 m.
-- The drawings were converted with LibreDWG 0.14; drawing units mm.
-- Placed at the drawing's own coordinates in metres (to line up with the drawings imported in metres), or centred on
-- the origin if you untick that box in the script's window.
-- Every part stays LIVE (no Editable Poly): an editable spline outline + an Extrude modifier (output: Mesh) + Smooth.
--   * Change a height: the Extrude amount on that object, or "Update levels and heights" in this script's window.
--   * Change an outline: select the spline level under the modifiers and move vertices.
--   * Editable Mesh: tick "Collapse to Editable Mesh" before Build, or press "Collapse all now" later.
-- Each object's pivot is at the middle of its own outline, on its base. Layers per level and kind (TB_L1_Walls ...).
-- "Update levels and heights" sets the tops of the walls (those marked to), columns, glass (those marked to) and lintels to their level's wall height and keeps
-- the mullions, the railings, the slabs, the ceilings and the parapets at their own heights (only parts marked to follow the wall height change).
-- Glass partitions (Revit glass wall types) are their own objects on TB_<level>_Glass, at the height their type
-- name gives (2600H = 2.60 m).
-- Stairs: Level 1 to Level 2, 18 risers of 0.167 m, 17 treads; Level 1 to Level 2, 21 risers of 0.143 m, 17 treads and 3 landings.
-- Treads and landings are on TB_<level>_Treads and _Landings, on the level the stair rises from; the walls
-- cut under a flight stay on _Walls. "Update levels and heights" scales each stair, and the walls cut under it,
-- with its storey (their user property TB_storey is the level the stair rises to), so a stair still meets
-- the floor above.
-- Ceilings are on hidden layers TB_<level>_Ceilings: switch them on for interior views. A ceiling keeps its
-- height above its level when the levels change.
-- Each part is checked as it is built (closed solid, height, position). A part that fails is kept on layer
-- TB_Check_Failed and listed in the MAXScript Listener; the rest is still built.
-- Build sets System Units to metres. Nothing in an existing scene is changed: run it in a NEW EMPTY scene.
global TB_UI
global TB_nodes = #()
global TB_failed = #()
global TB_levels = #(0.00,3.00)
global TB_heights = #(3.00,3.00)
global TB_floorNames = #("L1","L2")
global TB_collapse = false
global TB_shift = [0.0, 0.0]
global TB_mats
-- Furniture boxes: one coloured placeholder box per furniture piece (colour = kind), on layers TB_<level>_Furn_<Kind>. Type
-- each kind's height in mm in the window, before the build or later with "Apply furniture heights" (boxes on a table, counter or
-- cabinet follow its height). A box is a live Box, never an Editable Poly, and carries the piece's family, block and DWG layer
-- as user properties, so the 3D team can swap it for their own model by family name. A property with nothing to say (no support,
-- no block, no handle) holds the word none, never empty text: 3ds Max does not say what getUserProp returns for empty text.
-- Each box is checked as it is built: base z, top z and its four corners carried through its transform, and the node's min and
-- max in the plan only for an unrotated box (Autodesk does not say what they are for a turned node). A box that fails goes on
-- layer TB_Check_Failed and is listed in the Listener; the rest is still built.
-- "Furniture boxes only" adds just the boxes to a scene already built from this model. Below: the kinds in the model's order,
-- heights and bases in metres.
global TB_furnWant = true
global TB_furnAddOnly = false
global TB_furnFloors = #("L1","L2")
global TB_furnKeys = #("computer","printer","tv","partition","plant","sanitary","seat","sofa","table","coffee-table","cabinet","tall-cabinet","other")
global TB_furnLayers = #("Computer","Printer","Tv","Partition","Plant","Sanitary","Seat","Sofa","Table","CoffeeTable","Cabinet","TallCabinet","Other")
global TB_furnBases = #(0.0000,0.0000,0.9000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000)
global TB_furnHeights = #(0.4500,0.3000,0.6000,1.2000,0.6000,0.8500,0.4500,0.8000,0.7500,0.4500,0.9000,2.1000,0.7500)
global TB_furnLevels = #()
global TB_furnMats = #()

fn TB_layer n =
(
    local ly = LayerManager.getLayerFromName n
    if ly == undefined do ly = LayerManager.newLayerFromName n
    ly
)
fn TB_mat key =
(
    local m = undefined
    for x in TB_mats where x.name == ("TB " + key) do m = x
    m
)
fn TB_makeMaterials =
(
    TB_mats = #()
    append TB_mats (standardMaterial name:"TB Wall" diffuse:(color 227 221 211))
    append TB_mats (standardMaterial name:"TB Glass" diffuse:(color 170 200 214) opacity:30 specularLevel:60 glossiness:60)
    append TB_mats (standardMaterial name:"TB Rail" diffuse:(color 119 114 124))
    append TB_mats (standardMaterial name:"TB Single" diffuse:(color 224 164 88))
    append TB_mats (standardMaterial name:"TB Slab" diffuse:(color 212 216 210))
    append TB_mats (standardMaterial name:"TB Frame" diffuse:(color 93 107 116))
    append TB_mats (standardMaterial name:"TB Step" diffuse:(color 185 199 180))
    append TB_mats (standardMaterial name:"TB Tread" diffuse:(color 185 199 180))
    append TB_mats (standardMaterial name:"TB Landing" diffuse:(color 185 199 180))
    append TB_mats (standardMaterial name:"TB Ceiling" diffuse:(color 244 243 239))
)
fn TB_num v = ((v as string) as float)
-- The outline's knots are relative to c, the middle of the outline; the node is then moved to c, so that is its pivot.
fn TB_shape nm loops =
(
    local o = splineShape name:nm
    for j = 1 to loops.count do
    (
        addNewSpline o
        for p in loops[j] do addKnot o j #corner #line [p.x, p.y, 0]
        close o j
    )
    updateShape o
    o
)
fn TB_extrudeOf o =
(
    local ex = undefined
    for md in o.modifiers where classOf md == Extrude do ex = md
    ex
)
-- kind: #wall #column #lintel #sill #parapet #glass #mullion #railing #single #step #slab; z0/z1 in metres above the
-- level of floor fi (a step of a flight going down from a level starts below it);
-- follow = the top follows that level's wall height. c = pivot, mn/mx = outline extents (DWG coordinates).
fn TB_part kind nm loops z0 z1 follow fi c mn mx =
(
    local info = case kind of
    (
        #wall: #("Walls", "Wall")
        #column: #("Columns", "Wall")
        #lintel: #("Lintels", "Wall")
        #sill: #("Sills", "Wall")
        #parapet: #("Parapets", "Wall")
        #glass: #("Glass", "Glass")
        #mullion: #("GlassFrames", "Frame")
        #railing: #("Railings", "Rail")
        #single: #("SingleLines", "Single")
        #step: #("Steps", "Step")
        #slab: #("Slab", "Slab")
        #tread: #("Treads", "Tread")
        #landing: #("Landings", "Landing")
        #ceiling: #("Ceilings", "Ceiling")
    )
    local lvl = TB_levels[fi]
    local top = if follow then TB_heights[fi] else z1
    local zb = lvl + z0
    local ht = top - z0
    local o = TB_shape nm loops
    o.pos = [c.x - TB_shift.x, c.y - TB_shift.y, zb]
    addModifier o (Extrude amount:ht segs:1 capStart:true capEnd:true output:1 smooth:false)
    addModifier o (Smooth autoSmooth:true threshold:25.0)
    local mt = TB_mat info[2]
    o.material = mt
    o.wirecolor = mt.diffuse
    setUserProp o "TB_kind" (kind as string)
    setUserProp o "TB_floor" fi
    setUserProp o "TB_base" z0
    setUserProp o "TB_follow" follow
    -- the checks run on the evaluated mesh (what the modifiers produce)
    local m = snapshotAsMesh o
    local why = ""
    local tol = 0.002
    if m.numfaces < 3 then why = "no faces"
    else if (meshop.getOpenEdges m).numberSet != 0 then why = "open edges (not a closed solid)"
    else if abs(o.min.z - zb) > tol or abs(o.max.z - (zb + ht)) > tol then why = "height"
    else if abs(o.min.x - (mn.x - TB_shift.x)) > tol or abs(o.min.y - (mn.y - TB_shift.y)) > tol or abs(o.max.x - (mx.x - TB_shift.x)) > tol or abs(o.max.y - (mx.y - TB_shift.y)) > tol then why = "position"
    m = undefined
    if why == "" then
    (
        (TB_layer ("TB_" + TB_floorNames[fi] + "_" + info[1])).addNode o
        setUserProp o "TB_check" "ok"
    )
    else
    (
        (TB_layer "TB_Check_Failed").addNode o
        setUserProp o "TB_check" why
        append TB_failed (nm + ": " + why)
    )
    if TB_collapse do convertToMesh o
    append TB_nodes o
    o
)
-- Stair lines: one shape of open two-knot splines per level and kind, knots relative to c (its pivot).
fn TB_lines nm segs fi c lay =
(
    local o = splineShape name:nm
    for k = 1 to segs.count do
    (
        addNewSpline o
        addKnot o k #corner #line [segs[k][1].x, segs[k][1].y, 0]
        addKnot o k #corner #line [segs[k][2].x, segs[k][2].y, 0]
    )
    updateShape o
    o.pos = [c.x - TB_shift.x, c.y - TB_shift.y, TB_levels[fi]]
    o.wirecolor = if lay == "Stairs" then (color 46 139 71) else (color 160 210 170)
    setUserProp o "TB_floor" fi
    setUserProp o "TB_base" 0.0
    (TB_layer ("TB_" + TB_floorNames[fi] + "_" + lay)).addNode o
    append TB_nodes o
    o
)
fn TB_room nm p fi =
(
    local t = text text:nm size:0.3 pos:[p.x - TB_shift.x, p.y - TB_shift.y, TB_levels[fi] + 0.02]
    t.name = "TB_Room_" + TB_floorNames[fi] + "_" + nm
    t.wirecolor = color 30 60 110
    setUserProp t "TB_floor" fi
    setUserProp t "TB_base" 0.02
    (TB_layer ("TB_" + TB_floorNames[fi] + "_RoomNames")).addNode t
    append TB_nodes t
    t
)
-- After the build: move every part to its level and set every live part whose top follows the wall height to its
-- level's new wall height.
fn TB_updateLevels newLevels newHeights =
(
    local n = 0
    local skipped = 0
    for o in objects where (getUserProp o "TB_floor") != undefined do
    (
        local fi = (TB_num (getUserProp o "TB_floor")) as integer
        local base = TB_num (getUserProp o "TB_base")
        local up = getUserProp o "TB_storey"
        if up != undefined do
        (
            local ui = (TB_num up) as integer
            local d0 = TB_levels[ui] - TB_levels[fi]
            local d1 = newLevels[ui] - newLevels[fi]
            if d0 > 0 and d1 > 0 do
            (
                local s = d1 / (d0 as float)
                local ex = TB_extrudeOf o
                if ex == undefined then skipped += 1 else ex.amount = ex.amount * s
                base = base * s
                setUserProp o "TB_base" base
            )
        )
        o.pos.z = newLevels[fi] + base
        if ((getUserProp o "TB_follow") as string) == "true" do
        (
            local ex = TB_extrudeOf o
            if ex == undefined then skipped += 1
            else ( ex.amount = newHeights[fi] - base; n += 1 )
        )
    )
    TB_levels = newLevels
    TB_heights = newHeights
    #(n, skipped)
)
fn TB_collapseAll =
(
    local n = 0
    for o in objects where (getUserProp o "TB_kind") != undefined and o.modifiers.count > 0 do ( convertToMesh o; n += 1 )
    n
)
-- Furniture boxes: one coloured Box per piece, a placeholder the 3D team swaps for their own model by family name.
-- A box is a live Box (width along its own long axis, length across it, height), never an Editable Poly or Mesh and never
-- collapsed: "Collapse all now" only takes objects that carry TB_kind and a modifier, and a box has neither. Every box
-- carries TB_floor and TB_base (its bottom, in metres above its level) and TB_follow = false, so "Update levels
-- and heights" moves it with its level and leaves its height alone.
fn TB_furnNum v = ((v as string) as float)
fn TB_furnMakeMaterials =
(
    TB_furnMats = #()
    append TB_furnMats (standardMaterial name:"TB Furn computer" diffuse:(color 123 63 181))
    append TB_furnMats (standardMaterial name:"TB Furn printer" diffuse:(color 142 142 142))
    append TB_furnMats (standardMaterial name:"TB Furn tv" diffuse:(color 52 64 143))
    append TB_furnMats (standardMaterial name:"TB Furn partition" diffuse:(color 79 185 159))
    append TB_furnMats (standardMaterial name:"TB Furn plant" diffuse:(color 46 158 79))
    append TB_furnMats (standardMaterial name:"TB Furn sanitary" diffuse:(color 23 162 162))
    append TB_furnMats (standardMaterial name:"TB Furn seat" diffuse:(color 224 123 0))
    append TB_furnMats (standardMaterial name:"TB Furn sofa" diffuse:(color 255 179 71))
    append TB_furnMats (standardMaterial name:"TB Furn table" diffuse:(color 138 90 43))
    append TB_furnMats (standardMaterial name:"TB Furn coffee-table" diffuse:(color 201 163 122))
    append TB_furnMats (standardMaterial name:"TB Furn cabinet" diffuse:(color 47 127 193))
    append TB_furnMats (standardMaterial name:"TB Furn tall-cabinet" diffuse:(color 27 79 138))
    append TB_furnMats (standardMaterial name:"TB Furn other" diffuse:(color 107 107 107))
)
-- The floor levels the build was started with (a copy: nothing is shared with the script's own array).
fn TB_furnSetLevels =
(
    TB_furnLevels = #()
    for z in (TB_levels) do append TB_furnLevels z
)
-- Where a box stands, in metres above its level: on its kind's base, or on top of the kind of support it was drawn on
-- (ki = its kind, oki = the kind of its support, 0 for none). A support never stands on anything.
fn TB_furnZ0 ki oki =
(
    local z0 = TB_furnBases[ki]
    if oki > 0 do z0 = TB_furnBases[oki] + TB_furnHeights[oki]
    z0
)
-- kind = the kind, nm = the object's name, fi = the floor's index, pid = the piece's id, supId and supKind = its support's id
-- and kind ("none" for none), c = the box's centre and cs = its four corners (DWG coordinates), w d = its size along its own
-- long and short axis, ca sa = cos and sin of the angle from +x to the long axis, fam blk lay hnd = family, block, DWG layer,
-- handle ("none" for nothing). The box gets an explicit matrix: its X, Y and Z axes in the world, then its pivot (the middle of
-- its base).
fn TB_furnBox kind nm fi pid supId supKind c w d ca sa cs fam blk lay hnd =
(
    local ki = findItem TB_furnKeys kind
    local z0 = TB_furnZ0 ki (findItem TB_furnKeys supKind)
    local ht = TB_furnHeights[ki]
    local zb = TB_furnLevels[fi] + z0
    local o = box name:nm width:w length:d height:ht
    o.transform = (matrix3 [ca, sa, 0.0] [(0.0 - sa), ca, 0.0] [0.0, 0.0, 1.0] [c.x - TB_shift.x, c.y - TB_shift.y, zb])
    local mt = TB_furnMats[ki]
    o.material = mt
    o.wirecolor = mt.diffuse
    setUserProp o "TB_furn" "true"
    setUserProp o "TB_furnKind" kind
    setUserProp o "TB_furnId" pid
    setUserProp o "TB_furnOn" supId
    setUserProp o "TB_furnOnKind" supKind
    setUserProp o "TB_family" fam
    setUserProp o "TB_block" blk
    setUserProp o "TB_layer" lay
    setUserProp o "TB_handle" hnd
    setUserProp o "TB_floor" fi
    setUserProp o "TB_base" z0
    setUserProp o "TB_follow" false
    -- the checks: base and top z; the world bounding box, but only for an unrotated box (sin of its rotation below 0.00001 and cos
    -- positive: the node's min and max are then certainly the box's own extents; Autodesk does not say what they are for a node that
    -- is turned, a quarter turn included, and a box built right must not go on the failed layer for that); and the four corners
    -- (the box's own corner points carried to the world by its transform) against the corners the generator worked out from the
    -- model, which proves its position, size and rotation for every box
    local why = ""
    local tol = 0.002
    local unrotated = abs(sa) < 0.00001 and ca > 0.0
    local mnx = cs[1].x
    local mxx = cs[1].x
    local mny = cs[1].y
    local mxy = cs[1].y
    for p in cs do
    (
        if p.x < mnx do mnx = p.x
        if p.x > mxx do mxx = p.x
        if p.y < mny do mny = p.y
        if p.y > mxy do mxy = p.y
    )
    if abs(o.min.z - zb) > tol then why = "base z"
    else if abs(o.max.z - (zb + ht)) > tol then why = "top z"
    else if unrotated and (abs(o.min.x - (mnx - TB_shift.x)) > tol or abs(o.min.y - (mny - TB_shift.y)) > tol or abs(o.max.x - (mxx - TB_shift.x)) > tol or abs(o.max.y - (mxy - TB_shift.y)) > tol) then why = "bounding box"
    else
    (
        local hw = o.width / 2.0
        local hd = o.length / 2.0
        local lc = #([(0.0 - hw), (0.0 - hd), 0.0], [hw, (0.0 - hd), 0.0], [hw, hd, 0.0], [(0.0 - hw), hd, 0.0])
        for k = 1 to 4 do
        (
            local q = lc[k] * o.transform
            if why == "" and (abs(q.x - (cs[k].x - TB_shift.x)) > tol or abs(q.y - (cs[k].y - TB_shift.y)) > tol) then why = "corner " + (k as string)
        )
    )
    if why == "" then
    (
        (TB_layer ("TB_" + TB_furnFloors[fi] + "_Furn_" + TB_furnLayers[ki])).addNode o
        setUserProp o "TB_check" "ok"
    )
    else
    (
        (TB_layer "TB_Check_Failed").addNode o
        setUserProp o "TB_check" why
        append TB_failed (nm + ": " + why)
    )
    append TB_nodes o
    o
)
-- Every piece of the model, in the model's order.
fn TB_furnAll =
(
    TB_furnBox "computer" "TB_L1_Furn_computer_001_Enscape AssetDefinition - Computer 003" 1 "L1-computer-001" "L1-table-005" "table" [(-1.5080),4.6920] 0.7370 0.4280 (-0.406577193) 0.913616433 #([(-1.1627),4.4423],[(-1.4623),5.1157],[(-1.8533),4.9417],[(-1.5537),4.2683]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-2278189-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "E28"
    TB_furnBox "computer" "TB_L1_Furn_computer_002_Enscape AssetDefinition - Computer 003" 1 "L1-computer-002" "L1-table-001" "table" [(-1.4110),(-3.6770)] 0.7370 0.4280 (-0.406577193) 0.913616433 #([(-1.0657),(-3.9267)],[(-1.3653),(-3.2533)],[(-1.7563),(-3.4273)],[(-1.4567),(-4.1007)]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-2278189-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1C2C"
    TB_furnBox "computer" "TB_L1_Furn_computer_003_Enscape AssetDefinition - Computer 003" 1 "L1-computer-003" "L1-table-002" "table" [(-1.4110),(-1.8710)] 0.7370 0.4280 (-0.406577193) 0.913616433 #([(-1.0657),(-2.1207)],[(-1.3653),(-1.4473)],[(-1.7563),(-1.6213)],[(-1.4567),(-2.2947)]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-2278189-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1BEB"
    TB_furnBox "computer" "TB_L1_Furn_computer_004_Enscape AssetDefinition - Computer 003" 1 "L1-computer-004" "L1-table-003" "table" [(-1.4110),(-0.0710)] 0.7370 0.4280 (-0.406577193) 0.913616433 #([(-1.0657),(-0.3207)],[(-1.3653),0.3527],[(-1.7563),0.1787],[(-1.4567),(-0.4947)]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-V34-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1812"
    TB_furnBox "computer" "TB_L1_Furn_computer_005_Enscape AssetDefinition - Computer 003" 1 "L1-computer-005" "L1-table-004" "table" [(-1.4110),1.7740] 0.7370 0.4280 (-0.406577193) 0.913616433 #([(-1.0657),1.5243],[(-1.3653),2.1977],[(-1.7563),2.0237],[(-1.4567),1.3503]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-2278189-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1865"
    TB_furnBox "computer" "TB_L1_Furn_computer_006_Enscape AssetDefinition - Computer 003" 1 "L1-computer-006" "L1-table-006" "table" [2.2680,1.6690] 0.7370 0.4280 (-0.406577193) 0.913616433 #([2.6133,1.4193],[2.3137,2.0927],[1.9227,1.9187],[2.2223,1.2453]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-2278189-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "FF1"
    TB_furnBox "computer" "TB_L1_Furn_computer_007_Enscape AssetDefinition - Computer 003" 1 "L1-computer-007" "L1-table-007" "table" [3.6780,1.6690] 0.7370 0.4280 (-0.406577193) 0.913616433 #([4.0233,1.4193],[3.7237,2.0927],[3.3327,1.9187],[3.6323,1.2453]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-2278189-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1B32"
    TB_furnBox "printer" "TB_L1_Furn_printer_001_PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Typ" 1 "L1-printer-001" "none" "none" [(-2.9950),2.6690] 0.2200 0.1700 0.000000000 1.000000000 #([(-2.9100),2.5590],[(-2.9100),2.7790],[(-3.0800),2.7790],[(-3.0800),2.5590]) "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1" "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1-V24-LEVEL 1 GENERAL ARRANGEMENT" "Q-SPCQ" "E3D"
    TB_furnBox "printer" "TB_L1_Furn_printer_002_PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Typ" 1 "L1-printer-002" "none" "none" [(-2.9850),(-3.6510)] 0.4350 0.1900 0.000000000 1.000000000 #([(-2.8900),(-3.8685)],[(-2.8900),(-3.4335)],[(-3.0800),(-3.4335)],[(-3.0800),(-3.8685)]) "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1" "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1-2331658-LEVEL 1 GENERAL ARRANGEMENT" "Q-SPCQ" "A3A"
    TB_furnBox "tv" "TB_L1_Furn_tv_001_IF_J04_WALL TV - WALL TV 3800W" 1 "L1-tv-001" "none" "none" [0.7430,4.6130] 2.0000 0.1400 0.000000000 1.000000000 #([0.8130,3.6130],[0.8130,5.6130],[0.6730,5.6130],[0.6730,3.6130]) "IF_J04_WALL TV - WALL TV 3800W" "IF_J04_WALL TV - WALL TV 3800W-2364417-LEVEL 1 GENERAL ARRANGEMENT" "Q-CASE" "170C"
    TB_furnBox "tv" "TB_L1_Furn_tv_002_APPLIANCE_TV_WALL MOUNT WITH BRACKET - 7" 1 "L1-tv-002" "none" "none" [0.7780,4.6130] 1.6800 0.0500 0.000000000 1.000000000 #([0.8030,3.7730],[0.8030,5.4530],[0.7530,5.4530],[0.7530,3.7730]) "APPLIANCE_TV_WALL MOUNT WITH BRACKET - 75_" "APPLIANCE_TV_WALL MOUNT WITH BRACKET - 75_-2364407-LEVEL 1 GENERAL ARRANGEMENT" "Q-SPCQ" "16B0"
    TB_furnBox "partition" "TB_L1_Furn_partition_001_Steelcase - Height-Adjustable Desk - Pri" 1 "L1-partition-001" "none" "none" [(-1.3800),(-3.1510)] 1.0000 0.0790 1.000000000 0.000000000 #([(-1.8800),(-3.1905)],[(-0.8800),(-3.1905)],[(-0.8800),(-3.1115)],[(-1.8800),(-3.1115)]) "Steelcase - Height-Adjustable Desk - Privacy Screen - Sarto - 30W x 19_5H" "Steelcase - Height-Adjustable Desk - Privacy Screen - Sarto - 30W x 19_5H-2316532-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1B9A"
    TB_furnBox "partition" "TB_L1_Furn_partition_002_Steelcase - Height-Adjustable Desk - Pri" 1 "L1-partition-002" "none" "none" [(-1.3800),(-1.3510)] 1.0000 0.0790 1.000000000 0.000000000 #([(-1.8800),(-1.3905)],[(-0.8800),(-1.3905)],[(-0.8800),(-1.3115)],[(-1.8800),(-1.3115)]) "Steelcase - Height-Adjustable Desk - Privacy Screen - Sarto - 30W x 19_5H" "Steelcase - Height-Adjustable Desk - Privacy Screen - Sarto - 30W x 19_5H-2316532-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "174A"
    TB_furnBox "partition" "TB_L1_Furn_partition_003_Steelcase - Height-Adjustable Desk - Pri" 1 "L1-partition-003" "none" "none" [(-1.3800),0.4490] 1.0000 0.0790 1.000000000 0.000000000 #([(-1.8800),0.4095],[(-0.8800),0.4095],[(-0.8800),0.4885],[(-1.8800),0.4885]) "Steelcase - Height-Adjustable Desk - Privacy Screen - Sarto - 30W x 19_5H" "Steelcase - Height-Adjustable Desk - Privacy Screen - Sarto - 30W x 19_5H-2316532-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1813"
    TB_furnBox "partition" "TB_L1_Furn_partition_004_Steelcase - Height-Adjustable Desk - Pri" 1 "L1-partition-004" "none" "none" [3.2600,1.6190] 1.0000 0.0790 0.000000000 1.000000000 #([3.2995,1.1190],[3.2995,2.1190],[3.2205,2.1190],[3.2205,1.1190]) "Steelcase - Height-Adjustable Desk - Privacy Screen - Sarto - 30W x 19_5H" "Steelcase - Height-Adjustable Desk - Privacy Screen - Sarto - 30W x 19_5H-2316532-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1B33"
    TB_furnBox "plant" "TB_L1_Furn_plant_001_POTTED PLANT - STOOL LOW_VITRA_VISIONA S" 1 "L1-plant-001" "none" "none" [0.7060,(-6.2650)] 0.5570 0.1770 (-0.895401128) 0.445260396 #([0.9948,(-6.3098)],[0.4960,(-6.0618)],[0.4172,(-6.2202)],[0.9160,(-6.4682)]) "POTTED PLANT - STOOL LOW_VITRA_VISIONA STOOL" "POTTED PLANT - STOOL LOW_VITRA_VISIONA STOOL-2422933-LEVEL 1 GENERAL ARRANGEMENT" "Q-CASE" "1262"
    TB_furnBox "plant" "TB_L1_Furn_plant_002_Enscape AssetDefinition - Potted Plant 0" 1 "L1-plant-002" "none" "none" [0.7930,(-5.6580)] 0.9450 0.7820 0.012566040 0.999921044 #([1.1780,(-6.1354)],[1.1899,(-5.1905)],[0.4080,(-5.1806)],[0.3961,(-6.1255)]) "Enscape AssetDefinition - Potted Plant 028 Peace Lily - Enscape AssetDefinition - Potted Plant 028 Peace Lily 2" "Enscape AssetDefinition - Potted Plant 028 Peace Lily - Enscape AssetDefinition - Potted Plant 028 Peace Lily 2-2422935-LEVEL 1 GENERAL ARRANGEMENT" "L-PLNT" "1321"
    TB_furnBox "plant" "TB_L1_Furn_plant_003_Enscape AssetDefinition - Bush 020 Fern" 1 "L1-plant-003" "none" "none" [0.8550,(-6.1630)] 0.6720 0.3500 0.976220396 0.216780392 #([0.5649,(-6.4067)],[1.2209,(-6.2610)],[1.1451,(-5.9193)],[0.4891,(-6.0650)]) "Enscape AssetDefinition - Bush 020 Fern - Enscape AssetDefinition - Bush 020 Fern" "Enscape AssetDefinition - Bush 020 Fern - Enscape AssetDefinition - Bush 020 Fern-2422934-LEVEL 1 GENERAL ARRANGEMENT" "L-PLNT" "127C"
    TB_furnBox "sanitary" "TB_L1_Furn_sanitary_001_Wall-hung vitreous china basin-Meridian" 1 "L1-sanitary-001" "none" "none" [(-4.7360),(-7.5760)] 0.5960 0.4600 (-0.027398240) 0.999624598 #([(-4.4979),(-7.8676)],[(-4.5143),(-7.2718)],[(-4.9741),(-7.2844)],[(-4.9577),(-7.8802)]) "Wall-hung vitreous china basin-Meridian-327242xx0 - 327242000 White" "Wall-hung vitreous china basin-Meridian-327242xx0 - 327242000 White-2274270-LEVEL 1 GENERAL ARRANGEMENT" "P-SANR-FIXT" "none"
    TB_furnBox "sanitary" "TB_L1_Furn_sanitary_002_- C1403 - C1403" 1 "L1-sanitary-002" "none" "none" [(-4.2690),(-8.7040)] 0.6970 0.4060 0.049721374 0.998763128 #([(-4.0836),(-9.0622)],[(-4.0489),(-8.3660)],[(-4.4544),(-8.3458)],[(-4.4891),(-9.0420)]) "- C1403 - C1403" "- C1403 - C1403-2281794-LEVEL 1 GENERAL ARRANGEMENT" "P-SANR-FIXT" "none"
    TB_furnBox "sanitary" "TB_L1_Furn_sanitary_003_C12377 - C12377" 1 "L1-sanitary-003" "none" "none" [1.9430,7.4000] 0.7260 0.4110 0.014834754 0.999889959 #([2.1431,7.0340],[2.1539,7.7599],[1.7429,7.7660],[1.7321,7.0401]) "C12377 - C12377" "C12377 - C12377-2316655-LEVEL 1 GENERAL ARRANGEMENT" "P-SANR-FIXT" "7A7"
    TB_furnBox "sanitary" "TB_L1_Furn_sanitary_004_- C0240 - - C0240" 1 "L1-sanitary-004" "none" "none" [2.9300,8.1000] 0.8460 0.4500 (-0.036120457) 0.999347443 #([3.1701,7.6854],[3.1396,8.5309],[2.6899,8.5146],[2.7204,7.6691]) "- C0240 - - C0240" "- C0240 - - C0240-2329847-LEVEL 1 GENERAL ARRANGEMENT" "P-SANR-FIXT" "7FB"
    TB_furnBox "seat" "TB_L1_Furn_seat_001_HermanMiller_Seating_AER1A_NewAeron_Work" 1 "L1-seat-001" "none" "none" [(-2.1470),(-4.2390)] 0.6130 0.5350 0.000000000 1.000000000 #([(-1.8795),(-4.5455)],[(-1.8795),(-3.9325)],[(-2.4145),(-3.9325)],[(-2.4145),(-4.5455)]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2299212-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1BEE"
    TB_furnBox "seat" "TB_L1_Furn_seat_002_HermanMiller_Seating_AER1A_NewAeron_Work" 1 "L1-seat-002" "none" "none" [(-2.1470),(-2.4320)] 0.6130 0.5350 0.000000000 1.000000000 #([(-1.8795),(-2.7385)],[(-1.8795),(-2.1255)],[(-2.4145),(-2.1255)],[(-2.4145),(-2.7385)]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2299212-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1B9D"
    TB_furnBox "seat" "TB_L1_Furn_seat_003_HermanMiller_Seating_AER1A_NewAeron_Work" 1 "L1-seat-003" "none" "none" [(-2.1470),(-0.6320)] 0.6130 0.5350 0.000000000 1.000000000 #([(-1.8795),(-0.9385)],[(-1.8795),(-0.3255)],[(-2.4145),(-0.3255)],[(-2.4145),(-0.9385)]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2299212-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1752"
    TB_furnBox "seat" "TB_L1_Furn_seat_004_HermanMiller_Seating_AER1A_NewAeron_Work" 1 "L1-seat-004" "none" "none" [(-2.1470),1.1680] 0.6130 0.5350 0.000000000 1.000000000 #([(-1.8795),0.8615],[(-1.8795),1.4745],[(-2.4145),1.4745],[(-2.4145),0.8615]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2299212-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1816"
    TB_furnBox "seat" "TB_L1_Furn_seat_005_HermanMiller_Seating_AER1A_NewAeron_Work" 1 "L1-seat-005" "none" "none" [(-2.1470),4.2120] 0.6130 0.5350 0.000000000 1.000000000 #([(-1.8795),3.9055],[(-1.8795),4.5185],[(-2.4145),4.5185],[(-2.4145),3.9055]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2299212-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "B3D"
    TB_furnBox "seat" "TB_L1_Furn_seat_006_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - 50" 1 "L1-seat-006" "none" "none" [(-0.6140),(-4.6120)] 0.5000 0.5000 0.652495273 0.757792794 #([(-0.5877),(-4.9646)],[(-0.2614),(-4.5857)],[(-0.6403),(-4.2594)],[(-0.9666),(-4.6383)]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - 500W GRAY" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - 500W GRAY-2278169-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1BED"
    TB_furnBox "seat" "TB_L1_Furn_seat_007_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - 50" 1 "L1-seat-007" "none" "none" [(-0.6140),(-2.8050)] 0.5000 0.5000 0.652495273 0.757792794 #([(-0.5877),(-3.1576)],[(-0.2614),(-2.7787)],[(-0.6403),(-2.4524)],[(-0.9666),(-2.8313)]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - 500W GRAY" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - 500W GRAY-2278169-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1B9C"
    TB_furnBox "seat" "TB_L1_Furn_seat_008_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - 50" 1 "L1-seat-008" "none" "none" [(-0.6140),(-1.0050)] 0.5000 0.5000 0.652495273 0.757792794 #([(-0.5877),(-1.3576)],[(-0.2614),(-0.9787)],[(-0.6403),(-0.6524)],[(-0.9666),(-1.0313)]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - 500W GRAY" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - 500W GRAY-2278169-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1751"
    TB_furnBox "seat" "TB_L1_Furn_seat_009_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - 50" 1 "L1-seat-009" "none" "none" [(-0.6140),0.7950] 0.5000 0.5000 0.652495273 0.757792794 #([(-0.5877),0.4424],[(-0.2614),0.8213],[(-0.6403),1.1476],[(-0.9666),0.7687]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - 500W GRAY" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - 500W GRAY-2278169-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1815"
    TB_furnBox "seat" "TB_L1_Furn_seat_010_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 1 "L1-seat-010" "none" "none" [(-0.6040),3.8190] 0.5000 0.5000 0.652495273 0.757792794 #([(-0.5777),3.4664],[(-0.2514),3.8453],[(-0.6303),4.1716],[(-0.9566),3.7927]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE-2337390-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "AD5"
    TB_furnBox "seat" "TB_L1_Furn_seat_011_mollie_chair_a685_revit - A685 2" 1 "L1-seat-011" "none" "none" [(-0.5780),(-3.8840)] 0.5990 0.5630 0.998592754 0.053033118 #([(-0.8621),(-4.1810)],[(-0.2640),(-4.1492)],[(-0.2939),(-3.5870)],[(-0.8920),(-3.6188)]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2278197-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1BEC"
    TB_furnBox "seat" "TB_L1_Furn_seat_012_mollie_chair_a685_revit - A685 2" 1 "L1-seat-012" "none" "none" [(-0.5780),(-2.0780)] 0.5990 0.5630 0.998592754 0.053033118 #([(-0.8621),(-2.3750)],[(-0.2640),(-2.3432)],[(-0.2939),(-1.7810)],[(-0.8920),(-1.8128)]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2278197-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1B9B"
    TB_furnBox "seat" "TB_L1_Furn_seat_013_mollie_chair_a685_revit - A685 2" 1 "L1-seat-013" "none" "none" [(-0.5780),(-0.2780)] 0.5990 0.5630 0.998592754 0.053033118 #([(-0.8621),(-0.5750)],[(-0.2640),(-0.5432)],[(-0.2939),0.0190],[(-0.8920),(-0.0128)]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2278197-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "174B"
    TB_furnBox "seat" "TB_L1_Furn_seat_014_mollie_chair_a685_revit - A685 2" 1 "L1-seat-014" "none" "none" [(-0.5780),1.5220] 0.5990 0.5630 0.998592754 0.053033118 #([(-0.8621),1.2250],[(-0.2640),1.2568],[(-0.2939),1.8190],[(-0.8920),1.7872]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2278197-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1814"
    TB_furnBox "seat" "TB_L1_Furn_seat_015_mollie_chair_a685_revit - A685 2" 1 "L1-seat-015" "none" "none" [(-0.5680),4.6260] 0.5990 0.5630 0.998592754 0.053033118 #([(-0.8521),4.3290],[(-0.2540),4.3608],[(-0.2839),4.9230],[(-0.8820),4.8912]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2278197-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "ACF"
    TB_furnBox "seat" "TB_L1_Furn_seat_016_FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4" 1 "L1-seat-016" "none" "none" [0.8550,(-4.0660)] 0.5700 0.5700 0.991671162 0.128795597 #([0.6091,(-4.3853)],[1.1743,(-4.3119)],[1.1009,(-3.7467)],[0.5357,(-3.8201)]) "FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4" "FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4-2403364-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1063"
    TB_furnBox "seat" "TB_L1_Furn_seat_017_FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4" 1 "L1-seat-017" "none" "none" [0.8550,(-2.8060)] 0.5700 0.5700 0.991671162 0.128795597 #([0.6091,(-3.1253)],[1.1743,(-3.0519)],[1.1009,(-2.4867)],[0.5357,(-2.5601)]) "FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4" "FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4-2403364-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1061"
    TB_furnBox "seat" "TB_L1_Furn_seat_018_FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4" 1 "L1-seat-018" "none" "none" [0.8550,(-2.0860)] 0.5700 0.5700 0.991671162 0.128795597 #([0.6091,(-2.4053)],[1.1743,(-2.3319)],[1.1009,(-1.7667)],[0.5357,(-1.8401)]) "FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4" "FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4-2403364-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1062"
    TB_furnBox "seat" "TB_L1_Furn_seat_019_FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4" 1 "L1-seat-019" "none" "none" [0.8550,(-0.5440)] 0.5700 0.5700 0.995003430 0.099840746 #([0.5999,(-0.8560)],[1.1670,(-0.7991)],[1.1101,(-0.2320)],[0.5430,(-0.2889)]) "FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4" "FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4-2403364-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1060"
    TB_furnBox "seat" "TB_L1_Furn_seat_020_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 1 "L1-seat-020" "none" "none" [1.8370,(-0.9080)] 0.4000 0.4000 0.532580866 0.846379123 #([1.8998,(-1.1838)],[2.1128,(-0.8452)],[1.7742,(-0.6322)],[1.5612,(-0.9708)]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE104 400W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE104 400W BLUE-2572387-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1A86"
    TB_furnBox "seat" "TB_L1_Furn_seat_021_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 1 "L1-seat-021" "none" "none" [2.1830,0.8430] 0.5000 0.5000 0.565974648 0.824422645 #([2.2476,0.4954],[2.5306,0.9076],[2.1184,1.1906],[1.8354,0.7784]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE-2337390-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1001"
    TB_furnBox "seat" "TB_L1_Furn_seat_022_Meeting chair_Haworth_Chair_Very-Task" 1 "L1-seat-022" "none" "none" [2.2600,5.0090] 0.7460 0.5900 0.707106781 0.707106781 #([2.2048,4.5367],[2.7323,5.0642],[2.3152,5.4813],[1.7877,4.9538]) "Meeting chair_Haworth_Chair_Very-Task - SE14 GM CHAIR" "Meeting chair_Haworth_Chair_Very-Task - SE14 GM CHAIR-V36-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "19E8"
    TB_furnBox "seat" "TB_L1_Furn_seat_023_Meeting chair_Haworth_Chair_Very-Task" 1 "L1-seat-023" "none" "none" [2.2670,3.9680] 0.7460 0.5790 (-0.707106781) 0.707106781 #([2.7355,3.9090],[2.2080,4.4365],[1.7985,4.0270],[2.3260,3.4995]) "Meeting chair_Haworth_Chair_Very-Task - SE14 GM CHAIR" "Meeting chair_Haworth_Chair_Very-Task - SE14 GM CHAIR-2352777-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1473"
    TB_furnBox "seat" "TB_L1_Furn_seat_024_mollie_chair_a685_revit - A685 2" 1 "L1-seat-024" "none" "none" [2.3060,(-2.9320)] 0.5990 0.5630 (-0.053033118) 0.998592754 #([2.6030,(-3.2161)],[2.5712,(-2.6180)],[2.0090,(-2.6479)],[2.0408,(-3.2460)]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2278197-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1AF0"
    TB_furnBox "seat" "TB_L1_Furn_seat_025_HermanMiller_Seating_AER1A_NewAeron_Work" 1 "L1-seat-025" "none" "none" [2.5840,2.3850] 0.6130 0.5350 1.000000000 0.000000000 #([2.2775,2.1175],[2.8905,2.1175],[2.8905,2.6525],[2.2775,2.6525]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2299212-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1002"
    TB_furnBox "seat" "TB_L1_Furn_seat_026_mollie_chair_a685_revit - A685 2" 1 "L1-seat-026" "none" "none" [2.6640,(-0.4250)] 0.5990 0.5630 0.494700456 0.869063553 #([2.7605,(-0.8245)],[3.0568,(-0.3040)],[2.5675,(-0.0255)],[2.2712,(-0.5460)]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2437554-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1A8F"
    TB_furnBox "seat" "TB_L1_Furn_seat_027_mollie_chair_a685_revit - A685 2" 1 "L1-seat-027" "none" "none" [2.9910,0.8070] 0.5990 0.5630 (-0.053033118) 0.998592754 #([3.2880,0.5229],[3.2562,1.1210],[2.6940,1.0911],[2.7258,0.4930]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2278197-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1000"
    TB_furnBox "seat" "TB_L1_Furn_seat_028_CHAIR_BENCH BACK - SE107 STOOL LOW_VITRA" 1 "L1-seat-028" "none" "none" [3.1280,(-1.7320)] 1.9000 1.1820 1.000000000 0.000000000 #([2.1780,(-2.3230)],[4.0780,(-2.3230)],[4.0780,(-1.1410)],[2.1780,(-1.1410)]) "CHAIR_BENCH BACK - SE107 STOOL LOW_VITRA_VISIONA STOOL" "CHAIR_BENCH BACK - SE107 STOOL LOW_VITRA_VISIONA STOOL-2475694-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1A3C"
    TB_furnBox "seat" "TB_L1_Furn_seat_029_Meeting chair_Haworth_Chair_Very-Task" 1 "L1-seat-029" "none" "none" [3.3010,5.0020] 0.7460 0.5780 (-0.707106781) 0.707106781 #([3.7691,4.9426],[3.2416,5.4701],[2.8329,5.0614],[3.3604,4.5339]) "Meeting chair_Haworth_Chair_Very-Task - SE14 GM CHAIR" "Meeting chair_Haworth_Chair_Very-Task - SE14 GM CHAIR-2362416-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1587"
    TB_furnBox "seat" "TB_L1_Furn_seat_030_Meeting chair_Haworth_Chair_Very-Task" 1 "L1-seat-030" "none" "none" [3.3080,3.9610] 0.7460 0.5900 0.707106781 0.707106781 #([3.2528,3.4887],[3.7803,4.0162],[3.3632,4.4333],[2.8357,3.9058]) "Meeting chair_Haworth_Chair_Very-Task - SE14 GM CHAIR" "Meeting chair_Haworth_Chair_Very-Task - SE14 GM CHAIR-V31-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "16A2"
    TB_furnBox "seat" "TB_L1_Furn_seat_031_mollie_chair_a685_revit - A685 2" 1 "L1-seat-031" "none" "none" [3.3940,(-2.9680)] 0.5990 0.5630 0.545955743 0.837814017 #([3.4663,(-3.3726)],[3.7934,(-2.8708)],[3.3217,(-2.5634)],[2.9946,(-3.0652)]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2437554-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1A7E"
    TB_furnBox "seat" "TB_L1_Furn_seat_032_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 1 "L1-seat-032" "none" "none" [3.5980,0.8430] 0.5000 0.5000 0.565974648 0.824422645 #([3.6626,0.4954],[3.9456,0.9076],[3.5334,1.1906],[3.2504,0.7784]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE-2337390-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1AF6"
    TB_furnBox "seat" "TB_L1_Furn_seat_033_mollie_chair_a685_revit - A685 2" 1 "L1-seat-033" "none" "none" [3.7540,(-0.3550)] 0.5990 0.5630 (-0.053033118) 0.998592754 #([4.0510,(-0.6391)],[4.0192,(-0.0410)],[3.4570,(-0.0709)],[3.4888,(-0.6690)]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2278197-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1A80"
    TB_furnBox "seat" "TB_L1_Furn_seat_034_HermanMiller_Seating_AER1A_NewAeron_Work" 1 "L1-seat-034" "none" "none" [3.9990,2.3850] 0.6130 0.5350 1.000000000 0.000000000 #([3.6925,2.1175],[4.3055,2.1175],[4.3055,2.6525],[3.6925,2.6525]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2299212-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1AF7"
    TB_furnBox "seat" "TB_L1_Furn_seat_035_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 1 "L1-seat-035" "none" "none" [4.2520,(-2.5660)] 0.4000 0.4000 0.532580866 0.846379123 #([4.3148,(-2.8418)],[4.5278,(-2.5032)],[4.1892,(-2.2902)],[3.9762,(-2.6288)]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE104 400W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE104 400W BLUE-2471981-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1A4B"
    TB_furnBox "seat" "TB_L1_Furn_seat_036_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 1 "L1-seat-036" "none" "none" [4.3000,(-0.9480)] 0.4000 0.4000 0.498336430 0.866983738 #([4.3737,(-1.2211)],[4.5731,(-0.8743)],[4.2263,(-0.6749)],[4.0269,(-1.0217)]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE104 400W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE104 400W BLUE-2471981-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1A4A"
    TB_furnBox "seat" "TB_L1_Furn_seat_037_mollie_chair_a685_revit - A685 2" 1 "L1-seat-037" "none" "none" [4.4060,0.8070] 0.5990 0.5630 (-0.053033118) 0.998592754 #([4.7030,0.5229],[4.6712,1.1210],[4.1090,1.0911],[4.1408,0.4930]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2278197-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1AF5"
    TB_furnBox "sofa" "TB_L1_Furn_sofa_001_SOFA_BENCH_DIOR - TYPE 2" 1 "L1-sofa-001" "none" "none" [5.6720,(-3.1860)] 1.0000 0.7000 0.000000000 1.000000000 #([6.0220,(-3.6860)],[6.0220,(-2.6860)],[5.3220,(-2.6860)],[5.3220,(-3.6860)]) "SOFA_BENCH_DIOR - TYPE 2" "SOFA_BENCH_DIOR - TYPE 2-2572508-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1AA6"
    TB_furnBox "sofa" "TB_L1_Furn_sofa_002_SOFA_BENCH_DIOR - TYPE 2" 1 "L1-sofa-002" "none" "none" [5.6720,(-2.1860)] 1.0000 0.7000 0.000000000 1.000000000 #([6.0220,(-2.6860)],[6.0220,(-1.6860)],[5.3220,(-1.6860)],[5.3220,(-2.6860)]) "SOFA_BENCH_DIOR - TYPE 2" "SOFA_BENCH_DIOR - TYPE 2-V37-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1ABE"
    TB_furnBox "sofa" "TB_L1_Furn_sofa_003_SOFA_BENCH_DIOR - TYPE 2" 1 "L1-sofa-003" "none" "none" [5.6720,(-1.1860)] 1.0000 0.7000 0.000000000 1.000000000 #([6.0220,(-1.6860)],[6.0220,(-0.6860)],[5.3220,(-0.6860)],[5.3220,(-1.6860)]) "SOFA_BENCH_DIOR - TYPE 2" "SOFA_BENCH_DIOR - TYPE 2-V38-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1AD5"
    TB_furnBox "sofa" "TB_L1_Furn_sofa_004_SOFA_BENCH_DIOR - TYPE 2" 1 "L1-sofa-004" "none" "none" [5.6720,(-0.1860)] 1.0000 0.7000 0.000000000 1.000000000 #([6.0220,(-0.6860)],[6.0220,0.3140],[5.3220,0.3140],[5.3220,(-0.6860)]) "SOFA_BENCH_DIOR - TYPE 2" "SOFA_BENCH_DIOR - TYPE 2-V39-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1AEC"
    TB_furnBox "table" "TB_L1_Furn_table_001_IA_J15_WORKING TABLE - 1800W 1000D 750H" 1 "L1-table-001" "none" "none" [(-1.3800),(-4.0900)] 1.8000 1.0000 0.000000000 1.000000000 #([(-0.8800),(-4.9900)],[(-0.8800),(-3.1900)],[(-1.8800),(-3.1900)],[(-1.8800),(-4.9900)]) "IA_J15_WORKING TABLE - 1800W 1000D 750H" "IA_J15_WORKING TABLE - 1800W 1000D 750H-V43-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1C2A"
    TB_furnBox "table" "TB_L1_Furn_table_002_IA_J15_WORKING TABLE - 1800W 1000D 750H" 1 "L1-table-002" "none" "none" [(-1.3800),(-2.2840)] 1.7870 1.0000 0.000000000 1.000000000 #([(-0.8800),(-3.1775)],[(-0.8800),(-1.3905)],[(-1.8800),(-1.3905)],[(-1.8800),(-3.1775)]) "IA_J15_WORKING TABLE - 1800W 1000D 750H" "IA_J15_WORKING TABLE - 1800W 1000D 750H-V42-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1BE9"
    TB_furnBox "table" "TB_L1_Furn_table_003_IA_J15_WORKING TABLE - 1800W 1000D 750H" 1 "L1-table-003" "none" "none" [(-1.3800),(-0.4840)] 1.7870 1.0000 0.000000000 1.000000000 #([(-0.8800),(-1.3775)],[(-0.8800),0.4095],[(-1.8800),0.4095],[(-1.8800),(-1.3775)]) "IA_J15_WORKING TABLE - 1800W 1000D 750H" "IA_J15_WORKING TABLE - 1800W 1000D 750H-V33-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "179F"
    TB_furnBox "table" "TB_L1_Furn_table_004_IA_J15_WORKING TABLE - 1800W 1000D 750H" 1 "L1-table-004" "none" "none" [(-1.3800),1.3200] 1.7930 1.0000 0.000000000 1.000000000 #([(-0.8800),0.4235],[(-0.8800),2.2165],[(-1.8800),2.2165],[(-1.8800),0.4235]) "IA_J15_WORKING TABLE - 1800W 1000D 750H" "IA_J15_WORKING TABLE - 1800W 1000D 750H-V35-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1863"
    TB_furnBox "table" "TB_L1_Furn_table_005_IA_J15_WORKING TABLE - 1800W 1000D 750H" 1 "L1-table-005" "none" "none" [(-1.3800),4.2190] 1.8000 1.0000 0.000000000 1.000000000 #([(-0.8800),3.3190],[(-0.8800),5.1190],[(-1.8800),5.1190],[(-1.8800),3.3190]) "IA_J15_WORKING TABLE - 1800W 1000D 750H" "IA_J15_WORKING TABLE - 1800W 1000D 750H-2337398-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "E72"
    TB_furnBox "table" "TB_L1_Furn_table_006_IA_J15_WORKING TABLE - 1400W 1000D 750H" 1 "L1-table-006" "none" "none" [2.5830,1.6190] 1.4000 1.0000 1.000000000 0.000000000 #([1.8830,1.1190],[3.2830,1.1190],[3.2830,2.1190],[1.8830,2.1190]) "IA_J15_WORKING TABLE - 1400W 1000D 750H" "IA_J15_WORKING TABLE - 1400W 1000D 750H-2278198-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "104B"
    TB_furnBox "table" "TB_L1_Furn_table_007_IA_J15_WORKING TABLE - 1400W 1000D 750H" 1 "L1-table-007" "none" "none" [3.9990,1.6190] 1.3980 1.0000 1.000000000 0.000000000 #([3.3000,1.1190],[4.6980,1.1190],[4.6980,2.1190],[3.3000,2.1190]) "IA_J15_WORKING TABLE - 1400W 1000D 750H" "IA_J15_WORKING TABLE - 1400W 1000D 750H-V40-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1B2C"
    TB_furnBox "coffee-table" "TB_L1_Furn_coffee-table_001_TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 6" 1 "L1-coffee-table-001" "none" "none" [2.2980,(-2.3310)] 0.5000 0.5000 0.738455341 0.674302388 #([2.2820,(-2.6842)],[2.6512,(-2.3470)],[2.3140,(-1.9778)],[1.9448,(-2.3150)]) "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H" "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H-2385305-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1AEF"
    TB_furnBox "coffee-table" "TB_L1_Furn_coffee-table_002_TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 6" 1 "L1-coffee-table-002" "none" "none" [2.3750,(-0.9860)] 0.5000 0.5000 0.380909007 0.924612529 #([2.5109,(-1.3124)],[2.7014,(-0.8501)],[2.2391,(-0.6596)],[2.0486,(-1.1219)]) "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H" "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H-2385305-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1A8E"
    TB_furnBox "coffee-table" "TB_L1_Furn_coffee-table_003_TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 1" 1 "L1-coffee-table-003" "none" "none" [2.7840,4.4850] 1.0000 1.0000 0.855725703 0.517429726 #([2.6149,3.7984],[3.4706,4.3159],[2.9531,5.1716],[2.0974,4.6541]) "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 1000W" "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 1000W-2566611-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "135F"
    TB_furnBox "coffee-table" "TB_L1_Furn_coffee-table_004_TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 6" 1 "L1-coffee-table-004" "none" "none" [3.7610,(-0.9860)] 0.5000 0.5000 0.380909007 0.924612529 #([3.8969,(-1.3124)],[4.0874,(-0.8501)],[3.6251,(-0.6596)],[3.4346,(-1.1219)]) "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H" "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H-2395479-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1A7F"
    TB_furnBox "coffee-table" "TB_L1_Furn_coffee-table_005_TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 6" 1 "L1-coffee-table-005" "none" "none" [3.7730,(-2.4260)] 0.5000 0.5000 0.380909007 0.924612529 #([3.9089,(-2.7524)],[4.0994,(-2.2901)],[3.6371,(-2.0996)],[3.4466,(-2.5619)]) "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H" "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H-2395479-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1A44"
    TB_furnBox "coffee-table" "TB_L1_Furn_coffee-table_006_TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 6" 1 "L1-coffee-table-006" "none" "none" [5.1630,(-2.7010)] 0.5000 0.5000 0.380909007 0.924612529 #([5.2989,(-3.0274)],[5.4894,(-2.5651)],[5.0271,(-2.3746)],[4.8366,(-2.8369)]) "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H" "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H-2385305-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1AEE"
    TB_furnBox "coffee-table" "TB_L1_Furn_coffee-table_007_TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 6" 1 "L1-coffee-table-007" "none" "none" [5.1630,(-0.7210)] 0.5000 0.5000 0.380909007 0.924612529 #([5.2989,(-1.0474)],[5.4894,(-0.5851)],[5.0271,(-0.3946)],[4.8366,(-0.8569)]) "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H" "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H-2385305-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1AED"
    TB_furnBox "cabinet" "TB_L1_Furn_cabinet_001_CONSOLE_CABINET_BAKER - TA13 1800W 400D" 1 "L1-cabinet-001" "none" "none" [0.9630,4.6130] 1.8000 0.3200 0.000000000 1.000000000 #([1.1230,3.7130],[1.1230,5.5130],[0.8030,5.5130],[0.8030,3.7130]) "CONSOLE_CABINET_BAKER - TA13 1800W 400D" "CONSOLE_CABINET_BAKER - TA13 1800W 400D-2569772-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "1B6E"
    TB_furnBox "cabinet" "TB_L1_Furn_cabinet_002_CONSOLE_CABINET_BAKER - TA13 1200W 400D" 1 "L1-cabinet-002" "none" "none" [2.2150,(-8.7430)] 1.2000 0.4000 1.000000000 0.000000000 #([1.6150,(-8.9430)],[2.8150,(-8.9430)],[2.8150,(-8.5430)],[1.6150,(-8.5430)]) "CONSOLE_CABINET_BAKER - TA13 1200W 400D" "CONSOLE_CABINET_BAKER - TA13 1200W 400D-2383324-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "105A"
    TB_furnBox "tall-cabinet" "TB_L1_Furn_tall-cabinet_001_TALL CABINET - TALL CABINET 2800W" 1 "L1-tall-cabinet-001" "none" "none" [(-3.2780),3.7190] 2.8000 0.4050 0.000000000 1.000000000 #([(-3.0755),2.3190],[(-3.0755),5.1190],[(-3.4805),5.1190],[(-3.4805),2.3190]) "TALL CABINET - TALL CABINET 2800W" "TALL CABINET - TALL CABINET 2800W-2337389-LEVEL 1 GENERAL ARRANGEMENT" "Q-CASE" "BDA"
    TB_furnBox "tall-cabinet" "TB_L1_Furn_tall-cabinet_002_TALL CABINET 4200W - TALL CABINET 4200W" 1 "L1-tall-cabinet-002" "none" "none" [(-3.2710),(-1.3940)] 7.2250 0.4190 0.000000000 1.000000000 #([(-3.0615),(-5.0065)],[(-3.0615),2.2185],[(-3.4805),2.2185],[(-3.4805),(-5.0065)]) "TALL CABINET 4200W - TALL CABINET 4200W" "TALL CABINET 4200W - TALL CABINET 4200W-2331846-LEVEL 1 GENERAL ARRANGEMENT" "Q-CASE" "8E6"
    TB_furnBox "computer" "TB_L2_Furn_computer_001_Enscape AssetDefinition - Computer 003" 2 "L2-computer-001" "L2-cabinet-003" "cabinet" [(-3.8910),0.1980] 0.7370 0.4280 0.098277676 0.995159032 #([(-3.7143),(-0.1897)],[(-3.6418),0.5437],[(-4.0677),0.5857],[(-4.1402),(-0.1477)]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-2278189-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "FAE"
    TB_furnBox "computer" "TB_L2_Furn_computer_002_Enscape AssetDefinition - Computer 003" 2 "L2-computer-002" "L2-cabinet-004" "cabinet" [(-3.8910),1.7250] 0.7370 0.4280 0.098277676 0.995159032 #([(-3.7143),1.3373],[(-3.6418),2.0707],[(-4.0677),2.1127],[(-4.1402),1.3793]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-2278189-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "10CA"
    TB_furnBox "computer" "TB_L2_Furn_computer_003_Enscape AssetDefinition - Computer 003" 2 "L2-computer-003" "L2-cabinet-004" "cabinet" [(-3.8910),2.9250] 0.7370 0.4280 0.098277676 0.995159032 #([(-3.7143),2.5373],[(-3.6418),3.2707],[(-4.0677),3.3127],[(-4.1402),2.5793]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-V29-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "10C2"
    TB_furnBox "computer" "TB_L2_Furn_computer_004_Enscape AssetDefinition - Computer 003" 2 "L2-computer-004" "L2-cabinet-007" "cabinet" [(-1.6590),(-4.1770)] 0.7370 0.4280 (-0.406577193) 0.913616433 #([(-1.3137),(-4.4267)],[(-1.6133),(-3.7533)],[(-2.0043),(-3.9273)],[(-1.7047),(-4.6007)]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-2278189-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "ABE"
    TB_furnBox "computer" "TB_L2_Furn_computer_005_Enscape AssetDefinition - Computer 003" 2 "L2-computer-005" "L2-cabinet-007" "cabinet" [(-1.6590),(-2.5020)] 0.7370 0.4280 (-0.406577193) 0.913616433 #([(-1.3137),(-2.7517)],[(-1.6133),(-2.0783)],[(-2.0043),(-2.2523)],[(-1.7047),(-2.9257)]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-2278189-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "ABD"
    TB_furnBox "computer" "TB_L2_Furn_computer_006_Enscape AssetDefinition - Computer 003" 2 "L2-computer-006" "L2-cabinet-007" "cabinet" [(-1.6590),(-0.4270)] 0.7370 0.4280 (-0.406577193) 0.913616433 #([(-1.3137),(-0.6767)],[(-1.6133),(-0.0033)],[(-2.0043),(-0.1773)],[(-1.7047),(-0.8507)]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-2278189-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "ABC"
    TB_furnBox "computer" "TB_L2_Furn_computer_007_Enscape AssetDefinition - Computer 003" 2 "L2-computer-007" "L2-cabinet-007" "cabinet" [(-1.6590),1.2480] 0.7370 0.4280 (-0.406577193) 0.913616433 #([(-1.3137),0.9983],[(-1.6133),1.6717],[(-2.0043),1.4977],[(-1.7047),0.8243]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-2278189-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "ABB"
    TB_furnBox "computer" "TB_L2_Furn_computer_008_Enscape AssetDefinition - Computer 003" 2 "L2-computer-008" "L2-table-001" "table" [(-1.6590),3.3350] 0.7370 0.4280 (-0.406577193) 0.913616433 #([(-1.3137),3.0853],[(-1.6133),3.7587],[(-2.0043),3.5847],[(-1.7047),2.9113]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-2278189-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "E47"
    TB_furnBox "computer" "TB_L2_Furn_computer_009_Enscape AssetDefinition - Computer 003" 2 "L2-computer-009" "L2-table-002" "table" [0.8370,5.6270] 0.7370 0.4280 0.913616433 0.406577193 #([0.5873,5.2817],[1.2607,5.5813],[1.0867,5.9723],[0.4133,5.6727]) "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003-V40-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "1764"
    TB_furnBox "printer" "TB_L2_Furn_printer_001_PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Typ" 2 "L2-printer-001" "L2-cabinet-004" "cabinet" [(-3.8480),4.1900] 0.5700 0.4350 0.000000000 1.000000000 #([(-3.6305),3.9050],[(-3.6305),4.4750],[(-4.0655),4.4750],[(-4.0655),3.9050]) "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1" "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1-V28-LEVEL 2 GENERAL ARRANGEMENT" "Q-SPCQ" "1068"
    TB_furnBox "printer" "TB_L2_Furn_printer_002_PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Typ" 2 "L2-printer-002" "L2-cabinet-005" "cabinet" [(-2.9550),(-3.7300)] 0.2200 0.1700 0.000000000 1.000000000 #([(-2.8700),(-3.8400)],[(-2.8700),(-3.6200)],[(-3.0400),(-3.6200)],[(-3.0400),(-3.8400)]) "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1" "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1-2331658-LEVEL 2 GENERAL ARRANGEMENT" "Q-SPCQ" "DCE"
    TB_furnBox "printer" "TB_L2_Furn_printer_003_PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Typ" 2 "L2-printer-003" "L2-cabinet-005" "cabinet" [(-2.9550),(-1.7800)] 0.2200 0.1700 0.000000000 1.000000000 #([(-2.8700),(-1.8900)],[(-2.8700),(-1.6700)],[(-3.0400),(-1.6700)],[(-3.0400),(-1.8900)]) "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1" "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1-2331658-LEVEL 2 GENERAL ARRANGEMENT" "Q-SPCQ" "DCF"
    TB_furnBox "printer" "TB_L2_Furn_printer_004_PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Typ" 2 "L2-printer-004" "L2-cabinet-005" "cabinet" [(-2.9550),0.1700] 0.2200 0.1700 0.000000000 1.000000000 #([(-2.8700),0.0600],[(-2.8700),0.2800],[(-3.0400),0.2800],[(-3.0400),0.0600]) "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1" "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1-2331658-LEVEL 2 GENERAL ARRANGEMENT" "Q-SPCQ" "DCD"
    TB_furnBox "printer" "TB_L2_Furn_printer_005_PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Typ" 2 "L2-printer-005" "none" "none" [(-0.6730),6.6490] 0.4350 0.2100 0.000000000 1.000000000 #([(-0.5680),6.4315],[(-0.5680),6.8665],[(-0.7780),6.8665],[(-0.7780),6.4315]) "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1" "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1-2483475-LEVEL 2 GENERAL ARRANGEMENT" "Q-SPCQ" "168C"
    TB_furnBox "plant" "TB_L2_Furn_plant_001_Enscape AssetDefinition - Potted Plant 0" 2 "L2-plant-001" "none" "none" [2.5160,6.6270] 0.5570 0.5310 0.028270567 0.999600308 #([2.7735,6.3411],[2.7893,6.8979],[2.2585,6.9129],[2.2427,6.3561]) "Enscape AssetDefinition - Potted Plant 011 Epipremnum - Enscape AssetDefinition - Potted Plant 011 Epipremnum" "Enscape AssetDefinition - Potted Plant 011 Epipremnum - Enscape AssetDefinition - Potted Plant 011 Epipremnum-2609662-LEVEL 2 GENERAL ARRANGEMENT" "L-PLNT" "23F6"
    TB_furnBox "plant" "TB_L2_Furn_plant_002_Enscape AssetDefinition - Vase 003 Herac" 2 "L2-plant-002" "L2-coffee-table-003" "coffee-table" [4.3270,2.8790] 0.3530 0.1970 0.915030086 0.403385600 #([4.2052,2.7177],[4.5282,2.8601],[4.4488,3.0403],[4.1258,2.8979]) "Enscape AssetDefinition - Vase 003 Heracleum - Enscape AssetDefinition - Vase 003 Heracleum" "Enscape AssetDefinition - Vase 003 Heracleum - Enscape AssetDefinition - Vase 003 Heracleum-V53-LEVEL 2 GENERAL ARRANGEMENT" "L-PLNT" "22D4"
    TB_furnBox "plant" "TB_L2_Furn_plant_003_Enscape AssetDefinition - Vase 003 Herac" 2 "L2-plant-003" "L2-coffee-table-005" "coffee-table" [4.5670,(-2.6990)] 0.3530 0.1970 (-0.915030086) 0.403385600 #([4.7682,(-2.6801)],[4.4452,(-2.5377)],[4.3658,(-2.7179)],[4.6888,(-2.8603)]) "Enscape AssetDefinition - Vase 003 Heracleum - Enscape AssetDefinition - Vase 003 Heracleum" "Enscape AssetDefinition - Vase 003 Heracleum - Enscape AssetDefinition - Vase 003 Heracleum-2471975-LEVEL 2 GENERAL ARRANGEMENT" "L-PLNT" "13D4"
    TB_furnBox "plant" "TB_L2_Furn_plant_004_Enscape AssetDefinition - Vase 003 Herac" 2 "L2-plant-004" "L2-coffee-table-006" "coffee-table" [5.4100,0.0540] 0.3530 0.1970 (-0.403385600) 0.915030086 #([5.5713,(-0.0678)],[5.4289,0.2552],[5.2487,0.1758],[5.3911,(-0.1472)]) "Enscape AssetDefinition - Vase 003 Heracleum - Enscape AssetDefinition - Vase 003 Heracleum" "Enscape AssetDefinition - Vase 003 Heracleum - Enscape AssetDefinition - Vase 003 Heracleum-2475695-LEVEL 2 GENERAL ARRANGEMENT" "L-PLNT" "1338"
    TB_furnBox "sanitary" "TB_L2_Furn_sanitary_001_COTTO Two piece toilet Elzra C13920 _1" 2 "L2-sanitary-001" "none" "none" [(-5.1530),10.2840] 0.6650 0.3660 (-0.998954674) 0.045711692 #([(-4.8125),10.4516],[(-5.4768),10.4820],[(-5.4935),10.1164],[(-4.8292),10.0860]) "COTTO Two piece toilet Elzra C13920 _1_ - COTTO Two piece toilet Elzra C13920" "COTTO Two piece toilet Elzra C13920 _1_ - COTTO Two piece toilet Elzra C13920-2270619-LEVEL 2 GENERAL ARRANGEMENT" "P-SANR-FIXT" "none"
    TB_furnBox "sanitary" "TB_L2_Furn_sanitary_002_COTTO Two piece toilet Elzra C13920 _1" 2 "L2-sanitary-002" "none" "none" [(-5.1530),11.1140] 0.6650 0.3660 (-0.998954674) 0.045711692 #([(-4.8125),11.2816],[(-5.4768),11.3120],[(-5.4935),10.9464],[(-4.8292),10.9160]) "COTTO Two piece toilet Elzra C13920 _1_ - COTTO Two piece toilet Elzra C13920" "COTTO Two piece toilet Elzra C13920 _1_ - COTTO Two piece toilet Elzra C13920-2270619-LEVEL 2 GENERAL ARRANGEMENT" "P-SANR-FIXT" "none"
    TB_furnBox "sanitary" "TB_L2_Furn_sanitary_003_Wall-hung vitreous china basin-Meridian" 2 "L2-sanitary-003" "none" "none" [(-2.0080),11.0880] 0.5960 0.4600 0.000000000 1.000000000 #([(-1.7780),10.7900],[(-1.7780),11.3860],[(-2.2380),11.3860],[(-2.2380),10.7900]) "Wall-hung vitreous china basin-Meridian-327242xx0 - 327242000 White" "Wall-hung vitreous china basin-Meridian-327242xx0 - 327242000 White-2576848-LEVEL 2 GENERAL ARRANGEMENT" "P-SANR-FIXT" "none"
    TB_furnBox "sanitary" "TB_L2_Furn_sanitary_004_Wall-hung vitreous china basin-Meridian" 2 "L2-sanitary-004" "none" "none" [(-1.4480),11.0880] 0.5960 0.4600 0.000000000 1.000000000 #([(-1.2180),10.7900],[(-1.2180),11.3860],[(-1.6780),11.3860],[(-1.6780),10.7900]) "Wall-hung vitreous china basin-Meridian-327242xx0 - 327242000 White" "Wall-hung vitreous china basin-Meridian-327242xx0 - 327242000 White-2274270-LEVEL 2 GENERAL ARRANGEMENT" "P-SANR-FIXT" "none"
    TB_furnBox "sanitary" "TB_L2_Furn_sanitary_005_COTTO Wall hung urinal Natasha C313BI _1" 2 "L2-sanitary-005" "none" "none" [(-0.1180),9.8630] 0.3300 0.3150 1.000000000 0.000000000 #([(-0.2830),9.7055],[0.0470,9.7055],[0.0470,10.0205],[(-0.2830),10.0205]) "COTTO Wall hung urinal Natasha C313BI _1_ - COTTO Wall hung urinal Natasha C313BI" "COTTO Wall hung urinal Natasha C313BI _1_ - COTTO Wall hung urinal Natasha C313BI-2279716-LEVEL 2 GENERAL ARRANGEMENT" "P-SANR-FIXT" "none"
    TB_furnBox "sanitary" "TB_L2_Furn_sanitary_006_COTTO Two piece toilet Elzra C13920 _1" 2 "L2-sanitary-006" "none" "none" [0.8400,10.4630] 0.6600 0.3650 0.000000000 1.000000000 #([1.0225,10.1330],[1.0225,10.7930],[0.6575,10.7930],[0.6575,10.1330]) "COTTO Two piece toilet Elzra C13920 _1_ - COTTO Two piece toilet Elzra C13920" "COTTO Two piece toilet Elzra C13920 _1_ - COTTO Two piece toilet Elzra C13920-V6-LEVEL 2 GENERAL ARRANGEMENT" "P-SANR-FIXT" "none"
    TB_furnBox "seat" "TB_L2_Furn_seat_001_HermanMiller_Seating_AER1A_NewAeron_Work" 2 "L2-seat-001" "none" "none" [(-4.5080),0.2160] 0.6130 0.5460 0.000000000 1.000000000 #([(-4.2350),(-0.0905)],[(-4.2350),0.5225],[(-4.7810),0.5225],[(-4.7810),(-0.0905)]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2299212-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "FAD"
    TB_furnBox "seat" "TB_L2_Furn_seat_002_HermanMiller_Seating_AER1A_NewAeron_Work" 2 "L2-seat-002" "none" "none" [(-4.5080),1.7360] 0.6130 0.5460 0.000000000 1.000000000 #([(-4.2350),1.4295],[(-4.2350),2.0425],[(-4.7810),2.0425],[(-4.7810),1.4295]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2299212-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "10C9"
    TB_furnBox "seat" "TB_L2_Furn_seat_003_HermanMiller_Seating_AER1A_NewAeron_Work" 2 "L2-seat-003" "none" "none" [(-4.5080),2.9360] 0.6130 0.5460 0.000000000 1.000000000 #([(-4.2350),2.6295],[(-4.2350),3.2425],[(-4.7810),3.2425],[(-4.7810),2.6295]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2299212-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "101F"
    TB_furnBox "seat" "TB_L2_Furn_seat_004_HermanMiller_Seating_AER1A_NewAeron_Work" 2 "L2-seat-004" "none" "none" [(-2.3880),(-4.5430)] 0.6130 0.5460 0.000000000 1.000000000 #([(-2.1150),(-4.8495)],[(-2.1150),(-4.2365)],[(-2.6610),(-4.2365)],[(-2.6610),(-4.8495)]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2437551-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "A0C"
    TB_furnBox "seat" "TB_L2_Furn_seat_005_HermanMiller_Seating_AER1A_NewAeron_Work" 2 "L2-seat-005" "none" "none" [(-2.3880),(-2.8680)] 0.6130 0.5460 0.000000000 1.000000000 #([(-2.1150),(-3.1745)],[(-2.1150),(-2.5615)],[(-2.6610),(-2.5615)],[(-2.6610),(-3.1745)]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2437551-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "A0B"
    TB_furnBox "seat" "TB_L2_Furn_seat_006_HermanMiller_Seating_AER1A_NewAeron_Work" 2 "L2-seat-006" "none" "none" [(-2.3880),(-0.7930)] 0.6130 0.5460 0.000000000 1.000000000 #([(-2.1150),(-1.0995)],[(-2.1150),(-0.4865)],[(-2.6610),(-0.4865)],[(-2.6610),(-1.0995)]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2437551-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "A0A"
    TB_furnBox "seat" "TB_L2_Furn_seat_007_HermanMiller_Seating_AER1A_NewAeron_Work" 2 "L2-seat-007" "none" "none" [(-2.3880),0.8820] 0.6130 0.5460 0.000000000 1.000000000 #([(-2.1150),0.5755],[(-2.1150),1.1885],[(-2.6610),1.1885],[(-2.6610),0.5755]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2437551-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "A09"
    TB_furnBox "seat" "TB_L2_Furn_seat_008_HermanMiller_Seating_AER1A_NewAeron_Work" 2 "L2-seat-008" "none" "none" [(-2.3880),2.9690] 0.6130 0.5460 0.000000000 1.000000000 #([(-2.1150),2.6625],[(-2.1150),3.2755],[(-2.6610),3.2755],[(-2.6610),2.6625]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2437551-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "E44"
    TB_furnBox "seat" "TB_L2_Furn_seat_009_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 2 "L2-seat-009" "none" "none" [(-0.7640),(-4.1000)] 0.5000 0.5000 0.996025535 0.089068137 #([(-0.9907),(-4.3713)],[(-0.4927),(-4.3267)],[(-0.5373),(-3.8287)],[(-1.0353),(-3.8733)]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE-2437550-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "A60"
    TB_furnBox "seat" "TB_L2_Furn_seat_010_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 2 "L2-seat-010" "none" "none" [(-0.7640),(-2.6250)] 0.5000 0.5000 0.996025535 0.089068137 #([(-0.9907),(-2.8963)],[(-0.4927),(-2.8517)],[(-0.5373),(-2.3537)],[(-1.0353),(-2.3983)]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE-2437550-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "A40"
    TB_furnBox "seat" "TB_L2_Furn_seat_011_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 2 "L2-seat-011" "none" "none" [(-0.7640),(-0.2300)] 0.5000 0.5000 0.652495273 0.757792794 #([(-0.7377),(-0.5826)],[(-0.4114),(-0.2037)],[(-0.7903),0.1226],[(-1.1166),(-0.2563)]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE-2437550-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "A5E"
    TB_furnBox "seat" "TB_L2_Furn_seat_012_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 2 "L2-seat-012" "none" "none" [(-0.7640),1.1700] 0.5000 0.5000 0.652495273 0.757792794 #([(-0.7377),0.8174],[(-0.4114),1.1963],[(-0.7903),1.5226],[(-1.1166),1.1437]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE-2437550-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "9A1"
    TB_furnBox "seat" "TB_L2_Furn_seat_013_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 2 "L2-seat-013" "none" "none" [(-0.7640),3.2580] 0.5000 0.5000 0.652495273 0.757792794 #([(-0.7377),2.9054],[(-0.4114),3.2843],[(-0.7903),3.6106],[(-1.1166),3.2317]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE-2437550-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "E43"
    TB_furnBox "seat" "TB_L2_Furn_seat_014_mollie_chair_a685_revit - A685 2" 2 "L2-seat-014" "none" "none" [(-0.7280),(-4.8070)] 0.5990 0.5630 (-0.998592754) 0.053033118 #([(-0.4140),(-4.5418)],[(-1.0121),(-4.5100)],[(-1.0420),(-5.0722)],[(-0.4439),(-5.1040)]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2437554-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "A61"
    TB_furnBox "seat" "TB_L2_Furn_seat_015_mollie_chair_a685_revit - A685 2" 2 "L2-seat-015" "none" "none" [(-0.7280),(-3.3320)] 0.5990 0.5630 (-0.998592754) 0.053033118 #([(-0.4140),(-3.0668)],[(-1.0121),(-3.0350)],[(-1.0420),(-3.5972)],[(-0.4439),(-3.6290)]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2437554-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "A41"
    TB_furnBox "seat" "TB_L2_Furn_seat_016_mollie_chair_a685_revit - A685 2" 2 "L2-seat-016" "none" "none" [(-0.7280),(-0.9370)] 0.5990 0.5630 (-0.998592754) 0.053033118 #([(-0.4140),(-0.6718)],[(-1.0121),(-0.6400)],[(-1.0420),(-1.2022)],[(-0.4439),(-1.2340)]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2437554-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "A5F"
    TB_furnBox "seat" "TB_L2_Furn_seat_017_mollie_chair_a685_revit - A685 2" 2 "L2-seat-017" "none" "none" [(-0.7280),0.4630] 0.5990 0.5630 (-0.998592754) 0.053033118 #([(-0.4140),0.7282],[(-1.0121),0.7600],[(-1.0420),0.1978],[(-0.4439),0.1660]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2437554-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "A3F"
    TB_furnBox "seat" "TB_L2_Furn_seat_018_mollie_chair_a685_revit - A685 2" 2 "L2-seat-018" "none" "none" [(-0.7280),2.5500] 0.5990 0.5630 (-0.998592754) 0.053033118 #([(-0.4140),2.8152],[(-1.0121),2.8470],[(-1.0420),2.2848],[(-0.4439),2.2530]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2437554-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "E45"
    TB_furnBox "seat" "TB_L2_Furn_seat_019_mollie_chair_a685_revit - A685 2" 2 "L2-seat-019" "none" "none" [0.0520,4.6010] 0.5990 0.5630 0.053033118 0.998592754 #([0.3172,4.2870],[0.3490,4.8851],[(-0.2132),4.9150],[(-0.2450),4.3169]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2437554-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "1709"
    TB_furnBox "seat" "TB_L2_Furn_seat_020_HermanMiller_Seating_AER1A_NewAeron_Work" 2 "L2-seat-020" "none" "none" [0.2910,6.2600] 0.6130 0.5460 1.000000000 0.000000000 #([(-0.0155),5.9870],[0.5975,5.9870],[0.5975,6.5330],[(-0.0155),6.5330]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range-2437551-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "1708"
    TB_furnBox "seat" "TB_L2_Furn_seat_021_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 2 "L2-seat-021" "none" "none" [0.7590,4.6370] 0.5000 0.5000 0.267574730 0.963537111 #([0.9330,4.3292],[1.0668,4.8110],[0.5850,4.9448],[0.4512,4.4630]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE-2437550-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "1707"
    TB_furnBox "seat" "TB_L2_Furn_seat_022_CHAIR_BENCH BACK - SE107 STOOL LOW_VITRA" 2 "L2-seat-022" "none" "none" [2.8610,(-5.3900)] 1.9000 1.2000 0.000000000 1.000000000 #([3.4610,(-6.3400)],[3.4610,(-4.4400)],[2.2610,(-4.4400)],[2.2610,(-6.3400)]) "CHAIR_BENCH BACK - SE107 STOOL LOW_VITRA_VISIONA STOOL" "CHAIR_BENCH BACK - SE107 STOOL LOW_VITRA_VISIONA STOOL-2471969-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "1217"
    TB_furnBox "seat" "TB_L2_Furn_seat_023_FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4" 2 "L2-seat-023" "none" "none" [2.9950,5.5030] 0.5700 0.5700 0.103486945 0.994630812 #([3.2490,5.1900],[3.3080,5.7570],[2.7410,5.8160],[2.6820,5.2490]) "FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4" "FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4-2403364-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "2346"
    TB_furnBox "seat" "TB_L2_Furn_seat_024_mollie_chair_a685_revit - A685 2" 2 "L2-seat-024" "none" "none" [3.7240,(-8.6550)] 0.5990 0.5630 (-0.998592754) 0.053033118 #([4.0380,(-8.3898)],[3.4399,(-8.3580)],[3.4100,(-8.9202)],[4.0081,(-8.9520)]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2437554-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "127F"
    TB_furnBox "seat" "TB_L2_Furn_seat_025_CHAIR_BENCH BACK - SE107 STOOL LOW_VITRA" 2 "L2-seat-025" "none" "none" [4.3580,(-6.6120)] 1.9000 1.2000 1.000000000 0.000000000 #([3.4080,(-7.2120)],[5.3080,(-7.2120)],[5.3080,(-6.0120)],[3.4080,(-6.0120)]) "CHAIR_BENCH BACK - SE107 STOOL LOW_VITRA_VISIONA STOOL" "CHAIR_BENCH BACK - SE107 STOOL LOW_VITRA_VISIONA STOOL-2475694-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "126E"
    TB_furnBox "seat" "TB_L2_Furn_seat_026_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 2 "L2-seat-026" "none" "none" [4.4750,(-5.4460)] 0.4000 0.4000 0.955329958 0.295541318 #([4.3430,(-5.6962)],[4.7252,(-5.5780)],[4.6070,(-5.1958)],[4.2248,(-5.3140)]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE104 400W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE104 400W BLUE-2471981-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "1275"
    TB_furnBox "seat" "TB_L2_Furn_seat_027_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 2 "L2-seat-027" "none" "none" [4.8580,(-7.5800)] 0.4000 0.4000 0.532580866 0.846379123 #([4.9208,(-7.8558)],[5.1338,(-7.5172)],[4.7952,(-7.3042)],[4.5822,(-7.6428)]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE104 400W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE104 400W BLUE-2471981-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "1276"
    TB_furnBox "seat" "TB_L2_Furn_seat_028_mollie_chair_a685_revit - A685 2" 2 "L2-seat-028" "none" "none" [5.0730,(-8.6550)] 0.5990 0.5630 0.998592754 0.053033118 #([4.7889,(-8.9520)],[5.3870,(-8.9202)],[5.3571,(-8.3580)],[4.7590,(-8.3898)]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-2278197-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "12B2"
    TB_furnBox "seat" "TB_L2_Furn_seat_029_BENCH-INSTANCE GENERIC - TYPE 1" 2 "L2-seat-029" "none" "none" [5.9850,0.5380] 0.9350 0.5510 (-0.028445030) 0.999595358 #([6.2737,0.0785],[6.2471,1.0131],[5.6963,0.9975],[5.7229,0.0629]) "BENCH-INSTANCE GENERIC - TYPE 1" "BENCH-INSTANCE GENERIC - TYPE 1-2598774-LEVEL 2 GENERAL ARRANGEMENT" "Q-CASE" "1D51"
    TB_furnBox "seat" "TB_L2_Furn_seat_030_BENCH-INSTANCE GENERIC - TYPE 1" 2 "L2-seat-030" "none" "none" [6.0120,(-0.3980)] 0.9350 0.5510 (-0.028445030) 0.999595358 #([6.3007,(-0.8575)],[6.2741,0.0771],[5.7233,0.0615],[5.7499,(-0.8731)]) "BENCH-INSTANCE GENERIC - TYPE 1" "BENCH-INSTANCE GENERIC - TYPE 1-V47-LEVEL 2 GENERAL ARRANGEMENT" "Q-CASE" "2251"
    TB_furnBox "sofa" "TB_L2_Furn_sofa_001_SOFA_03_1 - 1500W x 400D SE18" 2 "L2-sofa-001" "none" "none" [0.8550,(-1.6510)] 1.5500 0.4500 0.000000000 1.000000000 #([1.0800,(-2.4260)],[1.0800,(-0.8760)],[0.6300,(-0.8760)],[0.6300,(-2.4260)]) "SOFA_03_1 - 1500W x 400D SE18" "SOFA_03_1 - 1500W x 400D SE18-V41-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "179C"
    TB_furnBox "sofa" "TB_L2_Furn_sofa_002_SOFA_03_1 - 1500W x 400D SE18" 2 "L2-sofa-002" "none" "none" [0.8550,1.6490] 1.5500 0.4500 0.000000000 1.000000000 #([1.0800,0.8740],[1.0800,2.4240],[0.6300,2.4240],[0.6300,0.8740]) "SOFA_03_1 - 1500W x 400D SE18" "SOFA_03_1 - 1500W x 400D SE18-2492731-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "1783"
    TB_furnBox "sofa" "TB_L2_Furn_sofa_003_SOFA_BENCH_DIOR - TYPE 1" 2 "L2-sofa-003" "none" "none" [3.6070,6.5490] 1.5000 0.7000 1.000000000 0.000000000 #([2.8570,6.1990],[4.3570,6.1990],[4.3570,6.8990],[2.8570,6.8990]) "SOFA_BENCH_DIOR - TYPE 1" "SOFA_BENCH_DIOR - TYPE 1-2479320-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "233E"
    TB_furnBox "sofa" "TB_L2_Furn_sofa_004_Etta Armchair1 - TYPE 2" 2 "L2-sofa-004" "none" "none" [4.3190,5.4230] 0.6930 0.6440 (-0.707106781) 0.707106781 #([4.7917,5.4057],[4.3017,5.8957],[3.8463,5.4403],[4.3363,4.9503]) "Etta Armchair1 - TYPE 2" "Etta Armchair1 - TYPE 2-2606587-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "2340"
    TB_furnBox "sofa" "TB_L2_Furn_sofa_005_Etta Armchair1 - TYPE 2" 2 "L2-sofa-005" "none" "none" [4.6250,(-0.7140)] 0.6930 0.6440 0.735506121 0.677518078 #([4.5883,(-1.1856)],[5.0980,(-0.7161)],[4.6617,(-0.2424)],[4.1520,(-0.7119)]) "Etta Armchair1 - TYPE 2" "Etta Armchair1 - TYPE 2-2607583-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "2323"
    TB_furnBox "sofa" "TB_L2_Furn_sofa_006_Etta Armchair1 - TYPE 2" 2 "L2-sofa-006" "none" "none" [4.6250,0.7870] 0.6930 0.6440 (-0.735506121) 0.677518078 #([5.0980,0.7891],[4.5883,1.2586],[4.1520,0.7849],[4.6617,0.3154]) "Etta Armchair1 - TYPE 2" "Etta Armchair1 - TYPE 2-2606587-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "2309"
    TB_furnBox "table" "TB_L2_Furn_table_001_WORKING TABLE - WORKING TABLE" 2 "L2-table-001" "none" "none" [(-1.5400),2.7640] 2.0870 1.0000 0.000000000 1.000000000 #([(-1.0400),1.7205],[(-1.0400),3.8075],[(-2.0400),3.8075],[(-2.0400),1.7205]) "WORKING TABLE - WORKING TABLE" "WORKING TABLE - WORKING TABLE-2446851-LEVEL 2 GENERAL ARRANGEMENT" "Q-CASE" "E42"
    TB_furnBox "table" "TB_L2_Furn_table_002_WORKING TABLE - WORKING TABLE" 2 "L2-table-002" "none" "none" [0.2650,5.4130] 2.0870 1.0000 1.000000000 0.000000000 #([(-0.7785),4.9130],[1.3085,4.9130],[1.3085,5.9130],[(-0.7785),5.9130]) "WORKING TABLE - WORKING TABLE" "WORKING TABLE - WORKING TABLE-V39-LEVEL 2 GENERAL ARRANGEMENT" "Q-CASE" "1706"
    TB_furnBox "table" "TB_L2_Furn_table_003_TABLE_DINING_RECTANGLE CHAMPAGNE LEG - T" 2 "L2-table-003" "none" "none" [3.5960,(-5.2720)] 0.3800 0.3800 1.000000000 0.000000000 #([3.4060,(-5.4620)],[3.7860,(-5.4620)],[3.7860,(-5.0820)],[3.4060,(-5.0820)]) "TABLE_DINING_RECTANGLE CHAMPAGNE LEG - TA103 380W x 380D x 750H" "TABLE_DINING_RECTANGLE CHAMPAGNE LEG - TA103 380W x 380D x 750H-2475481-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "11C0"
    TB_furnBox "table" "TB_L2_Furn_table_004_TABLE_DINING_RECTANGLE CHAMPAGNE LEG - T" 2 "L2-table-004" "none" "none" [4.4590,(-7.2910)] 0.3800 0.3800 1.000000000 0.000000000 #([4.2690,(-7.4810)],[4.6490,(-7.4810)],[4.6490,(-7.1010)],[4.2690,(-7.1010)]) "TABLE_DINING_RECTANGLE CHAMPAGNE LEG - TA103 380W x 380D x 750H" "TABLE_DINING_RECTANGLE CHAMPAGNE LEG - TA103 380W x 380D x 750H-2475481-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "126F"
    TB_furnBox "table" "TB_L2_Furn_table_005_TABLE_DINING_RECTANGLE CHAMPAGNE LEG - T" 2 "L2-table-005" "none" "none" [4.8190,(-5.8840)] 0.3800 0.3800 1.000000000 0.000000000 #([4.6290,(-6.0740)],[5.0090,(-6.0740)],[5.0090,(-5.6940)],[4.6290,(-5.6940)]) "TABLE_DINING_RECTANGLE CHAMPAGNE LEG - TA103 380W x 380D x 750H" "TABLE_DINING_RECTANGLE CHAMPAGNE LEG - TA103 380W x 380D x 750H-2385270-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "1805"
    TB_furnBox "coffee-table" "TB_L2_Furn_coffee-table_001_TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 6" 2 "L2-coffee-table-001" "none" "none" [2.1360,(-5.1120)] 0.5000 0.5000 0.998789025 0.049198416 #([1.8986,(-5.3740)],[2.3980,(-5.3494)],[2.3734,(-4.8500)],[1.8740,(-4.8746)]) "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H" "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H-2395479-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "11B2"
    TB_furnBox "coffee-table" "TB_L2_Furn_coffee-table_002_TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 6" 2 "L2-coffee-table-002" "none" "none" [3.6190,6.0090] 0.5000 0.5000 0.998198181 0.060003262 #([3.3845,5.7444],[3.8836,5.7745],[3.8535,6.2736],[3.3544,6.2435]) "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H" "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H-2385305-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "233F"
    TB_furnBox "coffee-table" "TB_L2_Furn_coffee-table_003_TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 7" 2 "L2-coffee-table-003" "none" "none" [4.3410,2.7600] 0.7000 0.7000 0.738455341 0.674302388 #([4.3185,2.2655],[4.8355,2.7375],[4.3635,3.2545],[3.8465,2.7825]) "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 700W 400H" "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 700W 400H-2621907-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "225A"
    TB_furnBox "coffee-table" "TB_L2_Furn_coffee-table_004_TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 6" 2 "L2-coffee-table-004" "none" "none" [4.4050,(-8.6620)] 0.5000 0.5000 0.842358351 0.538917812 #([4.3291,(-9.0073)],[4.7503,(-8.7379)],[4.4809,(-8.3167)],[4.0597,(-8.5861)]) "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H" "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H-2385305-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "127E"
    TB_furnBox "coffee-table" "TB_L2_Furn_coffee-table_005_TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 7" 2 "L2-coffee-table-005" "none" "none" [4.5810,(-2.6000)] 0.7000 0.7000 0.738455341 0.674302388 #([4.5585,(-3.0945)],[5.0755,(-2.6225)],[4.6035,(-2.1055)],[4.0865,(-2.5775)]) "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 700W 400H" "TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 700W 400H-2621897-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "135A"
    TB_furnBox "coffee-table" "TB_L2_Furn_coffee-table_006_COFFEE TABLE RETANGLE - VENNATIVE - TYPE" 2 "L2-coffee-table-006" "none" "none" [5.3550,0.0460] 1.0000 0.5000 (-0.028445030) 0.999595358 #([5.6191,(-0.4467)],[5.5907,0.5529],[5.0909,0.5387],[5.1193,(-0.4609)]) "COFFEE TABLE RETANGLE - VENNATIVE - TYPE 1" "COFFEE TABLE RETANGLE - VENNATIVE - TYPE 1-2607763-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "12BE"
    TB_furnBox "cabinet" "TB_L2_Furn_cabinet_001_IA_J10_WORK CABINET - IA_J10_WORK CABINE" 2 "L2-cabinet-001" "none" "none" [(-4.2200),6.4150] 2.4500 0.6000 1.000000000 0.000000000 #([(-5.4450),6.1150],[(-2.9950),6.1150],[(-2.9950),6.7150],[(-5.4450),6.7150]) "IA_J10_WORK CABINET - IA_J10_WORK CABINET" "IA_J10_WORK CABINET - IA_J10_WORK CABINET-2576886-LEVEL 2 GENERAL ARRANGEMENT" "Q-CASE" "17F7"
    TB_furnBox "cabinet" "TB_L2_Furn_cabinet_002_IA_J12_CABINET - IA_J12_CABINET" 2 "L2-cabinet-002" "none" "none" [(-3.8800),(-3.3550)] 4.0500 0.6000 0.000000000 1.000000000 #([(-3.5800),(-5.3800)],[(-3.5800),(-1.3300)],[(-4.1800),(-1.3300)],[(-4.1800),(-5.3800)]) "IA_J12_CABINET - IA_J12_CABINET" "IA_J12_CABINET - IA_J12_CABINET-2459946-LEVEL 2 GENERAL ARRANGEMENT" "Q-CASE" "1016"
    TB_furnBox "cabinet" "TB_L2_Furn_cabinet_003_IA_J10_WORK CABINET - IA_J10_WORK CABINE" 2 "L2-cabinet-003" "none" "none" [(-3.8800),(-0.1070)] 2.4500 0.6000 0.000000000 1.000000000 #([(-3.5800),(-1.3320)],[(-3.5800),1.1180],[(-4.1800),1.1180],[(-4.1800),(-1.3320)]) "IA_J10_WORK CABINET - IA_J10_WORK CABINET" "IA_J10_WORK CABINET - IA_J10_WORK CABINET-2579628-LEVEL 2 GENERAL ARRANGEMENT" "Q-CASE" "17E6"
    TB_furnBox "cabinet" "TB_L2_Furn_cabinet_004_IA_J11_WORK CABINET - IA_J11_WORK CABINE" 2 "L2-cabinet-004" "none" "none" [(-3.8800),3.0630] 3.8900 0.6000 0.000000000 1.000000000 #([(-3.5800),1.1180],[(-3.5800),5.0080],[(-4.1800),5.0080],[(-4.1800),1.1180]) "IA_J11_WORK CABINET - IA_J11_WORK CABINET" "IA_J11_WORK CABINET - IA_J11_WORK CABINET-2459944-LEVEL 2 GENERAL ARRANGEMENT" "Q-CASE" "1155"
    TB_furnBox "cabinet" "TB_L2_Furn_cabinet_005_IA_J07_WORK CABINET - IA_J07_WORK CABINE" 2 "L2-cabinet-005" "none" "none" [(-3.2580),(-1.7800)] 7.2000 0.4450 0.000000000 1.000000000 #([(-3.0355),(-5.3800)],[(-3.0355),1.8200],[(-3.4805),1.8200],[(-3.4805),(-5.3800)]) "IA_J07_WORK CABINET - IA_J07_WORK CABINET" "IA_J07_WORK CABINET - IA_J07_WORK CABINET-2425803-LEVEL 2 GENERAL ARRANGEMENT" "Q-CASE" "D77"
    TB_furnBox "cabinet" "TB_L2_Furn_cabinet_006_WORK CABINET-1 - WORK CABINET-1" 2 "L2-cabinet-006" "none" "none" [(-3.2580),3.4080] 3.0000 0.4450 0.000000000 1.000000000 #([(-3.0355),1.9080],[(-3.0355),4.9080],[(-3.4805),4.9080],[(-3.4805),1.9080]) "WORK CABINET-1 - WORK CABINET-1" "WORK CABINET-1 - WORK CABINET-1-2458913-LEVEL 2 GENERAL ARRANGEMENT" "Q-CASE" "F08"
    TB_furnBox "cabinet" "TB_L2_Furn_cabinet_007_loose shapes on Q-CASE" 2 "L2-cabinet-007" "none" "none" [(-1.5400),(-1.8300)] 7.1000 1.0000 0.000000000 1.000000000 #([(-1.0400),(-5.3800)],[(-1.0400),1.7200],[(-2.0400),1.7200],[(-2.0400),(-5.3800)]) "loose shapes on Q-CASE" "none" "Q-CASE" "none"
    TB_furnBox "cabinet" "TB_L2_Furn_cabinet_008_CONSOLE_CABINET_BAKER - TA13 1800W 400D" 2 "L2-cabinet-008" "none" "none" [2.9260,0.0600] 1.8000 0.3500 0.000000000 1.000000000 #([3.1010,(-0.8400)],[3.1010,0.9600],[2.7510,0.9600],[2.7510,(-0.8400)]) "CONSOLE_CABINET_BAKER - TA13 1800W 400D" "CONSOLE_CABINET_BAKER - TA13 1800W 400D-2602679-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "22EF"
    TB_furnBox "cabinet" "TB_L2_Furn_cabinet_009_Casework 2 - Casework 2" 2 "L2-cabinet-009" "none" "none" [4.5040,2.9930] 3.5970 1.2270 1.000000000 0.000000000 #([2.7055,2.3795],[6.3025,2.3795],[6.3025,3.6065],[2.7055,3.6065]) "Casework 2 - Casework 2" "Casework 2 - Casework 2-2619104-LEVEL 2 GENERAL ARRANGEMENT" "Q-CASE" "44D8"
    TB_furnBox "cabinet" "TB_L2_Furn_cabinet_010_Casework 1 - Casework 2" 2 "L2-cabinet-010" "none" "none" [4.5790,(-2.8730)] 3.7530 1.1750 0.999595358 0.028445030 #([2.7200,(-3.5136)],[6.4715,(-3.4069)],[6.4380,(-2.2324)],[2.6865,(-2.3391)]) "Casework 1 - Casework 2" "Casework 1 - Casework 2-2622302-LEVEL 2 GENERAL ARRANGEMENT" "Q-CASE" "6636"
    TB_furnBox "tall-cabinet" "TB_L2_Furn_tall-cabinet_001_RACKS_DATA - 1100x600" 2 "L2-tall-cabinet-001" "none" "none" [(-5.0800),8.1530] 1.8000 0.6000 0.000000000 1.000000000 #([(-4.7800),7.2530],[(-4.7800),9.0530],[(-5.3800),9.0530],[(-5.3800),7.2530]) "RACKS_DATA - 1100x600" "RACKS_DATA - 1100x600-2280828-LEVEL 2 GENERAL ARRANGEMENT" "Q-SPCQ" "none"
    TB_furnBox "tall-cabinet" "TB_L2_Furn_tall-cabinet_002_RACKS_DATA - 1100x600" 2 "L2-tall-cabinet-002" "none" "none" [(-4.2510),8.1530] 1.8000 0.6000 0.000000000 1.000000000 #([(-3.9510),7.2530],[(-3.9510),9.0530],[(-4.5510),9.0530],[(-4.5510),7.2530]) "RACKS_DATA - 1100x600" "RACKS_DATA - 1100x600-2280828-LEVEL 2 GENERAL ARRANGEMENT" "Q-SPCQ" "none"
    TB_furnBox "tall-cabinet" "TB_L2_Furn_tall-cabinet_003_TALL CABINET - TALL CABINET 1875W" 2 "L2-tall-cabinet-003" "none" "none" [(-0.9760),5.9470] 1.8750 0.4050 0.000000000 1.000000000 #([(-0.7735),5.0095],[(-0.7735),6.8845],[(-1.1785),6.8845],[(-1.1785),5.0095]) "TALL CABINET - TALL CABINET 1875W" "TALL CABINET - TALL CABINET 1875W-2561397-LEVEL 2 GENERAL ARRANGEMENT" "Q-CASE" "1472"
    TB_furnBox "other" "TB_L2_Furn_other_001_Fritz-Hansen_SH200 - Default" 2 "L2-other-001" "none" "none" [1.7230,(-4.5650)] 0.6150 0.5940 0.674560116 0.738219920 #([1.7348,(-4.9923)],[2.1497,(-4.5383)],[1.7112,(-4.1377)],[1.2963,(-4.5917)]) "Fritz-Hansen_SH200 - Default" "Fritz-Hansen_SH200 - Default-2479048-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "1769"
    TB_furnBox "other" "TB_L2_Furn_other_002_Fritz-Hansen_SH200 - Default" 2 "L2-other-002" "none" "none" [1.7760,(-5.6790)] 0.6150 0.5940 (-0.795684962) 0.605710691 #([2.2006,(-5.6289)],[1.7112,(-5.2564)],[1.3514,(-5.7291)],[1.8408,(-6.1016)]) "Fritz-Hansen_SH200 - Default" "Fritz-Hansen_SH200 - Default-2476898-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "11AA"
    TB_furnBox "other" "TB_L2_Furn_other_003_Fritz-Hansen_SH200 - Default" 2 "L2-other-003" "none" "none" [3.8200,2.2700] 0.6150 0.5940 (-0.788869611) 0.614560605 #([4.2451,2.3153],[3.7599,2.6933],[3.3949,2.2247],[3.8801,1.8467]) "Fritz-Hansen_SH200 - Default" "Fritz-Hansen_SH200 - Default-2479048-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "1352"
    TB_furnBox "other" "TB_L2_Furn_other_004_Fritz-Hansen_SH200 - Default" 2 "L2-other-004" "none" "none" [3.9990,(-7.6960)] 0.6150 0.5940 (-0.733136661) 0.680081346 #([4.4264,(-7.6874)],[3.9755,(-7.2691)],[3.5716,(-7.7046)],[4.0225,(-8.1229)]) "Fritz-Hansen_SH200 - Default" "Fritz-Hansen_SH200 - Default-2479048-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "1860"
    TB_furnBox "other" "TB_L2_Furn_other_005_Fritz-Hansen_SH200 - Default" 2 "L2-other-005" "none" "none" [4.1270,(-2.0220)] 0.6150 0.5940 0.872325393 0.488925770 #([4.0040,(-2.4314)],[4.5405,(-2.1307)],[4.2500,(-1.6126)],[3.7135,(-1.9133)]) "Fritz-Hansen_SH200 - Default" "Fritz-Hansen_SH200 - Default-2476898-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "663A"
    TB_furnBox "other" "TB_L2_Furn_other_006_Fritz-Hansen_SH200 - Default" 2 "L2-other-006" "none" "none" [4.8980,2.2880] 0.6150 0.5940 0.680848711 0.732424079 #([4.9062,1.8606],[5.3249,2.3110],[4.8898,2.7154],[4.4711,2.2650]) "Fritz-Hansen_SH200 - Default" "Fritz-Hansen_SH200 - Default-2476898-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "44E0"
    TB_furnBox "other" "TB_L2_Furn_other_007_Fritz-Hansen_SH200 - Default" 2 "L2-other-007" "none" "none" [5.0940,(-2.1300)] 0.6150 0.5940 (-0.797689196) 0.603068774 #([5.5184,(-2.0785)],[5.0278,(-1.7076)],[4.6696,(-2.1815)],[5.1602,(-2.5524)]) "Fritz-Hansen_SH200 - Default" "Fritz-Hansen_SH200 - Default-2479048-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "13D5"
    TB_furnBox "other" "TB_L2_Furn_other_008_Fritz-Hansen_SH200 - Default" 2 "L2-other-008" "none" "none" [5.3030,(-5.4050)] 0.6150 0.5940 (-0.634595636) 0.772844343 #([5.7277,(-5.4542)],[5.3374,(-4.9789)],[4.8783,(-5.3558)],[5.2686,(-5.8311)]) "Fritz-Hansen_SH200 - Default" "Fritz-Hansen_SH200 - Default-2476898-LEVEL 2 GENERAL ARRANGEMENT" "I-FURN" "1806"
)
-- The build's furniture step: materials, levels, every box.
fn TB_furnRun =
(
    TB_furnMakeMaterials()
    TB_furnSetLevels()
    TB_furnAll()
)
-- For every floor, its level as the scene has it: the most common value (to the millimetre) of z minus TB_base over the
-- objects that carry TB_floor and TB_base. Sets TB_furnLevels for the floors it finds and returns how many.
fn TB_furnSceneLevels =
(
    local fis = #()
    local mms = #()
    local cnt = #()
    for o in objects where (getUserProp o "TB_floor") != undefined and (getUserProp o "TB_base") != undefined do
    (
        local fi = (TB_furnNum (getUserProp o "TB_floor")) as integer
        local mmv = (floor ((o.pos.z - (TB_furnNum (getUserProp o "TB_base"))) * 1000.0 + 0.5)) as integer
        local k = 0
        for j = 1 to fis.count where fis[j] == fi and mms[j] == mmv do k = j
        if k == 0 then ( append fis fi; append mms mmv; append cnt 1 )
        else cnt[k] += 1
    )
    local found = 0
    for f = 1 to TB_furnFloors.count do
    (
        local best = 0
        for j = 1 to fis.count where fis[j] == f and cnt[j] > best do
        (
            best = cnt[j]
            TB_furnLevels[f] = mms[j] / 1000.0
        )
        if best > 0 do found += 1
    )
    found
)
-- "Furniture boxes only": adds the boxes to a scene already built from this model and changes nothing else. It refuses, and
-- changes nothing, when boxes are there already or System Units are not metres. The placement shift comes from the hidden
-- datum TB_ORIGIN_DWG (shift = minus its x, y) and each level from the objects that carry TB_floor and TB_base;
-- what it cannot find it takes from the window (the tick box and the level spinners), and says so. It reports in message boxes
-- of its own (the Build button's message is written for parts), so TB_build returns false after it.
fn TB_furnAdd =
(
    if TB_furnWant == false then
    (
        messageBox "Tick Build furniture boxes as well. Nothing in this scene has been changed." title:"TEST_BANK"
        return false
    )
    if abs(units.systemScale - 1.0) > 0.0001 or units.systemType != #meters then
    (
        messageBox "This scene's System Units are not metres, so the boxes would come out the wrong size. Nothing in this scene has been changed." title:"TEST_BANK"
        return false
    )
    local existing = 0
    for o in objects where (getUserProp o "TB_furn") != undefined or (matchPattern o.layer.name pattern:"TB_*_Furn_*") do existing += 1
    if existing > 0 then
    (
        messageBox ("This scene already has furniture boxes (" + (existing as string) + " objects). Nothing in this scene has been changed.") title:"TEST_BANK"
        return false
    )
    local t0 = timeStamp()
    local notes = ""
    local datum = undefined
    for o in objects where o.name == "TB_ORIGIN_DWG" do datum = o
    if datum == undefined then notes += "The origin datum TB_ORIGIN_DWG was not found, so the boxes are placed by the tick box At the drawing's own coordinates. "
    else TB_shift = [0.0 - datum.pos.x, 0.0 - datum.pos.y]
    TB_nodes = #()
    TB_failed = #()
    TB_furnMakeMaterials()
    TB_furnSetLevels()
    local found = TB_furnSceneLevels()
    if found < TB_furnFloors.count then notes += "The level of " + ((TB_furnFloors.count - found) as string) + " floor(s) was not found in the scene, so the level spinners are used for it. "
    TB_furnAll()
    format "TB FURNITURE BOXES ADDED: % boxes in % s, % failed checks\n" TB_nodes.count ((timeStamp() - t0) / 1000.0) TB_failed.count
    for f in TB_failed do format "  check failed: %\n" f
    if notes != "" do messageBox notes title:"TEST_BANK"
    if TB_failed.count == 0 then messageBox ("Added " + (TB_nodes.count as string) + " furniture boxes. Every box passed its height and position checks. Nothing else in this scene was changed. Save As to keep your .max file.") title:"TEST_BANK"
    else messageBox ((TB_failed.count as string) + " of the " + (TB_nodes.count as string) + " furniture boxes failed a check and are on layer TB_Check_Failed (listed in the MAXScript Listener). The others were added and passed. Nothing else in this scene was changed.") title:"TEST_BANK"
    true
)
-- After the build: every box takes the height of its kind (TB_furnHeights, read from the window) and stands on its kind's
-- base, or on top of the kind of support it was drawn on (the support's kind is none, or undefined, or empty: no support). A box
-- keeps the level it is on (its z minus its TB_base), so levels moved by "Update levels and heights" stay. A box that is not
-- a Box any more, or of an unknown kind, is left alone.
fn TB_furnApply =
(
    local n = 0
    local skipped = 0
    for o in objects where (getUserProp o "TB_furn") != undefined do
    (
        local ki = findItem TB_furnKeys ((getUserProp o "TB_furnKind") as string)
        if (classOf o) != Box or ki == 0 then skipped += 1
        else
        (
            local z0 = TB_furnZ0 ki (findItem TB_furnKeys ((getUserProp o "TB_furnOnKind") as string))
            o.pos.z = o.pos.z - (TB_furnNum (getUserProp o "TB_base")) + z0
            o.height = TB_furnHeights[ki]
            setUserProp o "TB_base" z0
            n += 1
        )
    )
    #(n, skipped)
)
fn TB_build =
(
    if TB_furnAddOnly then
    (
        -- "Furniture boxes only" has said what it did, or why it did nothing, in its own message: false = nothing more to report
        TB_furnAdd()
        return false
    )
    if objects.count > 0 then
    (
        messageBox "Open a NEW EMPTY scene first. Nothing in this scene has been changed." title:"TEST_BANK"
        return false
    )
    units.systemType = #meters
    units.systemScale = 1.0
    units.displayType = #metric
    units.metricType = #meters
    TB_nodes = #()
    TB_failed = #()
    TB_makeMaterials()
    local t0 = timeStamp()
    TB_part #wall "TB_L1_Wall_001" #(#([(-0.4465),0.1400],[(-0.4465),(-0.1400)],[0.1035,(-0.1400)],[0.1035,0.0390],[0.4455,0.0390],[0.4465,0.1390])) 0.0000 3.0000 true 1 [1.0195,(-9.2190)] [0.5730,(-9.3590)] [1.4660,(-9.0790)]
    TB_part #wall "TB_L1_Wall_002" #(#([(-0.3660),(-0.3515)],[0.3660,(-0.3485)],[0.3660,0.3515],[(-0.0240),0.3515],[(-0.0240),(-0.2515)],[(-0.3660),(-0.2545)])) 0.0000 3.0000 true 1 [3.3520,(-8.8285)] [2.9860,(-9.1800)] [3.7180,(-8.4770)]
    TB_part #wall "TB_L1_Wall_003" #(#([0.2315,0.0500],[(-0.3205),0.0500],[(-0.3205),(-0.0500)],[0.2945,(-0.0500)],[0.3205,(-0.0090)])) 0.0000 3.0000 true 1 [4.6385,(-8.5270)] [4.3180,(-8.5770)] [4.9590,(-8.4770)]
    TB_part #wall "TB_L1_Wall_004" #(#([0.5000,(-0.1785)],[0.5000,0.1785],[(-0.5000),0.1785],[(-0.5000),0.0785],[0.4000,0.0785],[0.4000,(-0.1785)])) 0.0000 3.0000 true 1 [(-1.3800),(-5.1685)] [(-1.8800),(-5.3470)] [(-0.8800),(-4.9900)]
    TB_part #wall "TB_L1_Wall_005" #(#([1.1395,8.0405],[1.1575,8.0405],[1.1575,8.3335],[1.4795,8.3335],[1.4795,8.3405],[5.5415,8.3405],[5.5535,7.7345],[5.8975,7.7415],[5.9135,6.9115],[6.0135,6.9135],[5.9795,8.6405],[1.1235,8.6405],[1.0755,10.4675],[(-6.0135),10.4675],[(-5.4455),(-10.1675)],[(-5.4455),(-10.4675)],[(-0.8425),(-10.4675)],[(-0.8425),(-10.3675)],[(-1.6955),(-10.3675)],[(-1.6955),(-9.4675)],[(-1.8455),(-9.4675)],[(-1.8455),(-9.8675)],[(-3.6455),(-9.8675)],[(-3.6455),(-8.0945)],[(-1.8455),(-8.0945)],[(-1.8455),(-8.3675)],[(-1.6955),(-8.3675)],[(-1.6955),(-7.9445)],[1.3015,(-7.9445)],[1.3015,(-7.8445)],[0.9075,(-7.8445)],[0.9075,(-7.6445)],[0.3575,(-7.6445)],[0.3575,(-7.8445)],[(-1.0955),(-7.8445)],[(-1.0955),(-7.6345)],[(-1.1955),(-7.6345)],[(-1.1955),(-7.8445)],[(-3.7955),(-7.8445)],[(-3.7955),(-10.3675)],[(-5.1455),(-10.3675)],[(-5.1455),(-10.1675)],[(-5.2035),(-8.0675)],[(-4.5955),(-8.0675)],[(-4.5955),(-7.9675)],[(-5.2065),(-7.9675)],[(-5.2495),(-6.3945)],[(-5.1445),(-6.3915)],[(-5.1455),(-6.3415)],[(-5.1465),(-6.2915)],[(-5.2525),(-6.2915)],[(-5.5315),3.8315],[(-3.7955),3.8315],[(-3.7955),(-6.2915)],[(-4.1455),(-6.2915)],[(-4.1445),(-6.3915)],[(-3.3005),(-6.3915)],[(-3.3005),(-6.2915)],[(-3.6955),(-6.2935)],[(-3.6955),0.9315],[(-1.0965),0.9315],[(-1.0965),1.0315],[(-3.6955),1.0315],[(-3.6955),3.8315],[0.3575,3.8315],[0.3575,1.8715],[4.5825,1.8715],[4.5825,1.9945],[4.4825,1.9945],[4.4825,1.9705],[0.9075,1.9705],[0.9075,2.1705],[0.4575,2.1705],[0.4575,4.4705],[4.5825,4.4715],[4.5825,4.5705],[0.3575,4.5705],[0.3575,3.9315],[(-5.5335),3.9315],[(-5.5815),5.6465],[(-3.3335),5.6465],[(-3.3335),4.9315],[(-3.2335),4.9315],[(-3.2335),5.9465],[(-5.5895),5.9465],[(-5.7055),10.1675],[0.7835,10.1675],[0.8935,5.9465],[(-1.9335),5.9465],[(-1.9335),5.6465],[0.8075,5.6465],[0.8075,5.5705],[0.9075,5.5705],[0.9075,5.6465],[2.2545,5.6475],[2.2545,5.7265],[1.1575,5.7265],[1.1575,7.3335])) 0.0000 3.0000 true 1 [0.2155,1.2875] [(-5.7980),(-9.1800)] [6.2290,11.7550]
    TB_part #wall "TB_L1_Wall_006" #(#([(-0.4995),0.1285],[0.3995,0.1285],[0.3995,(-0.2285)],[0.4995,(-0.2285)],[0.4995,0.2285],[(-0.4995),0.2285])) 0.0000 3.0000 true 1 [2.7705,8.3925] [2.2710,8.1640] [3.2700,8.6210]
    TB_part #wall "TB_L1_Wall_007" #(#([0.0500,0.0400],[(-0.0500),0.0400],[(-0.0500),(-0.0400)],[0.0500,(-0.0400)])) 0.0000 3.0000 true 1 [3.2200,6.9740] [3.1700,6.9340] [3.2700,7.0140]
    TB_part #wall "TB_L1_Wall_008" #(#([(-0.4490),(-0.0040)],[0.4490,(-0.0040)],[0.4490,0.0040],[(-0.4490),0.0040])) 0.0000 1.1360 false 1 [1.8220,8.6170] [1.3730,8.6130] [2.2710,8.6210]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #wall "TB_L1_Wall_009" #(#([0.1610,(-0.1465)],[0.1610,0.1465],[(-0.1610),0.1465],[(-0.1610),(-0.1465)])) 0.0000 1.1360 false 1 [1.5340,9.4745] [1.3730,9.3280] [1.6950,9.6210]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #wall "TB_L1_Wall_010" #(#([(-0.4350),(-0.2500)],[(-0.4460),0.1580],[0.4490,0.1580],[0.4490,0.2500],[(-0.4490),0.2500],[(-0.4490),(-0.2500)])) 0.0000 1.1430 false 1 [1.8220,8.3630] [1.3730,8.1130] [2.2710,8.6130]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #wall "TB_L1_Wall_011" #(#([0.5485,(-0.5285)],[(-0.5065),(-0.5285)],[(-0.5345),0.5495],[(-0.5485),0.5495],[(-0.5485),(-0.5495)],[0.5485,(-0.5495)])) 0.0000 1.5640 false 1 [1.9215,7.5635] [1.3730,7.0140] [2.4700,8.1130]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #wall "TB_L1_Wall_012" #(#([(-0.0500),(-0.5750)],[0.0500,(-0.5750)],[0.0500,0.5750],[(-0.0500),0.5750])) 0.0000 1.8570 false 1 [3.2200,7.5890] [3.1700,7.0140] [3.2700,8.1640]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #wall "TB_L1_Wall_013" #(#([0.1290,0.8530],[0.0290,0.8510],[0.0420,0.1810],[(-0.1580),0.1770],[(-0.1380),(-0.8530)],[(-0.0380),(-0.8510)],[(-0.0420),(-0.6210)],[0.1580,(-0.6170)])) 0.0000 3.0000 true 1 [6.1120,6.7680] [5.9540,5.9150] [6.2700,7.6210]
    TB_part #wall "TB_L1_Wall_014" #(#([(-0.0290),(-0.1460)],[(-0.0710),(-0.2080)],[0.0120,(-0.2640)],[0.0710,(-0.1770)],[0.0710,0.2640],[(-0.0290),0.2640])) 0.0000 3.0000 true 1 [5.8410,(-6.9430)] [5.7700,(-7.2070)] [5.9120,(-6.6790)]
    TB_part #wall "TB_L1_Wall_015" #(#([(-0.1700),(-0.2500)],[0.7300,(-0.2500)],[0.7300,0.1500],[0.3220,0.1500],[0.3210,0.2150],[0.0710,0.2120],[0.0700,0.2500],[(-0.7300),0.2500],[(-0.7300),0.1500],[(-0.1700),0.1500])) 0.0000 3.0000 true 1 [5.9820,(-5.8290)] [5.2520,(-6.0790)] [6.7120,(-5.5790)]
    TB_part #wall "TB_L1_Wall_016" #(#([0.6070,(-0.3305)],[0.5910,0.4695],[0.2910,0.4635],[0.3050,(-0.2365)],[(-0.6070),(-0.2365)],[(-0.6070),(-0.3365)],[0.3070,(-0.3365)],[0.3100,(-0.4695)],[0.4100,(-0.4675)],[0.4070,(-0.3345)])) 0.0000 3.0000 true 1 [5.8600,(-3.4795)] [5.2530,(-3.9490)] [6.4670,(-3.0100)]
    TB_part #column "TB_L1_Column_001" #(#([(-0.2750),0.1500],[(-0.2750),(-0.1500)],[0.2750,(-0.1500)],[0.2750,0.1500])) 0.0000 3.0000 true 1 [0.8480,(-3.4020)] [0.5730,(-3.5520)] [1.1230,(-3.2520)]
    TB_part #column "TB_L1_Column_002" #(#([0.2750,0.1500],[(-0.2750),0.1500],[(-0.2750),(-0.1500)],[0.2750,(-0.1500)])) 0.0000 3.0000 true 1 [0.8480,0.0280] [0.5730,(-0.1220)] [1.1230,0.1780]
    TB_part #column "TB_L1_Column_003" #(#([0.1580,(-0.3975)],[0.1420,0.4025],[(-0.1580),0.3965],[(-0.1420),(-0.4025)])) 0.0000 3.0000 true 1 [6.2410,(-0.0505)] [6.0830,(-0.4530)] [6.3990,0.3520]
    TB_part #column "TB_L1_Column_004" #(#([(-0.0560),0.2910],[(-0.0600),0.5110],[(-0.1600),0.5090],[(-0.1400),(-0.5110)],[0.1600,(-0.5050)],[0.1440,0.2950])) 0.0000 3.0000 true 1 [6.1740,3.4070] [6.0140,2.8960] [6.3340,3.9180]
    TB_part #wall "TB_L1_Wall_017_closure (ATM Machine - ATM Machine)" #(#([0.0560,(-0.2890)],[0.0440,0.2910],[(-0.0560),0.2890],[(-0.0440),(-0.2910)])) 0.0000 3.0000 true 1 [6.1850,7.9100] [6.1290,7.6190] [6.2410,8.2010]
    TB_part #glass "TB_L1_Glass_001" #(#([(-0.0500),0.0125],[(-0.0500),(-0.0125)],[0.0500,(-0.0125)],[0.0500,0.0125])) 0.0000 3.0000 true 1 [4.7480,1.1315] [4.6980,1.1190] [4.7980,1.1440]
    TB_part #glass "TB_L1_Glass_002" #(#([(-0.0580),0.4120],[(-0.0400),(-0.5120)],[0.0600,(-0.5100)],[0.0400,0.5120],[(-0.0600),0.5120],[(-0.0590),0.4120])) 0.0000 3.0000 true 1 [6.0540,4.4280] [5.9940,3.9160] [6.1140,4.9400]
    TB_part #glass "TB_L1_Glass_003_GLASS WALL 2600H 20X100" #(#([(-0.0335),(-0.0050)],[0.0335,(-0.0050)],[0.0335,0.0050],[(-0.0335),0.0050])) 0.0000 2.6000 false 1 [0.5395,2.2690] [0.5060,2.2640] [0.5730,2.2740]
    TB_part #glass "TB_L1_Glass_004_GLASS WALL 2600H 20X100" #(#([(-0.0050),(-0.4195)],[0.0050,(-0.4195)],[0.0050,0.4195],[(-0.0050),0.4195])) 0.0000 2.6000 false 1 [0.6230,2.7385] [0.6180,2.3190] [0.6280,3.1580]
    TB_part #glass "TB_L1_Glass_005_GLASS WALL 2600H 20X100" #(#([(-0.0050),(-1.0070)],[0.0050,(-1.0070)],[0.0050,1.0070],[(-0.0050),1.0070])) 0.0000 2.6000 false 1 [4.7480,2.1510] [4.7430,1.1440] [4.7530,3.1580]
    TB_part #glass "TB_L1_Glass_006_GLASS WALL 2600H 20X100" #(#([0.4490,(-0.0050)],[0.4490,0.0050],[(-0.4390),0.0050],[(-0.4490),(-0.0050)])) 0.0000 2.6000 false 1 [4.8030,(-3.7660)] [4.3540,(-3.7710)] [5.2520,(-3.7610)]
    TB_part #glass "TB_L1_Glass_007_GLASS WALL 2600H 20X100" #(#([(-0.4815),(-0.5090)],[(-0.4745),(-0.5150)],[0.4815,0.5150],[0.4675,0.5150])) 0.0000 2.6000 false 1 [3.8825,(-4.2760)] [3.4010,(-4.7910)] [4.3640,(-3.7610)]
    TB_part #glass "TB_L1_Glass_008_GLASS WALL 2600H 20X100" #(#([(-0.0125),(-0.0065)],[0.0005,(-0.0065)],[0.0425,0.0385],[(-0.0425),0.0385],[(-0.0425),(-0.0385)])) 0.0000 2.6000 false 1 [1.7285,(-6.5955)] [1.6860,(-6.6340)] [1.7710,(-6.5570)]
    TB_part #glass "TB_L1_Glass_009_GLASS WALL 2600H 20X100" #(#([(-0.1055),(-0.0050)],[0.0965,(-0.0050)],[0.1055,0.0050],[(-0.1055),0.0050])) 0.0000 2.6000 false 1 [1.6235,(-6.6070)] [1.5180,(-6.6120)] [1.7290,(-6.6020)]
    TB_part #glass "TB_L1_Glass_010_GLASS WALL 2600H 20X100" #(#([(-0.2730),(-0.2905)],[(-0.2590),(-0.2905)],[0.2730,0.2835],[0.2660,0.2905])) 0.0000 2.6000 false 1 [2.0300,(-6.2665)] [1.7570,(-6.5570)] [2.3030,(-5.9760)]
    TB_part #glass "TB_L1_Glass_011_GLASS WALL 2600H 20X100" #(#([(-0.2305),(-0.0050)],[0.2305,(-0.0050)],[0.2305,0.0050],[(-0.2305),0.0050])) 0.0000 2.6000 false 1 [(-0.6495),2.2690] [(-0.8800),2.2640] [(-0.4190),2.2740]
    TB_part #glass "TB_L1_Glass_012_GLASS WALL 2600H 20X100" #(#([(-0.0050),(-0.0315)],[0.0050,(-0.0315)],[0.0050,0.0315],[(-0.0050),0.0315])) 0.0000 2.6000 false 1 [4.7480,3.3145] [4.7430,3.2830] [4.7530,3.3460]
    TB_part #glass "TB_L1_Glass_013_GLASS WALL 2600H 20X100" #(#([0.0050,(-0.4315)],[0.0050,0.4315],[(-0.0050),0.4315],[(-0.0050),(-0.4315)])) 0.0000 2.6000 false 1 [4.7480,5.3265] [4.7430,4.8950] [4.7530,5.7580]
    TB_part #glass "TB_L1_Glass_014_GLASS WALL 2600H 20X100" #(#([(-0.0050),(-0.3070)],[0.0050,(-0.3070)],[0.0050,0.3070],[(-0.0050),0.3070])) 0.0000 2.6000 false 1 [4.7480,4.5780] [4.7430,4.2710] [4.7530,4.8850]
    TB_part #glass "TB_L1_Glass_015_GLASS WALL 2600H 20X100" #(#([0.0995,(-0.0050)],[0.0995,0.0050],[(-0.0995),0.0050],[(-0.0995),(-0.0050)])) 0.0000 2.6000 false 1 [4.8425,4.8900] [4.7430,4.8850] [4.9420,4.8950]
    TB_part #glass "TB_L1_Glass_016_GLASS WALL 2600H 20X100" #(#([(-0.0640),(-0.0050)],[0.0640,(-0.0050)],[0.0640,0.0050],[(-0.0640),0.0050])) 0.0000 2.6000 false 1 [5.9310,4.8900] [5.8670,4.8850] [5.9950,4.8950]
    TB_part #glass "TB_L1_Glass_017_glass screen" #(#([(-0.0050),(-0.2055)],[0.0050,(-0.2055)],[0.0050,0.2055],[(-0.0050),0.2055])) 0.0000 3.0000 true 1 [1.0730,(-6.8625)] [1.0680,(-7.0680)] [1.0780,(-6.6570)]
    TB_part #glass "TB_L1_Glass_018_glass screen" #(#([(-0.0050),(-0.2055)],[0.0050,(-0.2055)],[0.0050,0.2055],[(-0.0050),0.2055])) 0.0000 3.0000 true 1 [1.0730,(-8.8735)] [1.0680,(-9.0790)] [1.0780,(-8.6680)]
    TB_part #mullion "TB_L1_Mullion_001_frame post" #(#([0.0495,(-0.0495)],[0.0495,0.0495],[(-0.0495),0.0495],[(-0.0495),(-0.0495)])) 0.0000 2.6000 false 1 [0.6235,2.2685] [0.5740,2.2190] [0.6730,2.3180]
    TB_part #glass "TB_L1_Glass_019_L1-001 pane" #(#([0.7595,(-0.0120)],[0.7595,0.0080],[(-0.7585),0.0120],[(-0.7595),(-0.0080)])) 0.0000 3.0000 true 1 [2.2255,(-9.1280)] [1.4660,(-9.1400)] [2.9850,(-9.1160)]
    TB_part #lintel "TB_L1_Lintel_001_L1-002" #(#([(-0.0500),(-0.4990)],[0.0500,(-0.4990)],[0.0500,0.4990],[(-0.0500),0.4990])) 2.4000 3.0000 true 1 [(-0.9300),(-5.8470)] [(-0.9800),(-6.3460)] [(-0.8800),(-5.3480)]
    TB_part #lintel "TB_L1_Lintel_002_L1-004" #(#([0.0750,0.5490],[(-0.0750),0.5490],[(-0.0750),(-0.5490)],[0.0750,(-0.5490)])) 2.4000 3.0000 true 1 [(-1.5550),(-7.6300)] [(-1.6300),(-8.1790)] [(-1.4800),(-7.0810)]
    TB_part #glass "TB_L1_Glass_020_L1-005 transom" #(#([0.5555,0.5915],[0.5485,0.5985],[(-0.5555),(-0.5915)],[(-0.5475),(-0.5985)])) 2.4000 2.6000 false 1 [2.8515,(-5.3835)] [2.2960,(-5.9820)] [3.4070,(-4.7850)]
    TB_part #lintel "TB_L1_Lintel_003_L1-006" #(#([0.4970,0.0635],[(-0.5000),0.0365],[(-0.4980),(-0.0635)],[0.5000,(-0.0365)])) 2.4000 3.0000 true 1 [(-4.4290),(-5.0705)] [(-4.9290),(-5.1340)] [(-3.9290),(-5.0070)]
    TB_part #glass "TB_L1_Glass_021_L1-007 transom" #(#([0.4615,(-0.0050)],[0.4615,0.0050],[(-0.4615),0.0050],[(-0.4615),(-0.0050)])) 2.4000 2.6000 false 1 [0.0435,2.2690] [(-0.4180),2.2640] [0.5050,2.2740]
    TB_part #glass "TB_L1_Glass_022_L1-008 transom" #(#([0.0050,0.4615],[(-0.0050),0.4615],[(-0.0050),(-0.4615)],[0.0050,(-0.4615)])) 2.4000 2.6000 false 1 [4.7480,3.8085] [4.7430,3.3470] [4.7530,4.2700]
    TB_part #glass "TB_L1_Glass_023_L1-009 pane" #(#([(-0.0155),1.2805],[(-0.0355),1.2795],[0.0155,(-1.2805)],[0.0355,(-1.2805)])) 0.0000 3.0000 true 1 [6.1735,(-1.7335)] [6.1380,(-3.0140)] [6.2090,(-0.4530)]
    TB_part #glass "TB_L1_Glass_024_L1-010 pane" #(#([(-0.0155),1.2740],[(-0.0355),1.2740],[0.0155,(-1.2740)],[0.0355,(-1.2730)])) 0.0000 3.0000 true 1 [6.1095,1.6220] [6.0740,0.3480] [6.1450,2.8960]
    TB_part #glass "TB_L1_Glass_025_L1-011 pane" #(#([(-0.2990),0.0100],[(-0.2990),(-0.0100)],[0.2990,(-0.0100)],[0.2990,0.0100])) 0.0000 3.0000 true 1 [4.0180,(-8.5270)] [3.7190,(-8.5370)] [4.3170,(-8.5170)]
    TB_part #glass "TB_L1_Glass_026_L1-012 pane" #(#([0.5990,(-0.0100)],[0.5990,0.0100],[(-0.5990),0.0100],[(-0.5990),(-0.0100)])) 0.0000 3.0000 true 1 [(-0.0270),(-9.1300)] [(-0.6260),(-9.1400)] [0.5720,(-9.1200)]
    TB_part #lintel "TB_L1_Lintel_004_L1-013" #(#([0.3990,(-0.0500)],[0.3990,0.0500],[(-0.3990),0.0500],[(-0.3990),(-0.0500)])) 2.4000 3.0000 true 1 [(-3.9800),(-6.7300)] [(-4.3790),(-6.7800)] [(-3.5810),(-6.6800)]
    TB_part #lintel "TB_L1_Lintel_005_L1-014" #(#([(-0.0500),(-0.4990)],[0.0500,(-0.4990)],[0.0500,0.4990],[(-0.0500),0.4990])) 2.4000 3.0000 true 1 [(-3.0680),5.7190] [(-3.1180),5.2200] [(-3.0180),6.2180]
    TB_part #lintel "TB_L1_Lintel_006_L1-015" #(#([(-0.6490),0.1500],[(-0.6490),(-0.1500)],[0.6490,(-0.1500)],[0.6490,0.1500])) 2.4000 3.0000 true 1 [(-2.3680),7.0840] [(-3.0170),6.9340] [(-1.7190),7.2340]
    TB_part #lintel "TB_L1_Lintel_007_L1-016" #(#([(-0.0500),(-0.4990)],[0.0500,(-0.4990)],[0.0500,0.4990],[(-0.0500),0.4990])) 2.4000 3.0000 true 1 [1.0730,6.3580] [1.0230,5.8590] [1.1230,6.8570]
    TB_part #lintel "TB_L1_Lintel_008_L1-017" #(#([0.3490,(-0.0495)],[0.3490,0.0285],[(-0.2810),0.0285],[(-0.2810),0.0495],[0.3490,0.0505],[(-0.3490),0.0495],[(-0.3490),(-0.0505)])) 2.4000 3.0000 true 1 [2.8200,6.9855] [2.4710,6.9350] [3.1690,7.0360]
    TB_part #lintel "TB_L1_Lintel_009_L1-018" #(#([(-0.4870),(-0.6370)],[(-0.4060),(-0.6910)],[0.4870,0.6370],[0.4060,0.6910])) 2.4000 3.0000 true 1 [5.3640,(-7.8430)] [4.8770,(-8.5340)] [5.8510,(-7.1520)]
    TB_part #glass "TB_L1_Glass_027_L1-019 pane" #(#([0.0100,0.2990],[(-0.0100),0.2990],[(-0.0100),(-0.2990)],[0.0100,(-0.2990)])) 0.0000 3.0000 true 1 [5.8620,(-6.3790)] [5.8520,(-6.6780)] [5.8720,(-6.0800)]
    TB_part #glass "TB_L1_Glass_028_L1-020 pane" #(#([0.0065,(-0.8320)],[0.0265,(-0.8320)],[(-0.0065),0.8320],[(-0.0265),0.8320])) 0.0000 3.0000 true 1 [6.2365,(-4.7810)] [6.2100,(-5.6130)] [6.2630,(-3.9490)]
    TB_part #glass "TB_L1_Glass_029_L1-021 transom" #(#([(-0.4615),0.0050],[(-0.4615),(-0.0050)],[0.4615,(-0.0050)],[0.4615,0.0050])) 2.4000 2.6000 false 1 [5.4045,4.8900] [4.9430,4.8850] [5.8660,4.8950]
    TB_part #lintel "TB_L1_Lintel_010_L1-022" #(#([0.0500,0.4865],[(-0.0500),0.4875],[(-0.0500),(-0.4875)],[0.0500,(-0.4865)])) 2.4000 3.0000 true 1 [6.0230,5.4275] [5.9730,4.9400] [6.0730,5.9150]
    TB_part #glass "TB_L1_Glass_030_L1-024 transom" #(#([0.0050,0.7990],[(-0.0050),0.7990],[(-0.0050),(-0.7990)],[0.0050,(-0.7990)])) 2.4000 3.0000 true 1 [1.0730,(-7.8680)] [1.0680,(-8.6670)] [1.0780,(-7.0690)]
    TB_part #railing "TB_L1_Railing_001" #(#([1.2710,0.8750],[(-1.2960),0.8750],[(-1.2960),0.7940],[1.1960,0.7940],[1.1960,(-0.8750)],[1.2960,(-0.8750)],[1.2960,0.8690],[1.2710,0.8690])) 0.0000 1.1000 false 1 [2.9920,8.7520] [1.6960,7.8770] [4.2880,9.6270]
    TB_part #railing "TB_L1_Railing_002" #(#([(-2.2065),0.3870],[(-2.1785),0.3870],[(-2.1785),0.3620],[2.1065,0.3620],[2.1065,(-0.4620)],[2.2065,(-0.4620)],[2.2065,0.4370],[2.1815,0.4370],[2.1815,0.4620],[(-2.1785),0.4620],[(-2.1785),0.4370],[(-2.2035),0.4370])) 0.0000 1.1000 false 1 [(-1.8115),12.2180] [(-4.0180),11.7560] [0.3950,12.6800]
    TB_part #tread "TB_L1_Tread_001_stair S1 tread 1" #(#([0.1000,(-0.4250)],[0.1000,0.4250],[(-0.1000),0.4250],[(-0.1000),(-0.4250)])) 0.0000 0.1670 false 1 [(-3.8830),12.1800] [(-3.9830),11.7550] [(-3.7830),12.6050]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_002_stair S1 tread 2" #(#([0.1000,(-0.4250)],[0.1000,0.4250],[(-0.1000),0.4250],[(-0.1000),(-0.4250)])) 0.0000 0.3330 false 1 [(-3.6830),12.1800] [(-3.7830),11.7550] [(-3.5830),12.6050]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_003_stair S1 tread 3" #(#([0.1000,(-0.4250)],[0.1000,0.4250],[(-0.1000),0.4250],[(-0.1000),(-0.4250)])) 0.1670 0.5000 false 1 [(-3.4830),12.1800] [(-3.5830),11.7550] [(-3.3830),12.6050]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_004_stair S1 tread 4" #(#([0.1000,(-0.4500)],[0.1000,0.4500],[(-0.1000),0.4000],[(-0.1000),(-0.4500)])) 0.3330 0.6670 false 1 [(-3.2830),12.2050] [(-3.3830),11.7550] [(-3.1830),12.6550]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_005_stair S1 tread 5" #(#([0.1000,(-0.4500)],[0.1000,0.4500],[(-0.1000),0.4500],[(-0.1000),(-0.4500)])) 0.5000 0.8330 false 1 [(-3.0830),12.2050] [(-3.1830),11.7550] [(-2.9830),12.6550]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_006_stair S1 tread 6" #(#([0.1000,(-0.4500)],[0.1000,0.4500],[(-0.1000),0.4500],[(-0.1000),(-0.4500)])) 0.6670 1.0000 false 1 [(-2.8830),12.2050] [(-2.9830),11.7550] [(-2.7830),12.6550]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_007_stair S1 tread 7" #(#([0.1000,(-0.4500)],[0.1000,0.4500],[(-0.1000),0.4500],[(-0.1000),(-0.4500)])) 0.8330 1.1670 false 1 [(-2.6830),12.2050] [(-2.7830),11.7550] [(-2.5830),12.6550]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_008_stair S1 tread 8" #(#([0.1000,(-0.4500)],[0.1000,0.4500],[(-0.1000),0.4500],[(-0.1000),(-0.4500)])) 1.0000 1.3330 false 1 [(-2.4830),12.2050] [(-2.5830),11.7550] [(-2.3830),12.6550]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_009_stair S1 tread 9" #(#([0.1000,(-0.4500)],[0.1000,0.4500],[(-0.1000),0.4500],[(-0.1000),(-0.4500)])) 1.1670 1.5000 false 1 [(-2.2830),12.2050] [(-2.3830),11.7550] [(-2.1830),12.6550]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_010_stair S1 tread 10" #(#([0.1000,(-0.4500)],[0.1000,0.4500],[(-0.1000),0.4500],[(-0.1000),(-0.4500)])) 1.3330 1.6670 false 1 [(-2.0830),12.2050] [(-2.1830),11.7550] [(-1.9830),12.6550]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_011_stair S1 tread 11" #(#([0.1000,(-0.4500)],[0.1000,0.4500],[(-0.1000),0.4500],[(-0.1000),(-0.4500)])) 1.5000 1.8330 false 1 [(-1.8830),12.2050] [(-1.9830),11.7550] [(-1.7830),12.6550]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_012_stair S1 tread 12" #(#([0.1000,(-0.4500)],[0.1000,0.4500],[(-0.1000),0.4500],[(-0.1000),(-0.4500)])) 1.6670 2.0000 false 1 [(-1.6830),12.2050] [(-1.7830),11.7550] [(-1.5830),12.6550]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_013_stair S1 tread 13" #(#([0.1000,(-0.4500)],[0.1000,0.4500],[(-0.1000),0.4500],[(-0.1000),(-0.4500)])) 1.8330 2.1670 false 1 [(-1.4830),12.2050] [(-1.5830),11.7550] [(-1.3830),12.6550]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_014_stair S1 tread 14" #(#([0.1000,(-0.4500)],[0.1000,0.4500],[(-0.1000),0.4500],[(-0.1000),(-0.4500)])) 2.0000 2.3330 false 1 [(-1.2830),12.2050] [(-1.3830),11.7550] [(-1.1830),12.6550]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_015_stair S1 tread 15" #(#([0.1000,(-0.4500)],[0.1000,0.4500],[(-0.1000),0.4500],[(-0.1000),(-0.4500)])) 2.1670 2.5000 false 1 [(-1.0830),12.2050] [(-1.1830),11.7550] [(-0.9830),12.6550]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_016_stair S1 tread 16" #(#([0.1000,(-0.4500)],[0.1000,0.4500],[(-0.1000),0.4500],[(-0.1000),(-0.4500)])) 2.3330 2.6670 false 1 [(-0.8830),12.2050] [(-0.9830),11.7550] [(-0.7830),12.6550]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_017_stair S1 tread 17" #(#([0.1250,(-0.4500)],[0.1250,0.4500],[(-0.1250),0.4500],[(-0.1250),(-0.4500)])) 2.5000 2.8330 false 1 [(-0.6580),12.2050] [(-0.7830),11.7550] [(-0.5330),12.6550]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_018_stair S2 tread 1" #(#([0.4710,0.1250],[(-0.4710),0.1250],[(-0.4710),(-0.1250)],[0.4710,(-0.1250)])) 0.0000 0.1430 false 1 [3.7420,8.0090] [3.2710,7.8840] [4.2130,8.1340]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_019_stair S2 tread 2" #(#([0.4710,0.1250],[(-0.4710),0.1250],[(-0.4710),(-0.1250)],[0.4710,(-0.1250)])) 0.0000 0.2860 false 1 [3.7420,8.2590] [3.2710,8.1340] [4.2130,8.3840]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_020_stair S2 tread 3" #(#([0.4710,0.1250],[(-0.4710),0.1250],[(-0.4710),(-0.1250)],[0.4710,(-0.1250)])) 0.1430 0.4290 false 1 [3.7420,8.5090] [3.2710,8.3840] [4.2130,8.6340]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_021_stair S2 tread 5" #(#([0.1250,0.4750],[(-0.1250),0.4750],[(-0.1250),(-0.4750)],[0.1250,(-0.4750)])) 0.4290 0.7140 false 1 [3.1380,9.0960] [3.0130,8.6210] [3.2630,9.5710]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_022_stair S2 tread 6" #(#([0.1250,0.4500],[(-0.1250),0.5000],[(-0.1250),(-0.5000)],[0.1250,(-0.5000)])) 0.5710 0.8570 false 1 [2.8880,9.1210] [2.7630,8.6210] [3.0130,9.6210]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_023_stair S2 tread 7" #(#([0.1250,0.5000],[(-0.1250),0.5000],[(-0.1250),(-0.5000)],[0.1250,(-0.5000)])) 0.7140 1.0000 false 1 [2.6380,9.1210] [2.5130,8.6210] [2.7630,9.6210]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_024_stair S2 tread 8" #(#([0.1250,0.5000],[(-0.1250),0.5000],[(-0.1250),(-0.5000)],[0.1250,(-0.5000)])) 0.8570 1.1430 false 1 [2.3880,9.1210] [2.2630,8.6210] [2.5130,9.6210]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_025_stair S2 tread 10" #(#([(-0.4490),0.1250],[(-0.4490),(-0.1250)],[0.4490,(-0.1250)],[0.4490,0.1250])) 1.1430 1.4290 false 1 [1.8220,8.4880] [1.3730,8.3630] [2.2710,8.6130]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_026_stair S2 tread 11" #(#([(-0.4490),0.1250],[(-0.4490),(-0.1250)],[0.4490,(-0.1250)],[0.4490,0.1250])) 1.2860 1.5710 false 1 [1.8220,8.2380] [1.3730,8.1130] [2.2710,8.3630]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_027_stair S2 tread 13" #(#([0.1265,(-0.5750)],[0.1265,0.5750],[(-0.1265),0.5750],[(-0.1265),(-0.5750)])) 1.5710 1.8570 false 1 [2.6655,7.5890] [2.5390,7.0140] [2.7920,8.1640]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_028_stair S2 tread 14" #(#([0.1250,(-0.5750)],[0.1250,0.5750],[(-0.1250),0.5750],[(-0.1250),(-0.5750)])) 1.7140 2.0000 false 1 [2.9170,7.5890] [2.7920,7.0140] [3.0420,8.1640]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_029_stair S2 tread 15" #(#([0.1250,(-0.5750)],[0.1250,0.5750],[(-0.1250),0.5750],[(-0.1250),(-0.5750)])) 1.8570 2.1430 false 1 [3.1670,7.5890] [3.0420,7.0140] [3.2920,8.1640]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_030_stair S2 tread 16" #(#([0.1250,(-0.5750)],[0.1250,0.5750],[(-0.1250),0.5750],[(-0.1250),(-0.5750)])) 2.0000 2.2860 false 1 [3.4170,7.5890] [3.2920,7.0140] [3.5420,8.1640]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_031_stair S2 tread 17" #(#([0.1250,(-0.5750)],[0.1250,0.5750],[(-0.1250),0.5750],[(-0.1250),(-0.5750)])) 2.1430 2.4290 false 1 [3.6670,7.5890] [3.5420,7.0140] [3.7920,8.1640]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_032_stair S2 tread 18" #(#([0.1250,(-0.5750)],[0.1250,0.5750],[(-0.1250),0.5750],[(-0.1250),(-0.5750)])) 2.2860 2.5710 false 1 [3.9170,7.5890] [3.7920,7.0140] [4.0420,8.1640]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_033_stair S2 tread 19" #(#([0.1250,(-0.5750)],[0.1250,0.5750],[(-0.1250),0.5750],[(-0.1250),(-0.5750)])) 2.4290 2.7140 false 1 [4.1670,7.5890] [4.0420,7.0140] [4.2920,8.1640]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #tread "TB_L1_Tread_034_stair S2 tread 20" #(#([0.1460,(-0.5750)],[0.1460,0.5750],[(-0.1460),0.5750],[(-0.1460),(-0.5750)])) 2.5710 2.8570 false 1 [4.4380,7.5890] [4.2920,7.0140] [4.5840,8.1640]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #landing "TB_L1_Landing_001_stair S2 landing 4" #(#([(-0.4750),0.4750],[(-0.4750),(-0.4750)],[(-0.4670),(-0.4750)],[(-0.4670),(-0.4620)],[0.4750,(-0.4620)],[0.4750,0.4750])) 0.4210 0.5710 false 1 [3.7380,9.0960] [3.2630,8.6210] [4.2130,9.5710]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #landing "TB_L1_Landing_002_stair S2 landing 9" #(#([(-0.4490),(-0.5040)],[0.4490,(-0.5040)],[0.4490,(-0.4960)],[0.4410,(-0.4960)],[0.4410,0.4790],[0.4490,0.4790],[0.4490,0.5040],[(-0.4490),0.5040])) 1.1360 1.2860 false 1 [1.8220,9.1170] [1.3730,8.6130] [2.2710,9.6210]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #landing "TB_L1_Landing_003_stair S2 landing 12" #(#([(-0.5830),(-0.5750)],[0.5830,(-0.5750)],[0.5830,0.5750],[0.3150,0.5750],[0.3150,0.5240],[(-0.5830),0.5240])) 1.5640 1.7140 false 1 [1.9560,7.5890] [1.3730,7.0140] [2.5390,8.1640]
    setUserProp TB_nodes[TB_nodes.count] "TB_storey" 2
    TB_part #slab "TB_L1_Slab_001" #(#([(-6.2905),10.1395],[(-5.7315),(-10.8655)],[0.0735,(-10.8855)],[0.0835,(-11.0545)],[0.6905,(-11.0545)],[0.7005,(-10.8755)],[3.2855,(-10.8725)],[3.2955,(-10.2815)],[4.4825,(-10.2725)],[4.5375,(-10.2235)],[5.4905,(-8.7875)],[5.5005,(-7.7745)],[6.2905,(-7.7645)],[6.2905,(-7.3055)],[5.8915,(-7.2955)],[5.8465,(-5.5075)],[6.0455,(-5.4935)],[6.0395,(-4.6645)],[5.8965,2.0755],[5.6965,2.0815],[5.6495,4.4545],[5.8485,4.4685],[5.7725,8.3025],[0.9165,8.3125],[0.8695,10.1175],[0.4025,10.3745],[0.2015,10.5765],[(-0.0525),11.0205],[(-0.1605),11.0545],[(-4.4655),11.0465],[(-4.6945),10.6955],[(-4.8765),10.5035],[(-5.0905),10.3485],[(-5.3275),10.2335],[(-5.7085),10.1395]),#([(-3.8925),(-8.4615)],[(-2.0915),(-8.4615)],[(-2.0905),(-8.7355)],[(-2.1105),(-8.7365)],[(-2.1105),(-9.8345)],[(-2.0905),(-9.8355)],[(-2.0915),(-10.2365)],[(-3.8925),(-10.2355)])) (-0.2500) 0.0000 false 1 [0.4615,1.6555] [(-5.8290),(-9.3990)] [6.7520,12.7100]
    TB_part #ceiling "TB_L1_Ceiling_001_ceiling" #(#([(-6.2650),10.5560],[(-5.6970),(-10.0780)],[(-5.6970),(-10.3780)],[(-5.6870),(-10.3780)],[(-5.6870),(-10.3880)],[(-1.0840),(-10.3880)],[(-1.0840),(-10.3980)],[0.1060,(-10.3980)],[0.1060,(-10.5570)],[0.1160,(-10.5570)],[0.1160,(-10.5670)],[0.6660,(-10.5670)],[0.6660,(-10.5570)],[0.6760,(-10.5570)],[0.6760,(-10.3880)],[1.0080,(-10.3880)],[1.0080,(-10.3980)],[2.5280,(-10.4020)],[2.5290,(-10.3880)],[3.2610,(-10.3850)],[3.2610,(-10.3750)],[3.2710,(-10.3750)],[3.2710,(-9.7950)],[3.8610,(-9.7950)],[3.8610,(-9.7850)],[4.4760,(-9.7850)],[4.4760,(-9.7170)],[4.5190,(-9.7460)],[5.4130,(-8.4160)],[5.4050,(-8.4100)],[5.4650,(-8.3210)],[5.4650,(-7.8770)],[5.4750,(-7.8770)],[5.4750,(-7.2870)],[6.2550,(-7.2870)],[6.2550,(-7.2770)],[6.2650,(-7.2770)],[6.2650,(-6.8770)],[6.2550,(-6.8770)],[6.2550,(-6.8670)],[5.8670,(-6.8670)],[5.8330,(-5.1440)],[5.8230,(-5.1450)],[5.8200,(-5.0220)],[6.0100,(-5.0180)],[6.0100,(-5.0080)],[6.0200,(-5.0080)],[6.0040,(-4.2080)],[6.0140,(-4.2080)],[5.9630,(-1.6450)],[5.9520,(-1.6450)],[5.9360,(-0.8460)],[5.9460,(-0.8450)],[5.8950,1.7040],[5.8870,1.7040],[5.8710,2.5040],[5.8610,2.5040],[5.8610,2.5140],[5.6710,2.5100],[5.6230,4.9400],[5.8130,4.9430],[5.8130,4.9530],[5.8230,4.9540],[5.7940,6.4230],[5.7840,6.4230],[5.7720,7.0030],[5.7820,7.0030],[5.7480,8.7300],[5.7380,8.7300],[5.7380,8.7400],[4.0750,8.7400],[4.0750,7.6890],[2.8560,7.6890],[2.8560,7.6250],[4.1120,7.6270],[4.1120,7.0300],[2.2030,7.0330],[2.1840,7.0400],[2.1670,7.0520],[2.1550,7.0680],[2.1480,7.0880],[2.1470,7.3730],[1.8640,7.3730],[1.8640,7.0160],[4.0770,7.0160],[4.0770,5.7660],[0.8660,5.7660],[0.8660,8.4730],[2.0810,8.4730],[2.0810,8.7400],[0.8920,8.7400],[0.8440,10.5570],[0.8340,10.5570],[0.8340,10.5670],[(-1.0400),10.5670],[(-1.0400),10.5070],[(-3.8900),10.5070],[(-3.8900),10.5670],[(-6.2550),10.5670],[(-6.2550),10.5570]),#([(-2.0870),(-8.0050)],[(-2.0870),(-8.2780)],[(-2.1070),(-8.2780)],[(-2.1070),(-9.3780)],[(-2.0870),(-9.3780)],[(-2.0870),(-9.7780)],[(-3.8870),(-9.7780)],[(-3.8870),(-8.0050)])) 2.6800 2.7000 false 1 [0.4570,1.1980] [(-5.8080),(-9.3690)] [6.7220,11.7650]
    TB_part #wall "TB_L2_Wall_001" #(#([(-0.6125),(-0.3505)],[(-0.0625),(-0.3505)],[(-0.0625),(-0.1505)],[0.6125,(-0.1505)],[0.6125,(-0.0505)],[(-0.0715),(-0.0505)],[(-0.0715),0.3505],[(-0.1715),0.3505],[(-0.1725),(-0.0505)],[(-0.6125),(-0.0505)])) 0.0000 3.0000 true 2 [1.1855,(-9.0285)] [0.5730,(-9.3790)] [1.7980,(-8.6780)]
    TB_part #wall "TB_L2_Wall_002" #(#([0.0465,(-0.1975)],[(-0.0055),(-0.1615)],[(-0.0565),(-0.1105)],[(-0.0955),(-0.0545)],[(-0.1245),0.0075],[(-0.1435),0.0775],[(-0.1495),0.1455],[(-0.1495),0.3545],[(-0.2495),0.3545],[(-0.2495),(-0.3545)],[0.2495,(-0.3545)],[0.2495,(-0.2545)],[0.1805,(-0.2475)],[0.1115,(-0.2285)]),#([(-0.1495),(-0.2545)],[(-0.1495),(-0.0785)],[(-0.0675),(-0.1725)],[0.0265,(-0.2545)])) 0.0000 3.0000 true 2 [2.8555,(-3.1675)] [2.6060,(-3.5220)] [3.1050,(-2.8130)]
    TB_part #wall "TB_L2_Wall_003" #(#([(-1.1700),(-5.2715)],[(-1.1700),(-5.2215)],[1.2700,(-5.2215)],[1.2700,(-5.1215)],[(-1.1700),(-5.1215)],[(-1.1700),5.1715],[(-0.0180),5.1715],[(-0.0180),5.2715],[(-1.2700),5.2715],[(-1.2700),(-5.2715)])) 0.0000 3.0000 true 2 [(-2.3100),(-0.2585)] [(-3.5800),(-5.5300)] [(-1.0400),5.0130]
    TB_part #wall "TB_L2_Wall_004" #(#([0.0500,(-0.9990)],[0.0500,0.9990],[(-0.0500),0.9990],[(-0.0500),(-0.9990)])) 0.0000 3.0000 true 2 [2.6560,0.0990] [2.6060,(-0.9000)] [2.7060,1.0980]
    TB_part #wall "TB_L2_Wall_005" #(#([5.8745,8.3665],[5.8855,7.8335],[6.0355,7.8365],[6.0145,8.8985],[1.0975,8.8985],[1.0535,10.4715],[0.7545,10.4625],[(-5.7355),10.4715],[(-6.0355),10.4635],[(-5.4635),(-10.4635)],[(-5.4595),(-10.4715)],[(-5.1595),(-10.4635)],[(-1.0445),(-10.4635)],[(-1.0445),(-10.3635)],[(-1.7175),(-10.3635)],[(-1.7175),(-9.4635)],[(-1.8675),(-9.4635)],[(-1.8675),(-9.8635)],[(-3.6675),(-9.8635)],[(-3.6675),(-8.1135)],[(-1.8675),(-8.1135)],[(-1.8675),(-8.3635)],[(-1.7175),(-8.3635)],[(-1.7175),(-7.9635)],[0.7795,(-7.9605)],[0.7795,(-8.2815)],[0.8795,(-8.2815)],[0.8805,(-7.6605)],[0.3305,(-7.6605)],[0.3305,(-7.8635)],[(-3.7175),(-7.8635)],[(-3.7175),(-7.8135)],[(-3.8175),(-7.8135)],[(-3.8175),(-10.3635)],[(-5.1625),(-10.3635)],[(-5.1675),(-10.1635)],[(-5.2285),(-10.1655)],[(-5.2285),(-8.0735)],[(-4.6175),(-8.0735)],[(-4.6175),(-7.9735)],[(-5.2285),(-7.9735)],[(-5.2375),(-7.6455)],[(-5.3875),(-7.6495)],[(-5.4645),(-4.8395)],[(-5.3145),(-4.8355)],[(-5.3225),(-4.5355)],[(-5.4725),(-4.5395)],[(-5.5585),(-1.4295)],[(-5.4085),(-1.4235)],[(-5.4165),(-1.1255)],[(-5.5665),(-1.1295)],[(-5.6495),1.8705],[(-5.4995),1.8745],[(-5.5075),2.1745],[(-5.6575),2.1705],[(-5.7475),5.4275],[(-3.2325),5.4315],[(-3.2325),7.4465],[(-3.3325),7.4465],[(-3.3325),5.5315],[(-5.5995),5.5315],[(-5.6055),5.7315],[(-5.7555),5.7275],[(-5.8265),8.3215],[(-2.7455),8.3215],[(-2.7455),8.4215],[(-3.2325),8.4215],[(-3.2325),8.4965],[(-3.3325),8.4965],[(-3.3325),8.4215],[(-4.2275),8.4215],[(-4.2275),8.5985],[(-4.3275),8.5985],[(-4.3275),8.4215],[(-5.7275),8.4215],[(-5.7275),9.4025],[(-4.3275),9.4025],[(-4.3275),9.3785],[(-4.2275),9.3785],[(-4.2275),9.5395],[(-4.3275),9.5395],[(-4.3275),9.5025],[(-5.7185),9.5025],[(-5.7315),10.3215],[(-2.0155),10.3165],[(-2.0155),9.3215],[(-2.8455),9.3215],[(-2.8455),9.2015],[(-2.7455),9.2015],[(-2.7455),9.2215],[(-1.5155),9.2215],[(-1.5155),9.2015],[(-1.4155),9.2015],[(-1.4155),9.3215],[(-1.9155),9.3215],[(-1.9155),10.3165],[0.0825,10.3135],[0.0825,10.1955],[0.1825,10.1955],[0.1825,10.3135],[0.7585,10.3125],[0.7625,10.1625],[0.9125,10.1675],[0.9485,8.8495],[0.1825,8.8495],[0.1825,9.4155],[0.0825,9.4155],[0.0825,8.4215],[(-1.5155),8.4215],[(-1.5155),7.9425],[(-1.4155),7.9425],[(-1.4155),8.3215],[0.9635,8.3215],[1.0345,5.7265],[0.8845,5.7225],[0.8815,5.7135],[0.4515,5.7015],[(-1.4155),5.7015],[(-1.4155),6.2625],[(-1.5155),6.2625],[(-1.5155),3.7295],[(-1.5655),3.7295],[(-1.5655),3.6295],[(-1.0155),3.6295],[(-1.0165),3.7295],[(-1.4155),3.7265],[(-1.4155),5.6015],[0.8875,5.6015],[0.8925,5.4225],[1.1925,5.4315],[1.1875,5.6305],[1.9665,5.6305],[1.9665,3.6295],[1.9765,3.6295],[1.9765,5.6305],[4.5765,5.6315],[4.5765,5.7315],[1.1845,5.7305],[1.1155,8.2485],[1.6015,8.2485],[1.6015,8.7485],[5.5175,8.7485],[5.5245,8.3595])) 0.0000 3.0000 true 2 [0.2375,1.2835] [(-5.7980),(-9.1880)] [6.2730,11.7550]
    TB_part #wall "TB_L2_Wall_006" #(#([(-0.0955),0.0545],[(-0.0545),0.1125],[(-0.0055),0.1615],[0.0505,0.2015],[0.1125,0.2305],[0.1795,0.2485],[0.2495,0.2545],[0.2495,0.3545],[(-0.2495),0.3545],[(-0.2495),(-0.3545)],[(-0.1495),(-0.3545)],[(-0.1495),(-0.1455)],[(-0.1435),(-0.0745)],[(-0.1245),(-0.0075)]),#([0.0265,0.2545],[(-0.0675),0.1725],[(-0.1495),0.0795],[(-0.1495),0.2545])) 0.0000 3.0000 true 2 [2.8555,3.3515] [2.6060,2.9970] [3.1050,3.7060]
    TB_part #wall "TB_L2_Wall_007" #(#([(-0.3400),0.0500],[(-0.3400),(-0.0500)],[0.3400,(-0.0500)],[0.3400,0.0500])) 0.0000 3.0000 true 2 [4.0180,(-9.1290)] [3.6780,(-9.1790)] [4.3580,(-9.0790)]
    TB_part #wall "TB_L2_Wall_008" #(#([(-0.3375),(-0.0265)],[(-0.3375),(-0.1265)],[0.2205,(-0.1265)],[0.3375,0.0415],[0.2135,0.1265],[0.1075,(-0.0265)])) 0.0000 3.0000 true 2 [5.3755,(-9.0525)] [5.0380,(-9.1790)] [5.7130,(-8.9260)]
    TB_part #wall "TB_L2_Wall_009" #(#([0.1560,(-0.0680)],[0.1450,0.3390],[(-0.0050),0.3350],[0.0050,(-0.0230)],[(-0.1560),(-0.2540)],[(-0.0330),(-0.3390)])) 0.0000 3.0000 true 2 [6.5330,(-7.5390)] [6.3770,(-7.8780)] [6.6890,(-7.2000)]
    TB_part #wall "TB_L2_Wall_010" #(#([0.1500,(-0.1255)],[0.1500,0.3145],[0.0520,0.3145],[0.0400,0.7295],[(-0.0600),0.7275],[(-0.0600),0.3145],[(-0.1500),0.3145],[(-0.1500),(-0.1255)],[(-0.0890),(-0.1255)],[(-0.0720),(-0.7295)],[0.0780,(-0.7255)],[0.0610,(-0.1255)])) 0.0000 3.0000 true 2 [6.5800,(-5.7945)] [6.4300,(-6.5240)] [6.7300,(-5.0650)]
    TB_part #wall "TB_L2_Wall_011" #(#([(-0.0690),(-0.3370)],[(-0.1160),(-0.3790)],[(-0.1720),(-0.4140)],[(-0.2320),(-0.4400)],[(-0.2980),(-0.4560)],[(-0.3620),(-0.4610)],[(-0.3620),(-0.5620)],[0.0590,(-0.5620)],[0.0590,(-0.5520)],[0.1620,(-0.5490)],[0.1670,(-0.7290)],[0.2670,(-0.7260)],[0.2620,(-0.5460)],[0.3620,(-0.5430)],[0.3480,(-0.0430)],[0.2460,(-0.0460)],[0.2240,0.7290],[0.1240,0.7260],[0.1460,(-0.0490)],[0.0480,(-0.0520)],[0.0310,(-0.1670)],[0.0070,(-0.2280)],[(-0.0290),(-0.2890)]),#([0.0590,(-0.4500)],[(-0.1290),(-0.4550)],[(-0.0260),(-0.3650)],[0.0540,(-0.2660)])) 0.0000 3.0000 true 2 [6.3140,(-2.9600)] [5.9520,(-3.6890)] [6.6760,(-2.2310)]
    TB_part #wall "TB_L2_Wall_012" #(#([0.0350,0.9400],[(-0.1660),0.9340],[(-0.1120),(-0.9400)],[0.0870,(-0.9340)],[0.0650,(-0.1590)],[0.1660,(-0.1560)],[0.1520,0.3440],[0.0540,0.3410])) 0.0000 3.0000 true 2 [6.4120,0.0830] [6.2460,(-0.8570)] [6.5780,1.0230]
    TB_part #wall "TB_L2_Wall_013" #(#([0.2855,(-1.0390)],[0.2605,(-0.2380)],[0.3695,(-0.2350)],[0.3545,0.2650],[0.2505,0.2620],[0.2285,1.0420],[0.1285,1.0390],[0.1505,0.2590],[(-0.3695),0.2600],[(-0.3695),0.1640],[(-0.2995),0.1640],[(-0.2355),0.1540],[(-0.1735),0.1330],[(-0.1135),0.1010],[(-0.0625),0.0600],[(-0.0155),0.0090],[0.0205,(-0.0470)],[0.0475,(-0.1090)],[0.0625,(-0.1750)],[0.0665,(-0.2420)],[0.1605,(-0.2440)],[0.1865,(-1.0420)]),#([0.0625,(-0.0020)],[(-0.0185),0.0880],[(-0.1075),0.1640],[0.0575,0.1640])) 0.0000 3.0000 true 2 [6.1165,3.4420] [5.7470,2.4000] [6.4860,4.4840]
    TB_part #wall "TB_L2_Wall_014" #(#([0.1235,0.1240],[0.1495,(-0.7900)],[0.2495,(-0.7870)],[0.2235,0.1260],[0.2625,0.1270],[0.2495,0.7900],[0.0995,0.7870],[0.1025,0.6240],[(-0.2475),0.6170],[(-0.2425),0.3660],[(-0.2625),0.3660],[(-0.2625),0.2660],[(-0.2405),0.2660],[(-0.2375),0.1170])) 0.0000 3.0000 true 2 [6.0565,6.6500] [5.7940,5.8600] [6.3190,7.4400]
    TB_part #column "TB_L2_Column_001" #(#([0.2750,(-0.1500)],[0.2750,0.1500],[(-0.2750),0.1500],[(-0.2750),(-0.1500)])) 0.0000 3.0000 true 2 [0.8480,(-3.4220)] [0.5730,(-3.5720)] [1.1230,(-3.2720)]
    TB_part #column "TB_L2_Column_002" #(#([0.2750,0.1500],[(-0.2750),0.1500],[(-0.2750),(-0.1500)],[0.2750,(-0.1500)])) 0.0000 3.0000 true 2 [0.8300,(-0.0000)] [0.5550,(-0.1500)] [1.1050,0.1500]
    TB_part #column "TB_L2_Column_003" #(#([(-0.2750),(-0.1500)],[0.2750,(-0.1500)],[0.2750,0.1500],[(-0.2750),0.1500])) 0.0000 3.0000 true 2 [0.8310,3.3000] [0.5560,3.1500] [1.1060,3.4500]
    TB_part #parapet "TB_L2_Parapet_001_parapet" #(#([0.9235,(-0.1270)],[0.8715,(-0.2430)],[0.8125,(-0.3560)],[0.6785,(-0.5710)],[0.5225,(-0.7710)],[0.4365,(-0.8650)],[0.2515,(-1.0380)],[0.0485,(-1.1910)],[(-0.0575),(-1.2590)],[(-0.2815),(-1.3790)],[(-0.5175),(-1.4740)],[(-0.7605),(-1.5450)],[(-1.0105),(-1.5890)],[(-1.2635),(-1.6070)],[(-1.2605),(-1.7570)],[(-0.9925),(-1.7380)],[(-0.8585),(-1.7180)],[(-0.5965),(-1.6570)],[(-0.3415),(-1.5690)],[(-0.0975),(-1.4540)],[0.1335,(-1.3150)],[0.3485,(-1.1530)],[0.4485,(-1.0630)],[0.6355,(-0.8690)],[0.8015,(-0.6570)],[0.9435,(-0.4280)],[1.0615,(-0.1860)],[1.1535,0.0680],[1.2185,0.3290],[1.2555,0.5960],[1.2635,0.7300],[1.2395,1.7570],[1.0895,1.7530],[1.1145,0.8620],[1.1065,0.6090],[1.0715,0.3570],[1.0105,0.1110])) 0.0000 1.1000 false 2 [6.9605,(-9.0920)] [5.6970,(-10.8490)] [8.2240,(-7.3350)]
    TB_part #glass "TB_L2_Glass_001_GLASS WALL 2600H 20X100" #(#([1.2800,(-0.0050)],[1.3200,0.0000],[1.3190,0.0050],[(-1.3200),0.0050],[(-1.3200),(-0.0050)])) 0.0000 2.6000 false 2 [4.4260,3.6560] [3.1060,3.6510] [5.7460,3.6610]
    TB_part #glass "TB_L2_Glass_002_GLASS WALL 2600H 20X100" #(#([1.4225,(-0.0050)],[1.4225,0.0050],[(-1.4225),0.0050],[(-1.4225),(-0.0050)])) 0.0000 2.6000 false 2 [4.5285,(-3.4720)] [3.1060,(-3.4770)] [5.9510,(-3.4670)]
    TB_part #glass "TB_L2_Glass_003_GLASS WALL 2600H 20X100" #(#([(-0.0050),(-0.9485)],[0.0050,(-0.9485)],[0.0050,0.9485],[(-0.0050),0.9485])) 0.0000 2.6000 false 2 [2.6560,2.0475] [2.6510,1.0990] [2.6610,2.9960]
    TB_part #glass "TB_L2_Glass_004_GLASS WALL 2600H 20X100" #(#([(-0.0050),(-0.3340)],[0.0050,(-0.3340)],[0.0050,0.3340],[(-0.0050),0.3340])) 0.0000 2.6000 false 2 [2.6560,(-1.2350)] [2.6510,(-1.5690)] [2.6610,(-0.9010)]
    TB_part #glass "TB_L2_Glass_005_GLASS WALL 2600H 20X100" #(#([(-0.0050),(-0.1715)],[0.0050,(-0.1715)],[0.0050,0.1715],[(-0.0050),0.1715])) 0.0000 2.6000 false 2 [2.6560,(-2.6405)] [2.6510,(-2.8120)] [2.6610,(-2.4690)]
    TB_part #lintel "TB_L2_Lintel_001_L2-001" #(#([(-0.9390),0.0500],[(-0.9390),(-0.0500)],[0.9390,(-0.0500)],[0.9390,0.0500])) 2.0000 3.0000 true 2 [2.7380,(-9.1290)] [1.7990,(-9.1790)] [3.6770,(-9.0790)]
    TB_part #lintel "TB_L2_Lintel_002_L2-002" #(#([0.3390,(-0.0500)],[0.3390,0.0500],[(-0.3390),0.0500],[(-0.3390),(-0.0500)])) 2.4000 3.0000 true 2 [4.6980,(-9.1290)] [4.3590,(-9.1790)] [5.0370,(-9.0790)]
    TB_part #lintel "TB_L2_Lintel_003_L2-003" #(#([0.0500,0.8395],[(-0.0500),0.8395],[(-0.0500),(-0.8385)],[0.0500,(-0.8395)])) 2.0000 3.0000 true 2 [1.0670,(-7.8385)] [1.0170,(-8.6780)] [1.1170,(-6.9990)]
    TB_part #lintel "TB_L2_Lintel_004_L2-004" #(#([0.4990,(-0.0500)],[0.4990,0.0500],[(-0.4990),0.0500],[(-0.4990),(-0.0500)])) 2.4000 3.0000 true 2 [(-1.8280),4.9630] [(-2.3270),4.9130] [(-1.3290),5.0130]
    TB_part #lintel "TB_L2_Lintel_005_L2-005" #(#([(-0.0500),(-0.4990)],[0.0500,(-0.4990)],[0.0500,0.4990],[(-0.0500),0.4990])) 2.4000 3.0000 true 2 [(-3.5300),(-6.0300)] [(-3.5800),(-6.5290)] [(-3.4800),(-5.5310)]
    TB_part #lintel "TB_L2_Lintel_006_L2-006" #(#([0.0750,0.5490],[(-0.0750),0.5490],[(-0.0750),(-0.5490)],[0.0750,(-0.5490)])) 2.4000 3.0000 true 2 [(-1.5550),(-7.6300)] [(-1.6300),(-8.1790)] [(-1.4800),(-7.0810)]
    TB_part #lintel "TB_L2_Lintel_007_L2-007" #(#([(-0.0500),(-0.3890)],[0.0500,(-0.3890)],[0.0500,0.3890],[(-0.0500),0.3890])) 2.4000 3.0000 true 2 [0.3700,11.0890] [0.3200,10.7000] [0.4200,11.4780]
    TB_part #lintel "TB_L2_Lintel_008_L2-008" #(#([(-0.0500),(-0.8390)],[0.0500,(-0.8390)],[0.0500,0.8390],[(-0.0500),0.8390])) 2.0000 3.0000 true 2 [(-1.2280),8.3860] [(-1.2780),7.5470] [(-1.1780),9.2250]
    TB_part #lintel "TB_L2_Lintel_009_L2-009" #(#([(-0.0585),(-0.8405)],[0.0915,(-0.8375)],[0.0585,0.8405],[(-0.0915),0.8375])) 2.0000 3.0000 true 2 [6.2145,8.2785] [6.1230,7.4380] [6.3060,9.1190]
    TB_part #glass "TB_L2_Glass_006_L2-010 transom" #(#([(-0.0050),(-0.4490)],[0.0050,(-0.4490)],[0.0050,0.4490],[(-0.0050),0.4490])) 2.4000 2.6000 false 2 [2.6560,(-2.0190)] [2.6510,(-2.4680)] [2.6610,(-1.5700)]
    TB_part #lintel "TB_L2_Lintel_010_L2-011" #(#([0.0305,0.6900],[(-0.0695),0.6870],[(-0.0305),(-0.6900)],[0.0695,(-0.6870)])) 2.0000 3.0000 true 2 [6.2755,5.1720] [6.2060,4.4820] [6.3450,5.8620]
    TB_part #lintel "TB_L2_Lintel_011_L2-012" #(#([0.4550,0.5235],[0.3320,0.6085],[(-0.4550),(-0.5225)],[(-0.3320),(-0.6085)])) 2.0000 3.0000 true 2 [6.0450,(-8.4025)] [5.5900,(-9.0110)] [6.5000,(-7.7940)]
    TB_part #lintel "TB_L2_Lintel_012_L2-013" #(#([0.0655,0.3410],[(-0.0845),0.3370],[(-0.0655),(-0.3410)],[0.0845,(-0.3370)])) 2.4000 3.0000 true 2 [6.5925,(-6.8620)] [6.5080,(-7.2030)] [6.6770,(-6.5210)]
    TB_part #lintel "TB_L2_Lintel_013_L2-014" #(#([0.6890,(-0.0500)],[0.6890,0.0500],[(-0.6890),0.0500],[(-0.6890),(-0.0500)])) 2.0000 3.0000 true 2 [(-0.1170),(-9.1300)] [(-0.8060),(-9.1800)] [0.5720,(-9.0800)]
    TB_part #lintel "TB_L2_Lintel_014_L2-015" #(#([0.3990,(-0.0500)],[0.3990,0.0500],[(-0.3990),0.0500],[(-0.3990),(-0.0500)])) 2.4000 3.0000 true 2 [(-3.9800),(-6.7400)] [(-4.3790),(-6.7900)] [(-3.5810),(-6.6900)]
    TB_part #lintel "TB_L2_Lintel_015_L2-016" #(#([0.0500,0.4365],[(-0.0500),0.4365],[(-0.0500),(-0.4365)],[0.0500,(-0.4365)])) 2.4000 3.0000 true 2 [(-3.0450),9.1675] [(-3.0950),8.7310] [(-2.9950),9.6040]
    TB_part #lintel "TB_L2_Lintel_016_L2-018" #(#([0.0500,0.3890],[(-0.0500),0.3890],[(-0.0500),(-0.3890)],[0.0500,(-0.3890)])) 2.4000 3.0000 true 2 [(-4.0400),10.2720] [(-4.0900),9.8830] [(-3.9900),10.6610]
    TB_part #lintel "TB_L2_Lintel_017_L2-019" #(#([0.4890,(-0.0495)],[0.4890,0.0505],[(-0.4890),0.0495],[(-0.4890),(-0.0505)])) 2.4000 3.0000 true 2 [5.3040,6.9655] [4.8150,6.9150] [5.7930,7.0160]
    TB_part #lintel "TB_L2_Lintel_018_L2-020" #(#([(-0.0285),(-0.6905)],[0.0715,(-0.6875)],[0.0285,0.6905],[(-0.0715),0.6875])) 2.0000 3.0000 true 2 [6.3745,1.7115] [6.3030,1.0210] [6.4460,2.4020]
    TB_part #lintel "TB_L2_Lintel_019_L2-021" #(#([0.0710,(-0.6870)],[0.0320,0.6900],[(-0.0710),0.6880],[(-0.0310),(-0.6900)])) 2.0000 3.0000 true 2 [6.5490,(-4.3770)] [6.4780,(-5.0670)] [6.6200,(-3.6870)]
    TB_part #lintel "TB_L2_Lintel_020_L2-022" #(#([0.0305,0.6905],[(-0.0695),0.6875],[(-0.0305),(-0.6905)],[0.0695,(-0.6875)])) 2.0000 3.0000 true 2 [6.4685,(-1.5425)] [6.3990,(-2.2330)] [6.5380,(-0.8520)]
    TB_part #lintel "TB_L2_Lintel_021_L2-023" #(#([0.0500,0.3890],[(-0.0500),0.3890],[(-0.0500),(-0.3890)],[0.0500,(-0.3890)])) 2.4000 3.0000 true 2 [(-4.0400),11.2130] [(-4.0900),10.8240] [(-3.9900),11.6020]
    TB_part #lintel "TB_L2_Lintel_022_L2-024" #(#([0.0500,0.3890],[(-0.0500),0.3890],[(-0.0500),(-0.3890)],[0.0500,(-0.3890)])) 2.4000 3.0000 true 2 [(-1.2280),10.0950] [(-1.2780),9.7060] [(-1.1780),10.4840]
    TB_part #lintel "TB_L2_Lintel_023_L2-025" #(#([0.0500,0.3885],[(-0.0500),0.3895],[(-0.0500),(-0.3895)],[0.0500,(-0.3895)])) 2.4000 3.0000 true 2 [(-2.6050),10.0955] [(-2.6550),9.7060] [(-2.5550),10.4850]
    TB_part #railing "TB_L2_Railing_001" #(#([0.8285,(-8.7990)],[0.9785,(-8.7960)],[0.6485,8.6500],[0.6735,8.6500],[0.6715,8.7500],[0.6215,8.7490],[0.6205,8.7990],[0.5205,8.7970],[0.5205,8.7720],[(-0.9785),8.7420],[(-0.9745),8.5920],[0.4985,8.6220])) 0.0000 1.1000 false 2 [7.2295,1.4610] [6.2510,(-7.3380)] [8.2080,10.2600]
    TB_part #railing "TB_L2_Railing_002" #(#([(-5.4510),(-0.1560)],[(-5.4510),(-0.1810)],[5.4780,0.0310],[5.4750,0.1810],[(-5.4540),(-0.0310)],[(-5.4530),(-0.0560)],[(-5.4780),(-0.0560)],[(-5.4760),(-0.1560)])) 0.0000 1.1000 false 2 [0.2210,(-10.8800)] [(-5.2570),(-11.0610)] [5.6990,(-10.6990)]
    TB_part #slab "TB_L2_Slab_001" #(#([(-7.0405),10.9760],[(-6.4735),(-10.0080)],[(-6.3805),(-10.1380)],[(-6.2635),(-10.4130)],[(-6.1985),(-10.8570)],[(-6.2695),(-11.2990)],[(-6.4965),(-11.7390)],[(-6.4935),(-11.8670)],[(-6.4095),(-11.9000)],[4.4515,(-11.6900)],[4.7905,(-11.6650)],[5.1235,(-11.5960)],[5.6985,(-11.3630)],[5.9315,(-11.2180)],[6.2385,(-10.9660)],[6.4325,(-10.7590)],[6.6985,(-10.3780)],[6.9405,(-9.8050)],[7.0405,(-9.2050)],[6.7015,9.0330],[6.7165,9.4190],[6.6085,9.4800],[5.0455,9.4120],[0.1625,9.4120],[0.1195,10.9630],[(-0.3425),11.2170],[(-0.5455),11.4190],[(-0.8025),11.8660],[(-0.9105),11.9000],[(-1.8235),11.8980],[(-1.8235),11.8690],[(-1.7935),11.8680],[(-1.7935),10.8940],[(-4.6445),10.8940],[(-4.6455),11.8340],[(-4.5275),11.8640],[(-4.4055),11.8640],[(-4.3815),11.8700],[(-4.3845),11.8930],[(-5.2155),11.8920],[(-5.4825),11.4920],[(-5.7125),11.2750],[(-5.9845),11.1120],[(-6.4165),10.9840]),#([0.1115,8.8610],[1.3255,8.8620],[1.3265,9.2230],[3.3215,9.2230],[3.3215,8.0770],[2.1025,8.0760],[2.1025,8.0140],[3.3575,8.0160],[3.3585,7.4170],[1.4485,7.4200],[1.4285,7.4270],[1.4125,7.4390],[1.3995,7.4560],[1.3925,7.4760],[1.3915,7.7600],[1.1105,7.7600],[1.1105,7.4050],[3.3235,7.4050],[3.3235,6.1540],[0.1105,6.1540]),#([(-4.6425),(-7.6390)],[(-2.8415),(-7.6390)],[(-2.8405),(-7.8900)],[(-2.8605),(-7.8910)],[(-2.8605),(-8.9890)],[(-2.8405),(-8.9900)],[(-2.8415),(-9.3910)],[(-4.6425),(-9.3900)])) (-0.2500) 0.0000 false 2 [1.2115,0.8100] [(-5.8290),(-11.0900)] [8.2520,12.7100]
    TB_part #ceiling "TB_L2_Ceiling_001_ceiling" #(#([(-6.2740),10.5580],[(-5.6980),(-10.3760)],[(-5.6880),(-10.3760)],[(-5.6880),(-10.3860)],[(-5.3880),(-10.3780)],[(-1.2730),(-10.3780)],[(-1.2730),(-10.3880)],[0.0970,(-10.3880)],[0.0970,(-10.5670)],[0.1070,(-10.5670)],[0.1070,(-10.5770)],[0.6570,(-10.5770)],[0.6570,(-10.5670)],[0.6670,(-10.5670)],[0.6670,(-10.3770)],[1.3320,(-10.3770)],[1.3320,(-10.3870)],[3.2120,(-10.3870)],[3.2120,(-10.3770)],[3.8920,(-10.3770)],[3.8920,(-10.3870)],[4.5720,(-10.3870)],[4.5720,(-10.3770)],[5.1350,(-10.3770)],[5.2550,(-10.2050)],[5.2630,(-10.2110)],[6.0510,(-9.0780)],[6.0420,(-9.0720)],[6.2330,(-8.7980)],[6.2220,(-8.3870)],[6.2310,(-8.3870)],[6.2120,(-7.7070)],[6.2020,(-7.7080)],[6.1850,(-7.1180)],[6.2640,(-7.1180)],[6.2640,(-7.1080)],[6.2740,(-7.1080)],[6.2740,(-6.6680)],[6.2640,(-6.6680)],[6.2640,(-6.6580)],[6.1760,(-6.6580)],[6.1640,(-6.2520)],[6.1740,(-6.2510)],[6.1350,(-4.8730)],[6.1250,(-4.8730)],[6.1200,(-4.7040)],[6.2100,(-4.7010)],[6.2100,(-4.6910)],[6.2200,(-4.6910)],[6.2060,(-4.1910)],[6.1960,(-4.1910)],[6.1950,(-4.1810)],[6.1040,(-4.1840)],[6.0820,(-3.4190)],[6.0920,(-3.4180)],[6.0530,(-2.0390)],[6.0430,(-2.0390)],[6.0210,(-1.2740)],[6.1130,(-1.2710)],[6.1120,(-1.2610)],[6.1220,(-1.2610)],[6.1080,(-0.7610)],[6.0980,(-0.7610)],[6.0980,(-0.7510)],[6.0090,(-0.7540)],[5.9910,(-0.1640)],[6.0000,(-0.1640)],[5.9560,1.2150],[5.9460,1.2150],[5.9210,2.0070],[6.0200,2.0090],[6.0200,2.0190],[6.0300,2.0200],[6.0150,2.5190],[6.0050,2.5190],[6.0050,2.5290],[5.9110,2.5270],[5.8890,3.2960],[5.8990,3.2960],[5.8600,4.6760],[5.8500,4.6760],[5.8240,5.5780],[5.8530,5.5790],[5.8530,5.5890],[5.8630,5.5890],[5.8500,6.2520],[5.8600,6.2520],[5.8270,7.9320],[5.8170,7.9320],[5.7960,8.9940],[5.7860,8.9940],[5.7860,9.0040],[0.8780,9.0040],[0.8350,10.5670],[0.8250,10.5670],[0.8250,10.5770],[0.5250,10.5680],[(-5.9650),10.5770],[(-6.2650),10.5690],[(-6.2640),10.5590]),#([(-2.0960),(-9.7680)],[(-3.8960),(-9.7680)],[(-3.8960),(-8.0180)],[(-2.0960),(-8.0180)],[(-2.0960),(-8.2680)],[(-2.1160),(-8.2680)],[(-2.1160),(-9.3680)],[(-2.0960),(-9.3680)])) 2.6800 2.7000 false 2 [0.4660,1.1880] [(-5.8080),(-9.3890)] [6.7400,11.7650]
    for f in TB_floorNames do
    (
        local ly = LayerManager.getLayerFromName ("TB_" + f + "_Ceilings")
        if ly != undefined do ly.isHidden = true
    )
    TB_lines "TB_L1_StairsAbove" #(#([0.4800,(-0.4535)],[0.4800,0.4535]),#([(-0.4800),(-0.4535)],[0.4800,(-0.4535)]),#([0.4800,0.4535],[(-0.4800),0.4535])) 1 [(-0.1100),12.2015] "StairsAbove"
    TB_lines "TB_L2_Stairs" #(#([(-2.3045),1.4300],[(-1.9145),1.4300]),#([2.3045,(-1.4300)],[2.3045,(-0.2860)]),#([2.2895,(-1.4300)],[2.2895,(-0.2860)])) 2 [2.2345,10.3180] "Stairs"
    TB_lines "TB_L2_StairsAbove" #(#([(-0.0165),0.0000],[(-0.7165),0.0000]),#([0.7165,0.0000],[(-0.0165),0.0000])) 2 [2.5555,10.0320] "StairsAbove"
    TB_room "TOILET - 3.2 m2" [(-4.5230),(-7.8950)] 1
    TB_room "LIFT HALL - 6.1 m2" [(-0.8860),(-7.7710)] 1
    TB_room "TOILET - 2.6 m2" [1.7870,8.2640] 1
    TB_room "MEEETING 4 PAX - 8.2 m2" [1.9000,5.6690] 1
    TB_room "MANAGER - 11.4 m2" [(-1.8350),3.0020] 1
    TB_room "F/C - 3.9 m2" [(-4.4020),6.2750] 1
    TB_room "LIFT HALL - 6.0 m2" [(-0.6490),(-7.7680)] 2
    TB_room "PANTRY - 3.9 m2" [(-4.6300),(-7.7680)] 2
    TB_room "F/C - 5.5 m2" [(-0.0260),8.3390] 2
    TB_room "MALE TOILET - 4.7 m2" [(-1.1590),10.7810] 2
    TB_room "FEMALE TOILET - 6.4 m2" [(-3.7950),10.7810] 2
    TB_room "RACK - 7.3 m2" [(-4.5400),8.1250] 2
    TB_room "BOH" [(-4.9590),1.3600] 2
    if TB_furnWant do TB_furnRun()
    local origin = point name:"TB_ORIGIN_DWG" size:1.0 pos:[0.0 - TB_shift.x, 0.0 - TB_shift.y, 0.0]
    origin.isHidden = true
    origin.ignoreExtents = true
    (TB_layer "TB_Datums").addNode origin
    setUserProp origin "Source" "I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg + I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg, converted with LibreDWG 0.14; drawing units mm, model in metres"
    setUserProp origin "Levels" ("floor levels " + (TB_levels as string) + " m, wall heights " + (TB_heights as string) + " m")
    setUserProp origin "Built" "by the walkthrough app, 17 Nov 2026 (model data 0b36911854fa)"
    viewport.setType #view_iso_user
    select TB_nodes
    max zoomext sel all
    clearSelection()
    redrawViews()
    format "TB BUILD COMPLETE: % objects in % s, % failed checks\n" TB_nodes.count ((timeStamp() - t0) / 1000.0) TB_failed.count
    for f in TB_failed do format "  check failed: %\n" f
    true
)
try (destroyDialog TB_UI) catch ()
rollout TB_UI "TEST_BANK" width:340
(
    label info "Open a new empty scene before Build." align:#left
    label units1 "Build sets System Units to metres." align:#left
    checkbox dwg "At the drawing's own coordinates" checked:true tooltip:"Untick to centre the model on the origin"
    spinner lv1 "Level 1 floor level (m):" range:[-50, 500, 0.00] type:#float fieldwidth:60
    spinner ht1 "Level 1 wall height (m):" range:[2.2, 15, 3.00] type:#float fieldwidth:60
    spinner lv2 "Level 2 floor level (m):" range:[-50, 500, 3.00] type:#float fieldwidth:60
    spinner ht2 "Level 2 wall height (m):" range:[2.2, 15, 3.00] type:#float fieldwidth:60
    group "Furniture boxes (heights in mm)"
    (
        checkbox fb "Build furniture boxes" checked:true
        checkbox fo "Furniture boxes only" checked:false tooltip:"Add only the boxes to the scene already built from this model: no structure, and the empty-scene check is skipped"
        label fol "(add to the scene already built from this model)" align:#left
        spinner fh1 "Computer:" across:2 range:[10, 5000, 450] type:#integer fieldwidth:40
        spinner fh2 "Printer / copier:" range:[10, 5000, 300] type:#integer fieldwidth:40
        spinner fh3 "TV / wall screen:" across:2 range:[10, 5000, 600] type:#integer fieldwidth:40
        spinner fh4 "Partition:" range:[10, 5000, 1200] type:#integer fieldwidth:40
        spinner fh5 "Plant:" across:2 range:[10, 5000, 600] type:#integer fieldwidth:40
        spinner fh6 "Sanitary fitting:" range:[10, 5000, 850] type:#integer fieldwidth:40
        spinner fh7 "Chair / stool:" across:2 range:[10, 5000, 450] type:#integer fieldwidth:40
        spinner fh8 "Sofa / armchair:" range:[10, 5000, 800] type:#integer fieldwidth:40
        spinner fh9 "Table / desk:" across:2 range:[10, 5000, 750] type:#integer fieldwidth:40
        spinner fh10 "Coffee table:" range:[10, 5000, 450] type:#integer fieldwidth:40
        spinner fh11 "Cabinet:" across:2 range:[10, 5000, 900] type:#integer fieldwidth:40
        spinner fh12 "Tall cabinet:" range:[10, 5000, 2100] type:#integer fieldwidth:40
        spinner fh13 "Other furniture:" range:[10, 5000, 750] type:#integer fieldwidth:40
    )
    checkbox cm "Collapse to Editable Mesh (no live modifiers)" checked:false
    button build "BUILD THE MODEL" width:310 height:32
    label note1 "Parts stay live: spline + Extrude (mesh) + Smooth." align:#left
    label note2 "Ceilings are on hidden layers TB_<level>_Ceilings:" align:#left
    label note3 "switch them on for interior views." align:#left
    group "After the build"
    (
        button upd "Update levels and heights" width:300
        button col "Collapse all now (Editable Mesh)" width:300
        button fap "Apply furniture heights" width:300
    )
    on build pressed do
    (
        TB_levels = #(lv1.value,lv2.value)
        TB_heights = #(ht1.value,ht2.value)
        TB_collapse = cm.checked
        TB_shift = if dwg.checked then [0.0, 0.0] else [1.2120, 0.3520]
        TB_furnHeights = #((fh1.value / 1000.0),(fh2.value / 1000.0),(fh3.value / 1000.0),(fh4.value / 1000.0),(fh5.value / 1000.0),(fh6.value / 1000.0),(fh7.value / 1000.0),(fh8.value / 1000.0),(fh9.value / 1000.0),(fh10.value / 1000.0),(fh11.value / 1000.0),(fh12.value / 1000.0),(fh13.value / 1000.0))
        TB_furnWant = fb.checked
        TB_furnAddOnly = fo.checked
        try
        (
            if TB_build() do
            (
                if TB_failed.count == 0 then messageBox ("Built " + (TB_nodes.count as string) + " objects. Every part passed the closed-solid, height and position checks. Save As to keep your .max file.") title:"TEST_BANK"
                else messageBox ((TB_failed.count as string) + " part(s) failed a check and are on layer TB_Check_Failed (listed in the MAXScript Listener). Everything else was built.") title:"TEST_BANK"
            )
        )
        catch (messageBox (getCurrentException()) title:"Build stopped")
    )
    on upd pressed do
    (
        local r = TB_updateLevels #(lv1.value,lv2.value) #(ht1.value,ht2.value)
        messageBox ("Every part moved to its level; " + (r[1] as string) + " parts set to their level's wall height." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were collapsed already and kept their height.") else "")) title:"TEST_BANK"
    )
    on col pressed do
    (
        local n = TB_collapseAll()
        messageBox ((n as string) + " parts collapsed to Editable Mesh.") title:"TEST_BANK"
    )
    on fap pressed do
    (
        TB_furnHeights = #((fh1.value / 1000.0),(fh2.value / 1000.0),(fh3.value / 1000.0),(fh4.value / 1000.0),(fh5.value / 1000.0),(fh6.value / 1000.0),(fh7.value / 1000.0),(fh8.value / 1000.0),(fh9.value / 1000.0),(fh10.value / 1000.0),(fh11.value / 1000.0),(fh12.value / 1000.0),(fh13.value / 1000.0))
        local r = TB_furnApply()
        messageBox ((r[1] as string) + " furniture boxes set to the heights in the window and stood on their floor or support." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were left alone (not a Box any more, or a kind this script does not know).") else "")) title:"TEST_BANK"
    )
)
createDialog TB_UI
