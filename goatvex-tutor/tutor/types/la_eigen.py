"""MATH 1104 (week 11): eigenvalues, eigenvectors, diagonalization, complex eigenvalues."""

from __future__ import annotations

import random

import sympy as sp

from tutor.errors import ProblemFormatError
from tutor.parse.schema import Problem
from tutor.registry import ProblemType, register
from tutor.solvers.linear_algebra import eigen
from tutor.text.unicode_math import matrix_text
from tutor.types import _answers, _gen
from tutor.types._common import describe_lines
from tutor.verify.la_more import verify_eigen


def validate(p: Problem) -> None:
    m = p.matrix
    if not m.is_square:
        raise ProblemFormatError("eigenvalues need a square matrix")
    if p.given.get("task", "eigen") not in ("eigen", "diagonalize"):
        raise ProblemFormatError("task must be 'eigen' or 'diagonalize'")


def describe(p: Problem) -> str:
    ask = "Diagonalize A (find P and D with A = PDP⁻¹), or show it can't be done, where A =" \
        if p.given.get("task") == "diagonalize" else "Find the eigenvalues and a basis of each eigenspace of A ="
    return describe_lines(p, ask, [matrix_text(p.matrix)])


def generate(rng: random.Random, difficulty: int = 2):
    n = 2 if difficulty == 1 else 3 if difficulty == 3 else rng.choice([2, 3])
    while True:
        P = _gen.unimodular(rng, n, spread=1)
        lams = [rng.randint(-3, 4) for _ in range(n)]
        A = P * sp.diag(*lams) * P.inv()
        if all(e.is_Integer and abs(e) <= 9 for e in A):
            break
    task = "diagonalize" if difficulty >= 2 else "eigen"
    return {"matrix": _gen.strs(A), "task": task}, ("Diagonalize A." if task == "diagonalize" else "Find the eigenvalues "
                                                    "and eigenvectors of A.")


def grade(solution, text: str):
    f = solution.facts
    with_mult = [lv for lv in f["eigenvalues"] for _ in range(f["multiplicities"][lv])]
    return _answers.grade_list(with_mult, text, ordered=False, imaginary=True)


register(ProblemType(
    name="eigen", course="MATH1104", topic="eigenvalues", title="Eigenvalues, eigenvectors, diagonalization",
    required=("matrix",), validate=validate, describe=describe, solve=eigen.solve, verify=verify_eigen,
    generate=generate, grade=grade,
    answer_text=lambda sol: ", ".join(str(lv) for lv in sol.facts["eigenvalues"]
                                      for _ in range(sol.facts["multiplicities"][lv])), answer_format="the eigenvalues, e.g. 2, -1 (repeat a repeated one)",
    template="derivation",
    sections={"Nicholson": ["3.3", "3.4", "5.5"], "Poole": ["4.1", "4.3", "4.4"]},
    keywords=("eigenvalue", "eigenvector", "characteristic polynomial", "diagonalize", "eigenspace"),
))
