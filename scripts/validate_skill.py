#!/usr/bin/env python3
"""Self-contained structural check for the quality-gates skill.

This does not depend on Anthropic's skill-creator tooling — it exists so this
repo can validate itself in any plain Python environment (a laptop, CI), not
only inside a Claude Code / Cowork session. It checks the same basics
skill-creator's quick_validate.py checks: valid frontmatter, required fields,
and a SKILL.md that stays within the recommended size so it loads cheaply.

Usage:
    python scripts/validate_skill.py [path/to/skill]   # defaults to skill/quality-gates
Exit code is non-zero on any failure, so this is safe to wire into a runner.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

MAX_RECOMMENDED_LINES = 500
REQUIRED_FIELDS = ("name", "description")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {}, text
    raw, body = m.group(1), m.group(2)
    fm: dict[str, str] = {}
    key = None
    for line in raw.splitlines():
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*:", line):
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip().strip(">-").strip()
        elif key and line.strip():
            fm[key] += " " + line.strip()
    return fm, body


def _check_resources_section(skill_dir: Path, body: str, errors: list) -> None:
    # Cross-check bundled-resource paths named in the "## Resources" section only.
    # The rest of the body is full of *example* paths (files the skill writes
    # into a target project, like CLAUDE.md or docs/quality-gates.md) which are
    # not supposed to exist inside the skill package itself — checking those
    # would flag correct skills as broken.
    resources_match = re.search(r"^## Resources\n(.*?)(?:\n## |\Z)", body, re.S | re.M)
    if resources_match:
        for rel in re.findall(r"`([\w./-]+\.(?:md|py|sh))`", resources_match.group(1)):
            if not (skill_dir / rel).exists():
                errors.append(f"SKILL.md's Resources section references '{rel}' "
                              "but that file does not exist in the skill.")


def validate(skill_dir: Path) -> list[str]:
    errors = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"SKILL.md not found at {skill_md}"]

    text = skill_md.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    if not fm:
        errors.append("No YAML frontmatter found (expected --- name/description --- block).")
    for field in REQUIRED_FIELDS:
        if not fm.get(field):
            errors.append(f"Frontmatter missing required field: {field}")

    name = fm.get("name", "")
    if name and name != skill_dir.name:
        errors.append(f"Frontmatter name '{name}' does not match directory name '{skill_dir.name}'")

    desc = fm.get("description", "")
    if desc and len(desc) < 40:
        errors.append("Description looks too short to describe when/why to trigger the skill.")

    n_lines = len(text.splitlines())
    if n_lines > MAX_RECOMMENDED_LINES:
        errors.append(f"SKILL.md is {n_lines} lines; recommended limit is {MAX_RECOMMENDED_LINES}. "
                      "Consider moving detail into references/.")

    _check_resources_section(skill_dir, body, errors)

    return errors


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "skill" / "quality-gates"
    errors = validate(target)
    if errors:
        print(f"FAILED — {len(errors)} issue(s) in {target}:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK — {target} passes structural validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
