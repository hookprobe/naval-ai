# Audit report: CFD-PREP + TIMING/ROBUSTNESS (agent E, 2026-08-14, static — no OpenFOAM invoked)

## MANIFEST (derived vs literal) — navalai/cfd/case.py
Derived: tank depth (max(1.0L,1.5*half_lambda) + assert), ny, g_air grading (capped 2.0), first layer t1 (ITTC), n_layers (capped _MAX_LAYERS=7, floor 3), hull shield radius, k_in/omega_in (flat-plate delta), writeInterval, Aref (halved if symmetric; refuses on failure), STL nx/nz (then clamped).
Literal: _DOMAIN_X=(-2.5,2.0):236, _DOMAIN_HALF_WIDTH_L=1.5:238, air height 0.25*lwl INLINE:2098, _Z_BANDS 0.09/0.09:222, _NX_BASE=57:264, _NZ_PER_NX=14/54:277 shares (6,2,2,4), _Z_EXPANSION=20.0:44, _TARGET_YPLUS=100.0:180, layer expansion 1.2:181, featureAngle 170:317, _HULL_REFINE=(4,5):203, _FS_BOX:155 fs_level=2:2228, _REFINE_ROUNDS=3:230, maxCo/maxAlphaCo/maxDeltaT 5/2/0.1 (LTS 10/5/1):909-912, deltaT 1|0.001:2306, rho/nu/g/sigma single-sourced:342-352, kOmegaSST, endTime default 40 OVERWRITTEN by _LTS_ITERATIONS=2000:323@2302, purgeWrite 3:574, locationInMesh -1.97L/0.137L/0.31L:2236.
**No CFD-manifest object exists**: ~25 module constants + local `dom` dict :2095-2244 + case.info text blob :2402-2501 + partial return dict. background_counts() :1986 is the one extracted rule (fidelity.py:58 imports it) — but fidelity.py:318 restates 4.5 and 2**2 (third copy of domain geometry).

## GEOMETRY-COUPLING
- Same Hull object, PARALLEL discretisation: closed_mesh lerps section control points between stations vs hydrostatics trapezoids exact areas -> documented always-negative ~0.19% loft bias no nz can close (:1376-1384). One Hull, two solids.
- THREE girth-resolution rules; CFD path uses stl_resolution->600x120, evaluate.l3_case_evidence identity check uses stl_girth_resolution bare default (16/96).
- KCS/external path separate and weaker: metres/WL-z0/x-range stated in prose only; enforced: closed-manifold; NOT enforced: units, scale, z-origin, x-origin, lwl<->extent (KCS extent 7.7165 vs Lpp 7.2786, handled for bow cut only). Scale/WL replayed from CHECKSUMS.json recipe; checked only by +/-% submerged-volume bar.
- Asymmetry: own hulls FATAL stl_watertight_report; imported get diagnose which counts winding_conflicts but never bars them.

## CFD-READY CHECKLIST — distributed, two languages
Generation-time FATALs: watertight, imported manifold, stack/hull_cell>1.2, n_layers<1, deep-water assert, layer_spec/blockMesh assert, Aref, bow-split refusals. WARN-only: last_ratio<0.12.
Run-time (run-case.sh): self-intersections recorded DELIBERATELY not a bar :151-196; "Surface is closed" FATAL; zero layer cells FATAL; checkMesh bars 0/5/20 FATAL; tet receipt; setFields FATAL.
Recorded in case.info ONLY. **navalai/evidence.py is NOT in the path — EvidenceGraph has zero CFD producers.** cells_per_wavelength computed :2401, written :2483, consumed by NOTHING; the >=20 bar lives in the parallel fidelity model that never sees a real case.

## TIMER-INVENTORY
- mesh_robustness.py: timeout=7200 :46 (dead at only call site, live for importers) | timeout=3600 :456 CLI per-hull | subprocess timeout :70-72 = ONLY wall-clock watchdog in CFD path | pkill -x reaper :80-81 no escalation/verify | foamDictionary subprocess :243-46 NO timeout (can hang classifier).
- run_campaign.sh: MAX=20 :19 (no rationale) | sleep 120 :92 (magic) | STALL>=2 -> exit 4 :80-87 (measured).
- run-case.sh: mpirun/interFoam UNBOUNDED :105,:497,:501 — no watchdog | resume branch :78-109 | FORCE/LAYERS_OPTIONAL/MESH_ONLY escapes.
- blender_foamcheck.py:43 timeout=3600 undocumented | blender/run.py 120/1800/3600.
- gates.py :847,:949 pytest subprocess NO timeout (historical CI-cancel cause) | CI timeout-minutes 50 x2 (measured 13m42+21m).
- case.py _LTS_ITERATIONS=2000 (a timer that is not a time) | writeInterval 10 x3 :609,:619,:703.
- post.py TAIL_FRAC .2 DRIFT_TOL .05 N_BATCHES 5 MIN_WINDOW 20 FLOW_THROUGH 1/5 | gate2m.py SETTLE_TOL=.05 documented mirror fenced by test_settled_drag.
- mesh_robustness classifiers min_deltaT<1e-12 / flow_time<1e-20 (measured).

## ROBUSTNESS-vs-COSMETIC
mesh_robustness OWNS measurement of the shipped pipeline (invokes run-case.sh; records both meshed + meshed_runner_bar; mechanism taxonomy). policy/ owns NOTHING in CFD. Ladder: search not prediction; default 0 rungs; back-off only on mesh refusal never solver failure; adopt best rung not last; run-case refuses cosmetic self-repair (diagnose(GENERATED) refuses to repair own hulls).
RESIDUAL CONCERN: ladder buys a passing mesh by changing the WALL MODEL (layer count); n_layers_used vs derived recorded but not gated — batch rate can improve without physics being comparable across hulls.

## GAP-MECHANISM
gaps.py append-only queue over data/evolution/gaps.jsonl, no reopen edge, Verified requires measurement note; seeded from docs/GAP-REGISTER.md. reconcile_gaps.py re-derives state from checkout predicates; NEEDS-HUMAN for unpredicatable. Enforced: reconciler tests (Gates SG/SR, 38 tests) + red-gate ledger. NOT enforced: queue file gitignored; scripts/reconcile_gaps.py invoked by NO workflow/hook/gate. Gap STATE advisory; gap MACHINERY enforced.

## GAPS
- G7.1 P0 import_winding_repaired receipt structurally always 'no' (diagnose never populates .applied; only repair() does) while comment claims "Winding is REPAIRED"; winding_conflicts counted, not gated — flipped-triangle import meshes with a false receipt. (case.py:1878-1905, mesh_repair.py:179-275)
- G7.2 P1 No CFD-manifest object; ~25 scattered constants; fidelity.py:318 third copy of 4.5/2^2.
- G7.3 P1 cells_per_wavelength gated nowhere (receipt only); the bar lives in the parallel fidelity model.
- G7.4 P2 No CFD receipt reaches evidence.py (zero producers).
- G7.5 P2 STL [80,600] clamp binds on EVERY hull — shipped STL resolution independent of lwl, 1.353x coarser than requested; recorded not barred.
- G7.6 P3 0.25*lwl air height inline literal.
- G8.1 P0 run-case.sh has NO timeout on interFoam/mpirun; hang bounded only by campaign MAX=20 x sleep 120.
- G8.2 P1 pkill -x kill path no escalation/verification.
- G8.3 P1 foamDictionary subprocess no timeout.
- G8.4 P2 two per-hull ceilings 7200/3600, neither measured.
- G8.5 P2 sleep 120 / MAX=20 / 3600 undocumented magic.
- G8.6 P3 writeInterval 10 declared three times.
- G11.1 P1 reconcile_gaps.py declared source of outstanding-state, invoked by no CI/hook — never refreshed automatically.
- G11.2 P2 queue gitignored — fresh clone reports nothing outstanding until --rebuild.
- G11.3 P2 EvidenceGraph exercised only by demo+tests; unsupported() empty by construction.

## UNKNOWNS
No OpenFOAM here — mesh/solve claims read from receipts/committed JSON, not re-measured. Layer-ladder drag-shift across batch untested. import_winding_repaired real-world relevance unverifiable (kcs.stl gitignored). pkill behaviour on Mac untestable statically. _Z_EXPANSION=20 optimality post-bbf1a47 unknown. Wall-clock distribution vs 3600 s not summarised.
