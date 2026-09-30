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
