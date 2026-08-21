# GATE 2 — the physics stack that replaced "Gate 2M = KCS"

**Operator directive, 2026-08-21.** Gate 2M was written when this project
intended to design arbitrary ships. The product is now **low-cost buildable
plywood boats**: hard-chine, developable panels, shallow draft, displacement
to semi-displacement, often solar-electric. That changes what a meaningful
benchmark is.

> The old question was *"can Naval-AI model arbitrary ships?"* — KCS answered
> it. The new question is *"can Naval-AI autonomously generate physically
> credible, buildable plywood boats?"* — KCS cannot answer it at all.

**The decision: KCS is KEPT and DEMOTED.** Not discarded — demoted from
primary physical anchor to *numerical* anchor, and labelled so in both the
registry and the ledger, with a fence
(`test_gate2d_KCS_is_labelled_SOLVER_VERIFICATION_and_cannot_drift_back`) so
the demotion cannot be quietly undone.

---

## Why KCS stays at all

MEASURED — at model scale it is the same dimensionless problem as our boats:

    case                     L (m)   U (m/s)     Fn         Re
    KCS model                7.279    2.196    0.260    1.40e+07
    our 10 m at 5 kn        10.000    2.572    0.260    2.26e+07
    our 6 m at 4 kn          6.000    2.058    0.268    1.08e+07

So it tests free-surface resolution, layer stack, y+, turbulence closure and
grid convergence **at our own operating point**, against the one case where
the true answer is published. Without an anchor like that a CFD number is
unfalsifiable.

## Why it cannot be the primary anchor

KCS has a **bulbous bow and a round bilge**. Our SKUs are hard-chine sheet
ply. Chine spray, hard-chine separation and transom ventilation are precisely
the physics it cannot exercise. CLAUDE.md has said so since before this
reframe: *"KCS will never validate chine, transom or spray physics — Gate 2M
green is not small-craft validation."*

---

## THE STACK

| rung | physics | reference | status |
|---|---|---|---|
| **2A** | hydrostatics | **Wigley, analytic** | **GREEN — executable, this file** |
| **2B** | free surface + wave resistance | Wigley (Fn 0.22–0.48) | machinery present, CFD run owed |
| **2C** | displacement-hull resistance, form sensitivity | **DSYHS** | **GREEN — 51 models, 742 points, acquired + MD5-verified** |
| **2D** | RANS / turbulence / solver | KCS | RED, ledgered, demoted |
| **2E** | hard-chine resistance, developable panels | **Naples Systematic Series** | **DATA NOT HELD** |
| **2F** | planing | Fridsma / DSDS / Series 62–65 | out of regime today |
| **2G** | waves, RAOs, added resistance | Wigley + Fridsma | `seakeeping.added_resistance_stawave1` head seas only |
| **2H** | wind | analytical first, NATO-GD for the solver | analytic only |

### 2A is done, and it is the strongest rung in the project
The Wigley hull's displaced volume is **exactly 4LBT/9**. No experiment, no
uncertainty band, no scatter to hide in. MEASURED:

    grid        volume      err %
    121 x 25    2.768698    -0.3269
    241 x 61    2.776237    -0.0555
    481 x 121   2.777386    -0.0141
    961 x 241   2.777679    -0.0036

Error falls ~4x per doubling — **second order**, which is what the trapezoid
rule owes. The test asserts convergence, monotonicity AND the order, because
the converged value alone would pass for an integrator that is accidentally
close. Cost: milliseconds, against ~69 h for the KCS triplet.

**This is the operator's point that hydrostatics is a mathematical gate, not
a CFD gate**, made executable.

---

## What is owed, and it is DATA rather than compute

**2C (DSYHS) and 2E (Naples) are the two rungs that would actually validate
this product**, and neither can be built here: the datasets are not in the
tree. This is the same blocker as gap E5. `benchmarks/holtrop_cases.py` sets
the standard for acquiring them — one worked example transcribed from an
OCR'd scan, trusted only because two INDEPENDENT internal checks would break
under corruption. **Nothing may be transcribed from memory.**

Priority, per the operator's own ranking:

1. **DSYHS** — highest strategic value; systematic displacement hulls with
   published hydrostatics and resistance. Lets us test that a geometric
   change (L/B, Cp, LCB, B/T) moves resistance the way the physics says.
2. **Wigley CFD (2B)** — highest numerical value; the machinery is already
   here (`benchmarks/wigley.py` has offsets, exact volume, wetted surface and
   a Michell curve) and it sits at our Fn.
3. **Naples Systematic Series** — highest geometric relevance; hard-chine
   hulls explicitly transformed to developable panels for plywood and
   aluminium construction. This is the closest published family to what the
   product builds. Note the Fn gap: NSS starts near Fr 0.5 while our design
   point is 0.26, so it validates the *transition and above*, not the cruise
   condition.

## What this changes about spending 69 hours

**It should not be spent finishing KCS as previously defined.** The coarse
KCS grid is built, smoke-validated (0.5 s clean, mass conserved, skew 8.93,
`n_layers=5` per the recorded incident) and kept as the 2D numerical anchor.
Completing the full triplet buys *numerical* credibility we can already
mostly claim, and buys **nothing** about chine physics. The same budget spent
acquiring DSYHS and NSS data would move rungs 2C and 2E from
"data not held" to green.


---

# 2C ACQUIRED, 2E REFUSED — and 2E is blocked twice over (2026-08-21)

## 2C DSYHS — done
Downloaded from 4TU.ResearchData (articles 21501375, 21501402), all five
files MD5-verified against the publisher's own checksums, then re-verified by
two independent internal checks (derived Cb vs the released `cb0`: 0.0000%
worst over 61 rows; wetted-surface shape ratio 0.4901..0.6089). **51 models,
742 bare-hull points, Fn 0.089–1.150.**

**MEASURED: our ITTC-57 friction line accounts for a MEDIAN 90.4% of measured
total resistance** over 63 points in Fn 0.12–0.16 across all 51 models. The
rest is form drag plus residual wave-making, which is what it should be.

The band's lower edge is an INSTRUMENT limit, not a fit: below Fn 0.12 the
median ratio is 1.026 — friction exceeding total, impossible for a bare hull
— on a median force of 0.303 N, and the six worst cases sit at Fn 0.100 on
0.11–0.23 N. That is the towing-tank load cell's floor. The test asserts the
excluded band **still** reads above 1.0, so the edge cannot quietly become a
convenience.

## 2E Naples Systematic Series — REFUSED, and not only for the obvious reason

**Blocker 1, access.** NSS is published in *Ocean Engineering* (Elsevier,
2017) and circulated on ResearchGate. There is **no open dataset with
publisher checksums**, so it cannot clear the bar DSYHS cleared. Transcribing
offsets from an abstract or a scan would be exactly what
`benchmarks/holtrop_cases.py` exists to warn against.

**Blocker 2, and this one matters more: THE FROUDE RANGE DOES NOT OVERLAP OUR
PRODUCT.** NSS was tested at **Fr 0.5–1.6** (Re > 3.5e6). Our design point is
**Fn 0.26**. So even fully acquired, NSS would validate the *transition and
planing* regimes — not the cruise condition our boats actually operate at.

**Consequence for priority.** NSS is the geometrically closest published
family — hard chine, explicitly transformed to developable surfaces for
plywood, aluminium and steel construction — and that is genuinely valuable
**when Naval-AI enters semi-planing**. It is NOT the anchor for a 5-knot
10 m displacement boat. It should be acquired when the design space expands
past Fn ~0.4, not before.

**So the hard-chine anchor AT OUR OWN FROUDE NUMBER remains genuinely open,
and no published series found so far fills it.** That is worth stating
plainly rather than substituting a family that is either the wrong shape
(DSYHS: round bilge) or the wrong speed (NSS: planing). The honest position
is that chine physics at Fn 0.26 is currently unvalidated, and the ladder
should say so rather than imply otherwise.
