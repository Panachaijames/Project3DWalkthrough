"""R3: overlay.json with the rooms milestone's fields and flags (docs/rooms/DESIGN.md R-6.1, R-6.3, R-12.4; ACCEPTANCE
2.1 R3), from the reference building's frozen build result (fixtures/rooms/build-result.reference.json):

* the overlay is the frozen `fixtures/rooms/overlay.reference.json`, byte for byte (its new floor fields and its seven
  new flags, written by the scaffold from the report with the texts of R-6.1);
* one flag of every new kind is `fixtures/rooms/flags.every-kind.json`'s (the `stairs-none` raised from the same result
  with the stair taken away);
* each kind's other cases (a gap with no mouth, an answered one, a closed area with no door, a piece taken out under a
  stair, a void too large to cut, walls that never close, a stair that passes a floor, no stair lines at all);
* `fix-unmatched` for the new fixes, and nothing for the ones that matched;
* `plate-dropped` with the old rule only; the old rule's overlay has none of the new fields;
* every overlay made here passes the API's own check (`check_file overlay`).
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

import kit
import test_u4_common as c
from walkthrough_builder.jsonfile import dumps
from walkthrough_builder.out import overlay as ov

ROOMS = kit.ROOMS_FIXTURES
NEW_KINDS = ('slab-gap', 'room-open', 'room-names', 'doorway', 'stair', 'stairs-none', 'stair-clash', 'hole-skipped')


def result() -> dict:
    return c.load_json(ROOMS / 'build-result.reference.json')


def settings() -> dict:
    return c.load_json(ROOMS / 'settings.reference.json')


def ctx(s: dict | None = None) -> dict:
    return {'spec': {'settings': s if s is not None else settings()}, 'sources': []}


def by_kind(o: dict, kind: str) -> list[dict]:
    return [f for f in o['flags'] if f['kind'] == kind]


def no_stair(res: dict) -> dict:
    """The reference result with its stair taken away: nothing climbs between its two floors."""
    res = copy.deepcopy(res)
    res['model']['stairways'] = []
    g = res['report']['floors']['ground']
    g['stairways'] = [r for r in g['stairways'] if r['state'] != 'climb']
    return res


# ---------------------------------------------------------------------------------------------------- the fixtures
def test_the_reference_overlay_is_the_frozen_fixture_byte_for_byte():
    got = ov.overlay(result(), ctx())
    want = (ROOMS / 'overlay.reference.json').read_bytes()
    assert dumps(got, pretty=False) == want
    for fl in got['floors']:
        assert list(fl)[-5:] == ['spaces', 'holes', 'stairs', 'closings', 'unfloored']


def test_one_flag_of_every_new_kind_is_the_fixtures():
    every = c.load_json(ROOMS / 'flags.every-kind.json')['flags']
    got = ov.overlay(result(), ctx())['flags'] + ov.overlay(no_stair(result()), ctx())['flags']
    first = {}
    for f in got:
        if f['kind'] in NEW_KINDS:
            first.setdefault(f['kind'], f)
    assert [first[k] for k in NEW_KINDS] == every


def test_the_reference_flags_carry_the_design_texts():
    o = ov.overlay(result(), ctx())
    gap = by_kind(o, 'slab-gap')[0]
    assert gap['ref'] == {'a': [8.9, 8.9], 'b': [11.8, 8.9]} and gap['at'] == [10.35, 8.9] and gap['severity'] == 'check'
    assert gap['detail'] == 'About 20 m2 beside the walls has no floor: the walls do not close here.'
    assert by_kind(o, 'doorway')[0]['detail'] == ('A gap of 1.20 m between two wall ends was closed as a doorway: no door was '
                                                  'found here.')
    assert by_kind(o, 'room-open')[0]['detail'] == ('GARAGE: its room is not closed (a gap in its walls). Close the gap or place '
                                                    'the name.')
    # RR S6: the names are in the sentence
    assert by_kind(o, 'room-names')[0]['detail'] == ('2 names in one room (LIVING, DINING): an open-plan room, or a wall between '
                                                     'them is missing.')
    assert by_kind(o, 'stair')[0]['detail'] == 'Stair at (3.1, 8.0): kept as lines: which end is the bottom was not found.'
    assert by_kind(o, 'stair-clash')[0]['detail'] == ("1 wall piece of Ground floor under the stair was cut to the stair's "
                                                      'underside.')
    assert by_kind(o, 'hole-skipped')[0] == {**by_kind(o, 'hole-skipped')[0], 'severity': 'info',
                                             'detail': 'An X marks a void on the lowest floor: not cut.'}
    assert not by_kind(o, 'plate-dropped') and not by_kind(o, 'stairs-none')


# ------------------------------------------------------------------------------------------------- the other cases
def test_slab_gap_cases():
    res = result()
    g = res['report']['floors']['ground']['slab']
    u = g['unfloored'][0]
    g['unfloored'] = [{**u, 'mouth': None, 'at': [9.4, 6.7]}, {**u, 'answered': True, 'at': [1.0, 1.0]},
                      {**u, 'area': 3.9, 'at': [2.0, 2.0]}]
    gaps = by_kind(ov.overlay(res, ctx()), 'slab-gap')
    assert len(gaps) == 1, 'an answered area and one under 4 m2 raise none'
    assert gaps[0]['detail'] == ('About 20 m2 beside the walls has no floor: the walls do not close here. Draw a line across the gap '
                                 'if it is inside the building, or say it is outdoors.')
    assert gaps[0]['at'] == [9.4, 6.7] and gaps[0]['ref'] == {}
    # the walls never close round the floor: one flag for the whole floor (R-2.5)
    res = result()
    res['report']['floors']['upper']['slab']['plate'] = 10.0
    m = res['model']
    m['parts'].append({**next(p for p in m['parts'] if p['floor'] == 'upper' and p['kind'] == 'wall'),
                       'o': [[-30.0, -30.0], [-29.8, -30.0], [-29.8, -29.8], [-30.0, -29.8]], 'h': []})
    whole = [f for f in by_kind(ov.overlay(res, ctx()), 'slab-gap') if f['floor'] == 'upper']
    assert len(whole) == 1 and whole[0]['detail'].startswith('The floor plate is 10 m2 of the about ')
    assert whole[0]['detail'].endswith('m2 the walls span: check the wall and glass layers on the Layers step.')


def test_room_open_for_a_closed_area_with_no_door():
    res = result()
    res['report']['floors']['ground']['rooms']['open'].append(
        {'name': '', 'at': [3.0, 4.0], 'space': 'ground-R001', 'area': 160.4, 'why': 'no door'})
    got = by_kind(ov.overlay(res, ctx()), 'room-open')
    assert [f['detail'] for f in got] == ['GARAGE: its room is not closed (a gap in its walls). Close the gap or place the name.',
                                          'A closed area of 160 m2 with no door: is it floor?']
    assert got[1]['ref'] == {'room': 'ground-R001'} and got[1]['severity'] == 'check'


def test_room_open_for_a_lost_room_and_a_name_given_to_a_small_room():
    """RR FID-1: a closed area of 10 m2 or more that is no room, and a name placed by distance in a room under 4 m2."""
    res = result()
    res['report']['floors']['ground']['rooms']['open'] += [
        {'name': '', 'at': [3.0, 4.0], 'area': 52.0, 'why': 'not a room'},
        {'name': 'LIVING & DINING AREA', 'at': [6.0, 4.0], 'room': 'ground-R002', 'area': 1.5, 'why': 'placed by distance'}]
    got = by_kind(ov.overlay(res, ctx()), 'room-open')
    assert [(f['title'], f['severity'], f['ref']) for f in got[1:]] == [
        ('A closed area is not a room', 'check', {}),
        ('LIVING & DINING AREA: placed in a small room nearby', 'check', {'room': 'ground-R002'})]
    assert got[1]['detail'].startswith('A closed area of 52 m2 is not counted as a room: less than half of its edge is wall.')
    assert got[2]['detail'].startswith('LIVING & DINING AREA stands in no room and was given to the nearest one, of 1.5 m2')
    assert len({f['id'] for f in got}) == 3


def test_stair_clash_counts_each_kind_and_the_pieces_taken_out():
    res = result()
    row = res['report']['floors']['ground']['stairClash'][0]
    res['report']['floors']['ground']['stairClash'] = [row, {**row, 'at': [3.0, 4.0]}, {**row, 'kind': 'lintel', 'label': 'g-1'},
                                                       {**row, 'kind': 'lintel', 'z1': None}]
    f = by_kind(ov.overlay(res, ctx()), 'stair-clash')
    assert len(f) == 1 and f[0]['detail'] == ("2 wall pieces and 1 lintel of Ground floor under the stair were cut to the stair's "
                                              'underside. 1 lintel was taken out: no room under the stair.')


def test_hole_skipped_only_for_the_lowest_floor_and_the_large_marks():
    res = result()
    up = res['report']['floors']['upper']['slab']['holes']
    o = [[1.0, 1.0], [10.0, 1.0], [10.0, 8.0], [1.0, 8.0]]
    up += [{'what': 'void', 'area': 63.0, 'at': [5.5, 4.5], 'o': o, 'cut': False, 'why': 'over 60 m2'},
           {'what': 'X mark', 'area': 0.6, 'at': [2.0, 2.0], 'o': o, 'cut': False, 'why': 'narrower than 0.6 m'},
           {'what': 'void', 'area': 0.4, 'at': [3.0, 3.0], 'o': o, 'cut': False, 'why': 'under 0.5 m2'}]
    got = by_kind(ov.overlay(res, ctx()), 'hole-skipped')
    # RR BRK-2: the upper floor's X void that WAS cut is asked about too (info, with its box; the ref stays empty)
    assert [(f['floor'], f['severity'], f['title']) for f in got] == [
        ('ground', 'info', 'A void mark was not cut'), ('upper', 'info', 'An X mark was cut as a void'),
        ('upper', 'check', 'A large void mark was not cut')]
    assert got[1]['detail'] == 'An X marks 5.2 m2 as a void: it was cut out of the floor. If it is floor, say so.'
    assert got[1]['at'] == [4.7, 1.8] and got[1]['bbox'] == [3.4, 0.8, 6.0, 2.8] and got[1]['ref'] == {}
    assert got[2]['detail'] == 'An X marks 63 m2 as a void: is it one?' and got[2]['bbox'] == [1.0, 1.0, 10.0, 8.0]
    # a hole staff kept as floor, a stair well and a lift shaft raise nothing
    res = result()
    res['report']['floors']['upper']['slab']['holes'] = [
        {'what': 'shaft', 'area': 2.0, 'at': [2.0, 2.0], 'o': o, 'cut': False, 'why': 'kept as floor by staff'},
        {'what': 'lift shaft', 'area': 3.0, 'at': [3.0, 3.0], 'o': o, 'cut': True},
        {'what': 'stair well', 'area': 5.0, 'at': [4.0, 4.0], 'o': o, 'cut': True}]
    assert [f['floor'] for f in by_kind(ov.overlay(res, ctx()), 'hole-skipped')] == ['ground']


def test_stairs_none_cases():
    res = no_stair(result())
    f = by_kind(ov.overlay(res, ctx()), 'stairs-none')
    assert len(f) == 1 and (f[0]['floor'], f[0]['severity'], f[0]['ref']) == ('ground', 'check', {})
    # no stair lines at all on either floor
    for fl in res['report']['floors'].values():
        fl['stairways'] = []
    f = by_kind(ov.overlay(res, ctx()), 'stairs-none')
    assert f[0]['detail'] == ("No stair between Ground floor and Upper floor can be climbed. No stair lines were found: is the "
                              "stair's layer set to Stair on the Layers step?") and f[0]['at'] is None
    # stairs kept as lines by choice: no flag
    s = settings()
    s['options']['stairs'] = 'lines'
    assert not by_kind(ov.overlay(res, ctx(s)), 'stairs-none')
    # the old rule: none
    old = c.build_result()
    assert not by_kind(ov.overlay(old, c.bank_ctx(Path(kit.RUN) / 'r3-overlay-old')), 'stairs-none')


def test_stairs_none_a_stair_passing_a_floor_joins_both_pairs():
    res = result()
    m = res['model']
    mid = {**m['floors'][1], 'key': 'mezz', 'name': 'Mezzanine', 'level': 1.5}
    top = {**m['floors'][1], 'key': 'roof', 'name': 'Roof', 'level': 6.0}
    m['floors'] = [m['floors'][0], mid, m['floors'][1], top]
    for k in ('mezz', 'roof'):
        res['floors_frame'][k] = res['floors_frame']['upper']
        res['report']['floors'][k] = copy.deepcopy(res['report']['floors']['upper'])
    got = by_kind(ov.overlay(res, ctx()), 'stairs-none')
    assert [(f['floor'], f['detail'].split('. ')[0]) for f in got] == [('upper', 'No stair between Upper floor and Roof can be climbed')]


def test_fix_unmatched_for_the_new_fixes():
    res = result()
    s = settings()
    s['fixes'].update(closings=[{'floor': 'ground', 'a': [7.0, 5.6], 'b': [7.0, 6.8], 'use': 'none'},
                                {'floor': 'roof', 'a': [1.0, 1.0], 'b': [2.0, 1.0], 'use': 'line'},
                                {'floor': 'ground', 'a': [1.0, 1.0], 'b': [2.0, 1.0], 'use': 'line'},
                                {'floor': 'ground', 'a': [30.0, 1.0], 'b': [30.0, 4.0], 'use': 'line'}],
                      rooms=[{'floor': 'ground', 'at': [50.0, 50.0], 'name': 'X', 'slab': 'auto', 'ceiling': 'auto'},
                             {'floor': 'ground', 'at': [3.0, 3.0], 'name': 'Y', 'slab': 'auto', 'ceiling': 'auto'}],
                      stairs=[{'floor': 'ground', 'at': [40.0, 40.0], 'bottom': None, 'use': 'lines'}])
    res['report']['fixes'].update(closings=[{'fix': 0, 'matched': False}, {'fix': 1, 'matched': False}, {'fix': 2, 'matched': True},
                                            {'fix': 3, 'matched': False}],     # RR BRK-3: on a built floor, no end on a wall
                                  rooms=[{'fix': 0, 'matched': False}, {'fix': 1, 'matched': True}],
                                  stairs=[{'fix': 0, 'matched': False}])
    o = ov.overlay(res, ctx(s))
    got = by_kind(o, 'fix-unmatched')
    assert [(f['floor'], f['title'], f['ref']) for f in got] == [
        ('ground', 'A removed closing is no longer there', {'fix': 0, 'a': [7.0, 5.6], 'b': [7.0, 6.8]}),
        ('roof', 'A closing line finds no floor', {'fix': 1, 'a': [1.0, 1.0], 'b': [2.0, 1.0]}),
        ('ground', 'A closing line meets no wall', {'fix': 3, 'a': [30.0, 1.0], 'b': [30.0, 4.0]}),
        ('ground', 'A room fix finds no room', {'fix': 0}),
        ('ground', 'A stair fix finds no stair', {'fix': 0})]
    assert got[0]['detail'] == ('The removed closing at (7.00, 6.20) is no longer there: the fix is kept in the settings until you '
                                'drop it.')
    assert got[2]['detail'] == ('The closing line at (30.00, 2.50) meets no wall at either end: has the drawing moved? It is kept '
                                'in the settings until you drop it.')
    assert got[3]['detail'] == 'The room fix at (50.00, 50.00) finds no room: it is kept in the settings until you drop it.'
    assert got[4]['at'] == [40.0, 40.0] and all(f['severity'] == 'check' for f in got)
    ids = [f['id'] for f in o['flags']]
    assert len(ids) == len(set(ids))


def test_a_staff_closing_carries_its_fix_and_plate_dropped_is_the_old_rules_only(tmp_path: Path):
    res = result()
    g = res['report']['floors']['ground']
    g['slab']['closings'].append({'kind': 'staff', 'a': [8.9, 8.9], 'b': [11.8, 8.9], 'width': 2.9, 'fix': 0})
    g['platesDropped'] = [{'area': 9.0, 'at': [1.0, 1.0], 'bbox': [0, 0, 1, 1], 'why': 'no door'}]
    o = ov.overlay(res, ctx())
    assert o['floors'][0]['closings'][-1] == {'kind': 'staff', 'a': [8.9, 8.9], 'b': [11.8, 8.9], 'fix': 0}
    assert not by_kind(o, 'plate-dropped')
    p = tmp_path / 'overlay.json'
    p.write_bytes(dumps(o))
    q = tmp_path / 'overlay-no-stair.json'
    q.write_bytes(dumps(ov.overlay(no_stair(result()), ctx())))
    c.assert_checked([('overlay', p), ('overlay', q)])
    # the old rule: no new field, and its plate-dropped flags as before
    old = ov.overlay(c.build_result(), c.bank_ctx(tmp_path / 'old'))
    assert all(not ({'spaces', 'holes', 'stairs', 'closings', 'unfloored'} & set(fl)) for fl in old['floors'])
    assert by_kind(old, 'plate-dropped') and not any(f['kind'] in NEW_KINDS for f in old['flags'])


@pytest.mark.parametrize('kind', NEW_KINDS)
def test_every_new_kind_is_a_flag_kind_of_the_contract(kind):
    text = (kit.APP / 'docs' / 'upload' / 'upload-contracts.ts').read_text(encoding='utf-8')
    assert f"'{kind}'" in text
    assert kind in ov.__doc__
