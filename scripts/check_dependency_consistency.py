"""Fail before package installation when manifest, lock and audit snapshot drift.

The audit snapshot targets CPython 3.12/Linux. uv also checks its full lock
metadata via `uv lock --check`; this check does not replace the resolver.
"""
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def pinned_requirements(path, environment):
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        req = Requirement(line)
        if req.marker and not req.marker.evaluate(environment):
            continue
        specs = list(req.specifier)
        if len(specs) != 1 or specs[0].operator != "==":
            raise ValueError(f"{path.name}: unpinned requirement {req.name}")
        name = canonicalize_name(req.name)
        if name in result and result[name] != specs[0].version:
            raise ValueError(f"{path.name}: conflicting pins for {name}")
        result[name] = specs[0].version
    return result


def check(root):
    env = {key: str(value) for key, value in default_environment().items()}
    env.update(python_version="3.12", python_full_version="3.12.0",
               sys_platform="linux", os_name="posix", platform_system="Linux",
               platform_machine="x86_64", extra="")
    audit = pinned_requirements(root / "requirements-audit.txt", env)
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    if (root / "uv.lock").exists():
        lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
        locked = {}
        for package in lock["package"]:
            if "registry" not in package.get("source", {}):
                continue
            # The audit version must exist in the universal lock. Resolution
            # and platform-specific selections are additionally checked by uv.
            locked.setdefault(canonicalize_name(package["name"]), set()).add(package["version"])
        for name, versions in locked.items():
            if audit.get(name) not in versions:
                raise ValueError(f"audit/lock mismatch: {name}")
    else:
        locked = {name: {version} for name, version in
                  pinned_requirements(root / "requirements-ci.lock", env).items()}
        for name, versions in locked.items():
            if audit.get(name) not in versions:
                raise ValueError(f"audit/lock mismatch: {name}")
    deps = list(project["project"].get("dependencies", []))
    for requirements in project["project"].get("optional-dependencies", {}).values():
        deps.extend(requirements)
    for value in deps:
        req = Requirement(value)
        if req.marker and not req.marker.evaluate(env):
            continue
        name = canonicalize_name(req.name)
        if name not in locked or not any(v in req.specifier for v in locked[name]):
            raise ValueError(f"manifest/lock mismatch: {name}")
        if name not in audit or audit[name] not in req.specifier:
            raise ValueError(f"manifest/audit mismatch: {name}")
    for value in project["build-system"]["requires"]:
        req = Requirement(value)
        name = canonicalize_name(req.name)
        if name not in audit or audit[name] not in req.specifier:
            raise ValueError(f"build/audit mismatch: {name}")


if __name__ == "__main__":
    try:
        check(Path(__file__).resolve().parents[1])
    except (ValueError, KeyError) as exc:
        sys.exit(str(exc))
    print("Dependency consistency: PASS (audit target Python 3.12/Linux)")
