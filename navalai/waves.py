"""Environmental boundary conditions (original plan, Phase 3 — built per the
research verdict: climatological spectra, not forecast models).

OWNERSHIP (C-26): this module owns the SEAWAY (spectra, wave statistics,
the environment the boat sits in); `navalai.seakeeping` owns the RESPONSE
(added mass, damping, RAO tiers L0/L2). `waves.heave_response` is the
1-DOF closed-form bridge between them and reads seakeeping coefficients —
it does not re-derive them. RESEARCH module: consumed by experiments and
docs/research, not by the evaluate ladder.

JONSWAP spectrum (fetch-limited seas — the Black Sea's short steep chop is
the textbook case) + riverine wake preset, and the spectral seakeeping
response: S_response(w) = |RAO(w)|^2 * S_wave(w).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .constants import G_STANDARD as G


@dataclass(frozen=True)
class SeaState:
    name: str
    hs: float      # significant wave height [m]
    tp: float      # peak period [s]
    gamma: float   # JONSWAP peak enhancement

    @property
    def wp(self) -> float:
        return 2.0 * np.pi / self.tp


# presets: category context (ISO) + local knowledge encoded as data
BLACK_SEA_COASTAL = SeaState("black-sea coastal (cat C)", 2.0, 5.5, 3.3)
BLACK_SEA_INSHORE = SeaState("black-sea inshore", 1.0, 4.5, 3.3)
DANUBE_WAKE = SeaState("danube barge wake", 0.35, 2.8, 2.0)
CALM_RIVER = SeaState("calm river (cat D)", 0.25, 2.2, 1.5)


def jonswap(omega: np.ndarray, sea: SeaState) -> np.ndarray:
    """JONSWAP S(omega) [m^2 s], numerically normalised so m0 = Hs^2 / 16."""
    w = np.asarray(omega, float)
    wp = sea.wp
    sigma = np.where(w <= wp, 0.07, 0.09)
    r = np.exp(-((w - wp) ** 2) / (2.0 * sigma**2 * wp**2))
    base = np.where(w > 1e-9,
                    w**-5 * np.exp(-1.25 * (wp / np.maximum(w, 1e-9)) ** 4), 0.0)
    s = base * sea.gamma**r
    m0 = np.trapezoid(s, w)
    target = sea.hs**2 / 16.0
    return s * (target / max(m0, 1e-30))


def encounter_omega(omega: np.ndarray, speed: float = 0.0,
                    heading_deg: float = 180.0) -> np.ndarray:
    """Encounter frequency [rad/s] in deep water.

        w_e = w - (w^2 U / g) cos(mu)

    `heading_deg` is the wave heading relative to the ship's heading:
    **180 = head seas** (waves running at the bow), 90 = beam, 0 = following.
    That is the naval-architecture convention, so cos(180 deg) = -1 gives
    w_e > w for head seas, which is the sign every seakeeping text prints.

    The returned value is SIGNED. In following seas w_e passes through zero
    and goes negative — the ship overtakes the waves — and the sign is kept
    rather than absorbed, because `heave_response` has to know that the map
    w -> w_e stopped being one-to-one. See `ResponseReport.following_sea_fold`.
    """
    w = np.asarray(omega, float)
    return w - (w**2) * float(speed) * np.cos(np.radians(heading_deg)) / G


@dataclass(frozen=True)
class ResponseReport:
    sea: SeaState
    m0_wave: float
    hs_heave: float          # significant heave response [m]
    rao_peak: float
    rao_at_peak_freq: float
    # The frame the RAO was evaluated in, so a reader can tell a zero-speed
    # answer from a transformed one instead of having to guess (gap F5).
    speed: float = 0.0
    heading_deg: float = 180.0
    omega_e_peak: float = 0.0       # encounter frequency at the spectral peak
    # True when w_e(w) is not monotone over the frequency set, i.e. following
    # seas where three wave frequencies share one encounter frequency. The
    # response is still integrated in ABSOLUTE frequency (which stays
    # single-valued), but a caller reading a following-sea number should know
    # the transform folded.
    following_sea_fold: bool = False


def heave_response(omegas: np.ndarray, rao: np.ndarray, sea: SeaState,
                   speed: float = 0.0,
                   heading_deg: float = 180.0) -> ResponseReport:
    """Spectral heave response from an RAO curve and a sea state.

    AT FORWARD SPEED THE SHIP DOES NOT SEE THE WAVE'S OWN FREQUENCY (gap F5).
    This routine convolved a zero-speed RAO with JONSWAP in ABSOLUTE frequency,
    which is the right answer only at U = 0. MEASURED on the reference hull's
    RAO in the Black Sea coastal state (Hs 2.0 m, Tp 5.5 s) at its 5 kn cruise
    in head seas: the spectral peak sits at w = 1.142 rad/s and is encountered
    at w_e = 1.484 rad/s — **+30%** — which on a small-craft heave RAO is the
    difference between the resonant flank and the far side of it.

    The integral stays in absolute frequency (that is where JONSWAP is defined
    and where the map is single-valued); what moves is WHERE THE RAO IS READ:
    the vessel responds at w_e to a wave of absolute frequency w, so the RAO
    curve — which is indexed by the frequency of oscillation — is interpolated
    at w_e. `speed = 0` reproduces the previous behaviour exactly.

    The RAO is extrapolated flat outside the frequency set it was computed on.
    That is a real limitation and it is stated rather than hidden: a head-sea
    transform pushes w_e above the top of the set, and inventing a resonance
    out there would be worse than holding the last computed value.
    """
    w = np.asarray(omegas, float)
    rao = np.abs(np.asarray(rao, float))
    s_wave = jonswap(w, sea)
    we = encounter_omega(w, speed, heading_deg)
    fold = bool(speed != 0.0 and np.any(np.diff(we) <= 0.0))
    # np.interp needs an increasing x; the RAO is a function of the MAGNITUDE
    # of the oscillation frequency, so |w_e| is what indexes it.
    rao_e = np.interp(np.abs(we), w, rao) if speed != 0.0 else rao
    s_resp = rao_e**2 * s_wave
    m0w = float(np.trapezoid(s_wave, w))
    m0r = float(np.trapezoid(s_resp, w))
    i_peak = int(np.argmin(np.abs(w - sea.wp)))
    return ResponseReport(sea, m0w, 4.0 * np.sqrt(max(m0r, 0.0)),
                          float(np.max(rao_e)),
                          float(rao_e[i_peak]),
                          speed=float(speed), heading_deg=float(heading_deg),
                          omega_e_peak=float(encounter_omega(
                              np.array([sea.wp]), speed, heading_deg)[0]),
                          following_sea_fold=fold)
