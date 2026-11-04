-- PRESIDENTIAL SUITE (TEST) / from "layout presidential test.dwg" / built by the CAD-to-3D test pipeline, 19 Oct 2026
-- Same model as presidential_3d_preview.html (model data f1b95c53eb3d). Floor to floor 3.00 m, as given for the project.
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
global PS_furnKeys = #("tv","curtain","lamp","plant","sanitary","appliance","bed","seat","sofa","table","coffee-table","tall-cabinet","other")
global PS_furnLayers = #("Tv","Curtain","Lamp","Plant","Sanitary","Appliance","Bed","Seat","Sofa","Table","CoffeeTable","TallCabinet","Other")
global PS_furnBases = #(0.9000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000)
global PS_furnHeights = #(0.6000,2.7000,0.5000,2.5000,0.8500,0.9000,0.5000,0.4500,0.8000,0.7500,0.4500,2.1000,0.7500)
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
    append PS_furnMats (standardMaterial name:"PS Furn tv" diffuse:(color 52 64 143))
    append PS_furnMats (standardMaterial name:"PS Furn curtain" diffuse:(color 201 160 220))
    append PS_furnMats (standardMaterial name:"PS Furn lamp" diffuse:(color 255 210 63))
    append PS_furnMats (standardMaterial name:"PS Furn plant" diffuse:(color 46 158 79))
    append PS_furnMats (standardMaterial name:"PS Furn sanitary" diffuse:(color 23 162 162))
    append PS_furnMats (standardMaterial name:"PS Furn appliance" diffuse:(color 184 134 11))
    append PS_furnMats (standardMaterial name:"PS Furn bed" diffuse:(color 227 119 194))
    append PS_furnMats (standardMaterial name:"PS Furn seat" diffuse:(color 224 123 0))
    append PS_furnMats (standardMaterial name:"PS Furn sofa" diffuse:(color 255 179 71))
    append PS_furnMats (standardMaterial name:"PS Furn table" diffuse:(color 138 90 43))
    append PS_furnMats (standardMaterial name:"PS Furn coffee-table" diffuse:(color 201 163 122))
    append PS_furnMats (standardMaterial name:"PS Furn tall-cabinet" diffuse:(color 27 79 138))
    append PS_furnMats (standardMaterial name:"PS Furn other" diffuse:(color 107 107 107))
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
    PS_furnBox "tv" "PS_suite_Furn_tv_001_TV_55 inches_Recessed" 1 "suite-tv-001" "none" "none" [190.2820,(-3505.6190)] 1.8750 0.2250 (-0.866112657) 0.499848842 #([191.1502,(-3505.9902)],[189.5263,(-3505.0530)],[189.4138,(-3505.2478)],[191.0377,(-3506.1850)]) "TV_55 inches_Recessed" "Xr_SDC_DD_ID-PRS-Fur$0$TV_55 inches_Recessed" "A-2.Noi That" "1B22FD"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_001_Double Curtain" 1 "suite-curtain-001" "none" "none" [185.9030,(-3499.2710)] 0.7920 0.1230 0.000000000 1.000000000 #([185.9645,(-3499.6670)],[185.9645,(-3498.8750)],[185.8415,(-3498.8750)],[185.8415,(-3499.6670)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B2399"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_002_Double Curtain" 1 "suite-curtain-002" "none" "none" [185.9030,(-3491.0120)] 0.7920 0.1230 0.000000000 1.000000000 #([185.9645,(-3491.4080)],[185.9645,(-3490.6160)],[185.8415,(-3490.6160)],[185.8415,(-3491.4080)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B238D"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_003_Double Curtain" 1 "suite-curtain-003" "none" "none" [186.1100,(-3500.0430)] 0.7920 0.1230 (-0.500000000) 0.866025404 #([186.3613,(-3500.3552)],[185.9653,(-3499.6693)],[185.8587,(-3499.7308)],[186.2547,(-3500.4167)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B239B"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_004_Double Curtain" 1 "suite-curtain-004" "none" "none" [186.1100,(-3490.2400)] 0.7920 0.1230 0.500000000 0.866025404 #([185.9653,(-3490.6137)],[186.3613,(-3489.9278)],[186.2547,(-3489.8663)],[185.8587,(-3490.5522)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B238F"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_005_Double Curtain" 1 "suite-curtain-005" "none" "none" [187.2700,(-3502.0230)] 0.7920 0.1230 (-0.505732659) 0.862690256 #([187.5233,(-3502.3335)],[187.1228,(-3501.6503)],[187.0167,(-3501.7125)],[187.4172,(-3502.3957)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B23C6"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_006_Double Curtain" 1 "suite-curtain-006" "none" "none" [187.7690,(-3502.8760)] 0.7920 0.1230 (-0.503472411) 0.864011303 #([188.0215,(-3503.1872)],[187.6228,(-3502.5029)],[187.5165,(-3502.5648)],[187.9152,(-3503.2491)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B23C8"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_007_Double Curtain" 1 "suite-curtain-007" "none" "none" [189.0150,(-3505.0530)] 0.7920 0.1230 (-0.505883219) 0.862601976 #([189.2684,(-3505.3635)],[188.8677,(-3504.6803)],[188.7616,(-3504.7425)],[189.1623,(-3505.4257)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B23CA"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_008_Double Curtain" 1 "suite-curtain-008" "none" "none" [189.0330,(-3485.1760)] 0.7920 0.1230 0.500000000 0.866025404 #([188.8883,(-3485.5497)],[189.2843,(-3484.8638)],[189.1777,(-3484.8023)],[188.7817,(-3485.4882)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B2391"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_009_Double Curtain" 1 "suite-curtain-009" "none" "none" [189.5350,(-3484.6740)] 0.7920 0.1230 0.866287084 0.499546482 #([189.2227,(-3484.9251)],[189.9088,(-3484.5295)],[189.8473,(-3484.4229)],[189.1612,(-3484.8185)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B2393"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_010_Double Curtain" 1 "suite-curtain-010" "none" "none" [189.5870,(-3505.6220)] 0.7920 0.1230 (-0.865326428) 0.501208712 #([189.9605,(-3505.7673)],[189.2752,(-3505.3703)],[189.2135,(-3505.4767)],[189.8988,(-3505.8737)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B23CC"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_011_Double Curtain" 1 "suite-curtain-011" "none" "none" [190.5370,(-3506.1700)] 0.7920 0.1230 (-0.866722691) 0.498790313 #([190.9109,(-3506.3142)],[190.2245,(-3505.9192)],[190.1631,(-3506.0258)],[190.8495,(-3506.4208)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B23CE"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_012_Double Curtain" 1 "suite-curtain-012" "none" "none" [191.1320,(-3483.7530)] 0.7920 0.1230 0.866199884 0.499697670 #([190.8197,(-3484.0042)],[191.5057,(-3483.6084)],[191.4443,(-3483.5018)],[190.7583,(-3483.8976)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B2395"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_013_Double Curtain" 1 "suite-curtain-013" "none" "none" [191.2760,(-3506.3790)] 0.7920 0.1230 (-0.999999025) 0.001396263 #([191.6721,(-3506.3181)],[190.8801,(-3506.3169)],[190.8799,(-3506.4399)],[191.6719,(-3506.4411)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B23D0"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_014_Double Curtain" 1 "suite-curtain-014" "none" "none" [192.6210,(-3483.9050)] 0.7920 0.1230 1.000000000 0.000000000 #([192.2250,(-3483.9665)],[193.0170,(-3483.9665)],[193.0170,(-3483.8435)],[192.2250,(-3483.8435)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B2397"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_015_Double Curtain" 1 "suite-curtain-015" "none" "none" [194.8650,(-3506.3790)] 0.7920 0.1230 0.999999025 0.001396263 #([194.4691,(-3506.4411)],[195.2611,(-3506.4399)],[195.2609,(-3506.3169)],[194.4689,(-3506.3181)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B23D6"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_016_Double Curtain" 1 "suite-curtain-016" "none" "none" [195.7750,(-3506.3790)] 0.7920 0.1230 (-0.999999025) 0.001396263 #([196.1711,(-3506.3181)],[195.3791,(-3506.3169)],[195.3789,(-3506.4399)],[196.1709,(-3506.4411)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B23D4"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_017_Double Curtain" 1 "suite-curtain-017" "none" "none" [196.8780,(-3483.9050)] 0.7920 0.1230 1.000000000 0.000000000 #([196.4820,(-3483.9665)],[197.2740,(-3483.9665)],[197.2740,(-3483.8435)],[196.4820,(-3483.8435)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B2522"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_018_Double Curtain" 1 "suite-curtain-018" "none" "none" [197.3050,(-3506.3790)] 0.7920 0.1230 0.999999025 0.001396263 #([196.9091,(-3506.4411)],[197.7011,(-3506.4399)],[197.7009,(-3506.3169)],[196.9089,(-3506.3181)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B23D2"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_019_Double Curtain" 1 "suite-curtain-019" "none" "none" [197.8470,(-3483.9050)] 0.7920 0.1230 1.000000000 0.000000000 #([197.4510,(-3483.9665)],[198.2430,(-3483.9665)],[198.2430,(-3483.8435)],[197.4510,(-3483.8435)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B23C0"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_020_Double Curtain" 1 "suite-curtain-020" "none" "none" [202.0130,(-3483.9050)] 0.7920 0.1230 1.000000000 0.000000000 #([201.6170,(-3483.9665)],[202.4090,(-3483.9665)],[202.4090,(-3483.8435)],[201.6170,(-3483.8435)]) "Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$Double Curtain" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B23C2"
    PS_furnBox "curtain" "PS_suite_Furn_curtain_021_A$C86fb51a5" 1 "suite-curtain-021" "none" "none" [203.1220,(-3498.5390)] 1.2770 0.0870 (-0.866025404) 0.500000000 #([203.6967,(-3498.8206)],[202.5908,(-3498.1821)],[202.5473,(-3498.2574)],[203.6532,(-3498.8959)]) "A$C86fb51a5" "A$C86fb51a5" "Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES" "1B24CA"
    PS_furnBox "lamp" "PS_suite_Furn_lamp_001_1X-LAMP1" 1 "suite-lamp-001" "none" "none" [186.4090,(-3496.3930)] 0.3270 0.3090 (-0.829720137) 0.558179626 #([186.6309,(-3496.3561)],[186.3596,(-3496.1735)],[186.1871,(-3496.4299)],[186.4584,(-3496.6125)]) "1X-LAMP1" "Xr_SDC_DD_ID-PRS-Fur$0$XR_TP FL 8-27 INTERIOR$0$1X-LAMP1" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LEVEL-LIGHT" "1B244E"
    PS_furnBox "lamp" "PS_suite_Furn_lamp_002_1X-LAMP1" 1 "suite-lamp-002" "none" "none" [186.4090,(-3493.8980)] 0.3270 0.3090 0.829720137 0.558179626 #([186.3596,(-3494.1175)],[186.6309,(-3493.9349)],[186.4584,(-3493.6785)],[186.1871,(-3493.8611)]) "1X-LAMP1" "Xr_SDC_DD_ID-PRS-Fur$0$XR_TP FL 8-27 INTERIOR$0$1X-LAMP1" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LEVEL-LIGHT" "1B2373"
    PS_furnBox "lamp" "PS_suite_Furn_lamp_003_L_02" 1 "suite-lamp-003" "none" "none" [190.2820,(-3501.4050)] 0.4420 0.4420 0.981925694 0.189266824 #([190.1068,(-3501.6638)],[190.5408,(-3501.5802)],[190.4572,(-3501.1462)],[190.0232,(-3501.2298)]) "L_02" "Xr_SDC_DD_ID-PRS-Fur$0$L_02" "A-2.Noi That" "1B2338"
    PS_furnBox "lamp" "PS_suite_Furn_lamp_004_table lamp 01" 1 "suite-lamp-004" "suite-coffee-table-002" "coffee-table" [194.6960,(-3504.8690)] 0.1980 0.1980 0.005061433 0.999987191 #([194.7945,(-3504.9685)],[194.7955,(-3504.7705)],[194.5975,(-3504.7695)],[194.5965,(-3504.9675)]) "table lamp 01" "Xr_SDC_DD_ID-PRS-Fur$0$table lamp 01" "A-2.Noi That" "1B2461"
    PS_furnBox "lamp" "PS_suite_Furn_lamp_005_table lamp 01" 1 "suite-lamp-005" "suite-coffee-table-002" "coffee-table" [194.8260,(-3505.0200)] 0.1980 0.1980 0.005061433 0.999987191 #([194.9245,(-3505.1195)],[194.9255,(-3504.9215)],[194.7275,(-3504.9205)],[194.7265,(-3505.1185)]) "table lamp 01" "Xr_SDC_DD_ID-PRS-Fur$0$table lamp 01" "A-2.Noi That" "1B2460"
    PS_furnBox "lamp" "PS_suite_Furn_lamp_006_table lamp 01" 1 "suite-lamp-006" "suite-coffee-table-002" "coffee-table" [194.8770,(-3504.8110)] 0.1980 0.1980 0.005061433 0.999987191 #([194.9755,(-3504.9105)],[194.9765,(-3504.7125)],[194.7785,(-3504.7115)],[194.7775,(-3504.9095)]) "table lamp 01" "Xr_SDC_DD_ID-PRS-Fur$0$table lamp 01" "A-2.Noi That" "1B2462"
    PS_furnBox "lamp" "PS_suite_Furn_lamp_007_wall lamp king top" 1 "suite-lamp-007" "suite-coffee-table-001" "coffee-table" [194.9190,(-3502.2070)] 0.3010 0.2830 (-0.999999863) 0.000523599 #([195.0696,(-3502.0656)],[194.7686,(-3502.0654)],[194.7684,(-3502.3484)],[195.0694,(-3502.3486)]) "wall lamp king top" "Xr_SDC_DD_ID-PRS-Fur$0$wall lamp king top" "A-2.Noi That" "1B245E"
    PS_furnBox "lamp" "PS_suite_Furn_lamp_008_1X-LAMP1" 1 "suite-lamp-008" "suite-table-002" "table" [199.7040,(-3495.7430)] 0.3270 0.3090 0.829720137 0.558179626 #([199.6546,(-3495.9625)],[199.9259,(-3495.7799)],[199.7534,(-3495.5235)],[199.4821,(-3495.7061)]) "1X-LAMP1" "Xr_SDC_DD_ID-PRS-Fur$0$XR_TP FL 8-27 INTERIOR$0$1X-LAMP1" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LEVEL-LIGHT" "1B2375"
    PS_furnBox "lamp" "PS_suite_Furn_lamp_009_1X-LAMP1" 1 "suite-lamp-009" "suite-table-002" "table" [199.7040,(-3494.5680)] 0.3270 0.3090 (-0.829720137) 0.558179626 #([199.9259,(-3494.5311)],[199.6546,(-3494.3485)],[199.4821,(-3494.6049)],[199.7534,(-3494.7875)]) "1X-LAMP1" "Xr_SDC_DD_ID-PRS-Fur$0$XR_TP FL 8-27 INTERIOR$0$1X-LAMP1" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LEVEL-LIGHT" "1B2376"
    PS_furnBox "plant" "PS_suite_Furn_plant_001_jdlkasdjkla" 1 "suite-plant-001" "none" "none" [175.3700,(-3495.4330)] 0.9410 0.9410 0.197828427 0.980236662 #([175.7381,(-3495.9873)],[175.9243,(-3495.0649)],[175.0019,(-3494.8787)],[174.8157,(-3495.8011)]) "jdlkasdjkla" "jdlkasdjkla" "A-4. Cay (goccay)" "1B2296"
    PS_furnBox "plant" "PS_suite_Furn_plant_002_jdlkasdjkla" 1 "suite-plant-002" "none" "none" [175.6770,(-3495.9500)] 0.5400 0.5400 0.197828427 0.980236662 #([175.8883,(-3496.2681)],[175.9951,(-3495.7387)],[175.4657,(-3495.6319)],[175.3589,(-3496.1613)]) "jdlkasdjkla" "jdlkasdjkla" "A-4. Cay (goccay)" "1B2297"
    PS_furnBox "plant" "PS_suite_Furn_plant_003_jdlkasdjkla" 1 "suite-plant-003" "none" "none" [175.7520,(-3492.4490)] 2.2190 2.2190 0.197828427 0.980236662 #([176.6201,(-3493.7561)],[177.0591,(-3491.5809)],[174.8839,(-3491.1419)],[174.4449,(-3493.3171)]) "jdlkasdjkla" "jdlkasdjkla" "A-4. Cay (goccay)" "1B2291"
    PS_furnBox "plant" "PS_suite_Furn_plant_004_jdlkasdjkla" 1 "suite-plant-004" "none" "none" [178.3010,(-3499.4510)] 2.2190 2.2190 0.980236662 0.197828427 #([177.4329,(-3500.7581)],[179.6081,(-3500.3191)],[179.1691,(-3498.1439)],[176.9939,(-3498.5829)]) "jdlkasdjkla" "jdlkasdjkla" "A-4. Cay (goccay)" "1B2292"
    PS_furnBox "plant" "PS_suite_Furn_plant_005_jdlkasdjkla" 1 "suite-plant-005" "none" "none" [178.3660,(-3496.7890)] 0.9410 0.9410 0.980236662 0.197828427 #([177.9979,(-3497.3433)],[178.9203,(-3497.1571)],[178.7341,(-3496.2347)],[177.8117,(-3496.4209)]) "jdlkasdjkla" "jdlkasdjkla" "A-4. Cay (goccay)" "1B2294"
    PS_furnBox "plant" "PS_suite_Furn_plant_006_jdlkasdjkla" 1 "suite-plant-006" "none" "none" [178.8330,(-3497.1140)] 0.5400 0.5400 0.197828427 0.980236662 #([179.0443,(-3497.4321)],[179.1511,(-3496.9027)],[178.6217,(-3496.7959)],[178.5149,(-3497.3253)]) "jdlkasdjkla" "jdlkasdjkla" "A-4. Cay (goccay)" "1B2295"
    PS_furnBox "plant" "PS_suite_Furn_plant_007_jdlkasdjkla" 1 "suite-plant-007" "none" "none" [179.1020,(-3500.7150)] 1.3310 1.3310 0.197828427 0.980236662 #([179.6227,(-3501.4990)],[179.8860,(-3500.1943)],[178.5813,(-3499.9310)],[178.3180,(-3501.2357)]) "jdlkasdjkla" "jdlkasdjkla" "A-4. Cay (goccay)" "1B22A3"
    PS_furnBox "plant" "PS_suite_Furn_plant_008_jdlkasdjkla" 1 "suite-plant-008" "none" "none" [180.7190,(-3484.3210)] 2.2190 2.2190 0.197828427 0.980236662 #([181.5871,(-3485.6281)],[182.0261,(-3483.4529)],[179.8509,(-3483.0139)],[179.4119,(-3485.1891)]) "jdlkasdjkla" "jdlkasdjkla" "A-4. Cay (goccay)" "1B2293"
    PS_furnBox "plant" "PS_suite_Furn_plant_009_jdlkasdjkla" 1 "suite-plant-009" "none" "none" [188.2360,(-3504.7420)] 2.2190 2.2190 0.980236662 0.197828427 #([187.3679,(-3506.0491)],[189.5431,(-3505.6101)],[189.1041,(-3503.4349)],[186.9289,(-3503.8739)]) "jdlkasdjkla" "jdlkasdjkla" "A-4. Cay (goccay)" "1B22A1"
    PS_furnBox "plant" "PS_suite_Furn_plant_010_jdlkasdjkla" 1 "suite-plant-010" "none" "none" [189.1670,(-3505.7140)] 1.3310 1.3310 0.197828427 0.980236662 #([189.6877,(-3506.4980)],[189.9510,(-3505.1933)],[188.6463,(-3504.9300)],[188.3830,(-3506.2347)]) "jdlkasdjkla" "jdlkasdjkla" "A-4. Cay (goccay)" "1B22A2"
    PS_furnBox "plant" "PS_suite_Furn_plant_011_jdlkasdjkla" 1 "suite-plant-011" "none" "none" [190.2010,(-3483.0550)] 1.0650 1.0650 0.980236662 0.197828427 #([189.7844,(-3483.6823)],[190.8283,(-3483.4716)],[190.6176,(-3482.4277)],[189.5737,(-3482.6384)]) "jdlkasdjkla" "jdlkasdjkla" "A-4. Cay (goccay)" "1B22A5"
    PS_furnBox "plant" "PS_suite_Furn_plant_012_jdlkasdjkla" 1 "suite-plant-012" "none" "none" [190.9300,(-3483.0040)] 1.7750 1.7750 0.980236662 0.197828427 #([190.2356,(-3484.0495)],[191.9755,(-3483.6984)],[191.6244,(-3481.9585)],[189.8845,(-3482.3096)]) "jdlkasdjkla" "jdlkasdjkla" "A-4. Cay (goccay)" "1B22A4"
    PS_furnBox "sanitary" "PS_suite_Furn_sanitary_001_sdfhsdfhsdfh" 1 "suite-sanitary-001" "none" "none" [198.2240,(-3503.1680)] 0.4910 0.4800 (-0.693401828) 0.720551112 #([198.5672,(-3503.1785)],[198.2267,(-3502.8247)],[197.8808,(-3503.1575)],[198.2213,(-3503.5113)]) "sdfhsdfhsdfh" "sdfhsdfhsdfh" "A-2.Noi That" "1B23F6"
    PS_furnBox "sanitary" "PS_suite_Furn_sanitary_002_sdfhsdfhsdfh" 1 "suite-sanitary-002" "none" "none" [198.2240,(-3502.2680)] 0.4910 0.4800 0.693401828 0.720551112 #([198.2267,(-3502.6113)],[198.5672,(-3502.2575)],[198.2213,(-3501.9247)],[197.8808,(-3502.2785)]) "sdfhsdfhsdfh" "sdfhsdfhsdfh" "A-2.Noi That" "1B23F7"
    PS_furnBox "sanitary" "PS_suite_Furn_sanitary_003_SmartToilet-Plan" 1 "suite-sanitary-003" "none" "none" [202.4100,(-3502.7090)] 0.6830 0.3660 0.500000000 0.866025404 #([202.3977,(-3503.0962)],[202.7392,(-3502.5048)],[202.4223,(-3502.3218)],[202.0808,(-3502.9132)]) "SmartToilet-Plan" "Xr_SDC_DD_ID-PRS-ID wall$0$SmartToilet-Plan" "Xr_SDC_DD_ID-PRS-ID wall$0$DA-SANR" "1B23FC"
    PS_furnBox "sanitary" "PS_suite_Furn_sanitary_004_chau rua 2 ho" 1 "suite-sanitary-004" "none" "none" [203.8380,(-3489.2910)] 0.7700 0.4400 (-0.500000000) 0.866025404 #([204.2210,(-3489.5144)],[203.8360,(-3488.8476)],[203.4550,(-3489.0676)],[203.8400,(-3489.7344)]) "chau rua 2 ho" "Xr_SDC_DD_ID-PCS-Fur$0$chau rua 2 ho" "Xr_SDC_DD_ID-PCS-Fur$0$DA-SANR-FIXT" "1B232B"
    PS_furnBox "sanitary" "PS_suite_Furn_sanitary_005_sdfhsdfhsdfh" 1 "suite-sanitary-005" "none" "none" [205.2410,(-3498.6120)] 0.4910 0.4800 (-0.240228042) 0.970716482 #([205.5329,(-3498.7927)],[205.4150,(-3498.3160)],[204.9491,(-3498.4313)],[205.0670,(-3498.9080)]) "sdfhsdfhsdfh" "sdfhsdfhsdfh" "A-2.Noi That" "1B23F5"
    PS_furnBox "appliance" "PS_suite_Furn_appliance_001_01.MINIBAR800X600" 1 "suite-appliance-001" "none" "none" [193.9600,(-3499.9320)] 1.9400 0.6500 1.000000000 0.000000000 #([192.9900,(-3500.2570)],[194.9300,(-3500.2570)],[194.9300,(-3499.6070)],[192.9900,(-3499.6070)]) "01.MINIBAR800X600" "Xr_SDC_DD_ID-PRS-Fur$0$01.MINIBAR800X600" "A-2.Noi That" "1B22FE"
    PS_furnBox "appliance" "PS_suite_Furn_appliance_002_A$C632aa080" 1 "suite-appliance-002" "none" "none" [202.6080,(-3491.2200)] 0.5900 0.5200 (-0.500000000) 0.866025404 #([202.9807,(-3491.3455)],[202.6857,(-3490.8345)],[202.2353,(-3491.0945)],[202.5303,(-3491.6055)]) "A$C632aa080" "Xr_SDC_DD_ID-PCS-Fur$0$A$C632aa080" "Xr_SDC_DD_ID-PCS-Fur$0$DA-SANR-FIXT" "1B232C"
    PS_furnBox "bed" "PS_suite_Furn_bed_001_SDC_MUR.BED KING PLAN" 1 "suite-bed-001" "none" "none" [194.0120,(-3503.5750)] 2.1250 2.0400 1.000000000 0.000000000 #([192.9495,(-3504.5950)],[195.0745,(-3504.5950)],[195.0745,(-3502.5550)],[192.9495,(-3502.5550)]) "SDC_MUR.BED KING PLAN" "Xr_SDC_DD_ID-PRS-Fur$0$SDC_MUR.BED KING PLAN" "A-2.Noi That" "1B2464"
    PS_furnBox "seat" "PS_suite_Furn_seat_001_SDC_JUNIOR SUITE_DINING CHAIR-PLAN" 1 "suite-seat-001" "none" "none" [190.3450,(-3487.3050)] 0.7980 0.6710 (-0.775826212) 0.630946660 #([190.8662,(-3487.2965)],[190.2471,(-3486.7930)],[189.8238,(-3487.3135)],[190.4429,(-3487.8170)]) "SDC_JUNIOR SUITE_DINING CHAIR-PLAN" "Xr_SDC_DD_ID-PRS-Fur$0$Xr_SDC_DD_ID-MUR.JS-Furniture$0$SDC_JUNIOR SUITE_DINING CHAIR-PLAN" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LOOSE-FURN" "1B328C"
    PS_furnBox "seat" "PS_suite_Furn_seat_002_A$C1919ec32" 1 "suite-seat-002" "none" "none" [192.5250,(-3503.5780)] 1.8000 0.6000 0.000000000 1.000000000 #([192.8250,(-3504.4780)],[192.8250,(-3502.6780)],[192.2250,(-3502.6780)],[192.2250,(-3504.4780)]) "A$C1919ec32" "Xr_SDC_DD_ID-PRS-Fur$0$A$C1919ec32" "A-2.Noi That" "1B2465"
    PS_furnBox "seat" "PS_suite_Furn_seat_003_dining chair RS01" 1 "suite-seat-003" "none" "none" [194.6880,(-3496.3080)] 0.6050 0.6010 0.000000000 1.000000000 #([194.9885,(-3496.6105)],[194.9885,(-3496.0055)],[194.3875,(-3496.0055)],[194.3875,(-3496.6105)]) "dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LOOSE-FURN" "1B237F"
    PS_furnBox "seat" "PS_suite_Furn_seat_004_dining chair RS01" 1 "suite-seat-004" "none" "none" [194.6880,(-3494.0030)] 0.6050 0.6010 0.000000000 1.000000000 #([194.9885,(-3494.3055)],[194.9885,(-3493.7005)],[194.3875,(-3493.7005)],[194.3875,(-3494.3055)]) "dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LOOSE-FURN" "1B2384"
    PS_furnBox "seat" "PS_suite_Furn_seat_005_dining chair RS01" 1 "suite-seat-005" "none" "none" [195.4880,(-3496.3080)] 0.6050 0.6010 0.000000000 1.000000000 #([195.7885,(-3496.6105)],[195.7885,(-3496.0055)],[195.1875,(-3496.0055)],[195.1875,(-3496.6105)]) "dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LOOSE-FURN" "1B237E"
    PS_furnBox "seat" "PS_suite_Furn_seat_006_dining chair RS01" 1 "suite-seat-006" "none" "none" [195.4880,(-3494.0030)] 0.6050 0.6010 0.000000000 1.000000000 #([195.7885,(-3494.3055)],[195.7885,(-3493.7005)],[195.1875,(-3493.7005)],[195.1875,(-3494.3055)]) "dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LOOSE-FURN" "1B2383"
    PS_furnBox "seat" "PS_suite_Furn_seat_007_chair 1 1" 1 "suite-seat-007" "none" "none" [196.1030,(-3503.5180)] 0.5460 0.5000 1.000000000 0.000000000 #([195.8300,(-3503.7680)],[196.3760,(-3503.7680)],[196.3760,(-3503.2680)],[195.8300,(-3503.2680)]) "chair 1 1" "chair 1 1" "A-2.Noi That" "1B2300"
    PS_furnBox "seat" "PS_suite_Furn_seat_008_dining chair RS01" 1 "suite-seat-008" "none" "none" [196.2880,(-3496.3080)] 0.6050 0.6010 0.000000000 1.000000000 #([196.5885,(-3496.6105)],[196.5885,(-3496.0055)],[195.9875,(-3496.0055)],[195.9875,(-3496.6105)]) "dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LOOSE-FURN" "1B237D"
    PS_furnBox "seat" "PS_suite_Furn_seat_009_dining chair RS01" 1 "suite-seat-009" "none" "none" [196.2880,(-3494.0030)] 0.6050 0.6010 0.000000000 1.000000000 #([196.5885,(-3494.3055)],[196.5885,(-3493.7005)],[195.9875,(-3493.7005)],[195.9875,(-3494.3055)]) "dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LOOSE-FURN" "1B2382"
    PS_furnBox "seat" "PS_suite_Furn_seat_010_dining chair RS01" 1 "suite-seat-010" "none" "none" [197.0880,(-3496.3080)] 0.6050 0.6010 0.000000000 1.000000000 #([197.3885,(-3496.6105)],[197.3885,(-3496.0055)],[196.7875,(-3496.0055)],[196.7875,(-3496.6105)]) "dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LOOSE-FURN" "1B237C"
    PS_furnBox "seat" "PS_suite_Furn_seat_011_dining chair RS01" 1 "suite-seat-011" "none" "none" [197.0880,(-3494.0030)] 0.6050 0.6010 0.000000000 1.000000000 #([197.3885,(-3494.3055)],[197.3885,(-3493.7005)],[196.7875,(-3493.7005)],[196.7875,(-3494.3055)]) "dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LOOSE-FURN" "1B2381"
    PS_furnBox "seat" "PS_suite_Furn_seat_012_dining chair RS01" 1 "suite-seat-012" "none" "none" [197.8880,(-3496.3080)] 0.6050 0.6010 0.000000000 1.000000000 #([198.1885,(-3496.6105)],[198.1885,(-3496.0055)],[197.5875,(-3496.0055)],[197.5875,(-3496.6105)]) "dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LOOSE-FURN" "1B237B"
    PS_furnBox "seat" "PS_suite_Furn_seat_013_dining chair RS01" 1 "suite-seat-013" "none" "none" [197.8880,(-3494.0030)] 0.6050 0.6010 0.000000000 1.000000000 #([198.1885,(-3494.3055)],[198.1885,(-3493.7005)],[197.5875,(-3493.7005)],[197.5875,(-3494.3055)]) "dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LOOSE-FURN" "1B2380"
    PS_furnBox "seat" "PS_suite_Furn_seat_014_dining chair RS01" 1 "suite-seat-014" "none" "none" [198.7510,(-3495.1560)] 0.7260 0.7210 1.000000000 0.000000000 #([198.3880,(-3495.5165)],[199.1140,(-3495.5165)],[199.1140,(-3494.7955)],[198.3880,(-3494.7955)]) "dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$dining chair RS01" "Xr_SDC_DD_ID-PRS-Fur$0$DA-LOOSE-FURN" "1B2385"
    PS_furnBox "sofa" "PS_suite_Furn_sofa_001_sofa 1 1" 1 "suite-sofa-001" "none" "none" [189.0990,(-3502.5010)] 2.1870 1.2920 0.608899886 0.793247079 #([188.9456,(-3503.7618)],[190.2773,(-3502.0269)],[189.2524,(-3501.2402)],[187.9207,(-3502.9751)]) "sofa 1 1" "sofa 1 1" "A-2.Noi That" "1B2345"
    PS_furnBox "sofa" "PS_suite_Furn_sofa_002_sdhsdfhsdfh" 1 "suite-sofa-002" "none" "none" [189.3030,(-3498.0470)] 3.5080 1.5690 0.999769581 0.021465901 #([187.5662,(-3498.8690)],[191.0734,(-3498.7937)],[191.0398,(-3497.2250)],[187.5326,(-3497.3003)]) "sdhsdfhsdfh" "sdhsdfhsdfh" "A-2.Noi That" "1B236D"
    PS_furnBox "sofa" "PS_suite_Furn_sofa_003_sdhsdfhsdfh" 1 "suite-sofa-003" "none" "none" [189.3030,(-3492.1630)] 3.5080 1.5690 (-0.999769581) 0.021465901 #([191.0734,(-3491.4163)],[187.5662,(-3491.3410)],[187.5326,(-3492.9097)],[191.0398,(-3492.9850)]) "sdhsdfhsdfh" "sdhsdfhsdfh" "A-2.Noi That" "1B237A"
    PS_furnBox "sofa" "PS_suite_Furn_sofa_004_A$Cfa141486" 1 "suite-sofa-004" "none" "none" [190.7950,(-3485.9030)] 2.3410 2.2150 (-0.998601995) 0.052858830 #([192.0224,(-3484.8589)],[189.6847,(-3484.7352)],[189.5676,(-3486.9471)],[191.9053,(-3487.0708)]) "A$Cfa141486" "A$Cfa141486" "A-4. Dim" "1B243C"
    PS_furnBox "sofa" "PS_suite_Furn_sofa_005_TZSUCAI-30+ 53" 1 "suite-sofa-005" "none" "none" [191.9680,(-3496.5090)] 1.3320 1.1810 (-0.899710197) 0.436487757 #([192.8250,(-3496.2684)],[191.6265,(-3495.6870)],[191.1110,(-3496.7496)],[192.3095,(-3497.3310)]) "TZSUCAI-30+ 53" "TZSUCAI-30+ 53" "A-2.Noi That" "1B236E"
    PS_furnBox "sofa" "PS_suite_Furn_sofa_006_A$C2b06494e" 1 "suite-sofa-006" "none" "none" [196.9520,(-3487.0380)] 5.9910 0.7460 0.000000000 1.000000000 #([197.3250,(-3490.0335)],[197.3250,(-3484.0425)],[196.5790,(-3484.0425)],[196.5790,(-3490.0335)]) "A$C2b06494e" "A$C2b06494e" "A-2.Noi That" "1B23B7"
    PS_furnBox "sofa" "PS_suite_Furn_sofa_007_A$Cfa141486" 1 "suite-sofa-007" "none" "none" [198.1820,(-3488.0250)] 2.3410 2.2150 0.544785402 0.838575498 #([198.4731,(-3489.6099)],[199.7484,(-3487.6468)],[197.8909,(-3486.4401)],[196.6156,(-3488.4032)]) "A$Cfa141486" "A$Cfa141486" "A-4. Dim" "1B23BC"
    PS_furnBox "table" "PS_suite_Furn_table_001_A$Cf34708b2" 1 "suite-table-001" "none" "none" [194.9170,(-3487.0480)] 2.5360 2.5310 (-0.708093399) 0.706118785 #([196.7085,(-3487.0473)],[194.9127,(-3485.2565)],[193.1255,(-3487.0487)],[194.9213,(-3488.8395)]) "A$Cf34708b2" "A$Cf34708b2" "A-2.Noi That" "1B23BB"
    PS_furnBox "table" "PS_suite_Furn_table_002_CONSOLE TABLE - PLAN" 1 "suite-table-002" "none" "none" [199.7190,(-3495.1560)] 1.8000 0.3500 0.000000000 1.000000000 #([199.8940,(-3496.0560)],[199.8940,(-3494.2560)],[199.5440,(-3494.2560)],[199.5440,(-3496.0560)]) "CONSOLE TABLE - PLAN" "Xr_SDC_DD_ID-PRS-Fur$0$CONSOLE TABLE - PLAN" "A-2.Noi That" "1B2374"
    PS_furnBox "coffee-table" "PS_suite_Furn_coffee-table_001_1 BEDSIDE TABLE - PLAN" 1 "suite-coffee-table-001" "none" "none" [194.7530,(-3502.1970)] 0.4900 0.4900 0.980236662 0.197828427 #([194.5613,(-3502.4856)],[195.0416,(-3502.3887)],[194.9447,(-3501.9084)],[194.4644,(-3502.0053)]) "1 BEDSIDE TABLE - PLAN" "Xr_SDC_DD_ID-PRS-Fur$0$1 BEDSIDE TABLE - PLAN" "A-2.Noi That" "1B05B7"
    PS_furnBox "coffee-table" "PS_suite_Furn_coffee-table_002_nightstand 01" 1 "suite-coffee-table-002" "none" "none" [194.7540,(-3504.8950)] 0.5000 0.4990 (-0.999987191) 0.005061433 #([195.0053,(-3504.6468)],[194.5053,(-3504.6442)],[194.5027,(-3505.1432)],[195.0027,(-3505.1458)]) "nightstand 01" "Xr_SDC_DD_ID-PRS-Fur$0$nightstand 01" "A-2.Noi That" "1B245F"
    PS_furnBox "tall-cabinet" "PS_suite_Furn_tall-cabinet_001_*U1637" 1 "suite-tall-cabinet-001" "none" "none" [195.5700,(-3504.8000)] 0.8770 0.6800 0.000000000 1.000000000 #([195.9100,(-3505.2385)],[195.9100,(-3504.3615)],[195.2300,(-3504.3615)],[195.2300,(-3505.2385)]) "*U1637" "*U1637" "A-2.Noi That" "1B24BC"
    PS_furnBox "tall-cabinet" "PS_suite_Furn_tall-cabinet_002_*U1637" 1 "suite-tall-cabinet-002" "none" "none" [195.5700,(-3502.2370)] 0.8770 0.6800 0.000000000 1.000000000 #([195.9100,(-3502.6755)],[195.9100,(-3501.7985)],[195.2300,(-3501.7985)],[195.2300,(-3502.6755)]) "*U1637" "*U1637" "A-2.Noi That" "1B24B4"
    PS_furnBox "tall-cabinet" "PS_suite_Furn_tall-cabinet_003_*U1636" 1 "suite-tall-cabinet-003" "none" "none" [197.3500,(-3503.5180)] 3.4400 0.6800 0.000000000 1.000000000 #([197.6900,(-3505.2380)],[197.6900,(-3501.7980)],[197.0100,(-3501.7980)],[197.0100,(-3505.2380)]) "*U1636" "*U1636" "A-2.Noi That" "1B246E"
    PS_furnBox "other" "PS_suite_Furn_other_001_loose shapes on A-2.Noi That" 1 "suite-other-001" "none" "none" [178.3400,(-3494.8060)] 0.8400 0.7000 1.000000000 0.000000000 #([177.9200,(-3495.1560)],[178.7600,(-3495.1560)],[178.7600,(-3494.4560)],[177.9200,(-3494.4560)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_002_loose shapes on A-2.Noi That" 1 "suite-other-002" "none" "none" [178.3400,(-3494.1560)] 3.7600 1.0000 0.000000000 1.000000000 #([178.8400,(-3496.0360)],[178.8400,(-3492.2760)],[177.8400,(-3492.2760)],[177.8400,(-3496.0360)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_003_loose shapes on A-2.Noi That" 1 "suite-other-003" "none" "none" [178.3400,(-3493.5060)] 0.8400 0.7000 1.000000000 0.000000000 #([177.9200,(-3493.8560)],[178.7600,(-3493.8560)],[178.7600,(-3493.1560)],[177.9200,(-3493.1560)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_004_loose shapes on A-2.Noi That" 1 "suite-other-004" "none" "none" [183.5360,(-3503.1290)] 4.0230 1.9000 1.000000000 0.000000000 #([181.5245,(-3504.0790)],[185.5475,(-3504.0790)],[185.5475,(-3502.1790)],[181.5245,(-3502.1790)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_005_loose shapes on A-2.Noi That" 1 "suite-other-005" "none" "none" [186.4160,(-3495.1510)] 2.0000 0.5500 0.000000000 1.000000000 #([186.6910,(-3496.1510)],[186.6910,(-3494.1510)],[186.1410,(-3494.1510)],[186.1410,(-3496.1510)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_006_loose shapes on A-2.Noi That" 1 "suite-other-006" "none" "none" [188.2200,(-3502.5590)] 0.2890 0.2890 0.980236662 0.197828427 #([188.1069,(-3502.7292)],[188.3902,(-3502.6721)],[188.3331,(-3502.3888)],[188.0498,(-3502.4459)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_007_loose shapes on A-2.Noi That" 1 "suite-other-007" "none" "none" [189.1270,(-3495.0320)] 2.4080 1.6770 0.999999619 0.000872665 #([187.9237,(-3495.8716)],[190.3317,(-3495.8694)],[190.3303,(-3494.1924)],[187.9223,(-3494.1946)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_008_loose shapes on A-2.Noi That" 1 "suite-other-008" "none" "none" [189.2740,(-3493.0600)] 0.8150 0.8150 0.197828427 0.980236662 #([189.5928,(-3493.5401)],[189.7541,(-3492.7412)],[188.9552,(-3492.5799)],[188.7939,(-3493.3788)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_009_loose shapes on A-2.Noi That" 1 "suite-other-009" "none" "none" [189.3190,(-3497.2720)] 0.8150 0.8150 0.980236662 0.197828427 #([189.0002,(-3497.7521)],[189.7991,(-3497.5908)],[189.6378,(-3496.7919)],[188.8389,(-3496.9532)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_010_loose shapes on A-2.Noi That" 1 "suite-other-010" "none" "none" [189.8880,(-3503.0750)] 0.9080 0.6010 0.444635179 0.895711760 #([189.9553,(-3503.6153)],[190.3590,(-3502.8020)],[189.8207,(-3502.5347)],[189.4170,(-3503.3480)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_011_loose shapes on A-2.Noi That" 1 "suite-other-011" "none" "none" [190.1160,(-3502.3130)] 0.3490 0.3490 0.980236662 0.197828427 #([189.9795,(-3502.5186)],[190.3216,(-3502.4495)],[190.2525,(-3502.1074)],[189.9104,(-3502.1765)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_012_*U1315" 1 "suite-other-012" "none" "none" [190.2850,(-3505.6150)] 1.6000 0.4000 (-0.866025404) 0.500000000 #([191.0778,(-3505.8418)],[189.6922,(-3505.0418)],[189.4922,(-3505.3882)],[190.8778,(-3506.1882)]) "*U1315" "*U1315" "A-2.Noi That" "1B22F3"
    PS_furnBox "other" "PS_suite_Furn_other_013_loose shapes on A-2.Noi That" 1 "suite-other-013" "none" "none" [191.1570,(-3493.2300)] 0.4510 0.4510 0.980236662 0.197828427 #([190.9806,(-3493.4957)],[191.4227,(-3493.4064)],[191.3334,(-3492.9643)],[190.8913,(-3493.0536)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_014_3 3" 1 "suite-other-014" "none" "none" [191.7020,(-3493.7100)] 0.8900 0.8010 0.745708618 0.666272209 #([191.6370,(-3494.3051)],[192.3007,(-3493.7122)],[191.7670,(-3493.1149)],[191.1033,(-3493.7078)]) "3 3" "3 3" "A-2.Noi That" "1B244C"
    PS_furnBox "other" "PS_suite_Furn_other_015_*U1025" 1 "suite-other-015" "none" "none" [192.1170,(-3504.1400)] 0.4900 0.4900 0.197828427 0.980236662 #([192.3087,(-3504.4286)],[192.4056,(-3503.9483)],[191.9253,(-3503.8514)],[191.8284,(-3504.3317)]) "*U1025" "*U1025" "A-2.Noi That" "1B2466"
    PS_furnBox "other" "PS_suite_Furn_other_016_loose shapes on A-2.Noi That" 1 "suite-other-016" "none" "none" [192.3080,(-3495.6890)] 0.4510 0.4510 0.197828427 0.980236662 #([192.4844,(-3495.9547)],[192.5737,(-3495.5126)],[192.1316,(-3495.4233)],[192.0423,(-3495.8654)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_017_A$C17cdd4d6" 1 "suite-other-017" "none" "none" [194.0610,(-3499.2630)] 1.5000 0.3500 1.000000000 0.000000000 #([193.3110,(-3499.4380)],[194.8110,(-3499.4380)],[194.8110,(-3499.0880)],[193.3110,(-3499.0880)]) "A$C17cdd4d6" "A$C17cdd4d6" "A-2.Noi That" "1B248F"
    PS_furnBox "other" "PS_suite_Furn_other_018_A$C17cdd4d6" 1 "suite-other-018" "none" "none" [194.0610,(-3491.0480)] 1.5000 0.3500 1.000000000 0.000000000 #([193.3110,(-3491.2230)],[194.8110,(-3491.2230)],[194.8110,(-3490.8730)],[193.3110,(-3490.8730)]) "A$C17cdd4d6" "A$C17cdd4d6" "A-2.Noi That" "1B8E5C"
    PS_furnBox "other" "PS_suite_Furn_other_019_loose shapes on A-2.Noi That" 1 "suite-other-019" "none" "none" [194.8000,(-3503.5180)] 3.6000 0.7000 0.000000000 1.000000000 #([195.1500,(-3505.3180)],[195.1500,(-3501.7180)],[194.4500,(-3501.7180)],[194.4500,(-3505.3180)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_020_loose shapes on A-2.Noi That" 1 "suite-other-020" "none" "none" [195.5700,(-3503.5180)] 3.4400 0.6800 0.000000000 1.000000000 #([195.9100,(-3505.2380)],[195.9100,(-3501.7980)],[195.2300,(-3501.7980)],[195.2300,(-3505.2380)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_021_loose shapes on A-2.Noi That" 1 "suite-other-021" "none" "none" [196.2880,(-3495.1560)] 4.0000 1.5000 1.000000000 0.000000000 #([194.2880,(-3495.9060)],[198.2880,(-3495.9060)],[198.2880,(-3494.4060)],[194.2880,(-3494.4060)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_022_loose shapes on A-2.Noi That" 1 "suite-other-022" "none" "none" [198.1700,(-3502.7180)] 2.0000 0.6000 0.000000000 1.000000000 #([198.4700,(-3503.7180)],[198.4700,(-3501.7180)],[197.8700,(-3501.7180)],[197.8700,(-3503.7180)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_023_A$Ccffa946e" 1 "suite-other-023" "none" "none" [198.5730,(-3500.1600)] 1.5380 1.0760 0.976030848 0.217632223 #([197.9395,(-3500.8525)],[199.4407,(-3500.5177)],[199.2065,(-3499.4675)],[197.7053,(-3499.8023)]) "A$Ccffa946e" "A$Ccffa946e" "A-4. Dim" "1B8E5A"
    PS_furnBox "other" "PS_suite_Furn_other_024_loose shapes on A-2.Noi That" 1 "suite-other-024" "none" "none" [199.6700,(-3505.6680)] 2.5000 1.4000 1.000000000 0.000000000 #([198.4200,(-3506.3680)],[200.9200,(-3506.3680)],[200.9200,(-3504.9680)],[198.4200,(-3504.9680)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_025_loose shapes on A-2.Noi That" 1 "suite-other-025" "none" "none" [199.8620,(-3496.1100)] 0.2760 0.0940 0.636212884 0.771513555 #([199.8105,(-3496.2464)],[199.9861,(-3496.0334)],[199.9135,(-3495.9736)],[199.7379,(-3496.1866)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_026_loose shapes on A-2.Noi That" 1 "suite-other-026" "none" "none" [199.8620,(-3494.2010)] 0.2760 0.0940 (-0.636212884) 0.771513555 #([199.9861,(-3494.2776)],[199.8105,(-3494.0646)],[199.7379,(-3494.1244)],[199.9135,(-3494.3374)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_027_loose shapes on A-2.Noi That" 1 "suite-other-027" "none" "none" [199.8770,(-3499.9050)] 1.4000 0.2500 0.500000000 0.866025404 #([199.6353,(-3500.5737)],[200.3353,(-3499.3613)],[200.1187,(-3499.2363)],[199.4187,(-3500.4487)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_028_loose shapes on A-2.Noi That" 1 "suite-other-028" "none" "none" [200.5460,(-3498.9570)] 0.2940 0.2940 0.980236662 0.197828427 #([200.4310,(-3499.1302)],[200.7192,(-3499.0720)],[200.6610,(-3498.7838)],[200.3728,(-3498.8420)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_029_loose shapes on A-2.Noi That" 1 "suite-other-029" "none" "none" [200.8430,(-3492.0730)] 1.5000 0.6000 (-0.500000000) 0.866025404 #([201.4778,(-3492.5725)],[200.7278,(-3491.2735)],[200.2082,(-3491.5735)],[200.9582,(-3492.8725)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_030_*U1448" 1 "suite-other-030" "none" "none" [201.5800,(-3487.7660)] 1.8000 0.7000 0.866025404 0.500000000 #([200.9756,(-3488.5191)],[202.5344,(-3487.6191)],[202.1844,(-3487.0129)],[200.6256,(-3487.9129)]) "*U1448" "*U1448" "A-2.Noi That" "1B243D"
    PS_furnBox "other" "PS_suite_Furn_other_031_loose shapes on A-2.Noi That" 1 "suite-other-031" "none" "none" [202.2400,(-3491.7380)] 2.2820 0.3500 (-0.500000000) 0.866025404 #([202.9621,(-3492.6386)],[201.8211,(-3490.6624)],[201.5179,(-3490.8374)],[202.6589,(-3492.8136)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_032_loose shapes on A-2.Noi That" 1 "suite-other-032" "none" "none" [202.8890,(-3488.9950)] 2.6880 1.9350 (-0.981760154) 0.190123644 #([204.3924,(-3488.3007)],[201.7535,(-3487.7896)],[201.3856,(-3489.6893)],[204.0245,(-3490.2004)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_033_*U1665" 1 "suite-other-033" "none" "none" [203.2580,(-3501.2400)] 1.4000 0.0850 (-0.866025404) 0.500000000 #([203.8855,(-3501.5532)],[202.6730,(-3500.8532)],[202.6305,(-3500.9268)],[203.8430,(-3501.6268)]) "*U1665" "*U1665" "A-2.Noi That" "1B24FD"
    PS_furnBox "other" "PS_suite_Furn_other_034_*U1664" 1 "suite-other-034" "none" "none" [203.4040,(-3500.9860)] 1.4000 0.5000 (-0.866025404) 0.500000000 #([204.1352,(-3501.1195)],[202.9228,(-3500.4195)],[202.6728,(-3500.8525)],[203.8852,(-3501.5525)]) "*U1664" "*U1664" "A-2.Noi That" "1B24F3"
    PS_furnBox "other" "PS_suite_Furn_other_035_*U1666" 1 "suite-other-035" "none" "none" [203.6540,(-3500.5530)] 1.4000 0.5000 (-0.866025404) 0.500000000 #([204.3852,(-3500.6865)],[203.1728,(-3499.9865)],[202.9228,(-3500.4195)],[204.1352,(-3501.1195)]) "*U1666" "*U1666" "A-2.Noi That" "1B24E9"
    PS_furnBox "other" "PS_suite_Furn_other_036_grgr" 1 "suite-other-036" "none" "none" [203.7100,(-3497.7570)] 2.1000 0.8000 (-0.866025404) 0.500000000 #([204.8193,(-3497.9356)],[203.0007,(-3496.8856)],[202.6007,(-3497.5784)],[204.4193,(-3498.6284)]) "grgr" "grgr" "A-2.Noi That" "1B225C"
    PS_furnBox "other" "PS_suite_Furn_other_037_loose shapes on A-2.Noi That" 1 "suite-other-037" "none" "none" [204.3360,(-3493.4360)] 0.7300 0.4200 1.000000000 0.000000000 #([203.9710,(-3493.6460)],[204.7010,(-3493.6460)],[204.7010,(-3493.2260)],[203.9710,(-3493.2260)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_038_loose shapes on A-2.Noi That" 1 "suite-other-038" "none" "none" [204.6380,(-3499.8220)] 0.2940 0.2940 0.197828427 0.980236662 #([204.7530,(-3499.9952)],[204.8112,(-3499.7070)],[204.5230,(-3499.6488)],[204.4648,(-3499.9370)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_039_loose shapes on A-2.Noi That" 1 "suite-other-039" "none" "none" [204.7070,(-3490.5680)] 0.9000 0.3000 (-0.503773977) 0.863835505 #([205.0633,(-3490.8812)],[204.6099,(-3490.1037)],[204.3507,(-3490.2548)],[204.8041,(-3491.0323)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_040_loose shapes on A-2.Noi That" 1 "suite-other-040" "none" "none" [205.2380,(-3498.6100)] 1.2000 0.6000 0.500000000 0.866025404 #([205.1978,(-3499.2796)],[205.7978,(-3498.2404)],[205.2782,(-3497.9404)],[204.6782,(-3498.9796)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
    PS_furnBox "other" "PS_suite_Furn_other_041_loose shapes on A-2.Noi That" 1 "suite-other-041" "none" "none" [205.6660,(-3497.9520)] 0.2940 0.2940 0.980236662 0.197828427 #([205.5510,(-3498.1252)],[205.8392,(-3498.0670)],[205.7810,(-3497.7788)],[205.4928,(-3497.8370)]) "loose shapes on A-2.Noi That" "none" "A-2.Noi That" "none"
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
    PS_part #wall "PS_Wall_001" #(#([(-2.2215),(-3.2675)],[(-2.1045),(-3.2915)],[(-2.0095),(-3.3555)],[(-1.9455),(-3.4505)],[(-1.9215),(-3.5675)],[(-1.9455),(-3.6845)],[(-2.0095),(-3.7795)],[(-2.1045),(-3.8445)],[(-2.2215),(-3.8675)],[(-2.2215),(-4.3125)],[(-2.6735),(-5.0955)],[(-2.4555),(-5.2215)],[2.6735,3.6615],[2.4555,3.7875],[2.3805,3.6585],[0.7525,4.5985],[1.0665,5.1415],[1.1485,5.1415],[1.1485,5.2215],[(-0.7975),5.2215],[(-0.7975),5.1415],[(-0.3485),5.1415],[0.1355,4.8625],[0.2855,5.1215],[0.7755,4.8385],[0.6255,4.5795],[2.3405,3.5895],[1.2705,1.7365],[(-0.0105),2.4765],[(-0.1005),2.3205],[(-0.0305),2.2805],[0.0195,2.3665],[1.2305,1.6675],[0.1505,(-0.2045)],[(-1.0615),0.4955],[(-0.4055),1.6305],[(-0.4755),1.6705],[(-1.2205),0.3795],[(-1.1515),0.3395],[(-1.1015),0.4265],[0.1105,(-0.2735)],[(-0.6735),(-1.6305)],[(-0.7635),(-1.7105)],[(-0.8655),(-1.7735)],[(-1.0905),(-1.8445)],[(-1.3255),(-1.8395)],[(-1.4415),(-1.8075)],[(-1.5525),(-1.7555)],[(-1.6535),(-1.6855)],[(-1.7385),(-1.6005)],[(-1.8605),(-1.3995)],[(-1.9115),(-1.1695)],[(-1.9085),(-1.0495)],[(-1.8835),(-0.9295)],[(-1.6015),(-0.4395)],[(-1.6705),(-0.3995)],[(-2.2215),(-1.3545)]),#([(-1.0445),(-2.2735)],[(-1.4895),(-3.0445)],[(-2.0415),(-3.0445)],[(-2.0415),(-1.6985)])) 0.0000 3.0000 true [203.6915,(-3501.4225)] [201.0180,(-3506.6440)] [206.3650,(-3496.2010)]
    PS_part #wall "PS_Wall_002" #(#([0.2290,(-0.3420)],[0.4490,(-0.4690)],[0.7790,0.1000],[0.7340,0.1260],[0.7340,0.4690],[0.5540,0.4690],[0.5540,0.2240],[(-0.7790),0.2240],[(-0.7790),0.1440],[0.2290,0.1440])) 0.0000 3.0000 true [206.4190,(-3496.4250)] [205.6400,(-3496.8940)] [207.1980,(-3495.9560)]
    PS_part #wall "PS_Wall_003" #(#([(-4.0825),(-1.7185)],[(-4.0835),(-1.7985)],[(-3.2525),(-1.7985)],[(-3.2525),(-1.5565)],[(-3.6685),(-0.8365)],[(-2.1525),0.0385],[(-1.7025),(-0.7415)],[(-1.6335),(-0.7015)],[(-2.0835),0.0785],[0.1935,1.3925],[1.4745,(-0.8265)],[0.9555,(-1.1255)],[0.9955,(-1.1945)],[1.5145,(-0.8955)],[3.6065,(-4.5195)],[3.6065,(-4.9565)],[3.3705,(-4.9565)],[3.3705,(-5.0365)],[3.9035,(-5.0365)],[3.9035,(-5.2815)],[4.0835,(-5.2815)],[4.0835,(-4.8255)],[4.0745,(-4.8255)],[(-0.2255),2.6225],[0.7965,3.2125],[(-0.3995),5.2815],[(-0.6075),5.2815],[0.5485,3.2795],[(-0.5345),2.6535],[0.1035,1.5485],[(-3.8645),(-0.7425)],[(-3.8645),(-1.7185)])) 0.0000 3.0000 true [203.0695,(-3489.0745)] [198.9860,(-3494.3560)] [207.1530,(-3483.7930)]
    PS_part #wall "PS_Wall_004" #(#([(-1.8315),(-1.7840)],[(-1.8315),(-2.0290)],[(-1.6515),(-2.0290)],[(-1.6515),(-1.7840)],[(-0.2945),(-1.7840)],[(-0.2945),(-1.6040)],[(-0.6945),(-1.6040)],[(-0.6945),(-0.6140)],[1.2055,(-0.6140)],[1.2055,(-1.6040)],[0.5055,(-1.6040)],[0.5055,(-1.7840)],[2.1445,(-1.7840)],[2.1445,(-1.7040)],[2.1015,(-1.7040)],[1.9945,(-1.5290)],[1.7395,(-1.6860)],[1.4255,(-1.1740)],[1.6815,(-1.0180)],[1.1905,(-0.2190)],[0.8875,(-0.3940)],[0.5365,0.2140],[0.8395,0.3890],[0.4995,0.9780],[0.4305,0.9380],[0.7305,0.4190],[(-0.4385),(-0.2560)],[(-1.5445),1.6590],[(-1.0245),1.9590],[(-1.0645),2.0290],[(-1.6535),1.6890],[(-0.5075),(-0.2960)],[(-1.0995),(-0.6380)],[(-0.9245),(-0.9410)],[(-1.7095),(-1.3950)],[(-1.8845),(-1.0910)],[(-2.1445),(-1.2410)])) 0.0000 3.0000 true [203.4955,(-3492.3270)] [201.3510,(-3494.3560)] [205.6400,(-3490.2980)]
    PS_part #wall "PS_Wall_005" #(#([(-0.5885),(-1.8595)],[0.9065,(-2.7145)],[1.2185,(-2.1675)],[1.1495,(-2.1275)],[0.8745,(-2.6035)],[(-0.3375),(-1.9035)],[(-0.3775),(-1.8745)],[(-0.4115),(-1.8395)],[(-0.4375),(-1.7985)],[(-0.4545),(-1.7525)],[(-0.4625),(-1.7045)],[(-0.4615),(-1.6555)],[(-0.4505),(-1.6085)],[(-0.4305),(-1.5635)],[0.0205,(-0.7825)],[0.0865,(-0.7075)],[0.1725,(-0.6655)],[0.2685,(-0.6595)],[0.3625,(-0.6905)],[1.5745,(-1.3905)],[1.5245,(-1.4775)],[1.5935,(-1.5175)],[1.8095,(-1.1435)],[1.7405,(-1.1035)],[1.6905,(-1.1895)],[0.2615,(-0.3645)],[1.1215,1.1245],[2.5505,0.2995],[2.1155,(-0.4535)],[2.1855,(-0.4935)],[2.6595,0.3295],[1.1615,1.1945],[1.7795,2.2645],[1.8205,2.3175],[1.8715,2.3565],[1.9315,2.3815],[1.9965,2.3895],[2.0705,2.3895],[2.0705,2.4695],[1.8705,2.4695],[1.8705,2.7145],[1.6905,2.7145],[1.6905,2.4695],[(-0.1785),(-0.7675)],[(-1.8835),(-0.7675)],[(-2.0395),(-0.7995)],[(-2.1665),(-0.8845)],[(-2.2525),(-1.0115)],[(-2.2835),(-1.1675)],[(-2.2835),(-1.7675)],[(-2.6595),(-1.7675)],[(-2.6595),(-1.8475)],[(-2.1035),(-1.8475)],[(-2.1035),(-1.1675)],[(-2.0865),(-1.0815)],[(-2.0395),(-1.0125)],[(-1.9695),(-0.9645)],[(-1.8835),(-0.9475)],[(-0.8095),(-0.9475)],[(-0.7245),(-0.9645)],[(-0.6545),(-1.0115)],[(-0.6075),(-1.0815)],[(-0.5905),(-1.1665)])) 0.0000 3.0000 true [199.9735,(-3498.6705)] [197.3140,(-3501.3850)] [202.6330,(-3495.9560)]
    PS_part #wall "PS_Wall_006" #(#([(-0.0555),(-3.4600)],[(-2.7915),(-3.4600)],[(-2.8135),(-3.5400)],[2.8135,(-3.5400)],[2.8135,(-3.4600)],[2.1325,(-3.4600)],[2.1325,3.5400],[2.0525,3.5400],[2.0525,(-2.7010)],[0.3445,(-2.7010)],[0.1885,(-2.7320)],[0.0615,(-2.8180)],[(-0.0245),(-2.9450)],[(-0.0555),(-3.0930)]),#([0.6275,(-2.8180)],[0.5165,(-2.7410)],[0.5845,(-2.7810)],[2.0525,(-2.7810)],[2.0525,(-3.4600)],[0.5145,(-3.4600)],[0.6275,(-3.3840)],[0.7125,(-3.2570)],[0.7445,(-3.1010)],[0.7125,(-2.9450)])) 0.0000 3.0000 true [195.2725,(-3487.3330)] [192.4590,(-3490.8730)] [198.0860,(-3483.7930)]
    PS_part #wall "PS_Wall_007" #(#([(-0.4300),1.7200],[0.2500,1.7200],[0.2500,(-1.7200)],[(-0.4300),(-1.7200)],[(-0.4300),(-1.8000)],[0.4300,(-1.8000)],[0.4300,1.8000],[(-0.4300),1.8000])) 0.0000 3.0000 true [197.4400,(-3503.5180)] [197.0100,(-3505.3180)] [197.8700,(-3501.7180)]
    PS_part #wall "PS_Wall_008" #(#([0.0900,0.0175],[(-0.0900),0.0175],[(-0.0900),(-0.0175)],[0.0900,(-0.0175)])) 0.0000 3.0000 true [197.7800,(-3506.5005)] [197.6900,(-3506.5180)] [197.8700,(-3506.4830)]
    PS_part #wall "PS_Wall_009" #(#([0.7590,1.5590],[(-4.5190),(-1.4890)],[(-4.4790),(-1.5590)],[0.7800,1.4790],[3.5100,1.4790],[3.4390,1.4310],[3.3530,1.3040],[3.3220,1.1480],[3.3530,0.9930],[3.4390,0.8660],[3.5660,0.7800],[3.7220,0.7480],[3.8770,0.7800],[4.0050,0.8660],[4.0420,0.9210],[4.0420,0.4790],[4.5190,0.4790],[4.5190,0.5590],[4.1220,0.5590],[4.1220,1.1590],[4.0900,1.3150],[4.0050,1.4420],[3.8770,1.5270],[3.7220,1.5590])) 0.0000 3.0000 true [191.8950,(-3500.9970)] [187.3760,(-3502.5560)] [196.4140,(-3499.4380)]
    PS_part #wall "PS_Wall_010" #(#([(-0.3800),(-1.8000)],[0.3800,(-1.8000)],[0.3800,(-1.7200)],[(-0.3000),(-1.7200)],[(-0.3000),1.7200],[0.3800,1.7200],[0.3800,1.8000],[(-0.3800),1.8000])) 0.0000 3.0000 true [195.5300,(-3503.5180)] [195.1500,(-3505.3180)] [195.9100,(-3501.7180)]
    PS_part #wall "PS_Wall_011" #(#([(-0.3585),(-0.3360)],[0.1415,(-1.2030)],[0.3585,(-1.0780)],[(-0.1085),(-0.2690)],[(-0.1085),1.2030],[(-0.3585),1.2030])) 0.0000 3.0000 true [185.8865,(-3499.4490)] [185.5280,(-3500.6520)] [186.2450,(-3498.2460)]
    PS_part #wall "PS_Wall_012" #(#([(-0.1085),0.2685],[0.3585,1.0775],[0.1415,1.2025],[(-0.3585),0.3355],[(-0.3585),(-1.2025)],[(-0.1085),(-1.2025)])) 0.0000 3.0000 true [185.8865,(-3490.8335)] [185.5280,(-3492.0360)] [186.2450,(-3489.6310)]
    PS_part #column "PS_Column_001" #(#([(-0.3690),(-0.1560)],[(-0.2830),(-0.2830)],[(-0.1560),(-0.3690)],[0.0000,(-0.4000)],[0.1550,(-0.3690)],[0.2820,(-0.2830)],[0.3680,(-0.1560)],[0.4000,0.0000],[0.3680,0.1550],[0.2820,0.2830],[0.1550,0.3680],[0.0000,0.4000],[(-0.1560),0.3680],[(-0.2830),0.2830],[(-0.3690),0.1550],[(-0.4000),0.0000])) 0.0000 3.0000 true [192.4270,(-3505.3870)] [192.0270,(-3505.7870)] [192.8270,(-3504.9870)]
    PS_part #column "PS_Column_002" #(#([(-0.3690),(-0.1560)],[(-0.2830),(-0.2830)],[(-0.1560),(-0.3690)],[0.0000,(-0.4000)],[0.1550,(-0.3690)],[0.2820,(-0.2830)],[0.3680,(-0.1560)],[0.4000,0.0000],[0.3680,0.1550],[0.2820,0.2830],[0.1550,0.3680],[0.0000,0.4000],[(-0.1560),0.3680],[(-0.2830),0.2830],[(-0.3690),0.1550],[(-0.4000),0.0000])) 0.0000 3.0000 true [192.4270,(-3484.8950)] [192.0270,(-3485.2950)] [192.8270,(-3484.4950)]
    PS_part #lintel "PS_Lintel_001_D1" #(#([(-0.0900),0.7990],[(-0.0900),(-0.7990)],[0.0900,(-0.7990)],[0.0900,0.7990])) 2.1000 3.0000 true [207.0630,(-3495.1560)] [206.9730,(-3495.9550)] [207.1530,(-3494.3570)]
    PS_part #lintel "PS_Lintel_002_D2" #(#([(-0.0900),0.7990],[(-0.0900),(-0.7990)],[0.0900,(-0.7990)],[0.0900,0.7990])) 2.1000 3.0000 true [201.7540,(-3495.1560)] [201.6640,(-3495.9550)] [201.8440,(-3494.3570)]
    PS_part #lintel "PS_Lintel_003_D3" #(#([0.4240,(-0.0400)],[0.4240,0.0400],[(-0.4240),0.0400],[(-0.4240),(-0.0400)])) 2.1000 3.0000 true [202.4690,(-3496.2410)] [202.0450,(-3496.2810)] [202.8930,(-3496.2010)]
    PS_part #lintel "PS_Lintel_004_D4" #(#([(-0.4490),(-0.0400)],[0.4490,(-0.0400)],[0.4490,0.0400],[(-0.4490),0.0400])) 2.1000 3.0000 true [196.8640,(-3500.4780)] [196.4150,(-3500.5180)] [197.3130,(-3500.4380)]
    PS_part #lintel "PS_Lintel_005_D5" #(#([(-0.4490),(-0.0400)],[0.4490,(-0.0400)],[0.4490,0.0400],[(-0.4490),0.0400])) 2.1000 3.0000 true [198.5360,(-3490.8330)] [198.0870,(-3490.8730)] [198.9850,(-3490.7930)]
    PS_part #lintel "PS_Lintel_006_D6" #(#([(-0.3990),(-0.0400)],[0.3990,(-0.0400)],[0.3990,0.0400],[(-0.3990),0.0400])) 2.1000 3.0000 true [206.0400,(-3494.0710)] [205.6410,(-3494.1110)] [206.4390,(-3494.0310)]
    PS_part #lintel "PS_Lintel_007_D7" #(#([(-0.3990),(-0.0900)],[0.3990,(-0.0900)],[0.3990,0.0900],[(-0.3990),0.0900])) 2.1000 3.0000 true [203.6010,(-3494.0210)] [203.2020,(-3494.1110)] [204.0000,(-3493.9310)]
    PS_part #lintel "PS_Lintel_008_D8" #(#([(-0.2720),0.3900],[0.2030,(-0.4300)],[0.2720,(-0.3900)],[(-0.2020),0.4300])) 2.1000 3.0000 true [201.6390,(-3490.2070)] [201.3670,(-3490.6370)] [201.9110,(-3489.7770)]
    PS_part #lintel "PS_Lintel_009_D9" #(#([0.1555,0.3420],[(-0.2215),(-0.3040)],[(-0.1565),(-0.3420)],[0.2215,0.3040])) 2.1000 3.0000 true [201.9365,(-3499.4690)] [201.7150,(-3499.8110)] [202.1580,(-3499.1270)]
    PS_part #lintel "PS_Lintel_010_D10" #(#([0.1555,0.3420],[(-0.2215),(-0.3040)],[(-0.1565),(-0.3420)],[0.2215,0.3040])) 2.1000 3.0000 true [201.3455,(-3500.4930)] [201.1240,(-3500.8350)] [201.5670,(-3500.1510)]
    PS_part #lintel "PS_Lintel_011_D11" #(#([0.1555,0.3420],[(-0.2215),(-0.3040)],[(-0.1565),(-0.3420)],[0.2215,0.3040])) 2.1000 3.0000 true [203.4385,(-3499.4470)] [203.2170,(-3499.7890)] [203.6600,(-3499.1050)]
    PS_part #lintel "PS_Lintel_012_D12" #(#([0.1890,0.4085],[(-0.2590),(-0.3695)],[(-0.1900),(-0.4085)],[0.2590,0.3685])) 2.1000 3.0000 true [202.2810,(-3501.4525)] [202.0220,(-3501.8610)] [202.5400,(-3501.0440)]
    PS_part #lintel "PS_Lintel_013_D13" #(#([(-0.3990),(-0.0400)],[0.3990,(-0.0400)],[0.3990,0.0400],[(-0.3990),0.0400])) 2.1000 3.0000 true [205.2400,(-3496.2410)] [204.8410,(-3496.2810)] [205.6390,(-3496.2010)]
    PS_part #lintel "PS_Lintel_014_D14" #(#([(-0.1425),(-0.4955)],[0.3595,0.3695],[0.1425,0.4955],[(-0.3595),(-0.3695)])) 2.1000 3.0000 true [206.5075,(-3497.2645)] [206.1480,(-3497.7600)] [206.8670,(-3496.7690)]
    PS_part #lintel "PS_Lintel_015_O3" #(#([(-0.0900),0.5990],[(-0.0900),(-0.5990)],[0.0900,(-0.5990)],[0.0900,0.5990])) 2.1000 3.0000 true [197.7800,(-3501.1180)] [197.6900,(-3501.7170)] [197.8700,(-3500.5190)]
    PS_part #lintel "PS_Lintel_016_O5" #(#([(-0.5490),(-0.0400)],[0.5490,(-0.0400)],[0.5490,0.0400],[(-0.5490),0.0400])) 2.1000 3.0000 true [196.4600,(-3501.7580)] [195.9110,(-3501.7980)] [197.0090,(-3501.7180)]
    PS_part #lintel "PS_Lintel_017_O6" #(#([(-0.5490),(-0.0400)],[0.5490,(-0.0400)],[0.5490,0.0400],[(-0.5490),0.0400])) 2.1000 3.0000 true [196.4600,(-3505.2780)] [195.9110,(-3505.3180)] [197.0090,(-3505.2380)]
    PS_part #glass "PS_Glass_001" #(#([0.0900,(-3.1040)],[0.0900,3.1040],[(-0.0900),3.1040],[(-0.0900),(-3.1040)])) 0.0000 3.0000 true [185.6880,(-3495.1410)] [185.5980,(-3498.2450)] [185.7780,(-3492.0370)]
    PS_part #glass "PS_Glass_002" #(#([(-0.1600),(-0.2445)],[(-0.1250),(-0.2635)],[(-0.1060),(-0.2505)],[(-0.0910),(-0.2595)],[0.1750,0.2175],[0.1510,0.2305],[0.1320,0.2185],[0.1150,0.2275],[0.1160,0.2505],[0.0920,0.2635],[(-0.1750),(-0.2125)],[(-0.1590),(-0.2215)])) 0.0000 3.0000 true [192.0450,(-3490.5505)] [191.8700,(-3490.8140)] [192.2200,(-3490.2870)]
    PS_part #glass "PS_Glass_003" #(#([(-0.5800),(-1.1845)],[0.7360,1.0945],[0.5800,1.1845],[(-0.7360),(-1.0945)])) 0.0000 3.0000 true [186.8250,(-3488.5705)] [186.0890,(-3489.7550)] [187.5610,(-3487.3860)]
    PS_part #glass "PS_Glass_004" #(#([(-0.1600),(-0.2445)],[(-0.1260),(-0.2635)],[(-0.1070),(-0.2505)],[(-0.0910),(-0.2595)],[0.1750,0.2175],[0.1500,0.2305],[0.1320,0.2185],[0.1140,0.2275],[0.1150,0.2505],[0.0910,0.2635],[(-0.1750),(-0.2125)],[(-0.1590),(-0.2215)])) 0.0000 3.0000 true [187.7450,(-3488.0675)] [187.5700,(-3488.3310)] [187.9200,(-3487.8040)]
    PS_part #glass "PS_Glass_005" #(#([(-0.1600),(-0.2445)],[(-0.1250),(-0.2635)],[(-0.1070),(-0.2515)],[(-0.0910),(-0.2595)],[0.1750,0.2165],[0.1510,0.2305],[0.1320,0.2175],[0.1150,0.2275],[0.1160,0.2505],[0.0910,0.2635],[(-0.1750),(-0.2135)],[(-0.1590),(-0.2215)])) 0.0000 3.0000 true [187.6600,(-3488.0185)] [187.4850,(-3488.2820)] [187.8350,(-3487.7550)]
    PS_part #glass "PS_Glass_006" #(#([(-0.1605),(-0.2445)],[(-0.1255),(-0.2635)],[(-0.1065),(-0.2505)],[(-0.0915),(-0.2595)],[0.1745,0.2175],[0.1505,0.2305],[0.1325,0.2185],[0.1145,0.2275],[0.1155,0.2505],[0.0915,0.2635],[(-0.1745),(-0.2125)],[(-0.1595),(-0.2215)])) 0.0000 3.0000 true [187.5715,(-3487.9675)] [187.3970,(-3488.2310)] [187.7460,(-3487.7040)]
    PS_part #glass "PS_Glass_007" #(#([(-0.1600),(-0.2445)],[(-0.1250),(-0.2635)],[(-0.1070),(-0.2505)],[(-0.0910),(-0.2595)],[0.1750,0.2175],[0.1500,0.2305],[0.1320,0.2185],[0.1140,0.2275],[0.1150,0.2505],[0.0910,0.2635],[(-0.1750),(-0.2125)],[(-0.1590),(-0.2215)])) 0.0000 3.0000 true [187.4850,(-3487.9175)] [187.3100,(-3488.1810)] [187.6600,(-3487.6540)]
    PS_part #glass "PS_Glass_008" #(#([(-0.0300),(-0.5815)],[0.0300,(-0.5815)],[0.0300,0.5815],[(-0.0300),0.5815])) 0.0000 3.0000 true [197.7200,(-3505.9005)] [197.6900,(-3506.4820)] [197.7500,(-3505.3190)]
    PS_part #glass "PS_Glass_009" #(#([(-7.4650),2.9245],[(-4.5610),(-2.1055)],[(-3.0520),(-2.9765)],[(-2.8390),(-2.9765)],[(-2.8390),(-3.0145)],[7.4650,(-3.0145)],[7.4630,(-2.9765)],[(-2.6920),(-2.9765)],[(-4.4290),(-1.9735)],[(-7.3090),3.0145])) 0.0000 3.0000 true [193.5540,(-3503.5415)] [186.0890,(-3506.5560)] [201.0190,(-3500.5270)]
    PS_part #glass "PS_Glass_010" #(#([(-0.1600),(-0.2445)],[(-0.1260),(-0.2635)],[(-0.1070),(-0.2505)],[(-0.0910),(-0.2595)],[0.1750,0.2175],[0.1500,0.2305],[0.1320,0.2185],[0.1140,0.2275],[0.1150,0.2505],[0.0910,0.2635],[(-0.1750),(-0.2125)],[(-0.1590),(-0.2215)])) 0.0000 3.0000 true [192.3920,(-3490.7505)] [192.2170,(-3491.0140)] [192.5670,(-3490.4870)]
    PS_part #glass "PS_Glass_011" #(#([(-0.1600),(-0.2445)],[(-0.1250),(-0.2635)],[(-0.1070),(-0.2505)],[(-0.0910),(-0.2595)],[0.1750,0.2175],[0.1510,0.2305],[0.1320,0.2185],[0.1150,0.2275],[0.1160,0.2505],[0.0910,0.2635],[(-0.1750),(-0.2125)],[(-0.1590),(-0.2215)])) 0.0000 3.0000 true [192.3050,(-3490.7005)] [192.1300,(-3490.9640)] [192.4800,(-3490.4370)]
    PS_part #glass "PS_Glass_012" #(#([(-0.1610),(-0.2445)],[(-0.1260),(-0.2635)],[(-0.1070),(-0.2505)],[(-0.0910),(-0.2595)],[0.1750,0.2175],[0.1500,0.2305],[0.1320,0.2185],[0.1140,0.2275],[0.1150,0.2505],[0.0910,0.2635],[(-0.1750),(-0.2125)],[(-0.1600),(-0.2215)])) 0.0000 3.0000 true [192.2190,(-3490.6505)] [192.0440,(-3490.9140)] [192.3940,(-3490.3870)]
    PS_part #glass "PS_Glass_013" #(#([(-0.1600),(-0.2445)],[(-0.1250),(-0.2635)],[(-0.1070),(-0.2505)],[(-0.0910),(-0.2595)],[0.1750,0.2175],[0.1510,0.2305],[0.1320,0.2185],[0.1150,0.2275],[0.1160,0.2505],[0.0910,0.2635],[(-0.1750),(-0.2125)],[(-0.1590),(-0.2215)])) 0.0000 3.0000 true [192.1320,(-3490.6005)] [191.9570,(-3490.8640)] [192.3070,(-3490.3370)]
    PS_part #glass "PS_Glass_014" #(#([7.2500,1.1150],[(-3.4670),1.1150],[(-3.6720),1.5000],[(-3.6910),1.4910],[(-3.7780),1.6430],[(-6.2160),0.2370],[(-7.2500),(-1.5530)],[(-7.0940),(-1.6430)],[(-6.0840),0.1050],[(-3.7050),1.4770],[(-3.4980),1.0870],[(-3.4800),1.0960],[(-3.4800),1.0780],[7.2500,1.0780])) 0.0000 3.0000 true [195.2100,(-3484.8710)] [187.9600,(-3486.5140)] [202.4600,(-3483.2280)]
    PS_part #glass "PS_Glass_015_D15 transom" #(#([(-0.1970),(-0.5210)],[0.3530,0.4310],[0.1970,0.5210],[(-0.3530),(-0.4310)])) 2.1000 3.0000 true [187.7610,(-3486.9500)] [187.4080,(-3487.4710)] [188.1140,(-3486.4290)]
    PS_part #builtin "PS_Builtin_001_Full-height panel" #(#([0.1700,1.4080],[0.1270,1.4720],[0.0640,1.5150],[(-0.0140),1.5300],[(-0.1860),1.5300],[(-0.1860),1.0600],[0.0860,1.0600],[0.0860,(-1.0600)],[(-0.1860),(-1.0600)],[(-0.1860),(-1.5300)],[(-0.0140),(-1.5300)],[0.0250,(-1.5260)],[0.0630,(-1.5140)],[0.0970,(-1.4960)],[0.1270,(-1.4710)],[0.1520,(-1.4410)],[0.1710,(-1.4060)],[0.1820,(-1.3690)],[0.1860,(-1.3300)],[0.1860,1.3300])) 0.0000 3.0000 true [199.8630,(-3495.1560)] [199.6770,(-3496.6860)] [200.0490,(-3493.6260)]
    PS_part #low "PS_Low_001_Jacuzzi kerb" #(#([0.4165,(-0.2500)],[0.4165,0.2500],[(-0.4165),0.2500],[(-0.4165),0.1700],[0.3365,0.1700],[0.3365,(-0.2500)])) 0.0000 0.1000 false [198.2865,(-3503.9680)] [197.8700,(-3504.2180)] [198.7030,(-3503.7180)]
    PS_part #low "PS_Low_002_Jacuzzi kerb" #(#([0.4165,0.1700],[0.4165,0.2500],[(-0.4165),0.2500],[(-0.4165),(-0.2500)],[(-0.3365),(-0.2500)],[(-0.3365),0.1700])) 0.0000 0.1000 false [201.0535,(-3503.9680)] [200.6370,(-3504.2180)] [201.4700,(-3503.7180)]
    PS_part #balustrade "PS_Balustrade_001" #(#([13.4100,11.0075],[13.4100,11.0475],[4.2570,11.0475],[3.6800,12.0475],[(-5.7720),12.0475],[(-5.9770),12.0405],[(-6.1820),12.0185],[(-6.3850),11.9835],[(-6.5840),11.9335],[(-6.7800),11.8695],[(-6.9710),11.7925],[(-7.1560),11.7025],[(-7.3340),11.5995],[(-7.5040),11.4845],[(-7.6670),11.3585],[(-7.8190),11.2205],[(-7.9620),11.0725],[(-8.0950),10.9145],[(-8.2150),10.7485],[(-8.3240),10.5745],[(-13.2900),1.9725],[(-13.3870),1.7915],[(-13.4700),1.6035],[(-13.5410),1.4105],[(-13.5970),1.2125],[(-13.6400),1.0115],[(-13.6690),0.8075],[(-13.6830),0.6025],[(-13.6830),0.3965],[(-13.6690),0.1915],[(-13.6400),(-0.0125)],[(-13.5970),(-0.2135)],[(-13.5410),(-0.4115)],[(-13.4700),(-0.6045)],[(-13.3870),(-0.7925)],[(-13.2900),(-0.9735)],[(-8.3390),(-9.5495)],[(-8.2290),(-9.7265)],[(-8.1060),(-9.8955)],[(-7.9710),(-10.0555)],[(-7.8260),(-10.2065)],[(-7.6700),(-10.3465)],[(-7.5050),(-10.4755)],[(-7.3320),(-10.5925)],[(-7.1510),(-10.6965)],[(-6.9630),(-10.7885)],[(-6.7690),(-10.8675)],[(-6.5700),(-10.9315)],[(-6.3670),(-10.9825)],[(-6.1610),(-11.0185)],[(-5.9530),(-11.0405)],[(-5.7440),(-11.0475)],[(-0.6160),(-11.0475)],[1.1160,(-12.0475)],[13.6830,(-12.0475)],[13.6830,(-12.0075)],[1.1270,(-12.0075)],[(-0.6050),(-11.0075)],[(-5.7430),(-11.0075)],[(-5.9500),(-11.0005)],[(-6.1550),(-10.9785)],[(-6.3580),(-10.9435)],[(-6.5590),(-10.8935)],[(-6.7550),(-10.8295)],[(-6.9460),(-10.7525)],[(-7.1320),(-10.6615)],[(-7.3110),(-10.5585)],[(-7.4820),(-10.4425)],[(-7.6450),(-10.3155)],[(-7.7980),(-10.1775)],[(-7.9410),(-10.0295)],[(-8.0740),(-9.8715)],[(-8.1950),(-9.7045)],[(-8.3050),(-9.5285)],[(-13.2550),(-0.9545)],[(-13.3510),(-0.7755)],[(-13.4330),(-0.5895)],[(-13.5030),(-0.3985)],[(-13.5590),(-0.2035)],[(-13.6010),(-0.0055)],[(-13.6290),0.1955],[(-13.6430),0.3975],[(-13.6430),0.6015],[(-13.6290),0.8035],[(-13.6010),1.0045],[(-13.5590),1.2025],[(-13.5030),1.3975],[(-13.4330),1.5885],[(-13.3510),1.7745],[(-13.2550),1.9535],[(-8.2900),10.5535],[(-8.1820),10.7255],[(-8.0630),10.8905],[(-7.9330),11.0455],[(-7.7920),11.1915],[(-7.6410),11.3275],[(-7.4810),11.4525],[(-7.3130),11.5655],[(-7.1370),11.6675],[(-6.9540),11.7565],[(-6.7660),11.8325],[(-6.5730),11.8945],[(-6.3760),11.9445],[(-6.1770),11.9795],[(-5.9750),12.0005],[(-5.7720),12.0075],[3.6570,12.0075],[4.2340,11.0075])) 0.0000 1.1000 false [187.5290,(-3494.6555)] [173.8460,(-3506.7030)] [201.2120,(-3482.6080)]
    PS_part #low "PS_Low_003_Terrace C-wall (backrest)" #(#([(-1.0000),2.0800],[(-1.0000),(-2.0800)],[1.0000,(-2.0800)],[1.0000,(-1.8800)],[(-0.8000),(-1.8800)],[(-0.8000),1.8800],[1.0000,1.8800],[1.0000,2.0800])) 0.0000 0.9000 false [177.8400,(-3494.1560)] [176.8400,(-3496.2360)] [178.8400,(-3492.0760)]
    PS_part #low "PS_Low_004_Built-in bench" #(#([(-0.9000),1.8800],[(-0.9000),(-1.8800)],[0.9000,(-1.8800)],[0.9000,(-1.0800)],[(-0.1000),(-1.0800)],[(-0.1000),1.0800],[0.9000,1.0800],[0.9000,1.8800])) 0.0000 0.4500 false [177.9400,(-3494.1560)] [177.0400,(-3496.0360)] [178.8400,(-3492.2760)]
    PS_part #low "PS_Low_005_Cabana backrest" #(#([1.1335,(-0.0770)],[0.7235,(-0.7870)],[(-1.0435),0.2330],[(-0.6335),0.9430],[(-0.7895),1.0330],[(-1.2895),0.1670],[0.7895,(-1.0330)],[1.2895,(-0.1670)])) 0.0000 0.9000 false [178.6845,(-3489.7070)] [177.3950,(-3490.7400)] [179.9740,(-3488.6740)]
    PS_part #low "PS_Low_006_Cabana backrest" #(#([(-0.7895),1.0330],[(-1.2895),0.1670],[(-1.1335),0.0770],[(-0.7235),0.7870],[1.0435,(-0.2330)],[0.6335,(-0.9430)],[0.7895,(-1.0330)],[1.2895,(-0.1670)])) 0.0000 0.9000 false [179.6145,(-3488.0960)] [178.3250,(-3489.1290)] [180.9040,(-3487.0630)]
    PS_part #low "PS_Low_007_Cabana lounge bed" #(#([(-1.2545),0.2285],[(-1.0975),0.1375],[(-1.5075),(-0.5725)],[0.2585,(-1.5915)],[0.6675,(-0.8815)],[0.8255,(-0.9715)],[1.2545,(-0.2285)],[1.0975,(-0.1375)],[1.5075,0.5725],[(-0.2585),1.5915],[(-0.6675),0.8815],[(-0.8245),0.9715])) 0.0000 0.4500 false [179.1495,(-3488.9015)] [177.6420,(-3490.4930)] [180.6570,(-3487.3100)]
    PS_part #deck "PS_Deck_001_Terrace deck (NW)" #(#([(-1.6760),(-2.5665)],[3.4240,(-2.5665)],[5.2230,0.5495],[5.2730,0.7755],[4.3940,2.5655],[(-1.9090),2.5665],[(-2.1540),2.5555],[(-2.3930),2.5235],[(-2.6280),2.4715],[(-2.8580),2.3995],[(-3.0800),2.3075],[(-3.2940),2.1955],[(-3.4980),2.0665],[(-3.6890),1.9195],[(-3.8670),1.7565],[(-4.0290),1.5785],[(-4.1760),1.3875],[(-5.2730),(-0.4895)])) 0.0000 0.0200 false [183.6700,(-3485.3585)] [178.3970,(-3487.9250)] [188.9430,(-3482.7920)]
    PS_part #deck "PS_Deck_002_Dining deck" #(#([(-2.9000),1.4500],[(-2.9000),(-1.4500)],[2.9000,(-1.4500)],[2.9000,1.4500])) 0.0000 0.0200 false [183.6470,(-3503.1290)] [180.7470,(-3504.5790)] [186.5470,(-3501.6790)]
    PS_part #post "PS_Post_001_Pergola post" #(#([0.0690,0.0290],[0.0530,0.0530],[0.0290,0.0690],[0.0000,0.0750],[(-0.0290),0.0690],[(-0.0530),0.0530],[(-0.0690),0.0290],[(-0.0750),0.0000],[(-0.0690),(-0.0290)],[(-0.0530),(-0.0530)],[(-0.0290),(-0.0690)],[0.0000,(-0.0750)],[0.0290,(-0.0690)],[0.0530,(-0.0530)],[0.0690,(-0.0290)],[0.0750,0.0000])) 0.0000 2.7000 false [180.9410,(-3501.8490)] [180.8660,(-3501.9240)] [181.0160,(-3501.7740)]
    PS_part #post "PS_Post_002_Pergola post" #(#([0.0690,0.0290],[0.0530,0.0530],[0.0290,0.0690],[0.0000,0.0750],[(-0.0290),0.0690],[(-0.0530),0.0530],[(-0.0690),0.0290],[(-0.0750),0.0000],[(-0.0690),(-0.0290)],[(-0.0530),(-0.0530)],[(-0.0290),(-0.0690)],[0.0000,(-0.0750)],[0.0290,(-0.0690)],[0.0530,(-0.0530)],[0.0690,(-0.0290)],[0.0750,0.0000])) 0.0000 2.7000 false [186.3530,(-3501.8490)] [186.2780,(-3501.9240)] [186.4280,(-3501.7740)]
    PS_part #post "PS_Post_003_Pergola post" #(#([0.0690,0.0290],[0.0530,0.0530],[0.0290,0.0690],[0.0000,0.0750],[(-0.0290),0.0690],[(-0.0530),0.0530],[(-0.0690),0.0290],[(-0.0750),0.0000],[(-0.0690),(-0.0290)],[(-0.0530),(-0.0530)],[(-0.0290),(-0.0690)],[0.0000,(-0.0750)],[0.0290,(-0.0690)],[0.0530,(-0.0530)],[0.0690,(-0.0290)],[0.0750,0.0000])) 0.0000 2.7000 false [186.3530,(-3504.4090)] [186.2780,(-3504.4840)] [186.4280,(-3504.3340)]
    PS_part #post "PS_Post_004_Pergola post" #(#([0.0690,0.0290],[0.0530,0.0530],[0.0290,0.0690],[0.0000,0.0750],[(-0.0290),0.0690],[(-0.0530),0.0530],[(-0.0690),0.0290],[(-0.0750),0.0000],[(-0.0690),(-0.0290)],[(-0.0530),(-0.0530)],[(-0.0290),(-0.0690)],[0.0000,(-0.0750)],[0.0290,(-0.0690)],[0.0530,(-0.0530)],[0.0690,(-0.0290)],[0.0750,0.0000])) 0.0000 2.7000 false [180.9410,(-3504.4090)] [180.8660,(-3504.4840)] [181.0160,(-3504.3340)]
    PS_part #slab "PS_Slab_001" #(#([10.6760,(-12.0505)],[10.7050,(-12.0005)],[10.7170,(-11.9915)],[16.6800,(-1.6695)],[16.6350,(-1.6405)],[16.6340,0.7575],[16.6200,0.7675],[12.3280,8.2015],[13.3460,8.7885],[13.3480,8.7935],[12.1510,10.8645],[12.1410,10.8725],[12.0390,11.0495],[1.2650,11.0495],[0.6870,12.0495],[(-8.7660),12.0505],[(-8.9720),12.0425],[(-9.1760),12.0215],[(-9.3790),11.9855],[(-9.5790),11.9355],[(-9.7750),11.8725],[(-9.9660),11.7955],[(-10.1510),11.7045],[(-10.3290),11.6015],[(-10.5000),11.4865],[(-10.6620),11.3595],[(-10.8150),11.2225],[(-10.9580),11.0745],[(-11.0900),10.9165],[(-11.2120),10.7495],[(-11.3210),10.5755],[(-16.2860),1.9745],[(-16.3830),1.7925],[(-16.4670),1.6045],[(-16.5370),1.4115],[(-16.5940),1.2135],[(-16.6370),1.0115],[(-16.6650),0.8075],[(-16.6800),0.6025],[(-16.6800),0.3965],[(-16.6650),0.1915],[(-16.6370),(-0.0125)],[(-16.5940),(-0.2145)],[(-16.5370),(-0.4125)],[(-16.4670),(-0.6055)],[(-16.3830),(-0.7935)],[(-16.2860),(-0.9755)],[(-11.3360),(-9.5505)],[(-11.2250),(-9.7275)],[(-11.1010),(-9.8975)],[(-10.9670),(-10.0575)],[(-10.8210),(-10.2085)],[(-10.6660),(-10.3485)],[(-10.5010),(-10.4775)],[(-10.3270),(-10.5945)],[(-10.1460),(-10.6995)],[(-9.9580),(-10.7905)],[(-9.7640),(-10.8695)],[(-9.5640),(-10.9345)],[(-9.3610),(-10.9845)],[(-9.1550),(-11.0215)],[(-8.9470),(-11.0425)],[(-8.7380),(-11.0505)],[(-3.6110),(-11.0505)],[(-1.8790),(-12.0505)])) (-0.2500) 0.0000 false [190.5230,(-3494.6555)] [173.8430,(-3506.7060)] [207.2030,(-3482.6050)]
    PS_room "Living & Dining" [192.9300,(-3495.2300)]
    PS_room "Study & Meeting" [193.1600,(-3487.1100)]
    PS_room "Gym & Yoga" [199.8900,(-3486.7100)]
    PS_room "Kitchen" [203.7500,(-3490.8200)]
    PS_room "Bar" [201.2000,(-3491.3900)]
    PS_room "Powder" [203.7500,(-3493.4400)]
    PS_room "Foyer" [204.4000,(-3495.1600)]
    PS_room "Massage" [203.6500,(-3497.7200)]
    PS_room "Steam" [201.3800,(-3498.7100)]
    PS_room "Shower" [200.5000,(-3500.2600)]
    PS_room "Sauna" [203.7700,(-3500.3300)]
    PS_room "Toilet" [202.7300,(-3502.1600)]
    PS_room "Master Bath" [199.3800,(-3502.0100)]
    PS_room "Jacuzzi" [199.6700,(-3505.6700)]
    PS_room "Walk-in Closet" [196.4600,(-3503.5200)]
    PS_room "Master Bedroom" [192.7200,(-3503.0600)]
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
        spinner fh1 "TV / wall screen:" across:2 range:[10, 5000, 600] type:#integer fieldwidth:40
        spinner fh2 "Curtain:" range:[10, 5000, 2700] type:#integer fieldwidth:40
        spinner fh3 "Lamp:" across:2 range:[10, 5000, 500] type:#integer fieldwidth:40
        spinner fh4 "Plant:" range:[10, 5000, 2500] type:#integer fieldwidth:40
        spinner fh5 "Sanitary fitting:" across:2 range:[10, 5000, 850] type:#integer fieldwidth:40
        spinner fh6 "Appliance:" range:[10, 5000, 900] type:#integer fieldwidth:40
        spinner fh7 "Bed:" across:2 range:[10, 5000, 500] type:#integer fieldwidth:40
        spinner fh8 "Chair / stool:" range:[10, 5000, 450] type:#integer fieldwidth:40
        spinner fh9 "Sofa / armchair:" across:2 range:[10, 5000, 800] type:#integer fieldwidth:40
        spinner fh10 "Table / desk:" range:[10, 5000, 750] type:#integer fieldwidth:40
        spinner fh11 "Coffee table:" across:2 range:[10, 5000, 450] type:#integer fieldwidth:40
        spinner fh12 "Tall cabinet:" range:[10, 5000, 2100] type:#integer fieldwidth:40
        spinner fh13 "Other furniture:" range:[10, 5000, 750] type:#integer fieldwidth:40
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
        PS_shift = if dwg.checked then [0.0, 0.0] else [190.5230, (-3494.6550)]
        PS_furnHeights = #((fh1.value / 1000.0),(fh2.value / 1000.0),(fh3.value / 1000.0),(fh4.value / 1000.0),(fh5.value / 1000.0),(fh6.value / 1000.0),(fh7.value / 1000.0),(fh8.value / 1000.0),(fh9.value / 1000.0),(fh10.value / 1000.0),(fh11.value / 1000.0),(fh12.value / 1000.0),(fh13.value / 1000.0))
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
        PS_furnHeights = #((fh1.value / 1000.0),(fh2.value / 1000.0),(fh3.value / 1000.0),(fh4.value / 1000.0),(fh5.value / 1000.0),(fh6.value / 1000.0),(fh7.value / 1000.0),(fh8.value / 1000.0),(fh9.value / 1000.0),(fh10.value / 1000.0),(fh11.value / 1000.0),(fh12.value / 1000.0),(fh13.value / 1000.0))
        local r = PS_furnApply()
        messageBox ((r[1] as string) + " furniture boxes set to the heights in the window and stood on their floor or support." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were left alone (not a Box any more, or a kind this script does not know).") else "")) title:"Presidential suite"
    )
)
createDialog PS_UI
