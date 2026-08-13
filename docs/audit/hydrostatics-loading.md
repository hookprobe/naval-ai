# Audit report: HYDROSTATICS / LOADING / WEIGHTS / ENERGY (agent C, 2026-08-14)

## IMPLEMENTATIONS + CALLERS — SEVEN independent volume/wetted/waterplane computations
A AUTHORITATIVE(L1) hydrostatics.solve :249-329 (vol,disp,LCB,KB,BM,BM_L,Awp,LCF,I_T,Cb,Cp,wetted,freeboard) <- evaluate:540 via solve_to_displacement:466; experiments:170; export:327; stl_thirdparty_check; tests. Well-guarded: bit-exact monohull reduction, interpolated waterline ends, converged-or-refuse bisection.
B section kernel geometry.py hydro_arrays:731/section_area:705/wetted_surface:839 <- A; energy.shell_area_m2; engineer; buildability.
C 2nd form-coefficient integrator Hull.form_coefficients geometry:739-773 (vol,Cp,Cm,Cwp,lcb_pct,lcf_pct; 401-pt resample, DESIGN WL only) <- plate checks/formlib; NOT evaluate.
D 3rd volume integrator export._displaced_volume_of/moulded_volume_m3 :178-293 — deliberately adversarial cross-check vs A.
E STL divergence-theorem hydrostatics cfd/post.py:885-1005 (Awp,LCF,I_L,vol,LCB/TCB/VCB) <- cfd.case.motion_from_geometry; evaluate.l3_case_evidence:1095; post.stl_wetted_area.
F CFD floating-body mass/stiffness sixdof_properties cfd/case.py:355-401.
G Holtrop regression wetted surface + Cb (parametric) — envelope reporting only.
Verdict: A is single L1 truth; E/F a genuinely independent L3 hydrostatics stack with different density and mass model.

## UNITS/FRAMES
Frame declared once weights.py:19-22 (x=0 transom +fwd; z=0 design WL +up; y +stbd). KB/KG above-keel; only conversion weights.MassAggregate.vcg_above_keel (+t_design); t_design re-derived hydrostatics:274 AND evaluate:462. draft = t_design+wl. Metres throughout; mm only refdata/reporting, converted in one place each.
Densities: geometry RHO_WATER=1000 (L1 default) | cfd/case _RHO_WATER=998.8 (all L3) | holtrop 1025 | similitude 999/1026. Bare 1000.0 RE-TYPED as default arg in 12 signatures (resistance x7, seakeeping x5) instead of importing geometry.RHO_WATER.
g: 9.80665 x3 modules + cfd/case 9.81 + formlib + hull_form_audit. Four declarations two values; case.py:326-341 documents the anti-pattern and 9.81 survives it.
Silent-divergence: L1 1000 vs L3 998.8 (0.12%) no reconciliation term; volume-compare sidesteps. similitude NOT in L1 path (extrapolate/planner/demo_apse only) — model-scale mixing contained, not solved.

## TRIM — LEVEL-TRIM ONLY
solve_to_displacement bisects HORIZONTAL plane on displacement alone; no trim DOF, no LCB<->LCG iteration. Longitudinal balance = single linearised post-hoc estimate weights.trim_angle_deg:129-153, checked vs TRIM_LIMIT_DEG=2.0. **Every reported hydrostatic is the UPRIGHT ZERO-TRIM value even when trim check reports 5.7 deg.** Undefined GM_L handled honestly (INFEASIBLE_G).
LCF computed+stored, only consumer parallel-axis I_L; NO MCT/TPC/sinkage-about-LCF; second independent lcf_pct at geometry:770 read by nothing in ladder.
Heel linear-only (atan(TCG/GM); iso12217 sin phi). **No GZ(phi) curve anywhere** (explicitly refused for multihull, silently absent for monohull — R-GM origin-slope proxy is the only stability bar).

## LOADING — ONE CONDITION, UNNAMED
MissionSpec.displacement_target_kg single scalar; no lightship/design/max/departure-arrival; no condition object.
Mass sites: energy.weight_budget (5 buckets + composite KG) || energy.weight_items (SAME buckets as positioned MassItems) — deliberate live duplicate, evaluate calls BOTH (:506-508); provenance row :954 records wb.kg_above_keel as the KG behind a GM actually computed from agg.vcg_above_keel — agree today only because 'unaccounted' filler sits at aggregate's own centre; **any tier-E/F item entering makes the DB row misreport KG**.
ORPHANS: arrangement.mass_items/supersede_outfit zero production callers (tier E masses cannot reach the float). refdata/flotation.py unimported outside its package (tier F dead). MassItem.volume_m3/material never read; no production item sets slack=True -> FSC identically 0.
Asymmetric loading representable in mass model, NOT in float (upright symmetric solve). Multihull loading symmetric-by-construction (n identical copies, one total); per-demihull split unrepresentable. Bridge deck contributes no mass/KG/solar (stated).

## COUPLING
L1 coherent: one state weights->float->stability->resistance(floated B/T, gap E7 fixed)->energy; hull count/separation resolved once in vessel_terms for both stability and interference. optimize/generative consume same state (call evaluate, no recompute). agents forwards ev.wl to engineer.
**CFD DOES NOT consume the floated state (the one real break):** motion_from_geometry derives mass=rho*V_STL, LCG=LCB, VCG=VCB-or-CLI, rho 998.8, design WL z=0; never sees agg.total_kg/lcg/vcg or wl. CFD hull = neutrally-ballasted geometric boat; L1 = weight-model boat at different draft. case.py:442-453 warns (19% KG error on KCS). l3_case_evidence compares volume at wl=0 explicitly NOT floated — identity check cannot detect the mismatch it sits downstream of. seakeeping correctly reuses ev.hydro.

## GAPS
- G3-1 P0 No trim equilibrium (iterate (T,theta) on sum Fz=0 ^ sum My=0 needed).
- G3-2 P0 No GZ(phi) anywhere; R-GM origin-slope proxy is the only stability bar.
- G3-3 P1 LCF unconsumed; no MCT/TPC; duplicate lcf_pct.
- G3-4 P2 Freeboard flat 0.25 m; no downflooding-angle check despite iso12217 helper existing.
- G3-5 P2 Two-hull symmetry hard-coded; trimaran refused by name.
- G0-1 P1 Four densities, no L1<->L3 conversion policy.
- G0-2 P1 rho=1000.0 retyped in 12 signatures (unguarded, contrast test_limits_single_source).
- G0-3 P2 g 9.80665 x3 vs 9.81 cfd.
- G0-4 P3 t_design derived twice.
- G8-1 P0 No loading conditions.
- G8-2 P0 Tier E dead weight: arrangement masses cannot reach the float (the exact promise weights.py:3-13 makes).
- G8-3 P1 Tier F dead: refdata/flotation unimported; FSC identically 0.
- G8-4 P1 CFD mass model disjoint from L1 weight model.
- G8-5 P2 Duplicate mass representation + provenance row cites wrong KG source.
- G8-6 P2 'unaccounted' filler up to ~54% of displacement at 6 t mission, at aggregate centre 50% sigma.
- G8-7 P3 LCG/VCG_FRACTION undeclared-source fractions drive trim/GM verdicts.

## UNKNOWNS
tests/test_cfd_gap_closure.py cited as guard at cfd/case.py:339 — NOT FOUND in tests/ (parity list lives in test_cfd_reference_parity:530). ui/server.py re-derivation not inspected. experiments floated-wl reuse untraced. GAP-REGISTER ID collision ('G3' already = BOM). MissionSpec.payload_kg vs EnergySpec.payload_kg reconciliation untraced.
