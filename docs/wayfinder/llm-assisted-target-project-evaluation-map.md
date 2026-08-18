---
labels:
  - wayfinder:map
status: open
---

# LLM-assisted target-project evaluation

## Destination

An implementation-ready specification for a best-effort LLM assessment that
supplements the quality-gates skill's deterministic target-project review. It
adds advisory value for unrecognised or ambiguous languages, frameworks, and
tooling, while an unavailable LLM is recorded but never blocks the review.

## Notes

- The deterministic review remains the authoritative source of evidence and of
  applies, no-op, and gap decisions.
- The LLM assessment is advisory: it may identify technology and recommend
  human validation, but it cannot invent commands or change gate states.
- All target-project material may be supplied to the authorised secure LLM.
- Use `/grilling` and `/domain-modeling` when resolving human-in-the-loop
  tickets.
- The repository has no configured external tracker; these Markdown files are
  the local tracker and express dependencies through `blocked_by`.

## Decisions so far

<!-- Closed tickets are added here as links with a one-line gist. -->

## Not yet specified

- The operational deployment policy for a selected LLM provider, including
  model lifecycle and organisation-wide cost controls, may be relevant after
  the execution contract is chosen.

## Out of scope

- Implementing the specification in the quality-gates skill.
- Making an LLM assessment, its recommendations, or its availability a
  done-done gate.
- Replacing deterministic evidence detection or allowing LLM output to mutate
  gate states without human validation.
