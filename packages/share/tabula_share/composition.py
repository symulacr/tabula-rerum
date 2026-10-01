"""Composition panel — CMC-selected basket membership, per day.

The one capability no comparable keyless product appears to expose. The caveat is not optional and
is rendered on the panel itself:

    this is CMC-SELECTED basket composition, not market churn. Entries and exits are CMC index
    rebalances, not market events.

CMC20 carries 20 names/day; CMC100 carries 100, and the schemas DIFFER — CMC100 has no `priceUsd`
and no `units`. That asymmetry is handled explicitly rather than by a shared field access.
"""

from __future__ import annotations

import datetime as dt
import html
from typing import Optional

from .svg import PALETTE, esc, _fmt

BAR_MAX = 100.0


def rows_for(series, day: Optional[dt.date] = None) -> tuple[list[dict], Optional[dt.date], int]:
    if not series.constituents:
        return [], None, 0
    day = day or max(series.constituents)
    rows = sorted(series.constituents.get(day, []), key=lambda c: -(c.get("weight") or 0))
    return rows, day, len(series.constituents)


def render_panel(series, day: Optional[dt.date] = None, name: str = "CMC100",
                 limit: int = 20) -> str:
    rows, day, span = rows_for(series, day)
    if not rows:
        return (f'<div class="card"><p class="lede">No constituent data for {esc(name)}.</p></div>')

    has_price = any("priceUsd" in r for r in rows)
    shown = rows[:limit]
    extra = len(rows) - len(shown)

    body = []
    for r in shown:
        w = float(r.get("weight") or 0.0)
        pct = 100.0 * w / sum(float(x.get("weight") or 0.0) for x in rows) if rows else 0.0
        bar = (f'<span class="bar" style="width:{min(100.0, pct):.1f}%"></span>')
        price = _fmt(r.get("priceUsd"), 2) if has_price and r.get("priceUsd") is not None else "—"
        body.append(
            f'<tr><td>{esc(r.get("symbol") or "?")}</td>'
            f'<td class="num">{_fmt(w, 3)}</td>'
            f'<td class="barcell">{bar}</td>'
            f'<td class="num">{price}</td></tr>'
        )

    more = (f'<p class="lede">Showing the top {len(shown)} of {len(rows)} constituents; '
            f'{extra} more are in the dataset.</p>') if extra > 0 else \
           f'<p class="lede">All {len(rows)} constituents shown.</p>'

    schema_note = ("priceUsd present" if has_price else
                   "no priceUsd/units on this index — schema differs from CMC20")

    return f"""
<div class="card" role="group" aria-labelledby="comp-h">
  <h2 id="comp-h">Basket composition &mdash; {esc(name)}</h2>
  <p class="lede">{esc(str(day))} &middot; {len(rows)} constituents &middot; {span} days recorded
     &middot; <strong>CMC-selected basket composition, not market churn</strong>: entries and exits
     are index rebalances, not market events.</p>
  {more}
  <table class="fallback">
    <caption>{esc(name)} constituents on {esc(str(day))}, by weight</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Weight</th>
      <th scope="col">Share</th><th scope="col">Price USD</th></tr></thead>
    <tbody>{''.join(body)}</tbody>
  </table>
  <p class="lede">Schema: {esc(schema_note)}.</p>
</div>"""


CSS_EXTRA = """
.bar{display:block;height:10px;background:%(accent)s;border-radius:1px;min-width:1px}
.barcell{width:38%%}
td.num{font-variant-numeric:tabular-nums;text-align:right}
table.fallback th:nth-child(2),table.fallback th:nth-child(4){text-align:right}
""" % {"accent": PALETTE["accent"]}
