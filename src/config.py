"""
src/config.py — All topic definitions, languages, and global constants.
6 topics × 2 languages (English + Hindi) = 12 reels/day

Hashtag strategy:
- Mix of high volume (1M+), medium (100K-1M), and niche (<100K) tags
- Niche tags get MORE engagement per post than mega tags
- Include brand tag #cosmoscapsule on every post for discovery
- Rotate between 3 hashtag sets per topic to avoid shadowban
- Max 30 hashtags per post (Instagram limit)
"""

import random

# ── Hashtag sets (3 rotating sets per topic per language) ─────────────────────
# Each set has 28 tags — mix of sizes for maximum reach

HASHTAG_SETS = {

    "space_en": [
        # Set A — Discovery & Education focused
        "#space #universe #astronomy #NASA #cosmos #spacefacts #didyouknow "
        "#astrophysics #blackhole #galaxy #sciencefacts #learneveryday "
        "#knowledgeispower #education #reels #reelsinstagram #reelsviral "
        "#viralreels #explorepage #explore #trending #instagramreels "
        "#sciencelovers #spaceexploration #ISRO #hubble #milkyway #cosmoscapsule",

        # Set B — Viral & Trending focused
        "#spacefacts #universeisbeautiful #nasagram #cosmicwonder #stargaze "
        "#astronomy101 #sciencedaily #mindblown #amazingfacts #factsdaily "
        "#interestingfacts #dailyfacts #reelsviral #reelsvideos #viral "
        "#viralposts #explorepage🔍 #foryou #foryoupage #fyp "
        "#instagramreels #reelsindia #indianreels #educationalreels "
        "#learnwithreel #spacenerd #cosmosfacts #cosmoscapsule",

        # Set C — India & Hindi audience crossover
        "#space #NASA #ISRO #chandrayaan #indianspace #sciencefacts "
        "#knowledgedose #factcheck #amazingworld #universefacts "
        "#spacescience #cosmicfacts #reelstrending #reelsexplore "
        "#viralvideo #trendingvideo #instareels #reelsindia "
        "#educationindia #learnindian #gyaan #factsinhindi "
        "#scienceindia #indiastudents #studymotivation #cosmoscapsule",
    ],

    "space_hi": [
        "#अंतरिक्ष #ब्रह्मांड #विज्ञान #नासा #इसरो #तथ्य #ज्ञान "
        "#शिक्षा #रोचकतथ्य #अद्भुततथ्य #विज्ञानतथ्य #अंतरिक्षविज्ञान "
        "#reels #reelsviral #reelsindia #instagramreels #viral "
        "#trending #foryou #explorepage #hindireels #hindipost "
        "#हिंदी #हिंदीरील्स #ज्ञानकीबातें #रोजनयातथ्य "
        "#विज्ञानप्रेमी #cosmoscapsule",

        "#space #universe #isro #chandrayaan #अंतरिक्ष #ब्रह्मांड "
        "#विज्ञान #तथ्य #ज्ञान #शिक्षा #reelsviral #reelsindia "
        "#hindireels #viralreels #trending #foryoupage #fyp "
        "#explorepage #instagramreels #educationalreels "
        "#हिंदीशिक्षा #भारत #indianstudents #gyaandose "
        "#factsinhindi #dailyfacts #cosmoscapsule",

        "#अंतरिक्ष #नासा #इसरो #ब्रह्मांड #तारे #ग्रह #आकाशगंगा "
        "#विज्ञान #तथ्य #रोचकजानकारी #ज्ञानवर्धक #शिक्षाप्रद "
        "#reels #viral #trending #hindireels #reelsindia "
        "#instagramreels #foryou #explorepage #हिंदी "
        "#भारतीयशिक्षा #स्टूडेंट्स #पढ़ाई #cosmoscapsule",
    ],

    "history_en": [
        "#history #worldhistory #historyfacts #ancienthistory #historybuff "
        "#civilization #didyouknow #amazingfacts #factsdaily #historydaily "
        "#ancientcivilization #historicalfacts #reelsviral #reelsinstagram "
        "#viral #trending #explorepage #foryou #fyp #instagramreels "
        "#educationalcontent #learneveryday #knowledgeispower "
        "#historylovers #ancientworld #mythology #historynerd #cosmoscapsule",

        "#history #ancient #egypt #rome #medieval #renaissance "
        "#worldwar #historyfacts #historybuff #didyouknow #mindblown "
        "#amazinghistory #factcheck #interestingfacts #dailyfacts "
        "#reelsviral #viralreels #reelsindia #instagramreels "
        "#explorepage🔍 #foryoupage #trending #viral #education "
        "#historyteacher #historylesson #historytime #cosmoscapsule",

        "#historyfacts #ancienthistory #historybuff #worldhistory "
        "#historicalevent #ancientcivilization #greekmythology "
        "#romanempire #egyptianhistory #medievalhistory "
        "#reels #reelsviral #viral #trending #foryou "
        "#explorepage #instagramreels #educationalreels "
        "#factsdaily #amazingfacts #knowledgedose #learnhistory "
        "#historyisfun #pastfacts #historynerd #cosmoscapsule",
    ],

    "history_hi": [
        "#इतिहास #विश्वइतिहास #इतिहासतथ्य #प्राचीनइतिहास #सभ्यता "
        "#तथ्य #ज्ञान #शिक्षा #रोचकतथ्य #इतिहासप्रेमी "
        "#reels #reelsviral #reelsindia #instagramreels #viral "
        "#trending #foryou #explorepage #hindireels #हिंदी "
        "#हिंदीरील्स #ज्ञानकीबातें #इतिहासकीबातें #भारतीयइतिहास "
        "#indianhistory #ancientindia #cosmoscapsule",

        "#इतिहास #प्राचीनभारत #मुगलसाम्राज्य #ब्रिटिशराज #स्वतंत्रता "
        "#इतिहासतथ्य #तथ्य #ज्ञान #reelsviral #hindireels "
        "#reelsindia #viral #trending #foryoupage #explorepage "
        "#instagramreels #हिंदी #भारत #indianhistory "
        "#historyinhindi #इतिहासप्रेमी #ऐतिहासिक #cosmoscapsule",

        "#इतिहास #विश्वइतिहास #रोचकइतिहास #ऐतिहासिकतथ्य "
        "#प्राचीनसभ्यता #reels #viral #trending #hindireels "
        "#reelsindia #instagramreels #foryou #explorepage "
        "#हिंदीशिक्षा #ज्ञानवर्धक #शिक्षाप्रद #इतिहासज्ञान "
        "#भारतीयइतिहास #worldhistory #historyfacts #cosmoscapsule",
    ],

    "geography_en": [
        "#geography #earthfacts #nature #travel #countries #geographyfacts "
        "#amazingearth #worldgeography #naturefacts #earthscience "
        "#didyouknow #amazingfacts #factsdaily #reelsviral #reelsinstagram "
        "#viral #trending #explorepage #foryou #fyp #instagramreels "
        "#travelreels #naturereels #educationalcontent #learneveryday "
        "#planetearth #worldwonders #naturelover #cosmoscapsule",

        "#geography #mountains #oceans #rivers #countries #deserts "
        "#forests #islands #volcanoes #earthfacts #naturefacts "
        "#amazingworld #wondersoftheworld #travelfacts #geofacts "
        "#reelsviral #viralreels #reelsindia #instagramreels "
        "#explorepage🔍 #foryoupage #trending #viral #education "
        "#naturephotography #travelgram #wanderlust #cosmoscapsule",

        "#geography #earthscience #worldmap #continents #oceans "
        "#amazingnature #naturalwonders #geographylovers "
        "#naturefacts #travelfacts #worldfacts #countryfacts "
        "#reels #reelsviral #viral #trending #foryou "
        "#explorepage #instagramreels #educationalreels "
        "#factsdaily #amazingfacts #knowledgedose #cosmoscapsule",
    ],

    "geography_hi": [
        "#भूगोल #पृथ्वी #प्रकृति #यात्रा #देश #भूगोलतथ्य "
        "#तथ्य #ज्ञान #शिक्षा #रोचकतथ्य #प्राकृतिकतथ्य "
        "#reels #reelsviral #reelsindia #instagramreels #viral "
        "#trending #foryou #explorepage #hindireels #हिंदी "
        "#हिंदीरील्स #ज्ञानकीबातें #भारतकीजानकारी "
        "#geographyinhindi #भूगोलज्ञान #cosmoscapsule",

        "#भूगोल #पहाड़ #नदी #समुद्र #देश #रेगिस्तान #जंगल "
        "#तथ्य #ज्ञान #reelsviral #hindireels #reelsindia "
        "#viral #trending #foryoupage #explorepage "
        "#instagramreels #हिंदी #भारत #प्रकृति "
        "#यात्रा #travelhindi #naturehindi #cosmoscapsule",

        "#भूगोल #विश्वभूगोल #रोचकभूगोल #भूगोलतथ्य "
        "#पृथ्वीतथ्य #reels #viral #trending #hindireels "
        "#reelsindia #instagramreels #foryou #explorepage "
        "#हिंदीशिक्षा #ज्ञानवर्धक #शिक्षाप्रद #cosmoscapsule",
    ],

    "science_en": [
        "#science #sciencefacts #biology #physics #chemistry #humanbody "
        "#sciencelovers #didyouknow #amazingfacts #factsdaily "
        "#sciencedaily #mindblown #sciencenerd #stemlearning "
        "#reelsviral #reelsinstagram #viral #trending #explorepage "
        "#foryou #fyp #instagramreels #educationalcontent "
        "#learneveryday #knowledgeispower #scienceeducation "
        "#funscience #sciencemindblown #cosmoscapsule",

        "#science #physics #chemistry #biology #neuroscience "
        "#evolution #genetics #quantum #sciencefacts #mindblown "
        "#amazingscience #scienceisfun #techscience #stemkids "
        "#reelsviral #viralreels #reelsindia #instagramreels "
        "#explorepage🔍 #foryoupage #trending #viral #education "
        "#scienceteacher #learnscience #sciencebuff #cosmoscapsule",

        "#sciencefacts #humanbody #brainfacts #physicsfacts "
        "#chemistryfacts #biologyfacts #sciencelovers "
        "#amazingscience #sciencenerd #stemlearning "
        "#reels #reelsviral #viral #trending #foryou "
        "#explorepage #instagramreels #educationalreels "
        "#factsdaily #amazingfacts #knowledgedose #cosmoscapsule",
    ],

    "science_hi": [
        "#विज्ञान #विज्ञानतथ्य #भौतिकी #रसायन #जीवविज्ञान "
        "#मानवशरीर #तथ्य #ज्ञान #शिक्षा #रोचकतथ्य "
        "#reels #reelsviral #reelsindia #instagramreels #viral "
        "#trending #foryou #explorepage #hindireels #हिंदी "
        "#हिंदीरील्स #विज्ञानप्रेमी #scienceinhindi #cosmoscapsule",

        "#विज्ञान #भौतिकी #रसायनशास्त्र #जीवविज्ञान #तंत्रिकाविज्ञान "
        "#तथ्य #ज्ञान #reelsviral #hindireels #reelsindia "
        "#viral #trending #foryoupage #explorepage "
        "#instagramreels #हिंदी #भारत #विज्ञानशिक्षा "
        "#scienceinhindi #विज्ञानज्ञान #cosmoscapsule",

        "#विज्ञान #अद्भुतविज्ञान #रोचकविज्ञान #विज्ञानतथ्य "
        "#reels #viral #trending #hindireels #reelsindia "
        "#instagramreels #foryou #explorepage "
        "#हिंदीशिक्षा #ज्ञानवर्धक #शिक्षाप्रद #cosmoscapsule",
    ],

    "sports_en": [
        "#sports #sportsnews #cricket #IPL #football #FIFA #olympics "
        "#athlete #India #sportsfacts #cricketlovers #sportsreels "
        "#cricketfans #sportsmotivation #didyouknow #amazingfacts "
        "#reelsviral #reelsinstagram #viral #trending #explorepage "
        "#foryou #fyp #instagramreels #sportsday #sportsindia "
        "#cricketindia #ipl2026 #cosmoscapsule",

        "#cricket #IPL #virat #rohit #football #neymar #messi "
        "#olympics #sportsnews #sportsupdate #cricketfever "
        "#cricketworld #footballfever #sportslover #athlete "
        "#reelsviral #viralreels #reelsindia #instagramreels "
        "#explorepage🔍 #foryoupage #trending #viral "
        "#sportstagram #sportslife #sportsmotivation #cosmoscapsule",

        "#sports #cricket #football #badminton #hockey #kabaddi "
        "#indiansports #sportsnews #sportsfacts #sportsreels "
        "#athletelife #sportsworld #olympicgames "
        "#reels #reelsviral #viral #trending #foryou "
        "#explorepage #instagramreels #sportsindiaofficial "
        "#bcci #ipl #cosmoscapsule",
    ],

    "sports_hi": [
        "#खेल #क्रिकेट #फुटबॉल #ओलंपिक #आईपीएल #भारत "
        "#खिलाड़ी #समाचार #खेलसमाचार #क्रिकेटप्रेमी "
        "#reels #reelsviral #reelsindia #instagramreels #viral "
        "#trending #foryou #explorepage #hindireels #हिंदी "
        "#हिंदीरील्स #खेलभावना #sportsinhindi #cosmoscapsule",

        "#क्रिकेट #आईपीएल #विराट #रोहित #फुटबॉल #बैडमिंटन "
        "#खेल #खेलसमाचार #reelsviral #hindireels #reelsindia "
        "#viral #trending #foryoupage #explorepage "
        "#instagramreels #हिंदी #भारत #भारतीयखेल "
        "#sportsinhindi #खेलप्रेमी #cosmoscapsule",

        "#खेल #क्रिकेट #हॉकी #कबड्डी #बैडमिंटन #ओलंपिक "
        "#खेलसमाचार #भारतीयखेल #reels #viral #trending "
        "#hindireels #reelsindia #instagramreels #foryou "
        "#explorepage #हिंदीशिक्षा #खेलभारत #cosmoscapsule",
    ],

    "worldnews_en": [
        "#worldnews #breakingnews #politics #NASA #ISRO #spaceagency "
        "#geopolitics #currentaffairs #newsupdate #todaynews "
        "#didyouknow #amazingfacts #factsdaily #newsfacts "
        "#reelsviral #reelsinstagram #viral #trending #explorepage "
        "#foryou #fyp #instagramreels #educationalcontent "
        "#awareness #globalaffairs #newsdaily #infonews #cosmoscapsule",

        "#worldnews #politics #war #conflict #diplomacy #NASA "
        "#spacenews #isronews #breakingnews #currentevents "
        "#newsreels #politicsnews #globalcrisis #worldaffairs "
        "#reelsviral #viralreels #reelsindia #instagramreels "
        "#explorepage🔍 #foryoupage #trending #viral "
        "#newsoftheday #dailynews #awarenessposts #cosmoscapsule",

        "#worldnews #india #politics #government #NASA #ISRO "
        "#spaceexploration #breakingnews #newsupdate #factsnews "
        "#globalaffairs #worldpolitics #currentaffairs "
        "#reels #reelsviral #viral #trending #foryou "
        "#explorepage #instagramreels #newsdaily "
        "#informative #awareness #cosmoscapsule",
    ],

    "worldnews_hi": [
        "#विश्वसमाचार #राजनीति #नासा #इसरो #युद्ध #भारत "
        "#वैश्विक #ताजाखबर #समाचार #खबरें #आजकीखबर "
        "#reels #reelsviral #reelsindia #instagramreels #viral "
        "#trending #foryou #explorepage #hindireels #हिंदी "
        "#हिंदीरील्स #हिंदीसमाचार #newsinhindi #cosmoscapsule",

        "#विश्वसमाचार #भारत #राजनीति #सरकार #नासा #इसरो "
        "#ताजासमाचार #खबरें #reelsviral #hindireels #reelsindia "
        "#viral #trending #foryoupage #explorepage "
        "#instagramreels #हिंदी #भारतसमाचार "
        "#newsinhindi #hindinews #cosmoscapsule",

        "#विश्वसमाचार #अंतर्राष्ट्रीयसमाचार #राजनीति #युद्ध "
        "#शांति #कूटनीति #reels #viral #trending #hindireels "
        "#reelsindia #instagramreels #foryou #explorepage "
        "#हिंदीखबरें #समाचार #ताजाखबर #cosmoscapsule",
    ],
}


def get_hashtags(topic_key: str, lang: str) -> str:
    """Returns a randomly selected hashtag set for the topic+language combo."""
    key = f"{topic_key}_{lang}"
    sets = HASHTAG_SETS.get(key, [f"#cosmoscapsule #{topic_key}"])
    return random.choice(sets)


# ── Topics ─────────────────────────────────────────────────────────────────────

TOPICS = {

    "space": {
        "name":     "Space & Universe",
        "name_hi":  "अंतरिक्ष और ब्रह्मांड",
        "emoji":    "🚀",
        "type":     "fact",
        "music_mood": "ambient cinematic space",
        "image_keywords": ["galaxy", "nebula", "cosmos", "planets", "stars", "milky way", "space telescope"],
        "color_scheme": {"bg": (5, 5, 25), "accent": (100, 180, 255), "text": (220, 240, 255)},
    },

    "history": {
        "name":     "World History",
        "name_hi":  "विश्व इतिहास",
        "emoji":    "📜",
        "type":     "fact",
        "music_mood": "epic orchestral historical",
        "image_keywords": ["ancient ruins", "historical monument", "medieval castle", "roman colosseum", "pyramid"],
        "color_scheme": {"bg": (25, 15, 5), "accent": (200, 150, 80), "text": (255, 240, 210)},
    },

    "geography": {
        "name":     "Geography",
        "name_hi":  "भूगोल",
        "emoji":    "🌍",
        "type":     "fact",
        "music_mood": "nature acoustic world",
        "image_keywords": ["mountain landscape", "ocean aerial", "rainforest", "desert dunes", "waterfall", "river"],
        "color_scheme": {"bg": (5, 20, 10), "accent": (80, 200, 120), "text": (210, 255, 225)},
    },

    "science": {
        "name":     "Science Facts",
        "name_hi":  "विज्ञान तथ्य",
        "emoji":    "🔬",
        "type":     "fact",
        "music_mood": "electronic upbeat discovery",
        "image_keywords": ["laboratory", "dna strand", "microscope", "chemistry", "atom", "research", "biology"],
        "color_scheme": {"bg": (15, 5, 25), "accent": (180, 100, 255), "text": (230, 210, 255)},
    },

    "sports": {
        "name":     "Sports News",
        "name_hi":  "खेल समाचार",
        "emoji":    "🏆",
        "type":     "news",
        "music_mood": "electronic upbeat discovery",
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
        "name":     "World News",
        "name_hi":  "विश्व समाचार",
        "emoji":    "🌐",
        "type":     "news",
        "music_mood": "epic orchestral historical",
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
        "font_url":    None,
    },
    "hi": {
        "code":        "hi",
        "name":        "हिंदी",
        "follow_text": "रोज़ नई जानकारी के लिए फॉलो करें  ✨",
        "font_url":    "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf",
        "font_url_reg":"https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
    },
}

# ── Schedule ───────────────────────────────────────────────────────────────────

SCHEDULE = [
    ("space",     "en",  7,  0),
    ("space",     "hi",  8,  0),
    ("history",   "en",  9,  0),
    ("history",   "hi", 10,  0),
    ("geography", "en", 11,  0),
    ("geography", "hi", 12,  0),
    ("science",   "en", 13,  0),
    ("science",   "hi", 14,  0),
    ("sports",    "en", 15,  0),
    ("sports",    "hi", 16,  0),
    ("worldnews", "en", 17,  0),
    ("worldnews", "hi", 21,  0),
]

# ── Video specs ────────────────────────────────────────────────────────────────
REEL_WIDTH    = 1080
REEL_HEIGHT   = 1920
REEL_DURATION = 20
REEL_FPS      = 30
MUSIC_VOLUME  = 0.38
