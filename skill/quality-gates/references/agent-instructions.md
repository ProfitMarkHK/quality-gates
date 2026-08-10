# Enforcing gates in agent-instruction files

Agent-instruction files are the documents an AI coding agent reads before it
works in a repo. To make gates stick, the "definition of done" must live in
these files, so that every future task — human- or agent-driven — inherits the
same bar. This file explains where those files live, how to edit them safely,
and how to avoid drift.

## The files and their conventions

| Convention | Path(s) | Read by |
|---|---|---|
| Claude | `CLAUDE.md` (repo root; also nested per-directory) | Claude Code, Cowork |
| AGENTS.md | `AGENTS.md` (repo root; may be nested) | Cross-tool agent standard |
| Copilot | `.github/copilot-instructions.md` | GitHub Copilot |
| Cursor | `.cursor/rules/*.mdc` (newer) or `.cursorrules` (legacy) | Cursor |

Notes that save mistakes:

- **Cursor** moved from a single `.cursorrules` file to a `.cursor/rules/`
  directory of `.mdc` files. Each `.mdc` file starts with a YAML frontmatter
  block (`description`, `globs`, `alwaysApply`). For a rule that must apply to
  all work, set `alwaysApply: true`. If the repo already uses `.cursorrules`,
  respect that and append there rather than introducing the new format
  uncalled-for.
- **Copilot** expects its file at `.github/copilot-instructions.md`. Create the
  `.github/` directory if enforcement in Copilot is wanted and it is missing.
- `CLAUDE.md` and `AGENTS.md` are plain Markdown with no required frontmatter.

## Single source of truth — avoid drift

The full gate checklist (all applicable gates, no-ops, gaps, the runner command)
belongs in **one** project doc — for example `docs/quality-gates.md`, or
wherever the project keeps its docs. Each agent-instruction file then gets a
**short** "Definition of done" block that states the rule and points to that one
doc plus the runner command.

Duplicating the full checklist into four files guarantees they drift out of sync
— and the catalog itself treats out-of-sync documentation as a bug. Keep the
detail in one place; keep the instruction-file blocks short and consistent.

## Edit idempotently — never clobber, never duplicate

These files usually already contain important project instructions. Follow this
sequence for each target file:

1. **Read the file first.** Preserve everything already there.
2. **Look for an existing gate block** by its marker (below). If present,
   **replace its contents in place** — do not append a second copy.
3. **If absent, append** the block at the end (or under an existing
   "Development" / "Contributing" heading if one fits naturally).
4. **If the file does not exist** and this convention is wanted, create it with
   the block as its content.

Use HTML-comment markers so the block can be found and updated reliably on later
runs without disturbing surrounding text:

```markdown
<!-- BEGIN QUALITY GATES (managed) -->
...block content...
<!-- END QUALITY GATES (managed) -->
```

Re-running the skill should find the markers and update between them, leaving
the rest of the file untouched. This is what makes enforcement safe to apply
repeatedly.

## If no agent-instruction file exists

Create at least one primary file so the rule has a home. Prefer `AGENTS.md` for
tool-neutral projects, or `CLAUDE.md` when the team works in Claude Code / Cowork.
Do not scatter empty files for conventions the team does not use — create the
ones the user asked for, and note which conventions you did not create and why.

## Note on the specification-alignment gate

Gate 11 (implementation matches the functional and technical specs) is largely a
manual, judgement-based check, so it does not belong in the automated runner.
Record it in the checklist doc with the location of the spec it is checked
against, and let the done-done block cover it by reference — the block already
says a task is not done until *every applicable gate* passes, which includes the
manual ones.

## The block template

Use `assets/done-done-block.md` as the template. Fill the placeholders with the
project's real runner command and the real path to the checklist doc. Keep it
short: the block states the rule and delegates the detail to the checklist.
