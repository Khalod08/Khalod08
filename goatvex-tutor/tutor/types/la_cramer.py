"""MATH 1104: Cramer's rule."""

from __future__ import annotations

import random

from tutor.errors import ProblemFormatError
from tutor.parse.schema import Problem
from tutor.registry import ProblemType, register
from tutor.solvers.linear_algebra import cramer
from tutor.text.unicode_math import matrix_text
from tutor.types import _answers, _gen
from tutor.types._common import describe_lines
from tutor.verify.la_more import verify_cramer


def validate(p: Problem) -> None:
    A, b = cramer.split_system(p)
    if not A.is_square:
        raise ProblemFormatError("Cramer's rule needs a square coefficient matrix A")
    if b.rows != A.rows:
        raise ProblemFormatError("b must have one entry per equation")


def describe(p: Problem) -> str:
    A, b = cramer.split_system(p)
    return describe_lines(p, "Solve A·x = b using Cramer's rule, where [A | b] =",
                          [matrix_text(A.row_join(b), augmented_at=A.cols)])


def generate(rng: random.Random, difficulty: int = 2):
    n = 2 if difficulty == 1 else 3
    A = _gen.unimodular(rng, n, det=rng.choice([1, 2, 3]))
    x = _gen.int_vector(rng, n)
    return {"matrix": _gen.strs(A), "vector": _gen.vstr(A * x)}, "Use Cramer's rule to solve A·x = b."


def grade(solution, text: str):
    if not solution.facts.get("applies", True):
        ok = "not" in text.lower() or "doesn" in text.lower() or "det" in text.lower()
        return ok, "Correct: det(A) = 0 so Cramer's rule doesn't apply." if ok else "Check det(A) first."
    return _answers.grade_list(list(solution.answer), text)


register(ProblemType(
    name="cramers_rule", course="MATH1104", topic="cramers-rule", title="Cramer's rule",
    required=("matrix",), validate=validate, describe=describe, solve=cramer.solve, verify=verify_cramer,
    generate=generate, grade=grade, answer_format="x₁, x₂, ... as a list, e.g. 2, -1, 3",
    template="cramer",
    sections={"Nicholson": ["3.2"], "Poole": ["4.4"]},
    keywords=("cramer", "cramer's rule"),
))
