# Gate 6R — the exact information needed (nothing else)

Reframed 2026-08-19: the gate is not "blocked on licensed ISO". Three of
six rules are already confirmed against ISO 12217-1:2015 (R-CAT, R-DFH,
R-OLH — that reading also CAUGHT two wrong models, so the process works).
What remains is exactly five items. Bring each as text, a photo of the
page, a scan, or the formula written out — any faithful source works;
the review record cites whatever edition the source is.

## From ISO 12215-5 (state the edition — 2008 or 2019+A1)

1. **Equation (7)'s factors** — the full bottom design pressure is
   P_BMD = P_BMD_BASE · kAR · kDC · kL. Needed: the DEFINITIONS/formulas
   of kAR (area reduction), kDC (design category) and kL (longitudinal
   position). Our base equation (9) is already verified; without the
   three factors we ship base pressure alone, which overstates the
   requirement amidships and understates nothing — conservative but
   wrong-shaped.
2. **Equation (8)** — the minimum pressure
   P_BM_MIN = (0,45·mLDC^0,33 + 0,9·LWL) · kDC. We have its shape from a
   non-citable third-party copy; needed: a citable confirmation + the
   kDC values. Our current flat 10 kN/m² floor is neither length- nor
   category-dependent and is KNOWN WRONG.
3. **Table E.2** — plywood ultimate flexural strength σ_uf as a FORMULA
   in plywood density (and ply count). This is THE R-TBM blocker: Table 9
   sets σ_d = 0,5·σ_uf, our flat 15 N/mm² is the wrong SHAPE, and the
   PDF text layer garbled the superscripts so the expression was never
   reconstructed. A photo of that one table closes it.
4. **The edition string** actually sourced (e.g. "ISO 12215-5:2008" or
   "ISO 12215-5:2019+A1:2022") — REVIEW['editions'] still carries a
   placeholder, which is itself a RED condition.

## From ISO 12217-1:2015

5. **Clause 6.6 body** (habitable multihulls, p. 27) — the inversion
   buoyancy and escape provisions. Everything else we use from this
   standard is already held and confirmed. 6.6 upgrades R-MHS from
   "names the gap" to real requirements for the liveaboard-cat SKU
   (the stability half is now covered by the NZ Part 40A criteria; 6.6
   is the inversion/escape half).

## What happens when each arrives

Each item -> verify against our implementation -> fix the implementation
where it differs (the R-OLH/R-DFH precedent: the standard wins, bars are
re-shaped not tuned) -> move the rule into REVIEW['confirmed'] with the
edition cited -> when items 1-4 land, R-PBM/R-TBM flip to
basis='standard' and Gate 6R's RED row meets its clearing condition.
