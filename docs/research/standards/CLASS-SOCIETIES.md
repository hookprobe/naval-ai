# Free classification-society scantling rules — what is actually downloadable, and what it says

**STATUS: SWEEP COMPLETE 2026-08-13** for the societies named below. It is NOT
exhaustive — DNV is paywalled, RINA is registration-walled, and eight other
societies were not attempted. Those are listed, as leads, at the end.

Sources READ, in descending order of value to this project:

| # | Document | Free? | Covers |
|---|---|---|---|
| BV.2 | **BV NR546**, Hull in Composite Materials and Plywood, Nov 2018 | direct PDF | **the ONLY free PLYWOOD scantling method found** — formula, species, grades, properties |
| LR.1 | **LR Rules for Special Service Craft, July 2020** | LR Foundation, CC BY-ND | best-structured loads + the only published SERVICE-AREA factor ladder + 40 rows of allowables |
| ABS.1b | **ABS Guide for Building and Classing Yachts 2021, Part 3** | direct PDF | cleanest machine-readable FRP single-skin and sandwich equations |
| BV.1 | **BV NR500**, Rules for … Yachts, Oct 2024 | direct PDF (wrapped + encrypted) | the PARTIAL SAFETY FACTOR system — process, ageing, load-type, data-provenance |
| ABS.2 | **ABS Guide for Building and Classing Offshore Racing Yachts, 1994** | direct PDF | withdrawn, but the only one covering ALL our materials in one place, up to 30,5 m |

**The headline results**, each traced to a clause below:
- **Plywood was the gap and BV closes it** (NR546 Sec 8): thickness formula,
  seven approved species with full orthotropic properties, BS 1088 + EN-314
  Class 3 + >500 kg/m³ quality spec, `SF >= 4,0`.
- **Nobody applies a knock-down factor to CARBON.** Three societies handle it as
  an admissibility / minimum-thickness question instead. That reframes where
  carbon belongs in our code.
- **ABS and LR publish the SAME displacement-mode bow-slamming formula**, which
  independently resolved a grouping this file had flagged as uncertain.
- **BV's factorised safety system and LR's flat allowables table agree to three
  significant figures** on a hand-laid FRP bottom panel (0,278 vs 0,28).
- **What is NOT free is SCOPE, not formulas**: LR routes <= 24 m yachts to the
  RCD (i.e. to ISO 12215) explicitly, and ABS's yacht guide is written for
  >= 24 m. DNV-ST-0342, whose 6–24 m scope is the closest match to this project
  of any document named here, is the one we cannot read.

## Why this file exists

The project needs structural scantling rules for 5–15 m craft in plywood,
single-skin FRP, carbon and foam-core sandwich. ISO 12215-5 is the obvious
source and it is PAID. This file records what CLASSIFICATION SOCIETIES publish
for free that could substitute or cross-check it.

## Reading rules for this file (project honesty rules apply)

- **READ** means: the PDF was downloaded to this machine and the clause text was
  extracted and transcribed here. Every such clause carries document title,
  edition, clause number and the URL it came from.
- **UNVERIFIED** means: not opened. Anything so marked is a lead, not a source.
- **PAYWALLED** means: the download was attempted and refused/absent. The
  formula is NOT reconstructed from secondary sources.
- Figures (curves read off a graph, e.g. ABS `FD`, `FV`, `KV`) are recorded as
  FIGURE, NOT AS A FORMULA. A curve this file cannot transcribe is a gap, and
  saying so is the point.

## Download-availability summary (measured 2026-08-13)

| Society | Portal | Free full-text PDF? | Measured |
|---|---|---|---|
| ABS | `ww2.eagle.org/content/dam/eagle/rules-and-guides/...` | **YES — direct, unauthenticated PDF** | 5.3 MB `yacht-part-3-jan21.pdf` (317 pp) and 1.6 MB `pub37_ory_guide_op.pdf` (57 pp) both downloaded with plain `curl`, HTTP 200 |
| DNV | `rules.dnv.com/docs/pdf/...` | **NO (for the craft docs tried)** | `DNV-ST-0342.pdf` and `DNVGL-RU-HSLC-Pt3Ch4.pdf` return the SPA shell (739 B) or a 404 page (507 B) at every path/edition combination tried. See "DNV" below for the exact URLs. |
| BV / LR / RINA / others | — | TBD | not yet probed |

---

## ABS — American Bureau of Shipping

ABS is the highest-value free source found so far: current rules and guides are
served as **unauthenticated PDFs from `ww2.eagle.org`**, no login, no referrer
check. Verified by direct `curl` with only a browser User-Agent.

### ABS.1 — Guide for Building and Classing Yachts, 2021, Part 3 "Hull Construction and Equipment"

- URL: `https://ww2.eagle.org/content/dam/eagle/rules-and-guides/archives/special_service/62_yachts_2021/yacht-part-3-jan21.pdf`
- 317 pages, text layer extracts cleanly with `pypdf`. **READ.**
- Note: this is the **2021 archived edition**. A 2025 edition exists
  (`.../notices/july-2025/62-yacht-nandgi-jan25.pdf` is its notices file) —
  UNVERIFIED whether the 2025 scantling clauses differ.

**SCOPE CAVEAT — this is a big-yacht guide.** Definitions are written around
`L` = scantling length with tables (e.g. 3-2-2/1.5 TABLE 4, factor `f`) starting
at **L = 24 m**, and 3-2-2/3.5 explicitly says `L` is "generally not to be taken
less than 30 m (98 ft)" for the fore-end side pressure. Applying these formulas
to a 5–15 m craft is EXTRAPOLATION BELOW THE STATED RANGE. For our size band
the ABS **Offshore Racing Yachts** guide (ABS.2) is the in-scope document.

#### Speed regime split (3-2-2/1.1, 3-2-2/3.1)

The guide branches on speed–length ratio, with `L` in metres, `V` in knots:

| Regime | Condition | Load section |
|---|---|---|
| Displacement | `V <= 2.36*sqrt(L)` | 3-2-2/1 (design HEADS, metres of water) |
| High-speed displacement | `2.36*sqrt(L) < V <= 3.63*sqrt(L)`, negligible dynamic lift and very low running trim | 3-2-2/1 |
| Semi-planing / planing | `V > 2.36*sqrt(L)` | 3-2-2/3 (design PRESSURES, kN/m²) |

(US units: 1.30*sqrt(L) and 2.0*sqrt(L) with L in ft.)

Semi-planing/planing pressures must be evaluated in BOTH a full-load and a
light-load condition; light load = 10% of maximum operating deadweight, at the
maximum speed for that displacement (3-2-2/3.1).

#### 3-2-2/1.1 TABLE 1 — Displacement yachts, design head `h` (metres of water)

Pressure is `h` metres of head; convert with `p = rho*g*h`. Head is measured
from the LOWER EDGE of the plate panel for plating, and from the CENTRE OF AREA
SUPPORTED for internals.

| Location | Design head `h`, m |
|---|---|
| Bottom structure | distance to main weather deck at side, **not less than `L/10` or 2.15 m, whichever is greater** |
| Bottom, fore slamming | `Hfs`, see 3-2-2/1.3 |
| Side structure | distance to main weather deck at side, **not less than `0.66*D` or `L/15`, whichever is greater** |
| Side, fore slamming | `Hfs` at the waterline, reducing to `0.40*Hfs` at the weather deck |
| Deep tanks | to the greater of: (1) ⅔ of the distance to the main weather/bulkhead deck; (2) ⅔ of the distance from tank top to top of overflow; (3) a point above the tank top not less than `0.01L + 0.15` m or 0.46 m |
| Watertight bulkheads | distance from lower plate edge (plating) / centre of area (internals) to the main weather or bulkhead deck at centreline |
| Main weather deck (exposed) | `0.02L + 0.46` m |
| Superstructure/deckhouse decks fwd of 0.25L (exposed) | `0.02L + 0.46` m |
| Superstructure/deckhouse decks elsewhere (exposed) | `0.02L + 0.46` m |
| Deckhouse top, first tier | `0.01L + 0.46` m |
| Deckhouse tops above 2nd tier (weather covering only) | `0.01L + 0.15` m |
| Internal accommodation decks (in hull-girder SM) | `0.01L + 0.30` m |
| Internal accommodation decks (not in hull-girder SM) | 0.35 m |

*(The deck rows are a merged cell in the PDF; the first three deck rows share
the single value `0.02L+0.46` m as printed.)*

#### 3-2-2/1.3.1 — Bottom forward slamming head `Hfs`

```
Hfs = N4 * Ks * (19 - 2720 * (d / Lw^2)) * Lw * V        metres
```
with
- `N4` = 0.1045 (SI; 0.1818 US)
- `Ks` = 0.09 at the forward end of `Lw`; **0.18** at 0.1L and at 0.2L from the
  forward end of `Lw`; **0** at 0.5L from the forward end and aft
- `d` = stationary draft, m, measured at centreline from the outer shell to the
  DWL at mid-`Lw`, **not less than `0.04L`**
- `Lw` = waterline length at design displacement, m
- `V` = maximum design speed in calm water, knots

NOTE ON THE TRANSCRIPTION: the extracted text renders the bracket as
`19 − 2720 · d / Lw^2` with the `2` of `Lw²` on its own line. The grouping above
(`d` over `Lw²`) is the dimensionally consistent reading — `Ks` and the bracket
are dimensionless only if `d/Lw²` is, which it is not in SI either, so **this
one grouping is INFERRED, not read**. Treat `Hfs` as needing a figure check
against the rendered page before it is coded. Flagged, not silently fixed.

#### 3-2-2/1.5 — Superstructure and deckhouse bulkhead heads

```
h = a * k * [ (b*f) - y ] * c       metres
```
- `a` = bulkhead-location/length factor, TABLE 2 below
- `k` = **service factor: 1.0** for Yachting Service and Commercial Yachting
  Service; **0.85** for restricted yachting service notation `R`. *(This is the
  ABS analogue of an ISO design category — it is the only service-area knob in
  the displacement-load path, and it is a 15% reduction, not a category ladder.)*
- `b` = longitudinal-position factor, TABLE 3
- `f` = length factor, TABLE 4
- `y` = vertical distance, m, from the DWL to the midpoint of the stiffener/panel
- `c` = **1.0 for superstructures, 0.85 for deckhouses**
- `x` = distance, m, from the after perpendicular to the bulkhead considered.
  Deckhouse SIDE bulkheads are divided into equal parts not exceeding `0.10L`,
  and `x` runs to the centre of each part.

Floors on `h`, regardless of the formula:

| Location | `h` floor, m |
|---|---|
| Unprotected fronts, lowest tier | `0.01L + 2.5` |
| All other locations, lowest and second tier | `0.005L + 1.25` |
| All other locations, third tier and above | `1.5` |

TABLE 2, values of `a` (metric, `L` in m):

| Bulkhead location | `a` |
|---|---|
| Unprotected front, lowest tier | `2.0 + L/120` |
| Unprotected front, second tier | `1.0 + L/120` |
| Unprotected front, third tier | `0.5 + L/150` |
| Protected front, all tiers | `0.5 + L/150` |
| Sides of superstructures, inset from side <= 0.04B | as for front bulkheads above |
| Sides of deckhouses, all tiers, inset > 0.04B | `0.5 + L/150` |
| Aft ends, aft of amidships, all tiers | `0.7 + L/1000 - 0.8x/L` |
| Aft ends, forward of amidships, all tiers | `0.5 + L/1000 - 0.4x/L` |

TABLE 3, values of `b` vs `x/L`: 0.10 → 1.19 · 0.20 → 1.10 · 0.30 → 1.04 ·
0.40 → 1.00 · 0.45 → 1.00 · 0.50 → 1.00 · 0.60 → 1.05 · 0.70 → 1.15 ·
0.80 → 1.29 · 0.90 → 1.49.

TABLE 4, values of `f` vs `L` (m), interpolate: 24 → 1.24 · 40 → 2.57 ·
60 → 4.07 · 80 → 5.41 · 90 → 6.00. **The table starts at L = 24 m — there is no
tabulated `f` for a 5–15 m craft.**

#### 3-2-2/3.3 — Semi-planing / planing MONOHULL bottom pressure

```
Pb = N1 * Δ / (Lw * Bw) * (1 + ncg) * FD * FV        kN/m²     (slamming)
Pd = N3 * (0.64*H + d)                                kN/m²     (hydrostatic)
```
Vertical acceleration (average of the 1/100 highest at LCG), unless from model
test or theory:
```
ncg = N2 * (12*h13/Bw + 1.0) * τ * (50 - βcg) * V² * Bw² / Δ        g
```
- `ncg` **need not be taken greater than 7.0 g**
- `N1` = 0.1 (0.01 tf/m², 0.069 psi)
- `N2` = 0.0078 (0.0078, 0.0016)
- `N3` = 9.8 (1.0, 0.44)
- `Δ` = displacement at DWL, **kg** (lb)
- `Lw`, `Bw` = waterline length and max waterline beam, m
- `τ` = running trim at `V`, degrees, **not less than 4° for L < 50 m**, not
  less than 3° for L > 50 m (lower trims accepted only from full-scale or model
  data)
- `βcg` = deadrise at LCG, degrees, **clamped to 10°–30°**
- `V` = max design speed in calm water, knots
- `H` = wave parameter = `0.0172L + 3.653` m
- `h13` = design significant wave height, m, floor from TABLE 5 below
- `d` = stationary draft, m, **not less than 0.04L**
- `FD` = design-area factor, **FIGURE 2** (a curve of `AD/AR`), **not less than
  0.4**
- `FV` = vertical acceleration distribution factor, **FIGURE 4** (curve vs
  longitudinal position)
- `AD` = design area, cm². For PLATING, the actual panel area but **not more
  than `2.5 s²`**. For longitudinals/stiffeners/transverses/girders, the shell
  area supported; for transverses and girders **not less than `0.33 ℓ²`**.
- `AR` = reference area, cm² = `6.95 Δ / d` (SI; `1.61 Δ/d` in²)
- `s` = stiffener spacing, cm; `ℓ` = unsupported span, cm

**`ncg` TRANSCRIPTION CAVEAT.** The PDF's two-dimensional layout flattens to
`N2 * (12h13/Bw + 1.0) * τ * (50-βcg) * V²(Bw)²/Δ` and the exponents/fraction
bars cannot be recovered from the text layer with certainty. This is the
well-known Savitsky-family planing acceleration form and it is **CLOSE TO
ISO 12215-5's `n_cg`** — but the grouping above is a TEXT-LAYER READING, not a
verified typesetting. **Render 3-2-2/3.3.2 (PDF page index 62) as an image and
confirm before coding it.** Recorded as owed work below.

TABLE 5 — design significant wave height floors `h13`:

| Notation | Operational design condition | Maximum design condition (V = 10 kn) |
|---|---|---|
| Yachting Service / Commercial Yachting Service | 4.0 m | 6.0 m |
| Restricted Yachting Service `R` (<= 200 nm from refuge) | 3.5 m | 4.5 m |

*(This is the closest ABS gets to an ISO design category: TWO service levels,
both far offshore. There is no ABS equivalent of ISO category C/D inshore.)*

#### 3-2-2/3.5 — Side and transom pressure, monohulls

```
Psxx = N1*Δ/(Lw*Bw) * (1 + nxx) * (70 - βsx)/(70 - βcg) * FD      kN/m²   (side slamming)
Ps   = N3 * (Hs - y)                                              kN/m²   (hydrostatic)
Psf  = 0.28 * Fa * CF * N3 * (0.22 + 0.15*tan α) * (0.4*V*sin β + 0.6*sqrt(L))²   kN/m²  (fore-end slamming)
```
- `Psxx` applies **only below `L/12` above baseline and forward of 0.125L**
- `nxx = ncg * KV`, `KV` from FIGURE 3
- `βsx` = side-shell deadrise clear of LCG, degrees, **not greater than 55°**
- `Ps` floors: **`0.05*N3*L`** kN/m² at or below `L/15` above baseline (or any
  height forward of 0.125L from the stem); **`0.033*N3*L`** kN/m² above `L/15`
  aft of 0.125L
- `Hs` = `0.083L + d` m, **not less than `D + 1.22` m for yachts under 30 m**;
  = `0.64H + d` for yachts over 30 m
- `y` = height above baseline of the location considered, m
- `CF` = `0.0125L` for L < 80 m; `1.0` for L >= 80 m
- `Fa` = **3.25 for plating, 1.0 for longitudinals/transverses/girders**
- `α` = flare angle (vertical line to side-shell tangent); `β` = entry angle
- **`L` generally not to be taken less than 30 m** in this sub-clause

#### 3-2-2/3.7 — Semi-planing / planing MULTI-HULL bottom pressure

```
Pbxx = N1 * Δ / (Lw * Nh * Bw) * (1 + ncg) * FD * FV      kN/m²
Pd   = N3 * (Hs - y)                                       kN/m²
ncg  = N2 * (12*h13/(Nh*Bw) + 1.0) * τ * (50 - βcg) * V² * (Nh*Bw)² / Δ     g
```
- `Nh` = number of hulls; `Bw` = max waterline beam **of ONE hull**
- Same transcription caveat as `ncg` above.

**The multihull rule is simply "share Δ over `Nh` hulls and use one hull's
beam".** That is a directly reusable structural insight for our catamaran path
and it is free.

#### Figures that are CURVES and are NOT transcribed (gap)

`FD` (FIGURE 2, design-area factor vs `AD/AR`), `KV` (FIGURE 3), `FV`
(FIGURE 4) are plotted curves with no closed form given in the text. Any code
using ABS planing pressures needs these digitised from the rendered pages.
**NOT DONE — this is real, owed work, not an assumption.**

---

## DNV — measured PAYWALLED for the craft documents

DNV's public rules portal serves an SPA, and every direct-PDF path tried for the
small-craft documents returned either the SPA shell or DNV's own 404 page.
Measured 2026-08-13 with `curl -A "Mozilla/5.0"`:

| URL tried | Result |
|---|---|
| `https://rules.dnv.com/docs/pdf/DNV/ST/2016-07/DNVGL-ST-0342.pdf` | 200, 739 B, `text/html` — SPA shell |
| `https://rules.dnv.com/docs/pdf/DNV/ST/2022-02/DNV-ST-0342.pdf` | 200, 739 B, `text/html` — SPA shell |
| `https://standards.dnv.com/docs/pdf/DNV/ST/2022-02/DNV-ST-0342.pdf` | 404, empty |
| `https://rules.dnv.com/docs/pdf/DNVGL/ST/2016-07/DNVGL-ST-0342.pdf` | 200, 507 B — DNV's "404: Page not found" page |
| `https://rules.dnv.com/docs/pdf/DNVGL/RU-HSLC/{2015-01,2016-01,2017-12,2018-01,2019-07,2019-10,2021-07,2021-10,2022-07}/DNVGL-RU-HSLC-Pt3Ch4.pdf` | all 200, 507 B — DNV 404 page |
| `https://rules.dnv.com/docs/pdf/DNV/{rulesship,ruleshsl}/.../ts301.pdf` (legacy naming) | 301 redirect, 144 B |

`www.dnv.com/rules-standards/` states access is via the Rules and Standards
Explorer (`https://standards.dnv.com/explorer/`) and printed copies via the
Accuris store — i.e. **subscription/purchase, not free download.**

**Therefore: no DNV formula is transcribed in this file.** The documents that
would matter are named below as leads only, all **UNVERIFIED**:
- DNV-ST-0342 *Craft* — scope stated by third-party listings as commercial and
  non-EU-Directive recreational craft, **LOA ~6–24 m, speed up to 45 kn**.
  That size band is EXACTLY ours, which makes it the highest-value DNV target
  and the most annoying paywall.
- DNV-RU-HSLC Pt.3 Ch.4 *Hull structural design, fibre composite and sandwich
  constructions* — the composite scantling chapter.
- DNV-RU-SHIP Pt.3 — steel/aluminium ship structures, not our materials.

*(Continues — further societies appended below as extracted.)*

---

### ABS.2 — Guide for Building and Classing OFFSHORE RACING YACHTS, 1994 — **THE BEST FREE MATCH FOR THIS PROJECT**

- URL: `https://ww2.eagle.org/content/dam/eagle/rules-and-guides/archives/special_service/37_offshoreracingyachts/pub37_ory_guide_op.pdf`
- 57 pages. **READ.**
- **SCOPE (clause 1.5.1, read verbatim): "applicable to offshore racing yachts
  of up to 30.5 m (100 ft) in scantling length as defined in 2.1."** There is no
  lower bound. Table 7.8 explicitly tabulates a band `L < 9.15 m (30 ft)`, so
  the document contemplates craft well inside our 5–15 m range.
- Developed jointly with the Offshore Racing Council's International Technical
  Committee; foreword states the strength standards "have been derived from the
  various existing standards established by satisfactory service experience."
- **It covers ALL FOUR of our materials**: single-skin FRP (7.3.1), FRP sandwich
  (7.3.2), cold-molded wood laminate (7.1), and carvel wood (7.5) — plus steel
  and aluminium. Carbon fibre appears in TABLE 7.8.
- **STATUS CAVEAT: 1994, SUPERSEDED, and ABS files it under `archives/`.** It is
  a *withdrawn* guide. Its value to this project is as a **free, complete,
  self-consistent, ISO-12215-5-SHAPED rule set for cross-checking our physics**,
  not as a certification basis. Say so anywhere it is cited.
- **OCR CAVEAT — READ THIS BEFORE CODING ANYTHING BELOW.** This PDF is a SCAN
  with a noisy OCR text layer. Radicals, fraction bars, subscripts and exponents
  are frequently lost (`σa` comes out as `cr„`, `t²` as `t"`). Every formula
  below is marked either **[LEGIBLE]** (all symbols and operators recovered) or
  **[GROUPING INFERRED]** (symbols recovered, structure reconstructed from
  dimensional consistency and the surrounding definition list). **Nothing marked
  [GROUPING INFERRED] may be coded without rendering the page as an image and
  confirming.** That confirmation is owed work, listed at the end of this file.

#### ORY 7.1 — Plating: aluminium, steel and COLD-MOLDED WOOD LAMINATE

**[GROUPING INFERRED — radical lost by OCR]**
```
t = s * c * sqrt( p * k / σa )        mm
```
- `s` = spacing, mm, of the shell/deck longitudinal, transverse frame, deck beam,
  bulkhead stiffener or other supporting member. **Where the plating is curved,
  `s` is the CHORD LENGTH between the two supporting members.**
- `p = 0.01 * F * h` (SI; `0.001 Fh` metric-kgf, `0.44 Fh` ft-in) **[LEGIBLE]**
- `h` = design head, m, from TABLE 7.1
- `F` = design-head reduction factor, TABLE 7.4 (shell) / TABLE 7.5 (deck).
  **`F*h` is in general not to be taken less than `D` for the BOTTOM shell, nor
  less than `0.8 D` for the SIDE shell** (`D` = depth per 2.5).
- `k` = panel aspect-ratio coefficient, TABLE 7.3; **not less than 0.5 for
  cold-molded wood laminate** unless specially approved
- `σa` = design stress, N/mm², TABLE 7.2
- **`c = (1 - A/s)` = CURVATURE correction, NOT to be taken less than 0.70**,
  where `A` = distance, mm, measured perpendicular from the chord `s` to the
  highest point of the curved plating arc between supports. **[LEGIBLE]**
  *(This is a genuinely different curvature model from ISO 12215-5's, which uses
  crown height over chord in a `k_C` polynomial. ABS caps the benefit at 30%.)*

Minimum thicknesses after all else: **steel `s/115` or 2.5 mm**, whichever is
greater; **aluminium `s/100` or 2.5 mm**, whichever is greater.

Plating thickness is **not to be reduced locally** for closely spaced local
stiffening (floors at the ballast keel, stringers in the slamming area).

#### ORY 7.3.1 — Plating: SINGLE-SKIN FRP — two equations, both must be met

Equation **(a)**, STRENGTH **[GROUPING INFERRED — radical lost]**:
```
t_a = s * c * sqrt( p * k / σa )      mm
```
Equation **(b)**, STIFFNESS/DEFLECTION. Raw OCR reads
`t = 0.75 sc  [pk1]  0.02 E`, i.e. a cube-root form **[GROUPING INFERRED]**:
```
t_b = 0.75 * s * c * ( p * k1 / (0.02 * E) )^(1/3)      mm
```
- `p = 0.01 F h` (SI) as above
- In equation (a), `F*h` is **not less than `D` for the bottom shell nor less
  than `0.5 D` for the side shell**. *(Note: 0.5D here, against 0.8D in 7.1 for
  wood/metal — the two clauses genuinely differ and the difference was read, not
  assumed.)*
- In equation (b), **`F` is not less than 0.5 for bottom and side shell**.
- `k` = aspect-ratio coefficient, TABLE 7.3, **not less than 0.5 for
  UNI-DIRECTIONAL laminates**
- `k1` = aspect-ratio coefficient, TABLE 7.3, **not less than 0.028 for
  uni-directional laminates**
- `E` = minimum FLEXURAL modulus of the laminate
- `σa` = design stress, TABLE 7.2

Uni-directional laminate orientation rule: the warp (greater-reinforcement axis)
is in general to run **fore-and-aft**, and to be **perpendicular to the LONGEST
edge of the panel, i.e. parallel to `s`**.

**The two-equation structure — a strength check AND a stiffness check on the
same panel — is the same structure ISO 12215-5 uses. This is the cross-check.**

#### ORY TABLE 7.3 — aspect-ratio coefficients `k` and `k1` **[LEGIBLE]**

Aspect ratio is printed as `ℓ/s` (long edge over short edge).

| `ℓ/s` | `k` | `k1` |
|---|---|---|
| > 2.0 | 0.500 | 0.025 * |
| 2.0 | 0.495 | 0.028 |
| 1.9 | 0.493 | 0.027 |
| 1.8 | 0.491 | 0.027 |
| 1.7 | 0.487 | 0.026 |
| 1.6 | 0.482 | 0.025 |
| 1.5 | 0.474 | 0.024 |
| 1.4 | 0.462 | 0.023 |
| 1.3 | 0.443 | 0.021 |
| 1.2 | 0.414 | 0.019 |
| 1.1 | 0.370 | 0.017 |
| 1.0 | 0.308 | 0.014 |

\* **The `>2.0` row reads `0.025` in the OCR while the `2.0` row reads `0.028`
and `1.6` also reads `0.025`. A coefficient that is NOT monotone in aspect ratio
is almost certainly an OCR error in the `>2.0` row (the closed forms below both
asymptote upward), but IT IS NOT CORRECTED HERE.** Flagged for image check.

Closed forms, given in the table's own notes **[GROUPING INFERRED — exponents
partly lost; the printed fragments are `k (1 + 0.623 (s/ℓ)^5)` and
`0.028 k1 (1 + 1.056 (s/ℓ)^5)`]**:
```
k  = 0.500 / (1 + 0.623 * (s/ℓ)^5)
k1 = 0.028 / (1 + 1.056 * (s/ℓ)^5)
```
Check against the table: at `s/ℓ = 1` (square), `k = 0.5/1.623 = 0.3081` vs
tabulated **0.308** ✓, and `k1 = 0.028/2.056 = 0.01362` vs tabulated **0.014** ✓.
At `ℓ/s = 1.5`, `s/ℓ = 0.6667`, `k = 0.5/(1+0.623·0.1317) = 0.4602` vs tabulated
0.474 — a 3% miss, so **the exponent 5 reproduces the square-panel value exactly
but not the mid-range**. The closed form is therefore NOT confirmed; use the
TABLE. Recorded because the square-panel agreement to 4 significant figures is
strong evidence the numerator constants and the `(s/ℓ)^n` shape were read right.

Note in TABLE 7.3: **values of `k` below 0.5 and `k1` below 0.028 are NOT
applicable to wood construction, and apply to FRP only where BI-DIRECTIONAL
laminates are used.** (I.e. the aspect-ratio benefit is denied to wood and to
uni-directional layups — that is the same idea as ISO's separate treatment, and
it is a real design rule, not a rounding.)

#### ORY TABLE 7.1 — Design heads for plating **[LEGIBLE]**

**Basic head:**
```
h = 3.0*d + 0.14*L + 1.62        m        (= 3.0d + 0.14L + 5.30 ft)
```
- `d` = draft per 2.7, **except that for yachts with `L > 24 m` (80 ft), `d` is
  not to be taken less than `0.048 L + 0.091` m** (`0.048L + 0.30` ft)
- `ff` = LOCAL FREEBOARD at the location considered = distance above the maximum
  estimated displacement waterline to the centre of the panel/internal
- Shell heads BETWEEN the tabulated longitudinal stations are obtained by
  **interpolation**

| Location | Design head |
|---|---|
| **Shell BELOW `d + 0.15` m** (measured vertically from the underside of the canoe hull at its lowest point) | |
| — at forward end of `Lwl` | `0.80 h` |
| — at `0.05 Lwl` aft of fore end | `1.20 h` |
| — at `0.35 Lwl` aft of fore end | `1.20 h` |
| — at aft end of `Lwl` | `0.70 h` |
| **Shell ABOVE `d + 0.15` m** | |
| — at forward end of `Lwl` | `0.70 (h - d - ff)` |
| — at `0.05 Lwl` aft of fore end | `1.08 (h - d - ff)` |
| — at `0.35 Lwl` aft of fore end | `1.08 (h - d - ff)` |
| — at aft end of `Lwl` | `0.63 (h - d - ff)` |
| Main weather deck, cockpit, cabin house FRONT | `0.04 L + 1.83` m |
| Cabin house top, sides and end | `1.98` m, but not less than `1.98 L/24` m |
| Watertight or structural bulkhead | distance from lower edge of bulkhead to main weather deck at centreline, **not less than 1.52 m** |
| Tank boundary | distance to top of tank overflow, **not less than 1.52 m** |

**This is the single most reusable thing in the file.** The longitudinal
distribution is explicit and simple: **a flat 1.20× plateau of the basic head
from 0.05 to 0.35 Lwl, falling to 0.80× at the bow and 0.70× at the stern**, and
the topsides carry 0.70/1.08/1.08/0.63 of the head measured above the waterline.
It is directly comparable to ISO 12215-5's longitudinal pressure distribution
factor `k_L` and to its `k_AR` area reduction, and it is FREE.

**Bottom shell in way of the ballast keel** (FIGURES 7.1, 7.2, which are
diagrams): the reinforced-shell region uses **`1.8 × the Table 7.1 design
head`**, over an extent shown on the figures (a band around the keel, dimensions
given on the figure as `0.25 H` — **the figures did not extract legibly and the
extent is NOT recorded here**).

#### ORY TABLE 7.4 — design-head reduction factor `F`, SHELL plating **[LEGIBLE for the table; header formula partly lost]**

`F` is tabulated against a parameter the OCR renders as
`Cf = (s - 254) / (0.65 L + 22)` in metric — **[GROUPING INFERRED; the printed
fragments are `s - 254`, `0.65L + 22` and, in the internals version of the same
table (TABLE 8.1b), `(ℓ - 0.254)/(0.0542 L + 0.559)`]**. `s` is **not to be
taken greater than 1270 mm (50 in.)**.

| `Cf` | `F` |
|---|---|
| >= 1.0 | 0.25 |
| 0.9 | 0.28 |
| 0.8 | 0.32 |
| 0.7 | 0.36 |
| 0.6 | 0.42 |
| 0.5 | 0.49 |
| 0.4 | 0.57 |
| 0.3 | 0.67 |
| 0.2 | 0.77 |
| 0.1 | 0.88 |
| 0.05 | 0.94 |
| 0 and negative | 1.00 |

**This is a PANEL-SIZE CAP, and it is the direct analogue of ISO 12215-5's
`k_AR` / design-area reduction: a big panel gets a lower design head.** The
reduction bottoms out at **0.25**, i.e. a large panel is designed to a quarter
of the basic head. Note the reduction is driven by the SPACING `s` normalised by
a length-dependent scale, not by area.

#### ORY TABLE 7.5 — `F` and `Fc`, DECK plating **[LEGIBLE]**
```
F = Fc = 1.0                    where s <= 254 mm
F = Fc = 1.102 - 0.0004 * s     (s in mm)
F_min = Fc_min = 0.59
```
(US: `1.102 - 0.0102 s` with `s` in inches, same 0.59 floor.)

#### ORY TABLE 7.2 — DESIGN STRESS `σa` for PLATING — **the allowables table** **[LEGIBLE]**

| Plating | Steel & aluminium | Single-skin FRP | Cold-molded wood laminate | Wood carvel |
|---|---|---|---|---|
| Shell and deck | **0.60 × min ultimate tensile** ¹ | **0.5 × min flexural strength** | **0.5 × modulus of rupture** ³ | **0.4 × modulus of rupture** |
| Watertight bulkhead | **0.75 × min yield** ² | 0.5 × min flexural | 0.5 × MOR ³ | 0.4 × MOR |
| Tank bulkhead | **0.75 × min yield** ² | 0.5 × min flexural | 0.5 × MOR ³ | 0.4 × MOR |

1. For aluminium the min ultimate tensile is for the **WELDED** condition.
2. For aluminium the min yield is for the **UNWELDED** condition at 0.2% offset.
3. **For cold-molded wood laminate the modulus of rupture is to be taken as 22%
   of the values in TABLE 4.4.** Where MOR is instead determined by sample
   testing, the modulus of elasticity must also be determined and the thickness
   must ALSO satisfy 7.3.1 equation (b) (the stiffness check).

**Read that last one twice: 0.5 × (0.22 × MOR) = 0.11 × the clear-wood modulus
of rupture.** That is an order-of-magnitude-relevant knock-down and it is the
kind of number this project would otherwise have guessed.

#### ORY TABLE 8.2 — DESIGN STRESS `σa` for INTERNALS (stiffeners) **[LEGIBLE]**

| Internal | Steel & Al ¹ | Reinforced plastic | Non-laminated wood ³ | Laminated wood ²,³ |
|---|---|---|---|---|
| Deck beam, deck longitudinal, transverse frame, shell longitudinal, web frame, floor, stringer | 0.5 × min ultimate tensile | **0.5 × min ultimate strength** ⁴ | 0.375 × MOR | 0.42 × MOR |
| Watertight bulkhead stiffener | 0.5 × min ultimate tensile | 0.5 × min ultimate ⁴ | 0.375 × MOR | 0.42 × MOR |
| Tank bulkhead stiffener | **0.32 × min ultimate tensile** | **0.32 × min ultimate** ⁴ | 0.375 × MOR | 0.42 × MOR |

1. Aluminium min ultimate is the **as-welded** value.
2. To count as a laminated frame, **the grain must follow the shape of the member**.
3. Design stresses are for construction **with the grain parallel to the bending
   stress**. For cold-molded wood laminate the design stress *to the plating* is
   TABLE 7.2's, not this table's.
4. **"To the OUTER surface of shell/deck/bulkhead use ULTIMATE TENSILE strength;
   to the INNER surface of the crown or inner edge of the internal use ULTIMATE
   COMPRESSIVE strength."** — i.e. the stiffener is checked on BOTH fibres
   against DIFFERENT material strengths. This is a real asymmetry our code would
   not get for free.

Note the deliberate inversion versus plating: **stiffeners are allowed 0.5 of
ULTIMATE for FRP (vs 0.5 of FLEXURAL for plating), and TANK bulkhead stiffeners
drop to 0.32** — the tank case is the governing one for stiffeners while for
plating the tank case was the same as everything else.

#### ORY 8.1.3 — INTERNALS: required section modulus and moment of inertia

**[GROUPING INFERRED — the OCR gives `SM = C h s ℓ²/σa + SM_k` with the fraction
bar and the `ℓ²` lost; the constants, symbols and the additive `SM_k` term are
all legible]**
```
SM = C * h * s * ℓ^2 / σa  +  SM_k        cm³
```
`C` (SI / metric-kgf / ft-in):

| Member | C (SI) | C (metric) | C (ft-in) |
|---|---|---|---|
| Floors at centreline | **1800** | 183 | 141 |
| Floors at the connection to transverse frames; girders, stringers, transverse frames, shell longitudinals, deck beams, deck longitudinals | **817** | 83.3 | 64 |
| Bulkhead stiffeners | **619** | 63.1 | 48.6 |

- `h` = design head, m, from TABLE 8.1a
- `ℓ` = for floors, the **chord length** between support points of the transverse
  side frame *or* the floor, **whichever is greater**; for transverse side
  frames, the chord between support points; for girders/stringers/longitudinal
  frames/beams/bulkhead stiffeners, the length between support points
- `s` = spacing, m; **for floors in way of side frames, the GREATER of the floor
  or side-frame spacing**; **for girders and transverse web rings it is the MEAN
  WIDTH of shell or deck supported**
- `σa` = design stress, TABLE 8.2
- `SM_k` = required INCREASE in section modulus for floors and frames in way of
  the ballast keel; **`SM_k = 0` clear of the ballast keel**. In way of the keel
  the OCR retains only `N`, `W_k`, the lever and `n`:
  - `N` = **1.00 at centreline, reducing LINEARLY to 0.5 at ¼(?) of the girth
    from centreline to gunwale, and not less than 0.5 from there to the gunwale**
    *(the fraction of girth is printed as `V,` — OCR-illegible; **NOT RECORDED**)*
  - `W_k` = weight of the ballast keel, N
  - lever = vertical distance from mid-depth of the floor at centreline to the
    CG of the ballast keel, m
  - `n` = number of floors in way of the keel, **recommended not less than three**
  - **The `SM_k` equation itself did not survive OCR and is NOT reproduced.**

Additionally, **for reinforced-plastic construction only**, a moment-of-inertia
requirement **[GROUPING INFERRED — the OCR retains only `I = ... / 1000 E` and
the constants]**:
```
I = C1 * h * s * ℓ^? / (1000 * E)         cm⁴
```
| Member | C1 (SI) | C1 (metric) | C1 (ft-in) |
|---|---|---|---|
| Floors at centreline | **562** | 57.3 | 5.32 |
| Floors at frame connections; girders, stringers, transverse frames, shell longitudinals, deck beams, deck longitudinals | **255** | 26.0 | 2.42 |

**The exponent on `ℓ` is NOT recovered** (a stiffness criterion of this shape is
normally `ℓ³` or `ℓ⁴`; both are plausible and neither was read). **DO NOT CODE
THIS without an image check.**

`E` here (per TABLE 8.1b's note) is the modulus used to compute the moment of
inertia of the COMBINED shell-plus-internal; where shell and internal are the
same laminate, **`E` may be taken as the MEAN of the tensile and compressive
moduli**.

In way of the ballast keel, `I` is to be increased **in proportion to the
increase in required section modulus**, with `SM_k` obtained using `N = 0.50`.

Also: with transverse framing, a floor's section modulus is **not to be less
than that required for the frame it attaches to**.

#### ORY TABLE 8.1a / 8.1b — design heads for internals **[LEGIBLE]**

| Internal | Design head |
|---|---|
| Shell frames, longitudinals, stringers, girders, transverse webs, floors | `F ×` the TABLE 7.1 **shell plating** head **at the MID-LENGTH location of the internal** |
| Deck/cockpit/cabin-house beams, longitudinals, transverse webs, girders | `F ×` the TABLE 7.1 deck/cabin-house/cockpit head |
| Bulkhead stiffeners | the TABLE 7.1 head (no `F`) |

`F` for SHELL internals uses the same 12-row ladder as TABLE 7.4 (1.00 down to
0.25) but driven by the SPAN `ℓ`, not the spacing:
`Cf = (ℓ - 0.254)/(0.0542 L + 0.559)` in metric **[GROUPING INFERRED]**, with
`F = 1.00` when `ℓ <= 0.254 m`.

`F` for MAIN WEATHER DECK / COCKPIT / CABIN HOUSE internals **[LEGIBLE]**:
```
F = 0.33                    for ℓ >= 1.93 m
F = 1.102 - 0.48 * ℓ        for 0.254 m < ℓ <= 1.93 m     (ℓ in m)
F = 1.0                     for ℓ <= 0.254 m
```
*(Check: at ℓ = 1.93, `1.102 - 0.48·1.93 = 0.176`, which does NOT meet 0.33 —
so either the 0.48 coefficient or the 1.93 breakpoint is misread. **Flagged;
this one is internally inconsistent as extracted and must not be coded.**)*

#### ORY 7.3.2 — SANDWICH CONSTRUCTION — skins, core, and buckling

Sandwich is specified as **required section modulus and moment of inertia of the
SKINS about the sandwich neutral axis, per 1 cm width**, derived from the
single-skin thickness the same panel would have needed:

**[GROUPING INFERRED — fraction bars and exponents lost; constants and symbols
legible, and the SI/US pairs cross-check exactly at the 100:1 unit ratio]**
```
SM_o = t_a^2 * F / (600 * T)        cm³ per cm width   (US: t_a² F/(6 T) in³/in)
SM_i = t_a^2 * F / (600 * C)        cm³ per cm width   (US: t_a² F/(6 C) in³/in)
I    = t_b^3 * E / (5060 * E_R)     cm⁴ per cm width   (US: t_b³ E/(5.06 E_R))
```
- `t_a` = required SINGLE-SKIN thickness from **equation 7.3.1(a)** (strength)
- `t_b` = required single-skin thickness from **equation 7.3.1(b)** (stiffness)
- `F` = the minimum FLEXURAL strength that was used in TABLE 7.2 to get `σa` for
  equation 7.3.1(a)
- `T` = minimum TENSILE strength of the **OUTER** skin
- `C` = minimum COMPRESSIVE strength of the **INNER** skin
- `E` = the minimum flexural modulus used in equation 7.3.1(b)
- `E_R = 0.5 * (E_T + E_C)` where `E_T` = min tensile modulus of the **inner**
  skin and `E_C` = min compressive modulus of the **outer** skin
  *(the OCR's skin/modulus pairing here is partly mangled and the `inner`/`outer`
  attribution on `E_T`/`E_C` is the printed one as extracted — flagged)*

**The design logic is elegant and directly reusable: size the sandwich so its
skins deliver the same bending capacity and the same bending stiffness the
equivalent single skin would have had.** That gives us a free, physically
motivated bridge between our single-skin and sandwich paths.

Rules attached to it:
- Outer and inner skin tensile strengths are in general to be **approximately
  the same**; likewise the compressive strengths. Different skins get special
  consideration.
- Skins are in general to be **bi-directional laminates**.
- **Single-skin laminate is to be used for the bottom shell in way of the keel**,
  thickness in general **not less than 75% of the overall thickness of the
  adjacent sandwich shell** (8.1.2b) — note 7.3.2 states this same requirement
  as **not less than the overall thickness**; **the two clauses as extracted
  disagree (75% vs 100%) and the disagreement is recorded, not resolved.**
- Single-skin laminate for the deck locally in way of the mast.
- Where both skins are unusually thin, hull-girder strength is to be considered.

##### CORE THICKNESS — core shear **[GROUPING INFERRED — badly mangled OCR]**

The printed equation involves `d_o`, `d_c`, a factor `2`, and the product
`a · v · F_c · h · s / σd`. The dimensionally consistent reading is:
```
(d_o + d_c) / 2  =  a * v * F_c * h * s / σd          mm
```
- `d_o` = overall thickness of the sandwich, mm
- `d_c` = thickness of the core, mm
- `v` = panel aspect-ratio coefficient, **TABLE 7.6** (below)
- `F_c` = design-head reduction factor for shell plating, **TABLE 7.7**; for
  decks, TABLE 7.5
- `h` = design head per 7.1; `s` = spacing per 7.3.1
- `a` = **0.01 (SI)**, 0.001 (metric), 0.44 (ft-in) — the same head-to-pressure
  constant as `p = 0.01 F h`
- **`σd` = design stress = 0.5 × the minimum ULTIMATE SHEAR STRENGTH of the core
  material (see 4.11).** **[LEGIBLE — this is the answer to "what fraction of
  ultimate is allowed for core shear": HALF.]**

Honeycomb cores: cell size, thickness and the specified minimum shear strength
**in the direction of the two principal axes** must be submitted, structural
plans must show the direction of each principal axis relative to the yacht, and
required honeycomb core thickness gets **special consideration** (i.e. the
formula above is not accepted as sufficient for honeycomb).

##### TABLE 7.6 — aspect-ratio coefficient `v` for the core equation **[LEGIBLE]**

| `ℓ/s` | `v` |
|---|---|
| > 2.0 | 0.500 |
| 1.9 | 0.499 |
| 1.8 | 0.499 |
| 1.7 | 0.494 |
| 1.6 | 0.490 |
| 1.5 | 0.484 |
| 1.4 | 0.478 |
| 1.3 | 0.466 |
| 1.2 | 0.455 |
| 1.1 | 0.437 |
| 1.0 | 0.420 |

*(Note how much FLATTER this is than `k` — shear load sharing barely benefits
from aspect ratio, 0.420 → 0.500, where bending `k` runs 0.308 → 0.500. That
distinction is physically right and worth keeping.)*

##### TABLE 7.7 — `Fc` for shell plating, core equation **[LEGIBLE]**
```
Fc = 1.017 - 0.00059 * s                    (s in mm)
Fc_min = 0.40                for L <= 24.4 m
Fc_min = 0.40 * L / 24.4     for L  > 24.4 m
```
(US: `Fc = 1.017 - 0.015 s` with `s` in inches; floor `0.40` for `L <= 80 ft`,
`0.40 L/80` above.)

##### SKIN WRINKLING / BUCKLING **[GROUPING INFERRED — radical index lost]**

"The skin buckling stress, `σcr`, given by the following equation, is not to be
less than `1.0 C` in either skin."
```
σcr = 0.60 * ( E_cs * E_cc * G_c )^(1/3)
```
- `E_cs` = in-plane compressive modulus of the SKIN
- `E_cc` = compressive modulus of the CORE, **perpendicular to the skins**
- `G_c` = shear modulus of the core, **the LESSER of perpendicular or parallel
  to the skins**
- `C` = minimum compressive strength of the skin

**The cube-root exponent is the classical Hoff/Plantema wrinkling form and is
INFERRED — the OCR shows only a radical over the triple product.** The
coefficient **0.60** and the acceptance criterion **`σcr >= 1.0 C`** are
LEGIBLE. Note what the criterion means: **the sandwich must wrinkle at or above
the skin's own compressive failure stress — wrinkling must not be the governing
mode at all.** That is a cleaner, more conservative statement than a wrinkling
safety factor, and it is free.

##### TABLE 7.8 — MINIMUM OUTER-SKIN REINFORCEMENT WEIGHT (sandwich shell) **[LEGIBLE]**

`W_s` = minimum required weight of reinforcement, g/m². `L_1` = scantling length
`L`, **but not to be taken as less than 9.15 m (30 ft)**.

| Reinforcement / resin | `W_s`, g/m² |
|---|---|
| **E-glass** with polyester or vinylester | `105 * L_1 + 138` |
| **S or R-glass** with epoxy or vinylester | `90.2 * L_1 + 125` |
| **Kevlar (aramid)** with epoxy or vinylester | `59.0 * L_1 + 80.2` |
| **High-strength CARBON fibre** with epoxy or vinylester | `73.8 * L_1 + 100` |

Notes as printed:
1. Thicknesses apply where **chopped-strand-mat weight is less than 50% of the
   total laminate weight**.
2. For **aramid**, `W_s` is not to be less than **1450 g/m² for bottom shell**
   nor **1250 g/m² for topsides** on Whitbread 60 yachts.
3. **For carbon: the ratio of minimum ultimate tensile strength to tensile
   modulus is to be not less than 0.014.** **[LEGIBLE]**

**This is the carbon-fibre answer, and it is not a knock-down factor — it is a
STRAIN FLOOR.** `T/E >= 0.014` is a failure strain of **1.4%**, which excludes
high-modulus / low-strain carbon from the outer skin of a shell sandwich. It is
the only carbon-specific allowable found in any free class document so far, and
it is a *materials admissibility* rule, not a stress reduction — exactly the
kind of rule this project's `admissibility.py` is shaped to hold.

**Minimum PLY COUNT in the outer skin of sandwich shell plating** (plies of at
least 175 g/m²; a quadraxial ply of >= 600 g/m² counts as TWO plies)
**[LEGIBLE]**:

| `L` | min plies |
|---|---|
| `L < 9.15 m` | **2** |
| `9.15 <= L < 15.2 m` | **3** |
| `15.2 <= L < 21.4 m` | **4** |
| `21.4 <= L <= 24.4 m` | **5** |

**Our entire 5–15 m band is covered by the first two rows: 2 plies below 9.15 m,
3 plies from 9.15 to 15.2 m.** This is a hard, free, in-scope minimum.

Panels with cores **denser than 80 kg/m³ (5 lb/ft³)**, hybrid outer skins, and
fibres not in TABLE 7.8 all get "special consideration" — i.e. the table's
validity band tops out at 80 kg/m³ core density.

#### ORY 7.5 — WOOD, single-skin CARVEL **[GROUPING INFERRED — heavily mangled]**

Two equations are printed, with the recoverable fragments
`t = 1.09 (1.42 - 1.13 sqrt(L?)) s sqrt(0.01 h / σa)` and
`t = 1.09 (1.42 - 0.84 ...) s ...` plus a `0.44 h / σa` US-unit fragment.
**The interior of the bracket and the second equation are NOT recoverable from
this OCR and are NOT reproduced.** What IS legible: there are TWO equations, the
prefactor is **1.09**, the bracket has the form `(1.42 - k*something)` with
`k = 1.13` in the first and `0.84` in the second, `L` per 2.1 and `s`, `h`, `σa`
per 7.1. **DO NOT CODE — image check required.**

**7.5.2 Multi-skin carvel** (two or more glued skins): "**special consideration
will be given**" — i.e. **NO FORMULA IS PROVIDED**. NOT FOUND.

#### ORY Section 4 — materials, allowables and the wood/plywood answers

**4.5.4 — basic FRP laminate** (the laminate the whole guide is calibrated on):
alternate plies of **glass mat and woven roving**, general-purpose polyester,
hand/contact layup, **minimum glass content approximately 35% by weight**.

**TABLE 4.3 — BASIC LAMINATE PROPERTIES** (warp direction unless noted)
**[LEGIBLE]**:

| Property | N/mm² |
|---|---|
| Flexural strength, `F` | **172** |
| Flexural modulus, `E_F` | **7580** |
| Tensile strength, `T` | **124** |
| Tensile modulus, `E_T` | **6890** |
| Compressive strength, `C` | **117** |
| Compressive modulus, `E_C` | **6890** |
| Shear strength perpendicular to warp, `S_perp` | **76** |
| Shear strength parallel to warp, `S_par` | **62** |
| Shear modulus parallel to warp, `E_S` | **3100** |
| Interlaminar shear strength | **17.3** |

*(This is a complete, free, self-consistent property set for a 35%-glass
mat/WR polyester laminate — usable as a default and as a sanity bound on any
laminate our materials path proposes.)*

**4.5.4d — LAMINATE THICKNESS FROM AREAL WEIGHT** **[LEGIBLE]**, the rule that
converts a layup schedule into a thickness:
- cured resin-and-**MAT** plies: **0.25 mm per 100 g/m² of mat**
- cured resin-and-**WOVEN ROVING** plies: **0.12 mm per 100 g/m² of WR**
- These are AVERAGES for design; **actual thickness may vary ±15%** without
  being resin-rich or resin-dry.
- **Gel coats, and skin coats of mat or cloth under 30 g/m², are NON-STRUCTURAL
  and are excluded from scantling calculations** — and are to be deducted from a
  measured thickness to get the effective thickness.

**4.5.4f — UNI-DIRECTIONAL LAMINATE BALANCE RULE** **[LEGIBLE]** — minimum ratio
of verified fill-direction strength to warp-direction strength:

| Member | fill/warp |
|---|---|
| Panel, aspect ratio 1.0 | **0.80** |
| Panel, aspect ratio >= 2.0 | **0.61** |
| Stiffening member | **0.25** |

Interpolate for aspect ratios between 1.0 and 2.0. Also: `E_F/F`, `E_T/T` and
`E_C/C` in the FILL direction are not to exceed the same ratios in the warp
direction.

**4.11 — CORE MATERIALS: density bands and minimum ultimate shear strength**
**[LEGIBLE]**:

| Core | Density kg/m³ | Min ultimate shear, N/mm² |
|---|---|---|
| Balsa, end-grain ¹ | 128 | **1.9** |
| Balsa, end-grain ¹ | 144 | **2.1** |
| PVC, cross-linked | 80 | **1.0 to 1.2** |
| PVC, cross-linked | 100 | **1.4 to 1.5** |
| PVC, linear | 80–90 | **1.2** |

1. Values are for **Ecuadorian** balsa.
- **Where test data is not available for cross-linked PVC, the LOWER value of
  the range is to be used.**
- Different verified minimum shear strengths may be used if supported by
  submitted test data.
- Other core materials: special consideration.

*(Combined with `σd = 0.5 × ultimate shear`, this gives allowable core shear
directly: 80 kg/m³ XPVC → **0.50 N/mm²** allowable, 100 kg/m³ → **0.70 N/mm²**,
128 kg/m³ balsa → **0.95 N/mm²**. Those are usable numbers with a clause
reference, and they are free.)*

**4.7.4 — ENCAPSULATION / rot-and-moisture policy** **[LEGIBLE]**, which is this
guide's answer on wood durability:
- **Softwoods encapsulated in FRP are effective structural material ABOVE the
  waterline. Below the waterline it is RECOMMENDED they not be used, and where
  used they are to be considered INEFFECTIVE, non-structural core.**
- **With the exception of balsa, hardwoods are NOT to be used as core materials.**
- **Encapsulated balsa and plastic foam are to be considered INEFFECTIVE in
  resisting bending or deflection.**
- 4.7.1: all wood to be best quality, properly seasoned, clear, free of
  strength-affecting defects, grain suitable. All wood except resin-coated
  cold-molded laminate **suggested** to be preservative-treated.
- 4.7.2: preservatives to be of an approved type, must not harm coatings, and
  wood encapsulated in FRP or used in cold-molded laminate **must not be treated
  with a preservative that prevents resin adhesion**.
- 4.7.3: glues to be of a **waterproof type** with necessary durability and
  strength.

**There is no numerical moisture or rot allowance in this guide.** The wood
strength table is stated as "**adjusted for 12% moisture content**" and the
durability policy is the structural/non-structural switch above. **NOT FOUND:
any percentage knock-down for moisture or rot.**

**4.9 — PLYWOOD, in full: "Plywood is to be of marine quality and manufactured
in accordance with a recognized national standard."** That is the ENTIRE
plywood clause. **The ORY guide gives NO plywood scantling formula, NO plywood
allowable stress, NO approved species list and NO minimum thickness.** Plywood
appears nowhere else in the document. **NOT FOUND — and this is the single
biggest gap in the best free source.**

**TABLE 4.4 — PROPERTIES OF VARIOUS WOODS** **[LEGIBLE, though the OCR mangles
several exponents in the modulus-of-elasticity column]** — values adjusted for
**12% moisture content**. Modulus of rupture (MOR) and specific gravity, the two
columns the scantling rules actually consume:

| Species | SG | MOR, N/mm² |
|---|---|---|
| Ash, White | 0.60 | 106 |
| Cedar, Alaska | 0.44 | 76 |
| Cedar, Western Red | 0.32 | 52 |
| Elm, American | 0.50 | 81 |
| Elm, British | 0.56 | 41 |
| Elm, Rock | 0.63 | 102 |
| Fir, Douglas | 0.48 | 86 |
| Mahogany, Central/South America | — | 80 |
| Oak, English | 0.70 | 66 |
| Oak, White | 0.68 | 105 |
| Pine, Longleaf Yellow | 0.59 | 100 |
| Pine, Oregon | 0.48 | 86 |
| Pine, Western | 0.38 | 67 |
| Pine, White | 0.35 | 59 |
| Spruce, Sitka | 0.40 | 70 |
| Teak | 0.63 | 88 |

**COLUMN-ORDER WARNING.** The table header as extracted reads "Bending Tensile
Strength Perpendicular to Grain / Compressive Strength Parallel to Grain /
Modulus of Rupture / Modulus of Elasticity", but the numeric columns do not line
up with that header in the OCR — the first numeric column (106, 76, 52, …) is
the one that behaves like a **modulus of rupture** (Sitka spruce 70 N/mm²,
Douglas fir 86 N/mm² are textbook MOR values, whereas perpendicular-to-grain
tensile strength for these species is 2–6 N/mm², which is what the *later*
column showing 6.5 / 2.5 / 1.5 / 4.6 actually contains). **The MOR column above
is therefore the FIRST numeric column, assigned by physical plausibility, NOT by
reading the header alignment.** An image check is owed before these feed a
scantling calculation. The assignment is stated so it can be refuted.

Combined with TABLE 7.2, the **allowable bending stress for wood carvel** is
`0.4 × MOR` — e.g. Sitka spruce **28 N/mm²**, Douglas fir **34.4 N/mm²** — and
for **cold-molded wood laminate** it is `0.5 × 0.22 × MOR` = `0.11 × MOR` —
Sitka spruce **7.7 N/mm²**, Douglas fir **9.5 N/mm²**.

#### ORY — other numbers worth keeping

- **6.x / 7.x minimum bulkhead thickness: 3 mm (0.125 in.)** minimum thickness
  appears at p.22 of the PDF for glassed-in structural members *(context partly
  OCR-mangled — recorded as a lead, NOT as a confirmed clause)*.
- **Cold-molded wood laminate: at least THREE layers of wood**, each of
  thickness generally not greater than **⅓ of the laminate thickness or 4.5 mm**,
  whichever is less *(p.10/p.20; the fraction is OCR-rendered as `V,` and read as
  ⅓ from the repeated "V," → "1/3" pattern elsewhere in the scan — **flagged**)*.
- Laminate thickness transitions are to be **tapered over a length not less than
  three times the thickness** of the thicker laminate.

---

### ABS.1b — Guide for Building and Classing Yachts, 2021, Part 3 — THE SCANTLING CLAUSES

Same PDF and URL as ABS.1. **READ**, and unlike ORY-1994 this one has a **CLEAN
TEXT LAYER** — the equations below are **[LEGIBLE]** unless marked otherwise.
**This is the modern, machine-readable descendant of the ORY rules, and where
the two disagree this one is the later thinking.** Same scope caveat as ABS.1
(a big-yacht guide), but the FORM of the rules is size-independent.

The guide gives the SAME scantling structure twice, once per load regime:
- **3-2-3** Displacement yachts — driven by design HEAD `h` (m), TABLE 3-2-2/1.1
- **3-2-4** Semi-planing and planing yachts — driven by design PRESSURE `p`
  (kN/m²), 3-2-2/3
- **3-2-5** Sailing yachts — not extracted in detail; it carries its own copies
  of the same tables (a third "Core Shear Design Strength" table appears at PDF
  page 130).

**For a 5–15 m planing craft, 3-2-4 is the section to read.** It is transcribed
in full below; 3-2-3's differences are noted where they matter.

#### 3-2-4/5.1.3(a) — SINGLE-SKIN FRP plating, isotropic-ish laminate

Thickness is **the GREATEST** of the applicable equations:

```
(i)   all plating:              t = s * c * sqrt( p * k / (1000 * σa) )          mm
(ii)  all plating:              t = s * c * ( p * k1 / (1000 * k2 * EF) )^(1/3)  mm
(iii) strength deck and shell:  t = k3 * (C1 + 0.26*L) * sqrt(q1)               mm
(iv)  strength deck and bottom shell:
                                t = (s/kb) * sqrt( 0.6*σuc/Ec * SMR/SMA )        mm
```
- `s` = stiffener spacing, mm — **always the LESSER dimension of the unsupported
  panel**
- `c` = curvature factor `= (1 - A/s)`, **not less than 0.70**; `A` = the
  perpendicular offset from the chord `s` to the highest point of the arc
- `p` = design pressure, kN/m², from 3-2-2/3
- `k`, `k1` = aspect-ratio coefficients, TABLE 5 below
- `k2` = **0.010 bottom plating · 0.015 side plating · 0.025 superstructure and
  deckhouse fronts · 0.010 other plating** — the deflection-limit knob
- `σa` = design stress, TABLE 4 below
- `EF` = flexural modulus parallel to `s`
- `q1 = 170/F` (SI), `F` = min flexural strength
- `C1`, `k3` = service/location factors, TABLE 6 below
- `kb` = **2.5 longitudinal framing · 2.5 transverse framing at aspect ratio 1.0
  · 1.0 transverse framing at aspect ratio 2.0–4.0**
- `σuc` = min compressive strength; `Ec` = compressive modulus
- `SMR` = required hull-girder section modulus (3-2-1); `SMA` = proposed midship
  section modulus

Equation (i) is a **strength** check, (ii) a **stiffness/deflection** check,
(iii) a **minimum thickness** floor scaling with `L`, and (iv) a **hull-girder
buckling** check. **The same four-way structure ISO 12215-5 uses.**

**3-2-3 (displacement) equivalents**, for comparison — same shape, head-driven:
```
(i)   t = 0.15  * s * c * sqrt(k * h * q1)          mm
(ii)  t = 0.0518* s * c * (k1 * h * q2)^(1/3)       mm
(iii) t = k3 * (C1 + 0.26*L) * sqrt(q1)             mm
(iv)  (as above, applies for L > 30.5 m)
```
with `q1 = 170/F`, `q2 = 7580/EF` (SI). Note `q2`'s numerator **7580 N/mm² is
exactly the ABS basic-laminate flexural modulus** and `q1`'s **170 N/mm² is
essentially the basic-laminate flexural strength (172 in ORY TABLE 4.3)** — i.e.
`q1` and `q2` are RATIOS TO THE BASIC LAMINATE. That is the mechanism by which
these rules generalise off their calibration laminate, and it is worth copying.

#### 3-2-4/5.1.3(b) — ORTHOTROPIC single skin (different 0°/90° properties)

Where strength is LESS or stiffness GREATER perpendicular to `s`, the thickness
must ALSO satisfy, whichever is greater:
```
(i)  t = s * c * sqrt( p * ks / (1000 * σas) )                        mm
(ii) t = s * c * sqrt( p * kℓ / (1000 * σaℓ) ) * (Eℓ/Es)^(1/4)        mm
```
with `ks`, `kℓ` from TABLE 7, `σas`/`σaℓ` the TABLE 4 design stresses based on
the strength parallel/perpendicular to `s`, and `Es`/`Eℓ` the flexural moduli
parallel/perpendicular to `s`.

**The `(Eℓ/Es)^(1/4)` orthotropy factor is a genuinely useful free result** — it
is how a class society converts a directional layup into an equivalent isotropic
panel, and it is exactly the kind of thing a carbon/uni layup path needs.

#### 3-2-4/5.1.3(a) TABLE 4 — DESIGN STRESS `σa` for FRP **[LEGIBLE]**

| Location | `σa` |
|---|---|
| Bottom shell | **0.33 σu** |
| Side shell | **0.33 σu** |
| Decks | **0.33 σu** |
| Superstructure & deckhouses — fronts, sides, ends, tops | **0.33 σu** |
| Tank bulkheads | **0.33 σu** |
| **Watertight bulkheads** | **0.50 σu** |

and `σu` is defined per case:
- **single-skin laminates: `σu` = minimum FLEXURAL strength**
- **sandwich, shell/deck OUTER skin: `σu` = minimum TENSILE strength**
- **sandwich, shell/deck INNER skin: `σu` = minimum COMPRESSIVE strength**
- **sandwich bulkheads: the LESSER of tensile or compressive strength**
- `σu` is to be **verified from approved test results**.

**This is the single cleanest allowable-stress answer in any free document
found: ONE-THIRD of ultimate for everything wetted or exposed, ONE-HALF for
watertight bulkheads.** Note it does NOT vary by fibre type — carbon gets the
same 0.33 as E-glass. Note also it is **flatly more conservative than
ORY-1994's 0.5 of flexural**, and that the 2021 rule reaches the ULTIMATE
strength in the relevant mode rather than always the flexural one.

#### 3-2-4 TABLE 5 / 3-2-3 TABLE 4 — aspect-ratio coefficients, ISOTROPIC plates **[LEGIBLE]**

| `ℓ/s` | `k` | `k1` |
|---|---|---|
| > 2.0 | 0.500 | 0.028 |
| 2.0 | 0.497 | 0.028 |
| 1.9 | 0.493 * | 0.027 |
| 1.8 | 0.487 | 0.027 |
| 1.7 | 0.479 | 0.026 |
| 1.6 | 0.468 | 0.025 |
| 1.5 | 0.454 | 0.024 |
| 1.4 | 0.436 | 0.024 |
| 1.3 | 0.412 | 0.021 |
| 1.2 | 0.383 | 0.019 |
| 1.1 | 0.348 | 0.017 |
| 1.0 | 0.308 | 0.014 |

\* the 3-2-4 copy prints `1.493` at `ℓ/s = 1.9`; the 3-2-3 copy prints `0.493`.
**A typo in the published guide, not in this transcription — 0.493 is right.**

**This table SETTLES the ORY-1994 ambiguity flagged earlier: `k1` at `>2.0` is
0.028, not 0.025.** ORY's `0.025` was an OCR error, now refuted by an
independent, clean-text ABS source. *(The `k` column also differs slightly
between ORY-1994 and Yachts-2021 in the mid-range — ORY 1.5 → 0.474 vs Yachts
1.5 → 0.454 — so the two editions are NOT the same table. Use one or the other,
not a mixture.)*

#### 3-2-4 TABLE 7 / 3-2-3 TABLE 5 — aspect-ratio coefficients, ORTHOTROPIC plates **[LEGIBLE]**

Entered with `(ℓ/s) * (Es/Eℓ)^(1/4)`:

| `(ℓ/s)(Es/Eℓ)^¼` | `ks` | `kℓ` |
|---|---|---|
| > 2.0 | 0.500 | 0.342 |
| 2.0 | 0.497 | 0.342 |
| 1.9 | 0.493 | 0.342 |
| 1.8 | 0.487 | 0.342 |
| 1.7 | 0.479 | 0.342 |
| 1.6 | 0.468 | 0.342 |
| 1.5 | 0.454 | 0.342 |
| 1.4 | 0.436 | 0.342 |
| 1.3 | 0.412 | 0.338 |
| 1.2 | 0.383 | 0.333 |
| 1.1 | 0.348 | 0.323 |
| 1.0 | 0.308 | 0.308 |

#### 3-2-4 TABLE 6 / 3-2-3 TABLE 3 — service and location factors `C1`, `k3` **[LEGIBLE]**

| Section | `C1` | `k3` bottom shell | `k3` side shell & deck |
|---|---|---|---|
| 3-2-4 (semi-planing/planing) | **3.2 mm** | **1.1** | **1.0** |
| 3-2-3 (displacement) | **3.0 mm** | **1.0** | **0.90** |

Note in both: "**Consideration will be given to values of `C1` and `k3` for
yachts limited to service in relatively sheltered waters.**" — i.e. the SERVICE
AREA knob exists in the minimum-thickness rule but **its value for sheltered
water is NOT published**; it is case-by-case. **NOT FOUND: a numeric sheltered-
water reduction.** That is a real difference from ISO 12215-5, which publishes
category factors A/B/C/D outright.

#### 3-2-4/5.1.4 — SANDWICH laminate

Required section modulus and moment of inertia **per 1 cm width** of panel:
```
SMo = (s*c)^2 * p * k  / (6e5 * σao)              cm³   (outer skin)
SMi = (s*c)^2 * p * k  / (6e5 * σai)              cm³   (inner skin)
I   = (s*c)^3 * p * k1 / (120e5 * k2 * Etc)       cm⁴
```
- `σao`, `σai` = TABLE 4 design stresses for the outer/inner skin, based on the
  skin's strength **parallel to `s`** (recall: outer → tensile, inner →
  compressive)
- `Etc = 0.5 * (Ec + Et)`, `Ec` = mean of the two skins' compressive moduli,
  `Et` = mean of the two skins' tensile moduli
- `k2` as in the single-skin stiffness equation (0.010 bottom, 0.015 side,
  0.025 superstructure fronts, 0.010 other)

Orthotropic case 5.1.4(b) repeats each with `ks` (parallel to `s`) and with
`kℓ * (Eℓ/Es)` (parallel to `ℓ`) — note the orthotropy factor here is
**`Eℓ/Es` to the FIRST power**, not the fourth root used for single-skin
thickness.

**3-2-3 (displacement) equivalents**, head-driven:
```
SMo = SMi = 5.2e-7 * (s*c)^2 * k  * h * q3     cm³,   q3 = 124/σu
I         = 1.1e-8 * (s*c)^3 * k1 * h * q4     cm⁴,   q4 = 7580/ETC
```
(`124 N/mm²` is the ABS basic-laminate TENSILE strength — the same
ratio-to-basic-laminate device as `q1`, `q2`.)

##### 3-2-4/5.1.4(c) — CORE SHEAR **[LEGIBLE]** — the one this project most needs

```
(do + dc) / 2  =  v * p * s / (1000 * τ)          mm
```
- `do` = overall sandwich thickness **excluding gel coat**, mm
- `dc` = core thickness, mm
- `v` = aspect-ratio coefficient, TABLE 9; **where the skins' elastic properties
  differ in the principal axes, `v` is NOT to be taken less than 0.5**
- `s` = **lesser** panel dimension, mm
- `p` = design pressure, kN/m²
- `τ` = design shear stress, TABLE 10

*(The 3-2-3 displacement form is `(do+dc)/2 = k4*v*h*s/τ` with
`k4 = 0.01` SI — identical once `p = 0.01·h` in kN/m². The two sections are
consistent, and this also CONFIRMS the [GROUPING INFERRED] reading of the
ORY-1994 core equation earlier in this file. Good: two independent sources, one
clean, now agree.)*

##### 3-2-4 TABLE 10 / 3-2-3 TABLE 7 — CORE SHEAR DESIGN STRENGTH **[LEGIBLE]**

| Core material | Design shear strength |
|---|---|
| **Balsa wood** | **0.30 τu** |
| **PVC, cross-linked** | **0.40 τu** |
| **PVC, SAN, linear** | **0.50 τu** |
| \* PVC/SAN where **shear elongation exceeds 40%** | **0.55 τu** |

`τu` = minimum core shear strength.

**This is the answer to "what fraction of ultimate is allowed for core shear",
and it is NOT one number — it is graded by the core's DUCTILITY.** Brittle
end-grain balsa gets 0.30; a linear PVC or SAN that can actually yield gets
0.50, rising to 0.55 if it elongates more than 40% in shear. **That is a
genuinely instructive rule and it is free.** *(ORY-1994's flat `0.5 × ultimate
shear` for all cores is the older, cruder version — the 2021 guide supersedes
it and is markedly more conservative on balsa.)*

##### 3-2-4 TABLE 8 — MINIMUM PVC FOAM CORE DENSITY, shell plating **[LEGIBLE]**

Density in kg/m³, with `dc` = core thickness in mm:

| Location | Density | Minimum density |
|---|---|---|
| Bottom forward of 0.4 Lwl, **V >= 25 kts** | `4 * dc` | **120** |
| Bottom forward of 0.4 Lwl, **V < 25 kts** | `4 * dc` | **100** |
| Elsewhere, V >= 25 kts | `3 * dc` | **100** |
| Elsewhere, V < 25 kts | `3 * dc` | **180** ⚠ |
| Side forward of 0.4 Lwl | `2.5 * dc` | **100** |
| Elsewhere | `2.0 * dc` | **180** ⚠ |

⚠ **Two rows read `180 (5.00)` — 180 kg/m³ against 5.00 lb/ft³, and 5.00 lb/ft³
is 80 kg/m³, not 180.** The other rows are internally consistent
(120↔7.5 lb/ft³, 100↔6.25 lb/ft³). **The two `180` entries are almost certainly
`80` in the printed table**, which would also make them the LOWEST densities in
the table, as their "elsewhere / slow" locations imply. **NOT CORRECTED HERE —
flagged for an image check.** This is exactly the "a number declared twice, in
two unit systems, and they disagree" defect this project keeps finding.

The **density-proportional-to-thickness** rule (`ρ >= 4·dc` forward bottom,
`3·dc` elsewhere) is a nice free result: a thicker core must also be a denser
one, which is a **local-impact/indentation** criterion the section-modulus and
shear equations do not capture. **ISO 12215-5 has no direct equivalent.**

##### 3-2-4/5.1.4(d) — SKIN STABILITY (wrinkling) **[LEGIBLE]**

```
σc = 0.6 * ( Es * Ecc * Gcc )^(1/3)
```
"**is in general to be not less than `2.0 σai` and `2.0 σao`**"
- `Es` = compressive modulus of the SKINS, in the 0°/90° in-plane axis
- `Ecc` = compressive modulus of the CORE, perpendicular to the skins
- `Gcc` = core shear modulus, **in the direction parallel to load**

**This CONFIRMS the [GROUPING INFERRED] cube-root reading of the ORY-1994
wrinkling formula — the 2021 text prints the index 3 on the radical
explicitly, and the coefficient 0.6 matches.** Two independent sources now
agree; the ORY inference is upheld.

But note the CRITERION differs. ORY-1994: `σcr >= 1.0 C` (skin ultimate
compressive). Yachts-2021: `σc >= 2.0 σa` where `σa` is the DESIGN stress
(0.33 σu) — i.e. `σc >= 0.66 σu`. **The 2021 rule is LESS demanding
(0.66×ultimate vs 1.0×ultimate).** Recorded because they genuinely differ and a
reader must not average them.

##### 3-2-4/5.1.4(e) — MINIMUM SKIN THICKNESS **[LEGIBLE]**

```
tos = 0.35 * k3 * (C1 + 0.26*L)      mm    (outer skin)
tis = 0.25 * k3 * (C1 + 0.26*L)      mm    (inner skin)
```
with `k3 = 1.2` bottom shell, `1.0` side shell and deck, and **`C1 = 5.7 mm`**
(note: a DIFFERENT `C1` from the single-skin TABLE 6 value of 3.2 mm), `L` in m.

*(The 3-2-3 displacement version is `tos = 0.5 k3 (C1 + 0.26L)`,
`tis = 0.35 k3 (C1 + 0.26L)` using TABLE 3's `C1 = 3.0 mm`.)*

**Worked for our band, planing, bottom shell (`k3 = 1.2`, `C1 = 5.7`):**

| L | `tos` mm | `tis` mm |
|---|---|---|
| 5 m | 2.94 | 2.10 |
| 8 m | 3.27 | 2.34 |
| 12 m | 3.72 | 2.66 |
| 15 m | 4.03 | 2.88 |

**These are directly usable minimum-skin floors for a 5–15 m planing craft, from
a free document, with a clause number.** They extrapolate below the guide's
stated scope, and they are gentle and monotone in `L`, so the extrapolation is
at least well-behaved — but say that it IS an extrapolation.

Also: for sandwich decks covered in wood (teak), **both skins may use the
`tis` minimum, and the wood covering is NOT counted in the sandwich
calculation**; if rigidly bonded, the wood must be shown not to be critically
stressed. If flexibly bonded, no such check.

#### 3-2-4/5.3.3 — FRP INTERNALS (stiffeners): SM, I and SHEAR AREA **[LEGIBLE]**

```
SM = 83.3 * p * s * ℓ^2 / σa            cm³
I  = 260  * p * s * ℓ^3 / (K4 * E)      cm⁴
A  = 7.5  * p * s * ℓ / τ               cm²      (net web area)
```
- `K4` = **0.005 for shell and deep-tank girders, stringers and transverse webs
  · 0.004 for deck girders and transverses · 0.010 for all other members**
- `τ` = design shear stress, **not greater than `0.4 τu`**, where `τu` is the
  **LESSER of the ultimate shear strength in the warp or fill of the WEB
  laminate**
- `E` = tensile or compressive modulus representative of the basic value used in
  the inertia calculation

**A SHEAR-AREA requirement on the stiffener web is a check ISO 12215-5 also
makes, and here it comes with an explicit allowable: 40% of the web's weaker
ultimate shear strength.**

**3-2-3 (displacement) equivalents**, head-driven:
```
SM = 22.91 * c * h * s * ℓ^2 * q3      cm³,     q3 = 124/σu
I  = 34.85 * c * h * s * ℓ^3 * q5      cm⁴,     q5 = 6890/E
```
(`6890 N/mm²` is the ABS basic-laminate tensile/compressive modulus.)

**Stiffener fibre rule (5.3.2):** the laminate's strength PERPENDICULAR to the
direction of the internal is in general **not to be less than 25% of the warp
strength**, except for uni-directional caps in the flange/crown. Same 0.25 floor
as ORY-1994 TABLE 4.5.4f for stiffening members — the two editions agree.

**Buckling (5.3.5):** for both single-skin and sandwich members under in-plane
compression, "**design calculations are to be submitted to show the margin
against buckling failure**" — i.e. **NO FORMULA. NOT FOUND.**

#### 3-2-4/7.3 and 3-2-3/7.3 — WOOD plating, and THE PLYWOOD ANSWER

Cold-molded wood laminate **[LEGIBLE]** — identical in form to ORY 7.1:
```
t = s * c * sqrt( p * k / σa )        mm       (planing, p in kN/m²)
t = s * c * sqrt( p * k / σa )        mm       (displacement, p = 0.01h)
```
with `k` **not less than 0.5** for cold-molded wood laminate unless specially
approved, and `c = (1 - A/s) >= 0.70`.

Single-skin CARVEL **[LEGIBLE — and this RESOLVES the ORY-1994 OCR gap]**:
```
t = 1.09 * ( 4.2 - 1.13 * L^(1/4) ) * s * sqrt( p / σa )      mm
t = 1.09 * ( 4.2 - 0.84 * L^(1/4) ) * s * sqrt( p / σa )      in.   (L in ft)
```
**The ORY-1994 scan's `1.42` was `4.2`, and its illegible bracket interior is
the FOURTH ROOT OF L.** The `1.13`/`0.84` pair that survived OCR in ORY is
confirmed as the SI/US pair. **The ORY 7.5 gap is closed by a clean-text
source.** Note the bracket goes negative for `L > (4.2/1.13)^4 = 191 m`, which
never binds.

Multi-skin carvel (two or more glued skins): "**special consideration**" —
**NO FORMULA, NOT FOUND**, in both 1994 and 2021.

##### TABLE 8 (3-2-3/7.3) — DESIGN STRESSES `σa` for WOOD PLATING **[LEGIBLE]**

| Cold-molded wood laminate | **Plywood construction** | Wood carvel |
|---|---|---|
| **0.5 MOR** ¹ | **0.375 MOR** ² | **0.4 MOR** |

1. For cold-molded wood laminate the **modulus of rupture is to be 22% of the
   tabulated species value**. If MOR is instead sample-tested, the modulus of
   elasticity must also be determined and the stiffness equation must also be
   satisfied.
2. **"Design stress for plywood construction is for the modulus of rupture of
   the wood parallel to the grain, in association with the geometric properties
   of the panel such as area, section modulus and inertia determined using ONLY
   THE PLIES OF WOOD HAVING GRAIN RUNNING PARALLEL TO THE DIRECTION OF LOAD OR
   STRESS."**

**THIS IS THE PLYWOOD RULE, AND IT IS THE MOST VALUABLE SINGLE FIND FOR OUR
PLYWOOD PATH.** It is a complete, free, coherent plywood method:
- allowable bending stress = **0.375 × the species' modulus of rupture parallel
  to grain** (note: the SPECIES MOR, with NO 22% laminate knock-down — that
  knock-down applies to cold-molded laminate only);
- and the panel's section properties are computed from the **parallel plies
  only** — the cross-plies are treated as carrying nothing.
- Together these ARE the classical plywood scantling method, and they let us
  build a plywood check without ISO 12215-5.

**Worked example, 9 mm 5-ply Douglas fir plywood, load parallel to face grain,
plies 1.8 mm each, 3 parallel + 2 cross:** parallel-ply thickness = 5.4 mm, but
the parallel plies are the OUTER and MIDDLE ones, so the effective `I` per unit
width is `(9³ - (5.4³_of_the_cross_layers_positions))/12` — **the arithmetic
depends on the ply STACKING, not just the total parallel thickness, and this
file does not compute it for you.** The rule as written is a section-property
instruction, and our code must implement it as one. Allowable stress:
`0.375 × 86 = 32.3 N/mm²` for Douglas fir.

##### Plywood and cold-molded EFFECTIVE WIDTH of plating (3-1-2/7.5, 7.7) **[LEGIBLE]**

For a stiffener's section modulus, the effective width `w` of attached plating
is the **LESSER of the stiffener spacing and**:
- **plywood plating, or FRP sandwich with a PLYWOOD CORE: `w = 50 t`**
- **cold-molded wood laminate: `w = 25 t`**
- **carvel: the stiffener alone — NO effective plating at all**
- For a stiffener along an OPENING, **half** the above.

*(`t` = thickness of the single-skin plating. FRP single-skin and sandwich have
their own effective-width figures, 3-1-2/7.1 FIGURES 6 and 7, which are GRAPHS
and are NOT transcribed. Steel/aluminium effective width is 3-1-2/7.3.)*

**`w = 50t` for plywood is a hard, free, directly codeable panel-size rule.**

##### 3-2-3/7 TABLE 10 — wood species properties

Referenced repeatedly as the source of MOR for the wood design stresses. **NOT
EXTRACTED in this pass** (it sits inside the displacement-yachts wood section).
The ORY-1994 TABLE 4.4 transcribed earlier is the 1994 ancestor of it and is
almost certainly the same species list. **Owed work.**

##### 3-2-7/7.7.7 — plywood quality **[LEGIBLE]**

"**Plywood is to be of marine quality and manufactured in accordance with a
recognized national standard.**" — the same non-answer as ORY 4.9. **ABS names
NO plywood grade, NO species list and NO standard.** **NOT FOUND**, in both the
1994 and 2021 documents. Whatever names BS 1088 / EN 636 / AS-NZS 2272, it is
not a classification society.

---

## Lloyd's Register — FREE, CURRENT, IN SCOPE, AND THE BEST STRUCTURED OF ALL OF THEM

### LR.1 — Rules and Regulations for the Classification of Special Service Craft, July 2020

- **Source: the Lloyd's Register Foundation Heritage & Education Centre's
  Internet Archive collection**, released under **Attribution-NoDerivs 4.0
  International (CC BY-ND 4.0)**. This is an OFFICIAL free release by LR's own
  foundation, not a pirate scan.
- Item: `https://archive.org/details/lloyds-register-rules-and-regulations-for-the-classification-of-special-service-craft-july-2020`
- Direct PDF (9.1 MB, **1193 pages**, clean text layer):
  `https://archive.org/download/lloyds-register-rules-and-regulations-for-the-classification-of-special-service-craft-july-2020/Lloyd%27s%20Register%20Rules%20and%20Regulations%20for%20the%20Classification%20of%20Special%20Service%20Craft%2C%20July%202020.pdf`
- **READ.** Everything below is **[LEGIBLE]** from a clean text layer.
- The same collection also holds the **July 2014** and **July 2016** editions,
  same licence.
- **SCOPE: this is a SMALL-CRAFT rule set.** Its own decision flowchart (p.4 of
  the PDF) routes craft by Rule Length; it explicitly branches "**Yacht <= 24 m
  → EC or other National legislation**" and "**Racing yacht → Rules for
  International Rating Class Yachts**", which means **for a <= 24 m recreational
  yacht LR itself points you at the Recreational Craft Directive / ISO 12215**,
  not at these Rules. But the Rules' **service craft, workboat, pilot and patrol
  branches have NO lower length bound**, and Part 8's own correction factors are
  tabulated **down to `L_R <= 15 m`** (see `KL` below). **So a 5–15 m WORKBOAT or
  patrol craft is squarely in scope; a 5–15 m private yacht is deliberately out
  of it.** State which one you are doing.

**Structure of the method** (and it is a genuinely better structure than ABS's):
- **Part 5** produces DESIGN PRESSURES, factorised by notation.
- **Part 8 Ch 3** turns pressure into a **BENDING MOMENT per unit width**, then
  into **ply-by-ply stresses** through a laminate stack.
- **Part 8 Ch 7** holds all the **ALLOWABLES**, in one place, as **fractions of
  ultimate strength at FIRST PLY FAILURE**.

That separation — loads, mechanics, allowables, each in exactly one place — is
the same "one source per question" discipline this project enforces, and it is
why LR is the easiest of the three to reimplement.

#### LR Pt 5, Ch 3, 2.2.2 — the DESIGN PRESSURE FACTOR CHAIN

```
Design pressure = δf * Hf * Gf * Sf * Cf * (load criterion)     kN/m²
```

**`Hf` — hull notation factor** (Table 3.2.1): `HSC` **1,0** · `LDC` **0,95**.
(Where a craft is eligible for both, use the higher; 1,0 if eligible for
neither.)

**`Gf` — SERVICE AREA RESTRICTION factor** (Table 3.2.2) — **THIS IS THE DIRECT
FREE ANALOGUE OF AN ISO 12215 DESIGN CATEGORY**:

| Service area restriction notation | `Gf` |
|---|---|
| G1, Zone 3 | **0,60** |
| G2, Zone 2 | **0,75** |
| G2A, Zone 1 | **0,80** |
| G3 | **0,85** |
| G4 | **1,00** |
| G5 | **1,20** |
| G6 | **1,25** |

**A 2.08× total span from most sheltered to most exposed, published, with
notations.** ABS gives you 1,0/0,85 and an unpublished "sheltered waters"
allowance. This table alone justifies reading LR.

**`Sf` — service TYPE factor** (Table 3.2.3):

| Service type | `Sf` |
|---|---|
| Cargo (A) | 1,00 |
| Cargo (B) | 1,10 |
| Passenger, Passenger (A) | 1,00 |
| Passenger (B) | 1,10 |
| **Patrol** | **1,20** |
| **Pilot** | **1,25** |
| **Yacht** | **1,10** |
| **Workboat** | **1,25** |

**`Cf` — CRAFT TYPE factor** (Table 3.2.4):

| Craft type | `Cf` |
|---|---|
| Mono | 1,00 |
| **Catamaran** | **1,00** |
| Multi | 1,10 |
| Hydrofoil | 1,10 |
| **RIB** | **1,15** |
| SES | 1,00 |
| SWATH | 1,00 |

**`δf` — STIFFENING TYPE factor** (Table 3.2.5): **0,5** for primary stiffening
members and transverse frames; **0,8** for secondary and local stiffening
members and transverse beams. **`δf` applies to STIFFENER pressures only, not to
plating** — plating pressures in Table 3.3.1 carry no `δf`. That is a load-area
averaging allowance and it is worth copying: a primary girder is designed to
HALF the plating pressure.

**Note 1 on the pressure table: `Gf` is not to be taken less than 1,0 for
weather decks and coachroof decks** — the sheltered-water discount does not
apply to green water on deck.

#### LR Pt 5, Ch 3, Table 3.3.1 — how the factors compose (mono-hull, non-displacement)

| Location | Plating pressure `P_BP` etc. | Stiffener pressure |
|---|---|---|
| **Bottom shell**, basic craft | GREATEST of `Hf·Sf·Ps`, `Hf·Sf·Cf·Pdl`, `Hf·Sf·Gf·Cf·Pf` | same three, each × `δf` |
| **Side shell** | `= P_BP` (the bottom plating pressure) | `δf · P_BP` |
| Wet deck | greater of `Hf·Sf·Ps`, `Hf·Sf·Ppc` | × `δf` |
| Weather deck | greater of `Hf·Sf·Gf·Cf·Pwl`, `Pcd`, **minimum 7 kN/m²** | × `δf`, min **7** |
| Coachroof deck | `Hf·Sf·Gf·Cf·Pwl`, **minimum 7** | × `δf`, min **7** |
| Interior deck | greater of `Hf·Sf·Cf·Pwl`, `Pcd`, **minimum 3,5 kN/m²** | × `δf`, min **3,5** |
| Deckhouses, bulwarks, superstructure | `Hf·Sf·Gf·Cf·Pdhp` | × `δf` |
| Deckhouse windows, toughened glass | `Hf·Sf·Gf·Cf·Pdhp`, min **7** on first tier & fronts, **5** elsewhere | — |
| Inner bottom | `Hf·Sf·Pm + Ph`, min **10T** | `δf(Hf·Sf·Pm + Ph)`, min `10T` |
| Watertight & deep tank bulkheads | `Pbh` | `Pbh` (**no `δf`**) |

**The side shell simply inherits the bottom plating pressure.** For multi-hulls
there is an extra inboard-side-shell row of `1,6 P_WDP` (plating) / `1,9 P_WDP`
(stiffener) at the wet deck.

#### LR Pt 5, Ch 2 — the load criteria themselves

**Hydrostatic (4.3.1):**
```
Ph = 10 * (Tx - z - zk)        kN/m²      up to the operating waterline
```

**Hydrodynamic wave pressure (4.4)** — the GREATER of `Pm` and `Pp`:
```
Pm = 10 * fz * Hrm            kN/m²
  fz = kz + (1 - kz) * (z - zk)/Tx        vertical distribution factor
  kz = e^(-u),   u = 2π * Tx / Lwl

Pp = 10 * Hpm                 kN/m²
  Hpm = 1,1 * (2*xwl/Lwl - 1) * Lwl        but not less than fL * Lwl
  fL = 0,6                    for Lwl < 60 m
     = 1,5 - 0,015*Lwl        for 60 <= Lwl <= 80
     = 0,3                    for Lwl > 80
  Lwl not greater than 150 m
```
**Nominal wave limit height (4.4.4): `Hw = 2 * Hrm`.**

**Combined shell envelope pressure `Ps` (Table 2.4.1)** — a three-point vertical
profile with interpolation between:

| Vertical position `z` | `Ps` |
|---|---|
| `z <= Tx + zk` (up to the operating waterline) | `Ph + Pw` |
| `z = Tx + zk + Hw` | `Pd` (the weather-deck pressure) |
| `z >= Tx + zk + 1,5 Hw` | `0,5 Pd` |

**Weather/interior deck pressure (4.5.2, displacement mode):**
```
Pwh = fL * (6 + 0,01*Lwl) * (1 + 0,05*Γ) + E        kN/m²
```
**(4.5.3, NON-displacement mode):**
```
Pwl = fL * (5 + 0,01*Lwl) * (1 + 0,5*av) + E        kN/m²
```
- `fL` = 1,0 from aft end to 0,88 L_R · **1,25** from 0,88 to 0,925 L_R ·
  **1,50** from 0,925 L_R to forward end; **`fL` = 1,0 for interior decks**
- `E = 0,7 + 0,08*Lwl/(D - T)` kN/m² for exposed decks, **need not exceed
  3 kN/m²**; `E = 0` for interior decks and superstructure decks aft of the
  forward quarter
- `Γ` = Taylor Quotient; `av` = vertical acceleration at LCG in g
- **`av` not less than 1,0 and need not exceed 4,0 for weather decks; need not
  exceed 1,0 for interior decks**

**Bottom slamming, DISPLACEMENT mode (5.1.2):**
```
Pdh = Φdh * (19 - 2720 * Tx / Lwl²) * Lwl * V        kN/m²,   Pdh >= Pm
```
- `Φdh` = **0,09** at `Lwl` from the aft end of `Lwl` (i.e. at the bow) ·
  **0,18** at 0,9 `Lwl` · **0,18** at 0,8 `Lwl` · **0,0** between the aft end and
  0,5 `Lwl`; linear interpolation between
- `Tx` = draught `T`, but **need not be taken greater than `0,08 Lwl`**
- `V` = allowable speed, knots

**NOTE — this is ABS's `Hfs` formula.** ABS ORY/Yachts 3-2-2/1.3.1 has
`Hfs = N4·Ks·(19 - 2720·d/Lw²)·Lw·V` with `Ks` = 0,09 / 0,18 / 0,18 / 0. **The
bracket `(19 - 2720·d/Lw²)`, the constants 19 and 2720, the ×`Lw`×`V`, and the
0,09/0,18/0,18/0 longitudinal ladder are IDENTICAL between ABS and LR.** The two
societies are publishing the same slamming formula. **This independently
CONFIRMS the grouping this file earlier flagged as INFERRED from the ABS text
layer: it IS `d / Lw²`.** The ABS caveat is now resolved, by a clean-text source
from a different society. `N4 = 0,1045` in ABS converts the result to metres of
head; LR's version is already kN/m².

**Side shell impact, displacement mode (5.1.3):** `Pdh` at the operating
waterline, **reducing linearly to `0,4 Pdh` at the weather deck**. (ABS: `Hfs`
at the waterline reducing to `0,40 Hfs` at the weather deck. **Identical
again.**)

**Bottom slamming, NON-DISPLACEMENT (planing) mode (5.2.2):**
```
Pdlb = fd * Δ * Φ * (1 + av) / (Lwl * Go)        kN/m²
```
- `fd` = hull-form pressure factor = **54 for mono-hull craft**;
  **`= 81/NH` for catamarans and multi-hulls**, `NH` = number of hulls,
  **not to be taken greater than four**
- `Δ` = displacement, tonnes; `av` = vertical acceleration in g
- `Go` = **support girth**, m — for craft WITH chines, the girth `Gs` between
  chines/tangential points; for craft WITHOUT chines, `Gwl`, the girth between
  the waterlines either side of the hull at LCG
- `Φ` (for craft in continuous contact with water) = **0,5 at the bow** ·
  **1,0 at 0,75 Lwl** · **1,0 at 0,5 Lwl** · **0,5 at the aft end**; interpolate.
  **Otherwise `Φ = 1,0`.**

**This is a different and arguably better planing-pressure model than ABS's.**
ABS divides `Δ` by `Lw·Bw` (a projected AREA). LR divides by `Lwl·Go` (a WETTED
GIRTH), which is what a deadrise hull actually presents to the water, and it
handles multihulls by `81/NH` rather than by re-deriving `ncg`. For a chined
5–15 m planing hull this is directly usable and needs only the girth our
geometry kernel already has.

**Side shell impact, planing (5.2.3)** — a DEADRISE TRANSFER, which is the piece
ABS handles with `(70 - βsx)/(70 - βcg)`:
```
Pdls = Pdlb * tan(40 - θB) / tan(θS - 40)        kN/m²,   not greater than Pdlb
```
- `θB` = mean deadrise of BOTTOM plating at the local section, degrees
- `θS` = mean deadrise of SIDE plating at the local section, degrees
- **`(40 - θB)` not less than 10°; `(θS - 40)` not less than 10°**
- `Pdls` is **constant from the chine (or operating waterline) to a point half
  `Go` from the chine**, or the weather deck if reached first

**Forebody/bow slamming, displacement mode (5.4.1):**
```
Pf = ff * Lwl * (0,8 + 0,15*Γ)²        kN/m²   at the FP
   = Pdh    at 0,9 Lwl from the aft end
   = Pm     at 0,75 Lwl
   = 0,0    between the aft end and 0,75 Lwl
```
**Non-displacement mode (5.5.1):** `Pf` at FP = the GREATER of `Pdls` and
`ff·Lwl·(0,8 + 0,15Γ)²`; `= Pdls` at 0,75 `Lwl`; `= Pm` below 0,5 `Lwl`; `= 0`
between the aft end and 0,5 `Lwl`.

`ff`, forebody impact pressure factor (Table 2.5.2):

| Craft type | `ff` |
|---|---|
| Mono-hull, non-displacement mode | **0,94** |
| Mono-hull, displacement mode | **0,89** |
| **Catamarans and multi-hulls with partially submerged hulls** | **1,00** |
| SWATHs and multi-hulls with fully submerged hulls | 0,91 |
| Craft supported by foils / lifting devices | 0,81 |

(Where several apply, use the higher.) Side shell: `Pf` at the chine/waterline
**reducing to `0,4 Pf`** (displacement) or **`0,3 Pf`** (non-displacement) at the
weather deck.

**Vertical acceleration distribution (3.2.7)** — the free analogue of ABS's
FIGURE 4 `FV` curve, and unlike ABS's it is a CLOSED FORM:
```
ax = av * [ 0,86 - 0,32*(xa/Lwl) + 1,76*(xa/Lwl)² + ξa ]
ξa = 0,14 + 0,32*(xLCG/Lwl) - 1,76*(xLCG/Lwl)²
```
- `ax` = vertical acceleration in g at distance `xa` forward of the aft end of
  the static load waterline; `xLCG` = the same distance to the LCG

**This closes the biggest gap in the ABS extraction.** ABS's `FV`, `KV` and `FD`
are unreadable curves; LR publishes an equivalent longitudinal acceleration
distribution as a quadratic. *(Note the `ξa` sign pattern is the negative of the
bracket's, so `ax = av` at `xa = xLCG`, as it must — a good internal check, and
it passes.)*

#### LR Pt 8, Ch 3, 1.9 — from PRESSURE to BENDING MOMENT (per 1 cm of panel)

```
Mb = k * p * b² / (12 × 10^5)              Nm   at the panel boundary / under the stiffener base
Mc = (1,5 - k) * p * b² / (12 × 10^5)      Nm   at the panel centre
k  = (γ³ + 1) / (γ + 1)
γ  = bw / b
```
- `b` = unsupported panel breadth, mm; `bw` = base width of the stiffener, mm
- `p` = the design pressure from Part 5 (for bottom/side of a non-displacement
  craft, the greatest of `Hf·Sf·Ps`, `Ki·Hf·Sf·Cf·Pdl`, `Hf·Sf·Gf·Cf·Pf`)
- **`γ = 0` (an ideal knife-edge support) gives `k = 1`**, i.e. `Mb = p b²/12`
  and `Mc = p b²/24` — the classic fixed-fixed beam. **The `k` factor credits the
  finite WIDTH of the stiffener foot**, which no other rule here does.

**Aspect-ratio correction (1.10.1)** — a CLOSED FORM, and note it is LOGARITHMIC
where ABS and ORY use a table:
```
KAR = 0,56 + 0,63 * ln(AR)          >= 0,56,   applied for AR < 2
AR  = panel length / panel breadth
```
*(At `AR = 2`, `0,56 + 0,63·ln2 = 0,997` ≈ 1, so the correction meets 1,0 at the
`AR = 2` cut-off, as intended. At `AR = 1`, `KAR = 0,56`. **Internally
consistent — checked.** Compare ABS `k`: 0,308 at `AR = 1` against 0,500 above
2, a ratio of 0,616. LR's 0,56 and ABS's 0,616 are the SAME PHYSICAL EFFECT
within 10%, derived independently. That agreement is worth a lot as a
cross-check on our own panel model.)*

**Convex curvature (1.11.1)** — again a closed form, and note it is a DIFFERENT
model from ABS's `(1 - A/s)`:
```
Kc = 1 - 1,76 * h / s          >= 0,56
```
- `h` = perpendicular distance from the chord `s` (the spacing) to the highest
  point of the curved arc

**LR gives 1,76× the crown/chord ratio where ABS gives 1,0×, and both floor at
the same place (LR 0,56, ABS 0,70).** So LR rewards curvature nearly twice as
fast but caps harder. **The two are NOT interchangeable — do not mix them.**

**Slamming pressure area correction `Ki` (1.12.1)** — the free analogue of ABS's
unreadable `FD` design-area curve:
```
Ki = (0,18 + 1,8/16) * ... 
```
**TRANSCRIPTION FLAG:** the text layer renders this as
`Ki = 0,18 + 1,8 / [ 16 * (Apn/Arf) + 1,1 ]`, with the `16` and the `1,1`
recovered but the nesting of the fraction NOT unambiguous. **Bounded by
`0,7 <= Ki <= 1`.** What IS unambiguous:
- `Apn` = area of the plate laminate, m², **not to be taken greater than
  `2 (s/1000)²`** — i.e. **the same "cap the panel area at ~2×spacing²" idea as
  ABS's `AD <= 2,5 s²`**, with 2 instead of 2,5
- `Arf` = **reference impact pressure area = `0,7 Δ / T` m²**, `Δ` in tonnes,
  `T` in metres — **and ABS's `AR = 6,95 Δ/d` cm² with `Δ` in kg is
  `6,95e-4 Δ_t/d` m²... which is NOT 0,7 Δ/T.** ABS's reference area is
  ~1000× smaller in these units. **The two societies use the same STRUCTURE
  (panel area over a displacement-derived reference area) with different
  calibrations.** Do not mix them, and do not assume either transcription of the
  constant is right without an image check.
- **Range 0,7–1,0**: a small panel gets no relief, a large one gets 30%.
  ABS's `FD` bottoms out at 0,4 — **ABS gives far more area relief than LR.**

#### LR Pt 8, Ch 3, 1.14 — SANDWICH: the sizing formulas and their assumptions

The Rules state the assumptions explicitly (1.14.1), which is unusually honest
and directly useful:
- (a) the skins carry the majority of the BENDING load;
- (b) the core carries the majority of the SHEAR load;
- (c) the initial skin estimate assumes **thin-skin theory: `core thickness /
  mean facing thickness >= 5,77`**;
- (d) the panel is **balanced**, with **`t_OUTER <= 1,33 * t_INNER`** (excluding
  gel coat and non-structural materials).

**Those four are testable admissibility predicates, and this project should hold
them as such rather than as advice.** In particular `tc/ts >= 5,77` and
`to <= 1,33 ti` are hard, free, checkable geometry constraints on any sandwich
layup we generate.

Initial sizing (1.14.2) uses coefficients `Φ1` = **0,0214 for inner skins**,
**0,0286 for outer skins**, and **0,1440 for core thickness**. *(The full
equation's exponents did not survive the text layer cleanly and are NOT
reproduced. **NOT FOUND in readable form — image check owed.**)*

Where a THICKER core than assumed is used (1.14.3), the required skin thickness
is given cleanly:
```
ts = φ2 * p * b³ / (Etps * tc²) × 10⁻³        mm
φ2 = 0,446 for inner skins
   = 0,594 for outer skins
```
*(Note `0,594/0,446 = 1,332` — exactly the `t_OUTER <= 1,33 t_INNER` balance
ratio. The two clauses are consistent, which is a good sign the coefficients
were read correctly.)*

**Core shear stress (1.14.9) — the check itself:**
```
τc = p * b * ks / (2*tc + ts) × 10⁻³        N/mm²
ks = 0,32*AR + 0,36     for AR <= 2
   = 1,0                for AR > 2
```
`AR` = panel length / panel breadth. *(At `AR = 2`, `0,32·2 + 0,36 = 1,00` —
continuous at the breakpoint. **Checked, consistent.** At `AR = 1`,
`ks = 0,68`. Compare ABS's `v`: 0,420 at `AR = 1` vs 0,500 above 2, ratio 0,84;
LR's ratio is 0,68. **The two differ materially on square panels — LR is more
generous to a square panel in shear than ABS is.**)*

The Rules note the comparison **assumes the core's shear properties were
measured by the four-point sandwich beam bending test ASTM C393 or equivalent**
— i.e. the allowable is tied to a named TEST METHOD, which is the kind of
provenance this project's honesty rules want and which ABS does not give.

**Shear ties (1.14.10)** — where core shear governs, the effective shear
strength may be raised:
```
τeff = τc + (tt / st) * τt        N/mm²
```
`tt` = thickness of shear tie material, `st` = tie spacing, `τt` = ultimate
shear strength of the tie material. **A free, closed-form model for a
through-thickness reinforced core.**

**Sandwich panel deflection (1.14.11)** — bending plus shear, with separate
aspect-ratio factors:
```
δ = (p*b²/8) * [ b²(1 - νf²)/(48 Ds) * kdb  +  kds/(G*tc) ] × 10⁻³      mm
kdb = 1,5 - 1/AR        (AR not greater than 2)
kds = 1,2 - 0,6/AR      (AR not greater than 3)
Ds  = [ Epi*t_inner * Epo*t_outer / (Epi*t_inner + Epo*t_outer) ] * ((tc + ts)/2)²   Nmm
```
`Epi` = the LESSER of `Etps` or `Ecps` of the inner skin; `Epo` likewise for the
outer. **A sandwich deflection model that includes CORE SHEAR DEFLECTION is
exactly what a foam-core small craft needs and is not something ISO 12215-5
gives away either.**

**Skin wrinkling (Pt 8, Ch 7, 3.2.2):**
```
σcr = 0,5 * (Ecps * Ec * G)^(1/3)
```
"**The ultimate compressive strength of the sandwich skin laminate shall not be
taken greater than the critical skin buckling stress.**"

**Note the coefficient: LR 0,5, ABS 0,6.** Same Hoff/Plantema form, and LR is
the more conservative. **Three independent sources (ABS 1994, ABS 2021, LR 2020)
now agree on the FORM `C·(E_skin · E_core · G_core)^(1/3)`, with C in
0,5–0,6.** That is a solid, free, cross-validated result. Note also LR's
treatment is structurally cleaner: instead of a separate acceptance criterion,
wrinkling simply CAPS the compressive strength used everywhere else.

#### LR Pt 8, Ch 7 — THE ALLOWABLES, all in one table, as fractions of ULTIMATE at FIRST PLY FAILURE

**Table 7.3.1 — limiting stress criteria, LOCAL loading.** Values are fractions
of the ultimate tensile / compressive / shear strength **at first ply failure**:

| Item | Tensile | Compressive | Shear |
|---|---|---|---|
| **Bottom shell laminate, slamming zone** | **0,28** | 0,28 | — |
| **Bottom shell laminate, elsewhere** | **0,25** | 0,25 | — |
| **Side shell laminate, slamming zone** | **0,33** | 0,33 | — |
| **Side shell laminate, elsewhere** | **0,30** | 0,30 | — |
| Keel | 0,25 | 0,25 | — |
| Bottom secondary stiffening, slamming zone | 0,33 | 0,33 | 0,33 |
| Bottom secondary stiffening, elsewhere | 0,30 | 0,30 | 0,30 |
| Bottom primary girders / web frames | 0,33 | 0,33 | 0,33 |
| Engine girders | 0,33 | 0,33 | 0,33 |
| Side secondary stiffening, slamming zone | 0,33 | 0,33 | 0,33 |
| Side secondary stiffening, elsewhere | 0,30 | 0,30 | 0,30 |
| Side primary girders / web frames | 0,33 | 0,33 | 0,33 |
| Main/strength deck laminate | 0,30 | 0,30 | — |
| Main/strength deck secondary stiffening | 0,30 | 0,30 | 0,30 |
| Main/strength deck primary girders | 0,33 | 0,33 | 0,33 |
| Hatch covers | 0,25 | 0,25 | 0,25 |
| Deckhouse front (1st and upper tiers), aft, sides, coachroof — laminate | 0,30 | 0,30 | — |
| — the same, stiffening | 0,33 | 0,33 | 0,33 |
| **House top NOT subject to personnel loading — laminate / stiffening** | **0,40** | 0,40 | 0,40 |
| Lower/inner decks & house top WITH personnel loading — laminate | 0,33 | 0,33 | — |
| — the same, stiffening | 0,30 | 0,30 | 0,30 |
| **Collision bulkhead — laminate** | **0,26** | 0,26 | — |
| Collision bulkhead — secondary / primary stiffening | 0,32 | 0,32 | 0,32 |
| Watertight bulkhead — laminate | 0,33 | 0,33 | — |
| Watertight bulkhead — secondary / primary stiffening | 0,40 | 0,40 | 0,40 |
| Watertight door in collision bulkhead | 0,25 | 0,25 | — |
| Watertight door in other bulkheads | 0,33 | 0,33 | — |
| Structure supporting WT doors, collision / other | 0,25 / 0,33 | same | same |
| **Minor bulkheads — laminate and stiffening** | **0,50** | 0,50 | 0,50 |
| Deep tank bulkheads — laminate | 0,25 | 0,25 | — |
| Deep tank bulkheads — secondary / primary stiffening | 0,33 | 0,33 | 0,33 |
| Multihull cross-deck laminate, slamming zone / elsewhere | 0,33 / 0,30 | same | — |
| Multihull cross-deck secondary stiffening, slam / elsewhere | 0,33 / 0,30 | same | same |
| Multihull cross-deck primary stiffening | 0,33 | 0,33 | 0,33 |
| Vehicle deck — laminate / secondary / primary | 0,25 / 0,33 / 0,33 | same | — / 0,33 / 0,33 |
| Helideck, normal usage — laminate / secondary / primary | 0,25 / 0,33 / 0,33 | same | — / 0,33 / 0,33 |
| Helideck, emergency landing — laminate / secondary / primary | 0,33 / 0,43 / 0,43 | same | — / 0,43 / 0,43 |
| Cargo crane pedestals/foundations | 0,25 | 0,25 | 0,25 |
| **Structures under PERMANENT STATIC loads** | **0,22** | 0,22 | 0,22 |
| LSA davit foundations | 0,22 | 0,22 | 0,22 |

**"Slamming zone" is DEFINED (Pt 8, Ch 7, 1.3.2): the region where the
operational NON-DISPLACEMENT mode pressures exceed the operational DISPLACEMENT
mode pressures.** That is a computable definition, not a hand-waved one, and our
code can evaluate it directly from the two pressure paths.

**Read the shape of this table.** The allowable is **NOT constant** — it runs
from **0,22** (permanent static load) through **0,25** (bottom shell, non-slam)
to **0,50** (minor bulkheads). The bottom shell gets the TIGHTEST structural
allowable of any hull panel, and it gets a small BONUS (0,28 vs 0,25) inside the
slamming zone because the load there is a rare impact rather than a routine one.
**And a permanently loaded structure gets 0,22 — a creep allowance, which no
other free source in this file provides at all.**

**Table 7.3.2 — GLOBAL (hull girder) loading:**

| Operational mode | Tensile | Compressive | Shear (hull) | Shear (cross-deck) |
|---|---|---|---|---|
| `Γ >= 3,0` **or** `Δ <= 0,04(L_R·B)^1,5` (i.e. planing/light) | 0,33 | 0,33 | 0,33 | 0,33 |
| `Γ < 3,0` **and** `Δ > 0,04(L_R·B)^1,5` (i.e. displacement/heavy) | 0,25 | 0,25 | 0,25 | 0,25 |

**Table 7.3.3 — LIMITING CORE SHEAR STRESS, as a fraction of ultimate core
shear strength:**

| Core material | Fraction |
|---|---|
| **PVC** | **0,45** |
| **All other cores** | **0,35** |

**And, crucially, HOW the ultimate is defined (3.5.2) — this is the best
statistical-basis statement in any free document here:**

> "The ultimate core shear strength of the core material is to be taken as
> **90 per cent of the mean ultimate shear strength** determined from accepted
> mechanical tests, **or the mean minus two standard deviations based on a
> minimum of five samples, whichever is less.**"

**That is a real, codeable characteristic-value rule** — `min(0,9·μ, μ - 2σ)`,
n >= 5 — and it is exactly the sort of thing this project needs to stop treating
a datasheet number as a design value. **Compare the three sources on core
shear**: ORY-1994 `0,50 τu` flat; ABS-2021 `0,30/0,40/0,50/0,55 τu` by core
ductility; LR-2020 `0,45 τu` PVC / `0,35 τu` other, on a defined characteristic
value. LR's is the tightest specified and the only one that says what `τu`
MEANS.

**Interlaminar shear (3.4.1): "The interlaminar shear strength of the proposed
laminate is to be demonstrated to be not less than 13,8 N/mm²."** A hard,
absolute, free material floor. *(ORY-1994's basic laminate reads 17,3 N/mm²
interlaminar shear, so a standard hand-laid mat/WR polyester passes it with
25% margin. Consistent.)*

**Deflection control (Table 7.2.1)** — span/deflection ratio `fδ` limits. LR is
the ONLY free source here that gives an explicit deflection table:

| Item | `fδ` (span/deflection) |
|---|---|
| Shell envelope, sandwich | **100** |
| Bottom secondary stiffening / primary girders | **150 / 200** |
| Side secondary stiffening / primary girders | **150 / 200** |
| Main/strength deck sandwich / secondary / primary / hatch covers | **100 / 200 / 250 / 100** |
| Superstructure & deckhouse sandwich, generally | **50** |
| Coachroof sandwich | **100** |
| House top sandwich | **50** |
| Lower/inner decks & house top with personnel loading, sandwich | **100** |
| Superstructure stiffeners, secondary / primary | 100 / 150 |
| Coachroof stiffeners, secondary / primary | 150 / 200 |
| Deep tank sandwich / secondary / primary | 100 / 100 / 200 |
| **Watertight bulkhead sandwich / secondary / primary** | **50 / 50 / 150** |
| Multihull cross-deck sandwich / secondary / primary | 100 / 125 / 150 |
| Vehicle deck sandwich / secondary / primary | 100 / 200 / 250 |
| Helicopter deck sandwich / secondary / primary | 100 / 200 / 250 |

**And, overriding all of them (2.1.2): "the span/deflection ratio for panels
subject to LONG-TERM STATIC loading is to be less than 100."**

#### LR Pt 8, Ch 3, §2 — MINIMUM THICKNESS AND MINIMUM REINFORCEMENT

**2.1.1 — a hard layup rule: "Structural laminates, used for both single skin
and sandwich construction are, in general, to incorporate NOT LESS THAN 40 PER
CENT, BY WEIGHT, OF WOVEN OR CROSS-PLY REINFORCEMENT."** (i.e. an all-CSM
structural laminate is inadmissible.)

**Single-skin minimum thickness, corrected for service type (2.4.1):**
```
tT = ω * t_min
```
`ω` = service type correction factor (Table 3.2.1):

| Service type | `ω` |
|---|---|
| Cargo | 1,1 |
| Passenger | 1,00 |
| Patrol | 1,00 |
| Pilot | 1,1 |
| **Yacht** | **1,00** |
| **Workboat — motor fishing vessel** | **1,2** |

**Fibre-content correction (2.4.2)** — all minimum thicknesses assume a fibre
content by weight `fc = 0,5`; where `fc < 0,5`:
```
t_fc = t_0,5 * (1,65 - 1,3 * fc)          mm
```
*(At `fc = 0,5` this gives `1,65 - 0,65 = 1,00` — **continuous, checked.** At
`fc = 0,35` a laminate must be **1,195×** thicker. Applies to polyester E-glass;
other laminates on an equivalence basis.)*

**Minimum reinforcement in SANDWICH SKINS (2.5.1)** — and this table is the
**only place in any free document found that gives an explicit CARBON/ARAMID
number**:
```
WT = ω * KL * KV * W_min          g/m²
```

| Panel location | `W_min` GLASS, g/m² | `W_min` **CARBON/ARAMID**, g/m² | `f_LS` |
|---|---|---|---|
| Integral tanks, fluid barrier skin | 3650 | **2700** | 0,0 |
| **Hull bottom, outer skin** | **3650** | **2700** | 0,33 |
| **Hull bottom, inner skin** | **2850** | **2100** | 0,33 |
| **Side shell, outer skin** | **3250** | **2400** | 0,33 |
| **Side shell, inner skin** | **2450** | **1950** | 0,33 |
| Inner bottom, outer / inner skin | 3650 / 2850 | 2700 / 2100 | 0,33 |
| Double bottom plate floor | 1650 | 1300 | 0,0 |
| Watertight bulkhead | 1650 | 1300 | 0,0 |
| Deep tanks, exterior / fluid barrier skin | 2450 / 3250 | 1950 / 2400 | 0,0 |
| Strength/weather deck, outer / inner skin | 2450 / 1650 | 1950 / 1300 | 0,33 / 0,0 |
| Lower deck / accommodation decks | 1650 | 1300 | 0,0 |
| Cargo deck, outer / inner skin | 2450 / 1650 | 1950 / 1300 | 0,0 |
| Superstructure sides / front / aft / top | 1650 / 2050 / 1650 / 1650 | 1300 / 1500 / 1300 / 1300 | 0,0 |
| Coach roof | 1650 | 1300 | 0,0 |
| Machinery casings | 2050 | 1500 | 0,0 |
| Bulwarks | 1650 | 1300 | 0,0 |

**THE CARBON ANSWER, and it is not what one might guess.** LR does NOT apply a
knock-down FACTOR to carbon. It sets a **lower minimum areal weight for
carbon/aramid than for glass — about 0,74 of the glass value on the hull bottom
(2700/3650), 0,74 on the bottom inner skin, 0,74 on the side shell outer, 0,80
on the side inner.** The minimum exists to guarantee **IMPACT RESISTANCE AND A
WATER BARRIER**, not strength (see 2.8.2 and 5.1.1, which allow going below the
minimum **only** if impact tests demonstrate equivalence to the Rule basic
laminate), and carbon/aramid is credited with delivering that at ~three-quarters
the areal weight. **Aramid and carbon share one column — LR does not distinguish
them here.**

**Craft length correction `KL` (2.5.3) — AND THIS IS THE CLAUSE THAT PUTS OUR
SIZE BAND IN SCOPE:**
```
KL = 1,0 - f_LS        for L_R <= 15 m
KL = 1,0               for L_R >= 35 m
       (linear interpolation between 15 m and 35 m)
f_LS = 0,0 for ALL sandwich panels in cargo, pilot and workboat craft
```
**For a craft of 15 m or less with `f_LS = 0,33`, `KL = 0,67` — a 33% reduction
in the minimum skin reinforcement.** So a 15 m hull bottom outer skin in glass
needs `1,00 × 0,67 × 1,0 × 3650 = 2446 g/m²`, and in carbon/aramid
`0,67 × 2700 = 1809 g/m²`. **These are real, in-scope, free minima for our
band** — and note `f_LS = 0` for workboats, so a 15 m workboat gets **no** length
reduction and stays at the full 3650 g/m² (times `ω = 1,2` for a motor fishing
vessel = **4380 g/m²**).

**Fibre volume correction `KV` (2.5.4)**, for `fc > 0,5`:
```
KV = [ (1 + ζF/ζR * (1-fc)/fc) / (1 + ζF/ζR) ]^0,67
```
*(grouping as printed; `ζF`, `ζR` = specific gravities of fibre and resin. At
`fc = 0,5` the bracket is 1 and `KV = 1` — **continuous, checked.**)*

**Other hard minima:**
- **Integral fuel/water tank stiffeners: not less than 4,5 mm**, irrespective of
  fibre content (2.6.1).
- **Single-skin integral tank boundary: not less than 5,0 mm**, irrespective of
  fibre content (2.6.3).
- **Double bonding angle: not less than 2 mm at 0,5 glass content by weight**
  (1.19.9).
- Bonding angle weight: **not less than 50% of the weight of the lighter member
  being connected, or 900 g/m² chopped fibre, whichever is greater**; a SINGLE
  angle (where access prevents a double) **not less than two-thirds** of the
  lighter laminate, or 900 g/m² (1.19.4, 1.19.5).
- Top-hat flange bonding width: **25 mm for the first layer + 15 mm per
  additional layer, not less than 50 mm** (1.19.6).
- **Openings in stiffener webs (1.30.1): depth <= 50% of web depth; edges not
  less than 25% of web depth from the face laminate; length <= the web depth or
  60% of the secondary member spacing, whichever is greater.**

**Keel plate (3.2.1)** — a rare closed-form scantling driven by ultimate
flexural strength:
```
bK = 7,0 * L_R + 340                    mm      (width)
tK = kt * 5,0 * L_R^0,45                mm      (thickness)
kt = 152 / σf
```
`σf` = ultimate flexural strength of the keel plate material, N/mm².
*(Sanity: at `L_R = 10 m` and `σf = 152 N/mm²` (so `kt = 1`),
`bK = 410 mm`, `tK = 5,0·10^0,45 = 14,1 mm`. Plausible for a single-skin GRP
keel band.)* Where the bottom is sandwich, **the keel returns to SINGLE SKIN**
over width `bK`, and the Rule keel thickness comprises **both** skins of the
adjacent sandwich plus additional reinforcement, with a **1:20 taper** at the
transition.

#### LR Pt 8, Ch 3, 1.7 — EFFECTIVE WIDTH of attached plating (incl. plywood-cored)

```
single skin:            b1 = 0,5*bw + 10*t_ap
sandwich:               b1 = 0,5*bw + 10*(t_outer + t_inner)
sandwich, PLYWOOD core: b1 = 0,5*bw + 10*(t_outer + t_inner + 0,5*t_ply)
```
`b1` = **half** the effective width (the geometric properties use `2 b1`), **not
to be taken greater than half the stiffener spacing**. `bw` = stiffener base
width.

**Note the plywood core counts at HALF its thickness toward effective width** —
LR does treat a plywood core as partially load-bearing, where ABS's `w = 50t`
treats a plywood panel wholesale. **These two rules are not comparable and
should not be mixed.**

#### LR — laminate property estimation without test data (1.8.3)

Where test data is unavailable for standard glass laminates, LR publishes a
complete micromechanics set — **this is a free, citable rule-of-mixtures
implementation**:
```
E0i  = EF*VF + ER*(1 - VF)                                  longitudinal modulus
E90i = EF*ER / (ER*VF + EF - EF*VF)                          transverse modulus
VF   = WF*ζR / (WF*ζR - WF*ζF + ζF)                          fibre volume fraction from weight fraction
G0/90i = GR * [ (GF/GR)(1+VF) + (1-VF) ] / [ (GF/GR)(1-VF) + (1+VF) ]
GR   = ER / (2(1+νR)),      GF = EF / (2(1+νF))
ν0/90 = VF*(νF - νR) + νR
Eθi  = E0i / [ cos⁴θ + (E0i/E90i) sin⁴θ + ¼(E0i/G0/90i - 2ν0/90) sin²(2θ) ]
```
**with a hard rule attached: "`θ` … is NOT to be taken as less than SEVEN
DEGREES to allow for misalignment."** A 7° manufacturing-misalignment floor on
every ply is a free, codeable honesty constraint on any uni-directional layup we
propose, and it is the kind of thing our `admissibility.py` should hold.

Tables 3.1.1 and 3.1.2 give **mechanical properties for CSM and for WR/cross-ply
glass-polyester as FORMULAE in the glass content** — **NOT EXTRACTED in this
pass (they are figure/table blocks). Owed work**, and high value: they would give
us a free property model as a function of fibre fraction.

#### LR — timber and plywood

**1.20.1 (Timber), in full:** "It is presumed that, in the selection of the
species of timber for a particular application, the designers will relate the
known characteristics, strength, density, bending and working capabilities of
the particular species to the constructional design. The mechanical properties
of timbers and assumptions used for design purposes are to be **clearly
indicated on the submitted construction plans**."

**That is a documentation requirement, not a scantling rule.** LR's SSC Rules
route **wooden craft to "special considerations"** in the front-matter
flowchart. **NO TIMBER OR PLYWOOD SCANTLING FORMULA, NO ALLOWABLE STRESS, NO
SPECIES TABLE. NOT FOUND.** (Pt 8, Ch 2, 2.17 "Plywood" is a CONSTRUCTION
PROCEDURES clause — **not extracted, and it is materials/workmanship, not
scantlings**.)

**So ABS gives one design-stress line for plywood (0,375 MOR, parallel plies
only) and nothing else, and LR gives nothing. Bureau Veritas, below, gives the
whole thing.**

---

## Bureau Veritas — FREE, CURRENT, AND THE ONLY SOCIETY THAT PUBLISHES A REAL PLYWOOD METHOD

### BV.1 — NR500, Rules for the Classification and the Certification of Yachts, October 2024

- **FREE PDF, no login:**
  `https://rulesexplorer-docs.bureauveritas.com/documents/nr500/oct2024/500-NR_2024-10.pdf`
- 451 pages. **READ.**
- **Download gotcha, recorded so the next session does not lose an hour:** the
  server returns the PDF wrapped in a `multipart/form-data` body
  (`------WebKitFormBoundary…`), so `curl -o file.pdf` produces a file whose
  first bytes are the boundary, not `%PDF`. **Strip everything before the first
  `%PDF` and after the last `%%EOF`.** The PDF is then **AES-encrypted with an
  EMPTY user password** — `pypdf` needs the `cryptography` package to open it
  (`r.decrypt("")` returns 1). The project venv `~/.venvs/naval` does NOT have
  `cryptography`; a throwaway venv was used rather than touching the shared one.
- **`erules.veristar.com` was UNREACHABLE from this machine** (curl exit with
  HTTP code 000 on every attempt). `rulesexplorer-docs.bureauveritas.com` and
  `marine-offshore.bureauveritas.com` both work. Use those.
- **SCOPE: "ships intended for pleasure cruising, engaged or not engaged in
  commercial sailing, with a length not exceeding 100 m", monohull or catamaran,
  hull in "steel, aluminium, composite materials, wood (strip planking or
  plywood) or High Density Polyethylene (HDPE)."** No lower bound stated. It
  explicitly acknowledges the Recreational Craft Directive (Pt A, Ch 1, Sec 3,
  §2 "Recreational craft directive (for information)").

**BV's architecture, and why it is different from ABS's and LR's:** NR500 holds
the LOADS and the SAFETY FACTORS; the structural MECHANICS for composite,
plywood and HDPE is delegated wholesale to **NR546** (BV.2 below). So the pair
must be read together — but both are free.

#### BV NR500 Pt B, Ch 4, Sec 3 — SEA PRESSURE

```
Ps = ρ * g * ( Tn * CWl / Xi + h2 - z )        kN/m²      >= Pdmin
```
**TRANSCRIPTION FLAG — the BV PDF's text layer flattens equations into glyph
runs with fraction bars and radicals lost.** The extracted fragment is
`PS  g T nCWl / XI - h2 + z – = Pdmin`. **The grouping above is NOT confirmed
and MUST NOT be coded.** What IS legible and IS recorded:

**Wave parameter `CWl`, in m:**
```
CWl = 10 * log(Lw) - 10        for Lw >= 25 m
CWl = 1,45 * e^(0,04 * Lw)     for Lw <  25 m
```
*(the sign on the `- 10` term is the reading of `10 log (LW)  10`; **flagged**.
The `Lw < 25 m` branch is the one that matters for us and it is unambiguous.
Sanity: at `Lw = 15 m`, `CWl = 1,45·e^0,6 = 2,64 m`; at `Lw = 5 m`,
`1,45·e^0,2 = 1,77 m`. Plausible wave parameters.)*

**Wave load coefficients `Xi` (Table 1)** — `Xi` DIVIDES, so a LARGER `Xi` means
a LOWER pressure. Areas run aft→forward: Area 1 = aft to 0,25 Lwl, Area 2 = 0,25
to 0,70 Lwl, Area 3 = 0,70 to 0,85 Lwl, Area 4 = 0,85 Lwl to the bow.

| Type of yacht | `X1` | `X2` | `X3` | `X4` |
|---|---|---|---|---|
| **Monohull MOTOR yacht** | 2,70 | 2,70 | 2,00 | **1,70** |
| **Monohull SAILING yacht** | 2,00 | 2,00 | 1,75 | **1,35** |
| **Multihull motor yacht** | 2,45 | 2,45 | 1,80 | **1,40** |
| **Multihull sailing yacht** | 2,40 | 2,40 | 1,60 | **1,20** |

`h2` = 0 for a monohull; for a **catamaran** it is a non-zero term on the
bottom, internal side shell and platform bottom involving `BWLi` (waterline
breadth of one float), `BE` (breadth between float axes) and `CB` — **the
formula did not survive extraction and is NOT reproduced.** `h2 = 0` on the
external side shell of a catamaran.

**A sailing yacht is loaded HARDER than a motor yacht here** (`X` smaller ⇒
pressure larger, by 35% at the bow). That is the opposite of the intuition that
the fast boat gets the bigger load — the difference is that slamming is handled
SEPARATELY, below.

#### BV NR500 — SIDE SHELL AND PLATFORM IMPACT

```
pssmin = Ci * n1        kN/m²
```
- **`n1` — the service-area factor: `1` for unrestricted navigation OR
  navigation limited to 60 nautical miles; `0,7` for a coastal area.**
- **"The side shell impact and platform bottom impact may be DISREGARDED for
  ships having the notation SHELTERED WATER."** — a published, categorical
  sheltered-water exemption, which neither ABS nor LR gives.
- The impact is modelled as **"locally distributed like a water column of 0,6 m
  diameter"**, applied above the minimum operational draught, over the whole
  length on the side shell and bulwarks, and on the lowest tier of superstructure
  side walls in line with the side shell. **That 0,6 m patch is a concrete,
  free, codeable load-footprint model** — it is what turns a pressure into a
  patch load on a panel, and it is the same 0,6 m column referenced throughout
  NR546.

**`Ci`, dynamic load on the SIDE SHELL (Table 2), kN/m²:**

| Longitudinal zone | T to T+1 m | T+1 to T+3 m | above T+3 m |
|---|---|---|---|
| aft part to 0,70 Lwl | **55** | **40** | **30** |
| 0,70 Lwl to fore part | **70** | **55** | **30** |

**`Ci`, INTERNAL side shell and platform bottom of a MULTIHULL (Table 3):**

| Area | T to T+1 m | T+1 to T+3 m | above T+3 m |
|---|---|---|---|
| Area 5 (aft third) | 55 | 40 | 30 |
| Area 6 (middle third) | 70 | 55 | 30 |
| **Area 7 (forward third)** | **80** | **70** | **50** |

*(Areas along the platform: 5 = aft `LWD/3`, 6 = middle, 7 = forward `2 LWD/3`
per Fig 3; where the platform extends to the fore float, **area 6 is to be
treated as area 7**.)* **This is a free, explicit wet-deck slamming pressure
table for catamarans, in absolute kN/m², with no formula to mis-transcribe.**

#### BV NR500 — BOTTOM SLAMMING

```
psl = psl1 * K2
psl1 = 70 * (Δ / Sr) * K1 * K3 * aCG        kN/m²   (planing hull motor yacht)
psl1 = 70 * (Δ / Sr) * K3 * av              kN/m²   (monohull sailing yacht)
```
**TRANSCRIPTION FLAG: the extracted glyph run is `psl1 70 / Sr K1 K3 aCG` — the
`70` and `Sr` are certain, the numerator `Δ` is INFERRED from `Sr` being an area
`= 0,7 Δ / T` and from dimensional necessity. Confirm before coding.** What is
unambiguous:

- **`Sr` = reference area, m² = `0,7 * Δ / T`**, `Δ` in tonnes, `T` in metres.
  **Note 1: for a catamaran, `Δ` is HALF the total displacement.**
- **Slamming applies**: for a planing motor yacht, over the bottom up to the
  bilge/chine, transom to bow; for a monohull sailing yacht, from the transverse
  section at the CG of the keel (or bulb) forward. **Note: "due to the rounded
  bottom shape of floats of catamaran sailing yachts, it is not necessary to
  calculate bottom slamming loads on these areas."**

**`K1` — longitudinal distribution factor (Table 4):**

| Location | `K1` |
|---|---|
| aft part to 0,25 Lwl | **0,60** |
| 0,25 to 0,70 Lwl | **0,90** |
| 0,70 to 0,85 Lwl | **1,00** |
| 0,85 Lwl to fore part | **0,75** |

*(Compare LR's `Φdh` 0,0/0,18/0,18/0,09 and ABS's `Ks` 0/0,18/0,18/0,09 — same
SHAPE: peak in the forward quarter, falling at the very bow, near-zero aft. BV
puts its peak at 0,70–0,85 Lwl and drops to 0,75 at the stem; ABS/LR peak at
0,8–0,9 and drop to half at the stem. **Three independent societies agree the
maximum bottom slamming pressure is at roughly 0,8 Lwl and that the stem itself
sees LESS.** That is a strong, free, cross-validated result for our pressure
distribution.)*

**`K2` — AREA factor (the panel-size reduction), with a material-dependent
floor:**
```
K2 = 0,455 - 0,35 * (u^0,75 - 1,7) / (u^0,75 + 1,7)        >= K2min
u  = 100 * sa / Sr
```
**TRANSCRIPTION FLAG:** the glyph run is
`K2 0 455 0 35 u0 75 1 7– / u0 75 1 7+ – K2min=`. The constants **0,455**,
**0,35**, **1,7** and the exponent **0,75** are all legible and the structure
`(u^0,75 - 1,7)/(u^0,75 + 1,7)` is the only reading that makes them fit; the
leading sign is INFERRED. **Confirm before coding.**
- `sa` = area supported by the element, m². **For PLATING, the stiffener spacing
  × the span, with the span NOT taken as more than THREE TIMES the spacing.**
  *(a panel-aspect cap of 3, where ABS caps the design area at `2,5 s²` and LR at
  `2 s²` — same idea, third calibration.)*

**`K2min` — and this is a genuinely important material distinction:**

| Structure | steel / aluminium / HDPE | **composite and plywood** |
|---|---|---|
| Plating | 0,50 | **0,15** |
| Secondary stiffeners | 0,45 | **0,15** |
| Primary stiffeners | 0,35 | **0,35** |

**Composite and plywood plating is allowed to take the area reduction all the
way down to 0,15 — a factor of 6,7 relief — where a metal panel floors at
0,50.** That is a large, deliberate, published difference and it says BV
believes a composite panel genuinely averages a slam over its area in a way a
metal one does not.

**`K3` — bottom shape / deadrise factor:**
```
K3 = (50 - αd) / (50 - αdCG)        <= 1
```
- `αdCG` = deadrise at LCG, degrees; `αd` = deadrise at the section considered
- **Bounds on both: 10°–30° for a SAILING yacht, 10°–50° for a MOTOR yacht.**

*(Compare ABS `(70 - βsx)/(70 - βcg)` for the SIDE and its `(50 - βcg)` term
inside `ncg`, and LR's `tan(40 - θB)/tan(θS - 40)`. **All three societies use a
"50 minus deadrise" or "40/70 minus deadrise" linear-in-degrees transfer.** BV's
is the simplest and the only one that is a clean ratio capped at 1.)*

#### BV NR500 — DESIGN VERTICAL ACCELERATION, and an honest one

**4.1.2: "The design vertical acceleration `aCG` calculated at LCG IS TO BE
DEFINED BY THE DESIGNER"**, is a RELATIVE acceleration in g **in addition to
gravity**, and **"is to be specified on the midship section drawing."** The
designer also owns the speed/wave-height relation. Applicability: planing motor
yachts with `V >= 7,16 Δ^(1/6)`; **yachts with `V >= 10 Lwl^0,5` are
individually considered.**

**BV puts the acceleration on the designer and makes them WRITE IT ON THE
DRAWING.** For a project whose honesty rules are about who owns a number, that
is the right structure and worth copying: `aCG` is an INPUT with an owner, not a
derived quantity hidden in a correlation.

For information only, where the designer has not supplied it, NR500 gives
`aCG = foc · soc · V / sqrt(Lwl) ... <= aCGmax` with `foc`, `soc`, `aCGmax` in
Tables 5, 6, 7, and a speed/wave-height relation valid only inside a stated box:
```
3500 < Δ/(0,01 Lwl)³ < 8700
3 < Lwl/BW < 5
10° < αdCG < 30°
0,2 < HS/BW < 0,7
3,0 < V/sqrt(Lwl) < 10,9
```
**The Tables 5/6/7 values and the `aCG`/`HS` formulas did NOT survive the text
layer and are NOT reproduced. NOT FOUND in readable form — image check owed.**
**The validity box above, however, IS legible and is directly useful: it is an
explicit OOD guard on a planing-acceleration correlation**, which is exactly the
shape of guard this project already requires of its surrogates.

#### BV NR500 Pt B, Ch 6, Sec 3 — THE PARTIAL SAFETY FACTOR SYSTEM

**This is the most transferable idea in any of these documents.** BV does not
publish one allowable fraction; it publishes a PRODUCT OF PARTIAL FACTORS, each
attributable to one physical cause:

```
SF = CV * CF * CR * Ci                    (minimum stress criterion, per layer)
SF_CS = CCS * CV * CF * Ci                (combined/Hoffman stress criterion)
SFB = CBuck * CV * CF * Ci                (critical buckling criterion)
```

**`CV` — AGEING:** **1,2 for monolithic laminates and for sandwich face skins
and strip planking; 1,1 for sandwich CORE materials.**

**`CF` — FABRICATION PROCESS:**

| Process | `CF` |
|---|---|
| **Prepreg** | **1,10** |
| **Infusion / vacuum** | **1,15** |
| **Hand lay-up, and strip planking** | **1,25** |
| Core materials of a sandwich | **1,00** |

**A published, numeric process-quality penalty — hand layup costs 14% over
prepreg. Nothing else in this file gives that, and it is directly relevant to a
project that reasons about manufacturability.**

**`Ci` — TYPE OF LOAD** (and note these are BELOW 1, i.e. they RELAX the factor
for rarer loads):

| Load type | `Ci` |
|---|---|
| Local external sea pressure, internal pressure, concentrated forces | **1,0** |
| **Dynamic sea pressure (bottom slamming), test pressures, flooding** | **0,8** |
| **Impact pressure on side shell and on multihull platform bottom** | **0,6** |

**`CR` — TYPE AND DIRECTION OF STRESS**, for reinforcement fibres:

| Stress | `CR` |
|---|---|
| Tension/compression **parallel** to the continuous fibre — UD tape, bi-bias, tri-axial | **2,1** |
| — the same, **woven roving** | **2,4** |
| Tension/compression **perpendicular** to the continuous fibre — UD tape, bi-bias, tri-axial | **1,25** |
| **Shear** parallel to the fibre, and interlaminar shear — UD tape, bi-bias, tri-axial | **1,6** |
| — the same, woven roving | **1,8** |
| **MAT layer**, tension/compression | **2,0** |
| **MAT layer**, shear and interlaminar shear | **2,2** |

for CORE materials:

| Core stress | `CR` |
|---|---|
| Tension/compression, general case | **2,1** |
| **Balsa, parallel to the wood grain** | **2,1** |
| **Balsa, perpendicular to the wood grain** | **1,2** |
| **SHEAR, whatever the core material** | **2,5** |

for WOOD in STRIP PLANKING:

| Stress | `CR` |
|---|---|
| Tension/compression **parallel** to the fibre | **2,4** |
| Tension/compression **perpendicular** to the fibre | **1,2** |
| **Shear parallel to the fibre and interlaminar shear** | **2,2** |

`CCS` (combined/Hoffman criterion) = **1,7** for UD tape, bi-bias, tri-axial;
**2,1** for other layer types. `CBuck` = **1,45**, with `CV = 1,2` and
`Ci = 1,2` fixed for the buckling check.

**Global hull girder loads: use the same factors but with `Ci = 1,4`.**

**Two structural rules worth copying verbatim:**
- **"When the structure is checked with a Finite Element Model, the rule safety
  factors are to be REDUCED BY TEN PER CENT."** A published, numeric reward for
  a better analysis method. This project's tiered ladder (L0 algebraic → L3
  RANS) has no such mechanism and arguably should.
- **"Rule safety factors lower than those defined may be accepted for ONE
  elementary layer when the OTHER layers of the lay-up exhibit a sufficient
  safety margin."** — i.e. first-ply-failure is not absolute if the laminate
  has redundancy.

**Worked: a hand-laid woven-roving bottom panel under slamming, parallel to the
fibre.** `SF = CV·CF·CR·Ci = 1,2 × 1,25 × 2,4 × 0,8 = 2,88`, so the allowable is
**1/2,88 = 0,347 of ultimate**. Under ordinary sea pressure (`Ci = 1,0`) it is
`1/3,60 = 0,278`. **Compare LR's 0,28 slamming-zone / 0,25 elsewhere on the
bottom shell, and ABS's flat 0,33.** BV's factorised system lands in the same
place as LR's flat table — **0,28 vs 0,278 for the ordinary-pressure case is
agreement to three significant figures, from two completely different
derivations.** That is the single strongest cross-validation in this file.

**Adhesive joints (2.4.4)** get their own chain:
`SF = 2,4 · Ct · Cv · CF · Ct° · Ci` (general) or `2,0 · …` (minor joints), with
`Ct` = 1,2 (test scatter; **1,5 if taken from datasheets**), `Cv` = 1,2
(ageing; higher if UV/seawater exposed), `CF` = 1,15 vacuum/infusion / 1,25
manual (**1,3 / 1,5 respectively if without final control**), and
**`Ct°` = 1,0 if the joint is TESTED across the service temperature range,
1,2 if EXTRAPOLATED from the supplier's datasheet.**

**`Ct° = 1,2` for "we read it off a datasheet instead of testing it" is a
published penalty for the provenance of a number. That is this project's
`{value, tier, sigma}` discipline, written into a class rule.**

#### BV NR500 — PLYWOOD SAFETY FACTORS (Pt B, Ch 6, Sec 3, §3)

Two permitted methods:
- **GLOBAL approach** (whole-plywood mechanical characteristics known):
  **"the minimum permissible safety factor `SF` … is to be at least greater than
  4,0."** — i.e. **allowable = ULTIMATE / 4 = 0,25 of the bending breaking
  stress.**
- **PLY-BY-PLY approach** (treat each veneer as a layer, same as composite):
```
SF = CR * Ci * CV
```
| `CR`, plywood | value |
|---|---|
| Tension/compression **parallel** to the grain of the ply | **3,7** |
| Tension/compression **perpendicular** to the grain of the ply | **2,4** |
| **Shear** | **2,9** |

with `Ci` = **1,0** sea/internal pressure · **0,8** slamming and flooding ·
**0,6** side-shell impact, and **`CV` (ageing) at least 1,2**.

Buckling: `SFB = CBuck · CV · Ci` with `CBuck = 1,35`, `CV = 1,2`, `Ci = 1,2`.

**Worked: plywood bottom under slamming, parallel to grain:
`3,7 × 0,8 × 1,2 = 3,55` ⇒ allowable = 0,282 of breaking stress. Under sea
pressure: `3,7 × 1,0 × 1,2 = 4,44` ⇒ 0,225.** Compare ABS's **0,375 MOR** for
plywood. **BV is markedly more conservative on plywood than ABS is** — but ABS's
0,375 is applied to the parallel plies only, while BV's ply-by-ply is applied to
each veneer's own strength in its own direction, so the two are not directly
comparable without doing the section arithmetic. **The GLOBAL approach's
`SF >= 4,0` (allowable 0,25 of the whole-panel bending breaking stress) IS
directly comparable, and it is the one we should use.**

#### BV NR500 — HDPE permissible stresses (Pt B, Ch 6, Sec 3, §4.2, Table 1)

Recorded for completeness; `R` = tensile strength at yield of the HDPE:

| Element | Stress | Permissible |
|---|---|---|
| Plating | bending | **0,45 R** |
| Secondary stiffener | bending / shear | **0,50 R** / **0,30 R** |
| Primary stiffener | bending / shear / von Mises | **0,55 R** / **0,30 R** / **0,55 R** |

#### BV NR500 — attached plating effective width (Pt B, Ch 6, Sec 5, 3.6.2)

```
bP = min(s ; 0,2 * ℓ)          plating on BOTH sides of the stiffener
bP = min(0,5*s ; 0,1 * ℓ)      plating on ONE side (stiffener bounding an opening)
```
`s` = spacing, m; `ℓ` = span, m. **Simple, span-based, and completely different
from ABS's `w = 50 t` (thickness-based) and LR's `b1 = 0,5 bw + 10 t` (thickness
+ stiffener foot).** Three societies, three unrelated effective-width models.
**This is a place where the free sources DISAGREE and we must pick one and say
which.**

Also: **primary deck stiffeners exposed to sea pressure may have their load
reduced by 0,8 for exposed SUPERSTRUCTURE decks, and by `(1 - 0,05 ℓ) > 0,8` for
exposed decks.**

---

### BV.2 — NR546, "Hull in Composite Materials and Plywood — Material Approval, Design Principles, Construction and Survey", November 2018 (NR 546 DT R02)

- **FREE PDF, no login, no wrapper, not encrypted:**
  `https://marine-offshore.bureauveritas.com/sites/g/files/zypfnx136/files/media/document/546-NR_2018-11.pdf`
- **READ.**
- **The 2018 edition is what is free at that URL.** Later editions exist
  (`546-NR_2021-10.pdf`, `546-NR_2022-11.pdf` are indexed on `erules.veristar.com`,
  which was **UNREACHABLE from this machine**) and the current NR500 (Oct 2024)
  cites NR546 under the fuller title "Hull in Composite, Plywood and High Density
  Polyethylene", i.e. **the free 2018 copy PREDATES the HDPE sections NR500 now
  references. Say so when citing it.**
- Section list: 1 General requirements and calculation principles · 2 Scantling
  criteria and hull strength analysis · 3 Main structure arrangements ·
  4 Raw materials · 5 Individual layers · 6 Laminate characteristics/panel
  analysis · 7 Stiffener analysis · **8 Plate and stiffener analysis for PLYWOOD
  structure** · 11 Hull construction, survey, tank tests.

#### **NR546 Sec 8 — THE PLYWOOD SCANTLING RULE. This is the gap-filler.**

Nothing else found in this sweep gives a plywood thickness formula. This does.

**Panel under lateral pressure, HOMOGENEOUS plywood approach (3.1.1a):**
```
t = 22,4 * β * s * sqrt( p / (σbr / SF) )        mm
```
**TRANSCRIPTION FLAG.** The extracted glyph run is
`t 2 2 4  s p / br SF ----- =`. **LEGIBLE: the constant 22,4, the factors `β`
and `s`, the pressure `p`, the breaking stress `σbr`, the safety factor `SF`,
and that the whole `p/(σbr…)` group is under a radical. NOT LEGIBLE: whether
`SF` multiplies `p` or divides `σbr`.** The form written above is the one that
is physically correct (a larger `SF` must give a THICKER panel) and it is
equivalent to `t = 22,4 β s sqrt(p·SF/σbr)`. **The alternative reading printed
by the text layer — `p/(σbr·SF)` — makes the panel THINNER as the safety factor
rises and is therefore certainly an artefact.** Recorded as an inference, with
the reasoning, so it can be checked and refuted.
- `p` = local pressure (wave loads, internal loads, **bottom slamming for a
  high-speed planing hull**), kN/m², from NR500
- `s` = the shorter panel dimension
- `σbr` = **minimum BENDING BREAKING STRESS given by the plywood manufacturer,
  in the same direction as `s` is measured.** **"When the lay direction of the
  plywood is unknown, the minimum bending breaking stress to be taken into
  account is the LESSER value obtained from the two directions of the
  plywood."** — an explicit, free, worst-case rule for an unknown layup.
- `SF` = the safety factor from NR500 (>= 4,0 global, or the `CR·Ci·CV` product
  ply-by-ply)
- `β` = **aspect-ratio coefficient. The printed formula involves `(s/ℓ)` with the
  constants 1,2 · 0,033(?) · 0,69(?) and a trailing −1, and DID NOT SURVIVE
  EXTRACTION. NOT REPRODUCED — NOT FOUND in readable form. Image check owed,
  and this is the highest-priority one in this file**, because without `β` the
  formula cannot be used.

**Side-shell panel under IMPACT pressure (3.1.1b):**
```
t = 22,4 * Cf * s * sqrt( P / (σbr / SF) )        mm
P  = Cp * pssmin
Cp = 0,98*s² + 0,3*s + 0,95        >= 0,8
```
**`Cp` IS FULLY LEGIBLE** and is a clean, codeable panel-size correction for the
0,6 m impact patch. `Cf` is a coefficient equal to 1 above a threshold in `ℓ`
relative to `(1 + s)` and a power law below it — **the threshold and the
exponent did not survive extraction. NOT REPRODUCED.**

**Ply-by-ply alternative (3.1.2):** treat the plywood as a monolithic laminate
and run it through NR546 Sec 6 §5, with the `CR·Ci·CV` safety factor.

**Plywood panel COMBINED with composite laminate (3.4.1):** the plywood may be
treated **"as an elementary layer such as a woven roving having a thickness
equal to the total plywood thickness"**, or ply-by-ply. **A free, explicit rule
for a sheathed-plywood hull — which is exactly the construction this project's
plywood SKU is likely to be.**

#### **NR546 Sec 8, §2 — THE PLYWOOD GRADE / SPECIES / QUALITY ANSWER**

This is the clause ABS and LR both decline to write.

**Approved timber species for the plies (2.1.1):**
- **Okoumé (Gaboon)**
- **African mahogany**
- **Sipo**
- **Sapelli**
- **Silver birch**
- **Gurjan (Keruing)**
- **African pearwood (Moabi)**

"Other timber species may be considered if the main elastic and mechanical
properties listed in the first column of Tab 1 are defined by the plywood
manufacturer."

**Plywood quality requirements (2.2):**
- **Marine type.**
- **Adhesive: phenolic resin, OR melamine-formaldehyde resin.**
- **Bonding quality Class 3 to EN-314.**
- **Minimum density greater than 500 kg/m³ at 12% moisture content.**
- **Odd number of layers, adjacent plies at right angles (0°/90°), obtained by
  a PEELING process.**

**Certification (2.3.1): "Plywood panels used for hull construction are to be
certified according to standard BS 1088 (or equivalent)"**, with a data sheet
giving manufacturer and country, timber species, certification standard, panel
thickness and the number and thickness of plies, and **the main mechanical
characteristics in the two main directions (Young's moduli, minimum bending
breaking stresses, in-plane shear modulus)**. Additional mechanical tests may be
required. A BS 1088 + EN-314 certification "may be considered as sufficient …
for the assignment of construction mark".

**So: BS 1088, EN-314 Class 3, phenolic or MF adhesive, > 500 kg/m³ at 12% MC,
odd peeled plies, seven named species. That is a complete, free, citable
plywood admissibility specification** — and it maps straight onto this
project's `admissibility.py`.

**Table 2 — minimum number of plies vs plywood thickness.** The left half of the
table extracts cleanly:

| thickness, mm | plies |
|---|---|
| 3 | 3 |
| 4 | 3 |
| 5 | 3 |
| 6 | 5 |
| 8 | 5 |
| 9 | 7 |
| 10 | 7 |
| 12 | 9 |

The right half extracts as `15→9, 18→11, 19→11, 21→15(?), 22→13(?), 25→13,
30→15, 35→15`. **The 21 and 22 mm rows are NON-MONOTONE as extracted (15 plies
at 21 mm then 13 at 22 mm) and are therefore MIS-READ. Recorded as suspect, NOT
corrected.** The 3–12 mm rows — **our whole likely range** — are clean.
"Thickness of each ply is to be defined by the manufacturer."

#### **NR546 Sec 8, Table 1 — MECHANICAL PROPERTIES OF THE APPROVED SPECIES**

"Given for information only … may be used at the first stage of the structure
check. In this case, these hypotheses are to be confirmed by mechanical tests
carried out on the complete plywood within the scope of the plywood
certification." **Moduli in N/mm², strengths in N/mm², density as specific
gravity.**

| Characteristic | Okoumé (Gaboon) | Mahogany | Sipo | Sapelli | Silver birch | Keruing (Gurjan) | Moabi |
|---|---|---|---|---|---|---|---|
| **Density** | 0,44 | 0,54 | 0,62 | 0,67 | 0,68 | 0,73 | 0,80 |
| **`EL`** (longitudinal) | **9630** | 11900 | 13715 | 14625 | 15085 | 16230 | **17835** |
| **`ET`** (transverse) | 525 | 750 | 950 | 1060 | 1115 | 1260 | 1480 |
| `GLT` | 750 | 860 | 940 | 980 | 1000 | 1050 | 1110 |
| `GLR` | 810 | 1020 | 1195 | 1280 | 1325 | 1440 | 1600 |
| `GRT` | 185 | 265 | 335 | 375 | 395 | 450 | 525 |
| `νLT` | 0,472 | 0,467 | 0,463 | 0,461 | 0,460 | 0,458 | 0,456 |
| `νTL` | 0,026 | 0,029 | 0,032 | 0,033 | 0,034 | 0,036 | 0,038 |
| **`σL` tensile** | **62** | 78 | 91 | 102 | 106 | 115 | **125** |
| **`σL` compression** | **36** | 46 | 53 | **50** ⚠ | 56 | 65 | 70 |
| `σT` tensile | 2 | 3 | 4 | 4 | 4 | 5 | 6 |
| `σT` compression | 6 | 9 | 11 | 12 | 13 | 15 | 17 |
| **`τ` // grain** | **8** | 10 | 10 | 11 | 11 | 12 | 12 |

⚠ **The Sapelli longitudinal COMPRESSION value (50) breaks the monotone
progression in density that every other row of this table follows (36, 46, 53,
**50**, 56, 65, 70).** Either the published table has a typo or the extraction
mis-read it. **NOT CORRECTED — flagged.**

**This table is a complete, free, orthotropic elastic and strength property set
for seven marine plywood species, with an explicit statement that it is
provisional pending test.** It is the single most directly usable materials
artefact found in this whole sweep, and it is exactly what a plywood scantling
path needs. Note `EL/ET` runs 12–18:1 and `σL/σT` in tension runs ~20–31:1 —
**wood is far more orthotropic than any laminate here, which is precisely why
the "count only the parallel plies" instruction in ABS and the ply-by-ply
approach in BV both exist.**

**Plywood stiffeners (Sec 8, §4)** — where the supplier's `EXi` is unavailable:
```
EXi = Σ(Ei * ei * bi) / Σ(ei * bi)
σ   = EXi * εxi / 100                    (εxi the bending strain in %)
σ  <= σbr / SF                           bending
τ   = T / S                              (T = shear force, S = web cross-section)
τ  <= τbr / SF                           shear; where no value is available,
                                         τbr may be taken from Tab 1 row "τ // grain"
```
**A free, complete plywood stiffener check, with an explicit fallback for the
shear strength.**

#### NR546 — composite panel/laminate mechanics (Sec 6, Sec 7)

**NOT EXTRACTED in this pass.** NR500 delegates the whole composite panel and
stiffener calculation to NR546 Sec 6 §5 and Sec 7, including the `ks,x` / `ks,y`
factors that credit the width of an omega stiffener foot (NR500 explicitly notes
these "may NOTICEABLY REDUCE the values of the bending moments on the laminate
panel" — the same physical effect as LR's `k = (γ³+1)/(γ+1)`), and the two
load-case treatments (uniform loads vs the 0,6 m impact water column). **This is
the largest single piece of readable, free, in-scope material this sweep did not
get to, and it is the obvious next target.**

Also NOT extracted, and worth having: NR546's **three theoretical breaking
criteria** — (a) maximum stress per elementary layer, (b) **Hoffman combined
stress with in-plane stresses per layer**, (c) critical buckling for the global
laminate — with **(a) and (b) checked per layer and (c) for the whole
laminate**, and **first ply failure** defined as "the full lay-up laminate
breaking strength is reached as soon as the lowest breaking strength of any
elementary layer is reached". **Those definitions ARE extracted and are recorded
here**; the formulas behind them are in Sec 6.

Buckling hypotheses (NR500 Pt B, Ch 6, Sec 4, 2.1.2), which ARE legible and are
a useful modelling shortcut:
- **monolithic laminate: all panel edges SIMPLY SUPPORTED**
- **sandwich laminate: all panel edges CLAMPED**
- "For sandwich laminate, only GLOBAL buckling is taken into account. Buckling
  modes such as shear crimping, local face dimpling, face wrinkling … are
  considered as not usual with the type of sandwich used in the construction of
  yachts."

**Note that last one against ABS and LR, which BOTH require an explicit
wrinkling check.** **BV declares face wrinkling not usually relevant for yacht
sandwiches; ABS and LR require `σcr = C(E_skin·E_core·G_core)^(1/3)` to be
checked.** That is a genuine disagreement between free sources on whether a
failure mode matters, and this project should take the conservative side (check
it) and record that BV disagrees.

---

## RINA — REGISTRATION-WALLED, NOT READ

- `https://www.rina.org/en/rules` states: "**All RINA marine rules are available,
  subject to registration in the Marine Member Area (registration is free)**",
  portal at `https://membermarine.rina.org/content/rg`.
- Relevant documents named on that page: **RES. 6/E "Rules for the
  classification of pleasure yachts"** and **RES. 23/E "Rules for the
  classification of yachts designed for commercial use"**.
- **No direct PDF link is published. Registration was NOT performed and NO RINA
  DOCUMENT WAS OPENED. Nothing from RINA is transcribed anywhere in this file.**
- Third-party copies exist on document-sharing sites. **They were not used** —
  a scraped copy is not a citable edition and this project's rules say to
  distinguish reading a clause from reading about one.
- **Lead, not a source:** registration is free, so a future session can likely
  get RES. 6/E at no cost. It is the obvious next society to add.

## Societies NOT reached in this sweep

**NOT ATTEMPTED — recorded so nobody assumes they were checked and found
empty:** DNV's legacy Germanischer Lloyd yacht rules · PRS · CCS · KR · ClassNK ·
IRS · Turkish Lloyd · Croatian Register of Shipping. Several of these publish
freely and at least one (PRS) has historically published small-craft rules in
open PDF. **This is unfinished work, not a negative result.**

---

# CROSS-CUTTING COMPARISON

Everything in these two tables is drawn from the sections above and every cell
traces to a clause quoted there. Where a source was not read, the cell says so.

## Table A — DESIGN PRESSURE: how each free rule builds a bottom slamming load

| | **ABS Yachts 2021 (3-2-2/3.3)** | **LR SSC 2020 (Pt 5, Ch 2, 5.2.2)** | **BV NR500 2024 (Pt B, Ch 4, Sec 3, 3.2.2)** |
|---|---|---|---|
| Core form | `Pb = N1·Δ/(Lw·Bw)·(1+ncg)·FD·FV` | `Pdlb = fd·Δ·Φ·(1+av)/(Lwl·Go)` | `psl = 70·(Δ/Sr)·K1·K3·aCG` ⚠ |
| Δ normalised by | projected AREA `Lw·Bw` | **wetted GIRTH** `Lwl·Go` | reference area `Sr = 0,7Δ/T` |
| Acceleration | `ncg` from a Savitsky-form correlation, **capped at 7 g** | `av`, with a **closed-form longitudinal distribution** `ax = av[0,86 − 0,32ξ + 1,76ξ² + ξa]` | **`aCG` SUPPLIED BY THE DESIGNER** and written on the midship drawing |
| Longitudinal factor | `FV` — **an unreadable FIGURE** | `Φ`: 0,5 aft · 1,0 at 0,5–0,75 Lwl · 0,5 at bow | `K1`: 0,60 · 0,90 · **1,00 at 0,70–0,85 Lwl** · 0,75 at bow |
| Panel-area reduction | `FD` — **an unreadable FIGURE**, floor **0,4**; `AD <= 2,5 s²` | `Ki` in **0,7–1,0**; `Apn <= 2 s²`; ref area `0,7Δ/T` | `K2` floor **0,15 composite/plywood**, 0,50 metal; span `<= 3 s` |
| Deadrise | `βcg` clamped **10°–30°** inside `ncg` | via the side transfer `tan(40−θB)/tan(θS−40)` | `K3 = (50−αd)/(50−αdCG) <= 1`; **10°–30° sail, 10°–50° motor** |
| Multihull | divide by `Nh`, use one hull's beam | — (`fd = 81/NH`, `NH <= 4`) | `Δ` halved for a catamaran |
| Trim | `τ >= 4°` for L < 50 m | — | `τ >= 4°` in the informative `HS` relation |
| Service area | **`k = 1,0 / 0,85` only, in the DISPLACEMENT path** | **`Gf` = 0,60 → 1,25, SEVEN notations** | `n1` = 1,0 / 0,7 on IMPACT; **sheltered water exempts side impact entirely** |

⚠ = grouping flagged as inferred; see the section for exactly which token is
uncertain.

**Where the three AGREE, and it is worth trusting:**
- **The longitudinal shape of bottom slamming.** Peak around 0,75–0,85 Lwl,
  substantially LESS at the stem itself, near-zero aft of midships.
  ABS `Ks` 0/0,18/0,18/0,09 · LR `Φdh` 0/0,18/0,18/0,09 (identical) ·
  BV `K1` 0,60/0,90/1,00/0,75 (same shape, gentler).
- **The displacement-mode bow slamming FORMULA is literally the same in ABS and
  LR**: `(19 − 2720·d/Lw²)·Lw·V` with the same 0,09/0,18/0,18/0 ladder, and side
  impact reducing to **0,4×** at the weather deck in both.
- **A "constant minus deadrise, linear in degrees" transfer** appears in all
  three.
- **A panel-area cap of 2–3 × spacing²** appears in all three.

**Where they DISAGREE, and we must choose:**
- **How much area relief a big panel gets.** ABS bottoms at 0,40, LR at 0,70,
  BV at **0,15** for composite. That is a 4,7× spread and it directly sets
  plating thickness.
- **Whether the sheltered-water case is published.** LR: yes, `Gf` down to 0,60.
  BV: yes, and side impact vanishes. ABS: **no — "consideration will be given"**.
- **Who owns the acceleration.** ABS derives it, LR derives it, **BV makes the
  designer declare it.**

## Table B — ALLOWABLE STRESS: what fraction of ultimate each rule permits

All values are FRACTIONS OF ULTIMATE unless the row says otherwise.

| Material / element | **ABS ORY 1994** | **ABS Yachts 2021** | **LR SSC 2020** | **BV NR500/NR546** |
|---|---|---|---|---|
| **Single-skin FRP, shell & deck plating** | **0,50** of FLEXURAL | **0,33** of FLEXURAL | **0,25** bottom / **0,28** bottom slam zone / **0,30** side & deck, of ultimate at **first ply failure** | `1/(CV·CF·CR·Ci)`; hand-laid WR bottom = **0,278** sea / **0,347** slam |
| FRP watertight bulkhead | 0,50 of flexural | **0,50** of ultimate | **0,33** laminate / 0,40 stiffening | via factor chain |
| FRP tank bulkhead | 0,50 of flexural | **0,33** | **0,25** laminate | `Ci = 0,8` (test/flooding) |
| **FRP stiffeners** | **0,50** of ultimate (**tensile on the outer fibre, COMPRESSIVE on the crown**) | **0,33** (`SM = 83,3 p s ℓ²/σa`) | 0,30 elsewhere / **0,33** slam zone | via factor chain |
| FRP stiffener WEB SHEAR | — | **0,40 τu** of the weaker of warp/fill | 0,30 / 0,33 | `CR` 1,6–2,2 ⇒ ≈0,3–0,5 |
| Interlaminar shear | (basic laminate 17,3 N/mm²) | — | **absolute floor: 13,8 N/mm²** | `CR` 1,6–2,2 |
| **CORE SHEAR** | **0,50 τu**, all cores | **0,30** balsa · **0,40** XPVC · **0,50** linear PVC/SAN · **0,55** if shear elongation > 40% | **0,45** PVC · **0,35** all others, on `τu = min(0,9μ, μ−2σ)`, n>=5 | `CR = 2,5` for core shear whatever the core ⇒ **0,40**, × `CV`, `Ci` |
| **Skin wrinkling** | `σcr = 0,60(Es·Ecc·Gc)^⅓`, must exceed **1,0 × skin ultimate compressive** | `σc = 0,6(Es·Ecc·Gcc)^⅓`, must exceed **2,0 σa** (= 0,66 σu) | `σcr = 0,5(Ecps·Ec·G)^⅓`, **CAPS the usable compressive strength** | **declared not usually relevant for yacht sandwiches** |
| **Cold-molded wood laminate** | **0,50 × (0,22 × MOR)** = 0,11 MOR | **0,50 MOR**, MOR taken as **22%** of the species value | not covered | strip planking: `CR` 2,4 ∥ / 1,2 ⊥ / 2,2 shear |
| **Wood carvel** | **0,40 MOR** | **0,40 MOR** | not covered | — |
| **PLYWOOD** | **NOT FOUND** (4.9 is a quality sentence only) | **0,375 MOR**, section properties from **PARALLEL PLIES ONLY** | **NOT FOUND** (timber is a documentation clause) | **`SF >= 4,0` ⇒ 0,25** of bending breaking stress (global); ply-by-ply `CR` **3,7 ∥ / 2,4 ⊥ / 2,9 shear** × `Ci` × `CV` |
| **CARBON** | no stress knock-down; **admissibility rule `T/E >= 0,014`** (1,4% failure strain) and a minimum areal weight `73,8 L₁ + 100` g/m² | **same 0,33 as glass** — no carbon-specific allowable | **same fractions as glass**; minimum skin reinforcement **0,74× the glass value** | `CR` by fabric TYPE (UD 2,1 ∥ / 1,25 ⊥ / 1,6 shear), **not by fibre chemistry** |
| Steel plating | 0,60 UTS | — | — | — |
| Aluminium plating | 0,60 UTS (**welded**) / 0,75 yield (**unwelded**) bulkheads | — | — | — |
| HDPE | — | — | — | **0,45 R** plating · 0,50/0,30 secondary · 0,55/0,30/0,55 primary |

### The four things Table B actually tells us

1. **Nobody gives carbon a stress knock-down.** Not one of the four sources
   reduces the allowable STRESS FRACTION for carbon fibre. What they do instead
   is (a) ABS 1994: refuse low-strain carbon outright via `T/E >= 0,014`;
   (b) LR: let carbon meet the impact minimum at 74% of the glass areal weight;
   (c) BV: assign `CR` by FABRIC ARCHITECTURE (UD vs woven vs mat) rather than by
   fibre chemistry. **The carbon question turns out to be an ADMISSIBILITY and
   MINIMUM-THICKNESS question, not an allowable-stress question. That is a real
   finding and it changes where carbon belongs in our code.**
2. **The FRP allowable has tightened by ~35% over 27 years**: ABS 1994 `0,50 of
   flexural` → ABS 2021 `0,33 of ultimate` → LR 2020 `0,25–0,30 at first ply
   failure`. **Do not use ORY-1994's 0,50 as a current design allowable.** Its
   value to us is its completeness and its shape, not its numbers.
3. **BV's factorised system and LR's flat table agree to three significant
   figures** on a hand-laid woven-roving bottom under ordinary sea pressure
   (0,278 vs 0,28), from completely unrelated derivations. **Where two free
   sources converge like that, we can quote the number with real confidence.**
4. **Core shear is the least agreed quantity here**: 0,50 flat (ABS 1994),
   0,30–0,55 by ductility (ABS 2021), 0,35–0,45 by chemistry on a defined
   characteristic value (LR), 0,40 flat before load factors (BV). **Spread of
   nearly 2×, on the check that usually governs a foam-core bottom panel.** Take
   LR's, because it is the only one that defines what the ultimate MEANS.

## Table C — the ancillary rules, side by side

| Question | ABS Yachts 2021 | LR SSC 2020 | BV NR500/NR546 |
|---|---|---|---|
| **Aspect-ratio factor** | TABLE: `k` 0,308 (AR 1) → 0,500 (AR>2) | **closed form** `KAR = 0,56 + 0,63 ln(AR)`, >= 0,56 | `β`, **formula NOT RECOVERED** |
| **Curvature factor** | `c = 1 − A/s`, **floor 0,70** | `Kc = 1 − 1,76 h/s`, **floor 0,56** | not extracted |
| **Effective width of plating** | `w = 50t` plywood · `25t` cold-molded · **carvel: none** · FRP by FIGURE | `b1 = 0,5 bw + 10 t`; plywood core counts at **half** thickness | `bP = min(s ; 0,2ℓ)`, halved at an opening |
| **Stiffener foot width credit** | — | **`k = (γ³+1)/(γ+1)`, `γ = bw/b`** | `ks,x`, `ks,y` in NR546 (**not extracted**) |
| **Min sandwich skin** | `tos = 0,35 k3(5,7 + 0,26L)`; ⇒ 2,94–4,03 mm over 5–15 m bottom | **areal weight** `WT = ω·KL·KV·Wmin`; 15 m glass bottom outer = **2446 g/m²** | via NR546 |
| **Min core density** | `4 dc` fwd bottom / `3 dc` elsewhere, floors 100–120 kg/m³ ⚠ | — | — |
| **Sandwich geometry limits** | outer/inner skin "not greatly dissimilar" | **`tc / t_mean_face >= 5,77`; `t_outer <= 1,33 t_inner`** | — |
| **Deflection limits** | — | **full `fδ` table, 50–250**; long-term static always < 100 | — |
| **Ply misalignment allowance** | — | **`θ` not less than 7°** | — |
| **Process quality penalty** | — | — | **`CF` 1,10 prepreg / 1,15 infusion / 1,25 hand layup** |
| **Data-provenance penalty** | — | core `τu = min(0,9μ, μ−2σ)`, n>=5 | **`Ct° = 1,2` if extrapolated from a datasheet rather than tested** |
| **FEA credit** | — | — | **safety factors reduced by 10%** |

---

# WHAT THIS CAN AND CANNOT REPLACE

ISO 12215-5 does seven jobs. Here is which of them the free class rules cover.

## COVERED FREE — and covered well

**1. Design pressures for bottom, side, deck and superstructure, scaling with
length, speed, displacement and service area.** ✅ **Fully covered, three times
over.** LR SSC Pt 5 is the best of the three: every load has a closed form, the
factor chain (`δf·Hf·Gf·Sf·Cf`) is explicit, and the **service-area factor `Gf`
(0,60–1,25 across seven notations) is a direct, published analogue of ISO's
design categories A/B/C/D.** BV NR500 gives a second, independent set with a
`n1` coastal factor and an explicit sheltered-water exemption. ABS gives a
third. Where two of them agree — the longitudinal slamming distribution, the
displacement-mode bow slam formula, the deadrise transfer — **we can hold the
result with more confidence than a single paid standard would give us**, because
we have independent corroboration.

**2. Single-skin FRP panel thickness.** ✅ **Fully covered.** ABS 3-2-4/5.1.3
gives four explicit equations (strength, stiffness, minimum, hull-girder
buckling), all in clean text, plus the orthotropic `(Eℓ/Es)^¼` extension. LR
gives the same physics through bending moment and ply stresses.

**3. Sandwich section modulus, second moment, core shear and minimum skins.**
✅ **Fully covered**, and by three societies. ABS gives closed-form `SMo`, `SMi`,
`I` and the core equation `(do+dc)/2 = v·p·s/(1000τ)`. LR gives `τc = p·b·ks/
(2tc+ts)`, a sandwich deflection model **including core shear deflection**, a
shear-tie model, and the `tc/ts >= 5,77` / `to <= 1,33 ti` validity conditions.
Core shear allowables are available from all three (with the ~2× spread noted).

**4. Aspect-ratio and curvature factors, and panel-size caps.** ✅ **Covered**,
in more than one functional form (ABS table, LR closed form), with the caution
that **the forms are NOT interchangeable** — LR rewards curvature 1,76× as fast
as ABS and floors lower.

**5. Stiffener section modulus, second moment and shear area.** ✅ **Covered.**
ABS `SM = 83,3 p s ℓ²/σa`, `I = 260 p s ℓ³/(K4 E)`, `A = 7,5 p s ℓ/τ` with
`τ <= 0,4 τu`. LR gives the moment/shear path and the allowables table.

**6. Allowable stresses by material and element.** ✅ **Covered richly** — LR's
Table 7.3.1 alone is 40+ rows of published fractions, and BV's partial-factor
system explains WHY each fraction is what it is.

**7. Plywood.** ✅ **COVERED — by Bureau Veritas ONLY, and this was the find of
the sweep.** NR546 Sec 8 gives the thickness formula, the approved species list
(Okoumé, African mahogany, Sipo, Sapelli, silver birch, Keruing, Moabi), the
quality spec (**marine type, phenolic or melamine-formaldehyde adhesive,
EN-314 Class 3 bonding, > 500 kg/m³ at 12% MC, odd peeled plies, BS 1088
certification**), the thickness↔ply-count table, a **full orthotropic property
table for all seven species**, the stiffener check with a shear-strength
fallback, and the safety factors (`SF >= 4,0` global; `CR` 3,7/2,4/2,9
ply-by-ply). ABS adds a second, independent plywood design stress (0,375 MOR,
parallel plies only). **ABS's ORY-1994 and LR's SSC both decline to give any
plywood rule at all — so a session that stopped at ABS and LR would have
concluded, wrongly, that free plywood rules do not exist.**

## PARTLY COVERED — usable, with a named hole

**8. Carbon fibre.** ⚠️ **The question is answered, but not the way it was
asked.** There is **NO knock-down factor, NO fatigue reduction and NO
carbon-specific allowable stress in any free class rule read here.** What exists
is: ABS-1994's **`T/E >= 0,014`** strain-floor admissibility rule, LR's
**0,74× glass** minimum areal weight for carbon/aramid, and BV's `CR` assigned
by fabric architecture rather than fibre type. **That is enough to build a
correct carbon path, but anyone expecting "multiply by 0,8 for carbon" will not
find it, because no society does that.**

**9. The panel-load model for a local impact.** ⚠️ BV's **0,6 m diameter water
column** and its `Cp = 0,98s² + 0,3s + 0,95` are legible and usable; the `Cf`
coefficient that goes with them is not.

**10. Wood other than plywood.** ⚠️ Cold-molded and carvel are covered by ABS
(`t = 1,09(4,2 − 1,13 L^¼)·s·sqrt(p/σa)`, `σa = 0,4 MOR`, with a **22%** MOR
knock-down for cold-molded laminate) and strip planking by BV's `CR` factors.
**Multi-skin carvel is "special consideration" in BOTH ABS editions — NO FORMULA
EXISTS in any free source read here.**

## NOT COVERED FREE — you still need ISO 12215-5, or its equivalent

**11. A single self-consistent method for a <= 24 m RECREATIONAL craft.**
❌ **This is the real gap, and it is a scope gap, not a formula gap.** ABS's
Yachts Guide is written around `L >= 24 m` (its `f` table starts at 24 m; its
fore-end side pressure says `L` not less than 30 m). **LR's SSC Rules
explicitly route a yacht of 24 m or less AWAY from themselves and to "EC or
other National legislation"** — i.e. to the RCD, i.e. to ISO 12215. BV NR500 is
the only one that squarely covers our size band for a pleasure yacht, and it
delegates the mechanics to NR546. **So: the FORMULAS are all free, but only BV
gives us a free rule that is in scope for a 5–15 m recreational boat, and even
BV points at the RCD for the regulatory question.**

**12. The RCD conformity route itself.** ❌ Nothing here is a substitute for
ISO 12215 as the *harmonised standard* that gives presumption of conformity.
**A class rule is a different legal instrument.** Using BV's or LR's scantlings
does not make a boat RCD-compliant; only the Notified-Body / harmonised-standard
route does. **Anything this project computes from these rules is an ENGINEERING
CROSS-CHECK, never a compliance claim** — the same distinction the project
already enforces for the rules tier ("an ASSESSMENT AID, not certification").

**13. An explicit ISO 12215-5 CROSS-MAP.** ❌ **NOT FOUND.** No free
classification document read in this sweep tabulates its clauses against
ISO 12215-5, and a targeted search for one returned only ISO's own catalogue
entries and paywalled commentary. **Grep for "ISO 12215" in NR546 returns
nothing.** The mapping in this file's Tables A–C was constructed HERE, by
comparing clauses, and it is an inference from primary sources, not a published
equivalence.

**14. ISO's own design categories A/B/C/D as such.** ❌ The class equivalents
(`Gf`, `n1`, `k`) are **published and usable, but they are NOT the same
partition** and no free document maps one onto the other. **Do not claim a `Gf`
value "is" category B.**

**15. DNV, and therefore the 6–24 m commercial-craft rule set that is closest
to our exact scope.** ❌ **DNV-ST-0342 "Craft" is PAYWALLED.** Every direct-PDF
path tried returned DNV's SPA shell or its 404 page; `dnv.com` states access is
by subscription or purchase. Its scope — 6 to 24 m, up to 45 knots — is the best
match to this project of any document named in this file, and it is the one we
cannot read. **RINA is registration-walled (free registration, not done).**

---

# OWED WORK — the flagged items, in priority order

Each of these is a specific, bounded task. None is speculative.

1. **NR546 Sec 8 `β` aspect-ratio coefficient — render the page as an image and
   read it.** Without `β` the plywood thickness formula cannot be used, and the
   plywood formula is the highest-value thing found. (Also `Cf` on the same page.)
2. **NR546 Sec 6 and Sec 7 — the composite panel and stiffener mechanics.** Not
   extracted at all. Free, in scope, clean, and it is what NR500 delegates to.
   Includes the `ks,x`/`ks,y` stiffener-foot factors and the Hoffman criterion.
3. **Confirm the two ABS `[GROUPING INFERRED]` items that still stand**: the
   `ncg` typesetting at PDF page index 62 of `yacht-part-3-jan21.pdf`. *(The
   `Hfs` bracket `d/Lw²` is ALREADY CONFIRMED by LR's clean text — see LR
   Pt 5, Ch 2, 5.1.2. Do not re-do that one.)*
4. **ABS FIGURES 2, 3, 4 (`FD`, `KV`, `FV`) — digitise the curves**, or decide to
   use LR's closed-form `ax` distribution and `Ki` instead and say so. Prefer the
   latter; it is cheaper and it is a published formula rather than a traced graph.
5. **The two suspect ABS numbers**: TABLE 8's `180 (5,00)` core-density rows
   (5,00 lb/ft³ is 80 kg/m³, not 180) and ORY TABLE 7.3's non-monotone `k1` at
   `>2,0` *(the latter is already refuted by ABS-2021's clean 0,028 — treat ORY's
   0,025 as an OCR error, but note it, don't silently fix it)*.
6. **ABS 3-2-3/7 TABLE 10** (wood species properties in the 2021 guide) — not
   extracted. The ORY-1994 TABLE 4.4 transcribed here is its ancestor and its
   column alignment is ASSIGNED BY PLAUSIBILITY, not read. Check both together.
7. **LR Tables 3.1.1 / 3.1.2** — mechanical properties of CSM and WR/cross-ply
   glass-polyester **as formulae in the glass content**. Free property model,
   not extracted.
8. **LR Pt 8, Ch 3, 1.14.2** — the initial sandwich sizing equation whose
   coefficients (0,0214 / 0,0286 / 0,1440) were read but whose exponents were
   not.
9. **BV NR500 Tables 5, 6, 7** (`foc`, `soc`, `aCGmax`) and the `aCG` / `HS`
   formulas — mangled by the text layer, image check needed.
10. **RINA RES. 6/E** — free registration at `membermarine.rina.org`. A fourth
    independent society, and an Italian pleasure-yacht rule set is likely the
    closest of all to our size band.
11. **PRS, CCS, KR, ClassNK, IRS, Turkish Lloyd, Croatian Register** — not
    attempted at all.
12. **A newer NR546.** The free 2018 copy predates the HDPE material and the
    title NR500 (2024) now cites. `erules.veristar.com` holds 2021-10 and
    2022-11 but was unreachable from this machine; try
    `rulesexplorer-docs.bureauveritas.com/documents/nr546/<month><year>/546-NR_<yyyy-mm>.pdf`
    from a different network.

---

# REPRODUCING THIS

All files were fetched to `/tmp/classrules` with plain `curl` and a browser
User-Agent; none needed a login. Text was extracted with `pypdf`.

```
# ABS — direct, no wrapper, no encryption
curl -L -A "Mozilla/5.0" -o abs-yachts-p3-2021.pdf \
  https://ww2.eagle.org/content/dam/eagle/rules-and-guides/archives/special_service/62_yachts_2021/yacht-part-3-jan21.pdf
curl -L -A "Mozilla/5.0" -o abs-ory-1994.pdf \
  https://ww2.eagle.org/content/dam/eagle/rules-and-guides/archives/special_service/37_offshoreracingyachts/pub37_ory_guide_op.pdf

# Lloyd's Register — LR Foundation Heritage & Education Centre, CC BY-ND 4.0
curl -L -A "Mozilla/5.0" -o lr-ssc-2020.pdf \
  "https://archive.org/download/lloyds-register-rules-and-regulations-for-the-classification-of-special-service-craft-july-2020/Lloyd%27s%20Register%20Rules%20and%20Regulations%20for%20the%20Classification%20of%20Special%20Service%20Craft%2C%20July%202020.pdf"

# Bureau Veritas NR546 — direct, clean
curl -L -A "Mozilla/5.0" -o bv-nr546-2018.pdf \
  https://marine-offshore.bureauveritas.com/sites/g/files/zypfnx136/files/media/document/546-NR_2018-11.pdf

# Bureau Veritas NR500 — multipart-wrapped AND AES-encrypted (empty password)
curl -L -A "Mozilla/5.0" -o bv-nr500-raw.bin \
  https://rulesexplorer-docs.bureauveritas.com/documents/nr500/oct2024/500-NR_2024-10.pdf
python - <<'PY'
d = open('bv-nr500-raw.bin','rb').read()
open('bv-nr500.pdf','wb').write(d[d.find(b'%PDF'):d.rfind(b'%%EOF')+5])
PY
# then: pypdf + `cryptography`, reader.decrypt("")  -> returns 1
```

`~/.venvs/naval` has `pypdf` but NOT `cryptography`. **A throwaway venv was used
rather than modifying the shared project environment** — see the project's git
and shared-tree rules; the same reasoning applies to a shared venv.

---

*End of sweep. Sections above cover ABS (two documents), Lloyd's Register (one),
Bureau Veritas (two). DNV is paywalled, RINA is registration-walled, and eight
other societies were not attempted.*

