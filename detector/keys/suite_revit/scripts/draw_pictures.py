"""Pictures of the suite_revit drawing for the labellers (step 2 of the held-out run), from the flattened cache only.

  python -B draw_pictures.py <prims.pkl> <out folder>

Writes into <out folder>:
  overview_all.png        the whole plan, every layer, 1 m grid (0.5 m minor), tile boxes, room names
  overview_structure.png  the whole plan with only A-WALL, layer 0, S-COLS, the curtain-wall layers, the door layers,
                          A-DETL, A-GENM(-HDLN): no loose furniture, fixtures, casework, lights (layer 0 still carries
                          the furniture outlines that sit on it)
  overview_layer0.png     layer 0 alone (with A-WALL in light grey for reference)
  tile_<C><R>.png         overlapping 6 x 6 m close-ups (columns A..F west to east, rows 1..3 south to north),
                          every layer, labelled 1 m grid with 0.5 m minor lines, block names at their geometry
  detail_*.png            close-ups that show how one kind of thing is drawn (examples of a convention, not a list)
The list of pictures with their boxes is printed; ../pictures/INDEX.md was written by hand from that list.
Coordinates are drawing metres (DXF millimetres / 1000), the same as prims.pkl and the detector.
Line work is coloured by layer; an entity whose own linetype is dashed or hidden is drawn dashed.
No detector output is read or drawn.
"""
import math, pickle, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

# layer: (colour, line width at 100 px/m, line style, z order, legend text, hatch fill alpha)
STYLE = {
    'A-WALL':       ('#000000', 1.4, '-', 9, 'A-WALL: facade, corridor and shaft walls (face lines + solid fills)', 0.55),
    '0':            ('#a0522d', 0.8, '-', 8, 'layer 0: partitions + wall linings (lines, solid fills) AND furniture / casework', 0.45),
    'S-COLS':       ('#222222', 1.2, '-', 9, 'S-COLS: concrete columns 500x1000 (blocks)', 0.6),
    'A-GLAZ-CURT':  ('#00a5c8', 1.2, '-', 10, 'A-GLAZ-CURT: curtain-wall glazed panels (blocks)', 0.5),
    'A-GLAZ-CWMG':  ('#006d6d', 1.0, '-', 10, 'A-GLAZ-CWMG: curtain-wall mullions 100x50 (blocks)', 0.6),
    'A-DOOR':       ('#e01b1b', 1.1, '-', 11, 'A-DOOR: door leaves, swing arcs (dashed), slide arrows, bi-fold panels', 0.5),
    'A-DOOR-FRAM':  ('#c000c0', 0.9, '-', 11, 'A-DOOR-FRAM: door frames', 0.5),
    'A-DETL-GENF':  ('#ff7f00', 0.9, '-', 11, 'A-DETL-GENF: door handles', 0.5),
    'A-DOOR-HDLN':  ('#e01b1b', 0.8, '--', 11, 'A-DOOR-HDLN: dashed 30-degree swings of the glass doors', 0.5),
    'A-DETL':       ('#b8860b', 1.2, '-', 10, 'A-DETL: X marks of service risers', 0.5),
    'A-GENM':       ('#7b3fbf', 1.0, '-', 10, 'A-GENM: generic models (bed linen, cushions, hatched tops)', 0.5),
    'A-GENM-HDLN':  ('#9e86d6', 0.6, '--', 6, 'A-GENM-HDLN: dashed handle outlines of the glass doors', 0.5),
    'Q-CASE':       ('#c49a5a', 0.45, '-', 4, 'Q-CASE: casework / joinery (wall panels, mini-bars)', 0.35),
    'Q-CASE-HDLN':  ('#c49a5a', 0.6, '--', 4, 'Q-CASE-HDLN: casework, hidden (dashed)', 0.35),
    'P-SANR-FIXT':  ('#1f4fff', 0.7, '-', 5, 'P-SANR-FIXT: sanitary fixtures', 0.35),
    'I-FURN':       ('#2e8b57', 0.7, '-', 5, 'I-FURN / I-FURN-CHAR: furniture', 0.35),
    'I-FURN-CHAR':  ('#2e8b57', 0.7, '-', 5, None, 0.35),
    'M_Arredi':     ('#6b8e23', 0.7, '-', 5, 'M_Arredi: furnishings', 0.35),
    'Q-SPCQ':       ('#86b830', 0.5, ':', 3, 'Q-SPCQ (frozen layer): curtains, TV, lamps, fridge', 0.3),
    'E-LITE-EQPM':  ('#d4a017', 0.6, '-', 4, 'E-LITE-EQPM: light fittings', 0.3),
    'M-EQPM':       ('#4682b4', 0.7, '-', 5, 'M-EQPM: round table tops (short segments), fire-hose cabinet', 0.3),
    'G-IMPT':       ('#7f7f7f', 0.6, '-', 3, 'G-IMPT (WC flush plate) / I-WALL-HATT (cushions)', 0.3),
    'I-WALL-HATT':  ('#7f7f7f', 0.6, '-', 3, None, 0.3),
}
OTHER = ('#999999', 0.5, '-', 3, 'other layers', 0.3)
STRUCTURE = {'A-WALL', '0', 'S-COLS', 'A-GLAZ-CURT', 'A-GLAZ-CWMG', 'A-DOOR', 'A-DOOR-FRAM', 'A-DETL-GENF', 'A-DOOR-HDLN',
             'A-DETL', 'A-GENM', 'A-GENM-HDLN'}

EXTENT = (1.0, -0.5, 26.0, 13.5)          # padded plan extent (the geometry is x 1.569-25.079, y 0.008-13.084)
TILE = 6.0
TX = [1.0, 4.8, 8.6, 12.4, 16.2, 20.0]    # tile west edges: 6 columns, 2.2 m overlap
TY = [-0.5, 3.5, 7.5]                    # tile south edges: 3 rows, 2 m overlap


def short_block(name):
    s = name.replace('-GENERAL ARRANGEMENT PLAN', '').replace('-FURNITURE PLAN - EXECUTIVE SUITE', '').replace('-FURNITURE PLAN', '')
    return s


def load(pkl):
    with open(pkl, 'rb') as f:
        return pickle.load(f)


def pts_of(d):
    return d.get('pts') or [q for l in d.get('loops', []) for q in l] or ([d['ins']] if 'ins' in d else [])


def block_labels(items):
    """One label per cluster of each top-level insert's expanded geometry (an insert of a Revit family whose geometry
    sits away from its insert point is labelled where the geometry is)."""
    tops = {d['h']: d for d in items if d['t'] == 'INSERT' and d['depth'] == 0}
    geo = {}
    for d in items:
        if d['depth'] >= 1 and d['t'] != 'INSERT' and 'text' not in d:
            geo.setdefault(d['h'], []).append(d)
    labels = []
    for h, ins in tops.items():
        clusters = []                                   # [xmin, ymin, xmax, ymax]
        for d in geo.get(h, []):
            P = pts_of(d)
            if not P:
                continue
            xs = [p[0] for p in P]; ys = [p[1] for p in P]
            b = [min(xs), min(ys), max(xs), max(ys)]
            for c in clusters:
                if b[0] <= c[2] + 0.6 and b[2] >= c[0] - 0.6 and b[1] <= c[3] + 0.6 and b[3] >= c[1] - 0.6:
                    c[0] = min(c[0], b[0]); c[1] = min(c[1], b[1]); c[2] = max(c[2], b[2]); c[3] = max(c[3], b[3])
                    break
            else:
                clusters.append(b)
        ix, iy = ins['ins']
        if clusters and (min(c[0] for c in clusters) - 0.5 <= ix <= max(c[2] for c in clusters) + 0.5 and
                         min(c[1] for c in clusters) - 0.5 <= iy <= max(c[3] for c in clusters) + 0.5):
            clusters = [[ix, iy, ix, iy]]                # family drawn around its insert point (doors, columns): one label there
        for c in clusters:
            labels.append({'name': short_block(ins['name']), 'lay': ins['lay'], 'x': (c[0] + c[2]) / 2, 'y': (c[1] + c[3]) / 2,
                           'box': c, 'rot': ins['rot'], 'mir': ins['sx'] * ins['sy'] < 0})
    return labels


def draw(items, labels, box, out, px=2400, grid=1.0, minor=0.5, title='', layers=None, tiles=None, label_blocks='all',
         text_scale=1.0, room_text=True):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    s = px / max(w, h)                                  # pixels per metre
    lw_scale = max(0.6, min(2.2, s / 160))
    segs, fills = {}, {}
    texts = []
    for d in items:
        lay = d['lay']
        if layers is not None and lay not in layers:
            continue
        if d['t'] == 'INSERT':
            continue
        if 'text' in d:
            x, y = d['ins']
            if x0 <= x <= x1 and y0 <= y <= y1 and d['text'] and d['t'] != 'ATTRIB':
                texts.append(d)
            continue
        polys = [d['pts']] if 'pts' in d else d.get('loops', [])
        for p in polys:
            if not p:
                continue
            xs = [q[0] for q in p]; ys = [q[1] for q in p]
            if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1:
                continue
            if d['t'] == 'HATCH' and d.get('solid') and len(p) > 2:
                fills.setdefault(lay, []).append(p)
            pp = p + [p[0]] if (d.get('closed') or 'loops' in d) and len(p) > 2 else p
            if len(pp) == 1:
                pp = [pp[0], [pp[0][0] + 1e-4, pp[0][1]]]
            dashed = d.get('lt') not in (None, 'BYLAYER', 'BYBLOCK', 'Continuous', 'CONTINUOUS')
            segs.setdefault((lay, dashed), []).extend(zip(pp, pp[1:]))
    W, H = w * s / 100 + 8.6, h * s / 100 + 1.4
    fig = plt.figure(figsize=(W, H), dpi=100)
    ax = fig.add_axes([0.7 / W, 0.75 / H, (w * s / 100) / W, (h * s / 100) / H])
    for gx in [math.floor(x0 / minor) * minor + i * minor for i in range(int(w / minor) + 3)]:
        if x0 <= gx <= x1:
            major = abs(gx / grid - round(gx / grid)) < 1e-6
            ax.axvline(gx, color='#e8c48a' if major else '#f4e6cc', lw=0.7 if major else 0.4, zorder=0)
    for gy in [math.floor(y0 / minor) * minor + i * minor for i in range(int(h / minor) + 3)]:
        if y0 <= gy <= y1:
            major = abs(gy / grid - round(gy / grid)) < 1e-6
            ax.axhline(gy, color='#e8c48a' if major else '#f4e6cc', lw=0.7 if major else 0.4, zorder=0)
    used = []
    any_dashed = False
    for lay in sorted(set(k[0] for k in segs) | set(fills), key=lambda k: STYLE.get(k, OTHER)[3]):
        c, lw, ls, z, leg, fa = STYLE.get(lay, OTHER)
        if lay in fills:
            ax.add_collection(PolyCollection(fills[lay], facecolors=c, edgecolors='none', alpha=fa, zorder=z - 0.5))
        for dashed in (False, True):
            if (lay, dashed) in segs:
                any_dashed |= dashed and ls == '-'
                ax.add_collection(LineCollection(segs[(lay, dashed)], colors=c, linewidths=lw * lw_scale,
                                                 linestyles=(0, (5, 3)) if dashed else ls, zorder=z))
        leg = leg or {'I-FURN-CHAR': STYLE['I-FURN'][4], 'I-WALL-HATT': STYLE['G-IMPT'][4]}.get(lay, OTHER[4])
        if not any(u[2] == leg for u in used):
            used.append((c, ls, leg))
    if any_dashed:
        used.append(('#555555', (0, (5, 3)), 'dashed: the entity itself has a dashed / hidden linetype (overhead or beyond)'))
    fs = 7.5 * text_scale
    if room_text:
        for d in texts:
            ax.text(d['ins'][0], d['ins'][1], d['text'][:40], fontsize=fs * 1.4, color='#303030', weight='bold', zorder=20,
                    va='top', ha='left', bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.7))
    for b in labels:
        if label_blocks == 'none':
            continue
        if label_blocks == 'doors' and b['lay'] not in ('A-DOOR', 'A-WALL', 'S-COLS', 'M-EQPM'):
            continue
        if layers is not None and b['lay'] not in layers:
            continue
        if not (x0 <= b['x'] <= x1 and y0 <= b['y'] <= y1):
            continue
        col = {'A-DOOR': '#b00000', 'A-WALL': '#000000', 'S-COLS': '#000000', 'A-GLAZ-CURT': '#006080',
               'A-GLAZ-CWMG': '#006d6d', 'Q-SPCQ': '#4d7a00', 'Q-CASE': '#8a6326'}.get(b['lay'], '#555555')
        nm = b['name'] + (' [mirrored]' if b['mir'] else '')
        small = b['lay'] in ('A-GLAZ-CWMG', 'A-GLAZ-CURT', 'Q-SPCQ', 'I-FURN-CHAR', 'Q-CASE')
        ax.plot(b['x'], b['y'], marker='+', color=col, ms=5, zorder=21)
        ax.text(b['x'], b['y'], ' ' + nm, fontsize=fs * (0.75 if small else 0.95), color=col, zorder=21, rotation=0,
                bbox=dict(boxstyle='square,pad=0.05', fc='white', ec='none', alpha=0.55))
    if tiles:
        for nm, (tx0, ty0, tx1, ty1) in tiles:
            ax.add_patch(Rectangle((tx0, ty0), tx1 - tx0, ty1 - ty0, fill=False, ec='#ff00aa', lw=0.9, ls='--', zorder=30))
            ax.text(tx0 + 0.08, ty1 - 0.08, nm, color='#ff00aa', fontsize=fs * 1.6, weight='bold', va='top', zorder=31)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
    xt = [math.ceil(x0 / grid) * grid + i * grid for i in range(int(w / grid) + 2)]
    yt = [math.ceil(y0 / grid) * grid + i * grid for i in range(int(h / grid) + 2)]
    ax.set_xticks([v for v in xt if v <= x1]); ax.set_yticks([v for v in yt if v <= y1])
    ax.set_xticklabels([f'{v:g}' for v in xt if v <= x1]); ax.set_yticklabels([f'{v:g}' for v in yt if v <= y1])
    ax.tick_params(labelsize=fs * 1.2, top=True, right=True, labeltop=True, labelright=True)
    ax.set_xlabel('x (drawing metres)', fontsize=fs * 1.2); ax.set_ylabel('y (drawing metres)', fontsize=fs * 1.2)
    ax.set_title(title, fontsize=fs * 1.6, pad=fs * 3)
    handles = [Line2D([0], [0], color=c, ls=ls, lw=2.2) for c, ls, _ in used]
    if handles:
        fig.legend(handles, [t for _, _, t in used], loc='upper left', fontsize=fs * 1.15, frameon=True,
                   bbox_to_anchor=((0.7 + w * s / 100 + 0.75) / W, 1.0 - 0.75 / H))
    fig.savefig(out)
    plt.close(fig)
    return out


DETAILS = [   # (name, box, what it shows) -- examples of how things are drawn, for the description; not a list of openings
    ('detail_pocket_door', (6.9, 1.9, 8.0, 3.7), 'a pocket (cavity) sliding door: wall split round the pocket, leaf inside it, '
     'slide arrow on A-DOOR, two continuous layer-0 core lines across the opening, frames on A-DOOR-FRAM'),
    ('detail_hinged_door', (10.3, 3.4, 12.0, 5.0), 'an exploded hinged door: leaf as a 40 mm rectangle drawn open 90 deg, dashed arc, '
     'frames, lever handle on A-DETL-GENF'),
    ('detail_glass_screen_doors', (8.9, 5.0, 10.0, 8.1), 'the 10 mm glass screen (two lines 10 mm apart, layer 0) between two '
     'continuous lines 0.10 m apart, glass leaves drawn open 30 deg, dashed swings (A-DOOR-HDLN), dashed handle outlines'),
    ('detail_bifold', (9.0, 0.7, 10.2, 3.5), 'a four-panel bi-fold door drawn folded (zigzag on A-DOOR) with its dashed track (layer 0)'),
    ('detail_head_lines', (12.6, 4.4, 15.8, 5.8), 'a gap without a leaf: the solid fill stops, the two face lines go on across it dashed'),
    ('detail_service_doors', (14.9, 0.4, 17.5, 3.9), 'door blocks of the corridor: leaves drawn open 35 deg, frame lines across the '
     'opening (A-DOOR-FRAM), X marks of the risers behind'),
    ('detail_unit_doors', (18.8, -0.2, 22.2, 1.4), 'two door blocks (D01) whose wall face lines (A-WALL) run on across the opening; '
     'leaves and arcs cut by the crop at y 0.009'),
    ('detail_bay', (3.4, 11.0, 7.7, 13.3), 'a curtain-wall bay: glass panels and mullions in blocks, frame lines on both sides of '
     'the glass, corner wall wedges (block Walls 13), solid angled facade wall, dashed layer-0 line inside the bay, curtains'),
]


def main():
    pkl, outdir = sys.argv[1], Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    D = load(pkl)
    items = D['items']
    labels = block_labels(items)
    tiles = []
    for r, ty in enumerate(TY, 1):
        for c, tx in enumerate(TX):
            tiles.append((f'{"ABCDEF"[c]}{r}', (tx, ty, tx + TILE, ty + TILE)))
    made = []
    draw(items, labels, EXTENT, outdir / 'overview_all.png', px=3000, grid=1.0, minor=0.5, tiles=tiles, label_blocks='doors',
         title='presidential suite_layout.dwg (suite_revit): whole plan, all layers, 1 m grid; dashed magenta = close-up tiles')
    made.append(('overview_all.png', EXTENT, 'whole plan, every layer, tile boxes, room names'))
    draw(items, labels, EXTENT, outdir / 'overview_structure.png', px=3000, grid=1.0, minor=0.5, layers=STRUCTURE, tiles=tiles,
         label_blocks='doors', title='suite_revit: A-WALL, layer 0, S-COLS, curtain wall, door layers, A-DETL, A-GENM only; 1 m grid')
    made.append(('overview_structure.png', EXTENT, 'walls, columns, curtain wall, door layers (layer 0 still shows the furniture drawn on it)'))
    l0 = [dict(d, lay='__ref__') if d['lay'] == 'A-WALL' else d for d in items if d['lay'] in ('0', 'A-WALL') or 'text' in d]
    STYLE['__ref__'] = ('#c8c8c8', 0.9, '-', 2, 'A-WALL, for reference (grey)', 0.25)
    draw(l0, [], EXTENT, outdir / 'overview_layer0.png', px=3000, grid=1.0, minor=0.5, tiles=tiles, label_blocks='none',
         title='suite_revit: layer 0 alone (brown; A-WALL in grey for reference): partitions, linings, furniture and casework outlines')
    made.append(('overview_layer0.png', EXTENT, 'layer 0 alone, A-WALL in grey'))
    for nm, box in tiles:
        draw(items, labels, box, outdir / f'tile_{nm}.png', px=2400, grid=1.0, minor=0.5, label_blocks='all',
             title=f'suite_revit tile {nm}: x {box[0]:g} to {box[2]:g}, y {box[1]:g} to {box[3]:g} (drawing metres); all layers')
        made.append((f'tile_{nm}.png', box, 'all layers'))
    for nm, box, what in DETAILS:
        draw(items, labels, box, outdir / f'{nm}.png', px=1600, grid=0.5, minor=0.1, label_blocks='all',
             title=f'{nm}: x {box[0]:g} to {box[2]:g}, y {box[1]:g} to {box[3]:g} (drawing metres)')
        made.append((f'{nm}.png', box, what))
    for nm, box, what in made:
        print(f'{nm}\t{box}\t{what}')


if __name__ == '__main__':
    main()
