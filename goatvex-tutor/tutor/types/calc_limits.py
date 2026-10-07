"""MATH 1004: limits (including one-sided, at infinity, L'Hôpital)."""

from __future__ import annotations

import random

from tutor.parse.schema import Problem, parse_math, require_only, require_variable
from tutor.registry import ProblemType, register
from tutor.solvers.calculus import limits
from tutor.text.unicode_math import to_text
from tutor.types import _answers
from tutor.types._common import describe_lines
from tutor.verify.calculus import verify_limit


def validate(p: Problem) -> None:
    x = require_variable(p)
    require_only(p.expr("function"), {x}, "the function")
    parse_math(p.given["point"])


def describe(p: Problem) -> str:
    d = p.given.get("direction", "+-")
    side = {"+": "⁺", "-": "⁻"}.get(d, "")
    return describe_lines(p, f"Find lim({p.given['variable']}→{to_text(parse_math(p.given['point']))}{side}) "
                             f"{to_text(p.expr('function'))}", [])


GEN = {
    1: [("(x^2 - {a2})/(x - {a})", "{a}"), ("(x^2 + {b}x)/x", "0"), ("({c}x^2 + 1)/({b}x^2 - x)", "oo")],
    2: [("(x^2 - {s}x + {p})/(x - {a})", "{a}"), ("(sqrt(x + {a2}) - {a})/x", "0"), ("sin({b}x)/x", "0"),
        ("({c}x^3 - x)/({b}x^3 + {a}x^2)", "oo")],
    3: [("(e^x - 1 - x)/x^2", "0"), ("x ln(x)", "0+"), ("(1 + {b}/x)^x", "oo"), ("(1 - cos(x))/x^2", "0"),
        ("1/(x - {a})", "{a}+")],
}


def generate(rng: random.Random, difficulty: int = 2):
    a = rng.randint(1, 5)
    b, c = rng.randint(2, 5), rng.randint(2, 6)
    r = rng.randint(1, 4)
    f, pt = rng.choice(GEN[max(1, min(3, difficulty))])
    f = f.format(a=a, a2=a * a, b=b, c=c, s=a + r, p=a * r)
    pt = pt.format(a=a)
    g = {"function": f, "variable": "x", "point": pt.rstrip("+-")}
    if pt.endswith("+") and pt != "+":
        g["direction"] = "+"
    return g, f"Find the limit of {f} as x → {pt}."


def grade(solution, text: str):
    t = text.lower()
    if solution.answer == limits.DNE:
        ok = "dne" in t or "does not exist" in t or "doesn't exist" in t
        return ok, "Correct: it does not exist." if ok else "Not quite: the one-sided limits differ, so it doesn't exist."
    return _answers.grade_expr(solution.answer, text)


register(ProblemType(
    name="limit", course="MATH1004", topic="limits", title="Limit",
    required=("function", "variable", "point"), validate=validate, describe=describe, solve=limits.solve,
    verify=verify_limit, generate=generate, grade=grade,
    answer_format="a number, oo / -oo, or DNE", template="limit",
    sections={"Mingarelli": ["2.1", "2.2", "2.3", "2.4", "2.5", "3.8", "3.9"]},
    keywords=("limit", "lim", "approaches", "l'hopital", "l'hospital", "asymptote", "indeterminate"),
))
