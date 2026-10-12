"""Command handlers for the study modes (called from ``python -m tutor``)."""

from __future__ import annotations

import sys

from tutor import registry
from tutor.pipeline import PROJECT_ROOT, run, solve_problem
from tutor.student import progress
from tutor.study import plan
from tutor.text.unicode_math import to_text


def _rel(path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _verified(problem):
    result = solve_problem(problem)
    if not result.verified:
        print(f"Verification status is {result.status}: GoatVex won't give hints or check work against an "
              "unverified solution. Run `python -m tutor solve` and read the report.")
        return None
    return result


# ------------------------------------------------------------------ per-problem modes
def writeup(args, problem) -> int:
    from tutor.writeup.html import write_solution

    result = run(problem)
    if not result.verified:
        print(f"Not writing a write-up: verification status is {result.status}.")
        return 2
    print(f"Write-up: {_rel(write_solution(result, open_browser=args.open))}")
    return 0


def hint(args, problem) -> int:
    from tutor.study.hints import ladder

    result = _verified(problem)
    if result is None:
        return 2
    lad = ladder(result.solution)
    shown = lad if args.all else lad[: max(1, min(args.level, len(lad)))][-1:]
    for h in shown:
        print(f"Hint {h.level} of {h.total}: {h.title}")
        print("  " + h.text.replace("\n", "\n  "))
    if not args.all and args.level < len(lad):
        print(f"\n(Next: --level {args.level + 1})")
    return 0


def check(args, problem) -> int:
    from tutor.study.check import check_attempt

    result = _verified(problem)
    if result is None:
        return 2
    attempt = sys.stdin.read() if args.attempt == "-" else open(args.attempt, encoding="utf-8").read()
    rep = check_attempt(result.solution, attempt)
    print(rep.text())
    if args.record:
        data = progress.load()
        progress.record(data, problem.topic, rep.final_correct if rep.final_correct is not None else None,
                        course=problem.course, mistake=rep.mistake, problem=problem.slug, detail=rep.explanation)
        progress.save(data)
        print("\n(Logged in student/progress.json.)")
    return 0


# ------------------------------------------------------------------ sessions
def _print_session(s, show_results=True) -> None:
    from tutor.study.practice import question_text

    for k, it in enumerate(s["items"], 1):
        print(question_text(it, k))
        if "choices" in it:
            for c in it["choices"]:
                print(f"   ({c['letter']}) {c['text']}")
        if show_results and it["result"]:
            r = it["result"]
            print(f"   → you answered {r['answer']!r}: {r['feedback']}")
        print()


def practice(args) -> int:
    from tutor.study import practice as P

    if args.action in ("new", "review"):
        course = plan.norm_course(args.course) if args.course else None
        specs = getattr(args, "types", None)
        if args.action == "review":
            data = progress.load()
            due = progress.due(data)
            if not due:
                print("Nothing is due for review today. Try `practice new` for fresh problems.")
                return 0
            topics = [k for k, _ in due]
            specs = [n for n in registry.names() if registry.get(n).topic in topics and registry.get(n).generate
                     and (course is None or registry.get(n).course == course)]
            if not specs:
                print("The topics due for review have no practice generator; review their write-ups instead.")
                return 0
            course = course or registry.get(specs[0]).course
            specs = [n for n in specs if registry.get(n).course == course]
        if course is None:
            if specs:
                course = registry.get(specs[0].partition(":")[0]).course
            else:
                print("Which course? Use --course MATH1104 or --course MATH1004.")
                return 1
        s = P.new_session("practice" if args.action == "new" else "review", course, n=args.n, specs=specs,
                          difficulty=getattr(args, "difficulty", None), seed=getattr(args, "seed", None))
        print(f"Session {s['id']} ({len(s['items'])} question(s); every one solved and verified, answers hidden)\n")
        _print_session(s, show_results=False)
        print(f"Answer with: python -m tutor practice answer {s['id']} <question> \"<your answer>\"")
        return 0
    if args.action == "show":
        _print_session(P.load_session(args.session))
        return 0
    if args.action == "answer":
        s = P.load_session(args.session)
        it = P.grade_item(s, args.question, args.text)
        r = it["result"]
        print(r["feedback"])
        if r["correct"] is False:
            if r["mistake"]:
                print(f"Likely mistake: {r['mistake']}.")
            print(f"Verified answer: {it['answer']}")
        elif r["correct"] is None:
            print(f"Verified answer: {it['answer']}")
        left = [k for k, i in enumerate(s["items"], 1) if not i["result"]]
        if not left:
            q = P.finish_quiz(P.load_session(s["id"]))
            print(f"\nSession done: {q['score']}/{q['total']}. Progress updated.")
        return 0
    if args.action == "finish":
        q = P.finish_quiz(P.load_session(args.session))
        print(f"Recorded: {q['score']}/{q['total']}.")
        return 0
    return 1


def testprep(args) -> int:
    from tutor.study import testprep as T
    from tutor.writeup.html import write

    if args.action == "upcoming":
        for t in T.upcoming():
            print(f"{t.course} {t.name}: {t.date:%a %b %d}")
        return 0
    if args.action == "new":
        s = T.build(args.course, args.test, n=args.n, seed=args.seed)
        page = T.TESTS_DIR / s["id"] / "test.html"
        if args.open:
            write(page, page.read_text(encoding="utf-8"), open_browser=True)
        print(f"{s['name']}: {len(s['items'])} questions, {s['minutes']} minutes. Session {s['id']}.")
        print(f"Covers weeks {', '.join(s['test']['covers_weeks'])}: {'; '.join(s['test']['topics'])}")
        print(f"Test page: {_rel(page)}\n")
        _print_session(s, show_results=False)
        return 0
    if args.action == "grade":
        answers = list(args.answers)
        if args.file:
            answers = [ln.rstrip("\n") for ln in open(args.file, encoding="utf-8")]
        s = T.grade(args.session, answers)
        sc = s["score"]
        print(f"Score: {sc['score']}/{sc['total']}\n")
        for k, it in enumerate(s["items"], 1):
            r = it["result"] or {}
            mark = "✓" if r.get("correct") else "✗"
            ans = it["answer"] if "choices" not in it else f"({it['correct_choice']})"
            print(f"{mark} Q{k} {it['title']}: you {r.get('answer', '(no answer)')!r}; verified {ans}"
                  + (f"; mistake: {r['mistake']}" if r.get("mistake") else ""))
        for k, folder in s.get("missed_folders", {}).items():
            print(f"   Q{k} write-up: {folder}/solution.html   video: python -m tutor.video.render {folder}/problem.json")
        page = T.TESTS_DIR / s["id"] / "report.html"
        if args.open:
            write(page, page.read_text(encoding="utf-8"), open_browser=True)
        print(f"\nWeak-spot report: {_rel(page)}")
        return 0
    return 1


def explain(args) -> int:
    from tutor.study import explain as E

    course = plan.norm_course(args.course) if args.course else None
    if args.type:
        spec = args.type
    else:
        ranked = E.match(" ".join(args.query), course)
        if not ranked:
            print("No verified problem type matches that. GoatVex can still explain the idea in words "
                  "(clearly labelled as not machine-verified).")
            return 4
        for name, score in ranked:
            pt = registry.get(name)
            secs = "; ".join(f"{b} §{', '.join(v)}" for b, v in pt.sections.items())
            print(f"{name:24} {pt.title}  [{pt.course}; {secs}]  score {score:.1f}")
        spec = E.best_spec(" ".join(args.query), course) or ranked[0][0]
    if not args.make:
        print(f"\nBest match: {spec}. Add --make for a verified worked example + write-up.")
        return 0
    from tutor.writeup.html import write_solution

    result = E.example(spec, seed=args.seed)
    if not result.verified:
        print(f"The example didn't verify ({result.status}); not using it.")
        return 2
    sol = result.solution
    print(f"\nVerified example ({sol.problem.statement}):")
    for st in sol.steps:
        print(f"  {st.operation}: {to_text(st.after)}".replace("\n", "\n    "))
    print(f"{sol.answer_label}: {to_text(sol.answer)}")
    print(f"\nProblem file: {_rel(result.out_dir / 'problem.json')}")
    print(f"Write-up: {_rel(write_solution(result, open_browser=args.open))}")
    print(f"Video: python -m tutor.video.render {_rel(result.out_dir / 'problem.json')}")
    return 0


def progress_cmd(args) -> int:
    from tutor.study import report
    from tutor.writeup.html import write

    print(report.summary())
    path = write(progress.STUDENT_DIR / "progress.html", report.page(), open_browser=args.open)
    print(f"\nFull report: {_rel(path)}")
    return 0
