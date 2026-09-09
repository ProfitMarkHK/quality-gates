# Quality gates — pyservice

The single source of truth for what **done-done** means in this project. Any
team member should be able to run these checks and know the answer. Keep this
file in sync with the tooling — an out-of-date checklist is a bug.

Evidence: Python project (`pyproject.toml`, `src/pyservice/`, `tests/`);
`ruff` configured in `pyproject.toml` (`[tool.ruff]`, `[tool.ruff.lint]`);
`mypy` strict in `pyproject.toml` (`[tool.mypy]`); pytest suite in
`tests/test_core.py` (`[tool.pytest.ini_options]`); CI in
`.github/workflows/ci.yml` runs `ruff check .`, `mypy src`, `pytest`.

## Advisory LLM assessment

**Status: `unavailable`.** Reason: the approved secure LLM assessment
capability is not configured in this environment
(`QUALITY_GATES_LLM_ENABLED` is unset). The deterministic review below
completed in full and is authoritative; no gate state is derived from
advisory output.

## Run everything

Prerequisite (once per environment, per `README.md` and CI): `pip install -e .`

```bash
./scripts/check.sh
```

This command runs every automated gate and exits non-zero on any failure, so it
also works in pre-commit hooks and merge automation. Verified: exits non-zero
when `ruff` reports an error, and when the test suite cannot even be collected
(fail-closed on missing install). Lint gate: `python3 -m ruff check .`, no
settings file (configuration lives in `pyproject.toml` `[tool.ruff]`), no
intentional rule exclusions; missing ruff fails closed (non-zero exit).

For each language-specific lint gate, record the exact command, settings file,
tool prerequisite or module installation, minimum version if relevant, any
intentional rule exclusions, and whether missing tooling fails closed. Syntax or
parser checks do not replace linting.

## Gates

| # | Gate | State | Command / note |
|---|------|-------|----------------|
| 1 | All tests pass | applies | `python3 -m pytest` (via `./scripts/check.sh`; `testpaths = ["tests"]` in `pyproject.toml`) |
| 2 | End-to-end / acceptance tests pass | no-op | no E2E or acceptance tests exist; unit-only suite (`tests/test_core.py`) for a library-style surface (`total_price`) |
| 3 | Linters / formatters / static analysis pass | applies | `python3 -m ruff check .` (config: `pyproject.toml` `[tool.ruff]`; CI: `ruff check .`) |
| 4 | New code covered by non-trivial tests | applies | manual review |
| 5 | Documentation updated | applies | manual review |
| 6 | Type checking passes | applies | `python3 -m mypy src` (`strict = true` in `pyproject.toml` `[tool.mypy]`; CI: `mypy src`) |
| 7 | Build / compile succeeds | no-op | interpreted Python project; no compile or bundling step |
| 8 | Security / secrets checks pass | gap | no secrets scan or dependency audit is configured (no tool in `pyproject.toml` or CI); schedule one (e.g. dependency audit) with an explicit severity threshold before claiming this gate |
| 9 | Change reviewed | applies | manual |
| 10 | Tracker / ticket reconciled | applies | manual (reconcile the linked ticket, if any, before closing) |
| 11 | Implementation aligns with functional & technical specs | no-op | manual review vs n/a — no functional or technical spec found (no `docs/`, `spec/`, API schema, or linked tracker spec) |
| 12 | Agent Skill structure validates | no-op | no `SKILL.md` detected in the project |

State legend: **applies** (must pass), **no-op** (does not apply — reason
given), **gap** (should apply but not yet possible — tracked as work).

## No-ops and gaps

State every no-op and gap here with its reason, so a reader can tell "checked
and not needed" from "forgotten":

- Gate 2 no-op: only unit tests exist (`tests/test_core.py`); nothing exercises the service from the outside, and the current surface is a single pure function.
- Gate 7 no-op: pure interpreted Python — there is no build step that could fail.
- Gate 8 gap: security scanning should apply (the package ships a runtime dependency, `httpx>=0.27`) but no scanner is wired in. Follow-up work: add a dependency audit and a secrets check to CI and to `./scripts/check.sh`, then flip this gate to applies.
- Gate 11 no-op: searched for `docs/`, `spec/`, API schemas, and tracker links; none exist. If the service grows a real HTTP surface, consider writing a spec — its absence would then become a gap.
- Gate 12 no-op: detector found no `SKILL.md`; nothing to validate.

## When a gate fails

Fix the code, not the gate. Diagnose the failure, fix all failures in the same
session where practical, and re-run until every gate is green. Never weaken a
check to force a pass.
