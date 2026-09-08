# Capability reference

The toolkit validates local requests and constructs an image-generation tool call for an experimental ChatGPT/Codex backend. The table describes **exposed options and local checks**, not a guarantee that every option is enabled on your account. The official OpenAI API is not implemented as a backend here.

## Models and output controls

| Control | Local behavior |
| --- | --- |
| Image models | Only `gpt-image-2.5-sunburst` and `gpt-image-2.5-flare`; Sunburst is the default. Earlier/unknown model IDs are rejected. |
| Host model | Separate `--host-model` value; defaults to `gpt-5.5`. |
| Quality | `low`, `medium`, `high`, `xhigh`, `max`, `auto`; default `medium`. |
| Aspect presets | `square`: requests `1024x1024`; `landscape`: `1536x1024`; `portrait`: `1024x1536`. |
| Explicit size | `--size auto` or `WIDTHxHEIGHT`; overrides `--aspect`. |
| Custom dimensions | Positive multiples of 16; neither edge above 3840; long/short ratio at most 3; 655,360–8,294,400 pixels total. |
| Background | `opaque`, `transparent`, `auto`; default `opaque`. Explicit transparency is rejected with JPEG. |
| Output format | `png`, `jpeg`, `webp`; default `png`. The output extension must match the selected format. |
| Compression | Integer 0–100, JPEG/WebP only. Omit for PNG. This is a backend encoding option, separate from model quality. |
| Action | `auto`, `generate`, `edit`. An edit requires `--edit-image`; an edit base cannot be combined with `generate`. |
| Timeout | Positive finite `--timeout`, in seconds. |
| Output count | One output image per live invocation; run once per requested asset for a series. |

Sunburst's editing focus and Flare's everyday-generation focus come from the [Sunburst model page](https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst) and [Flare model page](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare). These sources also list the six quality settings.

The [official image-generation guide](https://developers.openai.com/api/docs/guides/image-generation) documents custom dimensions, PNG/JPEG/WebP, compression and transparency. It marks resolutions above `2560x1440` experimental. Requested dimensions are not independent evidence of actual dimensions; inspect the decoded output metadata before export.

## Inputs, roles and masks

| Input | Local behavior |
| --- | --- |
| Reference images | Up to five combined refs across edit base, saved identity/style packs and explicit refs. This is a toolkit limit, not a model-wide API limit. |
| Reference roles | Explicit refs accept `identity`, `style`, `logo`, `layout`, `general`; if roles are supplied, their count must match explicit refs. |
| Input order | Edit base first, then saved identity refs, saved style refs and explicit refs. Roles align with this order. |
| Preserve instructions | Repeat `--preserve` with an edit base; instructions become part of the prompt. |
| Mask | `--mask` requires an edit base and an alpha PNG with matching pixel dimensions and some transparency. A fully opaque or non-alpha mask is rejected. |
| Exact text | Prompt construction preserves literal requested copy. Conflicting `no-text`/`russian-text` presets are rejected, including inherited presets. |

For masks, use a PNG edit base and a PNG mask of the same dimensions, within the toolkit's input limits. Transparent mask pixels identify the region to change. OpenAI's guide states that a mask applies to the first image and is guidance rather than an exact boundary guarantee. [Official mask guidance](https://developers.openai.com/api/docs/guides/image-generation#edit-an-image-using-a-mask).

Roles describe how to use an input; they do not select models automatically, grant rights to reuse private images or guarantee identity preservation. The toolkit does not expose `input_fidelity` or a server-side conversation/`previous_response_id` workflow. Use a saved output as a new explicit edit base when an edit is wanted.

## Completion and evidence

The live client requires a successful completed response before accepting image output. It validates the full image by decoding it and checks the decoded format against the requested format. Partial stream data, failed terminal responses and corrupt output do not become successful files. Writes are atomic, with no-overwrite protection unless `--overwrite` is explicit. The client does not automatically retry or fall back to another image model.

Receipts distinguish requested configuration from decoded output metadata. An `image_model` field records the submitted selection; it does not attest which model the backend executed unless separate evidence establishes that. A successful call only demonstrates the exact combination used on that account at that time.

See [verification status](../README.md#verification-status) for recorded checks. Mask support, compression, transparency, formats, quality levels, sizes and model access each need their own evidence before being called live-verified. No claim is made that every official API option is accepted through the subscription backend.
