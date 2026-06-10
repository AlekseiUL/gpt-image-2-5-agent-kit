# Receipt schema

Machine-readable schema: `schemas/receipt.v1.schema.json`. Identity/style schemas are listed in `docs/schemas.md`.

Receipts are the audit trail for agent-generated images.

A receipt is JSON with this schema name:

```json
"gpt-image2-agent.receipt.v1"
```

## Default privacy behavior

By default, receipts include a SHA-256 hash of the final prompt, not the raw prompt text.

Raw prompt text is stored only when `--include-prompt-in-receipt` is passed.

Reference images are recorded as paths, hashes, sizes and suffixes. Raw image bytes are never stored in the receipt.

## Example

```json
{
  "schema": "gpt-image2-agent.receipt.v1",
  "timestamp_utc": "2026-06-10T00:00:00+00:00",
  "status": "planned",
  "dry_run": true,
  "backend": "https://chatgpt.com/backend-api/codex",
  "host_model": "gpt-5.5",
  "image_model": "gpt-image-2",
  "quality": "low",
  "aspect": "square",
  "size": "1024x1024",
  "output_path": "generated/gpt-image-2/example.png",
  "prompt_sha256": "...",
  "refs": [
    {
      "path": ".gpt-image2-agent/identities/alex/ref-01.png",
      "sha256": "...",
      "bytes": 123456,
      "suffix": ".png"
    }
  ],
  "identity": "alex",
  "style": "graphite-brand",
  "edit_image": null
}
```

## Why receipts exist

Receipts let agents and humans answer:

- Which identity/style/reference pack was used?
- Was this dry-run or live?
- Which output path was selected?
- Which model/quality/aspect was requested?
- Can we reproduce or audit the run without saving secrets?
