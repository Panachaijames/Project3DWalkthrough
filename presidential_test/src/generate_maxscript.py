"""Write Presidential_Suite.ms: a 3ds Max script that builds the presidential suite from pres2_model.json.

Owner's choice (19 Oct): no Editable Poly. Every part stays LIVE: an editable spline (the outline, with its inner loops)
+ an Extrude modifier whose output is a MESH + a Smooth modifier (auto-smooth 25 deg: curves and round columns shade
smooth, the suite's 30/45-degree corners stay sharp). So:
- heights stay editable: change the Extrude amount on one object, or use "Update heights" in the script's window for all;
- outlines stay editable: edit the spline's vertices under the modifiers;
- "Collapse to Editable Mesh" (a tick box before Build, or a button afterwards) turns them into Editable Mesh objects.
Each object's pivot is at the middle of its own outline, on its base. Each part is checked as it is built (closed solid,
height, position); a part that fails goes on layer PS_Check_Failed and is listed at the end, and the rest is still built.
Nothing in a scene that already has objects is changed. Build sets System Units to metres (it says so in its window).
Placed at the DWG's own coordinates in metres (to line up with the DWG imported in metres), or centred on the origin.
Furniture (owner's decision of 28 Oct 2026, contract in furniture/README.md): when the model has 'furniture' (section 6 of
build_model.py; one level, key 'suite'), Build also makes one coloured Box per piece (colour = kind; live, never an Editable
Poly) and the window gets a text box per kind for its height in mm, "Apply furniture heights" and "Furniture boxes only" (the
parts carry no PS_floor, so that mode takes the level from the "Floor level" spinner and says so). That code is in
furniture/furniture_max.py, spliced in at the __FURN_*__ lines of the template below; a model without furniture gives the
script it gave before, byte for byte.
Usage: python generate_maxscript.py <out.ms>
"""
import hashlib, json, math, re, sys, unicodedata
from pathlib import Path
from shapely.geometry import Polygon, LinearRing

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / 'furniture')); import furniture_max
RAW = (HERE / 'pres2_model.json').read_bytes()
M = json.loads(RAW.decode('utf-8'))
SHA = hashlib.sha1(RAW).hexdigest()[:12]
ox, oy = M['offset']                       # the model is centred; add this back for the DWG's own coordinates
FTF = M['floorToFloor']

# kind -> follows the wall height? (walls, columns, lintels, full-height glass); a part can say so itself ('follow')
FOLLOW = {'wall': True, 'column': True, 'lintel': True, 'glass': True, 'builtin': False,
          'low': False, 'balustrade': False, 'slab': False, 'deck': False, 'post': False}


def ascii_name(s):                         # Max object names and text: plain ASCII ("Tổ hợp Khách Ăn" -> "To hop Khach An")
    s = s.replace('Đ', 'D').replace('đ', 'd')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return ' '.join(s.replace('"', "'").replace('\\', '/').split())


def signed(loop): return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(loop, loop[1:] + loop[:1])) / 2
def arr(v): return '#(' + ','.join(v) + ')'
def num(v): return f'({v:.4f})' if v < 0 else f'{v:.4f}'        # negative numbers in brackets: never read as a minus
def pt(p): return f'[{num(p[0])},{num(p[1])}]'


problems, calls, count = [], [], {}
for part in M['parts']:
    kind = part['kind']
    if kind not in FOLLOW: problems.append(f'unknown kind {kind}'); continue
    count[kind] = count.get(kind, 0) + 1
    name = f"PS_{kind.capitalize()}_{count[kind]:03}" + (f"_{ascii_name(part['label'])}" if part.get('label') else '')
    outer = [(x + ox, y + oy) for x, y in part['o']]
    holes = [[(x + ox, y + oy) for x, y in h] for h in part['h']]
    if not Polygon(outer, holes).is_valid: problems.append(f'{name}: invalid polygon')
    for loop in [outer] + holes:
        if len(loop) < 3: problems.append(f'{name}: loop with fewer than 3 points')
        for a, b in zip(loop, loop[1:] + loop[:1]):
            if math.dist(a, b) < 1e-4: problems.append(f'{name}: repeated point')
    for h in holes:                        # Extrude cannot cap a hole that touches the outline
        if LinearRing(h).distance(LinearRing(outer)) < 5e-4: problems.append(f'{name}: a hole touches the outline')
    mn = (min(x for x, _ in outer), min(y for _, y in outer)); mx = (max(x for x, _ in outer), max(y for _, y in outer))
    c = ((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2)              # the object's pivot: the middle of its outline
    loops = []
    for j, loop in enumerate([outer] + holes):          # outer counter-clockwise, holes clockwise; relative to c
        if (signed(loop) > 0) != (j == 0): loop = loop[::-1]
        loops.append(arr([pt((x - c[0], y - c[1])) for x, y in loop]))
    follow = 'true' if part.get('follow', FOLLOW[kind]) else 'false'
    calls.append(f'    PS_part #{kind} "{name}" {arr(loops)} {num(part["z0"])} {num(part["z1"])} {follow} {pt(c)} {pt(mn)} {pt(mx)}')
rooms = [f'    PS_room "{ascii_name(r["name"])}" {pt((r["x"] + ox, r["y"] + oy))}' for r in M['rooms']]
FURN, furn_problems = furniture_max.fragments(M, 'PS', [{'key': 'suite'}], '#(PS_level)', 'Presidential suite')
problems += furn_problems

header = r'''-- PRESIDENTIAL SUITE (TEST) / from "layout presidential test.dwg" / built by the CAD-to-3D test pipeline, 19 Oct 2026
-- Same model as presidential_3d_preview.html (model data __SHA__). Floor to floor __FTF__ m, as given for the project.
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
global PS_height = __FTF__
global PS_collapse = false
global PS_shift = [0.0, 0.0]
global PS_mats
__FURN_GLOBALS__

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
__FURN_FUNCTIONS__
fn PS_build =
(
__FURN_ADDONLY__
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
'''

footer = r'''
__FURN_BUILD__
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
    spinner ht "Floor to floor (m):" range:[2.2, 15, __FTF__] type:#float fieldwidth:70
__FURN_UI__
    checkbox cm "Collapse to Editable Mesh (no live modifiers)" checked:false
    button build "BUILD THE SUITE" width:310 height:32
    label note1 "Parts stay live: spline + Extrude (mesh) + Smooth." align:#left
    group "After the build"
    (
        button upd "Update heights to Floor to floor" width:300
        button col "Collapse all now (Editable Mesh)" width:300
__FURN_UI_AFTER__
    )
    on build pressed do
    (
        PS_level = lv.value
        PS_height = ht.value
        PS_collapse = cm.checked
        PS_shift = if dwg.checked then [0.0, 0.0] else [__OX__, __OY__]
__FURN_READ__
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
__FURN_HANDLERS__
)
createDialog PS_UI
'''

if problems:
    print('DATA PROBLEMS:'); print('\n'.join(problems[:30])); sys.exit(1)
script = (header + '\n'.join(calls + rooms) + footer).replace('__FTF__', f'{FTF:.2f}').replace('__SHA__', SHA) \
    .replace('__OX__', f'{ox:.4f}').replace('__OY__', num(oy))
script = furniture_max.splice(script, FURN)
out = Path(sys.argv[1])
out.write_text(script, encoding='utf-8')
print(FURN['summary'])
print('written', out, f'{len(script) // 1024} KB | model', SHA, '|', ', '.join(f'{k} {v}' for k, v in count.items()), '| room names', len(rooms))
print('balanced ( ):', script.count('(') == script.count(')'), '| [ ]:', script.count('[') == script.count(']'),
      '| even quotes:', script.count('"') % 2 == 0, '| ascii only:', all(ord(c) < 128 for c in script),
      '| no placeholders left:', not re.search(r'__[A-Z]+(?:_[A-Z]+)*__', script))
