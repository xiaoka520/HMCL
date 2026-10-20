#!/usr/bin/env python3
"""Keep this fork's single sync/build workflow when merging upstream CI changes."""

import argparse
from pathlib import Path

WORKFLOW = Path(".github/workflows/fork-sync-build.yml")


def enforce(root, apply=False):
    keep = root / WORKFLOW
    if not keep.is_file() or keep.is_symlink():
        raise ValueError("The fork sync/build workflow must exist as a regular file")
    directory = keep.parent
    extras = sorted(
        path for path in directory.rglob("*")
        if path.suffix in (".yml", ".yaml") and path != keep
    )
    if extras and not apply:
        raise ValueError(f"Unexpected upstream workflows: {[str(p.relative_to(root)) for p in extras]}")
    for path in extras:
        path.unlink()
        print(f"Removed upstream workflow: {path.relative_to(root)}")
    print("Workflow policy verified: Fork Sync and Build is the only workflow.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    enforce(args.root, args.apply)
