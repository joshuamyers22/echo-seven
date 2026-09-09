"""Pure unit conversion for a proposed additional underlying hedge."""

import math


def additional_hedge_dollars(
    *,
    signed_vega_dollars_per_point: float,
    current_iv_decimal: float,
    beta_relative: float,
) -> float:
    """Return hedge notional; positive means buy underlying exposure.

    This is a conversion, not authorization to hedge or evidence of optimality.
    The caller supplies a compatible contract/expiry and current valid inputs.
    """
    if (
        not all(
            math.isfinite(value)
            for value in (
                signed_vega_dollars_per_point,
                current_iv_decimal,
                beta_relative,
            )
        )
        or current_iv_decimal <= 0
    ):
        raise ValueError("hedge inputs must be finite with positive decimal IV")
    result = -signed_vega_dollars_per_point * (100 * current_iv_decimal) * beta_relative
    if not math.isfinite(result):
        raise ValueError("hedge conversion overflow")
    return result
