# Forensics — scripts/files/artifacts/serialization/caches (§8/§9/§10/§21/§22)
Agent report, HEAD 3527a59.

## Scripts (27 + benchmarks 3 + ui 2 + hooks 2)
ALL import-clean against HEAD; ZERO delete candidates; every one classified
KEEP-PRODUCTION / KEEP-RESEARCH / KEEP-BENCHMARK / KEEP-DEBUG with call
evidence (reconcile_gaps/gate2m/make_case/post_gci/run_campaign/
mesh_robustness/make_baseline/fetch_benchmark_geom/iges2stl/
physical_form_report/tank_resonance/clean-runs/install-hooks =
production; demo_apse/hull_form_audit/stl_thirdparty/blender_* =
research; render_* / wigley_stl / yplus_wetted = debug CLIs with
incident-header provenance). gate2m.py source is PARSED AT RUNTIME by
pipeline.py:556 + cfd/post.py (settle_tolerance).

## Files (226 tracked)
~78 production, 55 tests, 4 gate-data, ~18 docs, 24 research, ~10
historical evidence (docs/audit correctly kept), 7 VALID_HISTORICAL
gate2u JSONs, 0 backup/_old/_v2/notebook/log hits.
**4 GENERATED-DEAD: renders/*.png tracked despite .gitignore:25,
GAP-REGISTER J6 'fixed', CLAUDE.md:787 claiming gitignored — the J6
guard (reconcile_gaps.py:1342) probes only the ignore pattern, blind to
leftovers. Action: git rm --cached renders/*.png + strengthen J6.**

## Old artifacts (§10)
- gate-ledger/baselines/CHECKSUMS/formcheck_baseline: VALID_CURRENT.
- Seven gate2u-*.json (2026-08-11/12): VALID_HISTORICAL — pre-rebuild
  15-gene geometry, NO geometry hash; admissibility bars calibrated on
  them but the tree KNOWS (CALIBRATION_GENOME_N_PARAMS=15 probe,
  auto-un-skip tests, ledger debt). Open action: one 16-gene campaign.
- data/navalai.sqlite3 (untracked local): 5x15-gene hulls labelled
  chine-v1; **db.py:84 defaults grammar_version="chine-v1" and NO caller
  ever passes it** (evaluate.py:1063,1394,1463 bare) → new 16-gene rows
  get the same label. Fail-closed today only BY ACCIDENT (shape gates +
  ragged-array ValueError). One-line fix: derive from grammar.N_PARAMS.

## Serialization (§22)
Strong: baselines.json (suite+targets fingerprints — best in repo),
gate-ledger (units+owner+verify), case.info (stl_sha256 vs CHECKSUMS; no
code version), formcheck baseline, blender receipts (tool versions),
evolution jsonl (tamper guard). WEAK: export .receipt.json and
DesignCertification JSON carry NO genome/hull-id/code version — "a
receipt that can't name the hull it certifies repeats the gate2u mistake
in miniature"; gate2u rows lack geometry hash (fenced for future rows);
EvidenceGraph no code version.

## Caches (§21)
sac_exponents lru (full-arg key, pure) OK; ui/server per-mission pareto
cache OK (2026-08-11 defect fixed; residual: generator model loaded once
per process, no model identity in key — harmless, no hot-swap path);
pipeline lru(1) parses script SOURCE (stale only if edited in-process —
minor). **No cross-process stale-cache path found.**

## Sharpest
S1 grammar_version decorative (LIVE; one-line fix). S2 gate2u void-but-
quarantined (action: 16-gene campaign when CFD node returns). S3
renders/ tracked-vs-ignored contradiction + blind J6 guard. S4 anonymous
certification/export receipts. S5 scripts clean. S6 .claude settings
deny-rules point at the Mac paths (inert here).
