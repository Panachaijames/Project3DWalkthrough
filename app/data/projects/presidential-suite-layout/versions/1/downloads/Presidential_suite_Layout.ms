-- PRESIDENTIAL_SUITE_LAYOUT / built by the walkthrough app from "presidential suite_layout.dwg", 11 Nov 2026
-- Same model as the version in the walkthrough app (model data 9041e84fa2bb). Floor levels +0.00 m, wall heights 3.00 m.
-- The drawings were converted with LibreDWG 0.14; drawing units mm.
-- Placed at the drawing's own coordinates in metres (to line up with the drawings imported in metres), or centred on
-- the origin if you untick that box in the script's window.
-- Every part stays LIVE (no Editable Poly): an editable spline outline + an Extrude modifier (output: Mesh) + Smooth.
--   * Change a height: the Extrude amount on that object, or "Update levels and heights" in this script's window.
--   * Change an outline: select the spline level under the modifiers and move vertices.
--   * Editable Mesh: tick "Collapse to Editable Mesh" before Build, or press "Collapse all now" later.
-- Each object's pivot is at the middle of its own outline, on its base. Layers per level and kind (PSL_L1_Walls ...).
-- "Update levels and heights" sets the tops of the walls, glass and lintels to their level's wall height and keeps
-- the slabs at their own heights (only parts marked to follow the wall height change).
-- Each part is checked as it is built (closed solid, height, position). A part that fails is kept on layer
-- PSL_Check_Failed and listed in the MAXScript Listener; the rest is still built.
-- Build sets System Units to metres. Nothing in an existing scene is changed: run it in a NEW EMPTY scene.
global PSL_UI
global PSL_nodes = #()
global PSL_failed = #()
global PSL_levels = #(0.00)
global PSL_heights = #(3.00)
global PSL_floorNames = #("L1")
global PSL_collapse = false
global PSL_shift = [0.0, 0.0]
global PSL_mats
-- Furniture boxes: one coloured placeholder box per furniture piece (colour = kind), on layers PSL_<level>_Furn_<Kind>. Type
-- each kind's height in mm in the window, before the build or later with "Apply furniture heights" (boxes on a table, counter or
-- cabinet follow its height). A box is a live Box, never an Editable Poly, and carries the piece's family, block and DWG layer
-- as user properties, so the 3D team can swap it for their own model by family name. A property with nothing to say (no support,
-- no block, no handle) holds the word none, never empty text: 3ds Max does not say what getUserProp returns for empty text.
-- Each box is checked as it is built: base z, top z and its four corners carried through its transform, and the node's min and
-- max in the plan only for an unrotated box (Autodesk does not say what they are for a turned node). A box that fails goes on
-- layer PSL_Check_Failed and is listed in the Listener; the rest is still built.
-- "Furniture boxes only" adds just the boxes to a scene already built from this model. Below: the kinds in the model's order,
-- heights and bases in metres.
global PSL_furnWant = true
global PSL_furnAddOnly = false
global PSL_furnFloors = #("L1")
global PSL_furnKeys = #("tv","curtain","lamp","sanitary","appliance","seat","table","cabinet")
global PSL_furnLayers = #("Tv","Curtain","Lamp","Sanitary","Appliance","Seat","Table","Cabinet")
global PSL_furnBases = #(0.9000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000)
global PSL_furnHeights = #(0.6000,2.4000,0.5000,0.8500,0.9000,0.4500,0.7500,0.9000)
global PSL_furnLevels = #()
global PSL_furnMats = #()

fn PSL_layer n =
(
    local ly = LayerManager.getLayerFromName n
    if ly == undefined do ly = LayerManager.newLayerFromName n
    ly
)
fn PSL_mat key =
(
    local m = undefined
    for x in PSL_mats where x.name == ("PSL " + key) do m = x
    m
)
fn PSL_makeMaterials =
(
    PSL_mats = #()
    append PSL_mats (standardMaterial name:"PSL Wall" diffuse:(color 227 221 211))
    append PSL_mats (standardMaterial name:"PSL Glass" diffuse:(color 170 200 214) opacity:30 specularLevel:60 glossiness:60)
    append PSL_mats (standardMaterial name:"PSL Rail" diffuse:(color 119 114 124))
    append PSL_mats (standardMaterial name:"PSL Single" diffuse:(color 224 164 88))
    append PSL_mats (standardMaterial name:"PSL Slab" diffuse:(color 212 216 210))
    append PSL_mats (standardMaterial name:"PSL Frame" diffuse:(color 93 107 116))
    append PSL_mats (standardMaterial name:"PSL Step" diffuse:(color 185 199 180))
)
fn PSL_num v = ((v as string) as float)
-- The outline's knots are relative to c, the middle of the outline; the node is then moved to c, so that is its pivot.
fn PSL_shape nm loops =
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
fn PSL_extrudeOf o =
(
    local ex = undefined
    for md in o.modifiers where classOf md == Extrude do ex = md
    ex
)
-- kind: #wall #column #lintel #sill #parapet #glass #mullion #railing #single #step #slab; z0/z1 in metres above the
-- level of floor fi (a step of a flight going down from a level starts below it);
-- follow = the top follows that level's wall height. c = pivot, mn/mx = outline extents (DWG coordinates).
fn PSL_part kind nm loops z0 z1 follow fi c mn mx =
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
    local lvl = PSL_levels[fi]
    local top = if follow then PSL_heights[fi] else z1
    local zb = lvl + z0
    local ht = top - z0
    local o = PSL_shape nm loops
    o.pos = [c.x - PSL_shift.x, c.y - PSL_shift.y, zb]
    addModifier o (Extrude amount:ht segs:1 capStart:true capEnd:true output:1 smooth:false)
    addModifier o (Smooth autoSmooth:true threshold:25.0)
    local mt = PSL_mat info[2]
    o.material = mt
    o.wirecolor = mt.diffuse
    setUserProp o "PSL_kind" (kind as string)
    setUserProp o "PSL_floor" fi
    setUserProp o "PSL_base" z0
    setUserProp o "PSL_follow" follow
    -- the checks run on the evaluated mesh (what the modifiers produce)
    local m = snapshotAsMesh o
    local why = ""
    local tol = 0.002
    if m.numfaces < 3 then why = "no faces"
    else if (meshop.getOpenEdges m).numberSet != 0 then why = "open edges (not a closed solid)"
    else if abs(o.min.z - zb) > tol or abs(o.max.z - (zb + ht)) > tol then why = "height"
    else if abs(o.min.x - (mn.x - PSL_shift.x)) > tol or abs(o.min.y - (mn.y - PSL_shift.y)) > tol or abs(o.max.x - (mx.x - PSL_shift.x)) > tol or abs(o.max.y - (mx.y - PSL_shift.y)) > tol then why = "position"
    m = undefined
    if why == "" then
    (
        (PSL_layer ("PSL_" + PSL_floorNames[fi] + "_" + info[1])).addNode o
        setUserProp o "PSL_check" "ok"
    )
    else
    (
        (PSL_layer "PSL_Check_Failed").addNode o
        setUserProp o "PSL_check" why
        append PSL_failed (nm + ": " + why)
    )
    if PSL_collapse do convertToMesh o
    append PSL_nodes o
    o
)
-- Stair lines: one shape of open two-knot splines per level and kind, knots relative to c (its pivot).
fn PSL_lines nm segs fi c lay =
(
    local o = splineShape name:nm
    for k = 1 to segs.count do
    (
        addNewSpline o
        addKnot o k #corner #line [segs[k][1].x, segs[k][1].y, 0]
        addKnot o k #corner #line [segs[k][2].x, segs[k][2].y, 0]
    )
    updateShape o
    o.pos = [c.x - PSL_shift.x, c.y - PSL_shift.y, PSL_levels[fi]]
    o.wirecolor = if lay == "Stairs" then (color 46 139 71) else (color 160 210 170)
    setUserProp o "PSL_floor" fi
    setUserProp o "PSL_base" 0.0
    (PSL_layer ("PSL_" + PSL_floorNames[fi] + "_" + lay)).addNode o
    append PSL_nodes o
    o
)
fn PSL_room nm p fi =
(
    local t = text text:nm size:0.3 pos:[p.x - PSL_shift.x, p.y - PSL_shift.y, PSL_levels[fi] + 0.02]
    t.name = "PSL_Room_" + PSL_floorNames[fi] + "_" + nm
    t.wirecolor = color 30 60 110
    setUserProp t "PSL_floor" fi
    setUserProp t "PSL_base" 0.02
    (PSL_layer ("PSL_" + PSL_floorNames[fi] + "_RoomNames")).addNode t
    append PSL_nodes t
    t
)
-- After the build: move every part to its level and set every live part whose top follows the wall height to its
-- level's new wall height.
fn PSL_updateLevels newLevels newHeights =
(
    local n = 0
    local skipped = 0
    for o in objects where (getUserProp o "PSL_floor") != undefined do
    (
        local fi = (PSL_num (getUserProp o "PSL_floor")) as integer
        local base = PSL_num (getUserProp o "PSL_base")
        o.pos.z = newLevels[fi] + base
        if ((getUserProp o "PSL_follow") as string) == "true" do
        (
            local ex = PSL_extrudeOf o
            if ex == undefined then skipped += 1
            else ( ex.amount = newHeights[fi] - base; n += 1 )
        )
    )
    PSL_levels = newLevels
    PSL_heights = newHeights
    #(n, skipped)
)
fn PSL_collapseAll =
(
    local n = 0
    for o in objects where (getUserProp o "PSL_kind") != undefined and o.modifiers.count > 0 do ( convertToMesh o; n += 1 )
    n
)
-- Furniture boxes: one coloured Box per piece, a placeholder the 3D team swaps for their own model by family name.
-- A box is a live Box (width along its own long axis, length across it, height), never an Editable Poly or Mesh and never
-- collapsed: "Collapse all now" only takes objects that carry PSL_kind and a modifier, and a box has neither. Every box
-- carries PSL_floor and PSL_base (its bottom, in metres above its level) and PSL_follow = false, so "Update levels
-- and heights" moves it with its level and leaves its height alone.
fn PSL_furnNum v = ((v as string) as float)
fn PSL_furnMakeMaterials =
(
    PSL_furnMats = #()
    append PSL_furnMats (standardMaterial name:"PSL Furn tv" diffuse:(color 52 64 143))
    append PSL_furnMats (standardMaterial name:"PSL Furn curtain" diffuse:(color 201 160 220))
    append PSL_furnMats (standardMaterial name:"PSL Furn lamp" diffuse:(color 255 210 63))
    append PSL_furnMats (standardMaterial name:"PSL Furn sanitary" diffuse:(color 23 162 162))
    append PSL_furnMats (standardMaterial name:"PSL Furn appliance" diffuse:(color 184 134 11))
    append PSL_furnMats (standardMaterial name:"PSL Furn seat" diffuse:(color 224 123 0))
    append PSL_furnMats (standardMaterial name:"PSL Furn table" diffuse:(color 138 90 43))
    append PSL_furnMats (standardMaterial name:"PSL Furn cabinet" diffuse:(color 47 127 193))
)
-- The floor levels the build was started with (a copy: nothing is shared with the script's own array).
fn PSL_furnSetLevels =
(
    PSL_furnLevels = #()
    for z in (PSL_levels) do append PSL_furnLevels z
)
-- Where a box stands, in metres above its level: on its kind's base, or on top of the kind of support it was drawn on
-- (ki = its kind, oki = the kind of its support, 0 for none). A support never stands on anything.
fn PSL_furnZ0 ki oki =
(
    local z0 = PSL_furnBases[ki]
    if oki > 0 do z0 = PSL_furnBases[oki] + PSL_furnHeights[oki]
    z0
)
-- kind = the kind, nm = the object's name, fi = the floor's index, pid = the piece's id, supId and supKind = its support's id
-- and kind ("none" for none), c = the box's centre and cs = its four corners (DWG coordinates), w d = its size along its own
-- long and short axis, ca sa = cos and sin of the angle from +x to the long axis, fam blk lay hnd = family, block, DWG layer,
-- handle ("none" for nothing). The box gets an explicit matrix: its X, Y and Z axes in the world, then its pivot (the middle of
-- its base).
fn PSL_furnBox kind nm fi pid supId supKind c w d ca sa cs fam blk lay hnd =
(
    local ki = findItem PSL_furnKeys kind
    local z0 = PSL_furnZ0 ki (findItem PSL_furnKeys supKind)
    local ht = PSL_furnHeights[ki]
    local zb = PSL_furnLevels[fi] + z0
    local o = box name:nm width:w length:d height:ht
    o.transform = (matrix3 [ca, sa, 0.0] [(0.0 - sa), ca, 0.0] [0.0, 0.0, 1.0] [c.x - PSL_shift.x, c.y - PSL_shift.y, zb])
    local mt = PSL_furnMats[ki]
    o.material = mt
    o.wirecolor = mt.diffuse
    setUserProp o "PSL_furn" "true"
    setUserProp o "PSL_furnKind" kind
    setUserProp o "PSL_furnId" pid
    setUserProp o "PSL_furnOn" supId
    setUserProp o "PSL_furnOnKind" supKind
    setUserProp o "PSL_family" fam
    setUserProp o "PSL_block" blk
    setUserProp o "PSL_layer" lay
    setUserProp o "PSL_handle" hnd
    setUserProp o "PSL_floor" fi
    setUserProp o "PSL_base" z0
    setUserProp o "PSL_follow" false
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
    else if unrotated and (abs(o.min.x - (mnx - PSL_shift.x)) > tol or abs(o.min.y - (mny - PSL_shift.y)) > tol or abs(o.max.x - (mxx - PSL_shift.x)) > tol or abs(o.max.y - (mxy - PSL_shift.y)) > tol) then why = "bounding box"
    else
    (
        local hw = o.width / 2.0
        local hd = o.length / 2.0
        local lc = #([(0.0 - hw), (0.0 - hd), 0.0], [hw, (0.0 - hd), 0.0], [hw, hd, 0.0], [(0.0 - hw), hd, 0.0])
        for k = 1 to 4 do
        (
            local q = lc[k] * o.transform
            if why == "" and (abs(q.x - (cs[k].x - PSL_shift.x)) > tol or abs(q.y - (cs[k].y - PSL_shift.y)) > tol) then why = "corner " + (k as string)
        )
    )
    if why == "" then
    (
        (PSL_layer ("PSL_" + PSL_furnFloors[fi] + "_Furn_" + PSL_furnLayers[ki])).addNode o
        setUserProp o "PSL_check" "ok"
    )
    else
    (
        (PSL_layer "PSL_Check_Failed").addNode o
        setUserProp o "PSL_check" why
        append PSL_failed (nm + ": " + why)
    )
    append PSL_nodes o
    o
)
-- Every piece of the model, in the model's order.
fn PSL_furnAll =
(
    PSL_furnBox "tv" "PSL_L1_Furn_tv_001_APPLIANCE_TV - 70" 1 "L1-tv-001" "none" "none" [2.5300,5.8590] 1.5500 0.2800 0.000000000 1.000000000 #([2.6700,5.0840],[2.6700,6.6340],[2.3900,6.6340],[2.3900,5.0840]) "APPLIANCE_TV - 70_" "APPLIANCE_TV - 70_-12504961-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4EE2"
    PSL_furnBox "tv" "PSL_L1_Furn_tv_002_APPLIANCE_TV_WALL MOUNT WITH BRACKET - 6" 1 "L1-tv-002" "none" "none" [11.7870,8.4090] 1.4500 0.0500 0.000000000 1.000000000 #([11.8120,7.6840],[11.8120,9.1340],[11.7620,9.1340],[11.7620,7.6840]) "APPLIANCE_TV_WALL MOUNT WITH BRACKET - 65_" "APPLIANCE_TV_WALL MOUNT WITH BRACKET - 65_-11362946-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4F34"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_001_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-001" "none" "none" [2.5450,3.2950] 0.6160 0.0680 (-0.712883356) 0.701282625 #([2.7884,3.1032],[2.3493,3.5352],[2.3016,3.4868],[2.7407,3.0548]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11356429-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4ED2"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_002_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-002" "none" "none" [2.5450,8.4230] 0.6160 0.0680 0.712883356 0.701282625 #([2.3493,8.1828],[2.7884,8.6148],[2.7407,8.6632],[2.3016,8.2312]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11357310-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4ED4"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_003_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-003" "none" "none" [2.6170,3.3670] 0.6160 0.0680 (-0.712883356) 0.701282625 #([2.8604,3.1752],[2.4213,3.6072],[2.3736,3.5588],[2.8127,3.1268]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11356429-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4ED3"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_004_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-004" "none" "none" [2.6170,8.3510] 0.6160 0.0680 0.712883356 0.701282625 #([2.4213,8.1108],[2.8604,8.5428],[2.8127,8.5912],[2.3736,8.1592]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11357310-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4ED5"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_005_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-005" "none" "none" [4.0740,11.9000] 0.6160 0.0680 0.250717936 0.968060182 #([4.0297,11.5933],[4.1841,12.1896],[4.1183,12.2067],[3.9639,11.6104]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11356429-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4ED6"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_006_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-006" "none" "none" [4.1710,11.8750] 0.6160 0.0680 0.250717936 0.968060182 #([4.1267,11.5683],[4.2811,12.1646],[4.2153,12.1817],[4.0609,11.5854]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11356429-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4ED7"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_007_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-007" "none" "none" [5.6350,12.7200] 0.6160 0.0680 (-0.963770247) 0.266733784 #([5.9409,12.6706],[5.3472,12.8349],[5.3291,12.7694],[5.9228,12.6051]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11357310-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E1C"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_008_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-008" "none" "none" [5.6610,12.8170] 0.6160 0.0680 (-0.963770247) 0.266733784 #([5.9669,12.7676],[5.3732,12.9319],[5.3551,12.8664],[5.9488,12.7021]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11357310-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E1B"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_009_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-009" "none" "none" [8.4490,11.9000] 0.6160 0.0680 0.250717936 0.968060182 #([8.4047,11.5933],[8.5591,12.1896],[8.4933,12.2067],[8.3389,11.6104]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11356429-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E17"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_010_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-010" "none" "none" [8.5460,11.8750] 0.6160 0.0680 0.250717936 0.968060182 #([8.5017,11.5683],[8.6561,12.1646],[8.5903,12.1817],[8.4359,11.5854]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11356429-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E19"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_011_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-011" "none" "none" [10.0100,12.7200] 0.6160 0.0680 (-0.963770247) 0.266733784 #([10.3159,12.6706],[9.7222,12.8349],[9.7041,12.7694],[10.2978,12.6051]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11357310-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E1A"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_012_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-012" "none" "none" [10.0360,12.8170] 0.6160 0.0680 (-0.963770247) 0.266733784 #([10.3419,12.7676],[9.7482,12.9319],[9.7301,12.8664],[10.3238,12.7021]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11357310-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E18"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_013_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-013" "none" "none" [12.8240,11.9000] 0.6160 0.0680 0.250717936 0.968060182 #([12.7797,11.5933],[12.9341,12.1896],[12.8683,12.2067],[12.7139,11.6104]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11356429-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E13"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_014_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-014" "none" "none" [12.9210,11.8750] 0.6160 0.0680 0.250717936 0.968060182 #([12.8767,11.5683],[13.0311,12.1646],[12.9653,12.1817],[12.8109,11.5854]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11356429-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E15"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_015_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-015" "none" "none" [14.3850,12.7200] 0.6160 0.0680 (-0.963770247) 0.266733784 #([14.6909,12.6706],[14.0972,12.8349],[14.0791,12.7694],[14.6728,12.6051]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11357310-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E16"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_016_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-016" "none" "none" [14.4110,12.8170] 0.6160 0.0680 (-0.963770247) 0.266733784 #([14.7169,12.7676],[14.1232,12.9319],[14.1051,12.8664],[14.6988,12.7021]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11357310-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E14"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_017_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-017" "none" "none" [17.1990,11.9000] 0.6160 0.0680 0.250717936 0.968060182 #([17.1547,11.5933],[17.3091,12.1896],[17.2433,12.2067],[17.0889,11.6104]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11356429-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E0F"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_018_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-018" "none" "none" [17.2960,11.8750] 0.6160 0.0680 0.250717936 0.968060182 #([17.2517,11.5683],[17.4061,12.1646],[17.3403,12.1817],[17.1859,11.5854]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11356429-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E11"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_019_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-019" "none" "none" [18.7600,12.7200] 0.6160 0.0680 (-0.963770247) 0.266733784 #([19.0659,12.6706],[18.4722,12.8349],[18.4541,12.7694],[19.0478,12.6051]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11357310-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E12"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_020_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-020" "none" "none" [18.7860,12.8170] 0.6160 0.0680 (-0.963770247) 0.266733784 #([19.0919,12.7676],[18.4982,12.9319],[18.4801,12.8664],[19.0738,12.7021]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11357310-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E10"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_021_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-021" "none" "none" [21.5740,11.9000] 0.6160 0.0680 0.250717936 0.968060182 #([21.5297,11.5933],[21.6841,12.1896],[21.6183,12.2067],[21.4639,11.6104]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11356429-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E0B"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_022_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-022" "none" "none" [21.6710,11.8750] 0.6160 0.0680 0.250717936 0.968060182 #([21.6267,11.5683],[21.7811,12.1646],[21.7153,12.1817],[21.5609,11.5854]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11356429-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E0D"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_023_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-023" "none" "none" [23.1350,12.7200] 0.6160 0.0680 (-0.963770247) 0.266733784 #([23.4409,12.6706],[22.8472,12.8349],[22.8291,12.7694],[23.4228,12.6051]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11357310-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E0E"
    PSL_furnBox "curtain" "PSL_L1_Furn_curtain_024_CURTAIN_LINEAR_SINGLE - DB01" 1 "L1-curtain-024" "none" "none" [23.1610,12.8170] 0.6160 0.0680 (-0.963770247) 0.266733784 #([23.4669,12.7676],[22.8732,12.9319],[22.8551,12.8664],[23.4488,12.7021]) "CURTAIN_LINEAR_SINGLE - DB01" "CURTAIN_LINEAR_SINGLE - DB01-11357310-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E0C"
    PSL_furnBox "lamp" "PSL_L1_Furn_lamp_001_LAMP_TABLE LAMP_003_ANTIFONI - DL-08" 1 "L1-lamp-001" "none" "none" [4.6980,2.0800] 0.5070 0.1980 (-0.990983200) 0.133986185 #([4.9625,2.1441],[4.4601,2.2121],[4.4335,2.0159],[4.9359,1.9479]) "LAMP_TABLE LAMP_003_ANTIFONI - DL-08" "LAMP_TABLE LAMP_003_ANTIFONI - DL-08-13593144-FURNITURE PLAN - EXECUTIVE SUITE" "Q-SPCQ" "50EE"
    PSL_furnBox "lamp" "PSL_L1_Furn_lamp_002_LAMP_TABLE LAMP_003_ANTIFONI - DL-08" 1 "L1-lamp-002" "none" "none" [18.4220,11.5300] 0.5070 0.1980 (-0.611527040) 0.791223533 #([18.6554,11.3900],[18.3453,11.7911],[18.1886,11.6700],[18.4987,11.2689]) "LAMP_TABLE LAMP_003_ANTIFONI - DL-08" "LAMP_TABLE LAMP_003_ANTIFONI - DL-08-13906887-FURNITURE PLAN" "Q-SPCQ" "5022"
    PSL_furnBox "sanitary" "PSL_L1_Furn_sanitary_001_loose shapes on P-SANR-FIXT" 1 "L1-sanitary-001" "none" "none" [7.6690,7.0400] 0.0990 0.0470 0.139345933 0.990243763 #([7.6854,6.9877],[7.6992,7.0857],[7.6526,7.0923],[7.6388,6.9943]) "loose shapes on P-SANR-FIXT" "none" "P-SANR-FIXT" "none"
    PSL_furnBox "sanitary" "PSL_L1_Furn_sanitary_002_loose shapes on P-SANR-FIXT" 1 "L1-sanitary-002" "none" "none" [7.6690,7.2950] 0.0990 0.0470 (-0.139345933) 0.990243763 #([7.6992,7.2493],[7.6854,7.3473],[7.6388,7.3407],[7.6526,7.2427]) "loose shapes on P-SANR-FIXT" "none" "P-SANR-FIXT" "none"
    PSL_furnBox "sanitary" "PSL_L1_Furn_sanitary_003_loose shapes on P-SANR-FIXT" 1 "L1-sanitary-003" "none" "none" [7.6690,8.2250] 0.0990 0.0470 0.139345933 0.990243763 #([7.6854,8.1727],[7.6992,8.2707],[7.6526,8.2773],[7.6388,8.1793]) "loose shapes on P-SANR-FIXT" "none" "P-SANR-FIXT" "none"
    PSL_furnBox "sanitary" "PSL_L1_Furn_sanitary_004_loose shapes on P-SANR-FIXT" 1 "L1-sanitary-004" "none" "none" [7.6690,8.4800] 0.0990 0.0470 (-0.139345933) 0.990243763 #([7.6992,8.4343],[7.6854,8.5323],[7.6388,8.5257],[7.6526,8.4277]) "loose shapes on P-SANR-FIXT" "none" "P-SANR-FIXT" "none"
    PSL_furnBox "sanitary" "PSL_L1_Furn_sanitary_005_loose shapes on P-SANR-FIXT" 1 "L1-sanitary-005" "none" "none" [7.8600,7.1670] 0.5900 0.4570 0.000000000 1.000000000 #([8.0885,6.8720],[8.0885,7.4620],[7.6315,7.4620],[7.6315,6.8720]) "loose shapes on P-SANR-FIXT" "none" "P-SANR-FIXT" "none"
    PSL_furnBox "sanitary" "PSL_L1_Furn_sanitary_006_loose shapes on P-SANR-FIXT" 1 "L1-sanitary-006" "none" "none" [7.8600,8.3520] 0.5900 0.4570 0.000000000 1.000000000 #([8.0885,8.0570],[8.0885,8.6470],[7.6315,8.6470],[7.6315,8.0570]) "loose shapes on P-SANR-FIXT" "none" "P-SANR-FIXT" "none"
    PSL_furnBox "sanitary" "PSL_L1_Furn_sanitary_007_loose shapes on P-SANR-FIXT" 1 "L1-sanitary-007" "none" "none" [9.4670,11.9440] 0.0880 0.0310 0.870183755 0.492727342 #([9.4363,11.9088],[9.5129,11.9522],[9.4977,11.9792],[9.4211,11.9358]) "loose shapes on P-SANR-FIXT" "none" "P-SANR-FIXT" "none"
    PSL_furnBox "sanitary" "PSL_L1_Furn_sanitary_008_loose shapes on P-SANR-FIXT" 1 "L1-sanitary-008" "none" "none" [9.5820,11.7340] 1.7120 0.8490 0.866025404 0.500000000 #([9.0529,10.9384],[10.5356,11.7944],[10.1111,12.5296],[8.6284,11.6736]) "loose shapes on P-SANR-FIXT" "none" "P-SANR-FIXT" "none"
    PSL_furnBox "sanitary" "PSL_L1_Furn_sanitary_009_loose shapes on P-SANR-FIXT" 1 "L1-sanitary-009" "none" "none" [10.5090,6.5960] 0.6780 0.3740 0.000000000 1.000000000 #([10.6960,6.2570],[10.6960,6.9350],[10.3220,6.9350],[10.3220,6.2570]) "loose shapes on P-SANR-FIXT" "none" "P-SANR-FIXT" "none"
    PSL_furnBox "sanitary" "PSL_L1_Furn_sanitary_010_loose shapes on P-SANR-FIXT" 1 "L1-sanitary-010" "none" "none" [11.4220,7.9270] 0.2710 0.2130 (-0.500302269) 0.865850818 #([11.5820,7.8630],[11.4464,8.0976],[11.2620,7.9910],[11.3976,7.7564]) "loose shapes on P-SANR-FIXT" "none" "P-SANR-FIXT" "none"
    PSL_furnBox "sanitary" "PSL_L1_Furn_sanitary_011_loose shapes on P-SANR-FIXT" 1 "L1-sanitary-011" "none" "none" [11.4220,9.1750] 0.2710 0.2130 (-0.500302269) 0.865850818 #([11.5820,9.1110],[11.4464,9.3456],[11.2620,9.2390],[11.3976,9.0044]) "loose shapes on P-SANR-FIXT" "none" "P-SANR-FIXT" "none"
    PSL_furnBox "sanitary" "PSL_L1_Furn_sanitary_012_TOILET PAPER - SA-03" 1 "L1-sanitary-012" "none" "none" [11.6850,1.5890] 0.2800 0.1170 0.000000000 1.000000000 #([11.7435,1.4490],[11.7435,1.7290],[11.6265,1.7290],[11.6265,1.4490]) "TOILET PAPER - SA-03" "TOILET PAPER - SA-03-12051735-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4E57"
    PSL_furnBox "appliance" "PSL_L1_Furn_appliance_001_ADSK_US_M_M_Refrigerator - 500" 1 "L1-appliance-001" "none" "none" [22.1120,3.7340] 1.1000 0.5000 1.000000000 0.000000000 #([21.5620,3.4840],[22.6620,3.4840],[22.6620,3.9840],[21.5620,3.9840]) "ADSK_US_M_M_Refrigerator - 500" "ADSK_US_M_M_Refrigerator - 500-13836790-GENERAL ARRANGEMENT PLAN" "Q-SPCQ" "4F7F"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_001_loose shapes on I-FURN" 1 "L1-seat-001" "none" "none" [4.9240,5.7680] 1.5000 0.5000 0.000000000 1.000000000 #([5.1740,5.0180],[5.1740,6.5180],[4.6740,6.5180],[4.6740,5.0180]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_002_loose shapes on I-FURN" 1 "L1-seat-002" "none" "none" [5.2540,2.0940] 1.8000 0.7000 1.000000000 0.000000000 #([4.3540,1.7440],[6.1540,1.7440],[6.1540,2.4440],[4.3540,2.4440]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_003_loose shapes on I-FURN" 1 "L1-seat-003" "none" "none" [5.8500,8.7170] 0.9620 0.8110 0.432085749 0.901832526 #([6.0079,8.1080],[6.4235,8.9756],[5.6921,9.3260],[5.2765,8.4584]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_004_loose shapes on I-FURN" 1 "L1-seat-004" "none" "none" [6.2360,5.8590] 1.9250 1.8300 1.000000000 0.000000000 #([5.2735,4.9440],[7.1985,4.9440],[7.1985,6.7740],[5.2735,6.7740]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_005_loose shapes on I-FURN" 1 "L1-seat-005" "none" "none" [6.9600,4.5990] 0.5450 0.5390 (-0.980236662) 0.197828427 #([7.2804,4.8093],[6.7462,4.9171],[6.6396,4.3887],[7.1738,4.2809]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_006_loose shapes on I-FURN" 1 "L1-seat-006" "none" "none" [6.9600,7.1200] 0.5450 0.5390 0.980236662 0.197828427 #([6.7462,6.8019],[7.2804,6.9097],[7.1738,7.4381],[6.6396,7.3303]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_007_loose shapes on I-FURN" 1 "L1-seat-007" "none" "none" [7.0150,5.4150] 0.7040 0.3780 0.000000000 1.000000000 #([7.2040,5.0630],[7.2040,5.7670],[6.8260,5.7670],[6.8260,5.0630]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_008_loose shapes on I-FURN" 1 "L1-seat-008" "none" "none" [7.0150,6.3150] 0.7040 0.3780 0.000000000 1.000000000 #([7.2040,5.9630],[7.2040,6.6670],[6.8260,6.6670],[6.8260,5.9630]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_009_loose shapes on I-FURN" 1 "L1-seat-009" "none" "none" [13.4520,8.9100] 1.0210 0.8520 0.906896990 0.421352406 #([13.1685,8.3086],[14.0945,8.7388],[13.7355,9.5114],[12.8095,9.0812]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_010_loose shapes on I-FURN" 1 "L1-seat-010" "none" "none" [13.7090,8.1750] 0.7330 0.5250 (-0.976821954) 0.214053429 #([14.1232,8.3530],[13.4072,8.5099],[13.2948,7.9970],[14.0108,7.8401]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_011_loose shapes on I-FURN" 1 "L1-seat-011" "none" "none" [18.5500,8.6750] 1.4950 1.4950 0.648917027 0.760859181 #([18.6337,7.6212],[19.6038,8.7587],[18.4663,9.7288],[17.4962,8.5913]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_012_loose shapes on I-FURN" 1 "L1-seat-012" "none" "none" [18.5680,11.2510] 1.2000 0.6000 (-0.500000000) 0.866025404 #([19.1278,10.8814],[18.5278,11.9206],[18.0082,11.6206],[18.6082,10.5814]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_013_loose shapes on I-FURN" 1 "L1-seat-013" "none" "none" [23.2340,9.3520] 3.9500 2.7750 0.000000000 1.000000000 #([24.6215,7.3770],[24.6215,11.3270],[21.8465,11.3270],[21.8465,7.3770]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_014_loose shapes on I-FURN" 1 "L1-seat-014" "none" "none" [24.3990,8.2540] 0.7040 0.4000 0.000000000 1.000000000 #([24.5990,7.9020],[24.5990,8.6060],[24.1990,8.6060],[24.1990,7.9020]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_015_loose shapes on I-FURN" 1 "L1-seat-015" "none" "none" [24.3990,10.4590] 0.7040 0.4000 0.000000000 1.000000000 #([24.5990,10.1070],[24.5990,10.8110],[24.1990,10.8110],[24.1990,10.1070]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "seat" "PSL_L1_Furn_seat_016_loose shapes on I-FURN" 1 "L1-seat-016" "none" "none" [24.4590,9.3520] 0.5600 0.5360 0.000000000 1.000000000 #([24.7270,9.0720],[24.7270,9.6320],[24.1910,9.6320],[24.1910,9.0720]) "loose shapes on I-FURN" "none" "I-FURN" "none"
    PSL_furnBox "table" "PSL_L1_Furn_table_001_Gruppo-19" 1 "L1-table-001" "none" "none" [17.6330,8.6770] 0.6170 0.5920 0.999994502 0.003316120 #([17.3255,8.3800],[17.9425,8.3820],[17.9405,8.9740],[17.3235,8.9720]) "Gruppo-19" "Gruppo-19" "I-FURN-CHAR" "5F81"
    PSL_furnBox "table" "PSL_L1_Furn_table_002_Gruppo-19" 1 "L1-table-002" "none" "none" [17.9000,8.0280] 0.6170 0.5920 0.704758043 0.709447744 #([17.8926,7.6005],[18.3274,8.0383],[17.9074,8.4555],[17.4726,8.0177]) "Gruppo-19" "Gruppo-19" "I-FURN-CHAR" "5F82"
    PSL_furnBox "table" "PSL_L1_Furn_table_003_Gruppo-19" 1 "L1-table-003" "none" "none" [17.9020,9.3240] 0.6170 0.5920 (-0.709447744) 0.704758043 #([18.3295,9.3166],[17.8917,9.7514],[17.4745,9.3314],[17.9123,8.8966]) "Gruppo-19" "Gruppo-19" "I-FURN-CHAR" "5F80"
    PSL_furnBox "table" "PSL_L1_Furn_table_004_Gruppo-19" 1 "L1-table-004" "none" "none" [18.5480,7.7590] 0.6170 0.5920 (-0.003316120) 0.999994502 #([18.8450,7.4515],[18.8430,8.0685],[18.2510,8.0665],[18.2530,7.4495]) "Gruppo-19" "Gruppo-19" "I-FURN-CHAR" "5F7B"
    PSL_furnBox "table" "PSL_L1_Furn_table_005_Gruppo-19" 1 "L1-table-005" "none" "none" [18.5510,9.5920] 0.6170 0.5920 (-0.003490651) 0.999993908 #([18.8481,9.2845],[18.8459,9.9015],[18.2539,9.8995],[18.2561,9.2825]) "Gruppo-19" "Gruppo-19" "I-FURN-CHAR" "5F7F"
    PSL_furnBox "table" "PSL_L1_Furn_table_006_Gruppo-19" 1 "L1-table-006" "none" "none" [19.1970,8.0260] 0.6170 0.5920 (-0.709447744) 0.704758043 #([19.6245,8.0186],[19.1867,8.4534],[18.7695,8.0334],[19.2073,7.5986]) "Gruppo-19" "Gruppo-19" "I-FURN-CHAR" "5F7C"
    PSL_furnBox "table" "PSL_L1_Furn_table_007_Gruppo-19" 1 "L1-table-007" "none" "none" [19.1990,9.3220] 0.6170 0.5920 0.704758043 0.709447744 #([19.1916,8.8945],[19.6264,9.3323],[19.2064,9.7495],[18.7716,9.3117]) "Gruppo-19" "Gruppo-19" "I-FURN-CHAR" "5F7E"
    PSL_furnBox "table" "PSL_L1_Furn_table_008_Gruppo-19" 1 "L1-table-008" "none" "none" [19.4660,8.6740] 0.6170 0.5920 0.999994502 0.003316120 #([19.1585,8.3770],[19.7755,8.3790],[19.7735,8.9710],[19.1565,8.9690]) "Gruppo-19" "Gruppo-19" "I-FURN-CHAR" "5F7D"
    PSL_furnBox "cabinet" "PSL_L1_Furn_cabinet_001_loose shapes on Q-CASE" 1 "L1-cabinet-001" "none" "none" [3.1990,9.5140] 0.9880 0.6220 0.000000000 1.000000000 #([3.5100,9.0200],[3.5100,10.0080],[2.8880,10.0080],[2.8880,9.0200]) "loose shapes on Q-CASE" "none" "Q-CASE" "none"
    PSL_furnBox "cabinet" "PSL_L1_Furn_cabinet_002_loose shapes on Q-CASE" 1 "L1-cabinet-002" "none" "none" [7.2040,5.8590] 3.4500 0.3000 0.000000000 1.000000000 #([7.3540,4.1340],[7.3540,7.5840],[7.0540,7.5840],[7.0540,4.1340]) "loose shapes on Q-CASE" "none" "Q-CASE" "none"
    PSL_furnBox "cabinet" "PSL_L1_Furn_cabinet_003_loose shapes on Q-CASE" 1 "L1-cabinet-003" "none" "none" [20.8490,9.3520] 1.3500 0.1250 0.000000000 1.000000000 #([20.9115,8.6770],[20.9115,10.0270],[20.7865,10.0270],[20.7865,8.6770]) "loose shapes on Q-CASE" "none" "Q-CASE" "none"
    PSL_furnBox "cabinet" "PSL_L1_Furn_cabinet_004_loose shapes on Q-CASE" 1 "L1-cabinet-004" "none" "none" [20.9120,8.1270] 0.9000 0.6000 0.000000000 1.000000000 #([21.2120,7.6770],[21.2120,8.5770],[20.6120,8.5770],[20.6120,7.6770]) "loose shapes on Q-CASE" "none" "Q-CASE" "none"
    PSL_furnBox "cabinet" "PSL_L1_Furn_cabinet_005_loose shapes on Q-CASE" 1 "L1-cabinet-005" "none" "none" [21.0920,10.6080] 0.9880 0.6220 0.000000000 1.000000000 #([21.4030,10.1140],[21.4030,11.1020],[20.7810,11.1020],[20.7810,10.1140]) "loose shapes on Q-CASE" "none" "Q-CASE" "none"
    PSL_furnBox "cabinet" "PSL_L1_Furn_cabinet_006_loose shapes on Q-CASE" 1 "L1-cabinet-006" "none" "none" [24.6070,9.3690] 4.7500 0.3600 0.000000000 1.000000000 #([24.7870,6.9940],[24.7870,11.7440],[24.4270,11.7440],[24.4270,6.9940]) "loose shapes on Q-CASE" "none" "Q-CASE" "none"
    PSL_furnBox "cabinet" "PSL_L1_Furn_cabinet_007_loose shapes on Q-CASE" 1 "L1-cabinet-007" "none" "none" [24.6740,9.3520] 3.7100 0.1050 0.000000000 1.000000000 #([24.7265,7.4970],[24.7265,11.2070],[24.6215,11.2070],[24.6215,7.4970]) "loose shapes on Q-CASE" "none" "Q-CASE" "none"
    PSL_furnBox "cabinet" "PSL_L1_Furn_cabinet_008_FP_55-GENERAL ARRANGEMENT PLAN" 1 "L1-cabinet-008" "none" "none" [24.6770,11.5550] 0.2180 0.0650 (-0.707106781) 0.707106781 #([24.7771,11.5009],[24.6229,11.6551],[24.5769,11.6091],[24.7311,11.4549]) "FP_55-GENERAL ARRANGEMENT PLAN" "FP_55-GENERAL ARRANGEMENT PLAN" "Q-CASE" "5923"
    PSL_furnBox "cabinet" "PSL_L1_Furn_cabinet_009_FP_56-GENERAL ARRANGEMENT PLAN" 1 "L1-cabinet-009" "none" "none" [24.6800,7.1490] 0.2230 0.0680 0.707106781 0.707106781 #([24.6252,7.0461],[24.7829,7.2038],[24.7348,7.2519],[24.5771,7.0942]) "FP_56-GENERAL ARRANGEMENT PLAN" "FP_56-GENERAL ARRANGEMENT PLAN" "Q-CASE" "5924"
)
-- The build's furniture step: materials, levels, every box.
fn PSL_furnRun =
(
    PSL_furnMakeMaterials()
    PSL_furnSetLevels()
    PSL_furnAll()
)
-- For every floor, its level as the scene has it: the most common value (to the millimetre) of z minus PSL_base over the
-- objects that carry PSL_floor and PSL_base. Sets PSL_furnLevels for the floors it finds and returns how many.
fn PSL_furnSceneLevels =
(
    local fis = #()
    local mms = #()
    local cnt = #()
    for o in objects where (getUserProp o "PSL_floor") != undefined and (getUserProp o "PSL_base") != undefined do
    (
        local fi = (PSL_furnNum (getUserProp o "PSL_floor")) as integer
        local mmv = (floor ((o.pos.z - (PSL_furnNum (getUserProp o "PSL_base"))) * 1000.0 + 0.5)) as integer
        local k = 0
        for j = 1 to fis.count where fis[j] == fi and mms[j] == mmv do k = j
        if k == 0 then ( append fis fi; append mms mmv; append cnt 1 )
        else cnt[k] += 1
    )
    local found = 0
    for f = 1 to PSL_furnFloors.count do
    (
        local best = 0
        for j = 1 to fis.count where fis[j] == f and cnt[j] > best do
        (
            best = cnt[j]
            PSL_furnLevels[f] = mms[j] / 1000.0
        )
        if best > 0 do found += 1
    )
    found
)
-- "Furniture boxes only": adds the boxes to a scene already built from this model and changes nothing else. It refuses, and
-- changes nothing, when boxes are there already or System Units are not metres. The placement shift comes from the hidden
-- datum PSL_ORIGIN_DWG (shift = minus its x, y) and each level from the objects that carry PSL_floor and PSL_base;
-- what it cannot find it takes from the window (the tick box and the level spinners), and says so. It reports in message boxes
-- of its own (the Build button's message is written for parts), so PSL_build returns false after it.
fn PSL_furnAdd =
(
    if PSL_furnWant == false then
    (
        messageBox "Tick Build furniture boxes as well. Nothing in this scene has been changed." title:"Presidential_suite_Layout"
        return false
    )
    if abs(units.systemScale - 1.0) > 0.0001 or units.systemType != #meters then
    (
        messageBox "This scene's System Units are not metres, so the boxes would come out the wrong size. Nothing in this scene has been changed." title:"Presidential_suite_Layout"
        return false
    )
    local existing = 0
    for o in objects where (getUserProp o "PSL_furn") != undefined or (matchPattern o.layer.name pattern:"PSL_*_Furn_*") do existing += 1
    if existing > 0 then
    (
        messageBox ("This scene already has furniture boxes (" + (existing as string) + " objects). Nothing in this scene has been changed.") title:"Presidential_suite_Layout"
        return false
    )
    local t0 = timeStamp()
    local notes = ""
    local datum = undefined
    for o in objects where o.name == "PSL_ORIGIN_DWG" do datum = o
    if datum == undefined then notes += "The origin datum PSL_ORIGIN_DWG was not found, so the boxes are placed by the tick box At the drawing's own coordinates. "
    else PSL_shift = [0.0 - datum.pos.x, 0.0 - datum.pos.y]
    PSL_nodes = #()
    PSL_failed = #()
    PSL_furnMakeMaterials()
    PSL_furnSetLevels()
    local found = PSL_furnSceneLevels()
    if found < PSL_furnFloors.count then notes += "The level of " + ((PSL_furnFloors.count - found) as string) + " floor(s) was not found in the scene, so the level spinners are used for it. "
    PSL_furnAll()
    format "PSL FURNITURE BOXES ADDED: % boxes in % s, % failed checks\n" PSL_nodes.count ((timeStamp() - t0) / 1000.0) PSL_failed.count
    for f in PSL_failed do format "  check failed: %\n" f
    if notes != "" do messageBox notes title:"Presidential_suite_Layout"
    if PSL_failed.count == 0 then messageBox ("Added " + (PSL_nodes.count as string) + " furniture boxes. Every box passed its height and position checks. Nothing else in this scene was changed. Save As to keep your .max file.") title:"Presidential_suite_Layout"
    else messageBox ((PSL_failed.count as string) + " of the " + (PSL_nodes.count as string) + " furniture boxes failed a check and are on layer PSL_Check_Failed (listed in the MAXScript Listener). The others were added and passed. Nothing else in this scene was changed.") title:"Presidential_suite_Layout"
    true
)
-- After the build: every box takes the height of its kind (PSL_furnHeights, read from the window) and stands on its kind's
-- base, or on top of the kind of support it was drawn on (the support's kind is none, or undefined, or empty: no support). A box
-- keeps the level it is on (its z minus its PSL_base), so levels moved by "Update levels and heights" stay. A box that is not
-- a Box any more, or of an unknown kind, is left alone.
fn PSL_furnApply =
(
    local n = 0
    local skipped = 0
    for o in objects where (getUserProp o "PSL_furn") != undefined do
    (
        local ki = findItem PSL_furnKeys ((getUserProp o "PSL_furnKind") as string)
        if (classOf o) != Box or ki == 0 then skipped += 1
        else
        (
            local z0 = PSL_furnZ0 ki (findItem PSL_furnKeys ((getUserProp o "PSL_furnOnKind") as string))
            o.pos.z = o.pos.z - (PSL_furnNum (getUserProp o "PSL_base")) + z0
            o.height = PSL_furnHeights[ki]
            setUserProp o "PSL_base" z0
            n += 1
        )
    )
    #(n, skipped)
)
fn PSL_build =
(
    if PSL_furnAddOnly then
    (
        -- "Furniture boxes only" has said what it did, or why it did nothing, in its own message: false = nothing more to report
        PSL_furnAdd()
        return false
    )
    if objects.count > 0 then
    (
        messageBox "Open a NEW EMPTY scene first. Nothing in this scene has been changed." title:"Presidential_suite_Layout"
        return false
    )
    units.systemType = #meters
    units.systemScale = 1.0
    units.displayType = #metric
    units.metricType = #meters
    PSL_nodes = #()
    PSL_failed = #()
    PSL_makeMaterials()
    local t0 = timeStamp()
    PSL_part #wall "PSL_L1_Wall_001" #(#([(-10.5125),1.4305],[(-10.5425),1.4605],[(-10.6125),1.3895],[(-10.6125),(-1.2605)],[1.5125,(-1.2605)],[1.5125,(-0.4605)],[2.5125,(-0.4605)],[2.5125,(-1.4605)],[2.8125,(-1.4605)],[2.8125,(-0.8105)],[3.7625,(-0.8105)],[3.7625,(-0.3605)],[5.6125,(-0.3605)],[5.6125,(-0.6605)],[6.8875,(-0.6605)],[6.8875,(-1.2605)],[7.0375,(-1.2605)],[7.0375,(-1.4605)],[7.2375,(-1.4605)],[7.2375,(-1.2605)],[7.3875,(-1.2605)],[7.3875,(-0.6605)],[8.6625,(-0.6605)],[8.6625,(-0.3605)],[10.5125,(-0.3605)],[10.5125,(-0.8105)],[10.6125,(-0.8105)],[10.6125,(-0.2605)],[8.5625,(-0.2605)],[8.5625,(-0.5605)],[7.3875,(-0.5605)],[7.3875,(-0.2605)],[6.8875,(-0.2605)],[6.8875,(-0.5605)],[5.7125,(-0.5605)],[5.7125,(-0.2605)],[3.6625,(-0.2605)],[3.6625,(-0.7105)],[2.8125,(-0.7105)],[2.8125,(-0.2605)],[1.3125,(-0.2605)],[1.3125,(-1.0605)],[(-1.3625),(-1.0605)],[(-1.3625),(-0.4605)],[0.5125,(-0.4605)],[0.5125,(-0.2605)],[(-1.8625),(-0.2605)],[(-1.8625),(-1.1605)],[(-10.1125),(-1.1605)],[(-10.1125),(-0.2605)],[(-10.5125),(-0.2605)])) 0.0000 3.0000 true 1 [13.3745,1.4695] [2.7620,0.0090] [23.9870,2.9300]
    PSL_part #wall "PSL_L1_Wall_002" #(#([(-0.0710),0.3750],[(-0.0710),0.1250],[(-0.1210),0.1250],[(-0.1210),(-0.3750)],[(-0.0210),(-0.3750)],[(-0.0210),0.2750],[0.1210,0.2750],[0.1210,0.3750])) 0.0000 3.0000 true 1 [24.9580,0.3840] [24.8370,0.0090] [25.0790,0.7590]
    PSL_part #wall "PSL_L1_Wall_003" #(#([(-0.0500),0.2250],[(-0.0500),(-0.2250)],[0.0500,(-0.2250)],[0.0500,0.2250])) 0.0000 3.0000 true 1 [17.0870,3.4340] [17.0370,3.2090] [17.1370,3.6590]
    PSL_part #wall "PSL_L1_Wall_004" #(#([(-0.0500),(-0.0240)],[(-0.0230),(-0.0240)],[(-0.0210),(-0.2250)],[0.0500,(-0.2250)],[0.0500,0.2250],[(-0.0500),0.2250])) 0.0000 3.0000 true 1 [15.1870,3.5340] [15.1370,3.3090] [15.2370,3.7590]
    PSL_part #wall "PSL_L1_Wall_005" #(#([(-0.0465),0.0390],[(-0.0685),0.0610],[(-0.0875),0.1200],[(-0.0875),(-0.1200)],[(-0.0825),(-0.0900)],[(-0.0465),(-0.0400)],[(-0.0185),(-0.0250)],[0.0875,(-0.0150)],[0.0725,0.0000],[0.0875,0.0150],[0.0825,0.0200],[0.0125,0.0200])) 0.0000 3.0000 true 1 [20.6995,7.6570] [20.6120,7.5370] [20.7870,7.7770]
    PSL_part #wall "PSL_L1_Wall_006" #(#([0.5470,1.2605],[0.5670,1.3345],[0.4700,1.3605],[(-0.5670),1.3605],[(-0.5670),(-1.2895)],[(-0.4970),(-1.3605)],[(-0.4670),(-1.3305)],[(-0.4670),0.3605],[(-0.0670),0.3605],[(-0.0670),1.2605])) 0.0000 3.0000 true 1 [3.3290,10.1485] [2.7620,8.7880] [3.8960,11.5090]
    PSL_part #wall "PSL_L1_Wall_007" #(#([0.9830,(-0.2875)],[0.2460,(-0.2875)],[(-0.6640),1.2875],[(-1.0540),1.0625],[(-1.0800),0.9665],[(-1.0400),0.9555],[(-0.7010),1.1515],[0.1300,(-0.2875)],[(-0.0540),(-0.2875)],[(-0.0540),(-1.2875)],[0.4460,(-1.2875)],[0.4460,(-0.3875)],[1.0600,(-0.3875)],[1.0800,(-0.3135)])) 0.0000 3.0000 true 1 [20.3160,11.7965] [19.2360,10.5090] [21.3960,13.0840]
    PSL_part #wall "PSL_L1_Wall_008" #(#([0.9830,(-0.2875)],[0.2460,(-0.2875)],[(-0.6640),1.2875],[(-1.0540),1.0625],[(-1.0800),0.9665],[(-1.0400),0.9555],[(-0.7010),1.1515],[0.1300,(-0.2875)],[(-0.0540),(-0.2875)],[(-0.0540),(-1.2875)],[0.4460,(-1.2875)],[0.4460,(-0.3875)],[1.0600,(-0.3875)],[1.0800,(-0.3135)])) 0.0000 3.0000 true 1 [11.5660,11.7965] [10.4860,10.5090] [12.6460,13.0840]
    PSL_part #wall "PSL_L1_Wall_009" #(#([0.7340,(-0.7375)],[0.5920,(-0.7375)],[(-0.3180),0.8375],[(-0.7080),0.6125],[(-0.7340),0.5165],[(-0.6940),0.5055],[(-0.3550),0.7015],[0.5340,(-0.8375)],[0.7340,(-0.8375)])) 0.0000 3.0000 true 1 [24.3450,12.2465] [23.6110,11.4090] [25.0790,13.0840]
    PSL_part #wall "PSL_L1_Wall_010" #(#([1.0800,(-0.7635)],[0.9830,(-0.7375)],[0.2460,(-0.7375)],[(-0.6640),0.8375],[(-1.0540),0.6125],[(-1.0800),0.5165],[(-1.0400),0.5055],[(-0.7010),0.7015],[0.1880,(-0.8375)],[1.0600,(-0.8375)])) 0.0000 3.0000 true 1 [15.9410,12.2465] [14.8610,11.4090] [17.0210,13.0840]
    PSL_part #wall "PSL_L1_Wall_011" #(#([1.0800,(-0.7635)],[0.9830,(-0.7375)],[0.2460,(-0.7375)],[(-0.6640),0.8375],[(-1.0540),0.6125],[(-1.0800),0.5165],[(-1.0400),0.5055],[(-0.7010),0.7015],[0.1880,(-0.8375)],[1.0600,(-0.8375)])) 0.0000 3.0000 true 1 [7.1910,12.2465] [6.1110,11.4090] [8.2710,13.0840]
    PSL_part #glass "PSL_L1_Glass_001" #(#([0.0465,1.7590],[(-0.0465),1.7590],[(-0.0465),(-1.7590)],[0.0465,(-1.7590)])) 0.0000 3.0000 true 1 [1.6155,5.8590] [1.5690,4.1000] [1.6620,7.6180]
    PSL_part #glass "PSL_L1_Glass_002" #(#([(-0.6205),0.5505],[0.5505,(-0.6205)],[0.6205,(-0.5495)],[(-0.5495),0.6205])) 0.0000 3.0000 true 1 [2.2115,3.4795] [1.5910,2.8590] [2.8320,4.1000]
    PSL_part #glass "PSL_L1_Glass_003" #(#([(-0.6205),(-0.5505)],[(-0.5495),(-0.6205)],[0.6205,0.5495],[0.5505,0.6205])) 0.0000 3.0000 true 1 [2.2115,8.2385] [1.5910,7.6180] [2.8320,8.8590]
    PSL_part #lintel "PSL_L1_Lintel_001_L1-002" #(#([0.4240,(-0.0500)],[0.4240,0.0500],[(-0.4240),0.0500],[(-0.4240),(-0.0500)])) 2.4000 3.0000 true 1 [16.6120,1.1590] [16.1880,1.1090] [17.0360,1.2090]
    PSL_part #lintel "PSL_L1_Lintel_002_L1-003" #(#([(-0.8990),0.1750],[(-0.8990),(-0.1750)],[0.8990,(-0.1750)],[0.8990,0.1750])) 2.1000 3.0000 true 1 [16.1370,3.4840] [15.2380,3.3090] [17.0360,3.6590]
    PSL_part #lintel "PSL_L1_Lintel_003_L1-004" #(#([0.4490,(-0.0500)],[0.4490,0.0500],[(-0.4490),0.0500],[(-0.4490),(-0.0500)])) 2.1000 3.0000 true 1 [24.4370,0.7090] [23.9880,0.6590] [24.8860,0.7590]
    PSL_part #lintel "PSL_L1_Lintel_004_L1-006" #(#([0.4910,(-0.2200)],[0.4890,(-0.0200)],[0.4620,(-0.0190)],[0.4620,0.2290],[(-0.4910),0.2210],[(-0.4870),(-0.2290)])) 2.1000 3.0000 true 1 [14.6740,3.5290] [14.1830,3.3000] [15.1650,3.7580]
    PSL_part #glass "PSL_L1_Glass_004_L1-011 pane" #(#([0.6085,0.3630],[(-0.6185),(-0.3450)],[(-0.6085),(-0.3630)],[0.6185,0.3460])) 0.0000 3.0000 true 1 [4.6935,12.6600] [4.0750,12.2970] [5.3120,13.0230]
    PSL_part #glass "PSL_L1_Glass_005_L1-012 pane" #(#([0.3870,(-0.1140)],[0.3920,(-0.0950)],[(-0.3870),0.1140],[(-0.3920),0.0940])) 0.0000 3.0000 true 1 [5.7340,12.9160] [5.3420,12.8020] [6.1260,13.0300]
    PSL_part #glass "PSL_L1_Glass_006_L1-013 pane" #(#([(-0.1140),(-0.3865)],[(-0.0950),(-0.3915)],[0.1140,0.3865],[0.0940,0.3915])) 0.0000 3.0000 true 1 [3.9520,11.8865] [3.8380,11.4950] [4.0660,12.2780]
    PSL_part #glass "PSL_L1_Glass_007_L1-014 pane" #(#([0.6085,0.3630],[(-0.6185),(-0.3450)],[(-0.6085),(-0.3630)],[0.6185,0.3460])) 0.0000 3.0000 true 1 [9.0685,12.6600] [8.4500,12.2970] [9.6870,13.0230]
    PSL_part #glass "PSL_L1_Glass_008_L1-015 pane" #(#([0.3870,(-0.1140)],[0.3920,(-0.0950)],[(-0.3870),0.1140],[(-0.3920),0.0940])) 0.0000 3.0000 true 1 [10.1090,12.9160] [9.7170,12.8020] [10.5010,13.0300]
    PSL_part #glass "PSL_L1_Glass_009_L1-016 pane" #(#([(-0.1140),(-0.3865)],[(-0.0950),(-0.3915)],[0.1140,0.3865],[0.0940,0.3915])) 0.0000 3.0000 true 1 [8.3270,11.8865] [8.2130,11.4950] [8.4410,12.2780]
    PSL_part #glass "PSL_L1_Glass_010_L1-017 pane" #(#([0.6085,0.3630],[(-0.6185),(-0.3450)],[(-0.6085),(-0.3630)],[0.6185,0.3460])) 0.0000 3.0000 true 1 [13.4435,12.6600] [12.8250,12.2970] [14.0620,13.0230]
    PSL_part #glass "PSL_L1_Glass_011_L1-018 pane" #(#([0.3870,(-0.1140)],[0.3920,(-0.0950)],[(-0.3870),0.1140],[(-0.3920),0.0940])) 0.0000 3.0000 true 1 [14.4840,12.9160] [14.0920,12.8020] [14.8760,13.0300]
    PSL_part #glass "PSL_L1_Glass_012_L1-019 pane" #(#([(-0.1140),(-0.3865)],[(-0.0950),(-0.3915)],[0.1140,0.3865],[0.0940,0.3915])) 0.0000 3.0000 true 1 [12.7020,11.8865] [12.5880,11.4950] [12.8160,12.2780]
    PSL_part #glass "PSL_L1_Glass_013_L1-020 pane" #(#([0.6085,0.3630],[(-0.6185),(-0.3450)],[(-0.6085),(-0.3630)],[0.6185,0.3460])) 0.0000 3.0000 true 1 [17.8185,12.6600] [17.2000,12.2970] [18.4370,13.0230]
    PSL_part #glass "PSL_L1_Glass_014_L1-021 pane" #(#([0.3870,(-0.1140)],[0.3920,(-0.0950)],[(-0.3870),0.1140],[(-0.3920),0.0940])) 0.0000 3.0000 true 1 [18.8590,12.9160] [18.4670,12.8020] [19.2510,13.0300]
    PSL_part #glass "PSL_L1_Glass_015_L1-022 pane" #(#([(-0.1140),(-0.3865)],[(-0.0950),(-0.3915)],[0.1140,0.3865],[0.0940,0.3915])) 0.0000 3.0000 true 1 [17.0770,11.8865] [16.9630,11.4950] [17.1910,12.2780]
    PSL_part #glass "PSL_L1_Glass_016_L1-023 pane" #(#([0.6085,0.3630],[(-0.6185),(-0.3450)],[(-0.6085),(-0.3630)],[0.6185,0.3460])) 0.0000 3.0000 true 1 [22.1935,12.6600] [21.5750,12.2970] [22.8120,13.0230]
    PSL_part #glass "PSL_L1_Glass_017_L1-024 pane" #(#([0.3870,(-0.1140)],[0.3920,(-0.0950)],[(-0.3870),0.1140],[(-0.3920),0.0940])) 0.0000 3.0000 true 1 [23.2340,12.9160] [22.8420,12.8020] [23.6260,13.0300]
    PSL_part #glass "PSL_L1_Glass_018_L1-025 pane" #(#([(-0.1140),(-0.3865)],[(-0.0950),(-0.3915)],[0.1140,0.3865],[0.0940,0.3915])) 0.0000 3.0000 true 1 [21.4520,11.8865] [21.3380,11.4950] [21.5660,12.2780]
    PSL_part #slab "PSL_L1_Slab_001" #(#([(-11.6665),(-2.7985)],[(-10.4365),(-1.5685)],[(-10.4365),0.1055],[(-10.0365),0.1055],[(-10.0365),1.0055],[(-9.4305),1.0055],[(-9.1625),1.9245],[(-8.0475),2.5685],[(-7.2165),2.3465],[(-6.8495),2.5345],[(-5.9665),1.0055],[(-5.0555),1.0055],[(-4.7875),1.9245],[(-3.6725),2.5685],[(-2.8415),2.3465],[(-2.4745),2.5345],[(-1.6845),1.1655],[(-1.8465),1.1655],[(-1.8465),0.1055],[(-1.2865),0.1055],[(-1.2865),1.0055],[(-0.6805),1.0055],[(-0.4125),1.9245],[0.7025,2.5685],[1.5335,2.3465],[1.9005,2.5345],[2.7835,1.0055],[3.6945,1.0055],[3.9625,1.9245],[5.0775,2.5685],[5.9085,2.3465],[6.2755,2.5345],[7.0655,1.1655],[6.9035,1.1655],[6.9035,0.1055],[7.4635,0.1055],[7.4635,1.0055],[8.0695,1.0055],[8.3375,1.9245],[9.4525,2.5685],[10.2835,2.3465],[10.6505,2.5345],[11.5335,1.0055],[11.7805,1.0055],[11.7805,1.1655],[11.6255,1.1655],[10.7095,2.7515],[10.3905,2.5675],[9.5255,2.7985],[9.4935,2.6755],[9.4585,2.7355],[8.1795,1.9965],[8.2135,1.9375],[7.9585,2.0055],[7.7335,1.1655],[7.2505,1.1655],[6.3345,2.7515],[6.0155,2.5675],[5.1505,2.7985],[5.1185,2.6755],[5.0835,2.7355],[3.8045,1.9965],[3.8385,1.9375],[3.5835,2.0055],[3.3585,1.1655],[2.8755,1.1655],[1.9595,2.7515],[1.6405,2.5675],[0.7755,2.7985],[0.7435,2.6755],[0.7085,2.7355],[(-0.5705),1.9965],[(-0.5365),1.9375],[(-0.7915),2.0055],[(-1.0165),1.1655],[(-1.4995),1.1655],[(-2.4155),2.7515],[(-2.7345),2.5675],[(-3.5995),2.7985],[(-3.6315),2.6755],[(-3.6665),2.7355],[(-4.9455),1.9965],[(-4.9115),1.9375],[(-5.1665),2.0055],[(-5.3915),1.1655],[(-5.8745),1.1655],[(-6.7905),2.7515],[(-7.1095),2.5675],[(-7.9745),2.7985],[(-8.0065),2.6755],[(-8.0415),2.7355],[(-9.3205),1.9965],[(-9.2865),1.9375],[(-9.5415),2.0055],[(-9.7665),1.1655],[(-10.5965),1.1655],[(-10.5965),(-1.5015)],[(-11.7805),(-2.6855)])) (-0.2500) 0.0000 false 1 [13.3285,10.3735] [1.5480,7.5750] [25.1090,13.1720]
    PSL_part #slab "PSL_L1_Slab_002" #(#([(-11.7805),1.4160],[(-10.5965),0.2330],[(-10.5965),(-2.4350)],[1.5885,(-2.4350)],[1.5885,(-1.6350)],[2.5285,(-1.6350)],[2.5285,(-2.6350)],[2.8885,(-2.6350)],[2.8885,(-1.9850)],[3.8385,(-1.9850)],[3.8385,(-1.5350)],[5.6285,(-1.5350)],[5.6285,(-1.8350)],[6.9035,(-1.8350)],[6.9035,(-2.4350)],[7.0535,(-2.4350)],[7.0535,(-2.6350)],[7.3135,(-2.6350)],[7.3135,(-2.4350)],[7.4635,(-2.4350)],[7.4635,(-1.8350)],[8.7385,(-1.8350)],[8.7385,(-1.5350)],[10.5285,(-1.5350)],[10.5285,(-1.9840)],[11.5285,(-2.0040)],[11.5285,(-2.0750)],[11.4785,(-2.0750)],[11.4785,(-2.6350)],[11.6385,(-2.6350)],[11.6385,(-1.9850)],[11.7805,(-1.9850)],[11.7805,(-1.8250)],[11.5885,(-1.8250)],[11.5885,(-1.3550)],[9.2415,(-1.3750)],[9.2375,(-1.3530)],[8.8245,(-1.2080)],[8.4815,(-0.9600)],[8.2235,(-0.6250)],[8.0715,(-0.2300)],[8.0385,0.1920],[8.0835,0.4700],[8.1605,0.6950],[8.1615,0.8520],[7.9285,0.9980],[7.7235,1.1830],[7.4895,1.5240],[7.3585,1.9160],[7.3355,2.5560],[7.2415,2.6350],[7.1395,2.5550],[7.1335,1.8410],[7.3295,1.4600],[7.3965,1.1810],[7.4045,0.7010],[7.5095,0.4040],[7.5495,0.1210],[7.5045,(-0.3070)],[7.3375,(-0.7030)],[7.0635,(-1.0340)],[6.7055,(-1.2710)],[6.2945,(-1.3950)],[4.9565,(-1.3750)],[4.9525,(-1.3540)],[4.5105,(-1.1920)],[4.1595,(-0.9220)],[3.9055,(-0.5610)],[3.7695,(-0.1390)],[3.7515,0.1550],[3.8365,0.5940],[3.8305,1.0740],[2.3895,1.0950],[1.8735,1.1750],[0.8485,1.1640],[0.4915,0.9310],[0.2145,0.8320],[(-0.2015),0.7740],[(-0.4885),0.7900],[(-0.9005),0.9190],[(-1.2565),1.1620],[(-1.5285),1.4980],[(-1.6485),1.7590],[(-1.7215),2.0560],[(-1.9025),2.0640],[(-1.9205),1.1280],[(-1.7515),0.8490],[(-1.6415),0.5340],[(-1.4645),0.1910],[(-1.3765),(-0.2350)],[(-1.3895),(-0.5240)],[(-1.4595),(-0.8060)],[(-1.5825),(-1.0670)],[(-1.8465),(-1.3940)],[(-1.8465),(-2.2750)],[(-10.0365),(-2.2750)],[(-10.0365),(-1.3750)],[(-10.4365),(-1.3750)],[(-10.4365),0.2990],[(-11.6665),1.5290])) (-0.2500) 0.0000 false 1 [13.3285,2.6140] [1.5480,(-0.0210)] [25.1090,5.2490]
    PSL_room "FOYER" [13.6000,4.6360] 1
    PSL_room "LIVING & DINING AREA" [12.2150,6.0170] 1
    PSL_room "MASTER BEDROOM" [3.7980,3.5050] 1
    PSL_room "MASTER BATHROOM" [8.0760,10.7750] 1
    PSL_room "BEDROOM 2" [22.0680,9.4790] 1
    PSL_room "BEDROOM FOYER" [8.0300,4.5170] 1
    if PSL_furnWant do PSL_furnRun()
    local origin = point name:"PSL_ORIGIN_DWG" size:1.0 pos:[0.0 - PSL_shift.x, 0.0 - PSL_shift.y, 0.0]
    origin.isHidden = true
    origin.ignoreExtents = true
    (PSL_layer "PSL_Datums").addNode origin
    setUserProp origin "Source" "presidential suite_layout.dwg, converted with LibreDWG 0.14; drawing units mm, model in metres"
    setUserProp origin "Levels" ("floor levels " + (PSL_levels as string) + " m, wall heights " + (PSL_heights as string) + " m")
    setUserProp origin "Built" "by the walkthrough app, 11 Nov 2026 (model data 9041e84fa2bb)"
    viewport.setType #view_iso_user
    select PSL_nodes
    max zoomext sel all
    clearSelection()
    redrawViews()
    format "PSL BUILD COMPLETE: % objects in % s, % failed checks\n" PSL_nodes.count ((timeStamp() - t0) / 1000.0) PSL_failed.count
    for f in PSL_failed do format "  check failed: %\n" f
    true
)
try (destroyDialog PSL_UI) catch ()
rollout PSL_UI "Presidential_suite_Layout" width:340
(
    label info "Open a new empty scene before Build." align:#left
    label units1 "Build sets System Units to metres." align:#left
    checkbox dwg "At the drawing's own coordinates" checked:true tooltip:"Untick to centre the model on the origin"
    spinner lv1 "Level 1 floor level (m):" range:[-50, 500, 0.00] type:#float fieldwidth:60
    spinner ht1 "Level 1 wall height (m):" range:[2.2, 15, 3.00] type:#float fieldwidth:60
    group "Furniture boxes (heights in mm)"
    (
        checkbox fb "Build furniture boxes" checked:true
        checkbox fo "Furniture boxes only" checked:false tooltip:"Add only the boxes to the scene already built from this model: no structure, and the empty-scene check is skipped"
        label fol "(add to the scene already built from this model)" align:#left
        spinner fh1 "TV / wall screen:" across:2 range:[10, 5000, 600] type:#integer fieldwidth:40
        spinner fh2 "Curtain:" range:[10, 5000, 2400] type:#integer fieldwidth:40
        spinner fh3 "Lamp:" across:2 range:[10, 5000, 500] type:#integer fieldwidth:40
        spinner fh4 "Sanitary fitting:" range:[10, 5000, 850] type:#integer fieldwidth:40
        spinner fh5 "Appliance:" across:2 range:[10, 5000, 900] type:#integer fieldwidth:40
        spinner fh6 "Chair / stool:" range:[10, 5000, 450] type:#integer fieldwidth:40
        spinner fh7 "Table / desk:" across:2 range:[10, 5000, 750] type:#integer fieldwidth:40
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
        PSL_levels = #(lv1.value)
        PSL_heights = #(ht1.value)
        PSL_collapse = cm.checked
        PSL_shift = if dwg.checked then [0.0, 0.0] else [13.3290, 6.5750]
        PSL_furnHeights = #((fh1.value / 1000.0),(fh2.value / 1000.0),(fh3.value / 1000.0),(fh4.value / 1000.0),(fh5.value / 1000.0),(fh6.value / 1000.0),(fh7.value / 1000.0),(fh8.value / 1000.0))
        PSL_furnWant = fb.checked
        PSL_furnAddOnly = fo.checked
        try
        (
            if PSL_build() do
            (
                if PSL_failed.count == 0 then messageBox ("Built " + (PSL_nodes.count as string) + " objects. Every part passed the closed-solid, height and position checks. Save As to keep your .max file.") title:"Presidential_suite_Layout"
                else messageBox ((PSL_failed.count as string) + " part(s) failed a check and are on layer PSL_Check_Failed (listed in the MAXScript Listener). Everything else was built.") title:"Presidential_suite_Layout"
            )
        )
        catch (messageBox (getCurrentException()) title:"Build stopped")
    )
    on upd pressed do
    (
        local r = PSL_updateLevels #(lv1.value) #(ht1.value)
        messageBox ("Every part moved to its level; " + (r[1] as string) + " parts set to their level's wall height." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were collapsed already and kept their height.") else "")) title:"Presidential_suite_Layout"
    )
    on col pressed do
    (
        local n = PSL_collapseAll()
        messageBox ((n as string) + " parts collapsed to Editable Mesh.") title:"Presidential_suite_Layout"
    )
    on fap pressed do
    (
        PSL_furnHeights = #((fh1.value / 1000.0),(fh2.value / 1000.0),(fh3.value / 1000.0),(fh4.value / 1000.0),(fh5.value / 1000.0),(fh6.value / 1000.0),(fh7.value / 1000.0),(fh8.value / 1000.0))
        local r = PSL_furnApply()
        messageBox ((r[1] as string) + " furniture boxes set to the heights in the window and stood on their floor or support." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were left alone (not a Box any more, or a kind this script does not know).") else "")) title:"Presidential_suite_Layout"
    )
)
createDialog PSL_UI
