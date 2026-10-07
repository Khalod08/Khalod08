"""Linear transformations (Nicholson 7.1–7.2, Poole 3.6, 6.4–6.6).

Given T by a formula, e.g. T(x, y, z) = (2x − y, x + z):
  * check linearity (a non-linear T gets a concrete counterexample)
  * standard matrix A = [T(e₁) … T(eₙ)], one column per step
  * optionally T(v) = A·v, the kernel (Nul A) and the range (Col A), via row reduction
"""

from __future__ import annotations

import sympy as sp

from tutor.errors import ProblemFormatError
from tutor.parse.schema import Problem, parse_math, parse_vector
from tutor.solvers.builder import A as Add_, Builder, M, dot_formula
from tutor.solvers.linear_algebra.row_ops import gauss_jordan
from tutor.solvers.linear_algebra.rref import row_op_steps
from tutor.solvers.linear_algebra.subspaces import null_basis
from tutor.steps import FACT, SETUP, Solution, Step
from tutor.text.unicode_math import sub, to_text, vec_text


def read_T(p: Problem):
    names = list(p.given["variables"])
    xs = [sp.Symbol(n, real=True) for n in names]
    comps = [parse_math(c, names) for c in p.given["formula"]]
    for c in comps:
        if c.free_symbols - set(xs):
            raise ProblemFormatError(f"T uses unknown symbols {sorted(map(str, c.free_symbols - set(xs)))}")
    return xs, comps


def is_linear(xs, comps) -> tuple[bool, str | None]:
    for c in comps:
        poly = sp.Poly(c, *xs) if c.is_polynomial(*xs) else None
        if poly is None or poly.total_degree() > 1 or poly.coeff_monomial(1) != 0:
            return False, to_text(c)
    return True, None


def solve(p: Problem) -> Solution:
    xs, comps = read_T(p)
    n, m = len(xs), len(comps)
    B = Builder()
    T = sp.ImmutableMatrix(comps)
    B.steps.append(Step(id="s0", kind=SETUP, before=None, operation="The transformation", after=T,
                        justification=f"T: ℝ{_sup(n)} → ℝ{_sup(m)}, T{vec_text(xs)} = {vec_text(comps)}.",
                        data={"chain": False}))
    linear, bad = is_linear(xs, comps)
    facts = {"xs": xs, "comps": comps}
    if not linear:
        e1 = [1] + [0] * (n - 1)
        T1 = [c.subs(dict(zip(xs, e1))) for c in comps]
        T2 = [c.subs(dict(zip(xs, [2 * v for v in e1]))) for c in comps]
        B.add(None, "Not linear", [sp.ImmutableMatrix(T2), sp.ImmutableMatrix([2 * v for v in T1])],
              f"The component {bad} is not of the form a₁x₁ + … + aₙxₙ. Counterexample: T(2e₁) = {vec_text(T2)} but "
              f"2T(e₁) = {vec_text([2 * v for v in T1])}.", kind=FACT, rule="counterexample")
        facts.update(linear=False, T2=T2, T1=T1)
        return Solution(problem=p, steps=B.steps, answer="not linear", answer_label="linear?", facts=facts,
                        notes=["T is not linear, so it has no standard matrix."])
    cols = []
    for j in range(n):
        e = [1 if i == j else 0 for i in range(n)]
        with sp.evaluate(False):
            shown = sp.ImmutableMatrix([c.xreplace(dict(zip(xs, e))) for c in comps])
        col = sp.ImmutableMatrix([c.subs(dict(zip(xs, e))) for c in comps])
        B.add(shown, f"T(e{sub(j + 1)})", col, f"Put e{sub(j + 1)} = {vec_text(e)} into the formula.")
        cols.append(col)
    A = sp.Matrix.hstack(*cols)
    B.add(None, "Standard matrix A = [T(e₁) … T(eₙ)]", A, "The images of the standard basis vectors are the columns.",
          kind=FACT, rule="matrix")
    facts.update(linear=True, A=A)
    answer, label = A, "standard matrix"
    notes = []
    if "v" in p.given:
        v = sp.Matrix(parse_vector(p.given["v"]))
        Av = B.add(sp.ImmutableMatrix([dot_formula(list(A[i, :]), list(v)) for i in range(m)]), "T(v) = A·v",
                   sp.ImmutableMatrix(A * v), f"Multiply A by v = {vec_text(v)}.")
        facts["v"], facts["Tv"] = v, Av
        notes.append(f"T{vec_text(v)} = {vec_text(Av)}")
    if p.given.get("kernel_range", True):
        B.steps.append(Step(id=f"s{B.k}", kind=SETUP, before=None, operation="Kernel and range: row reduce A",
                            after=A, justification="ker T = Nul A, range T = Col A.", data={"chain": False}))
        B.k += 1
        trace = gauss_jordan(A)
        ops = row_op_steps(trace, start=B.k)
        B.steps += ops
        B.k += len(ops)
        ker = null_basis(trace.result, trace.pivots, n)
        rng = [A[:, c] for _, c in trace.pivots]
        B.add(None, "Kernel", ker if ker else "{0}", "Solve A·x = 0." + (" Only x = 0: T is one-to-one." if not ker else ""),
              kind=FACT, rule="kernel")
        B.add(None, "Range", rng, "The pivot columns of A span the range." + (" They span all of ℝ" + _sup(m) +
              ": T is onto." if len(rng) == m else ""), kind=FACT, rule="range")
        facts.update(kernel=ker, range=rng)
        notes.append(f"dim ker T = {len(ker)}, dim range T = {len(rng)}; {len(ker)} + {len(rng)} = {n}.")
    return Solution(problem=p, steps=B.steps, answer=answer, answer_label=label, facts=facts, notes=notes)


def _sup(n):
    from tutor.text.unicode_math import sup

    return sup(n)
