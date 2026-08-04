# NavalAI — project guide for Claude Code

Autonomous naval-architecture validation AI: mission in natural language →
grammar-constrained hull generation → slider surface with live physics →
tiered validation ladder (L0 algebraic → L1 Michell/hydrostatics → L2
Capytaine BEM → L3 OpenFOAM RANS → R ISO rules) → manufacturing export.
Canonical docs: `NavalArchAI-BuildPlan.md` (research-grounded plan),
`ALIGNMENT.md` (audit vs the original agentic-PLM plan), `README.md`
(gate-status table), `MACBOOK.md` (Mac simulation-node runbook).

## Machine roles

- **fortress001 (Linux)**: development, full test suite, gate ladder.
- **Mac (M5, 24 GB)**: THE SIMULATION NODE — OpenFOAM runs (Gate 2M),
  diffusion/LoRA training. If you are running on macOS, this is you.
- Coordinate via git (github.com/hookprobe/naval-ai, branch master).
  Pull before working; push results. Don't assume the other machine's
  uncommitted state.

## Non-negotiable honesty rules (enforced by tests)

1. Every quantity carries `{value, tier, sigma}` — no bare numbers.
2. Kept designs re-validate up the ladder; surrogates refuse OOD queries.
3. LLMs translate missions and explain; they have NO code path to geometry.
4. Retrained surrogates that degrade the frozen benchmark never deploy.
5. Rules tier output is an ASSESSMENT AID, not certification.
6. Never soften a failing gate threshold to make it pass — a failing gate is
   information. Record measured findings (see ALIGNMENT.md scorecard).

## Working on the Mac (OpenFOAM)

- OpenFOAM v2606 native via openfoam-app. One-shot commands WITHOUT an
  interactive session: `openfoam <command args>` (the launcher execs its
  args) or `openfoam bash -c '...'`. Interactive: bare `openfoam` (bash
  inside, so `#` comments are safe there; in zsh outside they are NOT).
- Campaign flow:
  `python scripts/make_case.py --out runs/<name> [--triplet|--stl X --lwl L] --speed U --np 10`
  → `openfoam navalai/cfd/run-case.sh runs/<name>[/grid] 10`
  → `python scripts/post_gci.py runs/<name>`
  → `scripts/clean-runs.sh` (trim keeps forces+logs; --purge deletes).
- Python env: `source ~/.venvs/naval/bin/activate` (numpy scipy pymoo
  capytaine mujoco cadquery pytest).

## Hard-won CFD gotchas (do not re-learn these)

- Hull STL must be a CLOSED manifold (deck + transom capped);
  `stl_watertight_report` gates it. Open shells flood the interior.
- alpha.water inlet must be height-stratified (`exprFixedValue`,
  z<0 → 1); `inletOutlet $internalField` drains the tank.
- Waterline MUST lie on a background-mesh cell FACE: nz multiple of 3
  (domain z in [-1.5L, 0.75L]). Misalignment doubled medium-grid drag.
- Watch `Phase-1 volume fraction` in log.interFoam: it must stay constant.
- post_gci drift column > 5% ⇒ not settled ⇒ extend --end-time, don't trust.
- v2606 requires the full addLayersControls set (maxFaceThicknessRatio etc.).

## Current campaign state (2026-08-04)

- Full pipeline proven end-to-end on the Mac (mesh+layers+solve+forces+GCI).
- Own-hull GCI triplet: coarse/fine done; MEDIUM re-run pending after the
  waterline-alignment fix. Then record baselines.
- Next milestone: **Gate 2M** — KCS calibration (IGES from t2015.nmri.go.jp,
  model scale 1:31.6, LWL 7.2786 m, Fn 0.26 → 2.196 m/s) via
  `scripts/iges2stl.py` + `make_case.py --stl`. Success = fine-grid Ct inside
  Tokyo-2015 scatter with GCI ≲ 2.5%.
- Then: record L3 results in provenance (tier 'L3') and wire the co-kriging
  L1→L3 correction; parallel tracks: diffusion (PyTorch-MPS), LoRA (mlx-lm).

## Verification

- `python -m pytest tests/ -q` (expect all green, ~3 min) and
  `python -m navalai.gates` before/after non-trivial changes.
- Tests encode the gates; new physics/fixes get a gate test with the
  measured bar and a comment naming the incident that motivated it.
