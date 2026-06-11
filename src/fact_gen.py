"""
src/fact_gen.py — Hindi-only fact generation for 5 viral topics.
Includes fact verification + multi-source image fetching.
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

# Image source weights
IMAGE_SOURCES = [("pollinations", 40), ("pexels", 35), ("pil", 25)]

POLLINATIONS_STYLES = {
    "psychology":   ["human brain colorful digital art", "psychology mind explosion art",
                     "neural network illustration colorful", "mind concept surreal art"],
    "mindblowing":  ["mind blown surreal explosion art", "shocking fact visual art",
                     "amazing universe concept digital", "wow factor colorful art"],
    "space":        ["galaxy nebula anime art style", "cosmic space digital painting",
                     "universe illustration watercolor", "sci-fi space concept art"],
    "sciencewrong": ["mad scientist cartoon colorful", "science experiment gone wrong art",
                     "chemistry explosion illustration", "funny science fail digital art"],
    "earthglitch":  ["earth glitch digital art surreal", "mysterious nature phenomenon art",
                     "planet earth anomaly illustration", "earth crack surreal concept"],
}

FALLBACK_KEYWORDS = {
    "psychology":   ["brain", "mind", "psychology", "thinking", "human mind"],
    "mindblowing":  ["explosion", "surreal", "amazing", "shock", "wow"],
    "space":        ["galaxy", "nebula", "stars", "cosmos", "universe"],
    "sciencewrong": ["laboratory", "chemistry", "experiment", "science"],
    "earthglitch":  ["earth", "nature", "landscape", "mysterious", "planet"],
}

PIL_PALETTES = {
    "psychology":   {"bg": [(8,4,20),(20,10,50),(35,15,80)],   "stars": True,  "shapes": "circles"},
    "mindblowing":  {"bg": [(20,5,5),(55,15,10),(80,25,15)],   "stars": False, "shapes": "lines"},
    "space":        {"bg": [(4,6,22),(8,15,45),(12,22,65)],    "stars": True,  "shapes": "circles"},
    "sciencewrong": {"bg": [(5,18,5),(12,45,15),(20,70,25)],   "stars": False, "shapes": "grid"},
    "earthglitch":  {"bg": [(4,14,8),(10,35,18),(16,55,28)],   "stars": False, "shapes": "waves"},
}

SYSTEM_PROMPT = """\
आप Instagram Reels के लिए एक विशेषज्ञ हिंदी वायरल कंटेंट लेखक हैं।
तथ्य 100% सटीक, सत्यापित और चौंकाने वाले होने चाहिए।
पहले 2 सेकंड में scroll रोकने वाला hook चाहिए।
केवल valid JSON में उत्तर दें — कोई markdown नहीं।\
"""

TOPIC_PROMPTS = {
    "psychology": """\
एक 100% सत्यापित मनोविज्ञान तथ्य बनाएं जो लोगों का दिमाग हिला दे।
मानव व्यवहार, दिमाग की शक्ति, या मनोवैज्ञानिक घटनाओं के बारे में।

JSON लौटाएं:
{{
  "hook": "अधिकतम 8 शब्द। पहले 2 सेकंड में scroll रोकने वाला।",
  "body": "2-3 वाक्य। सिद्ध मनोवैज्ञानिक तथ्य, आसान भाषा में।",
  "caption": "Caption जो comment करने पर मजबूर करे। सवाल से खत्म हो।",
  "fact_category": "Memory / Behavior / Emotions / Perception / Social Psychology"
}}""",

    "mindblowing": """\
एक 100% सत्यापित ऐसा तथ्य बनाएं जो सुनकर लोग 'ये कैसे हो सकता है?' कहें।
विज्ञान, इतिहास, प्रकृति, या ब्रह्मांड से — जो सबसे shocking हो।

JSON लौटाएं:
{{
  "hook": "अधिकतम 8 शब्द। इतना shocking कि scroll रुक जाए।",
  "body": "2-3 वाक्य। तथ्य + क्यों/कैसे की व्याख्या।",
  "caption": "Caption जो share करने पर मजबूर करे।",
  "fact_category": "Universe / Biology / Physics / History / Nature"
}}""",

    "space": """\
एक 100% सत्यापित अंतरिक्ष या ब्रह्मांड का तथ्य बनाएं।
ऐसा जो सुनकर लगे — ये दुनिया कितनी बड़ी है।

JSON लौटाएं:
{{
  "hook": "अधिकतम 8 शब्द। ब्रह्मांड की विशालता या रहस्य दिखाए।",
  "body": "2-3 वाक्य। सटीक संख्या/तारीख के साथ।",
  "caption": "Caption जो अंतरिक्ष प्रेमियों को comment करने दे।",
  "fact_category": "Black Holes / Stars / Planets / Galaxies / Dark Matter / ISRO / NASA"
}}""",

    "sciencewrong": """\
एक 100% सत्यापित ऐसा तथ्य बनाएं जहाँ विज्ञान ने गलती की, या कोई प्रयोग बुरी तरह fail हुआ।
असली historical science fails, wrong theories, या funny experiments।

JSON लौटाएं:
{{
  "hook": "अधिकतम 8 शब्द। 'वैज्ञानिकों ने सोचा था...' style।",
  "body": "2-3 वाक्य। क्या गलत हुआ, कब हुआ, नतीजा क्या निकला।",
  "caption": "Caption जो लोगों को 'और बताओ' कहने दे।",
  "fact_category": "Failed Experiments / Wrong Theories / Science Disasters / Funny Science"
}}""",

    "earthglitch": """\
एक 100% सत्यापित ऐसी घटना बताएं जो धरती पर होती है और लगती है जैसे simulation में glitch आ गया।
जैसे: अजीब प्राकृतिक घटनाएं, unexplained phenomena, या धरती के रहस्य।

JSON लौटाएं:
{{
  "hook": "अधिकतम 8 शब्द। 'धरती पर ऐसा भी होता है?' style।",
  "body": "2-3 वाक्य। क्या होता है, कहाँ होता है, क्यों होता है।",
  "caption": "Caption जो लोगों को हैरान करे।",
  "fact_category": "Natural Phenomena / Earth Mysteries / Weather Anomalies / Geographic Wonders"
}}""",

    "gk": """\
एक 100% सत्यापित सामान्य ज्ञान का तथ्य बनाएं।
भारत, विश्व इतिहास, भूगोल, विज्ञान, खेल, या संस्कृति से।
ऐसा जो लोग share करें और दोस्तों को बताएं।

JSON लौटाएं:
{{
  "hook": "अधिकतम 8 शब्द। चौंकाने वाला सामान्य ज्ञान।",
  "body": "2-3 वाक्य। सटीक तथ्य + रोचक संदर्भ।",
  "caption": "Caption जो quiz style हो। 'क्या आप जानते थे?' से खत्म हो।",
  "fact_category": "India / World History / Geography / Science / Sports / Culture"
}}""",

    "examfacts": """\
एक specific competitive exam के लिए एक important question/fact बनाएं।
इनमें से किसी एक exam को target करें: UPSC, SSC CGL, NEET, IIT JEE।
exam_type में ONLY वही exam लिखें जिससे यह question directly related हो।
Question style में hook, clear answer body में।

JSON लौटाएं:
{{
  "hook": "अधिकतम 8 शब्द। Question format — जैसे 'भारत का सबसे लंबा बांध कौन सा है?'",
  "body": "Answer पहले लिखें। फिर 1-2 sentences explanation। 100% accurate facts।",
  "caption": "Caption जो students share और save करें। Comment में guess करने को कहें।",
  "fact_category": "History / Geography / Polity / Economy / Biology / Physics / Chemistry / Maths",
  "exam_type": "UPSC या SSC CGL या NEET या IIT JEE — सिर्फ एक exact exam"
}}""",
}

VERIFICATION_PROMPT = """\
इस हिंदी तथ्य की सत्यता जाँचें:

Hook: {hook}
Body: {body}

जाँचें:
1. क्या मुख्य दावा सही है?
2. क्या संख्या/तारीख सही है?
3. क्या कुछ भ्रामक है?

केवल JSON में उत्तर दें:
{{
  "is_accurate": true/false,
  "confidence": 0.0-1.0,
  "issue": "समस्या बताएं या null",
  "corrected_body": "सुधरा हुआ version या null"
}}"""


class FactGenerator:
    def __init__(self):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        from fact_memory import FactMemory
        self.memory    = FactMemory()
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    def generate(self, topic_key: str, topic_config: dict,
                 lang: str = "hi") -> dict:

        prompt = TOPIC_PROMPTS.get(topic_key, TOPIC_PROMPTS["mindblowing"])

        # Add memory context — tell Claude what to avoid
        avoid_ctx = self.memory.get_avoid_context(topic_key)
        if avoid_ctx:
            prompt += f"\n\n---\n{avoid_ctx}\n---\n\nBe creative and different from the above."

        max_attempts = 3
        for attempt in range(max_attempts):
            msg  = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=700,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            data = self._parse_json(msg.content[0].text)
            log.info(f"Generated (attempt {attempt+1}): {data['hook'][:60]}")

            # Check for duplicate
            if self.memory.is_duplicate(topic_key, data["hook"], data["body"]):
                log.warning(f"Duplicate detected — regenerating ({attempt+1}/{max_attempts})")
                prompt += f"\n\nThis hook was too similar to recent ones: '{data['hook']}'\nGenerate something completely different."
                continue

            # Verify accuracy
            data = self._verify(data)

            # Track in memory
            self.memory.track(
                topic    = topic_key,
                hook     = data["hook"],
                body     = data["body"],
                category = data.get("fact_category", ""),
            )
            return data

        # After max attempts, return last generated (at least different category)
        log.warning("Max uniqueness attempts reached — using last generated")
        self.memory.track(topic_key, data["hook"], data["body"],
                          data.get("fact_category",""))
        return data

    def _verify(self, data: dict) -> dict:
        for attempt in range(2):
            try:
                prompt = VERIFICATION_PROMPT.format(
                    hook=data["hook"], body=data["body"]
                )
                msg = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=300,
                    system="आप एक strict fact-checker हैं। केवल JSON में उत्तर दें।",
                    messages=[{"role": "user", "content": prompt}],
                )
                result = self._parse_json(msg.content[0].text)
                if result.get("is_accurate") and result.get("confidence", 0) >= 0.82:
                    log.info(f"✅ Verified (confidence: {result['confidence']:.2f})")
                    if result.get("corrected_body"):
                        data["body"] = result["corrected_body"]
                    return data
                else:
                    log.warning(f"⚠️ Fact issue: {result.get('issue')} — regenerating...")
                    if attempt == 0:
                        msg2 = self.client.messages.create(
                            model="claude-haiku-4-5-20251001",
                            max_tokens=700,
                            system=SYSTEM_PROMPT,
                            messages=[{"role": "user", "content":
                                f"पिछले तथ्य में यह समस्या थी: {result.get('issue')}\n"
                                f"एक अलग, 100% सटीक तथ्य बनाएं।\n"
                                + list(TOPIC_PROMPTS.values())[0]}],
                        )
                        data = self._parse_json(msg2.content[0].text)
            except Exception as e:
                log.warning(f"Verification failed: {e}")
                break
        return data

    def fetch_image(self, keywords: list, topic_key: str) -> tuple:
        """Returns (image_path, source_name, duration_hint)."""
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        sources, weights = zip(*IMAGE_SOURCES)
        source = random.choices(sources, weights=weights, k=1)[0]

        if source == "pollinations":
            result = self._pollinations(topic_key)
            if result:
                return result, "pollinations", random.randint(15, 20)

        if source == "pexels" and PEXELS_API_KEY:
            result = self._pexels(keywords, topic_key)
            if result:
                return result, "pexels", random.randint(10, 20)

        result = self._pil_art(topic_key)
        return result, "pil", random.randint(10, 20)

    def _pollinations(self, topic_key: str) -> Path | None:
        try:
            style  = random.choice(POLLINATIONS_STYLES.get(topic_key, ["colorful digital art"]))
            prompt = urllib.parse.quote(f"{style}, vibrant colors, vertical portrait")
            seed   = random.randint(1, 99999)
            url    = (f"https://image.pollinations.ai/prompt/{prompt}"
                      f"?width=512&height=912&nologo=true&seed={seed}&model=flux")
            resp   = requests.get(url, timeout=45)
            resp.raise_for_status()
            if len(resp.content) < 5000:
                return None
            from PIL import Image as PI
            import io
            img = PI.open(io.BytesIO(resp.content)).convert("RGB")
            img = img.resize((1080, 1920), PI.LANCZOS)
            out = IMAGES_DIR / f"{topic_key}_poll_{seed}.jpg"
            img.save(out, "JPEG", quality=92)
            log.info(f"Pollinations: {out.name}")
            return out
        except Exception as e:
            log.warning(f"Pollinations: {e}")
            return None

    def _pexels(self, keywords: list, topic_key: str) -> Path | None:
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
                photo = random.choice(photos)
                out   = IMAGES_DIR / f"{topic_key}_pexels_{random.randint(1000,9999)}.jpg"
                out.write_bytes(requests.get(photo["src"]["large2x"], timeout=30).content)
                log.info(f"Pexels: {out.name}")
                return out
            except Exception:
                continue
        return None

    def _pil_art(self, topic_key: str) -> Path:
        from PIL import Image, ImageDraw
        import math
        pal = PIL_PALETTES.get(topic_key, {"bg": [(5,5,25),(20,20,60)], "stars": True, "shapes": "circles"})
        acc = {
            "psychology":  (160, 100, 255),
            "mindblowing": (255,  80,  50),
            "space":       (100, 185, 255),
            "sciencewrong":(80,  230, 120),
            "earthglitch": (70,  215, 130),
        }.get(topic_key, (120, 180, 255))
        out  = IMAGES_DIR / f"{topic_key}_pil_{random.randint(1000,9999)}.jpg"
        img  = Image.new("RGB", (1080, 1920))
        draw = ImageDraw.Draw(img)
        pix  = img.load()
        cols = pal["bg"]
        n    = len(cols)
        for y in range(1920):
            fy=y/1920; idx=fy*(n-1); i=min(int(idx),n-2); fr=idx-i
            c1,c2=cols[i],cols[i+1]
            color=tuple(int(c1[j]+(c2[j]-c1[j])*fr) for j in range(3))
            for x in range(1080):
                pix[x,y]=color
        rng=random.Random(hash(topic_key)%1000)
        shapes=pal.get("shapes","circles")
        if shapes=="circles":
            for r in range(80,600,65):
                a=max(0,min(255,int(100*(1-r/600))))
                draw.arc([540-r,700-r,540+r,700+r],start=rng.randint(0,180),
                         end=rng.randint(200,360),fill=(*acc,a),width=2)
        elif shapes=="grid":
            for x in range(0,1080,90):
                draw.rectangle([x,0,x+1,1920],fill=(*acc,15))
            for y in range(0,1920,90):
                draw.rectangle([0,y,1080,y+1],fill=(*acc,15))
        elif shapes=="waves":
            for i in range(12):
                pts=[(x,i*170+int(80*math.sin(x*0.015+i))) for x in range(0,1081,15)]
                if len(pts)>=2: draw.line(pts,fill=(*acc,30),width=2)
        elif shapes=="lines":
            for _ in range(20):
                x1=rng.randint(0,1080)
                draw.line([(x1,0),(x1+rng.randint(-100,100),1920)],fill=(*acc,20),width=1)
        if pal.get("stars"):
            for _ in range(200):
                sx,sy,ss=rng.randint(0,1080),rng.randint(0,1920),rng.randint(1,3)
                draw.ellipse([sx-ss,sy-ss,sx+ss,sy+ss],fill=(255,255,255,rng.randint(80,200)))
        for r in range(0,min(540,960),15):
            fade=int(80*(1-r/min(540,960))**2)
            draw.rectangle([r,r,1080-r,1920-r],outline=(0,0,0,fade),width=15)
        img.save(out,"JPEG",quality=94)
        log.info(f"PIL art: {out.name}")
        return out

    def _parse_json(self, raw: str) -> dict:
        raw = re.sub(r"^```json\s*","",raw.strip(),flags=re.MULTILINE)
        raw = re.sub(r"\s*```\s*$","",raw,flags=re.MULTILINE)
        return json.loads(raw)
