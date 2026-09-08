# Portrait with saved identity example

Create a local identity pack first:

```bash
gpt-image25-agent --root . --add-identity me \
  --ref refs/me-front.png \
  --ref refs/me-side.png
```

Plan an image with that identity:

```bash
gpt-image25-agent "cinematic portrait of me as a calm technical operator in a dark studio" \
  --identity me \
  --preset portrait \
  --preset likeness \
  --dry-run \
  --review-markdown
```

The identity refs are uploaded only in `--live` mode.
