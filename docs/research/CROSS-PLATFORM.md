# CROSS-PLATFORM VALIDATION — what "the same answer" means on two machines

**STATUS: this is the CONTRACT, and it is derived from measurements taken on
both machines. It replaces an assumption nobody had written down — that the
two boxes agree bitwise — which was false, and was found to be false twice
independently before anyone looked for it.**

There is no "BIT-EXACT" claim anywhere in this document, and one must not be
restored. `1e16b15` removed the last of them from the two guards that carried
it; the phrase is recoverable only as a same-machine statement, which §3 says
how to write.

| Question | Ask |
|---|---|
| are the two machines still saying the same thing? | `python3 scripts/parity.py --emit` on each, then `--compare` (Gate XP, `tests/test_parity.py`) |
| did a number in the resistance tier move? | `tests/test_resistance.py::test_resistance_is_bit_identical_to_the_golden` — **on x86-64**; see §4 |
| what class does a quantity belong to? | §2, §3, §4 of this file |
| what is still unresolved? | §7 — and it is not short |

---

## 1. THE TWO MACHINES, AND THE THREE MEASUREMENTS THAT FORCED THIS FILE

    fortress001   Intel N100, 4 cores, 6 W, x86-64, Linux   dev + full suite + gate ladder
    the Mac       Apple M5 Pro, 15 cores, 24 GB, arm64, Darwin   simulation node (OpenFOAM, training)

They are not a redundant pair. They are a heterogeneous pair, and that is a
deliberate product choice — the N100 is one of HookProbe OS's own target
platforms — so cross-platform agreement is a requirement, not a convenience.

**(a) A geometry equality fence passed on x86-64 and failed on arm64, by one
ulp.** `tests/test_geometry_kernel.py::test_the_batched_section_machinery_is_`
`the_per_station_definition` asserts that the batched
`geometry._sections_batch` is a transcription of `sample_section`, not a second
shape function. It compared with `np.array_equal`. MEASURED 2026-08-20 on the
Mac: `section rho=0.35 n=41 i=0: 62 of 514 elements differ, worst |diff|
1.110e-16`. Same source, same inputs; a different SIMD width and FMA schedule
reassociate the sum, and IEEE-754 permits every bit of it.

The conclusion recorded in `1e16b15` is the whole reason this file exists:
**exact equality was a property of ONE PLATFORM mistaken for a property of the
code.** Nothing was wrong with the batching. What was wrong was the contract.

**(b) `stl_sha256` is not portable between the two machines.** The h011/h012
investigation reached the same fact from the other end, weeks earlier and
independently: over one hull's **3,467,472 printed `%.6e` numbers, 13 sit
within 1e-12 relative of a rounding boundary** (0 at 1e-13, 4408 at 1e-9). The
genome reproduces exactly; the ASCII STL the emitter prints from it does not,
so the digest over that file moves. `docs/audit/H011-H012-ROOT-CAUSE.md` §7.1
carries the detail.

**(c) The resistance golden moves on arm64, and this document measures by how
much.** `tests/test_resistance.py` pins 4906 keys as `float.hex()` and SHA-256
over raw IEEE bytes, and declares `GOLDEN_ARCH = "x86_64"` so a mismatch
reports **PLATFORM**, not **REGRESSION**, off that architecture. MEASURED on
the Mac, re-run at `81fbf6b` and identical to the earlier `b7a91ef` run:

    total golden keys                    4906
    keys that move on arm64               530   (10.8%)
      of which SHA-256 digests            119   (a digest moves if any float under it does)
      of which floats                     411

    relative difference over those 411 floats
      min                             1.132e-16
      median                          2.990e-16
      max                             5.656e-13   (a spectrum tail — see §4)
      max excluding spectrum tails    3.380e-14
      max over PHYSICAL quantities    1.083e-15   (rw, cw, total, uncertainty, ittc57_cf)
      number exceeding parity's 1e-12 bar     0

The headline example the brief carries is one row of that table:
`free_wave_spectrum.cat[ref_r000@fn0.280,s13.0000].spectrum.first`, golden
`0x1.cd2dd93a62d1bp+8` -> got `0x1.cd2dd93a62d16p+8` — **5 ulps, 6.163e-16
relative.**

---

## 2. THE THREE CLASSES

A class is a property of a **(quantity, comparison) pair**, never of a quantity
on its own. `Hull.section()` is bit-identical to `sample_section` on x86-64 and
is not on arm64; the quantity did not change class, the comparison did. Every
claim below therefore names both the quantity and the scope it holds over.

### CLASS 1 — BIT-IDENTICAL
**Definition.** Equal in every bit of the IEEE-754 representation; comparable
with `float.hex()`, `np.array_equal` on a `uint64` view, or a SHA-256 over raw
bytes. **Scope: ONE machine, one toolchain.** Nothing in this repository is
bit-identical across the two machines, and nothing may claim to be.

**What belongs here, and why each one earns the strictness:**

| Quantity | The comparison it is bit-identical under |
|---|---|
| `resistance.michell_rw` and everything under it (4906 golden keys) | this machine today vs this machine before an optimisation. `michell_rw` feeds pinned figures across the repository, so a one-ulp move is a change, not a rounding error |
| `_free_wave_vals` vs the per-theta reference loop it replaced | two code paths on one machine — the only way to say "the rewrite is the same computation" rather than "the rewrite agrees with itself" |
| `_free_wave_vals` across `_FREE_WAVE_CHUNK_BYTES` | the chunking is a MEMORY bound; if the answer depended on it, it would be a quadrature knob wearing a memory knob's name |
| `geometry._sections_batch` vs `sample_section` | **DEMOTED to class 2 by measurement (a); see below** |
| `stl_sha256` | a **same-machine** identity for a written STL. Perfect at that job, and used for nothing else |
| the ungoverned/governed physics equality (`navalai/policy/`) | "delete the constitution and every physics result must be bit-identical" — one machine, one run, no arithmetic difference to permit |

The last row is the shape of a legitimate bit-exactness claim and is worth
naming: it compares **two code paths on one machine in one process**, where
IEEE permits nothing. That is the only setting in which "bit-exact" is a claim
about the code rather than about a box.

**`genome_sha256` is the one identity that is portable BY CONSTRUCTION** —
`hashlib.sha256` over `np.asarray(params, float).tobytes()` in declared gene
order, with no arithmetic between the input and the digest. It was added
(`navalai/contract.py`) precisely because `stl_sha256` is not. Its portability
is a construction argument and **is not currently measured** — see §7.

### CLASS 2 — NUMERICALLY EQUIVALENT
**Definition.** Different bits, agreeing to a stated tolerance whose value is
**derived from two anchors**, not chosen. **Scope: across machines, and across
two runs of an iterative solve on one machine.**

This project uses three tolerances, and each one is bracketed rather than
picked. That distinction is the whole of the honesty here: a tolerance chosen
because it makes both machines green is a tolerance that will absorb the next
real defect silently.

**2a. `PLATFORM_REL_TOL = 1e-12` — `scripts/parity.py`, the cross-machine bar.**
The argument is that the band around it is EMPTY in every measurement taken:

    BELOW  largest cross-architecture disagreement measured   see the table in §1
    ABOVE  smallest real defect this project ever caught      0.5 relative
           (`forceCoeffs` wrong by exactly 2x on every symmetric run)

`tests/test_parity.py::test_the_tolerance_band_is_empty_between_its_two_anchors`
asserts both anchors so that moving the bar has to argue with them, and two
sibling tests prove the classifier in both directions: nudge EVERY float by one
ulp and the verdict must stay `PARITY: OK`; plant a 2x error underneath that
same ulp noise and it must be NAMED.

**The lower anchor is weaker than `parity.py`'s comment states, and this
document is where that is recorded.** That comment says the largest measured
cross-architecture disagreement is one ulp, `1.110e-16`, "four orders inside
this bar". MEASURED here on 411 moved golden floats: the largest is
**5.656e-13**, which is **1.77x** inside the bar, not four orders. Restricted
to physically meaningful quantities it is **1.083e-15**, i.e. ~3 orders. The
bar itself stands — **0 of 411 exceed it** — but the margin is a function of
the quantity, and the sentence claiming a uniform four orders is understated by
about 3.4 orders. `parity.py` is not this file's to edit; the correction is
recorded here and reported.

Mitigating, and measured rather than assumed: `parity.py`'s receipt flattens
`HullEvaluation.to_dict()`, which contains **no free-wave spectrum**, so the
5.656e-13 tails are not among the numbers it actually compares. The narrow
margin is a property of the GOLDEN's comparison, not of parity's — today. It
would become parity's the moment a spectrum-like quantity entered the receipt.

**2b. `_BATCH_ULP_SLACK = 4` (of the ARRAY SCALE) —
`tests/test_geometry_kernel.py`, the batch-vs-definition fence.** The fix for
measurement (a). Judged against the array's largest term, not each element's
own ulp, because reassociation accumulates rounding proportional to the LARGEST
term summed: a 7 mm coordinate carries absolute error inherited from the big
ones, and asking it to be as exact as if computed alone is not what the
arithmetic did. Anchored the same way — 4 ulps of scale is **4.44e-16 m**
against a **worst observed rounding of 2.43e-17 m (18x headroom)**, while still
catching a **1e-9 relative** algebra change (7.0e-10 m). `sample_section`
remains THE DEFINITION; the slack says only how the comparison is read.

**2c. `_TOL_BY_KEY = 2e-3` for attitude-derived quantities — `trim`, `list`,
`freeboard_min`, `lcb_pct`, `gm`, `draft`.** These are not platform noise at
all: `solve_equilibrium` converges to `tol = 1e-3`, so its own convergence
dominates any architectural difference. MEASURED: two categories of the same
hull differ by **five microns** on downflooding height (0.8836405 vs 0.8836354
m, 5.7e-6 relative) purely because two equilibrium attitudes were solved
separately. Comparing those at 1e-12 across machines would report a solver's
convergence as a cross-machine regression. **A quantity that legitimately
accumulates error is compared at ITS OWN tolerance, and the tolerance is the
solver's, not a fitted one.**

### CLASS 3 — ENGINEERING EQUIVALENT
**Definition.** The two machines reach the same ENGINEERING CONCLUSION about
the same design, while the underlying numbers are not expected to agree to any
float tolerance at all — because the computation is not deterministic between
them in the first place (different core counts, different decompositions,
different iteration counts to the same residual).

**Everything downstream of a mesh is in this class.** It is the largest class
and the one most likely to be mis-stated, because its quantities are printed
with four significant figures and look like class 2.

| Quantity | The bar it is judged against, and who owns it |
|---|---|
| C_T from an OpenFOAM solve | KRISO EFD **3.711e-3** at Fn 0.26 and the Tokyo-2015 **7-group scatter band 3.620-3.733e-3** — `scripts/gate2m.py`, which REFUSES a verdict it cannot support |
| grid convergence | Roache GCI <= 5%, over a systematically refined FAMILY with measured `r` — `navalai.cfd.post.gci`, ONE implementation |
| stationarity | drift <= 5% over the last fifth **and** >= 1.0 flow-throughs; anything settled under 5.0 prints `UNDER-RUN` |
| mesh admissibility | 0 zero-volume cells, <= 5 incorrectly-oriented faces, max skewness < 20 — `navalai/cfd/run-case.sh`, bars calibrated against cases measured to solve and to die |
| Gate 2U unattended-mesh rate | a POPULATION statistic over a declared `(arity, seed)` split — Gate 2Y |
| layer coverage, cells-per-wavelength, y+ band | receipts in `case.info`, compared as envelopes |

An OpenFOAM run decomposed over 10 ranks is not bit-reproducible **against
itself** at a different rank count, let alone across architectures. Asking for
class 1 or class 2 here is a category error, and the honest form of a
cross-machine claim about a solve is: *the same case, run on both, lands inside
the same acceptance band, and the two verdicts agree.*

---

## 3. THE RULE THAT CUTS ACROSS ALL THREE: A VERDICT GETS NO TOLERANCE

Numbers get a tolerance. **Verdicts do not.** `parity.py` compares
`status | hull_verdict | model_verdict | mesh_verdict | result_verdict |
fidelity_tier | regimes | in_domain` as STRINGS, at zero tolerance, and
`tests/test_parity.py::test_a_disagreeing_VERDICT_is_never_excused_by_tolerance`
is the clause that says so. Two machines that disagree about `REFUSED` versus
`MARGINAL` have a defect no rounding can explain — and a tolerance that could
excuse it would be excusing the one thing a user acts on.

This is the cross-machine form of the rule `navalai/gates.py` already enforces
in-machine: a status is a typed enum, and a missed clause is RED BY RECORD, not
prose in a scope.

**How to write a bit-exactness claim so it stays true.** Say the machine.
`GOLDEN_ARCH = "x86_64"` is the pattern: the claim is scoped in the code, and
the failure message says which of two very different things a mismatch means.
A claim written without its machine is not a strong claim, it is an unscoped
one, and it will be falsified by the other box rather than by a bug.

---

## 4. THE GOLDEN, AND WHAT IT CANNOT DO TODAY

`test_resistance_is_bit_identical_to_the_golden` is a class-1 fence recorded on
fortress001. On the Mac it reports PLATFORM and fails, every time, by
construction — 530 of 4906 keys. That is correct behaviour and it is also a
hole: **there is no arm64 golden, so an arm64-only regression in the resistance
tier is currently invisible.** The failure is indistinguishable from the
expected platform delta, which is exactly the state the PLATFORM/REGRESSION
message was written to make legible rather than to fix.

The spectrum tails deserve their own note, because they are where a naive
relative comparison would first cry wolf. `free_wave_spectrum` spans
**1.656e+08 down to 1.122e-177** within a single array. The `.last` keys are
cancelled/underflowed tails: 82 of them move, median 2.139e-15 and max
5.656e-13 relative, while the same arrays' `.first` keys move by at most
6.468e-15. Relative-to-own-value is the wrong denominator for a tail; relative
to the array's scale, every one of them is ~1 ulp — the same denominator
argument that `_BATCH_ULP_SLACK` settles for the geometry kernel (§2b). The
golden sidesteps it by demanding exact equality on one architecture, which is
sound; a cross-machine comparator that included spectra would have to make the
choice explicitly.

---

## 5. HOW TO COMPARE THE TWO MACHINES IN PRACTICE

    # on each machine, at the same commit
    source ~/.venvs/naval/bin/activate
    python3 scripts/parity.py --emit > parity-$(uname -m).json

    # anywhere, on the pair
    python3 scripts/parity.py --compare parity-x86_64.json parity-arm64.json

Seconds, against ~20 minutes for the Mac's suite and ~5 hours for fortress's.
The receipt stamps `machine`, `system`, `python`, `numpy` and the commit, and
covers six fixed genomes — the reference hull, the kit reference, four
coverage-band and named forms — because a receipt that drew its own hulls would
differ between runs for reasons that have nothing to do with either box.

**Three things this does NOT do, stated because a green parity is easy to
over-read:**

1. **A green parity is not green tests.** It says the two machines agree, not
   that either is right. A consistent pair of wrong answers passes it, and the
   receipt's own `_README` says so.
2. **It is not a substitute for executing the other machine's claim.** What
   actually caught defects on 2026-08-20 was each box re-deriving the one
   number that mattered — the Mac found fortress's Block 3 arm A was a straw
   man, and found a wave-floor fix landed in a module the case writer never
   calls; fortress refuted the Mac's proposed crossover mechanism. None of
   those needed the other machine's prose. All needed its NUMBERS.
3. **Do not read the other machine's summary in place of its artefact.** The
   2026-08-20 P0 incident is the standing example: a triage tool sliced an
   error string at 88 characters, `worst |diff| 1.110e-16` became `worst |diff|
   1.110`, and a well-formed number wrong by sixteen orders of magnitude was
   ranked P0 above every other failure and used to tell the other machine its
   queue was blocked. Four independent checks were spent refuting it.
   `docs/LESSONS.md` carries it as the ANALYSIS-layer form of the lying
   receipt.

---

## 6. WHAT NOT TO DO

- **Do not restore a "BIT-EXACT" claim** that spans the two machines. It was
  removed by `1e16b15` from both guards that carried it, and measurement (a) is
  the counterexample.
- **Do not widen a tolerance to make both machines green.** Every tolerance in
  §2 is bracketed by two measured anchors. If a new difference exceeds one,
  that is a finding: record it, do not absorb it. A failing gate is
  information (CLAUDE.md; `docs/LESSONS.md` defect class 4).
- **Do not treat a `stl_sha256` mismatch between the two boxes as a defect.**
  It is a PLATFORM fact until the GENOME itself disagrees. Every `stl_sha256`
  recorded in `data/gate2u-*.json` is a same-machine receipt.
- **Do not compare a cancelled tail relatively** without saying so; use the
  array's scale (§4).
- **Do not attribute a cross-machine difference to "the architecture" as
  though it were established.** See §7.1. This is the same discipline
  `docs/research/CROSSOVER.md` enforces on the crossover: a real, repeatable,
  predictive observation is not thereby an explained one. PREDICTIVE != CAUSAL.

---

## 7. OPEN — and these are open, not hedged

**7.1 The MECHANISM behind the cross-machine difference is NOT isolated.**
Every guard in this tree attributes it to "a different SIMD width and FMA
schedule", and that is a plausible mechanism consistent with everything
measured. It is **not** an isolated one: the two machines differ in
architecture AND numpy build AND Python build AND libm AND compiler flags, and
no experiment here holds any of those fixed. The falsifying test is cheap and
has not been run — same architecture, two numpy builds; or one machine with FMA
contraction disabled. Until then the honest statement is *the two machines
disagree at the ulp level*, not *the architecture causes it*.

**7.2 There is no arm64 golden.** §4. The resistance tier has no regression
fence on the simulation node. Recording one is a decision, not an oversight —
two goldens mean two things to keep in step — and it has not been taken.

**7.3 `genome_sha256`'s portability is argued, not measured.** It is excluded
from `parity.py`'s compared `values` (with `reasons`, `warnings`, `detail`,
`fidelity_why`), so the one identity claimed to be portable is the one the
parity tool does not check. Including it would make the claim testable at zero
cost. **This is the shape of gap D3 and of defect class 1: the thing nobody
measures reads as fine.**

**7.4 No parity receipt pair has ever been exchanged.** `scripts/parity.py`
exists, Gate XP proves its classifier in both directions on synthetic receipts,
and `parity-x86_64.json` / `parity-arm64.json` **do not exist anywhere in this
tree.** The tool is proven; the measurement is owed. Nothing in this document's
class-2 section rests on a real two-machine comparison — it rests on the golden
delta (§1c) and on the two 2026-08-20 incidents.

**7.5 The golden records its architecture but not its toolchain.**
`GOLDEN_ARCH = "x86_64"` is one field, while `parity.py`'s receipt stamps
machine, system, python AND numpy. fortress001's numpy and Python versions are
not recorded anywhere in this repository, so the golden's provenance is thinner
than the parity receipt's and 7.1 cannot be tested against it retrospectively.

**7.6 Class 3 membership is not machine-checked.** Gate XP covers the contract
layer. Nothing asserts that C_T, GCI, drift or coverage are compared as
engineering-equivalent rather than numerically — the discipline in §2c exists
in `parity.py` for six attitude keys and nowhere else. A CFD quantity acquiring
a float-tolerance comparison would not fail any test today.

**7.7 The lower anchor of the 1e-12 bar is 1.77x, not four orders.** §2a. The
band is still empty, so the bar is not moved here — but a claim that it has
four orders of margin is now refuted, and the next quantity added to the parity
receipt could close the remaining 1.77x without anyone noticing. What would
settle it: compare against the array scale where a quantity can cancel, or
declare per-key denominators the way `_TOL_BY_KEY` already declares per-key
tolerances.
