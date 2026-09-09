# Changelog

## 0.3.1 — 2026-09-09

Reliability hardening after independent review of the 0.3.0 release.

- Disable unused streamed partial previews; the CLI consumes only the final validated image.
- Make the authenticated HTTP client scope explicit and test that the Bearer header is attached to that client.
- Fully decode reference images before upload instead of accepting image signatures alone.
- Persist a sanitized `error` receipt for live auth/backend failures when `--receipt` was requested.
- Clarify that custom-size bounds are a conservative local compatibility policy, not a documented GPT Image 2.5 capability guarantee.
- Add a clean wheel-install CLI smoke to CI.

## 0.3.0 — 2026-09-09

GPT Image 2.5-only release under the `gpt-image-2-5-agent-kit` project name.

- Rename CLI to `gpt-image25-agent` and Python import to `gpt_image25_agent`; change the default output directory to `generated/gpt-image-2.5/`.
- Remove earlier image models from execution. Keep Sunburst as the default and Flare as the explicit alternative.
- Add PNG/JPEG/WebP selection, JPEG/WebP compression, masked edits, reference roles, preserve instructions and explicit action selection.
- Preserve literal requested text and reject conflicting text/no-text presets.
- Require successful stream completion and full image decoding before output; commit validated files atomically and enforce no-overwrite protection at write time.
- Record actual output metadata separately from requested settings. Preserve existing library directories and v1 schema identifiers for saved-data compatibility.
- Refresh documentation and examples. Verification evidence is tracked in the [README](README.md#verification-status); the ChatGPT/Codex backend remains experimental and no official API backend is implemented.

See [migration notes](docs/migration-gpt-image-2.5.md) for breaking changes.

## 0.2.0 — historical

Introduced Sunburst and Flare selection, additional 2.5 quality levels, custom size and background planning. Kept the earlier model as an explicit compatibility option at that time; 0.3.0 removes that execution option.

## 0.1.0 — historical

Initial local prompt/reference toolkit with default dry-run, saved identity/style packs, edits, receipts and root-bounded paths. Earlier implementation details remain in Git history.
