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
from tabula.client import CmcClient, classify_error_code, is_client_sentinel  # noqa: E402
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

    def test_window_dropped_when_too_few_points(self):
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
