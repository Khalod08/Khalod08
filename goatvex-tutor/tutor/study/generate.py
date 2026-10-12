"""Verified practice problems.

A practice problem is only handed to the student after the full solver +
verifier pipeline passed on it, so its hidden answer is as trustworthy as a
worked solution. ``spec`` is a registry type name, optionally with a variant:
"indefinite_integral:parts".
"""

from __future__ import annotations

import hashlib
import random

import sympy as sp

from tutor import registry
from tutor.errors import GoatVexError
from tutor.parse.schema import Problem, parse_math, problem_from_dict
from tutor.pipeline import PipelineResult, solve_problem
from tutor.text.latex import latex_of, tex
from tutor.text.unicode_math import to_text


def split_spec(spec: str) -> tuple[str, str | None]:
    name, _, variant = spec.partition(":")
    return name, (variant or None)


def generator(spec: str):
    name, variant = split_spec(spec)
    pt = registry.get(name)
    if variant:
        if variant not in pt.variants:
            raise KeyError(f"{name} has no variant {variant!r} (has: {', '.join(pt.variants) or 'none'})")
        return pt, pt.variants[variant]
    if pt.generate is None:
        raise KeyError(f"{name} has no practice generator")
    return pt, pt.generate


def verified_problem(spec: str, rng: random.Random, difficulty: int = 2, slug: str = "practice",
                     tries: int = 12) -> tuple[Problem, PipelineResult]:
    """Generate problems until one passes every check (normally the first one does)."""
    pt, gen = generator(spec)
    last = None
    for _ in range(tries):
        given, statement = gen(rng, difficulty)
        p = problem_from_dict(dict(slug=slug, course=pt.course, type=pt.name, topic=pt.topic, given=given,
                                   statement=statement, confirmed_by_student=True))
        try:
            res = solve_problem(p)
        except GoatVexError as exc:  # e.g. UnsupportedProblem for an unlucky draw
            last = exc
            continue
        if res.verified:
            return p, res
        last = res.status
    raise RuntimeError(f"could not generate a verified {spec} problem (last: {last})")


def answer_text(sol) -> str:
    """The verified answer the way a student would type it (falls back to readable Unicode)."""
    pt = registry.get(sol.problem.type)
    if pt.answer_text:
        return pt.answer_text(sol)
    a = sol.answer
    if isinstance(a, sp.MatrixBase):
        if a.cols == 1:
            return "(" + ", ".join(to_text(e) for e in a) + ")"
        return "; ".join(" ".join(to_text(e) for e in a.row(i)) for i in range(a.rows))
    return to_text(a)


def practice_problem(problem: Problem) -> dict | None:
    """A similar problem (different numbers, same method) with its verified answer."""
    pt = registry.get(problem.type)
    if pt.generate is None:
        return None
    seed = int(hashlib.sha256(problem.slug.encode()).hexdigest()[:8], 16)
    difficulty = 2
    if problem.type in ("rref", "matrix_inverse", "determinant", "cramers_rule") and "matrix" in problem.given:
        difficulty = 1 if problem.matrix.rows <= 2 else 2  # same size as the worked example
    try:
        p, res = verified_problem(problem.type, random.Random(seed), difficulty, slug=f"{problem.slug}-practice")
    except RuntimeError:
        return None
    return {"given": p.given, "statement": p.statement, "latex": practice_tex(p),
            "answer_text": to_text(res.solution.answer), "type": problem.type}


def practice_tex(p: Problem) -> str | None:
    """LaTeX for a problem statement where we have a clean one (else the plain statement is shown)."""
    if p.type == "rref" and p.given.get("augmented"):
        m = p.matrix
        n = m.cols - 1
        names = sp.symbols("x y z")[:n] if n <= 3 else sp.symbols(f"x1:{n + 1}")
        eqs = [tex(sp.Eq(sum(m[i, j] * names[j] for j in range(n)), m[i, n])) for i in range(m.rows)]
        return r"\begin{aligned}" + r"\\".join(e.replace("=", "&=", 1) for e in eqs) + r"\end{aligned}"
    if p.type in ("rref", "matrix_inverse", "determinant"):
        return "A = " + tex(p.matrix)
    if p.type in ("derivative", "log_differentiation"):
        return r"\frac{d}{dx}\left(" + tex(p.function) + r"\right)"
    if p.type == "indefinite_integral":
        return r"\int " + tex(p.expr("integrand")) + r"\,dx"
    if p.type == "definite_integral":
        return (r"\int_{" + tex(sp.sympify(p.given["a"])) + "}^{" + tex(sp.sympify(p.given["b"])) + "} "
                + tex(p.expr("integrand")) + r"\,dx")
    if p.type == "limit":
        return tex(sp.Limit(p.expr("function"), sp.Symbol("x", real=True),
                                 sp.sympify(p.given["point"], locals={"oo": sp.oo}),
                                 p.given.get("direction", "+-")))
    if p.type == "complex" and p.given["task"] == "simplify":
        return tex(parse_math(p.given["expression"], imaginary=True, evaluate=False))

    g = p.given
    if p.type == "cramers_rule":
        m = p.matrix
        return r"[A \mid b] = " + latex_of(m, augmented_at=m.cols - 1)
    if "matrices" in g:
        from tutor.solvers.linear_algebra import matrix_ops

        return r",\qquad ".join(f"{k} = {latex_of(v)}" for k, v in matrix_ops.matrices(p).items())
    if "matrix" in g:
        return "A = " + latex_of(p.matrix)
    if "vectors" in g:
        parts = [rf"\mathbf{{v}}_{{{i + 1}}} = {latex_of(v)}" for i, v in enumerate(p.vecs("vectors"))]
        for k in ("w", "y"):
            if k in g:
                parts.append(rf"\mathbf{{{k}}} = {latex_of(p.vec(k))}")
        return r",\qquad ".join(parts)
    return None
