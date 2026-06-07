"""
src/audio_mixer.py — Mixes narration voice with background music.
Documentary style: voice at 95%, music ducked to 15% during speech.
Fully compatible with MoviePy 1.0.3 + numpy.
"""

import logging
import wave
import struct
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)

SAMPLE_RATE = 44100


def _load_audio_as_array(clip, duration: int) -> np.ndarray:
    """
    Safely load a MoviePy AudioClip as a (N, 2) float32 numpy array.
    Handles mono, stereo, and edge cases.
    """
    n_samples = duration * SAMPLE_RATE

    try:
        # Generate time array
        times = np.linspace(0, duration, n_samples, endpoint=False)
        # Get audio frame by frame
        arr = clip.get_frame(0)   # probe shape

        # Use make_frame to build full array
        frames = []
        chunk  = 1024
        for start in range(0, n_samples, chunk):
            end   = min(start + chunk, n_samples)
            t_arr = times[start:end]
            chunk_frames = np.array([clip.get_frame(t) for t in t_arr])
            frames.append(chunk_frames)

        arr = np.vstack(frames)   # (N,) or (N, 2)

    except Exception:
        # Fallback: use to_soundarray if available
        try:
            arr = clip.to_soundarray(fps=SAMPLE_RATE)
        except Exception as e:
            log.warning(f"Could not load audio: {e}")
            return np.zeros((n_samples, 2), dtype=np.float32)

    # Ensure 2D stereo
    if arr.ndim == 1:
        arr = np.column_stack([arr, arr])
    elif arr.shape[1] == 1:
        arr = np.hstack([arr, arr])

    # Trim or pad to exact duration
    if len(arr) > n_samples:
        arr = arr[:n_samples]
    elif len(arr) < n_samples:
        pad = np.zeros((n_samples - len(arr), 2), dtype=np.float32)
        arr = np.vstack([arr, pad])

    return arr.astype(np.float32)


def mix_audio(music_path: Path, narration_path: Path,
              output_dir: Path, duration: int = 20) -> Path:
    """
    Mix background music + narration.
    Music ducks to 15% during voice, returns to 40% after.
    """
    from moviepy.editor import AudioFileClip

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"mixed_audio_{duration}s.wav"

    try:
        n_samples = duration * SAMPLE_RATE

        # ── Load music ─────────────────────────────────────────────────────
        music_clip = (AudioFileClip(str(music_path))
                      .subclip(0, min(duration, AudioFileClip(str(music_path)).duration))
                      .audio_fadeout(2.0))
        music_arr  = _load_audio_as_array(music_clip, duration)

        # ── Load narration ─────────────────────────────────────────────────
        narr_raw   = AudioFileClip(str(narration_path))
        narr_dur   = min(narr_raw.duration, duration - 0.5)
        narr_clip  = narr_raw.subclip(0, narr_dur)
        narr_len   = int(narr_dur * SAMPLE_RATE)
        narr_clip2 = narr_clip.set_duration(narr_dur)
        narr_arr   = _load_audio_as_array(narr_clip2, int(narr_dur))

        # ── Build volume envelope for music ────────────────────────────────
        vol_env         = np.full(n_samples, 0.40, dtype=np.float32)
        narr_start_samp = int(0.3  * SAMPLE_RATE)
        narr_end_samp   = narr_start_samp + narr_len
        fade_in_samp    = int(0.4  * SAMPLE_RATE)
        fade_out_samp   = int(1.5  * SAMPLE_RATE)

        # Ramp down
        ramp_end = min(narr_start_samp + fade_in_samp, n_samples)
        for i in range(ramp_end - narr_start_samp):
            idx = narr_start_samp + i
            if idx < n_samples:
                vol_env[idx] = 0.40 - 0.25 * (i / fade_in_samp)

        # Full duck
        duck_start = ramp_end
        duck_end   = min(narr_end_samp, n_samples - fade_out_samp)
        if duck_end > duck_start:
            vol_env[duck_start:duck_end] = 0.15

        # Ramp back up
        ramp_up_end = min(duck_end + fade_out_samp, n_samples)
        for i in range(ramp_up_end - duck_end):
            idx = duck_end + i
            if idx < n_samples:
                vol_env[idx] = 0.15 + 0.25 * (i / fade_out_samp)

        # Rest at 0.40
        if ramp_up_end < n_samples:
            vol_env[ramp_up_end:] = 0.40

        # ── Apply envelope ─────────────────────────────────────────────────
        music_ducked = music_arr * vol_env.reshape(-1, 1)

        # ── Place narration ────────────────────────────────────────────────
        narr_full = np.zeros((n_samples, 2), dtype=np.float32)
        end_idx   = min(narr_start_samp + len(narr_arr), n_samples)
        copy_len  = end_idx - narr_start_samp
        narr_full[narr_start_samp:end_idx] = narr_arr[:copy_len] * 0.95

        # ── Mix & clip ─────────────────────────────────────────────────────
        mixed = np.clip(music_ducked + narr_full, -1.0, 1.0)

        # ── Write WAV ──────────────────────────────────────────────────────
        pcm = (mixed * 32767).astype(np.int16)
        with wave.open(str(out_path), "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm.tobytes())

        size_kb = out_path.stat().st_size // 1024
        log.info(f"✅ Mixed audio: {out_path.name} ({size_kb} KB)")
        return out_path

    except Exception as e:
        log.warning(f"Audio mixing failed ({e}), using music only")
        return music_path
