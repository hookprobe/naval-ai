"""CROSS-MACHINE PARITY: the classifier must separate the two classes.

`scripts/parity.py` exists because the naive cross-machine checks both
fail. Comparing exactly reports a failure every time — the two boxes were
MEASURED to disagree by one ulp (the Mac's suite run: `62 of 514 elements
differ, worst |diff| 1.110e-16`) and by hash (`stl_sha256` non-portable,
13 of 3.47M printed numbers within 1e-12 of a rounding boundary). Reading
the other machine's report instead is what produced the 2026-08-20 P0
incident, where a transcribed `1.110e-16` lost its exponent and became
"metre-scale, not float noise".

So the tool has to see THROUGH platform noise to code defects. These tests
assert exactly that, and they are the reason the bar can be trusted: a
classifier that has never been shown a defect it must catch is a
classifier nobody should believe.
"""
import copy
import importlib.util
import json
import math
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "_parity", Path(__file__).resolve().parents[1] / "scripts" / "parity.py")
parity = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(parity)


@pytest.fixture(scope="module")
def receipt():
    return parity.emit()


def test_the_receipt_stamps_the_machine_that_made_it(receipt):
    """A bit-level claim is a claim about ONE machine, so the receipt says
    which. This is the same lesson `GOLDEN_ARCH` records in
    tests/test_resistance.py, applied at the cross-machine boundary."""
    p = receipt["platform"]
    assert p["machine"] and p["numpy"] and p["python"] and p["system"]
    assert receipt["n_cases"] >= 2
    assert receipt["values"] and receipt["verdicts"]


def test_one_ulp_everywhere_is_PLATFORM_not_regression(receipt, capsys):
    """The arm64 case, simulated: nudge EVERY float by one ulp — larger
    than the 1.110e-16 the Mac actually measured — and the verdict must
    still be OK. A tool that cried regression here would be ignored within
    a day, which is the failure mode that matters most."""
    other = copy.deepcopy(receipt)
    other["platform"]["machine"] = "arm64"
    n = 0
    for k, v in other["values"].items():
        if isinstance(v, float) and math.isfinite(v) and v != 0.0:
            other["values"][k] = math.nextafter(v, math.inf)
            n += 1
    assert n > 50, "fixture too small to be a real test"

    assert parity.compare(receipt, other) == 0
    assert "PARITY: OK" in capsys.readouterr().out


def test_a_two_fold_error_is_REGRESSION_even_buried_in_ulp_noise(
        receipt, capsys):
    """The defect this repository actually shipped — `forceCoeffs wrong by
    exactly 2x on every symmetric run` — planted underneath the ulp noise
    of a different architecture. The tool must name it, and must not be
    distracted by the ~190 platform differences around it."""
    other = copy.deepcopy(receipt)
    other["platform"]["machine"] = "arm64"
    for k, v in other["values"].items():
        if isinstance(v, float) and math.isfinite(v) and v != 0.0:
            other["values"][k] = math.nextafter(v, math.inf)
    key = sorted(k for k, v in other["values"].items()
                 if isinstance(v, float) and math.isfinite(v) and v != 0.0)[0]
    other["values"][key] *= 2.0

    assert parity.compare(receipt, other) == 1
    out = capsys.readouterr().out
    assert "PARITY: FAILED" in out
    assert key in out, "the tool must NAME the quantity that moved"


def test_a_disagreeing_VERDICT_is_never_excused_by_tolerance(receipt,
                                                             capsys):
    """Numbers get a tolerance; verdicts do not. Two machines that disagree
    about REFUSED versus MARGINAL have a defect no rounding can explain,
    and this is the clause that says so."""
    other = copy.deepcopy(receipt)
    other["platform"]["machine"] = "arm64"
    k = sorted(other["verdicts"])[0]
    other["verdicts"][k] = "MARGINAL|MARGINAL|OK|OK|UNMEASURED|EMPIRICAL|X|True"

    assert parity.compare(receipt, other) == 1
    assert "VERDICT" in capsys.readouterr().out


def test_the_tolerance_band_is_empty_between_its_two_anchors():
    """The bar is 1e-12 because the band around it is EMPTY in every
    measurement taken: the largest cross-architecture difference measured
    is one ulp (~1.1e-16, four orders below) and the smallest real defect
    caught is a factor of two (twelve orders above). This test states the
    two anchors so that moving the bar has to argue with them."""
    assert parity.PLATFORM_REL_TOL == 1e-12
    one_ulp_relative = 1.110e-16
    smallest_real_defect = 1.0            # a 2x error is rel 0.5
    assert one_ulp_relative < parity.PLATFORM_REL_TOL < smallest_real_defect
    assert parity.PLATFORM_REL_TOL / one_ulp_relative > 1e3
