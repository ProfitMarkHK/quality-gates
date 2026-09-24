<!-- BEGIN QUALITY GATES (managed) -->
## Definition of done. Quality gates

No task is **done-done** (safe to merge, ship, or close) until every applicable
quality gate below passes. Gates catch regressions and omissions. They do not
replace design or review judgement.

Run all gates with one command before marking any unit of work complete:

```bash
{{RUNNER_COMMAND}}
```

The full, project-specific checklist lives in
[`{{CHECKLIST_PATH}}`]({{CHECKLIST_PATH}}). It names every gate, its exact command,
and the gates that are no-ops or gaps for this project. Keep it current.
Out-of-sync documentation is a bug.

Rules when a gate fails:

- Fix the code, not the gate. Do not weaken a test, silence a linter, or skip a
  doc update to force a green result.
- Fix all failures in the same session where practical, then re-run until every
  gate is green.
- Never commit or push secrets, even transiently.
<!-- END QUALITY GATES (managed) -->
