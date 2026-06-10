# Thumbnail request example

Goal: plan a YouTube/Telegram thumbnail before spending live generation quota.

```bash
gpt-image2-agent "YouTube thumbnail: AI agent designer preparing a bold visual plan, no text" \
  --preset thumbnail \
  --preset no-text \
  --aspect landscape \
  --quality low \
  --dry-run \
  --review-markdown
```

Use `--live` only after reviewing the prompt, refs and output path.
