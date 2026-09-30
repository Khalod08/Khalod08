from __future__ import annotations

import json

import pytest
import sympy as sp

from tutor.__main__ import describe, main
from tutor.errors import NotConfirmed, ProblemFormatError, UnsupportedProblem
from tutor.parse.schema import parse_math, problem_from_dict
from tutor.pipeline import run, solve_problem
from tutor.text.unicode_math import to_text


def prob(**kw):
    base = dict(slug="demo-problem", course="MATH1104", type="matrix_inverse", given={"matrix": [["2", "1"], ["5", "3"]]})
    base.update(kw)
    return problem_from_dict(base)


def test_parsing_is_exact():
    assert parse_math("0.5") == sp.Rational(1, 2)
    assert parse_math("1/3") == sp.Rational(1, 3)
    x = sp.Symbol("x", real=True)
    assert parse_math("3x^2 + e^x + ln(x)", ["x"]) == 3 * x**2 + sp.exp(x) + sp.log(x)


@pytest.mark.parametrize(
    "bad",
    [
        dict(course="MATH9999"),
        dict(slug="Bad Slug"),
        dict(type="integral"),
        dict(given={"matrix": [["1", "2"], ["3"]]}),
        dict(given={"matrix": [["1", "2", "3"]]}),  # inverse of a non-square matrix
        dict(type="derivative", given={"function": "x y", "variable": "x"}),
        dict(given={"matrix": [["1", "2"], ["3", "4+"]]}),
    ],
)
def test_bad_problems_are_rejected(bad):
    with pytest.raises(ProblemFormatError):
        prob(**bad)


def test_unconfirmed_problem_is_not_solved():
    with pytest.raises(NotConfirmed):
        solve_problem(prob())


def test_symbolic_matrix_is_honestly_unsupported():
    p = prob(given={"matrix": [["1", "k"], ["2", "3"]]}, confirmed_by_student=True)
    with pytest.raises(UnsupportedProblem):
        solve_problem(p)


def test_x_to_the_x_is_honestly_unsupported():
    p = prob(course="MATH1004", type="derivative", given={"function": "x^x", "variable": "x"}, confirmed_by_student=True)
    with pytest.raises(UnsupportedProblem):
        solve_problem(p)


def test_run_writes_outputs(tmp_path):
    result = run(prob(confirmed_by_student=True), out_dir=tmp_path)
    assert result.verified
    report = (tmp_path / "verification_report.md").read_text(encoding="utf-8")
    assert "ALL CHECKS PASSED" in report and "❌" not in report
    sol = json.loads((tmp_path / "solution.json").read_text(encoding="utf-8"))
    assert sol["status"] == "PASS" and sol["digest"] == result.solution.digest()
    assert json.loads((tmp_path / "problem.json").read_text(encoding="utf-8"))["slug"] == "demo-problem"


def test_cli_confirm_then_solve(tmp_path, capsys):
    path = tmp_path / "q.json"
    path.write_text(json.dumps(dict(slug="cli-demo", course="MATH1004", type="derivative",
                                    given={"function": "x^2 sin(x)", "variable": "x"})), encoding="utf-8")
    assert main(["solve", str(path), "--out", str(tmp_path / "out")]) == 3  # refuses: not confirmed
    assert main(["show", str(path)]) == 0
    assert "NOT YET" in capsys.readouterr().out
    assert main(["confirm", str(path)]) == 0
    assert main(["solve", str(path), "--out", str(tmp_path / "out")]) == 0
    out = capsys.readouterr().out
    assert "Verification: PASS" in out


def test_terminal_text_has_no_latex():
    p = prob(course="MATH1004", type="derivative", given={"function": "sqrt(x) e^x / (x^2+1)", "variable": "x"},
             confirmed_by_student=True)
    result = solve_problem(p)
    for s in result.solution.steps:
        t = to_text(s.after)
        assert "\\" not in t and "**" not in t and "frac" not in t
    assert "\\" not in describe(p)


def test_unicode_formatting():
    x = sp.Symbol("x", real=True)
    assert to_text(3 * x**4 - 5 * x**2 + 7 * x - 2) == "3x⁴ − 5x² + 7x − 2"
    assert to_text(sp.sqrt(x)) == "√x"
    assert to_text(sp.log(x)) == "ln(x)"


def test_derivatives_are_not_factorized():
    """Student preference: easy to read, not fully factorized."""
    p = prob(course="MATH1004", type="derivative", given={"function": "(2x-1)^3 (x+2)^2", "variable": "x"},
             confirmed_by_student=True)
    result = solve_problem(p)
    assert result.verified
    assert all(s.operation != "Factor" for s in result.solution.steps)
    assert result.solution.answer.is_Add  # a sum of product-rule terms, not one fully factored product
