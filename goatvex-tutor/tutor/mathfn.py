"""Extra SymPy functions GoatVex needs.

RealRoot(u, n): the REAL n-th root for odd n, e.g. ∛(−8) = −2. SymPy's own
u**(1/3) is the principal complex root, so (−8)**(1/3) is not −2 and an
inverse such as f⁻¹(x) = (x + 1)**(1/3) would be wrong for x < −1. Textbooks
mean the real root, so the solver writes RealRoot and the verifier rewrites it
as sign(u)·|u|^(1/n), which it already knows how to prove things about.
"""

from __future__ import annotations

import sympy as sp


class RealRoot(sp.Function):
    nargs = 2

    @classmethod
    def eval(cls, u, n):
        if not (n.is_Integer and n > 0 and n % 2 == 1):
            raise ValueError("RealRoot needs an odd positive integer index")
        if n == 1:
            return u
        if u.is_number and u.is_real:
            return sp.real_root(u, n)
        if u.is_nonnegative:
            return u ** sp.Rational(1, n)
        return None

    def _eval_is_real(self):
        return self.args[0].is_real

    def _eval_rewrite_as_Abs(self, u, n, **kwargs):
        return sp.sign(u) * sp.Abs(u) ** sp.Rational(1, n)

    def _eval_derivative(self, s):
        u, n = self.args
        return sp.diff(u, s) / (n * RealRoot(u, n) ** (n - 1))

    def _eval_evalf(self, prec):
        return self.rewrite(sp.Abs)._eval_evalf(prec)

    def as_abs(self):
        return self.rewrite(sp.Abs)

    def _latex(self, printer):
        u, n = self.args
        return rf"\sqrt[{n}]{{{printer._print(u)}}}"

    def _sympystr(self, printer):
        u, n = self.args
        inner = printer._print(u)
        mark = {3: "∛", 5: "⁵√", 7: "⁷√"}.get(int(n), f"root{n}")
        return f"{mark}{inner}" if u.is_Atom else f"{mark}({inner})"

    def _numpycode(self, printer):
        return printer._print(self.rewrite(sp.Abs))

    def _mpmathcode(self, printer):
        return printer._print(self.rewrite(sp.Abs))

    def _pythoncode(self, printer):
        return printer._print(self.rewrite(sp.Abs))


def real_roots_rewrite(expr):
    """Replace every RealRoot by sign(u)·|u|^(1/n) (for checking and numerics)."""
    return expr.replace(lambda e: isinstance(e, RealRoot), lambda e: e.as_abs()) if expr.has(RealRoot) else expr


def to_real_roots(expr):
    """Turn u**(k/n) with odd n (and u not known ≥ 0) into RealRoot(u, n)**k."""
    def fix(e):
        b, ex = e.as_base_exp()
        if ex.is_Rational and not ex.is_Integer and ex.q % 2 == 1 and not b.is_nonnegative:
            return RealRoot(b, ex.q) ** ex.p
        return e
    return expr.replace(lambda e: e.is_Pow, fix)
