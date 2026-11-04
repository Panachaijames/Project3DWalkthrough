from pathlib import Path
from PIL import Image, ImageDraw
import math

OUT = Path(__file__).resolve().parent
SRC = Path(r"C:\Users\DWP\Desktop\test xxx.jpg")

# Trace coordinates use the 2048 x 814 review image. The plan's lift-core axes are
# horizontal/vertical. Origin is placed at the centre of the three clean-lift shafts.
ORIGIN = (1128.0, 373.0)
M_PER_PX = 1.20 / 29.0  # calibrated from a 1.20 m lift-door opening in the core

def P(text):
    return [tuple(map(float, q.split(','))) for q in text.split()]

walls = []
core = []

def add(dst, text):
    for line in text.strip().splitlines():
        line = line.strip()
        if line:
            dst.append(P(line))

# Left patient-room wing - partition centre lines only.
add(walls, '''
250,42 232,88 215,133 202,170
265,55 242,113 226,150
309,72 289,122 270,172
362,91 344,143 322,197
416,111 399,159 377,215
469,130 450,179 429,232
521,150 503,198 482,250
574,169 556,218 534,268
628,189 610,237 588,286
681,208 663,256 641,305
734,228 716,276 694,325
786,246 768,295 747,344
836,266 819,314 798,363
887,284 870,333 849,382
240,182 260,191 280,198 300,205
318,210 338,218 358,225 378,232
397,239 417,246 437,253 457,260
477,267 497,274 517,281 537,288
557,295 577,302 597,309 617,316
637,323 657,330 677,337 697,344
717,351 737,358 757,365 777,372
204,278 242,292 280,306 318,320
339,327 379,342 419,357 459,372
479,379 519,394 559,409 599,424
620,432 660,447 700,462 740,477
178,323 216,337 254,351 292,365
312,372 352,387 392,402 432,417
452,424 492,439 532,454 572,469
592,476 632,491 672,506 712,521
305,110 291,148
329,160 315,198
410,142 395,182
434,192 420,231
516,175 501,215
540,225 526,264
622,208 607,248
646,258 632,297
728,241 713,281
752,291 738,330
834,274 819,314
858,324 844,364
282,314 266,356
366,345 350,389
450,376 434,420
534,408 518,451
618,439 602,482
702,470 686,513
''')

# Service/support rooms adjoining the lift lobby.
add(walls, '''
842,84 936,84 936,172
858,84 858,121 909,121
858,121 825,185
825,185 904,214
939,82 939,313
936,171 880,171 880,275
880,226 837,226
837,226 837,318
880,275 923,275
923,275 923,323
786,223 786,335
786,257 832,257
786,294 832,294
''')

# Right patient-room wing above corridor.
add(walls, '''
1305,333 1305,539
1370,333 1370,539
1436,333 1436,539
1503,333 1503,539
1570,333 1570,539
1637,333 1637,539
1705,333 1705,539
1772,333 1772,539
1839,333 1839,539
1907,333 1907,539
1977,333 1977,539
1369,459 1436,459
1436,459 1436,516
1502,459 1570,459
1570,459 1570,516
1636,459 1705,459
1705,459 1705,516
1771,459 1839,459
1839,459 1839,516
1906,444 1977,444
1906,444 1906,516
1839,421 1907,421
1839,421 1839,462
''')

# Right patient-room wing below corridor.
add(walls, '''
882,604 882,809
948,604 948,809
1015,604 1015,809
1082,604 1082,809
1149,604 1149,809
1217,604 1217,809
1284,604 1284,809
1351,604 1351,809
1419,604 1419,809
1486,604 1486,809
1554,604 1554,809
1622,604 1622,809
1689,604 1689,809
1757,604 1757,809
1825,604 1825,809
1893,604 1893,809
1961,604 1961,809
882,681 948,681
1015,681 1082,681
1149,681 1217,681
1284,681 1351,681
1419,681 1486,681
1554,681 1622,681
1689,681 1757,681
1825,681 1893,681
948,707 1015,707
1082,707 1149,707
1217,707 1284,707
1351,707 1419,707
1486,707 1554,707
1622,707 1689,707
1757,707 1825,707
1893,707 1961,707
''')

# Internal bathroom partitions in left wing (paired room modules).
add(walls, '''
236,197 273,211 263,239 226,225
273,211 309,224 299,252 263,239
395,255 432,269 422,297 385,283
432,269 469,283 459,311 422,297
554,313 591,327 581,355 544,341
591,327 628,341 618,369 581,355
713,371 750,385 740,413 703,399
750,385 787,399 777,427 740,413
264,338 301,352 291,380 254,366
301,352 338,366 328,394 291,380
423,396 460,410 450,438 413,424
460,410 497,424 487,452 450,438
582,454 619,468 609,496 572,482
619,468 656,482 646,510 609,496
''')

# Bathroom/service partitions in the right wings.
add(walls, '''
1424,454 1424,516
1450,454 1450,493
1450,493 1482,493
1557,454 1557,516
1583,454 1583,493
1583,493 1615,493
1692,454 1692,516
1718,454 1718,493
1718,493 1750,493
1827,454 1827,516
1853,454 1853,493
1853,493 1885,493
935,604 935,673
961,604 961,648
961,648 993,648
1069,604 1069,673
1095,604 1095,648
1095,648 1127,648
1204,604 1204,673
1230,604 1230,648
1230,648 1262,648
1338,604 1338,673
1364,604 1364,648
1364,648 1396,648
1473,604 1473,673
1499,604 1499,648
1499,648 1531,648
1609,604 1609,673
1635,604 1635,648
1635,648 1667,648
1744,604 1744,673
1770,604 1770,648
1770,648 1802,648
1879,604 1879,673
1905,604 1905,648
1905,648 1937,648
''')

# Lift/stair core reference - separate layer. This is not part of INTERIOR_WALL.
add(core, '''
958,85 1302,85 1302,337
958,85 958,300
958,300 1002,300
1002,300 1002,397
1002,397 1233,397
1233,397 1233,337
1233,337 1302,337
1003,92 1068,92 1068,301 1003,301 1003,92
1092,92 1160,92 1160,297 1092,297 1092,92
1172,93 1232,93 1232,297 1172,297 1172,93
1010,311 1068,311 1068,369 1010,369 1010,311
1092,311 1147,311 1147,369 1092,369 1092,311
1160,311 1218,311 1218,369 1160,369 1160,311
''')

def to_world(p):
    return ((p[0]-ORIGIN[0])*M_PER_PX, (ORIGIN[1]-p[1])*M_PER_PX)

def dxf_pair(code, value):
    return f"{code}\n{value}\n"

def layer_record(name, color):
    return (dxf_pair(0,'LAYER') + dxf_pair(2,name) + dxf_pair(70,0) +
            dxf_pair(62,color) + dxf_pair(6,'CONTINUOUS'))

def line_entity(layer, a, b):
    a=to_world(a); b=to_world(b)
    return (dxf_pair(0,'LINE')+dxf_pair(8,layer)+dxf_pair(10,f'{a[0]:.6f}')+
            dxf_pair(20,f'{a[1]:.6f}')+dxf_pair(30,'0.0')+
            dxf_pair(11,f'{b[0]:.6f}')+dxf_pair(21,f'{b[1]:.6f}')+dxf_pair(31,'0.0'))

def write_dxf(path):
    s=dxf_pair(0,'SECTION')+dxf_pair(2,'HEADER')
    s+=dxf_pair(9,'$ACADVER')+dxf_pair(1,'AC1009')
    s+=dxf_pair(9,'$INSUNITS')+dxf_pair(70,6)  # metres
    s+=dxf_pair(0,'ENDSEC')
    s+=dxf_pair(0,'SECTION')+dxf_pair(2,'TABLES')
    s+=dxf_pair(0,'TABLE')+dxf_pair(2,'LAYER')+dxf_pair(70,4)
    s+=layer_record('INTERIOR_WALL',7)
    s+=layer_record('LIFT_CORE_REFERENCE',1)
    s+=layer_record('AXIS_REFERENCE',3)
    s+=layer_record('NOTES',8)
    s+=dxf_pair(0,'ENDTAB')+dxf_pair(0,'ENDSEC')
    s+=dxf_pair(0,'SECTION')+dxf_pair(2,'ENTITIES')
    for poly in walls:
        for a,b in zip(poly,poly[1:]): s+=line_entity('INTERIOR_WALL',a,b)
    for poly in core:
        for a,b in zip(poly,poly[1:]): s+=line_entity('LIFT_CORE_REFERENCE',a,b)
    # 5 m axes through the lift-core origin.
    s+=line_entity('AXIS_REFERENCE',(ORIGIN[0]-120,ORIGIN[1]),(ORIGIN[0]+120,ORIGIN[1]))
    s+=line_entity('AXIS_REFERENCE',(ORIGIN[0],ORIGIN[1]-120),(ORIGIN[0],ORIGIN[1]+120))
    s+=dxf_pair(0,'ENDSEC')+dxf_pair(0,'EOF')
    path.write_text(s,encoding='ascii')

def validate(path):
    text=path.read_text(encoding='ascii')
    assert text.endswith('0\nEOF\n')
    assert text.count('\nLINE\n') == sum(len(p)-1 for p in walls+core)+2
    # Confirm the DXF scale encodes the stated lift-door reference.
    assert abs(29*M_PER_PX-1.20)<1e-9
    for poly in walls+core:
        for a,b in zip(poly,poly[1:]):
            assert math.dist(a,b)>1.0

def overlay(path):
    im=Image.open(SRC).convert('RGB').resize((2048,814))
    dr=ImageDraw.Draw(im,'RGBA')
    for poly in walls: dr.line(poly,fill=(255,25,25,220),width=3)
    for poly in core: dr.line(poly,fill=(0,125,255,230),width=3)
    dr.ellipse((ORIGIN[0]-7,ORIGIN[1]-7,ORIGIN[0]+7,ORIGIN[1]+7),fill=(0,220,80,255))
    dr.line((ORIGIN[0]-50,ORIGIN[1],ORIGIN[0]+50,ORIGIN[1]),fill=(0,220,80,255),width=2)
    dr.line((ORIGIN[0],ORIGIN[1]-50,ORIGIN[0],ORIGIN[1]+50),fill=(0,220,80,255),width=2)
    im.save(path)

OUT.mkdir(parents=True,exist_ok=True)
dxf=OUT/'Srisawan_Floor6_Interior_Walls.dxf'
write_dxf(dxf); validate(dxf); overlay(OUT/'Srisawan_Floor6_Trace_Check.png')
(OUT/'README_TH.txt').write_text('''Srisawan Hospital - Floor 6 interior wall trace\n\nไฟล์: Srisawan_Floor6_Interior_Walls.dxf\nรูปแบบ: AutoCAD R12 ASCII DXF\nหน่วย: เมตร\nจุดกำเนิด: แกนกลางกลุ่ม Clean Lift Core\nสเกล: อ้างอิงช่องประตูลิฟต์ 1.20 ม.\n\nLayers\n- INTERIOR_WALL: เส้นกึ่งกลางผนังกั้นห้อง\n- LIFT_CORE_REFERENCE: แนว Lift/Core สำหรับตรวจตำแหน่ง\n- AXIS_REFERENCE: แกน X/Y ที่จุดกำเนิด\n\nไม่ได้รวม Furniture, Landscape, ประตู, สุขภัณฑ์, งานระบบ และ Facade\nเส้นถอดจากภาพ JPG จึงใช้เป็น mass-model reference; ความแม่นยำระดับก่อสร้างต้องใช้ DWG ต้นฉบับ\n''',encoding='utf-8')
print(dxf)
print('Wall polylines',len(walls),'Core polylines',len(core),'LINE entities',sum(len(p)-1 for p in walls+core)+2)
