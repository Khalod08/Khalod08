"""Readable Unicode math for the terminal (never raw LaTeX).

    >>> to_text(3*x**4 - 5*x**2 + sp.sqrt(x))
    '3x⁴ − 5x² + √x'
"""

from __future__ import annotations

import re

import sympy as sp
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
        return self._with_order(expr, super()._print_Mul)

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

    def _print_Function(self, expr):
        name = _FUNC_NAMES.get(expr.func.__name__, expr.func.__name__)
        args = ", ".join(self._print(a) for a in expr.args)
        return f"{name}({args})"

    def _print_Derivative(self, expr):
        var = self._print(expr.variables[0])
        inner = self._print(expr.expr)
        return f"d/d{var}[{inner}]"

    def _print_Rational(self, expr):
        return f"{expr.p}/{expr.q}"

    def _print_ImaginaryUnit(self, expr):
        return "i"


def _built_by_hand(expr: sp.Basic) -> bool:
    """True for Add/Mul nodes built with evaluate=False (or holding d/dx[...])."""
    if expr.has(sp.Derivative):
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
        return ", ".join(to_text(o) for o in obj)
    # order="none" keeps the term order the solver built (matters for
    # unevaluated intermediate steps such as 5·(3x²)).
    return _tidy(_UnicodePrinter()._print(sp.sympify(obj)))


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
