"""
src/config.py — All topic definitions, languages, and global constants.
6 topics × 2 languages (English + Hindi) = 12 reels/day
"""

# ── Topics ─────────────────────────────────────────────────────────────────────

TOPICS = {

    # ── Knowledge topics (AI-generated facts) ──────────────────────────────────

    "space": {
        "name": "Space & Universe",
        "name_hi": "अंतरिक्ष और ब्रह्मांड",
        "emoji": "🚀",
        "type": "fact",          # "fact" = pure AI, "news" = web search + AI
        "music_mood": "ambient cinematic space",
        "hashtags": "#space #universe #astronomy #NASA #cosmos #sciencefacts #didyouknow #spacefacts #education #cosmoscapsule",
        "hashtags_hi": "#अंतरिक्ष #ब्रह्मांड #विज्ञान #नासा #तथ्य #ज्ञान #शिक्षा #cosmoscapsule",
        "image_keywords": ["galaxy", "nebula", "cosmos", "planets", "stars", "milky way", "space telescope"],
        "color_scheme": {"bg": (5, 5, 25), "accent": (100, 180, 255), "text": (220, 240, 255)},
    },

    "history": {
        "name": "World History",
        "name_hi": "विश्व इतिहास",
        "emoji": "📜",
        "type": "fact",
        "music_mood": "epic orchestral historical",
        "hashtags": "#history #worldhistory #historyfacts #ancient #civilization #didyouknow #historybuff #education #cosmoscapsule",
        "hashtags_hi": "#इतिहास #विश्वइतिहास #तथ्य #प्राचीन #सभ्यता #ज्ञान #शिक्षा #cosmoscapsule",
        "image_keywords": ["ancient ruins", "historical monument", "medieval castle", "roman colosseum", "pyramid"],
        "color_scheme": {"bg": (25, 15, 5), "accent": (200, 150, 80), "text": (255, 240, 210)},
    },

    "geography": {
        "name": "Geography",
        "name_hi": "भूगोल",
        "emoji": "🌍",
        "type": "fact",
        "music_mood": "nature acoustic world",
        "hashtags": "#geography #earthfacts #nature #travel #countries #didyouknow #geographyfacts #education #cosmoscapsule",
        "hashtags_hi": "#भूगोल #पृथ्वी #प्रकृति #यात्रा #तथ्य #ज्ञान #शिक्षा #cosmoscapsule",
        "image_keywords": ["mountain landscape", "ocean aerial", "rainforest", "desert dunes", "waterfall", "river"],
        "color_scheme": {"bg": (5, 20, 10), "accent": (80, 200, 120), "text": (210, 255, 225)},
    },

    "science": {
        "name": "Science Facts",
        "name_hi": "विज्ञान तथ्य",
        "emoji": "🔬",
        "type": "fact",
        "music_mood": "electronic upbeat discovery",
        "hashtags": "#science #sciencefacts #biology #physics #chemistry #didyouknow #sciencelovers #education #cosmoscapsule",
        "hashtags_hi": "#विज्ञान #भौतिकी #रसायन #जीवविज्ञान #तथ्य #ज्ञान #शिक्षा #cosmoscapsule",
        "image_keywords": ["laboratory", "dna strand", "microscope", "chemistry", "atom", "research", "biology"],
        "color_scheme": {"bg": (15, 5, 25), "accent": (180, 100, 255), "text": (230, 210, 255)},
    },

    # ── News topics (web search + AI summarization) ────────────────────────────

    "sports": {
        "name": "Sports News",
        "name_hi": "खेल समाचार",
        "emoji": "🏆",
        "type": "news",
        "music_mood": "electronic upbeat discovery",
        "hashtags": "#sports #sportsnews #cricket #football #olympics #IPL #FIFA #athlete #India #cosmoscapsule",
        "hashtags_hi": "#खेल #क्रिकेट #फुटबॉल #ओलंपिक #आईपीएल #भारत #खिलाड़ी #समाचार #cosmoscapsule",
        "image_keywords": ["cricket stadium", "football match", "olympic stadium", "sports arena", "athlete"],
        "color_scheme": {"bg": (5, 15, 5), "accent": (255, 200, 50), "text": (255, 250, 210)},
        "news_queries": [
            "latest sports news India today",
            "cricket news today IPL",
            "football news today FIFA",
            "Olympics sports news latest",
            "India sports achievement today",
        ],
    },

    "worldnews": {
        "name": "World News",
        "name_hi": "विश्व समाचार",
        "emoji": "🌐",
        "type": "news",
        "music_mood": "epic orchestral historical",
        "hashtags": "#worldnews #politics #NASA #spaceagency #war #geopolitics #breakingnews #India #global #cosmoscapsule",
        "hashtags_hi": "#विश्वसमाचार #राजनीति #नासा #युद्ध #भारत #वैश्विक #ताजाखबर #cosmoscapsule",
        "image_keywords": ["world map", "united nations", "space rocket launch", "news broadcast", "globe politics"],
        "color_scheme": {"bg": (20, 5, 5), "accent": (255, 100, 80), "text": (255, 225, 220)},
        "news_queries": [
            "NASA space news today",
            "India politics news today",
            "world war conflict news today",
            "ISRO space mission news",
            "global political news today",
            "India government news today",
            "international news today important",
        ],
    },
}

# ── Languages ──────────────────────────────────────────────────────────────────

LANGUAGES = {
    "en": {
        "code":        "en",
        "name":        "English",
        "follow_text": "Follow for daily facts  ✨",
        "font_url":    None,   # uses system font (Liberation/DejaVu)
    },
    "hi": {
        "code":        "hi",
        "name":        "हिंदी",
        "follow_text": "रोज़ नई जानकारी के लिए फॉलो करें  ✨",
        "font_url":    "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf",
        "font_url_reg":"https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
    },
}

# ── Schedule: (topic, language, hour_IST, minute_IST) ─────────────────────────
# 12 reels/day — every 2 hours from 7 AM to 9 PM IST

SCHEDULE = [
    ("space",     "en",  7,  0),   # 7:00 AM  — Space English
    ("space",     "hi",  8,  0),   # 8:00 AM  — Space Hindi
    ("history",   "en",  9,  0),   # 9:00 AM  — History English
    ("history",   "hi", 10,  0),   # 10:00 AM — History Hindi
    ("geography", "en", 11,  0),   # 11:00 AM — Geography English
    ("geography", "hi", 12,  0),   # 12:00 PM — Geography Hindi
    ("science",   "en", 13,  0),   # 1:00 PM  — Science English
    ("science",   "hi", 14,  0),   # 2:00 PM  — Science Hindi
    ("sports",    "en", 15,  0),   # 3:00 PM  — Sports English
    ("sports",    "hi", 16,  0),   # 4:00 PM  — Sports Hindi
    ("worldnews", "en", 17,  0),   # 5:00 PM  — World News English
    ("worldnews", "hi", 21,  0),   # 9:00 PM  — World News Hindi (prime time)
]

# ── Video specs ────────────────────────────────────────────────────────────────
REEL_WIDTH    = 1080
REEL_HEIGHT   = 1920
REEL_DURATION = 20
REEL_FPS      = 30
MUSIC_VOLUME  = 0.38
