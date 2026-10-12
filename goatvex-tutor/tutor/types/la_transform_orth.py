"""MATH 1104 (weeks 10 and 12): linear transformations; Gram–Schmidt and projections."""

from __future__ import annotations

import random

import sympy as sp

from tutor.errors import ProblemFormatError
from tutor.parse.schema import Problem
from tutor.registry import ProblemType, register
from tutor.solvers.linear_algebra import orthogonal, transformations
from tutor.text.unicode_math import to_text, vec_text
from tutor.types import _answers, _gen
from tutor.types._common import describe_lines
from tutor.verify.la_more import verify_orthogonal, verify_transformation


def _v_t(p: Problem) -> None:
    if not isinstance(p.given.get("variables"), list) or not isinstance(p.given.get("formula"), list):
        raise ProblemFormatError("give 'variables' (e.g. [\"x\",\"y\"]) and 'formula' (one string per component)")
    transformations.read_T(p)


def _d_t(p: Problem) -> str:
    xs, comps = transformations.read_T(p)
    extra = f" Also find T{vec_text(p.vec('v'))}." if "v" in p.given else ""
    return describe_lines(p, f"T{vec_text(xs)} = {vec_text(comps)}. Is T linear? Find its standard matrix, kernel "
                             f"and range.{extra}", [])


def _g_t(rng, difficulty=2):
    a, b, c, d = (rng.randint(-3, 3) or 1 for _ in range(4))
    g = {"variables": ["x", "y", "z"], "formula": [f"{a}x - {b}y + z", f"{c}x + {d}z"]}
    if difficulty >= 2:
        g["v"] = [str(rng.randint(-3, 3)) for _ in range(3)]
    return g, "Find the standard matrix, kernel and range of T."


def _v_o(p: Problem) -> None:
    if p.given.get("task") not in ("gram_schmidt", "projection"):
        raise ProblemFormatError("task must be gram_schmidt or projection")
    p.vecs("vectors")
    if p.given["task"] == "projection":
        p.vec("y")


def _d_o(p: Problem) -> str:
    vs = ", ".join(vec_text(v) for v in p.vecs("vectors"))
    if p.given["task"] == "gram_schmidt":
        return describe_lines(p, f"Apply Gram–Schmidt to {vs}" + (" and normalize" if p.given.get("normalize") else ""),
                              [])
    return describe_lines(p, f"Project y = {vec_text(p.vec('y'))} onto W = span{{{vs}}}", [])


def _g_o(rng, difficulty=2):
    x1 = [rng.choice([1, 2]), rng.randint(-1, 1), rng.randint(0, 2)]
    x2 = [rng.randint(-2, 2), rng.randint(1, 3), rng.randint(-1, 1)]
    if sp.Matrix.hstack(sp.Matrix(x1), sp.Matrix(x2)).rank() < 2:
        x2 = [0, 1, 1]
    if difficulty == 1 or rng.random() < 0.5:
        return {"task": "gram_schmidt", "vectors": [list(map(str, x1)), list(map(str, x2))]}, "Gram–Schmidt."
    return ({"task": "projection", "vectors": [list(map(str, x1)), list(map(str, x2))],
             "y": [str(rng.randint(-3, 3)) for _ in range(3)]}, "Project y onto W.")


register(ProblemType(
    name="linear_transformation", course="MATH1104", topic="linear-transformations", title="Linear transformation",
    required=("variables", "formula"), validate=_v_t, describe=_d_t, solve=transformations.solve,
    verify=verify_transformation, generate=_g_t,
    grade=lambda sol, text: _answers.grade_matrix(sol.answer, text) if sol.facts["linear"] else
    (("not" in text.lower()), "T is not linear."),
    answer_text=lambda sol: ("; ".join(" ".join(str(e) for e in sol.answer.row(i)) for i in range(sol.answer.rows))
                             if sol.facts["linear"] else "not linear"),
    answer_format="the standard matrix, rows separated by ';'", template="derivation",
    sections={"Nicholson": ["7.1", "7.2"], "Poole": ["3.6", "6.4", "6.5", "6.6"]},
    keywords=("linear transformation", "standard matrix", "kernel", "range", "one-to-one", "onto"),
))

register(ProblemType(
    name="orthogonality", course="MATH1104", topic="orthogonality", title="Gram–Schmidt and projections",
    required=("task", "vectors"), validate=_v_o, describe=_d_o, solve=orthogonal.solve, verify=verify_orthogonal,
    generate=_g_o,
    grade=lambda sol, text: _answers.grade_list(list(sol.answer), text) if sol.facts["task"] == "projection" else
    _answers.grade_orthogonal_basis(list(sol.facts["xs"]), text),
    answer_text=lambda sol: (", ".join(str(e) for e in sol.answer) if sol.facts["task"] == "projection"
                             else _answers.vectors_text(sol.answer)),
    answer_format="Gram–Schmidt: the vectors in brackets, e.g. (1, 0, 1), (1, 2, -1); projection: 1, 2, 0", template="derivation",
    sections={"Nicholson": ["5.3", "8.1"], "Poole": ["5.1", "5.2", "5.3"]},
    keywords=("gram-schmidt", "orthogonal", "orthonormal", "projection onto", "orthogonal basis"),
))
