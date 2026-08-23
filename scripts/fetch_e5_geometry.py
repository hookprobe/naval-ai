#!/usr/bin/env python
"""Restore the E5 source geometry. Same shape as fetch_benchmark_geom.py.

The DSYHS geometry release is 16 MB of IGES and is NOT committed; the
offsets extracted from it are. This script puts the release back and checks
it against the MD5 the publisher itself publishes beside the file, so a
truncated or substituted download is detected rather than silently extracted.

    python scripts/fetch_e5_geometry.py [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "refdata" / "dsyhs"
MANIFEST = DEST / "E5_CHECKSUMS.json"

#: figshare/4TU file ids and the MD5 the publisher states for each. These are
#: NOT hashes we computed of what we happened to receive -- they are the
#: publisher's `supplied_md5`, read from the figshare API, which is what makes
#: this a verification rather than a recording.
FILES = {
    "geometriesIGSmodelscale.zip": {
        "file_id": 38098299,
        "md5": "87870d25f6afd676a3a2a9b9028715e1",
        "bytes": 16192832,
        "article": 21501330,
        "doi": "10.4121/21501330.v1",
        "licence": "CC0",
        "title": "Delft Systematic Yacht Hull Series Geometries data",
    },
}


def _md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify what is on disk; download nothing")
    a = ap.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    bad = 0
    for name, spec in FILES.items():
        path = DEST / name
        if path.exists():
            got = _md5(path.read_bytes())
            ok = got == spec["md5"]
            print(f"{name}: {'OK' if ok else 'MD5 MISMATCH ' + got}")
            bad += 0 if ok else 1
            continue
        if a.check:
            print(f"{name}: MISSING")
            bad += 1
            continue
        url = f"https://ndownloader.figshare.com/files/{spec['file_id']}"
        print(f"{name}: fetching {url}")
        blob = urllib.request.urlopen(url, timeout=300).read()
        got = _md5(blob)
        if got != spec["md5"]:
            print(f"{name}: REFUSED — publisher states {spec['md5']}, "
                  f"download is {got}")
            bad += 1
            continue
        path.write_bytes(blob)
        print(f"{name}: {len(blob)} bytes, MD5 verified")
    MANIFEST.write_text(json.dumps(FILES, indent=2))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
