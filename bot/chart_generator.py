import io
import random
import time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.ticker as ticker
from PIL import Image

DARK_BG     = "#0D1117"
GRID_COLOR  = "#1E2D40"
UP_COLOR    = "#26A69A"
DOWN_COLOR  = "#EF5350"
TEXT_COLOR  = "#B0BEC5"
LABEL_COLOR = "#ECEFF1"
ACCENT      = "#00E5FF"


def generate_chart_image(token: dict, bars: list) -> bytes:
    if len(bars) < 5:
        bars = _make_realistic_bars(token, 60)
    style = random.choice([_chart_candles, _chart_area, _chart_line_fill, _chart_neon_candles])
    return style(token, bars)


# ─── Style 1: Classic dark candlestick (DEX Screener look) ──────────────────

def _chart_candles(token: dict, bars: list) -> bytes:
    bars = bars[-80:]
    fig, (ax_main, ax_vol) = plt.subplots(
        2, 1, figsize=(10, 6),
        gridspec_kw={"height_ratios": [4, 1], "hspace": 0},
        facecolor=DARK_BG
    )
    for ax in (ax_main, ax_vol):
        ax.set_facecolor(DARK_BG)
        ax.tick_params(colors=TEXT_COLOR, labelsize=8)
        ax.spines[:].set_color(GRID_COLOR)

    n  = len(bars)
    xs = list(range(n))
    opens  = [b["o"] for b in bars]
    highs  = [b["h"] for b in bars]
    lows   = [b["l"] for b in bars]
    closes = [b["c"] for b in bars]
    vols   = [b.get("v", 0) for b in bars]

    for i, x in enumerate(xs):
        o, h, l, c = opens[i], highs[i], lows[i], closes[i]
        color = UP_COLOR if c >= o else DOWN_COLOR
        ax_main.plot([x, x], [l, h], color=color, linewidth=0.8, alpha=0.9)
        rect_h = abs(c - o) or (h - l) * 0.01
        rect = FancyBboxPatch(
            (x - 0.3, min(o, c)), 0.6, rect_h,
            boxstyle="square,pad=0", facecolor=color, edgecolor=color,
            linewidth=0.3, alpha=0.92
        )
        ax_main.add_patch(rect)

    max_idx = np.argmax(highs)
    min_idx = np.argmin(lows)
    ax_main.annotate(f"${_fmt_price(highs[max_idx])}",
                     xy=(xs[max_idx], highs[max_idx]), xytext=(0, 12),
                     textcoords="offset points", color="#4FC3F7", fontsize=7,
                     fontweight="bold", ha="center",
                     arrowprops=dict(arrowstyle="-", color="#4FC3F7", lw=0.8))
    ax_main.annotate(f"${_fmt_price(lows[min_idx])}",
                     xy=(xs[min_idx], lows[min_idx]), xytext=(0, -14),
                     textcoords="offset points", color=DOWN_COLOR, fontsize=7,
                     fontweight="bold", ha="center",
                     arrowprops=dict(arrowstyle="-", color=DOWN_COLOR, lw=0.8))

    cur = closes[-1]
    ax_main.axhline(y=cur, color="#FF6F00", linewidth=0.8, linestyle="--", alpha=0.7)
    ax_main.text(n - 0.5, cur, f" {_fmt_price(cur)}", color="white", fontsize=7.5,
                 fontweight="bold", va="center",
                 bbox=dict(facecolor="#FF6F00", edgecolor="none", pad=1.5, alpha=0.9))

    ax_main.set_xlim(-1, n + 1)
    ax_main.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _fmt_price(v)))
    ax_main.yaxis.tick_right()
    ax_main.grid(True, color=GRID_COLOR, linewidth=0.4, alpha=0.6)
    ax_main.set_xticks([])

    vol_colors = [UP_COLOR if closes[i] >= opens[i] else DOWN_COLOR for i in range(n)]
    ax_vol.bar(xs, vols, color=vol_colors, alpha=0.7, width=0.7)
    ax_vol.set_xlim(-1, n + 1)
    ax_vol.yaxis.tick_right()
    ax_vol.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _fmt_vol(v)))
    ax_vol.grid(True, color=GRID_COLOR, linewidth=0.3, alpha=0.5)
    ax_vol.text(0.01, 0.85, f"Vol  {_fmt_vol(sum(vols))}", transform=ax_vol.transAxes,
                color="#4CAF50", fontsize=7.5, fontweight="bold")

    _apply_header(fig, token, opens, highs, lows, closes)
    return _save(fig)


# ─── Style 2: Gradient area chart (bullish vibe) ────────────────────────────

def _chart_area(token: dict, bars: list) -> bytes:
    bars  = bars[-80:]
    BG    = "#0A0E1A"
    BLUE  = "#00B4FF"
    fig, (ax_main, ax_vol) = plt.subplots(
        2, 1, figsize=(10, 6),
        gridspec_kw={"height_ratios": [4, 1], "hspace": 0},
        facecolor=BG
    )
    for ax in (ax_main, ax_vol):
        ax.set_facecolor(BG)
        ax.tick_params(colors="#7090B0", labelsize=8)
        ax.spines[:].set_color("#1A2A40")

    closes = [b["c"] for b in bars]
    highs  = [b["h"] for b in bars]
    lows   = [b["l"] for b in bars]
    opens  = [b["o"] for b in bars]
    vols   = [b.get("v", 0) for b in bars]
    xs     = list(range(len(bars)))
    n      = len(bars)

    ax_main.fill_between(xs, closes, alpha=0.18, color=BLUE)
    ax_main.plot(xs, closes, color=BLUE, linewidth=1.4, alpha=0.95)

    ma = [np.mean(closes[max(0,i-10):i+1]) for i in range(n)]
    ax_main.plot(xs, ma, color="#FF9800", linewidth=0.9, linestyle="--", alpha=0.7, label="MA10")

    cur = closes[-1]
    ax_main.axhline(y=cur, color="#00E5FF", linewidth=0.8, linestyle=":", alpha=0.8)
    ax_main.text(n - 0.5, cur, f" {_fmt_price(cur)}", color="white", fontsize=7.5,
                 fontweight="bold", va="center",
                 bbox=dict(facecolor="#00B4FF", edgecolor="none", pad=1.5, alpha=0.85))

    ax_main.set_xlim(-1, n + 1)
    ax_main.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _fmt_price(v)))
    ax_main.yaxis.tick_right()
    ax_main.grid(True, color="#1A2A40", linewidth=0.4, alpha=0.6)
    ax_main.set_xticks([])

    ax_vol.bar(xs, vols, color=BLUE, alpha=0.5, width=0.8)
    ax_vol.set_xlim(-1, n + 1)
    ax_vol.yaxis.tick_right()
    ax_vol.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _fmt_vol(v)))
    ax_vol.grid(True, color="#1A2A40", linewidth=0.3, alpha=0.5)
    ax_vol.text(0.01, 0.85, f"Vol  {_fmt_vol(sum(vols))}", transform=ax_vol.transAxes,
                color=BLUE, fontsize=7.5, fontweight="bold")

    _apply_header(fig, token, opens, highs, lows, closes, bg=BG)
    return _save(fig, bg=BG)


# ─── Style 3: Line + shaded fill (clean minimal) ────────────────────────────

def _chart_line_fill(token: dict, bars: list) -> bytes:
    bars  = bars[-80:]
    BG    = "#090C14"
    GREEN = "#00E676"
    RED   = "#FF1744"
    fig, (ax_main, ax_vol) = plt.subplots(
        2, 1, figsize=(10, 6),
        gridspec_kw={"height_ratios": [4, 1], "hspace": 0},
        facecolor=BG
    )
    for ax in (ax_main, ax_vol):
        ax.set_facecolor(BG)
        ax.tick_params(colors="#6080A0", labelsize=8)
        ax.spines[:].set_color("#15202E")

    closes = [b["c"] for b in bars]
    highs  = [b["h"] for b in bars]
    lows   = [b["l"] for b in bars]
    opens  = [b["o"] for b in bars]
    vols   = [b.get("v", 0) for b in bars]
    xs     = list(range(len(bars)))
    n      = len(bars)

    change = (closes[-1] - closes[0]) / closes[0] * 100 if closes[0] else 0
    line_col = GREEN if change >= 0 else RED
    base = min(closes)
    ax_main.fill_between(xs, closes, base, alpha=0.12, color=line_col)
    ax_main.plot(xs, closes, color=line_col, linewidth=1.6)
    ax_main.plot(xs, highs, color="#333D50", linewidth=0.5, alpha=0.6)
    ax_main.plot(xs, lows, color="#333D50", linewidth=0.5, alpha=0.6)
    ax_main.fill_between(xs, highs, lows, alpha=0.06, color="#7090B0")

    cur = closes[-1]
    ax_main.axhline(y=cur, color=line_col, linewidth=0.8, linestyle="--", alpha=0.6)
    ax_main.text(n - 0.5, cur, f" {_fmt_price(cur)}", color="black", fontsize=7.5,
                 fontweight="bold", va="center",
                 bbox=dict(facecolor=line_col, edgecolor="none", pad=1.5, alpha=0.95))

    ax_main.set_xlim(-1, n + 1)
    ax_main.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _fmt_price(v)))
    ax_main.yaxis.tick_right()
    ax_main.grid(True, color="#15202E", linewidth=0.4, alpha=0.6)
    ax_main.set_xticks([])

    vol_colors = [GREEN if closes[i] >= opens[i] else RED for i in range(n)]
    ax_vol.bar(xs, vols, color=vol_colors, alpha=0.65, width=0.8)
    ax_vol.set_xlim(-1, n + 1)
    ax_vol.yaxis.tick_right()
    ax_vol.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _fmt_vol(v)))
    ax_vol.grid(True, color="#15202E", linewidth=0.3, alpha=0.5)
    ax_vol.text(0.01, 0.85, f"Vol  {_fmt_vol(sum(vols))}", transform=ax_vol.transAxes,
                color=line_col, fontsize=7.5, fontweight="bold")

    _apply_header(fig, token, opens, highs, lows, closes, bg=BG)
    return _save(fig, bg=BG)


# ─── Style 4: Neon candles (purple-pink glow) ───────────────────────────────

def _chart_neon_candles(token: dict, bars: list) -> bytes:
    bars   = bars[-80:]
    BG     = "#06040F"
    BULL   = "#00FFAA"
    BEAR   = "#FF2D6F"
    PURPLE = "#7B2FBE"
    fig, (ax_main, ax_vol) = plt.subplots(
        2, 1, figsize=(10, 6),
        gridspec_kw={"height_ratios": [4, 1], "hspace": 0},
        facecolor=BG
    )
    for ax in (ax_main, ax_vol):
        ax.set_facecolor(BG)
        ax.tick_params(colors="#9060C0", labelsize=8)
        ax.spines[:].set_color("#2A1050")

    n  = len(bars)
    xs = list(range(n))
    opens  = [b["o"] for b in bars]
    highs  = [b["h"] for b in bars]
    lows   = [b["l"] for b in bars]
    closes = [b["c"] for b in bars]
    vols   = [b.get("v", 0) for b in bars]

    for i, x in enumerate(xs):
        o, h, l, c = opens[i], highs[i], lows[i], closes[i]
        color = BULL if c >= o else BEAR
        ax_main.plot([x, x], [l, h], color=color, linewidth=0.9, alpha=0.85)
        rect_h = abs(c - o) or (h - l) * 0.01
        rect = FancyBboxPatch(
            (x - 0.3, min(o, c)), 0.6, rect_h,
            boxstyle="square,pad=0", facecolor=color,
            edgecolor=color, linewidth=0.3, alpha=0.88
        )
        ax_main.add_patch(rect)

    cur = closes[-1]
    ax_main.axhline(y=cur, color="#E040FB", linewidth=1, linestyle="--", alpha=0.8)
    ax_main.text(n - 0.5, cur, f" {_fmt_price(cur)}", color="white", fontsize=7.5,
                 fontweight="bold", va="center",
                 bbox=dict(facecolor=PURPLE, edgecolor="none", pad=1.5, alpha=0.95))

    ma = [np.mean(closes[max(0,i-14):i+1]) for i in range(n)]
    ax_main.plot(xs, ma, color="#FFD600", linewidth=0.9, alpha=0.65)

    ax_main.set_xlim(-1, n + 1)
    ax_main.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _fmt_price(v)))
    ax_main.yaxis.tick_right()
    ax_main.grid(True, color="#2A1050", linewidth=0.4, alpha=0.6)
    ax_main.set_xticks([])

    vol_colors = [BULL if closes[i] >= opens[i] else BEAR for i in range(n)]
    ax_vol.bar(xs, vols, color=vol_colors, alpha=0.65, width=0.8)
    ax_vol.set_xlim(-1, n + 1)
    ax_vol.yaxis.tick_right()
    ax_vol.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _fmt_vol(v)))
    ax_vol.grid(True, color="#2A1050", linewidth=0.3, alpha=0.5)
    ax_vol.text(0.01, 0.85, f"Vol  {_fmt_vol(sum(vols))}", transform=ax_vol.transAxes,
                color=BULL, fontsize=7.5, fontweight="bold")

    _apply_header(fig, token, opens, highs, lows, closes, bg=BG)
    return _save(fig, bg=BG)


# ─── Shared helpers ──────────────────────────────────────────────────────────

def _apply_header(fig, token, opens, highs, lows, closes, bg=DARK_BG):
    symbol  = token.get("symbol", "???")
    dex     = token.get("dex", "DEX").title()
    chain   = token.get("chain", "SOL").upper()
    mc      = token.get("market_cap", 0)
    p_open  = opens[0]
    p_now   = closes[-1]
    chg     = ((p_now - p_open) / p_open * 100) if p_open else 0
    clr     = UP_COLOR if chg >= 0 else DOWN_COLOR

    title = f"{symbol}/{chain}  ·  {dex}  ·  15m  ·  dexscreener.com"
    fig.text(0.01, 0.97, title, color=LABEL_COLOR, fontsize=8.5, fontweight="bold",
             va="top", ha="left")

    ohlc = (f"O{_fmt_price(opens[0])}  H{_fmt_price(max(highs))}  "
            f"L{_fmt_price(min(lows))}  C{_fmt_price(closes[-1])}  "
            f"MC:{_fmt_mc(mc)}  {chg:+.1f}%")
    fig.text(0.01, 0.93, ohlc, color=clr, fontsize=7.5, va="top", ha="left")
    fig.text(0.98, 0.97, "●", color="#4CAF50", fontsize=12, va="top", ha="right")
    plt.tight_layout(rect=[0, 0, 1, 0.92])


def _save(fig, bg=DARK_BG) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=bg, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _make_realistic_bars(token: dict, n: int = 60) -> list:
    seed = token.get("price_usd") or random.uniform(0.000001, 0.01)
    bars  = []
    price = seed * random.uniform(0.5, 0.9)
    ts    = int(time.time()) - n * 15 * 60
    trend = random.uniform(0.005, 0.02)
    for i in range(n):
        noise = random.gauss(trend, 0.06)
        o = price
        c = price * (1 + noise)
        h = max(o, c) * (1 + abs(random.gauss(0, 0.02)))
        l = min(o, c) * (1 - abs(random.gauss(0, 0.02)))
        v = random.uniform(2000, 80000) * (1 + i / n)
        bars.append({"t": ts + i * 900, "o": o, "h": h, "l": l, "c": c, "v": v})
        price = c
    return bars


def _fmt_price(v: float) -> str:
    if v == 0: return "0"
    if v >= 1: return f"{v:.2f}"
    if v >= 0.001: return f"{v:.4f}"
    if v >= 0.000001: return f"{v:.7f}"
    return f"{v:.2e}"


def _fmt_vol(v: float) -> str:
    if v >= 1_000_000: return f"{v/1_000_000:.2f}M"
    if v >= 1_000:     return f"{v/1_000:.2f}K"
    return f"{v:.0f}"


def _fmt_mc(v: float) -> str:
    if v >= 1_000_000: return f"${v/1_000_000:.1f}M"
    if v >= 1_000:     return f"${v/1_000:.0f}K"
    return f"${v:.0f}"
