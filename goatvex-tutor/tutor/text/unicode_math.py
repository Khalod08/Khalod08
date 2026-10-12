"""Readable Unicode math for the terminal (never raw LaTeX).

    >>> to_text(3*x**4 - 5*x**2 + sp.sqrt(x))
    '3x⁴ − 5x² + √x'
"""

from __future__ import annotations

import re

import sympy as sp
from sympy.core.function import AppliedUndef
from sympy.printing.str import StrPrinter

SUPERSCRIPT = str.maketrans("0123456789-()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁽⁾")
SUBSCRIPT = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

_FUNC_NAMES = {"log": "ln", "asin": "arcsin", "acos": "arccos", "atan": "arctan"}


def sub(n: int | str) -> str:
    return str(n).translate(SUBSCRIPT)


def sup(n: int | str) -> str:
    return str(n).translate(SUPERSCRIPT)


class _UnicodePrinter(StrPrinter):
    def _needs_parens(self, e: sp.Basic) -> bool:
        return not (e.is_Atom or isinstance(e, sp.Function)) or (e.is_Number and e < 0)

    def _print_Pow(self, expr, rational=False):
        b, e = expr.as_base_exp()
        if e == sp.Rational(1, 2):
            inner = self._print(b)
            return f"√{inner}" if b.is_Atom else f"√({inner})"
        if e == sp.Rational(-1, 2):
            inner = self._print(b)
            return f"1/√{inner}" if b.is_Atom else f"1/√({inner})"
        if e.is_Integer and e < 0:
            return super()._print_Pow(expr, rational)
        base = self._print(b)
        if self._needs_parens(b):
            base = f"({base})"
        if b == sp.E:
            base = "e"
        if e.is_Integer:
            return base + sup(e)
        if e.is_Symbol:
            return f"{base}^{self._print(e)}"
        return f"{base}^({self._print(e)})"

    # Intermediate derivative lines are built unevaluated in a deliberate order
    # (u′v + uv′, term by term); keep it. Ordinary expressions use SymPy's order.
    def _print_Add(self, expr, order=None):
        return self._with_order(expr, super()._print_Add)

    def _print_Mul(self, expr):
        if _is_unevaluated_mul(expr):
            return self._print_hand_mul(expr)
        return self._with_order(expr, super()._print_Mul)

    def _print_hand_mul(self, expr):
        """A product built with evaluate=False: show every factor, e.g. 3·1 or 2·(−3)."""
        args = list(expr.args)
        prefix = ""
        if all(a.is_Number for a in args):  # 3·1 + (−1)·1: keep every number visible
            return "·".join(f"({self._print(a)})" if a < 0 or not a.is_Integer else self._print(a) for a in args)
        if len(args) > 1 and args[0] == -1:
            prefix, args = "-", args[1:]
        elif len(args) > 1 and args[0].is_Number and args[0] < 0:
            prefix, args = "-", [-args[0]] + args[1:]
        dens = [a.base for a in args if a.is_Pow and a.exp == -1]
        args = [a for a in args if not (a.is_Pow and a.exp == -1)] or [sp.Integer(1)]
        if dens and len(args) == 1:
            num = self._print(args[0])
            if isinstance(args[0], sp.Add):
                num = f"({num})"
            den = "·".join(self._print(d) if (d.is_Atom or isinstance(d, sp.Function)) and not (d.is_Number and d < 0)
                           else f"({self._print(d)})" for d in dens)
            return f"{prefix}{num}/{den}"
        if dens:
            den = "·".join(self._print(d) if d.is_Atom and not (d.is_Number and d < 0) else f"({self._print(d)})"
                           for d in dens)
            return f"{prefix}(" + "·".join(self._print(a) for a in args) + f")/{den}"
        parts = []
        for k, a in enumerate(args):
            t = self._print(a)
            needs = isinstance(a, (sp.Add, sp.Mul)) and not _is_unevaluated_mul(a) and a.is_Add \
                or (a.is_Number and a < 0) or (a.is_Rational and not a.is_Integer) \
                or (isinstance(a, sp.Mul) and _is_unevaluated_mul(a) and k > 0) \
                or isinstance(a, sp.Add)
            parts.append(f"({t})" if needs else t)
        return prefix + "·".join(parts)

    def _with_order(self, expr, print_fn):
        saved = self._settings["order"]
        self._settings["order"] = "none" if _built_by_hand(expr) else None
        try:
            return print_fn(expr)
        finally:
            self._settings["order"] = saved

    def _print_exp(self, expr):
        arg = expr.args[0]
        if arg.is_Integer and arg > 0:
            return "e" + sup(arg)
        if arg.is_Symbol:
            return f"e^{self._print(arg)}"
        return f"e^({self._print(arg)})"

    def _print_Exp1(self, expr):
        return "e"

    def _print_Pi(self, expr):
        return "π"


    def _print_Derivative(self, expr):
        var = self._print(expr.variables[0])
        order = len(expr.variables)
        if isinstance(expr.expr, AppliedUndef):  # dy/dx, dV/dt, d²y/dx²
            name = expr.expr.func.__name__
            if order == 1:
                return f"d{name}/d{var}"
            return f"d{sup(order)}{name}/d{var}{sup(order)}"
        inner = self._print(expr.expr)
        if order > 1:
            return f"d{sup(order)}/d{var}{sup(order)}[{inner}]"
        return f"d/d{var}[{inner}]"

    def _print_Function(self, expr):
        if isinstance(expr, AppliedUndef):
            return expr.func.__name__
        name = _FUNC_NAMES.get(expr.func.__name__, expr.func.__name__)
        args = ", ".join(self._print(a) for a in expr.args)
        return f"{name}({args})"

    def _print_Abs(self, expr):
        return f"|{self._print(expr.args[0])}|"

    def _print_Infinity(self, expr):
        return "∞"

    def _print_NegativeInfinity(self, expr):
        return "-∞"

    def _print_ComplexInfinity(self, expr):
        return "∞ (undefined)"

    def _print_Relational(self, expr):
        op = {"==": "=", "!=": "≠", "<=": "≤", ">=": "≥", "<": "<", ">": ">"}[expr.rel_op]
        return f"{self._print(expr.lhs)} {op} {self._print(expr.rhs)}"

    _print_Equality = _print_Relational
    _print_Unequality = _print_Relational

    def _print_Integral(self, expr):
        f = self._print(expr.function)
        if not (expr.function.is_Atom or isinstance(expr.function, sp.Function)) and not expr.function.is_Pow:
            f = f"({f})"
        parts = []
        for lim in expr.limits:
            var = self._print(lim[0])
            if len(lim) == 3:
                a, b = lim[1], lim[2]
                if a.is_Integer and b.is_Integer and a >= 0 and b >= 0:
                    parts.append((f"∫{sub(a)}{sup(b)}", var))
                else:
                    parts.append((f"∫[{self._print(a)}→{self._print(b)}]", var))
            else:
                parts.append(("∫", var))
        signs = " ".join(p for p, _ in parts)
        ds = " ".join(f"d{v}" for _, v in parts)
        return f"{signs} {f} {ds}"

    def _print_Limit(self, expr):
        e, z, z0, d = expr.args
        # GoatVex always builds two-sided limits with dir="+-"; "+"/"-" mean one-sided.
        side = ""
        if not z0.is_infinite and str(d) in ("+", "-"):
            side = "⁺" if str(d) == "+" else "⁻"
        return f"lim({self._print(z)}→{self._print(z0)}{side}) {self._print(e)}"

    def _print_Determinant(self, expr):
        m = expr.arg
        rows = "; ".join(" ".join(self._print(m[i, j]) for j in range(m.cols)) for i in range(m.rows))
        return f"det[{rows}]"

    def _print_MatrixBase(self, expr):
        return vec_text(expr) if expr.cols == 1 else matrix_text(expr)

    _print_MutableDenseMatrix = _print_MatrixBase
    _print_ImmutableDenseMatrix = _print_MatrixBase

    def _print_Rational(self, expr):
        return f"{expr.p}/{expr.q}"

    def _print_ImaginaryUnit(self, expr):
        return "i"


def _is_unevaluated_mul(expr: sp.Basic) -> bool:
    """A Mul that SymPy would have simplified (e.g. 3·1, 2·(−3), 5·(3x²))."""
    if not isinstance(expr, sp.Mul):
        return False
    try:
        return sp.Mul(*expr.args) != expr or sum(1 for a in expr.args if a.is_Number) > 1
    except Exception:
        return False


def _built_by_hand(expr: sp.Basic) -> bool:
    """True for Add/Mul nodes built with evaluate=False (or holding d/dx[...], ∫, lim)."""
    if expr.has(sp.Derivative, sp.Integral, sp.Limit):
        return True
    try:
        return expr.func(*expr.args).args != expr.args
    except Exception:
        return False


def _tidy(s: str) -> str:
    s = s.replace("**", "^")
    # multiplication: keep 3x² and 3√x compact, use · elsewhere
    s = re.sub(r"(?<=[0-9])\*(?=[A-Za-zα-ωπ√(])", "", s)
    s = s.replace("*", "·")
    s = s.replace(" - ", " − ").replace("-", "−")
    return s


def to_text(obj) -> str:
    """Render a SymPy expression or matrix as readable Unicode."""
    if isinstance(obj, sp.MatrixBase):
        return matrix_text(obj)
    if isinstance(obj, (list, tuple)):
        return ", ".join(vec_text(o) if isinstance(o, sp.MatrixBase) and o.cols == 1 else to_text(o) for o in obj)
    if isinstance(obj, dict):
        return "; ".join(f"{to_text(k)}: {to_text(v)}" for k, v in obj.items())
    if isinstance(obj, str):
        return obj
    # order="none" keeps the term order the solver built (matters for
    # unevaluated intermediate steps such as 5·(3x²)).
    return _tidy(_UnicodePrinter()._print(sp.sympify(obj)))


def vec_text(v) -> str:
    """Inline vector: (1, −2, 3)."""
    entries = list(v) if isinstance(v, sp.MatrixBase) else list(v)
    return "(" + ", ".join(to_text(e) for e in entries) + ")"


def matrix_text(m: sp.MatrixBase, augmented_at: int | None = None) -> str:
    """Multi-line bracketed matrix. ``augmented_at`` draws a bar before that column."""
    cells = [[to_text(m[i, j]) for j in range(m.cols)] for i in range(m.rows)]
    widths = [max(len(cells[i][j]) for i in range(m.rows)) for j in range(m.cols)]
    lines = []
    for i in range(m.rows):
        parts = []
        for j in range(m.cols):
            if augmented_at is not None and j == augmented_at:
                parts.append("│")
            parts.append(cells[i][j].rjust(widths[j]))
        if m.rows == 1:
            l, r = "[", "]"
        elif i == 0:
            l, r = "⎡", "⎤"
        elif i == m.rows - 1:
            l, r = "⎣", "⎦"
        else:
            l, r = "⎢", "⎥"
        lines.append(f"{l} {'  '.join(parts)} {r}")
    return "\n".join(lines)
