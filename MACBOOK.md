# MacBook Pro (M5, ~24 GB) — simulation-node runbook

Purpose of this machine in the project: **unblock Gate 2M** (OpenFOAM
KCS/JBC calibration — the only gap that needs compute we don't have) and run
the two planned upgrades (guided diffusion, LoRA translator). Everything else
already runs green on fortress001.

## 1 · Get the repo onto the Mac

```bash
git clone git@github.com:hookprobe/naval-ai.git && cd naval-ai
```

(Offline fallback: `~/naval-ai-transfer.bundle` on fortress001 —
`git clone naval-ai-transfer.bundle naval-ai`.) Push Gate-2M results back on
a branch; fortress001 pulls them into the provenance DB.

## 2 · Base toolchain (arm64-native, no Rosetta needed)

```bash
xcode-select --install
brew install python@3.12 git
python3.12 -m venv ~/.venvs/naval && source ~/.venvs/naval/bin/activate
pip install numpy scipy pytest pymoo capytaine mujoco cadquery
python -m pytest tests/ -q          # expect 93 passed (~3 min)
python -m navalai.gates             # expect 14 GREEN
```

All of these publish macOS arm64 wheels (capytaine, mujoco, pymoo: PyPI;
CadQuery via the cadquery-ocp arm64 wheels). If `cadquery` pip resolution
fails on a brand-new Python, fall back to `pip install cadquery-ocp-novtk
cadquery` or conda-forge.

## 3 · OpenFOAM (the reason this machine exists)

Native Apple Silicon build — gerlero/openfoam-app (OpenFOAM v2606-era,
bundles OpenMPI, installs via Homebrew):

```bash
brew install --no-quarantine gerlero/openfoam/openfoam       # native .app
openfoam                            # drops you into an OpenFOAM shell
which interFoam blockMesh snappyHexMesh mpirun               # all present
```

Docker fallback (if the app route misbehaves): `gerlero/openfoam-docker-arm`
or `docker run -it opencfd/openfoam-default` (arm64 images exist).

## 4 · The Gate 2M campaign (run in this order)

1. **Benchmark geometry**: download KCS (and optionally JBC) IGES + tank data
   from the Tokyo 2015 workshop site (t2015.nmri.go.jp). Model scale
   (KCS: 1:31.6, L≈7.28 m) — matches the published validation practice.
2. **Case generation** (repo side): `navalai.cfd.case.write_resistance_case`
   emits the case skeleton; point the STL/IGES at the benchmark hull instead
   of a grammar hull for calibration runs.
3. **Run**: `navalai/cfd/run-case.sh <case> 10` (10 = performance cores;
   leave efficiency cores for the OS).
4. **Three-grid GCI**: run coarse/medium/fine at refinement r = sqrt(2)
   (≈0.7 M / 2 M / 5.6 M cells). Post-process each with
   `navalai.cfd.post.mean_resistance` + `navalai.cfd.post.gci`.
5. **Acceptance (Gate 2M)**: resistance/sinkage/trim inside the Tokyo-2015
   scatter band with reported per-case GCI ≲ 2.5 % on the fine grid; write
   the numbers into `data/baselines.json` + provenance DB.

**Memory sizing (24 GB unified):** interFoam + snappy needs roughly
1.5–2 GB per million cells peak; keep the fine grid ≤ 8–10 M cells and you
have headroom. The 5.6 M fine grid fits comfortably.

**Wall-clock expectation:** coarse ~1 h, medium ~3–5 h, fine ~8–14 h on
~10 performance cores (unsteady interFoam to settled forces, tail-averaged).
Plan a weekend for the full triplet × 2 speeds; it is embarrassingly
restartable — each case is independent.

## 5 · Upgrade tracks the Mac also unlocks

- **Guided tabular diffusion** (replaces the GMM behind the SAME
  `HullFamilyModel` interface): `pip install torch` (MPS backend is
  automatic on Apple Silicon). A 45-param tabular DDPM at ShipGen scale
  trains in minutes-to-an-hour on the M5 GPU.
- **LoRA mission translator** (drops in ABOVE `translate.py`'s sanitizing
  seam — the seam stays, per Gate 5): `pip install mlx-lm`, LoRA-tune a
  1–3 B instruct model on mission-brief→MissionSpec-JSON pairs. 24 GB
  unified memory is ample for 3 B LoRA. The published precedent used one
  consumer GPU; this is the Mac equivalent.
- **Capytaine at convergence**: 10 k+ panel sweeps (the NREL-flagged bar)
  are minutes instead of the coarse meshes we gate on today.

## 6 · What stays where

| Work | Machine |
|---|---|
| L0/L1 ladder, slider UI, agents, rules, flywheel, tests | either (both green) |
| OpenFOAM Gate 2M campaign | **Mac only** |
| Diffusion + LoRA training | Mac (MPS/MLX) |
| ISO licensed-text parity (Gate 6R) | neither — a qualified reviewer, not compute |

Results flow back by re-bundling the repo (provenance DB + baselines.json
travel with it, `data/*.sqlite3` is gitignored — copy it explicitly or
re-harvest).
