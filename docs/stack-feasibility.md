# Tabula — Stack & Feasibility

## 1. Jev (TypeSafe AI) — auto-narrative?

| Question | Answer | Class |
|----------|--------|-------|
| What is Jev? | "System One" model: **typed decisions**, not text. Primitives **Choice**, **Score**, **Noul** (yes/no probability) + confidence. | **VERIFIED** |
| Can Jev *write* chart narrative? | **No.** It does not generate strings. | **VERIFIED** |
| What can Jev do for Tabula? | Structured **gates** on chart state JSON: e.g. Noul "is the CMC20–CMC100 spread widening?", Score "how extreme is rank churn?", Choice "regime: risk-on / chop / risk-off". A **generative LLM** (or template) then writes the caption. | **INFERRED (fit)** |
| Latency / cost | ~70–500ms; `jev-1.13.0` **$0.042 / 1M input tokens, output free**. Context ~32K (some sources 64K). | **VERIFIED-ish** |
| Access | TypeSafe console (early access/waitlist), OpenRouter `typesafe/jev-1.13`, Cloudflare `typesafe/jev`, LangChain `langchain-typesafe`. | **VERIFIED** |
| Hackathon risk | Waitlist — **do not block demo** on Jev. Ship templates first. | **VERIFIED constraint** |

### Hybrid narrative (ship this)

```text
CMC series → feature pack (JSON)
  → [optional] Jev Choice/Score/Noul → regime labels + confidence
  → template grammar OR public chat LLM writes 2–3 sentences
  → panel + PNG tab
```

Fallbacks: (1) **template grammar** (offline, always works); (2) **public LLMs** via OpenRouter / OpenAI-compatible for prose; (3) **Jev** only for the decision layer when available.

---

## 2. Twitter/X as share surface (user requirement)

| Concern | Approach | Class |
|---------|----------|-------|
| Submission rule | X post with DoraHacks link, demo video, `#BuildwithCMC` | **VERIFIED** |
| Share UX | "Share tab" → PNG (Playwright screenshot or Satori) → `https://twitter.com/intent/tweet?text&url&hashtags=BuildwithCMC` | **VERIFIED pattern** |
| OG unfurl | Per-tab `/t/:id` with `og:image` = board card | **INFERRED** |
| Render options | (a) Playwright `screenshot` of panel (most faithful), (b) Satori/`@vercel/og`, (c) ECharts `getDataURL` | **VERIFIED libs** |
| Craft | Large card; title + one takeaway + endpoint strip | **INFERRED** |

---

## 3. Build path in days (deadline 30 Sep 23:59 UTC)

| Day | Deliverable | Endpoints |
|-----|-------------|-----------|
| D1 | Scaffold, CMC client, keyless smoke, wax/bronze tokens | map, listings latest |
| D2 | **Tabula Regimen**: CMC20/100 rebased, differenced, spread in z-score units | `/v3/index/*` |
| D3 | Dual tape: F&G, Global Metrics (Altcoin Season *latest* only - `historical` is a 7-day stub) | `/v3/fear-and-greed/*`, `/v1/altcoin-season-index/*`, `/v1/global-metrics/*` |
| D4 | **Tabula Rerum**: bump chart + category treemap | listings historical/latest, categories |
| D5 | **Tabula Comparativa** + RWA island + OHLCV | `/v5/real-world-assets/*`, ohlcv historical |
| D6 | Narrative (template→optional Jev), PNG tab + Twitter, 7-pack, demo, X post | — |
| Buffer | Deploy, screen recording, judging prep | — |

**Stack:** Vite + React (Next optional for OG) · ECharts or Observable Plot · thin Node/TS or FastAPI proxy (key safety + cache) · template narrative first · Playwright PNG · Vercel/Netlify/Cloudflare Pages · `evidence/` curl+JSON for the real-call requirement.

> **SUPERSEDED 2026-09-27 by `TABULA-CONTRACT.md` §3.** The runtime is Python 3.12
> **stdlib only**, per `IN-5` and `build/shared/README.md:5` ("Stdlib only for judged
> path"). The stack recorded here was written without reference to that rule. Vite, React,
> ECharts, Playwright, Satori and the Node/FastAPI proxy are **not** dependencies of this
> build. The share card is the host's existing headless Chrome, as `SPEC.md:47` already
> specified. Rendering is hand-written server-side SVG.

---

## 4. Feasibility verdict

| Workstream | Feasible by deadline? | Notes |
|------------|----------------------|-------|
| Core viz (Regimen + Rerum + Comparativa) | **Yes** | CMC-only; free Startup tier for participants |
| RWA island | **Yes** | v5; historical via `crypto_id` bridge |
| Auto-narrative (template) | **Yes** | no external dependency |
| Auto-narrative (Jev) | **Maybe** | early access; degrade gracefully |
| Twitter tab cards | **Yes** | screenshot + intent |
| Arkham/Alchemy depth | **Optional / post-v1** | do not block |

## 5. Risks

1. **Track density:** Data-Viz is thin (~3–4/35) — differentiation must be non-obvious (regime geometry), not prettier sparklines.
2. **Credit burn:** batch IDs, cache; lead with index/global (fewer calls).
3. **Jev waitlist** — covered by fallback.
4. **Naming:** always ship subtitle **Tabula Rerum** in the 7-pack.
