"""Write the OpenAPI document without a server (DESIGN.md 10.5): `python -m walkthrough_api.openapi_export <out.json>`.

Sorted keys, indent 2, UTF-8, LF line ends, one trailing newline: the bytes the integration step compares.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .main import create_app


def openapi_text() -> str:
    return json.dumps(create_app().openapi(), indent=2, sort_keys=True, ensure_ascii=False) + '\n'


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print('usage: python -m walkthrough_api.openapi_export <out.json>', file=sys.stderr)
        return 2
    out = Path(args[0])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(openapi_text().encode('utf-8'))
    print(f'wrote {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
