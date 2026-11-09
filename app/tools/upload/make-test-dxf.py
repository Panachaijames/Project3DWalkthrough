"""Synthetic test drawings for the upload milestone (WORK_BREAKDOWN U0 step 7; ACCEPTANCE 2.5, A-7).

    node tools/run-builder-py.mjs tools/upload/make-test-dxf.py small|hostile <out.dxf>

Deterministic (ezdxf 1.4.4 with its fixed meta data: the same bytes on every run), DXF R2013, millimetres
($INSUNITS 4). The root .gitignore ignores *.dxf, so tests make them at test time (into their WT_TMP).

`small`: two rooms side by side (0 - 10 m x 0 - 4 m), 200 mm walls:
  * fills: solid hatches on A-WALL-PATT with their closed outlines on A-WALL (south, west and north-east walls, the
    partition), and paired faces: two parallel A-WALL lines 200 mm apart (the east wall, the north wall of room A);
  * a door in the partition (A-DOOR): a quarter arc of 900 mm about its hinge and the leaf line from the hinge;
  * a window in room A's north wall (A-GLAZ): two lines 20 mm apart across the 1.5 m gap;
  * a railing (A-FLOR-HRAL): two lines 50 mm apart in room B;
  * a stair (S-STRS): eight treads in room A;
  * two furniture blocks on I-FURN: 'Desk 1600x800' (inserted once) and 'FurnGroup', a group block holding the Revit
    style 'Chair-Mollie-1234567-Level 1' twice (one mirrored), so INSERTs nest two deep;
  * room names (A-AREA-IDEN): LOBBY, OFFICE;
  * grid lines (S-GRID) with their bubbles and labels 1, 2, A, B (S-GRID-IDEN).
`hostile`: the same drawing with the names of ACCEPTANCE A-7 in layer, block and text names (<img src=x onerror=...>,
  </script>, $', &amp;): written with placeholders, which are then replaced in the file's text (ezdxf refuses such
  names when it writes; a real drawing can carry them, and readers must treat them as text). ezdxf 1.4.4 READS them on
  line work, block names and texts, but not on an INSERT's own layer (it adds a SEQEND to the INSERT and validates that
  layer name: '<', '>', ';' and the like raise DXFValueError), so the INSERTs' layer carries only $' and &amp.
The file name is the caller's (a test picks a hostile one where the file system allows it).
The OBJECTS section's order follows Python's string hashing, so the tool runs itself again with PYTHONHASHSEED=0 when it
is not set: the same bytes on every run.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

import ezdxf
from ezdxf import units

#: placeholder -> hostile text (ACCEPTANCE A-7). Placeholders are unique strings that appear nowhere else in the file.
HOSTILE = {
    'HOSTILEWALLLAYER': 'A-WALL<img src=x onerror=alert(1)>',
    'HOSTILEDOORLAYER': "A-DOOR</script><script>alert(2)</script>",
    'HOSTILEFURNLAYER': "I-FURN $' $& &amp",                     # an INSERT's layer: see the module text
    'HOSTILEGLAZLAYER': "A-GLAZ $' &amp; $&",
    'HOSTILEDESKBLOCK': 'Desk<img src=x onerror=alert(3)> 1600x800',
    'HOSTILECHAIRBLOCK': "Chair</script>$'-1234567-Level 1",
    'HOSTILEROOMONE': '<img src=x onerror=alert(4)>LOBBY',
    'HOSTILEROOMTWO': "OFFICE</script>$'&amp;",
}


def names(hostile: bool) -> dict[str, str]:
    if hostile:
        return {'wall': 'HOSTILEWALLLAYER', 'door': 'HOSTILEDOORLAYER', 'furn': 'HOSTILEFURNLAYER', 'glaz': 'HOSTILEGLAZLAYER',
                'desk': 'HOSTILEDESKBLOCK', 'chair': 'HOSTILECHAIRBLOCK', 'room1': 'HOSTILEROOMONE',
                'room2': 'HOSTILEROOMTWO'}
    return {'wall': 'A-WALL', 'door': 'A-DOOR', 'furn': 'I-FURN', 'glaz': 'A-GLAZ', 'desk': 'Desk 1600x800',
            'chair': 'Chair-Mollie-1234567-Level 1', 'room1': 'LOBBY', 'room2': 'OFFICE'}


def make(hostile: bool) -> ezdxf.document.Drawing:
    N = names(hostile)
    doc = ezdxf.new('R2013', setup=False)
    doc.units = units.MM
    doc.header['$INSUNITS'] = 4
    doc.header['$MEASUREMENT'] = 1
    for name, colour in ((N['wall'], 7), ('A-WALL-PATT', 8), (N['glaz'], 4), (N['door'], 2), ('A-FLOR-HRAL', 6),
                         ('S-STRS', 3), (N['furn'], 5), ('A-AREA-IDEN', 7), ('S-GRID', 1), ('S-GRID-IDEN', 1)):
        doc.layers.add(name, color=colour)
    msp = doc.modelspace()

    def rect(x0, y0, x1, y1, fill=True):
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        msp.add_lwpolyline(pts, close=True, dxfattribs={'layer': N['wall']})
        if fill:
            h = msp.add_hatch(color=8, dxfattribs={'layer': 'A-WALL-PATT'})
            h.set_solid_fill(color=8)
            h.paths.add_polyline_path(pts, is_closed=True)

    def pair(a, b, offset):
        (x0, y0), (x1, y1) = a, b
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy)
        nx, ny = -dy / n * offset, dx / n * offset
        msp.add_line((x0, y0), (x1, y1), dxfattribs={'layer': N['wall']})
        msp.add_line((x0 + nx, y0 + ny), (x1 + nx, y1 + ny), dxfattribs={'layer': N['wall']})

    # walls: fills with outlines, and paired faces
    rect(0, 0, 10000, 200)                       # south
    rect(0, 200, 200, 3800)                      # west
    rect(6000, 3800, 10000, 4000)                # north of room B
    rect(5900, 200, 6100, 1000)                  # partition, below the door
    rect(5900, 1900, 6100, 3800)                 # partition, above the door
    pair((10000, 200), (10000, 3800), 200)       # east: faces at x 10000 and 9800 (the pair's normal points -x)
    pair((0, 4000), (2000, 4000), 200)           # north of room A, west of the window: faces at y 4000 and 3800
    pair((3500, 4000), (6000, 4000), 200)        # ... east of the window
    msp.add_line((0, 3800), (0, 4000), dxfattribs={'layer': N['wall']})          # corner caps
    msp.add_line((10000, 3800), (10000, 4000), dxfattribs={'layer': N['wall']})

    # the door: hinge (6000, 1000), leaf open along +x, arc from the open tip to the closed tip (6000, 1900)
    msp.add_arc((6000, 1000), 900, 0, 90, dxfattribs={'layer': N['door']})
    msp.add_line((6000, 1000), (6900, 1000), dxfattribs={'layer': N['door']})

    # the window: two glass lines 20 mm apart across the gap 2000 - 3500 of room A's north wall, and its jamb lines
    msp.add_line((2000, 3890), (3500, 3890), dxfattribs={'layer': N['glaz']})
    msp.add_line((2000, 3910), (3500, 3910), dxfattribs={'layer': N['glaz']})
    msp.add_line((2000, 3800), (2000, 4000), dxfattribs={'layer': N['glaz']})
    msp.add_line((3500, 3800), (3500, 4000), dxfattribs={'layer': N['glaz']})

    # a railing in room B
    msp.add_line((8000, 2500), (9500, 2500), dxfattribs={'layer': 'A-FLOR-HRAL'})
    msp.add_line((8000, 2550), (9500, 2550), dxfattribs={'layer': 'A-FLOR-HRAL'})

    # a stair in room A: eight treads 280 mm apart, 1 m wide, and its side lines
    for i in range(8):
        y = 600 + 280 * i
        msp.add_line((600, y), (1600, y), dxfattribs={'layer': 'S-STRS'})
    msp.add_line((600, 600), (600, 600 + 280 * 7), dxfattribs={'layer': 'S-STRS'})
    msp.add_line((1600, 600), (1600, 600 + 280 * 7), dxfattribs={'layer': 'S-STRS'})

    # furniture: a desk, and a group of two chairs (one mirrored) inside a block
    desk = doc.blocks.new(N['desk'])
    desk.add_lwpolyline([(0, 0), (1600, 0), (1600, 800), (0, 800)], close=True)
    desk.add_line((100, 100), (1500, 100))
    chair = doc.blocks.new(N['chair'])
    chair.add_lwpolyline([(0, 0), (500, 0), (500, 500), (0, 500)], close=True)
    chair.add_line((0, 450), (500, 450))                                # the back
    chair.add_arc((250, 250), 150, 0, 180)
    group = doc.blocks.new('FurnGroup')
    group.add_blockref(N['chair'], (0, 0))
    group.add_blockref(N['chair'], (1500, 0), dxfattribs={'xscale': -1})  # mirrored
    msp.add_blockref(N['desk'], (2000, 1200), dxfattribs={'layer': N['furn']})
    msp.add_blockref('FurnGroup', (7000, 1500), dxfattribs={'layer': N['furn'], 'rotation': 90})

    # room names
    msp.add_text(N['room1'], height=250, dxfattribs={'layer': 'A-AREA-IDEN'}).set_placement((3000, 2600))
    msp.add_text(N['room2'], height=250, dxfattribs={'layer': 'A-AREA-IDEN'}).set_placement((8000, 3200))

    # grid lines, bubbles and labels
    for x, label in ((0, '1'), (10000, '2')):
        msp.add_line((x, -2000), (x, 6000), dxfattribs={'layer': 'S-GRID'})
        msp.add_circle((x, 6400), 400, dxfattribs={'layer': 'S-GRID-IDEN'})
        msp.add_text(label, height=300, dxfattribs={'layer': 'S-GRID-IDEN'}).set_placement((x, 6400))
    for y, label in ((0, 'A'), (4000, 'B')):
        msp.add_line((-2000, y), (12000, y), dxfattribs={'layer': 'S-GRID'})
        msp.add_circle((-2400, y), 400, dxfattribs={'layer': 'S-GRID-IDEN'})
        msp.add_text(label, height=300, dxfattribs={'layer': 'S-GRID-IDEN'}).set_placement((-2400, y))
    return doc


def write(kind: str, out: Path) -> None:
    ezdxf.options.write_fixed_meta_data_for_testing = True
    hostile = kind == 'hostile'
    doc = make(hostile)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + '.tmp')
    doc.saveas(tmp)
    data = tmp.read_bytes()
    if hostile:
        for placeholder, text in HOSTILE.items():
            assert data.count(placeholder.encode()) > 0, placeholder
            data = data.replace(placeholder.encode(), text.encode('utf-8'))
    tmp.unlink()
    out.write_bytes(data)


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ('small', 'hostile'):
        print('usage: make-test-dxf.py small|hostile <out.dxf>', file=sys.stderr)
        return 2
    if os.environ.get('PYTHONHASHSEED') != '0':
        env = dict(os.environ, PYTHONHASHSEED='0')
        return subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), *argv], env=env).returncode
    write(argv[0], Path(argv[1]))
    print(f'make-test-dxf: {argv[0]} -> {argv[1]}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
