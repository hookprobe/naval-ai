"""BLENDER SIDE. Cycles render of a hull STL — NEVER import navalai.

    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python navalai/blender/render_hull.py -- \
        --stl hull.stl --out hull.png --samples 64 --receipt r.json

WHAT THIS ESTABLISHES, AND WHAT IT DOES NOT. It establishes that the installed
Blender can put a Cycles image on disk from an STL this pipeline already
writes, and how long that takes on this node. It does NOT establish anything
about rendering a CFD FREE SURFACE: Blender reads no OpenFOAM and no VTK (its
importers on this build are alembic / fbx / gltf / obj / ply / stl / usd /
svg-curve, MEASURED), so the wave field needs a polygonal intermediate
produced upstream. See `docs/research/BLENDER.md`.

CYCLES IS AN ADD-ON AND IS NOT ON BY DEFAULT UNDER `--factory-startup`.
MEASURED 2026-08-12: `bpy.types.RenderSettings.engine`'s enum lists only
`BLENDER_EEVEE` until `addon_utils.enable("cycles")` runs, and the enum STILL
reads `['BLENDER_EEVEE']` afterwards while `scene.render.engine = 'CYCLES'`
nevertheless succeeds — so the enum is not a reliable capability check and the
receipt records `engine_after_set`, i.e. what the scene actually held when the
render ran. An assumed engine would be exactly the "unmeasurable value scored
as a passing one" this project keeps paying for.
"""

import argparse
import json
import math
import sys
import time

import addon_utils
import bpy


def _parse(argv):
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--stl", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--res", type=int, default=960)
    ap.add_argument("--receipt", default=None)
    ap.add_argument("--engine", default="CYCLES")
    return ap.parse_args(argv)


def _scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"
    return sc


def _material(name, rgba, rough, metallic=0.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if "Transmission Weight" in b.inputs:
        b.inputs["Transmission Weight"].default_value = transmission
    return m


def main():
    a = _parse(sys.argv)
    sc = _scene()

    enabled = None
    if a.engine == "CYCLES":
        enabled = str(addon_utils.enable("cycles", default_set=True))
    enum_before = [i.identifier for i in
                   bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    try:
        sc.render.engine = a.engine
    except TypeError as exc:                                  # noqa: BLE001
        print(f"FATAL: engine {a.engine} unavailable: {exc}")
        return 1
    engine_after = sc.render.engine

    device = "CPU"
    if engine_after == "CYCLES":
        sc.cycles.samples = a.samples
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = "METAL"
            prefs.get_devices()
            for d in prefs.devices:
                d.use = (d.type == "METAL")
            sc.cycles.device = "GPU"
            device = "GPU/METAL"
        except Exception as exc:                              # noqa: BLE001
            print(f"GPU unavailable, staying on CPU: {exc}")

    bpy.ops.wm.stl_import(filepath=a.stl, forward_axis="Y", up_axis="Z",
                          global_scale=1.0)
    ob = bpy.context.selected_objects[0]
    n_tris = len(ob.data.polygons)
    bb = [ob.matrix_world @ v.co for v in ob.data.vertices]
    xs = [p.x for p in bb]
    ys = [p.y for p in bb]
    zs = [p.z for p in bb]
    lwl = max(xs) - min(xs)
    cx, cy = 0.5 * (max(xs) + min(xs)), 0.5 * (max(ys) + min(ys))

    ob.data.materials.append(_material("hull", (0.72, 0.74, 0.78, 1.0), 0.25,
                                       metallic=0.15))
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(25.0))

    # A sea plane at z = 0 — the waterline this project's geometry is built
    # about. It is DECORATION, not a free surface: no CFD field is involved.
    bpy.ops.mesh.primitive_plane_add(size=20 * lwl, location=(cx, cy, 0.0))
    sea = bpy.context.active_object
    sea.data.materials.append(_material("sea", (0.02, 0.09, 0.14, 1.0), 0.08,
                                        transmission=0.6))

    bpy.ops.object.light_add(type="SUN", location=(cx - lwl, cy - lwl, lwl))
    sun = bpy.context.active_object
    sun.data.energy = 4.0
    sun.data.angle = math.radians(1.5)
    sun.rotation_euler = (math.radians(52), 0.0, math.radians(35))

    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = \
        (0.28, 0.42, 0.62, 1.0)
    sc.world = world

    cam_d = 1.5 * lwl
    bpy.ops.object.camera_add(
        location=(cx + 0.95 * cam_d, cy - 0.85 * cam_d, 0.42 * cam_d))
    cam = bpy.context.active_object
    sc.camera = cam
    trk = cam.constraints.new(type="TRACK_TO")
    bpy.ops.object.empty_add(location=(cx, cy, 0.5 * (max(zs) + min(zs))))
    trk.target = bpy.context.active_object
    trk.track_axis = "TRACK_NEGATIVE_Z"
    trk.up_axis = "UP_Y"

    sc.render.resolution_x = a.res
    sc.render.resolution_y = int(a.res * 0.625)
    sc.render.filepath = a.out
    sc.render.image_settings.file_format = "PNG"

    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    wall = time.time() - t0

    import os
    rep = {"stl": a.stl, "out": a.out, "n_tris": n_tris, "lwl_m": lwl,
           "engine_requested": a.engine, "engine_after_set": engine_after,
           "engine_enum": enum_before, "cycles_addon_enable": enabled,
           "device": device, "samples": a.samples,
           "resolution": [sc.render.resolution_x, sc.render.resolution_y],
           "render_s": wall,
           "png_bytes": os.path.getsize(a.out) if os.path.exists(a.out) else 0,
           "blender_version": list(bpy.app.version)}
    if a.receipt:
        with open(a.receipt, "w") as fh:
            json.dump(rep, fh, indent=1)
    print("RENDER_RECEIPT " + json.dumps(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
