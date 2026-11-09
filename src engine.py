import asyncio, logging
from datetime import datetime, timezone
from .indicators import enrich
from .strategy import entry_signal, stop_distance, exit_decision
from .risk import position_size, validate_leverage
from .portfolio import Portfolio, OpenPosition
from .reporting import append_trade
from .state_manager import is_halted, set_runtime
from .utils import new_trade_id

log = logging.getLogger("engine")

class Engine:
    def __init__(self, adapter, exchange_cfg, strategy_cfg):
        self.adapter = adapter
        self.cfg = exchange_cfg
        self.scfg = strategy_cfg
        self.pf = Portfolio(exchange=adapter.name)
        for sym, a in exchange_cfg["assets"].items():
            if a.get("enabled", True):
                validate_leverage(int(a["leverage"]))
                self.pf.capital[sym] = float(a["capital_usd"])
        self.ready = False
        self._last_bar: dict[str, object] = {}

    async def bootstrap(self):
        await self.adapter.connect()
        for sym, a in self.cfg["assets"].items():
            if a.get("enabled", True):
                try:
                    await self.adapter.set_leverage(sym, int(a["leverage"]))
                except Exception as e:
                    log.warning(f"[{self.adapter.name}] set_leverage {sym}={a['leverage']} failed: {e}")
        self.ready = True
        log.info(f"[{self.adapter.name}] connected, assets={list(self.pf.capital)}")

    async def tick(self):
        if not self.ready: return
        if is_halted():
            await self._flatten_all("halt")
            return

        for sym, a in self.cfg["assets"].items():
            if not a.get("enabled", True):
                continue
            try:
                await self._tick_symbol(sym, a)
            except Exception as e:
                log.exception(f"[{self.adapter.name}] {sym} tick error: {e}")

        set_runtime(**{f"{self.adapter.name}_equity": self.pf.equity()})

    async def _tick_symbol(self, sym, asset_cfg):
        df = await self.adapter.fetch_ohlcv(sym, self.scfg["timeframe"], 500)
        if df.empty:
            return

        bar_ts = df.index[-1]
        if self._last_bar.get(sym) == bar_ts:
            return
        self._last_bar[sym] = bar_ts

        df = enrich(df, self.scfg)
        row = df.iloc[-1]
        price = float(row["close"])

        # --- manage open position ---
        pos = self.pf.positions.get(sym)
        if pos:
            pos.bars_held += 1
            if asset_cfg["exit"].get("mode", "both") in ("trailing_stop", "both"):
                st = float(row["st"])
                if st == st:  # not NaN
                    if pos.side == 1:  pos.stop = max(pos.stop, st)
                    else:              pos.stop = min(pos.stop, st)

            pos_dict = {"side": pos.side, "entry": pos.entry_price,
                        "stop": pos.stop, "r": pos.r_now(price),
                        "bars_held": pos.bars_held}
            reason, _ = exit_decision(pos_dict, row, asset_cfg["exit"])
            if reason:
                await self._close(sym, price, reason)
                # If the trend flipped, do NOT return. Let it fall through 
                # and immediately open the opposite trade.
                if reason != "supertrend_flip":
                    return

        # --- new entry ---
        if sym in self.pf.positions: return
        sig = entry_signal(row, self.scfg)
        if sig == 0: return

        lev = int(asset_cfg["leverage"])
        cap = self.pf.capital.get(sym, 0)
        sd  = stop_distance(row, self.scfg, asset_cfg["exit"])
        if sd <= 0: return
        qty = position_size(cap, lev, price, sd, self.scfg["risk"]["risk_per_trade"])
        if qty <= 0: return

        side_str = "buy" if sig == 1 else "sell"
        tid = new_trade_id(self.adapter.name)
        try:
            await self.adapter.market_order(sym, side_str, qty, client_id=tid)
        except Exception as e:
            log.error(f"[{self.adapter.name}] order failed {sym}: {e}")
            return
        stop = price - sig * sd
        self.pf.open(OpenPosition(
            trade_id=tid, exchange=self.adapter.name, symbol=sym, side=sig,
            entry_price=price, qty=qty, leverage=lev, stop=stop,
            initial_stop=stop, risk_usd=qty * sd, entry_time=datetime.now(timezone.utc),
        ))
        log.info(f"[{self.adapter.name}] OPEN {sym} side={sig} qty={qty} @ {price} stop={stop}")

    async def _close(self, sym, price, reason):
        pos = self.pf.positions.get(sym)
        if not pos: return
        side_str = "sell" if pos.side == 1 else "buy"
        try:
            await self.adapter.market_order(sym, side_str, pos.qty, reduce_only=True)
        except Exception as e:
            log.error(f"[{self.adapter.name}] close order failed {sym}: {e}")
            return
        gross = (price - pos.entry_price) * pos.side * pos.qty
        fee = (pos.entry_price + price) * pos.qty * self.scfg["fees"]["taker_bps"] / 10_000
        pnl = gross - fee - pos.funding_usd
        cap_before = self.pf.capital[sym]
        self.pf.close(sym, pnl)
        cap_after = self.pf.capital[sym]
        r = pnl / pos.risk_usd if pos.risk_usd else 0
        append_trade({
            "trade_id": pos.trade_id, "exchange": self.adapter.name,
            "symbol": sym, "side": pos.side, "leverage": pos.leverage,
            "entry_time": pos.entry_time.isoformat(),
            "exit_time": datetime.now(timezone.utc).isoformat(),
            "hold_hours": (datetime.now(timezone.utc) - pos.entry_time).total_seconds() / 3600,
            "entry_price": pos.entry_price, "exit_price": price, "qty": pos.qty,
            "notional_usd": pos.entry_price * pos.qty,
            "stop_price": pos.stop, "initial_stop": pos.initial_stop,
            "risk_usd": pos.risk_usd, "fees_usd": fee, "funding_usd": pos.funding_usd,
            "pnl_usd": pnl, "pnl_pct": pnl / cap_before if cap_before else 0,
            "r_multiple": r, "exit_reason": reason,
            "capital_before": cap_before, "capital_after": cap_after,
            "equity_after": self.pf.equity(),
        })
        log.info(f"[{self.adapter.name}] CLOSE {sym} reason={reason} pnl={pnl:.2f} r={r:.2f}")

    async def _flatten_all(self, reason):
        for sym in list(self.pf.positions.keys()):
            try:
                price = await self.adapter.ticker_price(sym)
                await self._close(sym, price, reason)
            except Exception as e:
                log.exception(f"flatten {sym} failed: {e}")