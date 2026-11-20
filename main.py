#!/usr/bin/env python3
"""Carry the finished front page to the output directory.

The repository already holds the image: entry.png, a 1024 by 1024
front page summing up the world news of Thursday 19 November 2026 —
the World Court's genocide verdict on Myanmar and the Shenzhen
trilateral declaration as the two leads, 42 headlines across seven
regions, a schematic world map with ten numbered markers, the day in
numbers, and an eight-event UTC timeline.

This script is the entrypoint. It walks the PNG chunk by chunk to
make sure the file is whole and the right size, then writes it to
$MAKEFUN_OUTPUT_DIR (or /output when that variable is unset).
Standard library only, no network, and the same bytes every run.
"""

import hashlib
import os
import sys
import zlib
from pathlib import Path

SIDE = 1024
CEILING = 1 << 20
MAGIC = bytes((0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A))


def refuse(why):
    sys.stderr.write("entry.png: " + why + "\n")
    raise SystemExit(1)


def walk_chunks(blob):
    """Yield (kind, data) for each chunk, checking every CRC."""
    pos = 8
    while pos < len(blob):
        if pos + 8 > len(blob):
            refuse("chunk header cut short")
        size = int.from_bytes(blob[pos:pos + 4], "big")
        kind = blob[pos + 4:pos + 8].decode("latin-1")
        end = pos + 12 + size
        if end > len(blob):
            refuse("chunk " + kind + " runs past the end of the file")
        data = blob[pos + 8:pos + 8 + size]
        stored = int.from_bytes(blob[end - 4:end], "big")
        if zlib.crc32(blob[pos + 4:pos + 8 + size]) != stored:
            refuse("chunk " + kind + " fails its CRC")
        yield kind, data
        pos = end
    if pos != len(blob):
        refuse("trailing bytes after the last chunk")


def main():
    here = Path(__file__).resolve().parent
    source = here / "entry.png"
    target_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output")
    target = target_dir / "entry.png"

    blob = source.read_bytes()
    if len(blob) > CEILING:
        refuse("bigger than the 1 MiB limit")
    if blob[:8] != MAGIC:
        refuse("does not start with the PNG magic bytes")

    seen = []
    header = None
    for kind, data in walk_chunks(blob):
        seen.append(kind)
        if kind == "IHDR":
            header = data
    if not seen or seen[0] != "IHDR":
        refuse("the first chunk is not IHDR")
    if seen[-1] != "IEND":
        refuse("the last chunk is not IEND")
    if header is None or len(header) < 8:
        refuse("IHDR chunk is too short")

    width = int.from_bytes(header[0:4], "big")
    height = int.from_bytes(header[4:8], "big")
    if width != SIDE or height != SIDE:
        refuse("expected a 1024 by 1024 image, found "
               + str(width) + " by " + str(height))

    target_dir.mkdir(parents=True, exist_ok=True)
    target.write_bytes(blob)
    print("wrote " + str(target) + " (" + str(len(blob)) + " bytes, sha256 "
          + hashlib.sha256(blob).hexdigest() + ")")


if __name__ == "__main__":
    main()
