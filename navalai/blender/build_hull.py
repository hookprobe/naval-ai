"""BLENDER SIDE. Runs inside Blender's embedded Python — NEVER import navalai.

    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python navalai/blender/build_hull.py -- \
        --spec spec.json --out hull.stl --receipt receipt.json

MEASURED on this node 2026-08-12: Blender 5.2.0 LTS, embedded CPython 3.13.13,
numpy 2.3.4. The project venv is cp312, so this file's import list is `bpy`,
`bmesh`, `mathutils` and the standard library, and nothing else.

WHAT IT DOES, AND WHY EACH STEP IS THERE
----------------------------------------
1. Sets `scene.unit_settings.system = 'METRIC'` and `scale_length = 1.0`
   EXPLICITLY. The startup file's units are not contractual and the hull is
   metric everywhere else in this project (`navalai/limits.py` is in metres).
2. Builds vertices from the starboard grid plus its y-mirror, WELDED on the
   exact float tuple. Welding is not cosmetic: the keel row has y == 0 on both
   sides and the stem station collapses to the centreline (w -> 0 at x = L, so
   y_chine and y_sheer are both 0 there), so an unwelded build duplicates two
   whole rows of vertices and the surface is not a manifold. The weld key is
   the exact tuple, i.e. the same bit-identical rule as
   `navalai.stl_forensics.weld`, so it merges what is coincident and moves
   nothing.
3. Builds quads with `closed_mesh`'s winding, transcribed and cited below.
   Faces with fewer than three distinct vertices are dropped, and after
   triangulation any triangle under 1e-10 m^2 is removed by COLLAPSING its
   shortest edge — the same bar `closed_mesh.quad` applies, because the stem
   cap is degenerate on every hull this grammar emits. It used to be removed
   by DELETING the face, which punched two holes in the 0.05 m voxel remesh;
   `_triangulate_and_clean` carries the measurement.
4. Optionally applies Catmull-Clark subdivision and/or the voxel Remesh
   modifier, both recorded in the receipt.
5. Exports STL via `bpy.ops.wm.stl_export`.

THE EXPORTER'S AXIS ARGUMENTS ARE A TRAP AND ARE PASSED EXPLICITLY.
`wm.stl_export` maps scene axes onto file axes, and its defaults are NOT the
identity for this project's convention (x aft-to-forward, y to starboard,
z up). Passing `forward_axis='Y', up_axis='Z'` is the identity, and
`tests/test_blender_hull.py` asserts a round trip reproduces the input
coordinates rather than trusting that. `global_scale=1.0` for the same reason.

FLOAT PRECISION IS A REAL COST AND IS NOT HIDDEN. Blender stores mesh
coordinates in SINGLE precision. The spec arrives as float64 and comes back
quantised; the receipt records the max coordinate round-trip error so the
number is on the record rather than inferred.
"""

import argparse
import json
import sys

import bpy  # noqa: F401  (Blender-only)
import bmesh


def _parse(argv):
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--receipt", default=None)
    return ap.parse_args(argv)


def _clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"


def _build_arrays(spec):
    """(verts, quads) welded on the exact float tuple.

    `grid` is the starboard side; port is the y-mirror. Winding is transcribed
    from `navalai.geometry.Hull.closed_mesh`, including the deck-lid winding
    that commit history records as having pointed the ENTIRE DECK DOWN INTO
    THE HULL (397 flipped triangles, signed volume understated by 38.1%)
    before it was fixed there. A second copy of a winding rule is exactly the
    defect that produced that, which is why the fence on this file is a
    signed-volume comparison against `closed_mesh` and not a code review.
    """
    nx, nzp1, _ = spec["grid_shape"]
    nz = nzp1 - 1
    flat = spec["grid"]
    verts = []
    index = {}

    def vid(x, y, z):
        key = (x, y, z)
        got = index.get(key)
        if got is None:
            got = len(verts)
            index[key] = got
            verts.append([x, y, z])
        return got

    S = [[0] * nzp1 for _ in range(nx)]
    P = [[0] * nzp1 for _ in range(nx)]
    for i in range(nx):
        for j in range(nzp1):
            o = (i * nzp1 + j) * 3
            x, y, z = flat[o], flat[o + 1], flat[o + 2]
            S[i][j] = vid(x, y, z)
            # -0.0 == 0.0 compares True and hashes equal in CPython, so the
            # keel row (y == 0.0) welds to itself across the mirror without a
            # tolerance. Verified by the receipt's vertex count, which is
            # strictly below 2*nx*(nz+1).
            P[i][j] = vid(x, -y, z)

    quads = []
    for i in range(nx - 1):
        for j in range(nz):
            quads.append((S[i][j], S[i][j + 1], S[i + 1][j + 1], S[i + 1][j]))
            quads.append((P[i + 1][j], P[i + 1][j + 1], P[i][j + 1], P[i][j]))
        quads.append((S[i][nz], P[i][nz], P[i + 1][nz], S[i + 1][nz]))
    for j in range(nz):                                    # transom, outward -x
        quads.append((S[0][j], P[0][j], P[0][j + 1], S[0][j + 1]))
    for j in range(nz):                                    # stem, outward +x
        quads.append((S[-1][j], S[-1][j + 1], P[-1][j + 1], P[-1][j]))

    keep = [q for q in quads if len(set(q)) >= 3]
    return verts, keep


def _make_object(verts, quads):
    me = bpy.data.meshes.new("hull")
    # A quad with a repeated vertex is invalid to from_pydata; those were
    # already dropped. Degenerate-by-AREA faces survive here and are removed
    # after triangulation, where the area bar is the one closed_mesh uses.
    faces = [list(dict.fromkeys(q)) for q in quads]
    me.from_pydata(verts, [], faces)
    me.validate(verbose=False)
    ob = bpy.data.objects.new("hull", me)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    return ob


def _crease_sharp_edges(ob, angle_deg):
    """Crease every cage edge whose dihedral exceeds `angle_deg`; return count.

    THIS IS BLENDER'S BEST EFFORT AND MEASURING WITHOUT IT WOULD BE A
    STRAWMAN. Catmull-Clark smooths a knuckle away by construction, but
    Blender's subdivision honours per-edge creases, so the fair question is
    not "does default subsurf keep the chine" (it cannot) but "does creased
    subsurf keep it".

    The bar is the PIPELINE'S OWN: `navalai/cfd/case.py` writes
    `includedAngle 150` for `surfaceFeatureExtract`, i.e. a 30 degree normal
    jump, so an edge that is a feature to the mesher is an edge that gets a
    crease here. Using any other angle would be a second bar for one question.
    Selecting by angle rather than by row index also keeps this file free of a
    transcription of `Hull.chine_row`, and picks up the keel, the deck edge
    and the transom corner for free.
    """
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    layer = bm.edges.layers.float.get("crease_edge") or \
        bm.edges.layers.float.new("crease_edge")
    n = 0
    bar = angle_deg * 3.14159265358979 / 180.0
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > bar:
            e[layer] = 1.0
            n += 1
    bm.to_mesh(ob.data)
    bm.free()
    return n


def _apply_modifiers(ob, subsurf, voxel):
    if subsurf:
        m = ob.modifiers.new("subsurf", "SUBSURF")
        m.subdivision_type = "CATMULL_CLARK"
        m.levels = subsurf
        m.render_levels = subsurf
        # `use_limit_surface` off makes the applied mesh the exact `levels`-th
        # subdivision rather than a limit-surface approximation of it, so the
        # measurement is of Catmull-Clark itself.
        if hasattr(m, "use_limit_surface"):
            m.use_limit_surface = False
        bpy.ops.object.modifier_apply(modifier=m.name)
    if voxel:
        m = ob.modifiers.new("remesh", "REMESH")
        m.mode = "VOXEL"
        m.voxel_size = voxel
        m.adaptivity = 0.0
        bpy.ops.object.modifier_apply(modifier=m.name)


def _tri_area(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    return 0.5 * (cx * cx + cy * cy + cz * cz) ** 0.5


def _edge_len(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
            + (a[2] - b[2]) ** 2) ** 0.5


def _triangulate_and_clean(ob, area_bar=1e-10):
    """Fan-triangulate each face from its FIRST loop vertex, then COLLAPSE
    slivers — never delete them.

    DONE IN PYTHON, NOT BY `bmesh.ops.triangulate`, and that is a measurement
    rather than a preference. `closed_mesh.quad` splits (v0,v1,v2)+(v0,v2,v3)
    off the loop as given; Blender's default `quad_method="BEAUTY"` picks the
    SHORTER DIAGONAL instead, and these quads are WARPED — a ruled panel
    between two non-parallel section polylines is not planar — so the diagonal
    is part of the shape and the other one is a different surface.

    MEASURED on hull 14 at 600x120:

        triangulation                  surfaceCheck self-intersections
        current path (closed_mesh)     166, all at x/L <= 0.042 (transom cap)
        bmesh BEAUTY                   332, spread over x/L 0.00 .. 1.00
        bmesh FIXED                    387, spread over x/L 0.00 .. 1.00
        this fan, off me.polygons      see docs/research/BLENDER.md

    `bmesh.ops.triangulate` with `quad_method="FIXED"` did NOT reproduce the
    split: 23263 of 288836 triangles still differed from the current path's,
    because bmesh does not guarantee it starts the split at the loop vertex
    the face was built with. `me.polygons` DOES preserve the loop order given
    to `from_pydata` (verified directly), so the fan is taken there.

    THE SLIVER RULE WAS `continue`, AND THAT PUNCHED HOLES IN THE SURFACE.
    MEASURED 2026-08-20 on `sample_valid(25, MissionSpec(), seed=0)[14]` at
    the shipped 600x120 with the owner's `voxel_size = 0.05` Remesh: this
    function reported `n_degenerate_dropped 4` and `n_open_edges 8`, and
    `tests/test_blender_hull.py::
    test_the_voxel_remesh_stays_closed_and_that_is_not_the_point` failed
    `assert 8 == 0` against a finding that had recorded the remesh as a CLOSED
    manifold. The eight edges are the boundaries of two mirror-image
    micro-quads the voxel remesher emits at the transom/deck/sheer corner:

        x                y            z          edge lengths
        -3.3527613e-08  -1.4000001    1.4499998   2.0e-07 (z)
         2.6106330e-06  -1.4000001    1.4500000   2.6e-06 (x)
        (and the same four vertices mirrored to y = +1.4000001)

    Each quad is ~5.3e-13 m^2, i.e. two fan triangles under the 1e-10 m^2 bar,
    and DELETING a face whose three vertices are distinct leaves its three
    edges bounded by one face each. An open shell is not a cosmetic defect
    here: CLAUDE.md's CFD section records that interFoam floods the interior
    of one, and `stl_watertight_report` gates exactly this.

    So a degenerate triangle is now removed by COLLAPSING ITS SHORTEST EDGE.
    A collapse cannot open a closed surface — it merges two vertices, and the
    faces that degenerate as a result have a REPEATED vertex, so each of them
    contributes its surviving edge twice and removing it leaves every edge
    count even. It also cannot move the surface: the vertex moves by exactly
    the length of the edge collapsed, and the SHORTEST edge of each of these
    four is the 2.0e-07 m one in z, so `weld_max_move_m` MEASURES
    2.384185791015625e-07 m — a quarter micron, below the 9.4e-07 m
    single-precision coordinate round trip the same receipt records. Signed
    volume moves from 112.94397334442795 to 112.94397334438304 m^3, 4e-13
    relative. RE-MEASURED after the fix: `n_open_edges` and
    `n_non_manifold_edges` are both 0 on the voxel arm of both reference
    hulls, and the STL read back through `stl_forensics.edge_table` agrees.

    A degenerate whose SHORTEST edge exceeds `area_bar ** 0.5` (1e-05 m at the
    shipped bar) is a CAP — three nearly collinear vertices far apart — and
    collapsing it would move geometry by that distance. Those are KEPT and
    COUNTED as `n_degenerate_kept` rather than deleted: a case this function
    cannot fix is reported, never converted into a hole (docs/LESSONS.md
    defect class 1). MEASURED on both arms of both reference hulls, that count
    is 0; the four voxel slivers are all needles.

    THE CAGE ARM IS UNAFFECTED AND THAT IS MEASURED, not argued: at 600x120
    the un-remeshed grid produces `n_degenerate_faces` 0 on both the round
    bilge and the hard chine (the stem cap's quads collapse to fewer than
    three DISTINCT vertices in `_build_arrays` and never reach this bar), so
    this branch does not execute on the shipped path at all.
    """
    me = ob.data
    me.calc_loop_triangles() if hasattr(me, "calc_loop_triangles") else None
    coords = [tuple(v.co) for v in me.vertices]
    raw = []
    for p in me.polygons:
        loop = list(p.vertices)
        for k in range(1, len(loop) - 1):
            raw.append((loop[0], loop[k], loop[k + 1]))

    # Union-find over vertices; the representative is the LOWEST index, so
    # the weld is a deterministic function of the mesh and not of iteration
    # order.
    parent = list(range(len(coords)))

    def _find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    weld_bar = area_bar ** 0.5
    n_degen = n_collapsed = n_kept = 0
    weld_move = 0.0
    for t in raw:
        if _tri_area(coords[t[0]], coords[t[1]], coords[t[2]]) > area_bar:
            continue
        n_degen += 1
        e = min(((_edge_len(coords[a], coords[b]), a, b)
                 for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0]))))
        if e[0] > weld_bar:
            n_kept += 1               # a CAP: not collapsible, so keep it
            continue
        n_collapsed += 1
        ra, rb = _find(e[1]), _find(e[2])
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    tris = []
    n_welded_away = 0
    for t in raw:
        u = (_find(t[0]), _find(t[1]), _find(t[2]))
        if len(set(u)) < 3:
            n_welded_away += 1
            continue
        tris.append(u)
    for i in range(len(coords)):
        r = _find(i)
        if r != i:
            weld_move = max(weld_move, _edge_len(coords[i], coords[r]))

    new = bpy.data.meshes.new(me.name + "_tri")
    new.from_pydata(coords, [], tris)
    new.validate(verbose=False)
    old = ob.data
    ob.data = new
    bpy.data.meshes.remove(old)

    bm = bmesh.new()
    bm.from_mesh(new)
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    open_edges = sum(1 for e in bm.edges if len(e.link_faces) < 2)
    vol = bm.calc_volume(signed=True)
    n_v, n_f, n_e = len(bm.verts), len(bm.faces), len(bm.edges)
    bm.to_mesh(new)
    bm.free()
    return {"n_verts": n_v, "n_tris": n_f, "n_edges": n_e,
            # `n_degenerate_dropped` was the old key and it is GONE rather
            # than kept beside these: it named the operation that punched the
            # holes, and it was answering several questions at once. Each of
            # the five below answers exactly one, so no reader has to guess
            # which. No other module in the tree read the old key (grepped).
            "n_degenerate_faces": n_degen,
            "n_degenerate_collapsed": n_collapsed,
            "n_degenerate_kept": n_kept,
            "n_faces_welded_away": n_welded_away,
            "weld_max_move_m": weld_move,
            "n_non_manifold_edges": non_manifold,
            "n_open_edges": open_edges,
            "signed_volume_m3": vol}


def _coord_roundtrip_error(ob, verts):
    """Max |single-precision coordinate - float64 input| over shared points.

    Only meaningful when no modifier ran; otherwise the vertex sets differ and
    this returns None rather than a number that would look like a precision
    figure and be a resampling figure. An unmeasurable value is never scored
    as a good one (docs/LESSONS.md defect class 1).
    """
    if len(ob.data.vertices) != len(verts):
        return None
    worst = 0.0
    for bv, sv in zip(ob.data.vertices, verts):
        for a, b in zip(bv.co, sv):
            d = abs(a - b)
            if d > worst:
                worst = d
    return worst


def main():
    args = _parse(sys.argv)
    with open(args.spec) as fh:
        spec = json.load(fh)
    build = spec.get("build", {})

    _clear_scene()
    verts, quads = _build_arrays(spec)
    ob = _make_object(verts, quads)
    pre = {"n_verts_built": len(verts), "n_quads_built": len(quads)}
    rt = _coord_roundtrip_error(ob, verts)
    crease = build.get("crease_angle_deg")
    pre["n_creased_edges"] = (_crease_sharp_edges(ob, float(crease))
                              if crease else 0)
    pre["crease_angle_deg"] = crease
    _apply_modifiers(ob, int(build.get("subsurf", 0) or 0),
                     build.get("voxel_m"))
    rep = _triangulate_and_clean(ob)

    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.wm.stl_export(
        filepath=args.out,
        export_selected_objects=True,
        ascii_format=bool(build.get("ascii_stl", True)),
        apply_modifiers=True,
        global_scale=1.0,
        use_scene_unit=False,
        forward_axis="Y",
        up_axis="Z",
    )

    rep.update(pre)
    rep["coord_roundtrip_max_m"] = rt
    rep["blender_version"] = list(bpy.app.version)
    rep["python_version"] = sys.version.split()[0]
    rep["unit_system"] = bpy.context.scene.unit_settings.system
    rep["scale_length"] = bpy.context.scene.unit_settings.scale_length
    rep["build"] = build
    rep["out"] = args.out
    if args.receipt:
        with open(args.receipt, "w") as fh:
            json.dump(rep, fh, indent=1)
    print("RECEIPT " + json.dumps(rep))


if __name__ == "__main__":
    main()
