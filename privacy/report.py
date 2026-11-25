#!/usr/bin/env python3
"""Text-only upstream report; never import or execute upstream code."""
import argparse
import json
from pathlib import Path
from privacy_tools import git, manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    config = manifest()
    record = args.state / "last-fetched.json"
    if record.is_file():
        candidate = json.loads(record.read_text())["candidate"]
        # Resolve as a commit; do not pass unchecked revision options to diff/log.
        candidate = git(args.repo, "rev-parse", "--verify", candidate + "^{commit}")
        base = config["reviewed_base"]
        (args.out / "candidate.json").write_text(json.dumps({"base": base, "candidate": candidate}, indent=2) + "\n")
        (args.out / "changed-files.txt").write_text(git(args.repo, "diff", "--stat", base, candidate, "--") + "\n")
        (args.out / "commits.txt").write_text(git(args.repo, "log", "--oneline", base + ".." + candidate, "--") + "\n")
    (args.out / "README.txt").write_text("Read-only report. Runtime/dependency changes require human review. No push, PR, merge, build or deployment performed.\n")
