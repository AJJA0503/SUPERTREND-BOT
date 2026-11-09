import asyncio, json
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from ..settings import settings
from ..reporting import load_trades, all_reports
from ..metrics import summarize
from ..state_manager import halt, resume, is_halted

BASE = Path(__file__).parent

def build_app(engines):
    app = FastAPI()
    templates = Jinja2Templates(directory=str(BASE / "templates"))
    static_dir = BASE / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    def auth(request: Request):
        if request.headers.get("x-auth") == settings.WEB_AUTH_TOKEN: return True
        if request.query_params.get("token") == settings.WEB_AUTH_TOKEN: return True
        raise HTTPException(401, "unauthorized")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        if request.query_params.get("token") != settings.WEB_AUTH_TOKEN:
            return HTMLResponse("append ?token=YOUR_TOKEN", status_code=401)
        return templates.TemplateResponse("index.html", {"request": request, "token": settings.WEB_AUTH_TOKEN})

    @app.get("/api/state")
    async def state(request: Request):
        auth(request)
        out = {"halted": is_halted(), "engines": {}}
        for name, e in engines.items():
            positions = []
            for sym, p in e.pf.positions.items():
                try: price = await e.adapter.ticker_price(sym)
                except Exception: price = p.entry_price
                positions.append({"symbol": sym, "side": p.side, "qty": p.qty,
                                  "entry": p.entry_price, "price": price,
                                  "r": p.r_now(price), "lev": p.leverage,
                                  "stop": p.stop, "trade_id": p.trade_id})
            out["engines"][name] = {
                "equity": e.pf.equity(),
                "capital": e.pf.capital,
                "positions": positions,
            }
        return JSONResponse(out)

    @app.get("/api/metrics")
    async def metrics(request: Request):
        auth(request)
        res = {}
        for name in engines:
            df = load_trades(name)
            res[name] = summarize(df)
        return JSONResponse(res)

    @app.get("/api/trades/{exchange}")
    async def trades(exchange: str, request: Request, limit: int = 50):
        auth(request)
        df = load_trades(exchange)
        if df.empty: return []
        return df.tail(limit).to_dict(orient="records")

    @app.get("/api/reports/{exchange}")
    async def reports(exchange: str, request: Request):
        auth(request)
        return {freq: df.to_dict(orient="records") for freq, df in all_reports(exchange).items()}

    @app.post("/api/kill")
    async def kill(request: Request):
        auth(request); halt()
        for e in engines.values(): await e._flatten_all("web_kill")
        return {"ok": True}

    @app.post("/api/run")
    async def run(request: Request):
        auth(request); resume()
        return {"ok": True}

    return app

async def run_web(engines):
    import uvicorn
    app = build_app(engines)
    cfg = {"host": settings.WEB_HOST, "port": settings.WEB_PORT, "log_level": "info"}
    server = uvicorn.Server(uvicorn.Config(app, **cfg))
    await server.serve()