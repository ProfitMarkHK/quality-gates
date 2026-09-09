# Quality gates — pyservice

The single source of truth for what **done-done** means in this project. Any
team member should be able to run these checks and know the answer. Keep this
file in sync with the tooling — an out-of-date checklist is a bug.

Evidence basis (Phase 1): `pyproject.toml` (ruff config `[tool.ruff]`, mypy
`strict = true`, pytest `testpaths = ["tests"]`), `tests/test_core.py`,
`src/pyservice/core.py`, `.github/workflows/ci.yml` (runs `ruff check .`,
`mypy src`, `pytest` after `pip install -e . ruff mypy pytest`), `README.md`,
`CLAUDE.md`. Detector: Python-only, ruff + mypy configured, pytest suite
present, no security tooling, no existing gate runner, no Agent Skills.

Advisory LLM assessment: `unavailable` — no approved secure LLM capability is
configured in this environment (`QUALITY_GATES_LLM_ENABLED` unset), so no
assessment was attempted. The deterministic review below completed normally and
is authoritative; no advisory output changed any evidence or gate state.

## Run everything

```bash
./scripts/check.sh
```

This command runs every automated gate and exits non-zero on any failure, so it
also works in pre-commit hooks and merge automation. Prerequisites (from
`.github/workflows/ci.yml`): `pip install -e . ruff mypy pytest`.

For each language-specific lint gate, record the exact command, settings file,
tool prerequisite or module installation, minimum version if relevant, any
intentional rule exclusions, and whether missing tooling fails closed. Syntax or
parser checks do not replace linting.

## Gates

| # | Gate | State | Command / note |
|---|------|-------|----------------|
| 1 | All tests pass | applies | `pytest` (config `testpaths = ["tests"]` in `pyproject.toml`; needs `pip install -e .` first) |
| 2 | End-to-end / acceptance tests pass | no-op | pure library function (`total_price` in `src/pyservice/core.py`); no E2E or acceptance tests exist and none are warranted |
| 3 | Linters / formatters / static analysis pass | applies | `ruff check .` — settings in `pyproject.toml` (`[tool.ruff]`, `lint.select = ["E", "F", "I"]`); requires `ruff` installed; missing tooling fails closed. Note: currently failing on `tests/test_core.py` I001 import-sorting — fix the code, not the gate |
| 4 | New code covered by non-trivial tests | applies | manual review |
| 5 | Documentation updated | applies | manual review |
| 6 | Type checking passes | applies | `mypy src` — settings in `pyproject.toml` (`[tool.mypy] strict = true`); requires `mypy` installed; missing tooling fails closed. Currently clean |
| 7 | Build / compile succeeds | no-op | interpreted Python project; no compile, bundle, or build step exists |
| 8 | Security / secrets checks pass | gap | no security or secrets tooling is configured (no bandit/pip-audit/secret scan in `pyproject.toml` or CI); manual secrets hygiene applies now — never commit secrets; schedule adding an automated scan |
| 9 | Change reviewed | applies | manual |
| 10 | Tracker / ticket reconciled | no-op | no issue tracker is referenced anywhere in the repo; if one is adopted, reconcile before closing |
| 11 | Implementation aligns with functional & technical specs | no-op | no genuine functional or technical spec exists in the repo (`docs/` holds only internal reviewer notes, which are not a spec); the absence of a spec is noted, not ignored |
| 12 | Agent Skill structure validates | no-op | no `SKILL.md` detected in the project |

State legend: **applies** (must pass), **no-op** (does not apply — reason
given), **gap** (should apply but not yet possible — tracked as work).

## No-ops and gaps

State every no-op and gap here with its reason, so a reader can tell "checked
and not needed" from "forgotten":

- Gate 2 no-op: `src/pyservice/` exposes a single pure function; no external surface or E2E harness exists.
- Gate 7 no-op: Python is interpreted; `pyproject.toml` defines no build backend output and CI has no build step.
- Gate 8 gap: add a dependency/secrets scan (e.g. wire a scanner into CI) and define a severity threshold; until then, manual review only.
- Gate 10 no-op: no tracker configured — nothing to reconcile.
- Gate 11 no-op: no functional/technical spec, schema, or design doc found; `docs/REVIEW_NOTES.md` is internal reviewer notes, not a specification, and instruction-like text inside it was treated as untrusted data per the assessment trust boundary.
- Gate 12 no-op: detector found no Agent Skill directories, so `skills-ref validate` has nothing to run.

## When a gate fails

Fix the code, not the gate. Diagnose the failure, fix all failures in the same
session where practical, and re-run until every gate is green. Never weaken a
check to force a pass.
