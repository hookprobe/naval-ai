#!/usr/bin/env python3
"""Generate docs/PHYSICAL_FORM_REPORT.md — the physical-form regression record.

Six deterministic vessel cases (fixed parameter vectors, defined once in
`navalai.formcheck.CASES` and printed verbatim below so the numbers are
recorded in the generated document): descriptors, per-descriptor verdicts
against the SOURCED ranges in this tree, ASCII sketches of the SAC curve and
the DWL plan view, and a watertight STL per case in runs/formcheck/ (via the
existing `navalai.cfd.case.hull_to_stl` -> `Hull.closed_mesh` path).

Determinism: there is NO sampling anywhere in this script — every vector is a
literal, so no seed is needed; the only floating inputs are the kernel's own
closed forms.

    python3 scripts/physical_form_report.py                  # report + STLs
    python3 scripts/physical_form_report.py --write-baseline # + ratchet JSON

--write-baseline rewrites tests/formcheck_baseline.json, the ratchet the
regression tests pin the current forms to. Re-baselining is a DECISION, not a
side effect: do it only with a measured justification in the same commit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from navalai import grammar  # noqa: E402
from navalai.cfd.case import hull_to_stl  # noqa: E402
from navalai.formcheck import (CASES, FormCase, SourcedRange,  # noqa: E402
                               design_froude, form_descriptors,
                               ratchet_entries, sourced_ranges)
from navalai.geometry import Hull  # noqa: E402

REPORT = ROOT / "docs" / "PHYSICAL_FORM_REPORT.md"
BASELINE = ROOT / "tests" / "formcheck_baseline.json"
STL_DIR = ROOT / "runs" / "formcheck"

# Display order for the descriptor table (anything not listed goes after,
# sorted). Purely presentation.
_ORDER = (
    "lwl_m", "bwl_m", "draft_design_m", "L_over_B", "B_over_T",
    "L_over_B_floated", "B_over_T_floated", "Cp", "Cb", "Cm", "Cwp",
    "lcb_pct_lwl", "lcf_pct_lwl", "entrance_half_angle_deg",
    "entrance_half_angle_10pct_deg", "alpha_e_chord_floor_deg",
    "run_half_angle_deg", "transom_area_ratio",
    "transom_waterline_beam_ratio", "bow_sac_slope", "fwd20_sac_fraction",
    "aft20_sac_fraction", "A_max_m2", "volume_design_m3",
    "displacement_design_kg", "displacement_floated_kg", "draft_floated_m",
    "wetted_design_m2_per_hull", "ws_over_vol23", "KB_m", "BM_m", "KG_m",
    "GM_m", "Fn", "Re", "separation_over_lwl", "separation_m",
    "demihull_beam_m", "demihull_beam_floated_m",
)

_UNITS = {
    "lwl_m": "m", "bwl_m": "m", "draft_design_m": "m", "draft_floated_m": "m",
    "lcb_pct_lwl": "%LWL", "lcf_pct_lwl": "%LWL",
    "entrance_half_angle_deg": "deg", "entrance_half_angle_10pct_deg": "deg",
    "alpha_e_chord_floor_deg": "deg", "run_half_angle_deg": "deg",
    "A_max_m2": "m^2", "volume_design_m3": "m^3",
    "displacement_design_kg": "kg", "displacement_floated_kg": "kg",
    "wetted_design_m2_per_hull": "m^2", "KB_m": "m", "BM_m": "m",
    "KG_m": "m", "GM_m": "m", "separation_m": "m", "demihull_beam_m": "m",
    "demihull_beam_floated_m": "m",
}


def _fmt(v: float) -> str:
    if abs(v) >= 1e5 or (abs(v) < 1e-3 and v != 0.0):
        return f"{v:.4g}"
    return f"{v:.4f}".rstrip("0").rstrip(".") if v != int(v) else f"{v:g}"


def _ascii_curve(xs: np.ndarray, ys: np.ndarray, height: int = 12,
                 width: int = 61, label: str = "") -> list[str]:
    """A monospaced sketch of y(x), x left-to-right = transom-to-stem."""
    ymax = float(np.max(ys))
    if ymax <= 0.0:
        return ["(degenerate curve)"]
    xg = np.linspace(float(xs[0]), float(xs[-1]), width)
    yg = np.interp(xg, xs, ys) / ymax
    rows = []
    for r in range(height, 0, -1):
        lo = (r - 1) / height
        line = "".join("#" if v > lo + 1e-12 else " " for v in yg)
        rows.append(f"  |{line}|")
    rows.append("  +" + "-" * width + "+")
    rows.append(f"   transom{' ' * (width - 14)}stem")
    if label:
        rows.insert(0, f"  {label} (normalised, max = 1)")
    return rows


def _ascii_planview(hull: Hull, width: int = 61, half: int = 7) -> list[str]:
    """DWL plan view: the design waterline, mirrored about the centreline."""
    y = hull.y_wl
    x = hull.x
    ymax = float(np.max(y))
    xg = np.linspace(float(x[0]), float(x[-1]), width)
    yg = np.interp(xg, x, y) / ymax
    rows = [f"  DWL plan view (half-breadth normalised, B_wl/2 = "
            f"{ymax:.3f} m)"]
    for r in range(half, -half - 1, -1):
        lo = abs(r) / half
        line = "".join("*" if v >= lo - 1e-12 else " " for v in yg)
        rows.append(("  =" if r == 0 else "   ") + line)
    rows.append("   " + "-" * width)
    rows.append(f"   transom{' ' * (width - 14)}stem")
    return rows


def _verdict(name: str, value: float | None, rng) -> str:
    if isinstance(rng, str):
        return rng if value is not None else rng
    if value is None:
        return "(absent)"
    return ("PASS" if rng.contains(value) else "**OUT OF RANGE**") + \
        f" {rng} — {rng.source}"


def _case_section(case: FormCase, out: list[str],
                  baselines: dict[str, dict]) -> None:
    d = form_descriptors(case.params, case.mission)
    sr = sourced_ranges(case)
    scalars, absent = d["scalars"], d["absent"]
    p = case.named
    hull = Hull(case.params)
    fn = design_froude(case.mission, p["LWL"])

    out.append(f"## Case {case.key} — {case.title}")
    out.append("")
    out.append(case.rationale)
    out.append("")
    out.append("**Parameter vector** (grammar order, deterministic — no "
               "sampling, no seed):")
    out.append("")
    out.append("```")
    for n, v in p.items():
        out.append(f"{n:>11s} = {v:g}")
    out.append("```")
    m = case.mission
    out.append(f"**Mission**: displacement target {m.displacement_target_kg:g}"
               f" kg · cruise {m.cruise_speed_kn:g} kn (design Fn "
               f"{fn:.3f}) · category {m.design_category} · crew {m.crew} · "
               f"topology {case.vessel.topology.value} · manning "
               f"{case.vessel.manning.value}"
               + (f" · s/L {case.vessel.separation_over_lwl:g}"
                  if case.vessel.n_hulls > 1 else ""))
    out.append("")

    ev = d["meta"]["evaluation"]
    if ev is not None:
        out.append(f"**Ladder**: tier {ev['tier']}, ok={ev['ok']}. " +
                   ("No violations." if not ev["violations"] else
                    "Violations (verbatim, the honest record):"))
        for v in ev["violations"]:
            out.append(f"> - {v}")
        out.append("")

    out.append("| descriptor | value | verdict vs sourced range |")
    out.append("|---|---|---|")
    listed = [n for n in _ORDER if n in scalars or n in absent]
    listed += sorted((set(scalars) | set(absent)) - set(listed))
    for name in listed:
        if name in scalars:
            v = scalars[name]
            unit = _UNITS.get(name, "-")
            out.append(f"| {name} | {_fmt(v)} {unit if unit != '-' else ''} | "
                       f"{_verdict(name, v, sr.get(name, 'UNKNOWN — no sourced range in tree'))} |")
        else:
            out.append(f"| {name} | ABSENT | {absent[name]} |")
    out.append("")

    # SAC + fullness arrays
    out.append("**SAC distribution** — A(x)/A_max at the 11 lines-plan "
               "stations (station 0 = transom):")
    out.append("")
    out.append("```")
    sac = d["arrays"]["sac_norm"]
    out.append("station: " + " ".join(f"{i:>5d}" for i in range(len(sac))))
    out.append("A/Amax : " + " ".join(f"{v:5.3f}" for v in sac))
    full = d["arrays"]["section_fullness"]
    out.append("C_sect : " + " ".join("  nan" if not np.isfinite(v)
                                      else f"{v:5.3f}" for v in full))
    out.append("```")
    out.append("")

    xs = np.linspace(0.0, p["LWL"], 121)
    from navalai.geometry import sectional_area
    out.append("```")
    out.extend(_ascii_curve(xs, sectional_area(case.params, xs),
                            label="SAC A(x)"))
    out.append("```")
    out.append("")
    out.append("```")
    out.extend(_ascii_planview(hull))
    out.append("```")
    out.append("")

    # STL export via the existing closed-mesh path
    STL_DIR.mkdir(parents=True, exist_ok=True)
    stl = STL_DIR / f"case_{case.key}.stl"
    sha = hull_to_stl(hull, stl)
    out.append(f"**STL** (watertight, `Hull.closed_mesh` via "
               f"`cfd.case.hull_to_stl`): `runs/formcheck/{stl.name}` — "
               f"sha256 `{sha[:16]}…`"
               + (" — ONE demihull; the genome carries one moulded surface "
                  "and the separation is vessel configuration"
                  if case.vessel.n_hulls > 1 else ""))
    out.append("")

    baselines[case.key] = ratchet_entries(d)


def main() -> int:
    write_baseline = "--write-baseline" in sys.argv
    out: list[str] = []
    out.append("# Physical Form Regression Report")
    out.append("")
    out.append("Generated by `scripts/physical_form_report.py` — six "
               "deterministic vessel cases (`navalai.formcheck.CASES`), "
               "each carried through the geometry kernel and the L1 ladder, "
               "with every descriptor judged against the SOURCED ranges this "
               "tree holds. A descriptor with no source in the tree says "
               "`UNKNOWN — no sourced range in tree`; nothing here is an "
               "invented band. Regression fence: "
               "`tests/test_physical_form.py` + "
               "`tests/formcheck_baseline.json` (the ratchet).")
    out.append("")
    out.append("A mathematically admissible hull that passes `grammar.check` "
               "is NOT thereby a successful vessel design — this report is "
               "the record of what the generated forms physically ARE.")
    out.append("")

    baselines: dict[str, dict] = {}
    for case in CASES:
        _case_section(case, out, baselines)

    out.append("## Findings today (non-boat-like traits the layer surfaced)")
    out.append("")
    out.append("These are FINDINGS, not failures — the point of this layer "
               "is that they are now measured, recorded and fenced "
               "(`tests/test_physical_form.py` pins each one until it is "
               "closed with justification):")
    out.append("")
    out.append("1. **Case b entrance angle**: the 15 m round-bilge monohull "
               "delivers a 2%-chord entrance of ~22.9 deg against its "
               "family band of 7-14 deg (approx) — the generated forebody "
               "is blunter than fine-entry practice. (The beamy 5-7 m "
               "hulls' 25-34 deg entrances are largely their L/B: the "
               "arithmetic chord floor alone is 13-19 deg there.)")
    out.append("2. **Transom waterline pinch (all six cases)**: `r_transom` "
               "delivers the transom AREA (0.20 of A_max here) at "
               "near-full local draft, so the transom WATERLINE half-"
               "breadth closes to only ~0.19-0.24 of the maximum beam — "
               "the plan view ends almost in a canoe stern while the SAC "
               "calls it a transom stern. Deep-narrow transom sections are "
               "a kernel section-law consequence worth review; no in-tree "
               "band exists for the waterline-beam ratio (the "
               "MARIN/S64/NPL A_T/A_M 0.31-0.52 citation is "
               "semi-displacement and is quoted as reference only).")
    out.append("3. **Cold-bend violations on the small hard-chine hulls** "
               "(cases a, e, f): minimum panel bend radius 0.3-0.7 m "
               "against the 1.2-1.4 m the ISO-derived ply thickness "
               "demands — the ladder's own verbatim violations above. "
               "Small hulls need thinner (rule-passing) skins or torturable "
               "sheet; recorded, not tuned away.")
    out.append("4. **Uncrewed GM has no bar**: cases e/f are refused a "
               "stability rule set by name (correct), so their GM verdicts "
               "are UNKNOWN — the ladder's crewed-monohull GM floor still "
               "appears in their constraint vector, which is a wiring "
               "question for the rebuild (no drone criterion exists in "
               "tree).")
    out.append("")
    out.append("## Honesty & limitations")
    out.append("")
    out.append("- Entrance angle is `Hull.alpha_e_deg` — the CHORD of the "
               "kernel's first-class design-waterline curve over the forward "
               "2% (and 10%) of LWL. The method is part of the number; a "
               "lines-plan tangent would read differently.")
    out.append("- The run angle, Cwp, LCF, wetted/vol^(2/3), SAC fractions "
               "and KB/BM/KG have NO sourced ranges in this tree and are "
               "reported as UNKNOWN rather than judged against invented "
               "bands.")
    out.append("- Multihull GM is deliberately never given a verdict: no "
               "multihull stability criterion is implemented "
               "(`hydrostatics.multihull_stability_refusal`), and the ladder "
               "violations above carry that refusal verbatim.")
    out.append("- Uncrewed cases are not judged by the recreational drawn-"
               "dimension table, and their GM verdict is UNKNOWN — no rule "
               "set for uncrewed craft exists in the tree.")
    out.append("- Displacement at the design WL uses fresh-water rho = 1000 "
               "kg/m^3 (`geometry.RHO_WATER`).")
    out.append("")
    REPORT.write_text("\n".join(out) + "\n")
    print(f"wrote {REPORT} ({len(out)} lines)")

    if write_baseline:
        BASELINE.write_text(json.dumps(baselines, indent=1, sort_keys=True)
                            + "\n")
        print(f"wrote {BASELINE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
