"""U3: the two readings of a floor's items (docs/upload/DESIGN.md U-9.1) and the settings coercion (U-10.4).

Per item: the first floor whose area holds the item (after scaling to metres), none for an item with no points, the
dedupe of plan_items.load_floor. Whole subtrees: an INSERT whose insertion point lies outside the box but whose
drawing lies inside goes to that floor with all of it; a container straddling two floors is walked into; a piece with
no majority is left out and counted; under wholeFile both readings are one list.
"""
from __future__ import annotations

import pytest

from walkthrough_builder.build import BuildError
from walkthrough_builder.build import items as I
from walkthrough_builder.build import settings as ST

LT = {'A-WALL': 'Continuous', 'FURN': 'Continuous', '0': 'Continuous'}


def line(x0, y0, x1, y1, depth=0, path='', lay='A-WALL', k=None):
    return {'t': 'LINE', 'lay': lay, 'depth': depth, 'path': path, 'h': 'T', 'k': k or f'{x0},{y0}',
            'pts': [[x0, y0], [x1, y1]], 'closed': False, 'lt': 'BYLAYER'}


def insert(name, x, y, depth=0, path='', lay='FURN', k=None):
    return {'t': 'INSERT', 'lay': lay, 'depth': depth, 'path': path, 'h': 'T', 'k': k or name, 'name': name,
            'ins': [x, y], 'rot': 0.0, 'sx': 1.0, 'sy': 1.0}


def box(x0, x1, pad=0.0, match='all'):
    return {'kind': 'box', 'bbox': [x0, 0.0, x1, 10.0], 'pad': pad, 'match': match}


FLOORS = [{'key': 'a', 'area': box(0.0, 10.0)}, {'key': 'b', 'area': box(20.0, 30.0)}]
ROLES = I.RoleOf({'A-WALL': 'wall', 'FURN': 'furniture'})


def keys(ds):
    return [d['k'] for d in ds]


def test_per_item_tags_after_scaling_and_no_points_in_no_floor():
    items = [line(1.0, 1.0, 2.0, 1.0, k='in-a'), line(21.0, 1.0, 22.0, 1.0, k='in-b'), line(9.0, 1.0, 11.0, 1.0, k='across'),
             {'t': 'HATCH', 'lay': 'A-WALL', 'depth': 0, 'path': '', 'h': 'H', 'k': 'empty', 'loops': []},
             line(1.0, 1.0, 2.0, 1.0, k='dup')]
    r = I.read_floors(items, FLOORS, 'mm', ROLES, LT)
    assert keys(r['a']['items']) == ['in-a'] and keys(r['b']['items']) == ['in-b']     # 'across' fits neither; 'dup' deduped
    assert r['a']['noPoints'] == 1
    # inches: the cache is DXF units / 1000, so the same numbers are 25.4 times further in metres
    r = I.read_floors([line(0.1, 0.1, 0.2, 0.1, k='inch')], [{'key': 'a', 'area': box(2.0, 6.0)}], 'in', ROLES, LT)
    assert keys(r['a']['items']) == ['inch'] and r['a']['items'][0]['pts'][0] == pytest.approx([2.54, 2.54])


def test_whole_subtree_goes_with_the_majority_of_its_drawing():
    chair = [insert('Chair', -0.5, 5.0, k='C'),                                         # inserted outside a's box ...
             line(0.5, 5.0, 1.5, 5.0, depth=1, path='Chair', lay='0', k='C/1'),       # ... drawn inside it
             line(0.5, 6.0, 1.5, 6.0, depth=1, path='Chair', lay='0', k='C/2')]
    walls = [line(1.0, 1.0, 9.0, 1.0, k='W1'), line(21.0, 1.0, 29.0, 1.0, k='W2')]
    r = I.read_floors(walls + chair, FLOORS, 'mm', ROLES, LT)
    assert keys(r['a']['items']) == ['W1', 'C/1', 'C/2']                               # per item: the INSERT is out
    assert keys(r['a']['src']) == ['W1', 'C', 'C/1', 'C/2']                            # whole subtree: in, in order
    assert r['a']['subtreesOutside'] == 0


def test_container_straddling_two_floors_is_walked_into_and_a_split_piece_left_out():
    view = [insert('View', 0.0, 0.0, lay='0', k='V'),
            insert('Desk', 2.0, 2.0, depth=1, path='View', k='V/D'),
            line(2.0, 2.0, 3.0, 2.0, depth=2, path='View>Desk', lay='0', k='V/D/1'),
            insert('Bed', 22.0, 2.0, depth=1, path='View', k='V/B'),
            line(22.0, 2.0, 24.0, 2.0, depth=2, path='View>Bed', lay='0', k='V/B/1'),
            insert('Bench', 9.0, 3.0, depth=1, path='View', k='V/X'),                  # half in a, half outside
            line(8.0, 3.0, 12.0, 3.0, depth=2, path='View>Bench', lay='0', k='V/X/1'),
            line(12.0, 4.0, 13.0, 4.0, depth=2, path='View>Bench', lay='0', k='V/X/2')]
    r = I.read_floors([line(1.0, 1.0, 9.0, 1.0, k='W1')] + view, FLOORS, 'mm', ROLES, LT)
    assert keys(r['a']['src']) == ['W1', 'V', 'V/D', 'V/D/1']
    assert keys(r['b']['src']) == ['V/B', 'V/B/1']
    assert r['a']['subtreesOutside'] == 1                                              # the bench: never split, counted


def test_whole_file_gives_one_list():
    items = [line(1.0, 1.0, 2.0, 1.0, k='a'), insert('Chair', 50.0, 50.0, k='C'),
             line(50.0, 50.0, 51.0, 50.0, depth=1, path='Chair', lay='0', k='C/1')]
    r = I.read_floors(items, [{'key': 'a', 'area': {'kind': 'wholeFile'}}], 'mm', ROLES, LT)
    assert r['a']['src'] is r['a']['items'] and r['a']['n_layers'] == 3


def test_roles_from_the_settings():
    role = I.RoleOf({'A-WALL': 'wall', 'LEV': 'level', 'LT': 'light', 'GR': 'screen', 'RO': 'room-outline'})
    assert role('A-WALL') == {'wall'} and role('LEV') == {'other'} and role('LT') == {'other'}
    assert role('GR') == {'screen'} and role('RO') == {'room-outline'} and role('unlisted') == {'other'}
    assert role('a-wall') == {'other'}                                                 # exact names (the settings' keys)


def test_settings_coercion():
    s = {'floors': [{'key': 'F', 'name': 'F', 'source': 'x', 'level': 0, 'wallHeight': 3, 'slabThickness': None,
                     'doorHead': 2, 'windowSill': None, 'windowHead': None, 'area': {'kind': 'box', 'bbox': [0, 0, 1, 1],
                                                                                         'pad': 0, 'match': 'any'}}],
         'furniture': {'heights': {'plant': 2500.0, '_why': 'x'}, 'bases': {'tv': 900}, 'minSize': 0},
         'defaults': {'doorHead': 2, 'singleLineHeight': 1}, 'options': {'offset': [1, 0]},
         'fixes': {'openings': [{'a': [0, 0], 'b': [1, 0], 'head': 2, 'sill': None}]}}
    c = ST.coerce(s)
    f = c['floors'][0]
    assert all(type(v) is float for v in (f['level'], f['wallHeight'], f['doorHead'], f['area']['pad'], *f['area']['bbox']))
    assert c['furniture']['heights'] == {'plant': 2500} and type(c['furniture']['heights']['plant']) is int
    assert type(c['furniture']['minSize']) is float and c['furniture']['minDepth'] is None
    assert c['defaults']['doorHead'] == 2.0 and type(c['defaults']['windowSill']) is float
    assert c['options']['offset'] == [1.0, 0.0] and c['options']['plinth'] == 'auto'
    assert type(c['fixes']['openings'][0]['head']) is float
    assert s['floors'][0]['level'] == 0 and type(s['floors'][0]['level']) is int        # the input is untouched
    s['floors'][0]['wallHeight'] = '3'
    with pytest.raises(BuildError) as e:
        ST.coerce(s)
    assert e.value.code == 'bad_settings'
