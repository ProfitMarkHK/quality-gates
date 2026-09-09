# Quality gates — pyservice

The single source of truth for what **done-done** means in this project. Any
team member should be able to run these checks and know the answer. Keep this
file in sync with the tooling — an out-of-date checklist is a bug.

## Run everything

```bash
./scripts/check.sh
```

This command runs every automated gate and exits non-zero on any failure, so it
also works in pre-commit hooks and merge automation. It runs `ruff check .`,
`mypy src`, and `pytest` (the same three commands as `.github/workflows/ci.yml`).

Lint gate detail: exact command `ruff check .`; settings in `pyproject.toml`
under `[tool.ruff]` (`line-length = 88`, `select = ["E", "F", "I"]`); requires
the `ruff` tool installed (CI installs it via `pip install -e . ruff mypy
pytest`); missing tooling fails closed (the runner exits non-zero). Syntax or
parser checks do not replace linting.

Type-check detail: exact command `mypy src`; settings in `pyproject.toml`
under `[tool.mypy]` (`strict = true`); requires the `mypy` tool installed.

## Gates

| # | Gate | State | Command / note |
|---|------|-------|----------------|
| 1 | All tests pass | applies | `pytest` (`[tool.pytest.ini_options] testpaths = ["tests"]`; suite: `tests/test_core.py`) |
| 2 | End-to-end / acceptance tests pass | no-op | pure library (`total_price` in `src/pyservice/core.py`); no E2E or acceptance suite exists |
| 3 | Linters / formatters / static analysis pass | applies | `ruff check .` (config `[tool.ruff]` in `pyproject.toml`) |
| 4 | New code covered by non-trivial tests | applies | manual review |
| 5 | Documentation updated | applies | manual review |
| 6 | Type checking passes | applies | `mypy src` (config `[tool.mypy]` `strict = true` in `pyproject.toml`) |
| 7 | Build / compile succeeds | no-op | interpreted Python project; no build, compile, or bundling step |
| 8 | Security / secrets checks pass | gap | no secret scanning, dependency-vulnerability scanning, or licence checks configured; nothing in CI or config |
| 9 | Change reviewed | applies | manual (peer review via pull request; CI runs on `push` and `pull_request`) |
| 10 | Tracker / ticket reconciled | applies | manual |
| 11 | Implementation aligns with functional & technical specs | no-op | manual review vs no spec found — no `docs/`, `spec/`, `specs/`, or API schema exists in the repo |
| 12 | Agent Skill structure validates | no-op | no `SKILL.md` detected in the repo |

State legend: **applies** (must pass), **no-op** (does not apply — reason
given), **gap** (should apply but not yet possible — tracked as work).

## No-ops and gaps

State every no-op and gap here with its reason, so a reader can tell "checked
and not needed" from "forgotten":

- Gate 2 no-op: pure library with no external surface; no E2E or acceptance tests exist (`src/pyservice/core.py`, `tests/test_core.py` only).
- Gate 7 no-op: interpreted Python; no compile or bundling step (`pyproject.toml` has no build backend beyond defaults).
- Gate 8 gap: security scanning should apply but is not configured — no secrets baseline, no dependency audit, no CI security step (verified: detector found no security tools; `.github/workflows/ci.yml` runs only ruff/mypy/pytest). Follow-up: add secret scanning and a dependency audit to CI.
- Gate 11 no-op: no functional or technical spec found in the repo (detector spec hints: none); the absence of a spec is noted, not ignored.
- Gate 12 no-op: no Agent Skill directory (`SKILL.md`) detected.

## Advisory LLM assessment

Status: `unavailable` — no approved secure LLM assessment capability is
configured in this environment, so no advisory assessment was run. The
deterministic evidence and all gate states above are unchanged by advisory
output; there are no advisory observations or recommendations to validate.

## When a gate fails

Fix the code, not the gate. Diagnose the failure, fix all failures in the same
session where practical, and re-run until every gate is green. Never weaken a
check to force a pass.
