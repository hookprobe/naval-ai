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

<!-- COLLISION-EXPLANATION BEGIN -->
### The rungs are named `2-PHYS-*`, and the rename is not cosmetic

MEASURED 2026-08-21, while aligning this file against `navalai/gates.py`:
this ladder was originally written as `2A`..`2H`, and **seven of those eight
letters were ALREADY TAKEN by executable gates that mean something entirely
different.**

| letter | `navalai/gates.py` means | this ladder meant |
|---|---|---|
| 2A | CFD-admissibility screen | hydrostatics |
| 2B | Blender generation (negative result) | Wigley free surface |
| 2C | campaign classifier | DSYHS |
| 2D | refusal of pathological hulls | KCS / RANS |
| 2F | STL forensics | planing |
| 2G | KCS benchmark geometry present | waves / RAOs |
| 2H | surface repair on import | wind |

`Gate 2G` was therefore "the KCS STL is on disk" to the runner and "waves,
RAOs and added resistance" to this document — and the runner reports 2G
SKIPPED when the gitignored geometry is absent, so a reader could take
"Gate 2G SKIPPED" as *seakeeping is unverified*. It is the project's signature
defect (A NAME DECLARED TWICE) applied to gate identifiers instead of to
numbers, and it was introduced by this file.

**The executable rows keep their letters** — they are the incumbents, cited by
`README.md`, `data/gate-ledger.json` and eleven test modules. The physics
ladder takes its own namespace instead. `tests/test_gate_integrity.py::
test_no_document_renames_an_executable_gate_letter` is the fence.
<!-- COLLISION-EXPLANATION END -->

| rung | physics | reference | status |
|---|---|---|---|
| **2-PHYS-A** | hydrostatics | **Wigley, analytic** | **GREEN — executable, this file** |
| **2-PHYS-B** | free surface + wave resistance | Wigley (Fn 0.22–0.48) | machinery present, CFD run owed |
| **2-PHYS-C** | displacement-hull resistance, form sensitivity | **DSYHS** | **GREEN — 51 models, 742 points, acquired + MD5-verified** |
| **2-PHYS-D** | RANS / turbulence / solver | KCS | RED, ledgered, demoted |
| **2-PHYS-E** | hard-chine resistance, developable panels | **Naples Systematic Series** | **DATA NOT HELD** |
| **2-PHYS-F** | planing | Fridsma / DSDS / Series 62–65 | out of regime today |
| **2-PHYS-G** | waves, RAOs, added resistance | Wigley + Fridsma | `seakeeping.added_resistance_stawave1` head seas only |
| **2-PHYS-H** | wind | analytical first, NATO-GD for the solver | analytic only |

### 2-PHYS-A is done, and it is the strongest rung in the project
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

**2-PHYS-C (DSYHS) and 2-PHYS-E (Naples) are the two rungs that would actually validate
this product**, and neither can be built here: the datasets are not in the
tree. This is the same blocker as gap E5. `benchmarks/holtrop_cases.py` sets
the standard for acquiring them — one worked example transcribed from an
OCR'd scan, trusted only because two INDEPENDENT internal checks would break
under corruption. **Nothing may be transcribed from memory.**

Priority, per the operator's own ranking:

1. **DSYHS** — highest strategic value; systematic displacement hulls with
   published hydrostatics and resistance. Lets us test that a geometric
   change (L/B, Cp, LCB, B/T) moves resistance the way the physics says.
2. **Wigley CFD (2-PHYS-B)** — highest numerical value; the machinery is already
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
`n_layers=5` per the recorded incident) and kept as the 2-PHYS-D numerical anchor.
Completing the full triplet buys *numerical* credibility we can already
mostly claim, and buys **nothing** about chine physics. The same budget spent
acquiring DSYHS and NSS data would move rungs 2-PHYS-C and 2-PHYS-E from
"data not held" to green.


---

# 2-PHYS-C ACQUIRED, 2-PHYS-E REFUSED — and 2-PHYS-E is blocked twice over (2026-08-21)

## 2-PHYS-C DSYHS — done
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

## 2-PHYS-E Naples Systematic Series — REFUSED, and not only for the obvious reason

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

---

# ~~2-PHYS-E FORENSIC HUNT — the gap is REAL~~ SUPERSEDED 2026-08-21

> **ITS CONCLUSION IS REFUTED. Read the final section of this file**
> ("THE FORENSIC HUNT'S CONCLUSION IS REFUTED") before using anything
> below. The claim that hard-chine series never reach Fn 0.26 is FALSE:
> Compton's 1986 USNA systematic series varies section shape between
> HARD CHINE and ROUND BILGE across **Fn 0.10-0.60**, so our 0.26 is
> interior to it. The ranked table below is still useful for the
> families it covers; its PATTERN ARGUMENT is not.


**Operator directive, 2026-08-21:** do not accept "no published series fills
the gap" until a targeted hunt has been run and every candidate ranked. Run.

## The ranked candidates

| family | hard chine? | tested range | overlaps our Fn 0.26 / FnV 0.61? | data obtainable? |
|---|---|---|---|---|
| **DSYHS** | **no** — round-bilge canoe body | Fn 0.089–1.150 | **YES** | **YES — acquired, publisher MD5** |
| **USCG + TUNS** | **yes** | **FnV 0.6–3.5** | **MARGINAL — our FnV is 0.609/0.621, the very bottom edge** | regression only (open); raw in SNAME Trans. 2006, paywalled |
| Naples NSS | yes, developable-for-plywood | Fr 0.5–1.6 | no | no (Elsevier) |
| NTUA double-chine | yes | Fn 0.5–0.9 | no | no (ResearchGate only) |
| VWS hard-chine catamaran '89 | yes | high speed | no | no |
| Fridsma | yes | planing | no | partial |
| Series 62 / 65 | yes | planing | no | partial |
| NPL / Series 64 | no — round bilge | Fn 0.2–1.2 | yes | partial |

## THE PATTERN, AND IT IS THE ANSWER

Read the "tested range" column. **Every hard-chine series starts at roughly
Fn 0.5 or FnV 0.6.** Every series that reaches down to Fn 0.26 is
**round-bilge**. The two conditions never co-occur.

That is not a gap in the search — it is a fact about why people build hard
chines. **A chine is normally chosen to generate dynamic lift**, so a
hard-chine model gets towed at planing speeds because that is what it is
for. Nobody tows a hard-chine hull at 5 knots, because nobody builds one for
5 knots —

**except us.** This product chooses a chine for BUILDABILITY: developable
plywood panels a person can cut and stitch, at displacement speed. That
combination — hard chine, Fn ~0.26, chosen for construction cost rather than
lift — is precisely the corner of the design space the experimental
literature skips.

~~**So the gap is real, it is explainable, and it will not be closed by
searching harder.**~~ **FALSE — see the refutation at the end of this file.**

## The one lead worth money

**USCG + TUNS.** Its volumetric Froude range (0.6–3.5) touches our design
point at the bottom edge: our 10 m at 5 kn is **FnV 0.609**, our 6 m at 4 kn
is **0.621**. The USCG series is four models from the 47 ft Motor Lifeboat
with warped bottoms, deadrise 16.6–22.5 deg. The regression is open access
(Polish Maritime Research); the underlying model data sit in SNAME
Transactions 2006 behind a paywall. **If the raw offsets and resistance
tables can be obtained, this is the only found family that both has a chine
and reaches our speed.** It is one marginal point, not a validation set — but
it is the only door not yet closed.

## Consequence: 2-PHYS-E splits into two claims

Recording them as one row is what let a solver benchmark be read as physical
validation, and the same mistake must not be repeated here:

| | status |
|---|---|
| **2-PHYS-E-solver** — the mesher and solver handle a chined hull without dying | **GREEN** (25/25 own hulls meshed, 24/25 smoke-converged) |
| **2-PHYS-E-physics** — ΔR_chine at Fn ≈ 0.26 is validated against experiment | **RED — no experiment exists** |

## What 2-PHYS-C does and does NOT mean

**Corrected wording, 2026-08-21.** DSYHS validates a **displacement-hull
hydrodynamic regime**, not our hulls. Decomposing:

    R_T = R_F + R_form + R_wave + R_chine

DSYHS gives real experimental evidence for **R_F** (median 90.4% of measured
total reproduced) and, through its round-bilge geometry, for R_form and
R_wave. It says **nothing about R_chine**. The unvalidated quantity is
precisely

    ΔR_chine = R_hard-chine − R_equivalent-round-bilge   at Fn ≈ 0.26

## The next move, given the literature is empty

Since no experiment exists, **isolate the unknown rather than substitute for
it** (operator's proposal, adopted): generate Hull A (hard chine) and Hull B
(smoothed round-bilge equivalent) holding L, displacement, LCB, waterplane
area, wetted area and Cp fixed, and run both at Fn 0.20/0.23/0.26/0.30/0.35.
ΔC_T between them **does not validate anything** — it QUANTIFIES exactly what
the missing experiment would have to measure, and turns "chine physics is
unvalidated" into a number with an error bar attached to it.

That is scientifically cleaner than comparing two unrelated hulls, and it is
the honest use of a solver whose numerics are anchored (2-PHYS-A, 2-PHYS-C, 2-PHYS-D) and whose
geometry class is not.

---

# THE FORENSIC HUNT'S CONCLUSION IS REFUTED (2026-08-21, operator)

**The section above claims a structural blind spot: "every hard-chine series
starts around Fn 0.5, and every series reaching down to Fn 0.26 is round-bilge
— the two conditions never co-occur." THAT IS FALSE, and the counterexample is
a whole systematic series.**

The operator supplied it: **Roger H. Compton, "Resistance of a Systematic
Series of Semiplaning Transom-Stern Hulls", *Marine Technology and SNAME News*
**23**(4), 345–370, 1986** (DOI `10.5957/MT1.1986.23.4.345`), run in the U.S.
Naval Academy 120-ft towing tank on 5-ft (1.524 m) models of coastal-patrol,
training and recreational powerboats.

    parameter varied        includes
    length/beam ratio       yes
    displacement/length     yes
    LCG                     yes
    SECTION SHAPE           HARD CHINE *and* ROUND BILGE
    measured                calm-water resistance, sinkage, TRIM
    speed range             Fn 0.10 - 0.60

**Fn 0.26 sits in the middle of that range, not at its edge.** Our design point
is interior to the experimental envelope — no extrapolation from a planing
regime, which is the defect that disqualified Naples, NTUA and USCG/TUNS.

## Why this is stronger than "another citation"

The related USNA YP81 programme is a **MATCHED PAIR** study: independent
sources describe **three round-bilge and three hard-chine hulls, tested at
three displacements and three LCG positions — 54 runs**, with the explicit
purpose of studying the effect of a hard versus soft chine on resistance.

That is not a series that happens to contain chined hulls. **It is the
controlled experiment this document proposed to APPROXIMATE in CFD** — the
"equivalent-hull comparison" (Hull A hard-chine vs Hull B round-bilge, other
parameters held) isolating

    dR_chine = R_hard-chine - R_equivalent-round-bilge

Someone already ran it, in water, with a tow post, in the 1980s.

## What this does NOT license

**2-PHYS-E does not go green on a citation.** The lesson 2-PHYS-C earned is
exactly this: DSYHS became evidence when the data was ACQUIRED and
MD5-verified against the publisher, not when the series was named. The state
of the Compton material as searched on 2026-08-21:

| route | state |
|---|---|
| OnePetro (SNAME), DOI `10.5957/MT1.1986.23.4.345` | the paper of record — **paywalled** |
| TU Delft Repositories `uuid:06ad1bae-…` | record exists; **HTTP 403 to automated fetch on BOTH the `resolver.tudelft.nl` and `repository.tudelft.nl/record/` forms** — blocked to a robot, not necessarily to a person |
| Scribd / pdfcoffee / dokumen.tips | OCR scrapes — **NOT provenance-grade, and must not be used as one** |
| USNA NAHL archive (`usna.edu/Hydromechanics/Archive.php`) | holds history, personnel and Trident Scholar PDFs; **no EW-series index and no offsets online**. Contact `stanbro@usna.edu` |
| USNA report numbers seen cited | `EW-20-82` (EHP tests, YP81-7), `EW-12-94` (EHP tests, model YP81) |

### THE NEXT ACTION, and it is one click, not a project

**Open `https://resolver.tudelft.nl/uuid:06ad1bae-46e5-49cd-ad7d-0849df4a9445`
in a browser and look for an attached PDF.** This is the single highest-value
step available on 2-PHYS-E, for a specific reason: that repository's ship-
hydromechanics collection is **where DSYHS came from**, it holds scanned
report series openly, and it is the one route to Compton that is neither a
paywall nor an OCR scrape. A record with an attached PDF would make the paper
citable with provenance; the offsets and tabulated runs are the actual prize.

If the record carries no file, the fallback order is:
1. `stanbro@usna.edu` (NAHL) for the EW-series reports and model offsets —
   `EW-20-82` and `EW-12-94` are the numbers seen cited.
2. SNAME/OnePetro purchase of the paper of record
   (DOI `10.5957/MT1.1986.23.4.345`).

An OCR scrape is NOT a fallback. It is how a checksum stops meaning anything.

So the honest 2-PHYS-E verdict changes from *"no experiment exists"* to:

> **The experiment exists and is the right one. What is missing is the DATA
> with provenance — the model offsets and the tabulated resistance/sinkage/trim
> at Fn 0.20–0.35 — and recovering it is a procurement task, not a research
> question.**

## Corrected status

| rung | before | after |
|---|---|---|
| 2-PHYS-E-solver | GREEN | GREEN (unchanged) |
| 2-PHYS-E-physics | **RED — no experiment exists** | **RED — experiment identified (Compton/USNA YP), data not yet held** |

## And one framing correction that matters more than the citation

The Trieste (1999) and 2001 semi-displacement comparisons cited by the operator
both report that the hard-chine form **slightly INCREASED** resistance while
reducing rolling. So the platform must never encode `hard_chine = better`. It
is a **different hydrodynamic regime**, and the sign of dR_chine depends on Fn,
deadrise, L/B, chine position, LCG and transom immersion. A model that learns
"chine = less drag" from a single comparison would be fitting the sign of one
experiment, not the physics.

## The standing lesson

This document asserted a structural absence in the literature after three
searches, and it was wrong — a systematic series with both section shapes,
spanning our exact Froude number, had existed since 1986. **A negative result
about the literature is a claim about the SEARCH, not about the world**, and it
should be stated with the search that produced it attached, so the next reader
knows what was actually looked at. The claim above is struck rather than
deleted, per PLM §3 step 7.
