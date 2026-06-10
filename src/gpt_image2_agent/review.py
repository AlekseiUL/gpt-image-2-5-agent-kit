from __future__ import annotations

from pathlib import Path
from typing import Any


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
) -> str:
    """Build a human-readable review plan for an agent/operator.

    This intentionally includes the final prompt because it is a review artifact
    printed to the operator. JSON receipts stay privacy-first and omit the raw
    prompt unless explicitly requested.
    """
    lines = [
        "# GPT Image 2 generation review",
        "",
        "## Mode",
        _line("Dry run", str(dry_run).lower()),
        _line("Network call", "no" if dry_run else "yes"),
        _line("Backend", backend),
        _line("Live generation executed", "no" if dry_run else "yes"),
        "",
        "## Settings",
        _line("Quality", quality),
        _line("Aspect", aspect),
        _line("Size", size),
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
