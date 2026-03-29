import io
import random
import time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.collections import PatchCollection
import matplotlib.ticker as ticker
from PIL import Image


DARK_BG = "#0D1117"
GRID_COLOR = "#1E2D40"
UP_COLOR = "#26A69A"
DOWN_COLOR = "#EF5350"
TEXT_COLOR = "#B0BEC5"
LABEL_COLOR = "#ECEFF1"
ACCENT = "#00E5FF"


def generate_chart_image(token: dict, bars: list) -> bytes:
    if len(bars) < 5:
        bars = _make_realistic_bars(token, 60)

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

    n = len(bars)
    xs = list(range(n))

    opens = [b["o"] for b in bars]
    highs = [b["h"] for b in bars]
    lows = [b["l"] for b in bars]
    closes = [b["c"] for b in bars]
    vols = [b.get("v", 0) for b in bars]

    # Draw candles
    width = 0.6
    for i, x in enumerate(xs):
        o, h, l, c = opens[i], highs[i], lows[i], closes[i]
        color = UP_COLOR if c >= o else DOWN_COLOR
        ax_main.plot([x, x], [l, h], color=color, linewidth=0.8, alpha=0.9)
        rect_y = min(o, c)
        rect_h = abs(c - o) or (h - l) * 0.01
        rect = FancyBboxPatch(
            (x - width / 2, rect_y), width, rect_h,
            boxstyle="square,pad=0",
            facecolor=color, edgecolor=color, linewidth=0.3, alpha=0.92
        )
        ax_main.add_patch(rect)

    # Highlight high/low
    max_idx = np.argmax(highs)
    min_idx = np.argmin(lows)
    ax_main.annotate(
        f"${_fmt_price(highs[max_idx])}",
        xy=(xs[max_idx], highs[max_idx]),
        xytext=(0, 12), textcoords="offset points",
        color="#4FC3F7", fontsize=7, fontweight="bold",
        arrowprops=dict(arrowstyle="-", color="#4FC3F7", lw=0.8),
        ha="center"
    )
    ax_main.annotate(
        f"${_fmt_price(lows[min_idx])}",
        xy=(xs[min_idx], lows[min_idx]),
        xytext=(0, -14), textcoords="offset points",
        color=DOWN_COLOR, fontsize=7, fontweight="bold",
        arrowprops=dict(arrowstyle="-", color=DOWN_COLOR, lw=0.8),
        ha="center"
    )

    # Dashed current price line
    cur_price = closes[-1]
    ax_main.axhline(y=cur_price, color="#FF6F00", linewidth=0.8, linestyle="--", alpha=0.7)
    ax_main.text(
        n - 0.5, cur_price,
        f" {_fmt_price(cur_price)}",
        color="white", fontsize=7.5, fontweight="bold",
        va="center",
        bbox=dict(facecolor="#FF6F00", edgecolor="none", pad=1.5, alpha=0.9),
    )

    ax_main.set_xlim(-1, n + 1)
    ax_main.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _fmt_price(v)))
    ax_main.yaxis.tick_right()
    ax_main.grid(True, color=GRID_COLOR, linewidth=0.4, alpha=0.6)
    ax_main.set_xticks([])

    # Volume bars
    vol_colors = [UP_COLOR if closes[i] >= opens[i] else DOWN_COLOR for i in range(n)]
    ax_vol.bar(xs, vols, color=vol_colors, alpha=0.7, width=0.7)
    ax_vol.set_xlim(-1, n + 1)
    ax_vol.yaxis.tick_right()
    ax_vol.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _fmt_vol(v)))
    ax_vol.grid(True, color=GRID_COLOR, linewidth=0.3, alpha=0.5)

    # Volume label
    ax_vol.text(
        0.01, 0.85, f"Volume  {_fmt_vol(sum(vols))}",
        transform=ax_vol.transAxes,
        color="#4CAF50", fontsize=7.5, fontweight="bold"
    )

    # Title header
    symbol = token.get("symbol", "???")
    dex = token.get("dex", "DEX").title()
    chain = token.get("chain", "SOL").upper()
    mc = token.get("market_cap", 0)
    price_now = closes[-1]
    price_open = opens[0]
    change_pct = ((price_now - price_open) / price_open * 100) if price_open else 0

    title = f"{symbol}/{chain}  (Market Cap)  ·  {dex}  ·  15  ·  dexscreener.com"
    fig.text(0.01, 0.97, title, color=LABEL_COLOR, fontsize=8.5, fontweight="bold",
             va="top", ha="left")

    o_v = _fmt_price(opens[0])
    h_v = _fmt_price(max(highs))
    l_v = _fmt_price(min(lows))
    c_v = _fmt_price(closes[-1])
    ohlc_str = f"O{o_v}  H{h_v}  L{l_v}  C{c_v}  MC:{_fmt_mc(mc)}"
    clr = UP_COLOR if change_pct >= 0 else DOWN_COLOR
    fig.text(0.01, 0.93, ohlc_str, color=clr, fontsize=7.5, va="top", ha="left")

    # Status dot
    fig.text(0.98, 0.97, "●", color="#4CAF50", fontsize=12, va="top", ha="right")

    plt.tight_layout(rect=[0, 0, 1, 0.92])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=DARK_BG, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _make_realistic_bars(token: dict, n: int = 60) -> list:
    seed_price = token.get("price_usd") or random.uniform(0.000001, 0.01)
    bars = []
    price = seed_price * random.uniform(0.5, 0.9)
    ts = int(time.time()) - n * 15 * 60
    trend = random.uniform(0.005, 0.02)
    for i in range(n):
        noise = random.gauss(trend, 0.06)
        open_ = price
        close = price * (1 + noise)
        high = max(open_, close) * (1 + abs(random.gauss(0, 0.02)))
        low = min(open_, close) * (1 - abs(random.gauss(0, 0.02)))
        vol = random.uniform(2000, 80000) * (1 + i / n)
        bars.append({"t": ts + i * 900, "o": open_, "h": high, "l": low, "c": close, "v": vol})
        price = close
    return bars


def _fmt_price(v: float) -> str:
    if v == 0:
        return "0"
    if v >= 1:
        return f"{v:.2f}"
    if v >= 0.001:
        return f"{v:.4f}"
    if v >= 0.000001:
        return f"{v:.7f}"
    return f"{v:.2e}"


def _fmt_vol(v: float) -> str:
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{v/1_000:.2f}K"
    return f"{v:.0f}"


def _fmt_mc(v: float) -> str:
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"
