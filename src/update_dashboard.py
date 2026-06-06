"""
src/update_dashboard.py — Reads run logs and writes dashboard/data.json
This JSON is served by GitHub Pages and read by the dashboard HTML.
"""

import os
import json
import glob
from pathlib import Path
from datetime import datetime, timezone

ROOT       = Path(__file__).parent.parent
LOGS_DIR   = ROOT / "output" / "logs"
DASH_DIR   = ROOT / "dashboard"
DATA_FILE  = DASH_DIR / "data.json"

DASH_DIR.mkdir(parents=True, exist_ok=True)


def load_all_runs() -> list[dict]:
    runs = []
    for f in sorted(LOGS_DIR.glob("run_*.json"), reverse=True):
        try:
            runs.append(json.loads(f.read_text()))
        except Exception:
            pass
    return runs


def compute_stats(runs: list[dict]) -> dict:
    total      = len(runs)
    posted     = sum(1 for r in runs if r.get("status") == "posted")
    failed     = sum(1 for r in runs if r.get("status") == "failed")
    dry_runs   = sum(1 for r in runs if r.get("dry_run"))
    success_rt = round(posted / total * 100, 1) if total else 0

    topic_counts: dict[str, int] = {}
    for r in runs:
        t = r.get("topic", "unknown")
        topic_counts[t] = topic_counts.get(t, 0) + 1

    # Last 10 runs for the activity feed
    recent = runs[:10]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_runs":   total,
        "posted":       posted,
        "failed":       failed,
        "dry_runs":     dry_runs,
        "success_rate": success_rt,
        "topic_counts": topic_counts,
        "recent_runs":  recent,
        "current_run":  {
            "status": os.environ.get("RUN_STATUS", "unknown"),
            "topic":  os.environ.get("TOPIC", ""),
        },
    }


def main():
    runs  = load_all_runs()
    stats = compute_stats(runs)
    DATA_FILE.write_text(json.dumps(stats, indent=2))
    print(f"Dashboard data written → {DATA_FILE}")
    print(f"  Total runs: {stats['total_runs']} | Posted: {stats['posted']} | Failed: {stats['failed']}")


if __name__ == "__main__":
    main()
