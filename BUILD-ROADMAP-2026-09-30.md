# BUILD ROADMAP — 2026-09-30

**Written after:** full codebase discovery, 3 research waves (6 agents), and independent live
re-verification of the API and of every third-party audit claim.

**Authority.** This file does not replace `TABULA-CONTRACT.md` — it is the contract's *current
state assessment*. Where the two disagree, the contract still wins on *design intent*, but every
point marked **CONTRACT DEFECT** is a case where the contract itself is factually wrong and must
be amended before it can be implemented.

**Everything in P0 is reproducible from this repository, not from a document.**

---

## 0. Current state, measured

| Item | Measured |
|---|---|
| Tests | **47 pass**, but **48 are defined** — one is silently shadowed |
| Source | 11 Python files, 1,782 LOC |
| Runtime deps | **0** — verified: no `pyproject.toml` / `requirements.txt` / `setup.py` |
| Interpreter | **3.12.3** — eleven patch releases behind, predates a published `http.server` fix |
| Live API | reachable keyless, but an unrouted path returns `HTTP 200` + `error_code 500` |
| Offline path | works — this is the product's real strength and must not be traded away |

---

## 1. CONTRACT DEFECTS — the contract is wrong; fix it first

Not opinions. Each was recomputed from the committed fixtures or fetched live today.

| # | Contract says | Reality | Evidence |
|---|---|---|---|
| **C1** | raw CMC20−CMC100 spread is flat: *"mean 7.981, sd 0.177, span 0.520 — 6.5% of the mean"* (`TABULA-CONTRACT.md` §5, `docs/CANONICAL-DATA.md` §5, `START-HERE.md` §0.2) | **span is 2.410 = 33.9% of the mean**, drift **+29.6%** over 70 days | recomputed from `evidence/fixtures/*.json` |
| **C2** | the z-score is the flagship statistic | `rho1 = 0.947`, `r(levels) = 0.999902`. The series has a **unit root**: no stationary distribution, no reference population. A z-score here is a **position**, not a test statistic | recomputed |
| **C3** | palette contrast `series A 5.4:1`, `accent 5.1:1`, `negative 6.1:1` (§14) | measured **6.41 / 4.56 / 7.01**. `rule #d8d6d0` is **1.35:1**, failing WCAG 1.4.11 | WCAG 2.2 relative-luminance formula |
| **C4** | Altcoin Season is a "7-day stub" (`START-HERE.md` §0.1, `CANONICAL-DATA.md` §9) | **`timeframe=90d` returns 90 daily points**, plus a bonus `altcoin_marketcap` field | agent-measured; my re-probe hit `429`, so high-confidence-not-directly-reproduced |
| **C5** | `error_code == 0` is the discriminator (`CANONICAL-DATA.md` §6) | **unrouted paths return `HTTP 200` + `error_code 500` + `"The system is busy"`** — byte-identical to a genuine transient error, so `error_code` alone is ambiguous | **reproduced directly**, 3 probes |
| **C6** | 41 tests, then 47 | 48 defined, 47 run | `re.findall(r"def test_\w+")` |

> **C1 and C2 together are the most important finding here.** The flagship claim rests on a
> measurement that is 5× wrong, and on a statistic that cannot support the inference drawn from
> it. A *provenance* product that prints a mismeasured number is worse than one that prints nothing.

---

## 2. CONFIRMED DEFECTS in shipped code

| # | Defect | Location | Impact |
|---|---|---|---|
| **D1** | `test_window_dropped_when_too_few_points` defined **twice** (lines 253 and 273). The 40-day coverage case at :253 **never runs** | `tests/test_tabula.py` | a test you believe is passing is not running |
| **D2** | bare `<polyline>` emitted over the axis | `packages/share/tabula_share/svg.py:123` | **bridges gaps and shifts x**. The alignment policy requires a gap to render as a gap — the same defect class as the prohibited forward-fill |
| **D3** | no `do_HEAD` → `HEAD /` returns **501** | `apps/api/tabula/server.py` | health-checkers and judges probing the URL get an error |
| **D4** | no `Content-Security-Policy`, no `X-Content-Type-Options: nosniff`, no `Referrer-Policy` | `server.py:_send` | a provenance product shipping an unhardened server |
| **D5** | `log_message` override opts out of the 3.12 control-character scrubbing fix | `server.py:201` | regresses a security fix upstream made |
| **D6** | `Server: BaseHTTP/0.6 Python/3.12.3` discloses the exact build | `server.py` | version disclosure |
| **D7** | F&G fixture is stored **newest-first**; index points use `update_time` but F&G uses `timestamp` | `evidence/fixtures/fng_historical.json` | silent axis inversion if wired as-is |
| **D8** | running **Python 3.12.3** | environment | predates gh-119452 (`http.server` DoS), fixed in 3.12.13 |

---

## 3. The research that changes the product

### 3.1 What the API offers that the project believes it does not have

| Capability | Prior belief | Current truth |
|---|---|---|
| Fear & Greed | 50 recorded points, keyless | `/v3/fear-and-greed/historical`, **~1,189 records from 2023-06-29**. `limit` max **500**. `start` is a **1-based offset**. Field is an **epoch string** |
| Altcoin Season | 7-day stub, unusable | `timeframe=90d` → **90 points**. Params other than `timeframe` are silently ignored |
| listings/historical | usable for churn | **403/1005 keyless** — the membership-churn panel cannot use it. Churn must come from **constituent snapshots** |
| Unknown paths | assumed 404 | **HTTP 200 + `error_code 500`**. Must be detected, not retried |

### 3.2 The statistical correction, in plain terms

- `r(CMC20, CMC100) = 0.999902`. They are the **same asset class**.
- Their **difference** has `rho1 = 0.947` → unit root → **no valid null distribution**.
- So the honest statement is a **percentile rank within the cross-window distribution**, a
  **percentage-point spread**, and a disclosed **`n_eff`** (`sqrt((1+rho)/(1-rho))` = **6.06**
  at `rho=0.947`) — **not** `z = −2.08σ`.
- The Newey–West correction is real but modest **within one series** (1.8–2.0×). The widely
  quoted "70.7 → 3.9" compares the naive t of the *raw* spread to the NW t of the *rebased*
  spread — two different series, so the 18× ratio is an artefact. Do not publish it.
- **Retire the z-score as the headline.** Keep the code; change the caption and the claim.

---

## 4. THE ROADMAP

Priority is by *risk to the claims the product makes*, not by feature appeal.

### P0 — CORRECTNESS (blocking, ~1 day)

Nothing else is worth doing until the product stops misreporting itself.

- [ ] **P0.1** Fix **D1** — rename the shadowed test so both run. Expect 48 tests.
- [ ] **P0.2** Fix **D2** — replace `<polyline>` with explicit path segments that break on `None`.
      Add a test: a gap renders a break, and every later point's x is unchanged. This is the
      single most important new test in the project.
- [ ] **P0.3** Amend **C1/C2** in `TABULA-CONTRACT.md` §5 and `docs/CANONICAL-DATA.md` §5.
      Replace the flatness claim with the measured 33.9% span and the `rho1` figure, and add the
      measured numbers to the acceptance criteria so they cannot silently regress.
- [ ] **P0.4** Add `rho1` and `n_eff` to the `flagship()` return and to the caption.
- [ ] **P0.5** Change the headline statistic to **percentile rank + percentage-point spread**.
      Keep `zscore()` exported and tested — it is a legitimate descriptive tool, just not evidence.
- [ ] **P0.6** Add the unrouted-path discriminator (**C5**): treat `error_code 500` **with no
      `data` key** as `UNROUTED`, not `TRANSIENT`. Never retry it blindly. Test with the exact
      bytes captured today.
- [ ] **P0.7** Fix **C3** — either republish the palette table truthfully or darken `rule` to
      ≥3:1. A provenance product that misreports its own audit fails its thesis.

**Gate:** 48+ tests pass; every number in the caption is recomputed by a test from the fixtures.

### P1 — UNDERSELLING (the product's real advantage, ~1 day)

- [ ] **P1.1** **Wire the Fear & Greed panel (B1).** ~1,189 keyless records exist, not 50. The
      largest available data win. Normalise the descending epoch ordering (**D7**) and label it
      **"Bitcoin Fear & Greed"** — it is BTC-only, and ~30% of its components are paused.
- [ ] **P1.2** **Wire the 90-day Altcoin Season tape.** Relabel it as *"share of the top 50
      (ex-BTC) outperforming BTC over 90d"* — the metric was redefined, so the old "it is a
      circular ratio" criticism no longer applies.
- [ ] **P1.3** **Publish the "where the API got in the way" note.** CMC asked for it and said it
      matters more than any single submission. The material is unusually good: the index
      endpoints are **absent from the track's own suggested menu**; auth failures are **masked
      as `error_code 500 "system is busy"`**; the keyless **`1022`** limit is **undocumented**;
      and keyless calls report `credit_count: 1` with no account. Nobody else has this.

### P2 — SURFACE (what a judge touches, ~1.5 days)

- [ ] **P2.1** Fix **D3/D4/D5/D6** — `do_HEAD`, CSP
      `default-src 'none'; style-src 'unsafe-inline'`, `nosniff`, `Referrer-Policy`, a
      `version_string` override, and stop opting out of log scrubbing.
- [ ] **P2.2** **Window control (B2)** — the server already takes `--days`. Surface it in the UI.
- [ ] **P2.3** **Freeze the rebase date** across all windows and **disclose the window length in
      the axis label**. Free window choice is a multiple-comparisons channel; the honest fix is
      disclosure plus a frozen anchor, not a lock.
- [ ] **P2.4** **Share card (B4)** via host headless Chrome. Chrome **154.0.8037.92** is present
      at `/usr/bin/google-chrome`. Use
      `--headless --screenshot=PATH --window-size=W,H --force-device-scale-factor=1
      --virtual-time-budget=N --hide-scrollbars --no-sandbox --user-data-dir=<temp>`.
      Write HTML to a **temp file** (never a `data:` URL — relative CSS and `<use href="#id">`
      break). Verified achievable: two runs produced byte-identical PNGs. **Do not post-process
      the PNG**; there is no timestamp metadata to strip. **Pin the Chrome major in the docs** or
      a future Chrome silently breaks determinism.
- [ ] **P2.5** Accessibility: add `prefers-contrast: more` and `forced-colors: active` blocks;
      apply `tabular-nums` to the **SVG axis ticks** (currently only on HTML tables); add a
      contrast test with hardcoded expected ratios.

### P3 — CRAFT & HYGIENE (low risk, ~1 day)

- [ ] **P3.1** Add `pyproject.toml` for **dev-only** tooling: ruff 0.16.9, mypy 2.3.1,
      pytest 9.1.1, coverage 7.16.2. **No `[build-system]` table** — its absence is what stops a
      PEP 517 frontend fabricating a wheel. Tooling config is neither a runtime dependency nor
      a build step, so it does not violate `TABULA-CONTRACT.md` §3.
- [ ] **P3.2** Set `lint.select` **explicitly** — ruff 0.16.9's default is 413 rules. Budget one
      commit for the 2026 style-guide reformat (9 of 11 files).
- [ ] **P3.3** Contrast tests with the verified fixture table.
- [ ] **P3.4** Move to **Python 3.13.15+** (or at minimum 3.12.14) — **D8**. 3.12 is in
      **security-only, source-only** status with no further binary installers.

---

## 5. Explicitly NOT doing

| Item | Why |
|---|---|
| Dependency bump to React/Vite/ECharts | `TABULA-CONTRACT.md` §3 rules it. Stdlib-only is enforced by `TestStdlibOnly` and is the product's *does-it-work* guarantee |
| `listings/historical`-based churn panel | **403/1005 keyless.** Use constituent snapshots instead |
| ADF / cointegration p-values | MacKinnon critical values are not reproducible without tables. Claiming them would be untruthful |
| Dark theme | needs a **product decision**, not a build step |
| Retrying `error_code 500` blindly | it is the **signature of a typo**, not a transient |
| `limit=1000` on F&G | the maximum is **500** |
| `z-score` as headline | see **C2** |
| The "70.7 → 3.9" framing | compares two different series; the 18× is an artefact |
| `sqrt((1+2ρ)/(1−ρ))` | wrong formula; the correct lag-1 factor is `sqrt((1+ρ)/(1−ρ))` = **6.06**, not 7.39 |

---

## 6. Strategic read

Two agents independently reached the same uncomfortable conclusion. It should be recorded
rather than argued away.

- The differentiator is **reproducibility**; the rubric's largest scoring block is *"does it
  reveal something genuinely non-obvious."* These are not the same axis.
- **"Reproducibility" is losing its novelty in real time** — three other 2026 submissions make
  the same argument in the same event. By submission #40 it reads as a genre, not a discovery.
- **Zero-credential is a commodity.** CMC markets the keyless API itself and gave all 228
  participants a Startup key. There is no judge for whom "no API key" unlocks anything.
- Stdlib-only is double-edged: it maximises *does-it-work*, but against competitors with Docker,
  Next.js, a credit ledger and a `JUDGE.md`, it can read as **austere rather than elegant**. The
  craft must be visible or it will be read as absence.

**So the most defensible positioning is not "every number has a receipt." It is:**

> **The only submission that measures the market's own claims and shows its work.**
> CMC20 and CMC100 correlate at 0.999902. The "regime spread" is a unit root, so it has no
> equilibrium to deviate from. The unbroadcasted Altcoin Season Index, once you read the
> parameter list, is a 90-day tape — not a 7-day stub. And the API's own failure modes are
> indistinguishable from its transient ones, which is why every figure here ships with the
> receipt that produced it.

That is a **finding**, it is **verifiable by a judge in under a minute**, and it is exactly the
"shows something in the data that was not obvious before" the track description asks for.

---

## 7. Start-here checklist

```bash
cd /home/eya/tabula-rerum
python3 run.py --test          # 47 today; P0.1 should make it 48
python3 run.py                 # offline from fixtures, port 8099
python3 run.py --live          # live keyless CMC
```

First three actions, in order: **P0.1** (fix the shadowed test), **P0.2** (fix the polyline gap
bug), **P0.3** (amend the contract's flatness claim). Then amend `ROADMAP.md`, which is the
single roadmap and currently claims every phase is complete.

---

## 8. Research provenance

Six agents across three waves, plus direct verification by the orchestrator.

| Wave | Agents | Focus |
|---|---|---|
| 1 | Python ecosystem · CMC API forensics | version lifecycle, dev-tooling versions, `http.server` advisories, WCAG 2.2/3.0, headless-Chrome determinism; endpoint inventory, paging caps, error codes, quota |
| 2 | CMC re-verification + statistics · tooling & a11y | live re-probe of every prior claim; Newey–West, effective-n, look-ahead bias; exact ruff/mypy/coverage config, CSP, gzip reproducibility |
| 3 | Competitive intelligence · dataviz & statistics | hackathon rubric and tracks, 87 competing builds, what wins; SVG craft rules, CVD-safe palettes, defensible caption language |

Key sources: official OpenAPI at `pro.coinmarketcap.com/api/documentation/openapi.json`
(1,141,955 bytes, OpenAPI 3.0.3, 110 paths); `coinmarketcap.com/api/documentation/changelog.md`;
WCAG 2.2 §1.4.3/§1.4.11; Newey & West (1987) *Econometrica* 55(3); Okabe & Ito; Machado et al.
(2009) *IEEE TVCG* 15(6); Chrome headless CLI docs.

**Unreproduced but high-confidence:** C4 (Altcoin `timeframe=90d`) — the orchestrator's own
re-probe returned `HTTP 429`, so this rests on the agent's measurement. Re-verify before
amending `START-HERE.md` §0.1 on the strength of it alone.
