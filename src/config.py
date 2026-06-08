"""
src/config.py — 5 viral topics, Hindi only, smart duration + voiceover logic.
"""

import random
from pathlib import Path

# ── Topics ─────────────────────────────────────────────────────────────────────

TOPICS = {
    "psychology": {
        "name":         "Psychology Facts",
        "name_hi":      "मनोविज्ञान तथ्य",
        "emoji":        "🧠",
        "type":         "fact",
        "music_mood":   "soft calm ambient",
        "music_energy": "calm",
        "image_keywords": ["human brain illustration", "psychology mind art",
                           "thinking person silhouette", "mind concept art",
                           "neuroscience illustration"],
        "color_scheme": {
            "bg":     (8,  4,  20),
            "accent": (160, 100, 255),
            "text":   (235, 220, 255),
        },
        "hashtags_hi": (
            "#मनोविज्ञान #psychology #मनोवैज्ञानिकतथ्य #दिमाग #brainpower "
            "#psychologyfacts #mindset #reelsviral #reelsindia #hindireels "
            "#trending #foryou #viral #didyouknow #cosmoscapsule"
        ),
    },

    "mindblowing": {
        "name":         "Mind-Blowing Facts",
        "name_hi":      "दिमाग हिला देने वाले तथ्य",
        "emoji":        "🤯",
        "type":         "fact",
        "music_mood":   "motivational epic upbeat",
        "music_energy": "high",
        "image_keywords": ["explosion mind art", "shock wave digital art",
                           "mind blown illustration", "surreal concept art",
                           "amazing universe art"],
        "color_scheme": {
            "bg":     (20, 5,  5),
            "accent": (255, 80, 50),
            "text":   (255, 235, 228),
        },
        "hashtags_hi": (
            "#mindblow #दिमागहिला #amazingfacts #रोचकतथ्य #अद्भुततथ्य "
            "#facts #didyouknow #reelsviral #reelsindia #hindireels "
            "#trending #foryou #viral #mindblown #cosmoscapsule"
        ),
    },

    "space": {
        "name":         "Space & Universe",
        "name_hi":      "अंतरिक्ष और ब्रह्मांड",
        "emoji":        "🚀",
        "type":         "fact",
        "music_mood":   "soft calm ambient",
        "music_energy": "calm",
        "image_keywords": ["galaxy digital art", "nebula illustration",
                           "space anime art", "cosmic concept art",
                           "universe watercolor painting"],
        "color_scheme": {
            "bg":     (4,  6,  22),
            "accent": (100, 185, 255),
            "text":   (225, 242, 255),
        },
        "hashtags_hi": (
            "#अंतरिक्ष #ब्रह्मांड #spacefacts #NASA #ISRO #universe "
            "#reelsviral #reelsindia #hindireels #trending #foryou "
            "#viral #spacehindi #cosmoscapsule"
        ),
    },

    "sciencewrong": {
        "name":         "Science Gone Wrong",
        "name_hi":      "विज्ञान जब गलत हो गया",
        "emoji":        "⚗️",
        "type":         "fact",
        "music_mood":   "motivational epic upbeat",
        "music_energy": "high",
        "image_keywords": ["science experiment explosion art",
                           "chemistry disaster illustration",
                           "mad scientist cartoon",
                           "laboratory accident comic",
                           "science fail concept art"],
        "color_scheme": {
            "bg":     (5,  18, 5),
            "accent": (80, 230, 120),
            "text":   (215, 255, 225),
        },
        "hashtags_hi": (
            "#sciencegonewrong #विज्ञानगलत #sciencefail #sciencefacts "
            "#रोचकविज्ञान #reelsviral #reelsindia #hindireels "
            "#trending #foryou #viral #sciencehindi #cosmoscapsule"
        ),
    },

    "earthglitch": {
        "name":         "Earth Glitches",
        "name_hi":      "धरती की अजीब घटनाएं",
        "emoji":        "🌍",
        "type":         "fact",
        "music_mood":   "motivational epic upbeat",
        "music_energy": "high",
        "image_keywords": ["earth glitch digital art",
                           "natural phenomenon illustration",
                           "mysterious nature art",
                           "earth anomaly concept",
                           "strange weather phenomenon art"],
        "color_scheme": {
            "bg":     (4,  14, 8),
            "accent": (70, 215, 130),
            "text":   (215, 255, 230),
        },
        "hashtags_hi": (
            "#earthglitch #धरतीकेरहस्य #naturalfacts #अजीबघटनाएं "
            "#amazingnature #reelsviral #reelsindia #hindireels "
            "#trending #foryou #viral #earthfacts #cosmoscapsule"
        ),
    },
}

# ── Language — Hindi only ──────────────────────────────────────────────────────

LANGUAGES = {
    "hi": {
        "code":        "hi",
        "name":        "हिंदी",
        "follow_text": "रोज़ नई जानकारी के लिए फॉलो करें  ✨",
        "font_url":    "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf",
        "font_url_reg":"https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
    },
}

# ── Duration logic ─────────────────────────────────────────────────────────────
# 30 out of 100 reels get voiceover (max 20s)
# Rest are 10–20s randomly (no voiceover)
VOICEOVER_PROBABILITY = 0.30   # 30%
DURATION_WITH_VOICE   = 20     # always 20s when voiceover
DURATION_MIN          = 10     # minimum without voiceover
DURATION_MAX          = 20     # maximum without voiceover


def get_duration_and_voice() -> tuple[int, bool]:
    """Returns (duration_seconds, use_voiceover)."""
    use_voice = random.random() < VOICEOVER_PROBABILITY
    if use_voice:
        return DURATION_WITH_VOICE, True
    return random.randint(DURATION_MIN, DURATION_MAX), False


# ── Schedule: 3 reels/day, all Hindi ──────────────────────────────────────────

# Day of week (0=Mon…6=Sun) → (9AM_topic, 1PM_topic, 7PM_topic)
DAY_ROTATION = {
    0: ("psychology",   "mindblowing",  "space"),        # Monday
    1: ("mindblowing",  "space",        "sciencewrong"), # Tuesday
    2: ("space",        "sciencewrong", "earthglitch"),  # Wednesday
    3: ("sciencewrong", "earthglitch",  "psychology"),   # Thursday
    4: ("earthglitch",  "psychology",   "mindblowing"),  # Friday
    5: ("psychology",   "space",        "mindblowing"),  # Saturday
    6: ("mindblowing",  "earthglitch",  "space"),        # Sunday
}

# ── Video specs ────────────────────────────────────────────────────────────────
REEL_WIDTH  = 1080
REEL_HEIGHT = 1920
REEL_FPS    = 30
MUSIC_VOLUME_CALM = 0.45    # calm music — slightly louder
MUSIC_VOLUME_HIGH = 0.38    # high energy music — let voice cut through


def get_music_volume(energy: str) -> float:
    return MUSIC_VOLUME_CALM if energy == "calm" else MUSIC_VOLUME_HIGH


def get_hashtags(topic_key: str, lang: str = "hi") -> str:
    return TOPICS[topic_key].get("hashtags_hi", "#cosmoscapsule")
