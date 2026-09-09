"""Causal fixed-horizon pairing with explicit rejection accounting."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from .observations import IvObservation


@dataclass(frozen=True, slots=True)
class SamplingPolicy:
    bar_seconds: int = 300
    maximum_quote_age_seconds: int = 30
    maximum_quote_skew_seconds: int = 2

    def __post_init__(self) -> None:
        for value in (
            self.bar_seconds,
            self.maximum_quote_age_seconds,
            self.maximum_quote_skew_seconds,
        ):
            if type(value) is not int or value < 0:
                raise ValueError("sampling limits must be nonnegative integer seconds")
        if self.bar_seconds == 0:
            raise ValueError("bar_seconds must be positive")


@dataclass(frozen=True, slots=True)
class ReturnPair:
    start_at: datetime
    end_at: datetime
    session_id: str
    underlying_log_return: float
    iv_log_return: float


@dataclass(frozen=True, slots=True)
class PairedSeries:
    series_id: str
    pairs: tuple[ReturnPair, ...]
    latest: IvObservation | None
    input_rows: int
    rejected: dict[str, int]
    unpaired: dict[str, int]


def rejection_reason(
    row: IvObservation,
    policy: SamplingPolicy,
    asof: datetime,
) -> str | None:
    if row.bar_at > asof:
        return "after_asof"
    if not row.values_valid:
        return "invalid_price_or_iv"
    if row.bar_at >= row.expiry_at:
        return "expired"
    offset = (row.bar_at - row.session_open).total_seconds()
    if row.bar_at > row.session_close or offset <= 0:
        return "outside_session"
    if offset % policy.bar_seconds:
        return "off_grid"
    if offset <= policy.bar_seconds:
        return "opening_bar"
    if row.available_at > row.bar_at or row.calibration_available_at > row.bar_at:
        return "future_availability"
    if row.available_at < max(
        row.option_quote_at, row.underlying_quote_at, row.calibration_available_at
    ):
        return "inconsistent_availability"
    for instant in (row.option_quote_at, row.underlying_quote_at):
        age = (row.bar_at - instant).total_seconds()
        if age < 0:
            return "future_quote"
        if age > policy.maximum_quote_age_seconds:
            return "stale_quote"
    if abs((row.option_quote_at - row.underlying_quote_at).total_seconds()) > (
        policy.maximum_quote_skew_seconds
    ):
        return "asynchronous_quotes"
    return None


def pair_observations(
    rows: tuple[IvObservation, ...],
    *,
    policy: SamplingPolicy,
    asof: datetime,
) -> tuple[PairedSeries, ...]:
    if asof.tzinfo is None or asof.utcoffset() is None:
        raise ValueError("asof must be timezone aware")
    grouped: dict[str, list[IvObservation]] = {}
    for row in rows:
        grouped.setdefault(row.series_id, []).append(row)
    output: list[PairedSeries] = []
    for series_id, series in sorted(grouped.items()):
        ordered = sorted(series, key=lambda item: item.bar_at)
        if len({row.identity for row in ordered}) != 1:
            raise ValueError("series identity changed: strike/expiry/side/underlying")
        if len({row.bar_at for row in ordered}) != len(ordered):
            raise ValueError("duplicate series/bar timestamp")
        sessions: dict[str, tuple[datetime, datetime]] = {}
        for row in ordered:
            boundary = row.session_open, row.session_close
            if sessions.setdefault(row.session_id, boundary) != boundary:
                raise ValueError("session boundaries changed within session_id")
        previous: IvObservation | None = None
        latest: IvObservation | None = None
        pairs: list[ReturnPair] = []
        rejected: Counter[str] = Counter()
        unpaired: Counter[str] = Counter()
        for row in ordered:
            reason = rejection_reason(row, policy, asof)
            if reason:
                rejected[reason] += 1
                previous = None
                continue
            latest = row
            if previous is None:
                unpaired["no_previous_valid_endpoint"] += 1
            elif (row.session_id, row.segment_id) != (
                previous.session_id,
                previous.segment_id,
            ):
                unpaired["session_or_halt_boundary"] += 1
            elif row.bar_at - previous.bar_at != timedelta(seconds=policy.bar_seconds):
                unpaired["gap"] += 1
            else:
                pairs.append(
                    ReturnPair(
                        previous.bar_at,
                        row.bar_at,
                        row.session_id,
                        math.log(float(row.underlying_price))
                        - math.log(float(previous.underlying_price)),
                        math.log(row.iv_decimal) - math.log(previous.iv_decimal),
                    )
                )
            previous = row
        output.append(
            PairedSeries(
                series_id,
                tuple(pairs),
                latest,
                len(series),
                dict(rejected),
                dict(unpaired),
            )
        )
    return tuple(output)
