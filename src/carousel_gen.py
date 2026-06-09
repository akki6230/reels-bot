"""
src/carousel_gen.py — Generates Instagram Carousel posts.
3-5 slide images, users swipe manually.
Each slide = 1080x1920 with fact overlaid on image.

Layout matches the reference (like space facts channel):
  - Dark/image background
  - Bold gold/accent headline
  - White subtitle
  - Number badge
  - Brand watermark
"""

import os, re, json, random, logging, urllib.parse
from pathlib import Path
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from anthropic import Anthropic

log = logging.getLogger(__name__)

ROOT         = Path(__file__).parent.parent
CAROUSEL_DIR = ROOT / "output" / "carousel"
CAROUSEL_DIR.mkdir(parents=True, exist_ok=True)
FONTS_DIR    = ROOT / "fonts"

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
PEXELS_API_KEY    = os.environ.get("PEXELS_API_KEY", "")

W, H  = 1080, 1920
PAD   = 60

# Per-topic accent colors (gold/yellow = most viral)
THEMES = {
    "psychology":   {"acc": (200,160,255), "num": (180,120,255), "bg": (8,4,20)},
    "mindblowing":  {"acc": (255,200, 50), "num": (255,180, 30), "bg": (10,8,4)},
    "space":        {"acc": (255,200, 50), "num": (255,180, 30), "bg": (4,6,22)},
    "sciencewrong": {"acc": (100,220,130), "num": (80, 200,110), "bg": (5,18,5)},
    "earthglitch":  {"acc": (100,220,130), "num": (80, 200,110), "bg": (4,14,8)},
}

SYSTEM = """\
आप Instagram carousel posts के लिए viral Hindi educational content writer हैं।
तथ्य 100% सटीक और verified होने चाहिए। केवल JSON में उत्तर दें।"""

CAROUSEL_PROMPTS = {
    "psychology": """\
मनोविज्ञान के 5 अलग mind-blowing facts बनाएं — एक intro slide + 4 fact slides।
JSON:
{
  "title": "5 मनोविज्ञान के रहस्य 🧠",
  "slides": [
    {"type": "intro", "headline": "5 ऐसे मनोवैज्ञानिक तथ्य जो आपको हैरान कर देंगे", "detail": "Swipe करें और जानें 👉", "image_query": "human brain colorful psychology"},
    {"type": "fact", "number": "01", "headline": "max 8 words bold fact", "detail": "1-2 sentences explanation.", "image_query": "english pexels search query"},
    {"type": "fact", "number": "02", "headline": "...", "detail": "...", "image_query": "..."},
    {"type": "fact", "number": "03", "headline": "...", "detail": "...", "image_query": "..."},
    {"type": "fact", "number": "04", "headline": "...", "detail": "...", "image_query": "..."}
  ]
}""",
    "mindblowing": """\
5 mind-blowing facts बनाएं — intro + 4 facts।
JSON:
{
  "title": "5 ऐसे तथ्य जो दिमाग हिला दें 🤯",
  "slides": [
    {"type": "intro", "headline": "5 तथ्य जो आप नहीं जानते", "detail": "Swipe करें 👉", "image_query": "amazing universe explosion"},
    {"type": "fact", "number": "01", "headline": "shocking fact 8 words", "detail": "explanation.", "image_query": "photo query"},
    {"type": "fact", "number": "02", "headline": "...", "detail": "...", "image_query": "..."},
    {"type": "fact", "number": "03", "headline": "...", "detail": "...", "image_query": "..."},
    {"type": "fact", "number": "04", "headline": "...", "detail": "...", "image_query": "..."}
  ]
}""",
    "space": """\
अंतरिक्ष के 5 facts — intro + 4 facts।
JSON:
{
  "title": "अंतरिक्ष के 5 रहस्य 🚀",
  "slides": [
    {"type": "intro", "headline": "5 space facts जो आप नहीं जानते", "detail": "Swipe करें 👉", "image_query": "galaxy stars cosmos"},
    {"type": "fact", "number": "01", "headline": "fact 8 words", "detail": "detail.", "image_query": "space photo"},
    {"type": "fact", "number": "02", "headline": "...", "detail": "...", "image_query": "..."},
    {"type": "fact", "number": "03", "headline": "...", "detail": "...", "image_query": "..."},
    {"type": "fact", "number": "04", "headline": "...", "detail": "...", "image_query": "..."}
  ]
}""",
    "sciencewrong": """\
विज्ञान की 5 गलतियाँ — intro + 4 facts।
JSON:
{
  "title": "विज्ञान की 5 बड़ी गलतियाँ ⚗️",
  "slides": [
    {"type": "intro", "headline": "जब वैज्ञानिक भी गलत साबित हुए", "detail": "Swipe करें 👉", "image_query": "science laboratory"},
    {"type": "fact", "number": "01", "headline": "...", "detail": "...", "image_query": "..."},
    {"type": "fact", "number": "02", "headline": "...", "detail": "...", "image_query": "..."},
    {"type": "fact", "number": "03", "headline": "...", "detail": "...", "image_query": "..."},
    {"type": "fact", "number": "04", "headline": "...", "detail": "...", "image_query": "..."}
  ]
}""",
    "earthglitch": """\
धरती की 5 अजीब घटनाएं — intro + 4 facts।
JSON:
{
  "title": "धरती की 5 अजीब घटनाएं 🌍",
  "slides": [
    {"type": "intro", "headline": "धरती पर होती हैं ये 5 अजीब घटनाएं", "detail": "Swipe करें 👉", "image_query": "earth nature phenomenon"},
    {"type": "fact", "number": "01", "headline": "...", "detail": "...", "image_query": "..."},
    {"type": "fact", "number": "02", "headline": "...", "detail": "...", "image_query": "..."},
    {"type": "fact", "number": "03", "headline": "...", "detail": "...", "image_query": "..."},
    {"type": "fact", "number": "04", "headline": "...", "detail": "...", "image_query": "..."}
  ]
}""",
}

TOPIC_FALLBACK_KEYWORDS = {
    "psychology":   ["brain neurons", "human mind", "psychology", "meditation", "thinking"],
    "mindblowing":  ["universe cosmos", "explosion energy", "amazing nature", "science art"],
    "space":        ["galaxy nebula", "stars cosmos", "planet space", "milky way", "aurora"],
    "sciencewrong": ["laboratory", "chemistry", "science experiment", "research"],
    "earthglitch":  ["nature phenomenon", "waterfall landscape", "earth aerial", "lightning"],
}

# ── Font helpers ───────────────────────────────────────────────────────────────
FC: dict = {}
DEVA_URLS = {
    "bold":    "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf",
    "regular": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
}
SYSTEM_NOTO = [
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/fonts-noto/NotoSansDevanagari-Regular.ttf",
]

def _ensure_fonts():
    for variant, url in DEVA_URLS.items():
        fname = f"NotoSansDevanagari-{'Bold' if variant=='bold' else 'Regular'}.ttf"
        dest  = FONTS_DIR / fname
        if dest.exists() and dest.stat().st_size > 10000:
            continue
        for sp in SYSTEM_NOTO:
            if Path(sp).exists():
                import shutil
                try: shutil.copy2(sp, dest); break
                except: pass
        if not (dest.exists() and dest.stat().st_size > 10000):
            try:
                r = requests.get(url, timeout=30)
                if len(r.content) > 10000:
                    dest.write_bytes(r.content)
                    log.info(f"Font downloaded: {fname}")
            except Exception as e:
                log.warning(f"Font DL failed: {e}")

def _f(size, bold=False, lang="hi"):
    key = f"{lang}_{size}_{bold}"
    if key in FC: return FC[key]
    cands = []
    if lang == "hi":
        bp = FONTS_DIR / "NotoSansDevanagari-Bold.ttf"
        rp = FONTS_DIR / "NotoSansDevanagari-Regular.ttf"
        cands = [bp if bold else rp]
        for sp in SYSTEM_NOTO:
            if Path(sp).exists(): cands.append(Path(sp))
    cands += [
        FONTS_DIR / ("Poppins-Bold.ttf" if bold else "Poppins-Regular.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
             if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
             if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for p in cands:
        p = Path(p)
        if p.exists() and p.stat().st_size > 1000:
            try:
                f = ImageFont.truetype(str(p), size)
                FC[key] = f; return f
            except: continue
    return ImageFont.load_default()

def _a(v): return max(0, min(255, int(v)))
def _is_latin(w): return sum(1 for c in w if ord(c)<256) > len(w)*0.5

def _wrap_mixed(text, size, max_w, bold=False):
    hi_f=_f(size,bold=bold,lang="hi"); en_f=_f(size,bold=bold,lang="en")
    words,lines,cur,cw=[],[],"",0
    for word in text.split():
        fnt=en_f if _is_latin(word) else hi_f
        ww=fnt.getbbox(word+" ")[2]
        if cw+ww<=max_w: cur+=word+" "; cw+=ww
        else:
            if cur: lines.append(cur.strip())
            cur=word+" "; cw=ww
    if cur.strip(): lines.append(cur.strip())
    return lines

def _txt_mixed(draw, x, y, text, size, col, bold=False,
               shadow=True, center_w=None):
    hi_f=_f(size,bold=bold,lang="hi"); en_f=_f(size,bold=bold,lang="en")
    total_w=sum((en_f if _is_latin(w) else hi_f).getbbox(w+" ")[2] for w in text.split())
    cx=(center_w-total_w)//2 if center_w else x
    for word in text.split():
        fnt=en_f if _is_latin(word) else hi_f
        wp=word+" "
        if shadow: draw.text((cx+2,y+2),wp,font=fnt,fill=(0,0,0,100))
        draw.text((cx,y),wp,font=fnt,fill=col)
        cx+=fnt.getbbox(wp)[2]

def _txt_w(text, size, bold=False):
    hi_f=_f(size,bold=bold,lang="hi"); en_f=_f(size,bold=bold,lang="en")
    return sum((en_f if _is_latin(w) else hi_f).getbbox(w+" ")[2] for w in text.split())


# ── Slide renderer ─────────────────────────────────────────────────────────────

def render_slide(slide: dict, photo: Image.Image,
                 topic_key: str, slide_idx: int,
                 total_slides: int) -> Image.Image:
    """Render one 1080×1920 carousel slide."""

    theme = THEMES.get(topic_key, THEMES["space"])
    acc   = theme["acc"]
    num_c = theme["num"]
    bg_c  = theme["bg"]

    img   = Image.new("RGB", (W, H), bg_c)
    draw  = ImageDraw.Draw(img)

    # ── Background photo (top 65% of slide) ───────────────────────────────
    photo_h = int(H * 0.62)
    photo_r = photo.resize((W, photo_h), Image.LANCZOS)
    # Slight desaturate + darken for premium feel
    photo_r = ImageEnhance.Color(photo_r).enhance(0.85)
    photo_r = ImageEnhance.Brightness(photo_r).enhance(0.75)
    img.paste(photo_r, (0, 0))

    # Gradient fade from photo into black
    for y in range(photo_h - 200, photo_h + 60):
        if 0 <= y < H:
            prog   = (y - (photo_h - 200)) / 260
            prog   = max(0, min(1, prog))
            alpha  = int(255 * (prog ** 1.4))
            draw.rectangle([0, y, W, y+1],
                           fill=(*bg_c, alpha))

    # Vignette on photo
    for i in range(0, photo_h, 1):
        va = _a(120 * (1 - i / photo_h) ** 2)
        if va > 2:
            draw.rectangle([0, i, W, i+1], fill=(0,0,0,va))

    # ── Thin accent top bar ────────────────────────────────────────────────
    draw.rectangle([0, 0, W, 5], fill=acc)

    # ── Brand watermark top-right ──────────────────────────────────────────
    br_fnt = _f(24, lang="en")
    draw.text((W - PAD - 230, 18), "cosmos.capsule",
              font=br_fnt, fill=(200,200,200,200))

    # Slide indicator dots top-right
    dot_y = 50
    for di in range(total_slides):
        dx    = W - PAD - (total_slides - di) * 22
        is_c  = di == slide_idx
        col_  = acc if is_c else (100,100,100)
        r_    = 5 if is_c else 3
        draw.ellipse([dx-r_, dot_y-r_, dx+r_, dot_y+r_],
                     fill=col_)

    # ── Text section (bottom 38%) ──────────────────────────────────────────
    text_start = photo_h - 30

    slide_type = slide.get("type", "fact")

    if slide_type == "intro":
        # Intro slide: large centered headline + swipe prompt
        headline = slide.get("headline", "")
        detail   = slide.get("detail", "Swipe करें 👉")

        # Large headline
        h_size  = 58
        h_lines = _wrap_mixed(headline, h_size, W-PAD*2, bold=True)
        h_total = len(h_lines) * 72
        hy      = text_start + 30

        for line in h_lines:
            lw_ = _txt_w(line, h_size, bold=True)
            _txt_mixed(draw, 0, hy, line, h_size,
                       (*acc, 255), bold=True, center_w=W)
            hy += 72

        # Detail / swipe prompt
        d_size  = 34
        d_lines = _wrap_mixed(detail, d_size, W-PAD*2)
        hy     += 16
        for line in d_lines:
            _txt_mixed(draw, 0, hy, line, d_size,
                       (220,220,220,240), center_w=W)
            hy += 46

        # Big arrow "swipe" indicator
        arr_fnt = _f(60, lang="en")
        draw.text((W//2-20, H-180), "›", font=arr_fnt,
                  fill=(*acc, 200))

    else:
        # Fact slide: number badge + headline + detail
        number   = slide.get("number", f"0{slide_idx}")
        headline = slide.get("headline", "")
        detail   = slide.get("detail", "")

        # Number badge
        num_fnt  = _f(52, bold=True, lang="en")
        num_bb   = num_fnt.getbbox(number)
        # Pill background
        pill_w   = num_bb[2] + 32
        pill_h   = 60
        pill_x   = PAD
        pill_y   = text_start + 20
        draw.rounded_rectangle(
            [pill_x, pill_y, pill_x+pill_w, pill_y+pill_h],
            radius=14, fill=(*num_c, 30),
            outline=(*num_c, 180), width=2
        )
        draw.text((pill_x+16, pill_y+4), number,
                  font=num_fnt, fill=(*num_c, 255))

        # Headline (bold, accent color)
        h_size  = 54
        h_start = pill_y + pill_h + 18
        h_lines = _wrap_mixed(headline, h_size, W-PAD*2, bold=True)

        hy = h_start
        for line in h_lines:
            lw_ = _txt_w(line, h_size, bold=True)
            lx_ = (W - lw_) // 2
            # Glow pass
            _txt_mixed(draw, lx_+1, hy+1, line, h_size,
                       (0,0,0,80), bold=True, shadow=False)
            _txt_mixed(draw, lx_, hy, line, h_size,
                       (*acc, 255), bold=True, shadow=False)
            hy += 66

        # Detail (white, regular)
        d_size  = 32
        d_start = hy + 12
        d_lines = _wrap_mixed(detail, d_size, W-PAD*2)

        dy = d_start
        for line in d_lines:
            lw_ = _txt_w(line, d_size)
            lx_ = (W - lw_) // 2
            _txt_mixed(draw, lx_, dy, line, d_size,
                       (225,225,225,240), shadow=True)
            dy += 44

        # Thin accent line at very bottom
        draw.rectangle([PAD, H-80, W-PAD, H-78],
                       fill=(*acc, 80))
        # Follow text
        fl_fnt = _f(24, lang="hi")
        fl_txt = "रोज़ नई जानकारी के लिए फॉलो करें ✨"
        fl_w   = _txt_w(fl_txt, 24)
        _txt_mixed(draw, 0, H-64, fl_txt, 24,
                   (160,160,160,200), center_w=W)

    return img


# ── CarouselGenerator ──────────────────────────────────────────────────────────

class CarouselGenerator:
    def __init__(self):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)

    def generate_content(self, topic_key: str) -> dict:
        """Generate 5 slides of content (1 intro + 4 facts)."""
        prompt = CAROUSEL_PROMPTS.get(topic_key, CAROUSEL_PROMPTS["mindblowing"])
        msg    = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw  = msg.content[0].text.strip()
        raw  = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
        raw  = re.sub(r"\s*```\s*$",  "", raw, flags=re.MULTILINE)
        data = json.loads(raw)
        log.info(f"📋 Carousel: {data.get('title','')} — {len(data.get('slides',[]))} slides")
        return data

    def fetch_images(self, slides: list, topic_key: str,
                     run_id: str) -> list[Path]:
        """Fetch one image per slide from Pexels."""
        paths = []
        for i, slide in enumerate(slides):
            query = slide.get("image_query", "")
            img   = self._fetch_one(query, topic_key, run_id, i)
            paths.append(img)
        return paths

    def _fetch_one(self, query: str, topic_key: str,
                   run_id: str, idx: int) -> Path:
        out = CAROUSEL_DIR / f"carousel_{run_id}_{idx}.jpg"

        if PEXELS_API_KEY and query:
            img = self._pexels(query, out)
            if img: return img

        if PEXELS_API_KEY:
            for kw in TOPIC_FALLBACK_KEYWORDS.get(topic_key, ["nature"]):
                img = self._pexels(kw, out)
                if img: return img

        img = self._picsum(out)
        if img: return img

        return self._pil_fallback(topic_key, out)

    def _pexels(self, query: str, out: Path) -> Path | None:
        try:
            resp = requests.get(
                "https://api.pexels.com/v1/search",
                params={"query": query, "orientation": "portrait",
                        "size": "large", "per_page": 15,
                        "page": random.randint(1, 4)},
                headers={"Authorization": PEXELS_API_KEY},
                timeout=15,
            )
            resp.raise_for_status()
            photos = resp.json().get("photos", [])
            if not photos: return None
            photo    = random.choice(photos)
            img_resp = requests.get(photo["src"]["large2x"], timeout=30)
            out.write_bytes(img_resp.content)
            log.info(f"  Pexels [{query[:25]}]: {out.name}")
            return out
        except Exception as e:
            log.warning(f"  Pexels: {e}")
            return None

    def _picsum(self, out: Path) -> Path | None:
        try:
            seed = random.randint(1, 1000)
            resp = requests.get(
                f"https://picsum.photos/seed/{seed}/1080/1920",
                timeout=20
            )
            resp.raise_for_status()
            if len(resp.content) < 10000: return None
            out.write_bytes(resp.content)
            log.info(f"  Picsum: {out.name}")
            return out
        except Exception as e:
            log.warning(f"  Picsum: {e}")
            return None

    def _pil_fallback(self, topic_key: str, out: Path) -> Path:
        th   = THEMES.get(topic_key, THEMES["space"])
        bg   = th["bg"]
        acc  = th["acc"]
        img  = Image.new("RGB", (W, H), bg)
        draw = ImageDraw.Draw(img)
        for i in range(8):
            cx = random.randint(100, W-100)
            cy = random.randint(100, H-100)
            r  = random.randint(50, 200)
            draw.ellipse([cx-r,cy-r,cx+r,cy+r], outline=(*acc,30), width=2)
        img.save(out, "JPEG", quality=92)
        return out

    def render_all_slides(self, content: dict, image_paths: list,
                           topic_key: str, run_id: str) -> list[Path]:
        """Render all slides and save as individual JPGs."""
        _ensure_fonts()
        slides       = content.get("slides", [])
        n            = len(slides)
        output_paths = []

        for i, (slide, img_path) in enumerate(zip(slides, image_paths)):
            try:
                photo = Image.open(img_path).convert("RGB")
            except Exception:
                photo = Image.new("RGB", (W, H), THEMES.get(topic_key,THEMES["space"])["bg"])

            rendered = render_slide(slide, photo, topic_key, i, n)
            out_path = CAROUSEL_DIR / f"slide_{run_id}_{i:02d}.jpg"
            rendered.save(out_path, "JPEG", quality=95)
            output_paths.append(out_path)
            log.info(f"  ✅ Slide {i+1}/{n}: {out_path.name}")

        return output_paths
