"""
src/fact_gen.py — Generates + VERIFIES educational facts via Claude API.
Images: randomly rotates between Pollinations.ai, Pexels, and PIL illustrated.
"""

import os
import re
import json
import random
import logging
import urllib.parse
from pathlib import Path

import requests
from anthropic import Anthropic

log = logging.getLogger(__name__)

ROOT            = Path(__file__).parent.parent
USED_FACTS_FILE = ROOT / "output" / "used_facts.json"
IMAGES_DIR      = ROOT / "output" / "images"

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
PEXELS_API_KEY    = os.environ.get("PEXELS_API_KEY", "")

# ── Image source rotation weights ────────────────────────────────────────────
# (source_name, weight) — higher weight = more frequent
IMAGE_SOURCES = [
    ("pollinations", 40),   # AI-generated cartoon/anime/illustrated
    ("pexels",       35),   # Real photos
    ("pil",          25),   # Pure Python illustrated art
]

POLLINATIONS_STYLES = {
    "space":     ["cosmic digital art", "space anime art style", "galaxy illustration watercolor",
                  "nebula comic book style", "sci-fi concept art digital painting"],
    "history":   ["ancient civilization illustration", "historical comic book art",
                  "medieval fantasy painting", "archaeological watercolor art",
                  "ancient world digital painting"],
    "geography": ["nature landscape illustration", "cartoon world map art",
                  "geographic watercolor painting", "earth from space digital art",
                  "nature comic style illustration"],
    "science":   ["science lab cartoon illustration", "DNA molecule digital art",
                  "physics concept art colorful", "biology illustration comic style",
                  "futuristic science digital painting"],
    "sports":    ["sports action comic book art", "cricket illustration cartoon",
                  "football digital painting", "athlete comic style art",
                  "sports stadium illustration"],
    "worldnews": ["global news illustration art", "world politics comic style",
                  "breaking news digital art", "newspaper front page illustration",
                  "world events concept art"],
}

FALLBACK_KEYWORDS = {
    "space":     ["galaxy", "stars", "nebula", "milky way", "cosmos"],
    "history":   ["ancient ruins", "castle", "monument", "historical site"],
    "geography": ["mountain", "ocean", "forest", "waterfall", "landscape"],
    "science":   ["laboratory", "microscope", "technology", "research"],
    "sports":    ["cricket stadium", "football", "athlete", "sports arena"],
    "worldnews": ["world map", "globe", "united nations", "space launch"],
}

# ── PIL illustrated art color palettes per topic ───────────────────────────────
PIL_PALETTES = {
    "space":     {"bg": [(5,5,25),(15,20,60),(30,10,80)],   "stars": True,  "shapes": "circles"},
    "history":   {"bg": [(30,20,5),(60,40,10),(80,55,20)],  "stars": False, "shapes": "arches"},
    "geography": {"bg": [(5,25,10),(15,60,25),(8,40,15)],   "stars": False, "shapes": "waves"},
    "science":   {"bg": [(15,5,30),(35,10,65),(50,20,90)],  "stars": True,  "shapes": "grid"},
    "sports":    {"bg": [(8,20,4),(20,50,8),(30,70,15)],    "stars": False, "shapes": "lines"},
    "worldnews": [(25,5,5),(55,15,10),(70,20,12)],
}

SYSTEM_PROMPT_EN = """\
You are an expert educational content writer for Instagram Reels.
Facts must be 100% accurate, verifiable, and well-known scientifically/historically.
NEVER invent statistics or dates. Only state facts you are completely certain about.
Always respond with valid JSON only — no markdown fences, no preamble.\
"""

SYSTEM_PROMPT_HI = """\
आप Instagram Reels के लिए एक विशेषज्ञ हिंदी शैक्षिक सामग्री लेखक हैं।
तथ्य 100% सटीक और सत्यापित होने चाहिए। कभी भी काल्पनिक तथ्य न बनाएं।
केवल valid JSON में उत्तर दें।\
"""

VERIFICATION_PROMPT = """\
You are a fact-checker. Review this educational fact and verify it is 100% accurate.

Hook: {hook}
Body: {body}

Check:
1. Is the core claim factually correct?
2. Are any numbers/dates/statistics accurate?
3. Is anything misleading or exaggerated?

Respond in JSON only:
{{
  "is_accurate": true/false,
  "confidence": 0.0-1.0,
  "issue": "describe any problem or null if accurate",
  "corrected_body": "corrected version if needed, or null"
}}
"""

FACT_PROMPTS_EN = {
    "space": """\
Generate one mind-blowing but 100% verified space fact.
Only use facts you are absolutely certain about.
Return JSON:
{{
  "hook": "Max 9 words. Punchy, ALL CAPS ready.",
  "body": "2-3 sentences. Accurate with correct numbers/dates.",
  "caption": "Engaging Instagram caption ending with a question.",
  "fact_category": "Black Holes / Stars / Planets / Galaxies / Dark Matter / Moons / Cosmology"
}}""",
    "history": """\
Generate one surprising but 100% verified world history fact.
Only use well-documented historical events.
Return JSON:
{{
  "hook": "Max 9 words. Surprising but true.",
  "body": "2-3 sentences. Include verified date, place, significance.",
  "caption": "Engaging Instagram caption ending with a question.",
  "fact_category": "Ancient Egypt / Roman Empire / World War / Medieval / Renaissance / Civilizations"
}}""",
    "geography": """\
Generate one jaw-dropping but 100% verified geography fact.
Only use accurate geographical statistics.
Return JSON:
{{
  "hook": "Max 9 words. Include a verified striking number.",
  "body": "2-3 sentences. Accurate geographical context.",
  "caption": "Engaging Instagram caption ending with a question.",
  "fact_category": "Mountains / Oceans / Rivers / Countries / Deserts / Forests / Islands"
}}""",
    "science": """\
Generate one astonishing but 100% verified science fact.
Only use established scientific knowledge.
Return JSON:
{{
  "hook": "Max 9 words. Sounds impossible but is proven.",
  "body": "2-3 sentences. Use accurate scientific explanation.",
  "caption": "Engaging Instagram caption ending with a question.",
  "fact_category": "Human Body / Physics / Chemistry / Biology / Neuroscience / Evolution"
}}""",
}

FACT_PROMPTS_HI = {
    "space": """\
अंतरिक्ष के बारे में एक 100% सत्यापित तथ्य बनाएं।
JSON लौटाएं:
{{
  "hook": "अधिकतम 8 शब्द। तुरंत जिज्ञासा जगाने वाला।",
  "body": "2-3 वाक्य। सटीक तथ्य, सही संख्या/तारीख के साथ।",
  "caption": "Instagram caption जो सवाल पर खत्म हो।",
  "fact_category": "ब्लैक होल / तारे / ग्रह / आकाशगंगा / चंद्रमा"
}}""",
    "history": """\
विश्व इतिहास का एक 100% सत्यापित तथ्य बनाएं।
JSON लौटाएं:
{{
  "hook": "अधिकतम 8 शब्द। अविश्वसनीय पर सच।",
  "body": "2-3 वाक्य। सत्यापित तारीख और स्थान के साथ।",
  "caption": "Instagram caption जो सवाल पर खत्म हो।",
  "fact_category": "प्राचीन / रोमन / विश्व युद्ध / मध्यकाल / सभ्यताएं"
}}""",
    "geography": """\
भूगोल का एक 100% सत्यापित तथ्य बनाएं।
JSON लौटाएं:
{{
  "hook": "अधिकतम 8 शब्द। सटीक आंकड़े के साथ।",
  "body": "2-3 वाक्य। सत्यापित भौगोलिक जानकारी।",
  "caption": "Instagram caption जो सवाल पर खत्म हो।",
  "fact_category": "पर्वत / महासागर / नदियां / देश / रेगिस्तान"
}}""",
    "science": """\
विज्ञान का एक 100% सत्यापित तथ्य बनाएं।
JSON लौटाएं:
{{
  "hook": "अधिकतम 8 शब्द। सिद्ध वैज्ञानिक तथ्य।",
  "body": "2-3 वाक्य। सटीक वैज्ञानिक व्याख्या।",
  "caption": "Instagram caption जो सवाल पर खत्म हो।",
  "fact_category": "मानव शरीर / भौतिकी / रसायन / जीव विज्ञान"
}}""",
}

NEWS_PROMPT_EN = """\
Based on these real news headlines:
{news_context}

Create an Instagram Reel about the most interesting story.
Only include information that appears in the news context — do NOT add facts.

Return JSON:
{{
  "hook": "Max 9 words. Factual, not sensational.",
  "body": "2-3 sentences. Only facts from the news context.",
  "caption": "Engaging caption ending with a question.",
  "fact_category": "{category_hint}",
  "news_source": "Brief source description"
}}"""

NEWS_PROMPT_HI = """\
इन वास्तविक समाचार शीर्षकों के आधार पर:
{news_context}

एक Instagram Reel बनाएं। केवल समाचार से प्राप्त जानकारी शामिल करें।

Return JSON:
{{
  "hook": "अधिकतम 8 शब्द। तथ्यात्मक।",
  "body": "2-3 वाक्य। केवल समाचार के तथ्य।",
  "caption": "Instagram caption जो सवाल पर खत्म हो।",
  "fact_category": "{category_hint}",
  "news_source": "संक्षिप्त स्रोत"
}}"""


class FactGenerator:
    def __init__(self):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self._used  = self._load_used()
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # ── Public ─────────────────────────────────────────────────────────────────

    def generate(self, topic_key: str, topic_config: dict,
                 lang: str = "en") -> dict:
        """Generate + verify content."""
        topic_type = topic_config.get("type", "fact")
        if topic_type == "news":
            return self._generate_news(topic_key, topic_config, lang)
        return self._generate_fact(topic_key, topic_config, lang)

    def fetch_image(self, keywords: list, topic_key: str) -> tuple:
        """
        Randomly pick image source and fetch image.
        Returns (image_path, source_name, duration_hint)
        source_name: 'pollinations' | 'pexels' | 'pil'
        duration_hint: 20 for pexels, 30-45 for others
        """
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        # Weighted random source selection
        sources, weights = zip(*IMAGE_SOURCES)
        source = random.choices(sources, weights=weights, k=1)[0]

        if source == "pollinations":
            result = self._fetch_pollinations(topic_key)
            if result:
                return result, "pollinations", random.randint(30, 45)

        if source == "pexels" and PEXELS_API_KEY:
            result = self._fetch_pexels_image(keywords, topic_key)
            if result:
                return result, "pexels", 20

        # PIL illustrated (always works as fallback)
        result = self._create_pil_art(topic_key)
        return result, "pil", random.randint(30, 45)

    # ── Fact generation ────────────────────────────────────────────────────────

    def _generate_fact(self, topic_key: str, topic_config: dict,
                       lang: str) -> dict:
        prompts = FACT_PROMPTS_HI if lang == "hi" else FACT_PROMPTS_EN
        system  = SYSTEM_PROMPT_HI if lang == "hi" else SYSTEM_PROMPT_EN
        prompt  = prompts.get(topic_key, prompts.get("science", ""))

        recent = self._used.get(f"{topic_key}_{lang}", [])[-6:]
        if recent:
            avoid = ", ".join(f'"{c}"' for c in recent)
            prompt += f"\n\nAvoid recently used categories: {avoid}"

        # Generate
        msg  = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        data = self._parse_json(msg.content[0].text)
        log.info(f"[{lang.upper()}] Generated: {data['hook'][:60]}")

        # Verify (English facts only for speed — Hindi is translated from same base)
        if lang == "en" and topic_key in FACT_PROMPTS_EN:
            data = self._verify_fact(data)

        self._track(f"{topic_key}_{lang}", data.get("fact_category", ""))
        return data

    def _verify_fact(self, data: dict, max_retries: int = 2) -> dict:
        """Verify fact accuracy with a second Claude call. Retry if inaccurate."""
        for attempt in range(max_retries + 1):
            prompt = VERIFICATION_PROMPT.format(
                hook=data["hook"], body=data["body"]
            )
            try:
                msg = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=400,
                    system="You are a strict fact-checker. Respond only in JSON.",
                    messages=[{"role": "user", "content": prompt}],
                )
                result = self._parse_json(msg.content[0].text)

                if result.get("is_accurate") and result.get("confidence", 0) >= 0.85:
                    log.info(f"✅ Fact verified (confidence: {result['confidence']:.2f})")
                    # Apply correction if provided
                    if result.get("corrected_body"):
                        data["body"] = result["corrected_body"]
                    return data
                else:
                    log.warning(f"⚠️ Fact issue: {result.get('issue')} — regenerating...")
                    if attempt < max_retries:
                        # Regenerate with issue context
                        regen_prompt = (
                            f"The previous fact had this issue: {result.get('issue')}\n"
                            f"Generate a DIFFERENT, 100% accurate fact.\n"
                            + list(FACT_PROMPTS_EN.values())[0]
                        )
                        msg2 = self.client.messages.create(
                            model="claude-haiku-4-5-20251001",
                            max_tokens=800,
                            system=SYSTEM_PROMPT_EN,
                            messages=[{"role": "user", "content": regen_prompt}],
                        )
                        data = self._parse_json(msg2.content[0].text)
            except Exception as e:
                log.warning(f"Verification failed: {e}")
                break

        return data  # Return best attempt

    # ── News generation ────────────────────────────────────────────────────────

    def _generate_news(self, topic_key: str, topic_config: dict,
                       lang: str) -> dict:
        queries      = topic_config.get("news_queries", [f"latest {topic_key} news"])
        query        = random.choice(queries)
        cat_hint     = topic_config.get("name", topic_key)
        news_context = self._web_search(query)

        if not news_context:
            # Fallback to fact generation
            log.warning("No news found, falling back to fact generation")
            fact_topics = {"sports": "science", "worldnews": "space"}
            fallback    = fact_topics.get(topic_key, "science")
            return self._generate_fact(fallback, {}, lang)

        template = NEWS_PROMPT_HI if lang == "hi" else NEWS_PROMPT_EN
        system   = SYSTEM_PROMPT_HI if lang == "hi" else SYSTEM_PROMPT_EN
        prompt   = template.format(
            news_context=news_context[:1500],
            category_hint=cat_hint,
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
        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{
                    "role": "user",
                    "content": (
                        f"Search for: {query}\n\n"
                        "Return a brief summary of the top 3 most recent results. "
                        "Include headline, key facts, and date. Plain text only."
                    ),
                }],
            )
            parts = [b.text.strip() for b in response.content
                     if hasattr(b, "text") and b.text]
            return "\n\n".join(parts)[:2000]
        except Exception as e:
            log.warning(f"Web search failed: {e}")
            return ""

    # ── Image sources ──────────────────────────────────────────────────────────

    def _fetch_pollinations(self, topic_key: str) -> Path | None:
        """Fetch AI-generated illustrated image from Pollinations.ai (free, no key)."""
        try:
            styles = POLLINATIONS_STYLES.get(topic_key, ["digital illustration art"])
            style  = random.choice(styles)
            prompt = urllib.parse.quote(
                f"{style}, high quality, detailed, vibrant colors, "
                f"9:16 aspect ratio, vertical format"
            )
            # Pollinations.ai free image generation
            url  = f"https://image.pollinations.ai/prompt/{prompt}?width=1080&height=1920&nologo=true&seed={random.randint(1,9999)}"
            resp = requests.get(url, timeout=45)
            resp.raise_for_status()

            if len(resp.content) < 5000:
                return None

            slug = style.replace(" ", "_")[:30]
            out  = IMAGES_DIR / f"{topic_key}_pollinations_{slug}_{random.randint(1000,9999)}.jpg"
            out.write_bytes(resp.content)
            log.info(f"Pollinations image: {out.name} ({len(resp.content)//1024}KB)")
            return out
        except Exception as e:
            log.warning(f"Pollinations failed: {e}")
            return None

    def _fetch_pexels_image(self, keywords: list, topic_key: str) -> Path | None:
        """Fetch portrait photo from Pexels."""
        all_kw = keywords + FALLBACK_KEYWORDS.get(topic_key, [])
        random.shuffle(all_kw)
        for kw in all_kw:
            try:
                resp = requests.get(
                    "https://api.pexels.com/v1/search",
                    params={"query": kw, "orientation": "portrait",
                            "size": "large", "per_page": 15,
                            "page": random.randint(1, 3)},
                    headers={"Authorization": PEXELS_API_KEY},
                    timeout=15,
                )
                resp.raise_for_status()
                photos = resp.json().get("photos", [])
                if not photos:
                    continue
                photo   = random.choice(photos)
                url     = photo["src"]["large2x"]
                out     = IMAGES_DIR / f"{topic_key}_pexels_{kw.replace(' ','_')}_{random.randint(1000,9999)}.jpg"
                out.write_bytes(requests.get(url, timeout=30).content)
                log.info(f"Pexels: {out.name}")
                return out
            except Exception as e:
                log.warning(f"Pexels '{kw}': {e}")
        return None

    def _create_pil_art(self, topic_key: str) -> Path:
        """Create rich illustrated artwork using PIL."""
        from PIL import Image, ImageDraw
        import math

        palette = PIL_PALETTES.get(topic_key, {"bg": [(10,10,30),(30,30,80)], "stars": True, "shapes": "circles"})
        if isinstance(palette, list):
            palette = {"bg": palette, "stars": False, "shapes": "lines"}

        bg_colors = palette["bg"]
        out = IMAGES_DIR / f"{topic_key}_pil_{random.randint(1000,9999)}.jpg"

        img  = Image.new("RGB", (1080, 1920))
        draw = ImageDraw.Draw(img)
        pix  = img.load()

        # Multi-stop gradient background
        n = len(bg_colors)
        for y in range(1920):
            fy  = y / 1920
            idx = fy * (n - 1)
            i   = min(int(idx), n - 2)
            fr  = idx - i
            c1, c2 = bg_colors[i], bg_colors[i+1]
            r = int(c1[0] + (c2[0]-c1[0]) * fr)
            g = int(c1[1] + (c2[1]-c1[1]) * fr)
            b = int(c1[2] + (c2[2]-c1[2]) * fr)
            for x in range(1080):
                pix[x, y] = (r, g, b)

        acc = {
            "space":     (100, 180, 255),
            "history":   (210, 170, 80),
            "geography": (75,  215, 125),
            "science":   (180, 100, 255),
            "sports":    (255, 200, 40),
            "worldnews": (255, 80, 70),
        }.get(topic_key, (100, 180, 255))

        shapes = palette.get("shapes", "circles")
        rng    = random.Random(hash(topic_key) % 1000)

        if shapes == "circles":
            # Concentric glowing rings
            for r in range(80, 600, 60):
                a = max(0, min(255, int(120 * (1 - r/600))))
                draw.arc([540-r, 700-r, 540+r, 700+r],
                         start=rng.randint(0,360),
                         end=rng.randint(180,360),
                         fill=(*acc, a), width=2)
            # Scatter circles
            for _ in range(25):
                cx = rng.randint(100, 980)
                cy = rng.randint(100, 1820)
                r2 = rng.randint(20, 120)
                a2 = rng.randint(20, 60)
                draw.ellipse([cx-r2,cy-r2,cx+r2,cy+r2],
                             outline=(*acc, a2), width=1)

        elif shapes == "arches":
            for i in range(8):
                y0 = 200 + i * 220
                draw.arc([80, y0, 1000, y0+300],
                         start=180, end=360,
                         fill=(*acc, 40), width=2)

        elif shapes == "waves":
            for wave_i in range(12):
                y_base = wave_i * 170
                pts    = []
                for x in range(0, 1081, 15):
                    y2 = y_base + int(80 * math.sin(x * 0.015 + wave_i))
                    pts.append((x, y2))
                if len(pts) >= 2:
                    draw.line(pts, fill=(*acc, 35), width=2)

        elif shapes == "grid":
            for x in range(0, 1080, 90):
                draw.rectangle([x, 0, x+1, 1920], fill=(*acc, 18))
            for y in range(0, 1920, 90):
                draw.rectangle([0, y, 1080, y+1], fill=(*acc, 18))
            # Glowing nodes at intersections
            for x in range(0, 1080, 180):
                for y in range(0, 1920, 180):
                    draw.ellipse([x-4, y-4, x+4, y+4], fill=(*acc, 60))

        elif shapes == "lines":
            for _ in range(20):
                x1 = rng.randint(0, 1080)
                draw.line([(x1, 0), (x1 + rng.randint(-100,100), 1920)],
                          fill=(*acc, 25), width=1)

        # Stars if applicable
        if palette.get("stars"):
            for _ in range(200):
                sx = rng.randint(0, 1080)
                sy = rng.randint(0, 1920)
                ss = rng.randint(1, 3)
                sa = rng.randint(100, 220)
                draw.ellipse([sx-ss, sy-ss, sx+ss, sy+ss],
                             fill=(255, 255, 255, sa))

        # Vignette
        for r2 in range(0, min(540, 960), 15):
            fade = int(80 * (1 - r2/min(540,960)) ** 2)
            draw.rectangle([r2, r2, 1080-r2, 1920-r2],
                           outline=(0, 0, 0, fade), width=15)

        img.save(out, "JPEG", quality=94)
        log.info(f"PIL art: {out.name}")
        return out

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
