"""
src/video.py — Ultra-premium Reel renderer

Design philosophy:
  - Each topic has its own unique visual identity
  - Rich layered backgrounds with blur, grain, gradient
  - Elegant typography — large, readable, weighted
  - Glassmorphism + frosted panels
  - Animated progress bar
  - Word-by-word subtitle reveal
  - NO countdown timer
  - Cinematic letterbox
"""

import math
import random
import logging
from pathlib import Path
from datetime import datetime

import numpy as np
import requests
from PIL import (Image, ImageDraw, ImageFont,
                 ImageEnhance, ImageFilter, ImageChops)
from moviepy.editor import VideoClip, AudioFileClip
from moviepy.video.fx.all import fadein, fadeout

from config import (REEL_WIDTH, REEL_HEIGHT, REEL_DURATION,
                    REEL_FPS, MUSIC_VOLUME, LANGUAGES)

log       = logging.getLogger(__name__)
W, H      = REEL_WIDTH, REEL_HEIGHT
PAD       = 68
ROOT      = Path(__file__).parent.parent
FONTS_DIR = ROOT / "fonts"
FONTS_DIR.mkdir(exist_ok=True)

# ── Timing ─────────────────────────────────────────────────────────────────────
T_BARS_IN      = 0.0
T_HEADER_IN    = 0.3
T_HOOK_IN      = 0.8
T_BODY_IN      = 5.0
T_SUBS_START   = 5.5
T_TAGS_IN      = 14.0
T_CTA_IN       = 15.5

# ── Themes ─────────────────────────────────────────────────────────────────────
THEMES = {
    "space": {
        "name":      "SPACE & UNIVERSE",
        "name_hi":   "अंतरिक्ष और ब्रह्मांड",
        "accent":    (120, 200, 255),
        "accent2":   (180, 130, 255),
        "accent3":   (80,  160, 255),
        "bg_tint":   (4,   8,   22),
        "text":      (230, 242, 255),
        "muted":     (140, 170, 210),
        "gradient":  [(4,8,22), (8,15,40), (12,20,55), (6,12,35)],
        "particles": True,
        "p_color":   (180, 220, 255),
        "bar_style": "line",
        "style":     "cosmic",
    },
    "history": {
        "name":      "WORLD HISTORY",
        "name_hi":   "विश्व इतिहास",
        "accent":    (220, 175, 85),
        "accent2":   (190, 130, 55),
        "accent3":   (240, 200, 110),
        "bg_tint":   (20,  12,  4),
        "text":      (255, 245, 220),
        "muted":     (200, 170, 120),
        "gradient":  [(20,12,4), (35,20,8), (50,30,10), (25,15,5)],
        "particles": False,
        "bar_style": "line",
        "style":     "parchment",
    },
    "geography": {
        "name":      "GEOGRAPHY",
        "name_hi":   "भूगोल",
        "accent":    (75,  215, 125),
        "accent2":   (45,  175,  90),
        "accent3":   (100, 235, 150),
        "bg_tint":   (4,   18,   8),
        "text":      (215, 255, 230),
        "muted":     (130, 200, 155),
        "gradient":  [(4,18,8), (8,30,15), (12,45,22), (6,25,12)],
        "particles": False,
        "bar_style": "line",
        "style":     "nature",
    },
    "science": {
        "name":      "SCIENCE FACTS",
        "name_hi":   "विज्ञान तथ्य",
        "accent":    (185, 105, 255),
        "accent2":   (130,  70, 220),
        "accent3":   (210, 140, 255),
        "bg_tint":   (12,   4,  24),
        "text":      (238, 220, 255),
        "muted":     (165, 135, 210),
        "gradient":  [(12,4,24), (20,8,40), (30,12,55), (15,5,30)],
        "particles": True,
        "p_color":   (200, 155, 255),
        "bar_style": "line",
        "style":     "tech",
    },
    "sports": {
        "name":      "SPORTS NEWS",
        "name_hi":   "खेल समाचार",
        "accent":    (255, 205,  45),
        "accent2":   (255, 155,  25),
        "accent3":   (255, 230,  90),
        "bg_tint":   (8,   16,   4),
        "text":      (255, 252, 220),
        "muted":     (200, 190, 130),
        "gradient":  [(8,16,4), (15,25,8), (22,38,10), (10,20,5)],
        "particles": False,
        "bar_style": "line",
        "style":     "dynamic",
    },
    "worldnews": {
        "name":      "WORLD NEWS",
        "name_hi":   "विश्व समाचार",
        "accent":    (255,  85,  70),
        "accent2":   (220,  55,  45),
        "accent3":   (255, 130, 115),
        "bg_tint":   (22,   4,   4),
        "text":      (255, 232, 228),
        "muted":     (210, 155, 148),
        "gradient":  [(22,4,4), (38,8,8), (55,12,10), (28,5,5)],
        "particles": False,
        "bar_style": "line",
        "style":     "news",
    },
}

VIDEO_TAGS = {
    "space_en":     ["#space","#universe","#NASA","#spacefacts","#didyouknow","#cosmoscapsule"],
    "space_hi":     ["#अंतरिक्ष","#ब्रह्मांड","#विज्ञान","#तथ्य","#इसरो","#cosmoscapsule"],
    "history_en":   ["#history","#ancienthistory","#historyfacts","#didyouknow","#civilization","#cosmoscapsule"],
    "history_hi":   ["#इतिहास","#प्राचीनइतिहास","#तथ्य","#ज्ञान","#सभ्यता","#cosmoscapsule"],
    "geography_en": ["#geography","#earthfacts","#nature","#travel","#amazingearth","#cosmoscapsule"],
    "geography_hi": ["#भूगोल","#पृथ्वी","#प्रकृति","#यात्रा","#तथ्य","#cosmoscapsule"],
    "science_en":   ["#science","#sciencefacts","#physics","#biology","#mindblown","#cosmoscapsule"],
    "science_hi":   ["#विज्ञान","#विज्ञानतथ्य","#भौतिकी","#जीवविज्ञान","#तथ्य","#cosmoscapsule"],
    "sports_en":    ["#sports","#cricket","#IPL","#football","#athlete","#cosmoscapsule"],
    "sports_hi":    ["#खेल","#क्रिकेट","#आईपीएल","#फुटबॉल","#खिलाड़ी","#cosmoscapsule"],
    "worldnews_en": ["#worldnews","#breakingnews","#NASA","#ISRO","#geopolitics","#cosmoscapsule"],
    "worldnews_hi": ["#विश्वसमाचार","#ताजाखबर","#राजनीति","#नासा","#इसरो","#cosmoscapsule"],
}

# ── Font helpers ───────────────────────────────────────────────────────────────
FONT_CACHE: dict = {}

def _dl_font(url: str, dest: Path):
    if dest.exists(): return
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)
    except Exception as e:
        log.warning(f"Font DL failed: {e}")

def _font(size: int, bold: bool = False, lang: str = "en"):
    key = f"{lang}_{size}_{bold}"
    if key in FONT_CACHE: return FONT_CACHE[key]
    cands = []
    if lang == "hi":
        lc = LANGUAGES["hi"]
        bp = FONTS_DIR / "NotoSansDevanagari-Bold.ttf"
        rp = FONTS_DIR / "NotoSansDevanagari-Regular.ttf"
        _dl_font(lc["font_url"], bp)
        _dl_font(lc["font_url_reg"], rp)
        cands = [bp if bold else rp]
    cands += [
        FONTS_DIR / ("Poppins-Bold.ttf" if bold else "Poppins-Regular.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
             if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
             if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for p in cands:
        if Path(p).exists():
            f = ImageFont.truetype(str(p), size)
            FONT_CACHE[key] = f
            return f
    return ImageFont.load_default()

# ── Math helpers ───────────────────────────────────────────────────────────────
def _a(v): return max(0, min(255, int(v)))
def _ease_out(x): return 1 - (1 - max(0, min(1, x))) ** 3
def _ease_in_out(x):
    x = max(0, min(1, x))
    return 3*x*x - 2*x*x*x
def _slide(t, start, dur=0.4):
    if t < start: return 0
    return _a(_ease_out((t - start) / dur) * 255)

# ── Drawing helpers ────────────────────────────────────────────────────────────
def _wrap(text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if fnt.getbbox(test)[2] <= max_w: cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def _text(draw, x, y, txt, fnt, col, alpha, shadow=True):
    if shadow:
        draw.text((x+2, y+2), txt, font=fnt, fill=(0,0,0,_a(alpha*0.4)))
    draw.text((x, y), txt, font=fnt, fill=(*col, _a(alpha)))

def _glass(draw, x1, y1, x2, y2, fill_col=(255,255,255),
           fill_a=20, stroke_col=(255,255,255), stroke_a=35,
           radius=18):
    draw.rounded_rectangle([x1,y1,x2,y2], radius=radius,
                            fill=(*fill_col, fill_a),
                            outline=(*stroke_col, stroke_a), width=1)

def _hairline(draw, x1, y, x2, col, alpha):
    draw.rectangle([x1, y, x2, y+1], fill=(*col, _a(alpha)))

def _particles(draw, t, col, n=30, seed=99):
    rng = random.Random(seed)
    for _ in range(n):
        px = rng.randint(0, W)
        py = rng.randint(0, H)
        sz = rng.choice([1,1,2,2,3])
        sp = rng.uniform(0.2, 1.2)
        py2 = int((py - t * sp * 18) % H)
        pulse = 0.5 + 0.5 * math.sin(t * sp + px * 0.02)
        draw.ellipse([px-sz, py2-sz, px+sz, py2+sz],
                     fill=(*col, _a(160*pulse)))

def _vignette(frame: Image.Image) -> Image.Image:
    """Strong cinema vignette."""
    vig = Image.new("RGBA", (W, H), (0,0,0,0))
    vd  = ImageDraw.Draw(vig)
    steps = 60
    for i in range(steps, 0, -1):
        r  = int((min(W,H)//2) * i / steps)
        aa = _a(200 * (1 - i/steps) ** 2.2)
        pad_ = steps - i
        vd.rectangle([pad_, pad_, W-pad_, H-pad_],
                     outline=(0,0,0,aa), width=6)
    return Image.alpha_composite(frame, vig)

def _grain(frame: Image.Image, strength: int = 12) -> Image.Image:
    """Subtle film grain for texture."""
    noise = np.random.randint(-strength, strength,
                              (H, W, 3), dtype=np.int16)
    arr   = np.array(frame.convert("RGB")).astype(np.int16)
    arr   = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr).convert("RGBA")

def _draw_background(theme: dict, t: float) -> Image.Image:
    """Animated multi-stop gradient background."""
    bg   = Image.new("RGBA", (W, H))
    pix  = bg.load()
    cols = theme["gradient"]
    n    = len(cols)
    # Slow animated shift
    shift = (t * 0.015) % 1.0
    for y in range(H):
        fy  = ((y / H) + shift) % 1.0
        idx = fy * (n - 1)
        i   = min(int(idx), n - 2)
        fr  = idx - i
        c1, c2 = cols[i], cols[i+1]
        r = int(c1[0] + (c2[0]-c1[0]) * fr)
        g = int(c1[1] + (c2[1]-c1[1]) * fr)
        b = int(c1[2] + (c2[2]-c1[2]) * fr)
        for x in range(W):
            pix[x, y] = (r, g, b, 255)
    return bg

def _draw_decorative_bg(draw, theme: dict, t: float, style: str):
    """Per-topic subtle decorative background elements."""
    acc = theme["accent"]
    a   = 18  # very subtle

    if style == "cosmic":
        # Concentric arc rings — nebula feel
        cx, cy = W // 2, int(H * 0.38)
        for r in range(180, 520, 70):
            rot = t * 0.04 * (1 if r % 2 == 0 else -1)
            pulse = 0.6 + 0.4 * math.sin(t * 0.3 + r * 0.008)
            sa = _a(a * pulse)
            if sa > 0:
                draw.arc([cx-r, cy-r, cx+r, cy+r],
                         start=int(rot*57), end=int(rot*57+200),
                         fill=(*acc, sa), width=1)

    elif style == "tech":
        # Dot grid
        spacing = 80
        for gx in range(0, W, spacing):
            for gy in range(0, H, spacing):
                drift_x = int(4 * math.sin(t * 0.5 + gy * 0.02))
                drift_y = int(4 * math.cos(t * 0.4 + gx * 0.02))
                draw.ellipse([gx+drift_x-1, gy+drift_y-1,
                              gx+drift_x+1, gy+drift_y+1],
                             fill=(*acc, a))

    elif style == "parchment":
        # Diagonal ruled lines
        for i in range(-4, 12):
            off = i * 220
            draw.line([(off, 0), (off + H, H)],
                      fill=(*acc, a // 2), width=1)

    elif style == "nature":
        # Organic wave arcs
        for i in range(4):
            cy2 = H // 2 + i * 180 - 250
            xo  = int(40 * math.sin(t * 0.2 + i))
            draw.arc([xo - 350, cy2 - 200, xo + 350, cy2 + 200],
                     start=0, end=180, fill=(*acc, a), width=1)

    elif style == "dynamic":
        # Speed lines (sport energy)
        rng = random.Random(42)
        for _ in range(12):
            lx = rng.randint(0, W)
            draw.line([(lx, 0), (lx + rng.randint(-30,30), H)],
                      fill=(*acc, a // 2), width=1)

    elif style == "news":
        # Horizontal rule lines (broadcast TV feel)
        for y2 in range(0, H, 160):
            draw.rectangle([0, y2, W, y2+1], fill=(*acc, a//2))


# ── MAIN FRAME ─────────────────────────────────────────────────────────────────

def _make_frame(bg_photo: Image.Image, hook: str, body: str,
                body_words: list, topic_key: str, topic: dict,
                lang: str, follow_text: str, tags: list,
                t: float, total: float) -> np.ndarray:

    th   = THEMES.get(topic_key, THEMES["space"])
    acc  = th["accent"]
    acc2 = th["accent2"]
    acc3 = th["accent3"]
    txt  = th["text"]
    mut  = th["muted"]

    # ── Layer 1: photo base ────────────────────────────────────────────────
    scale = 1.0 + 0.04 * (t / total)
    nw, nh = int(W * scale), int(H * scale)
    photo  = bg_photo.resize((nw, nh), Image.LANCZOS)
    lft    = (nw - W) // 2
    top_   = (nh - H) // 2
    photo  = photo.crop((lft, top_, lft+W, top_+H)).convert("RGBA")

    # Desaturate + darken for luxury look
    photo_rgb = ImageEnhance.Color(photo.convert("RGB")).enhance(0.65)
    photo_rgb = ImageEnhance.Brightness(photo_rgb).enhance(0.45)
    photo     = photo_rgb.convert("RGBA")

    # ── Layer 2: animated gradient bg (blended over photo) ────────────────
    grad = _draw_background(th, t)
    base = Image.blend(photo, grad, alpha=0.60)

    # ── Layer 3: vignette ─────────────────────────────────────────────────
    base = _vignette(base)

    # ── Layer 4: grain ────────────────────────────────────────────────────
    base = _grain(base, strength=8)

    draw = ImageDraw.Draw(base)

    # ── Layer 5: decorative bg elements ───────────────────────────────────
    _draw_decorative_bg(draw, th, t, th["style"])

    # ── Particles ─────────────────────────────────────────────────────────
    if th.get("particles"):
        _particles(draw, t, th.get("p_color", acc), n=35, seed=77)

    # ═══════════════════════════════════════════════════════════════════════
    # CINEMATIC BARS
    # ═══════════════════════════════════════════════════════════════════════
    bar_h = 100
    if t < 0.5:
        bp = _ease_out(t / 0.5)
        ty_top = int(-bar_h + bar_h * bp)
        ty_bot = int(H - bar_h * bp)
    else:
        ty_top = 0
        ty_bot = H - bar_h

    draw.rectangle([0, ty_top, W, ty_top+bar_h],   fill=(0,0,0,248))
    draw.rectangle([0, ty_bot, W, ty_bot+bar_h],   fill=(0,0,0,248))

    bar_a = _slide(t, 0.4, 0.3)
    _hairline(draw, 0, ty_top+bar_h,   W, acc,  bar_a)
    _hairline(draw, 0, ty_bot-1,       W, acc2, bar_a)

    # ═══════════════════════════════════════════════════════════════════════
    # PROGRESS BAR
    # ═══════════════════════════════════════════════════════════════════════
    pb_a   = _slide(t, 0.5, 0.3)
    pb_y   = ty_top + bar_h + 3
    pb_w   = int(W * (t / total))
    # Track
    draw.rectangle([0, pb_y, W, pb_y+3], fill=(*acc, _a(pb_a * 0.2)))
    # Fill with gradient effect
    for px_ in range(0, pb_w, 4):
        shade = 0.7 + 0.3 * (px_ / max(pb_w, 1))
        draw.rectangle([px_, pb_y, px_+4, pb_y+3],
                       fill=(*acc, _a(pb_a * shade)))
    # Glow head
    if 6 < pb_w < W - 6:
        draw.ellipse([pb_w-5, pb_y-2, pb_w+5, pb_y+5],
                     fill=(*acc3, pb_a))

    # ═══════════════════════════════════════════════════════════════════════
    # TOP BAR CONTENT
    # ═══════════════════════════════════════════════════════════════════════
    hdr_a = _slide(t, T_HEADER_IN, 0.4)

    # Topic label with dot
    lbl_fnt = _font(24, bold=True, lang="en")
    lbl_txt = th["name_hi"] if lang == "hi" else th["name"]
    dot_x   = PAD
    dot_y   = ty_top + 44
    # Glowing dot
    draw.ellipse([dot_x-1, dot_y-6, dot_x+11, dot_y+6],
                 fill=(*acc, _a(hdr_a * 0.3)))
    draw.ellipse([dot_x+1, dot_y-4, dot_x+9, dot_y+4],
                 fill=(*acc, hdr_a))
    _text(draw, dot_x+18, dot_y-12, lbl_txt,
          lbl_fnt, acc, hdr_a, shadow=False)

    # Brand name (top right)
    br_fnt = _font(21, bold=False, lang="en")
    br_txt = "cosmos.capsule"
    br_bb  = br_fnt.getbbox(br_txt)
    _text(draw, W - br_bb[2] - PAD, dot_y-10,
          br_txt, br_fnt, mut, _a(hdr_a * 0.8), shadow=False)

    # Language badge
    bd_fnt  = _font(20, bold=True, lang="en")
    bd_txt  = "HI" if lang == "hi" else "EN"
    bd_bb   = bd_fnt.getbbox(bd_txt)
    bd_x    = W - br_bb[2] - PAD - 48
    _glass(draw, bd_x-6, dot_y-12, bd_x+bd_bb[2]+6, dot_y+14,
           fill_col=acc, fill_a=30, stroke_col=acc, stroke_a=60, radius=8)
    _text(draw, bd_x, dot_y-10, bd_txt, bd_fnt, acc, hdr_a, shadow=False)

    # ═══════════════════════════════════════════════════════════════════════
    # HOOK SECTION
    # ═══════════════════════════════════════════════════════════════════════
    hook_a = _slide(t, T_HOOK_IN, 0.5)

    # "DID YOU KNOW?" teaser line
    tease_fnt = _font(32, bold=True, lang=lang)
    tease_txt = "क्या आप जानते हैं? 👀" if lang == "hi" else "DID YOU KNOW? 👀"
    tb        = tease_fnt.getbbox(tease_txt)
    tx_       = (W - tb[2]) // 2
    ty_tease  = H // 2 - 310

    # Pill behind teaser
    _glass(draw, tx_-16, ty_tease-8, tx_+tb[2]+16, ty_tease+tb[3]+8,
           fill_col=acc, fill_a=22, stroke_col=acc, stroke_a=45, radius=22)
    _text(draw, tx_, ty_tease, tease_txt, tease_fnt, acc, hook_a)

    # Thin separator line
    sep_y = ty_tease + tb[3] + 20
    for xi in range(PAD*3, W-PAD*3):
        fade = 1 - abs(xi - W//2) / (W//2 - PAD*3)
        draw.point((xi, sep_y), fill=(*acc, _a(hook_a * 0.4 * fade)))

    # Main hook text
    hook_fnt   = _font(72, bold=True, lang=lang)
    hook_txt   = hook.upper() if lang == "en" else hook
    hook_lines = _wrap(hook_txt, hook_fnt, W - PAD*2 - 16)
    line_h     = 86
    hook_total = len(hook_lines) * line_h
    card_top   = sep_y + 22
    card_bot   = card_top + hook_total + 40

    # Frosted card behind hook
    _glass(draw, PAD-24, card_top-16, W-PAD+24, card_bot+16,
           fill_col=(0,0,0), fill_a=68,
           stroke_col=acc, stroke_a=28, radius=20)

    # Left accent bar
    draw.rounded_rectangle(
        [PAD-24, card_top-16, PAD-21, card_bot+16],
        radius=2, fill=(*acc, _a(hook_a * 0.95))
    )
    # Subtle inner glow at top of card
    draw.rectangle([PAD-24, card_top-16, W-PAD+24, card_top-13],
                   fill=(*acc, _a(hook_a * 0.15)))

    hy = card_top
    for line in hook_lines:
        bb = hook_fnt.getbbox(line)
        hx = (W - bb[2]) // 2
        # Glow pass
        for off in [(0,-1),(0,1),(-1,0),(1,0)]:
            draw.text((hx+off[0], hy+off[1]), line, font=hook_fnt,
                      fill=(*acc3, _a(hook_a*0.12)))
        _text(draw, hx, hy, line, hook_fnt, txt, hook_a)
        hy += line_h

    # ═══════════════════════════════════════════════════════════════════════
    # WORD-BY-WORD SUBTITLES
    # ═══════════════════════════════════════════════════════════════════════
    body_card_a = _slide(t, T_BODY_IN, 0.5)

    if body_card_a > 0:
        sub_elapsed   = max(0, t - T_SUBS_START)
        sub_window    = T_TAGS_IN - T_SUBS_START
        word_interval = sub_window / max(len(body_words), 1)
        n_words       = min(len(body_words),
                            int(sub_elapsed / word_interval) + 1)

        sub_fnt   = _font(40, bold=False, lang=lang)
        sub_bold  = _font(40, bold=True,  lang=lang)
        sub_lines = _wrap(" ".join(body_words[:n_words]),
                          sub_fnt, W - PAD*2 - 10)
        sub_lh    = 54
        sub_total = len(sub_lines) * sub_lh
        sub_top   = card_bot + 40

        # Frosted card for body
        _glass(draw, PAD-20, sub_top-14, W-PAD+20, sub_top+sub_total+14,
               fill_col=(0,0,0), fill_a=62,
               stroke_col=acc2, stroke_a=22, radius=16)

        # Small accent corner markers
        mark_size = 8
        for mx, my in [(PAD-20, sub_top-14), (W-PAD+20-mark_size, sub_top-14)]:
            draw.rectangle([mx, my, mx+mark_size, my+2],
                           fill=(*acc2, _a(body_card_a*0.6)))
            draw.rectangle([mx, my, mx+2, my+mark_size],
                           fill=(*acc2, _a(body_card_a*0.6)))

        for li, sline in enumerate(sub_lines):
            sy_      = sub_top + li * sub_lh
            is_last  = li == len(sub_lines) - 1
            words_   = sline.split()

            if is_last and words_ and t >= T_SUBS_START:
                # Highlight last word
                normal = " ".join(words_[:-1])
                last_w = words_[-1]
                fl_bb  = sub_fnt.getbbox(sline)
                line_x = (W - fl_bb[2]) // 2

                if normal:
                    np_bb = sub_fnt.getbbox(normal + " ")
                    _text(draw, line_x, sy_, normal+" ", sub_fnt,
                          txt, body_card_a)
                    lw_x = line_x + np_bb[2]
                else:
                    lw_x = line_x

                lw_bb = sub_bold.getbbox(last_w)
                # Pill behind highlighted word
                _glass(draw, lw_x-6, sy_-4, lw_x+lw_bb[2]+6, sy_+lw_bb[3]+4,
                       fill_col=acc, fill_a=28,
                       stroke_col=acc, stroke_a=50, radius=8)
                _text(draw, lw_x, sy_, last_w, sub_bold, acc, body_card_a)
            else:
                bb_   = sub_fnt.getbbox(sline)
                sx_   = (W - bb_[2]) // 2
                _text(draw, sx_, sy_, sline, sub_fnt, txt, body_card_a)

    # ═══════════════════════════════════════════════════════════════════════
    # HASHTAG STRIP
    # ═══════════════════════════════════════════════════════════════════════
    tag_a = _slide(t, T_TAGS_IN, 0.45)
    if tag_a > 0 and tags:
        tag_fnt = _font(24, bold=False, lang=lang)
        tag_top = H - 195

        _glass(draw, PAD-16, tag_top-8, W-PAD+16, tag_top+64,
               fill_col=(0,0,0), fill_a=55,
               stroke_col=acc, stroke_a=25, radius=14)

        for ri, row in enumerate(["   ".join(tags[:3]),
                                   "   ".join(tags[3:6])]):
            if not row: continue
            rb  = tag_fnt.getbbox(row)
            rx_ = (W - rb[2]) // 2
            ry_ = tag_top + ri * 30
            _text(draw, rx_, ry_, row, tag_fnt, acc, _a(tag_a * 0.88))

    # ═══════════════════════════════════════════════════════════════════════
    # BOTTOM CTA
    # ═══════════════════════════════════════════════════════════════════════
    cta_a = _slide(t, T_CTA_IN, 0.5)

    # Gradient fade into bottom bar
    for i in range(bar_h + 20):
        fa = _a(240 * ((i / (bar_h + 20)) ** 1.8))
        draw.rectangle([0, ty_bot+i, W, ty_bot+i+1],
                       fill=(0,0,0, fa))

    cta_fnt  = _font(30, bold=True, lang=lang)
    cta_bb   = cta_fnt.getbbox(follow_text)
    ctx_     = (W - cta_bb[2]) // 2
    cty_     = ty_bot + (bar_h - cta_bb[3]) // 2 - 4

    # Pulsing glow dot before CTA
    pulse = 0.8 + 0.2 * math.sin(t * 4)
    dot_r = 5
    draw.ellipse([ctx_-22-dot_r, cty_+10-dot_r,
                  ctx_-22+dot_r, cty_+10+dot_r],
                 fill=(*acc, _a(cta_a * pulse)))

    _text(draw, ctx_, cty_, follow_text, cta_fnt,
          acc, _a(cta_a * pulse))

    # Up arrow
    arr_fnt = _font(26, bold=True, lang="en")
    draw.text((ctx_ + cta_bb[2] + 10, cty_+3), "↑",
              font=arr_fnt, fill=(*acc2, _a(cta_a * pulse)))

    return np.array(base.convert("RGB"))


# ── VideoCreator ───────────────────────────────────────────────────────────────

class VideoCreator:
    def create_reel(self, image_path: Path, music_path: Path,
                    fact_data: dict, topic: dict,
                    lang: str, output_dir: Path) -> Path:

        log.info(f"🎬 Rendering ultra-premium [{lang.upper()}] reel…")

        import config as cfg
        topic_key = "space"
        for k, v in cfg.TOPICS.items():
            if (v.get("name") == topic.get("name") or
                    v.get("name_hi") == topic.get("name_hi")):
                topic_key = k
                break

        bg          = Image.open(image_path).convert("RGB")
        hook        = fact_data["hook"]
        body        = fact_data["body"]
        body_words  = body.split()
        follow_text = LANGUAGES[lang]["follow_text"]
        tags        = VIDEO_TAGS.get(f"{topic_key}_{lang}", ["#cosmoscapsule"])

        def make_frame(t):
            return _make_frame(bg, hook, body, body_words,
                               topic_key, topic, lang,
                               follow_text, tags, t, REEL_DURATION)

        clip = VideoClip(make_frame, duration=REEL_DURATION).set_fps(REEL_FPS)
        clip = fadein(clip, 0.4)
        clip = fadeout(clip, 0.6)

        audio = (AudioFileClip(str(music_path))
                 .subclip(0, REEL_DURATION)
                 .audio_fadeout(2.5)
                 .volumex(MUSIC_VOLUME))
        clip = clip.set_audio(audio)

        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        cat_slug = (fact_data.get("fact_category", topic["name"])[:20]
                    .replace(" ", "_").lower())
        out_path = output_dir / f"reel_{cat_slug}_{lang}_{ts}.mp4"

        log.info(f"💾 Writing → {out_path.name}")
        clip.write_videofile(
            str(out_path),
            codec="libx264", audio_codec="aac",
            fps=REEL_FPS, preset="fast",
            bitrate="4500k", audio_bitrate="192k",
            ffmpeg_params=["-vf", f"scale={W}:{H}"],
            logger=None,
        )
        log.info(f"✅ [{lang.upper()}] {out_path.stat().st_size / 1e6:.1f} MB")
        return out_path
