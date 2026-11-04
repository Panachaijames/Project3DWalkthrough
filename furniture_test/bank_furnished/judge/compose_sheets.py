"""The slimming judge, step 3: the picture sheets and the picture differences (3 Nov 2026).

    python compose_sheets.py <cells folder> <judge folder> <sheets folder> [all]

Reads render_cells.mjs's cells (<cells>/<key>/<dist>_<level>.png, cells.json) and slim_levels.mjs's levels/<key>.json.
A level id 'a:<id>' is that level with its normals weighted by corner angle (cells <dist>_a_<id>.png); a plain id has them
worked out as the chair test did (three's toCreasedNormals, every face counted the same).
1. For every level of every model, both normal methods, at both distances, the picture against the full model's, pixel for
   pixel (the same camera, light and crop), over the pixels where either shows the model (each against the empty stage,
   1 px to spare):
     changedShare10 / changedShare25   share of those pixels whose brightness differs by more than 10 / 25 of 255
     meanDiff                          mean brightness difference, of 255
     ssim                              structural similarity of the brightness (Gaussian window, sigma 1.5), mean over them
     outlinePx                         pixels the model covers in one picture but not the other, as a share of the full one's
   written to <judge>/picture_diffs.json.
2. One sheet per model: the full model and the levels chosen below side by side, walking distance above, close up below, the
   triangle count under each, written to <sheets>/<key>.png; and normals_compare.png (the two ways of working out the
   normals, and the normals carried through the slimming, on the levels where they differ most). With 'all', every level of
   every model instead, both normal methods (for looking through them), and no diffs file.
Needs numpy and pillow only.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

CELLS, JUDGE, SHEETS = (Path(a) for a in sys.argv[1:4])
ALL = len(sys.argv) > 4 and sys.argv[4] == 'all'
SHEETS.mkdir(parents=True, exist_ok=True)
INDEX = json.loads((CELLS / 'cells.json').read_text(encoding='utf-8'))
ORDER = ['visitor_chair01', 'visitor_chair02', 'stool', 'sofa', 'banquet', 'working_table', 'side_table', 'monitor', 'chair_test']
INFO = {k: json.loads((JUDGE / 'levels' / f'{k}.json').read_text(encoding='utf-8')) for k in INDEX}
MODELS = [INFO[k] for k in sorted((k for k in INDEX if k in ORDER), key=ORDER.index)]
FONT_DIR = Path('C:/Windows/Fonts')
font = lambda size, bold=False: ImageFont.truetype(str(FONT_DIR / ('arialbd.ttf' if bold else 'arial.ttf')), size)

# the levels each sheet shows (normals as the chair test), chosen after looking through all of them: around where they
# start to look worse
CHOSEN = {
    'visitor_chair01': ['20000', '10000', '5000', '2500'],
    'visitor_chair02': ['50%', '2500', '25%', '12%'],
    'stool': ['50%', '25%', '12%', '6%'],
    'sofa': ['50%', '25%', '12%', '6%'],
    'banquet': ['50%', '25%', '12%', '6%'],
    'working_table': ['50%', '25%', '12%', '6%'],
    'side_table': ['50%', '25%', '12%', '6%'],
    'monitor': ['10000', '5000', '2500', '12%'],          # 5,000 shown: it is the close-up verdict (6 %, a jumble, dropped)
    'chair_test': ['20000', '10000', '5000', '2500'],
}
# normals_compare.png: (model, level, distance) where the two ways of working out the normals differ most
COMPARE = [('visitor_chair02', '2500', 'close'), ('visitor_chair02', '25%', 'walk'), ('visitor_chair01', '5000', 'close')]
DIST_TITLE = {'walk': 'Walking distance: 3 m from its centre', 'close': 'Close up: standing at it, 0.6 m from its edge'}


def cell_path(key, dist, level):
    return CELLS / key / f"{dist}_{level.replace('%', 'pct').replace(':', '_')}.png"


def load(key, dist, level):
    return np.asarray(Image.open(cell_path(key, dist, level)).convert('RGB'), dtype=np.float64)


def luminance(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def blur(a, sigma=1.5, radius=5):
    k = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    k /= k.sum()
    p = np.pad(a, radius, mode='edge')
    out = np.zeros_like(p)
    for i, w in enumerate(k):                      # rows
        out[:, radius:-radius] += w * p[:, i:i + p.shape[1] - 2 * radius]
    p2 = out[:, radius:-radius]
    out2 = np.zeros((p2.shape[0] - 2 * radius, p2.shape[1]))
    for i, w in enumerate(k):                      # columns
        out2 += w * p2[i:i + p2.shape[0] - 2 * radius, :]
    return out2


def ssim_map(x, y):
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    mx, my = blur(x), blur(y)
    sxx, syy, sxy = blur(x * x) - mx * mx, blur(y * y) - my * my, blur(x * y) - mx * my
    return ((2 * mx * my + c1) * (2 * sxy + c2)) / ((mx * mx + my * my + c1) * (sxx + syy + c2))


def dilate(m, r=1):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def compare(key, dist, level, cache):
    if (key, dist) not in cache:
        none, full = load(key, dist, 'none'), load(key, dist, 'full')
        cache[(key, dist)] = (none, full, np.abs(full - none).max(axis=2) > 3)
    none, full, mfull = cache[(key, dist)]
    lev = load(key, dist, level)
    mlev = np.abs(lev - none).max(axis=2) > 3
    mask = dilate(mfull | mlev)
    yf, yl = luminance(full), luminance(lev)
    d = np.abs(yf - yl)[mask]
    s = ssim_map(yf, yl)[mask]
    return {
        'pixels': int(mask.sum()),
        'changedShare10': round(float((d > 10).mean()), 4), 'changedShare25': round(float((d > 25).mean()), 4),
        'meanDiff': round(float(d.mean()), 2), 'ssim': round(float(s.mean()), 4),
        'outlinePx': round(float((mfull ^ mlev).sum() / max(1, mfull.sum())), 4),
    }


def fmt(n):
    return f'{n:,}'


def label_of(model, i):
    lv = {l['id']: l for l in model['levels']}
    base = lv[i.split(':', 1)[-1]]
    return base['label'], base['triangles']


def sheet(model, ids, out_file, note=None):
    key = model['key']
    cols = [('full', 'Full model, as exported', model['full']['triangles'])] + [(i, *label_of(model, i)) for i in ids]
    pad, label_h, head_h, row_head, max_w = 16, 50, 92, 34, 2800
    rows = []
    for dist in ('walk', 'close'):
        crop = INDEX[key]['dists'][dist]['crop']
        ims = [Image.open(cell_path(key, dist, i)).convert('RGB') for i, _, _ in cols]
        scale = min(1.0, (max_w - pad * (len(cols) + 1)) / (len(cols) * crop['w']))
        if scale < 1:                                  # a big piece: the cells shrunk to fit the sheet (noted in the row's title)
            ims = [im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS) for im in ims]
        rows.append((dist, crop, ims, scale))
    width = max(max(pad + sum(im.width + pad for im in r[2]) for r in rows), 1250)
    height = head_h + sum(row_head + r[2][0].height + label_h + pad for r in rows)
    img = Image.new('RGB', (width, height), (250, 250, 248))
    dr = ImageDraw.Draw(img)
    dr.text((pad, 12), f"{model['name']}  ({model['family']})", fill=(25, 28, 32), font=font(22, True))
    dr.text((pad, 44), note or (f"{model['kind']}, {model['size_m'][0]:.2f} x {model['size_m'][2]:.2f} m, {model['size_m'][1]:.2f} m tall. "
            "Same light and neutral material in every picture; the slimmed ones have their normals worked out again "
            "as in the chair test (smooth across edges under 40 degrees)."), fill=(70, 74, 80), font=font(15))
    dr.text((pad, 66), "Each picture is a crop of a 1920 x 1080 screen through the Walk camera (24 mm lens, eye 1.6 m, 30 degrees right of "
            "its front), so at 100 % the model is as many pixels as on the client's screen.", fill=(70, 74, 80), font=font(15))
    y = head_h
    for dist, crop, ims, scale in rows:
        cam = crop['camera']
        note_d = (f"   (camera {cam['distance_m']:.2f} m from its centre; the model is {crop['modelPx']['h']} px tall on screen"
                  + (', cut by the screen edge' if crop['clipped'] else '')
                  + (f'; shown here at {scale * 100:.0f} % of its size on screen, to fit' if scale < 1 else '; shown at its size on screen') + ')')
        dr.text((pad, y + 6), DIST_TITLE[dist], fill=(25, 28, 32), font=font(18, True))
        tw = dr.textlength(DIST_TITLE[dist], font=font(18, True))
        dr.text((pad + tw, y + 8), note_d, fill=(90, 94, 100), font=font(15))
        y += row_head
        x = pad
        for (i, lab, tris), im in zip(cols, ims):
            img.paste(im, (x, y))
            dr.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline=(200, 202, 205))
            share = '' if i == 'full' else f"  ({tris / model['full']['triangles'] * 100:.1f} %)"
            title = lab if i == 'full' or i.startswith('a:') or ALL is False else f'{lab}, normals as the chair test'
            if ALL and i.startswith('a:'):
                title = f'{lab}, normals by angle'
            dr.text((x, y + im.height + 6), title, fill=(25, 28, 32), font=font(16, True))
            dr.text((x, y + im.height + 27), f"{fmt(tris)} triangles{share}", fill=(60, 64, 70), font=font(15))
            x += im.width + pad
        y += ims[0].height + label_h + pad
    img.save(out_file, optimize=True)
    return out_file


def compare_sheet(out_file):
    """For each COMPARE row: the full model, the level with the chair test's normals, the same level weighted by angle, and
    (where the variant exists) the level with the exported normals carried through the slimming."""
    pad, label_h, head_h = 16, 50, 92
    rows = []
    for key, lev, dist in COMPARE:
        m = INFO[key]
        lab, tris = label_of(m, lev)
        cols = [(key, 'full', 'Full model', f"{fmt(m['full']['triangles'])} triangles"),
                (key, lev, 'Chair test normals', f'{lab}: {fmt(tris)} triangles'),
                (key, 'a:' + lev, 'By corner angle', f'{lab}: {fmt(tris)} triangles')]
        if f'{key}_n' in INDEX and cell_path(f'{key}_n', dist, lev).exists():
            mn = INFO[f'{key}_n']
            labn, trisn = label_of(mn, lev)
            cols.append((f'{key}_n', lev, 'Exported normals kept', f'{labn}: {fmt(trisn)} triangles'))
        ims = [Image.open(cell_path(k, dist, i)).convert('RGB') for k, i, _, _ in cols]
        if max(im.width for im in ims) > 640:          # true size, cut to the middle 640 px across where wider
            ims = [im.crop(((im.width - 640) // 2, 0, (im.width - 640) // 2 + 640, im.height)) for im in ims]
        rows.append((m, dist, cols, ims))
    width = max(pad + sum(im.width + pad for im in r[3]) for r in rows)
    height = head_h + sum(34 + r[3][0].height + label_h + pad for r in rows)
    img = Image.new('RGB', (width, height), (250, 250, 248))
    dr = ImageDraw.Draw(img)
    dr.text((pad, 12), 'Normals after slimming, three ways, at 100 % (true size on a 1920 x 1080 screen)', fill=(25, 28, 32), font=font(22, True))
    dr.text((pad, 44), "Chair test normals: three's toCreasedNormals, every face counted the same. By corner angle: each face weighted by its corner's angle. "
            "Exported normals kept: carried through SimplifyModifier",
            fill=(70, 74, 80), font=font(15))
    dr.text((pad, 66), '(that way cannot slim most of the models: see JUDGE.md). Same geometry in the second and third picture of each row: only the normals differ.',
            fill=(70, 74, 80), font=font(15))
    y = head_h
    for m, dist, cols, ims in rows:
        dr.text((pad, y + 6), f"{m['name']}, {DIST_TITLE[dist].lower()}", fill=(25, 28, 32), font=font(18, True))
        y += 34
        x = pad
        for (k, i, lab, sub), im in zip(cols, ims):
            img.paste(im, (x, y))
            dr.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline=(200, 202, 205))
            small = im.width < 260
            dr.text((x, y + im.height + 6), lab, fill=(25, 28, 32), font=font(14 if small else 16, True))
            dr.text((x, y + im.height + 27), sub, fill=(60, 64, 70), font=font(13 if small else 15))
            x += im.width + pad
        y += ims[0].height + label_h + pad
    img.save(out_file, optimize=True)
    return out_file


diffs, cache = {}, {}
for m in MODELS:
    key = m['key']
    ids = [l['id'] for l in m['levels']]
    have_a = cell_path(key, 'walk', 'a:' + ids[0]).exists()
    every = ids + (['a:' + i for i in ids] if have_a else [])
    diffs[key] = {dist: {i: compare(key, dist, i, cache) for i in every} for dist in ('walk', 'close')}
    cache.clear()
    if ALL:
        f = sheet(m, every, SHEETS / f'{key}_all.png')
    else:
        f = sheet(m, CHOSEN[key], SHEETS / f'{key}.png')
    print(key, '->', f)
    for dist in ('walk', 'close'):
        print('  ', dist, ' '.join(f"{i}:{d['changedShare10']:.3f}/{d['ssim']:.3f}" for i, d in diffs[key][dist].items()))
for k in INDEX:                                   # the normals-kept variant: its diffs too
    if k.endswith('_n') and k[:-2] in INDEX:
        diffs[k] = {dist: {l['id']: compare(k, dist, l['id'], {}) for l in INFO[k]['levels']} for dist in ('walk', 'close')}
if not ALL:
    print('->', compare_sheet(SHEETS / 'normals_compare.png'))
    (JUDGE / 'picture_diffs.json').write_text(json.dumps({
        'what': "each level's picture against the full model's, same camera, light and crop (compose_sheets.py); ids 'a:<id>' = normals weighted by corner angle, plain ids = normals as the chair test (toCreasedNormals); <key>_n = the exported normals carried through the slimming",
        'measures': {
            'pixels': 'pixels where either picture shows the model (against the empty stage), 1 px to spare',
            'changedShare10': 'share of those pixels whose brightness differs by more than 10 of 255',
            'changedShare25': 'the same, more than 25 of 255',
            'meanDiff': 'mean brightness difference over those pixels, of 255',
            'ssim': 'structural similarity of the brightness (Gaussian window, sigma 1.5), mean over those pixels; 1 = the same',
            'outlinePx': "pixels covered by the model in one picture but not the other, as a share of the full model's",
        },
        'models': diffs}, indent=1), encoding='utf-8')
    print('wrote', JUDGE / 'picture_diffs.json')
