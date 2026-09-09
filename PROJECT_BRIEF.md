# Spot-vol beta — initial project brief

Owner: J. Myers. Milestone: offline fixed-strike estimation kernel, not live trading.

## Objective and success

Estimate the intercept and relative fixed-strike IV response to underlying log
returns, with explicit timestamps, instrument identity, horizon, units, inference
status, and reproducible evidence. Consumers are research and, after validation,
GVV's separate hedge adjustment input. Success for this milestone: a synthetic
CSV replay reaches deterministic JSON; exact slope/sign/unit invariants and
adversarial timestamp/gap tests pass; template quality gates and wheel build pass.

## Selected architecture

Python 3.12, src layout, production template's python-data-quant archetype;
Polars ingestion, NumPy design matrix, Statsmodels OLS. Local batch CLI/library,
no service, credentials, network feed, or order execution. Generic template
examples remain available as examples, not the spot-vol estimator. The domain
runner accepts a vendor-neutral, already-calibrated IV observation contract.
This avoids choosing a pricing model before exercise style and futures delivery
mapping are known. Real-feed selection and timestamps remain adapter prerequisites.

## Statistical contract

OLS with intercept on log(IV_t/IV_previous) versus log(P_t/P_previous).
Unweighted, no return-size or sign filtering; fixed quote-side series, strike,
expiry, underlying contract, session and halt segment. At least 20 pairs and
nondegenerate return variation. HC3 is a diagnostic only, with normal-reference
interval explicitly labeled unvalidated under dependence; no production CI or
live hedge is approved. WLS, Huber, day clustering, HAC, shrinkage, SSR, and
rolling parameter selection require separate specified validation milestones.

## Data and timing

Prices/strikes retain Decimal representation at ingestion; IV is decimal units;
UTC-aware timestamps required, converted to UTC. Sessions and halt segments must
be supplied by an adapter from a market calendar, not inferred from UTC dates.
Reject future or stale quotes, future availability/calibration, invalid domains,
and first-bar endpoints. Never bridge missing bars, rejected endpoints, session
boundaries, halts, expiry changes, or futures rolls. Source files are hashed;
proprietary market data goes only in ignored data/raw or data/private.

## Operations and limits

Single local batch, maximum 100,000 observation rows and 50 MiB CSV. Fail closed
on invalid schema/identity; retain quality-rejection counts and insufficient-data
statuses. Output publication refuses overwrites; rerun into a new artifact name.
Artifacts bind source/code/analysis-plan hashes and parameters. No availability
SLA or live latency commitment; one bounded synthetic replay under 30 seconds is
the initial performance check. No queues, deployment or automatic recovery.
Retention/backup/access for real datasets must be set before ingestion into a
shared system. No restricted data in telemetry. Local safe run summaries support
review of rejection rates; no telemetry shipping service is deployed.

## Decision and release boundaries

The hedge conversion is a unit-checked arithmetic helper, not an executable hedge
recommendation. Zero added hedge is the eventual economic baseline. Field names
separate beta, covariance, correlation and dollar notional. Chronological model
selection, raw-quote inversion/synchronization, exercise/carry treatment, cluster
coverage, cost-aware hedge evaluation, empirical reconciliation and operational
release remain pending. Accountable financial/release review is still required;
agent tests alone do not authorize live use. See docs/ROADMAP.md.
