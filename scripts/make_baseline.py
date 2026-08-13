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
import statistics
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
# THE MARK IS MEASURED OVER A SEED ENSEMBLE, NOT ON ONE SEED (gap T3).
# `HARVEST_SEED = 21` alone produced a mark that `flywheel.retrain` then
# ratcheted against with a 1.25x tolerance. MEASURED 2026-08-12, eight honest
# seeds at the identical configuration (n=120, holdout 4242, GP.fit(seed=1)):
#
#     quantity    median   min      max      spread   seed 21 is
#     wh_per_nm   0.1901   0.1240   0.2509   2.02x    the MINIMUM
#     gm          0.4194   0.2504   0.7456   2.98x    the MINIMUM
#     rt          0.1901   0.1240   0.2312   1.86x    the MINIMUM
#
# The pinned seed was the best of the eight on all three quantities, so the
# recorded mark was an extreme order statistic and the gate was comparing a
# fresh random draw against it: against `best_median_rel_err * 1.25`, 4 of 8
# honest seeds are refused on wh_per_nm and 7 of 8 on gm. The first seed is
# still the one that produces the DEPLOYABLE entry -- that path is unchanged
# and still runs the real gate -- but the ensemble median and its spread are
# measured beside it and are what `retrain` ratchets on.
#
# Cost is measured and it is not a reason to skip this: one seed is 8.35 s
# (harvest 4.0 s + three quantities), the whole eight-seed ensemble 66 s.
HARVEST_SEEDS = (21, 22, 23, 24, 25, 26, 27, 28)
HARVEST_SEED = HARVEST_SEEDS[0]        # the seed the deployable entry uses
HOLDOUT_SEED = 4242
QUANTITIES = ("wh_per_nm", "gm", "rt")


def build(out: Path, dry_run: bool = False) -> dict:
    mission = MissionSpec()
    with tempfile.TemporaryDirectory() as tmp:
        prov = db.Provenance(Path(tmp) / "baseline_prov.sqlite3")
        n = harvest(N_HARVEST, mission, prov, seed=HARVEST_SEED)
        print(f"harvested {n} L1 hulls into a fresh provenance DB "
              f"(seed {HARVEST_SEED})")

        # THE RUN WRITES INTO A SCRATCH FILE, NEVER INTO `out` (2026-08-13).
        # `retrain` only REPLACES the key it deployed, so pointing it at the
        # file being regenerated left a REFUSED quantity's previous entry
        # standing. MEASURED on the first regeneration after the geometry
        # kernel rebuild: `gm` was refused at 0.7341 against the 0.35 absolute
        # floor, and the file that came out still carried the pre-rebuild
        # `gm` mark — median 0.2504, suite fingerprint d782c04bf198af11, a
        # timestamp from the previous day — which the ensemble block below
        # then averaged in as seed 21's value. A mark measured on hulls the
        # genome can no longer express, surviving its own regeneration and
        # entering a statistic: defect class 5 with a fresh timestamp on it.
        # The scratch file makes a refused quantity ABSENT, which is what
        # `refused_by_the_gate` is for.
        target = Path(tmp) / "baselines.json"
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

        # THE ENSEMBLE (gap T3). Every seed runs the SAME real path — a fresh
        # harvest into a throwaway DB, then `retrain(..., bootstrap=True)`
        # against a throwaway baseline file — so these are gate-computed
        # numbers, not a hand-written statistic. The first seed's numbers are
        # already in `baseline` above and are re-used rather than re-run.
        ens: dict[str, dict[str, list[float]]] = {
            q: {"med": [], "cov": []} for q in QUANTITIES}
        for q in QUANTITIES:
            if q in baseline:
                ens[q]["med"].append(float(baseline[q]["median_rel_err"]))
                ens[q]["cov"].append(float(baseline[q]["coverage_2sigma"]))
            elif q in refused:
                ens[q]["med"].append(float(refused[q]["median_err"]))
                ens[q]["cov"].append(float(refused[q]["coverage_2sigma"]))
        for seed in HARVEST_SEEDS[1:]:
            with tempfile.TemporaryDirectory() as t2:
                p2 = db.Provenance(Path(t2) / "ens.sqlite3")
                harvest(N_HARVEST, mission, p2, seed=seed)
                scratch = Path(t2) / "baselines.json"
                for q in QUANTITIES:
                    _gp, r = retrain(p2, mission, q, baseline_path=scratch,
                                     bootstrap=True, holdout_seed=HOLDOUT_SEED)
                    ens[q]["med"].append(float(r.median_rel_err))
                    ens[q]["cov"].append(float(r.coverage_2sigma))
            print(f"  ensemble seed {seed}: "
                  + "  ".join(f"{q}={ens[q]['med'][-1]:.4f}"
                              for q in QUANTITIES))

        # A quantity whose ensemble is incomplete gets NO ensemble keys. An
        # ensemble median over a subset, silently, is a statistic that does not
        # describe what its name says — the same shape as a coverage figure
        # computed over the rows that happened to be measurable.
        for q in QUANTITIES:
            meds, covs = ens[q]["med"], ens[q]["cov"]
            if q not in baseline or len(meds) != len(HARVEST_SEEDS):
                continue
            lo, hi = min(meds), max(meds)
            baseline[q].update({
                "seeds": list(HARVEST_SEEDS),
                "median_rel_err_seeds": meds,
                "coverage_2sigma_seeds": covs,
                # statistics.median, i.e. the AVERAGE of the two middle values
                # at an even seed count. Taking the upper middle
                # element instead would move wh_per_nm 0.1901 ->
                # 0.2118, a looser mark bought by an off-by-one.
                "ensemble_median_rel_err": float(statistics.median(meds)),
                "ensemble_coverage_2sigma": float(statistics.median(covs)),
                # max/min. The ratchet widens its tolerance to this when it is
                # larger than the declared one, because seed-to-seed variation
                # the baseline itself measured is not evidence of a regression.
                "seed_spread": float(hi / lo) if lo > 0 else float("inf"),
            })
            print(f"  {q:10} ensemble median {baseline[q]['ensemble_median_rel_err']:.4f} "
                  f"over {len(meds)} seeds  spread {baseline[q]['seed_spread']:.2f}x  "
                  f"[{lo:.4f}, {hi:.4f}]")

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
                       "harvest_seeds": list(HARVEST_SEEDS),
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
