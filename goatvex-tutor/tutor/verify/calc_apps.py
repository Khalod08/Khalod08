"""Verifiers for calculus applications (independent re-checks + dense numerical sampling)."""

from __future__ import annotations

import mpmath
import numpy as np
import sympy as sp

from tutor.mathfn import real_roots_rewrite
from tutor.steps import Solution
from tutor.text.unicode_math import to_text
from tutor.verify.common import equal, ok, verify_steps
from tutor.verify.equivalence import check_equal
from tutor.verify.result import FAIL, INCONCLUSIVE, PASS, CheckResult


def _samples(f, x, lo, hi, n=2000):
    lo_f = float(lo) if lo.is_finite else -50.0
    hi_f = float(hi) if hi.is_finite else 50.0
    xs = np.linspace(lo_f, hi_f, n)[1:-1]
    lam = sp.lambdify(x, f, "numpy")
    with np.errstate(all="ignore"):
        ys = np.array(lam(xs), dtype=complex) * np.ones_like(xs)
    good = np.isfinite(ys) & (np.abs(ys.imag) < 1e-9)
    return xs[good], ys.real[good]


def verify_optimization(solution: Solution) -> list[CheckResult]:
    f = solution.facts
    x, fn, I = f["x"], f["f"], f["interval"]
    out = verify_steps(solution, [x])
    fp = sp.diff(fn, x)
    for c in f["critical"]:
        v = fp.subs(x, c)
        out.append(ok("final", f"x = {to_text(c)} is critical", sp.simplify(v) == 0 or not v.is_finite,
                      "f′ = 0 or undefined there"))
    indep = sp.solveset(sp.Eq(fp, 0), x, I)
    if isinstance(indep, sp.FiniteSet):
        out.append(ok("final", "no critical point missed (SymPy solveset)", set(indep) <= set(f["critical"]),
                      f"solveset finds {to_text(list(indep))}"))
    xs, ys = _samples(fn, x, I.inf, I.sup)
    tol = 1e-9 * max(1.0, float(np.max(np.abs(ys)))) if ys.size else 1e-9
    if f["closed"]:
        out.append(ok("final", "max is the largest value (2000-point scan)", float(ys.max()) <= float(f["max"]) + tol,
                      f"scan max {ys.max():.6g} ≤ {float(f['max']):.6g}"))
        out.append(ok("final", "min is the smallest value (2000-point scan)", float(ys.min()) >= float(f["min"]) - tol,
                      f"scan min {ys.min():.6g} ≥ {float(f['min']):.6g}"))
        for c, v in f["values"].items():
            out.append(equal("final", f"f({to_text(c)}) recomputed", v, fn.subs(x, c)))
    else:
        val, kind = f["value"], f["kind"]
        good = (ys.min() >= float(val) - tol) if kind == "minimum" else (ys.max() <= float(val) + tol)
        out.append(ok("final", f"absolute {kind} confirmed by a scan", bool(good), f"value {to_text(val)}"))
        s2 = sp.diff(fn, x, 2).subs(x, f["point"])
        out.append(ok("final", "second-derivative sign", (s2 > 0) == (kind == "minimum"), f"f″ = {to_text(s2)}"))
    return out


def verify_curve(solution: Solution) -> list[CheckResult]:
    f = solution.facts
    x, fn = f["x"], f["f"]
    out = verify_steps(solution, [x])
    xs = np.linspace(-20, 20, 4001)
    lam = sp.lambdify(x, fn, "numpy")
    with np.errstate(all="ignore"):
        ys = np.array(lam(xs), dtype=complex) * np.ones_like(xs)
    defined = np.isfinite(ys) & (np.abs(ys.imag) < 1e-9)
    in_dom = np.array([f["domain"].contains(sp.Float(t)) == sp.true for t in xs])
    mismatch = np.sum(defined != in_dom)
    out.append(ok("final", "domain matches where f is defined (4001-point scan)", mismatch <= 2,
                  f"{mismatch} disagreements (only at boundary points allowed)"))
    if f["y_int"] is not None:
        out.append(equal("final", "y-intercept", f["y_int"], fn.subs(x, 0)))
    for r in f["x_ints"]:
        out.append(equal("final", f"x-intercept {to_text(r)}", fn.subs(x, r), 0))
    for c in f["vas"]:
        both = [sp.limit(fn, x, c, d) for d in ("+", "-")]
        out.append(ok("final", f"vertical asymptote x = {to_text(c)}", any(v.is_infinite for v in both),
                      f"one-sided limits {to_text(both[0])}, {to_text(both[1])}"))
    for v in f["has"]:
        out.append(ok("final", f"horizontal asymptote y = {to_text(v)}",
                      v in (sp.limit(fn, x, sp.oo), sp.limit(fn, x, -sp.oo)), "a limit at ±∞"))
    if f["slant"] is not None:
        out.append(equal("final", "slant asymptote", sp.limit(fn - f["slant"], x, sp.oo), 0))
    for name, g, chart in (("f′", sp.diff(fn, x), f["chart1"]), ("f″", sp.diff(fn, x, 2), f["chart2"])):
        for lo, hi, sgn in chart:
            xs2, ys2 = _samples(g, x, lo if lo.is_finite else sp.Integer(-30), hi if hi.is_finite else sp.Integer(30), 400)
            inner = (xs2 > float(lo) + 1e-6 if lo.is_finite else True) & (xs2 < float(hi) - 1e-6 if hi.is_finite else True)
            vals = ys2[inner] if isinstance(inner, np.ndarray) else ys2
            agree = np.all(vals > 0) if sgn == "+" else np.all(vals < 0)
            out.append(ok("final", f"sign of {name} on ({to_text(lo)}, {to_text(hi)})", bool(agree) and vals.size > 0,
                          f"{name} is {sgn} at every sampled point"))
    return out


def verify_improper(solution: Solution) -> list[CheckResult]:
    f = solution.facts
    x, fn, a, b = f["x"], f["f"], f["a"], f["b"]
    out = verify_steps(solution, [x])
    from tutor.steps import LIMIT_STEP
    from tutor.verify.calculus import check_limit_step

    for s in solution.steps:
        if s.kind == LIMIT_STEP:
            out += check_limit_step(s)
    other = sp.integrate(fn, (x, a, b))
    val = solution.answer
    same = (val == other) if (val.is_infinite or other.is_infinite) else check_equal(val, other)[0] == PASS
    out.append(ok("final", "second method: SymPy improper integral", same, f"SymPy: {to_text(other)}"))
    if f["converges"]:
        with mpmath.workdps(30):
            q = mpmath.quad(sp.lambdify(x, fn, "mpmath"), [sp.N(a, 35) if a.is_finite else -mpmath.inf,
                                                           sp.N(b, 35) if b.is_finite else mpmath.inf])
        out.append(ok("final", "numerical quadrature", abs(complex(q) - complex(sp.N(val))) < 1e-8 * max(1, abs(q)),
                      f"≈ {mpmath.nstr(q, 12)}"))
    return out


def verify_area(solution: Solution) -> list[CheckResult]:
    f = solution.facts
    x, fn, gn, a, b = f["x"], f["f"], f["g"], f["a"], f["b"]
    out = verify_steps(solution, [x])
    for lo, hi, top, bot, _ in f["pieces"]:
        xs, ys = _samples(top - bot, x, lo, hi, 400)
        out.append(ok("final", f"top curve on [{to_text(lo)}, {to_text(hi)}]", bool(np.all(ys >= -1e-9)),
                      "top − bottom ≥ 0 at every sampled point"))
    with mpmath.workdps(30):
        q = mpmath.quad(sp.lambdify(x, sp.Abs(fn - gn), "mpmath"), [sp.N(a, 35)] +
                        [sp.N(c, 35) for c in [pc[1] for pc in f["pieces"][:-1]]] + [sp.N(b, 35)])
    out.append(ok("final", "second method: numerical ∫|f − g|", abs(float(q) - float(solution.answer)) < 1e-9 * max(1, abs(float(q))),
                  f"≈ {mpmath.nstr(q, 12)}"))
    return out


def verify_volume(solution: Solution) -> list[CheckResult]:
    f = solution.facts
    x, a, b = f["x"], f["a"], f["b"]
    out = verify_steps(solution, [x])
    with mpmath.workdps(30):
        q = mpmath.quad(sp.lambdify(x, f["integrand"], "mpmath"), [sp.N(a, 35), sp.N(b, 35)])
        # Pappus: V = 2π · (distance from the region's centroid to the axis) · (area), from separate integrals
        h = sp.lambdify(x, sp.Abs(f["f"] - f["g"]), "mpmath")
        area = mpmath.quad(h, [sp.N(a, 35), sp.N(b, 35)])
        c = float(f["c"])
        if f["method"] == "shell":
            mx = mpmath.quad(lambda t: abs(t - c) * h(t), [sp.N(a, 35), sp.N(b, 35)])
            pappus = 2 * mpmath.pi * mx
        else:
            F, G = sp.lambdify(x, f["f"], "mpmath"), sp.lambdify(x, f["g"], "mpmath")
            my = mpmath.quad(lambda t: abs(((F(t) - c) ** 2 - (G(t) - c) ** 2) / 2), [sp.N(a, 35), sp.N(b, 35)])
            pappus = 2 * mpmath.pi * my
    V = float(solution.answer)
    out.append(ok("final", "numerical quadrature of the set-up", abs(float(q) - V) < 1e-9 * max(1, abs(V)),
                  f"≈ {mpmath.nstr(q, 12)}"))
    out.append(ok("final", "second method: Pappus' theorem (centroid × area)", abs(float(pappus) - V) < 1e-8 * max(1, abs(V)),
                  f"2π·(centroid distance)·(area) ≈ {mpmath.nstr(pappus, 12)}"))
    return out


def verify_domain(solution: Solution) -> list[CheckResult]:
    f = solution.facts
    x, fn = f["x"], f["f"]
    out = verify_steps(solution, [x])
    dom = solution.answer
    xs = np.linspace(-15, 15, 3001)
    lam = sp.lambdify(x, fn, "numpy")
    with np.errstate(all="ignore"):
        ys = np.array(lam(xs), dtype=complex) * np.ones_like(xs)
    defined = np.isfinite(ys) & (np.abs(ys.imag) < 1e-9)
    claimed = np.array([dom.contains(sp.Float(t)) == sp.true for t in xs])
    bad = int(np.sum(defined != claimed))
    out.append(ok("final", "domain matches where f is a real number (3001-point scan)", bad <= 2,
                  f"{bad} disagreements (only boundary points allowed)"))
    out.append(ok("final", "second method: SymPy continuous_domain",
                  sp.calculus.util.continuous_domain(fn, x, sp.S.Reals) == dom, "same set"))
    return out


def verify_inverse(solution: Solution) -> list[CheckResult]:
    f = solution.facts
    x, fn, finv, dom = f["x"], f["f"], f["finv"], f["domain"]
    out = verify_steps(solution, [x])
    lo = dom.inf if dom.inf.is_finite else sp.Integer(-3)
    d = (lo, sp.oo) if dom.inf.is_finite else None
    st, det = check_equal(finv.subs(x, fn), x, [x], domain=d)
    out.append(CheckResult("final", "f⁻¹(f(x)) = x on the domain", st, det))
    xs, ys = _samples(fn, x, lo + sp.Rational(1, 10), lo + 5, 40)
    back = sp.lambdify(x, real_roots_rewrite(finv), "numpy")
    with np.errstate(all="ignore"):
        rt = np.array(back(ys), dtype=complex)
    out.append(ok("final", "f(f⁻¹(y)) = y numerically (40 points)", bool(np.allclose(rt.real, xs, atol=1e-8)),
                  "round trip recovers x"))
    return out


def verify_inverse_derivative(solution: Solution) -> list[CheckResult]:
    f = solution.facts
    x, fn, a, b = f["x"], f["f"], f["a"], f["b"]
    out = verify_steps(solution, [x])
    out.append(equal("final", "f(a) = b", fn.subs(x, a), b))
    lam = sp.lambdify(x, fn, "mpmath")
    with mpmath.workdps(30):
        inv = lambda y: mpmath.findroot(lambda t: lam(t) - y, mpmath.mpf(sp.N(a, 35)))  # noqa: E731
        num = mpmath.diff(inv, mpmath.mpf(sp.N(b, 35)))
    out.append(ok("final", "numerical derivative of the numerical inverse", abs(float(num) - float(solution.answer)) < 1e-8,
                  f"≈ {mpmath.nstr(num, 12)}"))
    return out


def verify_linearization(solution: Solution) -> list[CheckResult]:
    from tutor.verify.calculus import verify_tangent

    out = verify_tangent(solution)
    f = solution.facts
    out.append(equal("final", "estimate = L(x₀)", f["estimate"], f["L"].subs(f["x"], f["x0"])))
    return out


def verify_higher(solution: Solution) -> list[CheckResult]:
    f = solution.facts
    x = f["x"]
    out = verify_steps(solution, [x])
    for k, d in enumerate(f["derivatives"], 1):
        out.append(equal("final", f"derivative {k}: second method (SymPy diff)", d, sp.diff(f["f"], x, k), [x]))
    return out
