"""The HOOKPROBE hull: an axe-bow / catamaran-stern MORPHING hull.

    python scripts/hookprobe_hull.py --out data/exports/houseboat16

THE SHAPE, from `downloads/hull-examples/hookprobe-hull.jpg` (the owner's own
schematic, which is where this design comes from):

    SECTION A-A (stem)      a deep, narrow V -- an axe bow, deep-V entry
    SECTION B-B (midships)  a single U -- rounded bottom, near-vertical sides
    SECTION C-C (stern)     TWIN DEMIHULLS bridged by a WET DECK

and between B and C a MORPHING TRANSITION ZONE where the single hull splits.

WHY THIS IS NOT EXPRESSIBLE IN `navalai.grammar`, stated plainly so nobody
tries to fit it there before the kernel is generalised. The genome carries ONE
moulded surface -- keel, bilge, sheer -- and `geometry._halfbreadth_at`
documents the assumption it rests on: "z increases monotonically along a
section (keel -> bilge -> sheer)", evaluated with `np.interp`. That is a
SINGLE-VALUED y(z): a half-section that starts on the centreline at y = 0 and
walks outboard. Section C-C does not. Aft of the split each half-section spans
y in [t(x), b(x)] -- it starts at the TUNNEL WALL, not at the centreline -- and
the transverse section stops being simply connected. No combination of the 23
genes produces that, because none of them can put a hole in a section.

So the generalisation the kernel needs is an INNER boundary beside the outer
one: area becomes the integral of (y_outer - y_inner) dz, and at t == 0 it
reduces to today's expression exactly. That is the same "0 is a provable no-op"
discipline `r_stem` and `pmb` were appended under, and it is the work this
script exists to justify rather than to replace. Nothing here writes to the
grammar; it draws the shape directly so the FORM can be judged before the
kernel is changed for it.

WHY THE SHAPE SHOULD BE FAST, which is the claim to be tested and not assumed:
  * the deep-V axe entry has its greatest draught forward, so the bow does not
    lift and therefore cannot slam back (Damen's own mechanism, quantified in
    CLAUDE.md's axe-bow notes);
  * the stern's two slender demihulls each carry a much finer L/B than one
    beamy hull of the same displacement, and wave-making falls steeply with
    slenderness at the Fn 0.2-0.35 this boat lives at;
  * the wide demihull separation buys transverse stability from GEOMETRY, so a
    monohull's roll fins are not needed -- which is exactly the owner's rule
    that a multihull does not carry them.
"""
from __future__ import annotations

import argparse
import json
import sys
import math
from pathlib import Path

import numpy as np

# Run as a script from anywhere: the repo root must be importable for
# `navalai.mesh_repair` (the manifold check at the end of main()).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# The one home of both numbers is navalai/constants.py — this script fed the
# C-33 fence its first true positive in scripts/ since hull_form_audit.py.
from navalai.constants import G_STANDARD as G          # noqa: E402
from navalai.geometry import RHO_WATER as RHO          # noqa: E402


# --------------------------------------------------------------------------
# The design curves. x = 0 at the TRANSOM, x = LOA at the STEM, matching
# navalai.geometry's convention so the two can be compared without a flip.
# --------------------------------------------------------------------------

from scipy.interpolate import make_interp_spline


def _fair(ctrl_s, ctrl_v):
    """A C2 cubic B-spline through named control points -> callable on [0,1].

    THE KEEL LINE WAS IRREGULAR AND THE OWNER SAW IT IN THE SIDE VIEW. It was
    built as two quintic ramps stitched at `x_bmax`, and each ramp contributes
    its own S-curve: MEASURED, 3 curvature sign changes and an 8% dead-flat
    patch, where the reference profile is ONE continuous sweep with a single
    inflection. The chine morphs (`turn_frac`, `roundness_at`, `deadrise`) had
    the same construction and the same lumps, which is what made the chine
    transition read as unfair.

    This is the fix the owner suggested and the literature confirms: represent
    a design line as a spline through a few control points, not as stitched
    ramps. Zhu et al. (jmse-11-01816, "Fast Reconstruction Model of the Ship
    Hull NURBS Surface with Uniform Continuity") fit section feature points by
    global interpolation and then skin the surface across the fitted curves;
    `natural` end conditions (zero second derivative) keep the ends from
    ringing. scipy's B-spline basis is the non-rational special case of NURBS,
    which is all a hull this shape needs -- rational weights exist to encode
    exact conics, and nothing here is a circle.
    """
    ctrl_s = np.asarray(ctrl_s, float)
    ctrl_v = np.asarray(ctrl_v, float)
    return make_interp_spline(ctrl_s, ctrl_v, k=3, bc_type="natural")


def _smoothstep(t: np.ndarray) -> np.ndarray:
    """C2 ramp on [0, 1]. Used for every morph so nothing has a crease.

    SMOOTHER-step (6t^5 - 15t^4 + 10t^3), not the classic 3t^2 - 2t^3. The
    cubic is only C1: its SECOND derivative jumps at both ends, and on a hull
    surface a curvature discontinuity is a visible knuckle and a drag line --
    which is what showed at the single-to-twin transition. The quintic has
    zero first AND second derivative at both ends, so the morph leaves and
    arrives with no curvature step.
    """
    t = np.clip(t, 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


class Hookprobe:
    """Axe-bow forward, twin demihulls aft, wet deck over the tunnel."""

    def __init__(self, loa=16.0, bmax=4.0, depth=1.55,
                 t_stem=1.34, t_mid=0.86, t_transom=0.52,
                 # THE BOW WAS TRIMMED. b_stem_frac 0.070 left the stem 280 mm wide, so the
                 # hull ended in a flat vertical face and the axe read as cut
                 # off. An axe bow closes to an EDGE -- 0.008 leaves a 32 mm
                 # stem, which is a real fabricated stem bar rather than a
                 # mathematical point, so the loft stays non-degenerate.
                 x_bmax=0.615, b_transom_frac=0.985, b_stem_frac=0.008,
                 # THE MORPH ZONE IS SIZED BY A FLOW CRITERION, not by eye.
                 # A quintic ramp's peak slope is 1.875*A/span, so opening a
                 # 0.70 m tunnel half-width over 2.08 m (the first version)
                 # gave a 19 deg divergence half-angle and over 5.76 m still
                 # gave 12.8 deg -- both past the ~10 deg where a diffusing
                 # passage separates, which is drag paid for nothing. 7.7 m
                 # brings it under the bar. This is the "smooth out the curve"
                 # the owner asked for, expressed as an angle that can be
                 # checked rather than as a shape that looks nicer.
                 x_split=0.68, x_full=0.20,
                 tunnel_half_max=0.70, wetdeck_frac=0.74,
                 beta_stem=62.0, beta_mid=14.0, beta_demi=22.0,
                 sheer_rise=0.09, roundness=0.55,
                 r_stem_sec=0.04, r_mid_sec=0.72, r_demi_sec=0.86,
                 entrance_pow=1.38,
                 turn_stem=0.97, turn_mid=0.55, turn_demi=0.42,
                 stem_rake_deg=20.0, rake_start=0.72,
                 tunnel_arch=0.55, bilge_radius=0.45,
                 # PLACED WHERE THE DRAWING PUTS THEM -- hard aft, just
                 # forward of the transom, not amidships. The first version
                 # ran them 0.56-5.4 m forward of the transom, which is a
                 # daggerboard's position and not a skeg's.
                 fin_x0=0.015, fin_x1=0.225, fin_half_t=0.040,
                 fin_depth=None):
        self.__dict__.update(locals())
        del self.__dict__["self"]

    # -- the stern fins ------------------------------------------------------
    def fin_bottom(self, s):
        """Underside of the skeg under EACH demihull; NaN where there is none.

        Two things the owner read off the profile view that the geometry did
        not have: a slight RAISE of the run toward the stern for flow, and TWO
        FINS matching the axe depth.

        They belong together. Raising the run helps the flow aft but it throws
        away lateral area exactly where the boat needs it, and this hull has an
        unusually deep forefoot -- so without something aft the centre of
        lateral resistance sits far forward and the boat wants to broach.
        The fins put that area back, and taking them down to the AXE DEPTH
        (`t_stem`) makes the draught uniform: deepest point forward and
        deepest point aft become the same, so the boat sits level on a
        trailer, a slip or the bottom.

        One fin per demihull, on the DEMIHULL's own centreline -- never on the
        hull centreline, which is open tunnel here.
        """
        s = np.asarray(s, float)
        d = self.fin_depth if self.fin_depth is not None else self.t_stem
        span = max(self.fin_x1 - self.fin_x0, 1e-9)
        u = np.clip((s - self.fin_x0) / (0.28 * span), 0.0, 1.0)
        v = np.clip((self.fin_x1 - s) / (0.42 * span), 0.0, 1.0)
        prof = _smoothstep(u) * _smoothstep(v)
        return np.where((s >= self.fin_x0) & (s <= self.fin_x1)
                        & (prof > 1e-6), -d * prof, np.nan)

    # -- longitudinal curves -------------------------------------------------
    def keel_z(self, s):
        """Keel depth below DWL: ONE fair spline sweep, deepest at the stem.

        Control points, transom to stem. The interior two are placed on the
        monotone run between the named draughts so the interpolant cannot
        overshoot them, and the result is verified fair by
        `main()`'s inflection count (1, was 3).
        """
        if not hasattr(self, "_keel_spl"):
            tt, tm, ts = self.t_transom, self.t_mid, self.t_stem
            self._keel_spl = _fair(
                [0.0, 0.30, self.x_bmax, 0.85, 1.0],
                [-tt, -(tt + 0.62 * (tm - tt)), -tm,
                 -(tm + 0.55 * (ts - tm)), -ts])
        return self._keel_spl(np.asarray(s, float))

    def sheer_z(self, s):
        s = np.asarray(s, float)
        base = self.depth - self.t_mid
        rise = self.sheer_rise * self.depth * _smoothstep(
            np.clip((s - 0.55) / 0.45, 0.0, 1.0)) ** 1.4
        return base + rise

    def beam_half(self, s):
        """Sheer half-beam. Wide transom, max near x_bmax, a SPIKE at the stem."""
        s = np.asarray(s, float)
        b = np.empty_like(s)
        fwd = s >= self.x_bmax
        u = (s[fwd] - self.x_bmax) / (1.0 - self.x_bmax)
        # a fine, hollow entrance: power > 1 keeps the waterline straight-ish
        b[fwd] = 0.5 * self.bmax * (
            1.0 - (1.0 - self.b_stem_frac) * u ** self.entrance_pow)
        aft = ~fwd
        # PARALLEL-SIDED AFT BODY. The schematic's demihulls run straight to
        # the transom at constant width -- that is what makes them demihulls
        # and not a tapering stern -- so the aft beam is held flat over the
        # run and only eased in near the max-beam station.
        u = np.clip((self.x_bmax - s[aft]) / max(self.x_bmax - self.x_full,
                                                 1e-9), 0.0, 1.0)
        b[aft] = 0.5 * self.bmax * (
            1.0 - (1.0 - self.b_transom_frac) * _smoothstep(u))
        return b

    def tunnel_half(self, s):
        """Half-width of the wet-deck tunnel. ZERO forward of the split."""
        s = np.asarray(s, float)
        t = np.zeros_like(s)
        m = s <= self.x_split
        u = np.clip((self.x_split - s[m]) / max(self.x_split - self.x_full,
                                                1e-9), 0.0, 1.0)
        t[m] = self.tunnel_half_max * _smoothstep(u)
        return t

    def wetdeck_z(self, s):
        """Underside of the wet deck (the tunnel roof), above the keel."""
        s = np.asarray(s, float)
        k = self.keel_z(s)
        top = self.wetdeck_frac * self.depth - self.t_mid
        u = np.clip((self.x_split - s) / max(self.x_split - self.x_full, 1e-9),
                    0.0, 1.0)
        return k + (top - k) * _smoothstep(u)

    def roundness_at(self, s):
        """Bilge roundness along the length. THE SCHEMATIC MORPHS THIS TOO.

        Section A-A is a SHARP V (an axe entry has straight, deep sections and
        no turn of bilge to speak of); B-B is a U; C-C is two U-shaped
        demihulls. A single `roundness` scalar drew a rounded U everywhere and
        made the axe bow read as a narrow tube rather than a wedge.
        """
        if not hasattr(self, "_rnd_spl"):
            self._rnd_spl = _fair(
                [0.0, 0.32, self.x_bmax, 1.0],
                [self.r_demi_sec, self.r_mid_sec, self.r_mid_sec,
                 self.r_stem_sec])
        return np.clip(self._rnd_spl(np.asarray(s, float)), 0.0, 1.0)

    def turn_frac(self, s):
        """Height of the turn of bilge as a fraction of the section's height.

        THE AXE SECTION IS A V ALL THE WAY UP. A fixed turn height made the
        V occupy only the bottom 0.31 m of a 2.6 m section at the stem, with a
        vertical topside above it -- so section A-A drew as a narrow TUBE and
        not as the wedge the schematic shows. Forward this goes to ~1, which
        puts the turn at the sheer and leaves straight V sides from keel to
        deck; aft it drops so the demihulls keep their U.
        """
        if not hasattr(self, "_turn_spl"):
            self._turn_spl = _fair(
                [0.0, 0.32, self.x_bmax, 1.0],
                [self.turn_demi, self.turn_mid, self.turn_mid, self.turn_stem])
        return np.clip(self._turn_spl(np.asarray(s, float)), 0.02, 0.99)

    def deadrise(self, s):
        if not hasattr(self, "_dead_spl"):
            self._dead_spl = _fair(
                [0.0, 0.32, self.x_bmax, 1.0],
                [self.beta_demi, self.beta_mid, self.beta_mid,
                 self.beta_stem])
        return self._dead_spl(np.asarray(s, float))

    def rake_dx(self, s, z):
        """x-shift that rakes the stem AFT by `stem_rake_deg` (schematic 02).

        `hokprobe-hull02.jpg` adds the one dimension the first drawing left
        implicit: "STEM RAKE ANGLE: 20 deg (BOW RAKED AFT)". Raked AFT is not
        a conventional bow overhang -- it is the REVERSE/INVERTED stem, where
        the top of the stem lies ABAFT the bottom, so the FOREFOOT is the
        furthest-forward point on the boat. That is the whole axe-bow
        mechanism: the deepest, most forward part enters first and stays in,
        which is why the bow does not lift and therefore cannot slam back.

        Implemented as a shear in x that grows with height above the waterline
        and ramps in over the forebody, so the stem profile comes out as a
        STRAIGHT line at 20 deg while the run aft is untouched. Over the ~2.6 m
        from forefoot to deck at the stem this puts the deck edge 2.6*tan(20)
        = 0.95 m abaft the forefoot, which is what the drawing shows.
        """
        s = np.asarray(s, float); z = np.asarray(z, float)
        w = _smoothstep((s - self.rake_start) / max(1.0 - self.rake_start, 1e-9))
        return -z * math.tan(math.radians(self.stem_rake_deg)) * w

    # -- one transverse half-section ----------------------------------------
    def section(self, s, n=48):
        """Closed HALF-section polygon (y >= 0) at s, as an (N, 2) array.

        Below the split this is a solid V/U walked from the centreline
        outboard. Aft of it the walk starts at the TUNNEL WALL and returns
        along the wet deck -- which is the part the moulded-surface kernel
        cannot represent.
        """
        s = float(s)
        zk = float(self.keel_z(s)); zs = float(self.sheer_z(s))
        b = float(self.beam_half(s)); t = float(self.tunnel_half(s))
        beta = math.radians(float(self.deadrise(s)))
        zw = float(self.wetdeck_z(s))

        # THE OUTER PATH MUST START WHERE THE INNER FILLET ENDS. It used to be
        # generated from (t, zk) and then FILTERED to `ys >= t + rr`, which
        # left a gap between the fillet's end and the first surviving point --
        # so the fillet rounded into nothing and the 90 deg inner bilge came
        # straight back. MEASURED: 89.7 deg on the wetted surface at s = 0.34,
        # after the fillet was supposedly added. Regenerating the path from
        # the fillet's end removes the join entirely.
        _arch = float(np.clip(self.tunnel_arch, 0.05, 0.95))
        _z_in = zk + (zw - zk) * _arch
        _rr = (float(np.clip(self.bilge_radius, 0.0, 0.9))
               * min(abs(_z_in - zk), max(b - t, 1e-6)) * 0.9) if t > 1e-9 else 0.0
        # the outer surface: rise from the keel/tunnel-wall at `beta`, then
        # round into a near-vertical topside. One blend, so no chine crease.
        y0 = t + _rr
        # The turn of bilge sits at a FRACTION OF SECTION HEIGHT, not at
        # whatever the deadrise happens to reach -- see `turn_frac`.
        z_turn = zk + (zs - zk) * float(self.turn_frac(np.array([s]))[0])
        z_turn = min(max(z_turn, zk + 1e-3), zs - 1e-3)
        u = np.linspace(0.0, 1.0, n)
        r = float(self.roundness_at(np.array([s]))[0])
        # quadratic Bezier from (y0, zk) to (b, z_turn) with the corner pulled
        # toward a hard chine as r -> 0
        # A quadratic Bezier whose control point sits ON THE CHORD draws a
        # STRAIGHT line; pulling it toward the bottom-outer corner rounds the
        # bilge. The first version had this inverted -- r = 0 put the control
        # at the corner, so the "hard V" setting produced a FLAT-BOTTOMED U and
        # the axe section drew as a parabolic tube. r = 0 is now the chord
        # (a straight-sided V, the axe entry) and r = 1 the corner (full
        # fillet), which is the sense `roundness` is documented with.
        cy = y0 + (b - y0) * (0.5 + 0.5 * r)
        cz = zk + (z_turn - zk) * (0.5 - 0.5 * r)
        yo = (1 - u) ** 2 * y0 + 2 * (1 - u) * u * cy + u ** 2 * b
        zo = (1 - u) ** 2 * zk + 2 * (1 - u) * u * cz + u ** 2 * z_turn
        # topside up to the sheer
        m = max(4, n // 3)
        v = np.linspace(0.0, 1.0, m)[1:]
        yt = b + (0.004 * b) * v         # slab topsides (the drawing has no flare)
        zt = z_turn + (zs - z_turn) * v

        ys = np.concatenate([yo, yt])
        zs_ = np.concatenate([zo, zt])

        # AN OPEN PATH FROM CENTRELINE TO CENTRELINE, not a closed half-loop.
        # The first version returned a closed half-section that INCLUDED the
        # y = 0 segments; mirroring it laid a second copy of every centreline
        # face on top of the first, which is where `mesh_repair.diagnose`
        # found 88 non-manifold edges, 428 winding conflicts and 66
        # self-intersections. A path that merely TOUCHES y = 0 at its two ends
        # mirrors into one clean closed loop, so the loft is a manifold tube.
        if t <= 1e-9:
            # solid: centreline keel -> outer -> sheer -> centreline deck
            return np.column_stack([np.concatenate([[0.0], ys, [0.0]]),
                                    np.concatenate([[zk], zs_, [zs]])])
        # TUNNELLED: A FAIRED ARCH. The first version walked a HORIZONTAL wet
        # deck into a VERTICAL tunnel wall, meeting at a hard 90 deg corner --
        # twice per demihull, running the whole length of the tunnel. Those are
        # sharp longitudinal lines sitting parallel to the flow just under the
        # waterline, and they are exactly the drag the owner spotted. The
        # schematic's Section C-C shows the wet deck arching into each demihull
        # through a radius, not a corner.
        #
        # So the inner boundary is now ONE cubic Bezier from the centreline at
        # the wet deck to the demihull's inner bilge: it leaves the centreline
        # HORIZONTALLY (which makes the arch smooth across y = 0 once mirrored,
        # rather than a peak) and arrives at the tunnel wall VERTICALLY, so it
        # meets the demihull bottom tangentially.
        k = max(8, n // 3)
        w = np.linspace(0.0, 1.0, k)
        z_in = _z_in                          # where the arch meets the wall
        P0 = np.array([0.0, zw])
        P1 = np.array([t * 0.58, zw])         # leaves the centreline flat
        P2 = np.array([t, zw - (zw - z_in) * 0.42])
        P3 = np.array([t, z_in])              # arrives tangent to the wall
        bz = ((1 - w)[:, None] ** 3 * P0 + 3 * (1 - w)[:, None] ** 2
              * w[:, None] * P1 + 3 * (1 - w)[:, None] * w[:, None] ** 2 * P2
              + w[:, None] ** 3 * P3)
        # THE INNER BILGE IS FILLETED TOO. The wall arrived vertically and the
        # demihull bottom left horizontally, so the two met at a 90 deg corner
        # at (t, zk) -- a second sharp longitudinal line under the waterline,
        # the twin of the roof corner fixed above. A quadratic Bezier that
        # takes the CORNER as its control point rounds vertical into
        # horizontal exactly, which is the standard fillet.
        rr = _rr
        j = max(3, n // 6)
        wall_z = z_in + ((zk + rr) - z_in) * np.linspace(0.0, 1.0, j)[1:]
        f = np.linspace(0.0, 1.0, max(6, n // 5))
        fy = (1 - f) ** 2 * t + 2 * (1 - f) * f * t + f ** 2 * (t + rr)
        fz = (1 - f) ** 2 * (zk + rr) + 2 * (1 - f) * f * zk + f ** 2 * zk
        # THE FIN IS PART OF THE SECTION, not a separate solid welded on. A
        # skeg lofted as its own body would meet the hull in a non-manifold
        # junction and need a boolean to clean up; carried as a downward
        # excursion in the SAME closed outline it is manifold by construction
        # and the caps still ear-clip.
        ys, zs_ = self._insert_fin(s, ys, zs_, t, b)
        return np.column_stack([
            np.concatenate([bz[:, 0], np.full(len(wall_z), t), fy, ys, [0.0]]),
            np.concatenate([bz[:, 1], wall_z, fz, zs_, [zs]]),
        ])

    def _insert_fin(self, s, ys, zs_, t, b):
        """Cut a downward skeg into the demihull's bottom at its centreline."""
        zf = float(self.fin_bottom(np.array([float(s)]))[0])
        if not np.isfinite(zf):
            return ys, zs_
        yf = 0.5 * (t + b)                      # the demihull's own centreline
        ht = float(self.fin_half_t)
        y0, y1 = yf - ht, yf + ht
        if y0 <= ys.min() or y1 >= ys.max():
            return ys, zs_
        z0 = float(np.interp(y0, ys, zs_))
        z1 = float(np.interp(y1, ys, zs_))
        if zf >= min(z0, z1):                   # fin shallower than the hull
            return ys, zs_
        k = 9
        down = np.linspace(z0, zf, k)
        up = np.linspace(zf, z1, k)
        pre = ys <= y0
        post = ys >= y1
        new_y = np.concatenate([ys[pre], np.full(k, y0), np.full(k, y1),
                                ys[post]])
        new_z = np.concatenate([zs_[pre], down, up, zs_[post]])
        return new_y, new_z

    def full_section(self, s, n=48):
        """The COMPLETE closed transverse loop: the half-path plus its mirror."""
        p = self.section(s, n=n)
        mir = p[::-1][1:-1].copy()
        mir[:, 0] *= -1.0
        return np.vstack([p, mir])


# --------------------------------------------------------------------------
# Hydrostatics straight off the sections -- no grammar, no ladder.
# --------------------------------------------------------------------------

def _clip_below(pts, wl=0.0):
    """The part of a closed half-section below z = wl, as a closed polygon."""
    out = []
    n = len(pts)
    for i in range(n):
        y1, z1 = pts[i]
        y2, z2 = pts[(i + 1) % n]
        in1, in2 = z1 <= wl, z2 <= wl
        if in1:
            out.append((y1, z1))
        if in1 != in2:
            f = (wl - z1) / (z2 - z1)
            out.append((y1 + f * (y2 - y1), wl))
    return np.asarray(out, float) if len(out) >= 3 else None


def _area_cent(p):
    y1, z1 = p[:, 0], p[:, 1]
    y2, z2 = np.roll(y1, -1), np.roll(z1, -1)
    c = y1 * z2 - y2 * z1
    a = 0.5 * c.sum()
    if abs(a) < 1e-12:
        return 0.0, 0.0, 0.0
    return (abs(a), ((y1 + y2) * c).sum() / (6 * a),
            ((z1 + z2) * c).sum() / (6 * a))


def hydrostatics(h: Hookprobe, wl: float, ns: int = 121):
    s = np.linspace(0.0, 1.0, ns)
    x = s * h.loa
    A = np.zeros(ns); yb = np.zeros(ns); zb = np.zeros(ns); bw = np.zeros(ns)
    for i, si in enumerate(s):
        p = h.section(si)
        c = _clip_below(p, wl)
        if c is None:
            continue
        a, cy, cz = _area_cent(c)
        A[i], yb[i], zb[i] = a, cy, cz
        at = c[np.abs(c[:, 1] - wl) < 1e-9]
        bw[i] = at[:, 0].max() if len(at) else 0.0
    vol = 2.0 * np.trapezoid(A, x)                 # both halves
    if vol <= 0:
        return None
    lcb = np.trapezoid(A * x, x) / max(np.trapezoid(A, x), 1e-12)
    kb = np.trapezoid(A * zb, x) / max(np.trapezoid(A, x), 1e-12)
    awp = 2.0 * np.trapezoid(bw, x)
    it = 2.0 / 3.0 * np.trapezoid(bw ** 3, x)      # transverse inertia
    wetted = 0.0
    for i, si in enumerate(s):
        p = h.section(si)
        c = _clip_below(p, wl)
        if c is None:
            continue
        d = np.diff(np.vstack([c, c[:1]]), axis=0)
        wetted += np.hypot(d[:, 0], d[:, 1]).sum()
    wetted *= 2.0 * (h.loa / ns)
    return dict(volume_m3=vol, disp_kg=RHO * vol, lcb_m=lcb, kb_m=kb,
                awp_m2=awp, i_t_m4=it, bm_m=it / vol, wetted_m2=wetted,
                cb=vol / max(2 * bw.max() * h.loa * abs(wl - h.keel_z(np.array([h.x_bmax]))[0]), 1e-9),
                bwl_m=2 * bw.max())


def float_to(h: Hookprobe, mass_kg: float):
    lo, hi = h.keel_z(np.array([h.x_bmax]))[0] + 1e-3, h.depth - h.t_mid - 1e-3
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        r = hydrostatics(h, mid, ns=61)
        d = (r["disp_kg"] if r else 0.0) - mass_kg
        if d > 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


# --------------------------------------------------------------------------

def _resample_arc(P: np.ndarray, m: int) -> np.ndarray:
    """Resample a closed section outline to `m` points by ARC LENGTH.

    THE GROOVE AT 32% FROM THE BOW. The loft joins point j of one section to
    point j of the next, so index j must mean the same PLACE on the outline at
    every station. It did not. The tunnelled branch of `section()` allocates a
    fixed ~28 points to the arch and ~10 to the inner wall whatever their
    length, so the instant the tunnel opened the point budget jumped even
    though the geometry had barely moved. MEASURED across the split:

        s = 0.6799   tunnel half-width 0.000000 m   170 pts, 12 in the first 5% of arc
        s = 0.6750   tunnel half-width 0.000008 m   252 pts, 52 in the first 5% of arc

    Eight MICROMETRES of tunnel, and the parameterisation jumps. Every quad
    across that station therefore connected mismatched points, which twists
    the surface into a crease running right round the hull -- and `m =
    min(len(p))` then truncated the 252-point sections on top of that.

    Resampling by arc length makes index j mean "this fraction along the
    outline" at every station, and because the tunnelled section tends
    continuously to the solid one as t -> 0, so does its parameterisation.
    """
    d = np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(d)])
    total = cum[-1]
    if total <= 0:
        return np.repeat(P[:1], m, axis=0)
    want = np.linspace(0.0, total, m, endpoint=False)
    closed = np.vstack([P, P[:1]])
    return np.column_stack([np.interp(want, cum, closed[:, 0]),
                            np.interp(want, cum, closed[:, 1])])


def _ear_clip(poly: np.ndarray) -> list[tuple[int, int, int]]:
    """Triangulate a simple closed 2-D polygon by ear clipping.

    THE TRANSOM CAP WAS SEALING THE TUNNEL. The caps used to be a fan from the
    section's centroid, and at the transom the centroid lies at y = 0 -- which
    is INSIDE THE TUNNEL VOID, not in the material. Every fan triangle
    therefore spanned the tunnel opening, so the two demihull transoms were
    bridged by a solid web and the stern did not match the hull it capped.

    A fan is only valid for a star-shaped polygon; a section with a notch cut
    into it is not star-shaped about any point on the notch. Ear clipping
    makes no such assumption, so the cap follows the real outline -- two
    separate demihull transoms with the arch open between them.
    """
    # DEDUPE FIRST. The lofted sections are resampled onto a common vertex
    # count, which leaves runs of coincident and collinear points; an ear test
    # cannot clip those (every candidate ear is degenerate) and the clipper
    # bailed with a hole, leaving 3 boundary edges in an otherwise closed mesh.
    keep = [0]
    for i in range(1, len(poly)):
        if np.hypot(*(poly[i] - poly[keep[-1]])) > 1e-9:
            keep.append(i)
    if len(keep) > 2 and np.hypot(*(poly[keep[-1]] - poly[keep[0]])) <= 1e-9:
        keep.pop()
    if len(keep) < 3:
        return []
    idx = list(keep)
    # work on a consistently counter-clockwise copy
    a = 0.0
    for i in range(len(idx)):
        u, v = idx[i], idx[(i + 1) % len(idx)]
        a += poly[u, 0] * poly[v, 1] - poly[v, 0] * poly[u, 1]
    if a < 0:
        idx.reverse()

    def cross(o, u, v):
        return ((poly[u, 0] - poly[o, 0]) * (poly[v, 1] - poly[o, 1])
                - (poly[u, 1] - poly[o, 1]) * (poly[v, 0] - poly[o, 0]))

    def inside(p, o, u, v):
        d1 = cross(o, u, p); d2 = cross(u, v, p); d3 = cross(v, o, p)
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))

    def quality(o, u, v):
        """Smallest angle of the candidate ear, as a cheap shape score."""
        a, b, c = poly[o], poly[u], poly[v]
        best = 1e9
        for (x, y, z) in ((a, b, c), (b, c, a), (c, a, b)):
            v1, v2 = y - x, z - x
            n1 = math.hypot(v1[0], v1[1]); n2 = math.hypot(v2[0], v2[1])
            if n1 < 1e-12 or n2 < 1e-12:
                return -1.0
            cosang = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
            best = min(best, math.acos(max(-1.0, min(1.0, cosang))))
        return best

    # CLIP THE BEST EAR, NOT THE FIRST ONE. Taking the first valid ear walks
    # round the outline shaving one vertex at a time off the same region, so
    # the cap came out as a near-fan: MEASURED on the transom, 240 of 250
    # triangles under 5 deg minimum angle and the worst at 0.00 deg. That is
    # manifold but it is not a mesh anyone should print or run a solver on.
    # Choosing the ear with the largest minimum angle is the standard fix and
    # costs nothing here -- there are only two caps.
    out, guard = [], 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        reflex = [w for w in idx
                  if cross(idx[idx.index(w) - 1], w,
                           idx[(idx.index(w) + 1) % len(idx)]) <= 0]
        best_i, best_q = -1, -1.0
        for i in range(len(idx)):
            o, u, v = idx[i - 1], idx[i], idx[(i + 1) % len(idx)]
            if cross(o, u, v) <= 1e-14:
                continue                       # reflex or degenerate
            if any(inside(w, o, u, v) for w in reflex if w not in (o, u, v)):
                continue                       # a reflex vertex inside the ear
            q = quality(o, u, v)
            if q > best_q:
                best_i, best_q = i, q
        if best_i < 0:
            break
        i = best_i
        out.append((idx[i - 1], idx[i], idx[(i + 1) % len(idx)]))
        idx.pop(i)
    if len(idx) == 3:
        out.append((idx[0], idx[1], idx[2]))
    elif len(idx) > 3:
        # A hole here is a LEAK, and a leaking cap is worse than an
        # approximate one -- fan the remainder so the surface still closes,
        # and say so rather than returning a mesh with a boundary.
        for i in range(1, len(idx) - 1):
            out.append((idx[0], idx[i], idx[i + 1]))
    return out


def write_stl(h: Hookprobe, path: Path, ns: int = 241, nsec: int = 56,
              n_ctrl: int = 81):
    """Loft by SKINNING: control sections -> B-spline curves -> surface.

    This is the owner's "we unite nurbs points, we make lines then we stretch
    the surface from the lines", and it is the skinning method of Zhu et al.
    (jmse-11-01816): section curves are given a COMMON parameterisation (here
    arc-length fraction, which is their "uniform continuity"), and the surface
    is the family of longitudinal B-splines through corresponding points.

    Before this the loft connected control sections DIRECTLY with straight
    quads, so the surface was only C0 between stations -- every station was a
    faint polyline crease, which is why the surfaces did not look faired.
    Now `n_ctrl` control sections define the geometry and the longitudinal
    B-spline (C2) is EVALUATED at `ns` stations: the dense stations lie on a
    smooth curve instead of being interpolation breakpoints.
    """
    sc = np.linspace(0.0, 1.0, n_ctrl)
    secs = [h.full_section(si, n=nsec) for si in sc]
    m = max(len(p) for p in secs)
    C = np.stack([_resample_arc(p, m) for p in secs])      # (n_ctrl, m, 2)
    spl = make_interp_spline(sc, C, k=3, axis=0, bc_type="natural")
    s = np.linspace(0.0, 1.0, ns)
    R = list(spl(s))                                        # ns x (m, 2)
    tris = []

    def quad(a, b, c, d):
        tris.append((a, b, c)); tris.append((a, c, d))

    # THE RAKE IS PER-VERTEX, not per-station: x depends on z, which is what
    # makes the stem a straight 20 deg line instead of a vertical cut.
    XP = [s[i] * h.loa + h.rake_dx(np.full(len(R[i]), s[i]), R[i][:, 1])
          for i in range(ns)]
    for i in range(ns - 1):
        P, Q = R[i], R[i + 1]
        xp, xq = XP[i], XP[i + 1]
        for j in range(m):            # WRAP: the loop is closed
            j2 = (j + 1) % m
            quad((xp[j], P[j, 0], P[j, 1]),
                 (xp[j2], P[j2, 0], P[j2, 1]),
                 (xq[j2], Q[j2, 0], Q[j2, 1]),
                 (xq[j], Q[j, 0], Q[j, 1]))
    # cap the ends
    for (P, xv, flip) in ((R[0], XP[0], True), (R[-1], XP[-1], False)):
        for (i0, i1, i2) in _ear_clip(P):
            a = (xv[i0], P[i0, 0], P[i0, 1])
            b = (xv[i1], P[i1, 0], P[i1, 1])
            c = (xv[i2], P[i2, 0], P[i2, 1])
            tris.append((a, b, c) if flip else (a, c, b))
    # NORMALISE LOA. The 20 deg aft rake pushes the forefoot FORWARD of the
    # last station, so the raw extent came out 16.49 m against a 16.00 m brief
    # -- a real spec violation, not a rounding one. A shear in x preserves
    # every sectional area (its Jacobian is 1), so the hydrostatics above are
    # unaffected; only the extent needs bringing back onto the brief.
    _V = np.array([v for t in tris for v in t], dtype=float)
    _lo, _hi = _V[:, 0].min(), _V[:, 0].max()
    _k = h.loa / (_hi - _lo)
    tris = [tuple(((v[0] - _lo) * _k, v[1], v[2]) for v in t) for t in tris]
    with open(path, "w") as f:
        f.write("solid hookprobe\n")
        for t in tris:
            f.write(" facet normal 0 0 0\n  outer loop\n")
            for v in t:
                f.write(f"   vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("  endloop\n endfacet\n")
        f.write("endsolid hookprobe\n")
    return len(tris)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/exports/houseboat16")
    ap.add_argument("--mass", type=float, default=14000.0)
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    h = Hookprobe()
    wl = float_to(h, args.mass)
    r = hydrostatics(h, wl, ns=161)
    kb = r["kb_m"]; bm = r["bm_m"]
    kg = 0.55 * h.depth - h.t_mid          # a plausible loaded VCG
    gm = kb + bm - kg
    print(f"HOOKPROBE  LOA {h.loa} m  Bmax {h.bmax} m  depth {h.depth} m")
    print(f"  floats {r['disp_kg']:.0f} kg at DWL z = {wl:+.3f} "
          f"(draft {wl - h.keel_z(np.array([h.x_bmax]))[0]:.3f} m at midships,"
          f" {wl - h.keel_z(np.array([1.0]))[0]:.3f} m at the stem)")
    print(f"  BWL {r['bwl_m']:.2f} m | Awp {r['awp_m2']:.1f} m2 | "
          f"wetted {r['wetted_m2']:.1f} m2")
    print(f"  KB {kb:.3f}  BM {bm:.3f}  GM {gm:.3f} m   "
          f"(twin demihulls: BM is LARGE by geometry, so no ROLL fins)")
    # Two DIFFERENT things are called fins and conflating them would be the
    # number-declared-twice defect wearing a different hat: the demihulls give
    # roll stiffness so no anti-roll fin is wanted, while the two skegs below
    # exist for LATERAL AREA and directional stability, which the raised run
    # takes away.
    _fs = np.linspace(0.0, 1.0, 401)
    _fb = h.fin_bottom(_fs)
    _kb0 = float(h.keel_z(np.array([0.0]))[0])
    _kbm = float(h.keel_z(np.array([h.x_bmax]))[0])
    print(f"  stern rise (midships -> transom) {_kb0 - _kbm:+.3f} m, for flow into the run")
    print(f"  2 skegs, one per demihull at y = +-{0.5 * (h.tunnel_half_max + 0.5 * h.bmax):.2f} m, "
          f"{np.nanmin(_fb):.3f} m deep = the axe forefoot ({-h.t_stem:.3f} m): uniform draught")
    stl = out / "houseboat16.stl"
    n = write_stl(h, stl)
    # REPAIR IS PART OF THE PIPELINE, not a manual afterthought. The loft
    # collapses toward a point at the stem, which necessarily produces
    # degenerate and duplicate faces there; `mesh_repair` drops them and fixes
    # the winding. An STL that is going to be MESHED or PRINTED must be
    # manifold, and this repo's own rule is that an unmeasured metric is
    # refused rather than assumed good -- so the mesh is re-diagnosed after
    # the repair and the report is printed, not swallowed.
    from navalai import mesh_repair as _mr
    V, T, rep = _mr.repair(str(stl))
    with open(stl, "w") as f:
        f.write("solid hookprobe\n")
        for t in T:
            a, b, c = V[t[0]], V[t[1]], V[t[2]]
            nn = np.cross(b - a, c - a)
            ln = np.linalg.norm(nn)
            nn = nn / ln if ln > 0 else nn
            f.write(f" facet normal {nn[0]:.6e} {nn[1]:.6e} {nn[2]:.6e}\n"
                    "  outer loop\n")
            for v in (a, b, c):
                f.write(f"   vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("  endloop\n endfacet\n")
        f.write("endsolid hookprobe\n")
    chk = _mr.diagnose(str(stl))
    print(f"  STL {stl}  {n} lofted -> {rep.n_tris_after} after repair")
    for a in rep.applied:
        print(f"    repair: {a}")
    bad = {k: v for k, v in chk.found.items() if v}
    print(f"    WATERTIGHT AND MANIFOLD: {not bad}"
          + ("" if not bad else f"  STILL FOUND {bad}"))
    json.dump({k: v for k, v in h.__dict__.items()
               if not k.startswith("_")},          # cached splines are not params
              open(out / "hookprobe_params.json", "w"), indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
