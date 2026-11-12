"""Coolest-art V4: copy the finished entry image to the output directory.

The entry image (entry.png, next to this program) is the artwork itself.
This program only copies it byte for byte, so the output is deterministic.
Standard library only; no network, no clock, no randomness.
"""
import os
import shutil
import sys
from pathlib import Path


def main() -> int:
    source = Path(__file__).resolve().parent / "entry.png"
    if not source.is_file():
        print(f"error: entry image not found: {source}", file=sys.stderr)
        return 1
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "entry.png"
    if dest.resolve() == source.resolve():
        # Output is the source itself; nothing to copy, just confirm it exists.
        return 0
    shutil.copyfile(source, dest)
    if dest.read_bytes() != source.read_bytes():
        print("error: copy mismatch: output differs from source", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
