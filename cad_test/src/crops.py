import json, sys, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ezdxf import recover
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy
exec(open('render.py').read().split("doc, _ = recover.readfile")[0])  # imports only
CATS = [
  ('wall',      '#d62728', ('WALL','WALL-GL','A-WALL','STRUCTURE')),
  ('column',    '#8c1a1a', ('COL',)),
  ('door',      '#1f5fd6', ('DOOR','D-JAMB','A-DOOR','I-DOOR')),
  ('window',    '#17becf', ('WIN','W_GRILL','A_GRILL')),
  ('stair',     '#2ca02c', ('STAIR',)),
  ('furniture', '#ff7f0e', ('FUR','FIXT','I-FURN','BOFFI','PIA1-FUR','WC-')),
  ('annotation','#9e9e9e', ('TEXT','RNAME','DIM','SPEC','GRID','NORTH','ELEV','SECTION')),
]
def category(layer):
    L = layer.upper()
    if L.endswith('COLCL'): return '#9e9e9e'
    for name, col, keys in CATS:
        if any(k in L for k in keys): return col
    return '#bdbdbd' if L != '0' else '#9467bd'   # layer 0 in purple so it stands out
doc, _ = recover.readfile('plan.dxf'); msp = doc.modelspace()
regions = json.load(open('regions.json'))
def render(region, mode, fname, pad=1500):
    x0,y0,x1,y1 = regions[region]
    w, h = x1-x0+2*pad, y1-y0+2*pad
    fig = plt.figure(figsize=(16, 16*h/w), dpi=110)
    ax = fig.add_axes([0,0,1,1])
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE,
                        color_policy=ColorPolicy.BLACK if mode=='pdf' else ColorPolicy.COLOR,
                        min_lineweight=0.12)
    fe = Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg)
    if mode == 'cat':
        fe.push_property_override_function(lambda e, p: setattr(p, 'color', category(p.layer)))
    fe.draw_layout(msp, finalize=True)
    ax.set_xlim(x0-pad, x1+pad); ax.set_ylim(y0-pad, y1+pad)
    fig.savefig(fname, dpi=110, facecolor='white'); plt.close(fig); print('saved', fname)
render('plan_left',  'cat', 'ground_categories.png')
render('plan_left',  'pdf', 'ground_pdf_like.png')
render('plan_right', 'cat', 'upper_categories.png')
render('plan_right', 'pdf', 'upper_pdf_like.png')
