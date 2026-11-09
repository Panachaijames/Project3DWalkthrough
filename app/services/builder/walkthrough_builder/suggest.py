"""Layer role suggestions with their evidence, no AI (docs/upload/DESIGN.md U-8.3, U-8.4; decision D).

    suggest(drawings, office) -> LayerSuggestions      drawings: the DrawingRead of every source of the build
                                                        office: its OfficeMapping, or None

One suggestion per layer name across the sources (their counts added up), the first of these that applies:
  1. office          the office memory holds this exact name (an entry's `names`);
  2. office-similar  the office memory holds its normalised name (U-8.4: upper case, xref prefix up to the last '$0$'
                     removed, spaces collapsed);
  3. name            the pattern table of U-8.3 (case-insensitive globs on the normalised name, in its order; first match
                     wins). Two rules carry a condition on the contents: `A-AREA` / `DEFPOINTS` need 3 or more closed
                     outlines (DrawingRead has no areas per outline, so: 3+ closed shapes and 17 m of line work, the
                     perimeters of three 2 m2 squares), `*LEVEL*` needs level tags on the layer. `*-IDEN` (room names)
                     leaves out GRID / AXIS identifiers, which go on to the grid patterns (S-GRID-IDEN holds the grid
                     bubbles' labels, not room names: U2.md);
  4. contents        what the layer holds (below);
  5. default         `other`: not built, still read by the detector as context.
A name hit that the contents contradict keeps the name's role and gets the contents' evidence added ("named like a
room-name layer, but its 41 texts are door or window tags D1 ... D23"): staff decide, nothing is built before the Layers
step was seen once (U-8.3). Contents, in this order (layer 0 gets none: it holds whatever blocks drew there):
  only dimensions -> ignore; level tags making up half its texts (2+) -> level; door swings with their leaves (2+) ->
  door; solid fills and wall-like line pairs (3+ each) -> wall; glass-like pairs (5+), no fills, their lines most of the
  layer's lines -> glass; 10+ inserts of families the furniture kit classifies (vendored furniture_kit.classify, by the
  family name alone) -> furniture; only texts -> room-name when most are names (two letters or more, not a tag), other
  when they are door or window tags (D1, W2) or numbers; circles with short labels -> grid.
Only the evidence that tells roles apart (dimensions, level tags, door swings, texts, grid bubbles) is quoted against a
name; fills, line pairs and furniture families only suggest a role when no name rule matched (a stair, a railing or a
cabinet pairs lines too). Evidence sentences quote layer, block and text names: untrusted, shown as text only. Owner: U2.
"""
from __future__ import annotations

import collections
import fnmatch
import re
from collections.abc import Iterable

from . import names, roles

#: U-8.1's labels, for the evidence sentences
LABELS: dict[str, str] = {
    'wall': 'walls', 'column': 'columns', 'glass': 'glass walls', 'window': 'windows', 'door': 'doors',
    'screen': 'screens', 'stair': 'stairs', 'stair-above': 'stairs above', 'railing': 'railings',
    'furniture': 'furniture', 'room-name': 'room names', 'room-outline': 'room outlines', 'level': 'levels',
    'grid': 'grid', 'light': 'lights', 'other': 'not built (kept as context)', 'ignore': 'ignore',
}

#: U-8.3's name table, in its order: (role, patterns). Conditions: see `_condition`.
NAME_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('other', ('A-DOOR-IDEN', 'A-GLAZ-IDEN', 'A-WIND-IDEN')),
    ('stair-above', ('*STRS*MBND*', '*STAIR*ABOVE*')),
    ('wall', ('A-WALL*', '*-WALL', 'WALL', '*TUONG*')),
    ('column', ('S-COLS*', 'COL', '*-COL', 'A.COT*', '*COT *')),
    ('window', ('A-GLAZ',)),
    ('glass', ('A-GLAZ-CURT*', 'A-GLAZ-CWMG*', '*-GL', '*GLASS*', '*KINH*')),
    ('window', ('A-WIND*', 'WIN', '*WINDOW*')),
    ('door', ('A-DOOR*', 'DOOR', '*-DOOR', 'D-JAMB', 'DSYM', '*DOOR-WIND*')),
    ('screen', ('*GRILL*', '*LOUV*')),
    ('stair', ('S-STRS*', '*STAIR*', '*THANG*')),
    ('railing', ('*HRAL*', '*RAIL*', '*LANCAN*', '*BALUS*')),
    ('furniture', ('I-FURN*', '*FURN*', 'FUR', 'Q-CASE*', 'Q-SPCQ*', 'P-SANR*', '*SANR*', 'FIXT', 'L-PLNT*',
                   '*NOI THAT*', '*CAY*')),
    ('room-name', ('A-AREA-IDEN', '*ROOM*NAME*', '*RNAME*', 'A-TEXT', '*-IDEN')),
    ('room-outline', ('A-AREA', 'DEFPOINTS')),
    ('grid', ('S-GRID*', '*GRID*', '*AXIS*')),
    ('level', ('*LEVEL*',)),
    ('light', ('E-LITE*', '*LIGHT*')),
    ('ignore', ('*DIM*', '*ANNO*', '*HATCH*', '*PATT*', '*TITLE*', 'VIEWPORT*')),
)

TAG_RE = re.compile(r'^[A-Z]{1,3}[-.]?\d{1,3}[A-Z]?$', re.I)       # door / window tags: D1, W2, WD-01
OUTLINES_MIN = 3
OUTLINES_LENGTH = 3 * 4 * 2 ** 0.5                                  # three 2 m2 squares' perimeters (17 m)
FURNITURE_INSERTS = 10
SHORT_LABEL = 3
WALL_MIN = 3                                                        # fills and wall-like pairs for a contents wall
GLASS_MIN = 5                                                       # glass-like pairs for a contents glass layer ...
GLASS_SHARE = 0.6                                                   # ... whose paired lines are most of its lines


class LayerFacts:
    """One layer name's counts over every source of the build."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.normalised = names.normalise_layer(name)
        self.items = 0
        self.by_type: collections.Counter = collections.Counter()
        self.solid = 0
        self.closed = 0
        self.length = 0.0
        self.door_arcs = 0
        self.door_leaf = 0
        self.texts = 0
        self.inserts = 0
        self.families: collections.Counter = collections.Counter()
        self.glass_pairs = 0
        self.wall_pairs = 0
        self.level_tags: list[str] = []
        self.grid_labels = 0
        self.listed_texts: list[str] = []
        self.in_blocks = 0

    def add(self, la: dict) -> None:
        self.items += int(la.get('items', 0))
        self.in_blocks += int(la.get('inBlocks', 0))
        self.by_type.update({k: int(v) for k, v in (la.get('byType') or {}).items()})
        self.solid += int(la.get('solidHatches', 0))
        self.closed += int(la.get('closedShapes', 0))
        self.length += float(la.get('length', 0.0))
        self.door_arcs += int(la.get('doorArcs', 0))
        self.door_leaf += int(la.get('doorArcsWithLeaf', 0))
        self.texts += int(la.get('texts', 0))
        self.inserts += int(la.get('inserts', 0))
        for fb in la.get('topBlocks') or []:
            self.families[str(fb.get('family', ''))] += int(fb.get('count', 0))
        pairs = la.get('pairs') or {}
        self.glass_pairs += int(pairs.get('glassLike', 0))
        self.wall_pairs += int(pairs.get('wallLike', 0))


def _n(n: int, word: str, plural: str | None = None) -> str:
    return f'{n} {word if n == 1 else (plural or word + "s")}'


def _like(role: str) -> str:
    """'named like a wall layer', 'named like an ignore layer'; the name rules that give `other` are the door and
    window tag layers (A-DOOR-IDEN ...)."""
    if role == 'other':
        return 'named like a door or window tag layer'
    return f'named like {"an" if role[:1] in "aeiou" else "a"} {role} layer'


def _examples(values: Iterable[str], n: int = 3) -> str:
    vals = sorted(set(values), key=lambda s: (len(s), s))
    if not vals:
        return ''
    if len(vals) <= n:
        return ', '.join(vals)
    return f'{vals[0]} ... {vals[-1]}' if n == 2 else ', '.join(vals[:n]) + ' ...'


def _furniture_kit():
    from .vendor.load import load
    return load('furniture_kit')


def _furniture_inserts(f: LayerFacts) -> tuple[int, list[str]]:
    """Inserts (among the layer's top families) whose family the furniture kit puts in a kind, and those families."""
    try:
        kit = _furniture_kit()
    except Exception:
        return 0, []
    n, fams = 0, []
    for fam, count in f.families.most_common():
        try:
            kind = kit.classify(fam, '')
        except Exception:
            kind = None
        if kind not in (None, 'other'):
            n += count
            fams.append(f'{fam} ({count})')
    return n, fams


def _name_like(text: str) -> bool:
    """A text that can name a room: two letters or more (any script) and not a door or window tag."""
    return sum(1 for ch in text if ch.isalpha()) >= 2 and not TAG_RE.match(text)


def contents(f: LayerFacts) -> tuple[str, str, bool] | None:
    """(role, evidence, strong) from what the layer holds, or None. `strong`: the evidence tells roles apart well
    enough to be quoted against a name (dimensions, level tags, door swings, texts, grid bubbles); fills, line pairs and
    furniture families only suggest a role when the name says nothing. Layer 0 gets no contents role: it holds whatever
    blocks drew there (the house's whole upper floor is an xref on it)."""
    if f.name == '0':
        return None
    types = {t for t, n in f.by_type.items() if n}
    lines = f.by_type.get('LINE', 0)
    if types == {'DIMENSION'}:
        return 'ignore', f'it holds only dimensions ({f.by_type["DIMENSION"]})', True
    if len(f.level_tags) >= 2 and len(f.level_tags) * 2 >= max(1, f.texts):
        return 'level', (f'{_n(len(f.level_tags), "level tag")} among its {_n(f.texts, "text")}, such as '
                         f'{_examples(f.level_tags)}'), True
    if f.door_leaf >= 2:
        return 'door', f'{_n(f.door_leaf, "door swing")} with {"its" if f.door_leaf == 1 else "their"} leaves', True
    if f.solid >= WALL_MIN and f.wall_pairs >= WALL_MIN:
        return 'wall', (f'{_n(f.solid, "solid fill")} and {_n(f.wall_pairs, "wall-like line pair")} '
                        f'(7 - 45 cm apart)'), False
    if (f.glass_pairs >= GLASS_MIN and f.solid == 0 and f.glass_pairs > f.wall_pairs
            and 2 * f.glass_pairs >= GLASS_SHARE * max(1, lines)):
        return 'glass', (f'{_n(f.glass_pairs, "glass-like line pair")} (0.5 - 7 cm apart) among its '
                         f'{_n(lines, "line")}, and no fills'), False
    n_furn, fams = _furniture_inserts(f)
    if n_furn >= FURNITURE_INSERTS:
        return 'furniture', f'{_n(n_furn, "insert")} of furniture families such as {", ".join(fams[:3])}', False
    if types and types <= {'TEXT', 'MTEXT', 'ATTRIB'}:
        listed = f.listed_texts
        named = [t for t in listed if _name_like(t)]
        tags = [t for t in listed if TAG_RE.match(t)]
        if listed and len(named) * 2 > len(listed):
            return 'room-name', f'only texts ({f.texts}), such as {_examples(named)}', True
        if tags and len(tags) * 2 >= len(listed):
            return 'other', f'its {_n(f.texts, "text")} are door or window tags {_examples(tags, 2)}', True
        return 'other', f'only texts ({f.texts}) that are numbers, tags or blank, not names', True
    if f.by_type.get('CIRCLE', 0) >= 2:
        short = [t for t in f.listed_texts if len(t) <= SHORT_LABEL]
        if f.grid_labels >= 2 or (len(short) >= 2 and len(short) * 5 >= 3 * max(1, len(f.listed_texts))):
            return 'grid', (f'{_n(f.by_type["CIRCLE"], "circle")} with short labels such as '
                            f'{_examples(short or ["-"])}'), True
    return None


#: contents that a name of these roles explains, so no contradiction is quoted
_EXPLAINED = {'door': {'door', 'window', 'furniture', 'stair', 'stair-above', 'screen', 'railing'}}


def _condition(role: str, pattern: str, f: LayerFacts) -> bool:
    if pattern == '*-IDEN' and ('GRID' in f.normalised or 'AXIS' in f.normalised):
        return False
    if role == 'room-outline':
        return f.closed >= OUTLINES_MIN and f.length >= OUTLINES_LENGTH
    if role == 'level':
        return bool(f.level_tags)
    if role == 'ignore' and pattern == '*PATT*':
        return f.normalised != 'A-WALL-PATT'
    return True


def by_name(f: LayerFacts) -> tuple[str, str] | None:
    """(role, evidence) from U-8.3's pattern table, or None."""
    for role, patterns in NAME_RULES:
        for p in patterns:
            if fnmatch.fnmatchcase(f.normalised, p) and _condition(role, p, f):
                why = f'{_like(role)} ({p})'
                if role == 'room-outline':
                    why += f', with {_n(f.closed, "closed outline")}'
                elif role == 'level':
                    why += f', with {_n(len(f.level_tags), "level tag")}'
                return role, why
    return None


def _office_index(office: dict | None) -> tuple[dict[str, dict], dict[str, dict]]:
    """exact name -> entry, normalised name -> entry (roles checked)."""
    exact, norm = {}, {}
    if not office:
        return exact, norm
    for key, entry in (office.get('layers') or {}).items():
        if not isinstance(entry, dict) or entry.get('role') not in roles.STAFF_ROLES:
            continue
        norm[names.normalise_layer(str(key))] = entry
        for n in entry.get('names') or []:
            exact.setdefault(str(n), entry)
    return exact, norm


def _office_why(office: dict, entry: dict, similar: bool, name: str) -> str:
    who = office.get('name') or office.get('id') or 'this office'
    uses = int(entry.get('uses', 0) or 0)
    last = entry.get('lastProject')
    tail = f' (used {_n(uses, "time")}' + (f', last in {last}' if last else '') + ')'
    if similar:
        seen = ', '.join(str(n) for n in (entry.get('names') or [])[:3]) or name
        return f'remembered for {who} as {entry["role"]} under a similar name: {seen}{tail}'
    return f'remembered for {who} as {entry["role"]}{tail}'


def facts_of(drawings: list[dict]) -> dict[str, LayerFacts]:
    """Every layer name of the drawings with its counts added up over them."""
    out: dict[str, LayerFacts] = {}
    for dr in drawings:
        for la in dr.get('layers') or []:
            f = out.get(la['name'])
            if f is None:
                f = out[la['name']] = LayerFacts(la['name'])
            f.add(la)
        for t in dr.get('levelTags') or []:
            if t.get('layer') in out:
                out[t['layer']].level_tags.append(str(t.get('text', '')))
        for g in dr.get('gridLabels') or []:
            if g.get('layer') in out:
                out[g['layer']].grid_labels += 1
        for t in dr.get('texts') or []:
            if t.get('layer') in out:
                out[t['layer']].listed_texts.append(str(t.get('text', '')).strip())
    return out


def layer0_evidence(f: LayerFacts) -> str:
    """What layer 0 holds, in one sentence (it never gets a role by its contents). UR, V1-5: 'layer 0 holds whatever
    blocks drew there' was said of every drawing, but the 3D team's Revit export of 9 Nov draws its partitions at the
    top level on layer 0 (2,634 items, none in blocks: 99 solid fills, 84 wall-like pairs), and the house's 5,101 layer-0
    items are top-level line work too; there the sentence names what is drawn and asks staff to look."""
    tail = 'not built, but still read when finding doors and windows'
    if not f.items:
        return f'layer 0 holds nothing: {tail}'
    top = f.items - f.in_blocks
    if top * 2 <= f.items:
        return (f'layer 0 holds what blocks drew there ({f.in_blocks} of its {_n(f.items, "item")} are inside blocks): '
                f'{tail}')
    found = [s for n, s in ((f.solid, _n(f.solid, 'solid fill')),
                            (f.wall_pairs, _n(f.wall_pairs, 'wall-like line pair')),
                            (f.glass_pairs, _n(f.glass_pairs, 'glass-like line pair')),
                            (f.door_leaf, _n(f.door_leaf, 'door swing')),
                            (f.texts, _n(f.texts, 'text')),
                            (f.inserts, _n(f.inserts, 'insert'))) if n]
    if not found:
        found = [f'{_n(n, t.lower())}' for t, n in f.by_type.most_common(3) if n]
    return (f'layer 0 holds {_n(top, "item")} drawn at the top level, not inside blocks ({", ".join(found)}): check '
            f'whether walls or other parts are drawn here, since layer 0 is never given a role by what it holds; '
            f'{tail}')


def suggest_one(f: LayerFacts, office: dict | None, exact: dict, norm: dict) -> dict:
    found = contents(f)
    if f.name in exact:
        e = exact[f.name]
        return {'role': e['role'], 'from': 'office', 'evidence': [_office_why(office or {}, e, False, f.name)]}
    if f.normalised in norm:
        e = norm[f.normalised]
        return {'role': e['role'], 'from': 'office-similar', 'evidence': [_office_why(office or {}, e, True, f.name)]}
    named = by_name(f)
    if named is not None:
        role, why = named
        evidence = [why]
        if found is not None and found[0] == role:
            evidence.append(f'its contents agree: {found[1]}')
        elif found is not None and found[2] and role not in _EXPLAINED.get(found[0], ()):
            evidence.append(f'{_like(role)}, but {found[1]}')
        return {'role': role, 'from': 'name', 'evidence': evidence}
    if found is not None:
        return {'role': found[0], 'from': 'contents', 'evidence': [found[1]]}
    if f.name == '0':
        return {'role': roles.DEFAULT_ROLE, 'from': 'default', 'evidence': [layer0_evidence(f)]}
    what = (f'{_n(f.items, "item")}, nothing that names a role' if f.items else 'no items in the drawing')
    return {'role': roles.DEFAULT_ROLE, 'from': 'default',
            'evidence': [f'no rule matched ({what}): not built, but still read when finding doors and windows']}


def suggest(drawings: list[dict], office: dict | None) -> dict:
    """-> LayerSuggestions (upload-contracts.ts section 4): one per layer name across the drawings, sorted by name."""
    exact, norm = _office_index(office)
    facts = facts_of(drawings)
    layers = {name: suggest_one(facts[name], office, exact, norm) for name in sorted(facts)}
    return {'format': 'layer-suggestions/1', 'office': (office or {}).get('id') if office else None, 'layers': layers}
