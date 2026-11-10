"""Draw every entry of ../A.json as a green a-b segment with its id (optional ones labelled with o:)."""
import json, subprocess, sys, os
here = os.path.dirname(os.path.abspath(__file__))
A = json.load(open(os.path.join(here, '..', 'A.json'), encoding='utf-8'))
def run(box, out, px):
    args = [sys.executable, '-B', os.path.join(here, 'draw.py')] + [str(v) for v in box] + [out, '--px', str(px), '--grid', '0.5']
    for o in A['openings']:
        lab = ('o:' if o.get('optional') else '') + o['id'][2:]
        args += ['--seg', f"{o['a'][0]},{o['a'][1]},{o['b'][0]},{o['b'][1]},{lab}"]
    subprocess.run(args, check=True, cwd=here)
run((1.4, -0.2, 25.3, 13.3), 'marked_all.png', 3200)
run((1.4, -0.2, 13.4, 13.3), 'marked_west.png', 2600)
run((11.0, -0.2, 25.3, 13.3), 'marked_east.png', 2600)
