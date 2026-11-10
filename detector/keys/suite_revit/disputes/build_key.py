"""Build the answer key of the suite_revit drawing (held-out test, step 4 of 7) from the three lists and the decided disputes.

Inputs (none edited): ../labels/A.json, B.json, C.json; comparison_full.json (compare_full.py) and suite_revit.json
(tools/three_way.py), both next to this file. Writes:
  ../parts/suite_revit.json   the adjudicated part (openings, glassWalls, uncertain, rejected, method, files), as
                              keys/tower/parts/*.json
  ../spec.json                one part covering the whole plan (drawing.json extent), floor 'suite_revit'
  ../suite_revit.json         the key, made from the spec by tools/combine_keys.py (run as it is), as keys/tower/tower.json
and prints a self-check with tools/score.py (the key against itself, and each list read as a detection file).

Agreed openings keep labeller A's record (as three_way.py does), renumbered SR-nn = A-nn, with the ids of the three lists
in 'lists'. Where the lists differ within tolerance the ends are set as written in ENDS below; the four disputes are
decided in DECIDED / REJECTED (reasons from the drawing, see ../README.md).

Usage (from detector/): python -B keys/suite_revit/disputes/build_key.py
"""
import copy, json, math, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent              # keys/suite_revit/disputes
KEY = HERE.parent                                   # keys/suite_revit
DET = KEY.parents[1]                                # detector
LAB = KEY / 'labels'
FLOOR = 'suite_revit'                               # drawing.json floor_tag (= the cache's area tag, see README)
BOX = [1.569, 0.008, 25.079, 13.084]                # drawing.json extent_m

A = json.load(open(LAB / 'A.json', encoding='utf-8'))
B = {o['id']: o for o in json.load(open(LAB / 'B.json', encoding='utf-8'))['openings']}
C = {o['id']: o for o in json.load(open(LAB / 'C.json', encoding='utf-8')) if o.get('floor') == FLOOR}
CMP = json.load(open(HERE / 'comparison_full.json', encoding='utf-8'))
TW = json.load(open(HERE / 'suite_revit.json', encoding='utf-8'))
assert len(TW['accepted']) == 41 and len(TW['disputes']) == 3, 'three_way output changed: re-read it before building'

lists_of = {c['ids']['A']: c['ids'] for c in CMP['list'] if 'A' in c['ids']}


def sr(text):
    """A's ids in A's own texts -> the key's ids (SR-nn = A-nn)."""
    return re.sub(r'\bA-(\d\d)\b', r'SR-\1', text)


def w(o): return round(math.dist(o['a'], o['b']), 4)


AGREED = 'A, B and C agree (kind, optional flag, ends within 5 cm; the ends are the same in the three lists)'

# ---- agreed openings whose ends differ within tolerance between the lists: which ends the key takes, and why
WEDGE = ('A, B and C agree (kind window, optional, ends within 5 cm). Ends: A ran 0.05 m past each end of the pane into the '
         'corner wedges (A-WALL, block Walls 13); B and C (identical) end at the wedge faces, where the pane and its mullion '
         'lines end (checked: west bay wedge y 4.0298-4.1005 and 7.6177-7.6884, pane and mullion fill from y 4.1005 to 7.6177; '
         'north bay 1 wedge face (4.0546, 12.3494)-(4.1046, 12.2628), pane from (4.0771, 12.3105)). The key takes B and C\'s '
         'ends: the faces of the bounding wall material, as all three lists have for facets 1 and 3 of every bay.')
ENDS = {
    'A-26': ('B', WEDGE), 'A-29': ('B', WEDGE), 'A-32': ('B', WEDGE), 'A-35': ('B', WEDGE), 'A-38': ('B', WEDGE),
    'A-41': ('B', WEDGE),
    'A-05': ('A', 'A, B and C agree (kind, optional flag, ends within 5 cm). Ends as A and C: the fill 51B3 starts at '
                  'y 4.6980; B took the drawn end line A634 / frame end at y 4.6974 (0.6 mm, a drawing artefact).'),
    'A-20': ('B', 'A, B and C agree (kind, optional flag, ends within 5 cm). Ends as B and C: the glass end line 510E at '
                  'y 7.8655; A took the end of the glass side lines 4FB0 / 4FB1 at y 7.8654 (0.1 mm).'),
}
WEDGE_EVIDENCE = ('; a/b = the pane ends, which lie on the faces of the A-WALL corner wedges (block Walls 13) at both ends; '
                  'the 50 x 100 mullion boxes at these corners belong to the neighbouring facets (key ends as lists B and C; '
                  'A had the pane ends + 0.05 m, inside the wedges).')

# ---- the disputes that stay in the key (decided from the drawing)
DECIDED = {
    'A-19': dict(optional=True, agreement='decided', decision=(
        'DISPUTE (optional flag: A and B optional, C scored). Decided OPTIONAL from the drawing. The door stands in the '
        'master bathroom\'s glass screen, not in a wall: 10 mm glass on layer 0 (lines x 9.5116 / 9.5216) between two '
        '0.10 m layer-0 kerb lines (4EE8 x 9.4666, 4EE5 x 9.5666) that run on unbroken past the door; the glass stops at '
        'y 5.3507 and restarts at y 6.0507 (the 0.70 m leaf). It is drawn exactly like the two shower doors on the same '
        'screen line (SR-20, SR-21): 10 mm glass leaf open 30 deg (A-DOOR 5A8D / 5A8F), dashed 30 deg swing on A-DOOR-HDLN '
        '(5A91), handle outline on A-GENM-HDLN, no A-DOOR-FRAM frame (every hinged and pocket door in a wall has 4 to 18 '
        'frame lines within 0.12 m; only the bi-fold and the four glass-screen doors have none), and it '
        'is one of the four exploded copies of the same unused shower-door family (IN_SHOWER DOOR1 - Shower '
        'door_700X2160MM). The compartment behind it (x 9.57-11.49, y 5.25-6.94) holds only the WC: an enclosure inside the '
        'master bathroom. The earlier keys list a shower screen as a glass wall with its door part of the enclosure '
        '(Sukhumvit, shared definition of 26 Oct) and toilet cubicle doors as optional (tower), and the three lists agree '
        'that the other three doors of these screens are optional; so this one is optional too (not scored either way). '
        'Ends as all three lists (the gap in the glass, 0.70 m). If the 3D team wants doors in glass screens scored, '
        'set optional false here (and on SR-20 to SR-22); the ends need no change.')),
    'A-24': dict(ends='B', agreement='decided', decision=(
        'DISPUTE (ends 0.070 m apart: A on y 6.9941, B and C on y 6.9241; same x ends, same kind, optional in all three). '
        'Decided from the drawing: the wall whose end bounds the mouth is the layer-0 fill 51FC, x 22.7366-24.7866, '
        'y 6.8541-6.9941 (0.14 m, lining lines at y 6.8691 / 6.9691); its centre line is y 6.9241, and A\'s y 6.9941 is '
        'its north face. The convention (A\'s own too) puts a/b on the wall centre line, so the key takes y 6.9241 (= B '
        'and C). Ends: x 20.6116 (face of the partition x 20.4116-20.6116, which holds the pocket door SR-11 at this '
        'height) and x 22.7366 (end of 51FC); 2.125 m. Optional passage mouth into open space, as all three lists.')),
}

REJECTED_DECIDED = [
    {'id': 'C-40 (C only)', 'where': [19.674, 1.159], 'lists': 'listed by C (optional passage); rejected by A (R-02) and B (R-03)',
     'reason': ('DISPUTE decided: not an opening. The corridor\'s south wall (A-WALL fill 5421, y 1.1091-1.2091) turns south '
                'at x 18.9866 (side wall 5410, x 18.9866-19.0866, down to y 0.8091) and resumes only at the column x '
                '20.2616-20.7616 (S-COLS, north face flush at y 1.2091): between them a recess 1.175 m wide and 0.30 m deep '
                '(to the wall y 0.8091-0.9091) with the unit door SR-15 at its back. Nothing is drawn across the mouth on any '
                'layer (a query of every cache item in x 19.10-20.25, y 0.95-1.22 finds none: no head, threshold, frame or '
                'leaf). The recess is the corridor\'s space in front of the door and the opening is the door at its back, '
                'which the key scores (SR-15). Same call as the older keys: presidential R5 (the mouth of the alcove in front '
                'of D4: D4 at the back of the alcove is the opening) and g-west R-02. C itself calls it "the mouth of a recess '
                'in front of a door, not an opening of its own". Close-up: disputes/work/d23_corridor_alcove.png.')},
    {'id': 'C-43 (C only)', 'where': [21.349, 1.159], 'lists': 'listed by C (optional passage); rejected by A (R-03) and B (R-03)',
     'reason': ('DISPUTE decided: not an opening, for the same reasons as C-40: the recess x 20.7616-21.9366 between the '
                'column\'s east face and the side wall 5413 (x 21.9366-22.0366, y 0.8091-1.2091; the corridor wall resumes '
                'from x 22.0366), 0.30 m deep, with the unit door SR-16 at its back; nothing drawn across the mouth (query of '
                'x 20.77-21.93, y 0.95-1.22: no item).')},
]

# the places the lists rejected (merged; the two corridor-alcove mouths are the decided entries above)
REJECTED_LISTS = [
    ('R-01', [14.287, 1.11], 'A R-01, B R-02, C', 'Gap x 13.887-14.687 in the 0.20 m corridor / shaft wall (A-WALL 540F, y 1.009-1.209): the fire-hose cabinet (block FHC 02 - Type 1, M-EQPM, x 13.89-14.69, y 0.86-1.21; text FHC) stands in it. A cabinet recess, not an opening.'),
    ('R-04', [20.7, 8.07], 'A R-04, B R-05, C', 'Niche x 20.612-20.787, y 7.537-8.607 in bedroom 2\'s west wall (rounded A-WALL returns 58C7/58C8) holding the slatted luggage rack (Q-CASE): blind, the partition 51B9 (x 20.407-20.612) runs on behind it.'),
    ('R-05', [15.31, 4.42], 'A R-05, B R-01, C', 'Closed space x 15.137-15.512, y 3.784-5.061 behind a single layer-0 line on the foyer\'s east side (x 15.112): built-in cupboard or duct; no door symbol, enclosed on all sides.'),
    ('R-06', [18.04, 5.21], 'A R-06, B R-10, C', 'North side of the bar, x 15.662-20.412: open plan to the living and dining area (4.75 m, no wall end at a door-wide distance); not a passage.'),
    ('R-07', [21.66, 5.73], 'A R-07, B R-07, C', 'Wardrobe of the lobby of bedroom 2 (x 20.61-22.71, y 5.43-6.03, hanging rails, front line y 6.034) and the wardrobes of the master bedroom (front y 0.959), walk-in wardrobe rails, mini-bars, TV and shelving units: casework.'),
    ('R-08', [15.73, 6.43], 'A R-08, B R-08, C', 'Furniture fills on layer 0 (sofa back 4FF1, SOLID 4FD2, sofa frame 502C) and furniture arcs on A-GENM / I-FURN (beds, round tables), the fridge door (Q-SPCQ arc r 0.5): not walls, no openings.'),
    ('R-09', [17.1, 3.43], 'A R-09, B R-04, C', 'Corridor widening x 17.137-20.437 (north face at y 3.659 instead of 3.209-3.309): the corridor\'s own width, a wall jog, not an opening.'),
    ('R-10', [9.52, 8.65], 'A R-10, C', 'Fixed glass of the bathroom screens beside the glass doors and the shower\'s north pane (see glassWalls): glass walls, not windows.'),
    ('R-11', [12.85, 0.71], 'A R-11, B R-09, C', 'Shaft x 12.012-14.687, y 0.409-1.009 (A-WALL 0.20 m walls) and the risers behind the four service doors: closed, no further door.'),
    ('R-12', [25.079, 7.0], 'A R-12', 'Walls cut by the view crop at x 25.079 (y 0.66-0.76, 3.66-3.76, 11.41-11.51) and y 0.009 (x 15.89-16.19, 20.41-20.61, 24.84-24.94): crop ends, not openings.'),
    ('R-13', [7.86, 11.4], 'A R-13, B R-06', 'Break x 7.787-7.937 in the 25 mm facade lining (4DE4 / 4DC5) on the bathroom side: lining only, the A-WALL facade 53F7 runs on behind it.'),
    ('R-14', [23.39, 3.6], 'C', 'Box x 22.90-23.87, y 3.42-3.77 at the south-west corner of the room east of the BOH (single layer-0 lines A625 / A626): a 0.35 m recess or bench, no gap in a wall.'),
    ('R-15', [5.6, 11.46], 'C (B R-10 in part)', 'Bay mouths on the facade line (one per bay), where a room runs on into its projecting curtain-wall bay: no wall across the mouth; the glazing is listed per facet (SR-25 to SR-42).'),
]

UNCERTAIN = [
    {'where': [9.5166, 5.7007], 'what': 'SR-19, the glass door of the WC compartment, is optional (dispute decided: a door of the bathroom glass screen, drawn as the shower doors). If the 3D team wants doors in glass screens scored regardless of the room, set optional false on SR-19 to SR-22 (ends 0.70 m by the leaf need no change); then the key has 20 scored openings.'},
    {'where': [19.7, 2.2], 'what': 'Doors outside the suite: the four corridor doors SR-13 to SR-16 (two riser doors, two doors of neighbouring units) are scored, as all three lists did (like the tower key\'s shaft doors); SR-17 / SR-18 are optional because the view crop cuts them. If the key is meant to cover the suite only, SR-13 to SR-16 become optional (12 scored openings).'},
    {'where': [24.887, 2.2], 'what': 'SR-17 / SR-18: the two D22 service double doors at the east edge are cut by the crop at x 25.079; only 1.092 m of each 1.80 m opening is drawn. The key keeps the nominal 1.80 m (centre at the block insert point); a detector can only see x 23.987-25.079. Optional either way.'},
    {'where': [9.4616, 2.0716], 'what': 'SR-03, the bi-fold door of the walk-in wardrobe (2.225 m, the full wall gap; the dashed track spans the same), is scored as a room door by all three lists. If walk-in wardrobes are read as casework it would be optional.'},
    {'where': [5.0, 12.4], 'what': 'Curtain-wall bays: listed per straight facet as 18 optional windows (all three lists), ends at the wall material that bounds each facet (straight facade wall ends, Walls 13 corner wedges, angled solid walls). Other readings: one window per bay (e.g. north bay 1 chord (3.8475, 11.4961)-(6.1244, 12.8110), west bay x 2.797 from y 2.894 to 8.824) or glass wall only (the tower key). None is scored either way.'},
    {'where': [10.0, 10.0], 'what': 'Width convention: every door is measured between the faces of the wall ends with the 50 mm A-DOOR-FRAM frames inside the opening (1.10 for the pocket doors, 0.80 / 0.75 / 1.00 for the hinged ones). The clear width between the frames is 0.10 m less (0.05 m less for SR-06), which for the 0.80 m and 1.00 m doors (SR-05, SR-09, SR-10, SR-12, SR-15, SR-16) is exactly the scorer\'s width limit (max(0.10 m, 10 %)): a detection measured between the frames passes or fails there on rounding.'},
    {'where': [20.5, 1.0], 'what': 'The corridor-alcove mouths (C-40, C-43) are rejected. A passage detected at a mouth is an extra; if the unit door behind it (SR-15 / SR-16) is not detected, the scorer pairs the door with such a passage (centres exactly 0.30 m apart, its centre limit) and fails it on width (1.175 vs 1.00).'},
    {'where': [8.47, 3.26], 'what': 'SR-23 and SR-24 (open sides of the dressing area and of the lobby of bedroom 2) are optional passage mouths: a wall end facing a cross wall that holds a pocket door at that point. They could also be read as no opening at all.'},
    {'where': [12.0866, 3.2591], 'what': 'SR-06 (small room south of the foyer): 0.75 m between the wall fills, but the frame on its east side stands 0.05 m inside the wall stub; leaf 0.70. Lists agree on 0.75.'},
    {'where': [1.0, 0.0], 'what': 'Floor tag: the key\'s floor is \'suite_revit\' (drawing.json floor_tag; tools/prims.py tags every item of this one-plan drawing with the cache name). The detector writes each opening\'s floor as the name the mapping\'s "floors" entry gives the area \'suite_revit\' (openings.py run()). The mapping lies in the blind-run folder, which this step does not read; if it names the floor differently, rename the key\'s floor (or the output\'s) before scoring, since score.py pairs per floor string.'},
]

GLASS_EXTRA_NOTE = ' (key ids SR-nn = A-nn)'


def main():
    ops = []
    for o in A['openings']:
        aid = o['id']
        k = {kk: copy.deepcopy(v) for kk, v in o.items() if kk != 'floor'}
        k['id'] = 'SR-' + aid.split('-')[1]
        k['evidence'] = sr(k.get('evidence', ''))
        k['notes'] = sr(k.get('notes', ''))
        ids = lists_of[aid]
        k['lists'] = {n: ids.get(n) for n in 'ABC'}
        k['agreement'] = 'all three'
        k['decision'] = AGREED
        if aid in ENDS:
            src, why = ENDS[aid]
            ref = {'A': o, 'B': B[ids['B']]}[src]
            k['a'], k['b'] = list(ref['a']), list(ref['b'])
            k['decision'] = why
            if why is WEDGE:
                k['evidence'] = re.sub(r'; a/b = pane ends \+0\.05 m \(the mullion / joint at each end\)\.?$', '', k['evidence']) + WEDGE_EVIDENCE
        if aid in DECIDED:
            d = DECIDED[aid]
            if d.get('ends') == 'B':
                k['a'], k['b'] = list(B[ids['B']]['a']), list(B[ids['B']]['b'])
            if 'optional' in d: k['optional'] = d['optional']
            k['agreement'] = d['agreement']
            k['decision'] = d['decision']
        k['width'] = w(k)
        if not k.get('optional'): k.pop('optional', None)
        ops.append(k)
    # sanity: every cluster of the comparison is either in the key or rejected
    in_key = {k['lists']['C'] for k in ops} | {k['lists']['B'] for k in ops}
    assert len(ops) == 42 and all(c['ids'].get('C') in in_key or c['ids'].get('C') in ('C-40', 'C-43') for c in CMP['list'])

    glass = []
    for g in A['glassWalls']:
        glass.append({**g, 'notes': sr(g['notes'])})
    rejected = REJECTED_DECIDED + [{'id': f'R-{n:02d}', 'where': wh, 'lists': ls, 'reason': sr(r)}
                                   for n, (_, wh, ls, r) in enumerate(REJECTED_LISTS, 1)]     # renumbered R-01.. in this order
    method = (
        'Answer key of presidential suite_layout.dwg (Revit export, 3D team, 9 Nov 2026; cache suite_revit, drawing metres), '
        'held-out test step 4 of 7, made without any detector output. Inputs: three independent lists in ../labels/ (A '
        'geometry first, 42 entries; B pictures first, 42; C a geometry-only inventory without pictures, 44). Comparison '
        'with the scorer\'s matching (tools/score.py match, pairwise, joined transitively): tools/three_way.py as it is '
        '(A and B as the two labellers, C as the inventory, floor suite_revit, box = drawing extent) -> disputes/suite_revit.json '
        '(41 accepted, 3 disputes); compare_full.py checks every cluster across all three lists on presence, kind, optional '
        'flag, ends (5 cm) and width (scorer tolerance) -> disputes/comparison_full.json: 44 clusters, 40 agreed, 4 disputes '
        '(three_way does not compare the optional flag, which adds the WC door). No subtype dispute: the subtypes name the '
        'same door types in other words. Each dispute was decided from the drawing (cache queries with disputes/work/q.py, '
        'close-ups in disputes/work/ drawn with scripts/zoom.py, the description and pictures), not by majority: the WC '
        'glass door optional, the two corridor-alcove mouths rejected, the lobby mouth on the wall centre line. Agreed '
        'openings stand as agreed (labeller A\'s record, as three_way.py takes it), renumbered SR-nn = A-nn; where the lists '
        'differ within tolerance the ends are those two lists share and the drawing supports (bay facets 2: B and C, at the '
        'corner-wedge faces; SR-05: A and C; SR-20: B and C). No opening was added that no list has and no agreed opening '
        'was re-judged. Conventions (the earlier keys\'): a/b on the wall centre line at the faces of the wall ends, frames '
        'inside the opening included; doors in glass screens by the leaf; passage mouths into open space, doors cut by the '
        'view crop, doors of shower / WC glass screens and fixed curtain-wall facets optional. Result: 16 scored (15 doors, '
        '1 passage) and 26 optional (6 doors, 2 passages, 18 windows).')
    files = ['keys/suite_revit/disputes/suite_revit.json', 'keys/suite_revit/disputes/comparison_full.json',
             'keys/suite_revit/disputes/compare_full.py', 'keys/suite_revit/disputes/build_key.py',
             'keys/suite_revit/disputes/work/q.py', 'keys/suite_revit/disputes/work/mark_key.py',
             'keys/suite_revit/disputes/work/*.png', 'keys/suite_revit/spec.json', 'keys/suite_revit/suite_revit.json']
    part = {'part': 'suite_revit', 'floor': FLOOR, 'box': BOX, 'units': 'drawing metres (DXF mm / 1000)', 'openings': ops,
            'glassWalls': glass, 'uncertain': UNCERTAIN, 'rejected': rejected, 'method': method, 'files': files}
    (KEY / 'parts').mkdir(exist_ok=True)
    (KEY / 'parts' / 'suite_revit.json').write_text(json.dumps(part, indent=1, ensure_ascii=False), encoding='utf-8')
    spec = {'parts': [{'file': 'keys/suite_revit/parts/suite_revit.json', 'floor': FLOOR, 'box': BOX, 'own': BOX}]}
    (KEY / 'spec.json').write_text(json.dumps(spec, indent=1) + '\n', encoding='utf-8')

    py = sys.executable
    r = subprocess.run([py, '-B', 'tools/combine_keys.py', 'keys/suite_revit/spec.json', 'keys/suite_revit/suite_revit.json'],
                       cwd=str(DET), capture_output=True, text=True)
    print(r.stdout.strip(), r.stderr.strip())
    key = json.load(open(KEY / 'suite_revit.json', encoding='utf-8'))
    sc = [o for o in key['openings'] if not o.get('optional')]
    op = [o for o in key['openings'] if o.get('optional')]
    by = lambda L: {k: sum(1 for o in L if o['kind'] == k) for k in ('door', 'window', 'passage')}
    print('key:', len(key['openings']), 'openings; scored', len(sc), by(sc), '; optional', len(op), by(op),
          '; floors', sorted({o['floor'] for o in key['openings']}))

    # self-check with the scorer: the key read as a detection file, and each list read as one
    work = HERE / 'work'
    checks = {'key itself': key['openings'],
              'list A': A['openings'], 'list B': list(B.values()),
              'list C': [dict(o, kind=o['kind'].rstrip('?')) for o in C.values()]}
    for name, dets in checks.items():
        p = work / '_selfcheck_det.json'
        p.write_text(json.dumps({'openings': [dict(o, floor=FLOOR) for o in dets]}), encoding='utf-8')
        r = subprocess.run([py, '-B', 'tools/score.py', 'keys/suite_revit/suite_revit.json', str(p), '--quiet'],
                           cwd=str(DET), capture_output=True, text=True)
        print(f'score.py, {name} as detections:', r.stdout.strip().splitlines()[-2].strip())
        p.unlink()


if __name__ == '__main__':
    main()
