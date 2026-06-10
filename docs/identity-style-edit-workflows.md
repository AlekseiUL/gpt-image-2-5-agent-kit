# Identity, style and edit workflows

This toolkit is designed for agents that need more than a one-shot prompt.

## Saved identity packs

Use identity packs when a user wants repeated generations with the same person or character.

Create a local identity pack:

```bash
gpt-image2-agent --root . \
  --add-identity alex \
  --ref refs/alex-front.png \
  --ref refs/alex-side.png \
  --identity-notes "Use only when the user explicitly asks to include Alex."
```

Use it later:

```bash
gpt-image2-agent "make a cinematic operator portrait with me" \
  --identity alex \
  --preset likeness \
  --dry-run
```

The tool copies references into `.gpt-image2-agent/identities/<name>/` under the selected `--root` and writes a small manifest. The public repo does not include real face references.

Privacy rule: live mode uploads the prompt and selected references to the configured backend. Use only images you have the right to upload.

## Saved style packs

Use style packs for brandbooks, creator styles, product visual systems or repeated campaign look.

Create a style pack:

```bash
gpt-image2-agent --root . \
  --add-style graphite-brand \
  --style-prompt "dark graphite palette, controlled contrast, clean premium lighting" \
  --style-preset brand-style \
  --ref refs/style-board.png
```

Use it:

```bash
gpt-image2-agent "landing page hero for an AI automation course" \
  --style graphite-brand \
  --preset product \
  --dry-run
```

Style references are guidance, not hidden assets. The dry-run prompt shows what will be sent.

## Edit workflow

Use edit mode when the user asks to change an existing image while preserving the rest.

```bash
gpt-image2-agent \
  --edit-image generated/source.png \
  --edit "remove the background, keep the person and lighting, add a clean dark studio backdrop" \
  --dry-run
```

For live mode, add `--live` and your token provider. The edit image is passed as a reference image with explicit edit instructions.

## Agent policy

A safe agent should follow this sequence:

1. If the user says “me”, “my face”, or names a saved identity, select the matching `--identity` pack.
2. If the user says “in our style”, “brand style”, or names a saved visual system, select the matching `--style` pack.
3. If the user asks to change an existing image, use `--edit-image` and `--edit`.
4. Always run `--dry-run --json` first and inspect:
   - final prompt;
   - refs count;
   - output path;
   - receipt metadata.
5. Run `--live` only after the plan is accepted by policy/human/operator.

Do not auto-use private identities for unrelated prompts. Saved identity packs are local memory, not permission to put a person into every image.
