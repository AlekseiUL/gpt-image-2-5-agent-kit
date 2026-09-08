# Schemas

Machine-readable JSON Schemas live in `schemas/`:

- `schemas/receipt.v1.schema.json`
- `schemas/identity.v1.schema.json`
- `schemas/style.v1.schema.json`

They document the stable local artifacts used by the toolkit.

## Receipt

Schema value:

```json
"gpt-image2-agent.receipt.v1"
```

Receipts are audit records for dry-run/live planning and generation. By default they store a prompt hash, not the raw prompt.

The 0.2.0 migration retains receipt v1 and expands image-model/quality/size metadata. New receipts include `background`, `output_format` and `action`; these fields remain optional for older receipts. See [receipt fields](receipt-schema.md) and the [migration notes](migration-gpt-image-2.5.md).

## Identity manifest

Schema value:

```json
"gpt-image2-agent.identity.v1"
```

Identity manifests live under `.gpt-image2-agent/identities/<name>/identity.json` and point to copied local reference images.

## Style manifest

Schema value:

```json
"gpt-image2-agent.style.v1"
```

Style manifests live under `.gpt-image2-agent/styles/<name>/style.json` and can store a style prompt, presets and optional style references.
