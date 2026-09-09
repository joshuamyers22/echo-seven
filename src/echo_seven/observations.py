"""Versioned calibrated-IV boundary; no vendor or pricing-model assumptions."""

from __future__ import annotations

import hashlib
import io
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

import polars as pl

COLUMNS = (
    "series_id",
    "underlying_id",
    "strike",
    "expiry_at",
    "option_type",
    "session_id",
    "segment_id",
    "session_open",
    "session_close",
    "bar_at",
    "option_quote_at",
    "underlying_quote_at",
    "available_at",
    "calibration_available_at",
    "underlying_price",
    "iv_decimal",
    "source_id",
    "calibration_id",
)


def utc_timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamps must have an explicit timezone")
    return result.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class IvObservation:
    series_id: str
    underlying_id: str
    strike: Decimal
    expiry_at: datetime
    option_type: str
    session_id: str
    segment_id: str
    session_open: datetime
    session_close: datetime
    bar_at: datetime
    option_quote_at: datetime
    underlying_quote_at: datetime
    available_at: datetime
    calibration_available_at: datetime
    underlying_price: Decimal
    iv_decimal: float
    source_id: str
    calibration_id: str

    def __post_init__(self) -> None:
        if not all(
            (
                self.series_id.strip(),
                self.underlying_id.strip(),
                self.session_id.strip(),
                self.segment_id.strip(),
                self.source_id.strip(),
                self.calibration_id.strip(),
            )
        ):
            raise ValueError("identifiers must not be blank")
        if self.option_type not in {"call", "put"}:
            raise ValueError("option_type must be call or put")
        if not self.strike.is_finite() or self.strike <= 0:
            raise ValueError("strike must be positive and finite")
        for instant in (
            self.expiry_at,
            self.session_open,
            self.session_close,
            self.bar_at,
            self.option_quote_at,
            self.underlying_quote_at,
            self.available_at,
            self.calibration_available_at,
        ):
            if instant.tzinfo is None or instant.utcoffset() is None:
                raise ValueError("timestamps must have an explicit timezone")
        if self.session_close <= self.session_open:
            raise ValueError("session close must follow session open")

    @property
    def identity(self) -> tuple[str, Decimal, datetime, str]:
        return self.underlying_id, self.strike, self.expiry_at, self.option_type

    @property
    def values_valid(self) -> bool:
        return (
            self.underlying_price.is_finite()
            and self.underlying_price > 0
            and math.isfinite(float(self.underlying_price))
            and float(self.underlying_price) > 0
            and math.isfinite(self.iv_decimal)
            and 0 < self.iv_decimal < 5
        )


@dataclass(frozen=True, slots=True)
class ObservationInput:
    rows: tuple[IvObservation, ...]
    source_sha256: str


def load_iv_csv(path: Path) -> ObservationInput:
    with path.open("rb") as handle:
        payload = handle.read(50 * 1024 * 1024 + 1)
    if len(payload) > 50 * 1024 * 1024:
        raise ValueError("input exceeds 50 MiB limit")
    try:
        frame = pl.read_csv(io.BytesIO(payload), infer_schema=False)
    except pl.exceptions.PolarsError as error:
        raise ValueError("invalid calibrated-IV CSV") from error
    if set(frame.columns) != set(COLUMNS) or len(frame.columns) != len(COLUMNS):
        raise ValueError("CSV must match calibrated-iv/v1 columns exactly")
    if not 1 <= frame.height <= 100_000:
        raise ValueError("input must have 1 to 100000 rows")
    if any(frame.null_count().row(0)):
        raise ValueError("CSV cannot contain nulls")
    rows: list[IvObservation] = []
    for index, item in enumerate(frame.iter_rows(named=True), 2):
        row = cast(dict[str, str], item)
        row = {key: value.strip() for key, value in row.items()}
        try:
            rows.append(
                IvObservation(
                    series_id=row["series_id"],
                    underlying_id=row["underlying_id"],
                    strike=Decimal(row["strike"]),
                    expiry_at=utc_timestamp(row["expiry_at"]),
                    option_type=row["option_type"],
                    session_id=row["session_id"],
                    segment_id=row["segment_id"],
                    session_open=utc_timestamp(row["session_open"]),
                    session_close=utc_timestamp(row["session_close"]),
                    bar_at=utc_timestamp(row["bar_at"]),
                    option_quote_at=utc_timestamp(row["option_quote_at"]),
                    underlying_quote_at=utc_timestamp(row["underlying_quote_at"]),
                    available_at=utc_timestamp(row["available_at"]),
                    calibration_available_at=utc_timestamp(
                        row["calibration_available_at"]
                    ),
                    underlying_price=Decimal(row["underlying_price"]),
                    iv_decimal=float(row["iv_decimal"]),
                    source_id=row["source_id"],
                    calibration_id=row["calibration_id"],
                )
            )
        except (ValueError, InvalidOperation) as error:
            raise ValueError(
                f"invalid observation at CSV row {index}: {error}"
            ) from error
    return ObservationInput(tuple(rows), hashlib.sha256(payload).hexdigest())
