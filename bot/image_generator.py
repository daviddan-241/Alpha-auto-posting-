import io
import math
import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

W, H = 960, 520

# Asset paths (relative to this file's directory)
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
SWAMP_BG   = os.path.join(ASSETS_DIR, "swamp_bg.png")
PEPE_VARIANTS = [
    os.path.join(ASSETS_DIR, "pepe_sunglasses.png"),
    os.path.join(ASSETS_DIR, "pepe_suit.png"),
    os.path.join(ASSETS_DIR, "pepe_moon.png"),
    os.path.join(ASSETS_DIR, "pepe_happy.png"),
]


# ─── Fonts ───────────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    import subprocess
    paths = []
    try:
        style = "Bold" if bold else "Regular"
        r = subprocess.run(["fc-list", f":style={style}", "--format=%{file}\n"],
                           capture_output=True, text=True, timeout=3)
        for line in r.stdout.strip().split("\n"):
            fp = line.strip()
            if fp and os.path.exists(fp) and ".ttf" in fp.lower():
                paths.append(fp)
    except Exception:
        pass
    fallbacks = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
         "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
         "/usr/share/fonts/truetype/freefont/FreeSans.ttf"]
    )
    for fp in paths + fallbacks:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _tw(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def _fmt(v: float) -> str:
    if v >= 1_000_000: return f"${v/1_000_000:.2f}M"
    if v >= 1_000:     return f"${v/1_000:.1f}K"
    return f"${v:.0f}"


# ─── Background ───────────────────────────────────────────────────────────────

def _load_bg() -> Image.Image:
    """Load the AI-generated swamp background, or fallback to solid color."""
    if os.path.exists(SWAMP_BG):
        bg = Image.open(SWAMP_BG).convert("RGB")
        bg = bg.resize((W, H), Image.LANCZOS)
        # Slightly darken for better text contrast
        bg = ImageEnhance.Brightness(bg).enhance(0.75)
        return bg
    # Fallback: dark green solid
    img = Image.new("RGB", (W, H), (5, 22, 8))
    return img


def _make_card_base() -> Image.Image:
    """Build the base: swamp bg with dark left panel."""
    bg = _load_bg()

    # Black panel on the far left (behind Pepe)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # Hard dark left edge → fades into swamp
    for x in range(W):
        t = x / W
        if t < 0.08:
            a = 230
        elif t < 0.45:
            a = int(230 * (1 - (t - 0.08) / 0.37) ** 1.2)
        else:
            a = 0
        if a > 0:
            od.line([(x, 0), (x, H)], fill=(0, 0, 0, a))

    # Semi-dark right panel for text readability
    for x in range(int(W * 0.42), W):
        t = (x - W * 0.42) / (W * 0.58)
        a = int(160 * t ** 0.7)
        od.line([(x, 0), (x, H)], fill=(0, 0, 0, a))

    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    return bg


# ─── Pepe character ───────────────────────────────────────────────────────────

def _paste_pepe(img: Image.Image, pepe_path: str) -> Image.Image:
    """Load a Pepe PNG (transparent) and composite it on the left side."""
    if not os.path.exists(pepe_path):
        return img

    pepe = Image.open(pepe_path).convert("RGBA")

    # Target: Pepe fills ~44% of card width, full height with small margin
    target_h = int(H * 0.95)
    target_w = int(W * 0.44)

    # Maintain aspect ratio
    pw, ph = pepe.size
    ratio = min(target_w / pw, target_h / ph)
    new_w = int(pw * ratio)
    new_h = int(ph * ratio)
    pepe = pepe.resize((new_w, new_h), Image.LANCZOS)

    # Position: vertically bottom-aligned, horizontally left
    px = int(W * 0.02)
    py = H - new_h - 5

    # Composite
    canvas = img.convert("RGBA")
    canvas.paste(pepe, (px, py), pepe)
    return canvas.convert("RGB")


# ─── Rounded border ───────────────────────────────────────────────────────────

def _draw_border(draw: ImageDraw.Draw, color=(20, 210, 65)):
    r = 20
    x0, y0, x1, y1 = 5, 5, W - 5, H - 5
    for i in range(5):
        m  = i * 2
        c  = tuple(max(0, v - i * 20) for v in color)
        w  = 2
        draw.arc([x0+m, y0+m, x0+m+2*r, y0+m+2*r], 180, 270, fill=c, width=w)
        draw.arc([x1-m-2*r, y0+m, x1-m, y0+m+2*r], 270, 360, fill=c, width=w)
        draw.arc([x0+m, y1-m-2*r, x0+m+2*r, y1-m], 90, 180, fill=c, width=w)
        draw.arc([x1-m-2*r, y1-m-2*r, x1-m, y1-m], 0, 90, fill=c, width=w)
        draw.line([x0+m+r, y0+m, x1-m-r, y0+m], fill=c, width=w)
        draw.line([x0+m+r, y1-m, x1-m-r, y1-m], fill=c, width=w)
        draw.line([x0+m, y0+m+r, x0+m, y1-m-r], fill=c, width=w)
        draw.line([x1-m, y0+m+r, x1-m, y1-m-r], fill=c, width=w)


# ─── Glow text ────────────────────────────────────────────────────────────────

def _glow_text(draw, pos, text, font, fill, glow, spread=5):
    x, y = pos
    for dx in range(-spread, spread + 1):
        for dy in range(-spread, spread + 1):
            d = math.sqrt(dx * dx + dy * dy)
            if d == 0 or d > spread:
                continue
            a = max(0.0, 1.0 - d / spread)
            gc = tuple(int(c * a) for c in glow)
            draw.text((x + dx, y + dy), text, fill=gc, font=font)
    # Shadow for depth
    draw.text((x + 3, y + 3), text, fill=(0, 0, 0, 120), font=font)
    draw.text((x, y), text, fill=fill, font=font)


# ─── Coin logo ────────────────────────────────────────────────────────────────

def _draw_coin_logo(draw, symbol: str, cx: int, cy: int, r: int = 28):
    draw.ellipse([cx-r-3, cy-r-3, cx+r+3, cy+r+3],
                 fill=(0, 160, 55), outline=None)
    draw.ellipse([cx-r, cy-r, cx+r, cy+r],
                 fill=(8, 32, 12), outline=(0, 210, 75), width=2)
    sym = symbol[:4].upper()
    f   = _font(max(9, r - 9))
    bb  = draw.textbbox((0, 0), sym, font=f)
    tw  = bb[2] - bb[0]
    th  = bb[3] - bb[1]
    draw.text((cx - tw // 2, cy - th // 2), sym, fill=(0, 240, 90), font=f)


# ─── SOL badge ────────────────────────────────────────────────────────────────

def _draw_sol(draw):
    sx, sy, sr = W - 38, 30, 16
    draw.ellipse([sx-sr, sy-sr, sx+sr, sy+sr],
                 fill=(70, 28, 190), outline=(110, 60, 250), width=2)
    f = _font(14)
    bb = draw.textbbox((0, 0), "◎", font=f)
    tw = bb[2] - bb[0]; th = bb[3] - bb[1]
    draw.text((sx - tw//2, sy - th//2), "◎", fill=(210, 200, 255), font=f)


# ─── Main card builder ────────────────────────────────────────────────────────

def _build_card(token: dict, mode: str,
                gain_pct: float = 0,
                called_at: str = "",
                elapsed_str: str = "") -> bytes:

    img  = _make_card_base()

    # Pick a random Pepe variant
    available = [p for p in PEPE_VARIANTS if os.path.exists(p)]
    if available:
        pepe_path = random.choice(available)
        img = _paste_pepe(img, pepe_path)

    draw = ImageDraw.Draw(img)
    _draw_border(draw)

    symbol  = token.get("symbol", "???").upper()
    mc      = token.get("market_cap", 0)
    liq     = token.get("liquidity_usd", 0)
    vol     = token.get("volume_24h", 0)
    ca      = token.get("address", "")
    short   = ca[:8] + "…" + ca[-4:] if len(ca) > 12 else ca

    # Coin logo top center
    _draw_coin_logo(draw, symbol, W // 2, 32, r=28)
    _draw_sol(draw)

    # Right text panel — starts at 45% of width
    rx = int(W * 0.46)
    rw = W - rx - 30

    # Token name — large white bold
    name_sz = 88
    while name_sz > 28:
        if _tw(draw, symbol, _font(name_sz)) <= rw:
            break
        name_sz -= 4

    name_y = 55

    if mode == "call":
        # Token name
        _glow_text(draw, (rx, name_y), symbol,
                   _font(name_sz), (255, 255, 255), (60, 180, 60), 4)

        y = name_y + name_sz + 14
        gap = 36
        lf  = _font(23)
        vf  = _font(23, bold=False)

        # Stats
        pairs = [
            ("MC:",  _fmt(mc)),
            ("Liq:", _fmt(liq)),
            ("Vol:", _fmt(vol)),
        ]
        label_w = 70
        for i, (label, val) in enumerate(pairs):
            draw.text((rx,            y + i * gap), label, fill=(140, 220, 155), font=lf)
            draw.text((rx + label_w,  y + i * gap), val,   fill=(255, 255, 255), font=lf)

        draw.text((rx, y + gap * 3 + 4), f"CA: {short}",
                  fill=(80, 155, 100), font=_font(15, bold=False))

    else:
        # Token name
        _glow_text(draw, (rx, name_y), symbol,
                   _font(name_sz), (255, 255, 255), (60, 180, 60), 4)

        # "called at X"
        sub_y = name_y + name_sz + 8
        draw.text((rx, sub_y), f"called at {called_at}",
                  fill=(185, 225, 195), font=_font(24, bold=False))

        # Giant gain number — neon green glow
        if gain_pct >= 100:
            gain_str = f"{gain_pct / 100 + 1:.1f}X"
        else:
            gain_str = f"{gain_pct:.0f}%"

        g_sz = 148
        while g_sz > 52:
            if _tw(draw, gain_str, _font(g_sz)) <= rw:
                break
            g_sz -= 6

        gy = sub_y + 38
        _glow_text(draw, (rx, gy), gain_str,
                   _font(g_sz), (0, 255, 80), (0, 120, 20), 7)

        # Info
        info_y = gy + g_sz + 14
        draw.text((rx, info_y),      "👤  Alpha Circle",           fill=(210, 240, 218), font=_font(21))
        draw.text((rx, info_y + 34), f"🕐  {elapsed_str or called_at}",
                  fill=(160, 205, 175), font=_font(19, bold=False))

    # Bottom branding
    draw.line([(14, H - 44), (W - 14, H - 44)], fill=(18, 90, 36), width=1)
    bf = _font(14, bold=False)
    draw.text((22,      H - 32), "t.me/AlphaCirclle",  fill=(80, 155, 105), font=bf)
    draw.text((W - 210, H - 32), "@AlphaCirclle",       fill=(80, 155, 105), font=bf)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ─── Public API ──────────────────────────────────────────────────────────────

def generate_initial_call_image(token: dict) -> bytes:
    return _build_card(token, mode="call")


def generate_kol_card(token: dict, gain_pct: float,
                      entry_mc: float, called_at: str,
                      elapsed_str: str = "") -> bytes:
    return _build_card(token, mode="update",
                       gain_pct=gain_pct, called_at=called_at,
                       elapsed_str=elapsed_str)
