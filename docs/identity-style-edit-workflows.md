# References, identities, styles and edits

Use references for a stated purpose: identity, style, a logo, layout or other task context. The toolkit does not infer permission to use a person merely because a saved pack exists. All file paths below are placeholders for your own files under `--root`.

## Saved identity packs

```bash
gpt-image25-agent --root . --add-identity alex \
  --ref refs/alex-front.png --ref refs/alex-side.png \
  --identity-notes "Use only when the request includes Alex."

gpt-image25-agent "cinematic portrait of Alex in a studio" \
  --identity alex --preset likeness --quality high --dry-run --json
```

References are copied into `.gpt-image2-agent/identities/<name>/` under the selected root with a manifest. The compatibility directory and schema names are unchanged in 0.3.0; no earlier model is enabled by these names. The public repository contains no private face references.

## Saved style packs

```bash
gpt-image25-agent --root . --add-style graphite-brand \
  --style-prompt "graphite palette, warm highlights, restrained visual density" \
  --style-preset brand-style --ref refs/style-board.png

gpt-image25-agent "landing-page hero for an automation course" \
  --style graphite-brand --preset product --dry-run --review-markdown
```

Style packs live under `.gpt-image2-agent/styles/<name>/`. Select them for the requested visual system; inspect the final prompt for inherited presets. `no-text` and `russian-text` are incompatible even when one comes from a style pack. Use `--list-library` to list local packs.

## Explicit reference roles

```bash
gpt-image25-agent "new product poster using the supplied mark and layout" \
  --ref refs/brand-mark.png --ref-role logo \
  --ref refs/layout.png --ref-role layout \
  --quality high --dry-run --review-markdown
```

When `--ref-role` is used, supply one role per explicit `--ref`, in the same order. Allowed roles are `identity`, `style`, `logo`, `layout`, and `general`; unlabeled explicit refs use `general`.

The actual image order is **edit base → saved identity refs → saved style refs → explicit refs**. The dry-run exposes the aligned roles and image indices. Saved packs receive automatic roles, and `--edit-image` assigns `edit_base`; a role label alone cannot select an edit base.

State what to borrow from each image. For example: identity without its pose/background, style without its original text, or layout without its original subjects. The combined five-reference limit is a toolkit policy, not an advertised model-wide limit.

## Edit changes and invariants

```bash
gpt-image25-agent \
  --edit-image generated/source.png \
  --edit "Replace the wall with a plain dark studio backdrop" \
  --preserve "person, face, clothing and pose" \
  --preserve "camera angle, crop and lighting" \
  --quality high --out generated/edited.png \
  --dry-run --review-markdown
```

`--edit` and repeatable `--preserve` require `--edit-image`. The base is the first image so its role is unambiguous. With a base, the toolkit requests `action: "edit"`; without one, the default action is `auto`. `--action generate` explicitly requests a new image and cannot be combined with an edit base; `--action edit` requires one.

Write separate, specific instructions for what changes and what stays. These are model guidance, not guarantees of exact identity, geometry or unchanged pixels. The payload does not send an `input_fidelity` parameter.

For a transparent cutout, request it explicitly and use an alpha-capable output format:

```bash
gpt-image25-agent \
  --edit-image generated/source.png --edit "Remove the background" \
  --preserve "person, face and clothing" \
  --background transparent --output-format png \
  --out generated/cutout.png --dry-run --json
```

## Masked edits

```bash
gpt-image25-agent \
  --edit-image generated/source.png --mask refs/sign-mask.png \
  --edit 'Change the sign to exactly "ЧАСТЬ 4"' \
  --preserve "everything outside the sign, including the approved title" \
  --quality high --out generated/sign-edit.png \
  --dry-run --review-markdown
```

Prepare an alpha PNG mask with the same pixel dimensions as the edit base. Use a PNG base for this workflow. Transparent mask pixels mark the area to edit; a fully opaque mask is rejected. An RGB image without an alpha channel is not a valid mask. Keep the base and mask within the toolkit's input/path limits.

The mask applies to the first image, which the toolkit reserves for the edit base. OpenAI describes masks as guidance that may not follow the boundary precisely. Inspect both the changed region and the content you asked to preserve. [Official mask guidance](https://developers.openai.com/api/docs/guides/image-generation#edit-an-image-using-a-mask).

## Exact text and independent variants

Quote literal text, including Cyrillic, and specify its placement, size, typographic direction and contrast. Preserve case, punctuation and line breaks. Use `--prompt-file` for long or multiline copy. See the [exact-text example](../examples/prompts/russian-text-cover.md).

For a series, run the CLI once per requested asset using the same approved anchors. Repeat the shared constraints and name the differences for each image; do not accidentally inherit old episode text or feed every result into an edit chain. The CLI produces one output image per live invocation and does not store a server-side conversation for iterative edits.

## Local planning and live use

A dry-run validates the local plan without token access or network calls. Read the final prompt, requested settings, references/roles, mask metadata and output path. Add `--live` to perform the operation using your compatible token provider; the prompt and selected images are then uploaded.

The ChatGPT/Codex backend remains experimental. Local validation does not prove account access, mask support or every other optional parameter on that backend. See [capabilities](capabilities.md) and the [verification status](../README.md#verification-status).
