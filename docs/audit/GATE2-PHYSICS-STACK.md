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
| **2C** | displacement-hull resistance, form sensitivity | **DSYHS** | **DATA NOT HELD** |
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
