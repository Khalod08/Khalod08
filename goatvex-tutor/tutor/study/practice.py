"""Practice sessions and mock tests: verified problems, hidden answers, grading, progress updates.

A session is a JSON file in student/sessions/. It holds the generated problems
(each one solved and verified before it was saved) and, separately, their
answers, which are never printed until the student has answered.
"""

from __future__ import annotations

import json
import random
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from tutor import registry
from tutor.parse.schema import problem_from_dict
from tutor.pipeline import solve_problem
from tutor.student import progress
from tutor.study import plan
from tutor.study.generate import answer_text, practice_tex, verified_problem

SESSIONS = progress.STUDENT_DIR / "sessions"


def _session_path(sid: str) -> Path:
    return SESSIONS / f"{sid}.json"


def save_session(s: dict) -> Path:
    SESSIONS.mkdir(parents=True, exist_ok=True)
    path = _session_path(s["id"])
    path.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_session(sid: str) -> dict:
    if sid == "latest":
        files = sorted(SESSIONS.glob("*.json"), key=lambda p: p.stat().st_mtime)
        if not files:
            raise FileNotFoundError("no practice sessions yet")
        return json.loads(files[-1].read_text(encoding="utf-8"))
    return json.loads(_session_path(sid).read_text(encoding="utf-8"))


def _topic_of(spec: str) -> str:
    return registry.get(spec.partition(":")[0]).topic


def available_specs(course: str, today: date | None = None) -> dict[str, float]:
    """Everything taught so far (by the course plan), or the first weeks before the term starts."""
    today = today or date.today()
    specs = plan.covered_specs(course, today + timedelta(days=1))
    if not specs:
        specs = plan.covered_specs(course, date.fromisoformat(plan.weeks(course)[1]["start"]))
    return specs


def choose_specs(course: str, n: int, data: dict, rng: random.Random, only: list[str] | None = None,
                 base: dict[str, float] | None = None) -> list[str]:
    """Weighted by weak spots and due reviews (tutor/student/progress.py), no repeats while possible."""
    base = base or ({s: 1.0 for s in only} if only else available_specs(course))
    weights = progress.topic_weights(data, [_topic_of(s) for s in base])
    pool = {s: base[s] * weights[_topic_of(s)] for s in base}
    out: list[str] = []
    while len(out) < n and pool:
        specs, w = zip(*pool.items())
        pick = rng.choices(specs, weights=w)[0]
        out.append(pick)
        if len(pool) > 1:
            pool.pop(pick)
        else:
            break
    while len(out) < n:  # fewer specs than questions: repeat
        out.append(rng.choice(list(base)))
    return out


def _latex_answer(sol) -> str | None:
    from tutor.text.latex import latex_of

    try:
        return latex_of(sol.answer)
    except Exception:  # noqa: BLE001
        return None


def _item(spec: str, rng: random.Random, difficulty: int, slug: str, multiple_choice: bool = False) -> dict:
    p, res = verified_problem(spec, rng, difficulty, slug=slug)
    pt = registry.get(p.type)
    extra = {}
    if multiple_choice:
        from tutor.study.choices import choices

        mc = choices(res.solution, rng)
        if mc:
            extra = mc
    return extra | {"spec": spec, "type": p.type, "topic": pt.topic, "course": p.course, "title": pt.title,
            "given": p.given, "statement": p.statement, "latex": practice_tex(p),
            "describe": pt.describe(p), "answer_format": pt.answer_format, "digest": res.solution.digest(),
            "answer": answer_text(res.solution),
            "answer_latex": _latex_answer(res.solution), "can_autograde": pt.grade is not None, "result": None}


def new_session(kind: str, course: str, n: int = 3, specs: list[str] | None = None, difficulty: int | None = None,
                seed: int | None = None, name: str = "", minutes: int | None = None,
                base: dict[str, float] | None = None, multiple_choice: bool = False,
                difficulties: tuple[int, ...] = (1, 2, 2)) -> dict:
    data = progress.load()
    seed = seed if seed is not None else int(time.time() * 1000) % 2**31
    rng = random.Random(seed)
    chosen = specs if (specs and len(specs) == n) else choose_specs(course, n, data, rng, specs, base)
    sid = f"{kind}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    items = []
    for k, spec in enumerate(chosen):
        d = difficulty if difficulty is not None else rng.choice(difficulties)
        items.append(_item(spec, rng, d, slug=f"{sid}-q{k + 1}", multiple_choice=multiple_choice))
    s = {"id": sid, "kind": kind, "course": course, "name": name or kind, "created": datetime.now().isoformat(
        timespec="seconds"), "seed": seed, "minutes": minutes, "items": items}
    save_session(s)
    return s


def problem_of(item: dict):
    return problem_from_dict(dict(slug="practice", course=item["course"], type=item["type"], given=item["given"],
                                  statement=item["statement"], confirmed_by_student=True))


def grade_item(s: dict, k: int, text: str, record: bool = True) -> dict:
    """Grade question k (1-based). Re-solves and re-verifies the stored problem; the digest must match."""
    item = s["items"][k - 1]
    p = problem_of(item)
    res = solve_problem(p)
    if not res.verified or res.solution.digest() != item["digest"]:
        raise RuntimeError("the stored problem no longer verifies the same way; not grading it")
    pt = registry.get(item["type"])
    if "choices" in item:
        letter = text.strip().strip("().").upper()[:1]
        ok = letter == item["correct_choice"]
        msg = "Correct!" if ok else f"Not quite: the answer is ({item['correct_choice']})."
    elif pt.grade is None:
        ok, msg = None, "This one is checked against the write-up rather than auto-graded."
    else:
        ok, msg = pt.grade(res.solution, text)
    mistake = None
    if ok is False and "choices" not in item:
        from tutor.study.check import check_attempt

        rep = check_attempt(res.solution, text)
        mistake = rep.mistake if rep.mistake not in (None, "other") else None
    item["result"] = {"answer": text, "correct": ok, "feedback": msg, "mistake": mistake,
                      "when": datetime.now().isoformat(timespec="seconds")}
    if record and ok is not None:
        data = progress.load()
        progress.record(data, item["topic"], ok, course=item["course"], mistake=mistake or (None if ok else "other"),
                        problem=item["statement"], detail=msg)
        progress.save(data)
    save_session(s)
    return item


def finish_quiz(s: dict) -> dict:
    """Store the session's score in progress.json (quiz history)."""
    data = progress.load()
    items = [{"q": i + 1, "topic": it["topic"], "type": it["type"],
              "correct": bool(it["result"] and it["result"]["correct"]),
              "mistake": it["result"]["mistake"] if it["result"] else "not answered"}
             for i, it in enumerate(s["items"])
             if not (it["result"] and it["result"]["correct"] is None)]  # write-up-checked items don't count
    q = progress.record_quiz(data, s["course"], s["name"], items)
    progress.save(data)
    s["score"] = {"score": q["score"], "total": q["total"]}
    save_session(s)
    return q


def question_text(item: dict, k: int) -> str:
    lines = [f"Question {k} ({item['title']})"]
    desc = [ln for ln in item["describe"].splitlines()
            if not ln.startswith(("Course:", "Confirmed by student", "Statement:"))]
    lines += desc
    if "choices" in item:
        lines.append("Answer: the letter of your choice")
    elif item["answer_format"]:
        lines.append(f"Answer format: {item['answer_format']}")
    return "\n".join(lines)
