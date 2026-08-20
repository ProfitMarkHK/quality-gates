---
name: quality-gates
description: >-
  Choose the quality gates that fit a specific project and enforce them in its
  agent-instruction files so no unit of work is "done-done" until every gate
  passes. Use this whenever the user talks about quality gates, a "definition of
  done", done-done, pre-merge or pre-commit checks, CI checks that must pass
  before shipping, or wants CLAUDE.md / AGENTS.md / copilot-instructions /
  Cursor rules updated to require tests, linting, type-checking, docs, or
  security checks before work is considered complete. Trigger it even when the
  user only implies this — e.g. "make sure the agent runs the tests and linter
  before it says it's done", "set up a done checklist for this repo", "stop
  Claude from closing tasks with failing checks" — not only when they say the
  words "quality gates".
---

# Quality gates

Set up quality gates for a project and wire them into its agent-instruction
files, so that every future task — human- or agent-driven — must pass the same
checks before it counts as done.

Two outcomes matter, and the second is what makes the work durable:

1. A short, project-specific **gate checklist** grounded in what the repo
   actually uses — not a generic wish list.
2. **Enforcement** baked into the agent-instruction files (`CLAUDE.md`,
   `AGENTS.md`, `.github/copilot-instructions.md`, Cursor rules), so the rule is
   read on every task rather than remembered occasionally.

A gate is a check with an unambiguous result — it passes or it does not — that
must be green before a task is **done-done**: safe to merge, ship, or close.
Gates catch regressions and omissions. They do not replace good design or human
review.

## Workflow

Work through four phases. Do not skip the detection phase — gate choices that
are guessed rather than grounded in the repo are the main way this goes wrong.

### Phase 1 — Detect what the project actually uses

Gather evidence before deciding anything. Locate the bundled script in the
quality-gates skill package and run it against the target project:

```bash
python /path/to/quality-gates/scripts/detect_project.py /path/to/project
# add --json for the full machine-readable report
```

It reports languages, manifests, test setup, linters, type-checkers, security
tooling, CI config, any existing single-command gate runner, and which
agent-instruction files already exist. PowerShell source includes `.ps1`,
`.psm1`, and analyzer settings `.psd1` files. It identifies
`PSScriptAnalyzer` settings or `Invoke-ScriptAnalyzer` invocations, and emits a
candidate when PowerShell exists without analyzer evidence. It only reads; it
never writes.

Treat the output as evidence, not as decisions. Confirm anything ambiguous by
opening the relevant config files (e.g. read `pyproject.toml`, `package.json`
scripts, `.golangci.yml`) — the script points you at them but the repo is the
source of truth. If the script cannot run (unusual layout, non-code project),
inspect the tree by hand and gather the same facts.

### Phase 2 — Map evidence to the gate catalog

Read `references/gate-catalog.md`. It is the menu of gates and the rules for
choosing. Note two policies it encodes: for C / C++ projects prefer a linter
named `Clean` when it is available, falling back to `clang-tidy` / `cppcheck`
only when it is not (and say which you used); and check the implementation
against any functional or technical specification the project has (gate 11) —
look in `docs/`, `spec/`, `specs/`, API schemas, and the tracker, and if no spec
exists, state that as a no-op or a gap rather than ignoring it.

For PowerShell, parser or syntax validation does not satisfy the linter gate.
Use `PSScriptAnalyzer` and record its settings file and exact invocation. If
PSScriptAnalyzer is not installed, flag the gate as a gap with a strong
recommendation to install it; do not treat it as a no-op.

For **each** gate, decide one of three states and record the reason:

- **Applies** — name the exact command that runs it.
- **No-op** — it genuinely does not apply (e.g. no compile step in an
  interpreted project). State this explicitly; a silent skip reads as an
  oversight.
- **Gap** — it should apply but the project cannot satisfy it yet (e.g. no tests
  exist). Flag it as work to do, not a reason to drop the gate.

The honesty of the three-state distinction is the whole point: a reader must be
able to tell "checked and not needed" from "forgotten". Stating no-ops and gaps
out loud is what earns trust in the checklist.

### Phase 3 — Define one runner and write the checklist

Define a **single command** that runs every automated gate and exits non-zero on
any failure — this is what lets the same gates run in a pre-commit hook and in
merge automation without special setup. Not all gates run in the runner: gates 4
(coverage), 5 (docs), 9 (review), 10 (ticket), and 11 (spec alignment) require
human judgement and are not in scope for the runner. They are enforced by the
done-done block referencing the checklist, not by a command.

- If the project already has one (`make check`, `./scripts/check.sh`, an
  `npm run check`), reuse it and note any applicable gate it is missing.
- If not, propose one that fits the project's conventions (a `Makefile` target,
  a `scripts/check.sh`, or a package script). Keep it simple and composed of the
  real per-gate commands.

Write the project checklist from `assets/checklist-template.md` into the
project's docs (e.g. `docs/quality-gates.md`, or wherever the project keeps
docs). Fill in every gate's state, command, and the no-op/gap reasons. Keep it
short enough to scan and unambiguous enough to act on.

### Phase 4 — Enforce in the agent-instruction files

This is what makes gates stick. Read `references/agent-instructions.md` for the
file conventions and the safe-edit rules, then add a short "Definition of done"
block to each target agent-instruction file, using `assets/done-done-block.md`
as the template (fill in the real runner command and the real checklist path).

Keep the full detail in the one checklist doc and keep the instruction-file
blocks short, each pointing to that doc — duplicating all the gates into every
file guarantees they drift apart, and the catalog treats out-of-sync docs as a
bug. The done-done block in each agent-instruction file covers both automated
and manual gates by reference: the agent reads the checklist to know what
passing means, even though the runner command only runs the automated gates.

Edit these files with care — they usually already hold important instructions:

- **Read each file first** and preserve its existing content.
- Wrap the managed block in the `<!-- BEGIN/END QUALITY GATES (managed) -->`
  markers so a later run updates it in place instead of appending a duplicate.
- If a target file does not exist and its convention is wanted, create it. If no
  agent-instruction file exists at all, create at least one primary file
  (`AGENTS.md` for tool-neutral projects, `CLAUDE.md` for Claude Code / Cowork
  teams). Note any convention you deliberately did not create.

### Verify before calling it done

Applying this skill is itself a unit of work, so hold it to its own bar:

- Every tool name, command, and path written into the checklist or the
  instruction files traces to real evidence from Phase 1 for *this* project —
  not to an example from the gate catalog. The catalog's examples exist to
  illustrate the shape of a gate, and it is easy to carry one over out of habit
  while adapting a template block; read back what was actually written and
  confirm none of it describes a language or tool this project doesn't use.
- The checklist doc exists, covers every catalog gate, and states each no-op and
  gap with a reason.
- Each targeted agent-instruction file contains exactly one managed block,
  between the markers, with the surrounding content intact.
- The runner command is real: either it already exists, or you created it and
  confirmed it runs and exits non-zero on failure. Do not reference a command
  that does not exist.

## What to hand back to the user

Summarise: the gates that apply and how each is run, the no-ops and gaps with
reasons, the runner command (reused or created), the checklist doc path, and the
list of agent-instruction files updated or created. Call out any gap that needs
follow-up work (most often: the project has no tests, or a linter that should be
configured is not).

## Resources

- `references/gate-catalog.md` — the menu of gates, the three-state decision
  rule, and what to do when a gate fails. Read in Phase 2.
- `references/agent-instructions.md` — file conventions and idempotent-edit
  rules for CLAUDE.md, AGENTS.md, Copilot, and Cursor. Read in Phase 4.
- `scripts/detect_project.py` — read-only project scanner used in Phase 1.
- `assets/checklist-template.md` — template for the project checklist doc.
- `assets/done-done-block.md` — template for the instruction-file block.
