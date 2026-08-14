---
labels:
  - wayfinder:map
status: open
---

# Agentic quality gates explainer

## Destination

An eight-slide Markdown deck for the internal development team. It explains why
agentic development needs a codified definition of done, how this
quality-gates project works, what its skill reports, and where its current
scope ends.

## Notes

- Audience: developers who are new to agentic development.
- Primary action: run the quality-gates skill on the next project.
- Visual register: systems map. Use evidence, flows, and explicit states.
- The deck must distinguish verified current behaviour from the future
  security-tool installation roadmap.
- Use `/grilling` and `/domain-modeling` when resolving human-in-the-loop
  tickets.

## Decisions so far

<!-- Closed tickets are added here as links with a one-line gist. -->

- [Verify the quality-gates skill's deck claims](tickets/verify-quality-gates-deck-claims.md) —
  The skill detects repository evidence, records each gate as applies, no-op,
  or gap, writes the checklist and managed instruction blocks, and does not
  install or prove local availability of security tools.
## Not yet specified

- The final visual language, diagram treatment, and accessibility details
  depend on the information architecture and deck authoring decision.
- Speaker notes and distribution needs will be revisited once the deck format
  is chosen.

## Out of scope

- Changing the quality-gates skill while preparing the explainer.
- Implementing automatic installation of security tools.
- General agentic-development training beyond the definition of done and this
  skill's workflow.
