# ML hull generation — Phase A investigation

**Written 2026-08-24.** Code referenced: `navalai/morphology.py`,
`morphology_families.py`, `morphology_search.py`, `scripts/build_shipd_corpus.py`.
Nothing in this document is a plan for code that does not exist yet without
saying so.

---

## 1. What representation does Naval-AI use?

A **21-gene parameter vector** → a sectional-area curve → a section solved
per station → 41-station offsets → a triangle mesh.

    genome (21) → sac_ordinate(x) → _stations(x) → offsets → closed_mesh → STL

It is **not** NURBS or BREP. `hull_to_stl` triangulates directly from the
station grid; CadQuery is used elsewhere in the tree but not by this generator.

## 2. Which genes actually control shape?

| group | genes |
|---|---|
| box | `LWL, BWL, T, D` |
| volume distribution | `Cp, lcb, x_mb, r_transom` |
| deadrise law | `beta_mid, beta_bow, beta_len, beta_transom, beta_run` |
| flare law | `flare, flare_bow, flare_len` |
| section / profile | `roundness, rocker, forefoot, stem_depth, sheer_rise` |

## 3. Which quantities are DERIVED, not controlled?

**Beam is derived.** This is the single most important fact about the
representation. Half-breadth is *solved* from the sectional area:

    A = K·yc·(c1·d − c2·m·yc) + d²·f      →  solve for yc

so `Cb`, `Cm`, `LCF`, waterplane area and inertia, `GM` and trim are all
consequences. A caller who "sets the beam" is setting `BWL`, which fixes the
half-breadth at ONE station.

## 4. Why do generated hulls become spearheads and boxes?

Because of §3. **Deck width and underwater shape are the same variable.**

- Ask for a wide deck → `Cp` must approach 0.92 with full ends → the plan
  becomes a rectangle and the bottom must stay flat. MEASURED: **24 of 24**
  forefoot/rocker combinations refused; the only buildable shape was a slab.
- Ask for a fine bow → `Cp` drops → beam coverage collapses to **22%** of the
  waterline. That is the spearhead.

There is no setting that yields both. One curve is doing two jobs; real
draughtsmen draw the deck plan and the sections as separate curves.

Two further causes, both measured:

- **The laws were single-scalar.** Deadrise warped only toward the bow, so
  transom deadrise was ALWAYS exactly `beta_mid` (measured 25.0 deg at the
  transom and 25.2 at midships on the same hull — no run at all). Flare was one
  scalar for every station, which `formlib` already recorded as the blocker
  making `axe_bow` and `wave_piercing_monohull` Expressible.NO. Both are fixed
  (§ commits of 2026-08-24); E5 shape error fell **8.92% → 7.19%**.
- **Nothing measured shape.** `Hull.alpha_e_deg` existed and was read by no
  constraint row, rule or badge. A 36.1 deg bluff bow passed everything.

## 5. What distinguishes real hulls from bad generated ones?

Measured over 58 published hulls and 30,000 ShipD hulls:

| descriptor | REAL median | GENERATED median |
|---|---|---|
| beam carried at ≥90% | 0.390 | **0.171** |
| waterline convexity | 1.000 | **0.512** |
| beam at transom / max | 0.687 | **0.413** |
| plan waist | 0.000 | — |

> **89–92% of L0-valid generated hulls are morphologically implausible.
> 0 of 58 published hulls are.**

## 6. Can ShipGen/ShipD integrate?

Partly, and it already has — as a **teacher, not a dependency**.
`scripts/build_shipd_corpus.py` reads it once and vendors OUR descriptor bands
to `data/shipd_morphology_bands.json`; `navalai/` never imports it. Reasons:
the upstream declares **no licence**, it needs a local numpy-2.x patch to run
at all (111 of 500 hulls crashed — exactly the 21% with a bulbous bow), and a
band that moves when someone re-clones a research repo is not a band.

Its 45-variable parameterisation contains what ours lacked — separate transom
deadrise, explicit bow shaping, bulbs — which is independent confirmation of
§4. It is a **different** parameterisation, so it cannot be adopted wholesale.

## 7. What should ML learn, and what must stay deterministic?

**Deterministic, because it is cheap and exact:** watertightness, hydrostatics,
stability, the L0 algebraic gate, the anti-pattern detectors, and the design
rules. **Learned, when there is data:** the plausibility manifold and the
performance surrogate.

**There is no neural network in this tree, deliberately.** The corpus is 58
published hulls in effectively one family plus 30,000 ShipD hulls at one LOA. A
latent model fitted to that learns Delft yachts badly. Ship-D reports the same
from the other end: 30,000 parametric hulls still contain many shapes no
architect would recognise, and this tree measures that at **64.2% plausible**.
More random geometry is not the answer.

---

## 8. The bow strategy — what the research says, and where the gap is

Four sources, and they do not agree, which is the useful part.

| source | mechanism | measured |
|---|---|---|
| **Damen Axe Bow** (TU Delft/MARIN/RNLN/USCG) | **vertical** stem, **greatest draught at the front** — delays bow emergence, so it cannot slam back | 20% fuel cut |
| **Baltic Workboats** | the **top surface** of the bow makes **downforce** that cancels bow buoyancy | 40% less vertical acceleration, 30% fuel |
| **Seo et al. 2016** (INA&OE 8) | slender piercing bow, round bilge, **small stern deadrise**, **spray rails** inducing bottom lift | trim 4.65° → 3.68°; pitch, heave and FP acceleration all down |
| **Wei/Yi/Li 2018** (SJTU) | above-waterline bow form | **insensitive in short waves; SIGNIFICANT for SMALL craft in calm water** |
| **Vakilabadi 2014** | wave-piercing **trimaran**, centre hull L/B **12.96** | heave RAO resonance at λ/L ≈ 1.0 |

**The universal tension, stated by the sources themselves:** every
wave-piercing mechanism costs transverse stability. Seo names it — *"the hull
has large Lpp/B and low transverse stability"*. Vakilabadi's answer is
outriggers. Nobody's answer is free.

### The Naval-AI thesis (to be tested, not assumed)

For **0–5 m waves on a small craft** the binding condition is the heave
resonance at **λ/L ≈ 1.0** — for an 8–16 m boat that is exactly the middle of
the stated wave range, not an edge case. Two of the sources point the same way
once that is recognised:

1. SJTU: in **short** waves the above-waterline bow barely matters, but for
   **small** craft it matters a lot in calm water. So the emerged bow should be
   tuned for resistance and for what happens when it DOES submerge — not for
   reserve buoyancy.
2. Seo: a **spray rail / lifting chine** recovers trim and cuts vertical
   acceleration.

So: **decouple the three bow functions that every existing design couples, and
recover stability with the chine rather than with a second hull.**

| function | mechanism | gene today |
|---|---|---|
| wave penetration | deep immersed forefoot | **`stem_depth`** ✅ |
| behaviour once submerged | emerged-bow flare / tumblehome | **`flare_bow`, `flare_len`** ✅ |
| stability + trim recovery | spray rail / lifting chine | **MISSING** ❌ |

The first two landed on 2026-08-24 and are measured: an axe bow now builds with
the keel **368 mm deeper at the stem than at midships**, flare running
12.0 deg amidships to −0.5 deg (tumblehome) at the stem, entrance 7.9 deg —
inside the published `axe_bow` band of 4–9.

**The third is the innovation and it is not yet expressible.** If a spray rail
can restore the roll damping and trim control that slenderness costs, a slender
MONOHULL gets wave-piercing efficiency without trimaran complexity — which is
precisely the trade every source above resolved by adding hulls.

### What would prove or refute it

Not a render, and not a plausibility score. A controlled comparison at fixed
displacement, L/B and speed across: conventional bow; slender piercing bow;
axe bow; the same axe bow **with** a rail; and a catamaran of equal
displacement — measured on calm-water resistance, trim, and pitch/heave/vertical
acceleration in a λ/L sweep spanning 0.5–1.5. The thesis is refuted if the
rail does not recover the stability, or if the catamaran wins anyway.

---

## 9. Honest status

| piece | state |
|---|---|
| descriptors (33, scale-free 0.37×–23×) | **built, tested** |
| deterministic critic (0 false positives / 58) | **built, tested** |
| learned manifold (30k ShipD, vendored) | **built, tested** |
| design rules (family-dependent, earned relaxation) | **built, tested** |
| directed search (15% → 95% plausible) | **built, tested** |
| encoder / latent space | **not built** |
| performance surrogate | **not built** |
| active-learning loop to OpenFOAM | **not built** |
| multi-hull geometry (cat/tri competition) | **not possible** — the genome carries ONE moulded surface |
| spray rail / lifting chine | **not possible** — no gene |

The two "not possible" rows are the blockers for the revised objective
(discovering ONE Naval-AI architecture), and both are geometry-kernel work
ahead of any generative model.
