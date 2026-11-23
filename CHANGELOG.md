# Changelog

All notable changes to the quality-gates skill are recorded here. Dates show
when the work was done, not calendar releases. This project has not yet cut a
tagged release. See `docs/deployment-readiness.md`.

## Unreleased

### Remote structural CI

A GitHub Actions workflow (`.github/workflows/validate.yml`) now runs the
deterministic, secret-free gates on every push to `main` and every pull
request: `scripts/validate_skill.py`, the detector unit tests, `skills-ref
validate` (via a Node runner, where it is cheaper than maintaining npx
locally), and a packaging smoke test whose log shows the packaged file list
on every run — the exact file count remains a release-time check
(deployment-readiness item 8), not an equality that would go red on `main`
before an unrelated content PR merges. What deliberately stays local and
manual: the behavioural evals (agent sessions) and the LLM-assessment
evals 5-7 (gateway credentials never enter a public repo's CI). This change
touches no skill behaviour — `SKILL.md`, `references/`, `assets/`, and
`detect_project.py` are untouched and the packaged `.skill` is
byte-identical — so the behavioural re-test gate is a stated no-op, not a
silent skip. The roadmap item "add a CI workflow once a remote exists" is
cleared; enabling branch protection on `main` (requiring the validate
checks) remains a GitHub-settings follow-up for an org admin.

The first remote run caught a real portability bug the local environment
could not see: the conftest-hermetic test spawns a child `pytest` process,
which exists on the development machine but not on a bare runner, so CI now
installs pytest explicitly — the second-environment signal remote CI exists
for, working as intended.

Branch protection on `main` is enabled: the `structural-gates` check is
required (strict), enforced for admins too, with force pushes and deletions
blocked. Applied with the repo-creator account, which already holds
repo-admin rights; no separate org-admin credential was needed. From this
point every change to `main` lands through a green-checked PR, including
this one.

### Good-tests reference, Gate 4b state-transition coverage, and Gate 13 core/shell boundary

Gate 4 gains a concrete test-quality bar in a new reference,
`references/good-tests.md`: the assertion-independence question ("if a
realistic bug were introduced, would this test fail?"), three failure smells
(circular assertion, vacuous pass, masking fixture), and a warning that call
counts prove less than they appear to. Gate 4b requires the changed code's
implicit state machines to be enumerated and every implemented transition —
especially failure and edge transitions — entered by a test or stated
unreachable; the audit method is in the same reference. Gate 13 checks the
functional core / imperative shell boundary: dependency direction,
nondeterminism behind an injected seam, and one decode path at the boundary.
Both new gates are judgement gates (checklist-enforced, not runner commands)
with the standard applies/no-op/gap states; Gate 13 is a no-op for projects
with no recognizable domain core.

Motivation, recorded from live use against a TypeScript market-data service
on 2026-11-23: a suite that had passed conventional review still contained a
circular pricing assertion, a vacuously-true live test, and a fixture that
masked a real pricing bug (a degenerate input returned zero in every case); a
state-machine pass then found six implemented but untested failure/edge
transitions, all closed with tests that each fail under a named plausible
bug; a core/shell review found domain modules importing the transport module,
wall-clock reads inside domain logic, and raw wire records bypassing the
decoders. All three additions generalize those findings. No fixture, tool, or
project appears in the skill text (example-leakage rule): the
new prose names only patterns (a cache, a cursor, a guard, an injected clock)
and says they are illustrations; the motivating findings appear only as
generalized, anonymous stories.

Mirrored per the docs-sync rule: `quality-gates.md` criterion 4 expanded and
criteria 4b and 13 added; the checklist template's gate table gained rows 4b
and 13; `SKILL.md` Phase 2 now points at the good-tests reference and Phase 3
lists the judgement gates as 4, 4b, 5, 9, 10, 11, and 13; `CONTEXT.md`'s
runner entry updated; deployment-readiness item 8 corrected to 18 packaged
files (the previous "exactly 14" had already drifted out of date before this
change; ADR-0004, ADR-0005, and the quarantine reader had been added without
updating it).

Structural gates: `scripts/validate_skill.py` passes, `npx --yes skills-ref
validate skill/quality-gates` passes, detector unit tests 116 pass (1 live
smoke skip). Behavioural gate: evals 0-4 re-run with and without the change
in ten blind agent sessions against fresh fixture copies. Result:
**30/30 assertions with the change, 30/30 without (60/60), no regression.**
The new gates landed as designed: Gate 4b appears in every with-change
checklist as a grounded no-op (each fixture is stateless code) and Gate 13
applies with grounded reasons where a domain core exists (py-service,
web-dashboard, jsonparser) while recording a designed no-op for
backup-scripts ("no recognizable domain core"); idempotency (eval-4) holds
with one marker pair and one checklist after a double run; coordinator
spot-checks of the produced files confirmed the agent reports and found zero
leakage from the new reference text. Packaging re-verified once:
`package_skill.py` writes exactly 18 files including
`references/good-tests.md`. Evals 5-7 (LLM assessment) are untouched by this
change and retain their iteration 3/4 live-gateway results.

Revised after independent review (Claude Opus, high effort): a violation the
change itself introduces now **fails** Gates 4b and 13, while pre-existing
violations in untouched code remain recorded gaps (previously both were
worded as gaps, so a change could ship its own untested transition); the
`quality-gates.md` mirrors now define the same gates as the catalog exactly
(the mirror had dropped 4b's new-or-changed-code scoping, the
stated-unreachable clause, and Gate 13's trigger); the checklist template's
4b/13 rows now carry their criteria instead of a bare "manual review";
`good-tests.md` scopes its bar to unit tests and states how full-task tests
are judged differently; SKILL.md's Phase 2 insertion no longer splits the
gate-11 paragraph and no longer points Gate 13 readers at the good-tests
reference; README lists the new reference. The reviewer's findings that
remain only partially addressed are accepted with reasons: the property-based
case is added to the unit-test bar (finding 6), Gate 13's applies decision
keeps its judgement explicitly and now defaults to applies-when-unclear for
code being changed (finding 7), and the leakage claim now says the
motivating findings appear as generalized, anonymous stories (finding 9).
The larger remaining finding — no fixture exercises 4b or 13, so the suite
cannot detect regressions in this change itself — is recorded as roadmap
work (a stateful fixture with expectations for 4b and 13) rather than
silently accepted.

### Documentation prose cleanup

- Rewrote project guidance, skill references, templates, and release notes to
  use plainer prose and sentence-case headings.
- Clarified that the quality-gates skill works with any coding agent. Claude
  references remain where they describe a supported instruction-file convention
  or record an actual historical eval run.

### Cyclomatic complexity budget as Gate 3b

Gate 3 now includes a strict complexity budget: max cyclomatic complexity 10
per function/method, tests excluded, no grandfathering. Fix violations
by splitting the function, never by raising the threshold. Python enforces
with `ruff check --select C901` (`mccabe-complexity = 10`) plus strict
`xenon --max-absolute B --max-modules B --max-average A` scoped to source;
other languages use their detected equivalent (`eslint` `complexity` 10,
`gocyclo -over 10` / cyclop 10, `lizard -C 10`); Bash/PowerShell-only projects
state a no-op. `detect_project.py` reports a new `complexity` evidence key
(ruff-C901, xenon, eslint-complexity, gocyclo/cyclop, lizard, plus
`(candidate)` gaps when source exists without wiring) with a `Complexity`
summary line; the checklist template's Gate 3 row and `SKILL.md` Phase 3
runner rule name the budget explicitly. Mirrored in `quality-gates.md`
criterion 3 and `references/gate-catalog.md` Gate 3 per the docs-sync rule.

Self-application (no grandfathering): the new budget failed closed on this
repo's own source, so every violation was fixed by splitting, not waived:
`detect_project.py::detect` split into module-level walk / package /
build-CI / tool-evidence / complexity / runner / spec helpers;
`llm_assessment_execute.py::execute_assessment` restructured into an
`_AssessmentRun` phase class (prepare / fetch / settle / repair / loop
methods. Nested closures count toward the outer C901 score, so nesting
alone could not fix it. `validate_result` was split into head / observation /
reference / recommendation / tail validators; plus smaller splits in
`build_input_package`, `build_redacted_preview`, `build_offending_items`,
`parse_exclude_patterns`, `_quarantine_write`, `validate_skill.validate`,
and `quarantine_read.summarize`. Root `pyproject.toml` wires the budget
(`mccabe-complexity = 10`, tests/examples excluded). The detector now
reports `Complexity: ruff-C901` on this repo instead of the candidate gap.
All unit tests pass with no behavior change. Still pending per this repo's
own done-done: rerun the eval suite in a Claude session. This is a manual gate
and cannot be waved through by a script.

Gate clarification (same session, recorded as a threshold correction with
its reason): ruff C901 ≤10 is the canonical measure; xenon is an opt-in
stricter companion, not a second reading of "10". Measured against this
repo with xenon 0.9.3 (pipx install, system Python untouched): xenon
grades the same code about 1–5 points higher per function. Ruff passed
everywhere, while xenon B failed 15 blocks with a B average. Therefore the
`--max-average A` first written here was unenforceable fail-closed and is
corrected to B. xenon-strict adoption is scheduled follow-up, itemized so
it cannot rot into a silent gap: `contract.py` `_validate_advisory_text`,
`_collapse_pattern_for_dir`, `main`, `load_exclude_patterns_for_target`,
`_glob_to_regex`; `detect_project.py` `summarize`, `_detect_gate_runner`;
`execute.py` `measure_input_tokens`, `extract_openai_text`, `load_config`,
`_http_host_allowed`, `_quarantine_write`, `main`, `parse_dotenv`,
`_run_attempt_loop`; plus the B average.

### Soften advisory-text rule for descriptive configured plus hedges (AIDEV-548)

The validator rejected benign descriptive prose. A live quarantine flagged
an observation solely for "configured" in "configured via a hardcoded base
URL". `_validate_advisory_text` no longer denylists "configured" (static
config presence, verifiable from cited material; "installed"/"passing"
still assert unverifiable runtime state) and masks single-word hedged
predicates ("appears/seems (to be) X") before the lexical checks. The
single-word bound holds: "appears to be passing" passes but "appears to be
configured and passing" still fails on "passing". The redaction
neutralizer shows "configured" plainly; repair and fail-closed paths
unchanged. See ADR 0005 for the accepted residual risk.

### Calibrate advisory observations to cut dependency noise (AIDEV-549)

Live runs filled all 30 observation slots by reporting every manifest dependency
and standard-library module as custom technology. The fixed assessment contract
now requires gate relevance. It covers technology absent from the deterministic
review that changes gate mapping, auth or secret handling, custom build, test, or
security tooling, and vendored code. The contract excludes categories such as
detected-language standard libraries, manifest-pinned versions, and generic
HTTP, serialization, test, and build libraries unless custom configured. It
groups related items and caps the result at eight observations. An empty result
is valid. The rules use categories instead of a package blocklist.

### Self-describing quarantine envelopes plus a display-only reader (AIDEV-547)

Quarantine files held the full model output as one escaped `raw_text`
string with the violating rule but no locator. The deterministic-review
echo buried the one failing sentence in bulk output. New envelopes carry summary
keys before `raw_text`: `echo` (byte size plus identical/not-identical
verdict against the sent review), `offending` (the failing observation or
uncertainties, redacted), and the persisted `redacted_preview`; `raw_text`
stays byte-identical, and unparsable output nulls the summary keys. The new
display-only `scripts/quarantine_read.py` renders old and new envelopes as
a triage summary without dumping the echo. Fail-closed behaviour, file
permissions, and atomic writes unchanged.

### Narrow the advisory-text semicolon rule (AIDEV-545)

`_validate_advisory_text` rejected any `;`, so the 2026-09-24 live run
failed twice on benign clause punctuation and burned its single repair
retry on unfixable wording. A semicolon now fails only when it cannot be
prose punctuation. It fails when no whitespace follows the semicolon, as in
`cmd1;cmd2`. The `&&`, `||`, pipe, substitution, backtick, URL, and
verb/target rules are unchanged, as is the preview neutralizer mapping.
Spaced bare-word chains are treated as English clauses: they are lexically
identical to ordinary punctuation and chains carrying real payloads still
trip the other rules. Covered by new denylist tests, and the live smoke
test now passes against the gateway.



### Quarantine output under a dedicated subdirectory (AIDEV-544)

Failing assessments were quarantined into the operator working directory,
which in practice is the config directory holding the `.env`. This caused data
outputs to accumulate alongside configuration. Quarantine files now default
to a `quarantine/` subdirectory (created 0700) under the working directory:
nothing new lands at the config top level. File guarantees are unchanged
(0600 via atomic O_CREAT|O_EXCL, same human-review envelope), as are the
never-inside-target invariant and the config-inside-target refusal.
Covered by updated quarantine tests plus a config-dir-with-`.env` case.



### Display-only redacted previews for rejected LLM observations

Advisory-text rejections discarded the whole assessment while the raw text
sat in a human-only quarantine file, so benign flags (`install
instructions`, `command-line`) were indistinguishable from real ones inside
a live session. Contract violations with a parsed candidate now also attach
`metadata.redacted_preview`: up to 5 neutralized observation/uncertainty
hints (ASCII-only, NFKC-stable category tags, capped at 500 chars per span).
The machine path stays fail-closed (`failed`, empty observations,
byte-identical deterministic review, one bounded repair retry unchanged);
previews never enter gate mapping. The denylist is broader to close the
underbroad hole the review found (`rm -rf`, `curl | sh` previously passed):
raw URLs, shell chaining (`&&`, `||`, compact `;`, spaced pipes, `${`, backslashes),
and dangerous verbs with targets now fail validation, while bare tool
mentions still pass. See `docs/adr/0004-redacted-preview-display-only.md`.
Covered by `tests/test_llm_assessment_redaction.py` (13 tests: denylist,
neutralizer table, ASCII/NFKC/idempotency/re-validation properties,
envelope caps, seam preview + quarantine + no-raw-leak).

### Collapse fully-excluded subtrees in the LLM assessment input (AIDEV-543)

The first live run against classification-agent failed closed. The input was
7 MB, above the 200 KB cap. Of that, 5.98 MB came from 18,565 per-file
`excluded` placeholders under `my_ai_brain/.venv`. The actual project content
was 52 files and 934K characters, about 248K tokens, within the model budget.
`build_input_package` now prunes a directory without
descent and emits one `collapsed: true` placeholder only when a
trailing-slash pattern covers it or a `**/NAME/**` pattern names its basename
literally; file globs, bare names, and anchored patterns still descend.
`references/llm-assessment.md` documents the collapse. Four new hermetic
tests cover prefix pruning, basename pruning, no-prune cases, and
real-material-set equality on a fake venv fixture.

### Harden `.env.example` exclusion patterns

Field experience on a large target with 18,619 materials and a roughly 900 MB
virtual environment showed that the old example missed nested caches. A plain
`.pytest_cache/**` pattern does not match nested copies. Use `**/` for that.
The example also lacked patterns for logs, `.env` files, and credential
directories. The scanner never reads `.gitignore`. It base64-encodes any
unexcluded binaries into the package. The example now ships the
31-pattern hardened set (lockfiles, venv, bytecode/caches, `data/`,
logs/jsonl, `.DS_Store`, secrets, reports/coverage, media/archive/data
binaries) with a comment explaining the `**/` and bare-basename rules.
Docs-only change; no contract or detector behaviour changed.

### Fix inverted hermetic env guard in the test suite

`tests/conftest.py` only stripped exported `QUALITY_GATES_LLM_*` operator
variables when `QUALITY_GATES_LIVE_SMOKE=1`, the opposite of its documented
intent. With gateway config exported and the live flag off, the variables
leaked into unit tests (`test_config_dir_inside_target_is_refused` failed,
and a unit test could reach a real gateway). The guard now strips them for
every non-live test regardless of the flag; the live module keeps its env.
`tests/test_conftest_hermetic.py` runs the real conftest in a child pytest
process to lock this in. Test-only change; no skill behaviour changed.

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

- Added `CONTEXT.md` defining the core domain vocabulary: done-done, gate,
  applies/no-op/gap, evidence, runner, done-done block, and
  agent-instruction file. This gives the docs consistent definitions.
- Fixed runner definition in SKILL.md: Phase 3 now names the five manual gates
  (4, 5, 9, 10, 11) that do not belong in the runner, and Phase 4 clarifies
  that the done-done block covers them by reference.
- Added `docs/adr/0001-clean-preferred-for-c-cpp.md`. ADRs for the two
  non-obvious linting policies encoded in the gate catalog.
- Added `docs/adr/0002-psscriptanalyzer-not-optional.md`. PSScriptAnalyzer
  is a strong recommendation when PowerShell source exists; absent tooling is
  flagged as a gap, not a hard-fail, to avoid blocking projects that have not
  yet installed the module.

### Eval execution documentation

- Added `docs/running-evals.md`, a guide for running the behavioural
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

## 2026-08-14. Planning

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

## 2026-08-13. Process decision

- Deployment-readiness item #6 (description trigger-accuracy eval) demoted
  from **gap** to **deferred, not blocking**. The eval requires
  skill-creator's description-optimization loop, which shells out to the
  Claude Code CLI (`claude -p`); this project deliberately avoids that
  dependency. The item stays tracked but never blocks a release or wide
  sharing. Revisit only if skill triggering proves unreliable in practice.

## Iteration 2. 2026-08-10

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

## Iteration 1. 2026-08-10

- Initial skill: `SKILL.md`, the gate catalog (10 gates at this point),
  agent-instruction-file conventions and idempotent-edit rules, the read-only
  `detect_project.py` scanner, and the checklist / done-done-block templates.
- Three evals covering a Python service (existing `CLAUDE.md`), a TypeScript
  app (enforcement across four instruction-file conventions at once), and a
  Bash-only repo with no tests and no instruction file (gap-flagging, no-op
  statements, creating an instruction file from scratch).
- Results: with-skill runs passed 100% of assertions (19/19); baseline runs
  (no skill) passed 52% (10/19). The same three gaps appeared each time:
  behaviours: no single checklist document, no explicit no-op statements, and
  no single runner command.
- Packaged as `quality-gates.skill` and delivered.
