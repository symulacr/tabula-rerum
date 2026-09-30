"""Canonical dataset and the alignment policy.

THE ALIGNMENT POLICY (decided here, not deferred; see docs/CANONICAL-DATA.md §5)
=================================================================================

1. Axis        UTC, ordered ascending, deduplicated by timestamp.
2. Statistics  INNER JOIN — a statistic is computed only on timestamps present in BOTH series.
3. Rendering   OUTER JOIN — every timestamp either series has is drawn; a gap is drawn as a gap.
4. Window      DROP — if inner-join coverage falls below MIN_COVERAGE of the requested window,
               the window is not analysed and the reason is recorded. No partial claims.
5. Fill        FORWARD FILL IS PROHIBITED in the judged path.

Why forward-fill is prohibited, not merely discouraged
-------------------------------------------------------
Carrying a value forward manufactures a run of zero daily returns. Volatility computed on daily
returns is therefore systematically *understated*, which shrinks the standard deviation, which
*inflates every z-score computed from it*. A filled block makes divergence look more significant
than the data supports — in a product whose entire claim is trustworthy provenance. See
docs/CANONICAL-DATA.md §5 for the full comparison.

Measured grid facts (live, 2026-09-27)
--------------------------------------
CMC20 and CMC100 both begin at 2024-01-01 and return IDENTICAL timestamp sets, so the flagship
comparison has no structural gap. The risk is confined to cross-family comparison and to
unproven API gap days, which is why coverage is checked rather than assumed.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Sequence

TIME_FIELD_CANDIDATES = ("update_time", "timestamp", "date")

# A window is analysed only if at least this fraction of its requested days are present in BOTH
# series. Below it the window is dropped and the drop is recorded, never silently analysed.
MIN_COVERAGE = 0.95

# A window needs at least this many paired observations for its statistics to mean anything.
MIN_PAIRED_POINTS = 30


def _ts_of(row: dict) -> Optional[str]:
    """The date field is `update_time` (ISO-8601 ms), NOT `timestamp`. Live-verified."""
    for k in TIME_FIELD_CANDIDATES:
        v = row.get(k)
        if isinstance(v, str) and v:
            return v
    return None


def _day_of(row: dict) -> Optional[dt.date]:
    ts = _ts_of(row)
    if not ts:
        return None
    try:
        return dt.date.fromisoformat(ts[:10])
    except ValueError:
        return None


@dataclass
class Series:
    """One canonical time series: day -> value, plus optional basket membership."""
    name: str
    values: dict[dt.date, float] = field(default_factory=dict)
    constituents: dict[dt.date, list[dict]] = field(default_factory=dict)
    unit: str = "index"

    @classmethod
    def from_index_history(cls, name: str, rows: Iterable[dict]) -> "Series":
        """Build from an index-historical payload.

        Point keys are exactly ['constituents','update_time','value'] (live-verified). Constituent
        schemas DIFFER between indices: CMC20 carries priceUsd/units, CMC100 does not.
        """
        s = cls(name=name)
        for row in rows or []:
            day = _day_of(row)
            val = row.get("value")
            if day is None or val is None:
                continue
            try:
                s.values[day] = float(val)
            except (TypeError, ValueError):
                continue
            cons = row.get("constituents")
            if isinstance(cons, list) and cons:
                s.constituents[day] = cons
        return s

    def days(self) -> list[dt.date]:
        return sorted(self.values)

    def __len__(self) -> int:
        return len(self.values)

    def mean(self) -> Optional[float]:
        if not self.values:
            return None
        return sum(self.values.values()) / len(self.values)

    def stdev(self) -> Optional[float]:
        """Population standard deviation — the whole series is the population, not a sample."""
        n = len(self.values)
        if n < 2:
            return None
        m = self.mean()
        var = sum((v - m) ** 2 for v in self.values.values()) / n
        return var ** 0.5


@dataclass
class Window:
    """A paired analysis window."""
    start: dt.date
    end: dt.date
    series: dict[str, Series]
    coverage: float
    paired_days: list[dt.date]
    dropped_reason: Optional[str] = None

    @property
    def is_analysable(self) -> bool:
        return self.dropped_reason is None and len(self.paired_days) >= MIN_PAIRED_POINTS

    def requested_days(self) -> int:
        return (self.end - self.start).days + 1


def build_window(
    series: dict[str, Series],
    start: dt.date,
    end: dt.date,
    min_coverage: float = MIN_COVERAGE,
) -> Window:
    """Apply the alignment policy. Deterministic; no network, no randomness."""
    requested = (end - start).days + 1
    inner = set.intersection(*(set(s.values) for s in series.values())) if series else set()
    paired = sorted(d for d in inner if start <= d <= end)
    coverage = (len(paired) / requested) if requested else 0.0

    reason = None
    if len(paired) < MIN_PAIRED_POINTS:
        reason = (f"only {len(paired)} paired observations, below the minimum of "
                  f"{MIN_PAIRED_POINTS}")
    elif coverage < min_coverage:
        reason = (f"inner-join coverage {coverage:.1%} below the required {min_coverage:.1%} "
                  f"of the {requested}-day window")

    return Window(start=start, end=end, series=series, coverage=coverage,
                  paired_days=paired, dropped_reason=reason)


def render_axis(series: dict[str, Series], start: dt.date, end: dt.date) -> list[dt.date]:
    """OUTER JOIN for rendering: every day any series has, so a gap is visible as a gap."""
    days: set[dt.date] = set()
    for s in series.values():
        days |= {d for d in s.values if start <= d <= end}
    return sorted(days)


def paired_values(win: Window, a: str, b: str) -> list[tuple[dt.date, float, float]]:
    """The paired observations a statistic may use. INNER JOIN only — never filled."""
    sa, sb = win.series.get(a), win.series.get(b)
    if not sa or not sb:
        return []
    return [(d, sa.values[d], sb.values[d]) for d in win.paired_days
            if d in sa.values and d in sb.values]
