"""Names createProject derives (docs/upload/DESIGN.md U-13.3, U-8.4): the project id, the project naming and office ids.

* **Project id:** the given one, or a slug of the name (NFKD, ASCII letters and digits, every other run as `-`, lower
  case), 2 - 40 characters for a NEW project (U-4.1's path length; existing ids keep the 63 limit when read). A longer
  slug is cut at a `-` (or at 40 when it has none there); an empty or one-character slug (a Thai name) becomes
  `project-<6 hex>`. Reserved whether or not they exist: `new` (the web app's /projects/new) and the seed table's ids.
* **Naming:** photoName = the short name's ASCII with every other run as `-`, at most 64, else `Project`; maxPrefix =
  the initials of the name's first two to four ASCII words that start with a letter, upper case, padded with `X` to 2;
  maxFileName = the name's ASCII words joined by `_` + `.ms`, the stem at most 60, else `Project.ms`.
* **Office id:** a slug of the office's name (`^[a-z0-9][a-z0-9-]{1,62}$`), else `office-<6 hex>`.
"""
from __future__ import annotations

import re
import secrets
import unicodedata
from collections.abc import Callable

from ..seed.sources import SEED_TABLE

NEW_ID_MAX = 40
NEW_ID = re.compile(r'[a-z0-9][a-z0-9-]{1,39}')
RESERVED_IDS = frozenset({'new', *(v.project_id for v in SEED_TABLE)})
_NOT_ALNUM = re.compile(r'[^A-Za-z0-9]+')


def ascii_text(text: str) -> str:
    """NFKD, then only the ASCII characters (accents dropped from their letters; Thai and the like dropped whole)."""
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')


def _cut(text: str, limit: int, sep: str) -> str:
    """At most `limit` characters, cut at the last `sep` within them when the cut would split a word."""
    if len(text) <= limit:
        return text
    head = text[:limit]
    if text[limit] != sep and sep in head:
        head = head[:head.rfind(sep)]
    return head.strip(sep)


def slug(text: str, limit: int = NEW_ID_MAX) -> str:
    s = _NOT_ALNUM.sub('-', ascii_text(text)).strip('-').lower()
    return _cut(s, limit, '-')


def derived_project_id(name: str) -> str:
    """The slug of the name, or `project-<6 hex>` when it is shorter than 2 or holds no letter (UR, V2-15: a Thai name
    with a number, 'บ้านสุขุมวิท ซอย 31', became the id '31')."""
    s = slug(name)
    return s if len(s) >= 2 and any(c.isalpha() for c in s) else f'project-{secrets.token_hex(3)}'


def id_problem(project_id: str) -> str | None:
    """Why a wanted new id cannot be used (None: it can, if free)."""
    if not NEW_ID.fullmatch(project_id):
        return ('a project id is 2 - 40 lower-case letters, digits and hyphens, starting with a letter or digit '
                '(the 40-character limit keeps every file path within Windows\' 260 characters)')
    if project_id.endswith('-') or '--' in project_id:
        # (UR, V2-15: 'ab-' and 'a--b' were taken; a slug never makes either)
        return 'a project id ends with a letter or digit and has no two hyphens in a row'
    return None


def next_free(base: str, taken: Callable[[str], bool]) -> str:
    """`base-2`, `base-3` ... (the base cut so the id stays within 40 characters): the first neither taken nor reserved."""
    for n in range(2, 10_000):
        suffix = f'-{n}'
        head = base[:NEW_ID_MAX - len(suffix)].rstrip('-')
        candidate = f'{head}{suffix}'
        if candidate not in RESERVED_IDS and not taken(candidate):
            return candidate
    return f'project-{secrets.token_hex(3)}'


def words(text: str) -> list[str]:
    return [w for w in _NOT_ALNUM.split(ascii_text(text)) if w]


def photo_name(short_name: str) -> str:
    s = _NOT_ALNUM.sub('-', ascii_text(short_name)).strip('-')
    s = _cut(s, 64, '-').strip('-.')
    return s or 'Project'


def max_prefix(name: str) -> str:
    initials = [w[0].upper() for w in words(name) if w[0].isalpha()][:4]
    return ''.join(initials).ljust(2, 'X')


def max_file_name(name: str) -> str:
    stem = _cut('_'.join(words(name)), 60, '_').strip('_')
    return f'{stem or "Project"}.ms'


def naming(name: str, short_name: str) -> dict[str, str]:
    """ProjectNaming (JSON names) derived from a project's names."""
    return {'photoName': photo_name(short_name or name), 'maxPrefix': max_prefix(name),
            'maxFileName': max_file_name(name)}


def office_id(name: str) -> str:
    s = slug(name, 63)
    return s if len(s) >= 2 else f'office-{secrets.token_hex(3)}'
