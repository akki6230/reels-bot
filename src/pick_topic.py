"""
src/pick_topic.py — 3 reels/day, all Hindi, 7 topics rotating by day.
GK and ExamFacts appear every day — highly viral for Indian audience.
"""

import os
from datetime import datetime, timezone
from config import DAY_ROTATION

VALID_TOPICS = list(__import__('config').TOPICS.keys())

HOUR_SLOT = {
    3:  0,   # 9:00 AM IST
    7:  1,   # 1:00 PM IST
    13: 2,   # 7:00 PM IST
}


def set_output(name: str, value: str):
    gop = os.environ.get("GITHUB_OUTPUT")
    if gop:
        with open(gop, "a") as f:
            f.write(f"{name}={value}\n")
    print(f"[pick_topic] {name}={value}")


def main():
    event    = os.environ.get("EVENT_NAME", "schedule")
    now_utc  = datetime.now(timezone.utc)
    utc_hour = now_utc.hour
    weekday  = now_utc.weekday()

    if event == "workflow_dispatch":
        topic = os.environ.get("INPUT_TOPIC", "").strip().lower()
        if not topic or topic not in VALID_TOPICS:
            topic = "gk"
        print(f"[pick_topic] Manual trigger → topic={topic}")
        set_output("topic", topic)
        set_output("lang",  "hi")
        return

    slot_idx = HOUR_SLOT.get(utc_hour)
    if slot_idx is None:
        closest  = min(HOUR_SLOT.keys(), key=lambda h: abs(h - utc_hour))
        slot_idx = HOUR_SLOT[closest]

    day_topics = DAY_ROTATION.get(weekday, ("gk", "mindblowing", "space"))
    topic      = day_topics[slot_idx]

    set_output("topic", topic)
    set_output("lang",  "hi")


if __name__ == "__main__":
    main()
