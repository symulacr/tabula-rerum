# TEST AND ACCEPTANCE CONTRACT

**Authoritative for verification.** 41 tests, all passing, run with the standard library only:
`python3 run.py --test`.

---

## 1. Why each parent defect has a test

The workspace client carried six confirmed defects. Each has a named test that **fails without the
fix**, so none can regress silently.

| Defect | Test | Fails without the fix because |
|---|---|---|
| **E1** pager never advanced | `TestE1Pager.test_walk_advances_and_never_duplicates` | asserts >1 page and no repeated window |
| **E3** fabricated `PLAN_GATED` | `TestE3Sentinels.test_sentinels_never_collide_with_cmc_codes` | `int(sentinel)` must raise, so it can never alias a CMC code |
| **E4** deprecated `/v1/simple/price` | `TestE4SimplePrice` | asserts the path is `/v2` and no `/v1/simple/price` exists |
| **E5** `200/0/[]` treated as success | `TestE5EmptyData.test_200_zero_error_empty_is_not_ok` | the exact live body must be `ok == False` |
| **E6** live capture indistinguishable from fixture | `TestE6Receipts` | receipt fields + fixtures must not carry provenance |
| **D7** key silently upgraded keyless calls | `TestD7AuthRouting` | keyless must win even with a key present |

**D7 is the most important of the six.** In the parent client, `auth_mode_for()` checked `has_key`
before consulting the keyless list, so an exported key turned all 18 keyless paths into keyed Pro
calls: credits burned, receipts mislabelled, and the `keyless_rejected` branch unreachable.

## 2. Test layers

**Unit — client:** auth routing, sentinel collision, error classification, count/interval guards,
ISO bound format, empty-data semantics, receipt fields.

**Unit — alignment:** inner join for statistics, outer join for rendering, coverage drop,
minimum-points drop, forward-fill prohibition (static scan of shipped source).

**Unit — transforms:** rebase arithmetic, rebase-to-zero rejection, z-score standardisation,
undefined-dispersion handling, determinism, and the sigma regression guard.

**Unit — rendering:** `role="img"`, `aria-labelledby`, `<title>`, `<desc>`, direction not carried
by colour alone, table always emitted, no canvas.

**Integration — end to end:** offline render from fixtures produces an analysable window with ≥30
paired observations, and a page containing SVG + table + receipts. Offline makes no call and uses
no auth mode.

**Hygiene:** no shipped source imports a third-party module; all shipped source compiles.

## 3. Acceptance criteria

Each criterion is stated as requirement → test → expected result → pass condition.

| # | Requirement | Test | Expected | Pass condition |
|---|---|---|---|---|
| A1 | Keyless is preferred even with a key present | `test_keyless_preferred_even_when_key_present` | every keyless path reports `keyless` | no path reports `keyed` |
| A2 | Keyed paths never called implicitly | `test_keyed_path_refuses_without_permission` | refusal with a client sentinel | `ok == False`, `auth_mode == "none"` |
| A3 | The environment cannot change behaviour | `TestD7AuthRouting` | no env read in the client | key must be passed in code |
| A4 | Sentinels cannot collide with CMC codes | `test_sentinels_never_collide_with_cmc_codes` | `int(sentinel)` raises | no sentinel is numeric |
| A5 | Empty success is a failure | `test_200_zero_error_empty_is_not_ok` | `SENTINEL_EMPTY_INVALID` | `ok == False` |
| A6 | `count` respects the API cap | `test_count_cap_enforced_client_side` | `SENTINEL_BAD_PARAM` mentioning 10 | `ok == False` |
| A7 | Bounds are full ISO-8601 with `Z` | `test_iso_z_emits_full_timestamp` | `YYYY-MM-DDT00:00:00Z` | regex matches |
| A8 | The pager advances | `test_walk_advances_and_never_duplicates` | >1 page, no repeated window | `len(asked) == len(set(asked))` |
| A9 | No duplicate timestamps | same | 0 duplicates | `len == len(set)` |
| A10 | Statistics use the intersection | `test_inner_join_for_statistics` | 57 of 60 paired | equals the intersection |
| A11 | Rendering keeps every day | `test_outer_join_for_rendering_shows_the_gap` | 60 axis points | axis ≥ paired |
| A12 | Sparse windows are dropped | `test_coverage_guard_fires_when_enough_points_but_sparse` | a recorded reason | `is_analysable == False` |
| A13 | Forward fill is absent | `test_forward_fill_is_prohibited` | no fill construct in source | scan finds nothing |
| A14 | Transforms are deterministic | `test_deterministic` | identical stats across calls | `stats == stats` |
| A15 | **Sigma is measured, not remembered** | `test_stats_are_measured_not_constants` | caption sigma equals `raw_span / raw_sd` | equal to 9 places |
| A16 | Every chart is accessible | `test_chart_has_accessibility_contract` | role, label, title, desc present | all four present |
| A17 | Direction is not colour alone | `test_direction_is_not_colour_alone` | dash pattern + a word column | both present |
| A18 | A table always exists | `test_table_is_always_emitted` | table even for an empty window | `<table` present |
| A19 | No canvas dependency | `test_no_canvas_dependency` | `<svg`, no "canvas" | both hold |
| A20 | Stdlib only | `test_no_third_party_imports_in_shipped_source` | no forbidden import | offenders list empty |
| A21 | Offline path needs no key | `test_no_key_used_offline` | `offline`, `auth_modes == ["none"]` | both hold |
| A22 | End-to-end offline render works | `test_offline_render_from_fixtures` | analysable window, ≥30 points, page with SVG + table | all three |

A15 is the regression guard for a real error in this project's history: a master plan stated that a
measured 0.520-point band becomes "3.5 sigma" when the same measurements give **2.94 sigma**,
because 3.5 belongs to a different series. The test recomputes sigma from the data, so a
hard-coded caption cannot survive.

## 4. Clean-environment test

The suite must pass from a copy of this folder alone, with the parent workspace off the path. This
proves standalone-ness rather than assuming it. Result recorded in `BUILD-READINESS-AUDIT.md`.

## 5. Not covered, and why

| Not covered | Why |
|---|---|
| Live keyed calls | forbidden without authorisation; the judged path needs no key |
| Browser rendering | the renderer is server-side SVG by ruling; there is no browser in the loop |
| Sustainable keyless rate | undocumented by CMC; bounded observations only |
| Dark mode | deferred by decision |
