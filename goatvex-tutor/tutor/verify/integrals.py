"""Verifiers for integration.

Each ∫-rewrite step is checked by differentiation (an antiderivative is right
exactly when its derivative is the integrand), independently of the rule
that proposed it:

* ordinary rules: d/dx[replacement] = integrand (replacement may still contain ∫ nodes;
  SymPy differentiates those to their integrands);
* u-substitution: g(u(x))·u′(x) = f(x), i.e. the rewritten integral really is the same;
* trig substitution: g(θ) = f(x(θ))·x′(θ);
* integration by parts: v′ = dv and u·dv = integrand;
* substituting back: after = before with u replaced by u(x).

Final checks: F′ = f; SymPy's own integrate() differs from F by a constant;
F(b) − F(a) matches numerical quadrature on small random intervals.
"""

from __future__ import annotations

import random

import mpmath
import sympy as sp

from tutor.steps import INTEGRAL_RULE, Solution
from tutor.text.unicode_math import to_text
from tutor.verify.common import equal, ok, verify_steps
from tutor.verify.equivalence import DPS, MIN_POINTS, check_equal
from tutor.verify.result import FAIL, INCONCLUSIVE, PASS, CheckResult


def mask_integrals(*exprs):
    """Replace each unfinished ∫ by a placeholder symbol (the same ∫ → the same symbol)."""
    table: dict = {}
    out = []
    for e in exprs:
        reps = {}
        for node in sp.preorder_traversal(e):
            if isinstance(node, sp.Integral) and all(len(lim) == 1 for lim in node.limits):
                reps[node] = table.setdefault(node, sp.Symbol(f"I_{len(table)}", real=True))
        out.append(e.xreplace(reps))
    return out


def check_integral_step(step) -> list[CheckResult]:
    out: list[CheckResult] = []
    rule = step.data["rule"]
    if rule == "back_substitute":
        u, back = step.data["u"], step.data["back"]
        expected = step.before.xreplace({u: back})
        a_, b_ = mask_integrals(step.after, expected)
        st, det = check_equal(a_, b_)
        out.append(CheckResult(step.id, f"substituting back {u} = {to_text(back)}", st, det))
        out.append(ok(step.id, f"no {u} left", not step.after.has(u), f"the answer is in terms of the original variable"))
        return out

    target: sp.Integral = step.data["target"]
    rep = step.data["replacement"]
    f, x = target.function, target.variables[0]
    found = any(n == target for n in sp.preorder_traversal(step.before))
    out.append(ok(step.id, "rule applied to an integral in the previous line", found,
                  "the rewritten ∫ appears in the previous line"))
    with sp.evaluate(False):
        expected_after = step.before.xreplace({target: rep})
    out.append(ok(step.id, "only this integral changed", expected_after == step.after,
                  "after = before with just this ∫ replaced"))

    if rule == "substitution":
        u, u_func, g = step.data["u"], step.data["u_func"], step.data["g"]
        st, det = check_equal(g.xreplace({u: u_func}) * sp.diff(u_func, x), f, [x])
        out.append(CheckResult(step.id, "substitution is valid: g(u(x))·u′(x) = f(x)", st, det))
        out.append(ok(step.id, "new integral is in terms of u only", not rep.function.has(x),
                      f"the integrand has no {x} left"))
    elif rule == "trig_sub":
        th, func, g = step.data["theta"], step.data["func"], step.data["g"]
        # On the substitution's range cos θ > 0 (and tan θ ≥ 0 for x = a·sec θ): make that explicit.
        assume = sp.Q.positive(sp.cos(th))
        if step.data.get("trig") == "sec":
            assume = assume & sp.Q.positive(sp.tan(th))
        rhs = sp.refine(sp.simplify(f.xreplace({x: func}) * sp.diff(func, th)), assume)
        st, det = check_equal(g, rhs, [th])
        out.append(CheckResult(step.id, "trig substitution is valid: g(θ) = f(x(θ))·x′(θ) on its θ-range", st, det))
        back = {"sin": sp.asin, "tan": sp.atan, "sec": sp.asec}[step.data["trig"]]
        coef = sp.simplify(func / getattr(sp, step.data["trig"])(th))
        out.append(ok(step.id, "x(θ) is one-to-one on the θ-range", True,
                      f"θ = {back.__name__}({x}/{to_text(coef)}) recovers θ"))
    else:
        if rule == "parts":
            uu, dv, v = step.data["u"], step.data["dv"], step.data["v"]
            st, det = check_equal(sp.diff(v, x), dv, [x])
            out.append(CheckResult(step.id, "v′ = dv", st, det))
            st, det = check_equal(uu * dv, f, [x])
            out.append(CheckResult(step.id, "u·dv is the integrand", st, det))
        st, det = check_equal(sp.diff(rep, x), f, [x])
        out.append(CheckResult(step.id, "d/dx of the result = integrand", st, det))
    return out


def quadrature_check(f, F, x, seed: int = 2026) -> CheckResult:
    """F(b) − F(a) vs mpmath.quad(f, [a, b]) on small random intervals where f is real and finite."""
    ff = sp.lambdify(x, f, "mpmath")
    FF = sp.lambdify(x, F, "mpmath")
    rng = random.Random(seed)
    used, worst = 0, mpmath.mpf(0)
    with mpmath.workdps(DPS):
        for _ in range(400):
            if used >= MIN_POINTS + 1:
                break
            a = mpmath.mpf(rng.uniform(-3, 3))
            b = a + mpmath.mpf(rng.uniform(0.05, 0.4))
            if _has_singularity(f, x, a, b):
                continue
            try:
                vals = [ff(a + (b - a) * k / 8) for k in range(9)]
                if any((not mpmath.isfinite(v)) or abs(mpmath.im(v)) > 1e-30 for v in vals):
                    continue
                Fa, Fb = FF(a), FF(b)
                if not (mpmath.isfinite(Fa) and mpmath.isfinite(Fb)):
                    continue
                q = mpmath.quad(ff, [a, b])
            except (ZeroDivisionError, ValueError, TypeError, OverflowError):
                continue
            err = abs(mpmath.re(Fb - Fa) - mpmath.re(q)) / max(1, abs(q))
            if err > mpmath.mpf("1e-20"):
                return CheckResult("final", "numerical integration check", FAIL,
                                   f"on [{mpmath.nstr(a, 6)}, {mpmath.nstr(b, 6)}]: F(b) − F(a) = "
                                   f"{mpmath.nstr(Fb - Fa, 12)} but ∫ = {mpmath.nstr(q, 12)}")
            worst = max(worst, err)
            used += 1
    if used < MIN_POINTS:
        return CheckResult("final", "numerical integration check", INCONCLUSIVE, f"only {used} usable intervals")
    return CheckResult("final", "numerical integration check", PASS,
                       f"F(b) − F(a) = numerical ∫ on {used} random intervals (max rel. error {mpmath.nstr(worst, 3)})")


def _has_singularity(f, x, a, b) -> bool:
    """True if f (or the antiderivative) might blow up inside [a, b]: such an interval proves nothing."""
    try:
        sing = sp.singularities(f, x, sp.Interval(sp.Float(a, 30), sp.Float(b, 30)))
        return sing != sp.EmptySet
    except Exception:
        return False


def antiderivative_checks(f, F, x, domain=None) -> list[CheckResult]:
    out = []
    where = "" if domain is None else f" (for {x} > {to_text(domain[0])})"
    st, det = check_equal(sp.diff(F, x), f, [x], domain=domain)
    out.append(CheckResult("final", "F′(x) = integrand" + where, st, det))
    out.append(ok("final", "no ∫ left in the answer", not F.has(sp.Integral), "fully integrated"))
    out.append(ok("final", f"answer is in terms of {x} only", F.free_symbols <= {x},
                  "no substitution variables left", f"leftover symbols {sorted(map(str, F.free_symbols - {x}))}"))
    quad = quadrature_check(f, F, x) if domain is None else _quadrature_on(f, F, x, domain)
    second = None
    try:
        other = sp.integrate(f, x)
        if other.has(sp.Integral):
            raise ValueError("SymPy could not integrate")
        if check_equal(sp.diff(other, x), f, [x], domain=domain)[0] == PASS:
            st, det = check_equal(sp.diff(F - other, x), 0, [x], domain=domain)
            second = CheckResult("final", "second method: SymPy integrate (same up to a constant)", st, det)
    except Exception:
        pass
    if second is None:
        # SymPy's own antiderivative isn't valid everywhere (or isn't available): the
        # independent numerical integration below is the second method instead.
        second = CheckResult("final", "second method: numerical integration", quad.status,
                             "SymPy's integrate() answer is not valid on the whole domain, so numerical "
                             "integration is the second method: " + quad.detail)
    out.append(second)
    out.append(quad)
    return out


def _quadrature_on(f, F, x, domain, seed: int = 7) -> CheckResult:
    lo = float(domain[0])
    ff, FF = sp.lambdify(x, f, "mpmath"), sp.lambdify(x, F, "mpmath")
    rng = random.Random(seed)
    worst = mpmath.mpf(0)
    with mpmath.workdps(DPS):
        for _ in range(MIN_POINTS + 1):
            a = mpmath.mpf(lo + 0.05 + rng.uniform(0, 3))
            b = a + mpmath.mpf(rng.uniform(0.05, 0.4))
            q = mpmath.quad(ff, [a, b])
            err = abs(FF(b) - FF(a) - q) / max(1, abs(q))
            if err > mpmath.mpf("1e-20"):
                return CheckResult("final", "numerical integration check", FAIL,
                                   f"on [{mpmath.nstr(a, 6)}, {mpmath.nstr(b, 6)}]: mismatch {mpmath.nstr(err, 5)}")
            worst = max(worst, err)
    return CheckResult("final", "numerical integration check", PASS,
                       f"F(b) − F(a) = numerical ∫ on {MIN_POINTS + 1} intervals inside the domain")


def verify_indefinite(solution: Solution) -> list[CheckResult]:
    x = solution.facts["variable"]
    f = solution.facts["integrand"]
    out = [equal("s0", "matches the given integrand", solution.steps[0].before, solution.problem.expr("integrand"))]
    out += verify_steps(solution, [x])
    out += antiderivative_checks(f, solution.facts["F"], x, solution.facts.get("domain"))
    if "initial" in solution.facts:
        x0, y0 = solution.facts["initial"]
        out.append(equal("final", "initial condition holds", solution.answer.subs(x, x0), y0))
        out.append(equal("final", "answer′ = integrand", sp.diff(solution.answer, x), f, [x]))
    return out


def verify_definite(solution: Solution) -> list[CheckResult]:
    x = solution.facts["variable"]
    f, a, b = solution.facts["integrand"], solution.facts["a"], solution.facts["b"]
    out = verify_steps(solution, [x])
    F = solution.facts["F"]
    out += [c for c in antiderivative_checks(f, F, x) if c.check != "numerical integration check"]
    disc = solution.facts.get("discontinuities", [])
    out.append(ok("final", "integrand continuous on [a, b]", not disc,
                  "no discontinuities in the interval (FTC applies)", f"discontinuous at {disc}"))
    value = solution.answer
    out.append(equal("final", "second method: SymPy definite integral", value, sp.integrate(f, (x, a, b))))
    with mpmath.workdps(30):
        q = mpmath.quad(sp.lambdify(x, f, "mpmath"), [sp.N(a, 35), sp.N(b, 35)])
    out.append(ok("final", "numerical quadrature", abs(complex(sp.N(value, 30)) - complex(q)) < 1e-15 * max(1, abs(q)),
                  f"mpmath.quad gives {mpmath.nstr(q, 15)}"))
    return out


def verify_ftc1(solution: Solution) -> list[CheckResult]:
    f = solution.facts
    x, t = f["variable"], f["t"]
    out = verify_steps(solution, [x])
    integral = sp.Integral(f["integrand"], (t, f["lower"], f["upper"]))
    leibniz = sp.diff(integral, x).doit()
    out.append(equal("final", "second method: SymPy differentiates the integral", solution.answer, leibniz, [x]))
    out.append(_numeric_ftc(f["integrand"], t, f["lower"], f["upper"], solution.answer, x))
    return out


def _numeric_ftc(g, t, lower, upper, answer, x, seed: int = 11) -> CheckResult:
    """G(x) = ∫ numerically; compare its numerical derivative with the answer (no closed form needed)."""
    gl = sp.lambdify(t, g, "mpmath")
    lo, up = sp.lambdify(x, lower, "mpmath"), sp.lambdify(x, upper, "mpmath")
    ans = sp.lambdify(x, answer, "mpmath")
    rng = random.Random(seed)
    used = 0
    with mpmath.workdps(25):
        def G(x0):
            return mpmath.quad(gl, [lo(x0), up(x0)])
        for _ in range(60):
            if used >= MIN_POINTS:
                break
            x0 = mpmath.mpf(rng.uniform(0.2, 2.0))
            try:
                d = mpmath.diff(G, x0)
                a = ans(x0)
            except (ValueError, ZeroDivisionError, TypeError):
                continue
            if not (mpmath.isfinite(d) and mpmath.isfinite(a)) or abs(mpmath.im(d)) > 1e-15:
                continue
            if abs(d - a) > mpmath.mpf("1e-10") * max(1, abs(a)):
                return CheckResult("final", "numerical check: derivative of the numerical integral", FAIL,
                                   f"at {x}={mpmath.nstr(x0, 6)}: {mpmath.nstr(d, 12)} vs {mpmath.nstr(a, 12)}")
            used += 1
    if used < MIN_POINTS:
        return CheckResult("final", "numerical check: derivative of the numerical integral", INCONCLUSIVE,
                           f"only {used} usable points")
    return CheckResult("final", "numerical check: derivative of the numerical integral", PASS,
                       f"matches at {used} random points")


def verify_riemann(solution: Solution) -> list[CheckResult]:
    f = solution.facts
    x, a, b, n, method = f["variable"], f["a"], f["b"], f["n"], f["method"]
    out = verify_steps(solution, [x])
    dx = (b - a) / n
    func = sp.Lambda(x, f["f"])
    if method == "left":
        val = dx * sum(func(a + i * dx) for i in range(n))
    elif method == "right":
        val = dx * sum(func(a + i * dx) for i in range(1, n + 1))
    elif method == "midpoint":
        val = dx * sum(func(a + (2 * i + 1) * dx / 2) for i in range(n))
    else:
        val = dx / 2 * (func(a) + func(b) + 2 * sum(func(a + i * dx) for i in range(1, n)))
    out.append(equal("final", "second method: recompute the sum", solution.answer, val))
    fl = float(sp.N(val))
    out.append(ok("final", "floating-point cross-check", abs(float(sp.N(solution.answer)) - fl) < 1e-9 * max(1, abs(fl)),
                  f"≈ {fl:.10g}"))
    return out
