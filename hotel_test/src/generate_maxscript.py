"""Write Hotel_Lobby.ms: a 3ds Max script that builds the hotel (floor 1 and floor 2) from hotel_model.json.

The bank's generator (bank_test/src/generate_maxscript.py) for a model read from two PICTURES instead of a CAD drawing. The
bank's script was run in real 3ds Max by the 3D team on 28 Oct (structure to their satisfaction), so this script's code is the
bank's, line for line, with the prefix HL and this model's data; the only lines that differ are the words that must change
because there is no DWG (the header, the datum's Source and Picture properties, the tooltip of the placement tick box).
test_hotel_maxscript.py lists those lines and checks that nothing else differs from the bank's scripts. The rules, with sizes
in metres:
 1. LIVE PARTS (owner's choice of 19 Oct: no Editable Poly). Every part is an editable spline (its outline with its inner
    loops) + an Extrude modifier whose output is a MESH + a Smooth modifier (auto-smooth 25 degrees). Heights stay editable:
    the Extrude amount on one object, or "Update levels and heights" in the script's window (every part moves with its floor;
    the tops of the parts marked 'follow' take the floor's wall height: here walls, mullions, glass and lintels; railings,
    steps and slabs keep theirs). Outlines stay editable: the spline's vertices under the modifiers. "Collapse to Editable
    Mesh" (a tick box before Build, or a button afterwards) turns them into Editable Mesh objects.
 2. PIVOTS AND CHECKS. Each object's pivot is the middle of its own outline, on its base. Each part is checked as it is built
    (closed solid; height and position within 0.002 m); a part that fails goes on layer HL_Check_Failed and is listed at the
    end, and the rest is still built. Layers per floor and kind (HL_F1_Walls, HL_F2_Lintels, ...).
 3. THE FRAME. The pictures have no coordinates of their own; the model's drawing frame stands in for the DWG's (rule 2 of
    build_model.py): metres, y up, 0,0 at the north-west outer corner of the lift core on both floors, so that the floors
    stack. "At the drawing's own coordinates" (ticked) places the model there (model + offset); unticked, it is centred on
    the origin. The hidden datum HL_ORIGIN_DWG (the name the furniture code looks for) stands at that corner and carries, per
    floor, where its picture goes (a plane's size in metres along x and along y and its centre from the datum, from the
    model's pictureFrame, which has a scale per axis: pixels per metre along x and along y), so the 3D team can lay each
    picture under its floor. The header and the datum's Source say how the pictures were scaled: from the owner's one real
    dimension of 2 Nov 2026, the main stair's width (the width of the steps of the flight from the lowest floor).
 4. STAIRS AND NAMES. Stair lines that are not built as steps (the model's 'stairs') come across as plain splines
    (HL_F2_Stairs); room names as text shapes 0.3 m high, 0.02 m above their floor.
 5. FURNITURE (owner's decision of 28 Oct, contract furniture/README.md): one coloured Box per piece (colour = kind; live,
    never an Editable Poly) on a layer per floor and kind, a height spinner per kind in mm, "Apply furniture heights" and
    "Furniture boxes only". That code is furniture/furniture_max.py, spliced in at the __FURN_*__ lines of the template below
    (its recipe); a model without furniture gives the script without any of it.
 6. SAFETY. Nothing in a scene that already has objects is changed. Build sets System Units to metres (its window says so).
 7. DATA. A part Extrude could not cap is refused before anything is written, as in the bank: an invalid outline, a loop of
    fewer than 3 points, two points closer than 0.0001 m, a hole within 0.0005 m of its outline; here also two holes within
    0.0005 m of each other (the slab of floor 2 has several: the stair, the lifts, a riser and a duct).
Usage: python generate_maxscript.py <out.ms>
"""
import hashlib, json, math, posixpath, re, sys, unicodedata
from pathlib import Path
from shapely.geometry import Polygon, LinearRing

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / 'furniture')); import furniture_max
RAW = (HERE / 'hotel_model.json').read_bytes()
M = json.loads(RAW.decode('utf-8'))
SHA = hashlib.sha1(RAW).hexdigest()[:12]                   # the viewer page carries the same stamp
ox, oy = M['offset']                       # the model is centred; add this back for the drawing's own coordinates
PX = M.get('maxPrefix', 'HL')
FLOORS = M['floors']
FI = {f['key']: i + 1 for i, f in enumerate(FLOORS)}       # MAXScript arrays count from 1
PAGE = 'hotel_3d_preview.html'             # the viewer page beside the script (the projects' <name>_3d_preview.html)
FRAME = "0,0 is the lift core's north-west corner on both floors, y up"      # rule 2 of build_model.py

# kind -> (layer suffix, material); whether the top follows the wall height comes with each part ('follow')
KINDS = {'wall': ('Walls', 'Wall'), 'column': ('Columns', 'Wall'), 'lintel': ('Lintels', 'Wall'), 'sill': ('Sills', 'Wall'),
         'parapet': ('Parapets', 'Wall'), 'glass': ('Glass', 'Glass'), 'mullion': ('GlassFrames', 'Frame'),
         'railing': ('Railings', 'Rail'), 'single': ('SingleLines', 'Single'), 'step': ('Steps', 'Step'), 'slab': ('Slab', 'Slab')}
PLURAL = {'wall': 'walls', 'column': 'columns', 'lintel': 'lintels', 'sill': 'sills', 'parapet': 'parapets', 'glass': 'glass',
          'mullion': 'mullions', 'railing': 'railings', 'single': 'single-line pieces', 'step': 'stair steps', 'slab': 'slabs'}


def ascii_name(s):                         # Max object names and text: plain ASCII
    s = s.replace('²', '2').replace('·', '-')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return ' '.join(s.replace('"', "'").replace('\\', '/').split())


def signed(loop): return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(loop, loop[1:] + loop[:1])) / 2
def arr(v): return '#(' + ','.join(v) + ')'
def num(v): return f'({v:.4f})' if v < 0 else f'{v:.4f}'        # negative numbers in brackets: never read as a minus
def pt(p): return f'[{num(p[0])},{num(p[1])}]'
def words(v): return ', '.join(v[:-1]) + ' and ' + v[-1] if len(v) > 1 else ''.join(v)


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
    for i in range(len(holes)):            # ... nor two holes that touch each other
        for j in range(i + 1, len(holes)):
            if LinearRing(holes[i]).distance(LinearRing(holes[j])) < 5e-4: problems.append(f'{name}: two holes touch')
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

# What "Update levels and heights" does to this model's parts, in words for the header: the kinds whose parts follow the wall
# height, and the kinds that keep their own (a kind with both says so).
kinds_seen = list(dict.fromkeys(p['kind'] for p in M['parts'] if p['kind'] in KINDS))
follows = {k: {bool(p.get('follow')) for p in M['parts'] if p['kind'] == k} for k in kinds_seen}
follow_txt = words([PLURAL[k] + (' (those marked to)' if len(follows[k]) > 1 else '') for k in kinds_seen if True in follows[k]]) or 'no part'
keep_txt = words(['the ' + PLURAL[k] for k in kinds_seen if follows[k] == {False}]) or 'nothing else'
# The scale, in the header and the datum's Source (the owner's answer of 2 Nov 2026): the one real dimension is the main stair's
# width, the flight from the lowest floor up to the next, built that wide between its side walls; so the width of its steps
# (each step's longer side) says it. The pictures were scaled per axis when the picture is drawn wider than tall.
flight = [p for p in M['parts'] if p['kind'] == 'step' and p['floor'] == FLOORS[0]['key']]
stair_w = max(max(max(x for x, _ in p['o']) - min(x for x, _ in p['o']), max(y for _, y in p['o']) - min(y for _, y in p['o'])) for p in flight) if flight else None
per_axis = [f['name'] for f in FLOORS if (M.get('pictureFrame') or {}).get(f['key']) and abs(M['pictureFrame'][f['key']]['pxPerMetreX'] - M['pictureFrame'][f['key']]['pxPerMetreY']) >= 0.005]
stair_txt = (f"the main stair's width, {stair_w:.2f} m between its side walls" if stair_w else 'no dimension')
axis_txt = (f"; {words(per_axis)}'s picture is drawn wider than tall (a scale per axis)" if per_axis else '')
# How far the scale can be trusted, in the header: the lift doors as drawn, at the scale the model uses (each is built 1.00 m).
drawn = [o['drawnWidth'] for o in M['openings'] if o.get('liftDoor') and o.get('drawnWidth')]
door_txt = (f'at that scale the {len(drawn)} lift doors measure {min(drawn):.2f} to {max(drawn):.2f} m as drawn '
            f'({sum(drawn) / len(drawn):.2f} m on average); they are built {max(o["width"] for o in M["openings"] if o.get("liftDoor")):.2f} m'
            if drawn else 'no lift door was measured')
scale_txt = (f"scaled from {stair_txt} (the owner's){', per axis where a picture is drawn wider than tall' if per_axis else ''}"
             if stair_w else 'scale not measured')

# Where each picture goes, from the model's pictureFrame (pixel x = originPx[0] + pxPerMetreX * X, y = originPx[1] - pxPerMetreY * Y,
# X Y = the drawing's own coordinates): a plane of the picture's size in metres along each axis, its centre given from the datum at 0,0.
pictures = []
for f in FLOORS:
    pf = (M.get('pictureFrame') or {}).get(f['key'])
    if not pf: continue
    (w, h), kx, ky, (px0, py0) = pf['size'], pf['pxPerMetreX'], pf['pxPerMetreY'], pf['originPx']
    rel = posixpath.normpath(posixpath.join('src', pf['file']))            # the file as seen from the script's folder
    cx, cy = (round((w / 2 - px0) / kx, 4) + 0.0, round((py0 - h / 2) / ky, 4) + 0.0)   # text for people: a plain minus (no -0.0000)
    pictures.append(f'    setUserProp origin "Picture_{f["key"]}" "{ascii_name(rel)} ({w} x {h} px at {kx:.4f} px per m along x and {ky:.4f} along y) '
                    f'is a plane {w / kx:.4f} m along x by {h / ky:.4f} m along y, its centre [{cx:.4f}, {cy:.4f}] m from '
                    f'this point, under {ascii_name(f["name"])}"')

header = r'''-- __PROJECT__ (TEST) / from "__SOURCE__" / built by the CAD-to-3D test pipeline, 2 Nov 2026
-- Same model as __PAGE__ (model data __SHA__). Floor levels __LEVELTXT__ m, wall heights __HEIGHTTXT__ m.
-- Read from two presentation pictures, not from CAD, and scaled from the one dimension the owner gave (2 Nov 2026):
-- __STAIRTXT____AXISTXT__.
-- Sizes are approximate: __DOORTXT__.
-- Placed at the drawing's own coordinates in metres (__FRAME__),
-- or centred on the origin if you untick that box in the script's window.
-- To lay a picture under its floor: the hidden point __PX___ORIGIN_DWG (layer __PX___Datums) gives each picture's size
-- and centre in metres (Object Properties > User Defined).
-- Every part stays LIVE (no Editable Poly): an editable spline outline + an Extrude modifier (output: Mesh) + Smooth.
--   * Change a height: the Extrude amount on that object, or "Update levels and heights" in this script's window.
--   * Change an outline: select the spline level under the modifiers and move vertices.
--   * Editable Mesh: tick "Collapse to Editable Mesh" before Build, or press "Collapse all now" later.
-- Each object's pivot is at the middle of its own outline, on its base. Layers per level and kind (__PX___F1_Walls ...).
-- "Update levels and heights" sets the tops of the __FOLLOWTXT__ to their level's wall height and keeps
-- __KEEPTXT__ at their own heights (only parts marked to follow the wall height change).
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
    setUserProp origin "Source" "__SOURCE__: two presentation pictures, no CAD, __SCALETXT__; model in metres, __FRAME__"
    setUserProp origin "Levels" ("floor levels " + (__PX___levels as string) + " m, wall heights " + (__PX___heights as string) + " m")
__PICTURES__
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
    checkbox dwg "At the drawing's own coordinates" checked:true tooltip:"Metres from the lift core's north-west corner, the frame the pictures were scaled in. Untick to centre the model on the origin"
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
             ('__PICTURES__\n', ''.join(p + '\n' for p in pictures)), ('__FOLLOWTXT__', follow_txt), ('__KEEPTXT__', keep_txt),
             ('__DOORTXT__', door_txt), ('__SCALETXT__', scale_txt), ('__STAIRTXT__', stair_txt), ('__AXISTXT__', axis_txt),
             ('__LEVELTXT__', ' / '.join(f"{f['level']:+.2f}" for f in FLOORS)),
             ('__HEIGHTTXT__', ' / '.join(f"{f['wallHeight']:.2f}" for f in FLOORS)),
             ('__LEVELS__', levels), ('__HEIGHTS__', heights), ('__NAMES__', names), ('__SHA__', SHA), ('__PAGE__', PAGE),
             ('__FRAME__', FRAME), ('__SOURCE__', ascii_name(source)), ('__PROJECT__', ascii_name(M['project']).upper()),
             ('__SHORT__', ascii_name(M.get('shortName', M['project']))),
             ('__OX__', f'{ox:.4f}'), ('__OY__', num(oy)), ('__PX__', PX)):
    script = script.replace(k, v)
out = Path(sys.argv[1])
out.write_text(script, encoding='utf-8')
print(FURN['summary'])
by_kind = {}
for (fl, kind), n in count.items(): by_kind[kind] = by_kind.get(kind, 0) + n
print('written', out, f'{len(script) // 1024} KB | model', SHA, '|', ', '.join(f'{k} {v}' for k, v in by_kind.items()),
      '| stair shapes', len(lines), '| room names', len(rooms), '| pictures', len(pictures))
print('objects Build announces:', len(calls) + len(lines) + len(rooms) + len(FURN['calls']),
      f'({len(calls)} parts, {len(lines)} stair shapes, {len(rooms)} room names, {len(FURN["calls"])} furniture boxes)')
# Brackets are counted as MAXScript reads them, outside strings and comments: an object name may hold half a bracket (a family
# name cut at 40 characters: '..._built-in bench, west leg of the L (9 cus'), which is text, not code.
code = re.sub(r'--[^\n]*', '', re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', script))
print('balanced ( ):', code.count('(') == code.count(')'), '| [ ]:', code.count('[') == code.count(']'),
      '| even quotes:', script.count('"') % 2 == 0, '| ascii only:', all(ord(c) < 128 for c in script),
      '| no placeholders left:', not re.search(r'__[A-Z]+(?:_[A-Z]+)*__', script))
print('brackets inside strings (text, not code):', script.count('(') - code.count('('), '(', script.count(')') - code.count(')'), ')')
