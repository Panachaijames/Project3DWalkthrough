"""Final check (UF): the e2e run's JSON report summarised: per spec file the tests passed / failed / flaky / skipped, the
slowest tests, every failure's message, and the annotations (the A-6 'should' walk failures, the A-10 redraw times).
    python -B e2e_summary.py <results.json>"""
import collections
import json
import sys

rep = json.load(open(sys.argv[1], encoding='utf-8'))
per = collections.defaultdict(collections.Counter)
tests = []


def walk(suite, file=None):
    file = suite.get('file') or file
    for spec in suite.get('specs', []):
        for t in spec.get('tests', []):
            res = t.get('results', [])
            status = t.get('status')            # expected | unexpected | flaky | skipped
            dur = sum(r.get('duration', 0) for r in res)
            err = next((r.get('error', {}).get('message', '') for r in res if r.get('status') not in ('passed', 'skipped')), '')
            tests.append({'file': spec.get('file') or file, 'title': spec['title'], 'status': status, 'seconds': dur / 1000,
                          'retries': len(res) - 1, 'annotations': t.get('annotations', []), 'error': err})
            per[spec.get('file') or file][status] += 1
    for s in suite.get('suites', []):
        walk(s, file)


for s in rep['suites']:
    walk(s)
tot = collections.Counter(t['status'] for t in tests)
print('total', len(tests), dict(tot))
for f, c in sorted(per.items()):
    print(f'  {f}: {dict(c)}')
print('slowest:')
for t in sorted(tests, key=lambda t: -t['seconds'])[:6]:
    print(f"  {t['seconds']:.1f} s  {t['file']} :: {t['title'][:120]}")
bad = [t for t in tests if t['status'] not in ('expected', 'skipped')]
print('not passed first time:', len(bad))
for t in bad:
    print(f"  {t['status']} {t['file']} :: {t['title'][:150]}\n     {t['error'][:600]}")
print('annotations:')
for t in tests:
    for a in t['annotations']:
        if a.get('type', '').startswith(('should', 'redraw')):
            print(f"  [{a['type']}] {t['file']} :: {t['title'][:60]}: {a.get('description', '')[:400]}")
st = rep.get('stats', {})
print('stats', {k: st.get(k) for k in ('expected', 'unexpected', 'flaky', 'skipped', 'duration')})
