from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate

from gpt_image2_agent import cli
from gpt_image2_agent.library import save_identity, save_style


def no_live_call(**kwargs):
    pytest.fail("dry-run or invalid options must not read auth or call the backend")


@pytest.mark.parametrize("model", ["gpt-image-2.5-sunburst", "gpt-image-2.5-flare"])
@pytest.mark.parametrize("quality", ["xhigh", "max", "auto"])
def test_new_options_are_planned_without_auth_network_or_image_writes(model, quality, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "read_token", no_live_call)
    monkeypatch.setattr(cli, "generate_image", no_live_call)
    out = tmp_path / "nested" / "out.png"
    assert cli.main([
        "glass sculpture", "--root", str(tmp_path), "--out", str(out),
        "--image-model", model, "--quality", quality, "--size", "1536x864",
        "--aspect", "portrait", "--background", "transparent", "--json",
    ]) == 0
    result = json.loads(capsys.readouterr().out)
    receipt = result["receipt"]
    assert receipt["image_model"] == model
    assert receipt["quality"] == quality
    assert receipt["size"] == "1536x864"
    assert receipt["aspect"] == "custom"
    assert receipt["background"] == "transparent"
    assert receipt["output_format"] == "png"
    assert receipt["action"] == "auto"
    validate(receipt, json.loads(Path("schemas/receipt.v1.schema.json").read_text()))
    assert list(tmp_path.iterdir()) == []


def test_default_model_and_compatible_defaults(tmp_path, capsys):
    assert cli.main(["robot", "--root", str(tmp_path), "--json"]) == 0
    receipt = json.loads(capsys.readouterr().out)["receipt"]
    assert receipt["image_model"] == "gpt-image-2.5-sunburst"
    assert receipt["host_model"] == "gpt-5.5"
    assert receipt["quality"] == "medium"
    assert receipt["background"] == "opaque"
    assert receipt["size"] == "1536x1024"
    assert receipt["aspect"] == "landscape"
    assert Path(receipt["output_path"]).parent == tmp_path / "generated" / "gpt-image-2"


@pytest.mark.parametrize("size, aspect", [("auto", "auto"), ("2160x3840", "custom")])
def test_size_auto_and_portrait_4k_receipt(size, aspect, tmp_path, capsys):
    assert cli.main(["robot", "--root", str(tmp_path), "--size", size, "--json"]) == 0
    receipt = json.loads(capsys.readouterr().out)["receipt"]
    assert receipt["size"] == size
    assert receipt["aspect"] == aspect
    validate(receipt, json.loads(Path("schemas/receipt.v1.schema.json").read_text()))


@pytest.mark.parametrize("options", [
    ["--image-model", "gpt-image-2", "--quality", "max"],
    ["--image-model", "gpt-image-2", "--quality", "xhigh"],
    ["--size", "1025x1024"],
    ["--size", "3840x3840"],
    ["--size", "0x1024"],
])
def test_invalid_options_fail_before_live_side_effects(options, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "read_token", no_live_call)
    monkeypatch.setattr(cli, "generate_image", no_live_call)
    assert cli.main([
        "robot", "--root", str(tmp_path), "--out", str(tmp_path / "nested" / "out.png"),
        "--receipt", str(tmp_path / "receipt.json"), "--live", "--json", *options,
    ]) == 2
    assert json.loads(capsys.readouterr().out)["success"] is False
    assert list(tmp_path.iterdir()) == []


def test_legacy_model_remains_selectable(tmp_path, capsys):
    assert cli.main(["robot", "--root", str(tmp_path), "--image-model", "gpt-image-2", "--quality", "high", "--json"]) == 0
    receipt = json.loads(capsys.readouterr().out)["receipt"]
    assert receipt["image_model"] == "gpt-image-2"
    assert receipt["quality"] == "high"


def test_markdown_shows_requested_models_and_new_options(tmp_path, capsys):
    assert cli.main([
        "robot", "--root", str(tmp_path), "--image-model", "gpt-image-2.5-flare",
        "--host-model", "configured-host", "--quality", "max", "--size", "auto",
        "--background", "transparent", "--review-markdown",
    ]) == 0
    report = capsys.readouterr().out
    for text in ["Image model:** gpt-image-2.5-flare", "Host model:** configured-host", "Quality:** max", "Size:** auto", "Background:** transparent"]:
        assert text in report


def test_edit_requires_base_image(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "read_token", no_live_call)
    monkeypatch.setattr(cli, "generate_image", no_live_call)
    assert cli.main(["--edit", "change background", "--root", str(tmp_path), "--live", "--json"]) == 2
    assert "--edit-image" in json.loads(capsys.readouterr().out)["error"]
    assert list(tmp_path.iterdir()) == []


def test_live_edit_forwards_same_options_as_receipt_and_base_first(monkeypatch, tmp_path, capsys):
    refs = []
    for name in ["base", "identity", "style", "extra"]:
        ref = tmp_path / f"{name}.png"
        ref.write_bytes(b"\x89PNG\r\n\x1a\n" + name.encode())
        refs.append(ref)
    save_identity(tmp_path, "person", [refs[1]])
    save_style(tmp_path, "brand", prompt="blue palette", refs=[refs[2]])
    sent = {}

    def fake_generate(**kwargs):
        sent.update(kwargs)
        kwargs["out"].write_bytes(b"\x89PNG\r\n\x1a\nmock")
        return kwargs["out"]

    monkeypatch.setattr(cli, "read_token", lambda **kwargs: "mock-token")
    monkeypatch.setattr(cli, "generate_image", fake_generate)
    receipt_path = tmp_path / "receipt.json"
    assert cli.main([
        "--edit", "replace the background", "--edit-image", str(refs[0]),
        "--identity", "person", "--style", "brand", "--ref", str(refs[3]),
        "--root", str(tmp_path), "--image-model", "gpt-image-2.5-flare", "--quality", "xhigh",
        "--size", "1536x864", "--background", "transparent", "--receipt", str(receipt_path),
        "--live", "--json",
    ]) == 0
    result = json.loads(capsys.readouterr().out)
    receipt = json.loads(receipt_path.read_text())
    assert result["receipt"] == receipt
    assert receipt["status"] == "success"
    for key in ["image_model", "host_model", "quality", "size", "background", "action"]:
        assert sent[key] == receipt[key]
    assert sent["action"] == "edit"
    assert sent["refs"][0] == refs[0]
    assert [r.read_bytes() for r in sent["refs"]] == [r.read_bytes() for r in refs]
    assert [r["path"] for r in receipt["refs"]] == [str(r) for r in sent["refs"]]
    assert "first supplied image" in sent["prompt"]
    validate(receipt, json.loads(Path("schemas/receipt.v1.schema.json").read_text()))


def test_existing_receipt_v1_still_valid_without_new_fields(tmp_path, capsys):
    assert cli.main(["robot", "--root", str(tmp_path), "--image-model", "gpt-image-2", "--json"]) == 0
    receipt = json.loads(capsys.readouterr().out)["receipt"]
    for key in ["background", "output_format", "action"]:
        receipt.pop(key)
    validate(receipt, json.loads(Path("schemas/receipt.v1.schema.json").read_text()))
