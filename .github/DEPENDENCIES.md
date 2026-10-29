# Dependency maintenance

Weekly Dependabot updates are proposals only: review changes and require passing CI; no auto-merge. Actions are pinned to upstream commit SHAs.

Group minor/patch Actions independently from test/build tools; major upgrades
stay individual. Runtime packages are not grouped with tooling. Every proposal
still needs exact-head CI and manual review.

Regenerate constraints with the lowest supported Python, not the local default:

```sh
uv pip compile pyproject.toml --extra test --universal --python-version 3.10 --no-header --output-file requirements-ci.lock
uv pip compile pyproject.toml requirements-build.in --all-extras --python-version 3.12 --python-platform linux --constraint requirements-ci.lock --no-header --no-annotate --output-file requirements-audit.txt
python -m pip install packaging==26.3 tomli==2.5.0
python scripts/check_dependency_consistency.py
python -m pip install -c requirements-ci.lock -e '.[test]'
python -m pytest
```

The pre-install consistency guard and negative fixtures reject manifest/lock/
audit drift without disabling constraints. The audit target is Python 3.12/Linux;
the universal CI lock retains Python 3.10 and platform-specific selections.
Pull requests run the matrix once; main and all tag pushes remain checked.

The weekly dependency audit blocks every known advisory in `requirements-audit.txt`, a fully pinned Python 3.12 snapshot including declared runtime/optional/build/test dependencies. It does not install the target packages. Regenerate and review this snapshot whenever pyproject/requirements change; keep uv.lock and requirements-ci.lock aligned where present. Use uv pip compile with pyproject.toml, requirements-build.in and --all-extras (frozen uv export as constraints for uv projects). Then run pip-audit --strict --disable-pip --no-deps -r requirements-audit.txt and the full regression/install gate. This does not attest arbitrary user-installed environments or remote services.
