# ROADMAP

**The single roadmap for this project.** It supersedes the schedules in
`docs/mvp-from-jev-builder.md`, `START-HERE.md` §6, and any dated plan in the parent workspace.
Where those disagree, this file is current.

Each phase states its completion condition. A phase is not complete because a document says so.

---

## PHASE 0 — FOUNDATION ✅ COMPLETE

- **Objective:** decide the runtime, create a real build root, and establish a command that runs.
- **Inputs:** `IN-5` and `SPEC.md:43-47` (runtime), `architecture.md:86-95` (layout).
- **Outputs:** `TABULA-CONTRACT.md`, build tree under `tabula-rerum/`, `run.py`.
- **Dependencies:** none.
- **Verification:** `python3 run.py --test` executes.
- **Completion condition:** a single command starts the app from a clean checkout. **Met.**

## PHASE 1 — DATA / CMC ✅ COMPLETE

- **Objective:** a keyless CMC client that cannot silently lie.
- **Inputs:** the parent client, plus its six confirmed defects.
- **Outputs:** `apps/api/tabula/client.py`, recorded fixtures in `evidence/fixtures/`.
- **Dependencies:** Phase 0.
- **Verification:** tests for D7 auth routing, E1 pager advance, E3 sentinel collision, E4 path, E5
  empty-data, E6 receipts. Live capture walked 70 points per index with **0 duplicate timestamps**.
- **Completion condition:** the client never reads a credential from the environment, prefers the
  keyless route unconditionally, and classifies `200/0/[]` as a failure. **Met.**

## PHASE 2 — TRANSFORMATIONS ✅ COMPLETE

- **Objective:** a canonical dataset and a decided alignment policy.
- **Inputs:** `docs/CANONICAL-DATA.md`, the alignment analysis.
- **Outputs:** `packages/features/tabula_features/{align,transforms}.py`.
- **Dependencies:** Phase 1.
- **Verification:** determinism test, inner/outer join tests, coverage-drop test, forward-fill
  prohibition test, and the "sigma is measured not stored" regression guard.
- **Completion condition:** no undefined dataset, no "TBD" in the policy, and forward-fill absent
  from shipped code. **Met.**

## PHASE 3 — VISUALIZATION ✅ COMPLETE (Regimen panel + composition panel)

- **Objective:** render the corrected flagship chart server-side.
- **Inputs:** Phase 2 output.
- **Outputs:** `packages/share/tabula_share/svg.py`.
- **Dependencies:** Phase 2.
- **Verification:** smoke test confirms `<svg>`, `role="img"`, `<desc>`, and a table on the page.
- **Completion condition:** the chart renders with no browser and no chart library. **Met.**
- **Phase 3b — composition panel: ✅ COMPLETE 2026-09-27.** `packages/share/tabula_share/composition.py`, 6 tests, caveat rendered on the panel. No longer deferred.

## PHASE 4 — UX / ACCESSIBILITY ✅ COMPLETE (baseline)

- **Objective:** make the board legible and accessible from the first render.
- **Outputs:** semantic palette, Georgia-based classical type, tabular figures, responsive rules,
  `prefers-reduced-motion` honoured, focus-visible styling, dark-mode deferred.
- **Dependencies:** Phase 3.
- **Verification:** every chart ships a table fallback; direction is stated in words.
- **Completion condition:** no chart conveys meaning by colour alone. **Met.**

## PHASE 5 — PROVENANCE / RECEIPTS ✅ COMPLETE

- **Objective:** make every number traceable.
- **Outputs:** `Receipt` dataclass, provenance table on the page, `capture_envelope` semantics.
- **Dependencies:** Phase 1.
- **Verification:** receipt field test; fixtures are distinguishable from live captures.
- **Completion condition:** each call records endpoint, params, auth mode, error code, credits,
  latency. **Met.**

## PHASE 6 — TESTING ✅ COMPLETE (47 tests)

- **Objective:** no regression can pass silently.
- **Outputs:** `tests/test_tabula.py`, `docs/TEST-AND-ACCEPTANCE.md`.
- **Dependencies:** Phases 1–5.
- **Verification:** 47/47 passing, including 6 for the composition panel.
- **Completion condition:** every parent defect has a named test that fails without its fix.
  **Met.**

## PHASE 7 — DEPLOYMENT ⬜ NOT REQUIRED FOR MVP (operator action)

- **Objective:** a public HTTPS URL, if one is wanted.
- **Blocked on:** an operator action. Not a build prerequisite, and not a code task.
- **Completion condition:** the static build is served and reachable.
- **Note:** the judged path needs no key, so nothing here is required to submit.

## PHASE 8 — FINAL VERIFICATION ✅ COMPLETE

- **Objective:** clean-environment proof, then the readiness audit.
- **Verification:** copy the folder alone to a temporary directory, with the parent workspace off
  the path, and run the suite plus a server smoke test.
- **Completion condition:** everything passes from the copy. **Tracked in
  `BUILD-READINESS-AUDIT.md`.**

---

## Deferred, with reasons

| Item | Why deferred |
|---|---|
| Dark mode | **Proven NOT REQUIRED FOR MVP**: `TABULA-CONTRACT.md` §9 specifies a single classical ground. Adding a second theme is a design decision that needs a product owner, not a build step. The wax ground in `architecture.md:103` was already rejected on measured contrast. |
| Fear & Greed tape | 50 points recorded. **Proven NOT REQUIRED FOR MVP**: `TABULA-CONTRACT.md` §2 scopes the MVP to Regimen + composition. Wiring it is a product decision, not a build prerequisite. |
| Board Lab canvas | **Rejected**, negative ROI, and refuted on type grounds. |
| AI assistance | Optional and last. The keyless path must work with no credentials. |
| Keyed capture | **Proven NOT REQUIRED FOR MVP**: the judged path is keyless by design, and `IN-5` puts the proxy on loopback. A key's presence in an environment is not authorisation. |


---

## BUILD PHASE — what the implementation agent does next

Phases 0-6 and 8 are complete. Nothing below is a re-do of existing work. Start from
`BUILD-HANDOFF.md`.

| # | Work | Why it is next | Gate |
|---|---|---|---|
| B1 | Panel for Fear & Greed | 50 keyless points are already recorded; the data contract is done | tests pass, table fallback, receipt shown |
| B2 | Window control in the UI | the server takes `--days`; surfacing it completes the "user-chosen window" promise in the contract | accessible control, no colour-only state |
| B3 | Composition for CMC20 as well as CMC100 | the renderer already handles both schemas | 6 composition tests extended |
| B4 | Share card via host headless Chrome | `SPEC.md:47` already specifies it; needs a script | reproducible PNG, no new dependency |
| B5 | Dark theme | **needs a product decision first.** Single-ground by design today | contrast measured, both themes pass |
| B6 | Public hosting | **operator action**, not a build task | reachable URL |

**Not to be built**, and why — see `TABULA-CONTRACT.md` §2 and §14:
node canvas · collaboration · LLM dependency · any keyed endpoint in the judged path.
