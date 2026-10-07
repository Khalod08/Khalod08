"""Structured solution steps.

A solver never returns prose. It returns a list of :class:`Step` objects whose
``before``/``after`` are SymPy objects, plus machine-readable ``data`` that the
verifier re-applies and that narration templates draw numbers from.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import sympy as sp

from tutor.parse.schema import Problem

# Step kinds understood by the verifier.
ROW_OP = "row_op"                # one elementary row operation on a matrix
DERIVATIVE_RULE = "derivative_rule"  # one differentiation rule applied to one d/dx[...] node
ALGEBRA = "algebra"              # an equivalence-preserving rewrite (simplify, expand, ...)
SETUP = "setup"                  # write down the starting object (e.g. [A | I])
EQUATION = "equation"            # equation(s) rewritten; same solutions for data["unknowns"]
INTEGRAL_RULE = "integral_rule"  # one integration rule applied to one ∫[...] node
LIMIT_STEP = "limit_step"        # rewrite inside a limit (valid near the limit point) or apply a limit law
FACT = "fact"                    # a stated result checked by the type's own verifier


@dataclass
class Step:
    id: str
    kind: str
    before: Any
    operation: str          # short readable label, e.g. "R₂ → R₂ − 3R₁" or "Power rule"
    after: Any
    justification: str      # one-sentence reason, readable Unicode (no LaTeX)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Solution:
    problem: Problem
    steps: list[Step]
    answer: Any                       # the verified final object
    answer_label: str                 # e.g. "RREF", "A⁻¹", "f′(x)"
    facts: dict[str, Any] = field(default_factory=dict)  # extra verified results (rank, pivots, ...)
    notes: list[str] = field(default_factory=list)       # plain-language notes for the write-up

    def digest(self) -> str:
        """Fingerprint of the exact verified content.

        Later stages (video, write-up) recompute this and refuse to render if it
        does not match the digest recorded in the verification report.
        """
        h = hashlib.sha256()
        for s in self.steps:
            h.update(f"{s.id}|{s.kind}|{sp.srepr(s.before)}|{s.operation}|{sp.srepr(s.after)}\n".encode())
        h.update(sp.srepr(self.answer).encode())
        return h.hexdigest()[:16]
