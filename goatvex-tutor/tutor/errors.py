"""Exceptions shared across the tutor."""


class GoatVexError(Exception):
    """Base class for tutor errors."""


class ProblemFormatError(GoatVexError):
    """problem.json is malformed or contains something SymPy cannot parse."""


class UnsupportedProblem(GoatVexError):
    """The solver cannot produce a *verifiable* solution for this problem.

    GoatVex must say so plainly instead of guessing.
    """


class NotConfirmed(GoatVexError):
    """The student has not yet confirmed the transcription of this problem."""
