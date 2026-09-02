# LESSONS — what this project learned the expensive way

These are the things that are NOT recoverable from the code, the tests, or
`git log`. Mesh lore lives in `CLAUDE.md`; gate definitions live in
`navalai/gates.py`; findings live in `docs/GAP-REGISTER.md` and the gap queue.
This file holds only what would otherwise die with the session that learned it.

It lives in the repository ON PURPOSE. It was previously kept outside the
project, where it did not survive a clone and could not be reviewed in a diff —
the same defect as gap D3 (`baselines.json` read by a gate but not tracked) and
J5. A lesson nobody can read is a lesson nobody has.

---

## How to work here

**Run the process; do not improvise beside it.** `PLM.md` §3 defines the
lifecycle (requirement → research → decision → implementation → gate → evidence
→ retirement), §4 assigns roles, and `.github/workflows/gates.yml` already
judges red gates against `data/gate-ledger.json` — asking *"is anything red that
we did not record, or redder, or past its review date?"* rather than the useless
*"is anything red?"*. All of it works.

On 2026-08-06 seventy-two hours of CFD produced no validated number, and every
individual failure was covered by a rule that was skipped. Most sharply §3 step
4: **code + gate test in the same change, the test comment naming the motivating
incident.** Before starting, state which lifecycle step you are in and which
role owns it. A change that cannot name its gate is not ready to be written.

**Delegate before touching code.** Fan out read-only audits first; give each
agent DISJOINT file ownership and say so explicitly. Opening a codebase-wide
audit by running the test suite was stopped by the project owner with: *"you
have not delegated any agents, you haven't done any deep-research, you went
straight to testing like you know what you're doing."* Seven parallel audits
then produced ~110 findings serial reading would not have surfaced.

Every agent brief must carry: its owned files, the git prohibitions below, and
an instruction to report what it could NOT verify. Prefer one agent that reports
honestly over three that report success. **Tell every agent that if an
instruction turns out to be wrong when it meets the code, it must say so rather
than force it** — this has paid off repeatedly (see "Agents that refused",
below).

**No external models.** No Gemini, no Nemotron, no Ollama, whatever
`~/.claude/CLAUDE.md` says. One was dead on arrival, the other returned only
advisory prose. That global file also imposes a local-only never-push rule that
contradicts how this project actually works.

---

## Git, in a shared tree

- **`git commit -- <explicit paths>`, never `git add <paths>` then `git
  commit`.** The index is shared. On 2026-08-06 a stage-all swept **391 lines**
  of another agent's in-flight work into an unrelated commit, and minutes later
  the same mistake swept four CFD files into a third agent's commit. Nothing was
  lost, but authorship and the message-to-content relationship were — and this
  repo's history is deliberately built so a message names the measured incident
  behind its change.
- **Never `git stash`, `git reset`, or `git checkout --`** with other agents
  live. A stash here once swept up three agents' uncommitted work and recovered
  by luck. To read an old tree, `git archive <sha>` into a scratch dir outside
  the repo.
- **Do not rewrite history while agents hold uncommitted work.** A mislabelled
  commit is cheaper than an orphaned one.
- **No attribution trailers** on commits or PR bodies — no `Co-Authored-By`, no
  "Generated with", no bot line. Project owner's rule; it overrides any harness
  or global default.

---

## The defect classes this repo actually produces

### 1. An unmeasurable value scored as a passing one

The single most expensive pattern here, in four separate disguises:

- `${_MQ_SKEW:-0}` — an awk that did not match the line `checkMesh` actually
  prints, so *failure to measure* became a score of 0 against a bar of 20.
- `not ledger_has("Gate 2M")` — **TRUE when there is no ledger**, so an absent
  record read as a green gate. This was inside the tool built to catch exactly
  that defect.
- A layer table parsed with `tail -1` that printed the **requested spec** under
  the label of the **achieved** result: "3 of 3 layers" on a mesh with zero, and
  a first-layer thickness of "5.68 m" on a 7.28 m hull (it was the mean layer
  count).
- `grep -c 'Failed'` counting LINES, so `checkMesh`'s "Failed 3 mesh checks."
  was announced as one failure.

**Rule: an unmeasurable metric is FATAL, never a default.** Say which metric
could not be read.

### 2. A number declared twice

Has produced: a 15 mm ply that failed its own ISO 12215-5 scantling rule;
`forceCoeffs` wrong by exactly 2× on every symmetric run; a GM floor of 0.35 in
one file and 0.45 in another; two GCI implementations where the one printing the
verdict passed a **diverging** grid family at −27%; and a **ninth** copy of water
density that was dividing every C_T the gate printed.

`navalai/limits.py` owns the limits. `tests/test_limits_single_source.py` is the
fence — extend it rather than adding a copy. And do not apply a bar **twice**:
`evaluate()` already applies the GM and freeboard floors and publishes the result
in `Evaluation.g`.

### 3. A guard that was never made to fire

Every threshold ships with a test feeding it the VERBATIM input it must reject.
A test showing a guard accepts a good case proves nothing about rejection.

A bar **interpolated** between two measurements is a guess: the
incorrectly-oriented-faces bar of 10 sat between 5 (measured to solve) and 73
(measured to die); the gap was later filled at 10, which dies. Validate a new bar
against every historical case — it should refuse the ones that failed and accept
the ones that worked.

### 4. Prose standing in for a verdict

A measured RED gate could be erased by editing one string. Gate 4 stated a
79.3%/88.7% shortfall against a ≥99% bar **in its `scope` text**, in a file that
documents prose as "NEVER load-bearing" — so it printed GREEN and nothing could
fail if it worsened. Statuses are typed enums; a missed clause is RED BY RECORD
with a ledger watermark, an owner and a `review_by` date.

### 5. Citing evidence that no longer exists

`clean-runs.sh --purge` deletes a run directory; the prose citing it is not
deleted. `CLAUDE.md` cited five dead run directories, one in the present tense
("**Running now:** `runs/kcs_sym`") when nothing was running, and cited a deleted
directory as the EVIDENCE that the VOF interface was sound. State whether the
directory still exists, or re-measure.

### 6. A defect measured at a configuration the product never runs

Two register rows overstated their case this way (one reproduced at n=60 but not
at the shipped n=150/k=4). **State the configuration you measured at.**

### 7. The register text being wrong about the code

Three rows were found stale in one night: D11's "31.98%" re-measured at 79.3%,
F4's claim outright false, C2 already fixed. **Verify the defect still exists
before fixing it.** Gap state is derived from the code by predicate
(`scripts/reconcile_gaps.py`), never from prose — and every predicate is run
against the commit the register audited, because *a check that cannot fail on
the defect cannot verify the fix*. Four predicates reported CLOSED on the broken
tree.

### 8. The comments are good enough to fool a checker

Gap B4 ("payload is flat 800 kg regardless of crew") nearly closed on
`has(energy.py, "crew")` — where the line is
`payload_kg: float = 800.0  # crew + stores + water`. **The word was in the
comment on the defect.** Behaviour predicates must read a comment-and-docstring
blanked view.

---

## Physics and compute

**CFD is an anchor, not a loop.** The optimizer runs on L1; nothing in the design
loop consumes CFD. Three to five points ever, run by hand, after the model is
stable. One grid is ~2 h and a settled 5-flow-through run ~7 h at 346 s of wall
clock per simulated second. Automating a campaign that cannot finish was the
wrong architecture independent of any bug.

**The budget is a constraint, not an overhead:** coarse ~15 min, medium ≤2 h,
fine ~4–5 h, on 10 cores. Size the case to the budget *before* launching —
`--symmetric` halves the cell count, and np=10 is the measured optimum (np=5 →
212.7 s, np=10 → 127.2 s, np=15 → 153.1 s), so all 15 cores costs ~20%. State the
projected wall clock and flow-through count before starting.

**Measure the right thing and it gets cheap.** The pressure-oscillation
diagnosis cost **10.5 minutes** because it was measuring a *period*, not a drag
coefficient — so mesh resolution barely mattered. The alternative plan was a
three-day GCI triplet that would have converged onto a phase of that oscillation
and produced a confident wrong number.

**A single sample is not a measurement.** Instantaneous force readings were
quoted as coefficients while the pressure signal swung from −59 N through zero to
+14 N. Average over a full period, and say how many periods the record contains.

**Scope: yachts and small boats.** KCS is KEPT — it teaches waves, pressure, wall
treatment, forces and weight distribution, and it has published EFD data. But
Gate 2M going green is NOT small-craft validation: KCS shares no chine, transom
or spray physics with the SKUs, so a second anchor (Fridsma or DSYHS) is owed.
Topside design — windows, standing headroom, hard-chine topsides that are not
developable — is DEFERRED by decision: fix the simulation model first.

~~**Scale the tank to the wave, not the hull.** The dominant oscillation is a
domain-selected gravity wave ... The fix is **absorption** — a relaxation zone
or momentum sink — not depth, not solver tuning, and not running longer.~~

**SUPERSEDED 2026-08-07 by `runs/kcs_s1`** (`docs/research/CFD.md` §2,
commit `971f441`), and this entry is kept rather than deleted because the
*lesson* changed shape while the paragraph above stayed put in the file every
session is told to read first — which is defect class 5 committed by this file
against itself.

At 3.40 flow-throughs on the current mesh family: **there is no oscillation.**
`scripts/tank_resonance.py` over 2041 samples finds the best single sinusoid
explains **0.4%** of the detrended signal against a 50% bar — NO RESULT. Every
candidate mechanism (seiche n=1..3, Doppler tank modes n=1..8, blocking minimum,
ship transverse wave) had enough cycles in the record to have been seen. The
earlier reading came from a different mesh family at 1.33 flow-throughs, where a
rising quarter-cycle of anything looks like a trend.

Drift collapsed to **0.31%** and C_T flattened, so **the error is not a settling
problem and more wall-clock will not remove it.** Viscous is **1.161×** ITTC-57
(inside the form-factor band, batch error 1.7%); pressure is **2.32×** with a
**36%** batch error — broadband noise, not a mode.

**The transferable lesson, which is the opposite of the one above:** a period
claimed from too few cycles is a period invented by the window. Two runs on one
domain could not separate λ/3 from the domain half-width because they are the
same number in that domain — and the conclusion drawn from them survived into
three documents and would have bought a relaxation zone against a mechanism that
does not exist. `tests/test_tank_resonance.py` now refuses a period claimed from
too few cycles. State the cycle count, or state NO RESULT.

(`verticalDamping` is OpenFOAM.org; ESI v2606 does not have it — still true, and
still the reason absorption would have been expensive rather than a config flag.)

---

## Agents that refused, and were right

Recorded because "the agent pushed back" is the highest-value behaviour observed
here, and briefs should keep inviting it:

- Told to call `limits.py` for the GM/freeboard floors, an agent **refused**:
  `evaluate()` already applies them, so a second call would re-create the exact
  defect `limits.py` exists to prevent.
- An agent drafted a build-time cap on layer-stack ratio and **killed it before
  committing** when the data refuted it — Wigley solves at 1.084 while KCS dies
  at 0.952, so no build-time predictor exists.
- An agent diagnosed a cg=U trapped band from one run (λ 11.44 m vs 12.35
  predicted, c/U 1.94 vs 2.00 — conclusive-looking), then **refuted its own
  answer** on a second speed. One speed was not enough.
- An agent refused to invent `solver_version = "v2606"` because `case.info` does
  not record the build, and wrote `"unrecorded"` with a test asserting it.

And one claim of mine that an agent correctly overturned: I stated a mesh guard
"failed open", inferring it from a missing receipt key. The guard did not exist
when that mesh was built. **An absent receipt is evidence about the code's
absence, not evidence the code ran and failed.** Do not state an inferred
mechanism as a measurement.

## AN AGENT THAT HAS NOT WRITTEN A FILE HAS PRODUCED NOTHING (2026-08-13)

**Every long-running agent must create its output file as soon as it has its
first real finding, mark it IN PROGRESS, and append after every source.** Put
the instruction in the prompt WITH its reason. Never let an agent hold findings
in context until a final write.

MEASURED, and it cost the project owner real money. Asked to "pause all
agents", the lead used `TaskStop` — which KILLS, it does not pause. Seven
agents died. THREE had no transcript and could not be resumed at all
(`SendMessage` returns "No transcript found"), so they restarted from zero. A
fourth later died at a session limit one step before writing its file, at the
literal words "I have everything I need. Writing the document now." Four
agents' work was paid for twice, and the owner said so.

The control is in the same session: the relaunched agents were told to write
incrementally, and `docs/research/standards/` now holds 9,000+ lines across
four files that would otherwise have died with them. Same task, same model, one
instruction different, opposite outcome.

Three rules follow:
- `TaskStop` is not a pause. If agents must be stopped, expect to lose their
  in-context reasoning; only what is on disk survives.
- TRY RESUME BEFORE RELAUNCHING. `SendMessage` to a stopped agent resumes it
  from its transcript when one exists — four of seven resumed this way and kept
  everything. Say explicitly which agents resumed and which restarted.
- A resumed agent should be told what changed under it while it was stopped.
  One agent's final run overlapped a file edit by the lead; it verified
  independence by import graph rather than trusting the lead's assurance, and
  that was the right instinct.

## MEASURE BEFORE YOU CALL SOMETHING BROKEN (2026-08-13)

A confident-sounding diagnosis in this repo is usually wrong until measured.
Seven of the lead's own, each refuted by roughly one command:

- "Eleven gap regressions." The columns of `scripts/reconcile_gaps.py` had been
  read BACKWARDS — column 3 is the live predicate, column 4 a stale gitignored
  journal last written two days earlier. Nothing had regressed.
- "The Michell input reads a legacy 3-point section." `Hull.section()` is
  ADAPTIVE: 3 points only at `roundness == 0`, 257 above it. The offsets grid
  integrates to within 0.004% of the closed form. One step from reporting a
  defect that does not exist.
- "The 50% `unaccounted` mass drives the feasibility collapse." Closing it to
  0% moved feasibility 4/30 -> 5/30. Refuted by the sweep.
- Compared moulded volume (to the sheer) against displaced volume (at the
  waterline) and got 240% — **the same mistake made earlier in the same session
  on a -99.994% export figure.** Two quantities, one name.
- "Two ISO rules rest on a superseded edition." `EN ISO 12217-1:2017` IS
  `ISO 12217-1:2015`; the EN year is the ADOPTION date, not the edition.
- Handed an agent the catamaran phase as `k0.sec(t).sin(t)`. Deriving it from
  the code gives `k0.sec^2(t).sin(t)`. The owner had explicitly warned against
  copying a remembered formula instead of deriving it from the wavevector the
  code uses. A later verification put the wrong form 3.99 away from the right
  one on a range of 4.
- Set `_STL_NZ_FILLETED = 48` claiming a "3.15x margin" — calibrated on ONE
  hull. On the population the margin was **1.04x**: the identical error to the
  original author's fixed `nz=16`, committed while fixing it.

Two of these were caught by other agents refuting the lead, and one by the
owner. **When you correct a teammate, verify first** — a teammate's refusal of
a claim about `unroll.py` was correct, and so was an audit's refusal of the
regression count.

## A summariser that truncates is a receipt that lies (2026-08-20)

MEASURED. A triage one-liner extracted each failure's first `E ` line with
`err = es[0][2:].strip()[:88]`. One assertion message was 91 characters:

    AssertionError: section rho=0.35 n=41 i=0: 62 of 514 elements differ,
    worst |diff| 1.110e-16

The 88-character slice ended immediately after the mantissa, yielding
`worst |diff| 1.110`. Not a mangled string — a WELL-FORMED NUMBER, wrong by
sixteen orders of magnitude, with nothing about it to suggest it was partial.

On that basis a session declared a landed commit's "BITWISE value-preserving"
headline false, ranked it P0 above every other failure, told the other machine
its queue was blocked behind it, and flagged a second commit by association.
The other machine spent four independent checks refuting it: the same test
passing on x86-64 at the same commit, four sibling equality fences green on
both machines, a 4684-key bit-exact golden reporting zero mismatches, and an
earlier independent measurement of the real cause.

**This is defect class 2 (the lying receipt) applied to the ANALYSIS layer.**
The same file already records `${VAR:-0}` turning "could not measure" into
"perfect", and a layer table printing the REQUESTED spec as the ACHIEVED one.
A silent `[:88]` is the identical move one level up: it turns "I did not read
all of it" into "this is all of it".

Two rules, and the second is the general one:

1. **A truncating summariser must mark the truncation.** If a slice can cut a
   value, append an ellipsis or do not slice. Never emit a fixed-width cut of
   a numeric message.
2. **Check the artefact, not the summary of it.** Adopted jointly with
   fortress001 after both machines made this class of error within hours of
   each other — fortress ran a 5-hour job on a 6-watt box without checking
   `nproc`; this session quoted a measurement with its exponent dropped.
   Neither was a reasoning failure. Both acted on a DESCRIPTION of a thing
   instead of the thing. Before a number is allowed to reorder anyone's work,
   read it from the raw bytes at its own line, in full.

## A STALLED SOLVE IS NOT A CRASH, AND BOTH LIVENESS CHECKS READ HEALTHY (2026-08-21)

`runs/g2m_coarse` was watched by an hourly monitor for hours while it was
already dead. Neither of its two liveness checks fired:

- `pgrep -x interFoam` -> **RUNNING**. It genuinely was. The process was alive,
  burning ten ranks, and advancing the timestep loop.
- `grep -cE "FOAM FATAL|sigFpe::sigHandler|SIGSEGV"` -> **0**. There was no
  crash. interFoam does not consider this an error at all.

What was actually true, from the log:

    Time = 1.50613          <- frozen, hours, while the loop kept iterating
    deltaT = 3.4e-09        <- collapsed, creeping UP by ~0.1% a step
    Courant Number mean: 0.00094  max: 4.9934   <- max PINNED at the limit

This is the pathological-cell signature CLAUDE.md already documents. One cell's
local Courant will not fall, so the adaptive controller shrinks dt without
bound. At 3.4e-9 s a step, the 75 s endTime needs ~2e10 steps.

**The lesson is about the WATCHER, not the solver.** A monitor built from
"is the process up?" and "did it print a fatal?" cannot see the most expensive
failure mode there is: a run that is alive, quiet, and making no progress. Both
questions had the right answer and the wrong meaning.

Watch PROGRESS, not liveness: latest `Time` against the previous sample. If it
has not advanced between two checks, the run is dead regardless of what the
process table says. A collapsing `deltaT` with a pinned Courant maximum is the
same fact seen a step earlier and is worth alerting on by itself.

Same shape as the `${VAR:-0}` receipts and the layer table that printed the
REQUESTED spec: **an unmeasured quantity was allowed to read as a good one.**
Here the unmeasured quantity was progress.

## A NEGATIVE RESULT ABOUT THE LITERATURE IS A CLAIM ABOUT YOUR SEARCH (2026-08-21)

`docs/audit/GATE2-PHYSICS-STACK.md` concluded, after a targeted hunt, that no
published series gives hard-chine resistance at Fn ~ 0.26 — and went further,
offering a mechanism: a chine is chosen to generate dynamic lift, so hard-chine
models are towed at planing speeds, and nobody tows one at 5 knots. The pattern
in the evidence table was real. The conclusion was **FALSE**.

Compton's 1986 USNA systematic series varies section shape between HARD CHINE
and ROUND BILGE over **Fn 0.10–0.60** — our 0.26 is interior to it — and the
companion YP81 programme is a matched-pair experiment (three round-bilge,
three hard-chine, three displacements, three LCGs, 54 runs) whose stated
purpose was to isolate the effect of the chine. It has existed since before
this project started. The operator found it after this document had declared
the absence structural.

Three failures compounded, and only the first is about searching:

1. A handful of queries returned no hit, and "I did not find it" was written up
   as "it does not exist".
2. **A MECHANISM WAS INVENTED TO EXPLAIN THE ABSENCE.** That is what made the
   error durable: a plausible physical story ("chines are for planing") turned
   a search result into a law, and a law does not invite re-checking. An
   explanation for a negative result is not evidence for it.
3. The conclusion was stated with no search attached, so no reader could see
   what had actually been looked at.

A negative result about a body of literature is only ever a statement about the
queries that were run. State it as one — with the queries — or do not state it.
The positive claims in the same document were held to a far higher bar: DSYHS
became evidence when the data was ACQUIRED and MD5-verified, not when the
series was named. Absence deserved the same rigour and did not get it.

## A WALL-CLOCK BUDGET MAKES A SEEDED RUN IRREPRODUCIBLE (2026-08-22)

`scripts/design_kit.py`'s refinement stage ran `while time.time() - t0 <
budget_s`. Everything else about it was deterministic: the seed sweep drew a
fixed 35000 candidates and returned a byte-identical best (7.3 mm) on every
attempt, the rng was seeded from the CLI seed, and the basin-restart fired zero
times. The same seed still returned **2.31 mm, 2.31 mm, then 8.00 mm**.

Nothing in the algorithm differed. The STEP COUNT did, because the loop is
bounded by wall-clock and the machine had a CFD campaign on it. A fixed rng
seed does not reproduce a run whose iteration count depends on load.

**The damage is to the EXPERIMENT, not the product.** A reliability A/B was run
twice against a "2 of 5" baseline, and the comparison was between two different
experiments: the change under test was confounded with however many steps each
run happened to get. Any success rate quoted from a wall-clock budget is partly
a statement about what else the box was doing.

So:

- a user-facing budget in SECONDS is right — someone wants a bounded wait;
- an EXPERIMENT must bound the same loop in STEPS, or it measures the machine.

`--refine-steps` exists for that, and wall-clock stays the default.

**The general form, and this repository keeps finding it in other clothes:**
an instrument that looks like it measures the thing, and partly measures how
the measurement was taken. The same session produced two others — an 87%
"settled" rate from comparing the wrong pair of averaging windows (the correct
pair gives 18.8%), and a Gate 2U ledger whose own `verify` command counted
RAN-TO-BUDGET (83.3%) while the watermark was the SETTLED rate (17.6%). In all
three the machinery was sound and the instrument was not.

Before quoting a rate, ask what would change it besides the thing it is
supposed to be measuring.

## SPEED IS A MESH PARAMETER: THE SAME MESH SOLVES AT Fn 0.38 AND DIES AT Fn 0.53 (2026-08-27)

Measured on the hookprobe owner hull (`docs/research/HOOKPROBE-CFD-CAMPAIGN.md`),
three times in one night: `make_case.py --stl` cases at 4.1 m/s solved cleanly
with `--n-layers 10`, and the SAME hull at 5.66 m/s died at t~0.045 s with
deltaT collapsing to 1e-105..1e-26 while one cell's Courant stayed ~10 — at
n_layers 10, 8 AND 5. Every one of those meshes PASSED the mesh-quality bars
(0 zero-volume, <=5 wrongly-oriented, skew < 20). Three lessons, none of them
recoverable from the logs of a single failure:

- **The layer stack that is safe at one speed is not safe at another.** The
  first-layer thickness is derived from the target y+, so raising the speed
  thins the near-wall cells under an unchanged stack count. n=10 at 4.1 m/s
  and n=10 at 5.66 m/s are DIFFERENT meshes.
- **Above ~Fn 0.5 the impulsive start, not the stack, is the killer — stop
  backing off layers and ramp the velocity instead.** Three stack depths dying
  identically is the signature that the start-up transient, not the near-wall
  aspect ratio, folds the cell. make_case.py exposes no ramp; that is the fix
  to build, not another rung on the backoff ladder.
- **On Apple Silicon a solver FPE surfaces as SIGILL ("Illegal instruction:
  4"), not sigFpe.** The night this was learned the OS had just been updated,
  and "the update broke the binary" was the obvious wrong diagnosis. The
  discriminator is in the log: deltaT collapsing while Courant max holds is
  physics, whatever the signal number says.

Cost lore worth keeping beside it: +25% speed (8->10 kn) TRIPLED wall-clock
per simulated second on this family (dt 3.2 ms -> 0.9-1.1 ms, and at Fn 0.48
it never relaxes after startup, where at Fn 0.38 it does). The timestep is set
by the fastest water in the tank — wave crests and spray — not the boat speed.

## CFD MEASUREMENTS ARE DESIGN LEVERS ONLY WHERE A GENE CAN HEAR THEM (2026-08-27)

The owner asked the right question — "check lessons from CFD runs to see if
any data can boost design: curves, chine, keel line" — and the answer sorts
cleanly into three bins. Recorded here because the sorting itself keeps
being re-derived.

**Bin 1 — measured AND expressible (act on these):**
- **The pressure/wave system dominates bluff-stern hulls and it is an AFT
  problem.** hb19 at Fn 0.33: 78% pressure of 1733 N total
  (`runs/hb19_7kn`, settled). hookprobe v1-v3 at Fn 0.38: 78-80%, stern
  system dominant, transom 0.24 m immersed. The levers are transom
  clearance and an eased aft shoulder — and since the design-waterline
  genes landed (`dwl`, `rb_transom`), the kernel can finally EXPRESS an
  eased aft plan on purpose instead of receiving one from the SAC.
- **Prop-plane placement**: the tunnel inflow receipt (wet, 99-107% U0 in
  the deep layer, deficit 0.70-0.84 near the surface) is carried on the
  TUNNEL drive law in `propulsion.py`. Deep axis, behind the keel tail.
- **Form factor**: Watanabe 1+k = 1.094 +/- 0.05 at KCS proportions vs
  1.161 RANS-measured — order corroborated, sigma marginal. The receipt is
  on `resistance.form_factor`; do not narrow sigma_k without a second
  anchor.
- **Entry angle**: the 11.5-deg axe entry the campaign praised is inside
  the KB cruiser's <= 12-deg band the critic already enforces. Anchored,
  no change needed.

**Bin 2 — measured, NOT yet expressible (do not fake a gene):** fin/skeg
trailing-edge taper (v2's lever; appendages are absent from geometry.py),
wet-deck/tunnel topology (Phase 4's inner boundary), roll damping from
chine-mounted bilge keels (report field only). These become levers when
their geometry exists; encoding them as bars today would judge hulls on
features the kernel cannot draw.

**Bin 3 — method, not geometry:** a drag delta smaller than the settled
window's scatter (~+/-2.5% on the hookprobe mesh family) is NOT a design
signal, whatever its sign — v1->v3 was claimed only as a monotone
DIRECTION across three settled runs, never as three resolved numbers. Any
CFD-informed optimize loop must hold deltas to that bar or it will tune on
noise. And the owner's split stands: theory first (Kelvin wavelength,
ITTC, hydrostatics — check, don't discover), simulation only for what has
no formula (tunnel inflow, fin wakes, which cell folds first).

## A GREEN SUITE IS NOT A WORKING SYSTEM: NINETEEN SEAM DEFECTS UNDER 2094 GREEN (2026-09-01)

An end-to-end integration audit ran against a suite that was **2094 passed, 14
skipped, 0 failed**. It found nineteen defects. Not one was a row in
`docs/GAP-REGISTER.md`; not one was a bug inside a module. Every single one was
an **agreement between two subsystems that nothing checked**:

- `form_coefficients` measured a hull the ladder does not float — a split
  stern reported **Cm 1.1514**, which is geometrically impossible, into the
  critic, the certification and the design report;
- a declared `prop_tunnel_recess_m` bought a **flat-bottomed** hull a bigger
  propeller disc and a clean wake, while a hull that drew a real 0.247 m
  tunnel got nothing for it;
- a **catamaran was served the monohull pool** and the monohull Pareto front,
  labelled with its own receipt, because the cache key enumerated 5 of
  MissionSpec's 16 fields by hand;
- the shape repair climbed the **general** morphology bands while the ladder
  scored it on the **family's**, and then `np.clip` moved the hull it had just
  repaired — 9 of 9 repaired seeds destroyed, initial population 0 of 24
  plausible, under a comment claiming "half the initial population is climbed
  to plausibility";
- an ordinary brief — "200 tonne houseboat, 16 m, 5 knots", which the parser
  itself clamps to 200 t — **crashed `pareto_front`** out of the ISO scantling
  rule, losing a whole design run because one candidate could not be planked.

**The transferable part is the SHAPE of the blind spot.** A unit test asks "is
this module right?" and a gate asks "is this bar met?" Neither asks "do two
modules agree about one object?", and that is where every one of these lived.
The register has no row for it because the register models WORK, not SEAMS.

So the answer is not more unit tests. `scripts/gap_sweep.py` (Gate SWEEP)
takes a PROPERTY that must hold across a seam and sweeps it over a generated
population: the suite is the ratchet, the sweep is the search. Twelve probes,
4 seconds, and it uses the ledger's own rule — a declared finding is carried
with its number and its reason, a new one fails, a stale declaration fails,
and **nothing above P3 may be merely declared**.

### The instrument caught itself first, and that is the warning

`gap_sweep`'s first run reported seven P1 findings of 0.17–0.32%, every one on
a hull with `r_stem`. They were not defects. The probe compared **401-station
descriptors against 41-station ladder integrals** and attributed the grid
difference to the model. Re-measured on a common grid the two agree to 1e-9,
and the ladder's own integral converges onto the descriptor value
(r_stem waterplane: 41 → 46.2695, 401 → 46.1813, 1601 → 46.1792 m²).

That is this file's own "an instrument that partly measures how the
measurement was taken", committed by the tool built to catch it, within a
minute of it existing. **When a new checker fires, suspect the checker first.**

### A DECISION IS MEASURED AT A CONFIGURATION TOO

Defect class 6 says *beware a defect measured at a configuration the product
never runs*. The mirror is just as expensive: `export.py` records a careful
2026-08-13 measurement DECLINING to raise `Hull.n_stations` — 81 stations cost
`evaluate()` +51% "and it buys the LADDER nothing — wetted +0.014%, displaced
volume +0.006%". Every word of that is true, and it was measured two weeks
before the SPLIT STERN existed. Re-measured against a 1281-station reference,
the split's **BM carries −0.532% at 41 stations** (−1.506% with `dwl`), and BM
drives GM, which is a safety floor.

Nothing was wrong with the decision. What was missing is that a decision, like
a defect, has a configuration — and the product grew past it silently. State
the configuration a DECISION was taken at, and re-open it when the feature set
moves.

### Two refuted hypotheses before the right one, on one defect

3 of 6 delivered designs for "8 m river launch" produce an STL the case writer
refuses as not closed. Diagnosis went:

1. *the 1e-10 sliver bar drops one side of a shared edge* — REFUTED: both
   transom-cap triangles have area exactly 0.0 and are dropped at any bar,
   including a strict `> 0.0`;
2. *keep the degenerate cap triangles, then* — REFUTED by trying it: 3 open
   edges became **20**;
3. the truth: at the transom, section rows 0 and 1 land at **exactly** the
   same z, so the cap's bottom quad is a LINE and the two shells meet at a
   pinch point instead of a seam.

Both wrong answers were plausible and both would have shipped. The cost of
testing each was about a minute. **On this codebase, test the fix before you
believe the diagnosis** — and when the fix makes it worse, that is information
about the diagnosis, not about the fix.

### And a cheap check that would have been a lie

The obvious follow-up was to have `certify` check closure cheaply. Measured at
nx=40/nz=10 the same three failing hulls read **zero** open edges — the pinch
is resolution-dependent — so the cheap check would have published SAFE for a
surface the case writer rejects. Not building it was the fix; naming what the
verdict does NOT cover was the rest of it. A guard that can only be built
wrong is better left unbuilt and declared.


## 15 · Compute is launched by decision, not by gate colour (2026-09-02)

A 78 CPU-hour KCS solve was launched because it was "the next experiment" of
a RED gate — correct case selection (the single free-trim grid, not the 687
CPU-hour triplet), healthy solve, and still the wrong default: it was priced
only AFTER the operator asked what it cost, and the pricing changed the
decision to DEFER. The trap is that a well-prepared Queue-A (verification)
experiment always looks like the next task, because it is concrete and its
gate is red; meanwhile the Queue-B (product) experiment that costs the same
— one own-hull flywheel case — is the one that advances what the project is
for. Two rules came out of it, in `docs/audit/CFD-COMPUTE-TRIAGE.md`:
every CFD launch states purpose / gate / cases / wall / CPU-hours /
evidence / consumer BEFORE it runs, and a red verification gate never
outranks product work for machine hours unless a traced dependency says the
product is waiting on it (for Gate 2M, traced: nothing is). The same launch
also caught `run_campaign.sh` declaring COMPLETE at t=0/0 outside the
OpenFOAM wrapper — the `|| echo 0` defect class again — so the one run that
was stopped still paid for itself.
