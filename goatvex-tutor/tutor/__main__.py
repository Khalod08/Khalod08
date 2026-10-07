"""Command line for the GoatVex pipeline.

    python -m tutor show     problems/q1.json   # readable transcription, for "Is this exactly the problem?"
    python -m tutor confirm  problems/q1.json   # record the student's "yes"
    python -m tutor solve    problems/q1.json   # solve + verify + write videos/<course>/<topic>/<slug>/
    python -m tutor types                       # which problem types can be verified today

Study modes (Phase 4):

    python -m tutor writeup  problems/q1.json [--open]        # KaTeX write-up of a verified solution
    python -m tutor hint     problems/q1.json --level 2       # hint ladder from the verified steps
    python -m tutor check    problems/q1.json attempt.txt     # find the first wrong line of the student's work
    python -m tutor practice new --course MATH1004 [--type limit] [--n 3]
    python -m tutor practice answer latest 1 "3x^2 + 2"
    python -m tutor practice review                           # spaced-repetition quiz on what's due
    python -m tutor testprep new MATH1104 test2
    python -m tutor testprep grade latest "answer 1" "answer 2" ...
    python -m tutor explain  "chain rule" [--make]
    python -m tutor progress [--open]
    python -m tutor materials ingest                          # index the course PDFs (Phase 5)
    python -m tutor materials find "cofactor expansion"
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
    s.add_argument("--no-html", action="store_true", help="skip solution.html")
    s.add_argument("--open", action="store_true", help="open the write-up in the browser")
    s.add_argument("--log", action="store_true", help="log a studied worked example in student/progress.json")
    sub.add_parser("types")
    w = sub.add_parser("writeup")
    w.add_argument("problem", type=Path)
    w.add_argument("--open", action="store_true")
    h = sub.add_parser("hint")
    h.add_argument("problem", type=Path)
    h.add_argument("--level", type=int, default=1)
    h.add_argument("--all", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("problem", type=Path)
    c.add_argument("attempt", help="text file with the student's work, one step per line ('-' = stdin)")
    c.add_argument("--record", action="store_true", help="log the result in student/progress.json")
    pr = sub.add_parser("practice")
    prs = pr.add_subparsers(dest="action", required=True)
    pn = prs.add_parser("new")
    pn.add_argument("--course", default=None)
    pn.add_argument("--type", action="append", dest="types", help="type or type:variant (repeatable)")
    pn.add_argument("--n", type=int, default=1)
    pn.add_argument("--difficulty", type=int, default=None)
    pn.add_argument("--seed", type=int, default=None)
    pa = prs.add_parser("answer")
    pa.add_argument("session")
    pa.add_argument("question", type=int)
    pa.add_argument("text")
    ps = prs.add_parser("show")
    ps.add_argument("session", nargs="?", default="latest")
    pv = prs.add_parser("review")
    pv.add_argument("--n", type=int, default=3)
    pv.add_argument("--course", default=None)
    pf = prs.add_parser("finish")
    pf.add_argument("session", nargs="?", default="latest")
    tp = sub.add_parser("testprep")
    tps = tp.add_subparsers(dest="action", required=True)
    tn = tps.add_parser("new")
    tn.add_argument("course")
    tn.add_argument("test", help="test1 … test4 or final")
    tn.add_argument("--n", type=int, default=None)
    tn.add_argument("--seed", type=int, default=None)
    tn.add_argument("--open", action="store_true")
    tg = tps.add_parser("grade")
    tg.add_argument("session")
    tg.add_argument("answers", nargs="*")
    tg.add_argument("--file", type=Path, default=None, help="one answer per line")
    tg.add_argument("--open", action="store_true")
    tps.add_parser("upcoming")
    ex = sub.add_parser("explain")
    ex.add_argument("query", nargs="+")
    ex.add_argument("--course", default=None)
    ex.add_argument("--type", default=None, help="skip matching: use this type (or type:variant)")
    ex.add_argument("--make", action="store_true", help="build a verified worked example + write-up")
    ex.add_argument("--seed", type=int, default=0)
    ex.add_argument("--open", action="store_true")
    mt = sub.add_parser("materials")
    mts = mt.add_subparsers(dest="action", required=True)
    for name in ("ingest", "show"):
        m_ = mts.add_parser(name)
        m_.add_argument("--course", default=None)
    mf = mts.add_parser("find")
    mf.add_argument("query", nargs="+")
    mf.add_argument("--course", default=None)
    pg = sub.add_parser("progress")
    pg.add_argument("--open", action="store_true")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "types":
            for name in registry.names():
                t = registry.get(name)
                var = f"  variants: {', '.join(t.variants)}" if t.variants else ""
                print(f"{t.course}  {name:24} {t.title}  (needs: {', '.join(t.required)}){var}")
            return 0
        if args.cmd == "materials":
            from tutor.materials.cli import run as materials_run

            return materials_run(args)
        if args.cmd in ("practice", "testprep", "explain", "progress"):
            from tutor.study import cli

            return getattr(cli, "progress_cmd" if args.cmd == "progress" else args.cmd)(args)
        problem = load_problem(args.problem)
        if args.cmd in ("writeup", "hint", "check"):
            from tutor.study import cli

            return getattr(cli, args.cmd)(args, problem)
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
        if result.verified and not args.no_html:
            from tutor.writeup.html import write_solution

            print(f"Write-up: {write_solution(result, open_browser=args.open)}")
        if result.verified and args.log:
            from tutor.student import progress

            data = progress.load()
            progress.record(data, problem.topic, None, course=problem.course, problem=problem.slug)
            progress.save(data)
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
