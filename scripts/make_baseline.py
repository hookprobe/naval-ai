#!/usr/bin/env python3
"""Create (or re-create) `data/baselines.json` — the flywheel's regression mark.

WHY THIS SCRIPT EXISTS (gap D3). `flywheel.retrain` now REFUSES to run without
a baseline, because a missing file used to mean `prior is None` -> `ok = True`,
so the first retrain on any fresh clone deployed unconditionally and wrote its
own numbers as the eternal reference. That was proven with a label-shuffled
model: median_rel_err 0.407 against an honest 0.165, DEPLOYED.

Closing that hole left the other half open: with no committed baseline the
flywheel could not deploy on ANY clone. The mechanism was right and the artefact
was missing. This script produces the artefact, and it produces it by running
THE REAL PATH — a seeded harvest into a fresh provenance DB, then
`retrain(..., bootstrap=True)`. Nothing here writes a metric by hand; every
number in `data/baselines.json` is one the deployment gate itself computed and
accepted, which is the only kind of baseline that means anything.

    python scripts/make_baseline.py                  # write data/baselines.json
    python scripts/make_baseline.py --dry-run        # print, write nothing
    python scripts/make_baseline.py --out /tmp/b.json

Determinism: the harvest seed, the sample count, the mission and the frozen
suite's own seed are all pinned below and recorded INSIDE the output file, so a
regenerated baseline is comparable to the committed one. The frozen suite is
`flywheel.frozen_suite` — published-hull proportions plus the held-out
long-and-narrow wedge — not the training draw.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from navalai import db                                    # noqa: E402
from navalai.flywheel import harvest, retrain             # noqa: E402
from navalai.mission import MissionSpec                   # noqa: E402

# Pinned generation parameters. Change these and the baseline changes, which is
# why they are recorded in the file rather than living only here.
N_HARVEST = 120
HARVEST_SEED = 21
HOLDOUT_SEED = 4242
QUANTITIES = ("wh_per_nm", "gm", "rt")


def build(out: Path, dry_run: bool = False) -> dict:
    mission = MissionSpec()
    with tempfile.TemporaryDirectory() as tmp:
        prov = db.Provenance(Path(tmp) / "baseline_prov.sqlite3")
        n = harvest(N_HARVEST, mission, prov, seed=HARVEST_SEED)
        print(f"harvested {n} L1 hulls into a fresh provenance DB "
              f"(seed {HARVEST_SEED})")

        target = out if not dry_run else Path(tmp) / "baselines.json"
        # The provenance DB is thrown away; the baseline is not. That is
        # deliberate: the baseline is a claim about the FROZEN SUITE, which is
        # reconstructible from `benchmarks/` and the held-out wedge, not about
        # the particular hulls that happened to train the GP.
        refused = {}
        for q in QUANTITIES:
            gp, rep = retrain(prov, mission, q, baseline_path=target,
                              bootstrap=True, holdout_seed=HOLDOUT_SEED)
            verdict = "DEPLOYED" if gp is not None else "REFUSED"
            print(f"  {q:10} {verdict:9} median {rep.err_kind} err "
                  f"{rep.median_rel_err:.4f}  2-sigma coverage "
                  f"{rep.coverage_2sigma:.3f}  ({rep.n_train} train, "
                  f"transform {rep.transform})")
            if gp is None:
                # HONESTY RULE 6. A quantity the deployment gate refuses does
                # NOT get an invented entry so the file looks complete: it is
                # recorded as refused, with the numbers that refused it, and
                # `retrain` will keep refusing it until the model improves.
                refused[q] = {"median_err": rep.median_rel_err,
                              "coverage_2sigma": rep.coverage_2sigma,
                              "err_kind": rep.err_kind,
                              "transform": rep.transform}

        baseline = json.loads(target.read_text()) if target.exists() else {}

    baseline["_README"] = {
        "what": "Frozen deployment marks for navalai.flywheel.retrain. Each "
                "quantity key holds the metrics of the last ACCEPTED retrain "
                "plus monotone best-ever marks; retrain refuses to deploy a "
                "model worse than best_median_rel_err * tol, or with 2-sigma "
                "coverage more than 0.15 below best_coverage_2sigma.",
        "how_produced": "scripts/make_baseline.py — a seeded harvest into a "
                        "throwaway provenance DB, then the real "
                        "retrain(..., bootstrap=True). No metric in this file "
                        "was written by hand.",
        "regenerate": "python scripts/make_baseline.py",
        "generation": {"n_harvest": N_HARVEST, "harvest_seed": HARVEST_SEED,
                       "holdout_seed": HOLDOUT_SEED,
                       "mission": "MissionSpec() defaults",
                       "frozen_suite": "flywheel.frozen_suite — "
                                       "BENCHMARK_PROBES + held-out wedge"},
        "refused_by_the_gate": refused,
        "wall_clock_caveat": "best_wall_clock_s was measured on the machine "
                             "that generated this file. flywheel.WALL_CLOCK_TOL "
                             "is 3x precisely because it is machine weather, "
                             "not model quality; a slower host that trips it is "
                             "reporting its own speed, not a regression. "
                             "Regenerate on the host if that becomes noise.",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    text = json.dumps(baseline, indent=2, sort_keys=True) + "\n"
    if dry_run:
        print(text)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        print(f"wrote {out}")
    return baseline


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(_ROOT / "data" / "baselines.json"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    build(Path(a.out), dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
