# Statistical simulation results

Generated from `statistical-results.json`; synthetic experiments, not market-data validation.

Seed: 20260909. 500 replications per scenario/window; 399 bootstrap draws per replication. 78 bars per day. All intervals nominally 95%. Coverage Monte Carlo SE near 95% is about 0.97 percentage points; see CSV for each actual value.

## Coverage of the declared target

| Scenario | Days | IID | HC3 | Bar HAC(12) | Day CR1 | Day HAC(3) | Day-block bootstrap(3) |
|---|---:|---:|---:|---:|---:|---:|---:|
| iid | 20 | 94.2% | 94.2% | 94.0% | 95.0% | 90.8% | 90.0% |
| heteroskedastic | 20 | 75.4% | 93.6% | 93.2% | 94.0% | 90.6% | 88.6% |
| within_day_dependence | 20 | 68.6% | 68.2% | 91.8% | 94.6% | 90.4% | 88.4% |
| persistent_daily_beta | 20 | 8.4% | 9.8% | 19.6% | 39.2% | 53.8% | 46.6% |
| classical_x_error | 20 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| shared_x_iv_error | 20 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| bad_option_prints | 20 | 94.4% | 95.6% | 95.6% | 95.6% | 92.2% | 87.8% |
| real_tail_response | 20 | 79.0% | 93.2% | 92.8% | 93.0% | 88.6% | 86.2% |
| liquidity_changes_beta | 20 | 84.2% | 94.0% | 93.4% | 94.4% | 90.2% | 89.0% |
| heavy_tails | 20 | 93.8% | 93.6% | 92.8% | 93.2% | 88.6% | 87.8% |
| within_day_dependence | 5 | 71.2% | 70.6% | 91.4% | 94.8% | 82.8% | 70.4% |
| persistent_daily_beta | 60 | 9.2% | 12.0% | 19.2% | 40.8% | 61.6% | 57.2% |

For measurement-error cases the declared target is the clean latent slope; observed-regression target coverage is a separate CSV field. For persistent daily beta it is the stationary population mean, not the realized window average or current state. A failing interval may be accurately centered on a different estimand.

## Point-estimator comparison

| Scenario (20 days) | Declared target | OLS mean / RMSE | Oracle WLS mean / RMSE | Huber mean / RMSE |
|---|---:|---:|---:|---:|
| iid | -2.000 | -1.999 / 0.025 | -1.999 / 0.025 | -1.999 / 0.025 |
| heteroskedastic | -2.000 | -1.989 / 0.084 | -1.994 / 0.060 | -1.992 / 0.079 |
| within_day_dependence | -2.000 | -2.003 / 0.048 | -2.003 / 0.048 | -2.003 / 0.049 |
| persistent_daily_beta | -2.000 | -1.987 / 0.492 | -1.987 / 0.492 | -1.987 / 0.495 |
| classical_x_error | -2.000 | -1.600 / 0.401 | -1.600 / 0.401 | -1.600 / 0.401 |
| shared_x_iv_error | -2.000 | -2.201 / 0.203 | -2.201 / 0.203 | -2.202 / 0.203 |
| bad_option_prints | -2.000 | -2.007 / 0.057 | -2.007 / 0.057 | -2.002 / 0.026 |
| real_tail_response | -2.392 | -2.390 / 0.047 | -2.390 / 0.047 | -2.245 / 0.154 |
| liquidity_changes_beta | -1.800 | -1.801 / 0.082 | -1.108 / 0.692 | -1.290 / 0.512 |
| heavy_tails | -2.000 | -2.000 / 0.027 | -2.000 / 0.027 | -1.999 / 0.020 |

WLS uses known innovation variances, not estimated production weights. Huber intervals are deliberately absent: its point estimator is assessed without pretending an OLS covariance formula applies.

## Chronological hedge experiment

100 independent replications per scenario; no future observations enter a hedge. All values below refer to the final 40 held-out days.

| Scenario | Method | Hedge MSE ($²/bar) | Synthetic cost ($/day) | Mean net P&L ($/bar) |
|---|---|---:|---:|---:|
| stable_with_bad_quotes | selected | 10025.07 | 0.0657 | 0.0402 |
| stable_with_bad_quotes | OLS_w20_shrink1.0 | 10049.85 | 0.1215 | 0.0373 |
| stable_with_bad_quotes | Huber_w20_shrink1.0 | 10024.78 | 0.0652 | 0.0401 |
| stable_with_bad_quotes | zero | 49967.77 | 0.0000 | 0.3748 |
| unanticipated_regime_flip | selected | 34424.02 | 0.9092 | -0.1932 |
| unanticipated_regime_flip | OLS_w20_shrink1.0 | 32038.55 | 0.9404 | -0.1947 |
| unanticipated_regime_flip | Huber_w20_shrink1.0 | 34450.60 | 0.9090 | -0.1981 |
| unanticipated_regime_flip | zero | 36931.73 | 0.0000 | -0.5564 |

Trading-cost assumptions and the dollar normalization are in the statistical review. These are first-order exposure experiments with constant vega-vol exposure, not full option repricing. Monte Carlo standard errors and selected-method counts are in the JSON. The selected strategy is picked on earlier validation data; the surprise regime flip occurs in the untouched test period.

## Verification

OLS/WLS coefficients and IID, HC3, bar-HAC and day-CR1 covariance calculations agree with statsmodels; day-score HAC and paired-day bootstrap have additional independent numerical checks. Huber coefficients agree with statsmodels RLM in the verification case. The result-file script hash matches the executed script. This verifies numerical implementation for these checks, not the econometric assumptions.
