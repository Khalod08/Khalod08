"""MATH 1004: antiderivatives, definite integrals, FTC, Riemann sums."""

from __future__ import annotations

import random

from tutor.errors import ProblemFormatError
from tutor.parse.schema import Problem, parse_math, require_only, require_variable
from tutor.registry import ProblemType, register
from tutor.solvers.calculus import integration_problems as ip
from tutor.text.unicode_math import to_text
from tutor.types import _answers
from tutor.types._common import describe_lines
from tutor.verify import integrals as vi


def _v_integrand(p: Problem) -> None:
    x = require_variable(p)
    require_only(p.expr("integrand"), {x}, "the integrand")


def _v_definite(p: Problem) -> None:
    _v_integrand(p)
    for k in ("a", "b"):
        if parse_math(p.given[k]).free_symbols:
            raise ProblemFormatError(f"limit {k} must be a number")


def _v_riemann(p: Problem) -> None:
    x = require_variable(p)
    require_only(p.expr("function"), {x}, "the function")
    int(p.given["n"])


def _v_ftc1(p: Problem) -> None:
    require_variable(p)


INDEF = {1: ["{a}x^{n} + {b}x - {c}", "{a}/x^2 + {b}sqrt(x)", "{a}e^x + {b}cos(x)"],
         2: ["x({a}x^2 + {b})^{n}", "{a}x e^(x^2)", "sin(x) cos(x)^{n}", "{a}x/(x^2 + {b})", "x^2 sqrt(x^3 + {b})"],
         3: ["x e^({a}x)", "x cos({a}x)", "ln(x)", "x^2 e^x", "1/(x^2 - {b}^2)", "({a}x + {b})/(x^2 + 3x + 2)"]}


def gen_indef(rng: random.Random, difficulty: int = 2):
    tpl = rng.choice(INDEF[max(1, min(3, difficulty))])
    f = tpl.format(a=rng.randint(2, 6), b=rng.randint(1, 5), c=rng.randint(1, 9), n=rng.randint(2, 4))
    return {"integrand": f, "variable": "x"}, f"Find ∫ {f} dx."


def gen_def(rng: random.Random, difficulty: int = 2):
    g, _ = gen_indef(rng, min(difficulty, 2))
    a, b = rng.choice([(0, 1), (0, 2), (1, 2), (1, 3), (-1, 1)])
    if "/x" in g["integrand"] or "sqrt(x)" in g["integrand"]:
        a, b = 1, 4
    g.update(a=str(a), b=str(b))
    return g, f"Evaluate ∫ from {a} to {b} of {g['integrand']} dx."


def gen_riemann(rng: random.Random, difficulty: int = 2):
    f = rng.choice(["x^2", "x^2 + 1", "4 - x^2", "x^3", "2x + 1", "1/x"])
    a, b = (1, 3) if f == "1/x" else rng.choice([(0, 2), (0, 4), (1, 3)])
    n = rng.choice([4]) if difficulty < 3 else rng.choice([4, 6])
    m = rng.choice(["left", "right", "midpoint"] if difficulty < 3 else ["trapezoid", "midpoint"])
    return {"function": f, "variable": "x", "a": str(a), "b": str(b), "n": n, "method": m}, \
        f"Approximate ∫ from {a} to {b} of {f} dx with a {m} sum, n = {n}."


def gen_ftc1(rng: random.Random, difficulty: int = 2):
    f = rng.choice(["sqrt(1 + t^3)", "sin(t^2)", "e^(-t^2)", "cos(t)/t", "ln(1 + t^2)"])
    up = rng.choice(["x", "x^2", "3x", "sin(x)"]) if difficulty > 1 else "x"
    g = {"integrand": f, "lower": "1", "upper": up, "variable": "x"}
    if difficulty >= 3:
        g["lower"] = "x"
    return g, f"Find d/dx of ∫ from {g['lower']} to {up} of {f} dt."


register(ProblemType(
    name="indefinite_integral", course="MATH1004", topic="integrals", title="Antiderivative (indefinite integral)",
    required=("integrand", "variable"), validate=_v_integrand,
    describe=lambda p: describe_lines(p, f"Find ∫ {to_text(p.expr('integrand'))} d{p.given['variable']}"
                                      + (f" with F({p.given['initial']['x']}) = {p.given['initial']['y']}"
                                         if "initial" in p.given else ""), []),
    solve=ip.indefinite, verify=vi.verify_indefinite, generate=gen_indef,
    grade=lambda sol, text: _answers.grade_expr(sol.answer, text, [str(sol.facts["variable"])],
                                                 up_to_constant="initial" not in sol.facts),
    answer_format="an antiderivative in x (the + C is optional)", template="integral",
    sections={"Mingarelli": ["6.1", "7.1", "7.2", "7.3", "7.4", "7.5", "7.6"]},
    keywords=("antiderivative", "integral", "integrate", "substitution", "by parts", "partial fractions"),
))

register(ProblemType(
    name="definite_integral", course="MATH1004", topic="integrals", title="Definite integral (FTC)",
    required=("integrand", "variable", "a", "b"), validate=_v_definite,
    describe=lambda p: describe_lines(p, f"Evaluate ∫ from {p.given['a']} to {p.given['b']} of "
                                         f"{to_text(p.expr('integrand'))} d{p.given['variable']}", []),
    solve=ip.definite, verify=vi.verify_definite, generate=gen_def,
    grade=lambda sol, text: _answers.grade_expr(sol.answer, text), answer_format="an exact number, e.g. 26/3",
    template="area_under_curve", sections={"Mingarelli": ["6.3", "6.4"]},
    keywords=("definite integral", "fundamental theorem", "area under"),
))

register(ProblemType(
    name="ftc_derivative", course="MATH1004", topic="integrals", title="FTC part 1 (derivative of an integral)",
    required=("integrand", "lower", "upper"), validate=_v_ftc1,
    describe=lambda p: describe_lines(p, f"Find d/dx of ∫ from {p.given['lower']} to {p.given['upper']} of "
                                         f"{p.given['integrand']} dt", []),
    solve=ip.ftc1, verify=vi.verify_ftc1, generate=gen_ftc1,
    grade=lambda sol, text: _answers.grade_expr(sol.answer, text, ["x"]), answer_format="an expression in x",
    template="ftc", sections={"Mingarelli": ["6.4"]},
    keywords=("fundamental theorem", "ftc", "derivative of an integral"),
))

register(ProblemType(
    name="riemann_sum", course="MATH1004", topic="integrals", title="Riemann sum",
    required=("function", "variable", "a", "b", "n"), validate=_v_riemann,
    describe=lambda p: describe_lines(p, f"Approximate ∫ from {p.given['a']} to {p.given['b']} of "
                                         f"{to_text(p.expr('function'))} dx using a {p.given.get('method', 'right')} "
                                         f"sum with n = {p.given['n']}", []),
    solve=ip.riemann, verify=vi.verify_riemann, generate=gen_riemann,
    grade=lambda sol, text: _answers.grade_expr(sol.answer, text), answer_format="an exact number or fraction",
    template="riemann", sections={"Mingarelli": ["6.2"]},
    keywords=("riemann", "left sum", "right sum", "midpoint", "trapezoid", "rectangles"),
))
