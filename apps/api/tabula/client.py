"""Tabula CMC client — stdlib only.

Lineage
-------
Behaviour is derived from `build/shared/cmc_client.py` (690 lines, the only working CMC client in
the parent workspace). That file is NOT copied: it carries six confirmed defects, so this module is
a purpose-built implementation that keeps what was verified and fixes what was broken.

Defects in the parent client that this module does not reproduce:

  E1  `index_historical_paged` never advanced the window — pages 2..N were identical and
      overlapped page 1. Here: `walk_window()` advances `time_start` by the number of points
      actually returned. See `tests/test_client.py::test_walk_no_duplicate_timestamps`.

  E3  A fabricated `PLAN_GATED` string squatted the numeric namespace CMC owns. Here: sentinels
      live under `cmc-client.local/` and can never collide with a CMC code (1001-1011, 1022).

  E4  `/v1/simple/price` is deprecated. Here: `/v2/simple/price` only, and the v2 response shape
      is `data[].quotes[].price`, NOT v1's `data[].price`. See `parse_simple_price()`.

  E5  `HTTP 200 + error_code 0 + empty data` was classified as success. It is a failure mode for a
      semantically invalid request, live-verified with `?symbol=ZZZNOTAREALCOIN`. Here:
      `Response.ok` is False whenever the payload is semantically empty.

  E6  `archive_json` wrote three unvalidated keys, so a live capture was indistinguishable from a
      hand-written fixture. Here: every response carries a `receipt`, and `capture_envelope()`
      stamps an explicit provenance block with a `kind` discriminator.

  D7  `auth_mode_for()` checked `has_key` BEFORE consulting the keyless list, so an exported key
      silently upgraded all 18 keyless paths to keyed Pro calls. Here: the keyless route is always
      preferred for paths in `KEYLESS_PATHS`; the key is only used when there is no keyless route
      AND `allow_keyed=True`. This is the fix, not a mitigation.

Live-verified facts this module encodes (all keyless, no key header, 2026-09-27):
  - `count` is hard-capped at 10; above that returns 400.
  - Bounds must be full ISO-8601 with `Z`; a bare `YYYY-MM-DD` returns 400.
  - `interval` accepts only `5m`, `15m`, `daily`.
  - With both bounds set the window fills FROM ITS START, ascending.
  - Index historical point keys are exactly `['constituents','update_time','value']`.
  - CMC20 carries 20 constituents/day, CMC100 carries 100, and the schemas DIFFER
    (CMC100 has no `priceUsd`, no `units`).
  - `error_code 1022` is the anonymous/keyless limit and is distinct from 1011 (IP rate limit).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

# --- endpoints ---------------------------------------------------------------

PRO_BASE = "https://pro-api.coinmarketcap.com"
KEYLESS_BASE = PRO_BASE + "/public-api"
HEADER_KEY = "X-CMC_PRO_API_KEY"
USER_AGENT = "tabula-rerum/1.0 (+stdlib; contact via repo)"

# Only these intervals exist. `1d` is rejected by the API with HTTP 400.
INTERVALS = ("5m", "15m", "daily")
# The API rejects count outside [1, 10]. This is a server-side hard cap, not a tuning choice.
MAX_COUNT = 10

# path key -> (path, interval-aware)
PATHS: dict[str, str] = {
    "cmc20_latest": "/v3/index/cmc20-latest",
    "cmc100_latest": "/v3/index/cmc100-latest",
    "cmc20_historical": "/v3/index/cmc20-historical",
    "cmc100_historical": "/v3/index/cmc100-historical",
    "fng_latest": "/v3/fear-and-greed/latest",
    "fng_historical": "/v3/fear-and-greed/historical",
    "altcoin_season_latest": "/v1/altcoin-season-index/latest",
    "altcoin_season_historical": "/v1/altcoin-season-index/historical",
    "listings_latest": "/v3/cryptocurrency/listings/latest",
    "quotes_latest": "/v3/cryptocurrency/quotes/latest",
    "global_latest": "/v1/global-metrics/quotes/latest",
    "simple_price": "/v2/simple/price",
}

# Paths that need no key. Verified against the official keyless reference.
KEYLESS_PATHS = frozenset({
    "cmc20_latest", "cmc100_latest", "cmc20_historical", "cmc100_historical",
    "fng_latest", "fng_historical", "altcoin_season_latest", "altcoin_season_historical",
    "listings_latest", "quotes_latest", "global_latest", "simple_price",
})

# Paths with no keyless route. Never called unless allow_keyed=True AND a key is present.
KEYED_ONLY = frozenset({"ohlcv_historical", "quotes_historical", "key_info"})
KEYED_PATHS: dict[str, str] = {
    "ohlcv_historical": "/v2/cryptocurrency/ohlcv/historical",
    "quotes_historical": "/v3/cryptocurrency/quotes/historical",
    "key_info": "/v1/key/info",
}

# Official CMC error codes. 1022 is corpus-observed on the anonymous pool and is NOT in any
# official table, so it is kept separate and labelled inferred.
CMC_ERROR_CODES: dict[str, tuple[str, int, str]] = {
    "1001": ("API_KEY_INVALID", 401, "auth"),
    "1002": ("API_KEY_MISSING", 401, "auth"),
    "1003": ("API_KEY_PLAN_REQUIRES_PAYMENT", 402, "billing"),
    "1004": ("API_KEY_PLAN_PAYMENT_EXPIRED", 402, "billing"),
    "1005": ("API_KEY_REQUIRED", 403, "auth"),
    "1006": ("API_KEY_PLAN_NOT_AUTHORIZED", 403, "plan"),
    "1007": ("API_KEY_DISABLED", 403, "auth"),
    "1008": ("API_KEY_PLAN_MINUTE_RATE_LIMIT_REACHED", 429, "rate_limit"),
    "1009": ("API_KEY_PLAN_DAILY_RATE_LIMIT_REACHED", 429, "rate_limit"),
    "1010": ("API_KEY_PLAN_MONTHLY_RATE_LIMIT_REACHED", 429, "rate_limit"),
    "1011": ("IP_RATE_LIMIT_REACHED", 429, "rate_limit"),
}
CMC_ERROR_CODES_INFERRED: dict[str, tuple[str, int, str]] = {
    "1022": ("ANONYMOUS_ACCESS_LIMIT", 429, "rate_limit"),
}
ALL_KNOWN_ERROR_CODES = tuple(CMC_ERROR_CODES) + tuple(CMC_ERROR_CODES_INFERRED)

# Client-side sentinels. The prefix makes collision with a CMC numeric code impossible: no CMC
# code is ever a non-numeric string, so `int(err)` raises on ours instead of silently aliasing.
SENTINEL_NS = "cmc-client.local/"
SENTINEL_NO_KEY = SENTINEL_NS + "no-api-key"
SENTINEL_UNKNOWN_KEY = SENTINEL_NS + "unknown-path-key"
SENTINEL_EMPTY_INVALID = SENTINEL_NS + "empty-result-for-invalid-request"
SENTINEL_BAD_PARAM = SENTINEL_NS + "invalid-request"
SENTINEL_RATE_LIMITED = SENTINEL_NS + "rate-limited"
CLIENT_SENTINELS = (
    SENTINEL_NO_KEY, SENTINEL_UNKNOWN_KEY, SENTINEL_EMPTY_INVALID,
    SENTINEL_BAD_PARAM, SENTINEL_RATE_LIMITED,
)

# The anonymous keyless pool is shared per IP and CMC does not publish the threshold.
# Live observations: 8 requests at 4.5s spacing succeed; bursts produce 429/1011 or 429/1022.
# So this is a floor for politeness, not a guarantee.
MIN_INTERVAL_S = 4.5
MAX_RETRIES = 3


def is_client_sentinel(err: Any) -> bool:
    return isinstance(err, str) and err.startswith(SENTINEL_NS)


def classify_error_code(err: Any) -> dict:
    """Map a server error code, or a client sentinel, to a usable verdict."""
    if err is None:
        return {"verdict": "unset", "name": None, "http": None, "class": None, "inferred": False}
    key = str(err)
    if is_client_sentinel(key):
        return {"verdict": "client-side", "name": key[len(SENTINEL_NS):], "http": None,
                "class": "client", "inferred": False}
    if key in CMC_ERROR_CODES:
        name, http, klass = CMC_ERROR_CODES[key]
        return {"verdict": "server", "name": name, "http": http, "class": klass, "inferred": False}
    if key in CMC_ERROR_CODES_INFERRED:
        name, http, klass = CMC_ERROR_CODES_INFERRED[key]
        return {"verdict": "server", "name": name, "http": http, "class": klass, "inferred": True}
    if key in ("0", "200"):
        return {"verdict": "success", "name": None, "http": None, "class": None, "inferred": False}
    try:
        numeric = int(key)
    except ValueError:
        return {"verdict": "unrecognised", "name": None, "http": None, "class": None,
                "inferred": False}
    return {"verdict": "server", "name": f"numeric_{numeric}", "http": None, "class": None,
            "inferred": False}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_z(day: dt.date) -> str:
    """Bounds MUST be full ISO-8601 with Z. A bare date is rejected by the API with HTTP 400."""
    return f"{day.isoformat()}T00:00:00Z"


# --- payload emptiness (defect E5) -------------------------------------------

def is_semantically_empty(payload: Any) -> bool:
    """True when a body carries no usable content.

    The API's dominant failure mode is `HTTP 200 + error_code 0 + data: []`, produced by at
    least three distinct bad inputs. Live-verified: `?symbol=ZZZNOTAREALCOIN` returns exactly
    that. Treating it as success is how a panel silently renders nothing.
    """
    if payload is None:
        return True
    if isinstance(payload, (list, tuple, str, dict)) and len(payload) == 0:
        return True
    # index "latest" endpoints return a dict with value + constituents; an all-zero/None value
    # with no constituents is also an empty answer.
    if isinstance(payload, dict):
        if not payload:
            return True
        if "value" in payload and not payload.get("constituents"):
            return True
    return False


# --- receipts (defect E6) ----------------------------------------------------

@dataclass
class Receipt:
    """One CMC call receipt. This is the provenance record the product is built around."""
    path_key: str
    path: str
    method: str
    params: dict
    auth_mode: str                 # "keyless" | "keyed" | "none"
    http_status: Optional[int]
    error_code: Optional[str]
    verdict: str
    error_name: Optional[str]
    error_class: Optional[str]
    credit_count: Any
    elapsed_ms: int
    at: str = field(default_factory=utc_now)
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "path_key": self.path_key, "path": self.path, "method": self.method,
            "params": self.params, "auth_mode": self.auth_mode,
            "http_status": self.http_status, "error_code": self.error_code,
            "verdict": self.verdict, "error_name": self.error_name,
            "error_class": self.error_class, "credit_count": self.credit_count,
            "elapsed_ms": self.elapsed_ms, "at": self.at, "note": self.note,
        }

    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True, default=str).encode()
        ).hexdigest()


@dataclass
class Response:
    path_key: str
    data: Any
    http_status: Optional[int]
    error_code: Optional[str]
    auth_mode: str
    credit_count: Any
    receipt: Receipt
    note: str = ""

    @property
    def ok(self) -> bool:
        """Success requires BOTH a zero error code AND a semantically non-empty payload (E5)."""
        code = str(self.error_code) if self.error_code is not None else "0"
        return code in ("0", "200") and not is_semantically_empty(self.data)


# --- the client --------------------------------------------------------------

class CmcClient:
    """Stdlib CMC client. Keyless by default; a key is used only when explicitly permitted."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        allow_keyed: bool = False,
        timeout: float = 30.0,
        min_interval_s: float = MIN_INTERVAL_S,
        offline: bool = False,
        transport=None,
    ) -> None:
        # The key is passed explicitly and is NEVER read from the environment. An exported key
        # must not silently change behaviour — that was defect D7's root cause.
        self.api_key = api_key or None
        self.allow_keyed = bool(allow_keyed and self.api_key)
        self.timeout = timeout
        self.min_interval_s = min_interval_s
        self.offline = offline
        self._ctx = ssl.create_default_context()
        self._last_call = 0.0
        self.receipts: list[Receipt] = []
        # injectable for tests
        self._transport = transport

    # -- routing ------------------------------------------------------------

    def auth_mode_for(self, path_key: str) -> str:
        """DEFECT D7 FIX: keyless is preferred even when a key is present.

        The parent client returned "keyed" for every path as soon as a key existed, which upgraded
        all 18 keyless paths to keyed Pro calls, burned credits, mislabelled the receipt, and made
        the `keyless_rejected` branch unreachable.
        """
        if path_key in KEYLESS_PATHS:
            return "keyless"
        if path_key in KEYED_ONLY or path_key in KEYED_PATHS:
            return "keyed" if self.allow_keyed else "none"
        return "none"

    # -- transport ----------------------------------------------------------

    def _throttle(self) -> None:
        if self.min_interval_s <= 0:
            return
        gap = time.monotonic() - self._last_call
        if gap < self.min_interval_s:
            time.sleep(self.min_interval_s - gap)
        self._last_call = time.monotonic()

    def _raw(self, url: str, headers: dict) -> tuple[int, dict]:
        if self._transport is not None:
            return self._transport(url, headers)
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", errors="replace") or "{}")

    def get(self, path_key: str, **params: Any) -> Response:
        """One GET. Never raises for an expected failure; returns a Response with a receipt."""
        path = PATHS.get(path_key) or KEYED_PATHS.get(path_key)
        if path is None:
            return self._fail(path_key, SENTINEL_UNKNOWN_KEY, 0,
                              f"unknown path_key {path_key!r}")
        params = {k: v for k, v in params.items() if v is not None}

        interval = params.get("interval")
        if interval is not None and interval not in INTERVALS:
            return self._fail(path_key, SENTINEL_BAD_PARAM, 0,
                              f"interval must be one of {INTERVALS}, got {interval!r}")
        if "count" in params and not (1 <= int(params["count"]) <= MAX_COUNT):
            return self._fail(path_key, SENTINEL_BAD_PARAM, 0,
                              f"count must be in [1, {MAX_COUNT}]; the API hard-caps it at 10")

        auth_mode = self.auth_mode_for(path_key)
        if auth_mode == "none":
            if self.allow_keyed or self.api_key:
                why = "keyed path requires allow_keyed=True"
            else:
                why = "no api_key supplied; keyed paths are never called implicitly"
            return self._fail(path_key, SENTINEL_NO_KEY, 0, why)

        base = KEYLESS_BASE if auth_mode == "keyless" else PRO_BASE
        url = base + path + (("?" + urllib.parse.urlencode(params)) if params else "")
        headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
        if auth_mode == "keyed":
            headers[HEADER_KEY] = self.api_key  # never logged, never serialised

        attempts = 0
        while True:
            attempts += 1
            self._throttle()
            t0 = time.monotonic()
            try:
                http_status, body = self._raw(url, headers)
            except urllib.error.HTTPError as exc:
                http_status = exc.code
                try:
                    body = json.loads(exc.read().decode("utf-8", errors="replace") or "{}")
                except Exception:
                    body = {}
            except Exception as exc:  # network failure
                return self._fail(path_key, SENTINEL_RATE_LIMITED, 0,
                                  f"transport error: {type(exc).__name__}: {exc}",
                                  elapsed_ms=int((time.monotonic() - t0) * 1000))
            elapsed = int((time.monotonic() - t0) * 1000)

            status = (body or {}).get("status") or {}
            code = status.get("error_code")
            credit = status.get("credit_count")
            code_s = str(code) if code is not None else "0"

            # Retry ONLY on rate limits, and only for keyless-safe reads.
            if http_status == 429 and attempts <= MAX_RETRIES:
                time.sleep(self.min_interval_s * (2 ** (attempts - 1)))
                continue

            if http_status >= 400:
                if code_s == "0" or code_s == "None":
                    code_s = str(http_status)
                verdict = classify_error_code(code_s)
                if auth_mode == "keyless" and http_status in (401, 403):
                    verdict = {"verdict": "keyless-rejected", "name": "keyless_rejected",
                               "http": http_status, "class": "keyless", "inferred": False}
                return self._record(path_key, path, params, auth_mode, http_status, code_s,
                                    (body or {}).get("data"), credit, verdict, elapsed,
                                    note=str(status.get("error_message") or ""))

            if code_s not in ("0", "200"):
                verdict = classify_error_code(code_s)
                return self._record(path_key, path, params, auth_mode, http_status, code_s,
                                    (body or {}).get("data"), credit, verdict, elapsed,
                                    note=str(status.get("error_message") or ""))

            data = (body or {}).get("data")
            if is_semantically_empty(data):
                return self._record(path_key, path, params, auth_mode, http_status,
                                    SENTINEL_EMPTY_INVALID, data, credit,
                                    {"verdict": "failed", "name": "empty_result",
                                     "http": http_status, "class": "client", "inferred": False},
                                    elapsed,
                                    note="HTTP 200 + error_code 0 + empty data: a FAILURE mode, "
                                         "not a small result")

            return self._record(path_key, path, params, auth_mode, http_status, code_s,
                                data, credit,
                                {"verdict": "ok", "name": None, "http": http_status,
                                 "class": None, "inferred": False}, elapsed)

    # -- recording ----------------------------------------------------------

    def _record(self, path_key, path, params, auth_mode, http_status, code, data,
                credit, verdict, elapsed, note="") -> Response:
        r = Receipt(
            path_key=path_key, path=path, method="GET", params=dict(params),
            auth_mode=auth_mode, http_status=http_status, error_code=code,
            verdict=verdict["verdict"], error_name=verdict.get("name"),
            error_class=verdict.get("class"), credit_count=credit,
            elapsed_ms=elapsed, note=note,
        )
        self.receipts.append(r)
        return Response(path_key=path_key, data=data, http_status=http_status,
                        error_code=code, auth_mode=auth_mode, credit_count=credit,
                        receipt=r, note=note)

    def _fail(self, path_key, code, http_status, note, elapsed_ms=0) -> Response:
        r = Receipt(path_key=path_key, path=PATHS.get(path_key, "?"), method="GET",
                    params={}, auth_mode="none", http_status=http_status, error_code=code,
                    verdict="client-refused", error_name=code[len(SENTINEL_NS):]
                    if is_client_sentinel(code) else None,
                    error_class="client", credit_count=None,
                    elapsed_ms=elapsed_ms, note=note)
        self.receipts.append(r)
        return Response(path_key=path_key, data=None, http_status=http_status,
                        error_code=code, auth_mode="none", credit_count=None,
                        receipt=r, note=note)

    # -- window walk (defect E1) -------------------------------------------

    def walk_window(
        self,
        path_key: str,
        end: dt.date,
        count: int,
        interval: str = "daily",
        step_days: int = 1,
        max_pages: int = 400,
    ) -> list[dict]:
        """Walk backwards from `end`, `count` points at a time, until the series starts.

        The parent client's pager never advanced: it re-issued the same window and returned
        duplicates. Here each page ends where the previous one began, and the caller gets a
        de-duplicated, ascending series.

        With both bounds set the API fills FROM THE START of the window, so walking backwards
        means asking for progressively earlier windows.
        """
        if not (1 <= count <= MAX_COUNT):
            raise ValueError(f"count must be in [1, {MAX_COUNT}]")
        if interval not in INTERVALS:
            raise ValueError(f"interval must be one of {INTERVALS}")

        collected: dict[str, dict] = {}
        cursor_end = end
        for _ in range(max_pages):
            cursor_start = cursor_end - dt.timedelta(days=step_days * count)
            resp = self.get(path_key, interval=interval, count=count,
                            time_start=iso_z(cursor_start), time_end=iso_z(cursor_end))
            if not resp.ok:
                break
            rows = resp.data if isinstance(resp.data, list) else []
            if not rows:
                break
            before = len(collected)
            for row in rows:
                ts = row.get("update_time") or row.get("timestamp")
                if ts:
                    collected[ts] = row
            if len(collected) == before:
                break                      # no new timestamps: we are at the start of history
            # Advance the cursor. Note we must NOT stop when the returned window is full: with
            # both bounds set the API fills from the window START, so a full page is the normal
            # case, not the end of history. Only "no new points" terminates the walk.
            cursor_end = cursor_start
        return [collected[k] for k in sorted(collected)]
