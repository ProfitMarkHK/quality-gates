# Quality gates — web-dashboard

The single source of truth for what **done-done** means in this project. Any
team member should be able to run these checks and know the answer. Keep this
file in sync with the tooling — an out-of-date checklist is a bug.

Evidence (Phase 1, `scripts/detect_project.py` + direct file reads):
TypeScript only (`src/format.ts`, `src/format.test.ts`); `package.json`
scripts `build` (`tsc -p tsconfig.json`), `test` (`jest`), `lint`
(`eslint "src/**/*.ts"`, config `.eslintrc.json`), `typecheck`
(`tsc --noEmit`), `format:check` (`prettier --check "src/**/*.ts"`);
`tsconfig.json` present; `jest`/`ts-jest` in devDependencies; no CI config,
no security tooling, no `docs/`/`spec/`/`specs/` spec, no `SKILL.md`.

Advisory LLM assessment: `unavailable` — no approved secure capability
configured (`QUALITY_GATES_LLM_ENABLED` unset/0) and network execution is out
of scope for this task. Deterministic evidence above remains authoritative;
no gate state was changed by advisory output.

## Run everything

```bash
npm run check
```

This command runs every automated gate and exits non-zero on any failure, so it
also works in pre-commit hooks and merge automation. It is the new `check`
script in `package.json` (the repo had individual `lint`, `format:check`,
`typecheck`, `test`, `build` scripts but no single runner):

```text
npm run lint && npm run format:check && npm run typecheck && npm test && npm run build
```

For each language-specific lint gate, record the exact command, settings file,
tool prerequisite or module installation, minimum version if relevant, any
intentional rule exclusions, and whether missing tooling fails closed. Syntax or
parser checks do not replace linting.

Lint detail: `npm run lint` runs `eslint "src/**/*.ts"` with settings
`.eslintrc.json` (requires `eslint` + `@typescript-eslint/parser` from
devDependencies; missing tooling fails closed — the runner exits non-zero).
`npm run format:check` runs `prettier --check "src/**/*.ts"` (requires
`prettier` from devDependencies; missing tooling fails closed). No intentional
rule exclusions.

## Gates

| # | Gate | State | Command / note |
|---|------|-------|----------------|
| 1 | All tests pass | applies | `npm test` (jest; covers `src/format.test.ts`) |
| 2 | End-to-end / acceptance tests pass | gap | no E2E suite found — only unit test `src/format.test.ts`; user-facing dashboard should add E2E as follow-up |
| 3 | Linters / formatters / static analysis pass | applies | `npm run lint` (eslint, `.eslintrc.json`) + `npm run format:check` (prettier) |
| 4 | New code covered by non-trivial tests | applies | manual review |
| 5 | Documentation updated | applies | manual review |
| 6 | Type checking passes | applies | `npm run typecheck` (`tsc --noEmit`, `tsconfig.json`) |
| 7 | Build / compile succeeds | applies | `npm run build` (`tsc -p tsconfig.json`) |
| 8 | Security / secrets checks pass | gap | no security tooling detected (no detect-secrets/gitleaks/dependabot/pre-commit config, no CI); never commit secrets; schedule secret + dependency scanning as follow-up |
| 9 | Change reviewed | applies | manual |
| 10 | Tracker / ticket reconciled | applies | manual |
| 11 | Implementation aligns with functional & technical specs | no-op | no functional or technical spec found in repo (no `docs/`, `spec/`, `specs/`, API schema, or tracker spec) |
| 12 | Agent Skill structure validates | no-op | no `SKILL.md` detected in project |

State legend: **applies** (must pass), **no-op** (does not apply — reason
given), **gap** (should apply but not yet possible — tracked as work).

## No-ops and gaps

State every no-op and gap here with its reason, so a reader can tell "checked
and not needed" from "forgotten":

- Gate 2 (E2E) — **gap**: project is a user-facing analytics dashboard but only a jest unit test (`src/format.test.ts`) exists; add an E2E suite before treating this gate as passing.
- Gate 8 (security/secrets) — **gap**: no secrets or dependency scanning is wired in; treat any exposed credential as compromised and add scanning (with an explicit severity threshold) as follow-up work.
- Gate 11 (spec alignment) — **no-op**: detector found no spec files and the repo has no `docs/`, `spec/`, `specs/`, or API schema to check against.
- Gate 12 (Agent Skill) — **no-op**: no `SKILL.md` detected, so there is nothing to validate.

## When a gate fails

Fix the code, not the gate. Diagnose the failure, fix all failures in the same
session where practical, and re-run until every gate is green. Never weaken a
check to force a pass.
