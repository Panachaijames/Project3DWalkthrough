"""Settings from the environment (DESIGN.md 10.6).

WALKTHROUGH_DATA_DIR          the local store (default `data`)
WALKTHROUGH_OFFLINE_TEMPLATE  the built offline template (default `dist/offline-template/viewer-template.html`)
WALKTHROUGH_CORS_ORIGINS      comma-separated origins allowed by CORS (default: the dev and preview origins, 10.4)
WALKTHROUGH_ALLOWED_HOSTS     comma-separated Host names the API answers (default `127.0.0.1, localhost`; any port).
                              The API has no login yet, so a request for another name (a page that points its own name at
                              127.0.0.1: DNS rebinding) is refused with 400 before it reaches a route (fix step, review
                              finding "code" 7). `*` answers every name.

The upload milestone (docs/upload/DESIGN.md U-13.5; scaffold U0):
WALKTHROUGH_BUILDER_PYTHON    the builder's Python (default `services/builder/.venv/Scripts/python.exe`, U-10.1)
WALKTHROUGH_LIBREDWG_DIR      the vendored LibreDWG (default `vendor/libredwg-0.14-win64`, U-6.1)
WALKTHROUGH_CACHE_DIR         the derived-file cache (default `%LOCALAPPDATA%/walkthrough/cache`, U-4.2)
WALKTHROUGH_CACHE_MAX_GB      the cache's size cap (default 5)
WALKTHROUGH_UPLOAD_MAX_BYTES  the largest upload (default 300 MiB, U-5.1)
WALKTHROUGH_RUN_LOCK          the machine run lock (default `%TEMP%/walkthrough-run.lock`, U-3.5)
`createBuild` and `runBuild` answer 503 builder_missing when the builder Python or LibreDWG is not there.

Relative paths resolve against `app/` (two folders above services/api), whatever the working folder.
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CORS_ORIGINS = (
    'http://localhost:5710',
    'http://127.0.0.1:5710',
    'http://localhost:4710',
    'http://127.0.0.1:4710',
)
DEFAULT_ALLOWED_HOSTS = ('127.0.0.1', 'localhost')
DEFAULT_BUILDER_PYTHON = 'services/builder/.venv/Scripts/python.exe'
DEFAULT_LIBREDWG_DIR = 'vendor/libredwg-0.14-win64'
DEFAULT_CACHE_MAX_GB = 5.0
DEFAULT_UPLOAD_MAX_BYTES = 300 * 1024 * 1024
#: an upload part (U-5.1): every part but the last is exactly this
PART_BYTES = 8 * 1024 * 1024


def default_cache_dir() -> Path:
    base = os.environ.get('LOCALAPPDATA') or tempfile.gettempdir()
    return Path(base) / 'walkthrough' / 'cache'


def default_run_lock() -> Path:
    return Path(tempfile.gettempdir()) / 'walkthrough-run.lock'


def _resolve(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (APP_ROOT / p).resolve()


def _names(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(o.strip() for o in value.split(',') if o.strip()) if value else default


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    offline_template: Path
    cors_origins: tuple[str, ...]
    allowed_hosts: tuple[str, ...] = DEFAULT_ALLOWED_HOSTS
    builder_python: Path = field(default_factory=lambda: _resolve(DEFAULT_BUILDER_PYTHON))
    libredwg_dir: Path = field(default_factory=lambda: _resolve(DEFAULT_LIBREDWG_DIR))
    cache_dir: Path = field(default_factory=default_cache_dir)
    cache_max_gb: float = DEFAULT_CACHE_MAX_GB
    upload_max_bytes: int = DEFAULT_UPLOAD_MAX_BYTES
    run_lock: Path = field(default_factory=default_run_lock)

    @staticmethod
    def display_path(path: Path) -> str:
        """A path for a message the API sends: relative to app/ when it lies inside it, else only its file name (the
        server's folders are not the caller's business)."""
        try:
            return Path(path).resolve().relative_to(APP_ROOT).as_posix()
        except ValueError:
            return Path(path).name

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        return cls(
            data_dir=_resolve(env.get('WALKTHROUGH_DATA_DIR') or 'data'),
            offline_template=_resolve(env.get('WALKTHROUGH_OFFLINE_TEMPLATE') or 'dist/offline-template/viewer-template.html'),
            cors_origins=_names(env.get('WALKTHROUGH_CORS_ORIGINS'), DEFAULT_CORS_ORIGINS),
            allowed_hosts=_names(env.get('WALKTHROUGH_ALLOWED_HOSTS'), DEFAULT_ALLOWED_HOSTS),
            builder_python=_resolve(env.get('WALKTHROUGH_BUILDER_PYTHON') or DEFAULT_BUILDER_PYTHON),
            libredwg_dir=_resolve(env.get('WALKTHROUGH_LIBREDWG_DIR') or DEFAULT_LIBREDWG_DIR),
            cache_dir=_resolve(env['WALKTHROUGH_CACHE_DIR']) if env.get('WALKTHROUGH_CACHE_DIR') else default_cache_dir(),
            cache_max_gb=float(env.get('WALKTHROUGH_CACHE_MAX_GB') or DEFAULT_CACHE_MAX_GB),
            upload_max_bytes=int(env.get('WALKTHROUGH_UPLOAD_MAX_BYTES') or DEFAULT_UPLOAD_MAX_BYTES),
            run_lock=_resolve(env['WALKTHROUGH_RUN_LOCK']) if env.get('WALKTHROUGH_RUN_LOCK') else default_run_lock(),
        )
