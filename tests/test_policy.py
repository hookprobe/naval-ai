"""Gate V3.0 — the governance kernel, and the four things it must prove.

BuildPlan 3 §3, verbatim:

    (a) every policy constant carries `source` + `basis`, no bare numbers;
    (b) a policy that would loosen **any** `limits.py` floor is **rejected at
        compile time** with the offending pair named — proven by a test that
        tries it;
    (c) the reference SKU resolves to a delivery mode with the RCD article
        cited, and a 13 m variant flips to "notified body required" **and**
        flags the AI Act Art. 6(1)(b) consequence;
    (d) **the structural test: with the constitution removed, every physics
        result in the regression suite is bit-identical.**

(d) is the one that decides whether the design is honest, so it is written to
be FALSIFIABLE rather than merely true: `test_the_structural_test_can_actually
_fail` runs the same comparator against a deliberately sabotaged policy and
asserts it catches it. A structural test that cannot fail is a decoration, and
this repository has shipped one of those before — `gate2m.py`'s private GCI
printed `VERDICT: PASS` on a DIVERGING triplet because `gci <= 5.0` is true of
-27.027%.
"""

from __future__ import annotations

import dataclasses
import inspect
import pkgutil
import struct
from pathlib import Path

import numpy as np
import pytest

from navalai import evaluate as ev_mod
from navalai import grammar, limits, policy
from navalai.evaluate import CONSTRAINT_NAMES, ConstraintOrderError, evaluate
from navalai.mission import MissionSpec
from navalai.policy import (CEILING, FLOOR, RATCHETS, Constitution, DesignDNA,
                            LegalEnvelope, PolicyError, PolicyRefusal,
                            PolicyValue, compile_policy, constants, owner,
                            reference_policy)
from navalai.policy import base as policy_base
from navalai.policy import compiler as policy_compiler
from navalai.policy import dna as policy_dna
from navalai.policy import legal as policy_legal

MISSION = MissionSpec()          # 6 t, 5 kn, category C — the reference mission


# ---------------------------------------------------------------------------
# hulls: a small, deterministic regression set, reused by several tests
# ---------------------------------------------------------------------------

def _hulls(n: int = 40, seed: int = 0) -> list[np.ndarray]:
    """`n` L0-feasible genomes that produce a full L1 evaluation.

    Drawn from the UNBOUNDED grammar box, not from the policy box, on purpose:
    the structural test has to include hulls the constitution REJECTS, or it
    would only ever compare designs on which policy is inert. Roughly two
    thirds of these breach `policy_legal` (measured — see `compiler` docstring).
    """
    rng = np.random.default_rng(seed)
    out: list[np.ndarray] = []
    while len(out) < n:
        x = rng.uniform(grammar.LOW, grammar.HIGH)
        if not grammar.check(x).ok:
            continue
        if evaluate(x, MISSION).hydro is None:
            continue
        out.append(x)
    return out


# ===========================================================================
# (a) EVERY POLICY CONSTANT CARRIES source + basis
# ===========================================================================

_POLICY_MODULES = (policy_base, policy_legal, policy_dna, policy_compiler)


def test_every_policy_module_is_covered_by_this_gate():
    """No module of the package escapes (a) by not being listed here.

    The failure mode this guards is the one `base.constants` warns about: a
    check that passes by vacuous truth. A new `policy/*.py` added tomorrow with
    a bare number in it must break this test on the day it lands, not on the
    day someone remembers to add it to the tuple above.
    """
    on_disk = {m.name for m in pkgutil.iter_modules([str(
        Path(policy.__file__).parent)])}
    listed = {m.__name__.rsplit(".", 1)[1] for m in _POLICY_MODULES}
    assert on_disk == listed, (
        f"navalai/policy has modules {sorted(on_disk - listed)} that Gate "
        f"V3.0(a) does not walk. Add them to _POLICY_MODULES.")


@pytest.mark.parametrize("mod", _POLICY_MODULES,
                         ids=[m.__name__ for m in _POLICY_MODULES])
def test_every_policy_constant_carries_source_and_basis(mod):
    found = constants(mod)
    for path, pv in found.items():
        assert isinstance(pv, PolicyValue)
        assert pv.basis in policy_base.BASES, f"{path} basis {pv.basis!r}"
        assert len(pv.source.strip()) >= policy_base.MIN_SOURCE_CHARS, (
            f"{path} is cited in {len(pv.source.strip())} characters; a "
            f"governance constant may not be cited more loosely than a "
            f"freeboard number")
        assert pv.unit is not None


def test_the_walk_is_not_passing_by_vacuous_truth():
    """`constants()` must actually FIND things, or (a) proves nothing.

    `refdata.constants` filters on `isinstance(obj, RefValue)` and returns {}
    for this package — pointing it here would have passed every assertion above
    while checking nothing at all. That is why `base.constants` exists, and
    this is the assertion that keeps it honest.
    """
    assert len(constants(policy_legal)) >= 8
    assert len(constants(policy_dna)) >= 7
    # dna.py's constants are ALL owner preference, and none of them may wear a
    # law's badge — that is the whole reason BASES has four members.
    for path, pv in constants(policy_dna).items():
        assert pv.basis == "policy", f"{path} is a preference wearing {pv.basis!r}"


def test_a_bare_number_in_a_design_dna_is_refused():
    with pytest.raises(PolicyError, match="bare float"):
        DesignDNA("bare", max_draft_m=1.10)       # a number with no provenance
    with pytest.raises(PolicyError, match="bare float"):
        DesignDNA("bare", floors={"freeboard_floor_m": 0.30})


def test_a_constant_cited_too_loosely_is_refused():
    with pytest.raises(PolicyError, match="names no document"):
        PolicyValue(0.30, "m", "ISO says so", "directive")
    with pytest.raises(PolicyError, match="not in"):
        PolicyValue(0.30, "m", "a source long enough to pass the length bar",
                    "vibes")


def test_the_policy_vocabulary_is_disjoint_from_refdata():
    """`base.py` claims this, so it is asserted rather than believed.

    Widening `refdata.BASES` with 'policy' would let an owner preference wear
    the same badge as a transcribed standard number, and a reader of a value
    would lose the ability to tell "ISO says 0.45" from "we prefer 0.45".
    """
    from navalai.refdata import BASES as REF_BASES
    assert not (set(policy_base.BASES) & set(REF_BASES))


def test_the_compiler_restates_no_limits_number():
    """(a) has a second half: no policy MODULE may hold a copy of a bar.

    Every ratchet reads `navalai.limits` through a callable, so this asserts
    what the design claims — that `compiler.py` contains no literal equal to a
    limits value it ratchets. The recurring defect in this codebase is A NUMBER
    DECLARED TWICE; the ratchet registry is the obvious place for the next one.
    """
    src = inspect.getsource(policy_compiler)
    body = "\n".join(line for line in src.splitlines()
                     if not line.lstrip().startswith("#"))
    for key, r in RATCHETS.items():
        live = r.live("C")
        # The value would have to appear as a literal to be a second copy.
        assert f"= {live}" not in body and f"({live})" not in body, (
            f"compiler.py appears to restate {key}'s live value {live}; "
            f"limits.py owns it and the ratchet must read it through "
            f"`Ratchet.live`")


# ===========================================================================
# (b) A POLICY THAT WOULD LOOSEN A limits.py FLOOR IS A COMPILE-TIME ERROR
# ===========================================================================

def _dna_with(**floors) -> DesignDNA:
    return DesignDNA("test constitution", floors={
        k: owner(v, RATCHETS[k].unit,
                 f"a test tightening of {RATCHETS[k].what}")
        for k, v in floors.items()})


def _constitution(dna: DesignDNA, cats=("C", "D")) -> Constitution:
    return Constitution("test", LegalEnvelope(allowed_categories=cats), dna)


def test_a_loosened_floor_is_rejected_at_compile_time_naming_the_pair():
    """Gate V3.0(b), the headline case: a GM floor below the platform's own.

    `limits.gm_floor('C')` is 0.45 m. A constitution declaring 0.30 m is not a
    ratchet, it is the `optimize.py` 0.35-vs-0.45 drift written down as policy
    — which is worse, because it would look authorised.
    """
    with pytest.raises(PolicyError) as e:
        compile_policy(_constitution(_dna_with(gm_floor_m=0.30)))
    msg = str(e.value)
    assert "gm_floor_m" in msg                       # the policy side of the pair
    assert "limits.gm_floor" in msg                  # the limits side of the pair
    assert "0.3" in msg and "0.45" in msg            # BOTH numbers
    assert "COMPILE TIME" in msg
    assert RATCHETS["gm_floor_m"].direction == FLOOR


def test_the_offending_pair_names_the_design_category_it_failed_on():
    """The trap: 0.40 m TIGHTENS category D (0.35) and LOOSENS category C (0.45).

    A compiler that checked one category would accept this and the constitution
    would silently authorise a 0.40 m GM on a category C boat. The check runs
    over every category the legal envelope admits and the error says which one.
    """
    with pytest.raises(PolicyError) as e:
        compile_policy(_constitution(_dna_with(gm_floor_m=0.40)))
    assert "design category C" in str(e.value)
    # ... and it is genuinely a tightening for a D-only constitution:
    compiled = compile_policy(_constitution(_dna_with(gm_floor_m=0.40), ("D",)))
    assert [f.key for f in compiled.ratchets] == ["gm_floor_m"]
    assert compiled.ratchets[0].limits_value == limits.gm_floor("D")


def test_a_ceiling_loosened_upward_is_rejected():
    """Direction matters: TRIM_LIMIT_DEG is a ceiling, so BIGGER is looser."""
    with pytest.raises(PolicyError, match="TRIM_LIMIT_DEG"):
        compile_policy(_constitution(_dna_with(trim_limit_deg=3.0)))
    compiled = compile_policy(_constitution(_dna_with(trim_limit_deg=1.5)))
    assert compiled.ratchets[0].direction == CEILING


def test_restating_the_limits_value_is_refused_as_a_second_copy():
    """Equal is not a ratchet. It is the defect this project keeps producing.

    A policy floor identical to `limits.py`'s tightens nothing and buys
    nothing, and it drifts the moment `limits.py` moves — which is exactly how
    the GM floor came to be 0.35 in three modules and 0.45 in the rules gate.
    """
    with pytest.raises(PolicyError, match="SECOND COPY"):
        compile_policy(_constitution(
            _dna_with(freeboard_floor_m=limits.FREEBOARD_FLOOR_M)))


def test_a_floor_on_a_bar_the_platform_does_not_own_is_refused():
    dna = DesignDNA("invented bar", floors={"hull_colour": owner(
        1.0, "-", "a bar that does not exist anywhere in limits.py")})
    with pytest.raises(PolicyError, match="names no bar this platform owns"):
        compile_policy(_constitution(dna))


def test_a_non_finite_policy_floor_is_refused():
    with pytest.raises(PolicyError, match="non-finite"):
        compile_policy(_constitution(_dna_with(gm_floor_m=float("nan"))))


def test_the_ratchet_reads_limits_py_live_and_holds_no_copy(monkeypatch):
    """Move `limits.py` and the SAME constitution must stop compiling.

    This is the test that would catch a cached or transcribed bar. A freeboard
    floor of 0.30 m is a legitimate tightening of the platform's 0.25 m; raise
    the platform's own floor above it and the same policy is now a loosening,
    and must be refused without a line of the policy changing.
    """
    dna = _dna_with(freeboard_floor_m=0.30)
    compile_policy(_constitution(dna))                    # compiles today
    monkeypatch.setattr(limits, "FREEBOARD_FLOOR_M", 0.35)
    with pytest.raises(PolicyError, match="LOOSEN"):
        compile_policy(_constitution(dna))


def test_a_tightened_floor_compiles_into_a_row_and_binds_a_real_hull():
    """(b)'s positive half: a legal tightening must actually reach the ladder.

    Rejecting the loosening is only half a ratchet. The tightening has to end
    up in `Evaluation.g` as its own row, or governance is a linter.
    """
    compiled = compile_policy(_constitution(_dna_with(gm_floor_m=1e6)))
    assert policy.ROW_FLOORS in compiled.rows
    x = _hulls(1)[0]
    ev = evaluate(x, MISSION, policy=compiled)
    assert ev.g[policy.ROW_FLOORS] > 0.0
    assert not ev.ok
    assert any("gm_floor_m" in v for v in ev.violations)


def test_a_bar_with_no_measured_counterpart_still_ratchets_but_emits_no_row():
    """`bend_radius_ratio` has no `Evaluation` field, and that is stated.

    A row this module could only fill by recomputing geometry would be the
    second engine §2.2 forbids, so the bar ratchet-checks and contributes
    nothing to the vector. The alternative — emitting a row that reads the same
    number forever — is the `list` -2.000 defect.
    """
    with pytest.raises(PolicyError, match="LOOSEN"):
        compile_policy(_constitution(_dna_with(bend_radius_ratio=40.0)))
    compiled = compile_policy(_constitution(_dna_with(bend_radius_ratio=120.0)))
    assert compiled.ratchets and policy.ROW_FLOORS not in compiled.rows


# ===========================================================================
# (c) THE REFERENCE SKU ROUTES, AND A 13 m VARIANT FLIPS
# ===========================================================================

def test_the_reference_sku_resolves_to_a_mode_with_the_rcd_article_cited():
    r = reference_policy().delivery_route(11.0, "C")
    assert r.mode == policy.MODULE_A_SELF_CERTIFIED
    assert r.article == "RCD Art. 20(1)(b)(i)"
    assert "Module A" in r.rationale
    # The category C sub-12 m cell is CONDITIONAL, and the condition is carried
    # rather than assumed: Annex I Part A points 3.2 and 3.3.
    assert any("3.2 and 3.3" in c for c in r.conditions)
    assert not r.needs_notified_body
    assert "NOT legal advice" in r.disclaimer


def test_a_13_m_variant_flips_and_flags_the_ai_act_consequence():
    """The coupling no physics gate can see, in one design change.

    Same hull family, same category, +2 m of length: the craft acquires a
    notified body AND satisfies AI Act Art. 6(1)(b) at the same moment.
    """
    cp = reference_policy()
    r11, r13 = cp.delivery_route(11.0, "C"), cp.delivery_route(13.0, "C")

    assert r11.mode == policy.MODULE_A_SELF_CERTIFIED
    assert r13.mode == policy.NOTIFIED_BODY_REQUIRED
    assert r13.article == "RCD Art. 20(1)(b)(ii)"

    assert r11.ai_act.third_party_assessment_required is False
    assert r13.ai_act.third_party_assessment_required is True
    assert "Art. 6(1)(b)" in r13.ai_act.article
    assert r13.ai_act.annex_i_item == 3          # RCD is Annex I Section A item 3
    assert any("Art. 6(1)" in c for c in r13.conditions)


def test_the_high_risk_question_is_refused_not_answered():
    """`high_risk` is ALWAYS None, on every route, in both directions.

    Limb (a) — whether a generative design tool is 'a safety component of' the
    craft — is a legal judgement this platform is not qualified to make. A
    boolean here would be an answer to a question we have refused to answer,
    and honesty rule 5 says the rules tier is an assessment aid.
    """
    cp = reference_policy()
    for lh, cat in ((11.0, "C"), (13.0, "C"), (20.0, "D"), (5.0, "D")):
        r = cp.delivery_route(lh, cat)
        assert r.ai_act.high_risk is None
        assert "OPEN, AND WE DO NOT ANSWER IT" in r.ai_act.safety_component_question


def test_category_d_crosses_12_m_untouched():
    """The recorded disagreement with BuildPlan3 §0, asserted.

    §0 says "anything 12-24 m requires a notified body". Art. 20(1)(c) gives
    category D the whole 2.5-24 m band on Module A. Over-routing is still
    routing wrongly, so the Directive wins and `legal.DISCREPANCIES` records it.
    """
    cp = reference_policy()
    assert cp.delivery_route(20.0, "D").mode == policy.MODULE_A_SELF_CERTIFIED
    assert cp.delivery_route(20.0, "D").article == "RCD Art. 20(1)(c)"
    assert any("Art. 20(1)(c)" in d for d in policy.DISCREPANCIES)


def test_a_craft_outside_the_rcd_is_refused_not_routed():
    with pytest.raises(PolicyRefusal, match="Art. 3\\(2\\)"):
        reference_policy().delivery_route(30.0, "C")


def test_a_refusal_reaches_the_ladder_as_a_refusal_not_as_an_exception():
    """A routing refusal must not abort a population, and must not become a mode.

    An out-of-scope craft is one the RCD does not define, so no delivery mode
    is honest for it. Raising inside `evaluate` would kill an NSGA-II
    generation over a design `policy_legal` has already scored; returning
    `module_a_self_certified` would be picking a mode because a mode had to be
    returned. It reads REFUSED, with the clause.
    """
    # lh_over_lwl > 1 pushes a 20 m grammar hull past the RCD's 24 m ceiling.
    dna = DesignDNA("long overhangs", lh_over_lwl=owner(
        1.3, "-", "a deliberately large stem/transom overhang allowance, to "
                  "push a grammar-legal hull out of the RCD's own scope"))
    cp = compile_policy(Constitution("out of scope", LegalEnvelope(), dna))
    x = _hulls(1)[0].copy()
    x[grammar.NAMES.index("LWL")] = 20.0
    ev = evaluate(x, MISSION, policy=cp)
    assert ev.policy["route"]["mode"] == "REFUSED"
    assert "Art. 3(2)" in ev.policy["route"]["refusal"]
    assert ev.g[policy.ROW_LEGAL] > 0.0
    assert not ev.ok


def test_the_route_reaches_an_evaluated_design():
    """(c) end to end: the route rides on the Evaluation, not just on the API."""
    cp = reference_policy()
    x = _hulls(1)[0].copy()
    x[grammar.NAMES.index("LWL")] = 11.0
    ev = evaluate(x, MISSION, policy=cp)
    assert ev.policy["route"]["mode"] == policy.MODULE_A_SELF_CERTIFIED
    x[grammar.NAMES.index("LWL")] = 13.0
    ev = evaluate(x, MISSION, policy=cp)
    assert ev.policy["route"]["mode"] == policy.NOTIFIED_BODY_REQUIRED
    assert ev.policy["route"]["ai_act"]["third_party_assessment_required"]
    assert ev.g[policy.ROW_LEGAL] > 0.0        # and it is a CONSTRAINT, not a note


def test_hull_length_is_modelled_from_the_declared_lwl_not_the_floated_one():
    """Reading the floated waterline would understate LH by ~5% at the break.

    MEASURED and recorded in CLAUDE.md: a declared 8.00 m floats at 7.60 m.
    LH >= LWL >= lwl_eff, so the declared value is both the larger and the
    honest one, and `dna.lh_over_lwl` is where the remaining optimism is
    declared rather than assumed.
    """
    cp = reference_policy()
    x = _hulls(1)[0].copy()
    x[grammar.NAMES.index("LWL")] = 12.4
    ev = evaluate(x, MISSION, policy=cp)
    assert ev.hydro.lwl_eff < ev.hull_lwl_m         # the two are not the same
    assert ev.policy["route"]["hull_length_m"] == pytest.approx(12.4)
    assert ev.policy["route"]["mode"] == policy.NOTIFIED_BODY_REQUIRED


# ===========================================================================
# (d) THE STRUCTURAL TEST — DELETE THE CONSTITUTION, NOTHING MOVES
# ===========================================================================

_POLICY_OWNED_FIELDS = {"ok", "violations", "g", "g_names", "policy",
                        "eval_ms"}


def _bits(v):
    """A hashable, EXACT representation. Not a rounded one, not `==`.

    `struct.pack('>d')` distinguishes 0.0 from -0.0 and preserves the payload
    of a nan, both of which `==` gets wrong in opposite directions (0.0 == -0.0
    is True; nan == nan is False). "Bit-identical" has to mean the bits.
    """
    if v is None or isinstance(v, (bool, int, str)):
        return (type(v).__name__, v)
    if isinstance(v, float):
        return ("f", struct.pack(">d", v).hex())
    if isinstance(v, np.ndarray):
        return ("a", v.dtype.str, v.shape, v.tobytes().hex())
    if isinstance(v, (list, tuple)):
        return (type(v).__name__, tuple(_bits(i) for i in v))
    if isinstance(v, dict):
        return ("d", tuple((k, _bits(v[k])) for k in sorted(v, key=repr)))
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        return (type(v).__name__,
                tuple((f.name, _bits(getattr(v, f.name)))
                      for f in dataclasses.fields(v)))
    return ("repr", repr(v))


def physics_fingerprint(ev) -> dict:
    """Every physics quantity an `Evaluation` carries, bit for bit.

    Built by WALKING `dataclasses.fields(Evaluation)` rather than by listing
    the fields, so a field added tomorrow is covered on the day it lands. The
    only exclusions are the four fields governance is ALLOWED to touch, plus
    the wall-clock `eval_ms`, and the CONSTRAINT_NAMES half of `g` is put back
    explicitly — those rows are physics margins and they must not move either.
    """
    fp = {f.name: _bits(getattr(ev, f.name))
          for f in dataclasses.fields(ev)
          if f.name not in _POLICY_OWNED_FIELDS}
    for k in CONSTRAINT_NAMES:
        fp[f"g[{k}]"] = _bits(ev.g[k]) if k in ev.g else ("missing",)
    return fp


def assert_bit_identical(plain, governed, label: str = "") -> None:
    a, b = physics_fingerprint(plain), physics_fingerprint(governed)
    diff = [k for k in a if a[k] != b[k]]
    assert not diff, (
        f"{label}: applying a constitution MOVED {diff}. Governance compiles, "
        f"it does not adjudicate — a policy that changes a physics number is a "
        f"second constraint engine and must be undone (BuildPlan 3 §2.2).")


def test_the_constitution_changes_no_physics_number_bit_for_bit():
    """GATE V3.0(d). The whole design is wrong if this fails.

    40 hulls, each evaluated twice — once ungoverned, once under the compiled
    reference constitution — and every field of the `Evaluation` compared
    through `struct.pack`, including the nested `HydroState`, `MassAggregate`,
    `ResistanceResult`, `EnergyReport` and the badge sigmas. About two thirds
    of these hulls BREACH the constitution, so this is not a comparison of
    designs on which policy happens to be inert.
    """
    cp = reference_policy()
    for i, x in enumerate(_hulls(40)):
        assert_bit_identical(evaluate(x, MISSION),
                             evaluate(x, MISSION, policy=cp), f"hull {i}")


def test_a_ratcheted_floor_is_additive_and_leaves_the_ladder_row_alone():
    """The case most likely to have been built wrong.

    The obvious implementation of "policy tightens the GM floor" is to
    substitute the tighter number into `g['gm']` — and then `g['gm']` differs
    between a governed and an ungoverned run, and (d) can only pass by
    exempting the row it is about. Implemented additively, the ladder's row is
    untouched and the tightening arrives as `policy_floors`. The feasible set
    is the same either way (max(a,b) <= 0 iff a <= 0 and b <= 0), so nothing is
    lost by being honest.
    """
    tight = compile_policy(_constitution(_dna_with(
        gm_floor_m=10.0 * limits.gm_floor("C"),
        freeboard_floor_m=10.0 * limits.FREEBOARD_FLOOR_M)))
    for i, x in enumerate(_hulls(12)):
        plain, governed = evaluate(x, MISSION), evaluate(x, MISSION, policy=tight)
        assert_bit_identical(plain, governed, f"ratcheted hull {i}")
        # ... and the ratchet is not merely inert: it bit.
        assert governed.g[policy.ROW_FLOORS] > 0.0
        assert not governed.ok


def test_the_structural_test_can_actually_fail():
    """PROOF THAT (d) IS FALSIFIABLE. Run the comparator against a saboteur.

    A test that cannot fail is a decoration. This builds a policy object with
    the same duck-typed surface as a `CompiledPolicy` whose `rows_for` does
    what a second constraint engine would do — recompute a physics quantity and
    write it back — and asserts that `assert_bit_identical` CATCHES it, naming
    the field.
    """
    real = reference_policy()

    class Saboteur:
        constitution = real.constitution
        rows = ("policy_legal",)

        def rows_for(self, ev, mission):
            ev.gm_m = float(ev.gm_m) * 1.0000000001    # a tenth of a ppb
            return {"policy_legal": -0.01}, {}

        def route_report(self, ev, mission):
            return real.route_report(ev, mission)

    x = _hulls(1)[0]
    with pytest.raises(AssertionError, match="gm_m"):
        assert_bit_identical(evaluate(x, MISSION),
                             evaluate(x, MISSION, policy=Saboteur()),
                             "saboteur")


def test_a_policy_row_may_not_overwrite_a_ladder_row():
    """The append-only rule, enforced in `evaluate.constraint_vector` itself.

    This is what makes (d) a property of the code rather than a promise about
    it: even a policy that TRIED to rewrite `gm` cannot, because the vector
    builder refuses the collision before a number is written.
    """
    real = reference_policy()

    class Overwriter:
        constitution = real.constitution
        rows = ("gm",)

        def rows_for(self, ev, mission):
            return {"gm": -999.0}, {}

        def route_report(self, ev, mission):
            return real.route_report(ev, mission)

    with pytest.raises(ConstraintOrderError, match="collide"):
        evaluate(_hulls(1)[0], MISSION, policy=Overwriter())


def test_the_ladder_imports_nothing_from_the_policy_package():
    """"Delete the constitution" has to mean deleting the FILES.

    If `evaluate.py` imported `navalai.policy`, removing the package would make
    the ladder unimportable and (d) would be untestable in the only sense that
    matters. The dependency runs one way only: a compiled policy is passed IN.
    """
    src = inspect.getsource(ev_mod)
    for line in src.splitlines():
        s = line.strip()
        if s.startswith(("import ", "from ")):
            assert "policy" not in s, f"evaluate.py imports policy: {s!r}"


def test_an_ungoverned_evaluation_is_shaped_exactly_as_before():
    ev = evaluate(_hulls(1)[0], MISSION)
    assert ev.g_names == CONSTRAINT_NAMES
    assert tuple(ev.g) == CONSTRAINT_NAMES
    assert ev.policy == {}


# ===========================================================================
# OUTPUT 1 — THE PARAMETER BOX
# ===========================================================================

def test_the_length_ceiling_is_a_bound_and_not_a_rejection():
    """BuildPlan 3 §2.2: "LOA <= 12 m becomes a bound, not a rejection".

    10,000 draws from the compiled box, and the number of over-length hulls
    that have to be rejected afterwards is ZERO — because none is generated.
    """
    box = reference_policy().box("C")
    i = grammar.NAMES.index("LWL")
    assert box.high[i] == pytest.approx(11.9)
    assert box.high[grammar.NAMES.index("T")] == pytest.approx(1.10)
    X = box.sample(10_000, np.random.default_rng(7))
    assert X[:, i].max() <= 11.9
    assert np.all(X >= box.low) and np.all(X <= box.high)


def test_the_box_only_ever_tightens():
    """A policy that WIDENED the search space would be the ratchet law broken
    on the other output. Every edit must move a bound inward."""
    for cat in ("C", "D"):
        box = reference_policy().box(cat)
        assert np.all(box.low >= grammar.LOW)
        assert np.all(box.high <= grammar.HIGH)
        for e in box.edits:
            assert (e.now > e.was) if e.edge == "low" else (e.now < e.was)
            assert len(e.source) >= policy_base.MIN_SOURCE_CHARS


def test_a_caller_s_own_bounds_are_tightened_never_widened():
    """`optimize.HullProblem` applies the mission's length hint first; the box
    must respect that and only narrow it further."""
    lo, hi = grammar.LOW.copy(), grammar.HIGH.copy()
    i = grammar.NAMES.index("LWL")
    lo[i], hi[i] = 8.0, 9.0
    box = reference_policy().box("C", low=lo, high=hi)
    assert box.low[i] == 8.0 and box.high[i] == 9.0


def test_the_art_20_break_appears_for_category_c_and_not_for_d():
    """The table decides, not a hard-coded list of which categories break.

    Category D has no 12 m break (Art. 20(1)(c)), so the bound must simply not
    be there — encoding one would be `legal.DISCREPANCIES`' error committed in
    the box instead of in the prose.
    """
    cp = reference_policy()
    rcd = policy_legal.MODULE_A_LENGTH_BREAK_M.source
    assert any(e.source == rcd for e in cp.box("C").edits)
    assert not any(e.source == rcd for e in cp.box("D").edits)


def test_the_art_20_bound_is_exclusive_at_the_break():
    """Art. 20(1)(b)(i) reads 'to LESS THAN 12 m', so 12.00 m is already the
    notified-body row and the bound must be strictly below it."""
    env = LegalEnvelope(allowed_categories=("C",))
    # A constitution with no length ceiling of its own, so the legal bound is
    # the only thing holding LWL.
    cp = compile_policy(Constitution("legal only", env, DesignDNA("none")))
    hi = cp.box("C").high[grammar.NAMES.index("LWL")]
    assert hi < 12.0
    assert cp.delivery_route(hi, "C").mode == policy.MODULE_A_SELF_CERTIFIED
    assert cp.delivery_route(12.0, "C").mode == policy.NOTIFIED_BODY_REQUIRED


def test_accepting_a_notified_body_removes_the_legal_length_bound():
    """The one genuine CHOICE in the envelope, and it must be visible."""
    env = LegalEnvelope(allowed_categories=("C",), accept_notified_body=True)
    cp = compile_policy(Constitution("nb ok", env, DesignDNA("none")))
    assert cp.box("C").high[grammar.NAMES.index("LWL")] == grammar.HIGH[
        grammar.NAMES.index("LWL")]


def test_an_empty_box_is_a_compile_time_error():
    """A box that admits nothing is a policy error, not a hard search problem.

    Left to the optimiser, "no feasible design" reads as a difficult mission
    rather than as a constitution that contradicts itself.
    """
    dna = DesignDNA("too small", max_hull_length_m=owner(
        3.0, "m", "a length ceiling below the grammar's own 4 m floor"))
    with pytest.raises(PolicyError, match="EMPTY parameter box"):
        compile_policy(Constitution("empty", LegalEnvelope(), dna))


def test_a_category_the_envelope_does_not_admit_has_no_box():
    with pytest.raises(PolicyRefusal, match="categorical breach"):
        reference_policy().box("A")


# ===========================================================================
# OUTPUT 2 — THE ROWS, AND THE -2.000 RULE
# ===========================================================================

def test_the_rows_are_appended_after_the_ladder_s_own_in_order():
    cp = reference_policy()
    ev = evaluate(_hulls(1)[0], MISSION, policy=cp)
    assert ev.g_names == CONSTRAINT_NAMES + cp.rows
    assert tuple(ev.g) == ev.g_names
    assert cp.constraint_names() == ev.g_names
    assert all(r.startswith("policy_") for r in cp.rows)
    assert not (set(cp.rows) & set(CONSTRAINT_NAMES))


def test_a_row_exists_only_where_the_constitution_takes_a_position():
    """The None doctrine, applied to the constraint vector.

    `DesignDNA` distinguishes None ("no position") from a permissive number,
    because a ceiling of 1e9 would occupy an NSGA-II dimension and read as
    satisfied forever. The rows follow: the reference SKU declares no `floors`,
    so `policy_floors` is not among its rows AT ALL.
    """
    cp = reference_policy()
    assert policy.ROW_FLOORS not in cp.rows
    bare = compile_policy(Constitution("bare", LegalEnvelope(),
                                       DesignDNA("no positions")))
    assert bare.rows == (policy.ROW_LEGAL,)


def test_every_policy_row_is_live_on_real_hulls():
    """No row may read the same satisfied number forever (the `list` defect).

    `evaluate`'s `list` row read EXACTLY -2.000 across 800 evaluations while
    occupying an NSGA-II constraint dimension. A governance row that did the
    same would be worse, because it would also be presented as compliance.
    MEASURED here on 200 L0-feasible hulls: 64.0% / 66.5% / 45.5% violated.
    """
    cp = reference_policy()
    seen = {r: set() for r in cp.rows}
    for x in _hulls(120, seed=1):
        ev = evaluate(x, MISSION, policy=cp)
        for r in cp.rows:
            seen[r].add(ev.g[r] > 0.0)
    for r, outcomes in seen.items():
        assert outcomes == {True, False}, (
            f"row {r!r} was always {outcomes} over 120 hulls — a constraint "
            f"dimension that cannot change is not a constraint")


def test_a_row_whose_quantity_is_undefined_is_a_violation_never_a_pass():
    """Gap E10's rule, extended to governance.

    `nan > 0.0` is False, so an unguarded non-finite policy row would read as
    satisfied — the exact shape of the defect that let a nan cruise speed
    produce ok=True and reach an HTTP response as literal `NaN`.
    """
    real = reference_policy()

    class NanPolicy:
        constitution = real.constitution
        rows = ("policy_legal",)

        def rows_for(self, ev, mission):
            return {"policy_legal": float("nan")}, {}

        def route_report(self, ev, mission):
            return real.route_report(ev, mission)

    ev = evaluate(_hulls(1)[0], MISSION, policy=NanPolicy())
    assert ev.g["policy_legal"] == ev_mod.INFEASIBLE_G
    assert not ev.ok
    assert any("not a finite number" in v for v in ev.violations)


def test_the_palettes_are_a_call_and_not_a_row():
    """Nothing in the ladder declares a propulsion yet, so a row would be dead.

    Compiled as `check_selection`, the palette is enforced where a selection is
    actually made — and it becomes a row in V3.2, live from its first
    evaluation.
    """
    cp = reference_policy()
    cp.check_selection("propulsion", "electric-pod")
    with pytest.raises(PolicyRefusal, match="forbidden list"):
        cp.check_selection("propulsion", "diesel-inboard")
    with pytest.raises(PolicyRefusal, match="palette"):
        cp.check_selection("material", "carbon-fibre")
    with pytest.raises(PolicyError, match="no palette named"):
        cp.check_selection("hull_colour", "blue")


def test_the_compile_report_names_what_it_compiled():
    rep = compile_policy(_constitution(_dna_with(trim_limit_deg=1.0))).report()
    assert rep["ratchets"] and "limits.TRIM_LIMIT_DEG" in rep["ratchets"][0]
    assert "1" in rep["ratchets"][0] and "2" in rep["ratchets"][0]
    assert "NOT legal advice" in rep["disclaimer"]
    assert rep["legal"]["allowed_categories"] == ["C", "D"]
