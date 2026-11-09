from dataclasses import dataclass, field, asdict
from datetime import datetime

@dataclass
class OpenPosition:
    trade_id: str
    exchange: str
    symbol: str
    side: int
    entry_price: float
    qty: float
    leverage: int
    stop: float
    initial_stop: float
    risk_usd: float
    entry_time: datetime
    bars_held: int = 0
    funding_usd: float = 0.0
    fees_entry: float = 0.0

    def r_now(self, price: float) -> float:
        if self.risk_usd <= 0: return 0.0
        pnl = (price - self.entry_price) * self.side * self.qty
        return pnl / self.risk_usd

    def to_dict(self) -> dict:
        d = asdict(self); d["entry_time"] = self.entry_time.isoformat()
        return d

@dataclass
class Portfolio:
    exchange: str
    capital: dict[str, float] = field(default_factory=dict)
    positions: dict[str, OpenPosition] = field(default_factory=dict)
    realized_pnl: float = 0.0

    def equity(self) -> float:
        return sum(self.capital.values())

    def open(self, pos: OpenPosition) -> None:
        self.positions[pos.symbol] = pos

    def close(self, symbol: str, pnl: float) -> OpenPosition:
        pos = self.positions.pop(symbol)
        self.capital[symbol] = self.capital.get(symbol, 0) + pnl
        self.realized_pnl += pnl
        return pos