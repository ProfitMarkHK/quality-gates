# Deployment readiness — quality-gates skill

This is the quality-gates skill's own checklist, in the same vocabulary it
teaches: every item is **applies** (must be green before release), **no-op**
(genuinely not relevant to a skill, stated so it isn't mistaken for an
oversight), or **gap** (should be done, isn't yet — tracked as work, not
quietly dropped). Run through this before tagging a release or widely sharing
the packaged `.skill` file.

| # | Check | State (as of iteration 2) | How |
|---|-------|------|-----|
| 1 | `SKILL.md` structural validation passes | **Applies — green** | `python3 scripts/validate_skill.py` |
| 2 | Detection script runs cleanly on representative project types | **Applies — green** | Exercised by evals against Python, TypeScript, Bash, and C fixtures |
| 3 | Eval suite: 100% with-skill pass rate, no regression vs. previous iteration | **Applies — green** | 19/19 (evals 0–2) + 7/7 (eval 3) + 4/4 (eval 4) as of iteration 2; re-run via skill-creator before each release |
| 4 | Idempotency: re-running on an already-gated repo doesn't duplicate the managed block | **Applies — green** | Covered by eval-4 |
| 5 | Policy correctness spot-checked (no example leakage across languages) | **Applies — green** | Covered by eval-3; safety wording added in iteration 2 after a near-miss |
| 6 | Description trigger-accuracy checked with a dedicated eval set | **Gap** | Not yet run. Do this via skill-creator's description-optimization loop (`scripts/run_loop.py`) before wide release — the current description has not been adversarially tested against near-miss queries |
| 7 | `CHANGELOG.md` reflects the version being released | **Applies — must confirm per release** | Manual — update before tagging |
| 8 | Packaged `.skill` produced and smoke-tested | **Applies — green** | `python3 scripts/package_skill.py`, then `unzip -l dist/quality-gates.skill` and confirm exactly 6 files, no stray artifacts |
| 9 | Reviewed by a human before distribution | **Applies — manual, always required** | Peer review can't be automated; this gate can never read as "always passes" |
| 10 | Security / secrets scan of the skill's own source | **No-op** | The skill contains no credentials, tokens, or executable payloads beyond `detect_project.py`, which only reads the filesystem it's pointed at |
| 11 | Specification alignment: does the skill do what `quality-gates.md` says it should? | **Applies — green, re-check on every change to either file** | Manual comparison — `quality-gates.md` is the spec, `skill/quality-gates/` is the implementation |

## Known gaps

- **#6 description trigger-accuracy** is the one open gap. The description in
  `SKILL.md`'s frontmatter has not been run through an adversarial eval set
  (near-miss queries that share keywords but need a different skill). Do this
  before the skill is shared widely — a skill that doesn't trigger reliably is
  no better than no skill.

## Not yet built (roadmap, not a gate)

- A CI workflow (e.g. GitHub Actions) that runs `scripts/validate_skill.py` on
  every push. Straightforward to add once this repo is pushed to a remote —
  intentionally left out for now since there's no remote configured yet.
