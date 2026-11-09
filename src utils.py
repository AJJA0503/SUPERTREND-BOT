import time, uuid
from datetime import datetime, timezone

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def iso(ts) -> str:
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts/1000, tz=timezone.utc).isoformat()
    return ts.astimezone(timezone.utc).isoformat()

def new_trade_id(prefix: str) -> str:
    return f"{prefix}-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"