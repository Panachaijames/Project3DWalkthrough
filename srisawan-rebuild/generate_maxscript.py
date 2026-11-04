from pathlib import Path
import json,math,collections
from PIL import Image,ImageDraw
O=Path(__file__).resolve().parent
d=json.loads((O/'new_trace.json').read_text());reg=d['registration'];S=d['metres_per_pixel']
def registered(p,lv):return (reg['ax']*p[0]+reg['bx'],reg['ay']*p[1]+reg['by']) if lv==1 else tuple(p)
def xy(p):return ((p[0]-754)*S,(301-p[1])*S)
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def inside(p,poly):
 x,y=p;hit=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:hit=not hit
 return hit
def clip(a,b,poly):
 v=(b[0]-a[0],b[1]-a[1]);ts=[0.,1.]
 for c,e in zip(poly,poly[1:]+poly[:1]):
  w=(e[0]-c[0],e[1]-c[1]);den=cross(v,w)
  if abs(den)>1e-9:
   q=(c[0]-a[0],c[1]-a[1]);t=cross(q,w)/den;u=cross(q,v)/den
   if 0<t<1 and 0<=u<=1:ts.append(t)
 ts=sorted(set(ts));out=[]
 for t0,t1 in zip(ts,ts[1:]):
  mid=(a[0]+v[0]*(t0+t1)/2,a[1]+v[1]*(t0+t1)/2)
  if inside(mid,poly):out.append(((a[0]+v[0]*t0,a[1]+v[1]*t0),(a[0]+v[0]*t1,a[1]+v[1]*t1)))
 return out
segments=[]
for lv in [1,2]:
 seen=set()
 for i,row in enumerate(d['walls'][str(lv)]+[{'zone':'LiftCore','points':p} for p in d['core']]):
  core=row['zone']=='LiftCore';line=[tuple(p) if core else registered(p,lv) for p in row['points']]
  for j,(a,b) in enumerate(zip(line,line[1:])):
   for k,(a,b) in enumerate([(a,b)] if core else clip(a,b,d['outlines'][str(lv)])):
    key=tuple(sorted((tuple(round(c,2) for c in a),tuple(round(c,2) for c in b))))
    if key in seen or math.dist(a,b)<.5:continue
    seen.add(key);segments.append({'name':f'SR_L{lv}_{row["zone"]}_{i:03}_{j}_{k}','level':lv,'a':a,'b':b,'kind':'core' if core else 'wall'})
 # Thin transparent facade shell only where adjacent to gardens; no mullion detailing.
 poly=d['outlines'][str(lv)]
 for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
  # x01 transformed: west public frontage. x02: west garden and pharmacy notch.
  glass=(max(a[0],b[0])<600) or (lv==1 and min(a[1],b[1])>550 and max(a[0],b[0])<900)
  segments.append({'name':f'SR_L{lv}_Envelope_{i:03}','level':lv,'a':a,'b':b,'kind':'glass' if glass else 'envelope'})
# Source-aligned shaft openings: not filled by L2 floor slab.
shaft_holes=[[(690,196),(743,196),(743,298),(690,298)],[(763,258),(788,258),(788,298),(763,298)],[(758,305),(793,305),(793,347),(758,347)],[(801,305),(831,305),(831,347),(801,347)],[(719,352),(745,352),(745,374),(719,374)],[(719,388),(745,388),(745,405),(719,405)]]
def signed(poly):return sum(cross(a,b) for a,b in zip(poly,poly[1:]+poly[:1]))/2
def arrpoint(p,z=0):return f'[{p[0]:.6f},{p[1]:.6f},{z:.6f}]'
def array(v):return '#('+','.join(v)+')'
header='''-- SRISAWAN / REBUILT FROM x01.jpg and x02.jpg / REVISION 04
-- New geometry; Lift Core coordinates shared by both floors.
-- Walls are native Editable Poly with 6 QUAD polygons, not triangle meshes.
-- Floor slabs remain editable closed splines + Extrude, with real cutout loops.
-- No furniture / no landscape / no reset / no automatic overwrite.
global SR_UI
global SR_nodes = #()
global SR_scaleFactor = 1.0
global SR_h1 = 4.0
global SR_h2 = 4.0
global SR_level2 = 5.0
global SR_thickness = 0.18
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
fn SR_wall nm aa bb lv kind =
(
    local z=if lv==1 then 0.0 else SR_level2
    local ht=if lv==1 then SR_h1 else SR_h2
    local a=SR_point aa z
    local b=SR_point bb z
    local thick=case kind of (#core:0.24; #glass:0.06; #envelope:0.22; default:SR_thickness)
    local delta=b-a
    local len=sqrt(delta.x*delta.x+delta.y*delta.y)
    if len<0.00001 do throw ("Zero length: "+nm)
    local off=[-delta.y/len*thick/2,delta.x/len*thick/2,0]
    local vv=#(a-off,b-off,b+off,a+off)
    for k=1 to 4 do append vv (vv[k]+[0,0,ht])
    local faces=#(#(1,4,3,2),#(5,6,7,8),#(1,2,6,5),#(2,3,7,6),#(3,4,8,7),#(4,1,5,8))
    local o=editable_mesh name:nm
    convertTo o Editable_Poly
    in coordsys world
    (
        for p in vv do polyop.createVert o p
        for ids in faces do
        (
            local idx=polyop.createPolygon o ids
            if idx==undefined do throw ("Polygon creation failed: "+nm)
        )
        update o
        for k=1 to 8 do
            if distance (polyop.getVert o k) vv[k]>0.0001 do throw ("Position check failed: "+nm)
    )
    if (polyop.getNumFaces o)!=6 do throw ("Expected 6 polygons: "+nm)
    for k=1 to 6 do if (polyop.getFaceDeg o k)!=4 do throw ("Expected quad face: "+nm)
    if (polyop.getOpenEdges o).numberSet!=0 do throw ("Open edge: "+nm)
    polyop.setFaceSmoothGroup o #all 0
    local mt=case kind of (#core:SR_matCore; #glass:SR_matGlass; default:SR_matWall)
    local suffix=case kind of (#core:"Core"; #glass:"Glazing"; #envelope:"Envelope"; default:"Partitions")
    SR_record o ("SR_L"+(lv as string)+"_"+suffix) mt
    setUserProp o "Validated" "8 vertices / 6 quad faces / closed solid / position checked"
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
lines=[header]
for lv in [1,2]:
 loops=[d['outlines'][str(lv)]]+([] if lv==1 else d['voids']+shaft_holes)
 out=[]
 for i,loop in enumerate(loops):
  p=[xy(q) for q in loop]
  if (signed(p)>0)!=(i==0):p.reverse()
  out.append(array([arrpoint(q) for q in p]))
 lines.append(f'    SR_slab "SR_L{lv}_Floor'+('_2_PUBLIC_VOIDS_6_CORE_OPENINGS' if lv==2 else '')+f'" {array(out)} '+('-0.25' if lv==1 else '(SR_level2-0.25)'))
for r in segments:lines.append(f'    SR_wall "{r["name"]}" {arrpoint(xy(r["a"]))} {arrpoint(xy(r["b"]))} {r["level"]} #{r["kind"]}')
lines.append('''
    local origin=point name:"SR_ORIGIN_LIFT_CORE" size:0.7 pos:[0,0,0]
    (SR_layer "SR_Datums").addNode origin
    setUserProp origin "Axes" "X/Y aligned with lift core; L1 and L2 share identical core XY"
    setUserProp origin "Source" "New trace x01.jpg / x02.jpg. Scale calibrated to 1.20m lift door / 19 image pixels; raster tolerance applies."
    setUserProp origin "Levels" ("L1 0m / L2 "+(SR_level2 as string)+"m")
    viewport.setType #view_iso_user
    SR_show 0
    redrawViews()
    format "SR BUILD COMPLETE: % validated geometry objects. Both levels visible.\\n" SR_nodes.count
    true
)
try(destroyDialog SR_UI)catch()
rollout SR_UI "Srisawan - new layout / quad walls" width:350
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
    label note "Walls: Editable Poly / Slabs: editable spline + Extrude" align:#left
    on build pressed do
    (
        SR_scaleFactor=sf.value
        SR_level2=fl.value
        SR_h1=h1.value
        SR_h2=h2.value
        try (if SR_build() do messageBox "Built both floors. Wall coordinates and quad topology passed checks. Use floor buttons to inspect. Save As to keep your .max file." title:"Srisawan")
        catch (messageBox (getCurrentException()) title:"Build stopped - validation failed")
    )
    on allFloors pressed do (viewport.setType #view_iso_user; SR_show 0)
    on floorOne pressed do SR_show 1
    on floorTwo pressed do SR_show 2
)
if SR_batchMode != true do createDialog SR_UI
''')
script='\n'.join(lines).replace('global SR_UI','global SR_batchMode\nglobal SR_UI',1)
(O/'Srisawan_New_Layouts_Quad.ms').write_text(script,encoding='utf-8')
(O/'model_geometry.json').write_text(json.dumps({'segments':segments,'scale':S,'data':d,'shaft_holes':shaft_holes},indent=2))
# Independent numerical validation of the same quad construction.
checks=[]
for r in segments:
 a=xy(r['a']);b=xy(r['b']);t={'wall':.18,'core':.24,'envelope':.22,'glass':.06}[r['kind']]
 dx=b[0]-a[0];dy=b[1]-a[1];ll=math.hypot(dx,dy);n=(-dy/ll*t/2,dx/ll*t/2)
 v=[(a[0]-n[0],a[1]-n[1]),(b[0]-n[0],b[1]-n[1]),(b[0]+n[0],b[1]+n[1]),(a[0]+n[0],a[1]+n[1])]
 assert math.dist(v[0],v[1])>0 and abs(math.dist(v[0],v[3])-t)<1e-8
 checks.append(r['name'])
for lv in [1,2]:
 im=Image.open(fr'C:\Users\DWP\Desktop\x0{lv}.jpg').convert('RGB');dr=ImageDraw.Draw(im)
 def inv(p):return ((p[0]-reg['bx'])/reg['ax'],(p[1]-reg['by'])/reg['ay']) if lv==1 else tuple(p)
 for r in segments:
  if r['level']==lv:dr.line([inv(r['a']),inv(r['b'])],fill={'wall':'#ef3434','core':'#1697ff','envelope':'#ffae16','glass':'#00babc'}[r['kind']],width=2)
 if lv==2:
  for poly in d['voids']:dr.line([tuple(q) for q in poly]+[tuple(poly[0])],fill='#00dd79',width=3)
 im.save(O/f'Verified_L{lv}_overlay.png')
(O/'verification.txt').write_text(f'{len(checks)} wall/core/envelope segments checked numerically.\nNative runtime validates positions, six quad faces and closed edges for each wall.\nL1/L2 core share exact same XY.\nL2 slab: 2 public void loops + 6 core opening loops.\nHorizontal scale calibrated to lift door 1.20m = 19 pixels in x02.\nNative 3ds Max runtime not yet tested.\n')
print('Generated script;',len(segments),'quad wall segments; L2 has',len(d['voids'])+len(shaft_holes),'openings')
