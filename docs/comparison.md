# Comparison and positioning

GPT Image tools usually fall into a few groups:

- simple prompt-to-image CLIs;
- web or desktop UIs with drag-and-drop references;
- prompt galleries / skill packs;
- browser automation wrappers;
- direct API wrappers.

GPT Image 2.5 Agent Kit is intentionally different.

## Main differentiator

It is not trying to be the richest UI. It is an agent-safe operating layer:

```text
request -> prompt plan -> references -> dry-run -> receipt -> optional live generation
```

That matters when an AI agent is doing the work, because the risky parts are not only the model call. The risky parts are:

- which private files were used as references;
- where the output was written;
- whether a person's likeness was used intentionally;
- whether a brand/style pack was selected correctly;
- whether the final prompt is inspectable before live generation;
- whether the run leaves an audit trail without leaking secrets.

## What this kit does better than a generic CLI

- Dry-run is default unless `--live` is passed.
- Saved identity packs let agents reuse approved local references by name.
- Saved style packs let agents keep a consistent brand/creator style.
- Edit mode gives agents a clear path for “change this image but preserve X”.
- JSON receipts store hashes and metadata, not raw tokens or image bytes.
- Output/reference/prompt/receipt paths are root-bounded by default.
- Symlink escapes are tested.
- Explicit reference roles, preservation instructions and masks make edit intent inspectable.
- Completed responses and full image decoding are required before an atomic output write.
- Offline validation and a repository quality scanner can run without live credentials.
- PNG/JPEG/WebP output settings are recorded separately from actual decoded output metadata.

## What this kit does not compete on

- It is not a full image studio UI.
- It does not promise unlimited/free generation.
- It does not hide account/rate-limit/product availability issues.
- It does not ship real identity references.
- It does not automate a logged-in browser.

## Best use cases

- AI agents producing images for a human operator.
- Repeatable portrait/avatar/thumbnail workflows with approved references.
- Brand-consistent visual generation from saved style packs.
- Safe image-edit planning before live calls.
- Local-first automation where receipts and boundaries matter.

Live execution uses an experimental ChatGPT/Codex backend, not an implemented official API integration. See [capabilities](capabilities.md) and [verification status](../README.md#verification-status) for the distinction between local controls and tested backend behavior.
