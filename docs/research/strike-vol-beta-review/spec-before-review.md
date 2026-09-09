# Strike-Vol Beta Estimation from Intraday Option Data

**Status:** design spec, pre-implementation
**Owner:** J. Myers
**Estimand:** ∂σ/∂S at fixed strike, per (strike, expiry), at intraday resolution
**Consumers:** effective-delta / delta-lean calculation, vanna pricing in GVV, sticky-vs-floating parametrization in the skew-dynamics model

---

## 1. Purpose

Produce a maintained, defensible estimate of how **strike vol** responds to spot, at a resolution fast enough to inform a delta lean on a live option book.

The naive alternatives fail for known reasons:

- **VIX or VXX beta on daily data.** Updates too slowly to be actionable, and measures a composite index rather than the vols you actually own.
- **ATM (floating) vol beta.** Contains the skew slide by construction. If the surface were perfectly floating, ATM vol would move with spot even with zero genuine spot-vol relationship. Reporting this number as "spot-vol correlation" double-counts skew.

Vega is a sensitivity to the vol *of the strike you hold*. That is the quantity to estimate.

The output is deliberately three numbers that are rescalings of one another (§2), because three different consumers want three different units.

---

## 2. Estimand and notation

| symbol | meaning |
|---|---|
| `S_t` | underlying (futures) price |
| `F_t(T)` | forward to expiry T |
| `K` | fixed strike |
| `k` | log-moneyness, ln(K/F) |
| `σ_t(K,T)` | implied vol of the fixed strike K |
| `r_t` | underlying log return over the bar |
| `ψ(k,T)` | local skew slope, ∂σ/∂k, from the fitted smile |
| `τ` | time to expiry in years |

### 2.1 The three normalizations

Define the primitive regression coefficient in **vol points per 1% spot move**:

```
β_pts(K,T)  =  ∂σ/∂S · S
```

From it:

```
β_rel = β_pts / σ              relative vol move per 1% spot move
SSR   = 1 + β_pts / ψ(k,τ)     skew-stickiness ratio (Bergomi 2009)
```

The SSR identity follows from decomposing the ATM vol move. Since the ATM strike tracks the forward one-for-one,

```
dσ_ATM/d ln S  =  β_pts + ψ
```

and Bergomi defines SSR as that quantity normalized by the skew, `SSR = (dσ_ATM/d ln S)/ψ = 1 + β_pts/ψ`. Estimating fixed-strike β and estimating SSR are therefore the same exercise in different coordinates.

Interpretation and use:

- **`β_pts`** — raw regression output. Not comparable across strikes, tenors, or vol regimes. Used only as an intermediate.
- **`β_rel`** — the elasticity. Feeds the lean formula directly (§2.2). This is the β in the Moontower framing.
- **`SSR`** — the surface-dynamics diagnostic, and the established quantity in the literature. Anchors:
  - `SSR = 1` — **sticky strike.** The fixed-strike surface is frozen, so `β_pts = 0`.
  - `SSR = 0` — **sticky delta / floating.** The smile is frozen in moneyness, so ATM vol does not move and `β_pts = −ψ`.
  - `SSR > 1` — **super-skew**, which is where index markets actually sit. The diffusive short-maturity limit is 2; Friz–Gatheral refine this to `H + 3/2` for a volatility process with Hurst exponent H.

**Report SSR rather than a bespoke ratio.** It makes the estimate directly comparable to published empirical values and to model-implied ones, which is the cheapest available sanity check on the whole pipeline (§7.3). It is also the parameter that belongs in the skew-dynamics model, replacing an assumed interpolation weight with a measured one.

**Sign discipline.** For an equity index, ψ < 0 and β_pts < 0, so SSR > 1 with both numerator and denominator negative. Getting a sign wrong here inverts the lean. Unit-test the identity against synthetic surfaces constructed to be exactly sticky-strike and exactly floating, and assert SSR recovers 1 and 0.

### 2.2 Connection to position sizing

The effective delta of an option is

```
Δ_eff = Δ_BS + Vega · ∂σ/∂S|_K
```

Multiplying the adjustment through by S and substituting gives the trader-units form:

```
delta lean = − Vega · σ · β_rel
```

with Vega in $ per vol point and σ in vol points. Long 1,000 vega at 40 vol with β_rel = 1.0 implies a $40,000 short lean. Short vega flips the sign.

These are the same quantity. The spec exists to put a defensible number in the β slot.

### 2.3 Explicit non-goals

- Not estimating the Heston ρ or any latent-parameter object. This is a reduced-form conditional sensitivity.
- Not estimating a realized-vol leverage effect. The LHS is implied.
- Not producing a forecast. `SSR` is estimated on realized co-movement; its use as a forward-looking input is a separate decision (§8.3).

---

## 3. Prerequisites

| requirement | note |
|---|---|
| Intraday option quotes with timestamps | Bid/ask, not trades. Trades are too sparse per strike and are sign-contaminated. |
| Intraday underlying at ≥ the option resolution | Same clock source. |
| Both timestamps preserved through ingest | Non-negotiable — see §5.1. A pipeline that stores only a bar label destroys the ability to detect staleness. |

**Data dependency:** IVolatility intraday equity options is currently tabled in the ivol warehouse; futures and futures options are the active focus. This spec is written against whichever source lands first. If the first cut runs on futures options, the smile fit (§4.4) and expiry handling are unchanged; the forward construction (§4.3) is simpler because carry is cleaner on a listed future.

Confirm before building: does the intraday feed deliver **quote timestamps** or only bar-aggregated snapshots? If only the latter, §5.1 controls degrade to a filter on bar completeness and the achievable resolution drops.

---

## 4. Pipeline

### 4.0 Overview

```
raw quotes ──▶ [4.1 clock] ──▶ [4.2 filter] ──▶ [4.3 forward] ──▶ [4.4 smile fit]
                                                                        │
                                                                        ▼
                                                            [4.5 strike-vol panel]
                                                                        │
                                                                        ▼
                                               [6.1 within-unit WLS] ──▶ [6.2 structure]
                                                                        │
                                                                        ▼
                                                          [6.3 temporal aggregation]
```

### 4.1 Clock and bar grid

- Bars: 5-minute, right-labeled, on the regular session only.
- Drop the first bar of the session. Opening-auction quotes invert unstably.
- Drop bars spanning any halt or session boundary. Never let a bar straddle the overnight gap.
- Regular equity session gives ~77 usable bars per day after the drop. Record the actual count per unit; it is an input to §7.

Within a bar, take the **last quote at or before the bar close** for each instrument, and record its own timestamp. Do not take a bar VWAP or midpoint-of-bar; it smears the timestamp and defeats §5.1.

### 4.2 Quote filtering

Reject a quote if any of:

- crossed or locked (bid ≥ ask)
- bid ≤ 0
- relative spread above threshold (config; start at 25% of mid, tighten by liquidity tier)
- absolute spread below one tick (stale-print artifact)
- implied vol outside plausible band, or inversion fails to converge
- option delta outside `[0.10, 0.90]` in absolute value

Log every rejection with a reason code. Rejection-rate drift by reason is a leading indicator of feed problems and belongs on the monitoring dashboard (§10.3).

### 4.3 Forward construction

**This is the highest-risk component in the pipeline.** See §5.2 for why.

Decompose the forward into a fast component that tracks spot bar-to-bar and a slow component that does not:

```
F_t(T) = S_t · exp(c_d(T) · τ)
```

- `S_t` — the contemporaneous underlying, refreshed every bar.
- `c_d(T)` — a carry rate (rate less dividend yield, or the futures basis), estimated **once per day per expiry** and smoothed across days.

Estimate `c_d(T)` from put-call parity on the tightest few near-ATM pairs, pooled across the whole day, then apply a smoother across days (EWMA or a local-level state-space filter). Carry is genuinely slow-moving; spot is not. The decomposition assigns each its correct timescale.

**Do not** compute a per-bar parity forward. Parity on a single bar inherits the full quote noise of both legs, and that noise then propagates into every IV on the surface with the amplification derived in §5.2.

**Do not** hold the forward fixed within the day. Then F fails to track S, and the identical error appears with the opposite sign.

### 4.4 Per-bar smile fit

Single-strike IV changes at 5-minute resolution are dominated by quote noise, particularly in the wings where vega is small and the inversion is ill-conditioned. Fit a smile per (bar, expiry) and evaluate it at the fixed strikes rather than differencing raw inverted IVs.

- Parametrize in `k = ln(K/F_t(T))` using the §4.3 forward.
- Functional form: cubic in `k` is sufficient for this purpose. SVI if no-arbitrage structure is wanted for other consumers; the marginal benefit for this estimand is small and the fit cost is not.
- Weighted least squares in the fit, weights as §6.1.
- Require a minimum number of surviving quotes per (bar, expiry); reject the bar otherwise.
- Store the fitted coefficients, not just the evaluated points. `ψ(k,τ)` is read off the fit analytically and is needed for `SSR`.

Evaluate at a **fixed strike ladder** defined once per (expiry, day) and held constant through the session. The ladder must not be redefined intraday — a ladder that tracks spot reintroduces the floating-vol problem the spec exists to avoid.

### 4.5 Panel construction

Output one row per `(expiry, strike, bar)`:

`σ_fit`, `ψ`, `k`, `S`, `F`, `τ`, `vega`, `spread`, `n_quotes`, `quote_ts`, `underlying_ts`, `fit_rmse`.

---

## 5. Contamination controls

Each entry: mechanism, control, test. These dominate the econometrics at this frequency. A perfect estimator on contaminated inputs produces a confident wrong number, and in both of the cases below the artifact has the *same sign and shape as the real effect*, which is what makes them dangerous.

### 5.1 Timestamp mismatch

**Mechanism.** Invert a stale option quote against a fresh underlying and the error is not random. A stale call price paired with a higher spot requires a *lower* implied vol to reconcile. Spot up, measured vol down — a manufactured negative spot-vol correlation, indistinguishable by eye from a genuine leverage effect.

**Control.**
- Invert each option against the underlying observed at **that option's own quote timestamp**, not at the bar label.
- Require `|quote_ts − underlying_ts| < δ`. Start at δ = 5 seconds; tune on the §7.1 signature plot.
- Drop the observation if the option quote age exceeds a threshold (config; start at 60s).

**Test.** Re-run the whole estimation deliberately mispairing option quotes to the *previous* bar's underlying. If the mispaired β is materially more negative than the correctly paired one, staleness is live in the data and δ needs tightening. This is a cheap, decisive test and should be a permanent fixture, not a one-off.

### 5.2 Forward error

**Mechanism.** The forward enters the inversion. Perturb F by a relative error ε and the implied vol shifts by, to first order,

```
Δσ_call = − ε · N(d₁) / (φ(d₁)·√τ)
Δσ_put  = + ε · N(−d₁) / (φ(d₁)·√τ)
```

Two consequences, both exploitable:

1. **The amplification is large.** At the money with one month to expiry, `N/φ ≈ 1.25` and `√τ ≈ 0.29`, so the multiplier is roughly **4.3**. A 10bp forward error moves the inverted vol by ~0.43 vol points. That is the same order as the entire quantity being estimated. The multiplier grows as `1/√τ`, so short tenors are worse.
2. **Calls and puts move in opposite directions.** This is the gift. It converts an invisible bias into an observable one.

**Control.** The fast/slow decomposition of §4.3. If both a call and a put are quoted at the strike with acceptable width, the parity-symmetric **average of the two implied vols cancels the forward error to first order** — prefer this to picking one leg. Fall back to OTM-only where one leg is unusable.

**Test.** Fit calls and puts separately at the same strike over the overlap region and compare. They must agree within tolerance. Systematic disagreement is a forward problem and nothing else; its magnitude backs out ε directly via the formula above. This test is more informative than any residual diagnostic and should gate publication (§7).

### 5.3 Errors-in-variables in the regressor

**Mechanism.** Microstructure noise in the underlying return attenuates the slope toward zero by the factor `σ²_true / (σ²_true + σ²_noise)`.

**Control.** For ES or a liquid index future at 5 minutes the signal-to-noise is high and the bias is small. It is not negligible for a less liquid underlying. Do not assume; measure it via §7.1.

### 5.4 Intraday seasonality

**Mechanism.** Both the regressor variance and the residual variance follow a strong U-shape. Pooling raw bars across days produces a fit dominated by the open and the close.

**Control.** The per-unit design of §6.1 largely handles this, since a single day's regression is estimated over one realization of the diurnal pattern rather than pooling across it. If a pooled specification is ever run, standardize by a time-of-day scale estimated on a trailing window first.

### 5.5 Earnings and scheduled events

**Mechanism.** Event-driven vol moves are not spot-driven and will masquerade as a large residual or, worse, as a large β if the event coincides with a spot move.

**Control.** Flag and exclude (underlying, day) pairs spanning an earnings release or scheduled macro event, into a separate estimation track. Do not silently pool them.

---

## 6. Estimation

Three levels: within-unit fit, cross-sectional structure, temporal aggregation.

### 6.1 Level 1 — within (expiry, strike, day)

Unit of estimation is one `(expiry, strike, day)` cell, ~77 bars.

```
Δ ln σ_t  =  α  +  β_rel · r_t  +  ε_t
```

**LHS in log vol.** Since `β_rel` is defined on relative vol moves, logs deliver it directly with no conversion. Within a single day σ barely moves, so log and level specifications are nearly identical here; logs simply skip a step.

**Weights.** IV measurement error is approximately `(spread/2)/vega`, so weight by its inverse variance:

```
w_t  ∝  vega_t² / spread_t²
```

Optionally multiply by the smile-fit precision at that strike.

**Intercept.** Retain it. It absorbs intraday vol drift and the shadow-theta glide. Do not force through the origin; a suppressed intercept pushes drift into the slope.

**Minimum bars.** Reject the unit below a floor (config; start at 40 usable bars).

Output per unit: `β_rel_hat`, its within-unit standard error, `R²`, `n`, and the mean `ψ` and `σ` over the day, so `SSR` and `β_pts` can be reconstructed.

### 6.2 Level 2 — cross-sectional structure

Level 1 gives a noisy `β̂` per strike per expiry per day. Do not consume these raw.

**Model SSR, not `β_pts`.** The skew slope `ψ` carries a term structure of roughly `τ^(−1/2)`. Normalizing by it absorbs that structure into the fitted smile, where it belongs, leaving a coefficient whose remaining tenor dependence is the economically interesting part.

**SSR is not flat in tenor, and its shape is known a priori.** It declines with maturity, approaching 1 (sticky strike) at long tenors and rising toward the short-maturity limit of 2 for a diffusive process — `H + 3/2` under rough volatility, so roughly 1.6 for the Hurst exponents typically estimated on index vol. Impose this shape rather than fitting it freely:

```
SSR(k, τ, d)  =  1  +  (γ₀(d) + γ₁(d)·k + γ₂(d)·k²) · h(τ)
```

with `h(τ)` a monotone decaying kernel (power law or exponential, one parameter, fitted on a long window and held fixed intraday). The known limits give hard bounds on the fit: `h → 0` at long tenor, and the short-tenor asymptote should land near 0.5–1.0 in the γ₀ scale.

Reconstruct `β_pts = (SSR − 1)·ψ` and `β_rel = β_pts/σ` for consumption.

Fit the cross-section per day, weighted by the inverse of the Level-1 standard errors. Shrink the per-unit estimates toward the fitted surface (hierarchical / empirical-Bayes; a James–Stein shrinkage on the daily cross-section is adequate to start). Strike-level daily estimates are too noisy to publish unshrunk.

**The imposed term structure is itself a test.** If the free fit of `h(τ)` disagrees materially with the theoretical decay — the wrong sign of slope, or a short-tenor asymptote far outside [1, 2] — that is evidence of contamination in §5, not a discovery about the market. The `1/√τ` amplification of forward error (§5.2) bites hardest at exactly the short tenors where SSR is largest, so a short end that looks anomalously high is the expected signature of a forward problem.

### 6.3 Level 3 — temporal aggregation

The live number is an EWMA of the daily cross-sectional coefficients, with a half-life set by the tradeoff between responsiveness and noise (config; start at 10 sessions and calibrate against §8).

Retain the full daily series. Its dispersion is the inference (§7) and its time variation is itself the signal — spot-vol behavior is regime-dependent, and a single pooled constant hides exactly the thing worth knowing.

### 6.4 Asymmetry

A single slope imposes a linear response the data will likely reject. Estimate, as a secondary specification:

```
Δ ln σ_t = α + β⁻·min(r_t,0) + β⁺·max(r_t,0) + ε_t
```

and separately a quadratic term for convexity. Publish the asymmetric form alongside the symmetric one. For a book with skewed inventory, `β⁻` is the number that matters, not the average.

### 6.5 Robust regression — screening only

Fit Huber alongside the WLS on each unit and flag observations receiving heavy downweight.

**Use the flags as a data-quality screen, not as the estimator.** The heavy-tailed joint observations *are* the spot-vol relationship; large down moves are where the effect is strongest and where the convexity of §6.4 lives. A high-breakdown estimator will discard precisely those and return a coefficient describing the quiet middle of the distribution, which is not the number that sizes a lean.

Procedure: inspect the downweighted bars, delete genuine data errors (crossed quotes, failed inversions, timestamp violations that escaped §5.1), then report the WLS fit on the cleaned set.

Record the WLS-minus-Huber gap per unit as a published statistic. It measures how much of the estimate rests on the tails, which is worth knowing regardless of which number is used.

---

## 7. Inference and acceptance gates

**Inference comes from the day-to-day dispersion of the Level-2 cross-sections, not from within-unit standard errors.** Classical or even HC standard errors on 5-minute data understate uncertainty badly, because the residual structure is misspecified in ways no sandwich fixes. The cross-section of daily estimates prices the uncertainty empirically and requires no assumption about the error process.

Report: median, IQR, and the 5th/95th percentiles of the daily estimates over the trailing window.

### 7.1 Signature plot

Estimate at 1, 2, 5, 15, and 30 minutes and plot β against sampling interval. Interpretation:

- **Flat** — 5 minutes is clean, proceed.
- **Rising, then flattening** — microstructure contamination at the fast end; the plateau indicates the shortest defensible interval. Adopt it.
- **Rising without flattening** — something structural is wrong. Do not proceed to production; return to §5.

Fixed-strike betas are more noise-sensitive than ATM ones, so this diagnostic is more likely to bite here than in the VIX/SPX work.

### 7.2 Gates

Publication of a daily estimate requires all of:

| gate | threshold |
|---|---|
| call/put agreement at overlapping strikes (§5.2) | within tolerance; else forward is broken |
| `SSR` stability across adjacent strikes | no discontinuities; a jump means the smile fit or forward is wrong, not the market |
| `SSR` within plausible range | roughly [1, 2] for an index; outside that, suspect §5 before believing it |
| sticky-strike and floating unit tests | SSR recovers 1 and 0 on synthetic surfaces (§2.1) |
| mispaired-timestamp control (§5.1) | correctly-paired β not materially more negative under mispairing |
| smile fit RMSE | below threshold, per (bar, expiry) |
| minimum bars per unit | ≥ floor |
| signature plot | flat or plateaued at the chosen interval |

A failed gate suppresses publication for that unit and raises an alert. It does not silently fall back to a stale value without marking it stale.

---

## 8. Economic validation

Statistical fit is not the acceptance criterion. The estimate is correct when it prices a position.

### 8.1 Vanna P&L test

Take a risk reversal, whose theta is not purely the cost of gamma — the put owner collects vanna as well. Attribute realized P&L to delta, gamma, and theta alone, and compare the residual to the vanna P&L implied by the fitted β.

If β is right, the residual closes. If it does not close, β is contaminated, and §5.2 is the first place to look. This test is the reason the spec exists and should run continuously, not once.

### 8.2 Delta-lean backtest

Apply the lean of §2.2 to a historical book and compare realized P&L variance against the unadjusted book. A correct β reduces variance; a β with the right sign but wrong magnitude may not.

### 8.3 Forward-looking use

`SSR` is estimated on realized co-movement. Using it as a forward-looking input assumes persistence. Measure that assumption: regress next-day `SSR` on the EWMA of trailing `SSR` and record the R². If persistence is weak, the EWMA half-life of §6.3 is doing more harm than good and the live number should be shortened or the estimate should carry a wider band.

---

## 9. Outputs

### 9.1 `strike_vol_beta_daily`

| column | type | note |
|---|---|---|
| `asof_date` | date | |
| `underlying` | text | |
| `expiry` | date | |
| `strike` | numeric | |
| `k` | numeric | mean log-moneyness over the day |
| `tau` | numeric | |
| `beta_pts` | numeric | vol points per 1% spot |
| `beta_rel` | numeric | feeds the lean formula |
| `ssr` | numeric | skew-stickiness ratio, 1 = sticky strike |
| `beta_rel_shrunk` | numeric | post-Level-2 |
| `beta_down`, `beta_up` | numeric | §6.4 |
| `se_within` | numeric | diagnostic only, not for inference |
| `r2`, `n_bars` | numeric, int | |
| `huber_gap` | numeric | §6.5 |
| `gates_passed` | bool | |
| `gate_failures` | text[] | reason codes |
| `config_hash` | text | §10.4 |

### 9.2 `strike_vol_beta_live`

The EWMA-aggregated surface, keyed by `(underlying, expiry, strike)`, refreshed daily, with `stale` and `last_good_date` flags.

### 9.3 Standing charts

Per house chart conventions: daily `SSR` series with the current regime window shaded, reference lines at 1 and 2,, no high/low markers, no fill under the line. Source line as configured. A companion signature plot refreshed weekly.

---

## 10. Implementation and operations

### 10.1 Placement

- Storage: Postgres on the data node, alongside the ivol warehouse. Panel intermediates are large; consider Parquet on the external HDD for the bar-level panel and Postgres for daily outputs only.
- Orchestration: Airflow DAG, downstream of the intraday options ingest, gated on its completion sensor.
- Compute: the Level-1 fits are embarrassingly parallel across `(expiry, strike, day)`. Run on the compute node.

### 10.2 Structure

Follow the ivol/ORATS package pattern: config-driven, thin CLI, clean separation between ingest, transform, estimation, and publication layers. The estimation layer takes a panel and returns coefficients and should have no knowledge of where the panel came from — that separation is what makes §7.1 and the §5.1 mispairing test cheap to run.

### 10.3 Observability

Emit structured telemetry per the telemetry project: Parquet on the external HDD, one record per unit fit with timings, gate outcomes, rejection counts by reason code, and coefficient values. Dashboard the rejection-rate-by-reason series; drift there is the earliest available warning of feed degradation.

### 10.4 Reproducibility

Hash the full config (bar size, δ, filter thresholds, smile form, weight scheme, shrinkage, EWMA half-life) and stamp it on every output row. Never overwrite a published estimate — append with a new `config_hash`. Backfills are new rows, not mutations.

---

## 11. Configuration

| parameter | initial | notes |
|---|---|---|
| bar size | 5 min | validate via §7.1 |
| δ (timestamp tolerance) | 5 s | tighten if §5.1 test fails |
| max quote age | 60 s | |
| delta band | 0.10 – 0.90 | |
| max relative spread | 25% of mid | tighten by liquidity tier |
| smile form | cubic in k | SVI optional |
| min quotes per smile | tbd | set from data |
| min bars per unit | 40 | of ~77 |
| weights | vega²/spread² | |
| shrinkage | James–Stein on daily cross-section | upgrade to hierarchical if warranted |
| SSR term-structure kernel | power law in τ | §6.2; long limit 1, short limit ≤ 2 |
| EWMA half-life | 10 sessions | calibrate against §8.3 |

---

## 12. Open decisions

1. **Feed granularity.** Does the intraday source deliver quote timestamps or bar snapshots (§3)? This determines whether §5.1 is enforceable or only approximable, and it is the single largest open risk in the spec.
2. **First underlying.** Equity options are tabled in the ivol warehouse; futures options are the active track. Building first on a liquid futures underlying is likely faster and has a cleaner forward, at the cost of not being the eventual production target.
3. **Kernel form for the SSR term structure.** §6.2 imposes a monotone decay with known limits. Power law versus exponential, and whether the kernel is estimated per underlying or shared, is open. Estimate on a long window before committing.
4. **Call/put averaging vs OTM-only.** §5.2 prefers the parity-symmetric average where both legs are quotable. Confirm liquidity supports it at the strikes of interest before committing.
5. **Event handling.** Whether excluded-event days get their own estimation track or are simply dropped (§5.5).

---

## 13. Sources

Citations marked **[v]** were verified against the source in preparation of this document. Those marked **[k]** are standard references cited from knowledge and should be confirmed before the spec is circulated externally.

### 13.1 The estimand

- **Bergomi, L. (2009), "Smile Dynamics IV"**, Risk; and *Stochastic Volatility Modeling* (2016), Chapman & Hall. Introduces the skew-stickiness ratio and establishes the SSR = 1 / SSR = 0 anchors used in §2.1. **[k for the primary, v for the definition and anchors via secondary sources below]**
- **Friz, P. and Gatheral, J. (2024), "Computing the SSR"**, arXiv:2406.16131. Model-free expression for the SSR via the characteristic function; establishes that the short-maturity limit is `H + 3/2` where H is the Hurst exponent of the vol process, generalizing the classical diffusive limit of 2. This is the source of the term-structure bounds imposed in §6.2. **[v]**
- **"Follow the moneyness"**, Risk.net, Dec 2021. Practitioner account confirming the SSR convention (1 = sticky strike, 0 = sticky delta) and its use as a desk-level monitor, plus the limitation that it describes joint dynamics only at the ATM strike — which is precisely why this spec estimates the full strike panel rather than a single ATM number. **[v]**
- **Ciliberti, Bouchaud, Vargas, "Skew and implied leverage effect: smile dynamics revisited"**, CFM. Shows the SSR saturates at 2 for linear models at short maturity and converges to 1 at long maturity, and that non-linear models (asymmetric GARCH) can exceed 2. Relevant to whether the §6.2 upper bound should be hard or soft. **[v]**
- **Derman, E. (1999), "Regimes of Volatility"**, Goldman Sachs Quantitative Strategies Research Notes. The original sticky-strike / sticky-delta / sticky-implied-tree taxonomy. **[k]**

### 13.2 Consuming the estimate

- **Hull, J. and White, A. (2017), "Optimal delta hedging for options"**, *Journal of Banking & Finance* 82, 180–190. The direct empirical antecedent to this spec: regresses implied vol changes on underlying returns to construct a minimum-variance delta, and shows it beats stochastic-vol models on SPX even when those are recalibrated daily. Read §§4–5 before implementing §6, and note two of their findings that set expectations here:
  - The R² of the vol-change-on-return regression is itself the headline diagnostic, and it is materially lower for single stocks than for the index. Idiosyncratic noise drives a wedge between parameters estimated in one period and those that would hedge best in the next — this is exactly the persistence question raised in §8.3.
  - MV hedging performed poorly or negatively for puts on single names. Do not assume the lean helps uniformly across the book; §8.2 must be run per bucket, not in aggregate. **[v]**
- **Alexander, C. et al. (2012)**; **Crépey, R. (2004)**; **Vähämaa, S. (2004)**. Earlier work decomposing MV delta as practitioner BS delta plus vega times ∂E[σ]/∂S, and testing the local-volatility prescription of setting that derivative to the negative smile slope. That prescription is the SSR = 2 case; §6.2 estimates it rather than assuming it. **[v, via Hull–White's discussion]**
- **Castagna, A. and Mercurio, F. (2007), "The vanna-volga method for implied volatilities"**, Risk. Background for the GVV consumer of this estimate. **[k]**
- **Bakshi, Cao, Chen (1997), "Empirical performance of alternative option pricing models"**, *Journal of Finance* 52. **[k]**

### 13.3 Leverage effect

- **Black, F. (1976)**, "Studies of stock price volatility changes", Proc. ASA. **[k]**
- **Christie, A. (1982)**, "The stochastic behavior of common stock variances", *JFE* 10. **[k]**

Both are cited by Hull–White as the origin of the negative price–vol correlation this spec measures. Note the distinction: they concern realized vol, this spec concerns implied. Do not use them to justify a prior on the sign of `β_pts` at the strike level.

### 13.4 Microstructure

- **Andersen, Bollerslev, Diebold, Labys (2000), "Great realizations"**, Risk. Origin of the volatility signature plot used in §7.1. **[k]**
- **Epps, T. (1979)**, "Comovements in stock prices in the very short run", *JASA* 74. The Epps effect: measured correlation between assets collapses as the sampling interval shortens, from non-synchronous trading. This is the mechanism behind the §7.1 diagnostic and the reason a rising signature plot is expected rather than alarming — what matters is whether it plateaus. **[k]**
- **Hayashi, T. and Yoshida, N. (2005)**, "On covariance estimation of non-synchronously observed diffusion processes", *Bernoulli* 11. The estimator for covariance under asynchronous observation. Worth evaluating as an alternative to the fixed-grid pairing of §5.1 if the timestamp tolerance δ proves impossible to tighten. **[k]**
- **Zhang, Mykland, Aït-Sahalia (2005)**, "A tale of two time scales", *JASA* 100. Two-scale correction for microstructure noise; relevant to §5.3 if attenuation turns out to be material. **[k]**

### 13.5 Moontower

The framing follows Kris Abdelmessih's *using tick data for spot-vol correlations* (Aug 2026) and *embedding spot-vol correlation in option deltas* (Jan 2026): the lean formula of §2.2, the argument for strike vol over composite and floating measures, the critique of daily VXX/SPY beta as too slow and too coarse, and the observation that risk-reversal theta contains vanna rather than gamma alone (§8.1).

**Both posts are paywalled and cut off before their methods.** The tick-data post ends at the line introducing the recipe; the deltas post ends before the spreadsheet walkthrough. Everything in §4 through §7 is constructed here, not taken from the source.

Sections most likely to need revision once the recipes are available: sampling frequency (§4.1), the tick-pairing rule (§5.1), whether he fits a smile per bar or differences raw strike IVs (§4.4), and how he aggregates across strikes (§6.2). Reconcile on access.

---

## 14. Revision log

| date | change |
|---|---|
| initial | first draft |
| rev 1 | **Corrected §2.1.** The original draft asserted that a skew-normalized coefficient of 1 corresponds to a fully floating smile. That is wrong. Reparametrized on Bergomi's SSR, where sticky strike is 1 and floating is 0; the original `b` equals SSR − 1, so floating is `b = −1`, not `+1`. **Corrected §6.2**, which had hypothesized the normalized coefficient is flat in tenor. SSR has a pronounced and theoretically characterized term structure (long limit 1, short limit ≤ 2); the panel model now imposes that shape rather than testing for its absence. Added §13. |
