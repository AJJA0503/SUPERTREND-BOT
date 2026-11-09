# Futures Trend Bot

Multi-exchange perpetual futures bot (Binance + Gate.io) running Supertrend + ADX + trend-fade on 15m candles.
Full Telegram control and web dashboard.

## Windows quick start

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    Copy-Item .env.example .env
    python -m src.main

## Linux quick start

    python3.11 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    ./run.sh
