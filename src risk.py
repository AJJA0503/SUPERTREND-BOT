import math

def validate_leverage(lev: int) -> int:
    if not (1 <= lev <= 40):
        raise ValueError(f"leverage must be 1..40, got {lev}")
    return lev

def position_size(capital_usd: float, leverage: int, price: float,
                  stop_dist: float, risk_per_trade: float,
                  contract_mult: float = 1.0, qty_step: float = 1e-6) -> float:
    if stop_dist <= 0 or price <= 0 or capital_usd <= 0:
        return 0.0
    risk_budget = capital_usd * risk_per_trade
    qty_by_risk = risk_budget / (stop_dist * contract_mult)
    max_notional = capital_usd * leverage
    qty_by_notional = max_notional / (price * contract_mult)
    qty = min(qty_by_risk, qty_by_notional)
    return max(math.floor(qty / qty_step) * qty_step, 0.0)