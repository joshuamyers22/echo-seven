# Echo Seven: initial analysis plan (v1)

Status: preregistered development baseline, synthetic verification only. Owner:
J. Myers. This plan records the initial implementation contract; changing it
requires a new evidence artifact and review. It is not a live hedge approval.

## Target and observation unit

For one identified option strike, expiry, call/put side and underlying contract,
fit y = alpha + beta_relative x + residual, where x = log(P_t/P_previous)
and y = log(IV_t/IV_previous). IV is an annualized decimal; P is the positive
underlying price used consistently by the upstream IV construction. A futures
price produces a futures-relative beta, not a cash-spot beta. Vendor mapping,
pricing convention, calendars and IV inversion are upstream responsibilities
and must be validated before a real-data claim.

A series cannot change identity. There is no daily ATM reselection, call/put
stitching, continuous-future roll or cross-strike pooling in this milestone.
Give distinct contracts distinct series IDs. Daily strike selection from the
prior close is a later, separately specified pooled estimand; do not relabel the
current output as that estimator.

## Sampling and information set

Defaults: 300-second bars anchored at supplied session open, quote age at most
30 seconds, quote timestamp skew at most 2 seconds. All instants are explicitly
timezone aware and compared in UTC. Exclude the first bar endpoint, outside-session,
off-grid, expired, nonpositive/nonfinite price and IV outside (0, 5), future
availability and calibration, stale or asynchronous quotes, and rows after asof.
IV cap 5 is an initial schema sanity bound, not a market universal; review before
using on instruments whose legitimate volatility can exceed 500%.

Use consecutive accepted endpoints exactly one bar apart within the same session
and uninterrupted segment. A rejected endpoint breaks the chain. No interpolation,
nearest-future match, backward filling, gap bridging or overnight return. Duplicate
timestamps, mixed identities and conflicting session metadata reject the entire
input series. Global structural validation includes rows after asof, so malformed
future metadata can reject a run; future numeric prices cannot influence fitted
historical pairs. Rejection counts are first-failure counts, not exhaustive labels.

The input already contains calibrated IV. Timestamp checks enforce declared
availability; they cannot prove the upstream calibration actually respected it.
Adapters must establish this with provenance and point-in-time replays. Missing
quotes can create informative selection; rejection accounting does not correct it.
No half-expected-move filter or selection by return sign/magnitude is applied.

## Point estimates and uncertainty

Unweighted OLS with an intercept is the reference conditional linear projection.
OLS does not establish structural causality or correct errors in the regressor;
shared underlying errors in IV inversion can bias beta. Scale x internally for
numerical conditioning and transform coefficients and uncertainty back to log
return units. Require at least 20 pairs and centered x sum of squares > 1e-12.
These are computation guardrails, not sufficient information for production.

HC3 standard errors and normal 95% intervals are diagnostics only. HC3 adjusts
for heteroskedasticity/leverage under suitable assumptions; it does not account
for serial or cross-session dependence. Report no HC3 interval at unit leverage
or a near-exact fit. Suppress nonfinite diagnostics. Fewer than 30 distinct supplied
session IDs produces a warning; 30 is a proposed guardrail, not a theorem or release
gate. Every estimate remains live_eligible=false regardless of sample size.

Do not select WLS because returns are heteroskedastic. Predetermined feasible
weights require a defensible conditional variance model and positive, bounded
weights; the weighted projection may change under misspecification. Any WLS
sandwich must use the squared raw weights in the meat, or the equivalent fully
whitened design and residuals. Include fitted-weight uncertainty in validation.
Do not silently replace OLS with Huber: it changes the estimating equation and
can downweight economically important tail behavior. These challengers are not
yet implemented or selected.

## Required next statistical study

Freeze simulation scenarios, seeds, confidence targets, interval-width tolerances
and economic loss budgets before selecting an inference method. Include time-
varying beta, stochastic volatility, serial correlation within/across sessions,
common shocks, stale/asynchronous quotes, IV inversion noise, informative quote
missingness, heteroskedasticity, outliers and high-leverage returns. Score bias,
RMSE, interval coverage/width, sign mistakes, effective independent sessions and
failure rates; retain unfavorable scenarios. Monte Carlo uncertainty on coverage
must accompany coverage estimates. IID HC3 success alone is insufficient.

Compare the unchanged OLS point estimate under HC3, prespecified HAC and session
cluster covariance, plus contiguous-session block bootstrap (refit the complete
pipeline inside each resample). HAC lag choice, cluster count, cross-day persistence
and block length need sensitivity analyses. IID pairs bootstrap is not the
production default. WLS and robust M-estimation are separate point-estimator
challengers with their own targets and uncertainty calibration.

Use chronological fit/validation/test windows. Fit all selection, calibration,
weights, smoothing and shrinkage on available training information. Overlapping
labels require explicit purging; do not tune on held-out windows. Report the OLS
reference even if a challenger is selected. No silent last-good beta fallback.
Any caching must surface estimate time, age, identity and policy.

## Hedge interface and GVV

For signed position vega V measured in dollars per one volatility point and current
IV sigma in decimals, additional underlying hedge dollars = -V * (100 sigma) *
beta_relative. Positive dollars mean buy underlying exposure. Dividing by the
underlying price is appropriate only for share units; futures contract counts need
the correct multiplier and conversion. This is an incremental vega adjustment to
a separately computed ordinary delta hedge. Rates, basis, surface changes and
transaction costs are not modeled here.

GVV can consume independently validated beta estimates in a later integration.
The initial helper is pure arithmetic and does not import GVV, call its pricing
code, route orders or alter its covariance. Its covariance audit is relevant to
future WLS implementation. Open GVV identity, units and backtest issues remain
separate integration blockers. There is no automatic mapping from SSR to beta,
no hard SSR 1–2 restriction and no enforced decay across maturity. SSR requires
matched local ATM conventions before interpretation.

## Evidence and release limits

Replay artifacts include exact input and plan SHA-256, package source hashes,
software versions, caller-supplied revision, sampling parameters, pairs, rejection
counts, identity and inference/hedge status. Revision text is provenance supplied
by the caller, not a verified Git attestation. Hashing a plan does not execute it;
this document explicitly marks future studies as pending. Results are immutable
on publication and outputs contain derived observations: store private inputs and
outputs only in approved local/private locations, never in Git.

Local synthetic tests and template gates authorize further development only.
Real-data adapters, chronological economic validation and explicit domain review
are needed before live eligibility can change. Source rationale and the earlier
adversarial/statistical reviews are indexed in research/README.md.
