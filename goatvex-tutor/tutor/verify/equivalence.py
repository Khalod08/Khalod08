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


UNEVALUATED = (sp.Derivative, sp.Determinant, sp.Sum, sp.Product)


def freeze_functions(expr):
    """Replace y(x) by a symbol Y and dy/dx by a symbol Y_1 (d²y/dx² by Y_2 …),
    so expressions from implicit differentiation can be compared and evaluated."""
    from sympy.core.function import AppliedUndef

    expr = sp.sympify(expr)
    reps = {}
    for d in expr.atoms(sp.Derivative):
        if isinstance(d.expr, AppliedUndef):
            reps[d] = sp.Symbol(f"{d.expr.func.__name__}_{len(d.variables)}", real=True)
    expr = expr.xreplace(reps)
    funcs = {f: sp.Symbol(f"{f.func.__name__}_0", real=True) for f in expr.atoms(AppliedUndef)}
    return expr.xreplace(funcs)


def evaluate_unevaluated(expr):
    """Carry out unevaluated d/dx[…], det[…], Σ and definite ∫ so values can be compared.

    Indefinite integrals are never evaluated here: they are only defined up to
    a constant and are checked by differentiation instead (verify/integrals.py).
    """
    expr = sp.sympify(expr)
    if expr.has(*UNEVALUATED):
        expr = expr.doit(integrals=False) if expr.has(sp.Integral) else expr.doit()
    definite = [i for i in expr.atoms(sp.Integral) if all(len(lim) == 3 for lim in i.limits)]
    if definite:
        expr = expr.xreplace({i: i.doit() for i in definite})
    return freeze_functions(expr)


def _zero_by_sign_regions(expr) -> bool | None:
    """Prove expr = 0 when it contains |g(x)| or sign(g(x)) (one real variable).

    Split ℝ at the real roots of every g; on each open interval g has a fixed
    sign s, so |g| = s·g and sign(g) = s. The expression must simplify to 0 on
    every interval (single points don't matter). Returns None if not applicable.
    """
    args = {a.args[0] for a in expr.atoms(sp.Abs, sp.sign)}
    syms = list(expr.free_symbols)
    if len(syms) != 1:
        return _zero_for_all_signs(expr, args)
    x = syms[0]
    cuts = set()
    for g in args:
        try:
            num, den = sp.fraction(sp.together(g))
            for part in (num, den):
                if part.has(x):
                    if not part.is_polynomial(x):
                        return _zero_for_all_signs(expr, args)
                    cuts |= {r for r in sp.Poly(part, x).real_roots()}
        except Exception:
            return None
    cuts = sorted(cuts, key=lambda r: float(r))
    edges = [None] + cuts + [None]
    for lo, hi in zip(edges, edges[1:]):
        if lo is None and hi is None:
            pt = sp.Integer(0)
        elif lo is None:
            pt = sp.floor(hi) - 1
        elif hi is None:
            pt = sp.ceiling(lo) + 1
        else:
            pt = (lo + hi) / 2
        reps = {}
        for g in args:
            sgn = sp.sign(sp.N(g.subs(x, pt), 30))
            if sgn == 0:
                return None
            reps[sp.Abs(g)] = sgn * g
            reps[sp.sign(g)] = sgn
        piece = expr.xreplace(reps)
        if piece.has(sp.Abs, sp.sign):
            return None
        if sp.simplify(piece) != 0:
            return None if sp.simplify(piece).equals(0) is None else False
    return True


def _zero_for_all_signs(expr, args) -> bool | None:
    """Sufficient test: replacing each |g| by s·g and sign(g) by s gives 0 for
    every choice of signs s = ±1, so expr = 0 wherever every g ≠ 0."""
    import itertools

    args = list(args)
    if len(args) > 4:
        return None
    for signs in itertools.product((1, -1), repeat=len(args)):
        reps = {}
        for g, sg in zip(args, signs):
            reps[sp.Abs(g)] = sg * g
            reps[sp.sign(g)] = sg
        piece = expr.xreplace(reps)
        if piece.has(sp.Abs, sp.sign) or sp.simplify(piece) != 0:
            return None
    return True


def symbolic_zero(expr: sp.Expr) -> bool | None:
    """True if ``expr`` is provably 0, False if provably nonzero, None if unknown."""
    expr = sp.sympify(expr)
    expr = evaluate_unevaluated(expr)
    if expr == 0:
        return True
    if expr.has(sp.Abs, sp.sign):
        by_region = _zero_by_sign_regions(expr)
        if by_region is not None:
            return by_region
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


def _reeval(e):
    if not e.args or isinstance(e, (sp.Symbol, sp.MatrixBase)):
        return e
    try:
        return e.func(*[_reeval(a) for a in e.args])
    except Exception:
        return e


def _ints_to_float(expr):
    """Integers → high-precision Floats, except exponents (keep x**2 an integer power)."""
    if expr.is_Integer:
        return sp.Float(expr, DPS + 10)
    if not expr.args or isinstance(expr, (sp.Symbol, sp.MatrixBase)):
        return expr
    if expr.is_Pow:
        b, e = expr.args
        return sp.Pow(_ints_to_float(b), e if e.is_Integer else _ints_to_float(e), evaluate=False)
    try:
        return expr.func(*[_ints_to_float(a) for a in expr.args], evaluate=False)
    except TypeError:
        return expr.func(*[_ints_to_float(a) for a in expr.args])


def _evaluator(expr: sp.Expr, symbols: Sequence[sp.Symbol]):
    expr = sp.sympify(expr)
    expr = evaluate_unevaluated(expr)
    # Re-evaluate structures built with evaluate=False first: printing nested unevaluated
    # powers like (x⁻¹)⁻¹ to Python code can go wrong (x**-1**-1 means x**(-1)).
    expr = _reeval(expr)
    # Turn every exact number into a 50-digit Float first: otherwise lambdify
    # computes things like (−5)**(−1) in ordinary double precision.
    expr = expr.xreplace({q: sp.Float(q, DPS + 10) for q in expr.atoms(sp.Rational) if not q.is_Integer
                          or abs(q) > 2**52})
    expr = _ints_to_float(expr)
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
    a, b = evaluate_unevaluated(a), evaluate_unevaluated(b)
    extra = (a.free_symbols | b.free_symbols) - set(symbols or [])
    symbols = list(symbols or []) + sorted(extra, key=str)
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


def check_equal(a: sp.Expr, b: sp.Expr, symbols=None, domain: tuple | None = None) -> tuple[str, str]:
    """Return (status, detail) for the claim a = b (equations: left = left and right = right)."""
    if isinstance(a, sp.Equality) and isinstance(b, sp.Equality):
        sl, dl = check_equal(a.lhs, b.lhs, symbols, domain=domain)
        sr, dr = check_equal(a.rhs, b.rhs, symbols, domain=domain)
        if FAIL in (sl, sr):
            return FAIL, f"left side: {dl}; right side: {dr}"
        if INCONCLUSIVE in (sl, sr):
            return INCONCLUSIVE, f"left side: {dl}; right side: {dr}"
        return PASS, f"both sides unchanged in value ({dl})"
    diff = sp.sympify(a) - sp.sympify(b)
    if domain is not None:
        # Only claimed on an interval (lo, hi) of the single variable: prove it with x = lo + p, p > 0
        # (or hi − p for (−∞, hi)), and sample only inside the interval.
        x = list(symbols)[0]
        lo, hi = domain
        p = sp.Symbol("p_", positive=True)
        # x = lo + p proves it for all x > lo; x = hi − p for all x < hi. Either one covers (lo, hi).
        sym = None
        if lo != -sp.oo:
            sym = symbolic_zero(diff.xreplace({x: lo + p}))
        if sym is not True and hi != sp.oo:
            sym2 = symbolic_zero(diff.xreplace({x: hi - p}))
            sym = True if sym2 is True else (sym if sym is not None else sym2)
        lo_f = float(lo) if lo != -sp.oo else float(hi) - 4
        hi_f = float(hi) if hi != sp.oo else lo_f + 4
        num, num_detail = numeric_agree(a, b, symbols, domains=((lo_f + 1e-3, hi_f - 1e-3),))
    else:
        sym = symbolic_zero(diff)
        num, num_detail = numeric_agree(a, b, symbols)
    if num is False:
        return FAIL, f"numeric check failed: {num_detail}"
    if sym is False and num is True:
        return INCONCLUSIVE, f"SymPy says the sides differ but {num_detail}; treating as unproven"
    if sym is False:
        return FAIL, "SymPy proves the two sides are different"
    if sym is True and num is True:
        return PASS, f"simplify(before − after) = 0; {num_detail}"
    if sym is True and num is None:
        return INCONCLUSIVE, f"simplify(before − after) = 0 but {num_detail}"
    return INCONCLUSIVE, f"SymPy could not prove equality; {num_detail}"
