"""Checks of the causes named in ../README.md: what the SAME frozen detector does when the lines a cause blames are left
out of a copy of the drawing's items. Nothing is fixed and nothing here is a result of the held-out test: the held-out
figure is the run on the drawing as it is (../score_first_mapping_audited.txt).

  OPENINGS_DATA=<WORK> python -B blind_run_suite_revit/diagnosis/whatif.py        (Git Bash, from detector/)

Each test names the drawing items it leaves out by their DXF handle (found with diagnose.py, which prints the handle of
every wall-layer line that runs along an opening).
"""
import json, math, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import diagnose as X                            # noqa: E402
sys.path.insert(0, str(X.DETECTOR / 'tools'))
import score as scorer                          # noqa: E402

KEY = json.loads(X.KEY.read_text(encoding='utf-8'))

# wall-layer lines drawn across a door opening, between its frames (each is one LINE that spans one opening only)
ACROSS = {
    'SR-01': ['4E93', '4EB9'], 'SR-02': ['4EBA', '4EE6'], 'SR-04': ['4E95', '4EE7'], 'SR-11': ['4F08', '4FA4'],   # pocket doors: the partition's two core lines (layer 0)
    'SR-10': ['4F07', '4FA2'],                                                                                 # a hinged door: the same two core lines (layer 0)
    'SR-15': ['54BD', '54C0'], 'SR-16': ['54C9', '54CC'],                                                      # unit doors D01: the wall's two face lines (A-WALL)
    'SR-06': ['4F03'],                                                                                         # a hinged door: its threshold line (layer 0)
}
# joinery of the walk-in wardrobe drawn on layer 0 beside the end wall of the bi-fold door SR-03 (shelf / rail lines)
WARDROBE = ['511B', '511C', '511D', '511F', '5120']


def run(name, drop):
    fl, ops, res = X.setup(set(drop))
    rep = scorer.score(KEY, {'openings': res})
    fr = rep['floors'][fl.name]
    by = {p['key']: p for p in fr['pairs']}
    print(f"\n== {name}: left out {len(drop)} line(s)")
    print(f"   {fr['right']} of {fr['keyCount']} right, {fr['matched']} found, {len(fr['extra'])} not in the key, optional found {len(fr['optionalFound'])}/{fr['optionalKeys']}")
    print('   missed:', ', '.join(m['key'] for m in fr['missed']) or 'none')
    print('   not in the key:', ', '.join(f"{x['kind']} {x['width']:.2f} at ({x['at'][0]:.2f}, {x['at'][1]:.2f})" for x in fr['extra']) or 'none')
    det = {o['id']: o for o in res}
    return fl, fr, by, det


def show(by, det, ids):
    for k in ids:
        p = by.get(k)
        if not p: print(f"   {k}: not found"); continue
        d = det[p['det']]
        print(f"   {k}: {d['kind']} {d['subtype']} w {d['width']:.3f} (key {p['widthKey']:.3f}) {'RIGHT' if p['right'] else 'not right'}  {d['evidence']}")


def main():
    fl, fr, by, det = run('the drawing as it is (the held-out run)', [])
    show(by, det, sorted(ACROSS) + ['SR-03', 'SR-08'])

    drop = [h for hs in ACROSS.values() for h in hs]
    fl, fr, by, det = run('without the wall-layer lines drawn across eight door openings', drop)
    show(by, det, sorted(ACROSS))

    fl, fr, by, det = run('without the wardrobe joinery lines beside the end wall of the bi-fold door', WARDROBE)
    show(by, det, ['SR-03'])
    k = next(o for o in KEY['openings'] if o['id'] == 'SR-03')
    for g in X.gaps_near(fl, tuple(k['a']), tuple(k['b'])):
        for r in X.describe_gap(fl, g): print(r)

    fl, fr, by, det = run('both', drop + WARDROBE)
    show(by, det, sorted(ACROSS) + ['SR-03', 'SR-08'])


if __name__ == '__main__':
    main()
