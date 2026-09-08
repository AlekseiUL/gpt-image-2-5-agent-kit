# Migration to GPT Image 2.5

Version **0.2.0** changes the default image model to `gpt-image-2.5-sunburst` and adds a model selector. Existing scripts still use `gpt-image2-agent` and the `gpt_image2_agent` Python package. The repository/package name remains `gpt-image-2-agent-kit`, and the default output directory remains `generated/gpt-image-2/`.

## Choose a model explicitly

| Image model | Toolkit use |
| --- | --- |
| `gpt-image-2.5-sunburst` | Default for this reference/edit toolkit |
| `gpt-image-2.5-flare` | Alternative for everyday generation |
| `gpt-image-2` | Explicit legacy selection for existing workflows |

The choice of Sunburst as the toolkit default follows OpenAI's emphasis on editing precision in the [Sunburst model page](https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst). The [Flare model page](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare) describes its speed focus. This is the rationale for the default, not a benchmark performed by this repository.

```bash
# New default, with no network or token access
gpt-image2-agent "cinematic product hero" --dry-run --review-markdown

# Select Flare
gpt-image2-agent "cinematic product hero" \
  --image-model gpt-image-2.5-flare --dry-run --json

# Keep the previous model selection
gpt-image2-agent "cinematic product hero" \
  --image-model gpt-image-2 --quality high --dry-run --json
```

The image model is a separate field from the host model. `--host-model` remains configurable and defaults to `gpt-5.5`; selecting an image model does not change the host model.

## Image settings

The CLI keeps `--quality medium` as its default. Both 2.5 models accept `low`, `medium`, `high`, `xhigh`, `max`, and `auto`; the CLI rejects `xhigh` and `max` when `gpt-image-2` is selected. These 2.5 quality options are listed on the [Sunburst](https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst) and [Flare](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare) model pages.

`--size auto` delegates size selection to the backend. `--size WIDTHxHEIGHT` selects an explicit canvas and takes precedence over `--aspect`, including when an aspect flag is also supplied. Without `--size`, the existing square/portrait/landscape presets remain available. The receipt records `aspect: "custom"` for explicit dimensions and `aspect: "auto"` for automatic size.

The size validator follows the [official image-generation guide](https://developers.openai.com/api/docs/guides/image-generation): dimensions are multiples of 16, the longer edge is no more than three times the shorter edge, neither edge exceeds 3840, and the total is 655,360–8,294,400 pixels. The guide marks resolutions above `2560x1440` experimental.

`--background` accepts `opaque` (the toolkit default), `transparent`, or `auto`. Output remains PNG-only; the toolkit requests `output_format: "png"` and checks returned bytes before writing. For example:

```bash
gpt-image2-agent "isolated ceramic robot mascot" \
  --image-model gpt-image-2.5-sunburst \
  --size 1024x1024 --quality xhigh --background transparent \
  --dry-run --review-markdown
```

## References, edits and receipts

Existing identity and style packs can be reused. `--edit-image` places the base image first among the input images and sends `action: "edit"`. Other requests send `action: "auto"`. `--edit` without `--edit-image` is now rejected because edit instructions need a base image.

The backend payload omits `input_fidelity`. This migration does not infer support for that parameter on 2.5 models or promise exact preservation of identity, composition, or pixels. Describe the intended preservation in the prompt and inspect the result.

Receipts keep the `gpt-image2-agent.receipt.v1` schema name and add `background`, `output_format`, and `action` metadata. Older v1 receipts remain valid. Consumers should accept the new model IDs, quality values and `custom`/`auto` aspects. Markdown review shows the chosen image model and host model. See the [receipt documentation](receipt-schema.md).

## Live backend status

**No real live generation was performed to validate this migration.** Local planning and payload compatibility are distinct from account/backend availability.

The [official guide](https://developers.openai.com/api/docs/guides/image-generation) demonstrates the 2.5 models in the Image API and Responses API. This repository still uses its existing experimental ChatGPT/Codex backend, and this release does not implement either official API backend. The documentation does not establish that a subscription token can access these models through that route, or that a particular host model is enabled for an account.

A dry-run does not probe model access. Live use remains subject to compatible access, backend behavior, availability, rate limits and terms. There is no free or unlimited access claim. If a backend rejects a selected model or option, inspect the error and choose a supported configuration explicitly; the toolkit does not silently switch models.

Official sources above were checked on **2026-09-08**. Model availability and documentation can change.
