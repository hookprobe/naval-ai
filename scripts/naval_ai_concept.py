"""naval-ai-concept.stl — the owner's coastal/inland axe-bow twin-demihull
vessel, designed WAKE-FIRST and analysed end-to-end.

The owner's third protocol (2026-08-25) asks for a named test artifact that
validates the whole chain: geometry → hydrostatics → propulsion → drag →
efficiency, for the hybrid class: wave-piercing axe bow → deep-V →
progressive chine separation → twin stern demihulls around a CENTRAL
PROTECTED PROPULSOR, flat stern keel, shallow draft, fins for directional
stability. `scripts/hookprobe_hull.py` is the geometric kernel (fair-spline
lines, C2 morphs, the ≤10° tunnel-divergence criterion); this script drives
it PROPULSION-FIRST, per §19 of the co-design protocol
(`docs/research/PROPULSION-INTEGRATION.md` §6):

    drag estimate → thrust → disc size (loading bar) →
    channel width set so the disc overlaps 10–15% into each demihull →
    rebuild hull → refloat → re-estimate drag → repeat to fixed point.

The 10–15% overlap is the owner's STARTING variable, not a rule — the value
used is printed and stored, and CFD ranking of alternatives (5/10/15/20%)
is recorded as owed, exactly like the Coandă-attachment hypothesis: the
geometry organizes flow toward the central stern region BY DESIGN, and
whether it stays attached is a CFD question this script does not pretend to
answer (protocol §13: "DO NOT ASSUME THE COANDĂ EFFECT IS OCCURRING").

Tier honesty: hydrostatics and all clearances are computed geometry (L0/L1);
drag is an ITTC-57 friction estimate carried as a BAND (form factor 1.15 to
1.45 — displacement-craft practice; no single number is claimed) and the
RANS anchor for this speed class (runs/hb19_7kn: total = 1.57 × the Michell
L1 prediction at 7 kn, measured 2026-08-25 on houseboat19) is reported
beside it, not silently applied. RANS on THIS geometry is owed.

Usage:
    python scripts/naval_ai_concept.py [--out data/exports]
                                       [--mass 14000] [--cruise-kn 7]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import hookprobe_hull as hp  # noqa: E402  (the geometric kernel)
import hull_kb_reconstruct as rk  # noqa: E402  (render + slice machinery)
from navalai import mesh_repair, propulsion  # noqa: E402
from navalai.constants import NU_SEA_15C as KIN_VISC  # noqa: E402
from navalai.energy import EnergySpec  # noqa: E402
from navalai.geometry import RHO_WATER  # noqa: E402

FORM_FACTOR_BAND = (1.15, 1.45)   # displacement-craft (1+k) practice band
THRUST_DEDUCTION = 0.08     # t, stated assumption for a tunnel-protected pod
OVERLAP_TARGET = 0.125      # per-side disc overlap into each demihull (§11)
PROP_TIP_WL_MARGIN = 0.10   # tip must sit at least 0.1 D below the DWL


def ittc57_cf(re: float) -> float:
    return 0.075 / (math.log10(re) - 2.0) ** 2


def drag_band_n(wetted_m2: float, lwl_m: float, u_ms: float) -> tuple[float, float]:
    re = u_ms * lwl_m / KIN_VISC
    rf = 0.5 * RHO_WATER * u_ms ** 2 * wetted_m2 * ittc57_cf(re)
    return FORM_FACTOR_BAND[0] * rf, FORM_FACTOR_BAND[1] * rf


def crown_and_keel_at(h, s: float) -> tuple[float, float]:
    """Tunnel crown z (centreline region) and demihull keel z at station s."""
    p = h.section(s)                       # (N,2) y,z of the half-section
    centre = p[np.abs(p[:, 0]) <= 0.25 * max(h.tunnel_half(np.array([s]))[0], 0.05)]
    crown = float(centre[:, 1].max()) if len(centre) else float(p[:, 1].max())
    return crown, float(p[:, 1].min())


# OWNER CORRECTION, OPEN (2026-08-25, on the first naval-ai-concept.stl):
# "the deep v hull needs to extend for about 70-80% of the length and the
# demihull the rest." The kernel's x_split=0.68 leaves only the forward 32%
# as the single body — inverted against that directive. MEASURED attempts
# the same day, both REFUSED by the watertightness check:
#   x_split 0.28 / x_full 0.06, fin_x1 0.225 →  8 self-intersections
#   x_split 0.28 / x_full 0.10, fin_x1 0.095 → 635 true pairs, spread over
#     x/L 0.0-0.4 at all heights — the wet-deck/topside loft FOLDS when the
#     tunnel opens this fast; it is not a skeg-local defect.
# The narrow wake-first channel clears the ≤10° divergence bar over the
# shorter morph (8.2° measured), so the FLOW criterion admits the owner's
# split; what refuses it is the LOFT — the arch/wet-deck morphs in
# hookprobe_hull.py assume a long transition. Moving the split aft needs
# kernel work (re-derive the arch morph for short spans), not a parameter
# push. Until then the kernel-default split ships, because an artifact that
# fails its own §29 checks must not be the named deliverable.
def build(tunnel_half: float) -> "hp.Hookprobe":
    return hp.Hookprobe(tunnel_half_max=tunnel_half)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/exports")
    ap.add_argument("--mass", type=float, default=14000.0)
    ap.add_argument("--cruise-kn", type=float, default=7.0)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    renders = REPO / "renders" / "hull_kb"
    u = a.cruise_kn * 0.514444
    spec = EnergySpec()
    s_prop = 0.06                          # prop plane, just fwd of transom

    # ---- wake-first fixed point: prop sizes the channel -------------------
    tunnel_half = 0.70                     # kernel default, first guess
    D = None
    for it in range(6):
        h = build(tunnel_half)
        wl = hp.float_to(h, a.mass)
        r = hp.hydrostatics(h, wl, ns=161)
        rlo, rhi = drag_band_n(r["wetted_m2"], h.loa, u)
        thrust = 0.5 * (rlo + rhi) / (1.0 - THRUST_DEDUCTION)
        d_min = propulsion.min_prop_diameter_m(thrust)
        d_new = 1.10 * d_min               # 10% margin over the loading bar
        # §11: channel = D - 2 * overlap  →  the propulsion sets the stern
        chan = d_new * (1.0 - 2.0 * OVERLAP_TARGET)
        if D is not None and abs(d_new - D) < 1e-3:
            D = d_new
            break
        D, tunnel_half = d_new, chan / 2.0
    h = build(tunnel_half)
    wl = hp.float_to(h, a.mass)
    r = hp.hydrostatics(h, wl, ns=161)
    rlo, rhi = drag_band_n(r["wetted_m2"], h.loa, u)
    thrust = 0.5 * (rlo + rhi) / (1.0 - THRUST_DEDUCTION)

    # ---- geometry artifact -------------------------------------------------
    stl = out / "naval-ai-concept.stl"
    hp.write_stl(h, stl)
    V, T, rep = mesh_repair.repair(str(stl))
    with open(stl, "w") as f:              # rewrite repaired, same as kernel
        f.write("solid naval-ai-concept\n")
        for t in T:
            p0, p1, p2 = V[t[0]], V[t[1]], V[t[2]]
            nn = np.cross(p1 - p0, p2 - p0)
            ln = np.linalg.norm(nn)
            nn = nn / ln if ln > 0 else nn
            f.write(f" facet normal {nn[0]:.6e} {nn[1]:.6e} {nn[2]:.6e}\n"
                    "  outer loop\n")
            for v in (p0, p1, p2):
                f.write(f"   vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("  endloop\n endfacet\nendsolid naval-ai-concept\n"
                    if t is T[-1] else "  endloop\n endfacet\n")
    chk = mesh_repair.diagnose(str(stl))
    watertight = not {k: v for k, v in chk.found.items() if v}

    # ---- hydrostatics ------------------------------------------------------
    kg = 0.55 * h.depth - h.t_mid          # kernel's loaded-VCG assumption
    gm = r["kb_m"] + r["bm_m"] - kg
    draft_mid = wl - float(h.keel_z(np.array([h.x_bmax]))[0])
    draft_stem = wl - float(h.keel_z(np.array([1.0]))[0])
    draft_over_skegs = wl + h.t_stem       # skegs reach the axe depth

    # ---- propulsion integration (geometry tier) ---------------------------
    crown, keel_p = crown_and_keel_at(h, s_prop)
    column = wl - keel_p                   # water above demihull keel plane
    recess = max(0.0, crown - wl)          # tunnel recess above the DWL
    d_max = propulsion.max_prop_diameter_m(column, recess, 0.0)  # no hang:
    # the disc stays ABOVE the keel/skeg plane — that is the protection
    axis_z = wl - (0.5 * D + PROP_TIP_WL_MARGIN * D)
    tip_lo, tip_hi = axis_z - 0.5 * D, axis_z + 0.5 * D
    grounding_margin = tip_lo - (-h.t_stem)   # skegs are the deepest point
    chan_meas = 2.0 * float(h.tunnel_half(np.array([s_prop]))[0])
    overlap_frac = (D - chan_meas) / (2.0 * D)
    # keel slope over the run approaching the disk (§8 of the protocol)
    s_run = np.linspace(s_prop, s_prop + 0.15, 20)
    zk = h.keel_z(s_run)
    keel_slope_deg = math.degrees(math.atan2(float(zk[-1] - zk[0]),
                                             float(0.15 * h.loa)))
    # the morph's divergence half-angle — the "no water funnel" bar (§15)
    morph_span = (h.x_split - h.x_full) * h.loa
    divergence_deg = math.degrees(math.atan(
        1.875 * h.tunnel_half_max / morph_span))
    tr_im = wl - float(h.keel_z(np.array([0.0]))[0])
    fn_t = propulsion.transom_froude(u, tr_im)

    # ---- drag band and efficiency -----------------------------------------
    p_el_lo = rlo * u / (spec.prop_efficiency * spec.motor_efficiency)
    p_el_hi = rhi * u / (spec.prop_efficiency * spec.motor_efficiency)
    wh_per_nm = (p_el_lo / a.cruise_kn, p_el_hi / a.cruise_kn)
    motor_frac = p_el_hi / (spec.motor_kw * 1e3)

    # ---- §29 failure conditions, checked not narrated ---------------------
    checks = {
        "watertight_manifold": watertight,
        "positive_GM": gm > 0.0,
        "prop_fits_disc_room": D <= d_max,
        "prop_tip_protected_above_skeg_plane": grounding_margin > 0.0,
        "prop_tip_submerged_at_rest": tip_hi < wl - 0.02,
        "overlap_in_target_band": 0.05 <= overlap_frac <= 0.20,
        "divergence_under_10deg": divergence_deg <= 10.0,
        "shallow_draft_under_1p5m": draft_over_skegs <= 1.5,
        "cruise_within_motor_continuous": motor_frac
        <= propulsion.MOTOR_CONTINUOUS_FRACTION,
        "topology_1_to_2_flow_bodies":
            rk.section_loops_at(V, T, V[:, 0].min() + 0.9 *
                                (V[:, 0].max() - V[:, 0].min()),
                                lower_frac=0.35) == 1
            and rk.section_loops_at(V, T, V[:, 0].min() + 0.1 *
                                    (V[:, 0].max() - V[:, 0].min()),
                                    lower_frac=0.35) == 2,
    }

    report = {
        "artifact": str(stl),
        "mission": {"loa_m": h.loa, "mass_kg": a.mass,
                    "cruise_kn": a.cruise_kn,
                    "waters": "coastal/inland (rivers, canals, lakes, "
                              "deltas, estuaries)"},
        "wake_first": {"overlap_target_per_side": OVERLAP_TARGET,
                       "iterations": it + 1,
                       "tunnel_half_m": round(tunnel_half, 3)},
        "geometry": {"watertight_manifold": watertight,
                     "n_tris": int(rep.n_tris_after),
                     "repairs": list(rep.applied)},
        "hydrostatics": {"dwl_z_m": round(wl, 3),
                         "draft_midships_m": round(draft_mid, 3),
                         "draft_stem_m": round(draft_stem, 3),
                         "draft_over_skegs_m": round(draft_over_skegs, 3),
                         "bwl_m": round(r["bwl_m"], 2),
                         "awp_m2": round(r["awp_m2"], 1),
                         "wetted_m2": round(r["wetted_m2"], 1),
                         "kb_m": round(r["kb_m"], 3),
                         "bm_m": round(r["bm_m"], 3),
                         "gm_m": round(gm, 3)},
        "propulsion": {
            "prop_diameter_m": round(D, 3),
            "d_min_loading_bar_m": round(propulsion.min_prop_diameter_m(thrust), 3),
            "d_max_disc_room_m": round(d_max, 3),
            "channel_width_m": round(chan_meas, 3),
            "overlap_per_side_frac_of_D": round(overlap_frac, 3),
            "axis_z_m": round(axis_z, 3),
            "tip_grounding_margin_above_skeg_plane_m": round(grounding_margin, 3),
            "tunnel_recess_above_dwl_m": round(recess, 3),
            "keel_slope_at_disk_deg": round(keel_slope_deg, 1),
            "morph_divergence_half_angle_deg": round(divergence_deg, 1),
            "transom_froude_at_cruise": round(fn_t, 2)
            if math.isfinite(fn_t) else "dry",
            "shaft_angle_deg": 0.0,
            "skegs": {"x_span_frac": [h.fin_x0, h.fin_x1],
                      "depth_m": h.t_stem,
                      "role": "lateral area / directional stability; "
                              "roll stiffness comes from the demihulls"},
            "deployable_fin_attachment": {
                "position": "demihull outer chine, over the skeg span",
                "area_span_chord_angle": "FREE optimization variables (§18)"},
        },
        "drag_efficiency": {
            "tier": "L0 ITTC-57 friction x form-factor BAND — not a claim",
            "form_factor_band": FORM_FACTOR_BAND,
            "resistance_band_n": [round(rlo), round(rhi)],
            "thrust_n_with_t_0.08": round(thrust),
            "p_electric_band_kw": [round(p_el_lo / 1e3, 2),
                                   round(p_el_hi / 1e3, 2)],
            "wh_per_nm_band": [round(wh_per_nm[0]), round(wh_per_nm[1])],
            "motor_fraction_at_cruise_hi": round(motor_frac, 2),
            "rans_anchor": "runs/hb19_7kn measured total = 1.57 x Michell L1 "
                           "at 7 kn on houseboat19 — RANS on THIS geometry "
                           "is OWED, as is CFD proof of the flow-attachment "
                           "hypothesis (protocol §13-14)",
        },
        "checks": checks,
        "all_checks_pass": bool(all(checks.values())),
    }

    # ---- renders (§26 exterior + propulsion views) ------------------------
    views = rk.render_stl_views(V, T, renders, "concept")
    # stern view with the propeller disk drawn where it will swing
    fig, ax = plt.subplots(figsize=(7, 5))
    x0 = V[:, 0].min()
    tri = V[T]
    xs = tri[:, :, 0]
    x_cut = x0 + s_prop * (V[:, 0].max() - x0)
    keep = (xs.min(1) <= x_cut) & (xs.max(1) >= x_cut)
    for t in tri[keep]:
        pts = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            xa, xb = t[i, 0], t[j, 0]
            if (xa - x_cut) * (xb - x_cut) <= 0 and xa != xb:
                w = (x_cut - xa) / (xb - xa)
                pts.append(t[i] + w * (t[j] - t[i]))
        if len(pts) >= 2:
            ax.plot([pts[0][1], pts[1][1]], [pts[0][2], pts[1][2]],
                    "k-", lw=0.7)
    th = np.linspace(0, 2 * math.pi, 100)
    ax.plot(0.5 * D * np.cos(th), axis_z + 0.5 * D * np.sin(th), "r-",
            lw=1.6, label=f"prop disk D={D:.2f} m")
    ax.axhline(wl, color="c", lw=0.8, label="DWL")
    ax.axhline(-h.t_stem, color="g", lw=0.8, ls="--", label="skeg plane")
    ax.set_aspect("equal"); ax.legend(fontsize=7)
    ax.set_title("concept — propulsion section at the prop plane")
    p = renders / "concept-propsection.png"
    fig.savefig(p, dpi=130, bbox_inches="tight"); plt.close(fig)
    views.append(p)

    # the station story (§23-24): 13 sections, bow to stern
    fig, axes = plt.subplots(3, 5, figsize=(15, 8))
    fr = [1.0, 0.95, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05, 0.0]
    for k, f in enumerate(fr):
        ax = axes.flat[k]
        s = max(min(f, 1.0), 0.0)
        pcs = h.section(s)
        ax.plot(pcs[:, 0], pcs[:, 1], "k-", lw=1.0)
        ax.plot(-pcs[:, 0], pcs[:, 1], "k-", lw=1.0)
        ax.axhline(wl, color="c", lw=0.6)
        ax.set_aspect("equal"); ax.set_title(f"x/L={f:.2f} (bow=1)", fontsize=8)
        ax.tick_params(labelsize=6)
    for k in range(len(fr), len(axes.flat)):
        axes.flat[k].axis("off")
    fig.suptitle("naval-ai-concept — the station story: axe entry → deep-V → "
                 "chine development → split → twin demihulls + channel")
    p = renders / "concept-stations.png"
    fig.savefig(p, dpi=130, bbox_inches="tight"); plt.close(fig)
    views.append(p)
    report["renders"] = [str(v) for v in views]

    def _py(o):
        return o.item() if hasattr(o, "item") else str(o)
    (out / "naval-ai-concept-report.json").write_text(
        json.dumps(report, indent=2, default=_py))
    print(json.dumps(report, indent=2, default=_py))
    return 0 if report["all_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
