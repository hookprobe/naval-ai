"""KCS benchmark — the tank-data anchor for the RANS tier (Gate 2M).

Source (primary, not remembered): Tokyo 2015 Workshop on CFD in Ship
Hydrodynamics, "Report of the Results for KCS Resistance & Self-Propulsion
(Case 2-1, 2-5, and 2-7)", Jin Kim, KRISO, 2015-12-03 @NMRI. Distributed in
the workshop proceedings bundle `All_20160729.zip` as
`Day2-AM2-KCS-Resistance_SP-Kim.pdf` (pages 2, 5, 6, 8).

GEOMETRY: that bundle is proceedings PDFs only. The hull comes separately as
`KCS.igs` (I-DEAS Master Series 7, 2000-02-18, 194 unsewn NURBS patches).
Neither the IGES nor the derived STL is committed — workshop geometry may carry
redistribution terms — so both are gitignored and REGENERATED from this recipe:

    python scripts/iges2stl.py downloads/KCS.igs /tmp/kcs_full.stl \\
        --scale 0.001 --z-shift -0.34178 --deflection 0.004 \\
        --sew-tol 1e-3 --mirror-y
    python -c "from navalai.cfd.post import cap_planar_holes; \\
        cap_planar_holes('/tmp/kcs_full.stl','data/benchmark_geom/kcs.stl')"

Why each flag, all measured rather than assumed:
  --scale 0.001   the IGES global section declares 2HMM, i.e. MILLIMETRES, at
                  model scale (x extent 7690 mm vs LPP 7278.6 mm; the excess is
                  bulbous bow forward of FP plus stern overhang aft of AP)
  --z-shift       z=0 in the file is the KEEL, not the waterline; the shift is
                  the model draft, 10.8 m / 31.6 = 0.34178 m
  --sew-tol 1e-3  the 194 patches are unsewn, so each tessellates independently:
                  450 open edges as delivered, of which 397 are patch seams.
                  Sewing at 1e-3 m leaves 4.
  --mirror-y      the distribution is a HALF body (y = 0 .. 0.5107 m)
  cap_planar_holes  closes the one remaining opening, the flat deck at z=+0.1332

VALIDATION of the result (see GEOMETRY_CHECK): submerged volume 1.6474 m^3 vs
published displacement 1.6489 m^3, i.e. -0.09%. That single number confirms the
unit scale, the draft shift, the mirroring and the capping simultaneously.
Wetted surface comes out +1.16% above the published bare-hull 9424 m^2 / 31.6^2,
consistent with Case 2.1 being run WITH the rudder fitted.

Case 2.1 conditions: calm water, model free to sink and trim (FRZ), rudder
fitted, LPP = 7.2786 m (model scale 1:31.6).

WHY A CONTAINERSHIP CALIBRATES A SMALL-CRAFT TOOL — AND WHERE IT STOPS.
KCS is not a design target; it is the ruler. It is the most heavily measured
hull at model scale (KRISO EFD + 13 independent CFD groups), so it answers the
one question our own hulls cannot: when the right answer is KNOWN, does this
solver/mesh/wall-model produce it? Concretely, the own-hull coarse grid gives
C_T/C_F ~ 9.8, which is implausible for any displacement hull — but with no
tank data for that hull, a perfectly converged GCI still cannot say whether the
fault is the hull (immersed transom at an unsuited speed) or the setup (y+,
~50% layer coverage). KCS separates those.

What transfers: VOF free-surface capture, wave resolution, ITTC friction line
and wall treatment, force integration, the C_t definition, and how the mesh
recipe converges. What does NOT transfer: KCS is slender, displacement, Fn
0.26, with no chines, no immersed transom and no spray — none of the physics
that dominates the chined semi-displacement craft this product line targets.

So Gate 2M buys a verified instrument and a known bias floor, NOT a licence to
trust small-craft numbers. This is the plan's own position, not a hedge added
here: BuildPlan §1.3 records Islam & Guedes Soares (2019) — "V&V is
case-specific; you cannot calibrate once on KCS and assume the bounds hold for
novel hulls" — which is why the ladder reports per-design uncertainty.

OPEN GAP (see ALIGNMENT.md): one containership is the wrong anchor SET for this
product line. A second anchor sharing our dominant features is owed — DTMB 5415
(transom stern, already named in the BuildPlan) or, closer to the SKUs, the
Delft Systematic Yacht Hull Series / Series 62 planing data for chined craft.
"""

from __future__ import annotations

# Case 2.1 speed ladder (PDF p.2). Fn = U / sqrt(g * LPP).
LPP = 7.2786                     # m, model scale
SPEEDS_MS = (0.915, 1.281, 1.647, 1.922, 2.196, 2.379)
FROUDE = (0.108, 0.152, 0.195, 0.227, 0.260, 0.282)
REYNOLDS = (5.23e6, 7.33e6, 9.42e6, 1.10e7, 1.26e7, 1.36e7)

# The design point the campaign targets.
DESIGN_FN = 0.260
DESIGN_SPEED = 2.196             # m/s
DESIGN_RE = 1.26e7

# Experimental data, KRISO towing tank (PDF p.5, row "EFD(KRISO)").
EFD = {
    "fn": 0.260,
    "ct": 3.711e-3,              # total resistance coefficient
    "sinkage_m": -1.394e-2,      # negative = sinks
    "trim_deg": -0.169,          # negative = bow down
}

# Finest-grid CT submitted by each participant at Fn 0.26 (PDF p.5, x1e-3).
# This is the "Tokyo-2015 scatter" the gate refers to — 13 groups, grids
# 1.1M-6.6M cells, all VOF/two-equation except one RSM and one level-set.
SUBMITTED_CT_FINEST = {
    "HHI": 3.714e-3,
    "KRISO": 3.707e-3,
    "NUMECA": 3.726e-3,
    "PNU": 3.620e-3,
    "SJTU": 3.733e-3,
    "UDE_FINEMarine": 3.728e-3,
    "UNIZAG-FSB": 3.726e-3,
}

# Grid uncertainty U_G as % of the fine-grid solution, reported by the groups
# that ran a formal V&V (PDF p.6). This is the honest bar: ~2.5-3.5% is what
# careful practitioners achieved on this case, so a GCI target of <=2.5% is a
# stretch goal, not a routine expectation.
REPORTED_GRID_UNCERTAINTY_PCT = {
    "KRISO": 2.7,
    "NUMECA": 3.07,
    "PNU": -2.57,                # sign as printed; magnitude is the bar
    "SJTU": 3.51,
    "UNIZAG-FSB": 9.39,
}


# Published model-scale particulars, and what the regenerated STL measured.
# Volume is the strong check: it is sensitive to unit scale, draft shift and
# mirroring all at once, so a 0.09% match is not a coincidence.
GEOMETRY_CHECK = {
    "scale_ratio": 31.6,
    "displacement_m3": 52030 / 31.6 ** 3,     # 1.6489, from full-scale 52030
    "measured_submerged_m3": 1.6474,
    "displacement_error_pct": -0.09,
    "wetted_surface_m2": 9424 / 31.6 ** 2,    # 9.4376, bare hull
    "measured_wetted_m2": 9.5475,             # +1.16%: rudder is fitted
    "draft_m": 10.8 / 31.6,                   # 0.34178
    "beam_m": 32.2 / 31.6,                    # 1.019
}


def scatter_band() -> tuple[float, float]:
    """(min, max) of the finest-grid submitted CT at Fn 0.26."""
    v = tuple(SUBMITTED_CT_FINEST.values())
    return min(v), max(v)


def error_vs_efd(ct: float) -> float:
    """E%D = (EFD - CFD)/EFD * 100, the sign convention used in the report."""
    return (EFD["ct"] - ct) / EFD["ct"] * 100.0


def within_scatter(ct: float, margin: float = 0.0) -> bool:
    """Is a computed CT inside the Tokyo-2015 participant scatter band?

    `margin` widens the band by a fraction (0.05 = 5%) when a softer check is
    wanted; Gate 2M itself uses margin=0. Widening the band to pass is exactly
    the move the honesty rules forbid, so any non-zero margin belongs in
    exploratory work, never in the gate.
    """
    lo, hi = scatter_band()
    return lo * (1.0 - margin) <= ct <= hi * (1.0 + margin)
