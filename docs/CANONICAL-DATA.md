# CANONICAL DATA CONTRACT

**Authoritative for data shape.** No build code may depend on a dataset not defined here.

Every fact below was verified live, keyless, with no key header, on **2026-09-27**.

---

## 1. Series

| | CMC20 | CMC100 |
|---|---|---|
| Endpoint (keyless) | `/public-api/v3/index/cmc20-historical` | `/public-api/v3/index/cmc100-historical` |
| Latest | `/public-api/v3/index/cmc20-latest` | `/public-api/v3/index/cmc100-latest` |
| Frequency | daily | daily |
| Unit | index points | index points |
| First available | **2024-01-01** | **2024-01-01** |
| Constituents/day | **20** | **100** |

## 2. Point schema

A historical point has **exactly three keys** (live-verified, not inferred):

```json
{ "update_time": "2026-09-26T00:00:00Z", "value": 177.8, "constituents": [ ... ] }
```

> **The date field is `update_time`, NOT `timestamp`.** Using the wrong field name silently yields
> an empty series rather than an error.

## 3. Constituent schemas DIFFER between the indices

| Field | CMC20 | CMC100 |
|---|:-:|:-:|
| `id`, `name`, `symbol`, `url`, `weight` | yes | yes |
| `priceUsd` | **yes** | **NO** |
| `units` | **yes** | **NO** |

**Code reading `priceUsd` must branch on the index.** An earlier note in this project described
constituents as a "20-name capability"; that is true of CMC20 only. CMC100 returns 100 names a day.

**Interpretation caveat, mandatory wherever this data is shown:** this is **CMC-selected basket
composition, not market churn**. Entries and exits are CMC index rebalances, not market events, so
the panel shows how the index provider reconstitutes its leaderboard. Depth is bounded at
2024-01-01, so a full rebalance history is roughly 2.7 years.

## 4. Paging and windows

| Rule | Value |
|---|---|
| `count` | **hard-capped at 10**; `count=30` → `400 'count' should be a positive number in range [1, 10]'` |
| Bounds format | **full ISO-8601 with `Z`**. A bare `YYYY-MM-DD` → `400 'time_end' must be a valid ISO 8601 timestamp or unix time value'` |
| `interval` | `5m`, `15m`, `daily` only. `1d` → `400` |
| Fill direction | with both bounds set, the window fills **from its START**, ascending |
| Unbounded | fills with the most recent N |

**Consequence for any multi-month pull:** history must be walked window by window. Measured: 70
points per index across 7 contiguous pages, **0 duplicate timestamps**.

## 5. Alignment policy (decided — not TBD)

1. **Axis:** UTC, ascending, deduplicated by timestamp.
2. **Statistics: INNER JOIN.** Only timestamps present in both series.
3. **Rendering: OUTER JOIN.** Every day either series has, so a gap renders as a gap.
4. **Window: DROP** if inner-join coverage < 95% of the requested window, or fewer than 30 paired
   observations. The drop is recorded, never silently analysed.
5. **Forward fill: PROHIBITED.**

### Why forward fill is prohibited

| Policy | Gains | Costs |
|---|---|---|
| Inner join | invents nothing | shrinks the sample; caption must state real n |
| Outer join | preserves the true calendar | every transform must declare its `None` policy |
| Forward fill | contiguous series | **manufactures zero returns → understates volatility → shrinks sigma → inflates every z-score.** Makes divergence look more significant than it is |
| Drop | every number is real and comparable | discards sparse windows |

Forward fill is the only option that fabricates the very finding this product reports, so it is
prohibited rather than discouraged. Enforced by `TestAlignment.test_forward_fill_is_prohibited`.

## 6. Missing, empty, and duplicate data

| Case | Handling |
|---|---|
| `HTTP 200 + error_code 0 + data: []` | **FAILURE**, not an empty success. Live-verified: `?symbol=ZZZNOTAREALCOIN` returns exactly this. |
| Duplicate timestamps | de-duplicated, last write wins, recorded in the walk |
| Point without `value` | skipped, counted |
| Point without `update_time` | skipped — there is no axis without it |
| Coverage below threshold | window dropped with a reason; nothing is drawn |
| Dispersion undefined (< 2 points) | z-score is `None`, rendered as "—", never as `0` |

**`error_code == 0` is necessary but not sufficient.** That is the single most important line in
this document.

## 7. Authentication and rate limits

| Fact | Detail |
|---|---|
| Keyless | shared **per-IP** pool; CMC does not publish the threshold |
| Observed | 8 requests at 4.5 s spacing succeed; bursts produce `429/1011` or `429/1022` |
| `1011` | `IP_RATE_LIMIT_REACHED` — official table |
| `1022` | anonymous keyless limit — **not in any official table**, corpus-observed, kept separate |
| Headers | no `Retry-After`, no `X-RateLimit-*` on 200 or 403 |
| Rule | retry 429 only, exponential, max 3; treat an empty body as failure |

## 8. Provenance

Every fetch emits a `Receipt`: `path_key, path, method, params, auth_mode, http_status,
error_code, verdict, error_name, error_class, credit_count, elapsed_ms, at, note`, plus a SHA-256
digest. Fixtures under `evidence/fixtures/` are raw payload arrays and carry **no** provenance
block, so a recorded capture can never masquerade as a live one.

## 9. What is deliberately absent

| Not a canonical series | Why |
|---|---|
| Altcoin Season **history** | The endpoint is keyless but returns `timeframe='7d'` and **7 points**. `limit`, `time_start`, `time_end`, `interval` are each accepted and each **ignored**. Keyless ≠ history. |
| OHLCV, quotes history | `403/1005` without a key; dies at the free Basic tier |
| RWA | `403/1006` even on an event key, and no history endpoint exists |
| Whole-market churn | requires `listings/historical`, which is keyed |

**Fear & Greed history is genuinely available** and 50 points are recorded in
`evidence/fixtures/fng_historical.json`. It is not yet wired into a panel; that is a product
decision, not a data gap.
