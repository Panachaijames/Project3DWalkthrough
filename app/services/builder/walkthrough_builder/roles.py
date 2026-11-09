"""Layer roles: the 17 staff roles and the two tables derived from them (docs/upload/DESIGN.md U-8.1, U-8.2).

One staff mapping (BuildSettings.layers: exact layer name -> staff role) gives
  * the builder's roles (the bank builder's plan_items roles, plus `screen` and `room-outline`), and
  * the detector's roles (geomkit.ROLES), where `room-outline` and `other` get no role at all: the detector still reads
    them as context (the bank's A-FLOR is its kerb context: dropping it changes 3 records), while `ignore` drops a layer
    everywhere (U-18.7).
Pure functions, no I/O. Scaffold U0; frozen after it (a defect goes in your own docs/upload/contract-issues/U<n>.md).
"""
from __future__ import annotations

from collections.abc import Mapping

#: The staff roles of the Layers step, in the order the select lists them (upload-contracts.ts LayerRole, U-8.1).
STAFF_ROLES: tuple[str, ...] = (
    'wall', 'column', 'glass', 'window', 'door', 'screen', 'stair', 'stair-above', 'railing',
    'furniture', 'room-name', 'room-outline', 'level', 'grid', 'light', 'other', 'ignore',
)

#: The builder's roles: bank_test/src/plan_items.py ROLES in their order, then the two this milestone adds (U-8.2).
ROLES: tuple[str, ...] = (
    'wall', 'column', 'glass', 'window', 'door', 'stair', 'stair-above', 'railing', 'room-name', 'grid', 'furniture',
    'other', 'ignore', 'screen', 'room-outline',
)

#: The detector's roles: detector/geomkit.py ROLES, in its order.
DETECTOR_ROLES: tuple[str, ...] = ('wall', 'column', 'glass', 'window', 'screen', 'door', 'stair', 'ignore')

#: Staff role -> builder role (U-8.2).
BUILDER_OF: dict[str, str] = {
    'wall': 'wall', 'column': 'column', 'glass': 'glass', 'window': 'window', 'door': 'door', 'stair': 'stair',
    'stair-above': 'stair-above', 'railing': 'railing', 'room-name': 'room-name', 'grid': 'grid',
    'furniture': 'furniture', 'other': 'other', 'ignore': 'ignore',
    'screen': 'screen', 'room-outline': 'room-outline',
    'level': 'other', 'light': 'other',
}

#: Staff role -> detector role, or None: no role, still read as context (U-8.2).
DETECTOR_OF: dict[str, str | None] = {
    'wall': 'wall', 'column': 'column', 'glass': 'glass', 'window': 'window', 'screen': 'screen', 'door': 'door',
    'stair': 'stair', 'stair-above': 'stair',
    'railing': 'ignore', 'furniture': 'ignore', 'room-name': 'ignore', 'level': 'ignore', 'grid': 'ignore',
    'light': 'ignore', 'ignore': 'ignore',
    'room-outline': None, 'other': None,
}

#: The roles a layer not listed in the settings gets (U-8.1: an unknown layer is `other`, read by the detector).
DEFAULT_ROLE = 'other'

#: The roles whose layers are walls for the Floors step's "propose again on the wall layers" and `area_empty` (U-9.1).
WALL_ROLES: frozenset[str] = frozenset({'wall', 'column'})


def check_role(role: str) -> str:
    if role not in STAFF_ROLES:
        raise ValueError(f'unknown layer role {role!r} (allowed: {", ".join(STAFF_ROLES)})')
    return role


def _group(layers: Mapping[str, str], table: Mapping[str, str | None], order: tuple[str, ...]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for name, role in layers.items():
        derived = table[check_role(role)]
        if derived is not None:
            groups.setdefault(derived, []).append(name)
    return {r: sorted(groups[r]) for r in order if r in groups}


def builder_layers(layers: Mapping[str, str]) -> dict[str, list[str]]:
    """BuildSettings.layers -> the bank builder's `layers` table {builder role: [layer, ...]} (names sorted; roles in
    ROLES order; a role with no layer left out). `level` and `light` layers come out as `other`."""
    return _group(layers, BUILDER_OF, ROLES)


def detector_layers(layers: Mapping[str, str]) -> dict[str, list[str]]:
    """BuildSettings.layers -> a detector mapping's `layers` table {detector role: [layer, ...]} (names sorted; roles in
    geomkit.ROLES order). `room-outline` and `other` layers are not listed: the detector reads them as context.
    docs/upload/reference/derived_detector_mapping_bank1.json is this table for the bank's settings."""
    return _group(layers, DETECTOR_OF, DETECTOR_ROLES)


def builder_role(layers: Mapping[str, str], name: str) -> str:
    """The builder role of one layer (exact name; a layer the settings do not list is `other`)."""
    return BUILDER_OF[check_role(layers.get(name, DEFAULT_ROLE))]


def detector_role(layers: Mapping[str, str], name: str) -> str | None:
    """The detector role of one layer (exact name), or None (read as context)."""
    return DETECTOR_OF[check_role(layers.get(name, DEFAULT_ROLE))]


def consistency(builder: Mapping[str, list[str]], detector: Mapping[str, list[str]]) -> list[str]:
    """The bank builder's self-check (build_model.py: 'the detector must have read the drawing with the same roles'):
    for wall, column, glass and door, the layer sets of the two tables must agree (case-insensitive). Returns the
    warnings, empty when they agree. Kept as a self-test of the two derived tables (U-8.2)."""
    out = []
    for role in ('wall', 'column', 'glass', 'door'):
        a = {x.upper() for x in detector.get(role, [])}
        b = {x.upper() for x in builder.get(role, [])}
        if a != b:
            out.append(f'the detector reads {role} from {sorted(a)}, the builder from {sorted(b)}')
    return out
