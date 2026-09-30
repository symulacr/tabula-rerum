# TABULA MANIFEST

Every file, what it is for, and whether a build needs it. Read this to navigate without any prior
knowledge of this project.

**10 Python files · 1,653 LOC (390 of it tests) · 17 Markdown files · 3 fixtures · 41 tests, all
passing.** Zero required external dependencies.

---

## Start here

| File | Purpose | Needed to build? | Authoritative? |
|---|---|:-:|:-:|
| `START-HERE.md` | Entry point. §0 live API corrections, §6 document hierarchy, §7 what changed | read | yes, for orientation |
| **`TABULA-CONTRACT.md`** | **The implementation contract.** Product, scope, runtime, APIs, data, alignment, rendering, JEV ledger, palette, acceptance | **yes** | **yes — the contract** |
| `ROADMAP.md` | The single roadmap, 9 phases with completion conditions | **yes** | yes |
| `docs/CANONICAL-DATA.md` | Dataset shape, paging rules, alignment policy, error semantics | **yes** | yes |
| `docs/TEST-AND-ACCEPTANCE.md` | Test layers, 22 acceptance criteria with pass conditions | **yes** | yes |
| `BUILD-READINESS-AUDIT.md` | Readiness state, evidence, remaining non-blocking gaps | read | current state |

## Run it

| File | Purpose | Needed to build? | Authoritative? |
|---|---|:-:|:-:|
| `run.py` | Entry point: dev server, `--live`, `--port`, `--days`, `--test` | **yes** | yes |
| `tests/test_tabula.py` | 41 tests covering every parent defect, the alignment policy, determinism, a11y, stdlib-only | **yes** | yes |

## Implementation

| File | LOC | Purpose | Needed to build? | Authoritative? |
|---|---:|---|:-:|:-:|
| `apps/api/tabula/client.py` | ~430 | CMC client. Keyless-first routing, the 10-point cap, ISO bounds, empty-as-failure, receipts, window walk | **yes** | yes |
| `apps/api/tabula/server.py` | ~250 | `ThreadingHTTPServer` on loopback, HTML page, `/healthz`, `/api/regimen` | **yes** | yes |
| `packages/features/tabula_features/align.py` | ~150 | Canonical `Series`, `Window`, the alignment policy, inner/outer joins | **yes** | yes |
| `packages/features/tabula_features/transforms.py` | ~180 | `rebase`, `difference`, `zscore`, `rolling_volatility`, the flagship computation | **yes** | yes |
| `packages/share/tabula_share/svg.py` | ~210 | Server-side inline SVG with the a11y contract, plus the table fallback | **yes** | yes |
| `apps/api/tabula/__init__.py` | 2 | package marker | yes | no |
| `packages/features/tabula_features/__init__.py` | 1 | package marker | yes | no |
| `packages/share/tabula_share/__init__.py` | 1 | package marker | yes | no |

## Evidence

| File | Purpose | Needed to build? | Authoritative? |
|---|---|:-:|:-:|
| `evidence/fixtures/cmc20_historical.json` | 70 recorded daily points, 20 constituents each | **yes** — the offline default | yes |
| `evidence/fixtures/cmc100_historical.json` | 70 recorded daily points, 100 constituents each | **yes** | yes |
| `evidence/fixtures/fng_historical.json` | 50 recorded points. Recorded but not yet wired to a panel | no | yes |

All three were captured **keyless with no key header**. They carry no provenance block, so a
recorded capture can never masquerade as a live one.

## Design detail (read as needed)

| File | Purpose | Needed to build? | Authoritative? |
|---|---|:-:|:-:|
| `docs/concept.md` | The product idea and the non-obvious claim | read | design |
| `docs/blueprint.md` | System shape in prose | read | design |
| `docs/architecture.md` | Layout and data flow. Its §9 JEV adaptation remains current; its React tree is **superseded** | read | partly |
| `docs/harden.md` | Per-panel series, takeaways, offline path, API quirks. Its **Stack** line is **superseded** | read | partly |
| `docs/external-apis.md` | Endpoint inventory. Altcoin `historical` corrected to "7-day stub" | read | partly |
| `docs/mvp-from-jev-builder.md` | The original MVP sequencing. Partly superseded by `ROADMAP.md` | read | historical |
| `docs/stack-feasibility.md` | Feasibility study. Its **Stack** line is **superseded** | read | historical |
| `README.md` | Folder overview. The stdlib contradiction is marked **RESOLVED** | read | partly |

## Historical (do not build from these)

| File | Purpose | Needed to build? | Authoritative? |
|---|---|:-:|:-:|
| `docs/jev-workflow-adaptation.md` | The extract-vs-fork analysis. Its conclusions are current; its breadth-tape row is corrected | no | historical |
| `docs/jev-workflow-ledger.md` | JEV research ledger | no | **no** |
| `docs/research-ledger.md` | Claim provenance. Row 113 is **retracted in place** | no | **no** |
| `SOURCE-MANIFEST.txt` | Maps the original 10 docs to their internal sources | no | **no** |

## Superseded — retained for provenance, must not be followed

| Claim | Where | Ruled by |
|---|---|---|
| Vite + React + ECharts + Node/FastAPI proxy | `docs/harden.md:217`, `docs/stack-feasibility.md:51` | `TABULA-CONTRACT.md` §3 |
| `tabula/` build tree at a non-existent root | `docs/architecture.md` §Repo layout | `TABULA-CONTRACT.md` §3 |
| Altcoin Season as a historical tape | `README.md`, `blueprint.md`, `harden.md`, `concept.md`, `mvp-from-jev-builder.md`, `stack-feasibility.md`, `architecture.md`, `jev-workflow-adaptation.md`, `external-apis.md` | `docs/CANONICAL-DATA.md` §9 |
| Raw CMC20−CMC100 spread as the flagship | `blueprint.md:27` and 9 other files | `docs/CANONICAL-DATA.md` §5 |
| "16-asterisk placeholder" in the CMC client | retracted 2026-09-27 | `START-HERE.md` §0 |

## Where the parent workspace is still cited

Documentation cites `build/shared/`, `plan/`, `research/` and `vendor/` for **provenance** — to show
which ruling came from where. **No shipped code imports from outside this folder**, and this is
enforced by `TestStdlibOnly` and proven by a clean-copy run with the parent off the path.
