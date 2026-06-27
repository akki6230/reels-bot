"""
src/poster.py — Posts Instagram Reels using instagrapi with:
- Pre-saved session (no fresh login from GitHub Actions)
- Trending Instagram audio IDs per topic
- Rotating audio selection to keep content fresh
"""

import os
import json
import time
import random
import logging
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired

log = logging.getLogger(__name__)

ROOT         = Path(__file__).parent.parent
SESSION_FILE = ROOT / "output" / "ig_session.json"

IG_USERNAME = os.environ["INSTAGRAM_USERNAME"]
IG_PASSWORD = os.environ["INSTAGRAM_PASSWORD"]
SESSION_ENV = os.environ.get("IG_SESSION_DATA", "").strip()

# ── Trending Instagram Audio IDs ───────────────────────────────────────────────
# These are real Instagram audio track IDs that are trending/popular
# Format: {"audio_id": "track_name"} — Instagram uses these internally
# Audio plays INSTEAD of your generated music when set
# Update these periodically with new trending tracks
# Find IDs by: saving a reel with trending audio → inspect the media object

TRENDING_AUDIO = {
    "examfacts": ["36312999321678028", "26595002846841454"],
    "psychology": ["36312999321678028", "945355724495601", "26595002846841454"],
    "mindblowing": ["37875166522082301", "645214053257804"],
    "gk": ["36109372152009884", "945355724495601"],
}


class InstagramPoster:
    def __init__(self):
        self.cl = Client()
        self.cl.delay_range = [3, 8]
        self._load_session()

    def _load_session(self):
        session_data = None

        if SESSION_ENV:
            try:
                session_data = json.loads(SESSION_ENV)
                log.info("Session loaded from IG_SESSION_DATA secret")
            except Exception:
                log.warning("IG_SESSION_DATA is not valid JSON")

        if not session_data and SESSION_FILE.exists():
            try:
                session_data = json.loads(SESSION_FILE.read_text())
                log.info("Session loaded from ig_session.json")
            except Exception:
                pass

        if not session_data:
            raise RuntimeError(
                "\n\n❌ No Instagram session found!\n"
                "Run on your LOCAL Mac:\n"
                "  pip install playwright instagrapi\n"
                "  playwright install chromium\n"
                "  python src/save_session_browser.py\n"
                "Then add ig_session.json contents as IG_SESSION_DATA secret."
            )

        self.cl.set_settings(session_data)

        try:
            self.cl.login(IG_USERNAME, IG_PASSWORD)
            log.info("✅ Instagram session restored")
            self._save_session()
        except ChallengeRequired:
            raise RuntimeError(
                "\n\n❌ Session expired!\n"
                "Run save_session_browser.py again on your Mac\n"
                "and update the IG_SESSION_DATA secret."
            )
        except Exception as e:
            log.warning(f"Session reuse failed ({e}), trying sessionid...")
            try:
                session_id = session_data.get(
                    "authorization_data", {}
                ).get("sessionid", "")
                if session_id:
                    self.cl.login_by_sessionid(session_id)
                    log.info("✅ Logged in by session ID")
                    self._save_session()
                else:
                    raise RuntimeError("No session ID in saved session.")
            except Exception as e2:
                raise RuntimeError(
                    f"\n\n❌ All login methods failed: {e2}\n"
                    "Run save_session_browser.py again on your Mac."
                )

    def _save_session(self):
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps(self.cl.get_settings(), indent=2))

    def post_reel(self, video_path: Path, caption: str,
                  topic_key: str = "space") -> str:
        delay = random.uniform(5, 12)
        log.info(f"Waiting {delay:.1f}s before posting…")
        time.sleep(delay)

        # Pick a trending audio ID for this topic
        audio_ids = TRENDING_AUDIO.get(topic_key, [])
        audio_id  = random.choice(audio_ids) if audio_ids else None

        try:
            if audio_id:
                log.info(f"🎵 Using trending audio ID: {audio_id}")
                try:
                    media = self.cl.clip_upload(
                        path=str(video_path),
                        caption=caption,
                        extra_data={"audio_muted": False,
                                    "clips_audio_type": "licensed",
                                    "original_audio_info": {"audio_id": audio_id}},
                    )
                except Exception as audio_err:
                    log.warning(f"Trending audio failed ({audio_err}), posting without it")
                    media = self.cl.clip_upload(
                        path=str(video_path),
                        caption=caption,
                    )
            else:
                media = self.cl.clip_upload(
                    path=str(video_path),
                    caption=caption,
                )

            self._save_session()
            log.info(f"✅ Reel posted — media ID: {media.id}")
            return str(media.id)

        except LoginRequired:
            raise RuntimeError(
                "Session expired mid-run.\n"
                "Run save_session_browser.py on your Mac "
                "and update the IG_SESSION_DATA secret."
            )
        except Exception as e:
            log.error(f"Post failed: {e}")
            raise

    def post_carousel(self, image_paths: list, caption: str) -> str:
        """
        Post a carousel (album) post — multiple images users can swipe.
        image_paths: list of Path objects (JPG files, max 10)
        """
        import time
        delay = random.uniform(5, 10)
        log.info(f"Waiting {delay:.1f}s before posting carousel...")
        time.sleep(delay)

        try:
            # instagrapi album_upload for carousel posts
            media = self.cl.album_upload(
                paths=[str(p) for p in image_paths[:10]],
                caption=caption,
            )
            self._save_session()
            log.info(f"✅ Carousel posted — media ID: {media.id} ({len(image_paths)} slides)")
            return str(media.id)

        except LoginRequired:
            raise RuntimeError(
                "Session expired. Run save_session_browser.py again."
            )
        except Exception as e:
            log.error(f"Carousel post failed: {e}")
            raise
