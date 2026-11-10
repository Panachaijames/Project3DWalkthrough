"""Labeller C, step 10: assemble the geometry-only inventory (format of keys/tower/labels/inventory-l29.json, plus a
header entry first), check every entry against the geometry, and write labels/C.json.

Checks per entry: (1) the two ends lie on wall material (points 2 cm beyond each end, along the opening, are inside the
wall fills / the glass line work), (2) the opening between them is free of wall fill (sampled every 1 cm on the centre
line, except the bays and screens where the check is on the glass), (3) width = |b - a|. The door evidence (arcs, leaves,
frames, arrows) was read in steps 2, 4 and 7 (c02_arcs.py, c04_doorlines.txt, c07_box.py)."""
import json, math, pickle, sys
import shapely
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

P = 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work/suite_revit/prims.pkl'
OUT = sys.argv[1]
FLOOR = 'suite_revit'

D = pickle.load(open(P, 'rb'))
EXCL = {'4FF1', '502C', '4E08', '4E09', '4DEB'}
polys = []
for d in D['items']:
    if d['t'] == 'HATCH' and d['lay'] in ('0', 'A-WALL', 'S-COLS') and d['h'] not in EXCL:
        for lp in d['loops']:
            if len(lp) > 2:
                p = Polygon(lp).buffer(0)
                if p.area > 1e-6: polys.append(p)
W = unary_union(polys).buffer(0.0005)
shapely.prepare(W)

E = []   # entries


def add(kind, a, b, subtype, host, encodings, note, optional=False, check='fill', rooms=''):
    o = {'id': None, 'floor': FLOOR, 'kind': kind, 'a': [round(a[0], 4), round(a[1], 4)], 'b': [round(b[0], 4), round(b[1], 4)],
         'width': round(math.dist(a, b), 4), 'encodings': encodings,
         'note': (f'[{subtype}] ' + ('OPTIONAL true - ' if optional else '') + note + (f' Rooms: {rooms}.' if rooms else '')),
         'subtype': subtype, 'host': host}
    if optional: o['optional'] = True
    o['_check'] = check
    E.append(o)


ENC_SWING = 'exploded door: dashed swing arc on A-DOOR (r = leaf) + open leaf (two A-DOOR lines 40 mm apart)'
ENC_FRAME = 'A-DOOR-FRAM frame returns 50 mm deep at both jambs'
ENC_FILL0 = 'gap between wall fills (layer-0 SOLID hatch partitions)'
ENC_FILLA = 'gap between wall fills (A-WALL SOLID hatch)'
ENC_BLOCK = 'Revit door family block on A-DOOR (leaves, dashed arcs on A-DOOR, frames on A-DOOR-FRAM)'
ENC_POCKET = 'pocket door: 1.0 m leaf (A-DOOR, two lines 40 mm apart) inside a slot in the wall + slide arrow on A-DOOR'
ENC_CORE = 'partition core lines (layer 0) run on across the opening'
ENC_GLASSDOOR = 'glass door: 10 mm leaf on A-DOOR drawn open 30 deg + dashed 30-deg swing on A-DOOR-HDLN + handle on A-GENM-HDLN'
ENC_SCREEN = 'gap in the 10 mm glass of a layer-0 glass screen (kerb lines 0.10 m apart run on across)'
ENC_CW = 'curtain-wall panel block (A-GLAZ-CURT System Panel - GLAZED) between mullion boxes (A-GLAZ-CWMG) and A-WALL pieces'
ENC_OPEN = 'open side: wall end with no wall in line on the far side'

# ---------------------------------------------------------------- suite: hinged doors (exploded families)
add('door', (11.5616, 3.6974), (11.5616, 4.6980), 'single swing, leaf 0.90 (exploded; matches the unused definition DOOR_SWING_1_SOLID - D09, 1.0 m)', 'wall',
    [ENC_SWING, ENC_FRAME, ENC_FILL0],
    'Partition x 11.4867-11.6367 (layer-0 fill 51C0 ends y 3.6974, fill 51B3 starts y 4.6980). Swing arc A7CA (A-DOOR, - DASH SMALL) '
    'centre = hinge (11.5067, 3.7474) r 0.900, 89.5->180 deg: closed leaf along the wall to (11.5145, 4.6473), open leaf A7C8/A7C9 '
    'drawn at 180 deg (x 10.6067-11.5067). Frames A7C0-A7C2 (y 3.6974-3.7474) and A7C3-A7C5 (y 4.6474-4.6974): clear 0.900, '
    'wall end to wall end 1.001. Lever handle on A-DETL-GENF at the leaf tip.',
    rooms='FOYER (east, x 11.64-15.11) / BEDROOM FOYER (west); leaf swings west')
add('door', (11.7116, 3.2591), (12.4616, 3.2591), 'single swing, leaf 0.70 (exploded; matches DOOR_SWING_1_SOLID - 800)', 'wall',
    [ENC_SWING, ENC_FRAME, ENC_FILL0, 'threshold line (layer 0) across'],
    'Wall y 3.2091-3.3091 (layer-0 fill 4DB8: stub x 11.6116-11.7116 and piece x 12.4616-13.2866). Swing arc 5552 centre = hinge '
    '(11.7116, 3.2291) r 0.700, 270->0.5 deg; leaf 5550/5551 open at 270 deg (south, into the small room). Frame line 554B across the '
    'wall at x 11.7116 (hinge side, flush with the wall end) and 554A at x 12.4116 + return 5549 (strike side, 50 mm inside the gap): '
    'clear 0.700, wall end to wall end 0.750 (the 0.80 m family frame starts at x 11.6616, inside the 0.10 m wall stub). Threshold line 4F03 (x 11.7616-12.4616, y 3.3091).',
    rooms='FOYER (north) / small room x 11.64-13.12, y 1.22-3.19 (toilet-roll holder block at (11.627, 1.589): probably a WC)')
add('door', (13.2866, 3.2591), (15.0866, 3.2591), 'double swing, 2 x 0.865 leaves, suite entrance (exploded; matches the unused definition DOOR_SWING_DOUBLE_TYPE 2 - L16_D07, 1.8 m)', 'wall',
    [ENC_SWING, ENC_FRAME, ENC_FILL0, 'threshold line (layer 0) across'],
    'Corridor wall y 3.2091-3.3091 (layer-0 fill 4DB8 pieces end at x 13.2866 and start at x 15.0866). Two dashed swing arcs on A-DOOR: '
    '552D centre (13.3216, 3.3091) r 0.865, 359.5->90 deg and 5544 centre (15.0516, 3.3091) r 0.865, 90->180.5 deg; both leaves drawn open '
    'at 90 deg into the foyer (x 13.3216-13.3616 and 15.0116-15.0516, y 3.3091-4.1741); closed tips meet at x 14.1866. Frames '
    '5532-5538 (x 13.2866-13.3366) and 553B-5543 (x 15.0366-15.0866): hinges 1.730 apart, wall end to wall end 1.800. Threshold line '
    '4F05 (x 13.3216-15.0516, y 3.3091).',
    rooms='corridor (south) / FOYER (north); the suite entrance')
add('door', (20.5116, 4.4091), (20.5116, 5.2091), 'single swing, leaf 0.70 (exploded; matches the unused definition DOOR_SWING_1_SOLID - 800, 0.8 m)', 'wall',
    [ENC_SWING, ENC_FRAME, ENC_FILL0, ENC_CORE],
    'Partition x 20.44-20.61 (fill 51BE x 20.4366-20.6116 ends y 4.4091; fill 51BC x 20.4116-20.6116 starts y 5.2091). Swing arc 57E2 '
    'centre = hinge (20.5666, 5.1591) r 0.700, 269.5->0 deg: closed leaf along the wall to (20.5605, 4.4591), open leaf 57E0/57E1 at 0 deg '
    '(east, into the BOH). Frames 57D8-57DA (y 4.4091-4.4591) and 57DB-57DD (y 5.1591-5.2091): clear 0.700, wall end to wall end 0.800. '
    'The core lines 4F07 / 4FA2 (x 20.4366 / 20.5866) run on across the opening. Centre line x 20.5116 = the core (frames x 20.4366-20.5866).',
    rooms='BAR (west) / BOH. (east)')
add('door', (20.7116, 3.3591), (21.5116, 3.3591), 'single swing, leaf 0.70 (exploded; matches the unused definition DOOR_SWING_1_SOLID - 800, 0.8 m)', 'wall',
    [ENC_SWING, ENC_FRAME, ENC_FILL0, 'threshold / core line (layer 0) across'],
    'Corridor wall y 3.3091-3.4091 (layer-0 fill 4DF8: stub x 20.5866-20.7116, piece from x 21.5116). Swing arc 580D centre = hinge '
    '(20.7616, 3.3891) r 0.700, 359.5->90 deg; leaf 580B/580C open at 90 deg (north, into the BOH). Frames 5806-5808 (x 20.7116-20.7616) '
    'and 5803-5805 (x 21.4616-21.5116): clear 0.700, wall end to wall end 0.800. Line 4FA3 (x 20.7616-21.4616, y 3.4091) across.',
    rooms='corridor (south) / BOH. (north)')
add('door', (22.8116, 6.0341), (22.8116, 6.8341), 'single swing, leaf 0.70, at a corner (exploded; matches DOOR_SWING_1_SOLID - 800, 0.8 m)', 'wall',
    [ENC_SWING, ENC_FRAME, ENC_FILL0],
    'Partition x 22.7116-22.8866 (fill 51FA ends y 6.0341); the north end is the face of the cross wall y 6.8341-6.9941 (fills 51FD / 51FC, '
    'x 22.7366-24.7866): a doorway at a corner. Swing arc A9CC centre = hinge (22.8666, 6.7841) r 0.700, 269.5->0 deg: closed leaf to '
    '(22.8605, 6.0841), open leaf A9CA/A9CB at 0 deg (east). Frames A9C2-A9C4 (y 6.0341-6.0841) and A9C5-A9C7 (y 6.7841-6.8341): '
    'clear 0.700, wall end to wall face 0.800. Centre line x 22.8116 = the core (frames x 22.7366-22.8866).',
    rooms='lobby of bedroom 2 (west, x 20.61-22.71) / unnamed room east of the BOH (x 22.89-24.79, y 3.42-6.85, probably bedroom 2 bathroom)')

# ---------------------------------------------------------------- suite: pocket doors
add('door', (7.4539, 2.2341), (7.4539, 3.3341), 'pocket (cavity) sliding door, leaf 1.00 (exploded; matches the unused definition DOOR_SLIDING_CAVITY_1_SOLID - D13, opening 1.1 m)', 'wall',
    [ENC_POCKET, ENC_FRAME, ENC_FILL0, ENC_CORE],
    'Partition x 7.3539-7.5539 (fill 51B7 ends y 2.2341; fill 51AF starts y 3.3341 with the pocket slot x 7.4195-7.4889 up to y 4.2665). '
    'Leaf 5576-5579 (x 7.4339-7.4739, y 3.2241-4.2241) sits in the pocket; slide arrow 5573-5575 (x 7.3239, y 2.4841-3.0841, head to the '
    'north) in the master bedroom. Frames 557D-557F (y 2.2341-2.2841, line across at 2.2841) and 557A-557C / 5580-5582 (returns at y '
    '3.2841-3.3341 either side of the slot): clear 1.000, wall end to wall end 1.100. Core lines 4EB9 / 4E93 (x 7.3789 / 7.5289, '
    'y 2.2841-3.3423) run on across. No swing arc.',
    rooms='MASTER BEDROOM (west) / dressing area and BEDROOM FOYER (east); the bedroom entrance')
add('door', (7.4539, 10.2841), (7.4539, 11.3841), 'pocket (cavity) sliding door, leaf 1.00 (exploded; matches the unused definition DOOR_SLIDING_CAVITY_1_SOLID - D13, opening 1.1 m), at a corner', 'wall',
    [ENC_POCKET, ENC_FRAME, ENC_FILL0, ENC_CORE],
    'North end of the partition x 7.3539-7.5439 (fill 51AF ends y 10.2841, pocket slot x 7.4189-7.4889 from y 9.3341); the north end of '
    'the opening is the facade lining face y 11.3841 (fill 4DE4, x 7.350-7.787). Leaf 5586-5589 (x 7.4339-7.4739, y 9.3941-10.3941) in '
    'the pocket; slide arrow 5583-5585 (x 7.3239, y 10.5341-11.1341, head to the south) in the master bedroom. Frames 558A-5592 (returns '
    'y 10.2841-10.3341; north jamb y 11.3341-11.3841, line across at 11.3341): clear 1.000, wall end to wall face 1.100. Core lines '
    '4EBA / 4EE6 (x 7.3789 / 7.5289) across.',
    rooms='MASTER BEDROOM (west) / MASTER BATHROOM (east)')
add('door', (8.1289, 5.1557), (9.2289, 5.1557), 'pocket (cavity) sliding door, leaf 1.00 (exploded; matches the unused definition DOOR_SLIDING_CAVITY_1_SOLID - D13, opening 1.1 m)', 'wall',
    [ENC_POCKET, ENC_FRAME, ENC_FILL0, ENC_CORE],
    'Wall y 5.0607-5.2507 (fill 51B2: piece x 7.5539-8.1289, piece from x 9.2289 with the pocket slot y 5.1257-5.1957 to x 10.6666). '
    'Leaf 5596-5599 (x 9.1189-10.1189, y 5.1407-5.1807) in the pocket; slide arrow 5593-5595 (y 5.2907, x 8.3789-8.9789, head to the '
    'east) on the bathroom side. Frames 559D-559F (x 8.1289-8.1789, line across at 8.1789) and 559A-55A2 (x 9.1789-9.2289, returns either '
    'side of the slot): clear 1.000, wall end to wall end 1.100. Core lines 4EE7 / 4E95 (y 5.2357 / 5.0857) across.',
    rooms='BEDROOM FOYER (south) / MASTER BATHROOM (north)')
add('door', (20.5116, 6.0841), (20.5116, 7.1841), 'pocket (cavity) sliding door, leaf 1.00 (exploded; matches the unused definition DOOR_SLIDING_CAVITY_1_SOLID - D13, opening 1.1 m)', 'wall',
    [ENC_POCKET, ENC_FRAME, ENC_FILL0, ENC_CORE],
    'Partition x 20.41-20.61 (fill 51BC ends y 6.0841; fill 51B9 starts y 7.1841 with the pocket slot x 20.4766-20.5466 to y 8.0718). '
    'Leaf 627C-627F (x 20.4916-20.5316, y 7.0741-8.0741) in the pocket; slide arrow 6279-627B (x 20.3816, y 6.3341-6.9341, head to the '
    'north) in the living area. Frames 6283-6285 (y 6.0841-6.1341) and 6280-6288 (returns y 7.1341-7.1841): clear 1.000, wall end to '
    'wall end 1.100. Core lines 4F08 / 4FA4 (x 20.4366 / 20.5866) across.',
    rooms='LIVING & DINING AREA (west) / lobby of bedroom 2 and BEDROOM 2 (east)')

# ---------------------------------------------------------------- suite: bi-fold
add('door', (9.4616, 0.9591), (9.4616, 3.1841), 'bi-fold door, 4 panels of 0.564 (exploded; matches the unused definition Doors 1 - Doors 1)', 'wall',
    ['bi-fold panels: zigzag of 8 A-DOOR lines of 0.564 m folded at one end', 'dashed track line (layer 0) along the opening', ENC_FILL0],
    'Wall x 9.4116-9.5116 with linings (fill 4DBA + end cap 4DD0) ends at y 0.9591; the north end is the lining face y 3.1841 (fill 4DD1) '
    'of the wall y 3.2091-3.3091 (fill 4DCA, x 9.4116-11.5116). Four panels drawn folded as a zigzag against the north end (A-DOOR '
    '59E8-59F7, x 9.3866-9.9441, y 2.4556-3.2324); dashed track line 4FC9 (layer 0, - DASH SMALL) on x 9.4616 from y 0.9591 to 3.1841 '
    'spans the whole opening. Wall end to wall face 2.225.',
    rooms='dressing area (west, x 7.55-9.39) / walk-in wardrobe (east, x 9.54-11.49, hanging rails); a room door, not a cupboard front')

# ---------------------------------------------------------------- suite: glass doors in the bathroom screens
add('door', (9.5166, 5.3507), (9.5166, 6.0507), 'glass hinged door 0.70 in a glass screen (exploded; matches the unused definition IN_SHOWER DOOR1 - Shower door_700X2160MM), WC compartment', 'glass',
    [ENC_GLASSDOOR, ENC_SCREEN],
    'Screen x 9.4666-9.5666 (kerb lines 4EE8 / 4EE5) with 10 mm glass on x 9.5116 / 9.5216 (layer 0): glass piece A7B4-A7B7 '
    'y 5.2507-5.3507, then the door, then glass 4FA8 / 4FA9 y 6.0507-6.9505 to the WC / shower wall (fills 4DC7-4DC9, y 6.9355-7.0655). '
    'Leaf 5A8D-5A90 (A-DOOR, 10 mm, 0.700) hinged at (9.5116, 5.3507), drawn open 30 deg to the west; dashed swing 5A91 '
    '(A-DOOR-HDLN) r 0.700, 90->120 deg; pull handle on A-GENM-HDLN. Measured by the leaf = the gap in the glass (0.700). The WC '
    '(P-SANR-FIXT, x 10.32-10.69, y 6.79-6.92) stands in the compartment x 9.57-11.49, y 5.25-6.94. Scored here as the door of an '
    'enclosed WC compartment; the family is the shower-door family of the three optional glass doors (master shower x2, room east '
    'of the BOH), so it may be judged like a '
    'toilet cubicle door (optional).',
    rooms='MASTER BATHROOM (west) / WC compartment (east)')
add('door', (9.5166, 7.1655), (9.5166, 7.8655), 'glass hinged shower door 0.70 (exploded; matches the unused definition IN_SHOWER DOOR1 - Shower door_700X2160MM)', 'glass',
    [ENC_GLASSDOOR, ENC_SCREEN],
    'Shower door. Same screen x 9.47-9.57: glass A8E5-A8E8 y 7.0655-7.1655, door, glass 4FB0 / 4FB1 y 7.8654-9.4341. Leaf A8E0-A8E3 '
    'hinged at (9.5116, 7.1655), open 30 deg to the west; dashed swing A8E4 (A-DOOR-HDLN) r 0.700, 90->120 deg. Gap in the glass 0.700. '
    'Optional because the conventions leave out shower screens and this is a door of the shower enclosure (x 9.57-11.49, y 7.07-10.23, '
    'shower valves on P-SANR-FIXT at x 11.29-11.49), a sanitary fitting rather than a room door.',
    optional=True, rooms='MASTER BATHROOM (west) / shower (east)')
add('door', (9.5166, 9.4341), (9.5166, 10.1341), 'glass hinged shower door 0.70 (exploded; matches the unused definition IN_SHOWER DOOR1 - Shower door_700X2160MM)', 'glass',
    [ENC_GLASSDOOR, ENC_SCREEN],
    'Second door of the same shower. Glass 4FB0 / 4FB1 to y 9.4341, door, glass 4FAD-4FAF y 10.1341-10.2391, then the fixed north '
    'pane of the shower (fill 4DEB, x 9.5116-11.4966, y 10.2291-10.2391). Leaf 5B15-5B18 hinged at (9.5116, 10.1341), open 30 deg; dashed '
    'swing 5B19 (A-DOOR-HDLN) r 0.700, 240->270 deg. Gap in the glass 0.700. Optional for the same reason (shower enclosure door).',
    optional=True, rooms='MASTER BATHROOM (west) / shower (east)')
add('door', (23.0016, 4.775), (23.7016, 4.775), 'glass hinged door 0.70 in a glass screen (exploded; matches the unused definition IN_SHOWER DOOR1 - Shower door_700X2160MM), probably a shower', 'glass',
    [ENC_GLASSDOOR, ENC_SCREEN],
    'Screen y 4.7241-4.8241 (kerb lines 4F81 / 4F80, x 22.9016-24.81) with 10 mm glass y 4.770-4.780: glass piece A621-A624 '
    'x 22.9016-23.0016, door, glass 4F85-4F87 x 23.7016-24.7966. Leaf 58B1-58B4 hinged at (23.0016, 4.7800), open 30 deg to the north; '
    'dashed swing 58B5 (A-DOOR-HDLN) r 0.700, 0->30 deg; handle on A-GENM-HDLN. Gap in the glass 0.700. Optional as a shower door: '
    'same shower-door family and kerbed screen as the master shower; the compartment behind (x 22.89-24.80, y 3.42-4.72) has no '
    'fixture drawn, only a 0.97 x 0.35 m box against its south wall (A625 / A626: a bench?). If it is a WC compartment it should be '
    'scored like the master-bathroom WC door.',
    optional=True, rooms='unnamed room east of the BOH: north part (y 4.82-6.85) / south compartment (y 3.42-4.72)')

# ---------------------------------------------------------------- suite: passage
add('passage', (13.1366, 5.1357), (15.1116, 5.1357), 'cased opening with a head (no leaf)', 'wall',
    [ENC_FILL0, 'the two face lines go on across the gap dashed (head over the opening)'],
    'Wall y 5.0607-5.2107: fill 51B6 (x 11.6366-13.1366) ends at x 13.1366; the arm of the L-shaped fill 51B6 (x 15.1116-15.6616, '
    'vertical leg x 15.5116-15.6616 down to y 3.7591) starts at x 15.1116: wall ends in line on both sides. No arc, leaf, frame or glass '
    'in the gap; the face lines 5F8F (y 5.2107) and 5F91 (y 5.0607) are drawn - DASH SMALL across the whole gap (the only dashed head '
    'of this kind). Wall end to wall end 1.975.',
    rooms='FOYER (south) / LIVING & DINING AREA (north)')

# ---------------------------------------------------------------- corridor: door blocks
add('door', (15.2366, 3.2591), (17.0366, 3.2591), 'double swing service door 2 x 0.865 (SERVICE_SWING_DOUBLE - D22 1800X2100MM), to a riser', 'wall',
    [ENC_BLOCK, 'three frame lines across the opening', ENC_FILL0, ENC_FILLA],
    'Block SERVICE_SWING_DOUBLE - D22 1800X2100MM-V24 (A-DOOR) ins (16.1366, 3.2591) rot 180: leaves 0.865 hinged at (15.2716, 3.2091) '
    'and (17.0016, 3.2091), drawn open 35 deg toward the corridor (south); dashed arcs r 0.865 (325->0.5 and 179.5->215 deg); frame '
    'lines across the opening at y 3.2091 / 3.2491 / 3.3091 (A-DOOR-FRAM). West jamb: layer-0 fill 4DB8 (x 15.0866-15.2366) and A-WALL '
    '540C (x 15.1366-15.2366, y 3.3091-3.7591); east jamb: A-WALL 540D (x 17.0366-17.1366, y 3.2091-3.6591). Wall end to wall end 1.800 '
    '= the type size. Behind it a 0.35 m riser (y 3.31-3.66, dashed X marks on A-DETL).',
    rooms='corridor (south) / service riser (north)')
add('door', (16.1866, 1.1591), (17.0366, 1.1591), 'single swing service door, leaf 0.78 (SERVICE_DOOR_SWING_1_SOLID - 850X2400MM_D06), to a riser', 'wall',
    [ENC_BLOCK, 'three frame lines across the opening', ENC_FILLA],
    'Block SERVICE_DOOR_SWING_1_SOLID - 850X2400MM_D06-3801650 (A-DOOR) ins (16.6116, 1.1591) rot 0: leaf 0.78 hinged at (17.0016, 1.2091) '
    'drawn open 35 deg into the corridor; dashed arc r 0.78 (145->180.5 deg); frame lines across at y 1.1091 / 1.1691 / 1.2091. Corridor '
    'wall y 1.1091-1.2091: A-WALL 5421 ends at x 16.1866 and restarts at x 17.0366. Wall end to wall end 0.850 = the type size. Behind it '
    'a 0.35 m riser x 16.19-17.04, y 0.76-1.11 (X on layer 0, 54AF / 54B0).',
    rooms='corridor (north) / service riser (south)')
add('door', (19.1766, 0.8591), (20.1766, 0.8591), 'single swing unit door, leaf 0.93 (UNIT_DOOR_SWING_1_SOLID - D01_1000X2250MM)', 'wall',
    [ENC_BLOCK, ENC_FILLA, 'A-WALL face lines run on across the opening'],
    'Block UNIT_DOOR_SWING_1_SOLID - D01_1000X2250MM-3324155 (A-DOOR) ins (19.6766, 0.8591) rot 0: hinge (20.1416, 0.8091), dashed arc '
    'r 0.930 from the closed position (19.2117, 0.8172) toward the south; leaf drawn open to the south, cut by the view crop at y 0.0086. '
    'Wall y 0.8091-0.9091 at the back of the corridor alcove: A-WALL fills 5422 end at x 19.1766 and start at x 20.1766; frames '
    '19.1766-19.2266 and 20.1266-20.1766; the two A-WALL face lines 54BD / 54C0 run on across the opening. Wall end to wall end 1.000 '
    '(clear 0.93). Door of a neighbouring unit (its room is outside the drawing); the opening itself is wholly drawn.',
    rooms='corridor alcove (north) / neighbouring unit (south, not drawn)')
add('door', (20.8466, 0.8591), (21.8466, 0.8591), 'single swing unit door, leaf 0.93 (UNIT_DOOR_SWING_1_SOLID - D01_1000X2250MM)', 'wall',
    [ENC_BLOCK, ENC_FILLA, 'A-WALL face lines run on across the opening'],
    'Block UNIT_DOOR_SWING_1_SOLID - D01_1000X2250MM-3324157 (A-DOOR) ins (21.3466, 0.8591) rot 180: hinge (20.8816, 0.8091), dashed arc '
    'r 0.930 from the closed position (21.8116, 0.8172) toward the south, cut by the crop. A-WALL fills 5423 end at x 20.8466 and start at '
    'x 21.8466 (y 0.8091-0.9091); frames 20.8466-20.8966 and 21.7966-21.8466; face lines 54C9 / 54CC run on across. Wall end to wall end '
    '1.000 (clear 0.93). Mirror of the previous door on the other side of the column x 20.26-20.76.',
    rooms='corridor alcove (north) / neighbouring unit (south, not drawn)')
add('door', (23.9866, 1.1591), (25.7866, 1.1591), 'double swing service door 2 x 0.865 (SERVICE_SWING_DOUBLE - D22 1800X2100MM), cut by the view crop', 'wall',
    [ENC_BLOCK, 'three frame lines across the opening', ENC_FILLA],
    'Block SERVICE_SWING_DOUBLE - D22 1800X2100MM-V25 (A-DOOR) ins (24.8866, 1.1591) rot 0: leaves hinged at (24.0216, 1.2091) and '
    '(25.7516, 1.2091), open 35 deg into the corridor; frame lines y 1.1091 / 1.1691 / 1.2091 from x 24.0216 to the crop. West jamb: '
    'A-WALL 5414 ends at x 23.9866 (y 1.1091-1.2091). The view crop at x 25.0785 cuts the opening: the east jamb and most of the second '
    'leaf are outside the drawing. Ends given from the family (1.800, symmetric about the insert); only x 23.9866-25.0785 (1.092) is '
    'drawn. Optional: the width cannot be read from the drawing.',
    optional=True, rooms='corridor (north) / service riser (south, X marks on A-DETL)')
add('door', (23.9866, 3.2591), (25.7866, 3.2591), 'double swing service door 2 x 0.865 (SERVICE_SWING_DOUBLE - D22 1800X2100MM), cut by the view crop', 'wall',
    [ENC_BLOCK, 'three frame lines across the opening', ENC_FILL0],
    'Block SERVICE_SWING_DOUBLE - D22 1800X2100MM-2804302 (A-DOOR) ins (24.8866, 3.2591) rot 180: leaves hinged at (24.0216, 3.2091) '
    'and (25.7516, 3.2091), open 35 deg into the corridor; frame lines y 3.2091 / 3.2491 / 3.3091 from x 24.0216 to the crop; west frame '
    'x 23.9866-24.0366 flush with the east ends of fills 4DF8 / 4DF9. The crop at x 25.0785 cuts the opening (east jamb not drawn). Ends '
    'from the family (1.800); drawn part x 23.9866-25.0785. Optional for the same reason.',
    optional=True, rooms='corridor (south) / service riser (north, X marks on A-DETL)')

# ---------------------------------------------------------------- optional passage mouths
add('passage?', (7.5539, 3.2591), (9.3866, 3.2591), 'open side of the dressing area', 'wall', [ENC_OPEN],
    'The wall y 3.2091-3.3091 (fill 4DCA with linings 4DD1 / 4DCC to x 9.3866) between the walk-in wardrobe and the bedroom foyer ends '
    'at x 9.3866; nothing stands in line to the west up to the partition x 7.3539-7.5539, which at this height holds the pocket door '
    '(y 2.2341-3.3341). The dressing area (x 7.55-9.39, y 0.33-3.18) is open along its whole north side. Passage mouth into open space: '
    'optional, probably not an opening.',
    optional=True, rooms='dressing area (south) / BEDROOM FOYER (north)')
add('passage?', (20.6116, 6.9241), (22.7366, 6.9241), 'open side of the lobby of bedroom 2', 'wall', [ENC_OPEN],
    'The wall y 6.8541-6.9941 (fill 51FC, south wall of bedroom 2 over the room east of the BOH) ends at x 22.7366; west of it the lobby '
    '(x 20.61-22.71, y 5.43-6.99) is open to bedroom 2 up to the partition x 20.41-20.61, which at this height holds the pocket door '
    '(y 6.0841-7.1841). Passage mouth into open space: optional, probably not an opening.',
    optional=True, rooms='lobby of bedroom 2 (south) / BEDROOM 2 (north)')
add('passage?', (19.0866, 1.1591), (20.2616, 1.1591), 'mouth of a 0.30 m door recess in the corridor wall', 'wall', [ENC_FILLA, ENC_OPEN],
    'Corridor south wall y 1.1091-1.2091 (A-WALL 5421 to x 18.9866, alcove side wall 5410 x 18.9866-19.0866) is interrupted up to the '
    'column x 20.2616-20.7616 (y 0.2091-1.2091, north face flush with the wall). Behind the gap a 0.30 m deep recess (y 0.9091-1.1091) '
    'with the unit door x 19.1766-20.1766 at its back. Optional: the mouth of a recess in front of a door, not an opening of its own.',
    optional=True, rooms='corridor / door recess')
add('passage?', (20.7616, 1.1591), (21.9366, 1.1591), 'mouth of a 0.30 m door recess in the corridor wall', 'wall', [ENC_FILLA, ENC_OPEN],
    'Between the column east face x 20.7616 and the alcove side wall 5413 (x 21.9366-22.0366, y 0.8091-1.2091); A-WALL 5414 resumes '
    'the corridor wall from x 22.0366. Recess in front of the unit door x 20.8466-21.8466. Optional, as the previous entry.',
    optional=True, rooms='corridor / door recess')

# ---------------------------------------------------------------- optional: curtain-wall bay facets
BAYNOTE = ('Fixed curtain-wall glazing, one facet of a projecting curtain-wall bay (A-GLAZ-CURT panel, two lines 10 mm apart; '
           'A-GLAZ-CWMG mullion lines 0.10 m apart along it), set between solid A-WALL pieces (wall ends, the corner wedges of block '
           'Walls 13). No opening sash, no window family and no window layer in the drawing. Optional, as fixed curtain-wall glazing '
           'set in a gap of the facade was in the bank key: by the conventions it is curtain wall (not a window) unless a sash opens; '
           'listed so that a detection here is neither a hit nor an extra. Ends on the glass line at the wall-piece faces.')
bays = [('W', 'MASTER BEDROOM west bay', 0.0)]
north = [('N1', 'MASTER BEDROOM north bay 1'), ('N2', 'MASTER BATHROOM north bay 2 (bath)'), ('N3', 'LIVING & DINING north bay 3'),
         ('N4', 'LIVING & DINING north bay 4'), ('N5', 'BEDROOM 2 north bay 5')]
add('window?', (2.7970, 2.8944), (1.6263, 4.0651), 'fixed curtain-wall glazing, west bay facet 1 at 135 deg (pane 1.556)', 'wall', [ENC_CW],
    BAYNOTE + ' Panel System Panel - GLAZED-2447693 ins (2.2116, 3.4798) rot -45; between the west wall end (A-WALL 541D) and the '
    'wedge (block Walls 13, x 1.569-1.662, y 4.030-4.100); 1.656 incl. two 0.05 mullion boxes.', optional=True,
    rooms='MASTER BEDROOM west bay (x 1.57-2.86, y 2.86-8.86)')
add('window?', (1.6116, 4.1005), (1.6116, 7.6177), 'fixed curtain-wall glazing, west bay facet 2 at 90 deg (pane 3.517)', 'wall', [ENC_CW],
    BAYNOTE + ' Panel System Panel - GLAZED-2447692 ins (1.6116, 5.8591) rot -90; between the two wedges of block Walls 13 '
    '(y 4.030-4.100 and 7.618-7.688); the pane fills the whole gap (3.517).', optional=True,
    rooms='MASTER BEDROOM west bay')
add('window?', (1.6263, 7.6530), (2.7970, 8.8237), 'fixed curtain-wall glazing, west bay facet 3 at 45 deg (pane 1.556)', 'wall', [ENC_CW],
    BAYNOTE + ' Panel System Panel - GLAZED-2447693 ins (2.2116, 8.2384) rot 45; between the wedge (y 7.618-7.688) and the west wall '
    'end (A-WALL 541C); 1.656 incl. two 0.05 mullion boxes.', optional=True, rooms='MASTER BEDROOM west bay')
PANELS = {'N1': ('54EC', '54E6', '54E8', '53F3', '53F4'), 'N2': ('54F6', '54F0', '54F2', '53F8', '53F9'),
          'N3': ('5500', '54FA', '54FC', '53FD', '53FE'), 'N4': ('550A', '5504', '5506', '5402', '5403'),
          'N5': ('5514', '550E', '5510', '5407', '5408')}
for k, (code, room) in enumerate(north):
    dx = 4.375 * k
    p1, p2, p3, wstart, wend = PANELS[code]
    add('window?', (3.8475 + dx, 11.4961), (4.0563 + dx, 12.2758), f'fixed curtain-wall glazing, bay {code} facet 1 at 75 deg (pane 0.707)', 'wall', [ENC_CW],
        BAYNOTE + f' Panel h {p1} (System Panel - GLAZED-2447686, rot -104.995); between the end of the straight facade wall (A-WALL '
        f'{wstart}, its 75-deg stub) and the first wedge of block Walls 13; 0.807 incl. two 0.05 mullion boxes.', optional=True,
        rooms=f'{room} (bay mouth on the facade line y 11.41-11.51)')
    add('window?', (4.0796 + dx, 12.3061), (5.3068 + dx, 13.0148), f'fixed curtain-wall glazing, bay {code} facet 2 at 30 deg (pane 1.417)', 'wall', [ENC_CW],
        BAYNOTE + f' Panel h {p2} (System Panel - GLAZED-2447687, rot 30.005); between the two wedges of block Walls 13; the pane fills '
        'the whole gap (1.417).', optional=True, rooms=room)
    add('window?', (6.1244 + dx, 12.8110), (5.3448 + dx, 13.0198), f'fixed curtain-wall glazing, bay {code} facet 3 at 165 deg (pane 0.707)', 'wall', [ENC_CW],
        BAYNOTE + f' Panel h {p3} (System Panel - GLAZED-2447686, rot -14.995); between the second wedge and the solid end wall of the '
        f'bay (A-WALL {wend}, then a 0.45 m piece at 30 deg and the 1.66-1.83 m angled solid wall back to the facade line); 0.807 incl. '
        'two 0.05 mullion boxes.', optional=True, rooms=room)

# ---------------------------------------------------------------- checks
import numpy as np
glass_lines = []
for d in D['items']:
    if d['t'] == 'LINE' and d['lay'] in ('0', 'A-GLAZ-CURT', 'A-GLAZ-CWMG', 'A-WALL') and 'pts' in d:
        glass_lines.append(d['pts'])
from shapely.geometry import LineString, MultiLineString
GL = MultiLineString([LineString(p) for p in glass_lines if len(p) > 1]).buffer(0.006)
shapely.prepare(GL)
bad = 0
for o in E:
    a, b = np.array(o['a']), np.array(o['b'])
    L = np.linalg.norm(b - a); u = (b - a) / L
    pa, pb = a - u * 0.02, b + u * 0.02
    v = np.array([-u[1], u[0]])
    def onmat(q): return any(W.contains(Point(*(q + v * t))) for t in (0.0, 0.06, -0.06))
    ends = [onmat(pa), onmat(pb)]
    inner = [a + u * t for t in np.arange(0.01, L - 0.009, 0.01)]
    free = sum(1 for q in inner if W.contains(Point(*q)))
    msg = ''
    if o['host'] == 'glass' or o['kind'].startswith('window'):
        # ends on glass / wall pieces: the glass line work or wall material must be just beyond each end
        ends = [W.contains(Point(*pa)) or GL.contains(Point(*pa)), W.contains(Point(*pb)) or GL.contains(Point(*pb))]
    if o['kind'].startswith('passage?') and not all(ends):
        msg = '(open side: one end is not on wall material, as described)'
    if 'cut by the view crop' in o['subtype'] and not all(ends):
        msg = '(cut by the crop: the far end is outside the drawing, as described)'
    ok = (all(ends) or msg) and free == 0
    if not ok: bad += 1
    print(f"{'ok ' if ok else 'BAD'} {o['kind']:9} w {o['width']:.4f} a {o['a']} b {o['b']} ends-on-material {ends} fill-inside {free} {msg} | {o['subtype'][:60]}")
print('entries', len(E), 'bad', bad)

# ---------------------------------------------------------------- ids (north to south, then west to east) and output
def cy(o): return (o['a'][1] + o['b'][1]) / 2
def cx(o): return (o['a'][0] + o['b'][0]) / 2
E.sort(key=lambda o: (-round(cy(o) * 2) / 2, cx(o)))
for i, o in enumerate(E, 1):
    o['id'] = f'C-{i:02d}'
    del o['_check']
from collections import Counter
cnt = Counter((o['kind'].rstrip('?'), bool(o.get('optional'))) for o in E)
header = json.load(open(sys.argv[2], encoding='utf-8'))
header['counts'] = {f"{k}{' (optional)' if opt else ''}": n for (k, opt), n in sorted(cnt.items())}
json.dump([header] + E, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('written', OUT, header['counts'])
