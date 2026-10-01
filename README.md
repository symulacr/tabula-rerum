# Tabula Rerum

**Track: Data and Visualisation** · Build with CMC: API Hackathon

> CMC20 and CMC100 correlate at **r = 0.999902** — the same asset class, so their difference is
> close to noise by construction. That difference's lag-1 autocorrelation is **ρ₁ = 0.7625**:
> strongly persistent, with no stationary distribution and no valid null. A 70-day window of it
> carries an effective sample size of **26, not 70**. So we report percentage points and
> percentile rank — and ship a receipt behind every number.

```bash
python3 run.py          # offline from fixtures — no key, no network
python3 run.py --live   # live keyless CoinMarketCap
python3 run.py --test   # 99 tests
bash demo.sh            # reproduce the finding end-to-end
python3 share_card.py --check   # render the share card and prove it is byte-reproducible
```

**Python 3.12, standard library only.** No npm, no bundler, no build step, no third-party runtime
dependency — enforced by `TestStdlibOnly`, because this environment *has* Flask/pandas/numpy and
the rule is a discipline, not an accident. Server-rendered inline SVG; no browser in the loop.
`share_card.py` drives the host's own headless Chrome rather than adding a rasteriser, and
verifies its output is byte-identical across runs.

## Endpoints — all keyless, no API key

```
GET /public-api/v3/index/cmc20-historical
GET /public-api/v3/index/cmc100-historical
GET /public-api/v3/index/cmc20-latest
GET /public-api/v3/index/cmc100-latest
GET /public-api/v3/fear-and-greed/historical
GET /v1/altcoin-season-index/historical?timeframe=90d
```

```bash
curl -s "https://pro-api.coinmarketcap.com/public-api/v3/index/cmc20-latest"
# {"status":{"error_code":"0","credit_count":1},"data":{"id":"cmc20","value":177.8,...}}
```

`count` is hard-capped at 10; bounds need full ISO-8601 with `Z`; 70 points took 7 contiguous
pages with 0 duplicate timestamps.

## Every number ships with its receipt

Each fetch records endpoint, params, auth mode, HTTP status, CMC error code, credit count,
latency and a SHA-256 digest. **A number without a receipt is a defect.** Fixtures carry no
provenance block, so a recorded capture can never masquerade as a live one.
`HTTP 200 + error_code 0 + data: []` is a **failure**, not empty success.

**Forward fill is prohibited** — it manufactures zero returns, understates volatility, and
inflates every z-score, i.e. it would fabricate the finding. Alignment: inner join for
statistics, outer join for rendering, windows dropped below 95% coverage.

## Where the API got in the way

1. **The index endpoints are missing from this track's own suggested menu** — the best keyless
   data is the data the brief doesn't point at.
2. **Auth failures are masked as transient.** An unrouted path returns `HTTP 200` +
   `error_code 500` + *"The system is busy"* — byte-identical to a real blip, and in conflict
   with the documented retry-500 guidance. The client classifies it `UNROUTED` by the absence of
   `data` and **never retries it**: a typo does not become correct on a second attempt.
3. **The keyless limit is `1022`**, in no published table. No `Retry-After`, no `X-RateLimit-*`.
4. **OpenAPI misdeclares F&G `timestamp`** as ISO-8601; the wire value is an epoch **string**.
   Altcoin Season uses ISO-8601 in the *same field name* — both encodings are handled.
5. **Constituent schemas differ** between `cmc20` (has `priceUsd`, `units`) and `cmc100` —
   unflagged anywhere.
6. **Fear & Greed returns newest-first** behind a **1-based `start` offset**; the axis inverts
   silently if you wire it as-is. Normalised, and pinned by a test.
7. **Altcoin Season honours only `timeframe`** (`7d`/`30d`/`90d`). `limit`, `time_start`,
   `time_end` and `interval` are accepted and **silently ignored** — false confidence.

## Limitations, stated plainly

`CMC20 − CMC100` is near-noise *because* the indices are 99.99% correlated — we show that rather
than hide it. Composition is **CMC index reconstitution, not market churn**. Fear & Greed is
Bitcoin-only and the vendor notes several of its component inputs are paused. The Altcoin Season
Index was **redefined**: it is now the share of the top 50 excluding BTC that outperformed BTC
over 90 days, not the old altcoin/BTC market-cap ratio. `listings/historical`, `quotes/historical`
and `ohlcv/historical` are **not keyless** (403/1005), so a keyless build cannot do whole-market
churn. The window is **yours to choose**, and both series rebase to 100 at the window's first
day — so the mean, sd and percentile describe that window, not the market.

*No investment advice.*
