"""Row reduce a matrix to RREF, step by step (and read off a system's solution).

If ``given.augmented`` is true the last column is the right-hand side b of a
system Ax = b, and the solution set is read from the RREF.
"""

from __future__ import annotations

import sympy as sp

from tutor.parse.schema import Problem
from tutor.solvers.linear_algebra.row_ops import gauss_jordan
from tutor.steps import ROW_OP, SETUP, Solution, Step
from tutor.text.unicode_math import sub

PHASE_REASON = {
    "swap": "Swap rows to bring a {why} into the pivot position of column {col}.",
    "scale": "Scale row {row} so the pivot in column {col} becomes a leading 1.",
    "replace_forward": "Create a zero below the leading 1 in column {col}.",
    "replace_backward": "Create a zero above the leading 1 in column {col}.",
}


def row_op_steps(trace, *, id_prefix: str = "s", start: int = 1) -> list[Step]:
    """Turn a :class:`ReductionTrace` into one :class:`Step` per row operation."""
    steps: list[Step] = []
    pivot_col_of_row = {r: c for r, c in trace.pivots}
    for k, op in enumerate(trace.ops):
        before, after = trace.matrices[k], trace.matrices[k + 1]
        if op.kind == "swap":
            # the pivot column is the first column where the new pivot row is nonzero
            col = pivot_col_of_row.get(op.i, 0)
            why = "leading 1" if after[op.i, col] == 1 else "nonzero entry"
            reason = PHASE_REASON["swap"].format(why=why, col=col + 1)
        elif op.kind == "scale":
            col = pivot_col_of_row[op.i]
            reason = PHASE_REASON["scale"].format(row=op.i + 1, col=col + 1)
        else:
            col = pivot_col_of_row[op.j]
            reason = PHASE_REASON[f"replace_{trace.phase_of_op[k]}"].format(col=col + 1)
        data = op.as_data()
        data.update(pivot_column=col + 1, phase=trace.phase_of_op[k], rowop=op)
        steps.append(
            Step(
                id=f"{id_prefix}{start + k}",
                kind=ROW_OP,
                before=before,
                operation=op.text(),
                after=after,
                justification=reason,
                data=data,
            )
        )
    return steps


def param_names(k: int) -> list[sp.Symbol]:
    from tutor.materials.notation import param_letters

    custom = param_letters(k)  # the professor's letters, if detected in the course materials
    if custom:
        return [sp.Symbol(n) for n in custom]
    names = {0: [], 1: ["t"], 2: ["s", "t"], 3: ["r", "s", "t"]}.get(k)
    if names is None:
        names = [f"t{sub(i + 1)}" for i in range(k)]
    return [sp.Symbol(n) for n in names]


def read_system(rref: sp.Matrix, pivots: list[tuple[int, int]]) -> dict:
    """Read the solution set of [A | b] from its RREF."""
    n = rref.cols - 1
    pivot_cols = [c for _, c in pivots]
    if n in pivot_cols:
        r = pivot_cols.index(n)
        return {"status": "inconsistent", "bad_row": r + 1, "num_vars": n}
    free = [c for c in range(n) if c not in pivot_cols]
    xp = sp.zeros(n, 1)
    for r, c in pivots:
        xp[c] = rref[r, n]
    basis = []
    for f in free:
        v = sp.zeros(n, 1)
        v[f] = 1
        for r, c in pivots:
            v[c] = -rref[r, f]
        basis.append(v)
    params = param_names(len(free))
    general = xp + sum((p * v for p, v in zip(params, basis)), sp.zeros(n, 1))
    return {
        "status": "unique" if not free else "infinite",
        "num_vars": n,
        "free_vars": [f + 1 for f in free],
        "particular": xp,
        "null_basis": basis,
        "params": params,
        "general": general,
    }


def solve(problem: Problem) -> Solution:
    m = problem.matrix
    augmented = bool(problem.given.get("augmented", False))
    trace = gauss_jordan(m)

    setup = Step(
        id="s0",
        kind=SETUP,
        before=m,
        operation="Write the matrix",
        after=m,
        justification="Start from the matrix exactly as given.",
        data={"augmented": augmented},
    )
    steps = [setup] + row_op_steps(trace)
    rref = trace.result
    facts: dict = {
        "pivots": [(r + 1, c + 1) for r, c in trace.pivots],
        "rank": len(trace.pivots),
        "ref": trace.matrices[trace.ref_index],
        "ref_step": steps[trace.ref_index].id,
        "augmented": augmented,
        "input": m,
    }
    notes = []
    if augmented:
        system = read_system(rref, trace.pivots)
        facts["system"] = system
        if system["status"] == "inconsistent":
            notes.append(
                f"Row {system['bad_row']} of the RREF reads 0 = 1, so the system has no solution (inconsistent)."
            )
        elif system["status"] == "unique":
            notes.append("Every variable column has a pivot, so the system has exactly one solution.")
        else:
            fv = ", ".join(f"x{sub(f)}" for f in system["free_vars"])
            notes.append(f"Free variable(s): {fv}. The system has infinitely many solutions.")
    return Solution(problem=problem, steps=steps, answer=rref, answer_label="RREF", facts=facts, notes=notes)
