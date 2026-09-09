"""Reproducible estimator/inference experiments, not a production estimator.

Run with .venv/bin/python statistical_experiments.py --reps 500 --bootstrap 399
Inputs x,y are log-return/log-IV-change divided by a common 0.001 scale.
All coverage targets and DGP parameters are explicitly recorded below.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
import scipy
from scipy.stats import norm, t
import statsmodels.api as sm
import statsmodels

ROOT = Path(__file__).resolve().parent
BETA = -2.0
BARS = 78


def fit(x, y, w=None):
    if w is None:
        w = np.ones_like(x)
    sw = w.sum()
    xm, ym = w @ x / sw, w @ y / sw
    b = (w * (x - xm)) @ (y - ym) / (w @ ((x - xm)**2))
    return np.array([ym - b * xm, b])


def huber(x, y):
    coef = fit(x, y)
    for iteration in range(100):
        e = y - coef[0] - coef[1] * x
        scale = max(np.median(np.abs(e)) / norm.ppf(.75), 1e-10)
        w = np.minimum(1.0, 1.345 * scale / np.maximum(np.abs(e), 1e-12))
        new = fit(x, y, w)
        if np.max(np.abs(new - coef)) < 1e-8:
            return new, True
        coef = new
    return coef, False


def covariances(x, y, coef, days, w=None):
    n = len(x)
    X = np.column_stack([np.ones(n), x])
    w = np.ones(n) if w is None else w
    e = y - X @ coef
    bread = np.linalg.inv(X.T @ (w[:, None] * X))
    score = w[:, None] * X * e[:, None]
    h = w * np.sum((X @ bread) * X, axis=1)
    hc3score = score / (1 - h[:, None])
    out = {'iid': (w @ e**2) / (n - 2) * bread,
           'HC3': bread @ (hc3score.T @ hc3score) @ bread}
    meat = score.T @ score
    # Row spacing is regular in these synthetic experiments only.
    for lag in range(1, 13):
        cross = score[lag:].T @ score[:-lag]
        meat = meat + (1 - lag / 13) * (cross + cross.T)
    out['HAC12'] = bread @ meat @ bread * n / (n - 2)
    gs = score.reshape(days, BARS, 2).sum(axis=1)
    correction = days / (days - 1) * (n - 1) / (n - 2)
    out['day_CR1'] = bread @ (gs.T @ gs) @ bread * correction
    for lags in [3, 5]:
        meat = gs.T @ gs
        for lag in range(1, min(lags, days - 1) + 1):
            cross = gs[lag:].T @ gs[:-lag]
            meat = meat + (1 - lag / (lags + 1)) * (cross + cross.T)
        out['day_HAC' + str(lags)] = bread @ meat @ bread * correction
    return out


def bootstrap_ci(x, y, days, rng, count, block):
    # Exact OLS on re-sampled paired days via sufficient statistics.
    xx, yy = x.reshape(days, BARS), y.reshape(days, BARS)
    stat = np.column_stack([xx.sum(1), yy.sum(1), (xx**2).sum(1), (xx*yy).sum(1)])
    starts = rng.integers(0, days, (count, int(np.ceil(days/block))))
    idx = ((starts[:, :, None] + np.arange(block)) % days).reshape(count, -1)[:, :days]
    sums = stat[idx].sum(axis=1)
    n = days * BARS
    b = (sums[:, 3] - sums[:, 0]*sums[:, 1]/n) / (sums[:, 2] - sums[:, 0]**2/n)
    return np.quantile(b, [.025, .975])


def ar1(rng, n, rho):
    z = rng.normal(size=n + 200)
    out = np.empty_like(z)
    out[0] = z[0]
    for i in range(1, len(z)):
        out[i] = rho*out[i-1] + np.sqrt(1-rho*rho)*z[i]
    return out[200:]


def generate(name, days, rng):
    n = days * BARS
    x = rng.normal(size=n)
    e = rng.normal(size=n)
    sd = np.ones(n)
    beta = np.full(n, BETA)
    target = BETA
    observed_target = target
    if name == 'heteroskedastic':
        sd = .4 + 1.6*np.abs(x)
    elif name == 'within_day_dependence':
        x = np.concatenate([ar1(rng, BARS, .7) for _ in range(days)])
        e = np.concatenate([ar1(rng, BARS, .8) for _ in range(days)])
    elif name == 'persistent_daily_beta':
        beta = BETA + np.repeat(.7*ar1(rng, days, .85), BARS)
    elif name == 'liquidity_changes_beta':
        state = rng.random(n) < .2
        beta = np.where(state, -5., -1.)
        sd = np.where(state, 3., 1.)
        target = observed_target = -1.8
    elif name == 'real_tail_response':
        beta = BETA - 1.5*(np.abs(x) > 2.)
        target = observed_target = BETA - 1.5*2*(2*norm.pdf(2) + norm.sf(2))
    elif name == 'heavy_tails':
        e = rng.standard_t(3, n)/np.sqrt(3)
    y = beta*x + sd*e
    if name == 'bad_option_prints':
        mask = rng.random(n) < .01
        y = y + mask*rng.normal(0, 20, n)
    if name in ['classical_x_error', 'shared_x_iv_error']:
        eta = .5*rng.normal(size=n)
        x = x + eta
        if name == 'shared_x_iv_error':
            y = y - 3*eta
            observed_target = (BETA - 3*.25)/1.25
        else:
            observed_target = BETA/1.25
    if name == 'persistent_daily_beta':
        observed_target = target
    return x, y, 1/sd**2, target, observed_target


def validate():
    rng = np.random.default_rng(7291)
    x, y, w, _, _ = generate('heteroskedastic', 8, rng)
    X = sm.add_constant(x)
    maxerr = 0.
    for wt in [None, w]:
        ours = fit(x, y, wt)
        reference = (sm.OLS(y, X) if wt is None else sm.WLS(y, X, weights=wt)).fit()
        np.testing.assert_allclose(ours, reference.params, rtol=1e-9, atol=1e-10)
        cov = covariances(x, y, ours, 8, wt)
        refs = {'iid': reference.cov_params(),
                'HC3': reference.get_robustcov_results(cov_type='HC3').cov_params(),
                'HAC12': reference.get_robustcov_results(cov_type='HAC', maxlags=12, use_correction=True).cov_params(),
                'day_CR1': reference.get_robustcov_results(cov_type='cluster', groups=np.repeat(np.arange(8), BARS), use_correction=True).cov_params()}
        for key in refs:
            np.testing.assert_allclose(cov[key], refs[key], rtol=1e-9, atol=1e-10)
            maxerr = max(maxerr, float(np.max(np.abs(cov[key]-refs[key]))))
    ours, converged = huber(x, y)
    reference = sm.RLM(y, X, M=sm.robust.norms.HuberT(1.345)).fit(maxiter=200, tol=1e-10)
    np.testing.assert_allclose(ours, reference.params, rtol=1e-5, atol=1e-6)
    assert converged
    return {'OLS_WLS_covariance_max_abs_error': maxerr, 'Huber_max_abs_error': float(np.max(np.abs(ours-reference.params)))}


def coverage_experiments(reps, boot):
    scenarios = [(name, 20) for name in ['iid', 'heteroskedastic', 'within_day_dependence',
                 'persistent_daily_beta', 'classical_x_error', 'shared_x_iv_error',
                 'bad_option_prints', 'real_tail_response', 'liquidity_changes_beta', 'heavy_tails']]
    scenarios += [('within_day_dependence', 5), ('persistent_daily_beta', 60)]
    results = []
    for si, (name, days) in enumerate(scenarios):
        records = {}
        for rep in range(reps):
            rng = np.random.default_rng(np.random.SeedSequence([20260909, si, rep]))
            x, y, w, target, observed_target = generate(name, days, rng)
            # Same held-out observations for every coefficient method.
            xt, yt, _, _, _ = generate(name, 10, rng)
            if name == 'bad_option_prints':
                xt, yt, _, _, _ = generate('iid', 10, rng)  # true economic marks
            for estimator in ['OLS', 'WLS_oracle', 'Huber']:
                coef, converged = (huber(x, y) if estimator == 'Huber' else (fit(x, y, w if estimator == 'WLS_oracle' else None), True))
                intervals = {}
                if estimator != 'Huber':
                    cov = covariances(x, y, coef, days, w if estimator == 'WLS_oracle' else None)
                    for covtype, matrix in cov.items():
                        critical = t.ppf(.975, days-1 if covtype.startswith('day') else len(x)-2)
                        half = critical*np.sqrt(max(matrix[1,1], 0))
                        intervals[covtype] = (coef[1]-half, coef[1]+half)
                else:
                    intervals['point_only'] = None
                if estimator == 'OLS':
                    for block in [1,3,5]:
                        intervals['day_boot_L'+str(block)] = bootstrap_ci(x,y,days,rng,boot,block)
                loss = np.mean((yt-coef[1]*xt)**2)
                unhedged = np.mean(yt**2)
                for inference, interval in intervals.items():
                    key = estimator + '/' + inference
                    row = [coef[1], loss, unhedged, float(converged)]
                    row += [np.nan, np.nan, np.nan] if interval is None else [float(interval[0]<=target<=interval[1]), interval[1]-interval[0], float(interval[0]<=observed_target<=interval[1])]
                    records.setdefault(key, []).append(row)
        for method, rows in records.items():
            a = np.asarray(rows)
            valid = np.isfinite(a[:,4])
            p = float(a[valid,4].mean()) if valid.any() else None
            results.append({'scenario':name,'days':days,'method':method,'target':target,
                'observed_projection_target':observed_target,'mean_beta':float(a[:,0].mean()),
                'bias_to_declared_target':float(a[:,0].mean()-target),
                'rmse_to_declared_target':float(np.sqrt(np.mean((a[:,0]-target)**2))),
                'coverage':p,'coverage_mcse':None if p is None else float(np.sqrt(p*(1-p)/reps)),
                'mean_CI_width':float(a[valid,5].mean()) if valid.any() else None,
                'coverage_observed_projection':float(a[valid,6].mean()) if valid.any() else None,
                'heldout_mse':float(a[:,1].mean()),'heldout_unhedged_mse':float(a[:,2].mean()),
                'convergence_fraction':float(a[:,3].mean())})
        print('completed', name, days, flush=True)
    return results


def rolling_experiment(reps):
    out = []
    for scenario in ['stable_with_bad_quotes', 'unanticipated_regime_flip']:
        records = []
        for rep in range(reps):
            rng = np.random.default_rng(np.random.SeedSequence([674213, rep, 0 if scenario.startswith('stable') else 1]))
            days = 100
            x = rng.normal(size=(days,BARS))
            truebeta = np.full(days, -2.)
            if scenario == 'unanticipated_regime_flip':
                truebeta[70:] = 1.5
            economic_y = truebeta[:,None]*x + rng.normal(size=x.shape)
            observed_y = economic_y.copy()
            bad = rng.random(x.shape)<.01
            observed_y += bad*rng.normal(0,20,x.shape)
            predictions = {}
            for estimator in ['OLS','Huber']:
                for window in [10,20]:
                    coef = np.zeros(days)
                    for day in range(20,days):
                        xx=x[day-window:day].ravel(); yy=observed_y[day-window:day].ravel()
                        coef[day] = huber(xx,yy)[0][1] if estimator=='Huber' else fit(xx,yy)[1]
                    for shrink in [.5,1.]:
                        predictions[f'{estimator}_w{window}_shrink{shrink}'] = shrink*coef
            predictions['zero'] = np.zeros(days)
            metric = {}
            for label,b in predictions.items():
                residual = economic_y-b[:,None]*x
                # Normalized dollars: initial V_pt*sigma_pt=100,000; returns=x*0.001.
                # First-order option residual = 100*y dollars; hedge = -100,000*b.
                # Synthetic one-way transaction cost = 1 bp of notional change.
                turnover = np.abs(np.diff(b,prepend=0))
                cost = 10.*turnover
                daily_sse = (100*residual)**2
                val_loss = daily_sse[40:60].mean()+1000*cost[40:60].mean()
                metric[label] = (val_loss,float(daily_sse[60:].mean()),float(cost[60:].mean()),float(turnover[60:].mean()),float(residual[60:].mean()*100-cost[60:].mean()/BARS))
            selected = min(metric,key=lambda k: metric[k][0])
            for label in ['selected','OLS_w20_shrink1.0','Huber_w20_shrink1.0','zero']:
                actual=selected if label=='selected' else label
                _,mse,cost,turnover,netmean=metric[actual]
                records.append({'method':label,'selected':actual,'hedge_mse_dollars2':mse,'cost_dollars_per_day':cost,'turnover_beta_per_day':turnover,'net_mean_dollars_per_bar':netmean,'utility_loss':mse+1000*cost})
        for label in ['selected','OLS_w20_shrink1.0','Huber_w20_shrink1.0','zero']:
            rows=[r for r in records if r['method']==label]
            entry={'scenario':scenario,'method':label,'reps':reps}
            for field in ['hedge_mse_dollars2','cost_dollars_per_day','turnover_beta_per_day','net_mean_dollars_per_bar','utility_loss']:
                arr=np.array([r[field] for r in rows]);entry[field]=float(arr.mean());entry[field+'_mcse']=float(arr.std(ddof=1)/np.sqrt(reps))
            counts={}
            for r in rows: counts[r['selected']]=counts.get(r['selected'],0)+1
            entry['selection_counts']=counts
            out.append(entry)
        print('completed rolling',scenario,flush=True)
    return out


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--reps',type=int,default=500);parser.add_argument('--bootstrap',type=int,default=399);parser.add_argument('--rolling-reps',type=int,default=100);parser.add_argument('--validate-only',action='store_true');args=parser.parse_args()
    validation=validate();print('independent implementation checks',validation,flush=True)
    if args.validate_only: return
    data={'metadata':{'seed':20260909,'reps':args.reps,'bootstrap':args.bootstrap,'rolling_reps':args.rolling_reps,'bars_per_day':BARS,'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'statsmodels':statsmodels.__version__,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},'implementation_checks':validation}
    data['coverage']=coverage_experiments(args.reps,args.bootstrap)
    (ROOT/'statistical-results.json').write_text(json.dumps(data,indent=2)+'\n')
    data['rolling']=rolling_experiment(args.rolling_reps)
    (ROOT/'statistical-results.json').write_text(json.dumps(data,indent=2)+'\n')
    print('wrote statistical-results.json',flush=True)


if __name__=='__main__': main()
