"""L3 CFD tier: OpenFOAM case generation + runner (metal-gated).

This machine has no OpenFOAM install; gate discipline says the tier ships as a
deterministic case-template generator + runner script whose gate is RED until
executed on a machine with OpenFOAM (same pattern as heqk metal gates).
"""

from .case import write_resistance_case  # noqa: F401
