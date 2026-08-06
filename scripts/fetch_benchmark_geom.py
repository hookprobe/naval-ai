#!/usr/bin/env python3
"""Regenerate `data/benchmark_geom/kcs.stl` from the workshop IGES.

Gap J5: the geometry is gitignored (workshop terms), so on a fresh clone the
KCS acceptance check has nothing to check and five tests skip. This script is
the committed recipe that ends that, and `data/benchmark_geom/CHECKSUMS.json`
is the committed record of what it should produce.

IT DOES NOT DOWNLOAD ANYTHING, AND THAT IS NOT AN OVERSIGHT. The Tokyo 2015
bundle comes from t2015.nmri.go.jp behind a registration the script cannot
honestly complete on the user's behalf, and re-hosting the geometry is exactly
what its terms may forbid. So: point this at the IGES you obtained, and it does
the deterministic half — the conversion whose seven flags were each measured,
not guessed (see benchmarks/kcs.py for why each one is what it is).

    python scripts/fetch_benchmark_geom.py --iges downloads/KCS.igs

Exit codes: 0 accepted · 2 source IGES missing · 3 produced but REJECTED by
the volume bar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_RECORD = _ROOT / "data" / "benchmark_geom" / "CHECKSUMS.json"
_OUT = _ROOT / "data" / "benchmark_geom" / "kcs.stl"


def main() -> int:
    rec = json.loads(_RECORD.read_text())["kcs.stl"]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--iges", default=str(_ROOT / "downloads" / "KCS.igs"),
                    help="the workshop IGES you obtained (not redistributed)")
    ap.add_argument("--out", default=str(_OUT))
    args = ap.parse_args()

    iges = Path(args.iges)
    if not iges.exists():
        print(f"source IGES not found: {iges}\n")
        print(f"  it comes from: {rec['source_document']}\n")
        print("  the recipe this script runs, for reference:")
        for step in rec["recipe"]:
            print(f"    {step}")
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / "kcs_full.stl"

    # The flags are transcribed from CHECKSUMS.json's recipe rather than
    # retyped here: two copies of a seven-flag command line is precisely the
    # "number declared twice" defect CLAUDE.md names, and the flags ARE the
    # recipe (--scale 0.001 for millimetres, --z-shift -0.34178 because z=0 is
    # the keel, --mirror-y because the distribution is a half body).
    conv = rec["recipe"][0].split()
    conv[conv.index("downloads/KCS.igs")] = str(iges)
    conv[conv.index("/tmp/kcs_full.stl")] = str(tmp)
    conv[0] = sys.executable
    conv[1] = str(_ROOT / "scripts" / "iges2stl.py")
    print("+ " + " ".join(conv))
    r = subprocess.run(conv, cwd=_ROOT)
    if r.returncode != 0:
        return r.returncode

    from navalai.cfd.post import cap_planar_holes, stl_submerged_properties
    print(f"+ cap_planar_holes({tmp} -> {out})")
    cap_planar_holes(str(tmp), str(out))

    got = hashlib.sha256(out.read_bytes()).hexdigest()
    if got == rec["sha256"]:
        print(f"sha256 MATCHES the record ({got[:12]}...)")
    else:
        print(f"sha256 {got[:12]}... != recorded {rec['sha256'][:12]}... — "
              f"REGENERATED, not necessarily wrong: the tessellation depends "
              f"on the OCC version. The volume bar below is the verdict.")

    a = rec["acceptance"]
    vol = stl_submerged_properties(str(out))["volume_m3"]
    err = (vol - a["published_m3"]) / a["published_m3"] * 100.0
    print(f"submerged volume {vol:.6f} m^3 vs published {a['published_m3']:.6f} "
          f"m^3 = {err:+.3f}% (bar +-{a['tolerance_pct']}%)")
    if abs(err) >= a["tolerance_pct"]:
        print("REJECTED. Do not run a calibration on this file.")
        return 3
    print("accepted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
