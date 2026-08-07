"""Governance kernel — what am I ALLOWED to design? (BuildPlan 3, V3.0)

  base.py      PolicyValue -- every policy constant carries source + basis
  legal.py     LegalEnvelope -- RCD 2013/53/EU Art. 20 routing, the own-use
               exemption and its 5-year clause, and the EU AI Act Art. 6(1)
               two-limb test
  dna.py       DesignDNA -- owner preference constraints, basis='policy'
  compiler.py  THE COMPILER -- one source, two outputs, and the ratchet law

GOVERNANCE COMPILES; IT DOES NOT ADJUDICATE (BuildPlan 3 §2.2)
--------------------------------------------------------------
The Architect's proposal was a separate engine acting as a pre-filter. Half of
that was right. The half that was not is the half this codebase has already
paid for: a separate engine means a second place a limit is written down, and
`limits.py`'s docstring is a post-mortem of exactly that (NSGA-II optimising to
its private GM 0.35 while the rules gate held 0.45).

So `compile_policy(Constitution)` emits BOTH outputs from ONE source:

  1. `CompiledPolicy.box(category)` -- a parameter-space box. `LOA <= 12 m` is
     a BOUND the sampler and NSGA-II are constructed inside, not a post-hoc
     rejection.
  2. `CompiledPolicy.rows` -- names APPENDED to `evaluate.CONSTRAINT_NAMES` /
     `Evaluation.g`, so everything already consuming that vector is governed
     for free. Pass the compiled policy as `evaluate(..., policy=compiled)`.

And the ratchet law, generalised from `translate.py` (where an LLM proposing a
weaker design category is overruled by `min()`, because 'A' < 'B' < 'C' < 'D'
orders severest first):

    Policy may only ratchet a gate TIGHTER. A policy that would loosen any
    floor in `limits.py` is a policy ERROR, rejected AT COMPILE TIME with the
    offending pair named -- not a runtime override, not a warning, not a note.

THE STRUCTURAL TEST: DELETE THE CONSTITUTION AND EVERY PHYSICS RESULT IS
BIT-IDENTICAL. That is a property of the code, not a promise about it -- policy
rows are APPEND-ONLY (`evaluate.constraint_vector` refuses a policy row that
collides with a ladder row), the compiler reads `limits.py` live and restates
no number from it, and `evaluate` imports nothing from this package. Deleting
`navalai/policy/` leaves the ladder importable and every number unchanged.
`tests/test_policy.py` proves it on real hulls to the last bit.

Rules framing, unchanged from the rest of the project: an ASSESSMENT AID that
routes work and cites clauses. Never legal advice, never a compliance claim.
Whether a generative design tool is an AI Act "safety component" is a legal
judgement this project is not qualified to make and does not make.
"""

from .base import PolicyError, PolicyRefusal, PolicyValue, constants
from .compiler import (CEILING, FLOOR, KIT_LINE_V3_CONSTITUTION, RATCHETS,
                       ROW_DNA, ROW_ENERGY, ROW_FLOORS, ROW_LEGAL, ROW_NAMES,
                       BoxEdit, CompiledPolicy, Constitution, ParameterBox,
                       Ratchet, RatchetFinding, compile_policy,
                       reference_policy)
from .dna import KIT_LINE_V3, DesignDNA, owner
from .legal import (DELIVERY_MODES, DISCLAIMER, DISCREPANCIES, INTENTS,
                    MODULE_A_SELF_CERTIFIED, NOTIFIED_BODY_REQUIRED, OWN_USE,
                    OWN_USE_KIT, PLACED_ON_MARKET, LegalEnvelope, art_20_row)

__all__ = [
    "PolicyValue", "PolicyError", "PolicyRefusal", "constants",
    "DesignDNA", "owner", "KIT_LINE_V3",
    "LegalEnvelope", "art_20_row", "DISCLAIMER", "DISCREPANCIES",
    "DELIVERY_MODES", "OWN_USE_KIT", "MODULE_A_SELF_CERTIFIED",
    "NOTIFIED_BODY_REQUIRED", "INTENTS", "OWN_USE", "PLACED_ON_MARKET",
    "Constitution", "CompiledPolicy", "compile_policy", "reference_policy",
    "KIT_LINE_V3_CONSTITUTION", "ParameterBox", "BoxEdit", "Ratchet",
    "RatchetFinding", "RATCHETS", "FLOOR", "CEILING",
    "ROW_NAMES", "ROW_LEGAL", "ROW_DNA", "ROW_ENERGY", "ROW_FLOORS",
]
