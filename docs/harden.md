# HARDEN — Tabula Rerum

**Agent:** RS · **As-of:** 2026-09-22 UTC  
**Track (one only):** Data and Visualisation  
**Product name stays:** **Tabula** / Tabula Rerum (Roman wax board of market *res*)  
**Deadline:** 30 Sep 2026 23:59 UTC  
**Evidence:** VERIFIED | INFERRED | UNVERIFIED · no invented endpoints · no keys · no winner ranking  

---

## 0. Deltas from current blueprint

| # | Delta | Why |
|---|-------|-----|
| H1 | Concrete **chart modules** (not just M1–M4 names) + data contracts | 25-pt non-obvious + craft 15 |
| H2 | **Named CMC endpoints with versions** (no invention) | 20-pt API |
| H3 | **Jev gates** on feature-pack JSON (regime / predicates / caption filters) | User: “only with Jev” |
| H4 | **Public-LLM + template** narrative fallbacks | Waitlist + offline judges |
| H5 | **Twitter artifacts** PNG tab + intent vs auto-post | Share loop |
| H6 | Arkham / Alchemy as **optional side data** only | CMC remains primary |
| H7 | **7-pack checklist** | Ship discipline |

**Non-goals unchanged:** not a one-screen screener · not an agent/trading bot · not RWA-only · not Arkham-first.

---

## 1. Chart modules (concrete)

### M1 — Tabula Regimen (regime geometry) **[25-pt lead]**

| Panel | Series (CMC) | Visual | One takeaway |
|-------|--------------|--------|--------------|
| Regime meter | `/v3/index/cmc20-latest` + `cmc20-historical`, `/v3/index/cmc100-latest` + `cmc100-historical` | Rebase both to 100; **spread ribbon** (CMC20 − CMC100) filled | “What kind of market is this index describing?” |
| Dual tape | `/v3/fear-and-greed/latest` + `historical` (Altcoin Season *latest* only - its `historical` is a 7-day stub), `/v1/global-metrics/quotes/historical` (BTC/ETH dominance) | Stacked normalized tapes on **one time axis** | Sentiment ↔ breadth ↔ dominance co-move |
| Auto-caption | feature pack JSON | 1 takeaway sentence (template/Jev/LLM) | Regime label stamped |

**Feature pack (JSON) — input to Jev:**
```json
{
  "spread_now": 0.0,
  "spread_delta_7d": 0.0,
  "spread_widening": true,
  "fg_value": 0,
  "fg_delta_7d": 0,
  "altseason": 0,
  "btc_d": 0.0,
  "churn_entropy": 0.0,
  "window": "30d"
}
```

### M2 — Tabula Rerum (composition churn) **[non-obvious]**

| Panel | Series | Visual | One takeaway |
|-------|--------|--------|--------------|
| Rank bump | `/v1/cryptocurrency/listings/historical` + `/v3/cryptocurrency/listings/latest` | Bump/sankey of top-20 or top-100 membership | Who entered/left |
| Churn spark | derived | Entropy / turnover rate | Is composition restless? |
| Category treemap | `/v1/cryptocurrency/categories` | Multi-period returns | Where rotation hides |
| Top-N on date D | listings historical | Table | Reconstruct membership |

### M3 — Tabula Comparativa (2–4 + RWA island)

| Panel | Series | Visual | Notes |
|-------|--------|--------|-------|
| Asset/basket compare | `/v3/cryptocurrency/quotes/historical`, `/v2/cryptocurrency/ohlcv/historical`, `/v2/cryptocurrency/price-performance-stats/latest` | Rebased lines + stats | |
| RWA island | `/v5/real-world-assets/quotes/latest`, `/v5/real-world-assets/assets/list`, `/v5/real-world-assets/issuers`, `/v5/real-world-assets/issuers/list` | Side-by-side with crypto (labeled) | **No RWA history** — bridge via `crypto_id` |
| Optional side | Alchemy Prices `by-symbol` / `historical` | DEX vs CEX chip | **Optional** |
| Optional side | Arkham entity chip | Who is behind a labeled address | **Optional / paid** |

### M4 — Narrative + Share as Tab

| Step | Output |
|------|--------|
| Feature pack → gates → caption | 1–3 sentences |
| PNG board card | Title + one takeaway + endpoint strip |
| Share | Intent URL **or** draft copy **or** optional X API |

---

## 2. Endpoints named in submission (versions exact)

**Primary (must appear in README table + evidence drawer):**

| Path | Role |
|------|------|
| `/v3/index/cmc20-latest` | Regime |
| `/v3/index/cmc20-historical` | Regime path |
| `/v3/index/cmc100-latest` | Regime |
| `/v3/index/cmc100-historical` | Regime path |
| `/v3/fear-and-greed/latest` | Dual tape |
| `/v3/fear-and-greed/historical` | Dual tape (epoch string trap) |
| `/v1/altcoin-season-index/latest` | Dual tape |
| `/v1/altcoin-season-index/historical` | **REMOVED from the tape** - returns `timeframe='7d'` and 7 points; `limit`/`time_start`/`time_end`/`interval` are each accepted and each ignored. Keyless does not mean history. See START-HERE.md 0.1 |
| `/v1/global-metrics/quotes/latest` | Dominance |
| `/v1/global-metrics/quotes/historical` | Dominance path |
| `/v3/cryptocurrency/listings/latest` | Universe / rank now |
| `/v1/cryptocurrency/listings/historical` | **Rank churn (lead)** |
| `/v3/cryptocurrency/quotes/latest` | Compare |
| `/v3/cryptocurrency/quotes/historical` | Compare path |
| `/v2/cryptocurrency/ohlcv/historical` | Path structure |
| `/v2/cryptocurrency/price-performance-stats/latest` | ATH/ATL context |
| `/v1/cryptocurrency/categories` | Treemap |
| `/v1/cryptocurrency/map` | Resolution |
| `/v2/cryptocurrency/info` | Metadata |
| `/v5/real-world-assets/quotes/latest` | RWA island |
| `/v5/real-world-assets/assets/list` | RWA island |
| `/v5/real-world-assets/issuers` | RWA island |
| `/v5/real-world-assets/issuers/list` | RWA island |

**Do not invent:** `/v1/rwa/*` · RWA historical (use `crypto_id` bridge) · Arkham/Alchemy paths beyond documented ones below.

**Optional side (document as non-primary):**

| Source | Documented paths only | Access |
|--------|----------------------|--------|
| Alchemy Prices | `GET https://api.g.alchemy.com/prices/v1/tokens/by-symbol` · `POST …/tokens/by-address` · historical by symbol/address | Free 30M CU/mo · 300 req/hr Prices |
| Arkham | Intel REST under `https://api.arkm.com` (OpenAPI published) · x402 `https://api.arkm.com/x402` | Paid / trial / USDC |

---

## 3. Jev gates (only-with-Jev) — concrete

Host: `POST https://api.typesafe.ai/v1/systemone` · pin `jev-1.13.0`.  
Ship: `NARRATIVE_MODE=template|jev|llm` · `DECISION_BACKEND` optional. **Template always works.**

| Gate ID | Question type | `state` | Criteria | Use |
|---------|---------------|---------|----------|-----|
| **T1 regime_label** | `choice` | feature pack | `risk_on` \| `risk_off` \| `chop` \| `transition` \| `other` | Stamp regime chip on M1 |
| **T2 spread_widening** | `noul` | feature pack | true: “CMC20–CMC100 spread widening vs 7d” / false: narrowing or flat | Ribbon caption clause |
| **T3 churn_extremity** | `score` 0–4 | churn_entropy + top-N turnover | levels: quiet / mild / active / elevated / extreme | Caption intensity |
| **T4 caption_include[i]** | `noul` × N (fan-out) | feature pack + draft line | each candidate takeaway line | Keep lines with p≥0.7 |
| **T5 rwa_relevant** | `noul` | RWA island summary | true: island belongs this tab | Hide weak RWA panel |
| **T6 share_safe** | `noul` | final caption + card text | true: no advice, no invented numbers | Gate Share button |

**Confidence policy:** `choice`/`score` conf ≥0.75 stamp label; else chip “insufficient confidence — template only.”  
**Noul:** no confidence field — use distance from 0.5 as signal.  
**Do not** mix Noul thresholds with Choice (TypeSafe jaggedness).

---

## 4. Public-LLM + template fallbacks

| Mode | Behavior | Dependency |
|------|----------|------------|
| **template (floor)** | Fixed grammar: “CMC20–CMC100 spread {widened|narrowed} {x} over {d}d; F&G {v}; altseason {a}. Regime chip: {rules}.” | **None** |
| **jev** | Gates T1–T6 → select template clauses | TYPESAFE_API_KEY optional |
| **llm** | Qwen3 Ollama / DeepSeek Flash writes 2–3 sentences **from feature pack only** | Optional |

**Number-binding:** every number in a caption must exist in the feature pack / evidence drawer. No free-generated prices.

**Offline judges:** fixtures for index/F&G/listings historical + template captions + banner `DATA MODE: labeled corpus`.

---

## 5. Twitter artifacts (draft vs auto-post)

| Artifact | Mechanism | Cost | Required? |
|----------|-----------|------|-----------|
| **Share as Tab** PNG | Playwright screenshot / Satori / ECharts `getDataURL` | $0 | Yes (craft) |
| **Intent button** | `https://twitter.com/intent/tweet?text={caption}&url={dorahacks}&hashtags=BuildwithCMC` | **$0** | Yes (in-product) |
| **Draft pack** | `tab-share-pack.md` with 3 card captions + thread | $0 | Yes (7-pack support) |
| **Auto-post** | X API `POST /2/tweets` optional | $0.015 plain / **$0.20 with URL** | **No** |
| **Human 7-pack X post** | DoraHacks + demo + `#BuildwithCMC` | $0 | **Yes (contract)** |

**Loop answer:** Twitter share is first-class as **PNG tab + intent/draft**. Auto-post is optional stretch behind budget flag. Never block demo on X API.

**Card craft (15-pt):** large takeaway title · one sentence · CMC endpoint strip · classical Tabula subtitle · `#BuildwithCMC`.

---

## 6. Collision-aware craft (vs Data-Viz neighbors)

| Neighbor | They show | Tabula must show instead |
|----------|-----------|---------------------------|
| 48422 TrendLab | Today’s breadth / leadership **snapshot** | **History of index regime** (CMC20/100) + churn |
| 49045 My Beginning | Lineage + family drift | **Regime geometry + rank churn** (not forks) |
| 48997 Cap or No Cap | Game | Research board with one takeaway |
| 48601 OverWatch | Overview monitor | Membership on date D + composition |
| RWA cluster | What is this RWA | RWA **in the same frame** as crypto regime — not a product |

---

## 7. 7-pack checklist (Tabula)

| # | Item | Owner | Done when | Gate |
|---|------|-------|-----------|------|
| 1 | Public repo `tabula-rerum` | — | `.env.example`, no keys, README = regime geometry thesis | Must |
| 2 | Demo or screen recording | UI | M1 Regimen + M2 churn + one share tab | Must |
| 3 | X post DoraHacks + demo + `#BuildwithCMC` | human | URL in README/notes | Must |
| 4 | Named endpoints with versions | §2 table | Matches evidence drawer | Must |
| 5 | Code AND response | evidence/ curl+JSON | Real calls or labeled fixtures | Must |
| 6 | API made possible / got in the way | API_FEEDBACK.md | ≥5 dated quirks (epoch F&G, no RWA history, 1006, error_code, listings historical params) | Must |
| 7 | One track: Data and Visualisation | form | Selected | Must |
| + | API Feedback | README | First-class | Must |
| + | Server proxy | Node/TS or FastAPI | No browser keys | Must |
| + | Fixture labels | UI banner | Post-close judging | Must |
| + | Jev optional docs | README | T1–T6 + template floor | Should |
| + | Arkham/Alchemy labeled optional | README | Not hard deps | Should |
| + | No financial advice | caption pack | Footer + tweets | Must |

---

## 8. Build path (hardened)

| Day | Exit gate | Endpoints |
|----:|-----------|-----------|
| 22 | Scaffold + CMC client + keyless smoke | map, listings latest |
| 23 | **M1** CMC20/100 rebased, differenced, spread in **z-score units** (the raw difference is flat: 0.520 pts on a mean of 7.981) | `/v3/index/*` |
| 24 | Dual tape F&G · altseason · dominance | F&G, altseason, global historical |
| 25 | **M2** bump + churn + treemap | listings historical/latest, categories |
| 26 | **M3** Comparativa + RWA island + OHLCV | RWA v5, ohlcv, quotes historical |
| 27 | **M4** template→optional Jev, PNG, intent | — |
| 28 | Non-obvious proof + craft pass | — |
| 29 | 7-pack + API_FEEDBACK + recording | — |
| 30 | Deploy polish; **submit <23:59 UTC** | — |

**Stack (unchanged + harden):** Vite + React · ECharts or Observable Plot · thin Node/TS or FastAPI proxy · template narrative first · Playwright/Satori PNG · free static host · `evidence/` real-call log.

> **SUPERSEDED 2026-09-27 by `TABULA-CONTRACT.md` §3.** The runtime is Python 3.12
> **stdlib only**, per `IN-5` and `build/shared/README.md:5` ("Stdlib only for judged
> path"). The stack recorded here was written without reference to that rule. Vite, React,
> ECharts, Playwright, Satori and the Node/FastAPI proxy are **not** dependencies of this
> build. The share card is the host's existing headless Chrome, as `SPEC.md:47` already
> specified. Rendering is hand-written server-side SVG.

---

## 9. Residual risks (hardened)

| Risk | Mitigation |
|------|------------|
| Looks like prettier dashboard | Lead with **the normalised spread as regime meter** (rebased + z-scored; the raw ribbon is flat) |
| TrendLab / My Beginning overlap | Stress **history + CMC20/100 + share tabs** |
| Jev waitlist | Template floor |
| Credit burn | Batch IDs; cache; lead with index/global |
| RWA path fiction | **Only** `/v5/real-world-assets/*` |
| Arkham/Alchemy scope creep | Optional chips only; CMC primary |
| Naming | Always ship subtitle **Tabula Rerum** in 7-pack |

---

*HARDEN-tabula · chart modules M1–M4 · Jev T1–T6 · template floor · Twitter intent · optional Arkham/Alchemy · Agent RS*
