-- PRESIDENTIAL SUITE (TEST) / from "layout presidential test.dwg" / built by the CAD-to-3D test pipeline, 19 Oct 2026
-- Same model as presidential_3d_preview.html (model data eefc6aede5ed). Floor to floor 3.00 m, as given for the project.
-- Placed at the DWG's own coordinates in metres (to line up with the DWG imported in metres), or centred on the origin
-- if you untick that box in the script's window.
-- Every part stays LIVE (no Editable Poly): an editable spline outline + an Extrude modifier (output: Mesh) + Smooth.
--   * Change a height: the Extrude amount on that object, or "Update heights" in this script's window for all of them.
--   * Change an outline: select the spline level under the modifiers and move vertices.
--   * Editable Mesh: tick "Collapse to Editable Mesh" before Build, or press "Collapse all now" later.
-- Each object's pivot is at the middle of its own outline, on its base.
-- Each part is checked as it is built (closed solid, height, position). A part that fails is kept on layer
-- PS_Check_Failed and listed in the MAXScript Listener; the rest is still built.
-- Build sets System Units to metres. Nothing in an existing scene is changed: run it in a NEW EMPTY scene.
global PS_UI
global PS_nodes = #()
global PS_failed = #()
global PS_level = 0.0
global PS_height = 3.00
global PS_collapse = false
global PS_shift = [0.0, 0.0]
global PS_mats
-- Furniture boxes: one coloured placeholder box per furniture piece (colour = kind), on layers PS_<level>_Furn_<Kind>. Type
-- each kind's height in mm in the window, before the build or later with "Apply furniture heights" (boxes on a table, counter or
-- cabinet follow its height). A box is a live Box, never an Editable Poly, and carries the piece's family, block and DWG layer
-- as user properties, so the 3D team can swap it for their own model by family name. A property with nothing to say (no support,
-- no block, no handle) holds the word none, never empty text: 3ds Max does not say what getUserProp returns for empty text.
-- Each box is checked as it is built: base z, top z and its four corners carried through its transform, and the node's min and
-- max in the plan only for an unrotated box (Autodesk does not say what they are for a turned node). A box that fails goes on
-- layer PS_Check_Failed and is listed in the Listener; the rest is still built.
-- "Furniture boxes only" adds just the boxes to a scene already built from this model. Below: the kinds in the model's order,
-- heights and bases in metres.
global PS_furnWant = true
global PS_furnAddOnly = false
global PS_furnFloors = #("suite")
global PS_furnKeys = #("computer","printer","tv","curtain","plant","seat","table","coffee-table","cabinet","tall-cabinet")
global PS_furnLayers = #("Computer","Printer","Tv","Curtain","Plant","Seat","Table","CoffeeTable","Cabinet","TallCabinet")
global PS_furnBases = #(0.0000,0.0000,0.9000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000)
global PS_furnHeights = #(0.4500,0.3000,0.6000,2.4000,0.6000,0.4500,0.7500,0.4500,0.9000,2.1000)
global PS_furnLevels = #()
global PS_furnMats = #()

fn PS_layer n =
(
    local ly = LayerManager.getLayerFromName n
    if ly == undefined do ly = LayerManager.newLayerFromName n
    ly
)
fn PS_mat key =
(
    local m = undefined
    for x in PS_mats where x.name == ("PS " + key) do m = x
    m
)
fn PS_makeMaterials =
(
    PS_mats = #()
    append PS_mats (standardMaterial name:"PS Wall" diffuse:(color 227 221 211))
    append PS_mats (standardMaterial name:"PS Stone" diffuse:(color 200 192 178))
    append PS_mats (standardMaterial name:"PS Wood" diffuse:(color 176 140 104))
    append PS_mats (standardMaterial name:"PS Glass" diffuse:(color 170 200 214) opacity:30 specularLevel:60 glossiness:60)
    append PS_mats (standardMaterial name:"PS Slab" diffuse:(color 212 216 210))
)
-- The outline's knots are relative to c, the middle of the outline; the node is then moved to c, so that is its pivot.
fn PS_shape nm loops =
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
fn PS_extrudeOf o =
(
    local ex = undefined
    for md in o.modifiers where classOf md == Extrude do ex = md
    ex
)
-- kind: #wall #column #lintel #glass #low #builtin #balustrade #slab #deck #post; z0/z1 in metres above the floor level;
-- follow = the top follows the wall height. c = pivot, mn/mx = outline extents (DWG coordinates).
fn PS_part kind nm loops z0 z1 follow c mn mx =
(
    local info = case kind of
    (
        #wall: #("PS_Walls", "Wall")
        #column: #("PS_Columns", "Wall")
        #lintel: #("PS_Lintels", "Wall")
        #glass: #("PS_Glass", "Glass")
        #low: #("PS_LowWalls", "Stone")
        #builtin: #("PS_BuiltIns", "Wood")
        #balustrade: #("PS_Balustrade", "Glass")
        #slab: #("PS_Slab", "Slab")
        #deck: #("PS_Decks", "Wood")
        #post: #("PS_Pergola", "Wood")
    )
    local top = if follow then PS_height else z1
    local zb = PS_level + z0
    local ht = top - z0
    local o = PS_shape nm loops
    o.pos = [c.x - PS_shift.x, c.y - PS_shift.y, zb]
    addModifier o (Extrude amount:ht segs:1 capStart:true capEnd:true output:1 smooth:false)
    addModifier o (Smooth autoSmooth:true threshold:25.0)
    local mt = PS_mat info[2]
    o.material = mt
    o.wirecolor = mt.diffuse
    setUserProp o "PS_kind" (kind as string)
    setUserProp o "PS_base" z0
    setUserProp o "PS_follow" follow
    -- the checks run on the evaluated mesh (what the modifiers produce)
    local m = snapshotAsMesh o
    local why = ""
    local tol = 0.002
    if m.numfaces < 3 then why = "no faces"
    else if (meshop.getOpenEdges m).numberSet != 0 then why = "open edges (not a closed solid)"
    else if abs(o.min.z - zb) > tol or abs(o.max.z - (zb + ht)) > tol then why = "height"
    else if abs(o.min.x - (mn.x - PS_shift.x)) > tol or abs(o.min.y - (mn.y - PS_shift.y)) > tol or abs(o.max.x - (mx.x - PS_shift.x)) > tol or abs(o.max.y - (mx.y - PS_shift.y)) > tol then why = "position"
    m = undefined
    if why == "" then
    (
        (PS_layer info[1]).addNode o
        setUserProp o "PS_check" "ok"
    )
    else
    (
        (PS_layer "PS_Check_Failed").addNode o
        setUserProp o "PS_check" why
        append PS_failed (nm + ": " + why)
    )
    if PS_collapse do convertToMesh o
    append PS_nodes o
    o
)
fn PS_room nm p =
(
    local t = text text:nm size:0.35 pos:[p.x - PS_shift.x, p.y - PS_shift.y, PS_level + 0.02]
    t.name = "PS_Room_" + nm
    t.wirecolor = color 30 60 110
    (PS_layer "PS_RoomNames").addNode t
    append PS_nodes t
    t
)
-- After the build: set every live part whose top follows the wall height to a new height (the floor level stays).
fn PS_updateHeights newH =
(
    local n = 0
    local skipped = 0
    for o in objects where ((getUserProp o "PS_follow") as string) == "true" do
    (
        local ex = PS_extrudeOf o
        if ex == undefined then skipped += 1
        else ( ex.amount = newH - (((getUserProp o "PS_base") as string) as float); n += 1 )
    )
    PS_height = newH
    #(n, skipped)
)
fn PS_collapseAll =
(
    local n = 0
    for o in objects where (getUserProp o "PS_kind") != undefined and o.modifiers.count > 0 do ( convertToMesh o; n += 1 )
    n
)
-- Furniture boxes: one coloured Box per piece, a placeholder the 3D team swaps for their own model by family name.
-- A box is a live Box (width along its own long axis, length across it, height), never an Editable Poly or Mesh and never
-- collapsed: "Collapse all now" only takes objects that carry PS_kind and a modifier, and a box has neither. Every box
-- carries PS_floor and PS_base (its bottom, in metres above its level) and PS_follow = false, so "Update levels
-- and heights" moves it with its level and leaves its height alone.
fn PS_furnNum v = ((v as string) as float)
fn PS_furnMakeMaterials =
(
    PS_furnMats = #()
    append PS_furnMats (standardMaterial name:"PS Furn computer" diffuse:(color 123 63 181))
    append PS_furnMats (standardMaterial name:"PS Furn printer" diffuse:(color 142 142 142))
    append PS_furnMats (standardMaterial name:"PS Furn tv" diffuse:(color 52 64 143))
    append PS_furnMats (standardMaterial name:"PS Furn curtain" diffuse:(color 201 160 220))
    append PS_furnMats (standardMaterial name:"PS Furn plant" diffuse:(color 46 158 79))
    append PS_furnMats (standardMaterial name:"PS Furn seat" diffuse:(color 224 123 0))
    append PS_furnMats (standardMaterial name:"PS Furn table" diffuse:(color 138 90 43))
    append PS_furnMats (standardMaterial name:"PS Furn coffee-table" diffuse:(color 201 163 122))
    append PS_furnMats (standardMaterial name:"PS Furn cabinet" diffuse:(color 47 127 193))
    append PS_furnMats (standardMaterial name:"PS Furn tall-cabinet" diffuse:(color 27 79 138))
)
-- The floor levels the build was started with (a copy: nothing is shared with the script's own array).
fn PS_furnSetLevels =
(
    PS_furnLevels = #()
    for z in (#(PS_level)) do append PS_furnLevels z
)
-- Where a box stands, in metres above its level: on its kind's base, or on top of the kind of support it was drawn on
-- (ki = its kind, oki = the kind of its support, 0 for none). A support never stands on anything.
fn PS_furnZ0 ki oki =
(
    local z0 = PS_furnBases[ki]
    if oki > 0 do z0 = PS_furnBases[oki] + PS_furnHeights[oki]
    z0
)
-- kind = the kind, nm = the object's name, fi = the floor's index, pid = the piece's id, supId and supKind = its support's id
-- and kind ("none" for none), c = the box's centre and cs = its four corners (DWG coordinates), w d = its size along its own
-- long and short axis, ca sa = cos and sin of the angle from +x to the long axis, fam blk lay hnd = family, block, DWG layer,
-- handle ("none" for nothing). The box gets an explicit matrix: its X, Y and Z axes in the world, then its pivot (the middle of
-- its base).
fn PS_furnBox kind nm fi pid supId supKind c w d ca sa cs fam blk lay hnd =
(
    local ki = findItem PS_furnKeys kind
    local z0 = PS_furnZ0 ki (findItem PS_furnKeys supKind)
    local ht = PS_furnHeights[ki]
    local zb = PS_furnLevels[fi] + z0
    local o = box name:nm width:w length:d height:ht
    o.transform = (matrix3 [ca, sa, 0.0] [(0.0 - sa), ca, 0.0] [0.0, 0.0, 1.0] [c.x - PS_shift.x, c.y - PS_shift.y, zb])
    local mt = PS_furnMats[ki]
    o.material = mt
    o.wirecolor = mt.diffuse
    setUserProp o "PS_furn" "true"
    setUserProp o "PS_furnKind" kind
    setUserProp o "PS_furnId" pid
    setUserProp o "PS_furnOn" supId
    setUserProp o "PS_furnOnKind" supKind
    setUserProp o "PS_family" fam
    setUserProp o "PS_block" blk
    setUserProp o "PS_layer" lay
    setUserProp o "PS_handle" hnd
    setUserProp o "PS_floor" fi
    setUserProp o "PS_base" z0
    setUserProp o "PS_follow" false
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
    else if unrotated and (abs(o.min.x - (mnx - PS_shift.x)) > tol or abs(o.min.y - (mny - PS_shift.y)) > tol or abs(o.max.x - (mxx - PS_shift.x)) > tol or abs(o.max.y - (mxy - PS_shift.y)) > tol) then why = "bounding box"
    else
    (
        local hw = o.width / 2.0
        local hd = o.length / 2.0
        local lc = #([(0.0 - hw), (0.0 - hd), 0.0], [hw, (0.0 - hd), 0.0], [hw, hd, 0.0], [(0.0 - hw), hd, 0.0])
        for k = 1 to 4 do
        (
            local q = lc[k] * o.transform
            if why == "" and (abs(q.x - (cs[k].x - PS_shift.x)) > tol or abs(q.y - (cs[k].y - PS_shift.y)) > tol) then why = "corner " + (k as string)
        )
    )
    if why == "" then
    (
        (PS_layer ("PS_" + PS_furnFloors[fi] + "_Furn_" + PS_furnLayers[ki])).addNode o
        setUserProp o "PS_check" "ok"
    )
    else
    (
        (PS_layer "PS_Check_Failed").addNode o
        setUserProp o "PS_check" why
        append PS_failed (nm + ": " + why)
    )
    append PS_nodes o
    o
)
-- Every piece of the model, in the model's order.
fn PS_furnAll =
(
    PS_furnBox "computer" "PS_suite_Furn_computer_001_Enscape AssetDefinition - Computer 003" 1 "suite-computer-001" "suite-table-001" "table" [1.3000,2.1000] 0.7400 0.4300 1.000000000 0.000000000 #([0.9300,1.8850],[1.6700,1.8850],[1.6700,2.3150],[0.9300,2.3150]) "Enscape AssetDefinition - Computer 003" "Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003" "I-FURN" "A1"
    PS_furnBox "printer" "PS_suite_Furn_printer_001_PRINTER_DESKTOP_LASER - Type 1" 1 "suite-printer-001" "suite-table-001" "table" [0.5000,1.9000] 0.4000 0.3000 1.000000000 0.000000000 #([0.3000,1.7500],[0.7000,1.7500],[0.7000,2.0500],[0.3000,2.0500]) "PRINTER_DESKTOP_LASER - Type 1" "PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1" "Q-SPCQ" "A2"
    PS_furnBox "tv" "PS_suite_Furn_tv_001_APPLIANCE_TV_WALL MOUNT WITH BRACKET - 7" 1 "suite-tv-001" "none" "none" [8.0000,5.0000] 1.6800 0.0500 0.000000000 1.000000000 #([8.0250,4.1600],[8.0250,5.8400],[7.9750,5.8400],[7.9750,4.1600]) "APPLIANCE_TV_WALL MOUNT WITH BRACKET - 75_" "APPLIANCE_TV_WALL MOUNT WITH BRACKET - 75_" "Q-SPCQ" "A3"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_001_Double Curtain" 1 "suite-curtain-001" "none" "none" [1.0000,7.0000] 3.0000 0.1500 1.000000000 0.000000000 #([(-0.5000),6.9250],[2.5000,6.9250],[2.5000,7.0750],[(-0.5000),7.0750]) "Double Curtain" "Double Curtain" "DA-FACILITIES" "A4"
    PS_furnBox "plant" "PS_suite_Furn_plant_001_Enscape AssetDefinition - Potted Plant 0" 1 "suite-plant-001" "none" "none" [7.0000,2.0000] 0.5000 0.5000 1.000000000 0.000000000 #([6.7500,1.7500],[7.2500,1.7500],[7.2500,2.2500],[6.7500,2.2500]) "Enscape AssetDefinition - Potted Plant 028 Peace Lily" "Enscape AssetDefinition - Potted Plant 028 Peace Lily" "L-PLNT" "A5"
    PS_furnBox "seat" "PS_suite_Furn_seat_001_mollie_chair_a685_revit - A685 2" 1 "suite-seat-001" "none" "none" [2.0000,3.0000] 0.6000 0.5700 1.000000000 0.000000000 #([1.7000,2.7150],[2.3000,2.7150],[2.3000,3.2850],[1.7000,3.2850]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-1234567-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "A6"
    PS_furnBox "seat" "PS_suite_Furn_seat_002_mollie_chair_a685_revit - A685 2" 1 "suite-seat-002" "none" "none" [3.0000,3.0000] 0.6000 0.5700 0.866025404 0.500000000 #([2.8827,2.6032],[3.4023,2.9032],[3.1173,3.3968],[2.5977,3.0968]) "mollie_chair_a685_revit - A685 2" "mollie_chair_a685_revit - A685 2-1234568-LEVEL 1 GENERAL ARRANGEMENT" "I-FURN" "A7"
    PS_furnBox "seat" "PS_suite_Furn_seat_003_CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE" 1 "suite-seat-003" "none" "none" [0.0000,5.0000] 0.5000 0.5000 0.000000000 1.000000000 #([0.2500,4.7500],[0.2500,5.2500],[(-0.2500),5.2500],[(-0.2500),4.7500]) "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE" "CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE103 500W BLUE" "I-FURN" "A8"
    PS_furnBox "table" "PS_suite_Furn_table_001_IA_J15_WORKING TABLE - 1800W 1000D 750H" 1 "suite-table-001" "none" "none" [1.0000,2.0000] 1.8000 1.0000 1.000000000 0.000000000 #([0.1000,1.5000],[1.9000,1.5000],[1.9000,2.5000],[0.1000,2.5000]) "IA_J15_WORKING TABLE - 1800W 1000D 750H" "IA_J15_WORKING TABLE - 1800W 1000D 750H" "I-FURN" "A9"
    PS_furnBox "table" "PS_suite_Furn_table_002_IA_J15_WORKING TABLE - 1400W 1000D 750H" 1 "suite-table-002" "none" "none" [5.0000,4.0000] 1.4000 1.0000 (-0.866025404) 0.500000000 #([5.8562,4.0830],[4.6438,4.7830],[4.1438,3.9170],[5.3562,3.2170]) "IA_J15_WORKING TABLE - 1400W 1000D 750H" "IA_J15_WORKING TABLE - 1400W 1000D 750H" "I-FURN" "AA"
    PS_furnBox "coffee-table" "PS_suite_Furn_coffee-table_001_COFFEE TABLE RETANGLE - VENNATIVE - TYPE" 1 "suite-coffee-table-001" "none" "none" [(-2.0000),0.0000] 1.0000 0.5000 1.000000000 0.000000000 #([(-2.5000),(-0.2500)],[(-1.5000),(-0.2500)],[(-1.5000),0.2500],[(-2.5000),0.2500]) "COFFEE TABLE RETANGLE - VENNATIVE - TYPE 1" "COFFEE TABLE RETANGLE - VENNATIVE - TYPE 1" "I-FURN" "AB"
    PS_furnBox "cabinet" "PS_suite_Furn_cabinet_001_IA_J10_WORK CABINET - IA_J10_WORK CABINE" 1 "suite-cabinet-001" "none" "none" [(-3.0000),6.0000] 2.4500 0.6000 1.000000000 0.000000000 #([(-4.2250),5.7000],[(-1.7750),5.7000],[(-1.7750),6.3000],[(-4.2250),6.3000]) "IA_J10_WORK CABINET - IA_J10_WORK CABINET" "IA_J10_WORK CABINET - IA_J10_WORK CABINET" "Q-CASE" "AC"
    PS_furnBox "tall-cabinet" "PS_suite_Furn_tall-cabinet_001_TALL CABINET - TALL CABINET 2800W" 1 "suite-tall-cabinet-001" "none" "none" [6.0000,(-1.0000)] 2.8000 0.4100 0.000000000 1.000000000 #([6.2050,(-2.4000)],[6.2050,0.4000],[5.7950,0.4000],[5.7950,(-2.4000)]) "TALL CABINET - TALL CABINET 2800W" "TALL CABINET - TALL CABINET 2800W" "Q-CASE" "AD"
)
-- The build's furniture step: materials, levels, every box.
fn PS_furnRun =
(
    PS_furnMakeMaterials()
    PS_furnSetLevels()
    PS_furnAll()
)
-- For every floor, its level as the scene has it: the most common value (to the millimetre) of z minus PS_base over the
-- objects that carry PS_floor and PS_base. Sets PS_furnLevels for the floors it finds and returns how many.
fn PS_furnSceneLevels =
(
    local fis = #()
    local mms = #()
    local cnt = #()
    for o in objects where (getUserProp o "PS_floor") != undefined and (getUserProp o "PS_base") != undefined do
    (
        local fi = (PS_furnNum (getUserProp o "PS_floor")) as integer
        local mmv = (floor ((o.pos.z - (PS_furnNum (getUserProp o "PS_base"))) * 1000.0 + 0.5)) as integer
        local k = 0
        for j = 1 to fis.count where fis[j] == fi and mms[j] == mmv do k = j
        if k == 0 then ( append fis fi; append mms mmv; append cnt 1 )
        else cnt[k] += 1
    )
    local found = 0
    for f = 1 to PS_furnFloors.count do
    (
        local best = 0
        for j = 1 to fis.count where fis[j] == f and cnt[j] > best do
        (
            best = cnt[j]
            PS_furnLevels[f] = mms[j] / 1000.0
        )
        if best > 0 do found += 1
    )
    found
)
-- "Furniture boxes only": adds the boxes to a scene already built from this model and changes nothing else. It refuses, and
-- changes nothing, when boxes are there already or System Units are not metres. The placement shift comes from the hidden
-- datum PS_ORIGIN_DWG (shift = minus its x, y) and each level from the objects that carry PS_floor and PS_base;
-- what it cannot find it takes from the window (the tick box and the level spinners), and says so. It reports in message boxes
-- of its own (the Build button's message is written for parts), so PS_build returns false after it.
fn PS_furnAdd =
(
    if PS_furnWant == false then
    (
        messageBox "Tick Build furniture boxes as well. Nothing in this scene has been changed." title:"Presidential suite"
        return false
    )
    if abs(units.systemScale - 1.0) > 0.0001 or units.systemType != #meters then
    (
        messageBox "This scene's System Units are not metres, so the boxes would come out the wrong size. Nothing in this scene has been changed." title:"Presidential suite"
        return false
    )
    local existing = 0
    for o in objects where (getUserProp o "PS_furn") != undefined or (matchPattern o.layer.name pattern:"PS_*_Furn_*") do existing += 1
    if existing > 0 then
    (
        messageBox ("This scene already has furniture boxes (" + (existing as string) + " objects). Nothing in this scene has been changed.") title:"Presidential suite"
        return false
    )
    local t0 = timeStamp()
    local notes = ""
    local datum = undefined
    for o in objects where o.name == "PS_ORIGIN_DWG" do datum = o
    if datum == undefined then notes += "The origin datum PS_ORIGIN_DWG was not found, so the boxes are placed by the tick box At the drawing's own coordinates. "
    else PS_shift = [0.0 - datum.pos.x, 0.0 - datum.pos.y]
    PS_nodes = #()
    PS_failed = #()
    PS_furnMakeMaterials()
    PS_furnSetLevels()
    local found = PS_furnSceneLevels()
    if found < PS_furnFloors.count then notes += "The level of " + ((PS_furnFloors.count - found) as string) + " floor(s) was not found in the scene, so the level spinners are used for it. "
    PS_furnAll()
    format "PS FURNITURE BOXES ADDED: % boxes in % s, % failed checks\n" PS_nodes.count ((timeStamp() - t0) / 1000.0) PS_failed.count
    for f in PS_failed do format "  check failed: %\n" f
    if notes != "" do messageBox notes title:"Presidential suite"
    if PS_failed.count == 0 then messageBox ("Added " + (PS_nodes.count as string) + " furniture boxes. Every box passed its height and position checks. Nothing else in this scene was changed. Save As to keep your .max file.") title:"Presidential suite"
    else messageBox ((PS_failed.count as string) + " of the " + (PS_nodes.count as string) + " furniture boxes failed a check and are on layer PS_Check_Failed (listed in the MAXScript Listener). The others were added and passed. Nothing else in this scene was changed.") title:"Presidential suite"
    true
)
-- After the build: every box takes the height of its kind (PS_furnHeights, read from the window) and stands on its kind's
-- base, or on top of the kind of support it was drawn on (the support's kind is none, or undefined, or empty: no support). A box
-- keeps the level it is on (its z minus its PS_base), so levels moved by "Update levels and heights" stay. A box that is not
-- a Box any more, or of an unknown kind, is left alone.
fn PS_furnApply =
(
    local n = 0
    local skipped = 0
    for o in objects where (getUserProp o "PS_furn") != undefined do
    (
        local ki = findItem PS_furnKeys ((getUserProp o "PS_furnKind") as string)
        if (classOf o) != Box or ki == 0 then skipped += 1
        else
        (
            local z0 = PS_furnZ0 ki (findItem PS_furnKeys ((getUserProp o "PS_furnOnKind") as string))
            o.pos.z = o.pos.z - (PS_furnNum (getUserProp o "PS_base")) + z0
            o.height = PS_furnHeights[ki]
            setUserProp o "PS_base" z0
            n += 1
        )
    )
    #(n, skipped)
)
fn PS_build =
(
    if PS_furnAddOnly then
    (
        -- "Furniture boxes only" has said what it did, or why it did nothing, in its own message: false = nothing more to report
        PS_furnAdd()
        return false
    )
    if objects.count > 0 then
    (
        messageBox "Open a NEW EMPTY scene first. Nothing in this scene has been changed." title:"Presidential suite"
        return false
    )
    units.systemType = #meters
    units.systemScale = 1.0
    units.displayType = #metric
    units.metricType = #meters
    PS_nodes = #()
    PS_failed = #()
    PS_makeMaterials()
    local t0 = timeStamp()
    PS_part #slab "PS_Slab_001" #(#([(-8.0000),(-6.5000)],[8.0000,(-6.5000)],[8.0000,6.5000],[(-8.0000),6.5000])) (-0.2500) 0.0000 false [2.5000,3.0000] [(-5.5000),(-3.5000)] [10.5000,9.5000]
    PS_part #wall "PS_Wall_001" #(#([(-8.0000),(-0.1000)],[8.0000,(-0.1000)],[8.0000,0.1000],[(-8.0000),0.1000])) 0.0000 3.7000 true [2.5000,(-3.6000)] [(-5.5000),(-3.7000)] [10.5000,(-3.5000)]
    PS_room "Room A" [1.0000,2.0000]
    if PS_furnWant do PS_furnRun()
    local origin = point name:"PS_ORIGIN_DWG" size:1.0 pos:[0.0 - PS_shift.x, 0.0 - PS_shift.y, 0.0]
    origin.isHidden = true
    origin.ignoreExtents = true
    (PS_layer "PS_Datums").addNode origin
    setUserProp origin "Source" "layout presidential test.dwg, converted with LibreDWG; drawing units mm, model in metres"
    setUserProp origin "Heights" ("floor " + (PS_level as string) + " m, floor to floor " + (PS_height as string) + " m")
    viewport.setType #view_iso_user
    select PS_nodes
    max zoomext sel all
    clearSelection()
    redrawViews()
    format "PS BUILD COMPLETE: % objects in % s, % failed checks\n" PS_nodes.count ((timeStamp() - t0) / 1000.0) PS_failed.count
    for f in PS_failed do format "  check failed: %\n" f
    true
)
try (destroyDialog PS_UI) catch ()
rollout PS_UI "Presidential suite (test)" width:340
(
    label info "Open a new empty scene before Build." align:#left
    label units1 "Build sets System Units to metres." align:#left
    checkbox dwg "At the drawing's own coordinates" checked:true tooltip:"Untick to centre the suite on the origin"
    spinner lv "Floor level (m):" range:[-50, 500, 0.0] type:#float fieldwidth:70
    spinner ht "Floor to floor (m):" range:[2.2, 15, 3.00] type:#float fieldwidth:70
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
    button build "BUILD THE SUITE" width:310 height:32
    label note1 "Parts stay live: spline + Extrude (mesh) + Smooth." align:#left
    group "After the build"
    (
        button upd "Update heights to Floor to floor" width:300
        button col "Collapse all now (Editable Mesh)" width:300
        button fap "Apply furniture heights" width:300
    )
    on build pressed do
    (
        PS_level = lv.value
        PS_height = ht.value
        PS_collapse = cm.checked
        PS_shift = if dwg.checked then [0.0, 0.0] else [1.0000, 2.0000]
        PS_furnHeights = #((fh1.value / 1000.0),(fh2.value / 1000.0),(fh3.value / 1000.0),(fh4.value / 1000.0),(fh5.value / 1000.0),(fh6.value / 1000.0),(fh7.value / 1000.0),(fh8.value / 1000.0),(fh9.value / 1000.0),(fh10.value / 1000.0))
        PS_furnWant = fb.checked
        PS_furnAddOnly = fo.checked
        try
        (
            if PS_build() do
            (
                if PS_failed.count == 0 then messageBox ("Built " + (PS_nodes.count as string) + " objects. Every part passed the closed-solid, height and position checks. Save As to keep your .max file.") title:"Presidential suite"
                else messageBox ((PS_failed.count as string) + " part(s) failed a check and are on layer PS_Check_Failed (listed in the MAXScript Listener). Everything else was built.") title:"Presidential suite"
            )
        )
        catch (messageBox (getCurrentException()) title:"Build stopped")
    )
    on upd pressed do
    (
        local r = PS_updateHeights ht.value
        messageBox ((r[1] as string) + " parts set to " + (ht.value as string) + " m." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were collapsed already and kept their height.") else "")) title:"Presidential suite"
    )
    on col pressed do
    (
        local n = PS_collapseAll()
        messageBox ((n as string) + " parts collapsed to Editable Mesh.") title:"Presidential suite"
    )
    on fap pressed do
    (
        PS_furnHeights = #((fh1.value / 1000.0),(fh2.value / 1000.0),(fh3.value / 1000.0),(fh4.value / 1000.0),(fh5.value / 1000.0),(fh6.value / 1000.0),(fh7.value / 1000.0),(fh8.value / 1000.0),(fh9.value / 1000.0),(fh10.value / 1000.0))
        local r = PS_furnApply()
        messageBox ((r[1] as string) + " furniture boxes set to the heights in the window and stood on their floor or support." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were left alone (not a Box any more, or a kind this script does not know).") else "")) title:"Presidential suite"
    )
)
createDialog PS_UI
