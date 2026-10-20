#!/usr/bin/env python3
"""Name distributable files by their system, architecture, format and source commit."""

import argparse
import hashlib
from pathlib import Path
import re
import shutil
import struct


def stage(source, destination, commit):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Expected the full 40-character source commit ID")
    files = {}
    for extension in ("jar", "exe", "sh", "deb"):
        matches = list(source.glob(f"HMCL-*.{extension}"))
        if len(matches) != 1:
            raise ValueError(f"Expected one {extension} distribution, got {len(matches)}")
        files[extension] = matches[0]

    executable = files["exe"].read_bytes()
    if executable[:2] != b"MZ":
        raise ValueError("Windows distribution has no DOS executable header")
    offset = struct.unpack_from("<I", executable, 0x3C)[0]
    if executable[offset:offset + 4] != b"PE\0\0":
        raise ValueError("Windows distribution has no PE executable header")
    machine = struct.unpack_from("<H", executable, offset + 4)[0]
    architectures = {0x014C: "x86", 0x8664: "x86_64", 0xAA64: "arm64"}
    if machine not in architectures:
        raise ValueError(f"Unknown Windows PE architecture: {machine:#x}")

    targets = {
        "jar": ("all", "universal"),
        "exe": ("windows", architectures[machine]),
        "sh": ("linux", "universal"),
        "deb": ("linux", "all"),
    }
    destination.mkdir(parents=True, exist_ok=True)
    checksums = []
    for extension, (system, architecture) in targets.items():
        name = f"HMCL-unrestricted-{system}-{architecture}-{extension}-{commit}.{extension}"
        target = destination / name
        shutil.copyfile(files[extension], target)
        checksum = hashlib.sha256(target.read_bytes()).hexdigest()
        if checksum != hashlib.sha256(files[extension].read_bytes()).hexdigest():
            raise ValueError(f"Staged distribution differs from its source: {name}")
        checksums.append(f"{checksum}  {name}\n")
        print(name)
    manifest = destination / f"HMCL-unrestricted-all-universal-sha256-{commit}.sha256"
    manifest.write_text("".join(checksums), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("HMCL/build/libs"))
    parser.add_argument("--destination", type=Path, default=Path("dist"))
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    stage(args.source, args.destination, args.commit)
