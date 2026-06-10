# GPT Image 2 Agent Kit

A local-first toolkit for agents and operators who want a safer GPT Image 2 workflow: better prompts, optional reference images, dry-run planning, receipts, and strict file boundaries.

It is built from the lessons of an internal designer-agent workflow, but this public repo is sanitized: no private paths, no private facepack, no tokens, no internal agent names.

## What it does

- Turns a short request into a stronger image-generation prompt with reusable presets.
- Supports optional reference images for likeness, style, logo, composition, or product context.
- Uses dry-run by default so agents can inspect the plan before spending quota.
- Writes outputs only inside a configured safe root unless you explicitly override it.
- Produces JSON receipts with hashes/metadata, not raw secrets or image bytes.
- Can call a ChatGPT/Codex GPT Image 2 route if you provide your own compatible access token.

## What it is not

- Not a hosted image service.
- Not a quota bypass.
- Not “free unlimited GPT Image 2.”
- Not an official OpenAI Images API SDK.
- Not browser automation.
- Not a way to publish or share your subscription token.

Use wording carefully: this tool can use your existing compatible ChatGPT/Codex access where available. Product availability, model access, rate limits, and terms can change.

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

Use a reference image in the plan. This repository intentionally does not include real face references; replace the path with your own local image:

```bash
gpt-image2-agent "make a cinematic Telegram avatar in the same likeness" \
  --ref path/to/your-reference.png \
  --preset likeness \
  --dry-run
```

Live generation is opt-in:

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

Presets are prompt additions, not magic. Check the final dry-run prompt before live generation.

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

Это локальный набор для работы с GPT Image 2 через агента или CLI. Он помогает не просто отправить короткий запрос, а собрать нормальный промпт, добавить референсы, проверить план без траты лимита и сохранить понятный отчёт о генерации.

Ключевая идея простая: сначала план, потом live-вызов. Без сюрпризов с файлами, токенами и приватными картинками.

Что умеет:

- улучшать запрос через готовые пресеты;
- работать с референсами лица, стиля, продукта или композиции;
- делать `dry-run` без токена, сети и записи файла;
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
