# Forensics — test batch: honesty/product/meta suites (16 files)

> **DATED SNAPSHOT — NOT A CURRENT STATE.** This file was measured at
> `HEAD 3527a59` (2026-08-18). That commit is now **174 commits**
> behind `master`. Read it as evidence of what was true THEN, never as
> an answer to "what is the state now" — CLAUDE.md routes that question
> to `python -m navalai.gates` and `python scripts/reconcile_gaps.py`.
> The 2026-08-11 incident this repo records is exactly this failure: four
> documents each asserted a subsystem did not exist, and all four were
> false because they were read as current.
Sub-agent batch report (parent test-forensics agent died at session
limit; this batch completed). HEAD 3527a59.

Per-file verdicts: gapfix_physics STRONG (1 mild self-referential sigma
assertion :475-476); gapfix_product STRONG (declared _stub synthetic
inputs); gaps STRONG (parallel-parser oracle); reconcile_gaps STRONG
(5bbffb7 negative control = strongest anti-tautology device); red_by_record
STRONG (blind spot: measurement-in-prose fence only matches N.N% — mm/N
figures pass); refdata ADEQUATE; limits_single_source STRONG (inverts
weight_budget to avoid compare-to-itself); manufacturing STRONG (records
its own cross-file staleness: unroll.py:864 + test_gaps.py:523 + Gate 6D
ledger prose still cite withdrawn 143.1/203.4mm figures — OPEN unowned
defect); multihull STRONG (production separation wiring PROVEN through
evaluate; borderline old-formula inertness pin :194-218); vessel_bands
STRONG (declared hand-built _Ev/_Hydro fixture — now redundant with
multihull's through-evaluate coverage, downgrade candidate); buildability
STRONG; constraints_honest STRONG (python -O subprocess attack); experiments
STRONG; policy STRONG (Saboteur comparator falsifiability); arrangement
STRONG (rule-coverage == __all__ fence); surrogate_honesty STRONG
(mocked-physics ratchet tests legitimate; real path covered piecewise).

Consolidated shortcut/bypass list: all physics monkeypatches are
restore-state saboteurs; hand-built Evaluations declared; NO pipeline
bypass found in this batch; no test asserts code against a copied
implementation without a declared wiring-pin purpose.

Sharpest findings:
1. Ledger prose staleness self-reported and unowned (manufacturing:817-821
   vs Gate 6D why_red prose) — owed withdrawal.
2. TWO HOMES, TWO SEMANTICS for the ITTC friction envelope:
   limits.friction_line_validity (strict, UNWIRED, tripwire
   test_vessel_bands:444-477) vs resistance.flow_regime.ittc57_ok
   (permissive, wired) — same physical invariant, different bars, held
   open only by a tripwire.
3. The committed surrogate mark REFUSES ITS OWN GENERATING SEED (seed 21,
   0.1721 vs 0.1413; 3/8 honest seeds false-refused) — recorded in
   docstrings, in no ledger row.
4. Anti-tautology engineering is systematic (4 named specimens).
5. Fragility concentrated in manufacturing ULP pins + 3 timing tests
   (all with re-measure instructions).
6. red_by_record prose fence N.N%-only blind spot.
