"""MATH 1004: implicit differentiation, tangent/normal lines, logarithmic differentiation, related rates."""

from __future__ import annotations

import random

from tutor.errors import ProblemFormatError
from tutor.parse.schema import Problem, parse_math, require_only, require_variable
from tutor.registry import ProblemType, register
from tutor.solvers.calculus import implicit as im
from tutor.text.unicode_math import to_text
from tutor.types import _answers
from tutor.types._common import describe_lines
from tutor.verify import calculus as vc


def _v_implicit(p: Problem) -> None:
    im.parse_equation(p.given["equation"], [p.given.get("variable", "x"), p.given.get("dependent", "y")])


def _v_tangent(p: Problem) -> None:
    x = require_variable(p)
    require_only(p.expr("function"), {x}, "the function")
    parse_math(p.given["point"])


def _v_rr(p: Problem) -> None:
    g = p.given
    if not isinstance(g.get("variables"), list) or not isinstance(g.get("known"), dict):
        raise ProblemFormatError("related rates need 'variables' (list), 'relation', 'known' (dict), 'find'")
    im.parse_equation(g["relation"], g["variables"])


def gen_implicit(rng, difficulty=2):
    eqs = {1: ["x^2 + y^2 = 25", "x y = 6"], 2: ["x^3 + y^3 = 9 x y", "x^2 y + y^3 = 10", "sin(y) + x = y^2"],
           3: ["x^2 + x y + y^2 = 7", "e^(x y) = x + y", "x^2 - x y + y^2 = 3"]}
    pts = {"x^2 + y^2 = 25": ["3", "4"], "x y = 6": ["2", "3"], "x^2 + x y + y^2 = 7": ["1", "2"],
           "x^2 - x y + y^2 = 3": ["1", "2"], "x^2 y + y^3 = 10": ["3", "1"]}
    e = rng.choice(eqs[max(1, min(3, difficulty))])
    g = {"equation": e, "variable": "x", "dependent": "y"}
    if e in pts and rng.random() < 0.6:
        g["point"] = pts[e]
    return g, f"Find dy/dx for {e}" + (f" and the tangent line at ({g['point'][0]}, {g['point'][1]})." if "point" in g else ".")


def gen_tangent(rng, difficulty=2):
    f = rng.choice(["x^2 - 3x + 1", "x^3 - 2x", "sqrt(x)", "1/x", "e^(2x)", "ln(x)", "sin(x)", "x e^x"])
    a = {"sqrt(x)": "4", "ln(x)": "1", "1/x": "2", "sin(x)": "pi"}.get(f, str(rng.randint(-2, 3)))
    g = {"function": f, "variable": "x", "point": a}
    if difficulty >= 3:
        g["normal"] = True
    return g, f"Find the {'normal' if g.get('normal') else 'tangent'} line to y = {f} at x = {a}."


def gen_logdiff(rng, difficulty=2):
    f = rng.choice(["x^x", "x^(sin(x))", "(x^2 + 1)^3 (x - 1)^4 / sqrt(x)", "x^(1/x)", "(ln(x))^x"])
    return {"function": f, "variable": "x"}, f"Use logarithmic differentiation to find dy/dx for y = {f}."


def gen_rr(rng, difficulty=2):
    kind = rng.choice(["ladder", "balloon", "circle"])
    if kind == "ladder":
        L, x0, r = rng.choice([(10, 6, 2), (13, 5, 3), (5, 3, 1)])
        return ({"variables": ["x", "y"], "relation": f"x^2 + y^2 = {L*L}", "known": {"x": str(x0), "dx/dt": str(r)},
                 "find": "dy/dt", "units": "m/s"},
                f"A {L} m ladder slides away from a wall at {r} m/s. How fast is the top sliding down when the bottom is {x0} m out?")
    if kind == "balloon":
        r0, rate = rng.choice([(5, 100), (10, 50), (3, 36)])
        return ({"variables": ["V", "r"], "relation": "V = 4/3 pi r^3", "known": {"r": str(r0), "dV/dt": str(rate)},
                 "find": "dr/dt", "units": "cm/s"},
                f"Air is pumped into a spherical balloon at {rate} cm³/s. How fast is the radius growing when r = {r0} cm?")
    r0, rate = rng.choice([(10, 2), (4, 3)])
    return ({"variables": ["A", "r"], "relation": "A = pi r^2", "known": {"r": str(r0), "dr/dt": str(rate)},
             "find": "dA/dt", "units": "cm²/s"},
            f"A circle's radius grows at {rate} cm/s. How fast is the area growing when r = {r0} cm?")


register(ProblemType(
    name="implicit_derivative", course="MATH1004", topic="implicit-differentiation", title="Implicit differentiation",
    required=("equation",), validate=_v_implicit,
    describe=lambda p: describe_lines(p, f"Find dy/dx for {p.given['equation']}"
                                      + (f" and the tangent line at ({p.given['point'][0]}, {p.given['point'][1]})"
                                         if "point" in p.given else ""), []),
    solve=im.implicit, verify=vc.verify_implicit, generate=gen_implicit,
    grade=lambda sol, text: (_answers.grade_expr(sol.answer.rhs, text, ["x"]) if hasattr(sol.answer, "rhs")
                             else _answers.grade_expr(sol.answer.xreplace({sol.facts["y"]: sol.facts["ysym"]}), text,
                                                      ["x", "y"])),
    answer_format="dy/dx in terms of x and y (or the tangent line y = mx + b if a point is given)",
    template="implicit", sections={"Mingarelli": ["3.3"]},
    keywords=("implicit", "dy/dx", "implicitly"),
))

register(ProblemType(
    name="tangent_line", course="MATH1004", topic="tangent-lines", title="Tangent / normal line",
    required=("function", "variable", "point"), validate=_v_tangent,
    describe=lambda p: describe_lines(p, f"Find the {'normal' if p.given.get('normal') else 'tangent'} line to "
                                         f"y = {to_text(p.expr('function'))} at x = {p.given['point']}", []),
    solve=im.tangent_line, verify=vc.verify_tangent, generate=gen_tangent,
    grade=lambda sol, text: _answers.grade_expr(sol.answer.rhs, text, ["x"]) if sol.answer.lhs != sol.facts["x"]
    else (False, "The line is vertical: x = constant."),
    answer_format="y = mx + b", template="tangent_line", sections={"Mingarelli": ["5.1"]},
    keywords=("tangent line", "normal line", "slope of the curve"),
))

register(ProblemType(
    name="log_differentiation", course="MATH1004", topic="derivatives", title="Logarithmic differentiation",
    required=("function", "variable"), validate=lambda p: require_only(p.expr("function"), {require_variable(p)}, "f"),
    describe=lambda p: describe_lines(p, f"Find dy/dx for y = {to_text(p.expr('function'))} (logarithmic "
                                         "differentiation)", []),
    solve=im.log_diff, verify=vc.verify_logdiff, generate=gen_logdiff,
    grade=lambda sol, text: _answers.grade_expr(sol.answer, text, ["x"]),
    answer_format="an expression in x", template="derivative", sections={"Mingarelli": ["4.4"]},
    keywords=("logarithmic differentiation", "x^x"),
))

register(ProblemType(
    name="related_rates", course="MATH1004", topic="related-rates", title="Related rates",
    required=("variables", "relation", "known", "find"), validate=_v_rr,
    describe=lambda p: describe_lines(p, f"Relation: {p.given['relation']}. Known: "
                                         + ", ".join(f"{k} = {v}" for k, v in p.given["known"].items())
                                         + f". Find {p.given['find']}"
                                         + ("" if not p.given.get("assume_positive", True)
                                            else " (all quantities positive)"), []),
    solve=im.related_rates, verify=vc.verify_related_rates, generate=gen_rr,
    grade=lambda sol, text: _answers.grade_expr(sol.answer, text), answer_format="a number (exact or decimal)",
    template="related_rates", sections={"Mingarelli": ["5.2"]},
    keywords=("related rates", "how fast", "rate of change", "ladder", "balloon"),
))
