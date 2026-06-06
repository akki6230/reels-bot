"""
src/fact_gen.py — Generates educational facts via Claude API.
Tracks previously used categories to ensure variety across runs.
"""

import os
import re
import json
import random
import logging
from pathlib import Path

import requests
from anthropic import Anthropic

log = logging.getLogger(__name__)

ROOT              = Path(__file__).parent.parent
USED_FACTS_FILE   = ROOT / "output" / "used_facts.json"
IMAGES_DIR        = ROOT / "output" / "images"

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
UNSPLASH_KEY      = os.environ.get("UNSPLASH_ACCESS_KEY", "")

SYSTEM_PROMPT = """\
You are an expert educational content writer for Instagram Reels.
Your facts must be:
- 100% scientifically/historically accurate
- Surprising enough to stop someone mid-scroll
- Written so a 15-year-old can understand
- Never repeated (check the avoid list carefully)
Always respond with valid JSON only — no markdown fences, no preamble.\
"""

TOPIC_PROMPTS = {
    "space": """\
Generate one mind-blowing fact about space or the universe.

Return JSON:
{
  "hook": "Max 9 words. All caps ready. Must create instant curiosity.",
  "body": "2-3 sentences. Fascinating explanation with a relatable analogy.",
  "caption": "Engaging Instagram caption. End with a question.",
  "fact_category": "One of: Black Holes / Stars / Planets / Galaxies / Dark Matter / Moons / Comets / Cosmology"
}""",

    "history": """\
Generate one surprising lesser-known world history fact.

Return JSON:
{
  "hook": "Max 9 words. All caps ready. Sounds unbelievable but is true.",
  "body": "2-3 sentences. Include date, place, significance.",
  "caption": "Engaging Instagram caption. End with a question.",
  "fact_category": "One of: Ancient Egypt / Roman Empire / World War / Medieval / Renaissance / Civilizations / Revolutions / Discoveries"
}""",

    "geography": """\
Generate one jaw-dropping geography fact about Earth, countries, or nature.

Return JSON:
{
  "hook": "Max 9 words. All caps ready. Include a striking number or claim.",
  "body": "2-3 sentences. Explain the geography with vivid context.",
  "caption": "Engaging Instagram caption. End with a question.",
  "fact_category": "One of: Mountains / Oceans / Rivers / Countries / Deserts / Forests / Islands / Volcanoes / Climate"
}""",

    "science": """\
Generate one astonishing science fact (biology, physics, chemistry, or human body).

Return JSON:
{
  "hook": "Max 9 words. All caps ready. Sounds impossible but is real.",
  "body": "2-3 sentences. Use an everyday analogy to explain.",
  "caption": "Engaging Instagram caption. End with a question.",
  "fact_category": "One of: Human Body / Physics / Chemistry / Biology / Neuroscience / Evolution / Genetics / Quantum"
}""",
}


class FactGenerator:
    def __init__(self):
        self.client     = Anthropic(api_key=ANTHROPIC_API_KEY)
        self._used      = self._load_used()
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # ── Public ─────────────────────────────────────────────────────────────────

    def generate(self, topic_key: str, topic_config: dict) -> dict:
        """Generate a unique fact, avoiding recently used categories."""
        base_prompt = TOPIC_PROMPTS[topic_key]

        recent = self._used.get(topic_key, [])[-6:]
        if recent:
            avoid_str = ", ".join(f'"{c}"' for c in recent)
            base_prompt += f"\n\nIMPORTANT — avoid these recently used categories: {avoid_str}"

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=700,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": base_prompt}],
        )

        raw  = message.content[0].text.strip()
        raw  = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
        raw  = re.sub(r"\s*```\s*$", "", raw, flags=re.MULTILINE)
        data = json.loads(raw)

        self._track(topic_key, data.get("fact_category", ""))
        return data

    def fetch_image(self, keywords: list[str], topic_key: str) -> Path:
        """Fetch a portrait image from Unsplash, or create a gradient fallback."""
        keyword = random.choice(keywords)
        slug    = keyword.replace(" ", "_")
        out     = IMAGES_DIR / f"{topic_key}_{slug}_{random.randint(1000,9999)}.jpg"

        if UNSPLASH_KEY:
            try:
                resp = requests.get(
                    "https://api.unsplash.com/photos/random",
                    params={"query": keyword, "orientation": "portrait", "content_filter": "high"},
                    headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
                    timeout=15,
                )
                resp.raise_for_status()
                url      = resp.json()["urls"]["regular"]   # ~1080px
                img_data = requests.get(url, timeout=30).content
                out.write_bytes(img_data)
                log.info(f"Unsplash image saved: {out.name}")
                return out
            except Exception as e:
                log.warning(f"Unsplash failed ({e}), using gradient fallback")

        return self._gradient_image(topic_key, out)

    # ── Private ────────────────────────────────────────────────────────────────

    def _gradient_image(self, topic_key: str, path: Path) -> Path:
        from PIL import Image
        palettes = {
            "space":     [(5, 5, 25),    (15, 35, 80)],
            "history":   [(25, 15, 5),   (65, 40, 10)],
            "geography": [(5, 25, 10),   (10, 60, 30)],
            "science":   [(15, 5, 25),   (50, 20, 80)],
        }
        c1, c2 = palettes.get(topic_key, [(10, 10, 30), (30, 30, 80)])
        W, H   = 1080, 1920
        img    = Image.new("RGB", (W, H))
        pix    = img.load()
        for y in range(H):
            t = y / H
            pix_color = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
            for x in range(W):
                pix[x, y] = pix_color
        img.save(path, "JPEG", quality=92)
        return path

    def _load_used(self) -> dict:
        if USED_FACTS_FILE.exists():
            try:
                return json.loads(USED_FACTS_FILE.read_text())
            except Exception:
                pass
        return {}

    def _track(self, topic_key: str, category: str):
        if not category:
            return
        bucket = self._used.setdefault(topic_key, [])
        bucket.append(category)
        self._used[topic_key] = bucket[-30:]   # keep last 30
        USED_FACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        USED_FACTS_FILE.write_text(json.dumps(self._used, indent=2))
