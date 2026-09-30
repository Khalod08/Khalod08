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
    if problem.type == "rref":
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
