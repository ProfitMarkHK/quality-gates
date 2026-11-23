# Running the eval suite

This guide helps an agent (or human) run the quality-gates behavioural eval
suite without guessing. It covers setup, execution, and output interpretation.

---

## What the evals test

The evals are **behavioural** tests. They verify that the quality-gates skill
produces the right files with the right content, not that the skill parses or
packages cleanly. Structural checks are separate. See
`docs/deployment-readiness.md` items 1 and 8.

The eval suite contains eight scenarios. Evals 0 through 4 use project fixtures.
Evals 5 through 7 test the optional LLM assessment.

| ID | Name | What it tests |
|----|------|---------------|
| 0 | `python-existing-claude-md` | Updates an existing `CLAUDE.md` without destroying its content |
| 1 | `typescript-all-four-instruction-files` | Wires gates into all four agent-instruction file types |
| 2 | `bash-no-tests-gap-and-noops` | Identifies missing tests as a gap, not a no-op |
| 3 | `c-lang-clean-linter-and-spec-alignment` | Prefers Clean over clang-tidy for C; checks spec alignment |
| 4 | `idempotent-rerun-no-duplicate-fence` | Running the skill twice produces one block, not two |
| 5 | `llm-unknown-technology-advisory` | Reports unknown technology with a source-backed advisory |
| 6 | `llm-repository-injection-boundary` | Treats instruction-like repository text as untrusted data |
| 7 | `llm-unavailable-is-non-blocking` | Completes deterministic review when LLM assessment is unavailable |

---

## Prerequisites

### skill-creator

The evals are run through the **skill-creator** skill. It feeds
prompts to an agent, captures the output, and compares it against the
expectations in `evals.json`.

skill-creator is **not bundled with quality-gates**. It must be installed
separately.

1. Check whether skill-creator is available in your agent environment.
2. If it is not available, install it from the gfox-skills marketplace or from
   its source repository.
3. Confirm it is active before proceeding.

### Fixtures

Each eval targets a fixture project. The fixtures are in:

```
skill/quality-gates/evals/fixtures.zip
```

They must be extracted before the evals can run. The extraction target is
`skill/quality-gates/evals/` (the zip holds the fixture folders at its top
level, with no wrapper directory):

```bash
cd /path/to/quality-gates
unzip -o skill/quality-gates/evals/fixtures.zip -d skill/quality-gates/evals/
```

After extraction, verify these directories exist:

```
skill/quality-gates/evals/py-service/
skill/quality-gates/evals/web-dashboard/
skill/quality-gates/evals/backup-scripts/
skill/quality-gates/evals/jsonparser/
```

> Note. The empty `eval-0` through `eval-4` folders at the repo root are
> optional working directories from past runs. They are not required and can be
> ignored or removed. The canonical eval output lives inside
> `skill-creator`'s own session working directory.

---

## Running the evals

### Step 1. Open an agent session in this repo

The evals require an interactive agent session with the skill loaded. Structural checks
(`validate_skill.py`, `package_skill.py`) do not need this. Behavioural checks
do.

### Step 2. Activate the quality-gates skill

Load the skill so the agent has access to the gate catalog, the detection
script, and the templates.

### Step 3. Ask the agent to use skill-creator

Prompt the agent to use skill-creator to run the prompts in `evals.json`. The
exact prompt is not prescribed. For example:

```
Use the skill-creator skill to run the evals in
skill/quality-gates/evals/evals.json against the quality-gates skill
(skill/quality-gates/). Run each eval both with and without the skill and
show me a comparison of the output.
```

### Step 4. Review the results

skill-creator can generate a comparison page showing:

- Which files each run created or changed
- A pass-rate benchmark against the expectations in `evals.json`

Read the actual output files, not just the summary. A gate catalog example can
leak into a project that does not use that gate.

### Step 5. Record the result

After running, add the pass counts and any limitations to the eval results
section of `docs/deployment-readiness.md`:

```
Iteration N result: eval-0 (X/Y) + eval-1 (X/Y) + eval-2 (X/Y) + eval-3 (X/Y) + eval-4 (X/Y) = Z/Z = pass%
```

---

## Running evals from scratch (no skill-creator available)

If skill-creator is not available, the evals can be run manually in a limited
fashion:

1. For each fixture directory, apply the prompt from `evals.json` manually.
2. Inspect the output by hand against the `expectations` array in `evals.json`.
3. Report pass or fail for each expectation.

This approach does not produce a pass-rate summary, but it is sufficient to
validate the skill's behaviour before packaging or sharing.

## Running via the OpenCode CLI (local, no skill-creator)

`scripts/run_evals_opencode.py` runs both suites with OpenCode as the model
provider. It needs only the `opencode` CLI (any configured model, chosen
with `--model`) and local `git`:

```bash
# Fixture evals 0-4: blind headless sessions apply the skill to fresh
# fixture copies; transcripts and modified trees are saved for scoring.
python3 scripts/run_evals_opencode.py --suite fixtures

# Same, compared against a baseline ref (with/without a change):
python3 scripts/run_evals_opencode.py --suite fixtures --baseline-ref HEAD

# Live assessment evals 5-7: the real seam against a built-in local
# OpenAI-compatible shim serving the chosen OpenCode model.
python3 scripts/run_evals_opencode.py --suite live --model opencode/big-pickle
```

Eval-5's unfamiliar-tool fixture and eval-6's injection document are
planted automatically; eval-7 points the seam at a dead endpoint and must
record the assessment as non-blocking. Scoring stays human: the runner
writes an `INDEX.md` listing every run's output dir, assessment status, and
the eval's expectations; read the output dirs and score them. No LLM judge,
per repo policy.

Verified 2026-11-23 against `opencode/big-pickle`: eval-5 completed with
the planted tool flagged and source-referenced; eval-6 failed closed with
the injection reported as untrusted material rather than followed; eval-7
recorded `unavailable` with the deterministic review intact; a
fixtures-suite smoke (eval-2) passed 6/6 with no leakage.

---

## Common failure modes

### Evals appear to pass but CLAUDE.md content was overwritten

Eval 0 and eval 4 specifically assert that pre-existing `CLAUDE.md` content is
preserved. Read the output file directly and check for this. Do not rely on
the skill's summary output alone.

### Gate catalog example leaked into a project of the wrong language

Eval 3 explicitly checks that the C linter policy (Clean preferred over
clang-tidy) does not appear in the Python fixture, and vice versa. This failure
mode is subtle and only visible by reading the actual produced files.

### Missing fixture files

If `skill/quality-gates/evals/` is empty or missing subdirectories, the
fixtures have not been extracted. Re-run the unzip command above.

### skill-creator unavailable

Without skill-creator, behavioural evals cannot be run in an automated fashion.
Use the manual fallback in the section above, or install skill-creator first.

---

## Relationship to deployment readiness

Running the evals is **not part of every commit cycle**. It is required when:

- A behavioural change was made to the skill (new gate, changed template,
  changed detection logic)
- A release is being prepared
- Peer review is being requested

Structural checks (`scripts/validate_skill.py`) are faster and should be run on
every commit. The evals are the slower, more thorough check that deployment
readiness item 3 governs.
