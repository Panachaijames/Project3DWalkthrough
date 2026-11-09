"""3ds Max side of the furniture proxy boxes (the contract is furniture/README.md).

Returns the text fragments that the two Max script generators (bank_test/src/generate_maxscript.py and
presidential_test/src/generate_maxscript.py) splice into their templates, so that Build also makes one coloured box per
furniture piece. Owner's rules (28 Oct 2026): one box per piece, colour = kind, boxes stand at their kind's height and every
kind has a text box for that height in mm. The scripts' own rules stay: no Editable Poly, every object live, nothing in an
existing scene is changed, System Units metres, DWG coordinates or centred on the origin.

    frags, problems = furniture_max.fragments(M, px, floors, levels_expr, title)
    script = furniture_max.splice(script, frags)

    M            the model: needs 'offset' (metres, added back so the boxes sit at the DWG's coordinates like the parts),
                 'furnitureKinds' and 'furniture' (README). No 'furniture' -> every fragment is '' and the script is the
                 script it was before.
    px           the script's prefix for globals, layers and user properties ('BB' bank, 'PS' suite)
    floors       [{'key': 'L1'}, ...] in the order of the script's floor index (the bank's FLOORS; the suite has one level)
    levels_expr  MAXScript for the array of floor levels in metres at the moment Build runs: 'BB_levels' / '#(PS_level)'
    title        the title of the message boxes (the generator's short name)
    frags        {name: text} for the placeholders below, plus 'calls' (the per-piece call lines; they are already part of
                 'functions') and 'summary' (a line to print). Every text is whole lines with no final newline.
    problems     list of str: invalid data (unknown kind or floor, a support that stands on something, bad ids, ...). The
                 generator prints them and stops, as it does for parts.

What one build does for a piece (README: x, y = centre, w >= d along its own long / short axis, rot = degrees counter-clockwise
from +x to the long axis, `on` = the support's id):
  * a Max Box, parametric (width = w, length = d, height = its kind's height), placed with an explicit matrix
        matrix3 [cos,sin,0] [-sin,cos,0] [0,0,1] [X,Y,Z]   X = x + offset.x - shift.x, Y = y + offset.y - shift.y, Z = level + z0
    (rows = the box's X, Y, Z axes in the world, then the pivot: a Max Box has its pivot in the middle of its base).
    z0 = the kind's base, or the top of the kind of support the piece stands on (that kind's base + current height).
  * layer <px>_<floor>_Furn_<Kind> (CamelCase of the key), standardMaterial '<px> Furn <key>' with the kind's colour (also the
    wire colour), name <px>_<floor>_Furn_<kind key>_<nnn>_<family, ASCII, at most 40 characters> (nnn = the id's number).
  * user properties: <px>_furn = true, _furnKind, _furnId, _furnOn (support id, none for no support), _furnOnKind (the support's
    kind, so "Apply furniture heights" needs no search; none for no support), _family, _block, _layer (the DWG layer), _handle,
    _floor (floor index) and _base (z0, metres) exactly as the parts carry them, _follow = false, _check = ok or the reason it
    failed. A value that is absent (no support, the block of a loose cluster, no handle) is the word none, never an empty string:
    Autodesk does not say what getUserProp returns for empty text. "Apply furniture heights" reads none, undefined and "" alike.
  * checked as the parts are: base z, top z, the world bounding box and the four corners carried to the world by the transform,
    against corners worked out here from the model. The bounding box (node min / max) is compared for an unrotated box only (sin
    of its rotation below 0.00001 and cos positive): the node's extents are then certainly the object's. For a turned node, a
    quarter turn included, Autodesk does not say what min / max return (the world box of the turned node or the extents of the
    unturned object), and a box built right must not go on <px>_Check_Failed for that. Base z, top z and the corners are compared
    for every box: the corners prove position, size and rotation through the transform. What that leaves unmeasured for a turned
    box is whether the node's own extents in the plan agree with its transform and size; the unrotated boxes, made by the same
    code, are the only ones that show it. A box that fails goes on <px>_Check_Failed and is listed with the failed parts (Listener
    and final message); the rest is still built.
In the window: a tick box 'Build furniture boxes' (on), 'Furniture boxes only' (off), one spinner per kind that occurs, two to a
row, in whole millimetres from 10 to 5000 (a half rounds up, as in the viewer and the CSV: 740.5 -> 741; default = the model's
height), captioned with the kind's label ('Chair / stool:') or, when the label is longer than CAPTION_MAX characters, with its
key in words ('Coffee table:'), and 'Apply furniture heights' after the build. 'Furniture boxes only' says what it did in a
message of its own: the Build button then has nothing to add, so Build returns false in that mode.
'Update levels and heights' needs no change: boxes carry <px>_floor / <px>_base, so it moves them with their level, and
<px>_follow = false keeps it away from their height. Collapse (the tick box and 'Collapse all now') leaves boxes alone: it only
takes objects that carry <px>_kind and a modifier; a box has neither, and nothing here collapses, converts or adds modifiers.

Integration recipe. Each Max template gets eight placeholder lines of its own, written at column 0 (a fragment brings its own
indentation). splice() replaces each line with its fragment, takes the line out when there is no furniture (so such a model builds
byte for byte the script it built before) and raises if a line is missing or twice there. Bank names are shown; the presidential
template has the same eight places with PS_.

    __FURN_GLOBALS__    right after   global __PX___mats
    __FURN_FUNCTIONS__  right before  fn __PX___build =
    __FURN_ADDONLY__    right after that function's opening paren (before the empty-scene check)
    __FURN_BUILD__      footer: right before  local origin = point name:"__PX___ORIGIN_DWG" ...   (after the part calls)
    __FURN_UI__         rollout: right after the  __SPINNERS__  line (bank) / the  spinner ht  line (suite)
    __FURN_UI_AFTER__   rollout, group "After the build": right after the  button col  line
    __FURN_READ__       on build pressed do: right after the  __PX___shift = if dwg.checked ...  line
    __FURN_HANDLERS__   rollout: right before its closing paren (the line before  createDialog )

    In the generator's Python (the suite's names in brackets):
        after   HERE = Path(__file__).resolve().parent
                    sys.path.insert(0, str(HERE.parent.parent / 'furniture')); import furniture_max
        before  levels = arr(...)    [after the  rooms = [...]  line]
                    FURN, furn_problems = furniture_max.fragments(M, PX, FLOORS, f'{PX}_levels', ascii_name(M.get('shortName', M['project'])))
                    [FURN, furn_problems = furniture_max.fragments(M, 'PS', [{'key': 'L1'}], '#(PS_level)', 'Presidential suite')
                     the key is the floor key the builder wrote for the suite's furniture]
                    problems += furn_problems            (the existing  if problems: print ... sys.exit(1)  then stops as for parts)
        after   script = (header + ...)    [before  out = Path(sys.argv[1])]
                    script = furniture_max.splice(script, FURN)
        after   out.write_text(script, ...)
                    print(FURN['summary'])
    test_furniture_max.py applies exactly these edits to copies of both generators and runs them (BANK_EDITS / PRES_EDITS there).
    Optional for the suite: setUserProp o "PS_floor" 1 in PS_part, so that 'Furniture boxes only' can read the level from the scene
    (without it the level spinner is used and the window says so). The bank generator's last print line tests for placeholders with
    '__' not in script: family and block names may hold a double underscore, so make that test a regex (__[A-Z]+__).

The fragments rely on these names of the template: <px>_layer, <px>_nodes, <px>_failed, <px>_shift, the hidden datum
<px>_ORIGIN_DWG (for 'Furniture boxes only') and the level expression. Numbers use the generators' num() and pt() spelling
(negative numbers in brackets), except cos and sin (9 decimals: 4 would skew the matrix, and Max stores a skew as a scale).
"""
import math, re, unicodedata

PLACEHOLDERS = ('globals', 'functions', 'addonly', 'build', 'ui', 'ui_after', 'read', 'handlers')
KIND_KEY = re.compile(r'[a-z][a-z0-9]*(-[a-z0-9]+)*')
HEX = re.compile(r'#[0-9a-fA-F]{6}')
NONE = 'none'                              # what a user property holds when it has nothing to say (no support, no block, no handle)
CAPTION_MAX = 16                           # characters of a spinner caption before its colon: the longest that fits half of the 340 px
                                           # window beside a 40 px field (half = 154 px, the field, its arrows and gap = 60, 5.5 px a letter)


def ascii_name(s):                         # Max object names and text: plain ASCII (the generators' ascii_name, both spellings)
    s = s.replace('²', '2').replace('·', '-').replace('Đ', 'D').replace('đ', 'd')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return ' '.join(re.sub(r'[\x00-\x1f\x7f]', ' ', s).replace('"', "'").replace('\\', '/').split())


def num(v):                                # the generators' num(): negative numbers in brackets, never read as a minus
    v = round(v, 4) + 0.0                  # (+ 0.0: no -0.0000)
    return f'({v:.4f})' if v < 0 else f'{v:.4f}'


def numx(v):                               # cos and sin: 9 decimals, so the matrix stays orthonormal to float precision
    v = round(v, 9) + 0.0
    return f'({v:.9f})' if v < 0 else f'{v:.9f}'


def pt(p): return f'[{num(p[0])},{num(p[1])}]'
def arr(v): return '#(' + ','.join(v) + ')'
def real(v): return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
def layer_suffix(key): return ''.join(w.capitalize() for w in key.split('-'))     # coffee-table -> CoffeeTable
def txt(s): return ascii_name(s or '') or NONE                                     # a property's text: ASCII, and none for nothing


def caption(k):                            # a spinner's caption: the kind's label, or its key in words when the label is too long
    s = ascii_name(k.get('label') or '').replace('&', 'and')                      # (& would underline the next letter)
    if not s or len(s) > CAPTION_MAX: s = k['key'].replace('-', ' ').capitalize()[:CAPTION_MAX]
    return s + ':'


# ---- the MAXScript fragments (the __PX__ prefix, __TITLE__ and the data are filled in by fragments()) -------------------

GLOBALS = r'''-- Furniture boxes: one coloured placeholder box per furniture piece (colour = kind), on layers __PX___<level>_Furn_<Kind>. Type
-- each kind's height in mm in the window, before the build or later with "Apply furniture heights" (boxes on a table, counter or
-- cabinet follow its height). A box is a live Box, never an Editable Poly, and carries the piece's family, block and DWG layer
-- as user properties, so the 3D team can swap it for their own model by family name. A property with nothing to say (no support,
-- no block, no handle) holds the word none, never empty text: 3ds Max does not say what getUserProp returns for empty text.
-- Each box is checked as it is built: base z, top z and its four corners carried through its transform, and the node's min and
-- max in the plan only for an unrotated box (Autodesk does not say what they are for a turned node). A box that fails goes on
-- layer __PX___Check_Failed and is listed in the Listener; the rest is still built.
-- "Furniture boxes only" adds just the boxes to a scene already built from this model. Below: the kinds in the model's order,
-- heights and bases in metres.
global __PX___furnWant = true
global __PX___furnAddOnly = false
global __PX___furnFloors = __FLOORS__
global __PX___furnKeys = __KEYS__
global __PX___furnLayers = __LAYERS__
global __PX___furnBases = __BASES__
global __PX___furnHeights = __HEIGHTS__
global __PX___furnLevels = #()
global __PX___furnMats = #()'''

FUNCTIONS = r'''-- Furniture boxes: one coloured Box per piece, a placeholder the 3D team swaps for their own model by family name.
-- A box is a live Box (width along its own long axis, length across it, height), never an Editable Poly or Mesh and never
-- collapsed: "Collapse all now" only takes objects that carry __PX___kind and a modifier, and a box has neither. Every box
-- carries __PX___floor and __PX___base (its bottom, in metres above its level) and __PX___follow = false, so "Update levels
-- and heights" moves it with its level and leaves its height alone.
fn __PX___furnNum v = ((v as string) as float)
fn __PX___furnMakeMaterials =
(
    __PX___furnMats = #()
__MATERIALS__
)
-- The floor levels the build was started with (a copy: nothing is shared with the script's own array).
fn __PX___furnSetLevels =
(
    __PX___furnLevels = #()
    for z in (__LEVELS__) do append __PX___furnLevels z
)
-- Where a box stands, in metres above its level: on its kind's base, or on top of the kind of support it was drawn on
-- (ki = its kind, oki = the kind of its support, 0 for none). A support never stands on anything.
fn __PX___furnZ0 ki oki =
(
    local z0 = __PX___furnBases[ki]
    if oki > 0 do z0 = __PX___furnBases[oki] + __PX___furnHeights[oki]
    z0
)
-- kind = the kind, nm = the object's name, fi = the floor's index, pid = the piece's id, supId and supKind = its support's id
-- and kind ("none" for none), c = the box's centre and cs = its four corners (DWG coordinates), w d = its size along its own
-- long and short axis, ca sa = cos and sin of the angle from +x to the long axis, fam blk lay hnd = family, block, DWG layer,
-- handle ("none" for nothing). The box gets an explicit matrix: its X, Y and Z axes in the world, then its pivot (the middle of
-- its base).
fn __PX___furnBox kind nm fi pid supId supKind c w d ca sa cs fam blk lay hnd =
(
    local ki = findItem __PX___furnKeys kind
    local z0 = __PX___furnZ0 ki (findItem __PX___furnKeys supKind)
    local ht = __PX___furnHeights[ki]
    local zb = __PX___furnLevels[fi] + z0
    local o = box name:nm width:w length:d height:ht
    o.transform = (matrix3 [ca, sa, 0.0] [(0.0 - sa), ca, 0.0] [0.0, 0.0, 1.0] [c.x - __PX___shift.x, c.y - __PX___shift.y, zb])
    local mt = __PX___furnMats[ki]
    o.material = mt
    o.wirecolor = mt.diffuse
    setUserProp o "__PX___furn" "true"
    setUserProp o "__PX___furnKind" kind
    setUserProp o "__PX___furnId" pid
    setUserProp o "__PX___furnOn" supId
    setUserProp o "__PX___furnOnKind" supKind
    setUserProp o "__PX___family" fam
    setUserProp o "__PX___block" blk
    setUserProp o "__PX___layer" lay
    setUserProp o "__PX___handle" hnd
    setUserProp o "__PX___floor" fi
    setUserProp o "__PX___base" z0
    setUserProp o "__PX___follow" false
    -- the checks: base and top z; the world bounding box, but only for an unrotated box (sin of its rotation below 0.00001 and cos
    -- positive: the node's min and max are then certainly the box's own extents; Autodesk does not say what they are for a node that
    -- is turned, a quarter turn included, and a box built right must not go on the failed layer for that); and the four corners
    -- (the box's own corner points carried to the world by its transform) against the corners the generator worked out from the
    -- model, which proves its position, size and rotation for every box
    local why = ""
    local tol = 0.002
    local unrotated = abs(sa) < 0.00001 and ca > 0.0
    local mnx = cs[1].x
    local mxx = cs[1].x
    local mny = cs[1].y
    local mxy = cs[1].y
    for p in cs do
    (
        if p.x < mnx do mnx = p.x
        if p.x > mxx do mxx = p.x
        if p.y < mny do mny = p.y
        if p.y > mxy do mxy = p.y
    )
    if abs(o.min.z - zb) > tol then why = "base z"
    else if abs(o.max.z - (zb + ht)) > tol then why = "top z"
    else if unrotated and (abs(o.min.x - (mnx - __PX___shift.x)) > tol or abs(o.min.y - (mny - __PX___shift.y)) > tol or abs(o.max.x - (mxx - __PX___shift.x)) > tol or abs(o.max.y - (mxy - __PX___shift.y)) > tol) then why = "bounding box"
    else
    (
        local hw = o.width / 2.0
        local hd = o.length / 2.0
        local lc = #([(0.0 - hw), (0.0 - hd), 0.0], [hw, (0.0 - hd), 0.0], [hw, hd, 0.0], [(0.0 - hw), hd, 0.0])
        for k = 1 to 4 do
        (
            local q = lc[k] * o.transform
            if why == "" and (abs(q.x - (cs[k].x - __PX___shift.x)) > tol or abs(q.y - (cs[k].y - __PX___shift.y)) > tol) then why = "corner " + (k as string)
        )
    )
    if why == "" then
    (
        (__PX___layer ("__PX___" + __PX___furnFloors[fi] + "_Furn_" + __PX___furnLayers[ki])).addNode o
        setUserProp o "__PX___check" "ok"
    )
    else
    (
        (__PX___layer "__PX___Check_Failed").addNode o
        setUserProp o "__PX___check" why
        append __PX___failed (nm + ": " + why)
    )
    append __PX___nodes o
    o
)
-- Every piece of the model, in the model's order.
fn __PX___furnAll =
(
__CALLS__
)
-- The build's furniture step: materials, levels, every box.
fn __PX___furnRun =
(
    __PX___furnMakeMaterials()
    __PX___furnSetLevels()
    __PX___furnAll()
)
-- For every floor, its level as the scene has it: the most common value (to the millimetre) of z minus __PX___base over the
-- objects that carry __PX___floor and __PX___base. Sets __PX___furnLevels for the floors it finds and returns how many.
fn __PX___furnSceneLevels =
(
    local fis = #()
    local mms = #()
    local cnt = #()
    for o in objects where (getUserProp o "__PX___floor") != undefined and (getUserProp o "__PX___base") != undefined do
    (
        local fi = (__PX___furnNum (getUserProp o "__PX___floor")) as integer
        local mmv = (floor ((o.pos.z - (__PX___furnNum (getUserProp o "__PX___base"))) * 1000.0 + 0.5)) as integer
        local k = 0
        for j = 1 to fis.count where fis[j] == fi and mms[j] == mmv do k = j
        if k == 0 then ( append fis fi; append mms mmv; append cnt 1 )
        else cnt[k] += 1
    )
    local found = 0
    for f = 1 to __PX___furnFloors.count do
    (
        local best = 0
        for j = 1 to fis.count where fis[j] == f and cnt[j] > best do
        (
            best = cnt[j]
            __PX___furnLevels[f] = mms[j] / 1000.0
        )
        if best > 0 do found += 1
    )
    found
)
-- "Furniture boxes only": adds the boxes to a scene already built from this model and changes nothing else. It refuses, and
-- changes nothing, when boxes are there already or System Units are not metres. The placement shift comes from the hidden
-- datum __PX___ORIGIN_DWG (shift = minus its x, y) and each level from the objects that carry __PX___floor and __PX___base;
-- what it cannot find it takes from the window (the tick box and the level spinners), and says so. It reports in message boxes
-- of its own (the Build button's message is written for parts), so __PX___build returns false after it.
fn __PX___furnAdd =
(
    if __PX___furnWant == false then
    (
        messageBox "Tick Build furniture boxes as well. Nothing in this scene has been changed." title:"__TITLE__"
        return false
    )
    if abs(units.systemScale - 1.0) > 0.0001 or units.systemType != #meters then
    (
        messageBox "This scene's System Units are not metres, so the boxes would come out the wrong size. Nothing in this scene has been changed." title:"__TITLE__"
        return false
    )
    local existing = 0
    for o in objects where (getUserProp o "__PX___furn") != undefined or (matchPattern o.layer.name pattern:"__PX___*_Furn_*") do existing += 1
    if existing > 0 then
    (
        messageBox ("This scene already has furniture boxes (" + (existing as string) + " objects). Nothing in this scene has been changed.") title:"__TITLE__"
        return false
    )
    local t0 = timeStamp()
    local notes = ""
    local datum = undefined
    for o in objects where o.name == "__PX___ORIGIN_DWG" do datum = o
    if datum == undefined then notes += "The origin datum __PX___ORIGIN_DWG was not found, so the boxes are placed by the tick box At the drawing's own coordinates. "
    else __PX___shift = [0.0 - datum.pos.x, 0.0 - datum.pos.y]
    __PX___nodes = #()
    __PX___failed = #()
    __PX___furnMakeMaterials()
    __PX___furnSetLevels()
    local found = __PX___furnSceneLevels()
    if found < __PX___furnFloors.count then notes += "The level of " + ((__PX___furnFloors.count - found) as string) + " floor(s) was not found in the scene, so the level spinners are used for it. "
    __PX___furnAll()
    format "__PX__ FURNITURE BOXES ADDED: % boxes in % s, % failed checks\n" __PX___nodes.count ((timeStamp() - t0) / 1000.0) __PX___failed.count
    for f in __PX___failed do format "  check failed: %\n" f
    if notes != "" do messageBox notes title:"__TITLE__"
    if __PX___failed.count == 0 then messageBox ("Added " + (__PX___nodes.count as string) + " furniture boxes. Every box passed its height and position checks. Nothing else in this scene was changed. Save As to keep your .max file.") title:"__TITLE__"
    else messageBox ((__PX___failed.count as string) + " of the " + (__PX___nodes.count as string) + " furniture boxes failed a check and are on layer __PX___Check_Failed (listed in the MAXScript Listener). The others were added and passed. Nothing else in this scene was changed.") title:"__TITLE__"
    true
)
-- After the build: every box takes the height of its kind (__PX___furnHeights, read from the window) and stands on its kind's
-- base, or on top of the kind of support it was drawn on (the support's kind is none, or undefined, or empty: no support). A box
-- keeps the level it is on (its z minus its __PX___base), so levels moved by "Update levels and heights" stay. A box that is not
-- a Box any more, or of an unknown kind, is left alone.
fn __PX___furnApply =
(
    local n = 0
    local skipped = 0
    for o in objects where (getUserProp o "__PX___furn") != undefined do
    (
        local ki = findItem __PX___furnKeys ((getUserProp o "__PX___furnKind") as string)
        if (classOf o) != Box or ki == 0 then skipped += 1
        else
        (
            local z0 = __PX___furnZ0 ki (findItem __PX___furnKeys ((getUserProp o "__PX___furnOnKind") as string))
            o.pos.z = o.pos.z - (__PX___furnNum (getUserProp o "__PX___base")) + z0
            o.height = __PX___furnHeights[ki]
            setUserProp o "__PX___base" z0
            n += 1
        )
    )
    #(n, skipped)
)'''

ADDONLY = r'''    if __PX___furnAddOnly then
    (
        -- "Furniture boxes only" has said what it did, or why it did nothing, in its own message: false = nothing more to report
        __PX___furnAdd()
        return false
    )'''

BUILD = r'''    if __PX___furnWant do __PX___furnRun()'''

UI = r'''    group "Furniture boxes (heights in mm)"
    (
        checkbox fb "Build furniture boxes" checked:true
        checkbox fo "Furniture boxes only" checked:false tooltip:"Add only the boxes to the scene already built from this model: no structure, and the empty-scene check is skipped"
        label fol "(add to the scene already built from this model)" align:#left
__SPINNERS__
    )'''

UI_AFTER = r'''        button fap "Apply furniture heights" width:300'''

READ = r'''        __PX___furnHeights = __READ__
        __PX___furnWant = fb.checked
        __PX___furnAddOnly = fo.checked'''

HANDLERS = r'''    on fap pressed do
    (
        __PX___furnHeights = __READ__
        local r = __PX___furnApply()
        messageBox ((r[1] as string) + " furniture boxes set to the heights in the window and stood on their floor or support." + (if r[2] > 0 then ("\n" + (r[2] as string) + " were left alone (not a Box any more, or a kind this script does not know).") else "")) title:"__TITLE__"
    )'''


def fragments(M, px, floors, levels_expr, title):
    out = {k: '' for k in PLACEHOLDERS}
    out['calls'], out['summary'] = [], 'no furniture'
    kinds, pieces = M.get('furnitureKinds') or [], M.get('furniture') or []
    if not pieces: return out, []
    problems = []
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*', px): problems.append(f'prefix {px!r}: letters and digits only')
    FI = {}                                # floor key -> the floor index the script's parts carry (MAXScript counts from 1)
    for i, f in enumerate(floors):
        k = f.get('key')
        if not isinstance(k, str) or not k or ascii_name(k) != k or ' ' in k: problems.append(f'floor key {k!r}: plain ASCII, no spaces')
        elif k in FI: problems.append(f'floor key {k}: listed twice')
        else: FI[k] = i + 1
    if not FI: problems.append('no floors')
    kind = {}
    for k in kinds:
        key = k.get('key')
        if not isinstance(key, str) or not KIND_KEY.fullmatch(key): problems.append(f'furniture kind {key!r}: key must be lower-case words joined by hyphens'); continue
        if key == NONE: problems.append(f'furniture kind {key}: the word {NONE} is what a box without a support carries, not a kind'); continue
        if key in kind: problems.append(f'furniture kind {key}: listed twice'); continue
        if not HEX.fullmatch(str(k.get('colour', ''))): problems.append(f'furniture kind {key}: colour {k.get("colour")!r} is not #rrggbb')
        if not real(k.get('height')) or k['height'] < 0.5: problems.append(f'furniture kind {key}: height must be a number of mm, 0.5 or more (it is rounded to whole mm)')
        if not real(k.get('base')) or k['base'] < 0: problems.append(f'furniture kind {key}: base must be a number of mm, 0 or more')
        kind[key] = k
    by_id = {}
    for p in pieces:
        pid = p.get('id')
        if not isinstance(pid, str) or not pid: problems.append(f'furniture piece without an id: {str(p)[:80]}')
        elif pid in by_id: problems.append(f'{pid}: id used twice')
        else: by_id[pid] = p
    ox, oy = M['offset']
    calls, seen = [], {}
    for pid, p in by_id.items():
        fl, key, on = p.get('floor'), p.get('kind'), p.get('on')
        if not isinstance(fl, str) or fl not in FI: problems.append(f'{pid}: unknown level {fl!r}'); continue
        if not isinstance(key, str) or key not in kind: problems.append(f'{pid}: unknown kind {key!r}'); continue
        if on is not None and not isinstance(on, str): problems.append(f'{pid}: stands on {on!r}, which is not an id'); continue
        seen[key] = seen.get(key, 0) + 1
        bad = [f for f in ('x', 'y', 'w', 'd', 'rot') if not real(p.get(f))]
        if bad: problems.append(f'{pid}: {", ".join(bad)} must be numbers'); continue
        if p['w'] <= 0 or p['d'] <= 0: problems.append(f'{pid}: size {p["w"]} x {p["d"]} must be above 0'); continue
        m = re.fullmatch(re.escape(f'{fl}-{key}-') + r'(\d+)', pid)
        if not m: problems.append(f'{pid}: id is not <level>-<kind>-<nnn> ({fl}-{key}-nnn)'); continue
        fam = ascii_name(p.get('family') or '')
        name = f'{px}_{fl}_Furn_{key}_{m.group(1)}' + (f'_{fam[:40].rstrip(" _-")}' if fam[:40].rstrip(' _-') else '')   # unique: the id is
        sup_key = ''
        if on is not None:                 # a piece stands on a support of its own level; supports never stand on anything
            s = by_id.get(on)
            if s is None: problems.append(f'{pid}: stands on {on}, which is not in the list')
            elif not kind.get(s.get('kind'), {}).get('support'): problems.append(f'{pid}: stands on {on}, a {s.get("kind")}, which is not a support kind')
            elif s.get('floor') != fl: problems.append(f'{pid}: stands on {on}, which is on another level')
            else: sup_key = s['kind']
            if kind[key].get('support'): problems.append(f'{pid}: a support ({key}) cannot stand on another piece')
        w, d = p['w'], p['d']
        a = math.radians(p['rot']); ca, sa = math.cos(a), math.sin(a)
        cx, cy = p['x'] + ox, p['y'] + oy
        cs = [(cx + ca * u - sa * v, cy + sa * u + ca * v) for u, v in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))]
        calls.append(f'    {px}_furnBox "{key}" "{name}" {FI[fl]} "{ascii_name(pid)}" "{txt(on)}" "{sup_key or NONE}" {pt((cx, cy))} '
                     f'{num(w)} {num(d)} {numx(ca)} {numx(sa)} {arr([pt(q) for q in cs])} "{fam or NONE}" "{txt(p.get("block"))}" '
                     f'"{txt(p.get("layer"))}" "{txt(p.get("handle"))}"')
    for key, k in kind.items():
        if real(k.get('count')) and k['count'] != seen.get(key, 0): problems.append(f'furniture kind {key}: count {k["count"]} but {seen.get(key, 0)} pieces')
    used = [k for key, k in kind.items() if key in seen]
    if not used and not problems: problems.append('furniture pieces but no furniture kinds')
    if problems: return out, problems
    mm = [math.floor(k['height'] + 0.5) for k in used]       # whole mm, a half rounds up (the viewer and the CSV round the same way)
    spinners = '\n'.join(f'        spinner fh{i + 1} "{caption(k)}" ' + ('across:2 ' if i % 2 == 0 and i + 1 < len(used) else '')
                         + f'range:[{min(10, h)}, {max(5000, h)}, {h}] type:#integer fieldwidth:40' for i, (k, h) in enumerate(zip(used, mm)))
    read = arr([f'(fh{i + 1}.value / 1000.0)' for i in range(len(used))])
    materials = '\n'.join('    append __PX___furnMats (standardMaterial name:"__PX__ Furn ' + k['key'] + '" diffuse:(color '
                          + ' '.join(str(int(k['colour'][j:j + 2], 16)) for j in (1, 3, 5)) + '))' for k in used)
    data = (('__FLOORS__', arr([f'"{k}"' for k in FI])), ('__KEYS__', arr([f'"{k["key"]}"' for k in used])),
            ('__LAYERS__', arr([f'"{layer_suffix(k["key"])}"' for k in used])), ('__BASES__', arr([num(k['base'] / 1000) for k in used])),
            ('__HEIGHTS__', arr([num(h / 1000) for h in mm])), ('__MATERIALS__', materials), ('__CALLS__', '\n'.join(calls)),
            ('__SPINNERS__', spinners), ('__READ__', read), ('__LEVELS__', levels_expr), ('__TITLE__', ascii_name(title)), ('__PX__', px))
    for name, text in (('globals', GLOBALS), ('functions', FUNCTIONS), ('addonly', ADDONLY), ('build', BUILD), ('ui', UI),
                       ('ui_after', UI_AFTER), ('read', READ), ('handlers', HANDLERS)):
        for k, v in data: text = text.replace(k, v)
        out[name] = text
    out['calls'] = calls
    out['summary'] = f'furniture boxes {len(calls)} (' + ', '.join(f'{k["key"]} {seen[k["key"]]}' for k in used) + f') | height spinners {len(used)}'
    return out, []


def splice(script, frags):
    for k in PLACEHOLDERS:
        line = f'__FURN_{k.upper()}__\n'
        if script.count(line) != 1: raise ValueError(f'the template needs exactly one line {line.strip()} (found {script.count(line)})')
        script = script.replace(line, frags[k] + '\n' if frags[k] else '')
    return script
