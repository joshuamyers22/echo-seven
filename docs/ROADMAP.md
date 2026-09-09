# Development milestones

1. **Implemented: offline fixed-strike research kernel.** Template scaffold,
   explicit IV boundary, causal bar pairing, OLS/HC3 diagnostic, unit-explicit hedge
   helper, deterministic evidence and synthetic tests. Verification is recorded in
   [the milestone review](reviews/bootstrap-verification.md).
2. **Next: first market-data adapter.** Choose futures versus equity-index source;
   map contracts, sessions, halts, quotes, pricing conventions and causal calibration.
   Validate a real reference day and archive controlled provenance. Feed selection
   is still open; no external database credentials or vendor defaults are embedded.
3. **Statistical calibration.** Implement the prespecified dependence simulations
   and chronological holdouts in STATISTICAL_ANALYSIS_PLAN.md. Compare covariance
   methods first, then WLS/Huber estimands. Define numerical/economic acceptance
   thresholds before examining challenger results.
4. **Surface and portfolio study.** Add justified daily strike selection, maturity
   treatment, local SSR diagnostics and cross-strike inference only after specifying
   their estimands. Validate hedge residuals after costs versus ordinary delta.
5. **GVV integration.** Resolve upstream identity/units/backtest audit blockers,
   establish an explicit versioned estimate interface, and shadow replay. Domain
   review is required before any live eligibility or order integration.

The template's generic regression, dataset and time-validation examples remain as
reference utilities. They do not implement or validate these pending milestones.
