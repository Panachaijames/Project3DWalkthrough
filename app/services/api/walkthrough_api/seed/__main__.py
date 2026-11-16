"""`python -m walkthrough_api.seed --prototypes <project folder> --data <dir> [--force] [--reset-overrides]` (DESIGN.md 9.2).

Rebuilds the store's seed-table versions from the prototype folders, which it only reads. Without --force an existing
version is left alone; --force rebuilds every version folder but keeps each overrides.json (the saved furniture heights
and deleted boxes; when a version's model changed, its deleted boxes are re-mapped to the new model's pieces) unless
--reset-overrides. Every model, replay file and presentation is checked first: on any issue the seed stops with exit code
1 and changes nothing. `npm run seed` runs it with --prototypes .. --data data --force.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..builtmodel import ModelInvalid
from .build import SeedError, seed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog='python -m walkthrough_api.seed', description=__doc__.split('\n\n')[1])
    ap.add_argument('--prototypes', required=True, type=Path, help='the project folder holding bank_test/, cad_test/ ...')
    ap.add_argument('--data', required=True, type=Path, help='the store to (re)build (app/data)')
    ap.add_argument('--force', action='store_true',
                    help='rebuild versions that exist (saved heights and deleted boxes are kept; deleted boxes are '
                         're-mapped when a model changed)')
    ap.add_argument('--reset-overrides', action='store_true',
                    help='drop the saved furniture heights and deleted boxes too')
    a = ap.parse_args(argv)
    try:
        result = seed(a.prototypes.resolve(), a.data.resolve(), force=a.force, reset_overrides=a.reset_overrides)
    except (SeedError, ModelInvalid) as exc:
        print(f'walkthrough_api.seed: {exc}', file=sys.stderr)
        if not getattr(exc, 'partial', False):
            print('walkthrough_api.seed: nothing was changed', file=sys.stderr)
        return 1
    print(f'walkthrough_api.seed: {len(result.built)} version(s) written, {len(result.left_alone)} left alone, '
          f'store {a.data.resolve()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
