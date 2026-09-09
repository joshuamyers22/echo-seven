"""Numerical counterexamples for the design review; no market-data claims.

Run: python3 check_counterexamples.py
European Black prices, discount factor 1, decimal IV, forward as underlying.
"""
import json
import math
from pathlib import Path


def normal(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def price(forward, strike, sigma, tau, call=True):
    d1 = (math.log(forward / strike) + 0.5 * sigma**2 * tau) / (sigma * math.sqrt(tau))
    d2 = d1 - sigma * math.sqrt(tau)
    if call:
        return forward * normal(d1) - strike * normal(d2)
    return strike * normal(-d2) - forward * normal(-d1)


def iv(premium, forward, strike, tau, call=True):
    lo, hi = 1e-8, 5.0
    assert price(forward, strike, lo, tau, call) <= premium <= price(forward, strike, hi, tau, call)
    for _ in range(100):
        mid = (lo + hi) / 2
        if price(forward, strike, mid, tau, call) < premium:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


results = {}
forward, strike, sigma, tau = 100.0, 90.0, 0.30, 0.25
d1 = (math.log(forward / strike) + 0.5 * sigma**2 * tau) / (sigma * math.sqrt(tau))
phi = math.exp(-0.5 * d1**2) / math.sqrt(2 * math.pi)
eps = 0.001
call_shift = -eps * normal(d1) / (phi * math.sqrt(tau))
put_shift = eps * normal(-d1) / (phi * math.sqrt(tau))
call_iv = iv(price(forward, strike, sigma, tau), forward * (1 + eps), strike, tau)
put_iv = iv(price(forward, strike, sigma, tau, False), forward * (1 + eps), strike, tau, False)
avg_first = (call_shift + put_shift) / 2
avg_actual = (call_iv + put_iv) / 2 - sigma
assert abs(avg_first) > 0.001
assert abs(avg_actual - avg_first) < 0.0001
call_weight = normal(-d1)
weighted_first = call_weight * call_shift + (1 - call_weight) * put_shift
assert abs(weighted_first) < 1e-14
results['call_put_average'] = {
    'inputs': {'forward': forward, 'strike': strike, 'sigma_decimal': sigma, 'tau': tau, 'forward_error': eps},
    'equal_average_first_order_error_vol_points': 100 * avg_first,
    'equal_average_repriced_error_vol_points': 100 * avg_actual,
    'cancellation_call_weight': call_weight,
    'weighted_first_order_error': weighted_first,
}

old_f, new_f, strike, sigma, tau = 100.0, 101.0, 100.0, .30, .25
old_call = price(old_f, strike, sigma, tau)
new_call = price(new_f, strike, sigma, tau)
stale_option_iv = iv(old_call, new_f, strike, tau)
stale_underlying_iv = iv(new_call, old_f, strike, tau)
assert stale_option_iv < sigma < stale_underlying_iv
results['timestamp_direction'] = {
    'true_iv_vol_points': 100 * sigma,
    'stale_call_fresh_underlying_iv_vol_points': 100 * stale_option_iv,
    'fresh_call_stale_underlying_iv_vol_points': 100 * stale_underlying_iv,
}

sigma_dec, beta_rel, vega_pt = .40, 1.0, 1000.0
b_dec_per_log = sigma_dec * beta_rel
b_pt_per_log = 100 * b_dec_per_log
b_pt_per_one_percent = .01 * b_pt_per_log
hedge = -vega_pt * 100 * sigma_dec * beta_rel
assert b_pt_per_one_percent == .4 and hedge == -40000
results['unit_contract'] = {
    'beta_dec_per_log_return': b_dec_per_log,
    'beta_vol_points_per_log_return': b_pt_per_log,
    'beta_vol_points_per_one_percent_return': b_pt_per_one_percent,
    'extra_hedge_dollars': hedge,
    'hedge_pnl_per_one_percent_up': .01 * hedge,
}

# Fixed strike vs moving ATM: affine smiles, no sampling or fitting noise.
psi, b_fixed = -.10, -.20
atm_response = b_fixed + psi
assert math.isclose(atm_response / psi, 3.0)
results['ssr_outside_bounds'] = {'psi_decimal': psi, 'fixed_strike_beta_decimal': b_fixed, 'ssr': atm_response / psi}

# An ordinary beta survives even when the normalization denominator vanishes.
psi, b_fixed = 0.0, .10
results['flat_skew'] = {'psi_decimal': psi, 'fixed_strike_beta_decimal': b_fixed, 'ssr': None}

# Forty rows are impossible for one regular-session day at these intervals.
results['bar_counts_before_endpoint_and_open_filters'] = {str(minutes): 390 // minutes for minutes in [1, 2, 5, 15, 30]}
assert results['bar_counts_before_endpoint_and_open_filters']['15'] < 40

out = Path(__file__).with_name('counterexample-results.json')
out.write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
