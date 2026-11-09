"""U2: level tags, grid labels and their lines, area proposals (docs/upload/DESIGN.md U-7.3, U-9.2, U-9.4; ACCEPTANCE
A-4, 2.1 U2)."""
from __future__ import annotations

import re

import pytest

import kit
from walkthrough_builder import areas as A
from walkthrough_builder import grid as G
from walkthrough_builder import levels as L

REFERENCE = (kit.DOCS / 'reference' / 'read_drawing.py').read_text(encoding='utf-8')


def _source_of(var: str) -> str:
    return re.search(rf"^{var} = re\.compile\((r'.*')\)$", REFERENCE, re.M).group(1)


def test_level_and_grid_patterns_are_copied_verbatim() -> None:
    assert L.LEVEL_RE.pattern == eval(_source_of('LEVEL_RE')) and L.LEVEL_RE.flags == re.compile('').flags
    assert G.GRID_RE.pattern == eval(_source_of('GRID_RE')) and G.GRID_RE.flags == re.compile('').flags
    assert r'[+\-±]' in L.LEVEL_RE.pattern                                # the escaped sign class (U-7.3)


def row(text, x=0.0, y=0.0, layer='SPEC', kind='TEXT', tag=None):
    return {'text': text, 'x': x, 'y': y, 'layer': layer, 'kind': kind, 'tag': tag}


@pytest.mark.parametrize('text, value', [
    ('+0.90', 0.9), ('-1.20', -1.2), ('±0.00', 0.0), ('FFL +3.50', 3.5), ('F.F.L. +3.50', 3.5), ('EL. 2,40', 2.4),
    ('LEVEL: 7.95', 7.95), ('LV=4.800', 4.8), ('S.S.L -0.050', -0.05), ('+900.00', 0.9), ('1.03', 1.03),
    (' +4.80 m', 4.8), ('T.O.S +12.30M', 12.3),
])
def test_level_tag_values(text, value) -> None:
    assert L.value_of(text, None) == pytest.approx(value)


@pytest.mark.parametrize('text', ['W1.20', 'D2.10', 'A1.00', 'R1.50', 'x0.900', '1.2', '+12', 'LOBBY', '1 : 100',
                                  '1234.00', 'FL', ''])
def test_door_and_window_tags_and_others_are_never_level_tags(text) -> None:
    assert L.value_of(text, None) is None


def test_tagged_attribs_count_with_a_number_and_blank_ones_do_not() -> None:
    assert L.value_of('+4.80', 'LEVEL') == pytest.approx(4.8)
    assert L.value_of('about 3.5', 'ELEV') == pytest.approx(3.5)          # not LEVEL_RE, the tag makes it one
    assert L.value_of('', 'LEVEL') is None                                 # a blank mark says no level (U2.md)
    assert L.value_of('n/a', 'FFL') is None
    assert L.value_of('3.5', 'NAME') is None                               # '3.5' has one decimal: no LEVEL_RE


def test_level_tags_rows_labels_and_order() -> None:
    rows = [row('+4.80', 10, 50, 'SPEC', 'ATTRIB', 'LEVEL'), row('ระดับพื้นชั้นที่ 2', 12, 50.2, 'RNAME'),
            row('+0.90', 10, 45), row('ระดับพื้นชั้นที่ 1', 11, 45.3, 'RNAME'), row('+7.95', 10, 47.5),
            row('', 10.5, 45, 'SPEC', 'ATTRIB', 'LEVEL'), row('far away', 30, 45, 'RNAME'), row('+9.05', 50, 50)]
    tags = L.level_tags(rows)
    assert [t['value'] for t in tags] == [0.9, 4.8, 7.95, 9.05]
    assert [t['label'] for t in tags] == ['ระดับพื้นชั้นที่ 1', 'ระดับพื้นชั้นที่ 2', 'ระดับพื้นชั้นที่ 1', None]
    assert tags[1]['source'] == 'attrib' and tags[0]['source'] == 'text'
    assert set(tags[0]) == {'x', 'y', 'value', 'text', 'layer', 'source', 'label'}


@pytest.mark.parametrize('text', ['1', '12', 'A', 'AB', "A'", 'A′', "1'", 'A1', 'A.1', 'A-1', 'H2', '1/2', '1.2',
                                  '1-2', ' C '])
def test_grid_labels_accepted(text) -> None:
    assert G.is_label(text, 'S-GRID-IDEN')


@pytest.mark.parametrize('text', ['ABC', '123', 'a', 'LOBBY', 'A1B', '1/2/3', 'A.1.2', ''])
def test_grid_labels_refused(text) -> None:
    assert not G.is_label(text, 'S-GRID-IDEN')


def test_grid_label_layers_its_own_or_an_enclosing_inserts() -> None:
    assert G.is_label('A', 'GRID-01') and G.is_label('A', 'x-axis') and G.is_label('A', 'S-GRID')
    assert not G.is_label('A', 'A-ANNO-TEXT')
    assert G.is_label('A', '0', ('A-ANNO', 'S-GRID-IDEN'))                # inside a block on a grid layer


def label(text, x, y, layer='S-GRID-IDEN', blays=()):
    return {'text': text, 'x': x, 'y': y, 'layer': layer, 'block': None, 'blays': blays}


def test_grid_line_by_its_end_or_passing_and_the_longest_wins() -> None:
    lines = [((0.0, 5.6), (0.0, -20.0)),          # ends 0.6 m below the bubble at (0, 6.2): the grid line, 25.6 m
             ((0.0, 5.7), (0.0, 5.0)),            # a short tick, also near: shorter, loses
             ((-30.0, 10.25), (30.0, 10.25))]     # passes 0.25 m from the bubble at (3, 10): taken for it
    out = G.grid_labels([label('1', 0.0, 6.2), label('A', 3.0, 10.0), label('B', 50, 50), label('LOBBY', 0, 6),
                         label('2', 0.0, 6.2, layer='A-ANNO')], lines)
    assert [o['text'] for o in out] == ['1', 'A', 'B']
    one, a, b = out
    assert one['line'] == [[0.0, 5.6], [0.0, -20.0]] and one['direction'] == [0.0, -1.0]
    assert a['line'] is not None and a['direction'] in ([1.0, 0.0], [-1.0, 0.0])
    assert b['line'] is None and b['direction'] is None
    assert set(one) == {'text', 'x', 'y', 'layer', 'block', 'direction', 'line'}


def test_grid_line_ends_further_than_a_metre_are_not_taken() -> None:
    out = G.grid_labels([label('1', 0.0, 7.0)], [((0.0, 5.6), (0.0, -20.0))])
    assert out[0]['line'] is None


def _block(x0, y0, w, h, layer='A-WALL'):
    """A w x h piece of drawing: short lines every metre (the areas sample points, as areas_propose.py does, so a
    piece must be dense, as real plans are)."""
    out = []
    for i in range(int(w) + 1):
        for j in range(int(h) + 1):
            x, y = x0 + i, y0 + j
            out.append({'t': 'LINE', 'lay': layer, 'pts': [[x, y], [x + 0.5, y]], 'closed': False})
    return out


def test_areas_separate_drawings_and_guess_what_they_are() -> None:
    plan = _block(0, 0, 20, 15)
    elev = _block(40, 0, 20, 10, layer='A-ELEV')
    tiny = _block(100, 100, 3, 3)                                          # 16 m2 cells: under 25 m2, dropped
    items = plan + elev + tiny + [{'t': 'TEXT', 'lay': 'X', 'ins': [500.0, 500.0], 'text': 'far'}]
    got = A.propose_areas(items, 1.0, wall_layers={'A-WALL'}, door_points=[(5, 5), (8, 5)],
                          level_points=[(45, 5), (45, 8)])
    assert [(g['id'], g['looks']) for g in got] == [('a1', 'plan'), ('a2', 'elevation')]
    assert got[0]['bbox'] == [0.0, 0.0, 21.0, 16.0]
    assert got[0]['items'] == len(plan) == got[0]['wallItems']
    assert got[1]['wallItems'] == 0


def test_areas_inside_a_larger_box_join_it_and_reading_order() -> None:
    main = _block(0, 0, 30, 20)
    inner = _block(10, 30, 4, 7)          # a cluster 10 m above a plan (bubbles): its box lies ... outside
    sliver = _block(28, 2, 8, 15)         # overlapping the plan's box by more than 30 %: joins it
    top = _block(0, 60, 10, 8)
    got = A.propose_areas(main + sliver + inner + top, 1.0)
    boxes = [g['bbox'] for g in got]
    assert [0.0, 0.0, 37.0, 21.0] in boxes                                # the plan and the sliver, one box
    assert boxes[0] == [0.0, 60.0, 11.0, 69.0]                             # the top row first
    assert [g['id'] for g in got] == [f'a{i + 1}' for i in range(len(got))]


def test_areas_ignore_texts_inserts_and_broken_points() -> None:
    items = _block(0, 0, 10, 10) + [{'t': 'INSERT', 'lay': 'A', 'ins': [100.0, 100.0], 'name': 'B'},
                                    {'t': 'LINE', 'lay': 'A', 'pts': [[float('nan'), 0.0], [1e12, 1.0]]}]
    got = A.propose_areas(items, 1.0)
    assert len(got) == 1 and got[0]['bbox'] == [0.0, 0.0, 11.0, 11.0]
