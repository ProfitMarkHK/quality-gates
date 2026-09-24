---
parent: ../agentic-quality-gates-explainer-map.md
labels:
  - wayfinder:prototype
status: closed
assignee: barrygfox
blocked_by:
  - choose-markdown-deck-authoring.md
  - define-deck-learning-arc.md
  - define-security-tooling-roadmap-message.md
---

# Prototype the deck information architecture

## Question

Which slide structure, diagrams, and sample project journey make the
evidence-to-feedback loop clear at a glance, while separating the current
quality-gates skill from the proposed security-tooling roadmap?

## Resolution

The team selected **Variant A, Evidence rail**. The final deck uses a linear,
self-guided sequence where each slide adds evidence to the initial agent
completion claim:

1. Claim
2. Risk
3. Done-done contract
4. Project structure
5. Skill process
6. Gate groups
7. Fictional service walkthrough
8. Current scope and next action

The prototype is preserved on the `prototype/deck-information-architecture`
branch at commit `69adae3`. It contains all three rejected or selected variants
in `docs/wayfinder/deck/prototype-information-architecture.html`; open it with
`?variant=A`, `?variant=B`, or `?variant=C`.

The prototype is not part of the main branch. The final deck must use
ASD-STE100 English.
