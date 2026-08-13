"""Gate 2S — slamming pressure is MEASURABLE, at L0 and at L3 (plate P6).

THE MOTIVATING MEASUREMENT, 2026-08-13, before any of this existed:

    grep -c "surfaceFieldValue\\|hull_bow\\|bowSlam" navalai/cfd/case.py  ->  0

`forces`, `forceCoeffs` and `yPlus` were all present and working; this one
family was absent, and it could not be added because the hull was a SINGLE
patch — there was nothing for a bow-region function object to point at. So
`P_slam` was not merely unmeasured, it was unmeasurABLE at every tier: no
analytic model in `navalai/seakeeping.py` and no instrument in the case.

Nothing here needs OpenFOAM. Every test reads what the generator WROTE or
evaluates a closed form, which is where all of P6 lives. The one claim that a
mesh would settle — that snappyHexMesh really creates a patch named `hull_bow`
— was settled instead by reading v2606's own source (searchableSurfaces.C
builds the global region name from `regions { <local> { name X; } }` verbatim,
and snappyHexMesh.C creates one patch per global region called exactly that),
and `test_the_generated_case_carries_the_bow_patch_and_the_function_object`
pins the dictionary shape that reading depends on.

WHAT IS STILL OWED, AND IS NOT CLAIMED ANYWHERE HERE: one mesh-only
snappyHexMesh build (~2 min) confirming that `constant/polyMesh/boundary`
carries both patches and that the layer table reports the bow patch layered.
No OpenFOAM was run for this change.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from navalai import grammar, seakeeping
from navalai.cfd import case as C
from navalai.geometry import RHO_WATER

_KCS_STL = (Path(__file__).resolve().parents[1] / "data" / "benchmark_geom"
            / "kcs.stl")

# THE GEOMETRY HERE IS AN STL, NOT A `Hull`, AND THAT IS DELIBERATE.
# The bow patch is cut out of `constant/triSurface/hull.stl` by
# `split_bow_region`, so the thing under test is a SURFACE — the parametric
# hull generator is upstream of it and irrelevant to it. Driving this gate
# through `write_resistance_case_from_stl` also exercises the path the KCS
# anchor takes, which is the hull a slamming comparison would eventually be
# made against. `test_the_partition_holds_on_the_real_KCS_hull` runs the same
# assertions on that hull when its (gitignored) geometry is present.
_LWL = 12.0


def _lofted_hull_stl(path: Path, lwl: float = _LWL, beam: float = 3.0,
                     draft: float = 0.9, freeboard: float = 0.8,
                     n: int = 40) -> None:
    """A closed, hull-shaped loft: rectangular sections tapering to a stem.

    Closed BY CONSTRUCTION — it is a quad tube of `n+1` four-cornered rings
    with a cap at each end, so every edge is shared by exactly two triangles
    and there is nothing for `mesh_repair.diagnose` to refuse. It has the two
    features this gate needs and a box does not: a real stem (the half-beam
    tapers to a stem post) and a forefoot (the keel rises toward it), so the
    forward fraction of LWL is a genuinely different part of the surface.
    """
    rings = []
    for i in range(n + 1):
        t = i / n
        half = 0.5 * beam * max(1.0 - t ** 3, 0.04)      # taper to a stem post
        keel = -draft * (1.0 - 0.8 * max(t - 0.7, 0.0) / 0.3)   # forefoot rise
        x = t * lwl
        rings.append([(x, -half, keel), (x, half, keel),
                      (x, half, freeboard), (x, -half, freeboard)])

    tris = []
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(4):
            k2 = (k + 1) % 4
            tris.append((a[k], a[k2], b[k2]))
            tris.append((a[k], b[k2], b[k]))
    tris.append((rings[0][0], rings[0][2], rings[0][1]))     # transom cap
    tris.append((rings[0][0], rings[0][3], rings[0][2]))
    tris.append((rings[-1][0], rings[-1][1], rings[-1][2]))  # stem cap
    tris.append((rings[-1][0], rings[-1][2], rings[-1][3]))

    out = ["solid hull"]
    for t3 in tris:
        out.append(" facet normal 0.000000e+00 0.000000e+00 1.000000e+00")
        out.append("  outer loop")
        for v in t3:
            out.append(f"   vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}")
        out += ["  endloop", " endfacet"]
    out.append("endsolid hull")
    path.write_text("\n".join(out) + "\n")


def _case(tmp_path: Path, name: str = "case", **kw) -> Path:
    """Generate a complete case from the lofted hull; return its directory."""
    stl = tmp_path / f"{name}.stl"
    _lofted_hull_stl(stl)
    out = tmp_path / name
    C.write_resistance_case_from_stl(stl, _LWL, 2.0, out, end_time=1.0,
                                     np_procs=1, **kw)
    return out


def _facet_blocks(path: Path) -> list[str]:
    """Every `facet ... endfacet` block of an ascii STL, as verbatim text."""
    out, cur = [], []
    for raw in Path(path).read_text().splitlines():
        s = raw.strip()
        if s.startswith("facet"):
            cur = [raw]
            continue
        if not cur:
            continue
        cur.append(raw)
        if s.startswith("endfacet"):
            out.append("\n".join(cur))
            cur = []
    return out


def _solids(path: Path) -> dict[str, list[str]]:
    """{solid name: [facet blocks]} — the partition the STL actually ships."""
    out: dict[str, list[str]] = {}
    name, cur = None, []
    for raw in Path(path).read_text().splitlines():
        s = raw.strip()
        if s.startswith("endsolid"):
            name = None
            continue
        if s.startswith("solid"):
            name = s.split()[1]
            out.setdefault(name, [])
            continue
        if name is None:
            continue
        if s.startswith("facet"):
            cur = [raw]
            continue
        if not cur:
            continue
        cur.append(raw)
        if s.startswith("endfacet"):
            out[name].append("\n".join(cur))
            cur = []
    return out


# ---------------------------------------------------------------------------
# BAR 2 — the closed form, at both limits
# ---------------------------------------------------------------------------

def test_cp_falls_monotonically_with_deadrise_over_the_whole_domain():
    """A blunter entry can never slam more gently than a sharper one.

    This is the property that makes the expression a slamming model rather than
    a curve: both terms of
        C_p = pi cot(beta) + (pi^2 / 2) (pi / (2 beta) - 1)^2
    are decreasing on (0, 90 deg], so nothing in between can invert. Asserted
    strictly (`<`, not `<=`) over 900 points because a plateau would mean a
    band of deadrise the model cannot tell apart, and `slam_pressure_band`
    RELIES on monotonicity: it brackets the patch by evaluating only the two
    endpoints, which is wrong the moment an interior point can exceed them.
    """
    betas = [0.1 + 0.1 * i for i in range(900)]     # 0.1 .. 90.0 deg
    cps = [seakeeping.wagner_impact_cp(b) for b in betas]
    assert betas[-1] == pytest.approx(90.0)
    bad = [(betas[i], cps[i], cps[i + 1])
           for i in range(len(cps) - 1) if not cps[i] > cps[i + 1]]
    assert not bad, f"C_p not strictly decreasing at {bad[:5]}"

    # And the interior really is bracketed by the endpoints, which is the
    # claim `slam_pressure_band` makes to the reader of a patch maximum.
    lo, hi = seakeeping.slam_pressure_band(8.0, 32.0, 5.0)
    interior = [seakeeping.slam_pressure(b, 5.0)
                for b in (8.0, 12.0, 20.0, 27.5, 32.0)]
    assert lo <= min(interior) and max(interior) <= hi


def test_cp_goes_to_zero_at_ninety_degrees_and_blows_up_toward_zero():
    """The two limits the physics demands.

    beta -> 90 deg: a vertical wall does not slam, it shears. In exact
    arithmetic cot(pi/2) = 0 and pi/(2 * pi/2) - 1 = 0, so both terms vanish.
    MEASURED in float it returns 1.92e-16, because `math.radians(90)` is the
    nearest double to pi/2 and `tan` of that is 1.633e16, not infinite. The
    bar is therefore < 1e-15 WITH THE RESIDUE NAMED, rather than a hand-placed
    0.0 at the endpoint: a special case there would hide whether the
    expression actually goes to zero, and a wave-piercing bow is the design
    direction this whole instrument exists to price.

    beta -> 0: a flat bottom has no finite Wagner answer. The second term grows
    as 1/beta^2, so halving the deadrise very nearly quadruples C_p, and the
    test asserts that RATE rather than merely "it is big" — a model that grew
    like 1/beta would pass a magnitude check and misprice every flat-bottomed
    hull by orders of magnitude.
    """
    at90 = seakeeping.wagner_impact_cp(90.0)
    assert 0.0 <= at90 < 1e-15
    assert at90 == pytest.approx(1.92e-16, rel=0.05), "the named float residue"
    assert seakeeping.wagner_impact_cp(89.0) > 1e4 * at90

    # 1/beta^2 growth: each halving multiplies C_p by ~4, approaching 4 from
    # ABOVE. MEASURED: 4.0018 / 4.0036 / 4.0071 / 4.0142 at beta = 0.05 / 0.1 /
    # 0.2 / 0.4 deg. Above, not below, because the -1 inside the squared term
    # makes the ratio ((pi/b - 1)/(pi/2b - 1))^2 = (2 + 1/(a-1))^2 > 4; the
    # pi*cot term, which only doubles, drags it back toward 4 as beta grows.
    # A model growing like 1/beta would give ~2 here and would still pass a
    # naive "it gets big" check while mispricing every flat-bottomed hull.
    for b in (0.05, 0.1, 0.2, 0.4):
        ratio = (seakeeping.wagner_impact_cp(b / 2.0)
                 / seakeeping.wagner_impact_cp(b))
        assert 3.9 < ratio < 4.1, f"beta {b} deg: C_p ratio {ratio}"
    assert seakeeping.wagner_impact_cp(0.01) > 1e8


def test_the_domain_guard_fires_on_the_inputs_that_would_report_a_negative_slam():
    """A guard is only real if it is fed the input it must reject.

    beta > 90 deg is a RE-ENTRANT section, and the expression does not degrade
    there — it CHANGES SIGN. MEASURED: at beta = 100 deg it evaluates to
    -0.5046, so `0.5 rho V^2 C_p` would report a slam that SUCKS, and a design
    loop consuming it would rank a re-entrant bow as the safest hull in the
    batch. That is docs/LESSONS.md defect class 1 exactly (an unmeasurable
    value scored as a passing one), so both ends of the domain raise instead.
    """
    # The verbatim number the guard exists for, computed straight from the
    # formula so the test cannot drift from the claim in the comment.
    b = math.radians(100.0)
    raw = math.pi / math.tan(b) + 0.5 * math.pi ** 2 * (math.pi / (2 * b) - 1) ** 2
    assert raw == pytest.approx(-0.5046, abs=1e-4), "the sign flip is the point"

    for bad in (100.0, 90.001, 180.0, 0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            seakeeping.wagner_impact_cp(bad)
        with pytest.raises(ValueError):
            seakeeping.slam_pressure(bad, 5.0)

    # ... and rho/velocity are guarded on the same principle.
    with pytest.raises(ValueError):
        seakeeping.slam_pressure(20.0, float("nan"))
    with pytest.raises(ValueError):
        seakeeping.slam_pressure(20.0, 5.0, rho=0.0)


def test_slam_pressure_is_half_rho_v_squared_cp_and_owns_no_second_density():
    """P_slam = 0.5 rho V^2 C_p, with rho from the ONE place that owns it.

    docs/LESSONS.md records a NINTH copy of water density that was dividing
    every C_T the gate printed. This function does not add a tenth: its default
    is `geometry.RHO_WATER`, asserted here by identity of the RESULT rather
    than by reading the signature, so aliasing the constant to a literal would
    still fail.
    """
    p = seakeeping.slam_pressure(15.0, 4.0)
    assert p == pytest.approx(0.5 * RHO_WATER * 16.0
                              * seakeeping.wagner_impact_cp(15.0))
    # V enters squared, so entry direction cannot change the magnitude.
    assert seakeeping.slam_pressure(15.0, -4.0) == pytest.approx(p)
    # ... and the band is sorted even when the caller hands it an
    # L0-infeasible hull (beta_bow < beta_mid violates `deadrise.order`).
    lo, hi = seakeeping.slam_pressure_band(30.0, 5.0, 3.0)
    assert lo < hi


# ---------------------------------------------------------------------------
# BAR 3 — the bow region is a strict subset of the hull, on REAL geometry
# ---------------------------------------------------------------------------

def test_the_bow_solid_partitions_the_hull_on_real_geometry(tmp_path):
    """bow is a STRICT subset, main is a strict subset, and the union is all.

    Asserted on the facet blocks of a lofted hull with a real stem and
    forefoot, and asserted as a MULTISET of verbatim text: that catches a
    partition that is correct in count while having reformatted a coordinate.
    `write_resistance_case_from_stl` exists to mesh a benchmark hull whose
    shape is the entire point of the comparison, so "the split moved nothing"
    has to be a test and not a docstring.
    """
    out = _case(tmp_path)
    stl = out / "constant" / "triSurface" / "hull.stl"

    solids = _solids(stl)
    assert set(solids) == {C._STL_MAIN_SOLID, C._STL_BOW_SOLID}
    bow = solids[C._STL_BOW_SOLID]
    main = solids[C._STL_MAIN_SOLID]
    whole = _facet_blocks(stl)

    assert bow and main, "both solids must be non-empty"
    assert len(bow) < len(whole) and len(main) < len(whole)   # STRICT subsets
    assert sorted(bow + main) == sorted(whole)                # union is all
    assert len(bow) + len(main) == len(whole)                 # disjoint

    # The cut is geometric, not accidental: every bow facet REACHES the split
    # plane and no main facet does. A straddling facet rounds FORWARD, so the
    # patch's actual aft edge is at or abaft the plane — and that edge is a
    # recorded number, not an assumption.
    def _xs(block: str) -> list[float]:
        return [float(l.split()[1]) for l in block.splitlines()
                if l.strip().startswith("vertex")]

    info = dict(l.split("=", 1) for l in (out / "case.info").read_text()
                .splitlines() if "=" in l and not l.startswith(" "))
    x_split = float(info["bow_patch_x_split_m"])
    assert min(max(_xs(b)) for b in bow) >= x_split
    assert max(max(_xs(m)) for m in main) < x_split
    aftmost = min(min(_xs(b)) for b in bow)
    assert float(info["bow_patch_x_aftmost_m"]) == pytest.approx(aftmost,
                                                                 abs=1e-4)
    assert aftmost <= x_split
    # The over-inclusion is ONE FACET ROW, not a material change to the patch,
    # and the fixture is built so that row has a known width: `_lofted_hull_stl`
    # lays 40 rings over the length, so one row is _LWL / 40 = 0.3 m and no
    # straddling facet can reach further back than that. MEASURED on the real
    # KCS hull the same quantity is 25.8 mm on a 7.7165 m surface — 0.33% —
    # because its tessellation is far finer; see the KCS test at the end.
    assert 0.0 <= (x_split - aftmost) <= _LWL / 40.0 + 1e-9


def test_the_split_is_geometry_preserving_to_the_byte(tmp_path):
    """The shipped hull is the delivered hull, regrouped — never re-emitted.

    `post._read_stl_tris` rounds to 7 decimals, so a parse-and-rewrite split
    would have perturbed an imported benchmark at the 100 nm level for no
    reason — and an imported benchmark's shape is the entire point of the
    comparison it exists for. The shipped facet blocks are compared VERBATIM
    against the source file the case was generated from.
    """
    src = tmp_path / "src.stl"
    _lofted_hull_stl(src)
    source_blocks = _facet_blocks(src)
    out = tmp_path / "case"
    C.write_resistance_case_from_stl(src, _LWL, 2.0, out, end_time=1.0,
                                     np_procs=1)
    shipped = out / "constant" / "triSurface" / "hull.stl"
    info = dict(l.split("=", 1) for l in (out / "case.info").read_text()
                .splitlines() if "=" in l and not l.startswith(" "))

    assert sorted(_facet_blocks(shipped)) == sorted(source_blocks)
    # The two hashes in case.info are DIFFERENT and both are honest: the
    # identity hash is of the geometry as delivered, the shipped hash is of the
    # file on disk. A reader running sha256sum must be able to reconcile.
    import hashlib
    assert info["stl_sha256_shipped"] == hashlib.sha256(
        shipped.read_bytes()).hexdigest()
    assert info["stl_sha256"] != info["stl_sha256_shipped"]


def test_the_split_refuses_rather_than_shipping_an_empty_region(tmp_path):
    """An empty bow solid would give `surfaceFieldValue` nothing to max over.

    docs/LESSONS.md defect class 1: failure to measure must never become a
    passing score. A zero-face patch does not raise in snappy — it produces a
    patch, and the function object then reports an empty reduction — so the
    refusal has to happen at generation time, where the fraction is known.
    """
    out = _case(tmp_path)
    stl = out / "constant" / "triSurface" / "hull.stl"
    lwl = _LWL

    for bad in (0.0, 1.0, -0.2, 1.5):
        with pytest.raises(ValueError, match="fraction"):
            C.split_bow_region(stl, fraction=bad)

    # AN EMPTY BOW IS IMPOSSIBLE BY CONSTRUCTION, and the code therefore does
    # not carry a guard for it: the facet attaining x_stem reaches the split
    # plane for any fraction in (0, 1). An unreachable branch claiming to be a
    # guard is worse than no guard, so the one direction that CAN happen — the
    # fraction swallowing the whole surface — is the one that raises, and it is
    # fed the verbatim input it must reject (docs/LESSONS.md defect class 3).
    one = tmp_path / "one.stl"
    one.write_text("solid s\n facet normal 0 0 1\n  outer loop\n"
                   "   vertex 0.0 0.0 0.0\n   vertex 0.0 1.0 0.0\n"
                   "   vertex 1.0 0.0 0.0\n  endloop\n endfacet\nendsolid s\n")
    with pytest.raises(ValueError, match="none\\s+in the main solid"):
        C.split_bow_region(one, fraction=0.9)
    # ... and a surface with NO longitudinal extent (every facet in one yz
    # plane) is entirely bow at any fraction, which is the same refusal.
    flat = tmp_path / "flat.stl"
    flat.write_text("solid s\n facet normal 1 0 0\n  outer loop\n"
                    "   vertex 1.0 0.0 0.0\n   vertex 1.0 1.0 0.0\n"
                    "   vertex 1.0 0.0 1.0\n  endloop\n endfacet\nendsolid s\n")
    with pytest.raises(ValueError, match="main solid"):
        C.split_bow_region(flat)

    # A binary STL reaches the ascii readers as ZERO facets. That must read as
    # "I could not parse this", never as "this hull has no triangles".
    binary = tmp_path / "binary.stl"
    binary.write_bytes(b"\0" * 84)
    with pytest.raises(ValueError, match="no ascii STL facets"):
        C.split_bow_region(binary)


# ---------------------------------------------------------------------------
# BAR 1 — the generated case carries the patch AND the instrument
# ---------------------------------------------------------------------------

def test_the_generated_case_carries_the_bow_patch_and_the_function_object(tmp_path):
    """Read the written dictionaries, not the source. Both entry points.

    The parametrised path (`write_resistance_case`) and the imported-geometry
    path (`write_resistance_case_from_stl`) reach the same private writer
    `_write_case_dicts`, which is where the split is performed and where the
    dictionaries are written — so instrumenting one instruments both, and this
    gate drives the imported path because that is the one the KCS anchor takes.
    """
    out = _case(tmp_path)

    snappy = (out / "system" / "snappyHexMeshDict").read_text()
    # The geometry entry is what makes the patch NAME `hull_bow` rather than
    # `hull_bow` by luck: searchableSurfaces.C uses the `regions { <local> {
    # name X; } }` value verbatim as the global region name, and
    # snappyHexMesh.C creates one patch per global region called exactly that.
    assert "regions" in snappy
    assert f"{C._STL_MAIN_SOLID} {{ name {C.HULL_PATCH_NAME}; }}" in snappy
    assert f"{C._STL_BOW_SOLID}  {{ name {C.BOW_PATCH_NAME}; }}" in snappy

    cd = (out / "system" / "controlDict").read_text()
    fo = cd.split("bowSlammingPressure", 1)[1].split("}", 1)[0]
    assert "type            surfaceFieldValue" in fo
    assert "regionType      patch" in fo
    assert f"name            {C.BOW_PATCH_NAME}" in fo
    assert "operation       max" in fo
    assert "p_rgh" in fo
    # `fieldValue::read` calls dict.readEntry("writeFields", ...), which is
    # MANDATORY — omitting it is a FATAL IO error at run time, the same shape
    # as the meshQualityControls/relaxed sub-dict that killed a run AFTER the
    # mesh was already built.
    assert "writeFields     false" in fo


def test_every_dictionary_that_addresses_the_hull_addresses_both_patches(tmp_path):
    """The split must not silently remove 20% of LWL from the reported drag.

    This is the regression that would have been hardest to see: `forces` with
    `patches (hull)` still runs, still writes a plausible force history, and
    reports a hull 20% shorter than the one that was meshed. Same class as
    `forceCoeffs` being wrong by exactly 2x on every symmetric run — an
    instrument that keeps working while measuring a different object.
    """
    motion = C.sixdof_properties(1000.0, (5.0, 0.0, -0.2), 1.0, 2.5, 2.5,
                                 lwl=_LWL, awp_m2=20.0, symmetric=False)
    out = _case(tmp_path, free_motion=motion)

    cd = (out / "system" / "controlDict").read_text()
    for fo in ("forces", "forceCoeffs"):
        line = [l for l in cd.splitlines()
                if l.strip().startswith(f"type {fo};")][0]
        assert f"patches ({C.HULL_PATCH_NAME} {C.BOW_PATCH_NAME})" in line, line

    dyn = (out / "constant" / "dynamicMeshDict").read_text()
    assert f"patches             ({C.HULL_PATCH_NAME} {C.BOW_PATCH_NAME});" in dyn

    # Boundary conditions: ONE regex entry covering both, never two copies that
    # can drift. OpenFOAM matches boundaryField keys as regexes.
    for f in ("U", "p_rgh", "alpha.water", "k", "omega", "nut",
              "pointDisplacement"):
        text = (out / "0.orig" / f).read_text()
        assert '"hull.*"' in text, f
        assert "\n  hull " not in text and "\n    hull " not in text, f

    # Prism layers on BOTH patches, from one regex. A bow patch left at zero
    # layers is a PARTIAL layer field, and CLAUDE.md records that partial
    # stacks — not full ones and not absent ones — are what fold cells.
    snappy = (out / "system" / "snappyHexMeshDict").read_text()
    layers = snappy.split("layers {", 1)[1].split("}", 1)[0]
    assert '"hull.*"' in layers
    import re
    pat = re.compile('hull.*')
    assert pat.fullmatch(C.HULL_PATCH_NAME) and pat.fullmatch(C.BOW_PATCH_NAME)


def test_the_region_split_does_not_invent_a_feature_edge(tmp_path):
    """`geometricTestOnly yes` is load-bearing, and its default is NO.

    `surfaceFeatures::classifyFeatureAngles` marks EVERY edge between two STL
    regions as a REGION feature edge before any angle test is applied
    (v2606 src/meshTools/triSurface/surfaceFeatures/surfaceFeatures.C). With
    the default, splitting hull.stl into two solids would have written a closed
    feature LOOP around the hull at the bow cut into hull.eMesh — and snappy
    snaps to feature edges, so a smooth hull would acquire a fabricated crease
    at the station where forefoot curvature is highest. That is a DIFFERENT
    HULL, not a worse mesh, and it is the one way this "pure instrument
    addition" could have changed the physics.
    """
    out = _case(tmp_path)
    sfe = (out / "system" / "surfaceFeatureExtractDict").read_text()
    assert "geometricTestOnly yes" in sfe
    # The angle bar is UNCHANGED; tests/test_stl_forensics.py owns it.
    assert "includedAngle 150" in sfe


def test_the_bow_patch_covers_the_forward_fraction_of_lwl_it_claims(tmp_path):
    """The receipt is the number, and the number is the geometry.

    A case directory must never have to be reverse-engineered to learn where
    its own bow patch ended: `clean-runs.sh --purge` deletes runs while the
    prose citing them survives (defect class 5), so the fraction, the stem and
    the split plane all live in case.info beside the facet count.
    """
    out = _case(tmp_path)
    info = dict(l.split("=", 1) for l in (out / "case.info").read_text()
                .splitlines() if "=" in l and not l.startswith(" "))

    assert float(info["bow_patch_fraction"]) == pytest.approx(
        C.BOW_PATCH_FRACTION)
    assert info["bow_patch"] == C.BOW_PATCH_NAME
    stem, split = (float(info["bow_patch_stem_x_m"]),
                   float(info["bow_patch_x_split_m"]))
    length = float(info["bow_patch_hull_length_m"])
    assert stem - split == pytest.approx(C.BOW_PATCH_FRACTION * length,
                                         abs=1e-4)
    # The lofted fixture spans [0, _LWL] exactly, like every hull this project
    # GENERATES (`hull_to_stl` writes `closed_mesh` over x in [0, lwl]), so
    # here the surface extent and Lwl coincide. They part company only for
    # imported geometry with overhang — see the KCS test at the end.
    assert length == pytest.approx(_LWL, abs=1e-4)

    # The cut sits inside the forebody `geometry.hull_curves` lifts (`x > 0.7
    # L`), which is the surface that re-enters in a slam, and inside the
    # deadrise warp zone for every hull the grammar can sample: `beta_len` is
    # bounded at >= 0.15 of LWL, so the patch's aft edge is never more than
    # 0.05 L abaft the start of the warp.
    beta_len_min = [lo for n, _u, lo, _hi, _d in grammar.PARAMS
                    if n == "beta_len"][0]
    assert C.BOW_PATCH_FRACTION <= 1.0 - 0.7     # inside the lifting bow
    assert round(C.BOW_PATCH_FRACTION - beta_len_min, 12) <= 0.05


@pytest.mark.skipif(
    not _KCS_STL.exists(),
    reason=("data/benchmark_geom/kcs.stl absent — run "
            "`python scripts/fetch_benchmark_geom.py`. The gate's other "
            "assertions do NOT depend on this artefact; this one test raises "
            "the partition claim from a lofted fixture to a real ship hull."))
def test_the_partition_holds_on_the_real_kcs_hull(tmp_path):
    """Bar 3 on genuinely real geometry: the KCS half body.

    The lofted fixture above is closed, has a stem and a forefoot, and is
    enough to test the partition logic — but KCS is the hull with published
    data, it is the one a slamming number would eventually be compared on, and
    it has the features a fixture does not: a bulbous bow, a sonar dome and a
    tessellation that came out of a NURBS sewing rather than out of this test.

    It is also the hull whose STL spans 0..7.7165 m against Lpp 7.2786 because
    the bulb reaches past the perpendicular, which is why the cut is measured
    back from the FILE'S OWN STEM and not from `lwl` — the two differ by 0.44 m
    on this hull, i.e. by 30% of the bow patch's own length.
    """
    out = tmp_path / "kcs"
    C.write_resistance_case_from_stl(_KCS_STL, 7.2786, 1.5, out, end_time=1.0,
                                     np_procs=1, symmetric=True)
    stl = out / "constant" / "triSurface" / "hull.stl"
    solids = _solids(stl)
    bow, main = solids[C._STL_BOW_SOLID], solids[C._STL_MAIN_SOLID]
    whole = _facet_blocks(stl)

    assert bow and main
    assert len(bow) < len(whole) and len(main) < len(whole)
    assert sorted(bow + main) == sorted(whole)
    assert sorted(whole) == sorted(_facet_blocks(_KCS_STL))   # nothing moved

    info = dict(l.split("=", 1) for l in (out / "case.info").read_text()
                .splitlines() if "=" in l and not l.startswith(" "))
    # THE CUT IS TAKEN FROM THE SURFACE, NOT FROM `lwl`, and KCS is the hull
    # where the two differ: the STL spans 0..7.7165 m against Lpp 7.2786
    # because the bulb and rudder reach past the perpendiculars, so the patch
    # is 1.5433 m rather than 1.4557 m — 6% longer. abs=1e-4 because case.info
    # writes these with %.4f; the tolerance is the receipt's own precision.
    assert float(info["bow_patch_stem_x_m"]) > 7.2786
    assert float(info["bow_patch_hull_length_m"]) == pytest.approx(7.7165,
                                                                   abs=1e-3)
    assert (float(info["bow_patch_stem_x_m"])
            - float(info["bow_patch_x_split_m"])) == pytest.approx(
                C.BOW_PATCH_FRACTION * 7.7165, abs=1e-3)

    # The forward-rounding overhang, MEASURED rather than bounded: split plane
    # x = 6.1732 m, patch aft edge x = 6.1474 m, i.e. 25.8 mm = 0.33% of the
    # hull's length, and 2202 of 10402 facets (21.2%) against a nominal 20%.
    # Pinned so a change to the membership rule cannot quietly move the patch.
    assert float(info["bow_patch_x_split_m"]) == pytest.approx(6.1732, abs=1e-4)
    assert float(info["bow_patch_x_aftmost_m"]) == pytest.approx(6.1474,
                                                                 abs=1e-4)
    assert info["bow_patch_facets"].startswith("2202 of 10402")
    # The benchmark identity survives the split: `stl_sha256` still names KCS,
    # because it is the hash of the geometry AS DELIVERED, and the split
    # rewrites only the file on disk.
    assert info["benchmark"] == "kcs"
    assert info["stl_sha256"] != info["stl_sha256_shipped"]


def test_the_cut_does_not_move_when_the_caller_changes_lwl(tmp_path):
    """MEASURED 2026-08-13, and the guard caught it on its first full run.

    The first version of `split_bow_region` cut at `x_stem - fraction * lwl`,
    mixing the STL's coordinate system with the caller's length scale.
    `tests/test_phase2.py::test_mesh_is_froude_similar_at_any_hull_size` meshes
    the SAME 7.7165 m KCS model STL at lwl 7.2786, 29.1 and 230.0 to prove the
    background mesh is geometrically similar at constant Froude number — a
    legitimate call, and at k = 31.6 the split plane landed at **x = -38.28 m**
    with all 10402 facets in the bow solid and none in main.

    The refusal was correct and the RULE was wrong: a guard firing on a
    legitimate call is a wrong rule, not a caught bug. The cut is now taken
    from the surface's own x-extent and has no length argument to disagree
    with. Asserted here by generating the same geometry at two wildly different
    `lwl` values and demanding the split plane be identical — the verbatim
    shape of the call that broke it.
    """
    src = tmp_path / "src.stl"
    _lofted_hull_stl(src)

    def _split_plane(lwl: float, tag: str) -> float:
        out = tmp_path / tag
        C.write_resistance_case_from_stl(src, lwl, 2.0, out, end_time=1.0,
                                         np_procs=1)
        return float([l.split("=")[1] for l in
                      (out / "case.info").read_text().splitlines()
                      if l.startswith("bow_patch_x_split_m=")][0])

    assert _split_plane(_LWL, "a") == _split_plane(_LWL * 31.6, "b")


def test_the_bow_instrument_never_claims_to_be_the_whole_slamming_load(tmp_path):
    """The target vessel is a CATAMARAN, and bow slam is not its governing one.

    For a catamaran the governing slam is usually CROSS-STRUCTURE (WET-DECK)
    slamming — the bridge deck between the demihulls impacting the wave surface
    in head seas. A wave-piercing bow is designed to reduce BOW slam and does
    nothing for the wet deck, so a green `bowSlammingPressure` is not evidence
    that the vessel is safe in a seaway.

    This is the same discipline as the deck-in-air hazard: a number that
    answers a narrower question than its name suggests is how this project has
    been burned repeatedly, and prose that only lives in a source file is not
    read by someone holding a run directory. The caveat is therefore asserted
    in the two places a future session actually reads — the module that
    computes it and the `case.info` of every case that measures it.
    """
    text = (Path(seakeeping.__file__).read_text()
            + Path(C.__file__).read_text())
    for term in ("wet-deck", "catamaran", "cross-structure"):
        assert term in text.lower(), term

    info = (_case(tmp_path) / "case.info").read_text().lower()
    assert "wet-deck" in info and "bow" in info

    # And the physics helper is NOT bow-specific: it takes an angle, a velocity
    # and a density, so the wet-deck case is a second CALL SITE. A second
    # implementation of the same physics is this repo's signature defect —
    # gate2m.py shipped a second GCI that returned -27.027% and printed PASS.
    import inspect
    sig = inspect.signature(seakeeping.slam_pressure)
    assert list(sig.parameters) == ["deadrise_deg", "v_entry", "rho"]
    assert "bow" not in inspect.signature(
        seakeeping.wagner_impact_cp).__str__().lower()
