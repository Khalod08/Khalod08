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
from tutor import registry
from tutor.parse.schema import Problem, load_problem, save_problem
from tutor.text.unicode_math import to_text


def describe(problem: Problem) -> str:
    """The readable form shown to the student before solving."""
    return registry.get(problem.type).describe(problem)


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
            for name in registry.names():
                t = registry.get(name)
                print(f"{t.course}  {name:24} {t.title}  (needs: {', '.join(t.required)})")
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
