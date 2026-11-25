#!/usr/bin/env python3
"""Fetch upstream; never merge/reset/push the user's branch or run unchecked code."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from privacy_tools import KIT, GIT, manifest, check_kit, git, require_reviewed_tree, apply_patch, run
from verify import verify


def update(repo, state, *, baseline=False):
    config = manifest()
    check_kit(config)
    state.mkdir(parents=True, exist_ok=True)
    with (state / "update.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if baseline:
            candidate = config["reviewed_base"]
        else:
            # Pin URL and branch rather than following the checkout's upstream remote.
            run([*GIT, "-C", repo, "fetch", "--no-tags", config["upstream_url"],
                 "refs/heads/" + config["upstream_branch"]], KIT)
            candidate = git(repo, "rev-parse", "FETCH_HEAD^{commit}")
        (state / "last-fetched.json").write_text(json.dumps({"candidate": candidate}, indent=2))
        # No candidate checkout, install, hook or test runs until the review gate passes.
        require_reviewed_tree(repo, config["reviewed_base"], candidate)
        current = state / "current"
        if current.is_symlink() and not current.resolve().is_relative_to(state):
            raise RuntimeError("current must point to a generated tree inside state")
        if current.exists() and not current.is_symlink():
            raise RuntimeError("Refusing to replace a non-symlink current path")
        status = state / "last-good.json"
        if status.exists() and current.is_symlink():
            previous = json.loads(status.read_text())
            if previous.get("candidate") == candidate and previous.get("patch_sha256") == config["kit_hashes"]["no-telemetry.patch"]:
                # Reverify even repeated runs; do not silently bless a mutated last-good tree.
                verify(current.resolve())
                print("UNCHANGED: last-good source reverified")
                return
        worktree = state / ("candidate-" + candidate[:12] + "-" + uuid.uuid4().hex[:8])
        run([*GIT, "-C", repo, "worktree", "add", "--detach", worktree, candidate], KIT)
        apply_patch(worktree, config)
        env = {**os.environ, "COREPACK_HOME": str(state / "corepack"), "CI": "true",
               "NODE_OPTIONS": "", "DO_NOT_TRACK": "1", "CLERK_TELEMETRY_DISABLED": "1",
               "T3_TASK_CACHE_TELEMETRY": "off", "VP_REMOTE_CACHE": "off",
               "npm_config_update_notifier": "false", "EXPO_NO_TELEMETRY": "1",
               "npm_config_ignore_scripts": "true", "COREPACK_ENABLE_DOWNLOAD_PROMPT": "0"}
        # --ignore-scripts is not a sandbox; review gate also pins all manifests and lockfiles.
        run(["pnpm", "install", "--frozen-lockfile", "--ignore-scripts", "--ignore-pnpmfile"], worktree, env=env)
        verify(worktree)
        temporary = state / (".current-" + uuid.uuid4().hex)
        temporary.symlink_to(worktree)
        os.replace(temporary, current)
        record = {"candidate": candidate, "source": str(worktree), "patch_sha256": config["kit_hashes"]["no-telemetry.patch"]}
        temporary_status = state / ".last-good.tmp"
        temporary_status.write_text(json.dumps(record, indent=2) + "\n")
        os.replace(temporary_status, status)
        print("READY:", current, "(validated source only; no build/install/deploy/push)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=KIT.parent)
    parser.add_argument("--state", type=Path, help="Default: sibling <repo>-privacy-state")
    parser.add_argument("--baseline", action="store_true", help="Initial offline baseline replay; daily runs omit this")
    args = parser.parse_args()
    try:
        repo = args.repo.resolve()
        state = args.state.resolve() if args.state else repo.parent / (repo.name + "-privacy-state")
        update(repo, state, baseline=args.baseline)
    except Exception as error:
        print(str(error), file=sys.stderr)
        print("STOPPED: previous current/last-good preserved; inspect failure and review changes", file=sys.stderr)
        sys.exit(42 if "REVIEW_REQUIRED" in str(error) else 1)
