# Contract issues: builder E (API, store, seed and converters), 3 Nov 2026

Written only by builder E. The integration step settles each with the architect (DESIGN.md 18.0). None of them blocked E:
each is worked around inside E's own files (`services/api/walkthrough_api/**`, `services/api/tests/**`), as said.

## Comparisons the breakdown asks to report (WORK_BREAKDOWN E "Tests alone")

* **Converters against the provisional fixtures: no difference.** `convert_suite.convert(pres2_model.json)` equals
  `fixtures/models/suite.model.json` and `convert_house.convert(house3d_merged.json, furniture_house.json)` equals
  `fixtures/models/house.model.json`, as parsed JSON and also byte for byte (`json.dumps(..., ensure_ascii=False,
  separators=(',', ':')) + '\n'`); the seeded house's stamp is therefore the fixture's sha1[:12], `e43270cc0c9b`
  (`tests/test_converters.py`).
* **Presentation port against `fixtures/presentation/*.json`: no difference.** All five versions equal the provisional
  fixtures exactly (same optional fields written, same values) and after filling the D-8 defaults
  (`tests/test_presentation.py`), and they meet the D-8 oracle against `fixtures/prototype/*.json` (title, heading, intro
  text and HTML, accent, legend, floor buttons, ticks with labels and checked state, the picture tick's title, camera).
* **Replay oracles (D-7.4): hold** for bank v1, bank v2, the suite and the house: with the model's levels and heights
  filled in, every caption, fact, layer row, layers title, intro title and step title equals the page's character for
  character (`tests/test_stages.py`).
* **Cross-check with builder A's parsers (3 Nov, 12:54, A's files as they were then):** a throwaway vitest run outside
  `app/` passed every seeded `model.json`, `presentation` and `stages.json` through A's `parseBuiltModel`,
  `parsePresentation` / `resolvePresentation` and `parseReplayData`: all accepted, no furniture warnings, and each
  resolved presentation equal to the resolved `fixtures/presentation/*.json`. Not a test E keeps (A's files are A's);
  the integration step's `npm run seed` + viewer runs cover it.
* **Counts and stamps of D-6.5: equal** for all five versions (the seed prints them; `tests/test_converters.py`).

## E-1. Store needs a raw-bytes read for the offline payload (D-9.3 against D-16)

D-16 builds the payload by "plain concatenation of raw file text" of `meta.json`, `version.json`, `model.json`,
`stages.json` and `overrides.json`, so that Node (`make-offline.mjs`, which reads the files) and Python give the same bytes.
D-9.3's `Store` hands out raw bytes only for `model.json` / `stages.json` (`read_json_bytes`, typed with that Literal); the
other three come back parsed (`get_project`, `get_version`, `read_overrides`), and re-serialising a parsed record is not
guaranteed to give the stored bytes (a hand-edited or older file). Workaround: `Store.read_file_bytes(project_id, n | None,
name, missing_ok=False)` added to `store/base.py` (Protocol) and `LocalStore` (`n=None` means `meta.json`); `offline.py`
uses it. Routes do not call it. Suggestion: adopt it in D-9.3 (a `SupabaseR2Store` keeps the files' text as objects or in
the rows). The byte-equality test with A's `make-offline.mjs` passes on the corpus store and the seeded store.

## E-2. Two error codes beyond D-10.2

* `503 offline_template_invalid`: the template file exists but does not hold each marker exactly once (D-16 "otherwise
  stop with an error"). The route's frozen `responses` declare 503 as `ErrorResponse` (description
  `offline_template_missing: ...`), so the client types still fit; only the code is new. The message says to rebuild the
  template (`npm run build:offline:template`).
* `500 store_error`: a store file that is not what the store writes: a `meta.json` / `version.json` / `overrides.json`
  that does not parse into its record, a version that `meta.json` lists but whose folder or `version.json` is missing (a
  version it does not list is a plain 404 `version_not_found`), a version folder without its model, and, for the offline
  download, any embedded file that is not strict JSON (UTF-8 without a BOM: `make-offline.mjs` refuses such a file too, so
  the API never hands out a page that cannot start). Not declared in the frozen `responses` (FastAPI's default 500 has no
  body schema either). Suggestion: list both codes in D-10.2.

## E-2b. The frozen `HeightsUpdate` model is lax: `"600"` is taken as 600

D-10.2: "every value an integer 10 - 5000". `models.py` (frozen) declares `heights: dict[str, int]`, and FastAPI validates
the parsed body in pydantic's lax mode, so a JSON string of digits (`"600"`) and an integral float (`600.0`) are accepted as
600, `true` becomes 1 (then refused: 422 `invalid_heights`, out of range), while `600.5` or `"6e2"` get FastAPI's 422
(checked 3 Nov through the route). What is stored is always whole numbers, and the generated client sends numbers, so
nothing downstream sees a string. Fixing it needs `models.py`: `heights: dict[str, StrictInt]` has the same JSON schema
(checked: identical `model_json_schema()`, so `openapi.json` should not move; re-export to confirm) and refuses `"600"`,
`true` and `600.0` (JavaScript's `JSON.stringify` never writes `600.0`). Left to the integration step.

## E-3. Codes D-9.3 leaves open

`Store.download` raises `NotFound('download_not_found')` (D-9.3 names no code; the download routes check `version.json`
first and answer `no_max_script` / `no_furniture`, so the API never shows it in practice). `read_file_bytes` raises
`file_not_found`, `stage` refs that do not exist `staged_not_found`. Information only.

## E-4. createdAt of a version made from two source files (D-9.2)

"createdAt = the mtime of the version's model source file". The house's model is made from `house3d_merged.json`
(28 Oct 07:18 UTC) and `furniture_house.json` (29 Oct 05:34 UTC); E takes the newer of the files the model is made from
(`2026-10-29T05:34:39Z`), which agrees with its label `29 Oct 2026: openings and furniture boxes`; with the merged file
alone it would say 28 Oct. Every other version has one source file. Suggestion: word D-9.2 "the newest mtime of the files
the model is made from".

## E-5. The furniture underside on a chain of supports (agrees with C-2)

`furniture_csv.py` ports `furniture_kit.csv_text` line for line (D-18.8): a piece on a support stands at the support's
KIND base + its kind height (one level), while `furniture_boxes.js` (C's port, the viewer's `csv()`) resolves the support's
own underside recursively. They agree for all four models (every support stands on nothing; the API's CSV equals the
prototype CSVs and the typed goldens byte for byte). E keeps the kit's rule and adds no 5.6 rule of its own (that would make
the API refuse models the design accepts). C's suggestion (a 5.6 rule "a support has no `on` itself", strict in the API)
would close the gap on both sides.

## E-6. pytest's seeded store is `<WT_TMP>/api-tests/seeded/data`, not `<WT_TMP>/data`

WORK_BREAKDOWN E says "a temp store seeded from the prototypes into `%TEMP%\wt-e\data`". Playwright's API web server
(`tests/e2e/playwright.config.ts`) replaces `<WT_TMP>/data` with a fresh copy of `app/data`, so a pytest session and an e2e
run sharing a `WT_TMP` (the integration step's) would delete each other's store. pytest therefore seeds into
`<WT_TMP>/api-tests/seeded/data` (and copies it per writing test under pytest's `basetemp`, `<WT_TMP>/api-tests/pytest`);
the manual uvicorn check on port 8725 used `%TEMP%\wt-e\data` as written. Information only.

## E-7. What the record types and sidecar checks are (S.md left them to E)

* `store/base.py` defines `ProjectMeta`, `VersionMeta` (+ `AssetMeta`, counts, floors, downloads, seed), `HeightOverridesFile`
  and `NewProject` as pydantic records of the contracts.ts section 4 shapes, camelCase on disk, `extra='forbid'`: a store
  file with an unknown field is a `StoreError` (500), so a later format change needs these records changed with it.
  `VersionDraft` follows D-9.5 field for field; `create_version` derives each asset's role from its name (`topview.png` is
  the thumbnail; a plan picture is named after its floor's `pictureFrame.file`, last path part), because the draft carries
  no role or floor. Suggestion for the next milestone: give `VersionDraft.assets` a role and floor per file.
* There is no JSON schema for ReplayData and Presentation: `walkthrough_api/checks.py` checks them against contracts.ts
  sections 2 and 3 by hand, strictly (no unknown fields; floor keys of the model), and the seed and `create_version`
  refuse on any issue (D-9.2 "fails loudly"). A field added to contracts.ts must be added there too.

## E-8. Smaller readings of the design (information)

* PUT furniture-heights with a map that ends up empty (every value equal to the model's) still writes `overrides.json`
  with `heights: {}` and revision + 1 (the revision is the seam for If-Match, D-10.2), rather than deleting it.
* Intro runs and page texts (D-8): the generators pasted their texts into HTML raw. The seed decodes the character
  references a browser would (`&amp; &lt; &gt; &quot; &apos; &nbsp;`, decimal and hex numeric ones) in the intro runs and
  in the other page texts (title, heading, legend texts, floor button names), and refuses any other named reference and
  any tag but `<b>` (intro) or any tag at all (the other texts). The four projects contain none of those.
* The hotel's `camera.away` is stored as `round(v * 0.9, 6)` = `[21.6, 22.05, 26.1]` (D-13 "(24, 24.5, 29) x 0.9"; the
  provisional fixture has the same numbers).
* A 304 (If-None-Match) answer carries the same `ETag`, `Cache-Control` and, for the model, `X-Model-Stamp` headers as the
  200; `If-None-Match: *` and weak tags (`W/"..."`) match.
* Asset, download and source file names: beyond D-9.3's `^[A-Za-z0-9._-]+$`, the store also refuses `.`, `..` and any name
  ending in a dot (Windows drops trailing dots, so `Hotel_Lobby.ms.` would open `Hotel_Lobby.ms`). An asset must also be
  listed in `version.json`.
* A seed whose checks all pass but whose folder swap fails (on Windows: a file in the old version folder held open, e.g.
  the running API sending it) stops with exit code 1, says which versions were already put in place, and leaves no staging
  folder behind (`SeedCommitError`); "nothing was changed" is printed only when that is true.
