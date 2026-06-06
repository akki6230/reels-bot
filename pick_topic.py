"""
src/pick_topic.py
Determines which topic to post based on:
  - Manual trigger input (workflow_dispatch)
  - UTC hour of the GitHub Actions cron run
Outputs a GitHub Actions step output: topic=<name>
"""

import os
import sys
from datetime import datetime, timezone

# Map UTC hours → topics (matches the cron schedule in the workflow)
#   3:30 UTC  = 9:00 AM IST  → space
#   7:30 UTC  = 1:00 PM IST  → history
#  12:30 UTC  = 6:00 PM IST  → geography or science (alternating days)
HOUR_TOPIC_MAP = {
    3: "space",
    7: "history",
    12: "geography",   # overridden by day-of-week below
}

DAY_EVENING_TOPIC = {
    0: "geography",   # Monday
    1: "science",     # Tuesday
    2: "geography",   # Wednesday
    3: "science",     # Thursday
    4: "geography",   # Friday
    5: "science",     # Saturday
    6: "science",     # Sunday
}

VALID_TOPICS = ["space", "history", "geography", "science"]


def set_output(name: str, value: str):
    """Write a GitHub Actions step output."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"{name}={value}\n")
    else:
        # Local dev fallback
        print(f"::set-output name={name}::{value}")
    print(f"[pick_topic] Selected topic: {value}")


def main():
    event = os.environ.get("GITHUB_EVENT_NAME", "schedule")
    now_utc = datetime.now(timezone.utc)
    utc_hour = now_utc.hour
    weekday = now_utc.weekday()   # 0=Monday

    # Manual trigger → use the provided input
    if event == "workflow_dispatch":
        topic = os.environ.get("INPUT_TOPIC", "space").strip().lower()
        if topic not in VALID_TOPICS:
            print(f"[pick_topic] Unknown topic '{topic}', defaulting to 'space'")
            topic = "space"
        set_output("topic", topic)
        return

    # Scheduled run → derive from UTC hour
    topic = HOUR_TOPIC_MAP.get(utc_hour)
    if topic is None:
        # Fallback: guess from closest hour
        closest = min(HOUR_TOPIC_MAP.keys(), key=lambda h: abs(h - utc_hour))
        topic = HOUR_TOPIC_MAP[closest]

    # Evening slot (12 UTC): alternate geography/science by weekday
    if utc_hour == 12:
        topic = DAY_EVENING_TOPIC.get(weekday, "geography")

    set_output("topic", topic)


if __name__ == "__main__":
    main()
