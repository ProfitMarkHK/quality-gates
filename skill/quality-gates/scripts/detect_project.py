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
    ".sh": "Bash", ".bash": "Bash", ".ps1": "PowerShell",
    ".psm1": "PowerShell", ".psd1": "PowerShell", ".scala": "Scala",
    ".ex": "Elixir",
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
    "PSScriptAnalyzer": [
        "PSScriptAnalyzerSettings.psd1",
        ".PSScriptAnalyzerSettings.psd1",
    ],
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

# Config-file fingerprints for cyclomatic-complexity enforcement (Gate 3b).
# ruff C901 needs no dedicated file — it is configured inside pyproject.toml
# (`mccabe-complexity`) or ruff.toml — and xenon is driven by CLI flags in a
# gate runner, so both are detected via content scans in detect(), not just
# the files listed here.
COMPLEXITY_CONFIGS = {
    "xenon": ["xenon.cfg", ".xenon"],
    "lizard": [".lizard", "lizard.cfg"],
}

# ESLint config files scanned for an explicit `complexity` rule (Gate 3b).
# Kept separate because presence of the file alone proves nothing — the rule
# text inside is the evidence.
ESLINT_CONFIG_FILES = [
    ".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json",
    ".eslintrc.yml", ".eslintrc.yaml", "eslint.config.js",
    "eslint.config.mjs",
]

CI_PATHS = [
    ".github/workflows", ".gitlab-ci.yml", ".circleci/config.yml",
    "azure-pipelines.yml", "Jenkinsfile", ".buildkite", "bitbucket-pipelines.yml",
]

AGENT_INSTRUCTION_FILES = [
    "CLAUDE.md", "AGENTS.md", ".github/copilot-instructions.md",
    "GEMINI.md", ".cursorrules",
]

CURSOR_RULES_DIR = ".cursor/rules"

GATE_SCRIPT_NAMES = (
    "check.sh", "ci.sh", "verify.sh", "test.sh",
    "check.ps1", "ci.ps1", "verify.ps1", "test.ps1",
)

LINTER_INVOCATION_ALIASES = {
    "PSScriptAnalyzer": ("invoke-scriptanalyzer",),
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def exists_any(root: Path, names) -> list:
    return [n for n in names if (root / n).exists()]


def _is_test_file(filename: str) -> bool:
    low = filename.lower()
    return (low.startswith("test_") or low.endswith("_test.py")
            or low.endswith("_test.go") or ".test." in low
            or ".spec." in low or low.endswith("_spec.rb"))


def _record_file(rel_dir: str, fn: str, lang_counts: dict,
                 test_files: list, agent_skills: list) -> None:
    lang = EXT_LANG.get(os.path.splitext(fn)[1].lower())
    if lang:
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    if _is_test_file(fn):
        rel = os.path.normpath(os.path.join(rel_dir, fn))
        if len(test_files) < 50:
            test_files.append(rel)
    if fn == "SKILL.md":
        rel = os.path.normpath(os.path.join(rel_dir, fn))
        directory = "." if rel_dir == "." else rel_dir
        agent_skills.append({"directory": directory, "file": rel})


def _walk_source_tree(root: Path) -> dict:
    lang_counts: dict[str, int] = {}
    test_files: list[str] = []
    has_tests_dir = False
    shell_scripts = 0
    agent_skills: list[dict[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, root)
        if os.path.basename(dirpath).lower() in {"test", "tests", "spec",
                                                  "specs", "__tests__"}:
            has_tests_dir = True
        for fn in filenames:
            _record_file(rel_dir, fn, lang_counts, test_files, agent_skills)
            if os.path.splitext(fn)[1].lower() in {".sh", ".bash"}:
                shell_scripts += 1
    return {
        "language_file_counts": lang_counts,
        "test_files": test_files,
        "has_tests_dir": has_tests_dir,
        "shell_scripts": shell_scripts,
        "agent_skills": agent_skills,
    }


def _load_package_signals(root: Path) -> tuple:
    pkg_scripts: list = []
    pkg_devdeps: list = []
    if (root / "package.json").exists():
        try:
            data = json.loads(read_text(root / "package.json") or "{}")
            pkg_scripts = list((data.get("scripts") or {}).keys())
            pkg_devdeps = list((data.get("devDependencies") or {}).keys())
            pkg_devdeps += list((data.get("dependencies") or {}).keys())
        except (ValueError, AttributeError):
            pass
    pyproject_text = read_text(root / "pyproject.toml")
    return pkg_scripts, pkg_devdeps, pyproject_text


def _read_build_ci_text(root: Path) -> str:
    # A tool may be invoked in build/CI with no config file of its own
    # (common for cppcheck, clang-tidy, and a "Clean" linter driven from a
    # Makefile target). Scanning it catches those cases.
    build_ci_text = read_text(root / "Makefile") + read_text(root / "makefile")
    for script_name in GATE_SCRIPT_NAMES:
        build_ci_text += read_text(root / "scripts" / script_name)
    for ci_dir in (".github/workflows", ".circleci"):
        d = root / ci_dir
        if d.is_dir():
            for p in d.rglob("*"):
                if p.is_file():
                    build_ci_text += read_text(p)
    for ci_file in (".gitlab-ci.yml", "azure-pipelines.yml", "Jenkinsfile"):
        build_ci_text += read_text(root / ci_file)
    return build_ci_text.lower()


def _match_word(name: str, text: str) -> bool:
    # Word-ish boundaries avoid e.g. "clean" matching inside "cleanup".
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", text))


def _depends_on(name: str, pkg_devdeps: list) -> bool:
    return any(name in d.lower() for d in pkg_devdeps)


def _mentions_any(text: str, names) -> bool:
    return any(k in text for k in names)


def _clean_build_hit(key: str, in_build: bool, build_ci_lower: str) -> bool:
    # "clean" as a bare token almost always means the `make clean`
    # artifact-removal target, not the Clean linter. Require a clearer
    # invocation ("clean lint/check/run/analyze") before trusting it.
    if key == "clean" and in_build:
        return bool(re.search(r"clean\s+(lint|check|run|analyz|scan)",
                              build_ci_lower))
    return in_build


def _pssa_note(tool: str, found: list, in_build: bool) -> str:
    if tool == "PSScriptAnalyzer" and found and not in_build:
        return "Settings file found; confirm Invoke-ScriptAnalyzer is wired into a gate"
    return ""


def _single_tool_evidence(root: Path, tool: str, files: list,
                           pkg_devdeps: list, pyproject_lower: str,
                           build_ci_lower: str) -> dict | None:
    found = exists_any(root, files)
    key = tool.split("/")[0].lower()
    in_pkg = tool in " ".join(pkg_devdeps).lower() or _depends_on(key, pkg_devdeps)
    in_pyproject = key in pyproject_lower
    in_build = _match_word(key, build_ci_lower)
    for alias in LINTER_INVOCATION_ALIASES.get(tool, ()):
        in_build = in_build or _match_word(alias, build_ci_lower)
    in_build = _clean_build_hit(key, in_build, build_ci_lower)
    if found or in_pkg or in_pyproject or in_build:
        evidence = {
            "config_files": found,
            "in_package_json": bool(in_pkg),
            "in_pyproject": bool(in_pyproject),
            "in_build_or_ci": bool(in_build),
        }
        note = _pssa_note(tool, found, in_build)
        if note:
            evidence["note"] = note
        return evidence
    return None


def _tool_hits_for(root: Path, configs: dict, pkg_devdeps: list,
                   pyproject_lower: str, build_ci_lower: str) -> dict:
    hits = {}
    for tool, files in configs.items():
        evidence = _single_tool_evidence(root, tool, files, pkg_devdeps,
                                          pyproject_lower, build_ci_lower)
        if evidence is not None:
            hits[tool] = evidence
    return hits


def _linter_candidates(linters: dict, shell_scripts: int,
                       lang_counts: dict, languages: list) -> None:
    if shell_scripts and "shellcheck" not in linters:
        linters["shellcheck (candidate)"] = {
            "config_files": [], "note": f"{shell_scripts} shell script(s) found",
        }
    powershell_scripts = lang_counts.get("PowerShell", 0)
    if powershell_scripts and "PSScriptAnalyzer" not in linters:
        linters["PSScriptAnalyzer (candidate)"] = {
            "config_files": [],
            "note": f"{powershell_scripts} PowerShell file(s) found; confirm PSScriptAnalyzer is available",
        }
    # Flag C/C++ so the caller applies the "prefer Clean" policy deliberately.
    if any(l in ("C", "C++") for l in languages) and "Clean" not in linters:
        linters["Clean (policy: preferred for C/C++ — confirm availability)"] = {
            "config_files": [],
            "note": "C/C++ detected; prefer 'Clean' if available, else clang-tidy/cppcheck",
        }


def _python_complexity(complexity: dict, pyproject_lower: str,
                       pkg_devdeps: list, build_ci_lower: str) -> None:
    # ruff C901 via `mccabe-complexity` or an explicit C901 select.
    if "mccabe-complexity" in pyproject_lower or "c901" in pyproject_lower:
        complexity["ruff-C901"] = {
            "config_files": [],
            "in_package_json": False,
            "in_pyproject": True,
            "in_build_or_ci": _match_word("ruff", build_ci_lower),
        }
    elif _match_word("ruff", build_ci_lower):
        # Bare `ruff` invocation with no C901 evidence: the linter is wired
        # but the complexity rule is not proven — record so Phase 2 can ask.
        complexity["ruff-C901 (unconfirmed)"] = {
            "config_files": [],
            "note": "ruff invoked in build/CI but no C901/mccabe-complexity evidence in pyproject.toml",
        }
    # Strict companion: xenon via config file, dependency, or runner invocation.
    if "xenon" not in complexity and ("xenon" in pyproject_lower
                                      or _depends_on("xenon", pkg_devdeps)
                                      or _match_word("xenon", build_ci_lower)):
        complexity["xenon"] = {
            "config_files": [],
            "in_package_json": _depends_on("xenon", pkg_devdeps),
            "in_pyproject": "xenon" in pyproject_lower,
            "in_build_or_ci": _match_word("xenon", build_ci_lower),
        }


def _eslint_rule_in_files(root: Path) -> bool:
    for cfg_name in ESLINT_CONFIG_FILES:
        cfg_text = read_text(root / cfg_name)
        if cfg_text and "complexity" in cfg_text.lower():
            return True
    return False


def _eslint_rule_in_package(root: Path) -> bool:
    try:
        data = json.loads(read_text(root / "package.json") or "{}")
        eslint_cfg = data.get("eslintConfig") or {}
    except (ValueError, AttributeError):
        return False
    return "complexity" in json.dumps(eslint_cfg).lower()


def _js_complexity(root: Path, complexity: dict, build_ci_lower: str) -> None:
    if _eslint_rule_in_files(root) or _eslint_rule_in_package(root):
        complexity["eslint-complexity"] = {
            "config_files": [n for n in ESLINT_CONFIG_FILES if (root / n).exists()],
            "in_package_json": False,
            "in_pyproject": False,
            "in_build_or_ci": _match_word("eslint", build_ci_lower),
        }


def _go_complexity(root: Path, complexity: dict, build_ci_lower: str) -> None:
    gocyclo_cfg = ""
    for cfg_name in (".golangci.yml", ".golangci.yaml", ".golangci.toml"):
        cfg_text = read_text(root / cfg_name)
        if cfg_text:
            gocyclo_cfg += cfg_text.lower()
    if (_mentions_any(gocyclo_cfg, ("cyclop", "gocyclo", "gocognit"))
            or _match_word("gocyclo", build_ci_lower)
            or _match_word("cyclop", build_ci_lower)
            or _match_word("gocognit", build_ci_lower)):
        complexity["gocyclo/cyclop"] = {
            "config_files": [n for n in (".golangci.yml", ".golangci.yaml", ".golangci.toml")
                             if (root / n).exists()],
            "in_package_json": False,
            "in_pyproject": False,
            "in_build_or_ci": True,
        }


def _complexity_candidates(complexity: dict, languages: list,
                           lang_counts: dict) -> None:
    # Source present, no budget wired — the caller maps these to gaps.
    has_budget = any(not k.endswith("(candidate)")
                     and not k.endswith("(unconfirmed)") for k in complexity)
    if has_budget:
        return
    if "Python" in languages:
        complexity["ruff-C901/xenon (candidate)"] = {
            "config_files": [],
            "note": (f"{lang_counts.get('Python', 0)} Python file(s) found; "
                     "no C901/mccabe-complexity or xenon evidence — wire `ruff check "
                     "--select C901` (mccabe-complexity = 10) plus strict "
                     "`xenon --max-absolute B`"),
        }
    if any(l in ("TypeScript", "JavaScript") for l in languages):
        complexity["eslint-complexity (candidate)"] = {
            "config_files": [],
            "note": "JS/TS found; no eslint `complexity` rule evidence — set `\"complexity\": [\"error\", 10]`",
        }
    if "Go" in languages:
        complexity["gocyclo/cyclop (candidate)"] = {
            "config_files": [],
            "note": "Go found; no gocyclo/cyclop evidence — wire `gocyclo -over 10` or cyclop max-complexity 10",
        }


def _detect_complexity(root: Path, languages: list, lang_counts: dict,
                       pkg_devdeps: list, pyproject_lower: str,
                       build_ci_lower: str) -> dict:
    # Gate 3b: strict max 10 per function/method, tests excluded, no
    # grandfathering. Presence is a strong signal the budget is wired in;
    # absence with matching source files yields a (candidate) gap.
    complexity: dict = _tool_hits_for(root, COMPLEXITY_CONFIGS, pkg_devdeps,
                                       pyproject_lower, build_ci_lower)
    _python_complexity(complexity, pyproject_lower, pkg_devdeps, build_ci_lower)
    _js_complexity(root, complexity, build_ci_lower)
    _go_complexity(root, complexity, build_ci_lower)
    if "lizard" not in complexity and _match_word("lizard", build_ci_lower):
        complexity["lizard"] = {
            "config_files": [],
            "in_package_json": False,
            "in_pyproject": False,
            "in_build_or_ci": True,
        }
    _complexity_candidates(complexity, languages, lang_counts)
    return complexity


def _make_gate_runner(makefile: Path) -> dict | None:
    mk = read_text(makefile)
    targets = [ln.split(":")[0].strip() for ln in mk.splitlines()
               if ":" in ln and not ln.startswith((" ", "\t", "#"))]
    gate_like = [t for t in targets
                 if t in {"check", "ci", "lint", "test", "verify", "all",
                          "precommit", "pre-commit", "qa"}]
    if gate_like:
        return {"type": "make", "targets": gate_like}
    return None


def _detect_gate_runner(root: Path, pkg_scripts: list) -> dict | None:
    gate_runner = None
    makefile = root / "Makefile"
    if not makefile.exists():
        makefile = root / "makefile"
    if makefile.exists():
        gate_runner = _make_gate_runner(makefile)
    for script_name in GATE_SCRIPT_NAMES:
        if (root / "scripts" / script_name).exists():
            gate_runner = gate_runner or {"type": "script",
                                          "path": f"scripts/{script_name}"}
    if pkg_scripts:
        gate_like = [s for s in pkg_scripts
                     if s in {"check", "ci", "lint", "test", "typecheck",
                              "verify", "validate"}]
        if gate_like and not gate_runner:
            gate_runner = {"type": "npm", "scripts": gate_like}
    return gate_runner


def _detect_instructions(root: Path) -> tuple:
    instruction_files = exists_any(root, AGENT_INSTRUCTION_FILES)
    cursor_rules = []
    crd = root / CURSOR_RULES_DIR
    if crd.is_dir():
        cursor_rules = [str(p.relative_to(root)) for p in crd.rglob("*")
                        if p.is_file()]
    return instruction_files, cursor_rules


def _spec_hits_in_dirs(root: Path) -> list:
    spec_hits = []
    for dname in SPEC_DIRS:
        d = root / dname
        if d.is_dir():
            for p in d.rglob("*"):
                if p.is_file() and p.suffix.lower() in {".md", ".rst", ".txt",
                        ".yaml", ".yml", ".json", ".feature", ".adoc"}:
                    spec_hits.append(str(p.relative_to(root)))
    return spec_hits


def _spec_hits_by_name(root: Path, spec_hits: list) -> list:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            low = fn.lower()
            if low.endswith(SPEC_FILE_SUFFIXES) or _mentions_any(low, SPEC_FILE_PATTERNS):
                rel = os.path.relpath(os.path.join(dirpath, fn), root)
                if rel not in spec_hits:
                    spec_hits.append(rel)
    return sorted(set(spec_hits))[:40]


def _detect_specs(root: Path) -> list:
    # Presence hints a functional/technical spec exists to check the
    # implementation against; absence prompts asking where the spec lives.
    return _spec_hits_by_name(root, _spec_hits_in_dirs(root))


def detect(root: Path) -> dict:
    root = root.resolve()
    tree = _walk_source_tree(root)
    lang_counts = tree["language_file_counts"]
    languages = sorted(lang_counts, key=lambda k: lang_counts[k], reverse=True)

    manifests_found = {}
    for name, meta in MANIFESTS.items():
        if (root / name).exists():
            manifests_found[name] = {"language": meta[0], "build_system": meta[1]}

    # package.json carries a lot of signal — inspect its scripts and devDeps.
    pkg_scripts, pkg_devdeps, pyproject_text = _load_package_signals(root)

    build_ci_lower = _read_build_ci_text(root)
    pyproject_lower = pyproject_text.lower()

    linters = _tool_hits_for(root, LINTER_CONFIGS, pkg_devdeps,
                              pyproject_lower, build_ci_lower)
    _linter_candidates(linters, tree["shell_scripts"], lang_counts, languages)
    typecheckers = _tool_hits_for(root, TYPECHECK_CONFIGS, pkg_devdeps,
                                   pyproject_lower, build_ci_lower)
    security = _tool_hits_for(root, SECURITY_CONFIGS, pkg_devdeps,
                               pyproject_lower, build_ci_lower)

    complexity = _detect_complexity(root, languages, lang_counts,
                                     pkg_devdeps, pyproject_lower, build_ci_lower)

    ci = [p for p in CI_PATHS if (root / p).exists()]

    # Existing single-command gate runner?
    gate_runner = _detect_gate_runner(root, pkg_scripts)

    instruction_files, cursor_rules = _detect_instructions(root)

    spec_hits = _detect_specs(root)
    agent_skills = tree["agent_skills"]
    agent_skills.sort(key=lambda item: item["directory"])

    return {
        "root": str(root),
        "languages": languages,
        "language_file_counts": lang_counts,
        "manifests": manifests_found,
        "has_tests_dir": tree["has_tests_dir"],
        "test_files_sample": tree["test_files"][:20],
        "test_file_count_seen": len(tree["test_files"]),
        "npm_scripts": pkg_scripts,
        "linters": linters,
        "complexity": complexity,
        "typecheckers": typecheckers,
        "security_tools": security,
        "ci": ci,
        "existing_gate_runner": gate_runner,
        "agent_instruction_files": instruction_files,
        "cursor_rules_files": cursor_rules,
        "specs": spec_hits,
        "agent_skills": agent_skills,
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
    linter_names = []
    for name, evidence in report["linters"].items():
        note = evidence.get("note")
        linter_names.append(f"{name} ({note})" if note else name)
    lines.append(f"Linters      : {', '.join(linter_names) or '(none found)'}")
    complexity_names = []
    for name, evidence in report.get("complexity", {}).items():
        note = evidence.get("note")
        complexity_names.append(f"{name} ({note})" if note else name)
    lines.append(f"Complexity   : {', '.join(complexity_names) or '(none found)'}")
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
    skills = report.get("agent_skills", [])
    skill_show = ", ".join(item["directory"] for item in skills)
    lines.append(f"Agent skills : {skill_show or '(none found)'}")
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
