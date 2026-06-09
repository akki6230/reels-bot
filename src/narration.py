"""
src/narration.py — Hindi TTS with timing metadata.
Returns both the audio path AND the actual duration
so video renderer can sync word reveal to speech.
"""

import asyncio
import logging
import random
from pathlib import Path

log = logging.getLogger(__name__)

HINDI_VOICES = [
    "hi-IN-SwaraNeural",
    "hi-IN-MadhurNeural",
]

# All rates made faster so speech fits in 10-20s reel
VOICE_STYLES = {
    "psychology":   {"rate": "+5%",  "pitch": "-2Hz",  "volume": "+10%"},
    "mindblowing":  {"rate": "+10%", "pitch": "+3Hz",  "volume": "+15%"},
    "space":        {"rate": "+5%",  "pitch": "-4Hz",  "volume": "+8%"},
    "sciencewrong": {"rate": "+12%", "pitch": "+2Hz",  "volume": "+12%"},
    "earthglitch":  {"rate": "+8%",  "pitch": "0Hz",   "volume": "+10%"},
}


async def _tts(text: str, voice: str, style: dict, out: Path) -> bool:
    try:
        import edge_tts
        comm = edge_tts.Communicate(
            text=text, voice=voice,
            rate=style.get("rate", "0%"),
            pitch=style.get("pitch", "0Hz"),
            volume=style.get("volume", "+0%"),
        )
        await comm.save(str(out))
        return True
    except Exception as e:
        log.warning(f"TTS failed: {e}")
        return False


def get_audio_duration(path: Path) -> float:
    """Get duration of audio file in seconds."""
    try:
        from moviepy.editor import AudioFileClip
        clip = AudioFileClip(str(path))
        dur  = clip.duration
        clip.close()
        return dur
    except Exception:
        try:
            # Fallback: estimate from file size (mp3 ~128kbps)
            size_kb = path.stat().st_size / 1024
            return size_kb / 16   # rough estimate
        except Exception:
            return 15.0


def generate_narration(hook: str, body: str, lang: str,
                        topic_key: str, output_dir: Path,
                        reel_duration: int = 20) -> tuple[Path | None, float]:
    """
    Generate TTS narration.
    Returns (audio_path, narration_duration_seconds).
    narration_duration is used to sync word reveal in video.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    voice  = random.choice(HINDI_VOICES)
    style  = VOICE_STYLES.get(topic_key,
             {"rate": "+8%", "pitch": "0Hz", "volume": "+10%"})

    # Keep script concise — hook only + short body (max ~15 words)
    # This ensures narration fits well within the reel duration
    body_words = body.split()
    # Use full body if reel is long enough, else trim
    max_body_words = min(len(body_words), max(8, reel_duration * 2))
    short_body = " ".join(body_words[:max_body_words])

    script = f"{hook}. {short_body}"
    out    = output_dir / f"narration_{topic_key}_{random.randint(100,999)}.mp3"

    log.info(f"🎙 TTS [{voice}]: {script[:70]}...")
    try:
        ok = asyncio.run(_tts(script, voice, style, out))
        if ok and out.exists() and out.stat().st_size > 500:
            duration = get_audio_duration(out)
            log.info(f"✅ Narration: {out.name} | duration: {duration:.1f}s")
            return out, duration
    except Exception as e:
        log.warning(f"Narration error: {e}")
    return None, 0.0
