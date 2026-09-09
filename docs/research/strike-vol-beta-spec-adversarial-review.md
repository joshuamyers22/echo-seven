# Adversarial review: strike-vol beta specification

**Date:** 2026-09-09  
**Verdict:** Revise before implementation. The economic objective is useful, but several proposed controls can manufacture, suppress, or misinterpret the very signal being estimated. Do not treat the current specification as a production contract.

**Statistical expansion:** The [production-oriented statistical review](strike-vol-beta-statistical-review.md) now specifies OLS/WLS/Huber selection, HC3/HAC/cluster/bootstrap inference, estimand and release contracts, and executed Monte Carlo and chronological hedge experiments. See §8 below for the relationship to these findings.

Reviewed baseline: [spec-before-review.md](strike-vol-beta-review/spec-before-review.md), SHA-256 `dddedf709344440b9c3c1948984f61fc48e978ef297bdfdc94622e74fe0ac61c`. All line references below refer to this preserved baseline. The working spec's source section has been reconciled with the full Moontower articles; substantive design changes below remain recommendations.

Evidence comprises a complete spec review, the two full articles accessed through the user's subscribed Safari session, primary literature checks, and executable numerical counterexamples. No production code or raw market dataset was supplied. Empirical performance, feed behavior, and the articles' regressions have not been independently reproduced.

## 1. Findings that block implementation

P1 means a design defect that can invalidate the output or its use. P2 means an unresolved contract or validation issue that must be settled before publication. These are specification findings, not claims about existing software.

| ID | Severity | Finding | Baseline location |
|---|---|---|---|
| F01 | P1 | Model-specific SSR behavior becomes a circular acceptance rule | §§2.1, 6.2, 7.2; L68, L277–291, L343–345 |
| F02 | P1 | ATM SSR is extended across strikes without identification or denominator controls | §§1, 2.1, 6.2; L17, L50–70, L277–289 |
| F03 | P1 | Full-day carry has no enforceable information cutoff | §4.3 and outputs; L160–170, L402 |
| F04 | P1 | Futures options lack a contract-specific pricing and hedge definition | §§2, 3, 4.1, 4.3, 9; L29–36, L108, L133–166, L380–402 |
| F05 | P1 | Call/put averaging does not generally cancel forward error | §5.2; L212–223 |
| F06 | P1 | Clock controls conflict, and the proposed lag test reverses the mechanism | §§4.1, 4.4, 5.1; L138, L176, L188, L198–205 |
| F07 | P1 | Vanna attribution is incorrectly used as an identification test and pricing bridge | §§2.3, 8; L96, L358–372 |
| F08 | P1 | Daily dispersion is presented as assumption-free statistical inference | §§6.2, 7; L289, L323–325 |
| F09 | P2 | The beta and Greek units permit incompatible implementations | §§2.1–2.2, 9.1; L40–59, L79–90, L388 |
| F10 | P2 | Regression weights target the wrong response variance and change the objective | §§4.4, 6.1–6.2; L178, L254–289 |
| F11 | P2 | Missing bars and multi-frequency eligibility are unspecified or contradictory | §§4.1, 4.5, 6.1, 7.1; L133–138, L186–188, L269, L329–350 |
| F12 | P2 | Smile smoothing and hierarchical shrinkage hide common estimation errors | §§4.4, 6.2; L174–188, L277–289 |
| F13 | P2 | Intraday claims, directional betas, and event exclusions lack an executable policy | §§5.4–5.5, 6.3–6.4, 8.3, 9.2 |
| F14 | P2 | Backtesting and publication contracts are not reproducible enough | §§8.2–10.4; L368–428 |

## 2. Reconciliation with Moontower

Treat these as high-quality primary practitioner sources for the economic problem and an implementable baseline. Their statistical heuristics remain testable choices, not guarantees.

**M1 — [Embedding spot-vol correlation in option deltas](https://moontower.substack.com/p/embedding-spot-vol-correlation-in), Kris Abdelmessih, January 15, 2026.** The post incorporates expected vega P&L into hedge delta, illustrates numerical repricing along a vol path, and initially assumes proportional changes across strikes. That simplification should be declared when reused, rather than silently treated as a measured surface law. The signed hedge adjustment in the spec is consistent with this framing when units are explicit.

**M2 — [Using tick data for spot-vol correlations](https://moontower.substack.com/p/using-tick-data-for-spot-vol-correlations), Kris Abdelmessih, August 20, 2026.** The recipe fixes the prior close's near-ATM strike, selects the OTM leg, and regresses relative IV changes on spot returns. The example uses five-minute intervals, a half-expected-move filter based on beginning-of-interval IV, two-week windows, directional splits, and pairs-bootstrap intervals. Expiry aggregation and the range over which to trust beta remain open choices.

The specification's per-bar cubic, equal call/put averaging, daily per-strike WLS, mandatory SSR surface, and James–Stein stage are its own extensions. M2 does not validate those layers. Start with a transparent reference estimator and require each added layer to demonstrate incremental value.

Do not inherit M2's suggestion that tiny returns inherently create an OLS division problem: OLS uses aggregate covariance and variance. A move filter can change signal quality, but also changes the estimation population. Individual-pair bootstrap resampling does not preserve time dependence; an interval including zero does not prove randomness. These are this review's statistical qualifications.

## 3. Detailed findings and corrections

### F01 — Rejecting valid markets because they disagree with the prior

**Failure.** The spec imposes monotonic maturity decay, a long limit of one, and short-end bounds, then declares deviations evidence of contamination. Fitting a constrained model and rejecting observations for violating its constraints is not independent validation. It can erase genuine regimes and make a smooth, plausible number appear more reliable than the data support.

**Primary-source check.** Bergomi's [original paper](https://www.fields.utoronto.ca/programs/scientific/09-10/finance/derivatives/bergomi.pdf), §§2.2–3.2, gives ATM anchors and derives ranges under stated approximations and covariance-decay assumptions. It also gives a long-maturity limit of `2 − γ` for a slower-decaying covariance family, not universally one. [Friz–Gatheral](https://arxiv.org/html/2406.16131v1), Corollary 5.6 and §§7–8, supports the stated rough short-time result in its setting, but discusses sensitivity to dynamics and differences between empirical and model SSR. [Vargas–Dao–Bouchaud](https://arxiv.org/abs/1311.4078) explicitly reports values exceeding two. The spec also misattributes that last paper to Ciliberti, Bouchaud, and Vargas.

**Correction.** Keep theory curves as labeled comparisons or optional soft priors. Publish direct beta independently of whether SSR matches those priors. Separate mechanical validity failures from model disagreement. Never clip a valid observation into a purported universal range. Validate supported assets individually.

**Acceptance check.** Feed a locally smooth synthetic surface with `ψ = −0.10` and fixed-strike sensitivity `b = −0.20`; local ATM SSR is three. The pipeline must retain the beta and flag prior disagreement, rather than classify the inputs as corrupt. This is a local algebraic counterexample, not an assertion of global arbitrage-free dynamics.

### F02 — The coordinate identity is local; the published diagnostic is ATM

**Failure.** L17 reverses the interpretation used later: a smile frozen in forward moneyness has constant ATM IV; a fixed-strike smile can exhibit moving ATM IV. At a non-ATM strike, `1 + b_K/ψ(K)` concerns movement of a corresponding constant-moneyness point, not necessarily ATM. A daily mean conversion is also not an exact rescaling of a stochastic regression when IV, skew, or sensitivities vary.

**Derivation.** At one state, let `b_K` denote the decimal-IV response per log spot move at fixed strike. For a moving strike with constant `k = ln(K/F)`, the local response is `b_K + a ψ`, where `a = d ln F / d ln S`. At ATM, with `a = 1`, this gives `SSR_ATM = 1 + b_ATM/ψ_ATM`. That relationship does not identify all strike-level dynamics from one ATM statistic. Nor does frozen moneyness exactly define frozen delta under every delta convention.

**Correction.** Keep fixed-strike beta as the primary output. Name any non-ATM ratio `local_skew_response_ratio`, document its definition, and avoid comparisons with ATM literature without a mapping. Report ATM SSR separately using matched coordinates, units, horizons, and weighting. Define which forward is moving and whether `a = 1` is assumed. When the denominator is small or imprecise, return an undefined diagnostic with a reason; retain a valid beta. Propagate numerator/denominator covariance instead of treating measured skew as exact.

**Acceptance check.** Constant-moneyness and fixed-strike synthetic smiles must produce the correct separate fixed-strike and floating-ATM responses. A flat-skew surface with nonzero strike beta must produce a usable beta and null SSR, not a failure of the hedge estimate.

### F03 — Full-day carry is retrospective unless publication is delayed

**Failure.** L166 estimates carry from the entire session and applies it to intraday observations. At 10:00, a 15:55 quote was not available. A backtest that acts on a same-day estimate can therefore use future information. A causal across-day filter does not cure within-day lookahead. A two-sided state-space smoother can add a second source of lookahead.

**Nuance.** An end-of-day reconstructed history published for use the following session can legitimately use the completed day. The defect is the absence of an explicit timing contract, not the mere existence of retrospective estimation.

**Correction.** Choose one of two products: (a) causal intraday estimates using prior-day or expanding-window carry, or (b) completed-day estimates effective only after all inputs and computation are available. Give every carry estimate `available_at`, `fit_window_end`, method, version, and forward-construction lineage. Never join on date alone. At decision time `t`, all inputs and fitted parameters must have `available_at ≤ t`.

**Acceptance check.** Modify only observations after noon; no pre-noon published estimate or simulated hedge may change. A revised after-close reconstruction must have a new version and later availability.

### F04 — Futures options require their actual underlying contracts

**Failure.** `S_t` is called an underlying futures price, but `F_t(T)` adds a carry term to it as though it were cash spot. Option expiry is also implicitly conflated with the delivery maturity of the underlying future. The keys cannot distinguish two futures contracts for the same root. A regular equity-session template is not a complete futures trading calendar.

**Exchange check.** [CME's options-on-futures explanation](https://www.cmegroup.com/education/whitepapers/fundamentals-of-options-on-futures) and [margining-style guide](https://www.cmegroup.com/education/articles-and-reports/a-primer-on-margining-styles-for-options) describe contract-specific exercise and settlement conventions. European put–call parity must not be indiscriminately applied to American exercise premiums.

**Correction.** Require option-series ID, exact underlying-future ID and delivery month, option expiration timestamp, exercise style, premium/margin convention, multiplier, currency, tick schedule, pricing model, and trading calendar. For a European Black option on a specified future, use that future's price as the pricing underlying and separate discounting; do not add cash carry again. Restrict the first supported product family explicitly. Continuous back-adjusted futures must not silently substitute for deliverable contracts.

**Hedge conversion.** With signed portfolio vega already including option multipliers, derive hedge contracts from P&L units. For the same future, `n_extra = −V_pt × σ_pt × β / (F × M_f)`, where `M_f` is currency per futures-price point. A different hedge future needs an estimated mapping or multivariate hedge. Portfolio legs mapping to different futures cannot simply be combined into one notional.

**Acceptance check.** Two options sharing a root and expiry date but referencing different futures must remain distinct. Unsupported exercise or price conventions must fail explicitly, before inversion or parity estimation.

### F05 — The claimed cancellation is algebraically false

**Failure.** Using the spec's own first-order formulas, the equal average has error

```text
δσ_avg = ε [1 − 2 N(d1)] / [2 φ(d1) √τ].
```

It vanishes only at `d1 = 0`, not generally, and not exactly at forward ATM for positive volatility and time. At `F=100, K=90, σ=0.30, τ=0.25`, a +10 bp forward error produces approximately **−0.191 volatility points** of first-order average error; direct repricing/inversion gives **−0.194**. The diagnostic's supposed error cancellation is itself a material error source.

For matched European calls and puts with the same true IV under these assumptions, weights `w_call = N(−d1)` and `w_put = N(d1)` cancel this particular first-order perturbation. That is an algebraic observation, not a recommendation to replace all data controls with those weights. Quote noise, different times, early exercise, model mismatch, and nonlinear errors remain.

**Correction.** Remove the unconditional cancellation claim. Use call/put discrepancy as a multi-cause diagnostic. It cannot uniquely identify forward error: asynchronous quotes, dividend assumptions, exercise models, and side-specific errors can also cause disagreement. Estimating a forward from the same pair and then testing that pair's parity is circular; use independent or held-out evidence where feasible.

**Acceptance check.** Reprice matched calls and puts over strike, maturity, and signed forward perturbations. Check the predicted error and residual error of any proposed combination. Include contaminated-leg and American-style cases rather than testing only ideal European ATM pairs.

### F06 — Correct inversion time does not create a synchronized surface

**Failure.** Inverting each quote against its own underlying is sensible, but then fitting a bar-close smile with bar-close `F` mixes volatility states observed at different times. A quote timestamp up to 60 seconds old can be a fifth of a five-minute interval. The single `quote_ts` in a fitted point also cannot describe the timestamps of all input quotes.

The proposed fault injection pairs a fresh option price with the previous underlying. For a call after a rally, that generally biases inferred IV upward, whereas the described mechanism—stale option with fresh underlying—biases it downward. In a controlled 100→101 move at constant 30 vol, these pairings invert to approximately **32.73 vol** and **27.28 vol**, respectively. A directional claim about a whole regression additionally depends on the price path; there is no universal 'more negative' rule.

**Correction.** Specify as-of joins using underlying observations at or before option quote time, with age limits on both legs and actual bid/ask timestamps if available. Define how asynchronous observations become a common-time surface, or use tightly synchronized direct observations first. Record the complete input quote set, timestamp dispersion, maximum age, and evaluation timestamp. A symmetric absolute timestamp tolerance must not authorize joining future observations.

**Acceptance check.** Inject stale options and stale underlyings separately, on both calls and puts, into a known zero-beta market. Verify predicted directions under controlled moves and detection of the injected faults. Do not require a particular sign from arbitrary live lead/lag regressions. Matching chart signatures alone cannot prove cleanliness.

### F07 — Beta does not identify vanna P&L or a pricing measure

**Failure.** The spec expects the delta/gamma/theta residual of a risk reversal to close using vanna implied by beta, and blames contamination when it does not. That residual contains at least

```text
Vega × Δσ
+ Vanna × ΔS × Δσ
+ 0.5 × Volga × (Δσ)^2
+ other state changes, higher-order terms, marking and execution effects.
```

The leading omitted term is vega. Even a correct conditional slope leaves residual volatility shocks. A regression coefficient also does not alone determine volatility variance, cross-strike covariance, or nonlinear joint moments. Historical finite-horizon sensitivity is not a sufficient risk-neutral input for GVV option pricing. Instantaneous diffusion covariations have useful measure invariances, but they do not establish equality between this finite-sample regression and every pricing-model parameter.

**Correction.** Separate three uses: local hedge adjustment, P&L attribution, and pricing-model calibration. Validate Greeks against full repricing with observed state changes. Validate the beta hedge on subsequent observations. Require a separately documented GVV mapping, volatility units, horizon, higher moments, and measure assumptions before permitting that consumer. If pricing residuals do not close, investigate all omitted terms and data conventions; do not diagnose a forward error by elimination.

**Acceptance check.** A simulation with correct beta and independent volatility shocks must retain nonzero attribution residuals without being labeled contaminated. Compare the proposed hedge against the conditional minimum-variance target for the chosen horizon and loss function. [Hull–White's primary abstract](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2658343) supports the minimum-variance-delta motivation; it does not validate this specific pipeline.

### F08 — Regime dispersion is not a confidence interval

**Failure.** Daily estimates mix measurement uncertainty and real changes in the coefficient. Their quantiles describe historical variation; they are neither automatically confidence intervals for today's latent beta nor prediction intervals for tomorrow. Serially correlated days and shared surface fits do not disappear by changing the aggregation level. The claim that no assumptions about the error process are required is false.

**Correction.** Report three separately labeled objects: uncertainty in a specified fitted coefficient, historical regime dispersion, and uncertainty in the next-period hedge input. Evaluate a block/day-cluster bootstrap or an explicit time-series model, preserving the whole intraday cross-section within the resampling unit. Refit carry where appropriate, smiles, regressions, shrinkage, and temporal aggregation in each replicate. Keep chronological forecasting evaluation separate from uncertainty resampling. Few days still mean little information; more bars are not more independent regimes. [Palm–Nagler](https://arxiv.org/abs/2310.19683) explains why dependent data require a dependence-aware bootstrap.

**Acceptance check.** Establish interval coverage in simulations containing persistent latent beta and correlated quote errors. An interval's coverage label must specify its target. Confidence intervals containing zero must not be labeled proof of no dependence.

### F09 — Specify units once, including the displayed beta

**Failure.** `β_pts = S ∂σ/∂S` is described as volatility points per 1% move, while `σ` later explicitly means volatility points. These are compatible numerically only under carefully defined conventions; the spec never declares the stored units of `σ_fit`, `ψ`, or Greek derivatives. The hedge example is correct, but it does not settle the API contract.

**Correction.** Use explicit names and decimal internal IV:

```text
σ_dec                 = 0.40
σ_pt                  = 100 × σ_dec = 40
r                     = Δ ln S, approximately 0.01 for a 1% move
β_rel                 = slope of Δ ln σ_dec on r
b_dec_per_log_return  ≈ σ_dec × β_rel       (local conversion)
b_pt_per_log_return   = 100 × b_dec_per_log_return
b_pt_per_1pct_return  = 0.01 × b_pt_per_log_return
extra_hedge_dollars   = −Vega_dollars_per_point × σ_pt × β_rel
```

For `β_rel=1`, `b_dec_per_log_return=0.4` and displayed `b_pt_per_1pct_return=0.4` happen to share a numerical value. With point-valued IV, `b_pt_per_log_return` is instead 40. Preserve this distinction. Computing a local derivative from a regression requires an approximation/conditioning statement; the header's bare `∂σ/∂S` is not a fully defined statistical estimand.

For decimal vega, `Vega_dec = 100 × Vega_pt`. The option's additional dollar delta is positive `Vega_pt × σ_pt × β_rel`; the additional hedge has the opposite sign. Total hedge must include conventional delta. Never apply the correction twice when the upstream delta already includes smile dynamics. Conversion of a daily log slope using mean IV/skew must be labeled approximate, not an exact identity.

**Acceptance check.** Test the same economic position through decimal and point-valued paths, signed long/short vega, positive/negative beta, and multipliers. A +$1,000/point vega at 40 vol with beta one requires −$40,000 additional underlying, which earns −$400 on a +1% move.

### F10 — Weighting is not just a precision improvement

**Failure.** `(spread/2)/vega` approximates uncertainty in IV levels, not in differences of log fitted IV. If `a_t` denotes the standard deviation of IV-level measurement error, a first-order variance approximation is

```text
Var(error in Δ ln σ_t)
≈ a_t²/σ_t² + a_(t−1)²/σ_(t−1)²
  − 2 Cov(e_t,e_(t−1))/(σ_t σ_(t−1)).
```

Both endpoints and covariance matter. A spread is a noise proxy, not an established standard deviation. Shared smile-fit errors create more dependence. Level 2 says inverse standard error rather than inverse variance and does not identify the intended objective. Multiplying by additional 'fit precision' may double-count information.

The classical attenuation formula in §5.3 also assumes more than the pipeline establishes. The same noisy underlying enters both the return regressor and IV inversion, so regressor error and response error can be correlated. Depending on option side and timing, bias can strengthen, weaken, or reverse the fitted relationship. An attenuation-only diagnosis is therefore incomplete even before applying WLS.

**Correction.** Name the statistical objective: unconditional linear projection, liquidity-weighted projection, filtered large-move projection, or a particular portfolio's hedging loss. WLS can change the estimated economic relationship when beta varies by liquidity or regime. Use unweighted regression as a comparator, derive the response-error model, and make weight caps and timing explicit. Do not claim daily IV is nearly constant during the shock regimes that matter most.

**Acceptance check.** Simulate a relationship whose beta changes with spreads. Document which target OLS and WLS recover; choose based on held-out hedge loss. Perturb one endpoint's uncertainty and verify both adjacent return observations receive the appropriate treatment.

### F11 — The advertised frequency test cannot run under the eligibility rule

**Failure.** A 390-minute equity session contains at most 26 fifteen-minute or 13 thirty-minute intervals before opening and endpoint filters. The 40-observation minimum rejects every such daily cell. Moreover, differencing the next surviving panel row after a dropped bar can silently create a longer interval paired with a five-minute underlying return. Redefining the strike ladder each day can similarly create artificial overnight changes if grouped incorrectly.

**Correction.** Construct explicit endpoint pairs. Require identical underlying and IV start/end times, fixed contract/strike, and the intended interval duration. Break at missing endpoints and session boundaries; never forward-fill a missing IV change as zero. Define whether the opening exclusion removes an endpoint, an interval, or both. Use multi-day windows or frequency-specific information requirements for the signature experiment, matched for dates, contracts, sessions, and event inclusion.

A signature plot is descriptive. Negative beta attenuated toward zero at high frequency may become more negative as the interval lengthens; it need not 'rise'. Genuine horizon dependence is also possible. Compare signed estimates and uncertainty, not a mandated direction or plateau.

**Acceptance check.** Remove an interior endpoint and ensure no accidental ten-minute change enters the five-minute regression. Verify that the entire 1/2/5/15/30-minute comparison yields eligible matched samples or a clear insufficient-data result.

### F12 — Fitted-strike observations are not independent measurements

**Failure.** A cubic fitted to a changing set of quotes can move because of composition changes, extrapolation, or coefficient instability. All evaluated strikes share the same coefficients and forward. Treating many ladder points as independent evidence exaggerates information. Smoothness gates then partly test smoothness imposed by construction. A good IV RMSE does not guarantee accurate derivatives or economically valid option prices.

**Correction.** Begin with direct liquid-strike IV as a reference and demonstrate whether smoothing helps. Keep interpolation within supported quote regions; declare wing and expiry support. Record the fit's input IDs, side selection, point/price residuals, conditioning, coefficient covariance, and derivative uncertainty. Check positive vol and appropriate strike-price monotonicity/convexity over the published domain. Carry full covariance or resample at the surface/day level during shrinkage. Naive James–Stein guarantees do not transfer automatically to correlated, heteroskedastic ratio estimates.

**Acceptance check.** Hold the true surface constant while changing quote coverage and injecting a common forward error. The system must identify fit/composition uncertainty rather than publish false precision. Compare raw and fitted responses at independently observed liquid strikes.

### F13 — 'Live' needs a timing and action policy

**Failure.** A daily fit followed by a ten-session EWMA and daily refresh is a daily-updated product, even if inputs are five-minute bars. It may be a sensible first version, but does not establish rapid intraday adaptation. A single day's regression does not remove intraday seasonality. Excluding every macro-event day changes the target population and may remove the strongest evidence about hedge behavior.

The statement that down beta is the number that matters for skewed inventory is too broad. Inventory, asset, stress direction, and objective all matter. The direction of the upcoming bar is not available when selecting its hedge. Weak next-day SSR predictability does not logically imply that shortening a noisy estimator's window improves it.

**Correction.** Specify update frequency, earliest effective time, training window, applicable session, and fallback. Keep up/down slopes as scenario outputs until a causal pre-trade hedge rule is validated. Candidate rules include a symmetric minimum-variance coefficient or a documented forecast-weighted/robust objective. Evaluate event and ordinary sessions separately without dropping event results from deployment assessment. Estimate or diagnose time-of-day variation on historical data. Tune window length and shrinkage jointly on chronological validation, allowing a zero-adjustment baseline.

**Acceptance check.** A hedge generated at the start of a bar must be identical regardless of that bar's future sign. A regime-flip simulation should report adaptation lag, extra turnover, and hedge deterioration. Overnight risk needs a separate stated policy.

### F14 — A backtest can look successful without proving this estimate useful

**Failure.** Lower in-sample P&L variance is insufficient: one can optimize the hedge after seeing the return, tune on the final evaluation period, suppress unfavorable failed-gate periods, or reduce variance while increasing costs or losses. `config_hash` alone cannot distinguish changed code, revised market data, different contract metadata, or a new run under unchanged settings. `expiry` as a date and a boolean gate do not fully identify eligible observations or consumer behavior.

**Correction.** Require chronological train/validation/test splits, point-in-time inputs and publication lag, common inventory and marks, matched hedge schedules, contract rounding, spread/slippage/fees, and net results by asset, tenor, moneyness, direction, event state, and liquidity. Include every requested hedge opportunity, reporting suppressed and stale periods and their actual fallback. Compare conventional delta, a transparent direct-strike reference, and each added modeling layer. Choose thresholds before looking at the final holdout.

For every output, store instrument IDs, `asof_ts`, `available_at`, `effective_from`, `training_start/end`, `sampling_interval`, `estimation_measure`, units, baseline-delta convention, source-data version, code revision, config hash, run ID, model version, uncertainty target/method, input coverage, and reason-coded status. Store live input IV/skew or their versions to distinguish current risk conversion from historical calibration. Define uniqueness/idempotency, retractions/supersession, stale maximum age, expiry handling, unknown-strike support, and how consumers handle unavailable estimates. Do not silently map unavailable beta to a reliable zero or carry stale beta indefinitely.

**Acceptance check.** Replay an archived decision using only information available then; recover the same estimate and hedge. Correct a source quote without changing config and ensure the revision creates an identifiable new version. Economic approval must include costs, coverage, and uncertainty in the improvement, not just an R² or a variance ratio.

## 4. Proposed replacement implementation sequence

1. **Freeze the product and estimand.** Choose one underlying contract family, pricing model, IV/Greek units, hedge instrument, sampling horizon, session calendar, publication cutoff, and loss function. Implement F02–F04 and F09 contracts before model work.
2. **Build the direct-strike reference.** Add matched endpoints and strict quote lineage. Make move filtering an explicit variant, retaining unfiltered results and keep counts. Keep contract/expiry windows separate. Establish the baseline before introducing cross-strike fits.
3. **Run adversarial input experiments.** Add both kinds of timestamp mismatch, forward perturbations, missing bars, call/put switches, flat skew, quote-composition changes, genuine beta sign flips, and event shocks. Verify fault detection against known truth.
4. **Estimate beta with honest uncertainty.** Use a window containing enough independent sessions; compare OLS and justified weights, symmetric and asymmetric response. Add dependence-aware inference. Record conditioning choices and information availability.
5. **Test complexity incrementally.** Introduce smoothing, shrinkage, and temporal filtering one at a time. Compare held-out hedge error, cost, coverage, and adaptation delay. Keep SSR as a diagnostic; any prior is optional and disclosed.
6. **Approve consumers separately.** Delta hedging can proceed after a successful point-in-time backtest and shadow evaluation. GVV pricing requires its own mathematical mapping and validation. One successful consumer does not validate the others.

## 5. Required adversarial acceptance matrix

| Experiment | Required result |
|---|---|
| Constant fixed-strike smile | Fixed-strike beta zero; moving ATM response consistent with skew |
| Constant forward-moneyness smile | Moving ATM response zero; fixed-strike response includes coordinate transport |
| Flat skew with real beta | Beta retained; SSR explicitly undefined |
| Local SSR above two | Prior disagreement flag without rejecting otherwise valid inputs |
| Signed forward perturbation | Correct call/put error signs and first-order magnitudes |
| Stale option vs stale underlying | Distinct fault mechanisms detected; no universal lag-sign rule |
| Changed post-cutoff data | No earlier estimate or hedge changes |
| Interior missing endpoint | No mismatched-duration regression row |
| Sparse 15/30-minute samples | Frequency-aware eligibility, with no impossible minimum |
| Shared fit error across strikes | No false multiplication of independent sample size |
| Persistent beta and quote noise | Coverage assessed for the declared uncertainty target |
| Positive commodity beta or sign flip | Estimate allowed; adaptation and hedge loss measured |
| Event/overnight observations | Explicit deployment coverage and fallback, not silent omission |
| Different futures delivery contracts | Separate identities and contract-aware hedge conversion |
| Decimal/point/multiplier conversions | Same economic hedge through every supported unit path |
| Dataset revision with same config | Traceable new output version and reproducible old decision |

## 6. Executed checks and limits

Run [check_counterexamples.py](strike-vol-beta-review/check_counterexamples.py) with Python 3; it writes [counterexample-results.json](strike-vol-beta-review/counterexample-results.json). All assertions passed. The checks use European Black prices with discount factor one and decimal IV; they test mathematical claims, not market performance.

| Executed check | Result |
|---|---|
| Equal call/put IV averaging, +10 bp forward error, 90 strike | −0.19094 vol points first-order; −0.19371 by inversion |
| Fresh call / stale underlying after 100→101 | 32.7310 inferred vol vs 30 true |
| Stale call / fresh underlying on the same move | 27.2774 inferred vol vs 30 true |
| Vega/IV/beta sizing conversion | −$40,000 hedge; −$400 hedge P&L per +1% |
| Smooth local beta/skew with ratio above assumed bound | SSR 3 algebraically; should not be rejected by fiat |
| Zero-skew denominator | Beta remains defined while SSR is null |
| 15/30-minute daily sample ceilings | 26/13 before additional filters; below the spec's 40 minimum |

The remaining acceptance-matrix entries are required future tests, not completed validations. Market-data quality, actual uncertainty coverage, runtime, and economic improvement remain unverified.

## 7. Source audit and confidence

| Source | What was actually checked | Appropriate use |
|---|---|---|
| Moontower M1 and M2, linked in §2 | Full subscribed text; accompanying hedge and regression summary images reviewed in the preceding article review | High-quality practitioner motivation and baseline; observational examples, not validation of the spec's extensions |
| Bergomi, *Smile Dynamics IV*, linked in F01 | Original 2009 manuscript, especially §§2.2–3.2 | ATM definition, anchors, and assumptions behind asymptotic results |
| Friz–Gatheral, *Computing the SSR*, linked in F01 | Full primary HTML, including asymptotics, §§7–8 and Appendix A | Model-dependent dynamics and comparison of instantaneous and sampled definitions |
| Vargas–Dao–Bouchaud, linked in F01 | Primary arXiv abstract | Direct counterexample to a universal upper bound; corrected authorship |
| Hull–White, linked in F07 | Primary abstract; full PDF endpoint was unavailable during this review | Minimum-variance motivation only; the spec's granular empirical claims were not reverified |
| Palm–Nagler, linked in F08 | Primary abstract and full HTML available | Dependence-aware resampling rationale |
| CME, linked in F04 | Exchange descriptions of exercise and margining conventions | Need for explicit product and pricing contracts |

The original `[v]` labels are claims made by the original author, not blanket certifications by this review. References not specifically checked above remain unaudited. Proposed remedies and counterexamples are reviewer analysis unless attributed to a source. No source is being used to claim that a fitted beta is a causal effect, a risk-neutral parameter, or a verified profitable hedge.

## 8. Statistical review expansion

The [statistical review](strike-vol-beta-statistical-review.md) completes the estimator/inference assessment requested after this initial review. It adds an explicit distinction between historical projection, state forecasting, and portfolio hedging targets; point-estimator and covariance decision tables; weighting and generated-input assumptions; bandwidth, clustering, and bootstrap requirements; and chronological selection and release criteria.

The [simulation results](strike-vol-beta-review/statistical-summary.md) cover 6,000 replicated estimation datasets and 200 chronological hedge experiments. Independent numerical checks compare coefficient and covariance calculations with statsmodels and bootstrap sufficient-statistic calculations with literal refits. These experiments qualify F08: dependence-aware resampling is not sufficient by itself, and the tested short-block methods are unreliable for the persistent-beta target. They also qualify §6.5 of the spec: Huber is a legitimate point-estimator challenger under some contamination models, while it can be inferior when large residuals reflect genuine state changes.

The original fourteen findings remain open design issues. Simulations validate or challenge specific statistical choices; they do not establish market-data quality or authorize deployment. Required future production checks are distinguished from the experiments actually executed.
