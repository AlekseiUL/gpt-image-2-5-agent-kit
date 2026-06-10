from __future__ import annotations

import base64
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

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def stream(self, *args, **kwargs):
        return StreamCtx(self.response)


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
