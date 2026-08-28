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
#: (family, run_type). RUN_TYPE is the field the audit's P0-2 demands: a
#: wave-loads record and a calm-water resistance record are DIFFERENT
#: MEASUREMENTS, and the seas run's nominal "speed" label invited reading
#: it as a Fn 0.24 resistance point (it has ZERO forward speed — native
#: waveModels carries no mean current). A mesh study is a third thing.
#: Only `calm_resistance` records may support a resistance prediction.
CASES: dict[str, tuple[str, str]] = {
    "hookprobe_cruise_n10": ("hookprobe_hybrid", "calm_resistance"),   # v1
    "hookprobe_v2": ("hookprobe_hybrid", "calm_resistance"),
    "hookprobe_v3": ("hookprobe_hybrid", "calm_resistance"),
    "hookprobe_v3_10kn": ("hookprobe_hybrid", "calm_resistance"),
    "hookprobe_v3_seas": ("hookprobe_hybrid", "wave_loads"),
    "hookprobe_v4": ("hookprobe_hybrid_appendaged", "calm_resistance"),
    "hookprobe_v5_20kn": ("hookprobe_hybrid", "calm_resistance"),
    "hb19_7kn": ("bluff_stern_houseboat", "calm_resistance"),
    "kcs": ("slender_cargo_benchmark", "calm_resistance"),
    "kcs_s1": ("slender_cargo_benchmark", "calm_resistance"),
    "c06_case_a_n5": ("canonical_case_a", "calm_resistance"),
}

#: Below this achieved layer coverage the near-wall mesh is not a boundary
#: layer, so the VISCOUS component is not a measurement of friction — the
#: run remains valid for pressure/wave behaviour. MEASURED on
#: `hookprobe_v5_20kn`: layers failed at ~0.1% coverage and the book
#: published a viscous force anyway (audit P0-2). The bar is the campaign
#: doc's own "a wall model without a boundary-layer mesh is a different
#: simulation".
VISCOUS_VALID_MIN_COVERAGE = 0.50


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

    for name, (family, run_type) in CASES.items():
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
        # LAYER COVERAGE decides whether the viscous half is a measurement.
        try:
            _cov = float(info.get("layers_achieved", "nan"))
        except ValueError:
            _cov = float("nan")
        cov = (_cov / float(info.get("n_layers", "1"))
               if _cov == _cov and _cov > 1.0 else _cov)
        viscous_valid = bool(cov == cov and cov >= VISCOUS_VALID_MIN_COVERAGE)
        # Ct IS COMPARABLE ONLY WITHIN A SURFACE CLASS. MEASURED: v2 and v3
        # are the "same" hull one edit apart and their STL wetted areas read
        # 42.14 vs 34.28 m2 — because v2 is a 20096-facet export and v3 is
        # 152126. The denominator is not wrong; the surfaces are different
        # objects, and a Ct compared across them is a comparison of
        # triangulations. The flag carries the facet count that decides it.
        _facets = 0
        for _line in (case / "case.info").read_text().splitlines():
            if _line.startswith("bow_patch_facets") and " of " in _line:
                try:
                    _facets = int(_line.split(" of ")[1].split()[0])
                except (ValueError, IndexError):
                    _facets = 0
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
            "run_type": run_type,
            "ct": float(r.get("ct") or 0.0) or None,
            "wetted_m2": float(r.get("s_wetted_m2") or 0.0) or None,
            "surface_facets": _facets or None,
            # a Ct is trusted only against records of the same surface class
            "ct_trusted": bool(_facets >= 100_000),
            "layer_coverage": None if cov != cov else float(cov),
            "viscous_valid": viscous_valid,
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
