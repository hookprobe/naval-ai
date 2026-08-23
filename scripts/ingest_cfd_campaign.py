"""Turn a solved CFD campaign into REAL high-fidelity provenance rows.

Gap I1 asks that co-kriging be fitted from real high-fidelity rows "rather than
the synthetic Forrester pair". Nothing in this repository ever put a solved
RANS result into the provenance DB, so there was no real high-fidelity tier to
fit from — `flywheel.retrain` reads `training_matrix("L1", ...)` and nothing
reads anything above it.

This ingests a `mesh_robustness` campaign: one L3 row per hull whose force
history SETTLES, and none for the rest.

ONLY SETTLED CASES BECOME ROWS, and that is the whole discipline here. An
unsettled drag is a number the solver happened to be passing through when the
budget ran out — recording it as high-fidelity truth would poison the tier that
exists precisely to correct L1. `post.settled_drag` is the single judge, the
same one Gate 2U's watermark is scored with, and its components rule (total AND
pressure AND viscous inside the drift bar) is what "settled" means.

    python scripts/ingest_cfd_campaign.py runs/g2u_repeat \
        --json data/campaigns/g2u-repeat-2026-08-22.json [--db data/provenance.db]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from navalai.cfd import post
from navalai.db import Provenance


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ingest_cfd_campaign")
    ap.add_argument("root", help="campaign root, e.g. runs/g2u_repeat")
    ap.add_argument("--json", required=True,
                    help="the campaign's row file (carries the genome per hull)")
    ap.add_argument("--db", default="data/provenance.db")
    ap.add_argument("--tier", default="L3")
    ap.add_argument("--quantity", default="resistance_N")
    ap.add_argument("--n", type=int, default=25,
                    help="the campaign's draw size — with --seed it names the "
                         "population the rows belong to")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    rows = json.load(open(a.json))
    rows = rows if isinstance(rows, list) else rows.get("rows", [])
    by_hull = {r.get("hull"): r for r in rows}

    # THE GENOME IS NOT IN THE CAMPAIGN FILE, and that is why this tier has
    # never existed. `mesh_robustness` records stl_sha256 and lwl but no
    # params, on the stated ground that the population is "reconstructible from
    # (seed, index) through sample_valid". It is — VERIFIED here rather than
    # trusted: redrawing (n, seed) reproduces the recorded LWL for all 25 rows
    # to the 3 dp the campaign stores, worst |delta| 0.0.
    #
    # Two checks that do NOT work, both tried: `stl_sha256` differs because the
    # hash covers the STL MESH, whose resolution the case writer scales with
    # the hull's refinement level, so a default-resolution redraw hashes
    # differently for an identical hull. And comparing LWL at 1e-6 fails
    # because the stored value is ROUNDED. Neither is evidence about the
    # genome; both looked like it.
    from navalai.evaluate import sample_valid
    from navalai.mission import MissionSpec
    from navalai import grammar as _g
    X, _ = sample_valid(a.n, MissionSpec(), seed=a.seed)
    mism = [r["hull"] for r in rows
            if r.get("lwl") is not None and r.get("hull") is not None
            and round(float(_g.named(X[r["hull"]])["LWL"]), 3) != r["lwl"]]
    if mism:
        print(f"REFUSED: the redrawn population does not match the campaign on "
              f"hull(s) {mism[:5]} — the rows cannot be attributed to a genome "
              f"and must not become provenance.")
        return 2
    print(f"population verified: {len(rows)} rows reconstruct from "
          f"(n={a.n}, seed={a.seed})\n")

    prov = None if a.dry_run else Provenance(a.db)
    kept = skipped = 0
    for d in sorted(glob.glob(os.path.join(a.root, "h*/"))):
        name = os.path.basename(d.rstrip("/"))
        try:
            n = int(name[1:])
        except ValueError:
            continue
        row = by_hull.get(n)
        if row is None or n >= len(X):
            print(f"  {name}: not in the campaign file — SKIPPED")
            skipped += 1
            continue
        try:
            r = post.settled_drag(d)
        except Exception as exc:                                # noqa: BLE001
            print(f"  {name}: unscorable ({type(exc).__name__}) — SKIPPED")
            skipped += 1
            continue
        if not r.get("settled"):
            why = "; ".join(r.get("reasons", ()))[:60]
            print(f"  {name}: NOT SETTLED ({why}) — SKIPPED")
            skipped += 1
            continue
        drag = abs(float(r["drag_n"]))
        # The batch error IS the uncertainty. A high-fidelity row without one
        # would be a bare number at the tier whose whole job is to correct a
        # tier that already carries a sigma.
        sigma = abs(float(r.get("error_total", 0.0))) * drag
        print(f"  {name}: SETTLED  drag {drag:9.2f} N  +-{sigma:6.2f}  -> {a.tier} row")
        kept += 1
        if prov is not None:
            x = np.asarray(X[n], float)
            hid = prov.add_hull(x)
            prov.add_result(
                hid, a.tier, "interFoam", "v2606", a.quantity, drag,
                uncertainty=sigma,
                meta={"case": d, "settled": True,
                      "drift_total": r.get("drift_total"),
                      "drift_pressure": r.get("drift_pressure"),
                      "drift_viscous": r.get("drift_viscous"),
                      "cells": r.get("cells"),
                      "scored_by": "post.settled_drag components rule"})
    print(f"\n{kept} settled row(s) ingested at {a.tier}, {skipped} skipped"
          + (" (DRY RUN — nothing written)" if a.dry_run else f" -> {a.db}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
