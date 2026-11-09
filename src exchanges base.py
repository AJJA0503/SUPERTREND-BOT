from abc import ABC, abstractmethod
import pandas as pd

class ExchangeAdapter(ABC):
    name: str

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame: ...

    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> None: ...

    @abstractmethod
    async def market_order(self, symbol: str, side: str, qty: float,
                           reduce_only: bool = False, client_id: str = "") -> dict: ...

    @abstractmethod
    async def cancel_all(self, symbol: str) -> None: ...

    @abstractmethod
    async def ticker_price(self, symbol: str) -> float: ...

    @abstractmethod
    async def fetch_funding(self, symbol: str) -> float: ...