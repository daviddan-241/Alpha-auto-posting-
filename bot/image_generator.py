import io
import math
import random
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 960, 520

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
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
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


# ─── Rich swamp background ────────────────────────────────────────────────────

def _make_bg() -> Image.Image:
    img = Image.new("RGB", (W, H), (3, 10, 4))

    # Base gradient: very dark top → slightly lighter bottom
    for y in range(H):
        t = y / H
        r = int(2 + t * 12)
        g = int(8  + t * 30)
        b = int(2  + t * 8)
        ImageDraw.Draw(img).line([(0, y), (W, y)], fill=(r, g, b))

    draw = ImageDraw.Draw(img)

    # Far background: tall thin trees silhouettes
    for _ in range(40):
        tx = random.randint(0, W)
        th_h = random.randint(H // 3, H - 10)
        tw = random.randint(3, 10)
        darkness = random.randint(0, 3)
        col = (4 + darkness, 20 + darkness * 2, 5 + darkness)
        draw.rectangle([tx, H - th_h, tx + tw, H], fill=col)
        cr = random.randint(14, 32)
        draw.ellipse([tx - cr + tw // 2, H - th_h - cr * 2,
                      tx + cr + tw // 2, H - th_h + cr // 2], fill=col)

    # Mid trees — slightly lighter
    for _ in range(18):
        tx = random.randint(0, W)
        th_h = random.randint(H // 4, H // 2)
        tw = random.randint(6, 16)
        col = (5, 28, 7)
        draw.rectangle([tx, H - th_h, tx + tw, H], fill=col)
        cr = random.randint(20, 50)
        draw.ellipse([tx - cr + tw // 2, H - th_h - cr * 2,
                      tx + cr + tw // 2, H - th_h + cr // 3], fill=col)

    # Mist / atmospheric fog layers
    img = img.convert("RGBA")
    for _ in range(8):
        cx = random.randint(-80, W + 80)
        cy = random.randint(H // 2, H)
        rx = random.randint(150, 340)
        ry = random.randint(22, 60)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.ellipse([cx - rx, cy - ry, cx + rx, cy + ry],
                   fill=(10, 60, 18, 22))
        img = Image.alpha_composite(img, ov)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    # Ground reeds / grass
    for _ in range(30):
        rx = random.randint(0, W)
        rh = random.randint(30, 120)
        rw = random.randint(2, 5)
        col = (6, random.randint(30, 55), 8)
        draw.rectangle([rx, H - rh, rx + rw, H], fill=col)
        lw = random.randint(7, 20)
        leaf_y = H - rh + random.randint(5, 20)
        draw.ellipse([rx - lw, leaf_y - 4, rx + lw + rw, leaf_y + 8],
                     fill=(7, random.randint(38, 65), 10))

    # Lily pads on water
    for _ in range(18):
        lx = random.randint(0, W)
        ly = random.randint(H * 3 // 4, H - 5)
        lr = random.randint(5, 14)
        draw.ellipse([lx - lr, ly - lr // 3, lx + lr, ly + lr // 3],
                     fill=(8, random.randint(50, 80), 12))

    # Subtle light beams from top right
    img = img.convert("RGBA")
    for i in range(3):
        beam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bd   = ImageDraw.Draw(beam)
        bx   = W - 80 + i * 40
        bd.polygon([(bx, 0), (bx + 30, 0), (bx + 200, H), (bx + 170, H)],
                   fill=(20, 80, 22, 6))
        img = Image.alpha_composite(img, beam)
    img = img.convert("RGB")

    return img


# ─── Realistic Pepe frog ──────────────────────────────────────────────────────

def _draw_pepe(img: Image.Image, cx: int, cy: int, size: int) -> Image.Image:
    """Draw a realistic cartoon Pepe (Phanes-style) facing right."""
    draw = ImageDraw.Draw(img)

    s = size

    # Color palette
    SKIN      = (68, 160, 58)
    SKIN_D    = (42, 118, 36)
    SKIN_L    = (95, 185, 78)
    BELLY_C   = (120, 178, 95)
    SHIRT     = (52, 105, 195)   # blue shirt
    SHIRT_D   = (34, 72, 148)
    LIP_TOP   = (58, 145, 50)
    LIP_BOT   = (200, 110, 95)   # pinkish lower lip
    EYE_W     = (230, 232, 210)
    PUPIL     = (20, 20, 20)
    IRIS      = (100, 135, 60)   # olive iris
    OUTLINE   = (22, 72, 18)
    WHITE_SH  = (255, 255, 255)

    # ── Shirt / body ──────────────────────────────────────────────────────
    body_w = int(s * 0.52)
    body_h = int(s * 0.50)
    body_y = cy + int(s * 0.24)
    # Main shirt body
    draw.ellipse([cx - body_w, body_y - body_h // 3,
                  cx + body_w, body_y + body_h], fill=SHIRT_D)
    draw.ellipse([cx - int(body_w * 0.85), body_y - body_h // 3 + 4,
                  cx + int(body_w * 0.85), body_y + body_h - 4], fill=SHIRT)
    # Collar
    draw.ellipse([cx - int(s * 0.16), body_y - int(s * 0.24),
                  cx + int(s * 0.16), body_y + int(s * 0.02)], fill=SHIRT_D)

    # ── Left arm reaching forward (peeking pose) ──────────────────────────
    arm_w = int(s * 0.18)
    arm_h = int(s * 0.38)
    arm_x = cx - int(s * 0.38)
    arm_y = body_y - int(s * 0.05)
    draw.ellipse([arm_x - arm_w // 2, arm_y,
                  arm_x + arm_w // 2, arm_y + arm_h], fill=SHIRT_D)
    # Hand / fist
    hx, hy, hr = arm_x, arm_y + arm_h - 4, int(s * 0.12)
    draw.ellipse([hx - hr, hy - hr // 2, hx + hr, hy + hr], fill=SKIN)
    draw.ellipse([hx - int(hr * 0.7), hy - int(hr * 0.4),
                  hx + int(hr * 0.7), hy + int(hr * 0.8)], fill=SKIN_L)

    # ── Right arm (thumb up / resting) ────────────────────────────────────
    ra_x = cx + int(s * 0.36)
    ra_y = body_y + int(s * 0.05)
    ra_w = int(s * 0.17)
    ra_h = int(s * 0.32)
    draw.ellipse([ra_x - ra_w // 2, ra_y,
                  ra_x + ra_w // 2, ra_y + ra_h], fill=SHIRT_D)
    rh_r = int(s * 0.11)
    draw.ellipse([ra_x - rh_r, ra_y + ra_h - 4,
                  ra_x + rh_r, ra_y + ra_h + rh_r * 2], fill=SKIN)

    # ── Head ──────────────────────────────────────────────────────────────
    hr_head = int(s * 0.38)
    # Slightly oval — wider than tall
    hx0 = cx - int(hr_head * 1.05)
    hy0 = cy - int(hr_head * 0.95)
    hx1 = cx + int(hr_head * 1.05)
    hy1 = cy + int(hr_head * 0.95)

    # Shadow / outline
    draw.ellipse([hx0 - 4, hy0 - 4, hx1 + 4, hy1 + 4], fill=OUTLINE)
    # Main head
    draw.ellipse([hx0, hy0, hx1, hy1], fill=SKIN)
    # Highlight on top
    draw.ellipse([cx - int(hr_head * 0.65), hy0 + 4,
                  cx + int(hr_head * 0.65), hy0 + 4 + int(hr_head * 0.48)],
                 fill=SKIN_L)

    # ── Lower jaw / chin protrusion ───────────────────────────────────────
    jaw_y = cy + int(hr_head * 0.55)
    draw.ellipse([cx - int(hr_head * 0.72), jaw_y - int(s * 0.06),
                  cx + int(hr_head * 0.72), jaw_y + int(s * 0.22)], fill=SKIN)
    draw.ellipse([cx - int(hr_head * 0.58), jaw_y,
                  cx + int(hr_head * 0.58), jaw_y + int(s * 0.20)], fill=BELLY_C)

    # ── Eyes (heavy-lidded Pepe style) ────────────────────────────────────
    eye_r  = int(s * 0.125)
    eye_y  = cy - int(hr_head * 0.12)
    eye_lx = cx - int(hr_head * 0.38)
    eye_rx = cx + int(hr_head * 0.38)

    for ex in (eye_lx, eye_rx):
        # Eye socket
        draw.ellipse([ex - eye_r - 3, eye_y - eye_r - 3,
                      ex + eye_r + 3, eye_y + eye_r + 3], fill=OUTLINE)
        # White of eye
        draw.ellipse([ex - eye_r, eye_y - eye_r,
                      ex + eye_r, eye_y + eye_r], fill=EYE_W)
        # Iris
        ir = int(eye_r * 0.64)
        draw.ellipse([ex - ir, eye_y - ir, ex + ir, eye_y + ir], fill=IRIS)
        # Pupil
        pr = int(ir * 0.62)
        draw.ellipse([ex - pr, eye_y - pr, ex + pr, eye_y + pr], fill=PUPIL)
        # Shine
        sr = max(2, int(pr * 0.30))
        draw.ellipse([ex - pr + 3, eye_y - pr + 3,
                      ex - pr + 3 + sr * 2, eye_y - pr + 3 + sr * 2],
                     fill=WHITE_SH)

        # Heavy upper eyelid (drooping, Pepe-signature)
        lid_h = int(eye_r * 0.55)
        lid_pts = [
            (ex - eye_r - 2, eye_y - eye_r + lid_h // 2),
            (ex,             eye_y - eye_r - 2),
            (ex + eye_r + 2, eye_y - eye_r + lid_h // 2),
            (ex + eye_r + 2, eye_y - eye_r + lid_h),
            (ex,             eye_y - eye_r + lid_h + 4),
            (ex - eye_r - 2, eye_y - eye_r + lid_h),
        ]
        draw.polygon(lid_pts, fill=SKIN)
        # Eyelid bottom line
        draw.arc([ex - eye_r - 2, eye_y - eye_r - 2,
                  ex + eye_r + 2, eye_y + eye_r + 2],
                 start=200, end=340, fill=OUTLINE, width=2)

    # ── Nose bumps ────────────────────────────────────────────────────────
    nr = int(s * 0.026)
    ny = cy + int(hr_head * 0.18)
    for nx in (cx - int(s * 0.07), cx + int(s * 0.07)):
        draw.ellipse([nx - nr, ny - nr, nx + nr, ny + nr], fill=SKIN_D)

    # ── Wide Pepe mouth (smug / half-open) ───────────────────────────────
    mouth_w = int(hr_head * 0.78)
    mouth_y = cy + int(hr_head * 0.50)
    mouth_h = int(s * 0.14)

    # Outer lip shape
    draw.ellipse([cx - mouth_w, mouth_y - mouth_h // 3,
                  cx + mouth_w, mouth_y + mouth_h], fill=LIP_TOP)
    # Inner mouth (dark)
    draw.ellipse([cx - int(mouth_w * 0.78), mouth_y,
                  cx + int(mouth_w * 0.78), mouth_y + mouth_h + 4], fill=(15, 15, 15))
    # Lower lip
    draw.ellipse([cx - int(mouth_w * 0.80), mouth_y + int(mouth_h * 0.55),
                  cx + int(mouth_w * 0.80), mouth_y + mouth_h + 8], fill=LIP_BOT)
    # Smile line
    draw.arc([cx - mouth_w + 6, mouth_y - mouth_h,
              cx + mouth_w - 6, mouth_y + int(mouth_h * 0.5)],
             start=10, end=170, fill=OUTLINE, width=max(2, int(s * 0.022)))

    return img


# ─── Coin logo ────────────────────────────────────────────────────────────────

def _coin_logo(draw, img, symbol: str, cx: int, cy: int, r: int = 30):
    # Outer glow ring
    for i in range(4, 0, -1):
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.ellipse([cx - r - i * 3, cy - r - i * 3,
                    cx + r + i * 3, cy + r + i * 3],
                   fill=(0, 200, 70, max(0, 30 - i * 6)))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

    draw = ImageDraw.Draw(img)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                 fill=(10, 38, 14), outline=(0, 215, 80), width=2)
    sym = symbol[:4].upper()
    f   = _font(max(9, r - 9))
    tw  = _tw(draw, sym, f)
    bb  = draw.textbbox((0, 0), sym, font=f)
    th  = bb[3] - bb[1]
    draw.text((cx - tw // 2, cy - th // 2), sym, fill=(0, 240, 90), font=f)
    return img


# ─── Rounded rectangle ────────────────────────────────────────────────────────

def _rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = xy
    r = radius
    if fill:
        draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
        draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
        draw.ellipse([x0, y0, x0 + 2*r, y0 + 2*r], fill=fill)
        draw.ellipse([x1 - 2*r, y0, x1, y0 + 2*r], fill=fill)
        draw.ellipse([x0, y1 - 2*r, x0 + 2*r, y1], fill=fill)
        draw.ellipse([x1 - 2*r, y1 - 2*r, x1, y1], fill=fill)
    if outline:
        draw.arc([x0, y0, x0+2*r, y0+2*r], 180, 270, fill=outline, width=width)
        draw.arc([x1-2*r, y0, x1, y0+2*r], 270, 360, fill=outline, width=width)
        draw.arc([x0, y1-2*r, x0+2*r, y1], 90, 180, fill=outline, width=width)
        draw.arc([x1-2*r, y1-2*r, x1, y1], 0, 90, fill=outline, width=width)
        draw.line([x0+r, y0, x1-r, y0], fill=outline, width=width)
        draw.line([x0+r, y1, x1-r, y1], fill=outline, width=width)
        draw.line([x0, y0+r, x0, y1-r], fill=outline, width=width)
        draw.line([x1, y0+r, x1, y1-r], fill=outline, width=width)


# ─── Glow text ────────────────────────────────────────────────────────────────

def _glow_text(draw, pos, text, font, fill, glow, spread=4):
    x, y = pos
    for dx in range(-spread, spread + 1):
        for dy in range(-spread, spread + 1):
            if dx == 0 and dy == 0:
                continue
            d = math.sqrt(dx*dx + dy*dy)
            if d > spread:
                continue
            a = max(0.0, 1.0 - d / spread)
            gc = tuple(int(c * a) for c in glow)
            draw.text((x + dx, y + dy), text, fill=gc, font=font)
    draw.text((x, y), text, fill=fill, font=font)


# ─── Card builder ────────────────────────────────────────────────────────────

def _build_card(token: dict, mode: str,
                gain_pct: float = 0, called_at: str = "",
                elapsed_str: str = "") -> bytes:

    img  = _make_bg()
    draw = ImageDraw.Draw(img)

    # ── Draw Pepe on the left ─────────────────────────────────────────────
    frog_cx = int(W * 0.215)
    frog_cy = int(H * 0.50)
    frog_sz = int(H * 0.90)
    img = _draw_pepe(img, cx=frog_cx, cy=frog_cy, size=frog_sz)

    # ── Dark gradient on right half (text readability) ────────────────────
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    split = int(W * 0.36)
    for x in range(split, W):
        a = int(200 * ((x - split) / (W - split)) ** 0.50)
        od.line([(x, 0), (x, H)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── Rounded border glow ───────────────────────────────────────────────
    border_color = (22, 200, 65)
    for i in range(5, 0, -1):
        c = tuple(max(0, v - (5 - i) * 18) for v in border_color)
        _rounded_rect(draw, [6 + (5-i)*2, 6 + (5-i)*2,
                              W - 6 - (5-i)*2, H - 6 - (5-i)*2],
                      radius=18, outline=c, width=2)

    symbol  = token.get("symbol", "???").upper()
    mc      = token.get("market_cap", 0)
    liq     = token.get("liquidity_usd", 0)
    vol     = token.get("volume_24h", 0)
    ca      = token.get("address", "")
    short   = ca[:8] + "…" + ca[-4:] if len(ca) > 12 else ca

    # ── Coin logo top center ──────────────────────────────────────────────
    logo_cx = int(W * 0.50)
    img = _coin_logo(draw, img, symbol, logo_cx, 34, r=30)
    draw = ImageDraw.Draw(img)

    # SOL badge top right
    sol_x, sol_y, sol_r = W - 38, 32, 15
    draw.ellipse([sol_x-sol_r, sol_y-sol_r, sol_x+sol_r, sol_y+sol_r],
                 fill=(72, 30, 185), outline=(110, 65, 245), width=2)
    draw.text((sol_x - 6, sol_y - 8), "◎", fill=(220, 210, 255), font=_font(13))

    # ── Right text panel ──────────────────────────────────────────────────
    rx = int(W * 0.42)
    rw = W - rx - 28

    # Token name — large white bold
    name_sz = 90
    while name_sz > 28:
        if _tw(draw, symbol, _font(name_sz)) <= rw:
            break
        name_sz -= 4
    name_y = 58
    _glow_text(draw, (rx, name_y), symbol,
               _font(name_sz), (255, 255, 255), (60, 180, 60), 5)

    if mode == "call":
        y = name_y + name_sz + 12
        sf  = _font(22)
        sfd = _font(22, bold=False)
        row_gap = 34
        draw.text((rx, y),                f"MC:",  fill=(150, 220, 165), font=sf)
        draw.text((rx + 70, y),           _fmt(mc), fill=(255, 255, 255), font=sf)
        draw.text((rx, y + row_gap),      f"Liq:", fill=(150, 220, 165), font=sf)
        draw.text((rx + 70, y+row_gap),   _fmt(liq), fill=(255, 255, 255), font=sf)
        draw.text((rx, y + row_gap*2),    f"Vol:", fill=(150, 220, 165), font=sf)
        draw.text((rx + 70, y+row_gap*2), _fmt(vol), fill=(255, 255, 255), font=sf)
        draw.text((rx, y + row_gap*3 + 6), f"CA: {short}",
                  fill=(90, 160, 110), font=_font(15, bold=False))

    else:  # gain update
        # "called at X"
        draw.text((rx, name_y + name_sz + 10), f"called at {called_at}",
                  fill=(190, 225, 200), font=_font(23, bold=False))

        # Big gain number
        if gain_pct >= 100:
            gain_str = f"{gain_pct / 100 + 1:.1f}X"
        else:
            gain_str = f"{gain_pct:.0f}%"

        g_sz = 140
        while g_sz > 52:
            if _tw(draw, gain_str, _font(g_sz)) <= rw:
                break
            g_sz -= 6

        gy = name_y + name_sz + 50
        _glow_text(draw, (rx, gy), gain_str,
                   _font(g_sz), (0, 255, 85), (0, 100, 20), 6)

        # Person + name
        info_y = gy + g_sz + 12
        draw.text((rx, info_y),      "👤  Alpha Circle",         fill=(210, 240, 218), font=_font(20))
        draw.text((rx, info_y + 32), f"🕐  {elapsed_str or called_at}", fill=(165, 205, 178), font=_font(18, bold=False))

    # ── Bottom branding ────────────────────────────────────────────────────
    draw.line([(16, H - 44), (W - 16, H - 44)], fill=(20, 95, 38), width=1)
    bf = _font(14, bold=False)
    draw.text((22,      H - 32), "t.me/AlphaCirclle",  fill=(90, 160, 110), font=bf)
    draw.text((W - 210, H - 32), "@AlphaCirclle",       fill=(90, 160, 110), font=bf)

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
