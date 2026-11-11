"""A-10 (should): times and memory of every recorded case, from job.json (the worker's step seconds), the driver's wall
clock (upload complete -> run done) and log.txt (each child's peak MB). python -B times.py <acc out dir>"""
import json
import re
import sys
from pathlib import Path

CHILD = re.compile(r'==== (?P<title>.+?): exit (?P<exit>\S+), (?P<sec>[\d.]+|None) s, peak (?P<peak>[\d.]+|None) MB')


def main() -> int:
    root = Path(sys.argv[1])
    out = {}
    for rec_path in sorted(root.glob('*/record.json')):
        rec = json.loads(rec_path.read_text(encoding='utf-8'))
        case = rec.get('case') or rec_path.parent.name
        row = {'ok': rec.get('ok')}
        if rec.get('prepare'):
            p = rec['prepare']
            row['prepare'] = {'wall': p.get('wall'), 'queued': p.get('queuedSeconds'),
                              'steps': {s['name']: s['seconds'] for s in (p.get('run') or {}).get('steps', [])}}
        for tag in ('build1', 'build2'):
            if rec.get(tag):
                b = rec[tag]
                row[tag] = {'wall': b.get('wall'), 'queued': b.get('queuedSeconds'),
                            'steps': {s['name']: s['seconds'] for s in (b.get('run') or {}).get('steps', [])}}
        peaks = []
        for log in sorted((rec_path.parent / 'runs').glob('*/log.txt')):
            for m in CHILD.finditer(log.read_text(encoding='utf-8', errors='replace')):
                peaks.append({'run': log.parent.name, 'child': m['title'].strip(), 'seconds': m['sec'],
                              'peakMB': None if m['peak'] == 'None' else float(m['peak'])})
        row['children'] = peaks
        row['maxPeakMB'] = max((c['peakMB'] or 0 for c in peaks), default=None)
        out[case] = row
    (root / '_times.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    for case, row in out.items():
        print(case, 'ok' if row['ok'] else 'FAILED',
              '| prepare', (row.get('prepare') or {}).get('wall'), 's (queued', (row.get('prepare') or {}).get('queued'), ')',
              '| build', (row.get('build1') or {}).get('wall'), 's', '| build2', (row.get('build2') or {}).get('wall'),
              '| max child peak', row['maxPeakMB'], 'MB')
    return 0


if __name__ == '__main__':
    sys.exit(main())
