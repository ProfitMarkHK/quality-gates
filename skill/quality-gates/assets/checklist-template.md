# Quality gates for {{PROJECT_NAME}}

The single source of truth for what **done-done** means in this project. Any
team member should be able to run these checks and know the answer. Keep this
file in sync with the tooling. An out-of-date checklist is a bug.

## Run everything

```bash
{{RUNNER_COMMAND}}
```

This command runs every automated gate and exits non-zero on any failure, so it
also works in pre-commit hooks and merge automation.

For each language-specific lint gate, record the exact command, settings file,
tool prerequisite or module installation, minimum version if relevant, any
intentional rule exclusions, and whether missing tooling fails closed. Syntax or
parser checks do not replace linting. Gate 3 includes the complexity budget:
strict max cyclomatic complexity 10 per function/method, tests excluded, no
grandfathering. Record its exact command alongside the linter (e.g. Python:
`ruff check --select C901` with `mccabe-complexity = 10` scoped to source,
plus `xenon --max-absolute B --max-modules B --max-average B` where the
project adopts the strict companion).

## Gates

| # | Gate | State | Command / note |
|---|------|-------|----------------|
| 1 | All tests pass | {{STATE}} | {{DETAIL}} |
| 2 | End-to-end / acceptance tests pass | {{STATE}} | {{DETAIL}} |
| 3 | Linters / formatters / static analysis pass (incl. complexity ≤ 10, tests excluded) | {{STATE}} | {{DETAIL}} |
| 4 | New code covered by non-trivial tests | {{STATE}} | manual review |
| 4b | Implemented state transitions covered | {{STATE}} | manual review — enumerate implicit state machines in code the change touches; every implemented transition entered by a test or stated unreachable; re-audit when code starts retaining state |
| 5 | Documentation updated | {{STATE}} | manual review |
| 6 | Type checking passes | {{STATE}} | {{DETAIL}} |
| 7 | Build / compile succeeds | {{STATE}} | {{DETAIL}} |
| 8 | Security / secrets checks pass | {{STATE}} | {{DETAIL}} |
| 9 | Change reviewed | {{STATE}} | manual |
| 10 | Tracker / ticket reconciled | {{STATE}} | manual |
| 11 | Implementation aligns with functional & technical specs | {{STATE}} | manual review vs {{SPEC_LOCATION}} |
| 12 | Agent skill structure validates | {{STATE}} | `npx --yes skills-ref validate <skill-directory>` for each detected skill |
| 13 | Functional core / imperative shell boundary | {{STATE}} | manual review — for changes touching domain logic: domain modules import no I/O; clock/env/network injected; one decode path; when unclear, apply and record the uncertainty |

State legend: **applies** (must pass), **no-op** (does not apply, reason
given), **gap** (should apply but not yet possible, tracked as work).

## No-ops and gaps

State every no-op and gap here with its reason, so a reader can tell "checked
and not needed" from "forgotten":

- {{NOOP_OR_GAP_NOTES}}

## When a gate fails

Fix the code, not the gate. Diagnose the failure, fix all failures in the same
session where practical, and re-run until every gate is green. Never weaken a
check to force a pass.
