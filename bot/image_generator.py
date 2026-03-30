import io
import math
import random
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
W, H = 800, 440


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    import subprocess
    candidates = []
    try:
        result = subprocess.run(
            ["fc-list", ":style=Bold", "--format=%{file}\n"],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.strip().split("\n"):
            fp = line.strip()
            if fp and os.path.exists(fp) and ".ttf" in fp.lower():
                candidates.append(fp)
    except Exception:
        pass
    fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for fp in candidates + fallbacks:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_text_centered(draw, text, x, y, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((x - tw // 2, y), text, fill=fill, font=font)


def _fmt_mc(v: float) -> str:
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.1f}K"
    return f"${v:.0f}"


# ─── STYLE 1: Swamp / Pepe dark green ───────────────────────────────────────

def _make_swamp_bg() -> Image.Image:
    img = Image.new("RGB", (W, H), (8, 20, 10))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        r = int(5 + (y / H) * 12)
        g = int(14 + (y / H) * 28)
        b = int(7 + (y / H) * 14)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    for _ in range(5):
        cx = random.randint(0, W)
        cy = random.randint(H // 3, H)
        for layer in range(10):
            rx = random.randint(80, 200) + layer * 4
            ry = random.randint(30, 70) + layer * 2
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=(5, random.randint(35,65), 12, 16))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    for _ in range(7):
        tx = random.randint(0, W)
        ty = random.randint(H // 4, H // 2)
        tw = random.randint(4, 12)
        th = random.randint(60, 120)
        draw.rectangle([tx-tw//2, ty-th, tx+tw//2, ty], fill=(7, random.randint(28,45), 11))
    return img


def _card_swamp(token, gain_pct, entry_mc, called_at, mode="update") -> bytes:
    img = _make_swamp_bg()
    draw = ImageDraw.Draw(img)
    for i in range(4):
        col = (30, 200, 80) if i < 2 else (10, 80, 30)
        m = i * 2
        draw.rectangle([6+m, 6+m, W-6-m, H-6-m], outline=col, width=2)

    symbol = token.get("symbol", "???").upper()
    name   = token.get("name", symbol)
    mc     = token.get("market_cap", 0)
    liq    = token.get("liquidity_usd", 0)
    ca     = token.get("address", "")
    short  = ca[:8] + "…" + ca[-4:] if len(ca) > 12 else ca

    NEON   = (0, 255, 100)
    WHITE  = (240, 250, 240)
    SOFT   = (180, 220, 185)

    if mode == "update":
        gain_str = f"{gain_pct/100+1:.1f}X" if gain_pct >= 100 else f"+{gain_pct:.0f}%"
        badge = "📈 GAIN UPDATE"
        badge_col = (0, 170, 60)
    else:
        gain_str = None
        badge = "🚀 NEW CALL"
        badge_col = (0, 120, 220)

    draw.rectangle([20, 16, 200, 46], fill=badge_col)
    draw.text((28, 18), badge, fill=(255, 255, 255), font=_get_font(17))

    name_sz = min(72, max(34, int(72 * 7 / max(len(symbol), 1))))
    draw.text((28, 55), symbol, fill=WHITE, font=_get_font(name_sz))

    if gain_str:
        gf = _get_font(min(100, max(56, int(100 * 4 / max(len(gain_str), 1)))))
        for dx, dy in [(-2,-2),(2,-2),(-2,2),(2,2)]:
            draw.text((28+dx, 150+dy), gain_str, fill=(0,90,35), font=gf)
        draw.text((28, 150), gain_str, fill=NEON, font=gf)

    mf = _get_font(20)
    if mode == "update":
        draw.text((28, H-130), f"Entry:   {called_at}", fill=SOFT, font=mf)
        draw.text((28, H-105), f"Now:    {_fmt_mc(mc)}", fill=NEON, font=mf)
        draw.text((28, H-80),  f"Liq:     {_fmt_mc(liq)}", fill=SOFT, font=mf)
    else:
        vol = token.get("volume_24h", 0)
        draw.text((28, H-130), f"MC:    {_fmt_mc(mc)}", fill=SOFT, font=mf)
        draw.text((28, H-105), f"Liq:   {_fmt_mc(liq)}", fill=NEON, font=mf)
        draw.text((28, H-80),  f"Vol:   {_fmt_mc(vol)}", fill=SOFT, font=mf)

    draw.text((28, H-55), f"CA: {short}", fill=(130, 190, 140), font=_get_font(15))
    draw.line([(18, H-62), (W-18, H-62)], fill=(30,100,50), width=1)
    draw.text((W-240, H-35), "t.me/AlphaCirclle", fill=(120,180,130), font=_get_font(14))
    draw.text((28,   H-35), "Alpha Circle 🐸", fill=(120,180,130), font=_get_font(14))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ─── STYLE 2: Neon / Cyberpunk purple-pink ──────────────────────────────────

def _card_neon(token, gain_pct, entry_mc, called_at, mode="update") -> bytes:
    img = Image.new("RGB", (W, H), (6, 4, 20))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        r = int(6 + (y/H) * 10)
        g = int(4 + (y/H) * 6)
        b = int(20 + (y/H) * 22)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    for _ in range(3):
        cx = random.randint(0, W)
        cy = random.randint(0, H)
        for r in range(80, 0, -10):
            col = (random.randint(80,160), 0, random.randint(180,255), max(0, r//6))
            overlay = Image.new("RGBA", (W, H), (0,0,0,0))
            od = ImageDraw.Draw(overlay)
            od.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(*col[:3], max(0,r//5)))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    PINK  = (255, 0, 180)
    CYAN  = (0, 230, 255)
    WHITE = (240, 235, 255)
    SOFT  = (180, 160, 220)

    symbol = token.get("symbol", "???").upper()
    mc  = token.get("market_cap", 0)
    liq = token.get("liquidity_usd", 0)
    ca  = token.get("address", "")
    short = ca[:8] + "…" + ca[-4:] if len(ca) > 12 else ca

    if mode == "update":
        gain_str = f"{gain_pct/100+1:.1f}X" if gain_pct >= 100 else f"+{gain_pct:.0f}%"
        badge = "⚡ GAIN UPDATE"
        badge_col = (140, 0, 200)
    else:
        gain_str = None
        badge = "🚀 ALPHA CALL"
        badge_col = (0, 80, 200)

    draw.rectangle([20, 16, 240, 46], fill=badge_col)
    draw.text((28, 19), badge, fill=WHITE, font=_get_font(17))

    name_sz = min(76, max(36, int(76 * 7 / max(len(symbol), 1))))
    for dx, dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
        draw.text((28+dx, 55+dy), symbol, fill=(120,0,90), font=_get_font(name_sz))
    draw.text((28, 55), symbol, fill=PINK, font=_get_font(name_sz))

    if gain_str:
        gf = _get_font(min(104, max(60, int(104 * 4 / max(len(gain_str), 1)))))
        for dx, dy in [(-2,-2),(2,2)]:
            draw.text((28+dx, 155+dy), gain_str, fill=(0,80,120), font=gf)
        draw.text((28, 155), gain_str, fill=CYAN, font=gf)

    mf = _get_font(20)
    if mode == "update":
        draw.text((28, H-130), f"Entry:  {called_at}", fill=SOFT, font=mf)
        draw.text((28, H-105), f"Now:   {_fmt_mc(mc)}", fill=CYAN, font=mf)
        draw.text((28, H-80),  f"Liq:    {_fmt_mc(liq)}", fill=SOFT, font=mf)
    else:
        vol = token.get("volume_24h", 0)
        draw.text((28, H-130), f"MC:   {_fmt_mc(mc)}", fill=SOFT, font=mf)
        draw.text((28, H-105), f"Liq:  {_fmt_mc(liq)}", fill=CYAN, font=mf)
        draw.text((28, H-80),  f"Vol:  {_fmt_mc(vol)}", fill=SOFT, font=mf)

    draw.text((28, H-55), f"CA: {short}", fill=(130, 110, 200), font=_get_font(15))
    draw.line([(18, H-62), (W-18, H-62)], fill=(80,0,160), width=1)
    draw.text((W-240, H-35), "t.me/AlphaCirclle", fill=SOFT, font=_get_font(14))
    draw.text((28,   H-35), "Alpha Circle ⚡", fill=PINK, font=_get_font(14))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ─── STYLE 3: Fire / Lava orange-red ────────────────────────────────────────

def _card_fire(token, gain_pct, entry_mc, called_at, mode="update") -> bytes:
    img = Image.new("RGB", (W, H), (15, 5, 2))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        r = int(15 + (y/H) * 35)
        g = int(5 + (y/H) * 15)
        b = int(2 + (y/H) * 4)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    for _ in range(40):
        x = random.randint(0, W)
        y = random.randint(H//2, H)
        r = random.randint(3, 25)
        alpha = random.randint(10, 50)
        overlay = Image.new("RGBA", (W, H), (0,0,0,0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([x-r, y-r*2, x+r, y], fill=(random.randint(200,255), random.randint(60,150), 0, alpha))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    ORANGE = (255, 120, 0)
    YELLOW = (255, 220, 0)
    WHITE  = (255, 245, 230)
    SOFT   = (220, 160, 120)

    symbol = token.get("symbol", "???").upper()
    mc  = token.get("market_cap", 0)
    liq = token.get("liquidity_usd", 0)
    ca  = token.get("address", "")
    short = ca[:8] + "…" + ca[-4:] if len(ca) > 12 else ca

    if mode == "update":
        gain_str = f"{gain_pct/100+1:.1f}X" if gain_pct >= 100 else f"+{gain_pct:.0f}%"
        badge = "🔥 PUMPING"
        badge_col = (180, 40, 0)
    else:
        gain_str = None
        badge = "🔥 HOT CALL"
        badge_col = (160, 60, 0)

    for i in range(3):
        m = i * 2
        draw.rectangle([6+m, 6+m, W-6-m, H-6-m], outline=ORANGE, width=2)

    draw.rectangle([20, 16, 200, 46], fill=badge_col)
    draw.text((28, 19), badge, fill=YELLOW, font=_get_font(17))

    name_sz = min(72, max(34, int(72 * 7 / max(len(symbol), 1))))
    for dx, dy in [(-2,-2),(2,2)]:
        draw.text((28+dx, 55+dy), symbol, fill=(100,30,0), font=_get_font(name_sz))
    draw.text((28, 55), symbol, fill=YELLOW, font=_get_font(name_sz))

    if gain_str:
        gf = _get_font(min(104, max(60, int(104 * 4 / max(len(gain_str), 1)))))
        for dx, dy in [(-2,-2),(2,2)]:
            draw.text((28+dx, 155+dy), gain_str, fill=(100,30,0), font=gf)
        draw.text((28, 155), gain_str, fill=ORANGE, font=gf)

    mf = _get_font(20)
    if mode == "update":
        draw.text((28, H-130), f"Entry:  {called_at}", fill=SOFT, font=mf)
        draw.text((28, H-105), f"Now:   {_fmt_mc(mc)}", fill=YELLOW, font=mf)
        draw.text((28, H-80),  f"Liq:    {_fmt_mc(liq)}", fill=SOFT, font=mf)
    else:
        vol = token.get("volume_24h", 0)
        draw.text((28, H-130), f"MC:   {_fmt_mc(mc)}", fill=SOFT, font=mf)
        draw.text((28, H-105), f"Liq:  {_fmt_mc(liq)}", fill=YELLOW, font=mf)
        draw.text((28, H-80),  f"Vol:  {_fmt_mc(vol)}", fill=SOFT, font=mf)

    draw.text((28, H-55), f"CA: {short}", fill=(220, 140, 80), font=_get_font(15))
    draw.line([(18, H-62), (W-18, H-62)], fill=(160, 60, 0), width=1)
    draw.text((W-240, H-35), "t.me/AlphaCirclle", fill=SOFT, font=_get_font(14))
    draw.text((28,   H-35), "Alpha Circle 🔥", fill=ORANGE, font=_get_font(14))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ─── STYLE 4: Matrix / Dark teal grid ───────────────────────────────────────

def _card_matrix(token, gain_pct, entry_mc, called_at, mode="update") -> bytes:
    img = Image.new("RGB", (W, H), (2, 8, 6))
    draw = ImageDraw.Draw(img)
    TEAL  = (0, 210, 180)
    LTEAL = (0, 255, 220)
    WHITE = (220, 255, 250)
    SOFT  = (140, 200, 190)

    for x in range(0, W, 24):
        draw.line([(x, 0), (x, H)], fill=(0, 30, 25), width=1)
    for y in range(0, H, 24):
        draw.line([(0, y), (W, y)], fill=(0, 30, 25), width=1)

    for _ in range(20):
        x = random.randint(0, W)
        y = random.randint(0, H)
        char = random.choice("01アイウエオカキ01")
        col = (0, random.randint(150, 255), random.randint(130, 220), random.randint(20, 60))
        overlay = Image.new("RGBA", (W, H), (0,0,0,0))
        od = ImageDraw.Draw(overlay)
        try:
            od.text((x, y), char, fill=col, font=_get_font(random.randint(10, 22)))
        except Exception:
            pass
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    for i in range(3):
        m = i * 2
        draw.rectangle([6+m, 6+m, W-6-m, H-6-m], outline=TEAL, width=2)

    symbol = token.get("symbol", "???").upper()
    mc  = token.get("market_cap", 0)
    liq = token.get("liquidity_usd", 0)
    ca  = token.get("address", "")
    short = ca[:8] + "…" + ca[-4:] if len(ca) > 12 else ca

    if mode == "update":
        gain_str = f"{gain_pct/100+1:.1f}X" if gain_pct >= 100 else f"+{gain_pct:.0f}%"
        badge = "▶ SIGNAL HIT"
        badge_col = (0, 90, 80)
    else:
        gain_str = None
        badge = "▶ SIGNAL FOUND"
        badge_col = (0, 70, 110)

    draw.rectangle([20, 16, 240, 46], fill=badge_col)
    draw.text((28, 19), badge, fill=LTEAL, font=_get_font(17))

    name_sz = min(72, max(34, int(72 * 7 / max(len(symbol), 1))))
    for dx, dy in [(-2,-2),(2,2)]:
        draw.text((28+dx, 55+dy), symbol, fill=(0,60,50), font=_get_font(name_sz))
    draw.text((28, 55), symbol, fill=WHITE, font=_get_font(name_sz))

    if gain_str:
        gf = _get_font(min(104, max(60, int(104 * 4 / max(len(gain_str), 1)))))
        for dx, dy in [(-2,-2),(2,2)]:
            draw.text((28+dx, 155+dy), gain_str, fill=(0,60,50), font=gf)
        draw.text((28, 155), gain_str, fill=LTEAL, font=gf)

    mf = _get_font(20)
    if mode == "update":
        draw.text((28, H-130), f"Entry:  {called_at}", fill=SOFT, font=mf)
        draw.text((28, H-105), f"Now:   {_fmt_mc(mc)}", fill=LTEAL, font=mf)
        draw.text((28, H-80),  f"Liq:    {_fmt_mc(liq)}", fill=SOFT, font=mf)
    else:
        vol = token.get("volume_24h", 0)
        draw.text((28, H-130), f"MC:   {_fmt_mc(mc)}", fill=SOFT, font=mf)
        draw.text((28, H-105), f"Liq:  {_fmt_mc(liq)}", fill=LTEAL, font=mf)
        draw.text((28, H-80),  f"Vol:  {_fmt_mc(vol)}", fill=SOFT, font=mf)

    draw.text((28, H-55), f"CA: {short}", fill=(80, 180, 160), font=_get_font(15))
    draw.line([(18, H-62), (W-18, H-62)], fill=(0, 100, 90), width=1)
    draw.text((W-240, H-35), "t.me/AlphaCirclle", fill=SOFT, font=_get_font(14))
    draw.text((28,   H-35), "Alpha Circle ◈", fill=TEAL, font=_get_font(14))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ─── Public interface ────────────────────────────────────────────────────────

CARD_STYLES = [_card_swamp, _card_neon, _card_fire, _card_matrix]


def generate_kol_card(token: dict, gain_pct: float, entry_mc: float, called_at: str) -> bytes:
    style = random.choice(CARD_STYLES)
    return style(token, gain_pct, entry_mc, called_at, mode="update")


def generate_initial_call_image(token: dict) -> bytes:
    style = random.choice(CARD_STYLES)
    return style(token, 0, None, None, mode="call")
