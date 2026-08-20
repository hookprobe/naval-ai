# MATH CONSOLIDATION — the audit matrix (operator brief, 2026-08-20)

**Scope of THIS document.** The operator's §2 asked for a matrix before any
code changes. This is it. It records what is PROVEN, PARTIAL, EMPIRICAL,
REFUTED and MISSING, with the evidence for each.

**Read this first, because the brief's premise needs one correction.** The
brief is written as though the consolidated path must be built. Most of it
**already exists** — `navalai/contract.py` carries `evaluate_hull`,
`supported_domain`, `classify_regime`, `MeshPrescription` and the four
separate verdicts the brief's §6 asks for. Claiming otherwise would repeat
the 2026-08-11 incident in which four documents each asserted that the
governance kernel did not exist and all four were false. The gaps below are
therefore SPECIFIC, not architectural.

---

## A. ALREADY PROVEN (verified in this audit, reproducible)

| Item | Evidence |
|---|---|
| §6 four-question separation A/B/C/D | `HullEvaluation.hull_verdict` / `model_verdict` / `mesh_verdict` / `result_verdict` are four independent fields. Built. |
| §9 one authoritative path | `contract.evaluate_hull(genome, mission, ...)` at `contract.py:602`. Returns 25 fields incl. Fn, Re, regimes, in_domain, tier, sigma, mesh prescription. Built. |
| §9 no second Fn/Re/water | `resistance.nu_water(rho)` interpolates between two named anchors; `flow_regime` is the one Re/Fn site. Built. |
| Regime taxonomy is a TUPLE not a label | `classify_regime` returns a tuple; a catamaran at Fn 0.4 is wave-making AND multihull. Built, and it is the right shape. |
| Domain refusal is by NAME | `supported_domain` returns `(bool, reasons)`, each reason naming its owning constant. Built. |
| Dimensional consistency of the L_min closed form | VERIFIED here: `Re·ν/(Fn·√g)` = (m²/s)/(m^0.5/s) = m^1.5; `^(2/3)` → m. Correct. |

## B. PARTIALLY PROVEN

| Item | What is proven | What is not |
|---|---|---|
| L_min closed form `L=(Re·ν/(Fn·√g))^(2/3)` | The algebra and the dimensions. | The VALUE. See §D-1 — it does not reproduce from the code's own constants. |
| §9 cost + escalation | Cost is computed (`basis["cost"]`, `contract.py:513`). | Neither `expected cost` nor `escalation requirement` is a first-class field; both live in a `detail` dict, so nothing type-checks them. |
| Under-settled taxonomy | Landed and exercised on a real lane (`b5_7p0_10p0`): drift 16.95%→0.738%, correctly classed UNDER-SETTLED. | ONE lane. n=1. |

## C. EMPIRICAL ONLY (predictive; NOT to be described as mechanism)

| Relationship | Status |
|---|---|
| Crossover (scale helps strained meshes, hurts healthy ones; crossover 4.6–5.8) | Predicted 6/6 out-of-sample across 3 hull families (`d92d548`). **Retain as PREDICTOR ONLY.** Mechanism refuted — see §D-2. |
| Layer-backoff ladder | Receipt-only. Works; no derivation. |
| `_HULL_REFINE = (4,5)`, `n_layers ≤ 3..5` envelope | Receipt-only, measured on KCS + own hulls. Does not transfer by derivation. |

## D. REFUTED — permanent record, do not silently replace

### D-1. "2.61 m from two constants the code already owns" — the VALUE does not reproduce
`a62bf48` claims `L_min = 2.61 m`. **MEASURED in this audit:**

    L = (RE_TRANSITION_BAND[1] · ν / (FN_MICHELL_MAX · √g))^(2/3)
    RE_TRANSITION_BAND[1] = 5.0e6      (limits.py, code-owned)
    FN_MICHELL_MAX        = 0.45       (resistance.py, code-owned)
    ν = resistance.NU_FRESH_15C = 1.14e-6   ->  L = 2.5384 m   <- NOT 2.61
    ν = 1.18831e-6 (NU_SEA_HOLTROP)         ->  L = 2.6096 m   <- this is it

The third input is **not a constant the code owns at that call site**: the
test types it inline as `nu, g = 1.19e-6, 9.81`, importing neither. So the
claim "two constants the code already owns" is false in a precise way — it
is two owned constants plus a **literal**, and that literal is a SEAWATER
viscosity while the narrative in `limits.py:284` cites `NU_FRESH_15C` for
the same argument. **A number declared twice, in two fluids.**

SENSITIVITY (measured): +5% on ν or Re moves L by +3.31%; +5% on Fn by
−3.20%. Fresh vs sea is a 4.2% span on ν, i.e. LARGER than the precision
"2.61" advertises. **The third significant digit is not supportable.**

NOT refuted, and worth keeping: the framing. The commit calls it "where two
of our own models stop overlapping", which is the brief's §4 preferred
reading — a REGIME boundary, not a physical impossibility. That survives.

### D-2. The crossover MECHANISM, and its alternative
`57da605` tested the proposed mechanism on fortress and REFUTED it; the
alternative the data suggested was refuted too. **PREDICTIVE ≠ CAUSAL.**
The 6/6 out-of-sample result (`d92d548`) is real and is retained as an
empirical predictor. It must never be written as a physical law.

### D-3. The "P0 batched-section" finding (mine, 2026-08-20)
`worst |diff| 1.110` was a triage tool's 88-char truncation of `1.110e-16`.
Retracted in full; `d7984da` and `2b48383` are NOT implicated. Recorded in
`docs/LESSONS.md`.

## E. MISSING (the gap list — this is the work queue)

| # | Gap | Brief § | Severity |
|---|---|---|---|
| ~~M1~~ **CLOSED d37b212** | ~~The derived L_min has **no code path**.~~ `supported_domain` enforces `RCD_HULL_LENGTH_SCOPE_M[0] = 2.5 m` (a LEGAL bound). MEASURED: `supported_domain(lwl_m=2.55)` returns `in_domain=True`. Hulls in [2.50, 2.61] pass the gate with no honest friction line. | §4 | **HIGH** |
| ~~M2~~ **CLOSED d37b212** | ~~Two DIFFERENT QUESTIONS collapsed to one number:~~ RCD 2.5 m is legal scope; ~2.54–2.61 m is a physics envelope. A refusal must say WHICH. | §4, §6 | HIGH |
| ~~M3~~ **CLOSED 635eb07** (`docs/research/CROSSOVER.md`) | ~~The crossover refutation exists only in commit messages and `STATUS.md` (a rolling channel). **No `docs/research/` record.** CLAUDE.md routes "what was MEASURED and what was refuted" to `docs/research/*.md`. A refutation that lives only in a rolling log will be re-proposed. | §3 | **HIGH** |
| M4 | `MeshPrescription` fields carry no per-field provenance. Brief §10 requires VALUE + EQUATION + REASON + VALIDITY DOMAIN + EVIDENCE. Today one comment says "DERIVED"; nothing distinguishes derived from receipt-only at runtime. | §10 | MED |
| M5 | `expected_cost` and `escalation_required` are not first-class fields on `HullEvaluation`. | §9 | MED |
| M6 | No DEVELOPMENT / VALIDATION / HELD-OUT split exists. Gate 2U's 17-hull bank has been tuned against repeatedly. | §13, §14 | **HIGH** |
| M7 | Minimum state vector not identified. Candidate from the code: `X = {LWL, Fn, Re, n_hulls, ν(ρ)}` — everything else in `mesh_prescription` appears to be a function of these plus geometry scale. **UNVERIFIED; stated as a hypothesis to test, not a result.** | §5 | MED |
| M8 | Suite accounting: 22→14 is NOT comparable (1452 vs 1468 collected). No permanent validation-set identity exists. | §12 | MED |

## F. THE STANDING RULE
From today's two errors, one on each machine (fortress ran a 5-hour job
without checking `nproc`; this node quoted a truncated measurement):
**CHECK THE ARTEFACT, NOT THE SUMMARY OF IT.**


---

## G. PROGRESS (this is a live matrix; update it in the same commit as the fix)

| Gap | State | Commit |
|---|---|---|
| M1 derived L_min had no code path | **CLOSED** | `d37b212` |
| M2 legal vs physical bound collapsed | **CLOSED** | `d37b212` |
| M3 crossover refutation not durable | **CLOSED** | `635eb07` |
| M4 MeshPrescription provenance | open | — |
| M5 cost/escalation not first-class | open — but note Gate HC already covers cost; re-audit before building | — |
| M6 no dev/validation/held-out split | **CLOSED** (Gate 2Y) | `210b00d` |
| M7 minimum state vector | open (hypothesis only) | — |
| M8 suite accounting / validation-set identity | **PARTLY CLOSED** — population identity is now `(arity, seed)` and machine-checked; the suite-count denominator is still open | `210b00d` |

### Skip reasons, captured (the `-rfs` gap fortress asked about)
18 skips, 12 distinct lines. The dominant one is a REAL gap and feeds M6:
**6 skips** read "the screen's bars were calibrated on a 15-parameter genome
and this tree has 16; the campaign labels cannot be transferred — re-run
`scripts/mesh_robustness.py` on the current genome". The rest are absent
`runs/` directories (gitignored) and one recalibration-needed guard fixture.


## H. M6 AS FOUND — the gap was bigger than the row said

The row read "no dev/validation/held-out split exists". MEASURED while
closing it, and this is the part that matters more:

**`seed = 0` names TWO DISJOINT POPULATIONS.** Every Gate 2U bank records
seed 0. The 15-gene banks (n74, cap7, postfix-backoff, campaign-baseline) and
the 16-gene banks share **ZERO** hulls — 0 of 25 by waterline length, 0 as a
set. `sample_valid` draws from `default_rng(seed)`, so adding a gene changes
the draw sequence. Within each group the banks are exact prefixes of the
largest, so there are precisely two streams, not seven.

**The 74-hull bank cannot be regenerated by this tree.** It is a 15-gene
population; the current arity is 16. It is the largest evidence base in the
repository and today's code cannot reproduce one hull of it, so any rate
quoted from it has a denominator that cannot be reconstructed — gap N6's
shape (a watermark citing a deleted directory) applied to a population.

That is what six of the eighteen skips have been saying in words all along.

**Enforced, not promised.** Seed 0 is development permanently (contamination
is a one-way door). Two fresh seeds are reserved. An unrecognised seed is
UNKNOWN, never silently dev. And the fence runs from the other side: any
artifact committed under `data/` is by definition something a session looked
at, so it may not carry the validation or held-out seed. If that test fails,
the held-out set is BURNED — draw a new seed, record the old one as spent,
never relax the check.
