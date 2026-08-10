#!/usr/bin/env python3
"""Detect the facts a quality-gate decision needs from a project tree.

This script does not decide which gates apply. It gathers evidence — languages,
manifests, test setups, linters, type-checkers, security tooling, CI config, an
existing gate runner, and existing agent-instruction files — so that the caller
can map that evidence to the gate catalog with confidence instead of guessing.

Usage:
    python detect_project.py [ROOT] [--json]

ROOT defaults to the current directory. With --json the report is emitted as a
single JSON object; without it a short human-readable summary is printed. The
script uses only the Python standard library and never writes to the tree.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Directories that never hold source worth scanning. Skipping them keeps the
# walk fast on large repos and avoids counting vendored code as the project's.
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "vendor", "dist", "build",
    "target", ".venv", "venv", "env", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", ".next", ".nuxt", ".gradle",
    ".idea", ".vscode", "coverage", ".tox", "site-packages",
}

# Extension -> language. Used to weigh which languages actually dominate the
# tree, not just which manifest files happen to be present.
EXT_LANG = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
    ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".c": "C", ".h": "C",
    ".cpp": "C++", ".cc": "C++", ".hpp": "C++", ".swift": "Swift",
    ".sh": "Bash", ".bash": "Bash", ".scala": "Scala", ".ex": "Elixir",
    ".exs": "Elixir", ".dart": "Dart", ".lua": "Lua", ".r": "R",
}

# Manifest / build files -> (language, build_system).
MANIFESTS = {
    "package.json": ("JavaScript/TypeScript", "npm/yarn/pnpm"),
    "pyproject.toml": ("Python", "pip/poetry/uv"),
    "setup.py": ("Python", "setuptools"),
    "setup.cfg": ("Python", "setuptools"),
    "requirements.txt": ("Python", "pip"),
    "Pipfile": ("Python", "pipenv"),
    "go.mod": ("Go", "go"),
    "Cargo.toml": ("Rust", "cargo"),
    "pom.xml": ("Java", "maven"),
    "build.gradle": ("Java/Kotlin", "gradle"),
    "build.gradle.kts": ("Java/Kotlin", "gradle"),
    "Gemfile": ("Ruby", "bundler"),
    "composer.json": ("PHP", "composer"),
    "mix.exs": ("Elixir", "mix"),
    "pubspec.yaml": ("Dart", "pub"),
    "CMakeLists.txt": ("C/C++", "cmake"),
    "Makefile": ("(any)", "make"),
    "makefile": ("(any)", "make"),
}

# Config-file fingerprints for each tool class. Presence is a strong signal the
# tool is already wired into the project.
LINTER_CONFIGS = {
    "eslint": [".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json",
               ".eslintrc.yml", ".eslintrc.yaml", "eslint.config.js",
               "eslint.config.mjs"],
    "prettier": [".prettierrc", ".prettierrc.json", ".prettierrc.js",
                 ".prettierrc.yml", "prettier.config.js"],
    "ruff": ["ruff.toml", ".ruff.toml"],
    "flake8": [".flake8", "tox.ini"],
    "pylint": [".pylintrc", "pylintrc"],
    "black": [],  # usually configured inside pyproject.toml
    "golangci-lint": [".golangci.yml", ".golangci.yaml", ".golangci.toml"],
    "clippy/rustfmt": ["rustfmt.toml", ".rustfmt.toml", "clippy.toml"],
    "rubocop": [".rubocop.yml"],
    # C / C++ linters. Policy: prefer "Clean" when present; clang-tidy and
    # cppcheck are the fallbacks. Config-file names for "Clean" are guesses —
    # confirm against the project, and also check the Makefile / CI for a
    # `clean`/`Clean` invocation, since a linter may be wired there with no
    # config file of its own.
    "Clean": [".clean.yml", ".clean.yaml", ".cleanrc", "clean.toml", ".clean.toml"],
    "clang-tidy": [".clang-tidy"],
    "cppcheck": [".cppcheck", "cppcheck.cfg"],
}

# Files / directories that usually hold functional or technical specifications.
# Used to inform the spec-alignment gate — presence is a hint, not proof.
SPEC_DIRS = ["spec", "specs", "docs", "doc", "design", "adr", "rfcs", "requirements"]
SPEC_FILE_PATTERNS = (
    "openapi", "swagger", "requirements", "design", "spec", "rfc", "adr",
)
SPEC_FILE_SUFFIXES = (".feature",)  # Gherkin acceptance specs

TYPECHECK_CONFIGS = {
    "mypy": ["mypy.ini", ".mypy.ini"],
    "pyright": ["pyrightconfig.json"],
    "tsc": ["tsconfig.json", "tsconfig.base.json"],
}

SECURITY_CONFIGS = {
    "detect-secrets": [".secrets.baseline"],
    "gitleaks": [".gitleaks.toml", "gitleaks.toml"],
    "dependabot": [".github/dependabot.yml", ".github/dependabot.yaml"],
    "pre-commit": [".pre-commit-config.yaml"],
}

CI_PATHS = [
    ".github/workflows", ".gitlab-ci.yml", ".circleci/config.yml",
    "azure-pipelines.yml", "Jenkinsfile", ".buildkite", "bitbucket-pipelines.yml",
]

AGENT_INSTRUCTION_FILES = [
    "CLAUDE.md", "AGENTS.md", ".github/copilot-instructions.md",
    "GEMINI.md", ".cursorrules",
]

CURSOR_RULES_DIR = ".cursor/rules"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def exists_any(root: Path, names) -> list:
    return [n for n in names if (root / n).exists()]


def detect(root: Path) -> dict:
    root = root.resolve()
    lang_counts: dict[str, int] = {}
    test_files: list[str] = []
    has_tests_dir = False
    shell_scripts = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, root)
        base = os.path.basename(dirpath).lower()
        if base in {"test", "tests", "spec", "specs", "__tests__"}:
            has_tests_dir = True
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            lang = EXT_LANG.get(ext)
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
            if ext in {".sh", ".bash"}:
                shell_scripts += 1
            low = fn.lower()
            # Common test-file naming conventions across ecosystems.
            if (low.startswith("test_") or low.endswith("_test.py")
                    or low.endswith("_test.go") or ".test." in low
                    or ".spec." in low or low.endswith("_spec.rb")):
                rel = os.path.normpath(os.path.join(rel_dir, fn))
                if len(test_files) < 50:
                    test_files.append(rel)

    languages = sorted(lang_counts, key=lambda k: lang_counts[k], reverse=True)

    manifests_found = {}
    for name, meta in MANIFESTS.items():
        if (root / name).exists():
            manifests_found[name] = {"language": meta[0], "build_system": meta[1]}

    # package.json carries a lot of signal — inspect its scripts and devDeps.
    pkg_scripts, pkg_devdeps = [], []
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(read_text(pkg) or "{}")
            pkg_scripts = list((data.get("scripts") or {}).keys())
            pkg_devdeps = list((data.get("devDependencies") or {}).keys())
            pkg_devdeps += list((data.get("dependencies") or {}).keys())
        except (ValueError, AttributeError):
            pass

    pyproject_text = read_text(root / "pyproject.toml")

    # Build / CI text — a tool may be invoked here with no config file of its
    # own (common for cppcheck, clang-tidy, and a "Clean" linter driven from a
    # Makefile target). Scanning it catches those cases.
    build_ci_text = read_text(root / "Makefile") + read_text(root / "makefile")
    for ci_dir in (".github/workflows", ".circleci"):
        d = root / ci_dir
        if d.is_dir():
            for p in d.rglob("*"):
                if p.is_file():
                    build_ci_text += read_text(p)
    for ci_file in (".gitlab-ci.yml", "azure-pipelines.yml", "Jenkinsfile"):
        build_ci_text += read_text(root / ci_file)
    build_ci_lower = build_ci_text.lower()

    def tool_hits(configs: dict) -> dict:
        hits = {}
        for tool, files in configs.items():
            found = exists_any(root, files)
            key = tool.split("/")[0].lower()
            in_pkg = tool in " ".join(pkg_devdeps).lower() or any(
                key in d.lower() for d in pkg_devdeps)
            in_pyproject = key in pyproject_text.lower()
            # Match the tool name as invoked in build/CI (word-ish boundary to
            # avoid e.g. "clean" matching inside "cleanup").
            in_build = bool(re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])",
                                      build_ci_lower))
            # "clean" as a bare token almost always means the `make clean`
            # artifact-removal target, not the Clean linter. Require a clearer
            # invocation ("clean lint/check/run/analyze") before trusting it.
            if key == "clean" and in_build:
                in_build = bool(re.search(r"clean\s+(lint|check|run|analyz|scan)",
                                          build_ci_lower))
            if found or in_pkg or in_pyproject or in_build:
                hits[tool] = {
                    "config_files": found,
                    "in_package_json": bool(in_pkg),
                    "in_pyproject": bool(in_pyproject),
                    "in_build_or_ci": bool(in_build),
                }
        return hits

    linters = tool_hits(LINTER_CONFIGS)
    if shell_scripts and "shellcheck" not in linters:
        linters["shellcheck (candidate)"] = {
            "config_files": [], "note": f"{shell_scripts} shell script(s) found",
        }
    # Flag C/C++ so the caller applies the "prefer Clean" policy deliberately.
    if any(l in ("C", "C++") for l in languages) and "Clean" not in linters:
        linters["Clean (policy: preferred for C/C++ — confirm availability)"] = {
            "config_files": [],
            "note": "C/C++ detected; prefer 'Clean' if available, else clang-tidy/cppcheck",
        }
    typecheckers = tool_hits(TYPECHECK_CONFIGS)
    security = tool_hits(SECURITY_CONFIGS)

    ci = [p for p in CI_PATHS if (root / p).exists()]

    # Existing single-command gate runner?
    gate_runner = None
    makefile = root / "Makefile"
    if not makefile.exists():
        makefile = root / "makefile"
    if makefile.exists():
        mk = read_text(makefile)
        targets = [ln.split(":")[0].strip() for ln in mk.splitlines()
                   if ":" in ln and not ln.startswith((" ", "\t", "#"))]
        gate_like = [t for t in targets
                     if t in {"check", "ci", "lint", "test", "verify", "all",
                              "precommit", "pre-commit", "qa"}]
        if gate_like:
            gate_runner = {"type": "make", "targets": gate_like}
    for script_name in ("check.sh", "ci.sh", "verify.sh", "test.sh"):
        if (root / "scripts" / script_name).exists():
            gate_runner = gate_runner or {"type": "script",
                                          "path": f"scripts/{script_name}"}
    if pkg_scripts:
        gate_like = [s for s in pkg_scripts
                     if s in {"check", "ci", "lint", "test", "typecheck",
                              "verify", "validate"}]
        if gate_like and not gate_runner:
            gate_runner = {"type": "npm", "scripts": gate_like}

    instruction_files = exists_any(root, AGENT_INSTRUCTION_FILES)
    cursor_rules = []
    crd = root / CURSOR_RULES_DIR
    if crd.is_dir():
        cursor_rules = [str(p.relative_to(root)) for p in crd.rglob("*")
                        if p.is_file()]

    # Specifications — evidence for the spec-alignment gate. Presence is a hint
    # that a functional/technical spec exists to check the implementation
    # against; absence is a prompt to ask the user where the spec lives.
    spec_hits = []
    for dname in SPEC_DIRS:
        d = root / dname
        if d.is_dir():
            for p in d.rglob("*"):
                if p.is_file() and p.suffix.lower() in {".md", ".rst", ".txt",
                        ".yaml", ".yml", ".json", ".feature", ".adoc"}:
                    spec_hits.append(str(p.relative_to(root)))
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            low = fn.lower()
            if low.endswith(SPEC_FILE_SUFFIXES) or any(k in low for k in SPEC_FILE_PATTERNS):
                rel = os.path.relpath(os.path.join(dirpath, fn), root)
                if rel not in spec_hits:
                    spec_hits.append(rel)
    spec_hits = sorted(set(spec_hits))[:40]

    return {
        "root": str(root),
        "languages": languages,
        "language_file_counts": lang_counts,
        "manifests": manifests_found,
        "has_tests_dir": has_tests_dir,
        "test_files_sample": test_files[:20],
        "test_file_count_seen": len(test_files),
        "npm_scripts": pkg_scripts,
        "linters": linters,
        "typecheckers": typecheckers,
        "security_tools": security,
        "ci": ci,
        "existing_gate_runner": gate_runner,
        "agent_instruction_files": instruction_files,
        "cursor_rules_files": cursor_rules,
        "specs": spec_hits,
    }


def summarize(report: dict) -> str:
    lines = []
    lines.append(f"Project root : {report['root']}")
    langs = report["languages"] or ["(none detected)"]
    lines.append(f"Languages    : {', '.join(langs)}")
    if report["manifests"]:
        lines.append(f"Manifests    : {', '.join(report['manifests'])}")
    lines.append(f"Tests dir    : {'yes' if report['has_tests_dir'] else 'no'}"
                 f"  ({report['test_file_count_seen']} test file(s) seen)")
    lines.append(f"Linters      : {', '.join(report['linters']) or '(none found)'}")
    lines.append(f"Type-checkers: {', '.join(report['typecheckers']) or '(none found)'}")
    lines.append(f"Security     : {', '.join(report['security_tools']) or '(none found)'}")
    lines.append(f"CI config    : {', '.join(report['ci']) or '(none found)'}")
    runner = report["existing_gate_runner"]
    lines.append(f"Gate runner  : {json.dumps(runner) if runner else '(none found)'}")
    instr = report["agent_instruction_files"] + report["cursor_rules_files"]
    lines.append(f"Agent instr. : {', '.join(instr) or '(none found)'}")
    specs = report.get("specs", [])
    spec_show = ", ".join(specs[:6]) + (" ..." if len(specs) > 6 else "")
    lines.append(f"Specs (hint) : {spec_show or '(none found — ask where the spec lives)'}")
    lines.append("")
    lines.append("This is evidence only. Map it to the gate catalog to decide "
                 "which gates apply, which are no-ops, and which are gaps.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--json", action="store_true",
                        help="emit the raw JSON report instead of a summary")
    args = parser.parse_args()
    root = Path(args.root)
    if not root.exists():
        print(f"error: path does not exist: {root}", file=sys.stderr)
        return 2
    report = detect(root)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(summarize(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
