"""/testprep: a timed mock test built from the course plan, graded, with a weak-spot report.

* Topics: every week that starts before the test date (tests are cumulative);
  weeks since the previous test count double (each test "focuses on recent topics").
* MATH 1104 allows no calculator, so questions are drawn at hand-doable difficulty.
* MATH 1004's final is multiple choice: options are the verified answer plus
  distractors PROVEN different from it (tutor/study/choices.py).
* After grading: score, every question with the verified answer, mistake types,
  topics to review (with textbook sections), and each missed question saved as a
  confirmed problem.json so a full write-up and video can be made for it.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from tutor import registry
from tutor.pipeline import PROJECT_ROOT, run
from tutor.student import progress
from tutor.study import plan
from tutor.study.practice import finish_quiz, grade_item, load_session, new_session, problem_of, save_session
from tutor.writeup import html as W

TESTS_DIR = progress.STUDENT_DIR / "tests"


def build(course: str, which: str, n: int | None = None, seed: int | None = None) -> dict:
    course = plan.norm_course(course)
    test = plan.find_test(course, which)
    earlier = [t for t in plan.tests(course) if t.date < test.date and t.number is not None]
    since = earlier[-1].date if earlier and test.number is not None else None
    base = plan.covered_specs(course, test.date, recent_since=since)
    # a test is graded automatically: leave out types that are only checked against a write-up
    base = {k: v for k, v in base.items() if registry.get(k.partition(":")[0]).grade is not None}
    if not base:
        raise ValueError(f"nothing in the course plan is taught before {test.name} ({test.date})")
    final = test.number is None
    n = n or (10 if final else 5)
    mc = final and course == "MATH1004"
    s = new_session("testprep", course, n=n, base=base, seed=seed, name=f"{course} {test.name} mock",
                    minutes=180 if final else 50, multiple_choice=mc,
                    difficulties=(1, 1, 2) if course == "MATH1104" else (1, 2, 2))
    s["test"] = {"name": test.name, "date": test.date.isoformat(), "multiple_choice": mc,
                 "topics": plan.topics_for(course, test.date), "covers_weeks": [str(w["week"]) for w in
                                                                               plan.weeks_before(course, test.date)]}
    save_session(s)
    folder = TESTS_DIR / s["id"]
    W.write(folder / "test.html", test_page(s))
    return s


def _question_html(item: dict, k: int) -> str:
    parts = [f'<div class="card problem"><strong>Question {k}</strong> '
             f'<span class="muted">({W.esc(item["title"])})</span>']
    if item.get("statement"):
        parts.append(f"<p>{W.esc(item['statement'])}</p>")
    if item.get("latex"):
        parts.append(W.display(item["latex"]))
    else:
        body = [ln for ln in item["describe"].splitlines()
                if not ln.startswith(("Course:", "Confirmed by student", "Statement:"))]
        parts.append("<pre style='white-space:pre-wrap;font:inherit'>" + W.esc("\n".join(body)) + "</pre>")
    if "choices" in item:
        parts.append("<ol type='A'>" + "".join(f"<li>\\({W.esc(c['latex'])}\\)</li>" for c in item["choices"])
                     + "</ol>")
    if "choices" in item:
        pass
    elif item.get("answer_format"):
        parts.append(f'<p class="muted">Answer format: {W.esc(item["answer_format"])}</p>')
    parts.append("</div>")
    return "".join(parts)


TIMER = """
<div class="card" id="timer-card"><strong>Time left: <span id="timer"></span></strong>
<span class="muted"> (starts when you open this page; work on paper, no calculator for MATH 1104)</span></div>
<script>
(function () {
  const total = %d * 60, key = "goatvex-%s";
  let start = null;
  try { start = Number(localStorage.getItem(key)); } catch (e) {}
  if (!start) { start = Date.now(); try { localStorage.setItem(key, String(start)); } catch (e) {} }
  function tick() {
    const left = Math.max(0, total - Math.floor((Date.now() - start) / 1000));
    const m = Math.floor(left / 60), s = left %% 60;
    document.getElementById("timer").textContent = m + ":" + String(s).padStart(2, "0") + (left === 0 ? "  (time's up)" : "");
    if (left > 0) setTimeout(tick, 1000);
  }
  document.addEventListener("DOMContentLoaded", tick);
})();
</script>
"""


def test_page(s: dict) -> str:
    t = s["test"]
    body = [TIMER % (s["minutes"], s["id"]),
            f'<p>Covers: {W.esc("; ".join(t["topics"]))}.</p>',
            '<p class="muted">Answers are hidden. When you are done, tell GoatVex your answers (or show your work) '
            'and it will grade the test and make a weak-spot report.</p>']
    body += [_question_html(it, k + 1) for k, it in enumerate(s["items"])]
    return W.page(f"{s['name']} ({s['minutes']} min)", "\n".join(body), crumbs=f"{s['course']} · test prep")


def grade(sid: str, answers: list[str], make_writeups: bool = True) -> dict:
    s = load_session(sid)
    for k, text in enumerate(answers, 1):
        if k <= len(s["items"]) and text.strip():
            grade_item(s, k, text)
    s = load_session(s["id"])
    q = finish_quiz(s)
    missed = [k for k, it in enumerate(s["items"], 1) if not (it["result"] and it["result"]["correct"])]
    s["missed_folders"] = {}
    if make_writeups:
        for k in missed:
            folder = save_missed(s, k)
            s["missed_folders"][str(k)] = str(folder.relative_to(PROJECT_ROOT))
    save_session(s)
    W.write(TESTS_DIR / s["id"] / "report.html", report_page(s, q))
    return s


def save_missed(s: dict, k: int) -> Path:
    """Save a missed question as a confirmed problem (GoatVex generated it, nothing to transcribe) + write-up."""
    item = s["items"][k - 1]
    p = problem_of(item)
    p.slug = f"{s['id']}-q{k}"
    p.topic = item["topic"]
    p.confirmed_by_student = True
    result = run(p)
    if result.verified:
        W.write_solution(result, practice=True)
    return result.out_dir


def report_page(s: dict, q: dict) -> str:
    rows = []
    for k, it in enumerate(s["items"], 1):
        r = it["result"] or {}
        ok = r.get("correct")
        mark = "✓" if ok else ("✗" if ok is False else "—")
        if "choices" in it:
            ch = next(c for c in it["choices"] if c["letter"] == it["correct_choice"])
            ans_html = f"({it['correct_choice']}) \\({W.esc(ch['latex'])}\\)"
        elif it.get("answer_latex"):
            ans_html = f"\\({W.esc(it['answer_latex'])}\\)"
        else:
            ans_html = W.esc(it["answer"])
        folder = s.get("missed_folders", {}).get(str(k))
        link = f' <a href="{W.esc(Path("../../..", folder, "solution.html").as_posix())}">write-up</a>' if folder else ""
        rows.append(f"<tr><td>{k}</td><td>{W.esc(it['title'])}</td><td>{mark}</td>"
                    f"<td>{W.esc(r.get('answer', 'not answered'))}</td><td>{ans_html}{link}</td>"
                    f"<td>{W.esc(r.get('mistake') or '')}</td></tr>")
    weak = {}
    for it in s["items"]:
        if not (it["result"] and it["result"]["correct"]):
            weak.setdefault(it["type"], 0)
            weak[it["type"]] += 1
    review = []
    for t in weak:
        pt = registry.get(t)
        secs = "; ".join(f"{b} §{', '.join(v)}" for b, v in pt.sections.items())
        review.append(f"<li><strong>{W.esc(pt.title)}</strong>: {W.esc(secs)}. Try <em>/practice {W.esc(t)}</em>.</li>")
    pct = round(100 * q["score"] / max(1, q["total"]))
    body = [f'<div class="card answer"><span class="label">Score: {q["score"]} / {q["total"]} ({pct}%)</span></div>',
            "<h2>Question by question</h2><table><tr><th>#</th><th>Topic</th><th></th><th>Your answer</th>"
            "<th>Verified answer</th><th>Mistake type</th></tr>" + "".join(rows) + "</table>"]
    body.append("<h2>What to review</h2>" + ("<ul>" + "".join(review) + "</ul>" if review else
                                             "<p>Nothing missed. Great work! Keep the streak going with "
                                             "spaced-repetition quizzes.</p>"))
    if s.get("missed_folders"):
        body.append('<p class="muted">Each missed question has a full verified write-up (linked above). Ask GoatVex '
                    'for the video of any of them.</p>')
    return W.page(f"{s['name']}: results", "\n".join(body), crumbs=f"{s['course']} · test prep")


def upcoming(today: date | None = None) -> list[plan.Test]:
    today = today or date.today()
    out = [t for c in plan.COURSES for t in plan.tests(c) if t.date >= today]
    return sorted(out, key=lambda t: t.date)
