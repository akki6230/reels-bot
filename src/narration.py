"""
src/narration.py — Hindi TTS with random voice selection.
30% of reels get voiceover (controlled by main.py).
"""

import asyncio
import logging
import random
from pathlib import Path

log = logging.getLogger(__name__)

# All available Hindi voices — randomly selected per reel
HINDI_VOICES = [
    "hi-IN-SwaraNeural",    # Female — warm, clear
    "hi-IN-MadhurNeural",   # Male — authoritative, deep
]

VOICE_STYLES = {
    "psychology":   {"rate": "-8%",  "pitch": "-2Hz",  "volume": "+10%"},
    "mindblowing":  {"rate": "-3%",  "pitch": "+3Hz",  "volume": "+15%"},
    "space":        {"rate": "-10%", "pitch": "-4Hz",  "volume": "+8%"},
    "sciencewrong": {"rate": "+2%",  "pitch": "+2Hz",  "volume": "+12%"},
    "earthglitch":  {"rate": "-5%",  "pitch": "0Hz",   "volume": "+10%"},
}


async def _tts(text: str, voice: str, style: dict, out: Path) -> bool:
    try:
        import edge_tts
        comm = edge_tts.Communicate(
            text=text, voice=voice,
            rate=style.get("rate","0%"),
            pitch=style.get("pitch","0Hz"),
            volume=style.get("volume","+0%"),
        )
        await comm.save(str(out))
        return True
    except Exception as e:
        log.warning(f"TTS failed: {e}")
        return False


def generate_narration(hook: str, body: str, lang: str,
                        topic_key: str, output_dir: Path) -> Path | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    voice  = random.choice(HINDI_VOICES)
    style  = VOICE_STYLES.get(topic_key, {"rate": "-5%", "pitch": "0Hz", "volume": "+10%"})
    # Natural pause between hook and body
    script = f"{hook}... {body}"
    out    = output_dir / f"narration_{topic_key}_{random.randint(100,999)}.mp3"

    log.info(f"🎙 TTS voice: {voice} | text: {script[:60]}...")
    try:
        ok = asyncio.run(_tts(script, voice, style, out))
        if ok and out.exists() and out.stat().st_size > 500:
            log.info(f"✅ Narration: {out.name} ({out.stat().st_size//1024}KB)")
            return out
    except Exception as e:
        log.warning(f"Narration error: {e}")
    return None
