# NATIONAL AND GOVERNMENTAL SMALL-CRAFT CODES — what the free texts give us

**STATUS: FIRST PASS COMPLETE, 2026-08-13 — but this file is NOT finished and
says so.** Written incrementally, appended after every source. Seven documents
were read to the depth recorded below; **everything not opened is marked
UNVERIFIED or NOT YET READ, and §10.4 enumerates the leads not followed.**
Priority 6 of the brief (EU member-state national codes) was NOT REACHED.

**Start at §10 if you want the answer;** §§1–8 are the evidence, §9 the
cross-jurisdiction comparison. **§10.5 is the deliberate check against
`docs/research/EU-REGULATORY.md`** — nothing here contradicts it, and one new
caution is raised.

**Scope of this file.** National / supranational REGULATOR-published codes only
(Australia, UK, Canada, USA, New Zealand, EU member states). It deliberately
does NOT cover: EU RCD 2013/53/EU and ES-TRIN (already measured in
`docs/research/EU-REGULATORY.md` — read that first), classification-society
rules, materials databases, or the ISO 12215 / 12217 family itself. Those are
other agents' domains.

**Companion question this file exists to answer:** ISO 12215-5 and ISO 12217-1
cost money and this project has no budget for them. *What do national
regulators publish, for free, that carries the same NUMBERS?*

## Honesty conventions used throughout

- **READ** — the text was opened and the quote transcribed from it. The PDF or
  page URL and the clause number are given.
- **UNVERIFIED** — the document's existence or content is asserted on a search
  result, a citation in another document, or a table of contents, and the text
  itself was not opened. Never treat an UNVERIFIED line as a source.
- **NOT FOUND** — looked for, not located free. This is a result, not a gap in
  the work.
- Every jurisdiction section states the **VESSEL SCOPE** (commercial vs
  recreational, length band, operational area) before any number, because a
  criterion measured at a configuration this product never runs is a known
  defect class here (`docs/LESSONS.md`).

---

## 1 · AUSTRALIA — NSCV (National Standard for Commercial Vessels)

### 1.0 The headline result, stated first

**NSCV Part C Section 3 "Construction" CONTAINS NO SCANTLING FORMULA OF ANY
KIND.** Edition 1.3 is 25 pages and it is a *performance* standard: Chapter 2
states nine required outcomes in prose, and Chapter 3 discharges them by
POINTING AT OTHER DOCUMENTS — Lloyd's Register rules, the ISO 12215 series,
AS 1799, and the USL Code Subsection 5M. There is no design pressure, no panel
thickness, no section modulus, no allowable stress anywhere in it.

This refutes the premise that AMSA publishes detailed free scantlings under
C3. What C3 *does* give free, and it is genuinely valuable, is a **binding
regulator's mapping from operational area to ISO design category** and a
**binding regulator's explicit acceptance of ISO 12215 as a compliance route**
— including the length bands where it is accepted (§1.3, §1.4 below).

The free Australian numbers, if they exist, are in **USL Code Section 5
Subsection 5M (Construction — Wood)**, which C3 references as a deemed-to-
satisfy solution for *all* length bands under 35 m. NOT YET READ — see §1.6.

### 1.1 Document identity and legal status — READ

> National Standard for Commercial Vessels, **Part C — Design and Construction,
> Section 3 — Construction, Edition 1.3**. Published by the Australian Maritime
> Safety Authority. "This edition 1.3 was prepared … to incorporate the NSCV
> Omnibus amendments instrument No.1, 2021. … approved by the National Marine
> Safety Regulator on 23 August 2021 and endorsed by the Infrastructure and
> Transport Ministers on 25 February 2022. This edition 1.3 commences on
> **1 April 2022**." (p. 2)

URL: `https://www.amsa.gov.au/sites/default/files/2023-11/nscv-c3-ed-1.3-february-2022-commencing-1-april-2022.pdf`
(25 pages, text layer intact, extracted with `pypdf`; local copy in the
gitignored `downloads/standards/national/nscv-c3-ed1.3.pdf`).

**Licence — this matters for us, and it is unusually permissive.** p. 2:

> "Except as otherwise specified, all material presented in this publication is
> provided under **Creative Commons Attribution 4.0 International licence**."

with a prescribed attribution string. So unlike ISO text, NSCV content may be
quoted, transcribed into code and redistributed, provided AMSA is credited.
**No other document in this project's standards corpus carries a CC-BY
licence.** (ISO text is copyright and may not be transcribed; the RCD is EU law
under its own reuse terms.)

**VESSEL SCOPE — commercial only.** Cl. 1.2: "This section applies to all
vessels, other than vessels that fall within the application of Part F—Special
Vessels" (Fast Craft, Novel Vessels). Cl. 1.1: "requirements for the
construction of vessels, including the hull, decks, superstructures, deckhouses
and bulkheads." NSCV governs *domestic commercial vessels* in Australia. It is
**not** a recreational code — but note cl. 3.4.2 below, which reaches into the
recreational ISO standards deliberately.

### 1.2 Chapter 2 — the required outcomes, and they carry no numbers

Nine clauses, 2.1–2.9, each one sentence. Transcribed in full because the
absence is the finding:

| cl. | requirement (verbatim opening) |
|---|---|
| 2.1 | "A vessel must be designed and constructed to withstand all static loading in both normal and abnormal conditions of operation." |
| 2.2 | "…to withstand the dynamic loading that may arise…" NOTE: "Dynamic loading includes loading from slamming, rolling, pitching and planing." |
| 2.3 | "…to withstand the loads that arise from the intended operating environment…" |
| 2.4 | "…to withstand any concentrated loading…" |
| 2.5 | "…avoid permanent deformation in normal operations…" and "limit the extent of deformation…" |
| 2.6 | "…incorporate a measure of redundancy to maintain serviceability in the event of structural degradation…" |
| 2.7 | "…to reduce the risks of impact loading…" |
| 2.8 | "Structure subject to cyclical loadings or repeated stress fluctuations must be designed and constructed to avoid or control the risks of fatigue failure." |
| 2.9 | "…avoid or minimise the effect of discontinuities, abrupt changes in section…" |

This is structurally identical to RCD Annex I A 3.1 "strong enough in all
respects" (`EU-REGULATORY.md` §2.4) — **the same boundary, reached from a
different legal system.** Two independent regulators state the structural
requirement and neither quantifies it. That is a convergent result, not a
coincidence: both defer to standards.

### 1.3 Table 1 — WHICH standard is permitted, by length and by duty. READ, transcribed verbatim

Cl. 3.1: "Vessels of **35 m or more** in measured length shall be classed."
Cl. 3.2.2 and **Table 1** (p. 11) for everything under 35 m not in class:

| measured length | Robust operations | Light operations |
|---|---|---|
| < 35 m and > 13 m | Lloyd's Rules (cl. 3.3) · USL Code Subsection 5M | Lloyd's Rules (cl. 3.3) |
| < 13 m and > 7.5 m | Lloyd's Rules (cl. 3.3) · USL Code Subsection 5M | Lloyd's Rules (cl. 3.3) · **ISO 12215 (cl. 3.4.4)** |
| < 7.5 m | Lloyd's Rules (cl. 3.3) · USL Code Subsection 5M | Lloyd's Rules (cl. 3.3) · **ISO 12215 (cl. 3.4.4)** · **AS 1799 (cl. 3.5)** |

**The two duty classes are DEFINED, and the definitions are usable.** Cl. 1.4:

> "**robust operations** — operations of a vessel that in normal circumstances
> may be exposed to loading arising from — a) heavy seas (for example all Class
> A and Class B vessels and seagoing patrol vessels); b) heavy loads from cargo,
> machinery, deck machinery or rigging …; c) heavy or frequent impacts (for
> example tugs, ferries, barges, tugs); d) frequent grounding (for example
> landing craft and large houseboats); or e) large accelerations and slamming
> (for example vessels used for skiing and wake boarding, thrill ride vessels,
> and dive vessels).
>
> **light operations** — operations of a vessel that are characterised by
> relatively light loading in normal circumstances, i.e., operations that are
> not robust operations."
>
> NOTE 1: "Light operations would be applicable to most hire and drive vessels
> (Class 4) and vessels intended primarily for sport and recreation."

**Consequence for this project, stated carefully.** ISO 12215 is an accepted
route *only* for **light operations** and *only* at **≤ 13 m**. A commercial
craft in robust operations at any length, or any craft over 13 m, must use
Lloyd's or USL 5M. Our SKU band is 5–15 m, so a 15 m commercial vessel is
outside the ISO route under Australian law even though it is inside ISO
12215-5's own 24 m scope.

### 1.4 Cl. 3.4.2 — a regulator explicitly extending a recreational standard to commercial craft. READ

This is the single most quotable paragraph in C3:

> "This standard allows for the application of specified standards in the ISO
> 12215 series to specified craft engaged in light operations, **notwithstanding
> that the Scope of these ISO standards limits their application to small boats
> used for recreational purposes only**, including craft equivalent to Class 4
> hire and drive. Except for the reference to non-commercial service, the
> specific ISO standard used shall be the one intended for application to a
> vessel of the specified type, size, design category and construction
> material."

Table 4 (pp. 13–14) then lists all nine parts of ISO 12215 with their applicable
ship types. Every row for Parts 1–9 reads "**13 m or less in measured length
engaged in light operations**" (Part 3 covers "Steel, aluminium, plywood and
composite FRP/wood craft"; Part 7 the multihull equivalent). Table 4's KEY:

> "At the time of development of this standard, Parts 5 and 6 of ISO 12215 were
> still in draft form. **Only the final published versions of Parts 5 and 6 of
> ISO 12215 are deemed-to-satisfy solutions for the standard, not the draft
> versions.**"

Note what is missing: **C3 cites the ISO parts UNDATED** (cl. 1.5 lists
"ISO 12215-5—Small craft - Hull construction and scantlings - Part 5: Design
pressures, design stresses, scantling determination" with no year). Contrast
`EU-REGULATORY.md` §3.1, where the RCD guide gives dated editions
(`EN ISO 12215-5:2019`). **No contradiction — different citation practice for
different legal purposes** (a harmonised-standard listing must be dated to fix
the presumption of conformity; a deemed-to-satisfy pointer need not be). Record
that C3 does NOT corroborate any edition year.

### 1.5 Table 5 — NSCV operational area ↔ ISO design category. READ, verbatim

This is a **binding regulator's own mapping** between an operational-area
regime and the ISO A/B/C/D categories, and it is free. p. 14–15:

| NSCV Operational Area | Equivalent ISO Design Category | Additional conditions |
|---|---|---|
| A | Nil | Not applicable |
| B | Nil | Not applicable |
| C | A: Ocean | None |
| C | B: Offshore | "Not to operate in wave heights greater than **4 m** significant, nor wind force exceeding **7 Beaufort**" |
| D | B: Offshore | None |
| D | C: Inshore | "Not to operate in wave heights greater than **2 m** significant, nor wind force exceeding **6 Beaufort**" |
| E | C: Inshore | None |
| E | D: Sheltered waters | "Except for sailing vessels, not to operate in wind force exceeding **4 Beaufort**" |

**Cross-check against `limits.CATEGORY_TABLE` and RCD Annex I A §1
(`EU-REGULATORY.md` §2.2): CONSISTENT, and independently so.** The RCD says
B ≤ 4 m / ≤ 8 Bft, C ≤ 2 m / ≤ 6 Bft, D ≤ 0,3 m / ≤ 4 Bft. AMSA's conditions
say 4 m and 7 Bft for B, 2 m and 6 Bft for C, 4 Bft for D. **The wave heights
match exactly; the WIND for category B does not (7 Bft here, 8 Bft in the
RCD).** AMSA's is the more restrictive, and it is stated as an *additional
condition on a downgrade*, not as a definition of category B — so this is
AMSA tightening, not a contradiction of the RCD. Do not read AMSA's "7" as
evidence that the RCD's "8" is wrong.

**Also note: NSCV Operational Areas A and B map to NO ISO category at all.**
The regulator's position is that the ISO design categories do not reach
unrestricted / 200-nm operation. That is a free, citable statement of ISO
12215's upper bound of applicability.

### 1.6 What C3 hands off to — and what is still to be read

Cl. 1.5 (Referenced documents) and Tables 2, 6, 7, 8. The free ones:

- **USL Code Section 5 Subsection 5M "Construction—Wood"** — cited as a
  deemed-to-satisfy solution for ALL length bands under 35 m in robust
  operations. Table 7 adds "USL Code Subsection 5M → Subsection 5M Part 1" for
  materials. **This is the most likely home of free Australian plywood/timber
  scantling numbers.** NOT YET READ. C3's foreword says C3 "replaces Section
  5A, 5B, 5G, 5H, 5K, 5L of the USL Code. It also replaces the elements of
  Section 5M that cover vessels built from **plywood**" — ⚠ **so the PLYWOOD
  part of 5M may be the part C3 superseded**, leaving 5M live only for planked
  timber. Verify before relying on it.
- **AS 1799.4 (Reinforced plastics) and AS 1799.5 (Aluminium)**, Small pleasure
  boats code — deemed-to-satisfy for ≤ 7.5 m light operations. These are
  **Standards Australia** documents, i.e. PAID, not free. Table 1's KEY says
  "It is anticipated that the various Parts of AS 1799 will be revised, in due
  course." **AS 1799.1 (design/construction, plywood) is not referenced by C3
  at all** — only .4 and .5.
- Material standards, all Standards Australia and all PAID: AS/NZS 3678,
  AS/NZS 3679.1 (steel); AS/NZS 1734, AS/NZS 1866 (aluminium); AS 3572.7 (FRP
  resin extension-to-failure test); AS 1720.1 (Timber structures — design
  methods) and AS 5604 (natural durability) for wood; **AS/NZS 2272 (Plywood —
  Marine)** for plywood. AS/NZS 2272 is the Australasian analogue of BS 1088.
- Lloyd's Register rules (Table 2) — classification society, another agent's
  domain; noted here only because C3 makes them the *primary* Australian route.
- **Annex B** ("Type and size of welds for various structural connections for
  aluminium alloys and steel") and **Annex C** ("Minimum mechanical properties
  for non-welded and welded aluminium alloys") — free numeric tables in C3
  itself, pp. 20–21, NOT YET READ. Aluminium is not in this project's material
  set (plywood / FRP / carbon / foam sandwich), so these are low priority.

**NOT FOUND in NSCV C3: any design pressure, panel thickness, section modulus,
allowable stress, curvature factor, aspect-ratio factor, core shear, skin
wrinkling, or minimum-skin rule.** For plywood, FRP, carbon or sandwich alike.

---

## 2 · AUSTRALIA — USL Code Section 5 Subsection 5M "Construction — Timber"

### 2.0 THIS IS THE FIND. Free, government-published, closed-form PLYWOOD SCANTLINGS

**USL Code 2008, Section 5M, Part 4 — "Scantlings for hard chine plywood hulls
constructed on a system of longitudinal frames supported by web frames"** —
gives a complete plywood panel-thickness rule set: an explicit design-pressure
floor, bottom/side/deck/transom thickness formulas, an aspect-ratio factor, a
frame-breadth factor, an absolute minimum, and a published table of allowable
working stresses with a rule for scaling to a different timber. **Every formula
below was READ off the page image and transcribed.**

This is the *only* free source found so far in any jurisdiction that gives a
closed-form panel thickness for a boatbuilding material this project actually
uses.

### 2.1 Document identity, status and the tooling problem — READ

- URL: `https://www.amsa.gov.au/sites/default/files/2023-11/usl_code_5m_2008.pdf`
  (**hosted by AMSA**; 68 pages; local copy
  `downloads/standards/national/usl_5m_2008.pdf`, gitignored).
- Cover page: "**Uniform Shipping Laws Code 2008 — Section 5M: Construction —
  Timber (CTH, NSW, NT, QLD, SA, TAS, VIC & WA)**".
- ⚠ **The cover carries a disclaimer, and it must travel with every number
  quoted from this document:** *"This is not the official version of the
  Uniform Shipping Laws Code. The official version is that last published by
  the Australian Government Publishing Service, Canberra, copies of which can
  be obtained from the National Marine Safety Committee."* AMSA hosts it; AMSA
  does not warrant it as the official text.
- ⚠ **TOOLING: this PDF IS A SCAN with NO TEXT LAYER.** `pypdf.extract_text()`
  returns the empty string for all 68 pages, so a grep-based search concludes
  the document is empty. It is not. Each page carries one full-page TIFF
  (2496×3520, 1-bit). They were extracted with `pypdf` `page.images` and
  converted to PNG with Pillow (`downloads/standards/national/usl5m_png/pNN.png`)
  and then read as images. **A future session that greps this file and finds
  nothing has been defeated by the scan, not by the content.** Same failure mode
  as the raster Annex ZA tables in `EU-REGULATORY.md` §3.
- A third-party copy of the **2010** edition exists
  (`storerboatplans.com/wp/wp-content/uploads/2017/02/USL-Wooden-hybrid-code-2010.pdf`,
  59 pages) and is likewise a scan behind a text cover page. **NOT COMPARED
  clause by clause against the 2008 AMSA copy.** Nothing below is sourced from
  it.

**VESSEL SCOPE — READ.** Cl. M.2: *"This Sub-section is to apply to timber
vessels of **less than 35 metres in length**. Vessels of 35 metres in length and
over will be specially considered by the Authority."* Commercial vessels
(Australian domestic). Cl. M.3.1: *"these requirements apply to vessels
constructed of timber and framed with bent or web frames."* Part 4 specifically
is **hard chine, plywood-skinned, longitudinally framed with web frames**.

**⚠ A LIVE CONTRADICTION between the two Australian documents, and it is not
resolved here.** NSCV C3 Ed 1.3 Table 1 lists "USL Code Subsection 5M" as a
deemed-to-satisfy solution at every length band under 35 m in robust
operations — but C3's own FOREWORD (p. 3) says C3 *"also replaces the elements
of Section 5M that cover **vessels built from plywood**."* Part 4 of 5M is
exactly and only the plywood part. **So on C3's own account the formulas below
may be the part of 5M that C3 superseded**, while C3's operative table
re-adopts 5M without carve-out. Two clauses of one instrument disagree.
UNRESOLVED — do not present USL 5M Part 4 as a currently-live Australian
compliance route without settling this with AMSA. Its value to this project is
as a **published, government-issued, physically-reasoned plywood rule set**,
not as a certificate.

### 2.2 Sub-section structure — READ (p. 2 of print)

Part 1 Application and general · Part 2 Scantlings for round bilge vessels ·
Part 3 Scantlings for hard chine vessels · **Part 4 Scantlings for hard chine
plywood hulls** · Part 5 Scantlings for vessels of sawn frame construction ·
Part 6 Tables · Part 7 Sketches.

Parts 2, 3 and 5 are **TABULATED** scantlings (Tables M.1–M.26), keyed to
measured length and read off, not computed — e.g. cl. M.29.1 "The minimum
scantlings for chines shall be determined from Table M.21". Part 4 is the only
part that is FORMULA-based. Parts 2/3/5 are for planked timber, which is not in
this project's material set; they are NOT transcribed here.

Two general rules from Part 1 that condition everything (READ, p. 3):

- Cl. M.3.1(e): *"Sizes, except where specially noted, are for **Australian
  hardwoods of 960 kg/m³ density at 12% moisture content**. Where the actual
  density of the timber used is less than 800 kg/m³ density at 12% moisture
  content the tabulated scantlings are to be increased by the ratio* **960/W**"
  where *W* is the actual density in kg/m³ at 12% MC, taken from **AS 1738-1975
  Timber for Marine Craft**. Note the DEAD BAND: the correction is triggered
  below 800 but referenced to 960, so a 850 kg/m³ timber gets no increase at
  all. That is what the text says; it is not a transcription slip.
- Cl. M.3.2 "Alternate Construction Methods": *"The scantlings of vessels
  constructed on other than the framing systems described herein shall be
  determined on the basis of the **midship section modulus** being considered
  equivalent to the midship section modulus of a vessel of similar dimensions
  obtained from the application of this Sub-section, and also that the stresses
  in the individual members of the vessel are acceptable to the Authority."*
  **This is a free, explicit equivalence route** — the same posture as RSG
  Comment n.7 in the RCD guide (`EU-REGULATORY.md` §3.4), and it names the
  measurand (midship section modulus).
- Cl. M.3.1(c): *"Marine plywoods used shall conform to **Australian Standard
  AS2272-1979, Plywood for Marine Craft**."* Cl. M.3.1(d): glues *"gap-filling
  resorcinol or phenolic type such as those complying with **BS 1204** …
  epoxy resins or other equivalent adhesive … which can give a **Type WBP
  bond**"*, with modified urea-formaldehydes permitted only in internal
  structure not continuously wet. **This is the free answer to the "approved
  grades" question for plywood: AS 2272 + WBP-bonded glue.** (BS 1088 is not
  named by this code; AS 2272 is its Australasian counterpart.)

### 2.3 Part 4 symbols and units — READ VERBATIM (cl. M.40.1, print p. 17)

| symbol | meaning | unit |
|---|---|---|
| B | maximum beam | m |
| D | depth moulded | m |
| h | height to deck edge from (i) mid span of the stiffener/frame, for stiffener or frame scantlings; (ii) the middle of the panel between effective stiffeners, for panel thickness; (iii) the centre of the longitudinal, for longitudinal scantlings | mm |
| **L** | **water line length** | **m** |
| e | length of span of frames, stiffeners or beams | mm |
| **P** | **bottom pressure: determined from Part II Displacement Hulls, or Part III Planing Hulls, of Design Loadings Sub-section, as appropriate** | **kPa** |
| **S** | **spacing of stiffeners, frames, beams or floors, measured centre to centre** | **mm** |
| t | thickness of panels | mm |
| **V** | **maximum speed** | **knots** |
| Z | modulus of section | mm³ |

Note **L is the WATERLINE length**, not measured length and not hull length.
That matters: NSCV/USL scope tests are on *measured length* while these
formulas take *L_WL*. Two different lengths in one document family.

### 2.4 ALLOWABLE STRESSES — cl. M.41 "Basis for scantlings". READ VERBATIM (print p. 18)

| | Plywood (MPa) | Timber (MPa) |
|---|---|---|
| Working stress (bending) | **14.0** | **14.0** |
| Working stress (tensile) | **11.0** | **11.0** |
| Modulus of elasticity | **12 500** | **12 500** |

**Answering the brief's question 3 directly: this code gives an ABSOLUTE
allowable stress in MPa, NOT a fraction of ultimate.** There is no σ_uf and no
safety factor in the text — the 14.0 MPa is handed over as the design working
stress, full stop. And **plywood and timber are given the SAME three numbers.**

Cl. M.41.2 — the rule for a better material, READ VERBATIM:

> "Where the plywood or timber has a greater bending strength than that given in
> sub-clause M.41.1, the thickness of plywood may be obtained from the formula:
>
> **t₂ = t_c · √( 14 / permissible working stress )**
>
> where t_c = thickness calculated in accordance with this Part, t₂ = required
> thickness. and the modulus of section of frames and stringers from the
> formula:
>
> **Z₂ = Z_c · ( 14 / permissible working strength )**
>
> where Z_c = modulus calculated in accordance with this Part, Z₂ = required
> modulus. The permissible working stress is to be taken from **Australian
> Standard 1720-1975, Rules for Use of Timber in Structures (SAA Timber
> Engineering Code)**."

**Read the exponents: thickness scales as the INVERSE SQUARE ROOT of allowable
stress, section modulus as the INVERSE FIRST POWER.** Both are exactly what
bending theory gives (σ = M/Z, and for a plate Z ∝ t²), which is a good sign
that the constants below are a real strength derivation and not a table of
custom. **The 14 in these two formulas is the same 14.0 MPa as in the M.41.1
table** — the one-number-one-place rule applies if this is ever implemented:
14.0 must be a single named constant feeding both M.41.1 and M.41.2.

⚠ The M.41.2 substitution is written for materials **stronger** than the base.
It is not stated whether it may be run in the weakening direction (permissible
< 14), which would *increase* t. Physically it should; the text says "greater".

### 2.5 DESIGN PRESSURE — cl. M.42.1. READ, and it is a FLOOR, not a full formula

> "**M.42.1.1** Bottom pressure is to be determined from Part II Displacement
> Hulls, or Part III Planing Hulls of the **Design Loadings Sub-section**, as
> appropriate.
> **M.42.1.2** Bottom pressure in any case should not be less than
> **3(L + 6) kPa**.
> **M.42.1.3** Where the rise of floor is less than 12°, the bottom pressure
> will be specially considered."

**So 5M does NOT itself contain the design-pressure formula** — it defers to a
*Design Loadings* sub-section of the USL Code, which is a DIFFERENT free AMSA
document. NOT YET READ; identifying and reading it is the highest-value
remaining Australian task, because that is where a length/speed/displacement-
scaled pressure would live.

What 5M does give free is a **pressure floor that scales linearly with
waterline length**: P_min = 3(L + 6) kPa, L in m. Worked, for orientation only:
L = 5 m → 33 kPa; L = 10 m → 48 kPa; L = 15 m → 63 kPa. And a **deadrise
threshold at 12°** below which the pressure is not covered by the rule at all.

### 2.6 BOTTOM PANEL THICKNESS — cl. M.42.2. READ VERBATIM (print p. 18)

> "**M.42.2.1** The thickness of plywood from hog to chine is not to be less
> than **the greater of**:
>
> **t = 0.018 f (125 + P) · S/100**
>
> **t = 0.021 (160 + 50L + 6V)**
>
> Where f = f₁ f₂ and f₁ and f₂ are defined in paragraphs M.42.2.2 and M.42.2.3
> respectively"

with t in mm, P in kPa, S in mm, L in m (L_WL), V in knots.

**Aspect-ratio factor, cl. M.42.2.2, READ VERBATIM:**

> "To correct for aspect ratio, where the aspect ratio of an unstiffened panel
> a/b (where a = length of longer side and b = length of shorter side) is **less
> than 2**, the calculated thickness may be multiplied by the factor f₁, where:
>
> **f₁ = 0.6 + 0.2 (a/b)**"

Self-consistent: at a/b = 2 it returns 1.00, so the base formula is written for
a long (2:1 or greater) panel and f₁ *reduces* thickness on squarer panels, down
to 0.80 at a/b = 1. **No upper branch is given for a/b > 2** — the factor is
simply not applied, i.e. f₁ = 1.

**Frame-breadth factor, cl. M.42.2.3, READ VERBATIM (print p. 19):**

> "To correct for breadth of frame, where the frame has a breadth K as shown
> below greater than K = 0.05S, the calculated thickness may be multiplied by
> the factor f₂, where:
>
> **f₂ = 1.1 − 2 (K/S)**
>
> In no case should f₂ be taken as less than **0.7**."

Also self-consistent: at K = 0.05S it returns 1.00, and it floors at 0.7
(reached at K = 0.2S). This credits the reduced clear span when the frame is
wide — a term ISO 12215-5 handles differently, and it is free here.

**There is no curvature factor in Part 4.** Expected: Part 4 governs HARD CHINE
hulls, whose panels are developable and flat. **NOT FOUND, and correctly so —
do not go looking for a k_C analogue in this document.**

### 2.7 SIDE PANEL THICKNESS — cl. M.42.3. READ VERBATIM (print p. 19)

> "**M.42.3.1** The loading P, illustrated below, should be used to determine
> the thickness of the side plywood where P is the bottom pressure determined
> from paragraph M.42.1.1 or paragraph M.42.1.2 as appropriate.
> **M.42.3.2** The pressure to be used is that applicable at the **middle of the
> panel** being considered.
> **M.42.3.3** The thickness of plywood from chine to deck at side is not to be
> less than **the greater of**:
>
> **t = 0.013 f (100 + P_s) · S/100  mm**
>
> **t = 0.021 (160 + 50L)  mm**
>
> Where f = f₁ f₂ and f₁ and f₂ are as defined in paragraphs M.42.2.2 and
> M.42.2.3 respectively. **In no case shall the thickness be less than 6 mm.**"

The accompanying figure shows a **triangular side-pressure distribution: P_s = 0
at the deck edge, rising linearly to P_s = P at the chine**, evaluated at panel
mid-height. That is the whole side-pressure model, and it is free.

Compare the two skins at the same P and S: the side coefficient is 0.013 against
the bottom's 0.018 and the additive constant 100 against 125, so the side is
about 0.72× the bottom in the pressure term — **and the side's length-minimum
drops the 6V speed term entirely**, i.e. speed loads the bottom and not the side.

**t ≥ 6 mm absolute minimum for side plywood — READ.** This is the free answer
to "plywood thickness minima", and it is *lower* than the 15 mm ply this
project's own scantling rule once failed against (see `docs/LESSONS.md`);
different member, different code, do not conflate them.

### 2.8 TRANSOM and DECK — cl. M.42.4 / M.42.5. READ VERBATIM (print pp. 19–20)

**Transom carrying an outboard or stern drive (M.42.4.1.1):**

> "(a) outside the area of attachment … **t = 0.041 (160 + 50L)**
> (b) in way of the area of attachment … **t = 0.041 (160 + 50L) + a**"

with *a* from a table keyed to **total installed engine power**:

| total installed engine power (kW) | a (mm) |
|---|---|
| less than 30 | 20 |
| 30 and over but less than 60 | 25 |
| 60 and over but less than 100 | 30 |
| 100 and over but less than 135 | 35 |
| 135 and over but less than 165 | 45 |
| 165 and over | "to be specially considered" |

Note 0.041 is almost exactly **twice** the 0.021 of the side/bottom length
minima — the transom is two times the minimum skin, plus a power-keyed pad.
A transom NOT carrying an engine takes the side-ply rule (M.42.4.2.1 → M.42.3.3).

**Deck (M.42.5.2–M.42.5.4):**

> "M.42.5.2 The thickness of plywood in the deck of a vessel having length (L)
> **less than or equal to 15 metres** shall not be less than:
> **t = 0.036 S**
>
> M.42.5.3 … a vessel having length (L) **greater than 15 metres** shall not be
> less than:
> (a) where the deck is supported by **transverse beams**: **t = 0.001 (L + 33) S**
> (b) where the deck is supported by **longitudinals**: **t = 0.001 (L + 18) S**
>
> M.42.5.4 After applying corrections f₁ and f₂ where appropriate the thickness
> of plywood in the deck of a vessel having length (L) greater than 15 metres
> shall in no case be less than **t = 2.1 (0.2L + 3)**"

⚠ **TRANSCRIPTION CAUTION on M.42.5.3.** The scan renders the operator inside
the bracket ambiguously; it is read here as **+**. The reading is supported by
sense — with "÷" the results are ~100× too small — and by the neighbouring
formulas, all of which are (constant + term). But it is a **1-bit scan of a
1980s typescript and the glyph is not crisp**; re-verify against the official
AGPS text before encoding. Note also that at exactly L = 15 m the two branches
are **not continuous** (0.036 S vs 0.048 S), which is what the text says.

⚠ Note the deck rule for L ≤ 15 m has **NO pressure term at all** — it is
purely 0.036 × stiffener spacing. Our whole SKU band is ≤ 15 m, so this is the
branch that would apply, and it is the crudest formula in Part 4.

### 2.9 Part 4 clauses NOT YET READ

Cl. M.42.6 (compensation for openings > 150 mm dia.), M.42.7 (local
reinforcement; a percentage increase in bottom ply where rise of floor < 30° in
way of the propeller — the table itself is on print p. 21 and is NOT YET READ),
M.43 Hull stiffening, M.44 Sheer clamp, M.45 Chines, M.46 Beam shelf,
M.47 Stringers, M.48 Fitting of longitudinal members, M.49 Web frames,
M.50 Floors, M.51 Transom stiffeners, M.52 Deck beams, M.53 Pillars,
M.54 Engine seatings, **M.55 Plywood bulkheads**, M.56 Deckhouses.

**M.43 and M.47 are the ones that would carry the STIFFENER SECTION MODULUS
formula (the brief's question 2, second half). NOT YET READ.** M.41.2 already
tells us a Z is computed somewhere in this Part, so the formula exists.

---

## 3 · AUSTRALIA — USL Code Section 5G "Construction — Design Loading"

### 3.0 This is the free DESIGN PRESSURE standard, and it is a complete method

USL 5M cl. M.42.1.1 deferred the bottom pressure to "Part II Displacement Hulls,
or Part III Planing Hulls of the Design Loadings Sub-section". **That
sub-section is USL Section 5G, it is hosted free by AMSA, and it contains a
full closed-form planing-craft impact-pressure derivation plus a table of
displacement-hull design heads.** Together with 5M Part 4 it forms a complete
free pressure → thickness chain for a hard-chine plywood boat.

- URL: `https://www.amsa.gov.au/sites/default/files/2023-11/usl_code_5g_2008.pdf`
- **"Uniform Shipping Laws Code 2008 — Section 5G: Construction — Design
  Loading (CTH, NSW, NT, QLD, SA, TAS, VIC & WA)"**, 10 pages.
- ⚠ **Also a pure SCAN with no text layer.** Same extraction route as 5M; PNGs
  at `downloads/standards/national/usl5g_png/`. Same "not the official version"
  disclaimer on the cover.
- Sibling sub-section **5B "Structural Strength"** (2 pages, HAS a text layer)
  is the enabling clause. Cl. B.1.2: *"A vessel constructed in accordance with
  the appropriate Rules of a Classification Society **or with the appropriate
  provisions of this Section** shall be accepted as complying"*; cl. B.1.7
  points at "Sub-section G, Design Loadings". **And cl. B.1.6 is a real
  operational-area scaling rule, READ VERBATIM:**

  > "For vessels of **Class E**, design heads and/or loadings used in the
  > determination of scantlings may, at the discretion of the Authority, be
  > **reduced by not more than 25%**; provided that, where special provision
  > exists in this section for scantlings or design loadings for Class E
  > vessels, then such reduction shall not apply."

  That is the only *general* operational-area load scaler in the Australian
  free corpus: a flat −25 % for the most sheltered class, at the regulator's
  discretion, and disapplied where a Class E number is already given.

**VESSEL SCOPE — READ.** Cl. G.2: *"Where scantlings for displacement vessels
are to be derived from **first principles**, then for displacement vessels
**less than 35 metres in length**, minimum loadings as determined below shall be
used in their determination. Vessels 35 metres in length and over will be
specially considered."* Cl. G.1 makes the whole sub-section the fallback route
*"[w]here a vessel is not designed and constructed in accordance with the Rules
of a classification society"*. Commercial vessels; Classes A–E are the USL
operational classes (A least sheltered → E most).

### 3.1 Part II, DISPLACEMENT HULLS — design heads and deck loads. READ VERBATIM

**Shell, cl. G.3 — the whole rule is one sentence:**

> "A head of salt water varying from **1.25 metres above the exposed deck at the
> bow** to **0.625 metres at the forward quarter point** and **constant at 0.625
> metres above the exposed deck aft to the transom** shall be used."

So the displacement-hull side/shell pressure is a *static head above deck*,
linearly tapering over the forward quarter and constant thereafter. No speed
term, no displacement term, no operational-area term. It is the crudest
possible longitudinal distribution and it is free.

**Decks, cl. G.4** — design loads in kg/m², written as (coefficient·L + constant)
× 1025 (the 1025 is the salt-water density, so each bracket is a HEAD IN METRES
and the product is a load in kg/m²). L is length in metres.

| location | Classes A, B or C | Classes D & E |
|---|---|---|
| exposed freeboard deck | (0.02 L + 0.76) × 1025 | (0.02 L + 0.46) × 1025 |
| forecastle deck / superstructure deck fwd of amidships 0.5 L | (0.02 L + 0.46) × 1025, **725 kg/m² minimum** | — |
| first deck above freeboard deck | — | (0.01 L + 0.46) × 1025 |
| freeboard deck within superstructure or deckhouse; any deck below freeboard deck between 0.25 L fwd of and 0.2 L aft of amidships | (0.01 L + 0.61) × 1025 | — |
| all other locations | (0.01 L + 0.3) × 1025 | (0.01 L + 0.3) × 1025 |

**This IS the free "how does design pressure scale with length and operational
area" answer for displacement hulls: linearly in L, and by a shift in the
CONSTANT (0.76 → 0.46 m of head) between the rougher classes A/B/C and the
sheltered D/E.** The slope is unchanged; only the offset moves. Worked, exposed
freeboard deck: L = 10 m → A/B/C 985 kg/m² (9.66 kPa) vs D/E 678 kg/m²
(6.65 kPa), a 31 % reduction. Compare that with cl. B.1.6's flat 25 % Class E
discretion — **two different sheltered-water reductions in the same Section**,
which is why B.1.6 disapplies itself where a specific number exists.

**Superstructures and deckhouses, cl. G.7** (kg/m²):

| | Classes A, B & C | Classes D & E |
|---|---|---|
| front ends | (0.0199 L + 0.51) × 1025 | (0.0199 L + 0.30) × 1025 |
| sides and after ends | (0.0159 L + 0.27) × 1025 | (0.0093 L + 0.19) × 1025 |

Note that here the sheltered classes get a shallower SLOPE as well (0.0093 vs
0.0159) on sides/after ends, unlike the deck rows. Front ends carry roughly
1.9× the sides at L = 10 m for classes A–C.

**Also READ:** cl. G.6 bulkheads — main sub-division bulkheads below main deck
resist *"a head to the main deck combined with the live and dead loads from the
deck(s) at the top of the bulkhead"*; structural non-tight bulkheads at the
first level below main deck *"a uniform load of **350 kilograms per square
metre** combined with the water and dead loads"*. Cl. G.4 tank tops: head =
**two-thirds** of the distance from tank top to overflow top, or to the bulkhead/
freeboard deck, whichever is greater; cargo mass reference **720 kg/m³**;
exposed cargo deck design loading **3750 kg/m²**, increased in proportion above
2636 kg/m². Cl. G.5 requires a longitudinal bending stress *"acting at the
extreme hull fibres tapering to zero at the neutral axis"*, tapering to zero at
the hull ends, superposed on all the above.

### 3.2 Part III, PLANING HULLS — the full impact-pressure method. READ VERBATIM

Cl. G.8.1 states its own provenance:

> "The design principles elaborated in this Part are based on those developed by
> **Heller and Jasper (Transactions of the Royal Institution of Naval Architects
> 1961, Volume 103, page 49)**."

**Basic assumptions, cl. G.9.1 — the acceleration model, and this is the load
scaling the brief asked for:**

> "(3) **rigid body accelerations varying linearly from 4.0 g at the bow to
> 0.0 g at the stern** with acceleration at the centre of gravity (assumed at
> Midships) of **2.0 g**, are applicable to **commercial planing craft**.
> (4) increased rigid body accelerations will be assumed for design of planing
> craft designed for more rigorous service than those of the conventional
> commercial planing craft (e.g. patrol craft, police launch, surveillance
> craft etc)."

plus: (1) single-degree-of-freedom idealisation; (5) peak pressure × dynamic
factor = an equivalent static "effective" pressure giving the same maximum
deformation and stress; (6) pressure distribution stationary, varying with time;
(7) hull rigid, vertical force components only.

**Symbols, cl. G.10 (verbatim, units as given):** P₀ maximum load per unit
length along hull (kg/m) · W mass of hull (kg) · L length of hull along
waterline (m) · a_CG acceleration of centre of gravity (m/s²) · g (m/s²) ·
**G half girth from keel to chine (m)** · p₀ peak pressure (Pa) · p_I maximum
effective pressure (Pa) · p equivalent static pressure (Pa) · P_h hydrostatic
pressure at rest (Pa) · **F_I impact factor** · **F_T transverse load
distribution factor** · **F_L longitudinal load distribution factor** · σ_y
yield stress (Pa) · w_m allowable permanent set (mm) · b shorter side of a panel
(mm) · a longer side (mm) · E modulus (Pa) · h thickness of plate (mm) ·
w uniformly distributed load on a frame (N/m²) · a_B, a_S acceleration at bow /
stern (m/s²) · σ₁ σ₂ σ₃ primary/secondary/tertiary stress (Pa) · P₂ effective
pressure at the maximum force condition (Pa) · K coefficient depending on
boundary conditions, aspect ratio and point of measurement of stress.

**The chain, cl. G.11.1 → G.11.4, READ VERBATIM:**

> "**G.11.1** Maximum load per unit length along the hull
>   **P₀ = (3W / 2L) · (1 + a_CG/g)**
>
> **G.11.2** Peak pressure for application to local strength of a structural
> element
>   **p₀ = 3 P₀ g / G**
>
> **G.11.3** Maximum effective pressure
>   **p_I = p₀ × dynamic load factor.**
>   The dynamic load factor may be taken as **1.1** where experimental or
>   full-scale values are not available.
>
> **G.11.4** The equivalent static pressure for the design of plating (or shell
> panel)
>   **p = (p_I × F_I × F_T) + P_h**
>   F_I is the impact factor expressed as a function of distance from the bow
>   and is determined from Figure 1. F_T is the transverse load distribution
>   factor and is determined from Figure 2."

⚠ **Symbol collision in the source, flagged not silently fixed.** G.11.2 is
typeset as `Po = 3Po g / G`. Per the G.10 symbol list, the left side must be
**p₀ (lower case, peak pressure, Pa)** and the right side **P₀ (upper case,
load per unit length, kg/m)** — the scan does not distinguish the cases. The
dimensional check settles it: (kg/m)·(m/s²)/(m) = kg/(m·s²) = Pa. ✔ Transcribed
above as p₀ and P₀ accordingly; **the source glyphs are identical and a reader
who takes them at face value gets a self-referential equation.**

**Longitudinal members use F_L, not F_T (cl. G.11.9):** *"Bottom longitudinals
are designed as fixed ended beams with span equal to the frame spacing. The
design pressure is determined from* **p_L = (p_I × F_I × F_L) + P_h** *… F_L
from Figure 5."*

**Combined-stress acceptance, cl. G.11.12–G.11.15 — the free "allowable stress"
rule for this method:**

> "**G.11.12** The bending moment amidships is determined from
> Bending moment (kilogram metres)
>   **= (W × L / 1920) · ( 160·a_CG/g − 41·a_B/g − 169·a_S/g − 50 )**
>
> **G.11.13** … Effective pressure **P₂ = P₀ g / G**; equivalent static pressure
> **p = (P₂ × F_I × F_L) + P_h**. Using this pressure, the uniformly distributed
> load, maximum bending moment **(p ℓ² / 12)** (at ends of longitudinals since
> they are regarded as fixed beams of length ℓ), modulus and secondary stress
> are determined.
>
> **G.11.14** The tertiary stress in the bottom plating is then calculated.
> **P₂ = P₀ g / G**; **p = (P₂ × F_I × F_T) + P_h**;
> **σ₃ = 5.46 K p (b/h)²**
> For a plate of aspect ratio 4 clamped on all four edges, to determine the
> longitudinal stress at the midpoint of short side **K = 0.0627**.
>
> **G.11.15** The sum of the three stresses is compared with the yield stress
> **σ₁ + σ₂ + σ₃ < σ_y**
> If the sum is less than the yield stress the overall strength of the craft is
> satisfactory."

**Answering the brief's question 3 for this method: the allowable is the YIELD
STRESS, with a safety factor of exactly 1.0 and no material-dependent knockdown
— but applied to the SUM of primary (hull girder) + secondary (longitudinal
bending) + tertiary (plate bending) stress.** That is a different and stricter
bookkeeping than a single-member check at a fraction of ultimate. Note also
**P₂ = P₀·g/G, i.e. one third of the G.11.2 peak** — the "maximum force
condition" for global/secondary work is a third of the local peak.

**Frame scantlings, cl. G.11.6:** treat as a beam of span = half girth (pin
ended, if the frame is slotted over the longitudinals) or span = longitudinal
spacing (fixed ended, if bracketed); *"a strip of plating of width **2h·√(E/σ_y)
mm** or the spacing of adjacent transverses whichever is less should be taken as
the bottom flange"*; **w = p × spacing**, **maximum bending moment = w(zG)²/8**.
Cl. G.11.8: side framing uses *"a **mean** of the design pressure for the deck
and bottom framing"*.

**Metal plate thickness, cl. G.11.5**, is chart-based (Figure 3) on four
non-dimensional groups: yield stress σ_y (heat-affected value if welded);
allowable-permanent-set ratio **w_m/b, "A ratio of 0.005 should normally be
adopted"**; permanent-set coefficient **(w_m/b)·√(E/σ_y)**; width-to-thickness
coefficient **(b/h)·√(σ_y/E)**; non-dimensional pressure coefficient
**pE/σ_y²**. Figure 3 plots pE/σ_y² against (b/h)√(σ_y/E) for permanent-set
coefficient 0, 0.1 and 0.2. ⚠ **Chart, not formula — and it is written for
METAL (σ_y). It does not reach plywood, FRP, carbon or sandwich.** Figure 4
adjusts aluminium thickness.

### 3.3 Figures 1 and 2 — DIGITIZED FROM THE CHART, marked as such

⚠ **The following are read off a 1-bit scan of a plotted curve, NOT from text.
They are the least reliable numbers in this file.** Do not encode them without
re-reading the official text. Recorded because F_I and F_T are otherwise dead
ends and the SHAPE is unambiguous even where the values are not.

**Figure 1 — impact factor F_I vs "percentage of length from bow"** (axis runs
100 at the left to 0 — i.e. 0 % is the BOW). Piecewise linear, three segments:

- ≈0.25 at 100 % from bow (transom), rising linearly
- reaching **1.0 at ≈50 %** from bow
- **flat at 1.0** from ≈50 % to ≈22 % from bow
- falling to **≈0.5 at 0 %** (the bow itself)

So the peak local impact factor sits between midships and the forward quarter,
NOT at the stem, and the stem is at half the peak. That is a real, and
counter-intuitive, free finding about longitudinal pressure distribution on a
planing hull — and it is the opposite sense to the displacement-hull head in
cl. G.3, which is HIGHEST at the bow. **Two hull types, two opposite
longitudinal distributions, in one document.**

**Figure 2 — transverse load distribution factor F_T vs "percentage of
unsupported half girth"** (F_T axis 1.0 at the left to 0 at the right; girth
axis 0 at bottom to 100 at top). F_T = 1.0 at ≈10 % of the half girth and falls
monotonically to roughly **0.7–0.75 at 100 %**, with most of the fall in the
upper half of the girth. Values between are a smooth concave curve. **Endpoint
values approximate to ±0.05; the 100 % end is the least legible.**

Figure 5 (F_L, longitudinal load distribution factor) is on a page NOT YET READ.

### 3.4 What USL 5G does NOT contain — NOT FOUND

- **No FRP, plywood, carbon or sandwich material properties**, and no allowable
  stress other than σ_y for metals. The plate-thickness chart is metal-only.
- **No core shear, skin wrinkling, minimum skin or core density rule anywhere.**
- **No curvature factor and no aspect-ratio factor as a multiplier**; aspect
  ratio enters only through K in σ₃ = 5.46 K p (b/h)², and only one value of K
  is given (0.0627, aspect ratio 4, clamped, longitudinal stress at the midpoint
  of the short side). **A K table is not printed** — one value, for one
  configuration. That is a serious practical gap: the σ₃ formula is unusable at
  any other aspect ratio without a plate-theory table from elsewhere.
- **No design-category / wave-height keying.** Load varies by USL vessel Class
  (A–E) only through the deck and superstructure constants of §3.1 and the
  cl. B.1.6 −25 % discretion.

### 3.5 USL Section 5K — FRP. NOT A SOURCE, and this is worth recording

`usl_code_5k_2008.pdf` (4 pages, text layer). Cl. K.2.1, READ VERBATIM:

> "Subject to K.2.2 and K.2.4, the detailed requirements of this Sub-Section
> shall be those of **Australian Standard AS.4132 Part 3 "Boat and Ship Design
> and Construction – Fibre-Reinforced Plastics Construction"** which shall be
> met to the satisfaction of the Authority."

with cl. K.2.2 upgrading every "should" in AS 4132.3 to "shall". **AS 4132.3 is
a Standards Australia document and is PAID.** So the free Australian corpus has
NO FRP scantling numbers at all — the FRP sub-section is a one-page pointer to a
priced standard, exactly as C3 is. **Plywood is the ONLY boatbuilding material
in this project's set for which Australia publishes free numbers.**

Cl. K.1.4–K.1.6 do give free *survey* thresholds worth noting: a certificate of
survey issues for an FRP vessel **6 m and over** only on survey per Appendix III
or IV to Section 14; **under 6 m** on lay-up drawings + a manufacturer's
affidavit + a surveyor's report; and for a **production series 6–10 m**, on the
prototype and *"at least every sixth vessel"* being surveyed with thickness
gauging after demoulding, plus an AS/NZS ISO 9000 QA scheme.

Sections 5H (Aluminium) and 5I (Copper Nickel) are similarly 2- and 5-page
pointers. **5J (Ferro-Cement, 45 pp) and 5L (Steel, 42 pp) are full documents
with text layers** — not this project's materials, NOT READ.

---

## 4 · AUSTRALIA — NSCV Part C Section 6 Subsection 6A "Intact stability requirements"

### 4.0 The second big find: a complete free stability code, with numbers

Where C3 handed the scantlings problem to somebody else, **C6A does the whole
stability job itself.** 112 pages, full numeric criteria, heeling-moment
formulas for persons / wind / turn, a freeboard-based simplified route with an
explicit downflooding margin, and a physical offset-load ("stability proof")
test. **This is the closest free substitute for ISO 12217 found anywhere in
this survey.**

- URL: `https://www.amsa.gov.au/sites/default/files/2024-10/nscv-c6a-ed-1.4-20241001.pdf`
  (**Edition 1.4**, "prepared … to incorporate the NSCV Omnibus amendments
  instrument No.1, 2024 … approved by the National Marine Safety Regulator on
  17 January 2024 and adopted by the Infrastructure and Transport Ministers on
  21 June 2024. **This edition 1.4 commences on 1 October 2024**." 112 pages,
  **text layer intact**, extracted with `pypdf`.)
- **Same CC-BY 4.0 licence as C3** (p. 2), with a prescribed attribution string.
  Quotable and transcribable into code.
- Cl. 1.6 names one external source: **"IMO Resolution A.749(18) Code on Intact
  Stability … as amended by Resolution MSC.75(69)"**, plus AS 1799 Part 1.
  The Chapter 5A numbers below are recognisably the IMO A.749 general criteria
  in metre-degrees, so their provenance is an IMO instrument, which is itself
  free.

**VESSEL SCOPE.** Cl. 1.1–1.2: intact stability for **all NSCV commercial
vessels** other than Part F Special Vessels. Read with Part C Subsection 6B
(buoyancy and stability after flooding) and 6C (stability tests and information).
Vessel classes: **Class 1 = passenger, Class 2 = non-passenger, Class 3 =
fishing**; operational areas A (least sheltered) to E (most).

### 4.1 THE COMPREHENSIVE CRITERIA — Chapter 5A, Table 10. READ VERBATIM

Applicable to **all vessels, all operational areas A–E**.

| No | applies to | criterion |
|---|---|---|
| 5A.1 | all | "The angle of maximum righting lever θ_max shall occur at an angle of heel **not less than 15 degrees**." |
| 5A.2a | θ_max occurs at 15° | area under GZ curve to 15° ≥ **4.01 metre-degrees** |
| 5A.2b | θ_max between 15° and 30° | area to θ_max ≥ **3.15 + 0.057 (30 − θ_max)** m·deg |
| 5A.2c | θ_max ≥ 30° | area to 30° ≥ **3.15 metre-degrees** |
| 5A.3 | all | area to 40°, **or to the angle of flooding θ_f if less than 40°**, ≥ **5.16 metre-degrees** |
| 5A.4 | all | area between 30° and 40° (or 30° and θ_f) ≥ **1.72 metre-degrees** |
| 5A.5 | all | **GZ ≥ 0.2 m at a heel angle ≥ 30°** |
| **5A.6a** | **Class 1, passenger vessels** | **GM₀ ≥ 0.15 m** |
| **5A.6b** | **Class 2, non-passenger vessels** | **GM₀ ≥ 0.20 m** |
| **5A.6c** | **Class 3, fishing vessels** | **GM₀ ≥ 0.35 m** |
| 5A.7a | all (except as modified by 5A.7b) | heel θ_h ≤ **θ_s** (Table 4) under **any single** heeling moment from person crowding, wind or turn |
| 5A.7b | all area A vessels, and area B vessels ≥ 24 m | apply the **severe wind and rolling (weather) criteria of Annex H** instead of the wind criterion |
| 5A.8 | vessels carrying **≥ 50 passengers** | heel θ_h ≤ **θ_c** (Table 4) under the **two greatest** heeling moments applied simultaneously |
| 5A.9 | θ_max < 25°, **or** (θ_s > 10° and single-moment heel > 10°) | residual area above the single heeling-lever curve up to 40° or θ_f ≥ A_RS |
| 5A.10 | ≥ 50 passengers where θ_c > 15° and combined heel > 15° | residual area above the combined heeling-lever curve ≥ A_RC |

⚠ **5A.9 and 5A.10 carry inline formula IMAGES that the text extractor
scrambles.** They extract as `fRS AA /400.2 1.03+ =` and
`fRC AA /400.13 0.65+ =`, i.e. **the coefficients are legible but their
ARRANGEMENT is not.** They are of the form
*A_RS = c₁ + c₂ · A_(40/θf)* — with digits 0.03, 1, 0.2 and 0.13, 0.65
respectively appearing — where A_(40/θf) is the total area under the GZ curve to
40° or θ_f. **NOT TRANSCRIBED AS FORMULAS. Do not reconstruct them from the
scrambled string.** Open pp. 35–36 of the PDF as images to read them.

**GM FLOORS — the answer to "can something free replace our R-GM?"** Three
values, and **their key is vessel USE (passenger / non-passenger / fishing), not
design category or wave height.** `EU-REGULATORY.md` §4.5 found ES-TRIN's only
GM floor (0.15 m) is a passenger-vessel figure and concluded R-GM stays ours.
**C6A's 0.15 m for Class 1 is the same number from a second, independent
regulator, and C6A additionally publishes 0.20 m for the NON-passenger case** —
which is the closer analogue for most of this project's SKUs. That is genuinely
new: a free, binding, government-published GM floor for a non-passenger
commercial vessel. It is still **not** keyed to a design category, so it does
not fill `limits.CATEGORY_TABLE`'s GM column row by row; it gives one floor for
one vessel class.

### 4.2 Table 4 — MAXIMUM ALLOWABLE ANGLES OF STATIC HEEL. READ VERBATIM (cl. 3.8)

The heel limits θ_s (single moment) and θ_c (combined) are not constants; they
are chosen by a **"heel consequence level"** determined by the vessel's fittings:

| consequence level | θ_s (deg) | θ_c (deg) | conditions of application (abridged, verbatim key phrases) |
|---|---|---|---|
| 1. High | **5** | **5** | "No specified conditions of application – applicable to any vessel that is unsuited to the application of large values of heel." |
| 2. Moderate | **10** | **15** | may exceed 5° where a slewing crane (if subject to lifting criteria) is safe to at least θ_s, and unsecured deck cargo is either rubber-tyred vehicles or has a shifting moment ≤ **20 %** of the greatest of M_P, M_W, M_T |
| 3. Low | **14** | **18** | may exceed 10°/15° where: all cargo incl. deck cargo secured against shifting; **seating provided for all persons**; furniture fixed; **sufficient grab rails** in spaces normally containing persons; decks arranged to reduce slipping hazards |

**This is a design-feature-to-allowable-heel ladder, and it is free.** It is a
different mechanism from ISO 12217's fixed offset-load heel limit: instead of
one angle, the regulator sells you a larger angle in exchange for named
arrangement provisions (seating, grab rails, secured cargo). That is directly
implementable as an arrangement-side constraint in `arrangement.py` terms — the
angle is a function of the fit-out, not only of the hull.

### 4.3 THE HEELING MOMENTS — Annexes A, B, C. READ VERBATIM, and all three are closed form

**Annex A — person crowding.** Cl. A5:

> **M_P = N · w · b · cos θ / 1000**  [tonne-metres]
>
> "N = for vessels **less than 6 m** in measured length, the number of persons
> on the vessel; = for vessels **6 m and more**, the number of PASSENGERS on the
> vessel. w = the mass per person in kilograms. b = the distance in metres from
> the vessel's centreline to the transverse centre of gravity of the persons
> when crowded. θ = the transverse angle of heel of the vessel in degrees."
>
> heeling lever **HZ_P = M_P / Δ = N·w·b·cos θ / (1000 Δ)**, Δ in tonnes.

**Table 40 — minimum assumed mass of persons. This is a directly citable free
number and it conflicts with nothing we hold, but it is not 75 kg and not
85 kg:**

| person type | min assumed mass (kg) | baggage allowance (kg) | extra diving equipment (kg) |
|---|---|---|---|
| passenger or crew, **day only** | **80** | nil | nil |
| passenger or crew, **overnight** | **80** | **15** | nil |
| diver, day only | 116 | nil | 17 |
| diver, overnight | 116 | 15 | 17 |

with NOTE 1: *"The mass of **80 kg** … represents a mean value for the
**Australian adult population as of 2005** including an allowance of **5 kg for
clothing and personal effects**."*

**Cross-reference — three different person masses now in this repository's
sources, all correctly distinct, and the distinction must be preserved:**
ISO 14946's **75 kg** is the *builder's-plate crew-limit basis*
(`EU-REGULATORY.md` §3.3); `limits.CREW_MASS_KG` is **85.0** and is used for the
*offset-load heel moment*; and AMSA's **80 kg (+15 overnight)** is the
*stability-criteria assumed mass*, with a stated population and year. **C6A's is
the only one of the three that says where its number comes from.** Note also
NSCV cl. 7.6.3.2(a) (Chapter 7D, boats < 7.5 m): *"a standard person mass of
**80 kg plus an allowance of 10 kg per person for ancillary equipment**"*, with
its own note that this *"differ[s] from the 75 kg per person and allowance for
15 kg per person specified in AS 1799.1"* — i.e. **90 kg total**, and the
regulator explicitly overriding the recreational standard upward. 90 kg is the
nearest free analogue to our 85.0.

**Geometry of the crowd, cl. A3.2–A3.3 (free, and directly usable by
`arrangement.py`):** VCG of a **standing** person = **1 m above the deck**; of a
**seated** person = **300 mm above the seat**. Crowd density **4 persons/m²**,
each occupying **625 mm × 400 mm**; divers **3/m²** at **625 mm × 533 mm**.
Cl. A4: on vessels ≥ 6 m only PASSENGERS move; under 6 m, everyone.

**Annex B — beam wind.** Cl. B4:

> **M_W = P_W · A_W · h · cos θ / (1000 g)**  [tonne-metres]
>
> "P_W = the applicable wind pressure … in Pascals from Table 41. A_W = the
> windage area of the vessel above the design waterline, in square metres.
> h = the vertical distance from the centre of area A_W to the centre of the
> lateral underwater area, in metres. **g = the acceleration due to gravity,
> 9.81 m/s²**."
>
> heeling lever **HZ_W = M_W / Δ**.

**Table 41 — wind pressure by operational area. THIS is the free
operational-area load scaling for stability:**

| operational area | gusting wind pressure (Pa) | gusting wind speed (kn) | equivalent average wind speed (kn) |
|---|---|---|---|
| **A & B** | **600** | 61 | 44 |
| **C** | **450** | 53 | 38 |
| **D** | **360** | 47 | 34 |
| **E** | **300** | 43 | 31 |

Read together with C3 Table 5 (§1.5 above), which maps NSCV area C→ISO A/B,
D→ISO B/C, E→ISO C/D, **this is a free bridge from the ISO design categories to
a numeric design wind pressure** — something neither the RCD nor ES-TRIN
supplies. Treat the bridge as a *reading of two tables together*, not as
something either document states. Note 44 kn average ≈ Beaufort 9 for area A/B,
consistent with "unrestricted".

Cl. B3.2 defines the windage area inclusively — *"all bulwarks, deck fittings,
masts, spars, deck cargo, safety equipment, seating, cranes, other fixtures …
awnings and screens"*, and portable side screens must be included. **For a
solar-electric craft the panel array is a fixture on this list.**

**Annex C — turning.** Cl. C3:

> **M_T = 0.0053 · V² · Δ · h · cos θ / L_WL**  [tonne-metres]
>
> "V = **the lesser value, in knots, of** (a) the maximum speed of the vessel,
> and (b) **4 √L_WL**. Δ = the vessel displacement, in tonnes. h = the vertical
> distance between the VCG and the centre of the projected lateral underwater
> area, in metres. L_WL = the waterline length in metres."
>
> heeling lever **HZ_T = M_T / Δ = 0.0053 V² h cos θ / L_WL**.

Note the speed cap **V ≤ 4√L_WL** knots — a Froude-number-like ceiling
(4√L_WL kn ≈ Fn 0.6 in these units) beyond which the turning moment is not
increased. **This is a complete free "heel in a turn" criterion**, one of the
brief's targets, and it is the same physical form as the classic IMO turning
moment.

### 4.4 THE SIMPLIFIED ROUTES — Chapter 7, and this is what a small craft actually uses

Cl. 7.1: simplified criteria *"may be substituted instead of the comprehensive
criteria"*, with the honest caveat (NOTE 3) that *"A failure of a vessel to be
able to apply or comply with simplified criteria does not necessarily mean that
the vessel would fail comprehensive criteria."*

**Table 25 — which simplified suite applies:**

| area | length limit | condition | suite |
|---|---|---|---|
| C | < 20 m | — | Ch. 7A or 7B |
| C | < 12 m | collared vessels | Ch. 7C |
| D, E | < 35 m | — | Ch. 7A or 7B |
| D, E | < 12 m | collared vessels | Ch. 7C |
| **D, E** | **< 7.5 m** | — | **Ch. 7D** |
| D, E | < 20 m | catamarans | Ch. 7E |
| D, E | < 50 m | dumb barges | Ch. 7F |

**Chapter 7A — a GM floor derived from the heeling moments (cl. 7.3.4,
Table 27), READ VERBATIM in substance:** GM₀ shall be not less than the largest
of

> **GM₀ = F_S · M_P / (Δ · tan θ_R)** , **F_S · M_W / (Δ · tan θ_R)** ,
> **F_S · M_T / (Δ · tan θ_R)**

where M_P, M_W, M_T are the upright (θ = 0) moments from Annexes A/B/C, Δ is
displacement in tonnes, F_S is the correction factor of cl. 7.3.5.5, and **θ_R
is the "maximum reliable angle of heel"**.

**θ_R, cl. 7.3.5.4 — this is C6A's downflooding/freeboard margin and it is the
direct free analogue of an ISO 12217 downflooding height.** θ_R is the LEAST of:

- a) the heel angle at **50 % of the freeboard to the deck edge** (θ_RF);
- b) the heel angle at **25 % of the freeboard to the first point of
  downflooding** (θ_RD);
- c) the heel angle at which **the chine emerges**, on a single-hard-chine
  vessel (θ_RC);
- d) **θ_s**, the maximum allowable single-moment heel from Table 4.

So the code never lets the working heel reach the deck edge or a downflooding
opening: it reserves **half** the deck-edge freeboard and **three quarters** of
the freeboard to the first downflooding point. Those two fractions are the
free, citable margins.

**F_S, cl. 7.3.5.5** = F_C · F_D, where F_C = max(L_CU/L_CH, 1) compensates
chine emergence and F_D = max(L_DU/L_DH, 1) compensates deck immersion (L_CU =
immersed chine length upright vs L_CH heeled to θ_R; L_DU = emerged deck length
upright vs L_DH heeled to **2 θ_R**). **"Chapter 7A criteria shall not be
applied to a vessel if either F_C or F_D exceeds 1.33."** Cl. 7.3.3.1 states the
underlying validity condition plainly: *"the deck edge does not immerse and the
chine does not emerge when the vessel is heeled to angles 2θ_R and θ_R
respectively"*, and warns *"The criteria are best suited to displacement vessels
of round bilge or deep chine hull form."*

**Minimum freeboard prerequisite (Table 26 for 7A, Table 29 for 7B, identical),
for vessels carrying passengers to sea in area C:**

| measured length L_m | minimum freeboard (mm) | alternative for all-diver passengers ≤ 5 nm |
|---|---|---|
| < 6 m | **150** | 150 |
| 6 m to 10 m | **150 + (L_m − 6) × 100 / 4** | 150 |
| > 10 m | **250** | 150 |

i.e. 150 mm up to 6 m, ramping linearly at **25 mm per metre** to 250 mm at
10 m, flat thereafter. **This is a free, closed-form minimum freeboard as a
function of length** — compare ES-TRIN Art. 4.02's 150 mm base freeboard
(`EU-REGULATORY.md` §4.1), which is the same starting value from a completely
different regime. Recorded as a coincidence of value, not as corroboration:
ES-TRIN's is an inland-vessel deck freeboard with a sheer credit, AMSA's is a
prerequisite for a simplified stability route on a seagoing passenger craft.

**Chapter 7B — the PHYSICAL OFFSET-LOAD TEST, and this is the free analogue of
the ISO 12217 offset-load criterion.** Cl. 7.4.1: a *"stability proof test
without the need to determine lightship particulars, loading conditions, KN data
and hydrostatic data."* Test conditions (cl. 7.4.4): normal trim and the most
unfavourable VCG likely in service; **non-return closures on freeing ports or
scuppers held OPEN** to allow water onto the cockpit or well deck; persons'
masses distributed for maximum VCG; on a vessel with an accessible deck above
the freeboard deck the upper-deck passenger mass is **increased by 33 %** and
the main-deck mass reduced by the same. Displacement (cl. 7.4.4.2): the worse of
a near-light condition with all persons aboard and tanks **25 %** full, and a
near-laden condition with tanks **75 %** full (both to create free surface).

Criteria (Table 30), all applied under **the most severe SINGLE** moment from
person crowding, wind or turning:

| No | hull type | criterion |
|---|---|---|
| 7B.1 | all | heel ≤ θ_s (Table 4) |
| 7B.2a | flush decked | inclined freeboard ≥ **50 %** of the minimum upright freeboard F_D to the deck |
| 7B.2b | well deck, area C | inclined freeboard ≥ **50 %** of the upright freeboard to the well deck |
| 7B.2c | well deck, areas D & E | (alternative) inclined freeboard ≥ **75 %** of the upright freeboard F_G to the top of the gunwale |
| 7B.2d | **cockpit vessel, area C** | inclined freeboard ≥ F_G − δ_f, where **δ_f < F_G (2L − 1.5 C) / 4L** |
| 7B.2e | **cockpit vessel, areas D & E** | as 7B.2d but **δ_f < F_G (2L − C) / 4L** |

with *"δ_f = the maximum allowable loss of freeboard, in metres; F_G = the
freeboard, in metres, measured from the waterline to the top of the gunwale when
the vessel is upright; L = the measured length of vessel in metres; C = the
length of cockpit in metres."*

**The cockpit formulas are the most interesting free result in C6A**: the
allowable loss of freeboard shrinks as the cockpit gets longer relative to the
hull, and the sheltered-water version (7B.2e) is more permissive by exactly the
1.5 factor on C. At C = 0 both reduce to δ_f < F_G/2 — the same 50 % as the
flush-deck rule. Fully implementable, and it prices a design feature (cockpit
length) directly into a stability margin.

**Chapter 7D — vessels < 7.5 m — IS A DEAD END for us.** Cl. 7.6.4: *"The vessel
shall comply with the stability criteria applicable to boats up to 7.5 m
operating in protected waters specified in **AS 1799.1**."* AS 1799.1 is a
Standards Australia document and is PAID. **So the one NSCV suite aimed squarely
at the smallest craft is the one that points at a priced standard.** Its free
content is the application envelope (< 7.5 m; areas D or E; ≤ 12 persons;
**enclosed buoyancy per Subsection 6B**; no accessible deck above the freeboard
deck) and the 80 + 10 kg person mass noted above.

### 4.5 Chapter 5B — free CATAMARAN stability criteria

Applicable to catamarans in operational areas B, C, D and E as an alternative to
Chapter 5A (cl. 5.5.1). Table 11, transcribed where the extractor was reliable:

- **5B.1**: the area A₁ under the GZ curve up to angle φ shall be at least
  **15.3 · (φ/30)** m·deg — ⚠ the extractor renders this as a scrambled inline
  image (`15. 31A` over `30`); the digits 15.3 and 30 are legible and the
  structure is a ratio, but **the formula is NOT SAFELY TRANSCRIBED. Read p. 37
  as an image before using it.** φ is defined as the LEAST of (1) the
  downflooding angle θ_f, (2) the angle θ_max at which maximum GZ occurs, and
  (3) **30 degrees** — that part is unambiguous.
- **5B.2**: θ_max shall occur at a heel **not less than 10 degrees** (vs 15° for
  monohulls under 5A.1 — the catamaran criterion is relaxed, as expected for a
  high-initial-stability form).
- **5B.3**: heel ≤ θ_s under any single moment (persons, wind, turn).
- **5B.4**: crowding **or** turning, whichever is greater, applied **in
  combination with** the wind heeling lever HZ₂; the resultant heel *"shall not
  be greater than **16 degrees**"*.
- **5B.5**: *"The effect of rolling in a seaway upon the vessel's stability shall
  be demonstrated mathematically"* — NOT YET READ beyond this sentence.

**A free catamaran stability criterion set is worth flagging separately**,
because `EU-REGULATORY.md` §3.1 records that **ISO 12215-7 (multihull
scantlings) is not in the harmonised list at all**. Stability and scantlings are
different questions, but the multihull SKU currently has neither, and this
supplies half of it for free.

### 4.6 What C6A does NOT give — NOT FOUND

- **No angle of vanishing stability (AVS) criterion.** Chapter 5A stops at 40°
  or the flooding angle. There is no "GZ shall remain positive to X degrees"
  clause of the ISO 12217 / RCD-category kind for a general vessel. (The sailing
  criteria in Chapter 6 and Annex J speak of a "range of stability of 90 degrees
  or more", but as a branch condition inside the SAILING criteria, not as a
  general requirement. Annexes J and K NOT YET READ.)
- **No design-category keying.** Every criterion keys off vessel USE class
  (1/2/3) and OPERATIONAL AREA (A–E). The only bridge to ISO A/B/C/D is C3
  Table 5, and that bridge is for scantlings.
- **No downflooding HEIGHT in metres.** C6A works in downflooding ANGLES and in
  fractions of freeboard (the 25 % / 50 % / 75 % of §4.4), never in a required
  height above the waterline. So it does not directly supply the quantity
  `iso12217.R-DFH` holds. It supplies a different, and arguably more physical,
  formulation of the same safety margin.
- **No offset-load heel LIMIT as a fixed angle.** The equivalent is θ_s from
  Table 4 (5 / 10 / 14 degrees by consequence level) plus the freeboard-loss
  criteria — again, a different formulation.
- Chapters 6 (special operations: sail, lifting, towing, trawling), 8
  (simplified criteria for special operations), Annexes D–H, J, K and the whole
  of Subsections 6B (damage/flooding) and 6C (stability tests, hydrostatics)
  are **NOT YET READ**. 6B is the buoyancy-and-flotation counterpart and is the
  obvious next target.

---

## 5 · UNITED KINGDOM — MCA Workboat Code Edition 3

### 5.0 Result: NO scantlings, but a full free stability and freeboard code

- URL: `https://assets.publishing.service.gov.uk/media/667c2220aec8650b10090087/Workboat_Code_Edition_3.pdf`
  349 pages, text layer intact.
- **Legal status: BINDING**, underpinned by **The Merchant Shipping (Small
  Workboats and Pilot Boats) Regulations 2023 (SI 2023/1216)**; the Code came
  into force **13 December 2023**. It supersedes the "Brown Code" and MGN 280
  for new vessels (the Code carries explicit transition clauses for vessels
  *"transitioning from the Brown Code or MGN 280"*, e.g. cl. 5.6.3.4, 12.1.1.2).
- **VESSEL SCOPE:** small workboats and pilot boats **under 24 m**, commercial,
  UK-flagged anywhere plus non-UK in UK waters. **MCA "area categories of
  operation" 0–6**, 0 being the least restricted.
- **NOT FOUND anywhere in 349 pages: the word "plywood" (0 hits), any design
  pressure formula, any panel thickness, any section modulus, any allowable
  stress.** "Scantling" occurs twice and neither is a rule (cl. 5.7.1 requires
  Offshore Energy Service Vessels to have *"scantlings equal to or greater than
  those typically required from a recognised Classification Society"*; the other
  is about fire-division scantlings).

### 5.1 Structural strength — cl. 5.2, and the ISO 12215-5 warning. READ VERBATIM

> "**5.2.1** All vessels certificated to operate in area category of operation
> **0, 1 or 2** shall be designed and built in accordance with the hull
> construction standards of a **Recognised Organisation or equivalent standard
> or to first principles**.
> **5.2.2** All vessels certificated to operate in area category of operation
> **3 – 6** shall be designed and built to a standard[14] approved by the
> Administration for their intended use or comply with higher standards listed
> in 5.2.1."

**Footnote 14, verbatim, and this is the most interesting single sentence the
UK contributes:**

> "**ISO 12215-5 should be used with caution where the vessel's hull or
> superstructure is fabricated of fibre reinforced plastic, or where the vessel
> is subject to impact loading from …**"

⚠ **The footnote is TRUNCATED in the text extraction at the page break** (p. 50
→ 51) and the continuation was not recovered. **The sentence as far as it goes
is verbatim; its ending is UNREAD.** Even truncated it is significant: a
national regulator publishing a caveat about the standard this project is being
asked to substitute for. **NSCV C3 accepts ISO 12215 flatly for light
operations ≤ 13 m; the MCA accepts it with a caution specifically about FRP and
impact loading.** That is not a contradiction of `EU-REGULATORY.md` (which says
nothing about 12215-5's technical adequacy) but it is a caution that belongs
beside any decision to buy or emulate 12215-5.

Cl. 5.3 lets a UK Load Line Assigning Authority's certificate of construction
stand in for the structural assessment, and cl. 5.3.2 ties any wind or
wave-height restriction on that certificate back to the area category.
Cl. 5.9.2.1 permits a RIB / buoyant-collar boat in area category 2 or 3 to be
built to **ISO 12215 and ISO 6185**, and cl. 5.9.2.2 accepts **RCR Design
Category A or B** (i.e. the RCD categories) for area category 3.

### 5.2 Person weight — 82.5 kg, stated three ways. READ VERBATIM (cl. 12.1.1.1)

> ".1 a person shall weigh a minimum of **82.5 kg**;
> .2 where a person weighs less than 82.5 kg, additional weight shall be carried
> so the total weight of person and weight is a minimum of 82.5 kg;
> .3 where a weight is used in lieu of a person, this shall weigh a minimum of
> 82.5 kg."

with cl. 12.1.1.2: existing vessels transitioning from MGN 280 or the Brown Code
may use **75 kg**. Cl. 13.1.2 repeats 82.5 kg for the freeboard calculation.
Police boats (Appendix, cl. 10.1.1) use **100 kg**.

**This is the fourth distinct person mass in this repository's sources.** For the
record, all four with their purpose:

| kg | source | purpose |
|---|---|---|
| 75 | ISO 14946 via RCD guide (`EU-REGULATORY.md` §3.3) | builder's-plate crew-limit basis |
| 75 | Transport Canada TP 1332 cl. 5.3.3.2(c) (§6 below) | emergency heeling condition |
| 80 (+15 overnight) | NSCV C6A Table 40 | stability criteria, Australian 2005 population |
| **82.5** | **MCA Workboat Code 3 cl. 12.1.1.1** | **all UK stability calculations** |
| 85.0 | `limits.CREW_MASS_KG` | our offset-load heel moment |
| 90 (80 + 10) | NSCV C6A cl. 7.6.3.2(a), boats < 7.5 m | stability proof test |
| 100 | MCA Workboat Code 3, police boats | stability assessment |

**`limits.CREW_MASS_KG = 85.0` sits inside this spread and is closest to the
MCA's 82.5.** No free source gives 85.0. If provenance is ever wanted for it,
82.5 kg from a binding UK code is the nearest attributable number — but that is
a *substitution*, not a confirmation, and it would change a result.

### 5.3 THE OFFSET-LOAD TEST — cl. 12A.2. READ VERBATIM, and it is the free ISO 12217 analogue

For vessels **not** required to have a Stability Information Booklet (i.e. not
in area category 0 or 1, fewer than 16 persons, cargo ≤ 1000 kg, no lifting
device, not a seagoing pilot boat — cl. 12.1.1.3):

> "**12A.2.1** A vessel shall be tested in the fully loaded condition(s) which
> shall correspond to the assigned freeboard. Testing shall ascertain the
> resulting angle of heel and position of the waterline **when the maximum
> number of persons the vessel is certificated to carry are assembled along one
> side of the vessel** (the helmsman may be assumed to be at the helm).
>
> **12A.2.2** A vessel shall be considered to have an acceptable standard of
> stability if:
> .1 the angle of heel **does not exceed 7º**; or
> .2 the angle of heel **does not exceed 10º** where it is not possible to
> comply with 12A.2.2.1, provided the freeboard in the heeled condition is in
> accordance with the requirements of Table 13.1.1.
>
> **12A.2.3** For decked vessels the freeboard to deck shall not be less than
> **75 mm** at any point."

**7° / 10° offset-load heel limits and a 75 mm residual freeboard, free and
binding.** This is a direct, quantitative substitute for the ISO 12217
offset-load criterion, and unlike ISO's it is a *physical test*, not a
calculation. (`iso12217.offset_load_heel_limit_deg(LH)` is a CUBIC in hull
length; the MCA's is two flat numbers with a freeboard side-condition. They are
not interchangeable and the difference should be stated if both are ever
implemented.)

**cl. 12A.2.4 — GM from the test, for vessels over 15 m. READ VERBATIM:**

> "**GM = 57.3 × HM / (θ × Δ)**
> where: HM = No. of persons × weight per person (kg) × distance from CL (m);
> θ = heel angle (degrees) obtained from the test defined in 12A.2.1 and
> 12A.2.2; Δ = full displacement including passengers, industrial personnel,
> crew, equipment and cargo (kg). Note: Weight of persons shall be taken in
> accordance with 12.1.1.1, and Cargo weight must not exceed 1,000 kg.
>
> **A vessel shall attain a value of initial GM not less than 0.5 m where
> displacement of the vessel is ESTIMATED, or 0.35 m where the displacement of
> the vessel is KNOWN and verified** by the Certifying Authority.
>
> Where displacement of the vessel is estimated:
> **Δ = C_B × LOA × Moulded Beam × Load Draught × 1.025**"

with footnote 25: *"In the case of doubt C_B of **0.9** can be used for pontoons
etc. or **0.67** for other vessels."*

**Two GM floors, and the gap between them is a KNOWLEDGE penalty, not a physics
one: 0.5 m if you estimated the displacement, 0.35 m if you measured it.** That
is an unusually explicit regulatory statement that uncertainty costs margin —
0.15 m of GM is the price of not weighing the boat. **For a project whose entire
honesty regime is `{value, tier, sigma}`, this is the single most philosophically
relevant clause found in the whole survey**: a binding code that prices
epistemic tier directly into a design bar.

### 5.4 Full GZ criteria — cl. 12B.3.8, and the multihull alternative 12B.3.9. READ VERBATIM

For vessels that DO need a Stability Information Booklet:

> "**12B.3.8** … .1 the area under the righting lever curve (GZ curve) shall be
> not less than **0.055 metre-radians up to 30 degrees** angle of heel and not
> less than **0.09 metre-radians up to 40 degrees**, or the angle of
> downflooding if this angle is less;
> .2 the area under the GZ curve **between 30 and 40 degrees** (or 30° and the
> downflooding angle) shall be not less than **0.03 metre-radians**;
> .3 **GZ shall be at least 0.20 metres at an angle of heel ≥ 30 degrees**;
> .4 the maximum GZ shall occur at an angle of heel of **not less than 25
> degrees**;
> .5 after correction for free surface effects the initial metacentric height
> **GM₀ shall not be less than 0.35 metres**."

**12B.3.9 — the broad-beam / multihull alternative, verbatim:**

> "Where a vessel with broad beam in relation to depth (such as a **catamaran or
> multihull**) does not meet the stability criteria given in section 12B.3.8, it
> shall meet the following criteria:
> .1 area under GZ **not less than 0.085 metre-radians up to θ_GZmax when
> θ_GZmax = 15º**, and **0.055 metre-radians up to θ_GZmax when
> θ_GZmax = 30º**. … When the maximum GZ occurs between θ = 15º and θ = 30º the
> required area under GZ up to θ_GZmax shall not be less than:
> **A = 0.055 + 0.002 (30º − θ_GZmax) metre-radians**;
> .2 area between 30º and 40º (or θ_f) **not less than 0.03 metre-radians**;
> .3 **GZ not less than 0.2 metre at 30º**;
> .4 the maximum GZ shall occur at an angle of **not less than 15º**;
> .5 **GM₀ not less than 0.35 metre**."

Note this is the same structure as NSCV C6A Table 10 (§4.1) in different units —
metre-radians here, metre-degrees there — because **both descend from the IMO
Intact Stability Code**. C6A cl. 1.6 names IMO A.749(18); MCA footnote 30 names
the **2008 IS Code (Resolution MSC.267(85))**. Sanity check of the two against
each other: MCA 0.055 m·rad = **3.15 m·deg**, exactly NSCV 5A.2c; MCA 0.09 m·rad
= **5.16 m·deg**, exactly NSCV 5A.3; MCA 0.03 m·rad = **1.72 m·deg**, exactly
NSCV 5A.4. **Three independent transcriptions agree to the digit, which is
strong evidence both were read correctly.** The two regimes differ only in
θ_max (MCA 25°, NSCV 15°) and in the GM floor (MCA 0.35 m for all booklet
vessels; NSCV 0.15 / 0.20 / 0.35 m by vessel class).

Also free, cl. 12B.3.11 — pontoon/barge alternative (C_B ≥ 0.9, B/D > 3):
area under GZ to θ_GZmax **≥ 0.08 m·rad**; static heel under a **uniformly
distributed wind load of 540 Pa (wind speed 30 m/s)**, lever from the windage
centroid to half the draught, **shall not exceed the angle corresponding to half
the freeboard**; **range of stability at least 20º**. That 540 Pa is a fourth
free wind pressure to set beside NSCV Table 41's 600/450/360/300 Pa.

**Damaged stability, Option 1, cl. 12B.1.2.1** (free, and the buoyancy analogue):
after minor hull damage or failure of any one hull fitting in one compartment —
angle of equilibrium **≤ 7°**; range to the downflooding angle **≥ 15° beyond
equilibrium**; maximum residual righting lever **≥ 100 mm**; area under the
curve **≥ 0.015 metre-radians**; and the vessel **shall not float at a waterline
less than 75 mm from the weather deck at any point**.

### 5.5 MINIMUM FREEBOARD — Table 13.1.2. READ VERBATIM, and it is closed form

Cl. 13.1.1: minimum freeboard may be met by **(a) complying with ISO 12217
Part 1** (with a declaration of conformity), **(b) Table 13.1.2**, or **(c) the
Merchant Shipping (Load Line) Regulations 1998 (SI 1998/2241)**. Applies to
vessels carrying ≤ 1000 kg of cargo; above that, Load Line Regs only (cl. 13.2).

| vessel LOA | continuous WT weather deck, **not** stepped/recessed/raised | continuous WT weather deck **which may be** stepped/recessed/raised | **open boats** (clear height of side, gunwale to water) |
|---|---|---|---|
| **< 7 m** | **300 mm** | **200 mm** | **400 mm** |
| ≥ 7 m and < 18 m | *"as determined by linear interpolation"* | (same) | (same) |
| **≥ 18 m** | **750 mm** | **400 mm** | **800 mm** |

Freeboard measured from the lowest point of the weather deck (or the lowest
point of the gunwale, for open boats) to the water surface, with the vessel in
sea water, upright, normal trim, fully loaded, persons at 82.5 kg (cl. 13.1.2).

**This is a free, fully specified, length-interpolated minimum freeboard rule**
and it is more demanding than the Australian one (§4.4: 150 mm under 6 m ramping
to 250 mm at 10 m). At 10 m LOA the MCA interpolation gives
300 + (750−300)·(10−7)/(18−7) = **423 mm** for an unstepped decked vessel,
against AMSA's 250 mm. **They are not comparable without care** — AMSA's is a
*prerequisite for a simplified stability route on a passenger vessel in area C*,
the MCA's is *the freeboard requirement itself*. Recorded as a factor-1.7
difference between two free national rules for the same nominal quantity, which
is itself a useful datum on how much such rules vary.

### 5.6 Table 12A.2.5 — MCA area category ↔ ISO 12217 design category. READ VERBATIM

Cl. 12A.2.5: vessels complying with any option of section 5.3 of ISO 12217-1
may, after verification by the Certifying Authority, be assigned an area
category per:

| permitted area of operation | MCA area category | ISO 12217 design category |
|---|---|---|
| up to 60 miles from a safe haven | 2 | **B** |
| up to 20 miles from a safe haven | 3 | **B** |
| up to 20 miles from a safe haven in favourable weather and daylight | 4 | **C** |
| up to 3 miles from a point of departure in favourable weather | 5 | **C** |
| up to 3 miles from a point of departure in favourable weather and daylight | 6 | **C** |

**This is the SECOND free national-regulator mapping from an operational-area
regime to the ISO design categories** (NSCV C3 Table 5 is the first, §1.5).
They are broadly consistent in spirit — category B buys roughly 20–60 nm,
category C roughly inshore/favourable-weather — but **they are NOT the same
mapping and must not be merged**: AMSA maps its area C to ISO A *or* B and its
area E to ISO C *or* D, while the MCA never invokes ISO A or D at all. Two
regulators, two different opinions about what a design category is worth.

Appendix 4 ("Use of ISO 'first of type' righting moment curve for stability
assessment") is a free MCA procedure for *verifying* an ISO 12217 righting
moment curve by physical test, including the rule that where the Loaded
Displacement Mass exceeds the Minimum Operating Condition by **more than 15 %**
the stability must also be assessed in the heavier condition. NOT FULLY READ.

**NOT SOUGHT / NOT READ:** the Brown Code, the Yellow Code and MGN 280 are
superseded for new vessels by this Code and were not pursued. Any MGN with
scantling content: **NOT FOUND** — no MGN was located that carries a scantling
formula, and the Workboat Code itself carries none.

---

## 6 · CANADA — TP 1332E and the Small Vessel Regulations

### 6.0 Result: NO scantlings; a real free stability standard; free flotation rules

- URL: `https://tc.canada.ca/sites/default/files/migrated/tp1332e.pdf`
- **"Construction Standards for Small Vessels, 2010 Edition, April 2010,
  TP 1332E"**, 170 PDF pages ("150 of 150" in its own numbering), text layer
  intact.
- **Legal status: this Standard is INCORPORATED BY REFERENCE into the Small
  Vessel Regulations (SOR/2010-91)** — the Standard reproduces the regulation
  text in boxes and states which parts are the Standard and which are
  information only ("Information contained in text boxes that is not numbered
  … is provided for information purposes only and does not form part of the
  Standard").
- **VESSEL SCOPE:** vessels *"constructed or imported in order to be sold or
  operated in Canada"* — pleasure craft AND non-pleasure craft, split at
  **6 metres** and, for non-pleasure craft, up to **15 gross tonnage** /
  24 m. Section 5 covers non-pleasure craft **exceeding 6 m**.
- **NOT FOUND: "12215" — ZERO hits in 170 pages. No design pressure, no section
  modulus. "plywood" appears twice and "scantling" once, none in a rule.**

### 6.1 Structural strength — Small Vessel Regulations s. 713, quoted in the Standard at cl. 3.2. READ VERBATIM

> "**713.** (1) A vessel's structural strength shall conform to the construction
> standards.
> (2) A vessel's structural strength and watertight integrity shall be adequate
> for its intended use, taking into account the maximum anticipated loads. **The
> vessel's strength and integrity are adequate if**
> (a) the vessel is constructed … **in accordance with the recommended practices
> and standards for the type of vessel**;
> (b) **the vessel's design has been used for a vessel of the same type that was
> operated for at least five years without a marine occurrence** or other event
> related to a deficiency in its construction or maintenance in an area where
> the wind and wave conditions are no less severe than those likely to be
> encountered in the vessel's intended area of operation;
> (c) **the vessel's design is supported by calculations or test documents
> proving that the design achieves the required structural strength**; or
> (d) in the case of an open vessel, the structural strength and watertight
> integrity are achieved by **following traditional construction methods that
> have proven to be effective and reliable over time**."

**Paragraph (c) is a binding, free, explicit CALCULATION route to structural
compliance, with no named standard attached.** It is the strongest such
provision found in this survey — stronger than RSG Comment n.7 in the RCD guide
(`EU-REGULATORY.md` §3.4), because it sits in a *regulation* rather than in
non-binding guidance, and stronger than NSCV C3, which offers only named
deemed-to-satisfy documents. **Four alternative sufficiency tests, and one of
them is "your calculations prove it".** Paragraph (b) — five years of
incident-free service in equally severe conditions — is the "empirical
knowledge" route made statutory.

The accompanying **Information Note** (explicitly *not* part of the Standard)
suggests: *"the **Nordic Boat Standard** (for commercial vessels less than
15 m), the International Organization for Standardization (ISO), or a
classification society such as ABS, LRS, BV, DNV or GL."* **The Nordic Boat
Standard is a lead worth following — a multi-government Nordic standard for
commercial craft < 15 m, i.e. exactly this project's band. NOT INVESTIGATED
here; flagged for a follow-up session.**

### 6.2 Stability — Table 5-1 and cl. 5.3. READ VERBATIM

**Table 5-1, suitable standards for stability evaluation (non-pleasure craft
> 6 m):**

| vessel type | length | suitable standard |
|---|---|---|
| **monohull** | > 6 m | **ISO 12217-1 or the standards set out in section 5.3** |
| pontoon | > 6 m and ≤ 8 m | ABYC H-35, or section 5.4 |
| pontoon | > 8 m | section 5.4 |
| inflatable / RIB | > 6 m and ≤ 8 m | ABYC H-28, or ISO 6185-3 |
| inflatable / RIB | > 8 m | ISO 6185-4 |
| sailing | > 6 m | ISO 12217-2 |

with the Information Note: *"For monohull vessels built after April 1, 2005 the
use of the Standard ISO 12217-1 **or the alternative standard set out in section
5.3** is mandatory"*, and — worth noting for this survey — that *"Other
alternatives standards … such as the **UK MCA Code for Small Workboats and Pilot
Boats** or the **Australian National Standard for Commercial Vessels, Part C,
Section 6**"* may be used for inflatables. **Transport Canada explicitly
cross-recognises the two other national codes in this file.**

**Cl. 5.3.2.1 — the free alternative to ISO 12217-1, VERBATIM:**

> "(a) The area under the righting lever (GZ) curve shall not be less than
> **0.055 metre-radians up to 30 degrees**, and not less than **0.09
> metre-radians up to 40 degrees** or the angle of downflooding if less …
> Additionally, the area between 30 and 40 degrees (or 30° and the downflooding
> angle) shall be not less than **0.03 metre-radians**.
> (b) The righting lever GZ shall be at least **0.20 metres** at an angle of heel
> ≥ **30 degrees**.
> (c) The maximum righting lever (GZ) shall occur at an angle of heel **not less
> than 30 degrees**.
> (d) The initial metacentric height (GM) shall not be less than **0.15
> metres**."

**Cl. 5.3.2.2, the alternative where the form cannot put θ_max at 30°:**

> "(a) The maximum righting lever (GZ) shall occur at an angle of heel **not less
> than 15°**; and
> (b) The area under the curve … should not be less than **0.070 metre-radians up
> to 15°** when the maximum GZ occurs at 15°, and **0.055 metre-radians up to
> 30°** when it occurs at 30° or above. Where the maximum GZ occurs between 15°
> and 30°: **Area ≥ 0.055 + 0.001 (30° − θ_max) metre-radians**."

⚠ **The interpolation coefficient is 0.001 here and 0.002 in the MCA's 12B.3.9
(§5.4), for the same-shaped formula.** Both were read from clean text layers.
**They differ, and the difference is real, not a transcription error** — at
θ_max = 15° Canada requires 0.070 m·rad and the MCA 0.085 m·rad, which is
exactly consistent with each code's own stated endpoint. Recorded because
anyone implementing "the IMO alternative-θ_max rule" from memory will pick one
coefficient and be wrong for the other jurisdiction.

**Cl. 5.3.3 — the EMERGENCY HEELING CONDITION, and this is Canada's
offset-load equivalent. READ VERBATIM:**

Triggered *"in all cases where the value of GZ at 10°, in the worst operating
condition, is equal to or less than"*

> **B × N / (34 × Δ)**
>
> "where B = moulded breadth of vessel in metres; N = total number of persons
> carried; Δ = displacement of vessels in tonnes"

**That is a free, closed-form screening criterion in exactly the form this
project can use** — a GZ floor at a fixed 10° heel, scaling with beam and
person count and inversely with displacement. Where triggered, the crowd model
is (cl. 5.3.3.2): persons on the "down" side standing adjacent to their seats,
the remainder moved down-side at **4 persons per square metre** (the same
density as NSCV C6A cl. A3.3), **person weight 75 kg**, and

> **PHA = Heeling moment × cos Θ / Δ**

with the criterion (cl. 5.3.3.3(a)) that *"the angle of static heel, determined
from the intersection of the GZ curve and the heeling arm curve, shall neither
**exceed 10°** nor **immerse the margin line**."*

**So three jurisdictions give three offset-load heel limits: MCA 7° (10° with a
freeboard proviso), Canada 10° (plus margin line), NSCV θ_s = 5/10/14° by heel
consequence level.** All free, all binding, all different, and all in the same
range.

### 6.3 What TP 1332 gives for craft ≤ 6 m — flotation and capacity, NOT YET READ in detail

Section 4 ("Hull design requirements and calculation of recommended maximum
capacities for vessels not more than 6 metres") contains cl. 4.3 recommended
maximum safety limits for monohulls, **cl. 4.4 flotation requirements for
monohull vessels**, 4.5 pontoons, 4.6 inflatables/RIBs, plus Appendices 4 and 5
on calculating hull volume. **"flotation" occurs 36 times.** This is Canada's
analogue of 33 CFR 183 and it is free and formula-bearing. **NOT YET READ** —
out of the length band that matters most to this project (our SKUs are 5–15 m,
so the ≤ 6 m section reaches only the smallest), but it is the obvious next
Canadian target if flotation ever becomes a gate.

Also free and NOT READ: **TP 7301, "Stability, Subdivision, and Load Line
Standards"** (Transport Canada), cited by cl. 5.3.1.3's information note for
inclining-experiment procedure.

---

## 7 · UNITED STATES — 46 CFR Subchapter T and 33 CFR 183

Source for everything in this section: **eCFR, current text, fetched via the
eCFR renderer API** (`https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/…`)
on 2026-08-13, converted to text locally. Direct browser URLs to ecfr.gov
redirect to `unblock.federalregister.gov` and cannot be fetched; **the API path
works and is the one to use.** 46 CFR 170.090 was read via
`law.cornell.edu/cfr/text/46/170.090` because the eCFR API was rate-limiting.

### 7.1 46 CFR 177.300 — the US answer on scantlings is "buy a class rule". READ VERBATIM

**VESSEL SCOPE:** 46 CFR Subchapter T = **small passenger vessels** — under
100 gross tons carrying more than 6 passengers, US-inspected.

> "**§ 177.300 Structural design.** Except as otherwise allowed by this subpart,
> a vessel must comply with the structural design requirements of one of the
> standards listed below for the hull material of the vessel.
> (a) **Wooden hull vessels:** Lloyd's Yachts and Small Craft (incorporated by
> reference, see 46 CFR 175.600);
> (b) **Steel hull vessels:** (1) Lloyd's Yachts and Small Craft; or (2) ABS
> Steel Vessel Rules (<61 Meters) …
> (c) **Fiber reinforced plastic vessels:** (1) Lloyd's Yachts and Small Craft;
> (2) ABS Plastic Vessel Rules …; or (3) ABS High Speed Craft …
> (d) **Aluminum hull vessels:** (1) Lloyd's Yachts and Small Craft; or (i) for
> a vessel of more than 30.5 meters (100 feet): ABS Aluminum Vessel Rules …;
> (ii) for a vessel of not more than 30.5 metres: ABS Steel Vessel Rules
> (<61 Meters), with the appropriate conversions from the ABS Aluminum Vessel
> Rules; or (2) ABS High Speed Craft;
> (e) **Steel hull vessels operating in protected waters:** ABS Steel Vessel
> Rules (Rivers/Intracoastal) …"

**Every one of those is a classification-society rule and every one is PAID.**
There is no CFR scantling formula. Note also **there is no plywood or
sandwich-composite row at all** — wood goes to Lloyd's, FRP to Lloyd's or ABS,
and foam-core sandwich is not named as a hull material.

**THE THREE FREE ESCAPE HATCHES, and they are the US contribution:**

> "**§ 177.310 Satisfactory service as a design basis.** When scantlings … differ
> from those specified by the standards listed in § 177.300 … and the owner can
> demonstrate that the vessel, **or another vessel approximating the same size,
> power, and displacement**, has been built to such scantlings and has been in
> satisfactory service insofar as structural adequacy is concerned **for a period
> of at least 5 years**, such scantlings may be approved by the cognizant OCMI …"
>
> "**§ 177.315 Vessels of not more than 19.8 meters (65 feet) in length carrying
> not more than 12 passengers.** The scantlings for a vessel [in that band] that
> do not meet the standards in § 177.300 or § 177.310 **may be approved by the
> cognizant OCMI if the builder … establishes to the satisfaction of the OCMI
> that the design and construction of the vessel is adequate for the intended
> service.**"
>
> "**§ 177.340 Alternate design considerations.** When the structure of vessel is
> of **novel design, unusual form, or special materials**, which cannot be
> reviewed or approved in accordance with § 177.300, § 177.310 or § 177.315, the
> structure **may be approved by the Commanding Officer, Marine Safety Center,
> when it can be shown by systematic analysis based on engineering principles
> that the structure provides adequate safety and strength.** The owner shall
> submit detailed plans, material component specifications, and design criteria,
> **including the expected operating environment, resulting loads on the vessel,
> and design limitations** for such vessel, to the Marine Safety Center."

**§ 177.340 is the cleanest statement of a first-principles route found in this
entire survey**, and it names precisely the four things this project's ladder
produces: operating environment, resulting loads, design limitations, plans.
The five-year service rule of § 177.310 is the same device as Canada's
s. 713(2)(b) — **two independent regulators both accept incident-free service
history as a substitute for a scantling rule.**

### 7.2 46 CFR 178.330 — the Simplified Stability Proof Test (SST). READ VERBATIM

**Applicability (§ 178.320(a)):** monohulls, and flush-deck catamarans that are
not pontoon vessels and carry ≤ 49 passengers, *"if they do not have tumblehome
at the deck, measured amidships, that exceeds **2 percent of the beam**"*.

**Test condition (§ 178.330(a)):** construction complete; ballast in place; fuel
and water tanks **approximately three-quarters full**; sewage tank empty or
full; total test weight of passengers, crew and variable loads aboard,
distributed for normal trim and the least stable likely VCG; **all non-return
closures on cockpit scuppers or weather deck drains kept OPEN during the test**
(the same provision as MCA 12A and NSCV 7B). Key numbers:

- *"The vertical center for the total test weight must be at least **30 inches
  (760 millimetres)** above the deck for **seated** passengers, and at least
  **39 inches (1.0 metre)** above the deck for **standing** passengers."*
  (Compare NSCV C6A cl. A3.2: standing 1 m above deck, seated 300 mm above the
  SEAT — a different datum, so 760 mm above deck and 300 mm above seat are
  compatible if the seat is ~460 mm high. Free cross-check, and it holds.)
- diving gear: *"Not less than **80 pounds (36.3 kilograms)** should be assumed
  for each person for whom diving gear is provided."*
- upper deck: *"Weight on Upper Deck = (Number of Passengers on Upper Deck) ×
  (Wt per Passenger) × **1.33**"* — **the same 33 % upper-deck penalty as MCA
  cl. 12A.2 / 12B and NSCV cl. 7.3.5.3 and 7.4.4(d).** Three jurisdictions, same
  factor.

**Heeling moments (§ 178.330(b)) — the vessel must not exceed the limits when
subjected to the GREATER of:**

> **M_p = (W)(B_p)/6** ; or **M_w = (P)(A)(H)**
>
> "M_p = passenger heeling moment in foot-pounds (kilogram-meters); W = the
> total weight of persons other than required crew, plus the personal effects …
> (total test weight); B_p = the maximum transverse distance … of a deck that is
> accessible to passengers; A = Area … of the projected lateral surface of the
> vessel above the waterline (including each projected area of the hull,
> superstructure, cargo, masts, area bounded by railings and canopies, but not
> protruding fixed objects such as antennas or running rigging)."

⚠ **The definitions of P and H are NOT PRESENT in the § 178.330(b) text as
retrieved**, though both symbols are used in the formula. They ARE given for
the sailing case (§ 178.330(c)(3): **P = 4.9 kg/m² (1.0 lb/ft²)** for protected
and partially protected waters, A with all sails set and trimmed flat, H to the
centre of effort) and for pontoon vessels (§ 178.340(b): **P = 7.5 lb/ft²
(36.6 kg/m²)**). **The general-case P is NOT FOUND and is not inferred here.**
For orientation only, 36.6 kg/m² ≈ **359 Pa**, which sits exactly on NSCV
Table 41's area-D value of 360 Pa — but that is a coincidence of two different
quantities until the general-case P is actually read.

**M_p = W·B_p/6 is a beautifully simple free offset-load moment**: total
passenger weight times the widest accessible deck breadth, divided by six.
(Implicitly it models the crowd's transverse CG at B_p/6 from centreline, i.e.
one-third of the half-breadth.) For pontoons, § 178.340(b) uses
**M_pc = W(B_p − K)/2 with K = 2.0 ft (0.61 m)** instead.

**THE LIMITS OF HEEL (§ 178.330(d)) — free, complete, and hull-type keyed:**

| hull type | limit |
|---|---|
| flush deck vessel | not more than **one-half of the freeboard** may be immersed |
| well deck vessel | not more than **one-half**; except on protected waters with non-return scuppers/freeing ports, the **full freeboard** may be immersed if the full freeboard is not more than **one-quarter** of the waterline-to-gunwale distance |
| **cockpit vessel, exposed waters** | **i = f (2L − 1.5 L′) / 4L** |
| **cockpit vessel, protected or partially protected waters** | **i = f (2L − L′) / 4L** |
| open boat | not more than **one quarter of the freeboard** may be immersed |
| flush deck **sailing** vessel | the **full freeboard** may be immersed |
| non-sailing flush deck **catamaran**, mechanically propelled | not more than **one-third of the freeboard or one-third of the draft, whichever is less** |
| **all cases** | *"In no case may the angle of heel exceed **14 degrees**."* |

> "where: i = maximum allowable immersion in meters (feet); f = freeboard in
> meters (feet); L = length of the weather deck, in meters (feet); and L′ =
> length of cockpit in meters (feet)."

**⚠ THIS RESOLVES A CROSS-JURISDICTION IDENTITY. NSCV C6A criteria 7B.2d and
7B.2e (§4.4 above) are the SAME TWO FORMULAS**, in the same two
exposed/protected variants, with the same 1.5 factor on the cockpit length —
`δ_f < F_G(2L − 1.5C)/4L` and `δ_f < F_G(2L − C)/4L`. AMSA writes freeboard as
F_G and cockpit length as C; the USCG writes f and L′. **They are one rule,
adopted by two regulators.** That is strong independent confirmation that both
were transcribed correctly, and it makes this the single best-attested free
formula in this file.

Heel is measured (§ 178.330(e)) *"at the point of minimum freeboard; or at a
point three-quarters of the vessel's length from the bow if the point of minimum
freeboard is aft of this point"*; freeboard is measured (§ 178.330(f)) to the
top of the weather deck at the side for flush/well deck vessels, and to the top
of the gunwale for cockpit vessels and open boats.

**Assumed weight per person, 46 CFR 170.090** (read at Cornell LII, not eCFR):
the Assumed Average Weight Per Person is **185 lb** (effective 1 December 2011),
derived by *"add mean weights of U.S. males and females aged 20+, divide by 2,
add **7.5 pounds** for clothing, and round to the nearest whole number"*.
**185 lb = 83.9 kg.** ⚠ **UNVERIFIED against the eCFR original** — this is a
paraphrase-plus-quote returned by a fetch of a secondary host, and the "185 lb"
should be confirmed in eCFR before it is quoted anywhere. If it holds, it is
the closest free number to `limits.CREW_MASS_KG = 85.0` found anywhere, and it
is the only one with a published derivation method rather than a bare value.

**Also free in Subchapter T, cl. 178.420(b):** *"The cockpit deck of a cockpit
vessel that operates on exposed or partially protected waters must be at least
**255 millimeters (10 inches)** above the deepest load waterline"* unless the
vessel meets the full Subchapter S intact and damage stability rules; and where
the deck is below 255 mm, scuppers must have non-return devices. **That is a
free, absolute, dimensional downflooding-style margin** and it is the nearest
thing in this survey to an ISO 12217 downflooding HEIGHT in metres.

### 7.3 33 CFR 183 — FLOTATION AND CAPACITY, EXPLICITLY NOT SCANTLINGS

**VESSEL SCOPE: recreational boats** (Subpart F applicability is boats
manufactured or imported for US recreational use; Subpart C excludes sailboats,
canoes, kayaks, inflatables, submersibles, surface effect vessels, amphibious
vessels and raceboats, and applies to monohulls under a horsepower ceiling).

**Confirmed by full-text search of the retrieved Part 183: the string
"scantling" occurs ZERO times.** There is no structural strength, panel
thickness or design pressure requirement anywhere in Part 183. Recording that
as a positive result, per the brief.

What it does contain, free and formula-bearing:

> "**§ 183.105 Quantity of flotation required.** (a) Each boat must have enough
> flotation to keep any portion of the boat above the surface of the water when
> the boat has been submerged in **calm, fresh water for at least 18 hours** and
> loaded with: (1) A weight that, when submerged, equals **two-fifteenths of the
> persons capacity** marked on the boat; (2) A weight that, when submerged,
> equals **25 percent of the dead weight**; and (3) A weight in pounds that, when
> submerged, equals **62.4 times the volume in cubic feet of the two largest air
> chambers**, if air chambers are used for flotation.
> (b) … 'dead weight' means the maximum weight capacity marked on the boat minus
> the persons capacity marked on the boat."

(62.4 lb/ft³ is fresh-water density; 2/15 is the assumed submerged fraction of
a person's weight.) Subpart C adds the level-flotation test preconditioning
(§ 183.320: 18 hours, 2/15 of persons capacity + 25 % of the maximum weight
capacity less engine weight from Table 183.75 less persons capacity) and the
geometric definitions of passenger-carrying area, reference areas and reference
depth (§§ 183.305–183.315). **Not read in full; not this project's gate.**

**USCG NVICs: NOT SEARCHED.** Out of time budget; noted as an unexplored source.
The brief flagged them as lower priority than the CFR itself.

---

## 8 · NEW ZEALAND — Maritime Rules Part 40A

### 8.0 Result: no scantlings; a compact free stability code that mirrors the others

- URL: `https://www.maritimenz.govt.nz/media/4qgplugn/part40a-maritime-rule-currentpdf.pdf`
- **"Maritime Rules Part 40A: Design, Construction and Equipment — Passenger
  Ships which are not SOLAS Ships"**, Maritime New Zealand **Consolidation,
  28 January 2026**. 118 PDF pages, text layer intact.
- **Legal status: BINDING** (a Maritime Rule made under the Maritime Transport
  Act).
- **VESSEL SCOPE:** non-SOLAS passenger ships — ferries, excursion ships, water
  taxis, commercial recreational-fishing and diving boats. Three sections:
  conventional craft, high-speed craft, hire-and-drive. Operating-limit tiers
  are **Offshore/Coastal, Restricted Coastal, Restricted Limits**.
- **NOT FOUND: "12215" and "12217" — ZERO hits each.** No scantling formula;
  "scantling" occurs once, in a rule about not altering scantlings after survey
  (r. 40A.8(3)).

### 8.1 Construction — r. 40A.9. READ VERBATIM

> "(1) The construction of a ship must provide strength for the safe operation of
> the ship and to withstand the sea and weather conditions likely to be
> encountered in the intended area of operation, **assuming that the ship is
> operated at its service draught and driven prudently at its maximum service
> speed**.
> (2) A post-27 May 2004 ship complies with rule 40A.9(1) if it is constructed
> under survey and is — (a) certified as being in accordance with hull or full
> certification standards … by any one of the following classification societies:
> **American Bureau of Shipping, Bureau Veritas, DNV GL AS / DNV GL / DNV / GL,
> Lloyd's Register of Shipping, Nippon Kaiji Kyokai**; or (b) certified by any
> one of the marine safety authorities of a State or Territory of the C[ommonwealth
> of Australia] …"

**Note (2)(b): New Zealand accepts an Australian State/Territory marine safety
authority's certification directly** — i.e. the NSCV route (§§1–4 above) is a
compliance path in New Zealand. Same cross-recognition pattern as Canada's
TP 1332 Table 5-1 information note.

**Materials, free and citable, Appendix 8 cl. 2.2(b)** (Code of Practice for
commercial recreational diving boats):

> "timber used in a rigid hulled boat must be suitable and appropriately treated
> for use in a marine environment. **Exposed plywood must be of a marine grade
> that complies with the current standard AS/NZS 2272 Plywood – Marine.**"

**Second free regulator naming AS/NZS 2272 for marine plywood** (USL 5M
cl. M.3.1(c) is the first, naming AS 2272-1979). No jurisdiction surveyed names
BS 1088 — **BS 1088 was NOT FOUND in any of the seven documents read.**

### 8.2 Appendix 1 cl. 1.1 — the heeling test. READ VERBATIM

Applies to a post-27 May 2004 **single-hull decked ship < 15 m LOA, carrying
≤ 50 passengers, within restricted limits**:

> "(3) … must be tested in the fully loaded condition to ascertain the angle of
> heel and the position of the waterline that would result if — (a) **all of the
> passengers that the ship is certified to carry are assembled along one side of
> the ship**; and (b) a helmsman is at the helm.
> (4) The results of the heel test must show — (a) the **angle of heel does not
> exceed 15°**; and (b) the **freeboard to the deck** or, if the ship has no side
> deck, to the top of the cockpit coaming, **is not less than 75 mm at any
> point**.
> (5) For the purpose of the test, each of the passengers and the helmsman must
> be represented by a mass of **at least 75 kg**.
> (6) If the ship is fitted with a cockpit, it must be demonstrated that the ship
> — (a) has a **reserve of buoyancy when the cockpit is full of water**; and
> (b) **does not heel more than 15° when the cockpit is full of water**."

**The 75 mm residual freeboard is IDENTICAL to MCA Workboat Code cl. 12A.2.3
and to MCA cl. 12B.1.2.1(.5).** The heel limit differs: NZ 15°, MCA 7°/10°.
Appendix 8 cl. 2.2(c) repeats the same test with a **15°** limit for commercial
recreational diving boats.

**Multihull heeling test, cl. 1.3:** a multihull decked ship < 15 m LOA carrying
≤ 50 passengers *"must be tested to establish that, in the fully loaded
condition, the ship **does not heel or trim in any direction by more than 8°**
when subject to uncontrolled passenger crowding"* (crowd model per cl. 1.2(8)(d)(i)).
Footnote: *"The heel test may be established by a physical test or by
calculation."* — **an explicit free statement that calculation substitutes for
the physical test.**

### 8.3 Appendix 1 cl. 1.2 — full GZ criteria (≥ 15 m LOA, > 50 passengers, or beyond restricted limits). READ VERBATIM

> "(a) area under the GZ curve must not be less than — (i) **0.055 metre-radians
> up to 30°**; and (ii) **0.09 metre-radians up to 40°** or the downflooding
> angle if less; and
> (b) area between 30° and 40° (or 30° and the downflooding angle if less than
> 40°) not less than **0.03 metre-radians**; and
> (c) **GZ must be at least 0.20 metres at a heel ≥ 30°**; and
> (d) except as in (e), the **maximum GZ must occur at a heel of not less than
> 25°**; and
> (e) if the hull form results in the maximum GZ occurring at less than 25° but
> **not less than 15°**, this may be accepted by a surveyor provided the area up
> to θ_m is not less than **0.055 + 0.001 (30 − θ_m) metre-radians**; and
> (f) after correction for free surface effects, **GM must not be less than 0.35
> metres**."

**Identical to MCA 12B.3.8 including θ_max ≥ 25° and GM ≥ 0.35 m, and identical
to Canada TP 1332 cl. 5.3.2 except for θ_max (25° vs 30°) and GM (0.35 vs
0.15 m).** The interpolation coefficient is **0.001**, matching Canada and NOT
matching the MCA's 0.002 (§6.2). So the split on that coefficient is
Canada + NZ (0.001) against the UK (0.002).

**For > 50 passengers, cl. 1.2(8) adds:** heel **≤ 10°** under any single
capsizing moment (crowding, wind, turning) or **≤ 15°** under the worst two
together; GZ at the intersection of the righting and heeling lever curves
**must not exceed 0.6 GZ_max**; and the residual area above the passenger
heeling lever curve up to the downflooding angle or second intercept **not less
than one quarter of the total area** under the righting lever curve to the same
angle.

**Heeling-moment models, cl. 1.2(8)(d) — free and closed form:**

- **crowding:** *"a standard mass per person of **75 kg**; a distribution of
  **4 passengers per square metre**; the centre of gravity of a standing person
  as **1 metre above the deck** and a seated person as **300 mm above the
  seat**."* — **character-for-character the same crowd model as NSCV C6A
  cl. A3.2–A3.3, except the person mass (NZ 75 kg vs AMSA 80 kg).**
- **wind:** **M = 0.000102 · P · A · h  (tonne-metres)**, with

  | operating limits | wind pressure |
  |---|---|
  | Offshore/Coastal | **500 Pa** |
  | Restricted Coastal | **450 Pa** |
  | Restricted Limits | **350 Pa** |

  A = projected area of ship above waterline (m²); h = vertical distance between
  the centroid of A and that of the lateral underwater area (m).
  **Note 0.000102 ≈ 1/9810 = 1/(1000 g)** — so this is algebraically the same
  formula as NSCV C6A Annex B (`M_W = P·A·h·cos θ / (1000 g)`) with the cos θ
  term dropped (upright value only).
- **turning:** **M = 0.0053 · V² · Δ · d / L  (tonne-metres)**, *"derived from
  the formula below **when V/√L is less than 4**"*, V = service speed in knots,
  L = waterline length (m), Δ = displacement (t), d = vertical distance between
  the CG and the centroid of the lateral underwater area (m).
  **This is EXACTLY NSCV C6A Annex C**, including the constant 0.0053 and the
  V ≤ 4√L cap — AMSA expresses the cap as a substitution (use the lesser of the
  max speed and 4√L), New Zealand as an applicability condition. **Second
  formula in this file attested identically by two independent regulators.**

### 8.4 Appendix 1 cl. 1.4 — multihull criteria, and it resolves the NSCV ambiguity

For a multihull decked ship ≥ 15 m LOA or carrying > 50 passengers:

> "(a) the area under the GZ curve must not be less than **0.055 × 30°/θ
> metre-radians up to θ**, where θ is the lesser of — (i) the downflooding
> angle; or (ii) the angle at which the maximum GZ occurs; or (iii) **30°**; and
> (b) the **maximum GZ must occur at a heel of not less than 10°**; and
> (c) the **heel due to steady wind must not exceed 16°** when the following wind
> heel lever is applied: **h_w = P·A·Z / (9800 Δ)  (metres)**, where P is the
> wind pressure from the table in cl. 1.2(8)(d)(ii), A is the projected lateral
> area above the lightest service waterline (m²), **Z is the vertical distance
> from the centre of A to a point one half the lightest service draught (m)**,
> and Δ is displacement (tonnes); and
> (d) the residual area (A₂) created by the wind lever plus crowding on one side
> (h_w + h_p) …" [remainder NOT READ]

**Cross-check against NSCV C6A Table 11 (§4.5): 5B.2 requires θ_max ≥ 10° —
identical. 5B.4 caps combined wind-plus-crowding/turning heel at 16° — the same
16° NZ applies to steady wind. And 5B.1's scrambled formula almost certainly
reads A₁ ≥ 3.15 × (30/φ) metre-degrees, which is 0.055 × 30/θ metre-radians
converted (0.055 rad = 3.151 deg), with φ defined by the same three-way
minimum.** ⚠ **That is a HYPOTHESIS from an independent regulator's identical
rule, NOT a reading of the AMSA page. It is recorded to say what to expect when
someone opens p. 37 of C6A as an image — it is not a substitute for doing so.**

---

## 9 · CROSS-CUTTING COMPARISON

### 9.1 Design pressure — only ONE free national source has a formula

| jurisdiction | free design-pressure rule for a small craft? |
|---|---|
| **Australia (USL 5G)** | **YES.** Displacement hulls: a static head above the exposed deck, 1.25 m at the bow tapering to 0.625 m at the forward quarter point and constant aft (cl. G.3); deck loads (0.02 L + 0.76)·1025 kg/m² for classes A/B/C and (0.02 L + 0.46)·1025 for D/E. Planing hulls: the full Heller & Jasper chain P₀ = (3W/2L)(1 + a_CG/g) → p₀ = 3P₀g/G → p_I = 1.1 p₀ → p = p_I F_I F_T + P_h. |
| **Australia (USL 5M)** | a pressure FLOOR only: P ≥ **3(L + 6) kPa**, deadrise < 12° specially considered. |
| UK (Workboat Code 3) | NO. |
| Canada (TP 1332) | NO. |
| USA (46 CFR 177) | NO. |
| NZ (Part 40A) | NO. |
| EU (RCD, ES-TRIN) | NO (`EU-REGULATORY.md` §2.4, §4.5). |

**Scaling behaviour, where it exists:** with **length** — linearly, in both the
displacement-hull deck loads (coefficient 0.01–0.02 per metre) and the 5M
minimum (3 L). With **speed** — only through the 6V term in the 5M bottom-ply
length minimum (V in knots) and, in 5G Part III, through the acceleration model
rather than an explicit V. With **displacement** — only in the planing chain
(P₀ ∝ W). With **operational area** — by a shift in the additive constant
(0.76 → 0.46 m of head between classes A/B/C and D/E), and by USL 5B cl. B.1.6's
discretionary **−25 % for Class E**.

### 9.2 Panel scantlings — one free formula set, plywood only

Only **USL 5M Part 4** gives one. Summary of the whole free rule, with t in mm,
P in kPa, S in mm (stiffener spacing), L in m (L_WL), V in knots:

| member | rule |
|---|---|
| bottom | greater of **t = 0.018 f (125 + P) S/100** and **t = 0.021 (160 + 50L + 6V)** |
| side | greater of **t = 0.013 f (100 + P_s) S/100** and **t = 0.021 (160 + 50L)**; **≥ 6 mm** |
| deck, L ≤ 15 m | **t = 0.036 S** |
| deck, L > 15 m | **t = 0.001 (L + 33) S** (transverse beams) or **t = 0.001 (L + 18) S** (longitudinals); floor **t = 2.1 (0.2L + 3)** |
| transom w/ engine | **t = 0.041 (160 + 50L) + a**, a from a kW table (20–45 mm) |
| aspect ratio | **f₁ = 0.6 + 0.2 (a/b)** for a/b < 2 (=1.0 at a/b = 2) |
| frame breadth | **f₂ = 1.1 − 2 (K/S)** for K > 0.05 S, floored at **0.7** |
| curvature | **NOT FOUND** (hard-chine code; developable panels) |

**FRP single-skin: NOT FOUND FREE anywhere.** Australia sends it to AS 4132.3
(paid), the US to Lloyd's or ABS (paid), the UK to a Recognised Organisation or
ISO 12215 (paid), Canada to ISO / Nordic Boat Standard / class, NZ to a class
society.

**CARBON FIBRE: NOT FOUND, in any document, in any jurisdiction.** Not one of
the seven codes read names carbon fibre as a hull material at all.

**FOAM-CORE SANDWICH: NOT FOUND.** No core shear rule, no skin-wrinkling rule,
no minimum-skin rule, no core-density rule, in any free national code read.
NSCV C3 Table 4 lists ISO 12215-2 (core materials) as a *deemed-to-satisfy
pointer*; that is the closest any free text comes, and it is a pointer to a
paid standard. **This is the single largest unmet need in the survey.**

**Stiffener section modulus: NOT FOUND as a closed-form rule.** The nearest are
USL 5M cl. M.41.2's scaling law **Z₂ = Z_c (14 / permissible working stress)**
(which presupposes a Z computed by clauses M.43/M.47, NOT YET READ) and USL 5G
cl. G.11.6's beam method (**max BM = w(zG)²/8** pin-ended, **p ℓ²/12**
fixed-ended, with an effective flange width of **2h√(E/σ_y)** mm or the
transverse spacing, whichever is less).

### 9.3 Allowable stress by material — two free answers, and they are different in KIND

| source | material | allowable |
|---|---|---|
| **USL 5M cl. M.41.1** | **plywood** | bending **14.0 MPa**, tensile **11.0 MPa**, E **12 500 MPa** |
| **USL 5M cl. M.41.1** | **timber** | bending **14.0 MPa**, tensile **11.0 MPa**, E **12 500 MPa** — *identical to plywood* |
| **USL 5G cl. G.11.15** | metals | **σ₁ + σ₂ + σ₃ < σ_y** — the yield stress, applied to the SUM of primary + secondary + tertiary stress |
| any code | FRP / carbon / sandwich | **NOT FOUND** |

**Neither free source expresses the allowable as a fraction of ultimate.** 5M
hands over an absolute working stress; 5G hands over yield with an implied
factor of 1.0 but a three-component stress sum. **So the answer to "does plywood
differ from FRP differ from carbon" is: no free national code says, because no
free national code covers FRP or carbon at all.** And within wood, the answer is
that **plywood and solid timber are given identical allowables** by USL 5M, with
the density correction (960/W below 800 kg/m³) and the M.41.2 √(14/σ_perm)
substitution as the only material differentiators.

### 9.4 Stability criteria — four regulators, one ancestor, small deliberate divergences

**The GZ-curve criteria are the IMO Intact Stability Code, adopted four times.**
Where they agree (all of AU / UK / CA / NZ):

- area to 30° ≥ **0.055 m·rad** (= 3.15 m·deg)
- area to 40° or θ_f ≥ **0.09 m·rad** (= 5.16 m·deg)
- area 30°–40° (or to θ_f) ≥ **0.03 m·rad** (= 1.72 m·deg)
- **GZ ≥ 0.20 m at ≥ 30°**

Where they diverge:

| | AU NSCV C6A | UK Workboat 3 | Canada TP 1332 | NZ 40A |
|---|---|---|---|---|
| θ_max floor | **15°** | **25°** | **30°** (15° alt.) | **25°** (15° alt.) |
| GM floor | **0.15 / 0.20 / 0.35 m** by vessel class | **0.35 m** (0.5 m if Δ estimated) | **0.15 m** | **0.35 m** |
| alt-θ_max interpolation | `3.15 + 0.057(30 − θ)` m·deg | `0.055 + 0.002(30 − θ)` m·rad | `0.055 + 0.001(30 − θ)` m·rad | `0.055 + 0.001(30 − θ)` m·rad |
| multihull θ_max floor | **10°** | **15°** | — | **10°** |

⚠ **AMSA's 3.15 + 0.057(30 − θ) m·deg converts to 0.055 + 0.000995(30 − θ)
m·rad** (0.057 m·deg = 0.000995 m·rad). **So Australia, Canada and New Zealand
all use the same 0.001 coefficient, and only the UK's 0.002 differs — by a
factor of two.** That is a real divergence between binding national codes, in a
formula that looks like a transcription of one IMO clause. **Do not implement
"the IMO rule" and assume it is jurisdiction-neutral.**

**Offset-load / heel-in-crowding limits, all free, all binding:**

| jurisdiction | heel limit | residual condition |
|---|---|---|
| **UK** (12A.2.2) | **7°**, or **10°** | if 10°, heeled freeboard per Table 13.1.1; ≥ **75 mm** freeboard to deck |
| **USA** (178.330(d)) | **≤ 14° in all cases**, plus a freeboard-immersion limit by hull type | ½ freeboard flush/well; ¼ open boat; ⅓ catamaran; cockpit by formula |
| **Canada** (5.3.3.3) | **≤ 10°** | must not immerse the margin line |
| **NZ** (App. 1 cl. 1.1) | **≤ 15°** monohull, **≤ 8°** multihull | ≥ **75 mm** freeboard to deck or cockpit coaming |
| **Australia** (Table 4 / 7B) | **θ_s = 5 / 10 / 14°** by heel consequence level | 50 % of freeboard (flush/well deck), 75 % to gunwale (D/E), cockpit by formula |

and the **cockpit formula is literally shared** between the USA (§178.330(d)(3))
and Australia (7B.2d/e): **i = f(2L − 1.5L′)/4L** exposed,
**i = f(2L − L′)/4L** protected.

**Wind pressures, free, by area:**

| Pa | source |
|---|---|
| 600 / 450 / 360 / 300 | NSCV C6A Table 41 (areas A&B / C / D / E) |
| 500 / 450 / 350 | NZ 40A cl. 1.2(8)(d)(ii) (Offshore-Coastal / Restricted Coastal / Restricted Limits) |
| 540 (30 m/s) | MCA 12B.3.11 (barges/pontoons only) |
| ~359 (7.5 lb/ft²) | 46 CFR 178.340(b) (pontoon vessels only) |
| ~48 (1.0 lb/ft²) | 46 CFR 178.330(c)(3) (sailing vessels, sails set) |

**Turning moment: two identical free statements** —
**M_T = 0.0053 V² Δ h / L_WL** with **V ≤ 4√L_WL knots**, AMSA C6A Annex C and
NZ 40A cl. 1.2(8)(d)(iii).

**Crowd model: three near-identical free statements** — 4 persons/m², standing
CG 1 m above deck, seated CG 300 mm above seat (AMSA C6A A3.2–A3.3; NZ 40A
cl. 1.2(8)(d)(i); Canada TP 1332 cl. 5.3.3.2 gives the 4/m² density), and a
1.33 upper-deck weight factor (AMSA, MCA, USCG).

### 9.5 Person mass — seven free values, and none of them is 85 kg

| kg | source | purpose |
|---|---|---|
| 75 | ISO 14946 via RCD guide | builder's-plate crew limit |
| 75 | Canada TP 1332 cl. 5.3.3.2(c) | emergency heeling condition |
| 75 | NZ 40A App. 1 cl. 1.1(5), 1.2(8)(d)(i) | heel test and crowding moment |
| 75 | MCA, existing vessels from MGN 280 / Brown Code | legacy stability |
| 80 (+15 overnight) | NSCV C6A Table 40 | stability criteria; Australian adults, 2005, incl. 5 kg clothing |
| **82.5** | **MCA Workboat 3 cl. 12.1.1.1, 13.1.2** | all UK stability and freeboard |
| ~83.9 (185 lb) ⚠ UNVERIFIED | 46 CFR 170.090 | US assumed average weight per person, incl. 7.5 lb clothing |
| 90 (80 + 10) | NSCV C6A cl. 7.6.3.2(a), < 7.5 m | stability proof test |
| 100 | MCA Workboat 3, police boats | stability assessment |
| **85.0** | **`limits.CREW_MASS_KG`** | our offset-load heel moment |

**Our 85.0 is inside the free range and between the MCA's 82.5 and the USCG's
~83.9 — but no free source states it.** Recorded as a finding, not a
recommendation: changing it would change every offset-load result and is not a
documentation fix.

### 9.6 Freeboard — two free closed-form rules, and they differ by ~1.7×

| | AMSA NSCV C6A Tables 26/29 | MCA Workboat 3 Table 13.1.2 |
|---|---|---|
| < 6 m / < 7 m | 150 mm | 300 mm (decked) · 200 mm (stepped) · 400 mm (open) |
| ramp | 150 + (L−6)·100/4 over 6–10 m | linear interpolation over 7–18 m |
| top | 250 mm at ≥ 10 m | 750 / 400 / 800 mm at ≥ 18 m |
| what it IS | a *prerequisite* for a simplified stability route, area C passenger vessels | *the* minimum freeboard requirement |

plus ES-TRIN Art. 4.02's **150 mm** base with sheer credits
(`EU-REGULATORY.md` §4.1), and 46 CFR 178.420(b)'s **255 mm** cockpit-deck
height above the deepest load waterline.

---

## 10 · WHAT THIS CAN AND CANNOT REPLACE

### 10.1 ISO 12215-5 (design pressures, design stresses, scantling determination)

| 12215-5 role | free national substitute | verdict |
|---|---|---|
| design pressure, displacement monohull | **USL 5G cl. G.3, G.4, G.7** (static head + length-linear deck/superstructure loads, class-keyed) | **PARTIAL.** Free and complete for what it covers, but it is a 1980s static-head rule with no wave-height or design-category keying and no hull-form terms. It will not reproduce a 12215-5 pressure. |
| design pressure, planing monohull | **USL 5G Part III** (Heller & Jasper: P₀, p₀, p_I, F_I, F_T, F_L, P_h) | **YES in structure, PARTIAL in data.** The chain is complete and closed-form except that **F_I, F_T and F_L are CHARTS**, two of which are digitized here only approximately and one of which (F_L, Figure 5) was not read at all. |
| **plywood panel thickness** | **USL 5M Part 4 cl. M.42** | **YES.** Bottom, side, deck, transom; aspect-ratio and frame-breadth factors; a 6 mm floor. This is the one place where a free national code fully does 12215-5's job for a material we use. |
| **FRP single-skin panel thickness** | — | **NO. NOT FOUND.** |
| **carbon-fibre laminate** | — | **NO. NOT FOUND — not even mentioned.** |
| **foam-core sandwich: core shear, skin wrinkling, minimum skin, core density** | — | **NO. NOT FOUND in any jurisdiction.** |
| stiffener section modulus | USL 5M cl. M.41.2 (scaling) + M.43/M.47 (NOT YET READ); USL 5G cl. G.11.6 (beam method) | **PARTIAL / UNKNOWN.** The scaling law and the beam method are free; the base Z formula for plywood is in unread clauses of a scanned document. |
| allowable stress | **USL 5M cl. M.41.1** (plywood/timber 14.0 / 11.0 / 12 500 MPa); **USL 5G cl. G.11.15** (σ₁+σ₂+σ₃ < σ_y) | **PARTIAL.** Free for wood and for metals. Nothing for composites. |
| curvature factor | — | **NOT FOUND** — and correctly absent from a hard-chine code, so this is not evidence that no such factor is needed. |
| approved plywood grade | **AS/NZS 2272 Plywood – Marine**, named by USL 5M cl. M.3.1(c) and NZ 40A App. 8 cl. 2.2(b); WBP-bonded glue per **BS 1204** or epoxy | **YES as a specification pointer** (though AS/NZS 2272 itself is a paid Standards Australia document). **BS 1088 was NOT FOUND in any national code read.** |
| legitimacy of a first-principles route | **46 CFR 177.340**, **Canada SVR s. 713(2)(c)**, **USL 5M cl. M.3.2**, **NSCV C3 ch. 2**, NZ 40A r. 40A.9(1) | **YES, strongly.** Five jurisdictions accept calculation or engineering analysis in place of a named scantling standard, three of them in binding regulation. This is the most important non-numeric result in the file. |

**Net:** the free national corpus replaces ISO 12215-5 **for plywood on a
hard-chine hull, and for nothing else.** For FRP, carbon and foam sandwich it
replaces nothing at all — and those are three of this project's four materials.

### 10.2 ISO 12217-1 (stability and buoyancy assessment and categorization)

| 12217-1 role | free national substitute | verdict |
|---|---|---|
| **GZ-curve intact criteria** | **NSCV C6A ch. 5A**, **MCA 12B.3.8**, **TP 1332 cl. 5.3.2**, **NZ 40A App. 1 cl. 1.2** — four independent adoptions of the IMO IS Code | **YES, fully.** Areas, GZ floor and θ_max are free, binding and mutually corroborating. |
| **GM floor** | 0.15 m (AU Class 1, CA) · 0.20 m (AU Class 2) · 0.35 m (AU Class 3, UK, NZ) · 0.50 m (UK, estimated Δ) | **YES for a value; NO for our KEY.** Every free floor is keyed to vessel USE or to knowledge of Δ. **None is keyed to design category, so `limits.CATEGORY_TABLE`'s GM column still has no free source and R-GM stays ours** — the same conclusion `EU-REGULATORY.md` §4.5 reached, now tested against four more regulators. |
| **offset-load heel limit** | UK 7°/10°, USA ≤14° + freeboard immersion, Canada ≤10° + margin line, NZ 15° (8° multihull), AU θ_s = 5/10/14° | **YES as a criterion, NO as a drop-in.** Five free limits spanning 7–15°, none of them a function of hull length. `iso12217.offset_load_heel_limit_deg(LH)` is a **cubic in L_H**; no free code has any length dependence at all. **Substituting one of these would change the physics, not just the citation.** |
| **downflooding height** | **NOT FOUND as a height in metres**, except 46 CFR 178.420(b)'s 255 mm cockpit-deck rule. Free codes instead use downflooding ANGLES (all four GZ regimes) and fractions of freeboard (NSCV 25 % to the first downflooding point, 50 % to the deck edge; UK/USA/AU 50 % / 75 % inclined-freeboard rules) | **PARTIAL, and in a different formulation.** `iso12217.R-DFH` holds a height; the free codes hold angles and ratios. They are not interconvertible without the hull geometry, which is exactly what our ladder has — so this is implementable, but it is a re-derivation, not a substitution. |
| **angle of vanishing stability** | **NOT FOUND** as a general criterion in any of the four codes. MCA 12B.3.11 requires a 20° range for barges only; MCA Annex J and NZ speak of a 90° range inside SAILING criteria | **NO.** |
| **heel in a turn** | **M_T = 0.0053 V² Δ h / L_WL, V ≤ 4√L_WL kn** — AMSA C6A Annex C and NZ 40A, identically | **YES, fully, and double-attested.** |
| **wind heeling** | **M_W = P·A·h·cos θ /(1000 g)** with P = 600/450/360/300 Pa (AU) or 500/450/350 Pa (NZ) | **YES, fully.** This is the first free source in this repository for a design wind pressure keyed to an operational area. |
| **person crowding moment** | **M_P = N·w·b·cos θ /1000**, 4 persons/m², standing CG 1 m above deck, seated 300 mm above seat; or **M_p = W·B_p/6** (USCG) | **YES, fully, and triple-attested.** |
| **design categories A/B/C/D** | the categories themselves come from the RCD (`EU-REGULATORY.md` §2.2). What the national codes add free is the **MAPPING**: NSCV C3 Table 5 (operational area ↔ ISO category) and MCA Table 12A.2.5 (area category ↔ ISO category) | **PARTIAL and CONTESTED.** Two free mappings exist and **they disagree** — AMSA reaches ISO A and D, the MCA uses only B and C. Neither is a definition of the categories. |
| **buoyancy / flotation after swamping** | 33 CFR 183.105 (2/15 persons capacity + 25 % dead weight + 62.4×air-chamber volume, 18 h submerged); TP 1332 §4.4 (NOT READ); NSCV Subsection 6B (NOT READ); NZ App. 1 cl. 1.1(6) (reserve buoyancy with the cockpit full) | **PARTIAL, and the recreational-boat rules are for boats smaller than our band.** |

**Net:** the free national corpus replaces **most** of ISO 12217-1's stability
job — the GZ criteria, all three heeling moments, the wind pressures and the
offset-load test are free, binding and cross-corroborated. What it does NOT
supply is **a design-category-keyed GM floor**, **an angle of vanishing
stability**, **a downflooding HEIGHT**, and **any length-dependent offset-load
heel limit**. And it cannot supply the one thing the RCD's Art. 20(1)(b)(i)
attaches to ISO 12217 compliance — the presumption of conformity that keeps a
category C craft under 12 m on Module A (`EU-REGULATORY.md` §2.6, §3.5). **A
free national criterion can inform our physics; it cannot buy the EU
conformity route.**

### 10.3 The three highest-value free sources, ranked

1. **USL Code Section 5G "Design Loading" + Section 5M Part 4** (Australia,
   AMSA-hosted, scanned). The only free closed-form pressure → plywood-thickness
   chain found. ⚠ scanned; ⚠ "not the official version"; ⚠ possibly superseded
   for plywood by NSCV C3.
2. **NSCV Part C Subsection 6A** (Australia, CC-BY 4.0, text layer). The most
   complete free stability code: criteria, three heeling moments, wind pressure
   table, freeboard prerequisite, offset-load test, catamaran criteria.
3. **MCA Workboat Code Edition 3** (UK, binding, text layer). Free freeboard
   table, offset-load test, full GZ criteria, and the ISO-12217-category
   mapping — plus the epistemically interesting GM penalty for an estimated
   displacement.

### 10.4 Leads NOT followed, in priority order

1. **Nordic Boat Standard** — named by Transport Canada's TP 1332 information
   note as a suitable standard *"for commercial vessels less than 15 m"*, which
   is precisely this project's band. Free status UNKNOWN, content UNREAD.
   **Highest-value unexplored lead in this survey.**
2. **USL 5M clauses M.43 and M.47** (hull stiffening, stringers) — the plywood
   stiffener section modulus is almost certainly there, and the pages are
   already rendered at `downloads/standards/national/usl5m_png/`.
3. **USL 5G Figure 5** (F_L, longitudinal load distribution factor) — needed to
   close the planing-hull chain for longitudinals; page not read.
4. **NSCV Part C Subsection 6B** (buoyancy and stability after flooding) and
   **6C** (stability tests, hydrostatics, freeboard measurement) — both free,
   both CC-BY, both unread.
5. **Transport Canada TP 7301** (Stability, Subdivision and Load Line Standards)
   and **TP 1332 §4.4** (flotation).
6. **NSCV C6A Annexes D–H, J, K** and **Chapter 8** (simplified criteria for
   special operations).
7. USCG NVICs; 46 CFR Subchapter S (Parts 170/171) in full.

### 10.5 Nothing in this file contradicts `docs/research/EU-REGULATORY.md`

Checked deliberately. The one place a contradiction could have arisen — the
design-category wave heights and wind forces — is **consistent**: NSCV C3
Table 5's additional conditions give 4 m / 2 m significant wave height for ISO
B / C, matching RCD Annex I A §1 exactly, and 6 Bft for C matching exactly.
The single numeric difference is **7 Beaufort for category B in AMSA's table
against the RCD's 8**, and it is not a contradiction: AMSA states it as an extra
restriction imposed when downgrading an operational area, not as a definition of
category B. Two further findings SUPPORT the EU file rather than contradicting
it: its §4.5 conclusion that no free source supplies a design-category GM floor
survives contact with four more national codes (§10.2 above), and its §3.4
finding that a calculation route to structural conformity is legitimate is
reinforced by five national instruments (§10.1, last row) — three of them
binding regulation rather than guidance.

The one genuinely NEW caution this file raises against the EU file's framing is
**MCA Workboat Code footnote 14**: *"ISO 12215-5 should be used with caution
where the vessel's hull or superstructure is fabricated of fibre reinforced
plastic, or where the vessel is subject to impact loading from …"* (truncated).
`EU-REGULATORY.md` treats ISO 12215-5 purely as a purchase decision; a binding
national code publishes a technical reservation about it. **That belongs in any
future purchase discussion and it is not recorded anywhere else in this tree.**

---

**STATUS AT END OF THIS PASS: IN PROGRESS.** Australia (NSCV C3, C6A, USL 5B,
5G, 5K, 5M), the UK (Workboat Code 3), Canada (TP 1332), the USA (46 CFR 177,
178; 33 CFR 183) and New Zealand (Part 40A) have been read to the depth recorded
above. **"Any EU member state national code with free scantling content" was NOT
REACHED** — priority 6 in the brief, and the budget was spent on priorities 1–5.
The unread items are enumerated in §10.4.
