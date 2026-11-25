#!/usr/bin/env python3
"""Dependency-free pre-install guard; deliberately does not execute candidate JS."""
import argparse
from pathlib import Path
from privacy_tools import manifest, check_kit, check_payload, check_source_delta

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path, nargs="?", default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    config = manifest()
    check_kit(config)
    check_payload(args.repo.resolve(), config)
    check_source_delta(args.repo.resolve(), config)
    print("PASS: reviewed source and hard-disabled telemetry boundaries")
