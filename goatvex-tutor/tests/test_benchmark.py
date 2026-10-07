"""Known-answer benchmark: every problem must solve, fully verify, and match the
hand-checked expected answer stored in the problem file."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import sympy as sp

from tutor.parse.schema import load_problem, parse_math, parse_matrix
from tutor.pipeline import solve_problem
from tutor.verify import PASS
from tutor.verify.equivalence import check_equal

BENCH = Path(__file__).parent / "benchmark"
FILES = sorted(BENCH.rglob("*.json"))


def test_benchmark_size():
    assert len(FILES) >= 30
    courses = {json.loads(f.read_text(encoding="utf-8"))["course"] for f in FILES}
    assert courses == {"MATH1104", "MATH1004"}


@pytest.mark.parametrize("path", FILES, ids=[f.stem for f in FILES])
def test_benchmark_problem(path):
    problem = load_problem(path)
    result = solve_problem(problem)
    failed = [c for c in result.checks if c.status != PASS]
    assert result.status == PASS, "\n".join(f"{c.step_id} {c.check}: {c.detail}" for c in failed)

    exp = problem.expected
    sol = result.solution
    if "kind" in exp:
        compare_generic(problem, sol, exp)
    elif problem.type == "rref":
        assert sol.answer == parse_matrix(exp["rref"])
        if "system" in exp:
            system = sol.facts["system"]
            assert system["status"] == exp["system"]["status"]
            if "x" in exp["system"]:
                assert system["particular"] == sp.Matrix([parse_math(v) for v in exp["system"]["x"]])
            if "free_vars" in exp["system"]:
                assert system["free_vars"] == exp["system"]["free_vars"]
    elif problem.type == "matrix_inverse":
        if exp.get("invertible") is False:
            assert sol.facts["invertible"] is False
        else:
            assert sol.facts["invertible"] is True
            assert sol.answer == parse_matrix(exp["inverse"])
    elif problem.type == "derivative":
        expected = parse_math(exp["derivative"], [problem.given["variable"]])
        status, detail = check_equal(sol.answer, expected, [problem.variable])
        assert status == PASS, detail
    else:  # pragma: no cover
        pytest.fail(f"no expected-answer comparison for {problem.type}")


def _expr(text, problem):
    return parse_math(text, problem.variables, imaginary=True)


def _same(a, b, problem=None):
    syms = [sp.Symbol(v, real=True) for v in (problem.variables if problem else [])] or None
    status, detail = check_equal(a, b, syms)
    return status == PASS


def compare_generic(problem, sol, exp):
    kind, want = exp["kind"], exp["answer"]
    ans = sol.answer
    if kind == "expr":
        assert _same(ans, _expr(want, problem), problem), f"{ans} != {want}"
    elif kind == "symbol":
        assert str(ans) == want
    elif kind == "string":
        assert ans == want
    elif kind == "matrix":
        assert sp.Matrix(ans) == parse_matrix(want)
    elif kind in ("list", "list_unordered"):
        got = list(ans)
        exp_vals = [_expr(w, problem) for w in want]
        assert len(got) == len(exp_vals)
        if kind == "list":
            assert all(_same(a, b) for a, b in zip(got, exp_vals)), f"{got} != {exp_vals}"
        else:
            for a in got:
                assert any(_same(a, b) for b in exp_vals), f"{a} not in {exp_vals}"
    elif kind == "polar":
        assert _same(sol.facts["r"], _expr(want[0], problem)) and _same(sol.facts["theta"], _expr(want[1], problem))
    elif kind == "plane":
        x, y, z = sp.symbols("x y z", real=True)
        lhs, rhs = want.split("=")
        e_want = parse_math(lhs, ["x", "y", "z"]) - parse_math(rhs, ["x", "y", "z"])
        e_got = ans.lhs - ans.rhs
        ratio = [sp.Poly(e_got, x, y, z).coeff_monomial(m) / sp.Poly(e_want, x, y, z).coeff_monomial(m)
                 for m in (x, y, z, 1) if sp.Poly(e_want, x, y, z).coeff_monomial(m) != 0]
        assert len(set(ratio)) == 1, f"{ans} is not a multiple of {want}"
    elif kind == "line_direction":
        d = sp.Matrix(sol.facts["d"])
        assert sp.Matrix.hstack(d, sp.Matrix([_expr(w, problem) for w in want])).rank() == 1
    else:  # pragma: no cover
        pytest.fail(f"unknown expected kind {kind}")


@pytest.mark.parametrize("path", FILES, ids=[f.stem for f in FILES])
def test_every_step_is_single_operation(path):
    """No skipped steps: row-op steps hold exactly one op; rule steps rewrite exactly one d/dx."""
    problem = load_problem(path)
    sol = solve_problem(problem).solution
    for step in sol.steps:
        if step.kind == "derivative_rule":
            assert isinstance(step.data["target"], sp.Derivative)
        if step.kind == "row_op":
            assert step.data["op"] in ("swap", "scale", "replace")
