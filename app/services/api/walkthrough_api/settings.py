"""Settings from the environment (DESIGN.md 10.6).

WALKTHROUGH_DATA_DIR          the local store (default `data`)
WALKTHROUGH_OFFLINE_TEMPLATE  the built offline template (default `dist/offline-template/viewer-template.html`)
WALKTHROUGH_CORS_ORIGINS      comma-separated origins allowed by CORS (default: the dev and preview origins, 10.4)
WALKTHROUGH_ALLOWED_HOSTS     comma-separated Host names the API answers (default `127.0.0.1, localhost`; any port).
                              The API has no login yet, so a request for another name (a page that points its own name at
                              127.0.0.1: DNS rebinding) is refused with 400 before it reaches a route (fix step, review
                              finding "code" 7). `*` answers every name.

Relative paths resolve against `app/` (two folders above services/api), whatever the working folder.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CORS_ORIGINS = (
    'http://localhost:5710',
    'http://127.0.0.1:5710',
    'http://localhost:4710',
    'http://127.0.0.1:4710',
)
DEFAULT_ALLOWED_HOSTS = ('127.0.0.1', 'localhost')


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
        )
