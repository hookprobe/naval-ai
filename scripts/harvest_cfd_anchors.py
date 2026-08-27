#!/usr/bin/env python
"""Harvest every citable CFD run into data/cfd_anchors.json — THE ANCHOR BOOK.

WHY THIS EXISTS (the owner's directive, 2026-08-28): "we have performed a
lot of CFD work in runs/hookprobe_* and this data should be used in future
designs so that we don't have to repeat it — the expected behaviour is
there." And gap N6 is the standing threat: run directories live on ONE
machine and `clean-runs.sh --purge` deletes them, which has already made a
recorded number unreproducible once (Gate 2M's watermark is the string
NONE for exactly that reason). A measurement that exists only in a
gitignored directory is a measurement on borrowed time.

So this script EXTRACTS — never transcribes — the settled force splits,
conditions and identities out of `runs/*` via the same
`navalai.cfd.post.settled_drag` the gates use, and writes them to a
COMMITTED artifact. Each record carries:

- identity: case name, stl_sha256 (from case.info when present), lwl;
- condition: speed, Fn, flow-throughs, cells, symmetric;
- outcome: total/pressure/viscous N, pressure fraction, Ct + wetted area;
- honesty: `settled` and the settle diagnostics VERBATIM — an unsettled
  run is recorded as an unsettled run and the consumer
  (`navalai.cfd_kb`) refuses to anchor a prediction on it;
- provenance: the run directory (which may later be deleted — the record
  outlives it, which is the point) and the harvest date.

FAMILY LABELS are the one hand-entered field, because a geometry class is
not derivable from a force history. Each label names its source.

Idempotent: re-running re-reads whatever runs exist and REPLACES records
whose case is still on disk, keeping records whose directory has since
been purged (marked "directory_gone": true) — deletion must never
un-measure a number (gap N6's lesson, applied in code).
"""
from __future__ import annotations

import datetime
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from navalai.cfd.post import settled_drag                        # noqa: E402
from navalai.constants import G_STANDARD                         # noqa: E402

OUT = ROOT / "data" / "cfd_anchors.json"

#: The runs worth anchoring on, with the hand-entered geometry family.
#: PROVENANCE of each label: the campaign docs that describe the geometry —
#: docs/research/HOOKPROBE-CFD-CAMPAIGN.md (hookprobe_*: 12 m LOA
#: axe-bow/keel-fin/twin-skeg/twin-tunnel hybrid, owner's Blender hulls),
#: docs/HULL-KB.md (hb19: the houseboat19 bluff-stern liveaboard),
#: benchmarks/kcs.py (kcs*: the KRISO container ship, slender cargo).
#: Mesh-sweep, smoke and zb_* diagnostics are deliberately NOT anchors —
#: they measured the MESH, not a hull.
CASES: dict[str, str] = {
    "hookprobe_cruise_n10": "hookprobe_hybrid",   # v1
    "hookprobe_v2": "hookprobe_hybrid",
    "hookprobe_v3": "hookprobe_hybrid",
    "hookprobe_v3_10kn": "hookprobe_hybrid",
    "hookprobe_v3_seas": "hookprobe_hybrid",
    "hookprobe_v4": "hookprobe_hybrid_appendaged",
    "hookprobe_v5_20kn": "hookprobe_hybrid",
    "hb19_7kn": "bluff_stern_houseboat",
    "kcs": "slender_cargo_benchmark",
    "kcs_s1": "slender_cargo_benchmark",
    "c06_case_a_n5": "canonical_case_a",
}


def _case_info(case: pathlib.Path) -> dict:
    info = {}
    f = case / "case.info"
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                info[k.strip()] = v.strip()
    return info


def main() -> int:
    book = {"_schema": "cfd-anchor-book/1",
            "_written": datetime.date.today().isoformat(),
            "_method": "extracted by scripts/harvest_cfd_anchors.py via "
                       "navalai.cfd.post.settled_drag; family labels are "
                       "hand-entered with provenance in the script",
            "anchors": {}}
    if OUT.exists():
        old = json.loads(OUT.read_text())
        book["anchors"] = old.get("anchors", {})

    for name, family in CASES.items():
        case = ROOT / "runs" / name
        if not case.exists():
            if name in book["anchors"]:
                book["anchors"][name]["directory_gone"] = True
            continue
        try:
            r = settled_drag(case)
        except Exception as exc:                    # noqa: BLE001 — recorded
            print(f"{name}: not harvestable ({type(exc).__name__}: "
                  f"{str(exc)[:60]})")
            continue
        info = _case_info(case)
        lwl = float(r.get("lwl") or info.get("lwl") or 0.0)
        u = float(r["speed"])
        fn = u / math.sqrt(G_STANDARD * lwl) if lwl > 0 else None
        total = abs(float(r["drag_n"]))
        pres = abs(float(r["pressure_n"]))
        book["anchors"][name] = {
            "family": family,
            "stl_sha256": info.get("stl_sha256"),
            "lwl_m": lwl,
            "speed_ms": u,
            "fn": fn,
            "flow_throughs": (None if not math.isfinite(
                float(r["flow_throughs"])) else float(r["flow_throughs"])),
            "cells": int(r.get("cells") or 0),
            "symmetric": bool(r.get("symmetric")),
            "total_n": total,
            "pressure_n": pres,
            "viscous_n": abs(float(r["viscous_n"])),
            "pressure_fraction": pres / total if total > 0 else None,
            "ct": float(r.get("ct") or 0.0) or None,
            "wetted_m2": float(r.get("s_wetted_m2") or 0.0) or None,
            "settled": bool(r["settled"]),
            "settle_reasons": list(r.get("reasons") or ()),
            "single_grid_no_gci": True,
            "case_dir": str(case.relative_to(ROOT)),
            "directory_gone": False,
            "harvested": book["_written"],
        }
        tag = "SETTLED" if r["settled"] else "unsettled"
        print(f"{name}: {tag} {total:.0f} N (p {100 * pres / total:.0f}%) "
              f"@ {u:.2f} m/s" + (f", Fn {fn:.2f}" if fn else ""))
    OUT.write_text(json.dumps(book, indent=1))
    n_s = sum(1 for a in book["anchors"].values() if a["settled"])
    print(f"\n{len(book['anchors'])} records ({n_s} settled) -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
