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
`test_geometric_scale_buys_no_cpu`.

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

So the next experiment is **free sinkage and trim** (`rigidBodyMotion` — code,
not compute), then free-surface resolution, then the grid. And the batch error
must be understood before a triplet means anything: three noisy numbers do not
make a Richardson extrapolation.

**A correction owed to `CLAUDE.md`, measured and never merged back:** the GCI
triplet is **~21× the coarse grid (~68.7 h), not ~12×**. The cell ratios (2.79×,
7.79×) are correct as cell ratios, but the timestep is Courant-limited so a √2
finer grid also takes √2 more steps. Using cell ratios as a time estimate
under-budgets by 75%.

---

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
   watermark → FAIL"*. `judge_red()` checks presence, `review_by` parseability
   and expiry — then **prints** the watermark into an f-string. **Nothing
   compares a fresh measurement against it.** In a repository whose thesis is
   that prose is never load-bearing, the regression half of the ledger's own
   contract is prose.
3. **gap ↔ gate linkage is prose-only.** 15 predicates name a gate in their
   evidence string; only **3** are machine-linked. `navalai/gates.py` cites gap
   ids in 7 places, all comments. There is no field on `Gate`, no mapping table,
   no test — **you cannot systematically say which gap blocks which gate.**
   Cheapest structural upgrade available: a `gate: str | None` on `Check`, plus a
   test that every named gate exists in `GATES`.
4. **Three predicates can be closed by a comment.** Three rows call `has()` on
   Python files instead of `has_code()`. `code()` exists precisely because a gap
   once closed on the word appearing in a comment *on the defect* — and one of
   the three is the row that produced that incident.
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

### 15.3 Bars that exist only in prose

Measured against `navalai/gates.py` on 2026-08-11: each bar below either has
**no gate row at all**, or has one that measures something **weaker than the
bar as written** — so nothing fails if the bar itself is missed. Each needs a
gate, a re-negotiation *in this file*, or a recorded retirement.

- ≥ 95% of generated layouts pass L0-A + tier E; ≤ ~1 min per layout.
- Tier F reproduces the USCG worked examples **exactly**, including the plywood
  **−0.81** negative-contribution case.
- The Etap criterion: fully flooded, freeboard loss < 3% LOA, remains
  manoeuvrable.
- Every material choice machine-checked against palette rules; the fire-exposed
  flotation redundancy rule enforced by the solver.
- End-to-end: a non-expert produces a full vessel passing every tier, and the
  report prints the purchase/review caveats it depends on.
- Verdict parity with a qualified reviewer on **≥ 3 reference designs** — the
  original Gate 6 bar. The parity gate that exists measures *threshold* parity,
  which is a different thing.
- ≤ 1–2% surrogate error near optima, measured across ≥ 5 holdout seeds, plus a
  separate *local* gate on a trust region around a Pareto point (which is what
  the published bar actually refers to).
- ≥ 90% of a held-out mission-brief set — and the **≥ 100-brief frozen corpus
  does not exist**; today's "held-out" set is 10 in-repo briefs the parser was
  demonstrably tuned against.
- p95 < 100 ms on **every** interactive endpoint, not only the one that is gated.

**And one bar declared twice, with different values.** The original plan sets
grid uncertainty at **≤ ~2.5%** ("the published bar"); the ledger sets **GCI
≤ 5%**. Two bars for one quantity, and the live one is 2× looser than the plan.
Nothing reconciles them. **Pick one, record why, delete the other.**

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
that uses the machinery.** Gap ids name rows in `docs/GAP-REGISTER.md`; their
text and their current state come from `python scripts/reconcile_gaps.py`, never
from here.

### P0 — Stop the machinery lying (days)

| # | Item | Done when |
|---|---|---|
| P0-1 | One `RHO_AIR`. Three copies, measured 2026-08-11: `dynamics.py` 1.225, `extrapolate.py` 1.226, `cfd/case.py` 1.2 | one definition, added to the fence's banned list |
| P0-2 | §15.2 item 2: the ledger's regression contract becomes code | a RED gate measured worse than its watermark FAILS, proven by a test that feeds it one |
| P0-3 | §15.2 item 3: `gate: str \| None` on `Check`, with a test that every named gate exists in `GATES` | the gap↔gate map is queryable |
| P0-4 | §15.2 item 4: predicates that call `has()` on Python source become `has_code()` / `func_code()` | a comment can no longer close a gap |
| P0-5 | Two remote refs, `origin/apse` and `origin/worktree-apse`, still appear in `git branch -r` (measured 2026-08-11). One branch is the law | `git fetch --prune` is run, and either they are gone or they are deleted upstream deliberately |

**Two things this table has already had to unlearn, and they are the reason it
is written this way.**

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

### P1 — SELL becomes a product (weeks)

`B4` (payload flat regardless of crew), `B5` (nothing costs length), `E1b`
(Holtrop implemented and anchored but not wired into `evaluate()`), plus §3:
freeze and hash the mission contract; `PriceValue` with a tier and an expiry;
BOM pricing and cost closure; feasibility negotiation over `Evaluation.g`;
render the delivery route `policy/legal.py` already computes and shows nobody.
**New gates M1, Q1, Q2, N1.**

### P2 — BUILD earns its guarantees

Wire `agents.py` onto `pipeline.py` (§4.2) — the spine has zero production
callers and its gate is green on unused code. Populate `EvidenceGraph` from
`evaluate()` + `db.Provenance` (§6). Resolve the badge-coverage question (§4.3).
Close the demonstration gap (§4.4). Also `E5` (public-CAD hull round-trip), `E9`
(`hull_id` collision), `E14`, `E17`, `E18`, `A6c` (ARD lengthscales saturating
at the optimiser bound), `I5` (calibration beyond one coverage assertion).

### P3 — The number we owe

`F16` (no settled GCI triplet), `F17` (unattended meshing measured at N=8, and
the "converges" half never run), `F1` (added resistance in waves: no drift
force, no heading sweep, no acceptance data, no gate row — the one CRITICAL
row). **The next CFD experiment is free sinkage and trim, not a longer run**
(§11.5). Then the triplet, then the robustness sweep with `--solve`.

### P4 — The rules moat

`D9` — verdict parity on ≥ 3 reference designs, the bar the original plan set
and nothing implements — plus `I13` (a recorded non-expert session), the
purchase queue in priority order (`docs/research/COMPLIANCE.md` §9), and
ES-TRIN's remaining scope work.

### P5 — RUN, and the loop closes

`I1` (co-kriging has never seen a real high-fidelity number) and `I14` (the
surrogate spine has no consumer) widened into a real high-fidelity arm:
observation rows in `db.py`, a generic delta engine, a `flywheel` data source
that is not `evaluate()`. **This is the phase that makes the learning loop stop
being closed on itself.** File the RUN gaps before writing the code.

### P6 — WindWing

Blocked behind P1 (environmental state on the mission) and the preconditions in
§10.2 — no 6-DOF model, no roll RAO, no centre of lateral resistance. **The LOAD
gate comes first**, not the power model. W2 stays recorded as blocked.

---

## 17 · Dependencies

### 17.1 The graph

```
P0 stop the machinery lying     ← BLOCKING. Nothing below is trustworthy until done.
     │
     ├──────────────┬────────────────────────────┐
P1 SELL          P2 BUILD guarantees        P3 the number  ← compute-bound, start early
     │               │                            │
     │               └──────────┬─────────────────┘
     │                          │
     │                     P5 RUN + delta engine   ← genuinely blocked: the
     │                          │                    high-fidelity arm needs P3's rows
P4 rules moat  (parallel with P2)
     │
P6 WindWing   ← blocked on P1 (environmental state) and on §10.2's P1/P2/P3/P5
```

- **P0 is blocking** for the same reason it always was: while a check can be
  edited to green, every subsequent claim of progress is unverifiable.
- **P1 and P4 are independent of each other** and can run in parallel across two
  owners.
- **P3 is compute-bound, not effort-bound.** Start it during P2 and let it run.
- **Only P5 is truly blocked by physics.** A surrogate starved of high-fidelity
  data cannot be fixed by effort.

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
makes every other number believable. P3 is measured in **days of wall-clock
compute** on a machine that thermally sleeps. The two genuine research risks are
the arrangement generator (no industry-adopted solver exists) and WindWing W2
(which is blocked on physics that does not exist yet); everything else is
engineering.

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
| BuildPlan 1 | the literature sweep and its verdicts | Phases 0–7 as a schedule; the "49 constraints" (built: 9 live) and "45–90 params" (built: 15) |
| BuildPlan 2 | the sourced ergonomics and flotation constants | V2.0–V2.6 as a schedule; its bars are in §15.3 until gated |
| BuildPlan 3 (mission→order) | the governance argument and the regulatory research | V3.x as a schedule; its §0 summary of RCD Art. 20 for category D, which `policy/legal.py::DISCREPANCIES` records as wrong with a passing test |
| BuildPlan 3 (gap closure) | the eliminated-hypothesis record | R0–R7 as a schedule, largely landed; R5.5's headline framing, superseded by the 2026-08-07 re-measurement |
| Stage plan | its dependency reasoning, inherited by §17 | S0–S7 as a schedule |
| HLD | §1–§8, which are §2 of this file | §9–§11, which were second copies of state the runners own; §11 described a repository crisis in the present tense after it had ended |
| APSE, pressure-oscillation, end-to-end audit, CFD blocker brief | everything, as `docs/research/*` and §4 | nothing |
| PLM §5–§6 | — | the gate registry restatement and the roadmap board; §1–§4 are narrowed and kept |

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

`ALIGNMENT.md` is owed the scorecard reconciliation recorded as P0-8. It is not
edited here because another session held it on 2026-08-11.

`docs/GAP-REGISTER.md` is owed nothing and must be given nothing: it is a dated,
immutable audit record, parsed by `navalai/gaps.py`, and its gradeable tables
must never be restructured. Corrections to it are made as **new** rows or as
re-grade requests recorded elsewhere — §16's note on C9 is the worked example.

## Appendix B · What this document does not verify

- **Nothing in the code-state readings above was executed.** They are static
  reading plus the greps quoted, dated 2026-08-11 at `b5002be`. No gate's colour
  is asserted anywhere in this file.
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
