from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BAD_PATTERNS = {
    "private_path": re.compile(r"/Users/[^/\s]+|MIKE_CENTER|agents/jesse|mike-jesse", re.I),
    "token_literal": re.compile(r"(ghp_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]+|Bearer\s+[A-Za-z0-9._~+/=-]{12,})"),
    "bytecode": re.compile(r"(__pycache__|\.pyc$)"),
}
SKIP_FILES = {"scripts/repository_quality.py", ".github/workflows/repository-quality.yml", ".gitignore"}
TEXT_EXTS = {".py", ".md", ".toml", ".yml", ".yaml", ".txt", ".gitignore"}

findings = []
for path in ROOT.rglob("*"):
    rel = path.relative_to(ROOT).as_posix()
    if ".git" in path.parts or any(part in {"__pycache__", ".pytest_cache", "dist", "build", ".venv"} for part in path.parts):
        continue
    if path.is_file() and (path.suffix in {".pyc", ".pyo"}):
        findings.append(("bytecode", rel, 0, "bytecode file"))
        continue
    if path.is_file() and path.suffix == ".py":
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except Exception as exc:
            findings.append(("syntax", rel, 0, str(exc)))
    if not path.is_file() or (path.suffix not in TEXT_EXTS and path.name != ".gitignore") or rel in SKIP_FILES:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for i, line in enumerate(text.splitlines(), 1):
        for kind, rx in BAD_PATTERNS.items():
            if rx.search(line):
                findings.append((kind, rel, i, line[:180]))
for item in findings[:80]:
    print(" | ".join(map(str, item)))
print("findings:", len(findings))
sys.exit(1 if findings else 0)
