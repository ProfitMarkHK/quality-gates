---
slide-level: 1
---

# When an agent says "done"

**A completion claim is not yet evidence.**

An agent can change many files quickly. The team still needs a clear answer:
can we merge, ship, or close this work?

| Agent claim | Evidence | Team decision |
|---|---|---|
| "The task is done." | Checks, records, and review | Done-done |

**Definition of done:** the checks that must pass before work is done-done.

# Agentic development changes the bar

Agents increase delivery speed and change scope. They can also miss a check,
copy an unsuitable tool, or report success before the project proves it.

> Fast output is not proof.

A codified definition of done gives every task the same finish line. It makes
the result clear to people and agents.

# Done-done is an executable contract

Each quality gate has one visible state.

| State | Meaning | Required action |
|---|---|---|
| **Applies** | The project needs this gate. | Run the named check. |
| **No-op** | The gate does not apply. | State the reason. |
| **Gap** | The gate should apply but cannot pass yet. | Plan and complete the missing work. |

This prevents a silent skip from looking like a successful check.

# How this project is structured

| Part | Purpose |
|---|---|
| `quality-gates.md` | General guidance and the gate model |
| `skill/quality-gates/SKILL.md` | The skill workflow |
| `scripts/detect_project.py` | Read-only project evidence scan |
| `references/gate-catalog.md` | The eleven-gate decision catalog |
| `assets/` | Checklist and instruction-block templates |
| Agent instruction files | The rule that future agents read |

The project keeps the full checklist in one place. Short instruction blocks
point to it. This prevents rule drift.

# How the skill turns evidence into action

| Step | Output |
|---|---|
| Detect | Facts about the repository and its tooling |
| Map | An applies, no-op, or gap state for every gate |
| Document | One project-specific checklist |
| Enforce | Managed definition-of-done blocks in agent instructions |
| Verify | A real runner, real paths, and real commands |
| Report | Gates, no-ops, gaps, and follow-up work |

The skill uses project evidence. It does not copy tools from an example.

# The eleven gates work as one system

| Correctness and delivery | Engineering health | Safety and accountability |
|---|---|---|
| Tests pass | Lint and static analysis pass | Security and secrets checks pass |
| Acceptance tests pass | Documentation is current | Change review is complete |
| New code has useful tests | Type checking passes | Tracker matches project reality |
| Build succeeds |  |  |
| Implementation matches specifications |  |  |

Not every gate applies to every project. Every gate still gets a visible state.

# A fictional service makes the result visible

The team runs the skill against a small service. The checklist shows the
result without naming a language or tool.

| Gate | State | What the team sees |
|---|---|---|
| Full test suite | **Applies** | Run the existing test command. |
| Build | **No-op** | This service has no compile step. |
| Security scan | **Gap** | A required check is missing. The task is not done. |
| Peer review | **Applies** | A reviewer must approve the change. |

The gap is work. It is not a false green result.

# What the skill does now, and what comes next

| Now | Next: roadmap |
|---|---|
| Detect repository evidence | Propose a project-appropriate security tool and setup |
| Record applies, no-ops, and gaps | Project owner approves the change |
| Write the checklist and instruction blocks | An agent can then bootstrap installation or configuration |
| Block done-done when a required gap remains | A refused approval leaves the gap visible |

The bootstrap path is not current skill behaviour.

**Next action:** run the quality-gates skill on the next project. Review every
applies, no-op, and gap state before you call the task done-done.
