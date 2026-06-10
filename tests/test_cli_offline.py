from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from gpt_image2_agent import files as f
from gpt_image2_agent import prompts
from gpt_image2_agent.redaction import sanitize_error_text


def png(path: Path, size: int = 16) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * size)
    return path


def run_cli(args, cwd: Path, env=None):
    e = os.environ.copy()
    if env:
        e.update(env)
    return subprocess.run([sys.executable, "-m", "gpt_image2_agent", *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=e)


def test_build_prompt_presets_and_refs():
    out = prompts.build_prompt("make avatar", ["portrait", "likeness"], refs_count=1)
    assert "make avatar" in out
    assert "Reference images supplied: 1" in out
    assert "watermarks" in out


def test_unknown_preset_rejected():
    with pytest.raises(ValueError):
        prompts.build_prompt("x", ["missing"])


def test_output_outside_root_blocked(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    with pytest.raises(f.PolicyError):
        f.resolve_output_path(tmp_path / "outside.png", "robot", root=root, allow_outside=False, overwrite=False, create_parent=False)


def test_prefix_attack_blocked(tmp_path):
    root = tmp_path / "safe"
    root.mkdir()
    outside = tmp_path / "safe2" / "out.png"
    with pytest.raises(f.PolicyError):
        f.resolve_output_path(outside, "robot", root=root, allow_outside=False, overwrite=False, create_parent=False)


def test_output_symlink_refused(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.png"
    link = root / "out.png"
    link.symlink_to(outside)
    with pytest.raises(f.PolicyError):
        f.resolve_output_path(link, "robot", root=root, allow_outside=False, overwrite=True, create_parent=False)


def test_parent_symlink_escape_blocked(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    link = root / "linked"
    link.symlink_to(outside_dir, target_is_directory=True)
    with pytest.raises(f.PolicyError):
        f.resolve_output_path(link / "out.png", "robot", root=root, allow_outside=False, overwrite=False, create_parent=False)


def test_existing_output_requires_overwrite(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    out = root / "out.png"
    out.write_bytes(b"old")
    with pytest.raises(f.PolicyError):
        f.resolve_output_path(out, "robot", root=root, allow_outside=False, overwrite=False, create_parent=False)


def test_refs_policy(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    ref = png(root / "ref.png")
    assert f.validate_refs([ref], root=root, allow_outside=False) == [ref]
    outside = png(tmp_path / "outside.png")
    with pytest.raises(f.PolicyError):
        f.validate_refs([outside], root=root, allow_outside=False)


def test_ref_symlink_escape_blocked(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = png(tmp_path / "private.png")
    link = root / "ref.png"
    link.symlink_to(outside)
    with pytest.raises(f.PolicyError):
        f.validate_refs([link], root=root, allow_outside=False)


def test_atomic_write_png_validates_png_and_no_partial(tmp_path):
    out = tmp_path / "out.png"
    with pytest.raises(f.PolicyError):
        f.atomic_write_png(out, b"not png", overwrite=False)
    assert not out.exists()
    f.atomic_write_png(out, b"\x89PNG\r\n\x1a\nabc", overwrite=False)
    assert out.read_bytes().startswith(b"\x89PNG")


def test_redaction_removes_real_sensitive_values():
    raw = "Authorization: Bearer secretABC access_token=tok123 cookie=session=tok456 {'refresh_token': 'tok789'} CHATGPT_CODEX_ACCESS_TOKEN=tok000"
    redacted = sanitize_error_text(raw)
    for value in ["secretABC", "tok123", "tok456", "tok789", "tok000"]:
        assert value not in redacted
    assert "[REDACTED]" in redacted


def test_cli_dry_run_json_no_auth_or_write(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    out = root / "nested" / "out.png"
    proc = run_cli(["robot painter", "--root", str(root), "--out", str(out), "--preset", "no-text", "--dry-run", "--json"], cwd=Path.cwd())
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["success"] is True
    assert payload["dry_run"] is True
    assert "robot painter" in payload["final_prompt"]
    assert not out.parent.exists()


def test_cli_default_is_dry_run(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    proc = run_cli(["robot", "--root", str(root), "--json"], cwd=Path.cwd())
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["dry_run"] is True


def test_cli_missing_token_live_fails_cleanly(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    proc = run_cli(["robot", "--root", str(root), "--live", "--json"], cwd=Path.cwd(), env={"CHATGPT_CODEX_ACCESS_TOKEN": ""})
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["success"] is False
    assert "traceback" not in proc.stderr.lower()


def test_receipt_excludes_prompt_by_default(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    receipt = root / "receipt.json"
    proc = run_cli(["private prompt text", "--root", str(root), "--receipt", str(receipt), "--dry-run", "--json"], cwd=Path.cwd())
    assert proc.returncode == 0
    data = json.loads(receipt.read_text())
    assert "prompt" not in data
    assert data["prompt_sha256"]


def test_receipt_can_include_prompt_explicitly(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    receipt = root / "receipt.json"
    proc = run_cli(["public prompt text", "--root", str(root), "--receipt", str(receipt), "--include-prompt-in-receipt", "--dry-run"], cwd=Path.cwd())
    assert proc.returncode == 0
    data = json.loads(receipt.read_text())
    assert data["prompt"].startswith("public prompt text")



def jpg(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 16)
    return path


def test_ref_magic_bytes_reject_fake_png(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    fake = root / "fake.png"
    fake.write_text("not an image", encoding="utf-8")
    with pytest.raises(f.PolicyError):
        f.validate_refs([fake], root=root, allow_outside=False)


def test_cli_add_identity_then_use_it_in_dry_run(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    ref = png(root / "me.png")
    proc = run_cli(["--root", str(root), "--add-identity", "me", "--ref", str(ref), "--json"], cwd=Path.cwd())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    created = json.loads(proc.stdout)
    assert created["created"] == "identity"
    proc = run_cli(["make image with me", "--root", str(root), "--identity", "me", "--preset", "likeness", "--dry-run", "--json"], cwd=Path.cwd())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["refs_count"] == 1
    assert "Saved identity pack selected: me" in payload["final_prompt"]


def test_cli_add_style_then_use_it_with_refs(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    ref = jpg(root / "style.jpg")
    proc = run_cli(["--root", str(root), "--add-style", "dark-brand", "--style-prompt", "dark graphite palette", "--style-preset", "brand-style", "--ref", str(ref), "--json"], cwd=Path.cwd())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    proc = run_cli(["product poster", "--root", str(root), "--style", "dark-brand", "--dry-run", "--json"], cwd=Path.cwd())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["refs_count"] == 1
    assert "dark graphite palette" in payload["final_prompt"]
    assert "Saved style pack selected: dark-brand" in payload["final_prompt"]


def test_cli_edit_image_adds_edit_guidance_and_ref(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    base = png(root / "base.png")
    proc = run_cli(["--root", str(root), "--edit-image", str(base), "--edit", "remove the background and keep the face", "--dry-run", "--json"], cwd=Path.cwd())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["refs_count"] == 1
    assert "Treat the supplied edit/base image" in payload["final_prompt"]
    assert payload["receipt"]["edit_image"] == str(base)


def test_list_library(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    ref = png(root / "me.png")
    assert run_cli(["--root", str(root), "--add-identity", "me", "--ref", str(ref)], cwd=Path.cwd()).returncode == 0
    proc = run_cli(["--root", str(root), "--list-library", "--json"], cwd=Path.cwd())
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["library"]["identities"] == ["me"]
