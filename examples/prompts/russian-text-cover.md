# Exact Cyrillic cover

Use the included prompt file to preserve quotes and line breaks:

```bash
gpt-image25-agent \
  --prompt-file examples/prompts/russian-title.txt \
  --image-model gpt-image-2.5-sunburst \
  --preset russian-text --preset thumbnail \
  --size 1536x864 --quality xhigh \
  --dry-run --review-markdown
```

Replace the title in the file with the exact requested copy. Do not combine `russian-text` with `no-text`, including through a saved style. Visually check every character, line break and placement before publishing an output; correct prompt construction does not guarantee correct rendered text.
