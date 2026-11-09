import csv, os
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
from .settings import settings
from .utils import atomic_write
from .metrics import summarize

TRADE_HEADER = [
    "trade_id","exchange","symbol","side","leverage",
    "entry_time","exit_time","hold_hours",
    "entry_price","exit_price","qty","notional_usd",
    "stop_price","initial_stop","risk_usd","fees_usd","funding_usd",
    "pnl_usd","pnl_pct","r_multiple","exit_reason",
    "capital_before","capital_after","equity_after",
]

def _trade_csv(exchange: str) -> Path:
    p = Path(settings.DATA_DIR) / "csv" / f"{exchange}_trades.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        atomic_write(p, ",".join(TRADE_HEADER) + "\n")
    return p

def append_trade(trade: dict) -> None:
    p = _trade_csv(trade["exchange"])
    with p.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TRADE_HEADER, extrasaction="ignore")
        w.writerow(trade)

def load_trades(exchange: str) -> pd.DataFrame:
    p = _trade_csv(exchange)
    return pd.read_csv(p) if p.stat().st_size > 0 else pd.DataFrame(columns=TRADE_HEADER)

def summary_report(exchange: str, freq: str) -> pd.DataFrame:
    df = load_trades(exchange)
    if df.empty:
        return pd.DataFrame()
    df["exit_time"] = pd.to_datetime(df["exit_time"], utc=True)
    out = []
    for period, g in df.groupby(pd.Grouper(key="exit_time", freq=freq)):
        s = summarize(g)
        s["period"] = period.isoformat() if period is not pd.NaT else ""
        s["exchange"] = exchange
        out.append(s)
    rep = pd.DataFrame(out)
    p = Path(settings.DATA_DIR) / "csv" / f"{exchange}_summary_{freq}.csv"
    rep.to_csv(p, index=False)
    return rep

def all_reports(exchange: str) -> dict[str, pd.DataFrame]:
    return {f: summary_report(exchange, f) for f in ("D","W","M","Y")}