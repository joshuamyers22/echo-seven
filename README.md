# Echo Seven

Offline research on fixed-strike implied-volatility sensitivity to underlying
returns. Generated from the local **production-project-template**, using its
`python-data-quant` archetype at template commit
`d59f3e661a1fa3456505cf36f91b51f4a1c873ac`.

The first milestone accepts calibrated IV observations, validates their declared
information times, forms same-session consecutive log returns and fits OLS with
an intercept. Output includes HC3 diagnostics, data rejection accounting and
reproducible evidence. Every result is marked **research only; live_eligible=false**.
HC3 intervals are not calibrated for intraday dependence.

## Run locally or on another machine

With Python/uv available:

```sh
git clone --branch dev/bootstrap https://github.com/joshuamyers22/echo-seven.git
cd echo-seven
uv sync --frozen --dev
make check
uv run echo-seven data/spot-vol-example.csv \
  --asof 2026-01-09T00:00:00Z \
  --analysis-plan docs/STATISTICAL_ANALYSIS_PLAN.md \
  --revision local-bootstrap \
  --output build/spot-vol-example.json
```

Use an actual source revision instead of `local-bootstrap` for recorded research.
The output filename must be new; publication refuses overwrite, including a race
with another publisher. Local filesystem hard-link support is required. Operational
events contain a result hash or stable failure code, not input rows or private paths.
The artifact contains derived observations and must follow the input's privacy rules.

The included four-session dataset is entirely synthetic, generated with beta -2
and small deterministic noise. Regenerate with
`uv run python scripts/generate_synthetic_fixture.py`. It is a correctness example,
not market evidence. `make build` creates the installable wheel and source archive;
`make audit` checks runtime dependency advisories and the template license allowlist.

## Current boundaries

- Immutable strike, expiry, call/put side and underlying identity per series.
- Explicit UTC-aware session, quote, availability and calibration timestamps.
- No gaps, halts or overnight bridging; defaults are five-minute bars, 30-second
  maximum quote age and two-second maximum quote skew.
- OLS reference, no return-magnitude filtering, WLS, Huber, smoothing or SSR overlay.
- Pure incremental hedge helper with signed dollar vega per volatility point.
- No vendor adapter, IV inversion, GVV import or live execution.

Read [PROJECT_BRIEF.md](PROJECT_BRIEF.md), the
[analysis plan](docs/STATISTICAL_ANALYSIS_PLAN.md),
[input contract](docs/INPUT_SCHEMA.md), and [roadmap](docs/ROADMAP.md).
The [research archive](docs/research/README.md) preserves the prior Moontower-informed
reviews. The original spec is superseded where it conflicts with the analysis plan.

## Engineering foundation

The template supplies strict Pyright, Ruff, unittest, locked dependencies, packaging,
CI workflows, telemetry schema, evidence utilities and governance documents. Its
generic examples remain available as `echo-seven-template-ingest`,
`echo-seven-regression`, `echo-seven-validate` and `echo-seven-dataset`;
they are reference utilities, separate from the primary replay command above.
Review [the initial verification record](docs/reviews/bootstrap-verification.md)
for the evidence and unresolved limits of this milestone.
