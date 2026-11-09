def entry_signal(row, cfg) -> int:
    if row is None: return 0
    if row["st_dir"] == 0 or row["st_dir"] != row["st_dir"]: return 0
    if row["adx"] < cfg["adx"]["threshold"]: return 0
    if abs(row["fade"]) >= cfg["fade"]["veto_abs_z"]: return 0
    return int(row["st_dir"])

def stop_distance(row, cfg, asset_exit: dict) -> float:
    cap = asset_exit.get("stop_atr_cap", cfg["risk"]["stop_atr_cap"])
    return cap * float(row["atr"])

def exit_decision(pos, row, asset_exit: dict):
    mode = asset_exit.get("mode", "both")
    price = float(row["close"]); st_dir = int(row["st_dir"])
    reasons = []

    if mode in ("trailing_stop", "both"):
        if pos["side"] == 1 and price <= pos["stop"]: reasons.append("stop")
        if pos["side"] == -1 and price >= pos["stop"]: reasons.append("stop")

    if mode in ("supertrend_flip", "both"):
        if st_dir != 0 and st_dir != pos["side"]: reasons.append("supertrend_flip")

    if mode == "fixed_r":
        tp = asset_exit.get("fixed_r_tp")
        if tp and pos["r"] >= tp: reasons.append("fixed_r_tp")

    if mode == "time":
        mh = asset_exit.get("max_hold_bars")
        if mh and pos["bars_held"] >= mh: reasons.append("time")

    return (reasons[0] if reasons else None), reasons