# quality-gates — agent notes

This repo is the development home for the **quality-gates** Claude skill (in
`skill/quality-gates/`) and the general guidance document it's built from
(`quality-gates.md`). See `README.md` for the full layout and workflow.

<!-- BEGIN QUALITY GATES (managed) -->
## Definition of done — quality gates

This project uses its own skill on itself. No change here is done-done until:

1. **Structural validation passes.** `python3 scripts/validate_skill.py` exits
   0. This is automated and has no excuse to be skipped.
2. **Behavioural changes are re-tested.** Any change to
   `skill/quality-gates/SKILL.md`, `references/`, `assets/`, or
   `scripts/detect_project.py` that could change what the skill *does* (not
   pure prose polish) must be re-run against `evals/evals.json` in a Claude
   Code / Cowork session before merging — with and without the change, so a
   regression is visible. This gate is manual by nature (it needs a real
   Claude session to execute), so it can never be waved through by a script;
   say explicitly that it was done and what the result was.
3. **Docs stay in sync.** `CHANGELOG.md` gets an entry for the change.
   `quality-gates.md` and `skill/quality-gates/references/gate-catalog.md`
   describe the same gates — if one changes, check whether the other needs to.
4. **No example leakage.** If the change touches a language-specific example
   (a tool name, a file path), confirm it can't bleed into a project of a
   different language. This is the exact mistake the iteration-2 safety note
   exists to prevent — see `references/gate-catalog.md`.
5. **Packaging succeeds before any release.** `python3 scripts/package_skill.py`
   produces `dist/quality-gates.skill` without errors. Before *tagging* a
   release (not every commit), also clear every item in
   `docs/deployment-readiness.md`.

Fix the code, not the gate — if a check is inconvenient, that's a signal to fix
the underlying thing, not to remove the check. No-ops (checks that don't apply)
must be stated, not silently skipped — see `quality-gates.md` for why.
<!-- END QUALITY GATES (managed) -->
