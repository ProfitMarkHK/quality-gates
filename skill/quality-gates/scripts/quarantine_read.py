#!/usr/bin/env python3
"""Display-only quarantine triage reader (operator-local tool).

Parses quality-gates quarantine envelopes and prints a structured human
summary WITHOUT dumping the deterministic_review echo bulk:

  1. violation summary (rule + observation id, in plain language)
  2. echo verdict (present/absent, byte size, sha prefix for comparison)
  3. offending strings (the failing observation / uncertainties)
  4. inventory (all observation ids, uncertainty count, recommendations)

HUMAN REVIEW ONLY. Output may contain raw model text: never paste it into
agent context, tickets, or gate decisions. A human re-derives any signal
from the repository.

Usage:
  python3 quarantine_read.py <file> [<file> ...]
  python3 quarantine_read.py --dir <quarantine-dir>
  python3 quarantine_read.py --full <file>   # also dump parsed candidate

Standard library only. Never modifies files. Exit 0 even on unparsable
input (reports it instead of crashing).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

BANNER = (
    "HUMAN REVIEW ONLY — output may hold raw model text. "
    "Never paste into agent context, tickets, or gate decisions."
)

RULE_GUIDE = {
    "observation_statement": (
        "an observation statement tripped the advisory-text rule "
        "(must be single-line with no commands or installed-tool claims)"
    ),
    "observation_source_references": (
        "an observation has missing/invalid source references"
    ),
    "observation_unknown_material": (
        "an observation cites a material_id not in the input package"
    ),
    "deterministic_review": (
        "the echoed deterministic review differs from the sent evidence"
    ),
    "uncertainty_text": (
        "an uncertainty string tripped the advisory-text rule "
        "(must be single-line with no commands or installed-tool claims)"
    ),
    "recommendation_format": (
        "a recommendation is not in the fixed validation-question format"
    ),
    "status": "an unexpected status value was returned",
}


def _sha_prefix(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


def _print_violation(envelope: dict) -> tuple[str, str]:
    violation = envelope.get("violation", {})
    rule = violation.get("rule", "") if isinstance(violation, dict) else ""
    obs_id = violation.get("observation_id", "") if isinstance(violation, dict) else ""
    print(f"violation rule : {rule or '(none recorded)'}")
    if rule in RULE_GUIDE:
        print(f"  meaning     : {RULE_GUIDE[rule]}")
    print(f"observation id : {obs_id or '(none — failure is not tied to one observation)'}")
    return rule, obs_id


def _load_candidate(envelope: dict) -> dict | None:
    raw_text = envelope.get("raw_text", "")
    if not isinstance(raw_text, str):
        print("raw payload  : missing")
        return None
    print(f"raw payload  : {len(raw_text.encode('utf-8'))} bytes, sha {_sha_prefix(raw_text)}")
    try:
        candidate = json.loads(raw_text)
    except ValueError:
        print("candidate    : UNPARSABLE as JSON (transport or truncation failure)")
        print("  first 300 chars:")
        print("  " + raw_text[:300].replace("\n", "\\n"))
        return None
    if not isinstance(candidate, dict):
        print("candidate    : parsed but top level is not an object")
        return None
    return candidate


def _print_echo(candidate: dict) -> None:
    echo = candidate.get("deterministic_review")
    if isinstance(echo, dict):
        echo_bytes = len(json.dumps(echo, sort_keys=True).encode("utf-8"))
        print(f"echo         : deterministic_review present, {echo_bytes} bytes (bulk — not dumped)")
    else:
        print("echo         : deterministic_review MISSING or not an object")


def _print_observations(candidate: dict, obs_id: str) -> None:
    observations = candidate.get("observations")
    if not isinstance(observations, list):
        print("observations : missing or not a list")
        return
    print(f"observations : {len(observations)}")
    for ob in observations:
        _print_observation(ob, obs_id)


def _print_observation(ob: object, obs_id: str) -> None:
    if not isinstance(ob, dict):
        return
    marker = "  <-- FLAGGED" if ob.get("id") == obs_id and obs_id else ""
    print(f"  - id={ob.get('id', '?')}{marker}")
    stmt = ob.get("statement")
    if isinstance(stmt, str):
        trimmed = stmt if len(stmt) <= 600 else stmt[:600] + "… [truncated]"
        print(f"    statement: {trimmed}")
    refs = ob.get("source_references")
    if isinstance(refs, list):
        print(f"    refs     : {len(refs)}")


def _print_uncertainties(candidate: dict, rule: str, obs_id: str) -> None:
    uncertainties = candidate.get("uncertainties")
    if not isinstance(uncertainties, list):
        print("uncertainties: missing or not a list")
        return
    print(f"uncertainties: {len(uncertainties)}")
    for i, u in enumerate(uncertainties):
        marker = ""
        if rule == "uncertainty_text" and not obs_id:
            marker = "  <-- CANDIDATE (rule is uncertainty_text, no observation id)"
        if isinstance(u, str):
            trimmed = u if len(u) <= 400 else u[:400] + "… [truncated]"
            print(f"  [{i}]{marker}: {trimmed}")


def _print_tail(candidate: dict, show_full: bool) -> None:
    recommendations = candidate.get("recommendations")
    if isinstance(recommendations, list):
        print(f"recommendations: {len(recommendations)}")
    print(f"status       : {candidate.get('status', '(missing)')}")
    if show_full:
        print("--- full parsed candidate ---")
        print(json.dumps(candidate, indent=2, ensure_ascii=False))


def summarize(path: Path, show_full: bool = False) -> int:
    print(f"=== {path} ===")
    print(BANNER)
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"unparsable envelope: {exc}")
        return 0
    if not isinstance(envelope, dict):
        print("unparsable envelope: top level is not an object")
        return 0

    rule, obs_id = _print_violation(envelope)
    candidate = _load_candidate(envelope)
    if candidate is None:
        return 0
    _print_echo(candidate)
    _print_observations(candidate, obs_id)
    _print_uncertainties(candidate, rule, obs_id)
    _print_tail(candidate, show_full)
    return 0


def main(argv: list[str]) -> int:
    paths: list[Path] = []
    show_full = False
    i = 0
    args = argv[1:]
    while i < len(args):
        if args[i] == "--dir" and i + 1 < len(args):
            d = Path(args[i + 1])
            paths.extend(sorted(d.glob("*.json")))
            i += 2
        elif args[i] == "--full":
            show_full = True
            i += 1
        elif args[i].startswith("-"):
            print(f"unknown flag: {args[i]}", file=sys.stderr)
            return 2
        else:
            paths.append(Path(args[i]))
            i += 1
    if not paths:
        print("usage: quarantine_read.py [--full] <file> ... | --dir <quarantine-dir>", file=sys.stderr)
        return 2
    for path in paths:
        summarize(path, show_full)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
