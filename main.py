"""
src/main.py — Pipeline orchestrator
Usage:
    python src/main.py run space
    python src/main.py run history --dry-run
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
OUTPUT_DIR   = ROOT / "output"
VIDEOS_DIR   = OUTPUT_DIR / "videos"
LOGS_DIR     = OUTPUT_DIR / "logs"
IMAGES_DIR   = OUTPUT_DIR / "images"

for d in [VIDEOS_DIR, LOGS_DIR, IMAGES_DIR, OUTPUT_DIR / "music"]:
    d.mkdir(parents=True, exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
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
from config    import TOPICS
from fact_gen  import FactGenerator
from video     import VideoCreator
from music     import MusicManager
from poster    import InstagramPoster


# ── Pipeline ───────────────────────────────────────────────────────────────────

def run_pipeline(topic_key: str, dry_run: bool = False) -> dict:
    topic  = TOPICS[topic_key]
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topic":     topic_key,
        "status":    "started",
        "dry_run":   dry_run,
    }

    try:
        log.info(f"{'[DRY RUN] ' if dry_run else ''}▶ Pipeline: {topic['name']}")

        # 1 — Generate fact
        generator = FactGenerator()
        fact_data = generator.generate(topic_key, topic)
        result["hook"]     = fact_data["hook"]
        result["category"] = fact_data.get("fact_category", "")
        log.info(f"✅ Fact: {fact_data['hook']}")

        # 2 — Fetch image
        image_path = generator.fetch_image(topic["image_keywords"], topic_key)
        log.info(f"✅ Image: {image_path}")

        # 3 — Music
        music_mgr  = MusicManager()
        music_path = music_mgr.get_track(topic["music_mood"], topic_key)
        log.info(f"✅ Music: {music_path}")

        # 4 — Render video
        creator    = VideoCreator()
        video_path = creator.create_reel(
            image_path=image_path,
            music_path=music_path,
            fact_data=fact_data,
            topic=topic,
            output_dir=VIDEOS_DIR,
        )
        result["video_path"] = str(video_path)
        log.info(f"✅ Video: {video_path}")

        # 5 — Post (skip if dry run)
        if dry_run:
            log.info("🔵 DRY RUN — skipping Instagram post")
            result["status"] = "dry_run_ok"
        else:
            poster  = InstagramPoster()
            caption = fact_data["caption"] + "\n\n" + topic["hashtags"]
            media_id = poster.post_reel(video_path, caption)
            result["media_id"] = str(media_id)
            result["status"]   = "posted"
            log.info(f"✅ Posted! Media ID: {media_id}")

    except Exception as exc:
        result["status"] = "failed"
        result["error"]  = str(exc)
        log.error(f"❌ Pipeline failed: {exc}", exc_info=True)
        sys.exit(1)
    finally:
        # Always save a run log
        log_path = LOGS_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_path.write_text(json.dumps(result, indent=2))

    return result


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] != "run":
        print("Usage: python src/main.py run <topic> [--dry-run]")
        print(f"Topics: {', '.join(TOPICS)}")
        sys.exit(0)

    topic_key = args[1] if len(args) > 1 else "space"
    dry_run   = "--dry-run" in args

    if topic_key not in TOPICS:
        print(f"Unknown topic '{topic_key}'. Valid: {', '.join(TOPICS)}")
        sys.exit(1)

    run_pipeline(topic_key, dry_run=dry_run)
