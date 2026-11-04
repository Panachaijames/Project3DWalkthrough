"""Puts the close-ups of shots_closeup.mjs side by side: one row per view, one column per way (full, then the four budgets).

    python -B compose_closeup.py <shots folder>        writes slimmed_closeup.png next to this script
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

shots = Path(sys.argv[1])
HERE = Path(__file__).resolve().parent
VIEWS = [('chair_1m', 'visitor chair01, about 1 m'), ('chair_3m', 'visitor chair01, about 3 m'), ('monitor_1m', 'monitor, about 1 m')]
WAYS = [('B', 'full detail'), ('C20000', '20,000 a piece'), ('C10000', '10,000'), ('C5000', '5,000'), ('C2500', '2,500')]
TRIS = {'chair': ['241,326', '19,993', '9,987', '4,994', '2,498'], 'monitor': ['15,290', '15,290 (as it is)', '9,989', '4,990', '2,489']}
CROP = (660, 190, 1260, 790)                  # the middle of the 1920 x 1080 view, 600 x 600
CROPS = {'monitor_1m': (740, 380, 1440, 1080)}  # the monitor: its stand and the keyboard below it
S = 360
try:
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 17)
    small = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 14)
except OSError:
    font = small = ImageFont.load_default()
W, H = 170 + S * len(WAYS), 40 + (S + 10) * len(VIEWS)
out = Image.new('RGB', (W, H), (238, 240, 242))
d = ImageDraw.Draw(out)
for j, (_, label) in enumerate(WAYS):
    d.text((170 + j * S + 8, 10), label, fill=(29, 35, 41), font=font)
for i, (key, label) in enumerate(VIEWS):
    y = 40 + i * (S + 10)
    d.multiline_text((10, y + S // 2 - 30), label.replace(', ', ',\n'), fill=(29, 35, 41), font=font)
    for j, (way, _) in enumerate(WAYS):
        im = Image.open(shots / f'{key}_{way}.png').convert('RGB').crop(CROPS.get(key, CROP)).resize((S, S), Image.LANCZOS)
        out.paste(im, (170 + j * S, y))
        t = TRIS['monitor' if key.startswith('monitor') else 'chair'][j] + ' triangles'
        d.rectangle((170 + j * S + 6, y + S - 26, 170 + j * S + 12 + int(d.textlength(t, font=small)), y + S - 6), fill=(255, 255, 255))
        d.text((170 + j * S + 9, y + S - 25), t, fill=(29, 35, 41), font=small)
out.save(HERE / 'slimmed_closeup.png', optimize=True)
print('slimmed_closeup.png', out.size)
