"""The scaffold's stand-in runner (U0), kept for tests that want a runner which refuses everything: every call answers
501 not_implemented. main.py serves the LocalJobRunner (U5)."""
from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
from typing import Any

from ..errors import not_implemented


class StubJobRunner:
    def start(self, run_dir: Path) -> None:
        raise not_implemented('JobRunner.start')

    def cancel(self, run_dir: Path) -> None:
        raise not_implemented('JobRunner.cancel')

    def alive(self, record: dict[str, Any]) -> bool:
        raise not_implemented('JobRunner.alive')

    def missing(self, kinds: Collection[str]) -> list[str]:
        raise not_implemented('JobRunner.missing')
