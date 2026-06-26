"""
src/config.py — Growth-strategy config (target: 100K followers / 6 months)

STRATEGY CHANGE (vs. old 7-topic/3-post-a-day version):
  - 4 focused topics only. Niche-authority > variety for a new account.
  - 1 post/day, scheduled at the single best Indian engagement window.
  - Every topic now carries a "cta_style" — the comment/save/share trigger
    that gets baked into every reel, not just the fact.
  - Hindi only.

Why these 4 and not the old 7:
  - examfacts  -> exam aspirants are Instagram's most save-happy, most
                  comment-happy demographic in India. Built-in urgency.
  - psychology -> highest share-to-friend rate ("yeh tera jaisa hai bro").
  - mindblowing-> broadest top-of-funnel discovery / Explore potential.
  - gk         -> best quiz/comment-bait format ("comment your answer").
  Dropped sciencewrong / earthglitch / space as separate slots — a single
  fact account with 7 unrelated topics never builds the "this account =
  X" recognition the algorithm rewards. Their best ideas got folded into
  mindblowing as a sub-angle, not a separate daily slot.
"""

import random

# ── Topics ─────────────────────────────────────────────────────────────────────
# cta_style drives which comment-bait / save-bait template fact_gen.py uses.

TOPICS = {

    "examfacts": {
        "name": "Exam Facts", "name_hi": "परीक्षा ज्ञान", "emoji": "🎯",
        "type": "fact", "music_mood": "soft calm ambient", "music_energy": "calm",
        "cta_style": "save_and_guess",
        "series_name": "Exam One-Liner",  "series_name_hi": "परीक्षा वन-लाइनर",
        "image_keywords": ["student studying india", "exam preparation art",
                            "india education illustration", "competitive exam concept",
                            "upsc ssc preparation art"],
        "color_scheme": {"bg": (4, 4, 18), "accent": (80, 200, 255), "text": (220, 240, 255)},
        "hashtags_hi": (
            "#UPSC #SSC #NEET #IITpreparation #exampreparation "
            "#UPSCpreparation #SSCpreparation #NEETpreparation "
            "#currentaffairs #gkinhindi #reelsindia #hindireels "
            "#trending #foryou #viral #studymotivation #cosmoscapsule"
        ),
    },

    "psychology": {
        "name": "Psychology Facts", "name_hi": "मनोविज्ञान तथ्य", "emoji": "🧠",
        "type": "fact", "music_mood": "soft calm ambient", "music_energy": "calm",
        "cta_style": "tag_a_friend",
        "series_name": "Mind Truths",     "series_name_hi": "दिमाग की सच्चाई",
        "image_keywords": ["human brain illustration", "psychology mind art",
                            "thinking person silhouette", "mind concept art"],
        "color_scheme": {"bg": (8, 4, 20), "accent": (160, 100, 255), "text": (235, 220, 255)},
        "hashtags_hi": (
            "#मनोविज्ञान #psychology #दिमाग #brainpower #psychologyfacts "
            "#mindset #reelsviral #reelsindia #hindireels #trending #foryou "
            "#viral #didyouknow #cosmoscapsule"
        ),
    },

    "mindblowing": {
        "name": "Mind-Blowing Facts", "name_hi": "दिमाग हिला देने वाले तथ्य", "emoji": "🤯",
        "type": "fact", "music_mood": "motivational epic upbeat", "music_energy": "high",
        "cta_style": "agree_or_not",
        "series_name": "Whoa Facts",      "series_name_hi": "हैरान कर देने वाला सच",
        "image_keywords": ["explosion mind art", "shock wave digital art",
                            "mind blown illustration", "surreal concept art",
                            "science experiment art", "earth glitch digital art"],
        "color_scheme": {"bg": (20, 5, 5), "accent": (255, 80, 50), "text": (255, 235, 228)},
        "hashtags_hi": (
            "#mindblow #दिमागहिला #amazingfacts #रोचकतथ्य #facts "
            "#didyouknow #reelsviral #reelsindia #hindireels #trending "
            "#foryou #viral #cosmoscapsule"
        ),
    },

    "gk": {
        "name": "General Knowledge", "name_hi": "सामान्य ज्ञान", "emoji": "📚",
        "type": "fact", "music_mood": "soft calm ambient", "music_energy": "calm",
        "cta_style": "comment_your_answer",
        "series_name": "Daily GK",        "series_name_hi": "रोज़ का GK",
        "image_keywords": ["india map illustration", "world history art",
                            "education book concept", "knowledge brain art",
                            "india culture illustration"],
        "color_scheme": {"bg": (4, 8, 18), "accent": (255, 180, 40), "text": (255, 245, 220)},
        "hashtags_hi": (
            "#सामान्यज्ञान #GK #generalknowledge #ज्ञान #facts "
            "#gkinhindi #india #reelsviral #reelsindia #hindireels "
            "#trending #foryou #viral #gkhindi #cosmoscapsule"
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

# ── Duration — no voiceover (fully automated, per business decision) ──────────
# Kept short: 7-15s window matches "highest replay rate" research finding.
VOICEOVER_PROBABILITY = 0.0
DURATION_MIN          = 11
DURATION_MAX          = 15


def get_duration_and_voice() -> tuple[int, bool]:
    return random.randint(DURATION_MIN, DURATION_MAX), False


# ── Schedule: 1 reel/day ───────────────────────────────────────────────────────
# Single best Indian engagement window: 7:00–8:30 PM IST (commute home / evening
# scroll). Posting once, well, beats 3x/day diluted attention.
# IST = UTC + 5:30, so 7:30 PM IST = 14:00 UTC.
POSTS_PER_DAY = 1

# Topic rotates daily so the niche stays narrow (4 topics) but never repeats
# two days running.
DAY_ROTATION = {
    0: "examfacts",    # Monday   — start the week with exam urgency
    1: "psychology",   # Tuesday
    2: "gk",           # Wednesday
    3: "examfacts",    # Thursday — exam content posted 2x/week, it converts best
    4: "mindblowing",  # Friday   — broad reach into the weekend
    5: "psychology",   # Saturday
    6: "gk",           # Sunday   — quiz-style content, people have downtime
}

# ── Video specs ────────────────────────────────────────────────────────────────
REEL_WIDTH        = 1080
REEL_HEIGHT       = 1920
REEL_FPS           = 30
MUSIC_VOLUME_CALM  = 0.55
MUSIC_VOLUME_HIGH  = 0.50


def get_music_volume(energy: str) -> float:
    return MUSIC_VOLUME_CALM if energy == "calm" else MUSIC_VOLUME_HIGH


def get_hashtags(topic_key: str, lang: str = "hi") -> str:
    return TOPICS[topic_key].get("hashtags_hi", "#cosmoscapsule")


def get_cta_style(topic_key: str) -> str:
    return TOPICS.get(topic_key, {}).get("cta_style", "comment_your_answer")


def get_series_label(topic_key: str, episode: int, lang: str = "hi") -> str:
    """
    On-screen series tag, e.g. 'रोज़ का GK #47'. Series identity is what
    converts a one-time viewer into a follower — they follow to catch the
    next episode, the same way people subscribe to a show. The episode
    number is supplied by FactMemory.next_episode() so it auto-increments
    and persists across runs.
    """
    t    = TOPICS.get(topic_key, {})
    name = t.get("series_name_hi") or t.get("series_name") or t.get("name_hi", "")
    return f"{name} #{episode}"

