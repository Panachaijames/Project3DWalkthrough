"""The job runner seam (docs/upload/DESIGN.md U-13.4): the API starts and stops worker runs only through this, so Cloud
Run Jobs can replace the local runner later without a route change. Routes get it from `Depends(get_jobs)` (deps.py),
never from app.state. Scaffold U0; completed by U5 (LocalJobRunner in local.py: launch.json after Popen with the FILETIME
procStart, the 15 s kill on a timer thread, alive(); `missing()` for the 503 builder_missing of U-13.5).
"""
from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
from typing import Any, Protocol


class JobRunner(Protocol):
    def start(self, run_dir: Path) -> None:
        """Starts the worker on a run folder holding spec.json (writes launch.json, U-3.4)."""

    def cancel(self, run_dir: Path) -> None:
        """Asks the run to stop (creates its cancel file; kills it 15 s later if it has not stopped, U-3.4)."""

    def alive(self, record: dict[str, Any]) -> bool:
        """True when the worker of a LaunchRecord or JobRecord ({pid, procStart}) is still that process."""

    def missing(self, kinds: Collection[str]) -> list[str]:
        """What the runner lacks to run a build of sources of these kinds ('dwg', 'dxf'): plain sentences, empty when
        nothing is missing (createBuild and runBuild answer 503 builder_missing with them)."""
