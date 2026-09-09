from __future__ import annotations

import base64
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .files import atomic_write_image, ref_to_data_url, validate_mask
from .models import DEFAULT_IMAGE_MODEL, resolve_size, validate_image_options
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
    output_format: str = "png", output_compression: int | None = None,
    mask: Path | None = None,
) -> dict[str, Any]:
    resolved_size = resolve_size(aspect, size)
    validate_image_options(image_model=image_model, quality=quality, size=resolved_size,
                           background=background, output_format=output_format,
                           output_compression=output_compression)
    if action not in {"auto", "generate", "edit"}:
        raise ValueError("Action must be auto, generate, or edit.")
    if action == "edit" and not refs:
        raise ValueError("The edit action requires at least one input image.")
    if mask is not None and action != "edit":
        raise ValueError("A mask requires action='edit' and a base image as the first input.")
    if mask is not None:
        mask = validate_mask(mask, refs[0])
    content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    for ref in refs:
        content.append({"type": "input_image", "image_url": ref_to_data_url(ref), "detail": "auto"})
    tool: dict[str, Any] = {
        "type": "image_generation", "model": image_model, "size": resolved_size,
        "quality": quality, "output_format": output_format, "background": background,
        # The CLI publishes only the final validated image. Asking for partial
        # previews would add output-token cost without exposing any benefit.
        "action": action, "partial_images": 0,
    }
    if output_compression is not None:
        tool["output_compression"] = output_compression
    if mask is not None:
        tool["input_image_mask"] = {"image_url": ref_to_data_url(mask)}
    return {
        "model": host_model,
        "store": False,
        "instructions": "Use the image_generation tool. Follow the requested medium, composition, exact text, and numbered reference roles. Preserve supplied identity, style, and edit details only as requested by the prompt.",
        "input": [{"type": "message", "role": "user", "content": content}],
        "tools": [tool],
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
                and value.get("status") == "completed"
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
    failed_statuses = {"failed", "incomplete", "cancelled", "canceled", "error"}
    for node in _objects(event):
        event_type = str(node.get("type", ""))
        status = node.get("status")
        if event_type.rsplit(".", 1)[-1] not in failed_statuses and status not in failed_statuses:
            continue
        response = node.get("response")
        response = response if isinstance(response, dict) else {}
        detail = (response.get("error") or response.get("incomplete_details")
                  or node.get("error") or node.get("incomplete_details")
                  or node.get("message") or node.get("code"))
        description = str(event_type or status)
        if detail:
            description += f": {json.dumps(detail, ensure_ascii=False)}"
        raise ClientError(sanitize_error_text(f"backend stream failed: {description}"))


def _objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _objects(child)


class _ImageStreamState:
    """Reconcile final call events without promoting previews or truncated streams."""

    def __init__(self) -> None:
        self.completed = False
        self.call_ids: set[str] = set()
        self.statuses: dict[str | None, str | None] = {}
        self.results: dict[str | None, str] = {}

    def consume(self, event: dict[str, Any]) -> None:
        _raise_stream_error(event)
        event_type = event.get("type")
        terminal = event_type == "response.completed"
        if terminal:
            response = event.get("response")
            if not isinstance(response, dict) or response.get("status") != "completed":
                raise ClientError("backend response.completed lacks a completed response status")
            self.completed = True
            calls = _objects(response.get("output", []))
        elif event_type in {"response.output_item.added", "response.output_item.done"}:
            calls = _objects(event.get("item", {}))
        else:
            return
        for call in calls:
            if call.get("type") != "image_generation_call":
                continue
            call_id = call.get("id")
            call_id = call_id if isinstance(call_id, str) and call_id else None
            if call_id is not None:
                self.call_ids.add(call_id)
                if len(self.call_ids) > 1:
                    raise ClientError("backend returned multiple image_generation calls; a single output is required")
            status = call.get("status")
            self.statuses[call_id] = status
            if terminal and status != "completed":
                raise ClientError("backend completed with a non-completed image_generation call")
            if (terminal or event_type == "response.output_item.done") and status == "completed":
                result = call.get("result")
                if isinstance(result, str) and result:
                    previous = self.results.get(call_id)
                    if previous is not None and previous != result:
                        raise ClientError("backend returned conflicting image_generation results; a single output is required")
                    self.results[call_id] = result

    def final_result(self) -> str:
        if not self.completed:
            raise ClientError("backend stream ended without response.completed")
        if any(status != "completed" for status in self.statuses.values()):
            raise ClientError("backend returned a non-completed image_generation call")
        results = set(self.results.values())
        if len(results) > 1:
            raise ClientError("backend returned multiple image_generation results; a single output is required")
        if not results:
            raise ClientError("backend returned no image_generation result")
        return results.pop()


def generate_image(
    *, prompt: str, refs: list[Path], out: Path, token: str, host_model: str,
    quality: str, aspect: str, timeout: float, overwrite: bool,
    image_model: str = DEFAULT_IMAGE_MODEL, size: str | None = None,
    background: str = "opaque", action: str = "auto",
    output_format: str = "png", output_compression: int | None = None,
    mask: Path | None = None,
) -> Path:
    import httpx
    headers = {"Accept": "text/event-stream", "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = build_payload(prompt, host_model=host_model, quality=quality, aspect=aspect, refs=refs,
                            image_model=image_model, size=size, background=background, action=action,
                            output_format=output_format, output_compression=output_compression, mask=mask)
    state = _ImageStreamState()
    timeout_cfg = httpx.Timeout(timeout, connect=30.0, read=timeout, write=30.0, pool=30.0)
    try:
        with (
            httpx.Client(timeout=timeout_cfg, headers=headers) as client_http,
            client_http.stream("POST", f"{CODEX_BASE_URL}/responses", json=payload) as response,
        ):
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                exc.response.read()
                raise ClientError(f"backend HTTP {exc.response.status_code}: {sanitize_error_text(exc.response.text)}") from exc
            for event in iter_sse_json(response):
                state.consume(event)
    except ClientError:
        raise
    except Exception as exc:
        raise ClientError(sanitize_error_text(f"backend request failed: {type(exc).__name__}: {exc}")) from exc
    image_b64 = state.final_result()
    try:
        data = base64.b64decode(image_b64, validate=True)
    except Exception as exc:
        raise ClientError("backend returned invalid base64 image data") from exc
    atomic_write_image(out, data, output_format=output_format, overwrite=overwrite)
    return out
