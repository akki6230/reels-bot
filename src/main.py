"""
src/main.py — Pipeline orchestrator.
- Hindi only
- 30% voiceover probability
- 10-20s duration (20s if voiceover)
- Music energy matched to topic
"""

import os, sys, json, random, logging
from datetime import datetime, timezone
from pathlib import Path

ROOT       = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "output"
VIDEOS_DIR = OUTPUT_DIR / "videos"
LOGS_DIR   = OUTPUT_DIR / "logs"
IMAGES_DIR = OUTPUT_DIR / "images"
AUDIO_DIR  = OUTPUT_DIR / "audio"

for d in [VIDEOS_DIR, LOGS_DIR, IMAGES_DIR, OUTPUT_DIR/"music", AUDIO_DIR]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_DIR/f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ],
)
log = logging.getLogger(__name__)

sys.path.insert(0, str(ROOT/"src"))
from config      import (TOPICS, LANGUAGES, get_hashtags,
                          get_duration_and_voice, get_music_volume)
from fact_gen    import FactGenerator
from video       import VideoCreator
from music       import MusicManager
from narration   import generate_narration
from audio_mixer import mix_audio
from poster      import InstagramPoster

REEL_STYLES = ["kinetic", "documentary", "cartoon"]


def run_pipeline(topic_key: str, lang: str = "hi",
                 dry_run: bool = False) -> dict:
    topic  = TOPICS[topic_key]
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topic": topic_key, "lang": lang,
        "status": "started", "dry_run": dry_run,
    }

    try:
        # 1 — Duration + voiceover decision
        duration, use_voice = get_duration_and_voice()
        result["duration"]    = duration
        result["use_voice"]   = use_voice
        log.info(f"▶ [{topic['name_hi']}] {duration}s | Voice: {'YES' if use_voice else 'NO'}")

        # 2 — Generate + verify fact
        generator = FactGenerator()
        fact_data = generator.generate(topic_key, topic, lang)
        result["hook"]     = fact_data["hook"]
        result["category"] = fact_data.get("fact_category","")
        log.info(f"✅ Fact: {fact_data['hook'][:60]}")

        # 3 — Image
        image_path, img_source, _ = generator.fetch_image(
            topic["image_keywords"], topic_key
        )
        result["image_source"] = img_source
        log.info(f"✅ Image [{img_source}]: {image_path.name}")

        # 4 — Reel style
        reel_style = random.choice(REEL_STYLES)
        result["reel_style"] = reel_style

        # 5 — Music (energy-matched)
        music_mgr  = MusicManager()
        music_path = music_mgr.get_track(topic["music_mood"], topic_key)
        vol        = get_music_volume(topic["music_energy"])
        log.info(f"✅ Music [{topic['music_energy']}]: {music_path.name}")

        # 6 — Voiceover (only 30% of reels)
        final_audio = music_path
        if use_voice:
            log.info("🎙 Generating voiceover...")
            narr = generate_narration(
                hook=fact_data["hook"], body=fact_data["body"],
                lang=lang, topic_key=topic_key, output_dir=AUDIO_DIR,
            )
            if narr and narr.exists():
                final_audio = mix_audio(
                    music_path=music_path, narration_path=narr,
                    output_dir=AUDIO_DIR, duration=duration,
                )
                log.info(f"✅ Mixed audio: {final_audio.name}")
            else:
                log.warning("Voiceover failed — using music only")

        # 7 — Render video
        creator    = VideoCreator()
        video_path = creator.create_reel(
            image_path=image_path, music_path=final_audio,
            fact_data=fact_data, topic=topic, lang=lang,
            output_dir=VIDEOS_DIR, reel_style=reel_style,
            duration=duration, music_volume=vol,
        )
        result["video_path"] = str(video_path)
        log.info(f"✅ Video: {video_path.name}")

        # 8 — Post
        if dry_run:
            log.info("🔵 Dry run — skipping post")
            result["status"] = "dry_run_ok"
        else:
            poster   = InstagramPoster()
            hashtags = get_hashtags(topic_key, lang)
            caption  = fact_data["caption"] + "\n\n" + hashtags
            media_id = poster.post_reel(video_path, caption, topic_key=topic_key)
            result["media_id"] = str(media_id)
            result["status"]   = "posted"
            log.info(f"✅ Posted! ID: {media_id}")

    except Exception as exc:
        result["status"] = "failed"
        result["error"]  = str(exc)
        log.error(f"❌ Failed: {exc}", exc_info=True)
        sys.exit(1)
    finally:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        (LOGS_DIR/f"run_{topic_key}_{lang}_{ts}.json").write_text(
            json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    args    = sys.argv[1:]
    dry_run = "--dry-run" in args
    args    = [a for a in args if a != "--dry-run"]

    if not args or args[0] != "run":
        print(f"Usage: python src/main.py run <topic> [--dry-run]")
        print(f"Topics: {', '.join(TOPICS)}")
        sys.exit(0)

    topic_key = args[1] if len(args) > 1 else "space"
    lang      = "hi"  # always Hindi
    if topic_key not in TOPICS:
        print(f"Unknown topic: {topic_key}")
        sys.exit(1)
    run_pipeline(topic_key, lang, dry_run=dry_run)
