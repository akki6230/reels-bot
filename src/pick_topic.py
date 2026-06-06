"""
src/pick_topic.py — Determines which topic + language to post.
Outputs two GitHub Actions step outputs: topic=<name> lang=<en|hi>
"""

import os
from datetime import datetime, timezone

# Map UTC hour → (topic, lang)  matching cron schedule
# IST = UTC + 5:30, so hour_IST = UTC_hour + 5 (approx, ignoring :30)
HOUR_MAP = {
    1:  ("space",     "en"),   # 7:00 AM IST
    2:  ("space",     "hi"),   # 8:00 AM IST
    3:  ("history",   "en"),   # 9:00 AM IST
    4:  ("history",   "hi"),   # 10:00 AM IST
    5:  ("geography", "en"),   # 11:00 AM IST
    6:  ("geography", "hi"),   # 12:00 PM IST
    7:  ("science",   "en"),   # 1:00 PM IST
    8:  ("science",   "hi"),   # 2:00 PM IST
    9:  ("sports",    "en"),   # 3:00 PM IST
    10: ("sports",    "hi"),   # 4:00 PM IST
    11: ("worldnews", "en"),   # 5:00 PM IST
    15: ("worldnews", "hi"),   # 9:00 PM IST
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
    event     = os.environ.get("GITHUB_EVENT_NAME", "schedule")
    now_utc   = datetime.now(timezone.utc)
    utc_hour  = now_utc.hour

    # Manual trigger
    if event == "workflow_dispatch":
        topic = os.environ.get("INPUT_TOPIC", "space").strip().lower()
        lang  = os.environ.get("INPUT_LANG", "en").strip().lower()
        topic = topic if topic in VALID_TOPICS else "space"
        lang  = lang  if lang  in VALID_LANGS  else "en"
        set_output("topic", topic)
        set_output("lang",  lang)
        return

    # Scheduled — map UTC hour to topic+lang
    pair = HOUR_MAP.get(utc_hour)
    if pair is None:
        closest = min(HOUR_MAP.keys(), key=lambda h: abs(h - utc_hour))
        pair    = HOUR_MAP[closest]

    set_output("topic", pair[0])
    set_output("lang",  pair[1])


if __name__ == "__main__":
    main()
