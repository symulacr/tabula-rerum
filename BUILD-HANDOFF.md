# BUILD HANDOFF

**Everything the implementation phase needs. No history unless a line prevents a mistake.**

Read this, then `TABULA-CONTRACT.md` (the contract) and `docs/CANONICAL-DATA.md` (the data).

---

## PRODUCT

A CoinMarketCap data-visualization workspace. The user compares two CMC index series over a chosen
window and reads the result as a chart, with a receipt for every API call behind it. The
differentiator is **reproducibility**, not chart polish.

## SCOPE

**In:** Regimen (CMC20 vs CMC100, normalised, charted) · basket composition per day · a receipt per
call · a non-visual equivalent for every chart.
**Out:** node canvas · collaboration · LLM dependency · any keyed endpoint in the judged path.

## AUTHORITATIVE CONTRACT

`TABULA-CONTRACT.md` — it overrides every other document on any point of contact. Conflict rule and
full hierarchy in `START-HERE.md` §6.

## RUNTIME

**Python 3.12, standard library only.** No bundler, no build step, no package manager, no install.
Ruled by `IN-5` and `build/shared/README.md:5`, not chosen. Enforced by `TestStdlibOnly` — the rule
is a discipline, not an environment fact, because Flask/pandas/numpy *are* importable here.

Server: `http.server.ThreadingHTTPServer` on `127.0.0.1`. Renderer: hand-written inline SVG,
emitted server-side. There is no browser in the loop, so no canvas renderer is available.

## PROJECT ROOT

`tabula-rerum/` — **this folder is the build root.** The old `tabula/` path in
`docs/architecture.md` is superseded; the tree is built here.

## DIRECTORY TREE

```
tabula-rerum/
  run.py                    entry point
  TABULA-CONTRACT.md        THE contract
  ROADMAP.md                the single roadmap
  TABULA-MANIFEST.md        every file, and whether it is needed to build
  BUILD-READINESS-AUDIT.md  current state
  BUILD-HANDOFF.md          this file
  apps/api/tabula/
    client.py               CMC client  (keyless-first, receipts, window walk)
    server.py               loopback server, page, /healthz, /api/regimen
  packages/features/tabula_features/
    align.py                Series, Window, the alignment policy
    transforms.py           rebase, difference, zscore, rolling vol, flagship
  packages/share/tabula_share/
    svg.py                  chart renderer + table fallback
    composition.py          composition panel
  evidence/fixtures/        190 recorded keyless points
  tests/test_tabula.py      47 tests
  docs/                     CANONICAL-DATA.md, TEST-AND-ACCEPTANCE.md + design docs
```

## DEV COMMAND

```bash
python3 run.py                # offline from fixtures, no key, no network  (default)
python3 run.py --live         # live keyless CMC
python3 run.py --port 9000 --days 90
```

## TEST COMMAND

```bash
python3 run.py --test         # 47 tests
```

## BUILD COMMAND

**None. There is no build step, by design** — a build step is what `SPEC.md:45` rules out
("no framework version that can drift inside the judged window").

## CMC STRATEGY

Existing client **re-implemented and defect-fixed** — not an SDK, not ad-hoc HTTP. The parent
client was not copied: it carried six confirmed defects, so copying it would have made the project
standalone only in the sense of relocating the bug.

| Rule | Value |
|---|---|
| Keyless route | **always preferred, even when a key is present** (the D7 fix) |
| Keyed route | only with explicit `allow_keyed=True` **and** a key passed in code |
| Environment | the client **never reads `CMC_API_KEY`** |
| `count` | hard-capped at 10; rejected client-side with a clear message |
| Bounds | full ISO-8601 with `Z`; a bare date returns 400 |
| `interval` | `5m`, `15m`, `daily` |
| Retries | 429 only, exponential, max 3 |
| Empty data | `200 + error_code 0 + empty` is a **FAILURE** |
| Browser secrets | none; the server proxies |

**Do not add a key to the judged path.** The keyless path is the design.

## CANONICAL DATASET

`docs/CANONICAL-DATA.md`. CMC20 and CMC100 daily index series keyed by **`update_time`** — *not*
`timestamp`; using the wrong name silently yields an empty series. Both start **2024-01-01** with
identical timestamp sets. Constituents: **20/day for CMC20, 100/day for CMC100, different schemas**
(CMC100 has no `priceUsd`, no `units`).

Fixtures carry **no provenance block**, so a recorded capture can never masquerade as a live one.

## ALIGNMENT POLICY

**Decided. Implement against it; do not re-decide it.**

1. UTC axis, ascending, deduplicated by timestamp.
2. **Statistics: INNER JOIN.** Only timestamps present in both series.
3. **Rendering: OUTER JOIN.** Every day either series has, so a gap shows as a gap.
4. **Drop the window** if inner-join coverage < 95% of the request, or fewer than 30 paired points.
   Record the drop; never analyse it silently.
5. **Forward fill is PROHIBITED.** It manufactures zero daily returns → understates volatility →
   shrinks sigma → **inflates every z-score**, i.e. it would manufacture the finding this product
   reports. Enforced by a test.

## TRANSFORMATIONS

Pure functions — no I/O, no clock, no randomness.

`rebase(→100)` → `difference` → `z-score`. Also `ratio`, `rolling volatility`.

**The raw CMC20−CMC100 difference is visually flat** — measured mean 7.981, sd 0.177, span 0.520,
6.5% of the mean. The spread is only legible after rebasing and differencing.

**Every printed figure is measured at render time.** A master plan once stated that a measured
0.520 band becomes "3.5 sigma" when the same numbers give **2.94 sigma** (3.5 belongs to a
different series). Acceptance criterion A15 recomputes sigma from the data so that cannot recur.

## UI / PANELS

Two panels, both server-rendered, both with a table fallback:

- **Regimen** — the spread chart, in z-score units, with a dashed zero line and a caption carrying
  measured `n`, mean, sd and coverage.
- **Composition** — per-day basket membership with weight bars, and the mandatory caveat rendered
  on the panel: *CMC-selected basket composition, not market churn; entries and exits are index
  rebalances, not market events.*

## JEV ASSETS TO REUSE

Full ledger with reasons in `TABULA-CONTRACT.md` §14. **Nothing in this build requires the reference
clone.** Reused as patterns: topological ordering · the confidence bar with its threshold tick ·
the retry-able status vocabulary · `prefers-reduced-motion` · `tabular-nums` · container queries ·
`useDraft` · `isEditableTarget`.

**Forbidden approaches — do not re-litigate, the evidence is recorded:**
a node canvas · collaboration · a string bus · copying the parent client · any keyed endpoint in the
judged path · an LLM dependency.

## PROVENANCE REQUIREMENTS

Every fetch emits a `Receipt`: `path_key, path, method, params, auth_mode, http_status, error_code,
verdict, error_name, error_class, credit_count, elapsed_ms, at, note` + a SHA-256 digest. The page
renders them. **A number without a receipt is a defect.**

## ACCESSIBILITY REQUIREMENTS

Nothing is inherited here — the reference app has `sr-only` = 0 and contrast defects to 2.03:1.

Every chart must carry `role="img"`, `aria-labelledby`, `<title>`, `<desc>`, and a **tabular
equivalent**. Direction must be in a stroke style **and** a word, never colour alone. Palette
contrast ratios are in `TABULA-CONTRACT.md` §14. `prefers-reduced-motion` and `focus-visible` are
honoured. Numeric cells use tabular figures.

## ACCEPTANCE CRITERIA

22 criteria in `docs/TEST-AND-ACCEPTANCE.md`, each as requirement → test → expected → pass
condition. A15 (sigma measured, not stored) is the one that guards a real error from this
project's history.

## DEFINITION OF DONE

A phase is done when its completion condition in `ROADMAP.md` is met **and** the suite passes.
A phase is not done because a document says so.

## KNOWN NON-BLOCKING ITEMS

| Item | Status |
|---|---|
| Public HTTPS | **operator action**, not a build task; the judged path needs no key |
| Keyed capture | **proved not required for MVP** — keyless by design; a key's presence is not authorisation |
| Dark theme | **proved not required for MVP** — needs a product decision first |
| Fear & Greed panel | 50 points recorded; a product decision, not a data gap |
| Track amendment | `IN-1`/`OUT-1` authorise Códice on AI Agents and Automation; this is Tabula on Data and Visualisation. **OWNER DECISION.** Does not affect implementation. |
