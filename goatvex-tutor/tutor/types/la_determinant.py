"""MATH 1104: determinant (cofactor expansion or row reduction)."""

from __future__ import annotations

import random

import sympy as sp

from tutor.errors import ProblemFormatError
from tutor.parse.schema import Problem
from tutor.registry import ProblemType, register
from tutor.solvers.linear_algebra.determinant import det_steps
from tutor.solvers.linear_algebra.row_ops import check_exact
from tutor.steps import Solution
from tutor.text.unicode_math import matrix_text
from tutor.types import _answers, _gen
from tutor.types._common import describe_lines
from tutor.verify.la_more import verify_determinant


def validate(p: Problem) -> None:
    m = p.matrix
    if not m.is_square:
        raise ProblemFormatError("a determinant needs a square matrix")
    if p.given.get("method") not in (None, "cofactor", "row_reduction"):
        raise ProblemFormatError("method must be 'cofactor' or 'row_reduction'")


def describe(p: Problem) -> str:
    how = {"cofactor": " (by cofactor expansion)", "row_reduction": " (by row reduction)"}.get(p.given.get("method"), "")
    return describe_lines(p, f"Find det(A){how}, where A =", [matrix_text(p.matrix)])


def solve(p: Problem) -> Solution:
    m = p.matrix
    check_exact(m)
    steps, value, facts = det_steps(m, p.given.get("method"))
    notes = []
    if value == 0:
        notes.append("det(A) = 0, so A is not invertible (its columns are linearly dependent).")
    else:
        notes.append("det(A) ≠ 0, so A is invertible.")
    return Solution(problem=p, steps=steps, answer=value, answer_label="det(A)",
                    facts={"input": m, **facts}, notes=notes)


def generate(rng: random.Random, difficulty: int = 2):
    n = {1: 2, 2: 3, 3: 4}[max(1, min(3, difficulty))]
    while True:
        m = sp.Matrix(n, n, lambda i, j: rng.randint(-4, 5) if rng.random() > 0.3 else 0)
        if abs(m.det()) <= 60:
            break
    return {"matrix": _gen.strs(m)}, "Find det(A)."


def grade(solution, text: str):
    return _answers.grade_expr(solution.answer, text)


register(ProblemType(
    name="determinant", course="MATH1104", topic="determinants", title="Determinant",
    required=("matrix",), validate=validate, describe=describe, solve=solve, verify=verify_determinant,
    generate=generate, grade=grade, answer_format="a number, e.g. -14",
    template="determinant",
    sections={"Nicholson": ["3.1", "3.2"], "Poole": ["4.2"]},
    keywords=("determinant", "det", "cofactor"),
))
