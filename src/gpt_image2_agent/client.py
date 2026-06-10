from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Iterable

from .files import atomic_write_png, ref_to_data_url
from .redaction import sanitize_error_text

CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
API_IMAGE_MODEL = "gpt-image-2"
DEFAULT_HOST_MODEL = "gpt-5.5"
SIZES = {"landscape": "1536x1024", "square": "1024x1024", "portrait": "1024x1536"}
QUALITIES = {"low", "medium", "high"}

class ClientError(RuntimeError):
    pass


def build_payload(prompt: str, *, host_model: str, quality: str, aspect: str, refs: list[Path]) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    for ref in refs:
        content.append({"type": "input_image", "image_url": ref_to_data_url(ref), "detail": "auto"})
    return {
        "model": host_model,
        "store": False,
        "instructions": "Use the image_generation tool. Preserve supplied reference identity/style only when requested by the prompt.",
        "input": [{"type": "message", "role": "user", "content": content}],
        "tools": [{"type": "image_generation", "model": API_IMAGE_MODEL, "size": SIZES[aspect], "quality": quality, "output_format": "png", "background": "opaque", "partial_images": 1}],
        "tool_choice": {"type": "allowed_tools", "mode": "required", "tools": [{"type": "image_generation"}]},
        "stream": True,
    }


def iter_sse_json(response: Any) -> Iterable[dict[str, Any]]:
    event_name = None
    data_lines: list[str] = []
    def flush() -> dict[str, Any] | None:
        nonlocal event_name, data_lines
        if not data_lines:
            event_name = None
            return None
        raw = "\n".join(data_lines).strip()
        event = event_name
        event_name = None
        data_lines = []
        if not raw or raw == "[DONE]":
            return None
        payload = json.loads(raw)
        if isinstance(payload, dict) and event and "type" not in payload:
            payload["type"] = event
        return payload if isinstance(payload, dict) else {"value": payload}
    for line in response.iter_lines():
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="replace")
        line = str(line)
        if line == "":
            payload = flush()
            if payload is not None:
                yield payload
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:"):].lstrip())
    payload = flush()
    if payload is not None:
        yield payload


def extract_image_b64(value: Any) -> str | None:
    found = None
    if isinstance(value, dict):
        if value.get("type") == "image_generation_call" and isinstance(value.get("result"), str):
            found = value["result"]
        if isinstance(value.get("partial_image_b64"), str):
            found = value["partial_image_b64"]
        item = value.get("item")
        if isinstance(item, dict) and item.get("type") == "image_generation_call" and isinstance(item.get("result"), str):
            found = item["result"]
        for child in value.values():
            nested = extract_image_b64(child)
            if nested:
                found = nested
    elif isinstance(value, list):
        for child in value:
            nested = extract_image_b64(child)
            if nested:
                found = nested
    return found


def generate_image(*, prompt: str, refs: list[Path], out: Path, token: str, host_model: str, quality: str, aspect: str, timeout: float, overwrite: bool) -> Path:
    import httpx
    headers = {"Accept": "text/event-stream", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = build_payload(prompt, host_model=host_model, quality=quality, aspect=aspect, refs=refs)
    image_b64 = None
    timeout_cfg = httpx.Timeout(timeout, connect=30.0, read=timeout, write=30.0, pool=30.0)
    try:
        with httpx.Client(timeout=timeout_cfg, headers=headers) as http:
            with http.stream("POST", f"{CODEX_BASE_URL}/responses", json=payload) as response:
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    exc.response.read()
                    raise ClientError(f"backend HTTP {exc.response.status_code}: {sanitize_error_text(exc.response.text)}") from exc
                for event in iter_sse_json(response):
                    found = extract_image_b64(event)
                    if found:
                        image_b64 = found
    except ClientError:
        raise
    except Exception as exc:
        raise ClientError(sanitize_error_text(f"backend request failed: {type(exc).__name__}: {exc}")) from exc
    if not image_b64:
        raise ClientError("backend returned no image_generation result")
    try:
        data = base64.b64decode(image_b64, validate=True)
    except Exception as exc:
        raise ClientError("backend returned invalid base64 image data") from exc
    atomic_write_png(out, data, overwrite=overwrite)
    return out
