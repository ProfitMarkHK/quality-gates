# Deployment readiness — quality-gates skill

This is the quality-gates skill's own checklist, in the same vocabulary it
teaches: every item is **applies** (must be green before release), **no-op**
(genuinely not relevant to a skill, stated so it isn't mistaken for an
oversight), **gap** (should be done, isn't yet — tracked as work, not
quietly dropped), or **deferred** (optional; tracked but never blocking —
revisit when conditions change). Run through this before tagging a release or
widely sharing the packaged `.skill` file.

| # | Check | State (as of iteration 4) | How |
|---|-------|------|-----|
| 1 | `SKILL.md` structural validation passes | **Applies — green** | `python3 scripts/validate_skill.py` |
| 2 | Detection script runs cleanly on representative project types | **Applies — green** | Exercised by evals against Python, TypeScript, Bash, C, and PowerShell fixtures, plus detector tests and a smoke check |
| 3 | Eval suite: 100% with-skill pass rate, no regression vs. previous iteration | **Applies — pending manual re-run** | Automated adapter contract tests pass (14/14), including executable unknown-technology, injection-boundary, and unavailable-status scenarios. See `docs/running-evals.md` for the full skill-creator procedure; skill-creator must be installed separately and `fixtures.zip` extracted before running. A direct Claude CLI behavioral check was attempted on 2026-08-18 but could not run because the CLI is not logged in. |
| 4 | Idempotency: re-running on an already-gated repo doesn't duplicate the managed block | **Applies — green** | Covered by eval-4 |
| 5 | Policy correctness spot-checked (no example leakage across languages) | **Applies — green** | Covered by eval-3 and the PowerShell detector tests/smoke check; safety wording added in iteration 2 after a near-miss |
| 6 | Description trigger-accuracy checked with a dedicated eval set | **Deferred — not blocking** | Optional. Requires skill-creator's description-optimization loop (`scripts/run_loop.py`), which depends on the Claude Code CLI (`claude -p`) — a dependency this project prefers to avoid. Not required for release or wide sharing. Revisit if skill triggering ever becomes a real problem |
| 7 | `CHANGELOG.md` reflects the version being released | **Applies — must confirm per release** | Manual — update before tagging |
| 8 | Packaged `.skill` produced and smoke-tested | **Applies — green** | `python3 scripts/package_skill.py`, then `unzip -l dist/quality-gates.skill` and confirm exactly 11 files, including the LLM assessment reference and adapter, with no stray artifacts |
| 9 | Reviewed by a human before distribution | **Applies — manual, always required** | Peer review can't be automated; this gate can never read as "always passes" |
| 10 | Security / secrets scan of the skill's own source | **No-op** | The skill contains no credentials or tokens. Its standard-library scripts only read the pointed-to filesystem and validate/serialize data; they do not make network calls, install tools, or execute target-project commands |
| 11 | Specification alignment: does the skill do what `quality-gates.md` says it should? | **Applies — green, re-check on every change to either file** | Manual comparison — `quality-gates.md` is the spec, `skill/quality-gates/` is the implementation |
| 12 | Agent Skill structure validation | **Applies — must confirm per release** | `npx --yes skills-ref validate skill/quality-gates` |

## Deferred (optional, not blocking)

- **#6 description trigger-accuracy**. The description in `SKILL.md`'s
  frontmatter has not been run through an adversarial eval set (near-miss
  queries that share keywords but need a different skill). Doing so requires
  skill-creator's description-optimization loop, which shells out to the
  Claude Code CLI. This project deliberately avoids that dependency, so the
  item is optional and never blocks a release. Revisit only if skill
  triggering proves unreliable in practice.

## Not yet built (roadmap, not a gate)

- A CI workflow (e.g. GitHub Actions) that runs `scripts/validate_skill.py` on
  every push. Straightforward to add once this repo is pushed to a remote —
  intentionally left out for now since there's no remote configured yet.
