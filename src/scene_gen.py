"""
src/scene_gen.py — Generates illustrated story scenes using Hugging Face.

Style: Indian 2D cartoon illustration (like @epictalesanimation)
- 3 scenes per reel, each shown 5-7 seconds
- Uses Stable Diffusion via HF Inference API
- Falls back to Pollinations if HF fails
"""

import os
import re
import json
import time
import random
import logging
import urllib.parse
from pathlib import Path

import requests
from anthropic import Anthropic

log = logging.getLogger(__name__)

ROOT       = Path(__file__).parent.parent
SCENES_DIR = ROOT / "output" / "scenes"
SCENES_DIR.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
HF_API_KEY        = os.environ.get("HF_API_KEY", "")

# Best HF models for Indian cartoon illustration style
HF_MODELS = [
    {
        "model": "stabilityai/stable-diffusion-xl-base-1.0",
        "url":   "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
    },
    {
        "model": "runwayml/stable-diffusion-v1-5",
        "url":   "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5",
    },
    {
        "model": "stabilityai/stable-diffusion-2-1",
        "url":   "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1",
    },
]

# Router endpoint — newer HF API that works better
HF_ROUTER_URL = "https://router.huggingface.co/hf-inference/models/{model}/v1/images/generate"

# Style suffix added to every prompt for consistent look
STYLE_SUFFIX = (
    "Indian 2D cartoon illustration style, flat colors, clean lines, "
    "Bollywood animation aesthetic, warm colors, detailed background, "
    "high quality digital art, no text, no watermark, "
    "9:16 vertical format, portrait orientation"
)

NEGATIVE_PROMPT = (
    "text, watermark, logo, blurry, low quality, distorted, "
    "western cartoon, 3D, realistic photo, dark, scary, "
    "nsfw, violence, gore"
)

# Scene description prompts per topic
SCENE_PROMPTS = {
    "psychology": [
        "A person sitting quietly thinking with a glowing brain visible, Indian setting, warm lighting",
        "Two Indian people having a conversation, one listening carefully with empathy",
        "A student studying at night with books and notes, focused expression, Indian home",
        "Person waking up feeling refreshed and happy, morning sunlight, Indian bedroom",
        "Group of Indian friends laughing and enjoying together, outdoor park setting",
    ],
    "mindblowing": [
        "A person with wide shocked eyes looking at something amazing in the sky, Indian street",
        "Tiny human standing next to a massive cosmic phenomenon, scale comparison art",
        "Indian scientist looking through microscope with amazed expression",
        "Person pointing at jaw-dropping statistics on a chalkboard, classroom setting",
        "Child and adult both looking shocked at an incredible natural phenomenon",
    ],
    "space": [
        "An Indian astronaut floating in space looking at Earth from above, colorful suit",
        "A rocket launching from ISRO launch pad with bright flames, crowd watching",
        "Beautiful view of galaxy and stars from a rooftop, Indian family stargazing",
        "Scientist at ISRO control room watching rocket launch on monitors",
        "Child looking through telescope at night sky, parents watching, Indian village",
    ],
    "sciencewrong": [
        "A scientist with wild hair in a messy lab with bubbling beakers everywhere",
        "Indian chemistry teacher showing a surprising experiment to shocked students",
        "Old scientist looking embarrassed at a failed experiment, lab setting",
        "Students in science class watching an unexpected reaction with wide eyes",
        "Scientist reading old wrong textbook with correction marks, comic expression",
    ],
    "earthglitch": [
        "A person standing at the edge of a mysterious natural phenomenon, India landscape",
        "Family watching an unusual weather event from their window, amazed expressions",
        "Indian village near a strange glowing lake or forest phenomenon at night",
        "Two people looking confused at an upside-down waterfall or unusual landform",
        "Scientist measuring an unusual earthquake crack in the ground, rural India",
    ],
}


class SceneGenerator:
    def __init__(self):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)

    def generate_scenes(self, topic_key: str, fact_data: dict,
                        run_id: str) -> list[Path]:
        """
        Generate 3 illustrated scene images for the reel.
        Returns list of 3 image paths.
        """
        # Generate scene descriptions tailored to the specific fact
        descriptions = self._get_scene_descriptions(topic_key, fact_data)
        log.info(f"📸 Generating {len(descriptions)} scenes for: {fact_data['hook'][:40]}")

        paths = []
        for i, desc in enumerate(descriptions[:3]):
            log.info(f"  Scene {i+1}/3: {desc[:60]}...")
            img_path = self._generate_image(desc, topic_key, run_id, i)
            if img_path:
                paths.append(img_path)
                log.info(f"  ✅ Scene {i+1} saved: {img_path.name}")
            else:
                log.warning(f"  ⚠️ Scene {i+1} failed — using fallback")
                fallback = self._fallback_image(topic_key, run_id, i)
                paths.append(fallback)

        return paths

    def _get_scene_descriptions(self, topic_key: str,
                                 fact_data: dict) -> list[str]:
        """Ask Claude to generate 3 scene descriptions for the fact."""
        hook  = fact_data.get("hook", "")
        body  = fact_data.get("body", "")

        prompt = f"""इस हिंदी तथ्य के लिए 3 cartoon illustration scenes बनाएं:

Hook: {hook}
Body: {body}

3 scenes describe करें जो इस तथ्य को visually explain करें।
Indian cartoon style में — जैसे Bollywood animation।
हर scene में Indian characters और Indian setting हो।

JSON में उत्तर दें:
{{
  "scene1": "Detailed English description of first scene for image generation",
  "scene2": "Detailed English description of second scene",
  "scene3": "Detailed English description of third scene (conclusion/reaction)"
}}

Rules:
- Each scene description in English (for image AI)
- Include specific Indian visual elements (sari, dhoti, Indian homes, etc.)
- Scene 1: Setup/intro of the fact
- Scene 2: Main visual explanation
- Scene 3: Reaction/conclusion/wow moment"""

        try:
            msg = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            raw  = msg.content[0].text.strip()
            raw  = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
            raw  = re.sub(r"\s*```\s*$", "", raw, flags=re.MULTILINE)
            data = json.loads(raw)
            return [data.get("scene1",""), data.get("scene2",""), data.get("scene3","")]
        except Exception as e:
            log.warning(f"Scene description generation failed: {e}")
            # Fall back to generic topic scenes
            pool = SCENE_PROMPTS.get(topic_key, SCENE_PROMPTS["mindblowing"])
            return random.sample(pool, min(3, len(pool)))

    def _generate_image(self, description: str, topic_key: str,
                         run_id: str, idx: int) -> Path | None:
        """Try HF → Pollinations → Picsum → PIL fallback."""
        out = SCENES_DIR / f"scene_{run_id}_{idx}.jpg"

        # 1. Try Hugging Face (best quality)
        if HF_API_KEY:
            result = self._hf_image(description, out)
            if result:
                return result
            log.warning("  HF failed — trying Pollinations...")

        # 2. Try Pollinations (free, short prompt)
        result = self._pollinations_image(description, topic_key, out)
        if result:
            return result

        # 3. Try Picsum (free beautiful photos — not illustrated but works)
        result = self._picsum_image(out)
        if result:
            return result

        return None

    def _picsum_image(self, out: Path) -> Path | None:
        """Picsum.photos — free, no key, always works."""
        try:
            seed = random.randint(1, 1000)
            url  = f"https://picsum.photos/seed/{seed}/1080/1920"
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            if len(resp.content) < 10000:
                return None
            out.write_bytes(resp.content)
            log.info(f"  Picsum fallback: {out.name}")
            return out
        except Exception as e:
            log.warning(f"  Picsum error: {e}")
            return None

    def _hf_image(self, description: str, out: Path) -> Path | None:
        """Generate image via Hugging Face Inference API."""
        full_prompt = f"{description}, {STYLE_SUFFIX}"

        for model_info in HF_MODELS:
            model = model_info["model"]
            # Try router endpoint first (newer, more reliable)
            endpoints = [
                HF_ROUTER_URL.format(model=model),
                model_info["url"],
            ]

            for url in endpoints:
                try:
                    log.info(f"  HF: {model.split('/')[-1]}")
                    resp = requests.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {HF_API_KEY}",
                            "Content-Type":  "application/json",
                        },
                        json={
                            "inputs": full_prompt,
                            "parameters": {
                                "negative_prompt":    NEGATIVE_PROMPT,
                                "num_inference_steps": 25,
                                "guidance_scale":      7.5,
                                "width":  576,
                                "height": 1024,
                            },
                            "options": {"wait_for_model": True},
                        },
                        timeout=120,
                    )

                    if resp.status_code == 200 and len(resp.content) > 5000:
                        from PIL import Image
                        import io
                        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                        img = img.resize((1080, 1920), Image.LANCZOS)
                        img.save(out, "JPEG", quality=92)
                        log.info(f"  ✅ HF success: {out.name}")
                        return out
                    elif resp.status_code == 503:
                        log.warning(f"  HF model loading, waiting 20s...")
                        time.sleep(20)
                        continue
                    elif resp.status_code in (401, 403):
                        log.warning(f"  HF auth error — check HF_API_KEY secret")
                        return None
                    else:
                        log.warning(f"  HF {resp.status_code}")
                        continue

                except requests.exceptions.ConnectionError as e:
                    log.warning(f"  HF DNS/connection error: {str(e)[:80]}")
                    log.warning(f"  → HF API unreachable from this runner")
                    # DNS failure means ALL HF endpoints will fail — exit early
                    return None
                except Exception as e:
                    log.warning(f"  HF error: {str(e)[:80]}")
                    continue

        return None

    def _pollinations_image(self, description: str, topic_key: str,
                             out: Path) -> Path | None:
        """Fallback: Pollinations.ai free tier with SHORT prompt."""
        try:
            # Keep prompt SHORT — long prompts cause 402 errors
            # Strip any Hindi/non-ASCII characters from prompt
            clean = re.sub(r'[^\x00-\x7F]+', '', description)
            clean = clean[:120].strip()   # max 120 chars
            if not clean:
                clean = f"Indian cartoon illustration {topic_key} scene"

            style = "Indian 2D cartoon flat colors clean lines"
            full  = f"{clean}, {style}"
            enc   = urllib.parse.quote(full)
            seed  = random.randint(1, 99999)

            # Use smaller size — free tier limit
            url = (f"https://image.pollinations.ai/prompt/{enc}"
                   f"?width=512&height=912&nologo=true&seed={seed}&model=flux&enhance=false")

            resp = requests.get(url, timeout=60)

            if resp.status_code == 402:
                log.warning("  Pollinations: payment required — using PIL fallback")
                return None

            resp.raise_for_status()
            if len(resp.content) < 5000:
                return None

            from PIL import Image
            import io
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            img = img.resize((1080, 1920), Image.LANCZOS)
            img.save(out, "JPEG", quality=92)
            log.info(f"  Pollinations: {out.name}")
            return out
        except Exception as e:
            log.warning(f"  Pollinations error: {e}")
            return None

    def _fallback_image(self, topic_key: str, run_id: str,
                         idx: int) -> Path:
        """Last resort: PIL illustrated art."""
        from PIL import Image, ImageDraw
        import math

        PALETTES = {
            "psychology":   [(8,4,20),(25,10,55),(40,15,85)],
            "mindblowing":  [(20,5,5),(50,10,8),(75,18,12)],
            "space":        [(4,6,22),(8,14,45),(12,22,68)],
            "sciencewrong": [(5,18,5),(12,45,15),(20,70,25)],
            "earthglitch":  [(4,14,8),(10,35,18),(16,55,28)],
        }
        ACCENTS = {
            "psychology":  (160,100,255),
            "mindblowing": (255,80,50),
            "space":       (100,185,255),
            "sciencewrong":(80,230,120),
            "earthglitch": (70,215,130),
        }

        cols = PALETTES.get(topic_key, [(10,10,30),(25,25,70),(40,40,100)])
        acc  = ACCENTS.get(topic_key, (100,180,255))
        out  = SCENES_DIR / f"scene_{run_id}_{idx}_fallback.jpg"
        img  = Image.new("RGB", (1080, 1920))
        draw = ImageDraw.Draw(img)
        pix  = img.load()

        # Gradient
        for y in range(1920):
            fy = y/1920
            if fy < 0.5:
                fr = fy/0.5
                c1,c2 = cols[0],cols[1]
            else:
                fr = (fy-0.5)/0.5
                c1,c2 = cols[1],cols[2]
            color = tuple(int(c1[j]+(c2[j]-c1[j])*fr) for j in range(3))
            for x in range(1080):
                pix[x,y] = color

        # Decorative elements
        rng = random.Random(idx*7)
        for _ in range(8):
            cx = rng.randint(100,980); cy = rng.randint(100,1820)
            r  = rng.randint(30,150)
            draw.ellipse([cx-r,cy-r,cx+r,cy+r],
                         outline=(*acc,40), width=2)

        # Stars if space
        if topic_key == "space":
            for _ in range(200):
                sx,sy = rng.randint(0,1080),rng.randint(0,1920)
                ss = rng.randint(1,3)
                draw.ellipse([sx-ss,sy-ss,sx+ss,sy+ss],
                             fill=(255,255,255,rng.randint(80,200)))

        # Vignette
        for r in range(0,min(540,960),15):
            fade = int(80*(1-r/min(540,960))**2)
            draw.rectangle([r,r,1080-r,1920-r],
                           outline=(0,0,0,fade),width=15)

        img.save(out,"JPEG",quality=94)
        return out
