"""
src/fact_gen.py — Generates content for all topics in English + Hindi.

- Fact topics (space, history, geography, science): pure Claude AI generation
- News topics (sports, worldnews): web search via Anthropic tool_use → Claude summarizes
- All content translated/generated in Hindi (Devanagari) separately
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

ROOT            = Path(__file__).parent.parent
USED_FACTS_FILE = ROOT / "output" / "used_facts.json"
IMAGES_DIR      = ROOT / "output" / "images"

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
PEXELS_API_KEY    = os.environ.get("PEXELS_API_KEY", "")

FALLBACK_KEYWORDS = {
    "space":     ["galaxy", "stars", "night sky", "nebula", "milky way"],
    "history":   ["ancient ruins", "castle", "museum", "monument"],
    "geography": ["mountain", "ocean", "forest", "landscape", "waterfall"],
    "science":   ["laboratory", "microscope", "technology", "research"],
    "sports":    ["cricket stadium", "football", "olympic stadium", "athlete"],
    "worldnews": ["world map", "globe", "news", "united nations", "space launch"],
}

SYSTEM_PROMPT_EN = """\
You are an expert educational content writer for Instagram Reels.
Facts must be 100% accurate, surprising, and understandable by a 15-year-old.
Always respond with valid JSON only — no markdown fences, no preamble.\
"""

SYSTEM_PROMPT_HI = """\
आप Instagram Reels के लिए एक विशेषज्ञ हिंदी शैक्षिक सामग्री लेखक हैं।
तथ्य 100% सटीक, आश्चर्यजनक और 15 साल के बच्चे को समझ आने वाले होने चाहिए।
केवल valid JSON में उत्तर दें — कोई markdown, कोई प्रस्तावना नहीं।\
"""

# ── English fact prompts ───────────────────────────────────────────────────────

FACT_PROMPTS_EN = {
    "space": """\
Generate one mind-blowing fact about space or the universe.
Return JSON:
{
  "hook": "Max 9 words. Punchy, curiosity-sparking, ALL CAPS ready.",
  "body": "2-3 sentences. Fascinating with a relatable analogy.",
  "caption": "Engaging Instagram caption ending with a question.",
  "fact_category": "Black Holes / Stars / Planets / Galaxies / Dark Matter / Moons / Cosmology"
}""",
    "history": """\
Generate one surprising lesser-known world history fact.
Return JSON:
{
  "hook": "Max 9 words. Sounds unbelievable but is true.",
  "body": "2-3 sentences. Include date, place, significance.",
  "caption": "Engaging Instagram caption ending with a question.",
  "fact_category": "Ancient Egypt / Roman Empire / World War / Medieval / Renaissance / Civilizations / Revolutions"
}""",
    "geography": """\
Generate one jaw-dropping geography fact about Earth, countries, or nature.
Return JSON:
{
  "hook": "Max 9 words. Include a striking number or claim.",
  "body": "2-3 sentences. Vivid geographical context.",
  "caption": "Engaging Instagram caption ending with a question.",
  "fact_category": "Mountains / Oceans / Rivers / Countries / Deserts / Forests / Islands / Volcanoes"
}""",
    "science": """\
Generate one astonishing science fact (biology, physics, chemistry, or human body).
Return JSON:
{
  "hook": "Max 9 words. Sounds impossible but is real.",
  "body": "2-3 sentences. Use an everyday analogy.",
  "caption": "Engaging Instagram caption ending with a question.",
  "fact_category": "Human Body / Physics / Chemistry / Biology / Neuroscience / Evolution / Genetics / Quantum"
}""",
}

# ── Hindi fact prompts ─────────────────────────────────────────────────────────

FACT_PROMPTS_HI = {
    "space": """\
अंतरिक्ष या ब्रह्मांड के बारे में एक अद्भुत तथ्य बनाएं।
JSON लौटाएं:
{
  "hook": "अधिकतम 8 शब्द। तुरंत जिज्ञासा जगाने वाला।",
  "body": "2-3 वाक्य। आसान भाषा में समझाएं, उदाहरण दें।",
  "caption": "Instagram caption जो सवाल पर खत्म हो।",
  "fact_category": "ब्लैक होल / तारे / ग्रह / आकाशगंगा / डार्क मैटर / चंद्रमा"
}""",
    "history": """\
विश्व इतिहास का एक आश्चर्यजनक और कम ज्ञात तथ्य बनाएं।
JSON लौटाएं:
{
  "hook": "अधिकतम 8 शब्द। अविश्वसनीय लगे पर सच हो।",
  "body": "2-3 वाक्य। तारीख, स्थान, महत्व के साथ।",
  "caption": "Instagram caption जो सवाल पर खत्म हो।",
  "fact_category": "प्राचीन मिस्र / रोमन साम्राज्य / विश्व युद्ध / मध्यकाल / सभ्यताएं"
}""",
    "geography": """\
पृथ्वी, देशों या प्रकृति के बारे में एक अद्भुत भूगोल तथ्य बनाएं।
JSON लौटाएं:
{
  "hook": "अधिकतम 8 शब्द। चौंका देने वाला आंकड़ा या दावा।",
  "body": "2-3 वाक्य। रोचक भौगोलिक संदर्भ के साथ।",
  "caption": "Instagram caption जो सवाल पर खत्म हो।",
  "fact_category": "पर्वत / महासागर / नदियां / देश / रेगिस्तान / जंगल / ज्वालामुखी"
}""",
    "science": """\
जीव विज्ञान, भौतिकी, रसायन या मानव शरीर का एक अद्भुत विज्ञान तथ्य बनाएं।
JSON लौटाएं:
{
  "hook": "अधिकतम 8 शब्द। असंभव लगे पर सच हो।",
  "body": "2-3 वाक्य। रोजमर्रा के उदाहरण से समझाएं।",
  "caption": "Instagram caption जो सवाल पर खत्म हो।",
  "fact_category": "मानव शरीर / भौतिकी / रसायन / जीव विज्ञान / तंत्रिका विज्ञान / विकास"
}""",
}

# ── News prompts (English) — used after web search results are injected ────────

NEWS_PROMPT_EN = """\
Based on these real news headlines and summaries:

{news_context}

Create an Instagram Reel about the most interesting/viral-worthy story.
Make it educational and engaging, NOT just a news bulletin.

Return JSON:
{{
  "hook": "Max 9 words. Shocking or surprising opener. ALL CAPS ready.",
  "body": "2-3 sentences. Explain what happened and why it matters. Keep it factual.",
  "caption": "Engaging Instagram caption with context, ending with a question.",
  "fact_category": "{category_hint}",
  "news_source": "Brief source description e.g. 'BBC Sports, June 2025'"
}}"""

NEWS_PROMPT_HI = """\
इन वास्तविक समाचार शीर्षकों और सारांशों के आधार पर:

{news_context}

सबसे दिलचस्प कहानी के बारे में एक Instagram Reel बनाएं।
इसे शैक्षिक और आकर्षक बनाएं — सिर्फ खबर नहीं।

JSON लौटाएं:
{{
  "hook": "अधिकतम 8 शब्द। चौंकाने वाली शुरुआत।",
  "body": "2-3 वाक्य। क्या हुआ और क्यों महत्वपूर्ण है — तथ्यात्मक रखें।",
  "caption": "Instagram caption जो सवाल पर खत्म हो।",
  "fact_category": "{category_hint}",
  "news_source": "संक्षिप्त स्रोत विवरण"
}}"""


class FactGenerator:
    def __init__(self):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self._used  = self._load_used()
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # ── Public ─────────────────────────────────────────────────────────────────

    def generate(self, topic_key: str, topic_config: dict, lang: str = "en") -> dict:
        """Generate content for a topic in the given language."""
        topic_type = topic_config.get("type", "fact")

        if topic_type == "news":
            return self._generate_news(topic_key, topic_config, lang)
        else:
            return self._generate_fact(topic_key, topic_config, lang)

    def fetch_image(self, keywords: list, topic_key: str) -> Path:
        """Fetch portrait image from Pexels with multiple keyword fallback."""
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        if PEXELS_API_KEY:
            all_kw = keywords + FALLBACK_KEYWORDS.get(topic_key, [])
            random.shuffle(all_kw)
            for kw in all_kw:
                slug = kw.replace(" ", "_")
                out  = IMAGES_DIR / f"{topic_key}_{slug}_{random.randint(1000,9999)}.jpg"
                result = self._fetch_pexels(kw, out)
                if result:
                    return result

        slug = keywords[0].replace(" ", "_")
        out  = IMAGES_DIR / f"{topic_key}_{slug}_gradient.jpg"
        return self._gradient_image(topic_key, out)

    # ── Fact generation ────────────────────────────────────────────────────────

    def _generate_fact(self, topic_key: str, topic_config: dict, lang: str) -> dict:
        prompts = FACT_PROMPTS_HI if lang == "hi" else FACT_PROMPTS_EN
        system  = SYSTEM_PROMPT_HI if lang == "hi" else SYSTEM_PROMPT_EN
        prompt  = prompts.get(topic_key, prompts.get("science"))

        # Avoid recently used categories
        recent = self._used.get(f"{topic_key}_{lang}", [])[-6:]
        if recent:
            avoid = ", ".join(f'"{c}"' for c in recent)
            avoid_note = f"\n\nIMPORTANT — avoid recently used: {avoid}" if lang == "en" \
                         else f"\n\nमहत्वपूर्ण — हाल ही में उपयोग किए गए विषय न दोहराएं: {avoid}"
            prompt += avoid_note

        msg = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        data = self._parse_json(msg.content[0].text)
        self._track(f"{topic_key}_{lang}", data.get("fact_category", ""))
        log.info(f"[{lang.upper()}] Fact: {data['hook'][:60]}")
        return data

    # ── News generation ────────────────────────────────────────────────────────

    def _generate_news(self, topic_key: str, topic_config: dict, lang: str) -> dict:
        """Search web for real news, then let Claude summarize into reel format."""
        queries       = topic_config.get("news_queries", [f"latest {topic_key} news today"])
        query         = random.choice(queries)
        category_hint = topic_config.get("name", topic_key)

        log.info(f"Searching news: '{query}'")
        news_context = self._web_search(query)

        if not news_context:
            log.warning("Web search returned nothing — falling back to AI knowledge")
            news_context = f"Generate a recent interesting {topic_key} story based on your knowledge."

        prompt_template = NEWS_PROMPT_HI if lang == "hi" else NEWS_PROMPT_EN
        system          = SYSTEM_PROMPT_HI if lang == "hi" else SYSTEM_PROMPT_EN
        prompt          = prompt_template.format(
            news_context=news_context,
            category_hint=category_hint,
        )

        msg  = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        data = self._parse_json(msg.content[0].text)
        self._track(f"{topic_key}_{lang}", data.get("fact_category", ""))
        log.info(f"[{lang.upper()}] News: {data['hook'][:60]}")
        return data

    def _web_search(self, query: str) -> str:
        """
        Call Anthropic API with web_search tool to get real news.
        Returns a plain-text summary of top results.
        """
        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{
                    "role": "user",
                    "content": (
                        f"Search for: {query}\n\n"
                        "Return a brief summary of the top 3 most interesting/recent results. "
                        "Include headline, key facts, and date if available. Plain text only."
                    ),
                }],
            )
            # Extract text from all content blocks
            parts = []
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    parts.append(block.text.strip())
            result = "\n\n".join(parts)
            log.info(f"Web search returned {len(result)} chars")
            return result[:2000]   # cap to avoid token overflow
        except Exception as e:
            log.warning(f"Web search failed: {e}")
            return ""

    # ── Image fetching ─────────────────────────────────────────────────────────

    def _fetch_pexels(self, keyword: str, out: Path) -> Path | None:
        try:
            resp = requests.get(
                "https://api.pexels.com/v1/search",
                params={"query": keyword, "orientation": "portrait",
                        "size": "large", "per_page": 15,
                        "page": random.randint(1, 3)},
                headers={"Authorization": PEXELS_API_KEY},
                timeout=15,
            )
            resp.raise_for_status()
            photos = resp.json().get("photos", [])
            if not photos:
                return None
            photo   = random.choice(photos)
            url     = photo["src"]["large2x"]
            out.write_bytes(requests.get(url, timeout=30).content)
            log.info(f"Pexels: {out.name} (by {photo['photographer']})")
            return out
        except Exception as e:
            log.warning(f"Pexels failed for '{keyword}': {e}")
            return None

    def _gradient_image(self, topic_key: str, path: Path) -> Path:
        from PIL import Image
        palettes = {
            "space":     [(5, 5, 25),    (15, 35, 80)],
            "history":   [(25, 15, 5),   (65, 40, 10)],
            "geography": [(5, 25, 10),   (10, 60, 30)],
            "science":   [(15, 5, 25),   (50, 20, 80)],
            "sports":    [(5, 15, 5),    (30, 60, 10)],
            "worldnews": [(25, 5, 5),    (70, 20, 10)],
        }
        c1, c2 = palettes.get(topic_key, [(10, 10, 30), (30, 30, 80)])
        W, H   = 1080, 1920
        img    = Image.new("RGB", (W, H))
        pix    = img.load()
        for y in range(H):
            t = y / H
            pix[y, 0]   # access check
            color = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
            for x in range(W):
                pix[x, y] = color
        img.save(path, "JPEG", quality=92)
        return path

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _parse_json(self, raw: str) -> dict:
        raw = re.sub(r"^```json\s*", "", raw.strip(), flags=re.MULTILINE)
        raw = re.sub(r"\s*```\s*$", "", raw, flags=re.MULTILINE)
        return json.loads(raw)

    def _load_used(self) -> dict:
        if USED_FACTS_FILE.exists():
            try:
                return json.loads(USED_FACTS_FILE.read_text())
            except Exception:
                pass
        return {}

    def _track(self, key: str, category: str):
        if not category:
            return
        bucket = self._used.setdefault(key, [])
        bucket.append(category)
        self._used[key] = bucket[-30:]
        USED_FACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        USED_FACTS_FILE.write_text(json.dumps(self._used, indent=2))
