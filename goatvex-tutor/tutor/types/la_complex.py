"""MATH 1104 (week 1): complex numbers and De Moivre's theorem."""

from __future__ import annotations

import random

from tutor.errors import ProblemFormatError
from tutor.parse.schema import Problem, parse_math
from tutor.registry import ProblemType, register
from tutor.solvers.linear_algebra import complex_numbers as cn
from tutor.text.unicode_math import to_text
from tutor.types import _answers
from tutor.types._common import describe_lines
from tutor.verify.la_more import verify_complex

NEEDS = {"simplify": ("expression",), "polar": ("z",), "power": ("z", "n"), "roots": ("w", "n"),
         "quadratic": ("a", "b", "c")}


def validate(p: Problem) -> None:
    task = p.given["task"]
    if task not in NEEDS:
        raise ProblemFormatError(f"task must be one of {sorted(NEEDS)}")
    missing = [k for k in NEEDS[task] if k not in p.given]
    if missing:
        raise ProblemFormatError(f"task {task!r} needs {missing}")
    for k in NEEDS[task]:
        if k == "n":
            if int(p.given["n"]) < 1:
                raise ProblemFormatError("n must be a positive whole number")
            continue
        e = parse_math(p.given[k], imaginary=True)
        if e.free_symbols:
            raise ProblemFormatError(f"{k} must be a number (use i for √−1)")


def describe(p: Problem) -> str:
    g, task = p.given, p.given["task"]
    if task == "simplify":
        ask = f"Write in the form a + bi:  {to_text(parse_math(g['expression'], imaginary=True, evaluate=False))}"
    elif task == "polar":
        ask = f"Write z = {to_text(parse_math(g['z'], imaginary=True))} in polar form r(cos θ + i sin θ)."
    elif task == "power":
        ask = f"Use De Moivre's theorem to compute ({to_text(parse_math(g['z'], imaginary=True))})^{g['n']} in a + bi form."
    elif task == "roots":
        ask = f"Find all {g['n']} complex {g['n']}th roots of w = {to_text(parse_math(g['w'], imaginary=True))}."
    else:
        ask = f"Solve {g['a']}z² + ({g['b']})z + ({g['c']}) = 0 over the complex numbers."
    return describe_lines(p, ask, [])


def generate(rng: random.Random, difficulty: int = 2):
    task = rng.choice(["simplify", "polar", "power", "roots", "quadratic"] if difficulty > 1 else ["simplify", "polar"])
    nice = ["1 + i", "1 - i", "-1 + i", "sqrt(3) + i", "1 + sqrt(3) i", "-sqrt(3) + i", "-2 - 2i", "2i", "-3"]
    if task == "simplify":
        a, b, c, d = (rng.randint(-4, 4) or 1 for _ in range(4))
        expr = rng.choice([f"({a} + {b}i)({c} + {d}i)", f"({a} + {b}i)/({c} + {d}i)"])
        return {"task": task, "expression": expr}, f"Write {expr} in the form a + bi."
    if task == "polar":
        z = rng.choice(nice)
        return {"task": task, "z": z}, f"Write {z} in polar form."
    if task == "power":
        z, n = rng.choice(nice[:6]), rng.randint(4, 8)
        return {"task": task, "z": z, "n": n}, f"Compute ({z})^{n} using De Moivre's theorem."
    if task == "roots":
        w, n = rng.choice(["-8", "16", "i", "-1", "8i", "1"]), rng.choice([2, 3, 4])
        return {"task": task, "w": w, "n": n}, f"Find the {n}th roots of {w}."
    b, c = rng.randint(-6, 6), rng.randint(1, 13)
    while b * b - 4 * c >= 0:
        c += 1
    return {"task": task, "a": "1", "b": str(b), "c": str(c)}, f"Solve z² + {b}z + {c} = 0."


def grade(solution, text: str):
    task = solution.facts["task"]
    if task in ("roots", "quadratic"):
        return _answers.grade_list(solution.answer, text, ordered=False, imaginary=True)
    if task == "polar":
        r, th = solution.facts["r"], solution.facts["theta"]
        return _answers.grade_list([r, th], text, imaginary=True)
    return _answers.grade_expr(solution.answer, text, imaginary=True)


register(ProblemType(
    name="complex", course="MATH1104", topic="complex-numbers", title="Complex numbers / De Moivre",
    required=("task",), validate=validate, describe=describe, solve=cn.solve, verify=verify_complex,
    generate=generate, grade=grade,
    answer_format="a + bi (e.g. 3 - 2i); for polar: r, θ; for roots: all roots separated by commas",
    template="complex_plane",
    sections={"Nicholson": ["Appendix A"], "Poole": ["Appendix C"]},
    keywords=("complex", "imaginary", "polar form", "de moivre", "modulus", "argument", "roots of unity"),
))
