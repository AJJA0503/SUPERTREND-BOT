import asyncio, logging, yaml, signal
from pathlib import Path
from .settings import settings
from .exchanges.binance_adapter import BinanceAdapter
from .exchanges.gateio_adapter import GateioAdapter
from .engine import Engine
from .telegram_bot import TelegramController
from .web_dashboard.app import run_web

def load_cfg(name):
    p = Path(settings.CONFIG_DIR) / name
    if not p.exists():
        raise FileNotFoundError(f"config not found: {p}")
    return yaml.safe_load(p.read_text())

async def main():
    logging.basicConfig(level=settings.LOG_LEVEL,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    strat = load_cfg("strategy.yaml")
    for k in ("supertrend","atr","adx","fade","risk","fees","timeframe"):
        assert k in strat, f"strategy.yaml missing '{k}'"

    engines = {}
    bcfg = load_cfg("binance.yaml")
    if bcfg.get("enabled", True):
        engines["binance"] = Engine(BinanceAdapter(), bcfg, strat)
    gcfg = load_cfg("gateio.yaml")
    if gcfg.get("enabled", True):
        engines["gateio"] = Engine(GateioAdapter(), gcfg, strat)

    for e in engines.values():
        await e.bootstrap()

    tg = TelegramController(engines)
    await tg.start()

    web_task = asyncio.create_task(run_web(engines))

    async def loop():
        while True:
            for e in engines.values():
                try:
                    await e.tick()
                except Exception as ex:
                    logging.exception(f"engine {e.adapter.name}: {ex}")
            await asyncio.sleep(60)
    trade_task = asyncio.create_task(loop())

    stop = asyncio.Event()
    loop_ = asyncio.get_running_loop()
    for s in (signal.SIGTERM, signal.SIGINT):
        loop_.add_signal_handler(s, stop.set)
    await stop.wait()

    trade_task.cancel()
    web_task.cancel()
    for e in engines.values():
        await e._flatten_all("shutdown")
        try:
            await e.adapter.close()
        except Exception:
            pass
    await tg.stop()

if __name__ == "__main__":
    asyncio.run(main())