# SUBMISSION PACKAGE — paste these into DoraHacks

**Track:** Data and Visualisation
**Repo:** (paste your GitHub URL here)
**Demo video:** (paste URL here)
**X post:** (paste URL here — must include **#BuildwithCMC**)

> ⚠️ `gh` on this machine reports: *"The token in GITHUB_TOKEN is invalid."* The repo is
> committed locally but **not pushed**. You must create the public repo and push it yourself.

---

## Title

Tabula Rerum — the market-claim auditor: every number ships with the receipt that made it

## One-line summary

A standard-library-only CoinMarketCap workspace that measures whether a market claim is
statistically defensible — and shows the receipt behind every figure.

## Description (paste this)

CMC20 and CMC100 are supposed to tell two different stories: concentrated leadership versus broad
participation. We built the dashboard, then checked whether the spread between them supports the
story.

It does not. The two indices correlate at **r = 0.999902** — they are the same asset class. Their
difference has lag-1 autocorrelation **ρ₁ = 0.947**, a unit root. There is no stationary
distribution behind "regime spread", so it has no equilibrium to deviate from and no valid null.
The effective sample size of a 70-day window is **6.06, not 70**.

So we stopped drawing the chart everyone draws. We report the spread in percentage points, its
position in the cross-window distribution, and its effective sample size. Every figure is
**measured at render time** — never a constant copied from a document — and every fetch emits a
receipt recording endpoint, params, auth mode, HTTP status, CMC error code, credit count, latency
and a SHA-256 digest. A number without a receipt is treated as a defect.

The second finding is about the API itself. An unrouted or unauthorised path returns
**HTTP 200** with `error_code: 500` and `"The system is busy, please try again later!"` —
byte-identical to a genuine transient error, and in direct conflict with the documented
"retry 500" guidance. Naive retry loops hang forever. We classify it as `UNROUTED` by the absence
of a `data` key and never retry it. The limit that actually governs anonymous access is
**`1022`**, which appears in no published error table.

**Built:** Python 3.12, **standard library only**. No npm, no bundler, no build step, no
third-party runtime dependency — enforced by a test, because this environment *has*
Flask/pandas/numpy and the rule is a discipline rather than an accident. Server-rendered
hand-written inline SVG, so no browser is in the loop and no chart library is needed. **47
tests**, each one a defect that would otherwise pass silently. Runs **offline from recorded
fixtures with no API key**, and live against keyless CMC with `--live`.

Every chart ships a tabular equivalent, carries `role="img"` with `<title>`/`<desc>`, and never
encodes meaning by colour alone. Alignment policy is decided rather than assumed: inner join for
statistics, outer join for rendering, windows dropped below 95% coverage, and **forward fill
prohibited** — it manufactures zero returns, understates volatility, and would inflate every
z-score, i.e. it would fabricate the finding.

## Endpoints used (named explicitly, as required)

All keyless — **no API key required**:
- `GET /public-api/v3/index/cmc20-historical`
- `GET /public-api/v3/index/cmc100-historical`
- `GET /public-api/v3/index/cmc20-latest`
- `GET /public-api/v3/index/cmc100-latest`
- `GET /public-api/v3/fear-and-greed/historical`
- `GET /v1/altcoin-season-index/historical?timeframe=90d`

## Evidence of a real API call

```bash

## Note to CMC: where the API got in the way

1. **The index endpoints are missing from this track's own suggested menu.** The Data and
   Visualisation track suggests historical quotes, OHLCV, global metrics, categories, DEX pairs
   and exchange listings. `/v3/index/cmc20-*`, `/v3/index/cmc100-*` and the Altcoin Season Index
   are not among them. The most interesting keyless data in the API is the data the track
   description does not point you at.
2. **Auth failures are indistinguishable from transient errors** — `HTTP 200` +
   `error_code 500` + "system is busy", colliding with the documented retry-500 guidance.
3. **The keyless rate limit is undocumented.** The error table stops at `1011`; the limit that
   actually governs anonymous access is `1022`, in no table. No `Retry-After`, no `X-RateLimit-*`
   headers — so there is no machine-readable contract for backing off.
4. **The OpenAPI spec is wrong about a field it documents.** Fear & Greed `timestamp` is declared
   as an ISO-8601 datetime; the wire value is a decimal **epoch string**. Spec-driven generators
   produce broken code here.
5. **Constituent schemas differ between the two indices without being flagged** —
   `cmc20-historical` returns `priceUsd` and `units`; `cmc100-historical` returns neither. Code
   must branch on the index and nothing says so.
6. **The changelog has a 17-month gap** (Oct 2024 → Mar 2026) and never records the Fear & Greed
   `v1` → `v3` move or the `/v3/index/*` endpoints at all.
7. **Credit accounting is opaque on the keyless tier** — every call reports `credit_count: 1`
   with no account and no visible quota.

## X post template

> We built a CoinMarketCap dashboard that told us not to believe its own headline.
>
> CMC20 and CMC100 correlate at r=0.999902. Their difference has ρ₁=0.947 — a unit root. So
> "regime spread" has no equilibrium to deviate from, and a 70-day window has an effective
> sample size of 6, not 70.
>
> We report percentage points, percentile rank and n_eff instead. Every number ships with the
> receipt that produced it.
>
> Also: your unrouted paths return HTTP 200 + error_code 500 + "system is busy", which is a typo
> wearing a retry loop's clothes.
>
> [link] #BuildwithCMC

---

## Final checklist

- [ ] `gh auth login` — the current `GITHUB_TOKEN` is **invalid**
- [ ] create the public repo, `git remote add origin …`, `git push -u origin main`
- [ ] `bash demo.sh` and **screen-record it** — that is your demo video
- [ ] paste repo URL + video URL into the DoraHacks form
- [ ] post the X text above with **#BuildwithCMC**
- [ ] **submit before 23:59 UTC**

curl -s "https://pro-api.coinmarketcap.com/public-api/v3/index/cmc20-latest"
```
```json
{"status":{"timestamp":"...","error_code":"0","elapsed":2,"credit_count":1},
 "data":{"id":"cmc20","name":"CMC20","value":177.8,
         "value_24h_percentage_change":-1.42,
         "last_update":"2026-09-30T00:00:00Z","next_update":"2026-09-30T05:00:00Z",
         "constituents":[ ... 20 entries ... ]}}
```

The failure mode, unedited:
```bash
curl -s "https://pro-api.coinmarketcap.com/public-api/v9/totally/bogus"
```
```json
{"status":{"timestamp":"...","error_code":"500",
           "error_message":"The system is busy, please try again later!",
           "elapsed":"0","credit_count":0}}
```

Run `bash demo.sh` to reproduce the entire finding end-to-end in about 40 seconds.
