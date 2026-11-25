#!/usr/bin/env python3
"""A scheduler entry point, not a scheduler installer."""
import argparse
from collections import deque
from datetime import datetime
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    logs = args.state.resolve() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S-%f")
    log = logs / (stamp + "-CST.log")
    command = [sys.executable, str(Path(__file__).with_name("update.py")),
               "--repo", str(args.repo.resolve()), "--state", str(args.state.resolve())]
    with log.open("w") as output:
        result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, timeout=3600)
    print(f"exit={result.returncode}; log={log}; Asia/Shanghai (UTC+8)")
    with log.open() as output:
        print("".join(deque(output, maxlen=24)), end="")
    sys.exit(result.returncode)
