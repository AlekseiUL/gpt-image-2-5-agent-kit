from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import DEFAULT_IMAGE_MODEL


def _line(label: str, value: Any) -> str:
    return f"- **{label}:** {value if value not in (None, '') else 'not set'}"


def build_review_markdown(
    *,
    dry_run: bool,
    backend: str,
    final_prompt: str,
    quality: str,
    aspect: str,
    size: str,
    out: Path,
    refs: list[Path],
    identity: str | None,
    style: str | None,
    edit_image: Path | None,
    receipt_path: Path | None = None,
    image_model: str = DEFAULT_IMAGE_MODEL,
    host_model: str | None = None,
    background: str = "opaque",
    action: str = "auto",
    output_format: str = "png",
    output_compression: int | None = None,
    mask: Path | None = None,
    reference_roles: list[str] | None = None,
) -> str:
    """Build a human-readable review plan for an agent/operator.

    This intentionally includes the final prompt because it is a review artifact
    printed to the operator. JSON receipts stay privacy-first and omit the raw
    prompt unless explicitly requested.
    """
    lines = [
        "# GPT Image 2.5 generation review",
        "",
        "## Mode",
        _line("Dry run", str(dry_run).lower()),
        _line("Network call", "no" if dry_run else "yes"),
        _line("Backend", backend),
        _line("Live generation executed", "no" if dry_run else "yes"),
        "",
        "## Settings",
        _line("Image model", image_model),
        _line("Host model", host_model),
        _line("Quality", quality),
        _line("Aspect", aspect),
        _line("Size", size),
        _line("Background", background),
        _line("Output format", output_format),
        _line("Output compression", output_compression),
        _line("Mask", mask),
        _line("Reference roles", ", ".join(reference_roles or [])),
        _line("Action", action),
        _line("Output path", out),
        _line("Receipt path", receipt_path),
        "",
        "## References",
        _line("Refs count", len(refs)),
        _line("Identity", identity),
        _line("Style", style),
        _line("Edit image", edit_image),
    ]
    if refs:
        lines.append("")
        lines.append("### Ref paths")
        for ref in refs:
            lines.append(f"- `{ref}`")
    lines.extend([
        "",
        "## Final prompt",
        "",
        "```text",
        final_prompt,
        "```",
        "",
        "## Safety note",
    ])
    if dry_run:
        lines.append("This was a dry run: no auth token was read, no network call was made, and no image output was written. If `--receipt` was provided, only the receipt file was written.")
    else:
        lines.append("Live mode sends the final prompt and selected reference images to the configured backend. Use only refs you have the right to upload.")
    return "\n".join(lines) + "\n"
