# Audit report: GRAMMAR / GENOME / TYPOLOGY / MISSION (agent B, 2026-08-14)

## TARGET-FLOW
**Cp and LCB are genome COLUMNS, not mission-derived targets.** limits.prismatic_target(fn) (:501-541) is the requirements->target function with ZERO production consumers (experiments comparison-only). Actual path: sample_valid -> rng.uniform(LOW,HIGH) -> check. Cp/lcb drawn uniformly; sac_exponents solves SAC to whatever was drawn. Only two mission->geometry couplings: optimize clamps LWL to lwl_hint±tol; evaluate floats to displacement target. Speed enters only downstream (scoring). LCB enforced post-hoc on floated hull; Cp has NO delivered-vs-target row in CONSTRAINT_NAMES.
**WHERE FORM-FOLLOWS-FUNCTION BREAKS: no requirements->targets stage.** MissionSpec carries no Cp/LCB/design-Fn/Cb. translate.requirements_from_mission emits 7 post-hoc graders reading a finished Evaluation. Design contract is a SCORECARD, not a specification. Pipeline is generate->filter, never synthesise-to-target.

## SOURCES OF TRUTH + DUPLICATES
Canonical grammar.PARAMS (16 genes, :191-272) with correct derivations (RCD scope, CP_GENE_BOUNDS, LCB band, formlib DRAWN ranges; optimize/generative/pipeline read LOW/HIGH).
LIVE DUPLICATES/DRIFT:
- D1 mission.lwl_hint_m (4.0,20.0) vs PARAMS LWL (2.5,24.0) — DRIFTED; clamps 22m brief to 20, 3m to 4; stale comment mission.py:63.
- D2 hull_ast.TYPOLOGY_RULES second bounds table (orphan).
- D3 arrangement.py:1229-1244 16 hard-coded params (self-declared dup of mid_params).
- D4 formlib.MISSION (12.0/0.8/0.6 CATAMARAN) vs MissionSpec defaults (6t 5kn MONOHULL) — two contradictory mission objects, nothing reconciles.
- D5 hull_form_audit TARGET_LBT third copy of 12/0.8/0.6.
- D6 evaluate.py:758-763 refusal message hard-wires MONOHULL band literals regardless of vessel.
- D7 stale comment crew (1,12) vs actual (1,250).
- D8 formlib._M_SEPARATION "total_resistance does not pass it" — NOW FALSE (evaluate:586 passes it); 3 families still carry the stale gap record.

## TYPOLOGY WIRING — ORPHAN MAP
hull_ast.{Typology,TYPOLOGY_RULES,type_check,infer_typology,fit_typology} imported ONLY by agents.py (run_plm — called by tests only). evaluate/optimize/pipeline/generative/latent/flywheel/ui import NOTHING from hull_ast. Dead node rules (x_mb<0.3 unfireable). Both Typology members pin roundness=0 — round-bilge kernel unreachable through AST path.
limits.HullRole DECLARED NOT REACHED: grammar.check(x, vessel=) exists with sourced DEMIHULL bands (Gate PV-B tested) but EVERY production call site passes no vessel -> hull_role()=MONOHULL always (evaluate:301,407,720; pipeline:599; flywheel; generative x6; latent x2; experiments; hull_form_audit).
**mission.SUPPORTED_HULL_COUNTS DOES NOT EXIST** — cited as load-bearing in grammar.py:102, limits.py:53, hydrostatics.py:244; real object is mission.HULL_COUNT + EVALUABLE_TOPOLOGIES.
EXECUTED TRACE: catamaran 12x0.8x0.6 -> grammar.check(x) refuses L/B 15 & B/T 1.33 as MONOHULL; grammar.check(x, vessel) -> only B/T 1.33 vs demihull floor 1.5 (L/B PASSES); evaluate(x,m) -> monohull refusal pair. **The project's own product target is refused as a monohull by the exact message grammar.py:42-51 was written to eliminate.**

## VESSEL-vs-HULL
VesselConfig exists and is partly wired (healthiest axis): topology/manning/separation; vessel_terms parallel-axis I_T; solve_to_displacement(vessel=); total_resistance(separation=); offset-load lever; manning rule-swap (R-GM->R-MHS).
NOT vessel-level: genome (one moulded surface, deliberate); L0 gate; bridge deck/cross-structure/wet deck (wet_deck_clearance_g zero callers); per-hull differential loading (n identical copies); bridge-deck weight/KG/solar (caveats declare); GZ(phi).

## DRONE
Naming + rule routing only. Manning.UNCREWED real: refuses whole stability assessment by name (honest, only drone-aware behaviour). Absent: payload object, endurance/mission-profile field, autonomy/sensors/comms windage.

## MULTIHULL HOOKS (live vs orphan)
LIVE: catamaran_interference; _separation_or_raise; n_theta_for_separation; total_resistance(separation=) <- evaluate:586; vessel_terms; b_wl_overall.
ORPHAN: wet_deck_clearance_g (NOBODY). NOT MODELLED: viscous form interference (declared). CITATIONS ONLY: Insel&Molland/NPL/Southampton. Wet-deck slamming explicitly not implemented.

## GAPS
- A P0 Demihull bands unreachable: grammar.check never receives vessel on any production path (evaluate:407,720; pipeline:599).
- B P0 Floated-state proportion re-check monohull-only for every vessel.
- C P0 No requirements->targets stage; prismatic_target zero consumers; contract is post-hoc grading.
- D P1 SUPPORTED_HULL_COUNTS ghost symbol cited as guarantee in 3 modules.
- E P1 hull_ast typology layer orphaned from production ladder.
- F P1 lwl_hint (4,20) vs LWL box (2.5,24) drift — silently rewrites user's stated length.
- G P1 No bridge-deck object (KG/solar/wet-deck absent; no constraint refuses).
- H P2 Two contradictory mission objects (formlib.MISSION vs MissionSpec).
- I P2 _M_SEPARATION stale-false gap record on 3 families.
- J P2 Drone naming only.
- K P3 Hard-coded reference-hull duplicates (arrangement, hull_form_audit).
- L P3 Stale comments (crew band, LWL ceiling).
- M P4 Dead AST node rules kept.

## UNKNOWNS
Repo gap taxonomy is G1-G8 (docs/GAP-REGISTER.md) — G0/G5/G6/G11 buckets unmapped there. Whether gap A is regression vs never-wired (bands landed 2026-08-14; no blame run). ui/server vessel dict decode likely AttributeError->L0 refusal (inferred, not executed). agents.run_plm reachability from shipped entrypoints unconfirmed. Delivered-Cp accuracy: PRISMATIC_TOLERANCE has no consumer.
