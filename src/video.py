"""
src/video.py — Renders 1080×1920 Instagram Reels with:
  - Ken Burns zoom effect on background image
  - Animated text (hook fades in, body fades in after)
  - Branded bottom bar
  - Background music mixed in
"""

import logging
import textwrap
from pathlib import Path
from datetime import datetime

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy.editor import VideoClip, AudioFileClip, CompositeVideoClip
from moviepy.video.fx.all import fadein, fadeout

from config import REEL_WIDTH, REEL_HEIGHT, REEL_DURATION, REEL_FPS, MUSIC_VOLUME

log = logging.getLogger(__name__)

W, H = REEL_WIDTH, REEL_HEIGHT
PAD  = 72   # horizontal padding


# ── Font loading ───────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    fonts_dir = Path(__file__).parent.parent / "fonts"
    if bold:
        candidates = [
            fonts_dir / "Poppins-Bold.ttf",
            fonts_dir / "Poppins-SemiBold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        candidates = [
            fonts_dir / "Poppins-Regular.ttf",
            fonts_dir / "Poppins-Medium.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(str(p), size)
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


def _draw_text_shadow(draw, x, y, text, font, color, alpha, shadow_offset=3):
    r, g, b = color
    a = alpha
    draw.text((x + shadow_offset, y + shadow_offset), text,
              font=font, fill=(0, 0, 0, a // 3))
    draw.text((x, y), text, font=font, fill=(r, g, b, a))


# ── Frame renderer ─────────────────────────────────────────────────────────────

def _make_frame_array(
    bg: Image.Image,
    hook: str,
    body: str,
    topic: dict,
    t: float,        # current time in seconds
    total: float,    # total duration
) -> np.ndarray:
    progress = t / total   # 0.0 → 1.0

    # Ken Burns: zoom from 1.00 to 1.08 over the clip
    scale   = 1.0 + 0.08 * progress
    new_w   = int(W * scale)
    new_h   = int(H * scale)
    zoomed  = bg.resize((new_w, new_h), Image.LANCZOS)
    left    = (new_w - W) // 2
    top     = (new_h - H) // 2
    frame   = zoomed.crop((left, top, left + W, top + H))

    # Dark overlay (slightly heavier at center for readability)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle([0, 0, W, H], fill=(0, 0, 0, 150))
    frame   = frame.convert("RGBA")
    frame   = Image.alpha_composite(frame, overlay)

    draw   = ImageDraw.Draw(frame)
    accent = topic["color_scheme"]["accent"]
    txt_c  = topic["color_scheme"]["text"]

    # ── Topic label (top) ──────────────────────────────────────────────────
    label_font = _font(38, bold=True)
    label      = f"{topic['emoji']}  {topic['name'].upper()}"
    label_a    = min(255, int(progress * 255 * 5))
    draw.text((PAD, 88), label, font=label_font, fill=(*accent, label_a))
    # Thin accent line
    line_a = min(200, int(progress * 255 * 4))
    draw.rectangle([PAD, 148, W - PAD, 152], fill=(*accent, line_a))

    # ── Hook text (animates in first 30% of clip) ──────────────────────────
    hook_font  = _font(82, bold=True)
    hook_lines = _wrap(hook.upper(), hook_font, W - PAD * 2)
    hook_alpha = min(255, int(progress * 255 / 0.35))

    total_hook_h = len(hook_lines) * 100
    hook_y       = H // 2 - total_hook_h // 2 - 60

    for line in hook_lines:
        bbox = hook_font.getbbox(line)
        x    = (W - bbox[2]) // 2
        _draw_text_shadow(draw, x, hook_y, line, hook_font, txt_c, hook_alpha)
        hook_y += 100

    # ── Body text (fades in after 40% of clip) ─────────────────────────────
    body_start = 0.40
    body_alpha = 0
    if progress > body_start:
        body_alpha = min(255, int((progress - body_start) * 255 / 0.30))

    if body_alpha > 0:
        body_font  = _font(44)
        body_lines = _wrap(body, body_font, W - PAD * 2)
        body_y     = H // 2 + 120

        for line in body_lines:
            bbox = body_font.getbbox(line)
            x    = (W - bbox[2]) // 2
            _draw_text_shadow(draw, x, body_y, line, body_font, txt_c, body_alpha)
            body_y += 60

    # ── Bottom brand bar ───────────────────────────────────────────────────
    bar_alpha = min(200, int(progress * 255 * 3))
    draw.rectangle([0, H - 130, W, H], fill=(0, 0, 0, bar_alpha // 2))
    wm_font = _font(30)
    wm_text = f"Follow for daily {topic['name']} facts  ✨"
    bbox    = wm_font.getbbox(wm_text)
    wx      = (W - bbox[2]) // 2
    draw.text((wx, H - 90), wm_text, font=wm_font,
              fill=(*accent, min(220, bar_alpha)))

    return np.array(frame.convert("RGB"))


# ── VideoCreator ───────────────────────────────────────────────────────────────

class VideoCreator:
    def create_reel(
        self,
        image_path: Path,
        music_path: Path,
        fact_data: dict,
        topic: dict,
        output_dir: Path,
    ) -> Path:
        log.info("🎬 Loading background image…")
        bg_img = Image.open(image_path).convert("RGB")

        hook = fact_data["hook"]
        body = fact_data["body"]

        log.info("🎞  Rendering frames (MoviePy)…")

        def make_frame(t):
            return _make_frame_array(bg_img, hook, body, topic, t, REEL_DURATION)

        clip = VideoClip(make_frame, duration=REEL_DURATION)
        clip = clip.set_fps(REEL_FPS)
        clip = fadein(clip, 0.5)
        clip = fadeout(clip, 0.8)

        # Audio
        log.info("🎵 Mixing audio…")
        audio = (
            AudioFileClip(str(music_path))
            .subclip(0, REEL_DURATION)
            .audio_fadeout(2.5)
            .volumex(MUSIC_VOLUME)
        )
        clip  = clip.set_audio(audio)

        # Output path
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        cat_slug = fact_data.get("fact_category", topic["name"]).replace(" ", "_").lower()
        out_path = output_dir / f"reel_{cat_slug}_{ts}.mp4"

        log.info(f"💾 Writing video → {out_path}")
        clip.write_videofile(
            str(out_path),
            codec="libx264",
            audio_codec="aac",
            fps=REEL_FPS,
            preset="fast",
            bitrate="4000k",
            audio_bitrate="192k",
            ffmpeg_params=["-vf", f"scale={W}:{H}"],
            logger=None,
        )

        log.info(f"✅ Video complete: {out_path.stat().st_size / 1e6:.1f} MB")
        return out_path
