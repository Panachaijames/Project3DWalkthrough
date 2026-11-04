from pathlib import Path
import math,json
from PIL import Image,ImageDraw
O=Path(__file__).resolve().parent
# Traced in a common 1888 x 1334 image coordinate system. Raster accuracy only.
outline1=[(500,169),(680,251),(1527,251),(1527,607),(1480,607),(1480,839),(1140,839),(1090,800),(1090,780),(831,780),(801,798),(766,875),(734,895),(701,898),(589,856),(517,755),(508,704),(540,607),(557,551),(424,490),(397,460),(390,411),(406,376),(463,401),(483,366),(419,347)]
outline2=[(574,177),(714,240),(1527,240),(1527,733),(1480,733),(1480,901),(1470,922),(1450,932),(814,932),(385,758),(366,739),(358,710),(358,573),(368,523),(405,482),(435,482)]
voids=[[(760,491),(866,537),(821,654),(806,668),(678,616)],[(955,592),(1087,592),(1087,674),(1076,687),(940,687),(920,678),(909,659),(913,635),(932,603)]]
def area(p):return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1]))/2)
# Approximate calibration to stated floor 2 GFA; NOT a surveyed dimension.
S=math.sqrt(3116/area(outline2))
def pts(s):return [tuple(map(float,p.split(','))) for p in s.split()]
W1=[];W2=[]
def add(dst,s):dst.append(pts(s))
for s in [
'938,252 938,357 1127,357 1127,252','1035,252 1035,319 1127,319','1077,252 1077,319','1180,252 1180,317 1191,332 1387,332 1387,252','1230,252 1230,332','1296,252 1296,332','1433,252 1433,433 1527,433','1387,332 1433,332','1127,357 1127,403 1142,417 1351,417 1351,374 1386,374 1386,417 1411,417','1188,370 1188,417','1234,370 1234,417','1269,370 1269,417','1295,370 1295,417','1325,370 1325,417',
'1127,451 1206,451 1206,514 1337,514 1337,451 1127,451','1246,451 1246,514','1294,451 1294,514','1127,451 1127,660 1142,676 1206,676','1237,544 1337,544 1337,615 1237,615 1237,544','1287,544 1287,615','1206,647 1287,647 1287,776 1206,776 1206,647','1206,722 1287,722','1206,678 1251,678','1287,647 1373,647 1373,744 1287,744','1327,647 1327,697 1373,697','1327,715 1327,776 1287,776','1337,451 1337,615 1373,615','1411,417 1450,417 1450,451 1497,451','1497,433 1497,565 1527,565','1450,491 1497,491','1450,521 1497,521','1410,568 1480,568 1480,725 1410,725 1410,568','1410,658 1480,658','1410,725 1373,725','1438,725 1438,839','1410,778 1438,778',
'558,192 505,307 559,332','539,234 591,257','521,274 573,298','615,219 592,268 644,292 668,242','592,324 616,334 641,344 674,355 662,393 588,362 592,324','616,334 602,369','641,344 627,381','643,295 701,322 684,358','665,305 649,341','682,313 667,349','535,381 765,483 718,588 557,551','577,401 556,447','620,421 599,468','665,441 643,489','710,460 689,507','734,471 714,514','583,470 744,541','621,487 585,565','662,506 626,583','701,523 667,601','724,366 820,408 795,455 700,413 724,366','763,384 740,430','803,401 780,447','818,377 850,390 836,423','789,438 883,496 871,535 767,489 789,438','825,458 807,513','650,650 759,699 745,732','650,650 634,685 672,702 643,771','689,667 671,708','634,685 607,705 586,742','607,705 650,726','517,716 671,788 683,855','938,727 1014,727 1014,802 938,802 938,727','1045,727 1045,802','1124,727 1169,727 1169,788 1124,788 1124,727']:
 add(W1,s)
for s in [
'656,214 608,311 648,330 690,228','640,254 675,270','625,283 660,299','714,277 771,300 713,423 665,402 714,277','689,332 740,356','675,366 724,390','613,408 665,430 651,458 713,485 696,526 583,476 613,408','614,408 597,447','665,430 650,469','771,283 851,283 851,327 891,344 891,371 851,354 827,407 713,357','776,309 851,343','752,340 830,374','742,367 819,399','725,399 796,430','750,411 718,477','784,424 739,537 697,518','784,454 886,494 870,535 767,493','823,471 807,509',
'941,240 941,355 1131,355 1131,310 990,310 990,240','1039,240 1039,263 990,263','991,310 991,355','1040,310 1040,355','1088,310 1088,368 1131,368','1166,240 1166,301 1248,301 1248,240','1166,301 1166,345 1238,345 1238,301','1166,347 1248,347 1248,405 1166,405 1166,347','1207,347 1207,405','1291,240 1291,294 1390,294 1390,240','1344,240 1344,294','1448,240 1448,367 1527,367','1287,329 1390,329 1390,380 1287,380 1287,329','1322,329 1322,380','1355,329 1355,380','1390,329 1448,329','1328,380 1390,380 1390,471 1328,471 1328,380','1328,426 1390,426','1390,402 1448,402 1448,453 1390,453','1448,367 1448,400 1527,400','1485,400 1485,458 1527,458','1448,458 1448,502 1527,502','1418,453 1448,453 1448,502 1418,502 1418,453','1328,471 1390,471 1390,503 1328,503','1328,503 1380,503 1380,560 1328,560','1328,560 1380,560 1380,622 1328,622','1328,622 1448,622 1448,679','1448,502 1448,622 1527,622','1485,502 1485,622',
'1128,439 1207,439 1207,491 1128,491','1165,439 1165,491','1207,439 1248,439 1248,489 1207,489','1165,491 1248,491 1248,531 1165,531 1165,491','1128,491 1128,664 1140,678 1287,678 1287,439','1128,548 1187,548 1187,613 1128,613','1187,548 1248,548 1248,613 1187,613','1207,531 1207,548','1287,380 1287,489 1328,489',
'359,573 416,573 416,648 360,648','359,609 416,609','446,605 505,605 505,650 446,650 446,605','505,605 551,622 528,673 484,655','399,648 416,648 433,655 399,728','433,655 474,674 440,748','474,674 513,691 479,765','513,691 552,709 518,782','399,728 551,796','418,737 399,765','458,755 440,782','498,773 478,799','551,622 591,641 565,697 526,679','551,796 583,726 605,736 593,765 632,783 610,831','570,791 611,809','668,666 711,684 694,724 659,708 668,666','711,684 758,704 728,772','678,827 722,847 698,903','850,737 1167,737','850,737 813,932','840,834 890,834 890,894 826,894','826,894 889,894 889,932','887,816 935,816 935,932','935,816 1045,816 1045,850 935,850','923,850 923,932','989,850 989,932','923,892 1045,892','1078,792 1125,792 1125,932','1078,849 1125,849','1078,883 1125,883','1167,737 1167,815 1125,815','1199,815 1199,850 1125,850','1162,815 1162,850','1125,885 1290,885 1290,932','1165,885 1165,932','1207,885 1207,932','1248,885 1248,932','1290,885 1344,885 1344,932','1254,737 1254,779 1353,779 1353,737','1296,737 1296,779','1287,815 1363,815 1363,850 1287,850 1287,815','1415,720 1480,720','1415,720 1415,751 1480,751','1415,784 1480,784','1415,815 1480,815','1415,849 1480,849','1377,737 1377,785']:
 add(W2,s)
# Repeated aligned service/lift core.
core=['940,357 940,473 1006,473 1006,357 940,357','1006,357 1090,357 1090,473 1006,473','1048,357 1048,473','1048,401 1090,401','1048,437 1090,437','968,473 1090,473 1090,592 968,592 968,473','1006,473 1006,592','1048,473 1048,523 1090,523','968,516 1006,516','968,553 1006,553']
for s in core:add(W1,s);add(W2,s)
data={'scale_m_per_image_unit':S,'outline1':outline1,'outline2':outline2,'voids':voids,'walls1':W1,'walls2':W2}
(O/'trace_data.json').write_text(json.dumps(data,indent=2))
ms=['-- Srisawan schematic raster-traced model. Run in a separate scene.','resetMaxFile #noPrompt','units.systemType = #meters','units.systemScale = 1.0','units.displayType = #metric','units.metricType = #meters',
'wallMat = standardMaterial name:"Partition warm white" diffuse:(color 220 217 209)',
'slabMat = standardMaterial name:"Floor slab" diffuse:(color 165 172 179)',
'glassMat = standardMaterial name:"Curtain wall provisional" diffuse:(color 103 182 205) opacity:28 twoSided:true',
'frameMat = standardMaterial name:"Facade mullions" diffuse:(color 68 83 93)',
'fn layerFor n = (local l = LayerManager.getLayerFromName n; if l == undefined do l = LayerManager.newLayerFromName n; l)',
'fn assignObj o ln mt = (o.material=mt; o.wirecolor=mt.diffuse; (layerFor ln).addNode o)',
'fn wallSeg a b thick ht nm ln mt = (local d=b-a; local o=box name:nm width:(length d) length:thick height:ht pos:((a+b)/2); o.rotation=angleaxis (atan2 d.y d.x) [0,0,1]; assignObj o ln mt; o)',
]
def point(p,z):return f'[{(p[0]-940)*S:.5f},{(700-p[1])*S:.5f},{z:.5f}]'
def slab(name,poly,holes,z,t,layer):
 ms.append(f's=splineShape name:"{name}"')
 for i,loop in enumerate([poly]+holes,1):
  ms.append('addNewSpline s')
  for p in loop:ms.append(f'addKnot s {i} #corner #line {point(p,z)}')
  ms.append(f'close s {i}')
 ms.extend(['updateShape s',f'addModifier s (extrude amount:{t})',f'assignObj s "{layer}" slabMat'])
slab('L1_Floor',outline1,[],-.25,.25,'L1_Slabs')
slab('L2_Floor_TWO_VOIDS',outline2,voids,4.75,.25,'L2_Slabs')
for level,walls,z in [(1,W1,0),(2,W2,5.0)]:
 for i,line in enumerate(walls):
  for j,(a,b) in enumerate(zip(line,line[1:])):
   ms.append(f'wallSeg {point(a,z)} {point(b,z)} 0.15 4.0 "L{level}_Partition_{i:03}_{j}" "L{level}_Partitions" wallMat')
 # Envelope initially glazed along public fronts, opaque along clinical/service side.
 outline=outline1 if level==1 else outline2
 for i,(a,b) in enumerate(zip(outline,outline[1:]+outline[:1])):
  glass=((a[1]>750 and b[1]>750 and max(a[0],b[0])<1145) or (a[0]<850 and b[0]<850) or (a[1]<260 and b[1]<260 and a[0]<1000)) if level==1 else ((max(a[0],b[0])<600) or (max(a[0],b[0])<850 and min(a[1],b[1])>830))
  mat='glassMat' if glass else 'wallMat'
  layer=f'L{level}_CurtainWall_PROVISIONAL' if glass else f'L{level}_Envelope'
  ms.append(f'wallSeg {point(a,z)} {point(b,z)} {0.06 if glass else 0.2} 4.0 "L{level}_Facade_{i:02}" "{layer}" {mat}')
  if glass:
   n=max(1,math.ceil(math.dist(a,b)*S/1.5))
   for k in range(n+1):
    p=(a[0]+(b[0]-a[0])*k/n,a[1]+(b[1]-a[1])*k/n)
    ms.append(f'o=box name:"L{level}_Mullion" width:0.06 length:0.10 height:4.0 pos:{point(p,z)}; assignObj o "L{level}_CurtainWall_PROVISIONAL" frameMat')
   for zz in [z,z+4]:ms.append(f'wallSeg {point(a,zz)} {point(b,zz)} 0.08 0.06 "L{level}_Transom" "L{level}_CurtainWall_PROVISIONAL" frameMat')
 # Hidden datum marks actual ceiling, not upper floor.
 ms.append(f'o=point name:"L{level}_Ceiling_Datum_{z+4}m" pos:[0,0,{z+4}] size:0.5; (layerFor "00_Datums").addNode o')
# Void edge guard as simple massing only.
for i,loop in enumerate(voids):
 for a,b in zip(loop,loop[1:]+loop[:1]):ms.append(f'wallSeg {point(a,5.0)} {point(b,5.0)} 0.04 1.1 "Void_{i+1}_Guard_PROVISIONAL" "L2_Void_Guards" glassMat')
ms += ['setUserProp rootNode "Model_Status" "SCHEMATIC raster trace; not construction accurate"',f'setUserProp rootNode "Scale" "Approximate GFA calibration: {S:.6f} metres/image unit"','setUserProp rootNode "Levels" "L1=0; L1 ceiling=4; L2=5.0 per user; L2 ceiling=9.0 per user"','setUserProp rootNode "Scope" "No furniture. Doors and detailed small wet-room cubicles not resolved. Facade allocation provisional."',
'viewport.setType #view_iso_user','viewport.setTM (matrix3 [0.707,-0.707,0] [0.408,0.408,0.816] [-0.577,-0.577,0.577] [0,0,0])','max tool zoomextents all',f'saveMaxFile @"{O.as_posix()}/Srisawan_L1_L2_Schematic.max" quiet:true',f'f=createFile @"{O.as_posix()}/build_success.txt"','format "Objects: %\\n" objects.count to:f','close f']
(O/'Build_Srisawan.ms').write_text('\n'.join(ms),encoding='utf-8')
# Review overlays preserve source for model accuracy checks.
for lev,walls,outline in [(1,W1,outline1),(2,W2,outline2)]:
 im=Image.open(O.parent.parent/f'tmp/pdfs/plan-{lev+6}-0.jpg').convert('RGB').resize((1888,1334))
 d=ImageDraw.Draw(im)
 d.line(outline+[outline[0]],fill='#007fdf',width=5)
 for line in walls:d.line(line,fill='#e53737',width=3)
 if lev==2:
  for loop in voids:d.line(loop+[loop[0]],fill='#00bc65',width=6)
 im.save(O/f'L{lev}_trace_review.jpg',quality=94)
print('Scale',S,'wall polylines',len(W1),len(W2),'script',O/'Build_Srisawan.ms')

