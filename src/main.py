"""
src/main.py — Pipeline with illustrated + animated mode selection.
65% illustrated (HF scenes), 35% animated (kinetic/documentary/cartoon)
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
SCENES_DIR = OUTPUT_DIR / "scenes"

for d in [VIDEOS_DIR,LOGS_DIR,IMAGES_DIR,OUTPUT_DIR/"music",AUDIO_DIR,SCENES_DIR]:
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

# Style weights: 70% listicle, 30% animated
LISTICLE_PROB  = 0.70
ANIMATED_STYLES = ["kinetic", "documentary", "cartoon"]


def pick_style() -> str:
    if random.random() < LISTICLE_PROB:
        return "listicle"
    return random.choice(ANIMATED_STYLES)


def run_pipeline(topic_key: str, lang: str = "hi",
                 dry_run: bool = False) -> dict:
    topic  = TOPICS[topic_key]
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topic": topic_key, "lang": lang,
        "status": "started", "dry_run": dry_run,
    }

    try:
        # 1 — Duration + voiceover
        duration, use_voice = get_duration_and_voice()
        result["duration"]  = duration
        result["use_voice"] = use_voice
        log.info(f"▶ [{topic['name_hi']}] {duration}s | Voice: {'YES' if use_voice else 'NO'}")

        # 2 — Style selection
        reel_style = pick_style()
        result["reel_style"] = reel_style
        log.info(f"🎨 Style: {reel_style}")

        # 3 — Generate content
        if reel_style == "listicle":
            # ── CAROUSEL MODE (swipeable slides) ──────────────────────────
            from carousel_gen import CarouselGenerator

            log.info("📋 Carousel mode — generating 5 slides...")
            cg      = CarouselGenerator()
            content = cg.generate_content(topic_key)
            slides  = content.get("slides", [])

            log.info(f"🖼 Fetching {len(slides)} images...")
            run_id      = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_paths = cg.fetch_images(slides, topic_key, run_id)

            log.info("🎨 Rendering carousel slides...")
            slide_paths = cg.render_all_slides(content, image_paths,
                                               topic_key, run_id)

            result["hook"]         = content.get("title", "")
            result["image_source"] = "carousel_pexels"
            result["reel_style"]   = "carousel"
            log.info(f"✅ {len(slide_paths)} slides rendered")

            # Post carousel
            if dry_run:
                log.info("🔵 Dry run — skipping carousel post")
                result["status"] = "dry_run_ok"
            else:
                poster   = InstagramPoster()
                hashtags = get_hashtags(topic_key, lang)
                title    = content.get("title", "")
                facts_preview = " | ".join(
                    s.get("headline","") for s in slides[1:4]
                )
                caption = f"{title}\n\n{facts_preview}\n\n{hashtags}"
                media_id = poster.post_carousel(slide_paths, caption)
                result["media_id"] = str(media_id)
                result["status"]   = "posted"
                log.info(f"✅ Carousel posted! ID: {media_id}")

            # Skip to finally — no video needed for carousel
            return result

        else:
            # ── ANIMATED MODE ──────────────────────────────────────────────
            generator = FactGenerator()
            fact_data = generator.generate(topic_key, topic, lang)
            result["hook"]     = fact_data["hook"]
            result["category"] = fact_data.get("fact_category","")
            log.info(f"✅ Fact: {fact_data['hook'][:60]}")
            caption_hook = fact_data["caption"]
            caption_body = ""

            # 4 — Image / scenes
            scene_paths = None
            image_path  = None
            image_path, img_source, _ = generator.fetch_image(
                topic["image_keywords"], topic_key
            )
            result["image_source"] = img_source
            log.info(f"✅ Image [{img_source}]")

            # 5 — Music
            music_mgr  = MusicManager()
            music_path = music_mgr.get_track(topic["music_mood"], topic_key)
            vol        = get_music_volume(topic["music_energy"])

            # 6 — Voiceover (30% probability)
            final_audio   = music_path
            narr_duration = 0.0

            if use_voice:
                log.info("🎙 Generating voiceover...")
                narr, narr_duration = generate_narration(
                    hook=fact_data["hook"], body=fact_data["body"],
                    lang=lang, topic_key=topic_key, output_dir=AUDIO_DIR,
                    reel_duration=duration,
                )
                if narr and narr.exists():
                    if narr_duration > duration - 2:
                        duration = min(45, int(narr_duration) + 4)
                        result["duration"] = duration
                        log.info(f"📐 Extended to {duration}s")
                    final_audio = mix_audio(
                        music_path=music_path, narration_path=narr,
                        output_dir=AUDIO_DIR, duration=duration,
                    )
                    log.info(f"✅ Narration: {narr_duration:.1f}s")
                else:
                    log.warning("Voiceover failed — music only")
                    narr_duration = 0.0

            # 7 — Render animated video
            creator    = VideoCreator()
            video_path = creator.create_reel(
                image_path    = image_path or Path("/dev/null"),
                music_path    = final_audio,
                fact_data     = fact_data,
                topic         = topic,
                lang          = lang,
                output_dir    = VIDEOS_DIR,
                reel_style    = reel_style,
                duration      = duration,
                music_volume  = vol,
                scene_paths   = scene_paths,
                narr_duration = narr_duration,
            )
            result["video_path"] = str(video_path)

        # 8 — Post
        if dry_run:
            log.info("🔵 Dry run — skipping post")
            result["status"] = "dry_run_ok"
        else:
            poster   = InstagramPoster()
            hashtags = get_hashtags(topic_key, lang)
            caption  = caption_hook + ("\n\n" + caption_body if caption_body else "") + "\n\n" + hashtags
            media_id = poster.post_reel(video_path, caption, topic_key=topic_key)
            result["media_id"] = str(media_id)
            result["status"]   = "posted"
            log.info(f"✅ Posted! ID: {media_id}")

    except Exception as exc:
        result["status"] = "failed"
        result["error"]  = str(exc)
        log.error(f"❌ {exc}", exc_info=True)
        sys.exit(1)
    finally:
        ts=(datetime.now().strftime("%Y%m%d_%H%M%S"))
        (LOGS_DIR/f"run_{topic_key}_{lang}_{ts}.json").write_text(
            json.dumps(result,indent=2))
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
    if topic_key not in TOPICS:
        print(f"Unknown topic: {topic_key}")
        sys.exit(1)
    run_pipeline(topic_key, "hi", dry_run=dry_run)
