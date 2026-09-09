# Spot-vol-beta project memory

Compact retrieval index only. Verify linked evidence before relying on an entry.
No private market data, secrets or unrestricted logs belong here.

| Key | Durable fact | Evidence | Last verified |
|---|---|---|---|
| template | Generated python-data-quant archetype from template d59f3e661a1fa3456505cf36f91b51f4a1c873ac; locked uv environment and template gates retained. | README.md, uv.lock | 2026-09-09 |
| estimand | Fixed strike/expiry/side/underlying OLS log-IV on log-underlying returns, with intercept. Futures-relative beta is not cash-spot beta. | docs/STATISTICAL_ANALYSIS_PLAN.md, src/spot_vol_beta/estimation.py | 2026-09-09 |
| inference | HC3 diagnostic only; every output live_eligible=false. Dependence-calibrated intervals, WLS/Huber and SSR remain unimplemented. | docs/STATISTICAL_ANALYSIS_PLAN.md, tests/test_spot_vol_beta.py | 2026-09-09 |
| causality | Declared quote/calibration availability is checked; gaps, sessions and halt boundaries are not bridged. Upstream metadata truth and IV inversion remain unaudited. | src/spot_vol_beta/pairing.py, docs/INPUT_SCHEMA.md | 2026-09-09 |
| provenance | Source/plan/package hashes and versions travel with immutable replay evidence. Revision is caller-supplied, not Git-attested. | src/spot_vol_beta/beta_cli.py, tests/test_spot_vol_beta.py | 2026-09-09 |
| gvv | GVV is a future consumer only. No pricing/backtest imports; its covariance audit branch does not resolve all integration blockers. | docs/decisions/0001-fixed-strike-kernel.md, docs/ROADMAP.md | 2026-09-09 |
| research | Archived original spec is historical and superseded where the current analysis plan differs. Earlier synthetic experiments are not tests of this package. | docs/research/README.md, docs/research/source-manifest.json | 2026-09-09 |
| next | Choose and implement the first real-data adapter, then preregister dependence/economic validation. Owner J. Myers; review at next milestone. | docs/ROADMAP.md | 2026-09-09 |
