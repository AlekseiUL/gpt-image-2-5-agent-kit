# Schemas

The toolkit uses these JSON Schemas for local saved artifacts:

- [`receipt.v1.schema.json`](../schemas/receipt.v1.schema.json)
- [`identity.v1.schema.json`](../schemas/identity.v1.schema.json)
- [`style.v1.schema.json`](../schemas/style.v1.schema.json)

Version 0.3.0 retains the `gpt-image2-agent.*.v1` IDs and `.gpt-image2-agent` storage directory for saved-data compatibility. Those names do not enable an earlier model. Historical receipt values describe past requests; the current CLI's model allowlist controls new execution.

## Receipts

Schema ID: `gpt-image2-agent.receipt.v1`.

Receipts describe dry-run/live requests, normally using a hash of the final prompt. New optional metadata covers output settings, reference roles, masks and decoded output details while retaining historical receipt compatibility. Requested configuration and actual output are separate. See [receipt fields](receipt-schema.md).

## Identity manifests

Schema ID: `gpt-image2-agent.identity.v1`.

Manifests live under `.gpt-image2-agent/identities/<name>/identity.json` and point to copied local references. They may contain sensitive identity data; a saved pack is not permission for unrelated use.

## Style manifests

Schema ID: `gpt-image2-agent.style.v1`.

Manifests live under `.gpt-image2-agent/styles/<name>/style.json`. They can store style instructions, presets and optional references. A style's inherited presets remain subject to the current validation rules, including incompatible text/no-text modes.
