# Forensics — test batch: phase/kernel suites (14 files, ~9,600 lines)
HEAD 3527a59. Environment: capytaine IS installed here (test_phase2
collects 18).

Verdicts: all 14 STRONG (phase2 ADEQUATE-STRONG). Physics mocking
essentially absent; only adversarial poisoning controls + ratchet
isolation, each with an unmocked E2E counterpart (test_phase7:493-567).

## Sharpest findings
1. **DEAD ASSERTION** test_phase0.py:80 — `assert np.allclose(...) or
   True` — cannot fail.
2. **Gate 3's suite is deliberately red at HEAD with NO 'Gate 3' ledger
   entry** — test_phase3.py:169 (bar now MET at 0.1471 → asserts the
   shortfall EXISTS → fails-on-good-news) and :646 (+0.0513 vs +0.10,
   'EXPECTED TO FAIL'). The repo's own doctrine says these belong in
   typed RED rows (as Gate 6R correctly does).
3. test_phase2 module-level importorskip over-couples ~14 capytaine-free
   CFD-case tests to capytaine (D15 aggravation: only ~4 need BEM).
4. Holtrop branch-coverage tests transcription-tautological
   (test_holtrop.py:155-182 mirror the implementation's expressions).
5. Hand-built Evaluation in test_phase6.py:99-101 (fail-closed path
   never proven against a real refused evaluation's shape) — minor.
Meta-tests on source/AST are appropriate to the repo's declared defect
class; measured-pin + invariant + fired-rejection is the dominant idiom.
