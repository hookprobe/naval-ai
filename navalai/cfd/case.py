"""OpenFOAM resistance-case generator (interFoam free-surface, snappyHexMesh).

Deterministic: same hull + same settings -> byte-identical case directory,
so the case dir hash goes into provenance. Runner: cfd/run-case.sh.
GATE STATUS: METAL-GATED — requires a machine with OpenFOAM (.com or .org
2306+); this box has none, so Gate 3 (KCS/JBC calibration) stays RED here.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np

from ..geometry import Hull

# Total z-expansion across the DEEP block (coarsest cell / finest cell). Held
# FIXED while cell counts scale, which is what makes the refinement
# systematic: every cell dimension then shrinks like 1/scale together. Fixing
# the per-cell ratio instead would shrink the interface cell exponentially in
# n and the three grids would not be a refinement family at all.
#
# THE AIR BLOCK NO LONGER USES THIS — see `_z_grading`. The deep block still
# does, AND THAT IS A MEASUREMENT, NOT AN OMISSION. This value is INVERTED on
# the deep block (it puts the block's coarsest cell, 3.30 m, against the
# 402 mm core band and its finest, 165 mm, at the tank floor where nothing
# happens), so correcting it was the obvious companion change. MEASURED
# 2026-08-12 over the 25-hull seed-0 batch at n_layers=7, and the data refuse
# it: correcting BOTH blocks took the run-case.sh bar from 19/25 to **16/25**,
# fixing hulls 4, 14 and 18 and breaking 0, 1, 6, 8, 20 and 22. The controlled
# pair on hull 0, which is clean at baseline:
#
#     hull 0   air derived, deep 20.0   619094 cells   0 zeroVol    0 wrongOri  skew  3.17  CLEAN
#     hull 0   air 20.0, deep derived   680425 cells   0 zeroVol    0 wrongOri  skew  4.52  CLEAN
#     hull 0   BOTH derived             686237 cells  30 zeroVol  324 wrongOri  skew 53.62  REFUSED
#
# Each change alone is clean and the pair is not, so there is no additive
# story to tell and no measurement that says the deep block is hurting
# anything. Changing it is therefore an unmotivated change to a shared
# constant that the KCS benchmark also rides on. It stays until something
# measures it.
_Z_EXPANSION = 20.0

# CEILING on the ratio between ADJACENT cells inside the DERIVED air grading.
# A total expansion is the wrong quantity to bound: 20.0 over the air block's
# 4 cells is a per-cell ratio of 2.714 (too aggressive) while the same 20.0
# over the deep block's 7 cells is 1.648 (mild), so one number bounded
# neither. The adjacent-cell ratio is the standard CFD guideline and it is
# what the finite-volume discretisation actually sees.
_Z_CELL_RATIO_MAX = 2.0


def _z_grading(dz_core: float, height: float, n: int, core_below: bool,
               cap: float = _Z_CELL_RATIO_MAX) -> float:
    """blockMesh `simpleGrading` z-ratio for a graded OUTER z-block, derived so
    its cell AT THE SHARED FACE equals the ungraded core band's cell.

    THE DEFECT THIS REPLACES, MEASURED 2026-08-12 on Gate 2U hull 4 (lwl
    8.9417, seed-0 batch). `_Z_EXPANSION` 20.0 was applied to both outer
    blocks as `simpleGrading (1 1 20.0)`, i.e. last cell / first cell = 20 with
    z increasing UPWARD. Consequences at scale 1, in units of Lwl (they are
    scale-free, so they held on every case this project has ever meshed):

        block   height   n   cell AT the core band   core band cell   jump
        air     0.160L   4   0.00515L (46.0 mm)      0.045L (402 mm)  8.74x
        deep    0.910L   7   0.36923L (3.301 m)      0.045L (402 mm)  8.20x

    The air block's grading was the right DIRECTION and eight times too
    strong: it made the first air cell 8.74x FINER than the ungraded cell
    beneath it, so the mesh got finer moving AWAY from the free surface and
    then coarser again. The deep block's grading was INVERTED: it put the
    block's coarsest cell (3.3 m) against the 402 mm core band and its finest
    (165 mm) at the tank floor, where nothing happens.

    The first air cell is 705.9 mm x 705.9 mm x 46.0 mm — 15.3:1 — and
    `hexRef8` preserves aspect ratio at every level, so at hull refinement
    level 4 it is 44.1 x 44.1 x 2.88 mm, still 15.3:1. That is CLAUDE.md's
    2026-08-05 root cause (snap displacement scales with the LONG edge, so a
    few-mm move is several cell HEIGHTS and the cell folds) reintroduced in a
    46 mm horizontal slab that no hull feature marks. The ratio is a CONSTANT
    15.335 for every hull, because dx and the first air cell are both
    proportional to Lwl.

    MEASURED on hull 4, geometry byte-identical (stl_sha256 3f8c87ae..), same
    n_layers=7, MESH_ONLY, only this constant moving:

        config                         cells   zeroVol  wrongOri   skew   nonOrtho
        _Z_BANDS 0.09, _Z_EXPANSION 20 916677     0        38     10.3992  98.9835
        _Z_BANDS 0.12, _Z_EXPANSION 20 843124     0        14      8.6104  89.1700
        _Z_BANDS 0.09, _Z_EXPANSION  1 1106081    0         0      2.4415  69.1067
        AIR derived, deep left at 20    935021    0         0      5.4157  69.9393

    and the 38 faces are LOCATED BY THE MESH, not by the hull. Decoded from
    `wrongOrientedFaces` via foamToVTK: at bands 0.09 they sit at z 0.8105 ..
    0.8365 inside the first air cell [0.804755, 0.850783]; at bands 0.12 they
    MOVED WITH THE BOUNDARY to z 1.0774 .. 1.0897 inside [1.073006, 1.110405].
    A defect that is a horizontal plane while x sweeps 0.44 Lwl, and that
    follows a blockMesh vertex when the geometry does not move, is not a
    geometry defect. Commit bbf1a47 (the chine became a row of the grid,
    removing a ~10 mm deviation floor) changed the surface underneath these
    faces and not one of the 38 moved.

    `core_below` is True for the air block (the core band is beneath it, so
    the block's FIRST cell is the shared one and it grows upward, grading >= 1)
    and False for the deep block (the core band is above it, so the block's
    LAST cell is the shared one and cells grow DOWNWARD, grading <= 1).
    ONLY THE AIR BLOCK CALLS THIS — the deep block keeps `_Z_EXPANSION`,
    because correcting both regressed the batch from 19/25 to 16/25. See the
    `_Z_EXPANSION` comment for the controlled pair.

    Returns 1.0 (uniform) when the block cannot hold `n` cells starting at
    `dz_core` — height/n < dz_core means even a uniform block is finer than the
    core, which is the air block's situation at the shipped proportions
    (0.160L / 4 = 0.040L against a 0.045L core, an 0.89x step).

    `cap` bounds the ADJACENT-cell ratio, so a match is not always reachable: a
    planing tank deepens itself as U^2 (depth = 1.5*lambda/2) while dz_core
    does not move. MEASURED on hull 4 at scale 1, deep block, n=7: the match
    holds exactly (1.00x) to U = 8 m/s, and at U = 20 m/s — a 192 m tank on an
    8.9 m hull — the cap binds and the step is 3.74x, still under the 5.6:1
    that CLAUDE.md records as the anisotropy bar. `case.info` records the
    achieved step as `z_step_wave_to_air` / `z_step_deep_to_hull`.
    """
    if n < 2 or dz_core <= 0.0 or height <= 0.0:
        return 1.0
    # Required sum of the geometric series, in units of the shared-face cell.
    target = height / dz_core
    if target <= n:                      # uniform is already finer than dz_core
        return 1.0
    lo, hi = 1.0, float(cap)
    if sum(hi ** i for i in range(n)) <= target:
        r = hi                           # the cap binds; see _Z_CELL_RATIO_MAX
    else:
        for _ in range(200):             # bisection on the ADJACENT-cell ratio
            mid = 0.5 * (lo + hi)
            if sum(mid ** i for i in range(n)) < target:
                lo = mid
            else:
                hi = mid
        r = 0.5 * (lo + hi)
    return r ** (n - 1) if core_below else r ** -(n - 1)

# Free-surface refinement slab, as multiples of LWL (hull occupies x in [0,L]).
# Refining the whole tank buys nothing for hull forces and costs the run:
# every refined cell is paid for at every one of the ~13k timesteps that
# maxAlphaCo sets. The slab covers the hull and the near wake, where the
# pressure field that makes the drag actually lives.
# Free-surface refinement box, as fractions of Lwl. z is the HALF-height of the
# band that gets the fine cells. It was 0.05 (+-0.36 m on KCS) against a wave
# field of roughly +-0.06 m — six times taller than the physics occupies, and
# every one of those cells was paid for in wall-clock. 0.025 still leaves ~3x
# the wave amplitude for sinkage, the bow wave crest and the transom trough.
_FS_BOX = dict(x0=-1.6, x1=1.3, y=0.7, z=0.025)

# Target y+ for the wall functions (build plan: y+ ~ 30, SJTU KCS pipeline).
# MEASURED before this was computed rather than assumed: 3 relative-sized
# layers gave y+ min 42 / avg 7491 / max 60017 on the hull -- one to three
# orders of magnitude outside where nutkWallFunction is valid. Skin friction
# is most of this hull's drag at Fn 0.26, so that is not a rounding error.
# TARGET y+ 100, NOT 30, AND FIVE LAYERS AT 1.2 — the Wolf Dynamics KCS
# reference regime, adopted after measuring why we had NO LAYERS AT ALL.
#
# The old settings asked for a 0.795 mm first layer at y+ 30 with 3 layers at
# expansion 1.3: a 3.06 mm stack against a 19 mm hull cell, i.e. a 28:1 jump
# from the last layer to the first background cell, and a stack covering 3.2%
# of the boundary layer. snappy's medial-axis solver will not bridge that: it
# extruded 44.98% of the hull faces on iteration 0 and DECAYED TO ZERO over 35
# iterations. Meanwhile the summary table kept printing the REQUESTED spec, so
# run-case.sh and CLAUDE.md both reported "3 of 3 layers, near-wall 0.795 mm"
# on a mesh with no prism cells whatsoever, for weeks.
#
# MEASURED with y+ 100 / 5 layers / 1.2 (first 2.65 mm, stack 19.7 mm, jump
# 4.5:1, ~20% of delta — the reference's proportions):
#     Extruding 11056 out of 11153 faces (99.13%)   coverage 97.4%
# 30 is also the WRONG target for a wall-function mesh whose measured min y+
# was already 12.8, i.e. in the buffer layer where nutkWallFunction is least
# valid. 100 puts the low-friction regions near 47, safely in the log layer.
_TARGET_YPLUS = 100.0
_LAYER_EXPANSION = 1.2

# snappy refinementSurfaces level (min, max) on the hull. MEASURED why this
# matters: at (2 3) the FLAT hull areas take only level 2, i.e. background/4
# ~208 mm, so a 0.7 mm first layer would need ~15 layers to bridge and snappy
# inserts almost none. The consequence, from a wetted-only y+ pass on the
# coarse grid at t=25: median y+ 11431 and only 2.0% of WET faces inside the
# 30<=y+<=300 wall-function band. Skin friction then came out 2.62x the
# ITTC-57 line. Raising this shrinks the local cell so a short layer stack can
# actually reach the wall.
# snappy surface refinement. The DTCHull reference uses level (0 0) — snappy
# SNAPS and adds LAYERS, it does not refine. All refinement happens beforehand
# with topoSet+refineMesh, which can refine x,y WITHOUT z. Raising this
# reintroduces the isotropic hanging-node transitions that produced wrongly
# oriented faces at (3 4) and zero-volume cells at (4 5).
# MEASURED on the isotropic background (aspect 1.85:1, was 38:1). The old
# background could not survive (3,4) -- 3 zero-volume / 49 wrongly-oriented
# faces -- because snappy refines ISOTROPICALLY, so a 38:1 cell stays 38:1 at
# every level while its height shrinks absolutely, and the snap displacement
# (which scales with the LONG edge) folds the cell inside out. Deriving dz
# from dx fixes it at the source: (2,3)/(3,4)/(4,5) are now ALL clean, and
# layer coverage went 32% -> 75% because layers insert into well-shaped cells.
_HULL_REFINE = (4, 5)

# z band extents as multiples of LWL. The CELL SIZE is no longer set here:
# it is derived to match dx so the background cell is ISOTROPIC.
#
# THE REASON, measured. snappyHexMesh refines ISOTROPICALLY, so whatever aspect
# ratio the background has is PRESERVED at every refinement level. Our old
# background was 606 x 910 x 16 mm — 38:1 — so at hull refinement (3 4) snappy
# was snapping cells 57 mm long and 1.0 mm tall, and at (4 5) 0.5 mm tall. Its
# snap displacement scales with the LONG edge, so a few-mm move is several cell
# HEIGHTS and the cell folds inside out: the "incorrectly oriented faces" and
# zero-volume cells that blocked every refinement past (2 3).
# DTCHull starts from the same 42:1 background but refines x,y ONLY, ending at
# 0.66:1 — nearly cubic — before snappy ever snaps. Same destination, reached
# the other way: we make the background cubic and let snappy stay cubic.
# Ungraded core bands above and below the waterline, as a fraction of Lwl.
# They are EQUAL so both hold near-cubic cells: a thin 0.03 band divided into
# the >=2 cells the refinement family needs gave 109 mm cells against a 607 mm
# dx (5.6:1), reintroducing the very anisotropy the isotropic background fixed.
_Z_BANDS = dict(hull=0.09, wave=0.09)

# refineMesh rounds. Each halves x and y inside a box that tightens toward the
# hull, so the near-hull cell is background/2**rounds in x,y while z keeps the
# blockMesh value. 4 rounds take a 0.61 m background cell to ~38 mm.
# z-only refineMesh rounds run AFTER snappy, in the free-surface band. Each
# halves the cell HEIGHT there, giving the interface the thin cells VOF needs
# without ever handing snappy an anisotropic mesh to snap.
_REFINE_ROUNDS = 3
# Tank extents, as multiples of Lwl, DECLARED ONCE. The half-width appeared
# three times — in `y_half` (which was computed and never read), in the
# blockMesh `y0`/`y1` entries, and inside the ny expression — and it is the
# third that decides the refinement family, so a drift between them would be
# invisible until a GCI came out wrong.
_DOMAIN_X = (-2.5, 2.0)                       # inlet .. outlet, x/Lwl
_DOMAIN_LENGTH_L = _DOMAIN_X[1] - _DOMAIN_X[0]
_DOMAIN_HALF_WIDTH_L = 1.5                    # y/Lwl, one side

# THE BACKGROUND x COUNT AT scale = 1, IN ONE PLACE.
# It was the literal `54` in two expressions — `_write_case_dicts` and
# `write_resistance_case`'s STL-resolution estimate — which is this project's
# documented anti-pattern (a number declared twice) in the file carrying the
# two RED gates.
#
# 57, NOT 54, AND THE THREE IS THE WHOLE POINT. ny is nx/3 (symmetric) or 2nx/3
# (full), so ny's own refinement ratio equals nx's only when nx divides by 3 at
# EVERY member of the family. At 54 the family is 54 / 76 / 108 and only the
# ends divide, so ny went 18 / 25 / 36 with ratios 1.3889 and 1.4400 against
# nx's 1.4074 and 1.4211 — ny was rounding independently and its error is
# largest on the SYMMETRIC domain, where the count is half the size.
# MEASURED spread between the two refinement steps (|r23-r12| / max):
#
#     base   family        symmetric        full domain
#      54    54/76/108     0.85%            0.47%
#      57    57/81/114     0.03%            0.03%
#
# 57*sqrt(2) = 80.61 -> 81, which also divides by 3, and 114 = 2*57; so the
# whole triplet is a multiple of 3 and ny is EXACT at every member. The cost is
# measured and real: (57/54)^3 = +19% cells at every grid. That buys a family
# whose two steps agree to 0.03% instead of 0.85%, which is what Richardson
# extrapolation assumes and what CLAUDE.md's recorded 0.47% claimed while the
# symmetric runs it recommends were at 0.85%.
_NX_BASE = 57

# y cells per x cell in the background, so ny is DERIVED from nx by a fixed
# ratio rather than re-rounded from a float division of the domain width.
# The half domain gets exactly half the cells of the full one — it must, or a
# `--symmetric` run is not the full run with the mirror removed but a
# different discretisation wearing the same scale number.
_NY_PER_NX_HALF = _DOMAIN_HALF_WIDTH_L / _DOMAIN_LENGTH_L

# z cells per x cell in the background. 14/54 reproduces the hand-tuned scale-1
# mesh exactly; everything else follows from it. (At _NX_BASE 57 it gives 15,
# and the background aspect ratio dx/dz_core is 1.75 against 1.85 at 54 — the
# near-cubic property the isotropic-background fix depends on is preserved.)
_NZ_PER_NX = 14.0 / 54.0

# Layers snappy will actually INSERT on this hull, measured (coarse grid,
# absolute first-layer thickness held at y+ 30):
#   n=3 -> 50.3%   n=5 -> 36.5%   n=8 -> 26.2%   n=15 -> 11.2%
# and loosening nLayerIter/nRelaxedIter changed nothing. A layer that is not
# inserted controls no y+ at all, so coverage wins over stack depth: the ideal
# bridging depth is still computed, and case.info records both so the gap is
# visible rather than silently absorbed.
# CAP, not a target. `n_layers_to_bridge` computes how many layers it takes to
# reach the adjacent cell, and that is what should decide; this only stops an
# absurd stack. It was 3, from a measurement ("n>=6 collapses coverage AND
# crashes interFoam") taken on the OLD 38:1 anisotropic background, which
# CLAUDE.md marks SUPERSEDED. Raised to 10 because a 52 mm hull cell on a 10 m
# hull needs ~9 layers to bridge at expansion 1.2, and capping at 5 there
# reproduces exactly the 0.08-of-cell ratio that produced ZERO layers on KCS.
# The opposite failure — a stack thicker than its host cell — is now caught by
# the stack/hull_cell check below, so both ends are guarded.
# LOWERED 10 -> 7 on 2026-08-11 by the Gate 2U coarse campaign, which measured
# the cap being the defect rather than the guard. At 10 the derivation asks for
# 8-10 on EVERY grammar hull and snappy achieves 3.9-8.1 — not one hull hit its
# request, and a PARTIAL stack is the documented cell-folding mechanism
# (CLAUDE.md, KCS: n=3 97.7% clean, n=5 92.6% solves, n=7 81.2% DIES). The
# campaign's own controlled pair:
#     hull 0  n=10 -> 12 zeroVol, 92 wrongOri, skew 23.76   REFUSED
#     hull 0  n= 7 ->  0 zeroVol,  0 wrongOri, skew  4.52   clean
#     hull 1  n= 9 ->  0 zeroVol,  8 wrongOri, skew 25.37   REFUSED
# and across the batch, requested-vs-achieved tracks the damage: hull 12 asked
# 10, achieved 4.31, produced 258 wrongly-oriented faces; hull 11 asked 9, got
# 3.91, 130 wrong. The clean hulls sit at the TOP of the achieved range
# (7.43, 6.64, 5.99), which is what "complete stack" looks like.
# NOT 5, and not back to 3: this file already records that capping at 5 on a
# 52 mm hull cell reproduces the 0.08-of-cell ratio that gave ZERO layers on
# KCS, and the 3 came from a measurement on the SUPERSEDED 38:1 anisotropic
# background. 7 is the largest count MEASURED clean on this mesh family.
_MAX_LAYERS = 7

# Angle across which layers may continue. 170 is the Wolf Dynamics KCS
# reference value and snappy's own DTCHull default; 60 terminated extrusion at
# the keel, transom, deck edge and bulb — see the SNAPPY_STUB comment.
_LAYER_FEATURE_ANGLE = 170

# LTS pseudo-iteration budget for a fixed-attitude resistance solve. The Wolf
# Dynamics reference uses 10000; a steady KCS resistance typically converges in
# 1-3k, and the drift criterion in gate2m decides when it HAS converged rather
# than this number. Sized so the coarse grid fits a 10-core workstation budget.
_LTS_ITERATIONS = 2000


# FLUID PROPERTIES, ONCE. The audit found rho declared FIVE times in this file,
# nu twice and g four times — the project's own documented anti-pattern, in the
# module that carries the two RED gates. They are constants now, and every
# template and helper below formats them in rather than retyping them.
#
# THAT CLAIM WAS FALSE WHEN IT WAS WRITTEN, and a claim of single-sourcing is
# worse than no claim: it stops the next reader from looking. RE-MEASURED
# 2026-08-06 — rho 998.8 also appeared as `motion_from_geometry`'s default
# argument and hardcoded in BOTH forces function objects (`forces` and
# `forceCoeffs`), nu 1.09e-6 as `first_layer_thickness`'s default, and g 9.81
# in the GRAVITY template (a plain string, so it could not format anything),
# in the deep-water half-wavelength and in the wavelength receipt. Eight
# restatements under a comment saying there were none.
# `tests/test_cfd_gap_closure.py` now greps this file for the bare digits, the
# way `tests/test_limits_single_source.py` does for limits.py, so the claim is
# enforced instead of asserted.
_G = 9.81               # matches constant/g in the generated case
_RHO_WATER = 998.8      # kg/m^3, ~20 C fresh water
_RHO_AIR = 1.2
_NU_WATER = 1.09e-6     # m^2/s
_NU_AIR = 1.48e-5
# Surface tension is set to ZERO, matching the Wolf Dynamics KCS reference.
# At model scale We >> 1 so it is physically negligible, but the CSF force
# sigma*kappa*grad(alpha) is evaluated on our ~15:1 interface cells sitting on
# refineMesh hanging nodes, where it is a known source of spurious currents —
# i.e. it contributes nothing but noise to exactly the cells that matter.
_SIGMA_WATER = 0.0


def sixdof_properties(mass_kg: float, cog: tuple[float, float, float],
                      k_roll: float, k_pitch: float, k_yaw: float,
                      lwl: float, awp_m2: float, symmetric: bool,
                      i_l_m4: float | None = None,
                      rho: float = _RHO_WATER, zeta: float = 0.3) -> dict:
    """Mass, inertia and damper coefficients for the sixDoF motion dict.

    THE HALVING LIVES HERE, not in the caller. A symmetric case meshes half the
    hull, so it feels half the hydrodynamic force — and must therefore carry
    half the mass and half the inertia, or the model accelerates at twice the
    right rate and settles at the wrong sinkage. Making a caller remember that
    is how we ended up reporting forces that were exactly 2x wrong once already.

    Radii of gyration are about the centre of mass, in metres. Dampers are set
    from the HEAVE mode: the restoring stiffness of a floating body is
    rho*g*Awp, and added mass at these frequencies is of order the displaced
    mass, so m_eff ~ 2m. c_crit = 2*m_eff*omega_n, and we use a fraction zeta
    of it. Damping acts on velocity, so it is exactly zero at equilibrium and
    cannot bias the converged answer.
    """
    half = 0.5 if symmetric else 1.0
    m = mass_kg * half
    awp = awp_m2 * half

    k_heave = rho * _G * awp                      # N/m
    m_eff = 2.0 * m                              # + added mass, same order
    omega_n = math.sqrt(k_heave / max(m_eff, 1e-9))
    c_lin = zeta * 2.0 * m_eff * omega_n         # N s/m

    i_pitch = m * k_pitch ** 2
    # Angular critical damping on the pitch mode. The restoring stiffness is
    # rho*g*I_L, and I_L is MEASURED from the waterplane when the caller can
    # supply it. The old approximation Awp*(lwl/2)^2 treats the waterplane as
    # two point areas at the ends: on KCS it gives 771030 N.m/rad against a
    # true 194539 — 3.96x too stiff — which put the damper at zeta 0.597
    # instead of 0.30 and roughly doubled the settling time.
    i_l = (i_l_m4 * half) if i_l_m4 is not None else (awp * (0.5 * lwl) ** 2)
    k_theta = rho * _G * i_l
    omega_p = math.sqrt(k_theta / max(2.0 * i_pitch, 1e-9))
    c_ang = zeta * 2.0 * (2.0 * i_pitch) * omega_p

    return {
        "mass": m, "cog_x": cog[0], "cog_y": cog[1], "cog_z": cog[2],
        "ixx": m * k_roll ** 2, "iyy": i_pitch, "izz": m * k_yaw ** 2,
        "inner": 0.05 * lwl, "outer": 0.17 * lwl,
        "c_lin": c_lin, "c_ang": c_ang,
    }


def motion_from_geometry(stl_path, lwl: float, symmetric: bool,
                        kg_above_keel: float | None = None,
                        k_roll_over_beam: float = 0.40,
                        k_pitch_over_lwl: float = 0.25,
                        cwp: float = 0.80, rho: float = _RHO_WATER) -> dict:
    """Free sinkage-and-trim properties, derived from the hull itself.

    The model must FLOAT at its own displacement, so mass = rho * submerged
    volume and LCG = LCB — taking either from a published percentage would be
    a second source of truth that can disagree with the geometry we actually
    mesh. (It also sidesteps a real problem: the KCS STL spans 0..7.7165 m
    against Lpp 7.2786, because bulb and rudder reach past the perpendiculars,
    so "-1.48% Lpp from midship" cannot be located in this file's coordinates.)

    Only KG is not derivable from a hull shape — it depends on how the model is
    ballasted — so it is the one number a caller may supply. Falling back to VCB
    means neutral placement, which is honest but will not reproduce a specific
    model's trim.
    """
    from .post import (WaterplaneError, stl_submerged_properties,
                       stl_waterplane_properties)

    props = stl_submerged_properties(stl_path, 0.0)
    # The waterplane is MEASURED, not assumed. `cwp` remains only as the
    # fallback for a geometry whose waterplane cannot be closed; on KCS the
    # measured C_wp is 0.829 against the 0.80 assumption, and the measured I_L
    # is what the pitch damper actually needs.
    try:
        wp = stl_waterplane_properties(stl_path, 0.0)
        awp, i_l = wp["awp_m2"], wp["i_l_m4"]
    except WaterplaneError:
        awp, i_l = None, None
    tris = np.asarray(_read_stl_tris_for_motion(stl_path), float)
    keel_z = float(tris[:, :, 2].min())
    beam = 2.0 * float(np.abs(tris[:, :, 1]).max())
    if awp is None:
        awp = cwp * lwl * beam

    if kg_above_keel is None:
        # KG is the one mass property a hull SHAPE cannot supply — it depends
        # on how the model is ballasted — and defaulting to VCB silently
        # answers a different ship. MEASURED on KCS: VCB gives KG-above-keel
        # 0.187 m against the published 0.2303 m, 19% low, and KG is the lever
        # that sets trim. Say so rather than let it pass as a derived number.
        import warnings
        warnings.warn(
            "no kg_above_keel given: VCG defaults to VCB (neutral ballast). "
            "This is NOT a specific model's ballast condition — on KCS it is "
            "19% below the published KG — and trim will not reproduce EFD.",
            stacklevel=2)
    vcg = keel_z + kg_above_keel if kg_above_keel is not None else props["vcb"]
    return sixdof_properties(
        mass_kg=rho * props["volume_m3"],
        cog=(props["lcb"], 0.0, vcg),
        k_roll=k_roll_over_beam * beam,
        k_pitch=k_pitch_over_lwl * lwl,
        k_yaw=k_pitch_over_lwl * lwl,
        lwl=lwl, awp_m2=awp, i_l_m4=i_l, symmetric=symmetric, rho=rho)


def _read_stl_tris_for_motion(path):
    from .post import _read_stl_tris
    return _read_stl_tris(path)


def first_layer_thickness(speed: float, lwl: float, target_yplus: float,
                          nu: float = _NU_WATER) -> float:
    """Absolute first-layer THICKNESS [m] that lands the first cell centre at
    `target_yplus`, via the ITTC-1957 flat-plate friction line.

    y+ = u_tau * y / nu with y the cell CENTRE, so the cell is twice that.
    """
    re = speed * lwl / nu
    cf = 0.075 / (math.log10(re) - 2.0) ** 2
    u_tau = speed * math.sqrt(cf / 2.0)
    return 2.0 * target_yplus * nu / u_tau


def n_layers_to_bridge(t1: float, cell: float, expansion: float) -> int:
    """Layers needed for a stack of first-thickness `t1` to reach `cell`.

    A stack that stops far short leaves a large size jump at its top, which is
    where snappy gives up and coverage collapses.
    """
    if t1 <= 0 or cell <= t1:
        return 3
    n = math.log(1.0 + (cell / t1) * (expansion - 1.0)) / math.log(expansion)
    return int(max(3, min(20, round(n))))



def _refine_boxes(lwl: float, symmetric: bool) -> list[dict]:
    """Nested boxes for the post-snappy free-surface refinement, outermost first.

    These are THIN in z and wide in x,y: their job is the wave field, not the
    hull. An earlier version reused tall hull-refinement boxes here and round 2
    alone selected 4,017,529 cells — refining most of the domain three times
    would have been ~64 M cells. The wave lives in a slab a few percent of LWL
    around z=0; everything below it is still water and everything above is air.

    Each round halves x,y inside its box, and each box is tighter than the last
    so the refinement grades in space rather than in one jump.
    """
    boxes = []
    for i in range(_REFINE_ROUNDS):
        f = 1.0 - i / (_REFINE_ROUNDS + 1.0)          # 1.0, 0.75, 0.5 ...
        # WAKE ASTERN, AND A RUN-OUT BEACH BEHIND IT.
        # The refined wake used to reach -1.9 Lwl with the outlet at -2.5, i.e.
        # only 0.6 Lwl of run-out coarsening a mere 4x. Waves reached the outlet
        # still resolved, reflected, and came back onto the hull: MEASURED
        # pressure drag was 2.6x the expected wave component at t=7.5 s, 2.9x at
        # 13.7 s and 4.2x on the only SETTLED run at 76 s — the error GROWS with
        # time, which is energy accumulating in a box it cannot leave. Viscous
        # drag over the same runs is 1.08x ITTC-57, so the friction side is
        # right and the entire discrepancy is on the wave side.
        # The Wolf Dynamics reference has no damping model either; it leaves
        # 2.31 Lpp of run-out coarsening 32x and lets numerical dissipation on
        # coarse cells eat the waves. ESI v2606 has no `verticalDamping`
        # fvOption (that is an OpenFOAM.org facility — checked, not present),
        # and its waveModels absorption is a patch BC that would need its own
        # constant/waveProperties. So we use the reference's mechanism: pull
        # the refined wake forward to -1.0 Lwl, leaving 1.5 Lwl of run-out.
        bx0 = -(0.4 + 0.6 * f) * lwl
        bx1 = (1.02 + 0.30 * f) * lwl                 # a little ahead of the bow
        by = (0.18 + 0.55 * f) * lwl                  # Kelvin wedge
        bz = (0.020 + 0.030 * f) * lwl                # THIN slab around z=0
        boxes.append(dict(bx0=bx0, bx1=bx1,
                          by0=0.0 if symmetric else -by, by1=by,
                          bz0=-bz, bz1=bz))
    return boxes


def _as_symmetric(text: str) -> str:
    """Rewrite the y=0 patch (`side1`) as a symmetry plane in a field file.

    Calm-water resistance on a port/starboard-symmetric hull only needs half
    the domain, and the half domain is strictly better here than mirroring:
    Uses the general `symmetry` type, NOT `symmetryPlane`: once the hull
    surface lies exactly ON the boundary, snappy leaves faces of both
    orientations there and symmetryPlane refuses ("normal (0 1 0) differs from
    the average normal (0 -1 0)"). OpenFOAM names this fix in the error itself.

    the Tokyo-2015 KCS ships as a HALF body whose keel-line vertices sit at
    y = 2.4 mm, so mirroring lays a ~4.8 mm sliver ribbon down the whole keel
    (measured triangle quality 4.8e-4 there). snappy then produced 14
    zero-volume cells and 73 wrongly oriented faces at EVERY refinement level
    tried, up to 914k cells, and interFoam died on the first timestep.
    Symmetry removes the seam entirely — and halves the cell count.
    """
    import re as _re
    return _re.sub(r"side1\s*\{[^}]*\}", "side1      { type symmetry; }",
                   text)


def _interface_dz(height: float, n: int, expansion: float) -> float:
    """Height of the cell touching the waterline in a graded block.

    Cells form a geometric series summing to `height`, with the largest/
    smallest ratio equal to `expansion`; the interface cell is the smallest.
    """
    if n < 2:
        return height
    q = expansion ** (1.0 / (n - 1))
    return height * (q - 1.0) / (q ** n - 1.0)   # smallest term of the series

CONTROL_DICT = """FoamFile {{ version 2.0; format ascii; class dictionary; object controlDict; }}
application     interFoam;
startFrom       startTime;  startTime 0;
stopAt          endTime;    endTime {end_time};
deltaT          {dt};
writeControl    adjustableRunTime;  writeInterval {write_int};
purgeWrite      3;
// maxAlphaCo 5 smears the interface: the alpha equation carries the wave, so
// it gets the tighter limit even though momentum tolerates Co>1. Measured
// cost of the limit: at maxAlphaCo 1 it, not the cell count, sets dt (0.0031 s
// -> ~4.9 h for the coarse grid alone, days for the fine). 2 is the compromise
// MULESCorr's semi-implicit alpha solve supports; interface sharpness is
// checked in the render rather than assumed.
{time_control}
functions {{
  // NO `rho rhoInf` here. That entry makes the FO charge WATER density to
  // every face including the DRY topsides, which sit in air (1.2 kg/m3).
  // MEASURED on KCS at t=75.97: forces reported 153.16 N where forceCoeffs,
  // which reads the real rho field, reported 98.03 N — a factor 1.56, all of
  // it in the viscous term. The reference DTCHull case sets rhoInf only.
  // BOTH HULL PATCHES. The hull surface is split into `hull` and `hull_bow` so
  // that slamming pressure can be instrumented (see `split_bow_region`), and a
  // `patches (hull)` left alone here would have silently dropped the forward
  // 20% of LWL out of every drag this project reports — a change to the
  // headline number disguised as an unrelated feature. `forces.C` reads this
  // as a `wordRes` and a regex would work, but the two names are known, so
  // they are named: a regex that stops matching is silent, a missing patch
  // name is not.
  forces {{
    type forces; libs (forces); patches (hull hull_bow);
    // BIN THE FORCE ALONG THE HULL. A single total tells you the answer is
    // wrong; the distribution tells you WHERE. MEASURED across six runs,
    // viscous drag is consistently right (1.15-1.22x ITTC-57) while pressure
    // drag is 3-6x the expected wave+form value and GROWS with time —
    // independent of mesh, tank depth, run-out length, layers and solver
    // settings. Bow-heavy would mean wave-making; transom-heavy would mean
    // base drag from a wrongly-wetted transom; uniform would mean a numerical
    // artefact. Costs nothing at runtime.
    binData {{ nBin 20; direction (1 0 0); cumulative no; }}
    rhoInf {rho_water}; CofR (0 0 0);
    writeControl timeStep; writeInterval 10;
  }}
  // OpenFOAM's own coefficient, as an independent cross-check on our
  // post-processing. It caught a double-counting bug in parse_forces that had
  // inflated every drag this project reported.
  forceCoeffs {{
    type forceCoeffs; libs (forces); patches (hull hull_bow);
    rhoInf {rho_water}; CofR (0 0 0);
    liftDir (0 0 1); dragDir (-1 0 0); pitchAxis (0 1 0);
    magUInf {speed_abs}; lRef {lwl}; Aref {aref:.6f};
    writeControl timeStep; writeInterval 10;
  }}
  // The build plan specifies wall functions at y+ ~ 30 (SJTU KCS pipeline).
  // Nothing measured it before, so the layer stack was unverified: y+ in the
  // buffer layer (5-30) is where wall functions are least valid and skin
  // friction — most of this hull's drag — goes quietly wrong.
  yPlus {{
    type yPlus; libs (fieldFunctionObjects);
    writeControl writeTime;
  }}
  // BOW SLAMMING PRESSURE, WHICH THIS PROJECT COULD NOT MEASURE AT ALL
  // (plate P6). MEASURED 2026-08-13: `grep -c
  // "surfaceFieldValue\\|hull_bow\\|bowSlam"` over this file returned 0. The
  // analytic companion is `seakeeping.slam_pressure` / `slam_pressure_band`;
  // the two are compared, never shared.
  //
  // IT IS NAMED `bowSlammingPressure` BECAUSE THAT IS ALL IT IS. The target
  // vessel is a CATAMARAN, and for a catamaran the governing slam load is
  // usually CROSS-STRUCTURE (WET-DECK) slamming — the bridge deck between the
  // demihulls impacting the wave surface in head seas — not bow slamming. A
  // wave-piercing bow is specifically designed to reduce bow slam and does
  // nothing whatever for the wet deck. So a comfortable number out of this
  // function object is NOT evidence that the vessel is safe in a seaway, and
  // there is no wet-deck instrument in this case at all. The same caveat is
  // written into every generated `case.info`, because a run directory outlives
  // the reader who knew what it measured.
  //
  // Wiring the wet-deck case later is a second CALL SITE, never a second
  // implementation (`gate2m.py` shipped a second GCI that returned -27.027%
  // on a diverging family and printed PASS). It needs: a `wet_deck` region cut
  // from the cross-structure underside — a HORIZONTAL cut at the underside z,
  // not a longitudinal cut at the stem, so `split_bow_region` gains a
  // predicate rather than a copy — the same `surfaceFieldValue` block pointed
  // at it, and on the analytic side `slam_pressure` called with the wet-deck
  // deadrise (near zero for a flat bridge deck, which is exactly where
  // `wagner_impact_cp` blows up) and the RELATIVE vertical velocity between
  // deck and wave surface rather than a bow entry velocity.
  //
  // `max`, NOT `average`, AND THE REASON IS THE SAME ONE THAT WRECKED y+.
  // CLAUDE.md records it for the `hull` patch: the patch includes the DECK and
  // the topsides, which sit in AIR, and those dry faces DOMINATE any average
  // (patch-average y+ read 7508, implying a 177 mm first cell against a 104 mm
  // local hull cell — a number about air, wearing the units of the wall). The
  // bow patch carries the same hazard, and worse: the stem region is mostly
  // topside by area. An area-average of p_rgh over it would be an average of
  // one wetted impact against a large dry remainder near zero, i.e. a slam
  // pressure that falls as the impact area shrinks. A MAXIMUM is immune to
  // that — an air face cannot raise it — and a peak impact pressure is the
  // quantity the Wagner model predicts anyway. The price is that a max is a
  // single sample: `docs/LESSONS.md` says a single sample is not a
  // measurement, so what gets quoted is the DISTRIBUTION of this signal over a
  // settled record, not one line of the .dat.
  //
  // `p_rgh`, NOT `p`. p_rgh = p - rho*g*h, so it is already the DYNAMIC part;
  // `p` would carry the hydrostatic head and make the reported maximum a
  // function of how deep the deepest face on the patch is, which is a property
  // of the draft and not of the impact. It also makes the comparison against
  // `0.5 rho V^2 C_p` dimensionally like-for-like.
  //
  // `writeControl timeStep; writeInterval 10` DELIBERATELY DEVIATES from the
  // `writeTime` this was specified with. `writeTime` fires with
  // `purgeWrite`/`writeInterval`, i.e. TEN times over the whole run: a slam
  // lasts milliseconds, and ten samples of a 20 s record cannot contain a peak.
  // `forces` above already samples every 10 timesteps for exactly this reason,
  // and this is a patch reduction, so it costs the same as that one.
  //
  // `writeFields false` IS MANDATORY, not decoration: `fieldValue::read` calls
  // `dict.readEntry("writeFields", ...)`, which FATALs when the entry is
  // absent. Same shape as the `meshQualityControls/relaxed` sub-dict that
  // killed a run AFTER the mesh was built.
  //
  // If the split failed and there is no `hull_bow` patch, `surfaceFieldValue`
  // is STRICT by default and raises with "No matching patches" plus the list
  // of patch names it does know. That is the behaviour we want: an instrument
  // pointed at nothing must stop the run, not report nothing and let a reader
  // score the absence as zero pressure.
  bowSlammingPressure {{
    type            surfaceFieldValue;
    libs            (fieldFunctionObjects);
    regionType      patch;
    name            {bow_patch};
    operation       max;
    fields          ( p_rgh );
    writeFields     false;
    writeControl    timeStep; writeInterval 10;
  }}
}}
"""

# TWO blocks stacked in z, split exactly at the waterline z=0. The split is a
# block boundary, so a mesh FACE lies on z=0 BY CONSTRUCTION for any cell count
# — this replaces the old "nz must be a multiple of 3" snapping, which forced
# z-refinement ratios of 1.333 and 1.5 and so broke the r=sqrt(2) systematic
# refinement that GCI requires (measured: p=nan, GCI 58.5%, oscillatory).
# Both blocks grade toward the interface (G_WATER<1 shrinks upward, G_AIR>1
# expands upward), buying a thin free-surface cell without paying for it
# through the full tank depth.
# FOUR blocks stacked in z, following the DTCHull reference architecture:
#
#   [z0, -zh]  deep water   graded, coarse at the bottom
#   [-zh, 0]   hull band    UNIFORM fine  <- the hull and the wave trough live here
#   [0,  +za]  wave band    UNIFORM fine, same dz  <- wave crest
#   [+za, z1]  air          graded, coarse upward
#
# Two reasons for the uniform middle bands. (1) The waterline is still a BLOCK
# BOUNDARY, so a face lies on z=0 by construction. (2) refineMesh refines in x
# and y ONLY, so ALL z resolution has to come from blockMesh — a graded mesh
# would leave the keel region coarse in z while the waterline is fine.
BLOCKMESH = """FoamFile {{ version 2.0; format ascii; class dictionary; object blockMeshDict; }}
scale 1;
vertices (
  ({x0} {y0} {z0})  ({x1} {y0} {z0})  ({x1} {y1} {z0})  ({x0} {y1} {z0})
  ({x0} {y0} {zh})  ({x1} {y0} {zh})  ({x1} {y1} {zh})  ({x0} {y1} {zh})
  ({x0} {y0} 0)     ({x1} {y0} 0)     ({x1} {y1} 0)     ({x0} {y1} 0)
  ({x0} {y0} {za})  ({x1} {y0} {za})  ({x1} {y1} {za})  ({x0} {y1} {za})
  ({x0} {y0} {z1})  ({x1} {y0} {z1})  ({x1} {y1} {z1})  ({x0} {y1} {z1})
);
blocks (
  hex (0 1 2 3 4 5 6 7)       ({nx} {ny} {nz_deep}) simpleGrading (1 1 {g_deep})
  hex (4 5 6 7 8 9 10 11)     ({nx} {ny} {nz_hull}) simpleGrading (1 1 1)
  hex (8 9 10 11 12 13 14 15) ({nx} {ny} {nz_wave}) simpleGrading (1 1 1)
  hex (12 13 14 15 16 17 18 19) ({nx} {ny} {nz_air}) simpleGrading (1 1 {g_air})
);
boundary (
  inlet      {{ type patch; faces ((1 2 6 5) (5 6 10 9) (9 10 14 13) (13 14 18 17)); }}
  outlet     {{ type patch; faces ((0 4 7 3) (4 8 11 7) (8 12 15 11) (12 16 19 15)); }}
  atmosphere {{ type patch; faces ((16 17 18 19)); }}
  bottom     {{ type wall;  faces ((0 3 2 1)); }}
  side1      {{ type {side1_type};  faces ((0 1 5 4) (4 5 9 8) (8 9 13 12) (12 13 17 16)); }}
  side2      {{ type wall;  faces ((3 7 6 2) (7 11 10 6) (11 15 14 10) (15 19 18 14)); }}
);
"""

# refineMesh refines in Z ONLY, and runs AFTER snappy. The direction enum is
# (tan1 tan2 normal) -- there is NO tan3; asking for one is a fatal error.
# With tan1=+x and tan2=+y, `normal` is their cross product, i.e. +z.
# Division of labour: snappy gets ISOTROPIC cells, which is the only shape it
# can snap and layer reliably; the free surface then gets its THIN cells from a
# z-only split that snappy never has to understand. Running it afterwards also
# sidesteps hexRef8 — snappy cannot refine a mesh refineMesh has touched
# ("cell N of level 0 uses more than 8 points of equal or lower level").
# Earlier this refined x,y, which serves the HULL; the free surface needs z.
DYNAMIC_MESH = """FoamFile {{ version 2.0; format ascii; class dictionary; object dynamicMeshDict; }}
dynamicFvMesh       dynamicMotionSolverFvMesh;
motionSolverLibs    (sixDoFRigidBodyMotion);
motionSolver        sixDoFRigidBodyMotion;

// BOTH hull patches move as one rigid body. Naming only `hull` would leave the
// bow patch behind while the rest of the hull sinks and trims — a torn surface,
// not a degraded one. `sixDoFRigidBodyMotionSolver` reads this as a wordReList.
patches             (hull hull_bow);
// Morphing zone: rigid within innerDistance of the hull, undeformed beyond
// outerDistance, blended between. Both scale with Lwl so the case is
// Froude-similar at any hull size.
innerDistance       {inner:.6f};
outerDistance       {outer:.6f};

centreOfMass        ({cog_x:.6f} {cog_y:.6f} {cog_z:.6f});
mass                {mass:.6f};
momentOfInertia     ({ixx:.6f} {iyy:.6f} {izz:.6f});
rhoInf              1;              // unused by interFoam (it carries rho)
report              on;
value               uniform (0 0 0);

accelerationRelaxation 0.3;   // reference value; 0.4 is a known instability path

solver {{ type Newmark; }}

constraints
{{
    // Sinkage: translation along z ONLY (no surge, no sway).
    heave  {{ sixDoFRigidBodyMotionConstraint line; direction (0 0 1); }}
    // Trim: rotation about the transverse axis ONLY (no roll, no yaw).
    pitch  {{ sixDoFRigidBodyMotionConstraint axis; axis (0 1 0); }}
}}

restraints
{{
    // Dampers act on VELOCITY, so they vanish at equilibrium and cannot bias
    // the converged sinkage or trim — they only suppress the start-up
    // transient, which is otherwise violent because the hull is released into
    // a flow field that has not developed yet. Coefficients are a fraction of
    // critical damping for the heave mode, derived rather than copied from a
    // tutorial tuned for a different hull.
    heaveDamper {{ sixDoFRigidBodyMotionRestraint linearDamper; coeff {c_lin:.1f}; }}
    pitchDamper {{ sixDoFRigidBodyMotionRestraint sphericalAngularDamper; coeff {c_ang:.1f}; }}
}}
"""

POINT_DISPLACEMENT = """FoamFile {{ version 2.0; format ascii; class pointVectorField; object pointDisplacement; }}
dimensions      [0 1 0 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{{
    #includeEtc "caseDicts/setConstraintTypes"
    inlet      {{ type fixedValue; value uniform (0 0 0); }}
    outlet     {{ type fixedValue; value uniform (0 0 0); }}
    atmosphere {{ type fixedValue; value uniform (0 0 0); }}
    bottom     {{ type fixedValue; value uniform (0 0 0); }}
    {side1_pd_entry}
    side2      {{ type fixedValue; value uniform (0 0 0); }}
    "hull.*"   {{ type calculated; }}
}}
"""

REFINE_MESH = """FoamFile { version 2.0; format ascii; class dictionary; object refineMeshDict; }
set             c0;
coordinateSystem global;
globalCoeffs { tan1 (1 0 0); tan2 (0 1 0);  }
directions      ( normal );
useHexTopology  yes;
geometricCut    no;
writeMesh       no;
"""

TOPO_SET = """FoamFile {{ version 2.0; format ascii; class dictionary; object topoSetDict; }}
// Free-surface band MINUS a shield around the hull. The shield matters: this
// runs AFTER snappy, so the prism layers already exist, and directionally
// splitting them would destroy the y+ they were built for.
actions (
  {{ name c0; type cellSet; action new; source boxToCell;
     box ({bx0} {by0} {bz0}) ({bx1} {by1} {bz1}); }}
  {{ name c0; type cellSet; action subtract; source surfaceToCell;
     file "constant/triSurface/hull.stl";
     outsidePoints (({loc_x} {loc_y} {loc_z}));
     includeCut false; includeInside false; includeOutside false;
     nearDistance {shield_m:.6f}; curvature -100; }}
  // HEXES ONLY. This is the fix for every "incorrectly oriented face" this
  // project has ever reported. `refineMesh`'s cellCuts cannot cut the
  // hanging-node POLYHEDRA that snappy's castellation leaves behind: it emits
  // "unexpected bad cut" and produces cells that do not close.
  //
  // MEASURED across all 11 meshes on disk, the correlation is perfect:
  //   0 refine rounds -> 0 wrongly oriented faces (7 of 7 cases, 45k..835k)
  //   3 refine rounds -> 2..47 wrongly oriented   (4 of 4 cases)
  // and runs/kcs uses the IDENTICAL STL with 0 rounds and is clean, which
  // exonerates the geometry. Localising them: 47 of 47 were INTERNAL faces,
  // zero on any patch, with owner/neighbour x and y extents equal (ratio
  // 1.02) and z extents 2:1 or 4:1 — the signature of a z-refinement
  // transition and nothing else.
  //
  // Restricting the set to genuine hexes, measured on the coarse KCS grid:
  //   bad-cut warnings 11563 -> 0      wrongly oriented 47 -> 0
  //   max skewness  15.66 -> 3.77      max nonOrtho  90.21 -> 84.39
  // at NO cost in free-surface resolution (median band cell z-extent 6.20 mm
  // vs 6.12 mm before). Copying the reference's `geometricCut yes` instead
  // makes it WORSE (53 bad faces).
  {{ name cHex; type cellSet; action new; source shapeToCell; shape hex; }}
  {{ name c0;   type cellSet; action subset; source cellToCell; set cHex; }}
);
"""
FV_SCHEMES = """FoamFile {{ version 2.0; format ascii; class dictionary; object fvSchemes; }}
ddtSchemes      {{ default {ddt}; }}
gradSchemes     {{ default Gauss linear; }}
divSchemes {{
  div(rhoPhi,U)     Gauss linearUpwind grad(U);
  div(phi,alpha)    Gauss vanLeer;
  div(phirb,alpha)  Gauss linear;
  div(phi,k)        Gauss upwind;
  div(phi,omega)    Gauss upwind;
  div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}}
laplacianSchemes {{ default Gauss linear corrected; }}
interpolationSchemes {{ default linear; }}
snGradSchemes   {{ default corrected; }}
wallDist        {{ method meshWave; }}
"""

# TIME CONTROL: two regimes, and the choice is what makes Gate 2M affordable.
#
# TRANSIENT is physically complete but pays the Courant limit on every step.
# MEASURED on the layered coarse KCS grid: the 2.65 mm first-layer cell with
# ~3 m/s local flow pins dt at ~0.002 s against maxCo 5, so 75 s of physical
# time needs ~37500 steps at ~0.95 s each -> ~10 h for the COARSE grid alone.
# Refinement halves the cell in all three directions AND halves the timestep,
# so cost scales as r^4: medium ~39 h, fine ~158 h. The transient triplet is
# ~8.6 days on this machine, which is not a plan.
#
# LTS (local time stepping) solves the SAME equations to a STEADY state with a
# per-cell pseudo-timestep, so the near-wall cells stop dictating a global dt.
# This is exactly what the Wolf Dynamics reference does for its FIXED-attitude
# KCS case (endTime 10000 pseudo-iterations). A GCI over three LTS grids is
# valid — it bounds SPATIAL discretisation, which is what Gate 2M's <=2.5%
# clause is about.
#
# Honest limits, which is why this is not the default for everything: the
# result is steady only, it cannot feed the free sinkage-and-trim work (that
# needs real time), and any number from it must be labelled LTS rather than
# passed off as the transient answer.
TIME_CONTROL_TRANSIENT = (
    "adjustTimeStep  yes;  maxCo 5;  maxAlphaCo 2;  maxDeltaT 0.1;")
TIME_CONTROL_LTS = (
    "adjustTimeStep  no;   // LTS: 'time' is a pseudo-iteration count\n"
    "maxCo 10; maxAlphaCo 5; maxDeltaT 1;")

FV_SOLUTION = """FoamFile {{ version 2.0; format ascii; class dictionary; object fvSolution; }}
solvers {{
  // MEASURED on runs/kcs_free, timestep 1: the alpha smoothSolver reported
  // "No Iterations 1000" with Final residual 1.55e-08 against tolerance 1e-8 —
  // it hit the DEFAULT maxIter and bailed UNCONVERGED, and MULES then blew
  // alpha to [-81402, +39618] and died with an FPE in GAMGSolver::scale.
  // nLimiterIter 3 is what starves the limiter. The Wolf Dynamics KCS
  // reference (both fixed and KCS_Dynamic) uses nAlphaCorr 3, nLimiterIter 10,
  // minIter 1 and tolerance 1e-10 — an order of magnitude more limiter work
  // per step, which is exactly the budget a moving interface needs.
  "alpha.water.*" {{
    nAlphaCorr 2; nAlphaSubCycles 1; cAlpha 1; icAlpha 0;
    MULESCorr yes; nLimiterIter 5; alphaApplyPrevCorr yes;
    solver smoothSolver; smoother symGaussSeidel;
    tolerance 1e-8; relTol 0; minIter 1;
  }}
  "pcorr.*" {{ solver PCG; preconditioner DIC; tolerance 1e-5; relTol 0; }}
  p_rgh {{ solver GAMG; smoother DIC; tolerance 1e-7; relTol 0.01; }}
  p_rghFinal {{ $p_rgh; relTol 0; }}
  "(U|k|omega).*" {{ solver smoothSolver; smoother symGaussSeidel;
                    tolerance 1e-7; relTol 0.1; nSweeps 1; }}
}}
PIMPLE {{
  {pimple_time}
  // nOuterCorrectors 1 is PISO: valid only at Co<1. Running maxCo 5 in PISO
  // mode leaves the pressure-velocity coupling unconverged within the step.
  // Under LTS the outer loop IS the pseudo-time iteration, so 1 is correct
  // there and 2 would be paying twice for the same convergence.
  momentumPredictor no; nOuterCorrectors {n_outer}; nCorrectors 3;
  // correctPhi is REQUIRED once the mesh moves: the face fluxes
  // inherited from the previous mesh do not satisfy continuity on
  // the new one, and interFoam will not recover on its own. It is
  // written ONLY for a moving case: it used to be unconditional, so
  // regenerating a FIXED case produced a different configuration
  // from the one that produced the recorded Gate 2M numbers (it adds
  // a pcorr solve at every startup and changes the order in which
  // alpha's and U's boundary conditions are evaluated — the very
  // ordering the setFields note below turns on).
  {correct_phi}moveMeshOuterCorrectors no;
  // MEASURED: runs/kcs_sym carries 11375 severely non-orthogonal faces (max
  // 86.6) and runs/kcs_free had 1277 (max 90.2) — an unavoidable product of
  // the post-snappy z-only refinement, whose hanging nodes leave skewed
  // transitions. Solving that with ZERO non-orthogonal correctors biases the
  // pressure gradient, and pressure is 49% of our drag. The reference uses 1.
  nNonOrthogonalCorrectors 1;
}}
relaxationFactors {{ equations {{ ".*" 1; }} }}
"""

DECOMPOSE = """FoamFile {{ version 2.0; format ascii; class dictionary; object decomposeParDict; }}
numberOfSubdomains {np};
method scotch;
"""

# `geometricTestOnly yes` IS LOAD-BEARING, NOT TIDINESS. Its default is NO,
# and with the default `surfaceFeatures::classifyFeatureAngles` marks EVERY
# edge whose two triangles belong to different STL regions as a REGION feature
# edge, before any angle test is applied
# (src/meshTools/triSurface/surfaceFeatures/surfaceFeatures.C: `if
# (!geometricTestOnly && surf_[face0].region() != surf_[face1].region())`).
# Since `split_bow_region` now ships hull.stl as two solids, the default would
# have written a closed feature LOOP around the hull at the bow cut into
# hull.eMesh, and snappy snaps to feature edges — inventing a sharp crease
# across a surface that is smooth there, at exactly the station where the
# forefoot curvature is highest. That is a fabricated geometric feature, i.e.
# a DIFFERENT HULL, not a worse mesh.
#
# With it set, the extracted feature set is a pure function of the angle test
# and is therefore BIT-IDENTICAL to what this dict extracted before the split
# — which is the property that lets the bow patch be called a pure instrument
# addition. `tests/test_slamming.py` asserts the entry is present; the
# existing `includedAngle 150` bar (30 deg) is untouched, and
# `tests/test_stl_forensics.py` still owns it.
SURFACE_FEATURES = """FoamFile { version 2.0; format ascii; class dictionary; object surfaceFeatureExtractDict; }
hull.stl {
  extractionMethod extractFromSurface;
  extractFromSurfaceCoeffs { includedAngle 150; geometricTestOnly yes; }
  writeObj no;
}
"""

SET_FIELDS = """FoamFile {{ version 2.0; format ascii; class dictionary; object setFieldsDict; }}
defaultFieldValues ( volScalarFieldValue alpha.water 0 );
regions (
  boxToCell {{ box (-1e6 -1e6 -1e6) (1e6 1e6 0);
              fieldValues ( volScalarFieldValue alpha.water 1 ); }}
{box_to_face});
"""

# Written for a MOVING case only. It was unconditional, which quietly changed
# every regenerated FIXED case away from the configuration that produced the
# recorded numbers — and the comment itself says a fixed run does not need it.
SET_FIELDS_BOX_TO_FACE = """  // boxToFace as well, or the BOUNDARY faces keep the uniform 0 from 0.orig
  // and the tank starts with every patch reading "pure air" while its cells
  // read water. MEASURED: that left alpha = 0 on the outlet, and
  // outletPhaseMeanVelocity divides by the water AREA of the patch — zero —
  // so interFoam died with an FPE inside
  // outletPhaseMeanVelocityFvPatchVectorField::updateCoeffs() on the first
  // timestep of a MOVING-mesh run. A fixed run survives only because alpha's
  // own boundary condition is evaluated from the internal field before U's
  // outlet condition is asked for a mean; with correctPhi the order flips.
  boxToFace { box (-1e6 -1e6 -1e6) (1e6 1e6 0);
              fieldValues ( volScalarFieldValue alpha.water 1 ); }
"""

TRANSPORT = f"""FoamFile {{ version 2.0; format ascii; class dictionary; object transportProperties; }}
phases (water air);
water {{ transportModel Newtonian; nu {_NU_WATER:.6g}; rho {_RHO_WATER:.6g}; }}
air   {{ transportModel Newtonian; nu {_NU_AIR:.6g}; rho {_RHO_AIR:.6g}; }}
sigma {_SIGMA_WATER:.6g};
"""

GRAVITY = f"""FoamFile {{ version 2.0; format ascii; class uniformDimensionedVectorField; object g; }}
dimensions [0 1 -2 0 0 0 0];
value (0 0 -{_G:.6g});
"""

TURBULENCE = """FoamFile { version 2.0; format ascii; class dictionary; object turbulenceProperties; }
simulationType RAS;
RAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }
"""

# `"hull.*"` IN EVERY FIELD FILE, AND IT IS A SINGLE SOURCE, NOT A SHORTHAND.
# The hull is two patches now (`hull` and `hull_bow`; see `split_bow_region`),
# and they are the SAME WALL — same wall functions, same no-slip, same
# fixedFluxPressure. Writing the entry twice would be this codebase's signature
# defect applied to boundary conditions, and the drift it invites is silent:
# the bow keeping `noSlip` while the rest of the hull moves would put a
# spurious mass flux through the one part of the surface that is slamming.
# OpenFOAM matches boundaryField keys as regexes, so one entry governs both,
# and a patch that matches NO entry is a fatal "cannot find patchField entry" —
# the missing-BC failure is loud, which is why a regex is safe here.
FIELD_U = """FoamFile {{ version 2.0; format ascii; class volVectorField; object U; }}
dimensions [0 1 -1 0 0 0 0];
internalField uniform (-{u} 0 0);
boundaryField {{
  inlet      {{ type fixedValue; value uniform (-{u} 0 0); }}
  outlet     {{ type outletPhaseMeanVelocity; alpha alpha.water;
               Umean {u}; value uniform (-{u} 0 0); }}
  atmosphere {{ type pressureInletOutletVelocity; value uniform (0 0 0); }}
  bottom     {{ type slip; }}
  side1      {{ type slip; }}
  side2      {{ type slip; }}
  "hull.*"   {{ {hull_u} }}
}}
"""

# A MOVING wall needs movingWallVelocity, not noSlip. noSlip pins the face
# velocity to zero in the ABSOLUTE frame and omits the mesh-motion flux, so a
# hull that is sinking and trimming has a spurious mass flux through its own
# surface. That is the leading suspect for runs/kcs_free dying on timestep 1:
# pcorr ground through 254 iterations, then the alpha solve hit its iteration
# ceiling unconverged. The Wolf Dynamics KCS reference uses movingWallVelocity
# on the hull in BOTH its fixed and its free case; we keep noSlip when the mesh
# does not move, where the two are equivalent and noSlip is clearer.
_HULL_U_FIXED = "type noSlip;"
_HULL_U_MOVING = "type movingWallVelocity; value uniform (0 0 0);"

FIELD_P_RGH = """FoamFile { version 2.0; format ascii; class volScalarField; object p_rgh; }
dimensions [1 -1 -2 0 0 0 0];
internalField uniform 0;
boundaryField {
  inlet      { type fixedFluxPressure; value uniform 0; }
  outlet     { type zeroGradient; }
  atmosphere { type totalPressure; p0 uniform 0; }
  bottom     { type fixedFluxPressure; value uniform 0; }
  side1      { type fixedFluxPressure; value uniform 0; }
  side2      { type fixedFluxPressure; value uniform 0; }
  "hull.*"   { type fixedFluxPressure; value uniform 0; }
}
"""

FIELD_ALPHA = """FoamFile { version 2.0; format ascii; class volScalarField; object alpha.water; }
dimensions [0 0 0 0 0 0 0];
internalField uniform 0;
boundaryField {
  // inlet MUST inject stratified water/air: an inletOutlet with inletValue
  // $internalField (= uniform 0) injects AIR below the waterline and drains
  // the tank (first Mac smoke run: phase fraction 0.667 -> 0.486 over 5 s)
  inlet      { type exprFixedValue; value uniform 0;
               valueExpr "(pos().z() < 0) ? 1 : 0"; }
  outlet     { type variableHeightFlowRate; lowerBound 0.0; upperBound 1.0;
               value uniform 0; }
  atmosphere { type inletOutlet; inletValue uniform 0; value uniform 0; }
  bottom     { type zeroGradient; }
  side1      { type zeroGradient; }
  side2      { type zeroGradient; }
  "hull.*"   { type zeroGradient; }
}
"""

FIELD_K = """FoamFile {{ version 2.0; format ascii; class volScalarField; object k; }}
dimensions [0 2 -2 0 0 0 0];
internalField uniform {k_in};
boundaryField {{
  inlet      {{ type fixedValue; value uniform {k_in}; }}
  outlet     {{ type inletOutlet; inletValue uniform {k_in}; value uniform {k_in}; }}
  atmosphere {{ type inletOutlet; inletValue uniform {k_in}; value uniform {k_in}; }}
  bottom     {{ type slip; }}
  side1      {{ type slip; }}
  side2      {{ type slip; }}
  "hull.*"   {{ type kqRWallFunction; value uniform {k_in}; }}
}}
"""

FIELD_OMEGA = """FoamFile {{ version 2.0; format ascii; class volScalarField; object omega; }}
dimensions [0 0 -1 0 0 0 0];
internalField uniform {w_in};
boundaryField {{
  inlet      {{ type fixedValue; value uniform {w_in}; }}
  outlet     {{ type inletOutlet; inletValue uniform {w_in}; value uniform {w_in}; }}
  atmosphere {{ type inletOutlet; inletValue uniform {w_in}; value uniform {w_in}; }}
  bottom     {{ type slip; }}
  side1      {{ type slip; }}
  side2      {{ type slip; }}
  "hull.*"   {{ type omegaWallFunction; value uniform {w_in}; }}
}}
"""

FIELD_NUT = """FoamFile { version 2.0; format ascii; class volScalarField; object nut; }
dimensions [0 2 -1 0 0 0 0];
internalField uniform 0;
boundaryField {
  inlet      { type calculated; value uniform 0; }
  outlet     { type calculated; value uniform 0; }
  atmosphere { type calculated; value uniform 0; }
  bottom     { type calculated; value uniform 0; }
  side1      { type calculated; value uniform 0; }
  side2      { type calculated; value uniform 0; }
  "hull.*"   { type nutkWallFunction; value uniform 0; }
}
"""

SNAPPY_STUB = """FoamFile {{ version 2.0; format ascii; class dictionary; object snappyHexMeshDict; }}
castellatedMesh {castellate}; snap {do_snap}; addLayers {do_layers};
geometry {{
  // TWO REGIONS, ONE SURFACE. hull.stl ships as two named solids (see
  // `split_bow_region`), and the `regions` sub-dict maps each to a patch name
  // VERBATIM — searchableSurfaces.C uses the `name` value as the global region
  // name with no surface prefix, and snappyHexMesh.C then creates one patch
  // per global region called exactly that. So the aft solid keeps the patch
  // name `hull` that every other dictionary, script and post-processor in this
  // project addresses, and only the forward faces become `hull_bow`.
  // A name here that does not match a solid in the file is FATAL
  // ("Unknown region name"), which is the failure mode we want.
  hull.stl {{ type triSurfaceMesh; name hull;
              regions {{ {stl_main_solid} {{ name {hull_patch}; }}
                        {stl_bow_solid}  {{ name {bow_patch}; }} }} }}
  freeSurface {{ type searchableBox; min ({fs_x0} {fs_y0} {fs_z0});
                                     max ({fs_x1} {fs_y1} {fs_z1}); }}
}}
castellatedMeshControls {{
  maxLocalCells 2000000; maxGlobalCells 12000000; minRefinementCells 0;
  nCellsBetweenLevels 3;
  // level 0: snappy must not refine ANYTHING here. hexRef8 (its octree
  // engine) cannot refine a mesh produced by refineMesh, and asking it to
  // aborts in danglingCellRefine. The reference uses level 0 as well.
  features ( {{ file "hull.eMesh"; level {hull_lvl_max}; }} );
  refinementSurfaces {{ hull {{ level ({hull_lvl_min} {hull_lvl_max}); }} }}
  refinementRegions {{ freeSurface {{ mode inside; levels ((1e15 {fs_level})); }} }}
  locationInMesh ({loc_x} {loc_y} {loc_z});
  allowFreeStandingZoneFaces true; resolveFeatureAngle 30;
}}
// MEASURED, and counter to expectation. Adopting the DTCHull reference
// values (tolerance 1.0, nSolveIter 100) made refinement (3 4) far WORSE:
// zero-volume cells 3 -> 79 and wrongly oriented faces 49 -> 767. These are
// the values that mesh clean at (2 3), which is what the GCI triplet uses.
snapControls {{ nSmoothPatch 3; tolerance 2.0; nSolveIter 50; nRelaxIter 5; }}
addLayersControls {{
  // ABSOLUTE sizing: y+ is a physical quantity, so the near-wall cell is set
  // in metres from the ITTC friction line, not as a fraction of whatever cell
  // snappy happened to leave there. relativeSizes true is what produced
  // y+ ~ 7500. Held CONSTANT across the GCI triplet so all three grids sit in
  // the wall-function's valid band -- the GCI then bounds OUTER-flow
  // discretisation with the near-wall treatment fixed, which is the honest
  // reading of it and is stated in case.info.
  // ONE ENTRY, BOTH HULL PATCHES, via a regex — `layerParameters.C` reads each
  // key as a `wordRe` and expands it through `boundaryMesh.patchSet`, which is
  // how the motorBike tutorial layers ~60 patches from a single line. Writing
  // `hull` and `hull_bow` as two entries would be the same number declared
  // twice, and the failure it invites is the worst kind here: a bow patch left
  // at zero layers is a PARTIAL layer field, and CLAUDE.md records that partial
  // stacks — not full ones and not absent ones — are what fold cells.
  // A regex matching nothing is only an IOWarning in snappy, so
  // `tests/test_slamming.py` asserts the pattern matches both names.
  relativeSizes false; layers {{ "hull.*" {{ nSurfaceLayers {n_layers}; }} }}
  expansionRatio {layer_expansion}; firstLayerThickness {first_layer:.6e};
  minThickness {min_thickness:.6e}; nGrow 0;
  // featureAngle is the angle ACROSS WHICH LAYERS ARE ALLOWED TO CONTINUE.
  // At 60 deg extrusion terminates at any junction sharper than that, which
  // on a hull means the keel line, the transom edge, the deck edge and the
  // bulb — i.e. exactly the places a boundary layer must not stop. The Wolf
  // Dynamics KCS reference uses 170 and so does snappy's own DTCHull tutorial.
  // MEASURED before the change: extrusion started at 44.98% of 11166 faces
  // and DECAYED to 0 over 35 iterations as the quality controls rejected it.
  featureAngle {layer_feature_angle}; slipFeatureAngle 30;
  nRelaxIter 5; nSmoothSurfaceNormals 1; nSmoothNormals 3; nSmoothThickness 10;
  // maxFaceThicknessRatio IS INERT HERE and is kept only so the dict is
  // complete. snappyLayerDriver::handleWarpedFaces guards the whole check with
  // `if (relativeSizes[patchI] && f.size() > 3)`, and we run relativeSizes
  // false — so it is never evaluated. The comment this replaces attributed a
  // measured 43.9% -> 46.3% coverage gain to loosening it from 0.5, which a
  // dead parameter cannot produce; that gain came from the co-varied
  // maxThicknessToMedialRatio, which IS live (it halves thickness toward
  // minThickness wherever thickness/medial-distance exceeds it).
  maxFaceThicknessRatio 0.8; maxThicknessToMedialRatio 0.6;
  // Documented purpose: "if there are just a few faces where there are mesh
  // errors (after adding the layers) print their face centres." This is the
  // built-in instrument for exactly the failure we were blind to for weeks.
  additionalReporting true;
  minMedialAxisAngle 90; nBufferCellsNoExtrude 0; nLayerIter 50;
  nRelaxedIter 20;
}}
// v2606 REQUIRES a `relaxed` sub-dict once layer addition reaches
// nRelaxedIter, and dies with "Entry 'relaxed' not found in dictionary" —
// a FATAL IO ERROR after the mesh is already built. It stayed hidden while
// nSurfaceLayers was 3 (iteration 20 was never reached) and only surfaced
// when the near-wall fix asked for 6 layers.
// minTetQuality -1e30, CHOSEN BY MEASUREMENT AGAINST THE DOCUMENTED ADVICE.
//
// First, a correction of record: an earlier commit claimed -1e30 "matches
// snappy's own DTCHull tutorial". It does NOT. DTCHull and DTCHullMoving both
// ship `minTetQuality 1e-30` — POSITIVE, which still rejects inside-out (<0)
// and flat (=0) tets and only removes a positive-quality floor. `-1e30` is the
// documented disable sentinel and accepts inverted tets. Opposite semantics.
//
// So 1e-30 was the obviously-correct middle setting, and it was tried. On the
// coarse KCS grid, mesh-only, everything else identical:
//
//     minTetQuality   layers   nonOrtho errors   wrongly oriented   skew
//     1e-30 (DTCHull)  75.8%        10                 18          13.18
//     -1e30 (disabled) 89.8%         0                  0           9.64
//
// The STRICTER check produced the WORSE mesh, including 18 folded cells and 10
// faces past the 90-degree legality limit. The mechanism is snappyLayerDriver's
// checkAndUnmark, which is MONOTONE — a face unmarked at iteration 3 is never
// re-enabled — so rejecting more faces mid-process leaves a patchy, unevenly
// terminated layer field, and partial stacks fold cells where full stacks or
// no stacks do not. It is not that the tet check is wrong; it is that
// enforcing it DURING a monotone extrusion is worse than enforcing it after.
//
// This is a knowing trade, so it carries a receipt: run-case.sh re-checks the
// FINISHED mesh with `checkMesh -meshQuality` against minTetQuality 1e-15 and
// records the count, because the mesh-motion machinery used by free sinkage
// and trim does consume the tet decomposition. minVol (1e-13) guards the
// finite-volume discretisation and is unchanged; the two are not
// interchangeable.
meshQualityControls {{ maxNonOrtho 70; maxBoundarySkewness 20; maxInternalSkewness 4;
  maxConcave 80; minVol 1e-13; minTetQuality -1e30; minArea -1; minTwist 0.02;
  minDeterminant 0.001; minFaceWeight 0.05; minVolRatio 0.01; minTriangleTwist -1;
  nSmoothScale 4; errorReduction 0.75;
  // Limits snappy falls back to for the final nRelaxedIter layer iterations.
  // Relax ONLY the angle/skew checks. The volume and twist checks are what
  // stand between us and degenerate cells, and relaxing them is not a
  // trade-off — it is fatal. MEASURED: with minTwist/minFaceWeight loosened,
  // snappy kept 11976 illegal faces (concave / zero-area / negative pyramid
  // volume) and interFoam then drove deltaT to 2.9e-40 while the Courant
  // number stayed ~9, i.e. a cell whose local Courant no timestep can fix,
  // and died with an FPE in the GAMG pressure solve. A dropped layer costs
  // accuracy; a degenerate cell costs the whole run.
  relaxed {{ maxNonOrtho 75; maxBoundarySkewness 25; maxInternalSkewness 6;
    maxConcave 80; minVol 1e-13; minTetQuality -1e30; minArea -1;
    minTwist 0.02; minDeterminant 0.001; minFaceWeight 0.05;
    minVolRatio 0.01; minTriangleTwist -1; }}
}}
writeFlags (scalarLevels); mergeTolerance 1e-6;
"""


# Triangulation bounds. The CAP is deliberate (600x120 ~ 144k triangles) and
# is not raised here: nothing measured says a finer STL helps, and the cost is
# paid in surfaceFeatureExtract and in every snap iteration.
_STL_NX_FLOOR, _STL_NX_CAP = 80, 600


def stl_resolution_request(lwl: float, target_edge: float) -> int:
    """The nx `stl_resolution` ASKS for, before the floor and the cap.

    Separate from the clamped value so the two can be recorded side by side
    without either being computed twice — the clamp is invisible otherwise,
    and it has been binding on every case this project has ever run.
    """
    return int(round(lwl / max(target_edge, 1e-6)))


def stl_resolution(lwl: float, target_edge: float) -> tuple[int, int]:
    """(nx, nz) giving a hull triangulation of roughly `target_edge` metres,
    CLAMPED to [80, 600] — and in production the cap binds on every hull, so
    the returned value does not depend on `lwl` at all.

    The STL must be FINER than the cells that snap to it or the mesher snaps
    to facets. MEASURED: the default 80x16 gives ~112 mm triangles on a 10 m
    hull — adequate against the 104 mm cells of hull refinement level 3, but
    the limiting surface as soon as the hull is refined to level 4-5 (52/26 mm)
    to get the near-wall spacing y+ needs. Keeps the original 1:5 nz:nx ratio.

    THE `lwl` ARGUMENT IS INERT AT THE ONLY CALL SITE, MEASURED 2026-08-12
    (docs/research/STL.md, commit 749801c). `write_resistance_case` passes
    `target_edge = 0.5 * (_DOMAIN_LENGTH_L * lwl / nx_bg) / 2**_HULL_REFINE[1]`,
    which is PROPORTIONAL to lwl, so lwl cancels and the request is
    `round(57 * 4.5 / (2 * 0.5 * 32)) = 811` for a 6.8 m hull and 811 for an
    18.7 m one. The cap binds on both, and across the 25-hull seed-0 batch
    `h_stl,x / h_cell = 0.676683` and `station spacing / h_cell = 10.1333` at
    EVERY lwl, to six decimals. Two consequences worth stating out loud:

    - the STL ships 1.353x COARSER in x than this function asks for, on every
      case ever run — the docstring above describes a resolution that scales
      with the hull and the refinement level, and it never varies;
    - a SIZE-DEPENDENT resolution deficit is therefore impossible by
      construction. Spearman(lwl, fraction of triangles coarser than the cell)
      = -0.740 (p 2.4e-5) — the correlation runs the OPPOSITE way to the
      intuition, because bigger hulls get bigger cells against a fixed nx.

    And nx is not the binding resolution in x anyway: `Hull.closed_mesh`
    interpolates linearly between 41 STATIONS, so raising nx from 80 to 600
    multiplies the triangle count by 55 and moves the effective longitudinal
    resolution NOT AT ALL (10.133 cells per station spacing, independent of
    nx). `case.info` records the request beside the shipped value so the clamp
    is visible from the case directory.
    """
    nx = int(min(max(stl_resolution_request(lwl, target_edge),
                     _STL_NX_FLOOR), _STL_NX_CAP))
    return nx, int(min(max(round(nx * 0.2), 16), 120))


# The GIRTH resolution a watertight STL needs, and it is a function of the
# BILGE SHAPE, which is why a single default was wrong.
#
# nz = 16 survived unnoticed because it was calibrated when every hull this
# grammar could draw had a HARD CHINE — a crease that a few girth points
# represent exactly. Plate P2 made the radiused bilge expressible and nothing
# re-derived the tessellation it needs.
#
# nz = 48 replaced it and was calibrated on ROUNDNESS VARIANTS OF ONE REFERENCE
# HULL (rho in {0.5, 0.9, 1.0}), which read a worst of 0.111% and 3.15x of
# margin. RE-MEASURED 2026-08-13 ON THE POPULATION THE BAR IS ACTUALLY APPLIED
# TO — the twelve designs `evaluate()` returns `ok=True` for out of
# `grammar.sample(600, rng(0))` — the worst is 0.3581% and the margin is 1.04x,
# and the test nz = 48 was raised to serve FAILED against its own 0.35% bar.
# Configuration is an argument, never an assumption (docs/LESSONS.md defect
# class 6), and the POPULATION a bar is calibrated on is part of the
# configuration.
#
# Worst |STL volume - ladder volume| / ladder volume over those twelve designs,
# nx held at this function's own default 80:
#
#     nz          48      64      96     128     192     384
#     worst   0.3581  0.2854  0.2579  0.2473  0.2398  0.2354
#
# IT DOES NOT GO TO ZERO, AND THAT IS THE POINT. The residual is NOT girth
# resolution; it is decomposed in `tests/test_end_to_end_flow.py` beside
# `STL_VOLUME_TOL_PCT`. Two terms:
#
#   * a GIRTH term that converges like h^2 and is what this constant buys.
#     Isolated by integrating the SAMPLED section area at the ladder's own 41
#     stations with the ladder's own trapezoid: 0.0920% (nz 48) -> 0.0240% (96)
#     -> 0.0059% (192) -> 0.0015% (384) on the worst design. Clean second
#     order, converging to zero. Measured on the whole population as the gap
#     between the STL and its own nz -> inf limit it reads 0.2701 (48) ->
#     0.1553 (64) -> 0.0673 (96) -> 0.0357 (128) -> 0.0140 (192). This one is
#     a tessellation error and 96 is where it stops being the dominant term.
#   * a LOFT term that does not converge with nz OR nx at all, worst 0.1869%,
#     always NEGATIVE. `closed_mesh` lerps the section control points between
#     41 stations while `hydrostatics.solve` trapezoids the EXACT section areas
#     at the same 41 stations, and area is convex in those control points, so
#     A(lerp(p)) <= lerp(A(p)) at every x in between. The STL and the ladder
#     are describing two different solids and no value of nz can close it.
#     MEASURED at roundness EXACTLY 0, where nz changes nothing: over twelve
#     validated hard-chine designs the STL still reads 0.1921% low, identical
#     at nz 16 and at nz 384. (The 0.032% recorded above for a hard chine was
#     ONE hull's loft term, not a property of hard chines.)
#
# So 96 is chosen to put the term this constant CONTROLS (0.0673% worst at 96)
# at about a third of the term it does not (0.1869%), rather than for a margin
# against the bar — the bar cannot be met at the file's usual 2x while the loft
# term stands. 192 would buy another 0.018% for 4x the triangles.
# THE COST IS MEASURED on design 1 of that population: 7.31 MB against 3.67 MB
# per STL and 0.65 s against 0.33 s to write, which is nothing beside the mesh
# it feeds.
#
# NX MATTERS ONLY THROUGH ALIGNMENT, and this function's 80 is misaligned.
# `closed_mesh` samples `linspace(0, LWL, nx)` over a surface whose parameter
# curves KINK at the 41 stations, so an nx that does not land on them chords
# across the kinks as well. MEASURED at nz = 48 on the worst of those twelve
# (design 2, and it is the worst at all four): nx 80 -> 0.3581%, 81 -> 0.3366%,
# 320 -> 0.3372%, 321 -> 0.3358%, i.e. nx = 2*(n_stations-1)+1 = 81 beats
# nx = 320 for a quarter of the triangles. `nx = k*(Hull.n_stations-1)+1`
# is worth ~0.05% for free and is NOT changed here, because the nx default is
# read by callers this constant does not own.
#
# The CFD case path does NOT use these; it calls `stl_resolution`, which
# returns 600x120 at scale 1.0. These govern the BARE default, which is what
# `evaluate.l3_case_evidence` writes when it checks whether a recorded RANS
# campaign is about this hull — so an under-resolved default here silently
# widens that identity test.
_STL_NZ_HARD_CHINE = 16
_STL_NZ_FILLETED = 96


def stl_girth_resolution(hull: Hull) -> int:
    """nz for a hull whose STL must enclose the displacement the ladder floated.

    ONE HOME for the choice, because the bare default is read by the L3
    identity check and by every ad-hoc `hull_to_stl(h, p)` call. A caller that
    genuinely wants a coarse mesh passes nz explicitly and says why.
    """
    from .. import grammar
    rho = float(grammar.named(hull.params)["roundness"])
    return _STL_NZ_HARD_CHINE if rho <= 0.0 else _STL_NZ_FILLETED


def hull_to_stl(hull: Hull, path: Path, nx: int = 80,
                nz: int | None = None) -> str:
    """Write a WATERTIGHT ascii STL (full hull + deck + transom); sha256.

    CFD needs a closed manifold: the earlier wetted-only shell had 198 open
    edges (surfaceFeatureExtract, first Mac smoke run) and let the mesher
    reach the hull interior.

    `nz` defaults to `stl_girth_resolution(hull)` rather than to a constant:
    a radiused bilge needs six times the girth points a chine does, and the
    old fixed 16 under-enclosed a filleted hull by 0.71% against a 0.35% bar.

    `nx` DOES NOT DEFAULT TO A STATION-ALIGNED VALUE and 80 is not one. The
    surface `closed_mesh` samples kinks at `Hull.n_stations` stations, so an nx
    off those kinks chords across them: MEASURED over twelve validated designs,
    worst submerged-volume error 0.3581% at nx=80 against 0.3366% at nx=81 and
    0.3372% at nx=320 — 81 beats 320 for a sixteenth of the triangles. Pass
    `nx = k * (hull.n_stations - 1) + 1` when the volume matters.
    """
    if nz is None:
        nz = stl_girth_resolution(hull)
    verts, tris = hull.closed_mesh(nx=nx, nz=nz)
    lines = ["solid hull"]
    for t in tris:
        p = verts[list(t)]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        nn = np.linalg.norm(n)
        n = n / nn if nn > 1e-14 else np.array([0.0, 0.0, 1.0])
        lines.append(f" facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}")
        lines.append("  outer loop")
        for v in p:
            lines.append(f"   vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}")
        lines.append("  endloop")
        lines.append(" endfacet")
    lines.append("endsolid hull")
    data = "\n".join(lines).encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# THE BOW PATCH — the instrument that makes P_slam MEASURABLE (plate P6)
#
# MEASURED 2026-08-13, before this change:
#     grep -c "surfaceFieldValue\|hull_bow\|bowSlam" navalai/cfd/case.py  ->  0
# `forces`, `forceCoeffs` and `yPlus` all existed and worked; this one family
# was simply absent, and it could not be added because the hull was ONE patch
# and a `surfaceFieldValue` needs something to point at. This is a pure
# instrument addition: no genome, no hull, no physics parameter changes.
#
# PATCH NAMING IS NOT GUESSED. Read out of the v2606 source rather than from
# memory, because getting it wrong renames the patch every other dictionary in
# this file addresses:
#   - src/meshTools/searchableSurfaces/searchableSurfaces/searchableSurfaces.C
#     builds the GLOBAL region name as the surface `name` when the surface has
#     exactly ONE region, as "<surface>_<region>" when it has several, and as
#     the VERBATIM `regions { <local> { name X; } }` value when one is given.
#   - applications/utilities/mesh/generation/snappyHexMesh/snappyHexMesh.C then
#     creates one patch per global region, named `regNames[i]` with NO prefix.
# So `regions { main { name hull; } bow { name hull_bow; } }` yields patches
# named EXACTLY `hull` and `hull_bow`. The existing `hull` patch keeps its name
# and every receipt, script and post-processor that addresses it keeps working;
# only the forward faces move.
#
# NOT RUN. No snappyHexMesh has been executed against this split — this change
# was made under a no-compute constraint, and the source reading above is the
# evidence, not a mesh. What is owed before the first result is quoted: one
# mesh-only build (~2 min) confirming `constant/polyMesh/boundary` carries both
# patches and that the layer table reports the bow patch layered.
BOW_PATCH_NAME = "hull_bow"
HULL_PATCH_NAME = "hull"
# Local region names INSIDE the STL, i.e. the `solid <name>` labels. They are
# not the patch names; snappy maps them through the `regions` dict above. If a
# name here stops matching a solid in the file, searchableSurfaces raises
# "Unknown region name" and FATALs — a loud failure, which is the point.
_STL_MAIN_SOLID = "main"
_STL_BOW_SOLID = "bow"

# THE CUT: the forward 20% of the hull, measured back from the stem.
#
# It is a FRACTION and not a fixed distance because everything else in this
# generator is Froude-similar; a fixed metre value would make a 4 m tender and
# a 20 m barge different experiments.
#
# THE FRACTION IS OF THE MESHED SURFACE'S OWN LONGITUDINAL EXTENT, NOT OF THE
# `lwl` ARGUMENT, AND THAT IS A MEASURED CORRECTION. The first version used
# `x_stem - fraction * lwl`, which mixes the STL's coordinate system with the
# caller's length scale, and `tests/test_phase2.py::
# test_mesh_is_froude_similar_at_any_hull_size` immediately found the hole: it
# meshes the SAME 7.7165 m KCS model STL at lwl 7.2786, 29.1 and 230.0 to prove
# the mesh is geometrically similar at constant Froude number, so at k=31.6 the
# cut landed at x = -38.28 m and the ENTIRE hull fell in the bow solid. The
# guard caught it (the run refused rather than shipping a one-region hull), but
# a guard firing on a legitimate call is a wrong rule, not a caught bug.
# Deriving the plane from the surface's own x-extent is self-consistent by
# construction and needs no length argument at all.
#
# For every hull this project GENERATES the two are identical: `hull_to_stl`
# writes `closed_mesh` over x in [0, lwl], so the STL extent IS Lwl. They differ
# only for imported geometry with overhang — on KCS the STL spans 0..7.7165 m
# against Lpp 7.2786 because the bulb and rudder reach past the perpendiculars,
# so the patch is 1.5433 m rather than 1.4557 m, 6% longer. `case.info` records
# the stem, the split plane and the fraction, and `lwl` sits three lines above
# them, so the reader can form either ratio without either being stored twice.
#
# WHY 0.20, stated as a trade rather than as a citation this project cannot
# check:
#  - It has to CONTAIN the impact site. A slam happens where the forefoot
#    re-enters, and `geometry.hull_curves` raises the keel over `x > 0.7 L`
#    (its `bow_zone`), so 0.20 L sits well inside the forebody that lifts, with
#    margin for the trim angle moving the contact point aft.
#  - It has to be SHORT enough that the patch maximum is attributable. The
#    statistic is a max, so a longer patch cannot dilute it — but it can move
#    the peak onto a section with a different deadrise, and the analytic
#    companion (`seakeeping.slam_pressure_band`) then brackets a wider and
#    less useful range. 0.20 L is inside the deadrise warp zone for every hull
#    the grammar can sample: `grammar.PARAMS` bounds `beta_len` (the fraction
#    of LWL over which deadrise warps) at >= 0.15, so the aft edge of the patch
#    never sits more than 0.05 L abaft the start of the warp.
#  - It is NOT tuned to a measurement, because there is no measurement yet.
#    Move it when a run says to, and re-derive nothing else: the value is
#    recorded in `case.info` as `bow_patch_fraction`, beside the split plane
#    and the patch's actual aft edge, so a case never has to be
#    reverse-engineered to learn where its own bow patch ended.
#
# WHAT THIS FRACTION IS NOT FOR. It bounds a BOW impact region. The target
# vessel is a catamaran, whose governing slam is usually cross-structure
# (wet-deck) impact — see the `bowSlammingPressure` block in CONTROL_DICT for
# why that is a separate patch with a separate (horizontal) cut, and for why it
# is a second call site of the same Wagner helper rather than a second model.
BOW_PATCH_FRACTION = 0.20


def split_bow_region(stl_path: str | Path,
                     fraction: float = BOW_PATCH_FRACTION) -> dict:
    """Re-emit an ascii STL as TWO named solids, `main` and `bow`, in place.

    The bow solid is every triangle that REACHES forward of the split plane
    `x_stem - fraction * (x_stem - x_aft)`, i.e. whose largest vertex x is at
    or ahead of it. Everything is taken from the file's own coordinates and
    there is deliberately NO length argument: see the constant above for the
    measurement that removed it — a cut scaled by a caller-supplied `lwl` put
    the split plane at x = -38.28 m on a legitimate call.

    REACHES, NOT CENTRED, AND THE ASYMMETRY IS THE POINT. A triangle straddling
    the plane must go wholly to one side (splitting it would retriangulate, and
    this function is not allowed to move geometry), so the choice is which way
    to round. It rounds FORWARD, because the statistic the patch exists to feed
    is a MAXIMUM: a straddling facet wrongly left in `main` can hide the peak,
    while one wrongly included in `hull_bow` can only widen the region the peak
    was found in — and `case.info` records the patch's ACTUAL aft edge, so the
    over-inclusion is visible rather than assumed small. It is exactly one
    facet row: MEASURED on KCS the split plane is x = 6.1732 m and the patch's
    aft edge is x = 6.1474 m, i.e. 25.8 mm or 0.33% of the hull's length, and
    the patch holds 2202 of 10402 facets (21.2%) against a nominal 20%.

    It also makes an EMPTY BOW impossible rather than merely unlikely: the
    facet attaining `x_stem` reaches the plane by definition, for any fraction
    in (0, 1). That is why only the empty-MAIN direction is guarded below — a
    branch that cannot execute is not a guard, it is unreachable code claiming
    to be one. MEASURED 2026-08-13: the centroid rule this replaces refused
    `tests/test_stageG.py::test_geometric_scale_buys_no_cpu`, whose fixture is
    a 4-facet tetrahedron on which no centroid lies in the forward fifth.

    Either way it PARTITIONS: every triangle lands in exactly one solid, so bow
    and main are disjoint, their union is the whole surface, and each is a
    strict subset of it. `tests/test_slamming.py` asserts that on real geometry
    rather than trusting the argument.

    GEOMETRY-PRESERVING BY CONSTRUCTION. The facet text is copied VERBATIM —
    this function never re-formats a coordinate — so the only bytes that change
    are the `solid`/`endsolid` lines and the order of the facet blocks. It is
    therefore impossible for the bow split to move a vertex, which matters
    because `write_resistance_case_from_stl` exists to mesh a benchmark hull
    whose shape is the whole point of the comparison. A re-parse-and-rewrite
    (`post._read_stl_tris` rounds to 7 decimals) would have perturbed it at the
    100 nm level for no reason at all.

    REFUSES rather than degrades, in three ways, because an instrument that
    silently points at nothing is worse than no instrument:
      - a file with no parseable facets, or a facet without exactly three
        vertices, is a parse failure and NOT an empty hull;
      - an empty main solid means the fraction swallowed the whole hull, which
        would give snappy a region with zero faces and, downstream, a patch
        `surfaceFieldValue` has no data to take a max over.

    Returns the receipt that goes into `case.info`.
    """
    path = Path(stl_path)
    text = path.read_text()
    frac = float(fraction)
    if not (0.0 < frac < 1.0):
        raise ValueError(
            f"bow patch fraction must be in (0, 1), got {fraction!r}")

    blocks: list[tuple[str, float, float]] = []   # (text, min_x, max_x)
    cur: list[str] = []
    verts: list[tuple[float, float, float]] = []
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("solid") or s.startswith("endsolid"):
            continue
        if s.startswith("facet"):
            cur, verts = [raw], []
            continue
        if not cur:
            continue
        cur.append(raw)
        if s.startswith("vertex"):
            verts.append(tuple(float(v) for v in s.split()[1:4]))
        elif s.startswith("endfacet"):
            if len(verts) != 3:
                raise ValueError(
                    f"{path}: facet {len(blocks)} has {len(verts)} vertex "
                    f"lines, not 3. This is a PARSE FAILURE, not a degenerate "
                    f"hull, and it is refused rather than defaulted — a bow "
                    f"patch built from a half-read file would still mesh and "
                    f"still report a number.")
            xs = [v[0] for v in verts]
            blocks.append(("\n".join(cur), min(xs), max(xs)))
            cur, verts = [], []
    if not blocks:
        raise ValueError(
            f"{path}: no ascii STL facets found, so the bow patch cannot be "
            f"cut. Every STL reader in this project ({path.name} included) is "
            f"an ASCII reader; a binary STL reaches here as zero facets and "
            f"must not be mistaken for an empty hull.")

    x_stem = max(b[2] for b in blocks)
    x_aft = min(b[1] for b in blocks)
    x_split = x_stem - frac * (x_stem - x_aft)
    bow = [b for b in blocks if b[2] >= x_split]
    main = [b for b in blocks if b[2] < x_split]
    if not main:
        raise ValueError(
            f"{path}: the bow cut at x = {x_split:.4f} m "
            f"(stem {x_stem:.4f} m minus {frac:g} of the {x_stem - x_aft:.4f} "
            f"m hull) puts ALL {len(bow)} facet(s) in the bow solid and none "
            f"in the main solid; the surface spans {x_aft:.4f}..{x_stem:.4f} "
            f"m. Both solids must be non-empty: an empty region gives snappy a "
            f"patch with no faces, and a hull that is entirely bow is not a "
            f"hull with a bow patch. Lower the fraction, or check that this "
            f"surface really has a longitudinal extent.")

    out = [f"solid {_STL_MAIN_SOLID}"]
    out += [b[0] for b in main]
    out.append(f"endsolid {_STL_MAIN_SOLID}")
    out.append(f"solid {_STL_BOW_SOLID}")
    out += [b[0] for b in bow]
    out.append(f"endsolid {_STL_BOW_SOLID}")
    data = ("\n".join(out) + "\n").encode()
    path.write_bytes(data)
    return {"fraction": frac, "x_stem": x_stem, "x_split": x_split,
            "hull_length": x_stem - x_aft,
            # The patch's ACTUAL aft edge, which is at or abaft the nominal
            # plane because a straddling facet rounds forward. Recorded so the
            # over-inclusion is a measured number in the case directory rather
            # than an assumption in a docstring.
            "x_aftmost": min(b[1] for b in bow),
            "n_bow": len(bow), "n_main": len(main), "n_total": len(blocks),
            "sha256_shipped": hashlib.sha256(data).hexdigest()}


def stl_watertight_report(path: Path) -> dict:
    """Parse an ascii STL and check closed-manifoldness geometrically.

    Every undirected edge of a closed 2-manifold is shared by exactly two
    triangles. Also returns the signed enclosed volume (divergence theorem) —
    meaningful only when windings are consistently outward.
    """
    tris = []
    cur: list = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line.startswith("vertex"):
            cur.append(tuple(round(float(v), 6) for v in line.split()[1:4]))
            if len(cur) == 3:
                tris.append(tuple(cur))
                cur = []
    from collections import Counter
    edges: Counter = Counter()      # undirected: closedness
    directed: Counter = Counter()   # directed: consistent winding
    vol = 0.0
    for a, b, c in tris:
        for e in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted(e))] += 1
            directed[e] += 1
        va, vb, vc = np.array(a), np.array(b), np.array(c)
        vol += float(np.dot(va, np.cross(vb, vc))) / 6.0
    bad = [e for e, n in edges.items() if n != 2]
    # WINDING, not just closedness. Keying only on tuple(sorted(edge)) is
    # blind to orientation: a flipped triangle still gives each of its edges a
    # count of 2, so this reported `watertight: True` on our own hulls while
    # 397 deck triangles pointed INTO the boat and the signed volume was 38%
    # low. A manifold edge that is traversed the same way TWICE means the two
    # triangles sharing it disagree — that is the actual signature.
    conflicts = sum(1 for e, n in directed.items() if n > 1)
    return {"n_tris": len(tris), "open_or_nonmanifold_edges": len(bad),
            "winding_conflicts": conflicts,
            "watertight": len(bad) == 0 and conflicts == 0,
            "outward": vol > 0.0,
            "signed_volume": vol}


def layer_spec(lwl: float, speed: float, scale: float = 1.0) -> dict:
    """The near-wall stack this case WOULD get at `scale`, without writing it.

    Exists so `scripts/make_case.py --triplet` can pin the anchor grid's layer
    count and hand it to every member. Deriving it inside each case is what
    made the stack thin from 12.9*t1 to 7.4*t1 across a triplet whose own
    case.info claimed the wall model was held fixed.
    """
    nx = max(int(round(_NX_BASE * scale)), 20)
    hull_cell = _DOMAIN_LENGTH_L * lwl / nx / 2 ** _HULL_REFINE[0]
    t1 = first_layer_thickness(speed, lwl, _TARGET_YPLUS)
    n_ideal = n_layers_to_bridge(t1, hull_cell, _LAYER_EXPANSION)
    return {"n_layers": min(n_ideal, _MAX_LAYERS), "n_ideal": n_ideal,
            "first_layer_m": t1, "hull_cell_m": hull_cell, "nx": nx}


# The floor is 3 because that is the count CLAUDE.md records as clean on KCS
# (97.7% coverage, 0 zero-volume, 0 wrongly-oriented) and because a 2-layer
# stack stops being a boundary layer. It is NOT "the safest count": MEASURED
# 2026-08-11 on grammar hull 1 (lwl 10.473), n=3 gives max skewness 20.32 and
# 2 wrongly-oriented faces and is REFUSED, while n=5 and n=7 on the same hull
# are clean. Lower is not monotonically better, which is why the ladder stops
# at the FIRST count that passes rather than going straight to the floor.
_LAYER_FLOOR = 3
_LAYER_SEARCH_STEP = 1   # was 2 and DESCENDING-only; see layer_backoff_ladder


def layer_backoff_ladder(n_derived: int, floor: int = _LAYER_FLOOR,
                         step: int = _LAYER_SEARCH_STEP,
                         ceiling: int | None = None) -> list[int]:
    """Prism-layer counts to try after `n_derived` is refused, in order.

    WHY THIS EXISTS (MEASURED 2026-08-11, the Gate 2U coarse campaign).
    `n_layers_to_bridge` derives 8, 9 or 10 layers for EVERY hull the grammar
    samples — it optimises for bridging the stack to the local hull cell and,
    as `scripts/make_case.py --n-layers` already says, "has no way to know what
    snappy will do to THIS geometry". On the first two hulls of the seed-0
    batch the derived count produces a mesh `run-case.sh` refuses:

        hull  lwl     n derived  zeroVol  wrongOri  skew    verdict
         0    15.015     10         12       92     23.76   REFUSED
         0    15.015      7          0        0      4.52   clean
         1    10.473      9          0        8     25.37   REFUSED
         1    10.473      7          0        0      3.25   clean

    docs/LESSONS.md records that a BUILD-TIME predictor was drafted for this
    and killed by its own data (Wigley solves at stack/hull_cell 1.084 while
    KCS dies at 0.952), so the count cannot be corrected before meshing. What
    remains is to MEASURE and back off — which is exactly the manual step
    `run-case.sh` already prints on refusal ("pass n_layers to the generator
    -- make_case.py --n-layers N"), and automating an operator's own documented
    response is what "unattended" means in this gate's bar.

    This changes NO bar. The checkMesh gates (0 zero-volume, <=5
    wrongly-oriented, <=20 skewness) judge every rung identically; a hull that
    fails all of them still fails.

    THE ONE-DIRECTIONAL WALK WAS STRUCTURALLY BROKEN, and it is fixed here.
    It started at `n_derived - step` and only ever went DOWN, so with rung 0 at
    _MAX_LAYERS=7 and step 2 the reachable set was {5, 3}. MEASURED over the
    25-hull seed-0 matrix, that cannot reach the count several hulls need:

        hull 10 meshes ONLY at n=8      hull 12 meshes ONLY at n=6
        hull 18 meshes CLEAN at n=10 (skew 6.19) and FAILS at 7 (skew 70.98)

    A ladder that can only descend cannot find any of those. Worse, the step of
    2 skipped the even counts entirely from an odd start, so hull 12's 6 was
    unreachable even within the descending range.

    AND THE TARGET IS NOT A THRESHOLD, IT IS A SET WITH HOLES. For a fixed hull
    the outcome is not monotone in n and not even unimodal — three of the twelve
    hulls run at three or more counts have a FAILURE STRICTLY BETWEEN TWO
    PASSES:

        hull 5:  n=3 ok   n=5 ok   n=7 FAIL (182 wrongOri, skew 56.80)  n=8 ok
        hull 8:  n=4 ok   n=6 FAIL         n=7 ok (0 wrongOri, skew 2.87)
        hull 3:  n=3 ok   n=5 FAIL         n=7 ok

    So no rule emitting ONE integer per hull can express an admissible set of
    {3, 5, 8}, and no early-exit on the first failure is safe: the count above a
    failure may pass. This is a SEARCH, not a prediction, and that is why it
    survives the standing counter-example — docs/LESSONS.md records that a
    build-time predictor was drafted and killed by its own data (Wigley solves
    at stack/hull_cell 1.084 while KCS dies at 0.952). A search predicts
    nothing, so it cannot be wrong about those two.

    ORDERED OUTWARD FROM THE DERIVED COUNT, step 1, both directions, bounded
    below by `floor` and above by `ceiling` (default `n_ideal`, the unclamped
    bridging count — going above it buys a stack the near-wall cell cannot
    support). Outward order because the derived count is still the best single
    guess: it is right on 19 of 25 hulls, so a hull that needs a rung usually
    needs a near one, and 1.9 rungs per hull is the measured mean.
    """
    n0, lo = int(n_derived), int(floor)
    hi = int(ceiling) if ceiling is not None else max(n0, lo)
    out: list[int] = []
    for d in range(1, max(n0 - lo, hi - n0) + 1):
        for cand in (n0 - d, n0 + d):        # down first: cheaper to mesh
            if lo <= cand <= hi and cand != n0 and cand not in out:
                out.append(cand)
    return out


def benchmark_of_sha(stl_sha: str) -> str | None:
    """Name the benchmark hull this STL hash belongs to, or None.

    `data/benchmark_geom/CHECKSUMS.json` already pins the hash of every
    benchmark geometry, so the case can record WHICH SHIP it is instead of
    leaving a downstream gate to assume. Gate 2M assumed, and scored a Wigley
    hull against KRISO KCS tank data.
    """
    import json
    checks = (Path(__file__).resolve().parents[2] / "data" /
              "benchmark_geom" / "CHECKSUMS.json")
    try:
        entries = json.loads(checks.read_text())
    except (OSError, ValueError):
        return None
    for name, entry in entries.items():
        if isinstance(entry, dict) and entry.get("sha256") == stl_sha:
            return Path(name).stem.lower()
    return None


def write_resistance_case_from_stl(stl_path: str | Path, lwl: float,
                                   speed: float, out_dir: str | Path,
                                   end_time: float = 40.0, scale: float = 1.0,
                                   np_procs: int = 8,
                                   symmetric: bool = False,
                                   free_motion: dict | None = None,
                                   lts: bool | None = None,
                                   n_layers: int | None = None) -> dict:
    """Same case generator, but for EXTERNAL geometry (KCS/JBC calibration).

    The STL must be watertight, in metres, with the free surface at z=0 and
    the hull spanning x in [0, lwl] (translate/scale upstream if needed).
    """
    out = Path(out_dir)
    (out / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)

    # THE IMPORT BOUNDARY, AND THE ONE PLACE REPAIR BELONGS. The docstring
    # above has said "The STL must be watertight" since this function was
    # written and enforced NOTHING — the same shape as `stl_watertight_report`
    # being reachable from everywhere except the code that meshes.
    #
    # This is where third-party geometry enters, and CLAUDE.md records what
    # arrives: the mirrored `KCS.igs` mesh died on the first timestep with 73
    # wrongly-oriented faces, and plain `surfaceCheck` called it fine.
    #
    # Winding is REPAIRED (relabelling triangles moves no vertex, so the shape
    # is bit-identical). Holes and true self-intersections are REFUSED, not
    # patched: closing them retriangulates, and silently changing an imported
    # benchmark's shape would invalidate the very comparison it exists for.
    from ..mesh_repair import IMPORTED, diagnose
    rep = diagnose(str(stl_path), origin=IMPORTED)
    if rep.found["boundary_edges"] or rep.found["nonmanifold_edges"]:
        raise ValueError(
            f"imported STL is not a closed manifold and will not be meshed: "
            f"{rep.found['boundary_edges']} boundary edge(s), "
            f"{rep.found['nonmanifold_edges']} non-manifold edge(s). An open "
            f"shell floods the interior and yields a complete, plausible, "
            f"meaningless run. Repair it upstream — navalai.mesh_repair.repair "
            f"reports what is wrong; it will not close a hole for you, because "
            f"that retriangulates and changes the geometry you are calibrating "
            f"against.")

    data = Path(stl_path).read_bytes()
    (out / "constant" / "triSurface" / "hull.stl").write_bytes(data)
    stl_sha = hashlib.sha256(data).hexdigest()
    info = _write_case_dicts(out, stl_sha, lwl, speed, end_time, scale,
                             np_procs, symmetric, free_motion, lts, n_layers)
    # The receipt goes in whether or not anything was wrong, so a reader can
    # tell "checked and clean" from "never checked".
    with (out / "case.info").open("a") as fh:
        for k, v in rep.found.items():
            fh.write(f"import_{k}={v}\n")
        fh.write(f"import_winding_repaired={'yes' if rep.applied else 'no'}\n")
    return info


def write_resistance_case(hull: Hull, speed: float, out_dir: str | Path,
                          end_time: float = 40.0, scale: float = 1.0,
                          np_procs: int = 8, symmetric: bool = False,
                          free_motion: dict | None = None,
                          lts: bool | None = None,
                          n_layers: int | None = None) -> dict:
    """Generate a COMPLETE, runnable interFoam resistance case.

    scale: background-mesh refinement multiplier (1.0 / sqrt(2) steps give
    the GCI triplet). Templates are DTCHull-tutorial-derived; first-run
    tuning on the OpenFOAM machine is expected and normal.

    n_layers: prism-layer count. Leave None for a single case (it is derived
    from the local hull cell); PIN it across a GCI triplet, or the wall mesh
    refines along with the outer mesh and the observed order p absorbs both.
    """
    out = Path(out_dir)
    (out / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)
    lwl = float(hull.x[-1])
    # Triangulate finer than the smallest cell that will snap to this surface,
    # or snappy snaps to facets and the layer stack sits on a faceted wall.
    bg_dx = _DOMAIN_LENGTH_L * lwl / max(int(round(_NX_BASE * scale)), 20)
    target_edge = 0.5 * bg_dx / 2 ** _HULL_REFINE[1]
    nx, nz = stl_resolution(lwl, target_edge)
    nx_req = stl_resolution_request(lwl, target_edge)
    stl_path = out / "constant" / "triSurface" / "hull.stl"
    stl_sha = hull_to_stl(hull, stl_path, nx=nx, nz=nz)

    # THE GUARD EXISTED AND NOTHING ON THIS PATH CALLED IT (defect class 3, a
    # guard never made to fire). MEASURED 2026-08-12: `stl_watertight_report`
    # was reachable from `pipeline.py` (a REPORTING surface), from three
    # standalone scripts and from the tests — but not from `write_resistance_case`
    # and not from `run-case.sh`, i.e. not from anything on the path that
    # actually hands a surface to snappyHexMesh. Every CFD case this project
    # has ever generated was meshed from an UNVALIDATED STL.
    #
    # CLAUDE.md's first hard-won CFD rule is "Hull STL must be a CLOSED
    # manifold; `stl_watertight_report` gates it. Open shells flood the
    # interior." It said "gates it" and nothing did.
    #
    # This is FATAL rather than a warning. An open shell does not produce a
    # worse mesh, it produces a DIFFERENT SIMULATION -- water inside the hull
    # -- and a complete, plausible, meaningless force history, which is the
    # same failure mode as the `setFields` guard three hundred lines down.
    rep = stl_watertight_report(stl_path)
    if not rep.get("watertight", False):
        raise ValueError(
            f"hull.stl is not a closed manifold and will not be meshed: "
            f"{rep}. An open shell floods the interior and yields a complete, "
            f"plausible, meaningless run — see CLAUDE.md 'Hard-won CFD "
            f"gotchas'. Fix the geometry; do not mesh this.")

    info = _write_case_dicts(out, stl_sha, lwl, speed,
                             end_time, scale, np_procs, symmetric,
                             free_motion, lts, n_layers)
    # THE CLAMP IS A SILENT KNOB, so it gets a receipt. MEASURED 2026-08-12
    # (docs/research/STL.md): `nx_requested` is 811 for EVERY hull in the
    # seed-0 batch — target_edge is proportional to lwl, so lwl cancels — and
    # the 600 cap binds on all of them, shipping an STL 1.353x coarser in x
    # than the generator asked for. Nothing in the case directory said so.
    # `stations` is the number that actually bounds longitudinal resolution:
    # `Hull.closed_mesh` interpolates linearly between them, so nx buys
    # triangles, not geometry.
    with (out / "case.info").open("a") as fh:
        fh.write(f"stl_nx_requested={nx_req}\nstl_nx_shipped={nx}\n"
                 f"stl_nz_shipped={nz}\n"
                 f"stl_target_edge_m={target_edge:.6f}\n"
                 f"stl_edge_x_m={lwl / nx:.6f}\n"
                 f"stl_resolution_shortfall={nx_req / nx:.4f}\n"
                 f"stl_stations={len(hull.x)}\n"
                 f"stl_station_spacing_m={lwl / max(len(hull.x) - 1, 1):.6f}\n"
                 "  # shortfall > 1 means the [80, 600] clamp bound. It binds\n"
                 "  # on every hull in the seed-0 batch, so stl_nx_shipped is\n"
                 "  # INDEPENDENT of lwl; see stl_resolution's docstring.\n")
    return info


def background_counts(scale: float, symmetric: bool) -> tuple[int, int, int, int, int, int]:
    """Background block counts: (nx, ny, nz_deep, nz_hull, nz_wave, nz_air).

    ONE home for the count rule. It was computed inline inside
    `_write_case_dicts`, and `navalai/fidelity.py` needed the same numbers to
    price a grid WITHOUT writing a case -- which is the shape of the defect
    this codebase keeps producing (a number declared twice), so it is a
    function rather than a second copy. The apportioning logic below is the
    MEASURED one: see the comments for why ny derives from nx by a fixed ratio
    and why the four z-bands use largest-remainder.
    """
    nx = max(int(round(_NX_BASE * scale)), 20)
    # ny FROM nx BY A FIXED RATIO, and the full domain is EXACTLY twice the
    # half domain. It used to be `round((1.5 if symmetric else 3.0) * lwl /
    # dx_bg)`, i.e. a second, independent rounding of a half-size number, and
    # half-size is where rounding hurts most: MEASURED on the scale
    # 1 / sqrt2 / 2 family at base 54, ny went 18 / 25 / 36 (ratios 1.3889 and
    # 1.4400) while the full domain got 36 / 51 / 72 (1.4167 and 1.4118). The
    # symmetric triplet's two refinement steps then disagreed by 0.85% against
    # the full domain's 0.47% — and 51 is ODD, so the "half domain" was not
    # half of anything, it was a third mesh. See `_NX_BASE` for the base change
    # that makes nx divisible by 3 at every member, which is what makes this
    # division exact.
    ny_half = max(int(round(nx * _NY_PER_NX_HALF)), 6)
    ny = ny_half if symmetric else 2 * ny_half

    # z resolution is tied to nx by a fixed constant, then apportioned across
    # the four bands by their scale-1 shares (6:2:2:4 of 14) using largest
    # remainder, so the total tracks nx exactly and the shares stay put.
    nz_total = max(int(round(nx * _NZ_PER_NX)), 4)
    shares = (6.0, 2.0, 2.0, 4.0)
    exact = [nz_total * s / sum(shares) for s in shares]
    counts = [max(int(e), 1) for e in exact]
    for i in sorted(range(4), key=lambda i: exact[i] - int(exact[i]),
                    reverse=True)[:max(nz_total - sum(counts), 0)]:
        counts[i] += 1
    nz_deep, n_hull, n_wave, nz_air = counts
    return nx, ny, nz_deep, n_hull, n_wave, nz_air


def _write_case_dicts(out: Path, stl_sha: str, lwl: float, speed: float,
                      end_time: float, scale: float, np_procs: int,
                      symmetric: bool = False,
                      free_motion: dict | None = None,
                      lts: bool | None = None,
                      n_layers: int | None = None) -> dict:
    (out / "system").mkdir(parents=True, exist_ok=True)
    # Initial fields live in 0.orig and are COPIED to 0 (the OpenFOAM tutorial
    # convention). setFields rewrites 0/alpha.water as a full non-uniform field
    # sized for the snapped mesh; re-running the pipeline in that directory then
    # hands snappyHexMesh a field with the wrong cell count and it dies with an
    # FPE in markFeatureCellLevel (measured: 1.67 MB alpha.water vs 817 B
    # pristine, snappy exit 132 on a case that had meshed cleanly minutes
    # before). A case directory has to be re-runnable.
    (out / "0.orig").mkdir(parents=True, exist_ok=True)

    # THE BOW PATCH IS CUT HERE, IN THE ONE PLACE BOTH ENTRY POINTS PASS
    # THROUGH, so a generated hull and an imported benchmark get the same
    # instrument. It happens before `stl_wetted_area` reads the file below
    # (that reader is vertex-line based, so the two solids are invisible to it)
    # and after both callers have hashed the geometry AS DELIVERED — see the
    # `stl_sha256_shipped` receipt in case.info for why those are two different
    # hashes and why neither may be dropped.
    bow = split_bow_region(out / "constant" / "triSurface" / "hull.stl")

    # Domain: towing-tank box around the hull (hull x in [0, L]), split at the
    # waterline. Depth 0.6L and air 0.25L replace the old 1.5L/0.75L: the tank
    # only has to be deep-water for the generated wave (lambda/2 = pi*U^2/g,
    # checked below), and the cells that bought 15 m of still water underneath
    # are worth far more spent on the free surface.
    # Deep water is a property of the WAVE, not of the hull: a tank shallower
    # than half a wavelength changes the dispersion relation, so the depth
    # tracks speed rather than sitting at a fixed multiple of LWL. 0.6L is
    # ample at the Fn ~ 0.26 design point; a planing-speed case deepens itself
    # instead of quietly computing shallow-water resistance and calling it
    # deep-water resistance.
    half_lambda = math.pi * speed ** 2 / _G
    # TANK DEPTH >= 1 SHIP LENGTH, not 0.6.
    # The deep-water WAVE criterion (depth > lambda/2) was already satisfied at
    # 0.6 L, but the snappyHexMesh user guide section 4.4.2 discussion of marine
    # domains and the Wolf Dynamics KCS reference (1.37 Lpp) both use at least a
    # ship length, and the reference deck states it outright: "the depth must be
    # greater than 1 wave length... a good choice is at least 1 ship length".
    # A shallow tank raises wave resistance, and pressure drag was MEASURED at
    # 2.6-4.2x the expected wave component in every run. The extra cells are in
    # the most graded, cheapest part of the mesh.
    depth = max(1.0 * lwl, 1.5 * half_lambda)

    # z bands. The uniform core spans the hull draft plus the wave, because
    # refineMesh cannot refine z at all — every z cell we need must exist in
    # blockMesh. zh reaches below the deepest keel we expect (0.09L covers a
    # 0.055L draft with margin); za covers the crest.
    zh = -_Z_BANDS["hull"] * lwl
    za = _Z_BANDS["wave"] * lwl
    # ONE BASE MESH, UNIFORMLY REFINED. Every count derives from nx, so the
    # three grids are the same mesh at three resolutions rather than three
    # separately-rounded meshes.
    #
    # They used to be computed independently — nx, ny and each of the four nz
    # blocks rounded from `scale` on its own — and independent rounding is not
    # a refinement family: the cell aspect wobbled 1.85 / 1.32 / 1.85 and the
    # measured ratio came out r12 1.378, r23 1.452 (5.1% apart) against the
    # sqrt(2) the triplet claims. Richardson extrapolation then measures a
    # changing cell SHAPE mixed in with the changing cell SIZE, which is the
    # same defect that made the v1 triplet oscillate.
    nx, ny, nz_deep, n_hull, n_wave, nz_air = background_counts(scale, symmetric)
    dx_bg = _DOMAIN_LENGTH_L * lwl / nx
    dz_core = abs(zh) / n_hull

    dom = dict(x0=_DOMAIN_X[0] * lwl, x1=_DOMAIN_X[1] * lwl,
               y0=0.0 if symmetric else -_DOMAIN_HALF_WIDTH_L * lwl,
               y1=_DOMAIN_HALF_WIDTH_L * lwl,
               z0=-depth, zh=zh, za=za, z1=0.25 * lwl,
               side1_type="symmetry" if symmetric else "wall",
               nx=nx, ny=ny,
               nz_deep=nz_deep, nz_hull=n_hull, nz_wave=n_wave, nz_air=nz_air,
               # THE AIR GRADING IS DERIVED so the block MATCHES the ungraded
               # core band at the face they share, instead of a fixed 20.0
               # that put an 8.74x refinement step there — see `_z_grading`
               # for the hull-4 measurement (38 wrongly-oriented faces, all
               # inside the first air cell, tracking the blockMesh boundary
               # when it moved). The deep block keeps the fixed value: it has
               # the same defect in the other direction and correcting it
               # MEASURED WORSE across the batch (19/25 -> 16/25).
               g_deep=float(_Z_EXPANSION),
               g_air=_z_grading(dz_core, 0.25 * lwl - za, nz_air,
                                core_below=True))
    assert depth >= half_lambda, "deep-water condition violated"

    # THE STEP ACROSS EACH INTERNAL z-BLOCK BOUNDARY, RECORDED. It was 8.74x
    # (wave/air) and 8.20x (deep/hull) for the life of this generator and
    # nothing in the case directory said so; hull 4's 38 wrongly-oriented
    # faces all sat inside the 46 mm cell that step produced. A receipt is
    # what makes the next one visible without decoding a VTK face set.
    def _shared_cell(height: float, n: int, grading: float,
                     first: bool) -> float:
        r = grading ** (1.0 / (n - 1))
        f = height / sum(r ** i for i in range(n))
        return f if first else f * r ** (n - 1)

    z_step_air = _shared_cell(0.25 * lwl - za, nz_air, dom["g_air"],
                              first=True) / dz_core
    z_step_deep = _shared_cell(depth + zh, nz_deep, dom["g_deep"],
                               first=False) / dz_core

    fs_dz = dz_core                     # uniform through hull and wave bands
    # x cell inside the free-surface refinement box (snappy, isotropic)
    dx = (dom["x1"] - dom["x0"]) / dom["nx"] / 2 ** 2
    # z cell there after the z-only refineMesh rounds that follow snappy
    fs_dz = dz_core / 2 ** 2 / 2 ** _REFINE_ROUNDS
    wavelength = 2 * math.pi * speed ** 2 / _G
    # near-wall stack sized for the wall functions, bridging to the local
    # hull cell (background dx divided by the hull surface refinement level)
    # Size the stack against the cell on FLAT hull area, which takes the MIN
    # refinement level — that is most of the hull, and it is where layers have
    # to bridge the furthest. Using the max level here flattered the estimate.
    # ONE derivation, shared with `layer_spec` so make_case.py can ask what the
    # anchor grid would get WITHOUT writing a case to find out.
    _spec = layer_spec(lwl, speed, scale)
    t1, hull_cell, n_ideal = (_spec["first_layer_m"], _spec["hull_cell_m"],
                              _spec["n_ideal"])
    assert _spec["nx"] == dom["nx"], "layer_spec disagrees with the block mesh"
    # THE WALL MODEL MUST BE FROZEN ACROSS A GCI TRIPLET, AND IT WAS NOT.
    # case.info has told every reader "first-layer thickness is held constant
    # across the GCI triplet, so the GCI bounds OUTER-flow discretisation, not
    # the wall model", and CLAUDE.md repeats it. The first layer IS constant —
    # `first_layer_thickness` depends only on speed and Lwl — but the LAYER
    # COUNT is not, because `n_layers_to_bridge` reads `hull_cell`, which
    # scales with nx. REPRODUCED on a scale 1 / sqrt2 / 2 symmetric KCS
    # triplet at base 54: n_layers came out 7 / 6 / 5, so the prism stack
    # height went 12.9*t1 -> 9.9*t1 -> 7.4*t1. The near-wall mesh was being
    # refined at the same time as the outer mesh, and the observed order p
    # absorbs BOTH — which is precisely the quantity the note says it excludes.
    # `n_layers` is therefore pinned ONCE at the anchor scale by the caller
    # (scripts/make_case.py --triplet) and passed to every member.
    n_layers = min(n_ideal, _MAX_LAYERS) if n_layers is None else int(n_layers)
    if n_layers < 1:
        raise ValueError(f"n_layers must be >= 1, got {n_layers}")

    # LAYER PROPORTIONS ARE ASSERTED AT BUILD TIME, not discovered after a
    # multi-hour solve. OpenFOAM's shipped default is `finalLayerThickness 0.3`
    # RELATIVE — i.e. its own intent is that the outermost layer is ~0.3 of the
    # adjacent undistorted cell, a ~3:1 step into the background. DTCHull goes
    # to 0.7. The configuration that produced NO LAYERS AT ALL had a last layer
    # at 0.071 of the adjacent cell and a stack at 0.167 of it: four times below
    # the documented proportion, and at the edge of the default minThickness.
    # This check is the thing that would have caught it in 2 minutes rather
    # than after weeks of solves on a layerless mesh.
    stack = t1 * (_LAYER_EXPANSION ** n_layers - 1) / (_LAYER_EXPANSION - 1)
    last_layer = t1 * _LAYER_EXPANSION ** (n_layers - 1)
    last_ratio = last_layer / hull_cell
    # The bar is 0.12, CALIBRATED FROM THE TWO MEASUREMENTS WE HAVE, not from
    # the documented 0.3 aspiration:
    #     last/adjacent = 0.071  ->   0% coverage (extrusion ratcheted to zero)
    #     last/adjacent = 0.145  -> 89.8% coverage, 5 layers
    # `hull_cell` is the MIN refinement level (37.9 mm), which is most of the
    # hull; against the max level (19 mm) the same stack reads 0.289, i.e. bang
    # on OpenFOAM's default. Setting the bar at 0.15 would have rejected a
    # configuration measured to work, so it sits just below the known-good
    # point and well above the known-bad one. Move it when a measurement says
    # to, not when a document does.
    # WARN, do not refuse. This is a PREDICTION calibrated from two KCS
    # measurements, and it fires on the analytic own-hull cases too — which is
    # itself a real finding (they share the bridging problem), but refusing to
    # generate a case on a predicted failure is overreach when the ACHIEVED
    # layer count is measured 2 minutes later and is already fatal in
    # run-case.sh. Predict here, gate there, and record the prediction so the
    # two can be compared.
    # THE STACK MUST ALSO FIT IN THE CELL IT IS INSERTED INTO.
    # Checking only last_layer/hull_cell misses the opposite failure. MEASURED:
    # at Fn 0.10 the first-layer thickness scales as 1/u_tau, so it is 2.9x
    # THICKER than at Fn 0.26 and the 5-layer stack came to 57 mm against a
    # 37.9 mm hull cell — layers thicker than the cell they extrude into. The
    # mesh built, and interFoam then died at t=0.0012 with deltaT collapsing to
    # 1e-23: CLAUDE.md's documented pathological-cell signature. The bar is
    # 1.2, just above OpenFOAM's own defaults (finalLayerThickness 0.3 with 5
    # layers at 1.2 gives a stack of ~1.08 of the adjacent cell).
    stack_ratio = stack / hull_cell
    if stack_ratio > 1.2:
        raise ValueError(
            f"layer stack {stack * 1e3:.1f} mm does not FIT the "
            f"{hull_cell * 1e3:.1f} mm hull cell (ratio {stack_ratio:.2f} > "
            f"1.2). snappy will extrude cells larger than their host and "
            f"interFoam will die with deltaT collapsing to ~1e-20. Lower "
            f"_MAX_LAYERS or _TARGET_YPLUS, or refine the hull less. "
            f"(first layer {t1 * 1e3:.2f} mm scales as 1/u_tau, so this bites "
            f"at LOW speed, not high.)")
    if last_ratio < 0.12:
        import warnings
        warnings.warn(
            f"layer stack may not bridge to the background: last layer "
            f"{last_layer * 1e3:.2f} mm is {last_ratio:.3f} of the "
            f"{hull_cell * 1e3:.1f} mm hull cell, against OpenFOAM's default "
            f"proportion of 0.3 (finalLayerThickness). MEASURED on KCS: 0.071 "
            f"gave ZERO layer coverage, 0.145 gave 89.8%. Raise _TARGET_YPLUS "
            f"or _MAX_LAYERS, or lower the hull refinement level. run-case.sh "
            f"will fail on the achieved count if this prediction is right.",
            stacklevel=2)
    dom.update(
        hull_lvl_min=_HULL_REFINE[0], hull_lvl_max=_HULL_REFINE[1],
        n_layers=n_layers, first_layer=t1, layer_expansion=_LAYER_EXPANSION,
        min_thickness=0.25 * t1, layer_feature_angle=_LAYER_FEATURE_ANGLE,
        fs_level=2, fs_dz_bg=dz_core, refine_rounds=_REFINE_ROUNDS,
        fs_x0=_FS_BOX["x0"] * lwl, fs_x1=_FS_BOX["x1"] * lwl,
        fs_y0=0.0 if symmetric else -_FS_BOX["y"] * lwl,
        fs_y1=_FS_BOX["y"] * lwl,
        fs_z0=-_FS_BOX["z"] * lwl, fs_z1=_FS_BOX["z"] * lwl,
        # locationInMesh: in the air, far upstream of the hull. The old
        # (-2.0L, 0.35L) sat ABOVE the new tank roof and off a round multiple
        # of the cell size; both are mesh-generation failures.
        loc_x=-1.97 * lwl, loc_z=0.137 * lwl,
        loc_y=0.31 * lwl if symmetric else 0.0,
        # Patch and STL-region names, from the module constants rather than
        # inlined into the templates: the same four words appear in
        # snappyHexMeshDict, controlDict, dynamicMeshDict and the field files,
        # and a name that drifts between them is a mesh that builds and a
        # function object that FATALs three hours later.
        hull_patch=HULL_PATCH_NAME, bow_patch=BOW_PATCH_NAME,
        stl_main_solid=_STL_MAIN_SOLID, stl_bow_solid=_STL_BOW_SOLID)

    # TURBULENCE INLET. The length scale is 1% of the BOUNDARY LAYER, not 1% of
    # the ship. MEASURED against the Wolf Dynamics KCS reference (k 7.233e-4,
    # omega 60.78): their inlet eddy viscosity is nu_t/nu = 11.9; ours was
    # 1968 — 165x — because the scale was 0.01*Lwl = 72.8 mm instead of ~0.8 mm,
    # and omega 1.35 1/s barely decays before reaching the hull. Excess
    # freestream nu_t thickens the boundary layer and RAISES skin friction,
    # which is the direction our C_T error already points (we over-predict).
    # delta ~ 0.37 L Re^-0.2 is the flat-plate estimate; 1% of it is the scale.
    re_l = max(speed * lwl / _NU_WATER, 1e4)
    delta = 0.37 * lwl * re_l ** -0.2
    turb_len = 0.01 * delta
    k_in = 1.5 * (0.01 * speed) ** 2 + 1e-8      # I = 1%, matching the reference
    w_in = k_in ** 0.5 / (0.09 ** 0.25 * turb_len)

    sysd, cons, zero = out / "system", out / "constant", out / "0.orig"
    # Checkpoint ~10 times per run. On a machine that thermal-sleeps mid-run
    # the write interval is what you lose per nap: at 5 s of sim time that was
    # ~1.7 h of fine-grid wall time thrown away each time. purgeWrite 3 keeps
    # the disk bounded regardless.
    write_int = max(end_time / 10.0, 0.5)
    # Aref must be the area the PATCH INTEGRAL actually covers, so a symmetric
    # case gets HALF the hull's wetted surface. MEASURED on runs/kcs_sym at
    # t=13.7063: forceCoeffs reported Cd 2.2158e-3 while force.dat gives
    # 4.4316e-3 — exactly 2x, because the STL spans the full beam while the
    # patch is half of it. gate2m.py is correct (it doubles the drag and uses
    # the full-hull area); forceCoeffs was silently wrong on EVERY symmetric
    # run, which disabled the independent cross-check that exists precisely to
    # catch a factor-of-two.
    from .post import stl_wetted_area
    try:
        aref = stl_wetted_area(out / 'constant' / 'triSurface' / 'hull.stl', 0.0)
        if symmetric:
            aref *= 0.5
    except Exception as exc:
        # Falling back to 1.0 silently turns every reported coefficient into
        # the raw force with a plausible-looking name. Refuse instead.
        raise RuntimeError(
            f"cannot compute Aref from the hull STL, so forceCoeffs would be "
            f"meaningless: {exc}") from exc
    # LTS is the default for FIXED-attitude cases and impossible for moving
    # ones: local time stepping has no global time, so a body that must move
    # through real time cannot use it.
    # LTS is impossible for a moving body (no global time), and it is also
    # WRONG for wave-making even when fixed: MEASURED on KCS, pressure drag
    # came out 14.5x the expected wave component under LTS against 2.6-4.2x
    # transient, because local pseudo-timesteps make wave propagation speed
    # meaningless. It is kept only as a cheap flow-field initialiser.
    lts = (not free_motion) if lts is None else bool(lts)
    if lts and free_motion:
        raise ValueError("LTS has no global time; a moving body needs transient")
    # Under LTS `endTime` counts PSEUDO-ITERATIONS, not seconds, so a caller
    # asking for "75 s" is asking for a physical duration that does not exist
    # here. Substitute an iteration budget and say so in case.info, rather than
    # silently running 75 iterations and reporting an unconverged number as a
    # result.
    if lts:
        end_time = float(_LTS_ITERATIONS)
        write_int = max(end_time / 10.0, 1.0)
    sysd.joinpath("controlDict").write_text(
        CONTROL_DICT.format(
            end_time=end_time, dt=1 if lts else 0.001, write_int=write_int,
            speed_abs=abs(speed), lwl=lwl, aref=max(aref, 1e-6),
            rho_water=f"{_RHO_WATER:.6g}", bow_patch=BOW_PATCH_NAME,
            time_control=TIME_CONTROL_LTS if lts else TIME_CONTROL_TRANSIENT))
    sysd.joinpath("blockMeshDict").write_text(BLOCKMESH.format(**dom))
    # Two passes: snap first (needs cubic cells), layers last (must not be
    # z-refined afterwards). With no refineMesh rounds the second dict is
    # unused and pass 1 does everything, so the single-pass case is unchanged.
    staged = _REFINE_ROUNDS > 0
    sysd.joinpath("snappyHexMeshDict").write_text(SNAPPY_STUB.format(
        castellate="true", do_snap="true",
        do_layers="false" if staged else "true", **dom))
    if staged:
        sysd.joinpath("snappyHexMeshDict.layers").write_text(SNAPPY_STUB.format(
            castellate="false", do_snap="false", do_layers="true", **dom))
    if free_motion:
        # Sinkage and trim. KCS Case 2.1 is towed FREE to sink and trim, so a
        # fixed-attitude solve answers a different question than the one the
        # tank measured — this is a known part of the C_T error, not a
        # refinement detail.
        cons.mkdir(parents=True, exist_ok=True)
        cons.joinpath("dynamicMeshDict").write_text(
            DYNAMIC_MESH.format(**free_motion))
        # side1 is a `symmetry` patch when symmetric, and constraint patches are
        # set by setConstraintTypes — declaring it again would clash.
        zero.joinpath("pointDisplacement").write_text(
            POINT_DISPLACEMENT.format(
                side1_pd_entry="" if symmetric else
                "side1      { type fixedValue; value uniform (0 0 0); }"))
    else:
        # A CASE DIRECTORY MUST BE REGENERABLE INTO WHAT WAS ASKED FOR.
        # These two files were only ever WRITTEN, never removed, so
        # regenerating a case FIXED on top of a previously FREE one left
        # `constant/dynamicMeshDict` and `0.orig/pointDisplacement` in place —
        # and interFoam reads dynamicMeshDict if it exists. The result is a
        # case that still sinks and trims while every receipt in it, including
        # `free_motion=False` in case.info, says it does not. The existing test
        # could not see it because it generates into a fresh `tmp_path`, which
        # is exactly the one situation where the stale file cannot exist.
        cons.mkdir(parents=True, exist_ok=True)
        (cons / "dynamicMeshDict").unlink(missing_ok=True)
        (zero / "pointDisplacement").unlink(missing_ok=True)
        (out / "0" / "pointDisplacement").unlink(missing_ok=True)

    sysd.joinpath("refineMeshDict").write_text(REFINE_MESH)
    # Nested boxes, each round halving x,y inside it. Box 1 covers the hull and
    # near wake generously; each subsequent box tightens toward the hull, so the
    # refinement is graded in space rather than in one jump.
    stack = t1 * (_LAYER_EXPANSION ** n_layers - 1) / (_LAYER_EXPANSION - 1)
    shield = max(2.5 * stack, 0.004 * lwl)
    for i, box in enumerate(_refine_boxes(lwl, symmetric), start=1):
        sysd.joinpath(f"topoSetDict.{i}").write_text(
            TOPO_SET.format(shield_m=shield, loc_x=dom["loc_x"],
                            loc_y=dom["loc_y"], loc_z=dom["loc_z"], **box))
    sysd.joinpath("fvSchemes").write_text(FV_SCHEMES.format(
        ddt="localEuler rDeltaT" if lts else "Euler"))
    sysd.joinpath("fvSolution").write_text(FV_SOLUTION.format(
        # LTS needs the pseudo-timestep smoothing/damping controls, or the
        # local dt field is discontinuous and the solve rings.
        pimple_time=("rDeltaTSmoothingCoeff 0.05; rDeltaTDampingCoeff 0.5;\n"
                     "  nAlphaSpreadIter 0; nAlphaSweepIter 0;" if lts else ""),
        # Under LTS the outer loop IS the pseudo-time march, so one is right.
        n_outer=1 if lts else 2,
        correct_phi="correctPhi yes; " if free_motion else ""))
    sysd.joinpath("decomposeParDict").write_text(DECOMPOSE.format(np=np_procs))
    sysd.joinpath("surfaceFeatureExtractDict").write_text(SURFACE_FEATURES)
    sysd.joinpath("setFieldsDict").write_text(SET_FIELDS.format(
        box_to_face=SET_FIELDS_BOX_TO_FACE if free_motion else ""))
    cons.joinpath("transportProperties").write_text(TRANSPORT)
    cons.joinpath("g").write_text(GRAVITY)
    cons.joinpath("turbulenceProperties").write_text(TURBULENCE)
    zero.joinpath("U").write_text(FIELD_U.format(
        u=speed, hull_u=_HULL_U_MOVING if free_motion else _HULL_U_FIXED))
    zero.joinpath("p_rgh").write_text(FIELD_P_RGH)
    zero.joinpath("alpha.water").write_text(FIELD_ALPHA)
    zero.joinpath("k").write_text(FIELD_K.format(k_in=f"{k_in:.3e}"))
    zero.joinpath("omega").write_text(FIELD_OMEGA.format(w_in=f"{w_in:.3e}"))
    zero.joinpath("nut").write_text(FIELD_NUT)

    if symmetric:
        for f in ("U", "p_rgh", "alpha.water", "k", "omega", "nut"):
            fp = zero / f
            fp.write_text(_as_symmetric(fp.read_text()))

    # working copy: run-case.sh restores this from 0.orig before every re-mesh
    import shutil
    if (out / "0").exists():
        shutil.rmtree(out / "0")
    shutil.copytree(zero, out / "0")

    bg_cells = dom["nx"] * dom["ny"] * (dom["nz_deep"] + dom["nz_hull"]
                                    + dom["nz_wave"] + dom["nz_air"])
    # Resolution receipt: the numbers that decide whether the wave field is
    # actually resolved, recorded per case so a bad triplet is diagnosable
    # from the case dir alone rather than from a post-hoc argument.
    cells_per_wave = wavelength / dx
    (out / "case.info").write_text(
        f"speed_ms={speed}\nlwl={lwl}\nscale={scale}\nstl_sha256={stl_sha}\n"
        # WHICH SHIP THIS IS. scripts/gate2m.py compared ANY directory against
        # the KRISO KCS tank data — `gate2m.py runs/wigley` printed E%D -59.0
        # for a Wigley hull under a header naming KCS's speed and Lpp. The
        # case now says what it is, from the STL hash the checksum record
        # pins, so the gate can refuse a hull it has no experiment for.
        f"benchmark={benchmark_of_sha(stl_sha) or 'unknown'}\n"
        # THE BOW PATCH, AND THE TWO HASHES, BOTH OF WHICH ARE NEEDED.
        # `stl_sha256` above is the identity of the geometry AS DELIVERED — it
        # is what `benchmark_of_sha` matches against CHECKSUMS.json, so it must
        # keep meaning "the file the benchmark ships". `split_bow_region` then
        # regroups the SAME facets into two named solids, which changes the
        # bytes on disk and therefore the hash of the file actually meshed.
        # Recording only one of them would make a reader who runs sha256sum on
        # `constant/triSurface/hull.stl` disagree with the case's own receipt
        # and have no way to tell which is lying. The split moves no vertex:
        # the facet text is copied verbatim.
        f"stl_sha256_shipped={bow['sha256_shipped']}\n"
        f"bow_patch={BOW_PATCH_NAME}\n"
        f"bow_patch_fraction={bow['fraction']:.4f}\n"
        f"bow_patch_hull_length_m={bow['hull_length']:.4f}\n"
        f"bow_patch_stem_x_m={bow['x_stem']:.4f}\n"
        f"bow_patch_x_split_m={bow['x_split']:.4f}\n"
        f"bow_patch_x_aftmost_m={bow['x_aftmost']:.4f}\n"
        f"bow_patch_facets={bow['n_bow']} of {bow['n_total']}"
        f" ({100.0 * bow['n_bow'] / bow['n_total']:.1f}%)\n"
        "  # instrument: functions/bowSlammingPressure -> max(p_rgh) over the\n"
        "  # bow patch, in postProcessing/bowSlammingPressure/. MAX, not\n"
        "  # average: the patch includes dry topsides, which dominate an\n"
        "  # average and cannot raise a maximum. Analytic companion:\n"
        "  # navalai.seakeeping.slam_pressure_band(beta_mid, beta_bow, V),\n  # which BRACKETS rather than predicting a point, because the\n  # deadrise varies across the patch and the FO does not say where\n  # its maximum occurred.\n"
        "  # THIS IS BOW IMPACT ONLY, AND IT IS PROBABLY NOT THE GOVERNING\n"
        "  # SLAM. The target vessel is a CATAMARAN, and a catamaran's\n"
        "  # governing slam is usually CROSS-STRUCTURE (WET-DECK) slamming --\n"
        "  # the bridge deck between the demihulls hitting the wave surface in\n"
        "  # head seas. A wave-piercing bow is designed to reduce BOW slam and\n"
        "  # does nothing for the wet deck, so this number is NOT evidence\n"
        "  # about seaway safety. There is no wet-deck patch in this case.\n"
        f"free_motion={bool(free_motion)}\n"
        f"nx={dom['nx']}\nny={dom['ny']}\n"
        f"nz_total={dom['nz_deep'] + dom['nz_hull'] + dom['nz_wave'] + dom['nz_air']}\n"
        f"cells_bg={bg_cells}\n"
        # THE FLOW-THROUGH TIME, so a reader never has to reconstruct the
        # domain to know whether a run is long enough to mean anything. The
        # 2026-08-06 re-audit found EVERY run in the repository sitting at
        # 0.13-0.70 of ONE flow-through while conclusions were drawn from
        # them, and nothing in case.info made that visible.
        f"domain_length_m={dom['x1'] - dom['x0']:.4f}\n"
        f"flow_through_s={(dom['x1'] - dom['x0']) / speed:.4f}\n"
        # AN ITERATION COUNT IS NOT A TIME, so it does not get divided by a
        # speed. MEASURED 2026-08-07: an LTS case generated with --end-time 20
        # recorded `end_time_flow_throughs=134.128`, because the LTS branch ten
        # lines above substitutes an ITERATION budget (2000) into `end_time`
        # and this line divided it by the domain length as if it were seconds.
        # 134 flow-throughs of a 32.75 m tank is 4.4 km of water: the receipt
        # was not merely wrong, it was unphysical, and it read as a run far
        # past the >= 5.0 the settled bar wants. Same defect as the layer table
        # that printed an achieved mean layer COUNT under the label of a first
        # layer thickness in metres. The enforcing guard was never fooled --
        # post.grid_result computes flow-throughs from the SOLVED time t[-1] --
        # but a receipt nobody can trust is worse than no receipt.
        + (f"end_time_iterations={int(end_time)}\n"
           "end_time_flow_throughs=N/A (LTS: end_time is an iteration budget, "
           "not seconds; flow-throughs are undefined for a pseudo-steady run)\n"
           if lts else
           f"end_time_s={end_time:.4f}\n"
           f"end_time_flow_throughs={end_time * speed / (dom['x1'] - dom['x0']):.3f}\n")
        + f"wavelength_m={wavelength:.4f}\ntank_depth_m={abs(dom['z0']):.4f}\n"
        f"fs_dz_m={fs_dz:.5f}\nfs_dx_m={dx:.5f}\n"
        # z-BLOCK CONTINUITY. 1.0 means the graded block's cell at the shared
        # face equals the ungraded core cell. The generator shipped 0.114 and
        # 8.20 here until 2026-08-12 (see `_z_grading`): the air block was
        # 8.74x FINER than the core band it adjoins, giving a 705.9 x 705.9 x
        # 46.0 mm slab — 15.34:1 — that hexRef8 carried to every refinement
        # level, and hull 4 folded 38 faces inside it at every layer count.
        f"z_core_dz_m={dz_core:.5f}\n"
        f"z_bg_aspect_dx_over_dz={dx * 2 ** 2 / dz_core:.3f}\n"
        f"z_step_wave_to_air={z_step_air:.4f}\n"
        f"z_step_deep_to_hull={z_step_deep:.4f}\n"
        f"z_grading_air={dom['g_air']:.6f}\nz_grading_deep={dom['g_deep']:.6f}\n"
        f"cells_per_wavelength={cells_per_wave:.1f}\n"
        f"target_yplus={_TARGET_YPLUS}\nfirst_layer_m={t1:.6e}\n"
        f"n_layers={n_layers}\nn_layers_to_fully_bridge={n_ideal}\n"
        f"layer_stack_m={stack:.6f}\nlast_layer_m={last_layer:.6f}\n"
        f"last_layer_over_hull_cell={last_ratio:.4f}\n"
        f"  # OpenFOAM's default finalLayerThickness is 0.3 of the adjacent\n"
        f"  # cell. MEASURED on KCS: 0.071 -> ZERO layers, 0.145 -> 89.8%.\n"
        f"symmetric={symmetric}\n"
        "NOTE: layers are capped for insertion success, so the stack does NOT\n"
        "  bridge to the local cell; y+ is controlled on layered faces only.\n"
        "  Check postProcessing/yPlus for what was actually achieved.\n"
        "NOTE: first-layer thickness AND layer count are held constant across\n"
        "  the GCI triplet (make_case.py --triplet pins n_layers at the anchor\n"
        "  scale), so the GCI bounds OUTER-flow discretisation with the wall\n"
        "  model fixed. Until 2026-08-06 only the THICKNESS was constant: the\n"
        "  count followed the hull cell and went 7/6/5 across the family, so\n"
        "  the prism stack thinned from 12.9*t1 to 7.4*t1 and p absorbed it.\n"
        "run: navalai/cfd/run-case.sh <this-dir> <np>\n"
        "Gate 2M = KCS/JBC resistance within Tokyo-2015 scatter, per-case GCI.\n")
    return {"stl_sha256": stl_sha, "speed": speed, "end_time": end_time,
            "scale": scale, "bg_cells": bg_cells,
            # n_layers is returned so a triplet can PIN the anchor's value on
            # every other member; first_layer_m was already constant by
            # construction and is returned beside it so both halves of the
            # "wall model held fixed" claim are checkable from the caller.
            "n_layers": n_layers, "first_layer_m": t1,
            "nx": dom["nx"], "ny": dom["ny"],
            "cells_per_wavelength": cells_per_wave, "fs_dz": fs_dz,
            "wavelength": wavelength, "tank_depth": abs(dom["z0"])}
