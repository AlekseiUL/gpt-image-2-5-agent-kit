# GPT Image 2.5 Agent Kit

![CI](https://github.com/AlekseiUL/gpt-image-2-agent-kit/actions/workflows/repository-quality.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Status](https://img.shields.io/badge/status-public_preview-orange.svg)

![GPT Image 2 Agent Kit hero: artist sketching a GPT Image 2 agent workflow in a colorful studio](docs/assets/gpt-image-2-agent-kit-hero.jpg)

*Hero illustration retained from the previous GPT Image 2 version.*

A local-first toolkit for agents and operators planning GPT Image 2.5 generation and edits: better prompts, optional reference images, dry-run planning, receipts, and strict file boundaries. Version 0.2.0 defaults to `gpt-image-2.5-sunburst`, with Flare and legacy GPT Image 2 selectable.

**Unofficial community toolkit. Not affiliated with, endorsed by, or sponsored by OpenAI.**

Live generation through the existing ChatGPT/Codex backend is experimental and best-effort. It depends on your own compatible ChatGPT/Codex access, current product availability, rate limits, regional/account policy, and terms. The stable core of this repo is the local planning workflow: dry-run, references, identity/style/edit organization, receipts and path safety.

**The 2.5 migration has not been validated with a real live generation.** Official API documentation confirms the new image models; it does not establish their availability through this toolkit's subscription-backed route. This release does not implement an OpenAI API backend. See the [migration notes](docs/migration-gpt-image-2.5.md).

It is built from the lessons of an internal designer-agent workflow, but this public repo is sanitized: no private paths, no private facepack, no tokens, no internal agent names.

## Why this exists

Most image tools optimize for a human clicking a UI. This kit optimizes for an AI agent that must be safe before it spends quota or touches private references.

The flow is:

```text
request -> prompt plan -> identity/style/edit references -> dry-run -> receipt -> optional live generation
```

## Modes

- **Default / dry-run**: no token, no network, no image output. Prints a plan for agent/operator review.
- **Dry-run + receipt**: no token and no network; writes only the requested JSON receipt.
- **Review Markdown**: `--review-markdown` prints a human-readable plan with prompt, selected image/host models, refs, output path and risk notes.
- **Live**: `--live` reads your configured token, sends the prompt and selected refs to the backend, and writes a PNG.
- **Identity**: `--identity NAME` reuses a saved local person/character reference pack.
- **Style**: `--style NAME` reuses a saved local brand/style/moodboard pack.
- **Edit**: `--edit-image IMAGE --edit "..."` modifies an existing image while preserving requested parts.

## What it does

- Turns a short request into a stronger image-generation prompt with reusable presets.
- Supports optional reference images for likeness, style, logo, composition, edits, or product context.
- Creates saved local identity packs, so an agent can later use `--identity me` instead of asking for the same face references again.
- Creates saved local style packs for brandbooks, creator styles, art direction and campaign look.
- Supports edit mode: pass a base image and ask what to change while preserving the rest.
- Uses dry-run by default so agents can inspect the plan before spending quota.
- Writes outputs only inside a configured safe root unless you explicitly override it.
- Produces JSON receipts with hashes/metadata, not raw secrets or image bytes.
- Can attempt a ChatGPT/Codex image-generation request with the selected model if you provide your own compatible access token.

## What it is not

- Not a hosted image service.
- Not a quota bypass.
- Not “free unlimited GPT Image 2.5.”
- Not an official OpenAI Images API SDK.
- Not browser automation.
- Not a way to publish or share your subscription token.

Use wording carefully: this tool can use your existing compatible ChatGPT/Codex access where available. Product availability, model access, rate limits, and terms can change.

## Models and image options

| Option | Values / behavior |
| --- | --- |
| `--image-model` | `gpt-image-2.5-sunburst` (default), `gpt-image-2.5-flare`, `gpt-image-2` (legacy) |
| `--quality` | `low`, `medium` (default), `high`, `xhigh`, `max`, `auto`; `xhigh`/`max` require a 2.5 model |
| `--aspect` | Existing presets: `square`, `portrait`, `landscape` |
| `--size` | `auto` or `WIDTHxHEIGHT`; overrides `--aspect` |
| `--background` | `opaque` (default), `transparent`, `auto` |
| `--host-model` | Host model for the backend request; remains `gpt-5.5` by default |

Sunburst is the default because this kit focuses on references and editing. OpenAI positions [Sunburst for precise edits](https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst) and [Flare for faster everyday generation](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare). The image model and host model are separate settings.

Custom dimensions must be multiples of 16, with an aspect ratio from 1:3 to 3:1, edges at most 3840 pixels, and 655,360–8,294,400 pixels total. Resolutions above `2560x1440` are experimental in the [official image guide](https://developers.openai.com/api/docs/guides/image-generation). This kit requests and validates **PNG output only**, including transparent backgrounds.

The package name, repository URL, `gpt_image2_agent` import, `gpt-image2-agent` command and `generated/gpt-image-2/` output directory remain unchanged for compatibility.

## Quick start

```bash
python -m pip install -e .
gpt-image2-agent --help
```

Dry-run a prompt plan without auth, network, or file writes:

```bash
gpt-image2-agent "portrait of a calm technical operator" \
  --preset portrait \
  --aspect square \
  --quality low \
  --dry-run \
  --json
```

Human-readable review plan:

```bash
gpt-image2-agent "portrait of a calm technical operator" \
  --preset portrait \
  --aspect square \
  --quality low \
  --dry-run \
  --review-markdown
```

Use a reference image in the plan. This repository intentionally does not include real face references; replace the path with your own local image:

```bash
gpt-image2-agent "make a cinematic Telegram avatar in the same likeness" \
  --ref path/to/your-reference.png \
  --preset likeness \
  --dry-run
```

Plan a Flare image with an explicit canvas, or a transparent Sunburst asset:

```bash
gpt-image2-agent "wide product hero, no text" \
  --image-model gpt-image-2.5-flare \
  --size 1536x864 --quality high --dry-run --review-markdown

gpt-image2-agent "isolated ceramic robot mascot" \
  --image-model gpt-image-2.5-sunburst \
  --background transparent --quality xhigh --dry-run --json
```

Live generation is opt-in and depends on backend availability:

```bash
export CHATGPT_CODEX_ACCESS_TOKEN="...your token..."
gpt-image2-agent "clean product hero image, no text" \
  --live \
  --auth-provider env \
  --out generated/hero.png \
  --receipt generated/hero.receipt.json
```

## Reference-image workflow

Reference images are useful when the output should preserve:

- a person's likeness;
- a product shape;
- a brand style;
- a scene composition;
- a character or mascot.

Privacy note: in live mode, prompts and reference images are uploaded to the configured backend. Use `--dry-run` when you only want local planning.

## Presets

- `portrait` — clean portrait composition.
- `likeness` — stronger identity-preservation language for user-supplied references.
- `thumbnail` — high-contrast YouTube/Telegram visual, avoids tiny text.
- `product` — product/landing hero image.
- `no-text` — explicitly avoids generated text.
- `russian-text` — if text is needed, asks for short readable Cyrillic and clean typography.
- `edit` — preserve the base image while changing only the requested part.
- `brand-style` — follow a saved or supplied style system.

Presets are prompt additions, not magic. Check the final dry-run prompt before live generation.

## Saved identities, styles and edits

Create a saved identity from local references:

```bash
gpt-image2-agent --root . --add-identity me \
  --ref refs/me-front.png \
  --ref refs/me-side.png
```

Use it later:

```bash
gpt-image2-agent "make a cinematic image with me in a black technical studio" \
  --identity me \
  --preset likeness \
  --dry-run
```

Create and reuse a style pack:

```bash
gpt-image2-agent --root . --add-style graphite-brand \
  --style-prompt "dark graphite palette, clean premium lighting" \
  --style-preset brand-style \
  --ref refs/style-board.png

gpt-image2-agent "hero image for an AI automation course" \
  --style graphite-brand \
  --preset product \
  --dry-run
```

Edit an existing image:

```bash
gpt-image2-agent \
  --edit-image generated/source.png \
  --edit "remove the background, keep the person and lighting" \
  --background transparent \
  --dry-run
```

`--edit-image` puts the base image first and requests `action: "edit"`. `--edit` requires a base image. Reference-only generation uses `action: "auto"`; preservation instructions are not a guarantee of unchanged pixels.

More detail:

- [GPT Image 2.5 migration notes](docs/migration-gpt-image-2.5.md)
- `docs/identity-style-edit-workflows.md`
- `docs/comparison.md`
- `docs/security-model.md`
- `docs/receipt-schema.md`
- `docs/schemas.md`
- `examples/prompts/` for copyable dry-run workflows
- `schemas/` for machine-readable receipt/identity/style schemas

## Safety model

Default behavior is conservative:

- dry-run is available and safe;
- output defaults to `./generated/gpt-image-2/`;
- output, prompt-file, refs and receipts must stay under `--root` by default;
- symlink escapes are blocked;
- existing output files require `--overwrite`;
- receipts exclude raw prompt text by default unless `--include-prompt-in-receipt` is set;
- tokens are redacted from errors.

## Auth providers

Supported token providers:

- `env` — reads `CHATGPT_CODEX_ACCESS_TOKEN` or `--token-env`.
- `file` — reads an explicitly provided `--token-file`.
- `command` — runs `--token-command` and reads token from stdout.

The command provider is powerful. Use only trusted local commands.

## Development

```bash
python -m pip install -e '.[test]'
python -m pytest
python -m gpt_image2_agent --help
```

Live smoke tests are not run by default. If you wire one, keep it behind an explicit env flag and never run it in normal CI.

## Public links / Полезные ссылки

- YouTube: https://youtube.com/@alekseiulianov
- Telegram channel - Sprut AI: https://t.me/Sprut_AI
- Telegram chat - Sprut AI: https://t.me/+eH-qNIDmud8zNDZi
- AI Операционка: https://t.me/tribute/app?startapp=sJyg

## Canonical source

This project is maintained by Aleksei Ulianov / Sprut_AI.
Original repository: https://github.com/AlekseiUL/gpt-image-2-agent-kit

If you found this project mirrored, repackaged, or redistributed elsewhere, check this repository as the source of truth.

## Attribution

Where permitted by the applicable license, if you reuse, fork, modify, package, or publish this work, keep the original copyright and license notice and link back to the canonical repository.

## Русская версия

Это локальный набор для подготовки генераций и редактирования в GPT Image 2.5 через агента или CLI. В версии 0.2.0 по умолчанию выбрана `gpt-image-2.5-sunburst`; доступны также `gpt-image-2.5-flare` и прежняя `gpt-image-2`. Он помогает не просто отправить короткий запрос, а собрать нормальный промпт, добавить референсы, проверить план без траты лимита и сохранить понятный отчёт о генерации.

Ключевая идея простая: сначала план, потом live-вызов. Без сюрпризов с файлами, токенами и приватными картинками.

Что умеет:

- улучшать запрос через готовые пресеты;
- работать с референсами лица, стиля, продукта или композиции;
- сохранять локальные identity packs: один раз добавили свои фото, потом агент может использовать `--identity me`;
- сохранять style packs: брендбук, визуальный стиль, moodboard, стиль автора;
- работать в edit mode: взять исходную картинку и изменить только то, что попросили;
- делать `dry-run` без токена, сети и записи результата;
- выводить понятный Markdown-план через `--review-markdown`, чтобы агент или человек мог проверить запрос до live-вызова;
- писать результат только в безопасную папку;
- сохранять receipt без токенов и без сырых картинок;
- запускать live-генерацию только когда вы сами передали доступ.

Чего он не делает:

- не даёт бесплатный безлимит;
- не раздаёт чужой доступ;
- не является официальным SDK OpenAI Images API;
- не кликает браузер;
- не превращает личную подписку в публичный сервис.

Для лица/похожести используйте свои референсы осознанно. В live-режиме промпт и изображения уходят во внешний backend. Если нужно только подготовить запрос — используйте `--dry-run`.

Что изменилось для GPT Image 2.5:

- выбор модели через `--image-model`: Sunburst выбран для работы с референсами и правок, Flare доступен для повседневных генераций;
- уровни качества `xhigh` и `max` для моделей 2.5; привычный `medium` остаётся по умолчанию;
- точный размер через `--size WIDTHxHEIGHT` или `--size auto`, с приоритетом над `--aspect`;
- прозрачный фон через `--background transparent`, результат в PNG;
- в плане и receipt видны выбранные модель изображения, host-модель, фон и режим работы.

Пример плана обложки с Flare:

```bash
gpt-image2-agent "Обложка об AI-агентах, один крупный объект, без текста" \
  --image-model gpt-image-2.5-flare \
  --size 1536x864 --quality high \
  --dry-run --review-markdown
```

Пример удаления фона с Sunburst:

```bash
gpt-image2-agent \
  --edit-image generated/source.png \
  --edit "Удали фон, сохрани лицо, одежду и освещение" \
  --image-model gpt-image-2.5-sunburst \
  --background transparent --quality xhigh \
  --dry-run --review-markdown
```

Для прежней модели добавьте `--image-model gpt-image-2 --quality high`. Команда установки, CLI, имя Python-пакета и папка результатов не переименованы.

**Реальная live-генерация на 2.5 при этой миграции не проверялась.** Документация OpenAI подтверждает модели в официальном API, но не гарантирует их доступность через используемый здесь ChatGPT/Codex backend. Поддержка официального API в этот релиз не добавлена. Подробнее — [переход на 2.5](docs/migration-gpt-image-2.5.md).
