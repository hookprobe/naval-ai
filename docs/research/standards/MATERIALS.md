# Free material property data for small-craft structures

Research record, dated 2026-08-13. Not a plan and not a status source — see
`CLAUDE.md` for which artifact owns which question. Every table below was
transcribed from a document that was opened in this session; the verification
log names them, and what could not be opened is listed as such.

## The short answer — best free sources by material family

| Need | Best FREE source | Basis it gives |
|---|---|---|
| Solid wood ultimate properties + COV | **FPL Wood Handbook FPL-GTR-190 Ch. 5** (§1) | MEAN ultimate, clear specimens, with published COV |
| Plywood panel ultimate properties | **FPL-GTR-282 Ch. 12, Table 12-2** (§2.2) | mean ultimate, by species |
| Plywood **ALLOWABLES** + wet/creep/duration factors | **APA *Panel Design Specification*** (§2.3) | allowable-stress design capacities, conservative by construction |
| Wood/epoxy fatigue + size effect + moisture formula | **Gougeon Brothers on Boat Construction, 5th ed.** (§3) | mean ultimate + measured knock-downs; **no allowables** |
| Foam core, with a **minimum** basis | **Diab Divinycell H** (§4.1) and **3A Airex C70** (§4.2, DNV-GL minimums) | nominal AND minimum guaranteed |
| Honeycomb core, with a minimum basis | **Hexcel HexWeb Attributes and Properties** (§4.5) | typical AND minimum, L and W directions |
| Fibre properties, carbon grades | **SP Systems / Gurit *Guide to Composites*** (§5.2, §6.1) | typical ultimate, basis not stated |
| FRP property vs fibre content **FORMULA** | **MIL-HDBK-17-3E** normalization rule (§5.3.2) | exact, for fibre-dominated properties only |
| FRP hot/wet and temperature knock-downs | **MIL-HDBK-17-2F Table A1.1** (§5.4.1) | mean + SD, dry vs wet at four temperatures |
| **Sandwich failure criteria** (wrinkling, dimpling, core shear, D) | **Zenkert, *An Introduction to Sandwich Structures*** (§7.2) | design formulas with derivations and validity bounds |
| **Marine GRP laminate table by glass content** | **NONE FOUND** — see §5.1 and §8 | — |

## Why this file exists

`navalai` computes scantlings for 5–15 m craft. A scantling formula returns a
required section modulus or a required thickness only once you supply an
**allowable stress** and a **modulus** for the actual material. ISO 12215-5
embeds that table and costs money; this project has no budget. This file
records what is FREE, AUTHORITATIVE and CITABLE, transcribed from documents
that were actually opened.

## Rules this file follows

1. Every number carries **units** and states whether it is **ULTIMATE** (failure)
   or **ALLOWABLE** (design), and at what safety factor if one is stated.
2. The **statistical basis** is recorded where the source states it (mean /
   typical / nominal / minimum guaranteed / B-basis / A-basis / characteristic).
   Where the source does not state one, that is written down as *basis not
   stated* — an undocumented uncertainty is a defect, not a detail.
3. **Manufacturer data is labelled as manufacturer data.** It is legitimate
   here (Diab, Gurit, 3A, Hexcel publish real test data with test methods) but
   it is NOT a standardised value and it is NOT a class-approved minimum unless
   the datasheet says so.
4. Anything not opened is marked **UNVERIFIED**.
5. **NOT FOUND is a valid result.** No allowable is invented. A wrong material
   allowable produces an unsafe boat and no test in this repository would catch
   it.

### Verification log — what was actually opened

| # | Document | Opened | How |
|---|---|---|---|
| 1 | Wood Handbook FPL-GTR-190 Ch. 5, *Mechanical Properties of Wood* | YES | PDF text-extracted |
| 2 | Wood Handbook FPL-GTR-282 Ch. 12, *Mechanical Properties of Wood-Based Composite Materials* (2021) | YES | PDF text-extracted |
| 3 | *The Gougeon Brothers on Boat Construction*, 5th ed. | YES | PDF text-extracted, 412 pp |
| 4 | APA *Panel Design Specification* | YES | PDF text-extracted, 28 pp |
| 5 | SP Systems *Guide to Composites* (1998, ancestor of the Gurit guide) | YES | PDF text-extracted, 69 pp |
| 6 | Diab *Divinycell H* datasheet rev 26 SI, May 2026 | YES | PDF text-extracted |
| 7 | 3A Composites *AIREX C70* datasheet 08.2022 | YES | PDF text-extracted |
| 8 | 3A Composites *BALTEK SB* datasheet 07.2011 | YES | PDF text-extracted |
| 9 | Gurit *Corecell M* PDS rev 6-1113 | YES | PDF text-extracted |
| 10 | Hexcel *HexWeb Honeycomb — Attributes and Properties* | YES | PDF text-extracted, 36 pp |
| 11 | MIL-HDBK-17-2F (2002) *Polymer Matrix Composites — Materials Properties* | YES | PDF text-extracted, partial vol. |
| 12 | Diab *Guideline to Core and Sandwich* | YES | PDF text-extracted, 32 pp |
| 13 | MIL-HDBK-17-3E (1997) *Polymer Matrix Composites — Materials Usage, Design, and Analysis* | YES | PDF text-extracted, 375 pp |
| 14 | Zenkert, *An Introduction to Sandwich Structures* (free download copy, KTH) | YES | PDF text-extracted, 454 pp |

---

# 1. Solid wood (the basis for plywood and for wood/epoxy construction)

## 1.1 Source

**USDA Forest Products Laboratory, *Wood Handbook — Wood as an Engineering
Material***. Free, public-domain US Government publication, no paywall.

- Centennial Edition: **FPL-GTR-190 (2010)**, Chapter 5 *Mechanical Properties
  of Wood*.
  `https://www.fpl.fs.usda.gov/documnts/fplgtr/fplgtr190/chapter_05.pdf`
  (that host returns 403 to scripted fetches; the identical chapter PDF is
  mirrored at `https://www.precisebits.com/PDF/USFS_mechanical_properties_of_wood.pdf`,
  which is the copy transcribed below).
- Current edition: **FPL-GTR-282 (2021)**. Chapter 12 downloads cleanly from
  `https://research.fs.usda.gov/download/treesearch/62260.pdf`.

## 1.2 Statistical basis — READ THIS BEFORE USING ANY NUMBER BELOW

FPL-GTR-190 §"Mechanical Properties of Clear Straight-Grained Wood" (p. 5-21):

> "Values in Table 5–3 are averages derived for a number of species grown in the
> United States. The tabulated value is an estimate of the average clear wood
> property of the species."

and for the imported-species table (Table 5–5), the handbook explicitly
disclaims representativeness:

> "Values reported in Table 5–5 were collected from the world literature; thus,
> the appropriateness of these properties to represent a species is not known.
> … may not necessarily represent average species characteristics because of
> inadequate sampling."

So: **Tables 5-3 and 5-5 are MEAN ULTIMATE properties of SMALL CLEAR
straight-grained specimens (ASTM D143). They are NOT allowables and they are
NOT the properties of a real board**, which contains knots, slope of grain and
density variation. Table 5-5 additionally has unknown sampling. Anything the
code derives from these must apply (a) a strength-ratio/grade reduction, (b) a
duration-of-load factor, and (c) a safety factor — none of which live in this
table.

**Coefficients of variation — FPL-GTR-190 Table 5–6** ("Average coefficients of
variation for some mechanical properties of clear wood", from tests on 50
species). This is the `sigma` the project's `{value, tier, sigma}` contract
needs for any wood-derived quantity:

| Property | COV (%) |
|---|---|
| Static bending — modulus of rupture | 16 |
| Static bending — modulus of elasticity | 22 |
| Work to maximum load | 34 |
| Impact bending | 25 |
| Compression parallel to grain | 18 |
| Compression perpendicular to grain | 28 |
| Shear parallel to grain, maximum shearing strength | 14 |
| Tension parallel to grain | 25 |
| Side hardness | 20 |
| Toughness | 34 |
| Specific gravity | 10 |

Source: FPL-GTR-190 Table 5–6, p. 5-26 (of the chapter PDF). Basis: average COV
over a limited sampling of specimens.

Two further caveats stated in the same chapter:
- **Modulus of elasticity in Table 5-3/5-5 is measured from a bending test and
  includes shear deflection.** The handbook notes it "may be increased by 10%
  to remove this effect approximately" (FPL-GTR-190 Table 5-3 footnote c).
  Gougeon repeats the same correction (Appendix B-1, footnote 2).
- **Compression perpendicular to grain is reported as stress at PROPORTIONAL
  LIMIT, not ultimate** — "There is no clearly defined ultimate stress for this
  property" (FPL-GTR-190 p. 5-3).

## 1.3 Boatbuilding species — MEAN ULTIMATE, clear specimens, at 12% MC

Transcribed from **FPL-GTR-190 Table 5–3a** (US species, metric) and **Table
5–5a** (imported species, metric). Columns as printed. All values MEAN of clear
specimens, ULTIMATE except where noted.

| Species | Table | MC | SG | MOR (kPa) | MOE (MPa) | Comp ∥ (kPa) | Comp ⊥ prop. limit (kPa) | Shear ∥ (kPa) | Tension ⊥ (kPa) | Hardness (N) |
|---|---|---|---|---|---|---|---|---|---|---|
| Western redcedar | 5–3a | green | 0.31 | 35,900 | 6,500 | 19,100 | 1,700 | 5,300 | 1,600 | 1,200 |
| Western redcedar | 5–3a | 12% | 0.32 | 51,700 | 7,700 | 31,400 | 3,200 | 6,800 | 1,500 | 1,600 |
| Douglas-fir (Coast) | 5–3a | green | 0.45 | 53,000 | 10,800 | 26,100 | 2,600 | 6,200 | 2,100 | 2,200 |
| Douglas-fir (Coast) | 5–3a | 12% | 0.48 | 85,000 | 13,400 | 49,900 | 5,500 | 7,800 | 2,300 | 3,200 |
| Port-Orford cedar | 5–3a | 12% | 0.43 | 88,000 | 11,700 | 43,100 | 5,000 | 9,400 | 2,800 | 2,800 |
| Alaska (yellow) cedar | 5–3a | 12% | 0.44 | 77,000 | 9,800 | 43,500 | 4,300 | 7,800 | 2,500 | 2,600 |

Table 5–5a (imported) prints fewer columns — MOR, MOE, work to max load,
compression ∥, shear ∥, side hardness only. No compression ⊥ and no tension ⊥.

| Species (botanical) | MC | SG | MOR (kPa) | MOE (MPa) | Comp ∥ (kPa) | Shear ∥ (kPa) | Hardness (N) |
|---|---|---|---|---|---|---|---|
| Mahogany, African — *Khaya* spp. | green | 0.42 | 51,000 | 7,900 | 25,700 | 6,400 | 2,800 |
| Mahogany, African — *Khaya* spp. | 12% | — | 73,800 | 9,700 | 44,500 | 10,300 | 3,700 |
| Mahogany, true — *Swietenia macrophylla* | green | 0.45 | 62,100 | 9,200 | 29,900 | 8,500 | 3,300 |
| Mahogany, true — *Swietenia macrophylla* | 12% | — | 79,300 | 10,300 | 46,700 | 8,500 | 3,600 |
| Okoumé — *Aucoumea klaineana* | 12% | 0.33 | 51,000 | 7,900 | 27,400 | 6,700 | 1,700 |
| Dark red meranti — *Shorea* spp. | green | 0.46 | 64,800 | 10,300 | 32,500 | 7,700 | 3,100 |
| Dark red meranti — *Shorea* spp. | 12% | — | 87,600 | 12,200 | 50,700 | 10,000 | 3,500 |
| Light red meranti — *Shorea* spp. | green | 0.34 | 45,500 | 7,200 | 23,000 | 4,900 | 2,000 |
| Light red meranti — *Shorea* spp. | 12% | — | 65,500 | 8,500 | 40,800 | 6,700 | 2,000 |
| White meranti — *Shorea* spp. | green | 0.55 | 67,600 | 9,000 | 37,900 | 9,100 | 4,400 |
| White meranti — *Shorea* spp. | 15% | — | 85,500 | 10,300 | 43,800 | 10,600 | 5,100 |
| Yellow meranti — *Shorea* spp. | green | 0.46 | 55,200 | 9,000 | 26,800 | 7,100 | 3,300 |
| Yellow meranti — *Shorea* spp. | 12% | — | 78,600 | 10,700 | 40,700 | 10,500 | 3,400 |
| Obeche — *Triplochiton scleroxylon* | 12% | 0.30 | 51,000 | 5,900 | 27,100 | 6,800 | 1,900 |
| Limba — *Terminalia superba* | 12% | 0.38 | 60,700 | 7,000 | 32,600 | 9,700 | 2,200 |

**Okoumé (gaboon) is the face/core species of most BS 1088 marine plywood and
it is in Table 5–5a — i.e. in the "world literature, sampling unknown"
category, one row, no compression-perpendicular and no tension-perpendicular
data.** That is the weakest link in the marine-plywood chain and it is called
out in §Gaps.

Sitka spruce is in FPL-GTR-190 Table 5–3a; the row was not transcribed cleanly
from the extracted text and is **NOT YET VERIFIED here**. Gougeon's Appendix
B-1 (§3 below) carries a Sitka spruce row from the 1974 Wood Handbook and that
IS transcribed.

---

# 2. Plywood

## 2.1 What the free sources do and do not give

There are three different things called "plywood properties" and they must not
be mixed:

| Want | Free source | What you get |
|---|---|---|
| Panel mechanical properties by SPECIES | FPL-GTR-282 Table 12–2 | mean ULTIMATE (MOE, MOR, rail shear, glue-line shear) |
| Panel ALLOWABLE design capacities | APA *Panel Design Specification* | ALLOWABLE capacities per foot of width, by span rating, with DOL / moisture / creep factors |
| MARINE plywood (BS 1088 / Lloyd's) allowables | **NOT FOUND FREE** | see §Gaps |

## 2.2 FPL-GTR-282 Table 12–2, "Selected properties of plywood sheathing products"

Source: Cai, Z.; Senalik, C.A.; Ross, R.J. 2021. *Chapter 12: Mechanical
properties of wood-based composite materials.* In: Wood handbook — wood as an
engineering material. GTR FPL-GTR-282. USDA FS FPL. 15 pp.
`https://research.fs.usda.gov/download/treesearch/62260.pdf`
Table footnote: **"From Biblis (2000)"**. Basis: not stated as anything other
than reported values; treat as **MEAN ULTIMATE, sheathing plywood, not marine
plywood**.

| Species | SG | MOE (GPa) | MOR (MPa) | Fibre stress at prop. limit (MPa) | Rail shear strength (MPa) | Glue-line shear strength (MPa) |
|---|---|---|---|---|---|---|
| Baldcypress | 0.50 | 7.58 | 39.23 | 29.4 | 5.6 | 2.7 |
| Douglas-fir | 0.53 | 7.45 | 41.37 | 39.3 | 3.8 | 1.4 |
| Lauan | 0.44 | 7.43 | 33.72 | 28.1 | 4.3 | 1.3 |
| Western redcedar | 0.41 | 8.55 | 37.37 | 33.3 | 4.6 | 1.7 |
| Redwood | 0.41 | 6.96 | 42.61 | 37.4 | 5.3 | 1.5 |
| Southern pine | 0.57 | 7.70 | 37.09 | 26.2 | 5.5 | 1.6 |

(The chapter prints inch–pound in parallel: e.g. Douglas-fir MOE 1.08×10⁶ lb/in²,
MOR 6,000 lb/in².)

**Lauan at MOE 7.43 GPa / MOR 33.7 MPa is the closest free species-level proxy
for an okoumé or meranti marine panel that this survey found.** It is a proxy,
not a substitute — the veneer grade, the glue and the void rules of BS 1088 are
what distinguish marine plywood, and none of those appear in this table.

FPL-GTR-282 Table 12–1 gives the family-level ranges, useful as a sanity bound:

| Material | SG | MOE (GPa) | MOR (MPa) |
|---|---|---|---|
| **Plywood** | 0.4–0.6 | **6.96–8.55** | **33.72–42.61** |
| Oriented strandboard | 0.5–0.8 | 4.41–6.28 | 21.80–34.70 |
| Particleboard | 0.6–0.8 | 2.76–4.14 | 15.17–24.13 |
| Medium-density fiberboard | 0.7–0.9 | 3.59 | 35.85 |
| Glued-laminated timber | 0.4–0.6 | 9.00–14.50 | 28.61–62.62 |
| Laminated veneer lumber | 0.4–0.7 | 8.96–19.24 | 33.78–86.18 |
| Douglas-fir (Coastal), clear | 0.48 | 13.44 | 85.49 |

Note the ratio the table makes visible: **plywood MOR is roughly 40–50% of the
clear-wood MOR of the same species, and MOE roughly 55–65%** — the cross-plies
carry little in the strong direction. Do not feed a clear-wood allowable into a
plywood panel calculation.

## 2.3 APA *Panel Design Specification* — the one free source of plywood ALLOWABLES

**This is the most directly usable free plywood source found.** APA — The
Engineered Wood Association, *Panel Design Specification* (the successor to
Form Y510 *Plywood Design Specification*). Opened via the free mirror
`https://www.socomi.com/wp-content/uploads/APA_PanelDesignSpec.pdf` (28 pp).

Its design values are stated to be conservative by construction (§4.3):

> "Design stresses are conservative … 'low end' of possible values."

and they are **ALLOWABLE STRESS DESIGN capacities at NORMAL DURATION OF LOAD
and CONTINUOUSLY DRY SERVICE**, expressed per foot of panel width so that the
section property is already folded in.

### 2.3.1 Table 4A — Rated Panels Design Capacities (extract)

Units: bending stiffness EI in lb-in²/ft of width; bending strength F_b·S in
lb-in./ft; axial tension F_t·A and axial compression F_c·A in lb/ft.
"Parallel"/"perpendicular" is relative to the panel strength axis.

| Span rating | EI ∥ 5-ply | EI ⊥ 5-ply | F_bS ∥ 5-ply | F_bS ⊥ 5-ply | F_tA ∥ 5-ply | F_cA ∥ 5-ply |
|---|---|---|---|---|---|---|
| 24/0 | 66,000 | 11,000 | 300 | 97 | 3,000 | 4,300 |
| 24/16 | 86,000 | 16,000 | 385 | 115 | 3,400 | 4,900 |
| 32/16 | 125,000 | 25,000 | 445 | 165 | 3,650 | 5,350 |
| 40/20 | 250,000 | 56,000 | 750 | 270 | 3,750 | 6,300 |
| 48/24 | 440,000 | 91,500 | 1,000 | 405 | 5,200 | 7,500 |
| 16 oc | 165,000 | 34,000 | 500 | 180 | 3,400 | 6,000 |
| 20 oc | 230,000 | 40,500 | 575 | 250 | 3,750 | 6,300 |
| 24 oc | 330,000 | 80,500 | 770 | 385 | 4,350 | 7,500 |
| 32 oc | 715,000 | 235,000 | 1,050 | 685 | 5,200 | 9,450 |
| 48 oc | 1,265,000 | 495,000 | 1,900 | 1,200 | 7,300 | 12,150 |

Structural I multipliers (applied to the above): EI ⊥ ×1.6 (5-ply), F_bS ⊥ ×1.5
(5-ply); ∥ multipliers are 1.0. 3-ply and 4-ply columns exist in the same table
and differ — the full table has 3-ply / 4-ply / 5-ply / OSB columns for each of
∥ and ⊥ and should be transcribed in full if the code needs it.

**Caveat for this project: these are US construction sheathing panels indexed by
SPAN RATING, not by thickness, and not marine plywood.** They are usable as a
free, conservative, standards-backed allowable for a plywood panel of known
span rating. They are NOT a substitute for a BS 1088 panel's properties.

### 2.3.2 Adjustment factors — the environmental knock-downs, verbatim

Duration of load, C_D (APA PDS §4.5.1; base is "normal duration of load" per
FPL Report R-1916):

| Time under load | C_D |
|---|---|
| Permanent | 0.90 |
| Normal | 1.00 |
| Two months | 1.15 |
| Seven days | 1.25 |
| Wind or earthquake | 1.60 (check local code) |

Note stated in the source: *"Adjustment for impact load does not apply to
structural-use panels."* — relevant to slamming loads.

Service moisture, C_m (APA PDS §4.5.2). Base capacities apply where equilibrium
moisture content is **< 16%**; where MC in service is **≥ 16%**:

| Capacity | C_m |
|---|---|
| Strength (F_bS, F_tA, F_cA, F_s[Ib/Q], F_v t_v) | **0.75** |
| Stiffness (EI, EA, G_v t_v) | **0.85** |
| Bearing (F_c⊥A) — plywood | 0.50 |
| Bearing (F_c⊥A) — OSB | 0.20 |

**This 0.75 strength / 0.85 stiffness wet knock-down is the single most useful
environmental factor found for plywood in a free source.** A boat's structure is
at or above 16% MC in service by assumption.

Creep, C_c, applied to panel stiffness EI for permanent loads (and cumulative
with C_m):

| Moisture condition | Plywood | OSB |
|---|---|---|
| Dry | 1/2 | 1/2 |
| 16% m.c. or greater | 1/2 | 1/6 |

The source qualifies this: creep need be considered only "when panels will
sustain permanent loads that will stress the product to one-half or more of its
design strength capacity", and describes the data as limited.

Dowel bearing strength for nailed connections (APA PDS §4.4):

| Panel | Specific gravity G | F_e |
|---|---|---|
| Plywood — **Structural I, Marine** | 0.50 | 4,650 psi [32 MPa] |
| Plywood — other grades | 0.42 (if species unknown) | 3,350 psi [23 MPa] |
| OSB — all grades | 0.50 | 4,650 psi [32 MPa] |

This is the ONE place in a free document where a **"Marine" plywood grade gets a
numeric property**: PS 1 Marine grade may be taken at G = 0.50. That is a
fastener property, not a panel strength, but it is a citable anchor.

Panel allowable bearing stress: **360 psi [2.5 N/mm²]** for APA structural-use
panels (§4.4.6), with a reduced value available at 0.04 in. [1.0 mm]
deformation.

---

# 3. Wood/epoxy composite construction — Gougeon Brothers

## 3.1 Source

**Meade Gougeon, *The Gougeon Brothers on Boat Construction*, 5th edition.**
Published FREE and in full as a PDF by Gougeon Brothers Inc. / WEST SYSTEM:
`https://www.westsystem.com/app/uploads/2022/10/GougeonBook-061205-1.pdf`
(412 pp, opened and text-extracted). This is the best free source in the survey
for **wood/epoxy laminate fatigue and size effect**, which nothing else free
covers.

## 3.2 Appendix B-1 — mechanical properties of commonly used boatbuilding woods

The book's own footnote: *"Extracted from Forest Products Laboratory, Wood
Handbook, U.S. Department of Agriculture Handbook No. 72 (1974), pp. 4-7–4-17.
Results of tests on small, clear, straight-grained specimens. Values in the
first line for each species are from tests of green material; those in the
second line are adjusted to 12% moisture content."*

So this is **1974 Wood Handbook data, MEAN ULTIMATE, small clear specimens** —
same basis and same caveats as §1.2, and superseded by FPL-GTR-190/282 where
the species overlap. Its value here is that it covers boatbuilding species the
current handbook tables do not conveniently collect. Units as printed: psi,
MOE in 10⁶ psi.

| Species | MC | SG | MOR (psi) | MOE (10⁶ psi) | Comp ∥ max crushing (psi) | Comp ⊥ at prop. limit (psi) | Shear ∥ (psi) | Tension ⊥ (psi) | Side hardness (lb) |
|---|---|---|---|---|---|---|---|---|---|
| Balsa, medium | green | .17 | 2,900 | .58 | 1,805 | 100 | 300 | 118 | 100 |
| Birch, yellow | green | .55 | 8,300 | 1.50 | 3,380 | 430 | 1,110 | 430 | 780 |
| Birch, yellow | 12% | .62 | 16,600 | 2.01 | 8,170 | 970 | 1,880 | 920 | 1,260 |
| Cedar, Alaskan | green | .42 | 6,400 | 1.14 | 3,050 | 350 | 840 | 330 | 440 |
| Cedar, Alaskan | 12% | .44 | 11,100 | 1.42 | 6,310 | 620 | 1,130 | 360 | 580 |
| Cedar, Port Orford | green | .39 | 6,600 | 1.30 | 3,140 | 300 | 840 | 180 | 380 |
| Cedar, Port Orford | 12% | .43 | 12,700 | 1.70 | 6,250 | 720 | 1,370 | 400 | 630 |
| Cedar, western red | green | .31 | 5,200 | 0.94 | 2,770 | 240 | 770 | 230 | 260 |
| Cedar, western red | 12% | .32 | 7,500 | 1.11 | 4,560 | 460 | 990 | 220 | 350 |
| Douglas fir, Coast | green | .45 | 7,700 | 1.56 | 3,780 | 380 | 900 | 300 | 500 |
| Douglas fir, Coast | 12% | .48 | 12,400 | 1.95 | 7,240 | 800 | 1,130 | 340 | 710 |
| Lauan, light red | green | .41 | 7,500 | 1.44 | 3,750 | — | 840 | — | 500 |
| Lauan, light red | 12% | .44 | 11,300 | 1.67 | 5,750 | — | 1,090 | — | 590 |
| Mahogany, Honduras | green | .45 | 9,300 | 1.28 | 4,510 | — | 1,310 | — | 700 |
| Mahogany, Honduras | 12% | — | 11,600 | 1.51 | 6,630 | — | 1,290 | — | 810 |
| Meranti, dark red | green | .43 | 8,600 | 1.50 | 4,450 | — | — | — | 560 |
| Meranti, dark red | 12% | — | 12,100 | 1.63 | 6,970 | — | — | — | 630 |
| **Okoumé / gaboon** | green | .37 | **7,300** | **1.14** | **3,900** | — | — | — | 380 |
| Pine, white | green | .34 | 4,900 | 0.99 | 2,440 | 220 | 680 | 250 | 290 |
| Pine, white | 12% | .35 | 8,600 | 1.24 | 4,800 | 440 | 900 | 310 | 380 |
| Ramin | green | .59 | 9,800 | 1.57 | 5,395 | — | 994 | 640 | — |
| Ramin | 12% | — | 18,400 | 2.17 | 10,080 | — | 1,514 | 1,300 | — |
| Spruce, black | green | .38 | 5,400 | 1.06 | 2,570 | 140 | 660 | 100 | 370 |
| Spruce, black | 12% | .40 | 10,300 | 1.53 | 5,320 | — | 1,030 | — | 520 |
| **Spruce, Sitka** | green | .37 | 5,700 | 1.23 | 2,670 | 280 | 760 | 250 | 350 |
| **Spruce, Sitka** | 12% | .40 | **10,200** | **1.57** | **5,610** | 580 | 1,150 | 370 | 510 |
| Teak | green | .57 | 11,000 | 1.51 | 5,470 | — | 1,290 | — | 1,070 |
| Teak | 12% | .63 | 12,800 | 1.59 | 7,110 | — | 1,480 | — | 1,030 |
| Pine, loblolly | 12% | .51 | 12,800 | 1.79 | 7,130 | 790 | 1,390 | 470 | 690 |
| Pine, longleaf | 12% | .59 | 14,500 | 1.98 | 8,470 | 960 | 1,510 | 470 | 870 |
| Hickory | 12% | .72 | 20,000 | 2.16 | 9,210 | 1,760 | 2,430 | — | — |

Footnote 2 of the same table: *"Modulus of elasticity measured from a simply
supported, center loaded beam, on a span depth ratio of 14 to 1. The modulus
can be corrected for the effect of shear deflection by increasing it 10%."*
Footnote 3: specific gravity is oven-dry weight over green (or 12% MC) volume.

**Okoumé appears here at MOR 7,300 psi (50.3 MPa) and MOE 1.14×10⁶ psi
(7.86 GPa), GREEN, no 12% row.** That is consistent with FPL-GTR-190 Table 5–5a's
12% row (51,000 kPa / 7,900 MPa) to within a few percent — which is
suspicious rather than reassuring, since it suggests both trace to the same
original measurement. Treat okoumé as ONE measurement of unknown sampling, not
two independent ones.

## 3.3 Appendix B-4 — moisture knock-down FORMULA (worth more than a table)

Source note: *"Extracted from Munitions Board Aircraft Committee, Design of
Wood Aircraft Structures, ANC-18, 1951 … p. 13."*

The rule as printed: *"Corrections to the strength properties should be made
successively for each 1% change in moisture content until the total change has
been covered. For each 1% DECREASE in moisture content, the strength is
multiplied by (1 + P) … For each 1% INCREASE in moisture content, the strength
is divided by (1 + P)"*, where P is the tabulated percentage expressed as a
decimal.

So, with ΔMC in percentage points (positive = drying):

    property(MC₂) = property(MC₁) × (1 + P)^(MC₁ − MC₂)

**Table B-4 — percent increase in strength per 1% decrease in MC (P, in %):**

| Species | Fibre stress at prop. limit | MOR | MOE | Work to max load | Comp ∥ max crushing | Comp ⊥ | Shear ∥ | Side hardness |
|---|---|---|---|---|---|---|---|---|
| Birch, yellow | 6.0 | 4.8 | 2.0 | 1.7 | 6.1 | 5.6 | 3.6 | 3.3 |
| Cedar, northern white | 5.4 | 3.6 | 1.8 | −1.5 | 5.9 | 2.3 | 2.8 | 3.0 |
| Cedar, Port Orford | 5.7 | 5.2 | 1.6 | 1.7 | 6.2 | 6.7 | 2.2 | 2.8 |
| Cedar, western red | 4.3 | 3.4 | 1.6 | 1.3 | 5.1 | 5.1 | 1.6 | 2.3 |
| Fir, Douglas | 4.5 | 3.7 | 1.8 | 1.9 | 5.5 | 5.0 | 1.7 | 2.9 |
| Mahogany, Honduras | 2.6 | 1.3 | 0.8 | −2.9 | 2.5 | 3.9 | — | 1.0 |
| Pine, eastern white | 5.6 | 4.8 | 2.0 | 2.1 | 5.7 | 5.6 | 2.2 | 2.2 |
| Spruce, Sitka | 4.7 | 3.9 | 1.7 | 2.0 | 5.3 | 4.3 | 2.6 | 2.4 |
| Hickory, true | 4.9 | 4.8 | 2.8 | −0.7 | 5.9¹ | 6.6 | −3.9 | — |

¹ printed as "59" in the extracted text; read as 5.9 by context — **flagged as
possibly mis-transcribed, verify against the PDF before use.**

Worked consequence: Douglas-fir MOR from 12% to 20% MC is
12,400 × 1.037^(12−20) = 12,400 × 0.749 ≈ **9,290 psi**, a 25% knock-down —
which is the same order as APA's C_m = 0.75 for a wet panel, from a completely
independent source. Two free sources agreeing on ~0.75 wet strength is the
strongest environmental result in this survey.

## 3.4 Appendix B-2 — curvature knock-down FORMULA for laminated members

From the FPL Wood Handbook p. 10-8 as quoted in the book. Ratio of allowable
design stress in a laminated CURVED member to that in a straight member:

    ratio = 1.00 − 2000 / (R/t)²

where R is the radius and t the thickness of the laminating stock, in the same
units. Worked example given in the source: R = 24 in, t = 3/8 in →
1 − 2000/4096 = 0.512; at t = 1/8 in the ratio is ~0.95.

This is directly codeable and applies to laminated stems, frames and knees.

## 3.5 Appendix B-3 — minimum bend radii, MEASURED at Gougeon (manufacturer test)

Samples 24 in × 6 in, average MC 7%. Smallest radius reached without breaking:

| Material | Thickness (in) | Radius (in) |
|---|---|---|
| Dark red meranti veneer | 1/8 | 8 |
| Douglas fir veneer | 1/8 | 12 |
| Sitka spruce veneer | 1/12 | 11 |
| Red cedar veneer | 1/8 | 10 |
| Okoumé plywood, 5-ply, face grain parallel | 1/4 | 24 |
| Okoumé plywood, 5-ply, face grain perpendicular | 1/4 | 16 |
| Okoumé plywood, 3-ply, parallel | 3/16 | 16 |
| Okoumé plywood, 3-ply, parallel | 5/32 | 8 |
| Okoumé plywood, 3-ply, perpendicular | 5/32 | 6 |

Basis: single-lab test result, no sample size, no statistics. **Manufacturer
data.**

## 3.6 Appendix B-5 — tensile strength of plywood and veneer

Source note: *Michelon, L.C. and Devereaux, R.J., "Composite Aircraft
Manufacture and Inspection" (Harper & Brothers, NY, 1944), p. 164.* Based on
total cross-sectional area, parallel to grain of faces; the single-ply column
assumes the centre ply carries no load. **Aircraft plywood, 1944 data, basis
not stated.**

| Species | MC at test (%) | SG of plywood | Tensile strength, 3-ply (psi) | Tensile strength, single-ply veneer (psi) |
|---|---|---|---|---|
| Birch, yellow | 8.5 | 0.67 | 13,210 | 19,820 |
| Fir, Douglas | 8.6 | 0.48 | 6,180 | 9,270 |
| Fir, white | 8.5 | 0.40 | 5,670 | 8,510 |
| Mahogany, African (*Khaya*) | 12.7 | 0.52 | **5,370** | 8,060 |
| Mahogany, Honduras | 11.4 | 0.48 | 6,390 | 9,580 |
| Pine, eastern white | 5.4 | 0.42 | 5,720 | 8,580 |
| Redwood | 9.7 | 0.42 | 4,770 | 7,160 |
| Spruce, Sitka | 8.2 | 0.42 | 5,650 | 8,480 |
| Tanguile (lauan) | 10.7 | 0.53 | 10,670 | 16,000 |

**Khaya 3-ply at 5,370 psi = 37.0 MPa ULTIMATE tension is the only
species-specific ULTIMATE strength for a mahogany-family marine-type plywood
found in any free source in this survey.**

## 3.7 Wood/epoxy laminate fatigue and SIZE EFFECT — the unique content

The NASA- and DoE-funded Gougeon test programmes are described in Ch. 3 and
Appendix C. What is directly usable:

**Radial (through-thickness) cross-grain tension, Douglas-fir/WEST SYSTEM epoxy
laminate, 5–6% MC:**

| Specimen population | n | Stressed volume | Static mean strength | 10⁷-cycle stress at R = 0.1 |
|---|---|---|---|---|
| Small | 28 | 1.5 × 0.5 × 2.0 in | **393 psi** | 275 psi |
| Large | 35 | 6.0 × 4.0 × 12.0 in | **280 psi** | **134 psi** |

Volume ratio 192:1. **Static size-effect knock-down ≈ 29%. Fatigue size-effect
knock-down ≈ 51%.**

**Rolling shear, same laminate, ~6% MC:**

| Specimen population | n | Stressed volume | Static mean strength | 10⁶-cycle stress at R = 0.1 |
|---|---|---|---|---|
| Small | 29 | 2.5 in³ | 276 psi | 185.5 psi |
| Large | 14 | 160 in³ | 268 psi | **152.2 psi** |

Volume ratio 64:1. Static size effect ~3% (negligible); fatigue size effect
~18%.

The book's own conclusion, quoted: *"This was convincing evidence that size
effect should determine the design allowables for large, fatigue-driven wood
structures."* and *"With the so-called secondary properties, size effect becomes
increasingly severe as cycle counts rise."*

**These are ULTIMATE / endurance stresses, means of the stated populations, NOT
allowables, and no safety factor is applied.** They are the only free fatigue
data for wood/epoxy found.

Also stated in Ch. 3 without a number this file can pin down: a wood laminate is
*"generally about five times stronger in tension parallel to the fiber direction
than tangentially"*.

## 3.8 What Gougeon does NOT give

**The book does not publish a table of design ALLOWABLE stresses and does not
state a recommended safety factor.** That was searched for specifically. It
publishes ULTIMATE properties (Appendix B-1, from the 1974 Wood Handbook),
fatigue curves, and the size-effect knock-downs above, and it leaves the
allowable to the designer. Appendix D is "Scantlings for Well-Known Boats Built
with WEST SYSTEM Epoxy" — worked examples of built boats, not allowables.
**Do not represent any Gougeon number as an allowable.**

Cured-epoxy neat-resin mechanical properties (tensile strength, modulus,
elongation, compressive strength) are in the WEST SYSTEM *Product Guide* /
technical datasheets, not in this book; **NOT YET VERIFIED here.**

---

# 4. Foam and honeycomb core materials

All of §4 is **MANUFACTURER DATA**, not standardised values. Each entry states
the manufacturer's own basis. Where a manufacturer publishes a MINIMUM as well
as a nominal, the minimum is the one a scantling calculation should use — it is
the closest free thing to a characteristic value.

## 4.1 Diab Divinycell H (cross-linked PVC)

Source: **Diab, "PVC Foam | Divinycell H", datasheet rev 26 SI, May 2026**,
`https://diab-media.azureedge.net/eyajkrhd/diab-divinycell-h-may-2026-rev26-si.pdf`
Opened and transcribed in full. All values measured at +23 °C. Properties
marked ¹ measured perpendicular to the plane.

Basis, quoted verbatim from the datasheet:

> "Nominal value is an average value of a mechanical property at nominal
> density. Minimum value is a minimum guaranteed mechanical property a material
> has independently of density."

and from the disclaimer:

> "If not stated as minimum values, the data is average data and should be
> treated as such. Calculations should be verified by actual tests."

| Property | Test | Unit | Basis | H45 | H60 | H80 | H100 | H130 | H160 | H200 | H250 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Density | ISO 845 | kg/m³ | nominal | 48 | 60 | 80 | 100 | 130 | 160 | 200 | 250 |
| Density range | — | kg/m³ | typical | 43–55 | 48–67 | 67–87 | 90–115 | 117–149 | 145–180 | 180–230 | 230–290 |
| Compressive strength¹ | ASTM D1621 | MPa | nominal | 0.6 | 0.9 | 1.4 | 2.0 | 3.0 | 3.4 | 5.4 | 7.2 |
| Compressive strength¹ | ASTM D1621 | MPa | **minimum** | 0.5 | 0.7 | 1.15 | 1.65 | 2.4 | 2.8 | 4.5 | 6.1 |
| Compressive modulus¹ | ASTM D1621-B-73 | MPa | nominal | 50 | 70 | 90 | 135 | 170 | 200 | 310 | 400 |
| Compressive modulus¹ | ASTM D1621-B-73 | MPa | **minimum** | 45 | 60 | 80 | 115 | 145 | 175 | 265 | 350 |
| Tensile strength¹ | ASTM D1623 | MPa | nominal | 1.4 | 1.8 | 2.5 | 3.5 | 4.8 | 5.4 | 7.1 | 9.2 |
| Tensile strength¹ | ASTM D1623 | MPa | **minimum** | 1.1 | 1.5 | 2.2 | 2.5 | 3.5 | 4.0 | 6.3 | 8.0 |
| Tensile modulus¹ | ASTM D1623 | MPa | nominal | 55 | 75 | 95 | 130 | 175 | 205 | 250 | 320 |
| Tensile modulus¹ | ASTM D1623 | MPa | **minimum** | 45 | 57 | 85 | 105 | 135 | 160 | 210 | 260 |
| **Shear strength** | ASTM C273 | MPa | nominal | 0.56 | 0.76 | 1.15 | 1.6 | 2.2 | 2.6 | 3.5 | 4.5 |
| **Shear strength** | ASTM C273 | MPa | **minimum** | 0.46 | 0.63 | 0.95 | 1.4 | 1.9 | 2.2 | 3.2 | 3.9 |
| **Shear modulus** | ASTM C273 | MPa | nominal | 15 | 20 | 27 | 35 | 50 | 60 | 73 | 97 |
| **Shear modulus** | ASTM C273 | MPa | **minimum** | 12 | 16 | 23 | 28 | 40 | 50 | 65 | 81 |
| Shear strain at break | ASTM C273 | % | nominal | 12 | 20 | 30 | 40 | 40 | 40 | 40 | 45 |
| Poisson's ratio | D638-08 | — | typical (σ = 0.045) | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 |

Thermal / service limits from the same datasheet: heat distortion temperature
+125 °C for all grades; continuous temperature range −200/+70 °C; **max process
temperature +90 °C for H45–H80 and +110 °C for H100–H250**; coefficient of
linear thermal expansion 40 × 10⁻⁶ /°C for all grades. Shelf life unlimited in
original packaging *"protected against UV exposure"* — i.e. the manufacturer
states a UV sensitivity but publishes **no UV knock-down factor**.

**No safety factor and no elevated-temperature or fatigue knock-down factor is
published on this datasheet.**

## 4.2 3A Composites AIREX C70 (cross-linked PVC)

Source: **3A Composites Core Materials, "AIREX C70 Universal Structural Foam",
DATA SHEET 08.2022 (replaces 03.2022), doc GM--TDS-094**,
`https://www.3accorematerials.com/uploads/pdf/TDS-AIREX-C70-E-08.2022-ex-Europe.pdf`
Opened and transcribed in full (metric table).

**This is the most useful core datasheet found, because its MINIMUM column has a
declared external basis.** Footnote 1, verbatim:

> "Minimum values acc. DNV-GL definition; density and compressive properties are
> measured with a specimen of at least 40 mm thickness (from center position of
> a block)."

and the header note:

> "The data provided gives approximate values for the nominal density and DNV-GL
> minimum values according to DNV-GL type approval certificate."

So the "Minimum" row is a **class-society-recognised minimum**, which is a
defensible design value in a way an "average" is not.

| Property | Test | Unit | Basis | C70.55 | C70.75 | C70.90 | C70.130 |
|---|---|---|---|---|---|---|---|
| Density | ISO 845 | kg/m³ | average | 60 | 80 | 100 | 130 |
| Density | ISO 845 | kg/m³ | typ. range | 54–69 | 72–92 | 90–115 | 120–150 |
| Compressive strength ⊥ | ISO 844 / ASTM C365 | N/mm² | average | 0.90 | 1.45 | 2.0 | 3.0 |
| Compressive strength ⊥ | ISO 844 / ASTM C365 | N/mm² | **min (DNV-GL)** | 0.75 | 1.10 | 1.7 | 2.6 |
| Compressive modulus ⊥ | ISO 844 / DIN 53421 | N/mm² | average | 69 | 104 | 130 | 170 |
| Compressive modulus ⊥ | ISO 844 / DIN 53421 | N/mm² | **min (DNV-GL)** | 55 | 80 | 110 | 145 |
| Compressive modulus ⊥ | ASTM C365 | N/mm² | average | 58 | 84 | 110 | 145 |
| Compressive modulus ⊥ | ASTM C365 | N/mm² | **min (DNV-GL)** | 45 | 67 | 93 | 123 |
| Tensile strength in plane | ISO 527-1/2 | N/mm² | average | 1.3 | 2.0 | 2.7 | 4.0 |
| Tensile strength in plane | ISO 527-1/2 | N/mm² | **min (DNV-GL)** | 1.0 | 1.6 | 2.2 | 3.0 |
| Tensile modulus in plane | ISO 527-1/2 | N/mm² | average | 45 | 66 | 84 | 115 |
| Tensile modulus in plane | ISO 527-1/2 | N/mm² | **min (DNV-GL)** | 35 | 50 | 65 | 95 |
| **Shear strength** | ISO 1922 | N/mm² | average | 0.85 | 1.2 | 1.7 | 2.4 |
| **Shear strength** | ISO 1922 | N/mm² | **min (DNV-GL)** | 0.70 | 1.0 | 1.4 | 2.1 |
| **Shear modulus** | ISO 1922 | N/mm² | average | 19 | 26 | 35 | 47 |
| **Shear modulus** | ISO 1922 | N/mm² | **min (DNV-GL)** | 16 | 21 | 29 | 39 |
| Shear modulus | ASTM C393 | N/mm² | average | 22 | 30 | 40 | 54 |
| Shear modulus | ASTM C393 | N/mm² | **min (DNV-GL)** | 18 | 24 | 34 | 45 |
| Shear elongation at break | ISO 1922 | % | average | 16 | 18 | 23 | 30 |
| Shear elongation at break | ISO 1922 | % | **min (DNV-GL)** | 10 | 10 | 12 | 20 |
| Thermal conductivity @ RT | ISO 8301 | W/m·K | average | 0.031 | 0.033 | 0.035 | 0.039 |

**Note the test-method dependence, which is a trap for the code:** the SAME
material has shear modulus 19 N/mm² by ISO 1922 and 22 N/mm² by ASTM C393
(C70.55) — a 16% spread from the test standard alone. Any core shear modulus
stored in this project must carry the test method with it, or it is a number
declared twice with two different meanings.

## 4.3 Gurit Corecell M (SAN, marine grade)

**TWO revisions were opened and THEY DISAGREE. Both are transcribed, because the
disagreement is itself the finding.**

- **CURRENT: Gurit, "Technical Datasheet Corecell M — 11-0623"**,
  `https://www.gurit.com/wp-content/uploads/2026/02/TDS-Corecell-M-Foam-11-0623.pdf`
  (3 pp, opened). States the product *"Benefits from DNV, RINA, ABS, Lloyds, BV,
  and IRS certifications"*.
- **SUPERSEDED: Gurit, "Gurit Corecell M — The Marine Foam",
  PDS-Gurit Corecell M-6-1113**, opened via the Rock West Composites mirror.

| Property | Test | Unit | M60 | M80 | M100 | M130 | M200 |
|---|---|---|---|---|---|---|---|
| Nominal density | ISO 845 | kg/m³ | 65 | 85 | 107.5 | 140 | 200 |
| Density range | ISO 845 | kg/m³ | 61–69 | 81–89 | 100–115 | 130–150 | 185–215 |
| Compressive strength | ASTM D1621 / ISO 844 | MPa | **0.69** | **1.16** | **1.72** | **2.58** | 4.40 |
| Compressive modulus | D1621-1973 / ISO 844 | MPa | **48** | **78** | **112** | **169** | 317 |
| **Shear strength** | ASTM C273 | MPa | **0.78** | **1.15** | **1.47** | **1.96** | 2.95 |
| **Shear modulus** | ASTM C273 | MPa | **23** | **34** | **44** | **60** | 98 |
| Shear elongation at break | ASTM C273 | % | 57 | 57 | 50 | 40 | **30** |
| Tensile strength | ASTM D1623 | MPa | **1.21** | **1.74** | **2.23** | **3.00** | 4.29 |
| Tensile modulus | ASTM D1623 | MPa | **67** | **98** | **134** | **186** | 334 |
| Thermal conductivity | ASTM C518 | W/m·K | 0.03 | 0.04 | 0.04 | 0.04 | 0.04 |
| Heat distortion temp. | DIN 53424 | °C | 110 | 110 | 110 | 110 | 110 |

*(Table above = CURRENT revision 11-0623. Bold entries are the ones that CHANGED
from revision 6-1113.)*

**The drift between revisions, measured:**

| Property, M80 | rev 6-1113 | rev 11-0623 | change |
|---|---|---|---|
| Compressive strength (MPa) | 1.02 | 1.16 | **+13.7%** |
| Compressive modulus 1973 (MPa) | 71 | 78 | +9.9% |
| Shear strength (MPa) | 1.09 | 1.15 | +5.5% |
| **Shear modulus (MPa)** | **29** | **34** | **+17.2%** |
| Tensile strength (MPa) | 1.62 | 1.74 | +7.4% |
| Tensile modulus (MPa) | 72 | 98 | **+36.1%** |
| Shear elongation at break (%) | 58 | 57 | −1.7% |

**A core property in this project must carry the datasheet revision string, or
it is ambiguous by up to 36%.** This is the "number declared twice" defect
arriving through a document revision rather than through a second file.

The superseded revision 6-1113 for reference:

| Property | Test | Unit | M60 | M80 | M100 | M130 | M200 |
|---|---|---|---|---|---|---|---|
| Compressive strength | ASTM D1621 | MPa | 0.55 | 1.02 | 1.55 | 2.31 | 4.40 |
| Compressive modulus | ASTM D1621-1973 | MPa | 45 | 71 | 107 | 170 | 317 |
| Compressive modulus | ASTM D1621-2004 | MPa | 31 | 52 | 76 | 111 | 210 |
| Shear strength | ASTM C273 | MPa | 0.68 | 1.09 | 1.45 | 1.98 | 2.95 |
| Shear modulus | ASTM C273 | MPa | 20 | 29 | 41 | 59 | 98 |
| Shear elongation at break | ASTM C273 | % | 53 | 58 | 52 | 43 | 20 |
| Tensile strength | ASTM D1623 | MPa | 0.81 | 1.62 | 2.11 | 2.85 | 4.29 |
| Tensile modulus | ASTM D1623 | MPa | 44 | 72 | 109 | 176 | 334 |

**The 2004 revision of ASTM D1621 was DROPPED between revisions.** The
superseded datasheet published compressive modulus by BOTH D1621-1973 and
D1621-2004 and they differ by **30–35%** on the same foam (M100: 107 vs 76 MPa).
The current datasheet publishes only the 1973 method — the higher of the two.
**Store the test-method revision with the value.**

### Statistical basis

**The CURRENT datasheet (11-0623) states NO statistical basis at all** — there
is no "average", "nominal", "typical" or "minimum" qualifier anywhere in it.
That is a documentation regression: the superseded revision did state one,
verbatim:

> "Data quoted is average data at each product's nominal density, and is derived
> from our regular testing of production materials. Statistically derived
> minimum value data, satisfying the design requirements of various
> classification societies, is available on request."

i.e. **the published values are AVERAGES; the class-acceptable minimums are NOT
published in either revision** and are *"available on request"*. The older
revision credits "GL, DNV, RINA and ABS certification"; the current one adds
Lloyd's, BV and IRS.

**Consequence for this project: Corecell M cannot be used with a
characteristic/minimum basis from free data.** Model with Divinycell H or Airex
C70, both of which publish minimums (§4.1, §4.2), or apply an explicit
engineering reduction to the Corecell averages and say so.

**Engineering note both revisions make explicitly:** Corecell M's selling point
is shear ELONGATION at break (43–58% for M60–M130 vs 20–40% for Divinycell H,
16–30% for Airex C70) — relevant because slamming is a strain-driven, not a
stress-driven, failure. The datasheet claims *"high elongation delivers higher
useful properties and the toughness to give impact resistance and superior
fatigue performance"* but publishes **no fatigue curve and no impact
knock-down**.

## 4.4 3A Composites BALTEK SB (end-grain balsa)

Source: **3A Composites, "BALTEK SB Select Grade Structural Balsa", TDS 07.2011
(replaces 08.2010)**,
`https://www.metyx.com/wp-content/uploads/PDF_Files/AIREX/TDS/KK-TDS-BALTEK-SB%20(07.11).pdf`
Opened and transcribed in full. **This is a 2011 revision — a current one should
be obtained before code depends on it.**

Basis, verbatim: *"The data provided gives approximate values for the nominal
density. Due to density variations these values can be lower than indicated
above. Minimum values to calculate sandwich constructions can be provided upon
request."* — i.e. **published values are TYPICAL AT NOMINAL DENSITY and the
manufacturer explicitly warns they can be exceeded on the low side.**

| Property | Test | Unit | SB.50 | SB.100 | SB.150 |
|---|---|---|---|---|---|
| Apparent nominal density | ASTM C-271 | kg/m³ | 94 | 153 | 247 |
| Compressive strength ⊥ | ASTM C-365 | N/mm² | 6.3 | 12.9 | 26.3 |
| Compressive modulus ⊥ | ASTM C-365 | N/mm² | 1,993 | 4,005 | 7,982 |
| Tensile strength ⊥ | ASTM C-297 | N/mm² | 7.4 | 13.2 | 23.5 |
| Tensile modulus ⊥ | ASTM C-297 | N/mm² | 2,200 | 3,570 | 5,759 |
| **Shear strength** | ASTM C-273 | N/mm² | 1.8 | 3.0 | 4.9 |
| **Shear modulus** | ASTM C-273 | N/mm² | 106 | 160 | 309 |
| Thermal conductivity @ RT | ASTM C-177 | W/m·K | 0.048 | 0.066 | 0.084 |

Operating range stated: −212 °C to +163 °C. Prepreg processing to 180 °C.

**Balsa vs PVC/SAN, the comparison the numbers make:** at ~150 kg/m³, balsa
SB.100 has shear strength 3.0 MPa and shear modulus 160 MPa against Divinycell
H130's 2.2 MPa / 50 MPa at 130 kg/m³ — balsa is **~3× stiffer in shear** per
unit density. What the datasheet does not carry, and what governs a boat, is
**water absorption and rot after core breach**, for which no free number was
found.

## 4.5 Hexcel HexWeb HRH-10 (Nomex aramid-fibre/phenolic honeycomb)

Source: **Hexcel, "HexWeb Honeycomb — Attributes and Properties: A comprehensive
guide to standard Hexcel honeycomb materials, configurations, and mechanical
properties"**,
`https://www.hexcel.com/wp-content/uploads/2026/01/HexWebHoneycombAttributesandProperties.pdf`
Opened, 36 pp, p. 30 transcribed.

**This source publishes BOTH typical and MINIMUM columns**, which makes it the
best-documented core in this survey. Units as printed: psi and ksi. Test data
obtained at 0.500 in thickness. Designation is `material – cell size (in) –
density (lb/ft³)`.

Hexagonal HRH-10:

| Designation | Bare comp. strength (psi) typ | Stabilised comp. strength (psi) typ / **min** | Stab. comp. modulus (ksi) typ | Plate shear L strength (psi) typ / **min** | Plate shear L modulus (ksi) typ | Plate shear W strength (psi) typ / **min** | Plate shear W modulus (ksi) typ |
|---|---|---|---|---|---|---|---|
| HRH-10-1/8-1.8 | 105 / **85** | 115 / **95** | 8 | 90 / **75** | 3.8 | 50 / **40** | 1.5 |
| HRH-10-1/8-3.0 | 300 / **235** | 325 / **270** | 20 | 175 / **155** | 6.0 | 100 / **85** | 3.5 |
| HRH-10-1/8-4.0 | 520 / **400** | 575 / **470** | 28 | 255 / **225** | 8.6 | 140 / **115** | 4.7 |
| HRH-10-1/8-5.0 | 700 / **560** | 770 / **620** | 37 | 325 / **275** | 10.2 | 175 / **150** | 5.4 |
| HRH-10-1/8-6.0 | 1050 / **850** | 1125 / **925** | 60 | 385 / **330** | 13.0 | 200 / **170** | 6.5 |
| HRH-10-1/8-8.0 | 1675 / **1370** | 1830 / **1450** | 78 | 480 / **400** | 16.0 | 260 / **210** | 9.5 |
| HRH-10-1/8-9.0 | 2000 / **1525** | 2100 / **1600** | 90 | 515 / **425** | 17.5 | 300 / **250** | 11.0 |
| HRH-10-3/16-1.8 | 120 / **95** | 130 / **105** | 8 | 90 / **75** | 3.8 | 50 / **40** | 1.9 |
| HRH-10-3/16-2.0 | 120 / **100** | 140 / **105** | 11 | 110 / **90** | 4.3 | 60 / **45** | 2.1 |
| HRH-10-3/16-3.0 | 300 / **235** | 325 / **270** | 20 | 175 / **140** | 6.5 | 100 / **85** | 3.4 |
| HRH-10-3/16-4.0 | 500 / **430** | 540 / **470** | 28 | 245 / **215** | 7.8 | 140 / **110** | 4.7 |
| HRH-10-3/16-6.0 | 935 / **780** | 1020 / **865** | 60 | 420 / **370** | 13.0 | 225 / **200** | 6.5 |
| HRH-10-1/4-1.5 | 80 / **65** | 90 / **75** | 6 | 70 / **55** | 3.0 | 35 / **25** | 1.3 |
| HRH-10-1/4-2.0 | 140 / **115** | 155 / **125** | 11 | 105 / **85** | 4.0 | 50 / **40** | 2.0 |
| HRH-10-1/4-3.1 | 285 / **240** | 310 / **265** | 21 | 185 / **160** | 6.5 | 90 / **75** | 3.0 |
| HRH-10-1/4-4.0 | 440 / **360** | 480 / **390** | 28 | 250 / **205** | 8.0 | 125 / **100** | 3.5 |
| HRH-10-3/8-1.5 | 95 / **75** | 105 / **80** | 6 | 70 / **55** | 3.0 | 35 / **25** | 1.5 |
| HRH-10-3/8-2.0 | 140 / **115** | 155 / **125** | 11 | 90 / **72** | 3.7 | 55 / **36** | 2.4 |
| HRH-10-3/8-3.0 | 290 / **240** | 320 / **270** | 17 | 185 / **160** | 5.6 | 95 / **80** | 3.5 |

(The bare-compression "min" column is printed in the source; the table above
collapses the typ/min pairs. OX-Core and HRH-310/HRH-36/HRH-49/HRP grades are
in the same document and are not transcribed here.)

**Honeycomb is direction-dependent: L (ribbon) and W (transverse) shear differ
by roughly 2:1.** A sandwich calculation that uses one G for a honeycomb core
is wrong in one of the two directions.

Conversions for the code: 1 psi = 6.895 kPa, 1 ksi = 6.895 MPa,
1 lb/ft³ = 16.018 kg/m³. So HRH-10-1/8-3.0 is a 48 kg/m³ core with L-shear
strength 1.21 MPa (min 1.07) and L-shear modulus 41.4 MPa — directly comparable
with Divinycell H45's 0.56/0.46 MPa and 15 MPa.

## 4.6 Cross-manufacturer core comparison (secondary source)

**SP Systems, *Guide to Composites*, doc GTC-1-1098 (1998)**, p. 49 "Cores –
Properties". Opened via the Ghent University mirror
`https://composites.ugent.be/home_made_composites/documentation/SP_Composites_Guide.pdf`.
This is the ancestor of the current Gurit *Guide to Composites*. Its core table
is footnoted *"Data from Reinforced Plastics Handbook, 1st edition. Reprinted by
permission of the publishers."* — i.e. **third-hand, ranges only, basis not
stated, 1998 vintage.** Use it for order-of-magnitude bracketing across core
families only; prefer §4.1–4.5 for any number that enters a calculation.

| Property | Unit | Corecell (SAN) | Linear PVC | X-linked PVC | Copolymer | PU rigid | PEI/PES | Al honeycomb | Aramid honeycomb |
|---|---|---|---|---|---|---|---|---|---|
| Nominal density | kg/m³ | 50–200 | 50–80 | 40–80 | 100–200 | 200–400 | — | 60 | 80 |
| Compressive strength | N/mm² | 0.4–0.9 | 0.5–1.4 | 2.0–4.6 | 4.0–13.0 | — | — | 0.42 | 0.75 |
| Shear strength | N/mm² | 0.5–1.2 | 0.4–1.2 | 1.6–3.5 | 3.0–8.0 | — | — | 0.41 | 0.9 |
| Shear modulus | N/mm² | 15–21 | 12–30 | 38–77 | 60–240 | — | — | 4.1 | 18 |
| Max operating temp | °C | 55–60 | 65–75 | 80 | 80 | 150 | 190 | — | — |

The column-to-property alignment in the extracted text of this table is
imperfect (the PDF's columns interleave metric and imperial rows). **Treat the
whole table as INDICATIVE and mis-alignment-prone; it is recorded for its
family-level shape, not for any single value.**

## 4.7 The governing rule for core data, from the manufacturer itself

Diab, *Guideline to Core and Sandwich* (opened, 32 pp),
`https://www.diabgroup.com/media/q5yldbe4/diab-guideline-to-core-and-sandwich.pdf`,
§"Mechanical properties – terminology", verbatim:

> "It is customary in the industry to publically provide nominal values on
> strength values; however, when doing structural design, it is recommended to
> use certified minimum values to make sure correct safety factors are used."

**This is the manufacturer stating that its own headline numbers are not design
values.** The rule this project should follow, from that:

- Divinycell H → use the **Minimum** row (§4.1), which is published.
- Airex C70 → use the **min (DNV-GL)** row (§4.2), which is published and is the
  type-approval minimum.
- Corecell M → published data is AVERAGE only; the class-acceptable minimum is
  *"available on request"* and is **NOT in any free source**. See §Gaps.
- Baltek SB → published data is TYPICAL only; minimums *"can be provided upon
  request"*. **NOT in any free source.** See §Gaps.
- HRH-10 honeycomb → use the **min** columns (§4.5), which are published.

---

# 5. FRP / GRP single-skin laminates

## 5.1 The honest headline

**No free, authoritative, standardised table of MARINE hand-laid GRP laminate
properties (CSM / woven roving / biaxial, polyester / vinylester) as a function
of glass content was found.** That is the single largest gap in this survey and
it is the property set a small-craft scantling calculation most needs. What free
sources do give:

| Free source | What it gives | What it does NOT give |
|---|---|---|
| MIL-HDBK-17-2F | fully documented **aerospace prepreg** E-glass/epoxy fabric laminate data, dry AND wet, at four temperatures, with SD and CV | anything hand-laid, anything polyester, anything CSM |
| MIL-HDBK-17-3E | the **method**: basis definitions, normalization formula, micromechanics | a marine allowable |
| SP Systems / Gurit *Guide to Composites* | fibre and carbon-grade property tables; qualitative laminate behaviour | numeric laminate tables (its laminate comparisons are BAR CHARTS with no printed values) |
| SSC-360 / SSC-403 | reportedly the marine laminate tables — **COULD NOT BE OPENED**, see §5.5 | — |

## 5.2 Reinforcing fibre properties (the input to any micromechanics estimate)

Source: **SP Systems, *Guide to Composites*, doc GTC-1-1098 (1998)**, p. 24
"Basic Properties of Fibres and Other Engineering Materials". Opened via
`https://composites.ugent.be/home_made_composites/documentation/SP_Composites_Guide.pdf`
**Manufacturer/trade-association data. Basis not stated — treat as TYPICAL
ULTIMATE fibre properties, not allowables.**

| Material | Tensile strength (MPa) | Tensile modulus (GPa) | Density (g/cm³) | Specific modulus |
|---|---|---|---|---|
| Carbon HS (high strength) | 3500 | 160–270 | 1.8 | 90–150 |
| Carbon IM (intermediate modulus) | 5300 | 270–325 | 1.8 | 150–180 |
| Carbon HM (high modulus) | 3500 | 325–440 | 1.8 | 180–240 |
| Carbon UHM | 2000 | 440+ | 2.0 | 200+ |
| Aramid LM | 3600 | 60 | 1.45 | 40 |
| Aramid HM | 3100 | 120 | 1.45 | 80 |
| Aramid UHM | 3400 | 180 | 1.47 | 120 |
| **Glass — E-glass** | **2400** | **69** | **2.5** | 27 |
| Glass — S2-glass | 3450 | 86 | 2.5 | 34 |
| Glass — quartz | 3700 | 69 | 2.2 | 31 |
| Aluminium alloy (7020) | 400 | 69¹ | 2.7 | 26 |
| Titanium | 950 | 110 | 4.5 | 24 |
| Mild steel (55 grade) | 450 | 205 | 7.8 | 26 |
| Stainless steel (A5-80) | 800 | 196 | 7.8 | 25 |
| HS steel (17/4 H900) | 1241 | 197 | 7.8 | 25 |

¹ printed as "1069" in the extracted text; 69 GPa is the physically correct
value for aluminium and the "10" is an extraction artefact of the adjacent
column. **Flagged.**

**E-glass at E_f = 69 GPa, ρ_f = 2.5 g/cm³, σ_f = 2400 MPa is the anchor for
every glass-laminate estimate below.**

## 5.3 The FORMULAS relating laminate properties to fibre content

These are worth more than any table, per the brief, and they come from free
sources.

### 5.3.1 Mass fraction → volume fraction

The reinforcement is specified by MASS (g/m² of cloth, or "glass content by
weight" ψ) but the mechanics are driven by VOLUME fraction V_f. The conversion
is elementary and exact:

    V_f = (ψ / ρ_f) / ( ψ/ρ_f + (1 − ψ)/ρ_m )

with ψ = fibre MASS fraction, ρ_f = fibre density, ρ_m = cured matrix density.
For E-glass (ρ_f = 2.5) in polyester (ρ_m ≈ 1.2):

| Glass mass fraction ψ | Fibre volume fraction V_f |
|---|---|
| 0.30 | 0.171 |
| 0.35 | 0.205 |
| 0.40 | 0.242 |
| 0.45 | 0.282 |
| 0.50 | 0.324 |
| 0.55 | 0.370 |
| 0.60 | 0.419 |
| 0.65 | 0.471 |
| 0.70 | 0.528 |

(Computed here from the identity above with ρ_f = 2.5, ρ_m = 1.2 g/cm³ — an
arithmetic conversion, not a measurement. Restate ρ_m for vinylester/epoxy;
epoxy is nearer 1.15–1.20.)

### 5.3.2 Fibre-dominated property scales LINEARLY with fibre volume — the
### normalization rule

**MIL-HDBK-17-3E (1997), Volume 3, §1.7 Glossary, "Normalized Stress"**,
verbatim:

> "Stress value adjusted to a specified fiber volume content by multiplying the
> measured stress value by the ratio of specimen fiber volume to the specified
> fiber volume."

and "Normalization":

> "A mathematical procedure for adjusting raw test values for fiber-dominated
> properties to a single (specified) fiber volume content."

i.e.

    σ(V_f, target) = σ(V_f, measured) × V_f,target / V_f,measured

**applicable only to FIBRE-DOMINATED properties** (0° tension, 0° compression,
0° modulus). It is NOT applicable to matrix-dominated properties (interlaminar
shear, transverse tension, in-plane shear of a UD ply), and the handbook is
explicit about that restriction. This is the free, citable formula that lets a
laminate property measured at one glass content be moved to another.

MIL-HDBK-17-2F, Vol. 2 §1.4.3 states the reference fibre volumes the handbook
normalizes to: **50% for ALL glass-fibre-reinforced material**, 60% for
carbon-fibre unidirectional tape, 57% for carbon-fibre fabric.

### 5.3.3 Rule of mixtures — where it lives, and why it is not transcribed here

The classical micromechanics relations (E₁ = E_f V_f + E_m(1−V_f), and the
Hashin composite-cylinder bounds for the transverse and shear moduli) are in
**MIL-HDBK-17-3E §4.2.2.1 "Elastic properties"** (p. 4-6 ff.), which is FREE at
everyspec.com. **The equations in that section did not survive PDF text
extraction** (the handbook uses a glyph-encoded maths font) and are therefore
**NOT transcribed here** — they must be read off the rendered page before being
coded. The section number is recorded so nobody has to search for it again.

What §4.2 states in readable prose and is safe to record: a unidirectional
composite is characterised by **four independent elastic constants** (§4.2.1.2),
its properties are "functions of fiber and matrix physical properties, of their
volume fractions, and perhaps also of statistical parameters associated with
fiber distribution" (§4.2.2), and stress-strain linearity is an assumption, not
a fact (§4.2.1.3).

### 5.3.4 The upper limit on fibre content — a real, citable bound

SP Systems *Guide to Composites*, p. 24, verbatim:

> "As a general rule, the stiffness and strength of a laminate will increase in
> proportion to the amount of fibre present. However, above about 60-70% FVF
> (depending on the way in which the fibres pack together) although tensile
> stiffness may continue to increase, the laminate's strength will reach a peak
> and then begin to decrease due to the lack of sufficient resin to hold the
> fibres together properly."

and, on what is achievable by process (p. 23):

> "in the [marine/industrial] industry, a limit for FVF is approximately
> 30-40%. With the higher quality, more sophisticated and precise processes used
> in the aerospace industry, FVF's approaching [higher values]…"

**This is the single most important process fact for this project: hand lay-up
in a boatyard reaches V_f ≈ 0.30–0.40, which by the identity in §5.3.1 is a
glass MASS fraction ψ ≈ 0.47–0.58 for E-glass in polyester** (computed here:
V_f 0.30 ⇒ ψ 0.472; V_f 0.40 ⇒ ψ 0.581). Any laminate property taken from an
aerospace source at V_f = 0.43–0.60 must be scaled DOWN by §5.3.2 before it
describes a boat — for a MIL-HDBK-17 glass value normalized to V_f = 0.50, a
hand-laid V_f = 0.35 laminate carries **0.70** of the tabulated
fibre-dominated strength.

## 5.4 The one fully documented free E-glass laminate dataset — and its
## environmental knock-downs

Source: **MIL-HDBK-17-2F, *Composite Materials Handbook, Volume 2. Polymer
Matrix Composites — Materials Properties*, 17 June 2002. DISTRIBUTION STATEMENT
A, approved for public release, distribution unlimited.** Free; opened via
`http://www.waveequation.com/HDBK17-Volume2.pdf` (also at everyspec.com and
DTIC, both of which refuse scripted access).

### 5.4.1 Table A1.1 — U.S. Polymeric E-720E/7781 (ECDE-1/0-550) fiberglass
### epoxy, DRY vs WET at four temperatures

Fabrication and physical properties as printed: 8 plies, parallel lay-up,
55–65 psi, cure 2 h/350 °F, postcure 4 h/400 °F; **weight percent resin 34.9,
average specific gravity 1.78, average voids 2.0%, average thickness 0.082 in.**
Test methods: tension ASTM D638 Type 1; shear MIL-HDBK-17 rail; flexure ASTM
D790; bearing ASTM D953; interlaminar shear short-beam.

Values are **Avg** and **SD** of the tested population — i.e. **MEAN ULTIMATE
with a standard deviation. NOT a B-basis or A-basis allowable.** This appendix
is legacy data carried forward in the handbook.

| Property | Dir. | −65 °F dry | −65 °F wet | 75 °F dry | 75 °F wet | 160 °F dry | 160 °F wet | 400 °F dry |
|---|---|---|---|---|---|---|---|---|
| Tension ultimate stress (ksi) | 0° | 69.2 (SD 1.6) | 69.1 (1.7) | **60.4 (1.7)** | **55.7 (1.5)** | 52.5 (1.0) | 42.9 (0.8) | 44.8 (2.0) |
| Tension ultimate stress (ksi) | 90° | 56.0 (2.0) | 56.5 (2.0) | 49.0 (1.8) | 45.9 (1.4) | 42.3 (1.2) | 36.9 (1.1) | 34.9 (1.6) |
| Tension ultimate strain (%) | 0° | 2.93 | 2.70 | 2.43 | 2.12 | 2.05 | 1.61 | 1.80 |
| Tension initial modulus (10⁶ psi) | 0° | 3.30 | 3.38 | **3.12** | **3.12** | 2.95 | 2.76 | 2.60 |
| Tension initial modulus (10⁶ psi) | 90° | 2.90 | 3.02 | 2.82 | 2.78 | 2.50 | 2.65 | 2.30 |
| Compression ultimate stress (ksi) | 0° | 77.1 (4.0) | 75.0 (3.7) | **64.8 (2.9)** | **57.3 (3.8)** | 54.0 (1.4) | 46.2 (1.4) | 23.8 (2.2) |
| Compression ultimate stress (ksi) | 90° | 57.2 (2.7) | 53.9 (2.7) | 50.2 (2.9) | 45.2 (2.4) | 40.8 (2.9) | 36.2 (3.1) | 14.7 (1.6) |
| Compression initial modulus (10⁶ psi) | 0° | 3.50 | 3.45 | 3.25 | 3.10 | 3.15 | 3.03 | 2.45 |
| Shear ultimate stress (ksi) | 0°–90° | 17.5 | — | **14.3 (0.6)** | — | 11.2 | — | — |

and, at three temperatures dry only (Avg / Max / Min):

| Property | Dir. | −65 °F | 75 °F | 160 °F |
|---|---|---|---|---|
| Flexure ultimate stress (ksi) | 0° | 115.6 (119.4/111.5) | **91.7 (93.4/90.3)** | 69.4 (71.1/67.2) |
| Flexure proportional limit (ksi) | 0° | 88.1 | 32.5 | 56.2 |
| Flexure initial modulus (10⁶ psi) | 0° | 2.87 | 3.21 | 2.81 |
| Bearing ultimate stress (ksi) | 0° | 74.1 | 60.8 | 50.0 |
| Bearing stress at 4% elongation (ksi) | 0° | 32.1 | 23.9 | 18.1 |
| Interlaminar shear ultimate (ksi) | 0° | 7.09 | **5.90 (6.07/5.72)** | 6.05 |

**The environmental knock-downs this table MEASURES** (all at 75 °F room
temperature unless stated), derived by division from the rows above:

| Effect | Property | Factor |
|---|---|---|
| **Wet / dry at RT** | tension ultimate 0° | 55.7/60.4 = **0.92** |
| **Wet / dry at RT** | tension ultimate 90° | 45.9/49.0 = **0.94** |
| **Wet / dry at RT** | compression ultimate 0° | 57.3/64.8 = **0.88** |
| **Wet / dry at RT** | tension modulus 0° | 3.12/3.12 = **1.00** |
| **160 °F / 75 °F dry** | tension ultimate 0° | 52.5/60.4 = **0.87** |
| **160 °F / 75 °F dry** | compression ultimate 0° | 54.0/64.8 = **0.83** |
| **160 °F WET / 75 °F dry** ("hot/wet") | tension ultimate 0° | 42.9/60.4 = **0.71** |
| **160 °F WET / 75 °F dry** ("hot/wet") | compression ultimate 0° | 46.2/64.8 = **0.71** |
| **400 °F dry / 75 °F dry** | compression ultimate 0° | 23.8/64.8 = **0.37** |

**The hot/wet knock-down of ≈ 0.71 on both tension and compression is the most
useful FRP environmental number in this survey**, and it is on a 350 °F-cure
aerospace epoxy — a room-temperature-cured polyester or vinylester boat laminate
will be WORSE, not better, because its glass transition is far lower. **Do not
apply 0.71 to a boat laminate as if it were conservative.** It bounds the
problem from the optimistic side only.

Note the compression collapse at 400 °F (0.37) while tension holds at 0.74:
matrix-dominated properties fail first with temperature. Any temperature
knock-down must be applied per-property, not as one number.

### 5.4.2 Table 6.2.3(a) — E-glass fabric/epoxy prepreg, modern documented entry

**MATERIAL: 7781G 816/PR 381 plain weave fabric, EGl/Ep 300-PW.** Fibre:
Clark-Schwebel 7781 E-glass fabric per MIL-C-9084C Type VIII B, DE-75 yarn, 558
finish. Matrix: 3M PR 381. Autoclave cure 260 °F, 100 min, 50 psi.
**Resin content 34–36 wt%; FIBRE VOLUME 43.0–48.4%; ply thickness
0.0091–0.0104 in.; Tg 282 °F ambient, 225 °F wet.**
Normalized by specimen thickness and batch fibre areal weight to **50% fibre
volume** (0.0091 in. cured ply thickness). Tension 1-axis, [0]₅, SRM 4-88.

| Statistic | 73 °F ambient, normalized | 73 °F ambient, measured | 220 °F ambient, normalized | 220 °F ambient, measured |
|---|---|---|---|---|
| F₁ᵗᵘ mean (ksi) | **74.9** | 70.9 | 71.3 | 67.5 |
| F₁ᵗᵘ minimum (ksi) | 70.4 | 62.9 | 67.0 | 60.5 |
| F₁ᵗᵘ maximum (ksi) | 79.6 | 77.8 | 77.4 | 74.4 |
| F₁ᵗᵘ C.V. (%) | 3.66 | 7.07 | 4.02 | 5.89 |
| F₁ᵗᵘ B-value | not presented | not presented | not presented | not presented |
| E₁ᵗ mean (Msi) | **3.83** | 3.64 | 3.64 | 3.44 |
| E₁ᵗ C.V. (%) | 2.63 | 4.51 | 2.78 | 5.40 |
| ε₁ᵗᵘ mean (µε) | — | 17,800 | — | 19,600 |
| No. specimens / batches | 16 / 5 | 13 / 4 | — | — |
| Data class | Interim | Screening | Interim | Screening |

**Footnote (2) of the source, verbatim: "Basis values are presented only for A
and B data classes."** This dataset is Interim/Screening class, so **there is no
B-basis value.** MIL-HDBK-17-3E defines the target it is not meeting:

> "the B-basis value is a 95% lower confidence limit on the tenth percentile of
> a distribution."
> — MIL-HDBK-17-3E §1.7 Glossary, "Tolerance Limit"

**Practical statistical basis for the code:** for E-glass fabric/epoxy the
handbook's own measured coefficient of variation is **2.6–4.5% on modulus and
3.7–7.1% on strength** at aerospace process control. A hand-laid boatyard
laminate will have a materially larger CV and no free source quantifies it.

## 5.5 What could NOT be opened — recorded so nobody repeats the search

These are genuinely FREE, public-release documents that are the RIGHT sources
for marine FRP laminate data, but every host that carries them refused
programmatic access from this session. **Nothing is transcribed from them and
nothing below should be treated as read.**

| Document | Status | URL tried |
|---|---|---|
| **SSC-403, *Design Guide for Marine Applications of Composites*, Eric Greene, Nov 1997, ~278 pp**, Ship Structure Committee / US DOT. Public release, unlimited distribution. **This is the single most on-target free document for this project's FRP needs.** | **UNVERIFIED — NOT OPENED.** `shipstructure.org` currently serves a "Unknown Domain" parking page and its TLS certificate does not match the hostname. | `https://www.shipstructure.org/pdf/403.pdf` |
| **SSC-360, *Use of Fiber Reinforced Plastics in the Marine Industry*, Eric Greene, 1990, ~286 pp** | **UNVERIFIED — NOT OPENED.** DTIC returns HTTP 403 to non-browser clients. | `https://apps.dtic.mil/sti/tr/pdf/ADA230414.pdf` |
| **Eric Greene, *Marine Composites*, 2nd ed., 1999** — was published free at marinecomposites.com | **NO LONGER FREE AT SOURCE.** `marinecomposites.com` now redirects to a GoDaddy "for sale" parking page; `ericgreeneassociates.com/images/MARINE_COMPOSITES.pdf` returns "Page cannot be displayed". | both, 2026-08-13 |

**Recovering SSC-403 is the highest-value single action left in this domain.**
It should be fetched with a browser (not a script) from
`shipstructure.org/pdf/403.pdf` if the site returns, or requested from NTIS
(accession PB98-111651), and its laminate tables transcribed here.

## 5.6 Neat resin properties

**NOT FOUND as numbers in a free source.** The SP Systems / Gurit *Guide to
Composites* compares polyester, vinylester and epoxy tensile strength, tensile
modulus, ILSS and strain-to-failure — but **only as BAR CHARTS with no printed
values** (Figs. at pp. 17–21). Its resin comparison is qualitative:

| Resin | Advantages (verbatim) | Disadvantages (verbatim) |
|---|---|---|
| Polyester | "Easy to use", "Lowest cost of resins available (£1-2/kg)" | "Only moderate mechanical properties", "High styrene emissions in open moulds", "High cure shrinkage", "Limited range of working times" |
| Vinylester | "Very high chemical/environmental resistance", "Higher mechanical properties than polyesters" | "Postcure generally required for high properties", "High styrene content", "High cure shrinkage", "Higher cost than polyesters (£2-4/kg)" |
| Epoxy | "High mechanical and thermal properties", "High water resistance", "Long working times available", "Temperature resistance can be up to 140°C wet / 220°C dry", "Low cure shrinkage" | "More expensive than vinylesters (£3-15/kg)", "Critical mixing", "Corrosive handling" |

The only numeric resin fact recoverable is the epoxy service envelope quoted
above: **140 °C wet / 220 °C dry** — and that is a maximum-temperature claim,
not a strength.

Cured WEST SYSTEM epoxy neat-resin properties are published by Gougeon Brothers
in the *WEST SYSTEM Product Guide* and per-hardener technical datasheets;
**those were not opened in this survey — UNVERIFIED.**

## 5.7 Environmental degradation of GRP: osmosis and microcracking

Qualitative only, from the SP Systems guide (pp. 19–20, opened):

- Microcracking strain: *"The strain that a laminate can reach before
  microcracking depends strongly on the toughness and adhesive properties of the
  resin system."* No number is printed.
- Osmosis: described as a mechanism (water permeating the gelcoat, dissolving
  water-soluble residues, osmotic pressure driving blistering) with the remedy
  being *"the replacement of the affected material"*. **No knock-down factor is
  given.**
- Fatigue: *"Generally composites show excellent fatigue resistance when compared
  with most metals"*, influenced by *"the toughness of the resin, its resistance
  to microcracking, and the quantity of voids"*. **No S-N curve, no endurance
  ratio.**

**There is therefore NO free numeric long-term / creep / UV / osmosis
knock-down for GRP in this survey.** See §Gaps.

---

# 6. Carbon fibre laminates

## 6.1 Commercial PAN-based carbon fibre grades

Source: **SP Systems, *Guide to Composites*, p. 29**, table "Strength and
Modulus Figures for Commercial PAN-based Carbon Fibres", footnoted in the source
as *"Information from manufacturer's datasheets"*. **MANUFACTURER DATA, FIBRE
properties, ULTIMATE, basis not stated, 1998 vintage.** Several of these grades
are still current; several are obsolete.

| Grade | Tensile modulus (GPa) | Tensile strength (GPa) | Origin |
|---|---|---|---|
| **Standard modulus (<265 GPa), a.k.a. "high strength"** | | | |
| T300 | 230 | 3.53 | France/Japan |
| T700 | 235 | 5.3 | Japan |
| HTA | 238 | 3.95 | Germany |
| UTS | 240 | 4.8 | Japan |
| 34-700 | 234 | 4.5 | Japan/USA |
| AS4 | 241 | 4.0 | USA |
| T650-35 | 241 | 4.55 | USA |
| Panex 33 | 228 | 3.6 | USA/Hungary |
| F3C | 228 | 3.8 | USA |
| TR50S | 235 | 4.83 | Japan |
| TR30S | 234 | 4.41 | Japan |
| **Intermediate modulus (265–320 GPa)** | | | |
| T800 | 294 | 5.94 | France/Japan |
| M30S | 294 | 5.49 | France |
| IMS | 295 | 4.12 / 5.5 | Japan |
| MR40 / MR50 | 289 | 4.4 / 5.1 | Japan |
| IM6 / IM7 | 303 | 5.1 / 5.3 | USA |
| IM9 | 310 | 5.3 | USA |
| T650-42 | 290 | 4.82 | USA |
| T40 | 290 | 5.65 | USA |
| **High modulus (320–440 GPa)** | | | |
| M40 | 392 | 2.74 | Japan |
| M40J | 377 | 4.41 | France/Japan |
| HMA | 358 | 3.0 | Japan |
| UMS2526 | 395 | 4.56 | Japan |
| MS40 | 340 | 4.8 | Japan |
| HR40 | 381 | 4.8 | Japan |
| **Ultra-high modulus (~440 GPa)** | | | |
| M46J | 436 | 4.21 | Japan |
| UMS3536 | 435 | 4.5 | Japan |
| HS40 | 441 | 4.4 | Japan |
| UHMS | 441 | 3.45 | USA |

Filament diameter is given as 5–7 µm and density as 1.8 g/cm³ (2.0 for UHM) in
the same document (§5.2 table).

## 6.2 Carbon LAMINATE properties — status

**CMH-17 (Composite Materials Handbook-17, the successor to MIL-HDBK-17) IS NOT
FREE.** Verified 2026-08-13: `cmh17.org/RESOURCES/Purchase-Handbook` and SAE
International sell it (SAE R-540 set); Knovel access is subscription. There is
no publicly downloadable volume.

**The FREE path is the superseded MIL-HDBK-17 revisions, which are US DoD
publications marked "DISTRIBUTION STATEMENT A. Approved for public release;
distribution unlimited" and are hosted openly at everyspec.com:**

| Volume | Revision | Date | Content | Opened? |
|---|---|---|---|---|
| MIL-HDBK-17-1F | Vol 1 of 5 | 17 Jun 2002 | Guidelines for characterization; statistical methods, A/B-basis computation | **UNVERIFIED** (DTIC 403) |
| **MIL-HDBK-17-2F** | Vol 2 of 5 | 17 Jun 2002 | **Materials properties — the data tables** | **YES**, 529 pp opened |
| **MIL-HDBK-17-3E** | Vol 3 of 3 | 23 Jan 1997 | **Materials usage, design and analysis — micromechanics, laminate theory, damage tolerance** | **YES**, 375 pp opened |
| MIL-HDBK-17-3F | Vol 3 of 5 | 17 Jun 2002 | as above, later revision | **UNVERIFIED** |
| MIL-HDBK-17-1E / -3E | — | 1997 | earlier revisions | -3E opened |

Free source URLs that worked from this session:
- MIL-HDBK-17-2F: `http://www.waveequation.com/HDBK17-Volume2.pdf`
- MIL-HDBK-17-3E: `http://everyspec.com/MIL-HDBK/MIL-HDBK-0001-0099/download.php?spec=MIL-HDBK-17-3E.022710.pdf`

**No carbon/epoxy laminate property table has been transcribed into this file
yet.** MIL-HDBK-17-2F Chapters 4–5 carry them (carbon/epoxy and carbon/other
matrices) and the 529-page copy obtained appears to be a partial volume. This is
recorded as outstanding work, not as a gap in the free literature — the data
exists and is free.

## 6.3 Documented carbon knock-downs — what MIL-HDBK-17 does and does not give

**MIL-HDBK-17 gives METHODOLOGY, not a universal knock-down number.** That is
the honest finding and it matters, because a single "carbon knockdown factor"
would be easy to invent and wrong.

What is stated and citable:

- **Impact.** MIL-HDBK-17-3E §4.11.1.4 "Compression after impact" treats CAI as
  a design-driving property and analyses it as a function of laminate stacking
  sequence. The section states that *"CAI of laminates with equivalent damage
  states (size and type) was found to be independent of material"* and that
  *"LSS has a strong effect on CAI"*. **No numeric knock-down factor is
  published** — CAI must be measured for the specific laminate. Detection
  threshold is defined by BVID (barely visible impact damage), §5 and §7.
- **Environment.** §8.3.4.10 lists *"Application of knockdown factors to account
  for environmental effects"* as a durability requirement without supplying the
  factors. The factors come from the DATA (§5.4.1 above shows how: measure
  hot/wet against RT/dry on the actual material system).
- **Impact resistance vs fibre type**, from the SP Systems guide, verbatim:
  carbon fibre's *"impact strength, however, is lower than either glass or
  aramid, with particularly brittle characteristics being exhibited by HM and
  UHM fibres"*, and *"in impact-critical applications, carbon is…"* — i.e. the
  trade is qualitative in the free literature.
- **Galvanic corrosion of metal fittings in contact with carbon** is a
  boat-specific failure mode. **NOT FOUND in any free source in this survey.**

---

# 7. Sandwich theory

## 7.1 What is free and what it is good for

| Reference | Free? | Opened? | Use |
|---|---|---|---|
| **Zenkert, D., *An Introduction to Sandwich Structures*** | **YES** — the author released it publicly because the publisher ceased trading; hosted by KTH at `https://www.diva-portal.org/smash/get/diva2:1366182/FULLTEXT01.pdf` | **YES — 454 pp opened and text-extracted.** See §7.2. | **The best free source in this entire survey for sandwich failure criteria.** Sandwich beam/plate theory, wrinkling, dimpling, core shear, fatigue |
| **Zenkert, D. (ed.), *The Handbook of Sandwich Construction*** | free at `https://www.diva-portal.org/smash/get/diva2:1366187/FULLTEXT01.pdf` | **NOT OPENED. UNVERIFIED.** | design handbook |
| **Hexcel, *HexWeb Honeycomb Sandwich Design Technology*** | **YES**, hexcel.com Technology Manuals | **PARTIAL — only p. 20 obtained** (a fragment mirrored at mecway.com). The full document was not retrieved. | Facing stress, core shear, intracell dimpling, face wrinkling, shear crimping formulas |
| **Diab, *Guideline to Core and Sandwich*** | **YES**, `https://www.diabgroup.com/media/q5yldbe4/diab-guideline-to-core-and-sandwich.pdf` | **YES**, 32 pp | Introductory/qualitative. Core function, test methods, terminology. **It does NOT contain the wrinkling or core-shear design formulas.** |
| **Diab, *Sandwich Handbook* (2003, ~52 pp)** | free, but only located on third-party aggregators (pdfroom, Scribd) | **NOT OPENED. UNVERIFIED.** | the formula-bearing DIAB document |

## 7.2 Zenkert — the formulas, transcribed from the opened text

**Source: Dan Zenkert, *An Introduction to Sandwich Structures*, free download
copy, KTH.** The PDF's own front page states:

> "This is a free download copy of An Introduction to Sandwich Structures. …
> This version has been used as a text in a course on sandwich structures at KTH
> for some time and has been through several minor updates since 1995. I have
> decided to make it publicly available since the publisher is no longer in
> business and therefore the book cannot be purchased anywhere."

Notation: subscript f = face, c = core; t_f = face thickness, t_c = core
thickness, **d = t_f + t_c** (distance between face centroids), E_f / E_c =
Young's moduli, G_c = core shear modulus, b = width.

### 7.2.1 Flexural rigidity — eq. (3.4), §3.1

For a SYMMETRIC sandwich (equal faces, same material), per unit width:

    D = E_f·t_f³/6  +  E_f·t_f·d²/2  +  E_c·t_c³/12
        └─ D_f ─┘     └── D_0 ────┘   └── D_c ──┘

The three terms are, in the source's own words, *"the flexural rigidity of the
faces alone bending about their individual neutral axes"*, *"the stiffness of the
faces associated with bending about the centroidal axis of the entire
sandwich"*, and *"the flexural rigidity of the core"*.

**Thin-face / weak-core approximation — eq. (3.7):**

    D ≈ E_f · t_f · d² / 2

**And, crucially, the source states WHEN that approximation is legitimate**,
which is exactly the kind of validity bound this project should encode rather
than assume:

- Term 1 is under 1% of term 2 when — eq. (3.5) — **(d/t_f)² > 3 × 100**, i.e.
  **d/t_f > 5.77**.
- Term 3 is under 1% of term 2 when — eq. (3.6) —
  **6·E_f·t_f·d² / (E_c·t_c³) > 100**.

The source notes the practical regime: *"the core/face thickness ratio is
commonly in the regime 10 to 50 and the face/core modulus ratio between 50 and
1000."*

**§3.1 gives the SYMMETRIC case. An ASYMMETRIC sandwich (unequal or dissimilar
faces) requires the neutral axis to be located first; that derivation is in the
same chapter but was NOT transcribed here — do not assume D = E_f t_f d²/2 for
an asymmetric lay-up.**

### 7.2.2 Face wrinkling — Chapter 6, and the constant that matters

**This is the section that justifies the warning in §7.3.** Zenkert derives the
critical face stress four ways and they give four different constants in front
of the same cube root. All of the following are transcribed verbatim from the
opened text.

| Case | Equation | Critical face stress |
|---|---|---|
| Hoff, symmetric, **thick core** (h < t_c/2) | (6.10) | **σ_f,cr = 0.91 · (E_f · E_c · G_c)^(1/3)** |
| Differential-equation method, ν_c = 0.3 | (6.16) | **σ_f,cr = 0.85 · (E_f · E_c · G_c)^(1/3)** |
| Hoff, anti-symmetric, thick core | (6.12) | σ_f,cr = 0.51·(E_f E_c G_c)^(1/3) + 0.33·G_c·(t_c/t_f) |
| **Recommended DESIGN formula** | **(6.14)** | **σ_f,cr = 0.5 · (E_f · E_c · G_c)^(1/3)** |

The source's own words on eq. (6.14), verbatim:

> "The reason for using the conservative formula in eq.(6.14) is mainly due to
> the effect of initial irregularities. … In practical cases, initial
> irregularities are likely to reduce the wrinkling strength to about 80% of the
> theoretical. Anyway, eq.(6.14) has proved to be one of the most useful formulas
> in the design of structural sandwich constructions since it shows very good
> agreement with both more sophisticated analytical formulae and also with
> experimental results."

**So: the theoretical constant is 0.85–0.91, the DESIGN constant is 0.5, and the
imperfection knock-down that motivates the gap is "about 80% of the
theoretical".** The 0.5 already contains that knock-down; do not apply it twice.

**Use σ_f,cr = 0.5·(E_f·E_c·G_c)^(1/3) and record it as an ALLOWABLE-style
design formula, not an ultimate.** For thin cores the source gives eqs. (6.11)
and (6.13) with additional t_c/t_f terms; those extracted with garbled maths
glyphs and are **NOT transcribed** — read them off the rendered page if a thin
core is in scope. Validity boundary from the worked example in the source (Al
faces E_f = 70 GPa, E_c = 100 MPa, G_c = 40 MPa): eq. (6.10) is valid for
**t_c/t_f > 30**, and eq. (6.11) below that.

For anisotropic faces, verbatim: *"the modulus of the face should be that which
is included in the bending stiffness of the face, i.e. E_fx, and … the moduli of
the core should be those corresponding to out-of-plane stresses, i.e. E_cz and
G_cxz."* — i.e. for a honeycomb core the wrinkling check uses the
through-thickness E_c and the appropriate in-plane-direction G_c, which is why
§4.5's L/W distinction matters.

### 7.2.3 Intercellular buckling (face dimpling) — §6.7, eq. (6.32)

For hexagonal honeycomb of constant cell size s:

    σ_f,cr = 2·E_f / (1 − ν_f²) · (t_f / s)²

described in the source as *"an empirical formula … which was verified by tests
using several different sandwiches with different face thicknesses and cell
sizes."* For square cells the form is the same with an unspecified constant —
eq. (6.31), σ_f,cr = constant · E_f (t_f/a)².

**This failure mode applies to HONEYCOMB and corrugated cores only, not to
foam.** The source also warns that the wrinkling formulas of §6.2–6.4 apply to
honeycomb *"only … with a cell size much less than the wavelength of the
wrinkles. In practice this may not be the case."*

### 7.2.4 Failure criteria — Chapter 7, §7.1

**(a) Face yielding/fracture in bending — eq. (7.2):**

    σ_fx = M_x · z_fx · E_fx / D_x   ≥  σ̂_fx    (failure)

with the source's warnings: *"the allowables may well differ between tensile and
compressive modes, so that, e.g., even if the compressive face has a nominally
lower stress level, it may be the first to fail if the compressive strength is
lower than the tensile. Hence, the criterion must be used twice, once for each
face."*

**(b) Core shear failure — §7.1(b):** for a beam with a weak core
(E_c ≪ E_f), σ_cx = σ_cy = 0 and the maximum core shear stress reduces to the
transverse force over the shear-carrying depth:

    τ_c = T / d      (weak-core, thin-face approximation; T = transverse force per unit width)

The source's framing: *"the core material is mainly subjected to shear and
carries almost the entire transverse force"*, and the core-yield criterion is
*"very seldom used since most core materials have a higher yield and fracture
strain than the faces."* — i.e. **for a foam-cored boat panel, expect face
failure or wrinkling before core direct-stress failure, but core SHEAR is a live
mode.**

### 7.2.5 Safety-factor practice, from the source's worked examples

Zenkert's worked design problems make the practice explicit, and it is worth
copying:

> "(i) Stiffness: No safety factor"

i.e. **the deflection limit is checked against the actual load with no factor,
while the strength checks carry one.** In the ferry-ramp example (Example 4.3)
the stated requirement is *"a safety factor of 5 against fracture, and the
maximum allowed deformation is 300 mm"*; another exercise in the same text uses
*"safety factor for material failure: 2.0"*. **These are pedagogical values, not
a standard** — they are recorded to show that a factor of 2 to 5 on strength
with none on stiffness is the shape of the practice, not to be lifted as a
number.

The PVC core properties Zenkert uses in Example 4.3 are teaching values and
differ from the current Diab datasheet (§4.1); **use §4.1, not these**:

| Zenkert Example 4.3 core | E_c (MPa) | G_c (MPa) | τ_cr (MPa) |
|---|---|---|---|
| H60 | 55 | 22 | 0.6 |
| H100 | 95 | 38 | 1.2 |
| H130 | 125 | 47 | 1.6 |
| H200 | 195 | 75 | 3.0 |

### 7.2.6 What else was verified

**Diab, *Guideline to Core and Sandwich*, §1.2.1 "The sandwich principle"** —
opened. Its worked comparison of a steel panel against a composite sandwich
panel at equal deflection:

| Panel | Weight | Deflection | Safety factor |
|---|---|---|---|
| Composite sandwich | 4.3 kg/m² | 30 mm | 5.7 |
| Steel | 39 kg/m² | 30 mm | 3.0 |

(Manufacturer's illustrative comparison; the panel dimensions and load are not
stated in the extracted text, so this is **not reproducible** and is recorded
only because it is the sole place in that document where a safety factor
appears.)

Also verified, §"a) Faces": *"The local flexural rigidity [of the faces] is so
small it can often be ignored."* — the standard thin-face assumption, stated by
the manufacturer.

**Hexcel, *HexWeb Honeycomb Sandwich Design Technology*, p. 20 "Computer
modelling of honeycomb sandwich panels"** — the one page obtained. Directly
codeable, verbatim, for an FE representation of a honeycomb core:

    E_X ≈ E_Y ≈ 0        (a very small value may be necessary to avoid singularity)
    ν_xy ≈ ν_xz ≈ ν_yz ≈ 0
    G_xy ≈ 0
    G_xz = G_L           shear modulus in ribbon direction
    G_yz = G_W           shear modulus in transverse direction
    E_Z  = E_C           compressive modulus of core material

with the source's own caveat: *"In general terms, the shear forces normal to the
panel will be carried by the honeycomb core. Bending moments and in-plane forces
on the panel will be carried as membrane forces in the facing skins"*, and *"For
many practical cases, where the span of the panel is large compared to its
thickness, the shear deflection will be negligible."*

## 7.3 What is still NOT in this file

Now verified and transcribed (§7.2): flexural rigidity with its validity bounds,
face wrinkling with FOUR different constants and the recommended design one,
intercellular buckling/dimpling, face-failure and core-shear criteria.

Still missing:

- **Asymmetric sandwich flexural rigidity.** §7.2.1 gives the SYMMETRIC case
  only. A hull with a heavier outer skin is asymmetric and needs the neutral
  axis located first. Zenkert Chapter 3 carries it; not transcribed.
- **Shear crimping.** Named in the Hexcel manual's contents; not obtained.
- **Thin-core wrinkling, eqs. (6.11) and (6.13).** The maths glyphs did not
  extract; read off the rendered page.
- **Core indentation under local/point load**, the mode that actually governs a
  hull under slamming or a hard point. Not located.

**Do not code a wrinkling constant from memory.** §7.2.2 shows the same
phenomenon yielding 0.5, 0.85 and 0.91 depending on the derivation and on
whether the imperfection knock-down is already inside it. That is the "number
declared twice" defect with a structural consequence. The value to use is
**0.5**, from eq. (6.14), and the reason is written down above.

---

# 8. Gaps — material data with no free source found

Ordered by how badly this project needs it.

1. **Marine GRP laminate properties as a function of glass content.** The core
   requirement, and unmet. ISO 12215-5's table is paywalled; SSC-403 is the free
   equivalent and could not be opened (§5.5); no other free authoritative source
   gives CSM / woven roving / biaxial laminate strengths and moduli for
   polyester or vinylester at boatyard fibre volume fractions. **Everything free
   that was found is aerospace prepreg at V_f ≈ 0.43–0.50.**
   *Next action: retrieve SSC-403 with a browser.*

2. **BS 1088 marine plywood mechanical properties.** BS 1088 is a paid British
   Standard and, as far as this survey found, it specifies **veneer quality,
   glue bond, and permissible defects — not mechanical properties**. No free
   source gives a design bending stress or modulus for a BS 1088 okoumé panel.
   The Lloyd's Register *List of Approved Manufacturers of Plywood* was not
   located as a free document in this survey (**UNVERIFIED**); even if found, an
   approval list names manufacturers, it does not publish allowables. The best
   free proxies found are FPL-GTR-282 Table 12–2's "Lauan" row (§2.2) and the
   APA allowable capacities (§2.3) — neither is BS 1088.

3. **APA *Plywood Design Specification* Form Y510 allowable stresses by species
   group and grade-stress-level (S-1/S-2/S-3).** The classic table of F_b, F_t,
   F_c, F_s, F_v and E by species group is **not in the free Panel Design
   Specification** obtained (which is organised by span rating instead) and Y510
   itself is sold through standards resellers. **NOT FOUND FREE.**

4. **Certified minimum (characteristic) values for Gurit Corecell M and Baltek
   SB.** Both manufacturers state the class-society minimums exist and are
   "available on request" (§4.3, §4.4) and publish only averages/typicals.
   Divinycell H and Airex C70 DO publish minimums and should be preferred as the
   modelled cores until the others' minimums are obtained.

5. **Long-term / creep knock-down for foam cores.** None of the four foam
   datasheets opened publishes a creep or sustained-load reduction factor,
   despite PVC and SAN foams being known to creep under sustained shear. The
   only creep factor found anywhere in this survey is APA's C_c for **plywood**
   (§2.3.2). **NOT FOUND for any core.**

6. **UV knock-down.** Diab states Divinycell H must be "protected against UV
   exposure" but publishes no factor (§4.1). Nothing free quantifies UV
   degradation of a foam core, a gelcoat or a laminate. **NOT FOUND.**

7. **Water absorption and post-breach degradation of end-grain balsa.** The
   dominant real-world failure of balsa-cored boats, and the Baltek datasheet
   carries only "good moisture resistance" as prose. **NOT FOUND.**

8. **Osmosis / long-term immersion knock-down for polyester GRP.** Mechanism
   described qualitatively in the SP guide; **no factor found free** (§5.7).

9. **Fatigue data for marine GRP and for foam cores.** Gurit claims Corecell M's
   elongation delivers "superior fatigue performance" and publishes no curve
   (§4.3). The only free fatigue data found in this whole survey is Gougeon's
   for **wood/epoxy** (§3.7). **NOT FOUND for GRP or for cores.**

10. **Carbon/epoxy laminate B-basis allowables.** Free in principle — they are in
    MIL-HDBK-17-2F, whose Chapters 4–5 were not reached in the partial copy
    obtained. **Outstanding work, not a literature gap.**

11. **Galvanic-corrosion design rules for carbon in contact with marine metals.**
    **NOT FOUND free.**

12. **Neat cured-resin mechanical properties (polyester / vinylester / epoxy) as
    numbers.** The free composites guides give bar charts only (§5.6).
    **NOT FOUND as a citable table.**

13. **Sandwich failure-mode formulas — MOSTLY CLOSED.** Zenkert (free, KTH) was
    opened and wrinkling, dimpling, flexural rigidity, face failure and core
    shear are transcribed in §7.2. Still outstanding: asymmetric flexural
    rigidity, shear crimping, thin-core wrinkling eqs. (6.11)/(6.13), and core
    indentation under local load. **Outstanding work, not a literature gap.**

14. **Core indentation / local point-load capacity.** The mode that governs a
    slammed hull bottom or a hard point, and no free source in this survey gives
    a design formula for it. **NOT FOUND.**

## 8.1 Cross-cutting warnings for whoever codes from this file

- **A test method is part of a number.** Airex C70 shear modulus is 19 N/mm² by
  ISO 1922 and 22 N/mm² by ASTM C393 (16% apart); Corecell M compressive modulus
  differs by 30–35% between ASTM D1621-1973 and D1621-2004. Store the method
  alongside the value or the value is ambiguous.
- **Nominal ≠ minimum, and the manufacturer says so** (§4.7). A scantling built
  on a nominal core shear strength has already spent its margin.
- **Nothing in this file is an ISO 12215-5 material value and nothing in it has
  been reconciled against one.** Do not present any number here as
  ISO-compliant.
- **Clear-wood ≠ plywood ≠ marine plywood**, and the three differ by roughly a
  factor of two in bending strength (§2.2).
- **Aerospace V_f ≠ boatyard V_f.** Scale by §5.3.2 before using any prepreg
  number for a hand-laid hull, and remember the scaling is valid only for
  fibre-dominated properties.
- **A datasheet REVISION is part of the number.** Gurit Corecell M's shear
  modulus moved +17% and its tensile modulus +36% between revisions 6-1113 and
  11-0623 (§4.3), and the current revision dropped the second compressive-modulus
  test method entirely. Store the revision string.
- **The wrinkling constant is 0.5, not 0.85 and not 0.91** (§7.2.2). The three
  values are all correct for different derivations; only 0.5 is the design value
  and only it already contains the imperfection knock-down.
- **Nothing in this file is an allowable unless it says so.** Only §2.3 (APA)
  and §7.2.2 eq. (6.14) are design values. Everything else is ultimate, mean,
  nominal or typical.

