"""Cramer's rule: xᵢ = det(Aᵢ)/det(A), with every determinant worked out."""

from __future__ import annotations

import sympy as sp

from tutor.parse.schema import Problem
from tutor.solvers.linear_algebra.determinant import D, cofactor_steps
from tutor.solvers.linear_algebra.row_ops import check_exact
from tutor.steps import ALGEBRA, SETUP, Solution, Step
from tutor.text.unicode_math import sub


def split_system(p: Problem) -> tuple[sp.Matrix, sp.Matrix]:
    if "vector" in p.given:
        return p.matrix, p.vec("vector")
    m = p.matrix
    return m[:, :-1], m[:, -1]


def solve(p: Problem) -> Solution:
    A, b = split_system(p)
    check_exact(A.row_join(b))
    n = A.rows
    steps: list[Step] = [Step(id="s0", kind=SETUP, before=A.row_join(b), operation="Write A and b", after=A,
                              justification="Cramer's rule: xᵢ = det(Aᵢ)/det(A), where Aᵢ is A with column i replaced by b.",
                              data={"chain": False})]
    k = 1

    def det_block(m, label, why):
        nonlocal k
        steps.append(Step(id=f"s{k}", kind=SETUP, before=m, operation=f"Find {label}", after=D(m),
                          justification=why, data={"chain": False}))
        k += 1
        sub_steps, value = cofactor_steps(m, start=k)
        steps.extend(sub_steps)
        k += len(sub_steps)
        return value

    detA = det_block(A, "det(A)", "First we need det(A); Cramer's rule only works if it is not 0.")
    facts = {"A": A, "b": b, "detA": detA, "A_i": [], "detAi": []}
    if detA == 0:
        facts["applies"] = False
        return Solution(problem=p, steps=steps, answer=sp.Symbol("cramer_does_not_apply"),
                        answer_label="Cramer's rule does not apply", facts=facts,
                        notes=["det(A) = 0, so Cramer's rule cannot be used. The system has either no solution "
                               "or infinitely many. Row reduce instead."])
    facts["applies"] = True
    xs = []
    for i in range(n):
        Ai = A.copy()
        Ai[:, i] = b
        facts["A_i"].append(Ai)
        val = det_block(Ai, f"det(A{sub(i + 1)})", f"A{sub(i + 1)} is A with column {i + 1} replaced by b.")
        facts["detAi"].append(val)
        frac = sp.Mul(val, sp.Pow(detA, -1, evaluate=False), evaluate=False)
        xi = val / detA
        steps.append(Step(id=f"s{k}", kind=ALGEBRA, before=frac, operation=f"x{sub(i + 1)} = det(A{sub(i + 1)})/det(A)",
                          after=xi, justification=f"x{sub(i + 1)} = {val}/{detA}.", data={"chain": False}))
        k += 1
        xs.append(xi)
    x = sp.Matrix(xs)
    return Solution(problem=p, steps=steps, answer=x, answer_label="x", facts=facts, notes=[])
