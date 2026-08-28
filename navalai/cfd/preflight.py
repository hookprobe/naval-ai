"""Ask the cheap questions BEFORE buying a solve, and check the free ones after.

CFD-audit P1 (docs/audit/CFD-KNOWLEDGE-AUDIT.md, Deliverable D/H). The
owner's methodology principle, made executable: *"Known water behaviour
should be known PRIOR to any simulation; simulation is for what we don't
know."* Three questions, in cost order, each answerable in milliseconds
against a solve that costs hours:

  1. `theory_answers` — does a closed form already answer this? The
     campaign's own KNOWN-BEFORE-SOLVING list (Kelvin wavelength, the
     ITTC-57 line, hydrostatics, hump-vs-Fn, Savitsky above Fn ~0.9) is
     a CFD-trigger policy that lived only as prose.
  2. `already_measured` — has THIS EXACT SURFACE been solved before?
     `cfd_kb.same_geometry` answered it from the day the book landed and
     nothing called it; 3 of 11 book records share a sha with another
     record, i.e. the corpus already contains re-solves of one surface.
  3. `family_expectation` — does the book already say what this family
     does at this Froude number? A report-tier expectation, never a
     substitute for the run — but a campaign that knows the answer to
     within the family band can spend its hours on a question it does
     not know.

And after the solve, one free validation the project already had the
inputs for and never ran:

  4. `kelvin_check` — the measured transverse wavelength against
     2*pi*U^2/g. The campaign named this match "a validation anchor" and
     computed both numbers into `case.info`; nothing compared them.

Plus the A/B validity rule the audit found violated in the campaign's own
headline ledger:

  5. `ab_comparable` — two runs may only be differenced on GEOMETRY if
     their meshes match. MEASURED: the v1/v2/v3 ladder carries
     414780 / 513941 / 414395 cells (v2 is 24% denser) under claimed
     deltas of 1.1-1.2%, which is inside the family's own +-2.5% window
     scatter. The +33% appendage delta survives this test; the ladder
     does not.

Every function REFUSES rather than guesses, and every refusal names the
number that would change the answer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..constants import G_STANDARD

#: Deltas below this fraction of the total are not design signals on the
#: mesh family the hookprobe campaign used — MEASURED as the settled
#: 5-second window scatter (docs/LESSONS.md Bin 3). A different mesh
#: family owes its own measurement; this is the one the project has.
WINDOW_SCATTER = 0.025

#: Two runs are comparable on geometry when their cell counts agree within
#: this fraction. Set at the measured confound: v2/v3 differ by 24%, and
#: the delta claimed across them was 1.1% — 20x smaller than the mesh
#: difference. 5% is tight enough that a real mesh change cannot hide and
#: loose enough that snappy's own cell-count jitter does not fire it.
AB_CELL_TOL = 0.05

#: Above this Froude number the campaign's own recipe says the impulsive
#: start folds a cell whatever the layer stack does (three deaths at
#: n=10, 8 and 5), and the fix is a velocity ramp, not layer backoff.
FN_IMPULSIVE_MAX = 0.50


@dataclass(frozen=True)
class Answer:
    """A cheap answer, or a refusal to give one. Falsy when it refuses."""
    ok: bool
    what: str
    detail: str = ""
    data: dict = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.ok


def theory_answers(question: str, fn: float | None = None) -> Answer:
    """Does a closed form answer this, making a solve a purchase of
    something already known?

    The list is the campaign's, verbatim in intent: wake wavelength,
    viscous line, hydrostatics and hump behaviour are CHECKED against
    theory, never discovered by CFD; tunnel inflow, fin wakes, this
    hull's stern-wave system and which cell folds first have no formula
    and are exactly what a solve is for.
    """
    q = question.strip().lower()
    known = {
        "wavelength": "lambda = 2*pi*U^2/g (deep-water Kelvin); compute it, "
                      "then use kelvin_check to VERIFY the run reproduced it",
        "viscous": "the ITTC-57 line on the wetted area, times a form "
                   "factor with its sigma (resistance.form_factor)",
        "friction": "same as viscous: ITTC-57, not a solve",
        "hydrostatics": "GM, waterplane, entry angle and displacement come "
                        "from the ladder in milliseconds (hydrostatics.solve)",
        "displacement": "hydrostatics, not CFD",
        "hump": "the hump is a Froude-number property: lambda/Lwl = "
                "2*pi*Fn^2 crossing 1 is the crest-to-crest condition",
        "planing": "above Fn ~0.9 use Savitsky BEFORE any CFD",
    }
    for key, how in known.items():
        if key in q:
            return Answer(True, "theory", how, {"key": key})
    return Answer(False, "theory",
                  f"no closed form in the known-before-solving list answers "
                  f"{question!r} — this is what a solve is for", {})


def already_measured(stl_sha: str, speed_ms: float | None = None) -> Answer:
    """Has this exact surface been solved? Returns the prior runs.

    The strongest reuse there is: an identical STL at the same condition
    is a question already paid for. A hit at a DIFFERENT speed is still
    reported — the geometry is known, only the condition is new.
    """
    from .. import cfd_kb
    hits = cfd_kb.same_geometry(stl_sha)
    if not hits:
        return Answer(False, "same_geometry", getattr(hits, "reason", ""), {})
    same_speed = {n: a for n, a in hits.items()
                  if speed_ms is not None
                  and abs(float(a.get("speed_ms") or -1) - speed_ms) < 1e-6}
    if same_speed:
        return Answer(True, "same_geometry",
                      f"this surface was already solved at this speed: "
                      f"{sorted(same_speed)} — re-solving buys nothing but "
                      f"a second sample of the same number",
                      {"runs": same_speed, "same_speed": True})
    return Answer(True, "same_geometry",
                  f"this surface has been solved at other speeds: "
                  f"{sorted(hits)} — the geometry is known, the condition "
                  f"is not", {"runs": hits, "same_speed": False})


def family_expectation(family: str, fn: float) -> Answer:
    """What the book says this family does at this Fn, or a refusal."""
    from .. import cfd_kb
    band = cfd_kb.pressure_fraction_band(family, fn)
    if not band:
        return Answer(False, "family_band", getattr(band, "reason", ""), {})
    lo, hi, prov = band
    return Answer(True, "family_band",
                  f"expect {100 * lo:.0f}-{100 * hi:.0f}% pressure drag "
                  f"({prov}) — a report-tier expectation, not a substitute "
                  f"for the run", {"lo": lo, "hi": hi})


def kelvin_check(speed_ms: float, measured_wavelength_m: float,
                 tol: float = 0.10) -> Answer:
    """Does the run's wave field reproduce deep-water Kelvin theory?

    THE FREE VALIDATION. lambda = 2*pi*U^2/g needs no reference data, no
    benchmark hull and no extra compute; the campaign called the match "a
    validation anchor" and checked it by hand, once. A run that does not
    reproduce the wavelength it was told to expect has a wave field that
    is not the physics, whatever its forces say.
    """
    if speed_ms <= 0 or measured_wavelength_m <= 0:
        return Answer(False, "kelvin",
                      "speed and measured wavelength must both be positive "
                      "— an unmeasured wavelength is not a passing one", {})
    theory = 2.0 * math.pi * speed_ms ** 2 / G_STANDARD
    err = abs(measured_wavelength_m - theory) / theory
    ok = err <= tol
    return Answer(ok, "kelvin",
                  f"measured {measured_wavelength_m:.3f} m against theory "
                  f"{theory:.3f} m ({100 * err:.1f}%, bar {100 * tol:.0f}%)"
                  + ("" if ok else " — the wave field is not the physics "
                                   "the case asked for"),
                  {"theory_m": theory, "rel_err": err})


def ab_comparable(a: dict, b: dict) -> Answer:
    """May these two runs be differenced on GEOMETRY?

    Requires: both settled, both calm-water resistance, speeds equal,
    meshes matched within AB_CELL_TOL, and — the clause that actually
    bites — a difference LARGER than the family's window scatter. A delta
    inside the noise is not a design signal whatever its sign, which is
    the discipline the campaign applied by hand and no code enforced.
    """
    for r, tag in ((a, "a"), (b, "b")):
        if not r.get("settled"):
            return Answer(False, "ab", f"run {tag} is not settled: "
                                       f"{r.get('settle_reasons')}", {})
        if r.get("run_type", "calm_resistance") != "calm_resistance":
            return Answer(False, "ab", f"run {tag} is a "
                                       f"{r.get('run_type')} record", {})
    if abs(float(a["speed_ms"]) - float(b["speed_ms"])) > 1e-6:
        return Answer(False, "ab", "different speeds — that is a speed "
                                   "comparison, not a geometry one", {})
    ca, cb = float(a.get("cells") or 0), float(b.get("cells") or 0)
    if ca <= 0 or cb <= 0:
        return Answer(False, "ab", "a run with no recorded cell count "
                                   "cannot be shown to share a mesh", {})
    mesh_gap = abs(ca - cb) / max(ca, cb)
    if mesh_gap > AB_CELL_TOL:
        return Answer(False, "ab",
                      f"meshes differ by {100 * mesh_gap:.0f}% "
                      f"({ca:.0f} vs {cb:.0f} cells) — a delta measured "
                      f"across them is not attributable to geometry",
                      {"mesh_gap": mesh_gap})
    ta, tb = float(a["total_n"]), float(b["total_n"])
    delta = abs(ta - tb) / max(ta, tb)
    if delta < WINDOW_SCATTER:
        return Answer(False, "ab",
                      f"the delta is {100 * delta:.1f}% against a "
                      f"{100 * WINDOW_SCATTER:.1f}% window scatter — "
                      f"unresolved; report a direction, never a number",
                      {"delta": delta, "mesh_gap": mesh_gap})
    return Answer(True, "ab",
                  f"comparable: meshes within {100 * mesh_gap:.1f}%, delta "
                  f"{100 * delta:.1f}% above the {100 * WINDOW_SCATTER:.1f}% "
                  f"scatter", {"delta": delta, "mesh_gap": mesh_gap})


def start_is_survivable(speed_ms: float, lwl_m: float,
                        ramped: bool = False) -> Answer:
    """Will an impulsive start survive at this Froude number?

    MEASURED: three 11-kn attempts (Fn 0.53) died at t ~ 0.045 s at
    n_layers 10, 8 AND 5 with deltaT collapsing to 1e-105 while one
    cell's Courant held ~10 — the pathological-cell signature. The fix is
    a velocity RAMP; backing off layers is measured NOT to help, so the
    ladder should not be walked here.
    """
    if lwl_m <= 0 or speed_ms <= 0:
        return Answer(False, "start", "speed and length must be positive", {})
    fn = speed_ms / math.sqrt(G_STANDARD * lwl_m)
    if fn <= FN_IMPULSIVE_MAX or ramped:
        return Answer(True, "start",
                      f"Fn {fn:.2f}" + (" with a ramped inlet" if ramped
                                        else " — impulsive start is fine"),
                      {"fn": fn})
    return Answer(False, "start",
                  f"Fn {fn:.2f} is above the measured impulsive-start "
                  f"ceiling {FN_IMPULSIVE_MAX}: three attempts at n_layers "
                  f"10, 8 and 5 all died at t ~ 0.045 s. Ramp the inlet "
                  f"velocity (and keep the outlet PASSIVE — a ramped inlet "
                  f"against a forced outlet drains the tank at t ~ 8e-4 s); "
                  f"do not spend rungs on layer backoff here",
                  {"fn": fn})


# ---------------------------------------------------------------------------
# WHEN TO STOP, AND WHEN TO KEEP PAYING
# ---------------------------------------------------------------------------

def more_time_will_help(result: dict) -> Answer:
    """Should this run be EXTENDED, or is its error something time cannot
    fix?

    THE MEASURED DISTINCTION, and it is worth real hours in both
    directions:

      * `runs/hookprobe_v3_10kn` stopped at 32 s because 32 s was the
        TARGET, with 11.5% drift and forces still climbing — a run
        abandoned mid-transient, whose number was then quoted as
        UNDER-RUN. Time would have helped and was not spent.
      * `runs/kcs_s1` reached 3.40 flow-throughs with drift collapsed to
        0.31% and E%D still -43.5% — converged to the wrong number.
        CLAUDE.md's operational conclusion: "do not spend another 16 h on
        a longer solve expecting the number to move." Time would NOT have
        helped and might have been spent.

    So the answer is not "is it settled" but "is it still MOVING": a run
    whose drift is falling window over window is converging and deserves
    its extension; one whose drift is already inside the bar has finished
    and owes its error to physics or mesh, not duration.
    """
    drift = float(result.get("drift", float("nan")))
    prev = float(result.get("prev_drift", float("nan")))
    settled = bool(result.get("settled"))
    if settled:
        return Answer(False, "extend",
                      "the run is settled — a longer solve cannot move a "
                      "number whose transient has already washed out; if "
                      "it disagrees with reference data the error is "
                      "physics or mesh, not duration", {"drift": drift})
    if drift != drift:
        return Answer(False, "extend",
                      "no drift measurement — extend nothing on an "
                      "unmeasured signal", {})
    if prev == prev and drift < prev:
        return Answer(True, "extend",
                      f"drift is FALLING ({100 * prev:.1f}% -> "
                      f"{100 * drift:.1f}%): the transient is still washing "
                      f"out and the run should continue to convergence, not "
                      f"stop at a target time", {"drift": drift, "prev": prev})
    if prev == prev and drift >= prev:
        return Answer(False, "extend",
                      f"drift is NOT falling ({100 * prev:.1f}% -> "
                      f"{100 * drift:.1f}%): more time is buying more of the "
                      f"same. Look at the mesh, the start or the physics",
                      {"drift": drift, "prev": prev})
    return Answer(True, "extend",
                  f"drift {100 * drift:.1f}% with no earlier window to "
                  f"compare — extend once and re-measure", {"drift": drift})


#: deltaT below this fraction of its own healthy value, while the Courant
#: number stays high, is the pathological-cell signature: no timestep can
#: fix a cell whose local Courant will not fall, so the adaptive
#: controller shrinks dt to underflow. MEASURED across the 11-kn deaths
#: (1e-105..1e-26 against a healthy 1e-3) and the KCS n=7 death
#: (1.2e-3 -> 2.5e-26).
DT_COLLAPSE_FRACTION = 1e-6

#: A Courant number this high WHILE dt collapses says the limiter is
#: fighting one cell, not the flow. Measured 9-12 on the KCS death and
#: ~10 on the 11-kn deaths.
COURANT_STUCK = 5.0


def diagnose_divergence(dt_now: float, dt_healthy: float,
                        courant_max: float) -> Answer:
    """Name the failure while the solve is still running.

    The campaign lost three runs and ~100 minutes of re-meshing to a
    signature a human had to read out of `log.interFoam`: deltaT
    collapsing toward underflow while Courant max stays high. That is a
    PATHOLOGICAL CELL — a geometry/mesh fault no timestep can repair —
    and it is distinguishable, live, from a merely slow solve.

    Returns ok=True when the solve looks healthy; a REFUSAL carries the
    named failure class so a campaign loop can stop instead of resuming
    into the same death (the "a crash is not a nap" rule, applied to the
    signature rather than to the exit code).
    """
    if dt_healthy <= 0:
        return Answer(False, "divergence",
                      "no healthy dt to compare against", {})
    ratio = dt_now / dt_healthy
    if ratio < DT_COLLAPSE_FRACTION and courant_max > COURANT_STUCK:
        return Answer(False, "divergence",
                      f"PATHOLOGICAL CELL: dt has collapsed to {ratio:.1e} "
                      f"of its healthy value while Courant max holds at "
                      f"{courant_max:.1f}. No timestep can fix a cell whose "
                      f"local Courant will not fall — stop, do not resume, "
                      f"and change the mesh or ramp the start",
                      {"dt_ratio": ratio, "courant": courant_max})
    if ratio < DT_COLLAPSE_FRACTION:
        return Answer(False, "divergence",
                      f"dt collapsed to {ratio:.1e} of healthy with Courant "
                      f"{courant_max:.1f} — falling Courant means the "
                      f"limiter is working, but this dt cannot finish a run",
                      {"dt_ratio": ratio, "courant": courant_max})
    return Answer(True, "divergence",
                  f"dt at {ratio:.2f} of healthy, Courant {courant_max:.1f} "
                  f"— no collapse signature", {"dt_ratio": ratio})
