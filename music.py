"""
src/music.py — Fetches royalty-free background music.
Priority: cached local file → Freesound API → silence placeholder
"""

import os
import random
import logging
import wave
from pathlib import Path

import requests

log = logging.getLogger(__name__)

ROOT            = Path(__file__).parent.parent
MUSIC_CACHE_DIR = ROOT / "output" / "music"
LOCAL_MUSIC_DIR = ROOT / "music"
FREESOUND_KEY   = os.environ.get("FREESOUND_API_KEY", "")

MOOD_QUERIES = {
    "ambient cinematic space": [
        "space ambient cinematic loop",
        "cosmic drone ambient",
        "deep space sci-fi music",
        "space exploration ambient",
    ],
    "epic orchestral historical": [
        "epic orchestral cinematic loop",
        "historical dramatic music",
        "ancient civilization orchestral",
        "medieval epic music loop",
    ],
    "nature acoustic world": [
        "nature acoustic guitar peaceful",
        "world music calm loop",
        "acoustic meditation music",
        "peaceful nature background music",
    ],
    "electronic upbeat discovery": [
        "electronic discovery upbeat loop",
        "science technology background music",
        "futuristic electronic loop",
        "uplifting electronic background",
    ],
}


class MusicManager:
    def get_track(self, mood: str, topic_key: str) -> Path:
        MUSIC_CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # 1. Cached file
        cached = self._cached(mood)
        if cached:
            log.info(f"Using cached music: {cached.name}")
            return cached

        # 2. Freesound API
        if FREESOUND_KEY:
            track = self._freesound(mood)
            if track:
                return track

        # 3. Local files
        local = self._local(topic_key)
        if local:
            log.info(f"Using local music: {local.name}")
            return local

        # 4. Silence
        log.warning("No music found — using silence")
        return self._silence()

    # ── Sources ────────────────────────────────────────────────────────────────

    def _cached(self, mood: str) -> Path | None:
        folder = MUSIC_CACHE_DIR / mood.replace(" ", "_")
        if folder.exists():
            files = list(folder.glob("*.mp3")) + list(folder.glob("*.wav"))
            if files:
                return random.choice(files)
        return None

    def _freesound(self, mood: str) -> Path | None:
        query = random.choice(MOOD_QUERIES.get(mood, [mood]))
        try:
            log.info(f"Searching Freesound: '{query}'")
            r = requests.get(
                "https://freesound.org/apiv2/search/text/",
                params={
                    "query": query,
                    "filter": "duration:[15 TO 120] type:mp3",
                    "fields": "id,name,previews,duration,license",
                    "page_size": 15,
                    "token": FREESOUND_KEY,
                },
                timeout=15,
            )
            r.raise_for_status()
            results = r.json().get("results", [])
            if not results:
                return None

            sound   = random.choice(results[:10])
            url     = (sound["previews"].get("preview-hq-mp3")
                       or sound["previews"].get("preview-lq-mp3"))

            folder  = MUSIC_CACHE_DIR / mood.replace(" ", "_")
            folder.mkdir(exist_ok=True)
            name    = sound["name"][:40].replace(" ", "_").replace("/", "-")
            out     = folder / f"{sound['id']}_{name}.mp3"

            if not out.exists():
                audio = requests.get(url, timeout=30).content
                out.write_bytes(audio)
                log.info(f"Downloaded: {out.name}")

            return out
        except Exception as e:
            log.warning(f"Freesound error: {e}")
            return None

    def _local(self, topic_key: str) -> Path | None:
        for folder in [LOCAL_MUSIC_DIR / topic_key, LOCAL_MUSIC_DIR]:
            if folder.exists():
                files = list(folder.glob("*.mp3")) + list(folder.glob("*.wav"))
                if files:
                    return random.choice(files)
        return None

    def _silence(self) -> Path:
        path = MUSIC_CACHE_DIR / "silence.wav"
        if not path.exists():
            sr = 44100
            with wave.open(str(path), "w") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(sr)
                f.writeframes(b"\x00\x00" * sr * 25)
        return path
