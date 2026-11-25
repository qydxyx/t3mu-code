#!/usr/bin/env python3
"""Offline tests of the public source-review gate using disposable Git repositories."""
from pathlib import Path
import os
import tempfile
import unittest
from privacy_tools import GIT, run, git, require_reviewed_tree


class SourceReviewGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="t3-privacy-gate-")
        self.repo = Path(self.temp.name)
        run([*GIT, "init", "-q", self.repo], self.repo)
        git(self.repo, "config", "user.name", "Privacy test")
        git(self.repo, "config", "user.email", "test@example.invalid")
        (self.repo / "docs").mkdir()
        (self.repo / "docs/guide.md").write_text("before\n")
        (self.repo / "app.ts").write_text("export const local = true;\n")
        (self.repo / "package.json").write_text('{"private":true}\n')
        self.base = self.commit()

    def tearDown(self):
        self.temp.cleanup()

    def commit(self):
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "fixture")
        return git(self.repo, "rev-parse", "HEAD")

    def test_unchanged_passes(self):
        require_reviewed_tree(self.repo, self.base, self.base)

    def test_plain_docs_change_passes(self):
        (self.repo / "docs/guide.md").write_text("updated\n")
        require_reviewed_tree(self.repo, self.base, self.commit())

    def test_runtime_change_stops(self):
        (self.repo / "app.ts").write_text('fetch("https://collector.example");\n')
        with self.assertRaisesRegex(RuntimeError, "REVIEW_REQUIRED"):
            require_reviewed_tree(self.repo, self.base, self.commit())

    def test_new_sdk_file_stops(self):
        (self.repo / "new-sdk.ts").write_text("export const init = true;\n")
        with self.assertRaisesRegex(RuntimeError, "new-sdk.ts"):
            require_reviewed_tree(self.repo, self.base, self.commit())

    def test_new_lock_stops(self):
        (self.repo / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")
        with self.assertRaisesRegex(RuntimeError, "pnpm-lock.yaml"):
            require_reviewed_tree(self.repo, self.base, self.commit())

    def test_dependency_change_stops(self):
        (self.repo / "package.json").write_text('{"scripts":{"postinstall":"anything"}}\n')
        with self.assertRaisesRegex(RuntimeError, "package.json"):
            require_reviewed_tree(self.repo, self.base, self.commit())

    def test_executable_markdown_stops(self):
        os.chmod(self.repo / "docs/guide.md", 0o755)
        with self.assertRaisesRegex(RuntimeError, "guide.md"):
            require_reviewed_tree(self.repo, self.base, self.commit())

    def test_docs_symlink_stops(self):
        (self.repo / "docs/guide.md").unlink()
        (self.repo / "docs/guide.md").symlink_to("../app.ts")
        with self.assertRaisesRegex(RuntimeError, "guide.md"):
            require_reviewed_tree(self.repo, self.base, self.commit())

    def test_hidden_install_config_stops(self):
        (self.repo / ".npmrc").write_text("registry=https://other.example\n")
        with self.assertRaisesRegex(RuntimeError, ".npmrc"):
            require_reviewed_tree(self.repo, self.base, self.commit())


if __name__ == "__main__":
    unittest.main()
