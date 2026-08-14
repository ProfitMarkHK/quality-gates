---
parent: ../agentic-quality-gates-explainer-map.md
labels:
  - wayfinder:grilling
status: closed
assignee: barrygfox
blocked_by:
  - verify-quality-gates-deck-claims.md
---

# Define the security-tooling roadmap message

## Question

How should the deck show the difference between the current skill's
evidence-based security-tool detection and gap reporting, and a future option
to install or configure missing security tooling, without implying that the
future capability exists today?

## Resolution

Slide 8 uses a two-lane diagram.

**Now** shows the current skill inspecting repository evidence and recording
security coverage as applies, no-op, or gap. A required security gap remains
visible, is owned by the project owner, and blocks done-done until resolved or
explicitly accepted as an exception. A genuine no-op is stated as such.

**Next** shows an approval-based bootstrap path: the skill proposes a
project-appropriate tool and setup, the project owner approves it, and only
then can an agent install or configure it. If approval is withheld, the gap
remains visible.

The deck must not name a universal security tool or imply that the future
bootstrap capability exists now.
