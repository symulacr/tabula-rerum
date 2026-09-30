# TABULA CONTRACT

**Authoritative.** This file overrides every older document in this folder on any point of contact.
Where a historical document disagrees with this one, this one is current. See the conflict rule in
`START-HERE.md` §6.

Decided 2026-09-27 from repository evidence. The runtime ruling below was **not** a preference.

---

## 1. PRODUCT

Tabula Rerum is a CoinMarketCap data-visualization workspace. A user selects CMC index data,
compares two series over a chosen window, and reads the result as a chart with a full provenance
record attached to every API call it rests on.

The distinguishing claim is not chart quality. It is **reproducibility**: every number on screen can
be traced to a receipt that names the endpoint, the parameters, the auth mode, the CMC error code,
the credits consumed, and the wall-clock latency.

## 2. SCOPE

**In:**
- Regimen: CMC20 vs CMC100 over a user-chosen window, normalised and charted.
- Basket composition per day, where available.
- A receipt for every API call, rendered on the page.
- A non-visual equivalent for every chart.

**Out:**
- A node canvas / workflow builder. Rejected on evidence: the reference implementation joins parent
  outputs with `join("\n\n")` over a string bus, so a time-aligned numeric join is not expressible.
- Collaboration / realtime. Rejected: the reference auth route grants `*:write` on a wildcard
  namespace, and there is no shared mutable state to converge on in a read-and-compare product.
- Any keyed CMC endpoint in the judged path.
- An LLM dependency. The keyless path must work with no credentials of any kind.

## 3. RUNTIME — RULED, NOT CHOSEN

| | |
|---|---|
| Language | **Python 3.12** |
| Libraries | **Standard library only. No third-party runtime dependency.** |
| Package manager | none |
| API/proxy | `http.server.ThreadingHTTPServer` on `127.0.0.1` |
| Renderer | **hand-written inline SVG**, emitted server-side |
| Frontend | server-built HTML from Python string templates; no bundler, no build step |
| Storage | stdlib `json`; `sqlite3` when a ledger is needed |
| Share card | the host's existing headless Chrome, zero install |

**Why this is a ruling and not a preference.** The repository contract decides it:
- `IN-5` in `plan/SCOPE-BOUNDARIES.md`: *"A Python 3.12 stdlib server that proxies every CMC call,
  so the key never reaches the browser."*
- `build/shared/README.md:5`: *"**Stdlib only** for judged path. No third-party deps required."*
- `plan/SPEC.md:43-47` pins the same architecture with a stated reason per row.

This folder previously prescribed Vite + React + ECharts (`docs/stack-feasibility.md:51`,
`docs/harden.md:217`) while `docs/architecture.md:6` drew `UI[Tabula UI - React]`. That prescription
**is superseded**. It was written without reference to the contract rule, exactly as
`START-HERE.md:200-217` observed.

Note the rule is not an environment fact: Flask, FastAPI, requests, pandas, numpy and matplotlib
are all importable on this host. Stdlib-only is a discipline, so it is **enforced by a test**
(`TestStdlibOnly`), not assumed.

## 4. COMMANDS

```bash
python3 run.py                # dev server, offline from fixtures, port 8099
python3 run.py --live         # dev server against live keyless CMC
python3 run.py --port 9000    # override port
python3 run.py --days 90      # window size
python3 run.py --test         # run the suite
```

Production build: **there is none.** A build step is precisely what `SPEC.md:45` rules out
(*"no framework version that can drift inside the judged window"*).

## 5. CMC STRATEGY

**Existing client, re-implemented and defect-fixed.** Not an SDK, not raw ad-hoc HTTP.

The parent `build/shared/cmc_client.py` is the only working CMC client in the workspace and is
stdlib-only, which matches the runtime. But it carries six confirmed defects, so it is **not
copied** — `apps/api/tabula/client.py` is a purpose-built implementation that keeps verified
behaviour and fixes what was broken. Copying known-defective code would not make the project
standalone, it would make the defect portable.

Official SDKs were considered and rejected: the corpus records 0% adoption among ~55 comparable
projects, and they do not cover the RWA or x402 families this spec references.

| Concern | Rule |
|---|---|
| Keyless route | **Always preferred**, even when a key is present. This is the fix for D7. |
| Keyed route | Only with an explicit `allow_keyed=True` **and** a key passed in code. |
| Environment | **The client never reads `CMC_API_KEY` from the environment.** An exported key must not change behaviour. |
| Count | Hard-capped at 10 by the API; rejected client-side with a clear message. |
| Bounds | Full ISO-8601 with `Z`. A bare date returns 400. |
| Interval | `5m`, `15m`, `daily` only. |
| Retries | Rate limits (429) only, exponential, max 3. |
| Empty data | `200 + error_code 0 + empty` is a **FAILURE**, not a small result. |
| Browser secrets | None. The server proxies; no key is ever reachable from the browser. |

## 6. CANONICAL DATASET

Defined in `docs/CANONICAL-DATA.md`. Summary:

- **Series:** CMC20 and CMC100 daily index values, keyed by `update_time` (ISO-8601 ms).
- **Frequency:** daily. **Unit:** index points. **Depth:** both series start 2024-01-01.
- **Constituents:** per-day basket membership — **20 names/day for CMC20, 100 for CMC100, with
  different schemas** (CMC100 carries no `priceUsd` and no `units`).
- **Provenance:** every dataset carries the receipts that produced it.

## 7. ALIGNMENT POLICY — DECIDED

1. Axis: UTC, ascending, deduplicated by timestamp.
2. **Statistics: INNER JOIN.** Only timestamps present in both series.
3. **Rendering: OUTER JOIN.** Every day either series has, so a gap shows as a gap.
4. **Window: DROP** if inner-join coverage falls below 95% of the requested window, or if fewer
   than 30 paired observations exist. The drop is recorded, never silently analysed.
5. **Forward fill is PROHIBITED.** Carrying a value forward manufactures a run of zero daily
   returns, which understates volatility, which shrinks sigma, which **inflates every z-score**.
   A filled block would make divergence look more significant than the data supports — in a product
   whose claim is trustworthy provenance.

Implemented in `packages/features/tabula_features/align.py`; the prohibition is enforced by
`TestAlignment.test_forward_fill_is_prohibited`.

## 8. TRANSFORMATIONS

Pure functions, no I/O, no clock, no randomness. Same input always gives the same output.

`rebase` → `difference` → `z-score`, with `ratio` and `rolling volatility` available.

**Every printed figure is measured at render time.** An earlier master plan stated that a measured
0.520-point band becomes "3.5 sigma" when the same measurements give **2.94 sigma** — 3.5 belongs to
a different series (daily returns, not levels). A provenance product that prints a remembered
constant is not a provenance product. Guarded by
`TestTransforms.test_stats_are_measured_not_constants`.

## 9. VISUALISATION

Server-side inline SVG. Chart choice was not "a library because it is popular": the judged path has
no browser in the loop, so a canvas renderer is unavailable, and SVG is text — it renders
server-side, stays crisp at any zoom, and screenshots at exact pixels.

Accessibility is contractual, not an enhancement, because there is nothing to inherit: the
reference app has `sr-only` = 0 repository-wide and contrast defects down to 2.03:1. Every chart
emits `role="img"`, `aria-labelledby`, `<title>` and `<desc>`, a tabular equivalent, and carries
direction in a stroke style and a word, never in colour alone.

## 10. TESTING

Full contract in `docs/TEST-AND-ACCEPTANCE.md`. 41 tests, all passing, covering every parent-client
defect (E1, E3, E4, E5, E6, D7), the alignment policy, transform determinism, the accessibility
contract, and the stdlib-only rule.

## 11. ACCEPTANCE CRITERIA

The build is accepted when, from a clean copy and with no parent workspace on the path:

1. `python3 run.py --test` passes 41/41.
2. `python3 run.py` serves a page containing an SVG chart, a table fallback, and receipts.
3. The caption values equal the values recomputed from the dataset.
4. The client makes no keyed call, and reads no credential from the environment.
5. No shipped source imports a third-party module.

## 12. DEPLOYMENT

Loopback only, by design: the key must never be reachable, and the judged path needs no key at all.
Public hosting is an operator action and is **not** a build prerequisite.

## 13. DEFINITION OF DONE

A phase is done when its completion condition in `ROADMAP.md` is met **and** the test suite passes.
A phase is not done because a document describes it.

---

## 14. JEV REUSE LEDGER

Extracted from the reference clone's patterns. No code is copied; only behaviour is reproduced, in
Python, with the semantics Tabula needs.

| Asset | Action | Note |
|---|---|---|
| topological walk, `null` on cycle | EXTRACT | ordering discipline; Tabula's pipeline is linear so no graph is needed |
| `any`/`all` activation | EXTRACT | not used by the current panels; retained for the optional Board Lab |
| typed gate → confidence-scored label | ADAPT | regime labelling with **published thresholds**; `confidence` = distance from a stated threshold, honest by construction |
| TraceNode / RunList (already a receipt list) | ADAPT | superseded by `Receipt`, which carries path, params, auth mode, error code, credits, latency — strictly more |
| 36-LOC confidence bar + threshold tick | ADAPT | the bar and tick are re-implemented in the palette below |
| 4+3 status vocabulary, retry-able errors | ADAPT | carried into the receipt `verdict` field |
| `prefers-reduced-motion` | PRESERVE | honoured in the stylesheet |
| `tabular-nums` | PRESERVE | applied to all numeric cells |
| container queries | PRESERVE | one media query here; the pattern is noted for the fuller board |
| `useDraft` commit discipline | PRESERVE | applies to the future configuration form |
| `isEditableTarget` (5 LOC) | PRESERVE | trivial, load-bearing |
| node cards, inspector panel (~3,000 LOC) | ADAPT | screens survive; the canvas does not |
| rooms → Boards | REFRAME | naming only |
| feeds → receipt log | REFRAME | naming only |
| React Flow canvas | DISCARD | **proven**: `executor.ts:250-256` joins parent outputs with `join("\n\n")` over a string bus, so a time-aligned numeric join is inexpressible |
| Liveblocks collaboration | DISCARD | **proven**: `route.ts:33` + `database.ts:68-70` grant `*:write` on a wildcard namespace |
| original workflow semantics | DISCARD | prose-generation domain, not data |
| string bus | DISCARD | typed dataclasses at the client boundary instead |
| auth / hardcoded users | DISCARD | no credential surface in the judged path |

**Nothing in this build requires the reference clone.** The ledger records what was learned from
it and why the rest was left behind, so the next reader does not repeat the investigation.

### Palette

| Token | Value | Contrast on ground |
|---|---|---|
| ground | `#f7f7f4` | — |
| ink | `#1c1b19` | 15.9:1 |
| ink-muted | `#5c5a54` | 7.0:1 |
| rule | `#d8d6d0` | structural |
| accent (bronze) | `#8a6d1f` | 5.1:1 |
| series A | `#2f5d8a` | 5.4:1 |
| series B | `#8a5a2b` | 5.0:1 |
| positive | `#1f6b45` | 5.3:1 |
| negative | `#9b2c2c` | 6.1:1 |

Bronze rather than the reference app's `#7654cb` purple, and measured rather than asserted: the
wax ground proposed in `architecture.md:103` collapses surface/ground separation to 1.09:1, so the
ground was rejected while the bronze accent was kept.
