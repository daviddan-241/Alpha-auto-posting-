import io
import math
import random
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 900, 500

# ─── Fonts ──────────────────────────────────────────────────────────────────

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
    if bold:
        fallbacks = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]
    else:
        fallbacks = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    for fp in paths + fallbacks:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _text_w(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def _text_h(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[3] - bb[1]


def _fmt(v: float) -> str:
    if v >= 1_000_000: return f"${v/1_000_000:.2f}M"
    if v >= 1_000:     return f"${v/1_000:.1f}K"
    return f"${v:.0f}"


# ─── Dark swamp background ────────────────────────────────────────────────────

def _make_bg() -> Image.Image:
    img = Image.new("RGB", (W, H), (4, 14, 6))
    draw = ImageDraw.Draw(img)

    # Sky-to-ground gradient (very dark green)
    for y in range(H):
        t = y / H
        r = int(3 + t * 10)
        g = int(12 + t * 22)
        b = int(4 + t * 8)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Background tree silhouettes (tall, thin)
    for _ in range(28):
        tx = random.randint(0, W)
        th = random.randint(H // 2, H - 30)
        tw = random.randint(3, 9)
        col = (random.randint(4, 12), random.randint(24, 42), random.randint(5, 16))
        draw.rectangle([tx, H - th, tx + tw, H], fill=col)
        # tree top
        cr = random.randint(18, 38)
        draw.ellipse([tx - cr + tw // 2, H - th - cr,
                      tx + cr + tw // 2, H - th + cr // 2], fill=col)

    # Fog/mist layers near bottom
    for _ in range(6):
        cx = random.randint(-50, W + 50)
        cy = random.randint(H * 2 // 3, H)
        rx = random.randint(120, 280)
        ry = random.randint(20, 55)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.ellipse([cx - rx, cy - ry, cx + rx, cy + ry],
                   fill=(8, 55, 16, 28))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

    draw = ImageDraw.Draw(img)

    # Water/ground reeds
    for _ in range(22):
        rx = random.randint(0, W)
        rh = random.randint(40, 130)
        rw = random.randint(2, 5)
        col = (random.randint(6, 16), random.randint(32, 56), random.randint(8, 22))
        draw.rectangle([rx, H - rh, rx + rw, H], fill=col)
        leaf_y = H - rh + random.randint(8, 25)
        lw = random.randint(8, 22)
        draw.ellipse([rx - lw, leaf_y - 4, rx + lw + rw, leaf_y + 9],
                     fill=(random.randint(10, 22), random.randint(40, 68), random.randint(10, 26)))

    # Water lily pads
    for _ in range(14):
        lx = random.randint(0, W)
        ly = random.randint(H * 3 // 4, H)
        lr = random.randint(6, 16)
        draw.ellipse([lx - lr, ly - lr // 2, lx + lr, ly + lr // 2],
                     fill=(random.randint(10, 26), random.randint(52, 90), random.randint(12, 30)))

    return img


# ─── Pepe frog character (left side, large) ───────────────────────────────────

def _draw_frog(img: Image.Image, cx: int, cy: int, size: int) -> Image.Image:
    draw = ImageDraw.Draw(img)

    def ell(x0, y0, x1, y1, fill, outline=None, width=0):
        if outline:
            draw.ellipse([x0, y0, x1, y1], fill=outline)
            m = width
            draw.ellipse([x0 + m, y0 + m, x1 - m, y1 - m], fill=fill)
        else:
            draw.ellipse([x0, y0, x1, y1], fill=fill)

    MID   = (58, 148, 52)
    DARK  = (34, 100, 32)
    LIGHT = (84, 180, 68)
    BELLY = (108, 168, 88)
    HOOD  = (22, 28, 24)
    EW    = (235, 235, 215)
    PUP   = (18, 18, 18)
    RED   = (190, 80, 70)

    s  = size
    hr = int(s * 0.37)
    hy = cy - int(s * 0.05)

    # Body / hoodie
    bw = int(s * 0.50)
    bh = int(s * 0.42)
    by = cy + int(s * 0.20)
    draw.ellipse([cx - bw, by - bh // 2, cx + bw, by + bh], fill=HOOD)
    draw.ellipse([cx - int(s * 0.17), by - int(s * 0.26),
                  cx + int(s * 0.17), by + int(s * 0.04)], fill=HOOD)

    # Arms hanging down
    for side in (-1, 1):
        ax = cx + side * int(s * 0.45)
        ay = by
        arm_w = int(s * 0.14)
        arm_h = int(s * 0.30)
        draw.ellipse([ax - arm_w, ay, ax + arm_w, ay + arm_h], fill=HOOD)
        hand_r = int(s * 0.10)
        draw.ellipse([ax - hand_r, ay + arm_h - hand_r,
                      ax + hand_r, ay + arm_h + hand_r], fill=MID)

    # Head
    ell(cx - hr, hy - hr, cx + hr, hy + hr, MID, DARK, 3)
    fh = int(hr * 0.42)
    fw = int(hr * 0.52)
    draw.ellipse([cx - fw, hy - hr + 4, cx + fw, hy - hr + 4 + fh], fill=LIGHT)

    # Eyes
    er  = int(s * 0.130)
    ey  = hy - int(hr * 0.15)
    exL = cx - int(hr * 0.38)
    exR = cx + int(hr * 0.38)
    for ex in (exL, exR):
        ell(ex - er - 2, ey - er - 2, ex + er + 2, ey + er + 2, DARK)
        ell(ex - er, ey - er, ex + er, ey + er, EW)
        pr = int(er * 0.56)
        ell(ex - pr, ey - pr, ex + pr, ey + pr, PUP)
        sr = max(2, int(er * 0.20))
        draw.ellipse([ex - pr + 2, ey - pr + 2,
                      ex - pr + 2 + sr * 2, ey - pr + 2 + sr * 2],
                     fill=(255, 255, 255))

    # Nose
    nr = int(s * 0.026)
    ny = hy + int(hr * 0.15)
    for nx in (cx - int(s * 0.065), cx + int(s * 0.065)):
        draw.ellipse([nx - nr, ny - nr, nx + nr, ny + nr], fill=DARK)

    # Mouth
    mw = int(hr * 0.70)
    my = hy + int(hr * 0.47)
    mh = int(s * 0.11)
    draw.ellipse([cx - mw, my - mh // 2, cx + mw, my + mh], fill=BELLY)
    draw.arc([cx - mw + 4, my - mh, cx + mw - 4, my + int(mh * 0.55)],
             start=8, end=172, fill=RED, width=max(2, int(s * 0.024)))
    draw.arc([cx - mw + 4, my - mh // 2, cx + mw - 4, my + int(mh * 1.1)],
             start=0, end=180, fill=DARK, width=max(2, int(s * 0.017)))

    # Cheeks blush
    for chx in (cx - int(hr * 0.70), cx + int(hr * 0.70)):
        cov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cod = ImageDraw.Draw(cov)
        chy = hy + int(hr * 0.28)
        cr  = int(s * 0.085)
        cod.ellipse([chx - cr, chy - cr // 2, chx + cr, chy + cr // 2],
                    fill=(175, 55, 55, 42))
        img = Image.alpha_composite(img.convert("RGBA"), cov).convert("RGB")
        draw = ImageDraw.Draw(img)

    return img


# ─── Coin logo circle ─────────────────────────────────────────────────────────

def _coin_logo(draw, symbol: str, cx: int, cy: int, r: int = 32):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                 fill=(12, 40, 16), outline=(0, 210, 80), width=2)
    sym = (symbol[:4]).upper()
    try:
        f   = _font(max(10, r - 8))
        tw  = _text_w(draw, sym, f)
        bb  = draw.textbbox((0, 0), sym, font=f)
        th  = bb[3] - bb[1]
        draw.text((cx - tw // 2, cy - th // 2), sym, fill=(0, 240, 90), font=f)
    except Exception:
        pass


# ─── SOL badge ────────────────────────────────────────────────────────────────

def _sol_badge(draw):
    x, y, r = W - 40, 32, 16
    draw.ellipse([x - r, y - r, x + r, y + r], fill=(80, 36, 195),
                 outline=(120, 72, 255), width=2)
    draw.text((x - 10, y - 8), "◎", fill=(255, 255, 255), font=_font(13))


# ─── Glow text helper ─────────────────────────────────────────────────────────

def _draw_glow_text(draw, pos, text, font, fill, glow_color, glow_range=3):
    x, y = pos
    for dx in range(-glow_range, glow_range + 1):
        for dy in range(-glow_range, glow_range + 1):
            if dx == 0 and dy == 0:
                continue
            alpha = max(0, 1 - (abs(dx) + abs(dy)) / (glow_range * 2))
            gc = tuple(int(c * alpha) for c in glow_color)
            draw.text((x + dx, y + dy), text, fill=gc, font=font)
    draw.text((x, y), text, fill=fill, font=font)


# ─── Border glow ─────────────────────────────────────────────────────────────

def _border(draw, color=(25, 200, 70)):
    for i in range(5):
        m = i * 2
        c = tuple(max(0, v - i * 22) for v in color)
        draw.rectangle([5 + m, 5 + m, W - 5 - m, H - 5 - m],
                       outline=c, width=2)


# ─── Main card builder ────────────────────────────────────────────────────────

def _build_card(
    token: dict,
    mode: str,
    gain_pct: float = 0,
    called_at: str = "",
) -> bytes:
    img  = _make_bg()

    # Draw Pepe on the left third
    frog_cx = int(W * 0.235)
    frog_cy = int(H * 0.56)
    frog_sz = int(H * 0.92)
    img = _draw_frog(img, cx=frog_cx, cy=frog_cy, size=frog_sz)

    draw = ImageDraw.Draw(img)

    # Dark gradient overlay on right side for text readability
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    split = int(W * 0.40)
    for x in range(split, W):
        a = int(185 * ((x - split) / (W - split)) ** 0.55)
        od.line([(x, 0), (x, H)], fill=(0, 0, 0, a))
    img  = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    draw = ImageDraw.Draw(img)

    _border(draw)

    symbol  = token.get("symbol", "???").upper()
    name    = token.get("name", symbol)
    mc      = token.get("market_cap", 0)
    liq     = token.get("liquidity_usd", 0)
    vol     = token.get("volume_24h", 0)
    ca      = token.get("address", "")

    # Coin logo top-center between frog and text
    logo_cx = int(W * 0.47)
    _coin_logo(draw, symbol, logo_cx, 34)
    _sol_badge(draw)

    # Right text panel
    rx = int(W * 0.44)
    rw = W - rx - 22

    # ── Token name (large white bold) ─────────────────────────────────────
    name_sz = 80
    while name_sz > 26:
        f = _font(name_sz)
        if _text_w(draw, symbol, f) <= rw:
            break
        name_sz -= 4

    name_y = 62
    _draw_glow_text(draw, (rx, name_y), symbol,
                    _font(name_sz), (255, 255, 255), (80, 200, 80), 4)

    if mode == "call":
        # NEW CALL badge
        badge_rect = [rx, 20, rx + 130, 48]
        draw.rectangle(badge_rect, fill=(0, 110, 210))
        draw.text((rx + 10, 24), "🚀 NEW CALL", fill=(255, 255, 255), font=_font(17))

        y = name_y + name_sz + 14
        sf = _font(21)
        draw.text((rx, y),       f"MC:    {_fmt(mc)}",   fill=(160, 230, 175), font=sf)
        draw.text((rx, y + 32),  f"Liq:    {_fmt(liq)}", fill=(160, 230, 175), font=sf)
        draw.text((rx, y + 64),  f"Vol:   {_fmt(vol)}",  fill=(160, 230, 175), font=sf)
        short = ca[:8] + "…" + ca[-4:] if len(ca) > 12 else ca
        draw.text((rx, y + 100), f"CA: {short}", fill=(100, 170, 120), font=_font(15))

    else:  # update / gain card
        # "called at X" subtitle
        cat_txt = f"called at {called_at}"
        draw.text((rx, name_y + name_sz + 8), cat_txt,
                  fill=(180, 220, 195), font=_font(22, bold=False))

        # Big gain number — neon green glow
        if gain_pct >= 100:
            gain_str = f"{gain_pct / 100 + 1:.1f}X"
        else:
            gain_str = f"{gain_pct:.0f}%"

        g_sz = 130
        while g_sz > 52:
            if _text_w(draw, gain_str, _font(g_sz)) <= rw:
                break
            g_sz -= 6

        gy = name_y + name_sz + 52
        _draw_glow_text(draw, (rx, gy), gain_str,
                        _font(g_sz), (0, 255, 90), (0, 120, 30), 5)

        # Info row — person icon + Alpha Circle name + clock + time
        elapsed = ""  # filled in by caller if needed
        info_y = gy + g_sz + 16
        icon_f = _font(19, bold=False)
        draw.text((rx, info_y),      "👤  Alpha Circle",          fill=(210, 235, 215), font=icon_f)
        draw.text((rx, info_y + 30), f"🕐  Entry: {called_at}",   fill=(165, 205, 175), font=_font(17, bold=False))

    # ── Bottom branding bar ────────────────────────────────────────────────
    draw.line([(12, H - 46), (W - 12, H - 46)], fill=(22, 100, 44), width=1)
    bf = _font(14, bold=False)
    draw.text((20,      H - 34), "t.me/AlphaCirclle",   fill=(100, 170, 120), font=bf)
    draw.text((W - 200, H - 34), "@AlphaCirclle",        fill=(100, 170, 120), font=bf)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ─── Public API ──────────────────────────────────────────────────────────────

def generate_initial_call_image(token: dict) -> bytes:
    return _build_card(token, mode="call")


def generate_kol_card(token: dict, gain_pct: float,
                      entry_mc: float, called_at: str) -> bytes:
    return _build_card(token, mode="update",
                       gain_pct=gain_pct, called_at=called_at)
