import logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
from .settings import settings
from .state_manager import halt, resume, is_halted
from .reporting import load_trades, all_reports
from .metrics import summarize

log = logging.getLogger("telegram")

class TelegramController:
    def __init__(self, engines):
        self.engines = engines
        self.app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        self._wire()

    def _auth(self, update):
        return update.effective_chat.id in settings.allowed_chats

    def _wire(self):
        a = self.app
        a.add_handler(CommandHandler("start", self.cmd_help))
        a.add_handler(CommandHandler("help", self.cmd_help))
        a.add_handler(CommandHandler("status", self.cmd_status))
        a.add_handler(CommandHandler("dashboard", self.cmd_dashboard))
        a.add_handler(CommandHandler("positions", self.cmd_positions))
        a.add_handler(CommandHandler("kill", self.cmd_kill))
        a.add_handler(CommandHandler("run", self.cmd_run))
        a.add_handler(CommandHandler("report", self.cmd_report))
        a.add_handler(CommandHandler("trades", self.cmd_trades))
        a.add_handler(CommandHandler("config", self.cmd_config_show))
        a.add_handler(CommandHandler("set", self.cmd_config_set))

    async def cmd_help(self, u, c):
        if not self._auth(u): return
        await u.message.reply_text(HELP_TEXT)

    async def cmd_status(self, u, c):
        if not self._auth(u): return
        halted = is_halted()
        lines = [f"HALTED={halted}"]
        for name, e in self.engines.items():
            eq = e.pf.equity()
            lines.append(f"{name}: equity=${eq:,.2f} open={len(e.pf.positions)}")
        await u.message.reply_text("\n".join(lines))

    async def cmd_dashboard(self, u, c):
        if not self._auth(u): return
        blocks = []
        for name, e in self.engines.items():
            for sym, a in e.cfg["assets"].items():
                if not a.get("enabled", True): continue
                try:
                    price = await e.adapter.ticker_price(sym)
                except Exception:
                    blocks.append(f"{name} {sym} price-error")
                    continue
                pos = e.pf.positions.get(sym)
                if pos:
                    r = pos.r_now(price)
                    blocks.append(f"{name} {sym} {price:.4f} | {'L' if pos.side==1 else 'S'} "
                                  f"qty={pos.qty} R={r:+.2f} stop={pos.stop:.4f} lev={pos.leverage}x")
                else:
                    blocks.append(f"{name} {sym} {price:.4f} | flat")
        await u.message.reply_text("\n".join(blocks) or "no assets")

    async def cmd_positions(self, u, c):
        if not self._auth(u): return
        out = []
        for name, e in self.engines.items():
            for sym, p in e.pf.positions.items():
                try:
                    price = await e.adapter.ticker_price(sym)
                except Exception:
                    price = p.entry_price
                out.append(f"{name} {sym} {p.side*1} qty={p.qty} @ {p.entry_price:.4f} "
                           f"now {price:.4f} R={p.r_now(price):+.2f} lev={p.leverage}x tid={p.trade_id}")
        await u.message.reply_text("\n".join(out) or "no open positions")

    async def cmd_kill(self, u, c):
        if not self._auth(u): return
        halt()
        for e in self.engines.values():
            await e._flatten_all("telegram_kill")
        await u.message.reply_text("HALTED and flattened.")

    async def cmd_run(self, u, c):
        if not self._auth(u): return
        resume()
        await u.message.reply_text("RESUMED. Entries re-enabled.")

    async def cmd_report(self, u, c):
        if not self._auth(u): return
        parts = []
        for name in self.engines:
            df = load_trades(name)
            s = summarize(df)
            parts.append(f"{name}: trades={s['trades']} wr={s['win_rate']:.1%} "
                         f"PF={s['profit_factor']:.2f} sharpe={s['sharpe']:.2f} "
                         f"pnl=${s['total_pnl']:,.2f} dd={s['max_dd']:.1%}")
        await u.message.reply_text("\n".join(parts) or "no data")

    async def cmd_trades(self, u, c):
        if not self._auth(u): return
        for name in self.engines:
            df = load_trades(name)
            if df.empty: continue
            tail = df.tail(5)[["symbol","side","pnl_usd","r_multiple","exit_reason","exit_time"]]
            await u.message.reply_text(f"{name}:\n{tail.to_string(index=False)}")

    async def cmd_config_show(self, u, c):
        if not self._auth(u): return
        for name, e in self.engines.items():
            msg = [f"{name}:"]
            for sym, a in e.cfg["assets"].items():
                msg.append(f"  {sym}: on={a.get('enabled',True)} cap=${a.get('capital_usd')} "
                           f"lev={a.get('leverage')}x exit={a.get('exit',{}).get('mode')}")
            await u.message.reply_text("\n".join(msg))

    async def cmd_config_set(self, u, c):
        if not self._auth(u): return
        try:
            _, exchange, symbol, kv = u.message.text.split(maxsplit=3)
            key, val = kv.split("=", 1)
        except ValueError:
            return await u.message.reply_text("usage: /set <exchange> <symbol> <key>=<value>")
        e = self.engines.get(exchange)
        if not e: return await u.message.reply_text("unknown exchange")
        a = e.cfg["assets"].get(symbol)
        if not a: return await u.message.reply_text("unknown symbol")

        v = val.lower()
        if v in ("true","false"): v = (v == "true")
        elif v in ("null","none"): v = None
        else:
            try: v = float(v) if "." in v else int(v)
            except ValueError: pass

        if key == "enabled":
            a["enabled"] = bool(v)
            if v: e.pf.capital[symbol] = float(a["capital_usd"])
        elif key == "capital_usd":
            a["capital_usd"] = float(v); e.pf.capital[symbol] = float(v)
        elif key == "leverage":
            lev = int(v)
            if not (1 <= lev <= 40): return await u.message.reply_text("leverage 1..40 only")
            a["leverage"] = lev
            try: await e.adapter.set_leverage(symbol, lev)
            except Exception as ex: return await u.message.reply_text(f"leverage set failed: {ex}")
        elif key.startswith("exit."):
            a.setdefault("exit", {})[key.split(".",1)[1]] = v
        else:
            a[key] = v
        await u.message.reply_text(f"updated {exchange} {symbol} {key}={v}")

    async def start(self):
        await self.app.initialize()
        await self.app.bot.set_my_commands([
            BotCommand("dashboard","per-asset price/R/position"),
            BotCommand("positions","open positions"),
            BotCommand("status","equity + halt state"),
            BotCommand("report","win rate, PF, sharpe, pnl"),
            BotCommand("trades","last 5 trades per exchange"),
            BotCommand("config","show config"),
            BotCommand("set","edit config: /set ex sym key=val"),
            BotCommand("kill","flatten + halt"),
            BotCommand("run","resume after kill"),
            BotCommand("help","command list"),
        ])
        await self.app.start()
        await self.app.updater.start_polling()

    async def stop(self):
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

HELP_TEXT = """Commands:
/dashboard  - live price, R, position, leverage per asset
/positions  - open positions
/status     - equity + halted flag
/report     - win rate / profit factor / sharpe / pnl / DD
/trades     - last 5 trades per exchange
/config     - show current config
/set        - /set <ex> <sym> <key>=<value>
             keys: enabled, capital_usd, leverage(1-40),
                   exit.mode, exit.fixed_r_tp, exit.max_hold_bars, exit.stop_atr_cap
/kill       - flatten everything + halt new entries
/run        - resume after /kill
/help       - this list
"""