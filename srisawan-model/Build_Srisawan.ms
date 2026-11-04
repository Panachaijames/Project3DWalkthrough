-- Revision 02: corrected Zoom Extents MAX command.
-- SRISAWAN HOSPITAL / L1 + L2 / MAXScript schematic shell
-- Open a NEW EMPTY scene, then Scripting > Run Script.
-- Metres; floor-to-floor 5m; each level ceiling/wall height 4m.
-- Horizontal scale approximated from raster/GFA. Not dimensionally verified.
-- No furniture; detailed door openings / wet-room cubicles not resolved.
-- This script does not delete objects, overwrite files, or save automatically.
if objects.count > 0 do
(
    messageBox "Please open a new empty scene before running this script. Save your current work first." title:"Srisawan model"
    throw "Srisawan requires an empty scene. Existing objects were not changed."
)
units.systemType = #meters
units.systemScale = 1.0
units.displayType = #metric
units.metricType = #meters
wallMat = standardMaterial name:"Partition warm white" diffuse:(color 220 217 209)
slabMat = standardMaterial name:"Floor slab" diffuse:(color 165 172 179)
glassMat = standardMaterial name:"Curtain wall provisional" diffuse:(color 103 182 205) opacity:28 twoSided:true
frameMat = standardMaterial name:"Facade mullions" diffuse:(color 68 83 93)
fn layerFor n = (local l = LayerManager.getLayerFromName n; if l == undefined do l = LayerManager.newLayerFromName n; l)
fn assignObj o ln mt = (o.material=mt; o.wirecolor=mt.diffuse; (layerFor ln).addNode o)
fn wallSeg a b thick ht nm ln mt = (local d=b-a; local o=box name:nm width:(length d) length:thick height:ht pos:((a+b)/2); o.rotation=angleaxis (atan2 d.y d.x) [0,0,1]; assignObj o ln mt; o)
s=splineShape name:"L1_Floor"
addNewSpline s
addKnot s 1 #corner #line [-28.77172,34.72224,-0.25000]
addKnot s 1 #corner #line [-17.00147,29.36023,-0.25000]
addKnot s 1 #corner #line [38.38409,29.36023,-0.25000]
addKnot s 1 #corner #line [38.38409,6.08130,-0.25000]
addKnot s 1 #corner #line [35.31075,6.08130,-0.25000]
addKnot s 1 #corner #line [35.31075,-9.08925,-0.25000]
addKnot s 1 #corner #line [13.07806,-9.08925,-0.25000]
addKnot s 1 #corner #line [9.80854,-6.53903,-0.25000]
addKnot s 1 #corner #line [9.80854,-5.23122,-0.25000]
addKnot s 1 #corner #line [-7.12754,-5.23122,-0.25000]
addKnot s 1 #corner #line [-9.08925,-6.40825,-0.25000]
addKnot s 1 #corner #line [-11.37791,-11.44330,-0.25000]
addKnot s 1 #corner #line [-13.47040,-12.75110,-0.25000]
addKnot s 1 #corner #line [-15.62828,-12.94727,-0.25000]
addKnot s 1 #corner #line [-22.95199,-10.20088,-0.25000]
addKnot s 1 #corner #line [-27.66009,-3.59647,-0.25000]
addKnot s 1 #corner #line [-28.24860,-0.26156,-0.25000]
addKnot s 1 #corner #line [-26.15611,6.08130,-0.25000]
addKnot s 1 #corner #line [-25.04448,9.74315,-0.25000]
addKnot s 1 #corner #line [-33.74138,13.73196,-0.25000]
addKnot s 1 #corner #line [-35.50692,15.69367,-0.25000]
addKnot s 1 #corner #line [-35.96465,18.89779,-0.25000]
addKnot s 1 #corner #line [-34.91841,21.18645,-0.25000]
addKnot s 1 #corner #line [-31.19116,19.55169,-0.25000]
addKnot s 1 #corner #line [-29.88336,21.84035,-0.25000]
addKnot s 1 #corner #line [-34.06833,23.08277,-0.25000]
close s 1
updateShape s
addModifier s (extrude amount:0.25)
assignObj s "L1_Slabs" slabMat
s=splineShape name:"L2_Floor_TWO_VOIDS"
addNewSpline s
addKnot s 1 #corner #line [-23.93284,34.19911,4.75000]
addKnot s 1 #corner #line [-14.77820,30.07953,4.75000]
addKnot s 1 #corner #line [38.38409,30.07953,4.75000]
addKnot s 1 #corner #line [38.38409,-2.15788,4.75000]
addKnot s 1 #corner #line [35.31075,-2.15788,4.75000]
addKnot s 1 #corner #line [35.31075,-13.14345,4.75000]
addKnot s 1 #corner #line [34.65685,-14.51664,4.75000]
addKnot s 1 #corner #line [33.34904,-15.17054,4.75000]
addKnot s 1 #corner #line [-8.23917,-15.17054,4.75000]
addKnot s 1 #corner #line [-36.29160,-3.79264,4.75000]
addKnot s 1 #corner #line [-37.53402,-2.55022,4.75000]
addKnot s 1 #corner #line [-38.05714,-0.65390,4.75000]
addKnot s 1 #corner #line [-38.05714,8.30456,4.75000]
addKnot s 1 #corner #line [-37.40324,11.57408,4.75000]
addKnot s 1 #corner #line [-34.98380,14.25508,4.75000]
addKnot s 1 #corner #line [-33.02209,14.25508,4.75000]
close s 1
addNewSpline s
addKnot s 2 #corner #line [-11.77025,13.66657,4.75000]
addKnot s 2 #corner #line [-4.83888,10.65861,4.75000]
addKnot s 2 #corner #line [-7.78144,3.00795,4.75000]
addKnot s 2 #corner #line [-8.76230,2.09249,4.75000]
addKnot s 2 #corner #line [-17.13225,5.49278,4.75000]
close s 2
addNewSpline s
addKnot s 3 #corner #line [0.98085,7.06215,4.75000]
addKnot s 3 #corner #line [9.61237,7.06215,4.75000]
addKnot s 3 #corner #line [9.61237,1.70015,4.75000]
addKnot s 3 #corner #line [8.89308,0.85007,4.75000]
addKnot s 3 #corner #line [0.00000,0.85007,4.75000]
addKnot s 3 #corner #line [-1.30781,1.43859,4.75000]
addKnot s 3 #corner #line [-2.02710,2.68100,4.75000]
addKnot s 3 #corner #line [-1.76554,4.25037,4.75000]
addKnot s 3 #corner #line [-0.52312,6.34286,4.75000]
close s 3
updateShape s
addModifier s (extrude amount:0.25)
assignObj s "L2_Slabs" slabMat
wallSeg [-0.13078,29.29484,0.00000] [-0.13078,22.42886,0.00000] 0.15 4.0 "L1_Partition_000_0" "L1_Partitions" wallMat
wallSeg [-0.13078,22.42886,0.00000] [12.22798,22.42886,0.00000] 0.15 4.0 "L1_Partition_000_1" "L1_Partitions" wallMat
wallSeg [12.22798,22.42886,0.00000] [12.22798,29.29484,0.00000] 0.15 4.0 "L1_Partition_000_2" "L1_Partitions" wallMat
wallSeg [6.21208,29.29484,0.00000] [6.21208,24.91369,0.00000] 0.15 4.0 "L1_Partition_001_0" "L1_Partitions" wallMat
wallSeg [6.21208,24.91369,0.00000] [12.22798,24.91369,0.00000] 0.15 4.0 "L1_Partition_001_1" "L1_Partitions" wallMat
wallSeg [8.95847,29.29484,0.00000] [8.95847,24.91369,0.00000] 0.15 4.0 "L1_Partition_002_0" "L1_Partitions" wallMat
wallSeg [15.69367,29.29484,0.00000] [15.69367,25.04448,0.00000] 0.15 4.0 "L1_Partition_003_0" "L1_Partitions" wallMat
wallSeg [15.69367,25.04448,0.00000] [16.41296,24.06362,0.00000] 0.15 4.0 "L1_Partition_003_1" "L1_Partitions" wallMat
wallSeg [16.41296,24.06362,0.00000] [29.22945,24.06362,0.00000] 0.15 4.0 "L1_Partition_003_2" "L1_Partitions" wallMat
wallSeg [29.22945,24.06362,0.00000] [29.22945,29.29484,0.00000] 0.15 4.0 "L1_Partition_003_3" "L1_Partitions" wallMat
wallSeg [18.96318,29.29484,0.00000] [18.96318,24.06362,0.00000] 0.15 4.0 "L1_Partition_004_0" "L1_Partitions" wallMat
wallSeg [23.27894,29.29484,0.00000] [23.27894,24.06362,0.00000] 0.15 4.0 "L1_Partition_005_0" "L1_Partitions" wallMat
wallSeg [32.23741,29.29484,0.00000] [32.23741,17.45920,0.00000] 0.15 4.0 "L1_Partition_006_0" "L1_Partitions" wallMat
wallSeg [32.23741,17.45920,0.00000] [38.38409,17.45920,0.00000] 0.15 4.0 "L1_Partition_006_1" "L1_Partitions" wallMat
wallSeg [29.22945,24.06362,0.00000] [32.23741,24.06362,0.00000] 0.15 4.0 "L1_Partition_007_0" "L1_Partitions" wallMat
wallSeg [12.22798,22.42886,0.00000] [12.22798,19.42091,0.00000] 0.15 4.0 "L1_Partition_008_0" "L1_Partitions" wallMat
wallSeg [12.22798,19.42091,0.00000] [13.20884,18.50545,0.00000] 0.15 4.0 "L1_Partition_008_1" "L1_Partitions" wallMat
wallSeg [13.20884,18.50545,0.00000] [26.87540,18.50545,0.00000] 0.15 4.0 "L1_Partition_008_2" "L1_Partitions" wallMat
wallSeg [26.87540,18.50545,0.00000] [26.87540,21.31723,0.00000] 0.15 4.0 "L1_Partition_008_3" "L1_Partitions" wallMat
wallSeg [26.87540,21.31723,0.00000] [29.16406,21.31723,0.00000] 0.15 4.0 "L1_Partition_008_4" "L1_Partitions" wallMat
wallSeg [29.16406,21.31723,0.00000] [29.16406,18.50545,0.00000] 0.15 4.0 "L1_Partition_008_5" "L1_Partitions" wallMat
wallSeg [29.16406,18.50545,0.00000] [30.79882,18.50545,0.00000] 0.15 4.0 "L1_Partition_008_6" "L1_Partitions" wallMat
wallSeg [16.21679,21.57879,0.00000] [16.21679,18.50545,0.00000] 0.15 4.0 "L1_Partition_009_0" "L1_Partitions" wallMat
wallSeg [19.22474,21.57879,0.00000] [19.22474,18.50545,0.00000] 0.15 4.0 "L1_Partition_010_0" "L1_Partitions" wallMat
wallSeg [21.51340,21.57879,0.00000] [21.51340,18.50545,0.00000] 0.15 4.0 "L1_Partition_011_0" "L1_Partitions" wallMat
wallSeg [23.21355,21.57879,0.00000] [23.21355,18.50545,0.00000] 0.15 4.0 "L1_Partition_012_0" "L1_Partitions" wallMat
wallSeg [25.17526,21.57879,0.00000] [25.17526,18.50545,0.00000] 0.15 4.0 "L1_Partition_013_0" "L1_Partitions" wallMat
wallSeg [12.22798,16.28218,0.00000] [17.39381,16.28218,0.00000] 0.15 4.0 "L1_Partition_014_0" "L1_Partitions" wallMat
wallSeg [17.39381,16.28218,0.00000] [17.39381,12.16259,0.00000] 0.15 4.0 "L1_Partition_014_1" "L1_Partitions" wallMat
wallSeg [17.39381,12.16259,0.00000] [25.95994,12.16259,0.00000] 0.15 4.0 "L1_Partition_014_2" "L1_Partitions" wallMat
wallSeg [25.95994,12.16259,0.00000] [25.95994,16.28218,0.00000] 0.15 4.0 "L1_Partition_014_3" "L1_Partitions" wallMat
wallSeg [25.95994,16.28218,0.00000] [12.22798,16.28218,0.00000] 0.15 4.0 "L1_Partition_014_4" "L1_Partitions" wallMat
wallSeg [20.00942,16.28218,0.00000] [20.00942,12.16259,0.00000] 0.15 4.0 "L1_Partition_015_0" "L1_Partitions" wallMat
wallSeg [23.14816,16.28218,0.00000] [23.14816,12.16259,0.00000] 0.15 4.0 "L1_Partition_016_0" "L1_Partitions" wallMat
wallSeg [12.22798,16.28218,0.00000] [12.22798,2.61561,0.00000] 0.15 4.0 "L1_Partition_017_0" "L1_Partitions" wallMat
wallSeg [12.22798,2.61561,0.00000] [13.20884,1.56937,0.00000] 0.15 4.0 "L1_Partition_017_1" "L1_Partitions" wallMat
wallSeg [13.20884,1.56937,0.00000] [17.39381,1.56937,0.00000] 0.15 4.0 "L1_Partition_017_2" "L1_Partitions" wallMat
wallSeg [19.42091,10.20088,0.00000] [25.95994,10.20088,0.00000] 0.15 4.0 "L1_Partition_018_0" "L1_Partitions" wallMat
wallSeg [25.95994,10.20088,0.00000] [25.95994,5.55817,0.00000] 0.15 4.0 "L1_Partition_018_1" "L1_Partitions" wallMat
wallSeg [25.95994,5.55817,0.00000] [19.42091,5.55817,0.00000] 0.15 4.0 "L1_Partition_018_2" "L1_Partitions" wallMat
wallSeg [19.42091,5.55817,0.00000] [19.42091,10.20088,0.00000] 0.15 4.0 "L1_Partition_018_3" "L1_Partitions" wallMat
wallSeg [22.69043,10.20088,0.00000] [22.69043,5.55817,0.00000] 0.15 4.0 "L1_Partition_019_0" "L1_Partitions" wallMat
wallSeg [17.39381,3.46568,0.00000] [22.69043,3.46568,0.00000] 0.15 4.0 "L1_Partition_020_0" "L1_Partitions" wallMat
wallSeg [22.69043,3.46568,0.00000] [22.69043,-4.96966,0.00000] 0.15 4.0 "L1_Partition_020_1" "L1_Partitions" wallMat
wallSeg [22.69043,-4.96966,0.00000] [17.39381,-4.96966,0.00000] 0.15 4.0 "L1_Partition_020_2" "L1_Partitions" wallMat
wallSeg [17.39381,-4.96966,0.00000] [17.39381,3.46568,0.00000] 0.15 4.0 "L1_Partition_020_3" "L1_Partitions" wallMat
wallSeg [17.39381,-1.43859,0.00000] [22.69043,-1.43859,0.00000] 0.15 4.0 "L1_Partition_021_0" "L1_Partitions" wallMat
wallSeg [17.39381,1.43859,0.00000] [20.33638,1.43859,0.00000] 0.15 4.0 "L1_Partition_022_0" "L1_Partitions" wallMat
wallSeg [22.69043,3.46568,0.00000] [28.31399,3.46568,0.00000] 0.15 4.0 "L1_Partition_023_0" "L1_Partitions" wallMat
wallSeg [28.31399,3.46568,0.00000] [28.31399,-2.87717,0.00000] 0.15 4.0 "L1_Partition_023_1" "L1_Partitions" wallMat
wallSeg [28.31399,-2.87717,0.00000] [22.69043,-2.87717,0.00000] 0.15 4.0 "L1_Partition_023_2" "L1_Partitions" wallMat
wallSeg [25.30604,3.46568,0.00000] [25.30604,0.19617,0.00000] 0.15 4.0 "L1_Partition_024_0" "L1_Partitions" wallMat
wallSeg [25.30604,0.19617,0.00000] [28.31399,0.19617,0.00000] 0.15 4.0 "L1_Partition_024_1" "L1_Partitions" wallMat
wallSeg [25.30604,-0.98085,0.00000] [25.30604,-4.96966,0.00000] 0.15 4.0 "L1_Partition_025_0" "L1_Partitions" wallMat
wallSeg [25.30604,-4.96966,0.00000] [22.69043,-4.96966,0.00000] 0.15 4.0 "L1_Partition_025_1" "L1_Partitions" wallMat
wallSeg [25.95994,16.28218,0.00000] [25.95994,5.55817,0.00000] 0.15 4.0 "L1_Partition_026_0" "L1_Partitions" wallMat
wallSeg [25.95994,5.55817,0.00000] [28.31399,5.55817,0.00000] 0.15 4.0 "L1_Partition_026_1" "L1_Partitions" wallMat
wallSeg [30.79882,18.50545,0.00000] [33.34904,18.50545,0.00000] 0.15 4.0 "L1_Partition_027_0" "L1_Partitions" wallMat
wallSeg [33.34904,18.50545,0.00000] [33.34904,16.28218,0.00000] 0.15 4.0 "L1_Partition_027_1" "L1_Partitions" wallMat
wallSeg [33.34904,16.28218,0.00000] [36.42238,16.28218,0.00000] 0.15 4.0 "L1_Partition_027_2" "L1_Partitions" wallMat
wallSeg [36.42238,17.45920,0.00000] [36.42238,8.82769,0.00000] 0.15 4.0 "L1_Partition_028_0" "L1_Partitions" wallMat
wallSeg [36.42238,8.82769,0.00000] [38.38409,8.82769,0.00000] 0.15 4.0 "L1_Partition_028_1" "L1_Partitions" wallMat
wallSeg [33.34904,13.66657,0.00000] [36.42238,13.66657,0.00000] 0.15 4.0 "L1_Partition_029_0" "L1_Partitions" wallMat
wallSeg [33.34904,11.70486,0.00000] [36.42238,11.70486,0.00000] 0.15 4.0 "L1_Partition_030_0" "L1_Partitions" wallMat
wallSeg [30.73343,8.63152,0.00000] [35.31075,8.63152,0.00000] 0.15 4.0 "L1_Partition_031_0" "L1_Partitions" wallMat
wallSeg [35.31075,8.63152,0.00000] [35.31075,-1.63476,0.00000] 0.15 4.0 "L1_Partition_031_1" "L1_Partitions" wallMat
wallSeg [35.31075,-1.63476,0.00000] [30.73343,-1.63476,0.00000] 0.15 4.0 "L1_Partition_031_2" "L1_Partitions" wallMat
wallSeg [30.73343,-1.63476,0.00000] [30.73343,8.63152,0.00000] 0.15 4.0 "L1_Partition_031_3" "L1_Partitions" wallMat
wallSeg [30.73343,2.74639,0.00000] [35.31075,2.74639,0.00000] 0.15 4.0 "L1_Partition_032_0" "L1_Partitions" wallMat
wallSeg [30.73343,-1.63476,0.00000] [28.31399,-1.63476,0.00000] 0.15 4.0 "L1_Partition_033_0" "L1_Partitions" wallMat
wallSeg [32.56436,-1.63476,0.00000] [32.56436,-9.08925,0.00000] 0.15 4.0 "L1_Partition_034_0" "L1_Partitions" wallMat
wallSeg [30.73343,-5.10044,0.00000] [32.56436,-5.10044,0.00000] 0.15 4.0 "L1_Partition_035_0" "L1_Partitions" wallMat
wallSeg [-24.97909,33.21826,0.00000] [-28.44477,25.69838,0.00000] 0.15 4.0 "L1_Partition_036_0" "L1_Partitions" wallMat
wallSeg [-28.44477,25.69838,0.00000] [-24.91369,24.06362,0.00000] 0.15 4.0 "L1_Partition_036_1" "L1_Partitions" wallMat
wallSeg [-26.22150,30.47187,0.00000] [-22.82121,28.96789,0.00000] 0.15 4.0 "L1_Partition_037_0" "L1_Partitions" wallMat
wallSeg [-27.39853,27.85626,0.00000] [-23.99823,26.28689,0.00000] 0.15 4.0 "L1_Partition_038_0" "L1_Partitions" wallMat
wallSeg [-21.25184,31.45272,0.00000] [-22.75582,28.24860,0.00000] 0.15 4.0 "L1_Partition_039_0" "L1_Partitions" wallMat
wallSeg [-22.75582,28.24860,0.00000] [-19.35552,26.67923,0.00000] 0.15 4.0 "L1_Partition_039_1" "L1_Partitions" wallMat
wallSeg [-19.35552,26.67923,0.00000] [-17.78615,29.94875,0.00000] 0.15 4.0 "L1_Partition_039_2" "L1_Partitions" wallMat
wallSeg [-22.75582,24.58674,0.00000] [-21.18645,23.93284,0.00000] 0.15 4.0 "L1_Partition_040_0" "L1_Partitions" wallMat
wallSeg [-21.18645,23.93284,0.00000] [-19.55169,23.27894,0.00000] 0.15 4.0 "L1_Partition_040_1" "L1_Partitions" wallMat
wallSeg [-19.55169,23.27894,0.00000] [-17.39381,22.55964,0.00000] 0.15 4.0 "L1_Partition_040_2" "L1_Partitions" wallMat
wallSeg [-17.39381,22.55964,0.00000] [-18.17850,20.07481,0.00000] 0.15 4.0 "L1_Partition_040_3" "L1_Partitions" wallMat
wallSeg [-18.17850,20.07481,0.00000] [-23.01738,22.10191,0.00000] 0.15 4.0 "L1_Partition_040_4" "L1_Partitions" wallMat
wallSeg [-23.01738,22.10191,0.00000] [-22.75582,24.58674,0.00000] 0.15 4.0 "L1_Partition_040_5" "L1_Partitions" wallMat
wallSeg [-21.18645,23.93284,0.00000] [-22.10191,21.64418,0.00000] 0.15 4.0 "L1_Partition_041_0" "L1_Partitions" wallMat
wallSeg [-19.55169,23.27894,0.00000] [-20.46716,20.85950,0.00000] 0.15 4.0 "L1_Partition_042_0" "L1_Partitions" wallMat
wallSeg [-19.42091,26.48306,0.00000] [-15.62828,24.71752,0.00000] 0.15 4.0 "L1_Partition_043_0" "L1_Partitions" wallMat
wallSeg [-15.62828,24.71752,0.00000] [-16.73991,22.36347,0.00000] 0.15 4.0 "L1_Partition_043_1" "L1_Partitions" wallMat
wallSeg [-17.98233,25.82916,0.00000] [-19.02857,23.47511,0.00000] 0.15 4.0 "L1_Partition_044_0" "L1_Partitions" wallMat
wallSeg [-16.87069,25.30604,0.00000] [-17.85155,22.95199,0.00000] 0.15 4.0 "L1_Partition_045_0" "L1_Partitions" wallMat
wallSeg [-26.48306,20.85950,0.00000] [-11.44330,14.18969,0.00000] 0.15 4.0 "L1_Partition_046_0" "L1_Partitions" wallMat
wallSeg [-11.44330,14.18969,0.00000] [-14.51664,7.32371,0.00000] 0.15 4.0 "L1_Partition_046_1" "L1_Partitions" wallMat
wallSeg [-14.51664,7.32371,0.00000] [-25.04448,9.74315,0.00000] 0.15 4.0 "L1_Partition_046_2" "L1_Partitions" wallMat
wallSeg [-23.73667,19.55169,0.00000] [-25.10987,16.54374,0.00000] 0.15 4.0 "L1_Partition_047_0" "L1_Partitions" wallMat
wallSeg [-20.92489,18.24389,0.00000] [-22.29808,15.17054,0.00000] 0.15 4.0 "L1_Partition_048_0" "L1_Partitions" wallMat
wallSeg [-17.98233,16.93608,0.00000] [-19.42091,13.79735,0.00000] 0.15 4.0 "L1_Partition_049_0" "L1_Partitions" wallMat
wallSeg [-15.03976,15.69367,0.00000] [-16.41296,12.62032,0.00000] 0.15 4.0 "L1_Partition_050_0" "L1_Partitions" wallMat
wallSeg [-13.47040,14.97437,0.00000] [-14.77820,12.16259,0.00000] 0.15 4.0 "L1_Partition_051_0" "L1_Partitions" wallMat
wallSeg [-23.34433,15.03976,0.00000] [-12.81649,10.39705,0.00000] 0.15 4.0 "L1_Partition_052_0" "L1_Partitions" wallMat
wallSeg [-20.85950,13.92813,0.00000] [-23.21355,8.82769,0.00000] 0.15 4.0 "L1_Partition_053_0" "L1_Partitions" wallMat
wallSeg [-18.17850,12.68571,0.00000] [-20.53255,7.65066,0.00000] 0.15 4.0 "L1_Partition_054_0" "L1_Partitions" wallMat
wallSeg [-15.62828,11.57408,0.00000] [-17.85155,6.47364,0.00000] 0.15 4.0 "L1_Partition_055_0" "L1_Partitions" wallMat
wallSeg [-14.12430,21.84035,0.00000] [-7.84683,19.09396,0.00000] 0.15 4.0 "L1_Partition_056_0" "L1_Partitions" wallMat
wallSeg [-7.84683,19.09396,0.00000] [-9.48159,16.02062,0.00000] 0.15 4.0 "L1_Partition_056_1" "L1_Partitions" wallMat
wallSeg [-9.48159,16.02062,0.00000] [-15.69367,18.76701,0.00000] 0.15 4.0 "L1_Partition_056_2" "L1_Partitions" wallMat
wallSeg [-15.69367,18.76701,0.00000] [-14.12430,21.84035,0.00000] 0.15 4.0 "L1_Partition_056_3" "L1_Partitions" wallMat
wallSeg [-11.57408,20.66333,0.00000] [-13.07806,17.65537,0.00000] 0.15 4.0 "L1_Partition_057_0" "L1_Partitions" wallMat
wallSeg [-8.95847,19.55169,0.00000] [-10.46244,16.54374,0.00000] 0.15 4.0 "L1_Partition_058_0" "L1_Partitions" wallMat
wallSeg [-7.97761,21.12106,0.00000] [-5.88512,20.27099,0.00000] 0.15 4.0 "L1_Partition_059_0" "L1_Partitions" wallMat
wallSeg [-5.88512,20.27099,0.00000] [-6.80059,18.11311,0.00000] 0.15 4.0 "L1_Partition_059_1" "L1_Partitions" wallMat
wallSeg [-9.87393,17.13225,0.00000] [-3.72725,13.33962,0.00000] 0.15 4.0 "L1_Partition_060_0" "L1_Partitions" wallMat
wallSeg [-3.72725,13.33962,0.00000] [-4.51193,10.78940,0.00000] 0.15 4.0 "L1_Partition_060_1" "L1_Partitions" wallMat
wallSeg [-4.51193,10.78940,0.00000] [-11.31252,13.79735,0.00000] 0.15 4.0 "L1_Partition_060_2" "L1_Partitions" wallMat
wallSeg [-11.31252,13.79735,0.00000] [-9.87393,17.13225,0.00000] 0.15 4.0 "L1_Partition_060_3" "L1_Partitions" wallMat
wallSeg [-7.51988,15.82445,0.00000] [-8.69691,12.22798,0.00000] 0.15 4.0 "L1_Partition_061_0" "L1_Partitions" wallMat
wallSeg [-18.96318,3.26951,0.00000] [-11.83564,0.06539,0.00000] 0.15 4.0 "L1_Partition_062_0" "L1_Partitions" wallMat
wallSeg [-11.83564,0.06539,0.00000] [-12.75110,-2.09249,0.00000] 0.15 4.0 "L1_Partition_062_1" "L1_Partitions" wallMat
wallSeg [-18.96318,3.26951,0.00000] [-20.00942,0.98085,0.00000] 0.15 4.0 "L1_Partition_063_0" "L1_Partitions" wallMat
wallSeg [-20.00942,0.98085,0.00000] [-17.52459,-0.13078,0.00000] 0.15 4.0 "L1_Partition_063_1" "L1_Partitions" wallMat
wallSeg [-17.52459,-0.13078,0.00000] [-19.42091,-4.64271,0.00000] 0.15 4.0 "L1_Partition_063_2" "L1_Partitions" wallMat
wallSeg [-16.41296,2.15788,0.00000] [-17.58998,-0.52312,0.00000] 0.15 4.0 "L1_Partition_064_0" "L1_Partitions" wallMat
wallSeg [-20.00942,0.98085,0.00000] [-21.77496,-0.32695,0.00000] 0.15 4.0 "L1_Partition_065_0" "L1_Partitions" wallMat
wallSeg [-21.77496,-0.32695,0.00000] [-23.14816,-2.74639,0.00000] 0.15 4.0 "L1_Partition_065_1" "L1_Partitions" wallMat
wallSeg [-21.77496,-0.32695,0.00000] [-18.96318,-1.70015,0.00000] 0.15 4.0 "L1_Partition_066_0" "L1_Partitions" wallMat
wallSeg [-27.66009,-1.04624,0.00000] [-17.58998,-5.75434,0.00000] 0.15 4.0 "L1_Partition_067_0" "L1_Partitions" wallMat
wallSeg [-17.58998,-5.75434,0.00000] [-16.80530,-10.13549,0.00000] 0.15 4.0 "L1_Partition_067_1" "L1_Partitions" wallMat
wallSeg [-0.13078,-1.76554,0.00000] [4.83888,-1.76554,0.00000] 0.15 4.0 "L1_Partition_068_0" "L1_Partitions" wallMat
wallSeg [4.83888,-1.76554,0.00000] [4.83888,-6.66981,0.00000] 0.15 4.0 "L1_Partition_068_1" "L1_Partitions" wallMat
wallSeg [4.83888,-6.66981,0.00000] [-0.13078,-6.66981,0.00000] 0.15 4.0 "L1_Partition_068_2" "L1_Partitions" wallMat
wallSeg [-0.13078,-6.66981,0.00000] [-0.13078,-1.76554,0.00000] 0.15 4.0 "L1_Partition_068_3" "L1_Partitions" wallMat
wallSeg [6.86598,-1.76554,0.00000] [6.86598,-6.66981,0.00000] 0.15 4.0 "L1_Partition_069_0" "L1_Partitions" wallMat
wallSeg [12.03181,-1.76554,0.00000] [14.97437,-1.76554,0.00000] 0.15 4.0 "L1_Partition_070_0" "L1_Partitions" wallMat
wallSeg [14.97437,-1.76554,0.00000] [14.97437,-5.75434,0.00000] 0.15 4.0 "L1_Partition_070_1" "L1_Partitions" wallMat
wallSeg [14.97437,-5.75434,0.00000] [12.03181,-5.75434,0.00000] 0.15 4.0 "L1_Partition_070_2" "L1_Partitions" wallMat
wallSeg [12.03181,-5.75434,0.00000] [12.03181,-1.76554,0.00000] 0.15 4.0 "L1_Partition_070_3" "L1_Partitions" wallMat
wallSeg [0.00000,22.42886,0.00000] [0.00000,14.84359,0.00000] 0.15 4.0 "L1_Partition_071_0" "L1_Partitions" wallMat
wallSeg [0.00000,14.84359,0.00000] [4.31576,14.84359,0.00000] 0.15 4.0 "L1_Partition_071_1" "L1_Partitions" wallMat
wallSeg [4.31576,14.84359,0.00000] [4.31576,22.42886,0.00000] 0.15 4.0 "L1_Partition_071_2" "L1_Partitions" wallMat
wallSeg [4.31576,22.42886,0.00000] [0.00000,22.42886,0.00000] 0.15 4.0 "L1_Partition_071_3" "L1_Partitions" wallMat
wallSeg [4.31576,22.42886,0.00000] [9.80854,22.42886,0.00000] 0.15 4.0 "L1_Partition_072_0" "L1_Partitions" wallMat
wallSeg [9.80854,22.42886,0.00000] [9.80854,14.84359,0.00000] 0.15 4.0 "L1_Partition_072_1" "L1_Partitions" wallMat
wallSeg [9.80854,14.84359,0.00000] [4.31576,14.84359,0.00000] 0.15 4.0 "L1_Partition_072_2" "L1_Partitions" wallMat
wallSeg [7.06215,22.42886,0.00000] [7.06215,14.84359,0.00000] 0.15 4.0 "L1_Partition_073_0" "L1_Partitions" wallMat
wallSeg [7.06215,19.55169,0.00000] [9.80854,19.55169,0.00000] 0.15 4.0 "L1_Partition_074_0" "L1_Partitions" wallMat
wallSeg [7.06215,17.19764,0.00000] [9.80854,17.19764,0.00000] 0.15 4.0 "L1_Partition_075_0" "L1_Partitions" wallMat
wallSeg [1.83093,14.84359,0.00000] [9.80854,14.84359,0.00000] 0.15 4.0 "L1_Partition_076_0" "L1_Partitions" wallMat
wallSeg [9.80854,14.84359,0.00000] [9.80854,7.06215,0.00000] 0.15 4.0 "L1_Partition_076_1" "L1_Partitions" wallMat
wallSeg [9.80854,7.06215,0.00000] [1.83093,7.06215,0.00000] 0.15 4.0 "L1_Partition_076_2" "L1_Partitions" wallMat
wallSeg [1.83093,7.06215,0.00000] [1.83093,14.84359,0.00000] 0.15 4.0 "L1_Partition_076_3" "L1_Partitions" wallMat
wallSeg [4.31576,14.84359,0.00000] [4.31576,7.06215,0.00000] 0.15 4.0 "L1_Partition_077_0" "L1_Partitions" wallMat
wallSeg [7.06215,14.84359,0.00000] [7.06215,11.57408,0.00000] 0.15 4.0 "L1_Partition_078_0" "L1_Partitions" wallMat
wallSeg [7.06215,11.57408,0.00000] [9.80854,11.57408,0.00000] 0.15 4.0 "L1_Partition_078_1" "L1_Partitions" wallMat
wallSeg [1.83093,12.03181,0.00000] [4.31576,12.03181,0.00000] 0.15 4.0 "L1_Partition_079_0" "L1_Partitions" wallMat
wallSeg [1.83093,9.61237,0.00000] [4.31576,9.61237,0.00000] 0.15 4.0 "L1_Partition_080_0" "L1_Partitions" wallMat
wallSeg [-28.77172,34.72224,0.00000] [-17.00147,29.36023,0.00000] 0.06 4.0 "L1_Facade_00" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-28.77172,34.72224,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-27.46392,34.12646,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-26.15611,33.53068,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-24.84830,32.93490,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-23.54050,32.33912,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-22.23269,31.74335,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-20.92489,31.14757,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-19.61708,30.55179,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-18.30928,29.95601,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-17.00147,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-28.77172,34.72224,0.00000] [-17.00147,29.36023,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-28.77172,34.72224,4.00000] [-17.00147,29.36023,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-17.00147,29.36023,0.00000] [38.38409,29.36023,0.00000] 0.06 4.0 "L1_Facade_01" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-17.00147,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-15.50456,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-14.00766,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-12.51075,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-11.01384,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-9.51694,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-8.02003,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-6.52312,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-5.02621,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-3.52931,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-2.03240,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-0.53549,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[0.96141,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[2.45832,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[3.95523,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[5.45214,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[6.94904,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[8.44595,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[9.94286,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[11.43976,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[12.93667,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[14.43358,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[15.93048,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[17.42739,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[18.92430,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[20.42121,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[21.91811,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[23.41502,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[24.91193,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[26.40883,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[27.90574,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[29.40265,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[30.89956,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[32.39646,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[33.89337,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[35.39028,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[36.88718,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[38.38409,29.36023,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-17.00147,29.36023,0.00000] [38.38409,29.36023,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-17.00147,29.36023,4.00000] [38.38409,29.36023,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [38.38409,29.36023,0.00000] [38.38409,6.08130,0.00000] 0.2 4.0 "L1_Facade_02" "L1_Envelope" wallMat
wallSeg [38.38409,6.08130,0.00000] [35.31075,6.08130,0.00000] 0.2 4.0 "L1_Facade_03" "L1_Envelope" wallMat
wallSeg [35.31075,6.08130,0.00000] [35.31075,-9.08925,0.00000] 0.2 4.0 "L1_Facade_04" "L1_Envelope" wallMat
wallSeg [35.31075,-9.08925,0.00000] [13.07806,-9.08925,0.00000] 0.2 4.0 "L1_Facade_05" "L1_Envelope" wallMat
wallSeg [13.07806,-9.08925,0.00000] [9.80854,-6.53903,0.00000] 0.06 4.0 "L1_Facade_06" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[13.07806,-9.08925,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[11.98822,-8.23917,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[10.89838,-7.38910,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[9.80854,-6.53903,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [13.07806,-9.08925,0.00000] [9.80854,-6.53903,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [13.07806,-9.08925,4.00000] [9.80854,-6.53903,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [9.80854,-6.53903,0.00000] [9.80854,-5.23122,0.00000] 0.06 4.0 "L1_Facade_07" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[9.80854,-6.53903,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[9.80854,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [9.80854,-6.53903,0.00000] [9.80854,-5.23122,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [9.80854,-6.53903,4.00000] [9.80854,-5.23122,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [9.80854,-5.23122,0.00000] [-7.12754,-5.23122,0.00000] 0.06 4.0 "L1_Facade_08" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[9.80854,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[8.39720,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[6.98586,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[5.57452,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[4.16318,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[2.75184,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[1.34050,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-0.07084,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-1.48218,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-2.89352,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-4.30486,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-5.71620,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-7.12754,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [9.80854,-5.23122,0.00000] [-7.12754,-5.23122,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [9.80854,-5.23122,4.00000] [-7.12754,-5.23122,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-7.12754,-5.23122,0.00000] [-9.08925,-6.40825,0.00000] 0.06 4.0 "L1_Facade_09" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-7.12754,-5.23122,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-8.10839,-5.81973,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-9.08925,-6.40825,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-7.12754,-5.23122,0.00000] [-9.08925,-6.40825,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-7.12754,-5.23122,4.00000] [-9.08925,-6.40825,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-9.08925,-6.40825,0.00000] [-11.37791,-11.44330,0.00000] 0.06 4.0 "L1_Facade_10" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-9.08925,-6.40825,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-9.66141,-7.66701,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-10.23358,-8.92577,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-10.80574,-10.18454,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-11.37791,-11.44330,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-9.08925,-6.40825,0.00000] [-11.37791,-11.44330,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-9.08925,-6.40825,4.00000] [-11.37791,-11.44330,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-11.37791,-11.44330,0.00000] [-13.47040,-12.75110,0.00000] 0.06 4.0 "L1_Facade_11" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-11.37791,-11.44330,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-12.42415,-12.09720,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-13.47040,-12.75110,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-11.37791,-11.44330,0.00000] [-13.47040,-12.75110,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-11.37791,-11.44330,4.00000] [-13.47040,-12.75110,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-13.47040,-12.75110,0.00000] [-15.62828,-12.94727,0.00000] 0.06 4.0 "L1_Facade_12" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-13.47040,-12.75110,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-14.54934,-12.84919,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-15.62828,-12.94727,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-13.47040,-12.75110,0.00000] [-15.62828,-12.94727,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-13.47040,-12.75110,4.00000] [-15.62828,-12.94727,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-15.62828,-12.94727,0.00000] [-22.95199,-10.20088,0.00000] 0.06 4.0 "L1_Facade_13" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-15.62828,-12.94727,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-16.84889,-12.48954,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-18.06951,-12.03181,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-19.29013,-11.57408,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-20.51075,-11.11635,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-21.73137,-10.65861,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-22.95199,-10.20088,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-15.62828,-12.94727,0.00000] [-22.95199,-10.20088,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-15.62828,-12.94727,4.00000] [-22.95199,-10.20088,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-22.95199,-10.20088,0.00000] [-27.66009,-3.59647,0.00000] 0.06 4.0 "L1_Facade_14" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-22.95199,-10.20088,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-23.73667,-9.10015,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-24.52135,-7.99941,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-25.30604,-6.89867,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-26.09072,-5.79794,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-26.87540,-4.69720,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-27.66009,-3.59647,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-22.95199,-10.20088,0.00000] [-27.66009,-3.59647,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-22.95199,-10.20088,4.00000] [-27.66009,-3.59647,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-27.66009,-3.59647,0.00000] [-28.24860,-0.26156,0.00000] 0.06 4.0 "L1_Facade_15" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-27.66009,-3.59647,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-27.85626,-2.48483,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-28.05243,-1.37320,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-28.24860,-0.26156,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-27.66009,-3.59647,0.00000] [-28.24860,-0.26156,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-27.66009,-3.59647,4.00000] [-28.24860,-0.26156,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-28.24860,-0.26156,0.00000] [-26.15611,6.08130,0.00000] 0.06 4.0 "L1_Facade_16" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-28.24860,-0.26156,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-27.83010,1.00701,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-27.41160,2.27558,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-26.99311,3.54415,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-26.57461,4.81272,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-26.15611,6.08130,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-28.24860,-0.26156,0.00000] [-26.15611,6.08130,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-28.24860,-0.26156,4.00000] [-26.15611,6.08130,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-26.15611,6.08130,0.00000] [-25.04448,9.74315,0.00000] 0.06 4.0 "L1_Facade_17" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-26.15611,6.08130,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-25.78557,7.30191,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-25.41502,8.52253,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-25.04448,9.74315,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-26.15611,6.08130,0.00000] [-25.04448,9.74315,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-26.15611,6.08130,4.00000] [-25.04448,9.74315,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-25.04448,9.74315,0.00000] [-33.74138,13.73196,0.00000] 0.06 4.0 "L1_Facade_18" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-25.04448,9.74315,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-26.28689,10.31298,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-27.52931,10.88281,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-28.77172,11.45264,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-30.01414,12.02247,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-31.25655,12.59230,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-32.49897,13.16213,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-33.74138,13.73196,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-25.04448,9.74315,0.00000] [-33.74138,13.73196,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-25.04448,9.74315,4.00000] [-33.74138,13.73196,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-33.74138,13.73196,0.00000] [-35.50692,15.69367,0.00000] 0.06 4.0 "L1_Facade_19" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-33.74138,13.73196,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-34.62415,14.71281,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-35.50692,15.69367,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-33.74138,13.73196,0.00000] [-35.50692,15.69367,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-33.74138,13.73196,4.00000] [-35.50692,15.69367,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-35.50692,15.69367,0.00000] [-35.96465,18.89779,0.00000] 0.06 4.0 "L1_Facade_20" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-35.50692,15.69367,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-35.65950,16.76171,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-35.81207,17.82975,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-35.96465,18.89779,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-35.50692,15.69367,0.00000] [-35.96465,18.89779,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-35.50692,15.69367,4.00000] [-35.96465,18.89779,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-35.96465,18.89779,0.00000] [-34.91841,21.18645,0.00000] 0.06 4.0 "L1_Facade_21" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-35.96465,18.89779,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-35.44153,20.04212,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-34.91841,21.18645,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-35.96465,18.89779,0.00000] [-34.91841,21.18645,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-35.96465,18.89779,4.00000] [-34.91841,21.18645,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-34.91841,21.18645,0.00000] [-31.19116,19.55169,0.00000] 0.06 4.0 "L1_Facade_22" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-34.91841,21.18645,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-33.67599,20.64153,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-32.43358,20.09661,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-31.19116,19.55169,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-34.91841,21.18645,0.00000] [-31.19116,19.55169,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-34.91841,21.18645,4.00000] [-31.19116,19.55169,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-31.19116,19.55169,0.00000] [-29.88336,21.84035,0.00000] 0.06 4.0 "L1_Facade_23" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-31.19116,19.55169,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-30.53726,20.69602,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-29.88336,21.84035,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-31.19116,19.55169,0.00000] [-29.88336,21.84035,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-31.19116,19.55169,4.00000] [-29.88336,21.84035,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-29.88336,21.84035,0.00000] [-34.06833,23.08277,0.00000] 0.06 4.0 "L1_Facade_24" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-29.88336,21.84035,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-31.27835,22.25449,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-32.67334,22.66863,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-34.06833,23.08277,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-29.88336,21.84035,0.00000] [-34.06833,23.08277,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-29.88336,21.84035,4.00000] [-34.06833,23.08277,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-34.06833,23.08277,0.00000] [-28.77172,34.72224,0.00000] 0.06 4.0 "L1_Facade_25" "L1_CurtainWall_PROVISIONAL" glassMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-34.06833,23.08277,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-33.47982,24.37604,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-32.89131,25.66932,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-32.30280,26.96259,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-31.71428,28.25586,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-31.12577,29.54914,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-30.53726,30.84241,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-29.94875,32.13569,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-29.36023,33.42896,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
o=box name:"L1_Mullion" width:0.06 length:0.10 height:4.0 pos:[-28.77172,34.72224,0.00000]; assignObj o "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-34.06833,23.08277,0.00000] [-28.77172,34.72224,0.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
wallSeg [-34.06833,23.08277,4.00000] [-28.77172,34.72224,4.00000] 0.08 0.06 "L1_Transom" "L1_CurtainWall_PROVISIONAL" frameMat
o=point name:"L1_Ceiling_Datum_4m" pos:[0,0,4] size:0.5; (layerFor "00_Datums").addNode o
wallSeg [-18.57084,31.77967,5.00000] [-21.70957,25.43682,5.00000] 0.15 4.0 "L2_Partition_000_0" "L2_Partitions" wallMat
wallSeg [-21.70957,25.43682,5.00000] [-19.09396,24.19440,5.00000] 0.15 4.0 "L2_Partition_000_1" "L2_Partitions" wallMat
wallSeg [-19.09396,24.19440,5.00000] [-16.34757,30.86421,5.00000] 0.15 4.0 "L2_Partition_000_2" "L2_Partitions" wallMat
wallSeg [-19.61708,29.16406,5.00000] [-17.32842,28.11782,5.00000] 0.15 4.0 "L2_Partition_001_0" "L2_Partitions" wallMat
wallSeg [-20.59794,27.26774,5.00000] [-18.30928,26.22150,5.00000] 0.15 4.0 "L2_Partition_002_0" "L2_Partitions" wallMat
wallSeg [-14.77820,27.66009,5.00000] [-11.05096,26.15611,5.00000] 0.15 4.0 "L2_Partition_003_0" "L2_Partitions" wallMat
wallSeg [-11.05096,26.15611,5.00000] [-14.84359,18.11311,5.00000] 0.15 4.0 "L2_Partition_003_1" "L2_Partitions" wallMat
wallSeg [-14.84359,18.11311,5.00000] [-17.98233,19.48630,5.00000] 0.15 4.0 "L2_Partition_003_2" "L2_Partitions" wallMat
wallSeg [-17.98233,19.48630,5.00000] [-14.77820,27.66009,5.00000] 0.15 4.0 "L2_Partition_003_3" "L2_Partitions" wallMat
wallSeg [-16.41296,24.06362,5.00000] [-13.07806,22.49425,5.00000] 0.15 4.0 "L2_Partition_004_0" "L2_Partitions" wallMat
wallSeg [-17.32842,21.84035,5.00000] [-14.12430,20.27099,5.00000] 0.15 4.0 "L2_Partition_005_0" "L2_Partitions" wallMat
wallSeg [-21.38262,19.09396,5.00000] [-17.98233,17.65537,5.00000] 0.15 4.0 "L2_Partition_006_0" "L2_Partitions" wallMat
wallSeg [-17.98233,17.65537,5.00000] [-18.89779,15.82445,5.00000] 0.15 4.0 "L2_Partition_006_1" "L2_Partitions" wallMat
wallSeg [-18.89779,15.82445,5.00000] [-14.84359,14.05891,5.00000] 0.15 4.0 "L2_Partition_006_2" "L2_Partitions" wallMat
wallSeg [-14.84359,14.05891,5.00000] [-15.95523,11.37791,5.00000] 0.15 4.0 "L2_Partition_006_3" "L2_Partitions" wallMat
wallSeg [-15.95523,11.37791,5.00000] [-23.34433,14.64742,5.00000] 0.15 4.0 "L2_Partition_006_4" "L2_Partitions" wallMat
wallSeg [-23.34433,14.64742,5.00000] [-21.38262,19.09396,5.00000] 0.15 4.0 "L2_Partition_006_5" "L2_Partitions" wallMat
wallSeg [-21.31723,19.09396,5.00000] [-22.42886,16.54374,5.00000] 0.15 4.0 "L2_Partition_007_0" "L2_Partitions" wallMat
wallSeg [-17.98233,17.65537,5.00000] [-18.96318,15.10515,5.00000] 0.15 4.0 "L2_Partition_008_0" "L2_Partitions" wallMat
wallSeg [-11.05096,27.26774,5.00000] [-5.81973,27.26774,5.00000] 0.15 4.0 "L2_Partition_009_0" "L2_Partitions" wallMat
wallSeg [-5.81973,27.26774,5.00000] [-5.81973,24.39057,5.00000] 0.15 4.0 "L2_Partition_009_1" "L2_Partitions" wallMat
wallSeg [-5.81973,24.39057,5.00000] [-3.20412,23.27894,5.00000] 0.15 4.0 "L2_Partition_009_2" "L2_Partitions" wallMat
wallSeg [-3.20412,23.27894,5.00000] [-3.20412,21.51340,5.00000] 0.15 4.0 "L2_Partition_009_3" "L2_Partitions" wallMat
wallSeg [-3.20412,21.51340,5.00000] [-5.81973,22.62504,5.00000] 0.15 4.0 "L2_Partition_009_4" "L2_Partitions" wallMat
wallSeg [-5.81973,22.62504,5.00000] [-7.38910,19.15935,5.00000] 0.15 4.0 "L2_Partition_009_5" "L2_Partitions" wallMat
wallSeg [-7.38910,19.15935,5.00000] [-14.84359,22.42886,5.00000] 0.15 4.0 "L2_Partition_009_6" "L2_Partitions" wallMat
wallSeg [-10.72401,25.56760,5.00000] [-5.81973,23.34433,5.00000] 0.15 4.0 "L2_Partition_010_0" "L2_Partitions" wallMat
wallSeg [-12.29337,23.54050,5.00000] [-7.19293,21.31723,5.00000] 0.15 4.0 "L2_Partition_011_0" "L2_Partitions" wallMat
wallSeg [-12.94727,21.77496,5.00000] [-7.91222,19.68247,5.00000] 0.15 4.0 "L2_Partition_012_0" "L2_Partitions" wallMat
wallSeg [-14.05891,19.68247,5.00000] [-9.41620,17.65537,5.00000] 0.15 4.0 "L2_Partition_013_0" "L2_Partitions" wallMat
wallSeg [-12.42415,18.89779,5.00000] [-14.51664,14.58203,5.00000] 0.15 4.0 "L2_Partition_014_0" "L2_Partitions" wallMat
wallSeg [-10.20088,18.04772,5.00000] [-13.14345,10.65861,5.00000] 0.15 4.0 "L2_Partition_015_0" "L2_Partitions" wallMat
wallSeg [-13.14345,10.65861,5.00000] [-15.88984,11.90103,5.00000] 0.15 4.0 "L2_Partition_015_1" "L2_Partitions" wallMat
wallSeg [-10.20088,16.08601,5.00000] [-3.53107,13.47040,5.00000] 0.15 4.0 "L2_Partition_016_0" "L2_Partitions" wallMat
wallSeg [-3.53107,13.47040,5.00000] [-4.57732,10.78940,5.00000] 0.15 4.0 "L2_Partition_016_1" "L2_Partitions" wallMat
wallSeg [-4.57732,10.78940,5.00000] [-11.31252,13.53579,5.00000] 0.15 4.0 "L2_Partition_016_2" "L2_Partitions" wallMat
wallSeg [-7.65066,14.97437,5.00000] [-8.69691,12.48954,5.00000] 0.15 4.0 "L2_Partition_017_0" "L2_Partitions" wallMat
wallSeg [0.06539,30.07953,5.00000] [0.06539,22.55964,5.00000] 0.15 4.0 "L2_Partition_018_0" "L2_Partitions" wallMat
wallSeg [0.06539,22.55964,5.00000] [12.48954,22.55964,5.00000] 0.15 4.0 "L2_Partition_018_1" "L2_Partitions" wallMat
wallSeg [12.48954,22.55964,5.00000] [12.48954,25.50221,5.00000] 0.15 4.0 "L2_Partition_018_2" "L2_Partitions" wallMat
wallSeg [12.48954,25.50221,5.00000] [3.26951,25.50221,5.00000] 0.15 4.0 "L2_Partition_018_3" "L2_Partitions" wallMat
wallSeg [3.26951,25.50221,5.00000] [3.26951,30.07953,5.00000] 0.15 4.0 "L2_Partition_018_4" "L2_Partitions" wallMat
wallSeg [6.47364,30.07953,5.00000] [6.47364,28.57555,5.00000] 0.15 4.0 "L2_Partition_019_0" "L2_Partitions" wallMat
wallSeg [6.47364,28.57555,5.00000] [3.26951,28.57555,5.00000] 0.15 4.0 "L2_Partition_019_1" "L2_Partitions" wallMat
wallSeg [3.33490,25.50221,5.00000] [3.33490,22.55964,5.00000] 0.15 4.0 "L2_Partition_020_0" "L2_Partitions" wallMat
wallSeg [6.53903,25.50221,5.00000] [6.53903,22.55964,5.00000] 0.15 4.0 "L2_Partition_021_0" "L2_Partitions" wallMat
wallSeg [9.67776,25.50221,5.00000] [9.67776,21.70957,5.00000] 0.15 4.0 "L2_Partition_022_0" "L2_Partitions" wallMat
wallSeg [9.67776,21.70957,5.00000] [12.48954,21.70957,5.00000] 0.15 4.0 "L2_Partition_022_1" "L2_Partitions" wallMat
wallSeg [14.77820,30.07953,5.00000] [14.77820,26.09072,5.00000] 0.15 4.0 "L2_Partition_023_0" "L2_Partitions" wallMat
wallSeg [14.77820,26.09072,5.00000] [20.14020,26.09072,5.00000] 0.15 4.0 "L2_Partition_023_1" "L2_Partitions" wallMat
wallSeg [20.14020,26.09072,5.00000] [20.14020,30.07953,5.00000] 0.15 4.0 "L2_Partition_023_2" "L2_Partitions" wallMat
wallSeg [14.77820,26.09072,5.00000] [14.77820,23.21355,5.00000] 0.15 4.0 "L2_Partition_024_0" "L2_Partitions" wallMat
wallSeg [14.77820,23.21355,5.00000] [19.48630,23.21355,5.00000] 0.15 4.0 "L2_Partition_024_1" "L2_Partitions" wallMat
wallSeg [19.48630,23.21355,5.00000] [19.48630,26.09072,5.00000] 0.15 4.0 "L2_Partition_024_2" "L2_Partitions" wallMat
wallSeg [14.77820,23.08277,5.00000] [20.14020,23.08277,5.00000] 0.15 4.0 "L2_Partition_025_0" "L2_Partitions" wallMat
wallSeg [20.14020,23.08277,5.00000] [20.14020,19.29013,5.00000] 0.15 4.0 "L2_Partition_025_1" "L2_Partitions" wallMat
wallSeg [20.14020,19.29013,5.00000] [14.77820,19.29013,5.00000] 0.15 4.0 "L2_Partition_025_2" "L2_Partitions" wallMat
wallSeg [14.77820,19.29013,5.00000] [14.77820,23.08277,5.00000] 0.15 4.0 "L2_Partition_025_3" "L2_Partitions" wallMat
wallSeg [17.45920,23.08277,5.00000] [17.45920,19.29013,5.00000] 0.15 4.0 "L2_Partition_026_0" "L2_Partitions" wallMat
wallSeg [22.95199,30.07953,5.00000] [22.95199,26.54845,5.00000] 0.15 4.0 "L2_Partition_027_0" "L2_Partitions" wallMat
wallSeg [22.95199,26.54845,5.00000] [29.42562,26.54845,5.00000] 0.15 4.0 "L2_Partition_027_1" "L2_Partitions" wallMat
wallSeg [29.42562,26.54845,5.00000] [29.42562,30.07953,5.00000] 0.15 4.0 "L2_Partition_027_2" "L2_Partitions" wallMat
wallSeg [26.41767,30.07953,5.00000] [26.41767,26.54845,5.00000] 0.15 4.0 "L2_Partition_028_0" "L2_Partitions" wallMat
wallSeg [33.21826,30.07953,5.00000] [33.21826,21.77496,5.00000] 0.15 4.0 "L2_Partition_029_0" "L2_Partitions" wallMat
wallSeg [33.21826,21.77496,5.00000] [38.38409,21.77496,5.00000] 0.15 4.0 "L2_Partition_029_1" "L2_Partitions" wallMat
wallSeg [22.69043,24.25979,5.00000] [29.42562,24.25979,5.00000] 0.15 4.0 "L2_Partition_030_0" "L2_Partitions" wallMat
wallSeg [29.42562,24.25979,5.00000] [29.42562,20.92489,5.00000] 0.15 4.0 "L2_Partition_030_1" "L2_Partitions" wallMat
wallSeg [29.42562,20.92489,5.00000] [22.69043,20.92489,5.00000] 0.15 4.0 "L2_Partition_030_2" "L2_Partitions" wallMat
wallSeg [22.69043,20.92489,5.00000] [22.69043,24.25979,5.00000] 0.15 4.0 "L2_Partition_030_3" "L2_Partitions" wallMat
wallSeg [24.97909,24.25979,5.00000] [24.97909,20.92489,5.00000] 0.15 4.0 "L2_Partition_031_0" "L2_Partitions" wallMat
wallSeg [27.13696,24.25979,5.00000] [27.13696,20.92489,5.00000] 0.15 4.0 "L2_Partition_032_0" "L2_Partitions" wallMat
wallSeg [29.42562,24.25979,5.00000] [33.21826,24.25979,5.00000] 0.15 4.0 "L2_Partition_033_0" "L2_Partitions" wallMat
wallSeg [25.37143,20.92489,5.00000] [29.42562,20.92489,5.00000] 0.15 4.0 "L2_Partition_034_0" "L2_Partitions" wallMat
wallSeg [29.42562,20.92489,5.00000] [29.42562,14.97437,5.00000] 0.15 4.0 "L2_Partition_034_1" "L2_Partitions" wallMat
wallSeg [29.42562,14.97437,5.00000] [25.37143,14.97437,5.00000] 0.15 4.0 "L2_Partition_034_2" "L2_Partitions" wallMat
wallSeg [25.37143,14.97437,5.00000] [25.37143,20.92489,5.00000] 0.15 4.0 "L2_Partition_034_3" "L2_Partitions" wallMat
wallSeg [25.37143,17.91694,5.00000] [29.42562,17.91694,5.00000] 0.15 4.0 "L2_Partition_035_0" "L2_Partitions" wallMat
wallSeg [29.42562,19.48630,5.00000] [33.21826,19.48630,5.00000] 0.15 4.0 "L2_Partition_036_0" "L2_Partitions" wallMat
wallSeg [33.21826,19.48630,5.00000] [33.21826,16.15140,5.00000] 0.15 4.0 "L2_Partition_036_1" "L2_Partitions" wallMat
wallSeg [33.21826,16.15140,5.00000] [29.42562,16.15140,5.00000] 0.15 4.0 "L2_Partition_036_2" "L2_Partitions" wallMat
wallSeg [33.21826,21.77496,5.00000] [33.21826,19.61708,5.00000] 0.15 4.0 "L2_Partition_037_0" "L2_Partitions" wallMat
wallSeg [33.21826,19.61708,5.00000] [38.38409,19.61708,5.00000] 0.15 4.0 "L2_Partition_037_1" "L2_Partitions" wallMat
wallSeg [35.63770,19.61708,5.00000] [35.63770,15.82445,5.00000] 0.15 4.0 "L2_Partition_038_0" "L2_Partitions" wallMat
wallSeg [35.63770,15.82445,5.00000] [38.38409,15.82445,5.00000] 0.15 4.0 "L2_Partition_038_1" "L2_Partitions" wallMat
wallSeg [33.21826,15.82445,5.00000] [33.21826,12.94727,5.00000] 0.15 4.0 "L2_Partition_039_0" "L2_Partitions" wallMat
wallSeg [33.21826,12.94727,5.00000] [38.38409,12.94727,5.00000] 0.15 4.0 "L2_Partition_039_1" "L2_Partitions" wallMat
wallSeg [31.25655,16.15140,5.00000] [33.21826,16.15140,5.00000] 0.15 4.0 "L2_Partition_040_0" "L2_Partitions" wallMat
wallSeg [33.21826,16.15140,5.00000] [33.21826,12.94727,5.00000] 0.15 4.0 "L2_Partition_040_1" "L2_Partitions" wallMat
wallSeg [33.21826,12.94727,5.00000] [31.25655,12.94727,5.00000] 0.15 4.0 "L2_Partition_040_2" "L2_Partitions" wallMat
wallSeg [31.25655,12.94727,5.00000] [31.25655,16.15140,5.00000] 0.15 4.0 "L2_Partition_040_3" "L2_Partitions" wallMat
wallSeg [25.37143,14.97437,5.00000] [29.42562,14.97437,5.00000] 0.15 4.0 "L2_Partition_041_0" "L2_Partitions" wallMat
wallSeg [29.42562,14.97437,5.00000] [29.42562,12.88188,5.00000] 0.15 4.0 "L2_Partition_041_1" "L2_Partitions" wallMat
wallSeg [29.42562,12.88188,5.00000] [25.37143,12.88188,5.00000] 0.15 4.0 "L2_Partition_041_2" "L2_Partitions" wallMat
wallSeg [25.37143,12.88188,5.00000] [28.77172,12.88188,5.00000] 0.15 4.0 "L2_Partition_042_0" "L2_Partitions" wallMat
wallSeg [28.77172,12.88188,5.00000] [28.77172,9.15464,5.00000] 0.15 4.0 "L2_Partition_042_1" "L2_Partitions" wallMat
wallSeg [28.77172,9.15464,5.00000] [25.37143,9.15464,5.00000] 0.15 4.0 "L2_Partition_042_2" "L2_Partitions" wallMat
wallSeg [25.37143,9.15464,5.00000] [28.77172,9.15464,5.00000] 0.15 4.0 "L2_Partition_043_0" "L2_Partitions" wallMat
wallSeg [28.77172,9.15464,5.00000] [28.77172,5.10044,5.00000] 0.15 4.0 "L2_Partition_043_1" "L2_Partitions" wallMat
wallSeg [28.77172,5.10044,5.00000] [25.37143,5.10044,5.00000] 0.15 4.0 "L2_Partition_043_2" "L2_Partitions" wallMat
wallSeg [25.37143,5.10044,5.00000] [33.21826,5.10044,5.00000] 0.15 4.0 "L2_Partition_044_0" "L2_Partitions" wallMat
wallSeg [33.21826,5.10044,5.00000] [33.21826,1.37320,5.00000] 0.15 4.0 "L2_Partition_044_1" "L2_Partitions" wallMat
wallSeg [33.21826,12.94727,5.00000] [33.21826,5.10044,5.00000] 0.15 4.0 "L2_Partition_045_0" "L2_Partitions" wallMat
wallSeg [33.21826,5.10044,5.00000] [38.38409,5.10044,5.00000] 0.15 4.0 "L2_Partition_045_1" "L2_Partitions" wallMat
wallSeg [35.63770,12.94727,5.00000] [35.63770,5.10044,5.00000] 0.15 4.0 "L2_Partition_046_0" "L2_Partitions" wallMat
wallSeg [12.29337,17.06686,5.00000] [17.45920,17.06686,5.00000] 0.15 4.0 "L2_Partition_047_0" "L2_Partitions" wallMat
wallSeg [17.45920,17.06686,5.00000] [17.45920,13.66657,5.00000] 0.15 4.0 "L2_Partition_047_1" "L2_Partitions" wallMat
wallSeg [17.45920,13.66657,5.00000] [12.29337,13.66657,5.00000] 0.15 4.0 "L2_Partition_047_2" "L2_Partitions" wallMat
wallSeg [14.71281,17.06686,5.00000] [14.71281,13.66657,5.00000] 0.15 4.0 "L2_Partition_048_0" "L2_Partitions" wallMat
wallSeg [17.45920,17.06686,5.00000] [20.14020,17.06686,5.00000] 0.15 4.0 "L2_Partition_049_0" "L2_Partitions" wallMat
wallSeg [20.14020,17.06686,5.00000] [20.14020,13.79735,5.00000] 0.15 4.0 "L2_Partition_049_1" "L2_Partitions" wallMat
wallSeg [20.14020,13.79735,5.00000] [17.45920,13.79735,5.00000] 0.15 4.0 "L2_Partition_049_2" "L2_Partitions" wallMat
wallSeg [14.71281,13.66657,5.00000] [20.14020,13.66657,5.00000] 0.15 4.0 "L2_Partition_050_0" "L2_Partitions" wallMat
wallSeg [20.14020,13.66657,5.00000] [20.14020,11.05096,5.00000] 0.15 4.0 "L2_Partition_050_1" "L2_Partitions" wallMat
wallSeg [20.14020,11.05096,5.00000] [14.71281,11.05096,5.00000] 0.15 4.0 "L2_Partition_050_2" "L2_Partitions" wallMat
wallSeg [14.71281,11.05096,5.00000] [14.71281,13.66657,5.00000] 0.15 4.0 "L2_Partition_050_3" "L2_Partitions" wallMat
wallSeg [12.29337,13.66657,5.00000] [12.29337,2.35405,5.00000] 0.15 4.0 "L2_Partition_051_0" "L2_Partitions" wallMat
wallSeg [12.29337,2.35405,5.00000] [13.07806,1.43859,5.00000] 0.15 4.0 "L2_Partition_051_1" "L2_Partitions" wallMat
wallSeg [13.07806,1.43859,5.00000] [22.69043,1.43859,5.00000] 0.15 4.0 "L2_Partition_051_2" "L2_Partitions" wallMat
wallSeg [22.69043,1.43859,5.00000] [22.69043,17.06686,5.00000] 0.15 4.0 "L2_Partition_051_3" "L2_Partitions" wallMat
wallSeg [12.29337,9.93932,5.00000] [16.15140,9.93932,5.00000] 0.15 4.0 "L2_Partition_052_0" "L2_Partitions" wallMat
wallSeg [16.15140,9.93932,5.00000] [16.15140,5.68895,5.00000] 0.15 4.0 "L2_Partition_052_1" "L2_Partitions" wallMat
wallSeg [16.15140,5.68895,5.00000] [12.29337,5.68895,5.00000] 0.15 4.0 "L2_Partition_052_2" "L2_Partitions" wallMat
wallSeg [16.15140,9.93932,5.00000] [20.14020,9.93932,5.00000] 0.15 4.0 "L2_Partition_053_0" "L2_Partitions" wallMat
wallSeg [20.14020,9.93932,5.00000] [20.14020,5.68895,5.00000] 0.15 4.0 "L2_Partition_053_1" "L2_Partitions" wallMat
wallSeg [20.14020,5.68895,5.00000] [16.15140,5.68895,5.00000] 0.15 4.0 "L2_Partition_053_2" "L2_Partitions" wallMat
wallSeg [17.45920,11.05096,5.00000] [17.45920,9.93932,5.00000] 0.15 4.0 "L2_Partition_054_0" "L2_Partitions" wallMat
wallSeg [22.69043,20.92489,5.00000] [22.69043,13.79735,5.00000] 0.15 4.0 "L2_Partition_055_0" "L2_Partitions" wallMat
wallSeg [22.69043,13.79735,5.00000] [25.37143,13.79735,5.00000] 0.15 4.0 "L2_Partition_055_1" "L2_Partitions" wallMat
wallSeg [-37.99175,8.30456,5.00000] [-34.26450,8.30456,5.00000] 0.15 4.0 "L2_Partition_056_0" "L2_Partitions" wallMat
wallSeg [-34.26450,8.30456,5.00000] [-34.26450,3.40029,5.00000] 0.15 4.0 "L2_Partition_056_1" "L2_Partitions" wallMat
wallSeg [-34.26450,3.40029,5.00000] [-37.92636,3.40029,5.00000] 0.15 4.0 "L2_Partition_056_2" "L2_Partitions" wallMat
wallSeg [-37.99175,5.95052,5.00000] [-34.26450,5.95052,5.00000] 0.15 4.0 "L2_Partition_057_0" "L2_Partitions" wallMat
wallSeg [-32.30280,6.21208,5.00000] [-28.44477,6.21208,5.00000] 0.15 4.0 "L2_Partition_058_0" "L2_Partitions" wallMat
wallSeg [-28.44477,6.21208,5.00000] [-28.44477,3.26951,5.00000] 0.15 4.0 "L2_Partition_058_1" "L2_Partitions" wallMat
wallSeg [-28.44477,3.26951,5.00000] [-32.30280,3.26951,5.00000] 0.15 4.0 "L2_Partition_058_2" "L2_Partitions" wallMat
wallSeg [-32.30280,3.26951,5.00000] [-32.30280,6.21208,5.00000] 0.15 4.0 "L2_Partition_058_3" "L2_Partitions" wallMat
wallSeg [-28.44477,6.21208,5.00000] [-25.43682,5.10044,5.00000] 0.15 4.0 "L2_Partition_059_0" "L2_Partitions" wallMat
wallSeg [-25.43682,5.10044,5.00000] [-26.94079,1.76554,5.00000] 0.15 4.0 "L2_Partition_059_1" "L2_Partitions" wallMat
wallSeg [-26.94079,1.76554,5.00000] [-29.81797,2.94256,5.00000] 0.15 4.0 "L2_Partition_059_2" "L2_Partitions" wallMat
wallSeg [-35.37614,3.40029,5.00000] [-34.26450,3.40029,5.00000] 0.15 4.0 "L2_Partition_060_0" "L2_Partitions" wallMat
wallSeg [-34.26450,3.40029,5.00000] [-33.15287,2.94256,5.00000] 0.15 4.0 "L2_Partition_060_1" "L2_Partitions" wallMat
wallSeg [-33.15287,2.94256,5.00000] [-35.37614,-1.83093,5.00000] 0.15 4.0 "L2_Partition_060_2" "L2_Partitions" wallMat
wallSeg [-33.15287,2.94256,5.00000] [-30.47187,1.70015,5.00000] 0.15 4.0 "L2_Partition_061_0" "L2_Partitions" wallMat
wallSeg [-30.47187,1.70015,5.00000] [-32.69514,-3.13873,5.00000] 0.15 4.0 "L2_Partition_061_1" "L2_Partitions" wallMat
wallSeg [-30.47187,1.70015,5.00000] [-27.92165,0.58851,5.00000] 0.15 4.0 "L2_Partition_062_0" "L2_Partitions" wallMat
wallSeg [-27.92165,0.58851,5.00000] [-30.14492,-4.25037,5.00000] 0.15 4.0 "L2_Partition_062_1" "L2_Partitions" wallMat
wallSeg [-27.92165,0.58851,5.00000] [-25.37143,-0.58851,5.00000] 0.15 4.0 "L2_Partition_063_0" "L2_Partitions" wallMat
wallSeg [-25.37143,-0.58851,5.00000] [-27.59470,-5.36200,5.00000] 0.15 4.0 "L2_Partition_063_1" "L2_Partitions" wallMat
wallSeg [-35.37614,-1.83093,5.00000] [-25.43682,-6.27747,5.00000] 0.15 4.0 "L2_Partition_064_0" "L2_Partitions" wallMat
wallSeg [-34.13372,-2.41944,5.00000] [-35.37614,-4.25037,5.00000] 0.15 4.0 "L2_Partition_065_0" "L2_Partitions" wallMat
wallSeg [-31.51811,-3.59647,5.00000] [-32.69514,-5.36200,5.00000] 0.15 4.0 "L2_Partition_066_0" "L2_Partitions" wallMat
wallSeg [-28.90250,-4.77349,5.00000] [-30.21031,-6.47364,5.00000] 0.15 4.0 "L2_Partition_067_0" "L2_Partitions" wallMat
wallSeg [-25.43682,5.10044,5.00000] [-22.82121,3.85803,5.00000] 0.15 4.0 "L2_Partition_068_0" "L2_Partitions" wallMat
wallSeg [-22.82121,3.85803,5.00000] [-24.52135,0.19617,5.00000] 0.15 4.0 "L2_Partition_068_1" "L2_Partitions" wallMat
wallSeg [-24.52135,0.19617,5.00000] [-27.07157,1.37320,5.00000] 0.15 4.0 "L2_Partition_068_2" "L2_Partitions" wallMat
wallSeg [-25.43682,-6.27747,5.00000] [-23.34433,-1.70015,5.00000] 0.15 4.0 "L2_Partition_069_0" "L2_Partitions" wallMat
wallSeg [-23.34433,-1.70015,5.00000] [-21.90574,-2.35405,5.00000] 0.15 4.0 "L2_Partition_069_1" "L2_Partitions" wallMat
wallSeg [-21.90574,-2.35405,5.00000] [-22.69043,-4.25037,5.00000] 0.15 4.0 "L2_Partition_069_2" "L2_Partitions" wallMat
wallSeg [-22.69043,-4.25037,5.00000] [-20.14020,-5.42739,5.00000] 0.15 4.0 "L2_Partition_069_3" "L2_Partitions" wallMat
wallSeg [-20.14020,-5.42739,5.00000] [-21.57879,-8.56613,5.00000] 0.15 4.0 "L2_Partition_069_4" "L2_Partitions" wallMat
wallSeg [-24.19440,-5.95052,5.00000] [-21.51340,-7.12754,5.00000] 0.15 4.0 "L2_Partition_070_0" "L2_Partitions" wallMat
wallSeg [-17.78615,2.22327,5.00000] [-14.97437,1.04624,5.00000] 0.15 4.0 "L2_Partition_071_0" "L2_Partitions" wallMat
wallSeg [-14.97437,1.04624,5.00000] [-16.08601,-1.56937,5.00000] 0.15 4.0 "L2_Partition_071_1" "L2_Partitions" wallMat
wallSeg [-16.08601,-1.56937,5.00000] [-18.37467,-0.52312,5.00000] 0.15 4.0 "L2_Partition_071_2" "L2_Partitions" wallMat
wallSeg [-18.37467,-0.52312,5.00000] [-17.78615,2.22327,5.00000] 0.15 4.0 "L2_Partition_071_3" "L2_Partitions" wallMat
wallSeg [-14.97437,1.04624,5.00000] [-11.90103,-0.26156,5.00000] 0.15 4.0 "L2_Partition_072_0" "L2_Partitions" wallMat
wallSeg [-11.90103,-0.26156,5.00000] [-13.86274,-4.70810,5.00000] 0.15 4.0 "L2_Partition_072_1" "L2_Partitions" wallMat
wallSeg [-17.13225,-8.30456,5.00000] [-14.25508,-9.61237,5.00000] 0.15 4.0 "L2_Partition_073_0" "L2_Partitions" wallMat
wallSeg [-14.25508,-9.61237,5.00000] [-15.82445,-13.27423,5.00000] 0.15 4.0 "L2_Partition_073_1" "L2_Partitions" wallMat
wallSeg [-5.88512,-2.41944,5.00000] [14.84359,-2.41944,5.00000] 0.15 4.0 "L2_Partition_074_0" "L2_Partitions" wallMat
wallSeg [-5.88512,-2.41944,5.00000] [-8.30456,-15.17054,5.00000] 0.15 4.0 "L2_Partition_075_0" "L2_Partitions" wallMat
wallSeg [-6.53903,-8.76230,5.00000] [-3.26951,-8.76230,5.00000] 0.15 4.0 "L2_Partition_076_0" "L2_Partitions" wallMat
wallSeg [-3.26951,-8.76230,5.00000] [-3.26951,-12.68571,5.00000] 0.15 4.0 "L2_Partition_076_1" "L2_Partitions" wallMat
wallSeg [-3.26951,-12.68571,5.00000] [-7.45449,-12.68571,5.00000] 0.15 4.0 "L2_Partition_076_2" "L2_Partitions" wallMat
wallSeg [-7.45449,-12.68571,5.00000] [-3.33490,-12.68571,5.00000] 0.15 4.0 "L2_Partition_077_0" "L2_Partitions" wallMat
wallSeg [-3.33490,-12.68571,5.00000] [-3.33490,-15.17054,5.00000] 0.15 4.0 "L2_Partition_077_1" "L2_Partitions" wallMat
wallSeg [-3.46568,-7.58527,5.00000] [-0.32695,-7.58527,5.00000] 0.15 4.0 "L2_Partition_078_0" "L2_Partitions" wallMat
wallSeg [-0.32695,-7.58527,5.00000] [-0.32695,-15.17054,5.00000] 0.15 4.0 "L2_Partition_078_1" "L2_Partitions" wallMat
wallSeg [-0.32695,-7.58527,5.00000] [6.86598,-7.58527,5.00000] 0.15 4.0 "L2_Partition_079_0" "L2_Partitions" wallMat
wallSeg [6.86598,-7.58527,5.00000] [6.86598,-9.80854,5.00000] 0.15 4.0 "L2_Partition_079_1" "L2_Partitions" wallMat
wallSeg [6.86598,-9.80854,5.00000] [-0.32695,-9.80854,5.00000] 0.15 4.0 "L2_Partition_079_2" "L2_Partitions" wallMat
wallSeg [-1.11163,-9.80854,5.00000] [-1.11163,-15.17054,5.00000] 0.15 4.0 "L2_Partition_080_0" "L2_Partitions" wallMat
wallSeg [3.20412,-9.80854,5.00000] [3.20412,-15.17054,5.00000] 0.15 4.0 "L2_Partition_081_0" "L2_Partitions" wallMat
wallSeg [-1.11163,-12.55493,5.00000] [6.86598,-12.55493,5.00000] 0.15 4.0 "L2_Partition_082_0" "L2_Partitions" wallMat
wallSeg [9.02386,-6.01591,5.00000] [12.09720,-6.01591,5.00000] 0.15 4.0 "L2_Partition_083_0" "L2_Partitions" wallMat
wallSeg [12.09720,-6.01591,5.00000] [12.09720,-15.17054,5.00000] 0.15 4.0 "L2_Partition_083_1" "L2_Partitions" wallMat
wallSeg [9.02386,-9.74315,5.00000] [12.09720,-9.74315,5.00000] 0.15 4.0 "L2_Partition_084_0" "L2_Partitions" wallMat
wallSeg [9.02386,-11.96642,5.00000] [12.09720,-11.96642,5.00000] 0.15 4.0 "L2_Partition_085_0" "L2_Partitions" wallMat
wallSeg [14.84359,-2.41944,5.00000] [14.84359,-7.51988,5.00000] 0.15 4.0 "L2_Partition_086_0" "L2_Partitions" wallMat
wallSeg [14.84359,-7.51988,5.00000] [12.09720,-7.51988,5.00000] 0.15 4.0 "L2_Partition_086_1" "L2_Partitions" wallMat
wallSeg [16.93608,-7.51988,5.00000] [16.93608,-9.80854,5.00000] 0.15 4.0 "L2_Partition_087_0" "L2_Partitions" wallMat
wallSeg [16.93608,-9.80854,5.00000] [12.09720,-9.80854,5.00000] 0.15 4.0 "L2_Partition_087_1" "L2_Partitions" wallMat
wallSeg [14.51664,-7.51988,5.00000] [14.51664,-9.80854,5.00000] 0.15 4.0 "L2_Partition_088_0" "L2_Partitions" wallMat
wallSeg [12.09720,-12.09720,5.00000] [22.88660,-12.09720,5.00000] 0.15 4.0 "L2_Partition_089_0" "L2_Partitions" wallMat
wallSeg [22.88660,-12.09720,5.00000] [22.88660,-15.17054,5.00000] 0.15 4.0 "L2_Partition_089_1" "L2_Partitions" wallMat
wallSeg [14.71281,-12.09720,5.00000] [14.71281,-15.17054,5.00000] 0.15 4.0 "L2_Partition_090_0" "L2_Partitions" wallMat
wallSeg [17.45920,-12.09720,5.00000] [17.45920,-15.17054,5.00000] 0.15 4.0 "L2_Partition_091_0" "L2_Partitions" wallMat
wallSeg [20.14020,-12.09720,5.00000] [20.14020,-15.17054,5.00000] 0.15 4.0 "L2_Partition_092_0" "L2_Partitions" wallMat
wallSeg [22.88660,-12.09720,5.00000] [26.41767,-12.09720,5.00000] 0.15 4.0 "L2_Partition_093_0" "L2_Partitions" wallMat
wallSeg [26.41767,-12.09720,5.00000] [26.41767,-15.17054,5.00000] 0.15 4.0 "L2_Partition_093_1" "L2_Partitions" wallMat
wallSeg [20.53255,-2.41944,5.00000] [20.53255,-5.16583,5.00000] 0.15 4.0 "L2_Partition_094_0" "L2_Partitions" wallMat
wallSeg [20.53255,-5.16583,5.00000] [27.00618,-5.16583,5.00000] 0.15 4.0 "L2_Partition_094_1" "L2_Partitions" wallMat
wallSeg [27.00618,-5.16583,5.00000] [27.00618,-2.41944,5.00000] 0.15 4.0 "L2_Partition_094_2" "L2_Partitions" wallMat
wallSeg [23.27894,-2.41944,5.00000] [23.27894,-5.16583,5.00000] 0.15 4.0 "L2_Partition_095_0" "L2_Partitions" wallMat
wallSeg [22.69043,-7.51988,5.00000] [27.66009,-7.51988,5.00000] 0.15 4.0 "L2_Partition_096_0" "L2_Partitions" wallMat
wallSeg [27.66009,-7.51988,5.00000] [27.66009,-9.80854,5.00000] 0.15 4.0 "L2_Partition_096_1" "L2_Partitions" wallMat
wallSeg [27.66009,-9.80854,5.00000] [22.69043,-9.80854,5.00000] 0.15 4.0 "L2_Partition_096_2" "L2_Partitions" wallMat
wallSeg [22.69043,-9.80854,5.00000] [22.69043,-7.51988,5.00000] 0.15 4.0 "L2_Partition_096_3" "L2_Partitions" wallMat
wallSeg [31.06038,-1.30781,5.00000] [35.31075,-1.30781,5.00000] 0.15 4.0 "L2_Partition_097_0" "L2_Partitions" wallMat
wallSeg [31.06038,-1.30781,5.00000] [31.06038,-3.33490,5.00000] 0.15 4.0 "L2_Partition_098_0" "L2_Partitions" wallMat
wallSeg [31.06038,-3.33490,5.00000] [35.31075,-3.33490,5.00000] 0.15 4.0 "L2_Partition_098_1" "L2_Partitions" wallMat
wallSeg [31.06038,-5.49278,5.00000] [35.31075,-5.49278,5.00000] 0.15 4.0 "L2_Partition_099_0" "L2_Partitions" wallMat
wallSeg [31.06038,-7.51988,5.00000] [35.31075,-7.51988,5.00000] 0.15 4.0 "L2_Partition_100_0" "L2_Partitions" wallMat
wallSeg [31.06038,-9.74315,5.00000] [35.31075,-9.74315,5.00000] 0.15 4.0 "L2_Partition_101_0" "L2_Partitions" wallMat
wallSeg [28.57555,-2.41944,5.00000] [28.57555,-5.55817,5.00000] 0.15 4.0 "L2_Partition_102_0" "L2_Partitions" wallMat
wallSeg [0.00000,22.42886,5.00000] [0.00000,14.84359,5.00000] 0.15 4.0 "L2_Partition_103_0" "L2_Partitions" wallMat
wallSeg [0.00000,14.84359,5.00000] [4.31576,14.84359,5.00000] 0.15 4.0 "L2_Partition_103_1" "L2_Partitions" wallMat
wallSeg [4.31576,14.84359,5.00000] [4.31576,22.42886,5.00000] 0.15 4.0 "L2_Partition_103_2" "L2_Partitions" wallMat
wallSeg [4.31576,22.42886,5.00000] [0.00000,22.42886,5.00000] 0.15 4.0 "L2_Partition_103_3" "L2_Partitions" wallMat
wallSeg [4.31576,22.42886,5.00000] [9.80854,22.42886,5.00000] 0.15 4.0 "L2_Partition_104_0" "L2_Partitions" wallMat
wallSeg [9.80854,22.42886,5.00000] [9.80854,14.84359,5.00000] 0.15 4.0 "L2_Partition_104_1" "L2_Partitions" wallMat
wallSeg [9.80854,14.84359,5.00000] [4.31576,14.84359,5.00000] 0.15 4.0 "L2_Partition_104_2" "L2_Partitions" wallMat
wallSeg [7.06215,22.42886,5.00000] [7.06215,14.84359,5.00000] 0.15 4.0 "L2_Partition_105_0" "L2_Partitions" wallMat
wallSeg [7.06215,19.55169,5.00000] [9.80854,19.55169,5.00000] 0.15 4.0 "L2_Partition_106_0" "L2_Partitions" wallMat
wallSeg [7.06215,17.19764,5.00000] [9.80854,17.19764,5.00000] 0.15 4.0 "L2_Partition_107_0" "L2_Partitions" wallMat
wallSeg [1.83093,14.84359,5.00000] [9.80854,14.84359,5.00000] 0.15 4.0 "L2_Partition_108_0" "L2_Partitions" wallMat
wallSeg [9.80854,14.84359,5.00000] [9.80854,7.06215,5.00000] 0.15 4.0 "L2_Partition_108_1" "L2_Partitions" wallMat
wallSeg [9.80854,7.06215,5.00000] [1.83093,7.06215,5.00000] 0.15 4.0 "L2_Partition_108_2" "L2_Partitions" wallMat
wallSeg [1.83093,7.06215,5.00000] [1.83093,14.84359,5.00000] 0.15 4.0 "L2_Partition_108_3" "L2_Partitions" wallMat
wallSeg [4.31576,14.84359,5.00000] [4.31576,7.06215,5.00000] 0.15 4.0 "L2_Partition_109_0" "L2_Partitions" wallMat
wallSeg [7.06215,14.84359,5.00000] [7.06215,11.57408,5.00000] 0.15 4.0 "L2_Partition_110_0" "L2_Partitions" wallMat
wallSeg [7.06215,11.57408,5.00000] [9.80854,11.57408,5.00000] 0.15 4.0 "L2_Partition_110_1" "L2_Partitions" wallMat
wallSeg [1.83093,12.03181,5.00000] [4.31576,12.03181,5.00000] 0.15 4.0 "L2_Partition_111_0" "L2_Partitions" wallMat
wallSeg [1.83093,9.61237,5.00000] [4.31576,9.61237,5.00000] 0.15 4.0 "L2_Partition_112_0" "L2_Partitions" wallMat
wallSeg [-23.93284,34.19911,5.00000] [-14.77820,30.07953,5.00000] 0.2 4.0 "L2_Facade_00" "L2_Envelope" wallMat
wallSeg [-14.77820,30.07953,5.00000] [38.38409,30.07953,5.00000] 0.2 4.0 "L2_Facade_01" "L2_Envelope" wallMat
wallSeg [38.38409,30.07953,5.00000] [38.38409,-2.15788,5.00000] 0.2 4.0 "L2_Facade_02" "L2_Envelope" wallMat
wallSeg [38.38409,-2.15788,5.00000] [35.31075,-2.15788,5.00000] 0.2 4.0 "L2_Facade_03" "L2_Envelope" wallMat
wallSeg [35.31075,-2.15788,5.00000] [35.31075,-13.14345,5.00000] 0.2 4.0 "L2_Facade_04" "L2_Envelope" wallMat
wallSeg [35.31075,-13.14345,5.00000] [34.65685,-14.51664,5.00000] 0.2 4.0 "L2_Facade_05" "L2_Envelope" wallMat
wallSeg [34.65685,-14.51664,5.00000] [33.34904,-15.17054,5.00000] 0.2 4.0 "L2_Facade_06" "L2_Envelope" wallMat
wallSeg [33.34904,-15.17054,5.00000] [-8.23917,-15.17054,5.00000] 0.2 4.0 "L2_Facade_07" "L2_Envelope" wallMat
wallSeg [-8.23917,-15.17054,5.00000] [-36.29160,-3.79264,5.00000] 0.2 4.0 "L2_Facade_08" "L2_Envelope" wallMat
wallSeg [-36.29160,-3.79264,5.00000] [-37.53402,-2.55022,5.00000] 0.06 4.0 "L2_Facade_09" "L2_CurtainWall_PROVISIONAL" glassMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-36.29160,-3.79264,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-36.91281,-3.17143,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-37.53402,-2.55022,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-36.29160,-3.79264,5.00000] [-37.53402,-2.55022,5.00000] 0.08 0.06 "L2_Transom" "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-36.29160,-3.79264,9.00000] [-37.53402,-2.55022,9.00000] 0.08 0.06 "L2_Transom" "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-37.53402,-2.55022,5.00000] [-38.05714,-0.65390,5.00000] 0.06 4.0 "L2_Facade_10" "L2_CurtainWall_PROVISIONAL" glassMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-37.53402,-2.55022,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-37.79558,-1.60206,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-38.05714,-0.65390,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-37.53402,-2.55022,5.00000] [-38.05714,-0.65390,5.00000] 0.08 0.06 "L2_Transom" "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-37.53402,-2.55022,9.00000] [-38.05714,-0.65390,9.00000] 0.08 0.06 "L2_Transom" "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-38.05714,-0.65390,5.00000] [-38.05714,8.30456,5.00000] 0.06 4.0 "L2_Facade_11" "L2_CurtainWall_PROVISIONAL" glassMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-38.05714,-0.65390,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-38.05714,0.83918,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-38.05714,2.33225,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-38.05714,3.82533,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-38.05714,5.31841,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-38.05714,6.81149,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-38.05714,8.30456,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-38.05714,-0.65390,5.00000] [-38.05714,8.30456,5.00000] 0.08 0.06 "L2_Transom" "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-38.05714,-0.65390,9.00000] [-38.05714,8.30456,9.00000] 0.08 0.06 "L2_Transom" "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-38.05714,8.30456,5.00000] [-37.40324,11.57408,5.00000] 0.06 4.0 "L2_Facade_12" "L2_CurtainWall_PROVISIONAL" glassMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-38.05714,8.30456,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-37.83917,9.39440,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-37.62121,10.48424,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-37.40324,11.57408,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-38.05714,8.30456,5.00000] [-37.40324,11.57408,5.00000] 0.08 0.06 "L2_Transom" "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-38.05714,8.30456,9.00000] [-37.40324,11.57408,9.00000] 0.08 0.06 "L2_Transom" "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-37.40324,11.57408,5.00000] [-34.98380,14.25508,5.00000] 0.06 4.0 "L2_Facade_13" "L2_CurtainWall_PROVISIONAL" glassMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-37.40324,11.57408,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-36.59676,12.46775,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-35.79028,13.36141,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-34.98380,14.25508,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-37.40324,11.57408,5.00000] [-34.98380,14.25508,5.00000] 0.08 0.06 "L2_Transom" "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-37.40324,11.57408,9.00000] [-34.98380,14.25508,9.00000] 0.08 0.06 "L2_Transom" "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-34.98380,14.25508,5.00000] [-33.02209,14.25508,5.00000] 0.06 4.0 "L2_Facade_14" "L2_CurtainWall_PROVISIONAL" glassMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-34.98380,14.25508,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-34.00294,14.25508,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-33.02209,14.25508,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-34.98380,14.25508,5.00000] [-33.02209,14.25508,5.00000] 0.08 0.06 "L2_Transom" "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-34.98380,14.25508,9.00000] [-33.02209,14.25508,9.00000] 0.08 0.06 "L2_Transom" "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-33.02209,14.25508,5.00000] [-23.93284,34.19911,5.00000] 0.06 4.0 "L2_Facade_15" "L2_CurtainWall_PROVISIONAL" glassMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-33.02209,14.25508,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-32.41614,15.58468,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-31.81019,16.91428,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-31.20424,18.24389,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-30.59829,19.57349,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-29.99234,20.90309,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-29.38639,22.23269,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-28.78044,23.56230,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-28.17449,24.89190,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-27.56854,26.22150,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-26.96259,27.55110,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-26.35664,28.88070,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-25.75069,30.21031,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-25.14474,31.53991,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-24.53879,32.86951,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
o=box name:"L2_Mullion" width:0.06 length:0.10 height:4.0 pos:[-23.93284,34.19911,5.00000]; assignObj o "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-33.02209,14.25508,5.00000] [-23.93284,34.19911,5.00000] 0.08 0.06 "L2_Transom" "L2_CurtainWall_PROVISIONAL" frameMat
wallSeg [-33.02209,14.25508,9.00000] [-23.93284,34.19911,9.00000] 0.08 0.06 "L2_Transom" "L2_CurtainWall_PROVISIONAL" frameMat
o=point name:"L2_Ceiling_Datum_9.0m" pos:[0,0,9.0] size:0.5; (layerFor "00_Datums").addNode o
wallSeg [-11.77025,13.66657,5.00000] [-4.83888,10.65861,5.00000] 0.04 1.1 "Void_1_Guard_PROVISIONAL" "L2_Void_Guards" glassMat
wallSeg [-4.83888,10.65861,5.00000] [-7.78144,3.00795,5.00000] 0.04 1.1 "Void_1_Guard_PROVISIONAL" "L2_Void_Guards" glassMat
wallSeg [-7.78144,3.00795,5.00000] [-8.76230,2.09249,5.00000] 0.04 1.1 "Void_1_Guard_PROVISIONAL" "L2_Void_Guards" glassMat
wallSeg [-8.76230,2.09249,5.00000] [-17.13225,5.49278,5.00000] 0.04 1.1 "Void_1_Guard_PROVISIONAL" "L2_Void_Guards" glassMat
wallSeg [-17.13225,5.49278,5.00000] [-11.77025,13.66657,5.00000] 0.04 1.1 "Void_1_Guard_PROVISIONAL" "L2_Void_Guards" glassMat
wallSeg [0.98085,7.06215,5.00000] [9.61237,7.06215,5.00000] 0.04 1.1 "Void_2_Guard_PROVISIONAL" "L2_Void_Guards" glassMat
wallSeg [9.61237,7.06215,5.00000] [9.61237,1.70015,5.00000] 0.04 1.1 "Void_2_Guard_PROVISIONAL" "L2_Void_Guards" glassMat
wallSeg [9.61237,1.70015,5.00000] [8.89308,0.85007,5.00000] 0.04 1.1 "Void_2_Guard_PROVISIONAL" "L2_Void_Guards" glassMat
wallSeg [8.89308,0.85007,5.00000] [0.00000,0.85007,5.00000] 0.04 1.1 "Void_2_Guard_PROVISIONAL" "L2_Void_Guards" glassMat
wallSeg [0.00000,0.85007,5.00000] [-1.30781,1.43859,5.00000] 0.04 1.1 "Void_2_Guard_PROVISIONAL" "L2_Void_Guards" glassMat
wallSeg [-1.30781,1.43859,5.00000] [-2.02710,2.68100,5.00000] 0.04 1.1 "Void_2_Guard_PROVISIONAL" "L2_Void_Guards" glassMat
wallSeg [-2.02710,2.68100,5.00000] [-1.76554,4.25037,5.00000] 0.04 1.1 "Void_2_Guard_PROVISIONAL" "L2_Void_Guards" glassMat
wallSeg [-1.76554,4.25037,5.00000] [-0.52312,6.34286,5.00000] 0.04 1.1 "Void_2_Guard_PROVISIONAL" "L2_Void_Guards" glassMat
wallSeg [-0.52312,6.34286,5.00000] [0.98085,7.06215,5.00000] 0.04 1.1 "Void_2_Guard_PROVISIONAL" "L2_Void_Guards" glassMat
modelInfo = point name:"SRISAWAN_MODEL_INFORMATION" size:0.5
(layerFor "00_Datums").addNode modelInfo
setUserProp modelInfo "Model_Status" "SCHEMATIC raster trace; not construction accurate"
setUserProp modelInfo "Scale" "Approximate GFA calibration: 0.065390 metres/image unit"
setUserProp modelInfo "Levels" "L1=0; L1 ceiling=4; L2=5.0 per user; L2 ceiling=9.0 per user"
setUserProp modelInfo "Scope" "No furniture. Doors and detailed small wet-room cubicles not resolved. Facade allocation provisional."
viewport.setType #view_iso_user
viewport.setTM (matrix3 [0.707,-0.707,0] [0.408,0.408,0.816] [-0.577,-0.577,0.577] [0,0,0])
max tool zoomextents all

redrawViews()
format "Srisawan shell generated. Objects: %. Save As to keep the .max scene.\n" objects.count
