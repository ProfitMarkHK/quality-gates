---
parent: ../agentic-quality-gates-explainer-map.md
labels:
  - wayfinder:grilling
status: closed
assignee: barrygfox
blocked_by:
  - verify-quality-gates-deck-claims.md
---

# Define the deck learning arc

## Question

What eight-slide narrative will move a developer from "an agent said it is
done" to "the project has evidence-based done-done gates," while accurately
covering project structure, the eleven gate types, one runner, instruction-file
enforcement, and visible no-ops and gaps?

## Resolution

The deck is self-guided and uses this eight-slide sequence:

1. **An agent says "done."** The claim has no visible evidence.
2. **Why agentic development changes the bar.** Higher delivery speed requires
   a shared, repeatable completion standard.
3. **Definition of done to done-done.** An executable contract replaces a
   memory aid.
4. **How this project is structured.** Guidance, skill, detector, catalog,
   templates, and enforced instruction blocks.
5. **How the skill works.** Detect, map, document, enforce, verify, and
   report.
6. **The gate system.** The eleven gates are grouped as correctness and delivery,
   engineering health, and safety and accountability.
7. **A fictional service walkthrough.** Show applies, no-op, and gap
   states without language-specific tools.
8. **What the skill does now.** State the current-scope boundary and the next
   action: run the skill on the next project.

The still-open security-roadmap ticket owns the final wording for slide 8's
boundary. Keep the fictional service language-neutral so its tools cannot be
mistaken for a template for every project.
