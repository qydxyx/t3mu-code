#!/usr/bin/env python3
"""Black-box updater lifecycle tests. Fake install/check tools live only in disposable fixtures."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from privacy_tools import KIT, GIT, git, run


class UpdaterTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="t3-privacy-updater-")
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.kit = self.root / "kit"
        self.state = self.root / "state"
        self.kit.mkdir()
        run([*GIT, "init", "-q", "-b", "main", self.repo], self.root)
        git(self.repo, "config", "user.name", "Privacy test")
        git(self.repo, "config", "user.email", "test@example.invalid")
        (self.repo / "value.txt").write_text("before\n")
        (self.repo / "docs").mkdir()
        (self.repo / "docs/guide.md").write_text("before\n")
        self.base = self.commit()
        for name in ["privacy_tools.py", "update.py", "apply.py"]:
            shutil.copy2(KIT / name, self.kit / name)
        (self.repo / "value.txt").write_text("private\n")
        self.patch = subprocess.check_output([*GIT, "-C", str(self.repo), "diff", "--binary"])
        (self.kit / "no-telemetry.patch").write_bytes(self.patch)
        (self.repo / "value.txt").write_text("before\n")
        (self.kit / "verify.py").write_text('''import os
from pathlib import Path
from privacy_tools import manifest, check_payload, check_source_delta

def verify(repo):
    config = manifest()
    check_payload(repo, config)
    check_source_delta(repo, config)
    if os.environ.get("FIXTURE_CHECK_FAIL"):
        raise RuntimeError("fixture checks failed")
    with Path(os.environ["FIXTURE_CHECK_MARKER"]).open("a") as out:
        out.write("checked\\n")
''')
        binary = self.root / "bin"
        binary.mkdir()
        fake_pnpm = binary / "pnpm"
        fake_pnpm.write_text("#!" + sys.executable + '''
import os, sys
from pathlib import Path
assert "--frozen-lockfile" in sys.argv
assert "--ignore-scripts" in sys.argv
assert "--ignore-pnpmfile" in sys.argv
with Path(os.environ["FIXTURE_INSTALL_MARKER"]).open("a") as out:
    out.write("installed\\n")
''')
        fake_pnpm.chmod(0o755)
        self.env = {**os.environ, "PATH": str(binary) + os.pathsep + os.environ["PATH"],
                    "FIXTURE_INSTALL_MARKER": str(self.root / "install.log"),
                    "FIXTURE_CHECK_MARKER": str(self.root / "check.log")}
        self.config = {"reviewed_base": self.base, "upstream_url": str(self.repo),
                       "upstream_branch": "main", "kit_hashes": {},
                       "patched_files": {"value.txt": hashlib.sha256(b"private\n").hexdigest()}}
        self.save_manifest()
        self.invoke(baseline=True, expected=0)
        self.previous = (self.state / "current").readlink()
        self.previous_metadata = (self.state / "last-good.json").read_bytes()

    def tearDown(self):
        self.temp.cleanup()

    def commit(self):
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "fixture")
        return git(self.repo, "rev-parse", "HEAD")

    def save_manifest(self):
        for name in ["privacy_tools.py", "update.py", "apply.py", "verify.py", "no-telemetry.patch"]:
            self.config["kit_hashes"][name] = hashlib.sha256((self.kit / name).read_bytes()).hexdigest()
        (self.kit / "manifest.json").write_text(json.dumps(self.config))

    def invoke(self, *, baseline=False, expected=0, extra_env=None):
        command = [sys.executable, str(self.kit / "update.py"), "--repo", str(self.repo), "--state", str(self.state)]
        if baseline:
            command.append("--baseline")
        result = subprocess.run(command, capture_output=True, text=True, env={**self.env, **(extra_env or {})})
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def assert_preserved(self):
        self.assertEqual((self.state / "current").readlink(), self.previous)
        self.assertEqual((self.state / "last-good.json").read_bytes(), self.previous_metadata)

    def test_repeated_candidate_does_not_reapply_or_create_worktree(self):
        self.invoke(baseline=True)
        self.assertEqual(len(list(self.state.glob("candidate-*"))), 1)
        self.assertEqual((self.root / "install.log").read_text(), "installed\n")
        self.assert_preserved()

    def test_mutated_last_good_is_not_silently_reused(self):
        (self.state / "current/value.txt").write_text("mutated\n")
        self.invoke(baseline=True, expected=1)
        self.assert_preserved()
        self.assertEqual((self.root / "install.log").read_text(), "installed\n")

    def test_source_change_stops_before_install_or_check(self):
        (self.repo / "new-sdk.ts").write_text('fetch("https://collector.example");\n')
        self.commit()
        before = (self.root / "check.log").read_text()
        self.invoke(expected=42)
        self.assertEqual((self.root / "install.log").read_text(), "installed\n")
        self.assertEqual((self.root / "check.log").read_text(), before)
        self.assert_preserved()

    def test_patch_conflict_preserves_last_good(self):
        broken = self.patch.replace(b"-before", b"-does-not-exist")
        (self.kit / "no-telemetry.patch").write_bytes(broken)
        self.save_manifest()
        self.invoke(baseline=True, expected=1)
        self.assert_preserved()

    def test_check_failure_never_promotes_new_candidate(self):
        (self.repo / "docs/guide.md").write_text("updated docs\n")
        self.commit()
        self.invoke(expected=1, extra_env={"FIXTURE_CHECK_FAIL": "1"})
        self.assert_preserved()

    def test_reviewed_docs_candidate_is_promoted_after_checks(self):
        (self.repo / "docs/guide.md").write_text("updated docs\n")
        self.commit()
        self.invoke()
        self.assertNotEqual((self.state / "current").readlink(), self.previous)
        self.assertEqual((self.state / "current/value.txt").read_text(), "private\n")
        self.assertEqual((self.state / "current/docs/guide.md").read_text(), "updated docs\n")


if __name__ == "__main__":
    unittest.main()
