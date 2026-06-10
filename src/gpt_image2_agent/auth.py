from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .redaction import sanitize_error_text

class AuthError(RuntimeError):
    pass


def read_token(*, provider: str, token_env: str = "CHATGPT_CODEX_ACCESS_TOKEN", token_file: Path | None = None, token_command: str | None = None) -> str:
    if provider == "env":
        token = os.environ.get(token_env, "")
    elif provider == "file":
        if not token_file:
            raise AuthError("--token-file is required for file auth provider")
        token = token_file.expanduser().read_text(encoding="utf-8").strip()
    elif provider == "command":
        if not token_command:
            raise AuthError("--token-command is required for command auth provider")
        try:
            completed = subprocess.run(token_command, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False)
        except Exception as exc:
            raise AuthError(f"token command failed: {type(exc).__name__}") from exc
        if completed.returncode != 0:
            raise AuthError(f"token command exited {completed.returncode}: {sanitize_error_text(completed.stderr)}")
        token = completed.stdout.strip()
    else:
        raise AuthError(f"unknown auth provider: {provider}")
    if not token:
        raise AuthError(f"no token available from auth provider {provider}")
    return token
