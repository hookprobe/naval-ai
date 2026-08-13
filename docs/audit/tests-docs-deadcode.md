# Audit report: TESTS / DOCS / DEAD CODE (agent G, 2026-08-14)

## TEST-MAP
51 files, 1209 collected. Gate-labelled suites (0,0B,0F,0G,0K,0X,1,1b,1C,1E,1H,1M,1P,2,2A,2B,2C,2F,2G,2H,2L,2P,2R,2T,3,4,4H,5,6,6M,6P,6R-mech,7,L,PV-B,R3,R4,S,SG,SR,V2.0,V2.1,V3.0 + stages B-G). Best-designed: test_end_to_end_flow (9-stage handoff agreement). Newest: test_multihull (27), test_vessel_bands (18). Thinnest: test_stageE (3).
HAZARDS:
- 16-number reference genome written THREE times (test_phase0.mid_params canonical, ~60 tests hang off it; arrangement.reference_hull_params self-declared dup; experiments.REFERENCE_DEMIHULL different boat same role); docstrings still say "fifteen".
- ~30 exact-float pins that will move under consolidation: test_multihull:328-330 (gm 0.6688/25.1147/54.3946 rel=1e-3), test_phase1:564 (REFERENCE_S 14.87905 rel=1e-6), test_holtrop abs=1e-6, test_cfd_reference_parity:326 (gci 7.8719), test_benchmark_geom:103,112,113 BARE == on floats.
- test_phase2 module-level importorskip(capytaine) deletes all 18 Gate-2 tests in CI while gate reports GREEN (gap D15, open).

## DOCS-BELIEFS
GAP-REGISTER.md (2026-08-05, ~110 rows, sections A-N): A ladder-not-a-ladder; B mission fidelity; C number-declared-twice; D gates-that-cannot-fail; E physics validity; F L2/L3; G manufacturing/rules; H uncertainty decoration; I learning spine; J docs/process; K/S/T/N BuildPlan2 coverage/retirements/fingerprint/prose-outlives-evidence.
HANDOFF 2026-08-13: declared tree uncommitted (now landed: 173cd00..f18fcba, tree clean); suite then 1117P/16S/5F; typology Pin fix "STILL A STOPGAP" (38.9% projection pass); experiments measured separation worth up to +59.7%; three owner decisions untaken (Gate 3E retirement, flywheel ratchet refusing 3/8 self-certified seeds, unaccounted mass 50.2%). Biggest unresolved: **6/40 feasibility, median GM 0.28 vs 0.45 floor — monohull GM floor applied to demihulls; "multihull hydrostatics are the largest single unlock and they do not exist."**

## DOC-CODE CONTRADICTIONS
1 Handoff stale-by-success (tree clean, 1209 tests, README table now matches; file instructs own deletion).
2 **BuildPlan2-FullVessel.md DOES NOT EXIST in tree** yet cited as normative by refdata/__init__, refdata/ergonomics, refdata/flotation, arrangement, test_refdata, test_arrangement (gap N6's defect class on the provenance spine itself).
3 **GATE-6R-REVIEW.md has 9 inline **confirmed markers vs review.py confirmed={R-CAT,R-DFH,R-OLH} only** (R-GM/R-PBM/R-TBM removed 2026-08-12) — reviewer packet disagrees with machine record; includes the row that says two values "cannot both be right".
4 review.py still lists ISO 12215-5 "edition not recorded — set this".
5 GAP-REGISTER G7 "ES-TRIN zero code" vs estrin.py 479 lines (with ZERO importers — letter closed, spirit not).
6 GAP-REGISTER A2 "nothing imports navalai.rules" vs evaluate.py:52-55 imports four symbols.
7 mid_params docstrings "fifteen" vs N_PARAMS==16.
8 README kernel-claims dated 2026-08-13, predates f18fcba.
9 Ledger review_by all future (inert ~3 wks); Gate 2M watermark literal string "NONE" — REDDER-than-recorded comparison undefined.

## IMPORT-GRAPH ORPHANS (zero non-test importers)
experiments.py 2674 LOC (has __main__; separation finding cannot reach product — HIGHEST-VALUE ORPHAN) | arrangement.py 1620 | rules/estrin.py 479 | agents.py 252 (run_plm tests-only) | dynamics.py 189 | waves.py 133 | refdata/flotation.py 227 (no rule consumes a flotation constant) | policy/dna.py 199 | blender/render_hull.py 169 (zero test refs). Near-orphans: surrogate, export, hull_ast, buildability, evidence, extrapolate, flywheel, compiler (1 importer each, several demo_apse-only).

## DUPLICATE-CANDIDATES
wetted surface x4 (geometry, holtrop, cfd/post stl_wetted_area, benchmarks/wigley) | ittc57_cf x2 + case inline | form_factor x2 + calibrate | STL read x3 / write x3+ | section builders x4 | displaced volume x3 (irreducibly disagreeing by convexity, measured) | hull_length_m x2 | GCI x2 partially consolidated | half-beam x3, to/from_vector x2-3, raw_feasibility x3, support_distance x2, sample_conditioned x3.

## TODO-INVENTORY
ZERO TODO/FIXME/XXX/HACK anywhere (house style: SUPERSEDED/RED BY RECORD/ledger rows instead). ~45 SUPERSEDED sites; self-declared dead branches kept with comments (mesh_robustness:366, gates:581, unroll:1236, gates:65 METAL/REVIEW unused-and-stated).

## refdata/ + rules/
RefValue enforces source+basis structurally (cannot exist without). basis in {standard-2003, approx, purchased}; nothing purchased yet (honest). Consumers: arrangement (E.* envelope) real; rules/ergonomics imports 3 symbols (reached only via translate.py:275 lazy); flotation NO rule consumer (walked only by refdata audit loop). iso12215+iso12217 wired into evaluate (tier R in constraint vector). estrin imported by nobody.

## UI
ui/server.py + index.html still track each other (5 endpoints, no orphans); imports live modules. BUT: no test file; the register's named escalation-free path (reaches no seakeeping/cfd/surrogate/rules); knows nothing of policy/arrangement/multihull/vessel bands — silently offers monohull-only physics under the new vessel model. Last touched 2026-08-11.

## GAPS
G9.1 P1 importorskip deletes Gate 2 in CI while GREEN (D15). G9.2 P1 3x reference genome. G9.3 P2 ~30 exact-float pins + bare == floats. G9.4 P2 stageE 3 tests; blender untested. G9.5 P3 ~150 prose-police tests are the cost of any doc restructure.
G10.1 P1 experiments.py orphan (separation +59.7% finding unreachable). G10.2 P1 estrin.py zero importers vs register "zero code". G10.3 P2 duplicate families (defect class 2 live). G10.4 P2 arrangement+flotation+policy/dna built-to-spec never wired. G10.5 P3 dynamics/waves/agents test-only. G10.6 P3 declared-dead branches in place.
G11.1 P0 GATE-6R-REVIEW contradicts review.py machine record. G11.2 P1 BuildPlan2-FullVessel.md missing yet normative for refdata spine. G11.3 P1 register rows A2/G7 factually wrong; reconciler has no check for either. G11.4 P2 handoff superseded, self-deletion owed. G11.5 P2 ledger 2M watermark "NONE" string. G11.6 P3 requirements.txt unpinned (J4). G11.7 P3 .DS_Store tracked; renders/downloads/runs in tree.
