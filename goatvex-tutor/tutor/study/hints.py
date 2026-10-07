"""The hint ladder: each level reveals a little more of the VERIFIED solution.

Level 1  the strategy (method recap + textbook sections), no specifics
Level 2  the first move: the name of the first operation and why
Level 3  the result of that first move
Level 4+ the next operation, then its result, and so on
Last     the final answer (never for a graded problem: graded work stops before the last steps)

All of it comes from the solver's verified steps; nothing is made up.
"""

from __future__ import annotations

from dataclasses import dataclass

from tutor import registry
from tutor.narration.generic import recap_line
from tutor.text.unicode_math import to_text


@dataclass
class Hint:
    level: int
    total: int
    title: str
    text: str


def _real_steps(sol):
    return [s for s in sol.steps if not (s.id == "s0" and s.kind == "setup")]


def ladder(sol) -> list[Hint]:
    p = sol.problem
    pt = registry.get(p.type)
    steps = _real_steps(sol)
    graded = p.is_graded
    out: list[tuple[str, str]] = []
    secs = "; ".join(f"{b} §{', '.join(v)}" for b, v in pt.sections.items())
    out.append(("Strategy", recap_line(p.type).caption() + (f" (See {secs}.)" if secs else "")))
    # graded work: reveal operations for every step but results only for the first half
    shown_results = len(steps) if not graded else max(1, len(steps) // 2)
    for i, st in enumerate(steps):
        out.append((f"Step {i + 1}: what to do", f"{st.operation}. {st.justification}"))
        if i < shown_results:
            out.append((f"Step {i + 1}: what you should get", to_text(st.after)))
    if not graded:
        out.append(("Answer", f"{sol.answer_label}: {to_text(sol.answer)}"))
    else:
        out.append(("That's as far as hints go",
                    "This is graded work, so GoatVex stops here. You have the method and the first steps; "
                    "finish it yourself, then use /check to find any mistake."))
    return [Hint(i + 1, len(out), t, x) for i, (t, x) in enumerate(out)]


def hint(sol, level: int) -> Hint:
    lad = ladder(sol)
    return lad[max(1, min(level, len(lad))) - 1]
