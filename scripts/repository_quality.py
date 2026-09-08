from __future__ import annotations

import ast
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BAD_PATTERNS = {
    "private_path": re.compile(r"/Users/[^/\s]+|MIKE_CENTER|agents/jesse|mike-jesse", re.IGNORECASE),
    "token_literal": re.compile(r"(ghp_[A-Za-z0-9_]+|(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._~+/=-]{12,})"),
    "bytecode": re.compile(r"(__pycache__|\.pyc$)"),
}
SKIP_FILES = {"scripts/repository_quality.py", ".github/workflows/repository-quality.yml", ".gitignore"}
TEXT_EXTS = {".py", ".md", ".toml", ".yml", ".yaml", ".txt", ".json", ".gitignore"}

findings = []
# Scan release candidates, not ignored local credentials, virtualenvs or outputs.
if (ROOT / ".git").exists():
    names = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT).decode().split("\0")
    candidates = (ROOT / name for name in set(names) if name)
else:
    candidates = ROOT.rglob("*")
for path in candidates:
    rel = path.relative_to(ROOT).as_posix()
    if ".git" in path.parts or any(part in {"__pycache__", ".pytest_cache", "dist", "build", ".venv", "generated", ".gpt-image2-agent"} for part in path.parts):
        continue
    if path.is_file() and (path.suffix in {".pyc", ".pyo"}):
        findings.append(("bytecode", rel, 0, "bytecode file"))
        continue
    if path.is_file() and path.suffix == ".py":
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeError, OSError, ValueError) as exc:
            findings.append(("syntax", rel, 0, str(exc)))
    if not path.is_file() or (path.suffix not in TEXT_EXTS and path.name != ".gitignore") or rel in SKIP_FILES:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for i, line in enumerate(text.splitlines(), 1):
        for kind, rx in BAD_PATTERNS.items():
            if rx.search(line):
                findings.append((kind, rel, i, "matching content withheld"))
for item in findings[:80]:
    print(" | ".join(map(str, item)))
print("findings:", len(findings))
sys.exit(1 if findings else 0)
