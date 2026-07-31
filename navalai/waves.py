"""Environmental boundary conditions (original plan, Phase 3 — built per the
research verdict: climatological spectra, not forecast models).

JONSWAP spectrum (fetch-limited seas — the Black Sea's short steep chop is
the textbook case) + riverine wake preset, and the spectral seakeeping
response: S_response(w) = |RAO(w)|^2 * S_wave(w).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

G = 9.80665


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


@dataclass(frozen=True)
class ResponseReport:
    sea: SeaState
    m0_wave: float
    hs_heave: float          # significant heave response [m]
    rao_peak: float
    rao_at_peak_freq: float


def heave_response(omegas: np.ndarray, rao: np.ndarray,
                   sea: SeaState) -> ResponseReport:
    """Spectral heave response from an RAO curve and a sea state."""
    s_wave = jonswap(omegas, sea)
    s_resp = np.abs(rao) ** 2 * s_wave
    m0w = float(np.trapezoid(s_wave, omegas))
    m0r = float(np.trapezoid(s_resp, omegas))
    i_peak = int(np.argmin(np.abs(omegas - sea.wp)))
    return ResponseReport(sea, m0w, 4.0 * np.sqrt(max(m0r, 0.0)),
                          float(np.max(np.abs(rao))),
                          float(np.abs(rao[i_peak])))
