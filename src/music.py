"""
src/music.py — Music selection with energy matching.
calm topics → soft ambient
high energy topics → motivational epic
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

# Calm soft music queries (psychology, space)
CALM_QUERIES = [
    "soft ambient piano meditation",
    "calm background music peaceful",
    "gentle ambient music relaxing",
    "soft instrumental background calm",
    "peaceful meditation music loop",
]

# High energy motivational (mindblowing, sciencewrong, earthglitch)
HYPE_QUERIES = [
    "motivational epic cinematic music",
    "epic upbeat background music",
    "powerful motivational instrumental",
    "dramatic epic music upbeat",
    "energetic motivational background",
]

MOOD_QUERIES = {
    "soft calm ambient":        CALM_QUERIES,
    "motivational epic upbeat": HYPE_QUERIES,
}


class MusicManager:
    def get_track(self, mood: str, topic_key: str) -> Path:
        MUSIC_CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Check local music folder first (topic-specific)
        local = self._local(topic_key, mood)
        if local:
            log.info(f"Local music: {local.name}")
            return local

        # Check cache
        cached = self._cached(mood)
        if cached:
            log.info(f"Cached music: {cached.name}")
            return cached

        # Freesound API
        if FREESOUND_KEY:
            track = self._freesound(mood)
            if track:
                return track

        # Generate ambient tone
        log.info(f"Generating ambient tone for mood: {mood}")
        return self._generate_tone(mood)

    def _local(self, topic_key: str, mood: str) -> Path | None:
        energy = "calm" if "calm" in mood else "hype"
        for folder in [
            LOCAL_MUSIC_DIR / topic_key,
            LOCAL_MUSIC_DIR / energy,
            LOCAL_MUSIC_DIR,
        ]:
            if folder.exists():
                files = [f for f in folder.glob("*") if f.suffix in (".mp3",".wav")]
                if files:
                    return random.choice(files)
        return None

    def _cached(self, mood: str) -> Path | None:
        folder = MUSIC_CACHE_DIR / mood.replace(" ","_")
        if folder.exists():
            files = [f for f in folder.glob("*")
                     if f.suffix in (".mp3",".wav") and "silence" not in f.name]
            if files:
                return random.choice(files)
        return None

    def _freesound(self, mood: str) -> Path | None:
        queries = MOOD_QUERIES.get(mood, CALM_QUERIES)
        query   = random.choice(queries)
        try:
            log.info(f"Freesound: '{query}'")
            r = requests.get(
                "https://freesound.org/apiv2/search/text/",
                params={"query": query, "filter": "duration:[15 TO 120] type:mp3",
                        "fields": "id,name,previews", "page_size": 15,
                        "token": FREESOUND_KEY},
                timeout=15,
            )
            r.raise_for_status()
            results = r.json().get("results", [])
            if not results:
                return None
            sound  = random.choice(results[:10])
            url    = (sound["previews"].get("preview-hq-mp3") or
                      sound["previews"].get("preview-lq-mp3"))
            folder = MUSIC_CACHE_DIR / mood.replace(" ","_")
            folder.mkdir(exist_ok=True)
            name   = sound["name"][:35].replace(" ","_").replace("/","-")
            out    = folder / f"{sound['id']}_{name}.mp3"
            if not out.exists():
                out.write_bytes(requests.get(url, timeout=30).content)
                log.info(f"Downloaded: {out.name}")
            return out
        except Exception as e:
            log.warning(f"Freesound: {e}")
            return None

    def _generate_tone(self, mood: str) -> Path:
        import math, struct
        is_hype = "motivational" in mood or "epic" in mood

        # Hype tone: brighter, faster pulse
        # Calm tone: deep, slow, meditative
        if is_hype:
            tones = [(130.8,0.22),(196.0,0.18),(261.6,0.20),(329.6,0.15),(392.0,0.10)]
            pulse_rate = 1.2
        else:
            tones = [(55.0,0.30),(82.4,0.20),(110.0,0.15),(164.8,0.10),(220.0,0.08)]
            pulse_rate = 0.08

        out_dir = MUSIC_CACHE_DIR / mood.replace(" ","_")
        out_dir.mkdir(exist_ok=True)
        out = out_dir / f"ambient_{'hype' if is_hype else 'calm'}.wav"
        if out.exists():
            return out

        SR  = 44100
        dur = 30
        samples = []
        for i in range(dur * SR):
            t     = i / SR
            env   = min(1.0, t/3.0) if t < 3 else max(0.0, (dur-t)/4.0) if t > dur-4 else 1.0
            breath = 0.85 + 0.15 * math.sin(2*math.pi*pulse_rate*t)
            s     = sum(v*math.sin(2*math.pi*f*t) for f,v in tones)
            s     = max(-0.85, min(0.85, s * env * breath))
            samples.append(int(s * 32767))

        with wave.open(str(out),"w") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
            wf.writeframes(struct.pack(f"<{len(samples)}h",*samples))
        log.info(f"Generated tone: {out.name}")
        return out
