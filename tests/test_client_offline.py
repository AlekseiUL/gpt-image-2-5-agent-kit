from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from gpt_image2_agent import client


class FakeResponse:
    def __init__(self, lines, status_code=200, text=""):
        self._lines = lines
        self.status_code = status_code
        self.text = text

    def iter_lines(self):
        yield from self._lines

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            request = httpx.Request("POST", "https://example.test")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("boom", request=request, response=response)

    def read(self):
        return self.text.encode()


class StreamCtx:
    def __init__(self, response):
        self.response = response

    def __enter__(self):
        return self.response

    def __exit__(self, *exc):
        return False


class FakeClient:
    response = None
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def stream(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return StreamCtx(self.response)


@pytest.fixture
def fake_backend(monkeypatch):
    monkeypatch.setattr(FakeClient, "calls", [])
    monkeypatch.setattr(FakeClient, "response", None)
    monkeypatch.setattr("httpx.Client", FakeClient)
    return FakeClient


def sse_events(*events):
    return FakeResponse([line for event in events for line in (f"data: {json.dumps(event)}", "")])


def generate(tmp_path, **options):
    return client.generate_image(
        prompt="x", refs=options.pop("refs", []), out=tmp_path / "out.png", token="tok",
        host_model="gpt-5.5", quality=options.pop("quality", "medium"), aspect="square",
        timeout=1, overwrite=options.pop("overwrite", False), **options,
    )


def test_generate_image_success_mocked_sse(monkeypatch, tmp_path):
    png = b"\x89PNG\r\n\x1a\nok"
    b64 = base64.b64encode(png).decode()
    FakeClient.response = FakeResponse([f'data: {{"type":"image_generation_call","result":"{b64}"}}', ""])
    monkeypatch.setattr("httpx.Client", FakeClient)
    out = tmp_path / "out.png"
    result = client.generate_image(prompt="x", refs=[], out=out, token="tok", host_model="gpt-5.5", quality="low", aspect="square", timeout=1, overwrite=False)
    assert result == out
    assert out.read_bytes() == png


def test_generate_image_http_error_redacts(monkeypatch, tmp_path):
    FakeClient.response = FakeResponse([], status_code=401, text="Authorization: Bearer SECRET access_token=tok123")
    monkeypatch.setattr("httpx.Client", FakeClient)
    with pytest.raises(client.ClientError) as exc:
        client.generate_image(prompt="x", refs=[], out=tmp_path / "out.png", token="tok", host_model="gpt-5.5", quality="low", aspect="square", timeout=1, overwrite=False)
    assert "SECRET" not in str(exc.value)
    assert "tok123" not in str(exc.value)
    assert "[REDACTED]" in str(exc.value)


def test_generate_image_invalid_base64(monkeypatch, tmp_path):
    FakeClient.response = FakeResponse(['data: {"type":"image_generation_call","result":"not-base64"}', ""])
    monkeypatch.setattr("httpx.Client", FakeClient)
    with pytest.raises(client.ClientError, match="invalid base64"):
        client.generate_image(prompt="x", refs=[], out=tmp_path / "out.png", token="tok", host_model="gpt-5.5", quality="low", aspect="square", timeout=1, overwrite=False)
    assert not (tmp_path / "out.png").exists()


def test_generate_image_no_image(monkeypatch, tmp_path):
    FakeClient.response = FakeResponse(['data: {"type":"response.completed"}', ""])
    monkeypatch.setattr("httpx.Client", FakeClient)
    with pytest.raises(client.ClientError, match="no image_generation"):
        client.generate_image(prompt="x", refs=[], out=tmp_path / "out.png", token="tok", host_model="gpt-5.5", quality="low", aspect="square", timeout=1, overwrite=False)


@pytest.mark.parametrize("image_model", ["gpt-image-2.5-sunburst", "gpt-image-2.5-flare"])
@pytest.mark.parametrize("quality", ["xhigh", "max", "auto"])
def test_selected_model_options_reach_mocked_request(fake_backend, tmp_path, image_model, quality):
    png = b"\x89PNG\r\n\x1a\nfinal"
    fake_backend.response = sse_events({
        "type": "response.completed",
        "response": {"status": "completed", "output": [
            {"type": "image_generation_call", "status": "completed", "result": base64.b64encode(png).decode()},
        ]},
    })
    out = generate(tmp_path, image_model=image_model, quality=quality, size="2048x1024", background="transparent")
    assert out.read_bytes() == png
    assert len(fake_backend.calls) == 1
    args, kwargs = fake_backend.calls[0]
    assert args == ("POST", f"{client.CODEX_BASE_URL}/responses")
    payload = kwargs["json"]
    assert payload["model"] == "gpt-5.5"
    assert payload["tools"] == [{
        "type": "image_generation", "model": image_model, "size": "2048x1024", "quality": quality,
        "output_format": "png", "background": "transparent", "action": "auto", "partial_images": 1,
    }]
    assert "input_fidelity" not in json.dumps(payload)


def test_payload_defaults_and_auto_size():
    payload = client.build_payload("x", host_model="gpt-5.5", quality="medium", aspect="portrait", refs=[])
    assert payload["tools"][0]["model"] == client.API_IMAGE_MODEL == "gpt-image-2.5-sunburst"
    assert payload["tools"][0]["size"] == "1024x1536"
    assert payload["tools"][0]["background"] == "opaque"
    auto = client.build_payload("x", host_model="gpt-5.5", quality="auto", aspect="portrait", refs=[], size="auto", background="auto")
    assert auto["tools"][0]["size"] == "auto"
    assert auto["tools"][0]["background"] == "auto"


@pytest.mark.parametrize("options", [
    {"image_model": "gpt-image-2", "quality": "xhigh"},
    {"image_model": "gpt-image-2", "quality": "max"},
    {"image_model": "unsupported"},
    {"quality": "ultra"},
    {"size": "512x512"},
    {"background": "blue"},
    {"action": "unsupported"},
])
def test_invalid_options_fail_before_reading_refs_or_network(monkeypatch, fake_backend, tmp_path, options):
    def refuse_ref_read(ref):
        pytest.fail("Invalid options must be rejected before reading references")

    monkeypatch.setattr(client, "ref_to_data_url", refuse_ref_read)
    with pytest.raises(ValueError):
        generate(tmp_path, refs=[tmp_path / "missing.png"], **options)
    assert fake_backend.calls == []
    assert not (tmp_path / "out.png").exists()


def test_edit_action_requires_input_before_network(fake_backend, tmp_path):
    with pytest.raises(ValueError, match="requires at least one input image"):
        generate(tmp_path, action="edit")
    assert fake_backend.calls == []


def test_edit_payload_keeps_input_image_order(tmp_path):
    base = tmp_path / "base.png"
    reference = tmp_path / "reference.png"
    base.write_bytes(b"\x89PNG\r\n\x1a\nbase")
    reference.write_bytes(b"\x89PNG\r\n\x1a\nreference")
    payload = client.build_payload("edit x", host_model="gpt-5.5", quality="high", aspect="square", refs=[base, reference], action="edit")
    assert payload["tools"][0]["action"] == "edit"
    content = payload["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "edit x"}
    assert content[1]["image_url"] == client.ref_to_data_url(base)
    assert content[2]["image_url"] == client.ref_to_data_url(reference)


@pytest.mark.parametrize("failure", [
    {"type": "response.failed", "response": {"status": "failed", "error": {"message": "Bearer SECRET access_token=tok123"}}},
    {"type": "response.incomplete", "response": {"status": "incomplete", "incomplete_details": {"reason": "Bearer SECRET access_token=tok123"}}},
    {"type": "error", "message": "Bearer SECRET access_token=tok123"},
    {"type": "response.error", "error": {"message": "Bearer SECRET access_token=tok123"}},
    {"type": "response.completed", "response": {"status": "failed", "error": {"message": "Bearer SECRET access_token=tok123"}}},
])
def test_partial_then_failure_never_writes_image(fake_backend, tmp_path, failure):
    partial = base64.b64encode(b"\x89PNG\r\n\x1a\npartial").decode()
    fake_backend.response = sse_events({"type": "response.image_generation_call.partial_image", "partial_image_b64": partial}, failure)
    with pytest.raises(client.ClientError, match="backend stream failed") as exc:
        generate(tmp_path)
    assert "SECRET" not in str(exc.value)
    assert "tok123" not in str(exc.value)
    assert "[REDACTED]" in str(exc.value)
    assert not (tmp_path / "out.png").exists()


def test_partial_without_final_result_is_not_success(fake_backend, tmp_path):
    partial = base64.b64encode(b"\x89PNG\r\n\x1a\npartial").decode()
    fake_backend.response = sse_events(
        {"type": "response.image_generation_call.partial_image", "partial_image_b64": partial},
        {"type": "response.completed", "response": {"status": "completed", "output": []}},
    )
    with pytest.raises(client.ClientError, match="no image_generation result"):
        generate(tmp_path)
    assert not (tmp_path / "out.png").exists()


@pytest.mark.parametrize("status", ["in_progress", "failed", "incomplete"])
def test_nonfinal_image_call_is_not_success(fake_backend, tmp_path, status):
    fake_backend.response = sse_events({"type": "image_generation_call", "status": status, "result": base64.b64encode(b"\x89PNG\r\n\x1a\npreview").decode()})
    with pytest.raises(client.ClientError, match="no image_generation result"):
        generate(tmp_path)
    assert not (tmp_path / "out.png").exists()


def test_final_result_survives_later_preview(fake_backend, tmp_path):
    png = b"\x89PNG\r\n\x1a\nfinal"
    fake_backend.response = sse_events(
        {"type": "response.output_item.done", "item": {"type": "image_generation_call", "status": "completed", "result": base64.b64encode(png).decode()}},
        {"type": "response.image_generation_call.partial_image", "partial_image_b64": base64.b64encode(b"\x89PNG\r\n\x1a\npartial").decode()},
        {"type": "response.completed"},
    )
    assert generate(tmp_path).read_bytes() == png


def test_failed_stream_after_final_keeps_existing_output(fake_backend, tmp_path):
    out = tmp_path / "out.png"
    previous = b"\x89PNG\r\n\x1a\nprevious"
    out.write_bytes(previous)
    fake_backend.response = sse_events(
        {"type": "response.output_item.done", "item": {"type": "image_generation_call", "status": "completed", "result": base64.b64encode(b"\x89PNG\r\n\x1a\nnew").decode()}},
        {"type": "response.failed", "response": {"status": "failed", "error": {"message": "generation failed"}}},
    )
    with pytest.raises(client.ClientError, match="backend stream failed"):
        generate(tmp_path, overwrite=True)
    assert out.read_bytes() == previous
