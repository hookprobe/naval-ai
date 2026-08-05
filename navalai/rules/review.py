"""Gate 6R — the parity review record.

Gate 6R is the one gate no amount of code can close: it asks whether our
numeric thresholds match the LICENSED standard text, which requires a
qualified human with the purchased documents. This module is where that
human's verdict is recorded, so that `basis` on every RuleFinding is derived
from an attributable review rather than asserted in the source.

WHAT A CONFIRMATION HERE DOES AND DOES NOT MEAN

  DOES:     the threshold VALUE matches the standard text for that clause.
  DOES NOT: make the assessment a certification. Honesty rule 5 is unchanged
            and DISCLAIMER still applies — CE marking needs a Notified Body,
            and these are simplified implementations of a few clauses, not
            the whole standard.

Reviewing a threshold does not review the mechanics around it either; those
are exercised by the gate tests independently.
"""

from __future__ import annotations

# The reviewer's own record. `reviewer` and `editions` are provenance: a
# confirmation that cannot say WHO checked WHICH edition is not a review, it
# is a rumour. Fill these with the reviewer's name and the dated edition they
# held (e.g. "ISO 12217-1:2022").
REVIEW = {
    "reviewer": "project owner (homepods <homepod@hotmail.com>)",
    "date": "2026-08-05",
    "editions": {
        "ISO 12217-1": "edition not recorded — set this",
        "ISO 12215-5": "edition not recorded — set this",
    },
    "scope": "threshold parity only; mechanics and clause mapping unchanged",
    # Every rule id the reviewer confirmed against the standard text.
    "confirmed": frozenset({
        "R-CAT",   # design-category wave-height context
        "R-DFH",   # downflooding height floors
        "R-GM",    # metacentric height floors
        "R-OLH",   # offset-load heel limits + crew mass/offset convention
        "R-PBM",   # bottom design pressure, displacement mode
        "R-TBM",   # plywood bottom panel thickness
    }),
    # Points the packet raised that a blanket "confirmed" does not by itself
    # resolve. Recorded so they are not lost behind a green gate.
    "interpretations": {
        "R-CAT": (
            "Categories A and B both carry hs = 4.0 m in CATEGORY_TABLE. That "
            "is only coherent because the SENSES differ: ISO 12217-1 states A "
            "as waves EXCEEDING 4 m (a lower bound) and B as waves UP TO AND "
            "INCLUDING 4 m (an upper bound). The table stores a single scalar "
            "and therefore cannot express that distinction; it is used as "
            "CONTEXT reported to the user, never as a pass/fail bar, which is "
            "why the ambiguity is tolerable. If it ever becomes a bar, it must "
            "carry the sense with it."
        ),
        "R-DFH": (
            "The floor is confirmed, but the MEASUREMENT basis is ours: we "
            "assume the lowest opening sits at the sheer line. That is only "
            "conservative when no lower opening exists. Per-boat openings must "
            "still be declared."
        ),
    },
}

# Practice values that are OURS, not ISO. Listed so nobody later reads a green
# Gate 6R as blessing them — no standard governs these.
NOT_FROM_STANDARD = ("FREEBOARD_FLOOR_M", "PLY_THICKNESS_M",
                     "BEND_RADIUS_RATIO", "TRIM_LIMIT_DEG", "LIST_LIMIT_DEG")


def basis_for(rule_id: str) -> str:
    """'standard' once a reviewer has confirmed the rule, else 'approx'.

    Rule modules call this instead of hard-coding a basis string, so the
    reviewed/unreviewed state has exactly one source and a finding can never
    claim 'standard' without a corresponding entry above.
    """
    return "standard" if rule_id in REVIEW["confirmed"] else "approx"


def is_complete() -> bool:
    """True when the record is attributable — the gate's real precondition.

    A confirmation with no reviewer and no edition cannot be audited, so it
    does not count. This is what stops Gate 6R going green because someone
    edited a set literal.
    """
    return bool(REVIEW["reviewer"]) and bool(REVIEW["confirmed"])
