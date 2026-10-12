"""Matrix arithmetic (sums, scalar multiples, products, transposes, powers).

The expression (e.g. "2A - B^T", "AB", "A^2 + I") is evaluated one operation
at a time, innermost first. A product gets two steps: each entry written as
(row i)·(column j), then the arithmetic. Undefined operations (size mismatch)
are reported, not guessed.
"""

from __future__ import annotations

import re

import sympy as sp
from sympy.parsing.sympy_parser import implicit_multiplication_application, parse_expr, standard_transformations

from tutor.errors import ProblemFormatError, UnsupportedProblem
from tutor.parse.schema import Problem, parse_matrix
from tutor.steps import ALGEBRA, Solution, Step
from tutor.text.unicode_math import sub, sup

_T = standard_transformations + (implicit_multiplication_application,)


def matrices(p: Problem) -> dict[str, sp.Matrix]:
    mats = p.given["matrices"]
    if not isinstance(mats, dict) or not mats:
        raise ProblemFormatError("'matrices' must map names like 'A' to matrices")
    out = {}
    for name, rows in mats.items():
        if not re.fullmatch(r"[A-HJ-Z]", name):
            raise ProblemFormatError(f"matrix names must be single capital letters (not I), got {name!r}")
        out[name] = parse_matrix(rows)
    return out


Tr = sp.Function("Tr")  # transpose marker used while parsing


def _mark_transposes(t: str) -> str:
    """Rewrite X^T and (…)^T as Tr(X) / Tr(…) so the parser can read them."""
    while "^T" in t:
        k = t.index("^T")
        if t[k - 1] == ")":
            depth, j = 0, k - 1
            while j >= 0:
                depth += t[j] == ")"
                depth -= t[j] == "("
                if depth == 0:
                    break
                j -= 1
            t = t[:j] + "Tr" + t[j:k] + t[k + 2:]
        else:
            t = t[:k - 1] + f"Tr({t[k - 1]})" + t[k + 2:]
    return t


def parse_matrix_expression(text: str, mats: dict[str, sp.Matrix]):
    """Parse into a tree of non-commuting symbols (order of products is kept)."""
    t = text.replace("ᵀ", "^T").replace("−", "-").replace("·", "*").replace(" ", "")
    t = _mark_transposes(t).replace("^", "**")
    syms = {n: sp.Symbol(n, commutative=False) for n in mats}
    syms["I"] = sp.Symbol("I", commutative=False)
    syms["Tr"] = Tr
    try:
        expr = parse_expr(t, local_dict=syms, transformations=_T, evaluate=False)
    except Exception as exc:
        raise ProblemFormatError(f"could not read the matrix expression {text!r}: {exc}") from exc
    unknown = {str(a) for a in expr.free_symbols} - set(mats) - {"I"}
    if unknown:
        raise ProblemFormatError(f"the expression uses {', '.join(sorted(unknown))}, which are not given")
    return expr, syms


def label(node) -> str:
    """Readable label for a sub-expression, e.g. 2A, Bᵀ, AB, 2A − Bᵀ."""
    if isinstance(node, sp.Symbol):
        return node.name
    if node.is_Number:
        return sp.sstr(node)
    if isinstance(node, sp.Function) and node.func == Tr:
        inner = node.args[0]
        return (label(inner) if isinstance(inner, sp.Symbol) else f"({label(inner)})") + "ᵀ"
    if node.is_Pow:
        b = node.base
        return (label(b) if isinstance(b, sp.Symbol) else f"({label(b)})") + sup(node.exp)
    if node.is_Mul:
        out = ""
        for a in node.args:
            if a == -1:
                out += "−"
            elif a.is_Number:
                out += sp.sstr(a)
            else:
                out += label(a) if not a.is_Add else f"({label(a)})"
        return out
    if node.is_Add:
        out = ""
        for k, a in enumerate(node.args):
            t = label(a)
            if k == 0:
                out = t
            elif t.startswith("−"):
                out += " − " + t[1:]
            else:
                out += " + " + t
        return out
    return str(node)


def solve(p: Problem) -> Solution:
    mats = matrices(p)
    expr, syms = parse_matrix_expression(p.given["expression"], mats)
    values = {n: sp.ImmutableMatrix(m) for n, m in mats.items()}
    sizes = {m.rows for m in mats.values() if m.is_square}
    steps: list[Step] = []
    k = 1

    def add(before, op, after, why, data=None):
        nonlocal k
        steps.append(Step(id=f"s{k}", kind=ALGEBRA, before=before, operation=op, after=after, justification=why,
                          data={"chain": False, **(data or {})}))
        k += 1

    def ev(node):
        if node.is_Number:
            return node
        if isinstance(node, sp.Symbol):
            if node.name == "I":
                if len(sizes) != 1:
                    raise ProblemFormatError("I (identity) is ambiguous here; give its size as a matrix")
                return sp.ImmutableMatrix(sp.eye(next(iter(sizes))))
            return values[node.name]
        lab = label(node)
        if isinstance(node, sp.Function) and node.func == Tr:
            m = ev(node.args[0])
            res = sp.ImmutableMatrix(m.T)
            add(sp.Transpose(m), f"Compute {lab}", res, "The transpose turns rows into columns.")
            return res
        if node.is_Pow:
            base = ev(node.base)
            n = node.exp
            if not (n.is_Integer and n >= 1):
                raise UnsupportedProblem("only positive whole-number powers are supported (use the inverse type for A⁻¹)")
            if not base.is_square:
                raise _Undefined(f"{lab} is not defined: only square matrices can be raised to a power.")
            res = base
            for _ in range(int(n) - 1):
                res = _product(res, base, lab, add)
            return res
        if node.is_Mul:
            scalars = [a for a in node.args if a.is_Number]
            parts = [ev(a) for a in node.args if not a.is_Number]
            res = parts[0]
            for m in parts[1:]:
                if res.cols != m.rows:
                    raise _Undefined(f"{lab} is not defined: a {res.rows}×{res.cols} matrix times a "
                                     f"{m.rows}×{m.cols} matrix (the inner sizes {res.cols} and {m.rows} differ).")
                res = _product(res, m, lab, add)
            if scalars:
                c = sp.Mul(*scalars)
                before = sp.ImmutableMatrix(res.rows, res.cols, lambda i, j: sp.Mul(c, res[i, j], evaluate=False))
                after = sp.ImmutableMatrix(c * sp.Matrix(res))
                add(before, f"Compute {lab}", after,
                    "Multiply every entry by −1." if c == -1 else f"Multiply every entry by {sp.sstr(c)}.")
                res = after
            return res
        if node.is_Add:
            terms = [ev(a) for a in node.args]
            shapes = [t.shape for t in terms]
            if len(set(shapes)) != 1:
                raise _Undefined(f"{lab} is not defined: you can only add matrices of the same size "
                                 f"(here {' and '.join(f'{r}×{c}' for r, c in shapes)}).")
            r, c = shapes[0]
            before = sp.ImmutableMatrix(r, c, lambda i, j: sp.Add(*[t[i, j] for t in terms], evaluate=False))
            after = sp.ImmutableMatrix(sum((sp.Matrix(t) for t in terms), sp.zeros(r, c)))
            add(before, f"Compute {lab}", after, "Add corresponding entries.")
            return after
        raise UnsupportedProblem(f"unsupported matrix operation in {p.given['expression']!r}")

    facts = {"matrices": mats, "expression": p.given["expression"], "parsed": expr}
    try:
        answer = ev(expr)
        facts["defined"] = True
        notes = []
    except _Undefined as exc:
        facts["defined"] = False
        facts["why_undefined"] = str(exc)
        answer = sp.Symbol("undefined")
        notes = [str(exc)]
    return Solution(problem=p, steps=steps, answer=answer, answer_label=label(expr), facts=facts, notes=notes)


def direct_value(expr, mats: dict[str, sp.Matrix]):
    """Independent plain evaluation (no steps) used by the verifier; None if undefined."""
    sizes = {m.rows for m in mats.values() if m.is_square}

    def ev(node):
        if node.is_Number:
            return node
        if isinstance(node, sp.Symbol):
            return sp.eye(next(iter(sizes))) if node.name == "I" else sp.Matrix(mats[node.name])
        if isinstance(node, sp.Function) and node.func == Tr:
            return ev(node.args[0]).T
        if node.is_Pow:
            return ev(node.base) ** int(node.exp)
        if node.is_Mul:
            out = sp.Integer(1)
            for a in node.args:
                out = out * ev(a)
            return out
        if node.is_Add:
            out = None
            for a in node.args:
                v = ev(a)
                out = v if out is None else out + v
            return out
        raise ValueError(node)

    try:
        return sp.ImmutableMatrix(ev(expr))
    except (sp.ShapeError, ValueError, TypeError, StopIteration):
        return None


def float_value(expr, mats: dict[str, sp.Matrix]):
    import numpy as np

    fl = {n: np.array(m.evalf(), dtype=float) for n, m in mats.items()}
    sizes = {m.rows for m in mats.values() if m.is_square}

    def ev(node):
        if node.is_Number:
            return float(node)
        if isinstance(node, sp.Symbol):
            return np.eye(next(iter(sizes))) if node.name == "I" else fl[node.name]
        if isinstance(node, sp.Function) and node.func == Tr:
            return ev(node.args[0]).T
        if node.is_Pow:
            return np.linalg.matrix_power(ev(node.base), int(node.exp))
        if node.is_Mul:
            out = None
            for a in node.args:
                v = ev(a)
                out = v if out is None else (out * v if np.isscalar(v) or np.isscalar(out) else out @ v)
            return out
        if node.is_Add:
            return sum(ev(a) for a in node.args)
        raise ValueError(node)

    return ev(expr)


class _Undefined(Exception):
    pass


def _product(a, b, lab, add):
    r, c, n = a.rows, b.cols, a.cols
    dots = sp.ImmutableMatrix(r, c, lambda i, j: sp.Add(*[sp.Mul(a[i, t], b[t, j], evaluate=False) for t in range(n)],
                                                        evaluate=False) if n > 1 else sp.Mul(a[i, 0], b[0, j], evaluate=False))
    add(sp.MatMul(a, b, evaluate=False), f"Compute {lab}: entries", dots,
        f"Entry (i, j) of the product is row i of the left matrix · column j of the right matrix "
        f"({r}×{n} times {n}×{c} gives {r}×{c}).", {"product_of": (a, b)})
    res = sp.ImmutableMatrix(sp.Matrix(r, c, lambda i, j: sum(a[i, t] * b[t, j] for t in range(n))))
    add(dots, "Arithmetic", res, "Multiply and add in each entry.")
    return res
