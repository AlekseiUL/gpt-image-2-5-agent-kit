from __future__ import annotations

import base64
import hashlib
import io
import os
import tempfile
import warnings
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
OUTPUT_EXTENSIONS = {"png": {".png"}, "jpeg": {".jpg", ".jpeg"}, "webp": {".webp"}}
MAX_REFS = 5
MAX_REF_BYTES = 15 * 1024 * 1024
MAX_REFS_TOTAL_BYTES = 40 * 1024 * 1024

class PolicyError(ValueError):
    """Raised for local policy violations before network calls."""


def resolve_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def assert_inside(path: Path, root: Path, label: str, *, allow_outside: bool = False) -> Path:
    resolved = resolve_path(path)
    root = resolve_path(root)
    if allow_outside:
        return resolved
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PolicyError(f"{label} must stay under {root}. Got: {resolved}. Use the explicit override flag only when intentional.") from exc
    return resolved


def default_root(root: Path | None = None) -> Path:
    return resolve_path(root or Path.cwd())


def resolve_output_path(out: Path | None, prompt_slug: str, *, root: Path, allow_outside: bool, overwrite: bool, create_parent: bool, output_format: str = "png") -> Path:
    from datetime import datetime
    import re
    import uuid
    extensions = _output_extensions(output_format)
    safe_root = default_root(root)
    if out is None:
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", prompt_slug.strip().lower()).strip("-._")[:42] or "gpt-image-2.5"
        suffix = ".jpg" if output_format == "jpeg" else f".{output_format}"
        candidate = safe_root / "generated" / "gpt-image-2.5" / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slug}-{uuid.uuid4().hex[:6]}{suffix}"
    else:
        candidate = out.expanduser()
    if candidate.suffix.lower() not in extensions:
        raise PolicyError(f"Output path must end with {' or '.join(sorted(extensions))} for {output_format}: {candidate}")
    if candidate.is_symlink():
        target = candidate.resolve(strict=False)
        if target.suffix.lower() not in extensions:
            raise PolicyError(f"Resolved output target must end with {' or '.join(sorted(extensions))}: {target}")
        assert_inside(target, safe_root, "Output file", allow_outside=allow_outside)
        raise PolicyError(f"Output path is a symlink and is refused for safety: {candidate}")
    if candidate.exists():
        existing = candidate.resolve(strict=True)
        assert_inside(existing, safe_root, "Output file", allow_outside=allow_outside)
        if not existing.is_file():
            raise PolicyError(f"Output must be a regular file, not a directory or special file: {existing}")
        if not overwrite:
            raise PolicyError(f"Output already exists: {existing}. Use --overwrite to replace it.")
        return existing
    parent = assert_inside(candidate.parent, safe_root, "Output parent", allow_outside=allow_outside)
    ancestor = parent
    while not ancestor.exists() and ancestor != ancestor.parent:
        ancestor = ancestor.parent
    if not ancestor.is_dir():
        raise PolicyError(f"Output parent ancestor must be a directory: {ancestor}")
    resolved = parent / candidate.name
    if create_parent:
        parent.mkdir(parents=True, exist_ok=True)
    return resolved


def resolve_prompt_file(path: Path, *, root: Path, allow_outside: bool) -> Path:
    p = assert_inside(path, root, "Prompt file", allow_outside=allow_outside)
    if not p.is_file():
        raise PolicyError(f"Prompt file not found: {p}")
    return p


def read_prompt(prompt: str | None, prompt_file: Path | None, *, root: Path, allow_prompt_file_outside: bool) -> str:
    if prompt and prompt_file:
        raise PolicyError("Pass either positional prompt or --prompt-file, not both.")
    if prompt_file:
        text = resolve_prompt_file(prompt_file, root=root, allow_outside=allow_prompt_file_outside).read_text(encoding="utf-8")
    elif prompt:
        text = prompt
    else:
        raise PolicyError("Prompt is required. Pass a positional prompt or --prompt-file.")
    text = text.strip()
    if not text:
        raise PolicyError("Prompt is empty after trimming whitespace.")
    return text


def validate_refs(refs: list[Path], *, root: Path, allow_outside: bool) -> list[Path]:
    if len(refs) > MAX_REFS:
        raise PolicyError(f"max {MAX_REFS} reference images, got {len(refs)}")
    resolved: list[Path] = []
    total = 0
    for ref in refs:
        path = assert_inside(ref, root, "Reference image", allow_outside=allow_outside)
        if not path.is_file():
            raise PolicyError(f"Reference image not found: {path}")
        if path.suffix.lower() not in IMAGE_EXTS:
            raise PolicyError(f"Unsupported reference image extension: {path}. Use png/jpg/webp.")
        image_kind_from_bytes(path)
        size = path.stat().st_size
        if size > MAX_REF_BYTES:
            raise PolicyError(f"Reference too large: {path} ({size} bytes > {MAX_REF_BYTES})")
        total += size
        resolved.append(path)
    if total > MAX_REFS_TOTAL_BYTES:
        raise PolicyError(f"reference images total too large: {total} bytes > {MAX_REFS_TOTAL_BYTES}")
    return resolved


def image_kind_from_bytes(path: Path) -> str:
    header = path.read_bytes()[:16]
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "webp"
    raise PolicyError(f"Reference image content is not png/jpg/webp: {path}")


def mime_for(path: Path) -> str:
    return f"image/{image_kind_from_bytes(path)}"


def ref_to_data_url(path: Path) -> str:
    return f"data:{mime_for(path)};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _output_extensions(output_format: str) -> set[str]:
    if output_format not in OUTPUT_EXTENSIONS:
        raise PolicyError("Output format must be png, jpeg, or webp.")
    return OUTPUT_EXTENSIONS[output_format]


def _decode_image(data: bytes, *, expected_format: str, label: str):
    """Verify the container and fully decode its pixels before accepting bytes."""
    from PIL import Image

    _output_extensions(expected_format)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as probe:
                if probe.format != expected_format.upper():
                    raise PolicyError(f"{label} is not a {expected_format.upper()} file.")
                probe.verify()
            with Image.open(io.BytesIO(data)) as decoded:
                decoded.load()
                return decoded.copy()
    except PolicyError:
        raise
    except Exception as exc:
        raise PolicyError(f"{label} is not a valid, fully decodable {expected_format.upper()} image.") from exc


def validate_mask(mask: Path, edit_base: Path, *, root: Path | None = None, allow_outside: bool = False) -> Path:
    """Validate a PNG mask independently of the reference-image count budget."""
    path = assert_inside(mask, root, "Mask image", allow_outside=allow_outside) if root is not None else resolve_path(mask)
    base = assert_inside(edit_base, root, "Edit base image", allow_outside=allow_outside) if root is not None else resolve_path(edit_base)
    decoded = []
    try:
        for source, label in ((path, "Mask image"), (base, "Edit base image")):
            if not source.is_file():
                raise PolicyError(f"{label} not found: {source}")
            if source.suffix.lower() != ".png":
                raise PolicyError(f"{label} must be PNG for masked edits: {source}")
            if source.stat().st_size > MAX_REF_BYTES:
                raise PolicyError(f"{label} too large: {source} (limit {MAX_REF_BYTES} bytes)")
            decoded.append(_decode_image(source.read_bytes(), expected_format="png", label=label))
        mask_image, base_image = decoded
        if mask_image.size != base_image.size:
            raise PolicyError("Mask image and edit base image must have the same dimensions.")
        if "A" not in mask_image.getbands() and "transparency" not in mask_image.info:
            raise PolicyError("Mask PNG must contain an alpha channel.")
        if mask_image.convert("RGBA").getchannel("A").getextrema()[0] == 255:
            raise PolicyError("Mask PNG is fully opaque; include transparent pixels for the area to edit.")
    finally:
        for image in decoded:
            image.close()
    return path


def atomic_write_image(path: Path, data: bytes, *, output_format: str = "png", overwrite: bool) -> None:
    decoded = _decode_image(data, expected_format=output_format, label="Generated payload")
    decoded.close()
    if path.suffix.lower() not in _output_extensions(output_format):
        raise PolicyError(f"Output extension does not match {output_format}: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise PolicyError(f"Refusing to write through output symlink: {path}")
    if path.exists() and not overwrite:
        raise PolicyError(f"Output already exists: {path}. Use --overwrite to replace it.")
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        if path.is_symlink():
            raise PolicyError(f"Refusing to replace output symlink: {path}")
        if overwrite:
            os.replace(tmp, path)
        else:
            try:
                # Hard-link publication is atomic and refuses a competing output.
                # An existence check followed by replace would clobber that file.
                os.link(tmp, path)
            except FileExistsError as exc:
                raise PolicyError(f"Output already exists: {path}. Use --overwrite to replace it.") from exc
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def atomic_write_png(path: Path, data: bytes, *, overwrite: bool) -> None:
    """Compatibility wrapper for callers explicitly requesting PNG output."""
    atomic_write_image(path, data, output_format="png", overwrite=overwrite)
