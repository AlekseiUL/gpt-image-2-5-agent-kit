# Edit background example

Plan an edit of an existing image:

```bash
gpt-image2-agent \
  --image-model gpt-image-2.5-sunburst \
  --edit-image generated/source.png \
  --edit "remove the background, keep the person, face, lighting and crop, add a clean dark studio backdrop" \
  --dry-run \
  --review-markdown
```

Edit mode puts the base image first, requests `action: "edit"`, and tells the backend what should stay unchanged. A base image is required for `--edit`.

For a transparent cutout instead of a replacement backdrop:

```bash
gpt-image2-agent \
  --edit-image generated/source.png \
  --edit "remove the background, keep the person, face, lighting and crop" \
  --background transparent --quality xhigh \
  --dry-run --review-markdown
```

Output is PNG. Real 2.5 live generation has not been validated for this migration.
