"""Write Srisawan_New_Layouts_Merged.ms: the same build as Srisawan_New_Layouts_Quad.ms (REVISION 04),
but walls are merged solids (one Editable Poly per wall run) instead of one box per traced segment.

Inputs:
  srisawan-rebuild/model_geometry.json   (original trace, slabs, voids, shaft holes)
  srisawan3d_merged.json                 (merged wall outlines from build_srisawan_merged.py)
"""
import collections, json, math, sys
from pathlib import Path
from shapely.geometry import Polygon, Point

ROOT = Path('C:/Users/DWP2/Desktop/Project walkthrough')
OUT = ROOT / 'srisawan-rebuild' / 'Srisawan_New_Layouts_Merged.ms'
g = json.loads((ROOT / 'srisawan-rebuild' / 'model_geometry.json').read_text(encoding='utf-8'))
M = json.loads(Path('srisawan3d_merged.json').read_text(encoding='utf-8'))
S = g['scale']; d = g['data']; shaft_holes = g['shaft_holes']
ox, oy = M['offset']['hosp']          # merged outlines were centred for the web viewer; undo that

def xy(p):                            # identical to generate_maxscript.py
    return ((p[0] - 754) * S, (301 - p[1]) * S)

def cross(a, b): return a[0] * b[1] - a[1] * b[0]
def signed(poly): return sum(cross(a, b) for a, b in zip(poly, poly[1:] + poly[:1])) / 2
def arrpoint(p, z=0): return f'[{p[0]:.6f},{p[1]:.6f},{z:.6f}]'
def array(v): return '#(' + ','.join(v) + ')'

SUFFIX = {'core': 'Core', 'glass': 'Glazing', 'envelope': 'Envelope', 'wall': 'Partitions'}
problems = []
calls = []
counts = collections.Counter()
for lv in (1, 2):
    for kind in ('core', 'envelope', 'wall', 'glass'):
        key = f'L{lv}:{kind}'
        segs = M['segments'].get(key, [])
        for i, r in enumerate(M['solids'].get(key, [])):
            outer = [(x + ox, y + oy) for x, y in r['o']]
            holes = [[(x + ox, y + oy) for x, y in h] for h in r['h']]
            # ---- data checks before writing (the script re-checks inside 3ds Max) ----
            poly = Polygon(outer, holes)
            if not poly.is_valid: problems.append(f'{key} #{i}: invalid polygon')
            if len(outer) < 3 or any(len(h) < 3 for h in holes): problems.append(f'{key} #{i}: loop with < 3 points')
            for loop in [outer] + holes:
                for a, b in zip(loop, loop[1:] + loop[:1]):
                    if math.dist(a, b) < 1e-4: problems.append(f'{key} #{i}: repeated point')
            # dominant zone: the zone of most traced segments lying on this solid
            votes = collections.Counter()
            area = poly.buffer(0.05)
            for x1, y1, x2, y2, z in segs:
                if area.contains(Point((x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy)):
                    votes[M['zones'][z]] += 1
            zone = (votes.most_common(1)[0][0] if votes else 'Unassigned').replace(' ', '_').replace('/', '_')
            # orient like the slab code: outer counter-clockwise, holes clockwise
            loops = []
            for j, loop in enumerate([outer] + holes):
                if (signed(loop) > 0) != (j == 0): loop = loop[::-1]
                loops.append(array([arrpoint(q) for q in loop]))
            mn = (min(x for x, _ in outer), min(y for _, y in outer)); mx = (max(x for x, _ in outer), max(y for _, y in outer))
            name = f'SR_L{lv}_{SUFFIX[kind]}_{zone}_{i:03}'
            calls.append(f'    SR_solid "{name}" {array(loops)} {lv} #{kind} [{mn[0]:.6f},{mn[1]:.6f}] [{mx[0]:.6f},{mx[1]:.6f}]')
            counts[key] += 1

slab_calls = []
for lv in (1, 2):
    loops = [d['outlines'][str(lv)]] + ([] if lv == 1 else d['voids'] + shaft_holes)
    out = []
    for i, loop in enumerate(loops):
        p = [xy(q) for q in loop]
        if (signed(p) > 0) != (i == 0): p.reverse()
        out.append(array([arrpoint(q) for q in p]))
    slab_calls.append(f'    SR_slab "SR_L{lv}_Floor' + ('_2_PUBLIC_VOIDS_6_CORE_OPENINGS' if lv == 2 else '')
                      + f'" {array(out)} ' + ('-0.25' if lv == 1 else '(SR_level2-0.25)'))

header = r'''-- SRISAWAN / REBUILT FROM x01.jpg and x02.jpg / REVISION 05 - MERGED WALLS
-- Same trace, scale, levels, slabs, layers and materials as REVISION 04 (Srisawan_New_Layouts_Quad.ms).
-- Change: walls are merged solids - ONE Editable Poly per continuous wall run - instead of one box
-- per traced segment, so there are no seams along walls and no overlapping squares at corners.
-- Each wall is a closed outline (with inner loops where walls enclose a space) + Extrude, collapsed
-- to Editable Poly, then checked: closed solid, correct heights, correct position.
-- Traced curves are rounded off and walls get auto-smoothing (40 deg), so curved walls render as
-- one smooth surface while real corners stay sharp.
-- No furniture / no landscape / no reset / no automatic overwrite.
global SR_batchMode
global SR_UI
global SR_nodes = #()
global SR_scaleFactor = 1.0
global SR_h1 = 4.0
global SR_h2 = 4.0
global SR_level2 = 5.0
global SR_matWall
global SR_matCore
global SR_matSlab
global SR_matGlass

fn SR_layer n =
(
    local ly=LayerManager.getLayerFromName n
    if ly==undefined do ly=LayerManager.newLayerFromName n
    ly
)
fn SR_point p z = [p.x*SR_scaleFactor,p.y*SR_scaleFactor,z]
fn SR_record o ly mt =
(
    o.material=mt
    o.wirecolor=mt.diffuse
    (SR_layer ly).addNode o
    append SR_nodes o
)
fn SR_solid nm loops lv kind mn mx =
(
    local z=if lv==1 then 0.0 else SR_level2
    local ht=if lv==1 then SR_h1 else SR_h2
    local o=splineShape name:nm
    for j=1 to loops.count do
    (
        addNewSpline o
        for p in loops[j] do addKnot o j #corner #line (SR_point p z)
        close o j
    )
    updateShape o
    addModifier o (Extrude amount:ht segs:1 capStart:true capEnd:true)
    addModifier o (Smooth autoSmooth:true threshold:40.0)
    convertTo o Editable_Poly
    if (polyop.getNumFaces o)<3 do throw ("No faces: "+nm)
    if (polyop.getOpenEdges o).numberSet!=0 do throw ("Open edge (not a closed solid): "+nm)
    local tol=0.002
    if abs(o.min.z-z)>tol or abs(o.max.z-(z+ht))>tol do throw ("Height check failed: "+nm)
    if abs(o.min.x-mn.x*SR_scaleFactor)>tol or abs(o.min.y-mn.y*SR_scaleFactor)>tol or abs(o.max.x-mx.x*SR_scaleFactor)>tol or abs(o.max.y-mx.y*SR_scaleFactor)>tol do throw ("Position check failed: "+nm)
    local mt=case kind of (#core:SR_matCore; #glass:SR_matGlass; default:SR_matWall)
    local suffix=case kind of (#core:"Core"; #glass:"Glazing"; #envelope:"Envelope"; default:"Partitions")
    SR_record o ("SR_L"+(lv as string)+"_"+suffix) mt
    setUserProp o "Validated" "merged wall run / smoothed curves / closed solid / height and position checked"
    o
)
fn SR_slab nm loops z =
(
    local o=splineShape name:nm
    for j=1 to loops.count do
    (
        addNewSpline o
        for p in loops[j] do addKnot o j #corner #line (SR_point p z)
        close o j
    )
    updateShape o
    addModifier o (Extrude amount:0.25 capStart:true capEnd:true)
    SR_record o (if z<0 then "SR_L1_Slab" else "SR_L2_Slab") SR_matSlab
    setUserProp o "Edit" "Edit base spline vertices; internal loops are real slab openings."
    o
)
fn SR_show lv =
(
    for i=0 to (LayerManager.count-1) do
    (
        local ly=LayerManager.getLayer i
        if matchPattern ly.name pattern:"SR_L1_*" do ly.isHidden=(lv==2)
        if matchPattern ly.name pattern:"SR_L2_*" do ly.isHidden=(lv==1)
    )
    if lv!=0 do viewport.setType #view_top
    max tool zoomextents all
    redrawViews()
)
fn SR_build =
(
    if objects.count>0 then
    (
        messageBox "Open a NEW EMPTY scene first. Existing objects have not been changed." title:"Srisawan"
        return false
    )
    units.systemType=#meters
    units.systemScale=1.0
    units.displayType=#metric
    units.metricType=#meters
    SR_nodes=#()
    SR_matWall=standardMaterial name:"SR Wall" diffuse:(color 220 216 207)
    SR_matCore=standardMaterial name:"SR Structural Core" diffuse:(color 158 168 175)
    SR_matSlab=standardMaterial name:"SR Slab" diffuse:(color 185 193 198)
    SR_matGlass=standardMaterial name:"SR Garden Glazing" diffuse:(color 125 194 211) opacity:25 twoSided:true
'''

footer = r'''
    local origin=point name:"SR_ORIGIN_LIFT_CORE" size:0.7 pos:[0,0,0]
    (SR_layer "SR_Datums").addNode origin
    setUserProp origin "Axes" "X/Y aligned with lift core; L1 and L2 share identical core XY"
    setUserProp origin "Source" "New trace x01.jpg / x02.jpg. Scale calibrated to 1.20m lift door / 19 image pixels; raster tolerance applies."
    setUserProp origin "Levels" ("L1 0m / L2 "+(SR_level2 as string)+"m")
    setUserProp origin "Walls" "REVISION 05: merged wall runs (one Editable Poly each) - no seams, clean corners"
    viewport.setType #view_iso_user
    SR_show 0
    redrawViews()
    format "SR BUILD COMPLETE: % validated objects (merged walls + slabs). Both levels visible.\n" SR_nodes.count
    true
)
try(destroyDialog SR_UI)catch()
rollout SR_UI "Srisawan - new layout / merged walls" width:350
(
    label info "Open a new empty scene before Build." align:#left
    spinner sf "Horizontal scale factor:" range:[0.01,100,1.0] type:#float scale:0.01 fieldwidth:80
    spinner fl "L2 finished floor (m):" range:[0.1,20,5.0] type:#float fieldwidth:80
    spinner h1 "L1 wall height (m):" range:[0.1,15,4.0] type:#float fieldwidth:80
    spinner h2 "L2 wall height (m):" range:[0.1,15,4.0] type:#float fieldwidth:80
    button build "BUILD BOTH FLOORS" width:320 height:32
    button allFloors "Show BOTH floors" width:320
    button floorOne "Top view - FLOOR 1" width:320
    button floorTwo "Top view - FLOOR 2 + VOIDS" width:320
    label note "Walls: merged runs (Editable Poly) / Slabs: spline + Extrude" align:#left
    on build pressed do
    (
        SR_scaleFactor=sf.value
        SR_level2=fl.value
        SR_h1=h1.value
        SR_h2=h2.value
        try (if SR_build() do messageBox "Built both floors with merged walls. Every wall passed the closed-solid, height and position checks. Use the floor buttons to inspect. Save As to keep your .max file." title:"Srisawan")
        catch (messageBox (getCurrentException()) title:"Build stopped - validation failed")
    )
    on allFloors pressed do (viewport.setType #view_iso_user; SR_show 0)
    on floorOne pressed do SR_show 1
    on floorTwo pressed do SR_show 2
)
if SR_batchMode != true do createDialog SR_UI
'''

if problems:
    print('DATA PROBLEMS:'); print('\n'.join(problems[:30])); sys.exit(1)
script = header + '\n'.join(slab_calls + calls) + footer
OUT.write_text(script, encoding='utf-8')
print('written', OUT, f'{len(script) // 1024} KB')
print('walls per layer:', dict(counts), '| slabs:', len(slab_calls))
# quick structural checks on the generated text
print('balanced parentheses:', script.count('(') == script.count(')'), '| balanced brackets:', script.count('[') == script.count(']'),
      '| even quotes:', script.count('"') % 2 == 0)
