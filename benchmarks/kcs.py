"""KCS benchmark — the tank-data anchor for the RANS tier (Gate 2M).

Source (primary, not remembered): Tokyo 2015 Workshop on CFD in Ship
Hydrodynamics, "Report of the Results for KCS Resistance & Self-Propulsion
(Case 2-1, 2-5, and 2-7)", Jin Kim, KRISO, 2015-12-03 @NMRI. Distributed in
the workshop proceedings bundle `All_20160729.zip` as
`Day2-AM2-KCS-Resistance_SP-Kim.pdf` (pages 2, 5, 6, 8).

GEOMETRY — USE `kcs_cfd_ready_final.igs` (NAPA export), NOT `KCS.igs`.
Two sources were tried and the difference decides whether the case runs at all:

  KCS.igs                    I-DEAS Master Series 7 (2000), 194 entities ->
                             18 faces, HALF body, mm, z=0 at the KEEL.
                             Needs mirroring; mirroring lays a ~4.8 mm sliver
                             ribbon down the keel because its centreline
                             vertices sit at y = 2.4 mm. Meshes to 14
                             zero-volume cells and 73 wrongly oriented faces,
                             and interFoam dies on the first timestep. At
                             sew tolerance 1e-4 it is OCC-INVALID (2 shells).

  kcs_cfd_ready_final.igs    NAPA, "TOIGES IGES,HULL,PTOL=0.002", 1558
                             entities -> 649 faces, FULL hull, FULL SCALE in
                             mm, and z=0 ALREADY at the design waterline.
                             No mirroring, no z-shift. Sews to ONE valid shell
                             at every tolerance from 1e-5 up.

Working recipe (produces 0 zero-volume cells, 0 wrongly oriented faces,
Failed 1 mesh check — the same as our own hull — and interFoam runs):

    python scripts/iges2stl.py downloads/kcs_cfd_ready_final.igs /tmp/k.stl \\
        --scale 3.164609e-05 --sew-tol 1e-5 --deflection 0.004
    # then, in python: weld_vertices(tol=5e-5) -> cap_planar_holes(
    #   only_axis=2, only_value=<deck z, 0.40214>, only_tol=3e-3)

  --scale 3.164609e-05  = 0.001 / (230 / 7.2786): mm full-scale -> m at 1:31.5995
  --deflection 0.004    MEASURED, and NOT "finer is better": self-intersections
                        after welding go 0.0005 -> 6, 0.001 -> 7, 0.002 -> 9,
                        0.004 -> 3. Only 0.004 meshes with no zero-volume cells.
  weld_vertices         the raw tessellation carries a ZERO-LENGTH edge and
                        zero-area triangles; welding drops 24 of them and cuts
                        self-intersections 22 -> 7.

A handful of residual self-intersections is expected and tolerable here: Case
2.1 is run WITH the rudder, and an appendage genuinely intersecting the hull is
a union, which snappy resolves.

The older half-body path is kept in the notes below only as the record of why
it does not work.
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

VALIDATION of the result (see GEOMETRY_CHECK): submerged volume 1.644484 m^3 vs
published displacement 1.6488934 m^3, i.e. -0.267%. That single number confirms
the unit scale, the draft shift, the mirroring and the capping simultaneously.
(It read -0.09% here until 2026-08-06, against 1.6474 m^3. RE-MEASURED with
`navalai.cfd.post.stl_submerged_properties` on the committed recipe's actual
output — the file whose hash `data/benchmark_geom/CHECKSUMS.json` pins — the
volume is 1.644484 m^3. The 0.18% disagreement was invisible because the test
compares at rel=0.01. Two figures for one measurement is the J1 defect; the one
kept is the one that can be re-run.)
Wetted surface comes out +1.16% above the published bare-hull 9424 m^2 / 31.6^2,
consistent with Case 2.1 being run WITH the rudder fitted.

Case 2.1 conditions: calm water, model free to sink and trim (FRZ), rudder
fitted, LPP = 7.2786 m (model scale 1:31.6).

WHY A CONTAINERSHIP CALIBRATES A SMALL-CRAFT TOOL — AND WHERE IT STOPS.
KCS is not a design target; it is the ruler. It is the most heavily measured
hull at model scale (KRISO EFD + the 7 CFD groups transcribed in
`SUBMITTED_CT_FINEST`), so it answers the
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

# Vertical centre of gravity, metres ABOVE THE KEEL, model scale.
#
# THIS NUMBER EXISTED ONLY IN A COMMENT IN navalai/cfd/case.py UNTIL
# 2026-08-12, which is why it belongs here: benchmarks/kcs.py is the single
# source for KCS constants, and a value a caller has to retype from a comment
# is a number with no source at all.
#
# It is the one mass property a hull SHAPE cannot supply -- it depends on how
# the model is ballasted -- so `motion_from_geometry` takes it as an argument
# and WARNS when it is absent. Defaulting to VCB answers a different ship:
# MEASURED on KCS, VCB gives KG-above-keel 0.187 m against this 0.2303, i.e.
# 19% low, and KG is the lever that sets trim under a towing force.
#
# It is what the FREE sinkage-and-trim experiment needs. KCS Case 2.1 is towed
# FREE to sink and trim and we solve FIXED, which is a known part of the Gate
# 2M error and the part the viscous/pressure split localises: viscous is right
# at 1.161x ITTC-57 while pressure carries 2.32x. EFD's free-condition
# attitude is recorded immediately below as the acceptance data.
KG_ABOVE_KEEL_M = 0.2303

# Experimental data, KRISO towing tank (PDF p.5, row "EFD(KRISO)").
EFD = {
    "fn": 0.260,
    "ct": 3.711e-3,              # total resistance coefficient
    "sinkage_m": -1.394e-2,      # negative = sinks
    "trim_deg": -0.169,          # negative = bow down
}

# Finest-grid CT submitted by each participant at Fn 0.26 (PDF p.5, x1e-3).
# This is the "Tokyo-2015 scatter" the gate refers to — SEVEN groups, which is
# how many are transcribed below and how many the band is computed from.
# It said "13 groups" here and "13 independent CFD groups" in the module
# docstring, i.e. the band was attributed to nearly twice the evidence anyone
# can check in this file. Whatever the workshop total was, the band this gate
# uses is min/max over these seven rows, so seven is the number that may be
# claimed. Transcribe the rest from the PDF and this comment moves with it.
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
# mirroring all at once, so a 0.27% match is not a coincidence.
# THESE TWO NUMBERS DISAGREED WITH data/benchmark_geom/CHECKSUMS.json (gap
# F18): this file said 1.6474 / -0.09%, the checksum record said 1.644484 /
# -0.267% from re-running stl_submerged_properties on the committed file. The
# checksum record wins because it is the one produced by re-measurement, and
# the test's rel=0.01 had been hiding the 0.18% gap between them.
GEOMETRY_CHECK = {
    "scale_ratio": 31.6,
    "displacement_m3": 52030 / 31.6 ** 3,     # 1.6489, from full-scale 52030
    "measured_submerged_m3": 1.644484,
    "displacement_error_pct": -0.267,
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
