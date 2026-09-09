# calibrated-iv/v1 CSV

UTF-8 CSV with the following exact columns (order may differ), no nulls,
at most 100,000 rows and 50 MiB. Additional columns are rejected. Example:
[data/spot-vol-example.csv](../data/spot-vol-example.csv). Prices and strikes
retain decimal input precision until log-return arithmetic uses float64.

| Columns | Meaning |
|---|---|
| series_id | Stable identifier of a fixed strike/expiry/side/underlying series |
| underlying_id | Actual spot or futures contract identifier, never a rolling alias |
| strike | Positive finite decimal strike in the instrument's quote units |
| expiry_at | Exact timezone-aware expiration instant |
| option_type | Exactly `call` or `put` |
| session_id | Calendar session identifier, consistently defined across instruments |
| segment_id | Uninterrupted session segment; change after a trading halt |
| session_open, session_close | Actual calendar boundaries with explicit timezone |
| bar_at | Decision instant on the session-open anchored sampling grid |
| option_quote_at, underlying_quote_at | Source event timestamps used by the observation |
| available_at | Time the complete calibrated observation became available |
| calibration_available_at | Time every curve/parameter used in inversion became available |
| underlying_price | Positive underlying level corresponding to the IV observation |
| iv_decimal | Annualized IV, e.g. `0.20` for 20%; valid range (0, 5) |
| source_id, calibration_id | Nonblank source and inversion/calibration provenance IDs |

No feed timezone, option side encoding, price multiplier or calendar is guessed.
The adapter must reconcile timestamp clocks and select a causal quote set.
`available_at` must be at least both quote timestamps and calibration availability,
and no later than the decision bar. If inversion completes after the bar, this
observation is unavailable at that decision, even if the quote was on time.

The schema does not yet include bid/ask, trade conditions or calibration curves.
It cannot validate a vendor's IV quality, economic exercise convention, spread
filters or quote-to-IV reconstruction. Implement these in an audited adapter
before claiming market-data validity. Numerical invalid observations break the
pairing chain and are counted; invalid contract/schema structure rejects the run.
