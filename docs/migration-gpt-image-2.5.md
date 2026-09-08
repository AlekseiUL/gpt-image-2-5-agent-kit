# Migration to GPT Image 2.5 Agent Kit 0.3.0

Version **0.3.0** makes this a GPT Image 2.5-only toolkit and renames the public package and command. Sunburst remains the default image model; Flare is the other supported choice. Earlier model IDs are rejected without a fallback call.

## Breaking name changes

| Before 0.3.0 | From 0.3.0 |
| --- | --- |
| Repository / distribution `gpt-image-2-agent-kit` | `gpt-image-2-5-agent-kit` |
| CLI `gpt-image2-agent` | `gpt-image25-agent` |
| Python import `gpt_image2_agent` | `gpt_image25_agent` |
| Default output `generated/gpt-image-2/` | `generated/gpt-image-2.5/` |

Canonical repository: [gpt-image-2-5-agent-kit](https://github.com/AlekseiUL/gpt-image-2-5-agent-kit). Update scripts, install instructions, import statements and any automation that relies on the default output directory. Use `--out` for a fixed path.

The `.gpt-image2-agent` library directory and `gpt-image2-agent.*.v1` schema IDs remain for saved-data compatibility. Existing packs and historical receipts do not need renaming, and their old-looking identifiers do not select an old model. Git history retains earlier versions as history, not as an active fallback procedure.

## Select a 2.5 model

```bash
gpt-image25-agent "cinematic product hero" \
  --image-model gpt-image-2.5-sunburst --quality high \
  --dry-run --review-markdown

gpt-image25-agent "minimal coastal illustration" \
  --image-model gpt-image-2.5-flare --quality low \
  --dry-run --json
```

Replace an explicit earlier model ID with one of these two choices. The image-model setting is separate from `--host-model`, which remains configurable and defaults to `gpt-5.5`. The quality default remains `medium`.

## New image controls

- Output can be `png`, `jpeg` or `webp` through `--output-format`; the default remains PNG. Choose a matching `--out` extension.
- `--output-compression` accepts an integer from 0 to 100 for JPEG/WebP; it is invalid for PNG.
- `--background transparent` requires PNG or WebP. Opaque remains the default.
- `--mask` requires a decoded alpha PNG matching the edit base dimensions, with a transparent edit region. Use a PNG base; the edit base is placed first.
- `--ref-role` labels explicit references; `--preserve` describes edit invariants. Both are visible in the planned prompt/metadata.
- `--action auto|generate|edit` makes the requested action explicit. An edit requires a base; generation cannot be combined with an edit base.

The 2.5 quality options `low`, `medium`, `high`, `xhigh`, `max`, `auto`, and `--size auto|WIDTHxHEIGHT` remain available. Explicit size overrides `--aspect`. Size validation follows the [official image-generation guide](https://developers.openai.com/api/docs/guides/image-generation); see [capabilities](capabilities.md) for limits and backend qualifications.

## Prompts and references

The prompt builder honors requested art medium, cropping, logos and text. It preserves literal Cyrillic without automatic shortening or translation. `no-text` and `russian-text` are mutually exclusive, including presets inherited from saved styles.

Reference order is edit base, saved identity references, saved style references, then explicit references. Index/role annotations follow that order. `--ref-role` applies only to explicit refs; saved packs receive automatic roles. `--edit`, `--preserve` and `--mask` require an edit base. Masks and preserve statements guide the model; they do not promise pixel-exact preservation. [Workflow examples](identity-style-edit-workflows.md).

## Completion and receipts

A live success now requires a successful completed response and a fully decodable image in the requested format. Interrupted streams, partial images, invalid image data and failed terminal responses are not accepted as successful output. Validated files are committed atomically, with protection against overwriting an existing or newly appeared file unless `--overwrite` is explicit. The CLI does not automatically retry or switch models.

Receipts retain schema v1. They distinguish **requested configuration** from **actual output** metadata such as dimensions, decoded format, byte count and SHA-256. The requested model comes from the submitted payload and is not independent backend model attestation. Older receipts remain historical records; consumers should handle newer optional fields. [Receipt fields](receipt-schema.md).

## Verification and backend status

The post-change verification record for 0.3.0 is [maintained in the README](../README.md#verification-status). Do not treat a dry-run, test fixture or one successful live option combination as proof that every optional parameter is available on every account.

This release continues to use the experimental ChatGPT/Codex backend. It does not implement the official Images API or Responses API backend. Official documentation describes those APIs; it does not establish equivalent support through this subscription route.

Official sources: [Sunburst](https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst), [Flare](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare), [image-generation guide](https://developers.openai.com/api/docs/guides/image-generation). Consulted for the September 2026 migration; current availability may change.
