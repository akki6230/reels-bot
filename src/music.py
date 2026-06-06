"""
src/music.py — Fetches royalty-free background music.
Priority: cached file → Freesound API → local files → generated ambient tone

The generated ambient fallback uses numpy to synthesize a soft, pleasant
background tone (layered sine waves with reverb-like decay) so there is
always music — even with no API key and no internet.
"""

import os
import math
import random
import struct
import logging
import wave
from pathlib import Path

import requests

log = logging.getLogger(__name__)

ROOT            = Path(__file__).parent.parent
MUSIC_CACHE_DIR = ROOT / "output" / "music"
LOCAL_MUSIC_DIR = ROOT / "music"
FREESOUND_KEY   = os.environ.get("FREESOUND_API_KEY", "")

SAMPLE_RATE = 44100

# Per-mood ambient tone settings: list of (frequency_hz, relative_volume)
# Layering multiple sine waves creates a rich, harmonic ambient sound
MOOD_TONES = {
    "ambient cinematic space": [
        # Deep space: low drones, slow pulse
        (55.0,  0.30),   # A1 — deep bass drone
        (82.4,  0.20),   # E2 — fifth above
        (110.0, 0.15),   # A2 — octave
        (164.8, 0.10),   # E3 — upper fifth
        (220.0, 0.08),   # A3 — shimmer
        (329.6, 0.05),   # E4 — high sparkle
    ],
    "epic orchestral historical": [
        # Cinematic: minor chord feel, dramatic
        (65.4,  0.28),   # C2 — powerful low
        (98.0,  0.22),   # G2 — fifth
        (130.8, 0.18),   # C3 — octave
        (155.6, 0.12),   # Eb3 — minor third (drama)
        (196.0, 0.10),   # G3 — upper fifth
        (261.6, 0.07),   # C4 — mid shimmer
    ],
    "nature acoustic world": [
        # Warm, acoustic, peaceful — major feel
        (174.6, 0.25),   # F3 — warm mid
        (220.0, 0.20),   # A3 — major third
        (261.6, 0.18),   # C4 — fifth
        (349.2, 0.12),   # F4 — octave
        (440.0, 0.08),   # A4 — high warmth
        (523.2, 0.05),   # C5 — airy top
    ],
    "electronic upbeat discovery": [
        # Bright, optimistic, electronic pulse
        (130.8, 0.22),   # C3 — punchy bass
        (196.0, 0.18),   # G3 — fifth
        (261.6, 0.20),   # C4 — main tone
        (329.6, 0.15),   # E4 — major third
        (392.0, 0.10),   # G4 — upper fifth
        (523.2, 0.08),   # C5 — sparkle
    ],
}

MOOD_QUERIES = {
    "ambient cinematic space": [
        "space ambient cinematic loop",
        "cosmic drone ambient",
        "deep space sci-fi music",
    ],
    "epic orchestral historical": [
        "epic orchestral cinematic loop",
        "historical dramatic music",
        "medieval epic music loop",
    ],
    "nature acoustic world": [
        "nature acoustic guitar peaceful",
        "world music calm loop",
        "acoustic meditation music",
    ],
    "electronic upbeat discovery": [
        "electronic discovery upbeat loop",
        "futuristic electronic loop",
        "uplifting electronic background",
    ],
}


class MusicManager:
    def get_track(self, mood: str, topic_key: str) -> Path:
        MUSIC_CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # 1. Cached file from previous runs
        cached = self._cached(mood)
        if cached:
            log.info(f"Using cached music: {cached.name}")
            return cached

        # 2. Freesound API (if key available)
        if FREESOUND_KEY:
            track = self._freesound(mood)
            if track:
                return track

        # 3. Local music files in repo
        local = self._local(topic_key)
        if local:
            log.info(f"Using local music: {local.name}")
            return local

        # 4. Generate ambient tone (always works, no internet needed)
        log.info(f"Generating ambient music for mood: {mood}")
        return self._generate_ambient(mood)

    # ── Sources ────────────────────────────────────────────────────────────────

    def _cached(self, mood: str) -> Path | None:
        folder = MUSIC_CACHE_DIR / mood.replace(" ", "_")
        if folder.exists():
            files = [f for f in folder.glob("*") if f.suffix in (".mp3", ".wav")
                     and "silence" not in f.name and "ambient" not in f.name]
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
                    "query":     query,
                    "filter":    "duration:[15 TO 120] type:mp3",
                    "fields":    "id,name,previews,duration",
                    "page_size": 15,
                    "token":     FREESOUND_KEY,
                },
                timeout=15,
            )
            r.raise_for_status()
            results = r.json().get("results", [])
            if not results:
                return None

            sound  = random.choice(results[:10])
            url    = (sound["previews"].get("preview-hq-mp3")
                      or sound["previews"].get("preview-lq-mp3"))
            folder = MUSIC_CACHE_DIR / mood.replace(" ", "_")
            folder.mkdir(exist_ok=True)
            name   = sound["name"][:40].replace(" ", "_").replace("/", "-")
            out    = folder / f"{sound['id']}_{name}.mp3"
            if not out.exists():
                out.write_bytes(requests.get(url, timeout=30).content)
                log.info(f"Downloaded from Freesound: {out.name}")
            return out
        except Exception as e:
            log.warning(f"Freesound error: {e}")
            return None

    def _local(self, topic_key: str) -> Path | None:
        for folder in [LOCAL_MUSIC_DIR / topic_key, LOCAL_MUSIC_DIR]:
            if folder.exists():
                files = [f for f in folder.glob("*") if f.suffix in (".mp3", ".wav")]
                if files:
                    return random.choice(files)
        return None

    # ── Ambient tone generator ─────────────────────────────────────────────────

    def _generate_ambient(self, mood: str, duration: int = 30) -> Path:
        """
        Synthesize a soft ambient background track by layering sine waves.
        Applies a slow volume envelope (fade in → sustain → fade out) and
        gentle amplitude modulation to make it feel alive, not mechanical.
        Pure Python + stdlib only — no numpy, no external deps.
        """
        out_dir = MUSIC_CACHE_DIR / mood.replace(" ", "_")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"ambient_{mood[:20].replace(' ','_')}.wav"

        # Return cached generated file if it exists
        if out_path.exists():
            log.info(f"Using previously generated ambient: {out_path.name}")
            return out_path

        log.info(f"Synthesizing ambient tone ({duration}s) for: {mood}")

        tones      = MOOD_TONES.get(mood, MOOD_TONES["ambient cinematic space"])
        n_samples  = duration * SAMPLE_RATE
        # Add a tiny random detune to each oscillator to avoid sterile perfection
        detunes    = [random.uniform(-0.3, 0.3) for _ in tones]

        frames = []
        for i in range(n_samples):
            t = i / SAMPLE_RATE

            # Master envelope: 3s fade-in, sustain, 4s fade-out
            if t < 3.0:
                env = t / 3.0
            elif t > duration - 4.0:
                env = (duration - t) / 4.0
            else:
                env = 1.0
            env = max(0.0, min(1.0, env))

            # Slow amplitude modulation (breathing effect, ~0.1 Hz)
            breath = 0.85 + 0.15 * math.sin(2 * math.pi * 0.08 * t)

            # Sum all oscillators
            sample = 0.0
            for (freq, vol), detune in zip(tones, detunes):
                f = freq + detune
                # Each oscillator gets its own slow vibrato
                vibrato = 1.0 + 0.003 * math.sin(2 * math.pi * 0.5 * t)
                sample += vol * math.sin(2 * math.pi * f * vibrato * t)

            # Mix down, apply envelope and breathing
            sample = sample * env * breath

            # Soft clip to prevent harsh distortion
            sample = max(-0.85, min(0.85, sample))

            # Convert to 16-bit PCM
            frames.append(int(sample * 32767))

        # Write WAV file
        with wave.open(str(out_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            packed = struct.pack(f"<{len(frames)}h", *frames)
            wf.writeframes(packed)

        log.info(f"Ambient tone generated: {out_path.name} ({out_path.stat().st_size // 1024} KB)")
        return out_path
