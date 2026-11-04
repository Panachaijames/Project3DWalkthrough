# Contract issues: scaffold (S), 3 Nov 2026

Written only by the scaffold. The integration step settles each with the architect (DESIGN.md 18.0).

## S-1. The house page's collider vertex totals in DESIGN.md 17.2 do not reproduce

17.2 says the house page had 6,924 (ground) and 6,348 (upper) collider vertices and that v1's 6,936 / 6,372 differ by
earcut 3.0.2 (three 0.186) against 2.2.4 (three 0.160). The page captured on 3 Nov (`cad_test/house_3d_preview.html`,
three r160 from its import map, checked with `THREE.REVISION`) has 6,936 and 6,372, the same totals as v1
(`fixtures/prototype/sukhumvit-house.json`; table in `fixtures/README.md`). The collider, walkable, late, tick, plinth and
pieces COUNTS of 17.2 match the page exactly; only the vertex claim and its earcut explanation do not.
Effect: none on builders (A checks the house against the v1 values, which stand). Risk 19's earcut row may be moot for
the house; worth one look at integration (e.g. whether the earcut difference shows only after the v1 grouping).

## S-2. JSON Pointer of a duplicate id (5.6) was not fixed by the design

`fixtures/models/broken/expected.json` reports a duplicate at its later occurrence (`/openings/5/id`) and a missing property
at its parent object (`/floors/1`, as ajv and jsonschema do). The architect's provisional checker
(`docs/reference/provisional_v1.py cross_issues`) names a duplicate `/openings`. Builders A (`parseBuiltModel`) and E
(`builtmodel.validate`) follow the manifest; recorded as DESIGN.md 18.49.

## Notes for the builders (scaffold decisions, DESIGN.md 18.42 - 18.50)

* `services/api/walkthrough_api/store/base.py` carries D-9.3's `Store` Protocol, `BlobRef`, `StagedRef`, `NotFound`; the
  store-file record types (`ProjectMeta`, `VersionMeta`, `HeightOverridesFile`, `NewProject`, `VersionDraft`) are left open
  (`Any`) for builder E to define. `store/local.py` is a stub (`list_projects()` returns `[]` so `/api/health` works).
  Both are E's files; the routes only import `Store` from `store.base`.
* Every route except health answers `501 not_implemented` until E writes its body. Route decorators, parameters and
  `models.py` are frozen: `apps/web/openapi.json` must stay byte-identical (DESIGN.md 10.1, 18.50).
* `packages/viewer/scripts/make-offline.mjs` is a stub that writes nothing and exits 0, so `npm run build` runs end to end
  before builder A's script exists.
* Vite moves the offline template's inlined module script into `<head>` (an inline module script is deferred, so it still
  runs after `#wtv-app` and `#wtv-data` are parsed); the data element stays in `<body>`, each marker once.
* The scaffold's own tests live in `packages/viewer/test/unit/scaffold/`, `test/harness/scaffold/`,
  `services/api/tests/test_smoke.py`, `apps/web/test/smoke.test.tsx` (F owns `apps/web/test/**` and may replace it) and
  `tests/e2e/lib/smoke-prototype.spec.ts`.
