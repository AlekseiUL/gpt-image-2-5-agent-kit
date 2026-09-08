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
  "timestamp_utc": "2026-09-08T00:00:00+00:00",
  "status": "planned",
  "dry_run": true,
  "backend": "https://chatgpt.com/backend-api/codex",
  "host_model": "gpt-5.5",
  "image_model": "gpt-image-2.5-sunburst",
  "quality": "low",
  "aspect": "square",
  "size": "1024x1024",
  "background": "opaque",
  "output_format": "png",
  "action": "auto",
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

## GPT Image 2.5 fields

Version 0.2.0 keeps schema v1. New receipts include `background` (`opaque`, `transparent`, or `auto`), `output_format` (`png`) and `action` (`auto` or `edit`). These added fields are optional in the schema so older v1 receipts remain valid.

`image_model` records the selected image model; `host_model` records the separate host. For 2.5, `quality` can also be `xhigh` or `max`. When `--size` is supplied, `aspect` is `custom` for dimensions or `auto` for automatic size, and `size` records the supplied choice. An edit base produces `action: "edit"`; reference-only planning uses `auto`.

These fields describe the requested configuration. A planned receipt is not evidence that the selected models are accessible through the live backend. See the [migration notes](migration-gpt-image-2.5.md).

## Why receipts exist

Receipts let agents and humans answer:

- Which identity/style/reference pack was used?
- Was this dry-run or live?
- Which output path was selected?
- Which model/quality/aspect was requested?
- Can we reproduce or audit the run without saving secrets?
