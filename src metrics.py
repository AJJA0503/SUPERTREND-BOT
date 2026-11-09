import numpy as np, pandas as pd

BARS_PER_YEAR_15M = 4 * 24 * 365

def win_rate(r: np.ndarray) -> float:
    return float((r > 0).mean()) if len(r) else 0.0

def profit_factor(r: np.ndarray) -> float:
    wins = r[r > 0].sum(); losses = -r[r < 0].sum()
    if losses == 0: return float("inf") if wins > 0 else 0.0
    return float(wins / losses)

def sharpe(daily_pnl: np.ndarray, rf: float = 0.0) -> float:
    if len(daily_pnl) < 2 or daily_pnl.std() == 0: return 0.0
    excess = daily_pnl - rf
    return float(np.sqrt(252) * excess.mean() / excess.std())

def sortino(daily_pnl: np.ndarray) -> float:
    downside = daily_pnl[daily_pnl < 0]
    if len(downside) == 0 or downside.std() == 0: return 0.0
    return float(np.sqrt(252) * daily_pnl.mean() / downside.std())

def max_drawdown(equity: np.ndarray) -> float:
    if len(equity) < 2: return 0.0
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return float(dd.min())

def summarize(trades_df: pd.DataFrame) -> dict:
    if trades_df.empty:
        return {k: 0 for k in ["trades","win_rate","profit_factor","sharpe","sortino",
                               "avg_r","expectancy_r","max_dd","total_pnl","avg_hold_h"]}
    r = trades_df["r_multiple"].to_numpy()
    trades_df = trades_df.copy()
    trades_df["entry_time"] = pd.to_datetime(trades_df["entry_time"], utc=True)
    trades_df["exit_time"]  = pd.to_datetime(trades_df["exit_time"],  utc=True)
    daily = trades_df.set_index("exit_time").resample("1D")["pnl_usd"].sum().fillna(0)
    equity = daily.cumsum().to_numpy()
    hold_h = ((trades_df["exit_time"] - trades_df["entry_time"]).dt.total_seconds() / 3600)
    return {
        "trades": len(trades_df),
        "win_rate": win_rate(r),
        "profit_factor": profit_factor(r),
        "sharpe": sharpe(daily.to_numpy()),
        "sortino": sortino(daily.to_numpy()),
        "avg_r": float(r.mean()),
        "expectancy_r": float(r.mean()),
        "max_dd": max_drawdown(equity),
        "total_pnl": float(trades_df["pnl_usd"].sum()),
        "avg_hold_h": float(hold_h.mean()),
    }