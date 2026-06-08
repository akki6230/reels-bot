"""
src/video.py — Multi-style premium reel renderer.

3 randomly selected styles:
  1. KINETIC   — words fly in one by one, scale, bounce, pop
  2. DOCUMENTARY — chapter sections with title cards, elegant
  3. CARTOON   — geometric mascot character + bouncy animations

All styles share:
  - Cinematic letterbox bars
  - Progress bar
  - Hashtag strip
  - Follow CTA
  - Per-topic color themes
"""

import math
import random
import logging
from pathlib import Path
from datetime import datetime

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from moviepy.editor import VideoClip, AudioFileClip
from moviepy.video.fx.all import fadein, fadeout

from config import REEL_WIDTH, REEL_HEIGHT, REEL_FPS, MUSIC_VOLUME, LANGUAGES

log       = logging.getLogger(__name__)
W, H      = REEL_WIDTH, REEL_HEIGHT
PAD       = 68
ROOT      = Path(__file__).parent.parent
FONTS_DIR = ROOT / "fonts"
FONTS_DIR.mkdir(exist_ok=True)

# ── Themes ─────────────────────────────────────────────────────────────────────
THEMES = {
    "space":     {"acc": (120,200,255), "acc2": (180,130,255), "txt": (230,242,255),
                  "bg":  (4,8,22),      "mut":  (140,170,210), "grad": [(4,8,22),(8,15,40),(12,20,55)]},
    "history":   {"acc": (220,175,85),  "acc2": (190,130,55),  "txt": (255,245,220),
                  "bg":  (20,12,4),     "mut":  (200,170,120), "grad": [(20,12,4),(35,20,8),(50,30,10)]},
    "geography": {"acc": (75,215,125),  "acc2": (45,175,90),   "txt": (215,255,230),
                  "bg":  (4,18,8),      "mut":  (130,200,155), "grad": [(4,18,8),(8,30,15),(12,45,22)]},
    "science":   {"acc": (185,105,255), "acc2": (130,70,220),  "txt": (238,220,255),
                  "bg":  (12,4,24),     "mut":  (165,135,210), "grad": [(12,4,24),(20,8,40),(30,12,55)]},
    "sports":    {"acc": (255,205,45),  "acc2": (255,155,25),  "txt": (255,252,220),
                  "bg":  (8,16,4),      "mut":  (200,190,130), "grad": [(8,16,4),(15,25,8),(22,38,10)]},
    "worldnews": {"acc": (255,85,70),   "acc2": (220,55,45),   "txt": (255,232,228),
                  "bg":  (22,4,4),      "mut":  (210,155,148), "grad": [(22,4,4),(38,8,8),(55,12,10)]},
}

TOPIC_LABELS = {
    "space":     {"en": "SPACE & UNIVERSE",  "hi": "अंतरिक्ष और ब्रह्मांड"},
    "history":   {"en": "WORLD HISTORY",     "hi": "विश्व इतिहास"},
    "geography": {"en": "GEOGRAPHY",         "hi": "भूगोल"},
    "science":   {"en": "SCIENCE FACTS",     "hi": "विज्ञान तथ्य"},
    "sports":    {"en": "SPORTS NEWS",       "hi": "खेल समाचार"},
    "worldnews": {"en": "WORLD NEWS",        "hi": "विश्व समाचार"},
}

VIDEO_TAGS = {
    "space_en":     ["#space","#universe","#NASA","#spacefacts","#didyouknow","#cosmoscapsule"],
    "space_hi":     ["#अंतरिक्ष","#ब्रह्मांड","#विज्ञान","#तथ्य","#इसरो","#cosmoscapsule"],
    "history_en":   ["#history","#ancienthistory","#historyfacts","#didyouknow","#civilization","#cosmoscapsule"],
    "history_hi":   ["#इतिहास","#प्राचीनइतिहास","#तथ्य","#ज्ञान","#सभ्यता","#cosmoscapsule"],
    "geography_en": ["#geography","#earthfacts","#nature","#travel","#amazingearth","#cosmoscapsule"],
    "geography_hi": ["#भूगोल","#पृथ्वी","#प्रकृति","#यात्रा","#तथ्य","#cosmoscapsule"],
    "science_en":   ["#science","#sciencefacts","#physics","#biology","#mindblown","#cosmoscapsule"],
    "science_hi":   ["#विज्ञान","#विज्ञानतथ्य","#भौतिकी","#जीवविज्ञान","#तथ्य","#cosmoscapsule"],
    "sports_en":    ["#sports","#cricket","#IPL","#football","#athlete","#cosmoscapsule"],
    "sports_hi":    ["#खेल","#क्रिकेट","#आईपीएल","#फुटबॉल","#खिलाड़ी","#cosmoscapsule"],
    "worldnews_en": ["#worldnews","#breakingnews","#NASA","#ISRO","#geopolitics","#cosmoscapsule"],
    "worldnews_hi": ["#विश्वसमाचार","#ताजाखबर","#राजनीति","#नासा","#इसरो","#cosmoscapsule"],
}

# ── Font helpers ───────────────────────────────────────────────────────────────
FONT_CACHE: dict = {}

def _dl_font(url, dest):
    if Path(dest).exists(): return
    try:
        r = requests.get(url, timeout=30); r.raise_for_status()
        Path(dest).write_bytes(r.content)
    except Exception as e: log.warning(f"Font DL: {e}")

def _font(size, bold=False, lang="en"):
    key = f"{lang}_{size}_{bold}"
    if key in FONT_CACHE: return FONT_CACHE[key]
    cands = []
    if lang == "hi":
        lc = LANGUAGES["hi"]
        bp = FONTS_DIR / "NotoSansDevanagari-Bold.ttf"
        rp = FONTS_DIR / "NotoSansDevanagari-Regular.ttf"
        _dl_font(lc["font_url"], bp); _dl_font(lc["font_url_reg"], rp)
        cands = [bp if bold else rp]
    cands += [
        FONTS_DIR / ("Poppins-Bold.ttf" if bold else "Poppins-Regular.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
             if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
             if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for p in cands:
        if Path(p).exists():
            f = ImageFont.truetype(str(p), size)
            FONT_CACHE[key] = f; return f
    return ImageFont.load_default()

# ── Math / draw helpers ────────────────────────────────────────────────────────
def _a(v): return max(0, min(255, int(v)))
def _eo(x): return 1-(1-max(0,min(1,x)))**3
def _eio(x):
    x=max(0,min(1,x)); return 3*x*x-2*x*x*x
def _eb(x):
    """Bounce ease."""
    x = max(0, min(1, x))
    if x < 0.36: return 7.5625 * x * x
    if x < 0.72: return 7.5625*(x-0.54)**2 + 0.75
    if x < 0.9:  return 7.5625*(x-0.81)**2 + 0.9375
    return 7.5625*(x-0.954)**2 + 0.984375
def _slide(t, start, dur=0.4): return _a(_eo(max(0,(t-start)/dur))*255) if t>=start else 0
def _wrap(text, fnt, max_w):
    words,lines,cur=text.split(),[],""
    for w in words:
        t_=(cur+" "+w).strip()
        if fnt.getbbox(t_)[2]<=max_w: cur=t_
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines
def _txt(draw,x,y,t,fnt,col,a,shadow=True):
    if shadow: draw.text((x+2,y+2),t,font=fnt,fill=(0,0,0,_a(a*0.4)))
    draw.text((x,y),t,font=fnt,fill=(*col,_a(a)))
def _glass(draw,x1,y1,x2,y2,fc=(255,255,255),fa=20,sc=(255,255,255),sa=35,r=18):
    draw.rounded_rectangle([x1,y1,x2,y2],radius=r,fill=(*fc,fa),outline=(*sc,sa),width=1)
def _hair(draw,x1,y,x2,col,a):
    draw.rectangle([x1,y,x2,y+1],fill=(*col,_a(a)))

def _bg_frame(photo, th, t, total):
    """Prepare base background frame."""
    scale = 1.0 + 0.035*(t/total)
    nw,nh = int(W*scale), int(H*scale)
    bg = photo.resize((nw,nh),Image.LANCZOS)
    lf = (nw-W)//2; tp = (nh-H)//2
    bg = bg.crop((lf,tp,lf+W,tp+H)).convert("RGB")
    bg = ImageEnhance.Color(bg).enhance(0.65)
    bg = ImageEnhance.Brightness(bg).enhance(0.40)
    bg = bg.convert("RGBA")
    # Gradient tint
    tint = Image.new("RGBA",(W,H))
    td   = ImageDraw.Draw(tint)
    cols = th["grad"]
    for y in range(H):
        fy=y/H; idx=fy*(len(cols)-1); i=min(int(idx),len(cols)-2); fr=idx-i
        c1,c2=cols[i],cols[i+1]
        r_=int(c1[0]+(c2[0]-c1[0])*fr)
        g_=int(c1[1]+(c2[1]-c1[1])*fr)
        b_=int(c1[2]+(c2[2]-c1[2])*fr)
        td.rectangle([0,y,W,y+1],fill=(r_,g_,b_,160))
    bg = Image.alpha_composite(bg,tint)
    # Vignette
    vd = ImageDraw.Draw(bg)
    for i in range(50):
        va=_a(180*(1-i/50)**2.5)
        vd.rectangle([i,i,W-i,H-i],outline=(0,0,0,va),width=6)
    return bg

def _common_chrome(draw, th, lang, topic_key, t, duration, tags, follow_text):
    """Draw letterbox, progress bar, header, hashtags, CTA — shared by all styles."""
    acc=th["acc"]; acc2=th["acc2"]; txt=th["txt"]; mut=th["mut"]

    # Letterbox
    bar_h=96
    if t<0.5: bp=_eo(t/0.5); ty_top=int(-bar_h+bar_h*bp); ty_bot=int(H-bar_h*bp)
    else:     ty_top=0; ty_bot=H-bar_h
    draw.rectangle([0,ty_top,W,ty_top+bar_h],fill=(0,0,0,248))
    draw.rectangle([0,ty_bot,W,ty_bot+bar_h],fill=(0,0,0,248))
    ba=_slide(t,0.4,0.3)
    _hair(draw,0,ty_top+bar_h,W,acc,ba)
    _hair(draw,0,ty_bot-1,    W,acc2,ba)

    # Progress bar
    pb_a=_slide(t,0.5,0.3); pb_y=ty_top+bar_h+3; pb_w=int(W*(t/duration))
    draw.rectangle([0,pb_y,W,pb_y+3],fill=(*acc,_a(pb_a*0.2)))
    for px_ in range(0,pb_w,4):
        sh=0.7+0.3*(px_/max(pb_w,1))
        draw.rectangle([px_,pb_y,px_+4,pb_y+3],fill=(*acc,_a(pb_a*sh)))
    if 6<pb_w<W-6: draw.ellipse([pb_w-5,pb_y-2,pb_w+5,pb_y+5],fill=(*acc,pb_a))

    # Header
    ha=_slide(t,0.3,0.4)
    lbl_fnt=_font(24,bold=True,lang="en")
    lbl=TOPIC_LABELS.get(topic_key,{}).get(lang,"COSMOS CAPSULE")
    draw.ellipse([PAD-1,ty_top+39,PAD+11,ty_top+51],fill=(*acc,_a(ha*0.3)))
    draw.ellipse([PAD+1,ty_top+41,PAD+9,ty_top+49], fill=(*acc,ha))
    _txt(draw,PAD+18,ty_top+31,lbl,lbl_fnt,acc,ha,shadow=False)
    br_fnt=_font(20,lang="en"); br_bb=br_fnt.getbbox("cosmos.capsule")
    _txt(draw,W-br_bb[2]-PAD,ty_top+33,"cosmos.capsule",br_fnt,mut,_a(ha*0.75),shadow=False)

    # Hashtag strip
    tag_a=_slide(t,duration*0.72,0.4)
    if tag_a>0 and tags:
        tag_fnt=_font(23,lang=lang); tag_top=H-190
        _glass(draw,PAD-16,tag_top-8,W-PAD+16,tag_top+64,fc=(0,0,0),fa=55,sc=acc,sa=22,r=12)
        for ri,row in enumerate(["   ".join(tags[:3]),"   ".join(tags[3:6])]):
            if not row: continue
            rb=tag_fnt.getbbox(row); rx_=(W-rb[2])//2; ry_=tag_top+ri*30
            _txt(draw,rx_,ry_,row,tag_fnt,acc,_a(tag_a*0.88))

    # CTA
    cta_a=_slide(t,duration*0.82,0.5)
    for i in range(bar_h+20):
        fa=_a(240*((i/(bar_h+20))**1.8))
        draw.rectangle([0,ty_bot+i,W,ty_bot+i+1],fill=(0,0,0,fa))
    if cta_a>0:
        cta_fnt=_font(29,bold=True,lang=lang)
        cta_bb=cta_fnt.getbbox(follow_text)
        pulse=0.82+0.18*math.sin(t*4)
        ctx_=(W-cta_bb[2])//2; cty_=ty_bot+(bar_h-cta_bb[3])//2-4
        draw.ellipse([ctx_-22-5,cty_+8,ctx_-12,cty_+18],fill=(*acc,_a(cta_a*pulse)))
        _txt(draw,ctx_,cty_,follow_text,cta_fnt,acc,_a(cta_a*pulse))
        arr_fnt=_font(24,bold=True,lang="en")
        draw.text((ctx_+cta_bb[2]+10,cty_+3),"↑",font=arr_fnt,fill=(*acc2,_a(cta_a*pulse)))

    return ty_top, ty_bot, bar_h


# ══════════════════════════════════════════════════════════════════════════════
# STYLE 1: KINETIC TEXT
# Words fly in one by one with scale + bounce effects
# ══════════════════════════════════════════════════════════════════════════════

def _kinetic_frame(bg_photo, hook, body, body_words, topic_key, lang, follow_text, tags, t, dur):
    th   = THEMES.get(topic_key, THEMES["space"])
    acc  = th["acc"]; txt = th["txt"]
    base = _bg_frame(bg_photo, th, t, dur)
    draw = ImageDraw.Draw(base)

    ty_top, ty_bot, bar_h = _common_chrome(draw, th, lang, topic_key, t, dur, tags, follow_text)

    # Hook words fly in one by one
    hook_words = (hook.upper() if lang=="en" else hook).split()
    hook_fnt   = _font(82, bold=True, lang=lang)
    word_dur   = 0.45
    hook_start = 0.7

    # Calculate total hook height
    test_lines = _wrap(" ".join(hook_words), hook_fnt, W-PAD*2-20)
    hook_card_h = len(test_lines) * 92 + 40
    hook_card_y = H//2 - hook_card_h//2 - 40
    _glass(draw, PAD-24, hook_card_y, W-PAD+24, hook_card_y+hook_card_h,
           fc=(0,0,0), fa=65, sc=acc, sa=30, r=22)
    draw.rounded_rectangle([PAD-24,hook_card_y,PAD-21,hook_card_y+hook_card_h],
                           radius=2, fill=(*acc,_a(min(255,t*400))))

    # Render each word individually with kinetic animation
    all_shown = []
    for wi, word in enumerate(hook_words):
        w_start = hook_start + wi * word_dur * 0.6
        if t < w_start: break
        elapsed  = t - w_start
        progress = min(1.0, elapsed / 0.3)
        # Bounce in from below
        bounce   = _eb(progress)
        scale_f  = 0.5 + 0.5 * bounce
        alpha_f  = progress
        all_shown.append((word, scale_f, alpha_f))

    # Layout shown words
    lines    = _wrap(" ".join(w for w,_,_ in all_shown), hook_fnt, W-PAD*2-20)
    hy       = hook_card_y + 20
    shown_so = 0
    for line in lines:
        words_in  = line.split()
        line_w    = sum(hook_fnt.getbbox(w+" ")[2] for w in words_in)
        x_start   = (W - line_w) // 2
        cx        = x_start
        for word in words_in:
            wi_abs = shown_so
            if wi_abs < len(all_shown):
                _, scale_f, alpha_f = all_shown[wi_abs]
                # Scale effect: slightly bigger then settle
                sz    = max(30, int(82 * scale_f))
                w_fnt = _font(sz, bold=True, lang=lang)
                wb    = w_fnt.getbbox(word+" ")
                # Slide up effect
                y_off = int(20 * (1 - scale_f))
                _txt(draw, cx, hy + y_off, word+" ", w_fnt,
                     acc if wi_abs == len(all_shown)-1 else txt,
                     _a(alpha_f * 255))
                cx += wb[2]
            shown_so += 1
        hy += 92

    # Body fades in word by word after hook complete
    if t > hook_start + len(hook_words) * word_dur * 0.6 + 0.5:
        body_elapsed = t - (hook_start + len(hook_words)*word_dur*0.6 + 0.5)
        body_window  = dur * 0.55 - (hook_start + len(hook_words)*word_dur*0.6)
        n_words      = min(len(body_words), int(body_elapsed / max(0.3,body_window/max(len(body_words),1)))+1)
        sub_fnt      = _font(38, lang=lang)
        sub_lines    = _wrap(" ".join(body_words[:n_words]), sub_fnt, W-PAD*2-10)
        sub_top      = hook_card_y + hook_card_h + 30
        sub_h        = len(sub_lines) * 52
        _glass(draw, PAD-20, sub_top-12, W-PAD+20, sub_top+sub_h+12,
               fc=(0,0,0), fa=60, sc=th["acc2"], sa=20, r=14)
        for li, sline in enumerate(sub_lines):
            bb  = sub_fnt.getbbox(sline)
            sx_ = (W-bb[2])//2
            body_a = _slide(t, hook_start+len(hook_words)*word_dur*0.6+0.5, 0.5)
            _txt(draw, sx_, sub_top+li*52, sline, sub_fnt, txt, body_a)

    return np.array(base.convert("RGB"))


# ══════════════════════════════════════════════════════════════════════════════
# STYLE 2: DOCUMENTARY
# Chapter title cards, elegant reveal, professional feel
# ══════════════════════════════════════════════════════════════════════════════

def _documentary_frame(bg_photo, hook, body, body_words, topic_key, lang, follow_text, tags, t, dur):
    th   = THEMES.get(topic_key, THEMES["space"])
    acc  = th["acc"]; acc2 = th["acc2"]; txt = th["txt"]; mut = th["mut"]
    base = _bg_frame(bg_photo, th, t, dur)
    draw = ImageDraw.Draw(base)

    ty_top, ty_bot, bar_h = _common_chrome(draw, th, lang, topic_key, t, dur, tags, follow_text)

    chapter_dur  = dur / 3
    chapter      = min(2, int(t / chapter_dur))
    ch_progress  = (t % chapter_dur) / chapter_dur
    ch_alpha     = _a(_eo(min(1, ch_progress * 3)) * 255)
    fade_out_a   = _a((1 - _eo(max(0, ch_progress - 0.8) / 0.2)) * 255) if ch_progress > 0.8 else 255

    # Chapter 0: "DID YOU KNOW?" intro
    if chapter == 0:
        intro_fnt = _font(36, bold=True, lang=lang)
        intro_txt = "क्या आप जानते हैं?" if lang=="hi" else "DID YOU KNOW?"
        ib        = intro_fnt.getbbox(intro_txt)
        ix        = (W-ib[2])//2
        iy        = H//2 - 200
        _glass(draw, ix-20, iy-14, ix+ib[2]+20, iy+ib[3]+14,
               fc=acc, fa=22, sc=acc, sa=50, r=24)
        _txt(draw, ix, iy, intro_txt, intro_fnt, acc,
             _a(ch_alpha * fade_out_a / 255))

        # Chapter number pill
        num_fnt = _font(100, bold=True, lang="en")
        draw.ellipse([W//2-80, H//2-60, W//2+80, H//2+120],
                     fill=(*acc, _a(ch_alpha*0.12*fade_out_a/255)))
        nb = num_fnt.getbbox("01")
        draw.text(((W-nb[2])//2, H//2-50), "01",
                  font=num_fnt, fill=(*acc, _a(ch_alpha*0.35*fade_out_a/255)))

        # Animated line
        line_w = int((W-PAD*4) * _eo(min(1, ch_progress*2)))
        _hair(draw, PAD*2, H//2+150, PAD*2+line_w, acc, ch_alpha)

    # Chapter 1: Main hook fact
    elif chapter == 1:
        # Chapter label
        ch_fnt  = _font(24, bold=True, lang="en")
        ch_txt  = "THE FACT" if lang=="en" else "तथ्य"
        ch_bb   = ch_fnt.getbbox(ch_txt)
        chy     = H//3 - 80
        _hair(draw, PAD*2, chy, PAD*2+ch_bb[2]+20, acc, ch_alpha)
        _txt(draw, PAD*2, chy+8, ch_txt, ch_fnt, acc, ch_alpha, shadow=False)

        hook_fnt   = _font(68, bold=True, lang=lang)
        hook_lines = _wrap(hook.upper() if lang=="en" else hook, hook_fnt, W-PAD*2-20)
        hook_h     = len(hook_lines)*84
        hook_y     = H//2 - hook_h//2 - 20
        _glass(draw, PAD-24, hook_y-20, W-PAD+24, hook_y+hook_h+20,
               fc=(0,0,0), fa=65, sc=acc, sa=28, r=20)
        draw.rounded_rectangle([PAD-24,hook_y-20,PAD-21,hook_y+hook_h+20],
                               radius=2,fill=(*acc,_a(ch_alpha*fade_out_a/255)))
        hy = hook_y
        for line in hook_lines:
            bb = hook_fnt.getbbox(line)
            _txt(draw,(W-bb[2])//2,hy,line,hook_fnt,txt,_a(ch_alpha*fade_out_a/255))
            hy += 84

    # Chapter 2: Deep dive body text
    elif chapter == 2:
        ch_fnt = _font(24, bold=True, lang="en")
        ch_txt = "LEARN MORE" if lang=="en" else "और जानें"
        ch_bb  = ch_fnt.getbbox(ch_txt)
        chy    = H//4 - 40
        _hair(draw, PAD*2, chy, PAD*2+ch_bb[2]+20, acc, ch_alpha)
        _txt(draw, PAD*2, chy+8, ch_txt, ch_fnt, acc, ch_alpha, shadow=False)

        sub_fnt   = _font(42, lang=lang)
        sub_lines = _wrap(body, sub_fnt, W-PAD*2-10)
        sub_top   = H//3
        sub_h     = len(sub_lines)*58
        _glass(draw, PAD-20, sub_top-16, W-PAD+20, sub_top+sub_h+16,
               fc=(0,0,0), fa=62, sc=acc2, sa=22, r=16)
        # Reveal words over time
        n_reveal = min(len(sub_lines), int(ch_progress * len(sub_lines) * 1.5) + 1)
        for li in range(n_reveal):
            if li >= len(sub_lines): break
            la  = _slide(t, chapter*chapter_dur + li*0.3, 0.4)
            bb  = sub_fnt.getbbox(sub_lines[li])
            sx_ = (W-bb[2])//2
            _txt(draw, sx_, sub_top+li*58, sub_lines[li],
                 sub_fnt, txt, _a(la*fade_out_a/255))

    return np.array(base.convert("RGB"))


# ══════════════════════════════════════════════════════════════════════════════
# STYLE 3: CARTOON MASCOT
# Simple geometric mascot character + bouncy text
# ══════════════════════════════════════════════════════════════════════════════

def _draw_mascot(draw, cx, cy, t, acc, acc2, txt_col, size=120):
    """Draw a simple cute geometric mascot character."""
    bounce   = math.sin(t * 2.5) * 8   # gentle bob
    cy_       = int(cy + bounce)
    eye_blink = t % 4 > 3.5             # blink every 4s

    # Body (rounded rectangle)
    bw, bh = size, int(size*1.1)
    draw.rounded_rectangle([cx-bw//2, cy_-bh//2, cx+bw//2, cy_+bh//2],
                           radius=30, fill=(*acc, 220))

    # Head
    hr = int(size*0.52)
    draw.ellipse([cx-hr, cy_-bh//2-hr*2+10, cx+hr, cy_-bh//2+hr*2-hr+10],
                fill=(*acc, 220))

    # Face eyes
    ew, eh = 14, (4 if eye_blink else 14)
    eye_y  = cy_-bh//2-hr+8
    for ex in [cx-22, cx+22]:
        draw.ellipse([ex-ew//2, eye_y-eh//2, ex+ew//2, eye_y+eh//2],
                    fill=(255,255,255,240))
        if not eye_blink:
            draw.ellipse([ex-5, eye_y-5, ex+5, eye_y+5],
                        fill=(20,20,40,240))

    # Smile
    smile_a = int(30 + 30*math.sin(t*1.5))
    draw.arc([cx-20, eye_y+12, cx+20, eye_y+30],
             start=0, end=180, fill=(20,20,40,200), width=3)

    # Arms (waving)
    arm_angle = math.sin(t * 3) * 0.4
    # Left arm
    ax1, ay1 = cx-bw//2, cy_-10
    ax2 = ax1 - int(50*math.cos(arm_angle+0.5))
    ay2 = ay1 + int(50*math.sin(arm_angle+0.5))
    draw.line([(ax1,ay1),(ax2,ay2)], fill=(*acc,200), width=12)
    draw.ellipse([ax2-10,ay2-10,ax2+10,ay2+10], fill=(*acc,200))

    # Right arm (wave)
    rx1, ry1 = cx+bw//2, cy_-10
    rx2 = rx1 + int(50*math.cos(arm_angle))
    ry2 = ry1 - int(50*math.sin(arm_angle))
    draw.line([(rx1,ry1),(rx2,ry2)], fill=(*acc,200), width=12)
    draw.ellipse([rx2-10,ry2-10,rx2+10,ry2+10], fill=(*acc,200))

    # Legs
    for lx_off, leg_phase in [(-25, 0), (25, math.pi)]:
        leg_swing = int(15*math.sin(t*2.5 + leg_phase))
        draw.line([(cx+lx_off, cy_+bh//2-10),
                   (cx+lx_off+leg_swing, cy_+bh//2+50)],
                  fill=(*acc,200), width=14)
        draw.ellipse([cx+lx_off+leg_swing-10, cy_+bh//2+40,
                      cx+lx_off+leg_swing+10, cy_+bh//2+60],
                    fill=(*acc2,200))

    # Speech bubble hint (small star/sparkle)
    sp_x = cx+hr+20; sp_y = cy_-bh//2-hr
    sp_r = int(8+4*math.sin(t*3))
    draw.ellipse([sp_x-sp_r,sp_y-sp_r,sp_x+sp_r,sp_y+sp_r],fill=(*txt_col,160))


def _cartoon_frame(bg_photo, hook, body, body_words, topic_key, lang, follow_text, tags, t, dur):
    th   = THEMES.get(topic_key, THEMES["space"])
    acc  = th["acc"]; acc2 = th["acc2"]; txt = th["txt"]
    base = _bg_frame(bg_photo, th, t, dur)
    draw = ImageDraw.Draw(base)

    ty_top, ty_bot, bar_h = _common_chrome(draw, th, lang, topic_key, t, dur, tags, follow_text)

    # Draw mascot (top third of screen)
    mascot_a = _slide(t, 0.4, 0.5)
    if mascot_a > 30:
        _draw_mascot(draw, W//2, H//4+60, t, acc, acc2, txt, size=110)

    # Speech bubble from mascot
    bubble_a = _slide(t, 0.8, 0.4)
    if bubble_a > 0:
        hook_fnt   = _font(62, bold=True, lang=lang)
        hook_txt   = hook.upper() if lang=="en" else hook
        hook_lines = _wrap(hook_txt, hook_fnt, W-PAD*2-20)
        hook_h     = len(hook_lines) * 78
        bubble_top = H//2 - 30
        bubble_bot = bubble_top + hook_h + 40

        # Bubble shape (rounded rect with pointer)
        _glass(draw, PAD-20, bubble_top-16, W-PAD+20, bubble_bot+16,
               fc=(255,255,255), fa=28, sc=acc, sa=60, r=24)

        # Bubble pointer (triangle pointing up toward mascot)
        pts = [(W//2-15, bubble_top-16),
               (W//2+15, bubble_top-16),
               (W//2,    bubble_top-40)]
        draw.polygon(pts, fill=(*acc, _a(bubble_a*0.4)))

        # Bouncy text
        hy = bubble_top
        for li, line in enumerate(hook_lines):
            bb    = hook_fnt.getbbox(line)
            hx    = (W-bb[2])//2
            # Each line bounces in
            line_a = _slide(t, 0.8 + li*0.2, 0.3)
            bounce_off = int(10 * (1 - min(1, (t-0.8-li*0.2)/0.3)))
            _txt(draw, hx, hy-bounce_off, line, hook_fnt, txt,
                 _a(line_a * bubble_a / 255))
            hy += 78

        # Body text with cartoon speech bubbles
        body_start_t = 0.8 + len(hook_lines)*0.2 + 0.8
        if t > body_start_t:
            body_a      = _slide(t, body_start_t, 0.5)
            sub_fnt     = _font(36, lang=lang)
            body_elapsed = t - body_start_t
            body_window  = dur*0.5
            n_words      = min(len(body_words), int(body_elapsed/max(0.25,body_window/max(len(body_words),1)))+1)
            sub_lines    = _wrap(" ".join(body_words[:n_words]), sub_fnt, W-PAD*2-10)
            sub_top      = bubble_bot + 28
            sub_h        = len(sub_lines) * 50
            _glass(draw, PAD-16, sub_top-12, W-PAD+16, sub_top+sub_h+12,
                   fc=(0,0,0), fa=60, sc=acc2, sa=22, r=14)
            for li, sline in enumerate(sub_lines):
                bb  = sub_fnt.getbbox(sline)
                sx_ = (W-bb[2])//2
                la  = _slide(t, body_start_t + li*0.2, 0.35)
                _txt(draw, sx_, sub_top+li*50, sline, sub_fnt, txt, la)

    return np.array(base.convert("RGB"))


# ══════════════════════════════════════════════════════════════════════════════
# VIDEO CREATOR
# ══════════════════════════════════════════════════════════════════════════════

class VideoCreator:
    def create_reel(self, image_path: Path, music_path: Path,
                    fact_data: dict, topic: dict,
                    lang: str, output_dir: Path,
                    reel_style: str = "kinetic",
                    duration: int = 20,
                    music_volume: float = 0.40) -> Path:

        log.info(f"🎬 [{reel_style.upper()}] [{lang.upper()}] {duration}s reel…")

        import config as cfg
        topic_key = "space"
        for k, v in cfg.TOPICS.items():
            if v.get("name") == topic.get("name") or v.get("name_hi") == topic.get("name_hi"):
                topic_key = k; break

        bg          = Image.open(image_path).convert("RGB")
        hook        = fact_data["hook"]
        body        = fact_data["body"]
        body_words  = body.split()
        follow_text = LANGUAGES["hi"]["follow_text"]

        # New topic-specific video tags
        VIDEO_TAGS_NEW = {
            "psychology":   ["#मनोविज्ञान","#psychology","#दिमाग","#mindset","#brainpower","#cosmoscapsule"],
            "mindblowing":  ["#mindblow","#दिमागहिला","#amazingfacts","#रोचकतथ्य","#viral","#cosmoscapsule"],
            "space":        ["#अंतरिक्ष","#ब्रह्मांड","#spacefacts","#NASA","#ISRO","#cosmoscapsule"],
            "sciencewrong": ["#sciencefail","#विज्ञान","#sciencefacts","#funny","#facts","#cosmoscapsule"],
            "earthglitch":  ["#earthglitch","#धरती","#naturalfacts","#amazing","#mystery","#cosmoscapsule"],
        }
        tags = VIDEO_TAGS_NEW.get(topic_key, VIDEO_TAGS.get(f"{topic_key}_hi", ["#cosmoscapsule"]))

        renderers = {
            "kinetic":     _kinetic_frame,
            "documentary": _documentary_frame,
            "cartoon":     _cartoon_frame,
        }
        render_fn = renderers.get(reel_style, _kinetic_frame)

        def make_frame(t):
            return render_fn(bg, hook, body, body_words,
                             topic_key, lang, follow_text, tags, t, duration)

        clip = VideoClip(make_frame, duration=duration).set_fps(REEL_FPS)
        clip = fadein(clip, min(0.4, duration * 0.05))
        clip = fadeout(clip, min(0.6, duration * 0.06))

        audio = (AudioFileClip(str(music_path))
                 .subclip(0, min(duration, AudioFileClip(str(music_path)).duration))
                 .audio_fadeout(min(2.5, duration * 0.15))
                 .volumex(music_volume))
        clip = clip.set_audio(audio)

        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        cat_slug = (fact_data.get("fact_category", topic.get("name",""))[:15]
                    .replace(" ","_").lower())
        out_path = output_dir / f"reel_{cat_slug}_{lang}_{reel_style}_{ts}.mp4"

        log.info(f"💾 Writing → {out_path.name}")
        clip.write_videofile(
            str(out_path),
            codec="libx264", audio_codec="aac",
            fps=REEL_FPS, preset="fast",
            bitrate="4500k", audio_bitrate="192k",
            ffmpeg_params=["-vf", f"scale={W}:{H}"],
            logger=None,
        )
        log.info(f"✅ {out_path.stat().st_size/1e6:.1f} MB")
        return out_path
