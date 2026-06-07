"""
src/audio_mixer.py — Mixes narration voice with background music.
Documentary style: voice at 100%, music ducked to 15% during speech,
fades back to 40% after narration ends.
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def mix_audio(music_path: Path, narration_path: Path,
              output_dir: Path, duration: int = 20) -> Path:
    """
    Mix background music + narration voice.

    Levels:
      - Music:     15% volume during narration (ducked)
      - Narration: 95% volume (clear and prominent)
      - Music fades back to 40% after narration ends

    Returns path to mixed .wav file.
    """
    from moviepy.editor import AudioFileClip, CompositeAudioClip

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "mixed_audio.wav"

    try:
        # Load music
        music = (AudioFileClip(str(music_path))
                 .subclip(0, duration)
                 .audio_fadeout(2.0))

        # Load narration
        narration = AudioFileClip(str(narration_path))
        narr_dur  = min(narration.duration, duration - 1.0)
        narration = narration.subclip(0, narr_dur)

        # Duck music during narration, fade back after
        def music_volume(t):
            """Volume curve: 40% → ducks to 15% at 0.5s → back to 40% after narration."""
            duck_start = 0.5
            duck_end   = narr_dur + 0.3
            fade_dur   = 1.5

            if t < duck_start:
                # Fade from 40% to 15%
                progress = t / duck_start
                return 0.40 - (0.25 * progress)
            elif t < duck_end:
                return 0.15   # ducked under voice
            elif t < duck_end + fade_dur:
                # Fade back up from 15% to 40%
                progress = (t - duck_end) / fade_dur
                return 0.15 + (0.25 * progress)
            else:
                return 0.40   # back to normal

        music_ducked = music.volumex(music_volume)

        # Set narration volume and start time
        narration_loud = narration.volumex(0.95).set_start(0.3)

        # Composite
        mixed = CompositeAudioClip([music_ducked, narration_loud])
        mixed = mixed.subclip(0, duration)

        # Export
        mixed.write_audiofile(
            str(out_path),
            fps=44100,
            nbytes=2,
            codec="pcm_s16le",
            logger=None,
        )
        log.info(f"✅ Mixed audio: {out_path.name}")
        return out_path

    except Exception as e:
        log.warning(f"Audio mixing failed ({e}), using music only")
        return music_path
