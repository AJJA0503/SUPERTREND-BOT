import numpy as np, pandas as pd
from src.indicators import enrich, atr, supertrend, adx

def synth(n=300):
    rng = np.random.default_rng(1)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.004, n)))
    high = close * (1 + np.abs(rng.normal(0, 0.002, n)))
    low  = close * (1 - np.abs(rng.normal(0, 0.002, n)))
    open_ = np.roll(close, 1); open_[0] = close[0]
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({"open":open_,"high":high,"low":low,"close":close,
                         "volume":np.ones(n)}, index=idx)

def test_enrich_has_columns():
    cfg = {"supertrend":{"period":10,"multiplier":3.0},"atr":{"period":14},
           "adx":{"period":14,"threshold":20.0},"fade":{"lookback":50,"veto_abs_z":2.0},
           "risk":{"stop_atr_cap":1.5,"risk_per_trade":0.01},"fees":{"taker_bps":4},
           "timeframe":"15m"}
    out = enrich(synth(), cfg)
    for c in ("atr","st","st_dir","adx","fade"):
        assert c in out.columns

def test_atr_positive():
    df = synth()
    assert (atr(df, 14).dropna() > 0).all()

def test_supertrend_direction():
    df = synth()
    _, d = supertrend(df, 10, 3.0)
    assert set(d.unique()) <= {-1, 1}

def test_adx_range():
    df = synth()
    v = adx(df, 14).dropna()
    assert (v >= 0).all() and (v <= 100).all()