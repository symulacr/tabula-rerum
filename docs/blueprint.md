# Tabula Rerum — Blueprint

**Product:** Tabula · **Subtitle:** Tabula Rerum  
**Track:** Data and Visualisation  
**Event:** Build with CMC: API Hackathon (`coinmarketcap-api-202609`)  
**Deadline:** 30 Sep 2026 23:59 UTC

## Flagship idea (one sentence)

**Tabula Rerum** is a classical market board that makes **regime geometry and composition churn** legible — CMC20 vs CMC100 as a regime meter, Fear & Greed + Altcoin Season as a dual tape, listings history as rank-churn narrative, RWA in the same frame as crypto — then exports each finding as a shareable *tab* for X.

## Gallery context (Data-Viz-adjacent, no winner ranking)

| ID | Name | Shows (evidence-weighted) | Still illegible |
|----|------|---------------------------|-----------------|
| 48422 | TrendLab Market Structure Map | structure/trend map | index regime + sentiment dual-tape |
| 48601 | OverWatch | monitoring/overview | historical membership (top-N on date D) |
| 48997 | Cap or No Cap | cap-centric viz | CMC20/100 spread as the *meter* |
| 49045 | My Beginning | early/onboarding board | churn entropy + RWA-in-frame |
| 48868 / 48987 | Crypto Screener / Pulse Screener | one-screen screeners | out of scope for Tabula |

IDs/names **VERIFIED** (local `research/CMC-BUIDL-MASTER.md` + gallery). Product depth **INFERRED** from names + public search; full cards in `research/archive`. Data-Viz track is thin (~3–4 of ~35 BUIDLs).

## Modules v1

### M1 — Tabula Regimen
Rebase CMC20 & CMC100 to 100; difference; spread in z-score units. Tape: Fear & Greed. (The raw CMC20-CMC100 difference is flat - 0.520 points on a mean of 7.981 - so the spread is only legible after rebasing. See docs/CANONICAL-DATA.md and START-HERE.md 0.)

### M2 — Tabula Rerum
Bump chart of top-20/100 membership (listings historical vs latest); churn spark; category treemap multi-period returns.

### M3 — Tabula Comparativa
2–4 CMC IDs; OHLCV + price-performance-stats; RWA island (`/v5/real-world-assets/*`) labeled with historical bridge via `crypto_id`.

### M4 — Narrative + Tab share
Feature pack → template caption (ship) / optional Jev labels / optional LLM prose → PNG tab → Twitter intent `#BuildwithCMC`.

## CMC endpoints (name in submission)

`/v3/index/cmc20-latest`, `/v3/index/cmc20-historical`, `/v3/index/cmc100-latest`, `/v3/index/cmc100-historical`,
`/v3/fear-and-greed/latest`, `/v3/fear-and-greed/historical`,
`/v1/altcoin-season-index/latest`  (its `historical` is a 7-day stub and is excluded),
`/v1/global-metrics/quotes/latest`, `/v1/global-metrics/quotes/historical`,
`/v3/cryptocurrency/listings/latest`, `/v1/cryptocurrency/listings/historical`,
`/v3/cryptocurrency/quotes/latest`, `/v3/cryptocurrency/quotes/historical`,
`/v2/cryptocurrency/ohlcv/historical`, `/v2/cryptocurrency/price-performance-stats/latest`,
`/v1/cryptocurrency/categories`, `/v1/cryptocurrency/map`, `/v2/cryptocurrency/info`,
`/v5/real-world-assets/quotes/latest`, `/v5/real-world-assets/issuers/list`,
`/v5/real-world-assets/issuers`, `/v5/real-world-assets/assets/list`

## Out of scope v1

Trading, wallets, agent execution, inventing endpoints, Arkham/Alchemy as hard dependencies.
