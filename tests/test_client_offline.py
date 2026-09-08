from __future__ import annotations

import base64
import io
import json

import pytest
from PIL import Image

from gpt_image25_agent import client
from gpt_image25_agent.files import PolicyError


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


def encoded_image(output_format="png", color="red"):
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color).save(buffer, format=output_format.upper())
    return buffer.getvalue()


def image_call(data=None, *, call_id="ig_1", status="completed", result=None):
    call = {"type": "image_generation_call", "status": status}
    if call_id is not None:
        call["id"] = call_id
    if data is not None:
        call["result"] = base64.b64encode(data).decode()
    elif result is not None:
        call["result"] = result
    return call


def completed(*calls, status="completed"):
    return {"type": "response.completed", "response": {"status": status, "output": list(calls)}}


def done(call):
    return {"type": "response.output_item.done", "item": call}


def preview():
    return {"type": "response.image_generation_call.partial_image", "partial_image_b64": base64.b64encode(encoded_image(color="blue")).decode()}


def sse_events(*events):
    return FakeResponse([line for event in events for line in (f"data: {json.dumps(event)}", "")])


def generate(tmp_path, **options):
    extension = "jpg" if options.get("output_format") == "jpeg" else options.get("output_format", "png")
    return client.generate_image(
        prompt="x", refs=options.pop("refs", []), out=tmp_path / f"out.{extension}", token="tok",
        host_model="gpt-5.5", quality=options.pop("quality", "medium"), aspect="square",
        timeout=1, overwrite=options.pop("overwrite", False), **options,
    )


@pytest.mark.parametrize("output_format,compression", [("png", None), ("jpeg", 0), ("webp", 100)])
def test_generate_image_success_mocked_sse(fake_backend, tmp_path, output_format, compression):
    data = encoded_image(output_format)
    fake_backend.response = sse_events(completed(image_call(data)))
    out = generate(tmp_path, output_format=output_format, output_compression=compression)
    assert out.read_bytes() == data
    tool = fake_backend.calls[0][1]["json"]["tools"][0]
    assert tool["output_format"] == output_format
    if compression is None:
        assert "output_compression" not in tool
    else:
        assert tool["output_compression"] == compression


def test_generate_image_http_error_redacts(fake_backend, tmp_path):
    fake_backend.response = FakeResponse([], status_code=401, text="Authorization: Bearer SECRET access_token=tok123")
    with pytest.raises(client.ClientError) as exc:
        generate(tmp_path)
    assert "SECRET" not in str(exc.value)
    assert "tok123" not in str(exc.value)
    assert "[REDACTED]" in str(exc.value)


def test_generate_image_invalid_base64(fake_backend, tmp_path):
    fake_backend.response = sse_events(completed(image_call(result="not-base64")))
    with pytest.raises(client.ClientError, match="invalid base64"):
        generate(tmp_path)
    assert not (tmp_path / "out.png").exists()


def test_generate_image_invalid_decoded_image(fake_backend, tmp_path):
    fake_backend.response = sse_events(completed(image_call(b"\x89PNG\r\n\x1a\ntruncated")))
    with pytest.raises(PolicyError, match="fully decodable"):
        generate(tmp_path)
    assert not (tmp_path / "out.png").exists()


def test_generate_image_no_image(fake_backend, tmp_path):
    fake_backend.response = sse_events(completed())
    with pytest.raises(client.ClientError, match="no image_generation"):
        generate(tmp_path)


@pytest.mark.parametrize("image_model", ["gpt-image-2.5-sunburst", "gpt-image-2.5-flare"])
@pytest.mark.parametrize("quality", ["xhigh", "max", "auto"])
def test_selected_model_options_reach_mocked_request(fake_backend, tmp_path, image_model, quality):
    png = encoded_image()
    fake_backend.response = sse_events(completed(image_call(png)))
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
    {"image_model": "gpt-image-2", "quality": "medium"},
    {"image_model": "unsupported"},
    {"quality": "ultra"},
    {"size": "512x512"},
    {"background": "blue"},
    {"action": "unsupported"},
    {"output_format": "gif"},
    {"output_compression": 80},
    {"output_format": "webp", "output_compression": -1},
    {"output_format": "jpeg", "output_compression": True},
    {"output_format": "jpeg", "background": "transparent"},
])
def test_invalid_options_fail_before_reading_refs_or_network(monkeypatch, fake_backend, tmp_path, options):
    def refuse_ref_read(ref):
        pytest.fail("Invalid options must be rejected before reading references")

    monkeypatch.setattr(client, "ref_to_data_url", refuse_ref_read)
    with pytest.raises(ValueError):
        generate(tmp_path, refs=[tmp_path / "missing.png"], **options)
    assert fake_backend.calls == []
    assert not list(tmp_path.glob("out.*"))


def test_edit_action_requires_input_before_network(fake_backend, tmp_path):
    with pytest.raises(ValueError, match="requires at least one input image"):
        generate(tmp_path, action="edit")
    assert fake_backend.calls == []


def test_edit_payload_keeps_input_order_and_sends_mask(tmp_path):
    base, reference, mask = (tmp_path / name for name in ("base.png", "reference.png", "mask.png"))
    base.write_bytes(encoded_image())
    reference.write_bytes(encoded_image(color="blue"))
    Image.new("RGBA", (16, 16), (255, 255, 255, 0)).save(mask)
    payload = client.build_payload("edit x", host_model="gpt-5.5", quality="high", aspect="square", refs=[base, reference], action="edit", mask=mask)
    assert payload["tools"][0]["action"] == "edit"
    assert payload["tools"][0]["input_image_mask"] == {"image_url": client.ref_to_data_url(mask)}
    content = payload["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "edit x"}
    assert content[1]["image_url"] == client.ref_to_data_url(base)
    assert content[2]["image_url"] == client.ref_to_data_url(reference)
    assert len(content) == 3


@pytest.mark.parametrize("options", [{"action": "auto"}, {"action": "generate"}, {"action": "edit"}])
def test_mask_invalid_action_or_input_fails_before_network(fake_backend, tmp_path, options):
    with pytest.raises(ValueError):
        generate(tmp_path, mask=tmp_path / "missing-mask.png", **options)
    assert fake_backend.calls == []


def test_invalid_mask_blocks_before_reading_refs_or_network(monkeypatch, fake_backend, tmp_path):
    base, mask = tmp_path / "base.png", tmp_path / "mask.png"
    base.write_bytes(encoded_image())
    mask.write_bytes(encoded_image())
    monkeypatch.setattr(client, "ref_to_data_url", lambda ref: pytest.fail("Invalid mask must be rejected first"))
    with pytest.raises(PolicyError, match="alpha"):
        generate(tmp_path, refs=[base], action="edit", mask=mask)
    assert fake_backend.calls == []


@pytest.mark.parametrize("failure", [
    {"type": "response.failed", "response": {"status": "failed", "error": {"message": "Bearer SECRET access_token=tok123"}}},
    {"type": "response.incomplete", "response": {"status": "incomplete", "incomplete_details": {"reason": "Bearer SECRET access_token=tok123"}}},
    {"type": "response.cancelled", "message": "Bearer SECRET access_token=tok123"},
    {"type": "error", "message": "Bearer SECRET access_token=tok123"},
    {"type": "response.error", "error": {"message": "Bearer SECRET access_token=tok123"}},
    {"type": "response.image_generation_call.error", "error": {"message": "Bearer SECRET access_token=tok123"}},
    {"type": "response.completed", "response": {"status": "failed", "error": {"message": "Bearer SECRET access_token=tok123"}}},
    {"type": "response.completed", "response": {"status": "cancelled", "error": {"message": "Bearer SECRET access_token=tok123"}}},
    {"type": "custom", "status": "incomplete", "message": "Bearer SECRET access_token=tok123"},
])
@pytest.mark.parametrize("before", ["preview", "final", "completed"])
def test_failure_never_writes_cached_image(fake_backend, tmp_path, failure, before):
    out = tmp_path / "out.png"
    previous = encoded_image(color="green")
    out.write_bytes(previous)
    first = {"preview": preview(), "final": done(image_call(encoded_image())), "completed": completed(image_call(encoded_image()))}[before]
    fake_backend.response = sse_events(first, failure)
    with pytest.raises(client.ClientError, match="backend stream failed") as exc:
        generate(tmp_path, overwrite=True)
    assert "SECRET" not in str(exc.value)
    assert "tok123" not in str(exc.value)
    assert "[REDACTED]" in str(exc.value)
    assert out.read_bytes() == previous


def test_partial_without_final_result_is_not_success(fake_backend, tmp_path):
    fake_backend.response = sse_events(preview(), completed())
    with pytest.raises(client.ClientError, match="no image_generation result"):
        generate(tmp_path)
    assert not (tmp_path / "out.png").exists()


@pytest.mark.parametrize("last_event", [None, {"type": "response.completed"}, {"type": "response.completed", "response": {"status": "in_progress"}}])
def test_exact_response_completion_is_required(fake_backend, tmp_path, last_event):
    events = [done(image_call(encoded_image()))]
    if last_event is not None:
        events.append(last_event)
    fake_backend.response = sse_events(*events)
    with pytest.raises(client.ClientError, match="response.completed"):
        generate(tmp_path)
    assert not (tmp_path / "out.png").exists()


@pytest.mark.parametrize("status", [None, "in_progress", "failed", "incomplete", "cancelled", "canceled", "error"])
def test_nonfinal_call_cannot_reuse_cached_result(fake_backend, tmp_path, status):
    fake_backend.response = sse_events(done(image_call(encoded_image())), completed(image_call(status=status)))
    with pytest.raises(client.ClientError):
        generate(tmp_path)
    assert not (tmp_path / "out.png").exists()


def test_later_in_progress_call_invalidates_cached_result(fake_backend, tmp_path):
    fake_backend.response = sse_events(done(image_call(encoded_image())), done(image_call(status="in_progress")), completed())
    with pytest.raises(client.ClientError, match="non-completed"):
        generate(tmp_path)


@pytest.mark.parametrize("call_id", ["ig_1", None])
@pytest.mark.parametrize("terminal_result", ["empty_output", "missing", "empty", "repeat"])
def test_final_result_survives_empty_completion_and_later_preview(fake_backend, tmp_path, call_id, terminal_result):
    png = encoded_image()
    call = image_call(png, call_id=call_id)
    terminal = {"empty_output": completed(), "missing": completed(image_call(call_id=call_id)), "empty": completed(image_call(call_id=call_id, result="")), "repeat": completed(call)}[terminal_result]
    fake_backend.response = sse_events(done(call), preview(), terminal)
    assert generate(tmp_path).read_bytes() == png


@pytest.mark.parametrize("different_bytes", [False, True])
def test_multiple_call_ids_are_ambiguous(fake_backend, tmp_path, different_bytes):
    png = encoded_image()
    other = encoded_image(color="blue") if different_bytes else png
    fake_backend.response = sse_events(done(image_call(png)), completed(image_call(other, call_id="ig_2")))
    with pytest.raises(client.ClientError, match="multiple image_generation calls"):
        generate(tmp_path)
    assert not (tmp_path / "out.png").exists()


def test_distinct_results_without_ids_are_ambiguous(fake_backend, tmp_path):
    fake_backend.response = sse_events(done(image_call(encoded_image(), call_id=None)), completed(image_call(encoded_image(color="blue"), call_id=None)))
    with pytest.raises(client.ClientError, match="conflicting image_generation results"):
        generate(tmp_path)


def test_added_call_followed_by_done_and_terminal(fake_backend, tmp_path):
    png = encoded_image()
    fake_backend.response = sse_events(
        {"type": "response.output_item.added", "item": image_call(status="in_progress")},
        done(image_call(png)), completed(),
    )
    assert generate(tmp_path).read_bytes() == png


def test_bare_call_is_not_a_final_event(fake_backend, tmp_path):
    fake_backend.response = sse_events(image_call(encoded_image()), completed())
    with pytest.raises(client.ClientError, match="no image_generation result"):
        generate(tmp_path)
