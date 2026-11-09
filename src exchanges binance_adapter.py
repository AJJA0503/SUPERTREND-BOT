import ccxt.async_support as ccxt
import pandas as pd
from .base import ExchangeAdapter
from ..settings import settings

class BinanceAdapter(ExchangeAdapter):
    name = "binance"

    def __init__(self):
        self.ex = ccxt.binanceusdm({
            "apiKey": settings.BINANCE_API_KEY,
            "secret": settings.BINANCE_API_SECRET,
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
        })
        if settings.BINANCE_TESTNET:
            self.ex.set_sandbox_mode(True)

    async def connect(self):
        await self.ex.load_markets()

    async def fetch_ohlcv(self, symbol, timeframe, limit=500):
        raw = await self.ex.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(raw, columns=["ts","open","high","low","close","volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        return df.set_index("ts")

    async def set_leverage(self, symbol, leverage):
        await self.ex.set_leverage(leverage, symbol)

    async def market_order(self, symbol, side, qty, reduce_only=False, client_id=""):
        params = {"reduceOnly": reduce_only}
        if client_id: params["newClientOrderId"] = client_id
        return await self.ex.create_order(symbol, "market", side, qty, None, params)

    async def cancel_all(self, symbol):
        try: await self.ex.cancel_all_orders(symbol)
        except Exception: pass

    async def ticker_price(self, symbol):
        t = await self.ex.fetch_ticker(symbol)
        return float(t["last"])

    async def fetch_funding(self, symbol):
        try:
            fr = await self.ex.fetch_funding_rate(symbol)
            return float(fr.get("fundingRate", 0.0))
        except Exception:
            return 0.0

    async def close(self):
        await self.ex.close()