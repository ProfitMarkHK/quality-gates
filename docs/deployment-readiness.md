# Deployment readiness for the quality-gates skill

This is the skill's release checklist. Each item is applies, no-op, gap, or
deferred. An applies item must pass before release. A no-op does not apply and
must include a reason. A gap should be addressed and tracked. A deferred item is
optional and never blocks release. Revisit it if conditions change. Use this
checklist before tagging a release or sharing the packaged `.skill` file.

| # | Check | State after iteration 4 | How |
|---|-------|-------------------------|-----|
| 1 | `SKILL.md` structural validation passes | **Applies. Green.** | `python3 scripts/validate_skill.py` |
| 2 | Detection script runs cleanly on representative project types | **Applies. Green.** | Evals cover Python, TypeScript, Bash, C, and PowerShell fixtures. Detector tests and a smoke check also pass. |
| 3 | Eval suite reaches 100% with-skill pass rate, with no regression | **Applies. Green.** | See eval results below. |
| 4 | Re-running on a gated repo does not duplicate the managed block | **Applies. Green.** | Covered by eval-4. |
| 5 | Policy check confirms no examples leak across languages | **Applies. Green.** | Covered by eval-3 and the PowerShell detector tests and smoke check. The safety note followed a near-miss in iteration 2. |
| 6 | Description trigger accuracy checked with a dedicated eval set | **Deferred. Not blocking.** | The optional skill-creator description optimization loop requires the Claude Code CLI. This project avoids that dependency. Revisit if skill triggering becomes unreliable. |
| 7 | `CHANGELOG.md` reflects the version being released | **Applies. Confirm per release.** | Update it before tagging. |
| 8 | Packaged `.skill` produced and smoke-tested | **Applies. Green.** | Run `python3 scripts/package_skill.py`, then inspect `unzip -l dist/quality-gates.skill`. Confirm exactly 14 files, including the LLM assessment reference, gateway execution seam, quarantine ADR-0003, and `.env.example`. Check for stray artifacts. |
| 9 | Human review completed before distribution | **Applies. Manual, always required.** | Peer review cannot be automated. Record the review before distribution. |
| 10 | Security and secrets scan of the skill source | **No-op.** | The skill contains no credentials or tokens. Its standard-library scripts read the pointed-to filesystem and validate or serialize data. They do not make network calls, install tools, or execute target-project commands. |
| 11 | Skill matches `quality-gates.md` | **Applies. Green. Re-check when either file changes.** | Compare the guidance with `skill/quality-gates/`. |
| 12 | Agent skill structure validation passes | **Applies. Confirm per release.** | `npx --yes skills-ref validate skill/quality-gates` |

## Eval results

- **Iteration 1, 2026-09-09.** With-skill runs passed 39/39 assertions. Baseline
  runs passed 20/39. OpenCode subagents ran the skill-creator harness. A Claude
  Code confirmation was pending because CLI authentication had expired. Adapter
  contract tests passed, 43/43. Results and a review page were saved under
  `quality-gates-workspace/iteration-1/`. The run did not record time or token
  data. Eval-0 did not check for out-of-scope rewrites. Evals 6 and 7 passed
  3/3 with and without the skill, so they did not distinguish the two runs.
  `claude -p` failed with expired OAuth. A later login was required.
- **Iteration 2, 2026-09-16, AIDEV-532.** Evals 0 through 4 passed 30/30
  assertions. Eval-7 passed 3/3. Live-model checks for evals 5 and 6 were
  blocked because no approved gateway was reachable. No model output was
  fabricated. Code checks covered two fail-closed validator rejections, the
  delimiter trust boundary, and non-blocking behavior when the assessment was
  unavailable.
- **Iteration 3, 2026-09-24, AIDEV-543.** Evals 0 through 7 passed 39/39
  assertions. Evals 5 through 7 ran against the live gateway. Eval-5 completed
  and flagged the unknown `muddle` builder with a source reference. Eval-6
  rejected the injected instruction, quarantined the output after two attempts,
  and failed closed with deterministic review unchanged. Eval-7 reported the
  assessment as unavailable and completed the deterministic review. Input
  packages before and after the AIDEV-543 fix matched across all four fixtures.
  The eval-0 runner failed on the fixture's real ruff error, as expected. The
  eval-2 runner passed. The eval-3 runner was checked with `make -n` because CMake
  was unavailable in the sandbox. Claude Code confirmation was still blocked at
  that time because `claude -p` hung without output.
- **Iteration 4, 2026-09-24.** A Claude Code run after `claude login` passed
  evals 0 through 4, 30/30 assertions. Eval-1 updated all four instruction-file
  conventions with exactly one marker pair each. Eval-3 preferred Clean when
  available, used an evidenced `clang-tidy` fallback, and checked the spec.
  Runners were tested where their tools were available. A grep found no
  cross-language example leakage. Evals 5 through 7 retain the live gateway
  results from iteration 3 because the later run did not change the executor.

## Deferred items

- **Description trigger accuracy.** The `SKILL.md` description has not been
  tested against adversarial near-miss prompts. Skill-creator's optimization
  loop requires the Claude Code CLI, which this project avoids. This check does
  not block release. Revisit it if skill triggering becomes unreliable.

## Roadmap

- Add a CI workflow to run `scripts/validate_skill.py` on every push after this
  repo has a remote. No remote is configured yet.
