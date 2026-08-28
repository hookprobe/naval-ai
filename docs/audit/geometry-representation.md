# Audit report: GEOMETRY & REPRESENTATION (agent A, 2026-08-14)

## SOURCE-OF-TRUTH
Representation = closed-form parametric offsets (NOT polyline stations, NOT NURBS). 16-gene vector -> design curves SAC a(x) (geometry:251) + DWL y_wl (:511) -> one station solve _stations (:311-440, closed-form quadratic chine root) = THE kernel. SAC exponents SOLVED from (Cp,lcb) by nested bisection sac_exponents (:157-248), refusal-not-clamp, 1921-station probe, wired into L0 (sac.target / section.solve).
Section kernel richer than 3 points (plate P2): sample_section (:539-574) = keel leg + quadratic-Bezier bilge fillet + topside leg; section_control 5-point (K,P0,C,P2,S); roundness gene; closed-form fillet area; roundness==0 reproduces old 3-point BIT-FOR-BIT (fenced test).
Immersed area/centroid EXACT (de Casteljau split), no sampling.
NO NURBS/BREP in active generation path — only export ruled loft (makeLoft through polygon wires) downstream + import-side iges2stl. A spline was REMOVED for 94.95mm sheer error (recorded :646).
STL derived, never primary (hull_to_stl -> closed_mesh; Blender path derived via admissibility.surface_grid).

## SECTION/STATION MACHINERY — 12 discretisations on one kernel
1 hydro_arrays (exact 5-pt) | 2 section/_section_points memoised | 3 closed_mesh (own x-grid, LERPs CONTROL POINTS between 41 stations) | 4 panel_mesh (own zs, own mirror) | 5 offsets_grid | 6 admissibility.surface_grid (EXPLICIT SECOND COPY, hard-chine branch transcribed) | 7 blender/build_hull._build_arrays (THIRD topology/winding copy) | 8 export._station_wires (rebuilds own 161-station Hull) | 9 export.moulded_volume (deliberately independent cross-check) | 10 unroll (edges only) | 11 blender/metrics | 12 buildability._strips.
Section-area algebra written THREE times textually (geometry:384, :718, :757).

## FAIRNESS
REAL but UNCONSUMED: Hull.fairness (:790-837) discrete curvature-energy over arc-length-resampled sections; converges on fillet, diverges O(1/h) on knuckle (that IS the criterion, tested). No gate/objective/evaluator calls it. panel_twist_rate + min_bend_radius ARE gated. Longitudinal continuity: NONE — C1 breaks at 0.3L/0.7L/x_mb/warp-start; unroll measures 6mm refold step at exactly x_mb; nothing gates it.

## MESH/STL PATH
mesh_repair: proactive-only diagnose; repair refuses GENERATED origin; holes/non-manifold/self-intersections REPORTED not patched (retriangulation destroys chine row). stl_forensics: pure measurement (weld, aspect, edge table, normal jumps, feature edges =includedAngle 150, spatial-hash Moller-Trumbore with complete:False honesty). closed_mesh watertight w/ documented winding fix (397 flipped deck tris, -38.1% volume incident). SILENT downstream patcher: seakeeping.py:141 mesh.heal_mesh() (Capytaine) on panel_mesh output.

## TOLERANCES (hard-coded)
Absolute not length-scaled: _SEAM_TOL_M 1e-9; degenerate 1e-12/1e-9 m2; closed_mesh sliver 1e-10 (mirrored in blender); stem widen 5e-3->2e-3 m; refold bar 5 mm ABSOLUTE (unroll:82, gates:681) on LWL range 2.5-24 m; CHINE_OFFSETS_M absolute (stated deliberate); Moller-Trumbore eps 1e-12 DIMENSIONALLY MIXED (det m3 vs barycentric); STL nz 16/96; stl_resolution clamp [80,600].

## FAMILIES-SUPPORTED
hard chine YES | round bilge YES IN KERNEL but formlib registry says Expressible.NO (_M_ROUND_BILGE "there is no bilge radius" — CONTRADICTED by shipped kernel) | ~~multi-chine NO~~ **multi-chine YES since 2026-08-28** (Phase 5 / BUILD-PLAN PV-4: the topside is a KNUCKLE LIST — `Hull._topside_chain`, genes `ch2_z`/`ch2_y`, Gate MULTI-CHINE. k=0 recovers the legacy clip and k=1 the Phase-3 waterline knuckle expression for expression, so the pre-Phase-5 fences hold at exactly 0.0) | deep V PARTIAL (no aft deadrise variation) | transom YES / pointed stern NO | wave-piercer NO (LOA==LWL by construction) | bulb NO (absent entirely) | catamaran demihull: NO geometry (one Hull = one demihull; separation scalar only; no second shell/cross-structure) | tunnel NO (y(z) single-valued by construction) | SWATH NO. Registry census: 47 Expressible rows, only 3 YES.

## GAPS
- G0-P0 formlib registry stale vs shipped kernel: _M_ROUND_BILGE/_M_SECTION false since plate P2 across ~20 family rows; _M_SEPARATION false; unexpressible() reports a stale backlog; no test fences the claims.
- G0-P1 fairness has no consumer (P2's stated purpose half-delivered).
- G1-P1 no longitudinal fairness/continuity anywhere; C1 breaks unmonitored (6mm refold step at x_mb measured).
- ~~G1-P2 one scalar roundness/flare for whole hull (U-fwd/V-aft inexpressible).~~ **HALF-CLOSED 2026-08-28**: `rho(x)` (genes `rho_bow`/`rho_len`, Gate RHO-X) warps the bilge along the hull, so a U-forward / V-aft section family IS expressible. The FLARE half of the row stands — flare is still one scalar.
- G2-P1 surface topology transcribed 3x (closed_mesh / admissibility / blender) — winding-rule triplication already produced the 397-tri incident.
- G2-P2 panel_mesh un-welded/un-validated (duplicate y=0 column, no closedness check), only surface handed to a solver, via silent third-party heal.
- G8-P1 BEM body is design DWL not floated: seakeeping._body_from_hull wl defaults 0.0; production never passes wl; the TESTED path (test_end_to_end passes ev.wl) != production path.
- G8-P2 section-area quadratic in 3 textual copies.
- G8-P2 mixed-dimension eps in intersection kernel.
- G8-P3 absolute mm bars on 2.5-24 m range (refold 5mm, stem widen, seam tol).
- G8-P3 closed_mesh piecewise-linear in x at 41 knots regardless of nx; export fixes for STEP (161), CFD STL documents but does not fix.
- G10-P2 _polygon duplicates _signed_polygon w/ different eps; constant-x unroll control; Typology pins roundness=0 (round bilge unreachable via AST).
- G10-P3 stale docstrings describing deleted kernel (w**0.15 etc.) in unroll, hull_form_audit, stl_thirdparty_check, mesh_repair NURBS note.
- G10-P3 unfireable AST guard kept.
TODO/FIXME markers: ZERO in navalai/.

## UNKNOWNS
_halfbreadth_at np.interp with weakly-monotone z at beta_mid=0 (flat bottom) — implementation-defined, untested. _split_at_z degenerate fallback reachability. All docstring convergence tables taken on record, not reproduced. surface_grid fence coverage of chine_row clamp edges. Blender effectively orphaned on Linux node (mac path). Whether runs/ artefacts predate the -99.994% exporter defect.
