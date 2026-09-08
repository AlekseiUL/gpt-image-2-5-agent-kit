# Masked text edit

Prepare your own PNG base and an alpha PNG mask with matching dimensions. Make the sign region transparent in the mask and the surrounding area opaque; an opaque-only mask is invalid.

```bash
gpt-image25-agent \
  --edit-image generated/source.png --mask refs/sign-mask.png \
  --edit 'Replace the sign text with exactly "ЧАСТЬ 4"' \
  --preserve "person, camera, crop, palette and lighting" \
  --preserve "all text and objects outside the sign" \
  --quality high --output-format png --out generated/sign-edit.png \
  --dry-run --review-markdown
```

The mask targets the first image, which is the edit base. Inspect the changed area and preserved regions in the actual output; mask boundaries are guidance, not an exact pixel lock. This dry-run does not establish live mask support on your backend/account.
