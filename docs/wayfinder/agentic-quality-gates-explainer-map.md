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
- [Choose Markdown deck authoring and rendering](tickets/choose-markdown-deck-authoring.md) —
  Use the installed Pandoc to export Markdown source to a local PowerPoint
  file. Do not add a Node dependency, remote presentation assets, or generated
  output to the repository.
- [Define the deck learning arc](tickets/define-deck-learning-arc.md) —
  Lead a self-guided audience from an agent's unsupported completion claim to
  visible evidence, then a fictional, language-neutral project walkthrough and
  the next action.
- [Define the security-tooling roadmap message](tickets/define-security-tooling-roadmap-message.md) —
  Show current detection and gap reporting beside a future, project-owner
  approved bootstrap path; never present the latter as current behaviour.
## Not yet specified

## Out of scope

- Changing the quality-gates skill while preparing the explainer.
- Implementing automatic installation of security tools.
- General agentic-development training beyond the definition of done and this
  skill's workflow.
