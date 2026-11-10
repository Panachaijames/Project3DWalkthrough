"""Labeller A (geometry first): write ../A.json, the list of door, window and passage openings of
presidential suite_layout.dwg (cache suite_revit), in the format of keys/tower/labels/l29-E-A.json.

Every a / b below was read from the wall fills of prims.pkl (exact vertex values printed by the helper scripts in this
folder: fills.py, endscan.py, arcs.py, bays.py, linepairs.py); the curtain-wall facets are computed here from the
A-GLAZ-CURT pane blocks. Coordinates are drawing metres (DXF mm / 1000)."""
import json, math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import load

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'A.json')
FLOOR = 'suite_revit'
ops = []


def add(kind, subtype, a, b, t, host, evidence, confidence, notes, optional=False):
    o = {'id': f'A-{len(ops) + 1:02d}', 'floor': FLOOR, 'kind': kind, 'subtype': subtype,
         'a': [round(a[0], 4), round(a[1], 4)], 'b': [round(b[0], 4), round(b[1], 4)],
         'width': round(math.dist(a, b), 3), 'wallThickness': t, 'host': host,
         'evidence': evidence, 'confidence': confidence}
    if optional: o['optional'] = True
    o['notes'] = notes
    ops.append(o)


# ---------------------------------------------------------------- scored: doors of the suite
add('door', 'pocket (cavity) sliding door, leaf 1.00 m',
    (7.4539, 2.2341), (7.4539, 3.3341), 0.2, 'wall',
    "Partition x 7.354-7.554 (layer-0 fill 51B7 ends at y 2.2341, fill 51AF starts at y 3.3341). Leaf A-DOOR 5577/5579 "
    "(x 7.434/7.474, 40 mm) 1.00 m long at y 3.224-4.224, inside the pocket slot of 51AF (x 7.419-7.489, y 3.334-4.267); "
    "slide arrow A-DOOR 5575 at x 7.324, y 2.484->3.084 (points north, into the pocket), drawn in the master bedroom; "
    "frames A-DOOR-FRAM 557D/557E/557F (y 2.234-2.284) and 557A/557B/557C/5580/5581/5582 (y 3.284-3.334, split round the slot); "
    "the two core lines x 7.379 / 7.529 (layer 0) run on across the gap.",
    'high', 'Master bedroom <-> dressing area / bedroom foyer. a/b = wall-fill end faces, frames included '
    '(clear between the frames 1.00 = the leaf).')

add('door', 'pocket (cavity) sliding door, leaf 1.00 m',
    (7.4539, 10.2841), (7.4539, 11.3841), 0.2, 'wall',
    "Partition x 7.354-7.554: fill 51AF ends at y 10.2841; the north end is the facade lining (layer-0 fill 4DE4, y 11.3841-11.4091) "
    "in front of the A-WALL facade (53F6/53F7). Leaf A-DOOR 5587/5589 (x 7.434/7.474) 1.00 m at y 9.394-10.394 in the pocket slot "
    "(x 7.419-7.489, y 9.334-10.284); slide arrow A-DOOR 5585 at x 7.324, y 11.134->10.534 (points south, into the pocket); "
    "frames A-DOOR-FRAM 558A/558B/558C/5590/5591/5592 (y 10.284-10.334) and 558D/558E/558F (y 11.334-11.384, against the facade); "
    "core lines 4EBA/4EE6 run on across the gap.",
    'high', 'Master bedroom <-> master bathroom (bath area of bay N2), at the facade corner. a/b = fill end to the facade lining face, '
    'frames included (clear 1.00).')

add('door', 'bi-fold door, 4 panels (drawn folded)',
    (9.4616, 0.9591), (9.4616, 3.1841), 0.15, 'wall',
    "Wall x 9.387-9.537 (core fill 4DBA x 9.412-9.512 + linings 4DCB/4DD2) ends at y 0.9591 (cap lining 4DD0); the north end is the "
    "south face (lining 4DD1, y 3.1841) of the wardrobe's north wall 4DCA (y 3.209-3.309). 8 A-DOOR panel lines of 0.564 m "
    "(59E9..59F7) folded as a zigzag x 9.387-9.944, y 2.456-3.232 against the north end; dashed layer-0 track 4FC9 along x 9.4616 "
    "from y 0.9591 to 3.1841 (exactly the gap). No frames.",
    'high', 'Dressing area <-> walk-in wardrobe (x 9.54-11.49, y 0.33-3.18, hanging rails). Counted as a room door (the wardrobe is '
    'walk-in, 1.95 x 2.85 m), not a cupboard door; see uncertain.')

add('door', 'pocket (cavity) sliding door, leaf 1.00 m',
    (8.1289, 5.1557), (9.2289, 5.1557), 0.19, 'wall',
    "Wall y 5.0607-5.2507 (layer-0 fill 51B2: piece x 7.554-8.1289, piece x 9.2289-11.487 with the pocket slot y 5.126-5.196 "
    "to x 10.667). Leaf A-DOOR 5597/5599 (y 5.141/5.181) 1.00 m at x 9.119-10.119 in the pocket; slide arrow A-DOOR 5595 at "
    "y 5.291, x 8.379->8.979 (points east), drawn on the bathroom side; frames A-DOOR-FRAM 559D/559E/559F (x 8.129-8.179) and "
    "559A/559B/559C/55A0/55A1/55A2 (x 9.179-9.229, split round the slot).",
    'high', 'Bedroom foyer <-> master bathroom (vanity side). a/b = fill end faces, frames included (clear 1.00).')

add('door', 'hinged single, leaf 0.90 m',
    (11.5616, 3.6974), (11.5616, 4.698), 0.15, 'wall',
    "Partition x 11.487-11.637: fill 51C0 ends at y 3.6974, fill 51B3 starts at y 4.698. Dashed swing A-DOOR A7CA r 0.90 about "
    "the hinge (11.507, 3.747), 90.5 deg; leaf A-DOOR A7C8/A7C9 (0.90 x 0.04) open west along y 3.747-3.787 into the bedroom foyer; "
    "frames A-DOOR-FRAM A7C0/A7C1/A7C2 (y 3.697-3.747) and A7C3/A7C4/A7C5 (y 4.647-4.697).",
    'high', 'Foyer <-> bedroom foyer. a/b = fill end faces, frames included (clear 0.90).')

add('door', 'hinged single, leaf 0.70 m',
    (11.7116, 3.2591), (12.4616, 3.2591), 0.1, 'wall',
    "Wall y 3.2091-3.3091 (layer-0 fill 4DB8: piece x 11.612-11.7116, piece x 12.4616-13.2866; linings 4DED/4DEE on the foyer "
    "side). Dashed swing A-DOOR 5552 r 0.70 about the hinge (11.712, 3.229), 90.5 deg; leaf A-DOOR 5550/5551 (x 11.712-11.752, "
    "y 2.529-3.194) open south into the small room; frame A-DOOR-FRAM 554B/554C at the west wall end, 554A/5549 0.05 inside the east end "
    "(x 12.412-12.462); threshold line 4F03 (y 3.309, x 11.762-12.462). The room's 15 mm tile lining 4DBC (y 3.194-3.209) is drawn "
    "on across the gap.",
    'high', 'Foyer <-> small room south of the foyer (x 11.64-13.12, y 1.22-3.19; toilet-roll holder: probably a powder room). '
    'a/b = fill end faces (0.75); the leaf closes 11.712-12.412 (0.70).')

add('door', 'hinged double, 2 leaves of 0.865 m (suite entrance)',
    (13.2866, 3.2591), (15.0866, 3.2591), 0.125, 'wall',
    "Corridor north wall y 3.2091-3.3091 (layer-0 fill 4DB8 ends at x 13.2866 and restarts at x 15.0866). Two dashed swings "
    "A-DOOR 552D / 5544, r 0.865 about the hinges (13.322, 3.309) and (15.052, 3.309); leaves 5530/5531 and 5547/5548 open north "
    "into the foyer; rebated frames A-DOOR-FRAM 5532..553A (x 13.287-13.337) and 553B..5543 (x 15.037-15.087); threshold 4F05 "
    "(y 3.309, x 13.322-15.052).",
    'high', 'Corridor <-> foyer: the suite entrance. a/b = fill end faces, frames included (leaves 2 x 0.865 = 1.73, clear 1.70).')

add('passage', 'doorless opening with a drawn head (dashed face lines across)',
    (13.1366, 5.1357), (15.1116, 5.1357), 0.15, 'wall',
    "Wall y 5.0607-5.2107 (layer-0 fill 51B6: piece x 11.637-13.1366 and the L-shaped piece x 15.1116-15.662 / y 3.759-5.211). "
    "The fill stops and the two face lines go on across the gap dashed (5F8F y 5.2107, 5F91 y 5.0607, '- DASH SMALL', "
    "x 13.1366-15.1116): head over the opening. No leaf, arc or frame.",
    'high', 'Foyer <-> living & dining area. Two wall ends in line (both pieces are on the same wall line), so a real passage, '
    'not a mouth into open space.')

add('door', 'hinged single, leaf 0.70 m',
    (20.7116, 3.3591), (21.5116, 3.3591), 0.125, 'wall',
    "Corridor north wall y 3.3091-3.4091 (layer-0 fill 4DF8: piece x 20.587-20.7116, piece x 21.5116-23.987; lining 4E02 on the "
    "BOH side). Dashed swing A-DOOR 580D r 0.70 about the hinge (20.762, 3.389); leaf 580B/580C open north into the BOH (room name 'BOH.'); "
    "frames A-DOOR-FRAM 5806/5807/5808 (x 20.712-20.762) and 5803/5804/5805 (x 21.462-21.512); threshold 4FA3 (y 3.409).",
    'high', 'Corridor <-> BOH. (service pantry). a/b = fill end faces, frames included (clear 0.70).')

add('door', 'hinged single, leaf 0.70 m',
    (20.5116, 4.4091), (20.5116, 5.2091), 0.175, 'wall',
    "Wall x 20.437-20.612 (layer-0 fill 51BE ends at y 4.4091, fill 51BC starts at y 5.2091). Dashed swing A-DOOR 57E2 r 0.70 "
    "about the hinge (20.567, 5.159); leaf 57E0/57E1 open east along y 5.119-5.159 into the BOH; frames A-DOOR-FRAM 57D8/57D9/57DA "
    "(y 4.409-4.459) and 57DB/57DC/57DD (y 5.159-5.209); the two core lines (x 20.437 / 20.587, 4F07 / 4FA2) run on across the gap.",
    'high', 'Bar <-> BOH. a/b = fill end faces, frames included (clear 0.70).')

add('door', 'pocket (cavity) sliding door, leaf 1.00 m',
    (20.5116, 6.0841), (20.5116, 7.1841), 0.2, 'wall',
    "Wall x 20.412-20.612 (layer-0 fill 51BC ends at y 6.0841; fill 51B9 starts at y 7.1841 with its pocket slot x 20.477-20.547 "
    "up to y 8.072). Leaf A-DOOR 627D/627F (x 20.492/20.532) 1.00 m at y 7.074-8.074 in the pocket; slide arrow A-DOOR 627B at "
    "x 20.382, y 6.334->6.934 (points north), drawn on the dining side; frames A-DOOR-FRAM 6283/6284/6285 (y 6.084-6.134) and "
    "6280/6281/6282/6286/6287/6288 (y 7.134-7.184, split round the slot); core lines 4F08/4FA4 across the gap.",
    'high', 'Living & dining area <-> lobby of bedroom 2. a/b = fill end faces, frames included (clear 1.00).')

add('door', 'hinged single, leaf 0.70 m',
    (22.8116, 6.0341), (22.8116, 6.8341), 0.175, 'wall',
    "Wall x 22.712-22.887: fill 51FA ends at y 6.0341; the north end is the end piece 51FD (y 6.8341-6.8541) of the room's north "
    "wall 51FC (y 6.854-6.994). Dashed swing A-DOOR A9CC r 0.70 about the hinge (22.867, 6.784); leaf A9CA/A9CB open east along "
    "y 6.744-6.784 into the room; frames A-DOOR-FRAM A9C2/A9C3/A9C4 (y 6.034-6.084) and A9C5/A9C6/A9C7 (y 6.784-6.834).",
    'high', 'Lobby of bedroom 2 <-> unlabelled room x 22.89-24.79, y 3.42-6.85 (probably bedroom 2\'s bathroom). '
    'a/b = wall end faces, frames included (clear 0.70).')

# ---------------------------------------------------------------- scored: doors in the corridor outside the suite
add('door', 'hinged double, 2 leaves of 0.865 m (SERVICE_SWING_DOUBLE - D22 1800X2100MM), riser door',
    (15.2366, 3.2591), (17.0366, 3.2591), 0.1, 'wall',
    "A-DOOR block 'SERVICE_SWING_DOUBLE - D22 1800X2100MM-V24' (insert 5529 at (16.137, 3.259), rot 180): leaves 0.865 hinged at "
    "(15.272, 3.209) and (17.002, 3.209), drawn open 35 deg into the corridor (dashed arcs r 0.865); three A-DOOR-FRAM lines across "
    "the whole opening (y 3.209 / 3.249 / 3.309). Wall ends: layer-0 fill 4DB8 (x 15.087-15.2366, y 3.209-3.309) with A-WALL jamb 540C "
    "(x 15.137-15.2366), and A-WALL 540D (x 17.0366-17.137, y 3.209-3.659). Behind: riser x 15.237-17.037, y 3.309-3.659 with the "
    "dashed A-DETL X.",
    'high', 'Corridor (outside the suite) <-> 0.35 m service riser. Scored as a door, like the shaft and riser doors of the tower key; '
    'see uncertain (outside the suite).')

add('door', 'hinged single, leaf 0.78 m (SERVICE_DOOR_SWING_1_SOLID - 850X2400MM_D06), riser door',
    (16.1866, 1.1591), (17.0366, 1.1591), 0.1, 'wall',
    "A-DOOR block 'SERVICE_DOOR_SWING_1_SOLID - 850X2400MM_D06' (insert 552B at (16.612, 1.159), rot 0): leaf 0.78 hinged at "
    "(17.002, 1.209), drawn open 35 deg north into the corridor (dashed arc r 0.78); frame lines across y 1.109 / 1.169 / 1.209. "
    "Corridor south wall y 1.109-1.209: A-WALL fill 5421 ends at x 16.1866 and restarts at x 17.0366. Behind: riser "
    "x 16.187-17.037, y 0.759-1.109 (A-WALL 5412/5411) with a layer-0 X (54AF/54B0).",
    'high', 'Corridor (outside the suite) <-> service riser.')

add('door', 'hinged single, leaf 0.93 m (UNIT_DOOR_SWING_1_SOLID - D01_1000X2250MM)',
    (19.1766, 0.8591), (20.1766, 0.8591), 0.1, 'wall',
    "A-DOOR block 'UNIT_DOOR_SWING_1_SOLID - D01_1000X2250MM-3324155' (insert 5527 at (19.677, 0.859), rot 0): dashed arc r 0.93 "
    "about the hinge (20.142, 0.809), leaf 0.04 thick going south, both cut by the view crop at y 0.009; rebated frames x 19.177-19.227 "
    "and 20.127-20.177. A-WALL wall y 0.809-0.909: fill 5422 ends at x 19.1766 and restarts at x 20.1766; its two face lines "
    "(54BD/54C0) run on across the opening.",
    'high', 'Door of a neighbouring unit (its room is not drawn), at the back of the corridor alcove x 19.087-20.262 west of the column. '
    'The opening itself is whole inside the drawing; see uncertain.')

add('door', 'hinged single, leaf 0.93 m (UNIT_DOOR_SWING_1_SOLID - D01_1000X2250MM)',
    (20.8466, 0.8591), (21.8466, 0.8591), 0.1, 'wall',
    "A-DOOR block 'UNIT_DOOR_SWING_1_SOLID - D01_1000X2250MM-3324157' (insert 5526 at (21.347, 0.859), rot 180): dashed arc r 0.93 "
    "about the hinge (20.882, 0.809), leaf going south, cut by the crop at y 0.009; frames x 20.847-20.897 and 21.797-21.847. "
    "A-WALL wall y 0.809-0.909: fill 5423 ends at x 20.8466 and restarts at x 21.8466; face lines 54C9/54CC run on across.",
    'high', 'Door of the other neighbouring unit, in the alcove east of the column. See uncertain.')

# ---------------------------------------------------------------- optional
add('door', 'hinged double (SERVICE_SWING_DOUBLE - D22 1800X2100MM), riser door CUT BY THE VIEW CROP',
    (23.9866, 3.2591), (25.7866, 3.2591), 0.1, 'wall',
    "A-DOOR block 'SERVICE_SWING_DOUBLE - D22 1800X2100MM-2804302' (insert 5528 at (24.887, 3.259), rot 180): hinges at x 24.022 and "
    "25.752 (the second beyond the crop x 25.079), leaves open 35 deg into the corridor; frame lines y 3.209-3.309 from x 23.987 to the "
    "crop. West end: layer-0 wall 4DF8 (y 3.309-3.409) ends at x 23.9866, riser wall 4DF9 (x 23.887-23.987). Riser x 23.987-25.079, "
    "y 3.309-3.659 with the A-DETL X 5426/5427.",
    'medium', 'OPTIONAL: the east jamb lies outside the drawing (crop at x 25.079): only 1.092 m of the opening is drawn. '
    'a/b = the nominal 1.80 m from the type name and the hinges (centre = insert point). The frame stands 0.10 m proud of the wall line '
    'into the corridor (wall y 3.309-3.409, frame y 3.209-3.309); a/b are on the frame line.', optional=True)

add('door', 'hinged double (SERVICE_SWING_DOUBLE - D22 1800X2100MM), riser door CUT BY THE VIEW CROP',
    (23.9866, 1.1591), (25.7866, 1.1591), 0.1, 'wall',
    "A-DOOR block 'SERVICE_SWING_DOUBLE - D22 1800X2100MM-V25' (insert 552A at (24.887, 1.159), rot 0): hinges at x 24.022 and 25.752, "
    "leaves open 35 deg north into the corridor; frame lines y 1.109 / 1.169 / 1.209 from x 23.987 to the crop. West end: A-WALL 5414 "
    "(y 1.109-1.209) ends at x 23.9866. Riser x 23.987-25.079, y 0.759-1.109 with the A-DETL X 5428/5429.",
    'medium', 'OPTIONAL: cut by the view crop like the one above (only 1.092 m drawn); nominal 1.80 m used.', optional=True)

add('door', 'glass hinged door 0.70 m in a glass screen (IN_SHOWER DOOR1 shower-door family), WC compartment',
    (9.5166, 5.3507), (9.5166, 6.0507), 0.01, 'glass',
    "Master-bathroom screen x 9.467-9.567: 10 mm glass on layer 0 (lines x 9.5116 / 9.5216) stops at y 5.3507 (A7B5/A7B7, fixed glass "
    "y 5.251-5.351) and restarts at y 6.0507 (4FA8/4FA9, fixed glass to y 6.950); leaf A-DOOR 5A8D/5A8F (0.70, 10 mm) drawn open 30 deg "
    "to the west; dashed 30 deg swing A-DOOR-HDLN 5A91 r 0.70 about the hinge (9.512, 5.351); handle outline on A-GENM-HDLN. The screen's "
    "two 0.10 m layer-0 lines (4EE8 x 9.4666, 4EE5 x 9.5666) run on past the door.",
    'high', 'OPTIONAL: door of the WC compartment (x 9.57-11.49, y 5.25-6.95) in the bathroom glass screen; treated like the toilet '
    'cubicle doors of the earlier keys (not scored either way). Measured by its leaf; the fixed glass beside it is glass wall.',
    optional=True)

add('door', 'glass hinged door 0.70 m in a shower screen (IN_SHOWER DOOR1)',
    (9.5166, 7.1655), (9.5166, 7.8654), 0.01, 'glass',
    "Same screen: glass stops at y 7.1655 (A8E6/A8E8, fixed y 7.066-7.166) and restarts at y 7.8654 (4FB0/4FB1, fixed to y 9.434); "
    "leaf A-DOOR A8E0/A8E2 open 30 deg west; dashed swing A-DOOR-HDLN A8E4 r 0.70 about (9.512, 7.165).",
    'high', 'OPTIONAL: south door of the shower (x 9.57-11.49, y 7.05-10.23). The conventions do not list shower screens; the door is '
    'nonetheless a drawn hinged leaf in a full-height glass partition, so it is listed as not scored either way.', optional=True)

add('door', 'glass hinged door 0.70 m in a shower screen (IN_SHOWER DOOR1)',
    (9.5166, 9.4341), (9.5166, 10.1341), 0.01, 'glass',
    "Same screen: glass stops at y 9.4341 (4FB0/4FB1) and restarts at y 10.1341 (4FAD/4FAF, fixed y 10.134-10.239, up to the 10 mm "
    "glass fill 4DEB along y 10.229-10.239 that closes the shower on the north); leaf A-DOOR 5B15/5B17 open 30 deg west; dashed swing "
    "A-DOOR-HDLN 5B19 r 0.70 about (9.512, 10.134).",
    'high', 'OPTIONAL: north door of the same shower (the shower has two doors in its west screen). Same reason as the one above.',
    optional=True)

add('door', 'glass hinged door 0.70 m in a glass (shower) screen (IN_SHOWER DOOR1)',
    (23.0016, 4.775), (23.7016, 4.775), 0.01, 'glass',
    "Screen y 4.724-4.824 (layer-0 lines 4F81 / 4F80) across the unlabelled room x 22.89-24.79: 10 mm glass (y 4.770 / 4.780) "
    "A622/A624 x 22.902-23.002 and 4F85/4F87 x 23.702-24.797; leaf A-DOOR 58B1/58B3 (0.70) open 30 deg north; dashed swing "
    "A-DOOR-HDLN 58B5 r 0.70 about the hinge (23.002, 4.780).",
    'high', 'OPTIONAL: probably a shower door (the part south of the screen, 1.9 x 1.3 m, holds only a 0.97 x 0.35 m box; no fixtures '
    'are drawn in the room). Same reason as the master-bathroom screen doors.', optional=True)

add('passage', 'open side of the dressing area (no wall, nothing drawn)',
    (7.5539, 3.2591), (9.3866, 3.2591), 0.15, 'wall',
    "The walk-in wardrobe's north wall (layer-0 fill 4DCA y 3.209-3.309 with linings 4DD1/4DCC, overall y 3.184-3.334) ends at "
    "x 9.3866; across 1.83 m to the west is the partition x 7.354-7.554, whose fill 51AF starts at y 3.334 (the line y 3.259 itself "
    "runs into the pocket-door gap A-01). Nothing is drawn across (no head, threshold or frame).",
    'low', 'OPTIONAL: passage mouth into open space. The dressing area (x 7.55-9.39, y 0.33-3.18) is an open nook of the bedroom foyer: '
    'one wall end facing the corner of a perpendicular wall, not two wall ends in line.', optional=True)

add('passage', 'open side of the lobby of bedroom 2 (no wall, nothing drawn)',
    (20.6116, 6.9941), (22.7366, 6.9941), 0.14, 'wall',
    "The north wall of the room east of the lobby (layer-0 fill 51FC y 6.854-6.994 + end piece 51FD) ends at x 22.7366; across "
    "2.13 m to the west is the partition x 20.41-20.61, whose fill 51B9 starts at y 7.184 (the wall line y 6.92 runs into the "
    "pocket-door gap A-11). Nothing is drawn across.",
    'low', 'OPTIONAL: passage mouth into open space; the lobby (x 20.61-22.71, y 6.03-6.99, in front of the wardrobe) is part of '
    'bedroom 2\'s open floor. Listed only so that a detection here is not scored either way.', optional=True)

# ---------------------------------------------------------------- optional: curtain-wall facets (fixed glazing)
D = load()
panes = {}
for d in D['items']:
    if d['lay'] == 'A-GLAZ-CURT' and d['t'] == 'LINE':
        panes.setdefault(d['h'], []).append(d['pts'])
fac = []
for h, L in panes.items():
    longs = sorted([p for p in L if math.dist(p[0], p[-1]) > 0.05], key=lambda p: -math.dist(p[0], p[-1]))
    p, q = longs[0], longs[1]
    if math.dist(p[0], q[0]) > math.dist(p[0], q[-1]): q = q[::-1]
    c0 = ((p[0][0] + q[0][0]) / 2, (p[0][1] + q[0][1]) / 2); c1 = ((p[-1][0] + q[-1][0]) / 2, (p[-1][1] + q[-1][1]) / 2)
    if (c0[0], c0[1]) > (c1[0], c1[1]): c0, c1 = c1, c0
    fac.append((h, c0, c1))
BAYS = [('W', 'west bay (master bedroom)', 1.0, 3.0), ('N1', 'north bay 1 (master bedroom)', 3.0, 6.5),
        ('N2', 'north bay 2 (master bathroom, bath)', 7.5, 11.0), ('N3', 'north bay 3 (living)', 12.0, 15.5),
        ('N4', 'north bay 4 (dining)', 16.5, 19.5), ('N5', 'north bay 5 (bedroom 2)', 21.0, 24.0)]
for tag, name, x0, x1 in BAYS:
    mine = [f for f in fac if x0 <= (f[1][0] + f[2][0]) / 2 <= x1 and (tag == 'W') == ((f[1][0] + f[2][0]) / 2 < 3.0)]
    mine.sort(key=lambda f: ((f[1][1] + f[2][1]) / 2) if tag == 'W' else ((f[1][0] + f[2][0]) / 2))
    for k, (h, c0, c1) in enumerate(mine):
        L = math.dist(c0, c1); u = ((c1[0] - c0[0]) / L, (c1[1] - c0[1]) / L)
        a = (c0[0] - 0.05 * u[0], c0[1] - 0.05 * u[1]); b = (c1[0] + 0.05 * u[0], c1[1] + 0.05 * u[1])
        ang = math.degrees(math.atan2(u[1], u[0])) % 180
        add('window', f'fixed curtain-wall glazing, facet {k + 1} of 3 of the {name}',
            a, b, 0.1, 'curtain wall',
            f"A-GLAZ-CURT pane insert {h} ('System Panel - GLAZED'): glass centre line {c0[0]:.4f},{c0[1]:.4f} -> {c1[0]:.4f},{c1[1]:.4f} "
            f"({L:.3f} m, {ang:.0f} deg); A-GLAZ-CWMG mullion lines 0.10 m apart along it and 50 x 100 mullion boxes / Walls 13 "
            f"wedges at its ends; a/b = pane ends +0.05 m (the mullion / joint at each end).",
            'medium', 'OPTIONAL: fixed curtain-wall pane of a projecting glazed bay; no opening sash is drawn. Curtain-wall glazing is not a '
            'window under the conventions (the tower key listed its curtain wall as glass wall), but the bank key kept fixed curtain-wall '
            'glazing between solid walls as optional windows, so it is listed here, not scored either way. One entry per straight facet; '
            'see uncertain for the one-per-bay alternative.', optional=True)

glass_walls = [
    {'a': [9.5166, 5.2507], 'b': [9.5166, 10.2391], 'notes': 'Master-bathroom glass screen (10 mm glass on layer 0, between two continuous 0.10 m '
     'layer-0 lines x 9.4666 / 9.5666 read as a kerb or channel). Fixed glass 0.10 + door A-19 + 0.90 (to the WC/shower wall y 6.95-7.05) | '
     '0.10 + door A-20 + 1.569 + door A-21 + 0.105.'},
    {'a': [9.5116, 10.234], 'b': [11.4966, 10.234], 'notes': 'Shower north glass: 10 mm layer-0 fill 4DEB (y 10.229-10.239) with lines 4EEB/4EEC; '
     'separates the shower from the bath area. No door.'},
    {'a': [22.9016, 4.775], 'b': [24.7966, 4.775], 'notes': 'Glass screen across the room east of the BOH (glass y 4.770-4.780 between 0.10 m '
     'lines y 4.724 / 4.824): fixed 0.10 + door A-22 + 1.095.'},
    {'a': [1.61, 2.86], 'b': [1.61, 8.86], 'notes': 'West bay of the master bedroom: three curtain-wall facets (A-25..A-27), between the west wall '
     'pieces A-WALL 541E/541D (ends y 2.86-2.93) and 541C/541F (y 8.79-8.86). a/b here only mark the bay\'s extent.'},
    {'a': [3.8, 11.46], 'b': [23.64, 12.82], 'notes': 'Five north bays (A-28..A-42), each three curtain-wall facets (0.707 / 1.417 / 0.707 m panes at '
     '75 / 30 / 165 deg) from the end of a 0.10 m straight facade wall to the top of a 1.7-1.8 m solid angled facade wall; a/b here only mark '
     'the extent of the row.'},
]

uncertain = [
    {'where': [20.0, 0.86], 'what': 'Doors outside the suite (A-13 to A-16 scored; A-17, A-18 optional): the corridor, its four service risers and '
     'the two neighbouring units\' doors (D01) are drawn and are real door openings, so they are listed and scored like the tower\'s shaft and '
     'riser doors. If the key is meant to cover the suite only, A-13 to A-16 should become optional.'},
    {'where': [24.53, 2.2], 'what': 'A-17 / A-18: the riser double doors at the east edge are cut by the view crop (x 25.079); only 1.092 m of each '
     '1.80 m opening is drawn. Listed optional with the nominal 1.80 m (centre at the block insert point); the drawn part would be '
     'x 23.987-25.079.'},
    {'where': [9.52, 7.7], 'what': 'Glass doors in the bathroom glass screens (A-19 WC compartment, A-20 / A-21 shower, A-22 probably shower): drawn '
     'as hinged 0.70 m glass leaves (family IN_SHOWER DOOR1 - Shower door_700X2160MM), each with fixed glass beside it. The conventions exclude '
     'shower screens, and a WC compartment door is like a toilet cubicle door, so all four are optional; if the key wants doors in glass '
     'partitions scored regardless of the room, they are doors measured by the leaf (0.70).'},
    {'where': [9.46, 2.07], 'what': 'A-03 bi-fold door: scored as the door of a walk-in wardrobe (a room 1.95 x 2.85 m one walks into, behind a 2.225 m '
     'gap in a 0.15 m partition). If walk-in wardrobes count as casework, it would be optional. The width is the full wall gap (the dashed '
     'track 4FC9 spans exactly the same 2.225 m).'},
    {'where': [5.0, 12.4], 'what': 'Curtain-wall bays (A-25 to A-42, all optional windows): listed one entry per straight facet (pane plus its end '
     'mullions). The alternative is one entry per bay (west bay: y 2.86-8.86 on the line x 2.81; north bays: from the end of the straight '
     'facade wall, e.g. (3.85, 11.46), to the top of the solid angled wall, e.g. (6.13, 12.82)). No sash or opening light is drawn in any bay.'},
    {'where': [7.45, 2.78], 'what': 'Pocket doors A-01, A-02, A-04, A-11 measured between the wall-fill ends (1.10 m), the frames (50 mm each side) '
     'included, as the tower and bank keys measured hinged doors; the clear width between the frames is 1.00 m (= the leaf). Hinged doors '
     'likewise: A-05 1.00 (clear 0.90), A-09 / A-10 / A-12 0.80 (clear 0.70), A-06 0.75 (leaf 0.70, frame inside the east end only).'},
    {'where': [20.08, 1.06], 'what': 'Corridor alcove x 19.087-21.937, y 0.909-1.209 in front of the two D01 doors, split by the column x 20.262-20.762: '
     'its two mouths in the corridor wall line (x 19.087-20.262 and 20.762-21.937, 1.175 m each, 0.30 m deep) are read as the door recesses of '
     'A-15 / A-16, not as separate openings (listed under rejected).'},
]

rejected = [
    {'id': 'R-01', 'where': [14.287, 1.11], 'reason': 'Gap x 13.887-14.687 in the 0.20 m corridor / shaft wall (A-WALL 540F, y 1.009-1.209): the '
     'fire-hose cabinet (block FHC 02 - Type 1, M-EQPM, x 13.89-14.69, y 0.86-1.21; text FHC) stands in it. A cabinet recess, not an opening.'},
    {'id': 'R-02', 'where': [19.675, 1.06], 'reason': 'West mouth of the corridor alcove (x 19.087-20.262 at y 1.209, 0.30 m deep): the recess in front '
     'of door A-15, part of the corridor; the opening is the door at its back.'},
    {'id': 'R-03', 'where': [21.35, 1.06], 'reason': 'East mouth of the alcove (x 20.762-21.937): recess in front of door A-16.'},
    {'id': 'R-04', 'where': [20.7, 8.07], 'reason': 'Niche x 20.612-20.787, y 7.537-8.607 in bedroom 2\'s west wall (rounded A-WALL returns 58C7/58C8) '
     'holding the slatted luggage rack (Q-CASE): blind, the partition 51B9 (x 20.407-20.612) runs on behind it.'},
    {'id': 'R-05', 'where': [15.31, 4.42], 'reason': 'Closed space x 15.137-15.512, y 3.784-5.061 behind a single layer-0 line on the foyer\'s east side '
     '(x 15.112): built-in cupboard or duct; no door symbol, enclosed on all sides.'},
    {'id': 'R-06', 'where': [18.04, 5.21], 'reason': 'North side of the bar, x 15.662-20.412: open plan to the living and dining area (4.75 m, no wall '
     'end at a door-wide distance); not a passage.'},
    {'id': 'R-07', 'where': [21.66, 5.73], 'reason': 'Wardrobe of the lobby of bedroom 2 (x 20.61-22.71, y 5.43-6.03, hanging rails, front line '
     'y 6.034) and the wardrobes of the master bedroom (front y 0.959), walk-in wardrobe rails, mini-bars, TV and shelving units: casework.'},
    {'id': 'R-08', 'where': [15.73, 6.43], 'reason': 'Furniture fills on layer 0 (sofa back 4FF1 x 15.77-16.07, y 7.0-8.95; SOLID 4FD2 x 16.04-16.07, '
     'y 8.95-9.75; sofa frame 502C x 7.04-7.25, y 7.70-8.68) and furniture arcs on A-GENM / I-FURN (beds, round tables): not walls, no '
     'openings.'},
    {'id': 'R-09', 'where': [17.1, 3.43], 'reason': 'Corridor widening x 17.137-20.437 (north face at y 3.659 instead of 3.209-3.309) and the faces '
     'of 540D, 540C, the south column and 51BE towards the corridor: the corridor\'s own width (2.0-2.1 m), not openings.'},
    {'id': 'R-10', 'where': [9.52, 8.65], 'reason': 'Fixed glass of the bathroom screens beside the glass doors (see glassWalls): glass wall, not '
     'windows.'},
    {'id': 'R-11', 'where': [12.85, 0.71], 'reason': 'Shaft x 12.012-14.687, y 0.409-1.009 (A-WALL 0.20 m walls): closed, no door.'},
    {'id': 'R-12', 'where': [25.079, 7.0], 'reason': 'Walls cut by the view crop at x 25.079 (y 0.66-0.76, 3.66-3.76, 11.41-11.51) and y 0.009 '
     '(x 15.89-16.19, 20.41-20.61, 24.84-24.94): crop ends, not openings.'},
    {'id': 'R-13', 'where': [7.86, 11.4], 'reason': 'Break x 7.787-7.937 in the 25 mm facade lining (4DE4 / 4DC5) on the bathroom side: lining '
     'only, the A-WALL facade 53F7 runs on behind it.'},
]

method = (
    "Labeller A, geometry first, from prims.pkl (29,886 items) and the DXF only; the description and pictures were used to orient and to "
    "check. (1) Listed every SOLID fill loop on the wall layers 0, A-WALL and S-COLS (183 loops, fills.py) with its oriented size: the "
    "partition cores and linings on layer 0, the shell on A-WALL, the six columns; set aside the two sofa fills, a 30 mm SOLID by the sofa "
    "and four specks. (2) Built the union of those fills and cast a ray from every wall-end cap along its outward normal to the next wall "
    "fill or glass (endscan.py): every gap between facing wall ends and every wall end facing a wall side or open space. (3) Fitted every "
    "arc (arcs.py): 16 door swings on A-DOOR (9 top level + 7 in the six corridor door blocks) and 4 glass-door swings on A-DOOR-HDLN; the "
    "33 swing-like arcs on A-GENM / I-FURN are beds and table rims. (4) Dumped every A-DOOR / A-DOOR-FRAM line (leaves, pocket leaves, "
    "slide arrows, frames, bi-fold panels) and the contents of the six door blocks, and tied each to a gap. (5) Searched for walls drawn "
    "with lines only (linepairs.py: unfilled parallel layer-0 / A-WALL line pairs 6-25 cm apart): only the two bathroom screens, pocket "
    "slots, lines drawn across door gaps, the dashed head and furniture. (6) Read the curtain-wall panes and mullions of the six bays "
    "(bays.py). (7) Drew zooms with my own renderer (draw.py: layer 0 brown with fills shaded, A-WALL black, glass cyan, A-DOOR red, "
    "frames magenta) of the master bathroom, dressing area, foyer, BOH, lobby, corridor ends, P2, the bedroom-2 niche and two bays, then "
    "a marked overview (marked_all.png) with every listed opening drawn as a green a-b segment and an id: no gap, swing, leaf, pocket, "
    "arrow or track is left without one. Conventions: a/b on the wall centre line at the faces of the wall fills that bound the gap, frames "
    "included; a door in a glass screen measured by its leaf; pocket doors between the fill ends (1.10 m; clear 1.00); doors outside the "
    "suite listed and scored, the two cut by the crop optional; glass-screen doors, open sides into open space and curtain-wall facets "
    "optional. No window family and no opening sash exist in the drawing.")

header = {'labeller': 'A', 'approach': 'geometry first (wall gaps from the fills, then what fills them; pictures only to check)',
          'drawing': 'presidential suite_layout.dwg (Revit export, 3D team, 9 Nov 2026), cache suite_revit, units mm -> drawing metres',
          'date': '2026-11-10', 'floor': FLOOR}

doc = {'header': header, 'openings': ops, 'glassWalls': glass_walls, 'uncertain': uncertain, 'rejected': rejected, 'method': method}
here = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
doc['files'] = [here + '/' + f for f in ('load.py', 'fills.py', 'endscan.py', 'arcs.py', 'bays.py', 'linepairs.py', 'draw.py',
                                          'make_list.py', 'mark.py', 'marked_all.png', 'marked_west.png', 'marked_east.png', 'overview_struct.png', 'z_masterbath.png', 'z_dressing.png',
                                          'z_foyer.png', 'z_boh.png', 'z_lobby.png', 'z_corr_south.png', 'z_east_corridor.png',
                                          'z_p2.png', 'z_niche.png', 'z_bay1.png', 'z_westbay.png')]
# counts
import collections
c = collections.Counter((o['kind'], bool(o.get('optional'))) for o in ops)
header['counts'] = {f"{k}{' (optional)' if opt else ''}": n for (k, opt), n in sorted(c.items())}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)
print(OUT, len(ops), header['counts'])
for o in ops:
    print(o['id'], o['kind'], 'OPT' if o.get('optional') else '   ', o['a'], o['b'], o['width'], o['subtype'][:70])
