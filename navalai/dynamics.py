"""Rigid-body dynamics plane (original plan, Phase 3, research-scoped):
mass moments of inertia, mooring loads, lifting-sling loads. MuJoCo is used
as an independent cross-check engine for the inertia pipeline (pendulum
period), NOT for hydrodynamics (it has no free surface — BuildPlan 1.3).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .energy import WeightBudget
from .geometry import G, Hull

RHO_AIR = 1.225
CD_LATERAL = 1.0        # bluff-body lateral drag, approx
CD_CURRENT = 1.0


@dataclass(frozen=True)
class InertiaReport:
    mass: float
    ixx: float           # roll  [kg m^2]
    iyy: float           # pitch [kg m^2]
    izz: float           # yaw   [kg m^2]
    kxx: float           # roll gyradius / beam
    kyy: float           # pitch gyradius / LWL


def inertia(hull: Hull, wb: WeightBudget) -> InertiaReport:
    """Component-lumped inertia about the composite CG.

    Masses: structure smeared over the shell strip-wise, battery low amidship,
    panels at deck, outfit + payload mid-depth — same stack as the VCG model.
    """
    L = float(hull.x[-1])
    B = 2.0 * float(hull.y_chine.max())
    D = float(hull.z_sheer.max() - hull.z_keel.min())
    m = wb.total_kg
    parts = [
        # (mass, x, z, own gyradius fractions rx(of B), ry(of L))
        (wb.structure_kg, 0.50 * L, 0.55 * D, 0.40, 0.29),
        (wb.battery_kg,   0.45 * L, 0.15 * D, 0.25, 0.05),
        (wb.panel_kg,     0.50 * L, 1.00 * D, 0.45, 0.30),
        (wb.outfit_kg,    0.50 * L, 0.60 * D, 0.30, 0.25),
        (wb.payload_kg,   0.55 * L, 0.70 * D, 0.30, 0.15),
    ]
    xg = sum(mm * x for mm, x, *_ in parts) / m
    zg = sum(mm * z for mm, _x, z, *_ in parts) / m
    ixx = sum(mm * ((rx * B) ** 2 + (z - zg) ** 2) for mm, _x, z, rx, _ry in parts)
    iyy = sum(mm * ((ry * L) ** 2 + (x - xg) ** 2 + (z - zg) ** 2)
              for mm, x, z, _rx, ry in parts)
    izz = sum(mm * ((ry * L) ** 2 + (rx * B) ** 2 + (x - xg) ** 2)
              for mm, x, _z, rx, ry in parts)
    return InertiaReport(m, ixx, iyy, izz,
                         math.sqrt(ixx / m) / B, math.sqrt(iyy / m) / L)


@dataclass(frozen=True)
class MooringReport:
    wind_force_n: float
    current_force_n: float
    line_tension_n: float
    safety_factor_vs: float   # line MBL the tension implies at SF=5


def mooring(hull: Hull, wind_ms: float = 25.0, current_ms: float = 1.5,
            line_angle_deg: float = 30.0) -> MooringReport:
    """Single bow line, storm wind + river current abeam-worst-case."""
    L = float(hull.x[-1])
    lateral_above = 2.0 * float(np.trapezoid(
        np.maximum(hull.z_sheer, 0.0), hull.x))          # windage area approx
    lateral_below = float(np.trapezoid(
        np.maximum(-hull.z_keel, 0.0), hull.x))
    fw = 0.5 * RHO_AIR * CD_LATERAL * lateral_above * wind_ms**2
    fc = 0.5 * 1000.0 * CD_CURRENT * lateral_below * current_ms**2
    total = fw + fc
    tension = total / math.cos(math.radians(line_angle_deg))
    return MooringReport(fw, fc, tension, 5.0 * tension)


@dataclass(frozen=True)
class LiftReport:
    weight_n: float
    sling_angle_deg: float
    tension_per_sling_n: float
    required_wll_kg: float    # per sling at SF=4


def lifting(mass_kg: float, sling_angle_deg: float = 30.0) -> LiftReport:
    """Two-sling crane lift; angle measured from vertical."""
    w = mass_kg * G
    t = w / (2.0 * math.cos(math.radians(sling_angle_deg)))
    return LiftReport(w, sling_angle_deg, t, 4.0 * t / G)


# ---------------- MuJoCo cross-check ----------------

def pendulum_period_mujoco(mass: float, iyy_cg: float, d: float,
                           sim_time: float = 20.0) -> float:
    """Swing a body of (mass, Iyy about its CG) on a hinge d metres above the
    CG in MuJoCo; return the measured small-oscillation period.

    Analytic truth: T = 2 pi sqrt((Iyy + m d^2) / (m g d)). If our inertia
    pipeline and MuJoCo disagree, one of us is wrong — that is the point.
    """
    import mujoco

    gyr2 = iyy_cg / mass
    # inertial ellipsoid: encode Iyy via diaginertia (others irrelevant to 1-D swing)
    xml = f"""
    <mujoco>
      <option gravity="0 0 -{G}" timestep="0.001"/>
      <worldbody>
        <body name="b" pos="0 0 0">
          <joint name="h" type="hinge" axis="0 1 0" pos="0 0 {d}"/>
          <inertial pos="0 0 0" mass="{mass}"
                    diaginertia="{gyr2 * mass} {gyr2 * mass} {gyr2 * mass}"/>
          <geom type="sphere" size="0.05" density="0"/>
        </body>
      </worldbody>
    </mujoco>"""
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    data.qpos[0] = 0.05                       # 2.9 deg: small oscillation
    crossings = []
    prev = data.qpos[0]
    steps = int(sim_time / model.opt.timestep)
    for _ in range(steps):
        mujoco.mj_step(model, data)
        cur = data.qpos[0]
        if prev < 0.0 <= cur:
            t = data.time
            crossings.append(t)
        prev = cur
    if len(crossings) < 3:
        raise RuntimeError("pendulum did not oscillate")
    periods = np.diff(crossings)
    return float(np.mean(periods))


def pendulum_period_analytic(mass: float, iyy_cg: float, d: float) -> float:
    return 2.0 * math.pi * math.sqrt((iyy_cg + mass * d * d) / (mass * G * d))
