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

**SUPERSEDED 2026-08-07 by `runs/kcs_s1`** (`docs/BUILD-PLAN.md` Part IV.a,
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
