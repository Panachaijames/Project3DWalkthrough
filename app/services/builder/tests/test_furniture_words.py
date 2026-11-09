"""After the final check of 9 Nov 2026 (docs/upload/contract-issues/UR.md, "After the final check (9 Nov)"): a grey
furniture family given a kind on the Check step takes that kind at the next build, whatever its capitals, digits,
underscores or symbols.

The Check step saves the family as its flag shows it ('TF2092P', settings.furniture.words[kind]); the vendored kit
(unchanged) matches its words against the family name split at camel case ('TF2092 P'), so such a word never matched:
in the house 5 of the 13 families staff gave a kind stayed grey. build/furniture.py `FamilyWords` now compares a word and
a family in one form (`family_form`: white space removed, lower case) and hands the kit its words in the kit's own
camel-case form.

  * the seven names of the final check (the house's five, SmartTable, a HermanMiller_ family): the kit alone misses
    each; FamilyWords gives each its kind, alone or all together; the acceptance settings' form ('TF2092 P') and the
    screen's ('TF2092P') are one family;
  * a word still matches whole inside longer names (the kit's rule); it cannot capture other families through the kit's
    '|' or a blank word; a skip word still wins; a loose-shape family takes its word; several kinds: the kit's order;
  * family_form against a table of names (apps/web/test/build/furniture-words.test.ts holds the same table for the web
    app's familyForm);
  * a synthetic plan: the flags name the grey families; the words saved exactly as the flags show them; the rebuild
    gives each its kind and no flag is left for them;
  * heavy: the house built with the 13 words as the screen saved them in the final check gives the same model, byte for
    byte, as with the acceptance settings' words; the bank with its word as the screen saves it gives v2's model and CSV.
"""
from __future__ import annotations

import collections

import pytest

from test_u3_helpers import (GOLDEN_CSV, GOLDEN_MODEL, csv_bytes, model_bytes, plan_dxf, plan_settings, read_plan,
                             ref_sources, run_build, settings, sha1, source_ctx)
from walkthrough_builder.build.furniture import FamilyWords, family_form, fk, loose_family
from walkthrough_builder.out.overlay import grey_furniture_flags

HERMAN = 'HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range'   # the bank's own family
#: the final check's names -> a kind the kit's vocabulary does not give them (so only the word can)
SEVEN = {'TF2092P': 'sanitary', 'TF0560P': 'sanitary', 'A$C2619574F': 'sanitary', 'A$C238E5230': 'bed',
         'A$C5BF14633': 'coffee-table', 'SmartTable': 'bar-table', HERMAN: 'sofa'}
#: the house's 13 words as the Check step saved them in the final check (the evidence's flags.json, project-data.json)
HOUSE_SCREEN_WORDS = {
    'sanitary': ['TF2092P', 'TF0560P', 'A$C2619574F', 'klkjlll'], 'sofa': ['bvvvv', 'jkhjhjj', 'kjjkjkkkk'],
    'seat': ['jkjllll'], 'coffee-table': ['fghfh', 'A$C5BF14633'], 'counter': ['A$Ce0b21054'], 'cabinet': ['BASE'],
    'bed': ['A$C238E5230'],
}
SHA = 'd' * 40


def words(w: dict, skip=None) -> FamilyWords:
    return FamilyWords({'words': w, 'skip': skip or []})


# ---------------------------------------------------------------------------------------------------- the rule
def test_the_kit_alone_misses_the_seven_names():
    """The fault itself (UF): the word as the screen saves it, handed to the kit as written, never gives the kind."""
    for name, kind in SEVEN.items():
        assert fk.classify(name, 'I-FURN', {kind: [name]}) != kind, name
    assert fk._camel('TF2092P') == 'TF2092 P' and fk._camel('A$C238E5230') == 'A$C238 E5230'


@pytest.mark.parametrize('name', list(SEVEN))
def test_a_family_word_as_the_check_step_saves_it_gives_its_kind(name):
    kind = SEVEN[name]
    assert words({kind: [name]}).of_block(name, 'I-FURN', name) == kind
    assert words({kind: [name]}).of_block(name, '', '') == kind                        # no layer, no block name
    every = collections.defaultdict(list)
    for n, k in SEVEN.items():
        every[k].append(n)
    assert words(dict(every)).of_block(name, 'I-FURN', name) == kind                   # all seven at once


def test_settings_saved_in_another_form_still_work():
    """The acceptance settings' form ('TF2092 P'), the screen's before and after the fix ('TF2092P'), other cases and
    white space: one family. The words the kit gets are its own camel-case form."""
    for word in ('TF2092P', 'TF2092 P', 'tf2092p', ' TF2092P ', 'TF 2092 P'):
        assert words({'sanitary': [word]}).of_block('TF2092P', 'I-FURN', 'TF2092P') == 'sanitary', word
    fw = words({'sanitary': ['TF2092P'], 'seat': ['Fritz-Hansen']})
    assert fw.kit_words == {'sanitary': ['TF2092 P'], 'seat': ['Fritz-Hansen']}             # the bank's word unchanged
    assert words({'bed': ['A$C238 E5230']}).of_block('A$C238E5230', 'I-FURN', 'A$C238E5230') == 'bed'


def test_a_word_still_matches_whole_inside_longer_names():
    """The kit's rule for words, now whatever the word's capitals: the bank's 'Fritz-Hansen'; 'TF2092P' in a variant."""
    fw = words({'seat': ['Fritz-Hansen'], 'sanitary': ['TF2092P']})
    assert fw.of_block('Fritz-Hansen_SH200 - Default', 'I-FURN', 'Fritz-Hansen_SH200 - Default') == 'seat'
    assert fw.of_block('TF2092P-L', 'I-FURN', 'TF2092P-L') == 'sanitary'
    assert fw.of_block('TF2092PX', 'I-FURN', 'TF2092PX') == 'other'                    # not a whole word
    assert fw.of_block('Office Chair 2', 'I-FURN', 'Office Chair 2') == 'seat'          # the vocabulary as before


def test_a_word_cannot_capture_other_families():
    """'|' is the kit's 'or' and a blank word matches almost anything: such a family's word names that family only."""
    assert fk.classify('Mystery 1', 'I-FURN', {'bed': ['|']}) == 'bed'                 # the kit's own hazard
    fw = words({'bed': ['|', 'A|B', '   ']})
    assert fw.kit_words == {'bed': []}
    assert fw.of_block('Mystery 1', 'I-FURN', 'Mystery 1') == 'other'
    assert fw.of_block('Office Chair 2', 'I-FURN', 'Office Chair 2') == 'seat'
    assert fw.of_block('A|B', 'I-FURN', 'A|B') == 'bed' and fw.of_block('|', 'I-FURN', '|') == 'bed'


def test_skip_words_still_win_and_several_kinds_take_the_kits_order():
    assert words({'sofa': ['Floor Box 1']}).of_block('Floor Box 1', 'I-FURN', 'Floor Box 1') is None   # not furniture
    assert words({'sofa': ['Mystery']}, skip=['Mystery']).of_block('Mystery', 'I-FURN', 'Mystery') is None
    fw = words({'sofa': ['TF2092P'], 'bed': ['TF2092 P']})                     # hand-made: two kinds hold one family
    assert fw.of_block('TF2092P', 'I-FURN', 'TF2092P') == 'bed'                 # the first kind in sorted order
    assert words({'nonsense': ['TF2092P']}).exact == {}                         # an unknown kind is the kit's to refuse


def test_the_family_the_flag_shows_and_loose_shapes():
    """A piece with no family shows its block (out/overlay.py); a loose-shape box's family is 'loose shapes on <layer>'
    and was never given its word before."""
    assert words({'table': ['-12345-View 1']}).of_block('', 'I-FURN', '-12345-View 1') == 'table'
    layer = 'XR_L44$0$I-FURN'
    assert fk.classify('', layer) == 'other'
    assert words({}).of_loose(layer) == 'other'
    assert words({'cabinet': [loose_family(layer)]}).of_loose(layer) == 'cabinet'
    assert words({'cabinet': ['Loose Shapes On XR_L44$0$I-FURN']}).of_loose(layer) == 'cabinet'
    assert words({'cabinet': ['A-FURN']}).of_loose(layer) == 'other'           # a word for another layer's boxes
    assert words({}).of_loose('P-SANR-FIXT') == 'sanitary'                     # the layer rule as before


#: family_form's table; apps/web/test/build/furniture-words.test.ts checks the web app's familyForm on the same rows
#: (code points written as numbers on both sides, so neither file depends on how an editor stores them)
FORMS = [
    ('TF2092P', 'tf2092p'), ('TF2092 P', 'tf2092p'), ('A$C238 E5230', 'a$c238e5230'), ('A$C5BF14633', 'a$c5bf14633'),
    ('SmartTable', 'smarttable'), (HERMAN, 'hermanmiller_seating_aer1a_newaeron_workchair_asize-se101_sizelow-hgtrange'),
    ('Fritz-Hansen_SH200 - Default', 'fritz-hansen_sh200-default'), ('loose shapes on XR_L44$0$I-FURN', 'looseshapesonxr_l44$0$i-furn'),
    (' tab\there\nand\rthere ', 'tabhereandthere'), ('', ''),
]
#: white space by code point (Python's str.isspace set) and a few that are not white space
CODES = [([0x58, 0x0b, 0x59, 0x0c, 0x5a, 0x1c, 0x61, 0x1f, 0x62, 0x85, 0x63, 0xa0, 0x64, 0x1680, 0x65, 0x2000, 0x66, 0x200a, 0x67,
           0x2028, 0x68, 0x2029, 0x69, 0x202f, 0x6a, 0x205f, 0x6b, 0x3000, 0x6c], 'xyzabcdefghijkl'),
         ([0xfeff, 0x42, 0x200b, 0x43], [0xfeff, 0x62, 0x200b, 0x63]),                  # BOM and zero width: kept
         ([0x130], [0x69, 0x307]),                                                       # capital I with dot: as str.lower
         ([0xe1a, 0xe49, 0xe32, 0xe19, 0x20, 0x33, 0x31], [0xe1a, 0xe49, 0xe32, 0xe19, 0x33, 0x31])]   # Thai, a space, 31


def test_family_form_table():
    for name, form in FORMS:
        assert family_form(name) == form, name
    for codes, want in CODES:
        got = family_form(''.join(map(chr, codes)))
        assert got == (want if isinstance(want, str) else ''.join(map(chr, want))), codes
    assert {chr(c) for c in range(0x110000) if chr(c).isspace()} == {chr(c) for c in (
        0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x85, 0xa0, 0x1680, *range(0x2000, 0x200b), 0x2028,
        0x2029, 0x202f, 0x205f, 0x3000)}                                                # the set the web app lists


# ---------------------------------------------------------------------------------------------------- a synthetic plan
def _plan_with_families(tmp):
    """The U3 synthetic plan plus one block per name on I-FURN (1.0 x 0.6 m) and a loose outline on I-FURN."""
    import ezdxf
    path = plan_dxf(tmp / 'families.dxf')
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    for i, name in enumerate(SEVEN):
        b = doc.blocks.new(name)
        b.add_lwpolyline([(0, 0), (1000, 0), (1000, 600), (0, 600)], close=True)
        msp.add_blockref(name, (1000 + 1100 * (i % 7), 4300 if i % 2 else 3600), dxfattribs={'layer': 'I-FURN'})
    msp.add_lwpolyline([(4000, 1200), (5000, 1200), (5000, 1800), (4000, 1800)], close=True, dxfattribs={'layer': 'I-FURN'})
    doc.saveas(path)
    return read_plan(path, tmp / 'families')


def test_a_rebuild_with_the_words_the_flags_show_gives_each_family_its_kind(scratch):
    plan = _plan_with_families(scratch)
    src = [source_ctx(SHA, 'families.dxf', plan['items'], drawing=plan['drawing'], kind='dxf')]
    s = plan_settings([SHA])
    first, _ = run_build(s, src, scratch / 'first')
    flags = {f['ref']['family'] for f in grey_furniture_flags(first['model'], first['floors_frame'])}
    loose = loose_family('I-FURN')
    assert flags >= {'TF2092P', 'TF0560P', 'A$C2619574F', 'A$C238E5230', 'A$C5BF14633', loose}
    # the Check step: each grey family's select -> settings.furniture.words[kind] gains the family as the flag shows it
    given = {**{n: k for n, k in SEVEN.items()}, loose: 'cabinet'}
    s['furniture']['words'] = {}
    for fam, kind in given.items():
        s['furniture']['words'].setdefault(kind, []).append(fam)
    second, _ = run_build(s, src, scratch / 'second')
    kinds = {p['family']: p['kind'] for p in second['model']['furniture']}
    for fam, kind in given.items():
        assert kinds[fam] == kind, fam
    left = {f['ref']['family'] for f in grey_furniture_flags(second['model'], second['floors_frame'])}
    assert not left & set(given)
    assert kinds['Desk 1600x800'] == 'table' and kinds['Chair-Mollie'] == 'seat'        # the others as before


# ---------------------------------------------------------------------------------------------------- heavy
@pytest.mark.heavy
def test_the_house_with_the_words_as_the_screen_saved_them(ref, tmp_path):
    """The final check's house path: its 13 words as the Check step saved them give the same model, byte for byte, as
    the acceptance settings' words (written in the kit's split form); before the fix 5 families stayed grey."""
    a = settings('house')
    b = settings('house')
    b['furniture']['words'] = {k: list(v) for k, v in HOUSE_SCREEN_WORDS.items()}
    res_a, _ = run_build(a, ref_sources('house', a, ref), tmp_path / 'acceptance', 'proj')   # the heavy fixture holds
    res_b, _ = run_build(b, ref_sources('house', b, ref), tmp_path / 'screen', 'proj')       # the machine run lock
    assert model_bytes(res_b['model']) == model_bytes(res_a['model'])
    assert csv_bytes(res_b['model']) == csv_bytes(res_a['model'])
    grey = {p['family'] for p in res_b['model']['furniture'] if p['kind'] == 'other'}
    assert not grey & {w for ws in HOUSE_SCREEN_WORDS.values() for w in ws}
    kinds = collections.defaultdict(set)
    for p in res_b['model']['furniture']:
        kinds[p['family']].add(p['kind'])
    assert kinds['TF2092P'] == {'sanitary'} and kinds['A$C238E5230'] == {'bed'} and kinds['A$C5BF14633'] == {'coffee-table'}


@pytest.mark.heavy
def test_the_bank_with_its_word_as_the_screen_saves_it(ref, tmp_path):
    """The owner's bank path: 'Fritz-Hansen_SH200 - Default' given Chair / stool on the Check step: v2's model and CSV."""
    s = settings('bank')
    s['furniture']['words'] = {'seat': ['Fritz-Hansen_SH200 - Default']}
    res, _ = run_build(s, ref_sources('bank', s, ref), tmp_path / 'bank', 'bank-sampeng')
    assert sha1(model_bytes(res['model'])) == GOLDEN_MODEL and sha1(csv_bytes(res['model'])) == GOLDEN_CSV
