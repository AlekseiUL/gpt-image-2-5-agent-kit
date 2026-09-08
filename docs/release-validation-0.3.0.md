# Release 0.3.0 validation

Verified on 2026-09-09. The release accepts only GPT Image 2.5 Sunburst and Flare. The repository, distribution, CLI and Python package use the new 2.5 names; historical storage/schema identifiers remain compatible.

## Automated checks

269 offline tests pass, including:

- rejection of old models, invalid format/compression/transparency combinations and impossible output paths before auth or network;
- exact Cyrillic copy, scoped reference roles, explicit edit invariants and inherited-preset conflicts;
- PNG/JPEG/WebP decoding, malformed and truncated outputs, mask alpha/dimensions and output-format matching;
- completed-stream requirements, cached final image with an empty terminal output, partial-only streams, cancellation, errors and ambiguous multiple results;
- atomic output/receipt writes, overwrite guards and concurrent-file protection;
- receipts, actual file metadata and historical receipt-schema compatibility.

Lint and the source/privacy scan pass. Wheel and source distribution are built and the renamed command is checked from an isolated installation. Normal CI makes no image-generation requests.

## Live generation and edit

| Check | Requested settings | Actual result |
| --- | --- | --- |
| Sunburst generation | `gpt-image-2.5-sunburst`, high, opaque PNG, `1536x864`, zero references | Success on attempt 1 in 43.10 s; RGB PNG `1672x941`, 1,791,363 bytes |
| Flare edit | `gpt-image-2.5-flare`, medium, opaque PNG, `1536x864`, one edit base | Success on attempt 1 in 40.35 s; RGB PNG `1672x941`, 1,666,107 bytes |

The first prompt requested a repository cover with the exact title “GPT IMAGE 2.5 / AGENT KIT.” The second requested changing coral accents to emerald while retaining the title and composition. Both outputs decode fully. Visual inspection confirmed readable correct lettering, the intended color change and preservation of the overall composition. No private person/reference images were used. There were two live requests and no retries.

Generated cover:

![Sunburst cover](assets/gpt-image-2-5-agent-kit-hero.png)

Flare edit:

![Flare accent-color edit](assets/gpt-image-2-5-flare-edit.png)

[Machine-readable validation and file hashes](release-validation-0.3.0.json).

## Limits of this evidence

The model names record the requested payload, not independent backend model attestation. These two checks establish generation and reference editing for this account/route at this time; they do not guarantee future account access, latency or arbitrary prompt quality.

The actual dimensions differed from the request and are reported without silently resizing. Masks, transparency, JPEG/WebP, compression, extended quality and other sizes are validated and covered by mocked request tests, but were not live-tested for this release. The experimental subscription backend may reject or handle optional settings differently from the official API. An output with the wrong file format or corrupt image data is an error, never silently converted or promoted to success.

The toolkit does not implement an official OpenAI API backend, persistent server-side conversation IDs, automatic retries or an automatic model fallback. Further edits use an explicitly supplied local base image.
