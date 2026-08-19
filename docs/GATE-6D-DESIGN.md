# Gate 6D — the refold fix, DESIGNED from measurement (2026-08-19)

Status: DESIGN BANKED, implementation deliberately gated behind the
current CFD validation window — the fix is a hull-kernel change, and the
Mac's in-flight calibration corpus (screen bars, 2U rows, one-mesh
receipts) describes current-kernel geometry. Landing it mid-window would
invalidate the calibration being bought at high CPU.

## The measurement (reference hull, 41 stations, developable rulings)

Two-sided refold deviation, localized by longitudinal decile (mm):

    bottom-stbd (watermark 124.0)        topside-stbd (43.7)
    x/Lwl      max     p95              x/Lwl      max     p95
    [0.0,0.5)  <=0.1   <=0.1           [0.0,0.5)  <=1.9   <=1.7
    [0.5,0.6)   16.3    0.7  <- x_mb   [0.5,0.6)    4.3    3.4
    [0.6,0.7)    2.3    1.5            [0.6,0.7)   37.6   26.7
    [0.7,0.8)    9.8    8.2            [0.7,0.8)   43.7   37.2
    [0.8,0.9)   29.2   21.5            [0.8,0.9)    9.8    7.1
    [0.9,1.0)  124.0   92.7  <- STEM   [0.9,1.0)   31.9   20.2

Direction: the watermark lives in HULL->PANEL (the panel undercovers the
curved stem region); panel->hull peaks at 39 mm in the same decile.

## What this re-weights

The ledger named two mechanisms without weights. Measured:

1. THE STEM DRIVES IT (124 / p95 93 on the bottom; 32-44 on the topside).
   The entrance/forefoot concentrates curvature in the last ~10% faster
   than any developable strip can follow — and the recorded 161-station
   re-measure (64.2/102.9, WORSE than at 41) proves it is the SHAPE, not
   the discretisation: the kernel's stem geometry is genuinely
   non-developable. The `w**0.15` sheer envelope's unbounded dy/dx and
   the forward plan-form branch both terminate here.
2. THE x_mb C1 BREAK IS A 16 mm CREASE — real, above the 5 mm bar,
   localized (max-only; p95 0.7), secondary.

## The kernel measurement (2026-08-20) — the mechanisms quantified

- **The SAC peak is a CORNER, and the family forces it.** Measured on the
  reference hull: a'(x_mb-) = +1.476/L against a'(x_mb+) = -0.031/L — a
  slope kink of 1.5/L in the area curve at the max-area station. The
  fullness family h(s) = s^p (p >= 1 branch) has h'(1) = p, so the aft
  branch CANNOT arrive at the peak flat; the 16 mm refold crease at
  [0.5, 0.6) is this corner expressed in the surface. No taper patch can
  fix a family-level property.
- **The stem ends as a wedge**: a'(stem) = -2.95/L (finite-slope area
  run-out) against a quadratic forefoot — the curvature concentration
  the 124 mm deviation lives in.

## The C1 family (the tractable fix)

Candidate replacing the p >= 1 branch: **h(s) = 1 - (1 - s^p)^2**
  - h(0) = 0, h(1) = 1 (the family contract);
  - h'(1) = 0 for every p — the peak is SMOOTH by construction;
  - closed-form moments (the property sac_exponents' Cp/lcb inversion
    cannot live without): int h = 2/(p+1) - 1/(2p+1),
    int s.h = 2/(p+2) - 1/(2p+2);
  - fullness range: p=1 gives 2/3 - 1/3 = 0.583...; p -> inf gives 1 —
    the range the solver needs on the aft body must be VERIFIED against
    sac_exponents' actual demand before adoption (the p < 1 branch's
    range may need its own C1 counterpart).

Acceptance unchanged (refold <= 5 mm both panels + the full Gate PF /
pin re-measure). Sequencing note superseded: the Mac's campaigns solve
FROZEN cases and the KCS benchmark is imported, so the kernel work no
longer waits on the window — it waits only on its own care.

## The implementation plan (post-window)

A. Kernel: replace the `w**0.15` sheer envelope with a taper whose dy/dx
   is bounded at the stem, and give the fore/aft plan-form branches a C1
   join at x_mb (the ledger's own prescription, now with measured
   priorities: A-stem first, A-xmb second).
B. Acceptance: refold_surface_deviation_mm <= 5 mm BOTH panels, the
   Gate PF descriptor ratchets re-measured (the kernel change moves every
   hull's shape — the physical-form layer exists exactly to govern this),
   and the FULL pin re-measure campaign (baselines, fronts, formcheck
   baseline JSON, screen bars — the same class of sweep R2.1 needed).
C. Sequencing: implement ONLY after the Mac's current window closes and
   its ledger rows are written, then regenerate the calibration corpus
   on the new kernel in the following window. The screen's confusion
   machinery re-accumulates automatically.

Reproduction: ~/.claude/jobs tmp 6d-profile/6d-hull2panel scripts, or
re-derive from this file's tables; refold_surface_deviation_mm is the
judge either way.

---

## The implementation campaign (2026-08-19) — measured, and the plan REVISED

The C1 family was built and probed (a SHARPER form than §"The C1 family"
banked: parameterise by FULLNESS f = int h directly — direct smoothed-power
h = (p+1)s^p − p·s^(p+1) for f ≤ 1/2, its mirror for f > 1/2, meeting at
smoothstep — flat at BOTH endpoints for every f, closed moments, and Cp
LINEAR in the two fullnesses so one bisection solves the LCB). Fleet demand
verified reachable: 299/300 sampled designs. Probe results, reference hull:

    kernel      bottom (two-sided)   topside    x_mb crease [0.5,0.6)
    current            124.0           43.7          16.3
    C1-hybrid           52.3           57.3           2.2  <- crease KILLED

Three further measurements MOVED THE PLAN:

1. **Transverse seams are a null result.** 1, 2, 3 seam cuts move the
   two-sided set metric < 0.1 mm. The deviation is LOCAL intrinsic twist
   in the last ~30%, not accumulated development error.
2. **Dial isolation.** Deadrise warp drives the bottom (8→30° = 52 mm
   under C1; no warp = 7.9; no warp + no forefoot = 4.1). Flare drives
   the topside (flare 0 = 9.4 mm; 3° alone = 26.8). The topside WORSENED
   under C1 because the flare envelope follows a(x) forward of x_mb.
3. **The low-twist corner EXISTS UNDER THE SHIPPED KERNEL**: flare = 0,
   forefoot = 0, warp ≤ +8° → 4.6–5.0 mm BOTH panels. Sharpie/dory-class.

REVISED DECISION: the kernel swap is NOT landed — it does not cross the
bar on warped hulls, the corner needs no swap, and swapping mid-window
invalidates the Mac's calibration corpus. What LANDED instead is the KIT
ADMISSION: `buildability.kit_buildability` (the gate's own meter, per
design, route = sheet-kit | mould), surfaced via `certify(with_kit=True)`,
REFOLD_BAR_MM single-sourced in limits.py, pinned by
tests/test_manufacturing.py::test_kit_admission_*. Gate 6D's re-framing
(watermark on a pinned kit-corner reference vs the mould-class reference
hull) is a decision OWED TO THE OPERATOR — see the gate-ledger row.
The C1 fullness-hybrid stays banked here for the post-calibration window;
its probe scripts: ~/.claude jobs tmp probe_c1_family.py.

**Existence proof (same day):** the KIT REFERENCE HULL — 12.2 m dory-class
(constant 9° deadrise, zero flare/forefoot, Cp 0.639), certifiable
(MARGINAL) AND sheet-kit at 4.16/4.16 mm; pinned by
`test_the_kit_reference_hull_is_certifiable_and_kit_buildable`. The 7 m
proportions in the corner refold fine but fail the 18 mm-ply cold-bend
radius — the Kit-Line's admissible region is the INTERSECTION of the refold
corner with the cold-bend and stability floors, and it is non-empty.
