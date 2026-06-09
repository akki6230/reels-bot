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
    """
    Render one 1080×1920 carousel slide.
    Photo fills the ENTIRE slide. Text overlaid in center.
    No split layout — exactly like the reference images.
    """
    theme = THEMES.get(topic_key, THEMES["space"])
    acc   = theme["acc"]
    num_c = theme["num"]

    # ── Full-bleed background photo ────────────────────────────────────────
    img = photo.resize((W, H), Image.LANCZOS)
    # Desaturate slightly + darken for text readability
    img = ImageEnhance.Color(img).enhance(0.80)
    img = ImageEnhance.Brightness(img).enhance(0.60)
    img = img.convert("RGBA")

    # Dark overlay in center area for text contrast
    overlay = Image.new("RGBA", (W, H), (0,0,0,0))
    od      = ImageDraw.Draw(overlay)

    # Vertical gradient — darker in middle where text lives
    for y in range(H):
        fy    = y / H
        # Darkest around 40-80% height (text area)
        dist  = abs(fy - 0.60)
        alpha = int(180 * max(0, 1 - dist * 2.5))
        od.rectangle([0, y, W, y+1], fill=(0,0,0,alpha))

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # ── Thin accent bar at top ─────────────────────────────────────────────
    draw.rectangle([0, 0, W, 6], fill=(*acc, 255))

    # ── Brand watermark top-left ───────────────────────────────────────────
    br_fnt = _f(26, bold=True, lang="en")
    draw.text((PAD, 20), "cosmos.capsule",
              font=br_fnt, fill=(*acc, 220))

    # ── Slide indicator dots top-right ────────────────────────────────────
    dot_y = 30
    for di in range(total_slides):
        dx   = W - PAD - (total_slides - di - 1) * 26
        is_c = di == slide_idx
        r_   = 6 if is_c else 4
        col_ = acc if is_c else (140,140,140)
        draw.ellipse([dx-r_, dot_y-r_, dx+r_, dot_y+r_],
                     fill=(*col_, 255))

    slide_type = slide.get("type", "fact")

    if slide_type == "intro":
        # ── INTRO SLIDE — centered big text ───────────────────────────────
        headline = slide.get("headline", "")
        detail   = slide.get("detail", "Swipe करें 👉")

        h_size  = 62
        h_lines = _wrap_mixed(headline, h_size, W-PAD*2, bold=True)
        h_total = len(h_lines) * 78
        # Center vertically
        hy      = H//2 - h_total//2 - 40

        for line in h_lines:
            _txt_mixed(draw, 0, hy, line, h_size,
                       (*acc, 255), bold=True, center_w=W)
            hy += 78

        # Divider line
        draw.rectangle([PAD*3, hy+10, W-PAD*3, hy+13],
                       fill=(*acc, 120))

        # Detail
        d_size  = 40
        d_lines = _wrap_mixed(detail, d_size, W-PAD*2)
        dy      = hy + 28
        for line in d_lines:
            _txt_mixed(draw, 0, dy, line, d_size,
                       (220,220,220,240), center_w=W)
            dy += 50

        # Swipe arrow at bottom
        arr_fnt = _f(72, lang="en")
        draw.text((W//2-22, H-180), "›",
                  font=arr_fnt, fill=(*acc, 200))

    else:
        # ── FACT SLIDE — number + headline + detail centered ──────────────
        number   = slide.get("number", f"0{slide_idx}")
        headline = slide.get("headline", "")
        detail   = slide.get("detail", "")

        # Calculate total text block height for centering
        h_size  = 56
        h_lines = _wrap_mixed(headline, h_size, W-PAD*2, bold=True)
        d_size  = 38
        d_lines = _wrap_mixed(detail, d_size, W-PAD*2)

        num_h   = 72    # number badge height
        h_h     = len(h_lines) * 70
        gap     = 20
        d_h     = len(d_lines) * 44
        total_h = num_h + gap + h_h + gap + d_h

        # Start Y to center the whole block
        start_y = H//2 - total_h//2

        # Number badge
        num_fnt = _f(48, bold=True, lang="en")
        num_bb  = num_fnt.getbbox(number)
        pill_w  = num_bb[2] + 40
        pill_h  = 60
        pill_x  = (W - pill_w) // 2   # centered
        pill_y  = start_y

        draw.rounded_rectangle(
            [pill_x, pill_y, pill_x+pill_w, pill_y+pill_h],
            radius=16,
            fill=(*num_c, 35),
            outline=(*num_c, 200),
            width=2
        )
        draw.text((pill_x + 20, pill_y + 6), number,
                  font=num_fnt, fill=(*num_c, 255))

        # Headline (bold, accent color, centered)
        hy = pill_y + pill_h + gap
        for line in h_lines:
            # Glow / shadow
            _txt_mixed(draw, 2, hy+2, line, h_size,
                       (0,0,0,100), bold=True,
                       shadow=False, center_w=W)
            _txt_mixed(draw, 0, hy, line, h_size,
                       (*acc, 255), bold=True,
                       shadow=False, center_w=W)
            hy += 70

        # Thin divider
        draw.rectangle([PAD*2, hy+8, W-PAD*2, hy+10],
                       fill=(*acc, 60))

        # Detail (white, centered)
        dy = hy + 24
        for line in d_lines:
            _txt_mixed(draw, 0, dy, line, d_size,
                       (225,225,225,235), center_w=W)
            dy += 52

    # ── Bottom bar ─────────────────────────────────────────────────────────
    draw.rectangle([0, H-70, W, H], fill=(0,0,0,180))
    draw.rectangle([0, H-70, W, H-68], fill=(*acc, 80))

    fl_fnt = _f(24, lang="hi")
    fl_txt = "रोज़ नई जानकारी के लिए फॉलो करें ✨"
    _txt_mixed(draw, 0, H-52, fl_txt, 24,
               (180,180,180,200), center_w=W)

    return img.convert("RGB")


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
                params={
                    "query":       query,
                    "orientation": "portrait",   # always portrait for 9:16
                    "size":        "large",
                    "per_page":    15,
                    "page":        random.randint(1, 4),
                },
                headers={"Authorization": PEXELS_API_KEY},
                timeout=15,
            )
            resp.raise_for_status()
            photos = resp.json().get("photos", [])
            if not photos:
                return None
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
            # Must be portrait 1080x1920 for carousel slides
            resp = requests.get(
                f"https://picsum.photos/seed/{seed}/1080/1920",
                timeout=20
            )
            resp.raise_for_status()
            if len(resp.content) < 10000:
                return None
            out.write_bytes(resp.content)
            log.info(f"  Picsum: {out.name}")
            return out
        except Exception as e:
            log.warning(f"  Picsum: {e}")
            return None

    def _pil_fallback(self, topic_key: str, out: Path) -> Path:
        """Rich PIL background when no photo available."""
        import math
        th   = THEMES.get(topic_key, THEMES["space"])
        bg   = th["bg"]
        acc  = th["acc"]
        num  = th["num"]
        img  = Image.new("RGBA", (W, H), (*bg, 255))
        draw = ImageDraw.Draw(img)

        # Multi-stop gradient
        colors = [bg, tuple(min(255,c+30) for c in bg),
                  tuple(min(255,c+15) for c in bg), bg]
        pix = img.load()
        n   = len(colors)
        for y in range(H):
            fy  = y / H
            idx = fy * (n-1)
            i   = min(int(idx), n-2)
            fr  = idx - i
            c1, c2 = colors[i], colors[i+1]
            color  = tuple(int(c1[j]+(c2[j]-c1[j])*fr) for j in range(3))
            for x in range(W):
                pix[x,y] = (*color, 255)

        # Decorative circles
        rng = random.Random(hash(topic_key) % 999)
        for _ in range(12):
            cx_ = rng.randint(0, W)
            cy_ = rng.randint(0, H)
            r_  = rng.randint(60, 300)
            draw.ellipse([cx_-r_,cy_-r_,cx_+r_,cy_+r_],
                         outline=(*acc,35), width=2)

        # Stars for space topic
        if topic_key == "space":
            for _ in range(250):
                sx, sy = rng.randint(0,W), rng.randint(0,H)
                ss     = rng.randint(1,3)
                draw.ellipse([sx-ss,sy-ss,sx+ss,sy+ss],
                             fill=(255,255,255,rng.randint(80,200)))

        # Vignette
        for r_ in range(0, min(540,960), 12):
            fade = int(100*(1-r_/min(540,960))**2)
            draw.rectangle([r_,r_,W-r_,H-r_],
                           outline=(0,0,0,fade),width=12)

        img.convert("RGB").save(out, "JPEG", quality=92)
        return out

    def render_all_slides(self, content: dict, image_paths: list,
                           topic_key: str, run_id: str) -> list[Path]:
        """
        Render text directly onto each fetched image.
        Overwrites the original fetched file — no duplicate images.
        Total output = same number of files as input.
        """
        _ensure_fonts()
        slides       = content.get("slides", [])
        n            = len(slides)
        output_paths = []

        for i, (slide, img_path) in enumerate(zip(slides, image_paths)):
            try:
                # Open the already-fetched Pexels/Picsum image
                photo = Image.open(img_path).convert("RGB")
            except Exception:
                photo = Image.new("RGB", (W, H),
                                  THEMES.get(topic_key, THEMES["space"])["bg"])

            # Render text centered on the image
            rendered = render_slide(slide, photo, topic_key, i, n)

            # Save back to the SAME path — no new file created
            rendered.save(img_path, "JPEG", quality=95)
            output_paths.append(img_path)
            log.info(f"  ✅ Slide {i+1}/{n}: {img_path.name}")

        return output_paths
