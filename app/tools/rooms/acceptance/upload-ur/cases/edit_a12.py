"""A-12: the office mapping's roles (dwp-revit), M_Arredi set to furniture, one floor at level 0.00 with 3.00 m walls."""
import json
import re
from pathlib import Path

MAPPING = Path(r'C:/Users/DWP2/Desktop/Project walkthrough/app/fixtures/upload/mappings/dwp-revit.json')


def norm(name):
    n = name.split('$0$')[-1] if '$0$' in name else name
    return re.sub(r' +', ' ', n.upper()).strip()


def edit(s, b):
    office = json.loads(MAPPING.read_text(encoding='utf-8'))
    for layer in list(s['layers']) + [k for k in (b.get('suggestions') or {}) if k not in s['layers']]:
        hit = office['layers'].get(norm(layer))
        if hit:
            s['layers'][layer] = hit['role']
    s['office'] = s.get('office') or 'dwp-revit'
    s['layers']['M_Arredi'] = 'furniture'
    for src in s['sources']:            # the Files step's Confirm: the doors say mm (7 against 0), the header inches
        src['unitsConfirmed'] = True
    # RI (rooms milestone, R5.md D-4): a new draft now gets the new rules; these two cases rebuild the upload
    # milestone's old stamps, so the edit writes the old rules (OLD_RULES) out
    s['options'].update({'slabs': 'closed-rooms', 'ceilings': 'off', 'stairs': 'lines'})
    assert len(s['floors']) == 1, s['floors']
    s['floors'][0]['level'] = 0.0
    s['floors'][0]['wallHeight'] = 3.0
    return s
