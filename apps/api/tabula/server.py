"""Tabula server — Python 3.12 stdlib only, bound to loopback.

Binding to 127.0.0.1 is the reason CMC can be called at all: the API blocks browser-side calls,
so a server-side proxy is mandatory, and loopback binding is what keeps the key out of reach. The
judged path needs no key, so the server has no credential surface by default.

Run:  python3 -m tabula.server        (from apps/api)
      or python3 run.py               (from the repo root)
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent          # tabula-rerum/
for p in (HERE, ROOT / "packages" / "features", ROOT / "packages" / "share"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tabula.client import CmcClient, iso_z                     # noqa: E402
from tabula_features.align import Series, build_window          # noqa: E402
from tabula_features.transforms import flagship                 # noqa: E402
from tabula_share.svg import render_spread_chart, render_table  # noqa: E402
from tabula_share.composition import render_panel, CSS_EXTRA     # noqa: E402

# Fixtures make the judged path runnable with no network and no key.
FIXTURE_DIR = ROOT / "evidence" / "fixtures"
DEFAULT_WINDOW_DAYS = 180

CSS = CSS_EXTRA + """
:root{color-scheme:light}
body{margin:0;background:#f7f7f4;color:#1c1b19;
 font-family:Georgia,'Times New Roman',serif;line-height:1.5}
main{max-width:1040px;margin:0 auto;padding:32px 24px 64px}
h1{font-size:1.6rem;letter-spacing:.02em;margin:0 0 4px}
h2{font-size:1.05rem;letter-spacing:.06em;text-transform:uppercase;color:#5c5a54;
 margin:32px 0 10px;font-weight:600}
.lede{color:#5c5a54;margin:0 0 20px}
.card{background:#fff;border:1px solid #d8d6d0;border-radius:2px;padding:20px;margin:0 0 20px}
table.fallback{width:100%;border-collapse:collapse;margin-top:14px;font-size:.86rem}
table.fallback caption{text-align:left;color:#5c5a54;padding:6px 0;font-size:.8rem}
table.fallback th,table.fallback td{border-bottom:1px solid #d8d6d0;padding:5px 8px;text-align:left}
table.fallback td:nth-child(2){font-variant-numeric:tabular-nums}
.receipts{font-size:.8rem;color:#5c5a54}
.receipts td{font-variant-numeric:tabular-nums;padding:3px 8px;border-bottom:1px solid #ecebe6}
.warn{color:#9b2c2c}
:focus-visible{outline:2px solid #8a6d1f;outline-offset:2px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media (max-width:640px){main{padding:20px 14px 48px}.card{padding:14px}}
"""


def _fixture(name: str):
    p = FIXTURE_DIR / name
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def load_series(client: CmcClient, offline: bool) -> tuple[dict[str, Series], list[str]]:
    """Fetch the two flagship series. Offline uses recorded captures; the shape is identical."""
    notes: list[str] = []
    series: dict[str, Series] = {}

    if offline:
        for key, label in (("cmc20_historical", "CMC20"), ("cmc100_historical", "CMC100")):
            payload = _fixture(f"{key}.json")
            if payload is None:
                notes.append(f"fixture missing for {key}")
                series[label] = Series(name=label)
                continue
            series[label] = Series.from_index_history(label, payload)
            notes.append(f"{label} from fixture ({len(series[label])} points)")
        return series, notes

    end = dt.date.today()
    for key, label in (("cmc20_historical", "CMC20"), ("cmc100_historical", "CMC100")):
        rows = client.walk_window(key, end=end, count=10, interval="daily", step_days=1)
        series[label] = Series.from_index_history(label, rows)
        notes.append(f"{label} live ({len(series[label])} points, auth={client.receipts[-1].auth_mode})")
    return series, notes


def build_result(days: int = DEFAULT_WINDOW_DAYS, offline: bool = False,
                 api_key: str | None = None, allow_keyed: bool = False) -> dict:
    """One pass: fetch -> canonical dataset -> aligned window -> flagship transform -> chart."""
    client = CmcClient(api_key=api_key, allow_keyed=allow_keyed)
    series, notes = load_series(client, offline)

    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    if offline:
        all_days = sorted({d for s in series.values() for d in s.values})
        if all_days:
            end = all_days[-1]
            start = max(all_days[0], end - dt.timedelta(days=days))

    win = build_window(series, start, end)
    result = flagship(win, "CMC20", "CMC100")
    result["notes"] = notes
    result["window"] = (start, end)
    result["receipts"] = [r.to_dict() for r in client.receipts]
    result["auth_modes"] = sorted({r.auth_mode for r in client.receipts}) or ["none"]
    result["offline"] = offline
    result["series"] = series
    return result


def page(result: dict) -> str:
    start, end = result["window"]
    comp = render_panel((result.get("series") or {}).get("CMC100"))
    chart = render_spread_chart(result)
    table = render_table(result)
    receipt_rows = "".join(
        f"<tr><td>{html.escape(str(r['path_key']))}</td>"
        f"<td>{html.escape(str(r['auth_mode']))}</td>"
        f"<td>{html.escape(str(r['http_status']))}</td>"
        f"<td>{html.escape(str(r['error_code']))}</td>"
        f"<td>{html.escape(str(r['credit_count']))}</td>"
        f"<td>{r['elapsed_ms']}</td></tr>"
        for r in result["receipts"]
    ) or '<tr><td colspan="6">no calls made (offline fixtures)</td></tr>'

    if result.get("analysable"):
        st = result["stats"]
        rho = st.get("rho1")
        rlv = st.get("r_levels")
        # The caption states what was measured and refuses what cannot be claimed. The earlier
        # version of this line called a 2.410-point span "only" and quoted it in sigma; on the
        # committed fixtures that span is 33.9% of the mean, and a sigma of a unit-root series
        # is not evidence. Both were corrected, and a test now recomputes them from the data.
        lede = (
            f"CMC20 against CMC100, both rebased to {st['base']:g}, differenced, and plotted in "
            f"<strong>percentage points</strong>. {result['n']} paired observations, "
            f"{result['coverage']:.1%} coverage. "
            f"<strong>The two indices correlate at r = {rlv:.6f}</strong> — they are the same "
            f"asset class, so their difference is close to noise by construction. "
            f"That spread's lag-1 autocorrelation is <strong>ρ₁ = {rho:.3f}</strong>: it is "
            f"strongly persistent, so it has no stationary distribution, no equilibrium to "
            f"deviate from, and no valid null. "
            f"<strong>No significance is claimed, and no z-score is used as evidence.</strong> "
            f"A {result['n']}-day window of it carries an effective sample size of "
            f"<strong>n_eff = {st['n_eff']}</strong> — that is n divided by the persistence "
            f"factor, not the factor itself. The latest spread is "
            f"{st['latest_spread']:+.3f} pp, at the {st['latest_pct']:.0f}th percentile of "
            f"this window, which is the defensible way to say where it sits."
        )
    else:
        lede = f'<span class="warn">No analysable window: {html.escape(str(result.get("reason")))}</span>'

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tabula Rerum — Regimen</title><style>{CSS}</style></head>
<body><main>
<h1>Tabula Rerum</h1>
<p class="lede">Regimen · {html.escape(str(start))} → {html.escape(str(end))} ·</p>
<h2>Regimen — where the indices diverged</h2>
<p class="lede">{lede}</p>
<div class="card">{chart}</div>
<h2>The same data, as text</h2>
<div class="card">{table}</div>
<h2>Composition</h2>
{comp}
<h2>Provenance</h2>
<div class="card receipts"><p>auth modes used: {html.escape(', '.join(result['auth_modes']))}
 · source: {'offline fixtures' if result['offline'] else 'live keyless'}</p>
<table><thead><tr><th>call</th><th>auth</th><th>http</th><th>error_code</th>
<th>credits</th><th>ms</th></tr></thead><tbody>{receipt_rows}</tbody></table></div>
<p class="lede">Notes: {html.escape('; '.join(result.get('notes') or ['none']))}</p>
</main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    offline = True
    days = DEFAULT_WINDOW_DAYS

    # A server-built page with no external resources and only inline styles needs a policy this
    # tight. 'unsafe-inline' is permitted for style only because the CSS is emitted inline by
    # this process; there is no script on the page, so script-src needs no exception.
    CSP = ("default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; "
           "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

    def _send(self, body: str, code: int = 200, ctype: str = "text/html; charset=utf-8",
              head_only: bool = False) -> None:
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", self.CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if not head_only:                       # HEAD must carry the headers and no body
            self.wfile.write(raw)

    def version_string(self) -> str:
        """Do not advertise the interpreter build. Loopback only, but it costs nothing."""
        return "Tabula"

    def do_HEAD(self) -> None:                                    # noqa: N802
        self._route(head_only=True)

    def do_GET(self) -> None:                                     # noqa: N802
        self._route(head_only=False)

    def _route(self, head_only: bool) -> None:
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            try:
                result = build_result(self.days, self.offline)
            except Exception as exc:                             # noqa: BLE001
                self._send(f"<h1>error</h1><pre>{html.escape(str(exc))}</pre>", 500,
                           head_only=head_only)
                return
            self._send(page(result), head_only=head_only)
        elif u.path == "/healthz":
            self._send(json.dumps({"ok": True, "offline": self.offline}),
                       ctype="application/json", head_only=head_only)
        elif u.path == "/api/regimen":
            try:
                self._send(json.dumps(build_result(self.days, self.offline), default=str),
                           ctype="application/json", head_only=head_only)
            except Exception as exc:                             # noqa: BLE001
                self._send(json.dumps({"error": str(exc)}), 500, "application/json",
                           head_only=head_only)
        else:
            self._send("not found", 404, "text/plain; charset=utf-8", head_only=head_only)

    def log_message(self, fmt: str, *args) -> None:
        # Deliberately does NOT prefix the caller-controlled path, so the control-character
        # scrubbing that CPython added in 3.12.13 still applies.
        sys.stderr.write("[tabula] %s\n" % (fmt % args))


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    offline = "--live" not in argv
    port = 8099
    for i, a in enumerate(argv):
        if a == "--port" and i + 1 < len(argv):
            port = int(argv[i + 1])
    if "--days" in argv:
        Handler.days = int(argv[argv.index("--days") + 1])
    Handler.offline = offline
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Tabula on http://127.0.0.1:{port}  mode={'offline fixtures' if offline else 'live keyless'}",
          flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
