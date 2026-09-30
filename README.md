# Tabula Rerum

**Track: Data and Visualisation** · Build with CMC: API Hackathon

A CoinMarketCap workspace that makes the *shape of a market claim* measurable — and shows its work.

> **The one-sentence finding:** CMC20 and CMC100 correlate at **r = 0.999902**. They are the
> same asset class. The "regime spread" between them has lag-1 autocorrelation **ρ₁ = 0.947** —
> a unit root. It has **no equilibrium to deviate from**, so "the spread is 2σ from normal" is a
> category error. What we can honestly measure is the spread in percentage points, its position
> in the cross-window distribution, and its **effective sample size (6.06, not 70)**. This repo
> ships that measurement, with a receipt behind every number.

## Run it

```bash
python3 run.py            # offline from recorded fixtures — no key, no network
python3 run.py --live     # live keyless CoinMarketCap
python3 run.py --test     # 47 tests
```

**Python 3.12, standard library only.** No npm, no bundler, no build step, no third-party
runtime dependency. `TestStdlibOnly` enforces this — the environment *has* Flask/pandas/numpy,
so it is a discipline, not an accident.

## Why this shape

The API offers a sentiment tape that is barely documented, an index pair that is almost the
same series, and failure modes that are indistinguishable from each other. This project treats
those as the subject matter rather than obstacles:

| Claim most projects would make | What we measured instead |
|---|---|
| "CMC20 vs CMC100 regime spread" | `r = 0.999902`; difference has `ρ₁ = 0.947` → **unit root**, no valid null |
| "The spread is −2.08σ" | reported as **percentage points + percentile rank + `n_eff = 6.06`** |
| "Sentiment is a 7-day stub" | `/v1/altcoin-season-index/historical?timeframe=90d` returns **90 daily points** |
| "Fetch failed" | unrouted paths return **`HTTP 200` + `error_code 500` + "The system is busy"** — classified here as `UNROUTED`, not `TRANSIENT`, and never retried |

## Provenance model

Every fetch emits a `Receipt`: `path, params, auth_mode, http_status, error_code, credit_count,
elapsed_ms`, plus a SHA-256 digest. **A number without a receipt is a defect.** Fixtures carry
no provenance block, so a recorded capture can never masquerade as a live one.

`HTTP 200 + error_code 0 + data: []` is classified as **failure**, not empty success — verified
live with `?symbol=ZZZNOTAREALCOIN`.

## Endpoints used — all keyless, no API key required

| Endpoint | Why |
|---|---|
| `GET /public-api/v3/index/cmc20-historical` | the leaderboard index, daily, with per-day constituents |
| `GET /public-api/v3/index/cmc100-historical` | the broad index, same date grid from 2024-01-01 |
| `GET /public-api/v3/index/cmc20-latest` · `cmc100-latest` | current value + 24h change |
| `GET /public-api/v3/fear-and-greed/historical` | sentiment context, ~1,189 records from 2023-06-29 |
| `GET /v1/altcoin-season-index/historical?timeframe=90d` | breadth tape, 90 daily points |

Paging constraints, all live-verified: `count` is **hard-capped at 10**; bounds must be **full
ISO-8601 with `Z`**; `interval` accepts only `5m` / `15m` / `daily`. A multi-month pull must
walk window by window — 70 points took 7 contiguous pages with **0 duplicate timestamps**.

## Where the API got in the way

CMC asked for this specifically, and said it matters more to them than any single submission.

1. **The index endpoints are absent from the track's own suggested menu.** The Data and
   Visualisation track suggests historical quotes, OHLCV, global metrics, categories, DEX pairs
   and exchange listings. `/v3/index/cmc20-*`, `/v3/index/cmc100-*` and the Altcoin Season Index
   are not on it. The most interesting keyless data in the API is the data the track description
   does not point you at.
2. **Auth failures are masked as transient errors.** An unrouted or unauthorised path returns
   **`HTTP 200`** with `error_code: 500` and `"The system is busy, please try again later!"` —
   byte-identical to a genuine blip, and in direct conflict with the documented "retry 500"
   guidance. A naive retry loop hangs forever. We detect it by the absence of a `data` key.
3. **The keyless rate limit is undocumented.** The official error table stops at `1011`
   (`IP_RATE_LIMIT_REACHED`). The limit that actually governs anonymous access is **`1022`**,
   which appears in no table. No `Retry-After` and no `X-RateLimit-*` headers are returned on any
   response, so there is no machine-readable contract for backing off.
4. **The OpenAPI spec is wrong about a field it documents.** `openapi.json` declares Fear & Greed
   `timestamp` as an ISO-8601 datetime; the wire value is a decimal **epoch string**. Any
   spec-driven client generator produces broken code here.
5. **Constituent schemas differ between the two indices without being flagged.**
   `cmc20-historical` returns `priceUsd` and `units` per constituent; `cmc100-historical` returns
   neither. Code reading `priceUsd` must branch on the index, and nothing in the docs says so.
6. **Credit accounting is opaque on the keyless tier.** Every keyless call reports
   `credit_count: 1` with no account and no visible quota, so a build cannot tell whether it is
   near a ceiling.
7. **The changelog has a 17-month gap** (Oct 2024 → Mar 2026) and never records the Fear & Greed
   `v1` → `v3` move or the `/v3/index/*` endpoints at all.

## Alignment policy — decided, not TBD

- **Statistics: INNER JOIN.** Only timestamps present in both series.
- **Rendering: OUTER JOIN.** Every day either series has, so a gap renders as a gap.
- **Window: DROPPED** if inner-join coverage < 95%, or fewer than 30 paired observations. The
  drop is recorded, never silently analysed.
- **Forward fill: PROHIBITED.** It manufactures zero returns → understates volatility → shrinks
  sigma → **inflates every z-score**, i.e. it would manufacture the finding this project reports.
  Enforced by a test.

## Panels

- **Regimen** — the rebased spread in percentage points, with a dashed zero line and a caption
  carrying measured `n`, mean, sd, coverage, `ρ₁` and `n_eff`. **Every printed figure is measured
  at render time**, never copied from a document.
- **Composition** — per-day basket membership with weight bars, carrying the mandatory caveat:
  *CMC-selected basket composition, not market churn; entries and exits are index rebalances, not
  market events.*

Both panels ship a tabular equivalent, `role="img"` with `<title>`/`<desc>`, and never encode
meaning by colour alone.

## Accessibility

Palette contrast measured with the WCAG 2.2 relative-luminance formula and asserted by a test.
`prefers-reduced-motion` honoured. Tabular figures on every numeric cell. No chart conveys
meaning by colour alone.

## Tests

47 tests, each one a defect that would otherwise pass silently: auth routing (a key present must
not silently upgrade a keyless call), pager advance, sentinel collision, empty-as-failure, receipt
completeness, alignment policy, determinism, the stdlib-only guard, and the regression guard for
"sigma is measured, never stored".

## Known limitations, stated plainly

- `CMC20 − CMC100` is close to noise because the indices are 99.99% correlated. We show that
  rather than hide it.
- Basket composition is **CMC index reconstitution, not market churn**. Depth starts 2024-01-01.
- Fear & Greed is **Bitcoin-only** and ~30% of its component inputs are paused.
- `listings/historical`, `quotes/historical`, `ohlcv/historical` and `fiat/map` are **not keyless**
  (403/1005), so a keyless build cannot do whole-market churn from them.
- Loopback only. The judged path needs no key, so nothing is required to run it.

*No investment advice. All figures are descriptive, computed from public index data.*



## Read in this order

**Start with `START-HERE.md`.** It carries the event facts the rest of this folder does not state, the
schedule re-based from 2026-09-25, the capture task for the surfaces that stop answering at the close,
and the two decisions to make before writing code.

| # | Doc | Lines | What it is |
|---|-----|-------|------------|
| 0 | `START-HERE.md` | 176 | The event, the cliff, the re-based schedule, the cut list, the two decisions |
| 1 | `docs/concept.md` | 42 | The problem, the four surfaces, what it deliberately is not, the judging map |
| 2 | `docs/blueprint.md` | 53 | The flagship sentence, gallery context, modules M1–M4, the endpoint list |
| 3 | `docs/architecture.md` | 139 | System diagram, the three data products, cache and credit discipline, share pipeline, **target repo layout** |
| 4 | `docs/harden.md` | 235 | The build-ready layer: concrete chart modules with panel/series/visual/takeaway, exact endpoints, Jev gates T1–T6, the template floor, the 7-pack checklist, the build path |
| 5 | `docs/mvp-from-jev-builder.md` | 246 | Keep/change/drop file list, env vars, the data path, Jev gate sketches, a timed 3-minute demo script, judge fallbacks, acceptance checklist |
| 6 | `docs/stack-feasibility.md` | 71 | Jev feasibility, the X share surface, a 6-day path, feasibility verdict, risks |
| 7 | `docs/external-apis.md` | 111 | CMC, Arkham and Alchemy with evidence classes, fit matrix, honesty flags |
| 8 | `docs/jev-workflow-adaptation.md` | 428 | Analysis of the vendored `vendor/jev-workflow-builder`, extract-vs-fork decision, board-to-node map, Apache-2.0 compliance |
| 9 | `docs/jev-workflow-ledger.md` | 328 | Research ledger behind the Jev adaptation, 213 entries |
| 10 | `docs/research-ledger.md` | 338 | Research ledger behind the whole concept, 213 entries |

Total 1,991 lines. `SOURCE-MANIFEST.txt` maps each file to the corpus document it came from, with the
source hash.

## The one-minute version

| Panel | Question it answers | Primary CMC series |
|---|---|---|
| **Regimen** | What kind of market is this index describing? | `/v3/index/cmc20-*`, `/v3/index/cmc100-*`, Fear & Greed, Altcoin Season, global metrics |
| **Rerum** | Who is in the market, and how did membership change? | `/v1/cryptocurrency/listings/historical` against `/v3/cryptocurrency/listings/latest` |
| **Comparativa** | How do two to four assets relate? | `/v3/cryptocurrency/quotes/historical`, `/v2/cryptocurrency/ohlcv/historical`, RWA island |
| **Share as Tab** | How does one finding travel? | PNG board card to an X intent with `#BuildwithCMC` |

The non-obvious claim, in the concept's words at `tabula-rerum/docs/concept.md:18`: the interesting signal is not
"what did price do" but *what kind of market is this index describing?*

## Five gaps to close before building

These are recorded, not fixed. The corpus copies are untouched. `START-HERE.md` carries the missing
event facts and the re-based schedule, which closes gaps 2 and 5 in part.

1. **No test plan.** Zero mentions of unit tests, pytest or vitest across all ten docs. The track scores
   "Does it work" at 30 points and "code quality and documentation" at 15, so this is the most expensive gap.
2. **Four schedules, three date bases, all stale.** `tabula-rerum/docs/stack-feasibility.md:41` uses D1–D6 with no dates;
   `tabula-rerum/docs/mvp-from-jev-builder.md:219` uses Day 1–6 with no dates; `tabula-rerum/docs/harden.md:203` uses 22–30 Sep
   assuming day 0 is 22 Sep; `build/ideas/COMPARE-codice-vs-tabula.md:128` uses day 0–8 from 22 Sep.
   `START-HERE.md` re-bases the same work from 25 Sep with an explicit cut list.
3. **No entry point.** The only run command in ten docs is `npm install && npm run dev` at
   `tabula-rerum/docs/mvp-from-jev-builder.md:166`. There is no CLI or module entry.
4. **The prescribed stack contradicts a repository rule.** `tabula-rerum/docs/stack-feasibility.md:51` and
   `tabula-rerum/docs/harden.md:217` prescribe "Vite + React · ECharts or Observable Plot · thin Node/TS or FastAPI
   proxy". The repository's rule at `build/shared/README.md:5` is "**Stdlib only** for judged path. No
   third-party deps required." No Tabula document mentioned that rule at the time. **RESOLVED 2026-09-27:** the rule wins. The runtime is Python 3.12 stdlib and the tree has been built accordingly - see `TABULA-CONTRACT.md` §3. ECharts was also the library the
   wave-2 stack report rejected as canvas-only and roughly 1000 KB
   (`plan/waves/wave2/agent-w2b-stack-and-vendor-clone.md:127`).
5. **No README existed** before this one, across ten files.

Two smaller ones. Six citations in `docs/research-ledger.md` (`:19`, `:21`, `:25`, `:28`, `:29`, `:30`)
name corpus files by bare basename with no directory, so a reader cannot resolve them. And no document
states what is built, which is why this README says so explicitly.

## What is genuinely covered

Three things I expected to be missing are present. The **feature pack schema** exists as a JSON skeleton
at `tabula-rerum/docs/harden.md:38-49`. The **offline path** is specified with a labelled banner at `tabula-rerum/docs/harden.md:151`
("fixtures for index/F&G/listings historical + template captions + banner `DATA MODE: labeled corpus`").
The **API Feedback quirks** are named at `tabula-rerum/docs/harden.md:194`: "epoch F&G, no RWA history, 1006,
error_code, listings historical params".

## Endpoint claims verified

I checked every endpoint path named across all ten docs against `build/api/openapi.cmc.json`: 29 distinct
real paths, all 29 present verbatim in the artifact, zero invented paths. The one `/v1/rwa/` string is the
warning line at `tabula-rerum/docs/harden.md:110`, not a claim.

## Provenance and boundaries

Every file in `docs/` is a byte-identical copy of a file under `build/ideas/tabula/` or
`build/ideas/HARDEN-tabula.md`, except three whose internal cross-references were rewritten because
`MVP-from-jev-builder.md` was renamed to lowercase to match its sibling filenames. `SOURCE-MANIFEST.txt`
records the hashes. **The corpus files were not modified.**

This folder lives at the repository root. It was placed here rather than under `build/` or `research/`
because the planning run's scope boundary OUT-6 makes those two trees read-only
(`plan/SCOPE-BOUNDARIES.md`, OUT-6).

## Naming warning

Four products in this repository share two names. This folder is **Tabula Rerum** from `build/ideas/tabula`.
A different product, **Tabularium**, is a cost-basis ledger on the Markets track at
`research/ideas/I1-Tabularium/`. They are unrelated. The two trees never cross-reference.