import io
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
W, H = 780, 420

SWAMP_DARKS = [
    (8, 25, 12), (5, 18, 8), (10, 30, 15), (3, 15, 7), (12, 35, 18)
]
SWAMP_MIDS = [
    (15, 55, 25), (20, 70, 30), (12, 45, 20), (25, 80, 35)
]
GREEN_GLOW = (0, 200, 80)
NEON_GREEN = (0, 255, 100)
WHITE = (255, 255, 255)
SOFT_WHITE = (220, 230, 220)
BORDER_GREEN = (30, 220, 80)


def _make_swamp_bg() -> Image.Image:
    img = Image.new("RGB", (W, H), SWAMP_DARKS[0])
    draw = ImageDraw.Draw(img)

    # Sky gradient (dark teal-green)
    for y in range(H):
        ratio = y / H
        r = int(5 + ratio * 10)
        g = int(15 + ratio * 30)
        b = int(8 + ratio * 15)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Foggy swamp atmosphere
    for _ in range(6):
        cx = random.randint(0, W)
        cy = random.randint(H // 3, H)
        rx = random.randint(80, 200)
        ry = random.randint(30, 80)
        for layer in range(12):
            alpha = int(18 - layer * 1.4)
            green_val = random.randint(35, 65)
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.ellipse(
                [cx - rx - layer * 4, cy - ry - layer * 2,
                 cx + rx + layer * 4, cy + ry + layer * 2],
                fill=(5, green_val, 12, alpha)
            )
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # Tree silhouettes in background
    draw = ImageDraw.Draw(img)
    for _ in range(8):
        tx = random.randint(0, W)
        ty = random.randint(H // 4, H // 2)
        tw = random.randint(4, 14)
        th = random.randint(60, 130)
        tree_color = (8, random.randint(28, 48), 12)
        draw.rectangle([tx - tw // 2, ty - th, tx + tw // 2, ty], fill=tree_color)
        for branch_y in range(ty - th, ty, 18):
            spread = random.randint(12, 32)
            draw.ellipse(
                [tx - spread, branch_y - 15, tx + spread, branch_y + 5],
                fill=(random.randint(8, 20), random.randint(38, 60), random.randint(12, 22))
            )

    # Water lily pads
    for _ in range(10):
        lx = random.randint(0, W)
        ly = random.randint(H * 2 // 3, H)
        lr = random.randint(8, 22)
        lily_color = (random.randint(10, 25), random.randint(60, 90), random.randint(15, 35))
        draw.ellipse([lx - lr, ly - lr // 2, lx + lr, ly + lr // 2], fill=lily_color)

    return img


def _add_glow_border(img: Image.Image) -> Image.Image:
    draw = ImageDraw.Draw(img)
    for i in range(3):
        alpha_val = 255 - i * 70
        col = (BORDER_GREEN[0], BORDER_GREEN[1], BORDER_GREEN[2])
        margin = i * 2
        draw.rectangle(
            [6 + margin, 6 + margin, W - 6 - margin, H - 6 - margin],
            outline=col, width=2
        )
    return img


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/nix/store/eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee-dejavu-fonts/share/fonts/truetype/DejaVuSans-Bold.ttf",
    ]
    import subprocess
    try:
        result = subprocess.run(["fc-list", ":style=Bold", "--format=%{file}\n"],
                                capture_output=True, text=True, timeout=3)
        for line in result.stdout.strip().split("\n"):
            fp = line.strip()
            if fp and os.path.exists(fp) and ".ttf" in fp.lower():
                font_paths.insert(0, fp)
                break
    except Exception:
        pass

    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_kol_card(token: dict, gain_pct: float, entry_mc: float, called_at_str: str) -> bytes:
    img = _make_swamp_bg()

    # Dark overlay on right half for text readability
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for x in range(W // 2, W):
        ratio = (x - W // 2) / (W // 2)
        alpha = int(160 * ratio)
        od.line([(x, 0), (x, H)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    img = _add_glow_border(img)
    draw = ImageDraw.Draw(img)

    # Coin logo placeholder (top center)
    logo_size = 52
    logo_x = W // 2 - logo_size
    logo_y = 10
    draw.ellipse(
        [logo_x, logo_y, logo_x + logo_size, logo_y + logo_size],
        fill=(15, 50, 20), outline=BORDER_GREEN, width=2
    )
    sym = token.get("symbol", "?")[:3]
    try:
        lf = _get_font(18, bold=True)
        bbox = draw.textbbox((0, 0), sym, font=lf)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (logo_x + (logo_size - tw) // 2, logo_y + (logo_size - th) // 2),
            sym, fill=NEON_GREEN, font=lf
        )
    except Exception:
        pass

    # Solana/chain icon top right
    draw.ellipse([W - 42, 14, W - 18, 38], fill=(100, 60, 200), outline=(140, 90, 255), width=1)
    try:
        sf = _get_font(9)
        draw.text((W - 37, 18), "SOL", fill=WHITE, font=sf)
    except Exception:
        pass

    # --- Right side text panel ---
    right_x = W // 2 + 20

    # Coin name
    coin_name = token.get("symbol", "???").upper()
    try:
        nf = _get_font(min(64, max(32, int(64 * 6 / max(len(coin_name), 1)))), bold=True)
        draw.text((right_x, 60), coin_name, fill=WHITE, font=nf)
    except Exception:
        draw.text((right_x, 60), coin_name, fill=WHITE)

    # "called at X"
    called_txt = f"called at {called_at_str}"
    try:
        cf = _get_font(20)
        draw.text((right_x, 145), called_txt, fill=SOFT_WHITE, font=cf)
    except Exception:
        draw.text((right_x, 145), called_txt, fill=SOFT_WHITE)

    # Big gain/multiplier number
    if gain_pct >= 100:
        multiplier = gain_pct / 100 + 1
        gain_str = f"{multiplier:.1f}X"
    else:
        gain_str = f"{gain_pct:.0f}%"

    try:
        gf = _get_font(min(110, max(60, int(110 * 4 / max(len(gain_str), 1)))), bold=True)
        # Glow effect — draw multiple times slightly offset
        for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
            draw.text((right_x + dx, 175 + dy), gain_str, fill=(0, 100, 40), font=gf)
        draw.text((right_x, 175), gain_str, fill=NEON_GREEN, font=gf)
    except Exception:
        draw.text((right_x, 175), gain_str, fill=NEON_GREEN)

    # Channel branding bottom
    brand_y = H - 40
    try:
        bf = _get_font(15)
        draw.text((W - 220, brand_y), "t.me/AlphaCirclle", fill=(150, 200, 160), font=bf)
        draw.text((16, brand_y), "Alpha Circle", fill=(120, 180, 130), font=bf)
    except Exception:
        pass

    # Bottom separator line
    draw.line([(16, H - 48), (W - 16, H - 48)], fill=(30, 100, 50), width=1)

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf.read()


def generate_initial_call_image(token: dict) -> bytes:
    img = _make_swamp_bg()
    img = _add_glow_border(img)
    draw = ImageDraw.Draw(img)

    # Dark right panel overlay
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for x in range(W // 2, W):
        ratio = (x - W // 2) / (W // 2)
        od.line([(x, 0), (x, H)], fill=(0, 0, 0, int(150 * ratio)))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # "NEW CALL" banner
    try:
        banner_font = _get_font(20, bold=True)
        draw.rectangle([W // 2 + 20, 15, W // 2 + 160, 45], fill=(0, 160, 60))
        draw.text((W // 2 + 28, 18), "🚀 NEW CALL", fill=WHITE, font=banner_font)
    except Exception:
        pass

    right_x = W // 2 + 20

    # Coin name
    coin_name = token.get("symbol", "???").upper()
    mc = token.get("market_cap", 0)
    mc_str = _fmt_mc(mc)

    try:
        nf = _get_font(min(60, max(28, int(60 * 6 / max(len(coin_name), 1)))), bold=True)
        draw.text((right_x, 58), coin_name, fill=WHITE, font=nf)
    except Exception:
        draw.text((right_x, 58), coin_name, fill=WHITE)

    try:
        mf = _get_font(22)
        draw.text((right_x, 140), f"Entry MC: {mc_str}", fill=SOFT_WHITE, font=mf)

        liq = token.get("liquidity_usd", 0)
        draw.text((right_x, 175), f"Liquidity: {_fmt_mc(liq)}", fill=(170, 220, 180), font=mf)

        chain = token.get("chain", "solana").upper()
        draw.text((right_x, 210), f"Chain: {chain}", fill=(170, 220, 180), font=mf)

        addr = token.get("address", "")
        short_addr = addr[:8] + "..." + addr[-4:] if len(addr) > 12 else addr
        draw.text((right_x, 245), f"CA: {short_addr}", fill=(140, 200, 150), font=_get_font(17))
    except Exception:
        pass

    # Dex label
    try:
        df = _get_font(16)
        dex_name = token.get("dex", "").upper() or "DEXSCREENER"
        draw.text((right_x, 295), f"DEX: {dex_name}", fill=(100, 180, 120), font=df)
    except Exception:
        pass

    # Branding
    brand_y = H - 40
    try:
        bf = _get_font(15)
        draw.line([(16, H - 48), (W - 16, H - 48)], fill=(30, 100, 50), width=1)
        draw.text((W - 220, brand_y), "t.me/AlphaCirclle", fill=(150, 200, 160), font=bf)
        draw.text((16, brand_y), "Alpha Circle", fill=(120, 180, 130), font=bf)
    except Exception:
        pass

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf.read()


def _fmt_mc(v: float) -> str:
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.1f}K"
    return f"${v:.0f}"
