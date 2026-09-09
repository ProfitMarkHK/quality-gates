# Quality gates — backup-scripts

The single source of truth for what **done-done** means in this project. Any
team member should be able to run these checks and know the answer. Keep this
file in sync with the tooling — an out-of-date checklist is a bug.

## Run everything

```bash
make check
```

(`make check` calls `./scripts/check.sh`.) This command runs every automated
gate and exits non-zero on any failure, so it also works in pre-commit hooks
and merge automation.

For each language-specific lint gate, record the exact command, settings file,
tool prerequisite or module installation, minimum version if relevant, any
intentional rule exclusions, and whether missing tooling fails closed. Syntax or
parser checks do not replace linting.

Lint detail (gate 3): exact command `shellcheck scripts/*.sh` plus
`bash -n scripts/*.sh`; settings file: none (no `.shellcheckrc` in repo);
prerequisite: `shellcheck` installed (verified 0.11.0); minimum version: none
pinned; intentional rule exclusions: none; missing tooling fails closed —
`scripts/check.sh` exits 1 with an install pointer when `shellcheck` is absent.
`bash -n` syntax checks supplement but do not replace `shellcheck`.

## Gates

| # | Gate | State | Command / note |
|---|------|-------|----------------|
| 1 | All tests pass | **gap** | no tests exist — no test files, no test dir, no `make check` test step yet; starting a suite is tracked as work |
| 2 | End-to-end / acceptance tests pass | **no-op** | no E2E or acceptance tests exist; small local shell utilities verified manually |
| 3 | Linters / formatters / static analysis pass | **applies** | `shellcheck scripts/*.sh` and `bash -n scripts/*.sh` via `make check` / `./scripts/check.sh` |
| 4 | New code covered by non-trivial tests | **applies** | manual review |
| 5 | Documentation updated | **applies** | manual review (`README.md`) |
| 6 | Type checking passes | **no-op** | Bash is untyped; no type-checker applies |
| 7 | Build / compile succeeds | **no-op** | interpreted shell scripts; no compile or bundling step |
| 8 | Security / secrets checks pass | **gap** | no automated secrets scan configured; check manually that no credentials are committed; follow-up is to add a secrets scanner |
| 9 | Change reviewed | **applies** | manual peer review |
| 10 | Tracker / ticket reconciled | **no-op** | no issue tracker in use for this project |
| 11 | Implementation aligns with functional & technical specs | **no-op** | no functional or technical spec found (checked `docs/`, `spec/`, `specs/`, API schemas, tracker — none exist) |
| 12 | Agent Skill structure validates | **no-op** | no `SKILL.md` in project |

State legend: **applies** (must pass), **no-op** (does not apply — reason
given), **gap** (should apply but not yet possible — tracked as work).

## No-ops and gaps

- Gate 1 (gap): `detect_project.py` found 0 test files and no test directory; there is nothing to run yet. Follow-up: add a smoke test (e.g. backup/restore round-trip on temp dirs) and wire it into `scripts/check.sh`.
- Gate 2 (no-op): no E2E/acceptance suite exists and the scripts expose only a local CLI; manual verification suffices.
- Gate 6 (no-op): Bash-only project (2 `.sh` files); static typing does not apply.
- Gate 7 (no-op): interpreted scripts; `make run` invokes `./scripts/backup.sh` directly with no build step.
- Gate 8 (gap): no security tooling detected and none configured. Follow-up: add a secrets scan or document the manual check; never commit credentials.
- Gate 10 (no-op): no tracker or issues directory detected; nothing to reconcile.
- Gate 11 (no-op): spec search found nothing (`specs` empty in detector report, no `docs/` yet besides this file); absence of a spec is noted, not ignored.
- Gate 12 (no-op): no Agent Skill (`SKILL.md`) detected.

## Advisory LLM assessment

Status: `unavailable` — no approved secure LLM assessment capability was
configured in this environment (`QUALITY_GATES_LLM_ENABLED` unset) and network
execution was out of scope, so no advisory assessment was attempted. The gate
states above rest entirely on deterministic evidence (`scripts/detect_project.py`
report plus direct reads of `Makefile`, `README.md`, `scripts/backup.sh`,
`scripts/restore.sh`).

## When a gate fails

Fix the code, not the gate. Diagnose the failure, fix all failures in the same
session where practical, and re-run until every gate is green. Never weaken a
check to force a pass.
