# Quality gates — pyservice

The single source of truth for what **done-done** means in this project. Any
team member should be able to run these checks and know the answer. Keep this
file in sync with the tooling — an out-of-date checklist is a bug.

## Run everything

```bash
./scripts/check.sh
```

This command runs every automated gate and exits non-zero on any failure, so it
also works in pre-commit hooks and merge automation. Prerequisite (same as CI):
`pip install -e . ruff mypy pytest`. Verified fail-closed: it exits 1 when
`ruff check .` reports an error.

Advisory LLM assessment status: **unavailable** — no approved secure LLM
assessment capability is configured in this environment, so no advisory
assessment was run. Gate states below rest entirely on deterministic evidence
(`scripts/detect_project.py` report plus direct reads of `pyproject.toml`,
`.github/workflows/ci.yml`, `src/`, and `tests/`).

For each language-specific lint gate, record the exact command, settings file,
tool prerequisite or module installation, minimum version if relevant, any
intentional rule exclusions, and whether missing tooling fails closed. Syntax or
parser checks do not replace linting.

## Gates

| # | Gate | State | Command / note |
|---|------|-------|----------------|
| 1 | All tests pass | applies | `python3 -m pytest` (CI runs bare `pytest`; `testpaths = ["tests"]` in `pyproject.toml`; suite: `tests/test_core.py`, 2 tests, verified passing once the package is installed) |
| 2 | End-to-end / acceptance tests pass | no-op | no E2E or acceptance tests exist; the package is a small pure-function library (`total_price` in `src/pyservice/core.py`) with no external surface to exercise |
| 3 | Linters / formatters / static analysis pass | applies | `ruff check .` — config `[tool.ruff]` in `pyproject.toml` (`line-length = 88`, lint select `E,F,I`); prerequisite: `ruff` module/binary (CI installs `ruff`); no rule exclusions; missing tooling fails closed. **Known failure at setup time:** `I001` unsorted import block in `tests/test_core.py` — fix the code (`ruff check --fix .`), not the gate |
| 4 | New code covered by non-trivial tests | applies | manual review |
| 5 | Documentation updated | applies | manual review (`README.md` is the user doc) |
| 6 | Type checking passes | applies | `python3 -m mypy src` (CI runs bare `mypy src`; config `[tool.mypy]` `strict = true` in `pyproject.toml`; verified passing) |
| 7 | Build / compile succeeds | no-op | interpreted Python project with no build, compile, or bundling step |
| 8 | Security / secrets checks pass | gap | no automated secrets or dependency-vulnerability scan is configured (nothing in `pyproject.toml` or `.github/workflows/ci.yml`); schedule adding one — until then, manual care: never commit secrets |
| 9 | Change reviewed | applies | manual peer review |
| 10 | Tracker / ticket reconciled | no-op | no issue tracker is referenced anywhere in the repo (no links in `README.md`, `pyproject.toml`, or CI config) |
| 11 | Implementation aligns with functional & technical specs | no-op | manual review vs n/a — no functional or technical spec found (no `docs/`, `spec/`, `specs/`, or API schema in the repo; detector `specs: []`) |
| 12 | Agent Skill structure validates | no-op | no `SKILL.md` in this project, so there is nothing to validate |

State legend: **applies** (must pass), **no-op** (does not apply — reason
given), **gap** (should apply but not yet possible — tracked as work).

## No-ops and gaps

State every no-op and gap here with its reason, so a reader can tell "checked
and not needed" from "forgotten":

- Gate 2 no-op: pure-function library, no external surface for E2E/acceptance tests.
- Gate 7 no-op: interpreted Python, no build step.
- Gate 8 gap: no secrets/dependency scan configured — follow-up work, not a dropped gate.
- Gate 10 no-op: no issue tracker referenced in the repo.
- Gate 11 no-op: no functional or technical spec exists in the repo or tracker.
- Gate 12 no-op: no Agent Skills in this project.

## When a gate fails

Fix the code, not the gate. Diagnose the failure, fix all failures in the same
session where practical, and re-run until every gate is green. Never weaken a
check to force a pass.
