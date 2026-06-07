"""
src/update_dashboard.py — Updates dashboard/data.json with run stats.

Strategy:
  - Reads existing data.json (cumulative history stored in repo)
  - Appends current run result
  - Writes back to data.json
  - This way history accumulates across runs even though logs are lost

data.json IS committed to repo so it persists between runs.
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


def load_existing() -> dict:
    """Load existing data.json — this is our cumulative history."""
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except Exception:
            pass
    return {
        "generated_at":  "",
        "total_runs":    0,
        "posted":        0,
        "failed":        0,
        "dry_runs":      0,
        "en_posted":     0,
        "hi_posted":     0,
        "success_rate":  0,
        "topic_counts":  {},
        "recent_runs":   [],
        "current_run":   {},
    }


def build_current_run() -> dict:
    """Build current run data from environment + latest log file."""
    run = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topic":     os.environ.get("TOPIC", "unknown"),
        "lang":      os.environ.get("LANG",  "en"),
        "status":    os.environ.get("RUN_STATUS", "unknown").lower(),
        "hook":      "",
        "category":  "",
        "media_id":  "",
        "error":     "",
        "image_source": "",
        "reel_style":   "",
        "duration":     0,
    }

    # Try to enrich from the latest log file written by main.py
    if LOGS_DIR.exists():
        log_files = sorted(LOGS_DIR.glob("run_*.json"), reverse=True)
        for lf in log_files[:3]:   # check last 3
            try:
                log_data = json.loads(lf.read_text())
                # Match topic+lang
                if (log_data.get("topic") == run["topic"] and
                        log_data.get("lang") == run["lang"]):
                    run["hook"]         = log_data.get("hook", "")
                    run["category"]     = log_data.get("category", "")
                    run["media_id"]     = log_data.get("media_id", "")
                    run["error"]        = log_data.get("error", "")
                    run["image_source"] = log_data.get("image_source", "")
                    run["reel_style"]   = log_data.get("reel_style", "")
                    run["duration"]     = log_data.get("duration", 20)
                    # Use status from log if available
                    if log_data.get("status"):
                        run["status"] = log_data["status"]
                    break
            except Exception:
                continue

    return run


def compute_stats(data: dict) -> dict:
    """Recompute all stats from recent_runs history."""
    runs    = data.get("recent_runs", [])
    total   = len(runs)
    posted  = sum(1 for r in runs if r.get("status") == "posted")
    failed  = sum(1 for r in runs if r.get("status") == "failed")
    dry     = sum(1 for r in runs if "dry" in r.get("status", ""))
    en_p    = sum(1 for r in runs if r.get("lang") == "en" and r.get("status") == "posted")
    hi_p    = sum(1 for r in runs if r.get("lang") == "hi" and r.get("status") == "posted")

    topic_counts: dict = {}
    for r in runs:
        if r.get("status") == "posted":
            t = r.get("topic", "unknown")
            topic_counts[t] = topic_counts.get(t, 0) + 1

    return {
        "total_runs":   total,
        "posted":       posted,
        "failed":       failed,
        "dry_runs":     dry,
        "en_posted":    en_p,
        "hi_posted":    hi_p,
        "success_rate": round(posted / total * 100, 1) if total else 0,
        "topic_counts": topic_counts,
    }


def main():
    # 1. Load existing cumulative data
    data = load_existing()

    # 2. Build current run entry
    current = build_current_run()

    # 3. Prepend to recent_runs (keep last 100 entries)
    recent = data.get("recent_runs", [])
    recent.insert(0, current)
    recent = recent[:100]
    data["recent_runs"] = recent

    # 4. Recompute all stats
    stats = compute_stats(data)
    data.update(stats)

    # 5. Update metadata
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    data["current_run"]  = current

    # 6. Write back to dashboard/data.json
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    print(f"✅ Dashboard updated → {DATA_FILE}")
    print(f"   Total: {data['total_runs']} | Posted: {data['posted']} (EN:{data['en_posted']} HI:{data['hi_posted']}) | Failed: {data['failed']}")
    print(f"   Current run: [{current['lang'].upper()}] {current['topic']} → {current['status']}")
    if current.get("hook"):
        print(f"   Hook: {current['hook'][:60]}")


if __name__ == "__main__":
    main()
