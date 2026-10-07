"""Span, linear independence, bases for Col/Nul/Row, rank (Nicholson 5.1–5.4).

All of them row reduce a matrix built from the vectors with the verified
Gauss–Jordan engine (every row operation is its own checked step) and then
read the answer off the RREF.
"""

from __future__ import annotations

import sympy as sp

from tutor.errors import ProblemFormatError
from tutor.parse.schema import Problem
from tutor.solvers.builder import A, Builder, M
from tutor.solvers.linear_algebra.row_ops import gauss_jordan
from tutor.solvers.linear_algebra.rref import param_names, row_op_steps
from tutor.steps import FACT, SETUP, Solution, Step
from tutor.text.unicode_math import sub, to_text, vec_text


def _reduce(B: Builder, m: sp.Matrix, why: str):
    B.steps.append(Step(id=f"s{B.k}", kind=SETUP, before=None, operation="Form the matrix", after=m,
                        justification=why, data={"chain": False}))
    B.k += 1
    trace = gauss_jordan(m)
    ops = row_op_steps(trace, start=B.k)
    B.steps += ops
    B.k += len(ops)
    return trace


def null_basis(rref: sp.Matrix, pivots, ncols: int) -> list[sp.Matrix]:
    pcols = [c for _, c in pivots]
    basis = []
    for f in range(ncols):
        if f in pcols:
            continue
        v = sp.zeros(ncols, 1)
        v[f] = 1
        for r, c in pivots:
            v[c] = -rref[r, f]
        basis.append(v)
    return basis


def solve(p: Problem) -> Solution:
    task = p.given["task"]
    B = Builder()
    facts: dict = {"task": task}
    notes: list[str] = []
    if task == "span":
        vs = p.vecs("vectors")
        w = p.vec("w")
        if w.rows != vs[0].rows:
            raise ProblemFormatError("w must have as many entries as the vectors")
        aug = sp.Matrix.hstack(*vs, w)
        trace = _reduce(B, aug, "w is in the span exactly when c₁v₁ + … + cₖvₖ = w has a solution: row reduce "
                                "[v₁ … vₖ | w].")
        pcols = [c for _, c in trace.pivots]
        k = len(vs)
        if k in pcols:
            answer = False
            notes.append("A pivot in the last column means the system is inconsistent: w is NOT in the span.")
            B.add(None, "Read off the answer", "not in the span", "The last column has a pivot (a row 0 = 1).",
                  kind=FACT)
        else:
            rref = trace.result
            coeffs = sp.zeros(k, 1)
            for r, c in trace.pivots:
                coeffs[c] = rref[r, k]
            combo = sp.ImmutableMatrix([A(*[M(coeffs[i], vs[i][r]) for i in range(k)]) for r in range(w.rows)])
            B.add(combo, "Write w as a combination", sp.ImmutableMatrix(w),
                  "With every free coefficient set to 0, the RREF gives " +
                  ", ".join(f"c{sub(i + 1)} = {to_text(coeffs[i])}" for i in range(k)) + ".")
            answer = True
            facts["coefficients"] = coeffs
            notes.append("w = " + " + ".join(f"({to_text(coeffs[i])}){vec_text(vs[i])}" for i in range(k)))
        facts.update(vectors=vs, w=w, aug=aug)
        label = "w in span?"
    elif task == "independence":
        vs = p.vecs("vectors")
        m = sp.Matrix.hstack(*vs)
        trace = _reduce(B, m, "The vectors are independent exactly when c₁v₁ + … + cₖvₖ = 0 has only the zero "
                              "solution: row reduce the matrix with the vectors as columns.")
        k = len(vs)
        pcols = [c for _, c in trace.pivots]
        if len(pcols) == k:
            answer = True
            B.add(None, "Read off the answer", "independent", "Every column has a pivot: no free variables, so only "
                  "the zero solution.", kind=FACT)
        else:
            answer = False
            dep = null_basis(trace.result, trace.pivots, k)[0]
            combo = sp.ImmutableMatrix([A(*[M(dep[i], vs[i][r]) for i in range(k)]) for r in range(vs[0].rows)])
            B.add(combo, "A dependence relation", sp.ImmutableMatrix(sp.zeros(vs[0].rows, 1)),
                  "A free variable gives a nonzero solution: " +
                  ", ".join(f"c{sub(i + 1)} = {to_text(dep[i])}" for i in range(k)) + ".")
            facts["relation"] = dep
        facts.update(vectors=vs, matrix=m)
        label = "independent?"
    elif task in ("bases", "rank"):
        a = p.matrix
        trace = _reduce(B, a, "Row reduce A. The pivots tell us everything: rank, a basis of the column space, of "
                              "the row space and of the null space.")
        rref = trace.result
        pcols = [c for _, c in trace.pivots]
        col_basis = [a[:, c] for c in pcols]
        row_basis = [rref[r, :].T for r, _ in trace.pivots]
        nul = null_basis(rref, trace.pivots, a.cols)
        B.add(None, "Column space", col_basis, "The pivot columns of the ORIGINAL matrix A (columns "
              + ", ".join(str(c + 1) for c in pcols) + ") form a basis of Col(A).", kind=FACT)
        B.add(None, "Row space", row_basis, "The nonzero rows of the RREF form a basis of Row(A).", kind=FACT)
        B.add(None, "Null space", nul if nul else "{0}",
              "Solve A·x = 0: each free variable gives one basis vector of Nul(A)." if nul else
              "No free variables: Nul(A) = {0}.", kind=FACT)
        rank = len(pcols)
        B.add(None, "Rank and nullity", sp.Eq(sp.Symbol("rank") + sp.Symbol("nullity"), a.cols),
              f"rank(A) = {rank} (number of pivots), nullity(A) = {len(nul)}: {rank} + {len(nul)} = {a.cols} "
              f"columns (rank–nullity theorem).", kind=FACT)
        facts.update(matrix=a, rank=rank, nullity=len(nul), col_basis=col_basis, row_basis=row_basis,
                     null_basis=nul, pivots=pcols)
        answer, label = rank, "rank(A)"
        if a.is_square:
            notes.append("A is invertible (Invertible Matrix Theorem)." if rank == a.rows else
                         "rank(A) < n, so A is NOT invertible (Invertible Matrix Theorem).")
    else:
        raise ProblemFormatError(f"unknown task {task!r}")
    return Solution(problem=p, steps=B.steps, answer=answer, answer_label=label, facts=facts, notes=notes)
