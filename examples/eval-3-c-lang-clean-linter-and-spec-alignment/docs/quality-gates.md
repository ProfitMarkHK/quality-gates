# Quality gates — jsonparser

The single source of truth for what **done-done** means in this project. Any
team member should be able to run these checks and know the answer. Keep this
file in sync with the tooling — an out-of-date checklist is a bug.

## Run everything

```bash
make check
```

This command runs every automated gate (`build` + `lint` + `test`) and exits
non-zero on any failure, so it also works in pre-commit hooks and merge
automation. (`make` stops on the first failing prerequisite, so a lint failure
blocks done-done even when tests would pass.)

For each language-specific lint gate, record the exact command, settings file,
tool prerequisite or module installation, minimum version if relevant, any
intentional rule exclusions, and whether missing tooling fails closed. Syntax or
parser checks do not replace linting.

## Gates

| # | Gate | State | Command / note |
|---|------|-------|----------------|
| 1 | All tests pass | applies | `make test` (`ctest --test-dir build --output-on-failure`) |
| 2 | End-to-end / acceptance tests pass | no-op | pure C library, no E2E surface or E2E tests |
| 3 | Linters / formatters / static analysis pass | applies | `make lint` → `clang-tidy src/*.c -- -Iinclude`; no config file; no rule exclusions; missing tooling fails closed (see below for Clean decision) |
| 4 | New code covered by non-trivial tests | applies | manual review |
| 5 | Documentation updated | applies | manual review |
| 6 | Type checking passes | applies | `make build` — the C compiler type-checks; no separate type-checker is configured |
| 7 | Build / compile succeeds | applies | `make build` (`cmake -S . -B build && cmake --build build`, C11) |
| 8 | Security / secrets checks pass | gap | no automated secrets or dependency scan is configured (see below) |
| 9 | Change reviewed | applies | manual |
| 10 | Tracker / ticket reconciled | applies | manual — reconcile related issues when they exist; no tracker is linked in the repo |
| 11 | Implementation aligns with functional & technical specs | applies | manual review vs `docs/functional-spec.md` + `docs/api.md` |
| 12 | Agent Skill structure validates | no-op | no `SKILL.md` in this project |

State legend: **applies** (must pass), **no-op** (does not apply — reason
given), **gap** (should apply but not yet possible — tracked as work).

## No-ops and gaps

- Gate 2, no-op: `jsonparser` is a pure C library (`src/parse.c`,
  `include/parse.h`) with no service, CLI, or external surface to drive
  end-to-end; verification is the unit suite in `tests/test_parse.c` run via
  `make test`.
- Gate 3, linter choice: per project policy the `Clean` linter is preferred for
  C, but no `Clean` binary, config, or reference to it was found anywhere in the
  repo or the environment (`which Clean clean` → not found; detector reports
  only `clang-tidy` in `Makefile`). So this gate uses the repo's configured
  fallback, `clang-tidy` via `make lint`, and that is stated here rather than
  silently substituted. Neither `clang-tidy` nor `cppcheck` is installed in the
  current environment, so the lint step cannot pass here until the tool is
  installed — missing tooling fails closed, it does not waive the gate.
- Gate 8, gap: the repo has no secrets scanning, dependency audit, or CI
  wiring (detector: `security_tools: {}`, `ci: []`). Follow-up work: add an
  automated secrets check and a defined severity threshold before this gate can
  pass automatically; until then, manual review must confirm no hardcoded
  credentials, keys, or secrets are committed.
- Gate 11, spec note: `docs/functional-spec.md` FR-1 (leading-digit value,
  `-1` for non-digit start and NULL) matches the current `parse_uint`
  implementation; FR-2 (overflow → `-2`) is explicitly planned and not yet
  implemented, so any change touching value accumulation must be checked
  against FR-2's pending contract, and implementing FR-2 requires updating the
  spec status, `include/parse.h`, and tests together.
- Gate 12, no-op: detector found no `SKILL.md`; there is no skill directory to
  run `npx --yes skills-ref validate` against.

## Advisory LLM assessment

Status: `unavailable` — `QUALITY_GATES_LLM_ENABLED` is unset and no approved
secure LLM assessment capability is configured, so no advisory assessment was
run. Reason recorded here per the assessment contract; the deterministic review
above (detector JSON plus direct reads of `Makefile`, `CMakeLists.txt`,
`sources`, `tests/`, and `docs/`) is the authoritative evidence, and all gate
states come from it unchanged.

## When a gate fails

Fix the code, not the gate. Diagnose the failure, fix all failures in the same
session where practical, and re-run until every gate is green. Never weaken a
check to force a pass.
