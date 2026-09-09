#!/usr/bin/env python3
"""Self-contained packager for the quality-gates skill.

Zips skill/quality-gates/ into dist/quality-gates.skill, excluding the evals/
directory (test fixtures and prompts — development-time only, not part of what
ships) and the usual junk (__pycache__, .DS_Store, *.pyc). Runs validate_skill.py
first and refuses to package a skill that fails validation.

Usage:
    python scripts/package_skill.py [path/to/skill] [output-dir]
Defaults: skill/quality-gates -> dist/quality-gates.skill
"""
from __future__ import annotations
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_skill import validate  # noqa: E402

EXCLUDE_DIR_NAMES = {"__pycache__", "node_modules", "evals"}
EXCLUDE_FILE_NAMES = {".DS_Store", ".env"}
EXCLUDE_SUFFIXES = (".pyc", ".pyo")


def should_skip(rel_parts: tuple[str, ...]) -> bool:
    if len(rel_parts) > 1 and rel_parts[1] in EXCLUDE_DIR_NAMES:
        return True
    if rel_parts[-1] in EXCLUDE_FILE_NAMES:
        return True
    if rel_parts[-1].endswith(EXCLUDE_SUFFIXES):
        return True
    return False


def package(skill_dir: Path, output_dir: Path) -> Path | None:
    errors = validate(skill_dir)
    if errors:
        print(f"Refusing to package — {len(errors)} validation issue(s):")
        for e in errors:
            print(f"  - {e}")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{skill_dir.name}.skill"
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(skill_dir.rglob("*")):
            if not path.is_file():
                continue
            arcname = path.relative_to(skill_dir.parent)
            if should_skip(arcname.parts):
                print(f"  skip:  {arcname}")
                continue
            zf.write(path, arcname)
            print(f"  add:   {arcname}")
    print(f"\nOK — wrote {out_path}")
    return out_path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    skill_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "skill" / "quality-gates"
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "dist"
    return 0 if package(skill_dir, output_dir) else 1


if __name__ == "__main__":
    raise SystemExit(main())
