"""
src/audio_mixer.py — Mixes narration voice with background music.
Documentary style: voice at 100%, music ducked to 15% during speech,
fades back to 40% after narration ends.

Fixed for MoviePy 1.0.3 compatibility.
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def mix_audio(music_path: Path, narration_path: Path,
              output_dir: Path, duration: int = 20) -> Path:
    """
    Mix background music + narration voice.
    Uses numpy-based ducking compatible with MoviePy 1.0.3
    """
    import numpy as np
    from moviepy.editor import AudioFileClip, CompositeAudioClip

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "mixed_audio.wav"

    try:
        # Load clips
        music     = (AudioFileClip(str(music_path))
                     .subclip(0, duration)
                     .audio_fadeout(2.0))
        narration = AudioFileClip(str(narration_path))
        narr_dur  = min(narration.duration, duration - 0.5)
        narration = narration.subclip(0, narr_dur)

        sample_rate = 44100
        n_samples   = duration * sample_rate

        # ── Get raw audio arrays ───────────────────────────────────────────
        music_arr = music.to_soundarray(fps=sample_rate)
        narr_arr  = narration.to_soundarray(fps=sample_rate)

        # Ensure stereo
        if music_arr.ndim == 1:
            music_arr = np.column_stack([music_arr, music_arr])
        if narr_arr.ndim == 1:
            narr_arr = np.column_stack([narr_arr, narr_arr])

        # Pad/trim to exact duration
        if len(music_arr) < n_samples:
            pad = np.zeros((n_samples - len(music_arr), 2))
            music_arr = np.vstack([music_arr, pad])
        music_arr = music_arr[:n_samples]

        # Narration starts at 0.3s
        narr_start = int(0.3 * sample_rate)
        narr_end   = narr_start + len(narr_arr)
        if narr_end > n_samples:
            narr_arr = narr_arr[:n_samples - narr_start]
            narr_end = n_samples

        # ── Build music volume envelope ────────────────────────────────────
        # 0.40 normally → ducks to 0.15 during narration → back to 0.40
        vol_env    = np.full(n_samples, 0.40)
        duck_start = narr_start - int(0.3 * sample_rate)  # start ducking 0.3s before narration
        duck_end   = narr_end   + int(0.5 * sample_rate)  # stop ducking 0.5s after narration
        fade_in_s  = int(0.4 * sample_rate)
        fade_out_s = int(1.2 * sample_rate)

        duck_start = max(0, duck_start)
        duck_end   = min(n_samples, duck_end)

        # Smooth fade down
        for i in range(min(fade_in_s, duck_start, n_samples - duck_start)):
            t = i / fade_in_s
            vol_env[duck_start + i] = 0.40 - 0.25 * t

        # Full duck region
        full_duck_start = duck_start + fade_in_s
        full_duck_end   = max(full_duck_start, duck_end - fade_out_s)
        vol_env[full_duck_start:full_duck_end] = 0.15

        # Smooth fade up
        fade_up_start = full_duck_end
        fade_up_end   = min(n_samples, fade_up_start + fade_out_s)
        for i in range(fade_up_end - fade_up_start):
            t = i / fade_out_s
            vol_env[fade_up_start + i] = 0.15 + 0.25 * t

        # Rest stays at 0.40
        vol_env[fade_up_end:] = 0.40

        # Apply volume envelope to music
        vol_col   = vol_env.reshape(-1, 1)
        music_arr = music_arr * vol_col

        # ── Narration at 0.95 volume ───────────────────────────────────────
        narr_full = np.zeros((n_samples, 2))
        end_idx   = min(narr_start + len(narr_arr), n_samples)
        narr_full[narr_start:end_idx] = narr_arr[:end_idx - narr_start] * 0.95

        # ── Mix ────────────────────────────────────────────────────────────
        mixed = music_arr + narr_full
        mixed = np.clip(mixed, -1.0, 1.0)   # prevent clipping

        # ── Write to WAV ───────────────────────────────────────────────────
        import wave, struct
        with wave.open(str(out_path), "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            pcm = (mixed * 32767).astype(np.int16)
            wf.writeframes(pcm.tobytes())

        log.info(f"✅ Mixed audio: {out_path.name} ({out_path.stat().st_size // 1024} KB)")
        return out_path

    except Exception as e:
        log.warning(f"Audio mixing failed ({e}), using music only")
        return music_path
