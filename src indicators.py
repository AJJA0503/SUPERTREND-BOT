import numpy as np, pandas as pd

def true_range(df):
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    return pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)

def atr(df, period):
    return true_range(df).ewm(alpha=1/period, adjust=False).mean()

def supertrend(df, period, mult):
    hl2 = (df["high"] + df["low"]) / 2
    a = atr(df, period)
    upper = (hl2 + mult * a).values
    lower = (hl2 - mult * a).values
    close = df["close"].values
    n = len(df)
    st = np.full(n, np.nan); direction = np.ones(n, dtype=int)
    for i in range(1, n):
        if lower[i] < lower[i-1] and close[i-1] > lower[i-1]:
            lower[i] = lower[i-1]
        if upper[i] > upper[i-1] and close[i-1] < upper[i-1]:
            upper[i] = upper[i-1]
        if np.isnan(st[i-1]):
            st[i] = upper[i]; direction[i] = -1
        elif st[i-1] == upper[i-1]:
            if close[i] > upper[i]:
                st[i] = lower[i]; direction[i] = 1
            else:
                st[i] = upper[i]; direction[i] = -1
        else:
            if close[i] < lower[i]:
                st[i] = upper[i]; direction[i] = -1
            else:
                st[i] = lower[i]; direction[i] = 1
    return pd.Series(st, index=df.index), pd.Series(direction, index=df.index)

def adx(df, period):
    h, l = df["high"], df["low"]
    up = h.diff(); down = -l.diff()
    plus_dm  = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = true_range(df)
    atr_ = tr.ewm(alpha=1/period, adjust=False).mean()
    pdi = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean() / atr_
    mdi = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean() / atr_
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1/period, adjust=False).mean()

def fade_score(df, lookback):
    ma = df["close"].rolling(lookback).mean()
    sd = df["close"].rolling(lookback).std()
    return ((df["close"] - ma) / sd.replace(0, np.nan)).fillna(0.0)

def enrich(df, cfg):
    out = df.copy()
    out["atr"] = atr(out, cfg["atr"]["period"])
    out["st"], out["st_dir"] = supertrend(out, cfg["supertrend"]["period"], cfg["supertrend"]["multiplier"])
    out["adx"] = adx(out, cfg["adx"]["period"])
    out["fade"] = fade_score(out, cfg["fade"]["lookback"])
    return out