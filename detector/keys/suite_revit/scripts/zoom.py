"""Close-up pictures of named boxes, drawn like the tiles (draw_pictures.py), for checking how things are drawn.

  python -B zoom.py <prims.pkl> <out folder> name:x0,y0,x1,y1 [name:x0,y0,x1,y1 ...] [--only LAYER,LAYER] [--grid G]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import draw_pictures as dp

args = sys.argv[1:]
only = None
grid, minor = 0.5, 0.1
if '--only' in args:
    i = args.index('--only'); only = set(args[i + 1].split(',')); del args[i:i + 2]
if '--grid' in args:
    i = args.index('--grid'); grid = float(args[i + 1]); minor = grid / 5; del args[i:i + 2]
pkl, outdir = args[0], Path(args[1])
outdir.mkdir(parents=True, exist_ok=True)
D = dp.load(pkl)
items = D['items']
labels = dp.block_labels(items)
for spec in args[2:]:
    name, box = spec.split(':')
    box = tuple(float(v) for v in box.split(','))
    out = outdir / f'{name}.png'
    dp.draw(items, labels, box, out, px=1600, grid=grid, minor=minor, layers=only,
            title=f'{name}: x {box[0]:g} to {box[2]:g}, y {box[1]:g} to {box[3]:g} (drawing metres)', label_blocks='all')
    print(out)
