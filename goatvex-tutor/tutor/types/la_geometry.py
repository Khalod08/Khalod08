"""MATH 1104 (week 2): vectors, lines and planes."""

from __future__ import annotations

import random

from tutor.errors import ProblemFormatError
from tutor.parse.schema import Problem
from tutor.registry import ProblemType, register
from tutor.solvers.linear_algebra import geometry as G
from tutor.text.unicode_math import to_text, vec_text
from tutor.types import _answers
from tutor.types._common import describe_lines
from tutor.verify.la_more import verify_geometry

NEEDS = {
    "dot": ("u", "v"), "norm": ("u",), "unit": ("u",), "angle": ("u", "v"), "projection": ("u", "v"),
    "cross": ("u", "v"), "area_parallelogram": ("u", "v"), "area_triangle": ("u", "v"),
    "line_through_points": ("P", "Q"), "plane_point_normal": ("P", "n"), "plane_through_points": ("P", "Q", "R"),
    "line_plane_intersection": ("line", "plane"), "line_line_intersection": ("line1", "line2"),
    "plane_plane_intersection": ("plane1", "plane2"), "point_plane_distance": ("Q", "plane"),
    "point_line_distance": ("Q", "line"),
}
ASK = {
    "dot": "Compute u·v", "norm": "Find ‖u‖", "unit": "Find the unit vector in the direction of u",
    "angle": "Find the angle between u and v", "projection": "Find proj_v u",
    "cross": "Compute u × v", "area_parallelogram": "Find the area of the parallelogram spanned by u and v",
    "area_triangle": "Find the area of the triangle with sides u and v",
    "line_through_points": "Find vector and parametric equations of the line through P and Q",
    "plane_point_normal": "Find the equation of the plane through P with normal n",
    "plane_through_points": "Find the equation of the plane through P, Q and R",
    "line_plane_intersection": "Find where the line meets the plane",
    "line_line_intersection": "Do the lines intersect? If so, where?",
    "plane_plane_intersection": "Find the line of intersection of the two planes",
    "point_plane_distance": "Find the distance from Q to the plane",
    "point_line_distance": "Find the distance from Q to the line",
}


def validate(p: Problem) -> None:
    task = p.given["task"]
    if task not in NEEDS:
        raise ProblemFormatError(f"task must be one of {sorted(NEEDS)}")
    for k in NEEDS[task]:
        if k not in p.given:
            raise ProblemFormatError(f"task {task!r} needs {k!r}")
        if k.startswith("plane"):
            G.read_plane(p, k)
        elif k.startswith("line"):
            G.read_line(p, k)
        else:
            p.vec(k)
    if task in ("cross", "area_parallelogram", "area_triangle", "plane_through_points") and any(
            p.vec(k).rows != 3 for k in NEEDS[task]):
        raise ProblemFormatError(f"{task} needs vectors/points in ℝ³")


def describe(p: Problem) -> str:
    task = p.given["task"]
    body = []
    for k in NEEDS[task]:
        val = p.given[k]
        if k.startswith("plane"):
            body.append(f"{k}: {val}")
        elif k.startswith("line"):
            P, d = G.read_line(p, k)
            body.append(f"{k}: (x, y, z) = {vec_text(P)} + t{vec_text(d)}")
        else:
            body.append(f"{k} = {vec_text(p.vec(k))}")
    return describe_lines(p, ASK[task] + ":", body)


def generate(rng: random.Random, difficulty: int = 2):
    r = lambda: [str(rng.randint(-4, 4)) for _ in range(3)]  # noqa: E731
    task = rng.choice(["dot", "angle", "projection", "cross", "plane_through_points", "line_plane_intersection",
                       "point_plane_distance"] if difficulty > 1 else ["dot", "norm", "cross", "line_through_points"])
    g = {"task": task}
    for k in NEEDS[task]:
        if k == "plane":
            a, b, c = (rng.randint(-3, 3) or 1 for _ in range(3))
            g[k] = f"{a}x + {b}y + {c}z = {rng.randint(-6, 6)}"
        elif k.startswith("line"):
            g[k] = {"point": r(), "direction": [str(rng.randint(-3, 3) or 1) for _ in range(3)]}
        else:
            g[k] = r()
    return g, ASK[task] + "."


def grade(solution, text: str):
    ans = solution.answer
    if isinstance(ans, str) or isinstance(ans, list):
        return False, "For this kind of answer, compare with the write-up (equations/cases aren't auto-graded yet)."
    if hasattr(ans, "rows"):
        return _answers.grade_list(list(ans), text)
    return _answers.grade_expr(ans, text)


register(ProblemType(
    name="geometry", course="MATH1104", topic="vectors-lines-planes", title="Vectors, lines and planes",
    required=("task",), validate=validate, describe=describe, solve=G.solve, verify=verify_geometry,
    generate=generate, grade=grade,
    answer_format="a number, or a vector as a list like 1, -2, 3",
    template="vectors_3d",
    sections={"Nicholson": ["4.1", "4.2"], "Poole": ["1.1", "1.2", "1.3"]},
    keywords=("vector", "dot product", "cross product", "projection", "line", "plane", "normal", "distance", "angle"),
))
