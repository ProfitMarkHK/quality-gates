# Quality Gates — Guidance

Quality gates are checks that run before a task is considered **done** — the point
after which it is safe to merge, ship, or close. A gate is only useful if its
result is unambiguous: either it passes or it does not.

## The Done-Done Question

Before defining gates, ask: *what does done mean for this project?* A task that
passes its gates may still need review, but it must not be blocked waiting for
checks that could have been run earlier. Gates catch regressions and omissions,
they do not substitute for good design.

---

## Criteria

### 1. All tests pass

All available tests pass without error. "Tests" means the full suite available in
the project — unit, integration, smoke, E2E, property-based, or whatever applies.

If the existing test suite is insufficient — coverage gaps, missing scenarios,
confidence below what the software requires — new tests must be proposed,
implemented, and then passed before the task is done. Tests that exist but are
not run do not count.

### 2. All end-to-end / acceptance tests pass

End-to-end or acceptance tests (if they exist) pass. These differ from unit tests
in scope: they exercise the system from the outside, confirming that components
work together and that the behaviour delivered matches what was asked for.

### 3. All linters and static analysers pass

All applicable linters, formatters, and static analysers pass without errors or
warnings. This is a standalone gate — a lint failure blocks done-done regardless
of whether tests pass.

The set of linters depends on the project. Common examples:

| Project type | Linters / analysers |
|---|---|
| Bash | `shellcheck` |
| PowerShell | `PSScriptAnalyzer` via `Invoke-ScriptAnalyzer` |
| Python | `ruff`, `flake8`, `mypy` |
| TypeScript / JS | `eslint`, `tsc --noEmit` |
| Go | `golangci-lint` |
| Rust | `clippy`, `rustfmt` |
| General | `prettier --check`, conventional-commit hook |

For PowerShell, parser or syntax validation is not a substitute for linting.
When PowerShell source exists, use `PSScriptAnalyzer` with the project's
settings file and record the exact `Invoke-ScriptAnalyzer` command. If the
analyzer is applicable but unavailable, mark the gate as a gap or fail the
runner closed; do not silently treat it as a no-op.

If no linter applies, this gate is a no-op — but it must be stated as such,
not silently skipped.

### 4. New code is covered by non-trivial tests

New code is subject to tests that evaluate complex, real-world application
behaviour rather than just surface-level correctness.

**Non-trivial means the tests:**
- Exercise meaningful logic paths, not just call counts or exit codes
- Assert on outputs or state, not only on the presence of log lines
- Cover edge cases and error paths, not only the happy path
- Are independent of implementation detail where appropriate (behaviour, not
  just structure)

**Trivial tests are not sufficient** — a test that asserts only that a function
returns without error, or that a log line contains a string, does not meet this
threshold.

### 5. Documentation is updated

Documentation is kept in sync with the changes made. This includes:

- User-facing documentation (README, usage guides, runbooks)
- Developer documentation (ARCHITECTURE, CONTRIBUTING, BUILD, setup guides)
- Agent instruction files (AGENTS.md, copilot-instructions.md, skill docs)
- Decision records, ADRs, or runbooks for significant architectural choices

Documentation that is out of sync with the code is treated as a bug — it is not
acceptable to leave it stale and move on.

### 6. Type checking passes *(if applicable)*

Projects written in statically typed languages must pass the type-checker without
errors. This is distinct from linting: a program may be syntactically correct and
well-formatted but still contain type errors.

### 7. Build / compile succeeds *(if applicable)*

Projects with a build or compile step must pass it. For interpreted or scripted
projects without one, state this gate as a no-op.

### 8. Security and secrets checks pass *(if applicable)*

Relevant security scans pass — for example:

- No hardcoded credentials, API keys, or secrets in the codebase
- No dependency vulnerabilities at or above a defined severity threshold
- Compliance requirements for the project are met (e.g., dependency licence checks)

> **Warning:** Do not commit or push secrets to repositories, even transiently.
> Treat exposed credentials as compromised immediately.

### 9. The change has been reviewed *(if applicable)*

Code changes have been reviewed by an appropriate reviewer. Peer review is not
automated and cannot be a gate that always passes — if the process requires a
review, the task is not done until one has been obtained.

### 10. Associated Jira tickets match project reality *(if applicable)*

Before completing a substantial change, reconcile every related Jira ticket with
the current project state. Update stale descriptions, decisions, status, and
evidence comments. Do not mark a ticket Done while acceptance or deployment
evidence is incomplete.

### 11. Implementation aligns with functional and technical specifications *(if applicable)*

The change matches the available specifications. Where a functional
specification (requirements, user stories, acceptance criteria) or a technical
specification (design documents, API contracts, interface definitions,
architecture decision records) exists, the implementation is checked against it
before the task is done:

- Every specified behaviour is implemented. No specified behaviour is missing,
  or changed, without an agreed change to the specification itself.
- The implementation adds no undocumented behaviour that conflicts with the
  specification.
- Where the code and the specification disagree, the discrepancy is resolved —
  either the code is corrected, or the specification is updated through the
  agreed change process. An out-of-date specification is treated like out-of-date
  documentation: a bug.

This gate depends on human or reviewer judgement, so it cannot be a check that
always passes. If no functional or technical specification exists, state this as
a no-op — and consider whether the absence of a specification is itself a gap to
address for a change of this size.

---

## Project-Specific Considerations

### Projects with no build phase

For interpreted or scripted projects (Bash, Python, Node without a compile step),
the "build succeeds" gate is a no-op. State this explicitly so the absence is
not mistaken for an oversight.

### Projects with no test phase

If a project has no tests at all, this is a gap to address before the work is
done — not a reason to skip the gate. A project with no tests cannot demonstrate
correctness; one must be started.

### Projects with no linter

If no linter applies (e.g., prose documentation only), state that linting is a
no-op for this project.

### Projects with an existing test baseline

When adding tests to an existing project, the baseline tests are part of "all
tests pass." New tests do not replace the baseline; they add to it.

---

## Automation

Where possible, quality gates should be executable by a single command so that
they can be run:

- Before marking a task done
- Automatically before merging
- By any team member without special setup

A typical pattern:

```bash
# All gates in one command
make check          # or: ./scripts/check.sh
```

The gate runner should produce clear output and exit non-zero on any failure,
so that it can be used in pre-commit hooks and merge automation.

If a gate cannot be automated, state this explicitly and document the manual
step — do not let it become an informal bypass.

---

## When a Gate Fails

When a quality gate fails:

1. **Fix the code, not the gate.** Do not weaken the test, remove the linter
   warning, or skip the documentation check to make the gate pass.
2. **Diagnose the failure first.** Read the output; run the failing command
   locally to confirm.
3. **Fix all failures in the same session** where practical — a partial fix
   that makes the gate pass temporarily while leaving real problems is not done.
4. **Re-run the gate** to confirm all criteria are green before closing the
   task.

---

## Defining Your Project's Gates

Every project should document its own gate checklist in a project-specific
document. This generic document is the foundation — tailor it:

- Add project-specific linters and analysers
- Remove gates that are no-ops for your project
- Add gates that are specific to your compliance, security, or product
  requirements
- State which gates are automated vs manual
- Define the severity threshold for security checks (if applicable)

The checklist should be short enough to scan and unambiguous enough that any
team member can run it and know the answer.
