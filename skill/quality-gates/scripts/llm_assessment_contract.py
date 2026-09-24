#!/usr/bin/env python3
"""Build and validate the optional advisory LLM assessment contract.

The skill remains responsible for choosing when to invoke an approved secure
LLM. This module owns the stable boundary around that invocation: every target
file is represented, repository text is serialized as data, observations carry
their own provenance, and deterministic review output cannot be changed by an
advisory result.
"""

from __future__ import annotations

import base64
import copy
import fnmatch
import json
import os
import re
import sys
import unicodedata
from pathlib import Path


ASSESSMENT_STATUS = {"completed", "partial", "unavailable", "timed_out", "failed"}
RESULT_FIELDS = {
    "status",
    "observations",
    "uncertainties",
    "recommendations",
    "failure_reason",
    "deterministic_review",
}
OBSERVATION_FIELDS = {"id", "statement", "source_references"}
REFERENCE_FIELDS = {"material_id", "path", "locator"}
RECOMMENDATION_FIELDS = {"id", "text", "related_observation_ids"}
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
# Verbs whose bare form in advisory prose is instruction-shaped. Kept in sync
# with _validate_advisory_text and the preview neutralizer below.
UNSAFE_VERBS = ("run", "execute", "install", "invoke", "command")
UNSAFE_STATES = ("installed", "configured", "passing")
# Commands that are only dangerous with a target (flags, paths, URLs). Bare
# mentions ("uses docker for builds") stay valid; invocations do not.
PREVIEW_DANGEROUS_VERBS = (
    "rm", "dd", "mkfs", "chmod", "chown", "sudo", "su",
    "curl", "wget", "ssh", "sh", "bash", "powershell", "cmd",
    "docker", "kubectl",
)
_DANGEROUS_TARGET = r"(?:-|\+|/|\\|\.|~|https?://|[A-Za-z0-9_.-]+/)"
_DANGEROUS_RE = r"\b(?:rm|dd|mkfs|chmod|chown|sudo|su|curl|wget|ssh|sh|bash|powershell|cmd|docker|kubectl)\b(?=\s+" + _DANGEROUS_TARGET + r")"
EXCLUDE_ENV_VAR = "QUALITY_GATES_LLM_EXCLUDE_PATTERNS"
EXCLUDED_REASON = "excluded by operator config QUALITY_GATES_LLM_EXCLUDE_PATTERNS"
MAX_EXCLUDE_PATTERNS = 128
MAX_EXCLUDE_PATTERN_LEN = 256
ASSESSMENT_CONTRACT = (
    "Inspect the supplied target-project material for technology that deterministic "
    "review may not recognise or may have classified ambiguously. Return only "
    "source-backed observations, uncertainty, and recommendations for human "
    "validation. Do not invent tools, commands, configuration, or gate decisions. "
    "Respond with a single JSON object containing only these fields: "
    '"status" (exactly one of "completed", "partial", "unavailable", "timed_out", '
    '"failed"); "observations" (a list of objects each with only "id", "statement", '
    'and "source_references", where each source reference has only "material_id" '
    'and "path" naming a supplied material); "uncertainties" (a list of strings); '
    '"recommendations" (a list of objects each with only "id", "text", and '
    '"related_observation_ids", where each text is exactly "Can the project owner '
    'validate observation <id>?" for one observed id); and "deterministic_review" '
    "(an exact copy of the supplied deterministic review). "
    "Include no other fields at any level. Return only the JSON object itself: "
    "no markdown fencing, no commentary, no other text. "
    "Limit the assessment to at most 30 observations, most significant first; "
    "omit low-signal naming details that deterministic review already covers. "
    "Observation and recommendation ids must be short ASCII slugs using only "
    "letters, digits, dot, underscore, and hyphen (for example obs-1)."
)


class AssessmentContractError(ValueError):
    """Raised when an advisory result violates the assessment contract.

    Carries machine-readable violation details alongside the human-readable
    message: ``rule`` names the rejecting validation rule and ``observation_id``
    names the specific observation that failed, or is empty when no single
    observation applies. The message text stays the sole human-readable
    description and is unchanged.
    """

    def __init__(self, message, rule="", observation_id=""):
        super().__init__(message)
        self.rule = rule
        # Metadata and the quarantine envelope carry strings only: a
        # non-string id (e.g. an integer that failed identifier validation)
        # is recorded as empty rather than leaking a raw value through.
        self.observation_id = observation_id if isinstance(observation_id, str) else ""


def parse_exclude_patterns(raw: str | None) -> list[str]:
    """Parse operator-only exclusion globs. Never read from target content."""
    if raw is None:
        return []
    text = raw.strip()
    if not text:
        return []
    seen: list[str] = []
    for part in text.split(","):
        stripped = part.strip()
        if not stripped or stripped in seen:
            continue
        seen.append(stripped)
    patterns = seen
    if len(patterns) > MAX_EXCLUDE_PATTERNS:
        raise AssessmentContractError(
            f"{EXCLUDE_ENV_VAR} holds too many patterns (max {MAX_EXCLUDE_PATTERNS})"
        )
    for pattern in patterns:
        if (
            len(pattern) > MAX_EXCLUDE_PATTERN_LEN
            or "\n" in pattern
            or "\r" in pattern
            or "\0" in pattern
        ):
            raise AssessmentContractError(
                f"{EXCLUDE_ENV_VAR} holds an invalid pattern"
            )
        if pattern in (".", "./"):
            raise AssessmentContractError(
                f"{EXCLUDE_ENV_VAR} holds an invalid pattern"
            )
        try:
            candidate = Path(pattern)
        except ValueError:
            raise AssessmentContractError(
                f"{EXCLUDE_ENV_VAR} holds an invalid pattern"
            )
        if candidate.is_absolute() or ".." in candidate.parts:
            raise AssessmentContractError(
                f"{EXCLUDE_ENV_VAR} patterns must be repo-relative without '..'"
            )
        if "\\" in pattern:
            raise AssessmentContractError(
                f"{EXCLUDE_ENV_VAR} patterns must use posix '/' separators"
            )
    return patterns


def load_exclude_patterns_from_env(env: dict[str, str] | None = None) -> list[str]:
    """Read exclusion patterns from operator environment only."""
    source = env if env is not None else os.environ
    return parse_exclude_patterns(source.get(EXCLUDE_ENV_VAR))


def _is_path_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def load_exclude_patterns_for_target(
    root: Path, config_dir: Path | None = None
) -> list[str]:
    """Load exclusions from operator env plus optional `.env` outside target.

    Refuses when the config directory resolves inside the target project so a
    target-controlled `.env` can never supply patterns. Contract and execute
    entry points share this rule.
    """
    directory = config_dir if config_dir is not None else Path.cwd()
    dotenv_path = directory / ".env"
    if dotenv_path.exists() and _is_path_inside(directory, root):
        raise AssessmentContractError(
            f"config directory {directory} resolves inside target {root}; "
            "run from outside the target so target content cannot supply config"
        )
    values: dict[str, str] = {}
    if dotenv_path.exists():
        for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() == EXCLUDE_ENV_VAR:
                values[key.strip()] = value.strip().strip("'\"")
    if os.environ.get(EXCLUDE_ENV_VAR) is not None:
        values[EXCLUDE_ENV_VAR] = os.environ[EXCLUDE_ENV_VAR]
    return parse_exclude_patterns(values.get(EXCLUDE_ENV_VAR))


def _glob_to_regex(pattern: str) -> str:
    """Translate a repo-relative glob to a full-match regex.

    Shell-style rules: `*` and `?` stay within a path segment, `**` crosses
    segments, a leading `**/` also matches the top level, and a trailing
    `/` means everything under that directory.
    """
    normalized = pattern.removeprefix("./")
    trailing_dir = normalized.endswith("/") and len(normalized) > 1
    if trailing_dir:
        normalized = normalized.rstrip("/")
    out: list[str] = []
    i = 0
    n = len(normalized)
    while i < n:
        char = normalized[i]
        if char == "*":
            if normalized[i:i + 2] == "**":
                if normalized[i:i + 3] == "**/":
                    out.append("(.*/)?")
                    i += 3
                else:
                    out.append(".*")
                    i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif char == "?":
            out.append("[^/]")
            i += 1
        elif char == "[":
            end = normalized.find("]", i + 1)
            if end == -1:
                out.append("\\[")
                i += 1
            else:
                out.append(normalized[i:end + 1])
                i = end + 1
        else:
            out.append(re.escape(char))
            i += 1
    body = "".join(out)
    if trailing_dir:
        body = f"(?:{body})(?:/.*)?"
    return f"(?:{body})\\Z"


def _is_excluded(material_id: str, patterns: list[str]) -> bool:
    basename = material_id.rsplit("/", 1)[-1]
    for pattern in patterns:
        normalized = pattern.removeprefix("./")
        if normalized.endswith("/") and len(normalized) > 1:
            prefix = normalized.rstrip("/")
            if material_id == prefix or material_id.startswith(prefix + "/"):
                return True
            continue
        if "/" not in normalized:
            if fnmatch.fnmatchcase(basename, normalized):
                return True
            continue
        try:
            if re.match(_glob_to_regex(normalized), material_id):
                return True
        except re.error:
            continue
    return False


def _excluded_record(path: Path, root: Path) -> dict:
    relative = path.relative_to(root).as_posix()
    return {
        "material_id": relative,
        "path": relative,
        "kind": "excluded",
        "readable": False,
        "reason": EXCLUDED_REASON,
    }


def _collapsed_excluded_record(path: Path, root: Path, pattern: str) -> dict:
    """Single placeholder for a pruned directory subtree (AIDEV-543).

    The subtree is provably fully excluded by one conservative operator
    pattern (see `_collapse_pattern_for_dir`); emitting one record keeps
    large vendored trees (e.g. `.venv`) from exploding the input package
    while keeping the exclusion visible and referenceable.
    """
    relative = path.relative_to(root).as_posix()
    return {
        "material_id": relative,
        "path": relative,
        "kind": "excluded",
        "readable": False,
        "reason": f"{EXCLUDED_REASON} (collapsed directory subtree via pattern '{pattern}')",
        "collapsed": True,
        "pattern": pattern,
    }


def _collapse_pattern_for_dir(dir_rel: str, patterns: list[str]) -> str | None:
    """Return the operator pattern proving a directory subtree fully excluded.

    Conservative rules only (AIDEV-543):
    1. a trailing-slash pattern whose prefix equals the dir or an ancestor;
    2. a `**/NAME/**` pattern with literal single-segment NAME equal to the
       dir basename. File globs, bare names, and anchored or multi-segment
       patterns never prune; the walk descends as usual for those.
    """
    basename = dir_rel.rsplit("/", 1)[-1]
    for pattern in patterns:
        normalized = pattern.removeprefix("./")
        if normalized.endswith("/") and len(normalized) > 1:
            prefix = normalized.rstrip("/")
            if dir_rel == prefix or dir_rel.startswith(prefix + "/"):
                return pattern
            continue
        if normalized.startswith("**/") and normalized.endswith("/**"):
            middle = normalized[3:-3]
            if (
                middle
                and "/" not in middle
                and "*" not in middle
                and "?" not in middle
                and "[" not in middle
                and "]" not in middle
                and basename == middle
            ):
                return pattern
            continue
    return None


def _material_record(path: Path, root: Path) -> dict:
    relative = path.relative_to(root).as_posix()
    record = {"material_id": relative, "path": relative}

    if path.is_symlink():
        record.update({
            "kind": "symlink",
            "readable": False,
            "reason": "symlink contents are not followed",
        })
        return record

    if not path.is_file():
        record.update({
            "kind": "special",
            "readable": False,
            "reason": "special filesystem entries are not read",
        })
        return record

    try:
        raw = path.read_bytes()
    except OSError as exc:
        record.update({
            "kind": "file",
            "readable": False,
            "reason": f"{type(exc).__name__}: {exc}",
        })
        return record

    if b"\x00" in raw:
        text = None
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = None

    if text is None:
        record.update({
            "kind": "binary",
            "readable": True,
            "encoding": "base64",
            "content": base64.b64encode(raw).decode("ascii"),
        })
    else:
        record.update({"kind": "text", "readable": True, "content": text})
    return record


def _unreadable_record(path: Path, root: Path, error: OSError) -> dict:
    relative = path.relative_to(root).as_posix()
    return {
        "material_id": relative,
        "path": relative,
        "kind": "directory",
        "readable": False,
        "reason": f"{type(error).__name__}: {error}",
    }


def build_input_package(
    root: Path,
    deterministic_review: dict,
    exclude_patterns: list[str] | None = None,
) -> dict:
    """Return a complete, JSON-serializable package for the secure LLM.

    The project walk intentionally does not reuse detector exclusions. The
    detector decides evidence; this package represents the target material.
    Version-control internals are not project material and are excluded.

    Operator-only `exclude_patterns` (repo-relative globs from
    QUALITY_GATES_LLM_EXCLUDE_PATTERNS) replace matching file contents with
    `{readable: False, reason: excluded by operator config ...}` placeholders.
    Placeholders keep `material_id` stable so result references still validate;
    nothing is silently dropped. Patterns never come from target content, and
    `.gitignore` / `.git/info/exclude` are never consulted.

    Fully-excluded directory subtrees collapse to one placeholder (AIDEV-543):
    a directory is pruned without descent only when a trailing-slash pattern
    covers it (prefix equals the dir or an ancestor) or a `**/NAME/**`
    pattern names its basename literally. All other patterns descend as usual.
    """
    root = root.resolve()
    patterns = list(exclude_patterns) if exclude_patterns else []
    materials = []
    def onerror(error: OSError) -> None:
        if error.filename:
            materials.append(_unreadable_record(Path(error.filename), root, error))

    for dirpath, dirnames, filenames in os.walk(root, onerror=onerror, followlinks=False):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for dirname in list(dirnames):
            path = Path(dirpath) / dirname
            if path.is_symlink():
                relative = path.relative_to(root).as_posix()
                if _is_excluded(relative, patterns):
                    materials.append(_excluded_record(path, root))
                else:
                    materials.append(_material_record(path, root))
                dirnames.remove(dirname)
                continue
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError:
                dirnames.remove(dirname)
                continue
            collapsed = _collapse_pattern_for_dir(relative, patterns)
            if collapsed is not None:
                materials.append(_collapsed_excluded_record(path, root, collapsed))
                dirnames.remove(dirname)
        for filename in sorted(filenames):
            if filename == ".git":
                continue
            path = Path(dirpath) / filename
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError:
                continue
            if _is_excluded(relative, patterns):
                materials.append(_excluded_record(path, root))
            else:
                materials.append(_material_record(path, root))

    materials.sort(key=lambda item: item["path"])
    return {
        "assessment_contract": ASSESSMENT_CONTRACT,
        "deterministic_review": copy.deepcopy(deterministic_review),
        "materials": materials,
    }


def serialize_input_package(package: dict) -> str:
    """Serialize the package with explicit contract/data delimiters."""
    contract = package["assessment_contract"]
    deterministic = json.dumps(package["deterministic_review"], sort_keys=True)
    material_lines = "\n".join(
        json.dumps(material, sort_keys=True) for material in package["materials"]
    )
    return "\n".join((
        "[ASSESSMENT_CONTRACT]",
        contract,
        "[/ASSESSMENT_CONTRACT]",
        "[DETERMINISTIC_REVIEW]",
        deterministic,
        "[/DETERMINISTIC_REVIEW]",
        "[TARGET_PROJECT_MATERIAL]",
        material_lines,
        "[/TARGET_PROJECT_MATERIAL]",
    ))


def _error(message, rule="", observation_id=""):
    raise AssessmentContractError(message, rule=rule, observation_id=observation_id)


def _is_relative_material_path(path: str) -> bool:
    candidate = Path(path)
    return not candidate.is_absolute() and ".." not in candidate.parts


def _validate_identifier(value, label, rule="", observation_id=""):
    if not isinstance(value, str) or not SAFE_IDENTIFIER.fullmatch(value):
        _error(f"{label} must be a safe identifier", rule=rule, observation_id=observation_id)


def _validate_advisory_text(value, label, rule="", observation_id=""):
    if not isinstance(value, str) or not value.strip() or "\n" in value:
        _error(
            f"{label} must be a non-empty single-line string",
            rule=rule, observation_id=observation_id,
        )
    lowered = value.lower()
    # AIDEV-545: a bare `;` is ordinary English clause punctuation
    # ("unknown; they could be internal tools"), so only a semicolon that
    # cannot be prose punctuation still fails: one not followed by
    # whitespace, the compact shell-chaining shape (`cmd1;cmd2`). Spaced
    # chains whose halves are bare words are lexically identical to
    # English clauses; chains carrying real payloads still trip the
    # verb, target, chaining, substitution, or quoting rules above.
    if (
        "```" in value
        or "`" in value
        or "$(" in value
        or "${" in value
        or "\\" in value
        or "&&" in value
        or "||" in value
        or re.search(r";(?!\s)", value)
        or re.search(r"(?<!\[)://", lowered)
        or re.search(r"\s\|\s", value)
        or re.search(
            r"\b(?:run|execute|install|invoke|command)\b|"
            r"\b(?:installed|configured|passing)\b",
            lowered,
        )
        or re.search(_DANGEROUS_RE, lowered)
        or re.search(
            r"\b[a-z][\w.-]*-[\w.-]*\s+"
            r"(?:check|scan|build|test|run|lint|format|verify|validate)\b",
            lowered,
        )
    ):
        _error(
            f"{label} must not contain commands or installed-tool claims",
            rule=rule, observation_id=observation_id,
        )


# Display-only preview neutralization (ASCII-only, NFKC-stable by construction).
# The machine path stays fail-closed on any violation; the preview lets a
# human understand the flagged content inside a live session without ingesting
# trigger keywords, shell metacharacters, raw URLs, or command payloads.
# Category tags deliberately avoid every denylisted word so preview output
# re-passes _validate_advisory_text. Never feed previews to gate decisions.
PREVIEW_VERB_TAGS = {
    "run": "[action]",
    "execute": "[action]",
    "install": "[setup-action]",
    "invoke": "[call]",
    "command": "[instruction]",
    "installed": "[setup-state]",
    "configured": "[config-state]",
    "passing": "[test-state]",
}
PREVIEW_TOOL_VERB_TAGS = {
    "check": "[check]",
    "scan": "[scan]",
    "build": "[build]",
    "test": "[test]",
    "run": "[action]",
    "lint": "[lint]",
    "format": "[format]",
    "verify": "[verify]",
    "validate": "[validate]",
}
REDACTED_PREVIEW_HEADER = (
    "REDACTED PREVIEW, HUMAN REVIEW ONLY: neutralized display text. "
    "Never fed to gate decisions; verify against the source file and "
    "the quarantined raw output."
)
PREVIEW_MAX_ITEMS = 5
PREVIEW_MAX_CHARS = 500
_PREVIEW_ID_LIMIT = 120


def _preview_tag(match: re.Match) -> str:
    return PREVIEW_VERB_TAGS[match.group(0).lower()]


def _preview_tool_verb(match: re.Match) -> str:
    return match.group(1) + " " + PREVIEW_TOOL_VERB_TAGS[match.group(2).lower()]


def _preview_dangerous_span(match: re.Match) -> str:
    return "[instruction withheld: " + match.group(1).lower() + "]"


def redact_preview_text(value: object) -> str:
    """Return ASCII-only neutralized display text for advisory prose."""
    if not isinstance(value, str):
        return ""
    text = value.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.replace("```", "[fenced-block]")
    text = text.replace("`", "'")
    text = text.replace("$(", "$ (")
    text = text.replace("${", "$ {")
    text = text.replace("\\", "[backslash]")
    text = text.replace("&&", "[and]")
    text = text.replace("||", "[or]")
    text = re.sub(r"\s\|\s", " [pipe] ", text)
    text = text.replace(";", "[semi]")
    text = text.replace(">", "[gt]")
    text = text.replace("<", "[lt]")
    text = re.sub(r"(?<!\[)://", "[://]", text)
    text = re.sub(
        r"\b(rm|dd|mkfs|chmod|chown|sudo|su|curl|wget|ssh|sh|bash|powershell|cmd|docker|kubectl)\b(?:\s+\S+){1,2}",
        _preview_dangerous_span,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:run|execute|install|invoke|command)\b"
        r"|\b(?:installed|configured|passing)\b",
        _preview_tag,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b([a-z][\w.-]*-[\w.-]*)\s+"
        r"(check|scan|build|test|run|lint|format|verify|validate)\b",
        _preview_tool_verb,
        text,
        flags=re.IGNORECASE,
    )
    return text


def build_redacted_preview(candidate: object, rule: str = "") -> dict | None:
    """Build a display-safe preview envelope for a rejected candidate.

    Returns None when there is no model-authored advisory content to show
    (unparsed prose, transport failures). The envelope carries neutralized
    text only, capped at PREVIEW_MAX_ITEMS observations and PREVIEW_MAX_CHARS
    per span, and never raw model text.
    """
    if not isinstance(candidate, dict):
        return None
    observations = candidate.get("observations")
    uncertainties = candidate.get("uncertainties")
    items: list[dict] = []
    truncated = False
    if isinstance(observations, list):
        for observation in observations:
            if not isinstance(observation, dict):
                continue
            if len(items) >= PREVIEW_MAX_ITEMS:
                truncated = True
                break
            raw_id = observation.get("id")
            if isinstance(raw_id, str):
                clean_id = "".join(
                    char if char.isprintable() else "?"
                    for char in raw_id.replace("\r", " ").replace("\n", " ")
                )[:_PREVIEW_ID_LIMIT]
            else:
                clean_id = ""
            statement = observation.get("statement")
            if not isinstance(statement, str) or not statement.strip():
                continue
            items.append({
                "id": clean_id,
                "statement_preview": redact_preview_text(statement)[:PREVIEW_MAX_CHARS],
            })
    uncertainty_previews: list[str] = []
    if isinstance(uncertainties, list):
        for uncertainty in uncertainties:
            if not isinstance(uncertainty, str) or not uncertainty.strip():
                continue
            if len(uncertainty_previews) >= PREVIEW_MAX_ITEMS:
                truncated = True
                break
            uncertainty_previews.append(
                redact_preview_text(uncertainty)[:PREVIEW_MAX_CHARS]
            )
    if not items and not uncertainty_previews:
        return None
    return {
        "header": REDACTED_PREVIEW_HEADER,
        "rule": rule if isinstance(rule, str) else "",
        "observations": items,
        "uncertainties": uncertainty_previews,
        "truncated": truncated,
    }


def build_offending_items(
    candidate: object, rule: str = "", observation_id: str = ""
) -> list[dict]:
    """Extract the specific failing advisory strings for quarantine display.

    Returns display-only items (neutralized via redact_preview_text, capped
    at PREVIEW_MAX_ITEMS / PREVIEW_MAX_CHARS) naming only the content the
    violation points at: the observation whose id matches observation_id,
    or — for uncertainty-level rules and empty observation ids — the
    candidate's uncertainties. Returns [] when the candidate is not a
    parsed object or names nothing matching. Never raises.
    """
    try:
        if not isinstance(candidate, dict):
            return []
        if isinstance(observation_id, str) and observation_id:
            observations = candidate.get("observations")
            if isinstance(observations, list):
                for observation in observations:
                    if (
                        isinstance(observation, dict)
                        and observation.get("id") == observation_id
                    ):
                        statement = observation.get("statement")
                        if isinstance(statement, str) and statement.strip():
                            return [{
                                "kind": "observation",
                                "id": observation_id,
                                "text_preview": redact_preview_text(statement)[:PREVIEW_MAX_CHARS],
                            }]
            return []
        uncertainties = candidate.get("uncertainties")
        if not isinstance(uncertainties, list):
            return []
        items = []
        for uncertainty in uncertainties:
            if not isinstance(uncertainty, str) or not uncertainty.strip():
                continue
            if len(items) >= PREVIEW_MAX_ITEMS:
                break
            items.append({
                "kind": "uncertainty",
                "text_preview": redact_preview_text(uncertainty)[:PREVIEW_MAX_CHARS],
            })
        return items
    except Exception:
        return []


def _failed_result(deterministic_review: dict, reason: str) -> dict:
    return {
        "status": "failed",
        "observations": [],
        "uncertainties": [],
        "recommendations": [],
        "failure_reason": reason,
        "deterministic_review": copy.deepcopy(deterministic_review),
    }


def validate_result(
    result: dict,
    deterministic_review: dict,
    material_ids: set[str],
) -> dict:
    """Validate and return an advisory result without changing its values."""
    if not isinstance(result, dict):
        _error("result must be an object", rule="result_shape")
    unknown_result_fields = set(result) - RESULT_FIELDS
    if unknown_result_fields:
        _error(
            f"result has unknown fields: {sorted(unknown_result_fields)}",
            rule="unknown_result_fields",
        )

    status = result.get("status")
    if not isinstance(status, str) or status not in ASSESSMENT_STATUS:
        _error(f"status must be one of {sorted(ASSESSMENT_STATUS)}", rule="status")

    expected_review = copy.deepcopy(deterministic_review)
    if result.get("deterministic_review") != expected_review:
        _error(
            "deterministic_review must exactly match the deterministic review",
            rule="deterministic_review",
        )

    observations = result.get("observations")
    if not isinstance(observations, list):
        _error("observations must be a list", rule="observations_shape")
    observation_ids = set()
    for observation in observations:
        if not isinstance(observation, dict):
            _error("each observation must be an object", rule="observation_shape")
        observation_id = observation.get("id")
        unknown_observation_fields = set(observation) - OBSERVATION_FIELDS
        if unknown_observation_fields:
            _error(
                f"observation has unknown fields: {sorted(unknown_observation_fields)}",
                rule="observation_unknown_fields",
                observation_id=observation_id if isinstance(observation_id, str) else "",
            )
        _validate_identifier(
            observation_id, "observation id",
            rule="observation_id_shape", observation_id=observation_id,
        )
        _validate_advisory_text(
            observation.get("statement"), "observation statement",
            rule="observation_statement", observation_id=observation_id,
        )
        references = observation.get("source_references")
        if observation_id in observation_ids:
            _error(
                "observations need unique ids",
                rule="observation_duplicate_id", observation_id=observation_id,
            )
        if not isinstance(references, list) or not references:
            _error(
                f"observation {observation_id} needs source_references",
                rule="observation_source_references", observation_id=observation_id,
            )
        for reference in references:
            if not isinstance(reference, dict):
                _error(
                    f"observation {observation_id} has an invalid source reference",
                    rule="observation_source_reference_shape", observation_id=observation_id,
                )
            unknown_reference_fields = set(reference) - REFERENCE_FIELDS
            if unknown_reference_fields:
                _error(
                    f"source reference has unknown fields: {sorted(unknown_reference_fields)}",
                    rule="observation_source_reference_fields", observation_id=observation_id,
                )
            if (not isinstance(reference.get("material_id"), str)
                    or not isinstance(reference.get("path"), str)
                    or reference["path"] != reference["material_id"]
                    or not _is_relative_material_path(reference["path"])):
                _error(
                    f"observation {observation_id} has an invalid source reference",
                    rule="observation_source_reference_valid", observation_id=observation_id,
                )
            if reference["material_id"] not in material_ids:
                _error(
                    f"observation {observation_id} references unknown material",
                    rule="observation_unknown_material", observation_id=observation_id,
                )
        observation_ids.add(observation_id)

    recommendations = result.get("recommendations")
    if not isinstance(recommendations, list):
        _error("recommendations must be a list", rule="recommendations_shape")
    for recommendation in recommendations:
        if not isinstance(recommendation, dict):
            _error("each recommendation must be an object", rule="recommendation_shape")
        unknown_recommendation_fields = set(recommendation) - RECOMMENDATION_FIELDS
        if unknown_recommendation_fields:
            _error(
                f"recommendation has unknown fields: {sorted(unknown_recommendation_fields)}",
                rule="recommendation_unknown_fields",
            )
        text = recommendation.get("text", "")
        _validate_identifier(recommendation.get("id"), "recommendation id", rule="recommendation_id")
        _validate_advisory_text(text, "recommendation text", rule="recommendation_text")
        related = recommendation.get("related_observation_ids", [])
        if (not isinstance(related, list)
                or any(not isinstance(item, str) for item in related)):
            _error(
                "recommendation related_observation_ids must be a list",
                rule="recommendation_related_shape",
            )
        if not set(related).issubset(observation_ids):
            _error(
                "recommendation references an unknown observation",
                rule="recommendation_unknown_observation",
            )
        if (len(related) != 1
                or text != f"Can the project owner validate observation {related[0]}?"):
            _error(
                "recommendations must use the fixed validation-question format",
                rule="recommendation_format",
            )

    uncertainties = result.get("uncertainties")
    if not isinstance(uncertainties, list):
        _error("uncertainties must be a list of non-empty strings", rule="uncertainties_shape")
    for uncertainty in uncertainties:
        _validate_advisory_text(uncertainty, "uncertainty", rule="uncertainty_text")
    if status != "completed" and not result.get("failure_reason"):
        _error(
            f"{status} results need failure_reason",
            rule="failure_reason_missing",
        )
    if status != "completed":
        failure_reason = result["failure_reason"]
        if (not isinstance(failure_reason, str)
                or not failure_reason.strip()
                or len(failure_reason) > 500
                or "\n" in failure_reason):
            _error(
                f"{status} results need a concise failure_reason",
                rule="failure_reason_shape",
            )

    return result


def main() -> int:
    if len(sys.argv) not in (2, 3, 4):
        print(
            f"usage: {Path(sys.argv[0]).name} PROJECT_ROOT "
            "[DETERMINISTIC_JSON] [RESULT_JSON]",
            file=sys.stderr,
        )
        return 2

    try:
        if len(sys.argv) == 2:
            deterministic_review = json.load(sys.stdin)
        else:
            with Path(sys.argv[2]).open(encoding="utf-8") as stream:
                deterministic_review = json.load(stream)
        try:
            exclude_patterns = load_exclude_patterns_for_target(Path(sys.argv[1]))
        except AssessmentContractError as exc:
            print(f"error: invalid {EXCLUDE_ENV_VAR}: {exc}", file=sys.stderr)
            return 2
        package = build_input_package(
            Path(sys.argv[1]), deterministic_review, exclude_patterns
        )
    except (OSError, TypeError, ValueError) as exc:
        print(f"error: unable to build assessment input: {exc}", file=sys.stderr)
        return 2
    if len(sys.argv) == 4:
        try:
            with Path(sys.argv[3]).open(encoding="utf-8") as stream:
                result = json.load(stream)
            material_ids = {item["material_id"] for item in package["materials"]}
            result = validate_result(result, deterministic_review, material_ids)
        except (AssessmentContractError, OSError, TypeError, ValueError) as exc:
            result = _failed_result(deterministic_review, str(exc))
        print(json.dumps(result, indent=2))
    else:
        total = len(package["materials"])
        excluded = sum(1 for item in package["materials"] if item.get("kind") == "excluded")
        if total and excluded == total:
            print(
                f"warning: all {total} materials excluded by {EXCLUDE_ENV_VAR}",
                file=sys.stderr,
            )
        elif excluded:
            print(
                f"excluded {excluded} of {total} materials by {EXCLUDE_ENV_VAR}",
                file=sys.stderr,
            )
        print(serialize_input_package(package))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
