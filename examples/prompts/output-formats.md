# Output formats and compression

JPEG plan:

```bash
gpt-image25-agent "minimal coastal landscape illustration" \
  --image-model gpt-image-2.5-flare --quality low \
  --output-format jpeg --output-compression 85 \
  --out generated/coast.jpg --dry-run --json
```

Transparent WebP plan:

```bash
gpt-image25-agent "isolated ceramic robot mascot" \
  --background transparent --output-format webp --output-compression 90 \
  --out generated/mascot.webp --dry-run --json
```

PNG is the default; omit `--output-compression` for PNG. Compression accepts an integer from 0 to 100 for JPEG/WebP and is distinct from `--quality`. Explicit transparent backgrounds are incompatible with JPEG. The output extension must match the selected format.
