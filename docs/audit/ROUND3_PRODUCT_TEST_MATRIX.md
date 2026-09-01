# ROUND 3 — PRODUCT TEST MATRIX

**What this is.** Seven briefs a customer could type, driven end to end through
the SAME functions the application calls, with the SURVIVAL FUNNEL printed for
each. Reproduce with:

    python scripts/product_test.py --n 25
    python scripts/product_test.py --mission P2 --json out.json

**Why a funnel.** The suite answers "is this module right?" and the gate ladder
answers "is this bar met?". Neither answers the question a product has to
answer: *given a mission, what comes out, and where do the candidates that do
NOT come out die?* A stage where most candidates die is the next
product-development problem, and it is the only output of this document that
matters.

**What it measures.** The FEED (`sample_valid` + the exploring stream), which
is the population `ui/server.get_model` fits the served generator on. The
optimizer (`pareto_front`) is a separate and much stronger route — it adds
parent seeding, the directed shape repair and 15 generations of selection —
and is reported separately in §4.

---

## 1 · The missions

| id | brief | what it exercises |
|---|---|---|
| P1 | 10 m recreational boat with an inboard, 7 knots, 3 tonne, category C, inland waters | the simple case |
| P2 | 16 m × 4.5 m liveaboard houseboat, 5 knots, 6 tonne, category C, 4 berths, coastal and inland | the flagship product: beam-carrying, barge family |
| P3 | 14 m catamaran, 8 knots, 7 tonne, category C, 4 berths | topology routing, demihull bands, multihull stability |
| P4 | 13 m river cruiser with a protected prop, 6 knots, 5 tonne, category C | mission → tunnel geometry → propulsion |
| P5 | 9 m hard chine plywood launch, 7 knots, 2.5 tonne, category C | sheet construction |
| P6 | 15 m wave piercing cruiser, 9 knots, 6 tonne, category C | family routing to the critic |
| P7 | 30 m submarine, 40 knots, 500 tonne, category A | **must be REFUSED with reasons** |

---

## 2 · Funnel, before and after the round-3 fixes (25 candidates each)

| id | valid designs BEFORE | AFTER | meshes | CFD-adm | buildable |
|---|---|---|---|---|---|
| P1 | 0 | **3** | 3 | 3 | 0 |
| P2 | 0 | **1** | 1 | 1 | 0 |
| P3 | 0 → 3 (topology fix) | **4** | 4 | 4 | 0 |
| P4 | 0 | 0 | 0 | 0 | 0 |
| P5 | 0 | **1** | 1 | 1 | 0 |
| P6 | 0 | **1** | 1 | 1 | 0 |
| P7 | hung forever | **REFUSED, 5000 draws, tally** | — | — | — |

Every design that reaches "all rows ok" also meshes closed and is
CFD-admissible — so nothing downstream of the ladder is losing candidates.

**`buildable` is 0 everywhere and that is CORRECT, not a defect.** These are
round-bilge hulls and `buildability.shell_complexity` refuses them by name:
*"a radiused bilge is doubly curved and not developable from flat sheet, which
is a fact about the material."* Developability is a POLICY row (the
`kit-line-v3` constitution), applied when the kit line is the target; an
ungoverned run is free to draw a moulded hull. P5 asks for plywood in prose and
the parser has no `construction` field to carry it — recorded in §5.

---

## 3 · Where the candidates die (after the fixes)

| id | dominant causes, of 25 |
|---|---|
| P1 | `rules` 12, `shape` 8, `bend_radius` 4, `lcb` 1 |
| P2 | `shape` 15, `bend_radius` 4, `rules` 4, `proportions` 1 |
| P3 | `shape` 18, `motor_power` 3, not-sheet-developable 3 |
| P4 | `rules` 9, `shape` 8, `prop_space` 7 |
| P5 | `shape` 11, `rules` 9, `bend_radius` 5 |
| P6 | `shape` 12, `rules` 7, `motor_power` 5 |

**`shape` dominates every mission.** That is Gate MORPH's own recorded
property from the other side — *"89–92% of L0-valid generated hulls fail; 0 of
58 real ones do"* — and it is Gate 4F's territory: the RAW generator draws
uniformly over sixteen correlated genes, and a boat is not a uniform draw.

The round-3 Cp fix moved this materially (0 → 1–4 valid per 25) by removing a
box that made plausibility unreachable, but it did not change the generator's
distribution. That remains the open product problem and it is stated in §5.

**P7's refusal**, verbatim and correct:

> the design feed found 0 of 25 valid hulls in 5000 draws and gave up: this
> mission has no reachable design space in the grammar's own box. What refused
> the draws: L0 freeboard.abs ×1833, L0 freeboard.rel ×1349, L0 L/B ×784,
> L0 section.solve ×315, L0 B/T ×312

---

## 4 · The optimizer route, for contrast

`pareto_front(pop=48, gens=15)` on the 12 m brief returns **48 designs in
14.4 s**. The optimizer is the production design route (`POST /pareto`) and it
does the work the feed cannot: parent seeding, the directed shape repair inside
the mission's own box, and constraint-dominated selection.

`/generate` is the OTHER route and it fits its generator on the FEED — which
is why, measured before the Cp fix, it served **12 hulls of which 0 were
shape-plausible and 0 were fully valid**. Improving the feed is therefore not
a laboratory concern; it is what that endpoint serves.

---

## 5 · What this matrix says is still owed

1. **The raw generator's distribution** (Gate 4F). `shape` is the dominant
   killer on every mission. `sample_valid(repair_shape=True)` exists and is OFF
   by default: measured, the directed climb takes 1/12 → 11/12 plausible in the
   grammar box but only ~1/12 inside a dimensioned mission's box, because what
   it needs to move is Cp — now freed, so this is worth re-measuring.
2. **P4, the tunnel mission**, is the only brief still at zero, and its causes
   are spread (`rules` 9, `shape` 8, `prop_space` 7) rather than one blocker. A
   single protected prop on a 13 m hull is a genuine design tension: the drawn
   tunnel's crown is calibrated against FLOTATION, and a deeper notch buys disc
   room at the cost of flotation solutions.
3. **`construction` is not a mission field.** P5 says "plywood" and nothing
   carries it, so sheet-buildability is never demanded of the design.
4. **P3 buildable = 0** for the same reason as everyone else, but a catamaran
   demihull is the shape most likely to WANT sheet construction.
