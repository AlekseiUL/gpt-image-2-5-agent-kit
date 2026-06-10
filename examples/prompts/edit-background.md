# Edit background example

Plan an edit of an existing image:

```bash
gpt-image2-agent \
  --edit-image generated/source.png \
  --edit "remove the background, keep the person, face, lighting and crop, add a clean dark studio backdrop" \
  --dry-run \
  --review-markdown
```

Edit mode treats the base image as a reference and tells the backend what should stay unchanged.
