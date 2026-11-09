"""Constants and helpers of the builder's tests (scaffold U0). Imported by conftest.py and the tests as `kit`.

Everything a test writes goes under WT_TMP (each step's own row: %TEMP%\\wt-u<n>; WORK_BREAKDOWN section 1);
WALKTHROUGH_DATA_DIR and WALKTHROUGH_CACHE_DIR default to WT_TMP\\data and WT_TMP\\cache (never app/data or the default
cache). WT_REF (default %TEMP%\\wt-u0\\ref) is the scaffold's `make:reference` output: read-only.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS = Path(__file__).resolve().parent
BUILDER = TESTS.parent                              # services/builder
APP = BUILDER.parents[1]                            # app/
PROJECT = APP.parent                                # the project folder (the prototypes: read-only)
FIXTURES = APP / 'fixtures'
UPLOAD_FIXTURES = FIXTURES / 'upload'
DOCS = APP / 'docs' / 'upload'
VENDOR = BUILDER / 'walkthrough_builder' / 'vendor'
LIBREDWG = APP / 'vendor' / 'libredwg-0.14-win64'

#: the run's own temp folder
RUN = Path(os.environ.get('WT_TMP') or Path(tempfile.gettempdir()) / 'wt-builder')
#: the scaffold's make:reference output (shared, read-only)
REF = Path(os.environ.get('WT_REF') or Path(tempfile.gettempdir()) / 'wt-u0' / 'ref')

#: the six drawings: reference name -> DWG in the project folder
DRAWINGS = {
    'bank1': 'I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg',
    'bank2': 'I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg',
    'sukhumvit': 'Test Sukhumvit Residence.dwg',
    'presidential': 'layout presidential test.dwg',
    'l29': 'L29.dwg',
    'l30': 'L30.dwg',
}

#: how long a `worker` test waits for its run, queue time included (seconds)
WORKER_TIMEOUT_S = float(os.environ.get('WT_WORKER_TIMEOUT', '1800'))


def child_env(**extra: str) -> dict[str, str]:
    """The environment of a Python child of a test: the builder's (U-3.5), with PYTHONPATH=services/builder."""
    env = dict(os.environ, PYTHONPATH=str(BUILDER), PYTHONIOENCODING='utf-8', PYTHONUTF8='1',
               PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MPLBACKEND='Agg')
    env.pop('PYTHONNOUSERSITE', None)
    env.update(extra)
    return env


def python_child(code: str, *args: str, env: dict[str, str] | None = None, **popen) -> subprocess.Popen:
    """Starts `python -B -P -c code args...` (the builder Python) with pipes for stdout and stderr, text mode."""
    return subprocess.Popen([sys.executable, '-B', '-P', '-c', code, *args], env=env or child_env(),
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            encoding='utf-8', **popen)


def ref_file(*parts: str) -> Path:
    """A file of the reference folder (WT_REF), e.g. ref_file('proj', 'detector', 'bank1', 'prims.pkl')."""
    return REF.joinpath(*parts)


def ref_prims(name: str) -> Path:
    """The prototype prims.py cache of one drawing in the reference folder (the reader's oracle, U-7.1)."""
    return REF / 'proj' / 'detector' / name / 'prims.pkl'


def ref_dxf(name: str) -> Path:
    return REF / 'proj' / 'detector' / name / 'plan.dxf'


def ref_openings(name: str) -> Path:
    """The detector output of the reference run (equal to detector/output/<name>_openings.json)."""
    return REF / 'proj' / 'detector' / 'output' / f'{name}_openings.json'
