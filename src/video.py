"""
src/video.py — Renders 1080×1920 Reels with full Hindi (Devanagari) support.
Downloads Noto Sans Devanagari font on first run for proper Hindi rendering.
"""

import math
import logging
import struct
import wave
from pathlib import Path
from datetime import datetime

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoClip, AudioFileClip
from moviepy.video.fx.all import fadein, fadeout

from config import REEL_WIDTH, REEL_HEIGHT, REEL_DURATION, REEL_FPS, MUSIC_VOLUME, LANGUAGES

log = logging.getLogger(__name__)

W, H    = REEL_WIDTH, REEL_HEIGHT
PAD     = 72
ROOT    = Path(__file__).parent.parent
FONTS_DIR = ROOT / "fonts"
FONTS_DIR.mkdir(exist_ok=True)

# ── Font management ────────────────────────────────────────────────────────────

FONT_CACHE: dict[str, ImageFont.FreeTypeFont] = {}

def _download_font(url: str, dest: Path):
    if dest.exists():
        return
    log.info(f"Downloading font: {dest.name}")
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
        # Download Noto Sans Devanagari if needed
        lang_cfg = LANGUAGES["hi"]
        bold_path = FONTS_DIR / "NotoSansDevanagari-Bold.ttf"
        reg_path  = FONTS_DIR / "NotoSansDevanagari-Regular.ttf"
        _download_font(lang_cfg["font_url"],     bold_path)
        _download_font(lang_cfg["font_url_reg"], reg_path)
        candidates = [bold_path if bold else reg_path]

    # English / fallback fonts
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

# ── Text helpers ───────────────────────────────────────────────────────────────

def _wrap(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
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

def _draw_shadowed(draw, x, y, text, font, color, alpha, shadow=3):
    draw.text((x + shadow, y + shadow), text, font=font, fill=(0, 0, 0, alpha // 3))
    draw.text((x, y), text, font=font, fill=(*color, alpha))

# ── Frame renderer ─────────────────────────────────────────────────────────────

def _make_frame(bg: Image.Image, hook: str, body: str, topic: dict,
                lang: str, follow_text: str, t: float, total: float) -> np.ndarray:
    progress = t / total

    # Ken Burns zoom
    scale  = 1.0 + 0.08 * progress
    nw, nh = int(W * scale), int(H * scale)
    zoomed = bg.resize((nw, nh), Image.LANCZOS)
    left   = (nw - W) // 2
    top    = (nh - H) // 2
    frame  = zoomed.crop((left, top, left + W, top + H)).convert("RGBA")

    # Dark overlay
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 155))
    frame = Image.alpha_composite(frame, ov)
    draw  = ImageDraw.Draw(frame)

    accent = topic["color_scheme"]["accent"]
    txt_c  = topic["color_scheme"]["text"]

    # ── Language badge (top-left) ──────────────────────────────────────────
    badge_font = _get_font(30, bold=True, lang="en")
    lang_label = "हिंदी" if lang == "hi" else "ENG"
    badge_a    = min(220, int(progress * 220 * 4))
    draw.rounded_rectangle([PAD - 10, 48, PAD + 80, 84],
                            radius=8, fill=(*accent, badge_a // 2))
    draw.text((PAD, 55), lang_label, font=badge_font,
              fill=(*accent, badge_a))

    # ── Topic label ────────────────────────────────────────────────────────
    label_font = _get_font(36, bold=True, lang=lang)
    topic_name = topic.get("name_hi", topic["name"]) if lang == "hi" else topic["name"]
    label      = f"{topic['emoji']}  {topic_name}"
    label_a    = min(255, int(progress * 255 * 5))
    draw.text((PAD, 100), label, font=label_font, fill=(*accent, label_a))
    draw.rectangle([PAD, 155, W - PAD, 159], fill=(*accent, label_a // 2))

    # ── Hook ───────────────────────────────────────────────────────────────
    hook_font  = _get_font(72, bold=True, lang=lang)
    hook_lines = _wrap(hook.upper() if lang == "en" else hook, hook_font, W - PAD * 2)
    hook_alpha = min(255, int(progress * 255 / 0.35))
    hook_h     = len(hook_lines) * 88
    hook_y     = H // 2 - hook_h // 2 - 70

    for line in hook_lines:
        bbox = hook_font.getbbox(line)
        x    = (W - bbox[2]) // 2
        _draw_shadowed(draw, x, hook_y, line, hook_font, txt_c, hook_alpha)
        hook_y += 88

    # ── Body ───────────────────────────────────────────────────────────────
    body_start = 0.40
    body_alpha = 0
    if progress > body_start:
        body_alpha = min(255, int((progress - body_start) * 255 / 0.30))

    if body_alpha > 0:
        body_font  = _get_font(40, lang=lang)
        body_lines = _wrap(body, body_font, W - PAD * 2)
        body_y     = H // 2 + 110
        for line in body_lines:
            bbox = body_font.getbbox(line)
            x    = (W - bbox[2]) // 2
            _draw_shadowed(draw, x, body_y, line, body_font, txt_c, body_alpha)
            body_y += 56

    # ── Bottom bar ─────────────────────────────────────────────────────────
    bar_a = min(200, int(progress * 200 * 3))
    draw.rectangle([0, H - 140, W, H], fill=(0, 0, 0, bar_a // 2))
    wm_font = _get_font(28, lang=lang)
    bbox    = wm_font.getbbox(follow_text)
    wx      = (W - bbox[2]) // 2
    draw.text((wx, H - 100), follow_text, font=wm_font,
              fill=(*accent, min(220, bar_a)))

    return np.array(frame.convert("RGB"))


# ── VideoCreator ───────────────────────────────────────────────────────────────

class VideoCreator:
    def create_reel(self, image_path: Path, music_path: Path, fact_data: dict,
                    topic: dict, lang: str, output_dir: Path) -> Path:

        log.info(f"🎬 Rendering [{lang.upper()}] reel…")
        bg_img      = Image.open(image_path).convert("RGB")
        hook        = fact_data["hook"]
        body        = fact_data["body"]
        follow_text = LANGUAGES[lang]["follow_text"]

        def make_frame(t):
            return _make_frame(bg_img, hook, body, topic, lang, follow_text, t, REEL_DURATION)

        clip = VideoClip(make_frame, duration=REEL_DURATION).set_fps(REEL_FPS)
        clip = fadein(clip, 0.5)
        clip = fadeout(clip, 0.8)

        audio = (AudioFileClip(str(music_path))
                 .subclip(0, REEL_DURATION)
                 .audio_fadeout(2.5)
                 .volumex(MUSIC_VOLUME))
        clip  = clip.set_audio(audio)

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
