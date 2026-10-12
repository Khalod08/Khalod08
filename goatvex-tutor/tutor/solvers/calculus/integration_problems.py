"""Integration problems built on the step engine in ``integral.py``.

* indefinite integral (optionally with an initial condition F(x₀) = y₀)
* definite integral by the Fundamental Theorem of Calculus (part 2)
* FTC part 1: d/dx ∫ₐ^{g(x)} f(t) dt
* Riemann sums (left, right, midpoint, trapezoid) and their limit
"""

from __future__ import annotations

import sympy as sp

from tutor.errors import ProblemFormatError, UnsupportedProblem
from tutor.parse.schema import Problem, parse_math
from tutor.solvers.builder import A, Builder, M, frac
from tutor.solvers.calculus.derivative import combine, rule_steps
from tutor.solvers.calculus.integral import antiderivative_steps
from tutor.steps import ALGEBRA, FACT, SETUP, Solution, Step
from tutor.text.unicode_math import sub, to_text

C = sp.Symbol("C")


def _var(p: Problem) -> sp.Symbol:
    return sp.Symbol(p.given.get("variable", "x"), real=True)


def _at(F, x, v):
    """F with x replaced by v, numbers visible (e.g. (2)³ + 2)."""
    with sp.evaluate(False):
        return F.xreplace({x: v})


def indefinite(p: Problem) -> Solution:
    x = _var(p)
    f = p.expr("integrand")
    setup = Step(id="s0", kind=SETUP, before=f, operation="Set up", after=sp.Integral(f, x),
                 justification=f"Find all antiderivatives of {to_text(f)}.", data={"variable": x})
    info: dict = {}
    steps, F = antiderivative_steps(f, x, info=info)
    steps = [setup] + steps
    facts = {"variable": x, "integrand": f, "F": F, "domain": info.get("domain")}
    notes = [f"Every antiderivative is {to_text(F)} + C."]
    if info.get("domain"):
        lo, hi = info["domain"]
        notes.append(f"This method (x = a·sec θ) gives the antiderivative for {x} > {to_text(lo)}; that is the "
                     f"part of the domain this answer is verified on.")
    answer, label = F, f"∫ {to_text(f)} d{x}  (+ C)"
    if "initial" in p.given:
        x0 = parse_math(p.given["initial"]["x"])
        y0 = parse_math(p.given["initial"]["y"])
        k = len(steps)
        B = Builder(start=k)
        eq = sp.Eq(A(_at(F, x, x0), C), y0)
        B.add(None, f"Use F({to_text(x0)}) = {to_text(y0)}", eq, "Plug the initial condition into F(x) + C.", kind=FACT)
        cval = sp.solve(sp.Eq(F.subs(x, x0) + C, y0), C)[0]
        B.add(eq, "Solve for C", sp.Eq(C, cval), "A linear equation in C.", kind="equation", unknowns=[C])
        answer = F + cval
        B.add(A(F, cval), "The particular antiderivative", answer, f"C = {to_text(cval)}.")
        steps += B.steps
        facts["initial"] = (x0, y0)
        label, notes = "F(x)", []
    return Solution(problem=p, steps=steps, answer=answer, answer_label=label, facts=facts, notes=notes)


def discontinuities(f, x, a, b) -> list:
    try:
        sing = sp.singularities(f, x, sp.Interval(a, b))
        if isinstance(sing, sp.FiniteSet):
            return sorted(sing, key=lambda v: float(v))
        return [] if sing == sp.EmptySet else ["(infinitely many)"]
    except Exception:
        return []


def definite(p: Problem) -> Solution:
    x = _var(p)
    f = p.expr("integrand")
    a, b = parse_math(p.given["a"]), parse_math(p.given["b"])
    if a.is_infinite or b.is_infinite:
        raise UnsupportedProblem("an infinite bound makes this an improper integral: use the improper_integral type")
    bad = discontinuities(f, x, a, b)
    if bad:
        raise UnsupportedProblem(f"{to_text(f)} is discontinuous at {', '.join(map(to_text, bad))} inside "
                                 f"[{to_text(a)}, {to_text(b)}], so this is an improper integral")
    steps: list[Step] = [Step(id="s0", kind=SETUP, before=f, operation="Set up", after=sp.Integral(f, (x, a, b)),
                              justification="By the Fundamental Theorem of Calculus, ∫ₐᵇ f = F(b) − F(a) for any "
                                            "antiderivative F. First find F.", data={"chain": False})]
    anti, F = antiderivative_steps(f, x)
    anti[0].data["chain"] = False
    steps += anti
    k = len(steps)
    B = Builder(start=k)
    ftc = A(_at(F, x, b), M(-1, _at(F, x, a)))
    B.add(sp.Integral(f, (x, a, b)), "Fundamental Theorem: F(b) − F(a)", ftc,
          f"Evaluate F at the top limit {to_text(b)} and subtract F at the bottom limit {to_text(a)}.")
    value = sp.nsimplify(sp.simplify(F.subs(x, b) - F.subs(x, a)))
    B.add(ftc, "Arithmetic", value, "Simplify.")
    steps += B.steps
    return Solution(problem=p, steps=steps, answer=value, answer_label=f"∫[{to_text(a)}→{to_text(b)}]",
                    facts={"variable": x, "integrand": f, "a": a, "b": b, "F": F, "discontinuities": bad},
                    notes=[f"Antiderivative used: F({x}) = {to_text(F)}. Decimal: ≈ {float(sp.N(value)):.6g}."])


def ftc1(p: Problem) -> Solution:
    x = _var(p)
    t = sp.Symbol(p.given.get("dummy", "t"), real=True)
    f = parse_math(p.given["integrand"], [t.name])
    lower = parse_math(p.given["lower"], [x.name])
    upper = parse_math(p.given["upper"], [x.name])
    if f.has(x):
        raise ProblemFormatError(f"the integrand should use the dummy variable {t}, not {x}")
    start = sp.Derivative(sp.Integral(f, (t, lower, upper)), x, evaluate=False)
    B = Builder()
    B.steps.append(Step(id="s0", kind=SETUP, before=start, operation="Set up", after=start,
                        justification=f"Differentiate an integral whose limits depend on {x}.", data={"chain": False}))
    terms = []
    if upper.has(x):
        terms.append(M(f.xreplace({t: upper}), sp.Derivative(upper, x, evaluate=False)))
    if lower.has(x):
        terms.append(M(-1, M(f.xreplace({t: lower}), sp.Derivative(lower, x, evaluate=False))))
    if not terms:
        raise UnsupportedProblem(f"neither limit depends on {x}, so the derivative is just 0")
    rep = A(*terms) if len(terms) > 1 else terms[0]
    B.add(start, "FTC part 1 + chain rule", rep,
          "d/dx ∫ₐ^{g(x)} f(t) dt = f(g(x))·g′(x): put the upper limit into f and multiply by its derivative"
          + (" (and subtract the same for the lower limit)." if lower.has(x) else "."), chain=True)
    rsteps, cur = rule_steps(rep, x, k=B.k)
    for s_ in rsteps:
        s_.data["chain"] = True
    B.steps += rsteps
    B.k += len(rsteps)
    ans = combine(cur)
    if ans != cur:
        B.add(cur, "Simplify", ans, "Combine.", chain=True)
    return Solution(problem=p, steps=B.steps, answer=ans, answer_label=f"d/d{x}", facts={"variable": x, "t": t,
                    "integrand": f, "lower": lower, "upper": upper}, notes=[])


def riemann(p: Problem) -> Solution:
    x = _var(p)
    f = p.expr("function")
    a, b = parse_math(p.given["a"]), parse_math(p.given["b"])
    n = int(p.given["n"])
    method = p.given.get("method", "right")
    if n < 1 or n > 50:
        raise ProblemFormatError("n must be between 1 and 50")
    B = Builder()
    dx = B.add(frac(A(b, -a), n), "Δx = (b − a)/n", (b - a) / n, f"Width of each of the {n} rectangles.")
    if method == "left":
        pts = [a + i * dx for i in range(n)]
    elif method == "right":
        pts = [a + i * dx for i in range(1, n + 1)]
    elif method == "midpoint":
        pts = [a + (i + sp.Rational(1, 2)) * dx for i in range(n)]
    elif method == "trapezoid":
        pts = [a + i * dx for i in range(n + 1)]
    else:
        raise ProblemFormatError("method must be left, right, midpoint or trapezoid")
    B.add(None, "Sample points", pts, f"{method.capitalize()} {'endpoints' if method != 'midpoint' else 'points'}: "
                                      + ", ".join(to_text(q) for q in pts) + ".", kind=FACT)
    vals = []
    for i, q in enumerate(pts):
        vals.append(B.add(_at(f, x, q), f"f(x{sub(i)})", sp.nsimplify(f.subs(x, q)), f"f at x = {to_text(q)}."))
    if method == "trapezoid":
        weights = [1] + [2] * (n - 1) + [1]
        total = A(*[M(w, v) for w, v in zip(weights, vals)])
        s = B.add(M(frac(dx, 2), total), "T = (Δx/2)[f(x₀) + 2f(x₁) + … + 2f(xₙ₋₁) + f(xₙ)]",
                  dx / 2 * sum(w * v for w, v in zip(weights, vals)), "Trapezoid rule.")
    else:
        s = B.add(M(dx, A(*vals) if len(vals) > 1 else vals[0]), "Sum = Δx·(f(x₁) + … )", dx * sum(vals),
                  "Add the heights and multiply by the width.")
    exact = sp.integrate(f, (x, a, b))
    return Solution(problem=p, steps=B.steps, answer=sp.nsimplify(s), answer_label=f"{method} sum",
                    facts={"variable": x, "f": f, "a": a, "b": b, "n": n, "method": method, "points": pts},
                    notes=[f"≈ {float(s):.6g}. For comparison, the exact area ∫ = {to_text(exact)} ≈ {float(sp.N(exact)):.6g}."])
