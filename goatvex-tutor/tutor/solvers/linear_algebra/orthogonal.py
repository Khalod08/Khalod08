"""Orthogonality in ℝⁿ: Gram–Schmidt, orthogonal projections (Nicholson 5.3, 8.1).

Gram–Schmidt: v₁ = x₁, vₖ = xₖ − Σ (xₖ·vᵢ / vᵢ·vᵢ) vᵢ, every coefficient shown.
Projection of y onto W = span{u₁ … uₖ}: make the basis orthogonal first
(Gram–Schmidt if needed), then proj_W y = Σ (y·vᵢ / vᵢ·vᵢ) vᵢ.
"""

from __future__ import annotations

import sympy as sp

from tutor.errors import ProblemFormatError, UnsupportedProblem
from tutor.parse.schema import Problem
from tutor.solvers.builder import A, Builder, M, dot_formula, frac, sumsq_formula
from tutor.steps import FACT, Solution
from tutor.text.unicode_math import sub, to_text, vec_text


def V(v):
    return sp.ImmutableMatrix(v)


def dot(u, v):
    return (sp.Matrix(u).T * sp.Matrix(v))[0]


def gram_schmidt(B: Builder, xs, normalize=False):
    vs = []
    for k, x in enumerate(xs):
        if k == 0:
            v = V(x)
            B.add(None, "v₁ = x₁", v, "The first vector stays as it is.", kind=FACT, rule="gs_first")
        else:
            coeffs = []
            for i, vi in enumerate(vs):
                num = B.add(dot_formula(list(x), list(vi)), f"x{sub(k + 1)}·v{sub(i + 1)}", dot(x, vi),
                            "Dot product.")
                den = B.add(sumsq_formula(list(vi)), f"v{sub(i + 1)}·v{sub(i + 1)}", dot(vi, vi), "Dot product.")
                coeffs.append(num / den)
            formula = V([A(x[r], *[M(-c, vs[i][r]) for i, c in enumerate(coeffs)]) for r in range(len(x))])
            v = V(sp.Matrix(x) - sum((c * sp.Matrix(vs[i]) for i, c in enumerate(coeffs)), sp.zeros(len(x), 1)))
            B.add(formula, f"v{sub(k + 1)} = x{sub(k + 1)} − Σ (x·vᵢ/vᵢ·vᵢ) vᵢ", v,
                  "Subtract the projections onto the earlier vᵢ: coefficients "
                  + ", ".join(to_text(c) for c in coeffs) + ".")
            if v == V(sp.zeros(len(x), 1)):
                raise UnsupportedProblem(f"x{sub(k + 1)} is a combination of the earlier vectors (the vectors are "
                                         "dependent), so Gram–Schmidt gives the zero vector")
        vs.append(v)
    if normalize:
        out = []
        for i, v in enumerate(vs):
            nv = sp.sqrt(dot(v, v))
            out.append(B.add(M(frac(1, nv), v), f"q{sub(i + 1)} = v{sub(i + 1)}/‖v{sub(i + 1)}‖", V(sp.Matrix(v) / nv),
                             f"‖v{sub(i + 1)}‖ = {to_text(nv)}."))
        return out
    return vs


def solve(p: Problem) -> Solution:
    task = p.given["task"]
    B = Builder()
    facts: dict = {"task": task}
    notes = []
    if task == "gram_schmidt":
        xs = p.vecs("vectors")
        vs = gram_schmidt(B, xs, bool(p.given.get("normalize", False)))
        facts.update(xs=xs, vs=vs, normalize=bool(p.given.get("normalize", False)))
        answer, label = vs, "orthogonal basis" if not facts["normalize"] else "orthonormal basis"
    elif task == "projection":
        us = p.vecs("vectors")
        y = p.vec("y")
        orth = all(dot(us[i], us[j]) == 0 for i in range(len(us)) for j in range(i + 1, len(us)))
        if orth:
            vs = [V(u) for u in us]
            B.add(None, "The basis is already orthogonal", vs, "Every pair has dot product 0.", kind=FACT,
                  rule="orth_ok")
        else:
            vs = gram_schmidt(B, us)
        terms = []
        for i, v in enumerate(vs):
            num = B.add(dot_formula(list(y), list(v)), f"y·v{sub(i + 1)}", dot(y, v), "Dot product.")
            den = B.add(sumsq_formula(list(v)), f"v{sub(i + 1)}·v{sub(i + 1)}", dot(v, v), "Dot product.")
            terms.append(num / den)
        formula = V([A(*[M(c, vs[i][r]) for i, c in enumerate(terms)]) for r in range(y.rows)])
        proj = B.add(formula, "proj_W y = Σ (y·vᵢ/vᵢ·vᵢ) vᵢ",
                     V(sum((c * sp.Matrix(vs[i]) for i, c in enumerate(terms)), sp.zeros(y.rows, 1))),
                     "Add up the projections onto each orthogonal basis vector.")
        perp = B.add(A(V(y), M(-1, proj)), "y − proj_W y", V(sp.Matrix(y) - sp.Matrix(proj)),
                     "The part of y orthogonal to W (its length is the distance from y to W).")
        facts.update(us=us, y=y, vs=vs, proj=proj, perp=perp)
        answer, label = proj, "proj_W y"
        notes.append(f"Distance from y to W = ‖y − proj‖ = {to_text(sp.sqrt(dot(perp, perp)))}.")
    else:
        raise ProblemFormatError("task must be gram_schmidt or projection")
    return Solution(problem=p, steps=B.steps, answer=answer, answer_label=label, facts=facts, notes=notes)
