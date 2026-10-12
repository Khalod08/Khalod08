"""A small helper for solvers that produce many short derivations."""

from __future__ import annotations

import sympy as sp

from tutor.steps import ALGEBRA, Step


class Builder:
    def __init__(self, start: int = 1, prefix: str = "s"):
        self.steps: list[Step] = []
        self.k = start
        self.prefix = prefix

    def add(self, before, op, after, why, kind=ALGEBRA, chain=False, **data):
        """Append a step. Steps don't chain by default (each is its own small computation)."""
        self.steps.append(Step(id=f"{self.prefix}{self.k}", kind=kind, before=before, operation=op, after=after,
                               justification=why, data={"chain": chain, **data}))
        self.k += 1
        return after


def M(*a):
    """Unevaluated product (keeps every factor visible)."""
    return sp.Mul(*a, evaluate=False)


def A(*a):
    """Unevaluated sum."""
    return sp.Add(*a, evaluate=False)


def P(b, e):
    return sp.Pow(b, e, evaluate=False)


def frac(n, d):
    return sp.Mul(n, sp.Pow(d, -1, evaluate=False), evaluate=False)


def dot_formula(u, v):
    """u₁v₁ + u₂v₂ + … with every product visible."""
    return A(*[M(a, b) for a, b in zip(u, v)]) if len(u) > 1 else M(u[0], v[0])


def sumsq_formula(u):
    return A(*[P(a, 2) for a in u]) if len(u) > 1 else P(u[0], 2)
