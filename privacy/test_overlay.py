#!/usr/bin/env python3
"""Guard fork metadata without hiding arbitrary new source or SDK files."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from privacy_tools import GIT, run, git, check_source_delta

class OverlayTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="t3-privacy-overlay-")
        self.repo = Path(self.temp.name)
        run([*GIT, "init", "-q", self.repo], self.repo)
        git(self.repo, "config", "user.name", "Privacy test")
        git(self.repo, "config", "user.email", "test@example.invalid")
        (self.repo / "app.ts").write_text("local\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "baseline")
        self.base = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "privacy").mkdir()
        (self.repo / "privacy/check.py").write_text("trusted\n")
        (self.repo / "privacy/manifest.json").write_text("{}\n")
        self.config = {"reviewed_base": self.base, "patched_files": {},
                       "kit_hashes": {"check.py": hashlib.sha256(b"trusted\n").hexdigest()}}

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_tracked_overlay_passes(self):
        git(self.repo, "add", ".")
        check_source_delta(self.repo, self.config)

    def test_exact_untracked_overlay_passes(self):
        check_source_delta(self.repo, self.config)

    def test_modified_overlay_stops(self):
        (self.repo / "privacy/check.py").write_text("not reviewed\n")
        with self.assertRaisesRegex(RuntimeError, "Maintenance boundary"):
            check_source_delta(self.repo, self.config)

    def test_new_file_inside_metadata_directory_stops(self):
        (self.repo / "privacy/hidden-sdk.js").write_text("fetch('https://collector.invalid')\n")
        with self.assertRaisesRegex(RuntimeError, "Unexpected untracked"):
            check_source_delta(self.repo, self.config)

if __name__ == "__main__":
    unittest.main()
