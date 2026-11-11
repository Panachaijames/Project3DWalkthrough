"""ACCEPTANCE A-8 checks (office memory) on the recorded cases: python -B check_a8.py <acc out dir> <store>"""
import json
import sys
from pathlib import Path

THIRTEEN = ['A-WALL', 'A-WALL-PATT', 'S-COLS', 'A-GLAZ-CURT', 'A-DOOR', 'A-DOOR-FRAM', 'A-DOOR-HDLN', 'S-STRS', 'S-STRS-MBND',
            'I-FURN', 'Q-CASE', 'P-SANR-FIXT', 'A-GENM']
APP = Path(r'C:\Users\DWP2\Desktop\Project walkthrough\app')


def main() -> int:
    out, store = Path(sys.argv[1]), Path(sys.argv[2])
    res = {}
    office = json.loads((store / 'mappings' / 'acceptance-revit.json').read_text(encoding='utf-8'))
    bank = json.loads((APP / 'fixtures' / 'upload' / 'settings' / 'bank.json').read_text(encoding='utf-8'))
    fixture = json.loads((APP / 'fixtures' / 'upload' / 'mappings' / 'dwp-revit.json').read_text(encoding='utf-8'))
    res['office'] = {'layers': len(office['layers']),
                     'sameRolesAsFixtureDwpRevit': {k: v['role'] for k, v in office['layers'].items()} ==
                     {k: v['role'] for k, v in fixture['layers'].items()},
                     'bankRolesNotOther': sum(1 for r in bank['layers'].values() if r != 'other')}
    tower = json.loads((out / 'tower' / 'prepare' / 'build-detail.json').read_text(encoding='utf-8'))
    sug = tower['suggestions']
    drawings = sorted((out / 'tower' / 'prepare').glob('*.drawing.json'))
    l29 = next(json.loads(p.read_text(encoding='utf-8')) for p in drawings
               if json.loads(p.read_text(encoding='utf-8'))['source']['name'] == 'L29.dwg')
    l29_layers = [l['name'] for l in l29['layers']]
    res['l29'] = {'layers': len(l29_layers), 'hasLPlnt': 'L-PLNT' in l29_layers,
                  'thirteen': {k: (sug.get(k) or {}).get('from') for k in THIRTEEN},
                  'thirteenAllOffice': all((sug.get(k) or {}).get('from') == 'office' for k in THIRTEEN)}
    norm = {k.upper() for k in office['layers']}
    others = [k for k in l29_layers if k not in THIRTEEN]
    res['l29']['otherInMemory'] = {k: (sug.get(k) or {}).get('from') for k in others if k.upper() in norm}
    res['l29']['rest'] = {k: (sug.get(k) or {}).get('from') for k in others if k.upper() not in norm}
    v3 = json.loads((out / 'bank-v3' / 'prepare' / 'adopted-settings.json').read_text(encoding='utf-8'))
    res['bankV3Proposal'] = {'floorKeys': [f['key'] for f in v3['floors']], 'office': v3['office'],
                             'naming': {k: v3['project'].get(k) for k in ('photoName', 'maxPrefix', 'maxFileName')},
                             'offset': v3['options']['offset']}
    print(json.dumps(res, indent=1))
    (out / '_a8.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
