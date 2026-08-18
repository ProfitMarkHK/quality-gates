---
slide-level: 1
---

# When an agent says "done"

**A claim of "we're done" requires evidence and a common understanding of "Done".**

An agent can change many files quickly and significantly change the shape of a project while executing a unit of work. The developers need a clear answer:
can we merge, ship, or close this work?

| Agent claim | Evidence | Team decision |
|---|---|---|
| "The task is done." | Checks, records, and review | Done-done |

**Definition of done:** the checks that must pass before work is done-done.

# Agentic development introduces change

Agents increase delivery speed and extend the scope of what we can build. They can also miss a check,
introduce an unsuitable tool/package, or report success without proof (agents lie).

> Fast output is great but we need proof that what's been produced is "good".

A codified definition of done gives every task the same finish line. It makes
the result of the work clear to people and agents.

The quality gates skill provides a list of conditions we want to pass for each unit of work. Passing is the definition of "done".

# Doneis an _executable_ contract

Each quality gate has one of the following states.

| State | Meaning | Required action |
|---|---|---|
| **Applies** | The project needs this gate. | Run the named check. |
| **No-op** | The gate does not apply. | State the reason. |
| **Gap** | The gate should apply but cannot pass yet. | Plan and complete the missing work. |

This prevents a silent skip from looking like a successful check.

# How the quality-gates project is structured

| Part | Purpose |
|---|---|
| `quality-gates.md` | General guidance and the gate model |
| `skill/quality-gates/SKILL.md` | The skill workflow |
| `skill/quality-gates/scripts/detect_project.py` | Read-only project evidence scan |
| `skill/quality-gates/references/gate-catalog.md` | The eleven-gate decision catalog |
| `skill/quality-gates/assets/` | Checklist and instruction-block templates |
| Target project instruction files | The rule that future agents read |

The project keeps the full checklist in one place. Short instruction blocks
point to it. (This helps prevent rule drift).

# How the skill turns project contents into a set of checks

| Step | Output |
|---|---|
| Detect | Facts about the repository and its tooling |
| Map | An `applies`, `no-op`, or `gap` state for every gate |
| Document | A project-specific checklist |
| "Enforce" | Managed definition-of-done blocks in agent instructions |
| Verify | An explicit runner, real paths, and real commands |
| Report | Gates, no-ops, gaps, and follow-up work |

The skill reviews the project and then chooses checks that are appropriate for that project.

# The eleven gates combine to provide provable end status for a unit of work

| Correctness and delivery | Engineering health | Safety and accountability |
|---|---|---|
| Tests pass | Lint and static analysis pass | Security and secrets checks pass |
| Acceptance tests pass | Documentation is current | Change review is complete |
| New code has useful tests | Type checking passes | Tracker matches project reality |
| Build succeeds |  |  |
| Implementation matches specifications |  |  |

Not every gate applies to every project. Every gate still gets a recorded, visible state.

# Example Output

## Quality gates - ms-graph-path-resolver

The single source of truth for what **done-done** means in this project. Any
team member should be able to run these checks and know the answer. Keep this
file in sync with the tooling. Out-of-date quality documentation is a bug.

### Run everything

```bash
bash scripts/check.sh
```

This command runs every automated gate and exits non-zero on any failure. It
can also be used in pre-commit hooks and merge automation.

### Gates

| # | Gate | State | Command / note |
|---|------|-------|----------------|
| 1 | All tests pass | applies | `node --test resolver.test.js`, run by `bash scripts/check.sh` |
| 2 | End-to-end / acceptance tests pass | gap | The CLI has a live SharePoint and Microsoft Graph surface, but no automated acceptance suite exists. Manual verification against a real URL is still required as described in `README.md`. |
| 3 | Linters / formatters / static analysis pass | no-op | No linter, formatter, or static analyser is configured. The runner uses `node --check` for syntax validation only. |
| 4 | New code covered by non-trivial tests | applies | Manual review of changed code and tests; meaningful parser and error-path behaviour must have assertions in `resolver.test.js` or a new test file. |
| 5 | Documentation updated | applies | Manual review of `README.md`, `PRODUCT.md`, and relevant agent instructions for documentable changes. |
| 6 | Type checking passes | no-op | The implementation is untyped CommonJS JavaScript. The unused `typescript` devDependency does not define a type-check step. |
| 7 | Build / compile succeeds | no-op | The project is a plain Node.js CLI with no build or compile step. |
| 8 | Security / secrets checks pass | gap | `npm audit --omit=dev --audit-level=high` checks runtime dependencies. No automated secrets scanner is configured, so source and token-handling review remains manual. |
| 9 | Change reviewed | applies | Manual peer review is required before merge or release. |
| 10 | Tracker / ticket reconciled | applies | For linked GitLab work, use `glab issue view <number> --comments` and update the issue to match the delivered change. |
| 11 | Implementation aligns with functional & technical specifications | applies | Manual review against `README.md` and `PRODUCT.md`; no separate formal API or technical specification was detected. |

State legend: **applies** (must pass), **no-op** (does not apply - reason
given), **gap** (should apply but is not yet fully possible - track the
follow-up in a GitLab issue).

### No-ops and gaps

Track each gap below as a GitLab issue, following
`docs/agents/issue-tracker.md`.

- Gate 2 is a gap because no automated end-to-end or acceptance test suite
  exists for the live SharePoint and Graph integration.
- Gate 3 is a no-op because no linter, formatter, or static analyser is
  configured.
- Gate 6 is a no-op because the implementation is untyped CommonJS JavaScript.
- Gate 7 is a no-op because the project has no build or compile step.
- Gate 8 is a gap because dependency auditing exists but automated secrets
  scanning does not.

### When a gate fails

Fix the code, not the gate. Diagnose the failure, fix all failures in the same
session where practical, and re-run until every gate is green. Never weaken a
check to force a pass.

The gap is explicit (and actionable by the developer). It is not a false green result potentially hiding issues.

# What the skill does now, and what comes next

| Now | Next: roadmap |
|---|---|
| Detect repository evidence | Propose a project-appropriate security tool and setup |
| Record applies, no-ops, and gaps | Project owner approves the change |
| Write the checklist and instruction blocks | An agent can then bootstrap installation or configuration |
| Block done-done when a required gap remains | A refused approval leaves the gap visible |

The bootstrap path is not current skill behaviour.

**Next action:** try the quality-gates skill on your next project. Review every
applies, no-op, and gap state and decide if the active checks really do define done-done.
