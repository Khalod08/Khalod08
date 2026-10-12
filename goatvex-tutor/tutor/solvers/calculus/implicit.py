"""Implicit differentiation, tangent lines, logarithmic differentiation, related rates.

All of them differentiate both sides of an equation with the same verified
one-rule-per-step engine (``derivative.rule_steps``), treating y as y(x)
(or x, y, V, r … as functions of t for related rates), and then solve for
the derivative with equation steps whose solution sets are checked.
"""

from __future__ import annotations

import sympy as sp

from tutor.errors import ProblemFormatError, UnsupportedProblem
from tutor.parse.schema import Problem, parse_math
from tutor.solvers.builder import A, Builder, M
from tutor.solvers.calculus.derivative import combine, rule_steps
from tutor.steps import ALGEBRA, EQUATION, FACT, SETUP, Solution, Step
from tutor.text.unicode_math import to_text


def parse_equation(text: str, names: list[str]) -> tuple[sp.Expr, sp.Expr]:
    if "=" not in text:
        raise ProblemFormatError("write the equation with an '=' sign, e.g. x^2 + y^2 = 25")
    lhs, rhs = text.split("=", 1)
    return parse_math(lhs, names), parse_math(rhs, names)


def _d_both_sides(B: Builder, eq: sp.Equality, var: sp.Symbol) -> sp.Equality:
    d_eq = sp.Eq(sp.Derivative(eq.lhs, var, evaluate=False), sp.Derivative(eq.rhs, var, evaluate=False), evaluate=False)
    B.add(eq, f"Differentiate both sides with respect to {var}", d_eq,
          "Apply d/d" + str(var) + " to each side; every dependent variable is a function of " + str(var)
          + ", so the chain rule gives its derivative.", kind=FACT, chain=True, rule="d_both_sides")
    steps, cur = rule_steps(d_eq, var, k=B.k)
    for s_ in steps:
        s_.data["chain"] = True
    B.steps += steps
    B.k += len(steps)
    simplified = combine(cur)
    if simplified != cur:
        B.add(cur, "Simplify", simplified, "Multiply out the constants.", chain=True)
    return simplified


def _solve_for(B: Builder, eq: sp.Equality, D: sp.Expr) -> sp.Expr:
    """Collect D terms, factor D out, divide. Returns the solution for D."""
    expr = sp.expand(eq.lhs - eq.rhs)
    with_d = sp.Add(*[t for t in sp.Add.make_args(expr) if t.has(D)])
    without = sp.Add(*[t for t in sp.Add.make_args(expr) if not t.has(D)])
    if with_d == 0:
        raise UnsupportedProblem("the derivative cancelled out, so it can't be solved for")
    moved = sp.Eq(with_d, -without, evaluate=False)
    B.add(eq, f"Move the {to_text(D)} terms to one side", moved,
          f"Keep every term containing {to_text(D)} on the left; move the rest to the right.",
          kind=EQUATION, chain=True, unknowns=[D])
    coef = sp.factor(sp.expand(with_d / D))
    factored = sp.Eq(M(D, coef), -without, evaluate=False)
    B.add(moved, f"Factor out {to_text(D)}", factored, f"Take {to_text(D)} out as a common factor.",
          kind=EQUATION, chain=True, unknowns=[D])
    sol = sp.simplify(-without / coef)
    B.add(factored, f"Divide by {to_text(coef)}", sp.Eq(D, sol), "Isolate the derivative.",
          kind=EQUATION, chain=True, unknowns=[D])
    return sol


def implicit(p: Problem) -> Solution:
    xname = p.given.get("variable", "x")
    yname = p.given.get("dependent", "y")
    x = sp.Symbol(xname, real=True)
    yf = sp.Function(yname)(x)
    ysym = sp.Symbol(yname, real=True)
    lhs, rhs = parse_equation(p.given["equation"], [xname, yname])
    eq = sp.Eq(lhs.xreplace({ysym: yf}), rhs.xreplace({ysym: yf}), evaluate=False)
    B = Builder()
    B.steps.append(Step(id="s0", kind=SETUP, before=None, operation="Treat y as a function of x", after=eq,
                        justification=f"{yname} depends on {xname}, so we write {yname} = {yname}({xname}).",
                        data={"chain": False}))
    deq = _d_both_sides(B, eq, x)
    D = sp.Derivative(yf, x)
    dydx = _solve_for(B, deq, D)
    facts = {"x": x, "y": yf, "equation": eq, "lhs": lhs, "rhs": rhs, "ysym": ysym}
    answer, label, notes = dydx, f"d{yname}/d{xname}", []
    if "point" in p.given:
        x0, y0 = (parse_math(v) for v in p.given["point"])
        facts["point"] = (x0, y0)
        with sp.evaluate(False):
            shown = dydx.xreplace({yf: y0}).xreplace({x: x0})
        slope = sp.simplify(dydx.subs(yf, y0).subs(x, x0))
        B.add(shown, f"Slope at ({to_text(x0)}, {to_text(y0)})", slope, f"Substitute {xname} = {to_text(x0)}, "
              f"{yname} = {to_text(y0)}.")
        facts["slope"] = slope
        if p.given.get("tangent_line", True):
            line = _line(B, x0, y0, slope, x, ysym)
            facts["line"] = line
            answer, label = line, "tangent line"
            notes.append(f"dy/dx = {to_text(dydx)}; slope at the point = {to_text(slope)}.")
    return Solution(problem=p, steps=B.steps, answer=answer, answer_label=label, facts=facts, notes=notes)


def _line(B: Builder, x0, y0, m, x, ysym, normal: bool = False):
    if m.is_infinite or m == sp.zoo:
        line = sp.Eq(x, x0)
        B.add(None, "Vertical tangent", line, "The slope is undefined, so the line is vertical.", kind=FACT)
        return line
    ps = sp.Eq(A(ysym, -y0), M(m, A(x, -x0)), evaluate=False)
    B.add(None, "Point-slope form", ps, f"y − y₀ = m(x − x₀) with m = {to_text(m)} through ({to_text(x0)}, "
          f"{to_text(y0)}).", kind=FACT)
    line = sp.Eq(ysym, sp.expand(m * (x - x0) + y0))
    B.add(ps, "Solve for y", line, "Expand and move y₀ over.", kind=EQUATION, chain=True, unknowns=[ysym])
    return line


def tangent_line(p: Problem) -> Solution:
    from tutor.solvers.calculus.derivative import derivative_steps

    x = sp.Symbol(p.given["variable"], real=True)
    ysym = sp.Symbol("y", real=True)
    f = p.expr("function")
    a = parse_math(p.given["point"])
    B = Builder()
    with sp.evaluate(False):
        shown = f.xreplace({x: a})
    fa = B.add(shown, f"f({to_text(a)})", sp.simplify(f.subs(x, a)), "The point on the curve.")
    dsteps, fp = derivative_steps(f, x)
    dsteps[0].data["chain"] = False
    for s_ in dsteps:
        s_.id = f"s{B.k}"
        B.k += 1
    B.steps += dsteps
    with sp.evaluate(False):
        shown_p = fp.xreplace({x: a})
    m = B.add(shown_p, f"f′({to_text(a)})", sp.simplify(fp.subs(x, a)), "The slope of the tangent line.")
    normal = bool(p.given.get("normal", False))
    if normal:
        if m == 0:
            line = sp.Eq(x, a)
            B.add(None, "Normal line", line, "The tangent is horizontal, so the normal is vertical.", kind=FACT)
            return Solution(problem=p, steps=B.steps, answer=line, answer_label="normal line",
                            facts={"x": x, "f": f, "a": a, "fa": fa, "slope": m, "normal": True, "line": line}, notes=[])
        m = B.add(sp.Mul(-1, sp.Pow(m, -1, evaluate=False), evaluate=False), "Normal slope = −1/m", -1 / m,
                  "The normal line is perpendicular to the tangent.")
    line = _line(B, a, fa, m, x, ysym)
    return Solution(problem=p, steps=B.steps, answer=line, answer_label="normal line" if normal else "tangent line",
                    facts={"x": x, "f": f, "a": a, "fa": fa, "slope": m, "normal": normal, "line": line,
                           "fprime": fp}, notes=[f"f′({x}) = {to_text(fp)}."])


def log_diff(p: Problem) -> Solution:
    x = sp.Symbol(p.given["variable"], real=True)
    f = p.expr("function")
    yf = sp.Function("y")(x)
    B = Builder()
    eq = sp.Eq(yf, f, evaluate=False)
    B.steps.append(Step(id="s0", kind=SETUP, before=None, operation="Write y = f(x)", after=eq,
                        justification="Logarithmic differentiation: take ln of both sides first.", data={"chain": False}))
    lo = positive_region(f, x)
    ln_eq = sp.Eq(sp.log(yf), sp.log(f), evaluate=False)
    B.add(eq, "Take ln of both sides", ln_eq, f"Valid where every factor is positive: here {x} > {to_text(lo)}.",
          kind=FACT, chain=True, rule="take_ln")
    expanded = sp.Eq(sp.log(yf), sp.expand_log(sp.log(f), force=True), evaluate=False)
    B.add(ln_eq, "Use log laws", expanded, "ln(ab) = ln a + ln b, ln(a/b) = ln a − ln b, ln(aᵏ) = k·ln a "
          f"(all factors are positive for {x} > {to_text(lo)}).", kind=ALGEBRA, chain=True, domain=(lo, sp.oo))
    deq = _d_both_sides(B, expanded, x)
    D = sp.Derivative(yf, x)
    rhs_ = sp.simplify(sp.solve(sp.Eq(deq.lhs, deq.rhs), D)[0])
    mult = sp.Eq(D, M(yf, sp.expand(rhs_ / yf)), evaluate=False)
    B.add(deq, "Multiply both sides by y", mult, "Isolate dy/dx.", kind=EQUATION, chain=True, unknowns=[D])
    final = sp.Eq(D, M(f, sp.expand(rhs_ / yf)), evaluate=False)
    B.add(mult, "Replace y by f(x)", final, f"y = {to_text(f)}.", kind=FACT, chain=True, rule="replace_y")
    ans = f * sp.expand(rhs_ / yf)
    return Solution(problem=p, steps=B.steps, answer=ans, answer_label="dy/dx", facts={"x": x, "f": f, "domain": (lo, sp.oo)},
                    notes=[f"Logarithmic differentiation needs every factor positive; here that means {x} > {to_text(lo)}, "
                           "and the answer is verified there."])


def positive_region(f, x) -> sp.Expr:
    """Smallest a such that every base (factor) of f is positive for all x > a."""
    bases = []
    for fac in sp.Mul.make_args(f):
        b = fac.base if fac.is_Pow else fac
        if b.has(x):
            bases.append(b)
            if b.is_Pow:
                bases.append(b.base)
    lo = sp.Integer(0)
    for b in bases:
        region = sp.solve_univariate_inequality(b > 0, x, relational=False, domain=sp.S.Reals)
        last = region.args[-1] if isinstance(region, sp.Union) else region
        if not (isinstance(last, sp.Interval) and last.end == sp.oo):
            raise UnsupportedProblem(f"{to_text(b)} is not positive for large {x}; logarithmic differentiation needs "
                                     "positive factors")
        lo = sp.Max(lo, last.start)
    return sp.simplify(lo)


def related_rates(p: Problem) -> Solution:
    g = p.given
    t = sp.Symbol("t", real=True)
    names = list(g["variables"])
    funcs = {n: sp.Function(n)(t) for n in names}
    syms = {n: sp.Symbol(n, real=True) for n in names}
    lhs, rhs = parse_equation(g["relation"], names)
    to_f = {syms[n]: funcs[n] for n in names}
    eq = sp.Eq(lhs.xreplace(to_f), rhs.xreplace(to_f), evaluate=False)
    B = Builder()
    B.steps.append(Step(id="s0", kind=SETUP, before=None, operation="Relation between the quantities", after=eq,
                        justification="Every quantity changes with time t.", data={"chain": False}))
    deq = _d_both_sides(B, eq, t)
    known = dict(g["known"])
    values: dict = {}
    rates: dict = {}
    for k_, v in known.items():
        if "/dt" in k_:
            rates[k_.split("/")[0][1:]] = parse_math(v)
        else:
            values[k_] = parse_math(v)
    find = g["find"]
    target = find.split("/")[0][1:] if "/dt" in find else find
    if target not in names:
        raise ProblemFormatError(f"'find' must be d<variable>/dt for one of {names}")
    # values of quantities not given: from the relation itself
    missing = [n for n in names if n not in values and not (n == target and "/dt" not in find)]
    positive = bool(g.get("assume_positive", True))
    for n in missing:
        rel = sp.Eq(lhs.xreplace({syms[k]: v for k, v in values.items()}), rhs.xreplace({syms[k]: v for k, v in values.items()}))
        sols = [s for s in sp.solve(rel, syms[n]) if s.is_real]
        if positive:
            sols = [s for s in sols if s.is_positive]
        if len(sols) != 1:
            raise UnsupportedProblem(f"can't pin down the value of {n} at that moment (solutions: {sols})")
        B.add(rel, f"Find {n} at that moment", sp.Eq(syms[n], sols[0]),
              f"Use the original relation{' (quantities are positive)' if positive else ''}.", kind=EQUATION,
              chain=False, unknowns=[syms[n]], positive=positive)
        values[n] = sols[0]
    D = {n: sp.Derivative(funcs[n], t) for n in names}
    subs_map = {D[n]: r for n, r in rates.items()}
    unknown_rate = sp.Symbol(f"d{target}/dt", real=True)
    subs_map[D[target]] = unknown_rate
    plugged_l = deq.lhs.xreplace(subs_map).xreplace({funcs[n]: v for n, v in values.items()})
    plugged_r = deq.rhs.xreplace(subs_map).xreplace({funcs[n]: v for n, v in values.items()})
    plugged = sp.Eq(plugged_l, plugged_r, evaluate=False)
    B.add(deq, "Substitute the values at that moment", plugged,
          "Put in " + ", ".join([f"{n} = {to_text(v)}" for n, v in values.items()]
                                + [f"d{n}/dt = {to_text(r)}" for n, r in rates.items()]) + ".",
          kind=FACT, chain=False, rule="plug_in", subs=subs_map, unknown=unknown_rate, from_eq=deq,
          funcs=funcs)
    sol = sp.solve(sp.Eq(plugged_l, plugged_r), unknown_rate)
    if len(sol) != 1:
        raise UnsupportedProblem("the rate could not be isolated")
    ans = sp.nsimplify(sol[0])
    B.add(plugged, f"Solve for d{target}/dt", sp.Eq(unknown_rate, ans), "A linear equation in the unknown rate.",
          kind=EQUATION, chain=True, unknowns=[unknown_rate])
    units = g.get("units", "")
    return Solution(problem=p, steps=B.steps, answer=ans, answer_label=f"d{target}/dt",
                    facts={"t": t, "names": names, "lhs": lhs, "rhs": rhs, "values": values, "rates": rates,
                           "target": target, "syms": syms},
                    notes=[f"d{target}/dt = {to_text(ans)}{' ' + units if units else ''}"
                           f"{' (negative: decreasing)' if ans.is_negative else ''}."])
