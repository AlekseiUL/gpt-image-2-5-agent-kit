from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .files import sha256_file, assert_inside, PolicyError


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def actual_output_metadata(path: Path) -> dict[str, Any]:
    from PIL import Image

    with Image.open(path) as image:
        image.load()
        return {"width": image.width, "height": image.height, "format": image.format.lower(),
                "mode": image.mode, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def build_receipt(*, status: str, dry_run: bool, backend: str, host_model: str, image_model: str,
                  quality: str, aspect: str, size: str, out: Path, prompt: str, refs: list[Path],
                  background: str = "opaque", action: str = "auto", include_prompt: bool = False,
                  error_class: str | None = None, output_format: str = "png",
                  output_compression: int | None = None, reference_roles: list[str] | None = None,
                  mask: Path | None = None) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": "gpt-image2-agent.receipt.v1",
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": status, "dry_run": dry_run, "backend": backend,
        "host_model": host_model, "image_model": image_model,
        "quality": quality, "aspect": aspect, "size": size, "background": background,
        "output_format": output_format, "output_compression": output_compression,
        "action": action, "output_path": str(out), "prompt_sha256": prompt_hash(prompt),
        "refs": [{"path": str(p), "sha256": sha256_file(p), "bytes": p.stat().st_size, "suffix": p.suffix.lower()} for p in refs],
        "reference_roles": reference_roles if reference_roles is not None else ["general"] * len(refs),
    }
    if mask:
        receipt["mask"] = {"path": str(mask), "sha256": sha256_file(mask), "bytes": mask.stat().st_size}
    if include_prompt:
        receipt["prompt"] = prompt
    if error_class:
        receipt["error_class"] = error_class
    return receipt


def validate_receipt_path(path: Path, *, root: Path, allow_outside: bool = False) -> Path:
    path = path.expanduser()
    if path.suffix.lower() != ".json":
        raise PolicyError("receipt path must end with .json")
    if path.is_symlink():
        raise PolicyError("Receipt path must not be a symlink.")
    resolved = assert_inside(path, root, "Receipt", allow_outside=allow_outside)
    if resolved.exists() and not resolved.is_file():
        raise PolicyError("Receipt path is not a regular file.")
    # Check an existing ancestor before a live request can spend quota.
    ancestor = resolved.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    if not ancestor.is_dir():
        raise PolicyError("Receipt parent is not a directory.")
    return resolved


def write_receipt(path: Path, receipt: dict[str, Any], *, root: Path, allow_outside: bool = False, overwrite: bool = True) -> Path:
    resolved = validate_receipt_path(path, root=root, allow_outside=allow_outside)
    if resolved.exists() and not overwrite:
        raise PolicyError(f"receipt already exists: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{resolved.name}.", suffix=".tmp", dir=resolved.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(receipt, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if resolved.is_symlink():
            raise PolicyError("Receipt path became a symlink.")
        if overwrite:
            os.replace(temporary, resolved)
        else:
            os.link(temporary, resolved)
    finally:
        temporary.unlink(missing_ok=True)
    return resolved
