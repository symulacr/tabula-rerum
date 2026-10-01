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


def lag1_autocorrelation(values: Sequence[float]) -> Optional[float]:
    """Lag-1 autocorrelation of a series, population form.

    Why this exists: it is the number that decides whether a z-score on this series means
    anything. Measured on the rebased CMC20-CMC100 spread it is 0.7625, so the series is
    strongly persistent: there is no stationary distribution behind the spread, no equilibrium
    to deviate from, and no valid null. Any "the spread is N sigma from normal" phrasing is a
    category error, and publishing one from a product whose claim is trustworthy provenance
    would be the exact failure this project exists to prevent.

    Note for anyone comparing figures: the RAW spread has rho1 = 0.9469, while the REBASED
    spread -- the one the chart actually plots -- has 0.7625. They are different series and the
    two numbers must never be mixed.

    Returns None when undefined (< 3 points, or zero variance).
    """
    n = len(values)
    if n < 3:
        return None
    m = sum(values) / n
    denom = sum((v - m) ** 2 for v in values)
    if not denom:
        return None
    num = sum((values[i] - m) * (values[i - 1] - m) for i in range(1, n))
    return num / denom


def effective_n(values: Sequence[float]) -> Optional[int]:
    """Effective sample size for a mean, given lag-1 autocorrelation.

        n_eff = n / sqrt((1 + rho) / (1 - rho))

    At rho = 0 this is n. At rho = 0.947 a 70-day window has n_eff = 6. Reporting n = 70 for
    that window overstates the evidence by more than an order of magnitude, so the caption must
    carry n_eff alongside n, or it is misleading by construction.
    """
    n = len(values)
    rho = lag1_autocorrelation(values)
    if rho is None or n == 0:
        return None
    if rho >= 1.0:
        return 1                      # perfectly persistent: one observation's worth of information
    if rho <= -1.0:
        return n
    inflation = math.sqrt((1.0 + rho) / (1.0 - rho))
    return max(1, int(round(n / inflation)))


def percentile_rank(values: Sequence[float]) -> list[Optional[float]]:
    """Empirical CDF position of each value within the window, as a percentage.

    This is the distribution-free replacement for the z-score as the headline statistic. It
    makes no normality assumption and no stationarity assumption, so it is defensible on a unit
    root. Ties share the midpoint rank. Returns None where the input is None.
    """
    n = len(values)
    out: list[Optional[float]] = [None] * n
    present = [(i, v) for i, v in enumerate(values) if v is not None]
    m = len(present)
    if m == 0:
        return out
    for i, v in present:
        below = sum(1 for _, w in present if w < v)
        equal = sum(1 for _, w in present if w == v)
        # midpoint rank, so ties do not depend on position
        out[i] = 100.0 * (below + (equal - 1) / 2.0) / (m - 1) if m > 1 else 50.0
    return out


# --- the flagship computation ------------------------------------------------

def flagship(win: Window, a: str, b: str, base: float = 100.0) -> dict:
    """CMC20 vs CMC100. Returns chart-ready data plus the numbers to print.

    The headline statistic is NOT a z-score, and the reason is measured rather than asserted.
    The rebased spread has lag-1 autocorrelation 0.7625: it is strongly persistent, so it has
    no stationary distribution, no equilibrium to deviate from and no valid null, which makes
    "the spread is N sigma from normal" a category error rather than a finding. The z-score is
    still computed and returned, because it is a legitimate description of where a value sits
    relative to the window's own mean and sd -- but it is no longer captioned as if it were
    evidence. The defensible statements are: the spread in percentage points and its percentile
    rank in the cross-window distribution.

    Every figure here is MEASURED at call time and returned for the caption. It is never a
    constant copied from a document: an earlier plan stated a 0.520 band becomes 3.5 sigma when
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
    raw_mean = mean(raw_spread)

    # --- the honesty block, all measured here ---
    rho1 = lag1_autocorrelation(spread)
    n_eff = effective_n(spread)
    pct = percentile_rank(spread)
    raw_span = (max(raw_spread) - min(raw_spread)) if raw_spread else None
    raw_span_pct_of_mean = (100.0 * raw_span / raw_mean) if (raw_span and raw_mean) else None
    raw_span_sigma = (raw_span / raw_sd) if raw_sd else None
    # how strongly the two indices move together -- the reason the spread is near-noise
    r_levels = _pearson(va, vb)

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
        "pct": pct,
        "raw_spread": raw_spread,
        "stats": {
            "base": base,
            "mean_spread": mean_spread,
            "sd_spread": sd_spread,
            # z_unit is deliberately NOT called a unit of evidence
            "z_unit": "standard deviations of the rebased spread (descriptive only)",
            "headline_unit": "percentage points of rebased spread",
            "rho1": rho1,
            "n_eff": n_eff,
            "r_levels": r_levels,
            "latest_pct": pct[-1] if pct else None,
            "latest_spread": spread[-1] if spread else None,
            "raw_mean_spread": raw_mean,
            "raw_sd_spread": raw_sd,
            "raw_span": raw_span,
            "raw_span_pct_of_mean": raw_span_pct_of_mean,
            "raw_span_in_sigma": raw_span_sigma,
        },
        "axis": axis,
    }


def _pearson(x: Sequence[float], y: Sequence[float]) -> Optional[float]:
    """Pearson correlation. Used to state how strongly the two indices move together."""
    n = len(x)
    if n < 2 or n != len(y):
        return None
    mx, my = sum(x) / n, sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    if not dx or not dy:
        return None
    return num / (dx * dy)


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
