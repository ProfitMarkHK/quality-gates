# Quality Gates

A framework for defining, automating, and enforcing quality checks — called gates — before a unit of work is considered complete. It lives in a skill that audits a project, selects applicable gates from the catalog, and writes enforcement instructions into the project's agent-instruction files.

## Language

**done-done**:
A unit of work is done-done when every gate that applies to it has passed. The exact scope depends on context — in a pull-request workflow it means safe to merge; in a feature-delivery workflow it means safe to ship; in a ticket workflow it means safe to close. The three scopes are equivalent; all are included in "done-done" and all must hold for done-done to be true.
_Avoid_: ready, complete, done

**gate**:
A single quality check with an unambiguous result: it passes or it does not. A gate that cannot be evaluated to a binary result is not a gate — it is a review. Gates are runnable; they do not depend on human judgement alone.
_Avoid_: check, criterion, quality bar

**quality gate**:
The framework — the catalog, the detection script, the skill, the enforcement mechanism, and the gate runner — taken as a whole. A quality gate (singular) is one check; quality gates (plural) is the system.
_Avoid_: quality bar, quality standard

**evidence**:
The output of `detect_project.py` — a structured report of languages, manifests, linters, CI config, and other signals found in a project tree. Evidence is read-only and is not a decision. It is the raw material for mapping to the gate catalog.
_Avoid_: findings, results, signals

**gate catalog**:
The structured mapping from detected evidence to applicable gates and their exact commands. The catalog is the authoritative decision layer — it defines which gates apply to which project types and how they are run. It lives in `references/gate-catalog.md`.
_Avoid_: rule set, gate rules

**applies** (gate state):
A gate is in scope for this project. The gate must pass before done-done is true. The exact command that runs it is named explicitly.
_Avoid_: active, enabled

**no-op** (gate state):
A gate does not apply to this project at all — there is nothing to check. The no-op must be stated explicitly so that "checked and not needed" is distinguishable from "forgotten".
_Avoid_: skipped, omitted, not applicable

**gap** (gate state):
A gate should apply to this project but cannot currently pass — test infrastructure is missing, a linter is not installed, a build step does not exist. A gap is work to schedule, not a reason to drop the gate. The gap is flagged and tracked.
_Avoid_: missing, TODO, not yet implemented

**runner**:
The single command that runs every automated gate and exits non-zero on any failure. The runner is the entry point for CI, pre-commit hooks, and merge automation. Not all gates run in the runner — gates 4, 5, 9, 10, and 11 require human judgement and are enforced by the instruction-file block referencing the checklist, not by the runner. The runner is therefore the command for automated gates only.
_Avoid_: check command, gate script, all-checks command

**done-done block**:
A short section in an agent-instruction file, between `<!-- BEGIN/END QUALITY GATES -->` markers, that states the done-done rule and points to the checklist document and runner command. It is not the full gate list — that lives in one central checklist document to avoid drift. Re-runs of the skill update the block in place.
_Avoid_: enforcement block, quality gates section, gate marker

**agent-instruction file**:
A file that an AI coding agent reads before working in a project. Examples: `CLAUDE.md` (Claude Code, Cowork), `AGENTS.md` (cross-tool standard), `.github/copilot-instructions.md` (GitHub Copilot), `.cursor/rules/` (Cursor).
_Avoid_: agent instructions, agent config, AI instructions