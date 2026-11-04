"""The offline single HTML (DESIGN.md 16, 17.3): assembly (each marker exactly once, else an error; the stamp first, then a
split, never a replace over the payload), the payload (the stored files' text, pictures in floor order, '<' escaped), the
escaping corpus (drawing names with </script><script>alert(1)</script>, $', $&, $`, $$, __WTV_DATA__ and __WTV_STAMP__
stay inside the JSON and parse back equal), and byte equality with packages/viewer/scripts/make-offline.mjs: skipped
while the Node script or the built template is missing (or the script is the scaffold's stub that writes nothing), but
FAILING instead when WT_INTEGRATION=1."""
from __future__ import annotations

import base64
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from kit import APP, FIXTURES, TEMPLATE, read_json
from walkthrough_api import builtmodel
from walkthrough_api.jsonio import dumps_compact, dumps_pretty
from walkthrough_api.offline import (DATA_MARKER, STAMP_MARKER, OfflineTemplateError, assemble, build_payload, check_template,
                                     escape_payload, offline_html, payload_text)
from walkthrough_api.store.base import NewProject, StoreError, VersionDraft
from walkthrough_api.store.local import LocalStore

CORPUS = ['</script><script>alert(1)</script>', "$'", '$&', '$`', '$$', DATA_MARKER, STAMP_MARKER, '<!--', ']]>', ' ']
NODE_SCRIPT = APP / 'packages' / 'viewer' / 'scripts' / 'make-offline.mjs'
BUILT_TEMPLATE = APP / 'dist' / 'offline-template' / 'viewer-template.html'
INTEGRATION = os.environ.get('WT_INTEGRATION') == '1'


def data_of(page: str) -> str:
    """The text of <script type="application/json" id="wtv-data"> as a browser finds it: up to the first </script."""
    start = page.index('id="wtv-data">') + len('id="wtv-data">')
    return page[start:page.index('</script', start)]


# ---------------------------------------------------------------------------------------------------- assembly
def test_markers_exactly_once() -> None:
    check_template(TEMPLATE)
    for bad in (TEMPLATE.replace(DATA_MARKER, ''), TEMPLATE.replace(STAMP_MARKER, ''), TEMPLATE + DATA_MARKER,
                TEMPLATE + STAMP_MARKER, ''):
        with pytest.raises(OfflineTemplateError):
            assemble(bad, '0123456789ab', '{}')
    for stamp in ('', '0123456789AB', '__WTV_DATA__', '0123456789abc'):
        with pytest.raises(ValueError):
            assemble(TEMPLATE, stamp, '{}')


def test_stamp_first_then_split() -> None:
    payload = '{"a":"__WTV_STAMP__ __WTV_DATA__ $\' $& $` $$"}'
    out = assemble(TEMPLATE, '0123456789ab', payload)
    head, tail = TEMPLATE.replace(STAMP_MARKER, '0123456789ab').split(DATA_MARKER)
    assert out == head + payload + tail
    assert out.count('0123456789ab') == 1 and '<meta name="model-data" content="0123456789ab">' in out
    assert "/* $' $& $` $$ */" in out                                        # the template's own tail, untouched


def test_escape_payload() -> None:
    raw = '{"x":"</script><!-- <b>"}'
    esc = escape_payload(raw)
    assert '<' not in esc and json.loads(esc) == json.loads(raw)


def test_payload_is_plain_concatenation() -> None:
    text = payload_text('{"m":1}\n', '{"v":2}\n', '{"model":3}\n', None, [('F1', 'image/png', b'\x89PNG')], None)
    assert text == ('{"format":"walkthrough-offline/1","project":{"m":1}\n,"version":{"v":2}\n,"model":{"model":3}\n,'
                    '"stages":null,"pictures":{"F1":"data:image/png;base64,iVBORw=="},"overrides":null}')
    assert json.loads(text)['pictures'] == {'F1': 'data:image/png;base64,iVBORw=='}


# ---------------------------------------------------------------------------------------------------- from a store
def parse_page(page: str) -> dict:
    data = data_of(page)
    assert '<' not in data
    return json.loads(data)


@pytest.mark.parametrize('project_id, n', [('hotel-lobby', 1), ('sukhumvit-house', 1), ('bank-sampeng', 1)])
def test_payload_from_the_seeded_store(seeded, project_id, n) -> None:
    store = LocalStore(seeded)
    page = offline_html(store, project_id, n, TEMPLATE)
    d = seeded / 'projects' / project_id / 'versions' / str(n)
    p = parse_page(page)
    assert set(p) == {'format', 'project', 'version', 'model', 'stages', 'pictures', 'overrides'}
    assert p['format'] == 'walkthrough-offline/1'
    assert p['project'] == read_json(d.parent.parent / 'meta.json') and p['version'] == read_json(d / 'version.json')
    assert p['model'] == read_json(d / 'model.json') and p['overrides'] is None
    assert p['stages'] == (read_json(d / 'stages.json') if (d / 'stages.json').exists() else None)
    version = read_json(d / 'version.json')
    pics = [(a['floor'], a['name']) for a in version['assets'] if a['role'] == 'plan-picture']
    assert list(p['pictures']) == [f for f, _ in pics]                         # model floor order
    for floor, name in pics:
        assert p['pictures'][floor] == 'data:image/png;base64,' + base64.b64encode((d / 'assets' / name).read_bytes()).decode()
    assert f'content="{version["stamp"]}"' in page
    stamp, payload = build_payload(store, project_id, n)
    assert stamp == version['stamp'] and page == assemble(TEMPLATE, stamp, payload)
    raw = ('{"format":"walkthrough-offline/1","project":' + (d.parent.parent / 'meta.json').read_text(encoding='utf-8', newline='')
           + ',"version":' + (d / 'version.json').read_text(encoding='utf-8', newline=''))
    assert payload.startswith(escape_payload(raw))                            # each file's text as stored, newline kept


def test_a_broken_store_file_is_refused_not_embedded(data_copy) -> None:
    """Each embedded file must be strict JSON (UTF-8, no BOM) as make-offline.mjs requires; the raw text is what goes in."""
    store = LocalStore(data_copy)
    d = data_copy / 'projects' / 'bank-sampeng' / 'versions' / '2'
    (d / 'overrides.json').write_bytes(b'{"heights": {"table": 600},')
    with pytest.raises(StoreError, match='bank-sampeng v2 overrides.json is not strict JSON'):
        build_payload(store, 'bank-sampeng', 2)
    (d / 'overrides.json').unlink()
    (d / 'stages.json').write_bytes(b'\xef\xbb\xbf' + (d / 'stages.json').read_bytes())
    with pytest.raises(StoreError, match='stages.json is not strict JSON .*byte-order mark'):
        build_payload(store, 'bank-sampeng', 2)


def test_saved_heights_go_in(data_copy) -> None:
    store = LocalStore(data_copy)
    saved = store.write_overrides('bank-sampeng', 2, {'table': 640})
    p = parse_page(offline_html(store, 'bank-sampeng', 2, TEMPLATE))
    assert p['overrides'] == saved.to_json()


def corpus_model() -> dict:
    """The bank's v2 model with the corpus in every drawing name (rooms, families, blocks, layers, notes, labels)."""
    m = copy.deepcopy(read_json(FIXTURES / 'models' / 'bank-v2.model.json'))
    for i, r in enumerate(m['rooms'][:len(CORPUS)]):
        r['label'] = f'room {CORPUS[i]} end'
        r['name'] = CORPUS[i]
    for i, p in enumerate(m['furniture'][:len(CORPUS)]):
        p['family'] = CORPUS[i]
        p['block'] = 'block ' + CORPUS[i]
        p['layer'] = CORPUS[(i + 1) % len(CORPUS)]
        p['note'] = CORPUS[(i + 2) % len(CORPUS)]
    m['project'] = 'Corpus ' + ' '.join(CORPUS)
    builtmodel.validate(m)
    return m


@pytest.fixture
def corpus_store(tmp_path) -> LocalStore:
    store = LocalStore(tmp_path / 'data')
    store.create_project(NewProject(id='corpus', name='Corpus ' + ''.join(CORPUS), short_name='$& corpus', source_kind='cad'))
    pres = copy.deepcopy(read_json(FIXTURES / 'presentation' / 'bank-sampeng-v2.json'))
    pres['heading'] = 'Heading ' + ' '.join(CORPUS)
    pres['intro'] = [{'text': t} for t in CORPUS]
    stages = copy.deepcopy(read_json(FIXTURES / 'stages' / 'bank-v2.stages.json'))
    stages['layers'] = [[c, c] for c in CORPUS]
    stages['captions']['read'] = ' '.join(CORPUS)
    store.create_version('corpus', VersionDraft(label='corpus ' + CORPUS[0], source_kind='cad', source_files=CORPUS,
                                                model_json=dumps_compact(corpus_model()), stages_json=dumps_compact(stages),
                                                presentation=pres))
    store.write_overrides('corpus', 1, {'table': 600})
    return store


def test_corpus_stays_inside_the_json(corpus_store: LocalStore) -> None:
    page = offline_html(corpus_store, 'corpus', 1, TEMPLATE)
    head, tail = TEMPLATE.replace(STAMP_MARKER, corpus_store.get_version('corpus', 1).stamp).split(DATA_MARKER)
    assert page.startswith(head) and page.endswith(tail)
    data = page[len(head):len(page) - len(tail)]
    assert data_of(page) == data                                              # nothing closes the data element early
    assert '<' not in data and '</script' not in data.lower() and '<!--' not in data
    p = json.loads(data)
    d = corpus_store.version_dir('corpus', 1)
    assert p['model'] == read_json(d / 'model.json') and p['stages'] == read_json(d / 'stages.json')
    assert p['project'] == read_json(d.parent.parent / 'meta.json') and p['version'] == read_json(d / 'version.json')
    assert p['overrides']['heights'] == {'table': 600}
    families = [f['family'] for f in p['model']['furniture'][:len(CORPUS)]]
    assert families == CORPUS                                                 # every pattern and marker text as written
    assert p['version']['presentation']['heading'] == 'Heading ' + ' '.join(CORPUS)
    assert page.count(STAMP_MARKER) == data.count(STAMP_MARKER) and page.count(DATA_MARKER) == data.count(DATA_MARKER)


# ---------------------------------------------------------------------------------------------------- Node == Python
def run_node(data: Path, template: Path, out: Path) -> subprocess.CompletedProcess:
    node = shutil.which('node')
    if node is None:
        pytest.fail('node is not on PATH') if INTEGRATION else pytest.skip('node is not on PATH')
    return subprocess.run([node, str(NODE_SCRIPT), '--data', str(data), '--template', str(template), '--out', str(out)],
                          capture_output=True, timeout=600, cwd=APP)


def missing(reason: str) -> None:
    if INTEGRATION:
        pytest.fail(f'{reason} (WT_INTEGRATION=1: the byte-equality check must run)')
    pytest.skip(reason)


def compare_with_node(store: LocalStore, template: Path, out: Path) -> list[str]:
    if not NODE_SCRIPT.is_file():
        missing(f'{NODE_SCRIPT} is missing')
    if out.exists():
        shutil.rmtree(out)
    r = run_node(store.root, template, out)
    assert r.returncode == 0, (r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace'))
    written = sorted(p.name for p in out.glob('*.html')) if out.is_dir() else []
    if not written:
        missing('make-offline.mjs wrote nothing (still the scaffold stub?): ' + r.stdout.decode('utf-8', 'replace').strip())
    text = template.read_bytes().decode('utf-8')
    want = [f'{p.id}-v{n}.html' for p in store.list_projects() for n in p.versions]
    assert written == sorted(want)
    for p in store.list_projects():
        for n in p.versions:
            node_bytes = (out / f'{p.id}-v{n}.html').read_bytes()
            python_bytes = offline_html(store, p.id, n, text).encode('utf-8')
            assert node_bytes == python_bytes, f'{p.id} v{n}: Node and Python differ'
    return written


def test_a_missing_piece_skips_alone_and_fails_at_integration(monkeypatch) -> None:
    """The switch the byte-equality checks use: skip while the template or the Node script is missing, but fail instead
    when WT_INTEGRATION=1 (WORK_BREAKDOWN E)."""
    module = sys.modules[__name__]
    monkeypatch.setattr(module, 'INTEGRATION', False)
    with pytest.raises(pytest.skip.Exception):
        missing('no template')
    monkeypatch.setattr(module, 'INTEGRATION', True)
    with pytest.raises(pytest.fail.Exception, match='WT_INTEGRATION=1'):
        missing('no template')


def test_node_and_python_give_the_same_bytes_on_the_corpus(corpus_store: LocalStore, template_file: Path, tmp_path) -> None:
    compare_with_node(corpus_store, template_file, tmp_path / 'out')


def test_node_and_python_give_the_same_bytes_on_the_seeded_store(data_copy, tmp_path) -> None:
    if not BUILT_TEMPLATE.is_file():
        missing(f'{BUILT_TEMPLATE} is missing (npm run build:offline:template)')
    store = LocalStore(data_copy)
    store.write_overrides('bank-sampeng', 2, {'table': 600, 'seat': 300})       # the current heights go in
    template = tmp_path / 'viewer-template.html'
    template.write_bytes(BUILT_TEMPLATE.read_bytes())
    written = compare_with_node(store, template, tmp_path / 'out')
    assert len(written) == 5


def _damage(d: Path, case: str) -> tuple[str, int]:
    """Breaks one store file of a copy of the seeded store; returns the version it belongs to."""
    bank, hotel = d / 'projects' / 'bank-sampeng' / 'versions' / '2', d / 'projects' / 'hotel-lobby' / 'versions' / '1'
    if case == 'version.json repeats a key':
        raw = (bank / 'version.json').read_bytes()
        (bank / 'version.json').write_bytes(raw.replace(b'{\n', b'{\n  "label": "twice",\n', 1))
    elif case == 'model.json is not UTF-8':
        (bank / 'model.json').write_bytes((bank / 'model.json').read_bytes().replace(b'"photoName"', b'"photo\xffName"', 1))
    elif case == 'model.json changed on disk':
        (bank / 'model.json').write_bytes((bank / 'model.json').read_bytes() + b' ')
    elif case == 'overrides.json has NaN':
        (bank / 'overrides.json').write_bytes(b'{"format":"walkthrough-overrides/1","heights":{"table":NaN},"revision":1,'
                                              b'"updatedAt":"2026-11-03T00:00:00Z"}\n')
    elif case == 'meta.json starts with a BOM':
        meta = d / 'projects' / 'bank-sampeng' / 'meta.json'
        meta.write_bytes(b'\xef\xbb\xbf' + meta.read_bytes())
    elif case == 'a plan picture media type is not a media type':
        raw = (hotel / 'version.json').read_bytes()
        assert b'"mediaType": "image/png"' in raw
        (hotel / 'version.json').write_bytes(raw.replace(b'"mediaType": "image/png"', b'"mediaType": "image/png\\"x"', 1))
        return 'hotel-lobby', 1
    else:
        raise AssertionError(case)
    return 'bank-sampeng', 2


@pytest.mark.parametrize('case', ['version.json repeats a key', 'model.json is not UTF-8', 'model.json changed on disk',
                                  'overrides.json has NaN', 'meta.json starts with a BOM',
                                  'a plan picture media type is not a media type'])
def test_node_and_python_refuse_the_same_broken_files(case: str, data_copy: Path, tmp_path: Path) -> None:
    """Byte equality holds for every store file either side accepts: a file one refuses, the other refuses too (fix step,
    first code review finding 16: Python wrote a page whose payload did not parse for a bad media type; Node took
    repeated keys, bad UTF-8 and a model changed on disk)."""
    if not NODE_SCRIPT.is_file():
        missing(f'{NODE_SCRIPT} is missing')
    project_id, n = _damage(data_copy, case)
    with pytest.raises(StoreError):
        offline_html(LocalStore(data_copy), project_id, n, TEMPLATE)
    template = tmp_path / 'template.html'
    template.write_text(TEMPLATE, encoding='utf-8', newline='')
    node = shutil.which('node') or pytest.fail('node is not on PATH')
    r = subprocess.run([node, str(NODE_SCRIPT), '--data', str(data_copy), '--template', str(template), '--out',
                        str(tmp_path / 'out'), '--project', project_id, '--version', str(n)], capture_output=True, timeout=600, cwd=APP)
    assert r.returncode == 1, (case, r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace'))
    assert not (tmp_path / 'out' / f'{project_id}-v{n}.html').exists()


def test_built_template_has_each_marker_once() -> None:
    if not BUILT_TEMPLATE.is_file():
        missing(f'{BUILT_TEMPLATE} is missing (npm run build:offline:template)')
    check_template(BUILT_TEMPLATE.read_bytes().decode('utf-8'))


def test_dumps_pretty_is_what_meta_and_version_use(seeded) -> None:
    meta = seeded / 'projects' / 'bank-sampeng' / 'meta.json'
    assert meta.read_bytes() == dumps_pretty(read_json(meta))
