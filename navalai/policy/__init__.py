"""Governance kernel — what am I ALLOWED to design? (BuildPlan 3, V3.0)

INCOMPLETE, AND DELIBERATELY NOT REGISTERED AS A GATE. What exists:

  base.py   PolicyValue -- every policy constant carries source + basis
  legal.py  LegalEnvelope -- RCD 2013/53/EU Art. 20 routing, the own-use
            exemption and its 5-year clause, and the EU AI Act Art. 6(1)
            two-limb test
  dna.py    DesignDNA -- owner preference constraints, basis='policy'

What does NOT exist yet, and is the load-bearing half:

  THE COMPILER. Governance must COMPILE to (a) a parameter-space box that
  bounds the search and (b) rows appended to evaluate.CONSTRAINT_NAMES --
  from ONE source, never a second engine beside the first. With it must come
  the ratchet law (policy may only tighten a floor in limits.py; a policy that
  would loosen one is a COMPILE-TIME error) and the structural test that makes
  the whole design honest: DELETE THE CONSTITUTION AND EVERY PHYSICS RESULT
  MUST BE BIT-IDENTICAL.

Until that lands this package is inert -- nothing in the ladder consults it,
and no gate row claims it works. That is on purpose: an unfinished governance
layer that a gate reported GREEN would be worse than no governance layer.

Rules framing, unchanged from the rest of the project: an ASSESSMENT AID that
routes work and cites clauses. Never legal advice, never a compliance claim.
Whether a generative design tool is an AI Act "safety component" is a legal
judgement this project is not qualified to make and does not make.
"""

from .base import PolicyError, PolicyRefusal, PolicyValue, constants
from .dna import DesignDNA, owner
from .legal import (DELIVERY_MODES, DISCLAIMER, DISCREPANCIES, INTENTS,
                    MODULE_A_SELF_CERTIFIED, NOTIFIED_BODY_REQUIRED, OWN_USE,
                    OWN_USE_KIT, PLACED_ON_MARKET, LegalEnvelope, art_20_row)

__all__ = [
    "PolicyValue", "PolicyError", "PolicyRefusal", "constants",
    "DesignDNA", "owner",
    "LegalEnvelope", "art_20_row", "DISCLAIMER", "DISCREPANCIES",
    "DELIVERY_MODES", "OWN_USE_KIT", "MODULE_A_SELF_CERTIFIED",
    "NOTIFIED_BODY_REQUIRED", "INTENTS", "OWN_USE", "PLACED_ON_MARKET",
]
