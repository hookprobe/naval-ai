# BuildPlan 2 — Full-Vessel Line
## From validated hull to validated vessel: arrangement, ergonomics, unsinkability

**Chief-architect intent.** BuildPlan 1 delivered a hull you can trust.
BuildPlan 2 delivers a *boat you can live in and cannot lose*: interior and
exterior arrangement generated and gated with the same rigor as hydrodynamics,
plus engineered always-floats survivability. Everything lands as PLATFORM
capability (PLM.md law: products configure, never fork) — the ladder grows
two tiers (E ergonomics, F flotation/survivability) and one grammar
(arrangement), and every SKU inherits them.

**Method.** Grounded in a deep-research sweep (50 sources fetched and
claim-extracted; 76 adversarial verification votes: 71 upheld, 5 refuted —
refuted claims corrected or excluded below, notably: ISO 12217-3 assigns
design category **C or D** (not "D ceiling"), and ISO 15085:2024 zone
*equipment assignments* need the purchased text even though the Z1/Z2/Z3
zone system itself is verified).

---

## 1 · What the research established

### 1.1 Ergonomics has canonical decompositions we can encode

- **Panero & Zelnik, *Human Dimension & Interior Space*** (1979) is exactly
  the "decompose space, furniture, heights, widths" book: hundreds of
  dimensioned plan/section drawings of user-to-space relationships, with
  percentile-organized anthropometric tables (5th–95th) — supporting
  percentile-*parameterized* rules, not single magic numbers. Caveat
  (verified): its body-size data is 1970s-era; modern populations are larger
  — we encode a configurable percentile stretch factor.
- **Marine practice numbers** (Robert Perry + marine accommodation guidance,
  verified): berth length 2 060 mm standard / 1 980 mm minimum (6'9"/6'6"),
  double berth ≥ 1 525 mm at the head; berth width 560 mm head → 380 mm
  foot taper; settee 455 mm high × 455 mm deep (610 mm lounging), ≥ 380 mm
  backrest, 610 mm width per person; headroom 2 060 mm preferred / 1 905 mm
  compromise floor; head compartment ≥ 560 mm bowl-to-door, shower ≥ 610 mm
  square; galley hob ~900 mm working height, ≥ 750 mm clearance above hob,
  75 mm kick space; hatches ≥ 460 mm clear (610 preferred).
- **The sea changes the rules** (verified, and absent from land references):
  stoves need **40° of gimbal**; sea berths must be narrow with lee
  cloths/boards (wedge-in design), often convertible single-sea/double-anchor;
  cockpit footwells taper (610→460 mm) so feet brace the leeward seat when
  heeled; handholds are a first-class layout element. Tier E encodes these
  as *marine modifiers* on top of the anthropometric base.
- **Reality-gap finding** (Practical Sailor): production boats routinely
  dimension interiors by build cost, not ergonomics — meaning an
  ergonomics-*gated* generator is a genuine differentiator, not a me-too.

### 1.2 Exterior/deck safety is largely standardized — and partly free

- **ISO 15085:2003** numbers verified from the standard text: side-deck
  widths ≥ 100/120/150 mm for categories D/C/A+B; **low barrier ≥ 450 mm,
  high barrier ≥ 600 mm**; working-deck continuity (avoid steps/obstacles
  > 500 mm); stanchion test 280 N horizontal with ≤ 50 mm deflection;
  working-deck definition excludes surfaces > 25° longitudinal / 30°
  transverse; reboarding means mandatory on every boat.
- **ISO 15085:2024** (2nd edition, verified) supersedes 2003: risk-based
  deck zones **Z1** (access at any time) / **Z2** (access ≤ 4 kn) / **Z3**
  (access nearly stationary), the craft must fit max persons within Z1 +
  interior, unified "barrier to falling overboard" concept, seat minimum
  400 × 750 mm incl. foot space. Exact per-zone equipment lists and 2024
  numeric clauses are paywalled → PURCHASE list; encode zones now with
  2003 numeric floors, basis='2003-standard', upgrade on purchase.
- **ABYC H-41** (verified at claim level): unassisted reboarding on all
  boats; 400 lb (1 780 N) loads for ladders and cockpit gates; handhold
  strength + clearance requirements — exact inch values behind membership →
  PURCHASE list, basis='approx' meanwhile.

### 1.3 Unsinkability is an engineering discipline with a free calculation core

- **USCG 33 CFR 183 subparts F/G/H** (verified in detail, method public):
  - Applies to monohulls **< 20 ft** (excludes sailboats/canoes/inflatables)
    — for our 10 m products it is NOT the governing law, but its
    calculation method is the industry-standard engineering core we adopt.
  - The implementable math: **F = Fb + Fp + Fc** with material submerged
    factors **K = (SG−1)/SG** — GRP laminate SG 1.50 → K +0.33 (needs foam
    to carry itself); **fir plywood SG 0.55 → K −0.81 (inherently
    buoyant)**; aluminium +0.63; steel +0.88. 2 lb/ft³ PU foam nets
    **60.3 lb/ft³ (≈ 966 kg/m³)** after self-weight + 5% moisture allowance.
  - Level-flotation pass criteria (swamped): heel ≤ 10°, reference-area
    freeboard rules; off-center load ≤ 30°.
  - **Placement is regulated in 3-D**, not just volume: propulsion flotation
    within 36 in of the transom, passenger flotation within 6 in of the hull
    sides, outboard and high — i.e. flotation is an *arrangement* problem,
    which is why Tier F belongs in this plan.
  - Durability (§183.114): ≤ 5% buoyancy loss after 30-day immersions in
    fuel/oil/TSP; polystyrene dissolves in gasoline and is highly flammable
    → **banned from our material palette for flotation**.
- **Foam honesty** (vendor + practitioner evidence, both verified): 2 lb PU
  is only 95–98% closed-cell; new absorption ~0.1 lb/ft³ but moored boats
  show waterlogging over years, foam is friable and absorbs spilled
  gasoline. Design responses: derate long-term buoyancy (policy: −15%),
  prefer sealed/inspectable compartments + foam **redundancy** (never foam
  alone as the only defense), specify ≤ 2%/24 h absorption closed-cell foam
  (the verified Etap spec) for the unsinkable SKU.
- **Production proof it works** (verified): Boston Whaler hulls sawn in half
  stay afloat and driveable (foam distributed in the structure — punctures
  can't defeat it); **Etap** double-hull foam: fully flooded ≈ 2 000 L on a
  21-footer, freeboard loss < 3% LOA, still sailable ~1 kn slower; Sadler
  floats when holed but near deck level — three tiers of "unsinkable" rigor,
  and we adopt **Etap's criterion as the SKU acceptance test**: *fully
  flooded, freeboard loss < 3% LOA, vessel remains maneuverable*.
- **ISO 12217-3:2022** (corrected per refutation): governs < 6 m craft,
  covers swamped flotation, assigns category **C or D**; paid text →
  PURCHASE list. For our > 6 m unsinkable SKU, the criterion above +
  USCG-method math + compartmentation is our self-engineered standard,
  declared as such (assessment aid, not certification). **ISO 9094** (fire
  protection) was not captured free → PURCHASE list; until parity review,
  fire rules ship basis='approx'.

### 1.4 Materials: buoyancy is a material property we already half-own

Plywood-epoxy (our developable grammar's native material) is inherently
buoyant (K −0.81) — a wooden boat needs flotation only for ballast, engine,
batteries and outfit. GRP needs foam for its own mass. This couples directly
into the existing weight-budget model: Tier F consumes the same component
masses the stability solver uses. Fire posture for wood: fire-retardant
epoxy/intumescent coatings exist; specifics → PURCHASE/verify list.

### 1.5 Arrangement generation: proven architecture, no off-the-shelf product

Verified lineage we reuse:
- **US Navy ISA**: hierarchical **Zone-deck decomposition** (allocate spaces
  to zone-decks, then arrange within each), fuzzy soft-constraint vocabulary
  (area, min dimension, min segment width, aspect ratio, adjacency,
  separation), hybrid agent+GA solver; 89 spaces / 1 307 constraints solved
  in ~20 min on 2008 hardware. Architecture reusable; Navy rule content not
  — we fill rules from ISO/ABYC/ergonomics instead.
- **CP + GA floor-plan generation** (HABX, Automation in Construction 2021,
  production-deployed): envelope + room list → valid plans in ~1 minute —
  hard constraints in CP, quality in GA. This is our solver pattern.
- **Ship-arrangement optimization review** (~40 studies): GA/NSGA-II
  dominant, MILP for exact sub-problems; stability/survivability encoded as
  numeric constraints (righting-area, GM floors) — proving Tier F couples
  into layout optimization. Honest maturity note (verified): industry
  still arranges ships manually; **no adopted off-the-shelf solver exists —
  building one is real engineering, and a moat** (same shape as the
  rules-as-code finding in BuildPlan 1).

---

## 2 · Architecture additions (platform, not product)

```
ARRANGEMENT GRAMMAR  (hierarchical AST, mirrors hull_ast.py)
  Vessel
   ├─ Envelope        from geometry kernel: interior volume, sole z, deck plan
   ├─ Interior zones  spaces: berth | galley | head | saloon | nav | stowage | machinery
   │    each space = envelope box + function tags + adjacency prefs + masses
   └─ Deck zones      Z1/Z2/Z3 (ISO 15085) + cockpit + side decks + barriers

LADDER grows:
  L0-A  arrangement algebraic gate     ms    fits-in-envelope, no overlap, min dims
  E     ergonomics tier                ms    percentile envelopes + marine modifiers
  F     flotation/survivability tier   ms    USCG-method solver + placement + swamped criteria
  (E and F feed masses/CG back into L1 stability — one weight model, one truth)

SOLVER: CP (hard: envelope, overlap, headroom, passage, bulkheads)
      + GA/NSGA-II (soft: adjacency, circulation, area utilization ~95%,
        CG placement, flotation distribution)  — HABX/ISA pattern
```

Slider surface gains arrangement knobs (berth count, galley size, saloon
priority…) with the same {value, tier, sigma} badges; provenance records
tiers 'E' and 'F'; the reference-data constants carry `source` and
`basis` ('standard-2003' | 'approx' | 'purchased') exactly like rules/.

## 3 · Phases and gates

**V2.0 — Reference-data spine** ▪▪
`navalai/refdata/ergonomics.py` + `flotation.py`: every constant from §1
as data with source/basis/percentile fields; PURCHASE queue (ISO 15085:2024,
ISO 12217-3:2022, ISO 9094, ABYC H-41, Panero & Zelnik, Larsson & Eliasson)
tracked in PLM. **Gate V2.0:** constants importable, every one carries
source+basis, no bare numbers.

**V2.1 — Arrangement grammar + AST** ▪▪
Spaces, deck zones, adjacency vocabulary, masses; flat vector bridge for
solvers; L0-A algebraic feasibility (overlap, envelope, min dims) < 10 ms.
**Gate V2.1:** the Solar-Liveaboard reference layout (hand-authored)
round-trips and passes L0-A; violations report reasons.

**V2.2 — Tier E ergonomics checker** ▪▪
Standing/seated/lying envelope checks, circulation widths, galley/head
minimums, marine modifiers (gimbal, sea-berth, handhold spacing, heel-aware
sole angles), ISO 15085 deck checks (2003 floors + zone structure).
**Gate V2.2:** verdicts flip on the correct dimension (shrink a berth 50 mm
→ exactly the berth rule fails); reference layout passes a cat-C profile;
percentile parameter demonstrably resizes envelopes.

**V2.3 — Arrangement generator (CP + GA)** ▪▪▪  ← most engineering risk
Envelope extracted from the hull geometry kernel; CP feasibility + NSGA-II
over adjacency/circulation/utilization/CG objectives.
**Gate V2.3:** ≥ 95% of generated layouts pass L0-A + Tier E unassisted;
generation ≤ ~1 min/layout (HABX parity benchmark); layouts visibly diverse
(front's berth-count/area spread, not one plan).

**V2.4 — Tier F flotation/survivability solver** ▪▪
USCG-method F = Fb+Fp+Fc generalized to our material DB and hull sizes;
3-D flotation placement as arrangement constraints; swamped-equilibrium
check (flooded waterline vs Etap < 3% LOA criterion); compartmentation model
(collision bulkhead + N-compartment flooding). Foam policy: closed-cell
≤ 2%/24 h spec, −15% aging derate, polystyrene banned, foam+compartment
redundancy for the unsinkable SKU.
**Gate V2.4:** reproduces the USCG handbook worked examples exactly (incl.
the plywood −0.81 negative-contribution case); reference liveaboard's foam
volume computed, placed, and fits the arrangement without evicting Tier-E
spaces; swamped criterion evaluated with honest uncertainty.

**V2.5 — Materials & fire posture** ▪▪  (partly REVIEW-GATED)
Material DB (SG, K, fire class, waterlogging derate); fire scenarios for
the survivability story (flotation must survive the design fire: foam
encapsulation/compartment sealing rules). ISO 9094 parity → REVIEW-GATED
until purchased + reviewed.
**Gate V2.5:** every material choice machine-checked against palette rules;
fire-exposed flotation redundancy rule enforced by the solver.

**V2.6 — Product integration: "Unsinkable Solar Liveaboard" SKU** ▪▪
Mission → hull (BuildPlan 1) → arrangement (V2.3) → tiers E+F → one report:
physics + ergonomics + flotation, all badged; sliders drive both grammars;
PLM SKU entry with its rules profile.
**Gate V2.6:** end-to-end demo from one mission sentence; a designated
non-expert produces a full vessel passing every tier; report prints the
purchase/review caveats it depends on.

## 4 · Top risks, honestly

1. **Paywalled exactness** — 2024 ISO numbers, ABYC inches, ISO 9094: we
   ship 2003/approx floors with declared basis; purchases upgrade in place.
2. **Anthropometric age** — 1979 data + larger modern bodies: percentile
   stretch parameter + preference for marine-practice numbers where they
   exceed Panero baselines.
3. **Foam field-reality** — vendor optimism vs moored-boat waterlogging:
   derate + inspectability + redundancy are design law, and "always floats"
   is always stated as the Etap-style measurable criterion, never marketing.
4. **Solver is real work** — verified: no industry-adopted arrangement
   solver exists. V2.3 carries the schedule risk; ISA/HABX patterns cap the
   research risk.
5. **Scope discipline** — Tier E/F are ASSESSMENT AIDS like rules/; the
   plan adds no certification claims anywhere.

## 5 · PLM hooks

- Roles: **ergonomics-architect** owns V2.1–V2.3; **cfd-engineer**
  unaffected (Gate 2M continues in parallel); **compliance** owns the
  purchase/parity queue (V2.0/V2.5); **chief-architect** owns gates.
- Roadmap board (PLM.md §6) updated in the same push.
- Retirement candidate registered: hand-authored reference layout retires
  when V2.3 generates a superior one that passes all tiers.

*Sources: 50 documents fetched and claim-extracted; 76 adversarial votes
(71 upheld / 5 refuted, corrections applied). Key anchors: ISO 15085:2003
text + ISO/FDIS 15085:2024 preview (iTeh) · ABYC H-41 (2014) · Panero &
Zelnik 1979 · Perry accommodation practice · USCG Flotation Handbook /
33 CFR 183.105–183.230 + §183.114 · Etap 21i flooded trial · Boston Whaler
demonstrations · ISO 12217-3:2022 scope · U-Mich/Navy ISA · HABX CP+GA
(Autom. Constr. 123:103491, 2021) · ship-arrangement optimization review
(~40 studies).*
