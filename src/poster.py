"""
src/poster.py — Posts Instagram Reels using instagrapi with:
- Pre-saved session (no fresh login from GitHub Actions)
- Trending Instagram audio IDs per topic (fill in real IDs — see below)
- Auto first-comment to seed early engagement signal

NOTE ON COMMENT REPLIES: we deliberately do NOT auto-reply to viewer
comments here. Generic auto-replies to real people read as bot-like and
risk triggering the exact AI-content suppression we're trying to avoid.
Per the growth plan, replying to the first 5-10 comments is a manual,
~2-minute task — do it within the first hour of posting, it's the
single highest-leverage 2 minutes of your day for this account.
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
# IMPORTANT — these lists start EMPTY on purpose. Instagram audio IDs are not
# something that can be reliably invented; they have to be real, currently-
# trending track IDs. Research is consistent that using trending audio gives
# a real reach boost, so this is worth doing, just not worth faking.
#
# HOW TO FILL THIS IN (~5 min, once a week):
#   1. Open Instagram → Reels tab → find 2-3 trending Hindi/instrumental
#      audios that fit each topic's mood (calm for psychology/gk/examfacts,
#      energetic for mindblowing).
#   2. Tap the audio name → "Save audio" → note the audio ID from the URL,
#      OR use an already-posted reel of yours: inspect the media object via
#      instagrapi (self.cl.media_info(media_pk).clips_metadata) to read back
#      the original_audio_info.audio_id of any reel that used trending audio.
#   3. Paste 2-5 IDs per topic below. Rotate them out every 1-2 weeks —
#      trending audio has a short shelf life.
#
# If a topic's list is empty, post_reel() below automatically falls back to
# the generated/Freesound background music — nothing breaks either way.
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
                  topic_key: str = "space",
                  first_comment: str = "") -> str:
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

            # Seed early engagement: post a first comment immediately.
            # Instagram's "phase 1" test window (first ~60 min) weighs early
            # comments/replies heavily — an automated first comment that
            # restates the question/answer prompt gives real commenters
            # something to reply to, instead of the post sitting silent.
            if first_comment:
                try:
                    time.sleep(random.uniform(8, 20))
                    self.cl.media_comment(media.id, first_comment)
                    log.info(f"💬 First comment posted: {first_comment[:50]}")
                except Exception as ce:
                    log.warning(f"First comment failed (non-fatal): {ce}")

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
