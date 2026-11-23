# quality-gates

Development home for the quality-gates skill. It runs under any coding agent.
Given a software project, it selects suitable quality gates and enforces them in
the project's agent-instruction files (`AGENTS.md`, `CLAUDE.md`,
`.github/copilot-instructions.md`, Cursor rules), so no unit of work counts as
done until every applicable gate passes.

This repo also holds `quality-gates.md`, the general guidance document the
skill is built from. The two evolve together. If you change what "done" means
in principle, update `quality-gates.md`. If you change how the skill acts on
that, update `skill/quality-gates/`.

## Layout

```
quality-gates.md              the general guidance doc. It explains the purpose and lists the gates
CLAUDE.md                     this repo's own definition of done (we use the skill on itself)
docs/
  deployment-readiness.md     the checklist a release of the skill must clear before shipping
skill/quality-gates/          the packageable skill. This directory contains the .skill contents
  SKILL.md
  references/                 gate-catalog.md, agent-instructions.md, llm-assessment.md. Loaded by the agent when the skill runs
  assets/                     done-done-block.md, checklist-template.md. Templates the skill fills in
  scripts/detect_project.py   read-only project scanner the skill runs first
  scripts/llm_assessment_contract.py  secure-LLM input serializer and result validator
  evals/                      test prompts + fixture projects (not shipped in the packaged .skill)
    evals.json                 the test prompts and their pass/fail assertions
    fixtures.zip                the sample projects each prompt runs against (unzip to evals/)
scripts/                      standalone tooling for this repo (no agent session required)
  validate_skill.py           structural check: frontmatter, size, that Resources links resolve
  package_skill.py            zips skill/quality-gates/ into dist/quality-gates.skill
  run_evals_opencode.py       runs the behavioural eval suite via the OpenCode CLI (see docs/running-evals.md)
dist/                         packaging output (gitignored)
```

## Continuing development

Development on this skill follows the same loop each time:

1. **Change** something in `skill/quality-gates/`. That may be the gate catalog,
   detection script, agent-instruction templates, or `SKILL.md` itself.
2. **Test it** by running the skill against realistic prompts. This needs an
   agent session with the skill loaded. Ask the agent to complete a task and
   inspect what it produces. Plain assertions cannot tell you whether an agent
   wrote a useful checklist. See `docs/running-evals.md` for the full procedure:
   extracting fixtures, confirming skill-creator is available, running the
   prompts, and reviewing the comparison output.
3. **Review** what came back. skill-creator can generate a comparison page
   showing exactly what files each run created or changed, plus a pass-rate
   benchmark. Read the actual output files, not just the summary. That is
   where problems show up, such as a gate catalog example leaking into a
   project that does not use that language.

   > **Note.** The empty `eval-0` through `eval-4` folders at the repo root are
   > optional working directories from past eval runs. They are not required
   > output destinations. The eval output lives in skill-creator's session
   > working directory.
4. **Fix, re-test, repeat** until satisfied, then update `CHANGELOG.md` and
   run through `docs/deployment-readiness.md` before packaging a release.

## Validating and packaging without an agent session

The two scripts under `scripts/` are plain Python (standard library only) so
they work in any shell, including CI:

```bash
python3 -m unittest discover -s tests  # detector regression tests
python3 scripts/validate_skill.py          # structural validation
python3 scripts/package_skill.py           # writes dist/quality-gates.skill
```

These are a lighter, self-contained version of the checks an agent session
would run via the skill-creator skill's own `quick_validate.py` and
`package_skill.py`. They catch structural mistakes such as bad frontmatter or a
Resources link to a file that does not exist. They cannot tell you whether the
skill instructions are useful. For that, run step 2 above.

On GitHub, the same structural checks run automatically on every push and
pull request via `.github/workflows/validate.yml`. The behavioural eval
suite never runs in CI: it needs an agent session (evals 0-4) and, for
evals 5-7, gateway credentials that must never enter CI.

## This repo's own definition of done

See `CLAUDE.md` for this repo's definition of done. A change is complete when
`scripts/validate_skill.py` passes, behavioral changes have passed the eval
suite, and `docs/deployment-readiness.md` is current.
