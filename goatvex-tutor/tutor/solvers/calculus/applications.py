"""Applications of derivatives and integrals (Mingarelli Ch. 5, 7.7–7.9; Ch. 1).

optimization, curve sketching, improper integrals, area between curves,
volumes of revolution, domain, inverse functions, derivative of an inverse,
linearization, higher derivatives.

Every derivative/antiderivative/limit inside these is produced by the
verified step engines; the new reasoning (critical points, sign charts,
which curve is on top …) is recorded as facts the verifier re-checks
independently (SymPy solveset/limits and dense numerical sampling).
"""

from __future__ import annotations

import sympy as sp

from tutor.errors import ProblemFormatError, UnsupportedProblem
from tutor.mathfn import to_real_roots
from tutor.parse.schema import Problem, parse_math
from tutor.solvers.builder import A, Builder, M, frac
from tutor.solvers.calculus.derivative import derivative_steps
from tutor.solvers.calculus.integral import antiderivative_steps
from tutor.steps import ALGEBRA, EQUATION, FACT, SETUP, Solution, Step
from tutor.text.unicode_math import to_text


def _at(f, x, v):
    with sp.evaluate(False):
        return f.xreplace({x: v})


def _block(B: Builder, steps: list[Step]):
    """Append steps from an engine as their own (renumbered) block."""
    if not steps:
        return
    steps[0].data["chain"] = False
    for s in steps:
        s.id = f"s{B.k}"
        B.k += 1
    B.steps += steps


def _derivative(B: Builder, f, x):
    steps, fp = derivative_steps(f, x)
    _block(B, steps)
    return fp


def _antiderivative(B: Builder, f, x):
    steps, F = antiderivative_steps(f, x)
    if steps:
        steps.insert(0, Step(id="", kind=SETUP, before=f, operation="Antiderivative", after=sp.Integral(f, x),
                             justification="Find an antiderivative first.", data={"chain": False}))
    _block(B, steps)
    return F


def real_solutions(eq, x, interval=sp.S.Reals) -> list:
    sol = sp.solveset(eq, x, domain=interval)
    if isinstance(sol, sp.FiniteSet):
        return sorted(sol, key=lambda v: float(v))
    if sol == sp.EmptySet:
        return []
    raise UnsupportedProblem(f"can't list the solutions of {to_text(eq)} exactly ({sol})")


def interval_of(p: Problem):
    a = parse_math(p.given.get("a", "-oo"))
    b = parse_math(p.given.get("b", "oo"))
    closed = p.given.get("closed", not (a.is_infinite or b.is_infinite))
    if closed and not (a.is_infinite or b.is_infinite):
        return sp.Interval(a, b), a, b, True
    return sp.Interval.open(a, b), a, b, False


# ---------------------------------------------------------------- optimization
def optimization(p: Problem) -> Solution:
    x = sp.Symbol(p.given["variable"], real=True)
    f = p.expr("function")
    I, a, b, closed = interval_of(p)
    goal = p.given.get("goal", "both")
    B = Builder()
    B.steps.append(Step(id="s0", kind=SETUP, before=None, operation="Objective", after=f,
                        justification=f"Find the absolute {'maximum and minimum' if goal == 'both' else goal} of "
                                      f"f({x}) = {to_text(f)} on {to_text(I)}.", data={"chain": False}))
    fp = _derivative(B, f, x)
    crit = real_solutions(sp.Eq(fp, 0), x, I)
    B.add(sp.Eq(fp, 0), "Critical points: f′(x) = 0", [sp.Eq(x, c) for c in crit] if crit else "none",
          "Solve f′(x) = 0 inside the interval." if crit else "f′(x) is never 0 inside the interval.",
          kind=FACT, rule="critical")
    undefined = [c for c in _singular(fp, x, I) if c not in crit and _defined(f, x, c)]
    if undefined:
        B.add(None, "Where f′ is undefined", [sp.Eq(x, c) for c in undefined], "These are critical points too.",
              kind=FACT, rule="critical_undefined")
    cands = sorted(set(crit) | set(undefined), key=lambda v: float(v))
    facts = {"x": x, "f": f, "fprime": fp, "interval": I, "critical": cands, "closed": closed, "goal": goal}
    if closed:
        pts = sorted(set(cands) | {a, b}, key=lambda v: float(v))
        vals = {}
        for c in pts:
            vals[c] = B.add(_at(f, x, c), f"f({to_text(c)})", sp.simplify(f.subs(x, c)),
                            "Endpoint." if c in (a, b) else "Critical point.")
        hi = max(pts, key=lambda c: float(vals[c]))
        lo = min(pts, key=lambda c: float(vals[c]))
        B.add(None, "Compare the values", f"max {to_text(vals[hi])} at x = {to_text(hi)}; min {to_text(vals[lo])} "
              f"at x = {to_text(lo)}", "Closed interval method: the largest value is the absolute maximum and the "
              "smallest is the absolute minimum.", kind=FACT, rule="compare")
        facts.update(values=vals, argmax=hi, argmin=lo, max=vals[hi], min=vals[lo])
    else:
        if len(cands) != 1:
            raise UnsupportedProblem("on an open interval the verified solver handles exactly one critical point "
                                     "(second-derivative test + limits at the ends)")
        c = cands[0]
        fpp = sp.simplify(sp.diff(fp, x))
        B.add(sp.Derivative(fp, x, evaluate=False), "Second derivative", fpp, "Differentiate f′ once more.")
        s2 = B.add(_at(fpp, x, c), f"f″({to_text(c)})", sp.simplify(fpp.subs(x, c)), "Second-derivative test.")
        if s2 == 0:
            raise UnsupportedProblem("the second-derivative test is inconclusive here")
        kind = "minimum" if s2 > 0 else "maximum"
        val = B.add(_at(f, x, c), f"f({to_text(c)})", sp.simplify(f.subs(x, c)), f"The value at the critical point.")
        B.add(None, "Conclusion", f"absolute {kind} {to_text(val)} at x = {to_text(c)}",
              f"f″ {'> 0' if s2 > 0 else '< 0'}, so x = {to_text(c)} is a local {kind}; it is the only critical point "
              f"on the interval, so it is the absolute {kind}.", kind=FACT, rule="second_derivative")
        facts.update(kind=kind, point=c, value=val, fpp=fpp)
    answer = (facts.get("max"), facts.get("min")) if closed else facts["value"]
    return Solution(problem=p, steps=B.steps, answer=answer,
                    answer_label="absolute max, min" if closed else f"absolute {facts['kind']}", facts=facts, notes=[])


def _singular(e, x, I) -> list:
    try:
        s = sp.singularities(e, x, I)
        return sorted(s, key=lambda v: float(v)) if isinstance(s, sp.FiniteSet) else []
    except Exception:
        return []


def _defined(f, x, c) -> bool:
    v = f.subs(x, c)
    return v.is_finite is True and v.is_real is not False


# ---------------------------------------------------------------- curve sketching
def curve_sketch(p: Problem) -> Solution:
    x = sp.Symbol(p.given["variable"], real=True)
    f = p.expr("function")
    B = Builder()
    B.steps.append(Step(id="s0", kind=SETUP, before=None, operation="Function", after=f,
                        justification="Domain, intercepts, asymptotes, increasing/decreasing, extrema, concavity.",
                        data={"chain": False}))
    dom = sp.calculus.util.continuous_domain(f, x, sp.S.Reals)
    B.add(None, "Domain", dom, "Exclude zeros of denominators, negative square-root arguments, nonpositive log "
          "arguments.", kind=FACT, rule="domain")
    y0 = sp.simplify(f.subs(x, 0)) if dom.contains(0) == sp.true else None
    xints = real_solutions(sp.Eq(f, 0), x, dom)
    B.add(None, "Intercepts", {"y-intercept": y0 if y0 is not None else "none", "x-intercepts": xints or "none"},
          "Set x = 0 for the y-intercept; solve f(x) = 0 for x-intercepts.", kind=FACT, rule="intercepts")
    vas = [c for c in _singular(f, x, sp.S.Reals) if sp.limit(f, x, c, "+").is_infinite or
           sp.limit(f, x, c, "-").is_infinite]
    hz = {d: sp.limit(f, x, d) for d in (sp.oo, -sp.oo)}
    has = sorted({v for v in hz.values() if v.is_finite}, key=float)
    slant = None
    num, den = sp.fraction(sp.together(f))
    if f.is_rational_function(x) and sp.degree(num, x) == sp.degree(den, x) + 1:
        q, r = sp.div(sp.Poly(num, x), sp.Poly(den, x))
        slant = q.as_expr()
    B.add(None, "Asymptotes", {"vertical": [sp.Eq(x, c) for c in vas] or "none",
                               "horizontal": [sp.Eq(sp.Symbol("y"), v) for v in has] or "none",
                               "slant": sp.Eq(sp.Symbol("y"), slant) if slant is not None else "none"},
          "Vertical: where f blows up. Horizontal: limits at ±∞. Slant: when the top's degree is one more than the "
          "bottom's.", kind=FACT, rule="asymptotes")
    fp = _derivative(B, f, x)
    fp = sp.simplify(fp)
    crit = real_solutions(sp.Eq(fp, 0), x, dom)
    breaks = sorted(set(crit) | set(vas) | set(_singular(fp, x, sp.S.Reals)), key=float)
    chart1 = _sign_chart(fp, x, breaks, dom)
    B.add(None, "Increasing / decreasing", chart1,
          "Test the sign of f′ on each interval between critical points (and vertical asymptotes).",
          kind=FACT, rule="sign_fprime")
    extrema = []
    for c in crit:
        left = next((s for (lo, hi, s) in chart1 if hi == c), None)
        right = next((s for (lo, hi, s) in chart1 if lo == c), None)
        if left and right and left != right:
            extrema.append(("local max" if left == "+" else "local min", c, sp.simplify(f.subs(x, c))))
    B.add(None, "Local extrema", [f"{k} at x = {to_text(c)}, f = {to_text(v)}" for k, c, v in extrema] or "none",
          "Where f′ changes sign (first derivative test).", kind=FACT, rule="extrema")
    fpp = sp.simplify(sp.diff(fp, x))
    B.add(sp.Derivative(fp, x, evaluate=False), "Second derivative", fpp, "Differentiate f′.")
    infl_c = real_solutions(sp.Eq(fpp, 0), x, dom)
    breaks2 = sorted(set(infl_c) | set(vas) | set(_singular(fpp, x, sp.S.Reals)), key=float)
    chart2 = _sign_chart(fpp, x, breaks2, dom)
    B.add(None, "Concavity", chart2, "Test the sign of f″: + means concave up, − concave down.", kind=FACT,
          rule="sign_fpp")
    infl = []
    for c in infl_c:
        left = next((s for (lo, hi, s) in chart2 if hi == c), None)
        right = next((s for (lo, hi, s) in chart2 if lo == c), None)
        if left and right and left != right:
            infl.append((c, sp.simplify(f.subs(x, c))))
    B.add(None, "Inflection points", [f"({to_text(c)}, {to_text(v)})" for c, v in infl] or "none",
          "Where the concavity changes.", kind=FACT, rule="inflection")
    facts = {"x": x, "f": f, "domain": dom, "y_int": y0, "x_ints": xints, "vas": vas, "has": has, "slant": slant,
             "fprime": fp, "fpp": fpp, "chart1": chart1, "chart2": chart2, "extrema": extrema, "inflections": infl}
    return Solution(problem=p, steps=B.steps, answer=facts["extrema"], answer_label="key features", facts=facts,
                    notes=[])


def _sign_chart(g, x, breaks, dom):
    """[(left, right, '+'/'−'), …] over the domain, split at the break points."""
    edges = [-sp.oo] + list(breaks) + [sp.oo]
    chart = []
    for lo, hi in zip(edges, edges[1:]):
        if lo == hi:
            continue
        if lo == -sp.oo and hi == sp.oo:
            t = sp.Integer(0)
        elif lo == -sp.oo:
            t = sp.floor(hi) - 1
        elif hi == sp.oo:
            t = sp.ceiling(lo) + 1
        else:
            t = (lo + hi) / 2
        if dom.contains(t) != sp.true:
            continue
        v = sp.N(g.subs(x, t), 30)
        if not v.is_real or v == 0:
            continue
        chart.append((lo, hi, "+" if v > 0 else "−"))
    return chart


# ---------------------------------------------------------------- improper integrals
def improper(p: Problem) -> Solution:
    from tutor.solvers.calculus.limits import LimitSolver

    x = sp.Symbol(p.given["variable"], real=True)
    f = p.expr("integrand")
    a, b = parse_math(p.given["a"]), parse_math(p.given["b"])
    t = sp.Symbol("t", real=True)
    B = Builder()
    if b == sp.oo and not a.is_infinite:
        lim_pt, lo, hi, side = sp.oo, a, t, "-"
        why = "The upper limit is ∞: replace it by t and let t → ∞."
    elif a == -sp.oo and not b.is_infinite:
        lim_pt, lo, hi, side = -sp.oo, t, b, "+"
        why = "The lower limit is −∞: replace it by t and let t → −∞."
    else:
        bad = [c for c in _singular(f, x, sp.Interval(a, b))]
        if len(bad) != 1 or bad[0] not in (a, b):
            raise UnsupportedProblem("the verified solver handles one infinite limit or one discontinuity at an "
                                     "endpoint (split the integral otherwise)")
        c = bad[0]
        if c == b:
            lim_pt, lo, hi, side = b, a, t, "-"
        else:
            lim_pt, lo, hi, side = a, t, b, "+"
        why = f"f is undefined at x = {to_text(c)}, an endpoint: replace it by t and take a one-sided limit."
    B.steps.append(Step(id="s0", kind=SETUP, before=None, operation="Improper integral as a limit",
                        after=sp.Limit(sp.Integral(f, (x, lo, hi)), t, lim_pt, side), justification=why,
                        data={"chain": False}))
    F = _antiderivative(B, f, x)
    with sp.evaluate(False):
        ftc = A(F.xreplace({x: hi}), M(-1, F.xreplace({x: lo})))
    G = sp.simplify(F.subs(x, hi) - F.subs(x, lo))
    B.add(ftc, "F(upper) − F(lower)", G, "Fundamental Theorem of Calculus with the variable limit t.")
    LS = LimitSolver(t, lim_pt, side)
    LS.B = Builder(start=B.k)
    LS.B.steps.append(Step(id=f"s{B.k}", kind=SETUP, before=G, operation="Take the limit",
                           after=sp.Limit(G, t, lim_pt, side), justification="Now let t approach the bad point.",
                           data={"chain": False}))
    LS.B.k += 1
    val = LS.solve(G)
    B.steps += LS.B.steps
    B.k = LS.B.k
    converges = val.is_finite is True
    B.add(None, "Conclusion", "converges" if converges else "diverges",
          f"The limit is {to_text(val)}, so the integral " + ("converges." if converges else "diverges."),
          kind=FACT, rule="conclusion")
    return Solution(problem=p, steps=B.steps, answer=val, answer_label="value" if converges else "diverges",
                    facts={"x": x, "f": f, "a": a, "b": b, "F": F, "converges": converges}, notes=[])


# ---------------------------------------------------------------- area between curves
def area_between(p: Problem) -> Solution:
    x = sp.Symbol(p.given["variable"], real=True)
    f, g = p.expr("top_or_first"), p.expr("second")
    B = Builder()
    B.steps.append(Step(id="s0", kind=SETUP, before=None, operation="The two curves", after=[sp.Eq(sp.Symbol("y"), f),
                        sp.Eq(sp.Symbol("y"), g)], justification="Area = ∫ (top − bottom) dx over each piece.",
                        data={"chain": False}))
    if "a" in p.given and "b" in p.given:
        a, b = parse_math(p.given["a"]), parse_math(p.given["b"])
        inner = real_solutions(sp.Eq(f, g), x, sp.Interval.open(a, b))
        if inner:
            B.add(sp.Eq(f, g), "Where the curves cross inside the interval", [sp.Eq(x, c) for c in inner],
                  "Solve f(x) = g(x); the top curve can change there.", kind=FACT, rule="cross")
    else:
        pts = real_solutions(sp.Eq(f, g), x)
        if len(pts) < 2:
            raise UnsupportedProblem("the curves don't enclose a bounded region (fewer than two intersections)")
        B.add(sp.Eq(f, g), "Intersection points", [sp.Eq(x, c) for c in pts], "Solve f(x) = g(x).", kind=FACT,
              rule="cross")
        a, b, inner = pts[0], pts[-1], pts[1:-1]
    cuts = [a] + list(inner) + [b]
    total = sp.Integer(0)
    pieces = []
    for lo, hi in zip(cuts, cuts[1:]):
        mid = (lo + hi) / 2
        dv = B.add(_at(f - g, x, mid), f"Which is on top on [{to_text(lo)}, {to_text(hi)}]?",
                   sp.simplify((f - g).subs(x, mid)), f"Test x = {to_text(mid)}: the sign of f − g.")
        top, bot = (f, g) if dv > 0 else (g, f)
        h = sp.expand(top - bot)
        F = _antiderivative(B, h, x)
        with sp.evaluate(False):
            ftc = A(F.xreplace({x: hi}), M(-1, F.xreplace({x: lo})))
        piece = B.add(ftc, f"∫ from {to_text(lo)} to {to_text(hi)} of (top − bottom)",
                      sp.nsimplify(sp.simplify(F.subs(x, hi) - F.subs(x, lo))), "Evaluate F(b) − F(a).")
        pieces.append((lo, hi, top, bot, piece))
        total += piece
    if len(pieces) > 1:
        B.add(A(*[pc[4] for pc in pieces]), "Add the pieces", sp.simplify(total), "Total area.")
    return Solution(problem=p, steps=B.steps, answer=sp.simplify(total), answer_label="area",
                    facts={"x": x, "f": f, "g": g, "a": a, "b": b, "pieces": pieces}, notes=[f"≈ {float(total):.6g}"])


# ---------------------------------------------------------------- volumes of revolution
def volume(p: Problem) -> Solution:
    x = sp.Symbol(p.given["variable"], real=True)
    f = p.expr("outer")
    g = p.expr("inner") if "inner" in p.given else sp.Integer(0)
    a, b = parse_math(p.given["a"]), parse_math(p.given["b"])
    axis = p.given.get("axis", "x")  # "x", "y", "y=c", "x=c"
    B = Builder()
    horizontal = axis == "x" or axis.startswith("y=")
    if horizontal:
        c = sp.Integer(0) if axis == "x" else parse_math(axis.split("=")[1])
        mid = (a + b) / 2
        # outer radius = the curve farther from the axis (checked at the middle of the interval)
        far, near = (f, g) if abs(sp.N((f - c).subs(x, mid))) >= abs(sp.N((g - c).subs(x, mid))) else (g, f)
        R, r = sp.simplify(far - c), sp.simplify(near - c)
        method = "disk" if r == 0 else "washer"
        integrand = sp.expand(sp.pi * (R**2 - r**2))
        B.steps.append(Step(id="s0", kind=SETUP, before=None, operation=f"{method.capitalize()} method",
                            after=sp.Integral(sp.pi * (R**2 - r**2), (x, a, b)),
                            justification=f"Rotating about the horizontal line y = {to_text(c)}: each slice is a "
                                          f"{method} with outer radius R = |{to_text(R)}|" +
                                          (f" and inner radius r = |{to_text(r)}|" if method == "washer" else "") +
                                          ", so V = π∫(R² − r²) dx.", data={"chain": False}))
    else:
        c = sp.Integer(0) if axis == "y" else parse_math(axis.split("=")[1])
        method = "shell"
        rad = sp.simplify(x - c)
        sign = 1 if (a + b) / 2 - c > 0 else -1
        integrand = sp.expand(2 * sp.pi * sign * rad * (f - g))
        B.steps.append(Step(id="s0", kind=SETUP, before=None, operation="Shell method",
                            after=sp.Integral(2 * sp.pi * sign * rad * (f - g), (x, a, b)),
                            justification=f"Rotating about the vertical line x = {to_text(c)}: shells of radius "
                                          f"|x − {to_text(c)}| and height {to_text(f - g)}, so "
                                          "V = 2π∫(radius)(height) dx.", data={"chain": False}))
    F = _antiderivative(B, integrand, x)
    with sp.evaluate(False):
        ftc = A(F.xreplace({x: b}), M(-1, F.xreplace({x: a})))
    V = B.add(ftc, "Evaluate F(b) − F(a)", sp.nsimplify(sp.simplify(F.subs(x, b) - F.subs(x, a)), [sp.pi]),
              "Fundamental Theorem of Calculus.")
    return Solution(problem=p, steps=B.steps, answer=sp.simplify(V), answer_label="volume",
                    facts={"x": x, "f": f, "g": g, "a": a, "b": b, "axis": axis, "c": c, "method": method,
                           "integrand": integrand}, notes=[f"≈ {float(V):.6g}"])


# ---------------------------------------------------------------- domain, inverse, linearization, higher derivative
def domain(p: Problem) -> Solution:
    x = sp.Symbol(p.given["variable"], real=True)
    f = p.expr("function")
    B = Builder()
    B.steps.append(Step(id="s0", kind=SETUP, before=None, operation="Function", after=f,
                        justification="List every condition needed for f(x) to be a real number.",
                        data={"chain": False}))
    conds = []
    for n in sp.preorder_traversal(f):
        if n.is_Pow and n.exp.is_negative:
            conds.append((sp.Ne(n.base, 0), "a denominator can't be 0"))
        if n.is_Pow and n.exp.is_Rational and not n.exp.is_Integer and n.exp.q % 2 == 0:
            conds.append((n.base >= 0, "an even root needs a nonnegative argument"))
        if isinstance(n, sp.log):
            conds.append((n.args[0] > 0, "ln needs a positive argument"))
        if isinstance(n, (sp.asin, sp.acos)):
            conds.append((sp.And(n.args[0] >= -1, n.args[0] <= 1), "arcsin/arccos need an argument in [−1, 1]"))
    dom = sp.S.Reals
    for cond, why in conds:
        if isinstance(cond, sp.Ne):
            sset = sp.S.Reals - sp.solveset(sp.Eq(cond.lhs, cond.rhs), x, sp.S.Reals)
        else:
            sset = sp.solveset(cond, x, sp.S.Reals)
        B.add(cond, why.capitalize(), sset, f"Solve {to_text(cond)}.", kind=FACT, rule="condition")
        dom = dom.intersect(sset)
    B.add(None, "Domain", dom, "All conditions together (intersection).", kind=FACT, rule="domain")
    return Solution(problem=p, steps=B.steps, answer=dom, answer_label="domain", facts={"x": x, "f": f}, notes=[])


def inverse_function(p: Problem) -> Solution:
    x = sp.Symbol(p.given["variable"], real=True)
    y = sp.Symbol("y", real=True)
    f = p.expr("function")
    lo = parse_math(p.given.get("domain_from", "-oo"))
    B = Builder()
    eq = sp.Eq(y, f)
    B.steps.append(Step(id="s0", kind=SETUP, before=None, operation="Write y = f(x)", after=eq,
                        justification="Solve for x, then swap the names of x and y.", data={"chain": False}))
    all_sols = [to_real_roots(s) for s in sp.solve(eq, x)]
    sols = [s for s in all_sols if s.is_real is not False]
    dom = sp.Interval(lo, sp.oo) if lo != -sp.oo else sp.S.Reals
    if len(sols) > 1:
        test = lo + 1 if lo != -sp.oo else sp.Integer(1)
        sols = [s for s in sols if sp.simplify(s.subs(y, f.subs(x, test)) - test) == 0]
    if len(sols) != 1:
        raise UnsupportedProblem("f is not one-to-one on this domain (or x can't be isolated); give 'domain_from'")
    xs = sols[0]
    if len([s_ for s_ in all_sols if s_.is_real is not False]) > 1:
        # the domain picks one branch: checked by f⁻¹(f(x)) = x on the domain (see the verifier)
        why = (f"Isolate x; only this solution has x ≥ {to_text(lo)}." if lo != -sp.oo else
               "Isolate x; this is the real solution (an odd root of a negative number is negative).")
        B.add(eq, "Solve for x" + (" (on the given domain)" if lo != -sp.oo else ""), sp.Eq(x, xs), why,
              kind=FACT, chain=True, rule="branch")
    else:
        B.add(eq, "Solve for x", sp.Eq(x, xs), "Isolate x.", kind=EQUATION, chain=True, unknowns=[x])
    finv = xs.subs(y, x)
    B.add(None, "Swap x and y", sp.Eq(sp.Symbol("f⁻¹(x)"), finv), "Rename: the inverse takes x back to the input.",
          kind=FACT, rule="swap")
    return Solution(problem=p, steps=B.steps, answer=finv, answer_label="f⁻¹(x)",
                    facts={"x": x, "f": f, "finv": finv, "domain": dom}, notes=[])


def inverse_derivative(p: Problem) -> Solution:
    x = sp.Symbol(p.given["variable"], real=True)
    f = p.expr("function")
    b = parse_math(p.given["at"])
    B = Builder()
    B.steps.append(Step(id="s0", kind=SETUP, before=None, operation="Formula", after=sp.Symbol("(f⁻¹)′(b) = 1/f′(a)"),
                        justification=f"(f⁻¹)′(b) = 1/f′(a) where f(a) = b = {to_text(b)}.", data={"chain": False}))
    sols = real_solutions(sp.Eq(f, b), x)
    if len(sols) != 1:
        raise UnsupportedProblem(f"f(a) = {to_text(b)} must have exactly one real solution")
    a = sols[0]
    B.add(sp.Eq(f, b), f"Find a with f(a) = {to_text(b)}", sp.Eq(x, a), "Solve.", kind=EQUATION, unknowns=[x])
    fp = _derivative(B, f, x)
    fpa = B.add(_at(fp, x, a), f"f′({to_text(a)})", sp.simplify(fp.subs(x, a)), "Evaluate the derivative.")
    if fpa == 0:
        raise UnsupportedProblem("f′(a) = 0, so the inverse is not differentiable there")
    ans = B.add(frac(1, fpa), "(f⁻¹)′(b) = 1/f′(a)", 1 / fpa, "Take the reciprocal.")
    return Solution(problem=p, steps=B.steps, answer=ans, answer_label=f"(f⁻¹)′({to_text(b)})",
                    facts={"x": x, "f": f, "a": a, "b": b, "fprime": fp}, notes=[])


def linearization(p: Problem) -> Solution:
    from tutor.solvers.calculus.implicit import tangent_line

    sol = tangent_line(p)
    x = sol.facts["x"]
    L = sol.facts["line"].rhs
    B = Builder(start=len(sol.steps))
    x0 = parse_math(p.given["estimate_at"])
    est = B.add(_at(L, x, x0), f"L({to_text(x0)})", sp.nsimplify(L.subs(x, x0)),
                f"Use L(x) ≈ f(x) near x = {to_text(sol.facts['a'])}.")
    sol.steps += B.steps
    sol.facts.update(L=L, x0=x0, estimate=est)
    true = sp.N(sol.facts["f"].subs(x, x0), 15)
    sol.notes.append(f"L({to_text(x0)}) = {to_text(est)} ≈ {float(est):.6g}; the true value is ≈ {float(true):.6g}.")
    sol.answer, sol.answer_label = est, f"f({to_text(x0)}) ≈"
    return sol


def higher_derivative(p: Problem) -> Solution:
    x = sp.Symbol(p.given["variable"], real=True)
    f = p.expr("function")
    n = int(p.given["order"])
    if not 1 <= n <= 4:
        raise ProblemFormatError("order must be 1–4")
    B = Builder()
    B.steps.append(Step(id="s0", kind=SETUP, before=None, operation="Function", after=f,
                        justification=f"Differentiate {n} times, one derivative at a time.", data={"chain": False}))
    cur = f
    ders = []
    for k in range(n):
        cur = _derivative(B, cur, x)
        ders.append(cur)
    return Solution(problem=p, steps=B.steps, answer=cur, answer_label=f"order-{n} derivative",
                    facts={"x": x, "f": f, "order": n, "derivatives": ders}, notes=[])
