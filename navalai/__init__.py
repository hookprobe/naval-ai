"""navalai — autonomous naval-architecture validation AI.

Phased implementation of NavalArchAI-BuildPlan.md:
  L0 algebraic gate  -> grammar.py
  geometry kernel    -> geometry.py
  L1 physics         -> hydrostatics.py, resistance.py, energy.py
  L2 BEM seakeeping  -> seakeeping.py (Capytaine)
  L3 RANS CFD        -> cfd/ (OpenFOAM case templates, metal-gated)
  surrogate spine    -> surrogate.py
  generative + UI    -> generative.py, ui/
  mission front end  -> mission.py
  rules gate         -> rules/ (ISO 12217 / ISO 12215-5 subsets, assessment aid only)
  provenance         -> db.py
  flywheel           -> flywheel.py, gates.py
"""

__version__ = "0.1.0"
