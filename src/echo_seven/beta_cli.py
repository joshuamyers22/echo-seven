"""Offline spot-vol replay with deterministic, immutable result evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .estimation import estimate_beta
from .evidence import SoftwareVersions
from .observations import load_iv_csv, utc_timestamp
from .pairing import SamplingPolicy, pair_observations


class BetaEvidence:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values

    def to_json_bytes(self) -> bytes:
        return (
            json.dumps(self.values, sort_keys=True, indent=2, allow_nan=False) + "\n"
        ).encode()


def publish_evidence(path: Path, artifact: BetaEvidence) -> str:
    """Publish complete local evidence atomically without overwriting a winner."""
    content = artifact.to_json_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
            temporary_name = temporary.name
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.link(temporary_name, path)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)
    return hashlib.sha256(content).hexdigest()


def run_replay(
    *,
    input_path: Path,
    output_path: Path,
    asof_text: str,
    plan_path: Path,
    revision: str,
    policy: SamplingPolicy,
    minimum_pairs: int = 20,
) -> str:
    if not revision.strip() or len(revision) > 128:
        raise ValueError("code revision must contain 1 to 128 characters")
    if output_path.exists():
        raise FileExistsError("output exists; choose a new artifact name")
    asof = utc_timestamp(asof_text)
    dataset = load_iv_csv(input_path)
    series = pair_observations(dataset.rows, policy=policy, asof=asof)
    results: list[dict[str, object]] = []
    for item in series:
        fit = estimate_beta(item, minimum_pairs=minimum_pairs)
        latest = item.latest
        results.append(
            {
                "estimate": asdict(fit),
                "input_rows": item.input_rows,
                "rejected_rows_by_reason": item.rejected,
                "unpaired_rows_by_reason": item.unpaired,
                "last_valid_bar_at": latest.bar_at.isoformat() if latest else None,
                "last_valid_bar_age_seconds": (asof - latest.bar_at).total_seconds()
                if latest
                else None,
                "identity": {
                    "underlying_id": latest.underlying_id,
                    "strike": str(latest.strike),
                    "expiry_at": latest.expiry_at.isoformat(),
                    "option_type": latest.option_type,
                }
                if latest
                else None,
                "pairs": [
                    {
                        "start_at": pair.start_at.isoformat(),
                        "end_at": pair.end_at.isoformat(),
                        "session_id": pair.session_id,
                        "underlying_log_return": pair.underlying_log_return,
                        "iv_log_return": pair.iv_log_return,
                    }
                    for pair in item.pairs
                ],
            }
        )
    payload: dict[str, object] = {
        "schema_version": "echo-seven-evidence/v1",
        "asof_utc": asof.isoformat(),
        "code_revision": revision,
        "source_sha256": dataset.source_sha256,
        "analysis_plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "implementation_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(Path(__file__).parent.glob("*.py"))
        },
        "software": asdict(SoftwareVersions.current()),
        "sampling_policy": asdict(policy),
        "minimum_pairs": minimum_pairs,
        "point_estimator": "OLS_with_intercept",
        "estimand": "slope_of_fixed_strike_log_iv_change_on_underlying_log_return",
        "weight_policy": "unweighted; no return magnitude or sign filtering",
        "upstream_contract": "calibrated-iv/v1; upstream inversion not validated here",
        "inference_status": "diagnostic_HC3_only; not_calibrated_for_dependence",
        "hedge_status": "research_only; live_use_not_approved",
        "series": results,
    }
    return publish_evidence(output_path, BetaEvidence(payload))


def operational_event(revision: str, digest: str | None) -> str:
    event: dict[str, object] = {
        "schema_version": 1,
        "timestamp": datetime.now(UTC).isoformat(),
        "severity": "INFO" if digest else "ERROR",
        "event": "echo_seven_evidence_written"
        if digest
        else "echo_seven_replay_failed",
        "service": "echo-seven",
        "environment": "local",
        "release": "0.1.0",
        "revision": (revision.strip() or "unknown")[:128],
        "operation": "replay",
        "outcome": "success" if digest else "error",
    }
    if digest:
        event["attrs"] = {"artifact_sha256": digest}
    else:
        event.update(
            error_code="REPLAY_REJECTED", error_type="ReplayError", retryable=False
        )
    return json.dumps(event, sort_keys=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, prog="echo-seven")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--analysis-plan", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--bar-seconds", type=int, default=300)
    parser.add_argument("--max-quote-age-seconds", type=int, default=30)
    parser.add_argument("--max-quote-skew-seconds", type=int, default=2)
    parser.add_argument("--minimum-pairs", type=int, default=20)
    args = parser.parse_args()
    try:
        digest = run_replay(
            input_path=args.input,
            output_path=args.output,
            asof_text=args.asof,
            plan_path=args.analysis_plan,
            revision=args.revision,
            policy=SamplingPolicy(
                args.bar_seconds,
                args.max_quote_age_seconds,
                args.max_quote_skew_seconds,
            ),
            minimum_pairs=args.minimum_pairs,
        )
    except (ValueError, OSError):
        parser.exit(2, operational_event(args.revision, None) + "\n")
    print(operational_event(args.revision, digest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
