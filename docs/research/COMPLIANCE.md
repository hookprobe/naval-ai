# RESEARCH RECORD — regulation, standards and the legal envelope

> **Role: RESEARCH / EVIDENCE.** What the law and the standards actually say,
> with the article or clause quoted, and what was verified against primary text
> versus taken from a search summary. It is the source behind
> `navalai/policy/legal.py`, `navalai/rules/` and `navalai/refdata/`.
>
> **This is an assessment aid, never legal advice and never a compliance
> claim.** That framing is the rules tier's, and it is not softened here.
>
> Verification tags, carried from the sweeps that produced this material:
> **[P]** = extracted from the primary/authoritative text; **[S]** = search
> result only, primary text not fetched — a lead, not a threshold. **A claim
> tagged [S] must be confirmed against primary text before it becomes a gate
> threshold.**
>
> No status here. Which of these are implemented, and how green, is
> `python -m navalai.gates` and `docs/GAP-REGISTER.md`.

---

## 1 · The self-certifiable envelope — where two regulators agree

This is the finding that reorganised the governance work: **the law already
draws the box, and the box is small, sharp, and machine-checkable.**

- **RCD Article 20** [P] — conformity assessment by design category and hull
  length. **Category D** may use **Module A** (internal production control =
  self-certification, no notified body). **Category C under 12 m** may use
  Module A *only if the harmonised standards are complied with*; if they are
  not, it falls to A1/B+/G/H. **Categories A and B, and anything 12–24 m**,
  require a notified body (B+, G, or H).
- **RCD Article 2(2)(a)(vii)** [P] — watercraft **built for own use are outside
  the Directive entirely**, "provided that they are not subsequently placed on
  the Union market during a period of five years from the putting into
  service". Article 19(4) [P]: sell before year five and post-construction
  assessment (Article 23, Annex V) applies.
- **EU AI Act Annex I Section A item 3 IS Directive 2013/53/EU** [S], and
  **Article 6(1)** [P] makes an AI system high-risk only when **both** (a) it is
  a safety component of — or is — a product covered by Annex I, **and** (b) that
  product "is required to undergo a third-party conformity assessment".

Put together:

> **The self-certifiable envelope.** Hull length < 12 m, design category C or D,
> harmonised standards applied → the *boat* needs no notified body (RCD Art. 20),
> and because no third-party assessment is required, Art. 6(1)(b) is not
> satisfied, so **the design AI is not high-risk** under the AI Act either.
> Step outside it — 13 m, or category B — and you have simultaneously acquired
> a notified body *and* an AI Act high-risk classification.

That is a **coupling no physics gate can see**, and it is why the governance
layer compiles a length ceiling of **12 m**, not the 24 m an early design-DNA
sketch proposed. A 24 m constitution walks the platform into third-party
assessment on its first project.

**Honest limit, and it is deliberately left open:** whether a *generative design
tool* counts as a "safety component" is a legal judgement this project is not
qualified to make. `AiActConsequence.high_risk` is therefore always `None` for
limb (a) — the abstention is a feature and must survive to any customer surface.

**A recorded disagreement, kept rather than silently fixed:** the summary of
Art. 20 in the original BuildPlan 3 §0 is wrong for category D.
`navalai/policy/legal.py::DISCREPANCIES` records it with a passing test.

---

## 2 · The MASS Code does not apply to this product

Written down because the opposite was assumed. The IMO MASS Code was adopted by
resolution MSC.595(111) in May 2026 and took effect 1 July 2026 as a
**non-mandatory** instrument, applying to **cargo ships under SOLAS Chapter I —
generally over 500 GT on international voyages** — with a mandatory version
expected to be adopted by 2030 for force in 2032.

A 14 m recreational catamaran is governed by **Directive 2013/53/EU** (2.5–24 m
recreational craft) and by the ISO 12215/12217 series.

Claiming MASS-Code alignment for a craft outside its scope is prose standing in
for a verdict — the defect class that produced `gate2m.py` printing KCS's EFD
figure under a header for a Wigley hull. **Use the MASS Code as a voluntary
architecture template** — its goal-based structure (operational modes,
operating limitations, risk assessment, connectivity, cybersecurity, fallback on
limit exceedance) maps almost exactly onto the governance engine — and say
"voluntarily aligned with", never "compliant with".

---

## 3 · Scope is part of the standard

`navalai/rules/iso12217.py` implements **ISO 12217-1 — *motor* craft ≥ 6 m**,
and its `R-SCP` guard *refuses* rather than defaulting to pass, after a measured
incident where the −1 category floors were applied to a 4.5 m hull that −3
governs.

| standard | scope | held? |
|---|---|---|
| ISO 12217-1 | motor craft ≥ 6 m | implemented |
| ISO 12217-2 | **sailing** craft 6–24 m, incl. wind-heeling criteria | **not held** |
| ISO 12217-3 [S] | craft < 6 m, swamped flotation, assigns category **C or D** (corrected from a "D ceiling" reading) | **not held** |
| ISO 12215-5 [S] | scantlings, monohulls 2.5–24 m, explicitly covering glued wood/plywood | partly implemented; the derived source of bottom-panel thickness |
| ISO 12215-7 [S] | extends loads to **multihulls** | **not held — blocks any catamaran SKU** |
| ISO 9094 | fire protection | **not held**; fire rules ship `basis='approx'` |

**Design categories** [S]: A = wind > Bft 8, Hs > 4 m; B = ≤ Bft 8, ≤ 4 m;
C = ≤ Bft 6, ≤ 2 m; D = ≤ Bft 4, ≤ 0.3 m. Already in `limits.CATEGORY_TABLE`.

**The consequence for any wind-traction subsystem** (see
`docs/research/WINDWING.md`): fitting a traction kite raises a real question
about whether −1 or −2 governs, and the repository holds neither −2 nor −3. A
kite-rigged craft must therefore **extend `R-SCP`, not bypass it** — the rules
tier must refuse to produce −1 findings for it, exactly as it refuses for a
4.5 m hull. Acquiring −2 is a **purchase**.

---

## 4 · Deck safety and reboarding — largely standardised, partly free

- **ISO 15085:2003**, numbers verified from the standard text: side-deck widths
  ≥ 100/120/150 mm for categories D/C/A+B; **low barrier ≥ 450 mm, high barrier
  ≥ 600 mm**; working-deck continuity (avoid steps/obstacles > 500 mm);
  stanchion test 280 N horizontal with ≤ 50 mm deflection; working-deck
  definition excludes surfaces > 25° longitudinal / 30° transverse; reboarding
  means mandatory on every boat.
- **ISO 15085:2024** (2nd edition, verified) supersedes 2003: risk-based deck
  zones **Z1** (access at any time) / **Z2** (access ≤ 4 kn) / **Z3** (access
  nearly stationary); the craft must fit max persons within Z1 + interior;
  unified "barrier to falling overboard" concept; seat minimum 400 × 750 mm
  including foot space. Exact per-zone equipment lists and the 2024 numeric
  clauses are **paywalled** → purchase queue. Encode the zones now with the 2003
  numeric floors and `basis='2003-standard'`; upgrade in place on purchase.
- **ABYC H-41** (verified at claim level): unassisted reboarding on all boats;
  400 lb (1 780 N) loads for ladders and cockpit gates; handhold strength and
  clearance requirements — exact inch values behind membership → purchase queue,
  `basis='approx'` meanwhile.

---

## 5 · Flotation and unsinkability — a free calculation core with a regulated 3-D placement

**USCG 33 CFR 183 subparts F/G/H** (verified in detail; the method is public):

- Applies to monohulls **< 20 ft** (excluding sailboats/canoes/inflatables) — so
  for a 10 m product it is NOT the governing law, but its calculation method is
  the industry-standard engineering core, and it is adopted as such.
- The implementable math: **F = Fb + Fp + Fc** with material submerged factors
  **K = (SG−1)/SG** — GRP laminate SG 1.50 → K **+0.33** (needs foam to carry
  itself); **fir plywood SG 0.55 → K −0.81 (inherently buoyant)**; aluminium
  +0.63; steel +0.88. 2 lb/ft³ PU foam nets **60.3 lb/ft³ (≈ 966 kg/m³)** after
  self-weight and a 5% moisture allowance.
- Level-flotation pass criteria (swamped): heel ≤ 10°, reference-area freeboard
  rules; off-centre load ≤ 30°.
- **Placement is regulated in 3-D**, not just by volume: propulsion flotation
  within 36 in of the transom, passenger flotation within 6 in of the hull
  sides, outboard and high. Flotation is therefore an *arrangement* problem.
- Durability (§183.114): ≤ 5% buoyancy loss after 30-day immersions in
  fuel/oil/TSP. **Polystyrene dissolves in gasoline and is highly flammable →
  banned from the flotation material palette.**

**Foam honesty** (vendor and practitioner evidence, both verified): 2 lb PU is
only 95–98% closed-cell; new absorption ~0.1 lb/ft³ but moored boats show
waterlogging over years, and foam is friable and absorbs spilled gasoline.
Design responses: derate long-term buoyancy (policy: −15%), prefer
sealed/inspectable compartments plus foam **redundancy** (never foam alone as
the only defence), and specify ≤ 2%/24 h absorption closed-cell foam — the
verified Etap spec — for an unsinkable SKU.

**Production proof it works** (verified): Boston Whaler hulls sawn in half stay
afloat and driveable (foam distributed in the structure, so punctures cannot
defeat it); **Etap** double-hull foam gives fully-flooded ≈ 2 000 L on a
21-footer with freeboard loss < 3% LOA and still sailable ~1 kn slower; Sadler
floats when holed but near deck level. Three tiers of "unsinkable" rigor —
**Etap's criterion is adopted as the SKU acceptance test**: *fully flooded,
freeboard loss < 3% LOA, vessel remains manoeuvrable.*

Materials note that couples straight into the weight model: plywood-epoxy — the
developable grammar's native material — is inherently buoyant (K −0.81), so a
wooden boat needs flotation only for ballast, engine, batteries and outfit. GRP
needs foam for its own mass.

---

## 6 · Electrical and battery rules

- **ABYC E-13 (lithium ion)** [S] applies at **≥ 600 Wh** (≥ 50 Ah at 12 V) and
  requires a BMS, SAE/IEC/UL-tested cells, over-current protection, thermal
  runaway mitigation (barriers/isolation), fire suppression appropriate to the
  vessel, and an emergency disconnect. **ABYC E-11** [S] covers AC/DC systems
  generally. Both are membership/paywalled → purchase queue, `basis='approx'`
  meanwhile.
- **The EU battery passport** [S] is mandatory from **18 February 2027** for
  industrial and EV batteries **> 2 kWh** placed on the EU market —
  QR-accessible, GS1 Digital Link, three-tier access model, carrying material
  composition, carbon footprint, recycled content and state-of-health. Every
  serious electric-boat house bank is > 2 kWh. That makes the battery the
  **first component class with a machine-readable, legally guaranteed data
  sheet** — and the template ESPR will replicate. Build for it now rather than
  retrofitting.

---

## 7 · Digital twin and in-service performance — and the clause that deletes the headline feature

- **DNV-RP-A204** [S] is the maritime/energy recommended practice for assuring
  digital twins. It defines **capability levels: descriptive → diagnostic →
  predictive → autonomous**, plus requirements on data quality, cyber security,
  platform, and the *organisation* operating the twin. An off-the-shelf honesty
  scale: **declare the level, do not exceed it.**
- **Signal K** [P] is the open marine data layer: JSON model, HTTPS/WSS with
  standard auth, runs on a Raspberry Pi or any PC, bridges NMEA 0183/2000 and
  SeaTalk, plugin store, explicitly anticipates cloud and inter-vessel sharing.
  It is the ingestion path — no proprietary telemetry stack needed.
- **ISO 19030** [S] prescribes how to measure **changes in hull and propeller
  performance** from in-service data (speed/power KPIs, dry-docking
  before/after, Part 2 default method, Part 3 alternatives). **And it states in
  scope that the methods are *not* intended for comparing performance of ships
  of different types and sizes — explicitly including sister ships, and not for
  regulatory use.**

That last clause deletes the naive fleet-learning story. "2 000 boats told us
hull variant 7 beats CFD by 6%" is a **cross-vessel** comparison, which the only
standard in this space says its methods do not support. Fleet learning is
therefore **same-vessel, before/after, with an explicit correction model**, and
cross-vessel inference is gated behind validating that correction model.

---

## 8 · Governance-as-code: the right interchange formats, the wrong runtime

- **OPA / Rego** [S] is the CNCF-standard policy engine: policies as code,
  version-controlled, reviewed and rolled back through git, enforced at
  admission points. Broad production use.
- **OWL + SHACL** is the semantic-web equivalent: an ontology of entities
  (craft, components, clauses, materials) with SHACL *shapes* validating a
  candidate instance against it.
- **SysML v2** [S] was adopted by OMG in **July 2025**, with KerML and a
  standard **REST API with JSON or RDF representation** — the first time
  requirement→design→analysis traceability has a standard wire format.
- **W3C PROV-O** [S] is the domain-agnostic provenance vocabulary
  (entity / activity / agent) with defined extension points.

**Verdict:** these are the right *interchange* formats and the wrong *runtime*.
This platform's most-repeated defect is **a number declared twice** — putting
the legal envelope in a Rego file and the GM floor in Python guarantees a third
copy. Governance is therefore compiled **in-process from typed Python policy
objects** into the structures that already exist, and PROV-O / SysML v2 are
**export surfaces** for the evidence graph, never the enforcement path.

---

## 9 · The purchase queue, in priority order

Itemised in code as `navalai.refdata.PURCHASE_QUEUE`, with `refdata.absent()`
naming exactly which quantity each purchase unblocks. Nothing carries
`basis='purchased'` yet, and a test asserts that.

1. **ISO 12215-7** — multihull loads; blocks any catamaran SKU.
2. **ABYC E-13 / E-11** — lithium and general DC/AC systems.
3. **ISO 12217-1 full text**, and **ISO 12217-2** if any wind-traction SKU is
   pursued; **ISO 12217-3** for sub-6 m.
4. **ISO 15085:2024** — per-zone equipment lists and 2024 numeric clauses.
5. **ISO 9094** — fire protection.
6. **ABYC H-41** — reboarding, ladder and handhold exact values.
7. **DNV-RP-A204**, **ISO 19030-1/-2** — twin assurance and in-service KPIs.
8. **ES-TRIN** — the Danube SKU is the one product line that requires it.
9. Reference books: Panero & Zelnik; Larsson & Eliasson.

**The pattern, which is not negotiable:** a paywalled number is recorded
**ABSENT** via `refdata.absent()`, never filled in at a plausible value, and the
constant that stands in for it carries its `basis` (`standard` | `approx` |
`purchased`). An unmeasurable value scored as a passing one is this project's
single most expensive defect class.
