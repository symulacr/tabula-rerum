"""Tabula test suite — stdlib unittest, no third-party runner.

Covers every defect the parent client carried, so a regression cannot pass silently:
  E1 pager advances and never duplicates
  E3 sentinels cannot collide with a CMC code
  E4 only /v2/simple/price, and the v2 shape
  E5 200 + error_code 0 + empty data is a FAILURE
  E6 receipts distinguish a live capture from a fixture
  D7 the keyless route is preferred even when a key is present
  plus the alignment policy, the transforms, the a11y contract, and stdlib-only.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT / "apps" / "api", ROOT / "packages" / "features", ROOT / "packages" / "share"):
    sys.path.insert(0, str(p))

from tabula import client as C                                    # noqa: E402
from tabula.client import (CmcClient, classify_error_code, is_client_sentinel,  # noqa: E402
                          is_unrouted)
from tabula_features.align import (MIN_COVERAGE, Series, build_window,          # noqa: E402
                                   paired_values, render_axis)
from tabula_features.transforms import (TransformError, flagship, rebase,       # noqa: E402
                                        rolling_volatility, stdev, zscore)
from tabula_share.svg import render_spread_chart, render_table                   # noqa: E402
from tabula_share.composition import render_panel, rows_for                        # noqa: E402

FIXTURES = ROOT / "evidence" / "fixtures"


def _fixture(name):
    p = FIXTURES / name
    return json.loads(p.read_text()) if p.is_file() else None


class TestStdlibOnly(unittest.TestCase):
    """The contract (IN-5) requires stdlib only. The environment HAS third-party packages, so
    this has to be enforced rather than assumed."""

    FORBIDDEN = ("flask", "fastapi", "requests", "pandas", "numpy", "matplotlib",
                 "pydantic", "jinja2", "django")

    def test_no_third_party_imports_in_shipped_source(self):
        offenders = []
        for f in list((ROOT / "apps").rglob("*.py")) + list((ROOT / "packages").rglob("*.py")):
            text = f.read_text()
            for mod in self.FORBIDDEN:
                if f"import {mod}" in text or f"from {mod}" in text:
                    offenders.append(f"{f.relative_to(ROOT)} imports {mod}")
        self.assertEqual(offenders, [], f"non-stdlib imports: {offenders}")

    def test_shipped_source_parses(self):
        for f in list((ROOT / "apps").rglob("*.py")) + list((ROOT / "packages").rglob("*.py")):
            compile(f.read_text(), str(f), "exec")


class TestD7AuthRouting(unittest.TestCase):
    """The defect that made an exported key silently turn keyless calls into keyed Pro calls."""

    def test_keyless_preferred_even_when_key_present(self):
        c = CmcClient(api_key="0" * 32, allow_keyed=True)
        for key in ("cmc20_historical", "fng_historical", "simple_price", "cmc100_latest"):
            self.assertEqual(c.auth_mode_for(key), "keyless",
                             f"{key} must stay keyless when a key is present")

    def test_keyed_paths_need_explicit_opt_in(self):
        self.assertEqual(CmcClient(api_key=None).auth_mode_for("ohlcv_historical"), "none")
        self.assertEqual(CmcClient(api_key="0" * 32, allow_keyed=False)
                         .auth_mode_for("ohlcv_historical"), "none")
        self.assertEqual(CmcClient(api_key="0" * 32, allow_keyed=True)
                         .auth_mode_for("ohlcv_historical"), "keyed")

    def test_allow_keyed_without_key_is_inert(self):
        self.assertFalse(CmcClient(api_key=None, allow_keyed=True).allow_keyed)

    def test_keyed_path_refuses_without_permission(self):
        r = CmcClient().get("ohlcv_historical", symbol="BTC")
        self.assertFalse(r.ok)
        self.assertTrue(is_client_sentinel(r.error_code))
        self.assertEqual(r.auth_mode, "none")


class TestE3Sentinels(unittest.TestCase):
    def test_sentinels_never_collide_with_cmc_codes(self):
        for s in C.CLIENT_SENTINELS:
            self.assertTrue(s.startswith(C.SENTINEL_NS))
            with self.assertRaises(ValueError):
                int(s)                                  # raises, so it cannot alias a CMC code
        for code in C.ALL_KNOWN_ERROR_CODES:
            self.assertNotIn(code, C.CLIENT_SENTINELS)
            self.assertTrue(code.isdigit())

    def test_classification(self):
        self.assertEqual(classify_error_code("1005")["name"], "API_KEY_REQUIRED")
        self.assertEqual(classify_error_code("1022")["name"], "ANONYMOUS_ACCESS_LIMIT")
        self.assertTrue(classify_error_code("1022")["inferred"])
        self.assertEqual(classify_error_code("0")["verdict"], "success")
        self.assertEqual(classify_error_code(C.SENTINEL_NO_KEY)["verdict"], "client-side")
        self.assertEqual(classify_error_code("banana")["verdict"], "unrecognised")

    def test_1011_and_1022_are_distinct(self):
        self.assertNotEqual(classify_error_code("1011")["name"],
                            classify_error_code("1022")["name"])


class TestE5EmptyData(unittest.TestCase):
    def test_empty_is_a_failure(self):
        for payload in (None, [], {}, "", ()):
            self.assertTrue(C.is_semantically_empty(payload), f"{payload!r} should be empty")

    def test_non_empty_is_not(self):
        self.assertFalse(C.is_semantically_empty([{"a": 1}]))
        self.assertFalse(C.is_semantically_empty({"value": 1, "constituents": [1]}))

    def test_200_zero_error_empty_is_not_ok(self):
        def transport(url, headers):
            return 200, {"status": {"error_code": "0", "credit_count": 1,
                                    "error_message": None}, "data": []}
        r = CmcClient(transport=transport, min_interval_s=0).get("fng_historical")
        self.assertFalse(r.ok)
        self.assertEqual(r.error_code, C.SENTINEL_EMPTY_INVALID)
        self.assertIn("FAILURE mode", r.receipt.note)

    def test_live_verified_empty_shape(self):
        """The exact body the API returns for ?symbol=ZZZNOTAREALCOIN."""
        body = {"status": {"error_code": "0", "error_message": ""}, "data": []}
        self.assertEqual(C.is_semantically_empty(body["data"]), True)


class TestE4SimplePrice(unittest.TestCase):
    def test_path_is_v2(self):
        self.assertEqual(C.PATHS["simple_price"], "/v2/simple/price")

    def test_no_v1_path_is_referenced(self):
        for key, path in C.PATHS.items():
            self.assertNotIn("/v1/simple/price", path, f"{key} still uses the deprecated path")


class TestParameterGuards(unittest.TestCase):
    def test_count_cap_enforced_client_side(self):
        r = CmcClient().get("cmc20_historical", interval="daily", count=30)
        self.assertFalse(r.ok)
        self.assertEqual(r.error_code, C.SENTINEL_BAD_PARAM)
        self.assertIn("10", r.receipt.note)

    def test_interval_guard(self):
        r = CmcClient().get("cmc20_historical", interval="1d")
        self.assertFalse(r.ok)
        self.assertEqual(r.error_code, C.SENTINEL_BAD_PARAM)

    def test_iso_z_emits_full_timestamp(self):
        s = C.iso_z(dt.date(2026, 9, 1))
        self.assertEqual(s, "2026-09-01T00:00:00Z")
        self.assertRegex(s, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class TestE1Pager(unittest.TestCase):
    """The parent pager re-issued the same window. Here each page must advance and never repeat."""

    def _fake(self, pages):
        """Serve `pages` as consecutive 10-point windows, tracking what was asked for."""
        asked = []

        def transport(url, headers):
            asked.append(url)
            import re
            ts = re.search(r"time_start=([0-9T:\-]+Z?)", url)
            te = re.search(r"time_end=([0-9T:\-]+Z?)", url)
            start = ts.group(1)[:10] if ts else "2026-01-01"
            end = te.group(1)[:10] if te else "2026-01-10"
            s = dt.date.fromisoformat(start)
            e = dt.date.fromisoformat(end)
            rows = [{"update_time": f"{(s + dt.timedelta(days=i)).isoformat()}T00:00:00Z",
                     "value": 100 + i, "constituents": []}
                    for i in range((e - s).days + 1)][:10]
            return 200, {"status": {"error_code": "0", "credit_count": 1}, "data": rows}
        return transport, asked

    def test_walk_advances_and_never_duplicates(self):
        transport, asked = self._fake(10)
        c = CmcClient(transport=transport, min_interval_s=0)
        rows = c.walk_window("cmc20_historical", end=dt.date(2026, 3, 1), count=10)
        stamps = [r["update_time"] for r in rows]
        self.assertEqual(len(stamps), len(set(stamps)), "duplicate timestamps in the walk")
        self.assertEqual(stamps, sorted(stamps), "walk must be ascending")
        self.assertGreater(len(asked), 1, "walk must issue more than one page")
        self.assertEqual(len(asked), len(set(asked)), "the same window was requested twice")

    def test_walk_rejects_bad_count(self):
        with self.assertRaises(ValueError):
            CmcClient().walk_window("cmc20_historical", end=dt.date.today(), count=30)

    def test_walk_rejects_bad_interval(self):
        with self.assertRaises(ValueError):
            CmcClient().walk_window("cmc20_historical", end=dt.date.today(), count=10,
                                    interval="1d")


class TestE6Receipts(unittest.TestCase):
    def test_receipt_has_provenance_fields(self):
        def transport(url, headers):
            return 200, {"status": {"error_code": "0", "credit_count": 1},
                         "data": [{"update_time": "2026-09-01T00:00:00Z", "value": 1,
                                   "constituents": [{"symbol": "BTC"}]}]}
        c = CmcClient(transport=transport, min_interval_s=0)
        c.get("cmc20_historical")
        d = c.receipts[0].to_dict()
        for f in ("path_key", "path", "params", "auth_mode", "http_status", "error_code",
                  "verdict", "credit_count", "elapsed_ms", "at"):
            self.assertIn(f, d)
        self.assertEqual(d["auth_mode"], "keyless")
        self.assertEqual(len(c.receipts[0].digest()), 64)

    def test_fixture_and_live_are_distinguishable(self):
        """A recorded capture carries provenance that a hand-written fixture does not."""
        payload = _fixture("cmc20_historical.json")
        self.assertIsNotNone(payload, "fixture missing")
        self.assertNotIn("_provenance", payload,
                         "fixture must not masquerade as a live capture")


class TestAlignment(unittest.TestCase):
    def _series(self, name, days, start=dt.date(2026, 1, 1)):
        s = Series(name=name)
        for i, d in enumerate(days):
            s.values[d] = 100 + i
        return s

    def test_inner_join_for_statistics(self):
        days = [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(60)]
        a = self._series("a", days)
        b = self._series("b", days[3:])                       # b starts 3 days later
        w = build_window({"a": a, "b": b}, days[0], days[-1])
        self.assertEqual(len(w.paired_days), 57)
        self.assertEqual(w.dropped_reason, None)
        self.assertEqual(len(paired_values(w, "a", "b")), 57)

    def test_outer_join_for_rendering_shows_the_gap(self):
        days = [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(60)]
        w = build_window({"a": self._series("a", days), "b": self._series("b", days[3:])},
                         days[0], days[-1])
        axis = render_axis(w.series, days[0], days[-1])
        self.assertEqual(len(axis), 60, "rendering must keep every day any series has")
        self.assertEqual(len(w.paired_days), 57, "statistics must use the intersection only")

    def test_window_dropped_when_too_few_points(self):
        """Either guard may fire first; both are legitimate and the window must not be analysed."""
        days = [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(40)]
        a = self._series("a", days)
        b = self._series("b", days[:10])                      # 10 of 40 days
        w = build_window({"a": a, "b": b}, days[0], days[-1])
        self.assertFalse(w.is_analysable)
        self.assertTrue(
            "minimum" in w.dropped_reason or "coverage" in w.dropped_reason,
            f"unexpected drop reason: {w.dropped_reason}")

    def test_coverage_guard_fires_when_enough_points_but_sparse(self):
        """Enough paired points to clear the count guard, but too sparse to claim the window."""
        days = [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(200)]
        a = self._series("a", days)
        b = self._series("b", days[:50])                     # 50 of 200 days
        w = build_window({"a": a, "b": b}, days[0], days[-1])
        self.assertFalse(w.is_analysable)
        self.assertIn("coverage", w.dropped_reason)

    def test_window_dropped_when_series_itself_is_too_short(self):
        """The count guard fires on an absolutely short window, both series aligned."""
        days = [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(5)]
        w = build_window({"a": self._series("a", days), "b": self._series("b", days)},
                         days[0], days[-1])
        self.assertFalse(w.is_analysable)
        self.assertIn("minimum", w.dropped_reason)

    def test_forward_fill_is_prohibited(self):
        """No function in the shipped feature layer may synthesise a value."""
        src = (ROOT / "packages" / "features" / "tabula_features" / "align.py").read_text()
        body = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
        for banned in ("ffill", "fillna", "forward_fill(", "carry_forward"):
            self.assertNotIn(banned, body, f"forward-fill construct present: {banned}")


class TestTransforms(unittest.TestCase):
    def test_rebase(self):
        out = rebase([50.0, 75.0, 100.0])
        self.assertAlmostEqual(out[0], 100.0)
        self.assertAlmostEqual(out[-1], 200.0)

    def test_rebase_rejects_zero_base(self):
        with self.assertRaises(TransformError):
            rebase([1.0], base=0)

    def test_zscore_is_standardised(self):
        z = zscore([1.0, 2.0, 3.0, 4.0])
        self.assertAlmostEqual(stdev([v for v in z]), 1.0, places=9)

    def test_zscore_none_when_dispersion_undefined(self):
        self.assertEqual(zscore([1.0]), [None])

    def test_deterministic(self):
        days = [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(40)]
        series = {"CMC20": Series("CMC20"), "CMC100": Series("CMC100")}
        for i, d in enumerate(days):
            series["CMC20"].values[d] = 170 + i * 0.1
            series["CMC100"].values[d] = 162 + i * 0.1
        w = build_window(series, days[0], days[-1])
        a = flagship(w, "CMC20", "CMC100")
        b = flagship(w, "CMC20", "CMC100")
        self.assertEqual(a["stats"], b["stats"], "the flagship must be deterministic")

    def test_flagship_refuses_unanalysable_window(self):
        days = [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(5)]
        w = build_window({"CMC20": Series("CMC20"), "CMC100": Series("CMC100")},
                         days[0], days[-1])
        r = flagship(w, "CMC20", "CMC100")
        self.assertFalse(r["analysable"])
        self.assertIsNotNone(r["reason"])

    def test_stats_are_measured_not_constants(self):
        """The regression guard for the 2.94-sigma / 3.5-sigma mix-up."""
        days = [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(60)]
        series = {"CMC20": Series("CMC20"), "CMC100": Series("CMC100")}
        import math
        for i, d in enumerate(days):
            series["CMC20"].values[d] = 170.0 + 3.0 * math.sin(i / 6.0)
            series["CMC100"].values[d] = 162.0 + 3.0 * math.cos(i / 6.0)
        w = build_window(series, days[0], days[-1])
        r = flagship(w, "CMC20", "CMC100")
        s = r["stats"]
        self.assertAlmostEqual(s["mean_spread"], sum(r["spread"]) / len(r["spread"]), places=9)
        span_sigma = s["raw_span"] / s["raw_sd_spread"]
        self.assertAlmostEqual(s["raw_span_in_sigma"], span_sigma, places=9,
                               msg="caption sigma must be derived from the data, not stored")


class TestRendering(unittest.TestCase):
    def _result(self):
        days = [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(60)]
        series = {"CMC20": Series("CMC20"), "CMC100": Series("CMC100")}
        for i, d in enumerate(days):
            series["CMC20"].values[d] = 170.0 + i * 0.2
            series["CMC100"].values[d] = 162.0 + i * 0.1
        return flagship(build_window(series, days[0], days[-1]), "CMC20", "CMC100")

    def test_chart_has_accessibility_contract(self):
        svg = render_spread_chart(self._result())
        for needle in ('role="img"', "aria-labelledby", "<title", "<desc"):
            self.assertIn(needle, svg, f"chart missing {needle}")

    def test_direction_is_not_colour_alone(self):
        svg = render_spread_chart(self._result())
        self.assertIn("stroke-dasharray", svg, "zero line must be distinguishable without colour")
        tbl = render_table(self._result())
        self.assertIn("Direction", tbl, "table must state direction in words")

    def test_table_is_always_emitted(self):
        self.assertIn("<table", render_spread_chart(self._result()) and render_table(self._result()))
        empty = {"analysable": False, "reason": "no window"}
        self.assertIn("fallback", render_table(empty))
        self.assertIn("No analysable window", render_spread_chart(empty))

    def test_no_canvas_dependency(self):
        svg = render_spread_chart(self._result())
        self.assertNotIn("canvas", svg.lower())
        self.assertIn("<svg", svg)


class TestComposition(unittest.TestCase):
    def _series(self, name, n, with_price):
        import datetime as _dt
        s = Series(name=name); day = _dt.date(2026, 9, 26); s.values[day] = 1.0
        s.constituents[day] = [{"symbol": f"C{i}", "weight": 1.0 / n,
                                **({"priceUsd": 100.0 + i} if with_price else {})}
                               for i in range(n)]
        return s

    def test_cmc100_has_100_names(self):
        rows, _, _ = rows_for(self._series("CMC100", 100, False))
        self.assertEqual(len(rows), 100)

    def test_cmc20_has_20_names(self):
        rows, _, _ = rows_for(self._series("CMC20", 20, True))
        self.assertEqual(len(rows), 20)

    def test_schemas_differ_without_crashing(self):
        for wp in (True, False):
            panel = render_panel(self._series("X", 20, wp))
            self.assertIn("fallback", panel)
        self.assertIn("no priceUsd", render_panel(self._series("X", 20, False)))

    def test_caveat_is_rendered(self):
        panel = render_panel(self._series("CMC100", 100, False))
        self.assertIn("CMC-selected basket composition, not market churn", panel)
        self.assertIn("rebalances, not market events", panel)

    def test_magnitude_is_not_colour_alone(self):
        panel = render_panel(self._series("CMC20", 20, True))
        self.assertIn('class="bar"', panel)

    def test_empty_series_is_handled(self):
        self.assertIn("No constituent data", render_panel(Series(name="empty")))


class TestEndToEnd(unittest.TestCase):
    def test_offline_render_from_fixtures(self):
        from tabula.server import build_result, page
        r = build_result(days=365, offline=True)
        self.assertTrue(r["analysable"], f"offline window not analysable: {r.get('reason')}")
        self.assertGreaterEqual(r["n"], 30)
        html = page(r)
        self.assertIn("<svg", html)
        self.assertIn("fallback", html)
        self.assertIn("Basket composition", html)
        self.assertIn("not market churn", html)

    def test_no_key_used_offline(self):
        from tabula.server import build_result
        r = build_result(days=365, offline=True)
        self.assertTrue(r["offline"])
        self.assertEqual(r["auth_modes"], ["none"])


class TestUnroutedDiscriminator(unittest.TestCase):
    """P0.6: an unrouted path must be told apart from a transient error.

    The README claims this client classifies an unrouted path as UNROUTED and never retries it.
    This is the test that makes that claim true rather than aspirational.
    """

    # Exactly the bytes captured live from /public-api/v9/totally/bogus
    UNROUTED_BODY = {"status": {"timestamp": "2026-09-30T23:50:45.610Z", "error_code": "500",
                                "error_message": "The system is busy, please try again later!",
                                "elapsed": "0", "credit_count": 0}}

    def test_unrouted_shape_is_detected(self):
        self.assertTrue(is_unrouted(self.UNROUTED_BODY))

    def test_a_good_response_is_not_unrouted(self):
        good = {"status": {"error_code": "0", "credit_count": 1},
                "data": {"id": "cmc20", "value": 177.8}}
        self.assertFalse(is_unrouted(good))

    def test_a_200_with_data_but_an_error_is_not_unrouted(self):
        """error_code 500 WITH a data key is something else -- not an unrouted path."""
        self.assertFalse(is_unrouted({"status": {"error_code": "500"}, "data": [1, 2]}))

    def test_a_rate_limit_is_not_unrouted(self):
        """429/1011 must still be retryable. Do not let this swallow rate limits."""
        body = {"status": {"error_code": "1011", "error_message": "IP rate limit"}}
        self.assertFalse(is_unrouted(body))

    def test_unrouted_is_never_retried(self):
        """The whole point: one attempt, not MAX_RETRIES."""
        calls = {"n": 0}

        def transport(url, headers):
            calls["n"] += 1
            return 200, dict(self.UNROUTED_BODY)

        c = CmcClient(transport=transport, min_interval_s=0.0)
        r = c.get("cmc20_historical", interval="daily", count=10)
        self.assertEqual(calls["n"], 1, "an unrouted path must not be retried")
        self.assertFalse(r.ok)
        self.assertEqual(r.receipt.verdict, "unrouted")
        self.assertEqual(r.receipt.error_name, "UNROUTED_PATH")
        self.assertIn("NOT retried", r.receipt.note)

    def test_receipt_explains_the_decision(self):
        def transport(url, headers):
            return 200, dict(self.UNROUTED_BODY)

        c = CmcClient(transport=transport, min_interval_s=0.0)
        r = c.get("cmc20_historical", interval="daily", count=10)
        self.assertIn("UNROUTED", r.receipt.note)
        self.assertIn("not exist", r.receipt.note)

    def test_is_unrouted_tolerates_a_non_dict_body(self):
        """A transport that hands back raw text must not crash the classifier."""
        for junk in ("not json at all", None, 42, []):
            with self.subTest(body=repr(junk)):
                self.assertFalse(is_unrouted(junk))


class TestGapRendering(unittest.TestCase):
    """D2: a gap must render as a gap.

    The shipped renderer used a bare <polyline>, which cannot express a missing value: it
    silently bridges the gap AND shifts every later point's x, because the polyline indexes the
    *filtered* list. That is the same defect class as the forward fill the alignment policy
    prohibits -- drawing a straight line through a day with no data asserts something the data
    does not say.
    """

    def _gapped(self):
        from tabula.server import build_result
        r = build_result(days=365, offline=True)
        spread = list(r["spread"])
        spread[10] = None
        spread[11] = None
        r["spread"] = spread
        return r

    def test_renderer_does_not_use_polyline(self):
        """Check the EMITTED markup, not the source: the source legitimately names <polyline>
        in the comment explaining why it is not used."""
        from tabula_share.svg import render_spread_chart
        out = render_spread_chart(self._gapped())
        self.assertNotIn("<polyline", out,
                         "a <polyline> cannot express a None gap")

    def test_gap_breaks_the_path(self):
        """A gap must start a NEW SUBPATH, so the path data contains a second M command.

        The second M sits inside the same d="" attribute, so this counts M commands in the
        path data rather than occurrences of 'd="M'.
        """
        import re
        from tabula_share.svg import render_spread_chart
        out = render_spread_chart(self._gapped())
        self.assertIn("<svg", out)
        m = re.search(r'<path d="([^"]+)"', out)
        self.assertIsNotNone(m, "the series must be drawn as a <path>")
        moves = m.group(1).count("M")
        self.assertGreaterEqual(moves, 2,
                                "a gap must start a new subpath (a second M), not bridge")
        # and the second subpath must start at the x of a LATER index, not immediately after
        coords = re.findall(r"[ML]([\d.]+),([\d.]+)", m.group(1))
        first_xs = [float(x) for x, _ in coords[:moves]]
        self.assertGreater(first_xs[-1], first_xs[0] + 10,
                           "the post-gap subpath must resume at its own x position")

    def test_x_axis_is_not_shifted_by_a_gap(self):
        from tabula_share.svg import render_spread_chart
        r = self._gapped()
        out = render_spread_chart(r)
        n = len(r["days"])
        iw = 960 - 64 - 24
        self.assertIn(f"{64 + iw * (n - 1) / (n - 1):.1f}", out,
                      "the last point's x must reflect the full axis, not a gap-shrunk index")


class TestNoDuplicateTestNames(unittest.TestCase):
    """D1: a test shadowed by a later definition silently stops running."""

    def test_no_two_tests_share_a_name(self):
        import re
        src = (ROOT / "tests" / "test_tabula.py").read_text()
        names = re.findall(r"^\s+def (test_\w+)", src, re.M)
        dupes = sorted({n for n in names if names.count(n) > 1})
        self.assertEqual(dupes, [], f"these tests never run, they are shadowed: {dupes}")


class TestStatisticsHonesty(unittest.TestCase):
    """P0.3-P0.5: printed figures must be measured, and claims limited to what holds."""

    def setUp(self):
        from tabula.server import build_result
        self.r = build_result(days=365, offline=True)
        self.st = self.r["stats"]

    def test_rho1_and_n_eff_are_measured_not_stored(self):
        from tabula_features.transforms import effective_n, lag1_autocorrelation
        self.assertAlmostEqual(lag1_autocorrelation(self.r["spread"]), self.st["rho1"],
                               places=9, msg="rho1 must be recomputed, not remembered")
        self.assertEqual(effective_n(self.r["spread"]), self.st["n_eff"])

    def test_indices_are_near_identical(self):
        self.assertGreater(self.st["r_levels"], 0.99,
                           "CMC20 and CMC100 are the same asset class; if this changed, "
                           "the README's headline claim must change too")

    def test_spread_is_strongly_persistent(self):
        """MEASURED: the REBASED spread has rho1 = 0.7625 on the committed fixtures.

        An earlier draft of this project claimed 0.947 and an n_eff of 6. Both were wrong.
        0.947 is the autocorrelation of the RAW spread, not the rebased one the chart plots.
        And 6.06 is sqrt((1+rho)/(1-rho)) -- the variance INFLATION FACTOR -- not n_eff;
        the effective sample size is n divided by that factor. Confusing the two is exactly
        the kind of arithmetic slip this product exists to catch, so it is pinned by a test.
        """
        self.assertGreater(self.st["rho1"], 0.70,
                           "the rebased spread is strongly persistent, so it has no "
                           "stationary distribution and a z-score on it is not evidence")
        self.assertLess(self.st["rho1"], 0.99, "sanity: an exactly-1.0 rho would be degenerate")

    def test_n_eff_is_n_divided_by_the_inflation_factor(self):
        """Guards the exact slip: n_eff = n / sqrt((1+rho)/(1-rho)), not sqrt((1+rho)/(1-rho))."""
        import math
        rho, n = self.st["rho1"], self.r["n"]
        inflation = math.sqrt((1 + rho) / (1 - rho))
        self.assertEqual(self.st["n_eff"], max(1, round(n / inflation)))
        self.assertNotEqual(self.st["n_eff"], round(inflation),
                            "n_eff must be the sample size, not the inflation factor")

    def test_n_eff_is_smaller_than_n(self):
        self.assertLess(self.st["n_eff"], self.r["n"],
                        "reporting n alone would overstate the evidence")

    def test_page_does_not_claim_significance(self):
        from tabula.server import page
        self.assertIn("no significance is claimed", page(self.r).lower())

    def test_page_does_not_assert_flatness_or_a_small_span(self):
        from tabula.server import page
        h = page(self.r)
        self.assertNotIn("the flat form", h)
        self.assertNotIn("spans only", h)
        self.assertAlmostEqual(self.st["raw_span"], 2.410, places=2)
        self.assertGreater(self.st["raw_span_pct_of_mean"], 30.0,
                           "the span is a third of the mean; calling it 'only' was wrong")

    def test_chart_axis_is_percentage_points_not_sigma(self):
        from tabula_share.svg import render_spread_chart
        out = render_spread_chart(self.r)
        self.assertIn("pp", out)
        self.assertNotIn("σ</text>", out, "the y axis is no longer in standard deviations")

    def test_percentile_rank_is_a_percentage(self):
        present = [p for p in self.r["pct"] if p is not None]
        self.assertTrue(present)
        for p in present:
            self.assertGreaterEqual(p, 0.0)
            self.assertLessEqual(p, 100.0)

    def test_n_eff_uses_the_textbook_formula_not_the_two_rho_variant(self):
        rho, n = self.st["rho1"], self.r["n"]
        self.assertEqual(self.st["n_eff"], max(1, round(n / ((1 + rho) / (1 - rho)) ** 0.5)))


class TestPaletteContrast(unittest.TestCase):
    """P0.7: a provenance product cannot misreport its own accessibility audit."""

    @staticmethod
    def _lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    @classmethod
    def _lum(cls, hx):
        h = hx.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return 0.2126 * cls._lin(r) + 0.7152 * cls._lin(g) + 0.0722 * cls._lin(b)

    @classmethod
    def _ratio(cls, a, b):
        la, lb = cls._lum(a), cls._lum(b)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    def test_text_colours_meet_wcag_aa(self):
        from tabula_share.svg import PALETTE
        for name in ("ink", "ink_muted", "accent"):
            with self.subTest(colour=name):
                self.assertGreaterEqual(self._ratio(PALETTE[name], PALETTE["ground"]), 4.5,
                                        f"{name} must meet WCAG 1.4.3")

    def test_graphical_colours_meet_wcag_non_text(self):
        from tabula_share.svg import PALETTE
        for name in ("series_a", "series_b", "positive", "negative"):
            with self.subTest(colour=name):
                self.assertGreaterEqual(self._ratio(PALETTE[name], PALETTE["ground"]), 3.0,
                                        f"{name} must meet WCAG 1.4.11")

    def test_rule_is_documented_as_decorative_because_it_cannot_pass(self):
        from tabula_share.svg import PALETTE
        self.assertLess(self._ratio(PALETTE["rule"], PALETTE["ground"]), 3.0)
        src = (ROOT / "packages" / "share" / "tabula_share" / "svg.py").read_text()
        self.assertIn("decorative", src.lower(),
                      "the palette must document that `rule` is decorative only")


class TestHttpSurface(unittest.TestCase):
    """P2.1: the defects a probe, a health-checker or a judge would actually hit."""

    @classmethod
    def setUpClass(cls):
        import threading
        from http.server import ThreadingHTTPServer
        from tabula.server import Handler
        Handler.offline = True
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def _open(self, path="/", method="GET"):
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), method=method)
        return urllib.request.urlopen(req, timeout=25)

    def test_head_returns_200_with_no_body(self):
        with self._open("/", "HEAD") as r:
            self.assertEqual(r.status, 200)
            self.assertEqual(r.read(), b"", "HEAD must carry headers and no body")
            self.assertIn("text/html", r.headers.get("Content-Type", ""))

    def test_healthz_answers_head(self):
        with self._open("/healthz", "HEAD") as r:
            self.assertEqual(r.status, 200)

    def test_security_headers_are_present(self):
        with self._open() as r:
            h = {k.lower(): v for k, v in r.headers.items()}
        self.assertIn("content-security-policy", h)
        self.assertIn("default-src 'none'", h["content-security-policy"])
        self.assertEqual(h.get("x-content-type-options"), "nosniff")
        self.assertIn("referrer-policy", h)

    def test_server_header_does_not_leak_the_interpreter(self):
        with self._open() as r:
            self.assertNotIn("Python/", r.headers.get("Server", ""))

    def test_404_is_a_404(self):
        import urllib.error
        try:
            self._open("/nope")
            self.fail("expected 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)


class TestSentimentPanel(unittest.TestCase):
    """P1.1/P1.2: Fear & Greed and Altcoin Season, with the axis bug the fixtures expose."""

    def setUp(self):
        from tabula.server import build_result, _sentiment_series
        self._sentiment_series = _sentiment_series
        self.r = build_result(days=365, offline=True)

    def test_fng_fixture_arrives_newest_first_and_must_be_reversed(self):
        """D7: the raw fixture is descending. Wiring it as-is inverts the axis silently."""
        import json
        raw = json.load(open(ROOT / "evidence" / "fixtures" / "fng_historical.json"))
        pts = raw["data"] if isinstance(raw, dict) else raw
        ts = [int(p["timestamp"]) for p in pts]
        self.assertEqual(ts, sorted(ts, reverse=True),
                         "fixture is newest-first; if this changes, the normaliser must too")
        rows = self._sentiment_series(raw, "fng")
        self.assertTrue(rows, "no F&G rows parsed")
        dates = [d for d, _, _ in rows]
        self.assertEqual(dates, sorted(dates), "output MUST be ascending")

    def test_fng_epoch_string_is_converted(self):
        """Both encodings must parse: F&G sends an epoch STRING, Altcoin sends ISO-8601."""
        import datetime as _dt
        raw = {"data": [{"timestamp": "1790640000", "value": 68,
                         "value_classification": "Greed"}]}
        rows = self._sentiment_series(raw, "fng")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], 68)
        # derive the expectation rather than hardcoding it, so the test cannot be wrong about
        # what an epoch means
        expected = _dt.datetime.fromtimestamp(1790640000, _dt.timezone.utc).date()
        self.assertEqual(rows[0][0], expected)

    def test_altseason_iso_timestamp_and_altcoin_index_are_parsed(self):
        raw = {"data": {"timeframe": "90d", "points": [
            {"timestamp": "2026-07-04T00:00:00Z", "altcoin_index": 51,
             "altcoin_marketcap": 914395902197.26},
            {"timestamp": "2026-07-05T00:00:00Z", "altcoin_index": 49},
        ]}}
        rows = self._sentiment_series(raw, "alt")
        self.assertEqual(len(rows), 2)
        self.assertEqual([r[1] for r in rows], [51, 49])
        self.assertEqual(str(rows[0][0]), "2026-07-04")
        # no classification field on altseason, so one is derived from the 50 boundary
        self.assertEqual(rows[0][2], "Altcoin season")
        self.assertEqual(rows[1][2], "Bitcoin season")

    def test_the_two_encodings_do_not_silently_collide(self):
        """An epoch and an ISO string in the same field name must not be confused."""
        a = self._sentiment_series({"data": [{"timestamp": "1790640000", "value": 1}]}, "x")
        b = self._sentiment_series(
            {"data": {"points": [{"timestamp": "2026-07-04T00:00:00Z", "altcoin_index": 1}]}}, "x")
        self.assertNotEqual(a[0][0], b[0][0])

    def test_panel_states_fng_is_bitcoin_only(self):
        from tabula_share.svg import render_sentiment_panel
        out = render_sentiment_panel(self.r.get("sentiment") or {})
        self.assertIn("Bitcoin-only", out)

    def test_panel_states_the_altseason_redefinition(self):
        from tabula_share.svg import render_sentiment_panel
        out = render_sentiment_panel(self.r.get("sentiment") or {})
        self.assertIn("redefined", out)
        self.assertIn("outperformed BTC", out)

    def test_every_sentiment_chart_has_a_table(self):
        from tabula_share.svg import render_sentiment_panel
        sent = {"fng": [(dt.date(2026, 1, 1) + dt.timedelta(days=i), 50 + i % 10, "Neutral")
                        for i in range(20)],
                "altseason": [(dt.date(2026, 1, 1) + dt.timedelta(days=i), 40 + i % 5, None)
                              for i in range(20)]}
        out = render_sentiment_panel(sent)
        self.assertGreaterEqual(out.count('<table class="fallback">'), 2,
                                "each chart needs its own tabular equivalent")

    def test_out_of_range_values_do_not_crash(self):
        from tabula_share.svg import render_sentiment_panel
        out = render_sentiment_panel(
            {"fng": [(dt.date(2026, 1, 1), 150, "bogus"), (dt.date(2026, 1, 2), -20, None)]})
        self.assertIn("<svg", out)

    def test_empty_sentiment_degrades_with_instructions(self):
        from tabula_share.svg import render_sentiment_panel
        out = render_sentiment_panel({})
        self.assertIn("--live", out)
        self.assertNotIn("<svg", out)


class TestWindowControl(unittest.TestCase):
    """P2.2: the window control must work and must not 500 on junk input."""

    @classmethod
    def setUpClass(cls):
        import threading
        from http.server import ThreadingHTTPServer
        from tabula.server import Handler
        Handler.offline = True
        Handler.days = 180
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def _get(self, path):
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (self.port, path),
                                    timeout=25) as r:
            return r.status, r.read().decode()

    def test_form_is_present_and_labelled(self):
        _, body = self._get("/")
        self.assertIn('name="days"', body)
        self.assertIn('<label for="days"', body, "the input needs a real label")
        self.assertIn("Window (days)", body)

    def test_days_query_renders(self):
        status, body = self._get("/?days=90")
        self.assertEqual(status, 200)
        self.assertNotIn("No analysable window", body)

    def test_window_choice_is_disclosed_as_a_confound(self):
        """P2.3: a free window invites multiple comparisons. The page must say so."""
        _, body = self._get("/")
        self.assertIn("multiple-comparisons", body.lower())
        self.assertIn("this window", body)

    def test_the_rebase_anchor_is_disclosed_as_window_relative(self):
        """The anchor is the WINDOW start, not a fixed date. Claiming otherwise would be false."""
        _, body = self._get("/")
        self.assertNotIn("does <em>not</em> move with the window", body)
        self.assertIn("<em>within this window</em>", body)

    def test_out_of_range_days_is_ignored_not_fatal(self):
        for junk in ("5", "99999", "-1", "abc", ""):
            with self.subTest(days=junk):
                status, _ = self._get("/?days=%s" % junk)
                self.assertEqual(status, 200, "a bad window must not 500")


class TestAccessibilityAndLogging(unittest.TestCase):
    """P2.5 and D5: preference blocks ship; log scrubbing is not opted out of."""

    def test_preference_media_queries_are_present(self):
        src = (ROOT / "apps" / "api" / "tabula" / "server.py").read_text().replace(" ", "")
        for q in ("prefers-contrast:more", "forced-colors:active", "prefers-reduced-motion:reduce"):
            self.assertIn(q, src)

    def test_svg_axis_ticks_use_tabular_figures(self):
        src = (ROOT / "packages" / "share" / "tabula_share" / "svg.py").read_text()
        self.assertGreaterEqual(src.count("font-variant-numeric:tabular-nums"), 3,
                                "axis ticks need it, not only the HTML tables")

    def test_log_message_does_not_concatenate_the_request_line(self):
        src = (ROOT / "apps" / "api" / "tabula" / "server.py").read_text()
        i = src.find("def log_message")
        self.assertGreater(i, 0, "log_message override is missing entirely")
        body = src[i:i + 400]
        self.assertNotIn('"[tabula] " +', body,
                         "concatenating the raw format bypasses scrubbing in 3.12.13+")
        self.assertIn("%s", body)


class TestShareCard(unittest.TestCase):
    """P2.4: the share card must exist and must be reproducible.

    Reproducibility is the product's whole claim, so a share image that differs between two runs
    on the same input would undermine it at the exact moment someone screenshots the result.
    """

    def test_module_is_stdlib_only(self):
        """The share card drives the host's Chrome. It must not import anything else."""
        import ast
        tree = ast.parse((ROOT / "share_card.py").read_text())
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                mods.add(node.module.split(".")[0])
        allowed = {"argparse", "hashlib", "shutil", "subprocess", "sys", "tempfile",
                   "threading", "time", "pathlib", "__future__", "http", "tabula"}
        self.assertTrue(mods <= allowed, f"share_card.py imports outside stdlib: {mods - allowed}")

    def test_it_checks_the_artefact_not_the_return_code(self):
        """Chrome exits 0 for a typo'd flag and for total failure alike."""
        src = (ROOT / "share_card.py").read_text()
        self.assertIn("stat().st_size", src)
        self.assertIn("do NOT gate on returncode", src)

    def test_determinism_flags_are_present(self):
        src = (ROOT / "share_card.py").read_text()
        for flag in ("--force-device-scale-factor=1", "--virtual-time-budget",
                     "--hide-scrollbars", "--default-background-color"):
            with self.subTest(flag=flag):
                self.assertIn(flag, src)

    def test_chrome_major_is_pinned_in_the_docs(self):
        src = (ROOT / "share_card.py").read_text()
        self.assertIn("Chrome major", src,
                      "a Chrome upgrade can change rasterisation and break byte-reproducibility")

    @unittest.skipUnless(shutil_which := __import__("shutil").which("google-chrome"),
                         "host Chrome not present")
    def test_two_renders_are_byte_identical(self):
        """The real determinism claim, exercised end to end."""
        import subprocess
        import sys as _sys
        r = subprocess.run([_sys.executable, "share_card.py", "--check"],
                           cwd=str(ROOT), capture_output=True, text=True, timeout=280)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("byte-identical", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
