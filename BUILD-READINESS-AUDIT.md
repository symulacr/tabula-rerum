# TABULA BUILD-READINESS AUDIT — FINAL

**2026-09-27.** The third and final audit under this name. The first was **NOT BUILD-READY**; the
second was **BUILD-READY**; this one **re-verified every claim independently** rather than accepting
it, and closed the gaps that were still open.

## FINAL VERDICT

# BUILD-READY WITH EXPLICIT NON-BLOCKING ITEMS

Seven of the eight previously-reported gaps are now **closed** — one by building it, six by proving
it is **not required for MVP**. One item remains and is an **owner decision no agent can close**.

---

## Independent re-verification

Every claim from the previous pass was treated as untrusted and re-proven.

| Check | Result | Evidence |
|---|---|---|
| Runtime | **PASS** | `IN-5` + `build/shared/README.md:5` + `SPEC.md:43-47`; contract §3; stdlib-only enforced by `TestStdlibOnly` |
| Build root | **PASS** | `tabula-rerum/` exists and is the build root; the old `tabula/` path marked superseded |
| Standalone | **PASS** | isolated copy, **scrubbed environment** (`env -i`), 47/47; no absolute paths; every `open()` project-relative |
| CMC client | **PASS** | 6 defects re-checked, each with a named test |
| CMC auth routing (D7) | **PASS** | three-way proof below |
| Pager (E1) | **PASS** | live proof below |
| Canonical data | **PASS** | `docs/CANONICAL-DATA.md`; 190 recorded points; schema asymmetry explicit |
| Alignment | **PASS** | decided, implemented, forward-fill prohibited **and enforced by test** |
| Tests | **PASS** | 47/47, in-tree and isolated |
| Acceptance criteria | **PASS** | 22 criteria, `docs/TEST-AND-ACCEPTANCE.md` |
| Documentation | **PASS** | full sweep below; one contract, one roadmap |
| Roadmap | **PASS** | `ROADMAP.md` is the only one; phases + explicit BUILD PHASE |
| Clean-room build | **PASS** | see below |
| Secret safety | **PASS** | no key-shaped literals, **no env reads**, keyless URL + no key header proven |

### D7, re-proven three ways

```
key ABSENT  + keyless endpoint -> keyless
key PRESENT + keyless endpoint -> keyless          <- the defect, fixed
key PRESENT + keyed endpoint, authorized   -> keyed
key PRESENT + keyed endpoint, unauthorized -> none
env access in CmcClient: NONE
keyless path with key present: receipt.auth_mode=keyless, headers sent = [Accept, User-Agent]
```

The last line matters most: with a key present, a keyless request still goes to `/public-api` with
**no key header**, and the receipt records `keyless`. Provenance cannot lie about where data came
from.

### Pager (E1), re-proven live against the real API

```
pages requested : 5  (bounded by max_pages=5)
points returned : 50
duplicates      : 0
ascending       : True
daily gaps      : 0
first/last      : 2026-08-08 .. 2026-09-26
auth modes      : ['keyless']
error codes     : ['0']
```

Bounded, contiguous, no duplicates, no skipped window, terminated correctly.

### Clean-room proof

Isolated `mktemp` directory, sibling resources absent, **environment scrubbed** (`env -i`):

```
47 tests ... OK
GET /healthz     -> {"ok": true, "offline": true}
GET /            -> 200, 16,373 bytes
GET /api/regimen -> 200, analysable=True n=70 coverage=1.000 auth=['none']
GET /nope        -> 404
```

Page verified in isolation: `<svg>`, `role="img"`, `<desc>`, `table.fallback`, the composition
panel, the *not market churn* caveat, and the provenance table.

---

## Gaps closed this pass

| # | Gap | How closed |
|---|---|---|
| 1 | Composition panel not built | **BUILT.** `packages/share/tabula_share/composition.py`, wired into the page, **6 new tests** (41 → 47). Renders 100 CMC100 constituents with weight bars, the schema-asymmetry note, and the mandatory caveat |
| 2 | Fear & Greed not wired | **PROVED NOT REQUIRED FOR MVP.** Contract §2 scopes the MVP to Regimen + composition. 50 points remain recorded; wiring is a product decision |
| 3 | Dark mode | **PROVED NOT REQUIRED FOR MVP.** §9 specifies a single classical ground. A second theme is a design decision needing a product owner. The wax ground in `architecture.md:103` was already rejected on measured contrast |
| 4 | Light theme rejected | **CLOSED** — documented with the measured reason in the palette section |
| 5 | Dark-mode contrast verification | **PRECEDENT** — follows from 3 |
| 6 | Public HTTPS | **PROVED EXTERNAL.** Operator action. The judged path is keyless |
| 7 | Keyed capture | **PROVED NOT REQUIRED FOR MVP.** Keyless by design; `IN-5` puts the proxy on loopback. A key's presence in an environment is not authorisation |
| 8 | Container queries partial | **NOT A GAP** — one media query is what the current two panels need; the pattern is recorded in the JEV ledger |

**No feature was built merely to tick a box.** One gap was real and got built; six were scope
questions and got answered with evidence.

---

## Track conflict — re-verified

| Question | Answer |
|---|---|
| Does it affect **implementation**? | **No.** The build is complete and self-contained |
| Does it affect **submission**? | **Yes** |
| Is an amendment required? | **Yes**, to `IN-1`/`OUT-1` in `plan/SCOPE-BOUNDARIES.md`, which name Códice Agentum on AI Agents and Automation. This folder is Tabula Rerum on Data and Visualisation |
| Can an agent make it? | **No.** Protected files; no agent may amend them unilaterally |

**OWNER DECISION REQUIRED — one only.** Submitting Tabula on Data and Visualisation requires an
amendment to the protected contract. It blocks no further implementation work.

---

## Documentation reconciliation

| Category | Live contradictions | Action |
|---|---|---|
| React / Vite / ECharts as a prescription | **0** | remaining mentions are SUPERSEDED markers, DISCARD decisions, or accurate descriptions of the reference clone |
| Altcoin `historical` as a usable source | **0** | 9 locations corrected; remaining hits are the correction itself or a historical search log |
| Raw spread as the flagship | **0** | substance corrected in 8 files; "spread ribbon" survives only as a panel *name* |
| Competing roadmaps | **0** | `ROADMAP.md` is the only one |
| Retracted claims live | **0** | the `16-asterisk` finding appears nowhere as a defect |
| Duplicate authorities | **0** | conflict rule in `START-HERE.md` §6; the contract overrides all |

---

## A bug found and fixed during this pass

Not carried from the previous pass — surfaced in this one. The composition work made it obvious that
`walk_window()`'s termination condition fired on a fully-populated window, so it stopped after one
page. The earlier live capture had masked it because the shell loop paged manually. Fixed; the
pager now returns 50 points over 5 bounded contiguous pages with 0 duplicates and 0 gaps.

---

## Final integrity check

| Item | Result |
|---|---|
| Protected files | **7/7 byte-identical to HEAD** |
| OUT-6 guard | **0** unexpected diffs in `research/` or `build/` |
| Verifier gate | **153 pass / 5 fail — unchanged.** step 7 still names only the original four root paths |
| Allowlist | not widened. All new entries match the existing `?? tabula-rerum/` prefix |
| Keyed calls | **none.** All live verification was keyless with no key header |
| Secrets | none in shipped code; no env reads |
| Unauthorized deps | **0** |

---

```
BUILD CAN START: YES
STANDALONE: YES

RUNTIME:          Python 3.12, standard library only (no build step, by design)
PROJECT ROOT:     tabula-rerum/
DEV COMMAND:      python3 run.py            ( --live  --port N  --days N )
TEST COMMAND:     python3 run.py --test     47 tests
BUILD COMMAND:    none
CMC STRATEGY:     existing client re-implemented and defect-fixed; keyless-first; never reads env
CANONICAL DATASET: docs/CANONICAL-DATA.md   (update_time, not timestamp)
ALIGNMENT:        inner join for stats · outer for render · drop <95% or <30 pts · forward-fill PROHIBITED
ROADMAP:          ROADMAP.md                (the only one; phases + BUILD PHASE)
BUILD HANDOFF:    BUILD-HANDOFF.md
TEST/ACCEPTANCE:  docs/TEST-AND-ACCEPTANCE.md   22 criteria
DEFINITION OF DONE: ROADMAP completion condition AND suite passing

SIZE: 11 Python files / 1,782 LOC · 19 Markdown / 3,515 LOC · 34 files · 47 tests passing

BLOCKERS: 0

OWNER DECISIONS:
  1. Track amendment — IN-1/OUT-1 authorise Códice on AI Agents and Automation; this is Tabula on
     Data and Visualisation. Protected files; no agent may amend. Does not block implementation.

NON-BLOCKING ITEMS:
  - public HTTPS hosting                  (operator action; keyless judged path does not need it)
  - dark theme                            (needs a product decision; single-ground by design)
  - Fear & Greed panel                    (50 points recorded; product decision, not a data gap)
  - window control in the UI              (server supports --days; BUILD PHASE B2)
  - CMC20 composition panel               (renderer handles both schemas; BUILD PHASE B3)
  - share card via host headless Chrome   (BUILD PHASE B4)
```

**TABULA IS READY FOR THE BUILD / IMPLEMENTATION PHASE.**
