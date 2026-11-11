"""Final check (UF): ACCEPTANCE A-3 (every DWG of the project root converts, with its verdict) and the A-4 numbers that a
served prepare shows (units and door votes, level tags, grid labels, area proposals), from the recorded cases' prepare
outputs (conversion.json, drawing.json) and the API's api.json of each prepare run (validated).
    python -B check_a3_a4.py <acc out dir> <store data dir>"""
import json
import sys
from pathlib import Path

PROJECT = Path(r'C:\Users\DWP2\Desktop\Project walkthrough')


def load(p):
    return json.loads(Path(p).read_bytes())


def main() -> int:
    out, store = Path(sys.argv[1]), Path(sys.argv[2])
    seen = {}
    for rec_path in sorted(out.glob('*/record.json')):
        rec = load(rec_path)
        case = rec_path.parent
        for u in rec.get('uploads') or []:
            conv = case / 'prepare' / f'{u["sha1"][:12]}.conversion.json'
            draw = case / 'prepare' / f'{u["sha1"][:12]}.drawing.json'
            if u['name'] in seen or not conv.is_file():
                continue
            c = load(conv)
            d = load(draw) if draw.is_file() else None
            row = {'case': rec['case'], 'kind': u['kind'], 'formatVersion': u.get('formatVersion'), 'bytes': u['bytes'],
                   'verdict': c['verdict'], 'missing': c['totals']['missing'], 'dwgEntities': c['totals']['dwgEntities'],
                   'messages': {m['class']: m['count'] for m in c['messages']},
                   'lostBlocksPlaced': [b['name'] for b in (c.get('lostBlocks') or []) if b.get('inserts')],
                   'lostBlocks': len(c.get('lostBlocks') or []), 'notes': c['notes'],
                   'convertSeconds': c.get('seconds'), 'peakMB': c.get('peakMemoryMB')}
            if d:
                tags = d['levelTags']
                row['units'] = {k: d['units'].get(k) for k in ('declared', 'votes', 'used', 'verdict')}
                row['levelTags'] = len(tags)
                row['levelTagLayers'] = {lay: sum(1 for t in tags if t.get('layer') == lay) for lay in sorted({t.get('layer') for t in tags})}
                row['gridLabels'] = len(d.get('gridLabels') or [])
                row['areas'] = len(d.get('areas') or [])
                row['layers'] = len(d['layers'])
                bad = [t['text'] for t in tags if t['text'].strip().upper().startswith(('W1.20', 'D2.10', 'A1.00', 'R1.50', 'X0.900'))]
                row['negativeTagsRead'] = bad
            seen[u['name']] = row
    root = sorted(p.name for p in PROJECT.glob('*.dwg'))
    print(f'DWGs in the project root: {len(root)}; converted in the cases: {len([n for n in root if n in seen])}')
    for n in root:
        r = seen.get(n)
        if not r:
            print(f'  {n}: NOT IN ANY CASE')
            continue
        print(f'  {n}: {r["verdict"]} (missing {r["missing"]} of {r["dwgEntities"]}), {r["formatVersion"]}, case {r["case"]}')
        print(f'      messages {r["messages"]}')
        if r['lostBlocksPlaced'] or r['lostBlocks']:
            print(f'      lost blocks {r["lostBlocks"]}, placed in the plan: {r["lostBlocksPlaced"]}')
        print(f'      notes {r["notes"]}')
        if 'units' in r:
            print(f'      units {r["units"]}; level tags {r["levelTags"]} {r["levelTagLayers"]}; grid labels {r["gridLabels"]}; '
                  f'area proposals {r["areas"]}; layers {r["layers"]}; negative cases read as tags: {r["negativeTagsRead"]}')
    # every prepare and build run validated by the API
    runs = []
    for api in sorted(store.glob('projects/*/builds/*/runs/*/api.json')):
        a = load(api)
        runs.append((api.parent.parent.parent.parent.parent.name, api.parent.name, a.get('validated'), a.get('issues')))
    bad = [r for r in runs if r[2] is not True]
    print(f'runs with api.json: {len(runs)}; validated: {sum(1 for r in runs if r[2] is True)}; not validated: {len(bad)}')
    for r in bad:
        print('   ', r)
    (out / '_a3_a4.json').write_text(json.dumps({'sources': seen, 'runs': runs}, indent=1, ensure_ascii=False), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
