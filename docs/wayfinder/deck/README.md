# Presentation workspace

This workspace keeps the explainer source separate from the quality-gates
skill. It uses the locally installed Pandoc to produce a PowerPoint file.

## Requirements

- Pandoc 3.10.2 or later

Verify the installed version:

```bash
pandoc --version
```

## Export a deck

The included `example.md` verifies the toolchain. It is not part of the final
explainer.

```bash
mkdir -p dist
pandoc --from markdown --to pptx --output dist/example.pptx example.md
```

The information-architecture ticket will add the final deck source. Export it
with the same command, replacing `example.md` and the output filename.

Generated files in `dist/` are intentionally ignored. The Markdown source is
canonical. This workflow does not use remote presentation assets and does not
promise PDF output.
