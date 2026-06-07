"""
src/pick_topic.py — 3 reels/day: 2 Hindi + 1 English

Schedule:
  9:00 AM IST (3:30 UTC)  → Hindi   (morning commute peak)
  1:00 PM IST (7:30 UTC)  → English (afternoon international reach)
  7:00 PM IST (13:30 UTC) → Hindi   (prime time — highest Indian traffic)

Topic rotates by day of week for variety.
"""

import os
from datetime import datetime, timezone

# Day of week (0=Mon ... 6=Sun) → (9AM_topic, 1PM_topic, 7PM_topic)
DAY_ROTATION = {
    0: ("space",     "history",   "science"),     # Monday
    1: ("history",   "geography", "space"),       # Tuesday
    2: ("geography", "science",   "history"),     # Wednesday
    3: ("science",   "sports",    "geography"),   # Thursday
    4: ("sports",    "worldnews", "science"),     # Friday
    5: ("worldnews", "space",     "sports"),      # Saturday
    6: ("space",     "science",   "worldnews"),   # Sunday
}

# UTC hour → (slot_index, language)
# 2 Hindi + 1 English per day
HOUR_SLOT = {
    3:  (0, "hi"),   # 9:00 AM IST  → Hindi
    7:  (1, "en"),   # 1:00 PM IST  → English
    13: (2, "hi"),   # 7:00 PM IST  → Hindi (prime time)
}

VALID_TOPICS = ["space", "history", "geography", "science", "sports", "worldnews"]
VALID_LANGS  = ["en", "hi"]


def set_output(name: str, value: str):
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"{name}={value}\n")
    print(f"[pick_topic] {name}={value}")


def main():
    event    = os.environ.get("GITHUB_EVENT_NAME", "schedule")
    now_utc  = datetime.now(timezone.utc)
    utc_hour = now_utc.hour
    weekday  = now_utc.weekday()

    # Manual trigger → use inputs
    if event == "workflow_dispatch":
        topic = os.environ.get("INPUT_TOPIC", "space").strip().lower()
        lang  = os.environ.get("INPUT_LANG",  "hi").strip().lower()
        topic = topic if topic in VALID_TOPICS else "space"
        lang  = lang  if lang  in VALID_LANGS  else "hi"
        set_output("topic", topic)
        set_output("lang",  lang)
        return

    # Scheduled run
    slot_info = HOUR_SLOT.get(utc_hour)
    if slot_info is None:
        closest   = min(HOUR_SLOT.keys(), key=lambda h: abs(h - utc_hour))
        slot_info = HOUR_SLOT[closest]

    slot_idx, lang = slot_info
    day_topics     = DAY_ROTATION.get(weekday, ("space", "history", "science"))
    topic          = day_topics[slot_idx]

    set_output("topic", topic)
    set_output("lang",  lang)


if __name__ == "__main__":
    main()
