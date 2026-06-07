"""
src/video.py — Premium Netflix/Apple-style Reel renderer

Reach-boosting features:
  1. Instant hook text (appears in first 0.3s)
  2. Countdown 3→2→1 reveal before main content
  3. Animated word-by-word subtitles
  4. Cinematic letterbox bars (movie feel)
  5. Progress bar (increases completion rate)
  6. Optimised first-frame thumbnail

Design: Minimalist dark luxury (Apple/Netflix)
  - Pure black/near-black backgrounds
  - Single accent color per topic (no busy gradients)
  - SF Pro / Liberation tight tracking
  - Thin hairline dividers
  - Restrained motion — only what matters moves
"""

import math
import random
import logging
from pathlib import Path
from datetime import datetime

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from moviepy.editor import VideoClip, AudioFileClip
from moviepy.video.fx.all import fadein, fadeout

from config import (REEL_WIDTH, REEL_HEIGHT, REEL_DURATION,
                    REEL_FPS, MUSIC_VOLUME, LANGUAGES)

log      = logging.getLogger(__name__)
W, H     = REEL_WIDTH, REEL_HEIGHT
PAD      = 64
ROOT     = Path(__file__).parent.parent
FONTS_DIR = ROOT / "fonts"
FONTS_DIR.mkdir(exist_ok=True)

# ── Timing constants (seconds) ─────────────────────────────────────────────────
T_LETTERBOX_IN  = 0.0    # cinematic bars slide in immediately
T_HOOK_IN       = 0.3    # instant hook line appears
T_COUNTDOWN     = 2.5    # countdown 3→2→1 starts
T_CONTENT       = 5.5    # main content (hook card + body) appears
T_SUBS_START    = 6.5    # animated subtitles begin
T_TAGS          = 14.0   # hashtag strip fades in
T_CTA           = 16.0   # follow CTA pulses

# ── Per-topic luxury themes ────────────────────────────────────────────────────
THEMES = {
    "space": {
        "accent":   (100, 180, 255),   # ice blue
        "accent2":  (160, 120, 255),   # soft violet
        "bg_tint":  (5,   8,   20),    # near-black blue
        "text":     (235, 242, 255),
        "particles": True,
        "label_en": "SPACE & UNIVERSE",
        "label_hi": "अंतरिक्ष और ब्रह्मांड",
    },
    "history": {
        "accent":   (210, 170,  80),   # antique gold
        "accent2":  (180, 130,  60),
        "bg_tint":  (18,  12,   4),
        "text":     (255, 245, 220),
        "particles": False,
        "label_en": "WORLD HISTORY",
        "label_hi": "विश्व इतिहास",
    },
    "geography": {
        "accent":   ( 70, 210, 120),   # emerald
        "accent2":  ( 40, 170,  90),
        "bg_tint":  ( 4,  16,   8),
        "text":     (215, 255, 230),
        "particles": False,
        "label_en": "GEOGRAPHY",
        "label_hi": "भूगोल",
    },
    "science": {
        "accent":   (180, 100, 255),   # electric violet
        "accent2":  (130,  70, 220),
        "bg_tint":  (12,   4,  22),
        "text":     (238, 220, 255),
        "particles": True,
        "label_en": "SCIENCE FACTS",
        "label_hi": "विज्ञान तथ्य",
    },
    "sports": {
        "accent":   (255, 200,  40),   # championship gold
        "accent2":  (255, 150,  20),
        "bg_tint":  ( 6,  14,   4),
        "text":     (255, 252, 220),
        "particles": False,
        "label_en": "SPORTS NEWS",
        "label_hi": "खेल समाचार",
    },
    "worldnews": {
        "accent":   (255,  80,  70),   # breaking red
        "accent2":  (220,  60,  50),
        "bg_tint":  (20,   4,   4),
        "text":     (255, 230, 228),
        "particles": False,
        "label_en": "WORLD NEWS",
        "label_hi": "विश्व समाचार",
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
    if dest.exists():
        return
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)
    except Exception as e:
        log.warning(f"Font DL failed: {e}")

def _font(size: int, bold: bool = False, lang: str = "en"):
    key = f"{lang}_{size}_{bold}"
    if key in FONT_CACHE:
        return FONT_CACHE[key]
    cands = []
    if lang == "hi":
        lc = LANGUAGES["hi"]
        bp = FONTS_DIR / "NotoSansDevanagari-Bold.ttf"
        rp = FONTS_DIR / "NotoSansDevanagari-Regular.ttf"
        _dl_font(lc["font_url"],     bp)
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

# ── Drawing primitives ─────────────────────────────────────────────────────────

def _wrap(text: str, fnt, max_w: int) -> list:
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if fnt.getbbox(t)[2] <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def _alpha(val: float) -> int:
    return max(0, min(255, int(val)))

def _ease_in_out(x: float) -> float:
    """Smooth cubic ease."""
    return 3 * x * x - 2 * x * x * x

def _ease_out(x: float) -> float:
    return 1 - (1 - x) ** 3

def _slide_alpha(t: float, start: float, dur: float = 0.35) -> int:
    if t < start:
        return 0
    return _alpha(_ease_out(min(1.0, (t - start) / dur)) * 255)

def _draw_text_crisp(draw, x, y, text, fnt, color, alpha):
    """Crisp text with single subtle shadow — Apple style."""
    draw.text((x + 2, y + 2), text, font=fnt, fill=(0, 0, 0, _alpha(alpha * 0.35)))
    draw.text((x, y), text, font=fnt, fill=(*color, _alpha(alpha)))

def _draw_hairline(draw, x1, y, x2, color, alpha):
    draw.rectangle([x1, y, x2, y + 1], fill=(*color, _alpha(alpha)))

def _draw_particles(draw, t: float, color: tuple, n: int = 35, seed: int = 7):
    rng = random.Random(seed)
    for _ in range(n):
        px = rng.randint(0, W)
        py = rng.randint(0, H)
        sz = rng.choice([1, 1, 1, 2, 2, 3])
        sp = rng.uniform(0.2, 1.0)
        py2 = int((py - t * sp * 15) % H)
        pulse = 0.5 + 0.5 * math.sin(t * sp * 1.5 + px * 0.01)
        a = _alpha(140 * pulse)
        draw.ellipse([px-sz, py2-sz, px+sz, py2+sz], fill=(*color, a))


# ── Frame renderer ─────────────────────────────────────────────────────────────

def _make_frame(bg: Image.Image, hook: str, body: str, body_words: list,
                topic_key: str, topic: dict, lang: str,
                follow_text: str, tags: list,
                t: float, total: float) -> np.ndarray:

    th = THEMES.get(topic_key, THEMES["space"])
    acc  = th["accent"]
    acc2 = th["accent2"]
    txt  = th["text"]
    tint = th["bg_tint"]

    # ── Background: darkened + tinted image ───────────────────────────────
    scale = 1.0 + 0.04 * (t / total)   # very subtle Ken Burns
    nw, nh = int(W * scale), int(H * scale)
    bg_s  = bg.resize((nw, nh), Image.LANCZOS)
    lft   = (nw - W) // 2
    top_  = (nh - H) // 2
    frame = bg_s.crop((lft, top_, lft + W, top_ + H)).convert("RGB")

    # Desaturate slightly → luxury feel
    frame = ImageEnhance.Color(frame).enhance(0.75)
    frame = ImageEnhance.Brightness(frame).enhance(0.55)   # darker = premium

    # Tint overlay
    tint_layer = Image.new("RGB", (W, H), tint)
    frame = Image.blend(frame, tint_layer, alpha=0.55)
    frame = frame.convert("RGBA")

    # Vignette (dark edges → cinema look)
    vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd  = ImageDraw.Draw(vig)
    for r in range(0, min(W, H) // 2, 8):
        a_vig = _alpha(180 * (1 - r / (min(W, H) // 2)) ** 2)
        vd.rectangle([r, r, W - r, H - r],
                     outline=(0, 0, 0, a_vig), width=8)
    frame = Image.alpha_composite(frame, vig)

    draw = ImageDraw.Draw(frame)

    # ── Particles ────────────────────────────────────────────────────────
    if th.get("particles"):
        _draw_particles(draw, t, acc, n=30, seed=42)

    # ── Cinematic letterbox bars ──────────────────────────────────────────
    # Slide in from top and bottom over 0.4s
    bar_h = 90
    if t < 0.4:
        bar_prog = _ease_out(t / 0.4)
        top_bar_y  = int(-bar_h + bar_h * bar_prog)
        bot_bar_y  = int(H - bar_h * bar_prog)
    else:
        top_bar_y  = 0
        bot_bar_y  = H - bar_h

    draw.rectangle([0, top_bar_y, W, top_bar_y + bar_h], fill=(0, 0, 0, 240))
    draw.rectangle([0, bot_bar_y, W, bot_bar_y + bar_h], fill=(0, 0, 0, 240))

    # Thin accent line at letterbox edges
    _draw_hairline(draw, 0, top_bar_y + bar_h, W, acc, _slide_alpha(t, 0.4))
    _draw_hairline(draw, 0, bot_bar_y - 1,     W, acc, _slide_alpha(t, 0.4))

    # ── Progress bar (thin, at very top) ─────────────────────────────────
    prog_a = _slide_alpha(t, 0.5)
    prog_w = int(W * (t / total))
    # Track
    draw.rectangle([0, top_bar_y + bar_h + 2, W, top_bar_y + bar_h + 4],
                   fill=(*acc, _alpha(prog_a * 0.25)))
    # Fill
    if prog_w > 0:
        draw.rectangle([0, top_bar_y + bar_h + 2, prog_w, top_bar_y + bar_h + 4],
                       fill=(*acc, prog_a))
    # Glowing dot at progress head
    if 4 < prog_w < W - 4:
        draw.ellipse([prog_w - 4, top_bar_y + bar_h,
                      prog_w + 4, top_bar_y + bar_h + 8],
                     fill=(*acc, prog_a))

    # ── Top bar content: topic label + brand ─────────────────────────────
    label_a = _slide_alpha(t, 0.2)
    lbl_fnt = _font(26, bold=True, lang="en")   # always EN for label
    lbl_key = "label_hi" if lang == "hi" else "label_en"
    lbl_txt = th.get(lbl_key, topic.get("name", ""))
    # Dot + label
    dot_x = PAD
    dot_y = top_bar_y + 38
    draw.ellipse([dot_x, dot_y - 5, dot_x + 10, dot_y + 5],
                 fill=(*acc, label_a))
    draw.text((dot_x + 18, dot_y - 12), lbl_txt, font=lbl_fnt,
              fill=(*acc, label_a))

    # Brand top-right
    br_fnt  = _font(22, bold=False, lang="en")
    br_text = "cosmos.capsule"
    br_bbox = br_fnt.getbbox(br_text)
    draw.text((W - br_bbox[2] - PAD, dot_y - 10),
              br_text, font=br_fnt, fill=(*txt, _alpha(label_a * 0.7)))

    # Lang badge
    bd_fnt  = _font(22, bold=True, lang="en")
    bd_text = "HI" if lang == "hi" else "EN"
    draw.text((W - br_bbox[2] - PAD - 50, dot_y - 10),
              bd_text, font=bd_fnt, fill=(*acc2, label_a))

    # ── INSTANT HOOK LINE (appears at 0.3s) ───────────────────────────────
    # Short teaser line above main content — stops the scroll
    hook_a   = _slide_alpha(t, T_HOOK_IN, dur=0.25)
    tease_fnt = _font(38, bold=True, lang=lang)
    if lang == "en":
        tease = "DID YOU KNOW? 👀"
    else:
        tease = "क्या आप जानते हैं? 👀"
    tb      = tease_fnt.getbbox(tease)
    tx      = (W - tb[2]) // 2
    ty      = H // 2 - 320
    _draw_text_crisp(draw, tx, ty, tease, tease_fnt, acc, hook_a)

    # Hairline below tease
    _draw_hairline(draw, PAD * 2, ty + 52, W - PAD * 2, acc,
                   _alpha(hook_a * 0.5))

    # ── COUNTDOWN 3 → 2 → 1 ──────────────────────────────────────────────
    if T_COUNTDOWN <= t < T_CONTENT:
        elapsed = t - T_COUNTDOWN
        cd_dur  = (T_CONTENT - T_COUNTDOWN) / 3.0   # each digit shown ~1s
        digit   = 3 - int(elapsed / cd_dur)
        digit   = max(1, min(3, digit))
        frac    = (elapsed % cd_dur) / cd_dur

        # Pulse: grows then fades
        if frac < 0.4:
            cd_scale = 1.0 + 0.15 * _ease_out(frac / 0.4)
            cd_alpha = 255
        else:
            cd_scale = 1.15
            cd_alpha = _alpha(255 * (1 - (frac - 0.4) / 0.6))

        cd_size = int(160 * cd_scale)
        cd_fnt  = _font(cd_size, bold=True, lang="en")
        cd_str  = str(digit)
        cd_bbox = cd_fnt.getbbox(cd_str)
        cdx     = (W - cd_bbox[2]) // 2
        cdy     = H // 2 - cd_bbox[3] // 2 - 20

        # Circle behind countdown
        r = cd_size // 2 + 30
        draw.ellipse([W//2 - r, H//2 - r - 20,
                      W//2 + r, H//2 + r - 20],
                     fill=(*acc, _alpha(cd_alpha * 0.12)))
        draw.ellipse([W//2 - r + 3, H//2 - r - 17,
                      W//2 + r - 3, H//2 + r - 23],
                     outline=(*acc, _alpha(cd_alpha * 0.4)), width=2)

        _draw_text_crisp(draw, cdx, cdy, cd_str, cd_fnt, acc, cd_alpha)

    # ── MAIN HOOK CARD (appears at T_CONTENT) ────────────────────────────
    content_a = _slide_alpha(t, T_CONTENT, dur=0.5)

    if content_a > 0:
        hook_fnt   = _font(70, bold=True, lang=lang)
        hook_text  = hook.upper() if lang == "en" else hook
        hook_lines = _wrap(hook_text, hook_fnt, W - PAD * 2 - 20)
        line_h     = 84
        hook_h     = len(hook_lines) * line_h
        card_y     = H // 2 - hook_h // 2 - 60
        card_pad   = 28

        # Luxury card: very subtle white stroke, near-black fill
        draw.rounded_rectangle(
            [PAD - card_pad, card_y - card_pad,
             W - PAD + card_pad, card_y + hook_h + card_pad],
            radius=16,
            fill=(0, 0, 0, _alpha(content_a * 0.72)),
            outline=(*acc, _alpha(content_a * 0.25)),
            width=1,
        )

        # Left accent stripe
        draw.rounded_rectangle(
            [PAD - card_pad, card_y - card_pad,
             PAD - card_pad + 3, card_y + hook_h + card_pad],
            radius=2, fill=(*acc, _alpha(content_a * 0.9))
        )

        hy = card_y
        for line in hook_lines:
            bb  = hook_fnt.getbbox(line)
            hx  = (W - bb[2]) // 2
            _draw_text_crisp(draw, hx, hy, line, hook_fnt, txt, content_a)
            hy += line_h

    # ── ANIMATED SUBTITLES word-by-word ──────────────────────────────────
    if t >= T_SUBS_START and content_a > 0:
        sub_elapsed  = t - T_SUBS_START
        sub_duration = T_TAGS - T_SUBS_START
        word_interval = sub_duration / max(len(body_words), 1)
        words_shown  = min(len(body_words),
                           int(sub_elapsed / word_interval) + 1)

        sub_fnt  = _font(38, bold=False, lang=lang)
        sub_line = " ".join(body_words[:words_shown])
        sub_lines = _wrap(sub_line, sub_fnt, W - PAD * 2)

        sub_line_h = 52
        sub_total  = len(sub_lines) * sub_line_h
        sub_y      = H // 2 + 130

        # Subtitle card
        if sub_lines:
            draw.rounded_rectangle(
                [PAD - 20, sub_y - 14,
                 W - PAD + 20, sub_y + sub_total + 14],
                radius=12,
                fill=(0, 0, 0, _alpha(content_a * 0.65)),
            )

        # Last word highlight
        for li, sline in enumerate(sub_lines):
            words_in_line = sline.split()
            is_last_line  = li == len(sub_lines) - 1
            sy = sub_y + li * sub_line_h

            if is_last_line and words_in_line:
                # Render all but last word normally
                normal_part = " ".join(words_in_line[:-1])
                last_word   = words_in_line[-1]

                # Measure normal part
                np_fnt  = _font(38, bold=False, lang=lang)
                lw_fnt  = _font(38, bold=True,  lang=lang)

                if normal_part:
                    np_bb = np_fnt.getbbox(normal_part + " ")
                    np_w  = np_bb[2]
                else:
                    np_w = 0

                # Full line width to center
                full_line = sline
                fl_bb     = np_fnt.getbbox(full_line)
                line_x    = (W - fl_bb[2]) // 2

                if normal_part:
                    _draw_text_crisp(draw, line_x, sy,
                                     normal_part + " ", np_fnt,
                                     txt, content_a)
                # Highlighted last word
                lw_bb = lw_fnt.getbbox(last_word)
                lw_x  = line_x + np_w
                # Accent pill behind last word
                pill_pad = 6
                draw.rounded_rectangle(
                    [lw_x - pill_pad, sy - 4,
                     lw_x + lw_bb[2] + pill_pad, sy + lw_bb[3] + 4],
                    radius=8,
                    fill=(*acc, _alpha(content_a * 0.25)),
                )
                _draw_text_crisp(draw, lw_x, sy, last_word,
                                 lw_fnt, acc, content_a)
            else:
                bb  = sub_fnt.getbbox(sline)
                sx_ = (W - bb[2]) // 2
                _draw_text_crisp(draw, sx_, sy, sline,
                                 sub_fnt, txt, content_a)

    # ── HASHTAG STRIP ────────────────────────────────────────────────────
    tag_a = _slide_alpha(t, T_TAGS, dur=0.4)
    if tag_a > 0 and tags:
        tag_fnt = _font(24, bold=False, lang=lang)
        tag_y   = H - 185
        # Subtle card
        draw.rounded_rectangle(
            [PAD - 16, tag_y - 8, W - PAD + 16, tag_y + 62],
            radius=10, fill=(0, 0, 0, _alpha(tag_a * 0.5)),
        )
        row1 = "   ".join(tags[:3])
        row2 = "   ".join(tags[3:6])
        for ri, row in enumerate([row1, row2]):
            if not row:
                continue
            rb   = tag_fnt.getbbox(row)
            rx   = (W - rb[2]) // 2
            ry   = tag_y + ri * 30
            draw.text((rx + 1, ry + 1), row, font=tag_fnt,
                      fill=(0, 0, 0, _alpha(tag_a * 0.4)))
            draw.text((rx, ry), row, font=tag_fnt,
                      fill=(*acc, _alpha(tag_a * 0.9)))

    # ── BOTTOM BAR: Follow CTA ────────────────────────────────────────────
    cta_a = _slide_alpha(t, T_CTA, dur=0.5)

    # Gradient fade bottom
    for i in range(bar_h):
        ba = _alpha(230 * (i / bar_h) ** 1.5)
        draw.rectangle([0, bot_bar_y + i, W, bot_bar_y + i + 1],
                       fill=(0, 0, 0, ba))

    # CTA text
    cta_fnt  = _font(30, bold=True, lang=lang)
    cta_text = follow_text
    cta_bb   = cta_fnt.getbbox(cta_text)
    ctx      = (W - cta_bb[2]) // 2
    cty      = bot_bar_y + (bar_h - cta_bb[3]) // 2 - 4

    # Pulsing glow on CTA
    pulse = 0.85 + 0.15 * math.sin(t * 3.5)
    _draw_text_crisp(draw, ctx, cty, cta_text, cta_fnt,
                     acc, _alpha(cta_a * pulse))

    # Small arrow after CTA
    arr_fnt = _font(28, bold=True, lang="en")
    draw.text((ctx + cta_bb[2] + 10, cty + 2), "↑",
              font=arr_fnt, fill=(*acc, _alpha(cta_a * pulse)))

    return np.array(frame.convert("RGB"))


# ── VideoCreator ───────────────────────────────────────────────────────────────

class VideoCreator:
    def create_reel(self, image_path: Path, music_path: Path,
                    fact_data: dict, topic: dict, lang: str,
                    output_dir: Path) -> Path:

        log.info(f"🎬 Rendering premium [{lang.upper()}] reel…")

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
        clip = fadein(clip, 0.3)
        clip = fadeout(clip, 0.5)

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
