"""
src/update_dashboard.py — Writes dashboard/data.json from run logs.
Now tracks topic + language breakdowns.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT      = Path(__file__).parent.parent
LOGS_DIR  = ROOT / "output" / "logs"
DASH_DIR  = ROOT / "dashboard"
DATA_FILE = DASH_DIR / "data.json"
DASH_DIR.mkdir(parents=True, exist_ok=True)

TOPIC_META = {
    "space":     {"emoji": "🚀", "name": "Space & Universe",  "name_hi": "अंतरिक्ष"},
    "history":   {"emoji": "📜", "name": "World History",     "name_hi": "इतिहास"},
    "geography": {"emoji": "🌍", "name": "Geography",         "name_hi": "भूगोल"},
    "science":   {"emoji": "🔬", "name": "Science Facts",     "name_hi": "विज्ञान"},
    "sports":    {"emoji": "🏆", "name": "Sports News",       "name_hi": "खेल"},
    "worldnews": {"emoji": "🌐", "name": "World News",        "name_hi": "विश्व समाचार"},
}


def load_runs() -> list:
    runs = []
    for f in sorted(LOGS_DIR.glob("run_*.json"), reverse=True):
        try:
            runs.append(json.loads(f.read_text()))
        except Exception:
            pass
    return runs


def compute_stats(runs: list) -> dict:
    total    = len(runs)
    posted   = sum(1 for r in runs if r.get("status") == "posted")
    failed   = sum(1 for r in runs if r.get("status") == "failed")
    dry_runs = sum(1 for r in runs if r.get("dry_run"))
    en_count = sum(1 for r in runs if r.get("lang") == "en" and r.get("status") == "posted")
    hi_count = sum(1 for r in runs if r.get("lang") == "hi" and r.get("status") == "posted")

    topic_counts: dict = {}
    for r in runs:
        if r.get("status") == "posted":
            t = r.get("topic", "unknown")
            topic_counts[t] = topic_counts.get(t, 0) + 1

    return {
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "total_runs":    total,
        "posted":        posted,
        "failed":        failed,
        "dry_runs":      dry_runs,
        "en_posted":     en_count,
        "hi_posted":     hi_count,
        "success_rate":  round(posted / total * 100, 1) if total else 0,
        "topic_counts":  topic_counts,
        "recent_runs":   runs[:15],
        "current_run": {
            "status": os.environ.get("RUN_STATUS", "unknown"),
            "topic":  os.environ.get("TOPIC", ""),
            "lang":   os.environ.get("LANG", ""),
        },
    }


def main():
    runs  = load_runs()
    stats = compute_stats(runs)
    DATA_FILE.write_text(json.dumps(stats, indent=2))
    print(f"Dashboard updated → {DATA_FILE}")
    print(f"  Posted: EN={stats['en_posted']} HI={stats['hi_posted']} | Failed={stats['failed']}")


if __name__ == "__main__":
    main()
