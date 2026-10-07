"""Verifiers for step-by-step derivatives.

For every rule step we check, independently of the solver's rule code:
  1. the step starts where the previous one ended;
  2. the rule's name actually fits the shape of the expression it was applied to;
  3. the local rewrite is correct: replacement ≡ sympy.diff(target);
  4. only that one d/dx[...] was rewritten (after = before with target replaced);
  5. the whole expression's value is unchanged (symbolic + ≥5 numeric points).
The final answer is compared with ``sympy.diff`` and with an mpmath numerical
derivative (finite differences) at random points.
"""

from __future__ import annotations

import random

import mpmath
import sympy as sp

from tutor.solvers.calculus import derivative as D
from tutor.steps import ALGEBRA, DERIVATIVE_RULE, SETUP, Solution
from tutor.text.unicode_math import to_text
from tutor.verify.equivalence import DPS, MIN_POINTS, check_equal
from tutor.verify.result import FAIL, INCONCLUSIVE, PASS, CheckResult


def _rule_fits(rule: str, g: sp.Expr, x: sp.Symbol) -> bool:
    """Independent description of when each rule's *name* is the right one."""
    has = lambda e: e.has(x)  # noqa: E731
    if rule == D.CONSTANT:
        return not has(g)
    if rule == D.IDENTITY:
        return g == x
    if rule == D.SUM:
        return g.is_Add
    if rule == D.CONST_MULTIPLE:
        return g.is_Mul and any(not has(f) for f in g.args) and has(g)
    if rule in (D.PRODUCT, D.QUOTIENT):
        return g.is_Mul and sum(1 for f in g.args if has(f)) >= 2
    if rule == D.POWER:
        return g.is_Pow and g.base == x and not has(g.exp)
    if rule == D.POWER_CHAIN:
        return g.is_Pow and has(g.base) and g.base != x and not has(g.exp)
    if rule == D.EXPONENTIAL_BASE:
        return g.is_Pow and not has(g.base) and g.exp == x
    if rule == D.EXPONENTIAL_BASE_CHAIN:
        return g.is_Pow and not has(g.base) and has(g.exp) and g.exp != x
    if rule == D.BASIC_FUNCTION:
        return isinstance(g, sp.Function) and g.args == (x,)
    if rule == D.FUNCTION_CHAIN:
        return isinstance(g, sp.Function) and len(g.args) == 1 and g.args[0] != x and has(g.args[0])
    return False


def check_rule_step(step, x) -> list[CheckResult]:
    out: list[CheckResult] = []
    target: sp.Derivative = step.data["target"]
    rep = step.data["replacement"]
    rule = step.data["rule"]
    g = target.expr

    fits = _rule_fits(rule, g, x)
    out.append(CheckResult(step.id, "rule matches the expression", PASS if fits else FAIL,
                           f"{step.operation} applies to {to_text(g)}" if fits
                           else f"{step.operation} does NOT apply to {to_text(g)}"))

    found = any(node == target for node in sp.preorder_traversal(step.before))
    out.append(CheckResult(step.id, "rule applied to a term in the expression", PASS if found else FAIL,
                           "the rewritten d/dx[…] appears in the previous line" if found
                           else "the rewritten d/dx[…] is not in the previous line"))

    status, detail = check_equal(rep.doit(), sp.diff(g, x), [x])
    out.append(CheckResult(step.id, "local rewrite vs sympy.diff", status, detail))

    with sp.evaluate(False):
        expected_after = step.before.xreplace({target: rep})
    same = expected_after == step.after
    out.append(CheckResult(step.id, "only this term changed", PASS if same else FAIL,
                           "after = before with just this d/dx[…] replaced" if same
                           else "other parts of the expression changed too"))

    status, detail = check_equal(step.before.doit(), step.after.doit(), [x])
    out.append(CheckResult(step.id, "whole line still equal", status, detail))
    return out


def finite_difference_check(f: sp.Expr, fprime: sp.Expr, x: sp.Symbol, seed: int = 1004) -> CheckResult:
    """Compare f′ with mpmath's numerical derivative of f at random points."""
    ff = sp.lambdify(x, f, "mpmath")
    fp = sp.lambdify(x, fprime, "mpmath")
    rng = random.Random(seed)
    used, worst = 0, mpmath.mpf(0)
    with mpmath.workdps(DPS):
        for low, high in ((-3, 3), (0.05, 4)):
            tries = 0
            while used < MIN_POINTS + 2 and tries < 300:
                tries += 1
                x0 = mpmath.mpf(rng.uniform(low, high))
                try:
                    exact = mpmath.mpmathify(fp(x0))
                    numeric = mpmath.diff(ff, x0)
                    if mpmath.im(ff(x0)) != 0:
                        continue
                except (ZeroDivisionError, ValueError, TypeError, OverflowError):
                    continue
                if not (mpmath.isfinite(exact) and mpmath.isfinite(numeric)) or mpmath.im(exact) != 0:
                    continue
                err = abs(exact - numeric) / max(1, abs(exact))
                if err > mpmath.mpf("1e-15"):
                    return CheckResult("final", "finite-difference check", FAIL,
                                       f"at {x}={mpmath.nstr(x0, 8)}: formula gives {mpmath.nstr(exact, 12)}, "
                                       f"numerical slope is {mpmath.nstr(numeric, 12)}")
                worst = max(worst, err)
                used += 1
            if used >= MIN_POINTS + 2:
                break
    if used < MIN_POINTS:
        return CheckResult("final", "finite-difference check", INCONCLUSIVE, f"only {used} usable points")
    return CheckResult("final", "finite-difference check", PASS,
                       f"numerical slope of f matches f′ at {used} random points (max rel. error {mpmath.nstr(worst, 3)})")


def verify_derivative(solution: Solution) -> list[CheckResult]:
    out: list[CheckResult] = []
    x = solution.facts["variable"]
    f = solution.facts["function"]
    steps = solution.steps
    first = steps[0]
    ok = first.kind == SETUP and first.before == solution.problem.function and first.after == sp.Derivative(f, x)
    out.append(CheckResult(first.id, "matches the given function", PASS if ok else FAIL,
                           f"starts from d/d{x}[{to_text(f)}], the confirmed problem" if ok
                           else "starting expression differs from problem.json"))
    for prev, cur in zip(steps, steps[1:]):
        same = prev.after == cur.before
        out.append(CheckResult(cur.id, "continues from previous step", PASS if same else FAIL,
                               f"starts from the result of {prev.id}" if same
                               else f"does not start from the result of {prev.id}"))
    for s in steps[1:]:
        if s.kind == DERIVATIVE_RULE:
            out += check_rule_step(s, x)
        elif s.kind == ALGEBRA:
            status, detail = check_equal(s.before, s.after, [x])
            out.append(CheckResult(s.id, "algebra step is an equality", status, detail))

    ans = solution.answer
    leftover = ans.has(sp.Derivative)
    out.append(CheckResult("final", "no d/dx left in the answer", FAIL if leftover else PASS,
                           "answer is fully differentiated" if not leftover else "answer still contains d/dx[…]"))
    out.append(CheckResult("final", "last step is the answer", PASS if steps[-1].after == ans else FAIL,
                           "the final line is the reported answer" if steps[-1].after == ans
                           else "the reported answer is not the final line"))
    status, detail = check_equal(ans, sp.diff(f, x), [x])
    out.append(CheckResult("final", "second method: sympy.diff", status, detail))
    out.append(finite_difference_check(f, ans, x))
    return out


# ---------------------------------------------------------------- limits
def _approach(f, x, a, side, L) -> CheckResult:
    """Evaluate f closer and closer to a (from one side) at 60 digits; values must settle at L."""
    import mpmath

    fn = sp.lambdify(x, f, "mpmath")
    label = {"+": "from the right", "-": "from the left"}[side]
    with mpmath.workdps(60):
        if a.is_infinite:
            pts = [mpmath.mpf(10) ** k * (1 if a > 0 else -1) for k in (3, 4, 5, 6, 8, 10, 12)]
        else:
            a0 = mpmath.mpf(sp.N(a, 70))
            pts = [a0 + (1 if side == "+" else -1) * mpmath.mpf(10) ** -k for k in (3, 4, 5, 6, 8, 10, 12)]
        try:
            vals = [fn(p_) for p_ in pts]
        except (ZeroDivisionError, ValueError, TypeError) as exc:
            return CheckResult("final", f"numeric approach {label}", INCONCLUSIVE, f"could not evaluate: {exc}")
        vals = [mpmath.re(v) if abs(mpmath.im(v)) < 1e-40 else None for v in vals]
        if any(v is None for v in vals):
            return CheckResult("final", f"numeric approach {label}", INCONCLUSIVE, "f is not real there")
        shown = ", ".join(mpmath.nstr(v, 8) for v in vals[-3:])
        if L.is_infinite:
            sign = 1 if L > 0 else -1
            ok_ = all(sign * v > 0 for v in vals[-3:]) and abs(vals[-1]) > 1e4 and abs(vals[-1]) > abs(vals[0])
            return CheckResult("final", f"numeric approach {label}", PASS if ok_ else FAIL,
                               f"values {shown} grow toward {to_text(L)}" if ok_ else f"values {shown} don't go to {to_text(L)}")
        Lf = mpmath.mpf(sp.N(L, 70))
        errs = [abs(v - Lf) for v in vals]
        ok_ = errs[-1] < mpmath.mpf("1e-4") * max(1, abs(Lf)) and errs[-1] <= errs[0]
        return CheckResult("final", f"numeric approach {label}", PASS if ok_ else FAIL,
                           f"f → {shown}… approaches {to_text(L)}" if ok_ else f"values {shown} don't approach {to_text(L)}")


def check_limit_step(step) -> list[CheckResult]:
    from tutor.solvers.calculus.limits import continuous_at
    from tutor.verify.common import ok

    out: list[CheckResult] = []
    rule = step.data.get("rule")
    x, a, d = step.data["x"], step.data["a"], step.data["dir"]
    if rule == "rewrite":
        g1, g2 = step.before.args[0], step.after.args[0]
        st, det = check_equal(g1, g2, [x], domain=step.data.get("domain"))
        out.append(CheckResult(step.id, "rewrite keeps the function the same near a", st, det))
    elif rule == "lhospital":
        num, den = step.data["num"], step.data["den"]
        g1, g2 = step.before.args[0], step.after.args[0]
        st, det = check_equal(g1, num / den, [x])
        out.append(CheckResult(step.id, "f/g really is the expression", st, det))
        side = "+" if d in ("+-", "+") else "-"
        sides = ["+", "-"] if (d == "+-" and not a.is_infinite) else [side]
        for sd in sides:
            ln_, ld_ = sp.limit(num, x, a, sd), sp.limit(den, x, a, sd)
            form_ok = (ln_ == 0 and ld_ == 0) or (ln_.is_infinite and ld_.is_infinite)
            out.append(ok(step.id, f"form is 0/0 or ∞/∞ ({'right' if sd == '+' else 'left'})", form_ok,
                          f"top → {to_text(ln_)}, bottom → {to_text(ld_)}", f"top → {to_text(ln_)}, bottom → {to_text(ld_)}: "
                          "L'Hôpital does not apply"))
        st, det = check_equal(g2, sp.diff(num, x) / sp.diff(den, x), [x])
        out.append(CheckResult(step.id, "f′/g′ computed correctly", st, det))
    elif rule == "substitute":
        g = step.data["g"]
        out.append(ok(step.id, f"continuous at {x} = {to_text(a)}", continuous_at(g, x, a, d),
                      "direct substitution is allowed"))
        st, det = check_equal(step.after, g.subs(x, a))
        out.append(CheckResult(step.id, "substituted value", st, det))
    elif rule in ("term_limits", "evaluate", "infinite"):
        g = step.data["g"]
        if rule != "infinite" and d == "+-" and not a.is_infinite:
            d = "+"
        sides = ["+", "-"] if (d == "+-" and not a.is_infinite) else [d if d != "+-" else "+"]
        vals = {sd: sp.limit(g, x, a, sd) for sd in sides}
        target = step.after
        if rule == "infinite" and "sides" in step.data:
            good = all(vals[sd] == step.data["sides"][sd] for sd in sides)
            out.append(ok(step.id, "one-sided limits", good, ", ".join(f"{sd}: {to_text(v)}" for sd, v in vals.items())))
        else:
            st, det = check_equal(target, vals[sides[0]]) if not vals[sides[0]].is_infinite else \
                (PASS if target == vals[sides[0]] else FAIL, f"SymPy: {to_text(vals[sides[0]])}")
            out.append(CheckResult(step.id, "limit of this line", st, det))
    return out


def verify_limit(solution: Solution) -> list[CheckResult]:
    from tutor.solvers.calculus.limits import DNE
    from tutor.steps import LIMIT_STEP
    from tutor.verify.common import chain_checks, equal, ok

    f = solution.facts
    x, a, d, fn = f["variable"], f["point"], f["direction"], f["function"]
    out = chain_checks(solution)
    for s in solution.steps:
        if s.kind == LIMIT_STEP:
            out += check_limit_step(s)
        elif s.kind == "algebra":
            out.append(equal(s.id, "arithmetic", s.before, s.after))
    ans = solution.answer
    sides = ["+", "-"] if (d == "+-" and not a.is_infinite) else [d]
    vals = {sd: sp.limit(fn, x, a, sd) for sd in sides}
    if ans == DNE:
        out.append(ok("final", "one-sided limits differ (SymPy)", len(set(vals.values())) > 1,
                      f"right: {to_text(vals.get('+'))}, left: {to_text(vals.get('-'))}"))
        for sd in sides:
            out.append(_approach(fn, x, a, sd, vals[sd]))
        return out
    for sd in sides:
        same = (ans == vals[sd]) if (ans.is_infinite or vals[sd].is_infinite) else check_equal(ans, vals[sd])[0] == PASS
        out.append(ok("final", f"second method: SymPy limit ({'right' if sd == '+' else 'left'})", same,
                      f"SymPy also gives {to_text(vals[sd])}", f"SymPy gives {to_text(vals[sd])}"))
        out.append(_approach(fn, x, a, sd, ans))
    return out


# ---------------------------------------------------------------- implicit, tangent lines, related rates
def _check_d_both_sides(solution) -> list[CheckResult]:
    from tutor.verify.common import ok

    out = []
    for s in solution.steps:
        if s.data.get("rule") == "d_both_sides":
            var = s.after.lhs.variables[0]
            good = (s.after.lhs == sp.Derivative(s.before.lhs, var, evaluate=False)
                    and s.after.rhs == sp.Derivative(s.before.rhs, var, evaluate=False))
            out.append(ok(s.id, "the same d/d" + str(var) + " applied to both sides", good,
                          "both sides differentiated, nothing else changed"))
    return out


def verify_implicit(solution: Solution) -> list[CheckResult]:
    from tutor.verify.common import equal, ok, verify_steps

    f = solution.facts
    x, yf, ysym = f["x"], f["y"], f["ysym"]
    out = verify_steps(solution, [x]) + _check_d_both_sides(solution)
    D = sp.Derivative(yf, x)
    dydx = [s for s in solution.steps if s.kind == "equation" and isinstance(s.after, sp.Equality)
            and s.after.lhs == D][-1].after.rhs
    Y = sp.Symbol(f"{yf.func.__name__}_0", real=True)
    F = (f["lhs"] - f["rhs"]).xreplace({ysym: Y})
    formula = -sp.diff(F, x) / sp.diff(F, Y)
    out.append(equal("final", "second method: dy/dx = −Fₓ/F_y", dydx.xreplace({yf: Y}), formula, [x, Y]))
    if "point" in f:
        x0, y0 = f["point"]
        on = sp.simplify(F.subs({x: x0, Y: y0})) == 0
        out.append(ok("final", "the point is on the curve", on, f"({to_text(x0)}, {to_text(y0)}) satisfies the equation"))
        out.append(equal("final", "slope at the point", f["slope"], formula.subs({x: x0, Y: y0})))
        if "line" in f:
            line = f["line"]
            if line.lhs == ysym:
                out.append(equal("final", "line passes through the point", line.rhs.subs(x, x0), y0))
                out.append(equal("final", "line has that slope", sp.diff(line.rhs, x), f["slope"]))
    return out


def verify_tangent(solution: Solution) -> list[CheckResult]:
    from tutor.verify.common import equal, ok, verify_steps

    f = solution.facts
    x, fn, a = f["x"], f["f"], f["a"]
    out = verify_steps(solution, [x])
    true_slope = sp.diff(fn, x).subs(x, a)
    out.append(equal("final", "f(a) by direct evaluation", f["fa"], fn.subs(x, a)))
    line = f["line"]
    if line.lhs == x:
        out.append(ok("final", "vertical line is correct", (true_slope == 0) if f["normal"] else true_slope.is_infinite,
                      "slope check for a vertical line"))
        return out
    m = sp.diff(line.rhs, x)
    expected = -1 / true_slope if f["normal"] else true_slope
    out.append(equal("final", "slope: second method (SymPy diff)", m, expected))
    out.append(equal("final", "line passes through (a, f(a))", line.rhs.subs(x, a), fn.subs(x, a)))
    import mpmath

    fl = sp.lambdify(x, fn, "mpmath")
    with mpmath.workdps(40):
        num_slope = mpmath.diff(fl, mpmath.mpf(sp.N(a, 45)))
    target = -1 / num_slope if f["normal"] else num_slope
    out.append(ok("final", "finite-difference slope", abs(complex(sp.N(m)) - complex(target)) < 1e-12 * max(1, abs(target)),
                  f"numerical slope {mpmath.nstr(target, 12)}"))
    return out


def verify_logdiff(solution: Solution) -> list[CheckResult]:
    from tutor.verify.common import equal, verify_steps

    x, fn = solution.facts["x"], solution.facts["f"]
    out = verify_steps(solution, [x]) + _check_d_both_sides(solution)
    dom = solution.facts.get("domain", (sp.Integer(0), sp.oo))
    out.append(equal("final", f"second method: SymPy diff ({x} > {to_text(dom[0])})", solution.answer,
                     sp.diff(fn, x), [x], domain=dom))
    out.append(finite_difference_check(fn, solution.answer, x))
    return out


def verify_related_rates(solution: Solution) -> list[CheckResult]:
    from tutor.verify.common import equal, ok, verify_steps

    f = solution.facts
    t, names, syms = f["t"], f["names"], f["syms"]
    out = verify_steps(solution, [t]) + _check_d_both_sides(solution)
    for s in solution.steps:
        if s.data.get("rule") == "plug_in":
            deq = s.data["from_eq"]
            prev_eq = [st for st in solution.steps if st.after == deq]
            out.append(ok(s.id, "substitutes into the differentiated equation", bool(prev_eq),
                          "uses the equation from the previous derivation"))
            vals_f = {s.data["funcs"][n]: v for n, v in f["values"].items()}
            for side_b, side_a in ((deq.lhs, s.after.lhs), (deq.rhs, s.after.rhs)):
                st_, det_ = check_equal(side_b.xreplace(s.data["subs"]).xreplace(vals_f), side_a)
                out.append(CheckResult(s.id, "values substituted correctly", st_, det_))
    rel = f["lhs"] - f["rhs"]
    vals = {syms[n]: v for n, v in f["values"].items()}
    out.append(ok("final", "values satisfy the relation", sp.simplify(rel.subs(vals)) == 0,
                  "the quantities at that moment fit the equation"))
    funcs = {syms[n]: sp.Function("Q" + n)(t) for n in names}
    drel = sp.diff(rel.xreplace(funcs), t)
    reps = {}
    for n in names:
        dn = sp.Derivative(funcs[syms[n]], t)
        if n in f["rates"]:
            reps[dn] = f["rates"][n]
        elif n == f["target"]:
            reps[dn] = sp.Symbol("unknown_rate")
    eq = drel.xreplace(reps).xreplace({funcs[syms[n]]: f["values"][n] for n in names if n in f["values"]})
    sol = sp.solve(eq, sp.Symbol("unknown_rate"))
    out.append(ok("final", "second method: SymPy differentiates the relation", len(sol) == 1, "one solution"))
    if len(sol) == 1:
        out.append(equal("final", "rate matches the second method", solution.answer, sol[0]))
    return out
