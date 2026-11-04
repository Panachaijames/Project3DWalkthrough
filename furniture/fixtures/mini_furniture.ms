-- FIXTURE OFFICE (TEST) / from "mini_model.json" / built by the CAD-to-3D test pipeline, 27 Oct 2026
-- Same model as bank_3d_preview.html (model data a4f1fc668459). Floor levels +0.00 / +3.70 m, wall heights 3.70 / 3.70 m.
-- Placed at the DWG's own coordinates in metres (to line up with the DWGs imported in metres), or centred on the origin
-- if you untick that box in the script's window.
-- Every part stays LIVE (no Editable Poly): an editable spline outline + an Extrude modifier (output: Mesh) + Smooth.
--   * Change a height: the Extrude amount on that object, or "Update levels and heights" in this script's window.
--   * Change an outline: select the spline level under the modifiers and move vertices.
--   * Editable Mesh: tick "Collapse to Editable Mesh" before Build, or press "Collapse all now" later.
-- Each object's pivot is at the middle of its own outline, on its base. Layers per level and kind (FX_L1_Walls ...).
-- Glass partitions (Revit glass wall types) are their own objects on FX_<level>_Glass, at the height their type
-- name gives (2600H = 2.60 m); "Update levels and heights" keeps them, the parapet and the stair steps at their own
-- heights (only parts marked to follow the wall height change).
-- Each part is checked as it is built (closed solid, height, position). A part that fails is kept on layer
-- FX_Check_Failed and listed in the MAXScript Listener; the rest is still built.
-- Build sets System Units to metres. Nothing in an existing scene is changed: run it in a NEW EMPTY scene.
global FX_UI
global FX_nodes = #()
global FX_failed = #()
global FX_levels = #(0.00,3.70)
global FX_heights = #(3.70,3.70)
global FX_floorNames = #("L1","L2")
global FX_collapse = false
global FX_shift = [0.0, 0.0]
global FX_mats
-- Furniture boxes: one coloured placeholder box per furniture piece (colour = kind), on layers FX_<level>_Furn_<Kind>. Type
-- each kind's height in mm in the window, before the build or later with "Apply furniture heights" (boxes on a table, counter or
-- cabinet follow its height). A box is a live Box, never an Editable Poly, and carries the piece's family, block and DWG layer
-- as user properties, so the 3D team can swap it for their own model by family name. A property with nothing to say (no support,
-- no block, no handle) holds the word none, never empty text: 3ds Max does not say what getUserProp returns for empty text.
-- Each box is checked as it is built: base z, top z and its four corners carried through its transform, and the node's min and
-- max in the plan only for an unrotated box (Autodesk does not say what they are for a turned node). A box that fails goes on
-- layer FX_Check_Failed and is listed in the Listener; the rest is still built.
-- "Furniture boxes only" adds just the boxes to a scene already built from this model. Below: the kinds in the model's order,
-- heights and bases in metres.
global FX_furnWant = true
global FX_furnAddOnly = false
global FX_furnFloors = #("L1","L2")
global FX_furnKeys = #("computer","printer","tv","curtain","plant","seat","table","coffee-table","cabinet","tall-cabinet")
global FX_furnLayers = #("Computer","Printer","Tv","Curtain","Plant","Seat","Table","CoffeeTable","Cabinet","TallCabinet")
global FX_furnBases = #(0.0000,0.0000,0.9000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000)
global FX_furnHeights = #(0.4500,0.3000,0.6000,2.4000,0.6000,0.4500,0.7500,0.4500,0.9000,2.1000)
global FX_furnLevels = #()
global FX_furnMats = #()

fn FX_layer n =
(
    local ly = LayerManager.getLayerFromName n
    if ly == undefined do ly = LayerManager.newLayerFromName n
    ly
)
fn FX_mat key =
(
    local m = undefined
    for x in FX_mats where x.name == ("FX " + key) do m = x
    m
)
fn FX_makeMaterials =
(
    FX_mats = #()
    append FX_mats (standardMaterial name:"FX Wall" diffuse:(color 227 221 211))
    append FX_mats (standardMaterial name:"FX Glass" diffuse:(color 170 200 214) opacity:30 specularLevel:60 glossiness:60)
    append FX_mats (standardMaterial name:"FX Rail" diffuse:(color 119 114 124))
    append FX_mats (standardMaterial name:"FX Single" diffuse:(color 224 164 88))
    append FX_mats (standardMaterial name:"FX Slab" diffuse:(color 212 216 210))
    append FX_mats (standardMaterial name:"FX Frame" diffuse:(color 93 107 116))
    append FX_mats (standardMaterial name:"FX Step" diffuse:(color 185 199 180))
)
fn FX_num v = ((v as string) as float)
-- The outline's knots are relative to c, the middle of the outline; the node is then moved to c, so that is its pivot.
fn FX_shape nm loops =
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
fn FX_extrudeOf o =
(
    local ex = undefined
    for md in o.modifiers where classOf md == Extrude do ex = md
    ex
)
-- kind: #wall #column #lintel #sill #parapet #glass #mullion #railing #single #step #slab; z0/z1 in metres above the
-- level of floor fi (a step of a flight going down from a level starts below it);
-- follow = the top follows that level's wall height. c = pivot, mn/mx = outline extents (DWG coordinates).
fn FX_part kind nm loops z0 z1 follow fi c mn mx =
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
    )
    local lvl = FX_levels[fi]
    local top = if follow then FX_heights[fi] else z1
    local zb = lvl + z0
    local ht = top - z0
    local o = FX_shape nm loops
    o.pos = [c.x - FX_shift.x, c.y - FX_shift.y, zb]
    addModifier o (Extrude amount:ht segs:1 capStart:true capEnd:true output:1 smooth:false)
    addModifier o (Smooth autoSmooth:true threshold:25.0)
    local mt = FX_mat info[2]
    o.material = mt
    o.wirecolor = mt.diffuse
    setUserProp o "FX_kind" (kind as string)
    setUserProp o "FX_floor" fi
    setUserProp o "FX_base" z0
    setUserProp o "FX_follow" follow
    -- the checks run on the evaluated mesh (what the modifiers produce)
    local m = snapshotAsMesh o
    local why = ""
    local tol = 0.002
    if m.numfaces < 3 then why = "no faces"
    else if (meshop.getOpenEdges m).numberSet != 0 then why = "open edges (not a closed solid)"
    else if abs(o.min.z - zb) > tol or abs(o.max.z - (zb + ht)) > tol then why = "height"
    else if abs(o.min.x - (mn.x - FX_shift.x)) > tol or abs(o.min.y - (mn.y - FX_shift.y)) > tol or abs(o.max.x - (mx.x - FX_shift.x)) > tol or abs(o.max.y - (mx.y - FX_shift.y)) > tol then why = "position"
    m = undefined
    if why == "" then
    (
        (FX_layer ("FX_" + FX_floorNames[fi] + "_" + info[1])).addNode o
        setUserProp o "FX_check" "ok"
    )
    else
    (
        (FX_layer "FX_Check_Failed").addNode o
        setUserProp o "FX_check" why
        append FX_failed (nm + ": " + why)
    )
    if FX_collapse do convertToMesh o
    append FX_nodes o
    o
)
-- Stair lines: one shape of open two-knot splines per level and kind, knots relative to c (its pivot).
fn FX_lines nm segs fi c lay =
(
    local o = splineShape name:nm
    for k = 1 to segs.count do
    (
        addNewSpline o
        addKnot o k #corner #line [segs[k][1].x, segs[k][1].y, 0]
        addKnot o k #corner #line [segs[k][2].x, segs[k][2].y, 0]
    )
    updateShape o
    o.pos = [c.x - FX_shift.x, c.y - FX_shift.y, FX_levels[fi]]
    o.wirecolor = if lay == "Stairs" then (color 46 139 71) else (color 160 210 170)
    setUserProp o "FX_floor" fi
    setUserProp o "FX_base" 0.0
    (FX_layer ("FX_" + FX_floorNames[fi] + "_" + lay)).addNode o
    append FX_nodes o
    o
)
fn FX_room nm p fi =
(
    local t = text text:nm size:0.3 pos:[p.x - FX_shift.x, p.y - FX_shift.y, FX_levels[fi] + 0.02]
    t.name = "FX_Room_" + FX_floorNames[fi] + "_" + nm
    t.wirecolor = color 30 60 110
    setUserProp t "FX_floor" fi
    setUserProp t "FX_base" 0.02
    (FX_layer ("FX_" + FX_floorNames[fi] + "_RoomNames")).addNode t
    append FX_nodes t
    t
)
-- After the build: move every part to its level and set every live part whose top follows the wall height to its
-- level's new wall height.
fn FX_updateLevels newLevels newHeights =
(
    local n = 0
    local skipped = 0
    for o in objects where (getUserProp o "FX_floor") != undefined do
    (
        local fi = (FX_num (getUserProp o "FX_floor")) as integer
        local base = FX_num (getUserProp o "FX_base")
        o.pos.z = newLevels[fi] + base
        if ((getUserProp o "FX_follow") as string) == "true" do
        (
            local ex = FX_extrudeOf o
            if ex == undefined then skipped += 1
            else ( ex.amount = newHeights[fi] - base; n += 1 )
        )
    )
    FX_levels = newLevels
    FX_heights = newHeights
    #(n, skipped)
)
fn FX_collapseAll =
(
    local n = 0
    for o in objects where (getUserProp o "FX_kind") != undefined and o.modifiers.count > 0 do ( convertToMesh o; n += 1 )
    n
)
-- Furniture boxes: one coloured Box per piece, a placeholder the 3D team swaps for their own model by family name.
-- A box is a live Box (width along its own long axis, length across it, height), never an Editable Poly or Mesh and never
-- collapsed: "Collapse all now" only takes objects that carry FX_kind and a modifier, and a box has neither. Every box
-- carries FX_floor and FX_base (its bottom, in metres above its level) and FX_follow = false, so "Update levels
-- and heights" moves it with its level and leaves its height alone.
fn FX_furnNum v = ((v as string) as float)
fn FX_furnMakeMaterials =
(
    FX_furnMats = #()
    append FX_furnMats (standardMaterial name:"FX Furn computer" diffuse:(color 123 63 181))
    append FX_furnMats (standardMaterial name:"FX Furn printer" diffuse:(color 142 142 142))
    append FX_furnMats (standardMaterial name:"FX Furn tv" diffuse:(color 52 64 143))
    append FX_furnMats (standardMaterial name:"FX Furn curtain" diffuse:(color 201 160 220))
    append FX_furnMats (standardMaterial name:"FX Furn plant" diffuse:(color 46 158 79))
    append FX_furnMats (standardMaterial name:"FX Furn seat" diffuse:(color 224 123 0))
    append FX_furnMats (standardMaterial name:"FX Furn table" diffuse:(color 138 90 43))
    append FX_furnMats (standardMaterial name:"FX Furn coffee-table" diffuse:(color 201 163 122))
    append FX_furnMats (standardMaterial name:"FX Furn cabinet" diffuse:(color 47 127 193))
    append FX_furnMats (standardMaterial name:"FX Furn tall-cabinet" diffuse:(color 27 79 138))
)
-- The floor levels the build was started with (a copy: nothing is shared with the script's own array).
fn FX_furnSetLevels =
(
    FX_furnLevels = #()
    for z in (FX_levels) do append FX_furnLevels z
)
-- Where a box stands, in metres above its level: on its kind's base, or on top of the kind of support it was drawn on
-- (ki = its kind, oki = the kind of its support, 0 for none). A support never stands on anything.
fn FX_furnZ0 ki oki =
(
    local z0 = FX_furnBases[ki]
    if oki > 0 do z0 = FX_furnBases[oki] + FX_furnHeights[oki]
    z0
)
-- kind = the kind, nm = the object's name, fi = the floor's index, pid = the piece's id, supId and supKind = its support's id
-- and kind ("none" for none), c = the box's centre and cs = its four corners (DWG coordinates), w d = its size along its own
-- long and short axis, ca sa = cos and sin of the angle from +x to the long axis, fam blk lay hnd = family, block, DWG layer,
-- handle ("none" for nothing). The box gets an explicit matrix: its X, Y and Z axes in the world, then its pivot (the middle of
-- its base).
fn FX_furnBox kind nm fi pid supId supKind c w d ca sa cs fam blk lay hnd =
(
    local ki = findItem FX_furnKeys kind
    local z0 = FX_furnZ0 ki (findItem FX_furnKeys supKind)
    local ht = FX_furnHeights[ki]
    local zb = FX_furnLevels[fi] + z0
    local o = box name:nm width:w length:d height:ht
    o.transform = (matrix3 [ca, sa, 0.0] [(0.0 - sa), ca, 0.0] [0.0, 0.0, 1.0] [c.x - FX_shift.x, c.y - FX_shift.y, zb])
    local mt = FX_furnMats[ki]
    o.material = mt
    o.wirecolor = mt.diffuse
    setUserProp o "FX_furn" "true"
    setUserProp o "FX_furnKind" kind
    setUserProp o "FX_furnId" pid
    setUserProp o "FX_furnOn" supId
    setUserProp o "FX_furnOnKind" supKind
    setUserProp o "FX_family" fam
    setUserProp o "FX_block" blk
    setUserProp o "FX_layer" lay
    setUserProp o "FX_handle" hnd
    setUserProp o "FX_floor" fi
    setUserProp o "FX_base" z0
    setUserProp o "FX_follow" false
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
    else if unrotated and (abs(o.min.x - (mnx - FX_shift.x)) > tol or abs(o.min.y - (mny - FX_shift.y)) > tol or abs(o.max.x - (mxx - FX_shift.x)) > tol or abs(o.max.y - (mxy - FX_shift.y)) > tol) then why = "bounding box"
    else
    (
        local hw = o.width / 2.0
        local hd = o.length / 2.0
        local lc = #([(0.0 - hw), (0.0 - hd), 0.0], [hw, (0.0 - hd), 0.0], [hw, hd, 0.0], [(0.0 - hw), hd, 0.0])
        for k = 1 to 4 do
        (
            local q = lc[k] * o.transform
            if why == "" and (abs(q.x - (cs[k].x - FX_shift.x)) > tol or abs(q.y - (cs[k].y - FX_shift.y)) > tol) then why = "corner " + (k as string)
        )
    )
    if why == "" then
    (
        (FX_layer ("FX_" + FX_furnFloors[fi] + "_Furn_" + FX_furnLayers[ki])).addNode o
        setUserProp o "FX_check" "ok"
    )
    else
    (
        (FX_layer "FX_Check_Failed").addNode o
        setUserProp o "FX_check" why
        append FX_failed (nm + ": " + why)
    )
    append FX_nodes o
    o
)
-- Every piece of the model, in the model's order.
fn FX_furnAll =
(
    FX_furnBox "computer" "FX_L1_Furn_computer_001_Enscape AssetDefinition - Computer 003" 1 "L1-computer-001" "L1-table-001" "table" [1.3000,2.1000] 0.7400 0.4300 1.000000000 0.000000000 #([0.9300,1.8850],[1.6700,1.8850],[1.6700,2.3150],[0.9300,2.3150]) "Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "I-FURN" "A1"
    FX_furnBox "printer" "FX_L1_Furn_printer_001_PRINTER_DESKTOP_LASER - Type 1" 1 "L1-printer-001" "L1-table-001" "table" [0.5000,1.9000] 0.4000 0.3000 1.000000000 0.000000000 #([0.3000,1.7500],[0.7000,1.7500],[0.7000,2.0500],[0.3000,2.0500]) "PRINTER_DESKTOP_LASER - Type 1" "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1" "Q-SPCQ" "A2"
    FX_furnBox "tv" "FX_L1_Furn_tv_001_APPLIANCE_TV_WALL MOUNT WITH BRACKET - 7" 1 "L1-tv-001" "none" "none" [8.0000,5.0000] 1.6800 0.0500 0.000000000 1.000000000 #([8.0250,4.1600],[8.0250,5.8400],[7.9750,5.8400],[7.9750,4.1600]) "APPLIANCE_TV_WALL MOUNT WITH BRACKET - 75_" "APPLIANCE_TV_WALL MOUNT WITH BRACKET - 75_" "Q-SPCQ" "A3"
    FX_furnBox "curtain" "FX_L1_Furn_curtain_001_Double Curtain" 1 "L1-curtain-001" "none" "none" [1.0000,7.0000] 3.0000 0.1500 1.000000000 0.000000000 #([(-0.5000),6.9250],[2.5000,6.9250],[2.5000,7.0750],[(-0.5000),7.0750]) "Double Curtain" "Double Curtain" "DA-FACILITIES" "A4"
    FX_furnBox "plant" "FX_L1_Furn_plant_001_Enscape AssetDefinition - Potted Plant 0" 1 "L1-plant-001" "none" "none" [7.0000,2.0000] 0.5000 0.5000 1.000000000 0.000000000 #([6.7500,1.7500],[7.2500,1.7500],[7.2500,2.2500],[6.7500,2.2500]) "Enscape AssetDefinition - Potted Plant 028 Peace Lily" "Enscape AssetDefinition - Potted Plant 028 Peace Lily" "L-PLNT" "A5"
    FX_furnBox "seat" "FX_L1_Furn_seat_001_mollie_chair_a685_revit - A685 2" 1 "L1-seat-001" "none" "none" [2.0000,3.0000] 0.6000 0.5700 1.000000000 0.000000000 #([1.7000,2.7150],[2.3000,2.7150],[2.3000,3.2850],[1.7000,3.2850]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-1234567-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "A6"
    FX_furnBox "seat" "FX_L1_Furn_seat_002_mollie_chair_a685_revit - A685 2" 1 "L1-seat-002" "none" "none" [3.0000,3.0000] 0.6000 0.5700 0.866025404 0.500000000 #([2.8827,2.6032],[3.4023,2.9032],[3.1173,3.3968],[2.5977,3.0968]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-1234568-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "A7"
    FX_furnBox "seat" "FX_L1_Furn_seat_003_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 1 "L1-seat-003" "none" "none" [0.0000,5.0000] 0.5000 0.5000 0.000000000 1.000000000 #([0.2500,4.7500],[0.2500,5.2500],[(-0.2500),5.2500],[(-0.2500),4.7500]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE" "I-FURN" "A8"
    FX_furnBox "table" "FX_L1_Furn_table_001_IA_J15_WORKING TABLE - 1800W 1000D 750H" 1 "L1-table-001" "none" "none" [1.0000,2.0000] 1.8000 1.0000 1.000000000 0.000000000 #([0.1000,1.5000],[1.9000,1.5000],[1.9000,2.5000],[0.1000,2.5000]) "IA_J15_WORKING TABLE - 1800W 1000D 750H" "IA_J15_WORKING TABLE - 1800W 1000D 750H" "I-FURN" "A9"
    FX_furnBox "table" "FX_L1_Furn_table_002_IA_J15_WORKING TABLE - 1400W 1000D 750H" 1 "L1-table-002" "none" "none" [5.0000,4.0000] 1.4000 1.0000 (-0.866025404) 0.500000000 #([5.8562,4.0830],[4.6438,4.7830],[4.1438,3.9170],[5.3562,3.2170]) "IA_J15_WORKING TABLE - 1400W 1000D 750H" "IA_J15_WORKING TABLE - 1400W 1000D 750H" "I-FURN" "AA"
    FX_furnBox "coffee-table" "FX_L1_Furn_coffee-table_001_COFFEE TABLE RETANGLE - VENNATIVE - TYPE" 1 "L1-coffee-table-001" "none" "none" [(-2.0000),0.0000] 1.0000 0.5000 1.000000000 0.000000000 #([(-2.5000),(-0.2500)],[(-1.5000),(-0.2500)],[(-1.5000),0.2500],[(-2.5000),0.2500]) "COFFEE TABLE RETANGLE - VENNATIVE - TYPE 1" "COFFEE TABLE RETANGLE - VENNATIVE - TYPE 1" "I-FURN" "AB"
    FX_furnBox "cabinet" "FX_L1_Furn_cabinet_001_IA_J10_WORK CABINET - IA_J10_WORK CABINE" 1 "L1-cabinet-001" "none" "none" [(-3.0000),6.0000] 2.4500 0.6000 1.000000000 0.000000000 #([(-4.2250),5.7000],[(-1.7750),5.7000],[(-1.7750),6.3000],[(-4.2250),6.3000]) "IA_J10_WORK CABINET - IA_J10_WORK CABINET" "IA_J10_WORK CABINET - IA_J10_WORK CABINET" "Q-CASE" "AC"
    FX_furnBox "tall-cabinet" "FX_L1_Furn_tall-cabinet_001_TALL CABINET - TALL CABINET 2800W" 1 "L1-tall-cabinet-001" "none" "none" [6.0000,(-1.0000)] 2.8000 0.4100 0.000000000 1.000000000 #([6.2050,(-2.4000)],[6.2050,0.4000],[5.7950,0.4000],[5.7950,(-2.4000)]) "TALL CABINET - TALL CABINET 2800W" "TALL CABINET - TALL CABINET 2800W" "Q-CASE" "AD"
    FX_furnBox "computer" "FX_L2_Furn_computer_001_Enscape AssetDefinition - Computer 003" 2 "L2-computer-001" "L2-table-001" "table" [3.1000,4.0000] 0.7400 0.4300 0.707106781 0.707106781 #([2.9904,3.5863],[3.5137,4.1096],[3.2096,4.4137],[2.6863,3.8904]) "Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "I-FURN" "B1"
    FX_furnBox "seat" "FX_L2_Furn_seat_001_HermanMiller_Seating_AER1A_NewAeron_Work" 2 "L2-seat-001" "none" "none" [2.0000,3.0000] 0.6100 0.5500 1.000000000 0.000000000 #([1.6950,2.7250],[2.3050,2.7250],[2.3050,3.2750],[1.6950,3.2750]) "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range" "I-FURN" "B2"
    FX_furnBox "table" "FX_L2_Furn_table_001_IA_J15_WORKING TABLE - 1400W 1000D 750H" 2 "L2-table-001" "none" "none" [3.0000,4.0000] 1.4000 1.0000 0.707106781 0.707106781 #([2.8586,3.1515],[3.8485,4.1414],[3.1414,4.8485],[2.1515,3.8586]) "IA_J15_WORKING TABLE - 1400W 1000D 750H" "IA_J15_WORKING TABLE - 1400W 1000D 750H" "I-FURN" "B3"
    FX_furnBox "cabinet" "FX_L2_Furn_cabinet_001_PANEL_ADJ_GEN - ADJUSTABLE CUPBOARD DOOR" 2 "L2-cabinet-001" "none" "none" [(-1.0000),0.0000] 3.6000 1.2000 1.000000000 0.000000000 #([(-2.8000),(-0.6000)],[0.8000,(-0.6000)],[0.8000,0.6000],[(-2.8000),0.6000]) "PANEL_ADJ_GEN - ADJUSTABLE CUPBOARD DOOR" "PANEL_ADJ_GEN - ADJUSTABLE CUPBOARD DOOR" "Q-CASE" "none"
)
-- The build's furniture step: materials, levels, every box.
fn FX_furnRun =
(
    FX_furnMakeMaterials()
    FX_furnSetLevels()
    FX_furnAll()
)
-- For every floor, its level as the scene has it: the most common value (to the millimetre) of z minus FX_base over the
-- objects that carry FX_floor and FX_base. Sets FX_furnLevels for the floors it finds and returns how many.
fn FX_furnSceneLevels =
(
    local fis = #()
    local mms = #()
    local cnt = #()
    for o in objects where (getUserProp o "FX_floor") != undefined and (getUserProp o "FX_base") != undefined do
    (
        local fi = (FX_furnNum (getUserProp o "FX_floor")) as integer
        local mmv = (floor ((o.pos.z - (FX_furnNum (getUserProp o "FX_base"))) * 1000.0 + 0.5)) as integer
        local k = 0
        for j = 1 to fis.count where fis[j] == fi and mms[j] == mmv do k = j
        if k == 0 then ( append fis fi; append mms mmv; append cnt 1 )
        else cnt[k] += 1
    )
    local found = 0
    for f = 1 to FX_furnFloors.count do
    (
        local best = 0
        for j = 1 to fis.count where fis[j] == f and cnt[j] > best do
        (
            best = cnt[j]
            FX_furnLevels[f] = mms[j] / 1000.0
        )
        if best > 0 do found += 1
    )
    found
)
-- "Furniture boxes only": adds the boxes to a scene already built from this model and changes nothing else. It refuses, and
-- changes nothing, when boxes are there already or System Units are not metres. The placement shift comes from the hidden
-- datum FX_ORIGIN_DWG (shift = minus its x, y) and each level from the objects that carry FX_floor and FX_base;
-- what it cannot find it takes from the window (the tick box and the level spinners), and says so. It reports in message boxes
-- of its own (the Build button's message is written for parts), so FX_build returns false after it.
fn FX_furnAdd =
(
    if FX_furnWant == false then
    (
        messageBox "Tick Build furniture boxes as well. Nothing in this scene has been changed." title:"Fixture"
        return false
    )
    if abs(units.systemScale - 1.0) > 0.0001 or units.systemType != #meters then
    (
        messageBox "This scene's System Units are not metres, so the boxes would come out the wrong size. Nothing in this scene has been changed." title:"Fixture"
        return false
    )
    local existing = 0
    for o in objects where (getUserProp o "FX_furn") != undefined or (matchPattern o.layer.name pattern:"FX_*_Furn_*") do existing += 1
    if existing > 0 then
    (
        messageBox ("This scene already has furniture boxes (" + (existing as string) + " objects). Nothing in this scene has been changed.") title:"Fixture"
        return false
    )
    local t0 = timeStamp()
    local notes = ""
    local datum = undefined
    for o in objects where o.name == "FX_ORIGIN_DWG" do datum = o
    if datum == undefined then notes += "The origin datum FX_ORIGIN_DWG was not found, so the boxes are placed by the tick box At the drawing's own coordinates. "
    else FX_shift = [0.0 - datum.pos.x, 0.0 - datum.pos.y]
    FX_nodes = #()
    FX_failed = #()
    FX_furnMakeMaterials()
    FX_furnSetLevels()
    local found = FX_furnSceneLevels()
    if found < FX_furnFloors.count then notes += "The level of " + ((FX_furnFloors.count - found) as string) + " floor(s) was not found in the scene, so the level spinners are used for it. "
    FX_furnAll()
    format "FX FURNITURE BOXES ADDED: % boxes in % s, % failed checks\n" FX_nodes.count ((timeStamp() - t0) / 1000.0) FX_failed.count
    for f in FX_failed do format "  check failed: %\n" f
    if notes != "" do messageBox notes title:"Fixture"
    if FX_failed.count == 0 then messageBox ("Added " + (FX_nodes.count as string) + " furniture boxes. Every box passed its height and position checks. Nothing else in this scene was changed. Save As to keep your .max file.") title:"Fixture"
    else messageBox ((FX_failed.count as string) + " of the " + (FX_nodes.count as string) + " furniture boxes failed a check and are on layer FX_Check_Failed (listed in the MAXScript Listener). The others were added and passed. Nothing else in this scene was changed.") title:"Fixture"
    true
)
-- After the build: every box takes the height of its kind (FX_furnHeights, read from the window) and stands on its kind's
-- base, or on top of the kind of support it was drawn on (the support's kind is none, or undefined, or empty: no support). A box
-- keeps the level it is on (its z minus its FX_base), so levels moved by "Update levels and heights" stay. A box that is not
-- a Box any more, or of an unknown kind, is left alone.
fn FX_furnApply =
(
    local n = 0
    local skipped = 0
    for o in objects where (getUserProp o "FX_furn") != undefined do
    (
        local ki = findItem FX_furnKeys ((getUserProp o "FX_furnKind") as string)
        if (classOf o) != Box or ki == 0 then skipped += 1
        else
        (
            local z0 = FX_furnZ0 ki (findItem FX_furnKeys ((getUserProp o "FX_furnOnKind") as string))
            o.pos.z = o.pos.z - (FX_furnNum (getUserProp o "FX_base")) + z0
            o.height = FX_furnHeights[ki]
            setUserProp o "FX_base" z0
            n += 1
        )
    )
    #(n, skipped)
)
fn FX_build =
(
    if FX_furnAddOnly then
    (
        -- "Furniture boxes only" has said what it did, or why it did nothing, in its own message: false = nothing more to report
        FX_furnAdd()
        return false
    )
    if objects.count > 0 then
    (
        messageBox "Open a NEW EMPTY scene first. Nothing in this scene has been changed." title:"Fixture"
        return false
    )
    units.systemType = #meters
    units.systemScale = 1.0
    units.displayType = #metric
    units.metricType = #meters
    FX_nodes = #()
    FX_failed = #()
    FX_makeMaterials()
    local t0 = timeStamp()
    FX_part #slab "FX_L1_Slab_001" #(#([(-8.0000),(-6.5000)],[8.0000,(-6.5000)],[8.0000,6.5000],[(-8.0000),6.5000])) (-0.2500) 0.0000 false 1 [2.5000,3.0000] [(-5.5000),(-3.5000)] [10.5000,9.5000]
    FX_part #wall "FX_L1_Wall_001" #(#([(-8.0000),(-0.1000)],[8.0000,(-0.1000)],[8.0000,0.1000],[(-8.0000),0.1000])) 0.0000 3.7000 true 1 [2.5000,(-3.6000)] [(-5.5000),(-3.7000)] [10.5000,(-3.5000)]
    FX_part #slab "FX_L2_Slab_001" #(#([(-4.8500),(-4.8000)],[4.8500,(-4.8000)],[4.8500,4.8000],[(-4.8500),4.8000])) (-0.2500) 0.0000 false 2 [1.0500,2.0000] [(-3.8000),(-2.8000)] [5.9000,6.8000]
    FX_part #wall "FX_L2_Wall_001" #(#([(-4.8500),(-0.1000)],[4.8500,(-0.1000)],[4.8500,0.1000],[(-4.8500),0.1000])) 0.0000 3.7000 true 2 [1.0500,(-2.9000)] [(-3.8000),(-3.0000)] [5.9000,(-2.8000)]
    FX_room "Room A" [1.0000,2.0000] 1
    FX_room "Room B" [2.0000,3.0000] 2
    if FX_furnWant do FX_furnRun()
    local origin = point name:"FX_ORIGIN_DWG" size:1.0 pos:[0.0 - FX_shift.x, 0.0 - FX_shift.y, 0.0]
    origin.isHidden = true
    origin.ignoreExtents = true
    (FX_layer "FX_Datums").addNode origin
    setUserProp origin "Source" "mini_model.json, converted with LibreDWG; drawing units mm, model in metres"
    setUserProp origin "Levels" ("floor levels " + (FX_levels as string) + " m, wall heights " + (FX_heights as string) + " m")
    viewport.setType #view_iso_user
    select FX_nodes
    max zoomext sel all
    clearSelection()
    redrawViews()
    format "FX BUILD COMPLETE: % objects in % s, % failed checks\n" FX_nodes.count ((timeStamp() - t0) / 1000.0) FX_failed.count
    for f in FX_failed do format "  check failed: %\n" f
    true
)
try (destroyDialog FX_UI) catch ()
rollout FX_UI "Fixture (test)" width:340
(
    label info "Open a new empty scene before Build." align:#left
    label units1 "Build sets System Units to metres." align:#left
    checkbox dwg "At the drawing's own coordinates" checked:true tooltip:"Untick to centre the model on the origin"
    spinner lv1 "Level 1 floor level (m):" range:[-50, 500, 0.00] type:#float fieldwidth:60
    spinner ht1 "Level 1 wall height (m):" range:[2.2, 15, 3.70] type:#float fieldwidth:60
    spinner lv2 "Level 2 floor level (m):" range:[-50, 500, 3.70] type:#float fieldwidth:60
    spinner ht2 "Level 2 wall height (m):" range:[2.2, 15, 3.70] type:#float fieldwidth:60
    group "Furniture boxes (heights in mm)"
    (
        checkbox fb "Build furniture boxes" checked:true
        checkbox fo "Furniture boxes only" checked:false tooltip:"Add only the boxes to the scene already built from this model: no structure, and the empty-scene check is skipped"
        label fol "(add to the scene already built from this model)" align:#left
        spinner fh1 "Computer:" across:2 range:[10, 5000, 450] type:#integer fieldwidth:40
        spinner fh2 "Printer / copier:" range:[10, 5000, 300] type:#integer fieldwidth:40
        spinner fh3 "TV / wall screen:" across:2 range:[10, 5000, 600] type:#integer fieldwidth:40
        spinner fh4 "Curtain:" range:[10, 5000, 2400] type:#integer fieldwidth:40
        spinner fh5 "Plant:" across:2 range:[10, 5000, 600] type:#integer fieldwidth:40
        spinner fh6 "Chair / stool:" range:[10, 5000, 450] type:#integer fieldwidth:40
        spinner fh7 "Table / desk:" across:2 range:[10, 5000, 750] type:#integer fieldwidth:40
        spinner fh8 "Coffee table:" range:[10, 5000, 450] type:#integer fieldwidth:40
        spinner fh9 "Cabinet:" across:2 range:[10, 5000, 900] type:#integer fieldwidth:40
        spinner fh10 "Tall cabinet:" range:[10, 5000, 2100] type:#integer fieldwidth:40
    )
    checkbox cm "Collapse to Editable Mesh (no live modifiers)" checked:false
    button build "BUILD THE MODEL" width:310 height:32
    label note1 "Parts stay live: spline + Extrude (mesh) + Smooth." align:#left
    group "After the build"
    (
        button upd "Update levels and heights" width:300
        button col "Collapse all now (Editable Mesh)" width:300
        button fap "Apply furniture heights" width:300
    )
    on build pressed do
    (
        FX_levels = #(lv1.value,lv2.value)
        FX_heights = #(ht1.value,ht2.value)
        FX_collapse = cm.checked
        FX_shift = if dwg.checked then [0.0, 0.0] else [1.0000, 2.0000]
        FX_furnHeights = #((fh1.value / 1000.0),(fh2.value / 1000.0),(fh3.value / 1000.0),(fh4.value / 1000.0),(fh5.value / 1000.0),(fh6.value / 1000.0),(fh7.value / 1000.0),(fh8.value / 1000.0),(fh9.value / 1000.0),(fh10.value / 1000.0))
        FX_furnWant = fb.checked
        FX_furnAddOnly = fo.checked
        try
        (
            if FX_build() do
            (
                if FX_failed.count == 0 then messageBox ("Built " + (FX_nodes.count as string) + " objects. Every part passed the closed-solid, height and position checks. Save As to keep your .max file.") title:"Fixture"
                else messageBox ((FX_failed.count as string) + " part(s) failed a check and are on layer FX_Check_Failed (listed in the MAXScript Listener). Everything else was built.") title:"Fixture"
            )
        )
        catch (messageBox (getCurrentException()) title:"Build stopped")
    )
    on upd pressed do
    (
        local r = FX_updateLevels #(lv1.value,lv2.value) #(ht1.value,ht2.value)
        messageBox ("Every part moved to its level; " + (r[1] as string) + " parts set to their level's wall height." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were collapsed already and kept their height.") else "")) title:"Fixture"
    )
    on col pressed do
    (
        local n = FX_collapseAll()
        messageBox ((n as string) + " parts collapsed to Editable Mesh.") title:"Fixture"
    )
    on fap pressed do
    (
        FX_furnHeights = #((fh1.value / 1000.0),(fh2.value / 1000.0),(fh3.value / 1000.0),(fh4.value / 1000.0),(fh5.value / 1000.0),(fh6.value / 1000.0),(fh7.value / 1000.0),(fh8.value / 1000.0),(fh9.value / 1000.0),(fh10.value / 1000.0))
        local r = FX_furnApply()
        messageBox ((r[1] as string) + " furniture boxes set to the heights in the window and stood on their floor or support." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were left alone (not a Box any more, or a kind this script does not know).") else "")) title:"Fixture"
    )
)
createDialog FX_UI
