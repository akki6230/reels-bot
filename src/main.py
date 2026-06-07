"""
src/main.py — Pipeline orchestrator with:
- Fact verification
- Variable duration (20s for Pexels, 30-45s for others)
- Random style selection (kinetic/documentary/cartoon)
"""

import os
import sys
import json
import random
import logging
from datetime import datetime, timezone
from pathlib import Path

ROOT       = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "output"
VIDEOS_DIR = OUTPUT_DIR / "videos"
LOGS_DIR   = OUTPUT_DIR / "logs"
IMAGES_DIR = OUTPUT_DIR / "images"
AUDIO_DIR  = OUTPUT_DIR / "audio"

for d in [VIDEOS_DIR, LOGS_DIR, IMAGES_DIR,
          OUTPUT_DIR / "music", AUDIO_DIR]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            LOGS_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)
log = logging.getLogger(__name__)

sys.path.insert(0, str(ROOT / "src"))
from config      import TOPICS, LANGUAGES, get_hashtags
from fact_gen    import FactGenerator
from video       import VideoCreator
from music       import MusicManager
from narration   import generate_narration
from audio_mixer import mix_audio
from poster      import InstagramPoster

# Reel styles — randomly selected per run
REEL_STYLES = ["kinetic", "documentary", "cartoon"]


def run_pipeline(topic_key: str, lang: str = "en",
                 dry_run: bool = False) -> dict:
    topic  = TOPICS[topic_key]
    result = {
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "topic":        topic_key,
        "lang":         lang,
        "status":       "started",
        "dry_run":      dry_run,
    }

    try:
        prefix = f"{'[DRY RUN] ' if dry_run else ''}[{lang.upper()}]"
        log.info(f"{prefix} ▶ {topic['name']}")

        # 1 — Generate + verify content
        generator = FactGenerator()
        fact_data = generator.generate(topic_key, topic, lang)
        result["hook"]     = fact_data["hook"]
        result["category"] = fact_data.get("fact_category", "")
        log.info(f"{prefix} ✅ Content verified: {fact_data['hook'][:60]}")

        # 2 — Fetch image (random source: Pollinations/Pexels/PIL)
        image_path, img_source, duration_hint = generator.fetch_image(
            topic["image_keywords"], topic_key
        )
        result["image_source"] = img_source
        result["duration"]     = duration_hint
        log.info(f"{prefix} ✅ Image [{img_source}]: {image_path.name}")
        log.info(f"{prefix} 📐 Duration: {duration_hint}s")

        # 3 — Random reel style
        reel_style = random.choice(REEL_STYLES)
        result["reel_style"] = reel_style
        log.info(f"{prefix} 🎨 Style: {reel_style}")

        # 4 — Background music
        music_mgr  = MusicManager()
        music_path = music_mgr.get_track(topic["music_mood"], topic_key)
        log.info(f"{prefix} ✅ Music: {music_path.name}")

        # 5 — Generate narration (TTS)
        log.info(f"{prefix} 🎙 Generating narration...")
        narration_path = generate_narration(
            hook       = fact_data["hook"],
            body       = fact_data["body"],
            lang       = lang,
            topic_key  = topic_key,
            output_dir = AUDIO_DIR,
        )

        # 6 — Mix narration + music
        if narration_path and narration_path.exists():
            log.info(f"{prefix} 🎚 Mixing audio...")
            final_audio = mix_audio(
                music_path     = music_path,
                narration_path = narration_path,
                output_dir     = AUDIO_DIR,
                duration       = duration_hint,
            )
        else:
            log.warning(f"{prefix} ⚠️ No narration — using music only")
            final_audio = music_path

        # 7 — Render video
        creator    = VideoCreator()
        video_path = creator.create_reel(
            image_path  = image_path,
            music_path  = final_audio,
            fact_data   = fact_data,
            topic       = topic,
            lang        = lang,
            output_dir  = VIDEOS_DIR,
            reel_style  = reel_style,
            duration    = duration_hint,
        )
        result["video_path"] = str(video_path)
        log.info(f"{prefix} ✅ Video: {video_path.name}")

        # 8 — Post to Instagram
        if dry_run:
            log.info(f"{prefix} 🔵 Skipping post (dry run)")
            result["status"] = "dry_run_ok"
        else:
            poster   = InstagramPoster()
            hashtags = get_hashtags(topic_key, lang)
            caption  = fact_data["caption"] + "\n\n" + hashtags
            media_id = poster.post_reel(
                video_path, caption, topic_key=topic_key
            )
            result["media_id"] = str(media_id)
            result["status"]   = "posted"
            log.info(f"{prefix} ✅ Posted! ID: {media_id}")

    except Exception as exc:
        result["status"] = "failed"
        result["error"]  = str(exc)
        log.error(f"❌ Pipeline failed: {exc}", exc_info=True)
        sys.exit(1)
    finally:
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = LOGS_DIR / f"run_{topic_key}_{lang}_{ts}.json"
        log_path.write_text(json.dumps(result, indent=2))

    return result


if __name__ == "__main__":
    args    = sys.argv[1:]
    dry_run = "--dry-run" in args
    args    = [a for a in args if a != "--dry-run"]

    if not args or args[0] != "run":
        print("Usage:")
        print("  python src/main.py run <topic> <lang> [--dry-run]")
        print("  python src/main.py run all [--dry-run]")
        print(f"\nTopics: {', '.join(TOPICS)}")
        print(f"Langs:  {', '.join(LANGUAGES)}")
        sys.exit(0)

    if len(args) >= 2 and args[1] == "all":
        for tk in TOPICS:
            for lg in LANGUAGES:
                run_pipeline(tk, lg, dry_run=dry_run)
    else:
        topic_key = args[1] if len(args) > 1 else "space"
        lang      = args[2] if len(args) > 2 else "en"
        if topic_key not in TOPICS:
            print(f"Unknown topic: {topic_key}")
            sys.exit(1)
        run_pipeline(topic_key, lang, dry_run=dry_run)
