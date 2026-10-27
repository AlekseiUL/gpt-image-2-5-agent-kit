# Dependency maintenance

Weekly Dependabot updates are proposals only: review changes and require passing CI; no auto-merge. Actions are pinned to upstream commit SHAs.

The weekly dependency audit blocks every known advisory in `requirements-audit.txt`, a fully pinned Python 3.12 snapshot including declared runtime/optional/build/test dependencies. It does not install the target packages. Regenerate and review this snapshot whenever pyproject/requirements change; keep uv.lock and requirements-ci.lock aligned where present. Use uv pip compile with pyproject.toml, requirements-build.in and --all-extras (frozen uv export as constraints for uv projects). Then run pip-audit --strict --disable-pip --no-deps -r requirements-audit.txt and the full regression/install gate. This does not attest arbitrary user-installed environments or remote services.
