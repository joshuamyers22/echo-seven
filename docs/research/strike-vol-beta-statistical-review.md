# Statistical review: estimation, inference, and hedge validation

**Date:** 2026-09-09  
**Scope:** Production-oriented statistical assessment of [strike-vol-beta-spec.md](strike-vol-beta-spec.md), extending findings F08–F14 in the [adversarial review](strike-vol-beta-spec-adversarial-review.md). This specifies defensible replacements and tests their behavior in simulations. It is not a certification of an unbuilt market-data pipeline.

**Recommendation:** Use unweighted OLS on clean fixed-strike observations as the transparent reference estimator. Choose covariance estimation separately, from the dependence structure of the regression scores. Keep WLS and Huber as explicitly targeted challengers; neither is a universal upgrade. Retain the option to publish a point estimate without a calibrated confidence claim, or to withhold a hedge adjustment entirely.

The strongest unresolved obstacle is identification from noisy, jointly constructed prices. HC3, HAC, clustering, and bootstrap methods can change uncertainty estimates; none removes a systematic error in the underlying/IV pairing. Choosing a covariance estimator is not a substitute for those controls.

## 1. What must be estimated

For one identified contract and fixed strike, define `x_t = Δ ln S_t` and `y_t = Δ ln σ_t` over identical, non-overlapping endpoints. A trailing-window reference estimates

```text
(α*, β*) = argmin_(α,β) E_window[(y − α − β x)^2]
β* = Cov_window(x,y) / Var_window(x).
```

The population includes the explicitly chosen session, tenor support, eligibility filters, event rules, and sampling horizon. A regression with an intercept estimates this linear projection under finite moments, a nondegenerate design, and suitable laws of large numbers. It does not require normal residuals. Interpreting the same coefficient as a structural constant in `y = α + βx + ε` additionally requires the relevant orthogonality/exogeneity assumptions. Calling it a causal derivative requires more identification than this design supplies.

Three targets must not share an unlabeled field:

| Target | Meaning | Appropriate evaluation |
|---|---|---|
| Historical projection | Best linear approximation in the stated estimation population | Estimation error and coefficient-interval coverage for that population |
| Current or next-period sensitivity | A state/forecast assumed to persist into the hedge interval | Chronological forecasting error and predictive coverage |
| Portfolio hedge coefficient | Coefficient minimizing the selected book's economic loss | Subsequent dollar hedge error, costs, tails, and deployment coverage |

If beta changes across a window, OLS is generally a return-variance-weighted mixture, not the final day's beta. A confidence interval for a stationary population mean is not a prediction interval for tomorrow's state. A daily sequence's dispersion is yet another object.

The full [Moontower delta article](https://moontower.substack.com/p/embedding-spot-vol-correlation-in) supplies the economic motivation; the [fixed-strike article](https://moontower.substack.com/p/using-tick-data-for-spot-vol-correlations) supplies the reference measurement approach. Their methodological reconciliation remains in the original review. Neither establishes a universal choice of estimator or covariance procedure.

### 1.1 The hedge objective can differ from the log-regression objective

Let `A_t = signed portfolio Vega_pt,t × σ_pt,t`, measured before the interval. For a locally constant beta, the vega component is approximately `A_t y_t`, and the additional hedge notional is `−A_t β`. The exposure variation matters:

```text
Unweighted log fit:      minimize Σ (y_t − α − β x_t)^2
Exposure-weighted fit:   minimize Σ A_t² (y_t − α − β x_t)^2
Dollar residual fit:    minimize Σ (R_t − a − β A_t x_t)^2
```

`R_t` in the third objective is a clearly defined conventional-delta-hedged option P&L residual. These objectives are not interchangeable. They treat intercepts, exposure variation, and omitted Greeks differently. Precision weights based on quote uncertainty are different again. A constant-exposure local model can make the first objective a useful hedge proxy; changing positions, volatility, gamma, or hedge instruments breaks that exact equivalence. Do not claim minimum-variance portfolio optimality merely because an IV regression has a high R². [Hull–White](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2658343) provides the minimum-variance motivation, not approval of these proposed implementation choices.

## 2. Separate the three decisions

| Decision | Choices | What changes |
|---|---|---|
| Point estimator | OLS, precision WLS/FGLS, Huber, an explicit nonlinear/state model | Coefficients, target under misspecification, and potentially the hedge |
| Covariance/inference | Classical, HC3, HAC, clustered, dependence-aware bootstrap | Standard errors, intervals, and tests; OLS coefficients remain unchanged |
| Action policy | Shrinkage, no adjustment, position caps, state conditioning | Trading decisions and economic risk |

Huber–White standard errors and Huber regression are different procedures. A WLS estimate may need robust covariance. An OLS estimate can remain useful under heteroskedasticity even when its classical standard errors fail. Conversely, robust standard errors can be numerically correct for the wrong projection target.

### 2.1 OLS: recommended reference, not assumed truth

Keep the intercept and record any time-of-day or state controls. Controls and interactions change the projection and must be fitted using information available before deployment. A fitted intercept does not remove arbitrary deterministic seasonality or serial dependence. Day fixed effects estimate a within-day relationship; they cannot be treated as known next-day drift or subtracted from future test P&L after observing it.

Use QR/SVD or an equivalent numerically checked solver, explicitly scale regressors, monitor rank and condition, and report return variation. Counting 40 near-zero returns is not sufficient information. Report leverage and leave-one-day-out changes in beta; a large return is influential even if its residual is small.

### 2.2 WLS: specify why the weights exist

For a correctly specified common conditional slope, inverse conditional residual variance can improve precision. The WLS API expects inverse variance, not inverse standard deviation. [statsmodels WLS documentation](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.WLS.html)

If the conditional mean is nonlinear or state dependent, WLS instead estimates

```text
θ*_w = argmin_θ E[w_t (y_t − X_t θ)^2].
```

That can be a deliberate choice. It is not automatically the same beta with less noise. For common-slope identification, require `E[w X ε] = 0`; weights depending on observed regressors can satisfy this under conditional exogeneity. A blanket requirement that every estimation weight be known before its own return is unnecessarily strong. The actual restrictions are that weights must not induce endogeneity or future-information leakage into a published decision. Response/residual-based weights need their own estimating-equation and uncertainty treatment.

The spec's `vega²/spread²` describes a proxy for IV-level precision. For log differences, a defensible noise approximation includes both endpoints:

```text
q_t = Var(e_t)/σ_t² + Var(e_(t−1))/σ_(t−1)²
      − 2 Cov(e_t,e_(t−1))/(σ_t σ_(t−1)).
v_t = q_t + Var(genuine regression innovation | state).
w_t ∝ 1/v_t, with explicit regularization and weight caps.
```

Even perfectly estimated quote noise is only one part of total residual variance. Taking its inverse alone can assign excessive weight to tight quotes with substantial genuine volatility shocks. Shared endpoint errors produce dependence between adjacent differences; a diagonal weight cannot eliminate it.

For feasible WLS, fit the variance model on training data, use out-of-fold residuals when judging its calibration, regularize positive variance away from zero, and document clipping. Fit the hedge coefficient only with the permitted historical inputs. Refit the weight model within uncertainty resampling unless conditioning on a genuinely external fixed estimate. Chronological validation must include the cost of estimating those nuisance parameters. Report OLS alongside WLS, weight concentration, effective weighted observation/day counts, and the weighted population represented.

### 2.3 Huber and other robust point estimators

Huber solves an M-estimation problem with bounded residual score. It is useful against some vertical price/IV outliers and heavy residual tails. It is not generally protected against bad high-leverage underlying returns, and its target need not equal the least-squares projection under asymmetry or nonlinear market responses. Robust regression implementations expose the norm and scale choices; those are model parameters, not interchangeable names for standard errors. [statsmodels robust-model documentation](https://www.statsmodels.org/stable/rlm.html)

The original spec is too categorical in limiting robust regression to screening. A robust point estimator is a legitimate challenger if the target and contamination model justify it. Conversely, automatic promotion of Huber is equally unjustified. Keep large legitimate returns; distinguish quote faults from economic shocks using independent metadata. Do not delete observations just because doing so makes a preferred beta look stable.

A Huber interval requires an M-estimation covariance built from its score and derivative, with dependence corrections as appropriate, or a bootstrap that refits the complete robust procedure including scale. Do not use OLS bread and residual formulas on the resulting coefficient. The experiments here assess Huber's point estimates and hedge behavior; they deliberately do not claim validated Huber confidence intervals.

## 3. Inference for dependent intraday data

Let `X_t = (1,x_t)`, `u_t = y_t − X_t θ_hat`, `A = Σ w_t X_t'X_t`, and `g_t = w_t X_t' u_t`. Sandwich covariance is

```text
V_hat(θ_hat) = A^(-1) M_hat A^(-1),
```

where `M_hat` estimates the covariance of the summed scores. Inspect dependence in **scores**, particularly the slope score, not only residual autocorrelation. Independent residual and return processes can each be serially correlated and create persistent products; conversely, residual correlation alone need not imply the same slope-score correlation.

### 3.1 Method decision table

| Method | Defensible setting | What it does not fix |
|---|---|---|
| Classical OLS covariance | Common residual variance and correctly specified serial structure, with suitable regressor assumptions | Heteroskedasticity, dependent scores, endogenous inputs |
| HC3 | Heteroskedastic observations with sufficiently weak cross-observation score dependence; leverage correction helps finite-sample behavior | Serial or common-surface dependence, coefficient bias |
| Bar-time HAC | Weakly dependent scores, meaningful time ordering, adequate span relative to dependence, justified kernel/bandwidth | Arbitrary long persistence, structural breaks, stale-price bias |
| Day-cluster covariance | Arbitrary within-day dependence; sufficiently many informative, approximately independent day clusters | Dependence between days; sparse or dominant clusters |
| HAC on summed day scores | Within-day dependence plus weak cross-day score dependence and adequate number of days | Near-nonstationarity, unknown structural breaks, insufficient span |
| Block resampling of days | Approximately stationary weakly dependent sequence of paired daily panels, adequate independent blocks | Inconsistent point estimator; regime information absent from the sample |
| Explicit state-space model | A stated latent evolution/observation model with calibrated prediction uncertainty | Misspecified transitions, unidentified observation error, unanticipated shocks |

For HC3, the meat uses leverage-adjusted scores, `g_t/(1-h_t)`, with leverage from the fitted OLS or WLS design. HAC replaces independent-observation meat by weighted lagged score cross-products. [Newey–West](https://www.nber.org/papers/t0055) establishes a positive-semidefinite HAC construction under its consistency conditions; it is not an all-sample guarantee.

For day clustering, aggregate **all jointly fitted observations** within each day before forming outer products. Duplicating the same underlying return across many fitted strikes must not multiply the number of independent observations. If days are independent, CR1 with a finite-sample multiplier and a `t_(G−1)` reference is a useful comparator; it is not a universal small-sample solution. Cluster leverage and effective degrees of freedom matter beyond the literal cluster count. [Cameron–Miller](https://cameron.econ.ucdavis.edu/research/Cameron_Miller_JHR_2015_February.pdf)

When clusters are few or unbalanced, compare leverage-adjusted cluster covariance/CR2 or CR3 and restricted wild-cluster bootstrap inference, using a verified implementation. Wild-cluster methods still need an appropriate cluster independence structure; applying independent multipliers to correlated days does not solve cross-day dependence. See [MacKinnon–Nielsen–Webb](https://arxiv.org/pdf/2205.03285). These variants are specified as additional validation candidates; they were not implemented in this experiment suite.

### 3.2 Bandwidth, block length, and clocks

The statistical policy must record units for every lag. A lag of three trading days is not three five-minute bars. Never compress missing timestamps and pretend adjacent surviving rows have the original spacing. With overlapping return intervals, account for the induced score dependence; an overlap-implied lag is a lower bound on relevant dependence, not necessarily a sufficient bandwidth.

For initial research, compare prespecified bar-lag lengths such as 3/6/12/24 and day-lag or day-block lengths such as 1/3/5/10 where sample size supports them. These are diagnostic grids, not universal defaults. Tie the range to observed score persistence, overlap, and economic timing. A plug-in bandwidth is another candidate; selecting it from data does not remove finite-sample size distortion. [Newey–West automatic lag selection](https://www.nber.org/papers/t0144)

A circular paired-day block bootstrap keeps each day's joint returns, quote state, and cross-section together, and retains dependence inside consecutive day blocks. Circular wrapping introduces an artificial end-to-start join and assumes a stationary window; do not apply it across a deliberate structural break without a justified target. The bootstrap should refit the complete estimator, not shuffle individual residuals across unrelated market states. Studentization, percentile versus basic intervals, block choice, and small-sample coverage must be explicitly tested. [Palm–Nagler](https://arxiv.org/abs/2310.19683) motivates accounting for dependence; the particular block procedure here is a reviewer-selected experiment.

A five-day window resampled in circular five-day blocks contains no new day combinations: OLS is invariant to their order, so this procedure gives a degenerate interval. That is an information failure, not high confidence. Record effective independent blocks and reject unsupported configurations before inference.

### 3.3 Operational uncertainty policy

1. Publish the coefficient's target, estimation population, horizon, window, weights, and earliest availability.
2. Keep HC3 as a heteroskedasticity diagnostic, not the sole intraday confidence interval by default.
3. Permit a day-cluster interval only under a documented cross-day score assumption, supported by diagnostics and matched simulation coverage. A non-significant autocorrelation test alone is insufficient evidence of independence.
4. If scores remain dependent across days, evaluate day-score HAC and block resampling over sufficient span. If procedures remain materially unstable or undercover, do not label the output a calibrated 95% interval. Extend the data span, narrow the target, or fit and validate a state model; otherwise mark uncertainty unvalidated.
5. Report historical beta dispersion separately from coefficient and predictive uncertainty. Retain raw beta when an unstable skew denominator makes SSR inference unavailable.

No fixed count of 20, 30, or 60 days is universally adequate. As conservative **proposed operational guardrails**, flag fewer than 30 days for extra small-cluster validation and fewer than 10 effective blocks as unsupported for a nominal block-bootstrap confidence claim. These thresholds are review recommendations, not theorems or guarantees. The experiments below deliberately include violations to show their consequences.

## 4. Identification and specification checks that covariance cannot replace

**Errors in variables.** If `x_obs = x + η` and `y_obs = βx + ε + cη`, with independent latent terms for illustration, the observed projection is

```text
β_obs = [β Var(x) + c Var(η)] / [Var(x) + Var(η)].
```

Classical attenuation is only the `c=0` special case. With the underlying reused in IV inversion, `c` can be nonzero. Standard errors may become very small around the wrong clean-market coefficient. A valid observed-data projection is not necessarily an executable hedge on clean underlying prices. More bars can make that distinction more painful.

**Filtering.** Conditioning on large `|x|` preserves a correctly specified common conditional slope under appropriate exogeneity, but changes a nonlinear/state-dependent projection. Measure filtered and unfiltered coverage and economic loss. Filtering on noisy observed returns can further change error dependence. Record the gate's information time and hold its calibration fixed before judging future data.

**Generated responses and shrinkage.** The smile, carry, and IV inversion are estimated upstream. A conditional covariance calculation that treats them as exact understates total pipeline uncertainty when those errors matter. Cross-strike ratios have correlated numerator and denominator errors. Bootstrap the original joint panel and rerun supported upstream stages, or derive the joint influence function. Do not apply simple independent James–Stein formulas to correlated heterogeneous ratios and claim their textbook guarantees.

**Functional form and economic tails.** Fit prespecified return-sign and state interactions as challengers. Test `β_up = β_down` with the appropriate covariance or bootstrap; report joint intervals and economic consequences. Many strike-by-expiry tests require a multiple-testing or hierarchical policy. Do not select significant cells and then report their unadjusted intervals as though selection never happened.

**Influence and breaks.** Report leave-one-day-out coefficient changes, concentration of `Σ w x²`, state coverage, and sensitivity to block/window lengths. Monitor out-of-time forecast errors and regime changes. A long homogeneous window can improve precision while worsening adaptation; a short window can adapt quickly while making confidence claims indefensible.

## 5. Executed experiments

The [results summary](strike-vol-beta-review/statistical-summary.md), [CSV](strike-vol-beta-review/statistical-coverage.csv), and [JSON](strike-vol-beta-review/statistical-results.json) contain the full output. There are **6,000 coefficient/inference Monte Carlo replications** across twelve scenario/window combinations, plus **200 independent chronological hedge experiments**. Most estimation windows contain 20 × 78 observations; there are also five- and sixty-day checks. Each OLS bootstrap uses 399 draws. Parameters and seed were fixed before inspecting results.

Every coefficient run compares OLS, oracle innovation-variance WLS, and Huber with tuning constant 1.345 and an iteratively updated MAD scale. OLS and WLS have classical, HC3, bar HAC(12), day CR1, and day-score HAC(3/5) intervals. OLS additionally has circular paired-day percentile intervals at block lengths 1/3/5. Huber is point-estimate only. Wald intervals use `t_(n−2)` for bar methods and `t_(G−1)` for day methods; those reference choices are explicit approximations, not claims of exact finite-sample distributions.

### 5.1 Data-generating processes

`x` and `y` are log return and log IV change divided by the same 0.001 scale, so the regression beta is unchanged. Baseline `x` and innovations are standard normal and beta is −2. All variables are synthetic.

| Scenario | Change from baseline | Declared coverage target |
|---|---|---|
| IID | None | −2 |
| Heteroskedastic | Innovation SD `0.4 + 1.6|x|` | −2 |
| Within-day dependence | Independent AR(1) return/innovation processes, persistence 0.7/0.8; reset by day | −2 |
| Persistent daily beta | Daily beta `−2 + 0.7 z_d`, stationary AR(1) `z_d` with persistence 0.85 | Stationary mean −2, not current state |
| Classical regressor error | Add independent underlying error of SD 0.5 | Clean latent −2; observed projection −1.6 also reported |
| Shared underlying/IV error | Same underlying error; add `−3η` to IV response | Clean latent −2; observed projection −2.2 also reported |
| Bad option prints | Add SD-20 noise to 1% of response observations | Clean latent −2 |
| Genuine tail response | Beta becomes −3.5 when `|x|>2` | Unweighted projection ≈ −2.392 |
| Liquidity changes beta | 80% beta −1/SD 1; 20% beta −5/SD 3 | Unweighted projection −1.8 |
| Heavy tails | Student-t(3) innovations divided by √3 | −2 |

Oracle WLS knows the genuine innovation variance in these designs; it does not estimate a feasible production variance model. Its advantage is an upper-bound illustration of a correctly informed weighting choice, not a measured result for spread-based WLS. In the liquidity scenario, its population weighted projection is approximately −1.108; error against −1.8 demonstrates a different target, not inconsistent estimation of its own target.

### 5.2 Results that determine the recommendation

| Result | Measured outcome | Implication |
|---|---|---|
| Heteroskedasticity, 20 days | Classical OLS coverage 75.4%; HC3 93.6% | An inference correction can help without changing coefficients |
| Within-day dependence, 20 days | HC3 68.2%; bar HAC(12) 91.8%; day CR1 94.6% | Heteroskedasticity-only covariance misses score dependence |
| Persistent daily beta, 20 days | Day CR1 39.2%; day HAC(3) 53.8%; block(3) 46.6% | Clustering or short blocks do not solve persistent cross-day state variation |
| Persistent daily beta, 60 days | Day HAC(5) only 66.4% | More days without sufficient dependence treatment is not automatic calibration |
| Classical/shared measurement error | HC3 coverage of clean beta 0% in both cases | Robust uncertainty does not repair input-induced bias |
| Correct oracle WLS under heteroskedasticity | Coefficient RMSE 0.060 vs OLS 0.084 | WLS can materially improve precision when its assumptions hold |
| Bad option prints | Huber RMSE 0.026 vs OLS 0.057 | A robust point estimator can help with genuine contamination |
| Genuine nonlinear tail response | Huber mean −2.245 vs target −2.392; OLS −2.390 | Huber can underweight economically important tails |
| Liquidity-dependent relationship | WLS mean −1.108 vs unweighted target −1.8; held-out regression MSE 5.662 vs OLS 5.189 | Precision weighting can be inferior for the desired economic population |

Coverage is measured against the declared target. These are nominal 95% procedures. Monte Carlo SE near 95% with 500 replications is approximately **0.97 percentage points**; near 50% it is about 2.24 points. Small differences should not be overinterpreted. Large undercoverage here is materially beyond simulation noise.

Even day HAC and block bootstrap undercover in benign 20-day examples. In the five-day dependence example, day CR1 happens to cover 94.8%, while the three-day block method covers only 70.4%. That favorable CR1 result in one balanced Gaussian design is not a license to generalize five-cluster reliability. At block length equal to the five-day window, the circular pairs bootstrap is degenerate by construction.

The persistent-beta coverage target is deliberately the stationary population mean. Much of the error is slow variation in the sampled state. If the desired target instead becomes the realized window-average response or tomorrow's sensitivity, both the estimand and the coverage experiment must change. This distinction is a major reason not to label all reported bands 'beta uncertainty'.

### 5.3 Chronological hedging and costs

Each 100-day path has constant local exposure `Vega_pt × σ_pt = $100,000`. Actual spot returns equal `0.001x`, and first-order vega P&L equals `$100y`. Each day's coefficient is fitted only on preceding observations, then held for that day's 78 bars. This is a normalized linear exposure experiment, not option-price path simulation.

The candidate grid is OLS/Huber × 10/20-day windows × 0.5/1.0 coefficient shrinkage, plus zero additional hedge. Hyperparameters are chosen on days 40–59 and frozen for evaluation on days 60–99. Each estimator can continue to refit its coefficient from past data during testing; no held-out outcomes select its hyperparameters. The surprise sign flip, from −2 to +1.5, occurs on day 70, after selection.

Synthetic transaction cost is one basis point of changed hedge notional: `$10 × |Δ beta_position|` per daily rebalance. Constant exposure omits turnover from moving vega, spot, gamma, and inventory. Selection minimizes held-out squared dollar hedge error plus `1000 × daily dollar cost`; the coefficient 1000 has units converting the cost term into the chosen loss and is an explicitly assumed risk preference. It is not a market-calibrated optimum. Evaluation separately records MSE, turnover, costs, and net mean P&L.

With stable beta and bad quotes, selection chooses full-size 20-day Huber in 99/100 runs. Its mean held-out hedge MSE is about **10,025 dollars-squared per bar**, versus 10,050 for the fixed OLS comparator, with synthetic daily cost about $0.066 versus $0.122. Under the unseen sign flip, the selected strategy's MSE rises to **34,424 dollars-squared**, versus 32,039 for fixed 20-day OLS. The selection policy learned before the break cannot know it is coming; robustness to old bad quotes can slow adaptation to a new real relationship.

These experiments demonstrate useful and adverse cases. They do not establish market profitability, a production transaction-cost model, a preferred universal window, or valid option-book tail hedging. The held-out regression MSE fields in the coefficient experiment describe its observed regression population; especially under errors in variables, they are not clean-market trading P&L.

## 6. Concrete production selection and release protocol

### 6.1 Reference implementation contract

The initial candidate should be OLS with an intercept, fixed-strike paired observations, explicit contract/session support, and a rolling historical window. Twenty completed sessions is a reproducible research starting point, **not** an approved universal live window or enough information for every interval claim. Current-IV risk conversion and stale/invalid statuses remain separate from historical fitting. Preserve unweighted/unfiltered comparators for any gated variant.

In parallel, emit diagnostics: HC3, bar-score autocorrelation, day-score autocorrelation, effective observation/day information, return variation, leverage, leave-one-day-out beta changes, and interval sensitivity. Do not select the covariance method with the smallest standard error or the first significant p-value.

Promote WLS only after defining its target, calibrating a feasible variance model, including nuisance-estimation uncertainty, and beating the reference on the matched economic objective. Promote Huber only after valid-shock and contamination experiments, high-leverage checks, scale/convergence checks, and chronological economics. If either becomes the published statistical estimator, validate its own interval procedure; do not inherit OLS intervals by convenience.

### 6.2 Simulation acceptance

Prespecify a validation envelope matching supported instruments: liquidity, timestamp errors, quote reuse, endpoint correlation, return/vol tails, genuine nonlinearities, common cross-strike errors, cross-day persistence, and missingness. Keep estimation target, DGP truth, and evaluation target separate.

As a proposed release gate for a nominal 95% coefficient interval, require at least 2,000 final independent replications per supported scenario and a lower 95% Wilson bound on coverage above 92.5%, with acceptable interval width and coefficient bias measured against economic tolerance. A mean bias below 0.05 beta units can be a provisional numerical screen, but position-level dollar impact must control the actual tolerance. These are explicit governance choices, not mathematically universal standards.

Use a distinct final validation seed set after tuning. Record all scenarios, failures, nonconvergence, and withheld outputs. Do not average excellent IID coverage with failed dependence coverage and call the procedure approved. The 500-replication experiments in this review are diagnostic evidence; they are below this proposed final release replication count and do not constitute that gate.

The already tested short-window HAC/block procedures fail badly under persistent beta. Their production release should remain blocked for that stated target until the model or procedure changes and passes a matching experiment. CR2, restricted wild-cluster bootstrap, feasible GLS, state-model prediction intervals, and full upstream-resampling coverage remain to be tested if selected for production.

### 6.3 Chronological economic acceptance

Use separate chronological development, validation, and final test periods. Keep the final test untouched during estimator, filter, window, weight, and covariance selection. Split dependent panels by time across the whole book, not random strike rows. Purge any training outcomes or label intervals that overlap the validation/test decision horizon; past-only rolling features do not justify arbitrary future leakage.

Evaluate candidate and incumbent on identical positions, eligible decision times, execution schedules, and marks. Include failed/stale periods using the actual fallback. Record net costs, hedge-error variance and mean, expected shortfall/tail loss, turnover, drawdown, and performance by direction, tenor, liquidity, event state, and asset. Confidence in incremental economic loss should use paired day/block differences, with block choices justified for that loss series. Multiple candidates require selection-aware final evaluation; significance in one selected bucket is not evidence of uniform improvement.

Require a preregistered economic improvement margin and no unacceptable tail or coverage deterioration. Define those dollar and risk-budget thresholds with the book owner before looking at final results. A lower regression R² can coexist with useful hedging; a high R² can coexist with biased or expensive hedging. Use shadow deployment to verify latency, availability, rounding, and rejection behavior before any production action.

### 6.4 Required output fields

Add `estimand_id`, `population_filter_id`, `response_units`, `estimator`, `weight_model_version`, `weight_concentration`, `n_days`, `effective_day_information`, `score_dependence_diagnostics`, `covariance_method`, `kernel`, `lag_units`, `bandwidth`, `cluster_definition`, `degrees_of_freedom_method`, `bootstrap_kind`, `block_length`, `resample_count`, `seed`, `interval_target`, `interval_level`, `interval_calibration_status`, `current_state_or_window_target`, `training_cutoff`, `available_at`, `code/data/config_versions`, `nuisance_refit_policy`, and reason-coded failure/fallback fields.

Approximate, uncalibrated, historical-dispersion, and predictive bands must have different labels. A statistically insignificant estimate is not automatically zero. A statistically significant estimate is not automatically an economically justified trade.

## 7. Reproducibility and remaining limits

Artifacts are in [strike-vol-beta-review](strike-vol-beta-review/):

- [statistical_experiments.py](strike-vol-beta-review/statistical_experiments.py): complete DGPs, estimators, coverage calculations, and chronological hedge experiment.
- [validate_and_summarize_statistics.py](strike-vol-beta-review/validate_and_summarize_statistics.py): independent numerical comparisons and results rendering.
- [statistical-results.json](strike-vol-beta-review/statistical-results.json), [statistical-coverage.csv](strike-vol-beta-review/statistical-coverage.csv), and [statistical-summary.md](strike-vol-beta-review/statistical-summary.md): complete results and readable comparisons.
- [statistical-additional-validation.json](strike-vol-beta-review/statistical-additional-validation.json): covariance/bootstrap checks and script-hash verification.
- [statistical-requirements.txt](strike-vol-beta-review/statistical-requirements.txt): the numerical package versions used.

Executed under Python 3.9.6, NumPy 2.0.2, SciPy 1.13.1, and statsmodels 0.14.6. The covariance API's distribution, lag, and correction settings must be specified explicitly; versioned [statsmodels documentation](https://www.statsmodels.org/v0.14.6/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html) describes those interfaces. The experiment uses its own transparent formulas checked against that installed version, rather than assuming website defaults.

```sh
cd /Users/josh/Downloads/strike-vol-beta-review
.venv/bin/python statistical_experiments.py --reps 500 --bootstrap 399 --rolling-reps 100
.venv/bin/python validate_and_summarize_statistics.py
```

OLS/WLS coefficient and classical/HC3/HAC/cluster covariance checks matched the independent library to numerical precision. Huber point estimates matched RLM in the verification case. Day-score HAC was additionally checked against the library's grouped-score routine; paired-day bootstrap sufficient-statistic results were checked against literal resampled refits. The executed-script hash is stored with results. These checks establish numerical agreement for the exercised cases, not empirical model validity.

Unverified requirements remain explicit: actual feed-error distributions, a feasible quote-variance model, full surface/carry-resampling inference, robust-estimator intervals, few-cluster refinements, instrument-specific cost calibration, full option repricing, and live latency. The statistical review is complete at the design-review level; production authorization still depends on those applicable implementation and data validations.
