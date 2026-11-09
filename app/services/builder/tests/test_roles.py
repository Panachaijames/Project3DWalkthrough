"""roles.py: the 17 staff roles and the two derived tables (docs/upload/DESIGN.md U-8.1, U-8.2; ACCEPTANCE 2.1 U0)."""
from __future__ import annotations

import json
import re

import pytest

import kit
from walkthrough_builder import roles

BANK_PROJECT = kit.PROJECT / 'bank_test' / 'src' / 'bank_project.json'
DERIVED_BANK1 = kit.DOCS / 'reference' / 'derived_detector_mapping_bank1.json'


def bank_settings_layers() -> dict[str, str]:
    """BuildSettings.layers for the bank, from fixtures/upload/settings/bank.json (or, before it exists, from
    bank_project.json's roles, which are the app's role names for the bank)."""
    fx = kit.UPLOAD_FIXTURES / 'settings' / 'bank.json'
    if fx.exists():
        return json.loads(fx.read_text(encoding='utf-8'))['layers']
    cfg = json.loads(BANK_PROJECT.read_text(encoding='utf-8'))
    return {name: role for role, names in cfg['layers'].items() for name in names}


def test_staff_roles_equal_the_contract() -> None:
    ts = (kit.DOCS / 'upload-contracts.ts').read_text(encoding='utf-8')
    block = re.search(r'export type LayerRole =(.*?);', ts, re.S).group(1)
    assert tuple(re.findall(r"'([a-z-]+)'", block)) == roles.STAFF_ROLES
    assert len(roles.STAFF_ROLES) == 17


def test_tables_cover_every_staff_role() -> None:
    assert set(roles.BUILDER_OF) == set(roles.STAFF_ROLES) == set(roles.DETECTOR_OF)
    assert set(roles.BUILDER_OF.values()) <= set(roles.ROLES)
    assert {v for v in roles.DETECTOR_OF.values() if v} <= set(roles.DETECTOR_ROLES)


def test_builder_roles_extend_the_bank_builders() -> None:
    src = (kit.PROJECT / 'bank_test' / 'src' / 'plan_items.py').read_text(encoding='utf-8')
    bank = tuple(re.findall(r"'([a-z-]+)'", re.search(r'^ROLES = \((.*?)\)$', src, re.M).group(1)))
    assert roles.ROLES[:len(bank)] == bank
    assert roles.ROLES[len(bank):] == ('screen', 'room-outline')


def test_detector_roles_equal_geomkit() -> None:
    src = (kit.VENDOR / 'geomkit.py').read_text(encoding='utf-8')
    gk = tuple(re.findall(r"'([a-z-]+)'", re.search(r'^ROLES = \((.*?)\)$', src, re.M).group(1)))
    assert roles.DETECTOR_ROLES == gk


@pytest.mark.parametrize('staff,builder,detector', [
    ('wall', 'wall', 'wall'), ('column', 'column', 'column'), ('glass', 'glass', 'glass'),
    ('window', 'window', 'window'), ('door', 'door', 'door'), ('screen', 'screen', 'screen'),
    ('stair', 'stair', 'stair'), ('stair-above', 'stair-above', 'stair'), ('railing', 'railing', 'ignore'),
    ('furniture', 'furniture', 'ignore'), ('room-name', 'room-name', 'ignore'),
    ('room-outline', 'room-outline', None), ('level', 'other', 'ignore'), ('grid', 'grid', 'ignore'),
    ('light', 'other', 'ignore'), ('other', 'other', None), ('ignore', 'ignore', 'ignore'),
])
def test_u82_tables(staff: str, builder: str, detector: str | None) -> None:
    assert roles.BUILDER_OF[staff] == builder
    assert roles.DETECTOR_OF[staff] == detector
    assert roles.builder_role({'L': staff}, 'L') == builder
    assert roles.detector_role({'L': staff}, 'L') == detector


def test_unlisted_layer_is_other() -> None:
    assert roles.builder_role({}, 'ANY') == 'other'
    assert roles.detector_role({}, 'ANY') is None


def test_unknown_role_refused() -> None:
    with pytest.raises(ValueError, match='unknown layer role'):
        roles.detector_layers({'A': 'walls'})


def test_bank_derived_detector_mapping_equals_the_reference() -> None:
    """The derived detector table of the bank's settings is docs/upload/reference/derived_detector_mapping_bank1.json's
    (the one that reproduced the bank's openings, U-0)."""
    want = json.loads(DERIVED_BANK1.read_text(encoding='utf-8'))['layers']
    got = roles.detector_layers(bank_settings_layers())
    assert got == want
    listed = {n for names in got.values() for n in names}
    assert not listed & {'A-FLOR', 'A-FLOR-HRAL-MBND', 'A-DETL', 'A-DETL-GENF'}       # other: read as context


def test_bank_builder_table_equals_bank_project() -> None:
    cfg = json.loads(BANK_PROJECT.read_text(encoding='utf-8'))['layers']
    got = roles.builder_layers(bank_settings_layers())
    assert {r: sorted(v) for r, v in cfg.items()} == got
    assert list(got) == [r for r in roles.ROLES if r in got]


def test_bank_tables_are_consistent() -> None:
    lay = bank_settings_layers()
    assert roles.consistency(roles.builder_layers(lay), roles.detector_layers(lay)) == []


def test_consistency_reports_a_difference() -> None:
    warnings = roles.consistency({'wall': ['A-WALL']}, {'wall': ['A-WALL', 'X']})
    assert len(warnings) == 1 and 'wall' in warnings[0]


def test_level_and_light_are_built_as_other_and_dropped_by_the_detector() -> None:
    lay = {'LV': 'level', 'LT': 'light', 'RO': 'room-outline', 'OT': 'other'}
    assert roles.builder_layers(lay) == {'other': ['LT', 'LV', 'OT'], 'room-outline': ['RO']}
    assert roles.detector_layers(lay) == {'ignore': ['LT', 'LV']}
