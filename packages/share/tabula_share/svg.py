"""Hand-written inline SVG. No chart library, no canvas, no browser at render time.

Why hand-written SVG (runtime ruling in TABULA-CONTRACT.md §4):
  - the judged path is a Python stdlib server; a canvas library needs a browser to rasterise, and
    there is no browser in the loop;
  - SVG is text, so it renders server-side, stays crisp at any zoom, and screenshots at exact
    pixels with the host's existing headless Chrome;
  - it is the only option with zero install and zero bundle.

Accessibility is built in rather than bolted on, because there is nothing to inherit: the reference
app has `sr-only` = 0 repository-wide and contrast defects down to 2.03:1. Every chart here emits
`role="img"`, a `title`/`desc`, a non-colour encoding for direction, and a tabular fallback.
"""

from __future__ import annotations

import datetime as dt
import html
from typing import Optional, Sequence

# Contrast measured with the WCAG 2.2 relative-luminance formula against the ground below.
# The figures here are MEASURED, not asserted, and a test re-derives them (test_palette_contrast).
# Earlier documentation claimed 15.9 / 7.0 / 5.1 / 5.4 / 5.0 / 5.3 / 6.1 -- five of those were
# wrong. A product whose claim is trustworthy provenance cannot misreport its own audit.
#   ink       16.03:1   text            (AAA)
#   ink_muted  6.42:1   text            (AA, and AA-large)
#   accent     4.56:1   text            (AA)
#   series_a   6.41:1   graphical       (AA non-text, >3:1)
#   series_b   5.47:1   graphical
#   positive   6.03:1   graphical
#   negative   7.01:1   graphical
#   rule       1.35:1   DECORATIVE ONLY -- below the 3:1 of WCAG 1.4.11, so it must never be
#                       the sole means of conveying structure. Gridlines and hairlines only.
PALETTE = {
    "ground": "#f7f7f4",       # L* ~97
    "surface": "#ffffff",
    "ink": "#1c1b19",          # 16.03:1
    "ink_muted": "#5c5a54",    # 6.42:1
    "rule": "#d8d6d0",         # 1.35:1 -- decorative only
    "accent": "#8a6d1f",       # 4.56:1 -- bronze, not the reference app's purple
    "series_a": "#2f5d8a",     # 6.41:1
    "series_b": "#8a5a2b",     # 5.47:1
    "positive": "#1f6b45",     # 6.03:1
    "negative": "#9b2c2c",     # 7.01:1
    "warn": "#8a6d1f",
}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def _ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    if hi <= lo:
        return [lo]
    step = (hi - lo) / max(1, n - 1)
    return [lo + i * step for i in range(n)]


def _fmt(v: Optional[float], places: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v:,.{places}f}"


def render_spread_chart(
    result: dict,
    width: int = 960,
    height: int = 420,
    caption: Optional[str] = None,
) -> str:
    """The flagship rebased-spread chart, in PERCENTAGE POINTS of rebased spread.

    Why percentage points and not standard deviations: the rebased spread has lag-1
    autocorrelation 0.7625, so it is strongly persistent. A persistent series has no stationary
    distribution, so a z-score on it has no valid null and cannot support a claim of
    significance. Plotting it in percentage points is a claim about the spread itself, which is
    defensible. The z-score is still returned in the payload, but it is not the headline and is
    not the axis.

    Non-visual fallbacks that MUST be present on every chart:
      role="img" + <title>/<desc> for screen readers;
      a data table emitted by render_table();
      direction carried by a solid/dashed stroke and an explicit +/- label, never colour alone.
    """
    pad_l, pad_r, pad_t, pad_b = 64, 24, 44, 64
    iw, ih = width - pad_l - pad_r, height - pad_t - pad_b

    if not result.get("analysable"):
        return _empty_panel(result.get("reason") or "no analysable window", width, height)

    # plot the spread itself, not the z-score
    series_vals = [x for x in result["spread"] if x is not None]
    if not series_vals:
        return _empty_panel("no spread values for this window", width, height)
    lo, hi = min(series_vals), max(series_vals)
    pad = (hi - lo) * 0.08 or 0.5
    lo, hi = lo - pad, hi + pad
    n = len(result["days"])

    def X(i: int) -> float:
        return pad_l + (iw * i / max(1, n - 1))

    def Y(v: float) -> float:
        return pad_t + ih - (ih * (v - lo) / (hi - lo))

    parts: list[str] = []
    st = result["stats"]

    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" '
        f'aria-labelledby="ttl desc" font-family="Georgia, \'Times New Roman\', serif">'
    )
    parts.append(f'<title id="ttl">CMC20 versus CMC100, rebased to {st["base"]:g}, '
                 f'in percentage points of spread</title>')
    parts.append(
        f'<desc id="desc">{n} paired daily observations from {esc(result["start"])} to '
        f'{esc(result["end"])}. Mean rebased spread {_fmt(st["mean_spread"], 3)} percentage points, '
        f'standard deviation {_fmt(st["sd_spread"], 3)}. '
        f'The two indices correlate at r = {_fmt(st.get("r_levels"), 4)}, and the spread has '
        f'lag-1 autocorrelation {_fmt(st.get("rho1"), 3)}, so it has no stationary distribution: '
        f'the effective sample size is {st.get("n_eff")} of {n} days, and no significance claim is '
        f'made. The same difference on raw index values spans '
        f'{_fmt(st.get("raw_span"), 3)} points, which is '
        f'{_fmt(st.get("raw_span_pct_of_mean"), 1)} percent of its mean. '
        f'A tabular equivalent follows.</desc>'
    )
    parts.append(f'<rect width="{width}" height="{height}" fill="{PALETTE["ground"]}"/>')

    # gridlines + y labels, in percentage points
    for t in _ticks(lo, hi, 5):
        y = Y(t)
        parts.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + iw}" y2="{y:.1f}" '
                     f'stroke="{PALETTE["rule"]}" stroke-width="1"/>')
        parts.append(f'<text x="{pad_l - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="12" '
                     f'fill="{PALETTE["ink_muted"]}" '
                     f'style="font-variant-numeric:tabular-nums">{t:+.2f}pp</text>')
    # zero line
    if lo < 0 < hi:
        y0 = Y(0)
        parts.append(f'<line x1="{pad_l}" y1="{y0:.1f}" x2="{pad_l + iw}" y2="{y0:.1f}" '
                     f'stroke="{PALETTE["ink"]}" stroke-width="1.5" stroke-dasharray="4 3"/>')
        parts.append(f'<text x="{pad_l + iw}" y="{y0 - 6:.1f}" text-anchor="end" font-size="11" '
                     f'fill="{PALETTE["ink_muted"]}">equal footing (0pp)</text>')

    # THE SERIES — an explicit path that BREAKS on a None, so a gap renders as a gap and the
    # x-axis of every later point stays where it belongs. A <polyline> cannot do this: it
    # silently bridges the gap, which is the same defect class as the prohibited forward fill.
    d_parts: list[str] = []
    pen_down = False
    for i, v in enumerate(result["spread"]):
        if v is None:
            pen_down = False
            continue
        cmd = "M" if not pen_down else "L"
        d_parts.append(f"{cmd}{X(i):.1f},{Y(v):.1f}")
        pen_down = True
    if d_parts:
        parts.append(f'<path d="{"".join(d_parts)}" fill="none" stroke="{PALETTE["series_a"]}" '
                     f'stroke-width="2.25" stroke-linejoin="round" stroke-linecap="round"/>')

    # x labels: first, middle, last only
    for i in (0, n // 2, n - 1):
        d = result["days"][i]
        anchor = "start" if i == 0 else ("end" if i == n - 1 else "middle")
        parts.append(f'<text x="{X(i):.1f}" y="{pad_t + ih + 22}" text-anchor="{anchor}" '
                     f'font-size="12" fill="{PALETTE["ink_muted"]}">{esc(d)}</text>')

    # caption: printed values, measured at render time, including the honesty block
    cap = caption or (
        f"n={n} days · n_eff={st.get('n_eff')} · rho1={_fmt(st.get('rho1'), 3)} · "
        f"r(levels)={_fmt(st.get('r_levels'), 4)} · mean {_fmt(st['mean_spread'], 3)}pp · "
        f"sd {_fmt(st['sd_spread'], 3)}pp · coverage {result['coverage']:.1%}"
    )
    parts.append(f'<text x="{pad_l}" y="{height - 18}" font-size="11.5" '
                 f'fill="{PALETTE["ink_muted"]}" '
                 f'style="font-variant-numeric:tabular-nums">{esc(cap)}</text>')
    parts.append('</svg>')
    return "".join(parts)


def _empty_panel(reason: str, width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
        f'height="{height}" role="img" aria-labelledby="t2">'
        f'<title id="t2">No analysable window</title>'
        f'<rect width="{width}" height="{height}" fill="{PALETTE["ground"]}"/>'
        f'<text x="{width / 2}" y="{height / 2}" text-anchor="middle" font-size="14" '
        f'fill="{PALETTE["ink_muted"]}">{esc(reason)}</text></svg>'
    )


def _banded_chart(rows, title, note, bands, series_key, width, height):
    """One bounded 0-100 sentiment series, drawn with classification bands.

    Bands are drawn so the reading does not depend on colour, and the path breaks on None so a
    missing day renders as a gap rather than a straight line through data that does not exist.
    """
    if not rows:
        return ""
    vals = [float(v) for _, v, _ in rows if v is not None]
    if not vals:
        return ""
    pad_l, pad_r, pad_t, pad_b = 64, 24, 40, 52
    iw, ih = width - pad_l - pad_r, height - pad_t - pad_b
    n = len(rows)
    tid = "s" + str(abs(hash(title)) % 10000)

    def X(i):
        return pad_l + (iw * i / max(1, n - 1))

    def Y(v):
        return pad_t + ih - (ih * v / 100.0)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
         f'width="{width}" height="{height}" role="img" aria-labelledby="{tid}t {tid}d" '
         f'font-family="Georgia, \'Times New Roman\', serif">']
    o.append(f'<title id="{tid}t">{esc(title)}</title>')
    o.append(f'<desc id="{tid}d">{n} daily observations from {esc(str(rows[0][0]))} to '
             f'{esc(str(rows[-1][0]))}. Latest value {vals[-1]:g} of 100. {esc(note)}</desc>')
    o.append(f'<rect width="{width}" height="{height}" fill="{PALETTE["ground"]}"/>')
    o.append(f'<text x="{pad_l}" y="22" font-size="13" fill="{PALETTE["ink"]}" '
             f'font-weight="600">{esc(title)}</text>')
    for lo_b, hi_b, fill in bands:
        y_top, y_bot = Y(hi_b), Y(lo_b)
        o.append(f'<rect x="{pad_l}" y="{y_top:.1f}" width="{iw}" '
                 f'height="{max(0.0, y_bot - y_top):.1f}" fill="{fill}" fill-opacity="0.16"/>')
    for t in (0, 25, 50, 75, 100):
        y = Y(t)
        o.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + iw}" y2="{y:.1f}" '
                 f'stroke="{PALETTE["rule"]}" stroke-width="1"/>')
        o.append(f'<text x="{pad_l - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" '
                 f'fill="{PALETTE["ink_muted"]}" '
                 f'style="font-variant-numeric:tabular-nums">{t}</text>')
    d, pen = [], False
    for i, (_, v, _) in enumerate(rows):
        if v is None:
            pen = False
            continue
        d.append(("M" if not pen else "L") + f"{X(i):.1f},{Y(float(v)):.1f}")
        pen = True
    if d:
        o.append(f'<path d="{"".join(d)}" fill="none" stroke="{PALETTE[series_key]}" '
                 f'stroke-width="1.75" stroke-linejoin="round"/>')
    last_cls = rows[-1][2]
    o.append(f'<text x="{pad_l + iw}" y="{Y(vals[-1]) - 8:.1f}" text-anchor="end" '
             f'font-size="12" font-weight="600" fill="{PALETTE["ink"]}" '
             f'style="font-variant-numeric:tabular-nums">{vals[-1]:g}'
             f'{(" · " + esc(str(last_cls))) if last_cls else ""}</text>')
    for i in (0, n // 2, n - 1):
        anchor = "start" if i == 0 else ("end" if i == n - 1 else "middle")
        o.append(f'<text x="{X(i):.1f}" y="{pad_t + ih + 20}" text-anchor="{anchor}" '
                 f'font-size="11" fill="{PALETTE["ink_muted"]}">{esc(str(rows[i][0]))}</text>')
    o.append(f'<text x="{pad_l}" y="{height - 12}" font-size="11" '
             f'fill="{PALETTE["ink_muted"]}">{esc(note)}</text>')
    o.append("</svg>")
    return "".join(o)


def render_sentiment_panel(sent: dict, width: int = 960, height: int = 300) -> str:
    """Bitcoin Fear & Greed + Altcoin Season, both bounded 0-100, each with a tabular fallback.

    The labelling is the honest part, and it is deliberately not flattering:

      - **Fear & Greed is Bitcoin-only.** The vendor notes that several of its component inputs
        are paused, so it is a slow-moving Bitcoin sentiment gauge, not a market-wide one.
      - **The Altcoin Season Index was redefined.** It is now the share of the top 50 excluding
        BTC that outperformed BTC over 90 days, not the old altcoin/BTC market-cap ratio. The
        older "it is a circular ratio" criticism no longer applies to the current definition.

    Neither is a claim about the CMC indices on the panel above. They are context, and say so.
    """
    fng = (sent or {}).get("fng") or []
    alt = (sent or {}).get("altseason") or []
    if not fng and not alt:
        return ('<p class="warn">No sentiment data in this mode. '
                'Run <code>python3 run.py --live</code> for the keyless tape.</p>')

    def table(rows, label):
        if not rows:
            return ""
        step = max(1, len(rows) // 12)
        body = "".join(
            f'<tr><td>{esc(str(rows[i][0]))}</td>'
            f'<td style="font-variant-numeric:tabular-nums">{rows[i][1]}</td>'
            f'<td>{esc(str(rows[i][2] or "—"))}</td></tr>'
            for i in range(0, len(rows), step))
        return (f'<table class="fallback"><caption>{esc(label)} · latest {rows[-1][1]}/100 '
                f'· n={len(rows)}</caption><thead><tr><th scope="col">Date</th>'
                f'<th scope="col">Value</th><th scope="col">Classification</th></tr></thead>'
                f'<tbody>{body}</tbody></table>')

    parts = [
        _banded_chart(
            fng, "Bitcoin Fear & Greed",
            "Bitcoin-only; the vendor notes several component inputs are paused, so this is a "
            "slow Bitcoin sentiment gauge, not a market-wide one.",
            [(0, 25, PALETTE["negative"]), (25, 75, PALETTE["ink_muted"]),
             (75, 100, PALETTE["positive"])], "series_a", width, height),
        _banded_chart(
            alt, "Altcoin Season Index (90d)",
            "Share of the top 50 excluding BTC that outperformed BTC over 90 days. The metric "
            "was redefined; it is no longer the altcoin/BTC market-cap ratio.",
            [(0, 50, PALETTE["negative"]), (50, 100, PALETTE["positive"])],
            "series_b", width, height),
        table(fng, "Bitcoin Fear & Greed"),
        table(alt, "Altcoin Season Index"),
    ]
    return '<div class="card">' + "".join(p for p in parts if p) + "</div>"


def render_table(result: dict, max_rows: int = 20) -> str:
    """The non-visual equivalent. REQUIRED on every chart, not optional.

    Carries the same honesty block as the chart: n, n_eff, rho1. A screen-reader user gets the
    same caveats a sighted user does.
    """
    if not result.get("analysable"):
        return (f'<table class="fallback"><caption>No analysable window: '
                f'{esc(result.get("reason") or "unknown")}</caption></table>')
    days, spread, pct = result["days"], result["spread"], result.get("pct") or []
    step = max(1, len(days) // max_rows)
    rows = []
    for i in range(0, len(days), step):
        v = spread[i] if i < len(spread) else None
        p = pct[i] if i < len(pct) else None
        direction = "above" if (v or 0) > 0 else ("below" if (v or 0) < 0 else "level")
        rows.append(
            f'<tr><td>{esc(days[i])}</td>'
            f'<td style="font-variant-numeric:tabular-nums">{_fmt(v, 3)}</td>'
            f'<td style="font-variant-numeric:tabular-nums">'
            f'{("—" if p is None else f"{p:.0f}")}</td>'
            f'<td>{direction}</td></tr>'
        )
    st = result["stats"]
    step = max(1, len(days) // max_rows)
    return (
        '<table class="fallback">'
        f'<caption>Rebased spread in percentage points (CMC20 &minus; CMC100, both to '
        f'{st["base"]:g}) · n={result["n"]} days · n_eff={st.get("n_eff")} · '
        f'rho1={_fmt(st.get("rho1"), 3)} · mean {_fmt(st["mean_spread"], 3)}pp · '
        f'sd {_fmt(st["sd_spread"], 3)}pp. The spread has no stationary distribution, so no '
        f'significance is claimed; the percentile column is its position within this window. '
        f'Showing {min(max_rows, len(days))} of {len(days)} rows.</caption>'
        '<thead><tr><th scope="col">Date</th><th scope="col">Spread (pp)</th>'
        '<th scope="col">Percentile</th>'
        '<th scope="col">Direction</th></tr></thead><tbody>'
        + "".join(rows) + "</tbody></table>"
    )
