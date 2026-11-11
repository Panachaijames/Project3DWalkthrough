"""Reading the stairs of a floor (docs/rooms/DESIGN.md R-7), with options.stairs 'climb'. Owner: R2.

THE TRACER of the rooms scaffold R0: thin but working, so that the whole chain from a drawing to a v2 model with a
stairway is green before R1 and R2 start (R-12.3). R2 replaces the body; the signature is contracts.py's and stays.

What the tracer reads: today's reader's result (FloorBuilt.old_stairs: bank.stairs_of, the flights of three or more
parallel lines 0.19 - 0.37 m apart, with an UP / DN word at one end), turned into StairFound rows. A flight with UP
leaves this floor, one with DN arrives at it; without a word its sense is not known. Not yet (R2's): riser pieces
joined, nosing pairs, lanes by mutual overlap, the median width, skipped risers counted, continuations on other
layers, deeper first steps, landings and turns, arrows and walking lines, the break line.
"""
from __future__ import annotations

import statistics


def find_stairs(fb, net, fixes, X) -> list:
    """-> [contracts.StairFound] of one floor (pass 1), ids `<floor key>-ST<n>` in today's reader's order."""
    S = fb['old_stairs']
    out = []
    for n, st in enumerate(S.get('stairs') or [], 1):
        flights = []
        for f in st['flights']:
            u, nrm, (s0, s1) = f['u'], f['n'], f['s']
            o = list(f['o'])
            sense = {'up': 'leaves', 'down': 'arrives'}.get(f['dir'], '')
            # the risers from the bottom of the flight to its top: an UP word stands at the bottom end, a DN word at
            # the top end (the end the flight arrives at)
            if (f['dir'] == 'up' and f['from'] == 'last') or (f['dir'] == 'down' and f['from'] == 'first'):
                o = o[::-1]
            P = lambda s, oo: (u[0] * s + nrm[0] * oo, u[1] * s + nrm[1] * oo)  # noqa: E731
            risers = [(P(s0, oo), P(s1, oo)) for oo in o]
            steps = [abs(b - a) for a, b in zip(o, o[1:])]
            flights.append({'risers': risers, 'going': round(statistics.median(steps), 4) if steps else 0.0,
                            'width': round(s1 - s0, 4), 'sense': sense, 'lines': list(f['lines'])})
        hull = st['hull']
        end = None
        if len(flights) == 1 and flights[0]['sense']:
            a, b = flights[0]['risers'][0 if flights[0]['sense'] == 'leaves' else -1]
            end = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        out.append({'id': f'{fb["key"]}-ST{n}', 'floor': fb['key'], 'flights': flights, 'landings': [], 'outline': hull,
                    'hull': hull, 'floorEnd': end, 'lines': list(st['lines'])})
    return out
