"""Copy the finished entry image to the output directory.

The entry image (entry.png, a JPEG) sits beside this program. The program
copies it byte for byte to the output directory (env MAKEFUN_OUTPUT_DIR,
else /output) as entry.png. Pure copy: deterministic by construction.
Standard library only, no network, no clock, no randomness.
"""

import os
import shutil
import sys
from pathlib import Path


def main() -> int:
    source = Path(__file__).resolve().parent / "entry.png"
    if not source.is_file():
        print(f"missing entry image: {source}", file=sys.stderr)
        return 1
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "entry.png"
    shutil.copyfile(source, dest)
    if dest.read_bytes() != source.read_bytes():
        print("copy mismatch: output differs from source", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
