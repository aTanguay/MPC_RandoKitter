#!/usr/bin/env python3
"""
mpc_random_kit.py
-----------------
CLI for MPC RandoKitter. Wraps mpc_randokitter.core.

Usage:
    python3 mpc_random_kit.py [source_dir] [--name "My Kit"] [--count 64] [--seed 42] [--kits 5]

If source_dir is omitted, the script scans the directory it lives in.
If --kits is omitted, the script asks interactively (1-10).
Output folders are created alongside the samples (unchanged behavior).
"""

import argparse
import os
import sys

from mpc_randokitter import core


def _cli_progress(fraction: float, status: str) -> None:
    print(f"[{int(fraction * 100):3d}%] {status}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate random MPC Drum Programs (.xpm) from a sample directory."
    )
    parser.add_argument("source_dir", nargs="?", default=None,
                        help="Root directory to scan for samples (default: script's own directory)")
    parser.add_argument("--name", default=None, help="Kit name (default: auto-generated)")
    parser.add_argument("--count", type=int, default=64, help="Number of pads to fill (default: 64)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--kits", type=int, default=None, help="Number of kits to generate (1-10)")
    args = parser.parse_args()

    if args.kits is None:
        try:
            answer = input("How many kits would you like to generate? (1-10, default 1): ").strip()
            args.kits = int(answer) if answer else 1
        except (ValueError, EOFError):
            args.kits = 1
    args.kits = max(1, min(10, args.kits))

    if args.source_dir:
        source_dir = os.path.expanduser(args.source_dir)
    else:
        source_dir = os.path.dirname(os.path.abspath(__file__))

    if not os.path.isdir(source_dir):
        print(f"ERROR: '{source_dir}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    # Unchanged legacy behavior: output folders live alongside samples.
    output_dir = source_dir

    try:
        core.generate_kits(
            source_dir=source_dir,
            output_dir=output_dir,
            num_kits=args.kits,
            pads_per_kit=args.count,
            name_override=args.name,
            seed=args.seed,
            progress_cb=_cli_progress,
        )
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
