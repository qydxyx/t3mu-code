#!/usr/bin/env python3
"""Manual post-review manifest generation. NEVER invoke from CI/updater."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from privacy_tools import KIT, GIT, git, sha256

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed-base", required=True)
    parser.add_argument("--payload-commit", required=True)
    parser.add_argument("--review-note", required=True, help="Existing Markdown filename in privacy/ containing reviewed SHA")
    args = parser.parse_args()
    repo = KIT.parent
    for value in (args.reviewed_base, args.payload_commit):
        if not re.fullmatch(r"[0-9a-f]{40}", value):
            raise SystemExit("Use explicit full commit SHA, not branch/revision expressions")
        git(repo, "rev-parse", "--verify", value + "^{commit}")
    note = KIT / args.review_note
    if note.parent != KIT or note.is_symlink() or note.suffix != ".md" or args.reviewed_base not in note.read_text():
        raise SystemExit("Write a baseline-specific human review note in privacy/ first")
    subprocess.run([*GIT, "-C", str(repo), "merge-base", "--is-ancestor", args.reviewed_base, args.payload_commit], check=True)
    names = git(repo, "diff", "--name-only", args.reviewed_base, args.payload_commit, "--").splitlines()
    if not names or any(n.startswith("privacy/") or n.startswith(".github/workflows/privacy") for n in names):
        raise SystemExit("Payload commit must contain only application patch, not the maintenance overlay")
    patched = {}
    for name in names:
        content = subprocess.check_output([*GIT, "-C", str(repo), "show", args.payload_commit + ":" + name])
        file = repo / name
        if file.is_symlink() or not file.is_file() or file.read_bytes() != content:
            raise SystemExit("Current payload differs from reviewed payload commit: " + name)
        patched[name] = hashlib.sha256(content).hexdigest()
    patch = subprocess.check_output([*GIT, "-C", str(repo), "diff", "--binary", args.reviewed_base, args.payload_commit, "--"])
    (KIT / "no-telemetry.patch").write_bytes(patch)
    members = sorted(p for p in KIT.iterdir() if p.is_file() and p.name != "manifest.json")
    if any(p.suffix not in (".py", ".md", ".patch") and p.name != ".gitignore" for p in members):
        raise SystemExit("Unexpected maintenance file; remove logs/private data before refreshing")
    config = {
        "repository": "https://github.com/qydxyx/t3mu-code",
        "upstream_url": "https://github.com/pingdotgg/t3code.git",
        "upstream_branch": "main",
        "reviewed_base": args.reviewed_base,
        "patch_commit": args.payload_commit,
        "review_note": args.review_note,
        "kit_hashes": {p.name: sha256(p) for p in members},
        "maintenance_files": {name: sha256(repo / name) for name in
                              (".github/workflows/privacy.yml", ".github/workflows/privacy-sync.yml")},
        "patched_files": patched,
    }
    temporary = KIT / "manifest.json.tmp"
    temporary.write_text(json.dumps(config, indent=2) + "\n")
    temporary.replace(KIT / "manifest.json")
    print("Manifest refreshed after explicit review; run all gates and fresh replay before pushing.")
