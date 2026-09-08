# Receipt schema

Machine-readable schema: [`schemas/receipt.v1.schema.json`](../schemas/receipt.v1.schema.json). Receipts record a requested operation and, after success, metadata about the resulting file.

The schema ID remains `gpt-image2-agent.receipt.v1` for saved-data compatibility. This identifier is not a model selector. Older receipts remain historical records; execution in 0.3.0 allows only Sunburst and Flare.

## Privacy

By default, receipts contain a SHA-256 of the final prompt, not the raw final prompt. `--include-prompt-in-receipt` includes the full prompt explicitly. Paths, selected pack names and other request metadata may still be sensitive.

References and masks are described by metadata such as paths, hashes and byte counts. Receipts never store image bytes or credentials. Treat receipts as local audit records and review their metadata before sharing them.

## Planned receipt example

The following is an illustrative plan, with a placeholder hash:

```json
{
  "schema": "gpt-image2-agent.receipt.v1",
  "timestamp_utc": "2026-09-09T00:00:00+00:00",
  "status": "planned",
  "dry_run": true,
  "backend": "https://chatgpt.com/backend-api/codex",
  "host_model": "gpt-5.5",
  "image_model": "gpt-image-2.5-sunburst",
  "quality": "high",
  "aspect": "custom",
  "size": "1536x864",
  "background": "opaque",
  "output_format": "png",
  "action": "auto",
  "output_path": "generated/gpt-image-2.5/example.png",
  "prompt_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "refs": [],
  "identity": null,
  "style": null,
  "edit_image": null
}
```

## Requested settings versus actual output

| Metadata | Meaning |
| --- | --- |
| `image_model`, `host_model` | Model selections submitted to the backend; not independent backend attestation. |
| `quality`, `size`, `background`, `output_format` | Requested image settings. Actual dimensions may differ. |
| `aspect` | Aspect preset, or `custom`/`auto` when explicit size selection is used. |
| `action` | Requested `auto`, `generate` or `edit` behavior. |
| References and roles | Which input files were used and what each was intended to contribute. |
| Mask metadata | The selected edit mask without embedding its bytes. |
| `actual_output` | Present after success: decoded width, height, format and color mode, plus file byte count and SHA-256. |

Optional metadata includes compression, reference roles and edit/mask details as available. The newer fields extend schema v1 without making historical receipts require metadata they could not have recorded. Check the JSON Schema for field-level definitions.

A `planned` receipt means local validation succeeded; it does not prove model access or backend support. A live success requires a completed response and a validated output file. Compare the requested settings with `actual_output`, and inspect the image itself for content, spelling and preservation requirements. See [capabilities](capabilities.md).
