# NavalAI ROADMAP — one ordered plan

> **This file is the ONE plan.** It supersedes the roadmap content of
> `NavalArchAI-BuildPlan.md`, `BuildPlan2-FullVessel.md`,
> `BuildPlan3-MissionToOrder.md`, `docs/BuildPlan3-GapClosure.md`,
> `docs/STAGE-PLAN.md` and `PLM.md` §6. Those files are **retired to research
> records** — §6 says exactly what each keeps and what it loses.
>
> **It states no status of its own.** Status comes from
> `python -m navalai.gates`, `data/gate-ledger.json` and
> `python scripts/reconcile_gaps.py`. Every number below carries the command
> that reproduces it and the moment it was taken.
>
> Consolidated 2026-08-11 at `b5002be` by four read-only audits with disjoint
> document ownership. Baseline measurements re-run by hand; see §8 for what was
> not verified.

---

## 0 · Why this file exists

Twenty markdown documents, **451 KB** (`cat *.md docs/*.md | wc -c`), carrying
**seven** overlapping roadmaps. This project's most expensive defect class is *a thing declared
twice* (`docs/LESSONS.md` §2 — it has produced a ply that failed its own
scantling rule, `forceCoeffs` wrong by 2×, and a GCI that passed a diverging
grid family). Applied to a number it costs a wrong answer. Applied to the plan
it costs the ability to know what is done.

The measured consequence, and the reason this is not a tidying exercise:

- **The same "what is not built" claim appears in four documents and all four
  are now false.** `README.md` contradicts *itself inside one file* — its
  GENERATED gate table carries `Gate V2.1` and `Gate V3.0`, and its
  hand-written prose eight lines below says the arrangement grammar and the
  policy module do not exist.
- **The blocker three documents route readers to is stale by a day.**
  `docs/BuildPlan3-GapClosure.md` R5.5 says pressure drag is "3–6× too high and
  **grows with time**". Re-measured 2026-08-07: **2.32×**, drift collapsed to
  **0.31%**, no growth. `PLM.md` §6, `ALIGNMENT.md` and
  `docs/CFD-BLOCKER-BRIEF.md` all still point at the stale framing, and
  `docs/LESSONS.md` still prescribes the fix for a mechanism that was
  subsequently measured not to exist.
- **`ALIGNMENT.md`'s scorecard contradicts the table directly above it** — it
  claims 15 ALIGNED/CLOSED; the table shows 7 with 11 rows still reading `GAP`.

None of that is carelessness. It is what happens when seven documents each hold
a copy of one state and only the code is regenerated.

**The law this file adds, which is the existing law one level up:**

> A number lives in exactly one place. **So does a work item.**
> No work item may exist only in prose.

Every item is a gap with a predicate, a gate with a bar, or a recorded
retirement. §4 is the list of things that currently satisfy none of the three,
and closing that list is Phase 0.

---

## 1 · The document map — who is authoritative for what

Consolidation does **not** mean one file. Four of the six audited documents are
not plans at all, and their unique content is the best prose in the repository:
`docs/HLD.md` §3 carries the TIER-vs-STAGE distinction (which it correctly
notes "is not stated in any build plan"), §5 the data contracts, §7 the
enforcement mesh; `docs/APSE.md` carries the refutation of cheap-CFD-by-scaling
with its three-case measurement. Merging those into a roadmap would destroy
them.

**All of the measured staleness lives in the STATUS sections — which are
exactly the duplicated ones.** So: consolidate status, preserve design.

| Artifact | Authoritative for | Must NOT contain |
|---|---|---|
| `CLAUDE.md` | how to work here: paths, git law, house style, CFD operating lore | status, roadmap, a measurement it is not the only home of |
| `PLM.md` §1–§4 | platform law, product lines, lifecycle, roles | §6's roadmap board (moves here); restated bars |
| `docs/LESSONS.md` | what was learned the hard way, not recoverable from code or `git log` | anything a predicate could answer |
| `navalai/gates.py` + `data/gate-ledger.json` | **the status** | prose verdicts |
| `docs/GAP-REGISTER.md` + `scripts/reconcile_gaps.py` | **the work queue** | items with no predicate |
| **`docs/ROADMAP.md`** (this file) | **the order, the dependencies, the owners** | duplicated bars, restated measurements |
| `docs/HLD.md` §1–§8 | the architecture as designed | §9/§10/§11 (status — deleted, see §6) |
| `docs/APSE.md`, `docs/END-TO-END-AUDIT.md`, `docs/PRESSURE-OSCILLATION.md` | dated measurement records | any forward plan |
| `docs/BuildPlan4-SellBuildRun-WindWing.md` | SELL/BUILD/RUN + WindWing research | status (it already refuses to carry any) |

---

## 2 · The state, measured

Reproduce all three before quoting any of them.

```
python -m navalai.gates                 # gate status
python scripts/reconcile_gaps.py        # the work queue
python -m pytest tests/ -q              # the suite
```

**Measured 2026-08-11 at `b5002be`, clean tree:**

| | |
|---|---|
| Register findings | **119** — 97 closed · **20 open** · 0 needs-human · 2 retired |
| Findings with a machine-checkable predicate | **117 of 119**; the other 2 are RETIRED with an argued reason and no path into `apply()` |
| Findings whose state is prose | **0** |
| Gates registered | 41 |
| Gates RED in the ledger | 4 — Gate 2M, 2U, 4F, 6R |
| Suite | **784 passed, 1 failed, 5 skipped** in 345 s |

**The one failing test is pre-existing and blocks every push.**
`tests/test_stageE.py::test_latent_front_spans_designs` — seed 11 gives an LWL
spread of **0.349** against a bar of 0.4, on a front of 15 members clustered
13.59–14.85 m out of a 4.0–20.0 m range. Reproduced on a clean `git archive` of
`df70d00` in a scratch tree, so it predates the consolidation work. The test's
own docstring records the bar being set at 0.4 against a then-measured minimum
of **0.810** over six seeds, after the gap I7 decoder fix was measured to cost
latent-front diversity (median 1.026 against 2.352). Something has since eaten
the remaining margin. `pareto_front_latent` is called with `policy=None` in the
test, so governance is **not** the cause. **Needs a bisect. The bar does not
move** (honesty rule 6). Tracked as **P0-1** below.

---

## 3 · The open work, machine-checked

These 20 rows are the only work items in this project whose state is derived
from the code rather than asserted. `scripts/reconcile_gaps.py` prints them;
this table adds the ordering and the owner.

| id | sev | one-line | owner | phase |
|---|---|---|---|---|
| **F1** | CRITICAL | added resistance in waves: zero implementation — no drift force, no heading sweep, no Case 2.10 EFD, no gate row | cfd-engineer | P3 |
| **B4** | HIGH | `payload_kg` flat 800 kg regardless of `crew`; crew=12 and crew=2 both float at 6004 kg | chief-architect | P1 |
| **B5** | HIGH | nothing costs length — Wh/NM falls monotonically with LWL | chief-architect | P1 |
| **D9** | HIGH | Gate 6R answers *threshold* parity; Gate 6 asks *verdict* parity — zero reference designs | compliance | P4 |
| **D10** | HIGH | Gate 3's 15% bar passes only on its chosen seed (0.112 @ 991 vs 0.170–0.193 elsewhere) | ml-engineer | P0 |
| **E5** | HIGH | no public-CAD hull round-trip; only `vector(named(x))` on one hand-picked vector | chief-architect | P2 |
| **E9** | HIGH | `hull_id` collides: hashes `round(v,10)`, stores unrounded under INSERT OR IGNORE | chief-architect | P2 |
| **F16** | HIGH | Gate 2M: no settled GCI triplet exists | cfd-engineer | P3 |
| **I1** | HIGH | co-kriging has never seen a real high-fidelity number — synthetic Forrester pair only | ml-engineer | P5 |
| **I5** | HIGH | no calibration metric beyond one coverage assertion accepting 75% of a 2σ band | ml-engineer | P2 |
| **A6c** | MED | ARD lengthscales saturate at the L-BFGS-B bound (10.0) — σ blind to two design axes | ml-engineer | P2 |
| **E1b** | MED | Holtrop-Mennen implemented and anchored but **not wired into `evaluate()`** | chief-architect | P1 |
| **F17** | MED | Gate 2U at 75% (N=8); `--solve` never run, so the "converges" half has no number | cfd-engineer | P3 |
| **H1** | MED | every badge σ is a hard-coded fraction of its own value | chief-architect | P2 |
| **I13** | MED | Gate 4 clause 3 (non-expert produces a passing hull) — no session, no artifact | verification | P4 |
| **I14** | MED | the surrogate spine has no consumer: `ui/server.py` imports neither surrogate nor flywheel | ml-engineer | P5 |
| **C9** | LOW | undocumented ×1.6 shell-area factor duplicating an exactly computable quantity | chief-architect | **P0 — see below** |
| **E14** | LOW | `solve_to_displacement` returns the midpoint after 80 iterations; target 1.00 kg → 4.13 kg | chief-architect | P2 |
| **E17** | LOW | `NU_WATER` never re-derived from rho; `wetted_surface` ignores longitudinal slope | chief-architect | P2 |
| **E18** | LOW | three of five AST node validators are dead | chief-architect | P2 |

### C9 is mis-severitied, and this is a re-grade request, not an edit

C9 is filed LOW. Re-measured independently on 2026-08-11 it is at least HIGH,
and the evidence is in the codebase's own docstring:

`energy.shell_area_m2()` exists specifically to kill the bare `× 1.6`, and it
says *"`engineer.assess` and the L1 weight path must plank the same boat."*
`engineer.py:139` uses it. **`evaluate.py:406` still reads
`hull.wetted_surface(0.0) * 1.6`.** The docstring's own measurement: true ratio
**1.6879** on the reference hull, and **1.251–6.702 across 200 grammar hulls**
(mean 2.062) — up to **76%** error, −15.4% average, *and the optimiser searches
exactly that box*, so the error varies systematically with the shape being
chosen.

The path is `shell → weight_budget → weight_items → aggregate → KG → GM`. GM
and displacement are two of the four badged quantities, and GM is a constraint
in `Evaluation.g`. A defect that moves a badged quantity and a live constraint
is not LOW. The trailing comment `# computed once, not twice` refers to caching
and makes the line read as already fixed, which is why it survived.

Re-grading is a register edit and the register is an immutable audit record, so
this is recorded here for the owner rather than done. It is scheduled at P0
regardless of its filed severity.

---

## 4 · The orphans — work that exists in no machine-checked place

This is the list the consolidation exists to produce. Every item below is real
work that today has **no predicate, no gate, and no ledger row**, so nothing in
CI would notice if it were forgotten.

### 4.1 Three findings the importer cannot see

`docs/GAP-REGISTER.md` §T (added 2026-08-07) uses a table header of
`| id | finding | where | severity |`. `import_gap_register` requires
`cells[0] == "ID"` **and** `"Sev"` in the header. It matches neither, so **T1,
T2 and T3 are not in the queue, not in `CHECKS`, and no test would notice.**

T1 is a genuine HIGH: *`suite_fingerprint` hashes coordinates and labels but not
targets — MEASURED, the frozen suite's y values moved −4.2% and the fingerprint
stayed identical.* That defeats the mechanism Gate 7 depends on.

The register itself records the mirror-image accident: a table once *was*
headed `| ID | … | Sev |` by mistake and double-imported J9/J10, growing the
register 119→121, caught by `tests/test_gaps.py`. **The guard runs in one
direction only — it catches over-import, never under-import.**

Fix: normalise §T's header, write three predicates, and update
`test_the_queue_is_the_119_findings_the_register_holds` to 122. Add a test that
counts gradeable tables so an unimported section is fatal.

### 4.2 A second gap-id namespace that nothing checks

`N6` exists only in `CLAUDE.md`. `R5.5` lives in `docs/BuildPlan3-GapClosure.md`
and is cited from `PLM.md`, `ALIGNMENT.md`, `CLAUDE.md` and
`navalai/gates.py:265`. **Neither is in the register.** There are two
gap-id namespaces and only one is machine-checked. Every R-number must become a
register row, a gate, or a retirement notice.

### 4.3 The ledger's regression contract is documentation, not code

`data/gate-ledger.json`'s `_README` and `.github/workflows/gates.yml:67` both
promise *"a RED gate worse than its watermark → FAIL"*. `judge_red()` checks
presence, `review_by` parseability and expiry — then **prints** the watermark
into an f-string. **Nothing ever compares a fresh measurement against it.** In a
repository whose thesis is that prose is never load-bearing, the regression half
of the ledger's own contract is prose.

### 4.4 gap ↔ gate linkage is prose-only

15 of 117 predicates name a gate in their evidence string; only **3** are
machine-linked (the `ledger_has()` calls in F16, F17, D11). `navalai/gates.py`
cites gap ids in 7 places, all comments. There is no field on `Gate`, no mapping
table, no test. **You cannot systematically say which gap blocks which gate.**
Cheapest structural upgrade available: a `gate: str | None` on `Check`, plus a
test that every named gate exists in `GATES`.

### 4.5 Three predicates can be closed by a comment

A4 (CRITICAL), F4 (HIGH) and E2 (CRITICAL) call `has()` on Python files instead
of `has_code()`. `code()` exists precisely because gap B4 once closed on the
word appearing in a comment *on the defect*, costing 332 unwound transitions.
The hazard survives in three rows — one of them A4, the row that produced the
original incident.

### 4.6 Bars with no gate

Measured against `navalai/gates.py`: **V2.2, V2.3, V2.4, V2.5 and V2.6 have no
gate row.** So these bars exist only in prose:

- ≥95% of generated layouts pass L0-A + Tier E; ≤ ~1 min/layout (V2.3)
- reproduces the USCG worked examples **exactly**, including the plywood
  **−0.81** negative-contribution case (V2.4)
- Etap criterion: fully flooded, freeboard loss < 3% LOA, remains manoeuvrable
- verdict parity with a qualified reviewer on **≥3 reference designs**
  (BuildPlan 1 Gate 6 — Gate 6R measures a *different* thing)
- ≤1–2% surrogate error near optima (BuildPlan 1 Gate 3)
- ≥90% of a held-out mission-brief set (BuildPlan 1 Gate 5) — and R1.8's
  **≥100-brief frozen corpus does not exist**; no corpus was found under `data/`

### 4.7 A bar declared twice, with different values

`NavalArchAI-BuildPlan.md` Gate 2 sets grid uncertainty at **≤ ~2.5%** ("the
published bar"). `data/gate-ledger.json` Gate 2M sets **GCI ≤ 5%**. Two bars for
one quantity and the live one is **2× looser than the plan**. Nothing reconciles
them. **Pick one, record why, delete the other.**

### 4.8 SELL and RUN are absent from the register, and it does not know

Grepped across the full 77 KB: **zero** occurrences of `telemetry`,
`in-service`, `fleet`, `as-built`, `commissioning`, `sensor`, `field data`,
`customer`. `operat` appears three times, never in this sense.

This is structural, not an oversight. `import_gap_register` files only what the
2026-08-05 audit found, and that audit was scoped by four documents
(`NavalArchAI-BuildPlan.md`, `BuildPlan2-FullVessel.md`, `PLM.md`, CLAUDE.md's
honesty rules). **None of them contains a RUN phase.** Seven parallel audits
could not have found a RUN gap. The machinery is a faithful mirror of a plan
that ends at manufacturing export.

SELL is half-covered under another name: §B (10 rows, 2 open) is customer-intent
fidelity and is the strongest section in the register. But there is **no row
about price, quotation, lead time, or any customer-facing artifact**. A SELL
motion needs a number to quote and the register does not know that number is
missing.

Closest RUN-adjacent seams, and the right place to widen rather than bolt on:
**I1** (co-kriging's high-fidelity arm has never seen a real measurement — that
arm is exactly where operational data enters) and **I14** (the surrogate spine
has no consumer).

### 4.9 Also owed, recorded in three documents and in no gap row

A **second benchmark anchor** (Fridsma / DSYHS / Series 62). `CLAUDE.md`,
`ALIGNMENT.md` and `docs/LESSONS.md` all record it as owed; §F covers KCS only.

---

## 5 · The ordered plan

Ordering rule: anything that makes the machinery lie comes before anything that
uses the machinery. Everything in P0 is measured, cheap, and currently blocking.

### P0 — Unblock and stop the lying (days)

| # | Item | Done when |
|---|---|---|
| **P0-1** | Bisect `test_latent_front_spans_designs`. The bar stays at 0.4 | the suite is green, or the regression is recorded in the ledger with a watermark, an owner and a `review_by` |
| **P0-2** | **C9** — one shell-area expression | `evaluate` and `engineer.assess` plank the same boat; extend `tests/test_limits_single_source.py` |
| **P0-3** | One `RHO_AIR`. Today: `dynamics.py` 1.225, `extrapolate.py` 1.226, `cfd/case.py` 1.2 | one definition; added to the fence's `_BANNED` list |
| **P0-4** | §T header normalised; T1–T3 predicated; count → 122; a test makes an unimported table fatal | `reconcile_gaps.py` answers 122 rows |
| **P0-5** | Retract the superseded CFD guidance (§7) | `LESSONS.md` and `CLAUDE.md` carry the 2026-08-07 finding |
| **P0-6** | Delete `HLD.md` §11; correct §4/§9/§10; fix the four false "not built" claims | the four claims of §0 are gone |
| **P0-7** | `ALIGNMENT.md`: reconcile the scorecard with its own table | scorecard is derived, or the 11 GAP rows are re-verdicted by predicate |
| **P0-8** | Rename `docs/BuildPlan3-GapClosure.md`; `STAGE-PLAN.md` asked for this and it was never done | the string "BuildPlan 3" identifies one document |

### P1 — SELL becomes a product (weeks)

`B4`, `B5`, `E1b`, plus the whole of `docs/BuildPlan4-SellBuildRun-WindWing.md`
§3: freeze and hash the mission contract; `PriceValue` with a tier and an
expiry; BOM pricing and cost closure; feasibility negotiation over
`Evaluation.g`; render the delivery route `policy/legal.py` already computes and
shows nobody. **New gates M1, Q1, Q2, N1.**

### P2 — BUILD earns its guarantees

Wire `agents.py` onto `pipeline.py` — the spine has zero production callers and
`Gate S` is green on unused code; `docs/END-TO-END-AUDIT.md` §1 already
specifies the mapping. Populate `EvidenceGraph` from `evaluate()` +
`db.Provenance`. Resolve the badge-coverage question (`H1`): honesty rule 1
says "every quantity"; four carry a badge. Also `E5`, `E9`, `E14`, `E17`,
`E18`, `A6c`, `I5`.

### P3 — The number we owe

`F16`, `F17`, `F1`. **The next CFD experiment is free sinkage and trim, not a
longer run** — §7. Then the GCI triplet, then Gate 2U at N=200 with `--solve`.

### P4 — The rules moat

`D9` (verdict parity on ≥3 reference designs — the bar BuildPlan 1 set and
nothing implements), `I13`, the purchase queue, ES-TRIN's remaining scope work.

### P5 — RUN, and the loop closes

`I1` and `I14` widened into a real high-fidelity arm: observation rows in
`db.py`, a generic delta engine, a `flywheel` data source that is not
`evaluate()`. This is the phase that makes the learning loop stop being closed
on itself. File the RUN gaps **before** writing the code, so the machinery
knows what it is missing.

### P6 — WindWing

Blocked behind P1 (environmental state on the mission) and the preconditions in
BuildPlan 4 §5.3 — no 6-DOF model, no roll RAO, no centre of lateral
resistance. The **load gate comes first**, not the power model.

---

## 6 · Retirement notices (PLM §3 step 7)

Nothing is deleted. Each file keeps its unique content and loses its roadmap.

| File | Keeps | Loses | Note to add at its head |
|---|---|---|---|
| `NavalArchAI-BuildPlan.md` | the research sweep and the literature verdicts — genuinely valuable and cited nowhere else | Phases 0–7 as a schedule; the "49 constraints" (measured: **9 live**) and "45–90 params" (built: **15**) | RESEARCH RECORD. Bars migrated to `gates.py`; schedule to ROADMAP §5 |
| `BuildPlan2-FullVessel.md` | §1's sourced ergonomics/flotation constants | V2.0–V2.6 as a schedule | RESEARCH RECORD. V2.0/V2.1 landed; V2.2–V2.6 bars are in ROADMAP §4.6 until gated |
| `BuildPlan3-MissionToOrder.md` | §2's governance argument; the V3.x gate bars | V3.0 written as unbuilt — it **is** built (`navalai/policy/`, Gate V3.0) | RESEARCH RECORD. **§0's Art. 20 summary is wrong for category D** and `policy/legal.py::DISCREPANCIES` says so with a passing test |
| `docs/BuildPlan3-GapClosure.md` | R5.5's eliminated-hypotheses list — the "do not re-try these" record is valuable | R0–R7 as a schedule (largely landed); R5.5's headline numbers | **RENAME.** Re-date R5.5 and correct hypothesis 1 |
| `docs/STAGE-PLAN.md` | S0's closure note (history, correctly marked) | S1–S7 as a schedule → ROADMAP §5 | Its dependency reasoning is inherited here |
| `PLM.md` §6 | — | the roadmap board → ROADMAP §5 | §1–§4 unchanged and load-bearing |
| `docs/HLD.md` §9–§11 | — | deleted; §11 is a present-tense description of a crisis that ended | §1–§8 unchanged and are the best design prose here |

Two corrections owed to files that must not be edited on an agent's say-so:

- **`CLAUDE.md`** — per its own rule, an agent "should not edit THIS file on
  another agent's say-so — surface the correction to the human instead." Owed:
  the superseded oscillation section (§7 below); the GCI triplet budget, which
  `docs/APSE.md` §4 corrects to **~21× / ~68.7 h** and which was never merged
  back, so the wrong number is the one a session reads first; and the absence of
  any mention of `policy/`, governance or BuildPlan 3 in 40 KB of house rules
  while `Gate V3.0` ships.
- **`PLM.md` §5** claims "No gate status or measurement is restated in this
  file". False of the file: it carries `C_T/C_F ~ 9.8`, `N=8`, "RED as of
  2026-08-06", "Gate V2.0 GREEN", "SHIPPED (gates green)". The existing fence
  bans only five specific Gate 2M figures. Either delete the sentence or make it
  enforceable.

---

## 7 · The CFD correction that must propagate

Recorded here because it changes what the next experiment is, and three
documents currently point the other way.

**Superseded** (`docs/BuildPlan3-GapClosure.md` R5.5, `CLAUDE.md` §"R5.5
REPRODUCES … and it is an OSCILLATION", `docs/LESSONS.md` "Scale the tank to the
wave"): pressure drag 3–6× too high and **growing**; a ~5 s tank-mode
oscillation; the fix is **absorption**, a relaxation zone or momentum sink.

**Measured 2026-08-07 on `runs/kcs_s1`** (`docs/PRESSURE-OSCILLATION.md`,
committed as `971f441`), 3.40 flow-throughs, 230,730 cells, mass conserved:

| | measured | expected | ratio |
|---|---|---|---|
| viscous | 75.6 N | 65.2 N (ITTC-57) | **1.161×** — inside the form-factor band, batch error 1.7% |
| pressure | 46.9 N | 20.2 N | **2.32×**, batch error 36% |

- **Drift collapsed to 0.31%.** The transient has washed out. *"The remaining
  error is not a settling problem, and more wall-clock will not remove it."*
  Gate 2M is **not** waiting on run length.
- **There is no oscillation.** Best single sinusoid explains **0.4%** of the
  detrended signal against a 50% bar — NO RESULT. The pressure signal is
  broadband. The earlier reading was taken on a different mesh family at 1.33
  flow-throughs, where a rising quarter-cycle looks like a trend.
- **The viscous half is right**, which localises the error to the pressure side.

**Therefore the next experiment is free sinkage and trim** — KCS Case 2.1 is
towed free; we solve fixed. It is code (`rigidBodyMotion`), not compute, and it
acts on exactly the component that is wrong. Then free-surface resolution
(`cells_per_wavelength` 21.5 against a ≥20 bar), then the grid.

A relaxation zone would have been weeks of work against a mechanism that was
subsequently measured not to exist.

---

## 8 · What was not verified

- **The 97 CLOSED rows are predicate-true, not behaviour-true.** Predicates
  check that a symbol or test *exists*, not that it *passes* —
  `navalai/gates.py` records this in its own words at the Gate 6P comment, where
  G7 and G8 read CLOSED while `tests/test_gapfix_product.py` was failing and
  owned by no gate. The compensating control is Gate 0G, not the reconciler.
- **`tests/test_reconcile_gaps.py` and `tests/test_gaps.py` were not run in
  isolation.** The negative control — all 117 predicates re-run against the
  commit the register audited, requiring zero CLOSED — is the load-bearing
  assurance behind §2's trust claim. It was inside the 784-pass suite run, but
  confirm it directly before relying on §2.
- **`data/evolution/gaps.jsonl` is worthless as a state source** — 119 records,
  all `kind="open"`, zero transitions, all written 2026-08-07 13:47 UTC. Never
  read gap state from it; run the reconciler.
- **The research provenance both BuildPlans lead with** — "24 primary sources,
  11 claims adversarially verified 3-0" and "50 sources, 76 votes, 71 upheld,
  5 refuted" — has **no artifact anywhere in the tree**. Unfalsifiable from this
  repository. Two of BuildPlan 2's five refuted claims are named; the other
  three are not.
- **`origin/apse` and `origin/worktree-apse` still exist as remote refs.**
  Whether they are live upstream or stale tracking refs needs
  `git fetch --prune`, which was not run.
- **`docs/APSE.md`'s constants** are attributed to `runs/kcs_sym` and
  `runs/kcs_iso`. Per LESSONS defect class 5, confirm those directories still
  exist before carrying the numbers forward. Not checked.
- **`STAGE-PLAN.md` S0's own exit criterion fails**:
  `git log --format='%B' master | grep -c Co-Authored-By` returns **5**, not 0.
  All five are inside the three commits that *document* the no-trailer rule and
  quote the string. The spirit holds; the measurable bar does not.

---

## 9 · The dated risk

**Gate 2M and Gate 2U both carry `review_by: 2026-09-06`**, and
`tests/test_gate_integrity.py::test_ledger_review_dates_are_parseable_and_not_already_expired`
asserts `due >= date.today()`.

**The suite goes RED on 2026-09-07** unless both are re-measured or a dated
extension is recorded. Gate 2M's clearing condition is a ~16 h × 3 solve on the
Mac node — that is a scheduling decision that must be taken well before the
date, not on it.

That is 27 days from this consolidation.
