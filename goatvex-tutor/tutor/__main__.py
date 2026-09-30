"""Command line for the GoatVex pipeline.

    python -m tutor show     problems/q1.json   # readable transcription, for "Is this exactly the problem?"
    python -m tutor confirm  problems/q1.json   # record the student's "yes"
    python -m tutor solve    problems/q1.json   # solve + verify + write videos/<course>/<topic>/<slug>/
    python -m tutor types                       # which problem types can be verified today
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from tutor.errors import GoatVexError, NotConfirmed, UnsupportedProblem
from tutor.parse.schema import PROBLEM_TYPES, Problem, load_problem, save_problem
from tutor.text.unicode_math import matrix_text, to_text


def describe(problem: Problem) -> str:
    """The readable form shown to the student before solving."""
    lines = [f"Course: {problem.course}    Topic: {problem.topic}    Type: {problem.type}"]
    if problem.statement:
        lines.append(f"Statement: {problem.statement}")
    if problem.type == "rref":
        m = problem.matrix
        aug = problem.given.get("augmented")
        lines.append("Row reduce this " + ("augmented matrix [A | b]" if aug else "matrix") + " to RREF:")
        lines.append(matrix_text(m, augmented_at=m.cols - 1 if aug else None))
    elif problem.type == "matrix_inverse":
        lines.append("Find A⁻¹ (or show A is not invertible), where A =")
        lines.append(matrix_text(problem.matrix))
    elif problem.type == "derivative":
        x = problem.given["variable"]
        lines.append(f"Find f′({x}) for  f({x}) = {to_text(problem.function)}")
    if problem.is_graded:
        lines.append("⚠ Marked as a graded assignment → hint mode / parallel problem only.")
    lines.append("Confirmed by student: " + ("yes" if problem.confirmed_by_student else "NOT YET"))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    # Windows terminals default to a legacy code page; make Unicode math printable.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="python -m tutor", description="GoatVex verified math pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("show", "confirm"):
        sp_ = sub.add_parser(name)
        sp_.add_argument("problem", type=Path)
    s = sub.add_parser("solve")
    s.add_argument("problem", type=Path)
    s.add_argument("--out", type=Path, default=None, help="output folder (default videos/<course>/<topic>/<slug>/)")
    s.add_argument("--quiet", action="store_true")
    sub.add_parser("types")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "types":
            for t, (topic, keys) in PROBLEM_TYPES.items():
                print(f"{t:16} topic={topic:16} needs given: {', '.join(keys)}")
            return 0
        problem = load_problem(args.problem)
        if args.cmd == "show":
            print(describe(problem))
            return 0
        if args.cmd == "confirm":
            problem.confirmed_by_student = True
            save_problem(problem, args.problem)
            print(f"Recorded: the student confirmed {args.problem.name}.")
            return 0
        from tutor.pipeline import run

        result = run(problem, out_dir=args.out)
        sol = result.solution
        if not args.quiet:
            for st in sol.steps:
                print(f"{st.id}  {st.operation}")
                print("    " + to_text(st.after).replace("\n", "\n    "))
            print(f"\n{sol.answer_label}:")
            print("    " + to_text(sol.answer).replace("\n", "\n    "))
            for n in sol.notes:
                print("  • " + n)
        n_pass = sum(c.ok for c in result.checks)
        print(f"\nVerification: {result.status} ({n_pass}/{len(result.checks)} checks passed)")
        print(f"Report: {result.out_dir / 'verification_report.md'}")
        return 0 if result.verified else 2
    except NotConfirmed as exc:
        print(f"Not solving yet: {exc}")
        return 3
    except UnsupportedProblem as exc:
        print(f"GoatVex can't verify this one: {exc}")
        return 4
    except GoatVexError as exc:
        print(f"Problem file error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
