# The mesh-scale CROSSOVER — real as an observation, REFUTED as a mechanism

**STATUS: EMPIRICAL PREDICTOR ONLY. Both proposed mechanisms are refuted.
PREDICTIVE != CAUSAL. Do not write this as a physical law, and do not
re-propose either mechanism below without new evidence that meets the bar
in §5.**

This file exists because the refutation previously lived only in commit
messages and in `docs/audit/STATUS.md`, which is a ROLLING channel. CLAUDE.md
routes "what was MEASURED, and what was refuted" to `docs/research/*.md`. A
refutation kept only in a rolling log gets re-proposed by the next session
that reads the prediction and not the test.

---

## 1. THE OBSERVATION — this part is real and survives

Increasing the background mesh density by 1.75% changes max skewness, and
**the SIGN of that change depends on how strained the baseline mesh already
is.** Sorted by arm A's baseline skewness, the deltas are monotone:

    baseline skew   3.279   4.592   5.803   10.757
    delta           +13%    +41%    -29%    -58%

The sign flips **once**, between 4.592 and 5.803, and never flips back.
Scale HELPS a strained mesh and HURTS a healthy one.

### 1a. It predicted BOTH directions out of sample, 6/6 (`d92d548`)
The prediction was filed BEFORE the runs — below ~4.6 scale makes it worse,
above ~5.8 better — and tested on two hull families it was not derived from:

    catamaran       A  3.974 -> C 5.710    predicted WORSE,  observed +44%
    wave-piercing   A 16.507 -> C 7.486    predicted BETTER, observed -55%

Six points across three families, every one on the correct side. This is the
campaign's strongest empirical result and it is NOT in question here.

**CAVEAT, stated at the time:** both new forms are 12-13.5 m, so hull FAMILY
is separated in this test but SIZE is not. A size confound is not excluded.

## 2. MECHANISM 1 — "tightest feature / background cell" — REFUTED BY COUNTEREXAMPLE

Proposed in `d92d548` as the likely cause: baseline skewness is only a
symptom, and the real driver is the ratio of a hull's tightest geometric
feature to its background cell — which is what scale changes.

This needed no CFD to test: `navalai/admissibility.py` already computes ten
such ratios. MEASURED at the A-arm scale across all six hulls (`57da605`):

    worse  = [0.88, 0.26, 0.62]
    better = [1.65, 1.07, 0.08]

**It does not separate.** The decisive counterexample is the hypothesis's own
strongest point: the **wave-piercing hull has by far the tightest feature in
the set** — 0.082 cells of bilge radius, twelve times tighter than anything
else — and scale HELPED it by 55%. A tightest-feature rule predicts the exact
opposite of the observation it was invented to explain.

## 3. MECHANISM 2 — `panel_twist_deg_per_m` — REFUTED BY PERMUTATION

One metric of fifteen DOES separate the two groups cleanly (gap between 7.35
and 10.80). It is **not reported as a finding**, because the permutation test
was run before belief rather than after it:

    metrics tested                        15
    hulls                                  6
    label splits (exact enumeration)      20
    observed separators                    1
    splits with >= 1 separator         14/20
    FAMILY-WISE p                      0.700
    mean separators under permutation   1.40

**Finding exactly one separator among fifteen is what chance produces** — the
expected count under the null is 1.40, and we found 1. Same instrument and
same answer as the h011 scan (p = 0.601).

## 4. WHAT THIS LEAVES

- The crossover is **REAL as an observation** and **UNEXPLAINED as a
  mechanism**, with both candidate explanations refuted — one by
  counterexample, one by permutation.
- It may be used as an **empirical predictor** (it earned that: 6/6
  out-of-sample). It may **not** be described as a physical law, and no
  operational rule may cite a mechanism for it.
- The conditional scale rule stays **unactionable**, and the REASON changed:
  no longer "we cannot predict baseline skewness pre-mesh" but **"we do not
  know what baseline skewness is a proxy FOR."**
- A threshold drawn at 5.2 on six points would be curve-fitting. The
  crossover interval is reported as the OPEN BAND (4.592, 5.803) and not as
  a number.

### 4a. A separate finding from the same runs, which is NOT about the crossover
The wave-piercing hull (plumb bow, zero flare) is the worst prism stack in the
set: 78.0% coverage, 5.43 of 7 layers unscaled. It meshes clean with no
backoff, but it is the nearest thing to a cliff outside h011, and the DERIVED
n=7 is what carries it.

## 5. THE BAR FOR RE-OPENING THIS

Per the operator's brief §11, no universal rule without a controlled
experiment, held-out validation, preferably multiple hull families, and
explicit failure analysis. Concretely, a new mechanism for the crossover must:

1. be stated BEFORE the data that tests it;
2. separate the six existing hulls, INCLUDING the wave-piercing
   counterexample that killed mechanism 1;
3. survive a permutation test at family-wise p < 0.05 — the same instrument
   that killed mechanism 2, not a weaker one;
4. break the SIZE confound noted in §1a, since all out-of-sample hulls to
   date are 12-13.5 m;
5. predict out of sample on a family not used to derive it.

Anything short of that is recorded here as UNDECIDABLE and stays out of the
prescription.
