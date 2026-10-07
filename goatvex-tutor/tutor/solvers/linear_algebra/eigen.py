"""Eigenvalues, eigenvectors and diagonalization (Nicholson 3.3–3.4, 5.5).

1. form A − λI
2. det(A − λI) by cofactor expansion, one 2×2/expansion per step (same engine
   as the determinant type, with λ as a symbol)
3. expand and factor the characteristic polynomial → eigenvalues (with multiplicity)
4. for each eigenvalue, row reduce A − λI (every row operation shown) → basis of the eigenspace
5. (diagonalize) P = [eigenvectors], D = diag(eigenvalues), A = P D P⁻¹

Complex or irrational eigenvalues: the eigenspace is found with SymPy and
checked by A·v = λ·v (row reduction is only shown for rational λ).
"""

from __future__ import annotations

import sympy as sp

from tutor.errors import ProblemFormatError, UnsupportedProblem
from tutor.parse.schema import Problem
from tutor.solvers.builder import Builder
from tutor.solvers.linear_algebra.determinant import D, cofactor_steps
from tutor.solvers.linear_algebra.row_ops import gauss_jordan
from tutor.solvers.linear_algebra.rref import row_op_steps
from tutor.solvers.linear_algebra.subspaces import null_basis
from tutor.steps import ALGEBRA, FACT, SETUP, Solution, Step
from tutor.text.unicode_math import sub, to_text, vec_text

LAM = sp.Symbol("λ")


def _clear(v: sp.Matrix) -> sp.Matrix:
    den = sp.ilcm(*[sp.fraction(e)[1] for e in v]) if any(not e.is_Integer for e in v) else 1
    return v * den


def solve(p: Problem) -> Solution:
    a = p.matrix
    if not a.is_square:
        raise ProblemFormatError("eigenvalues need a square matrix")
    if a.rows > 4:
        raise UnsupportedProblem("eigenvalue problems are supported up to 4×4")
    for e in a:
        if not e.is_rational:
            raise UnsupportedProblem("matrix entries must be exact rational numbers")
    n = a.rows
    task = p.given.get("task", "eigen")
    B = Builder()
    B.steps.append(Step(id="s0", kind=SETUP, before=None, operation="Start from A", after=a,
                        justification="λ is an eigenvalue exactly when det(A − λI) = 0.", data={"chain": False}))
    shifted = a - LAM * sp.eye(n)
    B.add(a, "Form A − λI", shifted, "Subtract λ from every diagonal entry.", kind=FACT, rule="shift")
    B.steps.append(Step(id=f"s{B.k}", kind=SETUP, before=shifted, operation="Characteristic polynomial",
                        after=D(shifted), justification="Compute det(A − λI).", data={"chain": False}))
    B.k += 1
    dsteps, poly = cofactor_steps(shifted, start=B.k)
    B.steps += dsteps
    B.k += len(dsteps)
    expanded = sp.expand(poly)
    if expanded != poly:
        B.add(poly, "Expand", expanded, "Multiply out to get a polynomial in λ.", chain=True)
    factored = sp.factor(expanded, extension=None)
    B.add(expanded, "Factor", factored, "Factor the characteristic polynomial.", chain=True)
    roots = sp.roots(sp.Poly(expanded, LAM))
    if sum(roots.values()) != n:
        raise UnsupportedProblem("the characteristic polynomial does not factor exactly; eigenvalues would be "
                                 "approximate")
    eigvals = sorted(roots, key=lambda r: (sp.im(r), sp.re(r)) if not r.is_real else (0, r))
    B.add(None, "Eigenvalues", [sp.Eq(sp.Symbol(f"λ{sub(i + 1)}"), lv) for i, lv in enumerate(eigvals)],
          "Set the characteristic polynomial to 0: " + ", ".join(
              f"λ = {to_text(lv)}" + (f" (multiplicity {roots[lv]})" if roots[lv] > 1 else "") for lv in eigvals) + ".",
          kind=FACT, rule="roots")
    spaces = {}
    for lv in eigvals:
        m = a - lv * sp.eye(n)
        if lv.is_rational:
            B.steps.append(Step(id=f"s{B.k}", kind=SETUP, before=None, operation=f"Eigenspace for λ = {to_text(lv)}",
                                after=m, justification=f"Solve (A − ({to_text(lv)})I)x = 0 by row reduction.",
                                data={"chain": False, "eigenvalue": lv}))
            B.k += 1
            trace = gauss_jordan(m)
            ops = row_op_steps(trace, start=B.k)
            B.steps += ops
            B.k += len(ops)
            basis = [_clear(v) for v in null_basis(trace.result, trace.pivots, n)]
        else:
            basis = [sp.simplify(v) for v in m.nullspace()]
            # scale to clear denominators for readability
            basis = [sp.simplify(v * sp.lcm([sp.fraction(sp.together(e))[1] for e in v])) for v in basis]
        if not basis:
            raise UnsupportedProblem(f"no eigenvector found for λ = {to_text(lv)} (unexpected)")
        spaces[lv] = basis
        B.add(None, f"Eigenvectors for λ = {to_text(lv)}", basis,
              "Each free variable gives one basis vector of the eigenspace (scaled to clear fractions — any nonzero "
              "multiple is still an eigenvector): "
              + ", ".join(vec_text(v) for v in basis) + ".", kind=FACT, rule="eigenspace", eigenvalue=lv)
    facts = {"matrix": a, "charpoly": expanded, "eigenvalues": eigvals, "multiplicities": roots, "spaces": spaces,
             "task": task}
    notes = []
    answer = {lv: spaces[lv] for lv in eigvals}
    label = "eigenvalues and eigenvectors"
    if task == "diagonalize":
        vecs = [v for lv in eigvals for v in spaces[lv]]
        if len(vecs) < n:
            short = [to_text(lv) for lv in eigvals if len(spaces[lv]) < roots[lv]]
            B.add(None, "Not diagonalizable", "not diagonalizable",
                  f"For λ = {', '.join(short)} the eigenspace is smaller than the multiplicity, so there are fewer than "
                  f"{n} independent eigenvectors.", kind=FACT, rule="not_diagonalizable")
            answer, label = "not diagonalizable", "diagonalizable?"
            facts["diagonalizable"] = False
        else:
            P = sp.Matrix.hstack(*vecs)
            Dm = sp.diag(*[lv for lv in eigvals for _ in spaces[lv]])
            Pinv = P.inv()
            B.add(None, "P = [eigenvectors]", P, "Put the eigenvectors in as columns.", kind=FACT, rule="P")
            B.add(None, "D = diag(eigenvalues)", Dm, "Eigenvalues in the same order as their eigenvectors in P.",
                  kind=FACT, rule="D")
            B.add(None, "P⁻¹", Pinv, "Invert P (row reduce [P | I]).", kind=FACT, rule="Pinv")
            facts.update(P=P, D=Dm, Pinv=Pinv, diagonalizable=True)
            answer, label = (P, Dm), "P, D"
            notes.append("A = P·D·P⁻¹.")
    return Solution(problem=p, steps=B.steps, answer=answer, answer_label=label, facts=facts, notes=notes)
