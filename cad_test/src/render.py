import ezdxf, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ezdxf import recover
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy

doc, _ = recover.readfile('plan.dxf')
msp = doc.modelspace()

CATS = [
  ('wall',      '#d62728', ('WALL','WALL-GL','A-WALL','COL','STRUCTURE')),
  ('door',      '#1f5fd6', ('DOOR','D-JAMB','A-DOOR','I-DOOR')),
  ('window',    '#17becf', ('WIN','W_GRILL','A_GRILL')),
  ('stair',     '#2ca02c', ('STAIR',)),
  ('furniture', '#ff7f0e', ('FUR','FIXT','I-FURN','BOFFI','PIA1-FUR','WC-')),
  ('text/dims', '#7f7f7f', ('TEXT','RNAME','DIM','SPEC','GRID','NORTH','ELEV','SECTION')),
]
def category(layer):
    L = layer.upper()
    for name, col, keys in CATS:
        if any(k in L for k in keys): return name, col
    return 'other', '#c8c8c8'

def render(fname, mode):
    fig = plt.figure(figsize=(40, 20), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor('white')
    ctx = RenderContext(doc)
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE,
                        color_policy=ColorPolicy.BLACK if mode == 'pdf' else ColorPolicy.COLOR)
    fe = Frontend(ctx, MatplotlibBackend(ax), config=cfg)
    if mode == 'cat':
        def override(entity, props):
            props.color = category(props.layer)[1]
        fe.push_property_override_function(override)
    fe.draw_layout(msp, finalize=True)
    fig.savefig(fname, dpi=100, facecolor='white'); plt.close(fig)
    print('saved', fname)

for f, m in (('render_cad.png','cad'), ('render_categories.png','cat'), ('render_pdf_like.png','pdf')):
    render(f, m)
