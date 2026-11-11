-- REFERENCE BUILDING / built by the walkthrough app from "rooms-reference-ground.dxf + rooms-reference-upper.dxf", 11 Nov 2026
-- Same model as the version in the walkthrough app (model data 2da587ccc0bd). Floor levels +0.00 / +3.00 m, wall heights 3.00 / 3.00 m.
-- The drawings were DXF exported by its own program; drawing units mm.
-- Placed at the drawing's own coordinates in metres (to line up with the drawings imported in metres), or centred on
-- the origin if you untick that box in the script's window.
-- Every part stays LIVE (no Editable Poly): an editable spline outline + an Extrude modifier (output: Mesh) + Smooth.
--   * Change a height: the Extrude amount on that object, or "Update levels and heights" in this script's window.
--   * Change an outline: select the spline level under the modifiers and move vertices.
--   * Editable Mesh: tick "Collapse to Editable Mesh" before Build, or press "Collapse all now" later.
-- Each object's pivot is at the middle of its own outline, on its base. Layers per level and kind (RF_ground_Walls ...).
-- "Update levels and heights" sets the tops of the walls (those marked to) and lintels to their level's wall height and keeps
-- the stair treads, the stair landings, the slabs, the ceilings and the railings at their own heights (only parts marked to follow the wall height change).
-- Each part is checked as it is built (closed solid, height, position). A part that fails is kept on layer
-- RF_Check_Failed and listed in the MAXScript Listener; the rest is still built.
-- Build sets System Units to metres. Nothing in an existing scene is changed: run it in a NEW EMPTY scene.
global RF_UI
global RF_nodes = #()
global RF_failed = #()
global RF_levels = #(0.00,3.00)
global RF_heights = #(3.00,3.00)
global RF_floorNames = #("ground","upper")
global RF_collapse = false
global RF_shift = [0.0, 0.0]
global RF_mats

fn RF_layer n =
(
    local ly = LayerManager.getLayerFromName n
    if ly == undefined do ly = LayerManager.newLayerFromName n
    ly
)
fn RF_mat key =
(
    local m = undefined
    for x in RF_mats where x.name == ("RF " + key) do m = x
    m
)
fn RF_makeMaterials =
(
    RF_mats = #()
    append RF_mats (standardMaterial name:"RF Wall" diffuse:(color 227 221 211))
    append RF_mats (standardMaterial name:"RF Glass" diffuse:(color 170 200 214) opacity:30 specularLevel:60 glossiness:60)
    append RF_mats (standardMaterial name:"RF Rail" diffuse:(color 119 114 124))
    append RF_mats (standardMaterial name:"RF Single" diffuse:(color 224 164 88))
    append RF_mats (standardMaterial name:"RF Slab" diffuse:(color 212 216 210))
    append RF_mats (standardMaterial name:"RF Frame" diffuse:(color 93 107 116))
    append RF_mats (standardMaterial name:"RF Step" diffuse:(color 185 199 180))
    append RF_mats (standardMaterial name:"RF Tread" diffuse:(color 185 199 180))
    append RF_mats (standardMaterial name:"RF Landing" diffuse:(color 185 199 180))
    append RF_mats (standardMaterial name:"RF Ceiling" diffuse:(color 236 236 232))
)
fn RF_num v = ((v as string) as float)
-- The outline's knots are relative to c, the middle of the outline; the node is then moved to c, so that is its pivot.
fn RF_shape nm loops =
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
fn RF_extrudeOf o =
(
    local ex = undefined
    for md in o.modifiers where classOf md == Extrude do ex = md
    ex
)
-- kind: #wall #column #lintel #sill #parapet #glass #mullion #railing #single #step #slab; z0/z1 in metres above the
-- level of floor fi (a step of a flight going down from a level starts below it);
-- follow = the top follows that level's wall height. c = pivot, mn/mx = outline extents (DWG coordinates).
fn RF_part kind nm loops z0 z1 follow fi c mn mx =
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
    local lvl = RF_levels[fi]
    local top = if follow then RF_heights[fi] else z1
    local zb = lvl + z0
    local ht = top - z0
    local o = RF_shape nm loops
    o.pos = [c.x - RF_shift.x, c.y - RF_shift.y, zb]
    addModifier o (Extrude amount:ht segs:1 capStart:true capEnd:true output:1 smooth:false)
    addModifier o (Smooth autoSmooth:true threshold:25.0)
    local mt = RF_mat info[2]
    o.material = mt
    o.wirecolor = mt.diffuse
    setUserProp o "RF_kind" (kind as string)
    setUserProp o "RF_floor" fi
    setUserProp o "RF_base" z0
    setUserProp o "RF_follow" follow
    -- the checks run on the evaluated mesh (what the modifiers produce)
    local m = snapshotAsMesh o
    local why = ""
    local tol = 0.002
    if m.numfaces < 3 then why = "no faces"
    else if (meshop.getOpenEdges m).numberSet != 0 then why = "open edges (not a closed solid)"
    else if abs(o.min.z - zb) > tol or abs(o.max.z - (zb + ht)) > tol then why = "height"
    else if abs(o.min.x - (mn.x - RF_shift.x)) > tol or abs(o.min.y - (mn.y - RF_shift.y)) > tol or abs(o.max.x - (mx.x - RF_shift.x)) > tol or abs(o.max.y - (mx.y - RF_shift.y)) > tol then why = "position"
    m = undefined
    if why == "" then
    (
        (RF_layer ("RF_" + RF_floorNames[fi] + "_" + info[1])).addNode o
        setUserProp o "RF_check" "ok"
    )
    else
    (
        (RF_layer "RF_Check_Failed").addNode o
        setUserProp o "RF_check" why
        append RF_failed (nm + ": " + why)
    )
    if RF_collapse do convertToMesh o
    append RF_nodes o
    o
)
-- Stair lines: one shape of open two-knot splines per level and kind, knots relative to c (its pivot).
fn RF_lines nm segs fi c lay =
(
    local o = splineShape name:nm
    for k = 1 to segs.count do
    (
        addNewSpline o
        addKnot o k #corner #line [segs[k][1].x, segs[k][1].y, 0]
        addKnot o k #corner #line [segs[k][2].x, segs[k][2].y, 0]
    )
    updateShape o
    o.pos = [c.x - RF_shift.x, c.y - RF_shift.y, RF_levels[fi]]
    o.wirecolor = if lay == "Stairs" then (color 46 139 71) else (color 160 210 170)
    setUserProp o "RF_floor" fi
    setUserProp o "RF_base" 0.0
    (RF_layer ("RF_" + RF_floorNames[fi] + "_" + lay)).addNode o
    append RF_nodes o
    o
)
fn RF_room nm p fi =
(
    local t = text text:nm size:0.3 pos:[p.x - RF_shift.x, p.y - RF_shift.y, RF_levels[fi] + 0.02]
    t.name = "RF_Room_" + RF_floorNames[fi] + "_" + nm
    t.wirecolor = color 30 60 110
    setUserProp t "RF_floor" fi
    setUserProp t "RF_base" 0.02
    (RF_layer ("RF_" + RF_floorNames[fi] + "_RoomNames")).addNode t
    append RF_nodes t
    t
)
-- After the build: move every part to its level and set every live part whose top follows the wall height to its
-- level's new wall height.
fn RF_updateLevels newLevels newHeights =
(
    local n = 0
    local skipped = 0
    for o in objects where (getUserProp o "RF_floor") != undefined do
    (
        local fi = (RF_num (getUserProp o "RF_floor")) as integer
        local base = RF_num (getUserProp o "RF_base")
        o.pos.z = newLevels[fi] + base
        if ((getUserProp o "RF_follow") as string) == "true" do
        (
            local ex = RF_extrudeOf o
            if ex == undefined then skipped += 1
            else ( ex.amount = newHeights[fi] - base; n += 1 )
        )
    )
    RF_levels = newLevels
    RF_heights = newHeights
    #(n, skipped)
)
fn RF_collapseAll =
(
    local n = 0
    for o in objects where (getUserProp o "RF_kind") != undefined and o.modifiers.count > 0 do ( convertToMesh o; n += 1 )
    n
)
fn RF_build =
(
    if objects.count > 0 then
    (
        messageBox "Open a NEW EMPTY scene first. Nothing in this scene has been changed." title:"Reference"
        return false
    )
    units.systemType = #meters
    units.systemScale = 1.0
    units.displayType = #metric
    units.metricType = #meters
    RF_nodes = #()
    RF_failed = #()
    RF_makeMaterials()
    local t0 = timeStamp()
    RF_part #wall "RF_ground_Wall_001" #(#([(-0.0500),(-0.1500)],[0.0500,(-0.1500)],[0.0500,0.1500],[(-0.0500),0.1500])) 0.0000 3.0000 true 1 [3.3500,3.3300] [3.3000,3.1800] [3.4000,3.4800]
    RF_part #wall "RF_ground_Wall_002" #(#([(-0.0500),0.6000],[(-0.0500),(-0.6000)],[0.0500,(-0.6000)],[0.0500,0.6000])) 0.0000 2.0620 false 1 [3.3500,4.0800] [3.3000,3.4800] [3.4000,4.6800]
    RF_part #wall "RF_ground_Wall_003" #(#([4.4500,4.3000],[4.4500,4.5000],[(-4.4500),4.5000],[(-4.4500),(-4.5000)],[0.0500,(-4.5000)],[0.0500,(-4.3000)],[(-4.2500),(-4.3000)],[(-4.2500),4.3000],[2.5200,4.3000],[2.5200,2.3000],[2.5800,2.3000],[2.5800,4.3000])) 0.0000 3.0000 true 1 [4.4500,4.5000] [0.0000,0.0000] [8.9000,9.0000]
    RF_part #wall "RF_ground_Wall_004" #(#([(-1.6000),(-4.3000)],[(-1.6000),(-3.3000)],[(-1.8000),(-3.3000)],[(-1.8000),(-4.3000)],[(-3.3000),(-4.3000)],[(-3.3000),(-4.5000)],[3.3000,(-4.5000)],[3.3000,4.5000],[3.1000,4.5000],[3.1000,0.1000],[(-1.6700),0.1000],[(-1.6700),1.1000],[(-1.7300),1.1000],[(-1.7300),0.1000],[(-1.8000),0.1000],[(-1.8000),(-2.4000)],[(-1.6000),(-2.4000)],[(-1.6000),(-0.1000)],[3.1000,(-0.1000)],[3.1000,(-4.3000)])) 0.0000 3.0000 true 1 [8.7000,4.5000] [5.4000,0.0000] [12.0000,9.0000]
    RF_part #lintel "RF_ground_Lintel_001_ground-001" #(#([0.4490,(-0.1000)],[0.4490,0.1000],[(-0.4490),0.1000],[(-0.4490),(-0.1000)])) 2.1000 3.0000 true 1 [4.9500,0.1000] [4.5010,0.0000] [5.3990,0.2000]
    RF_part #lintel "RF_ground_Lintel_002_ground-002" #(#([0.1000,0.4490],[(-0.1000),0.4490],[(-0.1000),(-0.4490)],[0.1000,(-0.4490)])) 2.1000 3.0000 true 1 [7.0000,1.6500] [6.9000,1.2010] [7.1000,2.0990]
    RF_part #tread "RF_ground_Tread_001_stair S1 tread 1" #(#([0.6000,(-0.1400)],[0.6000,0.1400],[(-0.6000),0.1400],[(-0.6000),(-0.1400)])) 0.0000 0.1880 false 1 [1.2000,1.9400] [0.6000,1.8000] [1.8000,2.0800]
    RF_part #tread "RF_ground_Tread_002_stair S1 tread 2" #(#([0.6000,(-0.1400)],[0.6000,0.1400],[(-0.6000),0.1400],[(-0.6000),(-0.1400)])) 0.0000 0.3750 false 1 [1.2000,2.2200] [0.6000,2.0800] [1.8000,2.3600]
    RF_part #tread "RF_ground_Tread_003_stair S1 tread 3" #(#([0.6000,(-0.1400)],[0.6000,0.1400],[(-0.6000),0.1400],[(-0.6000),(-0.1400)])) 0.1880 0.5620 false 1 [1.2000,2.5000] [0.6000,2.3600] [1.8000,2.6400]
    RF_part #tread "RF_ground_Tread_004_stair S1 tread 4" #(#([0.6000,(-0.1400)],[0.6000,0.1400],[(-0.6000),0.1400],[(-0.6000),(-0.1400)])) 0.3750 0.7500 false 1 [1.2000,2.7800] [0.6000,2.6400] [1.8000,2.9200]
    RF_part #tread "RF_ground_Tread_005_stair S1 tread 5" #(#([0.6000,(-0.1400)],[0.6000,0.1400],[(-0.6000),0.1400],[(-0.6000),(-0.1400)])) 0.5620 0.9380 false 1 [1.2000,3.0600] [0.6000,2.9200] [1.8000,3.2000]
    RF_part #tread "RF_ground_Tread_006_stair S1 tread 6" #(#([0.6000,(-0.1400)],[0.6000,0.1400],[(-0.6000),0.1400],[(-0.6000),(-0.1400)])) 0.7500 1.1250 false 1 [1.2000,3.3400] [0.6000,3.2000] [1.8000,3.4800]
    RF_part #tread "RF_ground_Tread_007_stair S1 tread 8" #(#([0.1400,(-0.6000)],[0.1400,0.6000],[(-0.1400),0.6000],[(-0.1400),(-0.6000)])) 1.1250 1.5000 false 1 [1.9400,4.0800] [1.8000,3.4800] [2.0800,4.6800]
    RF_part #tread "RF_ground_Tread_008_stair S1 tread 9" #(#([0.1400,(-0.6000)],[0.1400,0.6000],[(-0.1400),0.6000],[(-0.1400),(-0.6000)])) 1.3120 1.6880 false 1 [2.2200,4.0800] [2.0800,3.4800] [2.3600,4.6800]
    RF_part #tread "RF_ground_Tread_009_stair S1 tread 10" #(#([0.1400,(-0.6000)],[0.1400,0.6000],[(-0.1400),0.6000],[(-0.1400),(-0.6000)])) 1.5000 1.8750 false 1 [2.5000,4.0800] [2.3600,3.4800] [2.6400,4.6800]
    RF_part #tread "RF_ground_Tread_010_stair S1 tread 11" #(#([0.1400,(-0.6000)],[0.1400,0.6000],[(-0.1400),0.6000],[(-0.1400),(-0.6000)])) 1.6880 2.0620 false 1 [2.7800,4.0800] [2.6400,3.4800] [2.9200,4.6800]
    RF_part #tread "RF_ground_Tread_011_stair S1 tread 12" #(#([0.1400,(-0.6000)],[0.1400,0.6000],[(-0.1400),0.6000],[(-0.1400),(-0.6000)])) 1.8750 2.2500 false 1 [3.0600,4.0800] [2.9200,3.4800] [3.2000,4.6800]
    RF_part #tread "RF_ground_Tread_012_stair S1 tread 13" #(#([0.1400,(-0.6000)],[0.1400,0.6000],[(-0.1400),0.6000],[(-0.1400),(-0.6000)])) 2.0620 2.4380 false 1 [3.3400,4.0800] [3.2000,3.4800] [3.4800,4.6800]
    RF_part #tread "RF_ground_Tread_013_stair S1 tread 14" #(#([0.1400,(-0.6000)],[0.1400,0.6000],[(-0.1400),0.6000],[(-0.1400),(-0.6000)])) 2.2500 2.6250 false 1 [3.6200,4.0800] [3.4800,3.4800] [3.7600,4.6800]
    RF_part #tread "RF_ground_Tread_014_stair S1 tread 15" #(#([0.1650,(-0.6000)],[0.1650,0.6000],[(-0.1650),0.6000],[(-0.1650),(-0.6000)])) 2.4380 2.8120 false 1 [3.9250,4.0800] [3.7600,3.4800] [4.0900,4.6800]
    RF_part #landing "RF_ground_Landing_001_stair S1 landing 7" #(#([0.6000,0.6000],[(-0.6000),0.6000],[(-0.6000),(-0.6000)],[0.6000,(-0.6000)])) 1.1630 1.3120 false 1 [1.2000,4.0800] [0.6000,3.4800] [1.8000,4.6800]
    RF_part #slab "RF_ground_Slab_001" #(#([(-6.0300),(-4.5300)],[6.0300,(-4.5300)],[6.0300,4.5300],[5.7700,4.5300],[5.7700,0.1300],[1.0600,0.1300],[1.0600,4.2700],[2.9300,4.2700],[2.9300,4.5300],[(-6.0300),4.5300])) (-0.2500) 0.0000 false 1 [6.0000,4.5000] [(-0.0300),(-0.0300)] [12.0300,9.0300]
    RF_part #ceiling "RF_ground_Ceiling_001_ceiling" #(#([(-6.0000),4.5000],[(-6.0000),(-4.5000)],[6.0000,(-4.5000)],[6.0000,4.5000],[5.8000,4.5000],[5.8000,0.1000],[1.0300,0.1000],[1.0300,4.3000],[2.9000,4.3000],[2.9000,4.5000]),#([0.0000,(-1.7000)],[0.0000,(-3.7000)],[(-2.6000),(-3.7000)],[(-2.6000),(-1.7000)]),#([(-5.4500),(-1.9100)],[(-5.4500),0.2300],[(-1.9600),0.2300],[(-1.9600),(-1.0700)],[(-4.1500),(-1.0700)],[(-4.1500),(-1.9100)])) 2.6800 2.7000 false 1 [6.0000,4.5000] [0.0000,0.0000] [12.0000,9.0000]
    RF_part #wall "RF_upper_Wall_001" #(#([(-3.5500),(-4.5000)],[3.5500,(-4.5000)],[3.5500,(-3.3000)],[3.3500,(-3.3000)],[3.3500,(-4.3000)],[(-3.3500),(-4.3000)],[(-3.3500),4.3000],[3.3500,4.3000],[3.3500,(-2.4000)],[3.5500,(-2.4000)],[3.5500,4.5000],[(-3.5500),4.5000])) 0.0000 3.0000 true 2 [3.5500,4.5000] [0.0000,0.0000] [7.1000,9.0000]
    RF_part #lintel "RF_upper_Lintel_001_upper-001" #(#([0.1000,0.4490],[(-0.1000),0.4490],[(-0.1000),(-0.4490)],[0.1000,(-0.4490)])) 2.1000 3.0000 true 2 [7.0000,1.6500] [6.9000,1.2010] [7.1000,2.0990]
    RF_part #railing "RF_upper_Railing_001" #(#([(-2.4245),(-2.1500)],[(-2.4245),(-2.2500)],[2.3745,(-2.2500)],[2.3745,(-2.2000)],[2.4245,(-2.2000)],[2.4245,2.2000],[2.3745,2.2000],[2.3745,2.2500],[(-2.4245),2.2500],[(-2.4245),2.1500],[2.3245,2.1500],[2.3245,(-2.1500)])) 0.0000 1.1000 false 2 [9.5255,2.3000] [7.1010,0.0500] [11.9500,4.5500]
    RF_part #slab "RF_upper_Slab_001" #(#([5.9800,(-4.4300)],[5.9800,0.0300],[1.1800,0.0300],[1.1800,4.5300],[(-5.9800),4.5300],[(-5.9800),(-4.5300)],[1.1800,(-4.5300)],[1.1800,(-4.4300)]),#([(-2.5510),(-1.6990)],[0.0510,(-1.6990)],[0.0510,(-3.7010)],[(-2.5510),(-3.7000)]),#([(-4.0990),(-1.0710)],[(-4.0990),(-1.9110)],[(-5.4000),(-1.9110)],[(-5.4010),0.2300],[(-1.9100),0.2310],[(-1.9100),(-1.0710)])) (-0.2500) 0.0000 false 2 [5.9500,4.5000] [(-0.0300),(-0.0300)] [11.9300,9.0300]
    RF_part #ceiling "RF_upper_Ceiling_001_ceiling" #(#([3.5500,4.5000],[(-3.5500),4.5000],[(-3.5500),(-4.5000)],[3.5500,(-4.5000)])) 2.6800 2.7000 false 2 [3.5500,4.5000] [0.0000,0.0000] [7.1000,9.0000]
    RF_lines "RF_ground_Stairs" #(#([(-2.1000),(-0.6000)],[(-2.1000),0.6000]),#([(-1.8200),(-0.6000)],[(-1.8200),0.6000]),#([(-1.5400),(-0.6000)],[(-1.5400),0.6000]),#([(-1.2600),(-0.6000)],[(-1.2600),0.6000]),#([(-0.9800),(-0.6000)],[(-0.9800),0.6000]),#([(-0.7000),(-0.6000)],[(-0.7000),0.6000]),#([(-0.4200),(-0.6000)],[(-0.4200),0.6000]),#([(-0.1400),(-0.6000)],[(-0.1400),0.6000]),#([0.1400,(-0.6000)],[0.1400,0.6000]),#([0.4200,(-0.6000)],[0.4200,0.6000]),#([0.7000,(-0.6000)],[0.7000,0.6000]),#([0.9800,(-0.6000)],[0.9800,0.6000]),#([1.2600,(-0.6000)],[1.2600,0.6000]),#([1.5400,(-0.6000)],[1.5400,0.6000]),#([1.8200,(-0.6000)],[1.8200,0.6000]),#([2.1000,(-0.6000)],[2.1000,0.6000]),#([(-2.1000),(-0.6000)],[2.1000,(-0.6000)]),#([(-2.1000),0.6000],[2.1000,0.6000])) 1 [3.1000,8.0000] "Stairs"
    RF_room "LIVING" [3.0000,5.8000] 1
    RF_room "DINING" [5.2000,2.6000] 1
    RF_room "KITCHEN" [8.6000,3.4000] 1
    RF_room "GARAGE" [9.0000,6.6000] 1
    RF_room "LOUNGE" [3.0000,6.0000] 2
    local origin = point name:"RF_ORIGIN_DWG" size:1.0 pos:[0.0 - RF_shift.x, 0.0 - RF_shift.y, 0.0]
    origin.isHidden = true
    origin.ignoreExtents = true
    (RF_layer "RF_Datums").addNode origin
    setUserProp origin "Source" "rooms-reference-ground.dxf + rooms-reference-upper.dxf, DXF exported by its own program; drawing units mm, model in metres"
    setUserProp origin "Levels" ("floor levels " + (RF_levels as string) + " m, wall heights " + (RF_heights as string) + " m")
    setUserProp origin "Built" "by the walkthrough app, 11 Nov 2026 (model data 2da587ccc0bd)"
    viewport.setType #view_iso_user
    select RF_nodes
    max zoomext sel all
    clearSelection()
    redrawViews()
    format "RF BUILD COMPLETE: % objects in % s, % failed checks\n" RF_nodes.count ((timeStamp() - t0) / 1000.0) RF_failed.count
    for f in RF_failed do format "  check failed: %\n" f
    true
)
try (destroyDialog RF_UI) catch ()
rollout RF_UI "Reference" width:340
(
    label info "Open a new empty scene before Build." align:#left
    label units1 "Build sets System Units to metres." align:#left
    checkbox dwg "At the drawing's own coordinates" checked:true tooltip:"Untick to centre the model on the origin"
    spinner lv1 "Ground floor floor level (m):" range:[-50, 500, 0.00] type:#float fieldwidth:60
    spinner ht1 "Ground floor wall height (m):" range:[2.2, 15, 3.00] type:#float fieldwidth:60
    spinner lv2 "Upper floor floor level (m):" range:[-50, 500, 3.00] type:#float fieldwidth:60
    spinner ht2 "Upper floor wall height (m):" range:[2.2, 15, 3.00] type:#float fieldwidth:60
    checkbox cm "Collapse to Editable Mesh (no live modifiers)" checked:false
    button build "BUILD THE MODEL" width:310 height:32
    label note1 "Parts stay live: spline + Extrude (mesh) + Smooth." align:#left
    group "After the build"
    (
        button upd "Update levels and heights" width:300
        button col "Collapse all now (Editable Mesh)" width:300
    )
    on build pressed do
    (
        RF_levels = #(lv1.value,lv2.value)
        RF_heights = #(ht1.value,ht2.value)
        RF_collapse = cm.checked
        RF_shift = if dwg.checked then [0.0, 0.0] else [6.0000, 4.5000]
        try
        (
            if RF_build() do
            (
                if RF_failed.count == 0 then messageBox ("Built " + (RF_nodes.count as string) + " objects. Every part passed the closed-solid, height and position checks. Save As to keep your .max file.") title:"Reference"
                else messageBox ((RF_failed.count as string) + " part(s) failed a check and are on layer RF_Check_Failed (listed in the MAXScript Listener). Everything else was built.") title:"Reference"
            )
        )
        catch (messageBox (getCurrentException()) title:"Build stopped")
    )
    on upd pressed do
    (
        local r = RF_updateLevels #(lv1.value,lv2.value) #(ht1.value,ht2.value)
        messageBox ("Every part moved to its level; " + (r[1] as string) + " parts set to their level's wall height." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were collapsed already and kept their height.") else "")) title:"Reference"
    )
    on col pressed do
    (
        local n = RF_collapseAll()
        messageBox ((n as string) + " parts collapsed to Editable Mesh.") title:"Reference"
    )
)
createDialog RF_UI
