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


def render_table(result: dict, max_rows: int = 40) -> str:
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
    return (
        '<table class="fallback">'
        f'<caption>Rebased spread in percentage points (CMC20 &minus; CMC100, both to '
        f'{st["base"]:g}) · n={result["n"]} days · n_eff={st.get("n_eff")} · '
        f'rho1={_fmt(st.get("rho1"), 3)} · mean {_fmt(st["mean_spread"], 3)}pp · '
        f'sd {_fmt(st["sd_spread"], 3)}pp. The spread has no stationary distribution, so no '
        f'significance is claimed; the percentile column is its position within this window.</caption>'
        '<thead><tr><th scope="col">Date</th><th scope="col">Spread (pp)</th>'
        '<th scope="col">Percentile</th>'
        '<th scope="col">Direction</th></tr></thead><tbody>'
        + "".join(rows) + "</tbody></table>"
    )
