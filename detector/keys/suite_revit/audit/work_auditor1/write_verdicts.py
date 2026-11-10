"""auditor1: write ../verdicts_auditor1.json from the judgements below (made from the drawing: places.json, the place pictures,
the cache prims.pkl / plan.dxf read with probe.py, the description and the pictures folder). The claim checks (kind, ends, width
against places.json) are computed here, not typed. Run: python -B write_verdicts.py"""
import json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLACES = {p['place']: p for p in json.loads((HERE.parent / 'places.json').read_text(encoding='utf-8'))['places']}

R, N = 'real', 'not real'
V = [
 # place, verdict, kind, subtype, a, b, wall thickness, between, confidence, evidence / what it is
 ('P01', N, None, None, None, None, None, None, 0.95,
  'furniture / open floor',
  'Open floor in the living room on the edge of the rug outline (layer-0 rectangle x 12.21-16.13, y 6.71-11.01): the west end is '
  'the east edge of an ottoman (rounded box x 13.42-14.12, y 6.79-7.29 with a dashed cushion line), the east end the west end of '
  'the sofa (from x 15.14, y 7.01). No wall, glass or door-layer entity on or near the line; the nearest wall is the foyer partition '
  '1.5 m south.'),
 ('P02', N, None, None, None, None, None, None, 0.8,
  'mouth of a 0.30 m door recess (wall end beside open space)',
  'Corridor south side, east alcove: between the column (S-COLS x 20.262-20.762, y 0.209-1.209) and the alcove\'s east return wall '
  '(A-WALL x 21.937-22.037, y 0.809-1.209). The corridor wall (y 1.109-1.209) steps back 0.30 m here to the wall y 0.809-0.909 that '
  'holds the unit door D01 (place P10). Nothing spans the mouth (no head, frame, leaf or line); the opening in this recess is the '
  'door P10 itself. At most an optional "recess mouth" if the key lists such mouths.'),
 ('P03', N, None, None, None, None, None, None, 0.85,
  'recessed fire-hose cabinet (equipment niche in the wall)',
  'The 200 mm corridor/shaft wall (A-WALL y 1.009-1.209) is interrupted at x 13.887-14.687 by the fire-hose cabinet block '
  '"FHC 02 - Type 1" (M-EQPM rectangle x 13.887-14.687, y 0.859-1.209, text FHC): the cabinet fills the gap and stands 0.15 m into '
  'the closed shaft behind. No door, window or passage of the building; no door-layer entity.'),
 ('P04', R, 'door', 'pocket (cavity) sliding door: 1.0 m leaf parked in the wall pocket to the north (y 7.074-8.074, pocket x 20.477-20.547 '
  'to y 8.072), slide arrow on the dining side (x 20.382, y 6.33-6.93, pointing north), 50 mm frames at both jambs, the partition\'s '
  'two core lines (x 20.437 / 20.587) run across the opening',
  (20.512, 6.084), (20.512, 7.184), 0.20, 'bar / dining area (west) and the lobby of bedroom 2 (east)', 0.95,
  None, 'Layer-0 partition fill x 20.412-20.612 ends at y 6.084 and restarts at y 7.184 (north piece with the pocket slot); '
  'A-DOOR-FRAM returns y 6.084-6.134 and 7.134-7.184.'),
 ('P05', R, 'door', 'single hinged door: 0.70 m leaf (x 20.762-20.802, y 3.389-4.089) hinged at the west jamb, drawn open 90 deg into '
  'the BOH (north), dashed swing to (21.462, 3.383); 50 mm frames; a layer-0 threshold line y 3.409 across',
  (20.712, 3.359), (21.512, 3.359), 0.125, 'corridor (south) and the BOH. (north)', 0.95,
  None, 'Wall y 3.309-3.409 (+25 mm lining to 3.434 on the BOH side): west piece ends at x 20.712, east piece starts at x 21.512.'),
 ('P06', N, None, None, None, None, None, None, 0.75,
  'mouth of curtain-wall bay 3 (the room continues into the bay; nothing spans the mouth)',
  'Living room, north facade: the 100 mm facade wall (y 11.409-11.509) stops at the first mullion of bay 3 (x 12.55-12.66) and '
  'resumes only at the foot of the solid angled bay wall (x 16.13); the room continues into the projecting bay (curtain-wall glass '
  'and mullions in blocks, dashed layer-0 bay line, curtains). The place\'s line is 0.2 m inside the room, from the end of a 25 mm '
  'lining (x 12.904) to the foot of a shelf unit along the angled wall (x 15.665). No head, leaf, frame or line across. The glazing '
  'beyond is a curtain wall (glass wall). If the key counts bay / alcove mouths as (optional) passages, the mouth runs along the '
  'facade line y 11.46 from x 12.65 to 16.13 (about 3.48 m), not this line.'),
 ('P07', R, 'door', 'bi-fold door: four panels (8 A-DOOR lines of 0.564 m) drawn folded as a zigzag against the north jamb, dashed '
  'layer-0 track line along the opening (x 9.462, y 0.959-3.184)',
  (9.462, 0.959), (9.462, 3.184), 0.15, 'dressing area (west) and the walk-in wardrobe (east)', 0.92,
  None, 'Opening from the end face of the 0.65 m wall stub (x 9.387-9.537, ends y 0.959) to the south face of the wardrobe\'s north '
  'wall (y 3.184, lining of the wall y 3.184-3.334).'),
 ('P08', R, 'door', 'pocket (cavity) sliding door: 1.0 m leaf parked in the pocket to the east (x 9.119-10.119, slot y 5.126-5.196 to '
  'x 10.667), slide arrow on the bathroom side (y 5.291, pointing east), 50 mm frames, core lines y 5.086 / 5.236 across',
  (8.129, 5.156), (9.229, 5.156), 0.19, 'bedroom foyer (south) and the master bathroom (north)', 0.95,
  None, 'Layer-0 partition y 5.061-5.251: west piece ends at x 8.129, east piece (with the pocket) starts at x 9.229.'),
 ('P09', N, None, None, None, None, None, None, 0.8,
  'mouth of a 0.30 m door recess (wall end beside open space)',
  'Corridor south side, west alcove: between the alcove\'s west return wall (A-WALL x 18.987-19.087, y 0.809-1.209) and the column '
  '(x 20.262). The corridor wall steps back 0.30 m to the wall y 0.809-0.909 that holds the unit door D01 (place P23). Nothing '
  'spans the mouth; the opening is the door P23 itself. At most an optional "recess mouth" if the key lists such mouths.'),
 ('P10', R, 'door', 'single hinged unit door (block UNIT_DOOR_SWING_1_SOLID - D01_1000X2250MM, rot 180): leaf hinged at the west jamb '
  '(x 20.882-20.922) drawn open 90 deg to the south, leaf and swing cut by the view crop at y 0.009; frames; the A-WALL face lines '
  'y 0.809 / 0.909 run on across the opening; door of the neighbouring unit (its room is not drawn)',
  (20.847, 0.859), (21.847, 0.859), 0.10, 'corridor alcove (north) and the neighbouring unit (south, not drawn)', 0.93,
  None, 'A-WALL fills y 0.809-0.909 end at x 20.847 (piece from the column) and restart at x 21.847.'),
 ('P11', R, 'door', 'service double swing door (block SERVICE_SWING_DOUBLE - D22 1800X2100MM-V24, rot 180): two 0.865 m leaves hinged '
  'at x 15.272 and 17.002, drawn open 35 deg into the corridor (south); three A-DOOR-FRAM lines across the opening (y 3.209 / '
  '3.249 / 3.309); behind it a 0.35 m service riser (X marks on A-DETL)',
  (15.237, 3.259), (17.037, 3.259), 0.10, 'corridor (south) and a service riser (north)', 0.93,
  None, 'Between the A-WALL jambs x 15.137-15.237 and 17.037-17.137.'),
 ('P12', R, 'door', 'single hinged door: 0.90 m leaf (40 mm rectangle x 10.607-11.507, y 3.747-3.787) hinged at the south jamb, drawn '
  'open 90 deg into the bedroom foyer (west), dashed swing r 0.90; 50 mm frames; nothing across the opening',
  (11.562, 3.697), (11.562, 4.698), 0.15, 'bedroom foyer (west) and the foyer (east)', 0.96,
  None, 'Layer-0 partition x 11.487-11.637: south piece ends at y 3.697, north piece starts at y 4.698.'),
 ('P13', N, None, None, None, None, None, None, 0.97,
  'furniture (inside an ottoman)',
  'The line runs across an ottoman / pouf in the living room: layer-0 rounded rectangle x 12.669-13.369, y 6.792-7.292 with a '
  'dashed (Hidden) cushion outline inside; the ends are its two side faces. The nearest wall is the partition x 11.487-11.637, '
  '1.0 m west, continuous there.'),
 ('P14', R, 'door', 'single service door (block SERVICE_DOOR_SWING_1_SOLID - 850X2400MM_D06): 0.78 m leaf hinged at the east jamb '
  '(17.002, 1.209), drawn open 35 deg into the corridor (north); three frame lines across; behind it a 0.35 m riser (layer-0 X)',
  (16.187, 1.159), (17.037, 1.159), 0.10, 'corridor (north) and a service riser (south)', 0.93,
  None, 'Between the A-WALL piece x 16.087-16.187 and the corridor wall starting at x 17.037 (y 1.109-1.209).'),
 ('P15', R, 'door', 'double hinged entrance door of the suite: two 0.865 m leaves hinged at x 13.322-13.362 and 15.012-15.052, drawn '
  'open 90 deg into the foyer (north), dashed swings meeting at x 14.187; frames; layer-0 threshold line y 3.309 across',
  (13.287, 3.259), (15.087, 3.259), 0.125, 'corridor (south) and the foyer (north)', 0.96,
  None, 'Wall core y 3.209-3.309 (+25 mm lining to 3.334): west piece ends at x 13.287, east piece starts at x 15.087.'),
 ('P16', R, 'passage', 'doorless opening with a head: the partition fill stops and its two face lines (y 5.061 / 5.211) carry on across '
  'the gap dashed, with dashed end lines at x 13.137 and 15.112 (head / bulkhead over the opening); no leaf, frame or track',
  (13.137, 5.136), (15.112, 5.136), 0.15, 'foyer (south) and the living & dining area (north)', 0.92,
  None, 'Layer-0 partition y 5.061-5.211: west piece ends at x 13.137, east piece (L-shaped) starts at x 15.112.'),
 ('P17', R, 'door', 'pocket (cavity) sliding door: 1.0 m leaf parked in the pocket to the south (y 9.394-10.394), slide arrow on the '
  'bedroom side (x 7.324, y 10.53-11.13, pointing south), 50 mm frames at y 10.284-10.334 and 11.334-11.384, core lines x 7.379 / '
  '7.529 across; the north jamb is the inner (lining) face of the facade wall',
  (7.454, 10.284), (7.454, 11.384), 0.20, 'master bedroom (west) and the master bathroom (east)', 0.94,
  None, 'Layer-0 partition x 7.354-7.544 ends at y 10.284; north end = facade lining face y 11.384 (lining y 11.384-11.409, A-WALL '
  'facade from y 11.409).'),
 ('P18', R, 'door', 'single hinged door: 0.70 m leaf (x 22.867-23.567, y 6.744-6.784) hinged at the north jamb, drawn open 90 deg into '
  'the room east of the BOH (east), dashed swing to (22.861, 6.084); 50 mm frames',
  (22.812, 6.034), (22.812, 6.834), 0.15, 'lobby of bedroom 2 (west) and the unlabelled room east of the BOH, probably bedroom 2\'s '
  'bathroom (east)', 0.95,
  None, 'Layer-0 partition x 22.712/22.737-22.887 ends at y 6.034; north jamb = cap y 6.834-6.854 of the wall y 6.854-6.994.'),
 ('P19', N, None, None, None, None, None, None, 0.95,
  'joinery face and furniture / open floor',
  'Open floor in the living room between the face of the built-in media wall (layer-0 line x 12.012 from y 5.21 to 10.51, flush '
  'with the column face; TV block on Q-SPCQ and dashed lines behind it) and the west face of an ottoman (x 12.669-12.719), along '
  'the rug edge y 6.711. The actual partition (x 11.487-11.637) is continuous here.'),
 ('P20', N, None, None, None, None, None, None, 0.9,
  'open floor beside a continuous facade wall (rug corner to armchair)',
  'Living / dining room, 0.19 m south of the facade lining (y 11.384): from the corner of the rug outline (x 16.100, y 11.009) / the '
  'foot of bay 3\'s angled wall (x 16.11) to an armchair (x 17.79). The straight facade wall x 16.13-17.0 (lining continuous '
  'x 16.10-17.28) runs past unbroken; bay 4 only starts at x 17.0-17.28. Nothing on the line.'),
 ('P21', R, 'door', 'pocket (cavity) sliding door: 1.0 m leaf parked in the pocket to the north (y 3.224-4.224), slide arrow on the '
  'bedroom side (x 7.324, y 2.48-3.08, pointing north), 50 mm frames (y 2.234-2.284 and 3.284-3.334), core lines x 7.379 / 7.529 '
  'across',
  (7.454, 2.234), (7.454, 3.334), 0.20, 'master bedroom (west) and the dressing area / bedroom foyer (east)', 0.95,
  None, 'Layer-0 partition x 7.354-7.554: south piece ends at y 2.234, north piece (with the pocket) starts at y 3.334.'),
 ('P22', R, 'door', 'single hinged door: 0.70 m leaf (x 20.567-21.267, y 5.119-5.159) hinged at the north jamb, drawn open 90 deg into '
  'the BOH (east), dashed swing to (20.561, 4.459); 50 mm frames; the partition\'s core lines x 20.437 / 20.587 run across',
  (20.512, 4.409), (20.512, 5.209), 0.20, 'bar (west) and the BOH. (east)', 0.95,
  None, 'Layer-0 partition: south piece x 20.437-20.612 ends at y 4.409 (the bar back-counter line also ends there), north piece '
  'x 20.412-20.612 starts at y 5.209.'),
 ('P23', R, 'door', 'single hinged unit door (block UNIT_DOOR_SWING_1_SOLID - D01_1000X2250MM, rot 0): leaf hinged at the east jamb '
  '(x 20.102-20.142) drawn open 90 deg to the south, leaf and swing cut by the crop at y 0.009; frames; the A-WALL face lines run '
  'on across; door of the neighbouring unit',
  (19.177, 0.859), (20.177, 0.859), 0.10, 'corridor alcove (north) and the neighbouring unit (south, not drawn)', 0.93,
  None, 'A-WALL fills y 0.809-0.909 end at x 19.177 and restart at x 20.177 (piece against the column).'),
 ('P24', R, 'door', 'single hinged door: 0.665-0.70 m leaf (x 11.712-11.752, y 2.529-3.229) hinged at the west jamb, drawn open 90 deg '
  'into the small room south of the foyer (probably a WC), dashed swing r 0.70; frames; layer-0 threshold line y 3.309 across',
  (11.712, 3.259), (12.462, 3.259), 0.10, 'foyer (north) and the small room south of it (south)', 0.95,
  None, 'Wall core y 3.209-3.309 with linings: west piece x 11.612-11.712, east piece from x 12.462.'),
]


def rnd(p): return [round(p[0], 3), round(p[1], 3)]


verdicts = []
for place, verdict, kind, sub, a, b, wt, between, conf, *rest in V:
    P = PLACES[place]
    d = {'place': place, 'verdict': verdict, 'isOpening': verdict == R, 'confidence': conf,
         'claimed': {'kind': P['claimedKind'], 'ends': P['ends'], 'width': P['claimedWidth']}}
    if verdict == R:
        what, extra = rest
        w = math.dist(a, b)
        ea, eb = P['ends']
        end_err = max(math.dist(a, ea), math.dist(b, eb))
        d.update({'kind': kind, 'subtype': sub, 'a': rnd(a), 'b': rnd(b), 'ends': [rnd(a), rnd(b)], 'width': round(w, 3),
                  'wallThickness': wt, 'between': between,
                  'claimCheck': {'kindRight': kind == P['claimedKind'], 'endsRight': end_err <= 0.02,
                                 'widthRight': abs(w - P['claimedWidth']) <= 0.02, 'maxEndDifference_m': round(end_err, 3)},
                  'evidence': extra})
    else:
        what, ev = rest
        d.update({'kind': None, 'whatItIs': what, 'evidence': ev,
                  'claimCheck': {'kindRight': False, 'endsRight': False, 'widthRight': False}})
    verdicts.append(d)

nearby = [
 {'id': 'N1', 'isOpening': 'yes', 'kind': 'door',
  'subtype': 'glass swing door in the 10 mm glass screen of the master bathroom (WC compartment door): 0.70 m glass leaf (two lines '
             '10 mm apart on A-DOOR) hinged at the south end (9.512, 5.351), drawn open 30 deg to the west, dashed 30-deg swing on '
             'A-DOOR-HDLN, dashed pull handle on A-GENM-HDLN; no frames',
  'a': [9.517, 5.351], 'b': [9.517, 6.051], 'width': 0.70, 'nearestPlace': 'P08', 'distance_m': 0.35,
  'evidence': 'Screen x 9.467-9.567 (two continuous layer-0 lines 0.10 m apart run on past the door); glass lines x 9.512 / 9.522 '
              'stop at y 5.351 (0.10 m stub from the wall face y 5.251) and restart at y 6.051 (fixed pane to y 6.950). Ends given '
              'at the glass ends (leaf convention); measured from the wall face y 5.251 it would be 0.80 m with a 0.10 m sidelight.'},
 {'id': 'N2', 'isOpening': 'yes', 'kind': 'door',
  'subtype': 'glass swing door in the 10 mm glass screen of the room east of the BOH (shower door): 0.70 m glass leaf hinged at the '
             'west end (23.002, 4.780), drawn open 30 deg to the north, dashed swing on A-DOOR-HDLN, handle on A-GENM-HDLN',
  'a': [23.002, 4.775], 'b': [23.702, 4.775], 'width': 0.70, 'nearestPlace': 'P18', 'distance_m': 1.27,
  'evidence': 'Screen y 4.724-4.824 (continuous layer-0 lines); glass y 4.770-4.780 stops at x 23.002 (0.10 m stub from x 22.902) '
              'and restarts at x 23.702 (fixed pane to x 24.797).'},
 {'id': 'N7', 'isOpening': 'possible', 'kind': 'passage',
  'subtype': 'open side: the dressing area opens along its whole north side into the bedroom foyer; nothing drawn across (no head, '
             'frame or line)',
  'a': [7.554, 3.259], 'b': [9.387, 3.259], 'width': 1.833, 'nearestPlace': 'P21 / P07', 'distance_m': 0.10,
  'evidence': 'The wardrobe\'s north wall (y 3.184-3.334) has a squared free end at x 9.387 (also the bi-fold P07\'s north jamb); '
              'west of it nothing in the line up to the partition x 7.354-7.554, whose pocket-door opening P21 (y 2.234-3.334) meets '
              'this line. Low confidence (0.4): an open side of a nook rather than a gap in a wall; I would count it at most as '
              'optional, like the older keys\' "open side" / "passage mouth" entries.'},
 {'id': 'N8', 'isOpening': 'possible', 'kind': 'passage',
  'subtype': 'open side: the lobby of bedroom 2 (wardrobe on its south side) opens along its whole north side into bedroom 2; '
             'nothing drawn across',
  'a': [20.612, 6.924], 'b': [22.737, 6.924], 'width': 2.125, 'nearestPlace': 'P04 / P18', 'distance_m': 0.10,
  'evidence': 'The wall y 6.854-6.994 (north wall of the room east of the BOH) has a squared free end at x 22.737 (P18\'s north '
              'jamb); west of it nothing stands in the line up to the partition x 20.412-20.612, whose pocket-door opening P04 '
              '(y 6.084-7.184) meets this line. The description calls this open plan ("no walls at all"). Low confidence (0.3), '
              'the same kind of thing as N7: at most optional.'},
]
farther = [
 {'id': 'N3', 'kind': 'door', 'subtype': 'glass swing door in the master-bathroom screen (south shower door), 0.70 m glass leaf hinged '
  'at the south end (9.512, 7.165), drawn open 30 deg west, dashed swing on A-DOOR-HDLN', 'a': [9.517, 7.165], 'b': [9.517, 7.865],
  'width': 0.70, 'nearestPlace': 'P08', 'distance_m': 2.03},
 {'id': 'N4', 'kind': 'door', 'subtype': 'glass swing door in the master-bathroom screen (north shower door), 0.70 m glass leaf hinged '
  'at the north end (9.512, 10.134), drawn open 30 deg west, dashed swing on A-DOOR-HDLN', 'a': [9.517, 9.434], 'b': [9.517, 10.134],
  'width': 0.70, 'nearestPlace': 'P17', 'distance_m': 2.07},
 {'id': 'N5', 'kind': 'door', 'subtype': 'service double swing door (block SERVICE_SWING_DOUBLE - D22 1800X2100MM-V25, insert '
  '(24.887, 1.159)), leaves open 35 deg into the corridor, riser with X behind; the east jamb and part of the second leaf are cut '
  'by the view crop at x 25.079', 'a': [23.987, 1.159], 'b': [25.787, 1.159], 'width': 1.80, 'nearestPlace': 'P02',
  'distance_m': 2.05, 'note': 'east end from the family size (1.80 m); the drawing stops at x 25.079'},
 {'id': 'N6', 'kind': 'door', 'subtype': 'service double swing door (block SERVICE_SWING_DOUBLE - D22 1800X2100MM-2804302, insert '
  '(24.887, 3.259), rot 180), leaves open 35 deg into the corridor, riser with X behind; cut by the crop at x 25.079',
  'a': [23.987, 3.259], 'b': [25.787, 3.259], 'width': 1.80, 'nearestPlace': 'P05', 'distance_m': 2.48,
  'note': 'east end from the family size (1.80 m); the drawing stops at x 25.079'},
]
not_openings_near = [
 {'what': 'curtain-wall bays 3 and 4 (glass walls)', 'nearPlaces': ['P06', 'P20'],
  'why': 'projecting bays glazed with curtain-wall panels and mullions in blocks (A-GLAZ-CURT / A-GLAZ-CWMG), corner wedges on A-WALL, '
  'one solid angled wall each. A glass wall, not an opening by the task\'s definition. Note: the bank key listed in-line curtain-wall '
  'glazing between solid wall ends as optional windows; if that convention is used here, each bay (or each of its 3 facets) would be '
  'an optional window, on the glass line, not at the bay mouth.'},
 {'what': 'mouths of bays 1 and 2 (master bedroom, master bathroom)', 'nearPlaces': ['P17'],
  'why': 'same as P06: the room continues into the bay; nothing spans the mouth.'},
 {'what': 'luggage-rack niche in the west wall of bedroom 2 (A-WALL rounded returns x 20.61-20.79, y 7.54-8.61)', 'nearPlaces': ['P04'],
  'why': 'a recess formed by returns standing proud of the partition; the partition x 20.407-20.612 is continuous behind it.'},
 {'what': 'corridor widening x 17.137-20.437 (north side steps from y 3.309 to 3.659)', 'nearPlaces': ['P11', 'P05'],
  'why': 'a wider stretch of the corridor in front of the bar wall; not a gap in a wall.'},
 {'what': 'closed shaft x 12.01-14.69, y 0.41-1.01 behind the fire-hose cabinet', 'nearPlaces': ['P03'], 'why': 'no door drawn.'},
]

counts = {'real': sum(v['verdict'] == R for v in verdicts), 'notReal': sum(v['verdict'] == N for v in verdicts),
          'unsure': sum(v['verdict'] == 'unsure' for v in verdicts),
          'realWithClaimFullyRight': sum(1 for v in verdicts if v['verdict'] == R and all(v['claimCheck'][k] for k in ('kindRight', 'endsRight', 'widthRight'))),
          'openingsNoticedWithin2m': {'definite': sum(1 for x in nearby if x['isOpening'] == 'yes'),
                                     'possible': sum(1 for x in nearby if x['isOpening'] == 'possible')},
          'openingsNoticedJustBeyond2m': len(farther)}
out = {
 'auditor': 'auditor1',
 'drawing': 'presidential suite_layout.dwg (cache suite_revit)',
 'date': '2026-11-10',
 'inputsUsed': ['audit/places.json', 'audit/places/P01-P24.png', 'WORK/suite_revit/prims.pkl (the flattened plan.dxf) read with '
                'work_auditor1/probe.py', 'description.md', 'pictures/ (INDEX, overview_all, tiles B1, B3, C2, F2)',
                'own pictures in work_auditor1/ (draw_box.py)'],
 'notRead': ['audit/secret_map.json', 'suite_revit.json', 'labels/', 'disputes/', 'parts/', 'README.md of the key folder',
             'audit/make_audit_places.py', 'anything in blind_run_suite_revit/'],
 'conventions': {
  'ends': 'a and b on the wall centre line at the faces of the wall ends that bound the opening (where the wall fill stops), west to '
          'east or south to north as in places.json; door frames inside the opening are not deducted; a glass door in a glass screen is '
          'measured between the glass ends (its leaf), the short fixed glass beside it is screen',
  'opening': 'a gap in a wall, glass partition or curtain wall filled by a door, a window or nothing; the mouth of a recess, alcove or '
             'bay where the room simply continues, open floor, furniture, casework and equipment niches are not openings',
  'coordinates': 'drawing metres (DXF mm / 1000)'},
 'counts': counts,
 'verdicts': verdicts,
 'noticedNearby': nearby,
 'noticedJustBeyond2m': farther,
 'consideredNotOpeningsNearPlaces': not_openings_near,
 'pictures': ['work_auditor1/bath_screen_glass_doors.png', 'work_auditor1/east_room_glass_door_and_lobby.png',
              'work_auditor1/dressing_area_open_side.png'],
}
(HERE.parent / 'verdicts_auditor1.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(counts))
for v in verdicts:
    cc = v['claimCheck']
    print(v['place'], v['verdict'], v.get('kind'), v.get('width'), cc)
