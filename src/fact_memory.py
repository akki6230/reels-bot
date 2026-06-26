"""
src/fact_memory.py — Tracks all generated facts to prevent repetition.

Stores:
  - Last 50 hook lines per topic (exact text)
  - Last 20 categories used per topic
  - Last 10 image queries used per topic
  - Used fact fingerprints (hash of hook+body)

Persists in output/used_facts.json across runs via GitHub Actions cache.
"""

import json
import hashlib
import logging
from pathlib import Path

log = logging.getLogger(__name__)

ROOT            = Path(__file__).parent.parent
USED_FACTS_FILE = ROOT / "output" / "used_facts.json"


class FactMemory:
    def __init__(self):
        self._data = self._load()

    def _load(self) -> dict:
        if USED_FACTS_FILE.exists():
            try:
                return json.loads(USED_FACTS_FILE.read_text())
            except Exception:
                pass
        return {}

    def _save(self):
        USED_FACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        USED_FACTS_FILE.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False)
        )

    def _key(self, topic: str, field: str) -> str:
        return f"{topic}__{field}"

    def get_used_hooks(self, topic: str) -> list:
        return self._data.get(self._key(topic, "hooks"), [])

    def get_used_categories(self, topic: str) -> list:
        return self._data.get(self._key(topic, "categories"), [])

    def get_used_queries(self, topic: str) -> list:
        return self._data.get(self._key(topic, "queries"), [])

    def get_used_fingerprints(self, topic: str) -> list:
        return self._data.get(self._key(topic, "fingerprints"), [])

    def is_duplicate(self, topic: str, hook: str, body: str) -> bool:
        """Check if this fact is too similar to recent ones."""
        # Check fingerprint (exact duplicate)
        fp   = hashlib.md5(f"{hook}{body}".encode()).hexdigest()[:12]
        fps  = self.get_used_fingerprints(topic)
        if fp in fps:
            log.warning(f"Duplicate fingerprint detected: {hook[:40]}")
            return True

        # Check if hook is very similar to recent hooks (70%+ word overlap)
        hook_words = set(hook.lower().split())
        for old_hook in self.get_used_hooks(topic)[-20:]:
            old_words = set(old_hook.lower().split())
            if len(hook_words) > 0 and len(old_words) > 0:
                overlap = len(hook_words & old_words) / max(len(hook_words), len(old_words))
                if overlap > 0.70:
                    log.warning(f"Similar hook detected ({overlap:.0%} overlap): {hook[:40]}")
                    return True

        return False

    def next_episode(self, topic: str) -> int:
        """
        Return the next episode number for this topic's series and persist it.
        Series-based content ("रोज़ का GK #47") is the biggest lever for
        turning one-off viewers into followers — it gives people a reason to
        follow ("I want the next one"), not just watch once. The counter
        survives across runs via the same cached used_facts.json.
        """
        key = self._key(topic, "episode")
        n   = int(self._data.get(key, 0)) + 1
        self._data[key] = n
        self._save()
        return n

    def track(self, topic: str, hook: str, body: str,
              category: str = "", image_query: str = ""):
        """Record a used fact to prevent future repetition."""
        fp = hashlib.md5(f"{hook}{body}".encode()).hexdigest()[:12]

        def _append(key: str, value: str, max_size: int):
            if not value:
                return
            bucket = self._data.setdefault(key, [])
            if value not in bucket:
                bucket.append(value)
            self._data[key] = bucket[-max_size:]

        _append(self._key(topic, "hooks"),        hook,        50)
        _append(self._key(topic, "categories"),   category,    20)
        _append(self._key(topic, "queries"),      image_query, 15)
        _append(self._key(topic, "fingerprints"), fp,          100)

        self._save()
        log.info(f"📝 Tracked: [{topic}] {hook[:50]}")

    def get_avoid_context(self, topic: str) -> str:
        """Build a context string for Claude to avoid repetition."""
        hooks      = self.get_used_hooks(topic)[-10:]
        categories = self.get_used_categories(topic)[-8:]

        parts = []
        if hooks:
            parts.append(f"Recently used hooks (avoid similar):\n"
                         + "\n".join(f"- {h}" for h in hooks))
        if categories:
            parts.append(f"Recently used categories (pick different):\n"
                         + ", ".join(categories))

        return "\n\n".join(parts) if parts else ""
