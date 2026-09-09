# GPT Image 2.5 Agent Kit

![GPT Image 2.5 Agent Kit: generated photography, illustration and typography](docs/assets/gpt-image-2-5-agent-kit-hero.png)

![CI](https://github.com/AlekseiUL/gpt-image-2-5-agent-kit/actions/workflows/repository-quality.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Status](https://img.shields.io/badge/status-public_preview-orange.svg)

A local toolkit for agents and operators working with **GPT Image 2.5 Sunburst and Flare**. Build a prompt, assign reference roles, inspect a dry-run, generate or edit an image, and keep a receipt of the request and resulting file.

**Unofficial community toolkit. Not affiliated with, endorsed by, or sponsored by OpenAI.** Version **0.3.1** uses the `gpt-image25-agent` command and `gpt_image25_agent` Python package. Earlier image models are excluded from execution.

Live calls use an experimental ChatGPT/Codex backend with your own compatible access. An official OpenAI API backend is **not implemented**. Model availability in the official API does not establish availability through this subscription route; access, limits and supported options may differ. This is not a hosted service or a source of free/unlimited access.

## Quick start

From the repository checkout:

```bash
python -m pip install -e .
gpt-image25-agent --help
```

The default is a local dry-run: no token access, network call or generated image. Add `--receipt` only if you want to save the plan.

```bash
gpt-image25-agent "cinematic product hero, one clear subject, no text" \
  --image-model gpt-image-2.5-sunburst \
  --size 1536x864 --quality high \
  --dry-run --review-markdown
```

Use `--json` instead of `--review-markdown` for an agent-readable plan. Review the final prompt, image/host models, reference roles, options and output path before a live call.

## Features and options

| Feature | CLI / behavior |
| --- | --- |
| Image model | `--image-model gpt-image-2.5-sunburst` (default) or `gpt-image-2.5-flare`; no legacy model fallback |
| Quality | `--quality low\|medium\|high\|xhigh\|max\|auto`; default `medium` |
| Canvas | `--aspect square\|portrait\|landscape`, or `--size auto\|WIDTHxHEIGHT` to override the aspect preset |
| Background | `--background opaque\|transparent\|auto`; default `opaque`; transparency requires PNG or WebP |
| Output format | `--output-format png\|jpeg\|webp`; default `png`; choose a matching output extension |
| Compression | `--output-compression 0..100` for JPEG/WebP only |
| References | Repeat `--ref`; label explicit inputs with `--ref-role identity\|style\|logo\|layout\|general` |
| Saved packs | `--identity NAME` and `--style NAME` reuse local reference collections |
| Edits | `--edit-image BASE --edit "change"`; repeat `--preserve "invariant"` |
| Mask | `--mask MASK.png` with an edit base; alpha PNG, matching dimensions, transparent pixels indicate the edit region |
| Action | `--action auto\|generate\|edit`; edits need a base, and a base cannot be combined with `generate` |
| Receipts | Optional JSON recording requested settings, reference hashes and actual output metadata |
| Host model | `--host-model`; default `gpt-5.5`, separate from the image model |

Sunburst is the default for this reference/edit toolkit. OpenAI positions [Sunburst for precise editing](https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst) and [Flare for fast everyday generation](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare).

The toolkit applies conservative local bounds to custom dimensions: multiples of 16, an aspect ratio between 1:3 and 3:1, edges up to 3840 pixels, and 655,360–8,294,400 pixels total. These bounds are a compatibility policy inherited from documented earlier-model constraints, **not** proof that GPT Image 2.5 or the experimental subscription backend accepts every matching size. Requested dimensions and decoded output dimensions are recorded separately; inspect the returned file before using it in an exact-size layout.

The [capability reference](docs/capabilities.md) separates exposed options, local validation and backend support. A flag appearing in the CLI is not a claim that every account/provider accepts it.

## Copyable workflows

Fast draft with Flare, saved as JPEG if run live:

```bash
gpt-image25-agent "minimal landscape illustration of a coastal town" \
  --image-model gpt-image-2.5-flare --quality low \
  --output-format jpeg --output-compression 85 \
  --out generated/coast.jpg --dry-run --json
```

Transparent asset:

```bash
gpt-image25-agent "isolated ceramic robot mascot" \
  --background transparent --output-format webp --quality xhigh \
  --out generated/mascot.webp --dry-run --review-markdown
```

Reference roles — use your own local files under the selected `--root`:

```bash
gpt-image25-agent "portrait using the first image for identity and the second for lighting only" \
  --ref refs/person.png --ref-role identity \
  --ref refs/style-board.png --ref-role style \
  --preset likeness --quality high --dry-run --review-markdown
```

Edit a specific region while describing what must stay:

```bash
gpt-image25-agent \
  --edit-image generated/source.png --mask refs/sign-mask.png \
  --edit 'Replace the sign text with exactly "ЧАСТЬ 4"' \
  --preserve "person, camera angle and lighting" \
  --preserve "all text outside the sign" \
  --quality high --out generated/sign-edit.png \
  --dry-run --review-markdown
```

The mask must contain transparency and match the base image's pixel dimensions. Masks and preserve instructions guide the edit; they do not guarantee unchanged pixels outside the region. See [reference, identity, style and edit workflows](docs/identity-style-edit-workflows.md).

## Presets and exact text

Available presets: `portrait`, `likeness`, `thumbnail`, `product`, `no-text`, `russian-text`, `edit`, `brand-style`.

Presets add guidance to the actual request. Requested logos, lettering, sketches and deliberate crops are allowed. Quote literal in-image text and describe its placement and typography; `russian-text` preserves supplied Cyrillic, punctuation, case and line breaks. It does not authorize translation or shortening. `no-text` and `russian-text` cannot be combined, including through a saved style.

For multiline or quoted prompts, use `--prompt-file`; see the [Cyrillic example](examples/prompts/russian-text-cover.md). Visually inspect generated spelling, likeness and layout before publishing.

## Saved identities and styles

```bash
gpt-image25-agent --root . --add-identity me \
  --ref refs/me-front.png --ref refs/me-side.png

gpt-image25-agent "cinematic portrait of me in a studio" \
  --identity me --preset likeness --dry-run --json

gpt-image25-agent --root . --add-style graphite-brand \
  --style-prompt "graphite palette, warm highlights, restrained visual density" \
  --style-preset brand-style --ref refs/style-board.png
```

Use `--style graphite-brand` in later requests or `--list-library` to inspect saved packs. The `.gpt-image2-agent` storage directory and `gpt-image2-agent.*.v1` schema identifiers are retained for saved-data compatibility; they do not enable an older image model.

## Live generation

Provide your own compatible token through `env`, an explicit `file`, or a trusted local `command` provider. The default environment variable is `CHATGPT_CODEX_ACCESS_TOKEN`.

```bash
export CHATGPT_CODEX_ACCESS_TOKEN="...your token..."
gpt-image25-agent "clean product hero, no text" \
  --live --auth-provider env --quality high \
  --out generated/hero.png --receipt generated/hero.receipt.json
```

Live mode uploads the final prompt, selected references and any mask. References and final output are fully decoded before acceptance. The toolkit requests no partial previews, waits for a successful completed response and writes the validated final file atomically. Partial streams and corrupt files are not successful results. Existing outputs require `--overwrite`; the default also protects against a file appearing during the request. There is no automatic retry or switch to another image model. Each live invocation produces one image; for an authorized series, run one attempt per requested asset rather than retrying or silently restarting the batch. If `--receipt` is supplied, a live auth/backend failure writes a sanitized `error` receipt without raw error details or tokens.

## Verification status

**0.3.1 offline hardening verified on 2026-09-09:** 271 offline tests pass, including full reference decoding, authenticated-client wiring, zero partial previews and schema-valid error-receipt persistence. The 0.3.0 real Sunburst generation and Flare reference-based edit evidence remains valid for that exact release and option set; no additional paid request was made for 0.3.1. See the [0.3.0 release evidence and images](docs/release-validation-0.3.0.md).

The live checks used opaque PNG, high/medium quality and a requested `1536x864` canvas; both returned `1672x941`. Masks, transparent output, JPEG/WebP, compression and other quality/size combinations have offline validation and payload tests, but were not exercised against the live backend in this release.

Live tests are opt-in and are not part of normal CI. The backend remains experimental even after a successful smoke test.

## File and privacy boundaries

Outputs default to `generated/gpt-image-2.5/`. Output, prompt, reference, mask and receipt paths are bounded by `--root`, with explicit overrides where supported. Symlink escapes are blocked. Receipts omit raw prompts by default and never contain tokens or image bytes; use `--include-prompt-in-receipt` only when you want the prompt stored.

Read the [security model](docs/security-model.md), [receipt fields](docs/receipt-schema.md), [schemas](docs/schemas.md), [migration notes](docs/migration-gpt-image-2.5.md) and [changelog](CHANGELOG.md).

## Development

```bash
python -m pip install -e '.[test]'
python -m pytest
python -m gpt_image25_agent --help
```

## По-русски

Версия **0.3.1** — набор для GPT Image 2.5 с командой `gpt-image25-agent`. По умолчанию Sunburst; Flare выбирается явно. Старые модели удалены из рабочего маршрута. Референсы полностью декодируются до отправки, неиспользуемые partial previews отключены, а запрошенный receipt фиксирует и live-сбой без секретов.

Есть dry-run, роли референсов, сохранённые identity/style packs, точный текст, правки с `--preserve` и маской, PNG/JPEG/WebP, прозрачный фон и отчёты. Сначала проверьте план:

```bash
gpt-image25-agent 'Обложка про AI-агентов. Точный заголовок: "АГЕНТЫ БЕЗ ХАОСА"' \
  --preset russian-text --quality high --size 1536x864 \
  --dry-run --review-markdown
```

`--live` включает реальный запрос и расход вашего доступного лимита. ChatGPT/Codex backend остаётся экспериментальным; официальный API не реализован. Фактически проверенные параметры перечисляются в разделе Verification status выше. Примеры и подробности перехода — в [migration notes](docs/migration-gpt-image-2.5.md).

## Canonical source and attribution

Maintained by Aleksei Ulianov / Sprut_AI. Canonical repository: [gpt-image-2-5-agent-kit](https://github.com/AlekseiUL/gpt-image-2-5-agent-kit). Retain the original copyright/license notice when reusing the project and link back to the canonical source.

[YouTube](https://youtube.com/@alekseiulianov) · [Sprut AI channel](https://t.me/Sprut_AI) · [Sprut AI chat](https://t.me/+eH-qNIDmud8zNDZi) · [AI Операционка](https://t.me/tribute/app?startapp=sJyg)
