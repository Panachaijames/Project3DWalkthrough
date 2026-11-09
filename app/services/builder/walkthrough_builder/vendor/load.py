"""Import the vendored prototype modules by path (docs/upload/DESIGN.md U-10.2).

    from walkthrough_builder.vendor.load import load
    gk = load('geomkit')
    op = load('openings', openings_data=run_tmp)     # OPENINGS_DATA set before openings (and its prims) load

The modules are registered in sys.modules under their plain names (`openings`, `geomkit`, `prims`, `merge_cad`,
`geom`, `furniture_kit`, `furniture_max`), because they import each other that way (`openings.py` does `import prims`
and `from geomkit import *` after putting its own folder and `tools/` on sys.path; the bank builder imports `merge_cad`,
`geom` and `furniture_kit` by name). `sys.dont_write_bytecode` is set first, so no __pycache__ is written beside them.
`prims` reads OPENINGS_DATA once, when it loads, and is never used to build a cache here; it loads only because
`openings.py` imports it. Scaffold U0; frozen after it.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

VENDOR = Path(__file__).resolve().parent

#: plain module name -> file inside vendor/
MODULES: dict[str, str] = {
    'openings': 'openings.py',
    'geomkit': 'geomkit.py',
    'prims': 'tools/prims.py',
    'merge_cad': 'merge_cad.py',
    'geom': 'geom.py',
    'furniture_kit': 'furniture_kit.py',
    'furniture_max': 'furniture_max.py',
}


def manifest() -> dict:
    """VENDOR.json: {format, files: [{path, from, sha1, bytes}]}."""
    return json.loads((VENDOR / 'VENDOR.json').read_text(encoding='utf-8'))


def path_of(name: str) -> Path:
    if name not in MODULES:
        raise KeyError(f'no vendored module {name!r} (have {", ".join(MODULES)})')
    return VENDOR / MODULES[name]


def check(name: str) -> None:
    """Raises when the vendored file differs from its VENDOR.json sha1."""
    rel = MODULES[name]
    row = next((f for f in manifest()['files'] if f['path'] == rel), None)
    if row is None:
        raise RuntimeError(f'{rel} is not listed in VENDOR.json')
    got = hashlib.sha1(path_of(name).read_bytes()).hexdigest()
    if got != row['sha1']:
        raise RuntimeError(f'vendored {rel} has sha1 {got}, VENDOR.json says {row["sha1"]}: copied in by hand?')


def load(name: str, *, openings_data: Path | str | None = None) -> ModuleType:
    """The vendored module `name`, imported by path once per process (later calls return the same module).
    `openings` (and `prims`) need `openings_data` (a folder of the run's own, e.g. out/tmp/) unless OPENINGS_DATA is
    already set; it is set in the environment before they load."""
    sys.dont_write_bytecode = True
    if name in sys.modules and getattr(sys.modules[name], '__file__', None) == str(path_of(name)):
        return sys.modules[name]
    if name in ('openings', 'prims'):
        if openings_data is not None:
            os.environ['OPENINGS_DATA'] = str(openings_data)
        elif not os.environ.get('OPENINGS_DATA'):
            raise RuntimeError(f'load({name!r}) needs openings_data (OPENINGS_DATA is not set): prims would read its '
                               f'data folder beside the vendored copy')
    if name in sys.modules:
        raise RuntimeError(f'a module named {name!r} is already loaded from {getattr(sys.modules[name], "__file__", "?")}')
    if name == 'openings':
        # its own imports, by plain name, resolve to these copies
        for dep in ('geomkit', 'prims'):
            load(dep)
    check(name)
    spec = importlib.util.spec_from_file_location(name, path_of(name))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return mod
