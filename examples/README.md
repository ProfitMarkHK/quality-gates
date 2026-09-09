# Eval output examples

Each directory is the end state of a fixture project after the quality-gates
skill ran on it — real output from behavioural eval iteration 1 (2026-09-09),
kept here so you can see what the skill produces without re-running the suite.

| Directory | Eval | Fixture | Score |
|---|---|---|---|
| `eval-0-python-existing-claude-md` | 0 | `py-service` | 6/6 |
| `eval-1-typescript-all-four-instruction-files` | 1 | `web-dashboard` | 7/7 |
| `eval-2-bash-no-tests-gap-and-noops` | 2 | `backup-scripts` | 6/6 |
| `eval-3-c-lang-clean-linter-and-spec-alignment` | 3 | `jsonparser` | 7/7 |
| `eval-4-idempotent-rerun-no-duplicate-fence` | 4 | `py-service` (skill applied twice) | 4/4 |
| `eval-5-llm-unknown-technology-advisory` | 5 | `py-service` + `frobnicator.toml` | 3/3 |
| `eval-6-llm-repository-injection-boundary` | 6 | `py-service` + `docs/REVIEW_NOTES.md` | 3/3 |
| `eval-7-llm-unavailable-is-non-blocking` | 7 | `py-service`, LLM unavailable | 3/3 |

Total: 39/39 with-skill (baseline without the skill scored 20/39).

What to look at in each directory: the generated checklist
(`docs/quality-gates.md`), the single runner (`scripts/check.sh` or a `make
check` target), and the managed definition-of-done block in the agent
instruction file (`CLAUDE.md` and/or `AGENTS.md`).

Sources of truth: prompts and expectations in
`skill/quality-gates/evals/evals.json`, fixtures in
`skill/quality-gates/evals/` (extract `fixtures.zip` there), procedure in
`docs/running-evals.md`. Full run data (both configurations, grades,
benchmark, review page) lives in `quality-gates-workspace/iteration-1/`,
which is intentionally untracked (local-only git exclude, not committed).
