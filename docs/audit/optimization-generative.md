# Audit report: OPTIMIZATION / GENERATIVE / SURROGATE / ORCHESTRATION (agent F, 2026-08-14, @f18fcba)

## OPTIMIZER-VISIBILITY
Two Problem classes (HullProblem :25, LatentHullProblem :129) with VERBATIM-duplicated objective/constraint bodies. Objectives (min): (wh_per_nm, build_area, |gm - gm_mid|). Constraints: evaluate.CONSTRAINT_NAMES (freeboard, gm, bend_radius, trim, list, lcb, proportions, rules) + compiled-policy rows. Latent problem gets NO box (z ±2.5sigma; policy row only).
**THREE LEAKS — full ladder does NOT gate scoring:**
1. ev.ok NEVER consulted (admit test = tier!=L0 & hydro & energy). Three violation classes deliberately outside G matrix (early, multihull_stability_refusal, manning_refusals) -> ok=False designs score fitness and can win the front.
2. multihull_stability_refusal returns "NO CRITERION IS IMPLEMENTED" for every n_hulls>1 -> on a catamaran mission 100% of the front is ok=False, invisible to NSGA-II.
3. res.valid=False (out-of-envelope Michell) still populates energy -> invalid-badge Wh/NM scored as objective 1.
NOT in loop at all: buildability (zero evaluate/optimize callers), CFD-admissibility (stl_forensics/blender/tests only), refold/developability (engineer only). **Unmeshable/unbuildable geometry earns fitness.** Delivered-state proportions ARE re-checked.
Degeneracy: experiments exp5 swept 898 hulls x 10 objectives — every RATIO inflates, no ABSOLUTE does; all three live objectives absolute (good). Residual defects: build_area inline copy of shell_area_m2 MISSING n_hulls factor (catamaran build objective prices one demihull, mass model charges two); gm_mid uses design chine beam + MONOHULL gm_floor on multihulls (steers toward inapplicable band); ParetoResult.F docstring stale (-gm).

## GENOME-CONSISTENCY
Canonical grammar.PARAMS 16-D: optimize/generative/latent/flywheel/pipeline YES.
**surrogate NO** — never imports grammar; normalises on training draw's own min/max; no width check (legacy 15-vector fits silently; is_ood radius incomparable across retrains; the admissibility.calibration_is_current pattern NOT applied).
**db NO** — grammar_version="chine-v1" hardcoded, decoupled from N_PARAMS; live sqlite holds 5 hulls ALL 15-param ALL "chine-v1"; get_params returns vectors grammar.check refuses; training_matrix would hand flywheel ragged X.
p_bow/p_stern: no live navalai reader. LIVE STALE: scripts/stl_thirdparty_check.py :525,689,691,1112,1170 rebuilds plan-form from them (forensic reimplementation of deleted geometry). Stale prose: unroll :349,560,698.

## PIPELINE-WIRING
pipeline.py = lifecycle state machine (computes nothing); planner.py = Bayesian experimental design (which EXPERIMENT next, not which TARGETS). Real requirements object = translate.requirements_from_mission + grade() = POST-HOC checklist (agents + demo_mission only). What reaches search from mission: lwl_hint, displacement_target, design_category. Everything else aspirational.
Pipeline class/check_*: ZERO non-test callers; data/evolution/archive.jsonl DOES NOT EXIST — spine never driven. planner: demo_apse + tests only (whole fidelity/similitude/evidence/extrapolate subtree same single demo caller).

## AGENTS
4 async agents, typed audit trail; consumers = test_stageC ONLY. Sole consumer of hull_ast. Fitness = wh_per_nm ALONE — disagrees with optimize's 3-vector; two search paths rank differently, no reconciliation.

## GATES-AUDIT
57 gates; 51 pytest-backed; 6 typed-RED ledger gates (4F,3E,2M,2U,6R,6D).
**P0: ledger regression rule NOT IMPLEMENTED** — judge_red checks presence/review_by only; never re-measures, never compares watermark; better_is read by no production code. The regression signal the ledger design rests on is a formatted string.
**P0: Gate 2U watermark (27.8% solve, N=18) from the campaign admissibility.py declares VOID (15->16 genome)**; three incomparable metrics under one row (solve vs mesh rates; cap7-mesh 64% N=25, backoff 100% N=25); why_red admits re-measurement owed; nothing fails on it.
P1: Gate 6D watermark moved 66.2->124.1 under one row — human-edited; judge_red would not have noticed the 1.9x regression. P2: 2U scope claims 200-hull batch, evidence N=18-25. P3: Gate 1b GREEN does not cover the ev.ok leak.

## ORPHANS
pipeline.py (Pipeline/Genome/check_*/transition) ORPHAN (only JsonlLog + settle_tolerance escape) | agents.py ORPHAN | planner.py ORPHAN (demo_apse) | hull_ast orphan-by-transitivity | experiments.py consumer-orphan | buildability decision-path-orphan | evidence/extrapolate demo-only. latent LIVE via generative.PPCAGenerator.

## PROVENANCE — three parallel mechanisms, none aware of others
1. db.Provenance (SQLite; written only when caller passes provenance=; optimize NEVER passes it — nothing the optimizer evaluates is recorded). 2. pipeline.JsonlLog (only gaps.jsonl has data). 3. experiments.ExperimentRecord (in-memory, no persistence). canonical()/hull_id correct (E9 fenced).

## GAPS
G6-01 P0 ev.ok never checked -> invalid designs earn fitness. G6-02 P0 multihull front 100% ok=False scores normally. G0-01 P0 ledger regression rule unimplemented. G0-02 P0 Gate 2U void calibration + incomparable metrics. G9-01 P1 surrogate ignores grammar box. G9-02 P1 db version decoupled (15/16 mixing). G6-03 P1 build_area copy + missing n_hulls. G6-04 P1 gm_mid monohull floor on multihulls. G6-05 P1 buildability/meshability/refold absent from scoring. G10-01 P1 MDO spine never driven. G10-02 P2 two disagreeing search paths. G10-03 P2 requirements post-hoc not driver. G9-03 P2 stl_thirdparty_check p_bow/p_stern. G0-03 P2 2U scope/evidence mismatch. G10-04 P2 three provenance mechanisms; optimizer writes none. G6-06 P3 duplicated _evaluate bodies. G6-07 P3 stale docstring. G9-04 P4 unroll stale comments.

## UNKNOWNS
ui pareto_front ever non-empty under compiled policy; db.training_matrix behaviour on mixed widths; current-genome 2U rate at N>=200; LatentHullProblem reachability outside tests; policy/ internals unaudited.
