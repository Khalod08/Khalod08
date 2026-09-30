"""Are two expressions equal? Proven symbolically AND spot-checked numerically.

``check_equal`` returns PASS only when SymPy proves ``a − b = 0`` *and* at least
5 random points agree to high precision. A numeric disagreement is always a
FAIL (even if SymPy claimed equality). If SymPy cannot decide but the numbers
agree, the result is INCONCLUSIVE — which still blocks rendering.
"""

from __future__ import annotations

import random
from typing import Callable, Sequence

import mpmath
import sympy as sp

from tutor.verify.result import FAIL, INCONCLUSIVE, PASS

MIN_POINTS = 5
DPS = 40                 # mpmath working precision (decimal digits)
REL_TOL = mpmath.mpf("1e-25")


def symbolic_zero(expr: sp.Expr) -> bool | None:
    """True if ``expr`` is provably 0, False if provably nonzero, None if unknown."""
    expr = sp.sympify(expr)
    if isinstance(expr, sp.Derivative) or expr.has(sp.Derivative):
        expr = expr.doit()
    if expr == 0:
        return True
    # Only *sound* rewrites: nothing with force=True (those assume x > 0 and
    # would "prove" false identities such as ln(x²) = 2ln(x)).
    strategies: list[Callable[[sp.Expr], sp.Expr]] = [
        sp.expand, sp.cancel, sp.together, sp.simplify, sp.trigsimp,
        lambda e: sp.simplify(sp.expand_trig(e)),
        lambda e: sp.simplify(sp.expand_log(e)),
    ]
    for fn in strategies:
        try:
            if fn(expr) == 0:
                return True
        except Exception:
            continue
    try:
        verdict = expr.equals(0)
    except Exception:
        verdict = None
    return verdict


def _evaluator(expr: sp.Expr, symbols: Sequence[sp.Symbol]):
    expr = sp.sympify(expr)
    if expr.has(sp.Derivative):
        expr = expr.doit()
    f = sp.lambdify(list(symbols), expr, modules="mpmath")

    def ev(point):
        with mpmath.workdps(DPS):
            try:
                v = mpmath.mpmathify(f(*point))
            except (ZeroDivisionError, ValueError, TypeError, OverflowError):
                return None
            if not mpmath.isfinite(v):
                return None
            return v

    return ev


def random_points(symbols, rng: random.Random, low=-3.0, high=3.0):
    with mpmath.workdps(DPS):
        return [mpmath.mpf(rng.uniform(low, high)) for _ in symbols]


def numeric_agree(
    a: sp.Expr,
    b: sp.Expr,
    symbols: Sequence[sp.Symbol] | None = None,
    *,
    n: int = MIN_POINTS + 2,
    seed: int = 1104,
    domains: Sequence[tuple[float, float]] = ((-3.0, 3.0), (0.05, 4.0)),
) -> tuple[bool | None, str]:
    """Compare a and b at ``n`` random real points where both are finite.

    Returns (True, detail) if they agree everywhere tested, (False, detail) at the
    first disagreement, or (None, detail) if fewer than MIN_POINTS usable points
    were found (e.g. the expressions are only defined on a tiny domain).
    """
    a, b = sp.sympify(a), sp.sympify(b)
    if symbols is None:
        symbols = sorted((a.free_symbols | b.free_symbols), key=str)
    symbols = list(symbols)
    ea, eb = _evaluator(a, symbols), _evaluator(b, symbols)
    rng = random.Random(seed)
    used = []
    worst = mpmath.mpf(0)
    with mpmath.workdps(DPS):
        for low, high in domains:
            tries = 0
            while len(used) < n and tries < 300:
                tries += 1
                pt = random_points(symbols, rng, low, high) if symbols else []
                va, vb = ea(pt), eb(pt)
                if va is None or vb is None:
                    continue
                # Calculus here is over ℝ: if one side is real and the other is
                # not, the two expressions have different domains → disagreement.
                # If both are non-real (e.g. √x at x < 0) compare them as complex numbers.
                real_a = abs(mpmath.im(va)) <= REL_TOL * max(1, abs(va))
                real_b = abs(mpmath.im(vb)) <= REL_TOL * max(1, abs(vb))
                where = ", ".join(f"{s}={mpmath.nstr(p, 8)}" for s, p in zip(symbols, pt))
                if real_a != real_b:
                    return False, f"different domains at {where}: one side is real, the other is not"
                scale = max(mpmath.mpf(1), abs(va), abs(vb))
                err = abs(va - vb) / scale
                if err > REL_TOL:
                    return False, (f"differ at {where}: {mpmath.nstr(va, 12)} vs {mpmath.nstr(vb, 12)}")
                worst = max(worst, err)
                used.append(pt)
                if not symbols:
                    break
            if len(used) >= n or not symbols:
                break
    if not symbols:
        return (True, "constant values agree") if used else (None, "could not evaluate")
    if len(used) < MIN_POINTS:
        return None, f"only {len(used)} usable test points (need {MIN_POINTS})"
    return True, f"{len(used)} random points agree (max rel. error {mpmath.nstr(worst, 3)})"


def check_equal(a: sp.Expr, b: sp.Expr, symbols=None) -> tuple[str, str]:
    """Return (status, detail) for the claim a = b."""
    diff = sp.sympify(a) - sp.sympify(b)
    sym = symbolic_zero(diff)
    num, num_detail = numeric_agree(a, b, symbols)
    if num is False:
        return FAIL, f"numeric check failed: {num_detail}"
    if sym is False:
        return FAIL, "SymPy proves the two sides are different"
    if sym is True and num is True:
        return PASS, f"simplify(before − after) = 0; {num_detail}"
    if sym is True and num is None:
        return INCONCLUSIVE, f"simplify(before − after) = 0 but {num_detail}"
    return INCONCLUSIVE, f"SymPy could not prove equality; {num_detail}"
