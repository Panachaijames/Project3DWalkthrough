from pathlib import Path
import json,re,math
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent
d=json.loads((O/'trace_data.json').read_text());s=d['scale_m_per_image_unit']
objects=[]
def solid(name,poly,z,h,mat):
 n=len(poly);v=[(x,y,z) for x,y in poly]+[(x,y,z+h) for x,y in poly]
 f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 objects.append((name,mat,v,f))
def xy(p):return ((p[0]-940)*s,(700-p[1])*s)
def intervals(poly,y):
 xs=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if min(a[1],b[1])<y<max(a[1],b[1]):xs.append(a[0]+(b[0]-a[0])*(y-a[1])/(b[1]-a[1]))
 return sorted(xs)
def slab(name,poly,holes,z):
 loops=[poly]+holes;ys=sorted(set(p[1] for loop in loops for p in loop))
 for i,(y0,y1) in enumerate(zip(ys,ys[1:])):
  e=(y1-y0)*1e-7
  xs0=sorted(x for loop in loops for x in intervals(loop,y0+e));xs1=sorted(x for loop in loops for x in intervals(loop,y1-e))
  assert len(xs0)==len(xs1) and len(xs0)%2==0
  for j in range(0,len(xs0),2):
   solid(name+f'_{i}_{j}',[xy(p) for p in [(xs0[j],y0),(xs0[j+1],y0),(xs1[j+1],y1),(xs1[j],y1)]],z,.25,'slabMat')
slab('L1_Floor',d['outline1'],[],-.25)
slab('L2_Floor_TWO_VOIDS',d['outline2'],d['voids'],4.75)
txt=(O/'Build_Srisawan.ms').read_text()
for a,b,t,h,name,layer,mat in re.findall(r'wallSeg \[([^]]+)\] \[([^]]+)\] ([\d.]+) ([\d.]+) "([^"]+)" "([^"]+)" (\w+)',txt):
 a=list(map(float,a.split(',')));b=list(map(float,b.split(',')));t=float(t);h=float(h)
 dx=b[0]-a[0];dy=b[1]-a[1];l=math.hypot(dx,dy);nx=-dy/l*t/2;ny=dx/l*t/2
 solid(name,[(a[0]+nx,a[1]+ny),(a[0]-nx,a[1]-ny),(b[0]-nx,b[1]-ny),(b[0]+nx,b[1]+ny)],a[2],h,mat)
for name,w,l,h,p,layer in re.findall(r'o=box name:"([^"]+)" width:([\d.]+) length:([\d.]+) height:([\d.]+) pos:\[([^]]+)\]; assignObj o "([^"]+)" frameMat',txt):
 x,y,z=map(float,p.split(','));w=float(w)/2;l=float(l)/2
 solid(name,[(x-w,y-l),(x+w,y-l),(x+w,y+l),(x-w,y+l)],z,float(h),'frameMat')
with (O/'Srisawan_L1_L2_Schematic.obj').open('w') as f:
 f.write('# Units: metres. Z up. Raster trace, approximate horizontal dimensions.\nmtllib Srisawan.mtl\n');offset=1
 for i,(name,mat,v,faces) in enumerate(objects):
  f.write(f'o {name}_{i}\nusemtl {mat}\n')
  for p in v:f.write('v '+' '.join(f'{c:.6f}' for c in p)+'\n')
  for face in faces:f.write('f '+' '.join(str(k+offset) for k in face)+'\n')
  offset+=len(v)
colors={'wallMat':(220,217,209),'slabMat':(164,177,188),'glassMat':(126,199,214),'frameMat':(63,79,91)}
with (O/'Srisawan.mtl').open('w') as f:
 for k,c in colors.items():f.write(f'newmtl {k}\nKd '+' '.join(str(v/255) for v in c)+f'\nd {0.28 if k=="glassMat" else 1}\n\n')
def preview(level):
 sel=[o for o in objects if o[0].startswith(f'L{level}_') or (level==2 and o[0].startswith('Void_'))]
 zbase=0 if level==1 else 5
 def proj(p):
  x,y,z=p;return (x*.89+y*.45,x*.24-y*.48-(z-zbase)*1.0)
 allp=[proj(p) for _,_,v,_ in sel for p in v];lo=[min(p[k] for p in allp) for k in [0,1]];hi=[max(p[k] for p in allp) for k in [0,1]]
 scale=min(1700/(hi[0]-lo[0]),900/(hi[1]-lo[1]))
 def screen(p):
  q=proj(p);return (95+(q[0]-lo[0])*scale,155+(q[1]-lo[1])*scale)
 im=Image.new('RGB',(1900,1150),(243,246,248));draw=ImageDraw.Draw(im)
 faces=[]
 for _,mat,v,ff in sel:
  for k,f in enumerate(ff):
   pp=[v[j] for j in f];depth=sum(-p[0]*.45+p[1]*.89+p[2]*.45 for p in pp)/len(pp)
   c=colors[mat];shade=1 if k==1 else .80 if k%2 else .90
   faces.append((depth,[screen(p) for p in pp],tuple(int(t*shade) for t in c),mat))
 for _,p,c,mat in sorted(faces,key=lambda f:-f[0]):draw.polygon(p,fill=c,outline=(100,118,130) if mat!='slabMat' else c)
 try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',34);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
 except:font=small=None
 draw.text((70,40),f'SRISAWAN  /  LEVEL {level}  /  SCHEMATIC SHELL',font=font,fill=(27,48,66))
 draw.text((70,91),'4.00 m wall height | Floor-to-floor 5.00 m | No furniture | Raster-traced approximate plan',font=small,fill=(65,91,110))
 draw.text((70,1090),'Blue: provisional garden-facing glazing. Door openings and fine wet-room partitions require refinement.',font=small,fill=(65,91,110))
 im.save(O/f'L{level}_3D_preview.png')
preview(1);preview(2)
(O/'geometry_check.txt').write_text(f'Objects: {len(objects)}\nVertices: {offset-1}\nL1 walls: z=0..4\nL2 walls: z=5..9\nL2 slab: z=4.75..5 with two void cutouts\nMetres; Z up.\n')
print('Exported',len(objects),'objects;',offset-1,'vertices')
