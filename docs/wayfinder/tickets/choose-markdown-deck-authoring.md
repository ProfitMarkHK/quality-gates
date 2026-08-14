---
parent: ../agentic-quality-gates-explainer-map.md
labels:
  - wayfinder:grilling
status: closed
assignee: barrygfox
blocked_by: []
---

# Choose Markdown deck authoring and rendering

## Question

Which Markdown presentation workflow will create a shareable eight-slide deck
with the required systems-map visuals, accessible reading order, and a
repeatable preview or export path?

## Resolution

Use the existing Pandoc 3.10.2 installation to export the Markdown source to a
local PowerPoint file. The committed workspace is `docs/wayfinder/deck/`; it
contains source and workflow documentation only. Generated presentation files
remain ignored.

The initial Marp CLI option was rejected because its pinned current version
reported four high-severity dependency vulnerabilities. Pandoc's HTML
presentation output was also rejected because it loads remote presentation
assets. No local PDF engine is available. The local PowerPoint export works and
is the supported preview and distribution path.

The later information-architecture ticket owns the final slide source and any
custom presentation reference file.
