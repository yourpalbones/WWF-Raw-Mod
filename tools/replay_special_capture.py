"""Reproduce a recorded special from cold boot using controller inputs only."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from build_bret_gear import ORIGINAL_HASH


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("core", type=Path)
    parser.add_argument("rom", type=Path)
    parser.add_argument("case", help="Case ID in the recipe file")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--recipes",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "data"
        / "roster-special-captures.json",
    )
    args = parser.parse_args()
    if hashlib.sha256(args.rom.read_bytes()).hexdigest() != ORIGINAL_HASH:
        raise ValueError("Requires the verified original USA ROM")
    recipes = json.loads(args.recipes.read_text())
    case = next(c for c in recipes["captures"] if c["id"] == args.case)
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("Choose an empty output directory")
    state = None
    runner = Path(__file__).with_name("run_headless.py")
    for number, stage in enumerate(case["stages"]):
        final = number == len(case["stages"]) - 1
        output = args.output / ("capture" if final else f"setup-{number:02d}")
        command = [
            sys.executable,
            str(runner),
            str(args.core),
            str(args.rom),
            "--output",
            str(output),
            "--frames",
            str(stage["frames"]),
            "--interval",
            "6" if final else str(stage["frames"]),
        ]
        if state:
            command.extend(["--load-state", str(state)])
        for port, start, button, duration in stage["inputs"]:
            command.extend(
                [
                    "--press-p2" if port else "--press",
                    f"{start}:{button}:{duration}",
                ]
            )
        environment = os.environ.copy()
        environment.pop("WWF_TRACE_DIR", None)
        if final:
            environment["WWF_TRACE_DIR"] = str(output.resolve())
        subprocess.run(command, env=environment, check=True)
        prefix = output / f"frame-{stage['frames']:06d}"
        for suffix, expected in stage["snapshot_sha256"].items():
            actual = hashlib.sha256(Path(str(prefix) + suffix).read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError(f"Stage {number} differs from reference: {suffix}")
        state = Path(str(prefix) + ".state")
        print(f"Verified stage {number}: {stage['purpose']}", flush=True)
    print(f"Verified cold-boot replay: {case['id']}")


if __name__ == "__main__":
    main()
