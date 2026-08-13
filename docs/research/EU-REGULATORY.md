# EU REGULATORY TEXTS — what the free documents give us, and where they stop

**Read 2026-08-13.** Eight PDFs in `downloads/standards/` (gitignored —
`.gitignore:7` matches `downloads/`, verified with `git check-ignore -v`). This
file records what was MEASURED in them: what each contains, what is quotable,
what is implementable, and — the load-bearing part — **the exact boundary past
which a paid ISO standard is still required.**

**THE ONE-LINE ANSWER.** The free texts state REQUIREMENTS; the paid standards
state NUMBERS. That is not an accident of this document set, it is the New
Approach's design: RCD Art. 14 makes a harmonised standard a *presumption*
route, so the Directive is drafted so as not to restate what the standard says.
Consequently **none of our three unconfirmed rules (R-GM, R-PBM, R-TBM) can be
closed from these documents**, and Gate 6R's single remaining edition defect is
untouched by all eight of them.

What the free texts DO give is real and not small: several thresholds that are
currently ours or absent, a legally-keyed conformity-route table that tells us
which SKUs have a self-certification route at all, the first citable source this
repository has ever had for the design-category wave heights, the first citable
source of any kind in the electrical/battery domain — and, in ES-TRIN, a
*binding* 20 kWh lithium threshold with a closed-form ventilation formula behind
it.

## ⚠ READ THIS BEFORE TOUCHING `review.py` — the trap this review found

The RCD application guide hands us, for free, the dated edition strings of the
harmonised standards: **`EN ISO 12215-5:2019`** and **`EN ISO 12217-1:2017`**
(§3.1). `review.REVIEW["editions"]["ISO 12215-5"]` is the single placeholder
holding Gate 6R RED, `edition_defects()` only checks that the string names a
year, and typing `"ISO 12215-5:2019"` into it would flip Gate 6R **GREEN
without anybody having read one word of ISO 12215-5.**

**DO NOT DO THAT.** Gate 6R's bar is *"the DATED edition the reviewer HELD"*,
not "the edition that exists". Knowing a standard's edition number is not
holding its text, and `review.py`'s own reasons for R-PBM and R-TBM say so:
*"there is no 12215-5 text to have confirmed them against."* Writing the string
in would be defect class 1 from `docs/LESSONS.md` — an unmeasurable value scored
as a passing one — committed against the very gate that exists to prevent it,
using a number this document handed over.

The same guide creates a second, quieter problem, and it is a real one:
**`review.py` records `ISO 12217-1:2015 (Third edition, 2015-10-15)`, and the
harmonised edition is `EN ISO 12217-1:2017`.** R-DFH and R-OLH were confirmed
against a SUPERSEDED edition. Gate 6R does not catch this, because its bar is
attributability, not currency — and that is a finding about the gate's scope,
recorded in §7.5, not a reason to soften anything.

---

## 0 · How to read this file, and what it is not

- **It carries no status.** Gate state is `python -m navalai.gates`; outstanding
  work is `python scripts/reconcile_gaps.py`; the purchase list is
  `navalai.refdata.PURCHASE_QUEUE`. §9 proposes a reordering of that tuple; it
  does not restate it.
- **Nothing here is implemented.** `navalai/rules/**` and `navalai/refdata/**`
  were read-only for this work. Every "implementable" note is a REPORT.
- **Every number below was read in the text layer of the named PDF at the named
  page.** Where a page had no text layer, or a table came out garbled, that is
  said and the content is left UNREAD rather than reconstructed. Search
  "COULD NOT VERIFY".
- **PDF page vs printed page.** Citations give the PDF page and, where the
  document's own numbering differs, the printed or OJ page too.
- **Tooling.** `pdftoppm`/poppler is not installed on this machine, so the Read
  tool cannot open a PDF here at all. Text was extracted with `pypdf` from
  `~/.venvs/naval`. If a future session needs the *images* (several tables in
  SAFEMASS and one EMSA annex are raster-only, noted below), poppler must be
  installed first.

---

## 1 · The eight documents, and what each is worth

| document | what it actually is | legal status | worth to us |
|---|---|---|---|
| `CELEX_32013L0053_EN_TXT.pdf` | Directive 2013/53/EU (RCD), OJ L 354, 28.12.2013, p. 90 | **binding EU law** | **HIGH** — §2. Design categories, conformity-route table, four length-keyed rules |
| `GUIDE2024r1 RCD 2013_53_EU 240118.pdf` | Commission RCD application guide, rev. 1, 2024-01-18 | non-binding interpretation | §3 |
| `ES_TRIN_2025_signed_en.pdf` | CESNI European Standard for inland navigation vessels | referenced by Directive (EU) 2016/1629 → binding for in-scope inland craft | §4 |
| `ES-QIN_2024_signed_en.pdf` | CESNI standard for qualifications in inland navigation | binding via 2017/2397 | §4.4 — **crew, not vessel** |
| `EMSA Battery Guidance_v1.0.pdf` | EMSA guidance on BESS safety on ships, v1.0, Nov 2023 | **explicitly non-binding** | **MEDIUM** — §5. First electrical source in this tree |
| `SAFEMASS Part 1.pdf` / `Part 2.pdf` | DNV GL study for EMSA, 2020-03-25 | consultancy study; "no third party may rely on its contents" | **NIL** — §6.1 |
| `EN- Guide pour une plaisance responsable.pdf` | The SeaCleaners / EBI awareness booklet | none | **NIL** — §6.2 |

Two of the eight yield nothing implementable, and saying so precisely is part of
the deliverable — see §6. The duplicate `CELEX%3A...` file is byte-identical to
`CELEX_32013L0053_EN_TXT.pdf` (same 1089185 bytes); read one.

---

## 2 · Directive 2013/53/EU (RCD) — the binding text

This is the only *binding* document in the set that governs our recreational
SKUs, and it is the highest-value one. 42 PDF pages; OJ pagination L 354/90 to
L 354/131. Read in full.

### 2.1 Scope, and the two exemptions that matter operationally

Art. 3(2), PDF p. 7 (OJ L 354/95):

> "'recreational craft' means any watercraft of any type, excluding personal
> watercraft, intended for sports and leisure purposes **of hull length from
> 2,5 m to 24 m**, regardless of the means of propulsion"

Art. 2(2)(a), PDF pp. 6–7, excludes from the Part A design-and-construction
requirements — quoted because two of these are live options for this project:

> "(vi) experimental watercraft, provided that they are not placed on the Union
> market;
> (vii) watercraft built for own use, provided that they are not subsequently
> placed on the Union market during a period of five years from the putting
> into service of the watercraft;"

and "(viii) watercraft specifically intended to be crewed and to carry
passengers for commercial purposes … regardless of the number of passengers".
Art. 2(3) adds that charter or sports-and-leisure training use does not by
itself remove a craft from the Directive.

### 2.2 THE DESIGN CATEGORIES — free, verbatim, and it confirms our table

Annex I Part A §1, PDF p. 25 (OJ L 354/114). Transcribed exactly:

| Design category | Wind force (Beaufort scale) | Significant wave height (H⅓, metres) |
|---|---|---|
| A | exceeding 8 | exceeding 4 |
| B | up to, and including, 8 | up to, and including, 4 |
| C | up to, and including, 6 | up to, and including, 2 |
| D | up to, and including, 4 | up to, and including, 0,3 |

with explanatory note D adding: "significant wave height up to, and including,
0,3 m, **with occasional waves of 0,5 m maximum height**."

**This is the most immediately useful paragraph in the whole document set.**
`limits.CATEGORY_TABLE` column 1 holds `A 4.0 / B 4.0 / C 2.0 / D 0.3` and
`rules/iso12217.py` emits it as R-CAT with
`clause="ISO 12217-1 §5 (design categories)"`. Every one of those four numbers
appears verbatim in a **free, binding** text, and so does the A-vs-B sense
distinction that `review.REVIEW["interpretations"]["R-CAT"]` currently records
as an unresolvable ambiguity of the stored scalar. The Directive states it
plainly: A is a lower bound ("exceeding"), B an upper bound ("up to, and
including"). R-CAT's provenance therefore does not need ISO 12217-1 at all.

Note also the closing sentence of §1, which is the RCD's own statement of what
the categories are FOR:

> "Watercraft in each design category must be designed and constructed to
> withstand the parameters in respect of stability, buoyancy, and other relevant
> essential requirements listed in this Annex, and to have good handling
> characteristics."

That is a requirement with no number, and §2.4 below is where that matters.

### 2.3 The essential requirements that DO carry a number

Four, and only four, in Part A. All are length- or category-keyed and all are
computable from what the ladder already holds.

**Annex I A 3.3, buoyancy and flotation** — PDF p. 26 (OJ L 354/115):

> "All habitable multihull recreational craft susceptible of inversion shall
> have sufficient buoyancy to remain afloat in the inverted position.
>
> Watercraft of **less than 6 metres in length** that are susceptible to
> swamping when used in their design category shall be provided with
> appropriate means of flotation in the swamped condition."

**Annex I A 3.7, life raft stowage** — PDF p. 27 (OJ L 354/116):

> "All recreational craft of design **categories A and B**, and recreational
> craft of design categories **C and D longer than 6 metres** shall be provided
> with one or more stowage points for a life raft (life rafts) large enough to
> hold the number of persons the recreational craft was designed to carry as
> recommended by the manufacturer. Life raft stowage point(s) shall be readily
> accessible at all times."

**Annex I A 5.1.4, start-in-gear protection** — PDF p. 28 (OJ L 354/117):
exempts outboards producing "less than 500 Newton's (N) of static thrust", or
with a throttle limiter to 500 N at starting. Not applicable to our SKUs; noted
so nobody re-derives it.

**Annex I C 1.1–1.3, noise** — PDF p. 34 (OJ L 354/123): a table of sound
pressure limits (67 / 72 / 75 dB by rated engine power bands ≤10, 10–40, >40 kW,
+3 dB allowance for multi-engine) and a deemed-to-comply alternative at
**Fn ≤ 1,1 and power/displacement ≤ 40**, with

> "'Froude number' Fn shall be calculated by dividing the maximum recreational
> craft speed V (m/s) by the square root of the waterline length lwl (m)
> multiplied by a given gravitational acceleration constant, **g, of 9,8 m/s²**."

**Part C DOES NOT APPLY TO US and this is a trap worth naming.** Its own
applicability sentence limits it to "Recreational craft with inboard or stern
drive engines without integral exhaust, personal watercraft and outboard engines
and stern drive engines with integral exhaust". A solar-electric craft has none
of those. If anyone implements this Fn formula anyway they will have introduced
a *second* gravitational constant (9,8 against the project's own) for a rule
that does not apply — the number-declared-twice defect, imported from a statute.

### 2.4 The essential requirements that carry NO number — this is the boundary

Verbatim, Annex I Part A, PDF pp. 26–27 (OJ L 354/115):

> "**3.1. Structure.** The choice and combination of materials and its
> construction shall ensure that the watercraft is strong enough in all
> respects. Special attention shall be paid to the design category … and the
> manufacturer's maximum recommended load…"
>
> "**3.2. Stability and freeboard.** The watercraft shall have sufficient
> stability and freeboard considering its design category … and the
> manufacturer's maximum recommended load…"
>
> "**3.6. Manufacturer's maximum recommended load.** The manufacturer's maximum
> recommended load (fuel, water, provisions, miscellaneous equipment and people
> (in kilograms)) for which the watercraft was designed, shall be determined in
> accordance with the design category (Section 1), stability and freeboard
> (point 3.2) and buoyancy and flotation (point 3.3)."

"Strong enough in all respects" is the entire scantling requirement. "Sufficient
stability and freeboard" is the entire stability requirement. **There is no GM,
no heel angle, no downflooding height, no design pressure, no panel thickness,
no σ_d, no k2, no kC anywhere in the Directive.** A keyword sweep of the full
42-page text for `12217`, `12215`, `8666`, `ISO` returns exactly three hits, all
about engine emissions test cycles (ISO 8178-4:2007, Annex I B 2.3, PDF p. 31).
**The Directive names no stability standard and no scantling standard at all.**

### 2.5 Article 3(10) — the measurand we do not hold, and nobody logged it

Art. 3(10), PDF p. 8 (OJ L 354/96):

> "'hull length' means the length of the hull **measured in accordance with the
> harmonised standard**"

The Directive defines every other term itself and defers this one. Hull length
then decides, in the free text alone: RCD scope (2,5–24 m, Art. 3(2)); the
swamped-flotation rule (<6 m, A 3.3); the life-raft rule (>6 m, A 3.7); and the
entire conformity-route table (§2.6). It also decides `iso12217.R-SCP` (≥6 m)
and `iso12217.offset_load_heel_limit_deg(LH)`, which is a **cubic** in LH — so a
measurement error there is cubed.

**The harmonised standard for this is ISO 8666 (small craft — principal data),
we do not hold it, and it is in neither `PURCHASE_QUEUE` nor `refdata.absent()`.**
`iso12217.hull_length_m()` documents its substitution of L_WL for L_H and argues
the error is in the refusing direction, which is careful and right for the ISO
scope test — but the RCD's 6 m rules cut BOTH ways (A 3.3 applies *below* 6 m,
A 3.7 *above* it), so understating length flips one of them to the unsafe side.
This is the one genuinely new absence this review found in a quantity we already
depend on. See §9.

### 2.6 Article 20 — the conformity-route table, and the finding that reframes the ISO purchase

Art. 20(1), PDF pp. 13–14 (OJ L 354/102–103). This IS a decision table, keyed by
(design category, hull length), and it is free:

| category | hull length | permitted modules |
|---|---|---|
| A, B | 2,5 m – <12 m | A1, B+(C/D/E/F), G, H |
| A, B | 12 m – 24 m | B+(C/D/E/F), G, H |
| C | 2,5 m – <12 m | **where the harmonised standards relating to Annex I A 3.2 and 3.3 are complied with:** A, A1, B+(C/D/E/F), G, H |
| C | 2,5 m – <12 m | **where they are NOT complied with:** A1, B+(C/D/E/F), G, H |
| C | 12 m – 24 m | B+(C/D/E/F), G, H |
| D | 2,5 m – 24 m | A, A1, B+(C/D/E/F), G, H |

**Module A — internal production control, the only route with no notified-body
involvement at all — is available in exactly two cells: category D at any length
up to 24 m, and category C under 12 m ONLY IF the harmonised standards for
stability/freeboard (3.2) and buoyancy/flotation (3.3) are complied with.**

Quoted verbatim from Art. 20(1)(b)(i), PDF p. 14:

> "— where the harmonised standards relating to points 3.2 and 3.3 of Part A of
> Annex I are complied with: Module A (internal production control), Module A1
> …;
> — where the harmonised standards relating to points 3.2 and 3.3 of Part A of
> Annex I are not complied with: Module A1 (internal production control plus
> supervised product testing), Module B …"

**This is the strongest argument in the whole review for buying ISO 12217, and
it is an argument the project did not previously have.** Until now the case for
12217-1 was "it closes half of Gate 6R" — a documentation gate. Art. 20(1)(b)(i)
makes it a *product* gate: for a category C craft under 12 m (which is most of
the SKU range), whether the cheapest legal conformity route exists at all turns
on compliance with the harmonised stability/buoyancy standards. Without them the
manufacturer drops to Module A1 and a notified body enters the process.

### 2.7 Annex VI — "equivalent calculation" is explicitly a permitted route

PDF p. 39 (OJ L 354/128), the supplementary requirements when Module A1 is used:

> "On one or several watercrafts representing the production of the manufacturer
> one or more of the following **tests, equivalent calculation or control** shall
> be carried out by the manufacturer or on his behalf:
> (a) test of stability in accordance with point 3.2 of Part A of Annex I;
> (b) test of buoyancy characteristics in accordance with point 3.3 of Part A of
> Annex I."

Together with Art. 14 — PDF p. 12 (OJ L 354/101) — "Products which are in
conformity with harmonised standards or parts thereof the references of which
have been published in the *Official Journal of the European Union* **shall be
presumed** to be in conformity with the requirements covered by those standards
or parts thereof, set out in Article 4(1) and Annex I", the legal architecture
is: the harmonised standard is a *presumption* route and not the only one, and
calculation is expressly admitted in place of physical test under A1. **So this
project's computed physics is not legally excluded from a conformity argument.**
What it cannot do is *presume* conformity — that presumption is what the ISO
purchase buys, and Art. 20(1)(b)(i) attaches Module A to it specifically. Do not
overread this paragraph: "equivalent calculation" under A1 is performed under a
notified body's supervision, and A1 is precisely the module a category C craft
falls back to when the harmonised standards are *not* met.

### 2.8 The RCD's only electrical clause, and it has no numbers

Annex I A 5.3, PDF p. 28 (OJ L 354/117), quoted in full because it is the
entirety of EU recreational-craft electrical law:

> "**5.3. Electrical system.** Electrical systems shall be designed and installed
> so as to ensure proper operation of the watercraft under normal conditions of
> use and shall be such as to minimise risk of fire and electric shock.
>
> All electrical circuits, except engine starting circuits supplied from
> batteries, shall remain safe when exposed to overload.
>
> **Electric propulsion circuits shall not interact with other circuits in such
> a way that either would fail to operate as intended.**
>
> **Ventilation shall be provided to prevent the accumulation of explosive gases
> which might be emitted from batteries. Batteries shall be firmly secured and
> protected from ingress of water.**"

Note the drafting tension worth knowing: Art. 3(5) defines "'propulsion engine'
means any **spark or compression ignition, internal combustion** engine", so a
solar-electric craft has no "propulsion engine" and Annex I Parts B (exhaust)
and C (noise) do not reach it — yet Annex I A 5.3 explicitly contemplates
"electric propulsion circuits". Recital (8) (PDF p. 2) says the definition
"should be extended to also cover innovative propulsion solutions", which the
enacted Art. 3(5) does not do. **Read the enacted definition, not the recital.**

Four requirements, zero numbers: no ventilation rate, no battery-securing load
case, no separation distance, no IP rating. §5 is where those partly come from.

### 2.9 Other Part A content that is implementable as a documentation/arrangement check

- **A 2.2, builder's plate** (PDF pp. 25–26): must carry manufacturer contact,
  CE marking, "watercraft design category in accordance with Section 1",
  "manufacturer's maximum recommended load derived from point 3.6 **excluding
  the weight of the contents of the fixed tanks when full**", and the number of
  persons. A precise content list and one precise definitional exclusion.
- **A 2.1, watercraft identification number**: five fields (country code,
  manufacturer code, serial, month/year of production, model year), with
  "Detailed requirements … are set out in the relevant harmonised standard" —
  the same deferral as hull length.
- **A 2.3**: "Means of reboarding shall be accessible to or deployable by a
  person in the water unaided." Claim-level only; the dimensions are ABYC H-41,
  already logged in `refdata.absent()['ergonomics.abyc_h41_dimensions']`.
- **A 3.4** openings, **A 3.5** flooding, **A 3.8** escape, **A 3.9** anchoring
  strong points: requirements, no numbers.
- **A 5.7**: navigation lights/shapes/sound signals "shall comply with the 1972
  COLREG … or **CEVNI** (European Code for Interior Navigations for inland
  waterways) … as appropriate" — the RCD's one hook to the inland regime.
- **Annex II** lists the five components regulated separately; none is ours.
- **Annex V** (post-construction assessment, Module PCA) requires a notified
  body to "examine the individual product and carry out calculations, tests and
  other assessments" — a route for a craft whose manufacturer never assumed
  conformity, which is what a "built for own use" boat later sold becomes.

---

## 3 · The RCD application guide (RSG GUIDELINES 2024, rev. 1, 2024-01-18)

338 pages; the printed "Page N of 338" matches the PDF page index 1:1, so page
cites are both. **Prepared by the Recreational Craft Sectoral Group (RSG), not
by the Commission**, and it says what that is worth on p. 4:

> "This document has been prepared for guidance only and does not replace the
> official documents (Directive and Decisons/Regulations) nor does it have any
> official or legal meaning."

**A tooling warning that determines whether anyone else finds this content: the
Annex ZA harmonised-standards tables have NO TEXT LAYER — they are raster
images.** `extract_text()` on p. 220 returns only "Annex ZA … is reported in the
table below" and then nothing. Grepping the text layer for `12217` finds a
heading and would lead a reader to conclude there is no mapping table. There is
one; it is a picture. Everything transcribed in §3.1 below came from extracting
the embedded images with `pypdf` and viewing them as PNGs.

### 3.1 THE DATED EDITIONS — the single highest-value fact in the document set

Part 5, pp. 199–267, one page per standard. Verbatim from the page headings:

| standard, verbatim | page |
|---|---|
| **EN ISO 12215-5:2019** — Hull construction and scantlings, Part 5: design pressures for monohulls | 220 |
| **EN ISO 12217-1:2017** — Stability and buoyancy assessment and categorization, Part 1: non-sailing | 225 |
| **EN ISO 12217-2:2017** — Part 2: sailing | 226 |
| **EN ISO 12217-3:2017** — Part 3: boats of hull length less than 6 m | 227 |
| **EN ISO 8666:2020 + /A11:2021** — principal data | 259 |
| **EN ISO 16315:2016** — electric propulsion system | 244 |
| EN ISO 12215-1/-2/-3/-4/-6/-8/-9 : 2018 | 216–223 |
| EN ISO 14945:2021 (builder's plate) · EN ISO 14946:2021 (maximum load capacity) | 234, 235 |
| EN ISO 10133:2017 (ELV DC) · EN ISO 13297:2018 (AC) · EN 60092-507:2015 | 206, 228, 201 |

Three consequences, and each one moves something:

1. **`ISO 12215-5:2019` is the edition, and knowing that is NOT holding it.**
   See the warning at the top of this file. This is the number that could flip
   Gate 6R green fraudulently, and it must not be typed into `review.py`.
2. **The harmonised 12217-1 is the 2017 edition; we hold 2015.** R-DFH and
   R-OLH were confirmed against a superseded text. §7.5.
3. **`ISO 12215-7` is NOT in the harmonised list at all** — multihull
   scantlings is absent from it. The `PURCHASE_QUEUE` row for 12215-7 is not
   thereby wrong (it blocks a catamaran SKU on engineering grounds), but it
   cannot be justified as "the harmonised standard for a catamaran", because
   the guide's list does not contain one.

**Encode the caveat with the numbers.** This is a 2024-01-18 snapshot in a
document with no legal force, and it points elsewhere for the authoritative
list (p. 4): *"The list of harmonised standards in support of the RCD is
available on the RSG website www.rsg.be."* The legally operative list is the
OJEU citation. **UNVERIFIED: whether the OJEU currently cites these editions.**
"The RSG guide says 12217-1:2017" is strong evidence, not proof.

Note also that `PURCHASE_QUEUE` row 1 names **"ISO 12217-1:2022"** — an edition
no document in this set corroborates. The harmonised one is 2017, and ERFU
#188r1 (p. 329) says a revision was still pending: *"The revised 12217 series
will be published when dated referenced documents are published (Late 2022)."*

### 3.2 The ER → clause maps, which tell us exactly which clause to buy for

From the Annex ZA images. **EN ISO 12215-5:2019 (p. 220)** has only two ER rows:

- `Annex I Part A 2.5 Owner's Manual` → clause 13 except 13.4, A.7.4
- `Annex I Part A 3.1 Structure` → **"All clauses except Clause 12 and Annex J"**,
  remark: *"This document provides a means of demonstrating conformity with this
  requirement for recreational craft as defined in Article 3(2) of Directive
  2013/53/EU to 24m hull length (L_H) only."*

**EN ISO 12217-1:2017 (p. 225)**: `I.A.1 Watercraft Design Categories` →
clauses 5, 6, 7, Annex I; `3.2 Stability and Freeboard` → clauses 5, 6 +
Annexes A–E; `3.3 Buoyancy and flotation` → 6.6, 6.8 + Annexes F, G;
`3.5 Flooding` → clause 6 + Annexes A–D; `3.6 Maximum recommended load` →
clause 5; `3.8 Escape` → 6.6; `2.5 Owner's manual` → Annex H. All three 12217
ZA tables carry: *"Design categories A, B, C and D defined in this standard
correspond to design categories A, B, C and D of Directive 2013/53/EU."*

That last sentence is the formal statement of what §2.2 shows: the categories
originate in the Directive, and ISO transcribes them.

### 3.3 The guide states NO number for stability, buoyancy, freeboard, downflooding or scantlings

It reproduces Annex I qualitatively — "strong enough in all respects" (3.1,
p. 80), "sufficient stability and freeboard" (3.2, p. 81) — and never
quantifies. **The clearest single illustration is ERFU #185r1 (pp. 325–326)**,
four pages resolving a hard geometric question about downflooding at a topside
door. When it finally needs the height it writes:

> "the lowest part of the door is above **50% of the minimum downflooding height
> required by clause 6.1.2** above the loaded waterline"

A ratio and an ISO clause number. Never the metre value. That is the boundary,
demonstrated by a document that plainly *would* have given the number if it
could: the guide prints exact figures elsewhere when it has them (fuel-hose test
pressures 1,4 MPa / 1,0 MPa and vacuum-collapse 80 kPa / 35 kPa, ERFU #101r3,
p. 291). **The silence on stability and scantlings is deliberate, not an
oversight.**

**The one exception that touches us — 75 kg and 37,5 kg.** ERFU #143r3 (p. 303),
quoting ISO 14946 inside a free document:

> "ISO 14945 (Builder's Plate) states that the displayed figures for the number
> of persons and load should be as defined in EN ISO 14946 (Maximum Recommended
> Load). This states that the crew limit is based upon **75kg per person** and
> that 'where children are carried as part of the crew the maximum number of
> persons may be exceeded provided that each child's mass does not surpass a
> limit of **37.5kg** and the total persons' mass is not exceeded'."

**Do not read this as a contradiction of `limits.CREW_MASS_KG = 85.0` without
checking.** They are different quantities for different purposes: 75 kg is the
ISO 14946 *builder's-plate crew limit* basis, and the ERFU explicitly says the
12217-3 child range "is for the purpose of the stability/buoyancy assessment
only". Our 85 kg is used for the offset-load heel moment. **What IS established
is that 85 kg is not the ISO 14946 figure, and if we ever emit a builder's
plate, the plate's number is 75 kg.** Which of the two governs the offset-load
test is a question only ISO 12217-1 answers, and it is on the list of things
`PURCHASE_QUEUE` row 1 says the purchase supplies.

### 3.4 Presumption of conformity is VOLUNTARY — and there is a written calculation route

Guide's own gloss, p. 4:

> "It should be noted that Article 14 of the Directive **recommends** the use of
> harmonised standards as this ensures presumption of conformity … **The use of
> harmonised standards is voluntary.** A Notified Body has the necessary
> technical competence for the conformity assessment. The lack of harmonised
> standards does not exclude important essential requirements for assessment."

**RSG Comment n.7 on ER 3.1 Structure (p. 79) — four accepted approaches, and
only the first is ISO 12215:**

> "1. Application of appropriate parts of EN ISO 12215 …
> 2. The structural requirements of the hull may be assessed by **other
> acceptable scantling determination methods** that are applicable to the boat
> type, design category and the Manufacturer's maximum recommended load.
> Appropriate documentation shall be kept.
> 3. As an alternative to acceptable scantlings determination methods or in
> cases where no applicable rules exist, **acceptable construction
> calculation(s) or testing may be used**. Calculations and proof of testing
> shall be documented.
> 4. In particular cases and if acceptable **empirical knowledge** can be
> demonstrated as to the structural requirements of the hull, this may be
> used…"

It then specifies what the documentation must contain for the calculation
route: *"Reference to applied calculation method (loads, materials, geometry,
analysis principle)"*, *"Evaluation and statement of the applicability of the
method for assessment"*, *"Input and output calculation results on the different
structural members."*

**This is an endorsed conformity route for computed physics on ER 3.1, without
ISO 12215-5.** It is the strongest single result of this review for the
project's own method. Two limits attach:

- ERFU #168r1 (p. 316): the calculations are **mandatory in the technical
  file** — *"the Notified Body may produce calculations for verification in the
  assessment but they cannot become part of the manufacturer's technical file."*
  Likewise righting/stability curves (p. 315).
- Module A and A1 documentation (pp. 129, 133) require *"descriptions of the
  solutions adopted to meet the essential requirements … where those harmonised
  standards have not been applied"* — the machinery anticipates non-application.

### 3.5 Where a notified body is unavoidable — and the finding that inverts the ISO case

The guide reproduces Art. 20(1) (pp. 42–43); §2.6 above has the table. What the
guide adds is decisive:

- **Module A (p. 129) is pure self-certification** — *"the manufacturer … ensures
  and declares on his sole responsibility"*. No notified body appears anywhere
  in it.
- **Module A1 ALWAYS involves a notified body for the RCD.** The generic Module
  A1 text allows *"either by an accredited inhouse body or under the
  responsibility of a notified body"* — but Art. 24(3) (p. 47) strikes the
  in-house option out: *"The possibility of using accredited in-house bodies
  referred to in Modules A1 and C1 … shall not be applicable."* RSG Comment
  n.25 (p. 134) confirms the deletion.

Therefore, stated precisely, per SKU:

- **Category D, 2,5–24 m:** Module A is available **unconditionally**. With
  RSG Comment n.7's calculation route and Annex VI's "equivalent calculation",
  an own-physics conformity file is a legally coherent route.
- **Category C under 12 m:** Module A is available **only if the harmonised
  standards for ER 3.2 and 3.3 are complied with**. Assessing stability by our
  own method drops us to A1 → **notified body mandatory**. For category C, our
  physics does not replace the ISO purchase; **it replaces it with a notified
  body, which is more expensive.**
- **Categories A and B at any length, and category C ≥ 12 m:** notified body
  regardless. Module A never appears.

And the asymmetry that matters most: **the Art. 20 conditional names 3.2 and
3.3 only — not 3.1.** On its face ISO 12215-5 compliance is *not* a
precondition for Module A, while ISO 12217 compliance is. Read together with
RSG Comment n.7 that gives a coherent posture — **scantlings by our own
calculation, stability by ISO 12217.** Flagged as a reading of two provisions
together, not something the guide states in those words; confirm with a
notified body before relying on it.

### 3.6 Solar-electric propulsion — in scope for Part A, out of scope for B and C

Art. 3(5) (p. 26) defines a propulsion engine as internal-combustion only, so
an electric motor is not one. Part B (exhaust) never engages. Part C (noise) is
scoped by Art. 22 (p. 45) to stern-drive/inboard propulsion engines, PWC and
outboards — no trigger. **Annex I Part A applies in full**, and Art. 3(2)'s
*"regardless of the means of propulsion"* puts it beyond doubt.

**ERFU #165r2 (pp. 313–314)** is the RSG's dedicated treatment. It names the
architectures (ICE, hybrid, diesel-electric, dual source, full electric), notes
that an electrical power source *"can be a battery of accumulators, **a solar
panel array**, any other alternative energy electrical source or
supercapacitors"*, and rules:

> "Q1 – Can it be considered 'electrical propulsion' every time an electric
> motor is mechanically connected to the propeller(s)? **1 - Yes**
> Q2 – How total power of craft is to be determined? **2 - The certificate
> should state the maximum power that can be delivered to the propeller(s) at
> any time.**"

### 3.7 Battery and lithium rulings — three that touch code we already have

**ERFU #169r2 (p. 316), battery mass accounting:**

> "• **Batteries that are an integral part of an electric motor shall be
> considered as a part of the motor.**
> • **Batteries serving for propulsion only and not connected to any other
> circuit of the watercraft (including charging) shall be considered as part of
> the maximum load.**
> Note: **any battery connected to the watercraft's electrical installation
> shall be included in the mass of the light craft.**"

A solar-electric traction pack is connected to its charging circuit, so it goes
in **light craft mass**, not maximum load. **CHECKED, and we are on the right
side of this:** `energy.weight_budget` computes
`total = structure + battery + panels + outfit + payload_kg` with `battery` as
its own item and *not* inside `payload_kg` (`navalai/energy.py:83–96`). Recorded
because a passing check is worth as much as a failing one when it was in doubt.

**RFU #192r1 (p. 331), lithium fire-fighting — note the admission:**

> "there are no fire extinguishing systems (yet) that could extinguish a possible
> fire caused by these batteries. … **'Fire-fighting equipment' is therefore
> understood to mean all measures and devices which prevent the battery
> exceeding safe operating limits as specified by the battery manufacturer.**
> RSG recommends the application of **ISO/TS 23625** as a minimum."

So for ER 5.6.2 the compliance target on a lithium craft is reinterpreted from
extinguishing to *prevention* — i.e. BMS and operating limits. ISO/TS 23625 is a
technical specification, **not** a harmonised standard, so it carries no
presumption of conformity. UNVERIFIED: its content; we do not hold it.

**RFU #199r1 (p. 335):** replacing a non-lithium pack with lithium on a
CE-marked craft **is** a "major craft conversion" under Art. 3(7) — re-assessment
required.

**EN ISO 16315:2016 Annex ZA (p. 244)** maps ER 5.3 clause by clause, e.g.
`8.1` ↔ *"Batteries shall be firmly secured and protected from ingress of
water"*, `4.1, 8.5, Annex B(a)` ↔ the battery-ventilation sentence. **That map
is the shape an electrical rules module would take, and 16315 is the standard it
would need.**

### 3.8 A live standards conflict the guide reports against itself

ERFU #188r1 (pp. 328–329): EN ISO 14945:2021 and 14946:2021 *"no longer account
for the mass of manufacturer supplied optional equipment and fittings"*, while
*"In the published ISO 12217:2015 worksheets, the 'mass for optional equipment
and fittings not included in the basic outfit' are part of the maximum load."*
RSG's interim ruling is to exclude optional equipment from the plate figure and
include an allowance in `mLDC` — **and it attaches the disclaimer that
*"this paper does not provide the presumption of conformity to EN ISO 14945:2021
… and EN ISO 14946:2021"*.**

**So `mMBP ≠ mLDC`, and the two published standards are mutually inconsistent
right now.** `rules/iso12215.assess(mldc_kg, ...)` carries one mass quantity. If
a builder's plate is ever emitted from the same number, that conflates two
things the guide says are different. Not a defect today — nothing emits a plate
— but it is a trap sitting in front of the manufacturing export.

---

## 4 · ES-TRIN 2025/1 and ES-QIN 2024/1

578 PDF pages; **printed page N = PDF page N + 12**, constant, verified footer
by footer. 566 printed pages. `estrin.py`'s docstring says "a 558-page
standard" — that was the 2023/1 figure and is stale.

**The edition is `Edition 2025/1`** (cover, every footer, and the PDF `/Title`
metadata). **UNVERIFIED: its entry-into-force date.** There is no foreword,
preamble or adopting resolution in this PDF; the body starts at Chapter 1 after
the TOC. The only CESNI resolution cited anywhere is `2024-II-2 dated 17 October
2024`, and that is the footnote for **ES-RIS**, not ES-TRIN. Do not state an
ES-TRIN 2025/1 entry-into-force date on this document's authority.

**Text-layer caveat:** the PDF's italic/symbol font is mis-mapped — italic `L`
extracts as `W`, `GM` as `GG`, and `β` as `B` in Art. 4.02(4). Only those glyph
substitutions were corrected in the quotes below. **Figures 1, 2 and 3 in
Chapter 4 are images with no text layer**, so the geometric convention Figure 1
defines for the sheer abscissa `x` is UNVERIFIED against the source.

### 4.1 Parity: every number `estrin.py` transcribes survives into 2025/1 unchanged

No article renumbered, no value changed. Printed pages in brackets.

| item | 2025/1 text | vs `estrin.py` |
|---|---|---|
| 1.01(4.16) [5] | "'length' or 'L': the maximum length of the hull in m, excluding rudder and bowsprit" | MATCHES |
| 1.01(4.2) [5] | "'safety clearance': the distance between the plane of maximum draught and the parallel plane passing through the lowest point above which the craft is no longer deemed to be watertight" | MATCHES |
| 1.01(4.4) [5] | "'freeboard' or 'F': … the lowest point of the gunwale or, in the absence of a gunwale, the lowest point of the upper edge of the ship's side" | MATCHES |
| **4.01(1) [17]** | "The safety clearance shall be at least **300 mm**." | MATCHES |
| **4.02(1) [17]** | "The freeboard of vessels with a continuous deck, without sheer and superstructures, shall be **150 mm**." | MATCHES |
| 4.02(2) [17] | `F = 150 (1 − α) − (β_v·Se_v + β_a·Se_a) / 15 [mm]` | MATCHES |
| 4.02(3) [17] | `α = (Σl_Sa + Σl_Sm + Σl_Sv) / L` | MATCHES |
| 4.02(4) [18] | `β_v = 1 − 3·l_Sv/L`, `β_a = 1 − 3·l_Sa/L` | MATCHES |
| 4.02(5) [18] | S_v capped at **1000 mm**, S_a at **500 mm**, `r = 4·x/L` | MATCHES (the coefficient is named **r**, not `p`) |

Also verified because `hull_breadth_m` depends on it — **Art. 1.01(4.19) [6]**:
*"'breadth' or 'B': the maximum breadth of the hull in m, measured to the outer
edge of the shell plating (excluding paddle wheels, rub rails, and similar)"* —
MATCHES, including the shell-plating phrase. `L_WL` (4.18) and `B_WL` (4.21) are
separately defined, exactly as the module's comment claims.

One thing the module does not state: `T` is **Art. 1.01(4.23)**, *"the vertical
distance … between the lowest point of the hull **without taking into account
the keel** … and the maximum draught line"*, while `T_OA` (4.24) *includes* the
keel. Which of the two `ev.hydro.draft` is, is not recorded anywhere.

### 4.2 THE PARITY CHECK FOUND THREE MISSING CLAUSES, ALL PERMISSIVE

All three are in Art. 4.02 — the one formula the module already computes — and
all three make the required freeboard too LOW. That is the opposite of the
direction `required_freeboard_mm`'s own docstring argues a missing term must
err in.

1. **Art. 4.02(5), printed p. 19**, the sentence immediately after Figure 1:
   > "However, coefficient r will not be taken to be more than 1."

   `required_freeboard_mm` computes `p = 4.0 * x_abs / max(lwl, 1e-9)` with **no
   upper clamp**. Any hull whose sheer falls to a quarter of its peak further
   than L/4 from the extremity yields `r > 1`, inflating `Se`, inflating the
   credit, and understating required freeboard.

2. **Art. 4.02(6), printed p. 19:**
   > "If β_a·Se_a is greater than β_v·Se_v, the value of β_v·Se_v will be taken
   > as being the value for β_a·Se_a."

   The aft credit is capped at the forward credit. The module sums both
   unconditionally, so any hull with more aft sheer credit than forward
   over-credits.

3. **Art. 4.02(7), printed p. 19:**
   > "In view of the reductions referred to in (2) to (6) the freeboard shall be
   > not less than 0 mm."

   The module returns `150 - (se_v+se_a)/15` with no floor and can return a
   negative required freeboard.

A secondary ambiguity worth a code comment either way: Art. 4.02(5) locates `x`
where the sheer is `0,25 S_v` / `0,25 S_a`, and `S_v`/`S_a` are defined *as the
capped values*, while the module uses `target = 0.25 * s_raw` (uncapped) and
multiplies by the capped `s`. On a hull with >1000 mm forward sheer those are
different. The standard's wording is not unambiguous here and Figure 1, which
would settle it, has no text layer.

### 4.3 THE CHAPTER LIST IS WRONG — 33 chapters, not 20, and one title is the old edition's

1 General · 2 Procedure **(left void)** · 3 Shipbuilding requirements ·
4 Safety clearance, freeboard and draught scales · 5 Manoeuvrability ·
6 Steering system · 7 Wheelhouse · 8 Engine design · 9 Emission of gaseous and
particulate pollutants **from internal combustion engines** · 10 Electrical
equipment and installations · 11 **Special provisions applicable to electric
propulsion systems** · 12 Electronic equipment and systems **(left void)** ·
13 Equipment · 14 Safety at work stations · 15 Accommodation · 16 Fuel-fired
heating, cooking and refrigerating equipment · 17 Liquefied gas installations
**for domestic purposes** · 18 On-board sewage treatment plants · 19 Passenger
vessels · 20 Passenger sailing vessels **not navigating on the Rhine (Zone R)** ·
21 Pushed/towed convoy · 22 Floating equipment · 23 Worksite craft ·
24 Traditional craft · 25 Sea-going vessels · **26 Recreational craft** ·
27 Vessels carrying containers · 28 Craft longer than 110 m · 29 High-speed
vessels · 30 Fuels with flashpoint ≤ 55 °C · 31 Minimum crew · 32–33
Transitional provisions. Plus 8 annexes and the ESI instructions.

Against `estrin.UNIMPLEMENTED_CHAPTERS`:

- **It stops at 20. Chapters 21–33 are absent**, as is Chapter 2.
- **Three counts, all different, none right.** The tuple has 17 entries; the
  docstring says "eighteen"; `ES-COV` reports `1.0 / float(len+1) = 18.0`
  "chapters" and its note says "One chapter of twenty". **The truth is one of
  thirty-three.** ES-COV exists to be honest about coverage and it currently
  **overstates coverage by about 40 %** — which is defect class 4 from
  `docs/LESSONS.md` (prose standing in for a verdict) wearing a numeric
  disguise, in the finding whose entire job is the refusal.
- **Chapter 11's title is the previous edition's.** The tuple says
  `"11 electric vessel propulsion"`; 2025/1 says **"Special provisions
  applicable to electric propulsion systems"**. That is the single most
  load-bearing chapter for this project.
- Chapters 9, 17 and 20 truncated; 2 and 12 are "(left void)".

### 4.4 CHAPTER 26 — a recreational craft is not subject to Chapter 4 at all

**Art. 26.01, printed p. 191, headed "Application of Part II"**, lists exactly
which Part II provisions bind recreational craft:

> "1. Recreational craft shall meet the following requirements:
> a) from Chapter 3: Article 3.01, Article 3.02(1)(a) and (2), Article 3.03(1)(a)
> and (6), and Article 3.04(1);
> b) from Chapter 5: … c) from Chapter 6: … d) from Chapter 7: …
> e) from Chapter 8: … f) Chapter 9; **g) from Chapter 10: Article 10.01(1),
> mutatis mutandis;** h) from Chapter 13: … i) Chapter 16; j) Chapter 17;
> k) from Chapter 21: …"

**Chapter 4 does not appear.** Chapter 4 is in Part II, and the list is
structured as exhaustive. Art. 4.01 and Art. 4.02 are the only two bars
`estrin.py` implements. Note also that 26.01(1)(a) invokes only Art. 3.02(1)(a)
and (2), so even the general stability sentence 3.02(3) is excluded.

The honest caveat: para (1) does not carry the word "only" — but **para (2)
does**:

> "2. For recreational craft subject to Directive 2013/53/EU (or previously
> Directive 94/25/EC), **only the following requirements apply**: a) Article
> 6.08; b) from Chapter 7: … c) from Chapter 8: … d) from Chapter 13: …"

and that shorter list omits Chapters 3, 4, 5, 9 and 10 entirely.

**The RCD and ES-TRIN are not alternatives, and the module says they are.** Its
out-of-scope finding reads *"It is a recreational craft under the RCD instead"*.
The ESI instruction **ESI-III-8, printed p. 549** (referenced from Art.
26.01(2)) states the overlap directly — verified by reading it:

> "Recreational craft of up to 24 metres length, that are placed on the market,
> have to comply with the requirements of Directive 2013/53/EU. According to
> Article 7 in conjunction with Article 2 of Directive (EU) 2016/1629 …,
> recreational craft having a length of **20 metres or more** shall carry an
> inland navigation vessel certificate attesting the craft's compliance with the
> technical requirements of this Standard."

So a recreational craft of **20–24 m is subject to BOTH regimes at once** — and
that is precisely the band `estrin.py`'s own scope comment works in (it records
a 20.0 m grammar hull as the case that motivated using hull rather than
waterline dimensions). The "instead" is wrong exactly where it matters most.

ESI-III-8 also hands us two more dated harmonised editions for free:
**EN ISO 15083:2023** (bilge pumping, Art. 8.08(2)) and **EN ISO 14509-1:2018 /
-3:2018** (noise emission, Art. 8.10). Art. 26.01(2)(d) additionally offers
**ISO 9094:2022** as an alternative to Art. 13.03(2)–(6) — the dated edition of
a standard `refdata.absent()['flotation.iso9094_fire_thresholds']` records as
unsourced.

### 4.5 Stability — ES-TRIN HAS GM floors, and none of them reaches our SKUs

This was the question that motivated reading 578 pages, and the answer is
**"yes, but not for you"**.

The general requirement is one sentence — **Art. 3.02(3), printed p. 13**:

> "The stability of vessels shall correspond to their intended use."

**That is the entirety of ES-TRIN's stability requirement for a non-passenger,
non-container, non-sailing, non-floating-equipment craft.** No GM, no righting
lever, no heel limit. And per §4.4, a recreational craft does not even get that
sentence.

The numeric criteria that do exist, each class-limited:

| criterion | applies to | article [printed p.] |
|---|---|---|
| **GM₀ ≥ 0,15 m**, corrected for free surface | **passenger vessels** (">12 passengers", 1.01(1.17)) | 19.03(3)(d) [133] |
| h_max ≥ 0,20 m at φ_max ≥ φ_mom+3°; area ≥ 0,05 / 0,035+0,001(30−φ) / 0,035 m·rad by case; φ_mom ≤ 12° | passenger vessels | 19.03(3)(a)–(e) [133] |
| **GM ≥ 1,00 m**, heel ≤ 5°, deck edge not immersed | vessels carrying **non-secured containers** | 27.02(1)(a) [193] |
| **GM ≥ 0,15 m**, trim+heel ≤ 10°, residual freeboard ≥ 0,05 m | **floating equipment** with reduced residual freeboard | 22.08(a) [181] |
| wind heel ≤ 20° at 0,07 kN/m²; h_max at ≥25°, ≥0,20 m at 30°, positive to 60° | **passenger sailing vessels** | 20.03 [163] |
| residual safety clearance ≥ 0,10 m; ≥ 0,50 m without bulkhead deck; freeboard ≥ 0,30 m | passenger vessels | 19.04 [138] |
| freeboard ≥ **500 mm** (derogating from 4.02) | **high-speed vessels** (>40 km/h) | 29.04 [206] |

**So ES-TRIN cannot supply a standard behind `limits.CATEGORY_TABLE`'s GM
column** — the same answer ISO 12217-1:2015 gave. The nearest borrowable anchor
is the 0,15 m of Art. 19.03(3)(d), and quoting it would oblige us to say out
loud that it is a passenger-vessel figure being borrowed for a craft the article
does not govern. **R-GM stays ours.** §7.2.

### 4.6 Chapters 10 and 11 — the electrical harvest, and it is binding, free and real

The project has zero electrical rules. This is where they would come from. Two
negative results first, because they bound the harvest:

- **No numeric insulation-resistance value exists anywhere in ES-TRIN 2025/1.**
  Two hits across 578 pages, Art. 19.10(9) and its transitional row, both:
  *"The insulation resistances and the earthing for electrical systems shall be
  tested on the occasion of periodical inspections."* No value. **Do not encode
  one.**
- **No solar, photovoltaic, renewable or autonomous provision exists.** Zero
  hits for solar / photovolta\* / renewable / wind turbine. Chapter 30 + Annex 8
  cover only fuels with flashpoint ≤ 55 °C (LNG, methanol, hydrogen, fuel
  cells). **A battery-electric solar craft is governed by Chapters 10 and 11
  alone; there is no solar overlay coming.**

The thresholds, with printed pages:

**Art. 10.11(17) [64] — the single most valuable bar in the document set for
this project.** Rooms holding lithium-ion accumulators need an expert
fire-protection concept (or a fireproof enclosure with fire and thermal-runaway
monitoring plus fixed extinguishing per Art. 13.06), **A60 partitions**, and
**mechanical ventilation to the open deck** sited so persons aboard are not
endangered. Then, verified by direct read of the extract:

> "These requirements do not apply if the cumulative capacity of the lithium-ion
> accumulators in the room is below **20 kWh**."

`EnergySpec.battery_kwh` defaults to **30.0** (`navalai/energy.py:20`), i.e.
**above the exemption**, so the default configuration of the Danube SKU triggers
A60 partitions and mechanical ventilation to open deck. Those are *arrangement*
constraints, not merely electrical ones.

**Art. 10.02(1) [55]:**

> "Where craft are fitted with an electrical installation, that installation
> shall have **at least two power sources** in such a way that where one power
> source fails the remaining source is able to supply the consumer equipment
> needed for the safe operation for **at least 30 minutes**."

10.02(2) requires a **power budget calculation**. 10.02(4) exempts
electric-propulsion sources, which fall to **Art. 11.01(2)(a) [73]**: **one**
source for a single main propulsor, **two** for more than one.

**Art. 10.11(2)/(3)/(5) [62–63]** — accumulators barred from wheelhouse,
accommodation, lounges and holds (exception: charging power **< 0,2 kW**);
**> 2,0 kW** needs a special room or an on-deck cupboard, mechanically
ventilated to open deck; **≤ 2,0 kW** may go below decks in a cupboard or chest.

**Art. 10.11(7)–(9) [63] — a closed-form ventilation calculation, which is the
kind of thing this project can actually implement.** Mechanical ventilation
required above **2,0 kW NiCd** / **3,0 kW lead**. Required air throughput:

> `Q = f · I_gas · n  [m³/h]`

with **f = 0,11** for liquid electrolytes and **f = 0,03** for enclosed cells
(*"electrolyte immobilised in gel, non-woven fibrous material"*), **I_gas = ¼ of
the maximum current of the charging device in A**, and the third symbol defined
as **"number of cells in series circuit"**. Natural ventilation is sized on an
air-flow velocity of **0,5 m/s** with a minimum duct cross-section of
**80 cm² (lead) / 120 cm² (NiCd)**.

(The mathematical-italic glyphs are mis-mapped in this PDF — the cell-count
symbol extracts as `m`. **The symbol letters are therefore not reliable; the
definition lines are, and they are unambiguous.** Read the coefficients and the
definitions, not the letters.)

**Art. 10.11(12)/(14)/(15)/(16) [63–64]:** discharged accumulators rechargeable
to **80 % of nominal capacity within a maximum of 15 hours**; charging voltage
≤ **120 % of rated**, **125 % for traction batteries**; *"The requirements of
European Standard **EN 62619 : 2022** and **EN 62620 : 2023** shall apply for
lithium-ion accumulators"*; and **a BMS is mandatory for lithium-ion**, with six
listed minimum functions (cell protection, charge control, load management,
charge-level determination, cell balancing, thermal management).

**That EN 62619:2022 citation is the second independent pointer at the same
standard** — the EMSA guidance cites IEC 62619:2022 by clause more than a dozen
times (§5.5). Two documents, one free and non-binding, one free and *binding*
for in-scope inland craft, converge on it. §9.

**Art. 10.01(3) [55] — the design envelope**, and it is quotable as-is:

> "The equipment and installations shall be designed for a permanent list of the
> craft of up to **15°** and internal ambient temperatures from **0 °C to
> +40 °C** and on deck from **−20 °C to +40 °C**."

Note this is the ONE Chapter 10 article a recreational craft does get, via Art.
26.01(1)(g) — *"Article 10.01(1), mutatis mutandis"* — though that limb names
(1), not (3).

**Voltages, Art. 10.06(1) [59]:** 250 V DC / 250 V 1φ / 690 V 3φ for power and
heating; **50 V** for sockets feeding mobile equipment on open decks, in
confined or damp metal-enclosed rooms, and in boilers and tanks; 250 V with an
isolation transformer or protective double insulation; 250/690 V with a
**residual-current circuit-breaker ≤ 30 mA**. **The 50 V line recurs as the
safety threshold throughout** — 10.05(1) earthing required above 50 V; 10.08(3)
hull earthing above 50 V; 10.12(1)(a) separate marked terminals; 10.12(3)(b)
insulation monitoring with optical and acoustic alarm on non-earthed networks
above 50 V; 10.12(4)(c) insulating mats; 10.18(5) discharge to below 50 V in
under 5 seconds.

**Cables, Art. 10.15 [66–68]:** minimum conductor cross-section **1,5 mm²**;
voltage drop from main switchboard to the least favourable point **≤ 5 % for
lighting, ≤ 7 % for power or heating**.

**Chapter 11 [73–77]:** emergency shut-down for each electric engine, manually
operated, **outside the wheelhouse** (11.01(5)); winding insulation classes
**B, F or H** per EN 60085:2008 (11.03(3)); on external-cooling failure the
vessel must stay *"capable of making steerageway under its own power for **30
minutes**"* (11.04(3)); non-volatile logging of operating conditions, **not
required below 100 kW total power** (11.05); earth-fault monitoring plus
differential protection per propulsion engine (11.07(3)).

**On the two tables — RE-CHECKED DIRECTLY, and the caution was half right.**

- **Art. 10.06 (voltages) extracts CLEANLY and is verified.** The header on
  printed p. 59 reads *"Maximum permissible voltage | Direct current |
  Single-phase alternating current | Three-phase alternating current"* and every
  row carries its three values inline (e.g. *"a) Power and heating
  installations, including the sockets for general use … 250 V 250 V 690 V"*).
  Row (c)1 and row (e) both read *"50 V(1)"*, and comment (1) is *"When this
  voltage comes from higher voltage networks, a galvanic isolator (isolation
  transformer) must be used."* **The figures in this section were read, not
  reconstructed.**
- **Art. 10.03 (IP ratings) is the one that does not extract cleanly.** Its
  six-column layout flattens and the row/column association is a reading.
  **Verify against a rendered page before encoding any IP grade.**

This distinction is the point of re-checking rather than repeating a caveat: one
table was recoverable and one was not, and treating both as unverified would
have thrown away a verified result.

### 4.7 Other ES-TRIN thresholds computable from geometry we already hold

Recorded so a later session does not re-derive them. Note §4.4 first: if the
craft is recreational, most of these do not bind it.

- **Art. 4.03(7)/(10) [20]** draught-mark placement: three pairs at L/2 and
  L/6 from each end; **two pairs at ~L/4 if L < 40 m**; one pair amidships if
  not carrying goods. **Both limbs apply to our SKUs.**
- **Art. 4.04(1) [21]** a draught scale is required where *"draught may exceed
  1 m"*.
- **Art. 4.05 [22]** zone-4 derogation: safety clearance **150 mm** (closable
  openings) / **200 mm** (non-closable), freeboard *"may not be less than
  0 mm"*. This is a RELAXATION — a craft failing the 300 mm bar may still be
  compliant on zone-4 waterways, so a single-zone check can produce a **false
  FAIL**.
- **Art. 4.01(2) [17]** safety clearance rises to **500 mm** at openings that
  cannot be closed spray-proof and weathertight. `estrin.py`'s note describes
  this correctly and does not evaluate it; it becomes a pure geometry check once
  openings are modelled.
- **Art. 3.02(1)(b) [13]** hull plate minimum thickness, **two formulae split at
  L = 40 m**: `t_min = f·b·c·(2,3 + 0,04 L)` above, `f·b·c·(1,5 + 0,06 L)` below,
  *"however, not less than 3,00 mm"*, and `t_min = 0,005 × a`.
- **Art. 3.03(1) [14–15]** collision bulkhead between **0,04 L** and
  **0,04 L + 2 m** from the FP (reducible to 0,03 L with a damage calculation);
  aft-peak bulkhead required where **L exceeds 25 m**; residual safety clearance
  **100 mm** with the end compartment flooded.
- **Art. 13.01(1)/(2) [81–82]** bow anchor mass `P = k·B·T [kg]` with
  `k = c·√(L/(8B))`, `c` from a dead-weight table (20/25/30/45/55/65/70). **Every
  input already exists in the model** — this is the most immediately computable
  unimplemented ES-TRIN rule in the standard, and Art. 26.01(1)(h) and (2)(d)
  both invoke Art. 13.01(2), so **it binds recreational craft under both limbs.**

### 4.8 ES-QIN 2024/1 — crew, not vessel. Nothing here.

166 pages in five parts: standards of competence, practical examinations,
technical requirements for vessel-handling and radar **simulators**, medical
fitness criteria, and models of crew documents. Keyword counts over all 166
pages: **freeboard 0, safety clearance 0, metacentric 0, scantling 0, hull
thickness 0.** "Stability" appears 34 times and every sampled occurrence is a
*competence* — "Ability to supervise the craft's stability and to give
instructions". Where a vessel requirement is needed it **defers to ES-TRIN**
(9 references, e.g. *"shall fulfil the technical requirement laid down in
ES-TRIN in its current version"*).

**Nothing in ES-QIN belongs in `navalai/rules/`.** Its only numeric technical
content is Part III's simulator specification, which governs a training rig.

---

## 5 · EMSA Battery Guidance v1.0 — the first electrical source this tree has

82 PDF pages. Printed page = PDF page − 2. **Publisher EMSA; "Version 1.0, Date:
November 2023"** (PDF p. 1); document history gives 25/10/2023 (PDF p. 6).

### 5.1 Status — non-binding, and it says so three times

PDF p. 3, verbatim:

> "None of the provisions within the EMSA Guidance are binding in nature and
> should be regarded as guidance for good practice. Adequate application of the
> recommendations within the EMSA Guidance should always be done in conjunction
> with **the referenced industry standards** on the design and installation of
> maritime battery energy storage systems."

PDF p. 9 (printed 7): "there is no regulatory instrument at international level
on the safety aspects of using batteries in ships … EMSA … has drawn-up this
**non-mandatory Guidance**". PDF p. 11 (printed 9): the Guidance should "be goal
based, **non-mandatory**".

**Consequence for `rules/`: nothing derived from this document may be reported
as a requirement that is passed or failed.** It is `check_selection()` material
or an advisory finding, never a pass/fail bar presented as law. The disclaimer
also states outright that the numbers live in the referenced industry standards
— §5.5 lists which.

### 5.2 Scope — and the 5 kWh cut-off that decides whether it reaches us at all

Application clause, PDF p. 11 (printed 9):

> "This non-mandatory Guidance applies to lithium-ion battery energy storage
> systems installations on board ships. This non-mandatory Guidance refers to
> **all ships engaged in international or domestic voyages, irrespective of
> their material of construction**, for which a battery energy storage system
> based on lithium-ion technologies serves any of the following functions or
> their combination: main propulsion, auxiliary services, emergency propulsion,
> emergency services and/or other ancillary services."

Exclusion, PDF p. 13 (printed 11):

> "This non-mandatory Guidance is **not applicable to installations of less than
> 5 kWh**."
> "This non-mandatory Guidance does not refer to second life batteries."

**Be honest about the fit.** The words "recreational craft", "pleasure craft",
"yacht", "inland" and "24 m" as a scope limit do not appear in the 82 pages (the
one "<24 m" hit, PDF p. 71, is a crew-training concession for Directive
2009/45/EC passenger ships in sea area D). The application clause is written
broadly and is *not* SOLAS-only — it names domestic voyages repeatedly — but the
whole prescriptive apparatus is expressed in SOLAS II-2 space categories, A-60
insulation, SRtP and STCW ETO certificates, machinery that does not exist for a
Directive 2013/53/EU recreational craft. **It is applicable by its own wording
and a poor fit in practice.** `EnergySpec.battery_kwh` defaults to 30.0 kWh
(`navalai/energy.py:20`), which lands in the 5–50 kWh band — inside scope, and
in the *lighter* of the two tiers.

### 5.3 The numbers it does state

Energy bands (the tiering is the most directly implementable thing here):

| threshold | consequence | cite (PDF / printed) |
|---|---|---|
| **< 5 kWh** | Guidance not applicable | 13 / 11 |
| **< 5 kWh** | may be installed in accommodation spaces and corridors | 73 / 71 |
| **> 5 kWh** | §2.2 space requirements apply; Li-ion UPS treated as BESS | 34 / 32; 26 / 24 |
| **< 50 kWh** | may sit in a non-category-A machinery space; in a *service* space only if rack-type modular with integrated cooling, gas/heat/smoke detection, firefighting and extraction | 45 / 43; 46 / 44 |
| **≥ 50 kWh** | dedicated battery room, category A machinery space; shipborne air take-in/extraction in addition to rack systems | 45 / 43; 49 / 47 |

Other hard numbers:

- **6 air changes per hour** — "For BESS of 50 kWh or more in normal conditions,
  not less than 6 air changes per hour of the battery room should be foreseen"
  (PDF 49 / 47). **The only numeric ventilation rate in the document.**
- **0,05 L from the FP** — "The battery space or room is located aft of the
  collision bulkhead. **For ships not required to have a collision bulkhead the
  battery space or room is not located forward of 0.05L from the forward
  perpendicular** where L is the overall length of the ship" (PDF 37 / 35). The
  second sentence is written for craft like ours.
- **1,5 m** — open-deck areas within 1,5 m of BESS inlet/exhaust openings are
  hazardous areas (PDF 37 / 35).
- **300 mm** — any metallic fuel-system component passing within 300 mm above
  the battery top must be electrically insulated (PDF 37 / 35).
- **IP44** minimum enclosure (PDF 25 / 23); open deck ">IP55 and preferably
  IP67", corrosion class **C5 or CX** (PDF 35 / 33; 46 / 44).
- **A-60** boundaries, "A60 protection secures containment for 60 minutes"
  (PDF 43 / 41).
- **Inerting: O₂ ≤ 11,3 % ⇔ 45,2 % agent concentration** (nitrogen, high hazard)
  for non-metallic lithium batteries, deferred to IMO Circ.848 / MSC/Circ.1165
  (PDF 47 / 45).
- **Water: fresh water first, minimum 30 min, preferably 60 min** (PDF 47 / 45).
  No flowrate — "established on the basis of the fire dynamics simulation".
- **Thermal-runaway definition**: self-heating "typically larger than > 80 °C or
  1 °C/s" (PDF 16 / 14).
- **Propagation-test acceptance** (PDF 62–63 / 60–61): start at 100 % SoC;
  ambient = max operating temperature ±5 °C **and not less than 45 °C**; BMS
  safety functions deactivated; monitor to ambient and **minimum 8 hours** after;
  no external firefighting or ventilation. Pass: no propagation between cells in
  **three witnessed tests**, **neighbouring cells ≤ 80 °C**, measurable voltage
  throughout, no case rupture, no external fire.
- **Redundancy, full-electric** (PDF 73 / 71): "When the main source of power is
  based on BESS only, the main sources of power should consist of **at least two
  independent BESS systems located in two separate rooms or spaces**. The two
  independent battery systems should not be connected to the same switchboard."
- **Two trained persons** on board at all times; **monthly** drills (PDF 72 / 70).
  **40 min** maximum smoke-gas exposure (PDF 69 / 67).

### 5.4 The three numbers we most wanted, and it does not have them

Stated as an explicit negative because a checker with no bar is worse than none:

1. **No return-to-port energy margin.** PDF 56 / 54 requires remaining autonomy
   to be displayed, "defined **to the satisfaction of the Administration**".
2. **No SOC operating window.** SoC appears only for UPS (100 %), test articles
   (100 %), and as a BMS display function. `navalai/energy.py:265` hard-codes
   `* 0.8  # 80% DoD` — and it is the only place that number exists, i.e. it is
   ours, it is not in `limits.py`, and **no document in this set blesses it.**
3. **No deck/securing load case.** PDF 36 / 34 says only that fixings "should be
   constructed to withstand the forces imparted from the batteries in design
   seagoing conditions". No accelerations, no g-values.

Also required-but-unquantified: installed-capacity calculation "considering
ageing" with no ageing model or margin (PDF 21 / 19); ventilation capacity
"calculated according to expected gas release" with no gas-release model
(PDF 49 / 47); short-circuit current calculation with no method named
(PDF 21 / 19); fire-dynamics simulation with no acceptance time (PDF 46 / 44).

### 5.5 Where the numbers actually live — the purchase signal

The document has **no formal normative-references clause** (consistent with its
non-binding status); every list is headed "Relevant standards". The ones cited
*by clause number*, i.e. the ones it leans on for real bars:

- **IEC 62619:2022** — industrial Li cell/battery safety. Cited by clause more
  than a dozen times: 7.2.1 external short circuit, 7.2.2 impact, 7.2.3 drop,
  7.2.4 thermal abuse, 7.2.5 overcharge, 7.2.6 forced discharge, 7.3.2 internal
  short circuit, 7.3.3 propagation, 8.2.2–8.2.4 overcharge/overheat control,
  6.7.4 BMS functional test. **If one electrical standard is ever bought, this
  is it.**
- **IEC 62620** — 6.2 charging, 6.3 discharge/capacity, 6.4 capacity retention,
  6.5 internal resistance.
- **UL 9540A** — thermal-runaway propagation test method, §7.4 vent-gas
  composition.
- **IEC 60079-10-1:2020** §4.4.2 — hazardous-area extent (the source behind the
  1,5 m figure's method).
- **EN 15004** series — the inerting-concentration calculation.
- **IEC 62742:2021** — EMC for **non-metallic hulls**. Directly ours.
- **IEC 63462-1** "Maritime battery system — Part 1" — **explicitly "under
  preparation"** (footnotes 3 and 15, PDF pp. 25 & 56). *The maritime-specific
  battery standard did not exist as of Nov 2023.* Do not queue a purchase for a
  document that may not be published; check first.
- **IEC 63056 is not cited anywhere in this document** — worth knowing, since it
  is a name that circulates in this domain.

### 5.6 COULD NOT VERIFY

- PDF p. 12 (printed 10) **Figure 1.1**, six BESS power-configuration single-line
  diagrams — raster, no text layer, unread.
- PDF pp. 81–82 **Annex C infographics, "Schematics of BESS boundaries"** — p. 82
  has **no text layer at all**. The system-boundary schematic, probably the
  clearest statement of where the BESS boundary sits, is unread. Needs poppler
  or a human.
- Tables 3.1/3.2 (PDF 58–61) extracted with columns flattened; the standard
  clause references are confident, the cell/cell-block/system **column
  assignment for rows 10, 15 and 21 may be wrong.** Verify against a render
  before using the level assignment.
- **The document's internal cross-references are broken.** §5 (PDF 73 / 71)
  refers to "Chapter 1.3", which does not exist (numbering runs 1.1.1–1.1.5);
  §2.4 refers to "section 1.3.1.3", "section 2.2.3.3" and "section 2.2.4", none
  of which exist. **Do not implement a rule whose applicability depends on
  resolving one of these.**

---

## 6 · The two documents that yield nothing — stated precisely

### 6.1 SAFEMASS Parts 1 and 2 — out of scope, and self-declared unquantified

Author **DNV GL AS** for EMSA under contract 2019/EMSA/OP/4/2019; **date of issue
2020-03-25**; Part 1 = Report 2019-1296 Rev. 0 (166 pp.), Part 2 = Report
2019-0805 Rev. 0 (104 pp.). It is a **consultancy study report** — not a
standard, not guidance, not a regulation. PDF p. 2 of each:

> "The information and views set out in this study are those of the author(s)
> and do not necessarily reflect the official opinion of EMSA."

And PDF p. 3 of each, which is decisive for citation: "(iii) **No third party
may rely on its contents**; and (iv) DNV GL undertakes no duty of care toward
any third party", with the distribution checkbox ticked as "INTERNAL use only".

**It quantified nothing, and says so.** Part 1 PDF p. 20 (printed 13) §3.3 and
verbatim again Part 2 PDF p. 16 (printed 10) §3.3:

> "Due to the lack of data and a high level of uncertainty inherent in the
> concepts described, **no quantification of risk has been performed**."

A sweep of both text layers for risk-acceptance criteria, ALARP, FN curves,
individual/societal risk, GCAF/NCAF, failure rates, MTBF and per-ship-year
figures returns **zero hits**. Across ~40 risk-control measures the only numeral
is the phrase "1 out of 2 MASS operators are indisposed" (Part 1 PDF p. 89).

**Its scope excludes our vessels entirely.** Every vessel studied is SOLAS-size:
a 130 m / 7500 GT ro-ro ferry, a 130 m container feeder, a 220 m bulk carrier
(Part 1), and three 80 m / 3000 GT container ships (Part 2). Recreational craft
appear only as a navigational hazard *to* the MASS. RCD 2013/53/EU, ISO 12217,
ISO 12215 and ES-TRIN are not mentioned in either report.

Two things in it are nonetheless worth knowing:

- Its **regulatory gap list** is precise and citable — Part 1 PDF p. 85
  (printed 78): COLREG Rule 2 (responsibility), COLREG Rule 5 (look-out), STCW
  VIII/2, SOLAS V/14 are the four instruments identified as preventing A3-B1
  operation. But every one of those is an instrument that does not reach a
  4–24 m EU recreational or inland craft in the first place, so even the gap
  analysis is not transferable.
- Its **conclusion argues against modelling autonomy as a vessel-level enum** —
  Part 1 §9.2, PDF p. 97 (printed 90): "One of the main findings of the study is
  that this approach is neither useful nor practical … automation design should
  therefore not be made at a global, ship level … Instead it should be made
  function by function on a system and task level." If this project ever adds an
  autonomy model, that is a useful prior. It is not a gate.

COULD NOT VERIFY: Tables 1 and 2 (the MSC 100/5/6 A/B autonomy ladder, Part 1
PDF pp. 16 and 22) are **raster images with no text layer**; the full
enumeration of autonomy levels is unread. Only the A2 and A3 cells that the
running prose reproduces in quotation marks were read.

### 6.2 "A Guide to Responsible Boating" — no design content whatsoever

The SeaCleaners (French NGO) with European Boating Industry. 14 pages, no
version, no date on the document, English translation of a French original. It
is an **awareness booklet for recreational boaters about marine plastic
pollution**: a personality quiz, onboard recycling tips, clean-port labels, a
citizen-science app list.

**It contains zero design, construction, stability, structural, electrical or
equipment requirements.** Its numbers are pollution statistics (9–14 Mt of
plastic per year; "a cigarette butt pollutes 500 L of water"). Its one
quasi-regulatory line — organic waste "forbidden to dispose of it before 12
miles off the coast" (p. 8) — is an uncited paraphrase of MARPOL Annex V and is
not a design requirement. The only sentence touching design is "Choose hull
paints (antifouling) that are free from biocides and heavy metals" (p. 8), with
no standard, substance list or limit.

**Do not cite it for anything.** It is recorded here so that the next session
does not spend a second read on it.

---

## 7 · THE BOUNDARY — which of our rules the free texts can and cannot satisfy

This is the load-bearing section. The rule ids are those in
`navalai/rules/review.py`; the verdicts below are about PROVENANCE, and none of
them is a licence to change a `basis` string without a reviewer.

| rule | current state | can a free text satisfy it? |
|---|---|---|
| **R-CAT** | confirmed vs ISO 12217-1:2015 | **YES — better provenance is available free.** §7.1 |
| **R-DFH** | confirmed vs ISO 12217-1:2015 Annex A + Table A.1 | **NO.** The formula and Table A.1 exist in no free text. §7.5 adds an edition problem. |
| **R-OLH** | confirmed vs ISO 12217-1:2015 6.2.3 a) + Table 4 | **NO.** Same. |
| **R-GM** | unconfirmed — "NOT IN THE STANDARD" | **NO. Confirmed ours by a second independent search.** §7.2 |
| **R-PBM** | unconfirmed — no 12215-5 text held | **NO.** §7.3 |
| **R-TBM** | unconfirmed — no 12215-5 text held | **NO.** §7.3 |
| **R-SCP** | in neither set (an oversight per the module's own law) | **NO — and the free texts make it worse.** §7.4 |
| ES-SCOPE / ES-SAFE / ES-FB / ES-COV | in neither set | **YES — ES-TRIN is free.** But §4.2 and §4.4 first. |

### 7.1 R-CAT — the one rule whose provenance improves, and it costs nothing

`rules/iso12217.py:175` cites `"ISO 12217-1 §5 (design categories)"` for the
significant-wave-height context. Every one of the four values in
`limits.CATEGORY_TABLE` column 1 appears verbatim in **RCD Annex I Part A §1**
(PDF p. 25, OJ L 354/114) — a **free, binding** text — and the harmonised
standards' own Annex ZA tables say so: *"Design categories A, B, C and D defined
in this standard correspond to design categories A, B, C and D of Directive
2013/53/EU"* (guide pp. 225–227). **The categories originate in the Directive
and ISO transcribes them, not the other way round.**

Two things the free text settles that the paid one was being asked to:

- **The A/B sense.** `REVIEW["interpretations"]["R-CAT"]` records that the table
  stores one scalar and cannot express that A is a lower bound and B an upper
  one. The Directive states both in words. **And it is more subtle than the note
  assumes:** category A's *wind* bound is strict (*"may exceed wind force 8"*)
  while its *wave* bound is **inclusive** — *"significant wave height of 4 m and
  above"* (explanatory note A, guide p. 68). B is *"up to, and including, 4 m"*.
  **So by the literal text Hs = 4,0 m satisfies BOTH A and B; the wave bound is
  not a partition.** A rules engine treating A as `Hs > 4.0` would disagree with
  the Directive.
- **Category D carries a second number we do not hold**: *"with occasional waves
  of 0,5 m maximum height"*. Modelling D with one Hs drops it.

**What this does NOT do.** It does not close Gate 6R, it does not license
editing `basis`, and R-CAT is already confirmed. What it does is remove a paid
dependency from a rule that had one, and add a bound (0,5 m) and a correction
(the inclusive A bound) that are free.

### 7.2 R-GM — searched twice more, still ours

`review.py` records zero hits for an absolute metacentric requirement across 86
pages of ISO 12217-1:2015. This review adds two independent negative searches:

- **RCD:** Annex I A 3.2 is *"sufficient stability and freeboard"* (PDF p. 26,
  OJ L 354/115). No number. The RSG guide reproduces it and adds nothing (p. 81).
- **ES-TRIN 2025/1:** the general clause is Art. 3.02(3), *"The stability of
  vessels shall correspond to their intended use"* (printed p. 13). Every GM
  floor in the standard is class-limited to passenger vessels (0,15 m),
  container carriers (1,00 m), floating equipment (0,15 m) or passenger sailing
  vessels — none of which is a 4–24 m solar craft. §4.5.

**Three documents, three searches, no GM floor for our vessels. R-GM is a
project practice bar and `NOT_FROM_STANDARD` is where it belongs.** Do not
borrow the 0,15 m: Art. 19.03(3)(d) governs a vessel carrying more than twelve
passengers, and importing it would be defect class 6 — a bar taken from a
configuration the product never runs.

### 7.3 R-PBM and R-TBM — the free texts get us a ROUTE, not a NUMBER

**The number: no.** The whole of EU recreational-craft structural law is Annex I
A 3.1, *"strong enough in all respects"* (PDF p. 26, OJ L 354/115). The guide
reproduces it and never quantifies (p. 80). ES-TRIN's plate-thickness formulae
(Art. 3.02(1)(b)) are for steel inland hulls, not plywood panels, and per §4.4
do not bind a recreational craft. **P_BM's coefficients, the k2 aspect-ratio
table, kC, and σ_d for okoumé exist in ISO 12215-5 and nowhere we can read.**
R-PBM and R-TBM stay `unconfirmed`, and the reasons already in `review.py`
remain exactly right.

**The route: yes, and this is new.** RSG Comment n.7 (guide p. 79) lists four
accepted approaches to ER 3.1 and only the first is ISO 12215; route 3 is
*"acceptable construction calculation(s) or testing"*, with a specified
documentation set (§3.4). And **Art. 20(1)'s Module A conditional names ER 3.2
and 3.3 only, not 3.1** — so on its face ISO 12215-5 compliance does not gate
the self-certification module.

**Say this carefully, because it is the sentence most likely to be
over-claimed.** It means an own-calculation scantling file is a legally
contemplated route. It does **not** mean our current numbers are defensible:
`SIGMA_D_OKOUME = 15.0` is a stand-in whose *shape* is known wrong (Table 9 makes
σ_d = 0,5 σ_uf and Table E.2 makes σ_uf a formula in density and ply count), and
the flat 10 kN/m² floor in `design_pressure_bottom` is neither length- nor
category-dependent where Equation (8) is both. **A route that permits our own
calculation raises the bar on that calculation; it does not lower it.**

### 7.4 R-SCP and the measurand nobody logged — ISO 8666

Every length-keyed rule in play turns on hull length: RCD scope 2,5–24 m
(Art. 3(2)); swamped flotation below 6 m (A 3.3); life-raft stowage above 6 m
(A 3.7); the whole Art. 20 module table at 12 m; `R-SCP` at 6 m; and
`offset_load_heel_limit_deg`, which is a **cubic** in L_H.

**The Directive refuses to define it.** Art. 3(10), PDF p. 8 (OJ L 354/96):
*"'hull length' means the length of the hull measured in accordance with the
harmonised standard."* The guide names that standard and its edition —
**EN ISO 8666:2020 + /A11:2021** (p. 259), with ERFU #166r2 (p. 314) on
removable parts. **We hold neither, and ISO 8666 appears in neither
`PURCHASE_QUEUE` nor `refdata.absent()`.**

`iso12217.hull_length_m()` substitutes L_WL and argues the error is in the
refusing direction. That reasoning is sound for the ISO scope test, where being
ruled out means getting no verdict — but the RCD's two 6 m rules cut **opposite
ways**, so understating length flips A 3.3 on and A 3.7 off, and one of those is
the unsafe direction. **This is the only genuinely new absence this review
found in a quantity the code already depends on.**

### 7.5 An edition problem Gate 6R is not built to catch

`review.REVIEW["editions"]["ISO 12217-1"]` reads
`"ISO 12217-1:2015 (Third edition, 2015-10-15)"`, and R-DFH and R-OLH are
confirmed against it. **The harmonised edition — the one that confers
presumption of conformity — is `EN ISO 12217-1:2017`** (guide p. 225).

Gate 6R's bar, from `data/gate-ledger.json`, is *"every implemented standard
named with the DATED edition the reviewer held"*. The record satisfies it: the
reviewer did hold 2015 and said so. **The gate asks about attributability, not
currency, and a confirmation against a superseded edition passes it.** That is a
finding about the gate's scope, recorded here so it is not lost; it is emphatically
**not** an argument for softening anything, and the honest reading is that
`review.py`'s note *"the gate was asking 'is the edition recorded?' when the
question it exists to ask is 'do the numbers match the text?'"* has a third layer
underneath it: *which* text.

What is NOT established: whether `phi_O(R) = 11,5 + (24 − L_H)³/520` or Annex A's
`hD(R) = (L_H/15)·F1..F5` changed between 2015 and 2017. **Nothing in the free
documents answers that.** ERFU #188r1 (guide p. 329) shows the series was in
flux — 14945/14946:2021 changed the maximum-load definition out from under the
12217 worksheets and *"The revised 12217 series will be published when dated
referenced documents are published (Late 2022)"* — which raises rather than
lowers the probability that something moved.

### 7.6 The measured state of Gate 6R, so nobody has to re-derive it

    $ python -c "from navalai.rules.review import edition_defects; print(edition_defects())"
    ["ISO 12215-5: edition is a placeholder ('edition not recorded — set this')"]

**ONE defect, not two.** `docs/research/COMPLIANCE.md` §9 still says *"The two
that close Gate 6R"* and `PURCHASE_QUEUE` row 1 still says 12217-1 *"CLOSES HALF
OF GATE 6R (RED)"*. Both were true when written and are now stale: the 12217-1
entry was filled in on 2026-08-12 when the 2015 text was read. **ISO 12215-5
alone holds Gate 6R red** — subject, always, to the warning at the top of this
file about what "closing" it legitimately requires.

---

## 8 · NEWLY REACHABLE — what these documents open that we are not doing at all

Reported, not implemented. Ordered by value per unit of work.

### 8.1 ES-TRIN's electrical chapters, and the module that has no caller

`navalai/rules/estrin.py` is 349 lines with **no production importer** —
`evaluate.py:51–54` wires `iso12215` and `iso12217` and nothing wires ES-TRIN
(verified directly; `docs/research/FLOW-AUDIT.md` §B records the same). So the
Danube SKU's governing standard is implemented and unreachable.

Before it is wired, §4.2 and §4.4 must be settled — **it has three missing
permissive clauses and it may be applying Chapter 4 to craft Chapter 26 exempts.**
Wiring a module with a known permissive defect into the ladder makes the defect
load-bearing.

What ES-TRIN opens beyond Chapter 4, all free and binding for in-scope craft:

- **Art. 10.11(17)'s 20 kWh lithium threshold** — above it, A60 partitions and
  mechanical ventilation to open deck. `EnergySpec.battery_kwh` defaults to
  30.0, so the **default configuration is above the exemption.** These are
  arrangement constraints and land on `arrangement.py`, not only on `rules/`.
- **Art. 10.11(8)'s `Q = f · I_gas · n`** — a closed-form ventilation
  calculation with all three coefficients stated (f = 0,11 / 0,03; I_gas = ¼ of
  max charger current; n = cells in series). This is the only ventilation
  *formula* in the entire document set; EMSA gives a 6 ACH floor and defers the
  rest to an unspecified gas-release model.
- **Art. 10.02(1)** two power sources / 30 minutes, with a required power-budget
  calculation; **Art. 11.01(2)(a)** one or two sources by propulsor count.
- **Art. 10.11(3)** the 2,0 kW charging-power trigger for a dedicated room.
- **Art. 13.01(2)** anchor mass `P = k·B·T`, `k = c·√(L/8B)` — **every input
  already exists in the model**, and Art. 26.01 invokes 13.01(2) under *both*
  limbs, so it binds recreational craft either way. The most immediately
  computable unimplemented rule found in this review.

### 8.2 Four RCD thresholds that are free, binding, and currently unchecked

- **A 3.3** — craft under 6 m susceptible to swamping need means of flotation in
  the swamped condition. `refdata/flotation.py` exists; the RCD supplies the
  trigger, though **not** the pass criterion (that is 33 CFR 183 / ISO 12217,
  and `flotation.NOT_SOURCED` already records the gap).
- **A 3.7** — life-raft stowage points for categories A and B at any length, and
  C and D above 6 m. A pure (category, length) predicate over an arrangement.
- **A 2.2** — builder's-plate content, including *"excluding the weight of the
  contents of the fixed tanks when full"*. A documentation checker on the export
  surface. **But read §3.8 first: `mMBP ≠ mLDC` and the two published standards
  are inconsistent, so a plate emitted from `mldc_kg` would be wrong.**
- **Art. 20(1)** — the conformity-route decision table. Not a physics rule; a
  *governance* one. It is exactly the shape `navalai/policy/` compiles: a
  (category, length) input producing a conformity route, and a **ratchet** in
  the policy sense — declaring category C under 12 m without ISO 12217
  compliance moves the route inward, from Module A to A1. The three policy
  clauses (append only, ratchet inward, `if policy is not None`) fit it without
  modification.

### 8.3 The electrical/battery domain, where we currently have nothing

Two documents converge on the same standard, one non-binding and one binding:

- **EMSA** cites **IEC 62619:2022** by clause more than a dozen times (7.2.1–7.2.6,
  7.3.2, 7.3.3, 8.2.2–8.2.4, 6.7.4).
- **ES-TRIN Art. 10.11(15)** states flatly: *"The requirements of European
  Standard **EN 62619 : 2022** and **EN 62620 : 2023** shall apply for lithium-ion
  accumulators."*

Free content that can be used *now*, with the non-binding status stated:
EMSA's 5 kWh / 50 kWh energy bands, 6 ACH, 0,05 L longitudinal position, 1,5 m
hazardous zone, IP grades, and the propagation-test acceptance bars (§5.3); and
ES-TRIN's 20 kWh, 15 h/80 %, 120 %/125 % charge voltage, mandatory BMS with six
functions, and the 15° / 0–40 °C / −20–40 °C design envelope (§4.6).

**And what is NOT there, which must be recorded as absent rather than invented:**
no return-to-port energy margin, no SOC operating window, no battery-securing
load case, no insulation-resistance value. `navalai/energy.py:265` hard-codes
`* 0.8  # 80% DoD` — the only place that number exists in the tree, it is not in
`limits.py`, and **no document in this set blesses it.** It is a candidate for
both `limits.py` and an `absent()` row, and it is currently neither.

### 8.4 Two operational facts worth knowing before any of the above

- **RFU #199r1 (guide p. 335): retrofitting lithium to a CE-marked craft is a
  "major craft conversion"** under Art. 3(7) — full re-assessment.
- **Art. 2(2)(a)(vi)–(vii) (RCD, PDF p. 6):** experimental watercraft not placed
  on the market, and watercraft built for own use not placed on the market
  within five years, are **exempt from Annex I Part A entirely**. Every
  conformity conclusion in §3.5 is conditional on placing product on the market.

---

## 9 · PURCHASE_QUEUE — proposed reordering, with the evidence for each move

`refdata.PURCHASE_QUEUE` is the one list (`tests/test_refdata.py` fences it two
ways: every edition defect must have a row, and every row must say what it
supplies). **The following is a proposal for whoever owns `refdata/`; nothing
was edited.**

### 9.1 The moves

**1. ISO 12215-5:2019 → position 1.** MEASURED (§7.6): `edition_defects()`
returns exactly one defect and it is 12215-5. It alone holds Gate 6R red, and it
supplies four numbers whose *shape* — not just value — is known wrong (σ_d, the
k2 table, kC, and the P_BM_MIN floor). The row text should change from *"CLOSES
THE OTHER HALF OF GATE 6R"* to closing all of it, and should gain the dated
edition **EN ISO 12215-5:2019** as the thing to buy — **as a purchasing target,
never as a `review.py` edition string.** See the warning at the top.

**2. ISO 12217-1 → position 2, and RE-SCOPE the row, which is now wrong in three
ways.** It currently says the purchase *"CLOSES HALF OF GATE 6R (RED)"* and
supplies *"the GM floor"* and *"the significant wave height each category
implies"*. All three are false as of this review:

- It closes no part of Gate 6R — the 12217-1 edition entry was filled in on
  2026-08-12.
- There is no GM floor in it (`review.py`, zero hits over 86 pages).
- The wave heights come free from RCD Annex I Part A §1 (§7.1).

Its **real** justification is now stronger and different: **Art. 20(1)(b)(i)
makes compliance with it the condition for Module A** on a category C craft
under 12 m — the only unsupervised conformity route those SKUs have (§3.5). And
the edition to buy is **EN ISO 12217-1:2017**, not the *"ISO 12217-1:2022"* the
row names, which no document in this set corroborates. What it still genuinely
supplies: the Annex A / Table A.1 and Table 4 content at the **2017** edition,
so R-DFH and R-OLH can be re-confirmed against the harmonised text (§7.5), plus
the crew-mass and crowding-fraction basis for the offset-load test.

**3. NEW ROW — ISO 8666:2020 + /A11:2021 (small craft — principal data).**
§7.4. It is the measurand behind six length thresholds we already implement or
depend on, the Directive expressly defers to it (Art. 3(10)), and it is in
neither `PURCHASE_QUEUE` nor `absent()`. **This is the only new absence this
review found, and the absence is in the denominator of a cubic.** An
`absent()` row is owed regardless of whether it is ever bought — that is the
discipline `docs/research/PRODUCTION.md` §2.8 records ISO 7250/15537 as the one
existing hole in.

**4. ISO 12217-3 → up, above 15085 and 9094.** The dayboat SKU is 4–7 m,
`PARAMS["LWL"].low` is 4.0, and `R-SCP` refuses everything under 6 m with no
verdict. The RCD now adds two *free* rules that fire in exactly that band and in
opposite directions (A 3.3 below 6 m, A 3.7 above it), so the band where we have
no stability standard is the band where the free text has just become
informative. Buy edition **EN ISO 12217-3:2017**.

**5. NEW ROW — IEC/EN 62619:2022 (+ EN 62620:2023).** §8.3. Two independent
documents converge on it, one of them (**ES-TRIN Art. 10.11(15)**) *binding*.
It is the source of the cell- and system-level safety bars that both the EMSA
guidance and ES-TRIN decline to restate. Place it **below** the SKU-blocking
rows and above the comfort items — it becomes urgent the moment any electrical
rule is planned, and not before. **Pair it with an `absent()` row now**, so the
electrical domain stops being the one area with no logged absences at all.

**6. NEW ROW — EN ISO 16315:2016 (small craft — electric propulsion system).**
It is the harmonised standard for RCD ER 5.3, and the guide (p. 244) publishes
its full Annex ZA clause map — so we already know *which* clauses answer *which*
sentence of 5.3, which makes this the cheapest possible electrical purchase to
scope. Lower priority than 62619 unless an RCD electrical claim is wanted.

**7. ISO 12215-7 — keep, but correct its justification.** It is **not in the
harmonised standards list** in the guide at all (§3.1). The row's engineering
rationale (multihull scantling loads block a catamaran SKU) stands; a rationale
of "it is the harmonised standard for a catamaran" would not.

**8. ISO 9094 — keep, and record the dated edition now available for free.**
ES-TRIN Art. 26.01(2)(d) names **ISO 9094:2022** as an alternative to Art.
13.03(2)–(6) (§4.4). That does not supply a fire number — `flotation.NOT_SOURCED`
stays as it is — but it dates the thing to buy.

**9. DO NOT QUEUE IEC 63462-1.** The maritime-specific battery standard was
**"under preparation"** as of the EMSA guidance, November 2023 (footnotes 3 and
15). Check publication before spending. Recorded because it is the obvious thing
to reach for and it may not exist.

### 9.2 Two rows the free documents make CHEAPER, not more urgent

- **ES-TRIN itself costs nothing** — CESNI publishes it free, and the 2025/1
  edition is on disk. The Danube SKU's governing standard is the one part of
  this project's compliance surface with no purchase attached at all. That
  asymmetry is worth stating: the inland SKU can be fully sourced for free and
  is the one with no production caller.
- **The design-category rows** no longer need a purchase at all (§7.1).

### 9.3 What did NOT change

`ISO 15085:2024`, `ABYC H-41`, `Panero & Zelnik` and `Larsson & Eliasson` are
untouched by this review — no free document in this set contains anthropometry,
reboarding dimensions, per-zone equipment lists or bilge depth. Their positions
should move only relative to the rows above them.

---

## 10 · Consolidated list of what COULD NOT BE VERIFIED

Gathered here so a later session can decide what is worth re-reading, and so no
claim above is mistaken for a complete read.

**Tooling.** `pdftoppm`/poppler is not installed; the Read tool cannot open a
PDF on this machine at all. Everything was read through `pypdf`'s text layer.
**Any content that is a raster image was therefore invisible unless the images
were extracted separately** — which was done only for the guide's Annex ZA
tables. Installing poppler is the single cheapest way to improve on this review.

| document | what is unread or uncertain |
|---|---|
| RCD guide | The **~60 Annex ZA tables not opened as images** — headings (dated editions) are known, ER rows are not, except for 12215-5, 12217-1/-2/-3, 14945, 14946 and 16315. **Whether the OJEU currently cites these editions** — the guide has no legal force and defers to rsg.be. The content of **ISO/TS 23625**. Whether the stalled 12217 revision has since published. |
| ES-TRIN | **Entry-into-force date of 2025/1 — absent from the PDF entirely.** **Figures 1, 2, 3 of Chapter 4** are images: the sheer-abscissa convention for `x` is unconfirmed. **The Art. 10.03 IP table flattens** — verify before encoding an IP grade. (Art. 10.06's voltage table was re-checked and IS clean — §4.6.) The mathematical-italic font is mis-mapped throughout, so **symbol letters are unreliable while definition lines are not**. Whether Art. 4.02(4)'s symbol is `β` or `B`. Directive (EU) 2016/1629 Art. 2(1)'s 20 m / 100 m³ thresholds are in neither PDF, so `SCOPE_LENGTH_M` and `SCOPE_LBT_VOLUME_M3` are unverified by this review. |
| EMSA | **Figure 1.1** (six BESS power configurations) and **Annex C p. 82** (BESS boundary schematic) have no text layer. Tables 3.1/3.2 column assignment for rows 10, 15, 21 may be wrong. **The document's internal cross-references are broken** (§5 cites a "Chapter 1.3" that does not exist) — do not implement a rule depending on resolving one. |
| SAFEMASS | **Tables 1 and 2** (the MSC 100/5/6 autonomy ladder) are raster images; the full level enumeration is unread. Fault trees and most figures unread. Appendices B/D scanned for numerals, not read line by line. |

**And one thing this file deliberately does not claim.** Every "implementable"
note above is a statement that a number exists in a free text and could be
checked against geometry we already compute. **None of it is a statement that
the resulting check would constitute compliance.** `rules.DISCLAIMER` —
ASSESSMENT AID, NOT CERTIFICATION — is unchanged by anything here, and the RCD's
own architecture is the reason: Art. 14 gives *presumption*, Art. 20 decides who
must supervise, and neither is a thing a Python module can confer on itself.
