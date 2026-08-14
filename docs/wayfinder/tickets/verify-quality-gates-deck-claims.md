---
parent: ../agentic-quality-gates-explainer-map.md
labels:
  - wayfinder:research
status: closed
assignee: barrygfox
blocked_by: []
---

# Verify the quality-gates skill's deck claims

## Question

Which statements about the quality-gates skill are supported by its primary
sources: what it detects, how it classifies each gate, which files it writes,
how it exposes no-ops and gaps, whether it installs security tooling, and what
it verifies before reporting done?

## Resolution

- **Evidence detection:** `SKILL.md` Phase 1 and
  `scripts/detect_project.py` show that the skill reads repository evidence for
  languages, manifests, tests, linters, type checkers, security configuration,
  CI, existing runners, instruction files, and specification hints. The
  detector only reads the project tree.
- **Feedback states:** `SKILL.md` Phase 2 and
  `references/gate-catalog.md` require every gate to be stated as **applies**,
  **no-op**, or **gap**, with a reason. This is the skill's explicit feedback
  on coverage and omissions.
- **Files changed:** `SKILL.md` Phases 3 and 4 instruct the skill to create or
  update one project checklist and short, managed definition-of-done blocks in
  the agent-instruction files the project uses. `references/agent-instructions.md`
  defines the supported Claude, AGENTS.md, Copilot, and Cursor locations.
- **Security boundary:** The skill can detect security-tool evidence in
  configuration, declared dependencies, build commands, and CI. It does not
  install security tools or verify that a local security executable is
  available. A missing required security check must be reported as a **gap**,
  not represented as installed.
- **Before it reports done:** `SKILL.md` requires the checklist to cover every
  catalog gate, exact commands and paths to trace to Phase 1 evidence, managed
  blocks to occur once per target file, and the runner command to exist and
  work. It also requires the project-specific gates themselves to pass.

Deck wording must say **detects and reports evidence and gaps**, not
**installs security tooling**.
