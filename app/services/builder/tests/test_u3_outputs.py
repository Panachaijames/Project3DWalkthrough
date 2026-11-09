"""U3: every model the builder makes is one the API accepts (docs/upload/DESIGN.md U-3.2, U-10.8, U-10.9, U-11.5).

When a build run is done the API checks its outputs (`builtmodel.validate_bytes`: the model schema and the D-5.6 rules;
the replay and the presentation against the model; the sidecar records) and marks the run `invalid_output` on any
problem; U4's Max generator refuses a part it cannot extrude. So the builder's results go through U4's
`contracts.write_outputs` and the API's own checker (`node tools/run-py.mjs -m walkthrough_api.check_file`, the API's
Python) here: the synthetic plans with one and three floors (the real detector), the extras (a parapet, glass standing
alone), a plan where nothing opens onto the room (no floor plate inside: every glass probe left out) and ACCEPTANCE
A-7's hostile drawing. The four acceptance drawings go the same way in test_u3_bank.py and test_u3_drawings.py (heavy).
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess

import pytest

import kit
from test_u3_helpers import (fake_detector, plan_dxf, plan_records, plan_settings, read_plan, run_build,  # noqa: F401
                             settings, source_ctx, write_and_check)

SHA = ['a' * 40, 'b' * 40, 'c' * 40]


@pytest.fixture(scope='module')
def plan(tmp_path_factory):
    d = tmp_path_factory.mktemp('u3out')
    return {name: read_plan(plan_dxf(d / f'{name}.dxf', **kw), d / name)
            for name, kw in (('base', {}), ('moved', {'dx': 5000.0}), ('extras', {'parapet': True, 'free_glass': True}))}


def src(plan, which='base', sha=SHA[0]):
    return source_ctx(sha, f'{which}.dxf', plan[which]['items'], drawing=plan[which]['drawing'], kind='dxf')


def _ok(res, s, srcs, tmp):
    written, problems = write_and_check(res, s, srcs, tmp)
    assert problems == []
    mb = written['model.json'].read_bytes()
    assert written['model.json'].name == 'model.json' and not mb.endswith(b'\n')
    stamp = hashlib.sha1(mb).hexdigest()[:12]
    ms = written[s['project']['maxFileName']].read_bytes().split(b'\r\n')[1]
    assert stamp.encode() in ms                                                  # the .ms line 2 names this model
    return written


def test_one_and_three_floors_with_the_real_detector(plan, scratch):
    s = plan_settings([SHA[0]])
    res, _ = run_build(s, [src(plan)], scratch / 'one')
    _ok(res, s, [src(plan)], scratch / 'one-out')
    s = plan_settings(SHA, levels=[0.0, 3.0, 6.5], heights=[3.0, 3.5, 3.2])
    srcs = [src(plan, 'base', SHA[0]), src(plan, 'base', SHA[1]), src(plan, 'moved', SHA[2])]
    res, _ = run_build(s, srcs, scratch / 'three')
    assert res['model']['floors'][2]['sheetShift'] == [5.0, 0.0]
    _ok(res, s, srcs, scratch / 'three-out')


HOSTILE_LAYERS = {'A-WALL': 'A-WALL<img src=x onerror=alert(1)>', 'A-DOOR': "A-DOOR</script><script>alert(2)</script>",
                  'I-FURN': "I-FURN $' $& &amp", 'A-GLAZ': "A-GLAZ $' &amp; $&"}


def test_the_hostile_drawing_builds_with_its_names_as_text(scratch):
    """ACCEPTANCE A-7's hostile DXF (tools/upload/make-test-dxf.py: layer, block and text names carrying markup, `$'`
    and `&amp;`), read by the provisional reader, built with the small drawing's roles on its hostile layer names: the
    names reach the model as they are (plain text: the screens and the viewer show them with textContent) and every
    output passes the API's checks (the Max script makes its own ASCII names, U-11.5)."""
    dxf = scratch / 'hostile.dxf'
    subprocess.run([shutil.which('node') or 'node', str(kit.APP / 'tools' / 'run-builder-py.mjs'),
                    'tools/upload/make-test-dxf.py', 'hostile', str(dxf)], cwd=kit.APP, check=True, capture_output=True,
                   stdin=subprocess.DEVNULL)
    sha = hashlib.sha1(dxf.read_bytes()).hexdigest()
    rd = read_plan(dxf, scratch / 'read')
    s = settings('small')
    s['sources'][0].update(sha1=sha, name='hostile <b>.dxf')
    s['floors'][0]['source'] = sha
    s['layers'] = {HOSTILE_LAYERS.get(k, k): v for k, v in s['layers'].items()}
    s['project'].update(name="Hostile <img src=x onerror=alert(9)> & Co $'", shortName='</script>')
    srcs = [source_ctx(sha, 'hostile <b>.dxf', rd['items'], drawing=rd['drawing'], kind='dxf')]
    res, _ = run_build(s, srcs, scratch / 'build', 'proj')
    m = res['model']
    assert m['project'] == "Hostile <img src=x onerror=alert(9)> & Co $'" and m['source'] == ['hostile <b>.dxf']
    assert {r['name'] for r in m['rooms']} == {'<img src=x onerror=alert(4)>LOBBY', "OFFICE</script>$'&amp;"}
    assert {f['family'] for f in m['furniture']} == {'Desk<img src=x onerror=alert(3)> 1600x800', "Chair</script>$'"}
    assert {o['kind'] for o in m['openings']} == {'door', 'window'}
    _ok(res, s, srcs, scratch / 'out')


def test_extras_and_a_plan_with_no_floor_inside(plan, scratch, fake_detector):
    fake_detector({'F1': plan_records()})
    s = plan_settings([SHA[0]], heights=[3.5])
    res, _ = run_build(s, [src(plan, 'extras')], scratch / 'extras')
    kinds = {p['kind'] for p in res['model']['parts']}
    assert {'parapet', 'railing', 'sill', 'lintel', 'glass', 'slab'} <= kinds
    _ok(res, s, [src(plan, 'extras')], scratch / 'extras-out')
    fake_detector({'F1': []})                                   # nothing opens onto the room: no plate inside the walls
    res, logs = run_build(s, [src(plan, 'extras')], scratch / 'closed')
    assert res['model']['probes'] == [] and any('glass probe(s) with no floor on either side left out' in m for m in logs)
    _ok(res, s, [src(plan, 'extras')], scratch / 'closed-out')
