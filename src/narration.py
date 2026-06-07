"""
src/narration.py — Text-to-speech narration using Microsoft Edge TTS.
Completely free, no API key needed, excellent Hindi + English voices.

Voices used:
  English: en-IN-NeerjaNeural (Indian female) or en-US-GuyNeural (US male)
  Hindi:   hi-IN-SwaraNeural (female) or hi-IN-MadhurNeural (male)

The narration speaks:
  1. The hook line (with dramatic pause after)
  2. The body text

Output: .mp3 file ready to mix with background music
"""

import asyncio
import logging
import random
from pathlib import Path

log = logging.getLogger(__name__)

# ── Voice profiles ─────────────────────────────────────────────────────────────

VOICES = {
    "en": [
        "en-IN-NeerjaNeural",      # Indian English female — warm, clear
        "en-IN-PrabhatNeural",     # Indian English male — authoritative
        "en-US-AriaNeural",        # US female — very natural
        "en-US-GuyNeural",         # US male — documentary feel
        "en-GB-SoniaNeural",       # British female — premium feel
    ],
    "hi": [
        "hi-IN-SwaraNeural",       # Hindi female — clear, natural
        "hi-IN-MadhurNeural",      # Hindi male — authoritative
    ],
}

# SSML rate and pitch per topic for variety
VOICE_STYLES = {
    "space":     {"rate": "-5%",  "pitch": "-2Hz",  "volume": "+10%"},
    "history":   {"rate": "-8%",  "pitch": "-4Hz",  "volume": "+8%"},
    "geography": {"rate": "-3%",  "pitch": "0Hz",   "volume": "+10%"},
    "science":   {"rate": "-2%",  "pitch": "+2Hz",  "volume": "+10%"},
    "sports":    {"rate": "+5%",  "pitch": "+4Hz",  "volume": "+15%"},
    "worldnews": {"rate": "-5%",  "pitch": "-2Hz",  "volume": "+12%"},
}


async def _generate_tts(text: str, voice: str, style: dict,
                         out_path: Path) -> bool:
    """Generate TTS audio using edge-tts library."""
    try:
        import edge_tts

        rate   = style.get("rate",   "0%")
        pitch  = style.get("pitch",  "0Hz")
        volume = style.get("volume", "+0%")

        communicate = edge_tts.Communicate(
            text  = text,
            voice = voice,
            rate  = rate,
            pitch = pitch,
            volume= volume,
        )
        await communicate.save(str(out_path))
        return True
    except Exception as e:
        log.warning(f"TTS generation failed: {e}")
        return False


def _build_narration_text(hook: str, body: str, lang: str) -> str:
    """Build the full narration script with pauses."""
    if lang == "hi":
        # Hindi narration: hook + pause + body
        return f"{hook}... {body}"
    else:
        # English: dramatic pause after hook
        return f"{hook}... {body}"


def generate_narration(hook: str, body: str, lang: str,
                        topic_key: str, output_dir: Path) -> Path | None:
    """
    Generate TTS narration for the reel.
    Returns path to .mp3 file, or None if generation fails.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Pick a random voice for variety
    voice_list = VOICES.get(lang, VOICES["en"])
    voice      = random.choice(voice_list)
    style      = VOICE_STYLES.get(topic_key, VOICE_STYLES["space"])

    # Build narration script
    narration_text = _build_narration_text(hook, body, lang)

    out_path = output_dir / f"narration_{topic_key}_{lang}.mp3"

    log.info(f"🎙 Generating {lang.upper()} narration with voice: {voice}")
    log.info(f"   Text: {narration_text[:80]}...")

    # Run async TTS
    try:
        success = asyncio.run(_generate_tts(narration_text, voice, style, out_path))
        if success and out_path.exists() and out_path.stat().st_size > 1000:
            log.info(f"✅ Narration saved: {out_path.name} ({out_path.stat().st_size // 1024} KB)")
            return out_path
        else:
            log.warning("TTS output empty or too small")
            return None
    except Exception as e:
        log.warning(f"Narration generation failed: {e}")
        return None
