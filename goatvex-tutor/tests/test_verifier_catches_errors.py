"""The verifier must not be a rubber stamp: plant realistic mistakes and make
sure each one is caught (overall status FAIL)."""

from __future__ import annotations

from dataclasses import replace

import pytest
import sympy as sp

from tutor.parse.schema import problem_from_dict
from tutor import registry
from tutor.solvers.calculus import derivative as D
from tutor.solvers.linear_algebra.row_ops import REPLACE, SCALE, RowOp
from tutor.verify import FAIL, PASS, overall, verify
from tutor.verify.equivalence import check_equal


def solve(ptype, course="MATH1104", **given):
    p = problem_from_dict(dict(slug="t", course=course, type=ptype, given=given, confirmed_by_student=True))
    return registry.get(ptype).solve(p)


def failing_checks(sol):
    return [c for c in verify(sol) if c.status != PASS]


def restep(sol, idx, **changes):
    steps = list(sol.steps)
    steps[idx] = replace(steps[idx], **changes)
    return replace(sol, steps=steps)


RREF_M = dict(matrix=[["1", "2", "-1", "3"], ["2", "5", "1", "8"], ["3", "7", "0", "11"]], augmented=True)


def test_untampered_solutions_pass():
    assert overall(verify(solve("rref", **RREF_M))) == PASS
    assert overall(verify(solve("matrix_inverse", matrix=[["2", "1"], ["5", "3"]]))) == PASS
    assert overall(verify(solve("derivative", course="MATH1004", function="(3x^2+1)^5", variable="x"))) == PASS


def test_wrong_row_op_multiplier_is_caught():
    sol = solve("rref", **RREF_M)
    k = next(i for i, s in enumerate(sol.steps) if s.kind == "row_op" and s.data["op"] == REPLACE)
    s = sol.steps[k]
    op = s.data["rowop"]
    bad_op = RowOp(REPLACE, op.i, op.j, op.c + 1)  # e.g. R₂ → R₂ − 1R₁ instead of − 2R₁
    bad = restep(sol, k, after=bad_op.apply(s.before), data={**s.data, "rowop": bad_op})
    names = {c.check for c in failing_checks(bad)}
    assert "creates the intended zero" in names


def test_sign_error_in_one_entry_is_caught():
    sol = solve("rref", **RREF_M)
    k = next(i for i, s in enumerate(sol.steps) if s.kind == "row_op")
    after = sol.steps[k].after.copy()
    after[1, 2] = -after[1, 2]  # a classic sign slip
    bad = restep(sol, k, after=after)
    names = {c.check for c in failing_checks(bad)}
    assert "row op re-applied" in names
    assert "continues from previous step" in names


def test_two_ops_squashed_into_one_step_is_caught():
    sol = solve("rref", **RREF_M)
    # replace step 1's result with the result of steps 1 AND 2 combined, then drop step 2
    steps = list(sol.steps)
    steps[1] = replace(steps[1], after=steps[2].after)
    del steps[2]
    bad = replace(sol, steps=steps)
    assert overall(verify(bad)) == FAIL


def test_scaling_by_zero_is_not_elementary():
    sol = solve("rref", **RREF_M)
    k = next(i for i, s in enumerate(sol.steps) if s.kind == "row_op")
    s = sol.steps[k]
    zero = RowOp(SCALE, 0, c=sp.Integer(0))
    bad = restep(sol, k, data={**s.data, "rowop": zero, "op": "scale"})
    names = {c.check for c in failing_checks(bad)}
    assert "elementary row operation" in names


def test_wrong_final_rref_is_caught():
    sol = solve("rref", **RREF_M)
    wrong = sol.answer.copy()
    wrong[0, 3] += 1
    assert overall(verify(replace(sol, answer=wrong))) == FAIL


def test_wrong_inverse_entry_is_caught():
    sol = solve("matrix_inverse", matrix=[["1", "0", "2"], ["2", "-1", "3"], ["4", "1", "8"]])
    wrong = sol.answer.copy()
    wrong[2, 2] = -wrong[2, 2]
    names = {c.check for c in failing_checks(replace(sol, answer=wrong))}
    assert {"A·A⁻¹ = I", "A⁻¹·A = I", "second method: adjugate formula"} <= names


def test_claiming_singular_matrix_invertible_is_caught():
    sol = solve("matrix_inverse", matrix=[["1", "2"], ["2", "4"]])
    fake = replace(sol, facts={**sol.facts, "invertible": True}, answer=sp.Matrix([[1, 0], [0, 1]]))
    assert overall(verify(fake)) == FAIL


def _chain_step_index(sol):
    return next(i for i, s in enumerate(sol.steps) if s.kind == "derivative_rule" and s.data["rule"] == D.POWER_CHAIN)


def test_forgotten_inner_derivative_is_caught():
    sol = solve("derivative", course="MATH1004", function="(3x^2+1)^5", variable="x")
    k = _chain_step_index(sol)
    s = sol.steps[k]
    x = sp.Symbol("x", real=True)
    forgot = 5 * (3 * x**2 + 1) ** 4  # "forgot the chain rule inner derivative"
    with sp.evaluate(False):
        after = s.before.xreplace({s.data["target"]: forgot})
    bad = restep(sol, k, after=after, data={**s.data, "replacement": forgot})
    names = {c.check for c in failing_checks(bad)}
    assert "local rewrite vs sympy.diff" in names
    assert "whole line still equal" in names


def test_mislabelled_rule_is_caught():
    sol = solve("derivative", course="MATH1004", function="(3x^2+1)^5", variable="x")
    k = _chain_step_index(sol)
    s = sol.steps[k]
    bad = restep(sol, k, operation="Power rule", data={**s.data, "rule": D.POWER})
    names = {c.check for c in failing_checks(bad)}
    assert "rule matches the expression" in names


def test_wrong_final_derivative_is_caught():
    sol = solve("derivative", course="MATH1004", function="x^2 sin(x)", variable="x")
    x = sp.Symbol("x", real=True)
    bad = replace(sol, answer=2 * x * sp.cos(x))  # product rule "forgotten"
    names = {c.check for c in failing_checks(bad)}
    assert {"second method: sympy.diff", "finite-difference check", "last step is the answer"} <= names


def test_changed_problem_is_caught():
    """If the solution silently solves a different problem, the first check fails."""
    sol = solve("derivative", course="MATH1004", function="x^3", variable="x")
    other = solve("derivative", course="MATH1004", function="x^4", variable="x")
    bad = replace(other, problem=sol.problem)
    assert overall(verify(bad)) == FAIL


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("sin(x)^2 + cos(x)^2", "1", PASS),
        ("(x^2 - 1)/(x - 1)", "x + 1", PASS),
        ("sqrt(x^2)", "x", FAIL),        # false for negative x
        ("x + 1", "x", FAIL),
        ("ln(x^2)", "2 ln(x)", FAIL),    # false for negative x (real calculus)
        ("e^(2 ln(x))", "x^2", PASS),    # only defined for x > 0; checked there
    ],
)
def test_equivalence_checker(a, b, expected):
    from tutor.parse.schema import parse_math

    x = sp.Symbol("x", real=True)
    status, detail = check_equal(parse_math(a, ["x"]), parse_math(b, ["x"]), [x])
    assert status == expected, detail


# ---- newer types --------------------------------------------------------------------------
def test_wrong_determinant_arithmetic_is_caught():
    sol = solve("determinant", matrix=[["1", "2", "3"], ["0", "4", "5"], ["1", "0", "6"]])
    k = len(sol.steps) - 1  # the final arithmetic step
    bad = restep(sol, k, after=sol.steps[k].after + 1)
    bad = replace(bad, answer=sol.answer + 1)
    names = {c.check for c in failing_checks(bad)}
    assert "algebra step is an equality" in names and "second method: Bareiss + Berkowitz" in names


def test_wrong_cofactor_sign_is_caught():
    sol = solve("determinant", matrix=[["1", "2", "3"], ["0", "4", "5"], ["1", "0", "6"]])
    s = sol.steps[1]  # the cofactor expansion; flip the sign of the second term
    a, b = s.after.args
    with sp.evaluate(False):
        flipped = sp.Add(a, -b)
    bad = restep(sol, 1, after=flipped)
    assert "algebra step is an equality" in {c.check for c in failing_checks(bad)}


def test_wrong_complex_product_is_caught():
    sol = solve("complex", task="simplify", expression="(2 + 3i)(1 - i)")
    bad = replace(sol, answer=sp.Integer(-1) + sp.I)  # forgot that i² = −1 (3·(−1)·i² = +3)
    names = {c.check for c in failing_checks(bad)}
    assert "second method: SymPy evaluates the whole expression" in names


def test_wrong_cross_product_is_caught():
    sol = solve("geometry", task="cross", u=["1", "2", "3"], v=["4", "5", "6"])
    bad = replace(sol, answer=sp.ImmutableMatrix([3, 6, -3]))  # sign slip in the first component
    names = {c.check for c in failing_checks(bad)}
    assert {"u × v is orthogonal to u", "second method: SymPy cross"} <= names


def test_wrong_plane_is_caught():
    sol = solve("geometry", task="plane_through_points", P=["1", "0", "2"], Q=["2", "1", "0"], R=["0", "3", "1"])
    x, y, z = sp.symbols("x y z", real=True)
    bad = replace(sol, answer=sp.Eq(5 * x + 3 * y + 4 * z, 12))
    assert overall(verify(bad)) == FAIL


def test_wrong_matrix_product_entry_is_caught():
    sol = solve("matrix_arithmetic", matrices={"A": [["1", "2", "0"], ["3", "-1", "4"]],
                                               "B": [["2", "1"], ["0", "1"], ["1", "-2"]]}, expression="AB")
    wrong = sp.ImmutableMatrix([[2, 3], [10, 6]])
    bad = replace(restep(sol, len(sol.steps) - 1, after=wrong), answer=wrong)
    assert overall(verify(bad)) == FAIL
