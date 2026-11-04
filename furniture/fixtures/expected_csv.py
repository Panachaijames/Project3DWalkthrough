"""The family list (furniture/README.md, "The family list (CSV, for the 3D team)") written straight from the contract, with
Python's own number formatting and csv writer, so test_boxes.mjs can compare the viewer's csv() with it byte for byte.
Usage: python expected_csv.py <model.json> [heights.json] [--kit]
  heights.json: {"<kind key>": mm}, the heights typed in.  --kit: print what the builders' writer, furniture_kit.csv_text, gives
  for the same data instead (needs shapely, which furniture_kit imports).
Prints the text on stdout as UTF-8, no byte-order mark (the download adds it).
Rounding the README leaves open, settled as furniture_kit.csv_text has it: whole mm round half up (floor(v + 0.5), like JavaScript's
Math.round); x_m, y_m and rotation_deg use f'{v:.nf}' (an exact tie such as 12.25 to one decimal goes to the even digit)."""
import csv, io, json, math, sys
from pathlib import Path

COLUMNS = ['id', 'level', 'kind', 'kind_label', 'family', 'block', 'layer', 'dxf_handle', 'x_m', 'y_m', 'width_mm', 'depth_mm',
           'height_mm', 'base_mm', 'rotation_deg', 'on_top_of', 'merged', 'note']


def fixed(v, places):
    s = f'{v:.{places}f}'
    return s[1:] if s.startswith('-') and not any(c in '123456789' for c in s) else s      # never -0.000


def whole(v):
    return math.floor(v + 0.5)


def csv_text(model, heights=None):
    heights = heights or {}
    kinds = {k['key']: dict(k, height=whole(heights.get(k['key'], k['height']))) for k in model['furnitureKinds']}
    pieces = {p['id']: p for p in model['furniture']}
    off = model.get('offset', [0, 0])

    def underside(p):                                  # mm: the top of the piece it stands on, else the kind's base
        s = pieces.get(p['on']) if p.get('on') else None
        return underside(s) + kinds[s['kind']]['height'] if s else kinds[p['kind']]['base']

    floors = [f['key'] for f in model['floors']]
    kind_order = {k['key']: i for i, k in enumerate(model['furnitureKinds'])}
    rows = sorted(model['furniture'], key=lambda p: (floors.index(p['floor']), kind_order[p['kind']], p['id']))
    out = io.StringIO()
    w = csv.writer(out, lineterminator='\r\n')
    w.writerow(COLUMNS)
    for p in rows:
        k = kinds[p['kind']]
        w.writerow([p['id'], p['floor'], p['kind'], k['label'], p['family'], p['block'], p['layer'], p['handle'],
                    fixed(p['x'] + off[0], 3), fixed(p['y'] + off[1], 3), whole(p['w'] * 1000), whole(p['d'] * 1000),
                    k['height'], whole(underside(p)), fixed(p['rot'], 1), p.get('on') or '', p.get('n', 1), p.get('note') or ''])
    return out.getvalue()


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    model = json.load(open(args[0], encoding='utf-8'))
    heights = json.load(open(args[1], encoding='utf-8')) if len(args) > 1 else None
    if '--kit' in sys.argv:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import furniture_kit
        text = furniture_kit.csv_text(model['furniture'], model['furnitureKinds'], model['floors'], model.get('offset', [0, 0]), heights)
    else:
        text = csv_text(model, heights)
    sys.stdout.buffer.write(text.encode('utf-8'))
