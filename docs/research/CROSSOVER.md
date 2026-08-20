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

## 6. THE EXECUTABLE HALF — `tests/test_evidence_promotion.py`

Sections 1-5 are a record, and a record is a thing a session can read past.
`635eb07` moved these refutations out of commit messages and `docs/audit/
STATUS.md` because **a refutation kept only in a rolling log gets re-proposed
by the next session that reads the prediction and not the test** — but moving
it to a durable file only changes WHERE it can be read past.

`tests/test_evidence_promotion.py` (Gate EP) is the half that cannot be read
past. It carries three fences, each proved in BOTH directions on a crafted
tree in `tmp_path` — docs/LESSONS.md defect class 3, *"a test showing a guard
accepts a good case proves nothing about rejection"*.

**Fence 1 — a receipt may not grow a mechanism.** `navalai/contract.py` labels
every prescribed number `DERIVED` / `EMPIRICAL` / `RECEIPT ONLY` / `INPUT`, and
`tests/test_contract.py` enforces that the label is present and spelled right.
Nothing enforced what the sentence AFTER the label says, and that is the cheap
edit: `"RECEIPT ONLY: measured on 4 points"` becomes `"RECEIPT ONLY: scale
helps BECAUSE the background cell ..."` with the label intact and every
existing check still green. The fence parses every string literal that OPENS
with a basis label (via AST, resolving the `f"{BASIS_RECEIPT}: ..."` form that
all of them actually use) and refuses causal vocabulary — *because, mechanism,
caused by, physical law, explains, explained by, the cause of, proves that, is
why* — inside an `EMPIRICAL` or `RECEIPT ONLY` one. `DERIVED` and `INPUT` are
exempt for opposite reasons: a derivation is SUPPOSED to name its equation,
and an input names a caller default.

MEASURED 2026-08-20 across `navalai/` and `scripts/`: **17 basis strings, one
hit.** The hit is `basis["n_layers"]`, which says the derived layer count "IS
the mesh-success mechanism ON THOSE HULLS". It is PINNED rather than exempted,
because it meets two of §5's clauses that the crossover mechanisms did not:
it was **pre-declared** (`docs/audit/H011-H012-ROOT-CAUSE.md` §7 wrote the
test before the data — *"if h011 and h012 mesh at n = 6 or 5 with 0
wrongly-oriented faces, the mechanism is the derived layer count"* — and the
measurement came back that way, mesh at n=6, fail at n=7 with 13/12
wrong-oriented faces), and it is **scoped to two hulls in the sentence
itself**, beside that document's own limit: *"No admissible-region boundary is
derivable from N=2."* A separate test asserts the scope tokens survive, so the
claim cannot be widened into a universal rule without failing — and any other
rewording fails too, by design, because a new hit has to be justified in front
of a reader.

The receipt is checked at RUNTIME as well as in source: a real
`mesh_prescription()` call's `basis` dict is scanned by the same rule, because
a static scan of source is a summary of what a caller receives and this
project's standing rule since 2026-08-20 is **check the artefact, not the
summary of it**.

**Fence 2 — cite the crossover with its standing, or do not cite it.** The
failure mode is not somebody writing *"the mechanism is X"*; it is somebody
quoting the 4.6-5.8 band in a new document with the caveat left behind, after
which the next reader has a rule with no standing attached. Every paragraph in
the live tree that mentions a crossover AND carries this crossover's own
coordinates (`4.6`, `5.8`, `4.592`, `5.803`, `baseline skew`, `baseline mesh
health` — the markers that separate it from the four unrelated "crossover"s in
this tree) must also carry one of *refuted, predictor, predictive, hypothesis,
receipt only, not a mechanism, unexplained, empirical*.

MEASURED, and the number moved while this section was being written, which
is itself the point. **Before the fence existed: 5 live citations, all 5
marked** — `navalai/contract.py`, `tests/test_contract.py`,
`docs/audit/MATH-CONSOLIDATION.md`, this file, and the fence's own comment
block, which FAILED on its first run and was fixed rather than exempted.
**After: 11, all 11 marked**, because the fence file, its gate row in
`navalai/gates.py` and this section are scanned like everything else. There is
no exemption for the scanner. Three further unmarked citations exist
in `docs/audit/STATUS.md` and **all three predate `57da605`**; `STATUS.md` and
`docs/GAP-REGISTER.md` are excluded as rolling/immutable historical channels,
named in the test with that reason. A fence that forced those to be edited
would be deleting a historical finding to make a test green — the very defect
this file exists to prevent, committed by the file itself. What makes the
history safe to read is that THIS document exists, which is why fence 3 is not
optional.

**Fence 3 — this record may not thin out.** The test asserts that §1-§5 still
carry: both refutation headings, both mechanisms by name (`tightest feature`,
`panel_twist_deg_per_m`), the wave-piercing counterexample, the family-wise
`0.700` and the `1.40` mean separators that make it legible, the standing
(`EMPIRICAL PREDICTOR ONLY`, `PREDICTIVE != CAUSAL`), **and the observation
itself** — the four deltas, their four baselines, the `6/6` and `d92d548`. The
mirror error is as bad as the original: a document that keeps the refutations
and loses the result would retract a predictor that earned 6/6 out of sample,
and a document that keeps the 6/6 and loses the refutations reads as an
endorsement. §5's five clauses are asserted individually, because without them
"REFUTED" is an opinion and the next plausible story reopens it cheaply.

The binding runs both ways: this section names the test, and the test asserts
this section names it — the same two-way binding `navalai/gates.py` keeps
between a gate row and its suite.

**What this fence does NOT do**, stated so nobody reads more into a green
gate: it is a vocabulary check over strings, not a proof that the code's
reasoning is sound. It cannot detect a causal claim made in numbers, in a
variable name, or in a comment that is not a basis string, and it does not
adjudicate whether a mechanism is TRUE — only whether an underivable receipt
is claiming to be one. §5 remains the bar for that, and it is a human's job.
