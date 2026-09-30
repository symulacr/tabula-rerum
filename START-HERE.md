# START HERE

Read this first, then `docs/concept.md` and `docs/harden.md`. This file carries the four event facts
the rest of the folder does not state, the schedule re-based from today, and the two decisions to make
before writing code.

**As-of:** 2026-09-27 UTC. **Nothing is built yet.** No `tabula/`, `apps/` or `packages/` exists.
**Read §0 first** — it carries live-verified corrections to three claims made elsewhere in this
folder.

## 0. Live-verified corrections (added 2026-09-27)

This folder predates a round of live keyless API probing. **Three claims below are now known to be
wrong or incomplete.** Read this section before building anything from the rest of the folder. All
findings are keyless probes against `https://pro-api.coinmarketcap.com/public-api` with no key
header; evidence is in `docs/api.md` §4a and `audit/data-alignment.md`.

### 0.1 Altcoin Season has no usable history — it is a 7-day stub

`/v1/altcoin-season-index/historical` answers `200` with `data.timeframe = "7d"` and **7 points**,
the oldest exactly 7 days before today. `limit`, `time_start`, `time_end` and `interval` are each
accepted and each **ignored**.

This breaks the reasoning at **line 48** of this file, which marks the dual tape as surviving
"because latest and historical are both keyless". The endpoint **is** keyless, and it **still** has
no history. The dual tape's historical leg must be rebuilt on Fear & Greed plus index history, or
the historical claim dropped. Affects the "dual tape" rows in `README.md`, `blueprint.md:27`,
`harden.md:34`, `:90-93`, `mvp-from-jev-builder.md:180`, `stack-feasibility.md:45`,
`concept.md:22`, and the row at `research-ledger.md:113` whose "historical exists / VERIFIED local"
is false — it was verified against a local catalogue, never against the live endpoint.

Fear & Greed history is unaffected and remains genuinely available.

### 0.2 The flagship spread is flat as specified

CMC20 − CMC100 on raw index values, over 9 daily points: mean **7.981**, sd **0.177**, span
**0.520** — **6.5% of the mean**, because the two indices sit ~170 apart and move nearly in
parallel. The "25-point regime geometry" this folder is built around **does not exist in the raw
data**.

The fix is arithmetic, not plumbing: rebase both to 100, subtract, and plot the y-axis in
**z-score units**. The raw span is **2.94σ**; a separate daily-return series gives **3.46σ**. Do not
mix the two figures, and **print the measured σ at render time** rather than a constant copied from
a document.

### 0.3 Basket composition history is keyless — and this folder never mentions it

Every historical index point carries a per-day `constituents[]` array:

| Index | Constituents/day | Fields |
|---|---:|---|
| `/v3/index/cmc20-historical` | **20** | `id, name, priceUsd, symbol, units, url, weight` |
| `/v3/index/cmc100-historical` | **100** | `id, name, symbol, url, weight` — **no `priceUsd`, no `units`** |

Both indices begin at **2024-01-01** and share a date grid exactly, so a join between them drops
nothing. Earlier notes in this engagement called this "a 20-name capability"; that is true of
**CMC20 only**.

State it accurately: this is **CMC-selected basket composition, not market churn**. Entries and
exits are CMC index rebalances, not market events. This is the strongest keyless differentiator the
API offers and it is the one capability in this folder that is entirely absent.

### 0.4 Paging constraints that bind any multi-month pull

`count` is **hard-capped at 10**; bounds must be **full ISO-8601 with `Z`** (a bare `YYYY-MM-DD`
returns `400`); with both bounds set the window fills **from its start**, ascending, so history must
be walked window by window. `interval` accepts only `5m`, `15m`, `daily`.

**`index_historical_paged` in `build/shared/cmc_client.py` never advances the window**, so
multi-page history is currently broken. Fix design: `audit/client-fix-design.md`; patches (written,
**not applied**): `audit/patches/`.

### 0.5 What this does not change

The `canon` claim at line 40-42 stands: the 30 Sep revert is the free **Startup key → Basic**, and
keyless `/public-api` access is plan-independent. The capture urgency in §3 is about **keyed**
surfaces. That reasoning was already right and is unaffected by the corrections above.

## 1. The event, in full

| Fact | Value | Source |
|---|---|---|
| Event | Build with CMC: API Hackathon, DoraHacks `coinmarketcap-api-202609` | `tabula-rerum/docs/blueprint.md:5` |
| Track | Data and Visualisation, one track only | `tabula-rerum/docs/harden.md:193` |
| Submissions close | **Wed 30 Sep 2026 23:59 UTC** | `build/shared/README.md:4`, `plan/ROADMAP.md:12` |
| **Judging runs** | **Thu 1 Oct to Fri 16 Oct 2026** | `plan/waves/wave1/agent-w1c-event-requirements.md:30` |
| Results | Mon 19 Oct 2026 | `plan/waves/wave1/agent-w1c-event-requirements.md:31` |
| Judging weights | 30 does it work, 25 non-obvious, 20 API use, 15 craft, 10 presentation | `tabula-rerum/docs/concept.md:36` |
| Plan during the event | free Startup tier for participants | `tabula-rerum/docs/research-ledger.md:187` |
| Plan at the close | reverts to free Basic | `plan/ROADMAP.md:12` |

**Remaining time: 5 days 21 hours.** Six working days, Fri 25 Sep through Wed 30 Sep.

Two submission fields are hard gates, not preferences. The live form renders them as
`GitHub/Gitlab/Bitbucket Link Required` and `Demo Video Required`.

The 7-pack contract, item by item, is at `tabula-rerum/docs/harden.md:187-193`: public repo, demo or recording,
X post with the DoraHacks link and `#BuildwithCMC`, named endpoints with versions, code **and** response,
the note on what the API made possible and where it got in the way, and one track selected.

## 2. The cliff, which changes what you build

This is the fact the folder is missing and the one that costs money to discover late. The event Startup
grant lapses at the close, the account reverts to Basic, and **23 surfaces that answer today stop
answering during judging**. A judged artifact that reads live plan-gated endpoints returns 403 with
`error_code` 1006 on a stranger's machine in October.

The repository's own list of what dies is wrong. `build/shared/cmc_client.py:178` names seven entries;
the honest set is 23, derived from the 16 official paths whose plan names carry strike-through marks
(`plan/waves/wave1/agent-w1b-cmc-api-facts.md`, finding 12, and the row-by-row table at
`plan/waves/wave2/agent-w2c-judging-survival-and-hygiene.md:121` onward).

### What this means for Tabula, panel by panel

| Panel | Status after the close | Why |
|---|---|---|
| **M1 Regimen**, CMC20 and CMC100 rebased, differenced, spread in z-score units | **survives** | both index paths are keyless. **But the raw spread is flat** — see §0.2; rebase to 100 and use z-score units |
| **M1 dual tape**, Fear and Greed, Altcoin Season | **partly survives** | F&G latest **and** historical are genuinely keyless. **Altcoin Season "historical" is a 7-day stub** — keyless but historyless. See §0.1 |
| **M1 basket composition** | **survives, and is unused** | `constituents[]` is keyless: 20/day for CMC20, **100/day for CMC100**. No panel in this folder uses it. See §0.3 |
| **M1 dominance path** | **dies** | `/v1/global-metrics/quotes/historical` is not keyless; the `latest` value survives |
| **M2 Rerum**, rank churn from `listings/historical` | **dies** | Startup floor, not keyless. This is M2's spine |
| **M3 Comparativa**, quotes historical, OHLCV, price performance | **dies** | all three are Startup floor |
| **M3 RWA island** | **dies** | RWA is not keyless, and `market-pairs/list` needs Growth |
| **Share as Tab** | **survives** | it renders from cached board state |

So M1 and the share loop are safe. M2's lead surface and all of M3 need captures taken **before
30 Sep 23:59 UTC**, or they cannot be demoed during judging at all.

### The capture task

The writer already exists. `archive_json(obj, path, label)` at `build/shared/cmc_client.py:633` writes
`source`, `archived_at` and `payload`, and `CallReceipt.to_dict()` at `:225` supplies the path, params,
HTTP status, `error_code` and `credit_count` that the 7-pack wants as "code AND response"
(`build/shared/README.md:63`). No new code is needed. What is missing is the destination decision and
the manifest.

Capture these, deepest window the event key allows:

| Priority | Surface | Lands at |
|---|---|---|
| 1 | `/v1/cryptocurrency/listings/historical` | `build/archive/listings_historical/<date>.json` |
| 2 | `/v3/cryptocurrency/quotes/historical` | `build/archive/quotes_historical/<asset>.json` |
| 3 | `/v2/cryptocurrency/ohlcv/historical` | `build/archive/ohlcv/<asset>_<interval>.json` |
| 4 | `/v2/cryptocurrency/price-performance-stats/latest` | `build/archive/price_performance/<date>.json` |
| 5 | `/v5/real-world-assets/{quotes/latest,assets/list,issuers,issuers/list}` | `build/archive/rwa/<name>.json` |
| 6 | `/v1/global-metrics/quotes/historical` | `build/archive/global_historical/<date>.json` |
| 7 | one snapshot per keyless path M1 uses | `build/archive/keyless/<name>.json` |

Priority 7 is cheap insurance rather than a requirement. The keyless catalog survives the revert
because it has no plan, but it has no key either, so its limit is a shared per-IP pool with no
documented error code. Keyless calls cost no credits, so one snapshot each is free.

### The trap in the obvious destination

`out/`, `dist/`, `*.log` and `secrets/` are all git-ignored (`.gitignore:11`, `:10`, `:32`, `:8`). A
capture written into a directory called `out/` looks correct on the machine that made it and never
reaches a judge who clones the repo. The destination must pass one test: `git check-ignore` reports it
trackable and `git ls-files` lists it after the commit. `build/archive/` passes; `out/` does not.

### The offline rule

`CMC_MODE=fixtures` opens no socket. Every capture carries its `archived_at` and its original HTTP
status, and the UI renders the archive timestamp. The vocabulary is `live`, `fixture`, `archive`, and a
fixture is never presented as live (`build/shared/cmc_client.py:636`). Note the gap: a capture taken
during the window is honestly labelled live at capture time and is a stale archive by October, so the
fix is to render `archived_at` rather than to relabel the file. The banner is specified at
`tabula-rerum/docs/harden.md:151`.

## 3. The schedule, re-based from today

The folder's four schedules all assume today is 22 September (`tabula-rerum/docs/harden.md:203` uses day 22, and the
COMPARE calendar starts at day 0 on 22 Sep). They are three days stale. This is the same work re-based
from 25 September, with the cliff capture pulled forward because it has a hard external deadline.

| Day | Date | Work | Exit gate |
|---|---|---|---|
| 1 | **Fri 25 Sep** | Freeze the stack. Scaffold. CMC client and keyless smoke test. **Begin the archive capture.** | One live call from the server; `archive_json` writes a file that `git ls-files` lists |
| 2 | Sat 26 Sep | **M1 Regimen**: rebase CMC20 and CMC100, difference, z-score spread | The panel renders from named endpoints, with an endpoint footer |
| 3 | Sun 27 Sep | Finish the tape. **The archive capture must be complete today.** | Captures committed; `manifest.json` lists one row per capture |
| 4 | Mon 28 Sep | **M2 Rerum**: membership bump and churn entropy, read from captures | Top-N on date D works with no network |
| 5 | Tue 29 Sep | Template narrative, PNG tab, `/evidence` page, 7-pack, demo recording | Submit-ready |
| 6 | **Wed 30 Sep** | Deploy. Verify the repo link resolves logged out. Submit. | Submitted before 23:59 UTC |

M3 Comparativa and the RWA island are **not** on this schedule. There is no room for them in six days
alongside the capture task, and they are the most cliff-exposed panels.

### Cut list, in order

If a day slips, cut in this order and no other:

1. **M3 Comparativa and the RWA island.** Already cut above. Frees day 4 entirely.
2. **The category treemap.** Keeps the membership bump and churn entropy, which are M2's actual claim.
3. **The Jev gates.** The template floor is already the shipping path, so this costs captions polish only.

Never cut: M1 Regimen, the archive capture, the `/evidence` page, the 7-pack, the demo recording. Those
five carry the 30-point work criterion, the 20-point API criterion and the submission contract.

## 4. Two decisions before writing code

**Decision one: the stack.** The repository's rule at `build/shared/README.md:5` is "**Stdlib only** for
judged path. No third-party deps required." The folder prescribes the opposite at
`tabula-rerum/docs/stack-feasibility.md:51` and `tabula-rerum/docs/harden.md:217`: Vite, React, ECharts or Observable Plot, and a
Node or FastAPI proxy. Neither document mentions the rule, so the two were never reconciled.

- **Option A, follow the rule.** Python standard library, `http.server.ThreadingHTTPServer` as the
  proxy, server-built HTML with hand-written inline SVG, stdlib `sqlite3`, and the host's headless
  Chrome for the PNG card. This is the stack the wave-2 report chose and costed
  (`plan/waves/wave2/agent-w2b-stack-and-vendor-clone.md:125`, `:127`). It costs no install step and no
  bundle.
- **Option B, take the exception.** Keep the folder's stack, and record the exception in writing with
  its reason, because a rule broken silently is worse than a rule changed deliberately. Note the cost:
  the wave-2 report measured ECharts at about 1000 KB against uPlot's 47.9 KB in uPlot's own benchmark,
  and chose hand-written inline SVG as the only charting option with zero install and full screenshot
  fidelity (`plan/waves/wave2/agent-w2b-stack-and-vendor-clone.md:299`, `:349`).

Option A is the lower-risk path for a six-day build, and it is the only one that keeps the judged path
install-free.

**Decision two: where captures land.** `build/archive/`, verified trackable, or a directory that
`git check-ignore` rejects. This one is not a preference. See section 2.

## 5. What is genuinely ready, and what is not

Ready: the concept, the chart modules with per-panel series and takeaways (`tabula-rerum/docs/harden.md:27-78`), the
endpoint list (29 real paths, all present verbatim in `build/api/openapi.cmc.json`, zero invented), the
feature pack schema (`tabula-rerum/docs/harden.md:40-49`), the offline path (`tabula-rerum/docs/harden.md:151`), the API Feedback
quirks (`tabula-rerum/docs/harden.md:194`), the 7-pack checklist, and the timed demo script
(`tabula-rerum/docs/mvp-from-jev-builder.md:164` onward).

Not ready, and worth fixing before day 4 rather than after:

1. **No test plan.** Zero mentions of unit tests across the ten docs, while the track scores "Does it
   work" at 30 points and "code quality and documentation" at 15. The lot-free path is to test the
   derived series (rebase, spread, churn entropy) as pure functions over committed fixtures.
2. **No entry point.** The only run command in the folder is `npm install && npm run dev`
   (`tabula-rerum/docs/mvp-from-jev-builder.md:166`). Pick the package name and the run command on day 1.
3. **Six citations in `docs/research-ledger.md`** (`:19`, `:21`, `:25`, `:28`, `:29`, `:30`) name corpus
   files by bare basename with no directory, so a reader cannot resolve them.
4. **No document states what is built.** This file says it: nothing.

## 6. Provenance

Every file in `docs/` is a byte-identical copy of a file under `build/ideas/tabula/` or
`build/ideas/HARDEN-tabula.md`, except three whose internal cross-references were rewritten when
`MVP-from-jev-builder.md` was renamed to lowercase. `SOURCE-MANIFEST.txt` records the hashes. The corpus
was not modified.

**Naming warning.** This folder is Tabula Rerum from `build/ideas/tabula`. A different product,
Tabularium, is a cost-basis ledger on the Markets track at `research/ideas/I1-Tabularium/`. The two are
unrelated and their trees never cross-reference.
---

## 6. AUTHORITATIVE DOCUMENT HIERARCHY (added 2026-09-27)

**Conflict rule: the higher document wins. A lower document never overrides a higher one, however
recent it looks.**

```
START-HERE.md              entry point; live corrections (§0) and open decisions (§4)
  ↓
TABULA-CONTRACT.md         THE implementation contract: product, scope, runtime, APIs,
                           data, alignment, rendering, tests, acceptance, DoD
  ↓
docs/architecture.md       system shape and the (now built) layout
  ↓
docs/CANONICAL-DATA.md     data shape, paging rules, alignment policy, error semantics
  ↓
docs/TEST-AND-ACCEPTANCE.md  verification and pass conditions
  ↓
ROADMAP.md                 the single roadmap
  ↓
docs/harden.md, docs/blueprint.md, docs/mvp-from-jev-builder.md,
docs/stack-feasibility.md, docs/external-apis.md      design detail
  ↓
docs/jev-workflow-*.md, docs/research-ledger.md       historical: how we got here
```

**If two documents disagree, the one higher in this list is current.** Anything marked
`SUPERSEDED` is retained for provenance and must not be followed. Historical ledgers record what
was believed at the time and are not specifications.

## 7. WHAT CHANGED ON 2026-09-27

The two decisions in §4 are now closed, and the project is built.

| Was | Now | Ruled by |
|---|---|---|
| Stack undecided: stdlib vs React/Vite | **Python 3.12 stdlib.** The folder's React/Vite/ECharts prescription is **superseded** | `IN-5`, `build/shared/README.md:5`, `SPEC.md:43-47` |
| Build tree specified at a `tabula/` root that did not exist | **Built inside this folder** | `TABULA-CONTRACT.md` §3 |
| No test plan | **41 tests, all passing**, each parent defect covered | `docs/TEST-AND-ACCEPTANCE.md` |
| No canonical dataset | **Defined**, with the alignment policy decided and forward-fill prohibited | `docs/CANONICAL-DATA.md` §5 |
| 63 external references to the parent workspace | **Zero required** — proven by a clean-copy run with no parent on the path | `BUILD-READINESS-AUDIT.md` |
| The parent CMC client (6 defects) | **Re-implemented clean**; no defective code copied | `apps/api/tabula/client.py` |

**Run it:**

```bash
python3 run.py            # offline from fixtures, no key, no network
python3 run.py --live     # live keyless CMC
python3 run.py --test     # 41 tests
```

Start at `TABULA-CONTRACT.md`. `START-HERE.md` §0 still holds the live API corrections, and those
are unchanged.
