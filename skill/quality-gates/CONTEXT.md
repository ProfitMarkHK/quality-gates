# Quality gates

A framework for defining, automating, and enforcing quality checks called gates before a unit of work is considered complete. It lives in a skill that audits a project, selects applicable gates from the catalog, and writes enforcement instructions into the project's agent-instruction files.

## Language

**done-done.**
A unit of work is done-done when every gate that applies to it has passed. The exact scope depends on context. In a pull-request workflow it means safe to merge. In a feature-delivery workflow it means safe to ship. In a ticket workflow it means safe to close.
_Avoid_: ready, complete, done

**gate.**
A single quality check with an unambiguous result: it passes or it does not. A gate that cannot be evaluated to a binary result is a review. Automated gates are runnable. Manual gates may require human judgement, but their outcome must still be recorded as pass or fail.
_Avoid_: check, criterion, quality bar

**quality gates.**
The framework as a whole: the catalog, detection script, skill, enforcement mechanism, and gate runner. An individual check is a gate. Together, the gates form the quality-gates system.
_Avoid_: quality bar, quality standard

**evidence.**
The output of `detect_project.py`: a structured report of languages, manifests, linters, CI config, and other signals found in a project tree. Evidence is read-only and is not a decision. It is the raw material for mapping to the gate catalog.
_Avoid_: findings, results, signals

**deterministic review.**
The read-only target-project inspection performed by `detect_project.py` and its direct file verification. Its evidence is authoritative for gate-state decisions. It completes independently of any LLM assessment.
_Avoid_: baseline scan, initial analysis

**LLM assessment.**
A best-effort, advisory analysis of target-project material performed after the deterministic review. It can identify ambiguous or unrecognised technology and recommend matters for human validation, but it is neither evidence nor a gate and cannot change gate states by itself. Its unavailable state is recorded without preventing the deterministic review from completing.
_Avoid_: LLM gate, AI evidence, AI verdict

**quarantine.**
A human-only retained copy of model output that failed validation, stored as a file outside the target project. It is never loaded into agent context and never feeds gate decisions. A human re-derives any signal from the repository directly.
_Avoid_: log, dump, cache

**gate catalog.**
The structured mapping from detected evidence to applicable gates and their exact commands. The catalog is authoritative. It defines which gates apply to which project types and how they run. It lives in `references/gate-catalog.md`.
_Avoid_: rule set, gate rules

**applies** (gate state).
A gate is in scope for this project. It must pass before done-done is true. Name the exact command that runs it.
_Avoid_: active, enabled

**no-op** (gate state).
A gate does not apply to this project. There is nothing to check. State the no-op explicitly so that "checked and not needed" is distinguishable from "forgotten".
_Avoid_: skipped, omitted, not applicable

**gap** (gate state).
A gate should apply to this project but cannot currently pass. Test infrastructure may be missing, a linter may not be installed, or the project may lack a build step. Schedule work to close the gap. Do not drop the gate.
_Avoid_: missing, TODO, not yet implemented

**runner.**
The single command that runs every automated gate and exits non-zero on any failure. The runner is the entry point for CI, pre-commit hooks, and merge automation. Gates 4, 4b, 5, 9, 10, 11, and 13 require human judgement and do not run through the runner. The instruction-file block enforces them by pointing to the checklist. The runner runs automated gates only.
_Avoid_: check command, gate script, all-checks command

**done-done block.**
A short section in an agent-instruction file, between `<!-- BEGIN/END QUALITY GATES -->` markers. It states the done-done rule and points to the checklist document and runner command. The full gate list lives in one central checklist document to prevent drift. Re-runs of the skill update the block in place.
_Avoid_: enforcement block, quality gates section, gate marker

**agent-instruction file.**
A file that an AI coding agent reads before working in a project. Examples include `CLAUDE.md` (Claude Code, Cowork), `AGENTS.md` (cross-tool standard), `.github/copilot-instructions.md` (GitHub Copilot), and `.cursor/rules/` (Cursor).
_Avoid_: agent instructions, agent config, AI instructions
