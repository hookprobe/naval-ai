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
