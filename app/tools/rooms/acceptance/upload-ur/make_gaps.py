"""Writes docs/upload/GAPS.md (step UI) from the acceptance store, the gap-report sections and the walk reports.

    python -B make_gaps.py <wt-ui dir> <out GAPS.md>     (runs gap-report.py through node for each pair)
"""
from __future__ import annotations

import collections
import json
import subprocess
import sys
from pathlib import Path

APP = Path(r'C:\Users\DWP2\Desktop\Project walkthrough\app')


def load(p):
    return json.loads(Path(p).read_bytes())


def walk_items(report: dict) -> list[dict]:
    """U7's per-file walk report -> gap-report's --walk list {floor, kind, id, passed, detail} (failures only, plus a
    count of the passing probes per check so that the section can say how many passed)."""
    out = []
    for check in ('walls', 'doors', 'glass'):
        r = report.get(check)
        if not r:
            continue
        fails = r.get('failures') or []
        for i, f in enumerate(fails):
            if isinstance(f, dict):
                fid = f.get('id') or f.get('probe') or f.get('part') or f.get('door') or f'{check}-{i + 1}'
                floor = f.get('floor') or (str(fid).split('-')[0].split(' ')[0] if fid else None)
                if check == 'doors':
                    d = (f'{"exterior" if f.get("exterior") else "interior"} {f.get("kind")}; through one way: '
                         f'{_walk_text(f.get("fwd"), f.get("fwdTries"))}; the other way: {_walk_text(f.get("back"), f.get("backTries"))}')
                elif check == 'glass':
                    d = (f'walked from side {f.get("side")}: stopped at {f.get("stoppedAt")} m'
                         + (f', by {f.get("ahead")}' if f.get('ahead') else ', nothing ahead (no start on a floor)'))
                else:
                    d = json.dumps({k: v for k, v in f.items() if k not in ('floor', 'id')}, ensure_ascii=False)[:220]
            else:
                floor, fid, d = None, f'{check}-{i + 1}', str(f)
            out.append({'floor': floor, 'kind': check, 'id': fid, 'passed': False, 'detail': d})
    return out


def _walk_text(v, tries) -> str:
    if v == 'no start':
        on = [t for t in (tries or []) if t.get('onFloor')]
        return 'no start: no floor 0.40 - 0.90 m before the door' if not on else 'no start'
    if isinstance(v, (int, float)):
        return f'{v} m' + (' (stopped before the door)' if v < 0 else '')
    return str(v)


def walk_counts(report: dict) -> dict:
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


def walk_table(items: list[dict], classes: list[dict], total_note: str) -> str:
    """The failing walk probes of a version with no prototype (the tower), classified as gap-report.py does."""
    nl, bar = chr(10), chr(124)
    if not items:
        return f'Every walk probe passes ({total_note}).' + nl
    lines = [f'{len(items)} failing probes ({total_note}).', '', '| Floor | Probe | Id | Detail | Cause | Class |',
             '|---|---|---|---|---|---|']
    for w in items:
        metric = f'walk: {w["kind"]}'
        hit = next((c for c in classes if c.get('metric') == metric and c.get('floor') in (None, w['floor'])
                    and (not c.get('ids') or w['id'] in c['ids'])), None)
        cause, cls = (hit.get('cause', ''), hit.get('class', 'to classify')) if hit else ('', 'to classify')
        cells = [w['floor'], metric, w['id'], w['detail'], cause, cls]
        lines.append('| ' + ' | '.join(str(c).replace(bar, chr(92) + bar).replace(nl, ' ') for c in cells) + ' |')
    return nl.join(lines) + nl


def gap_section(proto: Path, upload: Path, title: str, classes: Path | None, walk: Path | None, out: Path) -> str:
    cmd = ['node', 'tools/run-builder-py.mjs', 'tools/upload/gap-report.py', str(proto), str(upload), '--title', title,
           '--out', str(out)]
    if classes:
        cmd += ['--classes', str(classes)]
    if walk:
        cmd += ['--walk', str(walk)]
    r = subprocess.run(cmd, cwd=APP, capture_output=True, text=True, encoding='utf-8')
    if r.returncode:
        raise RuntimeError(r.stderr or r.stdout)
    text = out.read_text(encoding='utf-8')
    return text.replace(f'## {title}', f'### Gap report: {title}', 1).replace('\n### ', '\n#### ').replace(
        '\n#### Gap report', '\n### Gap report')


def main() -> int:
    wt, target = Path(sys.argv[1]), Path(sys.argv[2])
    store = wt / 'acc' / 'data' / 'projects'
    gaps = wt / 'gaps'
    walkdir = wt / 'e2e' / 'upload-walk'
    sec = gaps / 'sections'
    sec.mkdir(exist_ok=True)
    walks = {}
    for f in sorted(walkdir.glob('*.json')):
        rep = load(f)
        walks[f.stem] = rep
        (gaps / f'walk-{f.stem}.json').write_text(json.dumps(walk_items(rep), indent=1, ensure_ascii=False), encoding='utf-8')
    parts = {}
    pairs = [('bank', 'bank-sampeng/versions/2', 'bank-reupload/versions/1', None, 'bank-reupload-v1'),
             ('bank-v3', 'bank-sampeng/versions/2', 'bank-sampeng/versions/3', None, 'bank-sampeng-v3'),
             ('house', 'sukhumvit-house/versions/1', 'house-upload/versions/1', 'classes-house.json', 'house-upload-v1'),
             ('suite', 'presidential-suite/versions/1', 'suite-upload/versions/1', 'classes-suite.json', 'suite-upload-v1'),
             ('suite-outlines', 'presidential-suite/versions/1', 'suite-outlines/versions/1', 'classes-suite-outlines.json',
              'suite-outlines-v1'),
             ('a12-new', 'presidential-suite/versions/1', 'suite-revit/versions/1', 'classes-a12.json', 'suite-revit-v1'),
             ('a12-v2', 'presidential-suite/versions/1', 'presidential-suite/versions/2', 'classes-a12.json',
              'presidential-suite-v2')]
    for title, proto, up, classes, wk in pairs:
        cls = gaps / classes if classes and (gaps / classes).exists() else None
        w = gaps / f'walk-{wk}.json' if (gaps / f'walk-{wk}.json').exists() else None
        md = gap_section(store / proto, store / up, title, cls, None, sec / f'{title}.md')
        if w is not None:
            its = load(w)
            note = '; '.join(f'{k} {v}' for k, v in walk_counts(walks[wk]).items())
            wt = walk_table(its, load(cls) if cls else [], note)
            parts[f'walktable:{title}'] = wt
            md += chr(10) + '#### Walk checks (A-6)' + chr(10) + chr(10) + wt
        parts[title] = md
    summary = {k: walk_counts(v) for k, v in walks.items()}
    (gaps / 'walk-summary.json').write_text(json.dumps(summary, indent=1), encoding='utf-8')
    head = (gaps / 'head.md').read_text(encoding='utf-8')
    for key, row in summary.items():
        head = head.replace(f'@@walk:{key}@@', '; '.join(f'{k} {v}' for k, v in row.items()))
    body = [head]
    for name in ('bank', 'house', 'suite', 'tower', 'a12'):
        p = gaps / f'{name}.text.md'
        if p.exists():
            text = p.read_text(encoding='utf-8')
            for title, md in parts.items():
                text = text.replace(f'@@{title}@@', md)
            if '@@walk-tower@@' in text:
                cls = load(gaps / 'classes-tower.json') if (gaps / 'classes-tower.json').exists() else []
                its = load(gaps / 'walk-tower-upload-v1.json') if (gaps / 'walk-tower-upload-v1.json').exists() else []
                text = text.replace('@@walk-tower@@', walk_table(its, cls, ', '.join(f'{k} {v}' for k, v in summary.get('tower-upload-v1', {}).items())))
            if '@@a12-openings@@' in text:
                of = load(store / 'suite-revit' / 'versions' / '1' / 'source' / 'openings.json')
                rows = []
                for fl, recs in of['floors'].items():
                    for r in recs:
                        x = r['record']
                        rows.append(f"| {x['id']} | {x['kind']} | {x.get('subtype')} | {x['width']} | {[round(v, 2) for v in x['a']]} | {[round(v, 2) for v in x['b']]} | {x.get('confidence')} |")
                text = text.replace('@@a12-openings@@', chr(10).join(rows))
            for key, row in summary.items():
                text = text.replace(f'@@walk:{key}@@', ', '.join(f'{k} {v}' for k, v in row.items()))
            body.append(text)
    target.write_text('\n'.join(body), encoding='utf-8', newline='\n')
    print(f'wrote {target}: {sum(len(b) for b in body)} characters; walk files {sorted(walks)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
