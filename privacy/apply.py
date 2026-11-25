#!/usr/bin/env python3
import argparse
from pathlib import Path
from privacy_tools import manifest, check_kit, apply_patch

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply once to a clean, reviewed baseline checkout")
    parser.add_argument("repo", type=Path)
    args = parser.parse_args()
    config = manifest()
    check_kit(config)
    apply_patch(args.repo.resolve(), config)
    print("Patch applied; next run verify.py before using this source.")
