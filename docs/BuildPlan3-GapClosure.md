# BuildPlan 3 — Gap closure
## From a green ladder to a ladder worth being green

**Chief-architect intent.** BuildPlan 1 built the kernel. BuildPlan 2 planned the
vessel. This plan fixes what the 2026-08-05 audit measured: the kernel's physics
is right, and almost everything around it — the gates that judge it, the mission
that steers it, the tiers that are supposed to re-validate it — is not yet
connected or not yet honest. Every gap in `docs/GAP-REGISTER.md` lands in exactly
one phase below, and each phase closes with a gate that would have caught it.

**This plan adds no new capability that the build plans did not already promise.**
It is inherited: every phase names the BuildPlan 1 phase or BuildPlan 2 stage
whose bar it is finally meeting, and PLM §3's lifecycle (requirement → research →
decision → implementation → gate → evidence → retirement) is the unit of work.

---

## Ordering principle, and why R0 comes first

The audit's structural finding is that **the check and the thing checked share an
owner**. Fixing physics while a RED gate can be erased by renaming a string means
every subsequent claim of progress is unverifiable. So the order is:

```
R0  make the gates unfakeable          <- everything after is measured by these
R1  make the mission binding            <- independent of R0; highest user-visible value
R2  single-source every number          <- unblocks R4 (scantlings) and R7
R3  wire the ladder                     <- unblocks R6 (co-kriging needs HF data)
R4  physics validity                    <- Gate 0/1 bars
R5  L2/L3 correctness, then the number  <- Gate 2 bars; compute-bound
R6  learning spine                      <- depends on R3 + R5
R7  manufacturing + rules moat          <- Gate 6 bars
R8  BuildPlan 2 (V2.0-V2.6)             <- depends on R2 + R3
```

R0 and R1 are independent and can run in parallel. R6 genuinely cannot start
before R3 and R5 — co-kriging starved of high-fidelity data is the one gap that
is blocked by physics rather than by effort.

---

## R0 — Make the gates unfakeable
*Inherits: PLM §5 (gate registry as single source), honesty rule 6.*
*Owner: verification. Effort: ▪▪. Closes: D1–D16, J1–J4, J9.*

The gate ladder is the platform's law. Today it can be edited to green, silenced
by one line, and its CI signal is a constant.

**R0.1 · Structured verdicts, not prose.** Replace the free-text `blocked` string
with a typed verdict `(status, metric, value, evidence_path)`. Add a test
asserting (a) every `tests/test_*.py` appears in `GATES`, (b) every `suite=None`
row carries a machine-readable status, (c) the set of RED gates equals the set of
ledger entries. This kills D1 — renaming cannot change a verdict that is a
literal enum, and deleting a row fails the coverage test.

**R0.2 · The expected-red ledger.** Commit `data/gate-ledger.json`: one entry per
known-red gate with `metric`, `watermark`, `better_is`, `owner`, `verify`
command, `measured_utc`, and **`review_by`**. `gates.py --ledger` then exits 0
only for a red that is *in the ledger and no worse than its watermark*; **NEW**,
**REGRESSED**, **LEDGER STALE** (gate recovered, entry not removed) and **LEDGER
EXPIRED** (past `review_by`) all exit 1. Nothing is softened — the red rows still
print, and land on the CI run summary rather than in a collapsed log. The expiry
is the anti-wallpaper clause: a known-red gate cannot become permanent furniture.

**R0.3 · CI becomes a signal again.** Required check = `pytest` + `gates --ledger`
(exits 0 today). A second, always-run step publishes the full red table to
`$GITHUB_STEP_SUMMARY`. A second **job** installs `requirements-optional.txt` and
runs `--strict`, so Gate 2's 18 Capytaine tests stop silently vanishing and a
suite that stops running becomes a failure rather than a comfortable
`GREEN (n skipped)`. Closes D14, D15.

**R0.4 · Close the silencing holes.** Fail on `xfail`/`xpass`; anchor `counts()`
to pytest's summary line rather than reverse-scanning stdout; drop `-x`; require a
per-gate expected minimum test count. Closes D2, D13, D16.

**R0.5 · Break the self-refereeing loops.**
- `flywheel`: compare against an **immutable high-water mark**, not the last
  value; require strict improvement to *lower* the mark; add absolute floors
  (`med <= 0.35`, `cov >= 0.80`) no ratchet can move; clamp coverage to [0,1];
  hard-code the holdout seed and mission as module constants and store a hash of
  the holdout X in the baseline, refusing if it changes. Commit a seeded
  `data/baselines.json` and make a missing baseline a **refusal**, not a pass.
  Closes D3, D4, D5.
- `gate2m`: require GCI **below** a bar (≤5%) *and* the extrapolated C_T inside
  the band. Uncertainty must never widen the acceptance region. Return a distinct
  non-zero code for "no verdict". Closes D6, D7.
- `review.py`: `is_complete()` must require every edition string to be set and
  date-shaped. This **flips Gate 6R red today** — correctly, per honesty rule 6 —
  until the editions are recorded. Split the gate: `6R-thresholds` (what was
  actually reviewed) from `6R-parity` (Gate 6's real bar: verdict parity with a
  qualified reviewer on ≥3 reference designs). Closes D8, D9.

**R0.6 · One number, one source.** Delete the Gate 2M prose literal; derive the
row from `scripts/gate2m.py` lifted to a library function, printing the ledger's
recorded value labelled *"recorded <date>, not re-measured here"* when run without
data. Give `gate2m` its own test (J9). Generate README's gate table from the
runner and add a test that fails when they diverge. Reconcile the five circulating
Gate 2M figures to the one settled measurement with a superseded-by trail. Pin
`requirements.txt`. Closes J1–J4, J8.

**Gate R0:** every gate row carries a machine-readable verdict; the ledger and the
RED set cannot diverge; `xfail`, `importorskip` and a stdout-spoofing `conftest`
all fail the runner; a fresh clone's first retrain refuses; CI's required check
exits 0 and turns red on a *new* break, verified by deliberately breaking one gate.

---

## R1 — Make the mission binding
*Inherits: BuildPlan 1 Phase 1 and Phase 5 (Gate 5: "translates to correct specs";
§1.5 "requirements as typed, executable pass/fail checkers").*
*Owner: chief-architect. Effort: ▪▪. Closes: B1–B9, E12, E15.*

Four missions were driven end to end and all four hulls were rejected. The system
does not deliver the boat that was asked for, and its own requirement checkers
cannot notice.

**R1.1 · Consume the length hint.** Soft target + hard band, not a free variable:
narrow `HullProblem.xl/xu[0]` to the hint ± tolerance **and** add a `length` term
to `Evaluation.g` so the constraint is visible to the ladder, not just to the
optimiser. Measured price: **+21% to +76% Wh/NM** — and DLR moves from 21–43 into
122–387, L/B into 2.9–4.0, Cb into 0.55–0.72. Take the trade.
**Fix the LLM seam first** (R1.6): the moment the hint steers geometry it becomes
an LLM-writable geometry bound, and today's disjoint-names test would not notice.

**R1.2 · Make `carries-target` two-sided, and stop substituting.** `0.98·target ≤
disp ≤ 1.10·target`. When the weight model exceeds the mission target that is a
**mission failure to report**, not a number to overwrite with `max()`. Report
`disp/target` and `LWL/hint` in the delivered record so an overshoot is visible
without an audit.

**R1.3 · One validation gate for all three input paths.** Move `_FIELD_RANGES`
into `MissionSpec.__post_init__` so prose, HTTP and LLM share it. Closes the
0-knot → 1.278e13 NM/day path and `ui/server.py`'s unclamped `MissionSpec(**body)`.

**R1.4 · Fix the parser.** Strip `\d,\d{3}` groups before the decimal-comma
substitution (`"6,000 kg"` → 6.000 kg); add a sanity floor that appends to
`notes` rather than passing silently; delete the dead solar branch and the
double-counted waters inference.

**R1.5 · Make the mission reach the physics.** `payload_kg = crew ×
CREW_MASS_KG + stores`; deadrise related to cruise speed and design category; a
**Froude validity envelope** on `total_resistance` that refuses or routes to a
planing method above Fn ≈ 0.45 rather than reporting a thin-ship answer at Fn 1.09.

**R1.6 · Ratchet the LLM, never relax.** `design_category = min(llm, floor)` —
stricter wins — with the conflict appended to `notes` exactly as `parse_mission`
already does. Clamp LLM scalars to a **relative band around the deterministic
floor**, not a global range. Add `if not math.isfinite(val): continue` and move
the `int()` coercion inside the guard. Whitelist `waters` characters. Grade the
energy requirement against the mission's stated cruise plan, not the LLM's.

**R1.7 · Objectives that describe a boat.** Replace `−GM` maximisation with a GM
**band** (`gm ≤ 0.20·B_wl`, or a roll-period floor ~3 s); add an explicit cost or
structure-vs-length coupling so build area is a real cost rather than a Pareto
axis the selection rule discards; add an **LCB band** (−3…+3 %LWL) and re-apply
the proportion checks to the **floated** state (`b_wl_max/draft`), not only to the
parameter vector.

**R1.8 · A real held-out brief corpus.** ≥100 briefs, generated or collected
separately, checked in **frozen**, never edited to fix a failure, with adversarial
phrasings (ranges, negations, mixed units, non-English). Today's "held-out" set is
10 in-repo briefs scoring 100% that the parser was demonstrably tuned against.

**Gate R1:** for a suite of missions, the delivered hull's LWL is within the stated
band, displacement within ±10% of target, and LCB/L-B/B-T/Cb/GM-B inside the
naval-architecture bands — asserted per mission, not in aggregate. An LLM payload
can never produce a spec whose GM floor is below the deterministic floor's.

---

## R2 — Single-source every number
*Inherits: CLAUDE.md design-side invariants ("the recurring defect is A NUMBER
DECLARED TWICE"), PLM §1 platform law.*
*Owner: chief-architect. Effort: ▪. Closes: C1–C12.*

**R2.1 · Derive the scantling, don't declare it.** The platform's 15 mm ply fails
its own ISO 12215-5 rule for every SKU it sells (crossover at 845 kg; the 6 t
liveaboard needs 18.24 mm). Model it as the audit and the architect independently
recommended: `actual = max(nominal_sheet, iso_required)`, with the inequality
itself exposed as a constraint in `Evaluation.g`, so a design whose chosen sheet
is too thin is **infeasible** rather than silently re-specified. Then
`min_bend_radius_m` and the structural mass follow the same number automatically.
Expect the demo to go red — **that is the finding, not a bug in the demo.**

**R2.2 · Feed the rule the right mass.** mLDC is loaded displacement
(`hs.disp_kg`), not the weight budget. Better: close the loop so budget and
displacement agree instead of papering over the gap with `max()` (this is the same
defect as B2 and E3, seen from the scantling side).

**R2.3 · Frame spacing is one number.** `FRAME_SPACING_M` in `limits.py`, consumed
by both `iso12215` and `engineer`, which must then emit the frames and stringers
the scantling span presumes. At the spacing actually built today (1400 mm) the
rule wants 63.8 mm of plywood — the two modules describe different boats.

**R2.4 · Sweep the rest.** `FREEBOARD_FLOOR_M` imported by `translate`;
`min_bend_radius_m()` called rather than re-derived; `VCG_FRACTION` used by
`weight_budget` so the guarding test becomes tautological; `Hull.shell_area()`
replacing the magic 1.6; `CREW_MASS_KG` moved to `limits`; one GCI implementation.
**Extend `test_optimize.py:72`'s source-scan to every module**, so this class of
defect is caught by a test rather than by an audit.

**Gate R2:** a source scan finds no numeric literal duplicating a `limits.py`
constant anywhere in `navalai/`, `scripts/` or `ui/`; and a design whose declared
sheet is thinner than its ISO-required thickness is reported infeasible.

---

## R3 — Wire the ladder
*Inherits: BuildPlan 1 §2 honesty rule 2 ("nothing ships un-re-validated"),
Gate 3's "OOD queries reliably escalate to L2/L3".*
*Owner: chief-architect + cfd-engineer. Effort: ▪▪▪. Closes: A1–A6, I14.*

This is the architectural gap: L2, L3 and tier R all exist and none is reachable
from the product. There is no `keep` verb.

**R3.1 · `evaluate.revalidate(design, target_tier)`.** One dispatcher that runs
`seakeeping` (L2) or `cfd` (L3), records `{value, tier, sigma}` to provenance, and
lets a higher-tier result **supersede** the L1 badge. `Evaluation.tier` becomes
the *highest tier actually reached*, and the Gate 1b assertion that currently
forbids escalation (`ev.tier == "L1"`) is corrected to assert monotone promotion.

**R3.2 · Tier R inside the ladder.** Call `iso12217.assess` and `iso12215.assess`
from `evaluate()`, add `rules_pass` to `Evaluation`, and append the rule margins
to `CONSTRAINT_NAMES` so NSGA-II is constrained by them — exactly the pattern
`limits.py`'s own docstring prescribes for the GM floor.

**R3.3 · Export refuses.** `export_dxf`/`export_step` take an `Evaluation`, not a
`Hull`, and raise unless the design is `ok`, has reached the mission's required
tier, and passes the rules report. Stamp `hull_id`, tier, sigma and the rules
verdict into the STEP header and DXF layer comments.

**R3.4 · Escalate on OOD.** `surrogate.predict_or_escalate(x)` returns
`(value, tier, sigma)` and, when out of support, runs real physics or raises
`OODRefusal` — never an L1-badged number. Replace the σ-threshold with a
support-distance test calibrated against measured error, and make `CoKriging.is_ood`
consult the low-fidelity GP too.

**R3.5 · Content-addressed, resumable tier tasks.** Key every tier result by a
hash of `{genome, solver, solver version, source version, mission, rho}`; check
provenance before running. Resumability, caching and provenance become one
mechanism — which matters concretely because L3 runs here are killed by thermal
sleep. This also fixes `hull_id`'s collision (E9) by hashing the exact stored bytes.

**Gate R3:** a kept design's provenance shows an L2 (and, when requested, L3) row
superseding its L1 row; an export of a design that never re-validated raises; an
OOD query never returns an L1-badged number; re-running a completed tier task is a
cache hit rather than a recompute.

---

## R4 — Physics validity
*Inherits: BuildPlan 1 Phase 0 and Phase 1 (Gate 0, Gate 1).*
*Owner: chief-architect. Effort: ▪▪. Closes: E1–E18, H1–H3.*

The kernels are right; their inputs, their bars and their guards are not.

**R4.1 · Holtrop-Mennen.** Gate 1's bar names it explicitly and it does not exist.
Implement Holtrop 1984 with the 1988 corrections, commit its published validation
table, and assert per-point agreement. Until then Gate 1 must read PARTIAL with
the missing clause named — it currently reads GREEN.

**R4.2 · Anchor the anchor.** Commit a Michell/tank Cw(Fn) table for the standard
Wigley and assert per-point agreement within stated error bars, the way
`benchmarks/kcs.py` already does for EFD. A magnitude band is not a comparison.

**R4.3 · Account for the mass.** Refuse when `agg.total_kg < 0.95 × displacement`,
or add an explicit positioned ballast item — so KG, LCG and trim all see the 54–77%
of displacement that currently has no declared position. This is the single
largest correctness defect in the stability chain.

**R4.4 · Fix the friction arguments and the grid.** Pass floated beam, floated
draft and floated waterline length to `form_factor` and `ittc57_cf`; replace
Watanabe with a small-craft form factor and make the clamp *widen the reported
uncertainty* rather than silently apply; raise the Michell grid defaults to a
converged setting (~2 ms of the 43 ms Gate-1 headroom) and add a convergence test
on the **chine** hull, which has kinks the Wigley does not.

**R4.5 · Make the L0 gate bite.** Delete or widen the four tautologies; make the
twist proxy the **derivative** (or halve the bar) so the 18.8% of hulls that pass
buildability with a true twist above the limit stop passing; wire
`Hull.panel_twist_rate()` into the gate; add the missing small-craft checks
(transom immersion vs Fn, panel width, prismatic/LCB band). Add the Gate 0
**12-known-hull round-trip** that has never existed.

**R4.6 · Never map "undefined" onto "ideal".** Assert `np.isfinite` on every `g`
value and every badge sigma; a non-finite quantity is a violation, not a pass.
Trim and heel return `None`/violated when their denominators are non-positive.
Verify the lower bracket in `solve_to_displacement` and return a convergence flag.
Replace bare `except Exception` in `grade()`/`translate()` with a third `ERROR`
state so a broken checker cannot masquerade as a failed design. Build `g` from
`CONSTRAINT_NAMES` explicitly so `python -O` cannot silently re-map columns.

**R4.7 · Make the uncertainty real, or label it.** Add `basis` (`measured` |
`assumed`) to every badge and persist it. Propagate `agg.sigma_kg` into the
displacement badge and KG uncertainty into GM — the one honest sigma the codebase
computes is currently thrown away. Route every user-facing scalar through `_q()`
so `weights_kg` and `/pareto` stop shipping bare numbers.

**Gate R4:** Holtrop reproduces its validation set; Wigley matches the reference
curve per point; no evaluation returns `ok=True` with an unaccounted mass fraction
above 5% or a non-finite quantity anywhere; the L0 gate's live-constraint count is
asserted; 12 known hulls round-trip.

---

## R4b — BENCHMARK STRATEGY: a plan defect, not a chore
*Added 2026-08-06 after measurement. Inherits: BuildPlan 1 Phase 2 Gate 2,
ALIGNMENT.md "Benchmark anchor set is wrong for the product line".*

**PLM.md §2 says what we build: sharp-chine small craft, 4–14 m, buildable from
sheet — a 6 t solar liveaboard as the reference product and a 1–3 t dayboat.
BuildPlan 1's Gate 2 certifies the physics tier against KCS: a 230 m container
ship, slender, round-bilge, no chine, no immersed transom, at Fn 0.26.** The
gate that certifies the physics was written for ships and the product is boats.
Everything downstream inherited it — benchmark geometry, y+ targets, case
generator defaults, and months of CFD.

This was recorded (ALIGNMENT.md, PLM roadmap "second anchor QUEUED") but filed
as a future task rather than treated as the plan defect it is.

**The correction is SEQUENCE, not substitution.** KCS is not demoted: the
physics it teaches is hull-agnostic and every part of it transfers.

| Anchor | What it validates | Status |
|---|---|---|
| **Wigley** (analytic) | the wave-resistance MACHINERY, against a closed-form Michell answer we derived ourselves. Free, no tank data, no transom to confound it. | ADDED 2026-08-06, `scripts/wigley_stl.py` |
| **KCS** (tank) | free-surface capture, wall treatment and y+, force integration, grid convergence, AND — via its published sinkage −1.394e-2 m and trim −0.169° — the mass/inertia/CoG/6DoF chain that EVERY boat needs. The only hull we have with published truth. | keeps full workload |
| **DSYHS** | 9–14 m displacement/semi-displacement yachts. Directly the Solar Liveaboard. | OWED |
| **Fridsma / Series 62** | hard-chine planing: chine, immersed transom, spray, dynamic lift. Directly the Dayboat and tender. | OWED |

Gate 2 is rewritten to require the product anchors, not only KCS. Reading a
green Gate 2M as small-craft validation remains forbidden.

**Corollary for L1, same root cause:** Michell thin-ship is being applied at
Fn 1.09 on the tender case and reported as PASS (gap B7). A ship method on a
boat. The Froude validity envelope in R1.5 is the same correction one tier down.

**Corollary for the mesh:** `_HULL_REFINE`, `_TARGET_YPLUS` and the layer count
were all tuned on KCS and DO NOT TRANSFER. MEASURED: KCS bridges its 37.9 mm
hull cell with 5 layers, Wigley's 52.1 mm cell needs 10, and capping at 5 there
reproduces exactly the last-layer/cell ratio (0.082 vs 0.071) that produced ZERO
layers on KCS. The layer count is now DERIVED per hull by `n_layers_to_bridge`
and guarded at both ends — a stack that cannot bridge warns, a stack thicker
than its host cell raises. Any constant tuned on one hull is suspect.

---

## R5 — L2/L3 correctness, then the number
*Inherits: BuildPlan 1 Phase 2 (Gate 2, in full), §1.3's named traps.*
*Owner: cfd-engineer. Effort: ▪▪▪. Closes: F1–F19.*

Gate 2's bar has four clauses. Resistance is RED and re-measurable; sinkage and
trim are newly implemented but ungated; added resistance in waves does not exist;
unattended meshing is RED at 75%.

**R5.1 · Fix what would corrupt the number before spending the compute.**
- **Trim sign** — bow is at +x, so a correct bow-down result currently reports
  ≈+200% error. Unit-test with a synthetic log of known orientation.
- **`post_gci.py` symmetric handling** — it has none, and `runs/kcs_gci` *is*
  symmetric, so it would report exactly half the drag. Move the doubling into
  `post.settled_drag(case)` and have both scripts call it.
- **GCI p-clamp** — understates 5.37× at p=0.1. When p < 1, fall back to Roache's
  `p = 1, Fs = 3.0` and label which rule fired.
- **Crash detection** — `runs/kcs_free` diverged at t=0.0012 and the gate says "no
  force data yet". Distinguish crashed from unstarted (`FOAM FATAL`, signal,
  `Max(alpha.water) > 1.1`).
- **`setFields` must be fatal**, and `checkMesh` needs a fatal threshold on
  zero-volume and incorrectly-oriented faces — 47 of them went straight into a
  multi-hour diverging solve.
- Move the concurrency guard **above** the resume branch and the `rm -rf`; skip it
  for `MESH_ONLY=1`; make `run_campaign.sh` treat exit 3 as fatal.
- Raise `nLimiterIter` 3 → 15 and `nAlphaCorr` 2 → 3 to match `DTCHullMoving` —
  the diverging alpha solve, not the dict structure, is what killed the free run.
- Gate `correctPhi` behind `free_motion`; delete stale motion dicts when
  regenerating fixed; fix the pitch stiffness to `ρgI_L` (currently 3.96× high);
  warn loudly when `--kg` is omitted.

**R5.2 · Close the traps the plan names.** `cpt.BEMSolver(method="direct")` in one
factory, with a test asserting it; pin `Delhommeau(tabulation_nr=676,
tabulation_nz=372)` explicitly rather than relying on a library default; construct
`SeakeepingResult` with a convergence-derived `uncertainty_rel` so L2 numbers
carry a real sigma, or delete the dataclass so the badge is not implied.

**R5.3 · Added resistance in waves.** `seakeeping.added_resistance(hull, omegas,
heading, U)` via Capytaine's pressure field with a far-field drift formulation;
Tokyo-2015 Case 2.10 scatter into `benchmarks/kcs.py`; a **Gate 2W** row. This is
the largest un-started clause in the plan.

**R5.4 · Gate all three quantities.** Add sinkage/trim scatter bands and `and`
them into the verdict — today the gate can print PASS on C_T alone with sinkage 3×
wrong.

**R5.5 · THE OPEN BLOCKER: pressure drag is 3–6× too high and grows with time.**
MEASURED across six runs at 2026-08-06. Viscous drag is now CORRECT
(1.15–1.22× ITTC-57, stable) — the layer work landed. The entire discrepancy is
on the pressure side, and it is independent of mesh resolution, tank depth,
run-out length, layers, solver settings and time-stepping scheme:

| run | t | pressure | vs expected (~20.8 N) | viscous | vs ITTC |
|---|---|---|---|---|---|
| kcs_iso | 7.5 s | 41.4 N | 2.9× | 40.9 N | 0.63× |
| kcs_sym | 13.7 s | 36.8 N | 2.6× | 52.8 N | 0.82× |
| kcs | 76 s (settled) | 60.1 N | 4.2× | 93.3 N | 1.44× |
| beach + deep tank | 8–10 s | 84.8 N | 6.0× | 76.0 N | 1.18× |

Hypotheses TESTED AND ELIMINATED, each at real compute cost — recorded so they
are not re-tried:
- *insufficient convergence* — no; the error GROWS with convergence.
- *missing boundary layer* — fixed; viscous corrected, pressure unchanged.
- *wave reflection off the outlet* — a beach (run-out 0.6 → 1.5 Lwl) and a
  deeper tank (0.6 → 1.0 Lpp) made it WORSE (2.9× → 5.7× at the same t).
- *LTS as a cheap path* — far worse (14.5×). Waves are inherently unsteady, so
  per-cell pseudo-timesteps make propagation speed meaningless. LTS is kept
  only as a flow-field initialiser and can never produce a resistance number.
- *mass leak* — no; Phase-1 volume constant to 0.001%.

REMAINING CANDIDATES, in order: (a) the wave-resistance machinery is
systematically wrong — decided by the Wigley run against Michell; (b) the KCS
transom is wetted where it should ventilate at Fn 0.26, giving a growing
low-pressure base region, which matches the signature exactly.

**Nothing downstream of this is trustworthy.** A GCI would converge onto a
wrong number more precisely, and a DSYHS or Fridsma validation would be
corrupted identically. This is the gate on R5.6.

**R5.6 · Then run it.** The symmetric triplet for the GCI, the free
sinkage-and-trim run against the published values (the only validation of the
mass/inertia chain we have), and `mesh_robustness.py --n 200 --solve` for Gate
2U's "converges" half, which has never had a number.

**Gate R5:** C_T, sinkage and trim each inside the Tokyo-2015 band, with GCI ≤5%
computed from a measured refinement ratio on a solved triplet; added resistance
within workshop scatter; ≥95% of 200 hulls mesh **and converge** unattended.

---

## R6 — Learning spine
*Inherits: BuildPlan 1 Phases 3, 4, 7 (Gates 3, 4, 7).*
*Owner: ml-engineer. Effort: ▪▪▪. Blocked on R3 + R5. Closes: I1–I14, D10–D12.*

**R6.1 · A real interface.** `HullGenerator` Protocol
(`fit`/`sample`/`sample_conditioned`/`to_latent`/`from_latent`/`raw_feasibility`),
server takes a generator from a factory, Gate-4 tests re-expressed against the
Protocol so GMM and diffusion run the same suite. The "drop-in upgrade slot" does
not currently exist.

**R6.2 · Measure feasibility on the model, not the sampler.** Gate on
`raw_feasibility` at the 99% bar and record today's **77.6%** as RED per honesty
rule 6. That is the number the diffusion upgrade has to beat — and note the pPCA
latent already in the repo scores 89.4%.

**R6.3 · Make conditioning condition.** Start the candidate loop at `seed + 1` so
batches are disjoint from the reference, and make the test compare against the
same-batch top-k control — the only baseline that can fail.

**R6.4 · Honest surrogates.** Learn the nugget as a free hyperparameter and add it
to the predictive variance (coverage is 0.85–0.91 against a nominal 0.95); emit a
reliability diagram; average the Gate-3 metric over ≥5 holdout seeds and restate
the bar at the honestly measured value, plus a separate *local* gate on a trust
region around a Pareto point, which is what the 1–2% bar actually refers to.

**R6.5 · Fix the multi-fidelity machinery, then feed it.** Select ρ by the joint
KOH likelihood (it can currently pick ρ̂ = 0 and silently discard the LF model);
normalise `batch_infill` by the candidate box, not the HF training span, and raise
rather than silently returning fewer than k; then **wire `training_matrix("L2"/"L3")`
into a CoKriging builder** — the wiring R3 and R5 unblock.

**R6.6 · Latent honesty and Gate 7's second clause.** `from_latent` returns a
projection flag and displacement so a slider move that silently returns a training
hull (2.2–6.0%) is visible. Add `wall_clock_s` to `RetrainReport` and a
mission→validated-hull cycle timer persisted beside the error metrics — half of
Gate 7 is unbuilt. Build the frozen suite from `benchmarks/` plus a held-out
design-space region, not from the training distribution.

**R6.7 · The slider bar applies to every widget.** `/generate` is 1704 ms against
a 100 ms p95 bar and untested; pre-fit at server start, cap the conditioned search
by wall-clock, and extend the gate to `/generate` and `/pareto`.

**Gate R6:** raw generative feasibility ≥99%; conditioning beats the same-batch
top-k control; 2σ coverage ≥0.90 averaged over ≥5 seeds; co-kriging trained on
real L2/L3 rows beats single-fidelity kriging after re-validation; p95 <100 ms on
every interactive endpoint; retrain wall-clock recorded and non-increasing.

---

## R7 — Manufacturing and the rules moat
*Inherits: BuildPlan 1 Phase 6 (Gate 6, in full).*
*Owner: compliance + chief-architect. Effort: ▪▪▪. Closes: G1–G8, D9.*

**R7.1 · Make the DXF cuttable.** Write a `HEADER` with `$INSUNITS` and emit
millimetres. Today a shop importing the file cuts a 10 mm part instead of a 10 m
one. Add a round-trip test asserting the declared unit.

**R7.2 · Real nesting.** Rotation plus rectangle/no-fit-polygon packing onto
1.22 × 2.44 m sheets, with panels split at scarph joints — the two hull panels
currently fit on no sheet at all. Derive `ply_sheets` **from the layout** and
retire `WASTE_FACTOR`. Emit a line-item **BOM** from the same layout.

**R7.3 · Test the refold.** Implement `refold(FlatPanel) -> (n,3)` and assert max
deviation from the hull in millimetres against a stated bar. Gate 6's refold
clause is currently unmet and untested.

**R7.4 · A developability metric that can fail.** Replace the O(h²) chord residual
with discrete Gaussian curvature (angle defect), or a refinement-convergence test:
a true developable's residual falls as O(h²), a non-developable's plateaus. Add
the hyperbolic paraboloid as a **negative control** — it currently passes the
cylinder bar. (The hull's own topside panel carries a real warp: O(h^0.7).)

**R7.5 · Export the validated hull.** Default `n_stations` to `hull.n_stations`,
or record the discretisation error in the export receipt — 12 vs 41 stations is a
0.50% volume difference between what passed the ladder and what ships.

**R7.6 · Scope the standards honestly.** `iso12217.assess` must **refuse** below
6 m rather than silently applying the -1 path to a 4 m dayboat; implement ISO
12217-3 or record the refusal. Implement **ES-TRIN** — the Solar Liveaboard is a
Danube boat and it is the one SKU that requires it. Open `6R-parity` with three
worked reference designs, hand vs code, stored in-repo.

**Gate R7:** a nested DXF whose declared units re-import at the right scale and
whose panels fit real sheets; a BOM that reconciles with the layout; refolded
panels within the stated millimetre bar; the hypar negative control fails; no
design is assessed by a standard outside its scope.

---

## R8 — BuildPlan 2 (V2.0–V2.6)
*Inherits: `BuildPlan2-FullVessel.md`, unchanged.*
*Owner: ergonomics-architect. Blocked on R2 (one weight model) and R3 (tier
vocabulary reaching the ladder).*

Six of seven phases are at zero code, which matches PLM's "PLANNED" — no
correction needed. Two preconditions from this plan:

- **R2 must land first.** Tier F consumes the same component masses the stability
  solver uses; that only works once the mass model closes (R4.3) and the scantling
  is derived rather than declared (R2.1).
- **R3 must land first.** `MassItem.volume_m3`, `.material`, `by_tier` and the
  `'E'`/`'F'` tier vocabulary have **no reader anywhere** today. V2.4 is where they
  acquire one; until then, mark them explicitly reserved-unwired so a future reader
  does not assume the hook is live.

Then V2.0 → V2.6 proceed exactly as written in BuildPlan 2.

---

## Continuous — documentation as a gated artifact

Doc drift is a defect class here, not cosmetics: five different Gate 2M numbers
circulated because five documents each held their own copy. Fold into R0.6:
generate README's gate table from the runner; add a test that fails when a
document's gate status diverges from `navalai.gates`; apply CLAUDE.md's recorded
supersessions to ALIGNMENT.md (PLM §3 step 7 requires removal "with a note, never
left ambiguous"); add the missing Gate 2U row and honesty rule 6 to README; ignore
`renders/` and the tracked build artifacts; commit a checksum and fetch script for
the KCS geometry so its validation stops silently skipping everywhere but this Mac.

And enforce PLM §3 step 4 where it is actually violated: **CFD-path and script
changes ship without gate tests** (3 of the last 10 commits). `scripts/gate2m.py`
is now the executable authority on Gate 2M and has no test of its own — which is
precisely how its number drifted.
