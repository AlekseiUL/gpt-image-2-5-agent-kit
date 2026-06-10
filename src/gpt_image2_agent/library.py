from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from .files import PolicyError, assert_inside, default_root, validate_refs
from .prompts import available_presets

LIBRARY_DIR = ".gpt-image2-agent"


def _slug(name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip().lower()).strip("-._")
    if not value:
        raise PolicyError("library item name is empty")
    return value[:64]


def library_root(root: Path) -> Path:
    return default_root(root) / LIBRARY_DIR


def identity_dir(root: Path, name: str) -> Path:
    return library_root(root) / "identities" / _slug(name)


def style_dir(root: Path, name: str) -> Path:
    return library_root(root) / "styles" / _slug(name)


def _copy_refs(refs: list[Path], dest: Path, *, root: Path, allow_outside: bool) -> list[dict[str, Any]]:
    validated = validate_refs(refs, root=root, allow_outside=allow_outside)
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for idx, ref in enumerate(validated, 1):
        target = dest / f"ref-{idx:02d}{ref.suffix.lower()}"
        if target.exists() or target.is_symlink():
            raise PolicyError(f"library reference target already exists: {target}")
        shutil.copy2(ref, target)
        copied.append({"path": str(target.relative_to(root)), "source_name": ref.name, "bytes": target.stat().st_size})
    return copied


def save_identity(root: Path, name: str, refs: list[Path], *, notes: str = "", allow_ref_outside: bool = False) -> dict[str, Any]:
    root = default_root(root)
    if not refs:
        raise PolicyError("--add-identity requires at least one --ref image")
    dest = identity_dir(root, name)
    if dest.exists():
        raise PolicyError(f"identity already exists: {_slug(name)}. Remove it manually or choose another name.")
    copied = _copy_refs(refs, dest, root=root, allow_outside=allow_ref_outside)
    manifest = {"schema": "gpt-image2-agent.identity.v1", "name": _slug(name), "notes": notes, "refs": copied}
    (dest / "identity.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return manifest


def load_identity_refs(root: Path, name: str) -> list[Path]:
    root = default_root(root)
    manifest_path = assert_inside(identity_dir(root, name) / "identity.json", root, "Identity manifest")
    if not manifest_path.is_file():
        raise PolicyError(f"saved identity not found: {_slug(name)}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    refs = [assert_inside(root / item["path"], root, "Identity reference") for item in manifest.get("refs", [])]
    return validate_refs(refs, root=root, allow_outside=False)


def save_style(root: Path, name: str, *, prompt: str = "", presets: list[str] | None = None, refs: list[Path] | None = None, allow_ref_outside: bool = False) -> dict[str, Any]:
    root = default_root(root)
    presets = presets or []
    for preset in presets:
        if preset not in available_presets():
            raise PolicyError(f"unknown preset for style: {preset}")
    if not prompt.strip() and not presets and not refs:
        raise PolicyError("--add-style requires --style-prompt, --style-preset, or --ref")
    dest = style_dir(root, name)
    if dest.exists():
        raise PolicyError(f"style already exists: {_slug(name)}. Remove it manually or choose another name.")
    copied = _copy_refs(refs or [], dest, root=root, allow_outside=allow_ref_outside) if refs else []
    manifest = {"schema": "gpt-image2-agent.style.v1", "name": _slug(name), "prompt": prompt.strip(), "presets": presets, "refs": copied}
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "style.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return manifest


def load_style(root: Path, name: str) -> tuple[str, list[str], list[Path]]:
    root = default_root(root)
    manifest_path = assert_inside(style_dir(root, name) / "style.json", root, "Style manifest")
    if not manifest_path.is_file():
        raise PolicyError(f"saved style not found: {_slug(name)}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    refs = [assert_inside(root / item["path"], root, "Style reference") for item in manifest.get("refs", [])]
    refs = validate_refs(refs, root=root, allow_outside=False) if refs else []
    return str(manifest.get("prompt", "")).strip(), list(manifest.get("presets", [])), refs


def list_library(root: Path) -> dict[str, list[str]]:
    root = default_root(root)
    identities = sorted(p.name for p in (library_root(root) / "identities").glob("*") if (p / "identity.json").is_file()) if (library_root(root) / "identities").exists() else []
    styles = sorted(p.name for p in (library_root(root) / "styles").glob("*") if (p / "style.json").is_file()) if (library_root(root) / "styles").exists() else []
    return {"identities": identities, "styles": styles}
