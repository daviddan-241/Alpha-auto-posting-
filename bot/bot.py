import asyncio
import logging
import os
import random
import time
from io import BytesIO

from dotenv import load_dotenv
from telegram import (
    Bot, InlineKeyboardButton, InlineKeyboardMarkup,
    Update, ChatMember
)
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, filters, ChatMemberHandler
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

from dex_fetcher import (
    fetch_trending_tokens, fetch_new_coins, fetch_ohlcv_data,
    fetch_token_data, format_mc, format_short_addr
)
from chart_generator import generate_chart_image
from image_generator import generate_kol_card, generate_initial_call_image

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8765151932:AAFcxEoBl2Z9Iq4zJMCHlEr5yvBXK44Q8gY")
CHAT_ID = os.getenv("CHAT_ID", "-1003559583277")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@crypto_guy02")
CHANNEL_LINK = "https://t.me/AlphaCirclle"

MIN_MC = float(os.getenv("MIN_MC", 120_000))
MAX_MC = float(os.getenv("MAX_MC", 50_000_000))
GAIN_THRESHOLD_PCT = float(os.getenv("GAIN_THRESHOLD_PCT", 20))
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", 300))
SEND_INTERVAL_MIN = int(os.getenv("SEND_INTERVAL_MIN", 120))
SEND_INTERVAL_MAX = int(os.getenv("SEND_INTERVAL_MAX", 420))

tracked_coins: dict[str, dict] = {}
sent_updates: dict[str, list] = {}
last_sent_time = 0.0


KOL_TEMPLATES = [
    "🔥 *{name}* is MOVING fr fr\n\n📊 Entry MC: {entry_mc}\n📈 Current MC: {current_mc}\n💰 Gain: *+{gain}%*\n\n💧 Liquidity: {liq}\n📍 CA: `{ca}`\n\n⚡ {gain_str} in {time_str} — don't sleep on this one\n\n🔗 {dex_url}",

    "👀 Noticed *${symbol}* just jumped\n\n🎯 Called at: {entry_mc}\n📊 Now: {current_mc} (+{gain}%)\n\n💧 Liq: {liq} | Chain: Solana\n📍 `{ca}`\n\nThis thing got legs 🦵\n\n🔗 {dex_url}",

    "💎 *{name}* UPDATE\n\nCalled at {entry_mc}, sitting at {current_mc} right now\n\n📈 *{gain_str}* move\n🕒 Time since call: {time_str}\n💰 Liq: {liq}\n\n📌 CA: `{ca}`\n\nHolding strong 💪\n\n{dex_url}",

    "🚀 *${symbol}* running!\n\nEntry: {entry_mc} → Now: {current_mc}\n+{gain}% since we called it\n\n💧 {liq} liquidity, still healthy\n\n`{ca}`\n\n{dex_url}",

    "Ayo *{name}* said let's go 🏃\n\nWas at {entry_mc}\nNow chilling at {current_mc}\nThat's *{gain_str}* gains\n\n📍 `{ca}`\n💧 Liq: {liq}\n\n{dex_url}",
]

INITIAL_CALL_TEMPLATES = [
    "🚨 *NEW ALPHA* — *{name}* on Solana\n\n📍 Entry MC: *{mc}*\n💧 Liquidity: {liq}\n📊 24h Vol: {vol}\n\n🎯 Target: *2X–5X*\n\nCA: `{ca}`\n\n🔗 {dex_url}\n\n⚡ Early — don't say I never told you",

    "👀 *${symbol}* just showed up on radar\n\nMC: {mc} | Liq: {liq}\nVol 24h: {vol}\n\nCA on SOL: `{ca}`\n\nClean chart, decent liq — watching this 🔍\n\n{dex_url}",

    "🔥 *{name}* — Fresh Call\n\n💰 Market Cap: {mc}\n💧 Liq: {liq} (healthy)\n📈 Vol: {vol}\n\n`{ca}`\n\nTarget: 2–4X from here 🎯\n\n{dex_url}",

    "New bag alert 🎒 *${symbol}*\n\nSolana gem with {mc} MC right now\nLiquidity sittin at {liq} — not bad\n\nCA: `{ca}`\n\n{dex_url}\n\nEarly entry fr 🚀",

    "💡 *{name}* — Low cap opportunity\n\nMC: {mc} | Vol: {vol}\nLiq: {liq}\n\n📌 `{ca}`\n\nIf this hits the right eyes it's going 🔺\n\n{dex_url}",
]


def _fmt_time_since(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds//60)}m, {int(seconds%60)}s"
    return f"{int(seconds//3600)}h, {int((seconds%3600)//60)}m"


def _gain_str(pct: float) -> str:
    if pct >= 100:
        x = pct / 100 + 1
        return f"{x:.1f}X"
    return f"+{pct:.0f}%"


async def send_initial_call(bot: Bot, token: dict):
    global last_sent_time
    now = time.time()
    wait = random.uniform(SEND_INTERVAL_MIN, SEND_INTERVAL_MAX)
    if now - last_sent_time < wait:
        await asyncio.sleep(wait - (now - last_sent_time))

    mc = token.get("market_cap", 0)
    liq = token.get("liquidity_usd", 0)
    vol = token.get("volume_24h", 0)
    ca = token.get("address", "")
    name = token.get("name", token.get("symbol", "???"))
    symbol = token.get("symbol", "???")
    dex_url = token.get("url") or f"https://dexscreener.com/solana/{ca}"

    text = random.choice(INITIAL_CALL_TEMPLATES).format(
        name=name, symbol=symbol,
        mc=format_mc(mc), liq=format_mc(liq), vol=format_mc(vol),
        ca=ca, dex_url=dex_url
    )

    try:
        chart_img_bytes = None
        call_card_bytes = None

        try:
            bars = fetch_ohlcv_data(token.get("pair_address", ""))
            chart_img_bytes = generate_chart_image(token, bars)
        except Exception as e:
            log.warning(f"Chart gen failed: {e}")

        try:
            call_card_bytes = generate_initial_call_image(token)
        except Exception as e:
            log.warning(f"Call card gen failed: {e}")

        if call_card_bytes:
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=BytesIO(call_card_bytes),
                caption=text,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif chart_img_bytes:
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=BytesIO(chart_img_bytes),
                caption=text,
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode=ParseMode.MARKDOWN)

        if chart_img_bytes and call_card_bytes:
            await asyncio.sleep(random.uniform(2, 5))
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=BytesIO(chart_img_bytes),
                caption=f"📊 *{symbol}* Chart — DEX Screener style",
                parse_mode=ParseMode.MARKDOWN
            )

        last_sent_time = time.time()
        log.info(f"Sent initial call for {symbol}")

    except TelegramError as e:
        log.error(f"Telegram error sending call: {e}")
    except Exception as e:
        log.error(f"Error sending initial call: {e}")


async def send_gain_update(bot: Bot, token: dict, entry_mc: float, gain_pct: float, called_at_str: str):
    global last_sent_time
    now = time.time()
    wait = random.uniform(60, 180)
    if now - last_sent_time < wait:
        await asyncio.sleep(wait - (now - last_sent_time))

    mc = token.get("market_cap", 0)
    liq = token.get("liquidity_usd", 0)
    ca = token.get("address", "")
    name = token.get("name", token.get("symbol", "???"))
    symbol = token.get("symbol", "???")
    dex_url = token.get("url") or f"https://dexscreener.com/solana/{ca}"

    entry_ts = tracked_coins.get(ca, {}).get("first_seen", time.time())
    time_since = time.time() - entry_ts
    time_str = _fmt_time_since(time_since)
    gain_s = _gain_str(gain_pct)

    text = random.choice(KOL_TEMPLATES).format(
        name=name, symbol=symbol,
        entry_mc=called_at_str,
        current_mc=format_mc(mc),
        gain=f"{gain_pct:.0f}",
        gain_str=gain_s,
        liq=format_mc(liq),
        ca=ca,
        dex_url=dex_url,
        time_str=time_str
    )

    try:
        kol_card_bytes = None
        chart_img_bytes = None

        try:
            kol_card_bytes = generate_kol_card(token, gain_pct, entry_mc, called_at_str)
        except Exception as e:
            log.warning(f"KOL card gen failed: {e}")

        try:
            bars = fetch_ohlcv_data(token.get("pair_address", ""))
            chart_img_bytes = generate_chart_image(token, bars)
        except Exception as e:
            log.warning(f"Chart gen failed: {e}")

        if kol_card_bytes:
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=BytesIO(kol_card_bytes),
                caption=text,
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode=ParseMode.MARKDOWN)

        if chart_img_bytes:
            await asyncio.sleep(random.uniform(1, 4))
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=BytesIO(chart_img_bytes),
                caption=f"📊 *{symbol}* Price Chart — {gain_s} from entry",
                parse_mode=ParseMode.MARKDOWN
            )

        last_sent_time = time.time()
        log.info(f"Sent {gain_s} update for {symbol}")

    except TelegramError as e:
        log.error(f"Telegram error sending update: {e}")
    except Exception as e:
        log.error(f"Error sending gain update: {e}")


async def scan_and_send(bot: Bot):
    log.info("Running coin scan...")

    new_candidates = fetch_new_coins("solana", MIN_MC, MAX_MC)
    trending = fetch_trending_tokens("solana")
    all_tokens = {t["address"]: t for t in (new_candidates + trending) if t.get("address")}.values()

    for token in all_tokens:
        ca = token.get("address", "")
        mc = token.get("market_cap", 0)
        if not ca or mc < MIN_MC or mc > MAX_MC:
            continue

        if ca not in tracked_coins:
            tracked_coins[ca] = {
                "token": token,
                "entry_mc": mc,
                "entry_mc_str": format_mc(mc),
                "first_seen": time.time(),
                "last_mc": mc,
            }
            await send_initial_call(bot, token)
            await asyncio.sleep(random.uniform(5, 15))
            continue

        entry_mc = tracked_coins[ca]["entry_mc"]
        if entry_mc <= 0:
            continue

        gain_pct = ((mc - entry_mc) / entry_mc) * 100
        prev_updates = sent_updates.get(ca, [])

        thresholds = [20, 50, 100, 200, 300, 500, 1000]
        for threshold in thresholds:
            if gain_pct >= threshold and threshold not in prev_updates:
                await send_gain_update(
                    bot, token, entry_mc,
                    gain_pct,
                    tracked_coins[ca]["entry_mc_str"]
                )
                if ca not in sent_updates:
                    sent_updates[ca] = []
                sent_updates[ca].append(threshold)
                await asyncio.sleep(random.uniform(3, 10))
                break

        tracked_coins[ca]["last_mc"] = mc
        tracked_coins[ca]["token"] = token

    prune_old_coins()


def prune_old_coins():
    cutoff = time.time() - 86400 * 3
    to_del = [ca for ca, d in tracked_coins.items() if d.get("first_seen", 0) < cutoff]
    for ca in to_del:
        del tracked_coins[ca]
        sent_updates.pop(ca, None)


async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type != "private":
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{ctx.bot.username}?startgroup=true"),
            InlineKeyboardButton("💬 Support", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}"),
        ],
        [
            InlineKeyboardButton("📢 Alpha Channel", url=CHANNEL_LINK),
        ]
    ])

    welcome = (
        f"👋 Yo *{user.first_name}*!\n\n"
        f"I'm Alpha Circle's auto-call bot 🔥\n\n"
        f"I scan DEX Screener for fresh Solana gems "
        f"and drop real-time KOL calls straight to the group with charts and everything.\n\n"
        f"📊 *What I do:*\n"
        f"• Find coins from $120K to $50M+ MC\n"
        f"• Send calls with candlestick charts\n"
        f"• Update when coins pump 20%+ 50%+ 2X+ 3X+\n\n"
        f"Add me to your group to start getting calls 👇"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def new_member_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Suppress all join/leave notifications
    return


async def periodic_scan(app: Application):
    bot = app.bot
    while True:
        try:
            await scan_and_send(bot)
        except Exception as e:
            log.error(f"Scan error: {e}")
        wait = random.randint(SCAN_INTERVAL - 60, SCAN_INTERVAL + 120)
        log.info(f"Next scan in {wait}s")
        await asyncio.sleep(wait)


def main():
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member_handler)
    )

    async def post_init(application: Application):
        asyncio.create_task(periodic_scan(application))

    app.post_init = post_init

    log.info("🚀 Alpha Circle Bot starting...")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
