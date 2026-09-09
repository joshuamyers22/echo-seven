"""Generate synthetic levels with relative log-vol beta -2; no market data."""

import csv
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

from echo_seven.observations import COLUMNS


def generate(destination: Path) -> None:
    with destination.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        for day in range(4):
            opening = datetime(2026, 1, 5 + day, 14, 30, tzinfo=UTC)
            log_price, log_iv = math.log(100), math.log(0.2)
            for bar in range(1, 31):
                index = day * 30 + bar
                change = 0.001 * math.sin(index * 0.73) + 0.0002
                log_price += change
                log_iv += -2 * change + 0.0001 * math.cos(index * 1.37)
                at = opening + timedelta(minutes=bar * 5)
                quote = at - timedelta(seconds=1)
                writer.writerow(
                    (
                        "synthetic-fixed-100-call",
                        "SYNTHETIC-SPOT",
                        "100.00",
                        "2026-03-20T20:00:00Z",
                        "call",
                        opening.date().isoformat(),
                        "regular",
                        opening.isoformat(),
                        (opening + timedelta(hours=6, minutes=30)).isoformat(),
                        at.isoformat(),
                        quote.isoformat(),
                        quote.isoformat(),
                        at.isoformat(),
                        (opening - timedelta(days=1)).isoformat(),
                        format(math.exp(log_price), ".14f"),
                        format(math.exp(log_iv), ".16f"),
                        "synthetic-v1",
                        "synthetic-analytic-log-levels",
                    )
                )


if __name__ == "__main__":
    generate(Path(__file__).resolve().parents[1] / "data/spot-vol-example.csv")
