"""
src/config.py — 7 viral topics, Hindi only.
New: gk (General Knowledge) + examfacts (SSC/UPSC/NEET/IIT)
No topic labels shown on reels — content speaks for itself.
"""

import random

# ── Topics ─────────────────────────────────────────────────────────────────────

TOPICS = {

    "psychology": {
        "name": "Psychology Facts", "name_hi": "मनोविज्ञान तथ्य", "emoji": "🧠",
        "type": "fact", "music_mood": "soft calm ambient", "music_energy": "calm",
        "image_keywords": ["human brain illustration","psychology mind art",
                           "thinking person silhouette","mind concept art"],
        "color_scheme": {"bg":(8,4,20),"accent":(160,100,255),"text":(235,220,255)},
        "hashtags_hi": (
            "#मनोविज्ञान #psychology #दिमाग #brainpower #psychologyfacts "
            "#mindset #reelsviral #reelsindia #hindireels #trending #foryou "
            "#viral #didyouknow #cosmoscapsule"
        ),
    },

    "mindblowing": {
        "name": "Mind-Blowing Facts", "name_hi": "दिमाग हिला देने वाले तथ्य", "emoji": "🤯",
        "type": "fact", "music_mood": "motivational epic upbeat", "music_energy": "high",
        "image_keywords": ["explosion mind art","shock wave digital art",
                           "mind blown illustration","surreal concept art"],
        "color_scheme": {"bg":(20,5,5),"accent":(255,80,50),"text":(255,235,228)},
        "hashtags_hi": (
            "#mindblow #दिमागहिला #amazingfacts #रोचकतथ्य #facts "
            "#didyouknow #reelsviral #reelsindia #hindireels #trending "
            "#foryou #viral #cosmoscapsule"
        ),
    },

    "space": {
        "name": "Space & Universe", "name_hi": "अंतरिक्ष और ब्रह्मांड", "emoji": "🚀",
        "type": "fact", "music_mood": "soft calm ambient", "music_energy": "calm",
        "image_keywords": ["galaxy digital art","nebula illustration",
                           "space anime art","cosmic concept art"],
        "color_scheme": {"bg":(4,6,22),"accent":(100,185,255),"text":(225,242,255)},
        "hashtags_hi": (
            "#अंतरिक्ष #ब्रह्मांड #spacefacts #NASA #ISRO #universe "
            "#reelsviral #reelsindia #hindireels #trending #foryou "
            "#viral #spacehindi #cosmoscapsule"
        ),
    },

    "sciencewrong": {
        "name": "Science Gone Wrong", "name_hi": "विज्ञान जब गलत हो गया", "emoji": "⚗️",
        "type": "fact", "music_mood": "motivational epic upbeat", "music_energy": "high",
        "image_keywords": ["science experiment explosion art","chemistry disaster illustration",
                           "mad scientist cartoon","laboratory accident comic"],
        "color_scheme": {"bg":(5,18,5),"accent":(80,230,120),"text":(215,255,225)},
        "hashtags_hi": (
            "#sciencegonewrong #विज्ञानगलत #sciencefail #sciencefacts "
            "#रोचकविज्ञान #reelsviral #reelsindia #hindireels "
            "#trending #foryou #viral #cosmoscapsule"
        ),
    },

    "earthglitch": {
        "name": "Earth Glitches", "name_hi": "धरती की अजीब घटनाएं", "emoji": "🌍",
        "type": "fact", "music_mood": "motivational epic upbeat", "music_energy": "high",
        "image_keywords": ["earth glitch digital art","natural phenomenon illustration",
                           "mysterious nature art","earth anomaly concept"],
        "color_scheme": {"bg":(4,14,8),"accent":(70,215,130),"text":(215,255,230)},
        "hashtags_hi": (
            "#earthglitch #धरतीकेरहस्य #naturalfacts #अजीबघटनाएं "
            "#amazingnature #reelsviral #reelsindia #hindireels "
            "#trending #foryou #viral #cosmoscapsule"
        ),
    },

    "gk": {
        "name": "General Knowledge", "name_hi": "सामान्य ज्ञान", "emoji": "📚",
        "type": "fact", "music_mood": "soft calm ambient", "music_energy": "calm",
        "image_keywords": ["india map illustration","world history art",
                           "education book concept","knowledge brain art",
                           "india culture illustration"],
        "color_scheme": {"bg":(4,8,18),"accent":(255,180,40),"text":(255,245,220)},
        "hashtags_hi": (
            "#सामान्यज्ञान #GK #generalknowledge #ज्ञान #facts "
            "#gkinhindi #india #reelsviral #reelsindia #hindireels "
            "#trending #foryou #viral #gkhindi #cosmoscapsule"
        ),
    },

    "examfacts": {
        "name": "Exam Facts", "name_hi": "परीक्षा ज्ञान", "emoji": "🎯",
        "type": "fact", "music_mood": "soft calm ambient", "music_energy": "calm",
        "image_keywords": ["student studying india","exam preparation art",
                           "india education illustration","competitive exam concept",
                           "upsc ssc preparation art"],
        "color_scheme": {"bg":(4,4,18),"accent":(80,200,255),"text":(220,240,255)},
        "hashtags_hi": (
            "#UPSC #SSC #NEET #IIT #परीक्षा #exampreparation "
            "#gkinhindi #currentaffairs #reelsviral #reelsindia "
            "#hindireels #trending #foryou #viral #cosmoscapsule"
        ),
    },
}

# ── Language — Hindi only ──────────────────────────────────────────────────────

LANGUAGES = {
    "hi": {
        "code":         "hi",
        "name":         "हिंदी",
        "follow_text":  "रोज़ नई जानकारी के लिए फॉलो करें  ✨",
        "font_url":     "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf",
        "font_url_reg": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
    },
}

# ── Duration — no voiceover ────────────────────────────────────────────────────
VOICEOVER_PROBABILITY = 0.0
DURATION_MIN          = 15
DURATION_MAX          = 20


def get_duration_and_voice() -> tuple[int, bool]:
    return random.randint(DURATION_MIN, DURATION_MAX), False


# ── Schedule ───────────────────────────────────────────────────────────────────
# 7 topics rotate across the week — all 3 daily slots
DAY_ROTATION = {
    0: ("psychology",  "gk",         "space"),        # Monday
    1: ("mindblowing", "examfacts",  "sciencewrong"), # Tuesday
    2: ("space",       "examfacts",  "earthglitch"),  # Wednesday  ← examfacts added
    3: ("sciencewrong","examfacts",  "psychology"),   # Thursday
    4: ("earthglitch", "gk",         "mindblowing"),  # Friday
    5: ("psychology",  "examfacts",  "space"),        # Saturday
    6: ("mindblowing", "gk",         "earthglitch"),  # Sunday
}

# ── Video specs ────────────────────────────────────────────────────────────────
REEL_WIDTH        = 1080
REEL_HEIGHT       = 1920
REEL_FPS          = 30
MUSIC_VOLUME_CALM = 0.55
MUSIC_VOLUME_HIGH = 0.50


def get_music_volume(energy: str) -> float:
    return MUSIC_VOLUME_CALM if energy == "calm" else MUSIC_VOLUME_HIGH


def get_hashtags(topic_key: str, lang: str = "hi") -> str:
    return TOPICS[topic_key].get("hashtags_hi", "#cosmoscapsule")
