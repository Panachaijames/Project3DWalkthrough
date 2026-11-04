"""Write Presidential_Suite.ms: a 3ds Max script that builds the presidential suite test model.

Same model as the web viewer (pres3d_merged.json from pres_build.py), placed at the DWG's own coordinates in metres:
- walls: ONE Editable Poly per merged wall run (outline + inner loops -> Extrude -> Smooth 40 deg -> Editable Poly),
  each checked in Max: closed solid, height, position;
- the terrace parapet the same way (1.10 m);
- the floor slab: an editable spline + Extrude modifier (0.25 m under the floor);
- room names from the drawing as text shapes on their own layer.
A wall that fails a check does not stop the build: it goes on layer PS_Check_Failed and is listed at the end.
Usage: python generate_maxscript_pres.py <out.ms>
"""
import json, math, sys, unicodedata
from pathlib import Path
from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent
M = json.loads((HERE / 'pres3d_merged.json').read_text(encoding='utf-8'))
ox, oy = M['offset']                       # the viewer centred the model; add this back for the DWG's own coordinates
FLOOR_TO_FLOOR = M['tops']['suite'] - M['levels']['suite']

def ascii_name(s):                         # Max object names and text: plain ASCII ("Tổ hợp Khách Ăn" -> "To hop Khach An")
    s = s.replace('Đ', 'D').replace('đ', 'd')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return ' '.join(s.split())
def cross(a, b): return a[0] * b[1] - a[1] * b[0]
def signed(loop): return sum(cross(a, b) for a, b in zip(loop, loop[1:] + loop[:1])) / 2
def arr(v): return '#(' + ','.join(v) + ')'
def pt(p): return f'[{p[0]:.4f},{p[1]:.4f}]'

problems, calls = [], []
def solid_call(fn, name, r):
    outer = [(x + ox, y + oy) for x, y in r['o']]
    holes = [[(x + ox, y + oy) for x, y in h] for h in r['h']]
    poly = Polygon(outer, holes)
    if not poly.is_valid: problems.append(f'{name}: invalid polygon')
    for loop in [outer] + holes:
        if len(loop) < 3: problems.append(f'{name}: loop with fewer than 3 points')
        for a, b in zip(loop, loop[1:] + loop[:1]):
            if math.dist(a, b) < 1e-4: problems.append(f'{name}: repeated point')
    loops = []
    for j, loop in enumerate([outer] + holes):          # outer counter-clockwise, holes clockwise
        if (signed(loop) > 0) != (j == 0): loop = loop[::-1]
        loops.append(arr([pt(q) for q in loop]))
    mn = (min(x for x, _ in outer), min(y for _, y in outer)); mx = (max(x for x, _ in outer), max(y for _, y in outer))
    return f'    {fn} "{name}" {arr(loops)} {pt(mn)} {pt(mx)}'

for i, r in enumerate(M['solids'].get('suite:wall', [])): calls.append(solid_call('PS_wall', f'PS_Wall_{i:03}', r))
for i, r in enumerate(M['solids'].get('suite:parapet', [])): calls.append(solid_call('PS_parapet', f'PS_Parapet_{i:03}', r))
slabs = []
for i, r in enumerate(M['plates']['suite']):
    loops = []
    for j, loop in enumerate([[(x + ox, y + oy) for x, y in r['o']]] + [[(x + ox, y + oy) for x, y in h] for h in r['h']]):
        if (signed(loop) > 0) != (j == 0): loop = loop[::-1]
        loops.append(arr([pt(q) for q in loop]))
    slabs.append(f'    PS_slab "PS_Floor_Slab_{i}" {arr(loops)}')
rooms = [f'    PS_room "{ascii_name(rm["name"])}" {pt((rm["x"] + ox, rm["y"] + oy))}' for rm in M['rooms']]

header = r'''-- PRESIDENTIAL SUITE (TEST) / from "layout presidential xx.dwg" / built by the CAD-to-3D test pipeline, 19 Oct 2026
-- Walls are found by pairing parallel lines on layer 0 (this office draws walls with the furniture); five furniture
-- areas were set aside by hand. Floor to floor 3.00 m, as given for the project.
-- Same model as presidential_3d_preview.html, at the DWG's own coordinates in metres (import the DWG in metres to compare).
-- Walls: ONE Editable Poly per merged wall run, auto-smoothed at 40 deg, each checked: closed solid, height, position.
-- Parapet under the balcony railing: same, 1.10 m. Floor slab: editable spline + Extrude. Room names: text shapes.
-- A wall that fails a check is kept on layer PS_Check_Failed and listed at the end; the build goes on.
-- Nothing in an existing scene is changed: run it in a NEW EMPTY scene.
global PS_UI
global PS_nodes = #()
global PS_failed = #()
global PS_scale = 1.0
global PS_level = 0.0
global PS_height = 3.0
global PS_parapetH = 1.1
global PS_matWall
global PS_matParapet
global PS_matSlab

fn PS_layer n =
(
    local ly = LayerManager.getLayerFromName n
    if ly == undefined do ly = LayerManager.newLayerFromName n
    ly
)
fn PS_point p z = [p.x * PS_scale, p.y * PS_scale, z]
fn PS_shape nm loops z =
(
    local o = splineShape name:nm
    for j = 1 to loops.count do
    (
        addNewSpline o
        for p in loops[j] do addKnot o j #corner #line (PS_point p z)
        close o j
    )
    updateShape o
    o
)
fn PS_extruded nm loops z ht mn mx mt ly =
(
    local o = PS_shape nm loops z
    addModifier o (Extrude amount:ht segs:1 capStart:true capEnd:true)
    addModifier o (Smooth autoSmooth:true threshold:40.0)
    convertTo o Editable_Poly
    o.material = mt
    o.wirecolor = mt.diffuse
    local why = ""
    local tol = 0.002
    if (polyop.getNumFaces o) < 3 then why = "no faces"
    else if (polyop.getOpenEdges o).numberSet != 0 then why = "open edges (not a closed solid)"
    else if abs(o.min.z - z) > tol or abs(o.max.z - (z + ht)) > tol then why = "height"
    else if abs(o.min.x - mn.x * PS_scale) > tol or abs(o.min.y - mn.y * PS_scale) > tol or abs(o.max.x - mx.x * PS_scale) > tol or abs(o.max.y - mx.y * PS_scale) > tol then why = "position"
    if why == "" then
    (
        (PS_layer ly).addNode o
        setUserProp o "Validated" "merged wall run / closed solid / height and position checked"
    )
    else
    (
        (PS_layer "PS_Check_Failed").addNode o
        setUserProp o "Check failed" why
        append PS_failed (nm + ": " + why)
    )
    append PS_nodes o
    o
)
fn PS_wall nm loops mn mx = PS_extruded nm loops PS_level PS_height mn mx PS_matWall "PS_Walls"
fn PS_parapet nm loops mn mx = PS_extruded nm loops PS_level PS_parapetH mn mx PS_matParapet "PS_Parapet"
fn PS_slab nm loops =
(
    local o = PS_shape nm loops (PS_level - 0.25)
    addModifier o (Extrude amount:0.25 capStart:true capEnd:true)
    o.material = PS_matSlab
    o.wirecolor = PS_matSlab.diffuse
    (PS_layer "PS_Slab").addNode o
    setUserProp o "Edit" "Edit the base spline; the Extrude amount is the slab thickness."
    append PS_nodes o
    o
)
fn PS_room nm p =
(
    local t = text text:nm size:0.35 pos:(PS_point p (PS_level + 0.02))
    t.name = "PS_Room_" + nm
    t.wirecolor = color 30 60 110
    (PS_layer "PS_RoomNames").addNode t
    append PS_nodes t
    t
)
fn PS_build =
(
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
    PS_matWall = standardMaterial name:"PS Wall" diffuse:(color 227 221 211)
    PS_matParapet = standardMaterial name:"PS Parapet" diffuse:(color 217 185 138)
    PS_matSlab = standardMaterial name:"PS Floor Slab" diffuse:(color 212 216 210)
'''

footer = r'''
    local origin = point name:"PS_ORIGIN_DWG" size:1.0 pos:[0, 0, 0]
    (PS_layer "PS_Datums").addNode origin
    setUserProp origin "Source" "layout presidential xx.dwg, converted with LibreDWG; drawing units mm, model in metres at the DWG's own XY"
    setUserProp origin "Heights" ("floor " + (PS_level as string) + " m, walls " + (PS_height as string) + " m, parapet " + (PS_parapetH as string) + " m")
    viewport.setType #view_iso_user
    max tool zoomextents all
    redrawViews()
    format "PS BUILD COMPLETE: % objects, % failed checks\n" PS_nodes.count PS_failed.count
    for f in PS_failed do format "  check failed: %\n" f
    true
)
try (destroyDialog PS_UI) catch ()
rollout PS_UI "Presidential suite (test)" width:330
(
    label info "Open a new empty scene before Build." align:#left
    spinner sf "Scale factor:" range:[0.01, 100, 1.0] type:#float scale:0.01 fieldwidth:70
    spinner lv "Floor level (m):" range:[-50, 500, 0.0] type:#float fieldwidth:70
    spinner ht "Wall height (m):" range:[0.5, 15, 3.0] type:#float fieldwidth:70
    spinner ph "Parapet height (m):" range:[0.2, 3, 1.1] type:#float fieldwidth:70
    button build "BUILD THE SUITE" width:300 height:32
    label note "Walls: one Editable Poly per run / Slab: spline + Extrude" align:#left
    on build pressed do
    (
        PS_scale = sf.value
        PS_level = lv.value
        PS_height = ht.value
        PS_parapetH = ph.value
        try
        (
            if PS_build() do
            (
                if PS_failed.count == 0 then messageBox ("Built " + (PS_nodes.count as string) + " objects. Every wall passed the closed-solid, height and position checks. Save As to keep your .max file.") title:"Presidential suite"
                else messageBox ((PS_failed.count as string) + " wall(s) failed a check and are on layer PS_Check_Failed (listed in the MAXScript Listener). Everything else was built.") title:"Presidential suite"
            )
        )
        catch (messageBox (getCurrentException()) title:"Build stopped")
    )
)
createDialog PS_UI
'''

if problems:
    print('DATA PROBLEMS:'); print('\n'.join(problems[:30])); sys.exit(1)
script = header + '\n'.join(slabs + calls + rooms) + footer
out = Path(sys.argv[1])
out.write_text(script, encoding='utf-8')
print('written', out, f'{len(script) // 1024} KB | walls', len(M['solids'].get('suite:wall', [])), '| parapet', len(M['solids'].get('suite:parapet', [])),
      '| slabs', len(slabs), '| room names', len(rooms))
print('balanced ( ):', script.count('(') == script.count(')'), '| [ ]:', script.count('[') == script.count(']'), '| even quotes:', script.count('"') % 2 == 0,
      '| ascii only:', all(ord(c) < 128 for c in script))
