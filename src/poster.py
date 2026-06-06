"""
src/poster.py — Posts videos as Instagram Reels using Instagrapi.
Session is persisted in output/ig_session.json (committed back to repo or
stored in GitHub Secrets as IG_SESSION_DATA).
"""

import os
import json
import time
import random
import logging
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, BadPassword

log = logging.getLogger(__name__)

ROOT         = Path(__file__).parent.parent
SESSION_FILE = ROOT / "output" / "ig_session.json"

IG_USERNAME  = os.environ["INSTAGRAM_USERNAME"]
IG_PASSWORD  = os.environ["INSTAGRAM_PASSWORD"]
SESSION_ENV  = os.environ.get("IG_SESSION_DATA", "")   # base64 JSON from secret


class InstagramPoster:
    def __init__(self):
        self.cl = Client()
        self.cl.delay_range = [3, 7]
        self._login()

    def _login(self):
        # Try session from environment secret (GitHub Actions)
        if SESSION_ENV:
            try:
                settings = json.loads(SESSION_ENV)
                self.cl.set_settings(settings)
                self.cl.login(IG_USERNAME, IG_PASSWORD)
                log.info("✅ Logged in from env secret session")
                self._save_session()
                return
            except Exception as e:
                log.warning(f"Env session invalid ({e}), trying file…")

        # Try session from file (local dev)
        if SESSION_FILE.exists():
            try:
                settings = json.loads(SESSION_FILE.read_text())
                self.cl.set_settings(settings)
                self.cl.login(IG_USERNAME, IG_PASSWORD)
                log.info("✅ Logged in from file session")
                self._save_session()
                return
            except Exception as e:
                log.warning(f"File session invalid ({e}), fresh login…")

        # Fresh login
        self._fresh_login()

    def _fresh_login(self):
        try:
            self.cl.login(IG_USERNAME, IG_PASSWORD)
            self._save_session()
            log.info("✅ Fresh Instagram login successful")
        except ChallengeRequired:
            log.error(
                "❌ Instagram challenge required!\n"
                "   → Open Instagram app, approve the login, then re-run.\n"
                "   → Or disable 2FA temporarily for first login."
            )
            raise
        except BadPassword:
            log.error("❌ Wrong Instagram credentials — check INSTAGRAM_PASSWORD secret")
            raise

    def _save_session(self):
        """Save session to file so it can be committed back to the repo."""
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps(self.cl.get_settings(), indent=2))
        log.info(f"Session saved → {SESSION_FILE}")

    def post_reel(self, video_path: Path, caption: str) -> str:
        """Upload video as a Reel and return media ID."""
        delay = random.uniform(4, 10)
        log.info(f"Waiting {delay:.1f}s before posting…")
        time.sleep(delay)

        try:
            media = self.cl.clip_upload(path=str(video_path), caption=caption)
            self._save_session()   # refresh session after use
            log.info(f"✅ Posted reel — media ID: {media.id}")
            return str(media.id)
        except LoginRequired:
            log.warning("Session expired, re-logging in…")
            self._fresh_login()
            return self.post_reel(video_path, caption)
        except Exception as e:
            log.error(f"Post failed: {e}")
            raise
