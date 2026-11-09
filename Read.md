# Futures Trend Bot

Multi-exchange perpetual futures bot (Binance + Gate.io) running Supertrend +
ADX + trend-fade strategy on 15m candles. Full Telegram control and web dashboard.

## Quick start

    python3.11 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env  # fill in API keys, telegram token, web token
    # edit config/*.yaml
    ./run.sh

## Layout

- src/          — Python modules
- config/       — YAML per exchange + strategy + web
- state/        — HALTED flag, runtime.json
- data/csv/     — per-exchange trade CSVs + summaries
- data/logs/    — rotating logs

## Kill / Run

    Telegram:  /kill    /run
    Web:       click KILL / RUN buttons
    Shell:     touch state/HALTED    rm state/HALTED

## Reports

Per exchange, per period:

    data/csv/binance_trades.csv
    data/csv/gateio_trades.csv
    data/csv/binance_summary_D.csv
    data/csv/binance_summary_W.csv
    data/csv/binance_summary_M.csv
    data/csv/binance_summary_Y.csv
    (same for gateio)

## Web dashboard

    http://<vps>:8080/?token=WEB_AUTH_TOKEN

## Safety

- Leverage enforced 1-40
- Stop capped at 1.5 x ATR
- Kill switch checked every tick
- Testnet flags in .env