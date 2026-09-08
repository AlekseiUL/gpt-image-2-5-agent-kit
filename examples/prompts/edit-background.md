# Background edit

Use your own base image under the selected root:

```bash
gpt-image25-agent \
  --edit-image generated/source.png \
  --edit "Replace the background with a plain dark studio wall" \
  --preserve "person, face, clothing, lighting and crop" \
  --quality high --out generated/studio-edit.png \
  --dry-run --review-markdown
```

For a transparent cutout:

```bash
gpt-image25-agent \
  --edit-image generated/source.png --edit "Remove the background" \
  --preserve "person, face, clothing and lighting" \
  --background transparent --output-format webp --quality xhigh \
  --out generated/cutout.webp --dry-run --review-markdown
```

The base is the first input image and selects edit behavior by default. `--edit` and `--preserve` require a base. Transparent output requires PNG/WebP. Preserve instructions are guidance rather than a guarantee of unchanged pixels. Backend availability and optional-parameter support are described in [capabilities](../../docs/capabilities.md).
