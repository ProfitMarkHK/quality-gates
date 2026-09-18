# Changelog

All notable changes to the quality-gates skill are recorded here. Dates are
when the work was done, not calendar releases — this project has not yet cut a
tagged release (see `docs/deployment-readiness.md`).

## Unreleased

### Marketplace 0.3.0: target setup docs and full file set

Added a `Setup` section to `SKILL.md` covering runtime (Python 3 stdlib
only), target-side tools (surfaced as gaps, never invented), the optional
LLM assessment `.env` configuration outside the target, and the Gate 12
`skills-ref` prerequisite. Moved skill-author material into a `Developer
notes` section (`SKILL.md`) and marked the eval scenarios in
`references/llm-assessment.md` as author-only. Listed `.env.example`,
`CONTEXT.md`, and `docs/adr/` in `Resources` so the shipped 14-file package
and the marketplace allowlist match. No gate, contract, or detector
behaviour changed.

### Retain failing LLM assessments for human review (AIDEV-532)

When advisory model output violates the assessment contract, the machine
path stays fail-closed (status `failed`, empty observations, byte-identical
deterministic review) and the raw text is quarantined to a timestamped file
in the operator working directory for human review only (AIDEV-534). The
validator reports the violating observation id and rule in machine-readable
form (AIDEV-533), recorded in result metadata without raw model text
(AIDEV-535). One bounded repair retry with fixed operator wording follows a
validation failure; the transient-HTTP budget is unchanged (AIDEV-536).
Adversarial-review hardening (AIDEV-538/539/540/541): atomic 0o600 quarantine
creation, no quarantine-path clobber, no quarantine on repair transport
failures, sanitized untrusted observation ids, unconditional
config-inside-target refusal. See
`skill/quality-gates/docs/adr/0003-quarantine-failed-assessments.md`.

### Live-exercise hardening (real gateway, classification-agent)

First live run against the approved GFO-X coding gateway surfaced three
brittleness bugs, all fixed and covered by offline tests plus an opt-in live
smoke test (`tests/test_llm_assessment_live.py`, skipped unless
`QUALITY_GATES_LIVE_SMOKE=1` with operator `QUALITY_GATES_LLM_*` env set):

- The assessment contract told the model what to look for but never the
  exact JSON fields, so live output failed validation on extra fields. The
  contract now states the full response schema, bans anything else, and
  demands bare JSON.
- Model output wrapped in markdown fences failed parsing. The seam strips
  one wrapping fence before parsing; unfenced prose still fails closed.
- One benign tool-name mention (e.g. "git" in ordinary prose) failed the
  entire assessment, discarding all valid observations. The advisory-text
  filter no longer flags bare tool names: only instruction-shaped content
  (imperatives, install/run verbs, installed/passing claims, code spans,
  command substitution, hyphenated tool commands) fails, since bare tool
  mentions in human-validated advisories have no attack path to gates.
- Live run also needs a larger output budget for verbose models (operator
  `QUALITY_GATES_LLM_MAX_OUTPUT_TOKENS`, within the model window) and a
  longer timeout for large inputs; the contract asks for at most 30
  observations, most significant first.

### Exclusion hardening (AIDEV-530)

- Fixed the gateway CLI using config before assignment and added CLI tests.
- Refused config directories resolving inside the target in both entry points.
- Replaced cross-segment `fnmatch` with shell-style matching (`*` stays in
  segment, `**` crosses, leading `**/` matches top level, trailing `/`
  matches everything under).
- Rejected carriage-return, null-byte, `.`, and backslash patterns and
  deduplicated entries.
- Surfaced excluded/total counts plus an all-excluded stderr warning.

### Consistency follow-up

- Added conditional Gate 12 for Agent Skill structure validation with
  `npx --yes skills-ref validate`, including detector evidence for each
  `SKILL.md` directory and an explicit no-op for non-skill projects.
- Corrected the bundled project-detection script path so an installed skill
  does not assume its script exists in the target project.
- Synced the general guidance with the skill's softened `PSScriptAnalyzer`
  policy and its distinction between automated runner gates and manual gates.
- Updated deployment readiness to expect the current 9-file package manifest.
- Clarified the domain glossary so manual gates remain binary without requiring
  every gate to be executable.

### Advisory LLM assessment

- Added an optional, best-effort LLM assessment after deterministic project
  detection. The secure assessment can surface unrecognised or ambiguous
  technology, but its source-backed recommendations remain advisory and cannot
  invent commands or change gate states.
- Added an explicit trust boundary, provenance requirements, completed/partial/
  unavailable/timed-out/failed statuses, and non-blocking failure handling.
- Added a standard-library contract adapter that serializes all target material,
  validates per-observation provenance, and rejects changes to deterministic
  review output.
- Added evaluation scenarios for unknown technology, repository instruction
  injection, and unavailable LLM capability.
- Added a provider-neutral gateway execution seam (`llm_assessment_execute.py`)
  for the approved internal gateway: OpenAI-compatible default with
  Anthropic-compatible alternative, operator `QUALITY_GATES_LLM_*`
  configuration with `.env.example`, dynamic output budget against the
  393216-token model limit, bounded timeout/retry, five lifecycle states that
  never block deterministic review, and offline fake-gateway tests plus an
  opt-in live smoke test.

### Domain model and documentation

- Added `CONTEXT.md` defining the core domain vocabulary — done-done, gate,
  applies/no-op/gap, evidence, runner, done-done block, and
  agent-instruction file — so documents stop drifting.
- Fixed runner definition in SKILL.md: Phase 3 now names the five manual gates
  (4, 5, 9, 10, 11) that do not belong in the runner, and Phase 4 clarifies
  that the done-done block covers them by reference.
- Added `docs/adr/0001-clean-preferred-for-c-cpp.md` — ADRs for the two
  non-obvious linting policies encoded in the gate catalog.
- Added `docs/adr/0002-psscriptanalyzer-not-optional.md` — PSScriptAnalyzer
  is a strong recommendation when PowerShell source exists; absent tooling is
  flagged as a gap, not a hard-fail, to avoid blocking projects that have not
  yet installed the module.

### Eval execution documentation

- Added `docs/running-evals.md` — step-by-step guide for running the behavioural
  eval suite: fixture extraction, skill-creator prerequisites, execution steps,
  output interpretation, and common failure modes.
- Updated `docs/deployment-readiness.md` item 3 to point to the new guide and
  note the skill-creator and fixture-extraction requirements.
- Updated `README.md` step 2 with pointer to `running-evals.md`; added note that
  `eval-*` root folders are stale optional working directories.
- Updated `CLAUDE.md` "behavioural changes re-tested" gate to point to the new
  guide for the procedure.

### PowerShell detection

- Added PowerShell detection to the project scanner, including
  `PSScriptAnalyzer` configuration and invocation evidence, and an explicit
  candidate when PowerShell lint tooling is missing.
- Documented that PowerShell parser checks do not replace
  `PSScriptAnalyzer` linting and that missing applicable tooling must be
  reported as a gap, not a hard-fail.

## 2026-08-14 — planning

- Added a local Wayfinder decision map for an internal explainer about
  agentic-development quality gates. The first resolved ticket records the
  skill's verified detection, feedback, instruction-file, and security-tooling
  boundaries.
- Added a dependency-free Pandoc-to-PowerPoint workflow for the explainer's
  Markdown source. The earlier Marp CLI option was rejected after a manual
  dependency audit reported high-severity findings.
- Resolved the explainer's self-guided eight-slide learning arc. It introduces
  evidence-based done-done gates through a fictional, language-neutral service.
- Resolved the security-tooling roadmap message. The deck now separates current
  evidence and gap reporting from a future, project-owner approved bootstrap
  path.
- Selected the Evidence rail from a three-variant information-architecture
  prototype. The prototype is preserved on its throwaway branch.
- Added the eight-slide, ASD-STE100 Markdown deck for the agentic-development
  quality-gates explainer.

## 2026-08-13 — process decision

- Deployment-readiness item #6 (description trigger-accuracy eval) demoted
  from **gap** to **deferred — not blocking**. The eval requires
  skill-creator's description-optimization loop, which shells out to the
  Claude Code CLI (`claude -p`); this project deliberately avoids that
  dependency. The item stays tracked but never blocks a release or wide
  sharing. Revisit only if skill triggering proves unreliable in practice.

## Iteration 2 — 2026-08-10

- Added gate 11, **specification alignment**: checks the implementation
  against available functional and technical specs (`docs/`, `spec/`, API
  schemas). Stated as a no-op when no spec exists, per the same honesty
  principle as every other gate. Mirrored into `quality-gates.md` as
  criterion 11.
- Added C / C++ support to `detect_project.py` and the gate catalog, including
  a deliberate linter-preference policy: prefer a linter named `Clean` when
  available, fall back to `clang-tidy` / `cppcheck` otherwise, and say which
  one was used and why.
- Added a fourth eval (`eval-4`) that runs the skill twice on the same repo to
  confirm the managed `<!-- BEGIN/END QUALITY GATES -->` fence updates in
  place on a second run rather than duplicating.
- Added a fixture C project (`jsonparser`) with a functional spec, exercising
  both the new gate and the linter policy together (`eval-3`).
- Added a safety note to the gate catalog and to `SKILL.md`'s verification
  step: every tool name and path written into a real project must trace to
  Phase 1 evidence for *that* project, not to an example from the catalog.
  This followed a near-miss where a run briefly copied C-specific example text
  into a Bash project's instruction file before self-correcting.
- Results: with-skill runs passed 100% of assertions across all 5 evals
  (19/19 in iteration 1's three original evals, 7/7 on the new C eval, 4/4 on
  idempotency); the C-project baseline (no skill) passed 5/7, missing exactly
  the two assertions that check the `Clean` preference policy.

## Iteration 1 — 2026-08-10

- Initial skill: `SKILL.md`, the gate catalog (10 gates at this point),
  agent-instruction-file conventions and idempotent-edit rules, the read-only
  `detect_project.py` scanner, and the checklist / done-done-block templates.
- Three evals covering a Python service (existing `CLAUDE.md`), a TypeScript
  app (enforcement across four instruction-file conventions at once), and a
  Bash-only repo with no tests and no instruction file (gap-flagging, no-op
  statements, creating an instruction file from scratch).
- Results: with-skill runs passed 100% of assertions (19/19); baseline runs
  (no skill) passed 52% (10/19) — the gap was consistently the same three
  behaviours: no single checklist document, no explicit no-op statements, and
  no single runner command.
- Packaged as `quality-gates.skill` and delivered.
