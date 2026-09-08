from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from .files import sha256_file, assert_inside


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def build_receipt(*, status: str, dry_run: bool, backend: str, host_model: str, image_model: str, quality: str, aspect: str, size: str, out: Path, prompt: str, refs: list[Path], background: str = "opaque", action: str = "auto", include_prompt: bool = False, error_class: str | None = None) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": "gpt-image2-agent.receipt.v1",
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": status,
        "dry_run": dry_run,
        "backend": backend,
        "host_model": host_model,
        "image_model": image_model,
        "quality": quality,
        "aspect": aspect,
        "size": size,
        "background": background,
        "output_format": "png",
        "action": action,
        "output_path": str(out),
        "prompt_sha256": prompt_hash(prompt),
        "refs": [{"path": str(p), "sha256": sha256_file(p), "bytes": p.stat().st_size, "suffix": p.suffix.lower()} for p in refs],
    }
    if include_prompt:
        receipt["prompt"] = prompt
    if error_class:
        receipt["error_class"] = error_class
    return receipt


def write_receipt(path: Path, receipt: dict[str, Any], *, root: Path, allow_outside: bool = False, overwrite: bool = True) -> Path:
    if path.suffix.lower() != ".json":
        raise ValueError("receipt path must end with .json")
    resolved = assert_inside(path, root, "Receipt", allow_outside=allow_outside)
    if resolved.exists() and not overwrite:
        raise ValueError(f"receipt already exists: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return resolved
