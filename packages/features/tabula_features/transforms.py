"""Deterministic transformations. Pure functions: no I/O, no clock, no randomness.

Every function here is reproducible from the canonical dataset alone. That is the point — a
transformation that depends on anything but its inputs cannot be verified.
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Optional, Sequence

from .align import Window, paired_values, render_axis


class TransformError(ValueError):
    """Raised when a transformation cannot be performed. Never silently approximated."""


# --- level transforms --------------------------------------------------------

def rebase(values: Sequence[float], base: float = 100.0) -> list[float]:
    """Rebase a series to `base` at its first observation.

    Why this exists: the raw CMC20-CMC100 difference is visually flat. Measured over 9 daily
    points, mean 7.981, sd 0.177, span 0.520 — 6.5% of the mean, because the two indices sit ~170
    apart and move nearly in parallel. The "25-point regime geometry" the concept rests on does
    NOT exist in raw index values. Rebasing then differencing exposes it.
    """
    if not values:
        return []
    if base == 0:
        raise TransformError("cannot rebase to 0")
    return [v * (base / values[0]) for v in values]


def difference(a: Sequence[float], b: Sequence[float]) -> list[float]:
    if len(a) != len(b):
        raise TransformError(f"length mismatch: {len(a)} vs {len(b)}")
    return [x - y for x, y in zip(a, b)]


def ratio(a: Sequence[float], b: Sequence[float]) -> list[float]:
    if len(a) != len(b):
        raise TransformError(f"length mismatch: {len(a)} vs {len(b)}")
    out = []
    for x, y in zip(a, b):
        if y == 0:
            raise TransformError("ratio undefined: denominator is 0")
        out.append(x / y)
    return out


# --- dispersion --------------------------------------------------------------

def stdev(values: Sequence[float]) -> Optional[float]:
    """Population standard deviation. The series IS the population."""
    n = len(values)
    if n < 2:
        return None
    m = sum(values) / n
    return math.sqrt(sum((v - m) ** 2 for v in values) / n)


def mean(values: Sequence[float]) -> Optional[float]:
    return (sum(values) / len(values)) if values else None


def zscore(values: Sequence[float]) -> list[Optional[float]]:
    """Standardise. Returns None where the window is too short to have a dispersion.

    A z-score against an undefined sigma is not a small number, it is no number.
    """
    sd = stdev(values)
    if not sd:
        return [None] * len(values)
    m = sum(values) / len(values)
    return [(v - m) / sd for v in values]


def rolling_volatility(values: Sequence[float], window: int) -> list[Optional[float]]:
    """Population stdev of returns over a rolling window of observations.

    Measured in OBSERVATIONS, not calendar days. That is deliberate and it is why the alignment
    policy uses an inner join: with a gappy series a 20-observation window spans more calendar
    time than it does on a dense one, and two panels would not be comparable.
    """
    if window < 2:
        raise TransformError("rolling window must be >= 2")
    returns = [values[i] / values[i - 1] - 1 for i in range(1, len(values)) if values[i - 1]]
    out: list[Optional[float]] = [None]
    for i in range(len(returns)):
        chunk = returns[max(0, i - window + 1): i + 1]
        out.append(stdev(chunk) if len(chunk) >= 2 else None)
    return out


# --- the flagship computation ------------------------------------------------

def flagship(win: Window, a: str, b: str, base: float = 100.0) -> dict:
    """CMC20 vs CMC100, corrected for flatness. Returns chart-ready data plus the numbers to print.

    The reported sigma is MEASURED HERE and returned for the caption. It is never a constant
    copied from a document: an earlier master plan stated the 0.520 band becomes 3.5 sigma when
    the same measurements give 2.94 sigma, because 3.5 belongs to a different series (daily
    returns, not levels). A provenance product that prints a remembered constant is not a
    provenance product.
    """
    if not win.is_analysable:
        return {
            "analysable": False,
            "reason": win.dropped_reason,
            "coverage": win.coverage,
            "n": len(win.paired_days),
        }

    rows = paired_values(win, a, b)
    days = [d for d, _, _ in rows]
    va = [x for _, x, _ in rows]
    vb = [y for _, _, y in rows]

    ra, rb = rebase(va, base), rebase(vb, base)
    spread = difference(ra, rb)
    z = zscore(spread)
    mean_spread, sd_spread = mean(spread), stdev(spread)

    raw_spread = difference(va, vb)
    raw_sd = stdev(raw_spread)
    raw_span_sigma = (max(raw_spread) - min(raw_spread)) / raw_sd if raw_sd else None

    axis = render_axis(win.series, win.start, win.end)
    return {
        "analysable": True,
        "reason": None,
        "start": days[0], "end": days[-1], "days": days,
        "n": len(days),
        "coverage": win.coverage,
        "rebase": {a: [ra[i] if i < len(ra) else None for i in range(len(axis))],
                   b: [rb[i] if i < len(rb) else None for i in range(len(axis))]},
        "spread": spread,
        "z": z,
        "raw_spread": raw_spread,
        "stats": {
            "base": base,
            "mean_spread": mean_spread,
            "sd_spread": sd_spread,
            "z_unit": "standard deviations of the rebased spread",
            "raw_mean_spread": mean(raw_spread),
            "raw_sd_spread": raw_sd,
            "raw_span": (max(raw_spread) - min(raw_spread)) if raw_spread else None,
            "raw_span_in_sigma": raw_span_sigma,
        },
        "axis": axis,
    }


# --- composition -------------------------------------------------------------

def composition(series, day: Optional[dt.date] = None) -> list[dict]:
    """Per-day basket membership.

    CAVEAT THAT MUST TRAVEL WITH THIS FUNCTION'S OUTPUT: this is CMC-SELECTED basket
    composition, NOT market churn. Entries and exits are CMC index rebalances, not market events.
    CMC20 carries 20 names/day; CMC100 carries 100, with a different schema (no priceUsd/units).
    """
    if not series.constituents:
        return []
    if day is None:
        day = max(series.constituents)
    return sorted(series.constituents.get(day, []),
                  key=lambda c: -(c.get("weight") or 0))
