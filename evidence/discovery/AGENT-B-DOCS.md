# AGENT-B — DOCUMENTATION / NARRATIVE DISCOVERY REPORT
**Scope:** prose only (root MD/TXT + `docs/`). No source touched, no tests/app run (leader owns execution).
**Date:** 2026-09-30 · **Cwd:** `/home/eya/tabula-rerum` · **Method:** `cat -n`/`grep`/`wc`/`find`/`stat` only.
**Tree census:** 34 project files. Root MD/TXT: README 102, START-HERE 304, TABULA-CONTRACT 225, TABULA-MANIFEST 89, ROADMAP 124, BUILD-HANDOFF 193, BUILD-READINESS-AUDIT 186, SOURCE-MANIFEST.txt 40. `docs/` = 12 files / 2,261 lines. Python = 11 files / 1,782 LOC. `tests/test_tabula.py` = 429 lines / **48 `def test_*`**. Project Markdown = 19 files / **3,484** lines.
**Environment facts used as ground truth:** `git rev-parse` is fatal (no repo) and there is no `.gitignore`; `tabula/` `build/` `vendor/` `plan/` `research/` `audit/` `archive/` `docs/api.md` `docs/implementation.md` do not exist.

---

## 1. PROJECT IDENTITY (≤6 lines)
- TABULA is a **CoinMarketCap data-visualization workspace** whose product is "shareable, non-obvious comparative narratives — not another one-screen screener" (`TABULA-CONTRACT.md:13`, `docs/concept.md:4`).
- Named for the Roman wax tablet: a *tabula* of market *res* (`docs/concept.md:4`); the flagship panel is **Tabula Regimen**, a dual-tape regime comparison (`docs/blueprint.md:26`, `docs/concept.md:18`).
- Audience: readers of a single shareable image/page, not dashboard operators (`docs/concept.md:4`, `docs/stack-feasibility.md:78` "always ship subtitle **Tabula Rerum**").
- Core differentiator is **reproducibility** — every number re-derivable from a keyless API capture (`TABULA-CONTRACT.md:17-19`).
- Hard runtime posture: Python 3.12 **stdlib-only**, `ThreadingHTTPServer` on `127.0.0.1`, **inline SVG**, **no build step** (`TABULA-CONTRACT.md:41-48`).
- Deadline was **30 Sep 2026 23:59 UTC**, stated as "~6 days" / "5 days 21 hours" in docs written 09-26/27 (`docs/concept.md:42`, `docs/stack-feasibility.md:39`, `START-HERE.md:92`).

---

## 2. TABULA-CONTRACT OBLIGATIONS
`TABULA-CONTRACT.md:3` declares itself authoritative and overriding all other docs. "MUST" = imperative/prohibitive or enforced by a named test; "SHOULD" = advisory/optional.

### MUST
| # | Obligation / invariant | file:line |
|---|---|---|
| M1 | Python 3.12, **stdlib only** — no third-party imports | `TABULA-CONTRACT.md:41-43`; enforcement named at `:62-63` (`TestStdlibOnly`) |
| M2 | Serve via `ThreadingHTTPServer` bound to **127.0.0.1 only** | `TABULA-CONTRACT.md:44`, `:169-170` |
| M3 | Charts are **inline SVG**; **no build step**, no bundler | `TABULA-CONTRACT.md:45-46` |
| M4 | `sqlite3` optional only; host headless Chrome is the only external binary | `TABULA-CONTRACT.md:47-48` |
| M5 | External cites must resolve inside this folder (no parent-workspace imports) | `TABULA-CONTRACT.md:51-54` |
| M6 | CMC `count` hard cap **10**; exceeding is an error | `TABULA-CONTRACT.md:96-97` |
| M7 | Timestamps **ISO-8601 with `Z`**, else HTTP 400 | `TABULA-CONTRACT.md:98` |
| M8 | Intervals limited to **5m / 15m / daily** | `TABULA-CONTRACT.md:99` |
| M9 | Retry **only on 429**, max 3 attempts | `TABULA-CONTRACT.md:100` |
| M10 | `200` + `error_code 0` + empty `data` == **FAILURE**, not success | `TABULA-CONTRACT.md:101`; `docs/CANONICAL-DATA.md:85`, `:92-93` ("most important line") |
| M11 | **No reading of an API key from environment** (keyless only) | `TABULA-CONTRACT.md:102` |
| M12 | Alignment policy: INNER join for stats, OUTER for render | `TABULA-CONTRACT.md:115-119`; `docs/CANONICAL-DATA.md:60-67` |
| M13 | **DROP** a series at <95% coverage or <30 usable pairs | `TABULA-CONTRACT.md:120-121`; `docs/CANONICAL-DATA.md:64-65` |
| M14 | **Forward fill is PROHIBITED** and must be test-enforced | `TABULA-CONTRACT.md:125-126`; `docs/CANONICAL-DATA.md:66-67`, `:79` |
| M15 | Sigma threshold is **2.94** — do not use the remembered 3.5 | `TABULA-CONTRACT.md:134-138` |
| M16 | Accessibility is contractual, not aspirational | `TABULA-CONTRACT.md:146-149` |
| M17 | Palette + contrast ratios are fixed values | `TABULA-CONTRACT.md:211-221` |
| M18 | 5 named acceptance criteria must hold | `TABULA-CONTRACT.md:159-165` |
| M19 | **DoD** = ROADMAP exit condition AND suite green; "A phase is not done because a document describes it" | `TABULA-CONTRACT.md:174-175` |
| M20 | Smoke commands (`--live/--port/--days/--test`) must work as documented | `TABULA-CONTRACT.md:68-72` |

### SHOULD / advisory
| # | Obligation | file:line |
|---|---|---|
| S1 | Scope in: comparative narratives, keyless CMC data | `TABULA-CONTRACT.md:23-27` |
| S2 | Scope out (explicitly excluded) | `TABULA-CONTRACT.md:29-35` |
| S3 | Reproducibility framing as the differentiator (positioning, not a check) | `TABULA-CONTRACT.md:17-19` |
| S4 | Ship with subtitle "Tabula Rerum" | `docs/stack-feasibility.md:78` |
| S5 | Jev/LLM narration treated as optional, not required | `docs/architecture.md:103+` (Non-functional section) |

> Note: M1/M5 are the two obligations whose *evidence* the docs claim is a test + "clean-copy run" (`TABULA-MANIFEST.md:84-89`) — see §3/§4 for whether that evidence is machine-checkable.
