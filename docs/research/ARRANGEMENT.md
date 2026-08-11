# RESEARCH RECORD — ergonomics and arrangement generation

> **Role: RESEARCH / EVIDENCE.** The sourced human-factors constants behind
> `navalai/refdata/ergonomics.py` and the tier-E checker, plus the prior art for
> generating an interior/exterior arrangement. Standards-derived numbers (ISO
> 15085 deck safety, USCG flotation, ISO 12217-3) live in
> `docs/research/COMPLIANCE.md`; the plan lives in `docs/BUILD-PLAN.md`.
>
> Every constant here is data with `source`, `basis` and — where it applies — a
> `percentile` field. A paywalled number is recorded **ABSENT** via
> `refdata.absent()`, never filled in at a plausible value.

---

## 1 · Ergonomics has canonical decompositions we can encode

- **Panero & Zelnik, *Human Dimension & Interior Space*** (1979) is exactly the
  "decompose space, furniture, heights, widths" reference: hundreds of
  dimensioned plan/section drawings of user-to-space relationships, with
  percentile-organised anthropometric tables (5th–95th) — supporting
  percentile-*parameterised* rules, not single magic numbers. **Caveat
  (verified): its body-size data is 1970s-era and modern populations are
  larger** — so a configurable percentile stretch factor is encoded rather than
  the raw table.
- **Marine practice numbers** (Robert Perry plus marine accommodation guidance,
  verified): berth length 2 060 mm standard / 1 980 mm minimum (6'9"/6'6");
  double berth ≥ 1 525 mm at the head; berth width 560 mm at the head tapering
  to 380 mm at the foot; settee 455 mm high × 455 mm deep (610 mm lounging),
  ≥ 380 mm backrest, 610 mm width per person; headroom 2 060 mm preferred /
  1 905 mm compromise floor; head compartment ≥ 560 mm bowl-to-door, shower
  ≥ 610 mm square; galley hob ~900 mm working height with ≥ 750 mm clearance
  above the hob and 75 mm kick space; hatches ≥ 460 mm clear (610 preferred).
- **The sea changes the rules** (verified, and absent from land references):
  stoves need **40° of gimbal**; sea berths must be narrow with lee
  cloths/boards (wedge-in design), often convertible single-sea/double-anchor;
  cockpit footwells taper (610 → 460 mm) so feet brace the leeward seat when
  heeled; handholds are a first-class layout element. These are encoded as
  *marine modifiers* on top of the anthropometric base.
- **Reality-gap finding** (Practical Sailor): production boats routinely
  dimension interiors by build cost, not ergonomics — which is why an
  ergonomics-*gated* generator is a genuine differentiator rather than a me-too.

---

## 2 · Arrangement generation: proven architecture, no off-the-shelf product

Verified lineage worth reusing:

- **US Navy ISA**: hierarchical **zone-deck decomposition** (allocate spaces to
  zone-decks, then arrange within each), a fuzzy soft-constraint vocabulary
  (area, min dimension, min segment width, aspect ratio, adjacency, separation),
  and a hybrid agent+GA solver; 89 spaces / 1 307 constraints solved in ~20 min
  on 2008 hardware. **The architecture is reusable; the Navy rule content is
  not** — the rules come from ISO/ABYC/ergonomics instead.
- **CP + GA floor-plan generation** (HABX, Automation in Construction 123:103491,
  2021, production-deployed): envelope + room list → valid plans in ~1 minute,
  with hard constraints in CP and quality in GA. **That is the solver pattern.**
- **Ship-arrangement optimisation review** (~40 studies): GA/NSGA-II dominant,
  MILP for exact sub-problems; stability and survivability encoded as numeric
  constraints (righting-area, GM floors) — which is the evidence that a
  flotation tier couples into layout optimisation rather than sitting beside it.
  **Honest maturity note (verified): industry still arranges ships manually and
  no adopted off-the-shelf solver exists** — building one is real engineering,
  and a moat, the same shape as the rules-as-code finding.

**The architectural consequence:** hard constraints (envelope, overlap,
headroom, passage, bulkheads) go to CP; soft objectives (adjacency, circulation,
area utilisation, CG placement, flotation distribution) go to GA/NSGA-II. Tier E
and tier F feed masses and CG back into the **one** weight model — never a
second placement table.

---

## 3 · Risks this material carries

1. **Paywalled exactness.** 2024 ISO numbers, ABYC inch values and ISO 9094 are
   not held; 2003/approx floors ship with a declared basis and purchases upgrade
   them in place.
2. **Anthropometric age.** 1979 data against larger modern bodies: a percentile
   stretch parameter, and a preference for marine-practice numbers wherever they
   exceed the Panero baselines.
3. **The solver is the schedule risk.** No industry-adopted arrangement solver
   exists; the ISA and HABX patterns cap the *research* risk but not the
   engineering one.
4. **Scope discipline.** Tier E and tier F are ASSESSMENT AIDS, exactly like the
   rules tier. No certification claim attaches to either.

*Sources: Panero & Zelnik 1979 · Perry accommodation practice · Practical Sailor
interior-dimensioning survey · U-Mich/Navy ISA · HABX CP+GA (Autom. Constr.
123:103491, 2021) · ship-arrangement optimisation review (~40 studies).*
