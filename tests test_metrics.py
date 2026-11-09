import numpy as np, pandas as pd
from src.metrics import win_rate, profit_factor, max_drawdown, summarize

def test_win_rate():
    r = np.array([1, -1, 2, -1, 3])
    assert win_rate(r) == 0.6

def test_profit_factor():
    r = np.array([2, 2, -1, -1])
    assert profit_factor(r) == 4.0

def test_profit_factor_no_losses():
    assert profit_factor(np.array([1,2,3])) == float("inf")

def test_max_drawdown():
    eq = np.array([100, 120, 90, 110, 80])
    dd = max_drawdown(eq)
    assert -0.34 < dd < -0.33

def test_summarize_empty():
    s = summarize(pd.DataFrame())
    assert s["trades"] == 0