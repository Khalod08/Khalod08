"""MATH 1104: matrix arithmetic (sums, scalar multiples, products, transposes, powers)."""

from __future__ import annotations

import random
import re

import sympy as sp

from tutor.parse.schema import Problem
from tutor.registry import ProblemType, register
from tutor.solvers.linear_algebra import matrix_ops
from tutor.text.unicode_math import matrix_text
from tutor.types import _answers, _gen
from tutor.types._common import describe_lines
from tutor.verify.la_more import verify_matrix_arithmetic


def validate(p: Problem) -> None:
    mats = matrix_ops.matrices(p)
    matrix_ops.parse_matrix_expression(p.given["expression"], mats)


def describe(p: Problem) -> str:
    mats = matrix_ops.matrices(p)
    used = set(re.findall(r"[A-Z]", p.given["expression"].replace("^T", "")))
    body = []
    for name, m in mats.items():
        if name not in used:
            continue
        body.append(f"{name} =")
        body.append(matrix_text(m))
    return describe_lines(p, f"Compute {p.given['expression']}, where", body)


def generate(rng: random.Random, difficulty: int = 2):
    A = sp.Matrix(2, 3 if difficulty > 1 else 2, lambda i, j: rng.randint(-3, 4))
    B = sp.Matrix(A.cols, 2, lambda i, j: rng.randint(-3, 4))
    C = sp.Matrix(2, 2, lambda i, j: rng.randint(-3, 4))
    expr = rng.choice(["AB", "AB - 2C", "C^T + 3C", "(AB)^T"] if difficulty > 1 else ["2C - C^T", "AB"])
    mats = {k: _gen.strs(v) for k, v in (("A", A), ("B", B), ("C", C)) if k in expr}
    shown = expr.replace("^T", "ᵀ").replace(" - ", " − ")
    return {"matrices": mats, "expression": expr}, f"Compute {shown}."


def grade(solution, text: str):
    if not solution.facts.get("defined", True):
        ok = "not defined" in text.lower() or "undefined" in text.lower()
        return ok, "Correct: it isn't defined." if ok else "Check the sizes: this one is not defined."
    return _answers.grade_matrix(solution.answer, text)


register(ProblemType(
    name="matrix_arithmetic", course="MATH1104", topic="matrix-operations", title="Matrix arithmetic",
    required=("matrices", "expression"), validate=validate, describe=describe, solve=matrix_ops.solve,
    verify=verify_matrix_arithmetic, generate=generate, grade=grade,
    answer_format="the matrix with rows separated by ';', or 'not defined'",
    template="matrix_arithmetic",
    sections={"Nicholson": ["2.1", "2.2", "2.3"], "Poole": ["3.1", "3.2"]},
    keywords=("matrix product", "transpose", "matrix multiplication", "AB"),
))
