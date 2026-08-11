# NavalAI — High-Level Design

> **The architecture as DESIGNED.** §1–§8 are the load-bearing content and are
> unique to this file — §3's TIER-vs-STAGE distinction, §5's data contracts,
> §7's enforcement mesh and §8's seams are stated nowhere else.
>
> **This file states no status.** It used to: §9 carried a measured table, §10 a
> "what is not built" list and §11 a repository-topology risk. All three were
> second copies of state the runners own, and all three went stale within days —
> §10 denied two modules that ship with gates. §9 and §11 are retired in place
> with their corrections; status lives in `python -m navalai.gates`,
> `scripts/reconcile_gaps.py` and `docs/ROADMAP.md`.
>
> The original provenance line said every count came from running the code on
> `worktree-gap-closure`. **That branch no longer exists**, so those counts were
> unreproducible by the time anyone read them. Design content re-verified
> 2026-08-11 at `b5002be`.

---

## 1 · What the system is

One sentence: **a non-expert states a mission in natural language, and the
platform returns a vessel design that has passed a tiered physics-and-rules
validation ladder, with every number carrying the tier and uncertainty that
produced it, ending in build-ready manufacturing output.**

What makes it different from a CAD tool is not the geometry kernel. It is that
**nothing may claim more confidence than its evidence supports**, and that this
is enforced by executable gates rather than by discipline.

## 2 · The five laws

These are not style preferences. Each was written after a measured incident,
and each has a test that fails if it is violated.

| # | Law | Enforcement | The incident |
|---|---|---|---|
| 1 | Every quantity carries `{value, tier, sigma}` | `Evaluation.badges`, `ui/server._q` | bare floats presented L1 guesses as fact |
| 2 | A number lives in exactly one place | `navalai/limits.py`, Gate L | GM floor drifted 0.35 vs 0.45 across four files; NSGA-II optimised to its own bar and the rules gate then rejected the winner |
| 3 | LLMs translate and explain; they have **no code path to geometry** | Gate 5, `translate.sanitize` | an LLM returning `{"design_category":"D"}` on an ocean brief relaxed a stability bar 42% silently |
| 4 | A failing gate is information; never soften a bar | `data/gate-ledger.json` | a constant-red CI is not a signal |
| 5 | Policy/mission may only **ratchet a gate tighter** | `translate.py` `min()` on category | see law 3 |

Law 5 is the one BuildPlan 3 generalises from missions to governance.

## 3 · The two axes people confuse

This is the single most important structural idea in the system, and it is not
stated in any build plan.

**TIER is how well a number is known. STAGE is how far a design has travelled.**
They are orthogonal, they have separate machinery, and conflating them is how a
design gets a mesh built for a hull that never floated.

```
                    STAGE  (navalai/pipeline.py — where the genome is)
   NEW → GENERATING → VALIDATING → HYDROSTATICS → MESHING → CFD → SEA_STATE
        → ERGONOMICS → MANUFACTURING → SCORING → ARCHIVED → SUCCESS
   forward-only, one step at a time; any stage may fail to a Terminal
   Terminal ∈ {SUCCESS, FAILED_GEOMETRY, FAILED_HYDROSTATICS, FAILED_MESH,
               FAILED_CFD, FAILED_TIMEOUT, FAILED_RESOURCE}
   exactly ONE terminal per genome, append-only log, illegal edges RAISE

                    TIER  (how much you may believe a number)
   L0  algebraic feasibility          ~0.2 ms   grammar.check
   L1  hydrostatics · Michell · ITTC · Holtrop · energy     ~ms
   L2  Capytaine BEM (radiation/diffraction, RAOs)          ~min
   L3  OpenFOAM RANS (interFoam, per-case GCI)              ~hours
   R   ISO/ES-TRIN rules-as-code — an ASSESSMENT AID
   E   ergonomics (BuildPlan 2)      F   flotation/survivability (BuildPlan 2)
```

A stage may only advance when the tier that stage requires has actually been
reached. `Stage.MESHING` without `Stage.HYDROSTATICS` is gap B9 with a compute
bill attached — which is why `pipeline.transition` **raises** rather than
returning `False`: a caller that ignores a `False` keeps going.

## 4 · Layer model

BuildPlan 3 adds the layers above and below the engine. Measured status is in
the right column — this is where the plan and the code diverge most.

```
   Human intent (one sentence)
        ▼
   MISSION INTELLIGENCE   feasibility verdict + owed unknowns      NOT BUILT
        ▼
   GOVERNANCE             legal envelope · design DNA              BUILT (Gate V3.0)
     compiles to ↓ (never runs beside)
     ├─ parameter-space box  (bounds the search)
     └─ constraint rows      (into evaluate.g)
        ▼
   ENGINEERING INTELLIGENCE  component models · compatibility      NOT BUILT
        ▼
   PHYSICS & OPTIMIZATION   L0·L1·L2·L3·R (+E partial, F partial)  BUILT
        ▼
   PROCUREMENT              BOM · closure · quotes                 PARTIAL (BomLine)
        ▼
   MANUFACTURING            nest · DXF · refold · receipt          BUILT
        ▼
   DIGITAL TWIN → FLEET LEARNING                                   NOT BUILT
        ▼
   EVIDENCE GRAPH  (db.py content-addressed, append-only)          BUILT
                   (evidence.EvidenceGraph itself: BUILT, UNPOPULATED —
                    no caller constructs one from a computed Evaluation)
```

**The engine is the finished part.** Everything the last two build plans added
above and below it is unbuilt. That is the honest headline of this design.

## 5 · Data contracts

Six types carry the whole system. Each exists once.

| Contract | Home | Rule |
|---|---|---|
| `Quantity {value, tier, sigma}` | `Evaluation.badges` | law 1; no bare numbers cross a layer |
| `RefValue {value, source, basis}` | `navalai/refdata/` | `basis ∈ {standard, approx, purchased}`; no source, no constant |
| `Genome` | `pipeline.py` | content-addressed; a hull is named by its own contents |
| `MassItem → aggregate` | `weights.py` | **one** positioned mass model; LCG/TCG/VCG derive from it |
| `Evaluation.g` | `evaluate.py` | **one** inequality vector; `<= 0` is feasible; NSGA-II consumes it directly |
| `Gap {id, severity, state}` | `gaps.py` | a finding is a work item with a legal state machine, not prose |

The `Evaluation.g` rule is load-bearing: **adding a check to `evaluate()`
constrains the optimizer automatically.** That is why governance must compile
*into* this vector rather than run beside it — a second constraint engine is a
second place a limit is written down, i.e. a law-2 violation at platform scale.

## 6 · Module map (measured LOC, `worktree-gap-closure`)

```
  KERNEL          grammar 184 · hull_ast 178 · geometry 341 · hydrostatics 159
                  weights 172 · dynamics 168 · energy 134 · limits 137
  PHYSICS         resistance 304 · holtrop 711 · seakeeping 268 · waves 133
  L3              cfd/case 1872 · cfd/post 1021        (+ run-case.sh, campaign)
  DECISION        evaluate 1015 · optimize · pipeline 777
  LEARNING        surrogate 726 · latent 92 · generative 484 · flywheel 843
  RULES (moat)    rules/iso12215 · iso12217 · estrin 283 · ergonomics 171 · review 160
  REFDATA         refdata/ergonomics 219 · flotation 227 · __init__ 161
  PRODUCT         mission 250 · translate 316 · engineer 259 · unroll 790 · export 159
  GOVERNANCE      gates 650 · gaps 411 · db · agents 210
  SURFACES        ui/server.py + index.html · scripts/ (21) · tests/ (34 files)
```

~14.5k lines of `navalai/`. The two largest modules are both CFD, which is
proportionate: L3 is where the physics is hardest to keep honest.

## 7 · The enforcement mesh

Four independent mechanisms, deliberately not sharing an owner with what they
check:

1. **`navalai/gates.py`** — the gate ladder. `Verdict` is a typed status;
   `Gate.__post_init__` rejects anything else, so a RED cannot be erased by
   renaming a string. Gate 0G asserts **every test file is owned by a gate**.
2. **`data/gate-ledger.json`** — the expected-RED ledger. Each RED gate must
   carry a measured watermark, an owner and a `review_by`. CI then asks *"is
   anything red that we did not already record, or REDDER than we recorded?"*
   instead of *"is anything red?"* — which was constant and therefore no signal.
   A GREEN gate still listed is also a failure (stale entry).
3. **`navalai/gaps.py` + `scripts/reconcile_gaps.py`** — findings as work items
   with a legal state machine, reconciled against the code. The queue is a
   **cache**: the code is the truth, and drift is printed.
4. **`pipeline.JsonlLog`** — append-only; `LogTruncated` raises if the file
   shrank, because something rewrote history.

`.github/workflows/gates.yml` judges against the ledger, and `.githooks/pre-push`
refuses a push on a failing suite or a newly-red gate.

## 8 · The seams

A seam is where something untrusted meets something trusted. There are three,
and each is one-directional.

- **LLM seam** (`translate.sanitize`) — natural language in, typed
  `MissionSpec` out. Clamped ranges, whitelisted strings, category ratchets one
  way. Nothing beyond it can author geometry.
- **Policy seam** (BuildPlan 3, unbuilt) — the constitution compiles to bounds
  and constraint rows. Its structural test: **delete the constitution and every
  physics result must be bit-identical.**
- **Human seam** — REVIEW-GATED work (Gate 6R clause parity). Rules output is
  an assessment aid; a qualified human, not the platform, certifies.

## 9 · Measured state — SUPERSEDED, do not read numbers from here

**This table is retired 2026-08-11.** It was a second copy of a state the
runners already own, taken on a branch (`worktree-gap-closure`) that no longer
exists — so the provenance of every number in it points at nothing. Three of its
six rows had gone stale within four days.

**Status now comes from the commands, not from this file:**

```
python -m navalai.gates            # gates + the ledger
python scripts/reconcile_gaps.py   # the 119-row register, derived from code
python -m pytest tests/ -q         # the suite
```

`docs/ROADMAP.md` §2 carries a dated baseline with the command beside each
number, and §3 the ordered open-work list. What the retired table got wrong,
recorded so the correction is reviewable in a diff rather than silently
overwritten:

- **Gate 7 "RED and NOT in the ledger — a new break"** — superseded by
  `56e8c1d`, which **withdrew** the Gate 7 entry deliberately and recorded why:
  the ledger holds *declared* RED rows, not suite-failing ones. A gate failing
  its own suite is already loud. The ledger's four keys (2M, 2U, 4F, 6R) are
  correct and are enforced in both directions by
  `test_every_red_gate_has_a_ledger_entry_and_vice_versa`.
- **"94 closed, 23 open"** — measured 2026-08-11: **97 closed, 20 open,
  0 needs-human, 2 retired**.
- **"13 rows of queue-vs-code drift"** — not a defect. `data/evolution/gaps.jsonl`
  is a gitignored cache holding all rows `Open`; gap state is *derived* by
  `reconcile_gaps.py`, never read from the log.
- **E2 is CLOSED** (`d342b8b`) — `benchmarks/wigley.py` now carries
  `rw_analytic`, a closed-form Michell solution, so the anchor is no longer made
  of our own output. **F1 remains genuinely open and is the one CRITICAL row**:
  no added-resistance-in-waves routine exists in `seakeeping.py`, and there is
  no gate row for it.

## 10 · What is not built

Stated plainly so no reader infers otherwise from the plans:

- **BuildPlan 2:** V2.0 refdata spine is **done** (Gate V2.0). V2.2 tier E and
  V2.4 tier F are **partial** — `rules/ergonomics.assess` covers deck/seat only,
  and `refdata/flotation` exposes `submerged_factor` but no flotation solver.
  ~~V2.1 arrangement grammar ... do not exist (`navalai/arrangement.py` is
  absent).~~ **CORRECTED 2026-08-11:** `navalai/arrangement.py` is **1484 lines**
  and `Gate V2.1` is registered against `tests/test_arrangement.py` (landed
  `87719cf`). V2.3, V2.5 and V2.6 have no code **and no gate row** — their bars
  live only in prose; see `docs/ROADMAP.md` §4.6.
- **BuildPlan 3:** ~~**nothing.** No `policy/` ... module exists.~~
  **CORRECTED 2026-08-11:** `navalai/policy/` is five files and `Gate V3.0` is
  registered against `tests/test_policy.py` (landed `ded4dbf`, `487ec52`). It is
  consumed in production by `optimize.py` (parameter box + constraint rows) and
  `evaluate.py` (`extra_names`). `component/`, `bom/`, `procurement/` and
  `twin/` remain plan only.

  These two rows were false in the same direction, and the identical claim also
  stood in `README.md`, `docs/STAGE-PLAN.md` and `PLM.md` — four copies of one
  state, none regenerated. README contradicted itself inside one file, because
  its gate table is GENERATED and its prose is not. That is the whole argument
  for `docs/ROADMAP.md`.
- **The ladder's top:** Gate 2M has **no reproducible measurement at all** —
  its watermark is the string `NONE` because the run directory that carried the
  old figure was deleted. L3 is read from recorded evidence and never solved
  in-process, which is correct, but there is currently no evidence to read.

## 11 · Repository topology — RESOLVED, section removed

This section described a four-branch split and a mid-merge with 40 unresolved
conflicts, **in the present tense**, as "currently the top risk". It was resolved
on 2026-08-07 by Stage 0 of `docs/STAGE-PLAN.md`, whose closure note is the
correct home for the history.

**Measured 2026-08-11 at `b5002be`:** `git branch` shows `master` only. No
`.git/MERGE_HEAD`. One worktree.

Removed rather than updated because a design document should not carry a
schedule item at all — that belongs to `docs/ROADMAP.md`. Kept as this stub
rather than deleted outright because PLM §3 step 7 requires a superseded item to
be removed **with a note, never left ambiguous**, and because a reader who
remembers the old §11 needs to find out here that it ended.

Two remote refs, `origin/apse` and `origin/worktree-apse`, still appear in
`git branch -r`. Whether they are live upstream or stale tracking refs needs
`git fetch --prune`, which has not been run.
