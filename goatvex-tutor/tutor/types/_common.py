"""Helpers shared by problem-type modules (not itself a problem type)."""

from __future__ import annotations

from tutor.parse.schema import Problem
from tutor.text.unicode_math import matrix_text, to_text


def header(problem: Problem, ask: str) -> list[str]:
    lines = [f"Course: {problem.course}    Topic: {problem.topic}    Type: {problem.type}"]
    if problem.statement:
        lines.append(f"Statement: {problem.statement}")
    lines.append(ask)
    return lines


def footer(problem: Problem) -> list[str]:
    lines = []
    if problem.is_graded:
        lines.append("⚠ Marked as a graded assignment → hint mode / parallel problem only.")
    lines.append("Confirmed by student: " + ("yes" if problem.confirmed_by_student else "NOT YET"))
    return lines


def describe_lines(problem: Problem, ask: str, body: list[str]) -> str:
    return "\n".join(header(problem, ask) + body + footer(problem))


__all__ = ["header", "footer", "describe_lines", "matrix_text", "to_text"]
