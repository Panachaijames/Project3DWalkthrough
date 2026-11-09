"""keys.py: geometry signatures sig / rsig (docs/upload/DESIGN.md U-7.2, U-10.6; ACCEPTANCE 2.1 U0)."""
from __future__ import annotations

import math
import pickle
import re

import pytest

import kit
from walkthrough_builder import keys

LINE = {'t': 'LINE', 'lay': 'A-WALL', 'path': '', 'pts': [[1.0, 2.0], [3.0, 2.0]], 'closed': False}


def moved(d: dict, dx: float, dy: float, turn: float = 0.0, k: float = 1.0) -> dict:
    """The item turned by `turn` degrees about the origin, then moved; coordinates divided by k (a cache frame)."""
    c, s = math.cos(math.radians(turn)), math.sin(math.radians(turn))

    def f(p):
        x, y = p
        return [(x * c - y * s + dx) / k, (x * s + y * c + dy) / k]
    out = dict(d)
    if 'pts' in d:
        out['pts'] = [f(p) for p in d['pts']]
    if 'loops' in d:
        out['loops'] = [[f(p) for p in loop] for loop in d['loops']]
    if 'ins' in d:
        out['ins'] = f(d['ins'])
    if 'rot' in d:
        out['rot'] = round((d['rot'] + turn) % 360, 3)
    return out


def test_twelve_hex() -> None:
    assert re.fullmatch(r'[0-9a-f]{12}', keys.sig(LINE))


def test_line_is_always_read_backwards_so_two_directions_differ() -> None:
    # plan_items._signature reverses every LINE (and only open polylines whose first point lies after their last)
    back = dict(LINE, pts=LINE['pts'][::-1])
    assert keys.sig(back) != keys.sig(LINE)
    assert keys._parts(LINE, lambda q: q, None)[2] == [(3.0, 2.0), (1.0, 2.0)]


def test_open_polyline_direction_does_not_matter() -> None:
    a = {'t': 'LWPOLYLINE', 'lay': 'A', 'pts': [[0, 0], [1, 0], [1, 1]], 'closed': False}
    b = dict(a, pts=a['pts'][::-1])
    assert keys.sig(a) == keys.sig(b)


def test_closed_ring_start_does_not_matter() -> None:
    a = {'t': 'LWPOLYLINE', 'lay': 'A', 'pts': [[1, 0], [1, 1], [0, 1], [0, 0]], 'closed': True}
    b = dict(a, pts=a['pts'][2:] + a['pts'][:2])
    assert keys.sig(a) == keys.sig(b)


def test_layer_type_and_points_matter_rounding_to_a_millimetre() -> None:
    assert keys.sig(dict(LINE, lay='B')) != keys.sig(LINE)
    assert keys.sig(dict(LINE, t='LWPOLYLINE')) != keys.sig(LINE)
    near = dict(LINE, pts=[[1.0002, 2.0], [3.0, 2.0004]])
    assert keys.sig(near) == keys.sig(LINE)
    far = dict(LINE, pts=[[1.002, 2.0], [3.0, 2.0]])
    assert keys.sig(far) != keys.sig(LINE)


def test_negative_zero_is_zero() -> None:
    a = dict(LINE, pts=[[-0.0001, 0.0], [1.0, 0.0]])
    b = dict(LINE, pts=[[0.0001, 0.0], [1.0, 0.0]])
    assert keys.sig(a) == keys.sig(b)


def test_k_scales_cache_items_exactly_as_scaled_items() -> None:
    cache = {'t': 'LINE', 'lay': 'A', 'pts': [[0.0393700787, 0.0], [0.0787401575, 0.0]]}     # inches / 1000
    metres = dict(cache, pts=[[x * 25.4, y * 25.4] for x, y in cache['pts']])
    assert keys.sig(cache, k=25.4) == keys.sig(metres)


@pytest.mark.parametrize('item', [
    {'t': 'HATCH', 'lay': 'A-WALL-PATT', 'loops': [[[0, 0], [1, 0], [1, 0.2], [0, 0.2]]], 'solid': True, 'pattern': ''},
    {'t': 'TEXT', 'lay': 'A-AREA-IDEN', 'ins': [5.0, 6.0], 'text': 'LOBBY'},
    {'t': 'ATTRIB', 'lay': 'X', 'ins': [5.0, 6.0], 'text': '1', 'tag': 'NO', 'block': 'B'},
    {'t': 'INSERT', 'lay': 'I-FURN', 'name': 'Chair-Mollie-1234567-L1', 'ins': [5.0, 6.0], 'rot': 90.0, 'sx': 1.0,
     'sy': 1.0, 'path': 'V-x'},
])
def test_every_item_kind_has_a_stable_sig(item: dict) -> None:
    assert keys.sig(item) == keys.sig(dict(item))
    assert keys.sig(item) != keys.sig(dict(item, lay='OTHER'))


def test_insert_sig_follows_name_turn_scale_and_path() -> None:
    ins = {'t': 'INSERT', 'lay': 'I', 'name': 'N', 'ins': [0, 0], 'rot': 0.0, 'sx': 1.0, 'sy': 1.0, 'path': ''}
    for change in ({'name': 'M'}, {'rot': 1.0}, {'sx': -1.0}, {'path': 'P'}):
        assert keys.sig(dict(ins, **change)) != keys.sig(ins)


def test_rsig_empty_without_an_element() -> None:
    assert keys.rsig(LINE, None) == ''


ELEMENT = {'t': 'INSERT', 'lay': 'A-DOOR', 'name': 'Door-Single-123456-Level 1', 'ins': [10.0, 20.0], 'rot': 30.0,
           'sx': 1.0, 'sy': 1.0, 'path': 'V-x-V1-L1'}
LEAF = {'t': 'LWPOLYLINE', 'lay': 'A-DOOR', 'path': 'V-x-V1-L1>Door-Single-123456-Level 1',
        'pts': [[10.0, 20.0], [10.5, 20.8660254], [10.4, 20.9]], 'closed': False}


@pytest.mark.parametrize('dx,dy,turn', [(0, 0, 0), (7.25, -3.5, 0), (0, 0, 90), (-12.0, 4.0, 47.5), (3, 3, 180)])
def test_rsig_survives_moving_and_turning_the_element(dx, dy, turn) -> None:
    e2, l2 = moved(ELEMENT, dx, dy, turn), moved(LEAF, dx, dy, turn)
    assert keys.rsig(l2, e2) == keys.rsig(LEAF, ELEMENT)
    if (dx, dy, turn) != (0, 0, 0):
        assert keys.sig(l2) != keys.sig(LEAF)


def test_rsig_tells_lines_of_one_element_apart() -> None:
    other = dict(LEAF, pts=[[10.0, 20.0], [10.9, 20.0]])
    assert keys.rsig(other, ELEMENT) != keys.rsig(LEAF, ELEMENT)


def test_rsig_of_a_nested_insert_keeps_its_family_not_its_name() -> None:
    inner = {'t': 'INSERT', 'lay': 'A-DOOR', 'name': 'Handle-765432-L1', 'ins': [10.4, 20.1], 'rot': 45.0, 'sx': 1.0,
             'sy': 1.0, 'path': 'V>Door-Single-123456-Level 1'}
    renumbered = dict(inner, name='Handle-999999-L1', path='W>Door-Single-123456-Level 1')
    assert keys.rsig(renumbered, ELEMENT) == keys.rsig(inner, ELEMENT)
    assert keys.sig(renumbered) != keys.sig(inner)


def test_rsig_in_a_cache_frame_equals_metres() -> None:
    k = 25.4
    e_cache, l_cache = moved(ELEMENT, 0, 0, 0, k), moved(LEAF, 0, 0, 0, k)
    assert keys.rsig(l_cache, e_cache, k=k) == keys.rsig(LEAF, ELEMENT)


def test_sig_on_the_bank_cache_is_the_dedupe_signature(ref) -> None:
    """On bank1's reference cache: two items share a sig exactly when plan_items._signature calls them duplicates
    (the INSERT / pts / loops / text branches; mm, so k = 1)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('plan_items_ref', kit.PROJECT / 'bank_test' / 'src' / 'plan_items.py')
    pi = importlib.util.module_from_spec(spec)
    import sys
    sys.dont_write_bytecode = True
    spec.loader.exec_module(pi)
    with open(kit.ref_prims('bank1'), 'rb') as f:
        items = pickle.load(f)['items']
    by_sig: dict[str, object] = {}
    n = 0
    for d in items:
        if not (d.get('pts') or 'loops' in d or 'text' in d or d['t'] == 'INSERT'):
            continue
        s = keys.sig(d)
        sigtuple = pi._signature(d)
        if s in by_sig:
            assert by_sig[s] == sigtuple
        by_sig[s] = sigtuple
        n += 1
    assert n > 5000
    assert len(by_sig) == len({pi._signature(d) for d in items if d.get('pts') or 'loops' in d or 'text' in d
                               or d['t'] == 'INSERT'})
