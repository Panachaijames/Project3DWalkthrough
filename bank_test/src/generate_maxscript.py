"""Write Bangkok_Bank_Sampeng.ms: a 3ds Max script that builds the bank branch (both levels) from bank_model.json.

The pattern of presidential_test/src/generate_maxscript.py (run in real 3ds Max by the owner on 26 Oct: good), for
two levels. Owner's choice (19 Oct): no Editable Poly. Every part stays LIVE: an editable spline (the outline, with its
inner loops) + an Extrude modifier whose output is a MESH + a Smooth modifier (auto-smooth 25 deg: the curved terrace
wall shades smooth, 30/45-degree corners stay sharp). So:
- heights stay editable: change the Extrude amount on one object, or use "Update levels and heights" in the script's
  window (walls, columns, full-height glass and lintel tops follow each level's wall height; every part moves with its
  level);
- outlines stay editable: edit the spline's vertices under the modifiers;
- "Collapse to Editable Mesh" (a tick box before Build, or a button afterwards) turns them into Editable Mesh objects.
Each object's pivot is at the middle of its own outline, on its base. Each part is checked as it is built (closed solid,
height, position); a part that fails goes on layer BB_Check_Failed and is listed at the end, and the rest is still built.
Layers per level and kind (BB_L1_Walls, BB_L2_Lintels, ...). The stairs come across as plain splines (BB_L1_Stairs).
Nothing in a scene that already has objects is changed. Build sets System Units to metres (it says so in its window).
Placed at the DWG's own coordinates in metres (to line up with the DWGs imported in metres), or centred on the origin.
Furniture (owner's decision of 28 Oct 2026, contract in furniture/README.md): when the model has 'furniture' (rule 12 of
build_model.py), Build also makes one coloured Box per piece (colour = kind; live, never an Editable Poly) and the window
gets a text box per kind for its height in mm, "Apply furniture heights" and "Furniture boxes only". That code is in
furniture/furniture_max.py, spliced in at the __FURN_*__ lines of the template below; a model without furniture gives the
script it gave before, byte for byte.
Usage: python generate_maxscript.py <out.ms>
"""
import hashlib, json, math, re, sys, unicodedata
from pathlib import Path
from shapely.geometry import Polygon, LinearRing

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / 'furniture')); import furniture_max
RAW = (HERE / 'bank_model.json').read_bytes()
M = json.loads(RAW.decode('utf-8'))
SHA = hashlib.sha1(RAW).hexdigest()[:12]
ox, oy = M['offset']                       # the model is centred; add this back for the DWG's own coordinates
PX = M.get('maxPrefix', 'BB')
FLOORS = M['floors']
FI = {f['key']: i + 1 for i, f in enumerate(FLOORS)}       # MAXScript arrays count from 1

# kind -> (layer suffix, material); whether the top follows the wall height comes with each part ('follow')
KINDS = {'wall': ('Walls', 'Wall'), 'column': ('Columns', 'Wall'), 'lintel': ('Lintels', 'Wall'), 'sill': ('Sills', 'Wall'),
         'parapet': ('Parapets', 'Wall'), 'glass': ('Glass', 'Glass'), 'mullion': ('GlassFrames', 'Frame'),
         'railing': ('Railings', 'Rail'), 'single': ('SingleLines', 'Single'), 'step': ('Steps', 'Step'), 'slab': ('Slab', 'Slab')}


def ascii_name(s):                         # Max object names and text: plain ASCII
    s = s.replace('²', '2').replace('·', '-')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return ' '.join(s.replace('"', "'").replace('\\', '/').split())


def signed(loop): return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(loop, loop[1:] + loop[:1])) / 2
def arr(v): return '#(' + ','.join(v) + ')'
def num(v): return f'({v:.4f})' if v < 0 else f'{v:.4f}'        # negative numbers in brackets: never read as a minus
def pt(p): return f'[{num(p[0])},{num(p[1])}]'


problems, calls, count = [], [], {}
for part in M['parts']:
    kind, fl = part['kind'], part['floor']
    if kind not in KINDS: problems.append(f'unknown kind {kind}'); continue
    key = (fl, kind)
    count[key] = count.get(key, 0) + 1
    name = f"{PX}_{fl}_{kind.capitalize()}_{count[key]:03}" + (f"_{ascii_name(part['label'])}" if part.get('label') else '')
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
    follow = 'true' if part.get('follow') else 'false'
    calls.append(f'    {PX}_part #{kind} "{name}" {arr(loops)} {num(part["z0"])} {num(part["z1"])} {follow} {FI[fl]} {pt(c)} {pt(mn)} {pt(mx)}')

# Stairs: open splines (tread lines below the cut; flights above the cut on their own layer), pivot in their middle.
lines = []
for fl, st in M.get('stairs', {}).items():
    for part_name, a in (('Stairs', st['below']), ('StairsAbove', st['above'])):
        if not a: continue
        segs = [((a[i] + ox, a[i + 1] + oy), (a[i + 2] + ox, a[i + 3] + oy)) for i in range(0, len(a), 4)]
        xs = [p[0] for s in segs for p in s]; ys = [p[1] for s in segs for p in s]
        c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        sp = arr([arr([pt((p[0] - c[0], p[1] - c[1])) for p in s]) for s in segs])
        lines.append(f'    {PX}_lines "{PX}_{fl}_{part_name}" {sp} {FI[fl]} {pt(c)} "{part_name}"')
rooms = [f'    {PX}_room "{ascii_name(r["label"])}" {pt((r["x"] + ox, r["y"] + oy))} {FI[r["floor"]]}' for r in M['rooms']]

FURN, furn_problems = furniture_max.fragments(M, PX, FLOORS, f'{PX}_levels', ascii_name(M.get('shortName', M['project'])))
problems += furn_problems
levels = arr([f"{f['level']:.2f}" for f in FLOORS])
heights = arr([f"{f['wallHeight']:.2f}" for f in FLOORS])
names = arr([f'"{f["key"]}"' for f in FLOORS])
spinners = '\n'.join(
    f'    spinner lv{i + 1} "{f["name"]} floor level (m):" range:[-50, 500, {f["level"]:.2f}] type:#float fieldwidth:60\n'
    f'    spinner ht{i + 1} "{f["name"]} wall height (m):" range:[2.2, 15, {f["wallHeight"]:.2f}] type:#float fieldwidth:60'
    for i, f in enumerate(FLOORS))
read_levels = arr([f'lv{i + 1}.value' for i in range(len(FLOORS))])
read_heights = arr([f'ht{i + 1}.value' for i in range(len(FLOORS))])
source = ' + '.join(M['source'])

header = r'''-- __PROJECT__ (TEST) / from "__SOURCE__" / built by the CAD-to-3D test pipeline, 27 Oct 2026
-- Same model as bank_3d_preview.html (model data __SHA__). Floor levels __LEVELTXT__ m, wall heights __HEIGHTTXT__ m.
-- Placed at the DWG's own coordinates in metres (to line up with the DWGs imported in metres), or centred on the origin
-- if you untick that box in the script's window.
-- Every part stays LIVE (no Editable Poly): an editable spline outline + an Extrude modifier (output: Mesh) + Smooth.
--   * Change a height: the Extrude amount on that object, or "Update levels and heights" in this script's window.
--   * Change an outline: select the spline level under the modifiers and move vertices.
--   * Editable Mesh: tick "Collapse to Editable Mesh" before Build, or press "Collapse all now" later.
-- Each object's pivot is at the middle of its own outline, on its base. Layers per level and kind (__PX___L1_Walls ...).
-- Glass partitions (Revit glass wall types) are their own objects on __PX___<level>_Glass, at the height their type
-- name gives (2600H = 2.60 m); "Update levels and heights" keeps them, the parapet and the stair steps at their own
-- heights (only parts marked to follow the wall height change).
-- Each part is checked as it is built (closed solid, height, position). A part that fails is kept on layer
-- __PX___Check_Failed and listed in the MAXScript Listener; the rest is still built.
-- Build sets System Units to metres. Nothing in an existing scene is changed: run it in a NEW EMPTY scene.
global __PX___UI
global __PX___nodes = #()
global __PX___failed = #()
global __PX___levels = __LEVELS__
global __PX___heights = __HEIGHTS__
global __PX___floorNames = __NAMES__
global __PX___collapse = false
global __PX___shift = [0.0, 0.0]
global __PX___mats
__FURN_GLOBALS__

fn __PX___layer n =
(
    local ly = LayerManager.getLayerFromName n
    if ly == undefined do ly = LayerManager.newLayerFromName n
    ly
)
fn __PX___mat key =
(
    local m = undefined
    for x in __PX___mats where x.name == ("__PX__ " + key) do m = x
    m
)
fn __PX___makeMaterials =
(
    __PX___mats = #()
    append __PX___mats (standardMaterial name:"__PX__ Wall" diffuse:(color 227 221 211))
    append __PX___mats (standardMaterial name:"__PX__ Glass" diffuse:(color 170 200 214) opacity:30 specularLevel:60 glossiness:60)
    append __PX___mats (standardMaterial name:"__PX__ Rail" diffuse:(color 119 114 124))
    append __PX___mats (standardMaterial name:"__PX__ Single" diffuse:(color 224 164 88))
    append __PX___mats (standardMaterial name:"__PX__ Slab" diffuse:(color 212 216 210))
    append __PX___mats (standardMaterial name:"__PX__ Frame" diffuse:(color 93 107 116))
    append __PX___mats (standardMaterial name:"__PX__ Step" diffuse:(color 185 199 180))
)
fn __PX___num v = ((v as string) as float)
-- The outline's knots are relative to c, the middle of the outline; the node is then moved to c, so that is its pivot.
fn __PX___shape nm loops =
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
fn __PX___extrudeOf o =
(
    local ex = undefined
    for md in o.modifiers where classOf md == Extrude do ex = md
    ex
)
-- kind: #wall #column #lintel #sill #parapet #glass #mullion #railing #single #step #slab; z0/z1 in metres above the
-- level of floor fi (a step of a flight going down from a level starts below it);
-- follow = the top follows that level's wall height. c = pivot, mn/mx = outline extents (DWG coordinates).
fn __PX___part kind nm loops z0 z1 follow fi c mn mx =
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
    local lvl = __PX___levels[fi]
    local top = if follow then __PX___heights[fi] else z1
    local zb = lvl + z0
    local ht = top - z0
    local o = __PX___shape nm loops
    o.pos = [c.x - __PX___shift.x, c.y - __PX___shift.y, zb]
    addModifier o (Extrude amount:ht segs:1 capStart:true capEnd:true output:1 smooth:false)
    addModifier o (Smooth autoSmooth:true threshold:25.0)
    local mt = __PX___mat info[2]
    o.material = mt
    o.wirecolor = mt.diffuse
    setUserProp o "__PX___kind" (kind as string)
    setUserProp o "__PX___floor" fi
    setUserProp o "__PX___base" z0
    setUserProp o "__PX___follow" follow
    -- the checks run on the evaluated mesh (what the modifiers produce)
    local m = snapshotAsMesh o
    local why = ""
    local tol = 0.002
    if m.numfaces < 3 then why = "no faces"
    else if (meshop.getOpenEdges m).numberSet != 0 then why = "open edges (not a closed solid)"
    else if abs(o.min.z - zb) > tol or abs(o.max.z - (zb + ht)) > tol then why = "height"
    else if abs(o.min.x - (mn.x - __PX___shift.x)) > tol or abs(o.min.y - (mn.y - __PX___shift.y)) > tol or abs(o.max.x - (mx.x - __PX___shift.x)) > tol or abs(o.max.y - (mx.y - __PX___shift.y)) > tol then why = "position"
    m = undefined
    if why == "" then
    (
        (__PX___layer ("__PX___" + __PX___floorNames[fi] + "_" + info[1])).addNode o
        setUserProp o "__PX___check" "ok"
    )
    else
    (
        (__PX___layer "__PX___Check_Failed").addNode o
        setUserProp o "__PX___check" why
        append __PX___failed (nm + ": " + why)
    )
    if __PX___collapse do convertToMesh o
    append __PX___nodes o
    o
)
-- Stair lines: one shape of open two-knot splines per level and kind, knots relative to c (its pivot).
fn __PX___lines nm segs fi c lay =
(
    local o = splineShape name:nm
    for k = 1 to segs.count do
    (
        addNewSpline o
        addKnot o k #corner #line [segs[k][1].x, segs[k][1].y, 0]
        addKnot o k #corner #line [segs[k][2].x, segs[k][2].y, 0]
    )
    updateShape o
    o.pos = [c.x - __PX___shift.x, c.y - __PX___shift.y, __PX___levels[fi]]
    o.wirecolor = if lay == "Stairs" then (color 46 139 71) else (color 160 210 170)
    setUserProp o "__PX___floor" fi
    setUserProp o "__PX___base" 0.0
    (__PX___layer ("__PX___" + __PX___floorNames[fi] + "_" + lay)).addNode o
    append __PX___nodes o
    o
)
fn __PX___room nm p fi =
(
    local t = text text:nm size:0.3 pos:[p.x - __PX___shift.x, p.y - __PX___shift.y, __PX___levels[fi] + 0.02]
    t.name = "__PX___Room_" + __PX___floorNames[fi] + "_" + nm
    t.wirecolor = color 30 60 110
    setUserProp t "__PX___floor" fi
    setUserProp t "__PX___base" 0.02
    (__PX___layer ("__PX___" + __PX___floorNames[fi] + "_RoomNames")).addNode t
    append __PX___nodes t
    t
)
-- After the build: move every part to its level and set every live part whose top follows the wall height to its
-- level's new wall height.
fn __PX___updateLevels newLevels newHeights =
(
    local n = 0
    local skipped = 0
    for o in objects where (getUserProp o "__PX___floor") != undefined do
    (
        local fi = (__PX___num (getUserProp o "__PX___floor")) as integer
        local base = __PX___num (getUserProp o "__PX___base")
        o.pos.z = newLevels[fi] + base
        if ((getUserProp o "__PX___follow") as string) == "true" do
        (
            local ex = __PX___extrudeOf o
            if ex == undefined then skipped += 1
            else ( ex.amount = newHeights[fi] - base; n += 1 )
        )
    )
    __PX___levels = newLevels
    __PX___heights = newHeights
    #(n, skipped)
)
fn __PX___collapseAll =
(
    local n = 0
    for o in objects where (getUserProp o "__PX___kind") != undefined and o.modifiers.count > 0 do ( convertToMesh o; n += 1 )
    n
)
__FURN_FUNCTIONS__
fn __PX___build =
(
__FURN_ADDONLY__
    if objects.count > 0 then
    (
        messageBox "Open a NEW EMPTY scene first. Nothing in this scene has been changed." title:"__SHORT__"
        return false
    )
    units.systemType = #meters
    units.systemScale = 1.0
    units.displayType = #metric
    units.metricType = #meters
    __PX___nodes = #()
    __PX___failed = #()
    __PX___makeMaterials()
    local t0 = timeStamp()
'''

footer = r'''
__FURN_BUILD__
    local origin = point name:"__PX___ORIGIN_DWG" size:1.0 pos:[0.0 - __PX___shift.x, 0.0 - __PX___shift.y, 0.0]
    origin.isHidden = true
    origin.ignoreExtents = true
    (__PX___layer "__PX___Datums").addNode origin
    setUserProp origin "Source" "__SOURCE__, converted with LibreDWG; drawing units mm, model in metres"
    setUserProp origin "Levels" ("floor levels " + (__PX___levels as string) + " m, wall heights " + (__PX___heights as string) + " m")
    viewport.setType #view_iso_user
    select __PX___nodes
    max zoomext sel all
    clearSelection()
    redrawViews()
    format "__PX__ BUILD COMPLETE: % objects in % s, % failed checks\n" __PX___nodes.count ((timeStamp() - t0) / 1000.0) __PX___failed.count
    for f in __PX___failed do format "  check failed: %\n" f
    true
)
try (destroyDialog __PX___UI) catch ()
rollout __PX___UI "__SHORT__ (test)" width:340
(
    label info "Open a new empty scene before Build." align:#left
    label units1 "Build sets System Units to metres." align:#left
    checkbox dwg "At the drawing's own coordinates" checked:true tooltip:"Untick to centre the model on the origin"
__SPINNERS__
__FURN_UI__
    checkbox cm "Collapse to Editable Mesh (no live modifiers)" checked:false
    button build "BUILD THE MODEL" width:310 height:32
    label note1 "Parts stay live: spline + Extrude (mesh) + Smooth." align:#left
    group "After the build"
    (
        button upd "Update levels and heights" width:300
        button col "Collapse all now (Editable Mesh)" width:300
__FURN_UI_AFTER__
    )
    on build pressed do
    (
        __PX___levels = __READLEVELS__
        __PX___heights = __READHEIGHTS__
        __PX___collapse = cm.checked
        __PX___shift = if dwg.checked then [0.0, 0.0] else [__OX__, __OY__]
__FURN_READ__
        try
        (
            if __PX___build() do
            (
                if __PX___failed.count == 0 then messageBox ("Built " + (__PX___nodes.count as string) + " objects. Every part passed the closed-solid, height and position checks. Save As to keep your .max file.") title:"__SHORT__"
                else messageBox ((__PX___failed.count as string) + " part(s) failed a check and are on layer __PX___Check_Failed (listed in the MAXScript Listener). Everything else was built.") title:"__SHORT__"
            )
        )
        catch (messageBox (getCurrentException()) title:"Build stopped")
    )
    on upd pressed do
    (
        local r = __PX___updateLevels __READLEVELS__ __READHEIGHTS__
        messageBox ("Every part moved to its level; " + (r[1] as string) + " parts set to their level's wall height." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were collapsed already and kept their height.") else "")) title:"__SHORT__"
    )
    on col pressed do
    (
        local n = __PX___collapseAll()
        messageBox ((n as string) + " parts collapsed to Editable Mesh.") title:"__SHORT__"
    )
__FURN_HANDLERS__
)
createDialog __PX___UI
'''

if problems:
    print('DATA PROBLEMS:'); print('\n'.join(problems[:30])); sys.exit(1)
script = (header + '\n'.join(calls + lines + rooms) + footer)
script = furniture_max.splice(script, FURN)
for k, v in (('__SPINNERS__', spinners), ('__READLEVELS__', read_levels), ('__READHEIGHTS__', read_heights),
             ('__LEVELTXT__', ' / '.join(f"{f['level']:+.2f}" for f in FLOORS)),
             ('__HEIGHTTXT__', ' / '.join(f"{f['wallHeight']:.2f}" for f in FLOORS)),
             ('__LEVELS__', levels), ('__HEIGHTS__', heights), ('__NAMES__', names), ('__SHA__', SHA),
             ('__SOURCE__', ascii_name(source)), ('__PROJECT__', ascii_name(M['project']).upper()),
             ('__SHORT__', ascii_name(M.get('shortName', M['project']))),
             ('__OX__', f'{ox:.4f}'), ('__OY__', num(oy)), ('__PX__', PX)):
    script = script.replace(k, v)
out = Path(sys.argv[1])
out.write_text(script, encoding='utf-8')
print(FURN['summary'])
by_kind = {}
for (fl, kind), n in count.items(): by_kind[kind] = by_kind.get(kind, 0) + n
print('written', out, f'{len(script) // 1024} KB | model', SHA, '|', ', '.join(f'{k} {v}' for k, v in by_kind.items()),
      '| stair shapes', len(lines), '| room names', len(rooms))
print('balanced ( ):', script.count('(') == script.count(')'), '| [ ]:', script.count('[') == script.count(']'),
      '| even quotes:', script.count('"') % 2 == 0, '| ascii only:', all(ord(c) < 128 for c in script),
      '| no placeholders left:', not re.search(r'__[A-Z]+(?:_[A-Z]+)*__', script))
