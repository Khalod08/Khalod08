"""Random problem generators that produce hand-friendly numbers.

Tests and exams in MATH 1104 allow no calculator, so practice problems must
work out cleanly: small integers, determinants ±1/±2, friendly fractions.
"""

from __future__ import annotations

import random

import sympy as sp


def nonzero(rng: random.Random, lo: int = -5, hi: int = 5) -> int:
    while True:
        v = rng.randint(lo, hi)
        if v:
            return v


def unimodular(rng: random.Random, n: int, spread: int = 2, det: int = 1) -> sp.Matrix:
    """Random integer n×n matrix with determinant ±det, built as L·U (keeps
    row reduction mostly fraction-free)."""
    L = sp.eye(n)
    U = sp.eye(n)
    for i in range(n):
        for j in range(i):
            L[i, j] = rng.randint(-spread, spread)
        for j in range(i + 1, n):
            U[i, j] = rng.randint(-spread, spread)
        U[i, i] = rng.choice([1, -1])
    U[n - 1, n - 1] *= det
    P = sp.eye(n)
    if rng.random() < 0.3 and n > 1:  # sometimes start with a row swap needed
        P.row_swap(0, 1)
    return P * L * U


def int_vector(rng: random.Random, n: int, lo: int = -4, hi: int = 4) -> sp.Matrix:
    return sp.Matrix([rng.randint(lo, hi) for _ in range(n)])


def strs(m: sp.Matrix) -> list[list[str]]:
    return [[str(m[i, j]) for j in range(m.cols)] for i in range(m.rows)]


def vstr(v: sp.Matrix) -> list[str]:
    return [str(e) for e in v]
