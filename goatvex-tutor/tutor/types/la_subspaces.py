"""MATH 1104 (weeks 7–9): span, linear independence, bases of Col/Row/Nul, rank."""

from __future__ import annotations

import random

import sympy as sp

from tutor.errors import ProblemFormatError
from tutor.parse.schema import Problem
from tutor.registry import ProblemType, register
from tutor.solvers.linear_algebra import subspaces
from tutor.text.unicode_math import matrix_text, vec_text
from tutor.types import _answers, _gen
from tutor.types._common import describe_lines
from tutor.verify.la_more import verify_subspaces


def validate(p: Problem) -> None:
    task = p.given.get("task")
    if task == "span":
        p.vecs("vectors")
        p.vec("w")
    elif task == "independence":
        p.vecs("vectors")
    elif task in ("bases", "rank"):
        p.matrix
    else:
        raise ProblemFormatError("task must be span, independence, bases or rank")


def describe(p: Problem) -> str:
    task = p.given["task"]
    if task == "span":
        vs = ", ".join(vec_text(v) for v in p.vecs("vectors"))
        return describe_lines(p, f"Is w = {vec_text(p.vec('w'))} in span{{{vs}}}? If so, write it as a combination.", [])
    if task == "independence":
        vs = ", ".join(vec_text(v) for v in p.vecs("vectors"))
        return describe_lines(p, f"Are the vectors {vs} linearly independent?", [])
    return describe_lines(p, "Find the rank of A and bases for Col(A), Row(A) and Nul(A), where A =",
                          [matrix_text(p.matrix)])


def generate(rng: random.Random, difficulty: int = 2):
    task = rng.choice(["span", "independence", "bases"])
    v1 = _gen.int_vector(rng, 3, -3, 3)
    v2 = _gen.int_vector(rng, 3, -3, 3)
    while sp.Matrix.hstack(v1, v2).rank() < 2:
        v2 = _gen.int_vector(rng, 3, -3, 3)
    if task == "span":
        a, b = rng.randint(-3, 3), rng.randint(-3, 3)
        w = a * v1 + b * v2 if rng.random() < 0.6 else _gen.int_vector(rng, 3)
        return ({"task": task, "vectors": [_gen.vstr(v1), _gen.vstr(v2)], "w": _gen.vstr(w)},
                f"Is {_gen.vstr(w)} in the span of {_gen.vstr(v1)} and {_gen.vstr(v2)}?")
    if task == "independence":
        v3 = rng.randint(-2, 2) * v1 + rng.randint(-2, 2) * v2 if rng.random() < 0.5 else _gen.int_vector(rng, 3)
        return ({"task": task, "vectors": [_gen.vstr(v1), _gen.vstr(v2), _gen.vstr(v3)]},
                "Are these vectors linearly independent?")
    A = sp.Matrix.hstack(v1, v2, v1 + v2, rng.randint(-2, 2) * v1)
    return {"task": "bases", "matrix": _gen.strs(A)}, "Find the rank and bases for Col, Row and Nul."


def grade(solution, text: str):
    t = text.strip().lower()
    if solution.facts["task"] in ("span", "independence"):
        yes = t.startswith(("y", "true", "independent", "in"))
        no = t.startswith(("n", "false", "dependent", "not"))
        ok = (yes and solution.answer) or (no and not solution.answer)
        return bool(ok), "Correct!" if ok else "Not quite: look at where the pivots are."
    return _answers.grade_expr(solution.answer, text)


register(ProblemType(
    name="subspaces", course="MATH1104", topic="span-and-bases", title="Span, independence, bases and rank",
    required=("task",), validate=validate, describe=describe, solve=subspaces.solve, verify=verify_subspaces,
    generate=generate, grade=grade, answer_format="yes / no (span, independence) or the rank",
    template="derivation",
    sections={"Nicholson": ["5.1", "5.2", "5.4"], "Poole": ["3.5", "6.1", "6.2"]},
    keywords=("span", "linearly independent", "basis", "dimension", "column space", "null space", "rank", "row space"),
))
