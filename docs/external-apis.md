# Tabula — External APIs: Arkham · Alchemy · CMC OpenAPI

> Evidence: **VERIFIED** · **INFERRED** · **UNVERIFIED**. **Never store API keys in this repo.**

---

## 1. CoinMarketCap (primary data plane)

| Item | Finding | Class |
|------|---------|-------|
| Local OpenAPI | `build/api/openapi.cmc.json` (~1.2 MB) | **VERIFIED (local)** |
| Official docs | coinmarketcap.com/api/documentation · pro-api-reference | **VERIFIED (URL)** |
| Endpoint catalog | `build/api/sources/endpoint-catalog.md` — 100+ paths | **VERIFIED (local)** |
| Auth | `X-CMC_PRO_API_KEY` on pro-api.coinmarketcap.com | **VERIFIED** |
| Keyless base | `https://pro-api.coinmarketcap.com/public-api` — 18 Standard + 17 DEX routes, no key, no headers, GET only | **VERIFIED (official docs, 2026-09-26)** |
| Rate limits | `build/api/sources/errors-and-rate-limits.md` | **VERIFIED (local)** |

### Endpoints Tabula names explicitly

| Purpose | Paths | Version |
|---------|-------|---------|
| CMC20 / CMC100 | `/v3/index/cmc20-latest`, `/v3/index/cmc20-historical`, `/v3/index/cmc100-latest`, `/v3/index/cmc100-historical` | v3 |
| Fear & Greed | `/v3/fear-and-greed/latest`, `/v3/fear-and-greed/historical` | v3 |
| Altcoin Season | `/v1/altcoin-season-index/latest` (keyless) | v1 | **Its `historical` route is keyless but returns a 7-day stub - 7 points, `timeframe='7d'`, all parameters ignored. Not a history source. See START-HERE.md 0.1** |
| Global Metrics | `/v1/global-metrics/quotes/latest`, `/v1/global-metrics/quotes/historical` | v1 |
| Listings (churn) | `/v3/cryptocurrency/listings/latest`, `/v1/cryptocurrency/listings/historical` | v3 / v1 |
| Quotes | `/v3/cryptocurrency/quotes/latest`, `/v3/cryptocurrency/quotes/historical` | v3 |
| OHLCV | `/v2/cryptocurrency/ohlcv/latest`, `/v2/cryptocurrency/ohlcv/historical` | v2 |
| Performance stats | `/v2/cryptocurrency/price-performance-stats/latest` | v2 |
| Categories / map / info | `/v1/cryptocurrency/categories`, `/v1/cryptocurrency/map`, `/v2/cryptocurrency/info` | v1 / v2 |
| RWA | `/v5/real-world-assets/map`, `/v5/real-world-assets/info`, `/v5/real-world-assets/assets/list`, `/v5/real-world-assets/quotes/latest`, `/v5/real-world-assets/issuers/list`, `/v5/real-world-assets/issuers`, `/v5/real-world-assets/market-pairs/list` | v5 |
| Simple / convert | `/v2/simple/price`, `/v2/tools/price-conversion` | v2 |

**Gaps to mark in UI:** no RWA historical endpoint (bridge `crypto_id` → crypto historical). Prefer v3 quotes over legacy v2. Prefer v2 simple/price over v1.

> **Corrected 2026-09-26.** This file previously gave the keyless base as `…/trial-pro-api`. That is
> wrong — `trial-pro-api` appears nowhere in current CoinMarketCap documentation and traces to a stale
> Academy article. The keyless root is `…/public-api`, as used by
> `build/shared/cmc_client.py:52` and recorded in `openapi.cmc.json`. Re-verified against
> <https://pro.coinmarketcap.com/api/documentation/pro-api-reference/keyless-public-api/>.
>
> **Confirmed keyless (relevant to the flagship panel):** `/v3/fear-and-greed/historical`,
> `/v3/index/cmc20-historical`, `/v3/index/cmc100-historical`, and
> `/v1/altcoin-season-index/historical` are all *reachable* with **no key** - but Altcoin Season `historical` answers with 7 days only, so the tape it could have carried does not exist. **Reachable is not the same as sufficient.** The regime board and the
> dual tape therefore need no CMC plan and no third-party provider.
>
> **Known code defect, not a doc error:** `build/shared/cmc_client.py:94` maps `simple_price` to the
> deprecated `/v1/simple/price`, while the table above correctly specifies `/v2/simple/price`. The
> table is right and the client is wrong. Confirmed by in-process hash comparison, not string
> reading. See `docs/implementation.md`.
>
> Authoritative current API facts live in [`../../docs/api.md`](../../docs/api.md); where the two
> disagree, that document wins.

---

## 2. Arkham Intelligence (`arkm.com`)

| Item | Finding | Class |
|------|---------|-------|
| Human docs | https://arkm.com/api/docs | **VERIFIED (URL)** |
| Machine docs | https://arkm.com/llms.txt | **VERIFIED (mentioned on docs)** |
| Base URL | `https://api.arkm.com` | **VERIFIED (catalogs)** |
| OpenAPI Intelligence | `api-evangelist/arkham/.../arkham-intelligence-api-openapi.yml` (OpenAPI 3.0.0, 21 ops) | **VERIFIED (YAML retrieved)** |
| OpenAPI Balances | `.../arkham-balances-api-openapi.yml` | **VERIFIED (YAML retrieved)** |
| OpenAPI Transfers | `.../arkham-transfers-api-openapi.yml` | **UNVERIFIED (not fetched)** |
| Full catalog | `apis.yml` claims 135 ops / 128 paths + WS | **INFERRED** |
| Auth | API key header | **INFERRED (Postman)** |
| Billing | usage-based credits | **INFERRED** |
| Access | https://arkm.com/api · api@arkm.com | **VERIFIED** |
| WebSocket | `/ws/transfers` | **INFERRED** |

### Sample schemas (from retrieved OpenAPI YAML)

```yaml
# GET /intelligence/address/{address} → Address { address, chain, contract, arkhamEntity?, arkhamLabel? }
# GET /intelligence/entity/{entity} → ArkhamEntity { id, name, note, type, service, description }
# GET /balances/address/{address} → { addresses, totalBalance, totalBalance24hAgo, balances }
```

**OpenAPI status: PARTIAL VERIFIED.** Real OpenAPI 3.0.0 exists (api-evangelist mirror) for Intelligence + Balances. Full 135-op surface is **INFERRED** from `apis.yml`. Prefer `arkm.com/llms.txt` / API Reference as authority.

**Tabula use:** optional entity/risk labels on top holders (stretch). Do not block v1 on Arkham access.

---

## 3. Alchemy (`alchemy.com/rpc-api`)

| Item | Finding | Class |
|------|---------|-------|
| Human docs | alchemy.com/docs/get-started · Chain APIs · Enhanced APIs | **VERIFIED** |
| RPC base | `https://{network}.g.alchemy.com/v2/{apiKey}` | **VERIFIED** |
| x402 gateway | `https://x402.alchemy.com/{chainNetwork}/v2` | **VERIFIED** |
| OpenRPC | `alchemyplatform/docs` `src/openrpc/**` — OpenRPC **1.2.4**, 45+ chains | **VERIFIED** |
| OpenAPI (REST) | NFT / Portfolio / Prices / Notify families | **VERIFIED (DeepWiki)** |
| OpenAPI sample | `api-evangelist/alchemy/.../alchemy-transfers-api-openapi.yml` (`alchemy_getAssetTransfers`) | **VERIFIED (YAML retrieved)** |
| Auth | API key path or `X-Alchemy-Token` | **INFERRED** |
| Enhanced methods | `alchemy_getTokenBalances`, `alchemy_getTokenMetadata`, `alchemy_getTokenAllowance`, `alchemy_getAssetTransfers`, `alchemy_simulate*`, `alchemy_getTransactionReceipts` | **VERIFIED** |
| Subscriptions | `eth_subscribe`: newHeads, logs, pending, `alchemy_minedTransactions`, `alchemy_pendingTransactions` | **VERIFIED** |
| Cost | Compute Units | **VERIFIED** |

### Sample request

```bash
curl -s -X POST https://eth-mainnet.g.alchemy.com/v2/$ALCHEMY_API_KEY \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"alchemy_getTokenBalances","params":["0x…","erc20"]}'
```

**OpenAPI status: VERIFIED that machine-readable specs exist** — **OpenRPC 1.2.4** for JSON-RPC + **OpenAPI** for REST families (not one monolith). Spec homes: `alchemyplatform/docs`, DeepWiki indexes, api-evangelist mirrors.

**Tabula use:** optional enrichment (balances/transfers/labels). CMC remains the named product data plane.

---

## 4. Fit matrix

| Need | CMC | Arkham | Alchemy |
|------|-----|--------|---------|
| Index / regime / OHLCV / listings | **Primary** | no | no |
| RWA quotes/issuers | **Primary (v5)** | partial | no |
| Entity labels / risk | no | **optional** | no |
| Balances / transfers | no | yes | **optional** |
| Machine-readable OpenAPI | local + docs | **partial (mirror)** | **OpenRPC + OpenAPI families** |

## 5. Honesty flags

- Do **not** invent Arkham/Alchemy paths beyond the lists above.
- api-evangelist OpenAPI is a **mirrored/reconstructed** catalog — **VERIFIED content, INFERRED completeness**.
- Live Arkham/Alchemy demos need user-supplied keys via env (never committed).
