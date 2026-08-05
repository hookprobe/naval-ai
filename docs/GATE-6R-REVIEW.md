# Gate 6R — reviewer packet (ISO threshold parity)

**What this gate is.** Every number below is currently `basis='approx'`:
engineering-practice values standing in for the licensed standard text. The
**mechanics** around them (moment balance, geometry, the pressure/thickness
algebra) are exact and unit-tested — it is only the CONSTANTS that are
unreviewed. Gate 6R closes when a qualified reviewer with the purchased
standards confirms or corrects each row and flips its basis to `standard`.

**Nothing here is a certification.** Honesty rule 5: the rules tier is an
ASSESSMENT AID. Passing it is not CE marking, and a Notified Body is required
for the categories that need one.

## The two documents to obtain

| Standard | Scope here | ISO catalogue |
|---|---|---|
| **ISO 12217-1** — Small craft, stability and buoyancy assessment and categorization. Part 1: Non-sailing boats of hull length ≥ 6 m | R-CAT, R-DFH, R-GM, R-OLH | https://www.iso.org/standard/78514.html |
| **ISO 12215-5** — Small craft, hull construction and scantlings. Part 5: Design pressures, design stresses, scantlings determination | R-PBM, R-TBM | https://www.iso.org/standard/65578.html |

Also relevant to the surrounding claim, though not implemented as checks:
**Directive 2013/53/EU** (Recreational Craft Directive) — the legal instrument
the design categories serve. https://eur-lex.europa.eu/eli/dir/2013/53/oj

National standards bodies (ASRO in Romania, BSI, DIN, AFNOR…) resell the same
text, often cheaper than the ISO store.

## Row 1 — design-category table

`navalai/limits.py :: CATEGORY_TABLE`, consumed by `rules/iso12217.py`.

| Category | Significant wave height context (m) | Downflooding floor (m) | GM floor (m) | Max offset-load heel (deg) |
|---|---|---|---|---|
| A | 4.0 | 0.65 | 0.60 | 10.0 |
| B | 4.0 | 0.50 | 0.50 | 10.0 |
| C | 2.0 | 0.35 | 0.45 | 10.0 |
| D | 0.3 | 0.25 | 0.35 | 12.0 |

**To confirm against ISO 12217-1:**

1. **Wave-height context** (§5, design categories). Category A is conventionally
   stated as "above 4 m" rather than "4 m" — confirm whether a single number is
   even the right representation, or whether this row should be a lower bound.
   Note B and A currently carry the SAME 4.0, which cannot both be right.
2. **Downflooding height** (§6.2). Confirm the floors, and confirm the
   measurement basis: we assume the lowest opening is at the sheer line, which
   is only conservative if no lower opening exists. Real openings must be
   declared per boat.
3. **GM floor** (annex). This is the value with the most drift history — it was
   hard-coded in four places and disagreed (0.35 vs 0.45 for category C). It is
   now single-sourced, but the VALUE is still practice, not text.
4. **Offset-load heel limit** (§6.3). Confirm the limits, and confirm the crew
   loading convention below.

## Row 2 — offset-load test parameters

`navalai/rules/iso12217.py`

| Parameter | Value used | Confirm |
|---|---|---|
| `CREW_MASS_KG` | 85.0 kg | the standard's default person mass |
| `OFFSET_FRACTION` | 0.40 × beam | the standard's crew CG offset, and whether it is a fraction of beam or a defined position |

Mechanics used (exact, no review needed): `sin φ = m_crew · b / (Δ · GM)`,
from moment balance `m_crew · g · b = Δ · g · GM · sin φ`.

## Row 3 — scantlings

`navalai/rules/iso12215.py`

| Quantity | Implementation | Confirm |
|---|---|---|
| Bottom design pressure, displacement mode | `P_BM = max(10, 2.4 · mLDC^0.33 + 20)` kN/m² | the coefficients 2.4 / 0.33 / 20, the 10 kN/m² floor, and that the displacement-mode path is the right one for these craft |
| Required panel thickness | `t = b · kC · sqrt(P · k2 / (1000 · σ_d))` mm | the formula structure and the k-factor definitions |
| `k2` aspect-ratio coefficient | 0.5 (long panels; range 0.308–0.5) | the table it comes from |
| `kC` curvature correction | 1.0 (flat developable) | that 1.0 is correct for a developable panel |
| `σ_d` design bending stress | 15.0 N/mm², marine okoume ply | the design stress and whether it is a material property or a derived allowable |

**Additionally unreviewed and NOT from ISO** — practice values we chose, listed
so the reviewer can flag any that a standard actually governs:

| Constant | Value | Where |
|---|---|---|
| `FREEBOARD_FLOOR_M` | 0.25 m | ladder constraint |
| `PLY_THICKNESS_M` | 0.015 m | marine ply sheet |
| `BEND_RADIUS_RATIO` | 80 × thickness | plywood cold-bend limit |
| `TRIM_LIMIT_DEG` | 2.0 deg | our own design bar, no ISO basis |
| `LIST_LIMIT_DEG` | 2.0 deg | our own design bar, no ISO basis |

## How to record the outcome

For each row, the reviewer records **confirmed / corrected (with the value) /
not-applicable**. A corrected value goes into `navalai/limits.py` (the single
source) and its `basis` flips from `approx` to `standard` in the finding that
reports it. `rules/__init__.py` already aggregates `unreviewed_bases`, so the
gate turns green exactly when that set empties — no separate bookkeeping.

Do **not** soften a threshold to make a design pass. A failing rule is
information (honesty rule 6).
