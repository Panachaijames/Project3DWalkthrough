"""The hotel model drawn back onto the two pictures, in picture pixels (2 Nov 2026): walls, low walls (parapets), mullions, lintels
and sills, glass, steps, railings, the floor plates' outlines (outdoor slabs dotted) and their voids, the openings with their ids (doors red,
passages green, hatches blue), the furniture boxes in their kind's colour with their ids, the flat tread lines and the room
names. It is how the model is checked against the drawing: everything should sit on what it was read from.
Uses only the model's pictureFrame (the pixel of the origin and the pixels per metre along each axis) and offset, so it checks
those too: px = originPx[0] + pxPerMetreX * (x + offset x), py = originPx[1] - pxPerMetreY * (y + offset y).
Usage: python overlay.py <out folder> [hotel_model.json]   -> <out>/overlay_F1.png, overlay_F2.png (and a 2x zoom of each; and
       overlay_<floor>_margin.png when parts reach beyond the picture's edges: the terrace, the wall at floor 2's cut edge),
       <out>/stack.png (floor 2 over floor 1 in metres)
"""
import json, math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
M = json.loads(Path(sys.argv[2] if len(sys.argv) > 2 else HERE / 'hotel_model.json').read_text(encoding='utf-8'))
ox, oy = M['offset']
try:
    FONT = ImageFont.truetype('arial.ttf', 11); SMALL = ImageFont.truetype('arial.ttf', 9)
except OSError:
    FONT = SMALL = ImageFont.load_default()
COL = {'wall': (30, 60, 230), 'mullion': (0, 90, 160), 'lintel': (200, 120, 0), 'sill': (150, 90, 20), 'glass': (0, 190, 255),
       'railing': (170, 0, 200), 'step': (0, 150, 60), 'slab': (0, 140, 0), 'parapet': (110, 70, 160)}


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def frame(fr):
    """The model metres -> picture pixel map of a pictureFrame (per axis; an old frame's single pxPerMetre is read as both)."""
    kx = fr.get('pxPerMetreX', fr.get('pxPerMetre')); ky = fr.get('pxPerMetreY', fr.get('pxPerMetre'))
    px0, py0 = fr['originPx']
    return lambda x, y: (px0 + kx * (x + ox), py0 - ky * (y + oy))


def dotted(d, pts, fill, width=2, dash=6):
    for a, b in zip(pts, pts[1:] + pts[:1]):
        L = math.dist(a, b); n = max(1, int(L // dash))
        for i in range(0, n, 2):
            t0, t1 = i / n, min(1.0, (i + 1) / n)
            d.line([(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0), (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)], fill=fill, width=width)


for f in M['floors']:
    key = f['key']; fr = M['pictureFrame'][key]
    P0 = frame(fr)
    pic = Image.open((HERE / fr['file']).resolve()).convert('RGB')
    pic = Image.blend(pic, Image.new('RGB', pic.size, (255, 255, 255)), 0.45)
    # Parts beyond the picture's edges (floor 2's terrace, the wall closing its cut edge): drawn on a canvas MARGIN px wider on every
    # side, the picture at (MARGIN, MARGIN); overlay_<key>.png is the picture's own part of it (its pixels are the picture's),
    # overlay_<key>_margin.png the whole canvas with the picture's border drawn grey.
    xy = [P0(x, y) for p in M['parts'] if p['floor'] == key for x, y in p['o']]
    MARGIN = min(80, int(math.ceil(max([0.0] + [-x for x, _ in xy] + [-y for _, y in xy] + [x - pic.width for x, _ in xy] + [y - pic.height for _, y in xy]))) + 10)
    MARGIN = MARGIN if MARGIN > 10 else 0
    P = lambda x, y: (P0(x, y)[0] + MARGIN, P0(x, y)[1] + MARGIN)
    im = Image.new('RGB', (pic.width + 2 * MARGIN, pic.height + 2 * MARGIN), (255, 255, 255)); im.paste(pic, (MARGIN, MARGIN))
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for kind in ('slab', 'step', 'railing', 'wall', 'sill', 'parapet', 'mullion', 'lintel', 'glass'):
        for p in M['parts']:
            if p['floor'] != key or p['kind'] != kind: continue
            ring = [P(x, y) for x, y in p['o']]
            c = COL[kind]
            if kind == 'slab':
                if p.get('label'): dotted(d, ring, c + (255,), 2)
                else: d.line(ring + [ring[0]], fill=c + (255,), width=2)
                for h in p['h']: d.line([P(x, y) for x, y in h] + [P(*h[0])], fill=(200, 0, 0, 255), width=2)
            elif kind == 'lintel':
                d.line(ring + [ring[0]], fill=c + (255,), width=1)
            else:
                d.polygon(ring, fill=c + (70 if kind in ('wall', 'step', 'parapet') else 130,), outline=c + (255,))
    st = M['stairs'][key]['below']
    for i in range(0, len(st), 4): d.line([P(st[i], st[i + 1]), P(st[i + 2], st[i + 3])], fill=(0, 150, 60, 255), width=1)
    kinds = {kk['key']: kk for kk in M['furnitureKinds']}
    for b in M['furniture']:
        if b['floor'] != key: continue
        a = math.radians(b['rot']); c_, s_ = math.cos(a), math.sin(a)
        corners = [P(b['x'] + sx * b['w'] / 2 * c_ - sy * b['d'] / 2 * s_, b['y'] + sx * b['w'] / 2 * s_ + sy * b['d'] / 2 * c_)
                   for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        col = rgb(kinds[b['kind']]['colour'])
        d.polygon(corners, fill=col + (90,), outline=col + (255,))
        cxp, cyp = P(b['x'], b['y'])
        d.text((cxp, cyp), b['id'][len(key) + 1:], fill=(60, 30, 0, 255), font=SMALL, anchor='mm')
    for o in M['openings']:
        if o['floor'] != key: continue
        ux, uy = o['ny'], -o['nx']; h = o['width'] / 2
        a, b = P(o['x'] - ux * h, o['y'] - uy * h), P(o['x'] + ux * h, o['y'] + uy * h)
        col = {'door': (220, 0, 0, 255), 'passage': (0, 160, 0, 255), 'window': (0, 80, 230, 255)}[o['kind']]
        d.line([a, b], fill=col, width=3)
        t = P(o['x'] + o['nx'] * 0.45, o['y'] + o['ny'] * 0.45)
        d.text(t, o['id'], fill=col, font=FONT, anchor='mm')
        for sd in o['inside']:                                          # the sides a person can stand on: a short tick
            q0, q1 = P(o['x'] + o['nx'] * sd * 0.15, o['y'] + o['ny'] * sd * 0.15), P(o['x'] + o['nx'] * sd * 0.4, o['y'] + o['ny'] * sd * 0.4)
            d.line([q0, q1], fill=col, width=1)
    for g in M['probes']:
        if g['floor'] != key: continue
        for sd in g['inside']:
            q0, q1 = P(g['x'], g['y']), P(g['x'] + g['nx'] * sd * 0.5, g['y'] + g['ny'] * sd * 0.5)
            d.line([q0, q1], fill=(0, 120, 200, 255), width=2)
    for r in M['rooms']:
        if r['floor'] != key: continue
        d.text(P(r['x'], r['y']), r['name'], fill=(0, 70, 140, 255), font=FONT, anchor='mm')
    for v in M['voids'][key]:
        d.text(P(v['x'], v['y']), 'open: ' + v['what'], fill=(160, 0, 0, 255), font=SMALL, anchor='mm')
    whole = Image.alpha_composite(im.convert('RGBA'), lay).convert('RGB')
    out = whole.crop((MARGIN, MARGIN, MARGIN + pic.width, MARGIN + pic.height))
    out.save(OUT / f'overlay_{key}.png')
    out.resize((out.width * 2, out.height * 2), Image.LANCZOS).save(OUT / f'overlay_{key}_x2.png')
    print('written', OUT / f'overlay_{key}.png')
    if MARGIN:
        ImageDraw.Draw(whole).rectangle([MARGIN - 1, MARGIN - 1, MARGIN + pic.width, MARGIN + pic.height], outline=(150, 150, 150))
        whole.save(OUT / f'overlay_{key}_margin.png')
        print('written', OUT / f'overlay_{key}_margin.png', f'(the picture at {MARGIN}, {MARGIN}: parts reach beyond its edges)')

# The floors stacked in the model frame: floor 2's walls (red) over floor 1's (blue), the shafts' outlines, floor 1's steps and
# floor 2's floor-plate outline, so the lift cores, the facades and the stair can be compared where they should meet.
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
fig, ax = plt.subplots(figsize=(13, 15), dpi=90)
style = {'F1': dict(fc='#2f5fd0', ec='#1d3c8a', alpha=0.55), 'F2': dict(fc='#d0352f', ec='#8a1d1d', alpha=0.45)}
for p in M['parts']:
    if p['kind'] in ('wall', 'mullion'):
        ax.add_patch(MPoly(p['o'], closed=True, lw=0.4, **style[p['floor']]))
    elif p['kind'] == 'parapet':
        ax.add_patch(MPoly(p['o'], closed=True, lw=0.6, fc='none', ec=style[p['floor']]['ec'], hatch='///'))
    elif p['kind'] == 'step':
        ax.add_patch(MPoly(p['o'], closed=True, fc='none', ec='#2e8b47', lw=0.6))
    elif p['kind'] == 'railing' and p['floor'] == 'F2':
        ax.add_patch(MPoly(p['o'], closed=True, fc='#a020c0', ec='#a020c0', lw=0.8))
    elif p['kind'] == 'slab' and p['floor'] == 'F2':
        ax.add_patch(MPoly(p['o'], closed=True, fc='none', ec='#d0352f', lw=1.0, ls='--'))
        for h in p['h']: ax.add_patch(MPoly(h, closed=True, fc='none', ec='#d0352f', lw=1.0))
    elif p['kind'] == 'slab' and p['floor'] == 'F1' and p.get('label'):
        ax.add_patch(MPoly(p['o'], closed=True, fc='none', ec='#2f5fd0', lw=0.8, ls=':'))
for f in M['floors']:
    for v in M['voids'][f['key']]: ax.text(v['x'], v['y'], v['what'], fontsize=7, color='#8a1d1d', ha='center')
ax.autoscale(); ax.set_aspect('equal'); ax.grid(True, lw=0.3, alpha=0.5)
ax.set_title('Floor 1 walls blue (forecourt dotted), floor 2 walls red, floor 1 steps green, floor 2 railings purple, floor 2 plate dashed red '
             'with its holes (open stair, shafts); metres, model frame', fontsize=10)
fig.tight_layout(); fig.savefig(OUT / 'stack.png'); plt.close()
print('written', OUT / 'stack.png')
