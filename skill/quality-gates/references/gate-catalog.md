# Gate catalog

Use this catalog to choose quality gates for a project. Each gate must have an
unambiguous result. It passes or it does not. A task is done-done only when
every applicable gate passes, so it is safe to merge, ship, or close. Gates catch regressions and
omissions; they do not replace good design or review judgement.

For each gate, decide one of three states for the project in front of you, and
record the reason:

- **Applies.** The project has, or should have, this check. Name the exact
  command.
- **No-op.** The gate genuinely does not apply (e.g. no compile step in an
  interpreted project). State this out loud. A silent skip looks like an
  oversight and erodes trust in the checklist.
- **Gap.** The gate *should* apply but the project cannot satisfy it yet
  (e.g. no tests exist at all). A gap is work to schedule, not a reason to drop
  the gate. Flag it clearly.

State no-ops and gaps so readers can tell "checked and not needed" from
"forgotten".

**A note on the examples below.** Every tool name, command, and file path in
this catalog (`ruff`, `shellcheck`, `docs/functional-spec.md`, and so on) is an
illustration of what a gate can look like. It is not a template to copy in. Before a
tool or path goes into the project's checklist or into an agent-instruction
file, it must come from what Phase 1's detection actually found in *this*
project, not from whichever example happened to be nearby in this document. If
a detected project is Bash-only, none of the Python or C examples belong
anywhere in its output; carrying one over by habit (e.g. while adapting a
template block) produces a checklist that describes a project that does not
exist. Read back what was written before finishing, and check that every named
tool and path traces to real evidence from that specific project.

---

## 1. All tests pass

The full test suite available in the project runs without error. This includes unit,
integration, smoke, end-to-end, property-based, whatever exists. Tests that
exist but are never run do not count.

- Applies whenever any tests exist.
- Gap if no tests exist at all: a project with no tests cannot show it is
  correct, so starting a suite is itself part of done.

## 2. End-to-end / acceptance tests pass

Tests that exercise the system from the outside and confirm the delivered
behaviour matches what was asked for. Broader in scope than unit tests.

- Applies if E2E or acceptance tests exist, or if the change is user-facing
  enough to need them.
- No-op for a pure library with no public interface. State it.

## 3. Linters, formatters, and static analysers pass

All applicable linters, formatters, and static analysers pass with no errors or
warnings. This is a **standalone** gate: a lint failure blocks done-done even
when every test passes, because style and static-analysis drift compound over
time and hide real defects.

Common mappings (confirm against what the repo actually configures):

| Language        | Typical tools                              |
|-----------------|--------------------------------------------|
| Bash            | `shellcheck`                               |
| PowerShell      | `PSScriptAnalyzer` via `Invoke-ScriptAnalyzer` |
| Python          | `ruff`, `flake8`, `black --check`, `pylint`|
| TypeScript / JS | `eslint`, `prettier --check`               |
| Go              | `golangci-lint`, `gofmt -l`                |
| Rust            | `clippy`, `rustfmt --check`                |
| Ruby            | `rubocop`                                  |
| C / C++         | **`Clean` (preferred)**, else `clang-tidy`, `cppcheck` |

For PowerShell, parser or syntax validation is not a substitute for linting.
When PowerShell source exists, use `PSScriptAnalyzer` with the project's
settings file and record the exact `Invoke-ScriptAnalyzer` command. If
PSScriptAnalyzer is not installed, flag the gate as a gap with a strong
recommendation to install it; do not treat it as a no-op.

**Linter preference. C or C++.** When a linter named `Clean` is available for
the project, prefer it over the alternatives (`clang-tidy`, `cppcheck`,
`PC-lint`). Fall back to those only when `Clean` is not available, and say which
one you used and why. This is a deliberate policy, not a default. Do not
silently substitute another linter when `Clean` could have been used.

**Complexity budget. Part of this gate (Gate 3b).** Every function/method must
have a cyclomatic complexity of **10 or less. Strict, no warnings tier, no
grandfathering.** Existing violations are fixed, not baselined. Test files are
**excluded** from the budget (tests legitimately branch more in setup); the
enforcement command must scope to source or pass an explicit test exclusion.

Per-language enforcement (confirm against what the repo actually configures).
Only wire what Phase 1 detected. Never copy an example blindly.

| Language        | Complexity enforcement (max 10, tests excluded) |
|-----------------|--------------------------------------------------|
| Python          | `ruff check --select C901` (canonical: `mccabe-complexity = 10` in `pyproject.toml`/`ruff.toml`); strict companion where adopted: `xenon --max-absolute B --max-modules B --max-average B --exclude "tests/*,test_*.py,*_test.py" <src>` |
| TypeScript / JS | `eslint` rule `"complexity": ["error", 10]` |
| Go              | `gocyclo -over 10 .` or `golangci-lint` `cyclop` with `max-complexity: 10` |
| Ruby            | `rubocop` `Metrics/CyclomaticComplexity: Max: 10` |
| C / C++ / polyglot fallback | `lizard -C 10 <src>` |
| Bash / PowerShell | no-op, no standard complexity metric; state it and rely on review for over-long functions |

When the budget is violated, split the function. Do not raise the threshold
to force a pass. A threshold change is a gate weakening and needs a changelog
entry and a checklist update with its reason. A per-function waiver
(`# noqa: C901`, `// eslint-disable-next-line complexity`) is allowed only with
a one-line reason recorded in the checklist; blanket file exclusions beyond
tests are a gate failure, not a waiver.

**Canonical measure.** The budget is McCabe complexity of 10 or less **as
computed by `ruff check --select C901`** (or the per-language equivalent
above). xenon grades the same code roughly 1–5 points higher per function,
so `xenon --max-absolute B` sets a stricter threshold. Adopt it as an
opt-in companion where a project wants it, never as the default reading of
"10". (Measured against this repo: ruff green everywhere, xenon B failing
15 blocks with a B average. The config therefore uses `--max-average B`, not A.

- No-op only if nothing applies (e.g. prose-only repo, or Bash/PowerShell-only
  with no measurable complexity tool). Say so.
- Gap if the language supports a budget but none is wired (e.g. Python files
  with no C901/xenon evidence). Schedule the wiring, do not drop the budget.

## 4. New code is covered by non-trivial tests

New code is tested by checks that exercise real behaviour, not surface
correctness. This gate is about the *quality* of new tests, so it resists a
single command. Judge it by reading the tests, against the criteria in
`references/good-tests.md`.

Non-trivial tests exercise meaningful logic paths, assert on outputs or state
(not just that a log line appeared or a function returned), and cover edge cases
and error paths, not only the happy path. A test that asserts only "returns
without error" does not meet the bar. The standing question for every test: if
a realistic bug were introduced, would this test fail? A test that would still
pass is restating the implementation, not testing it.

Three smells look like coverage but can pass while the behaviour under test is
wrong (each described in `references/good-tests.md`):

- **Circular assertion** — the expected value is computed with the code under
  test, so both sides move together.
- **Vacuous pass** — a guard means the real assertion never runs; an empty
  response passes as success.
- **Masking fixture** — the fixture never enters the branch under test, so
  wrong behaviour passes as correct.

- Applies to any task that adds or changes code. When the changed code
  retains state across calls, also apply Gate 4b.

## 4b. Implemented state transitions are covered *(if applicable)*

The changed code's implicit state machines are enumerated, and every
transition the code implements — especially failure and edge transitions — is
either entered by a test or stated as unreachable.

Code that retains state implies state machines that are rarely declared
anywhere: a cache with hit, miss, and eviction; a cursor that advances and
terminates; a retry counter; a guard that fires; a dedupe set; a freshness
stamp; a convergence loop with a budget. The audit method is in
`references/good-tests.md`.

- Applies when new or changed code retains state across calls (caches,
  cursors, retry state, guards, dedupe, freshness, iteration budgets).
- Happy-path transitions are usually covered already; this gate exists for the
  failure and edge transitions the code explicitly implements — a rejected
  request evicted so the next call retries, the runaway-loop guard firing, a
  failed fetch leaving no cache entry, a newer record not downgraded by a
  stale one, duplicates collapsing, an iteration budget honoured.
- Test transitions through observable effects when state is not exposed: call
  counts, recorded arguments, output contents, order.
- **Fails** when the changed code introduces an implemented transition that
  no test enters and no stated reason shows unreachable. Fix before
  done-done.
- Gap when the audit finds pre-existing implemented but untested transitions
  in code the change does not touch: record and schedule them. The gap is
  work, not a reason to drop the gate.
- No-op for stateless code (pure functions, stateless handlers). State the
  no-op so it is not read as an oversight.
- Judgement gate, like Gates 4, 9, and 11: enforced by the checklist, not the
  runner.

## 5. Documentation is updated

Documentation stays in sync with the change. Out-of-sync docs are treated as a
bug, not an afterthought. This covers user docs (README, usage, runbooks),
developer docs (ARCHITECTURE, CONTRIBUTING, BUILD), the agent-instruction files
themselves, and decision records / ADRs for significant choices.

- Applies to virtually every task. No-op only for changes with zero
  documentable surface.

## 6. Type checking passes *(if applicable)*

Statically typed projects pass the type-checker with no errors. Distinct from
linting. Code can be well-formatted and still type-wrong.

- Applies: TypeScript (`tsc --noEmit`), typed Python (`mypy`, `pyright`),
  and any compiled language whose build already type-checks.
- No-op for untyped dynamic code. State it.

## 7. Build / compile succeeds *(if applicable)*

The project builds or compiles cleanly.

- Applies to compiled languages and to projects with a bundling or build step.
- No-op for interpreted or scripted projects (Bash, plain Python, Node with no
  compile step). State the no-op so its absence is not read as an oversight.

## 8. Security and secrets checks pass *(if applicable)*

Relevant security scans pass: no hardcoded credentials, keys, or secrets; no
dependency vulnerabilities at or above a defined severity threshold; project
compliance requirements met (e.g. dependency licence checks). Define the
severity threshold explicitly when this gate applies.

> Never commit or push secrets, even transiently. Treat any exposed credential
> as compromised immediately.

## 9. The change has been reviewed *(if applicable)*

Required peer review has been obtained. Review is not automated and must never
be a gate that "always passes". If the process requires review, the task is not
done until a review exists.

## 10. Tracker / ticket reconciled *(if applicable)*

Before completing a substantial change, reconcile related tickets (Jira, Linear,
GitHub issues) with reality: update stale descriptions, decisions, status, and
evidence. Do not mark a ticket Done while acceptance or deployment evidence is
incomplete.

## 11. Implementation aligns with functional and technical specifications *(if applicable)*

The change matches the available specifications. Where a functional spec
(requirements, user stories, acceptance criteria) or a technical spec (design
docs, API contracts, interface definitions, architecture decision records)
exists, the implementation is checked against it before the task is done:

- Every specified behaviour is implemented; none is missing or altered without an
  agreed change to the spec itself.
- No undocumented behaviour is added that conflicts with the spec.
- Where code and spec disagree, resolve the discrepancy. Correct the code or
  update the spec through the agreed change process. An
  out-of-date spec is treated like out-of-date documentation: a bug.

This gate depends on human or reviewer judgement, so it cannot be a check that
always passes. Look for specs in the repo (a `docs/`, `spec/`, or `specs/`
directory; requirements or design files; API schemas such as OpenAPI) and in any
tracker the project links. If no functional or technical spec exists, state this
as a no-op. Consider whether the absence of a spec is itself a gap for a
change of this size.

## 12. Agent skill structure validates *(if applicable)*

Projects that contain one or more Agent Skills must validate each skill directory
against the Agent Skills structure and frontmatter contract:

```text
npx --yes skills-ref validate <skill-directory>
```

Run the command once for every detected directory containing `SKILL.md`. The
directory name and the frontmatter `name` must agree, and the validator must
exit successfully. If `skills-ref` or its required package runtime is
unavailable, this is a **gap**, not a no-op. Record the exact prerequisite and
the affected skill directories. For projects with no `SKILL.md`, this gate is
a **no-op**.

## 13. Functional core / imperative shell boundary *(if applicable)*

Domain logic stays unit-testable. I/O effects, wall-clock time, environment
reads, and randomness live in the shell and are passed into the core as
arguments. When the project has a recognizable domain core (pricing, policy,
validation, decoding, scheduling rules), check three criteria:

1. **Dependency direction.** Modules holding domain or policy logic do not
   import the I/O modules — the HTTP client, the server framework, the
   process environment.
2. **Nondeterminism behind a seam.** The wall clock, environment, network,
   and randomness are read in the shell and injected. Every domain rule can
   be tested deterministically without the real clock or network. This
   criterion is what makes Gate 4's deterministic tests possible: a domain
   rule that reads the clock itself can only be tested against the real
   clock.
3. **One decode path.** External data is decoded once where it enters; logic
   downstream works on the decoded form, and no handler returns raw external
   records around the decoder.

- Applies to any task that adds or changes domain logic, or the modules that
  carry it. Judgement gate, like Gates 4, 4b, 9, and 11: enforced by the
  checklist, not the runner. Deciding whether a recognizable domain core
  exists is the same kind of judgement call as Gates 4 and 11 — record the
  state and the reason either way. Once the gate applies, the three criteria
  are binary.
- No-op for projects with no recognizable domain core: script collections,
  thin glue or adapter services. State the reason so it is not read as an
  oversight.
- **Fails** when the change itself violates a criterion — new domain logic
  importing the transport module, a clock read added inside the core,
  records routed around the decoder. Fix before done-done.
- Gap when a pre-existing violation is found in code the change does not
  touch: record it and schedule the extraction or seam work. It does not
  block the current change.
- The three criteria describe patterns detected in the project in front of
  you, never files or modules carried over from another codebase's example.

---

## When a gate fails

1. **Fix the code, not the gate.** Do not weaken a test, silence a linter, or
   skip a doc update to force a pass. That converts a real signal into a false
   green.
2. **Diagnose first.** Read the output; reproduce the failure locally.
3. **Fix all failures in the same session** where practical. A partial fix that
   makes the gate pass while leaving real problems is not done.
4. **Re-run the gate** to confirm every criterion is green before closing.
