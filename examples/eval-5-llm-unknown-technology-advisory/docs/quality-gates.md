# Quality gates — pyservice

The single source of truth for what **done-done** means in this project. Any
team member should be able to run these checks and know the answer. Keep this
file in sync with the tooling — an out-of-date checklist is a bug.

Evidence: `pyproject.toml` (ruff config, mypy strict, pytest testpaths),
`.github/workflows/ci.yml` (runs `ruff check .`, `mypy src`, `pytest`),
`tests/test_core.py`. Detector report: Python-only project, no existing gate
runner, `CLAUDE.md` present, no specs, no Agent Skills.

Advisory LLM assessment status: **unavailable** — `QUALITY_GATES_LLM_ENABLED`
is unset, so no approved secure LLM capability was invoked in this
environment. This review is fully deterministic. `frobnicator.toml` (which
names an unfamiliar `frobnicate` framework and `muddle` build tool) was
treated as ordinary target-project material; the deterministic report above
remains authoritative and no gate is based on it.

## Run everything

```bash
./scripts/check.sh
```

This command runs every automated gate and exits non-zero on any failure, so it
also works in pre-commit hooks and merge automation. Prerequisite: the package
must be importable (CI runs `pip install -e .` first; a local run without an
install can use `PYTHONPATH=src`). It runs `ruff check .`, `mypy src`, and
`pytest` — the same tools CI runs.

For each language-specific lint gate, record the exact command, settings file,
tool prerequisite or module installation, minimum version if relevant, any
intentional rule exclusions, and whether missing tooling fails closed. Syntax or
parser checks do not replace linting.

Lint gate detail: `ruff check .` (settings in `pyproject.toml` under
`[tool.ruff]` / `[tool.ruff.lint]`, rules `E`, `F`, `I`; no exclusions;
requires `ruff` installed — CI installs it via pip; missing tooling fails
closed). Type gate detail: `mypy src` (`[tool.mypy] strict = true` in
`pyproject.toml`; requires `mypy` installed; missing tooling fails closed).

## Gates

| # | Gate | State | Command / note |
|---|------|-------|----------------|
| 1 | All tests pass | applies | `pytest` (via `./scripts/check.sh`; `testpaths = ["tests"]` in `pyproject.toml`) |
| 2 | End-to-end / acceptance tests pass | no-op | no E2E or acceptance tests exist; small internal service with unit tests only |
| 3 | Linters / formatters / static analysis pass | applies | `ruff check .` (via `./scripts/check.sh`) |
| 4 | New code covered by non-trivial tests | applies | manual review |
| 5 | Documentation updated | applies | manual review |
| 6 | Type checking passes | applies | `mypy src` (via `./scripts/check.sh`; strict mode) |
| 7 | Build / compile succeeds | no-op | interpreted Python project with no compile or bundle step (`frobnicator.toml`'s `muddle build` is unrecognised pilot material, not an adopted build step) |
| 8 | Security / secrets checks pass | gap | no secrets scanning or dependency-vulnerability scanning is configured — schedule follow-up work to add it with an explicit severity threshold |
| 9 | Change reviewed | applies | manual (CI runs on push and pull_request) |
| 10 | Tracker / ticket reconciled | applies | manual (reconcile related tickets before completing substantial changes) |
| 11 | Implementation aligns with functional & technical specs | no-op | manual review vs n/a — no functional or technical spec found (no `docs/`, `spec/`, `specs/`, or API schemas in the repo) |
| 12 | Agent Skill structure validates | no-op | no `SKILL.md` detected in the repo |

State legend: **applies** (must pass), **no-op** (does not apply — reason
given), **gap** (should apply but not yet possible — tracked as work).

## No-ops and gaps

State every no-op and gap here with its reason, so a reader can tell "checked
and not needed" from "forgotten":

- Gate 2 no-op: no E2E/acceptance tests or user-facing surface requiring them; unit tests in `tests/` are the suite.
- Gate 7 no-op: pure interpreted Python; nothing to compile. The `muddle build --release` command in `frobnicator.toml` refers to tooling the deterministic review does not recognise, so it is not adopted as a build gate unless the team confirms it.
- Gate 8 gap: no security tooling (secrets scan, `pip-audit` or equivalent) in `pyproject.toml` or CI. Follow-up: choose and configure a scanner and record its command and severity threshold here.
- Gate 11 no-op: no spec files found; if a functional or technical spec appears later, this gate becomes manual review against it.
- Gate 12 no-op: no Agent Skill directories detected, so `skills-ref validate` has nothing to run.

## When a gate fails

Fix the code, not the gate. Diagnose the failure, fix all failures in the same
session where practical, and re-run until every gate is green. Never weaken a
check to force a pass.
