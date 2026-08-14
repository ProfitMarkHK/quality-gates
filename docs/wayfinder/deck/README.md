# Presentation workspace

This workspace keeps the explainer source separate from the quality-gates
skill. It uses the locally installed Pandoc to produce a PowerPoint file.

## Requirements

- Pandoc 3.10.2 or later

Verify the installed version:

```bash
pandoc --version
```

## Export the final deck

The final deck source is `agentic-quality-gates-explainer.md`.

```bash
mkdir -p dist
pandoc --from markdown --to pptx \
  --output dist/agentic-quality-gates-explainer.pptx \
  agentic-quality-gates-explainer.md
```

The included `example.md` verifies the toolchain. It is not part of the final
explainer.

Generated files in `dist/` are intentionally ignored. The Markdown source is
canonical. This workflow does not use remote presentation assets and does not
promise PDF output.
