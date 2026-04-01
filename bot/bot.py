import asyncio
import logging
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO

from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError, RetryAfter

from dex_fetcher import (
    fetch_trending_tokens, fetch_new_coins, fetch_ohlcv_data, format_mc
)
from chart_generator import generate_chart_image
from image_generator import generate_kol_card, generate_initial_call_image

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN", "8706555596:AAGE8SlGcu7b56B1kBD52jzxKjN3irWy6zk")
CHAT_ID           = os.getenv("CHAT_ID",           "-1003559583277")
MIN_MC            = float(os.getenv("MIN_MC",            10_000))
MAX_MC            = float(os.getenv("MAX_MC",           800_000))
SCAN_INTERVAL     = int(os.getenv("SCAN_INTERVAL",          300))
SEND_INTERVAL_MIN = int(os.getenv("SEND_INTERVAL_MIN",       60))
SEND_INTERVAL_MAX = int(os.getenv("SEND_INTERVAL_MAX",      180))
PORT              = int(os.getenv("PORT",                   8080))

tracked_coins: dict = {}
sent_updates:  dict = {}
last_sent_time: float = 0.0

# ─── Caption templates ────────────────────────────────────────────────────────

INITIAL_TEMPLATES = [
    "Keeping an eye on *{name}* — still early, low cap, strong on-chain activity. Not financial advice.\n\n💰 MC: {mc}  |  💧 Liq: {liq}\n📊 Vol 24h: {vol}\n\n`{ca}`",
    "👀 *${symbol}* just popped up on radar\n\nMC sitting at {mc}, liquidity looks decent at {liq}.\nChart's early — could go either way, but worth watching.\n\n`{ca}`\n\n{dex_url}",
    "New one: *{name}*\n\nLow cap play on Solana — {mc} MC right now.\nLiq: {liq}  |  Vol: {vol}\n\nIf this catches momentum it could move fast.\n\n`{ca}`",
    "📌 *${symbol}* added to watchlist\n\nEntry MC: {mc}\nLiquidity: {liq}\n24h Vol: {vol}\n\nClean tokenomics so far, volume picking up.\n\n`{ca}`\n{dex_url}",
    "🔍 Spotted *{name}* at {mc}\n\nStill very early. Liq is {liq} — manageable.\nWatching for a volume spike to confirm.\n\n`{ca}`\n{dex_url}",
    "Sharing a low-cap gem I found — *${symbol}*\n\nMC: {mc}  •  Liq: {liq}  •  Vol: {vol}\n\nNot a call yet. Doing more research. CA below:\n\n`{ca}`",
    "⚡ *{name}* — fresh find\n\nOnly {mc} MC. This one's early.\nLiquidity: {liq} | Volume: {vol}\n\nDyor, but this is on my radar.\n\n`{ca}`\n{dex_url}",
]

UPDATE_TEMPLATES = [
    "We called *{name}* at {entry_mc} — it's up *{gain_str}* now 📈\n\nCurrent MC: {current_mc}\nTime held: {time_str}\n\n`{ca}`\n{dex_url}",
    "🔥 *${symbol}* is running\n\nCalled at {entry_mc} → now {current_mc}\nThat's *{gain_str}* in {time_str}\n\n`{ca}`",
    "*{name}* update — *{gain_str}* from our entry 🚀\n\nEntry: {entry_mc}\nNow: {current_mc}  |  Liq: {liq}\n\n`{ca}`\n{dex_url}",
    "👀 *${symbol}* doing what we thought\n\nIn at {entry_mc}, sitting at {current_mc} now\n*{gain_str}* move — {time_str} since call\n\n`{ca}`",
    "*{gain_str}* on *{name}* 💰\n\nCalled it at {entry_mc}, now at {current_mc}\nLiquidity still healthy at {liq}\n\n`{ca}`\n{dex_url}",
    "Locked in on *{name}* at {entry_mc}\nNow {current_mc} — that's *{gain_str}* 📊\n\n{time_str} since the call. Still watching.\n\n`{ca}`",
    "🎯 *${symbol}* — *{gain_str}* return\n\nEntry MC: {entry_mc}\nCurrent MC: {current_mc}\nTime: {time_str}  |  Liq: {liq}\n\n`{ca}`\n{dex_url}",
]


def _fmt_time(s: float) -> str:
    if s < 60:   return f"{int(s)}s"
    if s < 3600: return f"{int(s//60)}m {int(s%60)}s"
    return f"{int(s//3600)}h {int((s%3600)//60)}m"


def _gain_str(pct: float) -> str:
    if pct >= 100: return f"{pct/100+1:.1f}X"
    return f"+{pct:.0f}%"


# ─── Health server (UptimeRobot) ──────────────────────────────────────────────

class _Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *_):
        pass


def _start_health_server():
    try:
        srv = HTTPServer(("0.0.0.0", PORT), _Health)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        log.info(f"✅ Health server listening on port {PORT}")
    except OSError as e:
        log.warning(f"Health server skipped (port {PORT} unavailable): {e}")


# ─── Telegram helpers ─────────────────────────────────────────────────────────

async def _throttle():
    global last_sent_time
    gap     = random.uniform(SEND_INTERVAL_MIN, SEND_INTERVAL_MAX)
    elapsed = time.time() - last_sent_time
    if elapsed < gap:
        await asyncio.sleep(gap - elapsed)


async def _send_photo(bot: Bot, photo: bytes, caption: str) -> bool:
    for attempt in range(4):
        try:
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=BytesIO(photo),
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
            )
            return True
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except TelegramError as e:
            msg = str(e)
            if "Peer_id_invalid" in msg or "chat not found" in msg.lower():
                log.error("❌ Bot not in group — add @carispost_bot to the channel")
                return False
            log.warning(f"Telegram error ({attempt+1}): {e}")
            await asyncio.sleep(6 * (attempt + 1))
        except Exception as e:
            log.warning(f"Send error ({attempt+1}): {e}")
            await asyncio.sleep(5)
    return False


async def _send_text(bot: Bot, text: str) -> bool:
    for attempt in range(4):
        try:
            await bot.send_message(
                chat_id=CHAT_ID, text=text, parse_mode=ParseMode.MARKDOWN
            )
            return True
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except TelegramError as e:
            msg = str(e)
            if "Peer_id_invalid" in msg or "chat not found" in msg.lower():
                log.error("❌ Bot not in group")
                return False
            log.warning(f"Telegram error ({attempt+1}): {e}")
            await asyncio.sleep(6 * (attempt + 1))
        except Exception as e:
            log.warning(f"Send error ({attempt+1}): {e}")
            await asyncio.sleep(5)
    return False


# ─── Send functions ───────────────────────────────────────────────────────────

async def send_initial_call(bot: Bot, token: dict):
    global last_sent_time
    await _throttle()

    mc      = token.get("market_cap", 0)
    liq     = token.get("liquidity_usd", 0)
    vol     = token.get("volume_24h", 0)
    ca      = token.get("address", "")
    name    = token.get("name", token.get("symbol", "???"))
    symbol  = token.get("symbol", "???")
    dex_url = token.get("url") or f"https://dexscreener.com/solana/{ca}"

    text = random.choice(INITIAL_TEMPLATES).format(
        name=name, symbol=symbol,
        mc=format_mc(mc), liq=format_mc(liq), vol=format_mc(vol),
        ca=ca, dex_url=dex_url
    )

    call_card = chart_img = None
    try:
        call_card = generate_initial_call_image(token)
    except Exception as e:
        log.warning(f"Call card error: {e}")
    try:
        bars = fetch_ohlcv_data(token.get("pair_address", ""))
        chart_img = generate_chart_image(token, bars)
    except Exception as e:
        log.warning(f"Chart error: {e}")

    sent = False
    if call_card:
        sent = await _send_photo(bot, call_card, text)
    elif chart_img:
        sent = await _send_photo(bot, chart_img, text)
    else:
        sent = await _send_text(bot, text)

    if sent and call_card and chart_img:
        await asyncio.sleep(random.uniform(3, 7))
        await _send_photo(bot, chart_img, f"📊 *{symbol}* chart")

    if sent:
        last_sent_time = time.time()
        log.info(f"✅ Call sent: {symbol}  MC={format_mc(mc)}")


async def send_gain_update(bot: Bot, token: dict,
                           entry_mc: float, gain_pct: float, called_at: str):
    global last_sent_time
    await _throttle()

    mc      = token.get("market_cap", 0)
    liq     = token.get("liquidity_usd", 0)
    ca      = token.get("address", "")
    name    = token.get("name", token.get("symbol", "???"))
    symbol  = token.get("symbol", "???")
    dex_url = token.get("url") or f"https://dexscreener.com/solana/{ca}"
    elapsed = time.time() - tracked_coins.get(ca, {}).get("first_seen", time.time())
    gain_s  = _gain_str(gain_pct)

    text = random.choice(UPDATE_TEMPLATES).format(
        name=name, symbol=symbol,
        entry_mc=called_at, current_mc=format_mc(mc),
        gain_str=gain_s, liq=format_mc(liq),
        ca=ca, dex_url=dex_url, time_str=_fmt_time(elapsed)
    )

    kol_card = chart_img = None
    try:
        kol_card = generate_kol_card(token, gain_pct, entry_mc, called_at)
    except Exception as e:
        log.warning(f"KOL card error: {e}")
    try:
        bars = fetch_ohlcv_data(token.get("pair_address", ""))
        chart_img = generate_chart_image(token, bars)
    except Exception as e:
        log.warning(f"Chart error: {e}")

    sent = False
    if kol_card:
        sent = await _send_photo(bot, kol_card, text)
    else:
        sent = await _send_text(bot, text)

    if sent and chart_img:
        await asyncio.sleep(random.uniform(2, 5))
        await _send_photo(bot, chart_img, f"📊 *{symbol}* — {gain_s} from entry")

    if sent:
        last_sent_time = time.time()
        log.info(f"✅ Update sent: {symbol}  {gain_s}")


# ─── Scan loop ────────────────────────────────────────────────────────────────

async def scan_and_send(bot: Bot):
    log.info("🔍 Scanning DEX Screener...")
    try:
        new_coins = fetch_new_coins("solana", MIN_MC, MAX_MC)
        trending  = fetch_trending_tokens("solana")
        all_tokens = {t["address"]: t for t in (new_coins + trending)
                      if t.get("address")}
    except Exception as e:
        log.error(f"Fetch error: {e}")
        return

    for ca, token in all_tokens.items():
        mc = token.get("market_cap", 0)
        if not ca or not (MIN_MC <= mc <= MAX_MC):
            continue

        if ca not in tracked_coins:
            tracked_coins[ca] = {
                "token":        token,
                "entry_mc":     mc,
                "entry_mc_str": format_mc(mc),
                "first_seen":   time.time(),
            }
            await send_initial_call(bot, token)
            await asyncio.sleep(random.uniform(8, 20))
            continue

        entry_mc = tracked_coins[ca]["entry_mc"]
        if entry_mc <= 0:
            continue

        gain_pct = ((mc - entry_mc) / entry_mc) * 100
        done = sent_updates.get(ca, [])
        for threshold in [20, 50, 100, 200, 300, 500, 1000]:
            if gain_pct >= threshold and threshold not in done:
                await send_gain_update(
                    bot, token, entry_mc, gain_pct,
                    tracked_coins[ca]["entry_mc_str"]
                )
                sent_updates.setdefault(ca, []).append(threshold)
                await asyncio.sleep(random.uniform(5, 12))
                break

        tracked_coins[ca]["token"] = token

    # Purge coins older than 3 days
    cutoff = time.time() - 86400 * 3
    for ca in [k for k, v in tracked_coins.items()
               if v.get("first_seen", 0) < cutoff]:
        tracked_coins.pop(ca, None)
        sent_updates.pop(ca, None)


async def run_bot():
    log.info("🚀 Alpha Circle Bot starting...")
    _start_health_server()

    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        me = await bot.get_me()
        log.info(f"✅ Connected as @{me.username}")
    except Exception as e:
        log.error(f"Connection failed: {e}")
        return

    while True:
        try:
            await scan_and_send(bot)
        except Exception as e:
            log.error(f"Scan error: {e}")
        wait = random.randint(
            max(60, SCAN_INTERVAL - 60),
            SCAN_INTERVAL + 120
        )
        log.info(f"⏳ Next scan in {wait}s")
        await asyncio.sleep(wait)


if __name__ == "__main__":
    asyncio.run(run_bot())
