# jsonparser — agent instructions

A tiny C library. Build with `make build`, test with `make test`.

<!-- BEGIN QUALITY GATES (managed) -->
## Definition of done — quality gates

No task is **done-done** (safe to merge, ship, or close) until every applicable
quality gate below passes. Gates catch regressions and omissions; they do not
replace design or review judgement.

Run all gates with one command before marking any unit of work complete:

```bash
make check
```

The full, project-specific checklist — every gate, its exact command, and the
gates that are no-ops or gaps for this project — lives in
[`docs/quality-gates.md`](docs/quality-gates.md). Keep it current: out-of-sync
documentation is treated as a bug.

Rules when a gate fails:

- Fix the code, not the gate. Do not weaken a test, silence a linter, or skip a
  doc update to force a green result.
- Fix all failures in the same session where practical, then re-run until every
  gate is green.
- Never commit or push secrets, even transiently.
<!-- END QUALITY GATES (managed) -->
