# Security model

This is a local CLI for an operator who controls the machine and files under `--root`. It is not a multi-user service or a quota bypass.

## Local boundaries

- Dry-run is the default unless `--live` is passed; it does not read tokens or use the network. An explicitly requested receipt is the only dry-run file write.
- Output, reference, prompt, mask and receipt paths are root-bounded. Explicit outside-root flags, where supported, are deliberate overrides for the selected files.
- Output symlinks and resolved parent-path escapes are blocked.
- Existing output files require `--overwrite`. The final write also enforces no-overwrite protection if a file appears while the request is running.
- Generated files are accepted only after successful response completion, full image decoding and format validation, then written atomically. Partial streams, image signatures without valid content and failed responses are not successful outputs.
- References are checked by extension/signature and fully decoded before upload. Masks require a valid alpha PNG of the edit base's dimensions with a transparent edit region.
- Earlier or unknown image models are rejected. There is no automatic retry or model fallback.

## Saved packs and receipts

Identity/style packs remain under `.gpt-image2-agent/identities/` and `.gpt-image2-agent/styles/`. They can contain private face or brand references. Do not commit them unless they are intentionally public fixtures.

Receipts omit the raw final prompt by default and exclude credentials and image bytes. Paths, hashes, pack names and request metadata can still reveal private context. Review them before sharing. [Receipt privacy](receipt-schema.md).

## Live uploads and authentication

Live mode uploads the final prompt, selected reference images and any mask to the configured ChatGPT/Codex backend. Use files that are appropriate for the current task and that you may upload. Local planning is available without uploading them.

Token providers:

- `env`: `CHATGPT_CODEX_ACCESS_TOKEN` or the name supplied with `--token-env`;
- `file`: an explicitly selected `--token-file`;
- `command`: a trusted local `--token-command`, executed without a shell.

The command provider runs code with your local permissions; choose it deliberately. Error redaction reduces accidental credential disclosure, but do not log or paste credentials. This toolkit does not provide tokens or implement an official OpenAI API backend.

## Limits of the boundary

Backend availability, account access and support for optional parameters are independent of local validation. A successful smoke test establishes only the tested combination. See [capabilities](capabilities.md) and [verification status](../README.md#verification-status).

A service built around this CLI needs its own authentication, per-user storage, authorization, retention and rate controls. The filesystem boundary here is not a substitute for those controls.
