"""Elementary row operations and a step-by-step Gauss–Jordan reducer.

Rows are 0-indexed internally and 1-indexed in anything a student sees
(R₁, R₂, ...). Arithmetic is exact (SymPy Rationals) — never floats.

Method (the "Gaussian algorithm" taught in most first-year courses):

  Forward phase, one column at a time, left to right:
    1. If the pivot position is 0 — or a row below has a leading 1 and the
       pivot is not already 1 — swap rows.            (Rᵢ ↔ Rⱼ)
    2. Scale the pivot row so the pivot is 1.          (Rᵢ → (1/c)Rᵢ)
    3. Create zeros below the pivot.                   (Rⱼ → Rⱼ − cRᵢ)
  Backward phase, rightmost pivot first:
    4. Create zeros above each leading 1.              (Rⱼ → Rⱼ − cRᵢ)

This gives REF after the forward phase and RREF at the end. Every operation is
returned as its own step — nothing is combined or skipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import sympy as sp

from tutor.errors import UnsupportedProblem
from tutor.text.unicode_math import sub, to_text

SWAP, SCALE, REPLACE = "swap", "scale", "replace"


@dataclass(frozen=True)
class RowOp:
    """One elementary row operation.

    swap:    Rᵢ ↔ Rⱼ
    scale:   Rᵢ → c·Rᵢ            (c ≠ 0)
    replace: Rᵢ → Rᵢ + c·Rⱼ       (i ≠ j; c is usually negative, "subtract")
    """

    kind: str
    i: int
    j: int | None = None
    c: sp.Expr | None = None

    def apply(self, m: sp.Matrix) -> sp.Matrix:
        out = sp.Matrix(m)
        if self.kind == SWAP:
            out.row_swap(self.i, self.j)
        elif self.kind == SCALE:
            out[self.i, :] = self.c * m[self.i, :]
        elif self.kind == REPLACE:
            out[self.i, :] = m[self.i, :] + self.c * m[self.j, :]
        else:
            raise ValueError(f"unknown row op kind {self.kind!r}")
        return out

    # ---- student-facing notation --------------------------------------------------
    def text(self) -> str:
        """Unicode notation, e.g. ``R₂ → R₂ − 3R₁``."""
        ri = f"R{sub(self.i + 1)}"
        if self.kind == SWAP:
            return f"{ri} ↔ R{sub(self.j + 1)}"
        if self.kind == SCALE:
            return f"{ri} → {_coef_text(self.c)}{ri}"
        rj = f"R{sub(self.j + 1)}"
        sign = "−" if self.c < 0 else "+"
        mag = abs(self.c)
        return f"{ri} → {ri} {sign} {_coef_text(mag)}{rj}"

    def latex(self) -> str:
        ri = f"R_{{{self.i + 1}}}"
        if self.kind == SWAP:
            return rf"{ri} \leftrightarrow R_{{{self.j + 1}}}"
        if self.kind == SCALE:
            return rf"{ri} \to {_coef_latex(self.c)}{ri}"
        rj = f"R_{{{self.j + 1}}}"
        sign = "-" if self.c < 0 else "+"
        return rf"{ri} \to {ri} {sign} {_coef_latex(abs(self.c))}{rj}"

    def as_data(self) -> dict:
        d = {"op": self.kind, "row": self.i + 1}
        if self.j is not None:
            d["other_row"] = self.j + 1
        if self.c is not None:
            d["multiplier"] = self.c
            if self.kind == REPLACE:
                d["subtract"] = bool(self.c < 0)
                d["magnitude"] = abs(self.c)
        return d


def _coef_text(c: sp.Expr) -> str:
    if c == 1:
        return ""
    t = to_text(c)
    return f"({t})" if "/" in t or t.startswith("−") else t


def _coef_latex(c: sp.Expr) -> str:
    if c == 1:
        return ""
    t = sp.latex(c)
    return rf"\left({t}\right)" if (isinstance(c, sp.Rational) and c.q != 1) or c < 0 else t


@dataclass
class ReductionTrace:
    ops: list[RowOp]
    matrices: list[sp.Matrix]  # matrices[0] is the input; matrices[k+1] = ops[k](matrices[k])
    pivots: list[tuple[int, int]]  # (row, col), 0-indexed
    phase_of_op: list[str]  # "forward" | "backward" per op
    ref_index: int  # index into ``matrices`` of the REF (end of forward phase)

    @property
    def result(self) -> sp.Matrix:
        return self.matrices[-1]


def check_exact(m: sp.Matrix) -> None:
    for e in m:
        if not (e.is_Rational or (e.is_number and e.is_rational)):
            raise UnsupportedProblem(
                "row reduction is only verified for matrices with exact rational numbers; "
                f"entry {to_text(e)} is symbolic or irrational (e.g. a parameter k needs case analysis)"
            )


def gauss_jordan(m: sp.Matrix, pivot_cols: Iterable[int] | None = None) -> ReductionTrace:
    """Reduce ``m`` to RREF, recording every elementary row operation.

    ``pivot_cols`` limits which columns may hold pivots (used for [A | I], where
    only the columns of A are reduced).
    """
    check_exact(m)
    cur = sp.Matrix(m)
    ops: list[RowOp] = []
    mats = [cur]
    phases: list[str] = []
    pivots: list[tuple[int, int]] = []

    def do(op: RowOp, phase: str) -> None:
        nonlocal cur
        cur = op.apply(cur)
        ops.append(op)
        mats.append(cur)
        phases.append(phase)

    cols = list(range(m.cols)) if pivot_cols is None else list(pivot_cols)
    r = 0
    for c in cols:
        if r >= m.rows:
            break
        nonzero = [p for p in range(r, m.rows) if cur[p, c] != 0]
        if not nonzero:
            continue
        if cur[r, c] != 1:
            ones = [p for p in nonzero if cur[p, c] == 1]
            if ones and ones[0] != r:
                do(RowOp(SWAP, r, ones[0]), "forward")
            elif cur[r, c] == 0:
                do(RowOp(SWAP, r, nonzero[0]), "forward")
        if cur[r, c] != 1:
            do(RowOp(SCALE, r, c=sp.Integer(1) / cur[r, c]), "forward")
        for i in range(r + 1, m.rows):
            if cur[i, c] != 0:
                do(RowOp(REPLACE, i, r, -cur[i, c]), "forward")
        pivots.append((r, c))
        r += 1

    ref_index = len(mats) - 1
    for r, c in reversed(pivots):
        for i in range(r):
            if cur[i, c] != 0:
                do(RowOp(REPLACE, i, r, -cur[i, c]), "backward")

    return ReductionTrace(ops=ops, matrices=mats, pivots=pivots, phase_of_op=phases, ref_index=ref_index)


def is_rref(m: sp.Matrix) -> tuple[bool, str]:
    """Independent check of the four RREF conditions (does not use the reducer)."""
    last_lead = -1
    seen_zero_row = False
    for i in range(m.rows):
        row = [m[i, j] for j in range(m.cols)]
        lead = next((j for j, v in enumerate(row) if v != 0), None)
        if lead is None:
            seen_zero_row = True
            continue
        if seen_zero_row:
            return False, f"row {i + 1} is nonzero but comes after a zero row"
        if row[lead] != 1:
            return False, f"leading entry of row {i + 1} is {to_text(row[lead])}, not 1"
        if lead <= last_lead:
            return False, f"leading 1 of row {i + 1} is not to the right of the one above"
        for k in range(m.rows):
            if k != i and m[k, lead] != 0:
                return False, f"column {lead + 1} has a nonzero entry in row {k + 1} besides its leading 1"
        last_lead = lead
    return True, "all four RREF conditions hold"


def is_ref(m: sp.Matrix) -> tuple[bool, str]:
    """Row echelon form with leading 1s (the form reached after the forward phase)."""
    last_lead = -1
    seen_zero_row = False
    for i in range(m.rows):
        lead = next((j for j in range(m.cols) if m[i, j] != 0), None)
        if lead is None:
            seen_zero_row = True
            continue
        if seen_zero_row:
            return False, f"row {i + 1} is nonzero but comes after a zero row"
        if lead <= last_lead:
            return False, f"leading entry of row {i + 1} is not to the right of the one above"
        for k in range(i + 1, m.rows):
            if m[k, lead] != 0:
                return False, f"column {lead + 1} is not zero below row {i + 1}'s leading entry"
        last_lead = lead
    return True, "row echelon form"
