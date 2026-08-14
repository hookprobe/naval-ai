"""ITTC-78 model-to-ship extrapolation, with the uncertainty carried through.

WHAT THIS IS FOR
================
`similitude.py` establishes that a model-scale result violates Reynolds number
by lambda^1.5 and says so. This module is the standard procedure that CORRECTS
that violation — the one thing every towing tank on earth does between measuring
a model and quoting a ship.

    C_Tm  = R_Tm / (0.5 rho_m S_m U_m^2)          measured (tank or model CFD)
    C_Fm  = 0.075 / (log10(Re_m) - 2)^2           ITTC-57 correlation line
    C_R   = C_Tm - (1 + k) C_Fm                   residuary, ASSUMED Re-invariant
    C_Fs  = 0.075 / (log10(Re_s) - 2)^2           at ship Reynolds
    C_Ts  = (1 + k) C_Fs + C_R + dC_F + C_AA + C_A
    R_Ts  = C_Ts * 0.5 rho_s S_s U_s^2

THE LOAD-BEARING ASSUMPTION, STATED OUT LOUD
============================================
`C_R` is assumed independent of Reynolds number. It is not — it absorbs the
whole 3-D viscous-pressure and wave-breaking difference between the two scales,
and the form factor (1+k) is itself measured at model Re and applied at ship Re.
This is the single largest error in ship-resistance prediction and it is the
reason full-scale CFD is worth doing at all: at lambda = 1 this entire procedure
collapses to the identity (asserted in the tests), and the assumption is never
invoked.

So the honest ordering for this project is:
  - Full-scale CFD needs NO extrapolation and costs the same (see
    `cfd.case.background_counts`: the mesh is Froude-similar, so scale is free).
  - Model-scale CFD is worth running only to reproduce a MEASUREMENT, and then
    it must be compared to the tank at MODEL scale, where both are honest.
  - Extrapolation is for turning either one into a ship prediction, and it adds
    an uncertainty of its own that this module refuses to leave out.

REFERENCES
  ITTC 7.5-02-03-01.4  1978 Performance Prediction Method
  ITTC 7.5-02-02-01    Resistance Test
  Bowden & Davison (1974), roughness allowance, as adopted by ITTC-78
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import RHO_SEA_15C_ITTC
from .resistance import form_factor, ittc57_cf
from .similitude import Condition, PhysicalModel

# Standard hull roughness [m] used by ITTC-78 when nothing better is known.
# 150 microns is a newly-painted hull; a fouled one is several times this and
# the allowance is the term that carries it.
STANDARD_ROUGHNESS_M = 150e-6

# One-sigma bands. These are DECLARED, with a basis, not derived — and they are
# the honest part of the answer, because ITTC-78 quotes no uncertainty at all.
#   - the form factor from a Prohaska plot scatters a few percent between tanks
#   - the roughness allowance is an empirical fit to ships that are not this
#     ship; treating it as half-known is generous, not pessimistic
#   - the residuary-invariance assumption is the unquantified one; the band
#     below is a stand-in until a full-scale CFD comparison measures it, which
#     is exactly what Gate 2M eventually enables.
SIGMA_FORM_FACTOR_REL = 0.10        # on (1+k)
SIGMA_ROUGHNESS_REL = 0.50          # on dC_F
SIGMA_CR_INVARIANCE_REL = 0.10      # on C_R, for the Re-invariance assumption

# Residuary resistance as a FRACTION of total, below which a form factor is
# suspected of having eaten the wave system. Expressed as a fraction rather than
# an absolute C_R so it does not have to be re-tuned per hull size or speed: for
# a displacement hull around Fn 0.26 the residuary share is O(15-25%), so 8% is
# well clear of a legitimate low-wave-making hull in one direction and well
# clear of the 3% that a 1.27 form factor produces on KCS in the other.
# basis='approx'.
RESIDUARY_FRACTION_FLOOR = 0.08


def roughness_allowance(lwl_ship: float, k_s: float = STANDARD_ROUGHNESS_M) -> float:
    """Bowden-Davison roughness allowance dC_F, as adopted by ITTC-78.

        dC_F = [105 (k_s / L_s)^(1/3) - 0.64] * 1e-3

    Can go NEGATIVE for a very long, very smooth ship; ITTC-78 applies it as
    written, so it is returned as written rather than clamped. A clamp here
    would be a silent softening of a standard.
    """
    if lwl_ship <= 0.0:
        raise ValueError("ship length must be positive")
    return (105.0 * (k_s / lwl_ship) ** (1.0 / 3.0) - 0.64) * 1e-3


def air_resistance_coefficient(area_transverse: float, wetted_ship: float,
                               cd_air: float = 0.8, rho_air: float = 1.226,
                               rho_water: float = RHO_SEA_15C_ITTC) -> float:
    """C_AA referred to the WETTED area, so it adds to C_T directly.

        C_AA = cd_air * (rho_air / rho_water) * A_T / S

    ITTC-78's own shortcut is C_AA = 0.001 A_T / S, which is this with
    cd_air * rho_air / rho_water ~ 0.00096. Kept in the physical form so a
    superstructure that is not a barn door can say so.
    """
    if wetted_ship <= 0.0:
        raise ValueError("wetted area must be positive")
    return cd_air * (rho_air / rho_water) * area_transverse / wetted_ship


@dataclass(frozen=True)
class ShipPrediction:
    """A full-scale prediction with every component kept separate.

    Components are exposed individually because that is what makes a
    disagreement diagnosable: a 10% miss that lives entirely in dC_F is a
    roughness argument, and the same 10% living in C_R is a hull-form argument.
    Collapsing them into R_Ts alone is how the two become indistinguishable.
    """

    ct_model: float
    cf_model: float
    form_k: float
    cr: float                  # residuary — the scale-invariance assumption
    cf_ship: float
    dcf_roughness: float
    caa_air: float
    ca_correlation: float
    ct_ship: float
    rt_ship: float             # [N]
    sigma_ct_ship: float       # one-sigma on C_Ts
    sigma_rt_ship: float       # one-sigma on R_Ts [N]
    re_model: float
    re_ship: float
    lam: float
    tier: str = "L1"           # the procedure is empirical, whatever fed it
    assumptions: tuple[str, ...] = ()

    @property
    def sigma_rel(self) -> float:
        return self.sigma_rt_ship / self.rt_ship if self.rt_ship else float("nan")

    def report(self) -> str:
        return "\n".join([
            f"ITTC-78 extrapolation 1:{self.lam:g}  "
            f"Re_m {self.re_model:.3e} -> Re_s {self.re_ship:.3e}",
            f"  C_Tm       {self.ct_model:.4e}   (measured at model scale)",
            f"  C_Fm       {self.cf_model:.4e}   ITTC-57",
            f"  (1+k)      {1.0 + self.form_k:.4f}",
            f"  C_R        {self.cr:.4e}   ASSUMED Reynolds-invariant",
            f"  C_Fs       {self.cf_ship:.4e}   ITTC-57 at ship Re",
            f"  dC_F       {self.dcf_roughness:+.4e}   roughness",
            f"  C_AA       {self.caa_air:+.4e}   air",
            f"  C_A        {self.ca_correlation:+.4e}   correlation",
            f"  C_Ts       {self.ct_ship:.4e} +/- {self.sigma_ct_ship:.2e}",
            f"  R_Ts       {self.rt_ship:.4g} N +/- {self.sigma_rt_ship:.2g} "
            f"({self.sigma_rel * 100:.1f}%)",
        ])


def ittc78(model: Condition, ship: Condition, ct_model: float,
           wetted_model: float, wetted_ship: float,
           form_k: float | None = None,
           sigma_ct_model: float = 0.0,
           k_s: float = STANDARD_ROUGHNESS_M,
           area_transverse: float = 0.0,
           ca_correlation: float = 0.0,
           hull_shape: tuple[float, float, float, float] | None = None,
           ) -> ShipPrediction:
    """Extrapolate a model-scale total-resistance coefficient to the ship.

    `ct_model` is C_T at MODEL scale, referred to `wetted_model`. It may come
    from a tank (EFD) or from a model-scale RANS run — the procedure does not
    care which, and that is the point: it lets Gate 2M's KCS number and the
    KRISO tank number be compared in the same frame.

    `form_k` is the Prohaska/CFD form factor k, NOT (1+k). If omitted it is
    estimated from `hull_shape` = (cb, lwl, beam, draught) via the same
    `resistance.form_factor` the L1 tier uses — imported, never restated, so
    the two tiers cannot drift apart the way the GM floor once did.

    Uncertainty is propagated in quadrature over the four independent
    contributions (measurement, form factor, roughness, residuary invariance).
    Correlations between them are ignored, which is the usual and slightly
    optimistic choice; it is recorded in `assumptions`.
    """
    if wetted_model <= 0.0 or wetted_ship <= 0.0:
        raise ValueError("wetted areas must be positive")
    lam = ship.lwl / model.lwl
    if lam < 1.0:
        raise ValueError(
            f"ship is smaller than the model (lambda = {lam:.4g}); "
            "arguments are (model, ship) in that order")

    if form_k is None:
        if hull_shape is None:
            raise ValueError("give either form_k or hull_shape=(cb,lwl,beam,T)")
        cb, l_, b_, t_ = hull_shape
        form_k = form_factor(cb, l_, b_, t_)

    cf_m = ittc57_cf(model.speed, model.lwl, model.nu)
    cf_s = ittc57_cf(ship.speed, ship.lwl, ship.nu)
    cr = ct_model - (1.0 + form_k) * cf_m
    dcf = roughness_allowance(ship.lwl, k_s)
    caa = (air_resistance_coefficient(area_transverse, wetted_ship,
                                      rho_water=ship.rho)
           if area_transverse > 0.0 else 0.0)
    ct_s = (1.0 + form_k) * cf_s + cr + dcf + caa + ca_correlation
    rt_s = ct_s * 0.5 * ship.rho * wetted_ship * ship.speed**2

    # Propagate. d(C_Ts)/d(C_Tm) = 1 via C_R; the form factor enters twice with
    # OPPOSITE signs (it is subtracted at model Re and added back at ship Re),
    # so its sensitivity is (C_Fs - C_Fm), which is negative and much smaller
    # than either term alone. That partial cancellation is real and worth
    # keeping: treating (1+k) as a flat 10% on C_Ts would overstate the band by
    # roughly an order of magnitude.
    s_meas = sigma_ct_model
    s_form = abs(cf_s - cf_m) * (1.0 + form_k) * SIGMA_FORM_FACTOR_REL
    s_rough = abs(dcf) * SIGMA_ROUGHNESS_REL
    s_cr = abs(cr) * SIGMA_CR_INVARIANCE_REL if lam > 1.0 else 0.0
    sigma_ct = math.sqrt(s_meas**2 + s_form**2 + s_rough**2 + s_cr**2)
    sigma_rt = sigma_ct * 0.5 * ship.rho * wetted_ship * ship.speed**2

    assumptions = (
        "C_R is independent of Reynolds number (the ITTC-78 premise; the "
        "dominant unquantified error, and zero only at lambda = 1)",
        "the form factor measured at model Re applies unchanged at ship Re",
        f"roughness k_s = {k_s * 1e6:.0f} um, Bowden-Davison allowance",
        "uncertainty contributions treated as independent (no covariance)",
    )
    if abs(lam - 1.0) < 1e-9:
        assumptions = ("lambda = 1: no extrapolation was applied; C_Ts = C_Tm "
                       "up to the roughness/air/correlation additions",)

    return ShipPrediction(
        ct_model=ct_model, cf_model=cf_m, form_k=form_k, cr=cr, cf_ship=cf_s,
        dcf_roughness=dcf, caa_air=caa, ca_correlation=ca_correlation,
        ct_ship=ct_s, rt_ship=rt_s, sigma_ct_ship=sigma_ct,
        sigma_rt_ship=sigma_rt, re_model=model.re, re_ship=ship.re, lam=lam,
        assumptions=assumptions)


def calibrate_form_factor(cond: Condition, ct: float) -> float:
    """Invert one measured C_T into a form factor k, at LOW Froude number.

    This is the Prohaska idea in its cheapest form and it is why one expensive
    CFD point is worth so much: (1+k) is a SHAPE property. Froude scales the
    wave-making, Reynolds scales the friction, and the form factor survives
    both — so a single calibrated k transfers to every scale and every speed of
    the same hull, and lets the L1 tier (`resistance.form_factor`, a Watanabe
    regression) be replaced by a measurement for hulls we have actually run.

        1 + k = C_T / C_F   with C_R assumed ~ 0

    THE VALIDITY CONDITION IS NOT OPTIONAL. C_R ~ 0 holds only as Fn -> 0
    (Prohaska fits over Fn 0.1-0.2 and extrapolates to zero). Applied at a
    wave-making speed this returns a number that silently contains the entire
    wave resistance, and it will then subtract that wave resistance from every
    future extrapolation. `residuary_check` below exists to catch exactly that.
    """
    cf = ittc57_cf(cond.speed, cond.lwl, cond.nu)
    if cf <= 0.0:
        raise ValueError("non-positive friction coefficient")
    return ct / cf - 1.0


def residuary_check(cond: Condition, ct: float, form_k: float) -> tuple[float, str]:
    """(C_R, verdict) — is this form factor a shape property or a sponge?

    A form factor calibrated at the wrong speed absorbs wave resistance, and
    the symptom is a residuary coefficient that is negative or implausibly
    small for the Froude number. Rough expectation for a displacement hull:
    C_R is a few tenths of 1e-3 by Fn ~ 0.25 and climbs steeply past it, so a
    C_R below ~0.1e-3 at Fn > 0.2 means the (1+k) has eaten the wave system.

    WORKED, on the numbers this project already has. KCS EFD C_Tm = 3.711e-3
    at Fn 0.26, model Re 1.40e7 -> C_Fm = 2.832e-3:

        (1+k) = 1.10  ->  C_R = 0.596e-3    plausible for Fn 0.26
        (1+k) = 1.27  ->  C_R = 0.114e-3    5x too small — suspect

    So a (1+k) of 1.27 for KCS is worth re-deriving before it is used as a
    calibration constant: it is well above the ~1.1 the Tokyo-2015 workshop
    uses for this hull, and at that value almost no wave-making is left over at
    a Froude number where KCS demonstrably makes waves. The likelier reading is
    that it absorbed a friction shortfall — which is the known state of our own
    mesh (y+ median 2475, 32% layer coverage on the old grid).

    This function does not refuse anything. It returns the verdict so the
    caller records it; a form factor is allowed to be surprising, it is just
    not allowed to be surprising and unremarked.
    """
    cf = ittc57_cf(cond.speed, cond.lwl, cond.nu)
    cr = ct - (1.0 + form_k) * cf
    if cr < 0.0:
        v = (f"C_R = {cr:.3e} is NEGATIVE: (1+k) = {1 + form_k:.3f} removes "
             f"more than the measured total. The form factor is wrong, or C_T "
             f"and the wetted area disagree.")
    elif cond.fn > 0.2 and cr < RESIDUARY_FRACTION_FLOOR * ct:
        v = (f"C_R = {cr:.3e} is {cr / ct * 100:.1f}% of C_T at Fn "
             f"{cond.fn:.3f} — implausibly small; (1+k) = {1 + form_k:.3f} "
             f"appears to have absorbed the wave resistance. Re-derive it at "
             f"low Fn (Prohaska).")
    else:
        v = f"C_R = {cr:.3e} at Fn {cond.fn:.3f}: plausible."
    return cr, v


def ittc78_from_model(pm: PhysicalModel, ct_model: float,
                      wetted_model: float, **kw) -> ShipPrediction:
    """`ittc78` driven by a PhysicalModel, with S_s scaled by lambda^2.

    The wetted area is a pure geometric quantity, so it scales exactly; taking
    it from the model rather than re-measuring the ship hull is what keeps the
    two consistent. Pass `wetted_ship=` explicitly to override.
    """
    wetted_ship = kw.pop("wetted_ship", None)
    if wetted_ship is None:
        wetted_ship = pm.to_ship(wetted_model, "area")
    return ittc78(pm.simulated, pm.ship, ct_model, wetted_model, wetted_ship, **kw)
