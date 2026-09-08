from __future__ import annotations

import io
import os
import stat
from pathlib import Path

import pytest
from PIL import Image

from gpt_image25_agent import files


def image_bytes(output_format="png", *, mode="RGB", size=(16, 16), color=None):
    stream = io.BytesIO()
    if color is None:
        color = (255, 100, 0, 0) if mode == "RGBA" else "red"
    Image.new(mode, size, color).save(stream, format=output_format.upper())
    return stream.getvalue()


def resolve(out, root, **kwargs):
    return files.resolve_output_path(out, "", root=root, allow_outside=False, overwrite=False, create_parent=False, **kwargs)


@pytest.mark.parametrize("output_format,extension", [("png", ".png"), ("jpeg", ".jpg"), ("jpeg", ".jpeg"), ("webp", ".webp")])
def test_full_decoded_image_is_saved_with_private_mode(tmp_path, output_format, extension):
    path = tmp_path / f"image{extension}"
    data = image_bytes(output_format)
    files.atomic_write_image(path, data, output_format=output_format, overwrite=False)
    assert path.read_bytes() == data
    with Image.open(path) as image:
        image.load()
        assert image.format == output_format.upper()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("output_format", ["png", "jpeg", "webp"])
def test_default_output_path_uses_selected_format_and_new_directory(tmp_path, output_format):
    path = resolve(None, tmp_path, output_format=output_format)
    assert path.parent == tmp_path / "generated" / "gpt-image-2.5"
    assert path.suffix == (".jpg" if output_format == "jpeg" else f".{output_format}")
    assert "gpt-image-2.5" in path.name


@pytest.mark.parametrize("output_format,extension", [("png", ".png"), ("jpeg", ".jpg"), ("jpeg", ".jpeg"), ("webp", ".webp")])
def test_explicit_output_extension_matches_format(tmp_path, output_format, extension):
    path = tmp_path / f"out{extension}"
    assert resolve(path, tmp_path, output_format=output_format) == path
    with pytest.raises(files.PolicyError, match="must end with"):
        resolve(tmp_path / "wrong.gif", tmp_path, output_format=output_format)


def test_output_preflight_rejects_regular_file_ancestor_without_creating_parents(tmp_path):
    blocked = tmp_path / "blocked"
    blocked.write_text("keep", encoding="utf-8")
    with pytest.raises(files.PolicyError, match="ancestor must be a directory"):
        resolve(blocked / "missing" / "out.png", tmp_path)
    assert list(tmp_path.iterdir()) == [blocked]
    assert blocked.read_text(encoding="utf-8") == "keep"


def test_output_preflight_rejects_existing_directory_even_with_overwrite(tmp_path):
    directory = tmp_path / "out.png"
    directory.mkdir()
    with pytest.raises(files.PolicyError, match="must be a regular file"):
        files.resolve_output_path(directory, "", root=tmp_path, allow_outside=False,
                                  overwrite=True, create_parent=False)
    assert directory.is_dir()


@pytest.mark.parametrize("output_format", ["png", "jpeg", "webp"])
def test_truncated_image_is_refused_without_touching_output(tmp_path, output_format):
    path = tmp_path / ("out.jpg" if output_format == "jpeg" else f"out.{output_format}")
    previous = image_bytes(output_format)
    path.write_bytes(previous)
    # Preserve the format's magic bytes while removing the complete pixel stream.
    truncated = image_bytes(output_format, size=(128, 128))[:24]
    with pytest.raises(files.PolicyError, match="fully decodable"):
        files.atomic_write_image(path, truncated, output_format=output_format, overwrite=True)
    assert path.read_bytes() == previous
    assert list(tmp_path.iterdir()) == [path]


def test_png_crc_corruption_is_refused(tmp_path):
    data = bytearray(image_bytes())
    data[29] ^= 1  # IHDR CRC: signature and dimensions still look like PNG.
    with pytest.raises(files.PolicyError, match="fully decodable"):
        files.atomic_write_png(tmp_path / "out.png", bytes(data), overwrite=False)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("actual,expected", [("jpeg", "png"), ("webp", "jpeg"), ("png", "webp")])
def test_valid_image_in_wrong_format_is_refused(tmp_path, actual, expected):
    path = tmp_path / ("out.jpg" if expected == "jpeg" else f"out.{expected}")
    with pytest.raises(files.PolicyError, match=f"not a {expected.upper()}"):
        files.atomic_write_image(path, image_bytes(actual), output_format=expected, overwrite=False)
    assert not list(tmp_path.iterdir())


def test_existing_output_requires_explicit_overwrite(tmp_path):
    path = tmp_path / "out.png"
    previous, replacement = image_bytes(), image_bytes(color="blue")
    path.write_bytes(previous)
    with pytest.raises(files.PolicyError, match="already exists"):
        files.atomic_write_png(path, replacement, overwrite=False)
    assert path.read_bytes() == previous
    files.atomic_write_png(path, replacement, overwrite=True)
    assert path.read_bytes() == replacement


def test_concurrent_creation_is_never_overwritten(tmp_path, monkeypatch):
    path = tmp_path / "out.png"
    competitor = b"another writer's output"
    real_link = os.link

    def competing_link(source, destination):
        Path(destination).write_bytes(competitor)
        return real_link(source, destination)

    monkeypatch.setattr(files.os, "link", competing_link)
    with pytest.raises(files.PolicyError, match="already exists"):
        files.atomic_write_png(path, image_bytes(), overwrite=False)
    assert path.read_bytes() == competitor
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("overwrite", [False, True])
def test_output_symlink_is_refused(tmp_path, overwrite):
    target, path = tmp_path / "target.png", tmp_path / "out.png"
    previous = image_bytes()
    target.write_bytes(previous)
    path.symlink_to(target)
    with pytest.raises(files.PolicyError, match="symlink"):
        files.atomic_write_png(path, image_bytes(color="blue"), overwrite=overwrite)
    assert path.is_symlink()
    assert target.read_bytes() == previous


def test_symlink_introduced_during_write_is_refused(tmp_path, monkeypatch):
    target, path = tmp_path / "target.png", tmp_path / "out.png"
    previous = image_bytes()
    target.write_bytes(previous)
    real_fsync = os.fsync

    def insert_symlink(fd):
        real_fsync(fd)
        path.symlink_to(target)

    monkeypatch.setattr(files.os, "fsync", insert_symlink)
    with pytest.raises(files.PolicyError, match="symlink"):
        files.atomic_write_png(path, image_bytes(color="blue"), overwrite=True)
    assert path.is_symlink()
    assert target.read_bytes() == previous
    assert sorted(p.name for p in tmp_path.iterdir()) == ["out.png", "target.png"]


def test_mask_validates_without_consuming_reference_budget(tmp_path, monkeypatch):
    base, mask = tmp_path / "base.png", tmp_path / "mask.png"
    base.write_bytes(image_bytes())
    mask.write_bytes(image_bytes(mode="RGBA"))
    monkeypatch.setattr(files, "MAX_REFS", 0)
    assert files.validate_mask(mask, base, root=tmp_path) == mask


@pytest.mark.parametrize("case,match", [
    ("opaque", "fully opaque"), ("no_alpha", "alpha channel"),
    ("dimensions", "same dimensions"), ("truncated", "fully decodable"),
    ("base_jpeg", "must be PNG"), ("base_wrong_content", "not a PNG"),
    ("mask_wrong_content", "not a PNG"), ("missing", "not found"),
])
def test_invalid_mask_is_refused(tmp_path, case, match):
    base, mask = tmp_path / "base.png", tmp_path / "mask.png"
    base.write_bytes(image_bytes())
    mask.write_bytes(image_bytes(mode="RGBA"))
    if case == "opaque":
        mask.write_bytes(image_bytes(mode="RGBA", color=(255, 255, 255, 255)))
    elif case == "no_alpha":
        mask.write_bytes(image_bytes())
    elif case == "dimensions":
        mask.write_bytes(image_bytes(mode="RGBA", size=(32, 16)))
    elif case == "truncated":
        mask.write_bytes(image_bytes(mode="RGBA")[:24])
    elif case == "base_jpeg":
        base = tmp_path / "base.jpg"
        base.write_bytes(image_bytes("jpeg"))
    elif case == "base_wrong_content":
        base.write_bytes(image_bytes("jpeg"))
    elif case == "mask_wrong_content":
        mask.write_bytes(image_bytes("webp"))
    elif case == "missing":
        mask.unlink()
    with pytest.raises(files.PolicyError, match=match):
        files.validate_mask(mask, base, root=tmp_path)


def test_mask_file_limit_is_checked_before_decode(tmp_path, monkeypatch):
    base, mask = tmp_path / "base.png", tmp_path / "mask.png"
    base.write_bytes(image_bytes())
    mask.write_bytes(image_bytes(mode="RGBA"))
    monkeypatch.setattr(files, "MAX_REF_BYTES", 8)
    with pytest.raises(files.PolicyError, match="too large"):
        files.validate_mask(mask, base)


def test_mask_root_policy_is_enforced_with_explicit_override(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    base, mask = root / "base.png", tmp_path / "mask.png"
    base.write_bytes(image_bytes())
    mask.write_bytes(image_bytes(mode="RGBA"))
    with pytest.raises(files.PolicyError, match="must stay under"):
        files.validate_mask(mask, base, root=root)
    assert files.validate_mask(mask, base, root=root, allow_outside=True) == mask


def test_reference_data_url_mime_follows_file_content(tmp_path):
    path = tmp_path / "mislabelled.png"
    path.write_bytes(image_bytes("jpeg"))
    assert files.ref_to_data_url(path).startswith("data:image/jpeg;base64,")
