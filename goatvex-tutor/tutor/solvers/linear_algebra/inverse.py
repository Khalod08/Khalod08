"""Matrix inverse by row reducing [A | I] to [I | A⁻¹]."""

from __future__ import annotations

import sympy as sp

from tutor.parse.schema import Problem
from tutor.solvers.linear_algebra.row_ops import check_exact, gauss_jordan
from tutor.solvers.linear_algebra.rref import row_op_steps
from tutor.steps import SETUP, Solution, Step


def solve(problem: Problem) -> Solution:
    a = problem.matrix
    check_exact(a)
    n = a.rows
    aug = a.row_join(sp.eye(n))
    setup = Step(
        id="s0",
        kind=SETUP,
        before=a,
        operation="Form [A | I]",
        after=aug,
        justification=f"Place the {n}×{n} identity matrix beside A. Row reducing the left half to I turns the right half into A⁻¹.",
        data={"augmented_at": n, "n": n},
    )
    trace = gauss_jordan(aug, pivot_cols=range(n))
    steps = [setup] + row_op_steps(trace)
    final = trace.result
    left, right = final[:, :n], final[:, n:]
    invertible = left == sp.eye(n)
    facts = {
        "n": n,
        "input": a,
        "invertible": invertible,
        "final_augmented": final,
        "rank": len(trace.pivots),
    }
    if invertible:
        notes = ["The left half became I, so A is invertible and the right half is A⁻¹."]
        answer, label = right, "A⁻¹"
    else:
        notes = [
            "The left half cannot be reduced to I (it has a row of zeros), so A is not invertible."
        ]
        answer, label = sp.Symbol("not_invertible"), "A⁻¹ does not exist"
    return Solution(problem=problem, steps=steps, answer=answer, answer_label=label, facts=facts, notes=notes)
