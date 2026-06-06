"""
src/config.py — All topic definitions and global constants
"""

TOPICS = {
    "space": {
        "name": "Space & Universe",
        "emoji": "🚀",
        "music_mood": "ambient cinematic space",
        "hashtags": (
            "#space #universe #astronomy #NASA #cosmos #sciencefacts "
            "#didyouknow #spacefacts #blackhole #astrophysics #education"
        ),
        "image_keywords": ["galaxy", "nebula", "cosmos", "planets", "stars", "milky way"],
        "color_scheme": {
            "bg":     (5,  5,  25),
            "accent": (100, 180, 255),
            "text":   (220, 240, 255),
        },
    },
    "history": {
        "name": "World History",
        "emoji": "📜",
        "music_mood": "epic orchestral historical",
        "hashtags": (
            "#history #worldhistory #historyfacts #ancient #civilization "
            "#facts #didyouknow #historybuff #education #ancienthistory"
        ),
        "image_keywords": ["ancient ruins", "historical monument", "medieval castle", "roman colosseum"],
        "color_scheme": {
            "bg":     (25, 15,  5),
            "accent": (200, 150, 80),
            "text":   (255, 240, 210),
        },
    },
    "geography": {
        "name": "Geography",
        "emoji": "🌍",
        "music_mood": "nature acoustic world",
        "hashtags": (
            "#geography #worldgeography #earthfacts #nature #travel "
            "#countries #facts #didyouknow #geographyfacts #earth"
        ),
        "image_keywords": ["mountain landscape", "ocean aerial", "rainforest", "desert dunes", "waterfall"],
        "color_scheme": {
            "bg":     (5,  20, 10),
            "accent": (80, 200, 120),
            "text":   (210, 255, 225),
        },
    },
    "science": {
        "name": "Science Facts",
        "emoji": "🔬",
        "music_mood": "electronic upbeat discovery",
        "hashtags": (
            "#science #sciencefacts #biology #physics #chemistry "
            "#facts #didyouknow #sciencelovers #education #stem"
        ),
        "image_keywords": ["laboratory", "dna strand", "microscope", "chemistry", "atom", "research"],
        "color_scheme": {
            "bg":     (15,  5, 25),
            "accent": (180, 100, 255),
            "text":   (230, 210, 255),
        },
    },
}

# Video specs
REEL_WIDTH    = 1080
REEL_HEIGHT   = 1920
REEL_DURATION = 20     # seconds
REEL_FPS      = 30
MUSIC_VOLUME  = 0.38   # 0.0 → 1.0
