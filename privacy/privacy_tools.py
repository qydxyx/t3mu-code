#!/usr/bin/env python3
"""Trusted, dependency-free patch/review gate. Never import candidate code here."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

KIT = Path(__file__).resolve().parent
GIT = ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false"]


def run(args, cwd, *, capture=False, env=None, timeout=900):
    print("+", " ".join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), cwd=cwd, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          env=env, timeout=timeout).stdout


def git(repo, *args):
    return run([*GIT, "-C", repo, *args], KIT, capture=True).strip()


def manifest():
    return json.loads((KIT / "manifest.json").read_text())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_kit(config):
    for name, expected in config["kit_hashes"].items():
        if sha256(KIT / name) != expected:
            raise RuntimeError(f"Trusted kit changed: {name}; review and regenerate manifest")


def protected_tree(repo, commit):
    # Only plain, non-executable Markdown inside docs/ is allowed to change unattended.
    raw = subprocess.check_output([*GIT, "-C", str(repo), "ls-tree", "-rz", commit])
    entries = {}
    for item in raw.split(b"\0"):
        if not item:
            continue
        info, raw_path = item.split(b"\t", 1)
        mode, kind, oid = info.decode().split()
        path = os.fsdecode(raw_path)
        if path.startswith("docs/") and path.endswith(".md") and mode == "100644" and kind == "blob":
            continue
        entries[path] = (mode, kind, oid)
    return entries


def require_reviewed_tree(repo, reviewed, candidate):
    old, new = protected_tree(repo, reviewed), protected_tree(repo, candidate)
    changed = sorted(p for p in old.keys() | new.keys() if old.get(p) != new.get(p))
    if changed:
        raise RuntimeError("REVIEW_REQUIRED: runtime/build/dependency/data changes:\n" + "\n".join(changed))


def apply_patch(repo, config):
    if git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("Refusing to patch a dirty checkout")
    require_reviewed_tree(repo, config["reviewed_base"], "HEAD")
    patch = KIT / "no-telemetry.patch"
    run([*GIT, "-C", repo, "apply", "--check", "--index", patch], KIT)
    run([*GIT, "-C", repo, "apply", "--index", patch], KIT)
    check_payload(repo, config)


def check_payload(repo, config):
    for name, expected in config["patched_files"].items():
        file = Path(repo) / name
        if not file.is_file() or file.is_symlink() or sha256(file) != expected:
            raise RuntimeError(f"Patched boundary changed: {name}; manual review required")


def check_source_delta(repo, config):
    changed = set(git(repo, "diff", "--name-only", config["reviewed_base"], "--").splitlines())
    allowed_metadata = {"privacy/" + name: digest for name, digest in config["kit_hashes"].items()}
    allowed_metadata.update(config.get("maintenance_files", {}))
    for name, expected in allowed_metadata.items():
        path = Path(repo) / name
        if path.exists() or path.is_symlink():
            if path.is_symlink() or not path.is_file() or sha256(path) != expected:
                raise RuntimeError(f"Maintenance boundary changed: {name}")
    extra = changed - config["patched_files"].keys()
    extra.discard("privacy/manifest.json")
    for name in list(extra):
        if name in allowed_metadata:
            extra.remove(name)
    for name in extra:
        path = Path(repo) / name
        if not (name.startswith("docs/") and name.endswith(".md") and path.is_file()
                and not path.is_symlink() and not (path.stat().st_mode & 0o111)):
            raise RuntimeError(f"Unreviewed worktree change: {name}")
    unknown = git(repo, "ls-files", "--others", "--exclude-standard").splitlines()
    if set(unknown) - config["patched_files"].keys() - allowed_metadata.keys() - {"privacy/manifest.json"}:
        raise RuntimeError("Unexpected untracked files in validation tree")
