"""venv side: drive the installed Blender binary across the process boundary.

Nothing here imports `bpy`. Blender is invoked as a subprocess with
`--background --python navalai/blender/build_hull.py`, which is the ONLY
supported way to reach it from cp312 — see this package's `__init__` for why
`import bpy` is not on the table.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from ..geometry import Hull
from .spec import BLENDER_BIN, write_spec

_SCRIPT = Path(__file__).with_name("build_hull.py")
_RENDER = Path(__file__).with_name("render_hull.py")


def have_blender(binary: str = BLENDER_BIN) -> bool:
    """Is the Blender binary present and executable on this node?

    Used by `tests/test_blender_hull.py` to skip rather than fail on a machine
    without it — fortress001 has no `/Applications`. It checks the FILE, never
    `shutil.which`: a PATH lookup is a property of the caller's environment,
    and reading an empty one as "not installed" is the exact mistake that sent
    a prior session down a `pip install bpy` path. (On this node the PATH
    lookup happens to succeed too, via a Homebrew cask wrapper — which is
    precisely why it must not be the test.)
    """
    return os.access(binary, os.X_OK)


class BlenderError(RuntimeError):
    """Blender exited non-zero, or produced no receipt.

    Raised rather than returning a default. A build whose outcome could not be
    read is not a build that succeeded (docs/LESSONS.md defect class 1).
    """


def blender_version(binary: str = BLENDER_BIN) -> str:
    """First line of `Blender --version`, or raise.

    MEASURED 2026-08-12 on this node: `Blender 5.2.0 LTS`.
    """
    out = subprocess.run([binary, "--version"], capture_output=True, text=True,
                         timeout=120)
    if out.returncode != 0:
        raise BlenderError(f"{binary} --version exited {out.returncode}")
    return out.stdout.strip().splitlines()[0].strip()


def build_via_blender(hull: Hull, out_stl: str | Path, nx: int, nz: int,
                      subsurf: int = 0, voxel: float | None = None,
                      workdir: str | Path | None = None,
                      binary: str = BLENDER_BIN,
                      ascii_stl: bool = True, timeout: float = 1800.0,
                      crease_angle_deg: float | None = None) -> dict:
    """Generate `out_stl` through Blender; returns the build receipt.

    The receipt carries the Blender and embedded-Python versions, the applied
    modifier settings, the triangle/vertex counts, the non-manifold and open
    edge counts and the bmesh signed volume. `wall_s` is added here.
    """
    out_stl = Path(out_stl)
    out_stl.parent.mkdir(parents=True, exist_ok=True)
    wd = Path(workdir) if workdir is not None else out_stl.parent
    wd.mkdir(parents=True, exist_ok=True)
    spec = write_spec(hull, wd / f"{out_stl.stem}.spec.json", nx, nz,
                      subsurf=subsurf, voxel=voxel, ascii_stl=ascii_stl,
                      crease_angle_deg=crease_angle_deg)
    receipt = wd / f"{out_stl.stem}.receipt.json"

    t0 = time.time()
    proc = subprocess.run(
        [binary, "--background", "--factory-startup", "--python", str(_SCRIPT),
         "--", "--spec", str(spec), "--out", str(out_stl),
         "--receipt", str(receipt)],
        capture_output=True, text=True, timeout=timeout)
    wall = time.time() - t0
    if proc.returncode != 0 or not receipt.exists():
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-40:])
        raise BlenderError(
            f"blender exited {proc.returncode}; receipt "
            f"{'present' if receipt.exists() else 'ABSENT'}\n{tail}")
    rep = json.loads(receipt.read_text())
    rep["wall_s"] = wall
    rep["stl_bytes"] = out_stl.stat().st_size
    rep["spec"] = str(spec)
    receipt.write_text(json.dumps(rep, indent=1))
    return rep


def render_via_blender(stl: str | Path, out_png: str | Path,
                       samples: int = 64, res: int = 960,
                       engine: str = "CYCLES", binary: str = BLENDER_BIN,
                       timeout: float = 3600.0) -> dict:
    """Cycles-render `stl` to `out_png`; returns the render receipt.

    The receipt records `engine_after_set` — what the scene actually held when
    the render ran — because the engine ENUM is not a reliable capability
    check on this build: it lists only BLENDER_EEVEE even after the cycles
    add-on is enabled and `render.engine = 'CYCLES'` has succeeded.
    """
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    receipt = out_png.with_suffix(".render.json")
    proc = subprocess.run(
        [binary, "--background", "--factory-startup", "--python", str(_RENDER),
         "--", "--stl", str(stl), "--out", str(out_png),
         "--samples", str(samples), "--res", str(res), "--engine", engine,
         "--receipt", str(receipt)],
        capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0 or not receipt.exists():
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-40:])
        raise BlenderError(f"blender render exited {proc.returncode}\n{tail}")
    return json.loads(receipt.read_text())
