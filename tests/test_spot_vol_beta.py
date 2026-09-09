from __future__ import annotations

import contextlib
import io
import json
import math
import tempfile
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast
from unittest import TestCase
from unittest.mock import patch

from spot_vol_beta.beta_cli import BetaEvidence, main, publish_evidence, run_replay
from spot_vol_beta.estimation import estimate_beta
from spot_vol_beta.hedge import additional_hedge_dollars
from spot_vol_beta.observations import IvObservation, load_iv_csv, utc_timestamp
from spot_vol_beta.pairing import (
    PairedSeries,
    ReturnPair,
    SamplingPolicy,
    pair_observations,
    rejection_reason,
)

ROOT = Path(__file__).resolve().parents[1]
OPEN = datetime(2026, 1, 5, 14, 30, tzinfo=UTC)
ASOF = OPEN + timedelta(days=5)
POLICY = SamplingPolicy()


def observation(bar: int) -> IvObservation:
    at = OPEN + timedelta(minutes=5 * bar)
    return IvObservation(
        "fixed",
        "spot",
        Decimal("100.00"),
        OPEN + timedelta(days=60),
        "call",
        "day1",
        "regular",
        OPEN,
        OPEN + timedelta(hours=6),
        at,
        at - timedelta(seconds=1),
        at - timedelta(seconds=1),
        at,
        OPEN - timedelta(days=1),
        Decimal(str(100 + bar / 10)),
        0.2,
        "synthetic",
        "known",
    )


def paired(x: list[float], y: list[float]) -> PairedSeries:
    return PairedSeries(
        "analytic",
        tuple(
            ReturnPair(
                OPEN + timedelta(minutes=i * 5),
                OPEN + timedelta(minutes=(i + 1) * 5),
                "day1",
                a,
                b,
            )
            for i, (a, b) in enumerate(zip(x, y, strict=True))
        ),
        None,
        len(x) + 1,
        {},
        {},
    )


class ObservationTests(TestCase):
    def test_timezone_is_required_and_normalized(self) -> None:
        self.assertEqual(utc_timestamp("2026-01-05T09:30:00-05:00"), OPEN)
        with self.assertRaises(ValueError):
            utc_timestamp("2026-01-05T09:30:00")

    def test_schema_and_exact_decimal_tokens(self) -> None:
        dataset = load_iv_csv(ROOT / "data/spot-vol-example.csv")
        self.assertEqual(len(dataset.rows), 120)
        self.assertEqual(str(dataset.rows[0].strike), "100.00")
        self.assertEqual(len(dataset.source_sha256), 64)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            for content in ("", "x,y\n1,2\n", 'bad\n"unterminated'):
                with self.subTest(content=content):
                    path.write_text(content)
                    with self.assertRaises(ValueError):
                        load_iv_csv(path)

    def test_rejects_invalid_contract_metadata(self) -> None:
        for changes in (
            {"strike": Decimal("NaN")},
            {"option_type": "1"},
            {"source_id": " "},
            {"session_close": OPEN},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(observation(2), **changes)

    def test_rejection_boundaries(self) -> None:
        row = observation(2)
        cases = [
            (observation(1), "opening_bar"),
            (replace(row, iv_decimal=float("nan")), "invalid_price_or_iv"),
            (replace(row, underlying_price=Decimal("0")), "invalid_price_or_iv"),
            (replace(row, expiry_at=row.bar_at), "expired"),
            (
                replace(row, available_at=row.bar_at + timedelta(seconds=1)),
                "future_availability",
            ),
            (
                replace(
                    row, calibration_available_at=row.bar_at + timedelta(seconds=1)
                ),
                "future_availability",
            ),
            (
                replace(row, option_quote_at=row.bar_at + timedelta(seconds=1)),
                "inconsistent_availability",
            ),
            (
                replace(row, option_quote_at=row.bar_at - timedelta(seconds=31)),
                "stale_quote",
            ),
            (
                replace(row, option_quote_at=row.bar_at - timedelta(seconds=4)),
                "asynchronous_quotes",
            ),
            (replace(row, bar_at=row.bar_at + timedelta(seconds=1)), "off_grid"),
        ]
        for candidate, expected in cases:
            with self.subTest(reason=expected):
                self.assertEqual(rejection_reason(candidate, POLICY, ASOF), expected)
        self.assertIsNone(rejection_reason(row, POLICY, ASOF))
        self.assertEqual(rejection_reason(row, POLICY, OPEN), "after_asof")

    def test_no_missing_bar_or_invalid_row_bridging(self) -> None:
        rows = (
            observation(2),
            observation(4),
            observation(5),
            replace(observation(6), iv_decimal=0),
            observation(7),
            observation(8),
        )
        result = pair_observations(rows, policy=POLICY, asof=ASOF)[0]
        self.assertEqual(
            [(p.start_at, p.end_at) for p in result.pairs],
            [
                (observation(4).bar_at, observation(5).bar_at),
                (observation(7).bar_at, observation(8).bar_at),
            ],
        )
        self.assertEqual(result.unpaired["gap"], 1)
        self.assertEqual(result.rejected["invalid_price_or_iv"], 1)
        self.assertEqual(
            len(result.pairs)
            + sum(result.unpaired.values())
            + sum(result.rejected.values()),
            result.input_rows,
        )

    def test_no_session_or_halt_bridging(self) -> None:
        for changes in ({"session_id": "day2"}, {"segment_id": "after_halt"}):
            result = pair_observations(
                (observation(2), replace(observation(3), **changes)),
                policy=POLICY,
                asof=ASOF,
            )[0]
            self.assertFalse(result.pairs)
            self.assertEqual(result.unpaired["session_or_halt_boundary"], 1)

    def test_identity_duplicates_and_session_inconsistency_fail_closed(self) -> None:
        row = observation(3)
        for changes in (
            {"underlying_id": "next_future"},
            {"strike": Decimal(101)},
            {"expiry_at": OPEN + timedelta(days=61)},
            {"option_type": "put"},
            {"session_close": OPEN + timedelta(hours=7)},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                pair_observations(
                    (observation(2), replace(row, **changes)), policy=POLICY, asof=ASOF
                )
        with self.assertRaises(ValueError):
            pair_observations((row, row), policy=POLICY, asof=ASOF)

    def test_future_prices_do_not_change_available_pairs(self) -> None:
        rows = tuple(observation(i) for i in range(2, 8))
        asof = observation(5).bar_at
        baseline = pair_observations(rows, policy=POLICY, asof=asof)[0]
        changed = tuple(
            replace(row, underlying_price=Decimal("9999"), iv_decimal=4)
            if row.bar_at > asof
            else row
            for row in rows
        )
        future = pair_observations(changed, policy=POLICY, asof=asof)[0]
        self.assertEqual(baseline.pairs, future.pairs)
        self.assertEqual(baseline.latest, future.latest)
        self.assertEqual(baseline.rejected, {"after_asof": 2})


class EstimationTests(TestCase):
    def test_ols_and_hc3_match_independent_scalar_formula(self) -> None:
        x = [(i - 13) * 0.0001 for i in range(30)]
        y = [
            0.00003 - 2.4 * value + 0.00007 * math.sin(i * 1.7)
            for i, value in enumerate(x)
        ]
        mx, my = sum(x) / len(x), sum(y) / len(y)
        sxx = sum((value - mx) ** 2 for value in x)
        beta = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True)) / sxx
        intercept = my - beta * mx
        variance = sum(
            ((a - mx) / sxx) ** 2
            * ((b - intercept - beta * a) / (1 - 1 / len(x) - (a - mx) ** 2 / sxx)) ** 2
            for a, b in zip(x, y, strict=True)
        )
        fit = estimate_beta(paired(x, y))
        self.assertAlmostEqual(cast(float, fit.beta_relative), beta, places=11)
        self.assertAlmostEqual(cast(float, fit.intercept), intercept, places=12)
        self.assertAlmostEqual(
            cast(float, fit.hc3_standard_error), math.sqrt(variance), places=11
        )
        self.assertFalse(fit.live_eligible)
        self.assertEqual(fit.inference_status, "unvalidated_under_dependence")

    def test_exact_positive_negative_and_zero_beta_are_not_clipped(self) -> None:
        x = [i * 0.0001 for i in range(30)]
        for beta in (-2.0, 0.0, 3.0):
            fit = estimate_beta(paired(x, [0.0001 + beta * a for a in x]))
            self.assertAlmostEqual(cast(float, fit.beta_relative), beta, places=10)
            self.assertIsNone(fit.hc3_normal_interval_95)
            self.assertIn("near_exact_fit_no_noise_calibration", fit.warnings)

    def test_insufficient_information(self) -> None:
        self.assertEqual(estimate_beta(paired([], [])).status, "insufficient_pairs")
        self.assertEqual(
            estimate_beta(paired([0.001] * 30, [0.002] * 30)).status,
            "insufficient_return_variation",
        )
        with self.assertRaises(ValueError):
            estimate_beta(paired([float("nan")] * 30, [0.0] * 30))

    def test_unit_leverage_disables_hc3(self) -> None:
        fit = estimate_beta(
            paired([0.0] * 29 + [0.01], [math.sin(i) * 0.001 for i in range(30)])
        )
        self.assertIsNone(fit.hc3_standard_error)
        self.assertIn("hc3_unavailable_at_unit_leverage", fit.warnings)

    def test_signed_vega_and_volatility_point_conversion(self) -> None:
        for sign in (-1, 1):
            dollars = additional_hedge_dollars(
                signed_vega_dollars_per_point=sign * 1000,
                current_iv_decimal=0.2,
                beta_relative=-2,
            )
            self.assertEqual(dollars, sign * 40000)
        with self.assertRaises(ValueError):
            additional_hedge_dollars(
                signed_vega_dollars_per_point=1000,
                current_iv_decimal=20,
                beta_relative=float("nan"),
            )


class ReplayTests(TestCase):
    def replay(self, output: Path) -> str:
        return run_replay(
            input_path=ROOT / "data/spot-vol-example.csv",
            output_path=output,
            asof_text="2026-01-09T00:00:00Z",
            plan_path=ROOT / "docs/STATISTICAL_ANALYSIS_PLAN.md",
            revision="test-revision",
            policy=POLICY,
        )

    def test_replay_is_deterministic_and_recovers_synthetic_beta(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "a.json", Path(directory) / "b.json"
            self.assertEqual(self.replay(first), self.replay(second))
            self.assertEqual(first.read_bytes(), second.read_bytes())
            payload = json.loads(first.read_text())
            estimate = payload["series"][0]["estimate"]
            self.assertEqual(estimate["pairs"], 112)
            self.assertEqual(estimate["sessions"], 4)
            self.assertAlmostEqual(estimate["beta_relative"], -2, delta=0.02)
            self.assertFalse(estimate["live_eligible"])
            self.assertIn("pairing.py", payload["implementation_sha256"])
            with self.assertRaises(FileExistsError):
                self.replay(first)

    def test_atomic_publish_does_not_overwrite_existing_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_bytes(b"winner")
            with self.assertRaises(FileExistsError):
                publish_evidence(path, BetaEvidence({"loser": True}))
            self.assertEqual(path.read_bytes(), b"winner")
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_malformed_input_emits_safe_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private-input.csv"
            path.write_text("")
            stderr = io.StringIO()
            argv = [
                "spot-vol-beta",
                str(path),
                "--output",
                str(path.with_suffix(".json")),
                "--asof",
                "2026-01-09T00:00:00Z",
                "--analysis-plan",
                "unused",
                "--revision",
                "test",
            ]
            with (
                patch("sys.argv", argv),
                contextlib.redirect_stderr(stderr),
                self.assertRaises(SystemExit) as result,
            ):
                main()
            self.assertEqual(result.exception.code, 2)
            event = json.loads(stderr.getvalue())
            self.assertEqual(event["error_code"], "REPLAY_REJECTED")
            self.assertNotIn(str(path), stderr.getvalue())
