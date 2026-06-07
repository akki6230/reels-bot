"""
src/video.py — Premium Reel renderer with:
- Animated gradient overlays per topic
- Particle/star effects (space topic)
- Glassmorphism text cards
- Decorative geometric shapes
- Painted/abstract color washes
- Beautiful typography with glow effects
- 5-6 hashtag tags overlaid on video
"""

import math
import random
import logging
import struct
import wave
from pathlib import Path
from datetime import datetime

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy.editor import VideoClip, AudioFileClip
from moviepy.video.fx.all import fadein, fadeout

from config import REEL_WIDTH, REEL_HEIGHT, REEL_DURATION, REEL_FPS, MUSIC_VOLUME, LANGUAGES

log = logging.getLogger(__name__)

W, H      = REEL_WIDTH, REEL_HEIGHT
PAD       = 72
ROOT      = Path(__file__).parent.parent
FONTS_DIR = ROOT / "fonts"
FONTS_DIR.mkdir(exist_ok=True)

# ── Video tags per topic ───────────────────────────────────────────────────────

VIDEO_TAGS = {
    "space_en":     ["#space", "#universe", "#NASA", "#spacefacts", "#didyouknow", "#cosmoscapsule"],
    "space_hi":     ["#अंतरिक्ष", "#ब्रह्मांड", "#विज्ञान", "#तथ्य", "#इसरो", "#cosmoscapsule"],
    "history_en":   ["#history", "#ancienthistory", "#historyfacts", "#didyouknow", "#civilization", "#cosmoscapsule"],
    "history_hi":   ["#इतिहास", "#प्राचीनइतिहास", "#तथ्य", "#ज्ञान", "#सभ्यता", "#cosmoscapsule"],
    "geography_en": ["#geography", "#earthfacts", "#nature", "#travel", "#amazingearth", "#cosmoscapsule"],
    "geography_hi": ["#भूगोल", "#पृथ्वी", "#प्रकृति", "#यात्रा", "#तथ्य", "#cosmoscapsule"],
    "science_en":   ["#science", "#sciencefacts", "#physics", "#biology", "#mindblown", "#cosmoscapsule"],
    "science_hi":   ["#विज्ञान", "#विज्ञानतथ्य", "#भौतिकी", "#जीवविज्ञान", "#तथ्य", "#cosmoscapsule"],
    "sports_en":    ["#sports", "#cricket", "#IPL", "#football", "#athlete", "#cosmoscapsule"],
    "sports_hi":    ["#खेल", "#क्रिकेट", "#आईपीएल", "#फुटबॉल", "#खिलाड़ी", "#cosmoscapsule"],
    "worldnews_en": ["#worldnews", "#breakingnews", "#NASA", "#ISRO", "#geopolitics", "#cosmoscapsule"],
    "worldnews_hi": ["#विश्वसमाचार", "#ताजाखबर", "#राजनीति", "#नासा", "#इसरो", "#cosmoscapsule"],
}

# ── Theme definitions per topic ────────────────────────────────────────────────

THEMES = {
    "space": {
        "gradient_colors": [(5, 5, 30), (15, 5, 50), (5, 10, 80), (20, 0, 60)],
        "accent":          (120, 180, 255),
        "accent2":         (180, 120, 255),
        "text":            (220, 240, 255),
        "glow":            (80, 140, 255),
        "particles":       True,
        "particle_color":  (255, 255, 255),
        "style":           "cosmic",
        "overlay_alpha":   130,
    },
    "history": {
        "gradient_colors": [(40, 20, 5), (70, 40, 10), (50, 25, 5), (80, 50, 15)],
        "accent":          (220, 170, 90),
        "accent2":         (200, 120, 60),
        "text":            (255, 240, 210),
        "glow":            (200, 150, 80),
        "particles":       False,
        "style":           "parchment",
        "overlay_alpha":   140,
    },
    "geography": {
        "gradient_colors": [(5, 30, 15), (10, 60, 30), (5, 45, 20), (15, 70, 40)],
        "accent":          (80, 220, 130),
        "accent2":         (50, 180, 100),
        "text":            (210, 255, 225),
        "glow":            (60, 200, 110),
        "particles":       False,
        "style":           "nature",
        "overlay_alpha":   135,
    },
    "science": {
        "gradient_colors": [(20, 5, 40), (40, 10, 70), (15, 5, 55), (50, 20, 80)],
        "accent":          (190, 110, 255),
        "accent2":         (130, 80, 255),
        "text":            (235, 215, 255),
        "glow":            (160, 90, 255),
        "particles":       True,
        "particle_color":  (200, 150, 255),
        "style":           "tech",
        "overlay_alpha":   130,
    },
    "sports": {
        "gradient_colors": [(5, 20, 5), (10, 40, 10), (20, 50, 5), (15, 60, 20)],
        "accent":          (255, 210, 50),
        "accent2":         (255, 160, 30),
        "text":            (255, 250, 210),
        "glow":            (255, 190, 40),
        "particles":       False,
        "style":           "dynamic",
        "overlay_alpha":   140,
    },
    "worldnews": {
        "gradient_colors": [(35, 5, 5), (60, 15, 10), (45, 8, 8), (70, 20, 15)],
        "accent":          (255, 110, 90),
        "accent2":         (255, 80, 60),
        "text":            (255, 230, 225),
        "glow":            (255, 90, 70),
        "particles":       False,
        "style":           "news",
        "overlay_alpha":   145,
    },
}

# ── Font management ────────────────────────────────────────────────────────────

FONT_CACHE: dict = {}

def _download_font(url: str, dest: Path):
    if dest.exists():
        return
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)
        log.info(f"Font saved: {dest.name}")
    except Exception as e:
        log.warning(f"Font download failed: {e}")

def _get_font(size: int, bold: bool = False, lang: str = "en") -> ImageFont.FreeTypeFont:
    cache_key = f"{lang}_{size}_{bold}"
    if cache_key in FONT_CACHE:
        return FONT_CACHE[cache_key]
    candidates = []
    if lang == "hi":
        lang_cfg  = LANGUAGES["hi"]
        bold_path = FONTS_DIR / "NotoSansDevanagari-Bold.ttf"
        reg_path  = FONTS_DIR / "NotoSansDevanagari-Regular.ttf"
        _download_font(lang_cfg["font_url"],     bold_path)
        _download_font(lang_cfg["font_url_reg"], reg_path)
        candidates = [bold_path if bold else reg_path]
    candidates += [
        FONTS_DIR / ("Poppins-Bold.ttf" if bold else "Poppins-Regular.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
             else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
             else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for p in candidates:
        if Path(p).exists():
            font = ImageFont.truetype(str(p), size)
            FONT_CACHE[cache_key] = font
            return font
    return ImageFont.load_default()

# ── Drawing helpers ────────────────────────────────────────────────────────────

def _wrap(text: str, font, max_w: int) -> list:
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.getbbox(test)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def _draw_glow_text(draw, x, y, text, font, color, alpha, glow_color, glow_r=8):
    """Draw text with a soft glow effect behind it."""
    gr, gg, gb = glow_color
    for offset in range(glow_r, 0, -2):
        glow_a = int(alpha * 0.15 * (1 - offset / glow_r))
        for dx in range(-offset, offset + 1, offset):
            for dy in range(-offset, offset + 1, offset):
                draw.text((x + dx, y + dy), text, font=font,
                          fill=(gr, gg, gb, glow_a))
    # Shadow
    draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, alpha // 3))
    # Main text
    draw.text((x, y), text, font=font, fill=(*color, alpha))

def _draw_glass_card(draw, x1, y1, x2, y2, color=(255,255,255), alpha=25, radius=20):
    """Draw a glassmorphism card (semi-transparent rounded rectangle)."""
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius,
                            fill=(*color, alpha),
                            outline=(*color, alpha + 20), width=1)

def _draw_gradient_overlay(frame: Image.Image, colors: list,
                            alpha: int, t: float) -> Image.Image:
    """Draw an animated diagonal gradient overlay."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    # Slow animated gradient shift
    shift = int(t * 30) % H

    for y in range(H):
        # Diagonal gradient with time-based animation
        fy  = ((y + shift) % H) / H
        fx  = 0.5
        idx = fy * (len(colors) - 1)
        i   = min(int(idx), len(colors) - 2)
        frac = idx - i
        c1, c2 = colors[i], colors[i + 1]
        r = int(c1[0] + (c2[0] - c1[0]) * frac)
        g = int(c1[1] + (c2[1] - c1[1]) * frac)
        b = int(c1[2] + (c2[2] - c1[2]) * frac)
        # Apply as a subtle tint
        for x in range(0, W, 4):   # every 4px for speed
            draw.point((x, y), fill=(r, g, b, alpha // 3))

    return Image.alpha_composite(frame, overlay)

def _draw_particles(draw, t: float, color: tuple, count: int = 40, seed: int = 42):
    """Draw animated floating particles (stars/dots)."""
    rng = random.Random(seed)
    for _ in range(count):
        px    = rng.randint(0, W)
        py    = rng.randint(0, H)
        size  = rng.randint(1, 4)
        speed = rng.uniform(0.3, 1.5)
        # Gentle floating motion
        py_anim = int((py + t * speed * 20) % H)
        pulse   = 0.6 + 0.4 * math.sin(t * speed * 2 + px)
        alpha   = int(180 * pulse)
        draw.ellipse([px - size, py_anim - size, px + size, py_anim + size],
                     fill=(*color, alpha))

def _draw_decorative_lines(draw, theme: dict, progress: float):
    """Draw subtle decorative geometric lines for aesthetics."""
    accent  = theme["accent"]
    accent2 = theme["accent2"]
    a       = min(60, int(progress * 60 * 3))

    # Top decorative bar with gradient effect
    for i in range(4):
        line_a = a - i * 12
        if line_a > 0:
            draw.rectangle([PAD, 180 + i * 3, W - PAD, 181 + i * 3],
                           fill=(*accent, line_a))

    # Bottom decorative elements
    for i in range(3):
        line_a = a - i * 15
        if line_a > 0:
            draw.rectangle([PAD, H - 160 - i * 3, W - PAD, H - 159 - i * 3],
                           fill=(*accent2, line_a))

    # Corner accents (top-right)
    corner_a = min(80, int(progress * 80 * 4))
    if corner_a > 0:
        draw.rectangle([W - 120, 40, W - 40, 42],
                       fill=(*accent, corner_a))
        draw.rectangle([W - 42, 40, W - 40, 120],
                       fill=(*accent, corner_a))

    # Corner accents (bottom-left)
    draw.rectangle([40, H - 42, 120, H - 40],
                   fill=(*accent2, corner_a))
    draw.rectangle([40, H - 120, 42, H - 40],
                   fill=(*accent2, corner_a))

def _draw_abstract_shapes(draw, theme: dict, t: float, progress: float):
    """Draw subtle animated abstract shapes in background."""
    style  = theme.get("style", "cosmic")
    accent = theme["accent"]
    a      = min(25, int(progress * 25 * 2))   # very subtle

    if style == "cosmic":
        # Concentric circles suggestion (nebula-like)
        cx, cy = W // 2, H // 3
        for r in range(200, 600, 80):
            pulse = 0.7 + 0.3 * math.sin(t * 0.5 + r * 0.01)
            ra    = int(a * pulse)
            if ra > 0:
                draw.arc([cx - r, cy - r, cx + r, cy + r],
                         start=0, end=360, fill=(*accent, ra), width=1)

    elif style == "tech":
        # Grid lines suggestion
        for x in range(0, W, 120):
            draw.rectangle([x, 0, x + 1, H], fill=(*accent, a // 2))
        for y in range(0, H, 120):
            draw.rectangle([0, y, W, y + 1], fill=(*accent, a // 2))

    elif style == "parchment":
        # Diagonal decorative lines
        for i in range(-5, 15):
            offset = i * 200
            draw.line([(offset, 0), (offset + H, H)],
                      fill=(*accent, a // 3), width=1)

    elif style == "nature":
        # Organic curves suggestion
        for i in range(3):
            x_off = int(100 * math.sin(t * 0.3 + i * 2))
            draw.arc([x_off - 300 + i * 200, H // 2 - 400,
                      x_off + 300 + i * 200, H // 2 + 400],
                     start=0, end=180, fill=(*accent, a), width=2)


# ── Main frame renderer ────────────────────────────────────────────────────────

def _make_frame(bg: Image.Image, hook: str, body: str,
                topic_key: str, topic: dict, lang: str,
                follow_text: str, tags: list,
                t: float, total: float) -> np.ndarray:

    progress = t / total
    theme    = THEMES.get(topic_key, THEMES["space"])

    # ── 1. Ken Burns zoom on background ───────────────────────────────────
    scale  = 1.0 + 0.06 * progress
    nw, nh = int(W * scale), int(H * scale)
    zoomed = bg.resize((nw, nh), Image.LANCZOS)
    left   = (nw - W) // 2
    top    = (nh - H) // 2
    frame  = zoomed.crop((left, top, left + W, top + H)).convert("RGBA")

    # ── 2. Enhance background (slight color boost) ─────────────────────
    frame_rgb = frame.convert("RGB")
    enhancer  = ImageEnhance.Color(frame_rgb)
    frame_rgb = enhancer.enhance(1.3)   # boost saturation
    enhancer2 = ImageEnhance.Contrast(frame_rgb)
    frame_rgb = enhancer2.enhance(1.1)
    frame     = frame_rgb.convert("RGBA")

    # ── 3. Animated gradient color wash ───────────────────────────────────
    frame = _draw_gradient_overlay(
        frame, theme["gradient_colors"],
        theme["overlay_alpha"], t
    )

    # ── 4. Draw on frame ───────────────────────────────────────────────────
    draw   = ImageDraw.Draw(frame)
    accent  = theme["accent"]
    accent2 = theme["accent2"]
    txt_c   = theme["text"]
    glow_c  = theme["glow"]

    # ── 5. Particles (space + science) ────────────────────────────────────
    if theme.get("particles"):
        _draw_particles(draw, t, theme.get("particle_color", (255, 255, 255)),
                        count=50, seed=hash(hook) % 1000)

    # ── 6. Abstract decorative shapes ────────────────────────────────────
    _draw_abstract_shapes(draw, theme, t, progress)

    # ── 7. Decorative geometric lines ─────────────────────────────────────
    _draw_decorative_lines(draw, theme, progress)

    # ── 8. Top section — brand + topic ────────────────────────────────────
    top_a = min(255, int(progress * 255 * 6))

    # Brand pill (top right)
    brand_font = _get_font(24, bold=True, lang="en")
    brand_text = "cosmos.capsule"
    brand_bbox = brand_font.getbbox(brand_text)
    bw         = brand_bbox[2] + 24
    bh         = 36
    bx         = W - bw - 40
    by         = 48
    _draw_glass_card(draw, bx - 4, by - 4, bx + bw, by + bh,
                     color=accent, alpha=30, radius=18)
    draw.text((bx + 8, by + 6), brand_text, font=brand_font,
              fill=(*accent, min(220, top_a)))

    # Language badge (top left)
    badge_font = _get_font(28, bold=True, lang="en")
    lang_label = "हिंदी" if lang == "hi" else "EN"
    _draw_glass_card(draw, PAD - 12, 46, PAD + 72, 86,
                     color=accent, alpha=35, radius=14)
    draw.text((PAD, 55), lang_label, font=badge_font,
              fill=(*accent, min(220, top_a)))

    # Topic label with glass card
    label_font = _get_font(38, bold=True, lang=lang)
    topic_name = topic.get("name_hi", topic["name"]) if lang == "hi" else topic["name"]
    label      = f"{topic['emoji']}  {topic_name}"
    label_bbox = label_font.getbbox(label)
    lw         = min(label_bbox[2] + 32, W - PAD * 2)
    _draw_glass_card(draw, PAD - 16, 98, PAD + lw, 150,
                     color=accent, alpha=20, radius=12)
    draw.text((PAD, 108), label, font=label_font,
              fill=(*accent, min(255, top_a)))

    # ── 9. Hook text with glass card backdrop ─────────────────────────────
    hook_font  = _get_font(74, bold=True, lang=lang)
    hook_text  = hook.upper() if lang == "en" else hook
    hook_lines = _wrap(hook_text, hook_font, W - PAD * 2)
    hook_alpha = min(255, int(progress * 255 / 0.35))
    hook_h     = len(hook_lines) * 92
    hook_y_start = H // 2 - hook_h // 2 - 80

    # Glass card behind hook
    card_pad = 24
    _draw_glass_card(draw,
                     PAD - card_pad,
                     hook_y_start - card_pad,
                     W - PAD + card_pad,
                     hook_y_start + hook_h + card_pad,
                     color=(0, 0, 0), alpha=60, radius=24)

    # Accent border on left of hook card
    draw.rounded_rectangle(
        [PAD - card_pad, hook_y_start - card_pad,
         PAD - card_pad + 4, hook_y_start + hook_h + card_pad],
        radius=2, fill=(*accent, min(200, hook_alpha))
    )

    hook_y = hook_y_start
    for line in hook_lines:
        bbox = hook_font.getbbox(line)
        x    = (W - bbox[2]) // 2
        _draw_glow_text(draw, x, hook_y, line, hook_font,
                        txt_c, hook_alpha, glow_c, glow_r=6)
        hook_y += 92

    # ── 10. Body text with glass card ─────────────────────────────────────
    body_start = 0.42
    body_alpha = 0
    if progress > body_start:
        body_alpha = min(255, int((progress - body_start) * 255 / 0.28))

    if body_alpha > 0:
        body_font  = _get_font(40, lang=lang)
        body_lines = _wrap(body, body_font, W - PAD * 2)
        body_h     = len(body_lines) * 58
        body_y_start = H // 2 + 130

        # Glass card behind body
        _draw_glass_card(draw,
                         PAD - 20,
                         body_y_start - 16,
                         W - PAD + 20,
                         body_y_start + body_h + 16,
                         color=(0, 0, 0), alpha=55, radius=20)

        body_y = body_y_start
        for line in body_lines:
            bbox = body_font.getbbox(line)
            x    = (W - bbox[2]) // 2
            draw.text((x + 2, body_y + 2), line, font=body_font,
                      fill=(0, 0, 0, body_alpha // 3))
            draw.text((x, body_y), line, font=body_font,
                      fill=(*txt_c, body_alpha))
            body_y += 58

    # ── 11. Hashtag strip with glass card ────────────────────────────────
    tag_start = 0.62
    tag_alpha = 0
    if progress > tag_start:
        tag_alpha = min(190, int((progress - tag_start) * 190 / 0.22))

    if tag_alpha > 0 and tags:
        tag_font  = _get_font(25, bold=False, lang=lang)
        tag_y     = H - 230

        # Glass card for tags
        _draw_glass_card(draw, PAD - 20, tag_y - 10,
                         W - PAD + 20, tag_y + 70,
                         color=accent, alpha=20, radius=16)

        # Render 2 rows of 3 tags
        row1 = "  ".join(tags[:3])
        row2 = "  ".join(tags[3:6]) if len(tags) > 3 else ""

        for i, trow in enumerate([row1, row2]):
            if not trow:
                continue
            bbox = tag_font.getbbox(trow)
            tx   = (W - bbox[2]) // 2
            ty   = tag_y + i * 32
            draw.text((tx + 1, ty + 1), trow, font=tag_font,
                      fill=(0, 0, 0, tag_alpha // 2))
            draw.text((tx, ty), trow, font=tag_font,
                      fill=(*accent, tag_alpha))

    # ── 12. Bottom bar with follow CTA ────────────────────────────────────
    bar_a = min(220, int(progress * 220 * 3))

    # Gradient bottom bar
    for i in range(80):
        bar_row_a = int(bar_a * (i / 80) * 0.8)
        draw.rectangle([0, H - 145 + i, W, H - 144 + i],
                       fill=(0, 0, 0, bar_row_a))

    # Follow text with glow
    wm_font = _get_font(30, bold=True, lang=lang)
    wm_text = follow_text
    bbox    = wm_font.getbbox(wm_text)
    wx      = (W - bbox[2]) // 2
    _draw_glow_text(draw, wx, H - 95, wm_text, wm_font,
                    accent, min(220, bar_a), glow_c, glow_r=4)

    # Accent dot row above follow text
    dot_a = min(150, bar_a)
    for i, dx in enumerate(range(W // 2 - 40, W // 2 + 40, 16)):
        pulse = 0.5 + 0.5 * math.sin(t * 2 + i * 0.8)
        da    = int(dot_a * pulse)
        draw.ellipse([dx - 3, H - 115 - 3, dx + 3, H - 115 + 3],
                     fill=(*accent2, da))

    return np.array(frame.convert("RGB"))


# ── VideoCreator ───────────────────────────────────────────────────────────────

class VideoCreator:
    def create_reel(self, image_path: Path, music_path: Path, fact_data: dict,
                    topic: dict, lang: str, output_dir: Path) -> Path:

        log.info(f"🎬 Rendering premium [{lang.upper()}] reel…")

        # Find topic key
        import config as cfg
        topic_key = "space"
        for k, v in cfg.TOPICS.items():
            if v.get("name") == topic.get("name") or v.get("name_hi") == topic.get("name_hi"):
                topic_key = k
                break

        bg_img      = Image.open(image_path).convert("RGB")
        hook        = fact_data["hook"]
        body        = fact_data["body"]
        follow_text = LANGUAGES[lang]["follow_text"]
        tags        = VIDEO_TAGS.get(f"{topic_key}_{lang}", ["#cosmoscapsule"])

        def make_frame(t):
            return _make_frame(bg_img, hook, body,
                               topic_key, topic, lang,
                               follow_text, tags, t, REEL_DURATION)

        clip = VideoClip(make_frame, duration=REEL_DURATION).set_fps(REEL_FPS)
        clip = fadein(clip, 0.6)
        clip = fadeout(clip, 0.8)

        audio = (AudioFileClip(str(music_path))
                 .subclip(0, REEL_DURATION)
                 .audio_fadeout(2.5)
                 .volumex(MUSIC_VOLUME))
        clip = clip.set_audio(audio)

        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        cat_slug = fact_data.get("fact_category", topic["name"])[:20].replace(" ", "_").lower()
        out_path = output_dir / f"reel_{cat_slug}_{lang}_{ts}.mp4"

        log.info(f"💾 Writing → {out_path.name}")
        clip.write_videofile(
            str(out_path),
            codec="libx264", audio_codec="aac",
            fps=REEL_FPS, preset="fast",
            bitrate="4000k", audio_bitrate="192k",
            ffmpeg_params=["-vf", f"scale={W}:{H}"],
            logger=None,
        )
        log.info(f"✅ [{lang.upper()}] {out_path.stat().st_size / 1e6:.1f} MB")
        return out_path
