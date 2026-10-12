"""MATH 1104: matrix inverse by row reducing [A | I]."""

from __future__ import annotations

import random

from tutor.errors import ProblemFormatError
from tutor.parse.schema import Problem
from tutor.registry import ProblemType, register
from tutor.solvers.linear_algebra import inverse
from tutor.text.unicode_math import matrix_text
from tutor.types import _answers, _gen
from tutor.types._common import describe_lines
from tutor.verify.linear_algebra import verify_inverse


def validate(p: Problem) -> None:
    m = p.matrix

    if not m.is_square:
        raise ProblemFormatError("matrix_inverse needs a square matrix")


def describe(p: Problem) -> str:
    return describe_lines(p, "Find A⁻¹ (or show A is not invertible), where A =", [matrix_text(p.matrix)])


def generate(rng: random.Random, difficulty: int = 2):
    n = 2 if difficulty == 1 else 3
    A = _gen.unimodular(rng, n, det=2 if difficulty >= 3 else 1)
    return {"matrix": _gen.strs(A)}, "Find A⁻¹ if it exists."


def grade(solution, text: str):
    if not solution.facts["invertible"]:
        ok = any(w in text.lower() for w in ("none", "not invertible", "singular", "dne"))
        return ok, "Correct! A is not invertible." if ok else "Not quite: this A has no inverse (det A = 0)."
    return _answers.grade_matrix(solution.answer, text)


register(ProblemType(
    name="matrix_inverse", course="MATH1104", topic="matrix-inverse", title="Matrix inverse",
    required=("matrix",), validate=validate, describe=describe, solve=inverse.solve, verify=verify_inverse,
    generate=generate, grade=grade,
    answer_format="A⁻¹ with rows separated by ';' (e.g. 3 -1; -5 2), or 'not invertible'",
    template="matrix_inverse",
    sections={"Nicholson": ["2.4"], "Poole": ["3.3"]},
    keywords=("inverse", "invertible", "A^-1"),
))
