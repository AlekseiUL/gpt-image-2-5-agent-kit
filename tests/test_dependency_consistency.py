"""Negative regression tests for the early dependency consistency gate."""
import runpy
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
check = runpy.run_path(str(ROOT / "scripts/check_dependency_consistency.py"))["check"]


class ConsistencyTests(unittest.TestCase):
    def test_current_repository(self):
        check(ROOT)

    def fixture(self, path, *, manifest="1.0", audit="1.0", locked="1.0", uv=False):
        (path / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["builder==1.0"]\n'
            f'[project]\ndependencies = ["example=={manifest}"]\n', encoding="utf-8")
        (path / "requirements-audit.txt").write_text(
            f"example=={audit}\nbuilder==1.0\n", encoding="utf-8")
        if uv:
            (path / "uv.lock").write_text(
                '[[package]]\nname = "example"\n'
                f'version = "{locked}"\nsource = {{registry = "https://pypi.org/simple"}}\n',
                encoding="utf-8")
        else:
            (path / "requirements-ci.lock").write_text(f"example=={locked}\n", encoding="utf-8")

    def test_manifest_drift_fails_for_both_lock_formats(self):
        for uv in (False, True):
            with self.subTest(uv=uv), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                self.fixture(path, manifest="2.0", uv=uv)
                with self.assertRaisesRegex(ValueError, "manifest/lock mismatch"):
                    check(path)

    def test_audit_drift_fails_for_both_lock_formats(self):
        for uv in (False, True):
            with self.subTest(uv=uv), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                self.fixture(path, audit="2.0", uv=uv)
                with self.assertRaisesRegex(ValueError, "audit/lock mismatch"):
                    check(path)

    def test_matching_inputs_pass(self):
        for uv in (False, True):
            with self.subTest(uv=uv), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                self.fixture(path, uv=uv)
                check(path)
