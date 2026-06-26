"""
src/apply_audio_update.py — Parses a "🎵 Update trending audio" issue
body and rewrites the TRENDING_AUDIO dict in poster.py accordingly.

Triggered by .github/workflows/update_trending_audio.yml whenever an issue
labeled "audio-update" is opened. Designed to fail loudly (non-zero exit,
clear error) rather than silently writing something wrong — a bad edit to
poster.py would break every future post, so this only ever applies a
change it's confident about.
"""

import os
import re
import sys
from pathlib import Path

ROOT       = Path(__file__).parent.parent
POSTER_PY  = ROOT / "src" / "poster.py"
TOPICS     = ["examfacts", "psychology", "mindblowing", "gk"]

# GitHub issue forms render each field as a "### <label>\n\n<value>" block,
# separated by blank lines, in the order fields were defined in the form.
FIELD_BLOCK_RE = re.compile(
    r"^###\s+(.+?)\s*\n+(.*?)(?=\n###|\Z)", re.DOTALL | re.MULTILINE
)


def parse_issue_body(body: str) -> dict:
    """Extract {field_label: raw_text} from a GitHub issue-form body."""
    fields = {}
    for match in FIELD_BLOCK_RE.finditer(body):
        label = match.group(1).strip()
        value = match.group(2).strip()
        fields[label] = value
    return fields


def extract_ids(raw: str) -> list:
    """
    Pull numeric audio IDs out of a field's raw text. Audio IDs are long
    digit strings; anything that isn't purely digits (placeholder text,
    "_No response_", stray words) is ignored rather than guessed at.
    """
    if not raw or raw.strip().lower() in ("_no response_", "none", ""):
        return []
    ids = []
    for line in raw.splitlines():
        line = line.strip().strip(",")
        if re.fullmatch(r"\d{6,}", line):
            ids.append(line)
        elif line and line.lower() not in ("_no response_",):
            print(f"::warning::Skipping non-numeric line in audio field: {line!r}")
    return ids


def build_new_dict(current: dict, updates: dict, mode: str) -> dict:
    new = dict(current)
    for topic, ids in updates.items():
        if not ids:
            continue  # blank field — leave that topic untouched
        if mode == "Add":
            merged = list(new.get(topic, []))
            for i in ids:
                if i not in merged:
                    merged.append(i)
            new[topic] = merged
        else:  # Replace
            new[topic] = ids
    return new


def render_dict_literal(d: dict) -> str:
    lines = ["TRENDING_AUDIO = {"]
    for topic in TOPICS:
        ids = d.get(topic, [])
        ids_repr = ", ".join(f'"{i}"' for i in ids)
        lines.append(f'    "{topic}": [{ids_repr}],')
    lines.append("}")
    return "\n".join(lines)


def main():
    issue_body = os.environ.get("ISSUE_BODY", "")
    if not issue_body.strip():
        print("::error::ISSUE_BODY is empty — nothing to parse.")
        sys.exit(1)

    fields = parse_issue_body(issue_body)
    print("Parsed issue fields:", list(fields.keys()))

    mode_raw = fields.get("Mode", "Replace").strip()
    mode = "Add" if mode_raw.lower().startswith("add") else "Replace"
    print(f"Mode: {mode}")

    updates = {topic: extract_ids(fields.get(topic, "")) for topic in TOPICS}
    total_new_ids = sum(len(v) for v in updates.values())
    if total_new_ids == 0:
        print("::warning::No valid audio IDs found in any field — nothing to update.")
        # Not a failure — someone may have opened the issue with everything
        # blank by mistake. Exit cleanly so the workflow can comment back
        # without committing a no-op change.
        Path(os.environ.get("GITHUB_OUTPUT", "/dev/null")).open("a").write(
            "changed=false\n"
        )
        return

    src = POSTER_PY.read_text(encoding="utf-8")

    # Locate the existing TRENDING_AUDIO = { ... } block precisely.
    block_re = re.compile(r"TRENDING_AUDIO\s*=\s*\{.*?\n\}", re.DOTALL)
    block_match = block_re.search(src)
    if not block_match:
        print("::error::Could not find TRENDING_AUDIO block in src/poster.py — aborting.")
        sys.exit(1)

    # Reconstruct the *current* dict from the live file so "Add" mode merges
    # against what's actually there, not a stale assumption.
    current = {}
    for topic in TOPICS:
        topic_re = re.compile(rf'"{topic}"\s*:\s*\[(.*?)\]', re.DOTALL)
        m = topic_re.search(block_match.group(0))
        ids_in_file = re.findall(r'"(\d+)"', m.group(1)) if m else []
        current[topic] = ids_in_file

    new_dict = build_new_dict(current, updates, mode)
    new_block = render_dict_literal(new_dict)

    new_src = src[: block_match.start()] + new_block + src[block_match.end() :]
    POSTER_PY.write_text(new_src, encoding="utf-8")

    print("\nUpdated TRENDING_AUDIO block:")
    print(new_block)

    summary_lines = []
    for topic in TOPICS:
        before = len(current.get(topic, []))
        after = len(new_dict.get(topic, []))
        if updates.get(topic):
            summary_lines.append(f"- **{topic}**: {before} → {after} IDs ({mode.lower()}d)")
    summary = "\n".join(summary_lines) if summary_lines else "(no topics changed)"

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write("changed=true\n")
            f.write("summary<<EOF\n")
            f.write(summary + "\n")
            f.write("EOF\n")


if __name__ == "__main__":
    main()
