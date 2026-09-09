"""OLS reference and explicitly unvalidated uncertainty diagnostics."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import polars as pl

from .pairing import PairedSeries
from .regression import fit_simple_ols


def finite_or_none(value: float) -> float | None:
    return value if math.isfinite(value) else None


@dataclass(frozen=True, slots=True)
class BetaEstimate:
    series_id: str
    status: str
    pairs: int
    sessions: int
    beta_relative: float | None
    intercept: float | None
    hc3_standard_error: float | None
    hc3_normal_interval_95: tuple[float, float] | None
    maximum_leverage: float | None
    return_sum_squares: float
    residual_rmse: float | None
    r_squared: float | None
    warnings: tuple[str, ...]
    inference_status: str = "unvalidated_under_dependence"
    live_eligible: bool = False


def estimate_beta(series: PairedSeries, *, minimum_pairs: int = 20) -> BetaEstimate:
    if type(minimum_pairs) is not int or minimum_pairs < 3:
        raise ValueError("minimum_pairs must be an integer at least three")
    n = len(series.pairs)
    days = len({pair.session_id for pair in series.pairs})
    x = np.asarray([p.underlying_log_return for p in series.pairs], dtype=np.float64)
    y = np.asarray([p.iv_log_return for p in series.pairs], dtype=np.float64)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("regression inputs must be finite")
    centered = x - x.mean() if n else x
    sxx = float(np.sum(centered * centered))
    warnings = ("fewer_than_30_sessions",) if days < 30 else ()
    unavailable = BetaEstimate(
        series.series_id,
        "insufficient_pairs",
        n,
        days,
        None,
        None,
        None,
        None,
        None,
        sxx,
        None,
        None,
        warnings,
    )
    if n < minimum_pairs:
        return unavailable
    if sxx <= 1e-12:
        return BetaEstimate(
            series.series_id,
            "insufficient_return_variation",
            n,
            days,
            None,
            None,
            None,
            None,
            None,
            sxx,
            None,
            None,
            warnings,
        )
    leverage = 1 / n + centered**2 / sxx
    max_leverage = float(leverage.max())
    # Standardize the predictor before solving so return units do not determine
    # numerical rank; explicitly undo that scale on beta and its uncertainty.
    scale = math.sqrt(sxx / n)
    frame = pl.DataFrame(
        {"underlying_log_return_scaled": x / scale, "iv_log_return": y}
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        fit = fit_simple_ols(
            frame, response="iv_log_return", predictor="underlying_log_return_scaled"
        )
    beta = fit.slope / scale
    if not math.isfinite(beta) or not math.isfinite(fit.intercept):
        raise ValueError("nonfinite OLS coefficients")
    coefficient = fit.coefficients[1]
    se = finite_or_none(coefficient.standard_error / scale)
    interval_values = tuple(v / scale for v in coefficient.confidence_interval_95)
    interval = (
        (interval_values[0], interval_values[1])
        if all(math.isfinite(v) for v in interval_values)
        else None
    )
    if max_leverage >= 1 - 1e-10:
        se, interval = None, None
        warnings += ("hc3_unavailable_at_unit_leverage",)
    if fit.diagnostics.residual_root_mean_square < 1e-12:
        se, interval = None, None
        warnings += ("near_exact_fit_no_noise_calibration",)
    return BetaEstimate(
        series.series_id,
        "estimated",
        n,
        days,
        beta,
        fit.intercept,
        se,
        interval,
        max_leverage,
        sxx,
        finite_or_none(fit.diagnostics.residual_root_mean_square),
        finite_or_none(fit.r_squared),
        warnings,
    )
