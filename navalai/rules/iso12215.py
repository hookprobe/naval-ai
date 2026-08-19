"""ISO 12215-5:2008(E) — plywood bottom-panel scantling check, TO THE TEXT.

RE-SHAPED 2026-08-19 from the operator-sourced clause text (Gate 6R items
1-4, docs/GATE-6R-REQUEST.md). Provenance is pinned: **ISO 12215-5:2008(E),
First edition, 2008-04** — withdrawn and replaced by ISO 12215-5:2019,
which REORGANIZED the calculation (kAR via its Table 9, kDYN renaming).
NEVER mix these 2008 equations with 2019 tables; a future upgrade replaces
this module wholesale against the 2019 text, not clause-by-clause.

The displacement-mode bottom path now implemented:

  P_BMD      = P_BASE * kAR * kDC * kL          (Eq 7)
  P_BASE     = 2.4 * mLDC^0.33 + 20             (Eq 9)   [kN/m^2]
  P_BM_MIN   = (0.45 * mLDC^0.33 + 0.9 * LWL) * kDC   (Eq 8)
  P_BM       = max(P_BMD, P_BM_MIN)
  t_req      = b * kC * sqrt(P_BM * k2 / (1000 * sigma_d))   (Eq 36) [mm]
  sigma_d    = 0.5 * sigma_uf                   (Table 9, plywood)
  sigma_uf,par  = 0.5 * (rho/1000) * (68 - 2*N + 0.03*N^2)   (Table E.2)
  sigma_uf,perp = 0.5 * (rho/1000) * (11 + 6.5*N - 0.28*N^2) (Table E.2)

The old module carried P = max(10, P_BASE) — a flat 10 kN/m^2 floor that
was neither length- nor category-dependent (KNOWN WRONG, review.py) — and
SIGMA_D_OKOUME = 15.0, a constant where the standard gives a formula in
plywood density and ply count (the wrong SHAPE). Both are gone.

NAMED ASSUMPTIONS (ours, basis 'approx'; the equations above are
basis 'standard'):
  * the governing bottom panel is assessed at x/LWL > 0.6, where Eq (3)
    gives kL = 1 exactly — not an assumption about the formula, only about
    which panel governs (the forward one, conservatively);
  * the panel long dimension is unmodeled, so AD = b^2 (l = b), the
    smallest admissible design area and therefore the LARGEST kAR —
    conservative by the direction of Eq (4);
  * face grain runs across the stiffeners (the build-practice
    orientation), so the PARALLEL Table E.2 strength governs bending;
    the perpendicular formula is provided for a future declared layup;
  * N_ply is mapped from sheet thickness by build practice (odd, clamped
    to the standard's presumed 5..15) — the standard presumes the count,
    it does not derive it from thickness.
"""

from __future__ import annotations

import math

from ..energy import PLY_DENSITY
from ..limits import FRAME_SPACING_M, STOCK_PLY_THICKNESS_M
from . import RuleFinding
from .review import basis_for

# ---- Eq 7 factors, ISO 12215-5:2008(E) ------------------------------------

# §7.2: "kDC accounts for variation in pressure loads with design category."
K_DC = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4}


def k_dc(design_category: str) -> float:
    """Design-category factor (§7.2). An unknown category is refused —
    defaulting it would silently pick a pressure regime."""
    try:
        return K_DC[design_category.strip().upper()]
    except (KeyError, AttributeError) as exc:
        raise ValueError(
            f"ISO 12215-5 kDC: design category {design_category!r} is not "
            f"one of {sorted(K_DC)}") from exc


def k_l(x_over_lwl: float, n_cg: float = 3.0) -> float:
    """Longitudinal pressure distribution factor, Eq (3).

    kL = (1 - 0.167*nCG)/0.6 * (x/LWL) + 0.167*nCG   for x/LWL <= 0.6
    kL = 1                                            for x/LWL >  0.6

    nCG is clamped to [3, 6] (the standard's constraint); displacement and
    sailing craft use nCG = 3. INTERPRETATION NOTE (recorded in
    review.REVIEW['interpretations']): the sourced transcription rendered
    the slope term ambiguously; the reading above is fixed by continuity —
    kL(0.6) = 0.6*(1 - 0.167*nCG)/0.6 + 0.167*nCG = 1 exactly, matching
    the x/LWL > 0.6 branch. The alternative parse is discontinuous at 0.6
    and is rejected on that ground. x/LWL = 0 is the AFT end of LWL;
    overhangs take the kL of the corresponding end.
    """
    n = min(6.0, max(3.0, float(n_cg)))
    f = float(x_over_lwl)
    if f > 0.6:
        return 1.0
    return (1.0 - 0.167 * n) / 0.6 * max(f, 0.0) + 0.167 * n


def k_ar(mldc_kg: float, b_mm: float, l_mm: float | None = None) -> float:
    """Area pressure reduction factor, Eq (4), displacement-mode plating.

    kAR = kR * 0.1 * mLDC^0.15 / AD^0.3, kAR <= 1, with the Table 3
    single-skin bottom minimum of 0.25 as the floor. kR for bottom/side/
    deck PLATING of displacement craft is 1.5 - 3e-4*b (b in mm). The
    design area is AD = l*b*1e-6 m^2, capped at 2.5*b^2*1e-6; with the
    panel length unmodeled, l = b (the smallest admissible AD, hence the
    LARGEST kAR — the conservative direction).
    """
    b = float(b_mm)
    l = b if l_mm is None else float(l_mm)
    k_r = 1.5 - 3e-4 * b
    a_d = min(l * b, 2.5 * b * b) * 1e-6
    raw = k_r * 0.1 * float(mldc_kg) ** 0.15 / max(a_d, 1e-12) ** 0.3
    return min(1.0, max(0.25, raw))


# ---- pressures -------------------------------------------------------------

def design_pressure_bottom(mldc_kg: float, lwl_m: float,
                           design_category: str = "C",
                           span_mm: float | None = None,
                           x_over_lwl: float = 1.0,
                           l_mm: float | None = None) -> float:
    """P_BM [kN/m^2] = max(Eq 7, Eq 8) for the displacement-mode bottom.

    Assessed at the governing forward panel (x/LWL = 1 -> kL = 1) unless a
    position is given. The old flat max(10, P_BASE) is gone: the minimum
    is Eq (8)'s mass+length expression scaled by kDC, exactly as the text
    gives it.
    """
    b_mm = DEFAULT_SPAN_MM if span_mm is None else float(span_mm)
    # the long dimension defaults to the Eq (4) cap value 2.5b — exact for
    # every measured monohull (girth 3.0-3.9b); pass the measured pair from
    # bottom_panel_dims_mm for the general case.
    l_eff = 2.5 * b_mm if l_mm is None else float(l_mm)
    base = 2.4 * float(mldc_kg) ** 0.33 + 20.0
    p_bmd = (base * k_ar(mldc_kg, b_mm, l_eff) * k_dc(design_category)
             * k_l(x_over_lwl))
    p_min = ((0.45 * float(mldc_kg) ** 0.33 + 0.9 * float(lwl_m))
             * k_dc(design_category))
    return max(p_bmd, p_min)


# ---- plywood strength, Table E.2 + Table 9 ---------------------------------

def sigma_uf_parallel(rho_pw_kg_m3: float, n_ply: int) -> float:
    """Ultimate flexural strength PARALLEL to face grain [N/mm^2],
    Table E.2. rho includes glue lines; N presumed odd, 5..15."""
    n = float(n_ply)
    return 0.5 * (float(rho_pw_kg_m3) / 1000.0) * (68.0 - 2.0 * n
                                                   + 0.03 * n * n)


def sigma_uf_perpendicular(rho_pw_kg_m3: float, n_ply: int) -> float:
    """Ultimate flexural strength PERPENDICULAR to face grain [N/mm^2],
    Table E.2."""
    n = float(n_ply)
    return 0.5 * (float(rho_pw_kg_m3) / 1000.0) * (11.0 + 6.5 * n
                                                   - 0.28 * n * n)


def n_plies_for_thickness(t_m: float) -> int:
    """Build-practice ply count for a stock sheet (OURS, basis 'approx'):
    odd, clamped to the standard's presumed 5..15."""
    t_mm = t_m * 1e3
    n = int(round(t_mm / 2.0))
    if n % 2 == 0:
        n += 1
    return min(15, max(5, n))


def sigma_d_plywood(rho_pw_kg_m3: float = PLY_DENSITY,
                    n_ply: int = 5) -> float:
    """Design stress = 0.5 * sigma_uf,parallel (Table 9 + Table E.2)."""
    return 0.5 * sigma_uf_parallel(rho_pw_kg_m3, n_ply)


# The panel short span is the frame spacing, declared ONCE in limits.py.
DEFAULT_SPAN_MM = FRAME_SPACING_M * 1e3


def bottom_panel_dims_mm(hull) -> tuple[float, float]:
    """(b_mm, l_mm) of the bottom panel, MEASURED from the hull.

    The panel is bounded by frames one way (the declared spacing) and by
    the keel->chine girth the other. MEASURED across the canonical fleet
    (2026-08-19): monohull girths run 3.0-3.9x the frame spacing — the
    Eq (4) area cap governs and l = 2.5b would be exact — but a CATAMARAN
    demihull's girth is 0.19 m, HALF the frame spacing, so its short span
    is the girth, not the spacing. The short/long assignment is therefore
    computed, never assumed. Duck-typed on section/chine arrays so the
    rules module stays geometry-import-free.
    """
    import numpy as _np
    i = len(hull.x) // 2
    sec = _np.asarray(hull.section(i), float)
    zc = float(hull.z_chine[i])
    d = _np.diff(sec, axis=0)
    seg = _np.sqrt((d ** 2).sum(1))
    girth_mm = float(seg[sec[:-1, 1] <= zc].sum()) * 1e3
    frame_mm = DEFAULT_SPAN_MM
    if girth_mm <= 0.0 or not _np.isfinite(girth_mm):
        return frame_mm, 2.5 * frame_mm   # degenerate: monohull-shaped default
    return min(girth_mm, frame_mm), max(girth_mm, frame_mm)


def required_thickness_mm(mldc_kg: float, lwl_m: float,
                          span_mm: float = DEFAULT_SPAN_MM,
                          design_category: str = "C",
                          k2: float = 0.5,
                          sigma_d: float | None = None,
                          n_ply: int = 5,
                          k_curve: float = 1.0,
                          l_mm: float | None = None) -> float:
    """Eq (36): t = b * kC * sqrt(P * k2 / (1000 * sigma_d)) [mm]."""
    p = design_pressure_bottom(mldc_kg, lwl_m, design_category, span_mm,
                               l_mm=l_mm)
    sd = sigma_d_plywood(n_ply=n_ply) if sigma_d is None else float(sigma_d)
    return span_mm * k_curve * math.sqrt(p * k2 / (1000.0 * sd))


def select_stock_thickness_m(mldc_kg: float, lwl_m: float,
                             span_mm: float = DEFAULT_SPAN_MM,
                             design_category: str = "C",
                             k_curve: float = 1.0,
                             l_mm: float | None = None) -> float:
    """Thinnest STOCK sheet [m] satisfying its OWN self-consistent check.

    sigma_d depends on the sheet's ply count, which depends on the sheet —
    so each candidate is judged with ITS OWN sigma_d (thickness -> N_ply
    -> sigma_d -> required t), not a global constant. Still raises when no
    sheet suffices: an unbuildable panel is a finding, not a rounding.
    """
    for t in STOCK_PLY_THICKNESS_M:
        n = n_plies_for_thickness(t)
        t_req_mm = required_thickness_mm(mldc_kg, lwl_m, span_mm,
                                         design_category, n_ply=n,
                                         k_curve=k_curve, l_mm=l_mm)
        if t * 1e3 >= t_req_mm:
            return t
    n = n_plies_for_thickness(max(STOCK_PLY_THICKNESS_M))
    t_req_mm = required_thickness_mm(mldc_kg, lwl_m, span_mm,
                                     design_category, n_ply=n,
                                     k_curve=k_curve, l_mm=l_mm)
    raise ValueError(
        f"ISO 12215-5:2008 wants {t_req_mm:.1f} mm at mLDC {mldc_kg:.0f} kg, "
        f"LWL {lwl_m:.1f} m, category {design_category}, "
        f"{span_mm:.0f} mm span; thickest stock sheet is "
        f"{max(STOCK_PLY_THICKNESS_M) * 1e3:.0f} mm. Reduce the frame "
        f"spacing or change material — do not round the requirement down.")


def assess(mldc_kg: float, provided_mm: float,
           span_mm: float = DEFAULT_SPAN_MM,
           design_category: str = "C",
           lwl_m: float | None = None,
           sigma_d: float | None = None,
           l_mm: float | None = None) -> list[RuleFinding]:
    """R-PBM + R-TBM findings against the 2008(E) text.

    `lwl_m` feeds Eq (8)'s minimum; absent, the minimum cannot be computed
    and the assessment is REFUSED rather than run on the base alone.
    """
    if lwl_m is None or not (math.isfinite(lwl_m) and lwl_m > 0):
        return [RuleFinding(
            "R-PBM", "ISO 12215-5:2008(E) Eq 7/8 (bottom design pressure)",
            basis_for("R-PBM"), False, float("nan"), float("nan"), "kN/m^2",
            f"LWL {lwl_m!r}: Eq (8)'s minimum is length-dependent and "
            f"cannot be computed — the assessment is refused, not run on "
            f"the base pressure alone")]
    n = n_plies_for_thickness(provided_mm * 1e-3)
    sd = sigma_d_plywood(n_ply=n) if sigma_d is None else float(sigma_d)
    p = design_pressure_bottom(mldc_kg, lwl_m, design_category, span_mm,
                               l_mm=l_mm)
    t_req = required_thickness_mm(mldc_kg, lwl_m, span_mm, design_category,
                                  sigma_d=sd, l_mm=l_mm)
    return [
        RuleFinding("R-PBM",
                    "ISO 12215-5:2008(E) Eq 7/8 (bottom pressure, displ. mode)",
                    basis_for("R-PBM"), True, p, p, "kN/m^2",
                    f"mLDC {mldc_kg:.0f} kg, LWL {lwl_m:.1f} m, cat "
                    f"{design_category}: kAR "
                    f"{k_ar(mldc_kg, span_mm):.3f} (l=b conservative), kDC "
                    f"{k_dc(design_category)}, kL 1.0 (forward panel "
                    f"governs); Eq 8 floor included"),
        RuleFinding("R-TBM",
                    "ISO 12215-5:2008(E) Eq 36 + Table 9 + Table E.2 "
                    "(plywood bottom thickness)",
                    basis_for("R-TBM"), provided_mm >= t_req, provided_mm,
                    t_req, "mm",
                    f"span {span_mm:.0f} mm, sigma_d {sd:.2f} N/mm^2 "
                    f"(0.5 x Table E.2 parallel at rho {PLY_DENSITY:.0f}, "
                    f"N {n}), flat panel"),
    ]
