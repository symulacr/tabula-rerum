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

# Contrast checked against the background below. Ratios measured in docs/CANONICAL-DATA.md.
PALETTE = {
    "ground": "#f7f7f4",       # L* ~97
    "surface": "#ffffff",
    "ink": "#1c1b19",          # 15.9:1 on ground
    "ink_muted": "#5c5a54",    # 7.0:1  on ground
    "rule": "#d8d6d0",
    "accent": "#8a6d1f",       # 5.1:1  on ground — bronze, not the reference app's purple
    "series_a": "#2f5d8a",     # 5.4:1  on ground
    "series_b": "#8a5a2b",     # 5.0:1  on ground
    "positive": "#1f6b45",     # 5.3:1
    "negative": "#9b2c2c",     # 6.1:1
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
    """The flagship rebased-spread chart, in z-score units.

    Non-visual fallbacks that MUST be present on every chart:
      role="img" + <title>/<desc> for screen readers;
      a data table emitted by render_table();
      direction carried by a solid/dashed stroke and an explicit +/- label, never colour alone.
    """
    pad_l, pad_r, pad_t, pad_b = 64, 24, 44, 64
    iw, ih = width - pad_l - pad_r, height - pad_t - pad_b

    if not result.get("analysable"):
        return _empty_panel(result.get("reason") or "no analysable window", width, height)

    z = [x for x in result["z"] if x is not None]
    if not z:
        return _empty_panel("dispersion undefined for this window", width, height)
    lo, hi = min(z), max(z)
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
                 f'in standard deviations</title>')
    parts.append(
        f'<desc id="desc">{n} paired daily observations from {esc(result["start"])} to '
        f'{esc(result["end"])}. Mean rebased spread {_fmt(st["mean_spread"], 3)}, standard '
        f'deviation {_fmt(st["sd_spread"], 3)}. The same difference on raw index values spans only '
        f'{_fmt(st.get("raw_span"), 3)} points, or {_fmt(st.get("raw_span_in_sigma"), 2)} standard '
        f'deviations, which is why the rebased form is shown. A tabular equivalent follows.</desc>'
    )
    parts.append(f'<rect width="{width}" height="{height}" fill="{PALETTE["ground"]}"/>')

    # gridlines + y labels
    for t in _ticks(lo, hi, 5):
        y = Y(t)
        parts.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + iw}" y2="{y:.1f}" '
                     f'stroke="{PALETTE["rule"]}" stroke-width="1"/>')
        parts.append(f'<text x="{pad_l - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="12" '
                     f'fill="{PALETTE["ink_muted"]}">{t:+.2f}σ</text>')
    # zero line
    if lo < 0 < hi:
        y0 = Y(0)
        parts.append(f'<line x1="{pad_l}" y1="{y0:.1f}" x2="{pad_l + iw}" y2="{y0:.1f}" '
                     f'stroke="{PALETTE["ink"]}" stroke-width="1.5" stroke-dasharray="4 3"/>')
        parts.append(f'<text x="{pad_l + iw}" y="{y0 - 6:.1f}" text-anchor="end" font-size="11" '
                     f'fill="{PALETTE["ink_muted"]}">equal footing (0σ)</text>')

    # the series — solid stroke, so direction is not carried by colour
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(result["z"]) if v is not None)
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{PALETTE["series_a"]}" '
                 f'stroke-width="2.25" stroke-linejoin="round" stroke-linecap="round"/>')

    # x labels: first, middle, last only
    for i in (0, n // 2, n - 1):
        d = result["days"][i]
        anchor = "start" if i == 0 else ("end" if i == n - 1 else "middle")
        parts.append(f'<text x="{X(i):.1f}" y="{pad_t + ih + 22}" text-anchor="{anchor}" '
                     f'font-size="12" fill="{PALETTE["ink_muted"]}">{esc(d)}</text>')

    # caption: printed values, measured at render time
    cap = caption or (
        f"n={n} · mean {_fmt(st['mean_spread'], 3)} · sd {_fmt(st['sd_spread'], 3)} "
        f"(rebased to {st['base']:g}) · coverage {result['coverage']:.1%}"
    )
    parts.append(f'<text x="{pad_l}" y="{height - 18}" font-size="11.5" '
                 f'fill="{PALETTE["ink_muted"]}">{esc(cap)}</text>')
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
    """The non-visual equivalent. REQUIRED on every chart, not optional."""
    if not result.get("analysable"):
        return (f'<table class="fallback"><caption>No analysable window: '
                f'{esc(result.get("reason") or "unknown")}</caption></table>')
    days, z = result["days"], result["z"]
    step = max(1, len(days) // max_rows)
    rows = []
    for i in range(0, len(days), step):
        v = z[i]
        direction = "above" if (v or 0) > 0 else ("below" if (v or 0) < 0 else "level")
        colour = PALETTE["positive"] if (v or 0) > 0 else (
            PALETTE["negative"] if (v or 0) < 0 else PALETTE["ink_muted"])
        rows.append(
            f'<tr><td>{esc(days[i])}</td>'
            f'<td style="font-variant-numeric:tabular-nums">{_fmt(v, 3)}</td>'
            f'<td>{direction}</td></tr>'
        )
    st = result["stats"]
    return (
        '<table class="fallback">'
        f'<caption>C rebased spread in standard deviations · n={result["n"]} · '
        f'mean {_fmt(st["mean_spread"], 3)} · sd {_fmt(st["sd_spread"], 3)}</caption>'
        '<thead><tr><th scope="col">Date</th><th scope="col">σ</th>'
        '<th scope="col">Direction</th></tr></thead><tbody>'
        + "".join(rows) + "</tbody></table>"
    )
