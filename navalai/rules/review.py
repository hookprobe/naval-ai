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

AND IT IS NOT THE QUESTION GATE 6 ASKS (gap D9). Gate 6R's scope is THRESHOLD
parity: does the number in our source equal the number in the standard text.
BuildPlan Gate 6's bar is VERDICT parity — the same verdict as a qualified
reviewer on at least three reference designs, hand-calculated. Zero reference
designs and zero hand calculations exist. A green 6R is therefore not evidence
for Gate 6, and the reviewer of record is the project owner reviewing his own
code, with no qualification recorded. Both facts are in `docs/GAP-REGISTER.md`
so a future reader does not have to re-derive them from this file.
"""

from __future__ import annotations

import re

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


# An edition string has to name a DATED edition, because that is the only part
# of it a later auditor can go and check. "ISO 12217-1" identifies a standard;
# "ISO 12217-1:2022" identifies the text somebody actually held.
_EDITION_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_PLACEHOLDER = ("not recorded", "tbd", "todo", "unknown", "?")


def edition_defects(record: dict | None = None) -> list[str]:
    """Every reason the record cannot name WHICH document was reviewed.

    Returned as words rather than a bool so the gate ledger and any operator
    can see what is missing without reading this file.
    """
    rec = REVIEW if record is None else record
    out: list[str] = []
    editions = rec.get("editions") or {}
    if not editions:
        return ["no editions recorded at all"]
    for standard, edition in sorted(editions.items()):
        text = str(edition or "").strip()
        if not text:
            out.append(f"{standard}: edition is empty")
        elif any(p in text.lower() for p in _PLACEHOLDER):
            out.append(f"{standard}: edition is a placeholder ({text!r})")
        elif not _EDITION_YEAR.search(text):
            out.append(f"{standard}: edition names no year ({text!r}) — an "
                       f"undated edition cannot be re-checked")
    return out


def is_complete(record: dict | None = None) -> bool:
    """True when the record is attributable — the gate's real precondition.

    A confirmation with no reviewer and no edition cannot be audited, so it
    does not count. This is what stops Gate 6R going green because someone
    edited a set literal.

    THE EDITIONS CLAUSE WAS MISSING, AND THE MODULE SAID SO ITSELF (gap D8,
    audit 2026-08-05). The docstring above `REVIEW` reads "a confirmation that
    cannot say WHO checked WHICH edition is not a review, it is a rumour" —
    and then this function checked `reviewer` and `confirmed` and NOT
    `editions`, which both read "edition not recorded — set this". Gate 6R was
    GREEN on a record that admits in its own field values that it cannot name
    the document it checked.

    Adding the clause FLIPS GATE 6R RED. That is honesty rule 6 working as
    designed, not a regression: the red is recorded in `data/gate-ledger.json`
    with an owner and a review-by date, and it clears the moment a reviewer
    writes the two dated editions in.
    """
    rec = REVIEW if record is None else record
    return (bool(rec.get("reviewer")) and bool(rec.get("confirmed"))
            and not edition_defects(rec))
