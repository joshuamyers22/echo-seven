"""Check additional numerical paths and render tables from stored experiments."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.sandwich_covariance import cov_nw_groupsum
from statistical_experiments import bootstrap_ci, covariances, fit, generate, BARS

root = Path(__file__).resolve().parent
data = json.loads((root/'statistical-results.json').read_text())
assert data['metadata']['script_sha256'] == hashlib.sha256((root/'statistical_experiments.py').read_bytes()).hexdigest()
rng=np.random.default_rng(1142)
x,y,w,_,_=generate('heteroskedastic',20,rng)
maxerr=0.
for weights in [None,w]:
    coef=fit(x,y,weights)
    ours=covariances(x,y,coef,20,weights)
    result=(sm.OLS(y,sm.add_constant(x)) if weights is None else sm.WLS(y,sm.add_constant(x),weights=weights)).fit()
    for lag in [3,5]:
        ref=cov_nw_groupsum(result,lag,np.repeat(np.arange(20),BARS),use_correction='cluster')
        np.testing.assert_allclose(ours['day_HAC'+str(lag)],ref,rtol=1e-9,atol=1e-10)
        maxerr=max(maxerr,float(np.max(np.abs(ours['day_HAC'+str(lag)]-ref))))
for block in [1,3,5]:
    a=bootstrap_ci(x,y,20,np.random.default_rng(972),99,block)
    rng=np.random.default_rng(972)
    starts=rng.integers(0,20,(99,int(np.ceil(20/block))))
    indices=((starts[:,:,None]+np.arange(block))%20).reshape(99,-1)[:,:20]
    slopes=[fit(x.reshape(20,BARS)[i].ravel(),y.reshape(20,BARS)[i].ravel())[1] for i in indices]
    np.testing.assert_allclose(a,np.quantile(slopes,[.025,.975]),rtol=1e-10,atol=1e-10)
validation={'day_score_HAC_vs_statsmodels_max_abs_error':maxerr,'paired_day_bootstrap_vs_literal_refits':'passed for L=1,3,5','result_script_hash_match':True}
(root/'statistical-additional-validation.json').write_text(json.dumps(validation,indent=2)+'\n')

with (root/'statistical-coverage.csv').open('w') as f:
    writer=csv.DictWriter(f,fieldnames=list(data['coverage'][0]));writer.writeheader();writer.writerows(data['coverage'])

lookup={(r['scenario'],r['days'],r['method']):r for r in data['coverage']}
lines=['# Statistical simulation results','','Generated from `statistical-results.json`; synthetic experiments, not market-data validation.','','Seed: 20260909. 500 replications per scenario/window; 399 bootstrap draws per replication. 78 bars per day. All intervals nominally 95%. Coverage Monte Carlo SE near 95% is about 0.97 percentage points; see CSV for each actual value.','','## Coverage of the declared target','','| Scenario | Days | IID | HC3 | Bar HAC(12) | Day CR1 | Day HAC(3) | Day-block bootstrap(3) |','|---|---:|---:|---:|---:|---:|---:|---:|']
scenarios=list(dict.fromkeys((r['scenario'],r['days']) for r in data['coverage']))
for name,days in scenarios:
    values=[lookup[name,days,'OLS/'+m]['coverage'] for m in ['iid','HC3','HAC12','day_CR1','day_HAC3','day_boot_L3']]
    lines.append('| '+name+' | '+str(days)+' | '+' | '.join(f'{100*v:.1f}%' for v in values)+' |')
lines+=['','For measurement-error cases the declared target is the clean latent slope; observed-regression target coverage is a separate CSV field. For persistent daily beta it is the stationary population mean, not the realized window average or current state. A failing interval may be accurately centered on a different estimand.','','## Point-estimator comparison','','| Scenario (20 days) | Declared target | OLS mean / RMSE | Oracle WLS mean / RMSE | Huber mean / RMSE |','|---|---:|---:|---:|---:|']
for name,days in scenarios:
    if days!=20:continue
    rs=[lookup[name,days,m] for m in ['OLS/HC3','WLS_oracle/HC3','Huber/point_only']]
    lines.append('| '+name+f" | {rs[0]['target']:.3f} | "+' | '.join(f"{r['mean_beta']:.3f} / {r['rmse_to_declared_target']:.3f}" for r in rs)+' |')
lines+=['','WLS uses known innovation variances, not estimated production weights. Huber intervals are deliberately absent: its point estimator is assessed without pretending an OLS covariance formula applies.','','## Chronological hedge experiment','','100 independent replications per scenario; no future observations enter a hedge. All values below refer to the final 40 held-out days.','','| Scenario | Method | Hedge MSE ($²/bar) | Synthetic cost ($/day) | Mean net P&L ($/bar) |','|---|---|---:|---:|---:|']
for r in data['rolling']:
    lines.append(f"| {r['scenario']} | {r['method']} | {r['hedge_mse_dollars2']:.2f} | {r['cost_dollars_per_day']:.4f} | {r['net_mean_dollars_per_bar']:.4f} |")
lines+=['','Trading-cost assumptions and the dollar normalization are in the statistical review. These are first-order exposure experiments with constant vega-vol exposure, not full option repricing. Monte Carlo standard errors and selected-method counts are in the JSON. The selected strategy is picked on earlier validation data; the surprise regime flip occurs in the untouched test period.','','## Verification','','OLS/WLS coefficients and IID, HC3, bar-HAC and day-CR1 covariance calculations agree with statsmodels; day-score HAC and paired-day bootstrap have additional independent numerical checks. Huber coefficients agree with statsmodels RLM in the verification case. The result-file script hash matches the executed script. This verifies numerical implementation for these checks, not the econometric assumptions.','']
(root/'statistical-summary.md').write_text('\n'.join(lines))
print(json.dumps(validation,indent=2))
print('Wrote statistical-summary.md and statistical-coverage.csv')
