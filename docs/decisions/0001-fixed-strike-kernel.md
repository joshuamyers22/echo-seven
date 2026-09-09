# ADR 0001: Start with a vendor-neutral fixed-strike estimator

Date: 2026-09-09. Status: implementation decision for an offline first milestone.

The original Downloads spec has unresolved findings in its accompanying
adversarial and statistical reviews. Those findings supersede its automatic
WLS, hard SSR range, pooled same-day carry and interval-confidence defaults.

Generate the production template's python-data-quant archetype and retain its
quality/release mechanics. Build an offline kernel on already-calibrated IV
observations before selecting a vendor/model. This boundary requires instrument,
quote, availability, calibration, session and halt metadata. It does not certify
upstream inversion. Futures and spot names must identify actual contracts.

Use OLS with intercept on relative log moves, with HC3 as a diagnostic only.
Do not conflate a historical log-regression coefficient with future hedge
optimality. No WLS/Huber promotion, SSR construction, enforced sign, clipping to
model-implied bounds or automatically calibrated interval at this stage.

Freeze strike/expiry/quote side within each series. A later OTM put/call handoff
needs its own synchronization and continuity tests. Convert current decimal IV
and signed vega per point to additional hedge dollars as
`-vega_per_point * (100 * current_iv_decimal) * beta_relative`.

GVV is a consumer through an explicit interface; do not import its funding,
pricing or backtest modules while the audit's material defects are open. No
pandas application layer is introduced; Statsmodels receives owned NumPy arrays.
