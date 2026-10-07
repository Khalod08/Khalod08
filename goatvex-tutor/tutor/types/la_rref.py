"""MATH 1104: row reduce to RREF / solve a linear system."""

from __future__ import annotations

import random

from tutor.errors import ProblemFormatError
from tutor.parse.schema import Problem
from tutor.registry import ProblemType, register
from tutor.solvers.linear_algebra import rref
from tutor.text.unicode_math import matrix_text, to_text
from tutor.types import _answers, _gen
from tutor.types._common import describe_lines
from tutor.verify.linear_algebra import verify_rref


def validate(p: Problem) -> None:
    m = p.matrix

    if p.given.get("augmented") and m.cols < 2:
        raise ProblemFormatError("an augmented matrix needs at least 2 columns")


def describe(p: Problem) -> str:
    m = p.matrix
    aug = p.given.get("augmented")
    ask = "Row reduce this " + ("augmented matrix [A | b]" if aug else "matrix") + " to RREF"
    ask += " and solve the system:" if aug else ":"
    return describe_lines(p, ask, [matrix_text(m, augmented_at=m.cols - 1 if aug else None)])


def generate(rng: random.Random, difficulty: int = 2):
    n = 2 if difficulty == 1 else 3
    A = _gen.unimodular(rng, n)
    x = _gen.int_vector(rng, n)
    if difficulty >= 3 and rng.random() < 0.5:
        # make row 3 a combination of rows 1 and 2 → a free variable
        a, b = _gen.nonzero(rng, -2, 2), _gen.nonzero(rng, -2, 2)
        A[2, :] = a * A[0, :] + b * A[1, :]
    bvec = A * x
    M = A.row_join(bvec)
    names = ["x", "y", "z"][:n]
    eqs = []
    for i in range(n):
        terms = " + ".join(f"{to_text(A[i, j])}{names[j]}" for j in range(n) if A[i, j] != 0)
        eqs.append(f"{terms} = {bvec[i]}".replace("+ −", "− ").replace("1x", "x").replace("1y", "y").replace("1z", "z"))
    statement = "Solve the system: " + ";  ".join(eqs)
    return {"matrix": _gen.strs(M), "augmented": True}, statement


def grade(solution, text: str):
    sysinfo = solution.facts.get("system")
    if ";" not in text and sysinfo and sysinfo["status"] == "unique":
        return _answers.grade_list(list(sysinfo["particular"]), text)
    if "no solution" in text.lower() or "inconsistent" in text.lower():
        ok = bool(sysinfo) and sysinfo["status"] == "inconsistent"
        return ok, "Correct! The system is inconsistent." if ok else "Not quite: this system does have solutions."
    return _answers.grade_matrix(solution.answer, text)


register(ProblemType(
    name="rref", course="MATH1104", topic="row-reduction", title="Row reduction / linear systems",
    required=("matrix",), validate=validate, describe=describe, solve=rref.solve, verify=verify_rref,
    generate=generate, grade=grade,
    answer_format="the solution as a list like 1, -2, 3 (or the RREF matrix with rows separated by ';')",
    template="row_reduction",
    sections={"Nicholson": ["1.1", "1.2", "1.3"], "Poole": ["2.1", "2.2"]},
    keywords=("row reduce", "rref", "echelon", "system", "gaussian", "gauss-jordan"),
))
