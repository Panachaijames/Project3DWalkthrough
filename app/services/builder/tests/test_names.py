"""names.py: normalised layer names, block families, element ids (docs/upload/DESIGN.md U-7.2, U-7.3, U-8.4)."""
from __future__ import annotations

import pickle
import re

import pytest

import kit
from walkthrough_builder import names


@pytest.mark.parametrize('raw,want', [
    ('Xr_SDC_DD_ID-PRS-ID wall$0$DA-DOOR-WIND', 'DA-DOOR-WIND'),          # U-8.4's example
    ('a-wall', 'A-WALL'),
    ('  A-2.Noi   That  ', 'A-2.NOI THAT'),
    ('A-2. Noi That - bo', 'A-2. NOI THAT - BO'),
    ('XR_L44 Plan$0$A-WALL', 'A-WALL'),
    ('X$0$Y$0$wall\tline', 'WALL LINE'),                                  # the LAST $0$; tabs are whitespace
    ('0', '0'),
    ('ชั้น 1', 'ชั้น 1'),                                                   # Thai stays as it is
])
def test_normalise_layer(raw: str, want: str) -> None:
    assert names.normalise_layer(raw) == want


@pytest.mark.parametrize('raw,want', [
    ('XR_L44$0$SINK-720-400', 'SINK-720-400'),                            # U-7.3's example
    ('M_Chair-Mollie-1234567-Level 1', 'M_Chair-Mollie'),
    ('Basic Wall _ GLASS WALL 2600H 20X100 - ___-765432-Level 2', 'Basic Wall _ GLASS WALL 2600H 20X100 - ___'),
    ('26-0216-AR-V12-Level 1', '26-0216-AR'),                              # a V# view block
    ('Desk 1600x800', 'Desk 1600x800'),
    ('A$C59a32014', 'A$C59a32014'),
    ('XR$0$Door-Single-12345-Level 1', 'Door-Single'),
    ('Door - 1234-x', 'Door - 1234-x'),                                    # 4 digits: no element id
])
def test_family(raw: str, want: str) -> None:
    assert names.family(raw) == want


def test_family_is_the_bank_builders_rule_on_names_without_xref() -> None:
    src = (kit.PROJECT / 'bank_test' / 'src' / 'build_model.py').read_text(encoding='utf-8')
    pat = re.search(r"re\.match\(r'(\^\(\.\*\?\)-\(\\d\{5,\}\|V\\d\+\)-)', name\)", src).group(1)
    assert pat == names.REVIT_SUFFIX.pattern


@pytest.mark.parametrize('path,want', [
    ('', None),
    ('Door-Single-123456-Level 1', '123456'),
    ('26-0216-AR-V12-Level 1>Door-Single-123456-Level 1', '123456'),
    ('Outer-111111-x>Inner-222222-y', '222222'),                           # the innermost name that has one
    ('Outer-111111-x>Plain', '111111'),
    ('Thing-11111-22222-z', '22222'),                                      # the last run of one name
    (['A-99999-b', 'C'], '99999'),
    ('A-1234-b', None),
])
def test_element_id(path, want) -> None:
    assert names.element_id(path) == want


def test_element_depth() -> None:
    assert names.element_depth('V-x>Door-123456-L1>Leaf') == 1
    assert names.element_depth('A>B') is None


def test_family_and_element_id_on_the_bank_blocks(ref) -> None:
    """On every INSERT of the bank's two reference caches: family() agrees with the bank builder's own family() (no
    xref names in the bank), and an INSERT's element id is the last 5+ digit run of its own name."""
    pat = re.compile(r'^(.*?)-(\d{5,}|V\d+)-')
    seen = 0
    for n in ('bank1', 'bank2'):
        with open(kit.ref_prims(n), 'rb') as f:
            items = pickle.load(f)['items']
        for d in items:
            if d['t'] != 'INSERT':
                continue
            nm = d['name']
            m = pat.match(nm)
            assert names.family(nm) == (m.group(1) if m else nm).strip()
            runs = re.findall(r'(?=-(\d{5,})-)', nm)
            if runs:
                assert names.element_id(names.split_path(d['path']) + [nm]) == runs[-1]
            seen += 1
    assert seen > 100
