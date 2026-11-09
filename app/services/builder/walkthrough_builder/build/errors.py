"""The builder's typed failure (docs/upload/contract-issues/U3.md item 1).

contracts.build has no error type of its own; a build that cannot go on raises BuildError with a RunErrorCode of
upload-contracts.ts (`no_floors`, `bad_settings`, `area_empty`, `align_failed`, `detect_failed`, `build_failed`), a
plain sentence that names floors and files by their names (never a server path) and the JobRecord step it failed in.
The worker's step child reads `code`, `message` and `step`; any other exception is `build_failed`.
"""
from __future__ import annotations

CODES = ('no_floors', 'bad_settings', 'area_empty', 'align_failed', 'detect_failed', 'build_failed')


class BuildError(Exception):
    def __init__(self, code: str, message: str, step: str | None = None):
        if code not in CODES:
            raise ValueError(f'unknown build error code {code!r}')
        super().__init__(message)
        self.code, self.message, self.step = code, message, step

    def record(self) -> dict:
        """JobRecord.error's shape: {code, message, step}."""
        return {'code': self.code, 'message': self.message, 'step': self.step}
