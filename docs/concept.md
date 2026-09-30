# Tabula Rerum

**Track:** Data and Visualisation · Build with CMC (`coinmarketcap-api-202609`)
**One-liner:** A classical *tabula* (Roman wax board of market *res*) that turns CoinMarketCap index, regime, and composition series into shareable, non-obvious comparative narratives — not another one-screen screener.

## The problem

Most crypto dashboards redraw the same screen: ticker, sparkline, rank table. The CMC API already exposes institutional series that almost nobody renders well:

| Underused series | What it encodes | Why it stays illegible |
|---|---|---|
| CMC20 / CMC100 index historical | regime-relative basket performance | apps show BTC price, not index shape vs the 20/100 spread |
| Listings Historical + OHLCV Historical | rank churn, composition change | rank tables are always *now* |
| Global Metrics historical | dominance, volume share | single dials, not composition over time |
| Fear & Greed historical | sentiment regime | (Altcoin Season contributes *latest* only — its `historical` is a 7-day stub) | isolated gauges, not a dual tape | isolated gauges, not a dual tape |
| RWA quotes/issuers (v5) | tokenised vs crypto beta | RWA lives in another tab |

**Non-obvious claim (25-pt hinge):** The interesting signal is not "what did price do?" but *what kind of market is this index describing?* Tabula makes **regime geometry** legible: how CMC20 and CMC100 diverge, how rank-churn rises before drawdowns, how Fear & Greed co-moves with Altcoin Season and dominance, and where RWA sits in the same frame as crypto.

## Product surfaces (v1)

1. **Tabula Regimen** — CMC20 vs CMC100 rebased, differenced, spread in z-score units; dual tape (F&G · dominance; Altcoin Season latest only, its `historical` is a 7-day stub); auto-caption of the shape.
2. **Tabula Rerum** — rank-churn bump/sankey from listings historical; category treemap; "top-N on date D."
3. **Tabula Comparativa** — 2–4 assets/baskets; RWA island (v5) in the same frame as crypto.
4. **Share as Tab** — PNG board card → Twitter/X intent with `#BuildwithCMC` + DoraHacks link.

## Deliberately not

Not a one-screen screener, not an agent/execution bot, not an RWA-only explorer.

## Judging map

| Weight | Criterion | Tabula answer |
|--------|-----------|---------------|
| 25 | Non-obvious | Regime geometry + churn history + RWA-in-frame |
| 15 | Craft/clarity | Classical naming, one takeaway per panel, shareable tabs |
| — | Real API use | Named CMC endpoints + live evidence |
| — | Something a person would use | A researcher can *read a market day* as a board |

## Deadline

Submissions close **30 Sep 2026 23:59 UTC**. Build path ~6 days (see `stack-feasibility.md`).
