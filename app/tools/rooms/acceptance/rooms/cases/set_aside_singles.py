"""RI (rooms milestone, ACCEPTANCE RA-6 "with the stray lines set aside"): every item named by a `single-line` flag of the
first build is set aside (floorPast false: a set-aside line still bounds the floor, the state staff will leave), as
staff would with "Set it aside" on each flag. acc.py calls fixes(settings, build, overlay, plans) after build1 and
rebuilds; the settings it returns are dumped into <case>/build2/settings.json, so the count is on disk."""


def fixes(s, b, ov, plans):
    src_of = {f['key']: f['source'] for f in s['floors']}
    have = {(x.get('floor'), x.get('key')) for x in s['fixes'].get('setAside', [])}
    index = {}
    for flag in ov['flags']:
        if flag['kind'] != 'single-line':
            continue
        floor = flag['floor']
        src = src_of[floor]
        plan = plans[src[:12]]
        it = plan['items']
        if src not in index:
            index[src] = {k: i for i, k in enumerate(it['key'])}
        for key in (flag.get('ref') or {}).get('keys') or []:
            i = index[src].get(key)
            if i is None or (floor, key) in have:
                continue
            have.add((floor, key))
            e = it['eid'][i]
            s['fixes']['setAside'].append({
                'floor': floor, 'source': src, 'key': key, 'sig': it['sig'][i], 'rsig': it['rsig'][i],
                'elementId': plan['elementIds'][e] if e >= 0 else None, 'layer': plan['layers'][it['layer'][i]],
                'note': f'RI acceptance: single-line flag {flag["id"]} set aside', 'floorPast': False})
    return s
