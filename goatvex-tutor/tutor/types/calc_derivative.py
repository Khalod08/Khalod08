"""MATH 1004: derivative, one rule per step."""

from __future__ import annotations

import random

from tutor.parse.schema import Problem, require_only, require_variable
from tutor.registry import ProblemType, register
from tutor.solvers.calculus import derivative
from tutor.text.unicode_math import to_text
from tutor.types import _answers
from tutor.types._common import describe_lines
from tutor.verify.calculus import verify_derivative


def validate(p: Problem) -> None:
    x = require_variable(p)
    require_only(p.function, {x}, "the function")


def describe(p: Problem) -> str:
    x = p.given["variable"]
    return describe_lines(p, f"Find f′({x}) for  f({x}) = {to_text(p.function)}", [])


TEMPLATES = {
    1: ["{a}x^{n} + {b}x^{m} - {c}x + {d}", "{a}x^{n} - {b}/x + {c}sqrt(x)"],
    2: ["({a}x^2 + {b})^{n}", "sin({a}x^2)", "e^({a}x) cos(x)", "sqrt({a}x^2 + {b})", "ln({a}x^2 + {b})"],
    3: ["x^2 e^(-{a}x)", "({a}x + {b})/(x^2 + {c})", "x sin({a}x)^2", "arctan({a}x)/x", "(x^2 + {b})^{n} cos({a}x)"],
}


def generate(rng: random.Random, difficulty: int = 2):
    tpl = rng.choice(TEMPLATES[max(1, min(3, difficulty))])
    f = tpl.format(a=rng.randint(2, 5), b=rng.randint(1, 6), c=rng.randint(1, 5), d=rng.randint(1, 9),
                   n=rng.randint(3, 5), m=2)
    return {"function": f, "variable": "x"}, f"Differentiate f(x) = {f}."


def grade(solution, text: str):
    return _answers.grade_expr(solution.answer, text, [str(solution.facts["variable"])])


register(ProblemType(
    name="derivative", course="MATH1004", topic="derivatives", title="Derivative (rules, chain rule)",
    required=("function", "variable"), validate=validate, describe=describe, solve=derivative.solve,
    verify=verify_derivative, generate=generate, grade=grade,
    answer_format="an expression in x, e.g. 6x(3x^2+1)^4",
    template="derivative",
    sections={"Mingarelli": ["3.1", "3.2", "3.3", "3.4", "3.6", "4.1"]},
    keywords=("derivative", "differentiate", "d/dx", "chain rule", "product rule", "quotient rule"),
))
