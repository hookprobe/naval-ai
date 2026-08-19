# NavalAI — THE BUILD PLAN

> **Role: SYSTEM PLAN.** What the system is, how it is put together, what is
> built next, in what order, and why. One document, one plan.
>
> **It states no status.** No gate colours, no test counts, no register
> tallies — those go stale between the writing and the reading, and this
> project has paid for that four times. Status comes only from the commands:
>
> ```
> python -m navalai.gates                 # gates + the expected-red ledger
> python scripts/reconcile_gaps.py        # the work queue, derived from code
> python -m pytest tests/ -q              # the suite
> ```
>
> What it *does* carry: **bars** (a bar is a requirement, not a status) and
> **dated measurements that justify a decision**. Every such measurement names
> its date and the thing it was measured on. Research and evidence live in
> `docs/research/`; this file references them and does not restate them.
>
> Restructured 2026-08-11 from a file that was twelve documents concatenated
> with `cat` — 279 KB, five mechanical PARTS, the same finding stated in four of
> them, and retired plans sitting inside it at full length.

---

## 0 · Document map — one authority role each

Consolidation is not one file. It is **one authority per question**, so that no
two documents can disagree about the same thing.

| Document | Authority for | Must NOT contain |
|---|---|---|
| **`docs/BUILD-PLAN.md`** (this file) | **SYSTEM PLAN** — the architecture, the order, the dependencies, the owners, the bars a new gate must meet | status of any kind; research it is not the only home of; a restated measurement |
| **`docs/GAP-REGISTER.md`** | **WORK QUEUE** — the dated audit findings, parsed by `navalai/gaps.py` into work items | anything with no predicate; forward plan; edits (it is an immutable audit record — its tables must never be restructured) |
| **`docs/LESSONS.md`** | **ENGINEERING MEMORY** — what was learned the hard way and is not recoverable from the code, the tests or `git log` | anything a predicate could answer; mesh operating lore (that is `CLAUDE.md`) |
| **`CLAUDE.md`** | **AGENT RULES** — paths, git law, house style, CFD operating lore for the Mac node | roadmap; status; a measurement it is not the only home of |
| **`PLM.md` §1–§4** | **PLATFORM LAW** — the shared kernel, the product lines, the lifecycle, the roles | gates, status, roadmap, or any restated bar (all narrowed out 2026-08-11) |
| **`docs/research/*`**, `docs/GATE-6R-REVIEW.md` | **RESEARCH / EVIDENCE** — dated measurement records, literature, sourced constants, refutations | any forward plan; any gate verdict |
| **`README.md`** gate table | **GENERATED** — regenerated from `navalai/gates.py` by `python -m navalai.gates --readme --write` | a hand edit. A hand-maintained copy of a generated table is the defect it exists to prevent |
| `navalai/gates.py` + `data/gate-ledger.json` | **THE STATUS** | prose verdicts |
| `navalai/experiments.py` (Gate 0X), run by `python -m navalai.experiments` | **THE HYDRODYNAMIC MEASUREMENT SUITE** — the controlled sweeps behind the 2026-08-13 findings (lever comparison, bow sharpness, catamaran separation, the Michell phase convention). It is CODE, so it re-measures on demand instead of ageing | a plan, an order, or a verdict about anything it did not sweep |
| `ALIGNMENT.md`, `MACBOOK.md` | the original-plan audit; the Mac runbook. Both are read by `scripts/reconcile_gaps.py` predicates | — |

**The law this table encodes, which is the existing law one level up:**

> A number lives in exactly one place. **So does a work item.**
> No work item may exist only in prose.

Every item is a gap with a predicate, a gate with a bar, or a recorded
retirement. §15.2 is the list of things that currently satisfy none of the
three, and closing it is P0 work.

### Where the old content went

The five mechanical PARTS of the concatenated file, and the twelve documents
before them, resolve as follows. Citations elsewhere in the tree that name a
Part or an old filename should be read through this table.

| Old location | Now |
|---|---|
| Part I (the plan) | this file, §15–§17 |
| Part II (SELL·BUILD·RUN + WindWing) | this file, §3–§10, §13; research in `docs/research/WINDWING.md` and `docs/research/PRIOR-ART.md` |
| Part III (architecture, was `HLD.md`) | this file, §2 |
| Part IV.a (pressure oscillation) | `docs/research/CFD.md` §1–§2 |
| Part IV.b (APSE) | `docs/research/APSE.md` |
| Part IV.c (end-to-end audit) | this file, §4 |
| Part V.a (BuildPlan 1) | research → `docs/research/PRIOR-ART.md`; bars → §15.3 and `navalai/gates.py` |
| Part V.b (BuildPlan 2) | research → `docs/research/ARRANGEMENT.md` and `docs/research/COMPLIANCE.md`; bars → §15.3 |
| Part V.c (BuildPlan 3) | governance → §9; regulation → `docs/research/COMPLIANCE.md`; catalog/market → `docs/research/PRIOR-ART.md`; bars → §15.3 |
| Part V.d (gap closure, R0–R8) | eliminations → `docs/research/CFD.md` §3; the rest is landed or in §16 |
| Part V.e (stage plan, S0–S7) | §17 (dependencies) |
| Part V.f (CFD blocker brief) | `docs/research/CFD.md` §4 |
| `docs/VESSEL-KERNEL-DIRECTION.md` (2026-08-13, deleted) | thesis → §1.5; ordering and work items → §16 "PV"; anchor candidate → §11.4; unaccounted debts → §15.2 items 8–9. Its measurements were NOT copied here: they live in `navalai/experiments.py`, `docs/research/HULL-FORM-RULES.md` and `docs/research/HULL-GAN-PAPERS.md`. **Several of its premises were stale against the code and are corrected at the point of absorption — see §16's "already built" table** |

---

## 1 · Vision

**A non-expert states a mission in natural language, and the platform returns a
vessel design that has passed a tiered physics-and-rules validation ladder, with
every number carrying the tier and uncertainty that produced it, ending in
build-ready manufacturing output — and then keeps learning from the boat once it
is in the water.**

What makes it different from a CAD tool is not the geometry kernel. It is that
**nothing may claim more confidence than its evidence supports**, and that this
is enforced by executable gates rather than by discipline.

### 1.1 The product, and the loop that closes it

SELL discovers the mission, BUILD produces a physically validated vessel, RUN
operates it and generates evidence, and that evidence returns to BUILD.

```
                         NAVALAI
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
      SELL                 BUILD                 RUN
       │                    │                    │
    Mission             Geometry              Sensors
    Governance          Physics               Navigation
    Feasibility         CFD                   Energy
    Concepts            AI/ML                 Propulsion
    Cost                Ergonomics            WindWing
    Regulatory          Manufacturing         Safety
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                       EVIDENCE GRAPH
                            │
                       DIGITAL TWIN
                            │
                       FLEET LEARNING
                            │
                            └──────► BUILD

                     ─────────────────
                     HookProbeOS
                         + HEQK
                     ─────────────────
```

Read the spine bottom-up, because that is the order the work has to land in.
**EVIDENCE GRAPH** is `evidence.EvidenceGraph` — built, well-designed, and
populated by nothing but a demo with six hand-typed strings. **DIGITAL TWIN**
and **FLEET LEARNING** do not exist. **HookProbeOS + HEQK** is the substrate the
whole column would run on, and it has not been read — §13 is a requirement list,
not a finding.

Of the three columns, **BUILD is largely real**, **SELL is half-real** (mission
and governance ship; feasibility, concepts, cost and the regulatory surface do
not), and **RUN is entirely absent**.

### 1.2 The five laws

Not style preferences. Each was written after a measured incident, and each has
a test that fails if it is violated.

| # | Law | Enforcement | The incident |
|---|---|---|---|
| 1 | Every quantity carries `{value, tier, sigma}` | `Evaluation.badges`, `ui/server._q` | bare floats presented L1 guesses as fact |
| 2 | A number lives in exactly one place | `navalai/limits.py`, Gate L | the GM floor drifted 0.35 vs 0.45 across four files; NSGA-II optimised to its own bar and the rules gate then rejected the winner |
| 3 | LLMs translate and explain; they have **no code path to geometry** | Gate 5, `translate.sanitize` | an LLM returning `{"design_category":"D"}` on an ocean brief relaxed a stability bar 42% silently |
| 4 | A failing gate is information; never soften a bar | `data/gate-ledger.json` | a constant-red CI is not a signal |
| 5 | Policy/mission may only **ratchet a gate tighter** | `translate.py` `min()` on category | see law 3 |

Law 5 is the one governance generalises from missions to a constitution (§9).

### 1.3 The thesis: the flywheel is closed on itself

This is the finding that orders everything below it.

`flywheel.harvest()` draws random grammar vectors via `sample_valid()`, runs
`evaluate()` on each, and trains the surrogate on the resulting **L1 rows**. The
frozen deployment benchmark it must not regress against is **also** generated by
`evaluate()`. The module is admirably honest about it: the benchmark probes are
not the benchmark hulls, "their truth is our own L1, never the tank data", and
only proportion transfers.

So the learning loop is: **our physics teaches a surrogate to imitate our
physics, and we measure the imitation.** The gating around it is genuinely
strong — a monotone high-water ratchet, absolute floors that bind on bootstrap,
a suite fingerprint so a mark cannot be carried across two benchmarks, a missing
baseline treated as a refusal rather than a pass. None of it can discover that
the physics is wrong.

Count the predicted-vs-observed comparisons in the repository:

| # | Predicted | "Observed" | Against reality? |
|---|---|---|---|
| 1 | L1 Michell/ITTC-57 | recorded L3 RANS drag | no — sim vs sim |
| 2 | GP surrogate | the ladder's own L1 | no — sim vs sim |
| 3 | recomputed Michell Cw | `benchmarks/wigley.rw_analytic` | now a closed-form solution, no longer our own frozen output |
| 4 | our CFD C_T | KRISO EFD | **yes** — and a human runs it by hand |

**One of four touches a physical measurement, it is a containership tank test
run manually, and its gate is recorded RED.** That is the argument for
SELL·BUILD·RUN, and it is stronger than an architecture preference:

> **RUN is the only available source of an observation that NavalAI did not
> generate itself.**

Not autonomy. Not a nicer autopilot. *Evidence.* Every hour a delivered vessel
operates is a measurement of the L1 model at a condition no tank test covers, on
the exact hull family the SKUs ship. Airseas is the cautionary case in public:
modelling and land tests projected **20%** fuel saving; the sea-trial projection
came back **16%**. That 4-point gap is precisely the quantity a closed loop
exists to find, and precisely the quantity a closed-on-itself flywheel cannot.

### 1.4 Scope, and where the moat is

**Scope is yachts and small boats**: 4–24 m plywood-native recreational craft
under RCD 2013/53/EU and ISO 12217/12215, sold to an owner and cut on a CNC
kit-cutter. Topside design — windows, standing headroom, hard-chine topsides
that are not developable — is DEFERRED by decision: fix the simulation model
first.

The competitive reading is in `docs/research/PRIOR-ART.md` §7 and its conclusion
is short: **do not compete on generative hull modelling.** The nearest
competitor trains on 52 591 validated real designs with Siemens, NVIDIA and a
government-funded consortium behind them; that fight is lost before it starts
and winning it would not differentiate the product.

Compete where the segment and the lifecycle differ:

- **Segment.** They design 32.5 m commercial vessels under class and SOLAS.
  Developable-panel manufacturability is a constraint their generative model has
  no reason to carry.
- **Lifecycle.** SELL and RUN, which they explicitly do not do.
- **Evidence.** The honesty machinery, and eventually a fleet of instrumented
  hulls — the one asset a competitor cannot buy, and the one that answers the
  second-benchmark-anchor debt.

**Where this project is genuinely ahead:** typed gate statuses with a committed
ledger; red-by-record so a miss cannot be edited away in prose; tier badges that
cannot be promoted by comparison; an OOD-refusing surrogate; a ratchet that
rejects a policy floor merely *equal* to a limit; a rules tier that refuses
out-of-scope verdicts rather than producing them. That combination is harder to
copy than physics, because it is a culture encoded as tests.

**Where it is behind, and it must be said:** the physics is weaker than the
incumbents today. Seakeeping is heave-only. There is no 6-DOF model. The
resistance model is Michell + ITTC-57 + Holtrop, all textbook, and valid only to
Fn ≈ 0.45. The second benchmark anchor the SKUs actually need is owed. A NAPA
user would be right to point at all of it.

**So the moat is not "better simulation."** It is (a) the honesty machinery,
(b) mission → quote → build → operate as one governed chain, and (c) if RUN
lands, a fleet of instrumented hulls in the SKU family.

### 1.5 The vessel kernel — inverse design, not generate-then-measure

Absorbed 2026-08-13 from the project owner's direction note (which is deleted;
§0's migration table records where each of its parts went).

> NavalAI is a **performance-constrained inverse-design system that generates a
> buildable vessel from mission requirements** — not a hull generator that
> measures what it happened to produce.

**This is a sharpening of §1.4, not a replacement of it.** The differentiator is
NOT that the tools do not exist: CAD, hydrostatics, resistance codes and CFD all
exist and are better than ours (§1.4, "where it is behind"). It is that **no
accessible integrated physics-aware workflow takes a MISSION to a safe,
efficient, structurally realisable vessel with a traceable evidence trail.** The
evidence trail is the thing this repository is already unusually good at, and
the direction treats it as the moat rather than as overhead — which is the same
conclusion §1.4 reached from the competitive side.

**The kernel already runs in the inverse direction where it matters most, and
that is a measurement rather than an aspiration.** `geometry.py`'s parametrisation
was inverted on 2026-08-13: `Cp` and `lcb` are genes the sectional-area curve is
SOLVED to deliver (`geometry.sac_exponents`), not emergent outputs of unrelated
shape knobs. The before/after and the acceptance bar are in
`tests/test_geometry_kernel.py::test_the_kernel_delivers_the_prismatic_and_lcb_it_was_asked_for`
and in `navalai/geometry.py`'s module docstring; they are not restated here.

**Two canonical end-to-end cases** are the direction's acceptance shape, and
they are chosen because they exercise different halves of the platform:

| Case | What it forces that the other does not |
|---|---|
| **A solar recreational vessel** | PV area as the binding constraint (§16 P2), standing headroom and interior (§16 P6), RCD/ISO scope (§16 P7), and the slender-demihull stability problem the objective keeps meeting (PV-1) |
| **An autonomous marine drone** | no crew and therefore no ergonomics floor, a payload rather than a passenger mass model, RUN as a first-class consumer (§16 P8), and a regulatory frame that is **not** the RCD — which this tree does not model and must not assume |

**Neither case is scheduled as a phase, and deliberately.** A canonical case is
an ACCEPTANCE ARTIFACT: it is the end-to-end run that proves the phases below
compose. Filing it as work would put a second copy of every phase's content in
one row. What it does change is §16's ordering rule, extended by one clause:

> Anything that makes the machinery lie comes before anything that uses the
> machinery — **and a vessel-level quantity the ladder does not model at all
> ranks with the lies, not with the improvements.** A monohull stability floor
> applied to a demihull, and a catamaran scored as one isolated demihull, are
> the same defect class as `gate2m.py` printing KCS's EFD figure over a Wigley
> hull. The number is not imprecise; it is a number for a different vessel.

**The drone case also names a scope hole this file did not have.** §1.4 scopes
the product to "4–24 m plywood-native recreational craft under RCD 2013/53/EU
and ISO 12217/12215", and the whole rules tier is written to that frame. Whether
an uncrewed vessel falls inside the RCD's subject matter at all is **UNVERIFIED**
— `docs/research/EU-REGULATORY.md` records only the adjacent negative result,
that ES-TRIN 2025/1 has zero hits for any autonomous provision — and
`navalai/rules/` has no second frame to fall back on. So: **the drone case may
be run for PHYSICS and must not be run for a compliance verdict** until the
frame is established. The determination itself is §16 P7's scope work, where
`rules/review.py`'s own law applies — a rule missing from both `confirmed` and
`unconfirmed` is an oversight, a rule present in one is a decision.

---

## 2 · System architecture

### 2.1 The two axes people confuse

The single most important structural idea in the system.

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
   E   ergonomics          F   flotation/survivability
   W0–W3  wind traction (§10)      S1  surrogate — deliberately outside TIER_ORDER
```

A stage may only advance when the tier that stage requires has actually been
reached. `Stage.MESHING` without `Stage.HYDROSTATICS` is a defect with a compute
bill attached — which is why `pipeline.transition` **raises** rather than
returning `False`: a caller that ignores a `False` keeps going.

A surrogate answer at tier `S1` can never satisfy a ladder-tier requirement
because `tier_rank("S1")` is −1. That trick is reused wherever a claim must not
be able to outrun its evidence (§5.2, §7).

### 2.2 The layer model

One diagram, replacing two that said the same thing in different words. The
right column is what exists, measured 2026-08-11 at `b5002be` — a dated reading,
not a status; re-derive it from the code before relying on it.

```
   Human intent (one sentence)
        ▼
   MISSION INTELLIGENCE   feasibility verdict + owed unknowns        not built
        ▼
   GOVERNANCE             legal envelope · design DNA                built
     compiles to ↓ (never runs beside)
     ├─ parameter-space box  (bounds the search)
     └─ constraint rows      (into evaluate.g)
        ▼
   ENGINEERING INTELLIGENCE  component models · compatibility        not built
        ▼
   PHYSICS & OPTIMIZATION   L0·L1·L2·L3·R (+E partial, F partial)    built
        ▼
   PROCUREMENT              BOM · closure · quotes                   partial (BomLine)
        ▼
   MANUFACTURING            nest · DXF · refold · receipt            built
        ▼
   DIGITAL TWIN → FLEET LEARNING                                     not built
        ▼
   EVIDENCE GRAPH  (db.py content-addressed, append-only)            built
                   (evidence.EvidenceGraph: built, UNPOPULATED)
```

**The engine is the finished part.** Everything above and below it is where the
work is.

### 2.3 Data contracts

Six types carry the whole system. Each exists once.

| Contract | Home | Rule |
|---|---|---|
| `Quantity {value, tier, sigma}` | `Evaluation.badges` | law 1; no bare numbers cross a layer |
| `RefValue {value, source, basis}` | `navalai/refdata/` | `basis ∈ {standard, approx, purchased}`; no source, no constant |
| `Genome` | `pipeline.py` | content-addressed; a hull is named by its own contents |
| `MassItem → aggregate` | `weights.py` | **one** positioned mass model; LCG/TCG/VCG derive from it |
| `Evaluation.g` | `evaluate.py` | **one** inequality vector; `≤ 0` is feasible; NSGA-II consumes it directly |
| `Gap {id, severity, state}` | `gaps.py` | a finding is a work item with a legal state machine, not prose |

The `Evaluation.g` rule is load-bearing: **adding a check to `evaluate()`
constrains the optimizer automatically.** That is why governance must compile
*into* this vector rather than run beside it — a second constraint engine is a
second place a limit is written down, i.e. a law-2 violation at platform scale.

`CONSTRAINT_NAMES` is one tuple: `(freeboard, gm, bend_radius, trim, list, lcb,
proportions, rules)`. `constraint_vector()` raises a real exception — not an
`assert`, because `python -O` strips those — on any missing, extra or duplicate
key.

**Where a bar lives is decided, not incidental.** `limits.py` owns **design and
rule** bars. **Model-validity envelopes deliberately live beside their models**
(`FN_MICHELL_MAX` in `resistance.py`, `SCOPE_MIN_HULL_LENGTH_M` in
`rules/iso12217.py`, `L2_MESHES` in `seakeeping.py`). Treating `limits.py` as
the home for *all* bars would separate a bar from the model that gives it
meaning.

### 2.4 The seams

A seam is where something untrusted meets something trusted. There are three,
and each is one-directional.

- **LLM seam** (`translate.sanitize`) — natural language in, typed `MissionSpec`
  out. Clamped ranges, whitelisted strings, category ratchets one way. Nothing
  beyond it can author geometry.
- **Policy seam** — the constitution compiles to bounds and constraint rows. Its
  structural test: **delete the constitution and every physics result must be
  bit-identical.**
- **Human seam** — REVIEW-GATED work (clause parity). Rules output is an
  assessment aid; a qualified human, not the platform, certifies.

### 2.5 The enforcement mesh

Four independent mechanisms, deliberately not sharing an owner with what they
check:

1. **`navalai/gates.py`** — the gate ladder. `Verdict` is a typed status;
   `Gate.__post_init__` rejects anything else, so a RED cannot be erased by
   renaming a string. Gate 0G asserts **every test file is owned by a gate**.
2. **`data/gate-ledger.json`** — the expected-RED ledger. Each RED gate carries
   a measured watermark, an owner and a `review_by`. CI asks *"is anything red
   that we did not already record, or REDDER than we recorded?"* instead of *"is
   anything red?"* — which was constant and therefore no signal. A GREEN gate
   still listed is also a failure.
3. **`navalai/gaps.py` + `scripts/reconcile_gaps.py`** — findings as work items
   with a legal state machine, reconciled against the code. The queue is a
   **cache**: the code is the truth, and drift is printed.
4. **`pipeline.JsonlLog`** — append-only; `LogTruncated` raises if the file
   shrank, because something rewrote history.

`.github/workflows/gates.yml` judges against the ledger, and `.githooks/pre-push`
refuses a push on a failing suite or a newly-red gate.

### 2.6 The contract this architecture is missing: there is no VESSEL

Recorded 2026-08-13, verified by grep, because it is a structural gap rather
than a defect in any one module and §16 PV is built on it.

**Every contract in §2.3 describes a HULL.** `Genome` is one parameter vector,
`Hull` is one lofted surface, `hydrostatics.solve` floats one of them, and
`CONSTRAINT_NAMES` measures one of them. **The word `separation` appears in
`navalai/grammar.py`, `navalai/mission.py`, `navalai/limits.py` and
`navalai/evaluate.py` exactly zero times**, and so does any hull count.

The consequence is not that catamarans are computed badly. It is that **a
catamaran cannot be expressed**, and the ladder therefore answers a question
about a different vessel without any mechanism able to notice:

- `resistance.michell_rw` accepts `separation` and is verified for it, and the
  single production caller cannot supply one (PV-2).
- `hydrostatics` has no transverse-separation term at all, so `limits.gm_floor`
  — a MONOHULL floor — is applied to what the brief intends as a demihull
  (PV-1).

**The fix is a contract, not a formula.** A seventh row belongs in §2.3's table:
a vessel-level descriptor that says how many hulls there are and where they are,
sitting between `Genome` and `Hull`, read by `hydrostatics` and `resistance`
through the SAME value — because the alternative is a separation declared once
for stability and once for resistance, which is law 2 at platform scale and the
exact defect §2.3 exists to prevent. It is deliberately NOT specified here:
specifying it is PV-1's first act, and a plan that designs the type before the
physics needs it would be writing the code in prose.

---

## 3 · SELL — mission intelligence, the contract, and the quote

The ask is "simple, streamlined, easy to use." The answer is not a better chat
interface. It is **three artifacts and one identity chain** (§6.2). SELL owns
the first artifact.

**Measured 2026-08-11 at `b5002be`, by reading the code**, because the design
below is a response to specific absences:

| Claim | State |
|---|---|
| A mission specification exists | **YES.** `mission.MissionSpec`, 9 fields |
| It is validated | **YES.** `clamp()` against `FIELD_RANGES`/`ENERGY_RANGES`, idempotent, rejects NaN/inf, records every clamp into `notes` |
| It is a *frozen contract* with provenance | **NO.** Not `frozen=True`; both `parse_mission` and `translate.sanitize` mutate by `setattr` after construction. **No hash, no id, no timestamp, no version.** `db.hull_id` content-addresses *geometry*; nothing addresses the mission that asked for it |
| The LLM has no code path to geometry | **YES, structurally** — geometry parameters are not fields of `MissionSpec`. The design-category ratchet lets an LLM only tighten a category |
| …and it is tested | **WEAKLY.** The nearest test asserts *name disjointness* between `MissionSpec` fields and `grammar.NAMES`. That is not a data-flow proof; it would pass if someone added a field a downstream caller decoded into a genome |
| Governance decides the admissible space | **YES, inside `evaluate`/`optimize`** |
| …and the customer sees it | **NO.** Importers of `navalai.policy` are `evaluate.py`, `optimize.py` and tests. `legal.py` computes the RCD Article 20 delivery route — and renders it to nobody |
| Feasibility negotiation | **ABSENT, not partial.** `translate.grade()` returns a PASS/FAIL list. Nothing ranks the failures, names the binding one, or proposes a relaxation |
| Competing concepts A/B/C/D | **NO.** The nearest thing is the NSGA-II front, unlabelled and uncosted |
| Any notion of money | **NONE.** Every "cost" in the package is CPU-seconds or a physical quantity. `BomLine` has no price field and no currency |
| An autonomous planner | **NOT WHAT THE NAME SUGGESTS.** `planner.py` plans *which rung of the ladder to run next*. It never sees a `MissionSpec`, a customer, or money |

### 3.1 The Mission Contract — freeze it and hash it

`MissionSpec` becomes `frozen=True` and gains `schema_version`, `created_utc`,
and `mission_id = sha256(canonical_json)` using the same canonicalisation `db.py`
already applies to parameter vectors. Mutation moves to `replace()`-style
returns, so `parse_mission` and `sanitize` compose instead of `setattr`-ing.

Why this is first, and why it is not bureaucracy: **you cannot compute a
predicted-vs-observed delta without knowing which promise was made.** A delta
engine (§8.1) needs to join an observation to the mission that specified it. The
chain is broken at the SELL end today, and it is the cheapest break to fix.

The clamp `notes` stay but stop being the provenance channel — deciding anything
by regexing that sentence "would make the row FAIL OPEN the day the wording
changes". Clamps become structured records on the contract.

**Bar (Gate M1, new):** `MissionSpec` is frozen; two textually different briefs
with identical semantics hash identically; any mutation attempt raises.

### 3.2 Feasibility negotiation is nearly free, because `Evaluation.g` exists

The most valuable thing in this section, and it needs almost no new machinery.
`Evaluation.g` is already *the one* inequality vector — ordered, complete,
finite-checked, and consumed directly by NSGA-II. A negotiation engine is a thin
layer over it:

- **The binding constraint** is `argmax(g_i)` over the infeasible set. That is
  the sentence "your 9 kn cruise is what is blocking you", computed rather than
  reasoned about.
- **The trade** is the sensitivity of the objective to relaxing a *requirement*
  — a shadow price. For the mission fields that enter as targets
  (`cruise_speed_kn`, `displacement_target_kg`, `lwl_hint_m`,
  `energy.battery_kwh`), a finite-difference re-solve at ±Δ gives
  ∂(objective)/∂(requirement) directly. At NSGA-II budgets already in use
  (pop 24 / gens 10 ≈ 1.2 s) a 4-field sensitivity sweep is seconds.
- **The output** is one ranked sentence per binding constraint with a number
  attached: *"cruise 9 kn → 7.5 kn recovers feasibility and saves €X"*.

Two rules it inherits, both already house law:

1. **Never relax a bar to make it pass.** The negotiator proposes changing the
   *mission*, never the *limit*. The policy ratchet already encodes the
   direction of legitimate movement.
2. **A refusal must name what it refused.** `translate.grade()` already
   separates "broken checker" from "failed design". The negotiator must preserve
   that distinction or it will report a crashed constraint as an infeasible
   customer.

**Bar (Gate N1, new):** on a deliberately infeasible mission the named binding
constraint is the true argmax of `g`, and the proposal changes the mission,
never a limit.

### 3.3 The quote — money carries a tier, like every other quantity

There is no money in the codebase, so this is greenfield and can be built right
the first time. The design falls out of law 1 and out of the shape
`policy/base.PolicyValue` already uses (which requires `source` to be at least
20 characters — a small, effective anti-handwave device):

```
PriceValue(value, currency, tier, source, quoted_on, sigma, note)
  tier ∈ ('quoted',    # a named supplier quote, with a date
          'listed',    # a public price list, with a URL and a date
          'estimated', # parametric, from build_hours / area / mass
          )
```

Rules, each with a test that feeds it the input it must reject:

- **A price with no tier is refused**, exactly as an unmeasurable mesh metric is
  fatal rather than defaulted to 0. There is no default currency and no default
  price.
- **A quote has an expiry.** A `quoted` price older than its validity window
  degrades to `estimated` with the sigma that implies — a silently expired quote
  is the money version of a layer table printing the requested spec as achieved.
- **Total cost carries a sigma**, aggregated in quadrature, and the quote states
  it. `engineer.EngineerReport` already produces the physical quantities
  (`ply_sheets`, `epoxy_kg`, `build_hours`, `nest_utilisation`); the missing half
  is the price.
- **Cost closure** is a first-class metric (§12.2). A quote that is 30% closed is
  a different product from one that is 95% closed, and the customer is told
  which they have.

**Bars (Gates Q1, Q2, new):** a price with no tier is REFUSED; an expired
`quoted` price degrades and its sigma grows; every `BomLine` is priced or
explicitly `absent()`; a 0%-closed quote cannot be presented as a quote.

### 3.4 Concepts A/B/C/D

These are the Pareto front, labelled and costed. Two things are needed: attach
`PriceValue` totals, and name the concepts by what distinguishes them rather
than by index. (The third — making `GET /pareto` answer the **caller's** mission
rather than a module default — was the front being keyed on a mission no caller
could pass, i.e. a customer shown the trade-off surface of somebody else's
boat.) The explanatory sentence the customer reads
("Concept C is the best engineering solution; B gives more peak traction but
larger roll moments…") is an LLM *reading* the computed front — exactly what
law 3 permits: translate and explain, never compute.

### 3.5 Surface the governance answer

`policy/legal.py` already computes the delivery route with articles and the
five-year clause verbatim, and already records where the plan that specified it
was wrong about category D rather than silently fixing it.
`AiActConsequence.high_risk` is deliberately always `None` because limb (a) is a
legal judgement the project refuses to make — that abstention is a feature and
must survive to the customer surface.

**Rendering this is zero new physics and it is the single most differentiating
thing SELL could show.** No competitor tells a customer, at concept stage, "this
configuration requires a notified body, here is the article." The regulation
itself is `docs/research/COMPLIANCE.md` §1.

---

## 4 · BUILD — and the defect at its centre

BUILD is the most complete of the three engines, and it has one structural
defect that costs more than everything else in this section.

### 4.1 There are two lifecycles and only one of them runs

**MEASURED 2026-08-07, re-verified 2026-08-11.**

| | `navalai/agents.py` | `navalai/pipeline.py` |
|---|---|---|
| Role | **the actual driver** | **the documented spine** |
| Entry | `run_plm(mission_text, n_designs, batch)` | `Pipeline` |
| States | 4 informal strings: `candidate` / `validated` / `rejected` / `engineered` | 11 typed `Stage` + 7 `Terminal` |
| Transition guard | none | forward-only; illegal edges **raise** `IllegalTransition` |
| Terminal uniqueness | not enforced | exactly one per genome, enforced |
| Archive | in-memory `Audit` | append-only `JsonlLog`, `LogTruncated` if the file shrinks |
| Unmeasured metric | not modelled | `Unmeasurable` — a guard with no evidence refuses |
| Reaches manufacturing | **yes** (`engineer` → `unroll`: panels, nest, BOM) | n/a |
| Production callers | it *is* the entry point | **ZERO** |

**`Stage.` does not appear anywhere in `navalai/`, `scripts/` or `ui/` outside
`pipeline.py` itself.** The only production imports of `navalai.pipeline` take
`JsonlLog` (a logging utility, reused by `gaps.py`) — never the lifecycle.

```
                        NAVALAI
                           │
                  ┌────────┴────────┐
                  ▼                 ▼
              agents.py         pipeline.py
              REAL FLOW         DOCUMENTED FLOW
                  │                 │
                  ▼                 ▼
             manufacturing     guarantees
```

**Why this is not cosmetic.** The properties `pipeline.py` exists to guarantee
are exactly the ones `agents.py` cannot offer:

- `agents.py` can emit `engineered` for a design with **no equivalent of
  `HYDROSTATICS` having succeeded**, because there is no transition graph — a
  hull with no floated state, with a manufacturing BOM attached.
- A failure in `agents.py` is a `rejected` message with free text. In
  `pipeline.py` a non-`SUCCESS` terminal **requires a reason** or the transition
  raises, because "a failure with no reason is a genome abandoned with
  paperwork".
- `Audit` is in-memory and dies with the process.

**So the product's real flow is the one with none of the guarantees, and the
guarantees are all in the flow nothing calls.**

### 4.2 The fix is wiring, not a rewrite

Both halves exist and are tested. `agents.py` stops being a parallel lifecycle
and becomes the orchestration layer *above* the spine, so the guarantees apply
to the flow that actually ships.

```
                      pipeline.py
                          ▲
                          │
                     agents.py
                     becomes
                   orchestration
```

The four kinds map on without inventing a state:

```
 _builder    emits 'candidate'  ->  Stage.NEW -> GENERATING
 _validator  emits 'validated'  ->  VALIDATING -> HYDROSTATICS  (or a Terminal
             emits 'rejected'   ->  FAILED_GEOMETRY / FAILED_HYDROSTATICS, WITH a reason)
 _engineer   emits 'engineered' ->  MANUFACTURING -> SCORING -> ARCHIVED -> SUCCESS
```

The stages `agents.py` has no step for (MESHING, CFD, SEA_STATE, ERGONOMICS) are
the ones that are compute-bound or unbuilt — and a genome that has not reached
them should say so *through the spine* rather than skip silently to
`engineered`. It converts the spine's gate from a gate on unused code into a
gate on the product.

### 4.3 Two more BUILD changes, in order

1. **Populate `EvidenceGraph` from `evaluate()` + `db.Provenance`** (§6).
2. **Extend badges, or stop claiming law 1.** `Evaluation.badges` carries
   `(tier, sigma, basis)` for exactly `displacement`, `GM`, `resistance`,
   `wh_per_nm`. `gm_l_m`, `trim_deg`, `list_deg`, `ply_thickness_m`,
   `unaccounted_frac`, `hull_lwl_m` and the whole `g` vector are bare numbers
   (measured 2026-08-11). Either every field carries `{value, tier, sigma}` or
   the law is restated to name the four. The former is better; the latter is
   honest. **The current state is neither.**

   The badge guard itself is good and must be preserved: a non-finite value or
   sigma downgrades to `L{n}-INVALID`, which `tier_rank` ranks at −1, *below* L0,
   so it can never be promoted by comparison.

### 4.4 The demonstration stops one step short of the claim

`scripts/demo_mission.py` is the artefact a reader runs to see the product. It
ends at provenance: it never calls `unroll` (panels, nesting, DXF), `engineer`
(BOM, sheet count) or `export` (STEP/IGES). The headline claim is *"…before it
exports as build-ready geometry"*, and the script that demonstrates the project
stops before that clause.

The capability is **not** missing — `agents.run_plm` reaches it. This is a
demonstration gap, not a capability gap, and it is cheap to close. But a reader
who runs the demo concludes the manufacturing tail does not exist.

### 4.5 Seams that are correctly closed — verified, no action

Recorded so this section is not read as uniformly negative:

- **The LLM seam.** `translate.sanitize` clamps ranges, whitelists strings, and
  ratchets the design category one way only.
- **Export refuses unvalidated designs.** `export.refuse_unvalidated` is called
  by `export_step`, `export_iges` and `export_dxf`.
- **The ladder is climbable and refuses honestly.** `evaluate.revalidate`
  escalates to L2 and refuses L3 with `TierRequiresOperator`; L3 is READ from
  recorded evidence and never solved in-process.

---

## 5 · RUN — the operating layer

### 5.1 The regulatory frame, corrected

The IMO MASS Code **does not apply to this product** — it is non-mandatory, and
scoped to cargo ships generally over 500 GT on international voyages. A 14 m
recreational catamaran is governed by Directive 2013/53/EU and the ISO
12215/12217 series. Use the MASS Code as a **voluntary architecture template**
— its goal-based structure (operational modes, operating limitations, risk
assessment, connectivity, cybersecurity, fallback on limit exceedance) maps
almost exactly onto the governance engine — and say "voluntarily aligned with",
never "compliant with". Detail: `docs/research/COMPLIANCE.md` §2.

### 5.2 Sensors: law 1, extended with time

Every reading carries `{value, tier, sigma, source, age}`. **Age is the new term
and it is the important one.** A stale sensor reading treated as current is the
runtime form of this project's most expensive defect class — an unmeasurable
value scored as a passing one. A reading past its validity horizon must be
*refused*, not extrapolated.

```
T0 hard safety   bilge, fire, battery protection, motor temp, tether tension
T1 navigation    GNSS(+Galileo HAS), IMU, compass, log, depth
T2 perception    radar, AIS, camera
T3 environment   wind, pressure, temperature, irradiance, wave
T4 external      Copernicus Marine / ERA5, charts, traffic   ← ADVISORY ONLY
```

Apply the `tier_rank("S1") = −1` trick: **a forecast can never satisfy a
requirement for a measurement.**

**Copernicus is strategic, never in the control loop.** Local sensors own
seconds-to-minutes; CMEMS/ERA5 own hours-to-days (ERA5 is hourly from 1940 via
the `cdsapi` client; Copernicus Marine has a Python toolbox/CLI). **The vessel
must be fully operational with the internet off** — cloud is for forecast, fleet
learning and supervision, not survival.

### 5.3 Autonomy is a degradable state, not a boolean

A0 manual → A5 mission autonomy, with the state a *function* of sensor
confidence, weather, traffic, battery, comms and navigation confidence, and
degradation automatic. Same idea as `tier_rank`, and it should reuse the
vocabulary: an autonomy level is a claim about evidence quality, and a claim that
outruns its evidence is refused rather than rounded up.

### 5.4 What RUN is confirmed not to be today

**MEASURED 2026-08-11:** grep for `sensor|telemetry|gnss|gps|nmea|mqtt|realtime|
as-built|onboard|field data` across the tree returns zero hits meaning any of
those things. Every hit is a homonym — `runtime` always means a governance
override, `real-time` a transient solver mode, `on-board` a quoted ES-TRIN
chapter title. `db.py`'s `result` table has `tier ∈ {L0,L1,L2,L3,R}`; **there is
no tier value that could mean "measured on a real boat."** Prose and code agree
here, which is the good case.

---

## 6 · The evidence graph

### 6.1 What it is, and why its rules are the way they are

```
Requirement → Decision → Assumption → Experiment → Evidence → Confidence
```

`db.Provenance` records *what* was computed. The evidence graph records *why the
design is shaped the way it is*. Two queries earn it:

- `unsupported()` — every decision with no path to any evidence. **The honest
  agenda.** On a real project it is never empty.
- `explain()` — the chain behind one node, as text a reviewer can argue with.

**Confidence is the weakest link, deliberately.** A decision resting on a 97%
experiment and a 60% assumption is a 60% decision. Averaging would let a pile of
cheap confirmations bury one load-bearing guess — laundering a tier-0 assumption
into a tier-3 result, which is exactly what law 1 forbids. Confidence is
computed as a minimum over the **ancestor set**, so it is path-independent and
linear.

`ALLOWED_SUPPORT` rejects a decision justifying a requirement — the most common
way a design argument quietly becomes self-supporting ("we chose L/B 9.5 because
we need 25 kn, and we need 25 kn because we chose 9.5"). Cycles are rejected at
insertion.

**It is unpopulated.** Its only callers construct six hand-typed nodes with
hardcoded strings. There is no function anywhere that takes an `Evaluation`, a
`db.Provenance` id or a `Pipeline` genome and emits a graph. The graph's
guarantees become real the moment something builds one from computed results —
and confidence over the ancestor set is then the number to put on the front of
the design evidence package.

**Export surfaces are PROV-O and the SysML v2 REST API (JSON/RDF); the store
stays ours.** They are export formats, never the enforcement path
(`docs/research/COMPLIANCE.md` §8).

### 6.2 The identity chain — three artifacts, one thread

```
SELL  →  MISSION CONTRACT        one page, frozen, hashed, human-readable
                                 what you asked for + what governs it + what it costs (with tiers)
BUILD →  DESIGN EVIDENCE PACKAGE EvidenceGraph, populated from computed results
                                 what we built + why + how confident + what is unsupported
RUN   →  OPERATING ENVELOPE      what it may do, when it must stop, and
         + DELTA REPORT          how the real boat differs from the designed one
```

threaded by one identity chain:

```
mission_id  ──►  design_id  ──►  vessel_id  ──►  observation rows
(sha256 of      (db.hull_id,     (hull serial)   (measured, tier ≠ L*)
 the contract)   EXISTS TODAY)
```

**Only the middle link exists.** Fixing the two ends is cheap, mechanical, and
is the precondition for §1.3, §3.1, §8.1 and every claim about fleet learning.
That is the whole "simplify" answer: not fewer features — *one artifact per
phase and one identifier that survives all three*.

One known defect on the middle link: `hull_id` hashes `round(v,10)` but stores
the unrounded vector under `INSERT OR IGNORE`, so two vectors differing by 1e-11
collide. A content address must address the content stored.

---

## 7 · Digital twin

Descriptive first, and **declared**. DNV-RP-A204 defines capability levels —
descriptive → diagnostic → predictive → autonomous — plus requirements on data
quality, cyber security, platform and the *organisation* operating the twin. It
is an off-the-shelf honesty scale, and it is used the way `tier_rank` is used:
**declare the level, and refuse any query above it.**

Ingestion is **Signal K** (JSON over WSS, Raspberry-Pi class hardware, bridges
NMEA 0183/2000 and SeaTalk) — no proprietary telemetry stack needed.

**Bars for a first descriptive twin:**

- the twin **refuses any query above its declared capability level** (a
  descriptive twin does not answer predictive questions);
- an as-built that diverges from its design (substituted component, different
  battery) is **detected and recorded**, not silently reconciled;
- ingestion survives gaps, duplicates and clock skew without corrupting the
  record;
- the as-built record is bound to the design's content hash (§6.2).

---

## 8 · Fleet learning

### 8.1 The delta engine — the smallest change that opens the flywheel

Everything above is architecture. **This is the part that pays for RUN.** The
minimum viable version is small:

1. `db.py` gains an **observation** row: `(vessel_id, mission_id, quantity,
   predicted, observed, condition, sigma_obs, source, t)`. It needs a *tier*
   value meaning "measured on a real boat" — today there is none.
2. A generic `delta(quantity, predicted, observed, condition) → residual`,
   recorded against the design, **never silently folded into a total**. The
   precedent is `extrapolate.ShipPrediction`, written specifically so that
   collapsing components does not make a disagreement undiagnosable.
3. `flywheel` gains a second data source that is not `evaluate()`.

With that, the loop in §1.3 opens: a residual on `wh_per_nm` at a measured
condition is the first thing in this system's history that can tell it its
physics is wrong. And it directly serves the benchmark problem — a fleet of real
hulls in the SKU family is a *second benchmark anchor*, which KCS by
construction can never be.

### 8.2 The constraint that deletes the naive version

ISO 19030 prescribes how to measure changes in hull and propeller performance
from in-service data — **and states in scope that its methods are not intended
for comparing ships of different types and sizes, explicitly including sister
ships.** "2 000 boats told us hull variant 7 beats CFD by 6%" is exactly that
comparison.

So fleet learning is **same-vessel, before/after, with an explicit correction
model** for loading, sea state, wind and fouling. Cross-vessel inference is
gated behind *validating* that correction model on held-out vessels, not
assumed.

**Bars:**

- a fleet-updated surrogate that degrades the frozen benchmark **never deploys**
  (law 4, unchanged);
- a **cross-vessel** performance claim is **refused** unless the correction
  model has been validated on held-out vessels;
- **selection bias is measured and reported** — which boats report data, and how
  they differ from those that do not. An unmeasured fleet is not evidence.

---

## 9 · Governance

### 9.1 Governance compiles; it does not adjudicate

The tempting architecture is a separate policy engine acting as a pre-filter.
Half of that is right and half would break this codebase. Right: governance
rules *are* categorical, they *do* prune before physics, and pruning early is
cheap. Wrong: a *separate engine* is a second place a limit is written down —
the single most expensive class of bug in this project's history.

So governance is a **compiler with two outputs from one source**:

1. a **parameter-space box** the sampler and NSGA-II are constructed inside
   (LOA ≤ 12 m becomes a bound, not a rejection), and
2. **rows appended to the existing `CONSTRAINT_NAMES` / `Evaluation.g` vector**,
   so anything already consuming that vector is governed for free.

It inherits the **ratchet law**, generalised from the LLM seam:

> **Policy may only ratchet a gate tighter. A policy that would loosen any floor
> in `limits.py` is a policy ERROR, rejected when the constitution is compiled —
> not a runtime override, not a warning, not a note.**

The compiler goes further and rejects a policy floor merely *equal* to the
`limits.py` value: "POLICY IS NOT A RATCHET, IT IS A SECOND COPY".

**The structural test, and it is the one that matters: delete the constitution
and every physics result in the regression suite must be bit-identical.** If
deleting policy changes a GM number, governance became a second constraint
engine and must be undone.

### 9.2 What it decides, and what it must not claim

The legal envelope is the load-bearing half: hull length < 12 m and design
category C or D is the envelope in which the *boat* needs no notified body and
the *design AI* is not high-risk under the AI Act — **a coupling no physics gate
can see** (`docs/research/COMPLIANCE.md` §1). The 12 m number is not a
preference; a 24 m constitution walks the platform into third-party assessment
on its first project.

Sustainability policy (allowed propulsion, banned fuels, material palette,
minimum recyclability) rides the same compiler — but these are **preference
constraints, not safety constraints**. They carry `basis='policy'` and can be
relaxed by the *owner* of the constitution; the legal envelope and the physics
floors cannot.

And the framing never moves: **assessment aid, clause citations, never
certification, never legal advice**, with the AI Act "safety component" question
stated as *open* rather than answered.

---

## 10 · WindWing — airborne-wind traction

Research, sources and every operator datum: `docs/research/WINDWING.md`. This
section is the plan, and its shape is unusual because the physics the subsystem
needs does not exist yet.

### 10.1 The binding constraint is structure and stability, not aerodynamics

At the reported ~1 kN/m², a 25 m² kite on a 14 m / 6.8 t catamaran develops on
the order of **25 kN ≈ 37% of displacement**, as a dynamic oscillating vector
applied above deck near the bow. Two consequences invert the instinctive build
order:

1. **The first WindWing gate is a LOAD gate, not a power gate.** "Does the
   vessel survive the kite" is answerable before "how much does the kite pull".
2. **Peak-to-average tether force is the structural sizing driver**, which makes
   this project's objective different from every AWE company's: they maximise
   cycle-averaged power, a boat wants mean thrust subject to a peak-load ceiling.

### 10.2 Preconditions, stated as work items rather than assumptions

**MEASURED 2026-08-11 — the physics a kite would attach to:**

| | Precondition | State | Why WindWing needs it |
|---|---|---|---|
| P1 | Centre of lateral resistance | absent — `dynamics.py` integrates the underwater side-profile *area* and never takes its centroid | the heeling lever (attachment → CLR) |
| P2 | Roll + pitch RAOs | absent — seakeeping is **heave only**, at zero speed | resonance avoidance; the whole §10.4 idea |
| P3 | A force-balance stability path | absent — `solve_to_displacement` bisects to a target **mass**, not a force | a kite's vertical force has no home |
| P4 | Environmental state on the mission | absent — `MissionSpec` has no wind, no sea state | there is nothing to size a kite against |
| P5 | Rigid-body equations of motion | **absent at every tier.** `dynamics.py` is component-lumped inertia arithmetic plus two *static scalar* load cases; the MuJoCo path is a 1-DOF hinge used to cross-check inertia | anything time-domain. **Its own lifecycle item, its own gate** |
| P6 | Yaw/leeway balance | absent — no rudder, no lateral plane, no course-keeping | side force cannot be balanced by anything the model knows about |

Two traps recorded with them, because both are silent:

- **The only heeling-moment balance in the codebase is in kg·m, not N·m**
  (`rules/iso12217.py`: `sin φ = m_crew·b / (disp_kg·GM)`; `g` cancels).
  **Substituting a kite side force in newtons there is a silent 9.8× error.**
- **`energy_report` fails open on a non-positive net** (`max(wh_nm, 1e-9)`), so
  a design whose resistance is fully overcome returns ranges of order 10¹² NM.
  Latent today; **it becomes live the moment a traction term exists.** The
  single force→power conversion is one line, and that is where a traction term
  must enter — there is no second candidate.

`weights.MassItem` **is** clean and is the right attachment point for kite,
tether, winch and launch-arm mass. One constraint: its tier set raises on
anything outside `("L1","E","F","R")`, so a WindWing item must claim an existing
tier or the tier set must be extended, with provenance and UI following.

### 10.3 The tier ladder

Its own letter, so a WindWing tier can never be mistaken for a hull tier:

| Tier | What | Cost | Depends on |
|---|---|---|---|
| **W0** | Loyd algebraic: traction and power from `(A, C_L, C_D, v_w, elevation)`; static and crosswind bounds | <1 ms | nothing |
| **W1** | Quasi-steady: + tether drag and sag, apparent wind from boat speed, cosine losses, elevation angle. **Tether drag is where Makani's measured shortfall lived — it is not a correction, it is the dominant loss** | ~ms | P4 |
| **W2** | Dynamic flight over a parameterised trajectory; peak/mean tension; excitation spectrum | ~s | P1, P2, P3, P5 |
| **W3** | CFD of the wing section | hrs | deferred — the existing OpenFOAM machinery is a free-surface marine solver, not an aero solver |

W0 and W1 are buildable now and are enough for the LOAD gate and for concept
sizing. **W2 is blocked behind P1/P2/P3/P5 and must be recorded as blocked** in
`data/gate-ledger.json`, with an owner and a review-by date, rather than
approximated.

**Bars:**

- **Gate W0** — reproduces Loyd's published `P_max` and the `v_w/3` optimum;
  the crosswind/static ratio lands in the 8–12× band operators report.
- **Gate W1** — tether drag is a *reported component*, never folded into a total.
- **Gate WL, the LOAD gate** — for a given (vessel, kite) the peak tether
  tension, heel and trim are computed and the configuration is **REFUSED** when
  any exceeds `limits`. The test feeds it the 25 m²-on-6.8 t case, which must be
  refused.
- **Gate P1** — CLR of a known analytic section within tolerance.
- **Gate P3** — an applied external force at a height reproduces the existing
  kg·m offset-load result when converted. **The g-cancellation trap gets its own
  test.**
- **Scope guard extended** — a kite-rigged craft does not receive ISO 12217-**1**
  findings; `iso12217_2_thresholds` is recorded via `refdata.absent()` and added
  to the purchase queue (`docs/research/COMPLIANCE.md` §3).

### 10.4 The defensible innovation, and its honesty condition

> **Choose the kite trajectory against the vessel's dynamic response, not
> against power.**

No airborne-wind company has the vessel's RAOs; no naval-architecture tool has
the kite. **This cannot be evaluated today and it is important to say so
plainly** — writing the trajectory optimiser before P1/P2/P3/P5 exist would
produce a confident number with nothing behind it.

### 10.5 "Aft wind only" is policy, not physics

The instinct to hard-code downwind-only operation is right as a *policy* and
wrong as *physics*. A WindWing operating envelope (true-wind sector, wind speed
band, sea-state ceiling, altitude cap, tether tension ceiling, harbour
prohibition) belongs in `policy/dna.py` with `basis='policy'`, leaving the
physics able to evaluate the full 0–360° envelope so the policy can be **widened
later against evidence rather than rewritten against belief**.

Design bars (max tether tension, max heel under kite load) go in `limits.py`.
The kite model's own validity envelope — the apparent-wind range its polar was
fitted over — goes **beside the model**, per the `FN_MICHELL_MAX` precedent.

---

## 11 · CFD and similitude — how the physics earns its badge

Measurement records: `docs/research/CFD.md`. Cost model, similitude and
extrapolation: `docs/research/APSE.md`.

### 11.1 CFD is an anchor, not a loop

The optimizer runs on L1; **nothing in the design loop consumes CFD.** Three to
five points ever, run by hand, after the model is stable. Automating a campaign
that cannot finish was the wrong architecture independent of any bug.

The budget is a constraint, not an overhead: state the projected wall clock and
the flow-through count **before** launching. `--symmetric` halves the cell count
and np=10 is the measured optimum on the Mac node.

### 11.2 Scale is an input; mesh density is the cost variable

**MEASURED:** three cases at Fn 0.26 spanning 100:1 in hull size and 1000:1 in
Reynolds number produce **the same background cell count to the cell**, because
every domain extent is a multiple of Lwl and the tank depth is wave-derived.
Shrinking the geometry costs exactly the same CPU and throws away Reynolds
number (λ^1.5) and Weber number (λ²). Model scale is what a *towing tank* is
forced into; CFD has no such constraint. Guarded by
`test_geometric_scale_buys_no_cpu` (`tests/test_stageG.py:54`, Gate G), which
asserts an identical `bg_cells` at 2.3 m / 7.28 m / 230 m and requires the
Reynolds span to exceed 900× so the point cannot be made vacuously. The
derivation is `docs/research/APSE.md` §1; the step count is scale-invariant too,
because the run length is a number of flow-throughs and `T ~ L/U`.

**So "shrink the model" is not the compute strategy, and it never was.** It is
the intuition imported from towing-tank practice, and this repository has the
measurement that refutes it. Naming the replacement matters, because a refuted
strategy with no successor gets re-invented by the next session:

> **The compute strategy is ADAPTIVE FIDELITY — buy the cheapest run that can
> still answer the question, and refuse the ones that cannot answer it at all.**

That is not aspiration; the machinery is built and gated under Gate G:

- `navalai/fidelity.py` — `estimate()` costs a case from measured constants
  (`CELL_STEP_S`, `COURANT_EFFICIENCY`, `NP_SPEEDUP`, `BYTES_PER_CELL`), each
  with a sigma; `admit()` returns a typed `Refusal` rather than raising, so a
  rejected option **keeps its cost and its reason** and can be compared against
  the ones that were admitted; `cheapest_admissible()` picks against a `Budget`.
  `MIN_CELLS_PER_WAVELENGTH = 20` is the §11.3 bar, applied here rather than
  restated.
- `navalai/planner.py` — expected information gain per CPU-second, in closed
  form on Gaussian beliefs. Three behaviours fall out of the arithmetic that a
  rule table would get wrong: an experiment vaguer than the current belief
  scores ≈ 0; diminishing returns are automatic (a second identical run gains
  `ln√2`); and **"do I actually need CFD?" is answered by arithmetic** — no CFD
  tier informs GM, so CFD's information gain on initial stability is exactly
  zero and it is never selected at any budget.

Two properties of that design are load-bearing and must survive any rewrite.
**The planner deliberately does not choose a geometric scale** — §1 of APSE
shows scale has no effect on the objective, so searching it would return an
arbitrary answer dressed as an optimum. And **the tier is discovered from the
uncertainty arithmetic, not hard-coded**: `QUESTION_QUANTITIES` maps a question
to the quantities it needs, and which rung to buy falls out. That is the same
refusal-over-rounding-up discipline as `tier_rank`, applied to spending money.

The honest limit: the planner's cost constants come from runs on one machine,
so it is a good instrument for *comparing* options and a weak one for
*promising* a wall clock. §11.5's 75% under-budget is the worked example.

### 11.3 A result has a minimum shape

These are bars, not preferences, and each was written after a run that violated
it produced a plausible wrong number:

- **≥ 20 cells per wavelength**, or the wave field is decoration.
- **≥ 1.0 flow-through**, always; anything settled under 5.0 is printed as
  UNDER-RUN. Domain length is 4.5 Lwl, so one flow-through at KCS Fn 0.26 is
  14.92 s. A domain the free stream has not crossed still holds its initial
  condition.
- **Drift ≤ 5% over the last fifth** — necessary, never sufficient. A low drift
  on a *total* dominated by a stable viscous part hides an oscillating pressure
  part underneath.
- **A GCI needs a systematically refined family**, with the refinement ratio
  MEASURED from real cell counts, the first-layer thickness AND the layer count
  held constant across it, and a settled member at every level.
- **An unmeasurable mesh metric is fatal, never a default.** `${VAR:-0}` turns
  "I could not measure this" into "this is perfect".
- **The identity of the case is checked, not assumed** — a gate applies a
  benchmark's acceptance data only to a case whose STL hash matches that
  benchmark.

### 11.4 The benchmark anchor set, and why it is a plan defect if left as-is

The product is sharp-chine small craft, 4–14 m, buildable from sheet. The gate
that certifies the physics was written against **KCS: a 230 m containership,
slender, round-bilge, no chine, no immersed transom, at Fn 0.26.** Everything
downstream inherited it — benchmark geometry, y+ targets, case-generator
defaults, and months of CFD.

**The correction is SEQUENCE, not substitution.** KCS is not demoted: what it
teaches is hull-agnostic and all of it transfers.

| Anchor | What it validates | State |
|---|---|---|
| **Wigley** (analytic) | the wave-resistance MACHINERY, against a closed-form Michell answer we derive ourselves. Free, no tank data, no transom to confound it | in the tree |
| **KCS** (tank) | free-surface capture, wall treatment and y+, force integration, grid convergence, AND — via published sinkage and trim — the mass/inertia/CoG/6-DOF chain every boat needs. The only hull we have with published truth | keeps the full workload |
| **DSYHS** | 9–14 m displacement/semi-displacement yachts. Directly the liveaboard SKU | **OWED** |
| **Fridsma / Series 62** | hard-chine planing: chine, immersed transom, spray, dynamic lift. Directly the dayboat and tender | **OWED** |
| **NTUA Series** | double-chine semi-displacement, with model-test resistance, CG rise and trim. **A CANDIDATE for the row above, surfaced 2026-08-13** — its bands are transcribed in `docs/research/HULL-FORM-RULES.md` §7, and unlike KCS it is in the SKU size band and it is chined | **CANDIDATE, not adopted.** Caveat that decides it: it is a *planing* series and `resistance.FN_MICHELL_MAX` is 0.45, so part of the series is outside the L1 model it would anchor. Adopting it means declaring which subset of the series L1 is allowed to be judged on |

**Reading a green KCS gate as small-craft validation is forbidden.** The same
root cause one tier down: Michell thin-ship applied at Fn 1.09 on a tender case
and reported as a pass. A ship method on a boat. The Froude validity envelope on
`total_resistance` is the same correction at L1.

**Corollary for the mesh, MEASURED:** `_HULL_REFINE`, `_TARGET_YPLUS` and the
layer count were all tuned on KCS and **do not transfer** — KCS bridges its
37.9 mm hull cell with 5 layers where Wigley's 52.1 mm cell needs 10. The layer
count is DERIVED per hull and guarded at both ends. **Any constant tuned on one
hull is suspect.**

### 11.5 What the next CFD experiment is, and why it is not a longer run

**MEASURED 2026-08-07 on `runs/kcs_s1`** at 3.40 flow-throughs, mass conserved:
the viscous component is **1.161×** the ITTC-57 line — inside the form-factor
band, batch error 1.7% — and the pressure component is **2.32×** its expected
value with a **36%** batch error. Drift collapsed to **0.31%**, and the best
single sinusoid explains **0.4%** of the detrended signal against a 50% bar, so
there is no coherent oscillation to name.

Three consequences, and they change what is worth buying:

1. **The error is not a settling problem, and more wall-clock will not remove
   it.** The transient has washed out.
2. **The viscous half is right**, which localises the error to the pressure side
   — exactly what sinkage and trim move.
3. **A relaxation zone would have been weeks of work against a mechanism
   subsequently measured not to exist.**

So the next experiment is **free sinkage and trim**, then free-surface
resolution, then the grid. And the batch error
must be understood before a triplet means anything: three noisy numbers do not
make a Richardson extrapolation.

**"code, not compute" was TRUE when it was written and is STALE — corrected
2026-08-12.** This sentence used to read *"free sinkage and trim (`rigidBodyMotion`
— code, not compute)"*, and commit `7b8f628` measured that the code has existed
for some time: `navalai/cfd/case.py` carries `DYNAMIC_MESH`
(`sixDoFRigidBodyMotion`, heave + pitch constraints, dampers),
`POINT_DISPLACEMENT`, `sixdof_properties` and `motion_from_geometry`;
`scripts/make_case.py` has `--free-motion` and `--kg`; and three suites exercise
`free_motion`. **The blocker was one number, not a solver.** KCS's published
`KG = 0.2303 m` above keel lived only inside a comment in `case.py`; with it
absent, `motion_from_geometry` falls back to VCB and gives 0.187 m — **19 % low**
— so a free run would have converged to a plausible attitude for a
differently-ballasted ship. `7b8f628` moved the constant into `benchmarks/kcs.py`
beside the acceptance data (EFD sinkage −1.394e-2 m, EFD trim −0.169°). The
experiment is now runnable, and it is COMPUTE. `CLAUDE.md` still carries the
stale phrasing in two places (its "next experiment" paragraph and its numbered
CFD list); it is flagged here rather than edited, because that file is read first
by every session and a correction to it belongs to its owner.

**A correction owed to `CLAUDE.md`, measured and never merged back:** the GCI
triplet is **~21× the coarse grid (~68.7 h), not ~12×**. The cell ratios (2.79×,
7.79×) are correct as cell ratios, but the timestep is Courant-limited so a √2
finer grid also takes √2 more steps. Using cell ratios as a time estimate
under-budgets by 75%.

### 11.6 Gate 2U: the missing admissibility layer, and how the gate must be split

**THE HYPOTHESIS, from an external review, tested rather than adopted:** Gate
2U's mesh failures are not an OpenFOAM problem — NavalAI defines "valid hull"
as `grammar.check()` plus a finite L1 evaluation, which is not the same set as
"CFD-meshable hull", so the grammar emits a design manifold larger than the
STL → snappyHexMesh → prism-layer pipeline can hold. **Confirmed in outline,
refuted in its two named mechanisms**, and the difference is where the work is.

#### 11.6.1 The two geometry claims: both TRUE, neither predictive

Gate 6D's panel-unrolling work independently measured two defects in
`geometry.station_geometry`, and the review proposed them as the CFD driver
too — one fix moving 6D and 2U together. Both were re-derived here from the
code, analytically and numerically:

- **(a) The stem tangent is unbounded.** `y_sheer = max(ys,0) * max(w,0)**0.15`
  with `w = 1 - ((x-x_mb)/(L-x_mb))**p_bow`, so near the stem
  `w ≈ p_bow·(L-x)/(L-x_mb)` and `y_sheer ~ (L-x)**0.15`, giving
  `dy/dx ~ (L-x)**-0.85 → -∞`. MEASURED local exponent on the reference hull:
  0.3265 at 100 mm from the stem, 0.1714 at 10 mm, 0.1502 at 0.1 mm, **0.1500
  at 1 µm** — the closed form, confirmed. In CFD terms the deck is already
  **6.2 hull cells wide (median over 200 hulls) one cell aft of the stem**: the
  bow closes over a length no cell in the case can resolve. CONFIRMED.
- **(b) The plan-form tangent breaks at `x_mb`.** Forward of `x_mb`,
  `dw/dx → 0` for any `p_bow > 1`; aft of it `dw/dx = (1-r_transom)·p_stern/x_mb`.
  The chine slope jump is therefore `0.5·B·(1-r_transom)·p_stern/(x_mb·L)`,
  which matches the closed form to six significant figures (0.218182 predicted,
  0.218182 measured at h = 1e-6) — a **12.308°** tangent break on the reference
  hull, and **up to 65.9°** over the grammar's box. CONFIRMED.

**And neither explains the mesh failures.** Over campaign hulls 0–17 (hull 5
excluded, its record is self-contradictory), AUC against mesh failure:
`bow_bluntness_cells` **0.500**, `xmb_tangent_break_deg` **0.500** — chance,
both. Claim (a) is worse than uninformative as a discriminator: it is a
property of the **grammar**, present in every hull it emits, so it cannot
account for per-hull variance in a batch where a third of the hulls mesh. So
**the "one fix moves 6D and 2U together" thesis is REFUTED on the CFD side.**
Fixing the cusp is still owed — it is Gate 6D's residual — but it must be
justified on 6D's numbers, not on a CFD benefit that is not measured.

The full battery is on the record so it is not re-run: max STL facet turn
(AUC 0.673, failures 24.7–40.9°, successes 24.9–42.2° — overlapping),
`stack/hull_cell` 0.621, chine curvature ratio 0.309, panel twist 0.561, and
per-parameter, only draft reaches `p = 0.0101` one-sided — **`p = 0.152` after
Bonferroni over the grammar's 15 parameters, i.e. not significant.**

#### 11.6.2 What DOES screen, and its honest strength

`navalai/admissibility.py` is a pre-mesh screen: no snappy, no OpenFOAM, no STL
on disk, **7.6 ms per hull** against ~80 s to mesh one. It returns a typed
per-metric report — `SAFE / MARGINAL / DANGEROUS / UNMEASURED`, never a single
score, because a single score is exactly what a system tunes until it goes
green. Two bars carry the result, and **both are derived from the pipeline's
own constants rather than fitted to the outcomes**:

| bar | derivation | labelled result |
|---|---|---|
| `draft_over_hull_cell < fs_band/cell` (= 14.187 at scale 1) | `_FS_BOX["z"]`, `_HULL_REFINE`, `_NX_BASE` — the keel sits inside the tightest post-snappy z-refinement box | refuses hulls 0, 1, 6, 12 at 10.14/12.31/11.82/13.20 cells; **4 of 4 failed**, 0 of 6 successes refused (next failure up is 15.55, so the bar is not sitting in a gap it was placed in) |
| `sheer_collapse_cells > 0` | `station_geometry` writes `np.maximum(ys, 0.0)`, silently substituting a zero-width deck when the grammar's own formula returns a negative half-breadth | refuses hulls 5, 11, 12 (3.04/2.13/4.36 cells of collapsed run); **3 of 3 failed**, 0 successes |

**Confusion matrix over campaign hulls 0–17** (refused = DANGEROUS; positive =
failed to mesh): **TP 6, FP 0, FN 6, TN 6 — precision 1.000, recall 0.500,
Fisher exact one-sided p = 0.0498.** That is evidence at the edge of
significance on 18 points, and it is reported as such. Half of Gate 2U's
failures still have no cheap geometric explanation, and
`test_the_screen_catches_half_the_failures_and_no_more` pins the recall as well
as the precision so a later edit cannot quietly claim more.

**Read that matrix against §11.6.2a before quoting it.** Those are rung-0
outcomes, and every hull the screen refuses meshes once the layer ladder is
allowed to run.

**Over 200 grammar-valid hulls** (seed 1234, speed 2.57, scale 1): **68
DANGEROUS / 79 MARGINAL / 53 SAFE**; 19.5% keel-in-band, 17.0% clipped sheer.
The review's structural claim is therefore *quantified*: **a third of the
manifold `grammar.check()` blesses is inadmissible to this pipeline.**

Two mechanisms proposed and killed, recorded so they are not re-proposed:

- The collapsed sheer does **not** open the STL. `stl_watertight_report` on
  hulls 5, 11 and 12 at the case's own 600×120 triangulation: 0 open or
  non-manifold edges, 0 winding conflicts, watertight, outward — identical to
  hulls 7 and 13, which mesh. Whatever the collapsed ridge does to snappy, it
  is not a hole.
- The first `stack_over_min_radius` refused 16 of 18 hulls, 4 of them
  successes, on a curvature of 28–50 — which was the **sampling artefact of the
  `x_mb` tangent break**, where a discrete curvature is `1/h` and diverges as
  the sampling refines. Excluding the four piecewise breakpoints drops it to
  0.005–3.5. A metric that refuses everything is not a screen.

#### 11.6.2a The finding that reframes all of the above: the refusals are RESCUABLE

**MEASURED 2026-08-11 on `data/gate2u-campaign-backoff-mesh.json`** — the same
seed-0 hulls, mesh-only, `--layer-backoff 3`:

| hull | screen | rung-0 (baseline) | with ladder | layers used | attempts | skew | wrongOri |
|---|---|---|---|---|---|---|---|
| 0 | DANGEROUS `draft` | FAILED zero-volume | **meshes** | 8 | 2 | 4.52 | 0 |
| 1 | DANGEROUS `draft` | FAILED wrong-oriented | **meshes** | 7 | 2 | 3.25 | 0 |
| 5 | DANGEROUS `collapse` | record corrupt | **meshes** | 8 | 1 | 4.54 | 0 |
| 6 | DANGEROUS `draft` | FAILED zero-volume | **meshes** | 8 | 2 | 4.65 | 0 |
| 11 | DANGEROUS `collapse` | FAILED wrong-oriented | **meshes** | 7 | 2 | 5.13 | 0 |
| 4 | **SAFE** | FAILED wrong-oriented | **still fails** | 3 | 4 | 10.47 | 38 |

**Every hull the screen refuses meshes cleanly once the prism-layer count steps
down by two, and the one hull the ladder cannot save is one the screen calls
SAFE.** Over hulls 0–11 the mesh rate goes **3/12 at rung 0 → 11/12 with the
ladder** (`success_pct` 83.3% on the 12 recorded, against the runner's own bar
11/12).

So the screen's verdict means *"expect a checkMesh refusal at the DERIVED layer
count"*, not *"this hull cannot be meshed"* — and `navalai/admissibility.py`
says so in its docstring rather than trading on the stronger reading. It is
still worth 7.6 ms: knowing which hulls will need the ladder before paying
~80 s of snappy is exactly the kind of cheap foreknowledge the plan's Phase 2
budget needs. But the headline claim it does **not** support is that the
grammar's manifold is geometrically outside the mesher's reach.

**The explanation the data actually supports is the derived prism-layer count.**
`n_layers_to_bridge` returns 8–10 for essentially every hull the grammar emits;
because it barely varies between hulls it cannot *discriminate* them, which is
precisely why it was invisible to the correlation study and is nevertheless the
largest measured lever in the campaign by a wide margin. The geometry metrics
above are best read as markers of *layer-insertion fragility* — a hull whose
keel sits in the refinement band or whose deck has been silently clipped is one
snappy struggles to extrude a full stack onto — rather than as markers of
inadmissible geometry.

#### 11.6.3 Gate 2U splits into 2U-A and 2U-B, and 2U-A is the one that counts

A single admissible-domain robustness number is gameable in the most natural
way possible: shrink the admissible domain until everything in it passes. The
review is right about that, and the defence is not a policy but a second gate.

- **Gate 2U-A — raw grammar robustness (the brutal truth).** Denominator is
  `sample_valid(N, seed)` with **no admissibility filter and no back-off**:
  exactly what the pipeline does today to exactly what the grammar emits.
  Current watermark **6/18 = 33.3%** against the ≥95% bar. This number may
  never be improved by narrowing the grammar's parameter ranges, by filtering
  the sample, or by adding rungs — only by making the pipeline hold more of the
  manifold, or by fixing the geometry kernel. **It is the gate that is allowed
  to be red, and it must stay red until it is honestly green.**
- **Gate 2U-B — admissible-domain robustness.** Denominator is the hulls
  `admissibility.screen()` returns as not-DANGEROUS, with the deterministic
  back-off ladder enabled. This is the number that describes what a *user* of
  the system experiences, and it is the one permitted to drive scheduling
  decisions. **Watermark today: 11/12 = 91.7% with the ladder on the FULL
  seed-0 set** (§11.6.2a), i.e. the admissibility filter is not currently what
  buys the improvement — the ladder is. Reporting 2U-B without saying that
  would credit the screen for the ladder's work.

**The anti-gaming clause, which is the load-bearing half:** 2U-B is
uninterpretable without 2U-A, so **the two are reported as one row and the
ledger entry for either carries both**, together with the *admissible
fraction* — because 2U-B rising while the admissible fraction falls is the
gaming signature, and it is only visible when the two are printed side by side.
A change that raises 2U-B and lowers the admissible fraction has bought
nothing. Concretely: 2U-B on an admissible fraction of 5% would be a headline
number about almost no boats.

**And the grammar's ranges are not to be narrowed to make either pass.** It
would work, and it would delete the evidence. Where a parameter predicts
failure the useful form is `P(failure | x)`, published so NSGA-II can carry it
as an objective and trade it against the mission — the optimiser is allowed to
avoid the bad region; the *grammar* is not allowed to pretend it is not there.
Today the honest statement is that **no fitted `P(failure|x)` is warranted**:
draft is the only parameter above chance and it does not survive Bonferroni at
N = 17. What `screen()` already provides is the usable substitute — a
deterministic, 7.6 ms, x-valued refusal that NSGA-II can consume as a
constraint column today, and which will become a probability when the campaign
has the ~200 labelled hulls the plan's own bar asks for.

#### 11.6.4 The funnel, which replaces the single rate

Gate 2U reports **eight** numbers, each a strict subset of the one above it.
A single percentage cannot distinguish "the mesher refused it" from "the solver
diverged", and those are different repairs:

| stage | definition |
|---|---|
| generated | `sample_valid(N, seed)` — L0 + finite L1 |
| geometry-admissible | `admissibility.screen()` not DANGEROUS |
| mesh-success | passes `run-case.sh`'s bars at **rung 0** (0 zero-volume, ≤5 wrongly-oriented, skew ≤20) |
| rescued-by-backoff | meshes only at a lower rung of the layer ladder |
| solve-started | `log.interFoam` exists — the runner did not refuse between checkMesh and setFields |
| solve-completed | reached `endTime` with no FATAL and no signal |
| converged | force history settled: drift ≤5% over the last fifth **and** ≥1.0 flow-throughs (§11 / `CLAUDE.md`) |
| end-to-end | converged ÷ generated |

**The ≥95% bar attaches to end-to-end, and it does not move.** The intermediate
stages exist to say *where* the 95% is lost, not to offer a softer denominator.
`generated` is the denominator for 2U-A; `geometry-admissible` is the
denominator for 2U-B and is **printed as a fraction of `generated` in the same
row**, per the anti-gaming clause above.

#### 11.6.5 Back-off tiers are deterministic, and the tier is part of the result

`layer_backoff_ladder` is already deterministic — `n_derived - 2` down to a
floor of 3 — and that property is a requirement, not an implementation detail:
a ladder that depended on wall clock, on machine state, or on a retry counter
would make Gate 2U unreproducible, and the gate's whole purpose is to be a
regression signal.

**A hull that meshes only with layers reduced has not passed the same physics
case as one that meshes at the derived count.** `_TARGET_YPLUS` is 100 and the
stack is sized to bridge to the local hull cell; dropping from 10 layers to 3
changes the wall treatment, which changes the friction, which is most of the
drag at these speeds. Reporting both under one percentage is the same defect as
printing the *requested* layer spec under the label of the *achieved* result.

So the honest report is: **`n_layers_used`, `layer_attempts` and
`layers_achieved` are recorded per hull** (they already are, in
`mesh_robustness.py`'s rows), the funnel splits `mesh-success` from
`rescued-by-backoff`, and **any C_T or resistance number carries the rung it
was produced at**. A campaign whose success rate rests on rung 3 reports "95%,
of which 60% at a reduced wall model" — two numbers, because it is two results.
The ledger watermark stays the **rung-0** rate, which is why
`mesh_robustness.py --layer-backoff` defaults to 0.

#### 11.6.6 Pre-registered, so the screen cannot be tuned after the fact

The seed-0 campaign was still running when this was written; hulls 18–24 had no
recorded outcome. The screen's verdicts for them are therefore recorded **in
advance**, and `tests/test_admissibility.py` pins hull 20's:

| hull | Lwl | verdict | refused by |
|---|---|---|---|
| 18 | 17.289 | SAFE | — |
| 19 | 11.969 | MARGINAL | — |
| **20** | 12.640 | **DANGEROUS** | `min_bottom_panel_width_cells`, `transom_half_beam_cells` (0.998 cells each) |
| 21 | 15.639 | MARGINAL | — |
| 22 | 15.733 | MARGINAL | — |
| **23** | 18.702 | **DANGEROUS** | `draft_over_hull_cell` (13.72), `sheer_collapse_cells` (73.26) |
| 24 | 14.618 | MARGINAL | — |

Prediction, **at rung 0** (which is what the baseline campaign runs): **hulls
20 and 23 fail to mesh; 18, 19, 21, 22 and 24 are not refused by the screen**
(which is not a prediction that they succeed — recall is 0.500). Hull 20 is the
first case to exercise the sub-cell bars at all. Per §11.6.2a the prediction
does **not** extend to the ladder campaign, where 20 and 23 are expected to be
rescued like every other refused hull; a refused hull that meshes at rung 0
falsifies the bar, and one that meshes only after a rung does not.
If 20 or 23 meshes cleanly at rung 0, the corresponding bar is wrong and must
be recorded as such rather than re-fitted.

#### 11.6.7 What this section does NOT establish

- **The mechanism behind `draft_over_hull_cell`.** The association is measured;
  the explanation — that the z-refinement transition wraps under a keel that
  sits inside the band — is a *candidate*. `navalai/cfd/case.py`'s TOPO_SET
  comment records z-refine transitions as the source of every wrongly-oriented
  face this project had measured before the hexes-only fix (0 rounds → 0 faces
  in 7 of 7 meshes; 3 rounds → 2–47 in 4 of 4), which is why it is the leading
  candidate — but no re-mesh with the band moved has been run. The experiment
  that would settle it is cheap (mesh-only, ~2 min): re-mesh hull 0 with
  `_FS_BOX["z"]` halved and see whether the zero-volume cells move.
- **Whether the six unexplained failures share a cause.** Seven of the twelve
  are `checkmesh-wrong-oriented` and no metric here separates them.
- **Hull 5's true mesh outcome.** Its campaign row is self-contradictory —
  `mesh-build-failed` with unmeasurable mesh metrics next to `solves: true`,
  the documented resume artefact — so it is excluded from every AUC above and
  counted as a failure only in the confusion matrix, where the screen refuses
  it either way.
- **Anything about the solve.** `solver-stopped-short` (hull 2) was a
  floating-point divergence on a mesh that passed every checkMesh bar. A
  geometry screen has nothing to say about it, and does not pretend to.
- **That the two campaigns are the same configuration.** The rung-0 baseline
  ran `--solve 2 --np 10`; the ladder campaign ran mesh-only at `--np 1`. The
  mesh build is serial and identical either way, so the comparison is believed
  to be sound — but it has not been demonstrated by re-running one hull both
  ways, and docs/LESSONS.md defect class 6 exists because that assumption has
  been wrong before. The cheap check is one `MESH_ONLY=1` re-mesh of hull 7.
- **Why hull 4 resists the ladder.** It reaches the floor at 3 layers with 38
  wrongly-oriented faces after 4 attempts, and this screen calls it SAFE. It is
  the single most informative hull in the batch for whatever the second
  mechanism is, and nothing here explains it.

**§11.7 supersedes this section's framing of the layer count.** Everything above
is written at `_MAX_LAYERS` = 10, where "rung 0" meant the derived count of
8–10. Rung 0 now means 7, and the confusion matrix in §11.6.2 does not transfer
to it — measured, restated, and its consequences scheduled in §11.7.

### 11.7 The prism-layer count is a per-hull MEASUREMENT, not a per-hull formula

**The evidence is `docs/research/LAYERS.md` (2026-08-12), which is its one
home.** This section carries only the plan: what changes, in what order, who
owns it, and what bar each step must meet. It restates no measurement that file
owns beyond the four numbers the ordering itself depends on.

#### 11.7.1 The question, and what the data answered

The layer cap has been 3, then 10, now 7. The standing question is whether one
number can serve 25 hulls that differ in size and shape, and if not whether the
count should be **derived per hull from its geometry**.

- **One number cannot serve them.** Within the counts actually run, hull 10
  meshes only at n=8 and hull 12 only at n=6; their admissible sets are
  disjoint, so no common count exists inside the tested grid.
- **Deriving it from geometry cannot work either, and this is the part that
  reshapes the plan.** For a FIXED hull the mesh outcome is not monotone in n
  and not even unimodal — three of the twelve hulls run at three or more counts
  have a *failure strictly between two passes*. A rule emitting one integer per
  hull cannot express an admissible set of `{4, 7}` or `{3, 5, 8}`.
- **Nothing separates the failures.** Twenty-nine geometric quantities were
  scored, reusing `admissibility.screen()` rather than re-deriving it. The best
  reaches AUC 0.842 and does not survive correction for the family
  (family-wise permutation p = 0.21). The five candidates an external reading
  would reach for first — curvature vs stack height, feature-angle density,
  `last_layer_over_hull_cell`, minimum panel width, medial-axis proximity — are
  each argued down from the data in `LAYERS.md` §4; two of them are *inverted*.

So the count is per-hull and it must be **measured** per hull. The plan item is
a search, not a formula, and a search is the one instrument this repository's
standing counter-example cannot refute: **Wigley solves at `stack/hull_cell`
1.084 while KCS dies at 0.952**, so no build-time predictor is admissible, and a
procedure that meshes and reads checkMesh makes no prediction to be wrong about.

#### 11.7.2 The change, in order, with its bar

Owner: whoever owns `navalai/cfd/case.py`. Files: `navalai/cfd/case.py`,
`scripts/mesh_robustness.py`, `scripts/make_case.py`, `tests/test_layer_cap.py`,
`navalai/admissibility.py`, `data/gate-ledger.json`. **These are disjoint from
this document, and none of them is to be edited on this document's say-so
without the measurement in `LAYERS.md` §8 in hand.**

| # | Item | Done when |
|---|---|---|
| 11.7-a | **Run the dense sweep** (`LAYERS.md` §8): the same 25 seed-0 hulls × n = 3…10, mesh-only, one rung per cell. 129 of the 200 cells are unmeasured; at the measured 96.2 s/hull that is **~3.4 h unattended**. Run the three hole cells (hull 5 at n=7, hull 8 at n=6, hull 3 at n=5, ~5 min) FIRST — they are what the specification rests on | the matrix is complete and committed as `data/gate2u-layer-grid.json`, and the three holes either reproduce or are withdrawn |
| 11.7-b | **Replace the one-sided step-2 ladder with a dense two-sided search** over `[3, n_ideal]`, step 1, ordered outward from the highest-yield rung, stopping at the first pass, deterministic in `(n_ideal, floor, n_start)` alone | a hull whose only good rung is ABOVE the shipped one (hull 10 at 8, hull 18 at 10) is reachable, proven by a test that feeds the search that hull's genome |
| 11.7-c | **`_MAX_LAYERS` stops being a quality lever.** It becomes a compute/fit bound beside the existing `stack_ratio > 1.2` refusal; `n_ideal` becomes the search's ceiling | `tests/test_layer_cap.py`'s cap assertion is REPLACED (not deleted) by one pinning the search's bounds and ordering to the sweep — its motivating incident, "the cap moved on an argument instead of a measurement", is unchanged and still governs |
| 11.7-d | **Receipts.** `case.info` records `n_layers_ideal`, `n_layers_ladder`, `n_layers_rung` and `layer_search=on\|off`; and its unconditional *"first-layer thickness AND layer count are held constant across the GCI triplet"* NOTE becomes conditional on the caller having pinned the count | a reader can tell a first-rung mesh from a sixth-rung one, and no case asserts a triplet property it does not have |
| 11.7-e | **Re-state the admissibility screen's confusion matrix at the shipped configuration**, in `admissibility.py`'s docstring and in §11.6.2, carrying both | the published precision describes what ships |
| 11.7-f | **Correct the Gate 2U ledger `units` string**, which describes `_MAX_LAYERS` = 10 | the watermark's configuration is the one that exists |

**The bar on 11.7-b is 92%, not 95%, and saying so is the point.** Across all
five recorded arms, 23 of the 25 hulls have at least one count that meshes
clean, against 19 at the best fixed count. A perfect search therefore reaches
**92%** on this batch and Gate 2U-A's ≥95% bar is still not met — hulls 4 and 14
pass at no count tried. **The search is not the close-out of Gate 2U-A; it is
what makes the residual visible.** Anyone reporting the improvement must report
that two hulls remain unexplained, or they have restated a 76% → 92% step as if
it were the gate.

**Cost, stated before it is spent:** the search averages ~1.9 rungs/hull on the
observed matrix, so a 25-hull campaign goes from ~40 min to ~77 min mesh-only —
**1.9× for +16 percentage points.**

#### 11.7.3 What it breaks, and the one that is expensive

- **Not the GCI triplet, directly.** The wall model must be frozen across the
  GRIDS of one family, and per-hull is a different axis: search once, pin, run
  the family. **But the search must run at the FINEST scale of the intended
  family** — `stack/hull_cell` doubles from coarse to fine, and `LAYERS.md` §6.1
  measures **six of 25 hulls whose n=7 fine grid is already refused at build
  time by the existing 1.2 fit check**. That is true of the shipped fixed cap
  today; the search does not create it, but it makes fixing it mandatory.
- **Cross-hull physics comparability, and this one is expensive.** The
  known-good rungs span 3 to 10, i.e. a **7.1× spread in prism-stack height** at
  a near-constant first layer. §11.6.5 already states that a hull meshed at a
  reduced count has not passed the same physics case; under per-hull search that
  becomes the norm rather than the exception, and there is no common count to
  re-mesh them at. **Consequence for §8.1 and for the surrogate flywheel: CFD
  labels from a searched batch are not mutually comparable and must not be
  pooled into one training set or one ranking** until either a common count is
  found (the sweep tests for one) or the wall-model difference is measured
  against the effect being ranked. Nothing does this pooling today. That is the
  window in which to write the rule down.
- **The admissibility screen's published strength.** Re-scored unchanged against
  the shipped rung 0, its precision falls from **1.000 to 0.250** and its recall
  from 0.500 to 0.333 — because the bars were validated at a rung 0 that no
  longer exists. **Both bars are `Basis.DERIVED` and must NOT be re-fitted**;
  re-fitting a derived bar to a new outcome set is exactly the tuning the module
  was built to prevent. Re-state the matrix (11.7-e). Correspondingly, §11.6.6's
  pre-registration for hulls 20 and 23 is **neither confirmed nor falsified**:
  the campaign it named stopped at hull 19, so those hulls were never run in the
  configuration the prediction was about (docs/LESSONS.md defect class 6).
- **`derived_n_layers` in the screen is now a constant** (7.0 on all 25) while
  its note describes a range of 8–10. It should report the uncapped `n_ideal`,
  or say which of the two it is.

#### 11.7.4 What this section refuses to do

- **No narrowing of the grammar.** §11.6.3's anti-gaming clause is unchanged and
  nothing here weakens it.
- **No `P(failure | transom width)`.** It is the best single metric measured and
  it does not survive correction for the family it was found in. It has also
  never been tested against KCS or Wigley — `screen()` takes a genome, not an
  STL — which is on its own sufficient reason not to ship it.
- **No claim that the search is a derivation.** It is a measurement with a
  starting hint, the hint is allowed to be wrong, and being wrong costs one
  96-second mesh.

---

### 11.8 The validation ladder and the fidelity governor (2026-08-19, three-agent investigation)

Three parallel investigations (regime physics from theory; independent
published-evidence verification; validation-flow forensics against this
repo's own campaign record) landed the same day. Full reports:
`docs/research/SMALL-CRAFT-REGIMES.md`; the flow forensics is folded into
this section and `docs/audit/STATUS.md`.

**The honest finding about the current flow:** the runner already refuses a
mesh that fails checkMesh BEFORE the solver starts — "mesh errors reaching
the solver" is not where the money goes. The full-solve-price discoveries in
the actual record are SOLVER-stage pathology: startup FPE (h2, died at
iteration 104 on a mesh that passed every bar), tau-collapse (h18, 4.4e-18 s,
checkMesh-blind), late divergence (h19, onset ~410), unsettledness (found at
the END of a solve budget), and wrong-regime (the KCS LTS lane, found by a
35-min solve + a 3 h probe). The confusion table also proves the pre-mesh
screen CANNOT predict checkMesh outcomes (measured at chance; the admissible
layer set has holes) — so the ladder's stages are real detectors, not
paperwork.

**The ladder** (stage N runs only on stage N-1 passers; each failure class is
caught by the cheapest detector that can catch it):

| stage | where | what | cost | catches |
|---|---|---|---|---|
| 0 | fortress | L0 + admissibility screen (EXISTS) | ~10 ms | geometric infeasibility, sub-cell features |
| 1 | Mac | mesh-only + checkMesh + layer ladder (EXISTS) + the geometric-tau receipt (TO BUILD, calibrate on the paired gate2u corpus first) | ~80 s–5 min | all checkMesh classes, layer collapse; candidate: the h2 class at mesh price |
| 2 | Mac | **the SMOKE SOLVE (the missing stage): ~200 LTS iterations of the REAL solve, checkpoint kept** — promotion costs ZERO net because run-case.sh's resume branch continues from the checkpoint | ~3 min gross, ~0 net for passers | startup FPE, tau-collapse, BC/setFields pathology — at 3 min instead of 28 |
| 3 | Mac | the full solve, resumed from the smoke checkpoint (EXISTS) | ~28 min median | late divergence (capped at onset by the live tau abort), resistance truth |
| 4 | both | settledness by ESTIMATION (`post.settled_estimate`, EXISTS — wire as the verdict route) | free | unsettledness without waiting out the drift bar; candidate 2–3x on transient tails |

**What the ladder does NOT claim:** settledness, late divergence and
resistance-vs-tank truth are only measurable by solving — the ladder
eliminates discovering AVOIDABLE failures at full-solve price and guarantees
the single Mac solve slot only ever holds designs that passed every cheaper
detector. Measured expectation on a 25-hull campaign: ~1 h of waste avoided
(the runner already gates well) — **the "two weeks of CFD" lives in the
CALIBRATION lane**, and that is killed by the estimator + the cancelled
triplet (one estimator-settled medium anchor + a coarse/medium Richardson
band) + CoKriging active selection (STATUS "the re-derived calibration
plan"), not by the ladder.

**The fidelity governor** (from the regime physics; conceptual — implement
only against `docs/research/SMALL-CRAFT-REGIMES.md` §16): every CFD request
passes gates before costing anything —
(0) ENVIRONMENT: if wave-follower (lambda/L > 5) or windage/orbital forces
dominate hull resistance, calm-water refinement cannot change the decision →
ANALYTICAL, flagged;
(1) WAVE EXISTENCE: V < 0.23 m/s has no wave system; V < 0.5 m/s is
capillary-contaminated;
(2) FRICTION REGIME: Re < 5e5 laminar → analytical only; 5e5–5e6 transitional
→ CFD BARRED unless transition-modelled (fully-turbulent RANS reproduces
ITTC-57's own bias — higher cost, same wrongness);
(3) FROUDE: Fn ≤ 0.20 → L0 (wave < 5–8%, measured); 0.20–0.45 slender → L1;
0.45–0.65 → CFD is the only honest tier at L ≥ 3 m;
(4) DECISION-WORTHINESS: upgrade fidelity only when the expected correction
exceeds `WH_PER_NM_SIGMA_PRODUCT` (0.10) AND a verdict could flip.
Gates 2/3/4 map onto existing seams (`limits.RE_TRANSITION_BAND`,
`FN_MICHELL_MAX`, `WH_PER_NM_SIGMA_PRODUCT`); gates 0/1 are new physics
(windage/orbital estimator; the wave-existence flags). First code
consequence already landed: `holtrop.envelope_violations` gained the missing
Reynolds clause (it validated a 0.5 m hull at Re 2.3e5 that
`resistance.flow_regime` refuses — the L1H badge could contradict L1).

**The size floor this buys the roadmap:** the full-fidelity window closes
below L ≈ 2.6 m (no speed is simultaneously turbulent-Re and displacement-
Fn); the independent evidence agrees (RANS validated at 3 m on Delft 372,
measured ≥30% friction error at 1 m, ITTC's own Re 5e6 stimulation floor,
and 30+ Microtransat attempts at ≤2.4 m with ONE finisher — which optimised
survivability, not resistance). **Minimum sensible maritime drone: 2–3 m
LWL** — and below ~1 m, hull-form calculus never matters at any speed
(environment 4–50x hull drag). The drone line's un-block list is therefore
three items, not one: a transitional friction line (±40%→±15% sigma), the
environment estimator (windage + orbital), and the 2–3 m sizing doctrine —
plus the rulebook gap (ISO/RCD scope starts at 2.5 m).

## 12 · Manufacturing

### 12.1 The shortest real path to a boat you can order

Ruthlessly scoped, and it is the one path where every link either exists or is
derivable from geometry the platform already generates:

```
mission sentence
   └─ governance: category C/D, LH < 12 m  → RCD Art. 20 Module A,
                                              or Art. 2(2)(a)(vii) own-use kit
   └─ hull grammar (developable, plywood-native — BUILT)
   └─ L0 + L1 + R + E + F ladder            (BUILT)
   └─ unroll.hull_panels → developable panels (BUILT)
   └─ NEST onto 2440×1220 sheets, kerf + measured thickness offsets baked in
   └─ DXF with named layers + part labels + T-bone corners
   └─ sheet count × sheet price + epoxy/glass/fasteners schedule
   └─ ORDER: send DXF to an existing CNC kit cutter
```

**The whole structural kit is derived from geometry the platform already
validates.** No catalog dependency, no supplier integration, no interface graph,
no notified body — and the legal path is the cleanest one in the Directive.
Systems (motor, batteries, solar) attach as a **separately-closed** second BOM
with its own closure number and its own clause set.

Two legal facts the user is told plainly, at order time and in the as-built
record: an own-use build is **out of RCD scope only while it stays own-use**, and
**selling it inside five years triggers post-construction assessment**.

### 12.2 BOM closure — the number that makes "ready to order" honest

"548 items — verified — available — ready to order" is a claim, and this
platform does not ship unmeasured claims. Every release carries **closure**,
measured two ways:

- **mass closure** = fraction of validated displacement that resolves to a
  catalog part with a source;
- **cost closure** = fraction of estimated total cost that resolves to a part
  priced `quoted` or `listed` (not `estimated`).

Both are printed on the release. Unresolved items are **listed by name**, never
absorbed into a margin. **A low first number is a finding, not a failure — it
does not get softened.**

Every component mass enters `weights.MassItem` **exactly once**. This is not a
detail: an audit found three placement tables disagreeing by 0.7 m on payload
LCG. A BOM is a mass model with prices attached; if it becomes a fourth table,
stability silently decouples from the parts list.

### 12.3 Bars for the manufacturing tail

- the nested DXF re-parses via `unroll.parse_dxf_polylines`, **every panel is
  present**, and panels re-fold to the hull within the stated millimetre bar;
- the DXF declares its units (`$INSUNITS`) and re-imports at the right scale —
  a shop importing a unitless file cuts a 10 mm part instead of a 10 m one;
- nesting utilisation is **measured** against the 5–10% commercial waste band
  and reported either way; `ply_sheets` is derived **from the layout**;
- a kit whose slot offsets were computed from nominal rather than measured stock
  thickness is rejected;
- a developability metric that can **fail**: a hyperbolic paraboloid is the
  negative control and must not pass the cylinder bar;
- the exported hull is the hull that passed the ladder — station count recorded
  in the export receipt, or defaulted to the validated discretisation.

### 12.4 The order package

Nested DXF set, both BOMs with closure, assembly sequence, cut/consumable
schedule, the ladder report (physics + rules + E + F badges), a
technical-documentation stub structured per RCD Art. 25 / Annex IX, the declared
delivery mode, and the caveats it depends on.

**Bars:** the release **refuses to emit** when governance routes to "notified
body required"; the own-use path prints the five-year rule verbatim with its
article; a non-expert goes from one sentence to a release unassisted; every
number in the package traces to an evidence-graph node — spot-checked on ≥ 20
randomly sampled numbers, **zero untraceable**.

---

## 13 · HookProbeOS + HEQK — stated as an assumption

**That repository has not been read and cannot be audited from here. What
follows is a requirement list, not a finding.**

The capability-security posture is a genuine differentiator for one specific
reason: a weather-data parser and a camera pipeline are *the* two components in
a maritime stack most likely to be handling untrusted input, and neither has any
business being able to reach motor-control memory. If HEQK provides capability
isolation, secure IPC, device isolation, cryptographic identity, secure boot and
deterministic scheduling, then the partition set is:

```
SAFETY · NAV · SENSOR · ENERGY · WINDWING · MOTOR · COMMS · TELEMETRY
```

with SAFETY below everything and the **emergency tether release in hardware,
below software altogether**.

To take this further: the HEQK repository, its capability model, its scheduling
guarantees, and whether it currently runs on the intended target. Until then
this section is a specification, not a plan.

---

## 14 · AI and agent architecture

### 14.1 Where the AI is, and where it is forbidden

```
NavalAI (slow, cognitive)   translate · explain · propose — never actuates, never computes
        ↓
Governance / safety envelope (deterministic)  — refuses out-of-envelope requests
        ↓
Trajectory + winch controller (MPC/LQR, 10–50 Hz)
        ↓
Flight controller (PID inner loop, 100–500 Hz)
        ↓
Emergency release (hardware, below software)
```

Law 3 says LLMs translate and explain and have no code path to geometry. Two
extensions, both owed as tested properties:

- **The RUN analogue: no LLM has a code path to an actuator.**
- **The BUILD analogue: no LLM has a code path to the BOM.** Component selection
  is a typed constraint solve; the LLM explains why Motor A won and asks the
  user the question only they can answer.

And both must be tested as **data-flow** properties, not as name disjointness —
the existing geometry-seam test would pass if someone added a field a downstream
caller decoded into a genome.

### 14.1.1 A model council is a DEVELOPMENT tool. It is never a runtime dependency.

Stated architecturally because the confusion has already cost this project a
session. Consulting a second or third frontier model — an MCP council, a
review-by-another-model pass, an adversarial critique of a diff — is a
legitimate and sometimes valuable way to **write** this software. It is a
property of the workbench, like a debugger or a linter.

**It must never appear in the product's dependency graph, its runtime, its CI,
or any gate's evidence path.** Three independent reasons, and any one of them is
sufficient:

1. **Law 3, applied one level up.** An LLM has no code path to geometry. A
   council of LLMs is still LLMs; routing a decision through several does not
   create a code path that law 3 permits, it creates several that it forbids.
2. **Correlated failure is the measured behaviour, not a worry.** Four
   independent models selected the **same wrong branch** on 36 failed runs of a
   benchmarked engineering workflow (`docs/research/PRIOR-ART.md` §5). That is
   the same evidence §14.2 uses to refuse an agent-per-component design.
   Redundant models do not vote their way out of correlated failure; a council
   converts one wrong answer into a *confident* wrong answer.
3. **A network call is an unmeasurable input with a nice interface.** A vendor
   deprecates a model, an API is down, a temperature changes, and a number that
   a gate depended on moves for a reason no receipt records. That is defect
   class 1 with a subscription. §5.2's rule — *the vessel must be fully
   operational with the internet off* — is the RUN form of the same principle,
   and it is not weaker on the design side.

`docs/LESSONS.md` records the operational half ("No external models. One was
dead on arrival, the other returned only advisory prose") and `CLAUDE.md`
records that a global config file has repeatedly sent sessions chasing one. The
architectural half is here: **advisory prose is the ONLY output a council may
produce, and a human merges it as their own change.** If a council's opinion
ever needs to be depended on, it must first become a test, a bar or a typed
constant with a source — at which point the dependency is on the artifact, not
on the model.

### 14.2 Component models, not component agents

The tempting design is an agent per component — solar, motor, battery, rudder,
kite, watermaker. The evidence refuses it: benchmarked LLM engineering
workflows fail *correlatedly* on conditional branches, with four independent
models selecting the same wrong branch on 36 failed runs
(`docs/research/PRIOR-ART.md` §5). Component selection is exactly conditional
("if crew > 3 and no blackwater plumbing then …"). Fourteen agents would produce
fourteen confidently wrong branches, and **redundant agents do not vote their way
out of correlated failure.**

The structure that survives is the one `rules/` already uses — typed objects with
clause provenance, and one reasoning shell above them:

```python
Component:                      # a data contract, not an agent
    id, class, supplier, sku
    physics:      typed curves/params, each {value, tier, sigma, source}
    ports:        typed + united  (48 V DC in, 5 kW out, CAN-J1939, M10×4 @ 120 mm)
    rules:        applicable clauses
    mass:         ONE MassItem → weights.aggregate  (never a fourth placement table)
    commerce:     price {tier: quoted|listed|estimated}, lead_time, availability
    basis:        datasheet | measured | approx      ← no basis, no catalog entry
```

**Compatibility is a graph check, not a judgement**: voltage windows, continuous
and peak current, protocol, bolt pattern — all executable.

**Bars:** an incompatible pairing is rejected **naming the failing port**; a
catalog entry without a `source` cannot be created; every component mass appears
**exactly once** in `weights.aggregate`; adding the systems package changes the
validated displacement and LCG by the amount the ladder predicts.

### 14.3 The agent shell, and how work is delegated in this repository

`agents.py` becomes orchestration above the spine (§4.2) — typed messages, an
audit trail that survives the process, and a `Fitness=∞` fast-reject gatekeeper.

For coding-agent sessions the rules are in `CLAUDE.md` and `docs/LESSONS.md`,
and one of them belongs here because it is architectural: **give each agent
disjoint file ownership and tell it to report what it could NOT verify.** An
agent that refuses a wrong instruction when it meets the code is the
highest-value behaviour observed on this project.

---

## 15 · Validation architecture

### 15.1 How a claim becomes true here

1. **A bar is stated in this file** with the configuration it is measured at.
2. **A gate row is registered** in `navalai/gates.py`, with a suite that must be
   owned (Gate 0G asserts every test file has an owner).
3. **The gate test ships in the same commit as the code**, and its comment names
   the measured incident that motivated it.
4. **A test feeds the guard the verbatim input it must reject.** A test showing
   a guard accepts a good case proves nothing about rejection.
5. **A miss is recorded, never softened** — into `data/gate-ledger.json` with a
   measured watermark, an owner and a `review_by`.
6. **A gap is closed when its proof PASSES**, not when its symbol exists.

Two derived rules that have each caught a real defect:

- **A bar interpolated between two measurements is a guess.** Validate a new bar
  against every historical case: it must refuse the ones that failed and accept
  the ones that worked.
- **A result whose evidence has been deleted is not a result.** The ledger
  refuses to quote a deleted run directory.
- **A guard that reads its own input cannot notice input it never read.** A
  coverage test comparing a predicate table against the queue passes when both
  are missing the same rows. Every importer needs a check on the *source* — a
  count of gradeable tables, a header shape — not only on what it imported.
  Over-import is visible twice; under-import is invisible once and forever.

### 15.2 Work that exists in no machine-checked place

This is the list the consolidation exists to produce. Every item is real work
with **no predicate, no gate and no ledger row**, so nothing in CI would notice
if it were forgotten. Measured 2026-08-11; re-derive before working it.

1. **A second gap-id namespace that nothing checks.** `N6` exists only in
   `CLAUDE.md`; `R5.5` was cited from four documents and from `navalai/gates.py`.
   Neither is a register row. **Every R-number must become a register row, a
   gate, or a retirement notice.**
2. **The ledger's regression contract is documentation, not code.** The ledger's
   `_README` and the CI workflow both promise *"a RED gate worse than its
   watermark → FAIL"* (`data/gate-ledger.json` `_README`;
   `.github/workflows/gates.yml:66-67`). `judge_red()`
   (`navalai/gates.py:426-443`) checks presence, `review_by` parseability and
   expiry — then reads `wm = entry.get("watermark")` and **interpolates it into
   an f-string**. That is the entire use of the watermark. **Nothing compares a
   fresh measurement against it**, and nothing could: `judge_red` is handed the
   gate NAME and the ledger, never a measurement. In a repository whose thesis
   is that prose is never load-bearing, the regression half of the ledger's own
   contract is prose. Re-verified 2026-08-11 at `e5942d7`.
3. **gap ↔ gate linkage is prose-only.** RE-COUNTED 2026-08-11 at `e5942d7` by
   walking the AST of `scripts/reconcile_gaps.py` — an earlier count of "15
   named, 3 machine-linked" was wrong in both halves and is corrected here.
   Of **120** `Check` rows, **14** name a gate in their evidence string (`A1`,
   `D1`, `D9`, `D10`, `D11`, `D12`, `E1`, `F16`, `F17`, `I10`, `I13`, `J1`, `J3`,
   `J5`) and **7** are machine-linked (`D8`, `D11`, `E1`, `F16`, `F17`, `J3`,
   `J5`) — five via `ledger_has()`, two more by grepping `navalai/gates.py` for
   the `Gate("Gate X"` row. **Eight name a gate that nothing checks.** The
   structural finding survives the correction intact: `Check` has exactly three
   fields — `source_id`, `evidence`, `closed` (`scripts/reconcile_gaps.py:423`)
   — there is no field on `Gate` either, no mapping table and no test, so **you
   cannot systematically say which gap blocks which gate.** Cheapest structural
   upgrade available: a `gate: str | None` on `Check`, plus a test that every
   named gate exists in `GATES`.
4. **Three behaviour predicates can be closed by a comment — and two more that
   look like them must be left alone.** `A4` and `F4` call `has()` on Python
   files inside an `any(... for rel in (...))`, and `E2`'s first clause calls
   `has("benchmarks/wigley.py", "REFERENCE_CW")`. `code()` exists precisely
   because a gap once closed on the word appearing in a comment *on the defect*
   (B4, and `code()`'s docstring is the record of it).

   **The exposure is latent, not live.** MEASURED 2026-08-11 at `e5942d7` by
   evaluating both forms of each clause: every one of the three matches REAL
   code today (`flywheel.py` for `A4`, `seakeeping.py` for `F4`,
   `benchmarks/wigley.py:239` for `E2`), so `has` and `has_code` agree and **no
   gap is currently mis-closed.** What the conversion buys is that they cannot
   become mis-closed by an edit to a comment. `E2` is nonetheless the sharpest
   case: `REFERENCE_CW` also appears in a COMMENT at `benchmarks/wigley.py:197`,
   so that clause would survive the symbol being deleted.

   **And the conversion must not be applied by pattern.** `F19` asks
   `has("benchmarks/kcs.py", "SEVEN groups")` and `has(..., "min/max over these
   seven rows")`; both strings live in comments at `benchmarks/kcs.py:136-141`
   **on purpose**, because `F19` is a claim about an ATTRIBUTION, not about
   behaviour. MEASURED: converting it flips both clauses `True → False`, i.e. a
   closed row would report OPEN forever. `E2`'s second clause,
   `lacks("not an independent validation")`, is the same kind. `code()`'s own
   docstring already states the law — *"a predicate about BEHAVIOUR reads
   `code()`, and only a predicate about PROSE (`F19`'s attribution, `J8`'s
   retraction, `J7`'s supersession markers) reads `text()`. Both exist, and the
   choice is made per row."* A blanket sweep would have broken the rows that
   document this project's retractions, which is the same class of damage as
   deleting them. **Convert per row, and measure the verdict in both directions
   before and after.**
5. **Bars with no gate** — see §15.3.
6. **SELL and RUN are absent from the register, and it does not know.** Grepped
   across the register: **zero** occurrences of `telemetry`, `in-service`,
   `fleet`, `as-built`, `commissioning`, `sensor`, `field data`, `customer`.
   This is structural, not an oversight: the importer files only what the
   2026-08-05 audit found, and that audit was scoped by four documents **none of
   which contains a RUN phase**. Seven parallel audits could not have found a
   RUN gap. SELL is half-covered under another name (customer-intent fidelity is
   the register's strongest section) but there is **no row about price,
   quotation, lead time, or any customer-facing artifact.** File the RUN gaps
   **before** writing the code.
7. **A second benchmark anchor** (§11.4) is recorded as owed in three documents
   and in no gap row.
8. **The catamaran interference term has no experimental anchor, and the
   citation looks like one.** `navalai/resistance.py` cites Insel & Molland
   (1992) and Molland, Wellicome & Couser (1996) in a comment block; neither is
   TRANSCRIBED, so no measured number from either enters the code. The Michell
   multihull superposition is internally verified — the phase convention is
   `k_y = k0·sec²(θ)·sin(θ)`, checked against an independent complex
   superposition and against the `s → ∞` limit, in `navalai/experiments.py` and
   `tests/test_phase1.py` — but **self-consistency is not validation**, and a
   named citation beside an unvalidated model is the strongest available
   invitation to read it as one. This is item 7 one tier down: §11.4's owed
   anchor is for RESISTANCE; this one is for INTERFERENCE, and neither DSYHS nor
   Fridsma supplies it. No gate row, no register row, no predicate.
9. **The design-pressure formula matches no standard, and the layer above it
   does.** `rules/iso12215.py::design_pressure_bottom` is
   `max(10, 2.4·mLDC^0.33 + 20)`; ISO 12215-5's bottom pressure is
   `P_bm = P_bm_base · k_AR · k_L`, a function of beam, `L_WL`, design category
   and the vertical acceleration `n_CG` — not a simplification of ours, unrelated
   to it. The THICKNESS formula immediately downstream **is** ISO equation (39)
   term for term. `rules/review.py` and `refdata/__init__.py` both record the
   mismatch in prose; nothing fails because of it. **The consequence for the
   plan is a sequencing one:** any item of the form "structure follows from
   pressure" is blocked on the PRESSURE side, not on the scantling side, and
   §16 PV-7 is written to that.

### 15.3 Bars that exist only in prose

Measured against `navalai/gates.py` on 2026-08-11: each bar below either has
**no gate row at all**, or has one that measures something **weaker than the
bar as written** — so nothing fails if the bar itself is missed. Each needs a
gate, a re-negotiation *in this file*, or a recorded retirement.

- ≥ 95% of generated layouts pass L0-A + tier E; ≤ ~1 min per layout.
  `tests/test_arrangement.py` proves every L0-A rule can fire and that each
  refusal names its subject — 40-odd rules, on ONE reference layout. **Nothing
  runs a batch and nothing computes a pass fraction**, so the number in the bar
  has no producer.
- Tier F reproduces the USCG worked examples **exactly**, including the plywood
  **−0.81** negative-contribution case. **Half-gated, and the weaker half is the
  one that exists.** `tests/test_refdata.py:140-149` (Gate V2.0) does check
  `flotation.submerged_factor(sg)` against every printed `MATERIAL_K`, plywood's
  negative sign included — but that is the CONSTANTS TABLE re-derived, not a
  worked example reproduced. There is no `navalai/flotation.py`: tier F exists
  as sourced numbers in `navalai/refdata/flotation.py` and as a letter in
  `weights._TIERS`, with **no computation between them**. Gate V2.0's scope is
  "every constant carries source + basis", which is a different bar.
- The Etap criterion: fully flooded, freeboard loss < 3% LOA, remains
  manoeuvrable. Nothing in `navalai/` computes a flooded condition.
- Every material choice machine-checked against palette rules; the fire-exposed
  flotation redundancy rule enforced by the solver.
- End-to-end: a non-expert produces a full vessel passing every tier, and the
  report prints the purchase/review caveats it depends on.
- Verdict parity with a qualified reviewer on **≥ 3 reference designs** — the
  original Gate 6 bar. The parity gate that exists measures *threshold* parity,
  which is a different thing. `REFERENCE_DESIGNS` and `hand_calculation` appear
  nowhere in the tree, which is exactly what row `D9` asks for.
- ≤ 1–2% surrogate error near optima, measured across ≥ 5 holdout seeds, plus a
  separate *local* gate on a trust region around a Pareto point (which is what
  the published bar actually refers to). Gate 3's error bar is still taken on
  its one chosen seed (991); row `D10` is the ask.
- ≥ 90% of a held-out mission-brief set — the **≥ 100-brief frozen corpus does
  not exist**; today's "held-out" set is 10 in-repo briefs the parser was
  demonstrably tuned against. This is the one entry in this list whose bar IS
  executable (`tests/test_phase5.py::test_translation_set_at_least_90pct`, Gate
  5) and whose **corpus** is the defect. Counted 2026-08-11: `BRIEFS` has 10
  entries.
- ~~p95 < 100 ms on **every** interactive endpoint, not only the one that is
  gated.~~ **REFUTED 2026-08-11 at `e5942d7`.** This bar is gated and the gate
  is not weaker than the bar:
  `tests/test_phase4.py:354::test_every_interactive_endpoint_meets_the_p95_bar_not_just_eval`
  (Gate 4) asserts the p95 on `/generate` at n=3 and n=20 and on `/pareto`
  alongside `/eval`, and its docstring carries the before/after measurement that
  motivated it. Register row `I9` is the same finding and reconciles CLOSED.
  Kept struck through rather than deleted: this list is the argument for P0 work,
  and an item that was already done weakens it if it is removed silently.

**And one bar declared twice, with different values.** The original plan sets
grid uncertainty at **≤ ~2.5%** ("the published bar"); the ledger and
`scripts/gate2m.py:53` set **GCI ≤ 5%**. Two bars for one quantity, and the live
one is 2× looser than the plan.

**A reconciliation does exist, and it is a comment** — `scripts/gate2m.py:49-53`:
*"The plan's Gate 2 bar is 'documented grid uncertainty (target ≤ ~2.5%, the
published bar)'. 5% is the outer limit we will call converged at all; the
Tokyo-2015 groups achieved 2.5-3.5%."* That is a real and defensible argument —
5% is a refusal threshold, 2.5% is a target — but it is prose beside the number
it governs, and it is the only place the two bars are related. So the item is
not "nothing reconciles them"; it is that **the reconciliation has no verdict.**
There is one executable bar (5%) and one aspirational one (2.5%) with no gate,
no ledger row and no owner. **Ratify the two-bar structure by making the 2.5%
target a recorded, owned aim — or delete it. A target nothing can fail is not a
bar.**

### 15.4 What a green predicate does and does not mean

**Predicates check that a symbol or test *exists*, not that it *passes*.** That
is recorded in `navalai/gates.py`'s own words at the point where two rows read
CLOSED while the tests proving them were failing in a file owned by no gate.
Three independent honesty mechanisms were live and all three missed it, because
the reconciler measures *presence of evidence* rather than *the evidence
passing*.

The compensating controls are Gate 0G (every test file is owned) and the
negative control: **all predicates re-run against the commit the register
audited, requiring zero CLOSED.** That negative control is the load-bearing
assurance behind any trust in the reconciler's output, and it is worth running
directly rather than trusting a green suite summary.

`data/evolution/gaps.jsonl` is **worthless as a state source** — it is a
gitignored cache written all-`Open` in one pass. Never read gap state from it;
run the reconciler.

---

## 16 · Roadmap

Ordering rule: **anything that makes the machinery lie comes before anything
that uses the machinery**, extended 2026-08-13 by one clause: **a vessel-level
quantity the ladder does not model at all ranks with the lies, not with the
improvements** (§1.5). Gap ids name rows in `docs/GAP-REGISTER.md`; their text
and their current state come from `python scripts/reconcile_gaps.py`, never from
here.

### P0 — Stop the machinery lying (days)

| # | Item | Done when |
|---|---|---|
| P0-1 | ~~One `RHO_AIR`. Three copies: `dynamics.py` 1.225, `extrapolate.py` 1.226, `cfd/case.py` 1.2.~~ **RETRACTED — see below. The row is kept struck through rather than deleted, because a plan that silently drops a wrong item teaches nothing.** | nothing. The item was wrong, and this row is its retirement notice |
| P0-2 | §15.2 item 2: the ledger's regression contract becomes code. The whole comparison is `wm = entry.get("watermark")` followed by an f-string, at `navalai/gates.py:426-443` | a RED gate measured worse than its watermark FAILS, proven by a test that feeds it one |
| P0-3 | §15.2 item 3: `gate: str \| None` on `Check` (`scripts/reconcile_gaps.py:423-433`, three fields, none of them a gate), with a test that every named gate exists in `GATES` | the gap↔gate map is queryable |
| P0-4 | §15.2 item 4: **the three behaviour predicates** `A4`, `F4` and `E2`'s first clause move from `has()` to `has_code()`. **`F19` and `E2`'s `lacks()` clause do NOT** — they are predicates about PROSE and the conversion breaks them (measured below) | a comment can no longer close a behaviour gap, and no prose predicate was converted with it |
| P0-5 | Two remote refs, `origin/apse` and `origin/worktree-apse`, still appear in `git branch -r` (re-measured 2026-08-11, unchanged). One branch is the law | `git fetch --prune` is run, and either they are gone or they are deleted upstream deliberately |
| P0-6 | The `ALIGNMENT.md` scorecard reconciliation. Recorded here so it has a number instead of a sentence in Appendix A | the scorecard and its rows agree, by its owner |

**Three things this table has already had to unlearn, and they are the reason it
is written this way.**

*A retracted finding can be re-filed by the document that summarises it.* P0-1
said "one `RHO_AIR`". That finding was raised, **measured, and withdrawn at
`140f7e4`** — five commits before this table was written — and the withdrawal
was landed AS CODE, in a comment block at `navalai/dynamics.py:18-36` that names
all three values and ends *"Do not centralise these. State the basis instead."*
The three are three CONVENTIONS and collapsing them corrupts two of them:

| where | value | what it is | what changing it breaks |
|---|---|---|---|
| `dynamics.RHO_AIR` | 1.225 | ISA sea level, dry, 15 °C — used for the windage bluff-body load only | nothing; it is the only free one |
| `extrapolate.air_resistance_coefficient(rho_air=…, rho_water=…)` | 1.226 / 1026.0 | the ITTC-78 pair at 15 °C. `C_AA = c_d · (ρ_air/ρ_water) · A_T/S` depends on the **RATIO** | moving one without the other silently rescales every ITTC-78 extrapolation |
| `cfd/case._RHO_AIR` | 1.2 | what is **written into** the OpenFOAM case, beside `_G = 9.81` "matches `constant/g` in the generated case" | the solver desyncs from its own receipt |

This is the `FN_MICHELL_MAX` precedent (§2.3), not the `limits.py` one: **a value
that belongs to a MODEL lives with that model.** What was genuinely missing was
a statement of basis, which is what made a reader see copies — and that is what
`140f7e4` added.

The transferable rule, which is why this is recorded at length rather than
quietly deleted: **a duplicate-number finding is not proved by three literals
differing. It is proved by showing the three are the SAME quantity under one
convention.** Law 2 says a number lives in one place; it does not say three
conventions must become one number. Before filing the next one, name the
convention each value is expressed in — and check `git log` for a retraction,
because this file re-filed one that the code had already answered.

*A failing test is not a plan item.* An earlier revision carried "bisect the
latent-front diversity regression" here; re-measured 2026-08-11 on a clean
`git archive`, it passes. It had become a status restatement with no owner. A
suite failure is fixed in the change that caused it, or recorded in the ledger
with a watermark, an owner and a `review_by`.

*A severity filed at audit time is not a scheduling input.* The shell-area
defect (C9) was filed LOW and, re-measured on 2026-08-11, was moving a badged
quantity and a live constraint in `Evaluation.g`: the true wetted-area ratio is
**1.6879** on the reference hull against a bare literal of 1.6, and **1.251 to
6.702 across 200 grammar hulls** (mean 2.062) — up to **76%** error, −15.4% on
average, *varying systematically with exactly the parameters NSGA-II is free to
move*. It was scheduled here at P0 against its filed severity and closed the
same day. **Read the measurement, not the label** — and because the register is
an immutable audit record, a re-grade is argued in this file rather than edited
into that one.

**On C9, and this is a re-grade request rather than an edit.** It is filed LOW.
Re-measured independently 2026-08-11 it is at least HIGH, and the evidence is in
the codebase's own docstring: `energy.shell_area_m2()` exists specifically to
kill a bare `× 1.6` and says *"`engineer.assess` and the L1 weight path must
plank the same boat"*; `engineer.py` uses it and **`evaluate.py` still reads
`hull.wetted_surface(0.0) * 1.6`**. The docstring's own measurement: true ratio
**1.6879** on the reference hull, **1.251–6.702 across 200 grammar hulls** (mean
2.062) — up to **76%** error, −15.4% average — *and the optimiser searches
exactly that box*, so the error varies systematically with the shape being
chosen. The path is `shell → weight_budget → weight_items → aggregate → KG →
GM`, and GM is both a badged quantity and a live constraint in `Evaluation.g`.
The trailing comment `# computed once, not twice` refers to caching and makes
the line read as already fixed, which is why it survived. **The register is an
immutable audit record, so the re-grade is recorded here for its owner rather
than done — and the work is scheduled at P0 regardless of its filed severity.**

### The 2026-08-12 production audit, and what it re-ordered

`docs/research/PRODUCTION.md` audited the owner's vessel-as-a-system architecture
against the code. It changed this table in four ways, and each is a measurement
rather than a preference:

- **Two proposed phases are REFUTED and are NOT scheduled.** An authoritative
  NURBS hull (both existing paths already emit the same piecewise-linear surface
  and agree to **9.67e-07 m**; smoothing moves points up to **19.07 mm** off the
  analytic hull and takes the chine from 72.0° to 37.8°) and a Blender spatial
  execution engine (voxel remesh takes the chine to **0.0°**;
  `bpy.ops.export_mesh` is an **empty namespace** in Blender 5.2.0). See
  PRODUCTION.md §3. A refuted item gets a retirement notice, not a slot.
- **The mission speed distribution is promoted to P1.** MEASURED: the same
  reference hull is solar-**positive** at 4 kn (`net +0.97 kWh/day`, solar/demand
  1.077) and solar-**negative** at the shipped default of 5 kn (`−20.89 kWh/day`,
  0.393), with daily solar range falling **5.8×** between 3 and 5 kn. The platform
  evaluates one speed, and the default one is the first that fails.
- **The CFD ladder is re-scoped, not cancelled.** MEASURED over 68 feasible hulls
  at a pinned `LWL` and a common Fn 0.2381: a ±50 % common-mode bias on the wave
  term leaves the winner **unchanged** (Spearman ρ ≥ 0.9969), and at the model's
  own declared 25 % hull-specific uncertainty the perturbed winner is in the true
  top 10 in **100.0 %** of 1000 trials. L1 ranks. What L1 cannot do is give an
  absolute number — range varies **2.7×** across a 0.75–2.0 resistance bias — or
  touch three of the four wave problems.
- **The solar roof is filed as new work with a new gate.** It is the largest
  single gap found: the coachroof is a declared 4-number box the geometry kernel
  has never heard of, and its roof contributes **zero m²** to a solar model whose
  binding constraint is PV area.

**What the audit found ALREADY BUILT, and which nothing below re-proposes:**
compliance as a constraint engine (`navalai/policy/compile_policy` — a parameter
box plus appended constraint rows, with a compile-time ratchet law), the
positioned mass spine (`weights.MassItem`/`aggregate`, LCG/TCG/VCG required,
quadrature sigma), `wh_per_nm` as NSGA-II objective 1, the arrangement grammar and
its 12-rule L0-A at a measured 0.44 ms median, Blender's non-authority stated in
its own package contract, and the whole manufacturing chain down to DXF and
nesting. The recurring defect here is a thing declared twice; a roadmap that
re-proposes them would be that defect at plan scale.

### The 2026-08-13 vessel-kernel direction, and what it re-ordered

§1.5 carries the thesis. This is its scheduling consequence. **Every claim below
was re-verified against the code on 2026-08-13 before it entered this file**,
because the direction note was written against commit `c7b7c4b` and the geometry
rebuild landed after it — so several of its premises describe a tree that no
longer exists, and scheduling them would send someone to rebuild working code.
That is the defect this repository has already paid for once: four documents each
claimed the governance kernel and the arrangement grammar did not exist, and all
four were false.

**ALREADY BUILT — not scheduled, and the symbol that proves it.** Read this
table before working any row of PV.

| The note proposed | The state of the code | Proof |
|---|---|---|
| "Replace the current three-point section model" | **Built, and the premise is stale.** `Hull.section()` is ADAPTIVE: 3 points at `roundness == 0` (the old shape, exactly) and `2·SECTION_FILLET_SAMPLES + 1 = 257` above it. `section_control()` returns quadratic-Bézier controls whose immersed area is CLOSED FORM | `geometry.Hull.section`, `geometry.section_control`, `geometry.SECTION_FILLET_SAMPLES`; fenced by `tests/test_geometry_kernel.py` |
| "P0: SAC + DWL + a section law" | **Largely built.** `sectional_area(params, x)` is closed form at the DWL, `design_waterline(params, x)` gives `y_WL(x)`, and `Cp`/`lcb` are GENES the area curve is SOLVED to deliver rather than emergent outputs | `geometry.sectional_area`, `geometry.design_waterline`, `geometry.sac_exponents`; acceptance bar and before/after in `tests/test_geometry_kernel.py::test_the_kernel_delivers_the_prismatic_and_lcb_it_was_asked_for` |
| "P0: a validity-aware resistance ladder" | **Built.** `FN_MICHELL_MAX = 0.45`, enforced, with an `L1-INVALID` badge that `evaluate.tier_rank` ranks at −1, BELOW L0 — so an out-of-envelope number can never win a `>=` comparison against a valid one | `resistance.FN_MICHELL_MAX`, `evaluate.tier_rank`, `evidence.L1_INVALID` |
| "the 15-parameter genome" | **Wrong count: it is SIXTEEN.** `grammar.PARAMS` is `LWL, BWL, T, D, Cp, lcb, x_mb, r_transom, beta_mid, beta_bow, beta_len, roundness, rocker, forefoot, flare, sheer_rise`. "Fifteen" is the PRE-rebuild genome and survives in `geometry.py`'s docstring as history, correctly labelled | `len(grammar.PARAMS) == 16` |
| "P0: multi-condition hydrostatics (light ship / design / full payload)" | **Genuinely absent from the code — and already SCHEDULED, at P3-2, with a bar (Gate 9L, five conditions, worst-case governing) and a stated prerequisite (P3-1).** It is not re-filed here | §16 P3 |
| "P1: active learning" | **Already the shape of P8**, which widens `flywheel` past its own `evaluate()`. Not re-filed | §16 P8, §1.3 |
| "P2: generative models LAST" | **Already the plan's position**, argued from the competitive side rather than the ordering side: §1.4 says *do not compete on generative hull modelling*. The direction's ordering argument — geometry → physics → validation → dataset → surrogate → active learning → generation, because *a diffusion model on a wrong manifold makes many excellent wrong hulls* — is the stronger form of the same conclusion and is adopted as PV's closing note | §1.4 |

**Two of the note's five P0 items were therefore already built.** What follows is
the remainder, in the order the measurements justify.

### PV — The vessel kernel: the ladder evaluates the vessel it was asked for

**Where this sits: after P0, before P1.** Its first three items are P0's defect
class — the machinery reporting a number for a vessel it is not evaluating — but
they are not P0's effort class, so they are not crammed into a table headed
"(days)". PV-4 onward is P1-class and runs alongside P1.

The measurements that justify this ordering were taken on 2026-08-13 and are
**not restated here**. They live in `navalai/experiments.py` (Gate 0X; reproduce
with `python -m navalai.experiments`), `docs/research/HULL-FORM-RULES.md` and
`docs/research/HULL-GAN-PAPERS.md`.

| # | Item | Gate | Done when |
|---|---|---|---|
| PV-1 | **Multihull hydrostatics: `I_T = Σ_j [ I_T,j + A_wp,j · d_j² ]`.** It does not exist — `navalai/hydrostatics.py` has no separation, no demihull and no hull count, so a slender demihull is judged by a MONOHULL stability floor and rejected for being what the brief asks it to be. The suite's feasibility and GM distribution, and the one design that floats at a NEGATIVE GM, are in `navalai/experiments.py`. **This is the largest single unlock in the tree** | **new Gate 11H** | `hydrostatics` returns a transverse metacentre for a declared multihull, `gm_floor` is applied to the VESSEL and not to one demihull, and a test feeds it the negative-GM design and gets a feasible catamaran and an infeasible monohull from the same demihull |
| PV-2 | **A vessel declares its hull count and separation, and `total_resistance` uses them.** `michell_rw(..., separation=s)` already exists and its phase convention is verified three ways (`k_y = k0·sec²(θ)·sin(θ)`), but the ONE production call site — `resistance.py:782` — passes no separation, so every catamaran this project has evaluated was scored as one isolated demihull. **CORRECTION to the note, and it changes the size of the job: this is not "one call site".** There is no `separation` to pass: `grammar`, `mission`, `limits` and `evaluate` contain the word nowhere. The genome must carry the variable, or the mission must, before the call site can be fixed | **Gate 11H** | a genome or mission declares `n_hulls`/`separation`, `evaluate()` reports a catamaran's resistance and its demihull's separately, and the interference is a swept quantity rather than a constant. The badge must still refuse: PV-2 makes the term LIVE, and §15.2 item 8 records that it is UNVALIDATED |
| PV-3 | **An objective that cannot be gamed by growing the boat.** **CORRECTION to the note, verified in `optimize.py`: wetted area IS already in the objective.** `HullProblem` minimises three things — `wh_per_nm` (which is `R_w + R_f`, so both resistance components are already priced), `build_area = wetted_surface(sheer) + deck_area()`, and distance from the middle of the GM band. What is genuinely absent is a **curvature / double-curvature / panel-count** term: `engineer.assess` computes `panel_count` and `panel_area_m2`, and `grammar` C43 measures bottom-panel twist per metre, and **none of them enters `F`** | **new Gate 12O** | the objective tuple is READ from one place (P1-3 already requires that), and a hull that halves `R_w` while doubling panel count or double-curvature area is measurably worse on `F`, proven by a test that constructs one |
| PV-4 | **A multi-chine section law.** The grammar reaches **two of the five standard body plans** and has ONE chine; the two it cannot draw are the double-chine forms (`docs/research/HULL-FORM-RULES.md`). Multi-chine is the plywood answer to a round bilge, and it is the honest replacement for the `roundness = 0` pin now applied to sheet-built typologies — that pin is a STOPGAP correct for the unroller we have, **not a principle** | **new Gate 13C** | the grammar draws all five body plans, and `hull_ast.Pin(roundness)` is retired against a section law rather than against a tolerance |
| PV-5 | **Non-uniform, feature-aware stations** — dense at the bow, maximum beam, chine and transom; sparse through the parallel midbody. 41 uniform today. **Sequenced deliberately AFTER PV-1..PV-4**, because a station change moves every number in the tree and the cost is measured: 41 → 81 is +51 % on `evaluate()` and 161 breaks Gate 1's 50 ms bar. The one home of that measurement is the comment block at `navalai/export.py:112`, where a proposal to raise `Hull.n_stations` was declined and the export path was fixed instead (`export._LOFT_STATIONS = 161`, station-aligned) | **Gate 1** (unchanged bar) | a feature-aware distribution beats 41 uniform on the same accuracy metric at **no more** wall-clock, or the item is retired with the measurement that retired it |
| PV-6 | **Buildability and cost as an objective, not a report.** Panel count, unique parts, double-curvature area, seam length, waste and build hours. This is PV-3's second half and it is what makes PV-3's bar reachable; it also feeds P1-5's quote | **Gate 12O** + P1-5's `Q1`/`Q2` | a cost objective is on `F`, sourced from `engineer.assess` rather than from a second table |
| PV-7 | **The structural chain, blocked on the PRESSURE side.** "Structure downstream of pressure" cannot be built until §15.2 item 9 is resolved: our design pressure matches no standard while the thickness formula immediately downstream is ISO equation (39) term for term. Free sources that deliver numbers are catalogued in `docs/research/standards/` | **Gate 6R** | the pressure formula either cites a standard or is labelled in code as a placeholder that the thickness formula must not be read as validating |
| PV-8 | **A physics fingerprint** (`Φ_H`, including moments of the SAC derivative). Cheap once PV-3 is fixed, and it has an independent derivation worth reading first: `docs/research/HULL-GAN-PAPERS.md` §1.4 records that the p-th moment of `S'(x)` **is** `−p` times the `(p−1)`-order longitudinal geometric moment, and that the same source states the limit honestly — moments capture the wave-making side, not the viscous side | **Gate 12O** (fingerprint clause) | the fingerprint is computed, and the quantity it is NOT predictive of is named in the same place |

**The warning PV-3 exists to answer, stated at the confidence the evidence
supports.** The direction note reports that performance-guided optimisation
elsewhere cut wave drag dramatically while total surface area rose ~2.1×,
bottom-half surface ~4.4× and Gaussian curvature ~1.51×.

- **Those three figures are UNVERIFIED.** They are attributed to ShipHullGAN and
  they do not appear in `docs/research/HULL-GAN-PAPERS.md`'s read of that paper.
  Do not quote them.
- **The mechanism, however, is CONFIRMED from the paper itself and by its own
  authors.** `docs/research/HULL-GAN-PAPERS.md` §1.9 records that only WAVE
  resistance was optimised, that the authors state the optimised designs "possess
  a larger wetted surface, increasing the frictional resistance component", and
  that the solver used to score them is stated to be unreliable exactly on the
  unconventional designs the model exists to produce.
- **So the risk is real and our exposure is PARTIAL, not total** — `wh_per_nm`
  already prices `R_f` and `build_area` already prices wetted area (PV-3). The
  uncovered surface is curvature and panel count, and that is what PV-3's bar
  measures. **A test written to the confirmed mechanism is worth more than a
  figure copied from a summary**, which is the whole reason this row is phrased
  as a bar rather than as a number.

**Generative models stay LAST, and the ordering argument is now sharper than the
competitive one.** §1.4 says do not compete on generative hull modelling; the
direction adds why the ORDER matters independently of that: geometry → physics →
validation → dataset → surrogate → active learning → generation, because a
generative model trained on a wrong manifold produces many excellent wrong hulls.
`docs/research/HULL-GAN-PAPERS.md` §1.2 supplies the specific reason the nearest
competitor's representation would not close our measured gap even if adopted
wholesale: it is a smooth-loft encoding with no chine anywhere in the work, and
the two body plans PV-4 needs are exactly the ones it is least equipped for.

### P1 — The mission becomes a profile, and SELL becomes a product (weeks)

Ordered first because everything downstream is evaluated *at* whatever the
mission says, and today the mission says one number.

| # | Item | Gate | Done when |
|---|---|---|---|
| P1-1 | **`MissionSpec` carries a weighted speed profile** — `speed_profile: tuple[(kn, weight), ...]`, clamped through the existing `FIELD_RANGES` mechanism, defaulting to a single point equal to `cruise_speed_kn` so every existing caller is bit-identical | **new Gate M2** | a mission with a profile produces an `E_mission` that equals the single-point answer when the profile has one point, proven by a test that feeds it both |
| P1-2 | **`EnergyReport` gains `e_mission_kwh_day` as a weighted integral** over `R(V)` — the loop wraps the existing `total_resistance` + `energy_report` calls; the sigma combines per-point sigmas, it is not re-declared | **Gate M2** | the 4 kn / 5 kn reversal recorded in PRODUCTION.md §2.1 is reproduced by a test, and a profile weighted to 4 kn and one weighted to 5 kn return different feasibility |
| P1-3 | **`optimize.py` objective 1 becomes the integral**, not the point. `ParetoResult.F`'s stale `# (wh_per_nm, build_area, -gm)` comment is corrected in the same change — it still names a `-gm` objective that the GM-band change replaced | **Gate 1b** (NSGA-II Pareto front) | the objective names are a tuple in code rather than a comment, so the comment can no longer disagree with `F`, proven by a test that reads the tuple |
| P1-4 | `B4` (payload flat regardless of crew), `B5` (nothing costs length), `E1b` (Holtrop implemented and anchored but **not wired into `evaluate()`** — and our own small craft fall outside its envelope, so wiring it must carry the `L1H-INVALID` badge rather than silently substituting) | gaps; predicates in `reconcile_gaps.py` | the predicates close |
| P1-5 | §3: freeze and hash the mission contract; `PriceValue` with a tier and an expiry; BOM pricing and cost closure; feasibility negotiation over `Evaluation.g`; render the delivery route `policy/legal.py` already computes and shows nobody | **new gates M1, Q1, Q2, N1** | as specified in §3 |

### P2 — The solar roof becomes an object (weeks)

The binding constraint of the product line is PV area, and PV area is currently
`Hull.deck_area() × 0.55`, which excludes the coachroof entirely. This is ahead
of loading conditions and ahead of the interior solver because it changes
displacement, VCG, windage **and** the objective at once.

| # | Item | Gate | Done when |
|---|---|---|---|
| P2-1 | **The coachroof enters the geometry kernel.** `arrangement.Trunk`'s four hand-authored numbers (`_TRUNK_X0 = 0.13`, `_TRUNK_X1 = 0.70`, `_SIDE_DECK_M = 0.25`, height from `HEADROOM_PREFERRED_MM`) become genome parameters or a declared sub-spec that `geometry.Hull` can render | **new Gate 8R** | `Hull` exposes a roof surface, and `arrangement.Trunk`'s docstring stops being the only place the vessel's standing headroom is described |
| P2-2 | **PV area is computed from that surface**, not from the sheer plan-form. Roof area, tilt and packing feed `energy.solar_kwh_day`; the existing `panel_packing` stays but stops standing in for geometry | **Gate 8R** | a hull with a coachroof reports more PV area than the same hull without one, and the delta is the roof's projected area |
| P2-3 | **PV mass and roof structure are positioned.** `PANEL_KG_PER_M2 = 12.0` already exists and `VCG_FRACTION["panels"] = 1.02` already places it high; the roof structure itself is not in the budget at all | **Gate 8R** + `weights` regression | GM moves when the roof does, and a roof heavy enough to breach `gm_floor` is refused by the existing `Evaluation.g` row rather than by a new one |
| P2-4 | **Say what is NOT modelled, in code.** Shading, temperature derate, azimuth and wind load on the array are absent; they get `refdata.absent()` entries with an unblocking action, in the pattern `refdata/ergonomics.NOT_SOURCED` already uses | **Gate 8R** | `absent()` names them, so a future reader cannot mistake their absence for a decision |
| P2-5 | **Gate 6D's geometry repair — `C1` continuity at `x_mb`, and bounded `dy/dx` at the stem.** Scheduled HERE, in the same pass, because it is a change to the same file (`geometry.station_geometry`) and the geometry kernel should be opened once, not twice | **Gate 6D** | the refold watermark in `data/gate-ledger.json` improves against its 5 mm bar, measured by the same `unroll.refold_surface_deviation_mm` at the same reference hull and station count. **The bar is NOT softened and the metric is NOT changed** — the two-sided metric replaced the edge-only one precisely because a pairing scored 0.07 mm on the old one while missing the chine by 97.5 mm |

**P2-5 is filed because the audit found Gate 6D had no scheduling home at all.**
It is the fifth and most recently measured RED ledger row, with an owner
(`chief-architect`) and a `review_by`, and it appeared in no phase of the
pre-audit P0–P6. A RED gate with a ledger entry and no plan slot is a work item
existing only in the ledger, which is the §0 law read from the other side. The
two mechanisms are measured in `navalai/unroll.py:84-108`: the sheer envelope
`y_sheer = ys · w**0.15` puts the sheer polyline **65.6 mm off the analytic curve
at 41 stations before developability is asked about** (81.0 / 65.6 / 47.3 /
29.9 mm at 21/41/81/161 — it converges at ~O(h^0.5), so refinement is not the
answer), and the chine/sheer slope discontinuity at `x = x_mb·L` puts a
**6.02–6.16 mm step** into the topside refold, larger than the whole bar by
itself. **Both refold families get WORSE with refinement**, which is why this is
a kernel change and not a tolerance.

**Bar for Gate 8R:** the roof is a first-class surface — it has an area, a mass, a
centroid, and a refusal path — and `solar_kwh_day` is derived from it. It is
explicitly **not** a bar on aerodynamic or structural validation of the roof;
those need the load model P9 is blocked on, and pretending otherwise would be a
bar that cannot fail.

### P3 — Loading conditions, and the constraint row that cannot move (weeks)

| # | Item | Gate | Done when |
|---|---|---|---|
| P3-1 | **`evaluate()` imports `arrangement`.** `Space.mass_item()` / `DeckZone.mass_item()` / `Arrangement.mass_items()` already emit tier-`E` positioned items with a real `y_m`, and the ladder has exactly one importer today: its own test | **Gate V2.1** (extended) | `agg.tcg_m` is non-zero on an asymmetric layout, so the `list` row in `Evaluation.g` stops reading exactly −2.000 on every hull |
| P3-2 | **A loading condition becomes a `(name, items, target)` tuple** and the ladder loops over five: light ship, design, full payload, uneven, extreme CG. `solve_to_displacement` is already a function of a target and a mass list | **new Gate 9L** | each condition reports displacement, draft, trim, heel, GM and freeboard, and a design is feasible only if **all five** are — a design that passes at design condition and fails at full payload is REFUSED, proven by a test that feeds it one |
| P3-3 | **Centre uncertainty propagates.** `MassAggregate` carries `sigma_kg` but no sigma on LCG/TCG/VCG, so the GM badge propagates mass uncertainty and not position uncertainty | **Gate 9L** | the GM badge's sigma moves when an item's position uncertainty moves |

**Bar for Gate 9L:** five conditions, each fully evaluated, worst-case governing.
The expensive part is not the loop — it is that four of the five need mass items
the five-bucket model in `energy.LCG_FRACTION`/`VCG_FRACTION` does not
distinguish. P3-1 is what supplies them, which is why it is ordered first.

### P4 — BUILD earns its guarantees

Unchanged in content from the pre-audit table, unchanged in position: it is
about making built machinery honest, and the audit found nothing that reorders it.

Wire `agents.py` onto `pipeline.py` (§4.2) — the spine has zero production
callers and its gate is green on unused code. Populate `EvidenceGraph` from
`evaluate()` + `db.Provenance` (§6), **and close the tier vocabulary while doing
it** — the reason is argued in §17.1.1 and it is the one thing here that is
cheaper before RUN than after. Resolve the badge-coverage question (§4.3). Close
the demonstration gap (§4.4). Also `E5` (public-CAD hull round-trip), `E9`
(`hull_id` collision), `E14`, `E17`, `E18`, `A6c` (ARD lengthscales saturating at
the optimiser bound), `I5` (calibration beyond one coverage assertion).

### P5 — The physics debts, RE-ORDERED by what the measurement says

The pre-audit order was: settled GCI triplet, then unattended meshing, then added
resistance in waves. **That order is inverted below, and the inversion is
measured.** `docs/research/APSE.md` §4 prices a triplet at **68.7 h ≈ 2.9
machine-days** and proves the stated budget and the ≥20 cells-per-wavelength bar
unsatisfiable together; `docs/research/CFD.md` §2 measures the residual at 3.40
flow-throughs with drift collapsed to 0.31 %, i.e. **not a discretisation
problem** — so a discretisation study has a measured expectation of returning
nothing. Meanwhile the L1 uncertainty every design decision rests on is
`SIGMA_DECLARED`, and both modules say in their own comments that it is declared
and not sourced.

| # | Item | Gate | Done when |
|---|---|---|---|
| P5-1 | **A small-craft resistance anchor** — Fridsma hard-chine, DSYHS, or DTMB 5415 — transcribed with its scatter, and `resistance.py`'s `0.25·rw` / `FORM_FACTOR_SIGMA_DECLARED` and `holtrop.SIGMA_DECLARED = 0.10` replaced by a **measured** spread against it | **new Gate 1S** | the L1 band is a measurement with a citation, and `holtrop.py`'s "Replace it the day a measured spread against tank data exists" comment is discharged. **No OpenFOAM is required for this item.** |
| P5-2 | **`F1` — added resistance in waves.** The one CRITICAL register row: no drift force, no heading sweep, no acceptance data, no gate row, no test. This is **Capytaine at L2**, not interFoam at L3 | **Gate 2**, added-resistance clause | a drift force over a heading sweep, compared to acceptance data, with a bar |
| P5-3 | **`F17` — unattended meshing.** Finish the running 74-hull campaign; then the **`--solve` half**, which is what the bar "meshes AND converges" actually asks for and which has never been measured | **Gate 2U** | the watermark is a meshes-AND-converges rate at the shipped configuration, with N and the configuration in the units string. §11.7 carries the per-hull layer search and its **92 % ceiling on the observed batch** — the search is what makes the residual visible, not the close-out |
| P5-4 | **ONE absolute point on a delivered SKU hull**, to bound the sizing error: range varies **2.7×** across a 0.75–2.0 resistance bias, and that is the number a customer is quoted. One grid, not a triplet; the honest output is a sigma, not a validated C_T | **Gate 2M** (scope note) | an absolute L3 number exists for a hull in the product family, with its flow-through count and its uncertainty |
| P5-5 | **`F16` — the settled GCI triplet. DEFERRED, and deliberately.** It is 2.9 machine-days to bound a discretisation error on a benchmark whose remaining error is measured not to be discretisation, at the cheapest Froude number in the product's band, on a container ship | **Gate 2M** | it is scheduled again only after P5-1 and P5-4, or when a measurement contradicts the paragraph above |

**Free sinkage and trim** (§11.5) stays the next CFD *experiment* if any CFD is
run — the viscous half being right localises the error to exactly what sinkage
and trim move. **It is now COMPUTE, not code:** `sixDoFRigidBodyMotion` has been
wired for some time and the real blocker was KCS's `KG`, which `7b8f628` sourced
into `benchmarks/kcs.py`. §11.5 carries the correction and names the two places
`CLAUDE.md` still states it the old way.

### P6 — The interior solver, and subdivision

| # | Item | Gate | Done when |
|---|---|---|---|
| P6-1 | **The space graph becomes a graph.** `Adjacency` is carried and, by an explicit test, never checked; nothing validates that an adjacency target id even exists (the reference layout points `berth.aft` at `"cockpit"`, a `DeckZone`) | **Gate V2.2** | adjacency ids resolve, and a dangling reference is refused |
| P6-2 | **Egress.** Zero hits for `escape\|egress\|corridor` in `arrangement.py` or `rules/`. Blocked on `refdata`'s own `circulation_passage_width_mm`, recorded as NOT_SOURCED and called "the single most load-bearing number in an interior arrangement" | **Gate V2.2** | either the number is purchased and the rule is written, or the absence stays logged and the gate says so — it must not be invented |
| P6-3 | **The inner optimiser.** `Arrangement.to_vector()` / `from_vector()` / `bounds()` and `n_slots == 64` already exist as the socket; `optimize.py` references `arrangement` nowhere | **Gate V2.3** | a layout is searched inside a hull the outer optimiser proposed, and the two exchange constraints through `Evaluation.g` rather than through a new vector |
| P6-4 | **Watertight subdivision as a second graph** — `Compartment`, `Bulkhead`, permeability, a damage case, ΔGM. Genuinely absent: in this tree "bulkhead" means a sheet of plywood in a BOM | **new Gate 10F** | a flooded compartment recomputes GM, and a design whose ΔGM breaches the floor is refused |
| P6-5 | **ISO 7250 and ISO 15537 enter `refdata`** — as data if purchased, and **as `absent()` entries either way.** They are the one hole in this repository's otherwise complete absence-logging discipline: unlike Panero & Zelnik and ABYC H-41, they appear in neither `NOT_SOURCED` nor `PURCHASE_QUEUE` | **Gate 6R** (purchase queue) | the queue names them |

### P7 — The rules moat

`D9` — verdict parity on ≥ 3 reference designs, the bar the original plan set and
nothing implements — plus `I13` (a recorded non-expert session), the purchase
queue in priority order (`docs/research/COMPLIANCE.md` §9), and ES-TRIN's
remaining scope work. **And the six rule ids that appear in neither `confirmed`
nor `unconfirmed`** (`R-SCP`, `E-DECK`, and the four ES-TRIN ids) get a decision
either way — `rules/review.py`'s own law is that "a rule missing from both sets is
an oversight; a rule here is a decision."

### P8 — RUN, and the loop closes

`I1` (co-kriging has never seen a real high-fidelity number) and `I14` (the
surrogate spine has no consumer) widened into a real high-fidelity arm:
observation rows in `db.py`, a generic delta engine, a `flywheel` data source that
is not `evaluate()`. **This is the phase that makes the learning loop stop being
closed on itself.** File the RUN gaps before writing the code.

**P5-1 is this phase's cheap rehearsal.** A tank anchor is the same shape of
thing as a delivered hull — an observation NavalAI did not generate — and it is
available now, in a book, for the cost of a transcription.

### P9 — WindWing

Blocked behind P1 (environmental state on the mission) and the preconditions in
§10.2 — no 6-DOF model, no roll RAO, no centre of lateral resistance. **The LOAD
gate comes first**, not the power model. W2 stays recorded as blocked.

### Retirement notices from the 2026-08-12 audit (PLM §3 step 7)

Recorded here rather than silently dropped, because a plan that quietly deletes a
proposal teaches nothing and invites its re-filing — the same reason P0-1 above
is kept struck through.

| Proposal | Why it is not scheduled |
|---|---|
| ~~An authoritative NURBS hull replacing the "crude STL-first geometry"~~ | **REFUTED.** `export_step` already emits 200 B-spline faces and **every one is degree 1×1 with a 2×2 pole net** — a bilinear quad in NURBS clothing — because `makeLoft(ruled=True)` is what makes a plywood panel developable. Blender reproduces `closed_mesh` to **9.67e-07 m**, so there is no second geometry with a different answer. One Catmull-Clark level moves points **up to 19.07 mm** off the analytic hull and drops the chine 72.0° → 37.8°; with creases it is at best *equal*, for 4× the triangles. PRODUCTION.md §3.1. **What the kernel does owe is `C1` at `x_mb` and bounded `dy/dx` at the stem** — two properties of the existing analytic hull, and the measured cause of Gate 6D's refold residual. That is a grammar repair, filed against Gate 6D, not a new kernel |
| ~~Blender as the spatial execution engine~~ | **REFUTED.** Voxel remesh at 0.05 m takes the chine dihedral to **0.0°** on all three hulls tested ("not a rounded chine, it is no chine") and self-intersections from 3–237 to 1479–1866. `bpy.ops.export_mesh` is an **empty namespace** in Blender 5.2.0 — there is no Paper Model add-on and no DXF exporter — and unfolding a 289 000-triangle mesh yields confetti, not boat panels. `navalai/unroll.py` already unrolls ruled panels and exports DXF in millimetres. Blender stays what its own package contract says it is: rendering and independent measurement. PRODUCTION.md §3.2 |
| ~~"CFD calibration is over-invested, so stop CFD"~~ | **Half right, and the half matters.** L1 ranks (ρ ≥ 0.9969 under ±50 % common-mode bias; winner in the true top 10 in 100.0 % of trials at 25 % hull-specific error), and the design loop has never consumed CFD — `optimize.py` imports nothing from `navalai.cfd`. But at the default cruise point **59 % of `R_T` is the Michell wave term**, its sigma is *declared and not sourced*, and there is no tank anchor anywhere in the repository. The spend moves to P5-1 and P5-2; it does not stop. PRODUCTION.md §4 |

---

## 17 · Dependencies

### 17.1 The graph

```
P0 stop the machinery lying     ← BLOCKING. Nothing below is trustworthy until done.
     │
PV vessel kernel                ← PV-1..PV-3 are P0's DEFECT class at P1's EFFORT
   (multihull hydrostatics,       class. The ladder must evaluate the vessel it was
    separation, objective)        asked for before anything optimises against it.
     │                            PV-4..PV-8 run alongside P1.
     │
P1 mission becomes a profile    ← everything downstream is evaluated AT the mission
     │
     ├──────────────┬───────────────┬──────────────────────┐
P2 solar roof   P4 BUILD        P5 physics debts       P7 rules moat
     │           guarantees      (P5-1 needs no          (parallel with P4)
     │               │            compute; P5-3 is
P3 loading           │            compute-bound)
   conditions        │                  │
     │               └────────┬─────────┘
P6 interior solver            │
   + subdivision         P8 RUN + delta engine  ← genuinely blocked: the
                              │                   high-fidelity arm needs P5's rows
                         P9 WindWing  ← blocked on P1 (environmental state)
                                        and on §10.2's own P1/P2/P3/P5
```

- **P0 is blocking** for the same reason it always was: while a check can be
  edited to green, every subsequent claim of progress is unverifiable.
- **PV-1..PV-3 are blocking for the optimiser, not for the suite.** They are
  ordered above P1 because P1 changes what the objective INTEGRATES and PV-3
  changes what the objective CONTAINS; doing P1 first means writing the speed
  integral against an objective that is about to gain terms. PV-1 and PV-2 are
  independent of both and can start immediately. **PV-5 must not start before
  PV-1..PV-4 land** — it moves every number in the tree and the phases above
  need a stable baseline to be measured against.
- **P1 is newly blocking for the physics phases**, and that is the 2026-08-12
  audit's structural change. `E_mission` is an integral over a speed
  distribution; until the mission carries one, every objective, every energy
  number and every solar-fraction verdict is a sample of one point — and
  MEASURED, the shipped default point is the first one that fails.
- **P2 precedes P3** because the roof moves displacement, VCG and windage, so
  loading conditions computed without it would be computed for a different boat.
- **P4 and P7 are independent of each other** and can run in parallel across two
  owners.
- **Within P5, P5-1 is effort-bound and P5-3 is compute-bound.** P5-1 (a
  small-craft tank anchor) needs **no OpenFOAM at all** and unblocks every sigma
  in the ladder; start it first and let P5-3's campaigns run beside it.
- **Only P8 is truly blocked by physics.** A surrogate starved of high-fidelity
  data cannot be fixed by effort.
- **§10.2's P1–P6 are a different namespace** — they are WindWing's preconditions,
  not this graph's phases. The collision is unfortunate and is called out here
  rather than renamed, because §10.2's labels are cited from `docs/GAP-REGISTER.md`.

### 17.1.1 "Land the evidence graph before RUN" — argued, and the reorder refused

An external re-audit on 2026-08-11 proposed moving **EVIDENCE GRAPH** ahead of
**RUN**, on the grounds that *"otherwise the first real boat telemetry arrives
and you don't have the evidence infrastructure to ingest it correctly."* The
concern is right and the reorder is unnecessary; both halves are worth writing
down, because the second half is only true by construction and could be undone
by a well-meaning edit.

**The order is already this.** Populating `EvidenceGraph` from `evaluate()` +
`db.Provenance` is a **P4** item (§16); RUN and the delta engine are **P8**; and
§17.1's graph already has P8 downstream of P4. Nothing needs to move. The
reorder would be a no-op that looked like a decision.

**But the mechanism named is the wrong one, and that does change what P4 owes.**
`EvidenceGraph` is a design-RATIONALE DAG — Requirement → Decision → Assumption
→ Experiment → Evidence, confidence as the minimum over the ancestor set. It is
not an ingestion path and it is not where a telemetry row lands. Telemetry lands
in `db.py`, next to `Provenance`, which records *what was computed*. Ingesting
an observation "correctly" needs three things, and only the third is the graph:

1. **The identity chain** (§6.2). MEASURED 2026-08-11 at `e5942d7`: `mission_id`
   appears **nowhere** in `navalai/`, `ui/` or `scripts/`, and `MissionSpec` is a
   plain `@dataclass` (`navalai/mission.py:106`), not frozen. `vessel_id` and
   `telemetry` return zero hits meaning those things. Only `db.hull_id` exists,
   and it has a known collision defect (`E9`, still open). **An observation you
   cannot join to a promise is a number, not evidence.**
2. **A tier that means "measured on a real boat"** (§8.1). `db.py`'s `result`
   table admits `{L0,L1,L2,L3,R}` and there is no such value.
3. **A graph whose shape you already know**, which is the reviewer's point in
   its strongest form. The schema is ALREADY able to hold an observation:
   `Kind.EXPERIMENT` may support `Kind.EVIDENCE` (`navalai/evidence.py:49-56`)
   and `Node` carries `tier`, `value` and `sigma` (`:59-69`). So the risk is not
   that the graph will refuse telemetry. **It is that the graph's first real
   population will BE telemetry** — the hardest case, arriving as the debut of a
   machine with no baseline, in a subsystem whose only current callers are a
   demo and two tests (`EvidenceGraph(` is constructed in exactly three places:
   `scripts/demo_apse.py:81`, `tests/test_stageG.py:571` and `:601`). Exercising
   it first on computed results, where the right answer is known and cheap to
   recompute, is what makes the telemetry case debuggable.

**One defect this argument exposes, which is why it was worth having.**
`Node.tier` is a free-form `str` defaulting to `""` — nothing constrains it to
the ladder's vocabulary. A real-boat observation is therefore admissible today
**under any spelling**, including a typo, and `tier_rank`'s whole trick (a claim
may not outrank its evidence; `S1` is −1 so a surrogate can never satisfy a
ladder requirement) is bypassed by a node that simply says something else.

So, as a **bar on the P4 item rather than a reorder**: the evidence graph is
populated from computed results first, and **before any observation row exists,
the tier vocabulary is CLOSED** — one enumeration, shared by `db.py`,
`Evaluation.badges` and `evidence.Node`, containing exactly one value that means
"measured on a real boat" — so the first telemetry cannot invent its own tier
and rank itself.

### 17.2 Standing dependencies that are not phases

- **The ledger's review dates are a scheduling dependency.** A `review_by` that
  passes turns the suite red by design. Clearing a compute-bound gate is a
  multi-day solve on the Mac node, so check the dates in
  `data/gate-ledger.json` *before* planning compute, not on the day.
- **Purchases block bars.** ISO 12215-7 blocks any catamaran SKU; ISO 12217-2
  blocks any kite-rigged SKU; the 2024 ISO 15085 clauses and ABYC values block
  exact deck and reboarding bars. Priority order in
  `docs/research/COMPLIANCE.md` §9.
- **A second benchmark anchor blocks any small-craft physics claim** (§11.4).
- **The Mac node thermally sleeps.** Any run over ~6 h must be resumable, and a
  crash must be told apart from a nap. Both are handled; both must stay handled.

### 17.3 Honest reading of effort

P0 is days and is the highest value per unit effort in the plan — it is what
makes every other number believable. **P1 is the next-highest and it is also
days**: the loop over a speed profile wraps two calls that already exist and
already carry a sigma, and it changes what the optimiser optimises. P5-3 and
P5-4 are measured in **days of wall-clock compute** on a machine that thermally
sleeps; P5-1 is days of *reading* and needs no compute at all. The two genuine
research risks are the arrangement generator (no industry-adopted solver exists)
and WindWing W2 (which is blocked on physics that does not exist yet);
everything else is engineering.

The system is roughly **one plan behind where its documents used to read**: the
engine is real and well-policed, the enforcement mesh is stronger than most
production codebases, and the layers above and below it — SELL, and RUN — are
almost entirely unbuilt.

---

## Appendix A · Retirement notices (PLM §3 step 7)

Nothing was deleted; everything was moved. The table in §0 is the map. What each
retired document **lost**, recorded so the removal is reviewable rather than
silent:

| Retired | Kept | Lost |
|---|---|---|
| BuildPlan 1 | the literature sweep and its verdicts | Phases 0–7 as a schedule; the "49 constraints" (built: 9 live) and "45–90 params" (built: **16** — corrected 2026-08-13 from 15, which was the pre-rebuild genome; `len(grammar.PARAMS)` is the one home of the count) |
| BuildPlan 2 | the sourced ergonomics and flotation constants | V2.0–V2.6 as a schedule; its bars are in §15.3 until gated |
| BuildPlan 3 (mission→order) | the governance argument and the regulatory research | V3.x as a schedule; its §0 summary of RCD Art. 20 for category D, which `policy/legal.py::DISCREPANCIES` records as wrong with a passing test |
| BuildPlan 3 (gap closure) | the eliminated-hypothesis record | R0–R7 as a schedule, largely landed; R5.5's headline framing, superseded by the 2026-08-07 re-measurement |
| Stage plan | its dependency reasoning, inherited by §17 | S0–S7 as a schedule |
| HLD | §1–§8, which are §2 of this file | §9–§11, which were second copies of state the runners own; §11 described a repository crisis in the present tense after it had ended |
| APSE, pressure-oscillation, end-to-end audit, CFD blocker brief | everything, as `docs/research/*` and §4 | nothing |
| PLM §5–§6 | — | the gate registry restatement and the roadmap board; §1–§4 are narrowed and kept |
| `docs/VESSEL-KERNEL-DIRECTION.md` (2026-08-13) | the thesis (§1.5), the ordering argument and the work items (§16 PV), the anchor candidate (§11.4), the two debts it surfaced (§15.2 items 8–9) | its measurements, which were NOT copied — they live in `navalai/experiments.py`, `docs/research/HULL-FORM-RULES.md` and `docs/research/HULL-GAN-PAPERS.md`; and **four stale premises**, refuted against the code at absorption and recorded in §16's "already built" table rather than deleted |

### Corrections owed to files this plan must not edit on its own say-so

`CLAUDE.md` states that an agent "should not edit THIS file on another agent's
say-so — surface the correction to the human instead." So, surfaced:

- **Its pointers into the old five-PART structure are now stale.** It cites
  `docs/BUILD-PLAN.md` Part III §1–§8, Part IV.a, and Parts V.a–V.e. §0's
  migration table resolves every one of them, but the citations themselves
  should be rewritten by their owner.
- **The GCI triplet budget in it is wrong by 75%** — it is ~21× the coarse grid
  (~68.7 h), not ~12×, because the timestep is Courant-limited (§11.5,
  `docs/research/APSE.md` §4). This correction has been measured twice and never
  merged back, so a session reads the wrong number first.
- **40 KB of house rules mention neither `policy/`, nor governance, nor the
  compiled legal envelope**, while that subsystem ships with a gate.
- The strikethrough oscillation section in it points at the superseded reading;
  the surviving measurement is `docs/research/CFD.md` §2.

`ALIGNMENT.md` is owed the scorecard reconciliation, which is **P0-6** in §16.
(It was cited as "P0-8" in the first revision of this file, and no such row ever
existed — a plan item that lives only as a cross-reference to itself is the same
defect as a work item that lives only in prose. It now has a row.) It is not
edited here because another session held it on 2026-08-11.

`docs/GAP-REGISTER.md` is owed nothing and must be given nothing: it is a dated,
immutable audit record, parsed by `navalai/gaps.py`, and its gradeable tables
must never be restructured. Corrections to it are made as **new** rows or as
re-grade requests recorded elsewhere — §16's note on C9 is the worked example.

## Appendix B · What this document does not verify

- **Most of the code-state readings above were not executed.** They are static
  reading plus the greps quoted, dated 2026-08-11 at `b5002be`. No gate's colour
  is asserted anywhere in this file.

  **Second exception, 2026-08-13, and it is why §16's "already built" table
  exists.** The vessel-kernel absorption pass (§1.5, §2.6, §16 PV) DID execute
  what it schedules: `len(grammar.PARAMS)`, `resistance.FN_MICHELL_MAX` and
  `geometry.SECTION_FILLET_SAMPLES` were imported and printed; `optimize.py`'s
  objective tuple, `resistance.py`'s single `michell_rw` call site,
  `hydrostatics.py`'s absent multihull term and the zero hits for `separation`
  in `grammar`/`mission`/`limits`/`evaluate` were read directly. **Four premises
  of the source note did not survive** — the three-point section, the SAC/DWL
  work, the validity-aware ladder and the parameter count — and a fifth ("the
  objective does not include wetted area") was refuted at `optimize.py:108`. The
  pattern named in the first exception held again: **every correction came from
  RUNNING something, and every error came from reading.**

- **What that pass did NOT verify.** The population statistics behind PV-1's
  ordering (feasibility fraction, the GM distribution, the negative-GM design)
  were taken on trust from `navalai/experiments.py`'s own output and not re-run
  here; re-run `python -m navalai.experiments` before quoting any of them. The
  ShipHullGAN surface-area and curvature figures are **UNVERIFIED and marked so
  in PV-3** — the qualitative mechanism is confirmed in
  `docs/research/HULL-GAN-PAPERS.md` §1.9, the numbers are not. Whether an
  uncrewed vessel falls inside the RCD's subject matter (§1.5) was not
  determined.

  **Exception, and it is why several claims above changed.** The 2026-08-11
  re-audit pass at `e5942d7` DID execute what it corrected: the `Check`-row
  census in §15.2 item 3 comes from walking the file's AST, not from a grep; the
  `has`/`has_code` verdicts in item 4 were evaluated in both forms on every
  clause; and `scripts/reconcile_gaps.py` was run. Three §15.3 entries and one
  P0 row did not survive that. **The pattern is worth naming: every correction
  came from RUNNING something, and every error came from reading.** An external
  reviewer's summary of this file was the trigger, but it reproduced the file's
  own numbers faithfully — including the retracted `RHO_AIR` item and the "15
  named, 3 machine-linked" count — which is the expected behaviour of a reader
  and the reason a document cannot audit itself.

- **This pass did NOT re-verify the whole of §15.3.** Four entries were checked
  against the code (layouts, tier F, reviewer parity, the brief corpus); the
  material-palette rule and the end-to-end non-expert bar were not, beyond
  confirming that `I13` is open. Treat them as unre-measured.
- **Whether the ladder has ever run above L1 on a real machine.** Whether any L2
  or L3 provenance row exists — i.e. whether `revalidate` has ever actually
  promoted a hull — was not queried. This is the single most load-bearing thing
  left unchecked.
- **Whether `pipeline.py` has ever executed outside tests.** The absent
  `archive.jsonl` is strong evidence it has not, but that path is gitignored, so
  a run on another machine would leave no trace here.
- **HookProbeOS / HEQK were not read** (§13).
- **The Makani repository was not cloned or built**, and the marine-kite figures
  are vendor and press claims (`docs/research/WINDWING.md`).
- **The research provenance the earliest sweeps lead with has no artifact in the
  tree** (`docs/research/PRIOR-ART.md` header).
- **`docs/research/APSE.md`'s cost constants** are attributed to run directories
  that were present on 2026-08-11 but are build artifacts and may be purged.
- **`git log --format='%B' master | grep -c Co-Authored-By` returns 5**, not 0
  (measured 2026-08-11). All five are inside the three commits that *document*
  the no-trailer rule and quote the string. The spirit holds; the measurable bar
  does not, and a bar that cannot be stated exactly is a bar that cannot be
  enforced.
