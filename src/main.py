"""
src/main.py — Pipeline orchestrator
Usage:
    python src/main.py run space en
    python src/main.py run sports hi --dry-run
    python src/main.py run all        ← runs all 12 topic+lang combos
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

ROOT       = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "output"
VIDEOS_DIR = OUTPUT_DIR / "videos"
LOGS_DIR   = OUTPUT_DIR / "logs"
IMAGES_DIR = OUTPUT_DIR / "images"

for d in [VIDEOS_DIR, LOGS_DIR, IMAGES_DIR, OUTPUT_DIR / "music"]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ],
)
log = logging.getLogger(__name__)

sys.path.insert(0, str(ROOT / "src"))
from config   import TOPICS, LANGUAGES, get_hashtags
from fact_gen import FactGenerator
from video    import VideoCreator
from music    import MusicManager
from poster   import InstagramPoster


def run_pipeline(topic_key: str, lang: str = "en", dry_run: bool = False) -> dict:
    topic  = TOPICS[topic_key]
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topic":     topic_key,
        "lang":      lang,
        "status":    "started",
        "dry_run":   dry_run,
    }

    try:
        prefix = f"{'[DRY RUN] ' if dry_run else ''}[{lang.upper()}]"
        log.info(f"{prefix} ▶ {topic['name']}")

        # 1 — Generate content (fact or news)
        generator = FactGenerator()
        fact_data = generator.generate(topic_key, topic, lang)
        result["hook"]     = fact_data["hook"]
        result["category"] = fact_data.get("fact_category", "")
        log.info(f"{prefix} ✅ Content: {fact_data['hook'][:60]}")

        # 2 — Fetch image (shared between EN + HI for same topic run)
        image_path = generator.fetch_image(topic["image_keywords"], topic_key)
        log.info(f"{prefix} ✅ Image: {image_path.name}")

        # 3 — Music
        music_mgr  = MusicManager()
        music_path = music_mgr.get_track(topic["music_mood"], topic_key)
        log.info(f"{prefix} ✅ Music: {music_path.name}")

        # 4 — Render video
        creator    = VideoCreator()
        video_path = creator.create_reel(
            image_path=image_path,
            music_path=music_path,
            fact_data=fact_data,
            topic=topic,
            lang=lang,
            output_dir=VIDEOS_DIR,
        )
        result["video_path"] = str(video_path)

        # 5 — Post to Instagram
        if dry_run:
            log.info(f"{prefix} 🔵 Skipping Instagram post (dry run)")
            result["status"] = "dry_run_ok"
        else:
            poster   = InstagramPoster()
            hashtags = get_hashtags(topic_key, lang)
            caption  = fact_data["caption"] + "\n\n" + hashtags
            media_id = poster.post_reel(video_path, caption, topic_key=topic_key)
            result["media_id"] = str(media_id)
            result["status"]   = "posted"
            log.info(f"{prefix} ✅ Posted! ID: {media_id}")

    except Exception as exc:
        result["status"] = "failed"
        result["error"]  = str(exc)
        log.error(f"❌ Pipeline failed [{lang}] {topic_key}: {exc}", exc_info=True)
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
        print(f"\nTopics : {', '.join(TOPICS)}")
        print(f"Langs  : {', '.join(LANGUAGES)}")
        sys.exit(0)

    if len(args) >= 2 and args[1] == "all":
        for tk in TOPICS:
            for lg in LANGUAGES:
                run_pipeline(tk, lg, dry_run=dry_run)
    else:
        topic_key = args[1] if len(args) > 1 else "space"
        lang      = args[2] if len(args) > 2 else "en"
        if topic_key not in TOPICS:
            print(f"Unknown topic '{topic_key}'. Valid: {', '.join(TOPICS)}")
            sys.exit(1)
        if lang not in LANGUAGES:
            print(f"Unknown lang '{lang}'. Valid: {', '.join(LANGUAGES)}")
            sys.exit(1)
        run_pipeline(topic_key, lang, dry_run=dry_run)
