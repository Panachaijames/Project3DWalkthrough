"""Why the frozen detector missed what it missed on `presidential suite_layout.dwg` (held-out run, step 7 of 7).

  OPENINGS_DATA=<WORK> python -B blind_run_suite_revit/diagnosis/diagnose.py [what ...]     (Git Bash, from detector/)

Changes nothing: it imports the frozen detector (../frozen_code, the files the held-out run used), runs the same steps
as openings.run() on the same mapping and cache, checks that the openings it gets are those of the held-out output
(compared in the program; nothing of that file is printed), and then prints what the detector's own intermediate
results say at each key opening that is not right and at each extra: the wall solid along the opening, the wall-layer
line work and fills that close it, the gaps the detector found there and what it made of them, the swings.

what: any of  reproduce  key  extras  found  (default: all)
The printed output of the run of 10 Nov 2026 is kept in diagnose_output.txt. <WORK> is the folder that holds
suite_revit/prims.pkl (the drawing cache, made as in "Run it" of ../../README.md; it is not kept in the project).
"""
import json, math, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RUN = HERE.parent
DETECTOR = RUN.parent
sys.path.insert(0, str(RUN / 'frozen_code'))
import openings as D                            # noqa: E402  the frozen detector
from geomkit import *                           # noqa: E402,F401,F403
from shapely.geometry import LineString, Point  # noqa: E402

MAPPING = RUN / 'mappings_first_run' / 'suite_revit.json'
HELD_OUT = RUN / 'output_first_mapping' / 'suite_revit.json'
KEY = DETECTOR / 'keys' / 'suite_revit' / 'suite_revit_audited.json'
SCORE = RUN / 'score_first_mapping_audited.json'


def setup(drop=()):
    """The same steps as openings.run(), keeping the floor object.
    drop: handles of drawing items to leave out (whatif.py only: a test on a copy of the items, never the held-out run)."""
    mp = json.loads(MAPPING.read_text(encoding='utf-8'))
    Dc = D.prims.load(mp['cache'])
    scale = D.UNITS[mp.get('units', 'mm')]
    roles = role_matcher(mp['layers'])
    (area, floor_name), = mp['floors'].items()
    items = [d for d in Dc['items'] if d.get('area') == area and d.get('h') not in drop]
    if scale != 1.0: items = [D.scaled(d, scale) for d in items]
    items = dedupe(items)
    fl = D.Floor(floor_name, items, Dc['layers'], roles, 1.0)
    ops = D.detect_floor(fl)
    res = D.finish(fl, ops, floor_name)
    return fl, ops, res


def f3(p): return '(%.3f, %.3f)' % (p[0], p[1])
def iv3(iv): return '[' + ', '.join('%.3f-%.3f' % (a, b) for a, b in iv) + ']'


def wall_sources(fl, a, b, lat):
    """Wall / column-layer items (the wall solid's raw material) inside the box a->b +- lat: fills, closed outlines, and
    straight segments running along the opening, with how much of the opening each covers."""
    u = unit(sub(b, a)); w = math.dist(a, b)
    bx = rect(a, u, 0.0, w, -lat, lat)
    rows = []
    for p in fl.P:
        if not (p.roles & {'wall', 'column'}): continue
        d = p.d
        if 'loops' in d:
            g = even_odd(d['loops'])
            if g.is_empty or not g.intersects(bx): continue
            x0, y0, x1, y1 = g.bounds
            ss = [dot(sub(q, a), u) for q in g.exterior.coords] if g.geom_type == 'Polygon' else [0, 0]
            inter = g.intersection(bx).area
            if inter < 1e-5: continue
            rows.append(f"    FILL {p.lay} h={p.h} bounds x {x0:.3f}-{x1:.3f} y {y0:.3f}-{y1:.3f} (mean width {mean_width(g):.3f}); "
                        f"covers {inter:.4f} m2 of the opening box, along it {max(min(ss), 0):.3f}-{min(max(ss), w):.3f}")
            continue
        if not p.pts: continue
        if p.poly is not None and p.poly.intersects(bx):
            x0, y0, x1, y1 = p.poly.bounds
            rows.append(f"    CLOSED {p.t} {p.lay} h={p.h} lt={p.lt} cont={p.cont} bounds x {x0:.3f}-{x1:.3f} y {y0:.3f}-{y1:.3f} "
                        f"mean width {mean_width(p.poly):.3f} -> {'wall piece' if (max(x1 - x0, y1 - y0) >= 0.15 and mean_width(p.poly) <= 0.35) else 'not a wall piece'}")
        pts = simplify_pts(p.pts) if p.t != 'ARC' else p.pts
        for q0, q1 in zip(pts, pts[1:]):
            if math.dist(q0, q1) <= 0.02: continue
            s0, l0 = dot(sub(q0, a), u), dot(sub(q0, a), perp(u))
            s1, l1 = dot(sub(q1, a), u), dot(sub(q1, a), perp(u))
            if abs(l0 - l1) > 0.02 or max(abs(l0), abs(l1)) > lat: continue          # along the opening only
            lo, hi = max(min(s0, s1), 0.0), min(max(s0, s1), w)
            if hi - lo < 0.05: continue
            rows.append(f"    LINE along {p.t} {p.lay} h={p.h} lt={p.lt} cont={p.cont} offset {((l0 + l1) / 2):+.3f} "
                        f"from {min(s0, s1):+.3f} to {max(s0, s1):+.3f} (opening 0-{w:.3f}): covers {100 * (hi - lo) / w:.0f} %"
                        + ('' if p.cont else '  [not continuous: not wall material]'))
    return rows


def explain_passage(fl, g):
    """passage_ok() of the frozen code, step by step (the same calls in the same order) -> list of lines."""
    out = []
    fr = D.framed(fl, g)
    out.append(f"      frame drawn (door-layer lines across the wall at both ends): {fr}")
    if g.near == 'T' or g.t < 0.07: return out + [f"      -> NO: near end {g.near}, thickness {g.t:.3f} (T or under 0.07)"]
    if max(g.nlen, g.flen) < 0.3 and not (fr or (g.near == 'cap' and g.how_end == 'collinear strip' and g.w <= 1.6 + D.EPS and
                                                 D.attached_to_wall(fl, g.at(-0.02)) and D.attached_to_wall(fl, g.at(g.w + 0.02)))):
        return out + [f"      -> NO: stub to stub (wall ends {g.nlen:.3f} / {g.flen:.3f} m, under 0.3) and no frame / own wall ends"]
    run = fl.G.cover(sub(g.b, mul(g.u, 0.005)), g.u, 0.5)
    far_run = run[0][1] if run and run[0][0] <= 0.01 else 0.0
    out.append(f"      wall carries on past the far end for {far_run:.3f} m (looked 0.5 m)")
    if g.far == 'end':
        lim = 3.6 if g.near == 'cap' else 2.75
        if not (0.6 - D.EPS <= g.w <= lim + D.EPS): return out + [f"      -> NO: width {g.w:.3f} outside 0.6-{lim} (far end = wall end)"]
        if g.near == 'L' and far_run < 0.2: return out + ["      -> NO: L-corner and the wall does not carry on 0.2 m past the far end"]
    elif g.far == 'face':
        if not (0.6 - D.EPS <= g.w <= 1.6 + D.EPS) or far_run < 0.3:
            return out + [f"      -> NO: far end is a wall face: width {g.w:.3f} must be 0.6-1.6 m and the wall must carry on 0.3 m (it does {far_run:.3f})"]
    else:
        return out + [f"      -> NO: far end is a {g.far} (neither a wall end nor a flat face)"]
    for p in (g.at(-0.02), g.at(g.w + 0.02)):
        if D.is_free_post(fl, p): return out + [f"      -> NO: free-standing post at {f3(p)}"]
    if D.crosses_stair(fl, g): return out + ["      -> NO: stair lines in the gap"]
    runs = D.face_runs(fl, g)
    across = [(face, s0, s1) for face, r in runs.items() for s0, s1 in r if s0 <= D.FACE_TOL + D.EPS and s1 >= g.w - D.FACE_TOL - D.EPS]
    out.append(f"      wall-solid faces along the gap's two faces: left {iv3(runs[1])}, right {iv3(runs[-1])} (gap 0-{g.w:.3f})")
    if across: out.append(f"      a face of the wall solid runs unbroken across the gap: {across}")
    face, lo, hi = D.far_face(fl, g)
    out.append(f"      far face met by the centre line: {face}; the far material stands out {lo:.3f} / {hi:.3f} m past the two faces")
    ok = D.interrupts_wall_line(fl, g, fr)
    if not ok: return out + ["      -> NO: does not interrupt a wall line (a mouth, or a wall face drawn across)"]
    if D.closed_by_glass(fl, g): return out + ["      -> NO: glazing along the gap close behind it (a recess against a glass wall)"]
    res = D.passage_ok(fl, g)
    return out + [f"      -> passage_ok = {res}"]


def gaps_near(fl, a, b, reach=0.45):
    """Gaps of the detector (after its own T filter) that overlap the opening a->b or lie within reach of it."""
    u = unit(sub(b, a)); w = math.dist(a, b)
    out = []
    for g in fl.gaps:
        if ang_diff(g.u, u) > 20: continue
        m = g.at(g.w / 2)
        s, l = dot(sub(m, a), u), dot(sub(m, a), perp(u))
        if abs(l) > reach or s < -g.w / 2 - 0.2 or s > w + g.w / 2 + 0.2: continue
        out.append(g)
    return out


def describe_gap(fl, g):
    rows = [f"    GAP {f3(g.a)} -> {f3(g.b)} w {g.w:.3f} t {g.t:.3f} near '{g.near}' far '{g.far}' ({g.how_end or 'by profile'}) "
            f"wall ends {g.nlen:.3f} / {g.flen:.3f} m"]
    rows.append(f"      swings {len(g.swings)}, glazing bands {len(g.bands)} (+{len(g.through)} running on), panels {g.panels}, "
                f"frame pieces inside {len(g.jambs)}, read as: {g.kind or 'nothing'} {g.sub} {g.ev}")
    if not g.kind and not g.swings and not g.bands and not g.through:
        if any(p[0] in ('sliding panel', 'pocket panel', 'closed leaf', 'low wall', 'pocket line') for p in g.panels) or len(g.jambs) >= 2:
            rows.append('      (has contents: not judged as a passage)')
        elif D.screened(fl, g):
            rows.append('      closed by a screen layer')
        else:
            rows += explain_passage(fl, g)
    return rows


def swings_near(fl, a, b, reach=1.3):
    m = mul(add(a, b), 0.5)
    rows = []
    for hyps in fl.swings:
        h = hyps[0]
        if math.dist(h.c, m) > reach + math.dist(a, b) / 2: continue
        used = any(x.used for x in hyps)
        leaf = [bool(x.leaf) for x in hyps]
        rows.append(f"    SWING arc on {h.p.lay} lt={h.p.lt} centre {f3(h.c)} r {h.r:.3f} sweep {h.sweep:.1f} ends {f3(h.p.arc['e0'])} {f3(h.p.arc['e1'])} "
                    f"leaf found for the two readings {leaf}; used in an opening: {used}")
        if not used:
            pick = D.pick_swing(hyps, fl.OB)
            if pick is None: rows.append('      free swing: which end is the closed leaf is undecided (no leaf found, or a tie) -> no door from the symbol')
            elif not pick.leaf: rows.append('      free swing: no leaf drawn toward the open end -> no door from the symbol')
            elif not (0.45 - D.EPS <= pick.r <= 1.6 + D.EPS and 25 <= pick.sweep <= 110): rows.append('      free swing: radius or sweep outside the symbol-door limits')
            else:
                o = D.symbol_door(fl, pick)
                rows.append(f"      free swing: symbol_door -> {None if o is None else (o['kind'], f3(o['a']), f3(o['b']), o['ev'])}")
    return rows


def door_lines(fl, a, b, lat=0.45):
    """Door-layer line work at the opening (leaves, frames, arrows): count and the long lines along it."""
    u = unit(sub(b, a)); w = math.dist(a, b)
    bx = rect(a, u, -1.3, w + 1.3, -lat, lat)
    n_lines, n_closed, along = 0, 0, []
    for p in fl.P:
        if 'door' not in p.roles or not p.pts: continue
        if not LineString(p.pts).intersects(bx): continue
        n_lines += 1
        if p.poly is not None: n_closed += 1
        if p.t == 'ARC': continue
        for q0, q1 in zip(p.pts, p.pts[1:]):
            L = math.dist(q0, q1)
            if L < 0.4: continue
            s0, l0 = dot(sub(q0, a), u), dot(sub(q0, a), perp(u))
            s1, l1 = dot(sub(q1, a), u), dot(sub(q1, a), perp(u))
            if abs(l0 - l1) <= 0.02 and max(abs(l0), abs(l1)) <= lat:
                along.append(f"{p.lay} {p.t}{' closed' if p.poly is not None else ''} offset {((l0 + l1) / 2):+.3f} from {min(s0, s1):+.3f} to {max(s0, s1):+.3f}")
    return [f"    door-layer items near: {n_lines} ({n_closed} closed outlines); long lines along the opening: {along or 'none'}"]


def at_opening(fl, name, a, b, t_guess=0.2):
    u = unit(sub(b, a)); w = math.dist(a, b); n = perp(u)
    print(f"\n=== {name}: {f3(a)} -> {f3(b)}, w {w:.3f}")
    for lat in (-0.05, 0.0, 0.05):
        iv = fl.G.cover(add(a, mul(n, lat)), u, w)
        cov = sum(y - x for x, y in iv)
        print(f"    wall solid along the opening at offset {lat:+.2f}: {iv3(iv)} = {100 * cov / w:.0f} % of it")
    sec = fl.G.section(add(a, mul(u, w / 2)), n, 0.6)
    print(f"    wall solid across the middle of the opening (offsets): {iv3(sec)}")
    for r in wall_sources(fl, a, b, 0.16): print(r)
    gs = gaps_near(fl, a, b)
    if not gs: print('    no gap found by the detector on this line')
    for g in gs:
        for r in describe_gap(fl, g): print(r)
    for r in swings_near(fl, a, b): print(r)
    for r in door_lines(fl, a, b): print(r)


def main():
    what = set(sys.argv[1:]) or {'reproduce', 'key', 'extras', 'found'}
    fl, ops, res = setup()
    print(f"frozen detector on {MAPPING.name}: {len(res)} openings, {fl.T['total']:.1f} s; wall solid {len(fl.G.parts)} parts, "
          f"{len(fl.strips)} strips, {len(fl.gaps)} gaps (T ends left out), {len(fl.swings)} swing arcs, {len(fl.bands)} glazing bands")
    if 'reproduce' in what:
        held = json.loads(HELD_OUT.read_text(encoding='utf-8'))['openings']
        same = held == json.loads(json.dumps(res))
        print(f"the openings of this run are those of the held-out output ({HELD_OUT.parent.name}/{HELD_OUT.name}): {same}")
        if not same: print(f"  DIFFERENT: {len(held)} held out, {len(res)} here")
    key = {o['id']: o for o in json.loads(KEY.read_text(encoding='utf-8'))['openings']}
    sc = json.loads(SCORE.read_text(encoding='utf-8'))['floors'][fl.name]
    det = {o['id']: o for o in res}
    if 'key' in what:
        print('\n################ key openings the detector missed')
        for m in sc['missed']:
            k = key[m['key']]
            at_opening(fl, f"{k['id']} {k['kind']} ({k.get('subtype', '')}) MISSED", tuple(k['a']), tuple(k['b']))
        print('\n################ key openings found but not right')
        for p in sc['pairs']:
            if p['right'] and p['kindOk']: continue
            k = key[p['key']]; d = det[p['det']]
            at_opening(fl, f"{k['id']} {k['kind']} ({k.get('subtype', '')}) found as {d['id']} {d['kind']} w {d['width']} {d['evidence']}", tuple(k['a']), tuple(k['b']))
    if 'found' in what:
        print('\n################ key openings found right (for comparison)')
        for p in sc['pairs']:
            if not (p['right'] and p['kindOk']): continue
            k = key[p['key']]; d = det[p['det']]
            at_opening(fl, f"{k['id']} {k['kind']} ({k.get('subtype', '')}) RIGHT as {d['id']} w {d['width']} {d['evidence']}", tuple(k['a']), tuple(k['b']))
    if 'extras' in what:
        print('\n################ detections the key does not list (extras)')
        for x in sc['extra']:
            d = det[x['det']]
            a, b = tuple(d['a']), tuple(d['b'])
            u = unit(sub(b, a))
            print(f"\n=== {d['id']} {d['kind']} w {d['width']} {f3(a)} -> {f3(b)} t {d['wallThickness']} {d['evidence']}")
            for g in gaps_near(fl, a, b, 0.1):
                if math.dist(g.at(g.w / 2), mul(add(a, b), 0.5)) > 0.2: continue
                for r in describe_gap(fl, g): print(r)
            for tag, q, dirn in (('end a', a, mul(u, -1)), ('end b', b, u)):
                pt = add(q, mul(dirn, 0.02))
                parts = [g for g in fl.G.parts if g.distance(Point(pt)) < 0.03]
                for g in parts:
                    x0, y0, x1, y1 = g.bounds
                    print(f"    {tag} {f3(q)} stands on a wall-solid part: bounds x {x0:.3f}-{x1:.3f} y {y0:.3f}-{y1:.3f}, area {g.area:.3f} m2")
                    near = g.buffer(0.01)
                    lays = {}
                    zone = Point(pt).buffer(0.35)
                    for p in fl.P:
                        if not (p.roles & {'wall', 'column'}): continue
                        if 'loops' in p.d:
                            gg = even_odd(p.d['loops'])
                            if not gg.is_empty and gg.intersects(zone) and gg.intersects(near):
                                lays.setdefault((p.lay, 'fill'), []).append(p.h)
                        elif p.pts and len(p.pts) >= 2:
                            ls = LineString(p.pts)
                            if ls.intersects(zone) and ls.intersection(near).length > 0.03:
                                lays.setdefault((p.lay, ('closed ' if p.poly is not None else '') + p.t + ('' if p.cont else ' (not continuous)')), []).append(p.h)
                    for (lay, kind), hs in sorted(lays.items()):
                        print(f"        made of, within 0.35 m of the end: {len(hs)} x {kind} on {lay} (handles {', '.join(sorted(set(str(h) for h in hs))[:8])})")
                if not parts: print(f"    {tag} {f3(q)}: no wall-solid part within 3 cm")


if __name__ == '__main__':
    main()
