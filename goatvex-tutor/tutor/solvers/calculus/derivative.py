"""Step-by-step differentiation: one rule applied to one d/dx[...] per step.

The working expression keeps *unevaluated* ``Derivative`` nodes. Each step
picks the outermost-leftmost unevaluated node and rewrites it with exactly one
rule (sum, constant multiple, power, chain, product, quotient, or a basic
function derivative). Arithmetic such as 5·(3x²) is kept visible (built with
``evaluate=False``) and only combined in a final, separately verified
"simplify" step — no hidden steps.

Supported: polynomials, rational powers/roots, sums, constant multiples,
products, quotients, chain rule through any nesting of
sin, cos, tan, sec, csc, cot, exp, ln, arcsin, arccos, arctan, aˣ.
Anything else raises :class:`UnsupportedProblem` so GoatVex says so plainly.
"""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp
from sympy.core.parameters import distribute

from tutor.errors import UnsupportedProblem
from tutor.parse.schema import Problem
from tutor.steps import ALGEBRA, DERIVATIVE_RULE, SETUP, Solution, Step
from tutor.text.unicode_math import to_text

# d/du f(u) for the basic functions, as functions of u
OUTER_DERIVATIVE = {
    sp.sin: lambda u: sp.cos(u),
    sp.cos: lambda u: -sp.sin(u),
    sp.tan: lambda u: sp.sec(u) ** 2,
    sp.sec: lambda u: sp.sec(u) * sp.tan(u),
    sp.csc: lambda u: -sp.csc(u) * sp.cot(u),
    sp.cot: lambda u: -sp.csc(u) ** 2,
    sp.exp: lambda u: sp.exp(u),
    sp.log: lambda u: 1 / u,
    sp.asin: lambda u: 1 / sp.sqrt(1 - u**2),
    sp.acos: lambda u: -1 / sp.sqrt(1 - u**2),
    sp.atan: lambda u: 1 / (1 + u**2),
}

FUNC_NAME = {
    sp.sin: "sin", sp.cos: "cos", sp.tan: "tan", sp.sec: "sec", sp.csc: "csc", sp.cot: "cot",
    sp.exp: "eˣ", sp.log: "ln", sp.asin: "arcsin", sp.acos: "arccos", sp.atan: "arctan",
}

# rule ids (also used by the verifier's independent rule-shape check)
CONSTANT = "constant"
IDENTITY = "identity"
SUM = "sum"
CONST_MULTIPLE = "constant_multiple"
POWER = "power"
POWER_CHAIN = "chain_power"
EXPONENTIAL_BASE = "exponential_base"
EXPONENTIAL_BASE_CHAIN = "chain_exponential_base"
BASIC_FUNCTION = "basic_function"
FUNCTION_CHAIN = "chain_function"
PRODUCT = "product"
QUOTIENT = "quotient"

RULE_TITLE = {
    CONSTANT: "Constant rule",
    IDENTITY: "Derivative of x",
    SUM: "Sum/difference rule",
    CONST_MULTIPLE: "Constant multiple rule",
    POWER: "Power rule",
    POWER_CHAIN: "Chain rule (power outside)",
    EXPONENTIAL_BASE: "Exponential rule",
    EXPONENTIAL_BASE_CHAIN: "Chain rule (exponential outside)",
    BASIC_FUNCTION: "Basic derivative",
    FUNCTION_CHAIN: "Chain rule",
    PRODUCT: "Product rule",
    QUOTIENT: "Quotient rule",
}


@dataclass
class RuleApplication:
    rule: str
    replacement: sp.Expr
    justification: str
    details: dict


def _D(e: sp.Expr, x: sp.Symbol) -> sp.Derivative:
    return sp.Derivative(e, x, evaluate=False)


def _mul(*args) -> sp.Expr:
    args = [a for a in args if a != 1]
    if not args:
        return sp.Integer(1)
    if len(args) == 1:
        return args[0]
    return sp.Mul(*args, evaluate=False)


def _neg_power_factors(expr: sp.Mul) -> tuple[list, list]:
    """Split a product into numerator factors and denominator bases (numeric negative exponents)."""
    num, den = [], []
    for f in expr.args:
        b, e = f.as_base_exp()
        if e.is_number and e.is_negative:
            den.append(b ** (-e))
        else:
            num.append(f)
    return num, den


def apply_rule(node: sp.Derivative) -> RuleApplication:
    g = node.expr
    x = node.variables[0]
    t = to_text

    if not g.has(x):
        return RuleApplication(CONSTANT, sp.Integer(0), f"{t(g)} does not depend on {x}, so its derivative is 0.", {})
    if g == x:
        return RuleApplication(IDENTITY, sp.Integer(1), f"The derivative of {x} with respect to {x} is 1.", {})

    if isinstance(g, sp.Add):
        terms = list(g.as_ordered_terms())
        rep = sp.Add(*[_D(term, x) for term in terms], evaluate=False)
        return RuleApplication(SUM, rep, "The derivative of a sum is the sum of the derivatives, term by term.",
                               {"terms": terms})

    if isinstance(g, sp.Mul):
        const, rest = g.as_independent(x, as_Add=False)
        if const != 1:
            rep = _mul(const, _D(rest, x))
            return RuleApplication(
                CONST_MULTIPLE, rep, f"The constant {t(const)} can be pulled out in front of the derivative.",
                {"constant": const, "rest": rest})
        num, den = _neg_power_factors(g)
        if den:
            u = sp.Mul(*num)
            v = sp.Mul(*den)
            rep = sp.Mul(
                sp.Add(_mul(v, _D(u, x)), sp.Mul(-1, _mul(u, _D(v, x)), evaluate=False), evaluate=False),
                sp.Pow(sp.Pow(v, 2, evaluate=False), -1, evaluate=False),
                evaluate=False,
            )
            return RuleApplication(
                QUOTIENT, rep,
                f"Quotient rule with top u = {t(u)} and bottom v = {t(v)}: (u/v)′ = (v·u′ − u·v′)/v².",
                {"u": u, "v": v})
        factors = list(g.as_ordered_factors())  # u = the first factor the student sees
        u = factors[0]
        v = sp.Mul(*factors[1:])
        rep = sp.Add(_mul(_D(u, x), v), _mul(u, _D(v, x)), evaluate=False)
        return RuleApplication(
            PRODUCT, rep, f"Product rule with u = {t(u)} and v = {t(v)}: (uv)′ = u′v + uv′.", {"u": u, "v": v})

    if isinstance(g, sp.Pow):
        b, e = g.args
        if b.has(x) and not e.has(x):
            new_e = e - 1
            if b == x:
                rep = _mul(e, sp.Pow(x, new_e))
                return RuleApplication(
                    POWER, rep, f"Power rule: bring down the exponent {t(e)} and lower the power by 1.",
                    {"exponent": e, "new_exponent": new_e})
            rep = _mul(e, sp.Pow(b, new_e), _D(b, x))
            return RuleApplication(
                POWER_CHAIN, rep,
                f"Chain rule: the outside is (inside)^{t(e)}, the inside is u = {t(b)}. "
                f"Differentiate the outside (power rule), keep the inside, then multiply by du/d{x}.",
                {"outer": "power", "exponent": e, "new_exponent": new_e, "inner": b})
        if not b.has(x) and e.has(x):
            if e == x:
                rep = _mul(sp.Pow(b, x), sp.log(b))
                return RuleApplication(
                    EXPONENTIAL_BASE, rep, f"d/d{x}[aˣ] = aˣ·ln(a) with a = {t(b)}.", {"base": b})
            rep = _mul(sp.Pow(b, e), sp.log(b), _D(e, x))
            return RuleApplication(
                EXPONENTIAL_BASE_CHAIN, rep,
                f"Chain rule with outside aᵘ (a = {t(b)}) and inside u = {t(e)}: aᵘ·ln(a)·du/d{x}.",
                {"base": b, "inner": e})
        raise UnsupportedProblem(
            f"{t(g)} has the variable in both the base and the exponent; that needs logarithmic "
            "differentiation, which the verified solver does not support yet.")

    if isinstance(g, sp.Function) and g.func in OUTER_DERIVATIVE and len(g.args) == 1:
        u = g.args[0]
        outer = OUTER_DERIVATIVE[g.func](u)
        name = FUNC_NAME[g.func]
        if u == x:
            return RuleApplication(
                BASIC_FUNCTION, outer, f"Standard derivative: d/d{x}[{t(g)}] = {t(outer)}.", {"function": name})
        rep = _mul(outer, _D(u, x))
        return RuleApplication(
            FUNCTION_CHAIN, rep,
            f"Chain rule: the outside is {name}(inside), the inside is u = {t(u)}. "
            f"Differentiate the outside, keep the inside, then multiply by du/d{x}.",
            {"outer": name, "inner": u, "outer_derivative": outer})

    raise UnsupportedProblem(f"the verified solver does not know how to differentiate {t(g)} yet")


def first_derivative_node(expr: sp.Basic) -> sp.Derivative | None:
    for node in sp.preorder_traversal(expr):
        if isinstance(node, sp.Derivative):
            return node
    return None


def derivative_steps(f: sp.Expr, x: sp.Symbol, max_steps: int = 200) -> tuple[list[Step], sp.Expr]:
    start = _D(f, x)
    steps = [Step(
        id="s0", kind=SETUP, before=f, operation="Set up", after=start,
        justification=f"We want the derivative of f({x}) = {to_text(f)}.", data={"variable": x})]
    cur: sp.Expr = start
    k = 1
    while (node := first_derivative_node(cur)) is not None:
        if k > max_steps:
            raise UnsupportedProblem("differentiation needed too many steps; refusing to guess")
        app = apply_rule(node)
        with sp.evaluate(False):
            after = cur.xreplace({node: app.replacement})
        steps.append(Step(
            id=f"s{k}", kind=DERIVATIVE_RULE, before=cur, operation=RULE_TITLE[app.rule], after=after,
            justification=app.justification,
            data={"rule": app.rule, "target": node, "replacement": app.replacement, **app.details}))
        cur = after
        k += 1

    # Combine arithmetic that was deliberately left visible. distribute(False)
    # keeps 2(x + 2) as written instead of SymPy's automatic 2x + 4.
    with distribute(False):
        simplified = _rebuild(cur)
    if simplified != cur:
        steps.append(Step(
            id=f"s{k}", kind=ALGEBRA, before=cur, operation="Simplify", after=simplified,
            justification="Multiply out the constants and combine like terms.", data={"how": "evaluate"}))
        k += 1
    tidy, how, why = _tidy_answer(simplified)
    if tidy is not None:
        steps.append(Step(
            id=f"s{k}", kind=ALGEBRA, before=simplified, operation=how, after=tidy,
            justification=why, data={"how": how}))
        simplified = tidy
    return steps, simplified


def _tidy_answer(e: sp.Expr) -> tuple[sp.Expr | None, str, str]:
    """Optionally one more tidy-up step for readability.

    Student preference: easy to read, but NOT fully factorized. So we only
    expand/collect the numerator of a quotient (cancelling a common factor if
    one appears); we never factor the answer.
    """
    if e.is_Add:  # separate terms stay separate (e.g. 3√x/2 + 4/x²)
        return None, "", ""
    num, den = sp.fraction(sp.together(e))
    if den != 1 and den.has(*e.free_symbols):
        candidate = sp.expand(num) / den
        if candidate != e and sp.count_ops(candidate) <= sp.count_ops(e):
            if sp.fraction(candidate)[1] != sp.fraction(e)[1]:
                return (candidate, "Expand the numerator and cancel",
                        "Multiply out the top, collect like terms, and cancel the factor common to top and bottom.")
            return candidate, "Expand the numerator", "Multiply out the top and collect like terms."
    return None, "", ""


def _rebuild(e: sp.Basic) -> sp.Basic:
    """Re-evaluate an expression built with evaluate=False (bottom-up)."""
    if not e.args:
        return e
    return e.func(*[_rebuild(a) for a in e.args])


def solve(problem: Problem) -> Solution:
    x = problem.variable
    f = problem.function
    steps, answer = derivative_steps(f, x)
    return Solution(
        problem=problem, steps=steps, answer=answer, answer_label=f"f′({x})",
        facts={"function": f, "variable": x}, notes=[])
