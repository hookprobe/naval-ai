#!/usr/bin/env bash
# Build the free-motion wave-riding case from scratch, reproducibly.
#
# WHY A SCRIPT. This case needs five edits on top of the generator, and doing
# them by hand cost three false starts in one afternoon: a `//` comment before
# a closing brace commented the brace out (FATAL IO ERROR), and later a
# `rm -rf <case>/[0-9]*` glob matched `0.orig` and destroyed the initial
# conditions (cannot find pointDisplacement). Both were MY errors, not the
# solver's, and both are the kind that only stop happening when the procedure
# stops being retyped.
#
# Usage: bash setup_wave_riding_case.sh [case_dir]
set -euo pipefail
cd "$(dirname "$0")/../.."
CASE="${1:-runs/hookprobe_seas_free}"
HULL=runs/hookprobe_inspect/hull-v3-8t-pipeline.stl
H=2.0; T=4.5; RAMP=9.0        # incident sea: 2 m, 4.5 s, 9 s ramp

rm -rf "$CASE"
source ~/.venvs/naval/bin/activate

# --wave-height sizes the ungraded core band AND the snappy refinement box to
# the incident wave. Without it both are sized off Lwl for a ship's own wake
# (+-0.296 m against a +-1.0 m sea) and the crests ride in coarse cells.
python scripts/make_case.py --out "$CASE" --stl "$HULL" --lwl 11.84 \
  --speed 2.57 --symmetric --transient --free-motion --kg 1.1 \
  --n-layers 10 --end-time 45 --np 10 --wave-height "$H" | tail -1

python - "$CASE" "$H" "$T" "$RAMP" <<'PYEOF'
import re, sys
from pathlib import Path
c, H, T, RAMP = Path(sys.argv[1]), *map(float, sys.argv[2:5])

(c/"constant/waveProperties").write_text(f"""FoamFile
{{ version 2.0; format ascii; class dictionary; object waveProperties; }}
inlet
{{
    alpha            alpha.water;
    waveModel        StokesII;
    nPaddle          1;
    waveHeight       {H};
    waveAngle        0.0;
    rampTime         {RAMP};
    activeAbsorption yes;
    wavePeriod       {T};
}}
outlet
{{ alpha alpha.water; waveModel shallowWaterAbsorption; nPaddle 1; }}
""")

u = c/"0.orig/U"; t = u.read_text()
t = t.replace("internalField uniform (-2.57 0 0);", "internalField uniform (0 0 0);")
t = t.replace("  inlet      { type fixedValue; value uniform (-2.57 0 0); }",
              "  inlet      { type waveVelocity; value uniform (0 0 0); }")
t = re.sub(r"  outlet     \{ type outletPhaseMeanVelocity;[^}]*\}",
           "  outlet     { type waveVelocity; value uniform (0 0 0); }", t, flags=re.S)
u.write_text(t)

a = c/"0.orig/alpha.water"; t = a.read_text()
t = re.sub(r"  inlet      \{ type exprFixedValue;.*?\n(?=  outlet)",
           "  inlet      { type waveAlpha; value uniform 0; }\n", t, flags=re.S)
t = re.sub(r"  outlet     \{ type variableHeightFlowRate;[^}]*\}",
           "  outlet     { type zeroGradient; }", t, flags=re.S)
a.write_text(t)

# dampers 45% -> 5% of critical. WHOLE-LINE rewrites: an inline // before the
# closing brace comments the brace out.
d = c/"constant/dynamicMeshDict"; out = []
for ln in d.read_text().splitlines():
    if "linearDamper" in ln and "coeff" in ln:
        v = float(re.search(r"coeff ([0-9.]+);", ln).group(1))
        out.append(f"    heaveDamper {{ sixDoFRigidBodyMotionRestraint linearDamper; coeff {v/9:.1f}; }}")
    elif "sphericalAngularDamper" in ln and "coeff" in ln:
        v = float(re.search(r"coeff ([0-9.]+);", ln).group(1))
        out.append(f"    pitchDamper {{ sixDoFRigidBodyMotionRestraint sphericalAngularDamper; coeff {v/9:.1f}; }}")
    else:
        out.append(ln)
d.write_text("\n".join(out) + "\n")

# ADDED-MASS INSTABILITY. MEASURED 2026-08-28: on four runs the heave
# velocity ran smoothly at +0.16 m/s and then jumped to +6226.88 m/s in ONE
# timestep, at t=5.83-5.96 every time, across two linear solvers and three
# meshes. A single-step explosion from a smooth state is not a mesh failure
# and not a Courant failure — it is the explicit fluid/body coupling going
# unstable, which happens when the added mass exceeds the body mass. This
# hull: 3897 kg (half) against a heave added mass of order 4000-8000 kg, i.e.
# squarely in the unstable regime.
#   accelerationRelaxation 0.3 -> 0.1  (relax the acceleration update harder)
#   nIter 1 -> 3                       (sub-iterate the coupling each step)
d2 = c/"constant/dynamicMeshDict"; t = d2.read_text()
t = t.replace("accelerationRelaxation 0.3;",
              "accelerationRelaxation 0.1;\n    nIter 3;")
d2.write_text(t)

s = c/"system/fvSolution"; t = s.read_text()
t = t.replace("nOuterCorrectors 2;", "nOuterCorrectors 5;")
t = t.replace("nNonOrthogonalCorrectors 1;", "nNonOrthogonalCorrectors 2;")
# GAMG's scaleCorrection divides by a quantity that reaches zero on a moving
# mesh: sigFpe inside GAMGSolver::scale at t~5.9 on THREE meshes with every
# field healthy. PCG/DIC carries no such division.
t = t.replace("  p_rgh { solver GAMG; smoother DIC; tolerance 1e-7; relTol 0.01; }",
              "  p_rgh { solver PCG; preconditioner DIC; tolerance 1e-7; relTol 0.01; }")
s.write_text(t)

cd_ = c/"system/controlDict"; t = cd_.read_text()
t = t.replace("purgeWrite      3;", "purgeWrite      0;")
t = re.sub(r"writeInterval [0-9.]+;", "writeInterval 0.5;", t, count=1)
cd_.write_text(t)

# receipts, so a wrong case is caught here and not three hours into a solve
dt = re.sub(r"//.*", "", d.read_text())
assert dt.count("{") == dt.count("}"), "dynamicMeshDict braces unbalanced"
assert (c/"0.orig/pointDisplacement").exists(), "pointDisplacement missing"
assert u.read_text().count("waveVelocity") == 2, "wave U BCs not applied"
assert a.read_text().count("waveAlpha") == 1, "wave alpha BC not applied"
assert "solver PCG" in s.read_text(), "pressure solver not switched off GAMG"
fs = (c/"system/snappyHexMeshDict").read_text()
zmax = float(re.search(r"freeSurface.*?max \([-0-9.]+ [-0-9.]+ ([-0-9.]+)\)", fs, re.S).group(1))
assert zmax >= 1.2*0.5*H - 1e-6, f"refinement band {zmax} m too small for a {H} m sea"
print(f"OK: refined band +-{zmax:.2f} m, braces balanced, wave BCs + PCG in place")
PYEOF
