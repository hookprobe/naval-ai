# BuildPlan 3 — Mission → Order
## Governance first: the platform stops asking "what can I design?" and asks "what am I ALLOWED to design?"

**Chief-architect intent.** BuildPlan 1 delivered a hull you can trust.
BuildPlan 2 delivers a vessel you can live in and cannot lose. BuildPlan 3
delivers a vessel you can **legally place in the world and actually order** —
mission sentence in, an orderable, cuttable, buildable, traceable release out.
The new capability is not another solver. It is a **governance kernel** that
decides the admissible design space *before* physics runs, and a **procurement
and manufacturing spine** that terminates the ladder in a purchase order
instead of a STEP file.

**Method.** Grounded in a research sweep run 2026-08-06 (28 searches, 8
primary documents fetched and claim-extracted). **No adversarial panel was run
this sweep** — the Nemotron consultant endpoint was unreachable, so unlike
BuildPlans 1 and 2 there is no vote count behind these claims. Every claim
below is therefore tagged with the verification that *actually happened*:
**[P]** = extracted from the primary/authoritative text; **[S]** = search-result
summary only, primary text not fetched, treat as a lead. Architect (Gemini)
was consulted on structure; §2.2 records where its recommendation was
**overruled** and why.

---

## 0 · The finding that reorganised this plan

The user's framing was that governance is an *ethics* layer — a company
constitution about sustainability and materials. That is real, but it is the
second-order use. The first-order use is that **the law already draws the box,
and the box is small, sharp, and machine-checkable**:

- **RCD Article 20** [P] — conformity assessment by design category and hull
  length. **Category D** may use **Module A (internal production control =
  self-certification, no notified body)**. **Category C under 12 m** may use
  Module A *only if the harmonised standards are complied with*; if they are
  not, it falls to A1/B+/G/H. **Categories A and B, and anything 12–24 m**,
  require a notified body (B+, G, or H).
- **RCD Article 2(2)(a)(vii)** [P] — watercraft **built for own use are outside
  the Directive entirely**, "provided that they are not subsequently placed on
  the Union market during a period of five years from the putting into service".
  Article 19(4) [P]: sell before year five and post-construction assessment
  (Article 23, Annex V) applies.
- **EU AI Act Annex I Section A item 3 IS Directive 2013/53/EU** [S], and
  **Article 6(1)** [P] makes an AI system high-risk only when **both** (a) it is
  a safety component of — or is — a product covered by Annex I, **and** (b) that
  product "is required to undergo a third-party conformity assessment".

Put those together and one envelope satisfies two regulators at once:

> **The self-certifiable envelope.** Hull length < 12 m, design category C or D,
> harmonised standards applied → the *boat* needs no notified body (RCD Art. 20),
> and because no third-party assessment is required, Art. 6(1)(b) is not
> satisfied, so **the design AI is not high-risk** under the AI Act either.
> Step outside it — 13 m, or category B — and you have simultaneously acquired
> a notified body *and* an AI Act high-risk classification.

That is the governance layer's real job, and it is a **coupling no physics
gate can see**. It also silently corrects the design-DNA sketch: a "maximum
length 24 m" constitution is a constitution that walks the platform into
third-party assessment on its first project. **The number is 12 m.**

Honest limit: whether a *generative design tool* counts as a "safety component"
is a legal judgement we are not qualified to make. The platform therefore treats
this as it treats the rules tier — **an assessment aid that routes work and
cites clauses, never legal advice, never a compliance claim.** The value is that
it makes the question unavoidable at mission time instead of at delivery time.

---

## 1 · What the research established

### 1.1 Governance-as-code has two mature patterns, and we should use neither runtime as-is

- **OPA / Rego** [S] is the CNCF-standard policy engine: policies as code,
  version-controlled, reviewed and rolled back through git, enforced at
  admission points across a pipeline. Broad production use.
- **OWL + SHACL** (the Architect's recommendation) is the semantic-web
  equivalent: an ontology of entities (craft, components, clauses, materials)
  with SHACL *shapes* validating any candidate instance against it.
- **SysML v2** [S] was finally adopted by OMG in **July 2025**, together with
  KerML and a standard **REST API with JSON or RDF representation** — the first
  time requirement→design→analysis traceability has a standard wire format.
- **W3C PROV-O** [S] is the domain-agnostic provenance vocabulary (entity /
  activity / agent) with defined extension points — the natural export schema
  for a design evidence graph.

**Verdict:** these are the right *interchange* formats and the wrong *runtime*.
This platform's most-repeated defect is **a number declared twice** (`limits.py`
exists because the GM floor drifted 0.35 vs 0.45 across four files). Putting the
legal envelope in a Rego file and the GM floor in Python guarantees a third
copy. Governance is therefore **compiled in-process from typed Python policy
objects into the structures that already exist**, and PROV-O / SysML v2 are
**export surfaces** for the evidence graph, not the enforcement path. See §2.2.

### 1.2 The click-to-order bottleneck is the catalog, not the CAD

- **Instant-quote manufacturing is solved for machined parts** [S]: Xometry's
  engine takes STEP/DXF/STL, runs ML geometry analysis, returns price, lead time
  and automated DFM feedback against 4 500+ manufacturers; Protolabs returns
  automated design analysis within hours, unlimited resubmissions. The pattern
  *geometry in → priced, manufacturable order out* is proven and commercial.
- **Distributed CNC kit manufacturing is proven at building scale** [P]
  (WikiHouse manufacturing guide, fetched): designs ship as **DXF/DWG nested on
  2440 × 1220 mm sheets with named, colour-coded layers** (labels, screw marks,
  internal cuts, external profiles, pocket mills); **0.25 mm offsets baked in**
  so an 18 mm slot is cut 18.5 mm; **T-bone corners** to avoid fillet
  interference; incoming sheet thickness policed at **17.1–18.1 mm** with
  sub-17.4 mm sheets demoted to facing panels; **20–40 minutes per sheet**;
  **0.5–1 t of waste per house**; microfactory setup **£50–100k** against
  £15–50m for a traditional factory.
- **Boat kits are an existing industry** [S]: CLC, Fyne Boat Kits, Pygmy,
  Denman, Dudley Dix (incl. a CNC kit for a 47 ft plywood catamaran) already
  sell CNC-cut okoume kits, and several will **cut a customer's own DXF** in
  their own stock. The manufacturing network for a plywood kit boat does not
  need to be built — it needs to be addressed.
- **Nesting has a fresh open-source solver** [P]: *sparrow* (arXiv:2509.13329,
  built on **jagua-rs**, **Apache-2.0**, github.com/JeroenGar/jagua-rs) solves 2D
  irregular strip packing by decomposing into a sequence of feasibility problems
  and "consistently outperforms the state of the art — in some cases by an
  unexpectedly wide margin". Quantitative tables were not extractable from the
  PDF and remain **owed**. Commercial true-shape nesters quote **5–10% waste** [S]
  as the achievable band.
- **And then the catalog stops being free.** There is **no open marine component
  data standard**. ETIM and eCl@ss [S] are rich and attribute-typed but scoped to
  electrical/technical goods; **IMPA** [S] is 6-digit ship-*stores* coding
  (~50 000 codes, CSV licence) for consumables, not engineering components with
  performance curves; UNSPSC is procurement taxonomy, not specification. Nothing
  gives a motor's efficiency-vs-RPM curve, its controller's CAN protocol, or its
  bolt pattern in machine-readable form. Even efficiency data is scarce enough
  that a comparison survey found published propulsive-efficiency figures **only**
  for Torqeedo and Oceanvolt (Torqeedo 10 kW pod ≈ 56%, Oceanvolt 15 kW
  ServoProp ≈ 51%) [S].
- **One future data source is legislated.** The **EU battery passport** [S] is
  mandatory from **18 February 2027** for industrial and EV batteries **> 2 kWh**
  placed on the EU market — QR-accessible, GS1 Digital Link, three-tier access
  model, carrying material composition, carbon footprint, recycled content and
  state-of-health. Every serious electric-boat house bank is > 2 kWh. That makes
  the battery the **first component class with a machine-readable, legally
  guaranteed data sheet** — and the template ESPR will replicate.

**Verdict:** the Architect predicted our biggest mistake would be
under-scoping component data, and the evidence agrees. So BuildPlan 3
**does not promise a 548-line auto-verified BOM.** It promises the part of the
BOM the platform can *derive from its own geometry* — the sheet-goods kit —
plus a curated catalog with a **measured coverage number attached to every
release** (§2.4, "BOM closure").

### 1.3 Component reasoning: the safety rules are real, specific, and mostly purchasable

- **ABYC E-13 (lithium ion)** [S] applies at **≥ 600 Wh** (≥ 50 Ah at 12 V) and
  requires a BMS, SAE/IEC/UL-tested cells, over-current protection, thermal
  runaway mitigation (barriers/isolation), fire suppression appropriate to the
  vessel, and an emergency disconnect. **ABYC E-11** [S] covers AC/DC systems
  generally. Both are membership/paywalled → PURCHASE queue, `basis='approx'`
  meanwhile — the pattern already used by `navalai/rules/`.
- **ISO 12215-5** [S] (scantlings, monohulls 2.5–24 m, explicitly covering
  glued wood/plywood) is already partly implemented and is now the **derived**
  source of bottom-panel thickness (see `limits.py` — this was fixed in the
  2026-08-05 audit). **ISO 12215-7** [S] extends loads to **multihulls** — and a
  catamaran product line cannot be gated without it. → PURCHASE queue, top of it.
- **Design categories** [S]: A = wind > Bft 8, Hs > 4 m; B = ≤ Bft 8, ≤ 4 m;
  C = ≤ Bft 6, ≤ 2 m; D = ≤ Bft 4, ≤ 0.3 m. Already in `limits.CATEGORY_TABLE`.

### 1.4 Energy claims must be gated against measured evidence, not brochures

The reference mission ("cross the Mediterranean entirely on solar") is exactly
the claim most likely to be false, so the anchors matter:

- A well-integrated array on a **12 m catamaran peaks around 6 kW and yields
  ~20–30 kWh on a good day** [S]; Sunreef Eco quotes up to 30 kWh [S].
- Silent Yachts' current flagship: **17 kWp of solar, 350 kWh of storage** [S].
- The honest one: a **Silent 62 crossed the Atlantic (~3 800 nm) burning
  ~5 500 L of fuel**, battery-powered for 72% of the journey — ~40% less fuel
  than a comparable 60 ft motor catamaran [S]. **The flagship solar yacht burned
  fuel to cross an ocean.** Any "unlimited autonomy" output from this platform
  must survive comparison with that number or be labelled as what it is.
- A watermaker producing 3 600 L/day draws **~14 kWh** [S] — over half a 12 m
  cat's entire daily solar yield, for one appliance.
- **Kite assist** [S]: SkySails measured 10–20% fuel saving; Airseas Seawing
  reported ~16% in validation, projecting up to 20%. **Both figures are from
  cargo ships**, where the kite is small relative to displacement and the route
  is a great-circle ocean crossing. Transferring them to a 14 m catamaran is
  **unsupported by anything in this sweep** and must be modelled, not assumed.

### 1.5 Digital twin and fleet learning: standards exist, and one of them refuses the headline feature

- **DNV-RP-A204** [S] is the maritime/energy recommended practice for assuring
  digital twins, and it defines **capability levels: descriptive → diagnostic →
  predictive → autonomous**, plus requirements on data quality, cyber security,
  platform, and the *organisation* operating the twin. This gives us an
  off-the-shelf honesty scale: **declare the level, don't exceed it.**
- **Signal K** [P] is the open marine data layer: JSON model, HTTPS/WSS with
  standard auth, runs on a Raspberry Pi or any PC, bridges NMEA 0183/2000 and
  SeaTalk, plugin store, and explicitly anticipates cloud and inter-vessel
  sharing. It is the ingestion path — no proprietary telemetry stack needed.
- **ISO 19030** [S] prescribes how to measure **changes in hull and propeller
  performance** from in-service data (speed/power KPIs, dry-docking before/after,
  Part 2 default method, Part 3 alternatives). **And it states in scope that the
  methods are *not* intended for comparing performance of ships of different
  types and sizes — explicitly including sister ships, and not for regulatory
  use.**

That last clause deletes the naive version of the fleet-learning story.
"2 000 boats told us hull variant 7 beats CFD by 6%" is a **cross-vessel**
comparison, which the only standard in this space says its methods do not
support. Fleet learning is therefore designed as **same-vessel, before/after,
with an explicit correction model** — and cross-vessel inference is gated
behind validating that correction model, not assumed (§3.8).

### 1.6 LLM agents in engineering: capable orchestrators, unreliable reasoners

**EngiAI** [P] (arXiv:2605.19743) benchmarks LLM-driven engineering workflows
(topology optimization, simulation, manufacturing export, HPC orchestration)
with a hierarchical supervisor routing to seven specialised agents. Results
that bear directly on the "every component gets its own agent" proposal:

- Frontier models reached **96–97% task completion** on the well-structured
  workflow; a 4B open model managed **55%**.
- **Conditional reasoning was the failure mode**: on one domain the best model
  reached only **53%**, and on 36 failed runs **all four models failed
  identically by selecting the opposite conditional branch**.
- Retrieval was **necessary, not optional** — scores collapsed to near zero
  without it, and an empty index degraded performance substantially.
- Multi-step instruction following **decayed over long workflows** (one model
  dropped from 100% to 50% depending on prompt style).

Correlated failure across independent models on the same conditional branch is
the important result: **redundant agents do not vote their way out of it.**
This is decisive support for the platform law — agents orchestrate and explain;
deterministic code decides. It also argues against fourteen autonomous
component agents and for **one reasoning shell over typed component data**
(§2.3).

### 1.7 The market shape, honestly

Configure-price-quote for boats already exists [S] — Infor/Godlan/Missoun/
SWIFTSELL sell CTO configurators feeding ERP, with 3-D visualisation and
automatic production documentation, and SAP variant configuration [S] has done
super-BOM → order-BOM explosion for decades. Naval architecture software
(NAPA, Maxsurf, Orca3D, ShipConstructor, AVEVA) [S] covers geometry and
analysis. **Nobody joins them.** A configurator picks from a catalog a human
engineered; a CAD tool draws what a human decided. The gap — *mission →
governed, physics-validated, novel design → its own orderable BOM* — is the
same shape as the rules-as-code gap BuildPlan 1 identified: unclaimed because
it is genuinely hard, and defensible for the same reason.

---

## 2 · Architecture

### 2.1 The stack (user's layering, adopted, with two corrections)

```
                         Human Intent  (one sentence)
                              │
        ┌─────────────────────▼─────────────────────┐
        │ MISSION INTELLIGENCE                      │  what is being asked,
        │  → feasibility VERDICT + owed unknowns    │  and is it possible
        └─────────────────────┬─────────────────────┘
        ┌─────────────────────▼─────────────────────┐
        │ GOVERNANCE  (policy/*.py, compiled)       │  what am I ALLOWED
        │  legal envelope · design DNA · palettes   │  to design
        │  COMPILES TO ↓ never runs beside ↓        │
        └─────────────────────┬─────────────────────┘
                    ┌─────────┴──────────┐
        parameter-space BOX        constraint ROWS ──┐
        (prunes the search)        (into evaluate.g) │
                    └─────────┬──────────┘           │
        ┌─────────────────────▼─────────────────────┐│
        │ ENGINEERING INTELLIGENCE                  ││ requirement synthesis,
        │  component models + compatibility graph   ││ system sizing, planner
        └─────────────────────┬─────────────────────┘│
        ┌─────────────────────▼─────────────────────┐│
        │ PHYSICS & OPTIMIZATION  (BuildPlan 1 + 2) │◄┘  UNCHANGED.
        │  L0 · L1 · L2 · L3 · R · E · F            │    One constraint vector.
        └─────────────────────┬─────────────────────┘
        ┌─────────────────────▼─────────────────────┐
        │ PROCUREMENT   BOM · closure · quotes      │  can it be bought
        └─────────────────────┬─────────────────────┘
        ┌─────────────────────▼─────────────────────┐
        │ MANUFACTURING  nest · kit · instructions  │  can it be made
        └─────────────────────┬─────────────────────┘
        ┌─────────────────────▼─────────────────────┐
        │ DIGITAL TWIN → FLEET LEARNING             │  what actually happened
        └───────────────────────────────────────────┘
              all of it writing into the
              DESIGN EVIDENCE GRAPH (db.py, content-addressed)
              exported as PROV-O / SysML v2 API
```

**Correction 1 — feasibility is not a percentage.** The sketch's *"Feasibility
94%"* is a number with no calibration behind it, and this platform's first
honesty rule is that every quantity carries `{value, tier, sigma}`. A
percentage that cannot state its tier is exactly the kind of number the
codebase exists to prevent. Mission Intelligence therefore returns a **verdict
object**: the binding constraint, its margin with units, and the explicit list
of **owed unknowns** each with the tier that would resolve it. "Feasible at L1;
binding constraint is solar yield vs hotel load, margin −0.8 kWh/day (σ 0.4);
owed: propeller efficiency (L2), fouling allowance (field)." That is
actionable. "94%" is not.

**Correction 2 — governance is a compiler, not a court.** See §2.2.

### 2.2 Governance compiles; it does not adjudicate (overruling the Architect)

The Architect argued governance should be a **separate engine acting as a
pre-filter**, for efficiency, clarity and independent maintenance. Half of that
is right and half of it would break this codebase.

Right: governance rules *are* categorical, they *do* prune before physics, and
pruning early is cheap. Wrong: making it a *separate engine* means a second
place where a limit is written down — and the single most expensive class of
bug in this project's history is a number that exists twice (`limits.py`'s
docstring is a post-mortem of exactly that: NSGA-II optimising to its private
GM 0.35 while the rules gate held 0.45).

So governance is a **compiler with two outputs from one source**:

1. a **parameter-space box** the sampler and NSGA-II are constructed inside
   (LOA ≤ 12 m becomes a bound, not a rejection), and
2. **rows appended to the existing `evaluate.CONSTRAINT_NAMES` / `Evaluation.g`
   vector**, so anything already consuming that vector is governed for free.

And it inherits the **ratchet law** already proven in `translate.py`, where an
LLM proposing a weaker design category is overruled by `min()` because
`'A' < 'B' < 'C' < 'D'` orders severest first. Generalised:

> **Policy may only ratchet a gate tighter. A policy that would loosen any
> floor in `limits.py` is a policy ERROR, rejected when the constitution is
> compiled — not a runtime override, not a warning, not a note.**

This is the structural test for whether we got it right: **delete the policy
file and no physics result may change.** If deleting the constitution changes a
GM number, we built a second engine and must undo it.

Sustainability policy (allowed propulsion, banned fuels, material palette,
minimum recyclability) rides the same compiler — but it is important to be
honest that these are **preference constraints, not safety constraints**. They
are recorded with `basis='policy'` and can be relaxed by the *owner* of the
constitution; the legal envelope and the physics floors cannot.

### 2.3 Component models, not component agents

The proposal was an agent per component — solar, motor, battery, rudder, kite,
watermaker, toilet. The EngiAI result (§1.6) says autonomous LLM agents fail
*correlatedly* on conditional branches, which is precisely what component
selection is ("if crew > 3 and no blackwater plumbing then …"). Fourteen of
them would produce fourteen confidently wrong branches.

The structure that survives is the one `rules/` already uses — **typed objects
with clause provenance, and one reasoning shell above them**:

```python
Component:                      # a data contract, not an agent
    id, class, supplier, sku
    physics:      typed curves/params, each {value, tier, sigma, source}
    ports:        typed + united  (48 V DC in, 5 kW out, CAN-J1939, M10×4 @ 120 mm)
    rules:        applicable clauses (ABYC E-13 ≥600 Wh, ISO 12215-7 …)
    mass:         ONE MassItem → weights.aggregate  (never a fourth placement table)
    commerce:     price {tier: quoted|listed|estimated}, lead_time, availability
    basis:        datasheet | measured | approx      ← no basis, no catalog entry
```

**Compatibility is a graph check, not a judgement.** Motor ↔ controller ↔
battery ↔ charger compatibility is voltage windows, continuous and peak current,
protocol, and bolt pattern — all executable. The LLM's job is to *explain* why
Motor A won and to ask the user the question only they can answer; the *decision*
is a typed constraint solve. This keeps honesty rule 3 intact: **LLMs have no
code path to geometry, and now no code path to the BOM either.**

Every component mass enters `weights.MassItem` **exactly once**. This is not a
detail: the 2026-08-05 audit found three placement tables disagreeing by 0.7 m
on payload LCG. A BOM is a mass model with prices attached — if it becomes a
fourth table, stability silently decouples from the parts list.

### 2.4 BOM closure — the number that makes "ready to order" honest

"Bill of materials — 548 items — verified — available — ready to order" is a
claim, and this platform does not ship unmeasured claims. Every release
therefore carries **BOM closure**, measured two ways:

- **mass closure** = fraction of the vessel's validated displacement that
  resolves to a catalog part with a source, and
- **cost closure** = fraction of estimated total cost that resolves to a part
  with a price whose tier is `quoted` or `listed` (not `estimated`).

Both are printed on the release. Unresolved items are **listed by name**, never
absorbed into a margin. A design is "orderable" only for the closure it can
demonstrate — and for the plywood kit path (§2.5) mass closure is high by
construction, because the platform *derived* the panels itself.

Prices and lead times are quantities like any other: `quoted` (binding, from a
supplier, with an expiry), `listed` (public price, scraped, dated), `estimated`
(parametric model, carries σ). **An order artifact may never present an
`estimated` price as a quote** — the same rule as never printing an L1 number
with an L3 badge.

### 2.5 The shortest real path to a boat you can order

Ruthlessly scoped, and it is the one path where every link already exists:

```
mission sentence
   └─ governance: category C/D, LH < 12 m  → RCD Art. 20 Module A,
                                              or Art. 2(2)(a)(vii) own-use kit
   └─ hull grammar (developable, plywood-native — ALREADY BUILT)
   └─ L0 + L1 + R + E + F ladder            (ALREADY BUILT)
   └─ unroll.hull_panels → developable panels (ALREADY BUILT, unroll.py)
   └─ NEST onto 2440×1220 sheets, kerf + thickness offsets baked in   ← NEW
   └─ DXF with named layers + labels + T-bones (WikiHouse pattern)    ← NEW
   └─ sheet count × sheet price + epoxy/glass/fasteners schedule      ← NEW
   └─ ORDER: send DXF to an existing CNC kit cutter                   ← NEW
```

The whole structural kit is **derived from geometry the platform already
generates and already validates**. There is no catalog dependency, no supplier
integration, no interface graph, no notified body — and the legal path is the
cleanest one in the Directive. Systems (motor, batteries, solar) attach as a
**separately-closed** second BOM with its own closure number and its own ABYC
clause set.

Two things this path must state plainly to the user, because they are legal
facts and not fine print: an own-use build is **out of RCD scope only while it
stays own-use**, and **selling it inside five years triggers post-construction
assessment** (Art. 19(4), Art. 23, Annex V). The platform surfaces this at
order time, in the release, and in the as-built record.

### 2.6 The Design Evidence Graph

`db.py` is already content-addressed and append-only; BuildPlan 3 gives it a
schema that reaches past physics. Every node is an `{entity, activity, agent}`
triple in the **PROV-O** sense: mission text → spec → policy compile →
constraint vector → hull genome → each ladder result → component selection →
BOM line → nested sheet → order → as-built → field observation. "Why this
motor?" resolves to a chain that terminates in a datasheet with a URL and a
retrieval date, or it is not shown as a reason. **PROV-O** and the **SysML v2
REST API** (JSON/RDF) are the export surfaces; the store stays ours.

---

## 3 · Phases and gates

Effort scale as in BuildPlan 1: ▪ = person-weeks, ▪▪ = 1–2 person-months,
▪▪▪ = a quarter+.

### V3.0 — Governance kernel ▪▪  ← the load-bearing phase
`navalai/policy/`: `LegalEnvelope` (RCD Art. 20/2/19/23 + AI Act Art. 6 routing,
every rule carrying its article reference and `basis`), `DesignDNA` (owner
policy: length/draft ceilings, solar fraction floors, propulsion allow/deny,
material palette, recyclability floor), and the **compiler** emitting a
parameter box + constraint rows.
**Gate V3.0:**
(a) every policy constant carries `source` + `basis`, no bare numbers;
(b) a policy that would loosen **any** `limits.py` floor is **rejected at
compile time** with the offending pair named — proven by a test that tries it;
(c) the reference SKU resolves to a delivery mode with the RCD article cited,
and a 13 m variant flips to "notified body required" **and** flags the AI Act
Art. 6(1)(b) consequence;
(d) **the structural test: with the constitution removed, every physics result
in the regression suite is bit-identical.**

### V3.1 — Mission Intelligence ▪▪
Mission sentence → feasibility **verdict**: binding constraint, margin with
units and σ, owed-unknowns list with the tier that resolves each. Sits above
`translate.py`, below governance, and reuses L0/L1 + the surrogate.
**Gate V3.1:** on a held-out brief set, the named binding constraint matches
the one a full NSGA-II run actually binds on ≥ 80% of briefs; an infeasible
mission is **declared infeasible with its reason**, never silently resized to
something achievable; **no output contains an uncalibrated confidence
percentage** (enforced by test).

### V3.2 — Component models + compatibility graph ▪▪
The `Component` contract of §2.3; a starter catalog covering exactly the
reference SKU (propulsion, controller, battery, charger, solar, MPPT, and the
kit's fasteners/adhesives); typed ports with units; masses wired into
`weights.MassItem`.
**Gate V3.2:** an incompatible pairing is rejected **naming the failing port**
(voltage window / current / protocol / pattern); a catalog entry without a
`source` cannot be created; every component mass appears **exactly once** in
`weights.aggregate` (test counts them); adding the systems package changes the
validated displacement and LCG by the amount the ladder predicts.

### V3.3 — BOM synthesis + closure ▪▪
eBOM from the validated design; mass closure and cost closure measured; price
tier enforcement.
**Gate V3.3:** closure is **measured and printed on every release**, never
asserted; unresolved items are listed by name; a release containing an
`estimated` price presented as a quote **fails to emit**; the kit path
demonstrates its own closure number, whatever that number turns out to be
(a low first number is a finding, not a failure — it does not get softened).

### V3.4 — Manufacturing: nesting and kit release ▪▪
`unroll.hull_panels` → nesting (evaluate *sparrow*/jagua-rs, Apache-2.0, against
an in-house baseline) → DXF with WikiHouse-pattern named layers, part labels,
T-bone corners, and **offsets baked in** (kerf + measured sheet-thickness
tolerance, not nominal). Sheet count, utilisation and waste reported. Assembly
sequence generated from the panel graph.
**Gate V3.4:** the nested DXF re-parses via the existing
`unroll.parse_dxf_polylines`, **every panel is present**, and panels re-fold to
the hull within the BuildPlan-1 Gate 6 tolerance; nesting utilisation is
**measured** against the 5–10% commercial waste band [S] and reported either
way; a kit whose slot offsets were computed from nominal rather than measured
stock thickness is rejected.

### V3.5 — Procurement ▪
Supplier bindings, quote retrieval where an API or a published price list
exists, dated `listed` prices otherwise, parametric `estimated` model with σ as
the floor. Lead times and availability with the same tiering.
**Gate V3.5:** total cost carries σ and the breakdown by price tier; a quote
past its expiry **degrades to `listed`** automatically rather than going stale
silently; the reference SKU's cost is reproduced within its stated σ by a hand
check on ≥ 3 line items.

### V3.6 — The Order ▪▪  ← the product moment
The release package: nested DXF set, both BOMs with closure, assembly sequence,
cut/consumable schedule, the ladder report (physics + rules + E + F badges), a
**technical-documentation stub** structured per RCD Art. 25 / Annex IX, the
declared **delivery mode**, and the caveats it depends on.
**Gate V3.6:** the release **refuses to emit** when governance routes to
"notified body required"; the own-use path prints the five-year rule verbatim
with its article; a designated non-expert goes from one sentence to a release
unassisted; every number in the package traces to an evidence-graph node
(spot-checked on ≥ 20 randomly sampled numbers, **zero** untraceable).

### V3.7 — Digital twin, descriptive ▪▪
Signal K ingestion (Raspberry Pi class hardware, JSON over WSS), as-built record
bound to the design's content hash, observation stream into the evidence graph.
**DNV-RP-A204 capability level declared** and enforced.
**Gate V3.7:** the twin **refuses any query above its declared capability
level** (a descriptive twin does not answer predictive questions); an as-built
that diverges from its design (substituted component, different battery) is
**detected and recorded**, not silently reconciled; ingestion survives gaps,
duplicates and clock skew without corrupting the record.

### V3.8 — Fleet learning ▪▪▪  ← most methodological risk
Same-vessel before/after in the ISO 19030 pattern, with an explicit correction
model for loading, sea state, wind and fouling. Field data enters surrogate
retraining through the **existing** frozen-benchmark regression gate.
**Gate V3.8:**
(a) a fleet-updated surrogate that degrades the frozen benchmark **never
deploys** (honesty rule 4, unchanged);
(b) a **cross-vessel** performance claim is **refused** unless the correction
model has been validated on held-out vessels — because ISO 19030 states its
methods are not intended for comparing different ships, sister ships included;
(c) selection bias is measured and reported (which boats report data, and how
they differ from those that don't) — an unmeasured fleet is not evidence.

---

## 4 · Top risks, honestly

1. **Component data is the bottleneck, and it is a curation cost, not an AI
   cost.** (Predicted by the Architect; confirmed by §1.2 — no marine
   equivalent of ETIM exists.) Mitigation: the kit path needs no catalog;
   closure is measured rather than promised; the **Feb 2027 battery passport**
   is the first legislated machine-readable component class and should be built
   for now, not retrofitted later.
2. **Governance becoming a second constraint engine.** The failure would look
   like success — a tidy policy DSL, and a GM floor quietly living in two
   places again. Mitigation: the delete-the-constitution test in Gate V3.0(d),
   and the compile-time ratchet.
3. **Legal over-reach.** Routing conformity modules is close enough to legal
   advice to be dangerous. Mitigation: the rules-tier framing, unchanged —
   **assessment aid, clause citations, never certification, never advice** —
   plus the AI Act "safety component" question stated as *open* rather than
   answered.
4. **Fleet learning that launders bias into the surrogate.** Boats that report
   data are not a random sample of boats. Mitigation: Gate V3.8(c), the frozen
   benchmark, and same-vessel comparison by default.
5. **Energy-autonomy claims outrunning evidence.** The Silent 62's 5 500 L
   Atlantic crossing is the anchor that keeps "unlimited autonomy" honest;
   kite savings measured on cargo ships are **not** transferable to a 14 m
   catamaran without modelling.
6. **Multihull scantlings are not yet gated.** ISO 12215-7 is unpurchased, and
   the reference mission in the sketch is a catamaran. Until it lands, a
   catamaran SKU ships with its structural verdict marked `basis='approx'` —
   or does not ship. **Top of the purchase queue.**
7. **Scope gravity.** Fourteen component agents, a marketplace, a fleet
   platform and a twin are four products. The kit path (§2.5) is one, and it is
   the one that reaches a real boat.

## 5 · PLM hooks

- **New role: `governance-architect`** — owns `navalai/policy/`, the legal
  envelope, and the delivery-mode routing. **`compliance`** absorbs the AI Act
  and battery-passport questions alongside the ISO parity queue.
  **`supply-architect`** (new) owns the component contract, catalog curation
  and closure metrics. `chief-architect` owns gates, as always.
- **Purchase queue additions (priority order):** ISO 12215-7 (multihull loads —
  blocks any catamaran SKU), ABYC E-13 and E-11, ISO 12217-1 full text,
  DNV-RP-A204, ISO 19030-1/-2.
- **Product-line addition:** *Kit-Line v3* — the self-certifiable envelope
  (LH < 12 m, category C/D) delivered as a CNC kit. It is a **configuration**,
  not a fork: same grammar, same ladder, one policy profile, one delivery mode.
- **Retirement candidate registered:** the hand-authored BOM in the demo
  retires when V3.3 synthesises one with a measured closure ≥ its coverage.

## 6 · What this plan does not claim

- Not certification, and not legal advice. Module routing is an assessment aid.
- Not a verified BOM. A **measured closure fraction** and a named list of what
  is unresolved.
- Not fleet-scale learning on day one. Same-vessel comparison, with
  cross-vessel inference gated behind a validated correction model.
- Not a feasibility percentage. A verdict, a binding constraint, a margin, and
  the unknowns still owed.
- Not an adversarially-verified research sweep. 8 primary documents fetched,
  the rest search-summary leads tagged **[S]**, and no consultant panel — the
  endpoint was down. **Claims tagged [S] are to be confirmed against primary
  text before any of them becomes a gate threshold.**

---

*Research sweep 2026-08-06: 28 searches, 8 primary documents fetched and
claim-extracted, no adversarial panel (consultant endpoint unreachable —
recorded, not hidden). Primary [P] anchors: Directive 2013/53/EU (EUR-Lex
CELEX:32013L0053 — Art. 2(2)(a)(vii), 19(4), 20, 23, 25, Annex V, Annex IX) ·
EU AI Act Art. 6(1)(a)(b), 6(2), 6(3) · WikiHouse manufacturing guide ·
sparrow / jagua-rs (arXiv:2509.13329, Apache-2.0) · EngiAI (arXiv:2605.19743) ·
Signal K overview. Secondary [S] leads: EU AI Act Annex I §A item 3 ·
RCD design-category wind/wave table · ABYC E-11 / E-13 · ISO 12215-5 / -7 ·
ISO 19030-1 scope · DNV-RP-A204 capability levels · OMG SysML v2 (July 2025) ·
W3C PROV-O · ETIM / eCl@ss / IMPA · EU battery passport (18 Feb 2027, >2 kWh) ·
Xometry / Protolabs instant quoting · CLC / Fyne / Dix CNC kit industry ·
Torqeedo & Oceanvolt propulsive efficiency · Silent Yachts / Sunreef solar and
Atlantic-crossing figures · SkySails & Airseas Seawing kite savings ·
CPQ / SAP variant configuration · RAGulating Compliance (arXiv:2508.09893) ·
Multi-Agent LLM + RAG for shipbuilding documents.*
