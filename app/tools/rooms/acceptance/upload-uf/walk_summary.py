"""Final check (UF): the A-6 walk reports (<WT_TMP>/upload-walk/<file>.json from tests/e2e/upload-walk.spec.ts) in one
line per uploaded version, counted as docs/upload/GAPS.md counts them, and each failing probe's id.
    python -B walk_summary.py <upload-walk dir>"""
import json
import sys
from pathlib import Path


def counts(report: dict) -> dict:
    res = {}
    for check in ('loads', 'start', 'floors', 'walls', 'doors', 'glass'):
        r = report.get(check)
        if r is None:
            res[check] = 'not run'
            continue
        if check in ('walls', 'doors', 'glass'):
            n = len(r.get('failures') or [])
            det = r.get('detail')
            total = None
            if check == 'walls' and isinstance(det, list):
                total = sum(x.get('tried', 0) for x in det)
            elif check == 'doors' and isinstance(det, dict):
                total = det.get('doors')
            elif check == 'glass' and isinstance(det, dict):
                total = f"{det.get('probes')} probes + {len(det.get('parts') or [])} random parts"
            if check == 'walls' and total == 0:
                res[check] = 'no start spot found (0 of 40 tried)'
                continue
            if check == 'glass' and total == '0 probes + 0 random parts':
                res[check] = 'no glass to probe'
                continue
            res[check] = (f'ok ({total})' if total is not None else 'ok') if r.get('ok') else \
                f'{n} failing' + (f' of {total}' if total is not None else '')
        elif check == 'loads':
            res[check] = 'ok' if (r.get('canvas') == 1 and not r.get('error') and not r.get('requests')
                                  and not r.get('problems') and r.get('stamp') == r.get('maxScriptStamp')) else 'FAILED'
        else:
            res[check] = 'ok' if r.get('ok', True) else 'FAILED'
    return res


def ids(report: dict) -> dict:
    out = {}
    for check in ('walls', 'doors', 'glass'):
        r = report.get(check) or {}
        fl = r.get('failures') or []
        out[check] = [f.get('id') or f.get('probe') or f.get('part') or f.get('door') if isinstance(f, dict) else str(f) for f in fl]
    return out


for f in sorted(Path(sys.argv[1]).glob('*.json')):
    rep = json.loads(f.read_text(encoding='utf-8'))
    print(f'{f.stem} (should: {rep.get("should")}): ' + '; '.join(f'{k} {v}' for k, v in counts(rep).items()))
    bad = {k: v for k, v in ids(rep).items() if v}
    if bad:
        print('    failing:', bad)
