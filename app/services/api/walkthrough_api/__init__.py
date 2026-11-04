"""Walkthrough API (DESIGN.md 9, 10): projects, versions, downloads and saved furniture heights over a local file store.

Routes reach the store only through `Depends(get_store)` (deps.py) and are plain `def` functions (DESIGN.md 9.3, 18.39).
The routes, their texts and models.py are frozen at the scaffold: `apps/web/openapi.json` must stay byte-identical.
"""

API_VERSION = '0.1.0'
