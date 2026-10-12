"""Registry of problem types.

Each type is one module (in ``tutor/types/``) that registers a
:class:`ProblemType`. Adding a new kind of problem means writing one module:
validation, a readable description for the "Is this exactly the problem?"
step, a step-by-step solver, a verifier, and optionally a practice-problem
generator, an answer grader and a video template.
"""

from __future__ import annotations

import importlib
import pkgutil
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:  # pragma: no cover
    from tutor.parse.schema import Problem
    from tutor.steps import Solution
    from tutor.verify.result import CheckResult


@dataclass
class ProblemType:
    name: str
    course: str                      # "MATH1104" | "MATH1004"
    topic: str                       # default topic slug (output folder, progress tracking)
    title: str                       # readable name, e.g. "Determinant"
    required: tuple[str, ...]        # keys required in "given"
    validate: Callable[["Problem"], None]
    describe: Callable[["Problem"], str]
    solve: Callable[["Problem"], "Solution"]
    verify: Callable[["Solution"], list["CheckResult"]]
    # practice: rng, difficulty (1-3) -> (given, statement)
    generate: Callable[[random.Random, int], tuple[dict[str, Any], str]] | None = None
    # variants: named sub-generators, e.g. {"parts": ...} for integration by parts ("indefinite_integral:parts")
    variants: dict[str, Callable[[random.Random, int], tuple[dict[str, Any], str]]] = field(default_factory=dict)
    # grade: verified solution + the student's answer text -> (correct?, explanation)
    grade: Callable[["Solution", str], tuple[bool, str]] | None = None
    # answer_text: the verified answer written the way a student would type it (for /practice and tests)
    answer_text: Callable[["Solution"], str] | None = None
    answer_format: str = ""          # how the student should type an answer, for /practice
    template: str | None = None      # video template key (tutor/video/templates)
    sections: dict[str, list[str]] = field(default_factory=dict)  # textbook sections, e.g. {"Nicholson": ["3.1"]}
    keywords: tuple[str, ...] = ()   # words that suggest this type (for /explain and transcription help)


TYPES: dict[str, ProblemType] = {}
_loaded = False


def register(pt: ProblemType) -> ProblemType:
    if pt.name in TYPES:
        raise ValueError(f"problem type {pt.name!r} registered twice")
    TYPES[pt.name] = pt
    return pt


def load_all() -> dict[str, ProblemType]:
    """Import every module in tutor.types so each registers itself."""
    global _loaded
    if not _loaded:
        import tutor.types as pkg

        for mod in pkgutil.iter_modules(pkg.__path__):
            if mod.name.startswith("_"):  # helpers, not problem types
                continue
            importlib.import_module(f"tutor.types.{mod.name}")
        from tutor.types import _variants

        _variants.attach(TYPES)
        _loaded = True
    return TYPES


def get(name: str) -> ProblemType:
    load_all()
    return TYPES[name]


def names() -> list[str]:
    return sorted(load_all())
