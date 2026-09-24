# quality-gates agent notes

This repo is the development home for the quality-gates skill (in
`skill/quality-gates/`) and the general guidance document it is built from
(`quality-gates.md`). See `README.md` for the full layout and workflow.

<!-- BEGIN QUALITY GATES (managed) -->
## Definition of done. Quality gates

This project uses its own skill on itself. No change here is done-done until:

1. **Structural validation passes.** `python3 scripts/validate_skill.py` exits
   0. Run this check for every change.
2. **Agent skill structure validation passes.** `npx --yes skills-ref validate
   skill/quality-gates` exits 0. This confirms the packaged skill directory and
   frontmatter agree.
3. **Behavioral changes are re-tested.** Changes to
   `skill/quality-gates/SKILL.md`, `references/`, `assets/`, or
   `scripts/detect_project.py` that could change the skill's behavior, not
   pure prose polish, must be tested against `evals/evals.json` in an agent
   session with the skill loaded. Run the evals both with and without the change
   before merging. This manual gate requires an agent session. A script cannot
   mark it complete. Record that it was done and include the result.
   See `docs/running-evals.md` for the procedure. Install skill-creator
   separately and extract `fixtures.zip` to `evals/` first.
4. **Docs stay in sync.** Add an entry to `CHANGELOG.md` for the change.
   `quality-gates.md` and `skill/quality-gates/references/gate-catalog.md`
   must describe the same gates. If one changes, check whether the other needs
   an update.
5. **No example leakage.** If the change touches a language-specific example,
   such as a tool name or file path, confirm it cannot appear in a project of a
   different language. The iteration-2 safety note addresses this issue. See
   `references/gate-catalog.md`.
6. **Packaging succeeds before a release.** `python3 scripts/package_skill.py`
   produces `dist/quality-gates.skill` without errors. Before tagging a release,
   not every commit, also clear every **applies** item and confirm any deferred
   or no-op items are stated in `docs/deployment-readiness.md`.

Fix the code, not the gate. If a check is inconvenient, fix the underlying
problem instead of removing the check. State no-ops, which are checks that do not
apply. Do not silently skip them. See `quality-gates.md` for why.
<!-- END QUALITY GATES (managed) -->
