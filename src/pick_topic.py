"""
src/pick_topic.py — 3 reels/day, all Hindi, 5 topics rotating by day.
"""

import os
from datetime import datetime, timezone

DAY_ROTATION = {
    0: ("psychology",   "mindblowing",  "space"),
    1: ("mindblowing",  "space",        "sciencewrong"),
    2: ("space",        "sciencewrong", "earthglitch"),
    3: ("sciencewrong", "earthglitch",  "psychology"),
    4: ("earthglitch",  "psychology",   "mindblowing"),
    5: ("psychology",   "space",        "mindblowing"),
    6: ("mindblowing",  "earthglitch",  "space"),
}

HOUR_SLOT = {
    3:  0,    # 9:00 AM IST
    7:  1,    # 1:00 PM IST
    13: 2,    # 7:00 PM IST
}

VALID_TOPICS = ["psychology", "mindblowing", "space", "sciencewrong", "earthglitch"]


def set_output(name: str, value: str):
    gop = os.environ.get("GITHUB_OUTPUT")
    if gop:
        with open(gop, "a") as f:
            f.write(f"{name}={value}\n")
    print(f"[pick_topic] {name}={value}")


def main():
    event    = os.environ.get("GITHUB_EVENT_NAME", "schedule")
    now_utc  = datetime.now(timezone.utc)
    utc_hour = now_utc.hour
    weekday  = now_utc.weekday()

    if event == "workflow_dispatch":
        topic = os.environ.get("INPUT_TOPIC", "space").strip().lower()
        topic = topic if topic in VALID_TOPICS else "space"
        set_output("topic", topic)
        set_output("lang",  "hi")
        return

    slot_idx = HOUR_SLOT.get(utc_hour)
    if slot_idx is None:
        closest  = min(HOUR_SLOT.keys(), key=lambda h: abs(h - utc_hour))
        slot_idx = HOUR_SLOT[closest]

    day_topics = DAY_ROTATION.get(weekday, ("psychology", "mindblowing", "space"))
    topic      = day_topics[slot_idx]

    set_output("topic", topic)
    set_output("lang",  "hi")


if __name__ == "__main__":
    main()
