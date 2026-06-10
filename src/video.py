"""
src/video.py — Dual-mode video renderer:

MODE A: ILLUSTRATED (6-7 out of 10 reels)
  - 3 AI-generated illustrated scenes from HF
  - Ken Burns zoom + pan between scenes
  - Hindi text overlay with smooth animations
  - Like @epictalesanimation style

MODE B: ANIMATED (3-4 out of 10 reels)
  - Random: kinetic / documentary / cartoon
  - Pure Python, no photos needed

Selection: random, weighted 65% illustrated / 35% animated
"""

import math, random, logging
from pathlib import Path
from datetime import datetime

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from moviepy.editor import VideoClip, AudioFileClip
from moviepy.video.fx.all import fadein, fadeout

from config import REEL_WIDTH, REEL_HEIGHT, REEL_FPS, LANGUAGES

log       = logging.getLogger(__name__)
W, H      = REEL_WIDTH, REEL_HEIGHT
PAD       = 68
ROOT      = Path(__file__).parent.parent
FONTS_DIR = ROOT / "fonts"
FONTS_DIR.mkdir(exist_ok=True)

# ── Themes ─────────────────────────────────────────────────────────────────────
THEMES = {
    "psychology":   {"acc":(160,100,255),"acc2":(200,140,255),"acc3":(220,180,255),
                     "txt":(235,220,255),"mut":(165,135,210),
                     "bg1":(8,4,20),"bg2":(25,10,55),"bg3":(40,15,85),
                     "particles":True,"p_col":(200,160,255),
                     "bg_style":"neural","emoji_pool":["🧠","💭","✨","🔮","💡","🌀"],
                     "label":"मनोविज्ञान तथ्य"},
    "mindblowing":  {"acc":(255,80,50),"acc2":(255,130,80),"acc3":(255,180,130),
                     "txt":(255,235,228),"mut":(210,155,148),
                     "bg1":(20,5,5),"bg2":(50,10,8),"bg3":(75,18,12),
                     "particles":True,"p_col":(255,150,100),
                     "bg_style":"explosion","emoji_pool":["🤯","💥","⚡","🔥","😱","🌪️"],
                     "label":"दिमाग हिला देने वाले तथ्य"},
    "space":        {"acc":(100,185,255),"acc2":(150,210,255),"acc3":(200,230,255),
                     "txt":(225,242,255),"mut":(140,170,210),
                     "bg1":(4,6,22),"bg2":(8,14,45),"bg3":(12,22,68),
                     "particles":True,"p_col":(200,225,255),
                     "bg_style":"cosmos","emoji_pool":["🚀","⭐","🌌","🪐","☄️","🌟"],
                     "label":"अंतरिक्ष और ब्रह्मांड"},
    "sciencewrong": {"acc":(80,230,120),"acc2":(120,245,160),"acc3":(180,255,200),
                     "txt":(215,255,225),"mut":(130,200,155),
                     "bg1":(5,18,5),"bg2":(10,40,15),"bg3":(15,65,22),
                     "particles":False,"p_col":(150,255,180),
                     "bg_style":"lab","emoji_pool":["⚗️","💊","🔬","🧪","💣","🤓"],
                     "label":"विज्ञान जब गलत हो गया"},
    "earthglitch":  {"acc":(70,215,130),"acc2":(110,235,165),"acc3":(170,250,195),
                     "txt":(215,255,230),"mut":(130,200,160),
                     "bg1":(4,14,8),"bg2":(8,32,16),"bg3":(12,52,24),
                     "particles":False,"p_col":(150,240,185),
                     "bg_style":"earth","emoji_pool":["🌍","⚡","🌊","🌋","❄️","🌪️"],
                     "label":"धरती की अजीब घटनाएं"},
    "gk":           {"acc":(255,180,40),"acc2":(255,200,80),"acc3":(255,220,120),
                     "txt":(255,245,220),"mut":(200,175,130),
                     "bg1":(4,8,18),"bg2":(15,18,40),"bg3":(25,28,60),
                     "particles":False,"p_col":(255,200,100),
                     "bg_style":"neural","emoji_pool":["📚","💡","🌍","🏛️","🔭","📖"],
                     "label":"सामान्य ज्ञान"},
    "examfacts":    {"acc":(80,200,255),"acc2":(120,220,255),"acc3":(180,235,255),
                     "txt":(220,240,255),"mut":(140,175,210),
                     "bg1":(4,4,18),"bg2":(8,10,35),"bg3":(12,16,52),
                     "particles":False,"p_col":(150,215,255),
                     "bg_style":"grid","emoji_pool":["🎯","📝","✅","🏆","📌","💯"],
                     "label":"परीक्षा ज्ञान"},
}

VIDEO_TAGS = {
    "psychology":   ["#मनोविज्ञान","#psychology","#दिमाग","#mindset","#facts","#cosmoscapsule"],
    "mindblowing":  ["#mindblow","#दिमागहिला","#amazingfacts","#रोचकतथ्य","#viral","#cosmoscapsule"],
    "space":        ["#अंतरिक्ष","#ब्रह्मांड","#spacefacts","#NASA","#ISRO","#cosmoscapsule"],
    "sciencewrong": ["#sciencefail","#विज्ञान","#sciencefacts","#funny","#facts","#cosmoscapsule"],
    "earthglitch":  ["#earthglitch","#धरती","#naturalfacts","#amazing","#mystery","#cosmoscapsule"],
    "gk":           ["#सामान्यज्ञान","#GK","#gkinhindi","#ज्ञान","#india","#cosmoscapsule"],
    "examfacts":    ["#UPSC","#SSC","#NEET","#IIT","#gkinhindi","#cosmoscapsule"],
}

# ── Font helpers ───────────────────────────────────────────────────────────────
FC: dict = {}

# Multiple CDN sources for Noto Sans Devanagari (fallback chain)
DEVANAGARI_FONT_URLS = {
    "bold": [
        "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf",
        "https://fonts.gstatic.com/s/notosansdevanagari/v25/TuGKUUVzXI5FBtUq5a8bjKYTZjtgv-_J9WqDBz4.ttf",
        "https://cdn.jsdelivr.net/npm/@fontsource/noto-sans-devanagari@5.0.8/files/noto-sans-devanagari-devanagari-700-normal.woff2",
    ],
    "regular": [
        "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
        "https://fonts.gstatic.com/s/notosansdevanagari/v25/TuGKUUVzXI5FBtUq5a8bjKYTZjtgv-_J9WqDBz4.ttf",
    ],
}

# System paths where Noto Devanagari may already be installed
SYSTEM_DEVANAGARI_PATHS = [
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/fonts-noto/NotoSansDevanagari-Regular.ttf",
]


def _ensure_hindi_fonts():
    """Download Hindi fonts at startup — call once before rendering."""
    bold_path = FONTS_DIR / "NotoSansDevanagari-Bold.ttf"
    reg_path  = FONTS_DIR / "NotoSansDevanagari-Regular.ttf"

    # Check system fonts first (fastest)
    for sp in SYSTEM_DEVANAGARI_PATHS:
        if Path(sp).exists():
            if not bold_path.exists():
                import shutil
                try: shutil.copy2(sp, bold_path)
                except: pass
            if not reg_path.exists():
                try: shutil.copy2(sp, reg_path)
                except: pass
            break

    # Download if still missing
    for path, urls in [(bold_path, DEVANAGARI_FONT_URLS["bold"]),
                       (reg_path,  DEVANAGARI_FONT_URLS["regular"])]:
        if path.exists() and path.stat().st_size > 10000:
            continue
        for url in urls:
            try:
                log.info(f"Downloading font: {path.name} from {url[:60]}...")
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                if len(r.content) > 10000:
                    path.write_bytes(r.content)
                    log.info(f"✅ Font saved: {path.name} ({path.stat().st_size//1024}KB)")
                    break
            except Exception as e:
                log.warning(f"Font URL failed {url[:50]}: {e}")
                continue

    # Final check
    if bold_path.exists() and bold_path.stat().st_size > 10000:
        log.info("✅ Hindi fonts ready")
    else:
        log.warning("⚠️ Hindi font download failed — boxes may appear in text")


def _dl(url, dest):
    if Path(dest).exists() and Path(dest).stat().st_size > 10000:
        return
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        if len(r.content) > 10000:
            Path(dest).write_bytes(r.content)
    except Exception as e:
        log.warning(f"Font DL: {e}")


def _f(size, bold=False, lang="hi"):
    key = f"{lang}_{size}_{bold}"
    if key in FC:
        return FC[key]

    cands = []

    if lang == "hi":
        # Primary: downloaded Noto Devanagari
        bp = FONTS_DIR / "NotoSansDevanagari-Bold.ttf"
        rp = FONTS_DIR / "NotoSansDevanagari-Regular.ttf"

        # Ensure downloaded (lazy fallback if _ensure_hindi_fonts wasn't called)
        target = bp if bold else rp
        if not target.exists() or target.stat().st_size < 10000:
            urls = DEVANAGARI_FONT_URLS["bold" if bold else "regular"]
            for url in urls:
                _dl(url, target)
                if target.exists() and target.stat().st_size > 10000:
                    break

        cands = [target]

        # System Noto fallbacks
        for sp in SYSTEM_DEVANAGARI_PATHS:
            if Path(sp).exists():
                cands.append(Path(sp))

    # Latin fallbacks (won't render Hindi but better than nothing)
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
                FC[key] = f
                return f
            except Exception:
                continue

    log.warning(f"No valid font found for {lang} size {size} — using default")
    return ImageFont.load_default()


# ── Math ───────────────────────────────────────────────────────────────────────
def _a(v): return max(0,min(255,int(v)))
def _eo(x): return 1-(1-max(0,min(1,x)))**3
def _eio(x): x=max(0,min(1,x)); return 3*x*x-2*x*x*x
def _eb(x):
    x=max(0,min(1,x))
    if x<0.36: return 7.5625*x*x
    if x<0.72: return 7.5625*(x-0.54)**2+0.75
    if x<0.9:  return 7.5625*(x-0.81)**2+0.9375
    return 7.5625*(x-0.954)**2+0.984375
def _slide(t,start,dur=0.4): return _a(_eo(max(0,(t-start)/dur))*255) if t>=start else 0

def _is_latin(word: str) -> bool:
    """Check if word is primarily Latin/English (not Devanagari)."""
    latin = sum(1 for c in word if ord(c) < 256)
    return latin > len(word) * 0.5

def _wrap(text, fnt, max_w):
    words,lines,cur=text.split(),[],""
    for w in words:
        tt=(cur+" "+w).strip()
        if fnt.getbbox(tt)[2]<=max_w: cur=tt
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

def _txt_mixed(draw, x, y, text, size, col, a, bold=False, shadow=True):
    """
    Render text with automatic font switching per word.
    Hindi words → Noto Devanagari
    English/Latin words (NASA, DNA, numbers) → Liberation/DejaVu
    This eliminates rectangle boxes for mixed Hindi-English text.
    """
    hi_fnt = _f(size, bold=bold, lang="hi")
    en_fnt = _f(size, bold=bold, lang="en")
    cx = x
    for word in text.split():
        fnt = en_fnt if _is_latin(word) else hi_fnt
        word_with_space = word + " "
        if shadow:
            draw.text((cx+2, y+2), word_with_space, font=fnt,
                     fill=(0,0,0,_a(a*0.4)))
        draw.text((cx, y), word_with_space, font=fnt,
                 fill=(*col, _a(a)))
        cx += fnt.getbbox(word_with_space)[2]

def _txt_mixed_width(text, size, bold=False) -> int:
    """Measure width of mixed-language text."""
    hi_fnt = _f(size, bold=bold, lang="hi")
    en_fnt = _f(size, bold=bold, lang="en")
    w = 0
    for word in text.split():
        fnt = en_fnt if _is_latin(word) else hi_fnt
        w += fnt.getbbox(word + " ")[2]
    return w

# Alias — both names used across the codebase
_txt_mixed_w = _txt_mixed_width

def _wrap_mixed(text, size, max_w, bold=False):
    """Wrap mixed Hindi-English text correctly."""
    hi_fnt = _f(size, bold=bold, lang="hi")
    en_fnt = _f(size, bold=bold, lang="en")
    words,lines,cur,cur_w=[],[],"",0
    for word in text.split():
        fnt = en_fnt if _is_latin(word) else hi_fnt
        ww  = fnt.getbbox(word+" ")[2]
        if cur_w + ww <= max_w:
            cur   += word+" "
            cur_w += ww
        else:
            if cur: lines.append(cur.strip())
            cur   = word+" "
            cur_w = ww
    if cur.strip(): lines.append(cur.strip())
    return lines

def _txt(draw,x,y,text,fnt,col,a,shadow=True):
    if shadow: draw.text((x+2,y+2),text,font=fnt,fill=(0,0,0,_a(a*0.4)))
    draw.text((x,y),text,font=fnt,fill=(*col,_a(a)))

def _glass(draw,x1,y1,x2,y2,fc=(255,255,255),fa=20,sc=(255,255,255),sa=35,r=18):
    draw.rounded_rectangle([x1,y1,x2,y2],radius=r,fill=(*fc,fa),outline=(*sc,sa),width=1)

def _hair(draw,x1,y,x2,col,a):
    draw.rectangle([x1,y,x2,y+1],fill=(*col,_a(a)))

def _vignette(draw):
    for i in range(55):
        va=_a(190*(1-i/55)**2.5)
        draw.rectangle([i,i,W-i,H-i],outline=(0,0,0,va),width=6)


# ── Shared chrome ──────────────────────────────────────────────────────────────
def _chrome(draw,th,topic_key,t,dur,tags,follow_text):
    acc=th["acc"]; acc2=th["acc2"]; txt=th["txt"]; mut=th["mut"]
    BAR=96
    if t<0.5: bp=_eo(t/0.5); ty_t=int(-BAR+BAR*bp); ty_b=int(H-BAR*bp)
    else:     ty_t=0; ty_b=H-BAR
    draw.rectangle([0,ty_t,W,ty_t+BAR],fill=(0,0,0,252))
    draw.rectangle([0,ty_b,W,ty_b+BAR],fill=(0,0,0,252))
    ba=_slide(t,0.4,0.3)
    _hair(draw,0,ty_t+BAR,W,acc,ba); _hair(draw,0,ty_b-1,W,acc2,ba)

    # Progress bar
    pb_a=_slide(t,0.5,0.3); pb_y=ty_t+BAR+4; pb_w=int(W*(t/dur))
    draw.rectangle([0,pb_y,W,pb_y+4],fill=(*acc,_a(pb_a*0.18)))
    for px_ in range(0,pb_w,4):
        sh=0.65+0.35*(px_/max(pb_w,1))
        draw.rectangle([px_,pb_y,min(px_+4,W),pb_y+4],fill=(*acc,_a(pb_a*sh)))
    if 8<pb_w<W-8: draw.ellipse([pb_w-6,pb_y-2,pb_w+6,pb_y+6],fill=(*th["acc3"],pb_a))

    # Header
    ha=_slide(t,0.25,0.4)
    lf=_f(24,bold=True,lang="en")
    lb=THEMES.get(topic_key,{}).get("label","")
    draw.ellipse([PAD,ty_t+40,PAD+12,ty_t+52],fill=(*acc,_a(ha*0.3)))
    draw.ellipse([PAD+2,ty_t+42,PAD+10,ty_t+50],fill=(*acc,ha))
    _txt(draw,PAD+18,ty_t+30,lb,lf,acc,ha,shadow=False)
    brf=_f(20,lang="en"); brb=brf.getbbox("cosmos.capsule")
    _txt(draw,W-brb[2]-PAD,ty_t+34,"cosmos.capsule",brf,mut,_a(ha*0.7),shadow=False)

    # Tags
    tag_a=_slide(t,dur*0.72,0.4)
    if tag_a>0 and tags:
        tag_sz=24; tt=H-195
        _glass(draw,PAD-16,tt-8,W-PAD+16,tt+62,fc=(0,0,0),fa=55,sc=acc,sa=22,r=12)
        for ri,row in enumerate(["  ".join(tags[:3]),"  ".join(tags[3:6])]):
            if not row: continue
            lw_=_txt_mixed_width(row,tag_sz)
            rx_=(W-lw_)//2; ry_=tt+ri*30
            _txt_mixed(draw,rx_,ry_,row,tag_sz,acc,_a(tag_a*0.88))

    # CTA
    cta_a=_slide(t,dur*0.82,0.5)
    for i in range(BAR+20):
        draw.rectangle([0,ty_b+i,W,ty_b+i+1],fill=(0,0,0,_a(240*((i/(BAR+20))**1.8))))
    if cta_a>0:
        cf=_f(29,bold=True,lang="hi"); cb=cf.getbbox(follow_text)
        pulse=0.82+0.18*math.sin(t*4)
        cx_=(W-cb[2])//2; cy_=ty_b+(BAR-cb[3])//2-4
        draw.ellipse([cx_-22,cy_+8,cx_-12,cy_+18],fill=(*acc,_a(cta_a*pulse)))
        _txt(draw,cx_,cy_,follow_text,cf,acc,_a(cta_a*pulse))
        af=_f(24,bold=True,lang="en")
        draw.text((cx_+cb[2]+10,cy_+3),"↑",font=af,fill=(*acc2,_a(cta_a*pulse)))
    return ty_t,ty_b,BAR


# ══════════════════════════════════════════════════════════════════════════════
# MODE A: ILLUSTRATED — 3 scene frames with Ken Burns + text overlay
# ══════════════════════════════════════════════════════════════════════════════

def _illustrated_frame(scenes: list, hook: str, body: str, body_words: list,
                        topic_key: str, lang: str, follow_text: str,
                        tags: list, t: float, dur: float,
                        scene_times: list,
                        body_start_t: float = 5.0,
                        body_window: float = 8.0) -> np.ndarray:
    """
    Render illustrated reel frame.
    3 scenes, each shown for scene_dur seconds with Ken Burns effect.
    Text overlaid on top.
    """
    th  = THEMES.get(topic_key, THEMES["space"])
    acc = th["acc"]; acc2=th["acc2"]; txt=th["txt"]

    # Which scene are we in?
    scene_idx = 0
    scene_t   = t
    for i, (st, en) in enumerate(scene_times):
        if st <= t < en:
            scene_idx = i
            scene_t   = t - st
            break
    else:
        scene_idx = len(scenes) - 1
        scene_t   = t - scene_times[-1][0]

    scene_dur = scene_times[scene_idx][1] - scene_times[scene_idx][0]
    progress  = min(1.0, scene_t / max(scene_dur, 0.001))

    # Load scene image
    bg = scenes[min(scene_idx, len(scenes)-1)]

    # Ken Burns effect: each scene has different motion direction
    kb_patterns = [
        # (start_scale, end_scale, x_drift, y_drift)
        (1.0,  1.08,  0,    -30),   # Scene 1: zoom in, drift up
        (1.08, 1.0,   -20,   20),   # Scene 2: zoom out, drift left-down
        (1.0,  1.06,  30,    0),    # Scene 3: zoom in, drift right
    ]
    ks, ke, xd, yd = kb_patterns[scene_idx % 3]
    scale = ks + (ke - ks) * _eio(progress)
    nw = int(W * scale); nh = int(H * scale)
    zoomed = bg.resize((nw, nh), Image.LANCZOS)

    x_off = int((nw - W) // 2 + xd * _eio(progress))
    y_off = int((nh - H) // 2 + yd * _eio(progress))
    x_off = max(0, min(x_off, nw - W))
    y_off = max(0, min(y_off, nh - H))

    frame = zoomed.crop((x_off, y_off, x_off+W, y_off+H)).convert("RGBA")

    # Scene transition: fade between scenes
    if scene_t < 0.4 and scene_idx > 0:
        fade_a = _a(255 * _eo(scene_t / 0.4))
        frame  = Image.blend(
            Image.new("RGBA", (W, H), (0, 0, 0, 255)),
            frame, alpha=fade_a/255
        )
    elif scene_dur - scene_t < 0.4:
        fade_a = _a(255 * _eo((scene_dur - scene_t) / 0.4))
        frame  = Image.blend(
            frame,
            Image.new("RGBA", (W, H), (0, 0, 0, 255)),
            alpha=1 - fade_a/255
        )

    draw = ImageDraw.Draw(frame)

    # Vignette (lighter than animated — let the illustration shine)
    for i in range(40):
        va = _a(140*(1-i/40)**2.2)
        draw.rectangle([i,i,W-i,H-i],outline=(0,0,0,va),width=5)

    # Dark gradient at bottom for text readability
    grad_start = int(H * 0.55)
    for y in range(grad_start, H):
        alpha = _a(200 * ((y - grad_start) / (H - grad_start)) ** 1.4)
        draw.rectangle([0, y, W, y+1], fill=(0, 0, 0, alpha))

    # Dark gradient at top for header
    for y in range(200):
        alpha = _a(160 * (1 - y/200) ** 1.2)
        draw.rectangle([0, y, W, y+1], fill=(0, 0, 0, alpha))

    # ── Scene number indicator (small dots) ───────────────────────────────
    dot_y = int(H * 0.54)
    for di in range(len(scenes)):
        dx   = W//2 + (di - len(scenes)//2)*24
        is_c = di == scene_idx
        draw.ellipse([dx-5, dot_y-5, dx+5, dot_y+5],
                     fill=(*acc, 220 if is_c else 80))
        if is_c:
            draw.ellipse([dx-7, dot_y-7, dx+7, dot_y+7],
                         outline=(*acc, 150), width=1)

    # ── Hook text (shown from t=0) ─────────────────────────────────────────
    hook_a    = _slide(t, 0.3, 0.5)
    hook_size = 68
    hook_lines= _wrap_mixed(hook, hook_size, W-PAD*2-20, bold=True)
    hook_h    = len(hook_lines)*82
    hook_y    = int(H*0.58)

    if hook_a > 0:
        _glass(draw, PAD-20, hook_y-14, W-PAD+20, hook_y+hook_h+14,
               fc=(0,0,0), fa=_a(hook_a*0.65), sc=acc, sa=_a(hook_a*0.3), r=18)
        draw.rounded_rectangle([PAD-20, hook_y-14, PAD-17, hook_y+hook_h+14],
                               radius=2, fill=(*acc, _a(hook_a*0.9)))
        hy = hook_y
        for line in hook_lines:
            lw  = _txt_mixed_width(line, hook_size, bold=True)
            hx  = (W-lw)//2
            _txt_mixed(draw, hx, hy, line, hook_size, txt, hook_a, bold=True)
            hy += 82

    # ── Body text fades in after scene 1 ──────────────────────────────────
    body_a = _slide(t, body_start_t, 0.6)

    if body_a > 0:
        body_elapsed = max(0, t - body_start_t)
        n_words      = min(len(body_words),
                           int(body_elapsed/max(0.25, body_window/max(len(body_words),1)))+1)
        body_size = 36
        sls  = _wrap_mixed(" ".join(body_words[:n_words]), body_size, W-PAD*2-10)
        st_  = hook_y + hook_h + 20
        sh_  = len(sls)*48

        _glass(draw, PAD-16, st_-10, W-PAD+16, st_+sh_+10,
               fc=(0,0,0), fa=_a(body_a*0.6), sc=acc2, sa=_a(body_a*0.2), r=14)
        for li, sl in enumerate(sls):
            la_ = _slide(t, body_start_t+li*0.2, 0.35)
            lw_ = _txt_mixed_width(sl, body_size)
            _txt_mixed(draw, (W-lw_)//2, st_+li*48, sl, body_size, txt, la_)

    # Chrome
    _chrome(draw, th, topic_key, t, dur, tags, follow_text)

    return np.array(frame.convert("RGB"))


# ══════════════════════════════════════════════════════════════════════════════
# MODE B: ANIMATED BACKGROUNDS (kinetic / documentary / cartoon)
# ══════════════════════════════════════════════════════════════════════════════

def _draw_animated_bg(img, th, t, style):
    draw = ImageDraw.Draw(img)
    acc  = th["acc"]; acc2=th["acc2"]
    if style=="cosmos":
        rng=random.Random(42)
        for _ in range(180):
            sx=rng.randint(0,W); sy=rng.randint(0,H); ss=rng.choice([1,1,2,2,3])
            pulse=0.4+0.6*math.sin(t*rng.uniform(0.5,2.0)+sx*0.05)
            draw.ellipse([sx-ss,sy-ss,sx+ss,sy+ss],fill=(255,255,255,_a(200*pulse)))
        cx,cy=W//2,H//3
        for arm in range(2):
            for i in range(80):
                angle=i*0.15+arm*math.pi+t*0.08; r_=i*5
                px=cx+int(r_*math.cos(angle)); py=cy+int(r_*math.sin(angle)*0.5)
                if 0<=px<W and 0<=py<H:
                    draw.ellipse([px-2,py-2,px+2,py+2],fill=(*acc,_a(100*(1-i/80))))
    elif style=="neural":
        rng2=random.Random(7)
        nodes=[(rng2.randint(80,W-80),rng2.randint(80,H-80)) for _ in range(18)]
        for i,(nx,ny) in enumerate(nodes):
            pulse=0.5+0.5*math.sin(t*1.2+i*0.7); r_=int(8+6*pulse)
            draw.ellipse([nx-r_,ny-r_,nx+r_,ny+r_],fill=(*acc,_a(120*pulse)))
            dists=sorted(range(len(nodes)),key=lambda j:abs(nodes[j][0]-nx)+abs(nodes[j][1]-ny))
            for j in dists[1:4]:
                mx,my=nodes[j]; lp=0.3+0.3*math.sin(t*0.8+i+j)
                draw.line([(nx,ny),(mx,my)],fill=(*acc2,_a(40*lp)),width=1)
    elif style=="explosion":
        for ring in range(5):
            phase=(t*0.8+ring*0.4)%3.0; r_=int(phase*300); fade=max(0,1-phase/3.0)
            if r_>0: draw.ellipse([W//2-r_,H//2-r_,W//2+r_,H//2+r_],outline=(*acc,_a(80*fade)),width=3)
        rng3=random.Random(99)
        for _ in range(30):
            angle=rng3.uniform(0,2*math.pi); speed=rng3.uniform(50,200)
            phase2=(t*0.5+rng3.random())%1.0
            px=W//2+int(math.cos(angle)*speed*phase2); py=H//2+int(math.sin(angle)*speed*phase2)
            draw.ellipse([px-3,py-3,px+3,py+3],fill=(*acc,_a(180*(1-phase2))))
    elif style=="lab":
        for bub in range(20):
            rng4=random.Random(bub*13); bx=rng4.randint(50,W-50)
            by_=int((H+(t*60+bub*95)%(H+100))%(H+100))-50; br=rng4.randint(6,20)
            draw.ellipse([bx-br,by_-br,bx+br,by_+br],fill=(*acc,_a(rng4.randint(30,80))))
    elif style=="earth":
        for wi in range(8):
            y_off=wi*250-100
            pts=[(x,y_off+int(60*math.sin(x*0.012+t*0.4+wi*0.8))) for x in range(0,W+1,12)]
            if len(pts)>=2: draw.line(pts,fill=(*acc,_a(25+wi*5)),width=2)

def _draw_gradient_bg(img, th, t):
    pix=img.load(); c1,c2,c3=th["bg1"],th["bg2"],th["bg3"]
    shift=(t*0.02)%1.0
    for y in range(H):
        fy=((y/H)+shift)%1.0
        if fy<0.5:
            fr=fy/0.5; c_a,c_b=c1,c2
        else:
            fr=(fy-0.5)/0.5; c_a,c_b=c2,c3
        r_=int(c_a[0]+(c_b[0]-c_a[0])*fr)
        g_=int(c_a[1]+(c_b[1]-c_a[1])*fr)
        b_=int(c_a[2]+(c_b[2]-c_a[2])*fr)
        for x in range(W): pix[x,y]=(r_,g_,b_,255)

def _kinetic_frame(bg,hook,body,body_words,topic_key,lang,follow_text,tags,t,dur,
                   hook_word_interval=0.35,body_start_t=5.5,body_window=None):
    th=THEMES.get(topic_key,THEMES["space"]); acc=th["acc"]; acc2=th["acc2"]; txt=th["txt"]
    base=Image.new("RGBA",(W,H)); _draw_gradient_bg(base,th,t)
    draw=ImageDraw.Draw(base); _draw_animated_bg(base,th,t,th["bg_style"])
    rng=random.Random(77)
    for i in range(6):
        ex_=rng.randint(PAD,W-PAD); speed=rng.uniform(40,100); offset=rng.random()*10
        ey_=int(H-((t*speed+offset*100+i*120)%(H+80)))
        if -40<ey_<H+20:
            try:
                ef=_f(rng.randint(28,40),lang="en")
                draw.text((ex_,ey_),th["emoji_pool"][i%len(th["emoji_pool"])],font=ef,fill=(255,255,255,_a(120)))
            except: pass
    _vignette(draw)
    ty_t,ty_b,BAR=_chrome(draw,th,topic_key,t,dur,tags,follow_text)
    hook_sz=76; hw=hook.split()
    hs=0.7
    bw_=body_window if body_window else dur*0.45
    shown=[]
    for wi,word in enumerate(hw):
        ws=hs+wi*hook_word_interval
        if t<ws: break
        shown.append((word,min(1.0,(t-ws)/0.28)))
    # Use mixed wrap for correct width calculation
    tls=_wrap_mixed(" ".join(w for w,_ in shown),hook_sz,W-PAD*2-20,bold=True)
    ht=len(tls)*88; cy_=H//2-ht//2-50
    _glass(draw,PAD-28,cy_-24,W-PAD+28,cy_+ht+24,fc=(0,0,0),fa=70,sc=acc,sa=35,r=26)
    draw.rounded_rectangle([PAD-28,cy_-24,PAD-24,cy_+ht+24],radius=2,fill=(*acc,_a(min(255,t*400))))
    hy=cy_; ss=0
    for line in tls:
        wds=line.split()
        lw_total=_txt_mixed_width(line,hook_sz,bold=True)
        cx_=(W-lw_total)//2
        for word in wds:
            if ss<len(shown):
                _,prog=shown[ss]
                bounce=int(18*(1-_eb(prog)))
                sz=max(32,int(hook_sz*_eo(prog)))
                col_=acc if ss==len(shown)-1 else txt
                en_f=_f(sz,bold=True,lang="en")
                hi_f=_f(sz,bold=True,lang="hi")
                wf=en_f if _is_latin(word) else hi_f
                wp=word+" "
                if prog>0:
                    draw.text((cx_+2,hy-bounce+2),wp,font=wf,fill=(0,0,0,_a(prog*100)))
                    draw.text((cx_,hy-bounce),wp,font=wf,fill=(*col_,_a(prog*255)))
                cx_+=wf.getbbox(wp)[2]
            ss+=1
        hy+=88
    if t>body_start_t:
        be=t-body_start_t
        nw=min(len(body_words),int(be/max(0.25,bw_/max(len(body_words),1)))+1)
        body_sz=38
        sls=_wrap_mixed(" ".join(body_words[:nw]),body_sz,W-PAD*2-10)
        sth=len(sls)*52; sto=cy_+ht+35
        _glass(draw,PAD-20,sto-12,W-PAD+20,sto+sth+12,fc=(0,0,0),fa=60,sc=acc2,sa=20,r=14)
        for li,sl in enumerate(sls):
            la=_slide(t,body_start_t+li*0.25,0.4)
            lw_=_txt_mixed_width(sl,body_sz)
            _txt_mixed(draw,(W-lw_)//2,sto+li*52,sl,body_sz,txt,la)
    return np.array(base.convert("RGB"))

def _documentary_frame(bg,hook,body,body_words,topic_key,lang,follow_text,tags,t,dur,
                       hook_word_interval=0.35,body_start_t=5.5,body_window=None):
    th=THEMES.get(topic_key,THEMES["space"]); acc=th["acc"]; acc2=th["acc2"]; txt=th["txt"]
    base=Image.new("RGBA",(W,H)); _draw_gradient_bg(base,th,t)
    draw=ImageDraw.Draw(base); _draw_animated_bg(base,th,t,th["bg_style"]); _vignette(draw)
    ty_t,ty_b,BAR=_chrome(draw,th,topic_key,t,dur,tags,follow_text)
    cd=dur/3; ch=min(2,int(t/cd)); cp=(t%cd)/cd
    ca=_a(_eo(min(1,cp*3))*255); fo=_a((1-_eo(max(0,(cp-0.8)/0.2)))*255) if cp>0.8 else 255
    if ch==0:
        ef=_f(90,lang="en"); ep=th["emoji_pool"][0]; pulse=0.85+0.15*math.sin(t*2.5)
        eb=ef.getbbox(ep); draw.text(((W-eb[2])//2,H//2-200),ep,font=ef,fill=(255,255,255,_a(ca*fo/255*pulse)))
        lb=THEMES.get(topic_key,{}).get("label","")
        lw_=_txt_mixed_width(lb,38,bold=True); lx=(W-lw_)//2
        _glass(draw,lx-20,H//2-60,lx+lw_+20,H//2+20,fc=acc,fa=30,sc=acc,sa=60,r=20)
        _txt_mixed(draw,lx,H//2-55,lb,38,acc,_a(ca*fo/255),bold=True)
        lw=int((W-PAD*4)*_eo(min(1,cp*2.5))); _hair(draw,PAD*2,H//2+40,PAD*2+lw,acc,ca)
    elif ch==1:
        hook_sz=66; hls=_wrap_mixed(hook,hook_sz,W-PAD*2-20,bold=True)
        hh=len(hls)*82; hy=H//2-hh//2-10
        _glass(draw,PAD-24,hy-18,W-PAD+24,hy+hh+18,fc=(0,0,0),fa=68,sc=acc,sa=30,r=22)
        draw.rounded_rectangle([PAD-24,hy-18,PAD-21,hy+hh+18],radius=2,fill=(*acc,_a(ca*fo/255)))
        hy2=hy
        for line in hls:
            lw_=_txt_mixed_width(line,hook_sz,bold=True)
            _txt_mixed(draw,(W-lw_)//2,hy2,line,hook_sz,txt,_a(ca*fo/255),bold=True)
            hy2+=82
    elif ch==2:
        body_sz=40; sls=_wrap_mixed(body,body_sz,W-PAD*2-10)
        st=H//3; sh=len(sls)*56
        _glass(draw,PAD-20,st-16,W-PAD+20,st+sh+16,fc=(0,0,0),fa=64,sc=acc2,sa=24,r=16)
        nr=min(len(sls),int(cp*len(sls)*1.8)+1)
        for li in range(nr):
            if li>=len(sls): break
            la=_slide(t,ch*cd+li*0.28,0.4)
            lw_=_txt_mixed_width(sls[li],body_sz)
            _txt_mixed(draw,(W-lw_)//2,st+li*56,sls[li],body_sz,txt,_a(la*fo/255))
    return np.array(base.convert("RGB"))

def _cartoon_frame(bg,hook,body,body_words,topic_key,lang,follow_text,tags,t,dur,
                   hook_word_interval=0.35,body_start_t=5.5,body_window=None):
    th=THEMES.get(topic_key,THEMES["space"]); acc=th["acc"]; acc2=th["acc2"]; txt=th["txt"]
    base=Image.new("RGBA",(W,H)); _draw_gradient_bg(base,th,t)
    draw=ImageDraw.Draw(base); _draw_animated_bg(base,th,t,th["bg_style"])
    # Emojis
    rng=random.Random(77)
    for i in range(8):
        ex_=rng.randint(PAD,W-PAD); sp=rng.uniform(40,100)
        ey_=int(H-((t*sp+rng.random()*1000+i*120)%(H+80)))
        if -40<ey_<H+20:
            try:
                ef=_f(rng.randint(28,44),lang="en")
                draw.text((ex_,ey_),th["emoji_pool"][i%len(th["emoji_pool"])],
                         font=ef,fill=(255,255,255,_a(130)))
            except: pass
    # Floor
    fy=int(H*0.72)
    for fx in range(0,W,4):
        fa=_a(40*(1-abs(fx-W//2)/(W//2)))
        draw.rectangle([fx,fy,fx+3,fy+2],fill=(*acc,fa))
    # Character (simplified for speed)
    wip=min(1.0,t/1.8); cx=W//2; cy=fy-10; sz=90; bob=int(8*math.sin(t*2.8))
    cx_anim=int(W+(cx-W)*_eo(wip)); cy_=cy+bob
    shad_a=_a(60*min(1.0,wip*2))
    draw.ellipse([cx_anim-sz//2,cy_+sz-10,cx_anim+sz//2,cy_+sz+10],fill=(0,0,0,shad_a))
    bc=th.get("char_body",acc)
    draw.rounded_rectangle([cx_anim-sz//2+5,cy_-sz//3,cx_anim+sz//2-5,cy_+sz//2],radius=28,fill=(*bc,235))
    hr=sz//2+5
    draw.ellipse([cx_anim-hr,cy_-sz-hr*2+20,cx_anim+hr,cy_-sz+hr*2-30],fill=(*bc,238))
    ey_=cy_-sz-12; blink=t%4.5>4.1
    for ex_ in [cx_anim-18,cx_anim+18]:
        draw.ellipse([ex_-7,ey_-7,ex_+7,ey_+(3 if blink else 7)],fill=(255,255,255,245))
        if not blink:
            draw.ellipse([ex_-3,ey_-3,ex_+3,ey_+3],fill=(*acc,255))
            draw.ellipse([ex_-1,ey_-2,ex_+1,ey_+2],fill=(10,10,30,240))
    draw.arc([cx_anim-12,ey_+10,cx_anim+12,ey_+24],start=0,end=180,fill=(30,15,10,200),width=3)
    # Speech bubble
    bp=max(0.0,min(1.0,(t-2.1)/0.6))
    if bp>0:
        hook_sz=58
        hls=_wrap_mixed(hook,hook_sz,W-PAD*2-60,bold=True)
        bw=W-PAD*2; bh=max(160,len(hls)*70+40); bx=PAD; by_=int(H*0.12)
        sc=_eb(min(1.0,bp*1.5))
        if sc>0.05:
            cxb=bx+bw//2; cyb=by_+bh//2; sw=int(bw*sc); sh=int(bh*sc)
            sx1=cxb-sw//2; sy1=cyb-sh//2; sx2=cxb+sw//2; sy2=cyb+sh//2
            draw.rounded_rectangle([sx1+5,sy1+5,sx2+5,sy2+5],radius=22,fill=(0,0,0,_a(55*sc)))
            draw.rounded_rectangle([sx1,sy1,sx2,sy2],radius=22,fill=(*acc,_a(210*sc)),outline=(255,255,255,_a(75*sc)),width=2)
            pts=[(cxb-15,sy2),(cxb+15,sy2),(cxb,sy2+28)]
            if sc>0.5: draw.polygon(pts,fill=(*acc,_a(210*sc)))
            if sc>0.7:
                ta=_a(255*(sc-0.7)/0.3); lh=int(sh*0.28)
                th_total=len(hls)*lh; ty_=cyb-th_total//2
                for li,line in enumerate(hls):
                    lp=max(0,bp-li*0.15)
                    bounce=int(12*(1-min(1,lp*3)))*(-1 if li%2==0 else 1)
                    lw_=_txt_mixed_width(line,hook_sz,bold=True)
                    lx_=cxb-lw_//2
                    # Shadow
                    _txt_mixed(draw,lx_+2,ty_+li*lh+2+bounce,line,hook_sz,(0,0,0),_a(ta*0.35),bold=True,shadow=False)
                    # Text
                    _txt_mixed(draw,lx_,ty_+li*lh+bounce,line,hook_sz,(255,255,255),_a(ta),bold=True,shadow=False)
    # Body text
    bst=2.1+0.6+0.5; ba=_slide(t,bst,0.6)
    if ba>0:
        be2=max(0,t-bst); bwnd=body_window if body_window else dur*0.45
        nw=min(len(body_words),int(be2/max(0.25,bwnd/max(len(body_words),1)))+1)
        body_sz=36
        sls=_wrap_mixed(" ".join(body_words[:nw]),body_sz,W-PAD*2-20)
        st=fy+30; sh_=len(sls)*52; sl_=int(40*(1-_eo(min(1,(t-bst)/0.4))))
        _glass(draw,PAD-16,st-14-sl_,W-PAD+16,st+sh_+14-sl_,fc=(0,0,0),fa=72,sc=acc,sa=28,r=18)
        for li,sl in enumerate(sls):
            la=_slide(t,bst+li*0.2,0.35)
            lw_=_txt_mixed_width(sl,body_sz)
            _txt_mixed(draw,(W-lw_)//2,st+li*52-sl_,sl,body_sz,txt,la)
    _vignette(draw)
    _chrome(draw,th,topic_key,t,dur,tags,follow_text)
    return np.array(base.convert("RGB"))


# ══════════════════════════════════════════════════════════════════════════════
# SINGLE REEL — CAROUSEL VISUAL STYLE
# Full photo background + centered text overlay. Clean and premium.
# ══════════════════════════════════════════════════════════════════════════════

def _single_carousel_frame(bg_photo, hook, body, body_words,
                            topic_key, lang, follow_text, tags,
                            t, dur,
                            body_start_t=5.0,
                            body_window=8.0,
                            fact_data=None) -> np.ndarray:
    th   = THEMES.get(topic_key, THEMES["space"])
    acc  = th["acc"]; acc2=th["acc2"]; acc3=th["acc3"]; txt=th["txt"]
    progress = t / dur

    # ── Full-bleed background + Ken Burns ─────────────────────────────────
    scale = 1.0 + 0.04 * progress
    nw, nh = int(W*scale), int(H*scale)
    bg = bg_photo.resize((nw, nh), Image.LANCZOS)
    lf = (nw-W)//2; tp = (nh-H)//2
    bg = bg.crop((lf, tp, lf+W, tp+H)).convert("RGB")
    bg = ImageEnhance.Color(bg).enhance(0.80)
    bg = ImageEnhance.Brightness(bg).enhance(0.55)
    frame = bg.convert("RGBA")

    # Dark center overlay for text contrast
    overlay = Image.new("RGBA", (W,H), (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    for y in range(H):
        fy    = y / H
        dist  = abs(fy - 0.52)
        alpha = _a(170 * max(0, 1 - dist*2.0))
        od.rectangle([0,y,W,y+1], fill=(0,0,0,alpha))
    frame = Image.alpha_composite(frame, overlay)
    draw  = ImageDraw.Draw(frame)
    _vignette(draw)

    # ── Top accent bar + progress ──────────────────────────────────────────
    bar_a = _slide(t, 0.2, 0.3)
    draw.rectangle([0, 0, W, 5], fill=(*acc, bar_a))
    pb_w = int(W * progress)
    draw.rectangle([0, 5, W, 9], fill=(*acc, _a(bar_a*0.2)))
    if pb_w > 0:
        draw.rectangle([0, 5, pb_w, 9], fill=(*acc, bar_a))
    if 6 < pb_w < W-6:
        draw.ellipse([pb_w-5, 3, pb_w+5, 11], fill=(*acc3, bar_a))

    # ── Topic label + brand ────────────────────────────────────────────────
    hdr_a   = _slide(t, 0.2, 0.4)
    lbl_fnt = _f(24, bold=True, lang="en")
    lbl     = THEMES.get(topic_key, {}).get("label", "")
    draw.text((PAD, 20), lbl, font=lbl_fnt, fill=(*acc, hdr_a))
    brand_fnt = _f(22, lang="en")
    brand_bb  = brand_fnt.getbbox("cosmos.capsule")
    draw.text((W-brand_bb[2]-PAD, 22), "cosmos.capsule",
              font=brand_fnt, fill=(180,180,180,hdr_a))

    # ── Exam label badge (only for examfacts topic) ────────────────────────
    exam_type = fact_data.get("exam_type", "") if isinstance(fact_data, dict) else ""
    if topic_key == "examfacts" and exam_type:
        exam_fnt  = _f(22, bold=True, lang="en")
        exam_text = f"📌 {exam_type} में पूछा गया"
        exam_bb   = exam_fnt.getbbox(exam_text)
        ex_w      = exam_bb[2] + 24
        ex_h      = 36
        ex_x      = (W - ex_w) // 2
        ex_y      = 60
        # Pill badge
        draw.rounded_rectangle([ex_x, ex_y, ex_x+ex_w, ex_y+ex_h],
                               radius=18,
                               fill=(*acc, _a(hdr_a*0.25)),
                               outline=(*acc, _a(hdr_a*0.8)),
                               width=1)
        draw.text((ex_x+12, ex_y+7), exam_text,
                  font=exam_fnt, fill=(*acc, hdr_a))

    # ── Calculate block layout ─────────────────────────────────────────────
    hook_sz  = 60
    h_lines  = _wrap_mixed(hook, hook_sz, W-PAD*2, bold=True)
    h_total  = len(h_lines) * 76
    d_size   = 38
    d_lines_full = _wrap_mixed(body, d_size, W-PAD*2)
    d_total  = len(d_lines_full) * 52
    gap      = 28
    block_h  = h_total + gap + 2 + gap + d_total
    start_y  = H//2 - block_h//2

    # ── Hook card ─────────────────────────────────────────────────────────
    hook_a = _slide(t, 0.4, 0.5)
    if hook_a > 0:
        _glass(draw, PAD-20, start_y-18, W-PAD+20, start_y+h_total+18,
               fc=(0,0,0), fa=_a(hook_a*0.65), sc=acc, sa=_a(hook_a*0.3), r=18)
        draw.rounded_rectangle([PAD-20, start_y-18, PAD-17, start_y+h_total+18],
                               radius=2, fill=(*acc, _a(hook_a*0.9)))
        hy = start_y
        for line in h_lines:
            lw_ = _txt_mixed_w(line, hook_sz, bold=True)
            lx_ = (W-lw_)//2
            draw.text((lx_+2, hy+2), "", fill=(0,0,0,0))  # placeholder
            _txt_mixed(draw, lx_+2, hy+2, line, hook_sz,
                       (0,0,0,_a(hook_a*0.4)), bold=True, shadow=False)
            _txt_mixed(draw, lx_, hy, line, hook_sz,
                       (*acc, _a(hook_a)), bold=True, shadow=False)
            hy += 76

    # ── Divider ────────────────────────────────────────────────────────────
    div_y = start_y + h_total + gap
    div_a = _slide(t, 0.8, 0.3)
    div_w = int((W-PAD*4) * _eo(min(1, max(0,(t-0.8)/0.5))))
    if div_w > 0:
        draw.rectangle([W//2-div_w//2, div_y, W//2+div_w//2, div_y+2],
                       fill=(*acc, _a(div_a*0.6)))

    # ── Body word-by-word ─────────────────────────────────────────────────
    body_a = _slide(t, body_start_t, 0.5)
    if body_a > 0:
        elapsed = max(0, t - body_start_t)
        n_words = min(len(body_words),
                      int(elapsed/max(0.25,body_window/max(len(body_words),1)))+1)
        sls  = _wrap_mixed(" ".join(body_words[:n_words]), d_size, W-PAD*2)
        sh_  = len(sls) * 52
        sy_  = div_y + gap
        _glass(draw, PAD-16, sy_-12, W-PAD+16, sy_+sh_+12,
               fc=(0,0,0), fa=_a(body_a*0.55), sc=acc2, sa=_a(body_a*0.2), r=14)
        for li, sl in enumerate(sls):
            la_ = _slide(t, body_start_t+li*0.2, 0.35)
            lw_ = _txt_mixed_w(sl, d_size)
            _txt_mixed(draw, (W-lw_)//2, sy_+li*52, sl,
                       d_size, (*txt, _a(la_)))

    # ── Hashtags ──────────────────────────────────────────────────────────
    tag_a = _slide(t, dur*0.72, 0.4)
    if tag_a > 0 and tags:
        tag_sz  = 22; tag_top = H-195
        _glass(draw, PAD-16, tag_top-8, W-PAD+16, tag_top+58,
               fc=(0,0,0), fa=55, sc=acc, sa=22, r=12)
        for ri, row in enumerate(["  ".join(tags[:3]), "  ".join(tags[3:6])]):
            if not row: continue
            lw_ = _txt_mixed_w(row, tag_sz)
            _txt_mixed(draw, (W-lw_)//2, tag_top+ri*28, row,
                       tag_sz, (*acc, _a(tag_a*0.88)))

    # ── Bottom CTA ────────────────────────────────────────────────────────
    cta_a = _slide(t, dur*0.82, 0.5)
    draw.rectangle([0, H-72, W, H], fill=(0,0,0,200))
    draw.rectangle([0, H-72, W, H-70], fill=(*acc, _a(cta_a*0.5)))
    if cta_a > 0:
        cta_fnt = _f(28, bold=True, lang="hi")
        cta_bb  = cta_fnt.getbbox(follow_text)
        pulse   = 0.85 + 0.15*math.sin(t*4)
        cx_     = (W-cta_bb[2])//2
        draw.text((cx_+2, H-52), follow_text, font=cta_fnt,
                  fill=(0,0,0,_a(cta_a*0.4)))
        draw.text((cx_, H-52), follow_text, font=cta_fnt,
                  fill=(*acc, _a(cta_a*pulse)))

    return np.array(frame.convert("RGB"))


# ══════════════════════════════════════════════════════════════════════════════
# VIDEO CREATOR
# ══════════════════════════════════════════════════════════════════════════════

class VideoCreator:
    def create_reel(self, image_path: Path, music_path: Path,
                    fact_data: dict, topic: dict,
                    lang: str, output_dir: Path,
                    reel_style: str = "illustrated",
                    duration: int = 20,
                    music_volume: float = 0.40,
                    scene_paths: list = None,
                    narr_duration: float = 0.0) -> Path:

        log.info(f"🎬 [{reel_style.upper()}] {duration}s | narr: {narr_duration:.1f}s…")

        # Pre-download Hindi fonts before any rendering
        _ensure_hindi_fonts()

        import config as cfg
        topic_key = "space"
        for k,v in cfg.TOPICS.items():
            if v.get("name")==topic.get("name") or v.get("name_hi")==topic.get("name_hi"):
                topic_key=k; break

        hook        = fact_data["hook"]
        body        = fact_data["body"]
        body_words  = body.split()
        follow_text = LANGUAGES["hi"]["follow_text"]
        tags        = VIDEO_TAGS.get(topic_key, ["#cosmoscapsule"])

        # Word reveal timing — sync to narration if available
        # narration starts at 0.3s (audio mixer offset)
        narr_start  = 0.3
        hook_words  = hook.split()
        body_words_ = body.split()

        if narr_duration > 1.0:
            # Sync to actual speech: split narr_duration between hook and body
            # Hook takes ~40% of speech time, body takes ~60%
            hook_speech_dur = narr_duration * 0.40
            body_speech_dur = narr_duration * 0.60
            # Word interval for hook
            hook_word_interval = hook_speech_dur / max(len(hook_words), 1)
            # Body starts after hook speech + small pause
            body_start_t = narr_start + hook_speech_dur + 0.3
            body_window  = body_speech_dur
        else:
            # No narration — use fixed timing spread across reel duration
            hook_word_interval = 0.35
            body_start_t       = min(duration * 0.35, 5.5)
            body_window        = duration * 0.45

        log.info(f"  Word timing: hook_interval={hook_word_interval:.2f}s body_start={body_start_t:.1f}s")

        if reel_style == "illustrated" and scene_paths and len(scene_paths) == 3:
            scenes = []
            for sp in scene_paths:
                try:
                    scenes.append(Image.open(sp).convert("RGB"))
                except Exception:
                    scenes.append(Image.new("RGB",(W,H),(10,10,30)))

            scene_dur   = duration / 3
            scene_times = [(i*scene_dur, (i+1)*scene_dur) for i in range(3)]

            def make_frame(t):
                return _illustrated_frame(
                    scenes, hook, body, body_words,
                    topic_key, lang, follow_text, tags,
                    t, duration, scene_times,
                    body_start_t=body_start_t,
                    body_window=body_window,
                )
        else:
            # All animated styles now use carousel visual style:
            # full photo background + centered text overlay
            bg = (Image.open(image_path).convert("RGB")
                  if image_path and image_path.exists()
                  else Image.new("RGB",(W,H),(10,10,30)))

            def make_frame(t):
                return _single_carousel_frame(
                    bg, hook, body, body_words,
                    topic_key, lang, follow_text, tags,
                    t, duration,
                    body_start_t=body_start_t,
                    body_window=body_window,
                    fact_data=fact_data,
                )

        clip = VideoClip(make_frame, duration=duration).set_fps(REEL_FPS)
        clip = fadein(clip, min(0.4, duration*0.05))
        clip = fadeout(clip, min(0.6, duration*0.06))

        try:
            actual_dur = AudioFileClip(str(music_path)).duration
            music_dur  = min(duration, actual_dur)
        except Exception:
            music_dur  = duration

        audio = (AudioFileClip(str(music_path))
                 .subclip(0, music_dur)
                 .audio_fadeout(min(2.5, duration*0.15))
                 .volumex(music_volume))
        clip = clip.set_audio(audio)

        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        cat_slug = (fact_data.get("fact_category",topic.get("name",""))[:15]
                    .replace(" ","_").lower())
        out_path = output_dir/f"reel_{cat_slug}_{lang}_{reel_style}_{ts}.mp4"

        log.info(f"💾 Writing → {out_path.name}")
        clip.write_videofile(
            str(out_path),
            codec="libx264", audio_codec="aac",
            fps=REEL_FPS, preset="fast",
            bitrate="4500k", audio_bitrate="192k",
            ffmpeg_params=["-vf",f"scale={W}:{H}"],
            logger=None,
        )
        log.info(f"✅ {out_path.stat().st_size/1e6:.1f} MB")
        return out_path
