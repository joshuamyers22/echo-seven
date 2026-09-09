# Research provenance

The initial kernel follows the adversarial and statistical reviews; the archived
original design is historical context and is not the implementation contract.
The active contract is ../STATISTICAL_ANALYSIS_PLAN.md plus ADR 0001.

High-quality practitioner sources reviewed through the user's paid subscription:

- Moontower, [Using Tick Data for Spot-Vol Correlations](https://moontower.substack.com/p/using-tick-data-for-spot-vol-correlations):
  motivates synchronized intraday fixed-strike observations and practical filtering.
  Its daily near-ATM selection is not implemented here; return-size filtering changes
  the target and dependent samples require more than IID pairs resampling.
- Moontower, [Embedding Spot-Vol Correlation in Option Deltas](https://moontower.substack.com/p/embedding-spot-vol-correlation-in),
  also available through the [author's public site](https://blog.moontower.ai/embedding-spot-vol-correlation-in-option-deltas/):
  motivates the log-vol/log-underlying relative beta and vega-based delta adjustment.
  The implementation makes decimal IV, volatility points and hedge signs explicit.

These are practitioner source material, not proof that a proposed estimator or
confidence interval has production coverage. No paywalled article text is bundled.

Archived project documents copied from Downloads on 2026-09-09:

- strike-vol-beta-spec.md — original proposal, including its review status notice.
- strike-vol-beta-spec-adversarial-review.md — design/counterexample review.
- strike-vol-beta-statistical-review.md — OLS, uncertainty and challenger review.
- strike-vol-beta-review/ — original synthetic experiment scripts and outputs,
  with an independently pinned requirements file. Historical experiments are
  evidence from the earlier review, not tests of the new package. They are kept
  outside the current package's lint/type gates and were not rerun this milestone.

See source-manifest.json for hashes of the copied files. Files inside this directory
can discuss unimplemented features; README and ROADMAP describe current behavior.

Related GVV change: showstopper branch dev/gvv-covariance-audit, commit
bb2a5a37761ae69b0d3c37b8d6cf5ad54e8ac181. Raw WLS covariance uses squared weights
in the sandwich meat. This project currently uses unweighted OLS and imports no
GVV implementation.
