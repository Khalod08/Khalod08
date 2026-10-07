"""Determinants, step by step.

Two methods (both taught in Nicholson 3.1–3.2):

* ``cofactor``: expand along the row or column with the most zeros. Each step
  rewrites ONE det[…] in the working expression: a 2×2 becomes ad − bc, a
  bigger one becomes its cofactor expansion. Arithmetic is kept visible and
  combined in a final step.
* ``row_reduction``: reduce to upper-triangular form using only row swaps
  (each flips the sign) and row replacements (no change), then multiply the
  diagonal.

Default: cofactor for n ≤ 3, row reduction for larger matrices.
"""

from __future__ import annotations

import sympy as sp

from tutor.solvers.linear_algebra.row_ops import REPLACE, SWAP, RowOp, check_exact
from tutor.steps import ALGEBRA, ROW_OP, SETUP, Step
from tutor.text.unicode_math import sub


def D(m) -> sp.Determinant:
    return sp.Determinant(sp.ImmutableMatrix(m))


def _mul(*args):
    return sp.Mul(*args, evaluate=False)


def best_line(m: sp.Matrix) -> tuple[str, int]:
    """Row or column with the most zeros (ties: rows first, lowest index)."""
    best = ("row", 0, -1)
    for i in range(m.rows):
        z = sum(1 for j in range(m.cols) if m[i, j] == 0)
        if z > best[2]:
            best = ("row", i, z)
    for j in range(m.cols):
        z = sum(1 for i in range(m.rows) if m[i, j] == 0)
        if z > best[2]:
            best = ("col", j, z)
    return best[0], best[1]


def minor(m: sp.Matrix, i: int, j: int) -> sp.Matrix:
    return m.minor_submatrix(i, j)


def expansion(m: sp.Matrix) -> tuple[sp.Expr, dict]:
    """Cofactor expansion of det(m) as an unevaluated sum (zero entries skipped)."""
    kind, k = best_line(m)
    terms = []
    used = []
    for t in range(m.cols if kind == "row" else m.rows):
        i, j = (k, t) if kind == "row" else (t, k)
        a = m[i, j]
        if a == 0:
            continue
        sign = (-1) ** (i + j)
        coef = a * sign
        terms.append(_mul(coef, D(minor(m, i, j))) if coef != 1 else D(minor(m, i, j)))
        used.append((i + 1, j + 1))
    if not terms:
        expr = sp.Integer(0)
    elif len(terms) == 1:
        expr = terms[0]
    else:
        expr = sp.Add(*terms, evaluate=False)
    return expr, {"line": kind, "index": k + 1, "entries": used,
                  "zeros_skipped": (m.cols if kind == "row" else m.rows) - len(used)}


def two_by_two(m: sp.Matrix) -> sp.Expr:
    a, b, c, d = m[0, 0], m[0, 1], m[1, 0], m[1, 1]
    return sp.Add(_mul(a, d), _mul(-1, _mul(b, c)), evaluate=False)


def first_det(expr) -> sp.Determinant | None:
    for node in sp.preorder_traversal(expr):
        if isinstance(node, sp.Determinant):
            return node
    return None


def _rebuild(e):
    if not e.args or isinstance(e, sp.Determinant):
        return e
    return e.func(*[_rebuild(a) for a in e.args])


def cofactor_steps(m: sp.Matrix, start: int = 1, prefix: str = "s") -> tuple[list[Step], sp.Expr]:
    """Steps turning det(m) into a number. Returns (steps, value)."""
    steps: list[Step] = []
    cur = D(m)
    k = start
    while (node := first_det(cur)) is not None:
        mm = sp.Matrix(node.arg)
        n = mm.rows
        if n == 1:
            rep, op, why, data = mm[0, 0], "1×1 determinant", "The determinant of a 1×1 matrix is its entry.", {}
        elif n == 2:
            rep = two_by_two(mm)
            op = "2×2 determinant"
            why = "For a 2×2 matrix, det = ad − bc."
            data = {}
        else:
            rep, data = expansion(mm)
            line = "row" if data["line"] == "row" else "column"
            op = f"Cofactor expansion along {line} {data['index']}"
            why = (f"Expand along {line} {data['index']}, the {line} with the most zeros. Each entry aᵢⱼ is "
                   f"multiplied by its cofactor (−1)ⁱ⁺ʲ·det(Mᵢⱼ).")
            if data["zeros_skipped"]:
                why += f" Terms with a 0 entry vanish ({data['zeros_skipped']} skipped)."
        with sp.evaluate(False):
            after = cur.xreplace({node: rep})
        steps.append(Step(id=f"{prefix}{k}", kind=ALGEBRA, before=cur, operation=op, after=after,
                          justification=why, data={"det_of": mm, **data}))
        cur = after
        k += 1
    value = _rebuild(cur)
    if value != cur:
        steps.append(Step(id=f"{prefix}{k}", kind=ALGEBRA, before=cur, operation="Arithmetic", after=value,
                          justification="Multiply and add.", data={}))
    return steps, value


def row_reduction_steps(m: sp.Matrix) -> tuple[list[Step], sp.Expr, dict]:
    """Forward elimination with swaps and replacements only; det = (−1)^swaps · product of pivots."""
    check_exact(m)
    cur = m.copy()
    n = m.rows
    steps: list[Step] = []
    sign = 1
    k = 1
    for c in range(n):
        nonzero = [p for p in range(c, n) if cur[p, c] != 0]
        if not nonzero:
            break  # a zero column below the diagonal → det = 0
        if cur[c, c] == 0:
            op = RowOp(SWAP, c, nonzero[0])
            new = op.apply(cur)
            sign = -sign
            steps.append(Step(id=f"s{k}", kind=ROW_OP, before=cur, operation=op.text(), after=new,
                              justification="Swap rows to get a nonzero pivot. A swap changes the sign of the determinant.",
                              data={**op.as_data(), "rowop": op, "pivot_column": c + 1, "det_sign": sign}))
            cur, k = new, k + 1
        for i in range(c + 1, n):
            if cur[i, c] != 0:
                op = RowOp(REPLACE, i, c, -cur[i, c] / cur[c, c])
                new = op.apply(cur)
                steps.append(Step(id=f"s{k}", kind=ROW_OP, before=cur, operation=op.text(), after=new,
                                  justification="Create a zero below the pivot. Adding a multiple of one row to "
                                                "another does not change the determinant.",
                                  data={**op.as_data(), "rowop": op, "pivot_column": c + 1, "det_sign": sign}))
                cur, k = new, k + 1
    diag = [cur[i, i] for i in range(n)]
    prod = _mul(*diag) if n > 1 else diag[0]
    formula = _mul(-1, prod) if sign < 0 else prod
    steps.append(Step(id=f"s{k}", kind=ALGEBRA, before=formula, operation="Multiply the diagonal",
                      after=sp.Mul(*diag) * sign,
                      justification=("The matrix is upper triangular, so its determinant is the product of the "
                                     "diagonal entries" + (", times −1 for the odd number of swaps." if sign < 0 else ".")),
                      data={"chain": False, "triangular": cur, "sign": sign}))
    return steps, sp.Mul(*diag) * sign, {"triangular": cur, "sign": sign}


def det_steps(m: sp.Matrix, method: str | None = None):
    """Steps for det(m) with a SETUP step first. Returns (steps, value, facts)."""
    method = method or ("cofactor" if m.rows <= 3 else "row_reduction")
    if method == "cofactor":
        steps, value = cofactor_steps(m)
        setup = Step(id="s0", kind=SETUP, before=m, operation="Write det(A)", after=D(m),
                     justification="We want the determinant of A.", data={"method": method})
        steps = [setup] + steps
        return steps, value, {"method": method}
    steps, value, facts = row_reduction_steps(m)
    setup = Step(id="s0", kind=SETUP, before=m, operation="Start from A", after=m,
                 justification="Reduce A to upper-triangular form, keeping track of row swaps.",
                 data={"method": method})
    return [setup] + steps, value, {"method": method, **facts}


def label(i: int, j: int) -> str:
    return f"M{sub(i)}{sub(j)}"
