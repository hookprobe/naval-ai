# E5 sources — what was used, what was refused, and why

GATE E5 validates the geometry kernel against hulls **someone else drew**.
This file is the acquisition record. `benchmarks/e5_sources.py` is the
machine-readable form of the same information and the two must agree; this
one carries the reasoning.

The measurements live in `data/e5_real_hulls.json` / `.csv`, the offsets under
`tests/e5_real_hulls/<id>/source_offsets.csv`, and the findings in
`docs/gates/E5.md`. Nothing is restated here that those own.

---

## The standard a source has to clear

1. **Published, and citable to a page, table or file.** Not a screenshot, not
   a CAD render, not a forum post, not Wikipedia.
2. **Legally usable.** Public domain, CC0, CC BY, or a closed form. A scan on
   a document-sharing site is neither authorised nor provenance-grade, and
   is refused however convenient.
3. **Geometry, not just coefficients.** A table of six numbers cannot test a
   geometry kernel — two different hulls can produce the same six. A source
   earns a place by publishing lines, offsets or a surface.
4. **Its conventions must be stated by the source**, not inferred by us.
   Draft (canoe body or moulded?), LCB (from where, positive which way?),
   depth (to a deck or to the top of a model?). Where a source does not say,
   the value is recorded as unavailable.

---

## 1. Delft Systematic Yacht Hull Series — USED

**What it is.** 51 systematically varied sailing-yacht canoe bodies, tested
at the Delft Ship Hydromechanics Laboratory from 1974 onward, in five
sub-series.

**Geometry.** *Delft Systematic Yacht Hull Series Geometries data*,
4TU.ResearchData, DOI **10.4121/21501330.v1**, licence **CC0** — all 51 hulls
as 3D IGES NURBS surfaces, published by the institution that ran the series.
The release zip was downloaded and verified against the **publisher's own
MD5** (`87870d25f6afd676a3a2a9b9028715e1`); it matched. So the geometry is not
a transcription at all, and a corrupted download is detectable.

**Scalar hydrostatics.** *DSYHS hydrostatics data*, DOI 10.4121/21501375.v1,
already in this repository (`data/refdata/dsyhs/`), also publisher-MD5
verified. Used **only as an independent cross-check** on the extraction —
never as the source of truth for shape.

**Primary publication.** Gerritsma, J., Moeyes, G. and Onnink, R., *Test
Results of a Systematic Yacht Hull Series*, 5th HISWA Symposium, Amsterdam,
November 1977 (Delft report 452-P). Downloaded from the DSYHS Publications
collection (figshare 21581568, CC BY 4.0), MD5 verified.

**What the primary publication settled, that no dataset states:**

- **the parent hull** — Sysser 1 "resembles closely the successful *Standfast
  43* designed in 1970 by Frans Maas of Breskens" (p. 6);
- **the scale** — "the scale factor of all models has been set to α = 6.25",
  model LWL 1.6 m, full scale 10 m (p. 6);
- **the draught convention** — "draught is referred to the canoe body" (p. 6);
- **depth** — "D_H is depth of the hull, which equals the constant freeboard
  (1.15 m) plus the draught of the canoe body" (p. 14).

That last line is why depth is recoverable at all for this family, and why
the modelled top edge is a flat constant-z line rather than a sheer: the
series was designed to a **constant freeboard**.

**Conventions, as the publisher states them** (4TU hydrostatics `Info` sheet):

| quantity | source definition | transformation applied |
|---|---|---|
| `lwl0` | waterline length, upright | none |
| `bwl0` | waterline beam | none — but see the finding in `docs/gates/E5.md` |
| `tc0` | **maximum canoe-body** draft | none; the difference from "draft at the midship keel" is carried, not absorbed |
| `lcb0` | metres from ½ waterline length, upright | `100·lcb0/lwl0`; sign unchanged, and **verified** rather than assumed (LCF is tabulated the same way and lies further aft on every model, which is only true if negative means aft) |
| `cp0` | longitudinal prismatic | none — published directly, not derived from Cb/Cm |

**What this family cannot do.** Every model normalises to LWL = 10.000 m, so
it supplies **no length diversity at all**. They are round-bilge fin-keel
canoe bodies: no chine, no spray rail, no immersed transom. Fifty-one of them
are one family and a handful of parent forms, not fifty-one independent
pieces of evidence — see `docs/gates/E5.md` for the counts kept apart.

---

## 2. Series 60 — USED (one parent)

**What it is.** The standard methodical series for single-screw merchant
hulls; five parents at block coefficients 0.60 to 0.80, with published body
plans, offset tables and sectional-area curves.

**Source.** Todd, F.H., *Series 60: Methodical Experiments with Models of
Single-Screw Merchant Ships*, DTMB Report 1712, US Government Printing
Office, 1963. **A work of the United States Government — public domain.**
Read from the Internet Archive scan `methodicalexperi00todd`.

**Used: Table 3, p. A-7 — model 4210W**, the 0.60 block-coefficient parent,
with the published `L/B = 7.50` and `B/H = 2.50`.

**This is an OCR transcription and is treated as one.** The house standard
(`benchmarks/holtrop_cases.py`) is that a scan is trusted only when
independent internal checks would *break* under corruption. Two were applied,
both computed from the transcribed table and compared against numbers the
transcription does not contain:

| check | from the transcription | published | difference |
|---|---|---|---|
| total prismatic, from the sectional-area column | 0.6123 | 0.614 | −0.28% |
| LCB, from the same column | 1.484% L aft | 1.50% L aft | 0.016 pt |

Visible OCR damage exists (`1/000` for `1.000`, `6.592` for `0.592`) and is
exactly what these checks are for; each repair is by rule and is recorded in
`scripts/build_e5_other.py`.

**LCB convention.** The report states its own rule in words — LCB is
"positive if forward of amidships and negative if aft" — which is already
this project's convention. **No transformation was applied**, and that fact is
recorded, because "no conversion needed" and "conversion never considered"
are indistinguishable after the event.

**Size is a declared choice.** A methodical series publishes *shape*, as
fractions of L, B and T; it has no natural length. The fixture header names
the length used. Nothing is claimed about a cargo hull of that size existing.

---

## 3. Wigley parabolic hull — USED (partial)

`y = (B/2)(1 − (2x/L)²)(1 − (z/T)²)`, L/B = 10, B/T = 1.6. Wigley, W.C.S.,
Proc. Royal Society A **144** (1934).

Not transcribed, not scanned, not downloaded: **evaluated**. It carries zero
provenance risk, and its particulars have closed forms — volume 4LBT/9,
Cp = Cm = 2/3, Cb = 4/9, LCB exactly 0 — so it doubles as the correctness
test of the independent measurement code itself.

**It has no deck.** `D` is recorded as **UNAVAILABLE**, not estimated, which
makes this hull *partial evidence*: it is excluded from the gate's
complete-hull count.

---

## Investigated and REFUSED

Recorded with reasons, because an absent source and a rejected one look
identical afterwards.

**NPL High Speed Round Bilge Displacement Hull Series** (Bailey, RINA
Maritime Technology Monograph No. 4, 1976) — *access*. RINA copyright, no
licence this project can use. The copies findable on document-sharing sites
are neither authorised nor provenance-grade. Genuinely wanted: a different
hull-form grammar (high-speed round bilge, transom-sterned) at 2.54 m model
length, which would add both a family and a length band.

**Series 60 parent at Cb 0.65 (model 4211W, Table 4)** — *OCR quality*. The
scan loses the "Max. half beam" row entirely, and the table gives each offset
as a fraction of the maximum beam **on that waterline**, so the missing row is
the scale of five of the eight columns. Repairing it by inference is guesswork
wearing a citation.

**Series 60 parents at Cb 0.75 and 0.80** — *out of range on prismatic*.
Published total prismatic 0.758 and 0.805 against a genome bound of 0.710
(from the Froude-number prismatic table in `navalai/limits.py`). These are
full cargo forms; the product does not claim to design them. Their tables are
cited should the bound ever move.

**KCS (KRISO container ship)** — *out of scope by length, not by quality*.
The geometry is already in this repository and MD5-verified, but at 232.5 m
LWL it lies outside the genome's own box, which RCD Article 3(2) bounds to
2.5–24 m. It cannot be encoded, so it cannot be round-tripped, and including
it as a "failure" would report the box's declared scope as a kernel defect.

**Compton (1986) USNA semi-planing transom-stern series** — *not yet
acquired*. The strongest known candidate for the hard-chine gap that both
DSYHS and Series 60 leave wide open. Acquisition route in
`docs/audit/GATE2-PHYSICS-STACK.md`.


---

# Hard-chine sources (GATE E5-CHINE)

E5's corpus is entirely round-bilge or mathematical. These are the sources
acquired for the hard-chine branch. The full findings are in
`docs/gates/E5-CHINE.md`; this section is the acquisition record.

## Fridsma R-1275 — USED, five fixtures

Fridsma, G., *A Systematic Study of the Rough-Water Performance of Planing
Boats*, Davidson Laboratory / Stevens Institute of Technology, Report R-1275,
November 1969. DTIC **AD0708694**; the cover carries *"Approved for public
release; distribution is unlimited"*.

**`geometry_status = PUBLISHED_PARAMETRIC`.** Figure 1 *prints the equations*
— chine planform `(x/9)² + (y/4.5)² = 1`, keel profile
`(x/9)² + (8y/4.5)² = 1` — with beam, bow length, model lengths, deadrise
angles and depth all dimensioned, and the text (p. 9) stating the sections
aft of the bow are constant hard-chine prismatic forms. Nothing is digitised
from a drawing. The design waterline comes from the published load
coefficients Δ/(w·b³) = 0.304 / 0.608 / 0.912.

## Naples Systematic Series — USED for parameters, NOT for geometry

De Luca, F. and Pensa, C., *The Naples warped hard chine hulls systematic
series*, Ocean Engineering **139** (2017) 205–236. Open access, CC BY-NC-ND.

Its **Table 1(a, b)** publishes the deadrise distribution of eight systematic
hard-chine series at three stations each. That single table is what makes the
warp survey possible with no offsets at all, and it is the strongest evidence
in E5-CHINE.

**But NSS yields no hull fixture:** there is no offset table, and the sections
appear only as Figs. 3 and 4 — `IMAGE_ONLY`. And the independence must be
counted honestly: **C2–C5 are C1 with depth and breadth scaled by the same
factor**, preserving homothetic sections and therefore identical hull
coefficients. That is *one* parent geometry with four affine derivatives.

This is the family most worth having in full. Its parent was explicitly
*"changed to obtain the plating as developable surfaces"* so it could be
built from rigid panels — warped hard chine on developable plating is exactly
what NavalAI is for.

## Pacuraru et al. (Galați, 2022) — corroboration only

*CFD Study on Hydrodynamic Performances of a Planing Hull*, JMSE 10 (2022)
1523, MDPI, CC BY. Its validation geometry is LOA 2.611 m — the NSS C1 model.
No offsets, no lines. Relevant to a future chine-**physics** gate, not to
E5-CHINE, which is about geometry.

## Radojcic, Kalajdzic & Simic (2019) — classification only

*Power Prediction Modeling of Conventional High-Speed Craft*, Springer,
ISBN 978-3-030-30606-9. No offsets; its Table 3.1 does not extract from the
PDF and the body plans it reproduces are figures.

It supplies one correction that matters to the independence count. Sect. 3.3
records that **Series 62 (β = 12.5°), Keuning & Gerritsma 1982 (β = 25°) and
Keuning et al. 1993 (β = 30°) are one series** tested across three decades —
Series 62, later PHF, now **DSDS** (Delft Systematic Deadrise Series). So the
warp survey in `docs/gates/E5-CHINE.md` covers **five independent families
over seven deadrise variations**, and must not be described as seven families.

## Series 62 — WANTED, not acquired

Clement, E.P. and Blount, D.L., *Resistance Tests of a Systematic Series of
Planing Hull Forms*, SNAME Transactions **71** (1963) 491–579. Models
4665–4669.

Its deadrise distribution is known second-hand from the NSS table above
(12.5 / 13.0 / 19.2 deg) and, notably, the grammar reproduces it **exactly** —
so Series 62 would be the first hard-chine family E5-CHINE could pass on, if
its offsets could be obtained. The SNAME Transactions volume is paywalled and
no DTIC accession for the underlying DTMB report was found. Not taken from a
document-sharing mirror.

## Photographs and figure crops — REFUSED as geometry

`downloads/hull-examples/world-examples/` holds photographs of a small
round-bilge fin-keel yacht. Photographs have no scale reference, no datum and
no stations; estimating a depth from one is precisely the fabrication E5
forbids. Likewise `Body-plans-of-five-equivalent-hull-forms.png` (a
dimensionless comparative drawing: Series 62, deep-V, two double-chine forms,
rounded bilge) and
`The-characteristics-of-the-tested-models-of-the-NTUA-Series.png` (a crop of a
loading-condition table with its column headers cut off) are `IMAGE_ONLY` and
are used for classification only, never as offsets.
