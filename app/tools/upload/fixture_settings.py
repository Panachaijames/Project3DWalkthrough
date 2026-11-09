"""The acceptance settings (BuildSettings) of the upload milestone and the bank's office memory, as data
(docs/upload/ACCEPTANCE.md 2.5, A-1, A-5; WORK_BREAKDOWN U0 step 8). Imported by make-fixtures.py and
check-derived-mapping.py; nothing here reads a drawing.

Sources of the roles: bank_test/src/bank_project.json (the bank, verbatim in the app's role names); for the house, the
suite and the tower the detector mappings that made detector/output/ (mappings_with_areas/{sukhumvit,presidential}.json,
mappings/{l29,l30}.json) for what the detector reads, and the prototypes' layer lists for the rest
(cad_test/src/build3d.py cat_of and furniture.json; presidential_test/src/build_model.py and furniture.json). Every
layer the reference caches use is listed; a role the prototypes give no layer stays `other`. Floor keys are the
prototypes' (L1/L2, ground/upper, suite, L29/L30: the detector outputs' ids carry them); levels and heights are
ACCEPTANCE A-5's. Every number is a float (the builder coerces anyway, U-10.4).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
PROJECT = APP.parent

DEFAULTS = {'doorHead': 2.1, 'windowSill': 0.9, 'windowHead': 2.1, 'railingHeight': 1.1, 'slabThickness': 0.25,
            'singleLineHeight': 1.0}
FURNITURE = {'heights': {}, 'bases': {}, 'words': {}, 'skip': [], 'minSize': 0.08, 'minDepth': None, 'looseLayers': [],
             'pieceLayer': 'insert'}
OPTIONS = {'revitWallTypes': 'auto', 'parapets': 'auto', 'objectClosures': True, 'liftShafts': True, 'plinth': 'auto',
           'outlineWalls': 'off', 'offset': 'auto'}
FIXES = {'setAside': [], 'openings': [], 'outlineEdges': []}

#: reference name (make-reference.py) -> DWG in the project folder
DWGS = {
    'bank1': 'I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg',
    'bank2': 'I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg',
    'sukhumvit': 'Test Sukhumvit Residence.dwg',
    'presidential': 'layout presidential test.dwg',
    'l29': 'L29.dwg',
    'l30': 'L30.dwg',
}


def _floor(key, name, source, area, level, wall_height, door_head=None, window_sill=None, window_head=None,
           align=None):
    return {'key': key, 'name': name, 'source': source, 'area': area, 'level': float(level),
            'wallHeight': float(wall_height), 'slabThickness': None,
            'doorHead': None if door_head is None else float(door_head),
            'windowSill': None if window_sill is None else float(window_sill),
            'windowHead': None if window_head is None else float(window_head),
            'align': align or {'method': 'auto'}}


def _source(sha1, name, kind='dwg', units='mm'):
    return {'sha1': sha1, 'name': name, 'kind': kind, 'units': units, 'unitsConfirmed': True}


def _layers(groups: dict[str, list[str]], used: list[str] | None = None) -> dict[str, str]:
    out: dict[str, str] = {}
    for role, names in groups.items():
        for n in names:
            if n in out and out[n] != role:
                raise ValueError(f'{n}: two roles')
            out[n] = role
    for n in used or []:
        out.setdefault(n, 'other')
    return dict(sorted(out.items(), key=lambda kv: kv[0]))


def _settings(project, sources, layers, floors, furniture=None, options=None, office=None):
    return {'format': 'build-settings/1', 'office': office, 'project': project, 'sources': sources, 'layers': layers,
            'floors': floors, 'defaults': dict(DEFAULTS), 'furniture': {**copy.deepcopy(FURNITURE), **(furniture or {})},
            'vocabulary': {}, 'options': {**OPTIONS, **(options or {})}, 'fixes': copy.deepcopy(FIXES)}


# ------------------------------------------------------------------------------------------------------------- bank
def bank(sha: dict[str, str]) -> dict:
    cfg = json.loads((PROJECT / 'bank_test' / 'src' / 'bank_project.json').read_text(encoding='utf-8'))
    layers = _layers(cfg['layers'])
    furn = cfg['furniture']
    return _settings(
        {'name': cfg['project'], 'shortName': cfg['shortName'], 'projectNo': cfg['projectNo'],
         'photoName': cfg['photoName'], 'maxPrefix': cfg['maxPrefix'], 'maxFileName': 'Bangkok_Bank_Sampeng.ms',
         'exportedFrom': cfg['exportedFrom']},
        [_source(sha['bank1'], DWGS['bank1']), _source(sha['bank2'], DWGS['bank2'])],
        layers,
        [_floor('L1', 'Level 1', sha['bank1'], {'kind': 'wholeFile'}, 0.0, 3.7),
         _floor('L2', 'Level 2', sha['bank2'], {'kind': 'wholeFile'}, 3.7, 3.7)],
        furniture={'words': {k: list(v) for k, v in furn['words'].items()}, 'minSize': float(furn['minSize'])})


# ------------------------------------------------------------------------------------------------------------ house
HOUSE_ROLES = {
    'wall': ['WALL', 'XR_L44 Plan$0$A-WALL', 'XR_L55 Plan$0$A-WALL', 'STRUCTURE'],
    'column': ['COL'],
    'glass': ['WALL-GL'],
    'window': ['WIN'],
    'screen': ['W_Grill', 'A_Grill'],
    'door': ['DOOR', 'D-JAMB', 'DSYM', 'XR_L44 Plan$0$A-DOOR', 'XR_L44$0$I-DOOR'],
    'stair': ['STAIR'],
    'furniture': ['XR_L44$0$I-FURN', 'XR_L44$0$Layer7', 'XR_L44$0$PIA1-FUR', 'I-FURN-FILE', 'FUR', 'FIXT'],
    'room-name': ['TEXT', 'RNAME'],
    'level': ['SPEC'],
    'grid': ['GRID-01'],
    'ignore': ['FLOOR-PATTERN', 'DIM25', 'DIM100', 'Section', 'SITE', 'drain', 'WC-DET', 'WC-DET1', 'WC-OUT', 'WC-OUTL'],
}


def house(sha: dict[str, str], used: list[str]) -> dict:
    furn = json.loads((PROJECT / 'cad_test' / 'src' / 'furniture.json').read_text(encoding='utf-8'))
    words = {k: list(v) for k, v in furn['words'].items() if not k.startswith('_')}
    src = sha['sukhumvit']
    box = lambda b: {'kind': 'box', 'bbox': b, 'pad': 0.5, 'match': 'all'}         # noqa: E731
    return _settings(
        {'name': 'Test Sukhumvit Residence', 'shortName': 'Sukhumvit house', 'projectNo': None,
         'photoName': 'Sukhumvit', 'maxPrefix': 'SK', 'maxFileName': 'Sukhumvit_House.ms', 'exportedFrom': None},
        [_source(src, DWGS['sukhumvit'])],
        _layers(HOUSE_ROLES, used),
        [_floor('ground', 'Ground floor', src, box([7.74826, 5.601038, 53.870897, 25.854851]), 0.9, 3.9, 3.0, 0.0, 3.0),
         _floor('upper', 'Upper floor', src, box([81.769533, 6.617993, 127.848522, 24.809115]), 4.8, 3.5, 2.6, 0.0,
                2.6)],
        furniture={'words': words, 'minSize': float(furn['minSize']), 'minDepth': float(furn['minDepth'])})


# ------------------------------------------------------------------------------------------------------------ suite
SUITE_ROLES = {
    'wall': ['A-1.Netcat - tuong'],
    'column': ['A.Cot 1'],
    'door': ['Xr_SDC_DD_ID-PRS-ID wall$0$DA-DOOR-WIND', 'Xr_SDC_DD_ID-PCS-ID wall$0$DA-DOOR-WIND'],
    'railing': ['KT-Lancan'],
    'furniture': ['A-2.Noi That', 'A-4. Cay', 'A-4. Cay (goccay)', 'Xr_SDC_DD_ID-PRS-Fur$0$DA-LOOSE-FURN',
                  'Xr_SDC_DD_ID-PRS-Fur$0$DA-FACILITIES', 'Xr_SDC_DD_ID-PRS-Fur$0$DA-LEVEL-LIGHT',
                  'Xr_SDC_DD_ID-PCS-Fur$0$DA-SANR-FIXT', 'Xr_SDC_DD_ID-PRS-ID wall$0$DA-SANR'],
    'room-name': ['A-Text', 'TG_Name'],
    'room-outline': ['Defpoints'],
    'ignore': ['A-2. Noi That - bo', 'A-Hatch thiet bi', 'A-HatchVatlieu', '1VinaPVC-Hatch',
               'washbasin$0$HLD - A - Hatch', 'Xr_SDC_DD_ID-PRS-ID wall$0$DA-FLOR-PATT',
               'Xr_SDC_DD_ID-PRS-ID wall$0$DA-ANNO-DIMS', 'Xr_SDC_DD_ID-ROS-Fur$0$DA-ANNO-DIMS', 'KT_BIEN DAM RED',
               'KT_BIEN PHAO GREEN', 'KT_BIEN SAN BLUE', 'A-DETL-GENF'],
}


def suite(sha: dict[str, str], used: list[str]) -> dict:
    furn = json.loads((PROJECT / 'presidential_test' / 'src' / 'furniture.json').read_text(encoding='utf-8'))
    clean = lambda d: {k: v for k, v in d.items() if not k.startswith('_')}       # noqa: E731
    src = sha['presidential']
    return _settings(
        {'name': 'Presidential suite', 'shortName': 'Presidential suite', 'projectNo': None,
         'photoName': 'Presidential', 'maxPrefix': 'PS', 'maxFileName': 'Presidential_Suite.ms', 'exportedFrom': None},
        [_source(src, DWGS['presidential'])],
        _layers(SUITE_ROLES, used),
        [_floor('suite', 'Suite (FL-01)', src,
                {'kind': 'box', 'bbox': [174.840173, -3508.518094, 209.056439, -3480.305594], 'pad': 0.0,
                 'match': 'any'}, 0.0, 3.0, door_head=2.1)],
        furniture={'heights': {k: float(v) for k, v in clean(furn['heights']).items()},
                   'bases': {k: float(v) for k, v in clean(furn['bases']).items()},
                   'words': {k: list(v) for k, v in clean(furn['words']).items()}, 'skip': list(furn['skip']),
                   'minSize': float(furn['minSize']), 'looseLayers': list(furn['looseLayers']), 'pieceLayer': 'drawn'})


# ------------------------------------------------------------------------------------------------------------ tower
TOWER_ROLES = {
    'wall': ['A-WALL', 'A-WALL-PATT'],
    'column': ['S-COLS'],
    'glass': ['A-GLAZ-CURT'],
    'door': ['A-DETL-MEDM', 'A-DOOR', 'A-DOOR-FRAM', 'A-DOOR-HDLN'],
    'stair': ['S-STRS'],
    'stair-above': ['S-STRS-MBND'],
    'furniture': ['I-FURN', 'L-PLNT', 'P-SANR-FIXT', 'Q-CASE', 'A-GENM'],     # A-GENM: the bank's office memory
    'light': ['E-LITE-EQPM'],
    'room-outline': ['A-AREA'],                                               # U-8.3's name rule
    'ignore': ['A-DETL', 'A-FLOR', 'A-FLOR-PATT', 'E-DATA'],                  # A-DETL, A-FLOR: as mappings/l29.json (U-8.2)
}


def tower(sha: dict[str, str], used: list[str]) -> dict:
    return _settings(
        {'name': 'Tower, levels 29 and 30', 'shortName': 'Tower', 'projectNo': None, 'photoName': 'Tower-L29-L30',
         'maxPrefix': 'TW', 'maxFileName': 'Tower_L29_L30.ms', 'exportedFrom': 'Revit'},
        [_source(sha['l29'], DWGS['l29']), _source(sha['l30'], DWGS['l30'])],
        _layers(TOWER_ROLES, used),
        [_floor('L29', 'Level 29', sha['l29'], {'kind': 'wholeFile'}, 0.0, 4.0),
         _floor('L30', 'Level 30', sha['l30'], {'kind': 'wholeFile'}, 4.0, 4.0, align={'method': 'origin'})])


# ------------------------------------------------------------------------------------------------------------ small
SMALL_ROLES = {
    'wall': ['A-WALL', 'A-WALL-PATT'], 'window': ['A-GLAZ'], 'door': ['A-DOOR'], 'railing': ['A-FLOR-HRAL'],
    'stair': ['S-STRS'], 'furniture': ['I-FURN'], 'room-name': ['A-AREA-IDEN'], 'grid': ['S-GRID', 'S-GRID-IDEN'],
}


def small(dxf_sha1: str) -> dict:
    return _settings(
        {'name': 'Small test drawing', 'shortName': 'Small', 'projectNo': None, 'photoName': 'Small-test',
         'maxPrefix': 'SM', 'maxFileName': 'Small_Test.ms', 'exportedFrom': None},
        [_source(dxf_sha1, 'small.dxf', kind='dxf')],
        _layers(SMALL_ROLES, ['0']),
        [_floor('L1', 'Level 1', dxf_sha1, {'kind': 'wholeFile'}, 0.0, 3.0)])


# ---------------------------------------------------------------------------------------------- office memory (U-8.4)
def office_mapping(bank_settings: dict, at: str = '2026-11-04T00:00:00Z') -> dict:
    """OfficeMapping after the bank was saved for office dwp-revit: every layer of the bank's settings (its `other`
    layers were set by hand in bank_project.json, so they are remembered too), by normalised name."""
    import sys
    sys.path.insert(0, str(APP / 'services' / 'builder'))
    from walkthrough_builder.names import normalise_layer
    layers = {}
    for name, role in sorted(bank_settings['layers'].items()):
        key = normalise_layer(name)
        entry = layers.setdefault(key, {'role': role, 'names': [], 'uses': 1, 'lastProject': 'bank-sampeng',
                                        'lastUsedAt': at, 'was': None})
        entry['names'].append(name)
    return {'format': 'office-mapping/1', 'id': 'dwp-revit', 'name': 'DWP (Revit)', 'createdAt': at, 'updatedAt': at,
            'layers': layers, 'furnitureWords': {}}
