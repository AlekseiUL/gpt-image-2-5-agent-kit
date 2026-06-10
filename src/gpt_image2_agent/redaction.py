from __future__ import annotations

import re
from typing import Any

SENSITIVE_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"(authorization\s*[:=]\s*)[^,;\n]+", re.IGNORECASE),
    re.compile(r"(cookie\s*[:=]\s*)[^\n]+", re.IGNORECASE),
    re.compile(r"([\"']?(?:access|refresh|id)_token[\"']?\s*[:=]\s*)[\"']?[^,}\]\s\"']+", re.IGNORECASE),
    re.compile(r"(CHATGPT_CODEX_ACCESS_TOKEN\s*=\s*)[^\s]+", re.IGNORECASE),
]


def sanitize_error_text(text: Any, *, limit: int = 1200) -> str:
    value = str(text or "")[:limit]
    for pattern in SENSITIVE_PATTERNS:
        value = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]" if match.groups() else "Bearer [REDACTED]", value)
    return value
