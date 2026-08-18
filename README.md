# quality-gates

Development home for the **quality-gates** Claude skill: given a software
project, it selects the quality gates that fit and enforces them in that
project's agent-instruction files (`CLAUDE.md`, `AGENTS.md`,
`.github/copilot-instructions.md`, Cursor rules), so no unit of work counts as
done until every applicable gate passes.

This repo also holds `quality-gates.md`, the general guidance document the
skill is built from — the two evolve together. If you change what "done" means
in principle, update `quality-gates.md`; if you change how the skill acts on
that, update `skill/quality-gates/`.

## Layout

```
quality-gates.md              the general guidance doc — the "why" and the gate catalog in prose
CLAUDE.md                     this repo's own definition-of-done (see below — we use the skill on itself)
docs/
  deployment-readiness.md     the checklist a release of the skill must clear before shipping
skill/quality-gates/          the packageable skill — this directory *is* the .skill contents
  SKILL.md
  references/                 gate-catalog.md, agent-instructions.md, llm-assessment.md — loaded by Claude when the skill runs
  assets/                     done-done-block.md, checklist-template.md — templates the skill fills in
  scripts/detect_project.py   read-only project scanner the skill runs first
  scripts/llm_assessment_contract.py  secure-LLM input serializer and result validator
  evals/                      test prompts + fixture projects (not shipped in the packaged .skill)
    evals.json                 the test prompts and their pass/fail assertions
    fixtures.zip                the sample projects each prompt runs against (unzip to evals/files/)
scripts/                      standalone tooling for this repo (no Claude session required)
  validate_skill.py           structural check: frontmatter, size, that Resources links resolve
  package_skill.py            zips skill/quality-gates/ into dist/quality-gates.skill
dist/                         packaging output (gitignored)
```

## Continuing development

Development on this skill follows the same loop each time:

1. **Change** something in `skill/quality-gates/` — the gate catalog, the
   detection script, the agent-instruction templates, or `SKILL.md` itself.
2. **Test it** by running the skill against realistic prompts. This needs a
   Claude Code or Cowork session, because it works by actually asking
   Claude-with-the-skill to complete a task and checking what it produces —
   there's no way to unit-test "did Claude write a good checklist" with plain
   assertions alone. See `docs/running-evals.md` for the full step-by-step:
   extracting fixtures, confirming skill-creator is available, running the
   prompts, and reviewing the comparison output.
3. **Review** what came back. skill-creator can generate a comparison page
   showing exactly what files each run created or changed, plus a pass-rate
   benchmark. Read the actual output files, not just the summary — that's
   where subtle problems (like an example from the gate catalog leaking into a
   project that doesn't use that language) show up.

   > **Note:** The empty `eval-0` through `eval-4` folders at the repo root are
   > optional working directories from past eval runs. They are not required
   > output destinations. The canonical output lives in skill-creator's session
   > working directory.
4. **Fix, re-test, repeat** until satisfied, then update `CHANGELOG.md` and
   run through `docs/deployment-readiness.md` before packaging a release.

## Validating and packaging without a Claude session

The two scripts under `scripts/` are plain Python (standard library only) so
they work in any shell, including CI:

```bash
python3 -m unittest discover -s tests  # detector regression tests
python3 scripts/validate_skill.py          # structural check — exit 0 = pass
python3 scripts/package_skill.py           # writes dist/quality-gates.skill
```

These are a lighter, self-contained version of the checks a Claude session
would run via the skill-creator skill's own `quick_validate.py` /
`package_skill.py`. They catch structural mistakes (bad frontmatter, a
Resources link to a file that doesn't exist) but they cannot tell you whether
the skill's *instructions* are any good — for that you need step 2 above.

## This repo's own definition of done

See `CLAUDE.md`. This project practices what the skill preaches: no change here
is done until `scripts/validate_skill.py` passes, the eval suite has been
re-run for any behavioural change, and `docs/deployment-readiness.md` is
current.
