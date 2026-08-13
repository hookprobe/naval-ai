# THE ISO SMALL-CRAFT FAMILY — editions, harmonised status, price, and what is free

**Read 2026-08-13.** §1–§7 and §9 are complete and measured. Two sub-sections are
explicitly open and say so where they sit: **§7.7** (academic / vendor secondary
sources for the 12215-5 formulas) and **§8.3** (the wider industry-association
survey), both awaiting a parallel search. Nothing elsewhere depends on them.

**Sibling document: `docs/research/EU-REGULATORY.md`** (read first; this file
does not restate it). That review read the free EU legal texts and found that
*"the free texts state REQUIREMENTS; the paid standards state NUMBERS"*. This
file is the other half: **what the paid standards ARE, what they cost, and how
much of their content is reachable without paying.**

**Four things it changes about the sibling document. All four are corrections,
and §2 carries the evidence.**

1. **`EN ISO 12217-1:2017` IS `ISO 12217-1:2015`.** The EU list gives every
   harmonised reference in the form `EN ISO X:<EN year> ... (ISO X:<ISO year>)`,
   and the RCD row reads *"EN ISO 12217-1:2017 … (ISO 12217-1:2015)"*. The 2017
   is the **European adoption date**, not a newer ISO text.
   EU-REGULATORY.md §3.1(2) and §7.5 conclude that R-DFH and R-OLH *"were
   confirmed against a SUPERSEDED edition"*. **They were not.** The reviewer held
   the ISO text that the harmonised standard adopts.
2. **`ISO 12217-1:2022` is real.** EU-REGULATORY.md §3.1 says the
   `PURCHASE_QUEUE` row naming it is *"an edition no document in this set
   corroborates"*. ISO's catalogue entry `iso.org/standard/79072.html` is
   ISO 12217-1:**2022**, and iTeh hosts the `ISO/FDIS 12217-1` draft that became
   it. It exists — it is simply **not the harmonised edition**, which is still
   the 2015 text. Both statements need to be made together or the row looks
   wrong when it is only mis-justified.
3. **ISO 12215-5:2019 has a `Corrected version 2023-11`,** and the corrections
   land in **Clause 9 (design pressures) and Table 12 (motor-craft pressures)** —
   the exact clauses this project needs. §4.1. Any secondary source predating
   November 2023 may be reproducing formulae ISO has since corrected.
4. **Both electrical standards EU-REGULATORY.md §3.1 lists are DEAD.**
   That table records *"EN ISO 10133:2017 (ELV DC) · EN ISO 13297:2018 (AC)"*
   from the 2024-01-18 RSG guide. MEASURED in the Commission list: **both ceased
   to confer presumption of conformity on 25.10.2025**, withdrawn by Commission
   Implementing Decision **2024/1197** of 25.04.2024, and both are replaced by a
   single merged standard — **EN ISO 13297:2021 + /A1:2022 + /A11:2023
   (ISO 13297:2020), "Electrical systems — Alternating **and direct** current
   installations"**, in force since 25.04.2024. This lands in the one domain
   EU-REGULATORY.md §8.3 identifies as having nothing at all, so it matters:
   **the electrical domain's harmonised standard is now one document, not two,
   and neither of the two the sibling names is current.** §2.4.

---

## 0 · How to read this file, and what it is not

- **It carries no status and no plan.** Gate state is `python -m navalai.gates`;
  outstanding work is `python scripts/reconcile_gaps.py`; the buy list in code is
  `navalai.refdata.PURCHASE_QUEUE`. §9 is a *proposal* with prices attached.
- **Nothing here was implemented.** `navalai/` was read-only for this work.
- **Provenance is graded, and the grade is stated at every claim:**

  | tag | meaning |
  |---|---|
  | **FIRST-PARTY (preview)** | read in ISO's own official preview pages of the standard, distributed by an authorised reseller. This is the standard's own text, just truncated. |
  | **FIRST-PARTY (EU law)** | read in a free, legally operative EU document. |
  | **SECONDARY SOURCE** | a third party says the standard says this. NOT read in the standard. Never to be encoded with `basis='standard-*'`. |
  | **NOT FOUND** | looked for, not found. Recorded so nobody re-runs the search. |
  | **PAYWALLED, price X** | reachable only by paying, and this is the price. |

- **No pirated copy was opened, quoted, or linked.** Full-text uploads of
  ISO 12215-5:2019 and ISO 12215-7:2020 exist on document-sharing sites and were
  returned by ordinary searches. **They were not used and are not cited.** They
  are recorded here as a hazard, because a future session running the same search
  will hit them on the first page of results and needs to know the decision was
  already taken.
- **`iso.org` is unreachable from this machine.** Every request (WebFetch, curl
  with a browser UA, and a public reader proxy) returns **HTTP 403** from a
  Cloudflare bot check. ISO's own CHF prices are therefore quoted only where a
  search-engine snippet carried them, and are flagged as such. Prices below come
  from **SIS (Swedish Institute for Standards)**, which is fetchable and gives a
  consistent, verified figure for every member of the family.

---

## 1 · THE FAMILY TABLE

Harmonised status, dated edition and legal effect come from the European
Commission's **"Summary list of titles and references of harmonised standards"**
for Directive 2013/53/EU — an `.xlsx` **generated 17/3/2026**, downloaded and
parsed for this review. FIRST-PARTY (EU law); it is the legally operative list
and it is free.

- Landing page: https://single-market-economy.ec.europa.eu/single-market/goods/european-standards/harmonised-standards/recreational-craft_en
- Direct xlsx: https://single-market-economy.ec.europa.eu/document/download/6594eaba-a3b0-47e3-baf6-466afc1f0784_en?filename=SummaryListForLegislation_1402.xlsx
- Direct pdf: https://single-market-economy.ec.europa.eu/document/download/2a2ae266-c602-4087-a974-421b8b0d92be_en?filename=SummaryListForLegislation_1402.pdf

Price is the **PDF single-user licence from SIS**, product `SS-EN ISO …`, read
from the product page on 2026-08-13. The Swedish adoption `SS-EN ISO X` is the
`EN ISO X` text — i.e. the ISO text plus the CEN foreword and Annex ZA — so this
is the price of the *harmonised* document, which is the one worth buying.

**MEASURED: the RCD has 62 harmonised references currently in force** (rows with
no `end of legal effect`), out of a much longer historical list. §1.1 below is
the subset this project touches or could touch; it is not the whole 62.

### 1.1 Harmonised under the RCD (presumption of conformity attaches)

| standard, as cited in the OJ | underlying ISO edition | in force since | OJ / decision | price (SIS, PDF) |
|---|---|---|---|---|
| **EN ISO 8666:2020** — Small craft — Principal data | ISO 8666:2020 | 29.06.2022 | OJ L 172, dec. **2022/1029** | **1 937 SEK** |
| **EN ISO 8666:2020/A11:2021** — the European amendment, cited in the same OJ row | — | 29.06.2022 | OJ L 172, dec. **2022/1029** | **687 SEK** |
| EN ISO 12215-1:2018 — Materials: thermosetting resins, glass-fibre reinforcement, reference laminate | ISO 12215-1:**2000** | 05.06.2019 | OJ L 146, dec. 2019/919 | 943 SEK |
| EN ISO 12215-2:2018 — Materials: core materials for sandwich construction, embedded materials | ISO 12215-2:**2002** | 05.06.2019 | OJ L 146, dec. 2019/919 | 943 SEK |
| EN ISO 12215-3:2018 — Materials: steel, aluminium alloys, wood, other materials | ISO 12215-3:**2002** | 05.06.2019 | OJ L 146, dec. 2019/919 | 943 SEK |
| EN ISO 12215-4:2018 — Workshop and manufacturing | ISO 12215-4:**2002** | 05.06.2019 | OJ L 146, dec. 2019/919 | 943 SEK |
| **EN ISO 12215-5:2019** — Design pressures for monohulls, design stresses, scantlings determination | ISO 12215-5:**2019** (2nd ed., *corrected version 2023-11*) | 22.01.2020 | OJ L 17, dec. **2020/50** | **1 988 SEK** |
| EN ISO 12215-6:2018 — Structural arrangements and details | ISO 12215-6:**2008** | 05.06.2019 | OJ L 146, dec. 2019/919 | 1 599 SEK |
| EN ISO 12215-8:2018 — Rudders | ISO 12215-8:2009 + Cor 1:2010 | 05.06.2019 | OJ L 146, dec. 2019/919 | 1 599 SEK |
| EN ISO 12215-9:2018 — Sailing craft appendages | ISO 12215-9:**2012** | 05.06.2019 | OJ L 146, dec. 2019/919 | 1 865 SEK |
| **EN ISO 12217-1:2017** — Stability and buoyancy — non-sailing, L_H ≥ 6 m | ISO 12217-1:**2015** | 15.12.2017 | OJ C 435 | **1 865 SEK** |
| EN ISO 12217-2:2017 — sailing, L_H ≥ 6 m | ISO 12217-2:**2015** | 15.12.2017 | OJ C 435 | 1 865 SEK |
| **EN ISO 12217-3:2017** — boats of L_H < 6 m | ISO 12217-3:**2015** | 15.12.2017 | OJ C 435 | **1 865 SEK** |
| EN ISO 12216:2018 — Windows, portlights, hatches, deadlights and doors — strength and watertightness | ISO 12216:**2002** | 05.06.2019 | OJ L 146, dec. 2019/919 | 1 737 SEK |
| EN ISO 11812:2018 — Watertight cockpits and quick-draining cockpits | ISO 11812:**2001** | 05.06.2019 | OJ L 146, dec. 2019/919 | 1 420 SEK |
| EN ISO 15085:2024 — Protection from falling overboard and means of reboarding | ISO 15085:**2024** | **13.03.2026** | OJ L, dec. **2026/550** | 1 420 SEK |
| EN ISO 9094:2017 — Fire protection | ISO 9094:**2015** | 15.12.2017 | OJ C 435 | 1 420 SEK |
| EN ISO 6185-1:2018 — Inflatable boats, ≤ 4,5 kW | ISO 6185-1:2001 | 05.06.2019 | OJ L 146, dec. 2019/919 | 1 420 SEK |
| EN ISO 6185-2:2018 — Inflatable boats, 4,5–15 kW | ISO 6185-2:2001 | 05.06.2019 | OJ L 146, dec. 2019/919 | 1 250 SEK |
| EN ISO 6185-3:2018 — Inflatable boats, L_H < 8 m, ≥ 15 kW | ISO 6185-3:2014 | 05.06.2019 | OJ L 146, dec. 2019/919 | 1 420 SEK |
| EN ISO 6185-4:2018 — Inflatable boats, 8–24 m, ≥ 15 kW | ISO 6185-4:2011 (corr. 2014-08-01) | 05.06.2019 | OJ L 146, dec. 2019/919 | 1 250 SEK |
| EN ISO 14945:2021 — Builder's plate | ISO 14945:2021 | 09.12.2021 | OJ L 440, dec. 2021/2173 | 789 SEK |
| EN ISO 14946:2021 — Maximum load capacity | ISO 14946:2021 | 09.12.2021 | OJ L 440, dec. 2021/2173 | 687 SEK |
| EN ISO 16315:2016 — Electric propulsion system | ISO 16315:2016 | 09.09.2016 | OJ C 332 | **NOT FOUND** — no SIS product page located under the small-craft category; SIS site search is behind a login. UNPRICED. |
| **EN ISO 8665-2:2024** — Power measurements and declarations — Part 2: **Electric marine propulsion** | ISO 8665-2:2024 | **13.03.2026** | OJ L, dec. **2026/550** | **789 SEK** |
| **EN ISO 13297:2021** + **/A1:2022** + **/A11:2023** — Electrical systems — **alternating AND direct current** installations | ISO 13297:2020 | **25.04.2024** | OJ L, dec. **2024/1197** | **2 752 SEK** (base; amendments not separately priced) |
| EN ISO 8665:2017 — Power measurements, reciprocating IC engines | ISO 8665:2006 | 15.12.2017 | OJ C 435 | not priced — **not applicable to a solar-electric SKU** |
| EN ISO 11592-1:2016 — max propulsion power, L_H < 8 m | ISO 11592-1:2016 | 10.06.2016 | OJ C 209 | **NOT FOUND** (slug not located) |
| EN ISO 11592-2:2021 — max propulsion power, L_H 8–24 m | ISO 11592-2:2021 | 29.06.2022 | OJ L 172, dec. 2022/1029 | 1 097 SEK |

### 1.2 In the ISO family but **NOT harmonised** under the RCD

Buying these buys engineering, not presumption of conformity. Say so when
justifying them.

| standard | edition | scope | price (SIS, PDF) |
|---|---|---|---|
| **ISO 12215-7:2020** | 2020 | Determination of loads for **multihulls** and of their local scantlings **using ISO 12215-5** | 1 737 SEK |
| **ISO 12215-10:2020** | 2020-11 | **Rig loads** and rig attachment in sailing craft | 1 865 SEK |
| ISO 12217-1:2022 | 2022 | newer edition of the stability standard; **not** the harmonised one | not priced |

**Confirmed by absence, twice.** Neither `12215-7` nor `12215-10` appears
anywhere in the Commission's summary list. This corroborates EU-REGULATORY.md
§3.1(3) from the legally operative source rather than from the RSG guide, and it
extends the same finding to Part 10. `PURCHASE_QUEUE`'s 12215-7 row therefore
stands on its engineering rationale (a catamaran SKU) and **cannot** be justified
as "the harmonised standard for a multihull" — there is none.

**12215-7 is not a standalone standard.** Its own title says it determines loads
*"using ISO 12215-5"*, and its scope (FIRST-PARTY, preview, §4.4) says scantlings
*"are then assessed using ISO 12215-5"*. **Buying 12215-7 without 12215-5 buys a
document that cannot be executed.** That is a hard ordering constraint on §9.

### 1.3 Price sources and their confidence

- **SIS (Swedish Institute for Standards), `sis.se`** — VERIFIED. Each price
  above was read out of the product page markup (`<strong>1&#160;988 SEK`) on
  2026-08-13. Paper is the same price as PDF; PDF+paper is ~1,6×
  (e.g. 12215-5: 1 988 / 1 988 / 3 180,80 SEK).
- **`en-standard.eu`** — ISO 12215-5:2019 = **257,42 EUR**, 126 pp (English),
  edition 2, 2019-05-13. VERIFIED individually. Other EUR figures from that site
  were collected in bulk and **three unrelated standards returned the identical
  231,34 EUR**, which is not credible; they are **UNVERIFIED** and not quoted.
- **ISO's own CHF list price** — `iso.org` is 403 from this machine. Two figures
  survive only as search-engine snippets and are **UNVERIFIED**:
  ISO 8666:2020 ≈ **CHF 135**, ISO 12215-10:2020 ≈ **CHF 204**. Do not budget off
  these; budget off SIS.
- **Currency.** No EUR/SEK rate is asserted here. A number this file cannot
  measure is a number this file does not print — §9 totals in SEK.

---

## 2 · WHAT THE OJ LIST ACTUALLY SAYS, AND THE FOUR CORRECTIONS

### 2.1 How to read a harmonised reference

Every row has the shape

    EN ISO <n>:<EN adoption year>
    <English title> (ISO <n>:<ISO edition year>)
    [EN ISO <n>:<year>/A<k>:<year>]

so **two years appear and they mean different things.** The first is when CEN
adopted or re-published it; the second is the ISO text inside. They coincide for
12215-5 (EN 2019 / ISO 2019) and diverge by fifteen years for 12216 (EN 2018 /
ISO 2002). Reading the EN year as the edition of the technical content is the
mistake §2.2 corrects.

### 2.2 The 12217-1 correction, stated precisely

The row, transcribed from the Commission xlsx:

> `EN ISO 12217-1:2017` — *Small craft - Stability and buoyancy assessment and
> categorization - Part 1: Non-sailing boats of hull length greater than or equal
> to 6 m* **(ISO 12217-1:2015)** — in force since 15.12.2017, OJ C 435.

Independently corroborated FIRST-PARTY (preview): **ISO 12215-5:2019's own
Clause 2 (Normative references) cites `ISO 12217-1:2015`, `ISO 12217-2:2015` and
`ISO 12217-3:2015`** — a 2019 standard would not normatively cite a superseded
2015 text if a 2017 revision existed. And the ISO 12217-1:2015 preview's title
page reads *"Third edition, 2015-10-15"*, exactly the string
`review.REVIEW["editions"]["ISO 12217-1"]` records.

**Consequence for `review.py` and Gate 6R: none, and that is the point.** R-DFH
and R-OLH were confirmed against the ISO text the harmonised standard adopts.
EU-REGULATORY.md §7.5's "finding about the gate's scope" is withdrawn — the gate
was not blind to a currency problem, because there was no currency problem.

**What is NOT thereby established:** whether `ISO 12217-1:2022` (which does
exist) changed `phi_O(R)` or the Annex A downflooding-height method. It is not
harmonised, so it confers no presumption, and nothing in this review reads it.

### 2.3 The warning at the top of EU-REGULATORY.md is unchanged and still binds

This file now names `EN ISO 12215-5:2019` from the **legally operative** source
rather than from a non-binding guide. That makes the string *better attested*
and **does not make it holdable**. Gate 6R's bar is the DATED EDITION THE
REVIEWER HELD. Nobody here has held ISO 12215-5. Typing `"ISO 12215-5:2019"`
into `review.py` on the strength of this document would be the same fraud with a
better citation.

### 2.4 The electrical standards moved, and both of the sibling's are dead

Transcribed from the Commission list, with the withdrawal columns:

| reference | in force from | **ceased to confer presumption** | withdrawn by |
|---|---|---|---|
| EN ISO 10133:2012 (ISO 10133:2012) — ELV d.c. | 12.02.2016 | 28.02.2018 | OJ C 435, 15.12.2017 |
| **EN ISO 10133:2017 (ISO 10133:2012) — ELV d.c.** | 15.12.2017 | **25.10.2025** | **dec. 2024/1197**, 25.04.2024 |
| EN ISO 13297:2014 (ISO 13297:2014) — a.c. | 12.02.2016 | 05.06.2019 | OJ L 146, dec. 2019/919 |
| **EN ISO 13297:2018 (ISO 13297:2014) — a.c.** | 05.06.2019 | **25.10.2025** | **dec. 2024/1197**, 25.04.2024 |
| **EN ISO 13297:2021 + /A1:2022 + /A11:2023 (ISO 13297:2020) — a.c. AND d.c.** | **25.04.2024** | — (in force) | — |

The pattern is worth naming because it recurs across this list: **a superseded
reference keeps conferring presumption for a transitional period after its
replacement is cited, and only then ends.** ISO/TC 188's own public news page
states the rule (§6.7): *"A default transitional period of **18 months**, when
both standards (new harmonized standard and superseded harmonized standard)
provide presumption of conformity, is applied in all EU technical harmonization
legislation' sectors and starts by the citation of the standard in OJEU."*
25.04.2024 + 18 months = 25.10.2025, exactly the dates above. **So "is it
harmonised?" has three answers, not two: in force, in transition, or withdrawn.**
Any future edition-currency check should read the `end of legal effect` column
and not merely the presence of a row.

### 2.5 The reverse trap: for two family members, the CURRENT ISO text is NOT the harmonised one

MEASURED, FIRST-PARTY (preview) — both of these exist and are newer than the
harmonised European text by a full edition:

| harmonised (confers presumption) | current ISO edition |
|---|---|
| EN ISO 12216:**2018** = ISO 12216:**2002** | **ISO 12216:2020**, *Second edition 2020-07* |
| EN ISO 11812:**2018** = ISO 11812:**2001** | **ISO 11812:2020**, *Second edition 2020-07*, **+ Amd 1:2024**, and retitled *"Watertight or quick-draining recesses **and cockpits**"* |

(previews: `cdn.standards.iteh.ai/samples/69553/bfeb89d3a7c34581b2d95c1e263bd284/ISO-12216-2020.pdf`
and `cdn.standards.iteh.ai/samples/84704/2c475791ae7747b1a43634971135a477/ISO-11812-2020-Amd-1-2024.pdf`)

**Eighteen years separate the harmonised windows standard from the current ISO
one, and the harmonised cockpit standard from its successor.** Buying "the
latest ISO 12216" buys a document that confers **no** presumption of conformity
under the RCD. Whichever is bought, the `review.py` edition string must record
which — and this is the same failure mode as §2.2 read from the other end: there
the EN year was mistaken for a newer ISO text; here a genuinely newer ISO text is
not the legal one.

**And 11812 is moving again.** ISO/TC 188's 2026 plenary decided to **start a
revision of ISO 11812** (§6.7). A purchase of 11812 today buys a text that is
already superseded once and is being revised a second time.

---

## 3 · ISO 8666 — THE MEASURAND, CHARACTERISED

The priority item. It is the standard RCD Art. 3(10) defers to for hull length,
and hull length keys six thresholds this project implements or depends on
(EU-REGULATORY.md §7.4), one of them cubic in L_H.

### 3.1 Identity, edition and price

**FIRST-PARTY (preview).** Title page, ISO's official preview:

> `Small craft — Principal data` / `Petits navires — Données principales`
> **INTERNATIONAL STANDARD ISO 8666, Third edition, 2020-10**
> Reference number `ISO 8666:2020(E)`, © ISO 2020

- Harmonised as **EN ISO 8666:2020 + EN ISO 8666:2020/A11:2021**, in force
  **29.06.2022**, OJ L 172, Commission Implementing Decision **2022/1029**.
- **Price: 1 937 SEK** (SIS, `SS-EN ISO 8666:2020`, PDF) **plus 687 SEK** for
  `SS-EN ISO 8666:2020/A11:2021`, which is a **separate SIS product** — both
  measured 2026-08-13. **Total 2 624 SEK.** The OJ cites the amendment in the
  same row as the base standard, so both are needed for the harmonised document.
  An `/A11` in CEN practice is a *European* amendment (typically the Annex ZA and
  scope alignment), i.e. exactly the part that makes it harmonised.
- Preview source: https://cdn.standards.iteh.ai/samples/79071/5b10fa79b7f949158a2452264bdaed04/ISO-8666-2020.pdf

**FIRST-PARTY (preview), Foreword:** the third edition *"cancels and replaces the
second edition (ISO 8666:2016), of which it constitutes a **minor revision**"*,
with exactly two changes: alignment to ISO/IEC Directives Part 2 (adding
Clause 2, renumbering the rest), and moving the *"allowance for the maximum mass
of optional equipment and fittings not included in the manufacturer's basic
outfit"* from 6.6 (Maximum load) to **7.8 (Maximum load condition)**.

That second change is not cosmetic for us: it is the same `mMBP` vs `mLDC`
optional-equipment question EU-REGULATORY.md §3.8 records as a live conflict
between EN ISO 14945/14946:2021 and the ISO 12217:2015 worksheets. **8666:2020
moved the allowance from the maximum LOAD to the maximum load CONDITION**, which
is the vocabulary the conflict turns on.

### 3.2 Scope — verbatim

**FIRST-PARTY (preview), Clause 1:**

> "This document establishes definitions of main dimensions and related data and
> of mass specifications and loading conditions. It applies to small craft having
> a length of the hull (L_H) of up to 24 m."

**Clause 2: "There are no normative references in this document."** It is a
terminal node — buying it unblocks its dependants and depends on nothing.

### 3.3 The clause map, so a purchase can be aimed

**FIRST-PARTY (preview), Contents.** Page numbers are the standard's own.

    1  Scope                                                    1
    2  Normative references                                     1
    3  Terms and definitions                                    1
    4  Symbols, designations and units                          3
    5  Measurements                                             4
       5.2.2  Maximum length, Lmax                              4
       5.2.3  Length of the hull, LH                            4
       5.2.4  Waterline length, LWL                             7
       5.3.2  Maximum beam, Bmax                                8
       5.3.3  Beam of hull, BH                                  8
       5.3.4  Beam, waterline, BWL                              8
       5.3.5  Maximum beam, waterline, BWLmax                   8
       5.3.6  Beam between hull centres, BCB                    8
       5.4.1  Maximum depth, Dmax                               9
       5.4.2  Midship depth, DLWL/2                             9
       5.4.3  Freeboard, F         (5.4.3.2 FA, .3 FM, .4 FF)  10
       5.4.4  Draught, T   (.2 Tmax, .3 Tmin, .4 TC canoe body) 10
       5.4.5  Draught, air, Ha                                 10
       5.4.6  Headroom                                         11
       5.5.1  Deadrise angle, beta                             11
       5.5.2  Reference sail area, AS                          12
       5.5.3  Standard sail area, A'S                          12
       5.5.4  Windage area, Alv                                12
       5.5.5  Volume of the craft, V  (VH hull, VS superstr.)  12
    6  Masses  (6.1 mN, 6.2 mG, 6.3 mLC, 6.4 mP, 6.5 mT, 6.6 mML)  13
    7  Loading conditions                                      19
       7.1 test · 7.2 ready-for-use · 7.3 FULLY LOADED READY-FOR-USE
       7.4 empty · 7.5 light craft · 7.6 minimum operating
       7.7 loaded arrival · 7.8 MAXIMUM LOAD CONDITION
    8  Tolerances (8.1 published data, 8.2 preliminary spec,
                  8.3 reference lengths)                       21

**Clause 8, "Tolerances", is the sleeper.** This project publishes computed
principal data with `{value, tier, sigma}`. ISO 8666 has a normative clause on
how much published data may deviate, split into *published data*, *preliminary
specification* and *reference lengths*. **NOT FOUND: the tolerance values** — they
are past the preview cut. They are the natural external anchor for `sigma` on
every principal dimension the export emits, and no other standard in the family
supplies them.

### 3.4 L_H — the definition, verbatim, and what it costs us to be missing it

**FIRST-PARTY (preview), 5.2.1 and 5.2.3:**

> "**5.2.1 General.** The lengths of a craft shall be measured parallel to the
> maximum load waterline/reference waterline and craft centreline as the distance
> between two vertical planes, perpendicular to the centreplane of the craft."
>
> "**5.2.3 Length of the hull, L_H.** The length of the hull (L_H) shall be
> measured in accordance with 5.2.1, one plane passing through the foremost part
> of the craft and the other through the aftermost part of the craft.
>
> This length includes all structural and integral parts of the craft, such as
> stems or sterns, bulwarks, and hull/deck joints.
>
> This length **excludes removable parts that can be detached in a
> non-destructive manner and without affecting the structural integrity of the
> craft**, e.g. spars, bowsprits, pulpits at either end of the craft, stemhead
> fittings, rudders, outdrives, outboard motors and their mounting brackets and
> plates, diving platforms, boarding platforms, rubbing strakes, and fenders **if
> they do not act as hydrostatic support when the watercraft is at rest or
> underway**.
>
> With multihull craft, the length of each hull shall be measured individually.
> The length of the hull, L_H, shall be taken as the **longest** of the
> individual measurements."

and, for contrast, **5.2.2 Maximum length, L_max** *includes* fixed spars,
bowsprits, pulpits, rudders, outdrives, waterjets, diving and boarding platforms,
rubbing strakes and permanent fenders, measured *"in their normal operating
condition to their maximum lengthwise extension when the craft is underway"*, and
excludes only outboard motors and *"any other type of equipment that can be
detached without the use of tools"*.

**This is the missing measurand, and it is now readable for free.**
`iso12217.hull_length_m()` substitutes `L_WL`. Against the definition above, that
substitution is wrong in a *knowable* direction and by a *knowable* mechanism:
L_H is measured at the maximum-load waterline **between planes through the
foremost and aftermost parts of the hull structure**, not at the waterline
intersection, so on any hull with stem rake, transom overhang or a bulwark
L_H > L_WL, and `hull_length_m()` **understates** it. EU-REGULATORY.md §7.4 says
understating flips RCD A 3.3 on and A 3.7 off, and one of those is the unsafe
direction. The definition confirms the sign of the error.

**What the preview does NOT give, and why the standard is still worth buying:**
Figure 1 (monohull L_max / L_H) and Figure 2 (multihull) are **images with no
text layer** in the preview, and Figure 1's own annotation *"a Hull ends here"*
is the whole content of the rake/transom convention. Clauses 5.2.4 (L_WL),
5.4.3 (freeboard F, F_A, F_M, F_F), 5.4.4 (T, T_max, T_min, **T_C canoe body**)
and 5.5.1 (deadrise β) are past the cut. **T_C and β are inputs to
ISO 12215-5 Tables 7, 12 and 13** (§4.2), so 8666 is not merely a length
standard for us — it defines two of the scantling inputs.

### 3.5 What else the preview hands over free

**FIRST-PARTY (preview), Clause 3, verbatim:**

- **3.6 loaded displacement, `mLDC`** — *"mass of water displaced by the craft,
  including all appendages, when in the fully loaded ready-for-use condition"*
  (condition described in 7.3). This is the definition
  `rules/iso12215.assess(mldc_kg, …)` and `iso12217` both depend on, and it has
  never had a citation in this tree.
- **3.10 / 3.11 — the sailing / non-sailing discriminator, closed form:**

      non-sailing boat:  A_S <  0,07 · mLDC^(2/3)
      sailing boat:      A_S >= 0,07 · mLDC^(2/3)

  with `A_S` the reference sail area (3.12): *"actual profile area of sails set
  abaft a mast, plus the maximum profile areas of all masts, plus reference
  triangle area(s) forward of each mast"*. **This is directly implementable and
  it is the WINDWING SKU's scope test** — whether a kite/wing-rigged craft is a
  "sailing boat" for 12217 and 12215-5 purposes is decided by this inequality,
  not by intent. `PURCHASE_QUEUE`'s 12217-2 row says the WindWing SKU *"must
  EXTEND R-SCP rather than bypass it"*; **the criterion for which branch it takes
  is now free.**
- **3.2 `WL_ref`** — the maximum load waterline / reference waterline, and
  5.1: *"Measurements shall be established with the craft at rest at the maximum
  load waterline/reference waterline, WL_ref, unless otherwise stated."*
- **3.4 transom beam `B_T`** — *"maximum width of the hull at the transom at or
  below the sheerline, excluding extensions, handles and fittings"*, with
  Note 1: *"Where spray rails act as chines or part of the planing surface, they
  are included"*, and Note 2: for a rounded/pointed stern, or a transom beam less
  than half the maximum beam, `B_T` is the widest beam at or below the sheerline
  **at the aft quarter length of the hull**.
- **3.3 sheerline** — *"intersection between deck and hull, for rounded deck
  edges the natural intersection, or, where no deck is fitted or the hull extends
  above the deck (bulwark), the upper edge of the craft's hull."*
- **3.7 `V_D` displacement volume**, with the note that a water density other
  than salt water at **1 025 kg/m³** must be stated.
- **Table 1 (complete symbol list)**, transcribed FIRST-PARTY (preview):

      A_lV windage area m2 (5.5.4) · A_S reference sail area m2 (5.5.2)
      A'_S standard sail area m2 (5.5.3) · B_CB beam between hull centres m (5.3.6)
      B_H beam of hull m (5.3.3) · B_max maximum beam m (5.3.2)
      B_WL beam waterline m (5.3.4) · B_WLmax max beam waterline m (5.3.5)
      B_T transom beam m (3.4) · D_max maximum depth m (5.4.1)
      D_LWL/2 midship depth m (5.4.2) · F freeboard m (5.4.3)
      F_A aft (5.4.3.2) · F_F forward (5.4.3.4) · F_M amidships (5.4.3.3)
      H_a air draught m (5.4.5) · L_H length of hull m (5.2.3)
      L_max maximum length m (5.2.2) · L_WL waterline length m (5.2.4)
      m_G gross shipping mass kg (6.2) · m_LDC loaded displacement kg (3.6)
      m_LC light craft mass kg (6.3) · m_N net shipping mass kg (6.1)
      m_P performance test mass kg (6.4) · m_T mass on trailer kg (6.5)
      m_ML maximum load kg (6.6) · T draught m (5.4.4)
      T_C draught canoe body m (5.4.4.4) · T_max (5.4.4.2) · T_min (5.4.4.3)
      V_D displacement volume m3 (3.7) · V volume of craft m3 (5.5.5)
      V_H volume of hull (5.5.5.2) · V_S volume of superstructure (5.5.5.3)
      WL waterline (3.1) · WL_ref maximum load waterline (3.2)
      beta deadrise angle degrees (5.5.1)

  **Note `T` vs `T_C`.** ES-TRIN has the same distinction (its Art. 1.01(4.23)
  vs (4.24) on keel inclusion) and EU-REGULATORY.md §4.1 records that *"which of
  the two `ev.hydro.draft` is, is not recorded anywhere"*. ISO 8666 makes it a
  third place the same ambiguity lives, and `T_C` (canoe body) is what
  ISO 12215-5 Tables 12 and 13 consume. Whatever `ev.hydro.draft` is, it needs
  saying once, in one place.

### 3.6 The bottom line on 8666

**BUY IT FIRST.** It is the cheapest way to remove the largest number of
unsourced definitions, it has no normative dependencies, and it is the input
vocabulary of every other standard in the family — ISO 12215-5's own Clause 4
closes with *"Unless otherwise specified, all dimensions, measured in mLDC
condition, are according to ISO 8666."* **1 937 SEK + the /A11:2021 amendment.**

---

## 4 · ISO 12215-5 — WHAT THE OFFICIAL PREVIEW GIVES, FREE

Source, FIRST-PARTY (preview), 14 pages:
https://cdn.standards.iteh.ai/samples/69552/019bbe6cf9164ddf8c3ab509bee75531/ISO-12215-5-2019.pdf

**No formula from the body of ISO 12215-5 is reproduced in this section, because
none is in the preview.** What the preview gives is the **complete map** — every
clause, every annex, every symbol, and the exact table each quantity lives in.
That is enough to (a) cite clauses correctly, (b) know exactly what a purchase
buys, and (c) date and check any secondary source in §7.

### 4.1 Identity, and the correction nobody has

**Title page, verbatim:**

> `INTERNATIONAL STANDARD ISO 12215-5` — *Small craft — Hull construction and
> scantlings — Part 5: Design pressures for monohulls, design stresses,
> scantlings determination*
> **Second edition 2019-05** · `ISO 12215-5:2019(E)` · © ISO 2019
> **Corrected version 2023-11**

**Foreword, verbatim:**

> "This corrected version of ISO 12215-1:2019 incorporates the following
> corrections:
> — errors in formulae, text and values in **Clause 7, Clause 9**, D.1.2, H.3.3,
> H.4, and **Tables 12, 17**, A.3, A.4, A.5, A.7, A.8, A.12, A.13, B.1, B.2, C.5,
> E.1, I.1 and K.1 have been corrected."

(The "ISO 12215-1:2019" in that sentence is ISO's own typo for 12215-5; the
document is 12215-5 throughout.)

**This is the single most important dating fact in this file.** Clause 7 is
*Dimensions of panels and stiffeners*; **Clause 9 is *Design pressures***;
**Table 12 is *motor craft design pressures*** and **Table 17 is *design stresses
by material***. Those four are precisely what `navalai/rules/iso12215.py` needs.
So:

- **Buy the corrected version, not "the 2019 edition" — and the obvious purchase
  may not be it.** MEASURED on the SIS product page for `SS-EN ISO 12215-5:2019`
  (read 2026-08-13): **approved 2019-06-18, 144 pages, status Valid,
  1 988 SEK PDF**, replacing `SS-EN ISO 12215-5:2008`, `…/A1:2014` and
  `SS-EN ISO 12215-5:2018`. **The page makes no mention of a corrected version,
  amendment or corrigendum.** The CEN adoption was approved in June 2019 and the
  ISO correction is dated November 2023, so on the face of it **the harmonised
  EN document predates the corrections and may carry the uncorrected formulae in
  Clause 7, Clause 9 and Tables 12 and 17.**

  This is the sharpest purchasing trap in this file. The document that confers
  presumption of conformity (the EN) and the document that is arithmetically
  current (the ISO corrected version) **may not be the same text**, and the
  clauses where they could differ are exactly the four this project needs.
  **UNVERIFIED and worth an email before paying:** ask SIS (or ISO) explicitly
  whether the PDF supplied is the 2023-11 corrected version. Record the answer
  here. If they are different, buy **both** — 1 988 SEK for the EN (for the
  Annex ZA and the presumption) and the ISO copy for the corrected numbers — or
  at minimum know which one is on the disk when a coefficient is transcribed.
  (144 EN pages against 126 ISO pages is the CEN foreword plus Annex ZA, not
  extra technical content.)
- **Any secondary source in §7 dated before 2023-11 is quoting a text ISO has
  since corrected in the exact clauses we care about.** A formula recovered from
  a 2020 or 2021 paper is not thereby wrong, but it is **not confirmable** as the
  current text and must not be encoded as if it were.

**Foreword, changes from the 2008 first edition** (verbatim, abridged to the
items that touch us) — this is also how to tell which edition a secondary source
is really quoting:

> "— definition of a theoretical hull/deck limit height Z_SDT in Table 3;
> — **renaming of n_CG into k_DYN** in Table 7;
> — **lowering of the values of k_L in the aft part of the craft** in Table 8;
> — **deletion of k_AR min**, to better consider large panels, mainly sandwiches,
> in Table 9;
> — improvement of the values of k_SUP in Table 10;
> — **modification of design pressures for motor and sailing craft in Tables 12
> & 13**;
> — **modification of design stresses introducing k_BB and k_AM factors in
> Tables 15 to 17**;
> — move of the previous assessment method (now called "simplified") in Annex A;
> — new Annex I only recommending minimum thickness for single skin and sandwich
> **that are no longer mandatory**;
> — for clarity, this edition generally uses tables to present formulas and
> requirements."

**Three tests for dating a secondary source, derived from that list:**
1. If it writes **`n_CG`**, it is quoting **2008**. If it writes **`k_DYN`**, 2019.
2. If it uses a **`k_AR min`** floor, it is quoting **2008** — that floor was
   deleted in 2019.
3. If it treats **minimum thickness as mandatory**, it is quoting **2008** —
   Annex I is informative and recommending in 2019.

Also, verbatim: *"NOTE The mechanical properties of ISO 12215-1 to -3 are
largely superseded by the ones of this document."* **That is ISO saying Parts
1–3 are largely redundant once you hold Part 5** — directly relevant to §9,
because Parts 1/2/3 are 943 SEK each and Part 5 supersedes most of their content.

### 4.2 The symbol table — Table 1, complete, with the table each symbol lives in

**FIRST-PARTY (preview), Clause 4, Table 1.** This is the whole variable
dictionary of the standard. The right-hand column is ISO's own cross-reference
and is what makes a targeted read of a purchased copy possible.

**Lengths and beams**

| symbol | unit | meaning | lives in |
|---|---|---|---|
| `B_C` | m | Chine beam per Figure 1, at 0,4 L_WL from its aft end | Fig 1, Table 7 |
| `GZ_MAX<60` | m | Max righting-moment lever, light and stable sailing craft, all stability-increasing devices active | Table 11 |
| `L_H` | m | Length of the hull | Clause 1 |
| `L_WL` | m | Length of waterline at rest, Figure 2 | Tables 3, 7, 8, 11 |
| `T_C` | m | **Max depth of canoe body**, Figure 2 | Tables 12 & 13 |
| `Z_C` | m | Local height of chine above WL | Fig 6d, Table 12 |
| `Z_Q` | m | Local height of point Q, centre of a panel or stiffener, above WL | Fig 6, Tables 12 & 13 |
| `Z_SDA` | m | Local height of **actual** side/deck limit above WL | Fig 6, Tables 12 & 13 |
| `Z_SDT` | m | Local height of **theoretical** side/deck limit above WL | Fig 6, Tables 3, 12 & 13 |

**Displacement, angles, speed**

| symbol | unit | meaning | lives in |
|---|---|---|---|
| `V` | **knots** | Max speed at mLDC, used for motor craft with V ≥ 5·√L_WL and for k_L of sailing craft with k_SLS > 1 | 3.6–3.8, Tables 7 & 8 |
| `mLDC` | kg | Mass in maximum load condition | 3.2, Tables 7, 12 & 13 |
| `β_0,4` | ° | **Deadrise angle at 0,4 L_WL from its aft end, taken as 10 < β_0,4 ≤ 30** | Fig 1, 6.1, Table 7 |

**Panel and stiffener geometry**

| symbol | unit | meaning | lives in |
|---|---|---|---|
| `A_D` | m² | **Design area under consideration** (panel or stiffener) | Table 9 |
| `b` | mm | Short unsupported dimension of a panel | Table 5, Figs 3–5 |
| `l` | mm | Long unsupported dimension of a panel | Table 5, Figs 3–5 |
| `c_b`, `c_l` | mm | Transverse / longitudinal camber of a curved panel | A.8.2.2, Fig A.7 |
| `s` | mm | Stiffener spacing between axes | Table 5, Figs 3 & 4 |
| `l_u` | mm | Stiffener span between axes | Table 5, Figs 3 & 4 |
| `x` | m | **Distance of mid panel or stiffener from aft end of L_WL** | Table 4, Fig 2 |
| `b_b` | mm | Base width of top-hat stiffeners or equivalent | Figs 3c, 4, A.13 |
| `b_e` | mm | Effective breadth of attached plating | A.12.5, Fig A.13 |
| `A_w` | cm² | Area of the shear web of a stiffener | Table A.9, H.4, G.4 |
| `SM` | cm³ | Section modulus of a stiffener | 3.5, Table A.9, Annex G, H.4 |
| `EI_NA` | N·mm² | Second moment × E at neutral axis | 3.4, Table A.9, H.4 |

**Factors — the ones the project stands in for**

| symbol | meaning | **lives in** |
|---|---|---|
| **`k_DC`** | **Design category factor** | **Table 6** |
| **`k_DYN`** | **Dynamic load factor** (`k_DYN`, `k_DYN1`, `k_DYN2`) | **Table 7** |
| **`k_L`** | **Longitudinal pressure distribution factor** | **Table 8 & Figure 7** |
| **`k_AR`** | **Area pressure reduction factor** | **Table 9** |
| **`k_R`** | **Structural component and craft type factor** | **Table 9** |
| **`k_SUP`** | Superstructure pressure reduction factor | Table 10 |
| **`k_SLS`** | Slamming pressure factor, light and stable sailing craft | Table 11 |
| **`k_BB`** | **Boat building quality factor** | **Tables 15 & 17** |
| **`k_AM`** | **Assessment method factor** | **Tables 16 & 17** |
| **`k_C`** | **Curvature correction factor for plating** | **A.8.2.2 & Table A.3** |
| `k_CS` | Curvature correction factor for stiffeners | Table A.10 |
| **`k_2`** | **Panel aspect ratio factor for BENDING MOMENT** (`k_2b`, `k_2l`) | **Tables A.2 & A.4** |
| `k_SH` | Panel aspect ratio factor for SHEAR force (`k_SHb`, `k_SHl`) | Table A.2 |
| `AR_E`, `AR_G` | Effective / geometric aspect ratio of a panel | Table A.2 |
| `k_CH` | Chine angle correction factor | A.5.4, Fig A.2 |
| `k_BM`, `k_SF` | Bending-moment / shear-force factor for stiffener | Table A.8 |
| `k_SM`, `k_AS` | Actual/design bending-moment and shear-force factors in a stiffener | Tables A.12, A.12.3 |
| `k_G` | "GREEN" factor for laminates | Tables C.6, C.9, C.10 |
| `k_5`…`k_10` | Single-skin minimum thickness or fibre factor | **Table I.1** |

**Pressures — every one, with its table**

| symbol | meaning | table |
|---|---|---|
| **`P_BMD`** | **Motor craft bottom pressure in DISPLACEMENT mode** | **Table 12** |
| **`P_BMD BASE`** | **Motor craft BASE bottom pressure, displacement mode** | **Table 12** |
| `P_BMP` / `P_BMP BASE` | Motor craft bottom pressure / base pressure, **planing** mode | Table 12 |
| **`P_BM MIN PLT`** | Motor craft bottom **minimum PLATING** pressure (displ./planing) | Table 12 |
| **`P_BM MIN STF`** | Motor craft bottom **minimum STIFFENER** pressure (displ./planing) | Table 12 |
| `P_SMD` / `P_SMP` | Motor craft **side** pressure, displacement / planing | Table 12 |
| `P_SMD MIN PLT` | Minimal motor craft side plating pressure | Table 12 |
| `P_DM` / `P_DM BASE` | Motor craft **deck and cockpit bottom** pressure / base | Table 12 |
| `P_SUP M` | Motor craft **superstructure** pressure | Table 12 |
| `P_BS`, `P_BS BASE`, `P_BS MIN PLT`, `P_BS MIN STF` | Sailing craft bottom pressures | Table 13 |
| `P_SS`, `P_SS MIN PLT`, `P_SS MIN STF` | Sailing craft side pressures | Table 13 |
| `P_DS`, `P_DS BASE`, `P_SUP S` | Sailing craft deck / superstructure pressures | Table 13 |
| `P_WB` / `P_TB` | **Watertight boundaries / integral tank boundaries** | **Table 14** |

**Stresses**

| symbol | meaning | table |
|---|---|---|
| **`σ_d`, `τ_d`** | **Design direct / shear stress for plate or stiffener** | **Table 17** |
| `σ_u`, `τ_u` | Ultimate direct / shear stress | Table 17 |
| `σ_dco`, `τ_dco`, `σ_uco`, `τ_uco` | Sandwich **core** design / ultimate stresses | Table 17 |
| `E`, `G`, `E_co`, `G_co` | Elastic / shear moduli, laminate and core | Table 17 |
| `w` | kg/m² dry fibre reinforcement mass per m² | 11.1, Annexes A, C, H, I |
| `F_d`, `M_d` | Design shear force / bending moment | Tables A.4, A.8 |

### 4.3 Four findings this table alone produces about `navalai/rules/iso12215.py`

Stated as findings, not fixes. The module is honest — it says `basis='approx'`
and *"coefficients await licensed-text parity review"* — but the *shape* is now
knowably wrong in four specific ways, and shape errors do not get fixed by
buying better coefficients.

1. **The single `max(10, …)` floor is two different floors in the standard.**
   `design_pressure_bottom` returns `max(10.0, 2.4·mLDC^0.33 + 20.0)`. Table 12
   carries **`P_BM MIN PLT` and `P_BM MIN STF` as separate symbols**. A plating
   check and a stiffener check do not share a minimum.
2. **`P_BMD` is not `P_BMD BASE`.** Both exist in Table 12 as distinct symbols.
   The module's stand-in has the *shape* of a BASE pressure
   (`2,4·mLDC^0.33 + 20`) and is used directly as the design pressure, with no
   `k_AR`, `k_DC` or `k_L` applied. Every one of those three factors is a real
   symbol in Table 6 / 8 / 9, and `k_DC` is the design-category factor — **so the
   module's bottom pressure is currently INDEPENDENT of design category**, while
   the whole point of the RCD categorisation is that it should not be.
3. **`k_2` is the aspect-ratio factor for BENDING MOMENT specifically**, and it
   has two forms, `k_2b` and `k_2l`, for the short and long panel directions
   (Tables A.2 and A.4). The module takes a single scalar `k2: float = 0.5` and
   its docstring says *"0.308..0.5; 0.5 for long panels"*. The 0.5 default is
   therefore the long-panel asymptote of one of two related factors, applied
   unconditionally. There is a separate shear family, `k_SH` (`k_SHb`, `k_SHl`),
   that the module has no equivalent of at all — **no shear check exists.**
4. **The design stress `σ_d` is a Table 17 quantity modulated by `k_BB` (boat
   building quality) and `k_AM` (assessment method).** The module has
   `SIGMA_D_OKOUME = 15.0` and nothing else. Two factors that the 2019 revision
   *introduced specifically to modulate design stresses* are absent, and
   `select_stock_thickness_m` divides by `σ_d` — so its output scales as
   `1/sqrt(σ_d)` and every missing factor lands directly on ply thickness.

**Plywood lives in Annex F**, *"Wood/plywood laminate properties and
calculations"*, **normative, pages 80–88** — nine pages. That is the target of a
12215-5 purchase for this project's material.

### 4.4 Scope, normative references, and the definitions that ARE free

**FIRST-PARTY (preview), Clause 1, verbatim (abridged):**

> "This document defines the dimensions, design local pressures, mechanical
> properties and design stresses for the scantlings determination of monohull
> small craft with a hull length (L_H) or a load line length of up to 24 m. It
> considers all parts of the craft that are assumed to be watertight or
> weathertight when assessing stability, freeboard and buoyancy in accordance
> with ISO 12217. …
> This document covers small craft built from the following materials:
> — fibre-reinforced plastics, either in single skin or sandwich construction;
> — aluminium or steel alloys;
> — **glued wood or plywood (single skin or sandwich), excluding traditional wood
> construction**;
> — non-reinforced plastics for craft with a hull length less than 6 m (see
> Annex D). …
> Throughout this document, unless otherwise specified, dimensions are in (m),
> areas in (m²), masses in (kg), forces in (N), moments in (N.m), **pressures in
> kN/m² (1 kN/m² = 1 kPa)**, stresses and elastic modulus in N/mm² (1 N/mm² =
> 1 MPa). Max(a;b;c) means that the required value is the maximum of a, b, and c
> …"

Two operational consequences: **"excluding traditional wood construction"** —
a strip-plank or carvel hull is out of scope, glued ply is in; and the units line
confirms `kN/m²` for pressure and `N/mm²` for σ_d, which is what the module uses.

**Clause 2, Normative references — verbatim, complete:**

> ISO **8666:2016**, *Small craft — Principal data*
> ISO 12215-9:2012, *… Part 9: Sailing craft appendages*
> ISO 12217-1:2015 · ISO 12217-2:2015 · ISO 12217-3:2015

**Note the dated `ISO 8666:2016`.** 12215-5:2019 normatively binds to the
**2016** edition of 8666 while the harmonised principal-data standard is
**EN ISO 8666:2020**. Because the reference is *dated*, "only the edition cited
applies" — so a strict 12215-5 calculation is against 8666:**2016**. Practically
this is benign (§3.1: 2020 is a *minor* revision of 2016 with two listed
changes), but it should be said out loud rather than discovered later, and it is
a reason the 2020 purchase is not strictly what 12215-5 asks for.

**Clause 3, terms — the discriminator that decides which pressure column applies:**

> "**3.7 displacement craft** — craft whose maximum speed in flat water and mLDC
> condition, declared by its manufacturer, is such that **V < 5·√L_WL**"
> "**3.9 planing craft** — … such that **V ≥ 5·√L_WL**"
> (V in knots, L_WL in m; Note: *"This speed/length ratio limit has been
> arbitrarily set up in this document"*)
>
> "**3.8 displacement mode** — mode of running of a craft in the sea such that
> its mass is mainly supported by buoyancy forces"
> "**3.11 non-walking area** — area of the working deck, cockpit or
> superstructures of a monohull **at an inclination of more than 25° to the
> horizontal in the longitudinal direction or more than 55° to the horizontal in
> the transverse direction**. Note: All other areas … are deemed **walking
> areas**."

**`V < 5·√L_WL` is FIRST-PARTY, free, and directly implementable.** It is the
gate on which of Table 12's two motor-craft columns applies, and this project's
solar-electric SKUs sit far below it — a 12 m hull is a displacement craft up to
17,3 knots. `rules/iso12215.py` currently hard-codes the displacement path with
no test; **the test is now citable.**

The **25° / 55° walking-area rule** is a pure geometry predicate over the
arrangement surface and needs nothing paid.

### 4.5 The clause map — what a purchase buys, by page

**FIRST-PARTY (preview), Contents:**

    1  Scope 1 · 2 Normative references 2 · 3 Terms and definitions 2
    4  Symbols 4
    5  General 6      5.1 Materials · 5.2 Overall procedure (Table 2)
    6  Main dimensions, data and areas 7
    7  Dimensions of panels and stiffeners 9
       7.2 Rectangular grid 10 · 7.3 Non-rectangular (trapezoidal/triangular) 12
       7.4 Pressure on a panel or a stiffener 14
    8  PRESSURE ADJUSTING FACTORS 15
       8.2 k_DC 15 · 8.3 k_DYN 15 · 8.4 k_L 16 · 8.5 k_AR 17
       8.6 k_SUP 18 · 8.7 k_SLS 18
    9  DESIGN PRESSURES 19
       9.1 motor craft 19 · 9.2 sailing craft 21
       9.3 watertight bulkheads and integral tank boundaries 22
           9.3.2 wash plates · 9.3.3 collision bulkheads
           9.3.4 non-watertight/partial · 9.3.5 lifting-keel wells
           9.3.6 transmission of pillar loads · 9.3.7 loads from outboard engines
    10 MECHANICAL PROPERTIES AND DESIGN STRESSES 24
       10.1 k_BB 24 · 10.2 k_AM 25
       10.3 design stresses by material and calculation method 25
    11 Methods for structural analysis and scantlings determination 27
       11.1 the six available methods · 11.2 M1 "Simplified" 27
       11.3 M2 "Enhanced" (ply by ply) · 11.4 M3 "Developed"
       11.5 M4 "Direct test" · 11.6 M5 "FEM" 28 · 11.7 M6 drop test 29
       11.8 "Good practice" minimal thickness 30
    12 Craft for professional use: commercial craft and workboats 30
    13 Owner's manual 30 · 14 Application form 30

    Annex A (normative)  Application of methods of analysis 1 to 3 of Table 18   31
    Annex B (normative)  Mechanical properties and design stress of METALS       58
    Annex C (normative)  FRP laminates properties and calculations               61
    Annex D (normative)  Drop test for craft < 6 m                               73
    Annex E (normative)  Sandwich calculations                                   76
    Annex F (normative)  WOOD/PLYWOOD laminate properties and calculations       80
    Annex G (normative)  Geometric properties of stiffeners                      89
    Annex H (normative)  Laminate stack analysis for plating and stiffeners     101
    Annex I (informative) "Good practice" values for minimum thickness or dry
                          fibre mass                                            116
    Annex J (normative)  Commercial craft and workboats — additional reqts      118
    Annex K (informative) Loads induced by outboard engines                     121
    Annex L (informative) Application form of ISO 12215-5                       123
    Bibliography                                                                125

**For this project the purchase is Clauses 8, 9, 10 and Annexes A and F —
roughly pages 15–30, 31–57 and 80–88, about 60 of 126 pages.**

**Cross-check against the RSG guide's Annex ZA** (EU-REGULATORY.md §3.2), which
maps RCD ER 3.1 *Structure* to *"All clauses except Clause 12 and Annex J"* —
i.e. everything except the commercial-craft material. Consistent.

### 4.6 What the Introduction says about what the standard is FOR

**FIRST-PARTY (preview), Introduction, verbatim:**

> "This document is intended to be a tool to determine the scantlings of a craft
> as per minimal requirements. **It is not intended to be a structural design
> procedure.** … it should only be used to check the main structural features of
> a craft but should not be used as a scantlings guide. …
> The scantlings requirements aim at providing adequate **local** strength.
> **Serviceability issues such as deflection under normal operating loads, global
> strength and its connected shell and deck stability are not addressed in this
> document.**"

**This is ISO stating this project's own disclaimer, in ISO's words.**
`rules.DISCLAIMER` (ASSESSMENT AID, NOT CERTIFICATION) is not a hedge we invented
— it is the posture the standard itself takes. Worth quoting in the module
docstring once the text is held. It also bounds what buying it can ever deliver:
**no global strength, no deflection, no panel-buckling.** If the project ever
needs those, ISO 12215-5 is not where they come from at any price.

### 4.7 ISO 12215-7:2020 (multihulls) — what the preview settles about the queue

Source, FIRST-PARTY (preview):
https://cdn.standards.iteh.ai/samples/73457/4c0a9c63d8cb4f94816cd70fb82cb2e4/ISO-12215-7-2020.pdf

**Scope, verbatim (abridged):**

> "This document defines the dimensions, local design pressures **and global
> loads** acting on multihull craft with a hull length (L_H) or load line length
> of up to 24 m. … **Scantlings corresponding to the local design pressures are
> then assessed using ISO 12215-5.** … applicable to multihulls built from the
> same materials as in ISO 12215-5 … It is not applicable to multihull racing
> craft designed only for professional racing."

**Clause 2, Normative references — verbatim:** `ISO 8666:2020` (note: the **2020**
edition, where 12215-5:2019 cites 8666:**2016**), `ISO 12215-5:2019`,
`ISO 12215-8:2009`, `ISO 12215-9:2012`, `ISO 12215-10:2020`, `ISO 12217-1:2015`,
`ISO 12217-2:2015`, `ISO 12217-3:2015`.

**Two things this settles:**

1. **12215-7 is strictly downstream of 12215-5 and of 8666.** It normatively
   requires both. Queueing it above either is queueing a document that cannot be
   executed. (It also pins `ISO 8666:2020` as the edition to buy, resolving the
   2016-vs-2020 tension §4.4 raises: the newer part of the family cites the
   newer 8666.)
2. **It is not "12215-5 for catamarans" — it adds GLOBAL loads, which 12215-5
   explicitly does not cover.** From its Contents, Clause 12 carries **six global
   load cases**: GLC 1–3 (transverse, past the preview cut), **GLC 4 longitudinal
   broaching/pitchpoling**, **GLC 5 longitudinal force on one hull**, **GLC 6
   bending of crossbeams connecting hulls for motor catamarans**. §4.6 records
   that 12215-5's Introduction disclaims global strength entirely. **So a
   catamaran SKU needs 12215-7 for a class of load the monohull standard does not
   contain at any price** — which is a stronger justification for the
   `PURCHASE_QUEUE` row than the one currently written, and it is an engineering
   justification, not a harmonisation one (§1.2).

Clause 3.4 also introduces **`mOC`, "mass in minimum operating condition"**,
deferring to ISO 8666 (clause 7.6 in the 8666 contents, §3.3) — a second loading
condition the project does not model, and another 8666 dependency.

---

## 5 · ISO 12217 — WHAT IS FREE, AND WHAT THE PARTS ARE

### 5.1 ISO 12217-1:2015 — the harmonised text, mapped

Source, FIRST-PARTY (preview):
https://cdn.standards.iteh.ai/samples/68140/22381f53c83f4b8b8443d35e31ac271e/ISO-12217-1-2015.pdf

Title page: *"Third edition, 2015-10-15"*, `ISO 12217-1:2015(E)` — **the same
string `review.py` records.** Harmonised as EN ISO 12217-1:2017 (§2.2).

**Contents, FIRST-PARTY (preview):**

    1 Scope 1 · 2 Normative references 2
    3 Terms and definitions 2  (3.1 Primary · 3.2 DOWNFLOODING 4
                                3.3 Dimensions, areas and angles 5
                                3.4 Condition, mass and volume 7 · 3.5 Other 9)
    4 Symbols 12
    5 Procedure 13   5.1 Maximum load · 5.2 Sailing or non-sailing
                     5.3 Tests and calculations to be applied 14
                     5.4 Variation in input parameters 15
    6 Tests, calculations and requirements 15
      6.1 DOWNFLOODING 15  (6.1.1 openings 15 · 6.1.2 HEIGHT 17 · 6.1.3 ANGLE 20)
      6.2 OFFSET-LOAD TEST 20 (6.2.1 objective · 6.2.2 test 21 · 6.2.3 reqts 21)
      6.3 Resistance to waves and wind 21
          (6.3.2 rolling in beam waves and wind 21 · 6.3.3 resistance to waves 22)
      6.4 Heel due to wind action 23 (6.4.2 calculation · 6.4.3 requirement 24)
      6.5 Recess size 24 (6.5.2 simplified 25 · 6.5.3 direct calculation 26
                          6.5.4 design category C boats using option 6 — 27)
      6.6 Habitable multihull boats 27 · 6.7 Motor sailers 27
      6.8 Flotation requirements 28 · 6.9 Detection and removal of water 28
    7 Application 29  (7.1 Deciding the design category · 7.2 MEANING of the
                       design categories 29)
    Annex A (normative) FULL METHOD FOR REQUIRED DOWNFLOODING HEIGHT      31
    Annex B (normative) Method for OFFSET-LOAD TEST                       33
    Annex C (normative) Methods for calculating DOWNFLOODING ANGLE        41
    Annex D (normative) Method for measuring FREEBOARD MARGIN             43
    Annex E (normative) Determining the CURVE OF RIGHTING MOMENTS         45
    Annex F (normative) Method for LEVEL FLOTATION TEST                   48
    Annex G (normative) Flotation material and elements                   53
    Annex H (normative) Information for owner's manual                    55
    Annex I (informative) Summary of requirements                         57
    Annex J (informative) Worksheets                                      58
    Annex K (informative) Illustration of recess retention level          75

**Annex A is the home of `hD(R)`** (`review.py`'s R-DFH) and **Annex B of the
offset-load test** (R-OLH). Both are **normative**. Annex E, *Determining the
curve of righting moments*, is the natural home of anything GM-adjacent —
EU-REGULATORY.md §7.2 records zero hits for a GM floor across 86 pages, so
**Annex E is what a re-read should target if the GM question is ever reopened.**

**Scope, verbatim (abridged):**

> "This part of ISO 12217 specifies methods for evaluating the stability and
> buoyancy of intact (i.e. undamaged) boats. The flotation characteristics of
> boats **susceptible to swamping** are also encompassed. …
> principally applicable to boats propelled by human or mechanical power of 6 m
> up to 24 m hull length. However, **it can also be applied to boats of under 6 m
> if they do not attain the desired design category specified in ISO 12217-3 and
> they are decked and have quick-draining recesses which comply with
> ISO 11812**."

That last sentence is the **only free statement of the 12217-1 ↔ 12217-3 ↔ 11812
interlock**, and it is what `R-SCP`'s ≥ 6 m refusal is a simplification of.
Note the dependency it creates: the sub-6 m escape hatch **requires ISO 11812
compliance** (1 420 SEK), which is why 11812 is not merely a cockpit standard.

**Two cautions printed on the standard's own first page, verbatim:**

> "**CAUTION — Compliance with this part of ISO 12217 does not guarantee total
> safety or total freedom of risk from capsize or sinking.**"
> "**IMPORTANT — The electronic file of this document contains colours which are
> considered to be useful for the correct understanding of the document.**"

The second one is a purchasing note: **buy the PDF, not the paper.**

**Foreword, changes from ISO 12217-1:2013** (verbatim, abridged) — the 2015 is a
*minor revision*: the RCD reference updated to 2013/53/EU; *"vulnerable"* replaced
by *"susceptible"*; ISO 6185-4:2011 added to Clause 2; entries 3.1.1, 3.4.3,
3.4.5, 3.4.6, 3.5.9 amended; **6.1.2.2 c) option 6 included**; *"6.3.2 and 6.4.1:
the formulae have been harmonised"*; **"6.5.2.3 and 6.5.2.4: formulae
coefficients have been corrected"**; 7.2 and Table 6 amended; F.4/Table F.5
amended and F.4.4 added; worksheets 1,2,3,6,7,8,9,10,12 corrected; Annex K added.

### 5.2 The three parts, and which SKU each governs

| part | harmonised as | scope | price |
|---|---|---|---|
| **12217-1** | EN ISO 12217-1:2017 (ISO …:2015) | **non-sailing** boats, L_H ≥ 6 m | 1 865 SEK |
| 12217-2 | EN ISO 12217-2:2017 (ISO …:2015) | **sailing** boats, L_H ≥ 6 m — includes the wind-heeling criteria | 1 865 SEK |
| **12217-3** | EN ISO 12217-3:2017 (ISO …:2015) | boats of **L_H < 6 m** | 1 865 SEK |

**The RCD Art. 20 argument for buying 12217 is in EU-REGULATORY.md §2.6/§3.5 and
is not restated here.** In one line: for a category C craft under 12 m,
compliance with the harmonised ER 3.2/3.3 standards is the **condition for Module
A**, the only conformity route with no notified body. That is a product
argument, not a documentation one, and it is the strongest justification in the
whole queue.

**ISO 12217-1:2022 exists and is not harmonised.** ISO catalogue entry
`iso.org/standard/79072.html`; the FDIS that became it is previewable at
`cdn.standards.iteh.ai/samples/79072/584c86f9bb4e410cbc2d04b8028cdf23/ISO-FDIS-12217-1.pdf`
(§6.4 — an FDIS draft is a legitimate free route). Buying 2022 instead of the
2015 text would buy a **newer** standard that confers **no** presumption of
conformity. `PURCHASE_QUEUE` row 1 names the 2022; **the row should name
EN ISO 12217-1:2017.**

---

## 6 · FREE ACCESS ROUTES — what works, what does not, and what is coming

Rated by whether it actually delivers content today.

### 6.1 WORKS TODAY — official ISO preview pages (this is how §3, §4 and §5 exist)

**iTeh Standards' sample PDFs**, `cdn.standards.iteh.ai/samples/<ISO-id>/<hash>/`.
iTeh is an authorised standards distributor and these are ISO's own official
preview extracts — the same pages ISO's "Preview" button serves — watermarked
`iTeh STANDARD PREVIEW` / `Document Preview`. **12–15 pages** each: cover,
copyright page, **full table of contents**, **foreword (including the complete
list of changes from the previous edition)**, introduction, **Clause 1 Scope**,
**Clause 2 Normative references**, **Clause 3 Terms and definitions**, and — for
12215-5 — **the whole of Clause 4, Table 1, the symbol list**.

Confirmed working, downloaded 2026-08-13:

| standard | preview URL | pages |
|---|---|---|
| ISO 12215-5:2019 | `https://cdn.standards.iteh.ai/samples/69552/019bbe6cf9164ddf8c3ab509bee75531/ISO-12215-5-2019.pdf` | 14 |
| ISO 8666:2020 | `https://cdn.standards.iteh.ai/samples/79071/5b10fa79b7f949158a2452264bdaed04/ISO-8666-2020.pdf` | 12 |
| ISO 12217-1:2015 | `https://cdn.standards.iteh.ai/samples/68140/22381f53c83f4b8b8443d35e31ac271e/ISO-12217-1-2015.pdf` | 15 |
| ISO 12215-7:2020 | `https://cdn.standards.iteh.ai/samples/73457/4c0a9c63d8cb4f94816cd70fb82cb2e4/ISO-12215-7-2020.pdf` | 15 |
| ISO 12215-6:2008 | `https://cdn.standards.iteh.ai/samples/42346/9716fcfc65e643ef88d2a8267ad08b48/ISO-12215-6-2008.pdf` | 15 |
| ISO/FDIS 12217-1 (→ 2022) | `https://cdn.standards.iteh.ai/samples/79072/584c86f9bb4e410cbc2d04b8028cdf23/ISO-FDIS-12217-1.pdf` | 15 |
| ISO 8666:2016 (superseded) | `https://cdn.standards.iteh.ai/samples/65424/2c21af72f3f64c6c8fa47a5ce1a77cd7/ISO-8666-2016.pdf` | — |

**How to find one:** web-search `cdn.standards.iteh.ai samples ISO-<n>-<year>.pdf`;
the ISO catalogue id (e.g. `69552` for 12215-5, `79071` for 8666, `68140` for
12217-1, `73457` for 12215-7, `67294` for 12215-10) is the first path segment.
`curl` with a browser UA works; `pypdf` extracts the text layer cleanly.

**The cut is always immediately before the first numbered requirement.** No
`k_DC` value, no pressure formula, no design stress, no tolerance figure appears
in any preview examined. **That boundary is the paywall, and it is drawn exactly
where the content becomes usable.**

### 6.2 WORKS TODAY — the harmonised standards LIST, free and legally operative

§1. The Commission's summary list (`.xlsx` and `.pdf`, regenerated periodically —
this one 17/3/2026) gives every dated reference, its OJ citation, its implementing
decision, its start of legal effect and — for withdrawn rows — its end of legal
effect and withdrawal decision. **This is the source EU-REGULATORY.md §3.1 flags
as UNVERIFIED** (*"whether the OJEU currently cites these editions"*): it is now
verified, from the Commission rather than from the RSG guide.

### 6.3 A ROUTE THAT EXISTS IN LAW — Regulation 1049/2001 after the Malamud judgment

**This is the highest-value item in this section and it is the only route that
could deliver the full text of ISO 12215-5 legitimately at zero cost.**

**Case C-588/21 P, `Public.Resource.Org Inc. and Right to Know CLG v Commission`,
judgment of the Court of Justice (Grand Chamber), 5 March 2024.**
Curia press release: https://curia.europa.eu/site/upload/docs/application/pdf/2024-03/cp240041en.pdf ·
EUR-Lex: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:62021CJ0588

The Court held that **harmonised standards form part of EU law**, and that there
is an **overriding public interest** under Regulation 1049/2001 in their
disclosure free of charge, because citizens and businesses must be able to know
the norms that bind them. It annulled the Commission's refusal and required
access to the four requested standards. **CEN-CENELEC's own statement** stresses
that copyright is not thereby extinguished and that access under 1049/2001 is
*"without prejudice to any existing copyright rules which may limit the right of
third parties to reproduce or use released documents"*
(https://www.cencenelec.eu/news-events/news/2024/brief-news/2024-03-05-ecj-case/).

**How it works in practice, as far as this review could establish:**

- Access is by **active request** — a Regulation 1049/2001 application to the
  European Commission naming the standard. There is no bulk publication.
- The Commission has a page and an access mechanism at
  **`https://ec.europa.eu/growth/tools-databases/enorm/access_to_harmonised_standards`**
  ("eNorm"), reported to require an **EU Login** account. **COULD NOT VERIFY:**
  the page returned no readable content to this session's fetcher — only the
  title "eNorm Platform". A human with an EU Login should open it directly.
- Released documents are reported to arrive **watermarked** — *"Copyright CEN.
  USE ONLY FOR INTERNAL AND INFORMATION PURPOSES"* / *"DO NOT COPY"*, and for
  ISO-origin texts *"Copyright ISO – licensed to CEN for limited distribution and
  restricted use to European Commission"*. **SECONDARY SOURCE** (commentary, not
  read on a released document).
- **European Ombudsman decision, case 437/2025/MIK**
  (https://www.ombudsman.europa.eu/en/decision/en/220602) records that the
  Commission *"provides public access to some standards upon request"*, that
  further access runs through CEN/CENELEC/ETSI portals, and that the Ombudsman
  recommended the Commission grant at least partial access to its own internal
  implementation assessment. **It does not name which standards have been
  released.** So: the route is real, its scope is undefined, and only a request
  will settle whether EN ISO 12215-5:2019 is in it.

**Recommended action, and it is cheap: file a Regulation 1049/2001 request for
`EN ISO 12215-5:2019` and `EN ISO 12217-1:2017` before spending 1 988 + 1 865
SEK.** It costs an email and some weeks. The worst case is a refusal, which is
itself a citable finding. **Two limits to state honestly when doing it:** a
watermarked read-only copy is a *reading* licence, not a redistribution licence —
it would let a reviewer confirm coefficients and close Gate 6R honestly, but it
would **not** license reproducing tables into `limits.py` as published values;
and a refusal or a delay is the likely outcome for a standard not among the four
litigated.

### 6.4 WORKS TODAY — public draft stages (ISO/DIS, ISO/FDIS, prEN)

A draft under public enquiry is legitimately circulated, and iTeh mirrors them.
Confirmed reachable:

- `ISO/FDIS 12217-1` (the draft of the 2022 edition) —
  `https://cdn.standards.iteh.ai/samples/79072/584c86f9bb4e410cbc2d04b8028cdf23/ISO-FDIS-12217-1.pdf`
- `ISO/FDIS 12217-2` —
  `https://cdn.standards.iteh.ai/samples/79073/7038902776064795967d72e67f47d127/ISO-FDIS-12217-2.pdf`
- `ISO/FDIS 12215-9` —
  `https://cdn.standards.iteh.ai/samples/iso/iso-fdis-12215-9/5dbe17de2a6647aa9dd558a7f8ad3a80/iso-fdis-12215-9.pdf`
- `oSIST prEN ISO 15085:2023` (the draft of the 2024 edition) —
  `https://cdn.standards.iteh.ai/samples/70353/fcb1d3ed57064f3aa38a8019a658f9e7/oSIST-prEN-ISO-15085-2023.pdf`
- `oSIST prEN ISO 8666:2020` —
  `https://cdn.standards.iteh.ai/samples/70149/e5d375e7f9634f6bbbf79dc9d9516cda/oSIST-prEN-ISO-8666-2020.pdf`

**Caveat that must travel with every one of these: these are the same truncated
previews, of a DRAFT.** A draft is not the standard, and a value read in a draft
must be marked as such and never given a `basis` implying the published text.

**AND THE ONE EXCEPTION, WHICH IS THE BIGGEST SINGLE FIND IN THIS REVIEW:**

> **`ISO/DIS 12215-5.3` (2004-12-18) is published IN FULL — all 95 pages, not a
> preview — free, by the National Marine Manufacturers Association:**
> https://www.nmma.org/lib/docs/nmma/cert/techupdates/dis_12215-5.3-e-_2004-12-18_for_validation.pdf

An industry association hosting a Draft International Standard that was
circulated for validation. It is legitimately public — the document's own warning
page says it *"is distributed for review and comment"* — and it contains the
complete pressure, plating, stiffener and wood-property clauses. **§7 is built on
it, and §7.0 is the list of reasons every number in it is out of date.**
**NOT FOUND: any public DIS or FDIS of the 2019 revision** — only this draft of
the first edition is public.

### 6.5 EXISTS BUT DOES NOT COVER US — national free read-only portals

- **NEN Connect (Netherlands)** publishes a genuinely free, registered,
  **read-only** collection of *national adoptations of harmonised European
  standards*:
  https://connect.nen.nl/portal/Registreren/Vrij-Beschikbare-Normen/Geharmoniseerde-Europese-normen/en
  Terms, verbatim: *"The present access to the standards is granted for direct
  information of the registered user only and under read-only format, without any
  right to especially download, print, commercialize, reproduce, make available
  or distribute the documents."* Free registration.
  **MEASURED: Directive 2013/53/EU is not covered, and neither EN ISO 12215 nor
  EN ISO 12217 appears.** The listed sectors are fire safety (EN 54), toys
  (EN 71), lifts (EN 81), construction products, machinery, water, rail.
  **The mechanism is exactly right and the content is not there.** Worth
  re-checking after the CEN readability platform lands (§6.6).
- **NEN Connect free national collection** — ~161 documents, *"predominantly
  available only in the Dutch language"*, NEN-numbered, environmental/soil/water/
  healthcare. **Nothing for us.**
- **SIS (Sweden)** — product pages advertise *"Preview this standard"*.
  **UNVERIFIED: what SIS's preview contains** (not opened; likely the same ISO
  preview as §6.1). SIS is however the best *price* source (§1.3).
- **SFS (Finland)** — **no free online reading room.** A physical library, open
  Mon–Fri 09:00–15:00, visits arranged in advance via `store@sfs.fi`; material
  cannot be borrowed. https://sfs.fi/en/information-and-assistance-on-standards/
- **DIN / BSI / Standards Norway / Standards Australia** — **NOT INVESTIGATED IN
  DEPTH.** Recorded as not done rather than as absent.

### 6.6 COMING, NOT HERE — the CEN-CENELEC "readability platform"

Following C-588/21 P, the Commission funded (through EISMEA, 2024) a call for
CEN and CENELEC to build a **centralised, free-to-read portal** for harmonised
standards — online reading without download or reproduction. As of the most
recent public information, **it has not launched**; developer procurement was
under way in mid-2025 and CEN-CENELEC issued a translation-services tender in
October 2025 (https://www.cencenelec.eu/news-events/news/2025/call-for-tender/2025-10-06_readibilityplatforms/).
**This is the route that would eventually make EN ISO 12215-5 free to read
legitimately. It does not exist yet. Do not plan around it.**

### 6.7 WORKS TODAY — ISO/TC 188's own public committee site

**`https://committee.iso.org/home/tc188` is reachable** even though `iso.org`
is not — it is a different host and is not behind the same bot check. Its
`About`, `News`, `Projects` and `Contact` pages are public. (`Projects → Ongoing`
and the "Related links" ISO portals are members-only.)

**Committee scope, verbatim:**

> "Standardization of equipment and construction details of recreational craft,
> and other small craft using similar equipment, **up to 24 metres length of the
> hull**. Excluded are lifeboats and lifesaving equipment covered by ISO/TC 8,
> Ships and marine technology."

and, on the RCD relationship: TC 188 *"Co-operates with CEN in response to the
European Union's Recreational Craft Directive"*. The Projects page adds that
*"ISO/TC 188 has published 79 standards (under the direct responsibility) since
the committee's creation in 1984"* — while the About page's counter reads
**83 published, 12 under development**. (Two counts on one site; neither is
load-bearing here, and both are noted rather than reconciled.)

**Three things the News page hands over free, and they are current:**

1. **The 2026 plenary (Gothenburg, ~40 members from 13 countries) decided to
   start revisions on `ISO 8469` (non-fire-resistant fuel hoses), `ISO 7840`
   (fire-resistant fuel hoses), `ISO 25197` (electrical/electronic control
   systems for steering, shift and throttle) and **`ISO 11812`**.** §2.5.
2. **The March 2026 RCD harmonisations**: `EN ISO 8665-2:2024` (electric marine
   propulsion) and `EN ISO 15085:2024` — corroborating decision 2026/550 in the
   Commission list independently.
3. **The 18-month transitional rule**, quoted in §2.4. This is the clearest free
   statement of it found anywhere in this review.

**This is the "TC 188 public documents" route, and it works.** It will not give
a formula, but it is the cheapest way to learn that a standard is under revision
before buying it. Worth re-reading before any purchase decision.

The page carries ISO's own disclaimer that the site *"is managed and maintained
by a third-party entity … not under the direct responsibility, control, or
oversight of"* ISO — so it is authoritative about committee business and is not
a source for the text of a standard.

### 6.8 NEGATIVE RESULTS — routes checked and found not to apply

- **`iso.org` and `webstore.ansi.org` are unreachable from this machine.** Both
  return HTTP 403 to WebFetch, to `curl` with a browser UA, and (for iso.org) to
  a public reader proxy that reported *"Performing security verification"*.
  ANSI *does* host free preview PDFs at
  `webstore.ansi.org/preview-pages/ISO/preview_ISO+<n>-<year>.pdf` — the URL
  pattern is real and appears in search results — but every fetch was blocked.
  **A session on a different network should retry these; they are a second
  independent preview source.**
- **ANSI IBR portal / US incorporation by reference — DOES NOT APPLY.** The
  US small-craft regime is **33 CFR 183**, which states its own requirements in
  the regulation text and does not incorporate ISO 12215 or ISO 12217. There is
  no US federal incorporation of the ISO small-craft family for this route to
  unlock. **NOT FOUND: any ISO small-craft standard incorporated by reference
  into US federal law.**
- **`law.resource.org/pub/eu/`** (Public.Resource.Org — the litigant that won
  C-588/21 P) publishes EU harmonised standards by directive and **does list a
  "Recreational Craft" category**, linking `recreational.html`. **MEASURED
  2026-08-13: that link returns HTTP 404**, serving Public.Resource's own
  standard notice — *"You Have Insufficient Privilege To Read This Law At This
  Time … Status Code 451: Your Request Has Been Denied … temporarily denied
  permission to access this document at this time due to the mislocation or
  other obfuscation of the item in question"*, signed Carl Malamud, dated
  November 7, 2015. **So the category exists and the content is withheld.**
  Twelve other directives on the same index (toys, machinery, PPE, construction
  products, Eurocodes, medical devices …) are listed alongside it; whether they
  serve is untested. This is a legitimate publisher, not a piracy site, and it
  is the organisation most likely to publish these the moment it can — **worth
  re-checking periodically, and worth checking whether the RCD collection is
  reachable under a different path.**
- **ISO/TC 188 public committee documents** — **NOT FOUND.** The committee's
  public area is behind `iso.org` (403 here). `committee.iso.org` appeared in a
  search result but was not reachable. **Recorded as not done.**
- **ISO Online Browsing Platform (OBP), `iso.org/obp/ui`** — ISO's own free
  service for **terms and definitions and scopes**. Both 12215-5 and 8666 point
  readers at it in their Clause 3. **Unreachable from this machine (403).** On a
  network where iso.org resolves, **OBP is a first-party free route to Clause 3
  of every standard in §1** and should be the first thing tried.
- **Pirated full texts.** Complete uploads of ISO 12215-5:2019 (including one
  explicitly labelled as the *corrected version 2023-11*) and ISO 12215-7:2020
  are indexed on document-sharing sites and surface on the first page of an
  ordinary search. **Not opened, not quoted, not cited, and not to be used.**
  Recorded so the decision is documented rather than re-litigated.

---

## 7 · THE ISO 12215-5 CALCULATION, RECOVERED FROM A FREE DRAFT

### 7.0 ⚠ READ THIS BEFORE USING ANY NUMBER IN THIS SECTION

**The source is `ISO/DIS 12215-5.3`, dated 2004-12-18, published in full and free
by the National Marine Manufacturers Association:**

> https://www.nmma.org/lib/docs/nmma/cert/techupdates/dis_12215-5.3-e-_2004-12-18_for_validation.pdf
> — 95 pages, `ISO TC 188/WG 18`, Secretariat SIS, marked *"Validation version"*.

Its own warning page, verbatim:

> "**This document is not an ISO International Standard. It is distributed for
> review and comment. It is subject to change without notice and may not be
> referred to as an International Standard.**"

**So this is a new provenance grade, and it is NOT "FIRST-PARTY".** Call it
**DRAFT (superseded lineage)**. Three separate gaps separate it from the text
that governs:

    ISO/DIS 12215-5.3  (2004-12-18)   <- what we read
        v  unknown changes at publication
    ISO 12215-5:2008 + Amd 1:2014      <- first published edition
        v  the 2019 revision, whose changes ARE listed (§4.1)
    ISO 12215-5:2019                   <- harmonised (EN ISO 12215-5:2019)
        v  Corrected version 2023-11: "errors in formulae, text and values in
           Clause 7, Clause 9, ... and Tables 12, 17 ... corrected"
    ISO 12215-5:2019 corrected 2023-11 <- current

**Every one of the 2019 Foreword's listed changes hits something in this
section.** Stated as a kill-list, so nobody has to work it out:

| the 2019 Foreword says | therefore this draft's … | status |
|---|---|---|
| *"renaming of n_CG into k_DYN in Table 7"* | `n_cg` and its equation (4), Table 2 caps | **renamed at minimum; formula unconfirmed** |
| *"lowering of the values of k_L in the aft part of the craft in Table 8"* | `k_L` equation (5), Figure 3 | **VALUES CHANGED — do not use** |
| *"deletion of k_AR min"* | the `k_ar ≥ 0,25 / ≥ 0,4` floors | **DELETED — do not use** |
| *"improvement of the values of k_SUP in Table 10"* | Table 4 `K_sup m` | **VALUES CHANGED** |
| *"modification of design pressures for motor and sailing craft in Tables 12 & 13"* | **every pressure equation, (1)–(17)** | **CHANGED** |
| *"modification of design stresses introducing k_BB and k_AM factors in Tables 15 to 17"* | **every design-stress table, 8–12** | **CHANGED, and two new factors added** |
| *"new Annex I only recommending minimum thickness … no longer mandatory"* | minimum-thickness requirements | **status changed** |
| corrected version 2023-11 corrects *Clause 9 and Table 12* | the pressure clauses again | **corrected after 2019** |

**Conclusion, stated plainly: NO NUMBER IN §7 MAY BE ENCODED AS A CURRENT
ISO 12215-5 VALUE.** Not `kDC = 0,75` for category C, not `σd = 0,5·σuf`, not a
plywood strength from Table E.3. `refdata.BASES` has no grade for this and
should not get one: it is not `standard-2003` (wrong text), it is not
`purchased`, and calling it `approx` without the caveat above would lose exactly
the information that matters.

**What §7 IS good for, and it is a lot:**

1. **Checking the SHAPE of `navalai/rules/iso12215.py`.** §7.2 (pressure) and
   §7.4 (thickness) do this. The headline: the module's **thickness** equation is
   the draft's plywood equation term for term, and its **pressure** equation is
   not the draft's pressure equation in any respect — not the base, not the
   floor, not the modulating factors.
2. **Knowing what to look up** in a purchased copy, and roughly what to expect —
   so a transcription error is detectable rather than invisible.
3. **Order-of-magnitude sanity.** §7.5 shows `SIGMA_D_OKOUME = 15.0` lands on a
   real plywood value, which is worth knowing before spending money.
4. **Finding whole checks that are MISSING**, which no coefficient purchase
   fixes: no stiffener section modulus, no stiffener shear area, no bottom/side
   distinction, no longitudinal distribution, no area reduction, no limits-of-
   application refusal.

### 7.1 ⚙ HOW THESE EQUATIONS WERE READ — a method that supersedes a repo-wide limitation

**This matters beyond §7 and should be lifted into `docs/LESSONS.md`.**

The draft's equations are typeset with an equation editor and `pypdf`'s text
extraction returns their tokens **out of order**. Equation (2) comes out as

    Pbm min= )17(10 w h c fLT ⋅+

— right symbols, wrong sequence, decimal points lost. Encoding anything from that
would be guessing. And `docs/research/EU-REGULATORY.md` §0 records the standing
constraint that made this look unfixable:

> "`pdftoppm`/poppler is not installed on this machine, so the Read tool cannot
> open a PDF here at all."

**CONFIRMED still true — and it no longer blocks anything.** Verified 2026-08-13:
no `pdftoppm`, no `mutool`, no `gs`, no `qpdf`, and no `fitz`/`pymupdf`/
`pdf2image`/`pypdfium2` in `~/.venvs/naval`. **But macOS ships a PDF renderer
already, and it needs no install:**

```bash
# 1. split the page(s) you want into single-page PDFs
python - <<'PY'
from pypdf import PdfReader, PdfWriter
r = PdfReader('doc.pdf')
for i in (13, 14, 15):                      # 0-indexed
    w = PdfWriter(); w.add_page(r.pages[i])
    with open(f'pg/p{i+1}.pdf', 'wb') as f: w.write(f)
PY
# 2. render each with QuickLook  (-t thumbnail, -s max edge in px, -o outdir)
qlmanage -t -s 2400 -o pg pg/p14.pdf        # -> pg/p14.pdf.png
# 3. Read the PNG with the Read tool
```

`qlmanage -t` renders **only the first page**, which is why step 1 is needed —
that one-page split is the whole trick. At `-s 2400` the output is legible enough
to transcribe subscripts, radicals, fraction bars and decimal commas. **Every
equation in §7.3 and §7.4 marked TRANSCRIBED was read this way**, and the
readings were cross-checked against the scrambled text layer for consistency.

**What this unblocks elsewhere, immediately and at zero cost** — every raster
item EU-REGULATORY.md §10 lists as unread: the ~60 unopened Annex ZA tables in
the RCD application guide, ES-TRIN Chapter 4 Figures 1–3 (the sheer-abscissa
convention behind the `r > 1` clamp), the ES-TRIN Art. 10.03 IP table, EMSA
Figure 1.1 and Annex C, and the SAFEMASS Tables 1 and 2. **The "install poppler"
item on that list can be closed without installing poppler.**

Two limits, stated: `qlmanage` is macOS-only (fortress001 still needs poppler),
and it is a *thumbnail* renderer — very dense tables may need cropping or a
higher `-s` before they read cleanly.

Confidence classes used below, marked at every item:

- **TRANSCRIBED** — read from running text, a table, or a rendered image of the
  equation. Reliable.
- **RECONSTRUCTED** — inferred from a scrambled token sequence only, because the
  page was not rendered. **Never encode a RECONSTRUCTED formula.** Every one of
  these can be promoted by rendering the named page with the recipe above; the
  pages are identified so the work is one command each.

### 7.2 Structure of the calculation — TRANSCRIBED

From Clause 5, verbatim:

> "The scantling determination shall be accomplished as follows:
> — for craft with a length L_H of **2,5 m up to 24 m**, according to sections 6
> to 10 of this part of ISO 12215;
> — for craft with a length L_H **2,5 m up to 12 m of design categories C and
> D**, Annex A.1 may be used as an alternative…;
> — for **sailing craft** with a length L_H 2,5 m up to 9 m of design categories
> C and D, Annex A.2…;
> — for craft with a length L_H **2,5 m up to 6 m and of single skin FRP bottom
> construction**, the **drop test in Annex B** may be used as an alternative…"

and the caveat the project's own disclaimer should echo:

> "NOTE 1 These scantling requirements are based on normal anticipated sea loads
> during normal usage. Compliance with these requirements does not eliminate the
> possibility of damage from accidental overloads, careless handling, trailing
> loads, chocking loads, grounding or berthing. … **For craft smaller than 6 m in
> particular, robustness criteria may be the governing aspect for scantling
> determination**, e.g. beaching, grounding, trailer and fender loads."

**Motor craft bottom pressure — TRANSCRIBED from the rendered page (PDF p. 14),
clause 6.1.2, equations (1) to (4) verbatim.** *"The bottom design pressure for
motor craft `P_bm` is the greater of:"*

    (1)   P_bm      = P_bm_base · k_ar · k_L                          [kN/m2]

    (2)   P_bm_min  = 10 · ( T_c  +  (L_h / 17) · f_w )               [kN/m2]

    (3)   P_bm_base = [ 0,1 · m_LDC / (L_WL · B_C) ] · ( 1 + f_w · n_cg )
                                                                      [kN/m2]

    (4)   n_cg      = 0,32 · ( L_WL / (10 · B_C) + 0,084 )
                           · ( 50 - beta )
                           · ( V^2 · B_C^2 / m_LDC )                  [g's]

with `T_c` the canoe-body draught, `L_h` the hull length, `f_w` the design
category factor (Table 3), `B_C` the chine beam at 0,4·L_WL forward of the aft
end of the loaded waterline, `β` the deadrise there (bounded 10°–30°), `V` in
knots and `m_LDC` in kg. `n_cg` is capped by Table 2.

**Look at equation (3): the base bottom pressure is an AREAL LOADING**
(`m_LDC / (L_WL·B_C)`, mass over a plan area) **multiplied by a dynamic
amplification** `(1 + f_w·n_cg)`. **The project's `2.4·mLDC^0.33 + 20` is not
that.** It is a monotone function of displacement alone — no beam, no waterline
length, no category, no acceleration. Two boats of the same mass, one 6 m × 2 m
and one 12 m × 2 m, get the same bottom pressure from the module and a **2:1
different** one from equation (3).

**And equation (2): the FLOOR is `10·(T_c + f_w·L_h/17)`, not a constant.** It
is a hydrostatic head term plus a category-scaled length term. The module's
floor is the bare number `10.0`, which — read against (2) — is the value for a
zero-draught, zero-length boat.

**Figure 1's bottom/side boundary is speed-dependent, TRANSCRIBED:** for a hard-
chine motor craft the split is drawn differently for `V/√L_WL ≤ 3,6` and
`V/√L_WL > 3,6`, and a round-bilge hull is a third case, with the boundary at the
"girth of bottom area". So *which panels are "bottom" at all* depends on speed
and section shape. The project has no bottom/side distinction.

**The structural fact behind all of it: the design pressure is a MAXIMUM OF TWO,
and the first is a base pressure MODULATED by two reduction factors:**

    P_bm = max( P_bm_base · k_ar · k_L ,  P_bm_min )

The
project's `design_pressure_bottom` is `max(10.0, 2.4·mLDC^0.33 + 20.0)` — a
maximum of two, with the *floor* a bare constant and the *base* unmodulated. The
draft's floor is a function of `T_c`, `L_H` and the design-category factor, and
its base is multiplied by **two** reduction factors, neither of which the module
has. (And per §4.2 the 2019 edition splits the floor again, into
`P_BM MIN PLT` and `P_BM MIN STF`.)

**Limits of application for motor craft — TRANSCRIBED, Clause 6.1.1:**

| parameter | minimum | maximum |
|---|---|---|
| `L_WL / ∇^(1/3)` | `3,6 + 0,06·L_WL` | `6,2 + 0,04·L_WL` |
| maximum speed | — | **50 knots** |

**Limits of application for sailing craft — TRANSCRIBED, Clause 6.2.1:**

> "— Category A and B boats for which `L_WL/∇^(1/3)` is less than `5,1 + 0,08·L_H`
> — Category C and D boats for which `L_WL/∇^(1/3)` is less than **7**
> Bottom pressure applies from the bottom of canoe body up to **150 mm above the
> waterline** in the fully loaded condition"

**These are refusal conditions, and the project has none.** A slender
solar-electric hull can easily exceed a length/displacement ratio ceiling, and
the correct behaviour there is to refuse a verdict, not to extrapolate.

### 7.3 The factors — TRANSCRIBED from tables, SUPERSEDED as values

**Design category factor, `f_w` (renamed `k_DC` in later editions) — Table 3:**

| Design Category | A | B | C | D |
|---|---|---|---|---|
| `f_w` | **1** | **0,9** | **0,75** | **0,5** |

**DRAFT 2004 VALUES.** The 2019 Foreword does not list a change to `k_DC`, which
is weak evidence they survived — but "not listed" is not "unchanged", and the
table moved from Table 3 to **Table 6** (§4.2), so at minimum the reference moved.
**The project applies NO design-category factor to bottom pressure at all**
(§4.3 finding 2), so whatever the values are, the shape is wrong.

**Dynamic load factor `n_cg` upper limits — Table 2, TRANSCRIBED verbatim:**

| normal mode of operation at maximum speed | example | `n_cg` |
|---|---|---|
| "Craft is primarily intended to be supported by a combination of buoyancy and planing forces" | cruising boats (semi-planing, planing) | **3,0** |
| "Craft may be entirely clear of the water for short periods of time in normal operation (i.e. become airborne)" | recreational RIBs and sports-boats | **4,5** |
| "Craft may be entirely clear of the water for long periods of time and craft is not intended to change course and speed to reduce sea loads" | rescue craft, offshore racing boats | **6,0** |
| "In addition to the above case, the craft is fitted with crew securing devices or requires special operating procedures" | bucket seats, belts, standing operation | **7,0** |

with the requirement that *"If the values of Table 2 are used to limit the
dynamic load factor … the information given in the first column of Table 2 shall
be written in the owner's manual"* — i.e. **the cap chosen becomes a
documentation obligation**, which is an arrangement/export-surface fact, not just
a number. **Renamed `k_DYN` in 2019 (Table 7), which now has three forms
(`k_DYN`, `k_DYN1`, `k_DYN2`) — so this table has certainly been restructured.**

**Bounds that are stated in running text and are therefore reliably TRANSCRIBED:**

- **`β`, deadrise at 0,4·L_WL forward of the aft end of the loaded waterline,
  "not to be taken smaller than 10°, nor more than 30°"** — the 2019 symbol table
  states the same bound as `10 < β_0,4 ≤ 30` (§4.2), so **this one is confirmed
  across both editions** and is the single most trustworthy number in §7.
- **`V` "shall not be taken smaller than `2,36·√L_WL`" (knots, m).** A speed
  FLOOR — a very slow craft is still designed for a minimum dynamic load. **The
  project has no such floor.** Note it interacts with the displacement/planing
  split at `5·√L_WL` (§4.4): the draft's design speed range for a motor craft is
  bounded below at 2,36·√L_WL, not at zero.
- **`k_ar` floors: "shall not be taken smaller than `k_ar = 0,25` when used in
  flexural strength and flexural stiffness calculations; `k_ar = 0,4` when used
  in panel shear strength calculations (cored panels)".** **DELETED in 2019** —
  the Foreword says so explicitly. Recorded because it shows `k_ar` is *not* a
  single scalar even in the draft: it is used differently in bending and in shear.
- **The design area `A_d`, TRANSCRIBED:** for plating `A_d = l·b·10⁻⁶` m² *"but
  shall not be taken greater than `2,5·b²·10⁻⁶`"*; for stiffeners `A_d = l_u·s`
  *"but need not be taken smaller than `0,33·l_u²`"*.
- **Longitudinal pressure distribution `k_L` — TRANSCRIBED from the rendered page
  (PDF p. 16), equation (5) verbatim:**

      k_L = 0,13 · [ ( 0,35 · V / sqrt(L_WL) ) + 4,14 ]     for  x/L_WL <= 0,25
      k_L = 1                                               for  x/L_WL >= 0,6

  with `x` *"the longitudinal position of mid panel forward of aft end of L_WL in
  m_LDC conditions"* (m), *"Intermediate values shall be obtained by
  interpolation"*, and *"The overhangs fore and aft shall have the same
  correction factor as the respective end of the fully loaded waterline."*

  Note what equation (5) does: at the aft end `k_L` depends **only on the speed/
  length ratio**, and at `V/√L_WL = 2,36` (the speed floor) it evaluates to
  `0,13·(0,35·2,36 + 4,14) ≈ 0,646`, rising to `1,0` at `V/√L_WL ≈ 6,6`. So for a
  slow displacement craft the aft bottom sees roughly **65%** of the forward
  pressure, linearly interpolated between `x/L_WL` 0,25 and 0,6.
  **⚠ The 2019 Foreword says the k_L values in the aft part were LOWERED, so the
  0,646 is not current — but the project applies NO longitudinal variation at
  all, computing one bottom pressure for the whole hull, which is the forward
  value everywhere.** That is conservative aft and correct nowhere.
- **Deck pressure reduction factor `K_d`, TRANSCRIBED:**
  `K_d = max(1,1 − 0,4·b/1000 ; 0,6)` for a deck or superstructure **panel**, and
  `K_d = max(1,1 − 0,4·l_u ; 0,33)` for a deck or superstructure **stiffener**,
  *"not to be taken greater than 1"*.
- **Superstructure factor `K_sup m` — Table 4, TRANSCRIBED**, as a proportion of
  deck design pressure: **front 1 · sides 0,67 · aft 0,5 · top first or single
  tier 0,5 · upper tiers 0,35 (walking areas)**; upper tiers in non-walking areas
  get the minimum deck pressure. *"Elements not exposed to weather shall be
  considered as upper tiers."* **`k_SUP` values were "improved" in 2019.**
- **Scantling height for motor craft side pressure: `h_sc = L_H/17` (m)** —
  eq. (12), TRANSCRIBED. The side-pressure region's upper limit is a horizontal
  line at `h_sc` above the loaded waterline abaft mid-L_WL, rising to `1,2·h_sc`
  at the stem.
- **Windows, hatches and doors are handed off:** *"Windows, hatches and doors
  shall comply with ISO 12216"* (6.1.6) — which is why 12216 sits in the family
  at all.

**STILL RECONSTRUCTED — not to be used, and each is one `qlmanage` command away
from being TRANSCRIBED (§7.1). The NMMA PDF page to render is named in each
case:** the `k_ar` equation (6) with `u = 100·A_d/A_r`, and the reference area
eq. (7) `A_r ≈ (0,36 − …)·L_H·B_C` — **PDF p. 17–18**; the motor-craft side
pressure equations (8)–(11), including the vertical distribution
`k_v = (z − h)/z` — **PDF p. 18–19**; the deck pressure eq. (13),
`≈ f_w · K_d · (0,43·L_H + 1,6)`, with a floor of **5 kN/m²** at eq. (14), and
the superstructure eq. (17) — **PDF p. 19–20**; and the stiffener section-modulus
and shear-area equations (47)/(48) — **PDF p. 38**. (The 5 kN/m² deck minimum and
the `(0,43·L_H + 1,6)` shape are legible in the text layer; their exact assembly
is not.)

### 7.4 Plating and stiffeners — the part that maps directly onto our code

**Panel aspect-ratio coefficients — Table 6, TRANSCRIBED in full.** `k_2` is for
bending strength, `k_3` for bending stiffness, both functions of `l/b`:

| `l/b` | `k_2` | `k_3` |
|---|---|---|
| > 2,0 | 0,500 | 0,028 |
| 2,0 | 0,497 | 0,028 |
| 1,9 | 0,493 | 0,027 |
| 1,8 | 0,487 | 0,027 |
| 1,7 | 0,479 | 0,026 |
| 1,6 | 0,468 | 0,025 |
| 1,5 | 0,454 | 0,024 |
| 1,4 | 0,436 | 0,023 |
| 1,3 | 0,412 | 0,021 |
| 1,2 | 0,383 | 0,019 |
| 1,1 | 0,349 | 0,016 |
| 1,0 | **0,308** | 0,014 |

and the table's own header carries the closed forms and one flat rule:

> `k_2` = [0,271·(l/b)² + 0,910·(l/b) − 0,554] / [(l/b)² − 0,313·(l/b) + 1,351]
> **"k_2 to be taken = 0,5 for laminated wood plating"**
> `k_3` = [0,027·(l/b)² − 0,029·(l/b) + 0,011] / [(l/b)² − 1,463·(l/b) + 1,108]

**The `0,308…0,5` range in `rules/iso12215.py`'s docstring is exactly this
table's `k_2` column.** So the module's provenance for that range is the
ISO 12215-5 lineage, and it is correctly described — but the module then takes
`k2` as a free parameter defaulting to 0,5, when for **laminated wood the draft
FIXES it at 0,5 regardless of aspect ratio**. For plywood the default is not a
default; it is the value.

**Curvature correction — Table 7, TRANSCRIBED:**

| `c/b` | `f_k` |
|---|---|
| 0 to 0,03 | 1,0 |
| 0,03 to 0,12 | **1,1 − 3,33·c/b** |
| > 0,12 | **0,7** |

where `c` is the crown of a curved panel. **And the note that matters most for
this project, verbatim from 8.3:**

> "NOTE **The curvature coefficient f_k is not relevant for wood** because the
> mechanical properties are very low in a direction perpendicular to the grain."

**`required_thickness_mm(..., k_curve=1.0)` therefore carries a parameter the
wood clause says does not apply.** At its default of 1,0 it is harmless; the
defect is that it is *offered*, and `select_stock_thickness_m` passes it through.
A caller who curves a plywood panel and passes `k_curve=0.7` would take a **30%
thickness reduction the standard does not grant for wood.**

**The plating equations — TRANSCRIBED from the rendered pages (PDF pp. 30 and 34),
Clause 8, verbatim.**

    8.1 FRP SINGLE SKIN
        "The minimum required thickness of the plating t is the greater of
         t_1 and t_2 defined below"

        (36)  t_1 = b · f_k · sqrt( P · k_2 / (1000 · sigma_d) )       [mm]
                    bending STRENGTH

        (37)  t_2 = b · f_k · cbrt( P · k_3 / (1000 · k_1 · E_f) )     [mm]
                    bending STIFFNESS;  k_1 = 0,047;  E_f = flexural modulus

    8.2 METAL (aluminium alloy and steel)
        (38)  t   = b · f_k · sqrt( P · k_2 / (1000 · sigma_d) )       [mm]

    8.3 LAMINATED WOOD  (plywood, moulded veneer, strip plank — Annex E)
        (39)  t_1 = b · sqrt( P · k_2 / (1000 · sigma_d) )             [mm]
              with  k_2 = 0,5   and  NO  f_k

`b` = short dimension of the panel (7.1.1, mm), `P` = the design pressure from
Clause 6 (kN/m²), `σ_d` = design stress from Table 10 (N/mm²).

**Equation (39) is, term for term, `rules/iso12215.required_thickness_mm`.**
That is a real result and worth stating plainly: **the project's thickness
formula has the right shape and the right lineage** — the `1000` is not a fudge,
it is the kN/m² → N/mm² reconciliation that makes the units close.

**Two differences, both real, both in the module's favour to fix:**

- **The draft has NO `f_k` for wood.** Verbatim, immediately under equation (39):
  *"NOTE The curvature coefficient f_k is not relevant for wood because the
  mechanical properties are very low in a direction perpendicular to the grain."*
  `required_thickness_mm(..., k_curve=1.0)` offers the parameter anyway.
- **It FIXES `k_2 = 0,5` for wood**, stated in the `where` list of equation (39)
  as a bare assignment — not looked up in Table 6. The module takes `k2` as a
  caller-supplied float.

**Note also what equation (39) is called: `t_1`.** In 8.1 that subscript
distinguishes the strength thickness from the stiffness thickness `t_2`, and the
answer is the larger of the two. **The wood clause defines a `t_1` and no `t_2`**
— so on the draft's own numbering there is no wood stiffness check, and
`max(t_1, t_2)` collapses to `t_1`. Worth knowing before someone "completes" the
wood path by inventing a stiffness criterion for it.

**Note the FRP path needs a SECOND thickness for stiffness (`t_2`, a cube root
in `E_f`) and the answer is the larger of the two.** Any future FRP SKU needs
both; wood has only the strength check.

**Design stresses — the tables, TRANSCRIBED. All superseded by the 2019
`k_BB`/`k_AM` revision.**

Table 8, FRP single skin: hull bottom and side `0,5·σ_uf`; decks and
superstructures `0,5·σ_uf`; structural and tank bulkheads `0,5·σ_uf`;
**watertight bulkheads `0,625·σ_uf`** — where `σ_uf` is the minimum ultimate
flexural strength.

**Table 10, laminated wood — this is ours:**

| material | structural element | design stress `σ_d` |
|---|---|---|
| laminated wood | **all elements except deck** | **0,5 · σ_uf** |
| laminated wood | **deck** | **0,25 · σ_uf** |

> "Where `σ_uf` is the minimum ultimate flexural strength **parallel to the short
> side of the panel** (see Table E.2)"

**Two findings against `SIGMA_D_OKOUME = 15.0`:**

1. **`σ_d` is not a material property, it is a fraction of one, and the fraction
   depends on WHERE the panel is.** A deck panel gets **half** the hull value.
   The module has one scalar for the whole boat, and `assess()` only ever checks
   the bottom — so there is no deck check to be wrong yet, but the constant's
   name (`SIGMA_D_OKOUME`, a species) asserts a material property where the
   standard has a location-dependent allowable.
2. **`σ_uf` is direction-dependent and panel-relative** — "parallel to the short
   side of the panel". Table E.2 (below) gives *different* values parallel and
   perpendicular to the face grain, and which applies depends on **how the sheet
   is oriented on the frame**. That is a manufacturing/export fact, not a
   material constant.

Table 9, metals: aluminium `min(0,9·σ_yw ; 0,6·σ_utw)` (welded condition), steel
`min(0,9·σ_y ; 0,6·σ_ut)`. Table 11, FRP sandwich: `0,5·σ_ut` or `0,5·σ_uc`
(watertight bulkheads `0,625`). Table 12, sandwich core shear: end-grain balsa
`0,4·τ_u` (or `0,5·τ_u` if low-variability and resin-sealed), cross-linked PVC
`0,5·τ_u`, linear PVC / SAN `0,6·τ_u`.

**Stiffeners — TRANSCRIBED coefficients, RECONSTRUCTED equations, eq. (47)/(48):**

    SM  = c · R_c · K_B · P · s · l_u^2 / sigma_d     [cm3]   RECONSTRUCTED
    A_W = k_sa · P · s · l_u / tau_d                  [cm2]   RECONSTRUCTED

with, TRANSCRIBED:

- **`K_B` = 83,3 for end fixity 1** (built-in / fully fixed, i.e. continuous at
  their ends or bracketed); **`K_B` = 125 for end fixity 0** (simply supported,
  i.e. sniped or unbracketed ends).
- **`k_sa` = 5** for stiffeners attached to plating providing an effective area
  greater than the stiffener's cross-section; **7,5 otherwise.**
- **`R_c`, stiffener curvature — Table 14:** `c_u/l_u` 0 to 0,03 → 1;
  0,03 to 0,1 → **1,1 − 3·(c_u/l_u)**; > 0,1 → **0,7**.

**The project has NO stiffener check at all.** `engineer.py` builds to a frame
spacing and `iso12215.py` uses that spacing as the panel short span `b`, but
nothing sizes the frame itself. The draft requires both a section modulus and a
**shear web area** for every stiffener. That is a whole missing check, and the
end-fixity factor (83,3 vs 125, a **50% swing**) says it depends on a
construction detail — bracketed or not — that the arrangement model does not
carry.

**Minimum sandwich skin fibre mass — eq. (45)/(46), coefficients TRANSCRIBED:**
`k_4` (location) = 1,0 bottom shell all craft and side shell forward of 0,6·L_WL
on sailing yachts / 0,9 motor craft side shell and aft of 0,6·L_WL on sailing
yachts / 0,8 deck; `k_5` (fibre type) = 1,0 E-glass with up to 50% CSM by mass /
0,9 continuous glass (biaxial, woven roving, unidirectional) / 0,7 aramid,
carbon or hybrids; `k_6` (care) = **0,9 for category C and D sports boats "used
with care and frequently inspected"** / 1 otherwise — and *"If k_6 = 0,9, a
statement saying that the boat shall be used with care and frequently inspected
for local damage, shall be inserted in the owner's manual"*. **Another factor
that is simultaneously a number and a documentation obligation.**

### 7.5 PLYWOOD PROPERTIES — Annex E, and the check on `SIGMA_D_OKOUME`

**Table E.2 — prediction equations for laminated wood panels, TRANSCRIBED:**

    Plywood, PARALLEL to face grain:
        sigma_uf = SG^0.5  · (68 - 2*N_ply + 0,03*N_ply^2)          [N/mm2]
        E_f      = SG^0.75 · (11400 - 580*N_ply + 16*N_ply^2)       [N/mm2]

    Plywood, PERPENDICULAR to face grain:
        sigma_uf = SG^0.5  · (11 + 6,5*N_ply - 0,28*N_ply^2)        [N/mm2]
        E_f      = SG^0.75 · (1320*N_ply - 55*N_ply^2 - 1200)       [N/mm2]

with, verbatim:

> "**SG** is the specific gravity (density in kg/m³ / 1000) of the plywood in
> question. It is intended that this Figure should be obtained by measurement of
> actual samples. This Figure will include the presence of glue lines and **may
> exceed the density of the base wood by 10%+**.
> **N_ply** is the number of plies, **presumed to be an odd number between 5 and
> 15**.
> a) The **parallel** to the face grain value is to be used in equation (39) when
> the face grain runs parallel to the **SHORT** panel side.
> b) The **perpendicular** to the face grain value is to be used in equation (39)
> when the face grain runs at 90° to the SHORT panel side."

**These two equations are the closest thing to a directly usable result in this
whole review**, and they are also the clearest example of why §7.0 matters: they
are from a 2004 draft of a superseded edition, and the 2019 edition rewrote
Annex F entirely (§4.5 — plywood is Annex **F** in 2019, not Annex E).

**Table E.3 — pre-calculated plywood properties, TRANSCRIBED** (the draft's own
evaluation of Table E.2):

| density kg/m³ | N_ply | σ_uf ∥ | σ_uf ⊥ | E_f ∥ | E_f ⊥ |
|---|---|---|---|---|---|
| 400 | 5 / 7 / 9 / 11 | 37 / 35 / 33 / 31 | 23 / 27 / 30 / 31 | 4 476 / 4 086 / 3 760 / 3 499 | 2 024 / 2 688 / 3 131 / 3 352 |
| 450 | 5 / 7 / 9 / 11 | 39 / 37 / 35 / 33 | 24 / 29 / 31 / 33 | 4 890 / 4 464 / 4 108 / 3 822 | 2 211 / 2 937 / 3 420 / 3 662 |
| 500 | 5 / 7 / 9 / 11 | 42 / 39 / 37 / 35 | 26 / 30 / 33 / 34 | 5 292 / 4 831 / 4 445 / 4 136 | 2 393 / 3 178 / 3 701 / 3 963 |
| 550 | 5 / 7 / 9 / 11 | 44 / 41 / 39 / 37 | 27 / 32 / 35 / 36 | 5 684 / 5 189 / 4 775 / 4 443 | 2 571 / 3 414 / 3 976 / 4 257 |
| 600 | 5 / 7 / 9 / 11 | 46 / 43 / 41 / 38 | 28 / 33 / 36 / 38 | 6 067 / 5 538 / 5 097 / 4 742 | 2 744 / 3 644 / 4 244 / 4 544 |

**THE CHECK ON `SIGMA_D_OKOUME = 15.0`.** With `σ_d = 0,5·σ_uf` (Table 10, all
elements except deck), a design stress of 15,0 N/mm² implies **σ_uf = 30,0
N/mm²**. Okoume marine ply is typically 400–450 kg/m³. Reading Table E.3 at that
density:

| orientation | 400 kg/m³ | 450 kg/m³ | implied σ_d = 0,5·σ_uf |
|---|---|---|---|
| ∥ face grain, 5–11 ply | 31–37 | 33–39 | **15,5 – 19,5** |
| ⊥ face grain, 5–11 ply | 23–31 | 24–33 | **11,5 – 16,5** |

**So 15,0 N/mm² is a real plywood number and it sits at the bottom of the
parallel-grain band / middle of the perpendicular band for okoume-density ply.**
It is not invented, and it is conservative against the parallel orientation.
**What it is NOT: attributable.** It is a single scalar standing in for a
two-parameter family (`SG`, `N_ply`) crossed with a panel-orientation choice,
and the module cannot say which cell of that table it means. That is precisely
the state `refdata.RefValue` exists to make visible, and it argues for the ply
strength becoming a *derived* quantity from measured density and ply count
rather than a constant — **once a text that is actually current is held.**

**Table E.1 — mechanical properties of typical wood species, TRANSCRIBED
(extract).** Densities in kg/m³, strengths in N/mm², all parallel to grain:

| species | ρ | σ_uf | σ_uc | τ_u |
|---|---|---|---|---|
| Douglas fir (*Pseudotsuga menziesii*) | 520 | 74 | 41 | 8,9 |
| European larch (*Larix decidua*) | 545 | 74 | 37 | 9,8 |
| Western red cedar (*Thuja plicata*) | 368 | 52 | 28 | 6,8 |
| European spruce (*Picea abies*) | 400 | 52 | 28 | 7,6 |
| Sitka spruce (*Picea sitchensis*) | 384 | 53 | 29 | 6,9 |
| **African mahogany (*Khaya anthotheca*)** | 513 | 67 | 36 | 10,0 |
| Sapele (*Entandrophragma cylindricum*) | 673 | 89 | 47 | 14,3 |
| Utile/Sipo (*Entandrophragma utile*) | 641 | 83 | 48 | 13,5 |
| Iroko (*Chlorophora excelsa*) | 657 | 72 | 43 | 11,3 |
| Teak (*Tectona grandis*) | 641 | 84 | 48 | 11,8 |

with **generic density correlations for any other species, TRANSCRIBED:**

    softwood:  sigma_uf = 0,137*rho   sigma_uc = 0,073*rho   tau_u = 0,019*rho
               E_f = 19,5*rho
    hardwood:  sigma_uf = 0,130*rho   sigma_uc = 0,070*rho   tau_u = 0,018*rho
               E_f = 17,5*rho

> "NOTE The values presented in Table E.1 correspond to **80 % of mean values**
> obtained from tests on small, essentially defect-free samples. The values shall
> be used with allowable stress factors as given in Table 10."

**Okoume (*Aucoumea klaineana*) is NOT in Table E.1.** The generic hardwood
correlation at ρ = 430 kg/m³ gives σ_uf ≈ 0,130 × 430 ≈ **56 N/mm² for the SOLID
wood**, which is a different quantity from the **plywood panel** flexural
strength in Table E.2/E.3 (≈ 31–39 ∥). Both are needed and they are not
interchangeable — the panel value already accounts for the cross-plied
construction. Confusing them would overstate plywood strength by ~50%.

**Also TRANSCRIBED, and it is a real constraint on how a `σ_uf` may ever be
sourced (E.2.1/E.2.2):** where properties come from tests, *"σ_uf used in the
calculations shall be **80% of the mean ultimate strength or mean ultimate
strength minus two standard deviations whichever is the lower**"*; where they do
not, they come from guaranteed minimum manufacturer data, or **80% of typical
manufacturer data**, or a verified stack analysis, or the Table E.2 equations.
**Every route has a knock-down factor built in.** A datasheet number typed
straight into `SIGMA_D_OKOUME` would be missing it.

### 7.6 What the free draft does NOT settle

- **No current value.** Everything above is 2004, two editions and one
  corrigendum behind (§7.0).
- **The equations are RECONSTRUCTED, not transcribed** (§7.1). Installing
  poppler and re-rendering pages 14–20 and 30–38 of the NMMA PDF as images would
  convert most of §7.3–§7.4 from RECONSTRUCTED to TRANSCRIBED **at zero cost**,
  and is the single highest-value follow-up in this file.
- **`k_BB` and `k_AM` do not exist in the draft at all.** They were introduced in
  2019 specifically to modulate design stresses. **There is no free source for
  them anywhere in this review**, and they multiply `σ_d`, which sets thickness
  as `1/√σ_d`. **This is the irreducible reason to buy ISO 12215-5.**
- **Annex A (2019) — the "simplified" method — is not this draft's Annex A.** The
  2019 Foreword records that the previous assessment method was *moved into*
  Annex A. So the draft's body ≈ the 2019 Annex A, roughly, and the draft's
  Annex A (the graphical method for category C/D under 12 m) is something else
  again. Do not map them one to one.
- **NOT FOUND: any public ISO/DIS or ISO/FDIS of the 2019 revision.** Only this
  2004 draft of the first edition is public. §6.4.

### 7.7 Other secondary sources

**PENDING** — a parallel search for academic papers, university course notes and
software-vendor documentation reproducing the 12215-5 formulas is still running.
Anything it returns will be added here under the **SECONDARY SOURCE** grade, with
author, title, year, URL and — mandatorily — **which edition of ISO 12215-5 the
source is quoting**, dated using the three tests in §4.1 (`n_CG` vs `k_DYN`;
presence of a `k_AR min` floor; mandatory vs recommended minimum thickness) and
against the 2023-11 corrected-version boundary.

---

## 8 · INDUSTRY ASSOCIATIONS AND WHAT THEY PUBLISH FREE

### 8.1 NMMA — the one that mattered

**National Marine Manufacturers Association, `nmma.org`.** Its certification
"tech updates" library hosts **`ISO/DIS 12215-5.3` in full and free** (§6.4, §7).
95 pages, `ISO TC 188/WG 18`, dated 2004-12-18, marked *"Validation version"*.

**This is the single most productive free source found in this review, and it was
found by an ordinary web search that also returned pirated full texts of the
published standard on the first page.** The difference between the two is not
subtle and is worth stating: a DIS circulated for public validation, hosted by
the US member body's industry association, is a document ISO put into public
circulation on purpose. A scan of the published 2019 text on a file-sharing site
is not. **We used the first and did not open the second.**

Worth a follow-up nobody has done: the same directory naming scheme
(`/lib/docs/nmma/cert/techupdates/`) suggests other TC 188 drafts may sit beside
it. **NOT CHECKED.**

### 8.2 ISO/TC 188 itself

`committee.iso.org/home/tc188` — see §6.7. Public, reachable, current, and the
only free source found for the **18-month transitional rule** and for which
standards are under revision.

### 8.3 Everything else

**PENDING** — a parallel survey of RSG, ICOMIA, European Boating Industry,
British Marine, ABYC, SNAME, RINA, the class societies' free rule sets and the
USCG *Boatbuilder's Handbook* is still running. Its results land here.

Two things already established elsewhere that belong in the summary when it does:

- **RSG's guidance is free and substantial**, and EU-REGULATORY.md §3 is built on
  it — 338 pages of ERFU/RFU rulings interpreting RCD clauses. It states no
  stability or scantling number (that review's §3.3), by design.
- **ABYC standards are paid.** `refdata.absent()['ergonomics.abyc_h41_dimensions']`
  already records H-41's dimensions as behind membership; **NOT PRICED in this
  review.**

---

## 9 · RECOMMENDED PURCHASE ORDER

**A proposal for whoever owns `navalai/refdata/`. Nothing was edited.** All
prices are SIS PDF single-user, measured 2026-08-13 (§1.3). No exchange rate is
asserted; totals are in SEK.

### 9.0 STEP ZERO, AND IT COSTS NOTHING — do this before buying anything

Three actions, in this order, each of which can change what is worth buying:

1. **File a Regulation 1049/2001 access request with the European Commission for
   `EN ISO 12215-5:2019` and `EN ISO 12217-1:2017`** (§6.3). Post-*Malamud*
   these are, on the Court's own reasoning, part of EU law. Cost: an email and
   some weeks. **Upside: 3 853 SEK and a legitimate read.** Downside: a refusal,
   which is itself a citable finding worth recording here. **Caveat that must be
   written into the record either way: a watermarked read-only copy licenses
   READING, not redistribution — it lets a reviewer confirm coefficients and
   close Gate 6R honestly; it does not license copying tables into `limits.py`
   as published values.**
2. **Ask SIS (or ISO) whether `SS-EN ISO 12215-5:2019` ships the ISO
   `Corrected version 2023-11`** (§4.1). The CEN adoption was approved
   2019-06-18 and the corrections are dated 2023-11, and they land in Clause 7,
   Clause 9, Table 12 and Table 17 — the four things being bought. **Buying the
   uncorrected text and transcribing from it would install known-wrong formulae
   with an impeccable citation**, which is the worst possible outcome and the
   one this project's whole provenance discipline exists to prevent.
3. **Re-read ISO/TC 188's public news page** (§6.7) for revisions in progress.
   It already tells us `ISO 11812` is being revised.
4. **Render the remaining equation pages of the free NMMA draft** (§7.1's
   `qlmanage` recipe, pages named in §7.3). It costs one command per page and it
   converts the last RECONSTRUCTED items — `k_ar`, the side and deck pressures,
   and the stiffener section modulus and shear area — into transcriptions. It
   will not make them *current*, but it means that when the purchased text
   arrives, a transcription error is visible instead of invisible.

### 9.1 The order, with justification and running cost

**TIER 1 — buy these, in this order. 6 477 SEK.**

| # | buy | SEK | why, and why here |
|---|---|---|---|
| 1 | **EN ISO 8666:2020** | 1 937 | §3.6. **No normative dependencies** — it is the only terminal node in the family, and every other standard's Clause 4 defers to it. It supplies the measurand (`L_H`) behind six length thresholds, one cubic; the loading conditions (`mLDC`, `mLC`, `mML`, `mOC`); **`T_C` and `β`, which are ISO 12215-5 Table 7/12/13 inputs**; and Clause 8 *Tolerances*, the only external anchor in the family for the `sigma` this project attaches to every principal dimension. |
| 2 | **EN ISO 8666:2020/A11:2021** | 687 | Separate SIS product, cited in the same OJ row. The `/A11` is the European amendment — i.e. the part that makes it harmonised. Buying 8666 without it buys the ISO text and not the harmonised one. |
| 3 | **EN ISO 12215-5:2019** | 1 988 | **The only remaining Gate 6R edition defect** (EU-REGULATORY.md §7.6). §4.3 and §7 together show the stand-in is wrong in *shape*, not merely in coefficients — and §7 makes it concrete against a real (if superseded) text: the design pressure should be an **areal loading** `0,1·mLDC/(L_WL·B_C)` times a dynamic amplification `(1 + f_w·n_cg)`, modulated by `k_ar` and `k_L`, floored at `10·(T_c + f_w·L_h/17)`. The module has `max(10, 2,4·mLDC^0,33 + 20)` — no beam, no waterline length, no design category, no acceleration, no area reduction, no longitudinal distribution, and a constant floor. **§7.4 also shows the thickness formula IS right in shape**, so the purchase is buying pressure coefficients and design stresses (`k_BB`, `k_AM` — for which §7.6 records there is no free source anywhere), not a new method. Target: **Clauses 8, 9, 10 and Annexes A and F** (plywood is Annex F, normative, pp. 80–88). **Subject to 9.0 step 2.** |
| 4 | **EN ISO 12217-1:2017** | 1 865 | Note the edition: **2017, not 2022** (§2.2, §5.2) — the harmonised text is ISO 12217-1:2015, which is what `review.py` already records. The justification is **not** Gate 6R (that entry is filled) and **not** the GM floor (there isn't one) and **not** the wave heights (free from the RCD). It is RCD Art. 20(1)(b)(i): for a **category C craft under 12 m — most of the SKU range — compliance with the harmonised ER 3.2/3.3 standards is the condition for Module A**, the only conformity route with no notified body. It also re-confirms R-DFH (Annex A) and R-OLH (Annex B) against the harmonised text and supplies the crew-mass and crowding-fraction basis. **Subject to 9.0 step 1.** |

**TIER 2 — the sub-6 m band. +3 285 SEK, running 9 762 SEK.**

| # | buy | SEK | why |
|---|---|---|---|
| 5 | **EN ISO 12217-3:2017** | 1 865 | The dayboat SKU is 4–7 m and `PARAMS["LWL"].low` is 4.0, while `R-SCP` refuses everything under 6 m with **no verdict**. The RCD adds two free rules that fire in exactly that band and in **opposite** directions (A 3.3 below 6 m, A 3.7 above it). Edition **2017**, not 2022. |
| 6 | **EN ISO 11812:2018** | 1 420 | Not merely a cockpit standard. ISO 12217-1's own Scope (§5.1, verbatim) makes the sub-6 m escape hatch conditional on the boat being *"decked and hav[ing] quick-draining recesses **which comply with ISO 11812**"* — so 12217-3 and 12217-1 are both partly unexecutable without it. **But see §2.5: the harmonised text is ISO 11812:2001, ISO 11812:2020+Amd 1:2024 exists, and TC 188 has just started a third revision.** Buy the harmonised one and record why. |

**TIER 3 — the export and arrangement surface. +4 495 SEK, running 14 257 SEK.**

| # | buy | SEK | why |
|---|---|---|---|
| 7 | EN ISO 12215-6:2018 | 1 599 | *Structural arrangements and details.* ISO 12215-5's Introduction says explicitly *"Many details can have a significant influence on the final stresses and strength of the structure, **ISO 12215-6 shows 'established practice'**"* — i.e. Part 5 hands the detail design to Part 6 by name. This is the standard behind hull/deck joints, stiffener terminations and bulkhead attachment, none of which the project models. |
| 8 | EN ISO 15085:2024 | 1 420 | Already in `PURCHASE_QUEUE`. **Newly harmonised 13.03.2026 by decision 2026/550** — so the 2003 zone numbers `refdata/ergonomics.py` ships are now two editions behind the legal text. The 18-month transitional rule (§2.4) means the previous edition stops conferring presumption around **September 2027**. |
| 9 | EN ISO 14946:2021 | 687 | The builder's-plate **crew-limit basis** (75 kg / 37,5 kg per EU-REGULATORY.md §3.3) and the maximum-load definition. |
| 10 | EN ISO 14945:2021 | 789 | Builder's-plate content. Buy **with** 14946: EU-REGULATORY.md §3.8 records that the two 2021 standards and the ISO 12217:2015 worksheets are **mutually inconsistent** on optional equipment, and ISO 8666:2020 moved that same allowance between clauses (§3.1). Three documents disagree about one mass; **holding two of them and not the third is how a wrong builder's plate gets emitted.** |

**TIER 4 — SKU-conditional. Buy only when the SKU is real. +5 467 SEK, running 19 724 SEK.**

| # | buy | SEK | condition |
|---|---|---|---|
| 11 | ISO 12215-7:2020 | 1 737 | **Catamaran SKU only, and only AFTER 12215-5** — it is inert without it (§4.7). Its real justification is that it adds **six GLOBAL load cases** (transverse bending, torsion, pitchpoling, longitudinal force on one hull, crossbeam bending), and §4.6 records that ISO 12215-5 disclaims global strength entirely — so this is a load class the monohull standard does not contain **at any price**. **Not harmonised** (§1.2): it buys engineering, not presumption. |
| 12 | EN ISO 12217-2:2017 | 1 865 | **WindWing SKU only.** Whether the SKU is even a "sailing boat" is decided free, by ISO 8666 3.10/3.11: `A_S ≥ 0,07·mLDC^(2/3)` (§3.5). **Run that test before spending this.** |
| 13 | ISO 12215-10:2020 | 1 865 | **WindWing SKU only.** Rig loads and rig attachment. Not harmonised. |

**TIER 5 — electrical, if and only if an electrical rules module is planned. +3 541 SEK plus one unpriced item, running 23 265+ SEK.**

| # | buy | SEK | why |
|---|---|---|---|
| 14 | **EN ISO 13297:2021** + /A1:2022 + /A11:2023 | **2 752** | §2.4. This is the **single** harmonised electrical-installation standard now — it merged a.c. and d.c. — and **both standards EU-REGULATORY.md §3.1 names stopped conferring presumption on 25.10.2025.** The most expensive single item in this file. |
| 15 | EN ISO 16315:2016 | **UNPRICED** | The harmonised standard for RCD ER 5.3, whose full Annex ZA clause map the RSG guide already publishes free (EU-REGULATORY.md §3.7) — so it is the cheapest electrical purchase to *scope* and the price is the one thing not established. **NOT FOUND on SIS.** |
| 16 | **EN ISO 8665-2:2024** | 789 | *Power measurements and declarations — Part 2: **Electric marine propulsion***. **Newly harmonised 13.03.2026, decision 2026/550.** This is the standard that says what "power" means for a solar-electric craft, and it did not exist as a harmonised reference when EU-REGULATORY.md was written. Cheap, current, and directly on this project's propulsion architecture. |

### 9.2 DO NOT BUY — with reasons, so nobody re-proposes them

| standard | SEK | why not |
|---|---|---|
| EN ISO 12215-1:2018 | 943 | **ISO's own Foreword to 12215-5:2019, verbatim: *"NOTE The mechanical properties of ISO 12215-1 to -3 are largely superseded by the ones of this document."*** |
| EN ISO 12215-2:2018 | 943 | same |
| EN ISO 12215-3:2018 | 943 | same — and this is the *wood and metals* materials part, so the temptation is real. **Annex F of Part 5 is the normative plywood route.** |
| EN ISO 12215-4:2018 | 943 | *Workshop and manufacturing* — process control, not scantlings. |
| **subtotal avoided** | **3 772** | on ISO's own statement, not on ours |
| EN ISO 12216:2018 | 1 737 | Nothing in the tree models a window or hatch. Also §2.5: harmonised text is ISO 12216:**2002**, current ISO is 2020. |
| EN ISO 9094:2017 | 1 420 | `flotation.NOT_SOURCED` names the fire numbers, so this WOULD close a logged absence — but nothing consumes them and ES-TRIN Art. 26.01(2)(d) already offers `ISO 9094:2022` as an alternative route. Keep queued, buy last. |
| EN ISO 6185-1..4:2018 | 1 420 / 1 250 / 1 420 / 1 250 | No inflatable SKU exists or is planned. |
| EN ISO 8665:2017 | — | Reciprocating internal-combustion engines. **A solar-electric craft has no "propulsion engine" under RCD Art. 3(5)** (EU-REGULATORY.md §3.6). Buy 8665-**2** instead. |
| ISO 12217-1:2022 | — | Newer than the harmonised text and confers **no** presumption of conformity (§2.2, §5.2). Buying it instead of the 2017/2015 text would be a strict downgrade in legal value. |

### 9.3 Totals

| scope | SEK |
|---|---|
| **Tier 1 — closes Gate 6R's last defect and the measurand gap** | **6 477** |
| Tiers 1–2 — adds the sub-6 m band the dayboat SKU lives in | 9 762 |
| Tiers 1–3 — adds detail design, reboarding and the plate | 14 257 |
| Tiers 1–4 — adds catamaran and WindWing | 19 724 |
| Tiers 1–5 — adds electrical (16315 still unpriced) | **23 265 +** |
| avoided by ISO's own supersession note (12215-1/-2/-3/-4) | −3 772 |
| **potentially avoided by a successful Reg. 1049/2001 request** | **−3 853** |

**The honest headline: 6 477 SEK buys everything needed to turn Gate 6R green
legitimately and to stop substituting `L_WL` for `L_H`. Everything above that is
SKU expansion or a different domain.** And the first 3 853 SEK of it may be
obtainable for the cost of an email (§9.0).

### 9.4 Corrections owed to `refdata.PURCHASE_QUEUE`, with the evidence

Reported, not applied — `navalai/refdata/__init__.py` is another agent's file.

1. **Row 1 names `ISO 12217-1:2022`. The edition to buy is `EN ISO 12217-1:2017`
   (= ISO 12217-1:2015).** §2.2, §5.2. The 2022 exists but is not harmonised.
2. **Row 1 says the purchase *"CLOSES HALF OF GATE 6R (RED)"*, supplies *"the GM
   floor"* and *"the significant wave height each category implies"*.** All three
   are stale (EU-REGULATORY.md §9.1 already establishes this); the real
   justification is RCD Art. 20(1)(b)(i) and Module A.
3. **Row 2 (12215-5) should name the dated edition `EN ISO 12215-5:2019` as a
   PURCHASING TARGET and carry the `Corrected version 2023-11` warning** — with
   the explicit note that the string must never be written into
   `review.REVIEW["editions"]`.
4. **The 12215-7 row's justification should be the six GLOBAL load cases, not
   "the harmonised multihull standard"** — there is no such thing (§1.2, §4.7).
5. **A new row for `EN ISO 8666:2020` + `/A11:2021` is owed** — the coordinator
   reports this was added while this review ran. **It is TWO products,
   1 937 + 687 = 2 624 SEK**; a row naming only the base standard under-buys.
6. **If an electrical row is ever added, it is `EN ISO 13297:2021 + /A1:2022 +
   /A11:2023`, not the 10133/13297:2018 pair** — both of those died 25.10.2025
   (§2.4).
7. **A new candidate row: `EN ISO 8665-2:2024`, 789 SEK** — the electric
   propulsion power-declaration standard, harmonised 13.03.2026.
