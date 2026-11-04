-- HOTEL GROUND FLOOR AND FLOOR 2 (FROM TWO PICTURES) (TEST) / from "source/floor1_plan.png + source/floor2_plan.png" / built by the CAD-to-3D test pipeline, 2 Nov 2026
-- Same model as hotel_3d_preview.html (model data 6ab030750886). Floor levels +0.00 / +2.90 m, wall heights 2.90 / 2.90 m.
-- Read from two presentation pictures, not from CAD, and scaled from the one dimension the owner gave (2 Nov 2026):
-- the main stair's width, 2.50 m between its side walls; Floor 1's picture is drawn wider than tall (a scale per axis).
-- Sizes are approximate: at that scale the 4 lift doors measure 1.12 to 1.28 m as drawn (1.19 m on average); they are built 1.00 m.
-- Placed at the drawing's own coordinates in metres (0,0 is the lift core's north-west corner on both floors, y up),
-- or centred on the origin if you untick that box in the script's window.
-- To lay a picture under its floor: the hidden point HL_ORIGIN_DWG (layer HL_Datums) gives each picture's size
-- and centre in metres (Object Properties > User Defined).
-- Every part stays LIVE (no Editable Poly): an editable spline outline + an Extrude modifier (output: Mesh) + Smooth.
--   * Change a height: the Extrude amount on that object, or "Update levels and heights" in this script's window.
--   * Change an outline: select the spline level under the modifiers and move vertices.
--   * Editable Mesh: tick "Collapse to Editable Mesh" before Build, or press "Collapse all now" later.
-- Each object's pivot is at the middle of its own outline, on its base. Layers per level and kind (HL_F1_Walls ...).
-- "Update levels and heights" sets the tops of the walls, mullions, glass and lintels to their level's wall height and keeps
-- the stair steps, the slabs, the parapets, the sills and the railings at their own heights (only parts marked to follow the wall height change).
-- Each part is checked as it is built (closed solid, height, position). A part that fails is kept on layer
-- HL_Check_Failed and listed in the MAXScript Listener; the rest is still built.
-- Build sets System Units to metres. Nothing in an existing scene is changed: run it in a NEW EMPTY scene.
global HL_UI
global HL_nodes = #()
global HL_failed = #()
global HL_levels = #(0.00,2.90)
global HL_heights = #(2.90,2.90)
global HL_floorNames = #("F1","F2")
global HL_collapse = false
global HL_shift = [0.0, 0.0]
global HL_mats
-- Furniture boxes: one coloured placeholder box per furniture piece (colour = kind), on layers HL_<level>_Furn_<Kind>. Type
-- each kind's height in mm in the window, before the build or later with "Apply furniture heights" (boxes on a table, counter or
-- cabinet follow its height). A box is a live Box, never an Editable Poly, and carries the piece's family, block and DWG layer
-- as user properties, so the 3D team can swap it for their own model by family name. A property with nothing to say (no support,
-- no block, no handle) holds the word none, never empty text: 3ds Max does not say what getUserProp returns for empty text.
-- Each box is checked as it is built: base z, top z and its four corners carried through its transform, and the node's min and
-- max in the plan only for an unrotated box (Autodesk does not say what they are for a turned node). A box that fails goes on
-- layer HL_Check_Failed and is listed in the Listener; the rest is still built.
-- "Furniture boxes only" adds just the boxes to a scene already built from this model. Below: the kinds in the model's order,
-- heights and bases in metres.
global HL_furnWant = true
global HL_furnAddOnly = false
global HL_furnFloors = #("F1","F2")
global HL_furnKeys = #("plant","seat","sofa","seat-back","table","coffee-table","counter","cabinet")
global HL_furnLayers = #("Plant","Seat","Sofa","SeatBack","Table","CoffeeTable","Counter","Cabinet")
global HL_furnBases = #(0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000)
global HL_furnHeights = #(0.6000,0.4500,0.8000,0.8000,0.7500,0.4500,0.8500,0.9000)
global HL_furnLevels = #()
global HL_furnMats = #()

fn HL_layer n =
(
    local ly = LayerManager.getLayerFromName n
    if ly == undefined do ly = LayerManager.newLayerFromName n
    ly
)
fn HL_mat key =
(
    local m = undefined
    for x in HL_mats where x.name == ("HL " + key) do m = x
    m
)
fn HL_makeMaterials =
(
    HL_mats = #()
    append HL_mats (standardMaterial name:"HL Wall" diffuse:(color 227 221 211))
    append HL_mats (standardMaterial name:"HL Glass" diffuse:(color 170 200 214) opacity:30 specularLevel:60 glossiness:60)
    append HL_mats (standardMaterial name:"HL Rail" diffuse:(color 119 114 124))
    append HL_mats (standardMaterial name:"HL Single" diffuse:(color 224 164 88))
    append HL_mats (standardMaterial name:"HL Slab" diffuse:(color 212 216 210))
    append HL_mats (standardMaterial name:"HL Frame" diffuse:(color 93 107 116))
    append HL_mats (standardMaterial name:"HL Step" diffuse:(color 185 199 180))
)
fn HL_num v = ((v as string) as float)
-- The outline's knots are relative to c, the middle of the outline; the node is then moved to c, so that is its pivot.
fn HL_shape nm loops =
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
fn HL_extrudeOf o =
(
    local ex = undefined
    for md in o.modifiers where classOf md == Extrude do ex = md
    ex
)
-- kind: #wall #column #lintel #sill #parapet #glass #mullion #railing #single #step #slab; z0/z1 in metres above the
-- level of floor fi (a step of a flight going down from a level starts below it);
-- follow = the top follows that level's wall height. c = pivot, mn/mx = outline extents (DWG coordinates).
fn HL_part kind nm loops z0 z1 follow fi c mn mx =
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
    local lvl = HL_levels[fi]
    local top = if follow then HL_heights[fi] else z1
    local zb = lvl + z0
    local ht = top - z0
    local o = HL_shape nm loops
    o.pos = [c.x - HL_shift.x, c.y - HL_shift.y, zb]
    addModifier o (Extrude amount:ht segs:1 capStart:true capEnd:true output:1 smooth:false)
    addModifier o (Smooth autoSmooth:true threshold:25.0)
    local mt = HL_mat info[2]
    o.material = mt
    o.wirecolor = mt.diffuse
    setUserProp o "HL_kind" (kind as string)
    setUserProp o "HL_floor" fi
    setUserProp o "HL_base" z0
    setUserProp o "HL_follow" follow
    -- the checks run on the evaluated mesh (what the modifiers produce)
    local m = snapshotAsMesh o
    local why = ""
    local tol = 0.002
    if m.numfaces < 3 then why = "no faces"
    else if (meshop.getOpenEdges m).numberSet != 0 then why = "open edges (not a closed solid)"
    else if abs(o.min.z - zb) > tol or abs(o.max.z - (zb + ht)) > tol then why = "height"
    else if abs(o.min.x - (mn.x - HL_shift.x)) > tol or abs(o.min.y - (mn.y - HL_shift.y)) > tol or abs(o.max.x - (mx.x - HL_shift.x)) > tol or abs(o.max.y - (mx.y - HL_shift.y)) > tol then why = "position"
    m = undefined
    if why == "" then
    (
        (HL_layer ("HL_" + HL_floorNames[fi] + "_" + info[1])).addNode o
        setUserProp o "HL_check" "ok"
    )
    else
    (
        (HL_layer "HL_Check_Failed").addNode o
        setUserProp o "HL_check" why
        append HL_failed (nm + ": " + why)
    )
    if HL_collapse do convertToMesh o
    append HL_nodes o
    o
)
-- Stair lines: one shape of open two-knot splines per level and kind, knots relative to c (its pivot).
fn HL_lines nm segs fi c lay =
(
    local o = splineShape name:nm
    for k = 1 to segs.count do
    (
        addNewSpline o
        addKnot o k #corner #line [segs[k][1].x, segs[k][1].y, 0]
        addKnot o k #corner #line [segs[k][2].x, segs[k][2].y, 0]
    )
    updateShape o
    o.pos = [c.x - HL_shift.x, c.y - HL_shift.y, HL_levels[fi]]
    o.wirecolor = if lay == "Stairs" then (color 46 139 71) else (color 160 210 170)
    setUserProp o "HL_floor" fi
    setUserProp o "HL_base" 0.0
    (HL_layer ("HL_" + HL_floorNames[fi] + "_" + lay)).addNode o
    append HL_nodes o
    o
)
fn HL_room nm p fi =
(
    local t = text text:nm size:0.3 pos:[p.x - HL_shift.x, p.y - HL_shift.y, HL_levels[fi] + 0.02]
    t.name = "HL_Room_" + HL_floorNames[fi] + "_" + nm
    t.wirecolor = color 30 60 110
    setUserProp t "HL_floor" fi
    setUserProp t "HL_base" 0.02
    (HL_layer ("HL_" + HL_floorNames[fi] + "_RoomNames")).addNode t
    append HL_nodes t
    t
)
-- After the build: move every part to its level and set every live part whose top follows the wall height to its
-- level's new wall height.
fn HL_updateLevels newLevels newHeights =
(
    local n = 0
    local skipped = 0
    for o in objects where (getUserProp o "HL_floor") != undefined do
    (
        local fi = (HL_num (getUserProp o "HL_floor")) as integer
        local base = HL_num (getUserProp o "HL_base")
        o.pos.z = newLevels[fi] + base
        if ((getUserProp o "HL_follow") as string) == "true" do
        (
            local ex = HL_extrudeOf o
            if ex == undefined then skipped += 1
            else ( ex.amount = newHeights[fi] - base; n += 1 )
        )
    )
    HL_levels = newLevels
    HL_heights = newHeights
    #(n, skipped)
)
fn HL_collapseAll =
(
    local n = 0
    for o in objects where (getUserProp o "HL_kind") != undefined and o.modifiers.count > 0 do ( convertToMesh o; n += 1 )
    n
)
-- Furniture boxes: one coloured Box per piece, a placeholder the 3D team swaps for their own model by family name.
-- A box is a live Box (width along its own long axis, length across it, height), never an Editable Poly or Mesh and never
-- collapsed: "Collapse all now" only takes objects that carry HL_kind and a modifier, and a box has neither. Every box
-- carries HL_floor and HL_base (its bottom, in metres above its level) and HL_follow = false, so "Update levels
-- and heights" moves it with its level and leaves its height alone.
fn HL_furnNum v = ((v as string) as float)
fn HL_furnMakeMaterials =
(
    HL_furnMats = #()
    append HL_furnMats (standardMaterial name:"HL Furn plant" diffuse:(color 46 158 79))
    append HL_furnMats (standardMaterial name:"HL Furn seat" diffuse:(color 224 123 0))
    append HL_furnMats (standardMaterial name:"HL Furn sofa" diffuse:(color 255 179 71))
    append HL_furnMats (standardMaterial name:"HL Furn seat-back" diffuse:(color 250 128 114))
    append HL_furnMats (standardMaterial name:"HL Furn table" diffuse:(color 138 90 43))
    append HL_furnMats (standardMaterial name:"HL Furn coffee-table" diffuse:(color 201 163 122))
    append HL_furnMats (standardMaterial name:"HL Furn counter" diffuse:(color 160 82 45))
    append HL_furnMats (standardMaterial name:"HL Furn cabinet" diffuse:(color 47 127 193))
)
-- The floor levels the build was started with (a copy: nothing is shared with the script's own array).
fn HL_furnSetLevels =
(
    HL_furnLevels = #()
    for z in (HL_levels) do append HL_furnLevels z
)
-- Where a box stands, in metres above its level: on its kind's base, or on top of the kind of support it was drawn on
-- (ki = its kind, oki = the kind of its support, 0 for none). A support never stands on anything.
fn HL_furnZ0 ki oki =
(
    local z0 = HL_furnBases[ki]
    if oki > 0 do z0 = HL_furnBases[oki] + HL_furnHeights[oki]
    z0
)
-- kind = the kind, nm = the object's name, fi = the floor's index, pid = the piece's id, supId and supKind = its support's id
-- and kind ("none" for none), c = the box's centre and cs = its four corners (DWG coordinates), w d = its size along its own
-- long and short axis, ca sa = cos and sin of the angle from +x to the long axis, fam blk lay hnd = family, block, DWG layer,
-- handle ("none" for nothing). The box gets an explicit matrix: its X, Y and Z axes in the world, then its pivot (the middle of
-- its base).
fn HL_furnBox kind nm fi pid supId supKind c w d ca sa cs fam blk lay hnd =
(
    local ki = findItem HL_furnKeys kind
    local z0 = HL_furnZ0 ki (findItem HL_furnKeys supKind)
    local ht = HL_furnHeights[ki]
    local zb = HL_furnLevels[fi] + z0
    local o = box name:nm width:w length:d height:ht
    o.transform = (matrix3 [ca, sa, 0.0] [(0.0 - sa), ca, 0.0] [0.0, 0.0, 1.0] [c.x - HL_shift.x, c.y - HL_shift.y, zb])
    local mt = HL_furnMats[ki]
    o.material = mt
    o.wirecolor = mt.diffuse
    setUserProp o "HL_furn" "true"
    setUserProp o "HL_furnKind" kind
    setUserProp o "HL_furnId" pid
    setUserProp o "HL_furnOn" supId
    setUserProp o "HL_furnOnKind" supKind
    setUserProp o "HL_family" fam
    setUserProp o "HL_block" blk
    setUserProp o "HL_layer" lay
    setUserProp o "HL_handle" hnd
    setUserProp o "HL_floor" fi
    setUserProp o "HL_base" z0
    setUserProp o "HL_follow" false
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
    else if unrotated and (abs(o.min.x - (mnx - HL_shift.x)) > tol or abs(o.min.y - (mny - HL_shift.y)) > tol or abs(o.max.x - (mxx - HL_shift.x)) > tol or abs(o.max.y - (mxy - HL_shift.y)) > tol) then why = "bounding box"
    else
    (
        local hw = o.width / 2.0
        local hd = o.length / 2.0
        local lc = #([(0.0 - hw), (0.0 - hd), 0.0], [hw, (0.0 - hd), 0.0], [hw, hd, 0.0], [(0.0 - hw), hd, 0.0])
        for k = 1 to 4 do
        (
            local q = lc[k] * o.transform
            if why == "" and (abs(q.x - (cs[k].x - HL_shift.x)) > tol or abs(q.y - (cs[k].y - HL_shift.y)) > tol) then why = "corner " + (k as string)
        )
    )
    if why == "" then
    (
        (HL_layer ("HL_" + HL_furnFloors[fi] + "_Furn_" + HL_furnLayers[ki])).addNode o
        setUserProp o "HL_check" "ok"
    )
    else
    (
        (HL_layer "HL_Check_Failed").addNode o
        setUserProp o "HL_check" why
        append HL_failed (nm + ": " + why)
    )
    append HL_nodes o
    o
)
-- Every piece of the model, in the model's order.
fn HL_furnAll =
(
    HL_furnBox "seat" "HL_F1_Furn_seat_001_built-in bench" 1 "F1-seat-001" "none" "none" [(-14.8360),(-1.7650)] 4.8470 0.5900 0.000000000 1.000000000 #([(-14.5410),(-4.1885)],[(-14.5410),0.6585],[(-15.1310),0.6585],[(-15.1310),(-4.1885)]) "built-in bench" "none" "picture" "none"
    HL_furnBox "seat" "HL_F1_Furn_seat_002_built-in bench" 1 "F1-seat-002" "none" "none" [(-12.8290),0.9840] 4.6730 0.6150 1.000000000 0.000000000 #([(-15.1655),0.6765],[(-10.4925),0.6765],[(-10.4925),1.2915],[(-15.1655),1.2915]) "built-in bench" "none" "picture" "none"
    HL_furnBox "seat" "HL_F1_Furn_seat_003_check-in sofa" 1 "F1-seat-003" "none" "none" [(-5.8360),(-0.3330)] 1.4170 1.0360 1.000000000 0.000000000 #([(-6.5445),(-0.8510)],[(-5.1275),(-0.8510)],[(-5.1275),0.1850],[(-6.5445),0.1850]) "check-in sofa" "none" "picture" "none"
    HL_furnBox "seat" "HL_F1_Furn_seat_004_round sofa" 1 "F1-seat-004" "none" "none" [(-4.5540),(-1.0090)] 2.4940 2.3960 0.000000000 1.000000000 #([(-3.3560),(-2.2560)],[(-3.3560),0.2380],[(-5.7520),0.2380],[(-5.7520),(-2.2560)]) "round sofa" "none" "picture" "none"
    HL_furnBox "seat" "HL_F1_Furn_seat_005_round stool" 1 "F1-seat-005" "none" "none" [(-3.8450),(-5.4530)] 0.4570 0.4390 0.000000000 1.000000000 #([(-3.6255),(-5.6815)],[(-3.6255),(-5.2245)],[(-4.0645),(-5.2245)],[(-4.0645),(-5.6815)]) "round stool" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F1_Furn_sofa_001_armchair" 1 "F1-sofa-001" "none" "none" [(-13.4750),(-3.7830)] 0.7770 0.7480 0.887010833 0.461748613 #([(-13.6469),(-4.2941)],[(-12.9577),(-3.9354)],[(-13.3031),(-3.2719)],[(-13.9923),(-3.6306)]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F1_Furn_sofa_002_armchair" 1 "F1-sofa-002" "none" "none" [(-13.4180),(-2.2110)] 0.7770 0.7380 0.482365334 0.875970139 #([(-13.2822),(-2.7293)],[(-12.9074),(-2.0487)],[(-13.5538),(-1.6927)],[(-13.9286),(-2.3733)]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F1_Furn_sofa_003_3-seat sofa" 1 "F1-sofa-003" "none" "none" [(-13.1490),(-0.0790)] 1.8390 0.8080 1.000000000 0.000000000 #([(-14.0685),(-0.4830)],[(-12.2295),(-0.4830)],[(-12.2295),0.3250],[(-14.0685),0.3250]) "3-seat sofa" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F1_Furn_sofa_004_armchair" 1 "F1-sofa-004" "none" "none" [(-11.0070),(-1.4840)] 0.7030 0.6920 0.000000000 1.000000000 #([(-10.6610),(-1.8355)],[(-10.6610),(-1.1325)],[(-11.3530),(-1.1325)],[(-11.3530),(-1.8355)]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F1_Furn_sofa_005_armchair" 1 "F1-sofa-005" "none" "none" [(-11.0070),0.0360] 0.6920 0.6850 1.000000000 0.000000000 #([(-11.3530),(-0.3065)],[(-10.6610),(-0.3065)],[(-10.6610),0.3785],[(-11.3530),0.3785]) "armchair" "none" "picture" "none"
    HL_furnBox "seat-back" "HL_F1_Furn_seat-back_001_seat back" 1 "F1-seat-back-001" "none" "none" [(-5.8950),(-0.0430)] 0.7930 0.1760 1.000000000 0.000000000 #([(-6.2915),(-0.1310)],[(-5.4985),(-0.1310)],[(-5.4985),0.0450],[(-6.2915),0.0450]) "seat back" "none" "picture" "none"
    HL_furnBox "seat-back" "HL_F1_Furn_seat-back_002_seat back" 1 "F1-seat-back-002" "none" "none" [(-5.2920),(-1.5560)] 0.8340 0.2260 (-0.489230239) 0.872154673 #([(-4.9894),(-1.8644)],[(-5.3975),(-1.1370)],[(-5.5946),(-1.2476)],[(-5.1865),(-1.9750)]) "seat back" "none" "picture" "none"
    HL_furnBox "seat-back" "HL_F1_Furn_seat-back_003_seat back" 1 "F1-seat-back-003" "none" "none" [(-4.4850),(-0.1930)] 0.8270 0.2390 (-0.964280562) 0.264882987 #([(-4.0546),(-0.1873)],[(-4.8521),0.0318],[(-4.9154),(-0.1987)],[(-4.1179),(-0.4178)]) "seat back" "none" "picture" "none"
    HL_furnBox "seat-back" "HL_F1_Furn_seat-back_004_seat back" 1 "F1-seat-back-004" "none" "none" [(-4.3080),(-1.7970)] 0.8350 0.2370 0.957066905 0.289867106 #([(-4.6732),(-2.0314)],[(-3.8741),(-1.7894)],[(-3.9428),(-1.5626)],[(-4.7419),(-1.8046)]) "seat back" "none" "picture" "none"
    HL_furnBox "seat-back" "HL_F1_Furn_seat-back_005_seat back" 1 "F1-seat-back-005" "none" "none" [(-3.7680),(-0.9080)] 0.8670 0.2310 (-0.246491603) 0.969144927 #([(-3.5492),(-1.2997)],[(-3.7629),(-0.4594)],[(-3.9868),(-0.5163)],[(-3.7731),(-1.3566)]) "seat back" "none" "picture" "none"
    HL_furnBox "table" "HL_F1_Furn_table_001_desk" 1 "F1-table-001" "none" "none" [(-3.7860),(-5.9090)] 1.7380 0.6320 1.000000000 0.000000000 #([(-4.6550),(-6.2250)],[(-2.9170),(-6.2250)],[(-2.9170),(-5.5930)],[(-4.6550),(-5.5930)]) "desk" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F1_Furn_coffee-table_001_coffee table" 1 "F1-coffee-table-001" "none" "none" [(-13.2170),(-1.2460)] 0.8270 0.5090 1.000000000 0.000000000 #([(-13.6305),(-1.5005)],[(-12.8035),(-1.5005)],[(-12.8035),(-0.9915)],[(-13.6305),(-0.9915)]) "coffee table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F1_Furn_coffee-table_002_round side table" 1 "F1-coffee-table-002" "none" "none" [(-12.6770),(-3.4420)] 0.5440 0.5230 0.000000000 1.000000000 #([(-12.4155),(-3.7140)],[(-12.4155),(-3.1700)],[(-12.9385),(-3.1700)],[(-12.9385),(-3.7140)]) "round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F1_Furn_coffee-table_003_round side table" 1 "F1-coffee-table-003" "none" "none" [(-12.4660),(-2.0980)] 0.4570 0.4390 0.000000000 1.000000000 #([(-12.2465),(-2.3265)],[(-12.2465),(-1.8695)],[(-12.6855),(-1.8695)],[(-12.6855),(-2.3265)]) "round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F1_Furn_coffee-table_004_round side table" 1 "F1-coffee-table-004" "none" "none" [(-12.3060),(-1.1760)] 0.3690 0.3540 0.000000000 1.000000000 #([(-12.1290),(-1.3605)],[(-12.1290),(-0.9915)],[(-12.4830),(-0.9915)],[(-12.4830),(-1.3605)]) "round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F1_Furn_coffee-table_005_round side table" 1 "F1-coffee-table-005" "none" "none" [(-12.0190),(-3.6700)] 0.4040 0.3880 0.000000000 1.000000000 #([(-11.8250),(-3.8720)],[(-11.8250),(-3.4680)],[(-12.2130),(-3.4680)],[(-12.2130),(-3.8720)]) "round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F1_Furn_coffee-table_006_round side table" 1 "F1-coffee-table-006" "none" "none" [(-11.0320),(-0.7200)] 0.6150 0.6070 0.000000000 1.000000000 #([(-10.7285),(-1.0275)],[(-10.7285),(-0.4125)],[(-11.3355),(-0.4125)],[(-11.3355),(-1.0275)]) "round side table" "none" "picture" "none"
    HL_furnBox "counter" "HL_F1_Furn_counter_001_coffee counter" 1 "F1-counter-001" "none" "none" [(-12.3980),(-5.5050)] 1.9910 0.8430 1.000000000 0.000000000 #([(-13.3935),(-5.9265)],[(-11.4025),(-5.9265)],[(-11.4025),(-5.0835)],[(-13.3935),(-5.0835)]) "coffee counter" "none" "picture" "none"
    HL_furnBox "plant" "HL_F2_Furn_plant_001_shrub" 2 "F2-plant-001" "none" "none" [(-15.2880),(-10.6200)] 0.6180 0.6180 1.000000000 0.000000000 #([(-15.5970),(-10.9290)],[(-14.9790),(-10.9290)],[(-14.9790),(-10.3110)],[(-15.5970),(-10.3110)]) "shrub" "none" "picture" "none"
    HL_furnBox "plant" "HL_F2_Furn_plant_002_shrub" 2 "F2-plant-002" "none" "none" [(-15.2880),(-9.9540)] 0.6180 0.6180 1.000000000 0.000000000 #([(-15.5970),(-10.2630)],[(-14.9790),(-10.2630)],[(-14.9790),(-9.6450)],[(-15.5970),(-9.6450)]) "shrub" "none" "picture" "none"
    HL_furnBox "plant" "HL_F2_Furn_plant_003_plant" 2 "F2-plant-003" "none" "none" [(-13.4930),(-8.2660)] 0.4990 0.4760 1.000000000 0.000000000 #([(-13.7425),(-8.5040)],[(-13.2435),(-8.5040)],[(-13.2435),(-8.0280)],[(-13.7425),(-8.0280)]) "plant" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_001_dining chair" 2 "F2-seat-001" "none" "none" [(-13.7550),(-0.5380)] 0.4280 0.3570 0.000000000 1.000000000 #([(-13.5765),(-0.7520)],[(-13.5765),(-0.3240)],[(-13.9335),(-0.3240)],[(-13.9335),(-0.7520)]) "dining chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_002_dining chair" 2 "F2-seat-002" "none" "none" [(-13.7550),0.6150] 0.4040 0.3570 0.000000000 1.000000000 #([(-13.5765),0.4130],[(-13.5765),0.8170],[(-13.9335),0.8170],[(-13.9335),0.4130]) "dining chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_003_dining chair" 2 "F2-seat-003" "none" "none" [(-13.7550),1.1980] 0.4280 0.3570 0.000000000 1.000000000 #([(-13.5765),0.9840],[(-13.5765),1.4120],[(-13.9335),1.4120],[(-13.9335),0.9840]) "dining chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_004_dining chair" 2 "F2-seat-004" "none" "none" [(-13.7430),0.0450] 0.4040 0.3330 0.000000000 1.000000000 #([(-13.5765),(-0.1570)],[(-13.5765),0.2470],[(-13.9095),0.2470],[(-13.9095),(-0.1570)]) "dining chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_005_dining chair" 2 "F2-seat-005" "none" "none" [(-13.0290),1.7330] 0.4280 0.3570 1.000000000 0.000000000 #([(-13.2430),1.5545],[(-12.8150),1.5545],[(-12.8150),1.9115],[(-13.2430),1.9115]) "dining chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_006_dining chair" 2 "F2-seat-006" "none" "none" [(-13.0170),(-1.0730)] 0.4040 0.3570 1.000000000 0.000000000 #([(-13.2190),(-1.2515)],[(-12.8150),(-1.2515)],[(-12.8150),(-0.8945)],[(-13.2190),(-0.8945)]) "dining chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_007_dining chair" 2 "F2-seat-007" "none" "none" [(-12.3280),(-0.5380)] 0.4280 0.3570 0.000000000 1.000000000 #([(-12.1495),(-0.7520)],[(-12.1495),(-0.3240)],[(-12.5065),(-0.3240)],[(-12.5065),(-0.7520)]) "dining chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_008_dining chair" 2 "F2-seat-008" "none" "none" [(-12.3280),0.0450] 0.4040 0.3570 0.000000000 1.000000000 #([(-12.1495),(-0.1570)],[(-12.1495),0.2470],[(-12.5065),0.2470],[(-12.5065),(-0.1570)]) "dining chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_009_dining chair" 2 "F2-seat-009" "none" "none" [(-12.3280),0.6150] 0.4040 0.3570 0.000000000 1.000000000 #([(-12.1495),0.4130],[(-12.1495),0.8170],[(-12.5065),0.8170],[(-12.5065),0.4130]) "dining chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_010_dining chair" 2 "F2-seat-010" "none" "none" [(-12.3280),1.1980] 0.4280 0.3570 0.000000000 1.000000000 #([(-12.1495),0.9840],[(-12.1495),1.4120],[(-12.5065),1.4120],[(-12.5065),0.9840]) "dining chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_011_round stool" 2 "F2-seat-011" "none" "none" [(-11.4360),1.8760] 0.4040 0.3800 0.000000000 1.000000000 #([(-11.2460),1.6740],[(-11.2460),2.0780],[(-11.6260),2.0780],[(-11.6260),1.6740]) "round stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_012_bar stool" 2 "F2-seat-012" "none" "none" [(-10.9010),(-4.2710)] 0.3800 0.3570 0.000000000 1.000000000 #([(-10.7225),(-4.4610)],[(-10.7225),(-4.0810)],[(-11.0795),(-4.0810)],[(-11.0795),(-4.4610)]) "bar stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_013_bar stool" 2 "F2-seat-013" "none" "none" [(-10.8660),(-7.8260)] 0.3800 0.3570 1.000000000 0.000000000 #([(-11.0560),(-8.0045)],[(-10.6760),(-8.0045)],[(-10.6760),(-7.6475)],[(-11.0560),(-7.6475)]) "bar stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_014_chair" 2 "F2-seat-014" "none" "none" [(-10.8420),1.3880] 0.2850 0.2850 1.000000000 0.000000000 #([(-10.9845),1.2455],[(-10.6995),1.2455],[(-10.6995),1.5305],[(-10.9845),1.5305]) "chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_015_chair" 2 "F2-seat-015" "none" "none" [(-10.8420),2.4110] 0.3330 0.3330 1.000000000 0.000000000 #([(-11.0085),2.2445],[(-10.6755),2.2445],[(-10.6755),2.5775],[(-11.0085),2.5775]) "chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_016_chair" 2 "F2-seat-016" "none" "none" [(-10.8300),(-0.3950)] 0.4280 0.3090 0.000000000 1.000000000 #([(-10.6755),(-0.6090)],[(-10.6755),(-0.1810)],[(-10.9845),(-0.1810)],[(-10.9845),(-0.6090)]) "chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_017_chair" 2 "F2-seat-017" "none" "none" [(-10.8180),0.0450] 0.3090 0.2850 0.000000000 1.000000000 #([(-10.6755),(-0.1095)],[(-10.6755),0.1995],[(-10.9605),0.1995],[(-10.9605),(-0.1095)]) "chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_018_bar stool" 2 "F2-seat-018" "none" "none" [(-10.2590),(-4.2830)] 0.3570 0.3570 1.000000000 0.000000000 #([(-10.4375),(-4.4615)],[(-10.0805),(-4.4615)],[(-10.0805),(-4.1045)],[(-10.4375),(-4.1045)]) "bar stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_019_bar stool" 2 "F2-seat-019" "none" "none" [(-10.1880),(-7.8140)] 0.3570 0.3330 1.000000000 0.000000000 #([(-10.3665),(-7.9805)],[(-10.0095),(-7.9805)],[(-10.0095),(-7.6475)],[(-10.3665),(-7.6475)]) "bar stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_020_bar stool" 2 "F2-seat-020" "none" "none" [(-9.4980),(-4.2830)] 0.3570 0.3570 1.000000000 0.000000000 #([(-9.6765),(-4.4615)],[(-9.3195),(-4.4615)],[(-9.3195),(-4.1045)],[(-9.6765),(-4.1045)]) "bar stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_021_bar stool" 2 "F2-seat-021" "none" "none" [(-9.4750),(-7.8260)] 0.3570 0.3570 1.000000000 0.000000000 #([(-9.6535),(-8.0045)],[(-9.2965),(-8.0045)],[(-9.2965),(-7.6475)],[(-9.6535),(-7.6475)]) "bar stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_022_chair" 2 "F2-seat-022" "none" "none" [(-9.4510),(-2.3570)] 0.3090 0.2620 0.000000000 1.000000000 #([(-9.3200),(-2.5115)],[(-9.3200),(-2.2025)],[(-9.5820),(-2.2025)],[(-9.5820),(-2.5115)]) "chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_023_bench" 2 "F2-seat-023" "none" "none" [(-8.9400),(-1.7390)] 1.7600 0.4040 1.000000000 0.000000000 #([(-9.8200),(-1.9410)],[(-8.0600),(-1.9410)],[(-8.0600),(-1.5370)],[(-9.8200),(-1.5370)]) "bench" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_024_bar stool" 2 "F2-seat-024" "none" "none" [(-8.7970),(-7.8140)] 0.3800 0.3800 1.000000000 0.000000000 #([(-8.9870),(-8.0040)],[(-8.6070),(-8.0040)],[(-8.6070),(-7.6240)],[(-8.9870),(-7.6240)]) "bar stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_025_bar stool" 2 "F2-seat-025" "none" "none" [(-8.7610),(-4.2830)] 0.3570 0.3570 1.000000000 0.000000000 #([(-8.9395),(-4.4615)],[(-8.5825),(-4.4615)],[(-8.5825),(-4.1045)],[(-8.9395),(-4.1045)]) "bar stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_026_chair" 2 "F2-seat-026" "none" "none" [(-8.4280),(-2.3570)] 0.3090 0.3090 1.000000000 0.000000000 #([(-8.5825),(-2.5115)],[(-8.2735),(-2.5115)],[(-8.2735),(-2.2025)],[(-8.5825),(-2.2025)]) "chair" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_027_bar stool" 2 "F2-seat-027" "none" "none" [(-8.1070),(-7.8140)] 0.3800 0.3800 1.000000000 0.000000000 #([(-8.2970),(-8.0040)],[(-7.9170),(-8.0040)],[(-7.9170),(-7.6240)],[(-8.2970),(-7.6240)]) "bar stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_028_bar stool" 2 "F2-seat-028" "none" "none" [(-8.0240),(-4.2830)] 0.3570 0.3570 1.000000000 0.000000000 #([(-8.2025),(-4.4615)],[(-7.8455),(-4.4615)],[(-7.8455),(-4.1045)],[(-8.2025),(-4.1045)]) "bar stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_029_bar stool" 2 "F2-seat-029" "none" "none" [(-6.8830),(-6.3630)] 0.3800 0.3570 0.000000000 1.000000000 #([(-6.7045),(-6.5530)],[(-6.7045),(-6.1730)],[(-7.0615),(-6.1730)],[(-7.0615),(-6.5530)]) "bar stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_030_bar stool" 2 "F2-seat-030" "none" "none" [(-6.8710),(-7.0050)] 0.3800 0.3800 1.000000000 0.000000000 #([(-7.0610),(-7.1950)],[(-6.6810),(-7.1950)],[(-6.6810),(-6.8150)],[(-7.0610),(-6.8150)]) "bar stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_031_bar stool" 2 "F2-seat-031" "none" "none" [(-6.8710),(-5.7210)] 0.3800 0.3800 1.000000000 0.000000000 #([(-7.0610),(-5.9110)],[(-6.6810),(-5.9110)],[(-6.6810),(-5.5310)],[(-7.0610),(-5.5310)]) "bar stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_032_bar stool" 2 "F2-seat-032" "none" "none" [(-6.8710),(-5.0910)] 0.3800 0.3570 1.000000000 0.000000000 #([(-7.0610),(-5.2695)],[(-6.6810),(-5.2695)],[(-6.6810),(-4.9125)],[(-7.0610),(-4.9125)]) "bar stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_033_round stool" 2 "F2-seat-033" "none" "none" [(-6.4670),(-1.0250)] 0.4280 0.4040 1.000000000 0.000000000 #([(-6.6810),(-1.2270)],[(-6.2530),(-1.2270)],[(-6.2530),(-0.8230)],[(-6.6810),(-0.8230)]) "round stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_034_round stool" 2 "F2-seat-034" "none" "none" [(-4.9800),(-3.0350)] 0.3570 0.3330 1.000000000 0.000000000 #([(-5.1585),(-3.2015)],[(-4.8015),(-3.2015)],[(-4.8015),(-2.8685)],[(-5.1585),(-2.8685)]) "round stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_035_sculptural seating" 2 "F2-seat-035" "none" "none" [(-4.8220),0.0530] 2.7000 2.6770 (-0.139173101) 0.990268069 #([(-3.3086),(-1.0976)],[(-3.6844),1.5761],[(-6.3354),1.2036],[(-5.9596),(-1.4701)]) "sculptural seating" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_036_round stool" 2 "F2-seat-036" "none" "none" [(-4.6000),2.2800] 0.4040 0.4040 1.000000000 0.000000000 #([(-4.8020),2.0780],[(-4.3980),2.0780],[(-4.3980),2.4820],[(-4.8020),2.4820]) "round stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_037_round stool" 2 "F2-seat-037" "none" "none" [(-4.4930),(-2.8320)] 0.4040 0.3800 0.000000000 1.000000000 #([(-4.3030),(-3.0340)],[(-4.3030),(-2.6300)],[(-4.6830),(-2.6300)],[(-4.6830),(-3.0340)]) "round stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_038_sculptural seating" 2 "F2-seat-038" "none" "none" [(-4.3630),1.7270] 1.2050 0.4880 0.990413267 0.138136019 #([(-4.9260),1.4021],[(-3.7326),1.5686],[(-3.8000),2.0519],[(-4.9934),1.8854]) "sculptural seating" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_039_sculptural seating" 2 "F2-seat-039" "none" "none" [(-4.0220),(-1.8280)] 1.8550 1.3910 1.000000000 0.000000000 #([(-4.9495),(-2.5235)],[(-3.0945),(-2.5235)],[(-3.0945),(-1.1325)],[(-4.9495),(-1.1325)]) "sculptural seating" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_040_round stool" 2 "F2-seat-040" "none" "none" [(-3.3280),2.0540] 0.4280 0.4280 1.000000000 0.000000000 #([(-3.5420),1.8400],[(-3.1140),1.8400],[(-3.1140),2.2680],[(-3.5420),2.2680]) "round stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_041_round stool" 2 "F2-seat-041" "none" "none" [(-3.2090),1.5070] 0.4280 0.4280 1.000000000 0.000000000 #([(-3.4230),1.2930],[(-2.9950),1.2930],[(-2.9950),1.7210],[(-3.4230),1.7210]) "round stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_042_round stool" 2 "F2-seat-042" "none" "none" [(-3.1500),(-0.0980)] 0.4520 0.4040 1.000000000 0.000000000 #([(-3.3760),(-0.3000)],[(-2.9240),(-0.3000)],[(-2.9240),0.1040],[(-3.3760),0.1040]) "round stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_043_round stool" 2 "F2-seat-043" "none" "none" [(-2.5550),(-0.1570)] 0.4520 0.4280 1.000000000 0.000000000 #([(-2.7810),(-0.3710)],[(-2.3290),(-0.3710)],[(-2.3290),0.0570],[(-2.7810),0.0570]) "round stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_044_round stool" 2 "F2-seat-044" "none" "none" [(-0.0820),1.8990] 0.4040 0.4040 1.000000000 0.000000000 #([(-0.2840),1.6970],[0.1200,1.6970],[0.1200,2.1010],[(-0.2840),2.1010]) "round stool" "none" "picture" "none"
    HL_furnBox "seat" "HL_F2_Furn_seat_045_round stool" 2 "F2-seat-045" "none" "none" [0.5720,2.7200] 0.3800 0.3800 1.000000000 0.000000000 #([0.3820,2.5300],[0.7620,2.5300],[0.7620,2.9100],[0.3820,2.9100]) "round stool" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_001_armchair" 2 "F2-sofa-001" "none" "none" [(-14.9550),3.9210] 0.5230 0.4520 1.000000000 0.000000000 #([(-15.2165),3.6950],[(-14.6935),3.6950],[(-14.6935),4.1470],[(-15.2165),4.1470]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_002_armchair" 2 "F2-sofa-002" "none" "none" [(-14.2950),4.5490] 0.5500 0.5430 0.140210031 0.990121784 #([(-14.0647),4.2386],[(-13.9876),4.7832],[(-14.5253),4.8594],[(-14.6024),4.3148]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_003_outdoor armchair" 2 "F2-sofa-003" "none" "none" [(-14.1710),(-10.6320)] 0.6420 0.5230 0.000000000 1.000000000 #([(-13.9095),(-10.9530)],[(-13.9095),(-10.3110)],[(-14.4325),(-10.3110)],[(-14.4325),(-10.9530)]) "outdoor armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_004_armchair" 2 "F2-sofa-004" "none" "none" [(-14.0250),3.6180] 0.4770 0.4630 (-0.553536913) 0.832824643 #([(-13.7002),3.5475],[(-13.9642),3.9448],[(-14.3498),3.6885],[(-14.0858),3.2912]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_005_armchair" 2 "F2-sofa-005" "none" "none" [(-14.0120),(-2.4140)] 0.8800 0.8190 (-0.809324647) 0.587361571 #([(-13.4154),(-2.3410)],[(-14.1276),(-1.8241)],[(-14.6086),(-2.4870)],[(-13.8964),(-3.0039)]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_006_armchair" 2 "F2-sofa-006" "none" "none" [(-13.9780),5.9730] 0.5320 0.5000 0.894388560 0.447290848 #([(-14.1041),5.6304],[(-13.6283),5.8684],[(-13.8519),6.3156],[(-14.3277),6.0776]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_007_sofa" 2 "F2-sofa-007" "none" "none" [(-13.5170),6.7620] 1.4030 0.5710 1.000000000 0.000000000 #([(-14.2185),6.4765],[(-12.8155),6.4765],[(-12.8155),7.0475],[(-14.2185),7.0475]) "sofa" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_008_outdoor 3-seat sofa" 2 "F2-sofa-008" "none" "none" [(-13.4570),(-9.1220)] 2.2350 0.7130 1.000000000 0.000000000 #([(-14.5745),(-9.4785)],[(-12.3395),(-9.4785)],[(-12.3395),(-8.7655)],[(-14.5745),(-8.7655)]) "outdoor 3-seat sofa" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_009_armchair" 2 "F2-sofa-009" "none" "none" [(-13.4020),(-2.9920)] 0.5440 0.5340 (-0.800522223) 0.599303070 #([(-13.0242),(-2.9413)],[(-13.4597),(-2.6153)],[(-13.7798),(-3.0427)],[(-13.3443),(-3.3687)]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_010_armchair" 2 "F2-sofa-010" "none" "none" [(-13.0030),5.9060] 0.5410 0.5230 (-0.779993715) 0.625787347 #([(-12.6284),5.9407],[(-13.0503),6.2792],[(-13.3776),5.8713],[(-12.9557),5.5328]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_011_outdoor armchair" 2 "F2-sofa-011" "none" "none" [(-12.7200),(-10.6320)] 0.6420 0.5230 0.000000000 1.000000000 #([(-12.4585),(-10.9530)],[(-12.4585),(-10.3110)],[(-12.9815),(-10.3110)],[(-12.9815),(-10.9530)]) "outdoor armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_012_armchair" 2 "F2-sofa-012" "none" "none" [(-11.8400),4.1110] 0.5550 0.5210 (-0.707106781) 0.707106781 #([(-11.4596),4.0990],[(-11.8520),4.4914],[(-12.2204),4.1230],[(-11.8280),3.7306]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_013_armchair" 2 "F2-sofa-013" "none" "none" [(-11.8270),6.0110] 0.4700 0.4510 (-0.391534272) 0.920163526 #([(-11.5275),5.8831],[(-11.7115),6.3155],[(-12.1265),6.1389],[(-11.9425),5.7065]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_014_armchair" 2 "F2-sofa-014" "none" "none" [(-11.7250),(-3.2060)] 0.4690 0.3960 (-0.660001668) 0.751264134 #([(-11.4215),(-3.2515)],[(-11.7310),(-2.8991)],[(-12.0285),(-3.1605)],[(-11.7190),(-3.5129)]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_015_outdoor armchair" 2 "F2-sofa-015" "none" "none" [(-11.6260),(-10.6320)] 0.6420 0.5230 0.000000000 1.000000000 #([(-11.3645),(-10.9530)],[(-11.3645),(-10.3110)],[(-11.8875),(-10.3110)],[(-11.8875),(-10.9530)]) "outdoor armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_016_outdoor armchair" 2 "F2-sofa-016" "none" "none" [(-11.6150),(-9.1450)] 0.6180 0.4990 0.000000000 1.000000000 #([(-11.3655),(-9.4540)],[(-11.3655),(-8.8360)],[(-11.8645),(-8.8360)],[(-11.8645),(-9.4540)]) "outdoor armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_017_armchair" 2 "F2-sofa-017" "none" "none" [(-11.5790),3.2290] 0.5470 0.4650 0.339723022 0.940525528 #([(-11.4532),2.8928],[(-11.2674),3.4072],[(-11.7048),3.5652],[(-11.8906),3.0508]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_018_sofa" 2 "F2-sofa-018" "none" "none" [(-11.4010),6.7620] 1.4030 0.5710 1.000000000 0.000000000 #([(-12.1025),6.4765],[(-10.6995),6.4765],[(-10.6995),7.0475],[(-12.1025),7.0475]) "sofa" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_019_armchair" 2 "F2-sofa-019" "none" "none" [(-10.9080),(-3.0350)] 0.4610 0.4190 (-0.927771141) 0.373149715 #([(-10.6160),(-2.9266)],[(-11.0437),(-2.7546)],[(-11.2000),(-3.1434)],[(-10.7723),(-3.3154)]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_020_armchair" 2 "F2-sofa-020" "none" "none" [(-10.9060),5.9630] 0.4750 0.4620 0.659214584 0.751954874 #([(-10.8889),5.6321],[(-10.5757),5.9893],[(-10.9231),6.2939],[(-11.2363),5.9367]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_021_armchair" 2 "F2-sofa-021" "none" "none" [(-10.8420),3.9210] 0.5230 0.4990 1.000000000 0.000000000 #([(-11.1035),3.6715],[(-10.5805),3.6715],[(-10.5805),4.1705],[(-11.1035),4.1705]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_022_outdoor armchair" 2 "F2-sofa-022" "none" "none" [(-10.1760),(-10.6320)] 0.6420 0.5230 0.000000000 1.000000000 #([(-9.9145),(-10.9530)],[(-9.9145),(-10.3110)],[(-10.4375),(-10.3110)],[(-10.4375),(-10.9530)]) "outdoor armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_023_outdoor armchair" 2 "F2-sofa-023" "none" "none" [(-10.1640),(-9.1570)] 0.5940 0.4990 0.000000000 1.000000000 #([(-9.9145),(-9.4540)],[(-9.9145),(-8.8600)],[(-10.4135),(-8.8600)],[(-10.4135),(-9.4540)]) "outdoor armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_024_outdoor armchair" 2 "F2-sofa-024" "none" "none" [(-9.0580),(-10.6320)] 0.6420 0.5230 0.000000000 1.000000000 #([(-8.7965),(-10.9530)],[(-8.7965),(-10.3110)],[(-9.3195),(-10.3110)],[(-9.3195),(-10.9530)]) "outdoor armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_025_outdoor 3-seat sofa" 2 "F2-sofa-025" "none" "none" [(-8.3930),(-9.1220)] 2.2350 0.7130 1.000000000 0.000000000 #([(-9.5105),(-9.4785)],[(-7.2755),(-9.4785)],[(-7.2755),(-8.7655)],[(-9.5105),(-8.7655)]) "outdoor 3-seat sofa" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_026_outdoor armchair" 2 "F2-sofa-026" "none" "none" [(-7.6080),(-10.6320)] 0.6420 0.5230 0.000000000 1.000000000 #([(-7.3465),(-10.9530)],[(-7.3465),(-10.3110)],[(-7.8695),(-10.3110)],[(-7.8695),(-10.9530)]) "outdoor armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_027_armchair" 2 "F2-sofa-027" "none" "none" [(-6.3700),(-2.2890)] 0.5870 0.5340 (-0.316145824) 0.948710608 #([(-6.0239),(-2.4830)],[(-6.2095),(-1.9261)],[(-6.7161),(-2.0950)],[(-6.5305),(-2.6519)]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_028_armchair" 2 "F2-sofa-028" "none" "none" [(-4.3160),2.9180] 0.6240 0.5870 0.316145824 0.948710608 #([(-4.1362),2.5292],[(-3.9389),3.1212],[(-4.4958),3.3068],[(-4.6931),2.7148]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_029_armchair" 2 "F2-sofa-029" "none" "none" [(-2.5360),2.4080] 0.6270 0.6060 0.894388560 0.447290848 #([(-2.6809),1.9968],[(-2.1201),2.2772],[(-2.3911),2.8192],[(-2.9519),2.5388]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_030_armchair" 2 "F2-sofa-030" "none" "none" [(-2.1620),0.8730] 0.6240 0.6020 0.948710608 0.316145824 #([(-2.3628),0.4888],[(-1.7708),0.6861],[(-1.9612),1.2572],[(-2.5532),1.0599]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_031_armchair" 2 "F2-sofa-031" "none" "none" [0.5840,1.1620] 0.6900 0.6420 1.000000000 0.000000000 #([0.2390,0.8410],[0.9290,0.8410],[0.9290,1.4830],[0.2390,1.4830]) "armchair" "none" "picture" "none"
    HL_furnBox "sofa" "HL_F2_Furn_sofa_032_sofa" 2 "F2-sofa-032" "none" "none" [1.5110,1.8520] 1.9740 0.6900 0.000000000 1.000000000 #([1.8560,0.8650],[1.8560,2.8390],[1.1660,2.8390],[1.1660,0.8650]) "sofa" "none" "picture" "none"
    HL_furnBox "table" "HL_F2_Furn_table_001_dining table" 2 "F2-table-001" "none" "none" [(-13.0410),0.3300] 2.4020 1.0220 0.000000000 1.000000000 #([(-12.5300),(-0.8710)],[(-12.5300),1.5310],[(-13.5520),1.5310],[(-13.5520),(-0.8710)]) "dining table" "none" "picture" "none"
    HL_furnBox "table" "HL_F2_Furn_table_002_small round table" 2 "F2-table-002" "none" "none" [(-10.8420),1.8760] 0.5710 0.5470 1.000000000 0.000000000 #([(-11.1275),1.6025],[(-10.5565),1.6025],[(-10.5565),2.1495],[(-11.1275),2.1495]) "small round table" "none" "picture" "none"
    HL_furnBox "table" "HL_F2_Furn_table_003_small round table" 2 "F2-table-003" "none" "none" [(-8.9400),(-2.3330)] 0.5710 0.5470 1.000000000 0.000000000 #([(-9.2255),(-2.6065)],[(-8.6545),(-2.6065)],[(-8.6545),(-2.0595)],[(-9.2255),(-2.0595)]) "small round table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_001_side table" 2 "F2-coffee-table-001" "none" "none" [(-14.4200),6.9400] 0.3090 0.3090 1.000000000 0.000000000 #([(-14.5745),6.7855],[(-14.2655),6.7855],[(-14.2655),7.0945],[(-14.5745),7.0945]) "side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_002_round side table" 2 "F2-coffee-table-002" "none" "none" [(-14.3970),4.0160] 0.4990 0.4990 1.000000000 0.000000000 #([(-14.6465),3.7665],[(-14.1475),3.7665],[(-14.1475),4.2655],[(-14.6465),4.2655]) "round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_003_round side table" 2 "F2-coffee-table-003" "none" "none" [(-14.3250),(-3.1650)] 0.4040 0.4040 1.000000000 0.000000000 #([(-14.5270),(-3.3670)],[(-14.1230),(-3.3670)],[(-14.1230),(-2.9630)],[(-14.5270),(-2.9630)]) "round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_004_round side table" 2 "F2-coffee-table-004" "none" "none" [(-14.2300),(-8.1820)] 0.6900 0.6900 1.000000000 0.000000000 #([(-14.5750),(-8.5270)],[(-13.8850),(-8.5270)],[(-13.8850),(-7.8370)],[(-14.5750),(-7.8370)]) "round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_005_round side table" 2 "F2-coffee-table-005" "none" "none" [(-13.4810),6.2270] 0.5230 0.4990 1.000000000 0.000000000 #([(-13.7425),5.9775],[(-13.2195),5.9775],[(-13.2195),6.4765],[(-13.7425),6.4765]) "round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_006_outdoor round side table" 2 "F2-coffee-table-006" "none" "none" [(-13.4340),(-10.6320)] 0.5230 0.4990 1.000000000 0.000000000 #([(-13.6955),(-10.8815)],[(-13.1725),(-10.8815)],[(-13.1725),(-10.3825)],[(-13.6955),(-10.3825)]) "outdoor round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_007_side table" 2 "F2-coffee-table-007" "none" "none" [(-12.6010),6.9400] 0.3090 0.2850 0.000000000 1.000000000 #([(-12.4585),6.7855],[(-12.4585),7.0945],[(-12.7435),7.0945],[(-12.7435),6.7855]) "side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_008_side table" 2 "F2-coffee-table-008" "none" "none" [(-12.2800),6.9400] 0.3090 0.3090 1.000000000 0.000000000 #([(-12.4345),6.7855],[(-12.1255),6.7855],[(-12.1255),7.0945],[(-12.4345),7.0945]) "side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_009_round side table" 2 "F2-coffee-table-009" "none" "none" [(-11.4010),(-2.8680)] 0.5230 0.4990 0.000000000 1.000000000 #([(-11.1515),(-3.1295)],[(-11.1515),(-2.6065)],[(-11.6505),(-2.6065)],[(-11.6505),(-3.1295)]) "round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_010_round side table" 2 "F2-coffee-table-010" "none" "none" [(-11.4010),3.7780] 0.4990 0.4990 1.000000000 0.000000000 #([(-11.6505),3.5285],[(-11.1515),3.5285],[(-11.1515),4.0275],[(-11.6505),4.0275]) "round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_011_round side table" 2 "F2-coffee-table-011" "none" "none" [(-11.3530),6.2390] 0.4990 0.4760 1.000000000 0.000000000 #([(-11.6025),6.0010],[(-11.1035),6.0010],[(-11.1035),6.4770],[(-11.6025),6.4770]) "round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_012_outdoor round side table" 2 "F2-coffee-table-012" "none" "none" [(-10.9130),(-10.6200)] 0.5230 0.5230 1.000000000 0.000000000 #([(-11.1745),(-10.8815)],[(-10.6515),(-10.8815)],[(-10.6515),(-10.3585)],[(-11.1745),(-10.3585)]) "outdoor round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_013_outdoor round side table" 2 "F2-coffee-table-013" "none" "none" [(-10.8890),(-9.1450)] 0.5230 0.4760 0.000000000 1.000000000 #([(-10.6510),(-9.4065)],[(-10.6510),(-8.8835)],[(-11.1270),(-8.8835)],[(-11.1270),(-9.4065)]) "outdoor round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_014_side table" 2 "F2-coffee-table-014" "none" "none" [(-10.4970),6.9520] 0.3570 0.2850 1.000000000 0.000000000 #([(-10.6755),6.8095],[(-10.3185),6.8095],[(-10.3185),7.0945],[(-10.6755),7.0945]) "side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_015_outdoor round side table" 2 "F2-coffee-table-015" "none" "none" [(-8.3450),(-10.6200)] 0.5230 0.5230 1.000000000 0.000000000 #([(-8.6065),(-10.8815)],[(-8.0835),(-10.8815)],[(-8.0835),(-10.3585)],[(-8.6065),(-10.3585)]) "outdoor round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_016_round side table" 2 "F2-coffee-table-016" "none" "none" [(-5.4920),(-2.0120)] 0.6660 0.6660 1.000000000 0.000000000 #([(-5.8250),(-2.3450)],[(-5.1590),(-2.3450)],[(-5.1590),(-1.6790)],[(-5.8250),(-1.6790)]) "round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_017_round side table" 2 "F2-coffee-table-017" "none" "none" [(-3.0660),0.6750] 0.7130 0.7130 1.000000000 0.000000000 #([(-3.4225),0.3185],[(-2.7095),0.3185],[(-2.7095),1.0315],[(-3.4225),1.0315]) "round side table" "none" "picture" "none"
    HL_furnBox "coffee-table" "HL_F2_Furn_coffee-table_018_round side table" 2 "F2-coffee-table-018" "none" "none" [0.5720,2.0420] 0.6180 0.5940 1.000000000 0.000000000 #([0.2630,1.7450],[0.8810,1.7450],[0.8810,2.3390],[0.2630,2.3390]) "round side table" "none" "picture" "none"
    HL_furnBox "counter" "HL_F2_Furn_counter_001_back bar counter" 2 "F2-counter-001" "none" "none" [(-12.6850),(-6.0660)] 2.8770 0.8800 0.000000000 1.000000000 #([(-12.2450),(-7.5045)],[(-12.2450),(-4.6275)],[(-13.1250),(-4.6275)],[(-13.1250),(-7.5045)]) "back bar counter" "none" "picture" "none"
    HL_furnBox "counter" "HL_F2_Furn_counter_002_bar counter" 2 "F2-counter-002" "none" "none" [(-9.2250),(-7.1120)] 4.0420 0.7370 1.000000000 0.000000000 #([(-11.2460),(-7.4805)],[(-7.2040),(-7.4805)],[(-7.2040),(-6.7435)],[(-11.2460),(-6.7435)]) "bar counter" "none" "picture" "none"
    HL_furnBox "counter" "HL_F2_Furn_counter_003_bar counter" 2 "F2-counter-003" "none" "none" [(-9.2250),(-4.9840)] 4.0420 0.7130 1.000000000 0.000000000 #([(-11.2460),(-5.3405)],[(-7.2040),(-5.3405)],[(-7.2040),(-4.6275)],[(-11.2460),(-4.6275)]) "bar counter" "none" "picture" "none"
    HL_furnBox "counter" "HL_F2_Furn_counter_004_bar counter" 2 "F2-counter-004" "none" "none" [(-7.5600),(-6.0420)] 1.4030 0.7130 0.000000000 1.000000000 #([(-7.2035),(-6.7435)],[(-7.2035),(-5.3405)],[(-7.9165),(-5.3405)],[(-7.9165),(-6.7435)]) "bar counter" "none" "picture" "none"
    HL_furnBox "counter" "HL_F2_Furn_counter_005_canteen counter" 2 "F2-counter-005" "none" "none" [(-5.0280),5.5610] 1.5930 0.7850 0.000000000 1.000000000 #([(-4.6355),4.7645],[(-4.6355),6.3575],[(-5.4205),6.3575],[(-5.4205),4.7645]) "canteen counter" "none" "picture" "none"
    HL_furnBox "counter" "HL_F2_Furn_counter_006_pantry counter" 2 "F2-counter-006" "none" "none" [(-3.6250),7.2140] 1.8310 0.3330 1.000000000 0.000000000 #([(-4.5405),7.0475],[(-2.7095),7.0475],[(-2.7095),7.3805],[(-4.5405),7.3805]) "pantry counter" "none" "picture" "none"
    HL_furnBox "counter" "HL_F2_Furn_counter_007_canteen counter" 2 "F2-counter-007" "none" "none" [(-1.8060),6.6910] 7.2290 0.6660 1.000000000 0.000000000 #([(-5.4205),6.3580],[1.8085,6.3580],[1.8085,7.0240],[(-5.4205),7.0240]) "canteen counter" "none" "picture" "none"
    HL_furnBox "counter" "HL_F2_Furn_counter_008_canteen counter" 2 "F2-counter-008" "none" "none" [(-1.7820),5.2280] 2.4730 0.8800 1.000000000 0.000000000 #([(-3.0185),4.7880],[(-0.5455),4.7880],[(-0.5455),5.6680],[(-3.0185),5.6680]) "canteen counter" "none" "picture" "none"
    HL_furnBox "counter" "HL_F2_Furn_counter_009_worktop" 2 "F2-counter-009" "none" "none" [0.7260,7.3800] 1.8310 0.2850 1.000000000 0.000000000 #([(-0.1895),7.2375],[1.6415,7.2375],[1.6415,7.5225],[(-0.1895),7.5225]) "worktop" "none" "picture" "none"
    HL_furnBox "counter" "HL_F2_Furn_counter_010_canteen counter" 2 "F2-counter-010" "none" "none" [1.4160,5.5610] 1.5930 0.7850 0.000000000 1.000000000 #([1.8085,4.7645],[1.8085,6.3575],[1.0235,6.3575],[1.0235,4.7645]) "canteen counter" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_001_signature display cabinet" 2 "F2-cabinet-001" "none" "none" [(-15.2880),(-1.4890)] 0.7610 0.5710 0.000000000 1.000000000 #([(-15.0025),(-1.8695)],[(-15.0025),(-1.1085)],[(-15.5735),(-1.1085)],[(-15.5735),(-1.8695)]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_002_signature display cabinet" 2 "F2-cabinet-002" "none" "none" [(-15.2880),(-0.5730)] 0.5940 0.5710 0.000000000 1.000000000 #([(-15.0025),(-0.8700)],[(-15.0025),(-0.2760)],[(-15.5735),(-0.2760)],[(-15.5735),(-0.8700)]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_003_signature display cabinet" 2 "F2-cabinet-003" "none" "none" [(-15.2880),0.0210] 0.5940 0.5710 0.000000000 1.000000000 #([(-15.0025),(-0.2760)],[(-15.0025),0.3180],[(-15.5735),0.3180],[(-15.5735),(-0.2760)]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_004_signature display cabinet" 2 "F2-cabinet-004" "none" "none" [(-15.2880),0.6390] 0.5940 0.5710 0.000000000 1.000000000 #([(-15.0025),0.3420],[(-15.0025),0.9360],[(-15.5735),0.9360],[(-15.5735),0.3420]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_005_signature display cabinet" 2 "F2-cabinet-005" "none" "none" [(-15.2880),1.2570] 0.5940 0.5710 0.000000000 1.000000000 #([(-15.0025),0.9600],[(-15.0025),1.5540],[(-15.5735),1.5540],[(-15.5735),0.9600]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_006_signature display cabinet" 2 "F2-cabinet-006" "none" "none" [(-15.2880),1.8640] 0.5710 0.5710 1.000000000 0.000000000 #([(-15.5735),1.5785],[(-15.0025),1.5785],[(-15.0025),2.1495],[(-15.5735),2.1495]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_007_signature display cabinet" 2 "F2-cabinet-007" "none" "none" [(-15.2880),2.7440] 0.7130 0.5710 0.000000000 1.000000000 #([(-15.0025),2.3875],[(-15.0025),3.1005],[(-15.5735),3.1005],[(-15.5735),2.3875]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_008_signature display cabinet" 2 "F2-cabinet-008" "none" "none" [(-15.2640),(-7.4100)] 0.6660 0.6180 0.000000000 1.000000000 #([(-14.9550),(-7.7430)],[(-14.9550),(-7.0770)],[(-15.5730),(-7.0770)],[(-15.5730),(-7.7430)]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_009_signature display cabinet" 2 "F2-cabinet-009" "none" "none" [(-15.2640),(-6.7200)] 0.6660 0.6180 0.000000000 1.000000000 #([(-14.9550),(-7.0530)],[(-14.9550),(-6.3870)],[(-15.5730),(-6.3870)],[(-15.5730),(-7.0530)]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_010_signature display cabinet" 2 "F2-cabinet-010" "none" "none" [(-15.2640),(-6.0420)] 0.6420 0.6180 0.000000000 1.000000000 #([(-14.9550),(-6.3630)],[(-14.9550),(-5.7210)],[(-15.5730),(-5.7210)],[(-15.5730),(-6.3630)]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_011_signature display cabinet" 2 "F2-cabinet-011" "none" "none" [(-15.2640),(-5.4120)] 0.6180 0.6180 1.000000000 0.000000000 #([(-15.5730),(-5.7210)],[(-14.9550),(-5.7210)],[(-14.9550),(-5.1030)],[(-15.5730),(-5.1030)]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_012_signature display cabinet" 2 "F2-cabinet-012" "none" "none" [(-15.2640),(-4.8060)] 0.6180 0.5470 1.000000000 0.000000000 #([(-15.5730),(-5.0795)],[(-14.9550),(-5.0795)],[(-14.9550),(-4.5325)],[(-15.5730),(-4.5325)]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_013_signature display cabinet" 2 "F2-cabinet-013" "none" "none" [(-15.2640),(-3.5340)] 0.6180 0.5710 1.000000000 0.000000000 #([(-15.5730),(-3.8195)],[(-14.9550),(-3.8195)],[(-14.9550),(-3.2485)],[(-15.5730),(-3.2485)]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_014_signature display cabinet" 2 "F2-cabinet-014" "none" "none" [(-15.2640),(-2.9510)] 0.6180 0.5940 1.000000000 0.000000000 #([(-15.5730),(-3.2480)],[(-14.9550),(-3.2480)],[(-14.9550),(-2.6540)],[(-15.5730),(-2.6540)]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_015_signature display cabinet" 2 "F2-cabinet-015" "none" "none" [(-15.2640),(-2.3810)] 0.6180 0.5470 1.000000000 0.000000000 #([(-15.5730),(-2.6545)],[(-14.9550),(-2.6545)],[(-14.9550),(-2.1075)],[(-15.5730),(-2.1075)]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_016_signature display cabinet" 2 "F2-cabinet-016" "none" "none" [(-15.2290),(-8.9910)] 1.0700 0.6900 0.000000000 1.000000000 #([(-14.8840),(-9.5260)],[(-14.8840),(-8.4560)],[(-15.5740),(-8.4560)],[(-15.5740),(-9.5260)]) "signature display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_017_cabinet" 2 "F2-cabinet-017" "none" "none" [(-0.9860),(-5.8640)] 0.8800 0.3800 1.000000000 0.000000000 #([(-1.4260),(-6.0540)],[(-0.5460),(-6.0540)],[(-0.5460),(-5.6740)],[(-1.4260),(-5.6740)]) "cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_018_console" 2 "F2-cabinet-018" "none" "none" [1.0590,0.2710] 1.1650 0.3800 1.000000000 0.000000000 #([0.4765,0.0810],[1.6415,0.0810],[1.6415,0.4610],[0.4765,0.4610]) "console" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_019_display cabinet" 2 "F2-cabinet-019" "none" "none" [2.5450,0.3180] 0.5230 0.4760 1.000000000 0.000000000 #([2.2835,0.0800],[2.8065,0.0800],[2.8065,0.5560],[2.2835,0.5560]) "display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_020_display cabinet" 2 "F2-cabinet-020" "none" "none" [2.5450,0.8410] 0.5230 0.5230 1.000000000 0.000000000 #([2.2835,0.5795],[2.8065,0.5795],[2.8065,1.1025],[2.2835,1.1025]) "display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_021_display cabinet" 2 "F2-cabinet-021" "none" "none" [2.5450,1.3640] 0.5230 0.4760 1.000000000 0.000000000 #([2.2835,1.1260],[2.8065,1.1260],[2.8065,1.6020],[2.2835,1.6020]) "display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_022_display cabinet" 2 "F2-cabinet-022" "none" "none" [2.5450,1.9110] 0.5230 0.5230 1.000000000 0.000000000 #([2.2835,1.6495],[2.8065,1.6495],[2.8065,2.1725],[2.2835,2.1725]) "display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_023_display cabinet" 2 "F2-cabinet-023" "none" "none" [2.5450,2.4460] 0.5230 0.4990 1.000000000 0.000000000 #([2.2835,2.1965],[2.8065,2.1965],[2.8065,2.6955],[2.2835,2.6955]) "display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_024_display cabinet" 2 "F2-cabinet-024" "none" "none" [2.5450,2.9690] 0.5230 0.4990 1.000000000 0.000000000 #([2.2835,2.7195],[2.8065,2.7195],[2.8065,3.2185],[2.2835,3.2185]) "display cabinet" "none" "picture" "none"
    HL_furnBox "cabinet" "HL_F2_Furn_cabinet_025_display cabinet" 2 "F2-cabinet-025" "none" "none" [2.5450,3.4930] 0.5230 0.4990 1.000000000 0.000000000 #([2.2835,3.2435],[2.8065,3.2435],[2.8065,3.7425],[2.2835,3.7425]) "display cabinet" "none" "picture" "none"
)
-- The build's furniture step: materials, levels, every box.
fn HL_furnRun =
(
    HL_furnMakeMaterials()
    HL_furnSetLevels()
    HL_furnAll()
)
-- For every floor, its level as the scene has it: the most common value (to the millimetre) of z minus HL_base over the
-- objects that carry HL_floor and HL_base. Sets HL_furnLevels for the floors it finds and returns how many.
fn HL_furnSceneLevels =
(
    local fis = #()
    local mms = #()
    local cnt = #()
    for o in objects where (getUserProp o "HL_floor") != undefined and (getUserProp o "HL_base") != undefined do
    (
        local fi = (HL_furnNum (getUserProp o "HL_floor")) as integer
        local mmv = (floor ((o.pos.z - (HL_furnNum (getUserProp o "HL_base"))) * 1000.0 + 0.5)) as integer
        local k = 0
        for j = 1 to fis.count where fis[j] == fi and mms[j] == mmv do k = j
        if k == 0 then ( append fis fi; append mms mmv; append cnt 1 )
        else cnt[k] += 1
    )
    local found = 0
    for f = 1 to HL_furnFloors.count do
    (
        local best = 0
        for j = 1 to fis.count where fis[j] == f and cnt[j] > best do
        (
            best = cnt[j]
            HL_furnLevels[f] = mms[j] / 1000.0
        )
        if best > 0 do found += 1
    )
    found
)
-- "Furniture boxes only": adds the boxes to a scene already built from this model and changes nothing else. It refuses, and
-- changes nothing, when boxes are there already or System Units are not metres. The placement shift comes from the hidden
-- datum HL_ORIGIN_DWG (shift = minus its x, y) and each level from the objects that carry HL_floor and HL_base;
-- what it cannot find it takes from the window (the tick box and the level spinners), and says so. It reports in message boxes
-- of its own (the Build button's message is written for parts), so HL_build returns false after it.
fn HL_furnAdd =
(
    if HL_furnWant == false then
    (
        messageBox "Tick Build furniture boxes as well. Nothing in this scene has been changed." title:"Hotel"
        return false
    )
    if abs(units.systemScale - 1.0) > 0.0001 or units.systemType != #meters then
    (
        messageBox "This scene's System Units are not metres, so the boxes would come out the wrong size. Nothing in this scene has been changed." title:"Hotel"
        return false
    )
    local existing = 0
    for o in objects where (getUserProp o "HL_furn") != undefined or (matchPattern o.layer.name pattern:"HL_*_Furn_*") do existing += 1
    if existing > 0 then
    (
        messageBox ("This scene already has furniture boxes (" + (existing as string) + " objects). Nothing in this scene has been changed.") title:"Hotel"
        return false
    )
    local t0 = timeStamp()
    local notes = ""
    local datum = undefined
    for o in objects where o.name == "HL_ORIGIN_DWG" do datum = o
    if datum == undefined then notes += "The origin datum HL_ORIGIN_DWG was not found, so the boxes are placed by the tick box At the drawing's own coordinates. "
    else HL_shift = [0.0 - datum.pos.x, 0.0 - datum.pos.y]
    HL_nodes = #()
    HL_failed = #()
    HL_furnMakeMaterials()
    HL_furnSetLevels()
    local found = HL_furnSceneLevels()
    if found < HL_furnFloors.count then notes += "The level of " + ((HL_furnFloors.count - found) as string) + " floor(s) was not found in the scene, so the level spinners are used for it. "
    HL_furnAll()
    format "HL FURNITURE BOXES ADDED: % boxes in % s, % failed checks\n" HL_nodes.count ((timeStamp() - t0) / 1000.0) HL_failed.count
    for f in HL_failed do format "  check failed: %\n" f
    if notes != "" do messageBox notes title:"Hotel"
    if HL_failed.count == 0 then messageBox ("Added " + (HL_nodes.count as string) + " furniture boxes. Every box passed its height and position checks. Nothing else in this scene was changed. Save As to keep your .max file.") title:"Hotel"
    else messageBox ((HL_failed.count as string) + " of the " + (HL_nodes.count as string) + " furniture boxes failed a check and are on layer HL_Check_Failed (listed in the MAXScript Listener). The others were added and passed. Nothing else in this scene was changed.") title:"Hotel"
    true
)
-- After the build: every box takes the height of its kind (HL_furnHeights, read from the window) and stands on its kind's
-- base, or on top of the kind of support it was drawn on (the support's kind is none, or undefined, or empty: no support). A box
-- keeps the level it is on (its z minus its HL_base), so levels moved by "Update levels and heights" stay. A box that is not
-- a Box any more, or of an unknown kind, is left alone.
fn HL_furnApply =
(
    local n = 0
    local skipped = 0
    for o in objects where (getUserProp o "HL_furn") != undefined do
    (
        local ki = findItem HL_furnKeys ((getUserProp o "HL_furnKind") as string)
        if (classOf o) != Box or ki == 0 then skipped += 1
        else
        (
            local z0 = HL_furnZ0 ki (findItem HL_furnKeys ((getUserProp o "HL_furnOnKind") as string))
            o.pos.z = o.pos.z - (HL_furnNum (getUserProp o "HL_base")) + z0
            o.height = HL_furnHeights[ki]
            setUserProp o "HL_base" z0
            n += 1
        )
    )
    #(n, skipped)
)
fn HL_build =
(
    if HL_furnAddOnly then
    (
        -- "Furniture boxes only" has said what it did, or why it did nothing, in its own message: false = nothing more to report
        HL_furnAdd()
        return false
    )
    if objects.count > 0 then
    (
        messageBox "Open a NEW EMPTY scene first. Nothing in this scene has been changed." title:"Hotel"
        return false
    )
    units.systemType = #meters
    units.systemScale = 1.0
    units.displayType = #metric
    units.metricType = #meters
    HL_nodes = #()
    HL_failed = #()
    HL_makeMaterials()
    local t0 = timeStamp()
    HL_part #wall "HL_F1_Wall_001" #(#([0.6245,(-1.3650)],[0.6245,(-0.2440)],[0.8435,(-0.2440)],[0.8435,(-0.1160)],[0.6865,(-0.1160)],[0.6245,(-0.0930)],[0.6245,1.3650],[(-0.7705),1.3650],[(-0.7705),1.3030],[0.4845,1.3030],[0.5555,1.2420],[0.5555,(-1.2510)],[(-0.8435),(-1.2510)],[(-0.8435),(-1.3260)],[0.4165,(-1.3260)],[0.4165,(-1.3650)])) 0.0000 2.9000 true 1 [(-6.1685),(-6.4310)] [(-7.0120),(-7.7960)] [(-5.3250),(-5.0660)]
    HL_part #wall "HL_F1_Wall_002" #(#([0.8180,(-1.3455)],[0.8180,(-1.2705)],[(-0.5130),(-1.2705)],[(-0.5130),1.2135],[0.8180,1.2135],[0.8180,1.3455],[(-0.5700),1.3455],[(-0.5700),(-0.0245)],[(-0.6530),(-0.1355)],[(-0.8180),(-0.1355)],[(-0.8180),(-0.2635)],[(-0.6360),(-0.2635)],[(-0.5700),(-0.3405)],[(-0.5700),(-1.3455)])) 0.0000 2.9000 true 1 [(-9.5860),(-6.4115)] [(-10.4040),(-7.7570)] [(-8.7680),(-5.0660)]
    HL_part #wall "HL_F1_Wall_003" #(#([(-0.1520),(-0.0295)],[0.1520,(-0.0295)],[0.1520,0.0295],[(-0.1520),0.0295])) 0.0000 2.9000 true 1 [0.1510,(-5.4545)] [(-0.0010),(-5.4840)] [0.3030,(-5.4250)]
    HL_part #wall "HL_F1_Wall_004" #(#([(-0.8245),(-1.8080)],[(-0.5205),(-1.8080)],[(-0.5205),(-1.7500)],[(-0.5255),(-1.7500)],[(-0.5255),(-1.1570)],[1.7725,(-1.1570)],[1.7725,(-3.4820)],[(-0.5255),(-3.4820)],[(-0.5255),(-2.8670)],[(-0.8225),(-2.8670)],[(-0.8225),(-3.4820)],[(-1.6995),(-3.4820)],[(-1.7415),(-3.5030)],[(-1.7415),(-3.9300)],[(-2.1215),(-3.9300)],[(-2.1215),(-4.0300)],[(-2.0035),(-4.0580)],[(-1.6325),(-4.0580)],[(-1.5985),(-4.1180)],[(-1.5985),(-4.1370)],[(-1.4565),(-4.1370)],[(-1.4565),(-3.8120)],[0.1845,(-3.8120)],[0.1845,(-4.0580)],[0.4175,(-4.0580)],[0.4175,(-3.8120)],[2.0205,(-3.8120)],[2.0205,(-4.1370)],[2.1975,(-4.1370)],[2.1975,4.1240],[1.8605,4.1240],[1.8095,4.1370],[1.7755,4.1240],[(-2.1975),4.1240],[(-2.1975),3.9400],[(-2.0965),3.9400],[(-2.0965),3.9700],[2.0865,3.9700],[2.0865,2.6180],[(-0.8225),2.6180],[(-0.8225),2.5740],[(-0.8395),2.5740],[(-0.8395),1.5900],[(-0.8225),1.5900],[(-0.8225),0.7820],[(-0.5255),0.7820],[(-0.5255),1.3180],[1.7725,1.3180],[1.7725,(-0.7630)],[1.7085,(-0.9200)],[(-0.5255),(-0.9200)],[(-0.5255),(-0.3350)],[(-0.8225),(-0.3350)],[(-0.8225),(-1.7470)],[(-0.8065),(-1.7500)],[(-0.8245),(-1.7500)]),#([(-0.5015),2.4700],[(-0.4845),2.4750],[1.5565,2.4750],[1.5565,2.4700],[1.7725,2.4700],[1.7725,1.6010],[(-0.6535),1.6010],[(-0.7375),1.6040],[(-0.7375),2.4750],[(-0.6195),2.4750],[(-0.6195),2.4700])) 0.0000 2.9000 true 1 [0.8235,(-2.6170)] [(-1.3740),(-6.7540)] [3.0210,1.5200]
    HL_part #wall "HL_F1_Wall_005" #(#([(-0.1520),(-0.0295)],[0.1520,(-0.0295)],[0.1520,0.0295],[(-0.1520),0.0295])) 0.0000 2.9000 true 1 [0.1510,(-2.9225)] [(-0.0010),(-2.9520)] [0.3030,(-2.8930)]
    HL_part #wall "HL_F1_Wall_006" #(#([2.3710,3.4595],[2.3810,3.4645],[(-2.6230),3.4645],[(-2.6260),3.4945],[(-2.6260),(-4.7965)],[(-1.9310),(-4.7965)],[(-1.8970),(-4.7245)],[(-1.8640),(-4.7175)],[(-1.6440),(-4.7175)],[(-1.6860),(-4.6725)],[(-1.6860),(-4.5895)],[(-1.8800),(-4.5895)],[(-1.8800),(-2.2745)],[(-2.3000),(-2.2745)],[(-2.3000),3.2805],[2.3890,3.2805],[2.3880,3.2845],[2.4050,3.2845],[2.4060,2.6695],[2.4590,2.6695],[2.4590,2.6165],[2.4060,2.6165],[2.4060,0.0525],[2.4590,(-0.0175)],[2.4590,(-0.0795)],[2.6070,(-0.0795)],[2.6260,(-0.0885)],[2.6250,4.7965],[2.4060,4.7965],[2.4050,3.4595])) 0.0000 2.9000 true 1 [(-12.8630),(-1.9575)] [(-15.4890),(-6.7540)] [(-10.2370),2.8390]
    HL_part #wall "HL_F1_Wall_007" #(#([(-0.1520),0.0290],[(-0.1520),(-0.0290)],[0.1520,(-0.0290)],[0.1520,0.0290])) 0.0000 2.9000 true 1 [0.1510,(-1.8640)] [(-0.0010),(-1.8930)] [0.3030,(-1.8350)]
    HL_part #wall "HL_F1_Wall_008" #(#([2.0915,0.5440],[2.0915,0.6480],[2.1595,0.6480],[2.1595,0.8320],[(-1.8875),0.8320],[(-1.8875),2.6890],[(-1.9235),2.6890],[(-1.9235),2.7120],[(-2.0245),2.7120],[(-2.0585),2.6590],[(-2.1205),2.6590],[(-2.1205),(-1.5610)],[(-2.1425),(-1.6260)],[(-2.1205),(-1.6260)],[(-2.1205),(-1.9650)],[(-2.1255),(-1.9830)],[(-2.1255),(-2.0180)],[(-2.1205),(-2.0360)],[(-2.1205),(-2.3690)],[(-2.1595),(-2.4040)],[(-2.1205),(-2.4040)],[(-2.1205),(-2.7120)],[(-1.8875),(-2.7120)],[(-1.8875),(-2.5270)],[(-1.9045),(-2.5270)],[(-1.9045),0.5440])) 0.0000 2.9000 true 1 [(-5.6165),0.6750] [(-7.7760),(-2.0370)] [(-3.4570),3.3870]
    HL_part #mullion "HL_F1_Mullion_001_mullion" #(#([(-0.1350),(-0.0615)],[0.1350,(-0.0615)],[0.1350,0.0615],[(-0.1350),0.0615])) 0.0000 2.9000 true 1 [(-3.9630),(-6.6205)] [(-4.0980),(-6.6820)] [(-3.8280),(-6.5590)]
    HL_part #mullion "HL_F1_Mullion_002_mullion" #(#([(-0.1180),(-0.0700)],[0.1180,(-0.0700)],[0.1180,0.0700],[(-0.1180),0.0700])) 0.0000 2.9000 true 1 [(-5.3970),(-6.6120)] [(-5.5150),(-6.6820)] [(-5.2790),(-6.5420)]
    HL_part #mullion "HL_F1_Mullion_003_mullion" #(#([(-0.1180),(-0.0530)],[0.1180,(-0.0530)],[0.1180,0.0530],[(-0.1180),0.0530])) 0.0000 2.9000 true 1 [(-14.6250),(-6.6120)] [(-14.7430),(-6.6650)] [(-14.5070),(-6.5590)]
    HL_part #mullion "HL_F1_Mullion_004_mullion" #(#([(-0.1185),(-0.0530)],[0.1185,(-0.0530)],[0.1185,0.0530],[(-0.1185),0.0530])) 0.0000 2.9000 true 1 [(-11.7405),(-6.6120)] [(-11.8590),(-6.6650)] [(-11.6220),(-6.5590)]
    HL_part #mullion "HL_F1_Mullion_005_mullion" #(#([(-0.1100),(-0.0530)],[0.1100,(-0.0530)],[0.1100,0.0530],[(-0.1100),0.0530])) 0.0000 2.9000 true 1 [(-1.0870),(-6.6120)] [(-1.1970),(-6.6650)] [(-0.9770),(-6.5590)]
    HL_part #mullion "HL_F1_Mullion_006_mullion" #(#([(-0.1265),(-0.0615)],[0.1265,(-0.0615)],[0.1265,0.0615],[(-0.1265),0.0615])) 0.0000 2.9000 true 1 [(-13.2165),(-6.6035)] [(-13.3430),(-6.6650)] [(-13.0900),(-6.5420)]
    HL_part #mullion "HL_F1_Mullion_007_mullion" #(#([(-0.1265),(-0.0615)],[0.1265,(-0.0615)],[0.1265,0.0615],[(-0.1265),0.0615])) 0.0000 2.9000 true 1 [(-2.4875),(-6.6035)] [(-2.6140),(-6.6650)] [(-2.3610),(-6.5420)]
    HL_part #mullion "HL_F1_Mullion_008_mullion" #(#([(-0.1180),(-0.0705)],[0.1180,(-0.0705)],[0.1180,0.0705],[(-0.1180),0.0705])) 0.0000 2.9000 true 1 [(-10.3230),(-6.5945)] [(-10.4410),(-6.6650)] [(-10.2050),(-6.5240)]
    HL_part #glass "HL_F1_Glass_001_F1-G1 glazing" #(#([(-0.5895),(-0.0250)],[0.5895,(-0.0250)],[0.5895,0.0250],[(-0.5895),0.0250])) 0.0000 2.9000 true 1 [(-11.0315),(-6.6100)] [(-11.6210),(-6.6350)] [(-10.4420),(-6.5850)]
    HL_part #glass "HL_F1_Glass_002_F1-G1 glazing" #(#([(-0.6145),(-0.0250)],[0.6145,(-0.0250)],[0.6145,0.0250],[(-0.6145),0.0250])) 0.0000 2.9000 true 1 [(-12.4745),(-6.6100)] [(-13.0890),(-6.6350)] [(-11.8600),(-6.5850)]
    HL_part #glass "HL_F1_Glass_003_F1-G1 glazing" #(#([(-0.5810),(-0.0250)],[0.5810,(-0.0250)],[0.5810,0.0250],[(-0.5810),0.0250])) 0.0000 2.9000 true 1 [(-13.9250),(-6.6100)] [(-14.5060),(-6.6350)] [(-13.3440),(-6.5850)]
    HL_part #glass "HL_F1_Glass_004_F1-G2 glazing" #(#([(-0.5305),(-0.0250)],[0.5305,(-0.0250)],[0.5305,0.0250],[(-0.5305),0.0250])) 0.0000 2.9000 true 1 [(-1.8295),(-6.6100)] [(-2.3600),(-6.6350)] [(-1.2990),(-6.5850)]
    HL_part #glass "HL_F1_Glass_005_F1-G2 glazing" #(#([(-0.6060),(-0.0250)],[0.6060,(-0.0250)],[0.6060,0.0250],[(-0.6060),0.0250])) 0.0000 2.9000 true 1 [(-3.2210),(-6.6100)] [(-3.8270),(-6.6350)] [(-2.6150),(-6.5850)]
    HL_part #glass "HL_F1_Glass_006_F1-G2 glazing" #(#([(-0.5895),(-0.0250)],[0.5895,(-0.0250)],[0.5895,0.0250],[(-0.5895),0.0250])) 0.0000 2.9000 true 1 [(-4.6885),(-6.6100)] [(-5.2780),(-6.6350)] [(-4.0990),(-6.5850)]
    HL_part #glass "HL_F1_Glass_007_F1-G3 glazing" #(#([(-0.8195),(-0.0250)],[0.8195,(-0.0250)],[0.8195,0.0250],[(-0.8195),0.0250])) 0.0000 2.9000 true 1 [0.1875,(-6.5400)] [(-0.6320),(-6.5650)] [1.0070,(-6.5150)]
    HL_part #glass "HL_F1_Glass_008_F1-G4 glazing" #(#([(-0.8005),(-0.0250)],[0.8005,(-0.0250)],[0.8005,0.0250],[(-0.8005),0.0250])) 0.0000 2.9000 true 1 [2.0425,(-6.5400)] [1.2420,(-6.5650)] [2.8430,(-6.5150)]
    HL_part #lintel "HL_F1_Lintel_001_F1-001" #(#([(-0.1520),(-0.4990)],[0.1520,(-0.4990)],[0.1520,0.4990],[(-0.1520),0.4990])) 2.1000 2.9000 true 1 [0.1510,(-2.3930)] [(-0.0010),(-2.8920)] [0.3030,(-1.8940)]
    HL_part #lintel "HL_F1_Lintel_002_F1-002" #(#([(-0.1520),(-0.4990)],[0.1520,(-0.4990)],[0.1520,0.4990],[(-0.1520),0.4990])) 2.1000 2.9000 true 1 [0.1510,(-4.9250)] [(-0.0010),(-5.4240)] [0.3030,(-4.4260)]
    HL_part #lintel "HL_F1_Lintel_003_F1-003" #(#([(-1.0405),0.0920],[(-1.0405),(-0.0920)],[1.0405,(-0.0920)],[1.0405,0.0920])) 2.1000 2.9000 true 1 [(-2.4155),1.4150] [(-3.4560),1.3230] [(-1.3750),1.5070]
    HL_part #lintel "HL_F1_Lintel_004_F1-004" #(#([(-0.9165),0.0520],[(-0.9165),(-0.0520)],[0.9165,(-0.0110)],[0.9105,(-0.0100)],[0.9105,0.0520])) 2.1000 2.9000 true 1 [(-7.8505),(-5.1180)] [(-8.7670),(-5.1700)] [(-6.9340),(-5.0660)]
    HL_part #lintel "HL_F1_Lintel_005_F1-005" #(#([(-0.8770),0.0375],[(-0.8770),(-0.0375)],[0.8770,(-0.0375)],[0.8770,0.0375])) 2.1000 2.9000 true 1 [(-7.8900),(-7.7195)] [(-8.7670),(-7.7570)] [(-7.0130),(-7.6820)]
    HL_part #step "HL_F1_Step_001_F1-S1 step 1 up" #(#([1.2500,0.1355],[(-1.2500),0.1355],[(-1.2500),(-0.1355)],[1.2500,(-0.1355)])) (-0.1710) 0.1710 false 1 [(-8.9880),(-1.3535)] [(-10.2380),(-1.4890)] [(-7.7380),(-1.2180)]
    HL_part #step "HL_F1_Step_002_F1-S1 step 2 up" #(#([1.2500,0.1350],[(-1.2500),0.1350],[(-1.2500),(-0.1350)],[1.2500,(-0.1350)])) 0.0000 0.3410 false 1 [(-8.9880),(-1.0830)] [(-10.2380),(-1.2180)] [(-7.7380),(-0.9480)]
    HL_part #step "HL_F1_Step_003_F1-S1 step 3 up" #(#([1.2500,0.1350],[(-1.2500),0.1350],[(-1.2500),(-0.1350)],[1.2500,(-0.1350)])) 0.1710 0.5120 false 1 [(-8.9880),(-0.8130)] [(-10.2380),(-0.9480)] [(-7.7380),(-0.6780)]
    HL_part #step "HL_F1_Step_004_F1-S1 step 4 up" #(#([1.2500,0.1355],[(-1.2500),0.1355],[(-1.2500),(-0.1355)],[1.2500,(-0.1355)])) 0.3410 0.6820 false 1 [(-8.9880),(-0.5425)] [(-10.2380),(-0.6780)] [(-7.7380),(-0.4070)]
    HL_part #step "HL_F1_Step_005_F1-S1 step 5 up" #(#([1.2500,0.1350],[(-1.2500),0.1350],[(-1.2500),(-0.1350)],[1.2500,(-0.1350)])) 0.5120 0.8530 false 1 [(-8.9880),(-0.2720)] [(-10.2380),(-0.4070)] [(-7.7380),(-0.1370)]
    HL_part #step "HL_F1_Step_006_F1-S1 step 6 up" #(#([1.2500,0.1355],[(-1.2500),0.1355],[(-1.2500),(-0.1355)],[1.2500,(-0.1355)])) 0.6820 1.0240 false 1 [(-8.9880),(-0.0015)] [(-10.2380),(-0.1370)] [(-7.7380),0.1340]
    HL_part #step "HL_F1_Step_007_F1-S1 step 7 up" #(#([1.2500,0.1350],[(-1.2500),0.1350],[(-1.2500),(-0.1350)],[1.2500,(-0.1350)])) 0.8530 1.1940 false 1 [(-8.9880),0.2690] [(-10.2380),0.1340] [(-7.7380),0.4040]
    HL_part #step "HL_F1_Step_008_F1-S1 step 8 up" #(#([1.2500,0.1355],[(-1.2500),0.1355],[(-1.2500),(-0.1355)],[1.2500,(-0.1355)])) 1.0240 1.3650 false 1 [(-8.9880),0.5395] [(-10.2380),0.4040] [(-7.7380),0.6750]
    HL_part #step "HL_F1_Step_009_F1-S1 step 9 up" #(#([1.2500,0.1350],[(-1.2500),0.1350],[(-1.2500),(-0.1350)],[1.2500,(-0.1350)])) 1.1940 1.5350 false 1 [(-8.9880),0.8100] [(-10.2380),0.6750] [(-7.7380),0.9450]
    HL_part #step "HL_F1_Step_010_F1-S1 step 10 up" #(#([1.2500,0.1355],[(-1.2500),0.1355],[(-1.2500),(-0.1355)],[1.2500,(-0.1355)])) 1.3650 1.7060 false 1 [(-8.9880),1.0805] [(-10.2380),0.9450] [(-7.7380),1.2160]
    HL_part #step "HL_F1_Step_011_F1-S1 step 11 up" #(#([1.2500,0.1350],[(-1.2500),0.1350],[(-1.2500),(-0.1350)],[1.2500,(-0.1350)])) 1.5350 1.8760 false 1 [(-8.9880),1.3510] [(-10.2380),1.2160] [(-7.7380),1.4860]
    HL_part #step "HL_F1_Step_012_F1-S1 step 12 up" #(#([1.2500,0.1355],[(-1.2500),0.1355],[(-1.2500),(-0.1355)],[1.2500,(-0.1355)])) 1.7060 2.0470 false 1 [(-8.9880),1.6215] [(-10.2380),1.4860] [(-7.7380),1.7570]
    HL_part #step "HL_F1_Step_013_F1-S1 step 13 up" #(#([1.2500,0.1350],[(-1.2500),0.1350],[(-1.2500),(-0.1350)],[1.2500,(-0.1350)])) 1.8760 2.2180 false 1 [(-8.9880),1.8920] [(-10.2380),1.7570] [(-7.7380),2.0270]
    HL_part #step "HL_F1_Step_014_F1-S1 step 14 up" #(#([1.2500,0.1355],[(-1.2500),0.1355],[(-1.2500),(-0.1355)],[1.2500,(-0.1355)])) 2.0470 2.3880 false 1 [(-8.9880),2.1625] [(-10.2380),2.0270] [(-7.7380),2.2980]
    HL_part #step "HL_F1_Step_015_F1-S1 step 15 up" #(#([1.2500,0.1350],[(-1.2500),0.1350],[(-1.2500),(-0.1350)],[1.2500,(-0.1350)])) 2.2180 2.5590 false 1 [(-8.9880),2.4330] [(-10.2380),2.2980] [(-7.7380),2.5680]
    HL_part #step "HL_F1_Step_016_F1-S1 step 16 up" #(#([1.2500,0.1355],[(-1.2500),0.1355],[(-1.2500),(-0.1355)],[1.2500,(-0.1355)])) 2.3880 2.7290 false 1 [(-8.9880),2.7035] [(-10.2380),2.5680] [(-7.7380),2.8390]
    HL_part #slab "HL_F1_Slab_001" #(#([(-9.2850),(-4.5795)],[(-8.5410),(-4.5795)],[(-8.5070),(-4.5075)],[(-8.2060),(-4.4985)],[(-8.2420),(-4.4605)],[(-7.1390),(-4.4605)],[(-7.1390),(-4.4905)],[(-6.8260),(-4.4905)],[(-6.8260),(-4.4605)],[(-5.6550),(-4.4605)],[(-5.6550),(-4.4905)],[(-5.3580),(-4.4905)],[(-5.3580),(-4.4605)],[(-4.2370),(-4.4605)],[(-4.2370),(-4.4825)],[(-4.1750),(-4.5005)],[(-4.0020),(-4.5005)],[(-3.9520),(-4.5585)],[(-3.9520),(-5.5825)],[0.4520,(-5.5825)],[0.4520,(-5.6215)],[0.7200,(-5.6215)],[0.7200,(-4.5075)],[0.9850,(-4.5075)],[0.9850,(-4.4605)],[2.1060,(-4.4605)],[2.1060,(-4.5075)],[2.4360,(-4.5075)],[2.4360,(-4.4605)],[3.5900,(-4.4605)],[3.5900,(-4.4905)],[3.9030,(-4.4905)],[3.9030,(-4.4605)],[4.9310,(-4.4605)],[5.0490,(-4.5005)],[5.4060,(-4.5005)],[5.4390,(-4.5795)],[5.6310,(-4.5795)],[5.6310,(-4.3905)],[7.2120,(-4.3905)],[7.2120,(-4.5005)],[7.5050,(-4.5005)],[7.5050,(-4.3905)],[9.0480,(-4.3905)],[9.0480,(-4.5795)],[9.2850,(-4.5795)],[9.2850,3.7415],[2.7070,3.7615],[(-1.2400),3.7425],[(-1.2400),5.5845],[(-1.2970),5.6215],[(-1.4230),5.6215],[(-1.4570),5.5685],[(-1.5330),5.5685],[(-1.5330),3.6585],[(-3.9730),3.6585],[(-3.9740),5.0735],[(-4.2530),5.0735],[(-4.2530),3.7415],[(-9.2250),3.7415],[(-9.2420),3.8925],[(-9.2850),3.8905])) (-0.2000) 0.0000 false 1 [(-6.2340),(-2.2045)] [(-15.5190),(-7.8260)] [3.0510,3.4170]
    HL_part #slab "HL_F1_Slab_002_forecourt (outdoor paving, assumed)" #(#([9.2620,0.6705],[9.0540,0.6705],[9.0540,0.8605],[7.5130,0.8605],[7.5120,0.7495],[7.2190,0.7495],[7.2190,0.8605],[5.6380,0.8605],[5.6380,0.6705],[5.4460,0.6705],[5.4120,0.7495],[5.0560,0.7495],[4.9380,0.7895],[3.9110,0.7895],[3.9100,0.7605],[3.5970,0.7605],[3.5970,0.7895],[2.4430,0.7895],[2.4430,0.7425],[2.1130,0.7425],[2.1120,0.7895],[0.9920,0.7895],[0.9920,0.7425],[0.7270,0.7425],[0.7270,(-0.3705)],[0.4590,(-0.3705)],[0.4590,(-0.3325)],[(-3.9450),(-0.3325)],[(-3.9460),0.6915],[(-3.9950),0.7495],[(-4.1680),0.7495],[(-4.2310),0.7895],[(-5.3510),0.7895],[(-5.3510),0.7605],[(-5.6480),0.7605],[(-5.6480),0.7895],[(-6.8190),0.7895],[(-6.8190),0.7605],[(-7.1320),0.7605],[(-7.1330),0.7895],[(-8.2330),0.7895],[(-8.1990),0.7515],[(-8.5000),0.7435],[(-8.5340),0.6705],[(-9.2620),0.6705],[(-9.2620),(-0.8605)],[9.2620,(-0.8605)])) (-0.2000) 0.0000 false 1 [(-6.2410),(-7.4555)] [(-15.5030),(-8.3160)] [3.0210,(-6.5950)]
    HL_part #wall "HL_F2_Wall_001" #(#([0.8400,(-6.3155)],[0.8400,(-6.1855)],[0.4950,(-6.1855)],[0.4950,(-6.3235)],[0.5670,(-6.3235)],[0.5920,(-6.3485)],[0.5920,(-6.5385)],[0.6680,(-6.5625)],[0.6680,(-6.9025)],[(-0.9280),(-6.9025)],[(-0.9280),(-6.4865)],[(-1.4220),(-6.4865)],[(-1.4220),(-6.5865)],[(-1.2820),(-6.6105)],[(-1.2820),(-7.0885)],[3.3260,(-7.0885)],[3.3260,(-10.2485)],[3.2690,(-10.3905)],[(-2.6040),(-10.3905)],[(-2.6040),(-10.3315)],[(-3.3170),(-10.3315)],[(-3.3170),(-7.0975)],[(-2.6040),(-7.0975)],[(-2.6040),(-6.8595)],[(-3.3170),(-6.8595)],[(-3.3170),(-6.8485)],[(-3.5310),(-6.8485)],[(-3.5310),(-10.5815)],[(-3.3170),(-10.5815)],[(-3.3170),(-10.5435)],[3.4760,(-10.5435)],[3.4760,7.2285],[3.5310,7.2285],[3.5310,10.5815],[3.2930,10.5815],[3.2930,7.2285],[3.3260,7.2285],[3.3260,6.4035],[3.2930,6.4035],[3.2930,6.2335],[3.3260,6.2065],[3.3260,(-0.7795)],[0.4250,(-0.7795)],[0.4250,(-1.0345)],[3.1170,(-1.0345)],[3.1170,(-1.8735)],[0.4250,(-1.8735)],[0.4250,(-2.5915)],[0.4510,(-2.6805)],[0.4130,(-2.6805)],[0.4130,(-2.8065)],[0.8180,(-2.8065)],[0.8180,(-2.6805)],[0.7980,(-2.6805)],[0.7980,(-2.1285)],[3.1170,(-2.1285)],[3.1170,(-4.3705)],[0.7980,(-4.3705)],[0.7980,(-3.9325)],[0.8180,(-3.9325)],[0.8180,(-3.8065)],[0.4130,(-3.8065)],[0.4130,(-3.9325)],[0.4250,(-3.9325)],[0.4250,(-4.9935)],[0.4630,(-5.0485)],[0.4950,(-5.0485)],[0.4950,(-5.1855)],[0.8400,(-5.1855)],[0.8400,(-5.0475)],[0.7980,(-5.0475)],[0.7980,(-4.5935)],[3.1170,(-4.5935)],[3.1170,(-6.9025)],[0.9390,(-6.9025)],[0.8440,(-6.8485)],[0.8440,(-6.3245)],[0.8670,(-6.3155)])) 0.0000 2.9000 true 2 [(-0.4860),0.8175] [(-4.0170),(-9.7640)] [3.0450,11.3990]
    HL_part #wall "HL_F2_Wall_002" #(#([2.3065,(-0.1425)],[2.1775,(-0.1425)],[2.1775,(-0.1355)],[(-2.1165),(-0.1355)],[(-2.1165),0.2855],[(-2.2595),0.2855],[(-2.2595),(-0.1355)],[(-2.3065),(-0.1355)],[(-2.3065),(-0.2855)],[2.3065,(-0.2855)])) 0.0000 2.9000 true 2 [(-0.3555),7.3565] [(-2.6620),7.0710] [1.9510,7.6420]
    HL_part #wall "HL_F2_Wall_003" #(#([0.4515,(-2.0210)],[0.3875,(-2.0210)],[0.3875,(-2.0140)],[(-0.2615),(-2.0140)],[(-0.2615),2.1640],[(-0.4515),2.1640],[(-0.4515),(-2.0930)],[(-0.4395),(-2.0930)],[(-0.4395),(-2.1640)],[0.4515,(-2.1640)])) 0.0000 2.9000 true 2 [(-4.9685),9.2350] [(-5.4200),7.0710] [(-4.5170),11.3990]
    HL_part #wall "HL_F2_Wall_004" #(#([(-2.0685),1.6350],[(-2.0685),1.4920],[(-0.4045),1.4920],[(-0.4045),1.3020],[(-0.2615),1.3020],[(-0.2615),1.4920],[1.9265,1.4920],[1.9265,0.1250],[1.6175,0.1250],[1.6175,0.0060],[1.8665,0.0060],[1.8665,(-1.5160)],[0.4635,(-1.5160)],[0.4635,0.0060],[0.6655,0.0060],[0.6655,0.1250],[0.3565,0.1250],[0.3565,0.0650],[0.3445,0.0650],[0.3445,(-1.6230)],[0.4045,(-1.6230)],[0.4045,(-1.6350)],[1.9265,(-1.6350)],[1.9265,(-1.6230)],[1.9855,(-1.6230)],[1.9855,0.0060],[1.9975,0.0060],[1.9975,0.0410],[2.0685,0.0410],[2.0685,1.5630],[1.9975,1.5630],[1.9975,1.6350])) 0.0000 2.9000 true 2 [(-2.2105),9.0270] [(-4.2790),7.3920] [(-0.1420),10.6620]
    HL_part #wall "HL_F2_Wall_005" #(#([0.0715,0.3095],[(-0.0715),0.3095],[(-0.0715),(-0.3095)],[0.0715,(-0.3095)])) 0.0000 2.9000 true 2 [(-2.5435),9.2825] [(-2.6150),8.9730] [(-2.4720),9.5920]
    HL_part #wall "HL_F2_Wall_006" #(#([4.0955,10.3100],[4.0955,10.5480],[3.9465,10.5480],[3.9465,10.3810],[3.8935,10.3120],[1.2785,10.3120],[1.2785,10.3580],[(-4.0835),10.3580],[(-4.0835),10.5480],[(-4.2005),10.5480],[(-4.2005),10.3580],[(-4.2385),10.3580],[(-4.2385),10.2150],[(-4.2005),10.2150],[(-4.2005),(-10.5480)],[(-4.0835),(-10.5480)],[(-4.0835),(-9.2710)],[(-3.3705),(-9.2710)],[(-3.3705),(-9.6640)],[(-3.1205),(-9.6640)],[(-3.1205),(-9.5490)],[(-2.5265),(-9.5490)],[(-2.5265),(-9.3590)],[(-3.3535),(-9.3590)],[(-3.3535),(-8.5700)],[(-4.0835),(-8.5700)],[(-4.0835),(-5.3950)],[(-3.3535),(-5.3950)],[(-3.3535),(-4.6960)],[(-4.0835),(-4.6960)],[(-4.0835),(-2.9340)],[(-3.3535),(-2.9340)],[(-3.3535),(-2.7540)],[(-4.0835),(-2.7540)],[(-4.0835),2.2250],[(-4.0625),2.2490],[(-4.0625),2.5010],[(-3.9435),2.5010],[(-3.9435),2.9390],[(-4.0625),3.0100],[(-4.0625),7.7540],[(-2.4785),7.7540],[(-2.4785),7.8130],[(-2.4545),7.8130],[(-2.4545),7.9560],[(-4.0835),7.9560],[(-4.0835),10.1630],[(-1.4685),10.1630],[(-1.4685),7.9560],[(-1.4915),7.9560],[(-1.4915),8.7640],[(-1.6225),8.7640],[(-1.6225),8.0060],[(-1.5275),8.0060],[(-1.5275),7.7630],[(-1.5805),7.7630],[(-1.5755),7.7540],[(-1.5185),7.7540],[(-1.5185),7.8130],[(-1.2545),7.8130],[(-1.2545),10.0960],[(-1.2185),10.1630],[1.0045,10.1630],[1.0045,10.0720],[1.1835,10.0720],[1.1835,10.1630],[3.9465,10.1630],[3.9465,6.2910],[3.9655,6.2200],[4.2025,6.2200],[4.2385,6.2440],[4.2385,9.6180],[4.1795,9.6180],[4.1795,9.6700],[4.0955,9.6700],[4.0955,10.1670],[4.2025,10.1670],[4.2025,10.3100])) 0.0000 2.9000 true 2 [(-11.5255),0.8510] [(-15.7640),(-9.6970)] [(-7.2870),11.3990]
    HL_part #wall "HL_F2_Wall_007" #(#([(-0.3185),(-0.9395)],[(-0.3185),(-0.9755)],[(-0.5355),(-0.9755)],[(-0.5355),(-1.1295)],[(-2.1165),(-1.1295)],[(-2.1165),(-1.4985)],[0.0475,(-1.4985)],[0.0475,(-1.5335)],[2.1165,(-1.5335)],[2.1165,1.5335],[1.9375,1.5335],[1.9375,(-1.4155)],[1.9025,(-1.4155)],[1.9025,(-1.4035)],[0.2375,(-1.4035)],[0.1825,(-1.3555)],[0.1825,(-1.0945)],[0.1185,(-1.0705)],[0.1825,(-1.0465)],[0.1825,(-0.9395)])) 0.0000 2.9000 true 2 [(-12.4585),8.6645] [(-14.5750),7.1310] [(-10.3420),10.1980]
    HL_part #wall "HL_F2_Wall_008_picture edge (the drawing stops here; assumed closed)" #(#([4.2325,(-0.0750)],[4.2325,0.0750],[(-4.2325),0.0750],[(-4.2325),(-0.0750)])) 0.0000 2.9000 true 2 [(-1.1875),11.4740] [(-5.4200),11.3990] [3.0450,11.5490]
    HL_part #parapet "HL_F2_Parapet_001_outside stair spine (low wall)" #(#([1.0580,(-0.2380)],[1.0580,0.2380],[(-1.0580),0.2380],[(-1.0580),(-0.2380)])) 0.0000 1.1000 false 2 [0.0370,(-7.8850)] [(-1.0210),(-8.1230)] [1.0950,(-7.6470)]
    HL_part #glass "HL_F2_Glass_001_F2-G1 glazing" #(#([3.9350,(-0.0250)],[3.9350,0.0250],[(-3.9350),0.0250],[(-3.9350),(-0.0250)])) 0.0000 2.9000 true 2 [(-10.1160),(-8.6560)] [(-14.0510),(-8.6810)] [(-6.1810),(-8.6310)]
    HL_part #glass "HL_F2_Glass_002_F2-G2 glazing" #(#([(-0.1305),0.0250],[(-0.1305),(-0.0250)],[0.1305,(-0.0250)],[0.1305,0.0250])) 0.0000 2.9000 true 2 [(-4.1485),(-8.6320)] [(-4.2790),(-8.6570)] [(-4.0180),(-8.6070)]
    HL_part #lintel "HL_F2_Lintel_001_F2-001" #(#([(-0.2025),(-0.4990)],[0.2025,(-0.4990)],[0.2025,0.4990],[(-0.2025),0.4990])) 2.1000 2.9000 true 2 [0.1295,(-2.4890)] [(-0.0730),(-2.9880)] [0.3320,(-1.9900)]
    HL_part #lintel "HL_F2_Lintel_002_F2-002" #(#([(-0.1725),(-0.4990)],[0.1725,(-0.4990)],[0.1725,0.4990],[(-0.1725),0.4990])) 2.1000 2.9000 true 2 [0.1815,(-4.8680)] [0.0090,(-5.3670)] [0.3540,(-4.3690)]
    HL_part #lintel "HL_F2_Lintel_003_F2-004" #(#([(-0.4625),0.0715],[(-0.4625),(-0.0715)],[0.4625,(-0.0715)],[0.4625,0.0715])) 2.1000 2.9000 true 2 [(-13.5165),8.7355] [(-13.9790),8.6640] [(-13.0540),8.8070]
    HL_part #lintel "HL_F2_Lintel_004_F2-005" #(#([(-0.0835),(-0.4865)],[0.0835,(-0.4865)],[0.0835,0.4865],[(-0.0835),0.4865])) 2.1000 2.9000 true 2 [(-12.9105),8.1765] [(-12.9940),7.6900] [(-12.8270),8.6630]
    HL_part #lintel "HL_F2_Lintel_005_F2-006" #(#([(-0.0895),(-0.3615)],[0.0895,(-0.3615)],[0.0895,0.3615],[(-0.0895),0.3615])) 2.1000 2.9000 true 2 [(-10.4315),10.5605] [(-10.5210),10.1990] [(-10.3420),10.9220]
    HL_part #lintel "HL_F2_Lintel_006_F2-007" #(#([(-1.0040),0.0950],[(-1.0040),(-0.0920)],[(-0.9210),(-0.0920)],[(-0.9200),(-0.0950)],[1.0040,(-0.0950)],[1.0040,0.0950])) 2.1000 2.9000 true 2 [(-6.4250),10.6140] [(-7.4290),10.5190] [(-5.4210),10.7090]
    HL_part #lintel "HL_F2_Lintel_007_F2-008" #(#([(-0.4745),0.0715],[(-0.4745),(-0.0715)],[0.4745,(-0.0715)],[0.4745,0.0715])) 2.1000 2.9000 true 2 [(-4.7545),10.5905] [(-5.2290),10.5190] [(-4.2800),10.6620]
    HL_part #lintel "HL_F2_Lintel_008_F2-009" #(#([(-0.0715),(-0.3675)],[0.0715,(-0.3675)],[0.0715,0.3675],[(-0.0715),0.3675])) 2.1000 2.9000 true 2 [(-2.5435),9.9605] [(-2.6150),9.5930] [(-2.4720),10.3280]
    HL_part #lintel "HL_F2_Lintel_009_F2-010" #(#([(-0.0715),(-0.6645)],[0.0715,(-0.6645)],[0.0715,0.6645],[(-0.0715),0.6645])) 2.1000 2.9000 true 2 [(-2.5435),8.3075] [(-2.6150),7.6430] [(-2.4720),8.9720]
    HL_part #lintel "HL_F2_Lintel_010_F2-011" #(#([(-0.4270),0.0715],[(-0.4270),(-0.0715)],[0.4270,(-0.0715)],[0.4270,0.0715])) 2.1000 2.9000 true 2 [2.3790,7.1425] [1.9520,7.0710] [2.8060,7.2140]
    HL_part #glass "HL_F2_Glass_003_F2-012 transom" #(#([(-0.9500),0.0140],[(-0.9500),(-0.0370)],[0.9500,(-0.0130)],[0.9500,0.0370])) 2.1000 2.9000 true 2 [(-5.2300),(-8.6440)] [(-6.1800),(-8.6810)] [(-4.2800),(-8.6070)]
    HL_part #lintel "HL_F2_Lintel_011_F2-013" #(#([(-0.6600),0.1120],[(-0.6600),(-0.1260)],[0.6600,(-0.1170)],[0.6600,0.1260])) 2.1000 2.9000 true 2 [(-2.4290),(-6.1540)] [(-3.0890),(-6.2800)] [(-1.7690),(-6.0280)]
    HL_part #sill "HL_F2_Sill_001_F2-014 below the hatch" #(#([0.9275,0.0750],[0.9225,0.0750],[0.9225,0.0680],[(-0.9275),0.0680],[(-0.9275),(-0.0750)],[0.9275,(-0.0750)])) 0.0000 0.8500 false 2 [(-3.5895),7.1460] [(-4.5170),7.0710] [(-2.6620),7.2210]
    HL_part #lintel "HL_F2_Lintel_012_F2-014 above the hatch" #(#([0.9275,0.0750],[0.9225,0.0750],[0.9225,0.0680],[(-0.9275),0.0680],[(-0.9275),(-0.0750)],[0.9275,(-0.0750)])) 2.1000 2.9000 true 2 [(-3.5895),7.1460] [(-4.5170),7.0710] [(-2.6620),7.2210]
    HL_part #sill "HL_F2_Sill_002_F2-016 below the hatch" #(#([(-0.4760),0.0595],[(-0.4760),(-0.0595)],[0.4760,(-0.0595)],[0.4760,0.0595])) 0.0000 0.9000 false 2 [(-1.0690),9.0925] [(-1.5450),9.0330] [(-0.5930),9.1520]
    HL_part #lintel "HL_F2_Lintel_013_F2-016 above the hatch" #(#([(-0.4760),0.0595],[(-0.4760),(-0.0595)],[0.4760,(-0.0595)],[0.4760,0.0595])) 2.1000 2.9000 true 2 [(-1.0690),9.0925] [(-1.5450),9.0330] [(-0.5930),9.1520]
    HL_part #railing "HL_F2_Railing_001_railing at the open stair, west" #(#([0.0250,2.1890],[(-0.0250),2.1890],[(-0.0250),(-2.1890)],[0.0250,(-2.1890)])) 0.0000 1.1000 false 2 [(-10.2630),0.6500] [(-10.2880),(-1.5390)] [(-10.2380),2.8390]
    HL_part #railing "HL_F2_Railing_002_railing at the open stair, east" #(#([0.0250,2.1890],[(-0.0250),2.1890],[(-0.0250),(-2.1890)],[0.0250,(-2.1890)])) 0.0000 1.1000 false 2 [(-7.7130),0.6500] [(-7.7380),(-1.5390)] [(-7.6880),2.8390]
    HL_part #railing "HL_F2_Railing_003_railing at the open stair, south" #(#([1.3000,0.0250],[(-1.3000),0.0250],[(-1.3000),(-0.0250)],[1.3000,(-0.0250)])) 0.0000 1.1000 false 2 [(-8.9880),(-1.5140)] [(-10.2880),(-1.5390)] [(-7.6880),(-1.4890)]
    HL_part #railing "HL_F2_Railing_004_railing at the terrace edge" #(#([0.0250,0.8865],[(-0.0250),0.8865],[(-0.0250),(-0.8865)],[0.0250,(-0.8865)])) 0.0000 1.1000 false 2 [(-15.7010),(-10.5835)] [(-15.7260),(-11.4700)] [(-15.6760),(-9.6970)]
    HL_part #railing "HL_F2_Railing_005_railing at the terrace edge" #(#([10.1785,(-0.0250)],[10.1785,0.0250],[(-10.1785),0.0250],[(-10.1785),(-0.0250)])) 0.0000 1.1000 false 2 [(-5.5475),(-11.4450)] [(-15.7260),(-11.4700)] [4.6310,(-11.4200)]
    HL_part #railing "HL_F2_Railing_006_railing at the terrace edge" #(#([0.0250,(-0.8770)],[0.0250,0.8770],[(-0.0250),0.8770],[(-0.0250),(-0.8770)])) 0.0000 1.1000 false 2 [4.6060,(-10.5930)] [4.5810,(-11.4700)] [4.6310,(-9.7160)]
    HL_part #railing "HL_F2_Railing_007_railing at the terrace edge" #(#([(-0.8205),0.0250],[(-0.8205),(-0.0250)],[0.8205,(-0.0250)],[0.8205,0.0250])) 0.0000 1.1000 false 2 [3.8105,(-9.7410)] [2.9900,(-9.7660)] [4.6310,(-9.7160)]
    HL_part #step "HL_F2_Step_001_F2-S1 step 1 up (to a floor 3, not drawn)" #(#([1.3815,0.1545],[(-1.3815),0.1545],[(-1.3815),(-0.1545)],[1.3815,(-0.1545)])) 0.0000 0.1710 false 2 [(-8.9605),7.3685] [(-10.3420),7.2140] [(-7.5790),7.5230]
    HL_part #step "HL_F2_Step_002_F2-S1 step 2 up (to a floor 3, not drawn)" #(#([1.3815,0.1665],[(-1.3815),0.1665],[(-1.3815),(-0.1665)],[1.3815,(-0.1665)])) 0.0000 0.3410 false 2 [(-8.9605),7.6895] [(-10.3420),7.5230] [(-7.5790),7.8560]
    HL_part #step "HL_F2_Step_003_F2-S1 step 3 up (to a floor 3, not drawn)" #(#([1.3815,0.1545],[(-1.3815),0.1545],[(-1.3815),(-0.1545)],[1.3815,(-0.1545)])) 0.1710 0.5120 false 2 [(-8.9605),8.0105] [(-10.3420),7.8560] [(-7.5790),8.1650]
    HL_part #step "HL_F2_Step_004_F2-S1 step 4 up (to a floor 3, not drawn)" #(#([1.3815,0.1665],[(-1.3815),0.1665],[(-1.3815),(-0.1665)],[1.3815,(-0.1665)])) 0.3410 0.6820 false 2 [(-8.9605),8.3315] [(-10.3420),8.1650] [(-7.5790),8.4980]
    HL_part #step "HL_F2_Step_005_F2-S1 step 5 up (to a floor 3, not drawn)" #(#([1.3815,0.1665],[(-1.3815),0.1665],[(-1.3815),(-0.1665)],[1.3815,(-0.1665)])) 0.5120 0.8530 false 2 [(-8.9605),8.6645] [(-10.3420),8.4980] [(-7.5790),8.8310]
    HL_part #step "HL_F2_Step_006_F2-S1 step 6 up (to a floor 3, not drawn)" #(#([1.3815,0.1545],[(-1.3815),0.1545],[(-1.3815),(-0.1545)],[1.3815,(-0.1545)])) 0.6820 1.0240 false 2 [(-8.9605),8.9855] [(-10.3420),8.8310] [(-7.5790),9.1400]
    HL_part #step "HL_F2_Step_007_F2-S1 step 7 up (to a floor 3, not drawn)" #(#([1.3815,0.1665],[(-1.3815),0.1665],[(-1.3815),(-0.1665)],[1.3815,(-0.1665)])) 0.8530 1.1940 false 2 [(-8.9605),9.3065] [(-10.3420),9.1400] [(-7.5790),9.4730]
    HL_part #slab "HL_F2_Slab_001" #(#([10.2340,(-11.5395)],[10.2340,(-9.7255)],[8.6580,(-9.7255)],[8.6580,(-9.6445)],[8.5930,(-9.6445)],[8.5930,7.9765],[8.6480,7.9765],[8.6480,11.5395],[0.1230,11.5395],[0.1230,10.7195],[(-1.8270),10.7195],[(-1.8270),10.9485],[(-1.7200),10.9485],[(-1.7200),11.1515],[(-1.8270),11.1515],[(-1.8270),11.3895],[(-2.0360),11.3895],[(-2.0360),11.2025],[(-2.0740),11.1535],[(-4.6440),11.1535],[(-4.6440),11.1995],[(-10.0060),11.1995],[(-10.0060),11.3895],[(-10.1830),11.3895],[(-10.1830),11.1995],[(-10.2210),11.1995],[(-10.2210),10.9965],[(-10.1830),10.9965],[(-10.1830),(-9.7065)],[(-10.2340),(-9.7325)],[(-10.2310),(-11.1275)],[(-10.1830),(-11.1275)],[(-10.1830),(-11.5395)]),#([5.6210,(-1.0535)],[5.6210,(-0.2205)],[8.2140,(-0.2195)],[8.2130,(-1.0535)]),#([8.1430,(-6.0705)],[5.9060,(-6.0705)],[5.9060,(-3.8345)],[8.1430,(-3.8345)]),#([8.1430,(-3.5505)],[5.9060,(-3.5505)],[5.9060,(-1.3375)],[8.1430,(-1.3385)]),#([5.6460,(-6.1655)],[5.0980,(-6.1655)],[5.0980,(-5.7365)],[5.6460,(-5.7375)]),#([(-2.1640),2.7995],[(-2.1640),(-1.5295)],[(-4.6650),(-1.5285)],[(-4.6650),2.8005])) (-0.2000) 0.0000 false 2 [(-5.5730),0.0395] [(-15.8070),(-11.5000)] [4.6610,11.5790]
    HL_lines "HL_F2_Stairs" #(#([(-0.8085),1.5925],[(-0.8085),0.3335]),#([(-0.8085),(-0.1445)],[(-0.8085),(-1.5925)]),#([(-0.5225),1.5925],[(-0.5225),0.3335]),#([(-0.5225),(-0.1445)],[(-0.5225),(-1.5925)]),#([(-0.2615),1.5925],[(-0.2615),0.3335]),#([(-0.2615),(-0.1445)],[(-0.2615),(-1.5925)]),#([0.0005,1.5925],[0.0005,0.3335]),#([0.0005,(-0.1445)],[0.0005,(-1.5925)]),#([0.2855,1.5925],[0.2855,0.3335]),#([0.2855,(-0.1445)],[0.2855,(-1.5925)]),#([0.5475,1.5925],[0.5475,0.3335]),#([0.5475,(-0.1445)],[0.5475,(-1.5925)]),#([0.8085,1.5925],[0.8085,0.3335]),#([0.8085,(-0.1445)],[0.8085,(-1.5925)])) 2 [(-0.0945),(-7.9795)] "Stairs"
    HL_room "Lounge area" [(-11.5720),(-2.3790)] 1
    HL_room "Coffee" [(-12.4320),(-4.7500)] 1
    HL_room "Art work" [(-14.2040),(-5.3470)] 1
    HL_room "Check-in / self check-in" [(-5.0430),0.5890] 1
    HL_room "Car park" [(-2.5460),2.4330] 1
    HL_room "Lift lobby" [(-1.8040),(-3.6790)] 1
    HL_room "Red box" [(-7.9450),(-6.4540)] 1
    HL_room "Entrance" [(-7.7250),(-8.7550)] 1
    HL_room "Luggage storage" [(-8.9910),2.3100] 1
    HL_room "Additional space for luggage" [1.6210,0.5190] 1
    HL_room "Male" [(-14.4320),9.8530] 2
    HL_room "Female" [(-11.6260),9.5920] 2
    HL_room "Iconic staircase" [(-8.7260),5.8820] 2
    HL_room "Door with key access" [(-6.4900),9.4960] 2
    HL_room "Pantry" [(-4.0170),9.3060] 2
    HL_room "Food lift" [(-1.1640),9.6150] 2
    HL_room "Canteen M." [(-1.8300),5.9300] 2
    HL_room "Mural wall" [(-14.9790),5.5490] 2
    HL_room "Signature cabinets" [(-13.9800),2.6720] 2
    HL_room "Feature carpet" [(-0.4270),2.7910] 2
    HL_room "Bar" [(-9.9140),(-6.1260)] 2
    HL_room "Entry" [(-5.2300),(-9.3590)] 2
    HL_room "Outdoor" [(-9.2720),(-9.8350)] 2
    HL_room "Outside stair" [(-0.1180),(-10.3820)] 2
    if HL_furnWant do HL_furnRun()
    local origin = point name:"HL_ORIGIN_DWG" size:1.0 pos:[0.0 - HL_shift.x, 0.0 - HL_shift.y, 0.0]
    origin.isHidden = true
    origin.ignoreExtents = true
    (HL_layer "HL_Datums").addNode origin
    setUserProp origin "Source" "source/floor1_plan.png + source/floor2_plan.png: two presentation pictures, no CAD, scaled from the main stair's width, 2.50 m between its side walls (the owner's), per axis where a picture is drawn wider than tall; model in metres, 0,0 is the lift core's north-west corner on both floors, y up"
    setUserProp origin "Levels" ("floor levels " + (HL_levels as string) + " m, wall heights " + (HL_heights as string) + " m")
    setUserProp origin "Picture_F1" "source/floor1_plan.png (1498 x 945 px at 59.2760 px per m along x and 56.9378 along y) is a plane 25.2716 m along x by 16.5971 m along y, its centre [-5.3129, -3.7404] m from this point, under Floor 1"
    setUserProp origin "Picture_F2" "source/floor2_plan.png (882 x 945 px at 42.0557 px per m along x and 42.0557 along y) is a plane 20.9722 m along x by 22.4702 m along y, its centre [-6.3953, 0.1636] m from this point, under Floor 2"
    viewport.setType #view_iso_user
    select HL_nodes
    max zoomext sel all
    clearSelection()
    redrawViews()
    format "HL BUILD COMPLETE: % objects in % s, % failed checks\n" HL_nodes.count ((timeStamp() - t0) / 1000.0) HL_failed.count
    for f in HL_failed do format "  check failed: %\n" f
    true
)
try (destroyDialog HL_UI) catch ()
rollout HL_UI "Hotel (test)" width:340
(
    label info "Open a new empty scene before Build." align:#left
    label units1 "Build sets System Units to metres." align:#left
    checkbox dwg "At the drawing's own coordinates" checked:true tooltip:"Metres from the lift core's north-west corner, the frame the pictures were scaled in. Untick to centre the model on the origin"
    spinner lv1 "Floor 1 floor level (m):" range:[-50, 500, 0.00] type:#float fieldwidth:60
    spinner ht1 "Floor 1 wall height (m):" range:[2.2, 15, 2.90] type:#float fieldwidth:60
    spinner lv2 "Floor 2 floor level (m):" range:[-50, 500, 2.90] type:#float fieldwidth:60
    spinner ht2 "Floor 2 wall height (m):" range:[2.2, 15, 2.90] type:#float fieldwidth:60
    group "Furniture boxes (heights in mm)"
    (
        checkbox fb "Build furniture boxes" checked:true
        checkbox fo "Furniture boxes only" checked:false tooltip:"Add only the boxes to the scene already built from this model: no structure, and the empty-scene check is skipped"
        label fol "(add to the scene already built from this model)" align:#left
        spinner fh1 "Plant:" across:2 range:[10, 5000, 600] type:#integer fieldwidth:40
        spinner fh2 "Chair / stool:" range:[10, 5000, 450] type:#integer fieldwidth:40
        spinner fh3 "Sofa / armchair:" across:2 range:[10, 5000, 800] type:#integer fieldwidth:40
        spinner fh4 "Seat back:" range:[10, 5000, 800] type:#integer fieldwidth:40
        spinner fh5 "Table / desk:" across:2 range:[10, 5000, 750] type:#integer fieldwidth:40
        spinner fh6 "Coffee table:" range:[10, 5000, 450] type:#integer fieldwidth:40
        spinner fh7 "Counter top:" across:2 range:[10, 5000, 850] type:#integer fieldwidth:40
        spinner fh8 "Cabinet:" range:[10, 5000, 900] type:#integer fieldwidth:40
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
        HL_levels = #(lv1.value,lv2.value)
        HL_heights = #(ht1.value,ht2.value)
        HL_collapse = cm.checked
        HL_shift = if dwg.checked then [0.0, 0.0] else [-5.5730, 0.0390]
        HL_furnHeights = #((fh1.value / 1000.0),(fh2.value / 1000.0),(fh3.value / 1000.0),(fh4.value / 1000.0),(fh5.value / 1000.0),(fh6.value / 1000.0),(fh7.value / 1000.0),(fh8.value / 1000.0))
        HL_furnWant = fb.checked
        HL_furnAddOnly = fo.checked
        try
        (
            if HL_build() do
            (
                if HL_failed.count == 0 then messageBox ("Built " + (HL_nodes.count as string) + " objects. Every part passed the closed-solid, height and position checks. Save As to keep your .max file.") title:"Hotel"
                else messageBox ((HL_failed.count as string) + " part(s) failed a check and are on layer HL_Check_Failed (listed in the MAXScript Listener). Everything else was built.") title:"Hotel"
            )
        )
        catch (messageBox (getCurrentException()) title:"Build stopped")
    )
    on upd pressed do
    (
        local r = HL_updateLevels #(lv1.value,lv2.value) #(ht1.value,ht2.value)
        messageBox ("Every part moved to its level; " + (r[1] as string) + " parts set to their level's wall height." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were collapsed already and kept their height.") else "")) title:"Hotel"
    )
    on col pressed do
    (
        local n = HL_collapseAll()
        messageBox ((n as string) + " parts collapsed to Editable Mesh.") title:"Hotel"
    )
    on fap pressed do
    (
        HL_furnHeights = #((fh1.value / 1000.0),(fh2.value / 1000.0),(fh3.value / 1000.0),(fh4.value / 1000.0),(fh5.value / 1000.0),(fh6.value / 1000.0),(fh7.value / 1000.0),(fh8.value / 1000.0))
        local r = HL_furnApply()
        messageBox ((r[1] as string) + " furniture boxes set to the heights in the window and stood on their floor or support." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were left alone (not a Box any more, or a kind this script does not know).") else "")) title:"Hotel"
    )
)
createDialog HL_UI
