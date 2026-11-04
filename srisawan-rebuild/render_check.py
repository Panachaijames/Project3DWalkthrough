from pathlib import Path
import json,math,collections
import numpy as np
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent
g=json.loads((O/'model_geometry.json').read_text());D=g['data'];S=g['scale']
def xy(p):return ((p[0]-754)*S,(301-p[1])*S)
def signed(p):return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1]))/2
def prism(p,z,h):
 if signed(p)<0:p=p[::-1]
 n=len(p);v=np.array([(x,y,z) for x,y in p]+[(x,y,z+h) for x,y in p],float)
 fs=[list(range(n-1,-1,-1)),list(range(n,2*n))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
 return v,fs
colors={'wall':(224,220,209),'core':(135,155,169),'envelope':(200,205,204),'glass':(106,177,194),'slab':(180,192,200)}
models=[]
for row in g['segments']:
 a=xy(row['a']);b=xy(row['b']);dx=b[0]-a[0];dy=b[1]-a[1];l=math.hypot(dx,dy);t={'wall':.18,'core':.24,'envelope':.22,'glass':.06}[row['kind']];nx=-dy/l*t/2;ny=dx/l*t/2
 p=[(a[0]-nx,a[1]-ny),(b[0]-nx,b[1]-ny),(b[0]+nx,b[1]+ny),(a[0]+nx,a[1]+ny)]
 v,f=prism(p,0 if row['level']==1 else 5,4)
 # Independent six-quad manifold check.
 edges=collections.Counter(tuple(sorted((face[i],face[(i+1)%len(face)]))) for face in f for i in range(len(face)))
 assert len(f)==6 and all(len(face)==4 for face in f) and all(n==2 for n in edges.values())
 models.append((row['level'],row['kind'],v,f))
def intersections(poly,y):
 xs=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if min(a[1],b[1])<y<max(a[1],b[1]):xs.append(a[0]+(b[0]-a[0])*(y-a[1])/(b[1]-a[1]))
 return xs
for lv in [1,2]:
 loops=[D['outlines'][str(lv)]]+([] if lv==1 else D['voids']+g['shaft_holes'])
 ys=sorted(set(q[1] for p in loops for q in p))
 for y0,y1 in zip(ys,ys[1:]):
  ep=(y1-y0)*1e-7
  xx0=sorted(x for p in loops for x in intersections(p,y0+ep));xx1=sorted(x for p in loops for x in intersections(p,y1-ep))
  assert len(xx0)==len(xx1) and len(xx0)%2==0
  for j in range(0,len(xx0),2):
   p=[xy(q) for q in [(xx0[j],y0),(xx0[j+1],y0),(xx1[j+1],y1),(xx1[j],y1)]]
   v,f=prism(p,-.25 if lv==1 else 4.75,.25);models.append((lv,'slab',v,f))
def render(mode):
 # Orthographic software depth rendering of the exact numerical model, not a Max render.
 selected=[m for m in models if mode==0 or m[0]==mode]
 direction=np.array([.60,-.78,.70]);direction/=np.linalg.norm(direction)
 right=np.cross([0,0,1],direction);right/=np.linalg.norm(right);up=np.cross(direction,right)
 basis=np.stack([right,-up,direction])
 allp=np.concatenate([v@basis.T for _,_,v,_ in selected]);mn=allp[:,:2].min(0);mx=allp[:,:2].max(0)
 width=1600;height=1100;scale=min((width-120)/(mx[0]-mn[0]),(height-200)/(mx[1]-mn[1]))
 zbuf=np.full((height,width),-np.inf);rgb=np.empty((height,width,3),dtype=np.uint8);rgb[:]=(241,245,248)
 light=np.array([-.3,-.4,1]);light/=np.linalg.norm(light)
 for lv,kind,v,faces in selected:
  q=v@basis.T;q[:,:2]=(q[:,:2]-mn)*scale+np.array([60,130])
  for face in faces:
   for k in range(1,len(face)-1):
    ids=[face[0],face[k],face[k+1]];a,b,c=q[ids];n=np.cross(v[ids[1]]-v[ids[0]],v[ids[2]]-v[ids[0]])
    norm=np.linalg.norm(n)
    if norm<1e-10:continue
    n/=norm
    if np.dot(n,direction)<0:continue
    shade=.62+.38*max(0,np.dot(n,light));col=np.array(colors[kind])*shade
    x0=max(0,int(min(a[0],b[0],c[0])));x1=min(width-1,int(max(a[0],b[0],c[0]))+1)
    y0=max(0,int(min(a[1],b[1],c[1])));y1=min(height-1,int(max(a[1],b[1],c[1]))+1)
    if x1<x0 or y1<y0:continue
    xx,yy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
    den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(den)<1e-8:continue
    u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
    w=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
    t=1-u-w;zz=u*a[2]+w*b[2]+t*c[2]
    sub=zbuf[y0:y1+1,x0:x1+1];mask=(u>=-1e-7)&(w>=-1e-7)&(t>=-1e-7)&(zz>sub)
    sub[mask]=zz[mask];rgb[y0:y1+1,x0:x1+1][mask]=col.astype(np.uint8)
 im=Image.fromarray(rgb);dr=ImageDraw.Draw(im)
 font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',30);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
 title='BOTH FLOORS' if mode==0 else f'LEVEL {mode}'
 dr.text((55,30),f'SRISAWAN | NEW LAYOUT | {title}',fill='#243c50',font=font)
 dr.text((55,77),'Aligned lift core | L2 +5.00 m | Walls 4.00 m | 1.20 m lift door reference',fill='#526878',font=small)
 dr.text((55,1060),'Geometry check preview (not a 3ds Max render). No furniture or landscape.',fill='#526878',font=small)
 im.save(O/f'Model_Check_{mode}.png')
for mode in [0,1,2]:render(mode)
print('Three depth-tested geometry previews generated.')
