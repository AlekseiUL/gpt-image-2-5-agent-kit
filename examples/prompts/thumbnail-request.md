# Thumbnail request example

Goal: plan a YouTube/Telegram thumbnail before spending live generation quota.

```bash
gpt-image2-agent "YouTube thumbnail: AI agent designer preparing a bold visual plan, no text" \
  --image-model gpt-image-2.5-flare \
  --preset thumbnail \
  --preset no-text \
  --size 1536x864 \
  --quality low \
  --dry-run \
  --review-markdown
```

Use `--live` only after reviewing the prompt, refs and output path.
