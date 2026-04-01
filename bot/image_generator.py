import io
import math
import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

W, H = 1280, 640

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
SWAMP_BG   = os.path.join(ASSETS_DIR, "swamp_bg.png")
PEPE_VARIANTS = [
    os.path.join(ASSETS_DIR, "pepe_sunglasses.png"),
    os.path.join(ASSETS_DIR, "pepe_suit.png"),
    os.path.join(ASSETS_DIR, "pepe_moon.png"),
    os.path.join(ASSETS_DIR, "pepe_happy.png"),
]


# ─── Fonts ─────────────────────────────────────────────────────────────────────

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

def _th(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[3] - bb[1]

def _fmt(v: float) -> str:
    if v >= 1_000_000: return f"${v/1_000_000:.2f}M"
    if v >= 1_000:     return f"${v/1_000:.1f}K"
    return f"${v:.0f}"


# ─── Background ────────────────────────────────────────────────────────────────

def _load_bg() -> Image.Image:
    if os.path.exists(SWAMP_BG):
        bg = Image.open(SWAMP_BG).convert("RGB")
        bg = bg.resize((W, H), Image.LANCZOS)
        bg = ImageEnhance.Brightness(bg).enhance(0.65)
        return bg
    img = Image.new("RGB", (W, H), (5, 18, 8))
    return img


def _make_card_base() -> Image.Image:
    bg = _load_bg()
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # Hard dark left strip (behind Pepe)
    for x in range(W):
        t = x / W
        if t < 0.05:
            a = 240
        elif t < 0.48:
            a = int(240 * (1 - (t - 0.05) / 0.43) ** 1.3)
        else:
            a = 0
        if a > 0:
            od.line([(x, 0), (x, H)], fill=(0, 0, 0, a))

    # Semi-dark right panel for text readability
    for x in range(int(W * 0.44), W):
        t = max(0.0, (x - W * 0.44) / (W * 0.56))
        a = int(170 * t ** 0.6)
        od.line([(x, 0), (x, H)], fill=(0, 0, 0, a))

    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    return bg


# ─── Pepe character ────────────────────────────────────────────────────────────

def _paste_pepe(img: Image.Image, pepe_path: str) -> Image.Image:
    if not os.path.exists(pepe_path):
        return img
    pepe = Image.open(pepe_path).convert("RGBA")
    target_h = int(H * 0.96)
    target_w = int(W * 0.46)
    pw, ph = pepe.size
    ratio = min(target_w / pw, target_h / ph)
    new_w = int(pw * ratio)
    new_h = int(ph * ratio)
    pepe = pepe.resize((new_w, new_h), Image.LANCZOS)
    px = int(W * 0.01)
    py = H - new_h - 4
    canvas = img.convert("RGBA")
    canvas.paste(pepe, (px, py), pepe)
    return canvas.convert("RGB")


# ─── Border ────────────────────────────────────────────────────────────────────

def _draw_border(img: Image.Image) -> Image.Image:
    """Draw a glowing rounded-rectangle border."""
    border = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(border)
    r = 28
    colors = [
        (0, 255, 85, 220),
        (0, 230, 70, 160),
        (0, 200, 55, 100),
        (0, 170, 45, 50),
    ]
    for i, col in enumerate(colors):
        m = i * 2
        bd.rounded_rectangle([m, m, W - 1 - m, H - 1 - m],
                              radius=max(4, r - m),
                              outline=col, width=2)
    blurred = border.filter(ImageFilter.GaussianBlur(2))
    result = Image.alpha_composite(img.convert("RGBA"), blurred)
    # sharp top layer
    sharp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sharp)
    sd.rounded_rectangle([3, 3, W - 4, H - 4], radius=r,
                          outline=(0, 255, 85, 255), width=2)
    result = Image.alpha_composite(result, sharp)
    return result.convert("RGB")


# ─── Glow text ────────────────────────────────────────────────────────────────

def _glow_text(draw, pos, text, font, fill, glow_color, spread=8):
    x, y = pos
    for dx in range(-spread, spread + 1):
        for dy in range(-spread, spread + 1):
            d = math.sqrt(dx * dx + dy * dy)
            if d == 0 or d > spread:
                continue
            a = max(0.0, 1.0 - d / spread) ** 1.5
            gc = tuple(int(c * a) for c in glow_color)
            draw.text((x + dx, y + dy), text, fill=gc, font=font)
    draw.text((x + 3, y + 4), text, fill=(0, 0, 0, 110), font=font)
    draw.text((x, y), text, fill=fill, font=font)


def _shadow_text(draw, pos, text, font, fill):
    x, y = pos
    draw.text((x + 2, y + 3), text, fill=(0, 0, 0, 140), font=font)
    draw.text((x, y), text, fill=fill, font=font)


# ─── Coin icon (top center) ────────────────────────────────────────────────────

def _draw_coin_icon(draw, symbol: str, cx: int, cy: int, r: int = 32):
    draw.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3],
                 fill=(0, 170, 60), outline=None)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                 fill=(8, 28, 12), outline=(0, 220, 80), width=2)
    sym = symbol[:4].upper()
    f = _font(max(10, r - 8))
    bb = draw.textbbox((0, 0), sym, font=f)
    tw = bb[2] - bb[0]; th = bb[3] - bb[1]
    draw.text((cx - tw // 2, cy - th // 2), sym, fill=(0, 255, 90), font=f)


# ─── Solana badge (top right) ─────────────────────────────────────────────────

def _draw_sol_badge(draw):
    sx, sy, sr = W - 44, 34, 18
    draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr],
                 fill=(65, 24, 190), outline=(115, 65, 255), width=2)
    f = _font(15)
    bb = draw.textbbox((0, 0), "◎", font=f)
    tw = bb[2] - bb[0]; th = bb[3] - bb[1]
    draw.text((sx - tw // 2, sy - th // 2), "◎", fill=(215, 205, 255), font=f)


# ─── Card builder ─────────────────────────────────────────────────────────────

def _build_card(token: dict, mode: str,
                gain_pct: float = 0,
                called_at: str = "",
                elapsed_str: str = "") -> bytes:

    img = _make_card_base()

    # Paste Pepe on left
    available = [p for p in PEPE_VARIANTS if os.path.exists(p)]
    if available:
        img = _paste_pepe(img, random.choice(available))

    # Glowing border
    img = _draw_border(img)

    draw = ImageDraw.Draw(img)

    symbol = token.get("symbol", "???").upper()
    mc     = token.get("market_cap", 0)
    liq    = token.get("liquidity_usd", 0)
    vol    = token.get("volume_24h", 0)
    ca     = token.get("address", "")
    short  = ca[:8] + "…" + ca[-4:] if len(ca) > 12 else ca

    # Top decorations
    _draw_coin_icon(draw, symbol, W // 2, 36, r=32)
    _draw_sol_badge(draw)

    # Right panel starts at 47% of width
    rx = int(W * 0.47)
    rw = W - rx - 50   # usable width for right panel text

    if mode == "call":
        # ── INITIAL CALL CARD ──────────────────────────────────────────────────

        # Token name — large, bold, white
        name_sz = 110
        while name_sz > 32:
            if _tw(draw, symbol, _font(name_sz)) <= rw:
                break
            name_sz -= 5
        name_y = 60
        _glow_text(draw, (rx, name_y), symbol,
                   _font(name_sz), (255, 255, 255), (40, 160, 55), 5)

        # Stats block
        y = name_y + name_sz + 20
        lf = _font(26)
        vf = _font(26, bold=False)
        gap = 44
        label_w = 85
        pairs = [
            ("MC:",  _fmt(mc)),
            ("Liq:", _fmt(liq)),
            ("Vol:", _fmt(vol)),
        ]
        for i, (label, val) in enumerate(pairs):
            _shadow_text(draw, (rx, y + i * gap),            label, lf, (100, 210, 130))
            _shadow_text(draw, (rx + label_w, y + i * gap),  val,   vf, (240, 255, 245))

        draw.text((rx, y + gap * 3 + 6), f"CA: {short}",
                  fill=(70, 140, 95), font=_font(17, bold=False))

        # NEW CALL badge
        badge_x = rx
        badge_y = y + gap * 3 + 48
        badge_text = "🟢  NEW CALL"
        badge_f = _font(22)
        bw = _tw(draw, badge_text, badge_f) + 28
        bh = 40
        draw.rounded_rectangle([badge_x, badge_y, badge_x + bw, badge_y + bh],
                                radius=10, fill=(0, 130, 45, 200))
        draw.text((badge_x + 14, badge_y + 9), badge_text,
                  fill=(255, 255, 255), font=badge_f)

    else:
        # ── GAIN UPDATE CARD ───────────────────────────────────────────────────

        # Token name
        name_sz = 110
        while name_sz > 32:
            if _tw(draw, symbol, _font(name_sz)) <= rw:
                break
            name_sz -= 5
        name_y = 52
        _glow_text(draw, (rx, name_y), symbol,
                   _font(name_sz), (255, 255, 255), (40, 160, 55), 5)

        # "called at X.XK"
        sub_y = name_y + name_sz + 6
        _shadow_text(draw, (rx, sub_y), f"called at {called_at}",
                     _font(28, bold=False), (190, 220, 200))

        # Giant gain number — the hero element
        if gain_pct >= 100:
            gain_str = f"{gain_pct / 100 + 1:.1f}X"
        else:
            gain_str = f"{gain_pct:.0f}%"

        g_sz = 200
        while g_sz > 60:
            if _tw(draw, gain_str, _font(g_sz)) <= rw:
                break
            g_sz -= 8

        gy = sub_y + 46
        _glow_text(draw, (rx, gy), gain_str,
                   _font(g_sz), (0, 255, 80), (0, 140, 30), 10)

        # Info rows
        info_y = gy + g_sz + 18
        info_f  = _font(26)
        time_f  = _font(24, bold=False)
        _shadow_text(draw, (rx, info_y),      f"👤  Alpha Circle",               info_f, (215, 245, 225))
        _shadow_text(draw, (rx, info_y + 42), f"🕐  {elapsed_str or called_at}", time_f, (165, 210, 185))

    # Bottom branding line
    draw.line([(18, H - 50), (W - 18, H - 50)], fill=(14, 80, 32), width=1)
    bf = _font(16, bold=False)
    draw.text((28,      H - 38), "t.me/AlphaCirclle",  fill=(70, 145, 100), font=bf)
    draw.text((W - 220, H - 38), "@AlphaCirclle",       fill=(70, 145, 100), font=bf)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_initial_call_image(token: dict) -> bytes:
    return _build_card(token, mode="call")


def generate_kol_card(token: dict, gain_pct: float,
                      entry_mc: float, called_at: str,
                      elapsed_str: str = "") -> bytes:
    return _build_card(token, mode="update",
                       gain_pct=gain_pct, called_at=called_at,
                       elapsed_str=elapsed_str)
