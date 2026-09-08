from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Iterable

from .files import atomic_write_png, ref_to_data_url
from .models import BACKGROUNDS, DEFAULT_IMAGE_MODEL, IMAGE_MODELS, QUALITIES, SIZES, resolve_size, validate_image_options
from .redaction import sanitize_error_text

CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
API_IMAGE_MODEL = DEFAULT_IMAGE_MODEL
DEFAULT_HOST_MODEL = "gpt-5.5"

class ClientError(RuntimeError):
    pass


def build_payload(
    prompt: str, *, host_model: str, quality: str, aspect: str, refs: list[Path],
    image_model: str = DEFAULT_IMAGE_MODEL, size: str | None = None,
    background: str = "opaque", action: str = "auto",
) -> dict[str, Any]:
    resolved_size = resolve_size(aspect, size)
    validate_image_options(image_model=image_model, quality=quality, size=resolved_size, background=background)
    if action not in {"auto", "generate", "edit"}:
        raise ValueError("Action must be auto, generate, or edit.")
    if action == "edit" and not refs:
        raise ValueError("The edit action requires at least one input image.")
    content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    for ref in refs:
        content.append({"type": "input_image", "image_url": ref_to_data_url(ref), "detail": "auto"})
    return {
        "model": host_model,
        "store": False,
        "instructions": "Use the image_generation tool. Preserve supplied reference identity/style only when requested by the prompt.",
        "input": [{"type": "message", "role": "user", "content": content}],
        "tools": [{"type": "image_generation", "model": image_model, "size": resolved_size, "quality": quality, "output_format": "png", "background": background, "action": action, "partial_images": 1}],
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
    """Find a final image result; streamed preview images are never final output."""
    found = None
    if isinstance(value, dict):
        if (value.get("type") == "image_generation_call"
                and value.get("status") in {None, "completed"}
                and isinstance(value.get("result"), str)):
            found = value["result"]
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


def _raise_stream_error(event: dict[str, Any]) -> None:
    event_type = event.get("type")
    response = event.get("response")
    response = response if isinstance(response, dict) else {}
    status = response.get("status")
    if event_type not in {"response.failed", "response.incomplete", "response.error", "error"} and status not in {"failed", "incomplete"}:
        return
    detail = (response.get("error") or response.get("incomplete_details")
              or event.get("error") or event.get("message") or event.get("code"))
    description = str(event_type or status)
    if detail:
        description += f": {json.dumps(detail, ensure_ascii=False)}"
    raise ClientError(sanitize_error_text(f"backend stream failed: {description}"))


def generate_image(
    *, prompt: str, refs: list[Path], out: Path, token: str, host_model: str,
    quality: str, aspect: str, timeout: float, overwrite: bool,
    image_model: str = DEFAULT_IMAGE_MODEL, size: str | None = None,
    background: str = "opaque", action: str = "auto",
) -> Path:
    import httpx
    headers = {"Accept": "text/event-stream", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = build_payload(prompt, host_model=host_model, quality=quality, aspect=aspect, refs=refs,
                            image_model=image_model, size=size, background=background, action=action)
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
                    _raise_stream_error(event)
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
