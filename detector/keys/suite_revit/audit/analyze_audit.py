"""Result of the blind audit of the held-out run on `presidential suite_layout.dwg` (cache suite_revit), step 7 of 7.
Done the way ../../tower/audit/analyze_audit.py and audit_followup.py did it for L29 / L30.

  python -B keys/suite_revit/audit/analyze_audit.py            (Git Bash, from detector/)

Reads (and changes none of them): secret_map.json, verdicts_auditor1.json, verdicts_auditor2.json, ../suite_revit.json.
The detector output is only hashed (to check it is the file the audit places were made from), not read.

The rule for the audited key:
  - a scored key opening that BOTH auditors call not an opening leaves the key (it moves to "rejected");
  - a detector extra that BOTH auditors accept as a real opening the key lacks is added (id AUD-nn, auditor 1's ends);
  - split verdicts stay as the key has them.

Writes:
  audit_result.json            every place with its source and both verdicts, the controls, the extras, the key openings,
                               what the auditors noticed near the places and whether the key has it, the key changes
  ../suite_revit_audited.json  the audited key: a copy of ../suite_revit.json with the changes applied and an "audit"
                               entry that records each change and why (tools/score.py reads "openings" only)
"""
import hashlib, json, math, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DETECTOR = HERE.parents[2]
sys.path.insert(0, str(DETECTOR / 'tools'))
import score as scorer                          # noqa: E402  tools/score.py, the referee (its matching rules)

KEY_PATH = HERE.parent / 'suite_revit.json'
OUT_KEY = HERE.parent / 'suite_revit_audited.json'
AUDITORS = ['auditor1', 'auditor2']


def sha1(p):
    return hashlib.sha1(Path(p).read_bytes()).hexdigest()


def load(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))


def verdict_row(v):
    """One auditor's verdict on a place, in one shape for both files."""
    real = v['verdict'] == 'real'
    assert v['verdict'] in ('real', 'not real', 'unsure'), v['verdict']
    ends = v.get('ends') or ([v['a'], v['b']] if 'a' in v else None)
    chk = v.get('claimCheck') or v.get('claimMatches') or {}
    return {'verdict': v['verdict'], 'real': real, 'kind': v.get('kind'), 'ends': ends,
            'width': round(math.dist(*ends), 4) if ends else None,
            'kindSameAsClaim': chk.get('kindRight', chk.get('kind')), 'widthSameAsClaim': chk.get('widthRight', chk.get('width')),
            'whatItIs': v.get('whatItIs') or v.get('whatIsThere') or v.get('subtype'),
            'confidence': v.get('confidence')}


def noticed(doc):
    """Everything an auditor noticed that is not one of the places (near, just beyond 2 m, farther)."""
    out = []
    for field in ('noticedNearby', 'noticedJustBeyond2m', 'noticedFartherAway'):
        for n in doc.get(field, []):
            ends = n.get('ends') or [n['a'], n['b']]
            status = n.get('status') or {'yes': 'definite opening', 'possible': 'possible'}.get(n.get('isOpening'), 'definite opening')
            out.append({'id': n['id'], 'field': field, 'status': status, 'kind': n['kind'], 'a': ends[0], 'b': ends[1],
                        'width': round(math.dist(*ends), 3), 'nearestPlace': n.get('nearestPlace')})
    return out


def main():
    secret = load('secret_map.json')
    docs = {a: load(f'verdicts_{a}.json') for a in AUDITORS}
    key = json.loads(KEY_PATH.read_text(encoding='utf-8'))
    KEYS = {o['id']: o for o in key['openings']}

    # the audit places were made from this key and this detector output
    checks = {'keySha1': sha1(KEY_PATH), 'keySha1InSecretMap': secret['keySha1'],
              'detectionsSha1': sha1(DETECTOR / secret['detections']), 'detectionsSha1InSecretMap': secret['detectionsSha1']}
    assert checks['keySha1'] == checks['keySha1InSecretMap'], 'the key changed since the audit places were made'
    assert checks['detectionsSha1'] == checks['detectionsSha1InSecretMap'], 'the detector output changed since the audit places were made'

    V = {a: {v['place']: verdict_row(v) for v in docs[a]['verdicts']} for a in AUDITORS}
    places = sorted(secret['places'])
    for a in AUDITORS:
        assert sorted(V[a]) == places, f'{a} did not judge every place'

    rows = []
    for pid in places:
        s = secret['places'][pid]
        claim = s['key'] if s['claimFrom'] == 'key' else s['detection']
        r = {'place': pid, 'source': s['source'], 'keyId': s['keyId'], 'detId': s['detId'], 'claimedKind': claim['kind'],
             'claimedWidth': round(claim['width'], 3)}
        for a in AUDITORS:
            v = V[a][pid]
            r[a] = v
            if v['real']:                            # a real opening: same kind as the claim, ends within the scorer's limits?
                cand = {'a': v['ends'][0], 'b': v['ends'][1], 'kind': v['kind']}
                m = scorer.match([claim], [cand])
                wk = scorer.width(claim)
                v['matchesClaimByScorer'] = bool(m)
                v['kindRight'] = v['kind'] == claim['kind']
                v['widthRight'] = abs(scorer.width(cand) - wk) <= max(0.10, 0.10 * wk)
        both_real = all(r[a]['real'] for a in AUDITORS)
        none_real = all(r[a]['verdict'] == 'not real' for a in AUDITORS)
        r['agreement'] = 'both real' if both_real else 'both not real' if none_real else 'split'
        rows.append(r)

    def of(src):
        return [r for r in rows if r['source'] == src]

    controls, extras = of('control: key opening found right'), of('detector extra')
    missed, wrong = of('key opening missed'), of('key opening found but not right')
    assert len(controls) + len(extras) + len(missed) + len(wrong) == len(rows) == secret['total']

    def tally(rs):
        return {k: sum(1 for r in rs if r['agreement'] == k) for k in ('both real', 'both not real', 'split')}

    ctrl = {a: {'controls': len(controls),
                'calledReal': sum(1 for r in controls if r[a]['real']),
                'calledRealWithTheKeysKind': sum(1 for r in controls if r[a]['real'] and r[a]['kindRight']),
                'withTheKeysKindAndWidth': sum(1 for r in controls if r[a]['real'] and r[a]['kindRight'] and r[a]['widthRight'])}
            for a in AUDITORS}
    keyops = missed + wrong
    keyop = {a: {'keyOpenings': len(keyops),
                 'calledReal': sum(1 for r in keyops if r[a]['real']),
                 'calledRealWithTheKeysKind': sum(1 for r in keyops if r[a]['real'] and r[a]['kindRight']),
                 'withTheKeysKindAndWidth': sum(1 for r in keyops if r[a]['real'] and r[a]['kindRight'] and r[a]['widthRight'])}
             for a in AUDITORS}
    ext = {a: {'extras': len(extras), 'rejected': sum(1 for r in extras if r[a]['verdict'] == 'not real'),
               'accepted': sum(1 for r in extras if r[a]['real'])} for a in AUDITORS}

    # what the auditors noticed that is not a place: is it in the key (scored or optional)?
    seen = {}
    for a in AUDITORS:
        lst = noticed(docs[a])
        for n in lst:
            m = scorer.match(key['openings'], [n])
            n['keyId'] = key['openings'][m[0][0]]['id'] if m else None
            n['keyOptional'] = bool(key['openings'][m[0][0]].get('optional')) if m else None
            n['keyKind'] = key['openings'][m[0][0]]['kind'] if m else None
        seen[a] = lst
    not_in_key = [(a, n) for a in AUDITORS for n in seen[a] if not n['keyId']]

    # ---- the key changes, by the rule in the docstring
    changes = []
    out = json.loads(json.dumps(key))
    for r in missed + wrong + controls:
        if r['agreement'] == 'both not real':
            o = next(x for x in out['openings'] if x['id'] == r['keyId'])
            out['openings'].remove(o)
            why = 'both auditors judged the place not an opening: ' + ' / '.join(str(r[a]['whatItIs']) for a in AUDITORS)
            out.setdefault('rejected', []).append({'id': r['keyId'] + ' (removed by the blind audit)', 'where': [round(c, 3) for c in scorer.centre(o)],
                                                   'reason': why, 'floor': o.get('floor')})
            changes.append({'change': 'removed', 'keyId': r['keyId'], 'place': r['place'], 'why': why})
    n = 0
    for r in extras:
        if r['agreement'] == 'both real':
            n += 1
            v = r[AUDITORS[0]]
            s = secret['places'][r['place']]
            a_, b_ = v['ends']
            why = 'both auditors judged the detector extra a real opening that the key lacks'
            out['openings'].append({'id': f'AUD-{n:02d}', 'kind': v['kind'], 'subtype': 'added by the blind audit (both auditors)',
                                    'a': a_, 'b': b_, 'width': round(math.dist(a_, b_), 4), 'host': 'wall',
                                    'evidence': str(v['whatItIs']), 'confidence': 'medium', 'optional': False, 'agreement': 'audited',
                                    'floor': KEYS[next(iter(KEYS))].get('floor'), 'part': KEYS[next(iter(KEYS))].get('part')})
            changes.append({'change': 'added', 'keyId': f'AUD-{n:02d}', 'place': r['place'], 'detId': s['detId'], 'why': why})

    scored = lambda k: sum(1 for o in k['openings'] if not o.get('optional'))
    audit = {
        'what': 'Blind audit of the held-out run (step 6 of 7), applied in step 7 by audit/analyze_audit.py',
        'date': '2026-11-10',
        'places': len(rows), 'auditors': AUDITORS,
        'rule': 'a scored key opening both auditors call not an opening is removed; a detector extra both auditors accept as a real '
                'opening the key lacks is added; split verdicts stay as the key has them',
        'controls': ctrl, 'extras': {'count': len(extras), **tally(extras), 'perAuditor': ext},
        'keyOpeningsMissedOrNotRight': {'count': len(keyops), **tally(keyops), 'perAuditor': keyop},
        'noticedBesideThePlaces': {a: {'count': len(seen[a]), 'inTheKey': sum(1 for x in seen[a] if x['keyId']),
                                       'notInTheKey': sum(1 for x in seen[a] if not x['keyId'])} for a in AUDITORS},
        'changes': changes,
        'result': (f'{len(changes)} change(s)' if changes else
                   'no change: no scored key opening was called not an opening by both auditors (none by either), and no detector '
                   'extra was accepted by both (none by either); there was no split verdict. The openings of this file are those of '
                   'suite_revit.json.'),
        'scoredOpenings': {'keyAsMade': scored(key), 'audited': scored(out)},
        'madeFrom': {'key': 'suite_revit.json', 'keySha1': checks['keySha1']},
    }
    out['audit'] = audit
    if not changes:
        assert out['openings'] == key['openings']
    OUT_KEY.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    (HERE / 'audit_result.json').write_text(json.dumps({
        'about': 'Result of the blind audit (step 7 of 7): made by analyze_audit.py from secret_map.json and the two verdict files.',
        'checks': checks, 'controls': ctrl, 'extras': {**tally(extras), 'perAuditor': ext},
        'keyOpeningsMissedOrNotRight': {**tally(keyops), 'perAuditor': keyop},
        'keyChanges': changes, 'places': rows, 'noticedBesideThePlaces': seen}, indent=1, ensure_ascii=False), encoding='utf-8')

    # ---- report
    print(f"{len(rows)} places: {len(controls)} controls, {len(extras)} detector extras, {len(missed)} key openings missed, "
          f"{len(wrong)} found but not right")
    print('\n=== CONTROLS (key openings the detector found right; the auditors could not tell them from the others) ===')
    for a in AUDITORS:
        c = ctrl[a]
        print(f"  {a}: real {c['calledReal']}/{c['controls']}, real with the key's kind {c['calledRealWithTheKeysKind']}/{c['controls']}, "
              f"kind and width {c['withTheKeysKindAndWidth']}/{c['controls']}")
    print('\n=== DETECTOR EXTRAS ===')
    print('  ', tally(extras))
    for r in extras:
        print(f"  {r['place']} {r['detId']} {r['claimedKind']} w {r['claimedWidth']:.3f}: {r['agreement']}")
        for a in AUDITORS:
            print(f"       {a}: {r[a]['verdict']} ({r[a]['confidence']}): {r[a]['whatItIs']}")
    print('\n=== KEY OPENINGS the detector missed or got wrong ===')
    print('  ', tally(keyops))
    for r in keyops:
        print(f"  {r['place']} {r['keyId']} {r['claimedKind']} w {r['claimedWidth']:.3f} ({r['source']}): {r['agreement']}; " +
              '; '.join(f"{a} {r[a]['kind']} w {r[a]['width']:.3f} kind {'ok' if r[a].get('kindRight') else 'DIFFERS'} "
                        f"width {'ok' if r[a].get('widthRight') else 'DIFFERS'}" for a in AUDITORS if r[a]['real']))
    print('\n=== NOTICED BESIDE THE PLACES: is it in the key? ===')
    for a in AUDITORS:
        for x in seen[a]:
            print(f"  {a} {x['id']} {x['status'][:40]:40} {x['kind']:8} w {x['width']:.3f} at {[round(c, 2) for c in scorer.centre(x)]}"
                  f" -> {('key ' + x['keyId'] + (' (optional)' if x['keyOptional'] else ' (scored)') + ' ' + x['keyKind']) if x['keyId'] else 'NOT IN THE KEY'}")
    print(f"  not in the key: {len(not_in_key)}")
    print('\n=== KEY CHANGES ===')
    for c in changes:
        print('  ', c)
    print('  none' if not changes else f'  {len(changes)} change(s)')
    print(f"\nwrote {OUT_KEY.name}: {scored(out)} scored openings ({scored(key)} in the key as made), "
          f"{sum(1 for o in out['openings'] if o.get('optional'))} optional; and audit_result.json")


if __name__ == '__main__':
    main()
