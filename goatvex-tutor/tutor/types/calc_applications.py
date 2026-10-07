"""MATH 1004: optimization, curve sketching, improper integrals, area, volume, domain, inverses,
linearization, higher derivatives."""

from __future__ import annotations

import random

from tutor.parse.schema import Problem, parse_math, require_only, require_variable
from tutor.registry import ProblemType, register
from tutor.solvers.calculus import applications as ap
from tutor.text.unicode_math import to_text
from tutor.types import _answers
from tutor.types._common import describe_lines
from tutor.verify import calc_apps as va


def _fx(key="function"):
    def v(p: Problem):
        x = require_variable(p)
        require_only(p.expr(key), {x}, key)
    return v


def _d(text_fn):
    return lambda p: describe_lines(p, text_fn(p), [])


def expr_grade(sol, text):
    return _answers.grade_expr(sol.answer, text, [str(sol.facts.get("x", "x"))])


def num_grade(sol, text):
    return _answers.grade_expr(sol.answer, text)


T = [
    dict(name="optimization", topic="optimization", title="Optimization (absolute max/min)",
         required=("function", "variable"), validate=_fx(), solve=ap.optimization, verify=va.verify_optimization,
         describe=_d(lambda p: f"Find the absolute {p.given.get('goal', 'maximum and minimum')} of f(x) = "
                                f"{to_text(p.function)} on [{p.given.get('a', '−∞')}, {p.given.get('b', '∞')}]"),
         generate=lambda r, d=2: ({"function": r.choice(["x^3 - 3x^2 + 1", "x^3 - 12x", "2x^3 - 9x^2 + 12x",
                                                         "x e^(-x)", "x^4 - 8x^2"]), "variable": "x",
                                   "a": str(r.randint(-3, 0)), "b": str(r.randint(2, 4))}, "Find the absolute extrema."),
         grade=lambda sol, text: _answers.grade_list(list(sol.answer), text) if isinstance(sol.answer, tuple)
         else num_grade(sol, text),
         answer_format="max, min (e.g. 5, -3)", sections={"Mingarelli": ["5.3"]},
         keywords=("maximum", "minimum", "optimize", "largest", "smallest", "critical point")),
    dict(name="curve_sketching", topic="curve-sketching", title="Curve sketching",
         required=("function", "variable"), validate=_fx(), solve=ap.curve_sketch, verify=va.verify_curve,
         describe=_d(lambda p: f"Sketch f(x) = {to_text(p.function)}: domain, intercepts, asymptotes, "
                                "increasing/decreasing, extrema, concavity, inflection points"),
         generate=lambda r, d=2: ({"function": r.choice(["x^3 - 3x", "x/(x^2 + 1)", "x^2/(x - 1)", "x e^(-x)",
                                                         "(x^2 - 4)/(x^2 - 1)"]), "variable": "x"}, "Sketch the curve."),
         grade=None, answer_format="(compared in the write-up)", sections={"Mingarelli": ["5.4", "5.5"]},
         keywords=("sketch", "concave", "inflection", "asymptote", "increasing", "decreasing")),
    dict(name="improper_integral", topic="integrals", title="Improper integral",
         required=("integrand", "variable", "a", "b"), validate=_fx("integrand"), solve=ap.improper,
         verify=va.verify_improper,
         describe=_d(lambda p: f"Evaluate ∫ from {p.given['a']} to {p.given['b']} of {to_text(p.expr('integrand'))} dx "
                                "(or show it diverges)"),
         generate=lambda r, d=2: ({"integrand": r.choice(["1/x^2", "e^(-x)", "1/(1 + x^2)", "x e^(-x^2)", "1/x"]),
                                   "variable": "x", "a": "1", "b": "oo"}, "Evaluate the improper integral."),
         grade=lambda sol, text: (("diverg" in text.lower()) == (not sol.facts["converges"]), "Check convergence first.")
         if not sol.facts["converges"] or "diverg" in text.lower() else num_grade(sol, text),
         answer_text=lambda sol: str(sol.answer) if sol.facts["converges"] else "diverges",
         answer_format="a number, or 'diverges'", sections={"Mingarelli": ["7.7"]},
         keywords=("improper", "converge", "diverge", "infinite limit of integration")),
    dict(name="area_between_curves", topic="area-volume", title="Area between curves",
         required=("top_or_first", "second", "variable"),
         validate=lambda p: [require_only(p.expr(k), {require_variable(p)}, k) for k in ("top_or_first", "second")],
         solve=ap.area_between, verify=va.verify_area,
         describe=_d(lambda p: f"Find the area between y = {to_text(p.expr('top_or_first'))} and y = "
                                f"{to_text(p.expr('second'))}" + (f" from x = {p.given['a']} to {p.given['b']}"
                                                                   if "a" in p.given else "")),
         generate=lambda r, d=2: (dict(zip(("top_or_first", "second"), r.choice(
                                      [("x + 2", "x^2"), ("4 - x^2", "x^2 - 4"), ("2x", "x^2"), ("sqrt(x)", "x^2"),
                                       ("x", "x^3"), ("4 - x^2", "x + 2"), ("x^2 - 2", "x")])), variable="x"),
                                  "Find the area enclosed by the curves."),
         grade=num_grade, answer_format="an exact number", sections={"Mingarelli": ["7.8"]},
         keywords=("area between", "enclosed", "bounded by")),
    dict(name="volume_of_revolution", topic="area-volume", title="Volume of revolution",
         required=("outer", "variable", "a", "b"),
         validate=lambda p: require_only(p.expr("outer"), {require_variable(p)}, "outer"), solve=ap.volume,
         verify=va.verify_volume,
         describe=_d(lambda p: f"Rotate the region under y = {to_text(p.expr('outer'))}"
                                + (f" and above y = {to_text(p.expr('inner'))}" if "inner" in p.given else "")
                                + f" for {p.given['a']} ≤ x ≤ {p.given['b']} about {p.given.get('axis', 'x')}"
                                  "-axis".replace("x-axis", "the x-axis") + ". Find the volume"),
         generate=lambda r, d=2: ({"outer": r.choice(["sqrt(x)", "x^2", "2x", "e^x"]), "variable": "x", "a": "0",
                                   "b": str(r.randint(1, 3)), "axis": r.choice(["x", "y"])},
                                  "Find the volume of the solid of revolution."),
         grade=num_grade, answer_format="an exact number (with π)", sections={"Mingarelli": ["7.9"]},
         keywords=("volume", "revolution", "disk", "washer", "shell", "rotate")),
    dict(name="function_domain", topic="functions", title="Domain of a function",
         required=("function", "variable"), validate=_fx(), solve=ap.domain, verify=va.verify_domain,
         describe=_d(lambda p: f"Find the domain of f(x) = {to_text(p.function)}"),
         generate=lambda r, d=2: ({"function": r.choice(["sqrt(x - 2)/(x - 5)", "ln(4 - x^2)", "1/(x^2 - 9)",
                                                         "sqrt(9 - x^2)", "ln(x)/(x - 1)"]), "variable": "x"},
                                  "Find the domain."),
         grade=None, answer_format="interval notation", sections={"Mingarelli": ["1"]},
         keywords=("domain",)),
    dict(name="inverse_function", topic="functions", title="Inverse function",
         required=("function", "variable"), validate=_fx(), solve=ap.inverse_function, verify=va.verify_inverse,
         describe=_d(lambda p: f"Find the inverse of f(x) = {to_text(p.function)}"
                                + (f" for x ≥ {p.given['domain_from']}" if "domain_from" in p.given else "")),
         generate=lambda r, d=2: ({"function": r.choice(["2x + 3", "(x - 1)/(x + 2)", "e^(2x) + 1", "x^3 - 1"]),
                                   "variable": "x"}, "Find the inverse function."),
         grade=expr_grade, answer_format="an expression in x", sections={"Mingarelli": ["1", "3.5"]},
         keywords=("inverse function", "f^-1", "one-to-one")),
    dict(name="inverse_derivative", topic="derivatives", title="Derivative of an inverse function",
         required=("function", "variable", "at"), validate=_fx(), solve=ap.inverse_derivative,
         verify=va.verify_inverse_derivative,
         describe=_d(lambda p: f"Find (f⁻¹)′({p.given['at']}) for f(x) = {to_text(p.function)}"),
         generate=lambda r, d=2: ({"function": "x^3 + x + 1", "variable": "x", "at": r.choice(["1", "3", "11"])},
                                  "Find the derivative of the inverse."),
         grade=num_grade, answer_format="a number", sections={"Mingarelli": ["3.5"]},
         keywords=("derivative of the inverse",)),
    dict(name="linearization", topic="tangent-lines", title="Linear approximation",
         required=("function", "variable", "point", "estimate_at"), validate=_fx(), solve=ap.linearization,
         verify=va.verify_linearization,
         describe=_d(lambda p: f"Use the linearization of f(x) = {to_text(p.function)} at x = {p.given['point']} to "
                                f"estimate f({p.given['estimate_at']})"),
         generate=lambda r, d=2: (r.choice([{"function": "sqrt(x)", "point": "4", "estimate_at": "4.1"},
                                            {"function": "x^(1/3)", "point": "8", "estimate_at": "8.2"},
                                            {"function": "ln(x)", "point": "1", "estimate_at": "1.1"}]) | {"variable": "x"},
                                  "Estimate using a linear approximation."),
         grade=num_grade, answer_format="a number", sections={"Mingarelli": ["5.1"]},
         keywords=("linearization", "linear approximation", "estimate")),
    dict(name="higher_derivative", topic="derivatives", title="Higher derivatives",
         required=("function", "variable", "order"), validate=_fx(), solve=ap.higher_derivative,
         verify=va.verify_higher,
         describe=_d(lambda p: f"Find the derivative of order {p.given['order']} of f(x) = {to_text(p.function)}"),
         generate=lambda r, d=2: ({"function": r.choice(["x^4 - 3x^2", "x e^x", "sin(2x)", "ln(x)"]), "variable": "x",
                                   "order": 2}, "Find f″(x)."),
         grade=expr_grade, answer_format="an expression in x", sections={"Mingarelli": ["3.1"]},
         keywords=("second derivative", "f''", "higher derivative")),
]

for t in T:
    register(ProblemType(course="MATH1004", template="derivation", **t))
