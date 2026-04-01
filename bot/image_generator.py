import io
import math
import random
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 820, 440

# ─── Fonts ──────────────────────────────────────────────────────────────────

def _font(size: int) -> ImageFont.FreeTypeFont:
    import subprocess
    paths = []
    try:
        r = subprocess.run(["fc-list", ":style=Bold", "--format=%{file}\n"],
                           capture_output=True, text=True, timeout=3)
        for line in r.stdout.strip().split("\n"):
            fp = line.strip()
            if fp and os.path.exists(fp) and ".ttf" in fp.lower():
                paths.append(fp)
    except Exception:
        pass
    fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
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


def _fmt(v: float) -> str:
    if v >= 1_000_000: return f"${v/1_000_000:.2f}M"
    if v >= 1_000:     return f"${v/1_000:.1f}K"
    return f"${v:.0f}"


# ─── Swamp background ────────────────────────────────────────────────────────

def _make_bg() -> Image.Image:
    img  = Image.new("RGB", (W, H), (6, 18, 8))
    draw = ImageDraw.Draw(img)

    # Vertical gradient — slightly lighter at bottom (water)
    for y in range(H):
        t = y / H
        r = int(6 + t * 14)
        g = int(18 + t * 24)
        b = int(8 + t * 10)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Atmospheric fog blobs
    for _ in range(7):
        cx = random.randint(20, W - 20)
        cy = random.randint(H // 3, H)
        for layer in range(14):
            rx = random.randint(90, 220) + layer * 5
            ry = random.randint(25, 65) + layer * 2
            al = max(0, 22 - layer * 1.5)
            gv = random.randint(40, 70)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            od.ellipse([cx-rx, cy-ry, cx+rx, cy+ry],
                       fill=(8, gv, 14, int(al)))
            img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

    draw = ImageDraw.Draw(img)

    # Reed/grass silhouettes
    for _ in range(18):
        rx = random.randint(0, W)
        ry = H
        rh = random.randint(55, 145)
        rw = random.randint(2, 5)
        col = (random.randint(8, 18), random.randint(35, 58), random.randint(10, 22))
        draw.rectangle([rx, ry - rh, rx + rw, ry], fill=col)
        # Leaf
        leaf_y = ry - rh + random.randint(10, 30)
        lw = random.randint(10, 24)
        draw.ellipse([rx - lw, leaf_y - 5, rx + lw + rw, leaf_y + 10],
                     fill=(random.randint(12, 24), random.randint(45, 70), random.randint(12, 26)))

    # Water lilies
    for _ in range(12):
        lx = random.randint(0, W)
        ly = random.randint(H * 3 // 4, H)
        lr = random.randint(7, 18)
        lc = (random.randint(12, 28), random.randint(60, 95), random.randint(15, 35))
        draw.ellipse([lx-lr, ly-lr//2, lx+lr, ly+lr//2], fill=lc)

    return img


# ─── Frog character ──────────────────────────────────────────────────────────

def _draw_frog(img: Image.Image, cx: int, cy: int, size: int) -> Image.Image:
    """Draw a cartoon Pepe-style frog face + torso."""
    draw = ImageDraw.Draw(img)

    def ell(x0, y0, x1, y1, fill, outline=None, width=0):
        if outline:
            draw.ellipse([x0, y0, x1, y1], fill=outline)
            m = width
            draw.ellipse([x0+m, y0+m, x1-m, y1-m], fill=fill)
        else:
            draw.ellipse([x0, y0, x1, y1], fill=fill)

    MID   = (62, 155, 58)
    DARK  = (38, 105, 36)
    LIGHT = (88, 185, 72)
    BELLY = (112, 175, 92)
    HOOD  = (25, 32, 28)
    EW    = (238, 238, 218)
    PUP   = (22, 22, 22)
    RED   = (195, 85, 75)

    s  = size
    hr = int(s * 0.38)   # head radius
    hy = cy - int(s * 0.06)   # head center y

    # ── Hoodie / body ────────────────────────────────────────────────────
    bw = int(s * 0.52)
    bh = int(s * 0.44)
    by = cy + int(s * 0.18)
    draw.ellipse([cx-bw, by-bh//2, cx+bw, by+bh], fill=HOOD)
    # Hood opening — dark trapezoid around neck
    draw.ellipse([cx-int(s*0.18), by-int(s*0.28),
                  cx+int(s*0.18), by+int(s*0.05)], fill=HOOD)

    # ── Head ─────────────────────────────────────────────────────────────
    ell(cx-hr, hy-hr, cx+hr, hy+hr, MID, DARK, 3)

    # Forehead shine
    fh = int(hr * 0.45)
    fw = int(hr * 0.55)
    draw.ellipse([cx-fw, hy-hr+4, cx+fw, hy-hr+4+fh], fill=LIGHT)

    # ── Big eyes (on top of head, frog-style) ────────────────────────────
    er   = int(s * 0.135)
    ey   = hy - int(hr * 0.18)
    exL  = cx - int(hr * 0.40)
    exR  = cx + int(hr * 0.40)

    for ex in (exL, exR):
        # Eye socket
        ell(ex-er-2, ey-er-2, ex+er+2, ey+er+2, DARK)
        # White
        ell(ex-er, ey-er, ex+er, ey+er, EW)
        # Pupil
        pr = int(er * 0.58)
        ell(ex-pr, ey-pr, ex+pr, ey+pr, PUP)
        # Shine dot
        sr = max(2, int(er * 0.22))
        draw.ellipse([ex-pr+2, ey-pr+2, ex-pr+2+sr*2, ey-pr+2+sr*2],
                     fill=(255, 255, 255))

    # ── Nose ─────────────────────────────────────────────────────────────
    nr  = int(s * 0.028)
    ny  = hy + int(hr * 0.14)
    for nx in (cx - int(s * 0.07), cx + int(s * 0.07)):
        draw.ellipse([nx-nr, ny-nr, nx+nr, ny+nr], fill=DARK)

    # ── Mouth (wide Pepe smile) ──────────────────────────────────────────
    mw  = int(hr * 0.72)
    my  = hy + int(hr * 0.45)
    mh  = int(s * 0.12)
    # Outer jaw shape
    draw.ellipse([cx-mw, my-mh//2, cx+mw, my+mh], fill=BELLY)
    # Smile line
    draw.arc([cx-mw+4, my-mh, cx+mw-4, my+int(mh*0.6)],
             start=8, end=172, fill=RED, width=max(2, int(s * 0.025)))
    # Lower lip thickness
    draw.arc([cx-mw+4, my-mh//2, cx+mw-4, my+int(mh*1.1)],
             start=0, end=180, fill=DARK, width=max(2, int(s * 0.018)))

    # ── Cheeks ───────────────────────────────────────────────────────────
    for chx in (cx - int(hr * 0.72), cx + int(hr * 0.72)):
        cov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cod = ImageDraw.Draw(cov)
        chy = hy + int(hr * 0.25)
        cr  = int(s * 0.09)
        cod.ellipse([chx-cr, chy-cr//2, chx+cr, chy+cr//2],
                    fill=(180, 60, 60, 45))
        img = Image.alpha_composite(img.convert("RGBA"), cov).convert("RGB")
        draw = ImageDraw.Draw(img)

    return img


# ─── Glow border ─────────────────────────────────────────────────────────────

def _border(draw, color=(30, 220, 80)):
    for i in range(4):
        m = i * 2
        alpha_col = tuple(max(0, c - i * 30) for c in color)
        draw.rectangle([6+m, 6+m, W-6-m, H-6-m], outline=alpha_col, width=2)


# ─── SOL badge ───────────────────────────────────────────────────────────────

def _sol_badge(draw):
    x, y, r = W - 36, 28, 13
    draw.ellipse([x-r, y-r, x+r, y+r], fill=(88, 45, 200), outline=(130, 80, 255), width=1)
    try:
        draw.text((x-8, y-7), "SOL", fill=(255, 255, 255), font=_font(10))
    except Exception:
        pass


# ─── Coin logo circle ─────────────────────────────────────────────────────────

def _coin_logo(draw, symbol: str, cx: int, cy: int, r: int = 28):
    draw.ellipse([cx-r, cy-r, cx+r, cy+r],
                 fill=(15, 45, 18), outline=(40, 200, 80), width=2)
    sym = (symbol[:3]).upper()
    try:
        f   = _font(max(10, r - 6))
        tw  = _text_w(draw, sym, f)
        bb  = draw.textbbox((0, 0), sym, font=f)
        th  = bb[3] - bb[1]
        draw.text((cx - tw//2, cy - th//2), sym, fill=(0, 240, 90), font=f)
    except Exception:
        pass


# ─── Main card builders ──────────────────────────────────────────────────────

def _build_card(
    token: dict,
    mode: str,          # "call" or "update"
    gain_pct: float = 0,
    called_at: str = "",
) -> bytes:

    img  = _make_bg()
    img  = _draw_frog(img, cx=int(W * 0.26), cy=int(H * 0.52), size=int(H * 0.88))
    draw = ImageDraw.Draw(img)

    # Dark gradient overlay on right half for legibility
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    split = int(W * 0.45)
    for x in range(split, W):
        a = int(165 * ((x - split) / (W - split)) ** 0.6)
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
    short   = ca[:8] + "…" + ca[-4:] if len(ca) > 12 else ca

    # ── Coin logo (top, between frog and text) ────────────────────────────
    logo_cx = int(W * 0.50)
    _coin_logo(draw, symbol, logo_cx, 30)
    _sol_badge(draw)

    # ── Right text panel ──────────────────────────────────────────────────
    rx = int(W * 0.475)   # left edge of text
    rw = W - rx - 18      # available width

    # Coin name — fit to width
    name_sz = 72
    while name_sz > 24:
        f = _font(name_sz)
        if _text_w(draw, symbol, f) <= rw:
            break
        name_sz -= 4
    draw.text((rx, 56), symbol, fill=(255, 255, 255), font=_font(name_sz))

    if mode == "call":
        # "NEW CALL" badge
        draw.rectangle([rx, 20, rx + 118, 46], fill=(0, 120, 220))
        draw.text((rx + 8, 22), "🚀 NEW CALL", fill=(255, 255, 255), font=_font(16))

        # Stats
        y = 56 + name_sz + 10
        sf = _font(20)
        draw.text((rx, y),      f"MC:   {_fmt(mc)}",  fill=(170, 230, 185), font=sf)
        draw.text((rx, y + 30), f"Liq:   {_fmt(liq)}", fill=(170, 230, 185), font=sf)
        draw.text((rx, y + 60), f"Vol:  {_fmt(vol)}",  fill=(170, 230, 185), font=sf)
        draw.text((rx, y + 94), f"CA: {short}",        fill=(110, 180, 125), font=_font(15))

    else:  # "update"
        # "called at X"
        cat_txt = f"called at {called_at}"
        draw.text((rx, 56 + name_sz + 6), cat_txt,
                  fill=(0, 210, 180), font=_font(21))

        # Big gain number
        if gain_pct >= 100:
            gain_str = f"{gain_pct/100 + 1:.1f}X"
        else:
            gain_str = f"{gain_pct:.0f}%"

        g_sz = 108
        while g_sz > 48:
            if _text_w(draw, gain_str, _font(g_sz)) <= rw:
                break
            g_sz -= 6

        gf = _font(g_sz)
        gy = 56 + name_sz + 40
        # Glow layers
        for dx, dy in [(-3,-3),(3,-3),(-3,3),(3,3),(-2,0),(2,0),(0,-2),(0,2)]:
            draw.text((rx+dx, gy+dy), gain_str, fill=(0, 80, 30), font=gf)
        draw.text((rx, gy), gain_str, fill=(0, 255, 90), font=gf)

        # Caller info
        info_y = gy + g_sz + 14
        draw.text((rx, info_y),      f"👤  Alpha Circle",        fill=(220, 230, 220), font=_font(19))
        draw.text((rx, info_y + 28), f"📊  Entry: {called_at}", fill=(170, 210, 180), font=_font(17))

    # ── Bottom branding ───────────────────────────────────────────────────
    draw.line([(14, H - 44), (W - 14, H - 44)], fill=(30, 110, 50), width=1)
    bf = _font(13)
    draw.text((22,     H - 34), "t.me/AlphaCirclle",  fill=(120, 180, 130), font=bf)
    draw.text((W - 190, H - 34), "@AlphaCirclle",     fill=(120, 180, 130), font=bf)

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
