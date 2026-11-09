"""One 3ds Max generator for every model, with a MaxTexts profile (docs/upload/DESIGN.md U-11.5; plan 3.6, the owner's
rule of 19 Oct).

The bank's `bank_test/src/generate_maxscript.py` and the hotel's `hotel_test/src/generate_maxscript.py` merged: their
code is the same line for line after the leading comment block (hotel_test/test_hotel_maxscript.py proves it), so the
body below is that code, and the lines that differ on purpose come from a profile (`fixtures/upload/max-texts/*.json`):
the header comment block, the "Placed at ..." lines, the tooltip of the placement tick box, the datum's Source property,
extra datum lines, the rollout's title suffix, and whether one datum Picture line per floor is written from
`model.pictureFrame`. The generator reads ONLY the model bytes and the profile (plus, for the `upload` profile's
sentences, the build's date and its sources' kinds and units). Every part stays live: an editable spline (outline and
holes) + Extrude (output: Mesh) + Smooth; "Collapse" gives Editable Mesh, never Editable Poly; furniture as Box primitives
through the vendored `furniture_max.fragments` / `splice` (unchanged).

    data = maxscript(model_bytes, load_profile('upload'), date='4 Nov 2026', sources=[{'kind': 'dwg', 'units': 'mm'}],
                     converter={'name': 'libredwg', 'version': '0.14', ...})

Bytes: CRLF written explicitly; line 2 carries `(model data <sha1(model)[:12]>)` in every profile; numbers as the
generators wrote them (4 decimals, negatives in brackets); ASCII only.
Kinds: the bank's 11 kinds and its 7 materials are fixed; a kind outside them that the model uses (pane, balustrade, low,
builtin, deck, post) adds exactly one case line and one material, so the bank's bytes cannot move.
Refusals (MaxScriptRefused, nothing written): the bank's checks (an unknown kind, an invalid outline, a loop of fewer than
3 points, two points closer than 0.0001 m, a hole within 0.0005 m of its outline) and the hotel's "two holes touch" (two
holes of one outline within 0.0005 m), for every model; the furniture problems of `furniture_max.fragments`.
Names: an object name or text that `ascii_name` reduces to nothing (Thai) falls back to its id (`BB_L1_Wall_012`, a
room's `room 003`, a floor's key, the project's photo name).
Placeholders are filled in ONE pass over the template (never inside names that came from the drawing), and the template
is checked for any placeholder left before anything is filled in.
"""
from __future__ import annotations

import hashlib
import json
import math
import posixpath
import re
import unicodedata
from pathlib import Path
from typing import Any

from shapely.geometry import LinearRing, Polygon

from ..vendor.load import load as _load_vendor

#: The profiles' folder (fixtures/upload/max-texts, owned by U4; U-11.5).
PROFILES = Path(__file__).resolve().parents[4] / 'fixtures' / 'upload' / 'max-texts'
PROFILE_FIELDS = ('format', 'profile', 'date', 'titleSuffix', 'builtBy', 'page', 'frame', 'header', 'placedAt', 'notes',
                  'tooltip', 'datumSource', 'datumExtra', 'rolloutSuffix', 'pictures')
NOTE_CONDITIONS = ('always', 'revitGlass', 'pictures', 'furniture', 'steps')
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')

# kind -> (layer suffix, material); whether the top follows the wall height comes with each part ('follow').
# The bank's 11, fixed (their case lines and the 7 materials are always written) ...
KINDS = {'wall': ('Walls', 'Wall'), 'column': ('Columns', 'Wall'), 'lintel': ('Lintels', 'Wall'), 'sill': ('Sills', 'Wall'),
         'parapet': ('Parapets', 'Wall'), 'glass': ('Glass', 'Glass'), 'mullion': ('GlassFrames', 'Frame'),
         'railing': ('Railings', 'Rail'), 'single': ('SingleLines', 'Single'), 'step': ('Steps', 'Step'), 'slab': ('Slab', 'Slab')}
# ... and the BuiltModel v1 kinds outside them (D-5.4): written only when the model uses them, one case line and one
# material each (colours of D-5.4; the glass-like ones with the bank's glass settings).
EXTRA_KINDS = {
    'pane': ('Panes', 'Pane', 'diffuse:(color 170 200 214) opacity:30 specularLevel:60 glossiness:60'),
    'balustrade': ('Balustrades', 'Balustrade', 'diffuse:(color 170 200 214) opacity:30 specularLevel:60 glossiness:60'),
    'low': ('LowWalls', 'Low', 'diffuse:(color 210 198 178)'),
    'builtin': ('BuiltIns', 'Builtin', 'diffuse:(color 201 167 127)'),
    'deck': ('Decks', 'Deck', 'diffuse:(color 176 138 92)'),
    'post': ('Posts', 'Post', 'diffuse:(color 111 97 83)'),
}
PLURAL = {'wall': 'walls', 'column': 'columns', 'lintel': 'lintels', 'sill': 'sills', 'parapet': 'parapets', 'glass': 'glass',
          'mullion': 'mullions', 'railing': 'railings', 'single': 'single-line pieces', 'step': 'stair steps', 'slab': 'slabs',
          'pane': 'panes', 'balustrade': 'balustrades', 'low': 'low walls', 'builtin': 'built-ins', 'deck': 'decks',
          'post': 'posts'}
UNIT_WORDS = {'mm': 'mm', 'cm': 'cm', 'm': 'm', 'in': 'inches', 'ft': 'feet'}

PLACEHOLDER = re.compile(r'__([A-Z0-9]+(?:_[A-Z0-9]+)*)__')
LEFT_OVER = re.compile(r'__[A-Z]+(?:_[A-Z]+)*__')


class MaxScriptRefused(ValueError):
    """The model has parts Extrude cannot cap (or furniture the Max code cannot place): nothing is written."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = list(problems)
        shown = '; '.join(problems[:5]) + (f' ... and {len(problems) - 5} more' if len(problems) > 5 else '')
        super().__init__(f'the 3ds Max script refuses this model ({len(problems)} problem'
                         f'{"s" if len(problems) != 1 else ""}): {shown}')


# ------------------------------------------------------------------------------------------------ the generators' helpers
def ascii_name(s: str) -> str:
    """Max object names and text: plain ASCII, both spellings of the prototypes (the bank's and hotel's ² and ·, the
    suite's Đ / đ) and furniture_max's control characters; quotes become ', backslashes /, spaces collapse."""
    s = s.replace('²', '2').replace('·', '-').replace('Đ', 'D').replace('đ', 'd')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return ' '.join(re.sub(r'[\x00-\x1f\x7f]', ' ', s).replace('"', "'").replace('\\', '/').split())


def signed(loop): return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(loop, loop[1:] + loop[:1])) / 2
def arr(v): return '#(' + ','.join(v) + ')'
def num(v): return f'({v:.4f})' if v < 0 else f'{v:.4f}'        # negative numbers in brackets: never read as a minus
def pt(p): return f'[{num(p[0])},{num(p[1])}]'
def words(v): return ', '.join(v[:-1]) + ' and ' + v[-1] if len(v) > 1 else ''.join(v)


def date_text(when) -> str:
    """'4 Nov 2026' (the prototypes' header dates) from a date or datetime."""
    return f'{when.day} {MONTHS[when.month - 1]} {when.year}'


def load_profile(name: str = 'upload', folder: Path | None = None) -> dict:
    """A MaxTexts profile by name (fixtures/upload/max-texts/<name>.json), checked."""
    p = (folder or PROFILES) / f'{name}.json'
    prof = json.loads(p.read_text(encoding='utf-8'))
    check_profile(prof)
    return prof


def check_profile(prof: dict) -> None:
    """Raises ValueError when a profile lacks a field or has one of the wrong type."""
    bad = []
    if prof.get('format') != 'max-texts/1':
        bad.append("format must be 'max-texts/1'")
    for k in ('titleSuffix', 'builtBy', 'page', 'frame', 'tooltip', 'datumSource', 'rolloutSuffix'):
        if not isinstance(prof.get(k), str):
            bad.append(f'{k} must be a string')
    for k in ('header', 'placedAt', 'datumExtra'):
        if not isinstance(prof.get(k), list) or not all(isinstance(x, str) for x in prof[k]):
            bad.append(f'{k} must be a list of strings')
    if not isinstance(prof.get('notes'), list) or not all(
            isinstance(n, dict) and n.get('when') in NOTE_CONDITIONS and isinstance(n.get('lines'), list)
            and all(isinstance(x, str) for x in n['lines']) for n in prof['notes']):
        bad.append(f'notes must be a list of {{when: {" | ".join(NOTE_CONDITIONS)}, lines: [...]}}')
    if not isinstance(prof.get('pictures'), bool):
        bad.append('pictures must be true or false')
    if prof.get('date') is not None and not isinstance(prof.get('date'), str):
        bad.append('date must be a string or null')
    for k in prof:
        if k not in PROFILE_FIELDS and not k.startswith('_'):
            bad.append(f'{k}: not a profile field')
    for k in ('tooltip', 'datumSource', 'rolloutSuffix', 'titleSuffix', 'builtBy', 'page', 'frame', 'date'):
        v = prof.get(k)
        if isinstance(v, str) and ('"' in v or '\\' in v or '\n' in v or '\r' in v):
            bad.append(f'{k}: no quote, backslash or line break (it goes inside a MAXScript string)')
    for k in ('header', 'placedAt', 'datumExtra'):
        for line in prof.get(k) or []:
            if isinstance(line, str) and ('\n' in line or '\r' in line or any(ord(ch) > 127 for ch in line)):
                bad.append(f'{k}: one line each, plain ASCII')
    if bad:
        raise ValueError(f'MaxTexts profile {prof.get("profile")!r}: ' + '; '.join(bad))


# ---------------------------------------------------------------------------------------------------------- the template
# The bank's and hotel's template after their header comment block, with the places where they differ (and the extra
# kinds) as placeholders. Block placeholders (a line of their own) vanish with their line when they have nothing to say.
BODY_HEAD = r'''global __PX___UI
global __PX___nodes = #()
global __PX___failed = #()
global __PX___levels = __LEVELS__
global __PX___heights = __HEIGHTS__
global __PX___floorNames = __NAMES__
global __PX___collapse = false
global __PX___shift = [0.0, 0.0]
global __PX___mats
__FURN_GLOBALS__

fn __PX___layer n =
(
    local ly = LayerManager.getLayerFromName n
    if ly == undefined do ly = LayerManager.newLayerFromName n
    ly
)
fn __PX___mat key =
(
    local m = undefined
    for x in __PX___mats where x.name == ("__PX__ " + key) do m = x
    m
)
fn __PX___makeMaterials =
(
    __PX___mats = #()
    append __PX___mats (standardMaterial name:"__PX__ Wall" diffuse:(color 227 221 211))
    append __PX___mats (standardMaterial name:"__PX__ Glass" diffuse:(color 170 200 214) opacity:30 specularLevel:60 glossiness:60)
    append __PX___mats (standardMaterial name:"__PX__ Rail" diffuse:(color 119 114 124))
    append __PX___mats (standardMaterial name:"__PX__ Single" diffuse:(color 224 164 88))
    append __PX___mats (standardMaterial name:"__PX__ Slab" diffuse:(color 212 216 210))
    append __PX___mats (standardMaterial name:"__PX__ Frame" diffuse:(color 93 107 116))
    append __PX___mats (standardMaterial name:"__PX__ Step" diffuse:(color 185 199 180))
__EXTRAMATS__
)
fn __PX___num v = ((v as string) as float)
-- The outline's knots are relative to c, the middle of the outline; the node is then moved to c, so that is its pivot.
fn __PX___shape nm loops =
(
    local o = splineShape name:nm
    for j = 1 to loops.count do
    (
        addNewSpline o
        for p in loops[j] do addKnot o j #corner #line [p.x, p.y, 0]
        close o j
    )
    updateShape o
    o
)
fn __PX___extrudeOf o =
(
    local ex = undefined
    for md in o.modifiers where classOf md == Extrude do ex = md
    ex
)
-- kind: #wall #column #lintel #sill #parapet #glass #mullion #railing #single #step #slab; z0/z1 in metres above the
-- level of floor fi (a step of a flight going down from a level starts below it);
-- follow = the top follows that level's wall height. c = pivot, mn/mx = outline extents (DWG coordinates).
fn __PX___part kind nm loops z0 z1 follow fi c mn mx =
(
    local info = case kind of
    (
        #wall: #("Walls", "Wall")
        #column: #("Columns", "Wall")
        #lintel: #("Lintels", "Wall")
        #sill: #("Sills", "Wall")
        #parapet: #("Parapets", "Wall")
        #glass: #("Glass", "Glass")
        #mullion: #("GlassFrames", "Frame")
        #railing: #("Railings", "Rail")
        #single: #("SingleLines", "Single")
        #step: #("Steps", "Step")
        #slab: #("Slab", "Slab")
__EXTRACASES__
    )
    local lvl = __PX___levels[fi]
    local top = if follow then __PX___heights[fi] else z1
    local zb = lvl + z0
    local ht = top - z0
    local o = __PX___shape nm loops
    o.pos = [c.x - __PX___shift.x, c.y - __PX___shift.y, zb]
    addModifier o (Extrude amount:ht segs:1 capStart:true capEnd:true output:1 smooth:false)
    addModifier o (Smooth autoSmooth:true threshold:25.0)
    local mt = __PX___mat info[2]
    o.material = mt
    o.wirecolor = mt.diffuse
    setUserProp o "__PX___kind" (kind as string)
    setUserProp o "__PX___floor" fi
    setUserProp o "__PX___base" z0
    setUserProp o "__PX___follow" follow
    -- the checks run on the evaluated mesh (what the modifiers produce)
    local m = snapshotAsMesh o
    local why = ""
    local tol = 0.002
    if m.numfaces < 3 then why = "no faces"
    else if (meshop.getOpenEdges m).numberSet != 0 then why = "open edges (not a closed solid)"
    else if abs(o.min.z - zb) > tol or abs(o.max.z - (zb + ht)) > tol then why = "height"
    else if abs(o.min.x - (mn.x - __PX___shift.x)) > tol or abs(o.min.y - (mn.y - __PX___shift.y)) > tol or abs(o.max.x - (mx.x - __PX___shift.x)) > tol or abs(o.max.y - (mx.y - __PX___shift.y)) > tol then why = "position"
    m = undefined
    if why == "" then
    (
        (__PX___layer ("__PX___" + __PX___floorNames[fi] + "_" + info[1])).addNode o
        setUserProp o "__PX___check" "ok"
    )
    else
    (
        (__PX___layer "__PX___Check_Failed").addNode o
        setUserProp o "__PX___check" why
        append __PX___failed (nm + ": " + why)
    )
    if __PX___collapse do convertToMesh o
    append __PX___nodes o
    o
)
-- Stair lines: one shape of open two-knot splines per level and kind, knots relative to c (its pivot).
fn __PX___lines nm segs fi c lay =
(
    local o = splineShape name:nm
    for k = 1 to segs.count do
    (
        addNewSpline o
        addKnot o k #corner #line [segs[k][1].x, segs[k][1].y, 0]
        addKnot o k #corner #line [segs[k][2].x, segs[k][2].y, 0]
    )
    updateShape o
    o.pos = [c.x - __PX___shift.x, c.y - __PX___shift.y, __PX___levels[fi]]
    o.wirecolor = if lay == "Stairs" then (color 46 139 71) else (color 160 210 170)
    setUserProp o "__PX___floor" fi
    setUserProp o "__PX___base" 0.0
    (__PX___layer ("__PX___" + __PX___floorNames[fi] + "_" + lay)).addNode o
    append __PX___nodes o
    o
)
fn __PX___room nm p fi =
(
    local t = text text:nm size:0.3 pos:[p.x - __PX___shift.x, p.y - __PX___shift.y, __PX___levels[fi] + 0.02]
    t.name = "__PX___Room_" + __PX___floorNames[fi] + "_" + nm
    t.wirecolor = color 30 60 110
    setUserProp t "__PX___floor" fi
    setUserProp t "__PX___base" 0.02
    (__PX___layer ("__PX___" + __PX___floorNames[fi] + "_RoomNames")).addNode t
    append __PX___nodes t
    t
)
-- After the build: move every part to its level and set every live part whose top follows the wall height to its
-- level's new wall height.
fn __PX___updateLevels newLevels newHeights =
(
    local n = 0
    local skipped = 0
    for o in objects where (getUserProp o "__PX___floor") != undefined do
    (
        local fi = (__PX___num (getUserProp o "__PX___floor")) as integer
        local base = __PX___num (getUserProp o "__PX___base")
        o.pos.z = newLevels[fi] + base
        if ((getUserProp o "__PX___follow") as string) == "true" do
        (
            local ex = __PX___extrudeOf o
            if ex == undefined then skipped += 1
            else ( ex.amount = newHeights[fi] - base; n += 1 )
        )
    )
    __PX___levels = newLevels
    __PX___heights = newHeights
    #(n, skipped)
)
fn __PX___collapseAll =
(
    local n = 0
    for o in objects where (getUserProp o "__PX___kind") != undefined and o.modifiers.count > 0 do ( convertToMesh o; n += 1 )
    n
)
__FURN_FUNCTIONS__
fn __PX___build =
(
__FURN_ADDONLY__
    if objects.count > 0 then
    (
        messageBox "Open a NEW EMPTY scene first. Nothing in this scene has been changed." title:"__SHORT__"
        return false
    )
    units.systemType = #meters
    units.systemScale = 1.0
    units.displayType = #metric
    units.metricType = #meters
    __PX___nodes = #()
    __PX___failed = #()
    __PX___makeMaterials()
    local t0 = timeStamp()
'''

FOOTER = r'''
__FURN_BUILD__
    local origin = point name:"__PX___ORIGIN_DWG" size:1.0 pos:[0.0 - __PX___shift.x, 0.0 - __PX___shift.y, 0.0]
    origin.isHidden = true
    origin.ignoreExtents = true
    (__PX___layer "__PX___Datums").addNode origin
    setUserProp origin "Source" "<<DATUMSOURCE>>"
    setUserProp origin "Levels" ("floor levels " + (__PX___levels as string) + " m, wall heights " + (__PX___heights as string) + " m")
<<DATUMEXTRA>>
__PICTURES__
    viewport.setType #view_iso_user
    select __PX___nodes
    max zoomext sel all
    clearSelection()
    redrawViews()
    format "__PX__ BUILD COMPLETE: % objects in % s, % failed checks\n" __PX___nodes.count ((timeStamp() - t0) / 1000.0) __PX___failed.count
    for f in __PX___failed do format "  check failed: %\n" f
    true
)
try (destroyDialog __PX___UI) catch ()
rollout __PX___UI "__SHORT__<<ROLLOUTSUFFIX>>" width:340
(
    label info "Open a new empty scene before Build." align:#left
    label units1 "Build sets System Units to metres." align:#left
    checkbox dwg "At the drawing's own coordinates" checked:true tooltip:"<<TOOLTIP>>"
__SPINNERS__
__FURN_UI__
    checkbox cm "Collapse to Editable Mesh (no live modifiers)" checked:false
    button build "BUILD THE MODEL" width:310 height:32
    label note1 "Parts stay live: spline + Extrude (mesh) + Smooth." align:#left
    group "After the build"
    (
        button upd "Update levels and heights" width:300
        button col "Collapse all now (Editable Mesh)" width:300
__FURN_UI_AFTER__
    )
    on build pressed do
    (
        __PX___levels = __READLEVELS__
        __PX___heights = __READHEIGHTS__
        __PX___collapse = cm.checked
        __PX___shift = if dwg.checked then [0.0, 0.0] else [__OX__, __OY__]
__FURN_READ__
        try
        (
            if __PX___build() do
            (
                if __PX___failed.count == 0 then messageBox ("Built " + (__PX___nodes.count as string) + " objects. Every part passed the closed-solid, height and position checks. Save As to keep your .max file.") title:"__SHORT__"
                else messageBox ((__PX___failed.count as string) + " part(s) failed a check and are on layer __PX___Check_Failed (listed in the MAXScript Listener). Everything else was built.") title:"__SHORT__"
            )
        )
        catch (messageBox (getCurrentException()) title:"Build stopped")
    )
    on upd pressed do
    (
        local r = __PX___updateLevels __READLEVELS__ __READHEIGHTS__
        messageBox ("Every part moved to its level; " + (r[1] as string) + " parts set to their level's wall height." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were collapsed already and kept their height.") else "")) title:"__SHORT__"
    )
    on col pressed do
    (
        local n = __PX___collapseAll()
        messageBox ((n as string) + " parts collapsed to Editable Mesh.") title:"__SHORT__"
    )
__FURN_HANDLERS__
)
createDialog __PX___UI
'''

#: placeholders that are lines of their own and vanish with their line when they have nothing to say
BLOCKS = ('EXTRAMATS', 'EXTRACASES', 'PICTURES')


# ----------------------------------------------------------------------------------------------------- what is computed
def _check_parts(M: dict, PX: str, FI: dict, ox: float, oy: float) -> tuple[list[str], list[str], dict, list[str]]:
    """The part calls, the problems (the bank's checks and the hotel's two holes), the count per (floor, kind) and the
    extra kinds used, in the bank generator's order."""
    problems, calls, count = [], [], {}
    plinth_level = {f['key']: f['level'] for f in M['floors']}
    for part in M['parts']:
        kind, fl = part['kind'], part['floor']
        if kind not in KINDS and kind not in EXTRA_KINDS:
            problems.append(f'unknown kind {kind}')
            continue
        if fl not in FI:
            problems.append(f'unknown floor {fl}')
            continue
        key = (fl, kind)
        count[key] = count.get(key, 0) + 1
        label = ascii_name(part['label']) if part.get('label') else ''
        name = f"{PX}_{fl}_{kind.capitalize()}_{count[key]:03}" + (f'_{label}' if label else '')
        outer = [(x + ox, y + oy) for x, y in part['o']]
        holes = [[(x + ox, y + oy) for x, y in h] for h in part['h']]
        if any(len(loop) < 3 for loop in [outer] + holes):       # (the prototypes crashed in shapely here)
            problems.append(f'{name}: loop with fewer than 3 points')
            continue
        if not Polygon(outer, holes).is_valid:
            problems.append(f'{name}: invalid polygon')
        for loop in [outer] + holes:
            for a, b in zip(loop, loop[1:] + loop[:1]):
                if math.dist(a, b) < 1e-4:
                    problems.append(f'{name}: repeated point')
        for h in holes:                    # Extrude cannot cap a hole that touches the outline
            if LinearRing(h).distance(LinearRing(outer)) < 5e-4:
                problems.append(f'{name}: a hole touches the outline')
        for i in range(len(holes)):        # ... nor two holes that touch each other (the hotel's check, every model)
            for j in range(i + 1, len(holes)):
                if LinearRing(holes[i]).distance(LinearRing(holes[j])) < 5e-4:
                    problems.append(f'{name}: two holes touch')
        mn = (min(x for x, _ in outer), min(y for _, y in outer))
        mx = (max(x for x, _ in outer), max(y for _, y in outer))
        c = ((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2)             # the object's pivot: the middle of its outline
        loops = []
        for j, loop in enumerate([outer] + holes):     # outer counter-clockwise, holes clockwise; relative to c
            if (signed(loop) > 0) != (j == 0):
                loop = loop[::-1]
            loops.append(arr([pt((x - c[0], y - c[1])) for x, y in loop]))
        follow = 'true' if part.get('follow') else 'false'
        z0 = part['z0']
        if part.get('plinth') and kind == 'slab':      # a plinth slab stands on the ground (D-5.5): from z0 = -level
            z0 = -plinth_level[fl]
        calls.append(f'    {PX}_part #{kind} "{name}" {arr(loops)} {num(z0)} {num(part["z1"])} {follow} {FI[fl]} {pt(c)} '
                     f'{pt(mn)} {pt(mx)}')
    used = [k for k in EXTRA_KINDS if any(k == kk for _, kk in count)]
    return calls, problems, count, used


def _stair_lines(M: dict, PX: str, FI: dict, ox: float, oy: float) -> list[str]:
    lines = []
    for fl, st in (M.get('stairs') or {}).items():
        if fl not in FI:
            continue
        for part_name, a in (('Stairs', st.get('below') or []), ('StairsAbove', st.get('above') or [])):
            if not a:
                continue
            segs = [((a[i] + ox, a[i + 1] + oy), (a[i + 2] + ox, a[i + 3] + oy)) for i in range(0, len(a), 4)]
            xs = [p[0] for s in segs for p in s]
            ys = [p[1] for s in segs for p in s]
            c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
            sp = arr([arr([pt((p[0] - c[0], p[1] - c[1])) for p in s]) for s in segs])
            lines.append(f'    {PX}_lines "{PX}_{fl}_{part_name}" {sp} {FI[fl]} {pt(c)} "{part_name}"')
    return lines


def _rooms(M: dict, PX: str, FI: dict, ox: float, oy: float) -> list[str]:
    out, n = [], {}
    for r in M['rooms']:
        if r['floor'] not in FI:
            continue
        n[r['floor']] = n.get(r['floor'], 0) + 1
        text = ascii_name(r.get('label') or r.get('name') or '') or f"room {n[r['floor']]:03}"   # Thai: falls back to its id
        out.append(f'    {PX}_room "{text}" {pt((r["x"] + ox, r["y"] + oy))} {FI[r["floor"]]}')
    return out


def _follow_keep(M: dict) -> tuple[str, str]:
    """What "Update levels and heights" does to this model's parts (the hotel's sentence, every profile)."""
    kinds_seen = list(dict.fromkeys(p['kind'] for p in M['parts'] if p['kind'] in KINDS or p['kind'] in EXTRA_KINDS))
    follows = {k: {bool(p.get('follow')) for p in M['parts'] if p['kind'] == k} for k in kinds_seen}
    follow_txt = words([PLURAL[k] + (' (those marked to)' if len(follows[k]) > 1 else '') for k in kinds_seen
                        if True in follows[k]]) or 'no part'
    keep_txt = words(['the ' + PLURAL[k] for k in kinds_seen if follows[k] == {False}]) or 'nothing else'
    return follow_txt, keep_txt


def _scale_texts(M: dict, FLOORS: list[dict]) -> dict[str, str]:
    """The hotel's stair, axis, door and scale sentences, computed for every model."""
    flight = [p for p in M['parts'] if p['kind'] == 'step' and p['floor'] == FLOORS[0]['key']]
    stair_w = max(max(max(x for x, _ in p['o']) - min(x for x, _ in p['o']), max(y for _, y in p['o']) - min(y for _, y in p['o']))
                  for p in flight) if flight else None
    frames = M.get('pictureFrame') or {}
    per_axis = [ascii_name(f['name']) or f['key'] for f in FLOORS if frames.get(f['key'])
                and abs(frames[f['key']]['pxPerMetreX'] - frames[f['key']]['pxPerMetreY']) >= 0.005]
    stair_txt = (f"the main stair's width, {stair_w:.2f} m between its side walls" if stair_w else 'no dimension')
    axis_txt = (f"; {words(per_axis)}'s picture is drawn wider than tall (a scale per axis)" if per_axis else '')
    drawn = [o['drawnWidth'] for o in M['openings'] if o.get('liftDoor') and o.get('drawnWidth')]
    door_txt = (f'at that scale the {len(drawn)} lift doors measure {min(drawn):.2f} to {max(drawn):.2f} m as drawn '
                f'({sum(drawn) / len(drawn):.2f} m on average); they are built '
                f'{max(o["width"] for o in M["openings"] if o.get("liftDoor")):.2f} m'
                if drawn else 'no lift door was measured')
    scale_txt = (f"scaled from {stair_txt} (the owner's){', per axis where a picture is drawn wider than tall' if per_axis else ''}"
                 if stair_w else 'scale not measured')
    return {'STAIRTXT': stair_txt, 'AXISTXT': axis_txt, 'DOORTXT': door_txt, 'SCALETXT': scale_txt}


def _pictures(M: dict, FLOORS: list[dict]) -> list[str]:
    """One datum Picture line per floor from model.pictureFrame (the hotel's)."""
    out = []
    for f in FLOORS:
        pf = (M.get('pictureFrame') or {}).get(f['key'])
        if not pf:
            continue
        (w, h), kx, ky, (px0, py0) = pf['size'], pf['pxPerMetreX'], pf['pxPerMetreY'], pf['originPx']
        rel = posixpath.normpath(posixpath.join('src', pf['file']))           # the file as seen from the script's folder
        cx, cy = (round((w / 2 - px0) / kx, 4) + 0.0, round((py0 - h / 2) / ky, 4) + 0.0)   # a plain minus (no -0.0000)
        out.append(f'    setUserProp origin "Picture_{f["key"]}" "{ascii_name(rel)} ({w} x {h} px at {kx:.4f} px per m '
                   f'along x and {ky:.4f} along y) is a plane {w / kx:.4f} m along x by {h / ky:.4f} m along y, its centre '
                   f'[{cx:.4f}, {cy:.4f}] m from this point, under {ascii_name(f["name"]) or f["key"]}"')
    return out


def is_revit_glass(part: dict) -> bool:
    """A glass part from a Revit glass wall type (the bank builder labels them with the type name; panes, transoms and
    glass screens carry other labels)."""
    lab = part.get('label')
    return (part['kind'] == 'glass' and bool(lab) and not lab.endswith((' pane', ' transom')) and lab != 'glass screen')


def _converted(sources: list[dict] | None, converter: dict | None) -> str:
    """'converted with LibreDWG 0.14; drawing units mm' / 'DXF exported by its own program; drawing units mm'."""
    srcs = sources or []
    kinds = list(dict.fromkeys(s.get('kind') for s in srcs))
    units = list(dict.fromkeys(UNIT_WORDS.get(s.get('units'), s.get('units') or '?') for s in srcs))
    conv = (f"converted with LibreDWG {ascii_name(str((converter or {}).get('version') or ''))}".rstrip())
    if kinds == ['dxf']:
        how = 'DXF exported by its own program'
    elif 'dxf' in kinds:
        how = f'DWG {conv}, DXF as exported by its own program'
    elif kinds:
        how = conv
    else:
        how = 'drawing source not recorded'
    return how + (f'; drawing units {" / ".join(units)}' if units else '')


# ----------------------------------------------------------------------------------------------------------- the script
def maxscript(model_bytes: bytes, profile: dict, *, date: str | None = None, sources: list[dict] | None = None,
              converter: dict | None = None) -> bytes:
    """The .ms bytes (CRLF, ASCII) for `model_bytes` with a MaxTexts `profile`. `date` ('4 Nov 2026', the build's date)
    fills __DATE__ unless the profile pins its own; `sources` ([{kind, units}], the build's sources in floor order) and
    `converter` ({name, version, exeSha1}) fill the upload profile's __CONVERTED__. Raises MaxScriptRefused."""
    check_profile(profile)
    fm = _load_vendor('furniture_max')
    M = json.loads(model_bytes.decode('utf-8'))
    SHA = hashlib.sha1(model_bytes).hexdigest()[:12]
    ox, oy = M['offset']                   # the model is centred; add this back for the drawing's own coordinates
    PX = M.get('maxPrefix', 'M')
    FLOORS = M['floors']
    FI = {f['key']: i + 1 for i, f in enumerate(FLOORS)}       # MAXScript arrays count from 1

    calls, problems, count, extra = _check_parts(M, PX, FI, ox, oy)
    lines = _stair_lines(M, PX, FI, ox, oy)
    rooms = _rooms(M, PX, FI, ox, oy)
    short = ascii_name(M.get('shortName', M['project'])) or ascii_name(M.get('photoName') or '') or PX
    FURN, furn_problems = fm.fragments(M, PX, FLOORS, f'{PX}_levels', short)
    problems += furn_problems
    if problems:
        raise MaxScriptRefused(problems)

    levels = arr([f"{f['level']:.2f}" for f in FLOORS])
    heights = arr([f"{f['wallHeight']:.2f}" for f in FLOORS])
    names = arr([f'"{f["key"]}"' for f in FLOORS])
    spinners = '\n'.join(
        f'    spinner lv{i + 1} "{ascii_name(f["name"]) or f["key"]} floor level (m):" range:[-50, 500, {f["level"]:.2f}] '
        f'type:#float fieldwidth:60\n'
        f'    spinner ht{i + 1} "{ascii_name(f["name"]) or f["key"]} wall height (m):" range:[2.2, 15, {f["wallHeight"]:.2f}] '
        f'type:#float fieldwidth:60'
        for i, f in enumerate(FLOORS))
    read_levels = arr([f'lv{i + 1}.value' for i in range(len(FLOORS))])
    read_heights = arr([f'ht{i + 1}.value' for i in range(len(FLOORS))])
    source = ' + '.join(ascii_name(s) or f'drawing {i + 1}' for i, s in enumerate(M['source']))
    follow_txt, keep_txt = _follow_keep(M)
    title = (ascii_name(M['project']) or ascii_name(M.get('photoName') or '') or PX).upper()

    values = {
        'SPINNERS': spinners, 'READLEVELS': read_levels, 'READHEIGHTS': read_heights,
        'FOLLOWTXT': follow_txt, 'KEEPTXT': keep_txt, **_scale_texts(M, FLOORS),
        'LEVELTXT': ' / '.join(f"{f['level']:+.2f}" for f in FLOORS),
        'HEIGHTTXT': ' / '.join(f"{f['wallHeight']:.2f}" for f in FLOORS),
        'LEVELS': levels, 'HEIGHTS': heights, 'NAMES': names, 'SHA': SHA, 'PAGE': profile['page'],
        'FRAME': profile['frame'], 'SOURCE': source, 'PROJECT': title, 'TITLE': title + profile['titleSuffix'].upper(),
        'SHORT': short, 'OX': f'{ox:.4f}', 'OY': num(oy), 'PX': PX, 'FLOOR1': FLOORS[0]['key'],
        'BUILTBY': profile['builtBy'], 'DATE': profile.get('date') or date or '',
        'CONVERTED': _converted(sources, converter),
        'PICTURES': '\n'.join(_pictures(M, FLOORS)) if profile['pictures'] else '',
        'EXTRACASES': '\n'.join(f'        #{k}: #("{EXTRA_KINDS[k][0]}", "{EXTRA_KINDS[k][1]}")' for k in extra),
        'EXTRAMATS': '\n'.join(f'    append __PX___mats (standardMaterial name:"__PX__ {EXTRA_KINDS[k][1]}" {EXTRA_KINDS[k][2]})'
                               for k in extra),
    }
    if not values['DATE']:
        raise ValueError(f'profile {profile.get("profile")!r} needs the build\'s date (date=...)')
    # the extra materials carry the prefix placeholder: fill it in their own text (they are code, not data)
    values['EXTRAMATS'] = values['EXTRAMATS'].replace('__PX__', PX)

    when = {'always': True, 'revitGlass': any(is_revit_glass(p) for p in M['parts']),
            'pictures': bool(M.get('pictureFrame')), 'furniture': bool(M.get('furniture')),
            'steps': any(p['kind'] == 'step' for p in M['parts'])}
    head_lines = []
    for line in profile['header']:
        if line == '__PLACEDAT__':
            head_lines += profile['placedAt']
        elif line == '__NOTES__':
            head_lines += [x for n in profile['notes'] if when[n['when']] for x in n['lines']]
        else:
            head_lines.append(line)
    header = '\n'.join(head_lines) + '\n' + BODY_HEAD
    footer = (FOOTER.replace('<<DATUMSOURCE>>', profile['datumSource']).replace('<<TOOLTIP>>', profile['tooltip'])
              .replace('<<ROLLOUTSUFFIX>>', profile['rolloutSuffix']))
    footer = (footer.replace('<<DATUMEXTRA>>\n', ''.join(x + '\n' for x in profile['datumExtra'])))

    def fill(text: str) -> str:
        for b in BLOCKS:                   # a block placeholder with nothing to say goes with its line
            if f'__{b}__\n' in text and not values[b]:
                text = text.replace(f'__{b}__\n', '')
        unknown = sorted({m.group(1) for m in PLACEHOLDER.finditer(text)
                          if m.group(1) not in values and not m.group(1).startswith('FURN_')})
        if unknown:
            raise ValueError(f'MaxTexts profile {profile.get("profile")!r}: placeholder(s) left: {", ".join(unknown)}')
        return PLACEHOLDER.sub(lambda m: m.group(0) if m.group(1).startswith('FURN_') else values[m.group(1)], text)

    script = fill(header) + '\n'.join(calls + lines + rooms) + fill(footer)
    script = fm.splice(script, FURN)
    if any(ord(ch) > 127 for ch in script):
        raise ValueError('the 3ds Max script is not plain ASCII (a name escaped ascii_name)')
    if '\r' in script:
        raise ValueError('the 3ds Max script holds a carriage return')
    return script.replace('\n', '\r\n').encode('ascii')


def stamp_of(ms: bytes) -> str | None:
    """The `(model data <12 hex>)` stamp on line 2 of a script (what create_version checks)."""
    lines = ms.split(b'\r\n')
    m = re.search(rb'model data ([0-9a-f]{12})', lines[1]) if len(lines) > 1 else None
    return m.group(1).decode() if m else None


def main(argv: list[str] | None = None) -> int:
    """The generator from the command line, e.g. for a test that needs the expected bytes of a version's script:

        node tools/run-builder-py.mjs -m walkthrough_builder.out <model.json> --profile upload
            --date "4 Nov 2026" --sources dwg:mm,dwg:mm --converter-version 0.14 --out <file.ms>

    (--sources: kind:units per source in the model's order, as write_outputs passes them; the golden profiles
    `bank-27oct` and `hotel-2nov` need neither --date nor --sources.)"""
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog='python -m walkthrough_builder.out', description='The 3ds Max script of a model.')
    ap.add_argument('model', type=Path)
    ap.add_argument('--profile', default='upload')
    ap.add_argument('--date')
    ap.add_argument('--sources', default='', help='kind:units per source, comma separated (e.g. dwg:mm,dwg:mm)')
    ap.add_argument('--converter-version')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    sources = [{'kind': s.split(':')[0], 'units': s.split(':')[1] if ':' in s else None} for s in a.sources.split(',') if s]
    conv = {'name': 'libredwg', 'version': a.converter_version} if a.converter_version else None
    try:
        data = maxscript(a.model.read_bytes(), load_profile(a.profile), date=a.date, sources=sources, converter=conv)
    except (OSError, ValueError) as exc:
        print(f'maxscript: {exc}', file=sys.stderr)
        return 1
    a.out.write_bytes(data)
    print(f'maxscript: {a.out.name}: {len(data)} bytes, stamp {stamp_of(data)}')
    return 0


def summary(model: dict, ms: bytes) -> dict[str, Any]:
    """Counts of what the script builds (for logs and tests): parts by kind, stair shapes, room names, furniture boxes."""
    text = ms.decode('ascii')
    px = model.get('maxPrefix', 'M')
    return {'parts': len(re.findall(rf'^    {px}_part #', text, re.M)), 'stairShapes': len(re.findall(rf'^    {px}_lines "', text, re.M)),
            'rooms': len(re.findall(rf'^    {px}_room "', text, re.M)), 'boxes': len(re.findall(rf'^    {px}_furnBox "', text, re.M)),
            'lines': text.count('\r\n'), 'stamp': stamp_of(ms)}
